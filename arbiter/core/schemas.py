"""Frozen data contracts shared by all three workstreams.

These types are the interface between:
  - Aniket's benchmark/validators (produces Task, returns Verdict)
  - Chirag's agent roles        (returns Solution)
  - Gautam's orchestrator       (consumes all of the above, emits WorkflowSpec)

Changing a field here breaks someone else's module, so changes are discussed
before they are made.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Family(str, Enum):
    """Task families, ordered by strength of the available external verifier.

    This ordering IS the experiment (RQ2): CODE has per-test objective feedback,
    SQL has objective but final-only feedback, MATH has only a final answer check
    with no usable intermediate signal.
    """

    CODE = "code"
    SQL = "sql"
    MATH = "math"


class Task(BaseModel):
    """One benchmark item. Produced by arbiter.bench, consumed by everything else."""

    task_id: str
    family: Family
    prompt: str

    # --- family-specific verification payload ---
    # CODE: python source defining test cases, appended after the solution
    tests: Optional[str] = None
    entry_point: Optional[str] = None

    # SQL: gold query + the SQLite database to execute both against
    gold_sql: Optional[str] = None
    db_path: Optional[str] = None
    schema_text: Optional[str] = None

    # MATH: exact expected final answer
    gold_answer: Optional[str] = None

    meta: dict[str, Any] = Field(default_factory=dict)

    def verifier_strength(self) -> str:
        return {
            Family.CODE: "strong",
            Family.SQL: "medium",
            Family.MATH: "weak",
        }[self.family]


class Solution(BaseModel):
    """What a generator/repair agent returns. Kept deliberately small."""

    content: str = Field(description="The code, SQL query, or final answer only.")
    reasoning: str = Field(default="", description="Brief justification.")


class Critique(BaseModel):
    """What an LLM critic returns. Separate from Verdict: a critic is advisory."""

    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggestion: str = ""


class Verdict(BaseModel):
    """The output of any validator, tool-based or LLM-based.

    `score` carries partial credit (e.g. fraction of unit tests passed) so the
    orchestrator can detect *improvement* rather than only pass/fail. Without
    partial credit the no-improvement stop condition cannot fire meaningfully.
    """

    passed: bool
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    detail: str = Field(default="", description="Feedback text handed to the agent.")
    validator: str = "unknown"
    is_objective: bool = Field(
        default=True,
        description="True for tool/execution validators, False for LLM critics. "
        "Used to compute the false-accept rate (RQ3).",
    )
    evidence: dict[str, Any] = Field(default_factory=dict)


class WorkflowSpec(BaseModel):
    """What the planner emits for ONE task. The 'adaptive' part of the system.

    Roles are selected from a fixed library (arbiter.agents.roles) - never
    invented at runtime. Runtime invention is unbounded and unevaluable; see
    docs/ARBITER_PLAN.md section B3.
    """

    roles: list[str] = Field(default_factory=lambda: ["generator"])
    validators: list[str] = Field(default_factory=list)
    max_iterations: int = 5
    rationale: str = ""

    def with_role(self, role: str) -> "WorkflowSpec":
        if role in self.roles:
            return self
        return self.model_copy(update={"roles": [*self.roles, role]})


class Action(str, Enum):
    """Decision-policy outcomes. Every iteration ends in exactly one of these."""

    ACCEPT = "accept"
    REFINE = "refine"
    ADD_AGENT = "add_agent"
    ESCALATE = "escalate"
    STOP = "stop"
