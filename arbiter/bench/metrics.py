"""Compute every reported number from the JSONL traces.

There is no separate measurement system. If a number is in the report, it came
from here, and it can be recomputed by anyone who has the trace file. That is
the reproducibility requirement in the brief.

Two guard rails are deliberate:
  - runs produced by the mock provider are refused, so a dry run can never be
    mistaken for a result
  - nothing is estimated or interpolated; if data is missing the cell is empty
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def load_runs(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # tolerate a torn final line from an interrupted run
    return runs


def _is_mock(run: dict[str, Any]) -> bool:
    for event in run.get("trace", []):
        if event.get("data", {}).get("provider") == "mock":
            return True
    return bool(run.get("provider") == "mock")


def false_accept_count(run: dict[str, Any]) -> int:
    """Times the LLM critic approved something execution rejected (RQ3)."""
    return sum(
        1
        for e in run.get("trace", [])
        if e.get("kind") == "validate" and e.get("data", {}).get("false_accept")
    )


def summarise(runs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    runs = [r for r in runs if not _is_mock(r)]
    if not runs:
        return {"n": 0}

    passed = [r for r in runs if r.get("passed")]
    tokens = [r.get("total_tokens", 0) for r in runs]
    calls = [r.get("llm_calls", 0) for r in runs]
    iters = [r.get("iterations", 0) for r in runs]
    scores = [r.get("best_score", 0.0) for r in runs]

    stops: dict[str, int] = defaultdict(int)
    for r in runs:
        stops[r.get("stop_reason") or "unknown"] += 1

    return {
        "n": len(runs),
        "pass_rate": round(len(passed) / len(runs), 4),
        "mean_score": round(statistics.fmean(scores), 4),
        "mean_tokens": round(statistics.fmean(tokens), 1),
        "median_tokens": round(statistics.median(tokens), 1),
        "total_tokens": sum(tokens),
        "mean_llm_calls": round(statistics.fmean(calls), 2),
        "mean_iterations": round(statistics.fmean(iters), 2),
        "false_accepts": sum(false_accept_count(r) for r in runs),
        "stop_reasons": dict(stops),
    }


def by_condition(runs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list] = defaultdict(list)
    for r in runs:
        buckets[r.get("condition", "?")].append(r)
    return {c: summarise(rs) for c, rs in sorted(buckets.items())}


def by_family_condition(runs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The table that answers RQ2: does benefit track verifier strength?"""
    buckets: dict[str, list] = defaultdict(list)
    for r in runs:
        buckets[f"{r.get('family','?')}/{r.get('condition','?')}"].append(r)
    return {k: summarise(v) for k, v in sorted(buckets.items())}


def tokens_per_solve(summary: dict[str, Any]) -> float | None:
    """Cost-effectiveness: mean tokens spent per task actually solved.

    This is the number that matters for the research question. A condition
    that passes 10% more tasks while spending 300% more tokens is not better,
    and a raw pass-rate table hides that.
    """
    if not summary.get("n") or not summary.get("pass_rate"):
        return None
    solved = summary["n"] * summary["pass_rate"]
    return round(summary["mean_tokens"] * summary["n"] / solved, 1) if solved else None


def format_table(by_cond: dict[str, dict[str, Any]]) -> str:
    """Markdown table, ready to paste into the report."""
    if not by_cond or all(s.get("n", 0) == 0 for s in by_cond.values()):
        return "_No non-mock runs recorded yet._"

    head = (
        "| Condition | n | Pass rate | Mean score | Mean tokens | "
        "Tokens/solve | Mean calls | Mean iters | False accepts |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for cond, s in by_cond.items():
        if not s.get("n"):
            continue
        tps = tokens_per_solve(s)
        rows.append(
            f"| {cond} | {s['n']} | {s['pass_rate']:.1%} | {s['mean_score']:.3f} | "
            f"{s['mean_tokens']:.0f} | {tps if tps is not None else '--'} | "
            f"{s['mean_llm_calls']:.1f} | {s['mean_iterations']:.1f} | {s['false_accepts']} |"
        )
    return head + "\n".join(rows)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="ARBITER metrics")
    ap.add_argument("trace", help="path to a traces/*.jsonl file")
    ap.add_argument("--by-family", action="store_true")
    args = ap.parse_args()

    runs = load_runs(args.trace)
    print(f"loaded {len(runs)} runs from {args.trace}\n")
    table = by_family_condition(runs) if args.by_family else by_condition(runs)
    print(format_table(table))


if __name__ == "__main__":
    main()
