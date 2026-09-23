"""Final-answer validator for the MATH family.

Deliberately the weakest validator in the system. It can only tell the agent
"wrong answer" - it cannot say which step was wrong. That is exactly why the
math family is in the benchmark: it is the control case where refinement has
almost no external signal to work with, which is where Huang et al. predict
iterative refinement stops helping.

Note the asymmetry with python_exec: there, `score` is graded (fraction of
tests). Here it is binary, because a partially-correct number is still wrong.
"""

from __future__ import annotations

import re

from arbiter.core.schemas import Task, Verdict

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def normalise(text: str) -> str:
    """Pull a comparable numeric answer out of model output."""
    cleaned = text.strip().replace(",", "").replace("$", "").replace("%", "")
    # models often still write "The answer is 42." despite the format instruction
    matches = _NUM.findall(cleaned)
    if not matches:
        return cleaned.lower()
    value = matches[-1]
    try:
        f = float(value)
    except ValueError:
        return value
    return str(int(f)) if f.is_integer() else str(f)


def validate_answer(task: Task, solution: str) -> Verdict:
    if task.gold_answer is None:
        return Verdict(
            passed=False, detail="task has no gold answer", validator="answer_match"
        )

    got = normalise(solution)
    want = normalise(task.gold_answer)
    ok = got == want

    return Verdict(
        passed=ok,
        score=1.0 if ok else 0.0,
        detail=(
            "Correct."
            if ok
            else f"Incorrect. Your answer was {got!r}. Re-check your working; "
            "the arithmetic or the interpretation of the problem is wrong."
        ),
        validator="answer_match",
        is_objective=True,
        evidence={"got": got, "expected": want},
    )
