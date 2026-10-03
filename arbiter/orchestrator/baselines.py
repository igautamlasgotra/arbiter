"""Condition A+ : the budget-matched single agent.

This is the most important baseline in the project and the one almost every
student multi-agent project omits. Without it, "our multi-agent system beat a
single LLM call" is meaningless, because the multi-agent system spent five
times the tokens to do it.

Method: sample the generator N times at a non-zero temperature until the token
budget given to the adaptive condition is consumed, then pick an answer by
majority vote over normalised outputs (self-consistency). Crucially A+ does NOT
get to see the validator - if it did, it would be a refinement loop, not a
single agent, and the comparison would be rigged in its favour.

Honest limitation to state in the report: exact-match majority voting works
well for math, where answers normalise to a number, and poorly for code, where
two correct programs rarely match character for character. That asymmetry is
itself informative - it is part of why refinement may help more on code - but
it must be reported, not hidden, because it makes A+ a weaker opponent on code
than on math.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from arbiter.agents import roles
from arbiter.core.schemas import Family, Task
from arbiter.core.state import Budget, RunState, StopReason
from arbiter.llm.router import LLMRouter
from arbiter.validators.answer_match import normalise
from arbiter.validators.python_exec import strip_fences


def _vote_key(content: str, family: Family) -> str:
    """Normalise an output so that equivalent answers collide."""
    if family is Family.MATH:
        return normalise(content)
    # code / sql: strip fences and collapse whitespace so formatting noise
    # does not split otherwise-identical candidates
    return " ".join(strip_fences(content).split())


def run_single_budget_matched(
    task: Task,
    router: LLMRouter,
    *,
    token_budget: int,
    seed: int = 0,
    max_samples: int = 8,
    temperature: float = 0.7,
) -> RunState:
    """Condition A+. Spends up to `token_budget` on independent samples."""
    state = RunState(
        task=task,
        condition="A+",
        budget=Budget(
            max_tokens=token_budget,
            max_llm_calls=max_samples,
            max_iterations=max_samples,
        ),
        seed=seed,
    )
    state.record("plan", summary=f"self-consistency, budget={token_budget} tokens")

    candidates: list[str] = []
    while len(candidates) < max_samples:
        if state.tokens_used >= token_budget:
            state.stop_reason = StopReason.MAX_TOKENS
            break
        state.iteration = len(candidates) + 1
        try:
            # vary the seed per sample, otherwise a deterministic provider
            # returns the identical answer N times and "voting" is a no-op
            sample_state = state
            sample_state.seed = seed * 1000 + len(candidates)
            sol = roles.generator(task, router, sample_state, feedback=None)
        except Exception as exc:
            state.record("error", summary=str(exc)[:300])
            break
        content = strip_fences(sol.content)
        candidates.append(content)
        state.record("generate", summary=f"sample {len(candidates)}", role="generator")

    state.seed = seed  # restore for the record

    if not candidates:
        state.stop_reason = state.stop_reason or StopReason.ERROR
        state.record("stop", summary="no samples produced")
        return state

    votes = Counter(_vote_key(c, task.family) for c in candidates)
    winning_key, winning_count = votes.most_common(1)[0]
    chosen = next(c for c in candidates if _vote_key(c, task.family) == winning_key)

    state.record(
        "decide",
        summary=f"majority {winning_count}/{len(candidates)}",
        distinct_candidates=len(votes),
        agreement=round(winning_count / len(candidates), 3),
    )

    # Scoring happens exactly once, after the answer is locked in - the same
    # way condition A is scored. The validator never influenced the choice.
    from arbiter.orchestrator.loop import validate

    verdict = validate(task, chosen)
    state.best_score = verdict.score
    state.best_content = chosen
    state.record(
        "validate",
        summary=f"{verdict.validator} score={verdict.score:.2f}",
        role=verdict.validator,
        passed=verdict.passed,
        score=verdict.score,
    )
    state.stop_reason = state.stop_reason or (
        StopReason.ACCEPTED if verdict.passed else StopReason.MAX_ITERATIONS
    )
    state.record("stop", summary=state.stop_reason.value)
    return state
