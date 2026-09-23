"""Gemini provider over the REST API.

Deliberately not using the google-genai SDK. Reasons:
  - exact control over the request body, which the cache key depends on
  - usageMetadata gives us real token counts, which the budget governor needs
  - one less dependency to break; the REST shape is stable
  - Groq / OpenRouter are OpenAI-compatible, so a second provider is a small
    sibling file rather than a second SDK
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from arbiter.llm.base import (
    LLMResponse,
    QuotaExhaustedError,
    RateLimitError,
    TransientError,
    Usage,
)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-flash-lite-latest",
        timeout: float = 60.0,
        label: str = "",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        # label identifies WHICH key this is (gautam/chirag/aniket) in logs,
        # without ever putting the key itself in a log line
        self.label = label or f"{self.name}:{model}"
        self._client = httpx.Client(timeout=timeout)

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
        gen_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if schema is not None:
            # Structured output enforced by schema, not by asking nicely in the
            # prompt. Malformed JSON stops being a failure mode we handle.
            gen_config["responseMimeType"] = "application/json"
            gen_config["responseSchema"] = schema
        if seed is not None:
            gen_config["seed"] = seed

        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{API_ROOT}/{self.model}:generateContent"
        started = time.perf_counter()
        try:
            resp = self._client.post(
                url, json=body, headers={"x-goog-api-key": self.api_key}
            )
        except httpx.TimeoutException as exc:
            raise TransientError(f"{self.label}: timeout") from exc
        except httpx.HTTPError as exc:
            raise TransientError(f"{self.label}: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        if resp.status_code == 429:
            # Gemini returns 429 for both per-minute and per-day exhaustion.
            # The body distinguishes them; getting this wrong means either
            # hammering a dead key or discarding a usable one.
            detail = resp.text.lower()
            if "per day" in detail or "perday" in detail or "quota" in detail:
                raise QuotaExhaustedError(f"{self.label}: daily quota exhausted")
            raise RateLimitError(f"{self.label}: rate limited")
        if resp.status_code >= 500:
            raise TransientError(f"{self.label}: http {resp.status_code}")
        if resp.status_code != 200:
            raise TransientError(f"{self.label}: http {resp.status_code} {resp.text[:200]}")

        data = resp.json()
        candidates = data.get("candidates") or []
        text = ""
        finish = ""
        if candidates:
            finish = candidates[0].get("finishReason", "")
            for part in candidates[0].get("content", {}).get("parts", []):
                text += part.get("text", "")

        um = data.get("usageMetadata", {})
        usage = Usage(
            prompt_tokens=um.get("promptTokenCount", 0),
            completion_tokens=um.get("candidatesTokenCount", 0),
        )

        return LLMResponse(
            text=text,
            usage=usage,
            model=self.model,
            provider=self.label,
            cached=False,
            latency_ms=latency_ms,
            finish_reason=finish,
        )

    def close(self) -> None:
        self._client.close()
