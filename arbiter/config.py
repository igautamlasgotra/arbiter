"""Settings loaded from environment / .env. No secret ever appears in code."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from arbiter.llm.cache import ResponseCache
from arbiter.llm.gemini import GeminiProvider
from arbiter.llm.router import LLMRouter

load_dotenv()

MODEL = os.getenv("ARBITER_MODEL", "gemini-flash-lite-latest")
CACHE_DIR = os.getenv("ARBITER_CACHE_DIR", ".cache/llm")
TRACE_DIR = Path(os.getenv("ARBITER_TRACE_DIR", "traces"))

_KEY_LABELS = ("gautam", "chirag", "aniket")


def _keys() -> list[str]:
    raw = os.getenv("ARBITER_GEMINI_KEYS", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def build_router(
    *,
    demo: bool = False,
    model: Optional[str] = None,
    cache_enabled: bool = True,
) -> LLMRouter:
    """Construct the router.

    `demo=True` uses ARBITER_DEMO_KEY only. That key is never touched by the
    experiment runner, so the live demo in front of the panel always has fresh
    daily quota no matter how hard the benchmark was run that week.
    """
    model = model or MODEL
    cache = ResponseCache(CACHE_DIR, enabled=cache_enabled)

    if demo:
        key = os.getenv("ARBITER_DEMO_KEY", "")
        if not key:
            raise RuntimeError("ARBITER_DEMO_KEY is not set; see .env.example")
        return LLMRouter([GeminiProvider(key, model, label="demo")], cache)

    keys = _keys()
    if not keys:
        raise RuntimeError("ARBITER_GEMINI_KEYS is not set; see .env.example")
    providers = [
        GeminiProvider(k, model, label=_KEY_LABELS[i] if i < len(_KEY_LABELS) else f"key{i}")
        for i, k in enumerate(keys)
    ]
    return LLMRouter(providers, cache)
