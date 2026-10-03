"""Test-designer agent: turns a natural-language task into executable tests.

Why this exists
---------------
The brief requires the system to accept *previously unseen* runtime tasks.
Benchmark tasks ship with their own test suite, but a task typed by a panel
member at demo time does not. Without this agent the system can only validate
tasks it already had answers for, which would make the whole demo circular.

This is AgentCoder's "test designer" role. The important design detail is that
it fixes the ENTRY POINT as well as the tests. If the test designer invents
`two_sum` and the generator writes `twoSum`, every test fails for the wrong
reason. So the signature is decided here, once, and handed to the generator.

Honest limitation, stated in the report: tests written by a model are not
ground truth. A wrong test makes a correct solution look broken. For benchmark
measurement we therefore use the dataset's own tests; model-written tests are
used only for live, unseen tasks. The two are never mixed in results.
"""

from __future__ import annotations

import re

from arbiter.core.schemas import Task
from arbiter.core.state import RunState
from arbiter.llm.router import LLMRouter

TESTPLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "entry_point": {"type": "string"},
        "signature": {"type": "string"},
        "tests": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["entry_point", "signature", "tests"],
}

_SYSTEM = """You write executable Python tests for a described task.

Rules you must follow exactly:
- Choose ONE function name and signature that a solution should implement.
- Write 3 to 6 test functions. Each MUST be named check_<something> and take no
  arguments. Each MUST use a plain `assert`.
- Tests may only call the entry-point function. No imports, no file access, no
  network, no input().
- Cover the ordinary case, at least one boundary case, and at least one tricky
  case. Do not write tests whose expected value you are unsure of.
- `tests` must be valid Python source, nothing else - no markdown fence, no prose.
"""

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FORBIDDEN = ("import ", "open(", "__", "exec(", "eval(", "input(", "subprocess")


class TestPlanError(RuntimeError):
    pass


def design_tests(task: Task, router: LLMRouter, state: RunState) -> tuple[str, str, str]:
    """Return (entry_point, signature, test_source) for an unseen task.

    Raises TestPlanError if the model produces something unusable, so the
    caller can fall back rather than running garbage.
    """
    import json

    prompt = (
        f"TASK:\n{task.prompt}\n\n"
        "Design the function signature and the tests that a correct solution "
        "must pass."
    )
    resp = router.call(
        prompt,
        state=state,
        system=_SYSTEM,
        schema=TESTPLAN_SCHEMA,
        temperature=0.0,
        seed=state.seed,
    )

    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError as exc:
        raise TestPlanError(f"test designer returned invalid JSON: {exc}") from exc

    entry = (data.get("entry_point") or "").strip()
    signature = (data.get("signature") or "").strip()
    tests = (data.get("tests") or "").strip()

    if not _IDENT.match(entry):
        raise TestPlanError(f"invalid entry point {entry!r}")
    if "def check_" not in tests:
        raise TestPlanError("no check_* test functions produced")

    # The tests run in the same sandbox as the solution, but there is no reason
    # for generated tests to touch the filesystem or the network, so refuse
    # anything that tries. Defence in depth behind the sandbox, not instead of it.
    lowered = tests.lower()
    for bad in _FORBIDDEN:
        if bad in lowered:
            raise TestPlanError(f"generated tests contain forbidden construct {bad!r}")

    # Make sure the tests actually exercise the function we are going to ask for
    if entry not in tests:
        raise TestPlanError(f"tests never call the entry point {entry!r}")

    return entry, signature, tests


def attach_tests(task: Task, router: LLMRouter, state: RunState) -> Task:
    """Return a copy of `task` with model-designed tests attached.

    Used for live/unseen tasks only. Benchmark tasks already carry their own
    tests and must never be routed through here.
    """
    entry, signature, tests = design_tests(task, router, state)
    state.record(
        "design_tests",
        summary=f"entry={entry}, {tests.count('def check_')} tests",
        role="test_designer",
        entry_point=entry,
        signature=signature,
    )
    augmented_prompt = (
        f"{task.prompt}\n\n"
        f"Implement exactly this function (the name and parameters must match):\n"
        f"{signature}"
    )
    return task.model_copy(
        update={"tests": tests, "entry_point": entry, "prompt": augmented_prompt}
    )
