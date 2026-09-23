"""Resumable experiment runner.

Resumability is not a nicety. A full sweep is thousands of calls against a
free tier; a quota error six hours in must not destroy the run. Every finished
task-run is appended to JSONL immediately and skipped on the next invocation,
so re-running the same command after the quota resets simply continues.

Usage:
    python -m arbiter.bench.runner --dataset smoke --conditions A B --seeds 0
    python -m arbiter.bench.runner --dataset smoke --conditions D --adaptive
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from arbiter.config import TRACE_DIR, build_router
from arbiter.core.schemas import Task
from arbiter.core.state import Budget
from arbiter.llm.router import AllKeysExhaustedError, LLMRouter
from arbiter.orchestrator.loop import run_task

DATASET_DIR = Path(__file__).parent / "datasets"


def load_tasks(name: str) -> list[Task]:
    path = DATASET_DIR / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"no dataset at {path}")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [Task.model_validate(r) for r in rows]


def completed_keys(out: Path) -> set[tuple[str, str, int]]:
    """(task_id, condition, seed) triples already on disk."""
    if not out.exists():
        return set()
    done = set()
    for line in out.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerate a torn final line from a killed run
        done.add((r["task_id"], r["condition"], r.get("seed", 0)))
    return done


def run_sweep(
    tasks: Iterable[Task],
    router: LLMRouter,
    conditions: list[str],
    seeds: list[int],
    out: Path,
    adaptive: bool = False,
    budget: Budget | None = None,
) -> dict:
    done = completed_keys(out)
    tasks = list(tasks)
    total = len(tasks) * len(conditions) * len(seeds)
    ran = skipped = failed = 0

    for seed in seeds:
        for condition in conditions:
            for task in tasks:
                key = (task.task_id, condition, seed)
                if key in done:
                    skipped += 1
                    continue
                try:
                    state = run_task(
                        task,
                        router,
                        condition=condition,
                        seed=seed,
                        adaptive=adaptive or condition == "D",
                        budget=budget.model_copy() if budget else None,
                    )
                except AllKeysExhaustedError as exc:
                    print(f"\n!! {exc}")
                    print(f"   progress saved to {out}; rerun this command to resume.")
                    return {"ran": ran, "skipped": skipped, "failed": failed, "halted": True}
                except Exception as exc:  # one bad task must not sink the sweep
                    failed += 1
                    print(f"  {task.task_id}/{condition}: ERROR {exc}")
                    continue

                state.append_jsonl(out)
                ran += 1
                mark = "PASS" if state.best_score >= 1.0 else "fail"
                print(
                    f"  [{ran + skipped}/{total}] {task.task_id} {condition} s{seed}: "
                    f"{mark} score={state.best_score:.2f} "
                    f"iters={state.iteration} calls={state.llm_calls} "
                    f"tok={state.tokens_used} stop={state.stop_reason.value if state.stop_reason else '?'}"
                )

    return {"ran": ran, "skipped": skipped, "failed": failed, "halted": False}


def main() -> None:
    ap = argparse.ArgumentParser(description="ARBITER experiment runner")
    ap.add_argument("--dataset", default="smoke")
    ap.add_argument("--conditions", nargs="+", default=["B"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--out", default=None)
    ap.add_argument("--adaptive", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=60_000)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    out = Path(args.out) if args.out else TRACE_DIR / f"{args.dataset}.jsonl"
    router = build_router(cache_enabled=not args.no_cache)
    tasks = load_tasks(args.dataset)

    print(
        f"dataset={args.dataset} tasks={len(tasks)} "
        f"conditions={args.conditions} seeds={args.seeds} -> {out}"
    )
    summary = run_sweep(
        tasks,
        router,
        args.conditions,
        args.seeds,
        out,
        adaptive=args.adaptive,
        budget=Budget(max_tokens=args.max_tokens),
    )
    print(f"\n{summary} | router {router.stats}")


if __name__ == "__main__":
    main()
