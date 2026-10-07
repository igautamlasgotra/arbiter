"""Tests for the Phase-1 additions: test designer, budget-matched baseline,
metrics, and the web endpoints. All offline - no API key, no cost.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from arbiter.agents.test_designer import (
    InfeasibleTaskError,
    TestPlanError,
    design_tests,
)
from arbiter.bench.metrics import (
    by_condition,
    false_accept_count,
    format_table,
    summarise,
    tokens_per_solve,
)
from arbiter.core.schemas import Family, Task
from arbiter.core.state import RunState
from arbiter.llm.base import LLMResponse, Usage
from arbiter.llm.cache import ResponseCache
from arbiter.llm.mock import MockProvider
from arbiter.llm.router import LLMRouter
from arbiter.orchestrator.baselines import run_single_budget_matched
from arbiter.web.app import app


def router_for(payloads: list[dict]) -> LLMRouter:
    """Router backed by a provider that returns scripted JSON payloads."""

    class Scripted:
        name, model = "scripted", "s1"

        def __init__(self):
            self.i = 0

        def generate(self, prompt, **kw):
            p = payloads[min(self.i, len(payloads) - 1)]
            self.i += 1
            return LLMResponse(
                text=json.dumps(p),
                usage=Usage(prompt_tokens=10, completion_tokens=10),
                model=self.model,
                provider="scripted",
            )

    return LLMRouter([Scripted()], ResponseCache(enabled=False))


def state_for(task: Task) -> RunState:
    return RunState(task=task, condition="test")


# ------------------------------------------------------- test designer


def test_design_tests_happy_path():
    task = Task(task_id="t", family=Family.CODE, prompt="double a number")
    r = router_for([{
        "entry_point": "solve",
        "signature": "def solve(x):",
        "tests": "def check_a():\n    assert solve(2) == 4\n",
    }])
    entry, sig, tests = design_tests(task, r, state_for(task))
    assert entry == "solve" and "check_a" in tests


def test_design_tests_rejects_bad_entry_point():
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{"entry_point": "not a name!", "signature": "", "tests": "def check_a(): pass"}])
    with pytest.raises(TestPlanError):
        design_tests(task, r, state_for(task))


def test_design_tests_rejects_tests_without_checks():
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{"entry_point": "solve", "signature": "", "tests": "x = 1"}])
    with pytest.raises(TestPlanError):
        design_tests(task, r, state_for(task))


def test_design_tests_rejects_filesystem_access():
    """Generated tests have no business touching the disk."""
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{
        "entry_point": "solve",
        "signature": "",
        "tests": "def check_a():\n    open('/etc/passwd')\n    assert solve(1)\n",
    }])
    with pytest.raises(TestPlanError):
        design_tests(task, r, state_for(task))


def test_design_tests_rejects_tests_that_ignore_entry_point():
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{
        "entry_point": "solve",
        "signature": "",
        "tests": "def check_a():\n    assert 1 == 1\n",
    }])
    with pytest.raises(TestPlanError):
        design_tests(task, r, state_for(task))


def test_design_tests_declines_a_task_it_cannot_verify():
    """An app or a UI has no single return value to assert on. Say so."""
    task = Task(task_id="t", family=Family.CODE, prompt="make a sudoku game as a flask app")
    r = router_for([{
        "entry_point": "",
        "signature": "",
        "tests": "",
        "feasible": False,
        "reason": "a web application has no single function to assert on",
    }])
    with pytest.raises(InfeasibleTaskError) as exc:
        design_tests(task, r, state_for(task))
    assert "write a function" in str(exc.value).lower()


def test_design_tests_allows_a_pure_stdlib_import():
    """`import math` is ordinary in a test; the old substring guard refused it."""
    task = Task(task_id="t", family=Family.CODE, prompt="hypotenuse")
    r = router_for([{
        "entry_point": "solve",
        "signature": "def solve(a, b):",
        "tests": "import math\n\ndef check_a():\n    assert solve(3, 4) == math.hypot(3, 4)\n",
    }])
    entry, _, tests = design_tests(task, r, state_for(task))
    assert entry == "solve" and "math.hypot" in tests


def test_design_tests_rejects_a_dangerous_import():
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{
        "entry_point": "solve",
        "signature": "",
        "tests": "import subprocess\n\ndef check_a():\n    assert solve(1)\n",
    }])
    with pytest.raises(TestPlanError):
        design_tests(task, r, state_for(task))


def test_design_tests_allows_the_word_import_inside_a_string():
    """The substring guard rejected tests whose *data* mentioned a banned word."""
    task = Task(task_id="t", family=Family.CODE, prompt="count words")
    r = router_for([{
        "entry_point": "solve",
        "signature": "def solve(s):",
        "tests": "def check_a():\n    assert solve('import os open(') == 3\n",
    }])
    entry, _, _ = design_tests(task, r, state_for(task))
    assert entry == "solve"


def test_design_tests_rejects_unparseable_tests():
    task = Task(task_id="t", family=Family.CODE, prompt="x")
    r = router_for([{
        "entry_point": "solve",
        "signature": "",
        "tests": "def check_a(:\n    assert solve(1)\n",
    }])
    with pytest.raises(TestPlanError) as exc:
        design_tests(task, r, state_for(task))
    assert "valid Python" in str(exc.value)


# -------------------------------------------- budget-matched baseline


def test_budget_matched_respects_token_budget():
    task = Task(task_id="t", family=Family.MATH, prompt="2+2?", gold_answer="4")
    r = router_for([{"content": "4", "reasoning": ""}])
    st = run_single_budget_matched(task, r, token_budget=60, max_samples=8)
    assert st.condition == "A+"
    assert st.tokens_used <= 60 + 20  # may overshoot by at most the last sample


def test_budget_matched_majority_vote_picks_the_common_answer():
    task = Task(task_id="t", family=Family.MATH, prompt="q", gold_answer="7")
    r = router_for([
        {"content": "7", "reasoning": ""},
        {"content": "7", "reasoning": ""},
        {"content": "9", "reasoning": ""},
    ])
    st = run_single_budget_matched(task, r, token_budget=10_000, max_samples=3)
    assert st.best_content.strip() == "7"
    assert st.best_score == 1.0


def test_budget_matched_never_uses_validator_to_choose():
    """A+ must pick before scoring, otherwise the comparison is rigged."""
    task = Task(task_id="t", family=Family.MATH, prompt="q", gold_answer="99")
    # majority is wrong; A+ must still return the majority, scoring 0
    r = router_for([
        {"content": "1", "reasoning": ""},
        {"content": "1", "reasoning": ""},
        {"content": "99", "reasoning": ""},
    ])
    st = run_single_budget_matched(task, r, token_budget=10_000, max_samples=3)
    assert st.best_content.strip() == "1"
    assert st.best_score == 0.0


# ------------------------------------------------------------ metrics


def _run(cond="B", passed=True, tokens=100, score=1.0, family="code", mock=False):
    trace = [{"kind": "validate", "data": {"provider": "mock"} if mock else {}}]
    return {
        "task_id": "x", "condition": cond, "family": family, "passed": passed,
        "best_score": score, "total_tokens": tokens, "llm_calls": 2,
        "iterations": 1, "stop_reason": "accepted", "trace": trace,
    }


def test_summarise_basic():
    s = summarise([_run(passed=True, tokens=100), _run(passed=False, tokens=300, score=0.5)])
    assert s["n"] == 2
    assert s["pass_rate"] == 0.5
    assert s["mean_tokens"] == 200.0


def test_metrics_refuse_mock_runs():
    """A dry run must never be mistaken for a result."""
    assert summarise([_run(mock=True), _run(mock=True)]) == {"n": 0}


def test_false_accept_counted():
    run = {"trace": [
        {"kind": "validate", "data": {"false_accept": True}},
        {"kind": "validate", "data": {"false_accept": False}},
    ]}
    assert false_accept_count(run) == 1


def test_tokens_per_solve():
    s = summarise([_run(passed=True, tokens=100), _run(passed=False, tokens=100, score=0.0)])
    # 2 runs, 200 tokens total, 1 solved -> 200 per solve
    assert tokens_per_solve(s) == 200.0


def test_format_table_handles_no_real_runs():
    assert "No non-mock runs" in format_table(by_condition([_run(mock=True)]))


# ---------------------------------------------------------- web layer


def test_health_endpoint():
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_index_serves_ui():
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200 and "ARBITER" in r.text


def test_icons_are_served_without_shadowing_the_api():
    """The icon route is a single-segment catch-all; check it stays in its lane."""
    c = TestClient(app)
    for path, media in [
        ("/favicon.svg", "image/svg+xml"),
        ("/favicon.ico", "image/x-icon"),
        ("/apple-touch-icon.png", "image/png"),
        ("/site.webmanifest", "application/manifest+json"),
    ]:
        r = c.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith(media), path

    assert c.get("/api/health").json()["ok"] is True
    assert c.get("/nonsense").status_code == 404


def test_run_rejects_unknown_family():
    c = TestClient(app)
    r = c.post("/api/run", json={"task": "x", "family": "nonsense"})
    assert r.status_code == 400


def test_offline_run_streams_to_completion():
    """The whole loop, over HTTP, with no API key."""
    c = TestClient(app)
    with c.stream(
        "POST", "/api/run",
        json={"task": "double a number", "family": "code", "condition": "B", "mock": True},
    ) as resp:
        body = "".join(resp.iter_text())
    assert "event: generate" in body
    assert "event: validate" in body
    assert "event: final" in body


def test_math_run_without_an_expected_answer_is_declined():
    """answer_match has nothing to compare to, so say so instead of failing."""
    c = TestClient(app)
    with c.stream(
        "POST", "/api/run",
        json={"task": "7 pens at 12 rupees, paid 100, change?",
              "family": "math", "condition": "B", "mock": True},
    ) as resp:
        body = "".join(resp.iter_text())
    assert "event: unsupported" in body
    assert "expected answer" in body.lower()


def test_replay_404s_on_missing_trace():
    c = TestClient(app)
    assert c.get("/api/replay", params={"trace": "nope.jsonl"}).status_code == 404


# ------------------------------------------- demo-token gate (public hosting)


def _with_token(token, fn):
    """Re-import the app module so the env var is read at import time."""
    import importlib
    import os

    import arbiter.web.app as web

    old = os.environ.get("ARBITER_DEMO_TOKEN")
    os.environ["ARBITER_DEMO_TOKEN"] = token
    try:
        return fn(importlib.reload(web))
    finally:
        if old is None:
            os.environ.pop("ARBITER_DEMO_TOKEN", None)
        else:
            os.environ["ARBITER_DEMO_TOKEN"] = old
        importlib.reload(web)


def test_live_run_rejected_without_demo_token():
    """A public URL that executes model-written code must not be open."""

    def check(web):
        r = TestClient(web.app).post(
            "/api/run", json={"task": "x", "family": "code", "mock": False}
        )
        assert r.status_code == 401

    _with_token("s3cret", check)


def test_offline_run_allowed_without_demo_token():
    """The gate protects quota and execution, not the demonstration itself."""

    def check(web):
        c = TestClient(web.app)
        with c.stream(
            "POST", "/api/run",
            json={"task": "double a number", "family": "code",
                  "condition": "B", "mock": True},
        ) as resp:
            body = "".join(resp.iter_text())
        assert "event: final" in body

    _with_token("s3cret", check)


def test_health_reports_unauthorised_without_token():
    def check(web):
        h = TestClient(web.app).get("/api/health").json()
        assert h["auth_required"] is True
        assert h["authorised"] is False
        assert h["live_mode_available"] is False

    _with_token("s3cret", check)


# ------------------------------------------------------- mock provider


def test_mock_fails_first_then_succeeds():
    """The offline demo must show the loop working, not a lucky first shot."""
    m = MockProvider()
    first = json.loads(m.generate("double the number x").text)["content"]
    second = json.loads(m.generate("double the number x\nPREVIOUS ATTEMPT failed").text)["content"]
    assert "x + 2" in first
    assert "x * 2" in second
