"""Disk cache for LLM responses.

This is not an optimisation, it is a project-critical component. Reasons:

1. Quota. A full sweep is ~6,000+ calls against a free tier of roughly 1,500
   requests/day across three keys. Without a cache, every re-run of the
   experiment (and there will be many while the metrics code is being written)
   costs another full day of quota.

2. Reproducibility. The brief (section 9) requires that results be
   reproducible. LLMs are non-deterministic; a cache keyed on the exact request
   makes a re-run of the analysis return byte-identical model outputs.

Key = sha256 over everything that can change the response. If any of those
inputs differ, it is a different call and must hit the API.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from arbiter.llm.base import LLMResponse


def cache_key(
    *,
    provider: str,
    model: str,
    prompt: str,
    system: Optional[str],
    schema: Optional[dict[str, Any]],
    temperature: float,
    max_output_tokens: int,
    seed: Optional[int],
) -> str:
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "system": system,
            "schema": schema,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "seed": seed,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, root: str | Path = ".cache/llm", enabled: bool = True) -> None:
        self.root = Path(root)
        self.enabled = enabled
        self.hits = 0
        self.misses = 0
        if self.enabled:
            try:
                self.root.mkdir(parents=True, exist_ok=True)
            except OSError:
                # Serverless hosts mount the deployment read-only. Losing the
                # cache costs quota; crashing the demo costs the demo.
                self.enabled = False

    def _path(self, key: str) -> Path:
        # shard by first 2 chars so directories stay small
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Optional[LLMResponse]:
        if not self.enabled:
            return None
        fp = self._path(key)
        if not fp.exists():
            self.misses += 1
            return None
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # a corrupt cache entry must never break a run
            self.misses += 1
            return None
        self.hits += 1
        resp = LLMResponse.model_validate(data)
        resp.cached = True
        return resp

    def put(self, key: str, response: LLMResponse) -> None:
        if not self.enabled:
            return
        fp = self._path(key)
        payload = response.model_dump()
        payload["cached"] = False  # store the original, mark on read
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            tmp = fp.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(fp)  # atomic, so a killed run cannot leave a partial file
        except OSError:
            self.enabled = False  # read-only disk: degrade, never fail the run

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
