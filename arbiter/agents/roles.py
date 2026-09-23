"""The fixed role library.

Roles are SELECTED from this library per task, never invented at runtime.
Runtime invention is unbounded, unreproducible and impossible to evaluate -
see docs/ARBITER_PLAN.md section B3.

An agent here is exactly three things: a role prompt, one LLM call, and a
typed parse of the result. There is no agent base class, no message bus, no
framework. That is the whole point - the orchestration logic stays visible.
"""

from __future__ import annotations

from typing import Optional

from arbiter.core.schemas import Critique, Family, Solution, Task, Verdict
from arbiter.llm.router import LLMRouter
from arbiter.core.state import RunState

# JSON schemas handed to the model so structured output is enforced by the
# API rather than requested politely in the prompt.
SOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "reasoning": {"type": "string"},
    },
    "required": ["content"],
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "suggestion": {"type": "string"},
    },
    "required": ["passed"],
}

_OUTPUT_RULES = {
    Family.CODE: (
        "Return complete, runnable Python. Define the required function at module "
        "level. Do not include tests, examples, or explanatory prose in `content`."
    ),
    Family.SQL: (
        "Return a single SQL query in `content`. No prose, no markdown fence, "
        "no trailing semicolon commentary."
    ),
    Family.MATH: (
        "Put ONLY the final numeric answer in `content` - no units, no working. "
        "Put your working in `reasoning`."
    ),
}


def _task_block(task: Task) -> str:
    parts = [f"TASK:\n{task.prompt}"]
    if task.schema_text:
        parts.append(f"DATABASE SCHEMA:\n{task.schema_text}")
    parts.append(f"OUTPUT REQUIREMENT:\n{_OUTPUT_RULES[task.family]}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- generator


def generator(
    task: Task, router: LLMRouter, state: RunState, feedback: Optional[str] = None
) -> Solution:
    """Produces a first attempt, or a revision when feedback is supplied."""
    system = (
        "You are a precise software engineer. You produce correct, minimal "
        "solutions and you follow output format requirements exactly."
    )
    prompt = _task_block(task)
    if feedback:
        prompt += (
            "\n\nYOUR PREVIOUS ATTEMPT FAILED VALIDATION.\n"
            f"{feedback}\n\n"
            "Fix the specific problems above. Do not rewrite working parts "
            "unnecessarily. Return the complete corrected solution."
        )

    resp = router.call(
        prompt,
        state=state,
        system=system,
        schema=SOLUTION_SCHEMA,
        temperature=0.0,
        seed=state.seed,
    )
    return Solution.model_validate_json(resp.text)


# ------------------------------------------------------------------- repair


def repair(task: Task, router: LLMRouter, state: RunState, feedback: str) -> Solution:
    """A second, differently-primed solver.

    This is the mentor's 'third agent that solves it again'. It is deliberately
    NOT the generator with more feedback: it is told to distrust the previous
    approach, which is what makes it something other than another refinement
    step. Whether that independence actually helps is measured, not assumed.
    """
    system = (
        "You are a debugging specialist. A previous engineer's solution failed. "
        "Do not assume their approach was correct - if it is fundamentally wrong, "
        "replace it rather than patching it."
    )
    prompt = (
        f"{_task_block(task)}\n\n"
        f"FAILED ATTEMPT AND ITS VALIDATION OUTPUT:\n{feedback}\n\n"
        "Diagnose the root cause, then return a complete working solution."
    )
    resp = router.call(
        prompt,
        state=state,
        system=system,
        schema=SOLUTION_SCHEMA,
        temperature=0.2,
        seed=state.seed,
    )
    return Solution.model_validate_json(resp.text)


# ------------------------------------------------------------------ critic


def critic(task: Task, solution: str, router: LLMRouter, state: RunState) -> Critique:
    """LLM reviewer - advisory only, never authoritative.

    Its verdict is recorded separately from the tool verdict so we can compute
    the false-accept rate: how often the critic says PASS while execution says
    FAIL. That number is the answer to RQ3.
    """
    system = (
        "You review solutions for correctness. You are sceptical and specific. "
        "You do not approve code you have not reasoned through."
    )
    prompt = (
        f"{_task_block(task)}\n\n"
        f"PROPOSED SOLUTION:\n{solution}\n\n"
        "Identify concrete correctness problems: wrong logic, unhandled edge "
        "cases, format violations. Set passed=true only if you find none."
    )
    resp = router.call(
        prompt,
        state=state,
        system=system,
        schema=CRITIQUE_SCHEMA,
        temperature=0.0,
        seed=state.seed,
    )
    return Critique.model_validate_json(resp.text)


def critique_to_verdict(c: Critique) -> Verdict:
    detail = c.suggestion if c.passed else "\n".join(f"- {i}" for i in c.issues)
    return Verdict(
        passed=c.passed,
        score=1.0 if c.passed else 0.0,
        detail=detail or ("looks correct" if c.passed else "unspecified issues"),
        validator="llm_critic",
        is_objective=False,  # <- excluded from ground truth; see RQ3
    )


ROLE_LIBRARY = {
    "generator": generator,
    "repair": repair,
    "critic": critic,
}
