"""Provider-agnostic LLM interface.

The whole system talks to this, never to a vendor SDK directly. That is what
makes the different-model-reviewer experiment (brief section 7) possible and
what stops a provider change from touching the research core.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMResponse(BaseModel):
    text: str
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    provider: str = ""
    cached: bool = False
    latency_ms: float = 0.0
    finish_reason: str = ""


class LLMError(Exception):
    """Base for all provider failures."""


class RateLimitError(LLMError):
    """429 / per-minute limit. Retryable after a wait, or rotate the key."""


class QuotaExhaustedError(LLMError):
    """Daily quota gone on this key. Rotate; do not retry this key today."""


class TransientError(LLMError):
    """5xx, timeout, connection reset. Retryable."""


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal surface every provider must implement."""

    name: str
    model: str

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
        ...
