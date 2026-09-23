"""Execution-based validator for the CODE family.

This is the most important component in the project and it contains no LLM.

Huang et al. (ICLR 2024) showed that iterative refinement without external
feedback does not help and often degrades output. The subprocess below IS that
external feedback. Everything the refinement loop achieves on the code family
is attributable to this file, not to the critic.
"""

from __future__ import annotations

import json
import re

from arbiter.core.schemas import Task, Verdict
from arbiter.sandbox.runner import run_python

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)

# Appended after solution + tests. Each test is a zero-arg callable named
# check_* or a plain assert block; we count them individually so `score`
# carries partial credit rather than only pass/fail.
_HARNESS = '''
import json as _json, traceback as _tb
_results = []
_checks = [(_n, _f) for _n, _f in sorted(globals().items())
           if _n.startswith("check_") and callable(_f)]
if not _checks:
    _results.append({"name": "module", "ok": True, "error": ""})
for _n, _f in _checks:
    try:
        _f()
        _results.append({"name": _n, "ok": True, "error": ""})
    except Exception:
        _results.append({"name": _n, "ok": False,
                         "error": _tb.format_exc(limit=3)[-500:]})
print("__ARBITER__" + _json.dumps(_results))
'''


def strip_fences(text: str) -> str:
    """Models wrap code in markdown fences roughly half the time."""
    match = _FENCE.search(text)
    return (match.group(1) if match else text).strip()


def validate_code(task: Task, solution: str) -> Verdict:
    if not task.tests:
        return Verdict(
            passed=False,
            detail="task has no tests attached",
            validator="python_exec",
            evidence={"error": "missing tests"},
        )

    program = "\n\n".join([strip_fences(solution), task.tests, _HARNESS])
    result = run_python(program)

    if result.timed_out:
        return Verdict(
            passed=False,
            score=0.0,
            detail=(
                "Your solution did not finish within the time limit. "
                "Check for an infinite loop or an inefficient algorithm."
            ),
            validator="python_exec",
            evidence={"timed_out": True},
        )

    marker = "__ARBITER__"
    if marker not in result.stdout:
        # crashed before the harness ran: syntax error, import error, etc.
        err = (result.stderr or "no output").strip()[-1200:]
        return Verdict(
            passed=False,
            score=0.0,
            detail=f"Your code failed to run.\n\n{err}",
            validator="python_exec",
            evidence={"returncode": result.returncode, "stderr": err},
        )

    payload = result.stdout.split(marker, 1)[1].strip().splitlines()[0]
    try:
        checks = json.loads(payload)
    except json.JSONDecodeError:
        return Verdict(
            passed=False,
            detail="validator could not parse the test harness output",
            validator="python_exec",
            evidence={"raw": payload[:500]},
        )

    total = len(checks) or 1
    passed_n = sum(1 for c in checks if c["ok"])
    failures = [c for c in checks if not c["ok"]]

    if failures:
        lines = [f"{passed_n}/{total} tests passed. Failures:"]
        for c in failures[:4]:
            lines.append(f"\n- {c['name']}:\n{c['error']}")
        detail = "\n".join(lines)
    else:
        detail = f"All {total} tests passed."

    return Verdict(
        passed=passed_n == total,
        score=passed_n / total,
        detail=detail,
        validator="python_exec",
        is_objective=True,
        evidence={
            "tests_total": total,
            "tests_passed": passed_n,
            "failed": [c["name"] for c in failures],
            "duration_s": round(result.duration_s, 3),
        },
    )
