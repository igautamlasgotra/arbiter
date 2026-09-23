"""Key rotation, caching and budget accounting in front of any provider.

This is the only object the rest of the system calls. It does four jobs:

1. Cache lookup first, so a repeated call costs nothing.
2. Round-robin across several API keys, so three free-tier accounts behave
   like one account with three times the daily quota.
3. Retire a key for the day when it reports daily-quota exhaustion, instead of
   retrying it into the ground.
4. Charge every call to the RunState budget, which is what makes budget-matched
   comparison between conditions possible at all.
"""

from __future__ import annotations

import itertools
import time
from typing import Any, Optional, Sequence

from arbiter.core.state import RunState
from arbiter.llm.base import (
    LLMError,
    LLMProvider,
    LLMResponse,
    QuotaExhaustedError,
    RateLimitError,
    TransientError,
)
from arbiter.llm.cache import ResponseCache, cache_key


class AllKeysExhaustedError(LLMError):
    """Every key is out of daily quota. The runner must checkpoint and stop."""


class LLMRouter:
    def __init__(
        self,
        providers: Sequence[LLMProvider],
        cache: Optional[ResponseCache] = None,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        if not providers:
            raise ValueError("LLMRouter needs at least one provider")
        self.providers = list(providers)
        self.cache = cache or ResponseCache()
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._exhausted: set[int] = set()
        self._cycle = itertools.cycle(range(len(self.providers)))

    # ---- key selection ----------------------------------------------

    def _live_indices(self) -> list[int]:
        return [i for i in range(len(self.providers)) if i not in self._exhausted]

    def _next_provider(self) -> tuple[int, LLMProvider]:
        live = self._live_indices()
        if not live:
            raise AllKeysExhaustedError(
                "all API keys report daily quota exhausted; "
                "checkpoint and resume after the quota resets (midnight PT)"
            )
        for _ in range(len(self.providers)):
            idx = next(self._cycle)
            if idx in live:
                return idx, self.providers[idx]
        idx = live[0]
        return idx, self.providers[idx]

    # ---- main entry point -------------------------------------------

    def call(
        self,
        prompt: str,
        *,
        state: Optional[RunState] = None,
        system: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
        seed: Optional[int] = None,
    ) -> LLMResponse:
        head = self.providers[0]
        key = cache_key(
            provider=head.name,
            model=head.model,
            prompt=prompt,
            system=system,
            schema=schema,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            seed=seed,
        )

        cached = self.cache.get(key)
        if cached is not None:
            if state is not None:
                state.charge(
                    cached.usage.prompt_tokens, cached.usage.completion_tokens, cached=True
                )
            return cached

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            idx, provider = self._next_provider()
            try:
                resp = provider.generate(
                    prompt,
                    system=system,
                    schema=schema,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    seed=seed,
                )
            except QuotaExhaustedError as exc:
                # retire this key for the rest of the run and try the next one
                self._exhausted.add(idx)
                last_error = exc
                continue
            except RateLimitError as exc:
                last_error = exc
                time.sleep(self.backoff_seconds * (2**attempt))
                continue
            except TransientError as exc:
                last_error = exc
                time.sleep(self.backoff_seconds * (2**attempt))
                continue

            self.cache.put(key, resp)
            if state is not None:
                state.charge(
                    resp.usage.prompt_tokens, resp.usage.completion_tokens, cached=False
                )
            return resp

        if self._live_indices():
            raise TransientError(f"exhausted retries: {last_error}")
        raise AllKeysExhaustedError(f"all keys exhausted: {last_error}")

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "cache_hits": self.cache.hits,
            "cache_misses": self.cache.misses,
            "cache_hit_rate": round(self.cache.hit_rate, 3),
            "keys_total": len(self.providers),
            "keys_exhausted": len(self._exhausted),
        }
