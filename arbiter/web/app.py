"""FastAPI demo server.

Purpose: make it visible that real agents are doing real work. The panel types
a task, and the agent cards, validator output and counters appear live as the
loop runs - not after it finishes.

Three deliberate choices:

1. Server-Sent Events, not WebSockets. The stream is one-directional and SSE
   reconnects by itself. Less code, fewer failure modes in a live demo.

2. The run executes in a worker thread and pushes events onto a queue. The
   orchestrator knows nothing about the web layer; it just calls a callback.

3. `/api/replay` serves a stored trace with the original timings. If the API
   key is dead or the venue wifi fails during the demo, the replay looks
   identical and is clearly labelled as a replay. Never bluff a live run.

Code execution is controlled by two switches, because the public deployment and
a laptop are not the same threat model:

  ARBITER_ALLOW_EXEC   must be 1 before any generated program is run at all.
  ARBITER_DEMO_TOKEN   when set, every *live* run must present that token.

On the public host both are set: the deployment can execute code, but only for
someone holding the demo link. Visitors without it still get the full interface,
the offline scripted provider and replay of stored runs - and cannot spend the
API quota or run code. Without the token gate a public URL that executes
model-written Python is simply a remote shell, so it is not offered.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from arbiter.config import TRACE_DIR, build_router
from arbiter.core.schemas import Family, Task
from arbiter.core.state import Budget, RunState, TraceEvent
from arbiter.llm.cache import ResponseCache
from arbiter.llm.mock import MockProvider
from arbiter.llm.router import LLMRouter

app = FastAPI(title="ARBITER", docs_url="/api/docs")

TEMPLATES = Path(__file__).parent / "templates"
ALLOW_EXEC = os.getenv("ARBITER_ALLOW_EXEC", "1") == "1"
DEMO_TOKEN = os.getenv("ARBITER_DEMO_TOKEN", "").strip()


def _authorise_live_run(token: Optional[str]) -> None:
    """Live runs spend real quota and execute real code. Gate them if asked."""
    if not DEMO_TOKEN:
        return  # local development: no token configured, no gate
    if (token or "").strip() != DEMO_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="live runs on this deployment require the demo link. "
            "Use 'Offline demo' or the replay view instead.",
        )


class RunRequest(BaseModel):
    task: str
    family: str = "code"
    condition: str = "B"
    mock: bool = False
    expected: str = ""   # MATH only: the answer the run is checked against


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _router(mock: bool) -> LLMRouter:
    if mock:
        return LLMRouter([MockProvider()], ResponseCache(enabled=False))
    # the demo key is reserved: the batch experiment runner never touches it,
    # so demo-day quota is always fresh
    return build_router(demo=True)


def _event_payload(e: TraceEvent, st: RunState) -> dict[str, Any]:
    return {
        "ts": round(e.ts, 2),
        "iteration": e.iteration,
        "kind": e.kind,
        "role": e.role,
        "summary": e.summary,
        "data": e.data,
        "metrics": {
            "iterations": st.iteration,
            "llm_calls": st.llm_calls,
            "tokens": st.tokens_used,
            "elapsed": round(st.elapsed, 1),
            "roles": st.spec.roles,
            "best_score": round(st.best_score, 3) if st.best_score >= 0 else None,
        },
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (TEMPLATES / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health(x_arbiter_token: Optional[str] = Header(default=None)) -> dict[str, Any]:
    keys_present = bool(os.getenv("ARBITER_DEMO_KEY") or os.getenv("ARBITER_GEMINI_KEYS"))
    authorised = not DEMO_TOKEN or (x_arbiter_token or "").strip() == DEMO_TOKEN
    return {
        "ok": True,
        "live_mode_available": keys_present and authorised,
        "keys_present": keys_present,
        "auth_required": bool(DEMO_TOKEN),
        "authorised": authorised,
        "exec_enabled": ALLOW_EXEC,
        "traces": sorted(p.name for p in TRACE_DIR.glob("*.jsonl")) if TRACE_DIR.exists() else [],
    }


@app.post("/api/run")
def run(
    req: RunRequest, x_arbiter_token: Optional[str] = Header(default=None)
) -> StreamingResponse:
    """Stream a live run as Server-Sent Events."""
    if not req.mock:
        _authorise_live_run(x_arbiter_token)
    if not ALLOW_EXEC and req.family == "code":
        raise HTTPException(
            status_code=403,
            detail="code execution is disabled on this deployment; use the SQL or "
            "math families, or the replay endpoint",
        )

    try:
        family = Family(req.family)
    except ValueError:
        raise HTTPException(400, f"unknown family {req.family!r}")

    q: queue.Queue = queue.Queue()
    sentinel = object()

    def worker() -> None:
        try:
            router = _router(req.mock)
            task = Task(
                task_id=f"live-{int(time.time())}",
                family=family,
                prompt=req.task,
                gold_answer=req.expected.strip() or None,
            )

            state = RunState(
                task=task,
                condition=req.condition,
                budget=Budget(),
                on_event=lambda e, st: q.put(_event_payload(e, st)),
            )

            # The math validator compares against a known answer and has nothing
            # else to go on - that weakness is the point of the family, but it
            # means a typed task must come with the answer or nothing can be
            # checked at all.
            if family is Family.MATH and not task.gold_answer:
                q.put(
                    {
                        "kind": "unsupported",
                        "summary": "A math task needs the expected answer to check "
                        "against. This family is deliberately the weakest verifier "
                        "in the study: it can only say right or wrong, never which "
                        "step was wrong. Enter the answer in the field beside the "
                        "task, or use the code family.",
                    }
                )
                q.put(sentinel)
                return

            # An unseen task has no tests. The test designer writes them first;
            # without this the validator has nothing to check against.
            if family is Family.CODE:
                from arbiter.agents.test_designer import (
                    InfeasibleTaskError,
                    TestPlanError,
                    attach_tests,
                )

                try:
                    task = attach_tests(task, router, state)
                    state.task = task
                except InfeasibleTaskError as exc:
                    # Not a malfunction: the system declines what it cannot
                    # verify rather than pretending to have checked it.
                    q.put({"kind": "unsupported", "summary": str(exc)})
                    q.put(sentinel)
                    return
                except TestPlanError as exc:
                    q.put({"kind": "error", "summary": f"test design failed: {exc}"})
                    q.put(sentinel)
                    return

            from arbiter.orchestrator.loop import run_task_with_state

            run_task_with_state(
                state, router, condition=req.condition, adaptive=req.condition == "D"
            )

            q.put(
                {
                    "kind": "final",
                    "summary": "done",
                    "data": {
                        "passed": state.best_score >= 1.0,
                        "score": round(state.best_score, 3),
                        "content": state.best_content or "",
                        "stop_reason": state.stop_reason.value if state.stop_reason else None,
                        "tests": task.tests or "",
                    },
                    "metrics": {
                        "iterations": state.iteration,
                        "llm_calls": state.llm_calls,
                        "tokens": state.tokens_used,
                        "elapsed": round(state.elapsed, 1),
                        "roles": state.spec.roles,
                    },
                }
            )
        except Exception as exc:  # surface the real reason in the UI
            q.put({"kind": "error", "summary": f"{type(exc).__name__}: {exc}"})
        finally:
            q.put(sentinel)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        yield _sse("start", {"task": req.task, "condition": req.condition, "mock": req.mock})
        while True:
            item = q.get()
            if item is sentinel:
                break
            yield _sse(item.get("kind", "event"), item)
        yield _sse("end", {})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/replay")
def replay(trace: str, task_id: Optional[str] = None, speed: float = 4.0) -> StreamingResponse:
    """Replay a stored run with its original timing. The demo safety net."""
    path = TRACE_DIR / trace
    if not path.exists():
        raise HTTPException(404, f"no trace {trace!r}")

    runs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if task_id:
        runs = [r for r in runs if r["task_id"] == task_id]
    if not runs:
        raise HTTPException(404, "no matching run in trace")
    run_record = runs[0]

    def stream():
        yield _sse(
            "start",
            {
                "task": run_record["task_id"],
                "condition": run_record["condition"],
                "replay": True,
            },
        )
        previous = 0.0
        for e in run_record["trace"]:
            delay = max(0.0, (e["ts"] - previous)) / max(speed, 0.1)
            time.sleep(min(delay, 1.5))
            previous = e["ts"]
            yield _sse(e["kind"], {**e, "metrics": {}, "replay": True})
        yield _sse(
            "final",
            {
                "kind": "final",
                "data": {
                    "passed": run_record.get("passed"),
                    "score": run_record.get("best_score"),
                    "content": run_record.get("final_content") or "",
                    "stop_reason": run_record.get("stop_reason"),
                },
                "metrics": {
                    "iterations": run_record.get("iterations"),
                    "llm_calls": run_record.get("llm_calls"),
                    "tokens": run_record.get("total_tokens"),
                    "roles": run_record.get("roles_used", []),
                },
                "replay": True,
            },
        )
        yield _sse("end", {})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/results")
def results(trace: str = "smoke.jsonl") -> dict[str, Any]:
    """Aggregated metrics for the results view."""
    from arbiter.bench.metrics import by_condition, format_table, load_runs

    runs = load_runs(TRACE_DIR / trace)
    table = by_condition(runs)
    return {"n_runs": len(runs), "by_condition": table, "markdown": format_table(table)}
