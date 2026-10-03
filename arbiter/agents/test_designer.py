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

import ast
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
        "feasible": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["entry_point", "signature", "tests", "feasible"],
}

_SYSTEM = """You write executable Python tests for a described task.

FIRST decide whether the task can be expressed as ONE pure function whose
correctness a unit test can assert. Set `feasible` accordingly.

Set feasible=false when the task asks for an application, a web or desktop UI, a
server, a game loop, file or database access, user interaction, randomness, or
anything whose result is not a value returned from a single call. Put a one-line
explanation in `reason` and leave the other fields empty.

If feasible=true, follow these rules exactly:
- Choose ONE function name and signature that a solution should implement.
- Write 3 to 6 test functions. Each MUST be named check_<something> and take no
  arguments. Each MUST use a plain `assert`.
- Tests may import from the standard library only where genuinely needed
  (e.g. math). No file access, no network, no input(), no randomness.
- Cover the ordinary case, at least one boundary case, and at least one tricky
  case. Do not write tests whose expected value you are unsure of.
- `tests` must be valid Python source, nothing else - no markdown fence, no prose.
"""

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Pure, deterministic standard-library modules a test may legitimately need.
# `random` and `time` are excluded deliberately: a non-deterministic test makes
# the whole refinement signal meaningless.
_ALLOWED_IMPORTS = frozenset(
    {
        "math", "cmath", "re", "string", "itertools", "functools", "operator",
        "collections", "bisect", "heapq", "fractions", "decimal", "statistics",
        "textwrap", "unicodedata", "typing",
    }
)

# Names that give generated code a way out of pure computation.
_BANNED_CALLS = frozenset(
    {
        "open", "exec", "eval", "compile", "input", "__import__", "breakpoint",
        "globals", "locals", "vars", "getattr", "setattr", "delattr", "exit",
        "quit", "memoryview",
    }
)


class TestPlanError(RuntimeError):
    pass


class InfeasibleTaskError(TestPlanError):
    """The task cannot be checked by running unit tests against one function."""


def _check_test_source(tests: str) -> None:
    """Reject unsafe generated tests.

    Parsed rather than string-matched. Substring checks were both too strict and
    too loose: they rejected `import math`, and the word "import" inside a string
    literal, while a construct spelled differently would have slipped past. They
    also never confirmed the source was valid Python, so a syntax error surfaced
    much later as a confusing execution failure.
    """
    try:
        tree = ast.parse(tests)
    except SyntaxError as exc:
        raise TestPlanError(f"generated tests are not valid Python: {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                roots = [(node.module or "").split(".")[0]]
            else:
                roots = [a.name.split(".")[0] for a in node.names]
            for root in roots:
                if root not in _ALLOWED_IMPORTS:
                    raise TestPlanError(
                        f"generated tests import {root!r}, which is not an allowed "
                        "standard-library module"
                    )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _BANNED_CALLS:
                raise TestPlanError(
                    f"generated tests call {node.func.id}(), which is not permitted"
                )
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise TestPlanError(
                f"generated tests reach into {node.attr!r}, which is not permitted"
            )


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

    if data.get("feasible") is False:
        reason = (data.get("reason") or "").strip()
        raise InfeasibleTaskError(
            "This task cannot be checked automatically. The code family validates "
            "a solution by running unit tests against a single function, so it "
            "handles problems of the form “write a function that …”. "
            + (f"The task designer's reading: {reason} " if reason else "")
            + "Try a self-contained function, or pick the math family."
        )

    entry = (data.get("entry_point") or "").strip()
    signature = (data.get("signature") or "").strip()
    tests = (data.get("tests") or "").strip()

    if not _IDENT.match(entry):
        raise TestPlanError(f"invalid entry point {entry!r}")
    if "def check_" not in tests:
        raise TestPlanError("no check_* test functions produced")

    # Defence in depth behind the sandbox, not instead of it.
    _check_test_source(tests)

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
