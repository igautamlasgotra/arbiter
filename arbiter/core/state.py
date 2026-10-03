"""Run state, budget enforcement and the execution trace.

The Budget is the methodological heart of the project: budget-matched
comparison between conditions is only possible because every LLM call is
metered here. See docs/ARBITER_PLAN.md section A2.
"""

from __future__ import annotations

import hashlib
import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from arbiter.core.schemas import Task, WorkflowSpec


class StopReason(str, Enum):
    ACCEPTED = "accepted"
    MAX_ITERATIONS = "max_iterations"
    MAX_LLM_CALLS = "max_llm_calls"
    MAX_TOKENS = "max_tokens"
    MAX_WALL_SECONDS = "max_wall_seconds"
    NO_IMPROVEMENT = "no_improvement"
    CYCLE_DETECTED = "cycle_detected"
    ERROR = "error"


class Budget(BaseModel):
    """Hard caps. The loop can never run unbounded (brief section 9)."""

    max_iterations: int = 5
    max_llm_calls: int = 20
    max_tokens: int = 60_000
    max_wall_seconds: float = 180.0
    no_improvement_patience: int = 2

    @classmethod
    def matched_to(cls, tokens_used: int, **overrides: Any) -> "Budget":
        """Build a budget matched to another run's actual token spend.

        This is how condition A+ (budget-matched single agent) is constructed:
        we first run the adaptive condition, read its real token usage, then
        give the single agent the same allowance. Without this, any comparison
        between conditions is confounded by compute (Tran & Kiela, 2025).
        """
        return cls(max_tokens=tokens_used, **overrides)


class TraceEvent(BaseModel):
    """One line of provenance. Everything measurable is derived from these."""

    ts: float
    iteration: int
    kind: str  # plan | generate | validate | decide | stop | error
    role: Optional[str] = None
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class RunState:
    """Mutable state for a single task run under a single condition."""

    def __init__(
        self,
        task: Task,
        condition: str,
        budget: Optional[Budget] = None,
        seed: int = 0,
        on_event: Optional[Callable[[TraceEvent, "RunState"], None]] = None,
    ) -> None:
        self.task = task
        self.condition = condition
        self.budget = budget or Budget()
        self.seed = seed
        # Optional live listener. The web UI uses this to stream agent cards as
        # they happen; the batch runner leaves it unset. Keeping it a plain
        # callback means the orchestrator has no idea a UI exists.
        self.on_event = on_event

        self.iteration = 0
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cached_calls = 0
        self.started_at = time.time()

        self.spec: WorkflowSpec = WorkflowSpec()
        self.feedback: Optional[str] = None
        self.best_score: float = -1.0
        self.best_content: Optional[str] = None
        self.stale_iterations = 0
        self._seen: set[str] = set()

        self.trace: list[TraceEvent] = []
        self.stop_reason: Optional[StopReason] = None

    # ---- accounting -------------------------------------------------

    @property
    def tokens_used(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at

    def charge(self, prompt_tokens: int, completion_tokens: int, cached: bool) -> None:
        """Record one LLM call against the budget.

        Cached responses still count as calls for reproducibility bookkeeping
        but are reported separately so cost can be computed honestly: a cached
        run costs nothing in money but the *experiment* still consumed that
        many tokens conceptually.
        """
        self.llm_calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        if cached:
            self.cached_calls += 1

    # ---- termination ------------------------------------------------

    def should_stop(self) -> Optional[StopReason]:
        b = self.budget
        if self.iteration >= b.max_iterations:
            return StopReason.MAX_ITERATIONS
        if self.llm_calls >= b.max_llm_calls:
            return StopReason.MAX_LLM_CALLS
        if self.tokens_used >= b.max_tokens:
            return StopReason.MAX_TOKENS
        if self.elapsed >= b.max_wall_seconds:
            return StopReason.MAX_WALL_SECONDS
        if self.stale_iterations >= b.no_improvement_patience:
            return StopReason.NO_IMPROVEMENT
        return None

    def note_attempt(self, content: str, score: float) -> bool:
        """Register an attempt. Returns True if it improved on the best so far.

        Also detects repeated identical outputs, which is MAST failure mode
        'step repetition' - the single most common multi-agent failure (17.1%).
        """
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest in self._seen:
            self.stop_reason = StopReason.CYCLE_DETECTED
        self._seen.add(digest)

        improved = score > self.best_score
        if improved:
            self.best_score = score
            self.best_content = content
            self.stale_iterations = 0
        else:
            self.stale_iterations += 1
        return improved

    # ---- trace ------------------------------------------------------

    def record(
        self,
        kind: str,
        summary: str = "",
        role: Optional[str] = None,
        **data: Any,
    ) -> None:
        event = TraceEvent(
            ts=time.time() - self.started_at,
            iteration=self.iteration,
            kind=kind,
            role=role,
            summary=summary,
            data=data,
        )
        self.trace.append(event)
        if self.on_event is not None:
            try:
                self.on_event(event, self)
            except Exception:
                # a broken UI listener must never break a research run
                pass

    def to_record(self) -> dict[str, Any]:
        """Flat record for JSONL. One line per task-run; this is the dataset
        every number in the report is computed from."""
        return {
            "task_id": self.task.task_id,
            "family": self.task.family.value,
            "verifier_strength": self.task.verifier_strength(),
            "condition": self.condition,
            "seed": self.seed,
            "passed": bool(self.best_score >= 1.0),
            "best_score": self.best_score,
            "iterations": self.iteration,
            "llm_calls": self.llm_calls,
            "cached_calls": self.cached_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.tokens_used,
            "wall_seconds": round(self.elapsed, 3),
            "roles_used": self.spec.roles,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "final_content": self.best_content,
            "trace": [e.model_dump() for e in self.trace],
        }

    def append_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(self.to_record(), ensure_ascii=False) + "\n")
