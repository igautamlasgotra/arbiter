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

_SYSTEM = """You allocate effort to a task. You are cost-aware: every extra agent \
and every extra iteration costs real tokens, so you only request them when the task \
plausibly needs them.

Available roles:
- generator: writes the solution. Always required.
- critic:    an LLM reviewer. Useful only when no strong automatic test exists,
             because it is unreliable and costs a call.
- repair:    a differently-primed solver for when refinement has stalled.

Guidance: a task with strong automatic verification rarely needs a critic, because
executed tests already give better feedback than an opinion. A task with weak
verification may need one. Simple tasks need one generator and few iterations."""


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

    return WorkflowSpec(
        roles=roles,
        validators=["tool"] + (["critic"] if "critic" in roles else []),
        # clamp: the planner is an LLM and will occasionally ask for 50 iterations
        max_iterations=max(1, min(int(data.get("max_iterations", 5)), 5)),
        rationale=f"{data.get('difficulty', '?')}: {data.get('rationale', '')}"[:300],
    )
