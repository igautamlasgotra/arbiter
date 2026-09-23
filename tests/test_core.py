"""Offline tests. No API key, no network, no cost.

Everything here exercises the parts that must be correct for the experiment to
mean anything: budget enforcement, the sandbox, the graded validator, and the
cache key. If these are wrong, every number in the report is wrong.
"""

from __future__ import annotations

import time

import pytest

from arbiter.core.schemas import Family, Task, Verdict
from arbiter.core.state import Budget, RunState, StopReason
from arbiter.llm.base import LLMResponse, Usage
from arbiter.llm.cache import ResponseCache, cache_key
from arbiter.sandbox.runner import run_python
from arbiter.validators.answer_match import normalise, validate_answer
from arbiter.validators.python_exec import strip_fences, validate_code


def make_task(**kw) -> Task:
    base = dict(task_id="t1", family=Family.CODE, prompt="p")
    base.update(kw)
    return Task(**base)


# ---------------------------------------------------------------- budget


def test_budget_stops_on_iterations():
    s = RunState(make_task(), "B", Budget(max_iterations=2))
    assert s.should_stop() is None
    s.iteration = 2
    assert s.should_stop() is StopReason.MAX_ITERATIONS


def test_budget_stops_on_tokens():
    s = RunState(make_task(), "B", Budget(max_tokens=100))
    s.charge(60, 50, cached=False)
    assert s.should_stop() is StopReason.MAX_TOKENS


def test_budget_stops_on_calls():
    s = RunState(make_task(), "B", Budget(max_llm_calls=2))
    s.charge(1, 1, cached=False)
    s.charge(1, 1, cached=False)
    assert s.should_stop() is StopReason.MAX_LLM_CALLS


def test_cached_calls_counted_separately():
    s = RunState(make_task(), "B")
    s.charge(10, 5, cached=True)
    s.charge(10, 5, cached=False)
    assert s.llm_calls == 2 and s.cached_calls == 1
    assert s.tokens_used == 30


def test_no_improvement_triggers_stop():
    s = RunState(make_task(), "B", Budget(no_improvement_patience=2))
    s.note_attempt("a", 0.5)          # improves
    s.note_attempt("b", 0.5)          # stale 1
    s.note_attempt("c", 0.4)          # stale 2
    assert s.should_stop() is StopReason.NO_IMPROVEMENT


def test_repeated_output_is_detected():
    """MAST's most common failure mode: step repetition."""
    s = RunState(make_task(), "B")
    s.note_attempt("same", 0.3)
    s.note_attempt("same", 0.3)
    assert s.stop_reason is StopReason.CYCLE_DETECTED


def test_matched_budget_copies_token_spend():
    b = Budget.matched_to(12_345)
    assert b.max_tokens == 12_345


# ---------------------------------------------------------------- sandbox


def test_sandbox_runs_normal_code():
    r = run_python("print(2 + 2)")
    assert r.ok and "4" in r.stdout


def test_sandbox_kills_infinite_loop():
    started = time.perf_counter()
    r = run_python("while True: pass", timeout=2.0)
    assert r.timed_out and not r.ok
    assert time.perf_counter() - started < 10


def test_sandbox_reports_crash():
    r = run_python("raise ValueError('boom')")
    assert not r.ok and "boom" in r.stderr


def test_sandbox_does_not_leak_parent_env():
    """Generated code must not be able to read our API keys."""
    r = run_python("import os; print(os.environ.get('ARBITER_GEMINI_KEYS', 'ABSENT'))")
    assert "ABSENT" in r.stdout


# ------------------------------------------------------------- validators


def test_strip_fences():
    assert strip_fences("```python\nx = 1\n```") == "x = 1"
    assert strip_fences("x = 1") == "x = 1"


def test_code_validator_all_pass():
    task = make_task(tests="def check_a():\n    assert f(1) == 2\n")
    v = validate_code(task, "def f(x):\n    return x + 1\n")
    assert v.passed and v.score == 1.0 and v.is_objective


def test_code_validator_partial_credit():
    """Graded score is what lets the loop notice improvement."""
    task = make_task(
        tests=(
            "def check_a():\n    assert f(1) == 2\n\n"
            "def check_b():\n    assert f(10) == 100\n"
        )
    )
    v = validate_code(task, "def f(x):\n    return x + 1\n")
    assert not v.passed
    assert v.score == pytest.approx(0.5)
    assert "check_b" in v.evidence["failed"]


def test_code_validator_handles_syntax_error():
    task = make_task(tests="def check_a():\n    assert f(1) == 2\n")
    v = validate_code(task, "def f(x)\n  return x")
    assert not v.passed and v.score == 0.0
    assert "failed to run" in v.detail.lower()


def test_answer_normalisation():
    assert normalise("The answer is 42.") == "42"
    assert normalise("1,250") == "1250"
    assert normalise("$4") == "4"
    assert normalise("7.0") == "7"


def test_answer_validator():
    task = make_task(family=Family.MATH, gold_answer="4")
    assert validate_answer(task, "the answer is 4").passed
    assert not validate_answer(task, "5").passed


# ----------------------------------------------------------------- cache


def test_cache_roundtrip(tmp_path):
    c = ResponseCache(tmp_path, enabled=True)
    key = cache_key(
        provider="gemini", model="m", prompt="hi", system=None, schema=None,
        temperature=0.0, max_output_tokens=10, seed=0,
    )
    assert c.get(key) is None
    c.put(key, LLMResponse(text="hello", usage=Usage(prompt_tokens=3, completion_tokens=2)))
    got = c.get(key)
    assert got is not None and got.text == "hello" and got.cached is True
    assert got.usage.total == 5


def test_cache_key_is_sensitive_to_every_input():
    base = dict(
        provider="gemini", model="m", prompt="p", system=None, schema=None,
        temperature=0.0, max_output_tokens=10, seed=0,
    )
    k = cache_key(**base)
    assert k != cache_key(**{**base, "prompt": "p2"})
    assert k != cache_key(**{**base, "temperature": 0.7})
    assert k != cache_key(**{**base, "seed": 1})
    assert k != cache_key(**{**base, "model": "m2"})


def test_disabled_cache_never_stores(tmp_path):
    c = ResponseCache(tmp_path, enabled=False)
    c.put("k", LLMResponse(text="x"))
    assert c.get("k") is None
