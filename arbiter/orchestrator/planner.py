"""Adaptive workflow planning - condition D.

This is the only place where the system decides *what shape of work* a task
needs. It is one LLM call producing a WorkflowSpec, constrained to roles that
actually exist.

Honest framing for the report and the viva: adaptive orchestration is not our
invention. It is an active, surveyed subfield (DyFlow, DAAO, AdaptOrch,
AgentSpawn, AORCHESTRA). What we contribute is measuring whether it still pays
off once the token budget is held equal against a single agent - which the
existing papers do not test, despite efficiency being their whole argument.
"""

from __future__ import annotations

from arbiter.core.schemas import Family, Task, WorkflowSpec
from arbiter.core.state import RunState
from arbiter.llm.router import LLMRouter

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "roles": {
            "type": "array",
            "items": {"type": "string", "enum": ["generator", "critic", "repair"]},
        },
        "max_iterations": {"type": "integer"},
        "rationale": {"type": "string"},
    },
    "required": ["difficulty", "roles", "max_iterations"],
}

_SYSTEM = """You allocate effort to a task. You are cost-aware, but the two things
you allocate do not cost the same way, and that distinction matters more than
anything else here.

ROLES cost unconditionally. Every role you add spends a model call on every task,
whether or not it turned out to be needed. Add one only when the task plausibly
needs it.

ITERATIONS cost only on failure. The iteration budget is a ceiling, not a plan:
the loop stops the moment the solution passes. Allowing 4 iterations on a task
that is solved at the first attempt costs exactly as much as allowing 1. Allowing
only 1 on a task that fails throws away the verifier's feedback for no saving.

So: be strict with roles, generous with iterations.

Available roles:
- generator: writes the solution. Always required.
- critic:    an LLM reviewer. Useful only when no strong automatic test exists,
             because it is unreliable and costs a call on every task.
- repair:    a differently-primed solver for when refinement has stalled.

Guidance: a task with strong automatic verification rarely needs a critic, because
executed tests already give better feedback than an opinion - but it is exactly
where iterations are most valuable, because that feedback can be trusted. A task
with weak verification may need a critic and gains less from iterating."""


def plan_adaptive(task: Task, router: LLMRouter, state: RunState) -> WorkflowSpec:
    prompt = (
        f"TASK FAMILY: {task.family.value}\n"
        f"AUTOMATIC VERIFIER STRENGTH: {task.verifier_strength()}\n"
        f"TASK:\n{task.prompt[:1500]}\n\n"
        "Choose the minimum set of roles and iterations that will plausibly "
        "solve this correctly."
    )
    try:
        resp = router.call(
            prompt,
            state=state,
            system=_SYSTEM,
            schema=PLAN_SCHEMA,
            temperature=0.0,
            seed=state.seed,
        )
        import json

        data = json.loads(resp.text)
    except Exception as exc:
        # planning must never sink a run; fall back to the safe default
        state.record("error", summary=f"planner fell back: {exc}"[:200])
        return WorkflowSpec(
            roles=["generator"],
            validators=["tool"],
            max_iterations=5,
            rationale="planner failed, default workflow",
        )

    roles = [r for r in data.get("roles", []) if r in {"generator", "critic", "repair"}]
    if "generator" not in roles:
        roles.insert(0, "generator")

    # A floor, not just a ceiling. Asked to be cost-aware, the planner reliably
    # requested a single iteration on code tasks, which silently collapses the
    # adaptive condition into the one-shot baseline: it would generate once and
    # discard the executed-test feedback it had just called trustworthy. An
    # unused iteration is free, so refusing to allow one is never the cheaper
    # choice. Where the verifier is strong its feedback is worth acting on, so
    # the floor is higher there.
    floor = 3 if task.verifier_strength() == "strong" else 2
    requested = int(data.get("max_iterations", 5))
    max_iterations = max(floor, min(requested, 5))

    return WorkflowSpec(
        roles=roles,
        validators=["tool"] + (["critic"] if "critic" in roles else []),
        # clamp: the planner is an LLM and will occasionally ask for 50 iterations
        max_iterations=max_iterations,
        rationale=f"{data.get('difficulty', '?')}: {data.get('rationale', '')}"[:300],
    )
