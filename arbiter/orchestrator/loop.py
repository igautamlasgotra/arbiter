"""The refinement loop.

This is literally what the mentor described:

    one agent solves -> another tests and validates it -> a third solves it
    again using that feedback -> repeat until the solution is correct

with one necessary addition: it is bounded. "Repeat until correct" is an
infinite loop on any task the model cannot solve, so the loop also stops on
iteration / call / token / wall-clock limits, on convergence, and on repeated
identical output. Every stop is recorded with its reason.

Conditions A, B and D are the SAME loop with different settings - not three
codebases. That is what keeps the comparison honest.
"""

from __future__ import annotations

from typing import Optional

from arbiter.agents import roles
from arbiter.core.schemas import Action, Family, Task, Verdict, WorkflowSpec
from arbiter.core.state import Budget, RunState, StopReason
from arbiter.llm.router import LLMRouter
from arbiter.validators.answer_match import validate_answer
from arbiter.validators.python_exec import strip_fences, validate_code


def validate(task: Task, content: str) -> Verdict:
    """Objective, tool-based validation. Dispatch on family."""
    if task.family is Family.CODE:
        return validate_code(task, content)
    if task.family is Family.MATH:
        return validate_answer(task, content)
    return Verdict(
        passed=False,
        detail=f"no validator wired for family {task.family.value} yet",
        validator="none",
    )


def plan_static(task: Task, condition: str) -> WorkflowSpec:
    """Fixed workflows for the baseline conditions."""
    if condition == "A":  # single agent, one shot
        return WorkflowSpec(roles=["generator"], max_iterations=1, rationale="baseline A")
    if condition == "B":  # generator <-> validator loop
        return WorkflowSpec(
            roles=["generator"], validators=["tool"], max_iterations=5, rationale="baseline B"
        )
    if condition == "C":  # fixed pipeline with a critic and a separate repairer
        return WorkflowSpec(
            roles=["generator", "critic", "repair"],
            validators=["tool", "critic"],
            max_iterations=5,
            rationale="baseline C",
        )
    return WorkflowSpec(roles=["generator"], validators=["tool"], max_iterations=5)


def decide(verdict: Verdict, state: RunState) -> Action:
    """Decision policy. Small and inspectable on purpose.

    The adaptive behaviour lives here and in the planner: escalate from plain
    refinement to a differently-primed solver once refinement has visibly
    stopped working, rather than repeating the same move.
    """
    if verdict.passed:
        return Action.ACCEPT
    if state.should_stop() is not None:
        return Action.STOP
    # two failures with no score improvement: refinement is not working,
    # bring in the repair specialist instead of asking again
    if state.stale_iterations >= 1 and "repair" not in state.spec.roles:
        return Action.ADD_AGENT
    return Action.REFINE


def run_task(
    task: Task,
    router: LLMRouter,
    *,
    condition: str = "B",
    budget: Optional[Budget] = None,
    seed: int = 0,
    adaptive: bool = False,
) -> RunState:
    """Execute one task under one condition. Returns the full RunState."""
    state = RunState(task=task, condition=condition, budget=budget, seed=seed)

    if adaptive:
        from arbiter.orchestrator.planner import plan_adaptive

        state.spec = plan_adaptive(task, router, state)
    else:
        state.spec = plan_static(task, condition)
    state.budget.max_iterations = min(
        state.budget.max_iterations, state.spec.max_iterations
    )
    state.record("plan", summary=state.spec.rationale, roles=state.spec.roles)

    solution_text = ""
    while True:
        reason = state.should_stop()
        if reason is not None:
            state.stop_reason = reason
            break
        state.iteration += 1

        # ---- generate ------------------------------------------------
        try:
            use_repair = "repair" in state.spec.roles and state.feedback is not None
            if use_repair:
                sol = roles.repair(task, router, state, state.feedback or "")
                actor = "repair"
            else:
                sol = roles.generator(task, router, state, state.feedback)
                actor = "generator"
            solution_text = strip_fences(sol.content)
        except Exception as exc:  # provider failure, malformed JSON, etc.
            state.record("error", summary=str(exc)[:300])
            state.stop_reason = StopReason.ERROR
            break

        state.record("generate", summary=f"{len(solution_text)} chars", role=actor)

        # ---- validate: tools first, they are ground truth -------------
        verdict = validate(task, solution_text)
        state.record(
            "validate",
            summary=f"{verdict.validator} score={verdict.score:.2f}",
            role=verdict.validator,
            passed=verdict.passed,
            score=verdict.score,
            is_objective=verdict.is_objective,
        )

        # ---- optional LLM critic, recorded but never authoritative -----
        if "critic" in state.spec.roles and not verdict.passed:
            try:
                crit = roles.critic(task, solution_text, router, state)
                cv = roles.critique_to_verdict(crit)
                state.record(
                    "validate",
                    summary=f"critic passed={cv.passed}",
                    role="llm_critic",
                    passed=cv.passed,
                    is_objective=False,
                    # false accept: critic approved something execution rejected
                    false_accept=bool(cv.passed and not verdict.passed),
                )
                if cv.detail:
                    verdict = verdict.model_copy(
                        update={"detail": f"{verdict.detail}\n\nReviewer notes:\n{cv.detail}"}
                    )
            except Exception as exc:
                state.record("error", summary=f"critic failed: {exc}"[:300])

        state.note_attempt(solution_text, verdict.score)
        if state.stop_reason is StopReason.CYCLE_DETECTED:
            state.record("stop", summary="identical output repeated")
            break

        # ---- decide ---------------------------------------------------
        action = decide(verdict, state)
        state.record("decide", summary=action.value)

        if action is Action.ACCEPT:
            state.stop_reason = StopReason.ACCEPTED
            state.best_score = max(state.best_score, verdict.score)
            state.best_content = solution_text
            break
        if action is Action.STOP:
            state.stop_reason = state.should_stop() or StopReason.MAX_ITERATIONS
            break
        if action is Action.ADD_AGENT:
            state.spec = state.spec.with_role("repair")
            state.record("plan", summary="added repair agent", roles=state.spec.roles)

        state.feedback = (
            f"Validation result: {verdict.detail}\n\n"
            f"Your previous attempt was:\n{solution_text}"
        )

    state.record("stop", summary=(state.stop_reason or StopReason.ERROR).value)
    return state
