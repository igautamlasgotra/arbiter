"""Offline provider for development, tests and dry-run demos.

This is NOT part of any experimental result. Every run made with it is tagged
`provider="mock"` in the trace, and the metrics module refuses to aggregate
mock runs into a results table. It exists so that:

  - the full loop can be exercised in CI with no API key and no cost
  - the web UI can be demonstrated offline
  - failure paths (bad JSON, timeouts, quota errors) can be tested deliberately,
    which is impossible to do reliably against a live API

It deliberately returns a WRONG first answer and a correct second one, because
a demo in which the first attempt already passes shows nothing about the
refinement loop.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from arbiter.llm.base import LLMResponse, Usage

_ADD = re.compile(r"\badd\b|\bsum\b|plus", re.I)
_DOUBLE = re.compile(r"double|twice|multiply by 2", re.I)
_REVERSE = re.compile(r"revers", re.I)


class MockProvider:
    """Scripted provider. Deterministic, free, offline."""

    name = "mock"

    def __init__(self, model: str = "mock-1", fail_first: bool = True) -> None:
        self.model = model
        self.fail_first = fail_first
        self.calls = 0
        self.label = "mock"

    # -- helpers ---------------------------------------------------------

    def _solution_for(self, prompt: str, attempt: int) -> str:
        """Return plausible code. Attempt 1 is deliberately subtly wrong."""
        wrong = attempt == 1 and self.fail_first

        if _DOUBLE.search(prompt):
            body = "return x + 2" if wrong else "return x * 2"
            return f"def solve(x):\n    {body}\n"
        if _ADD.search(prompt):
            body = "return a - b" if wrong else "return a + b"
            return f"def solve(a, b):\n    {body}\n"
        if _REVERSE.search(prompt):
            body = "return s" if wrong else "return s[::-1]"
            return f"def solve(s):\n    {body}\n"
        # generic fallback
        body = "return None" if wrong else "return True"
        return f"def solve(*args, **kwargs):\n    {body}\n"

    # -- provider API ----------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
        seed: Optional[int] = None,
    ) -> LLMResponse:
        self.calls += 1
        props = (schema or {}).get("properties", {})

        if "entry_point" in props:  # test designer
            payload = {
                "entry_point": "solve",
                "signature": "def solve(x):",
                "tests": (
                    "def check_basic():\n    assert solve(2) == 4\n\n"
                    "def check_zero():\n    assert solve(0) == 0\n"
                ),
                "notes": "mock test plan",
            }
        elif "roles" in props:  # planner
            payload = {
                "difficulty": "medium",
                "roles": ["generator", "repair"],
                "max_iterations": 3,
                "rationale": "mock plan",
            }
        elif "passed" in props and "issues" in props:  # critic
            payload = {"passed": False, "issues": ["mock: unverified edge case"], "suggestion": ""}
        else:  # generator / repair
            attempt = 1 if "PREVIOUS ATTEMPT" not in prompt and "FAILED" not in prompt else 2
            payload = {
                "content": self._solution_for(prompt, attempt),
                "reasoning": f"mock attempt {attempt}",
            }

        text = json.dumps(payload)
        return LLMResponse(
            text=text,
            usage=Usage(prompt_tokens=len(prompt) // 4, completion_tokens=len(text) // 4),
            model=self.model,
            provider="mock",
            cached=False,
            latency_ms=1.0,
            finish_reason="STOP",
        )
