# ARBITER

**Adaptive Role-Based Iterative Task Execution and Refinement**

A research prototype for studying multi-agent LLM refinement: one agent solves a
task, tools and other agents validate the result, feedback goes back, the work is
revised, and the loop repeats under a hard budget until the solution passes or the
system decides to stop.

7th Semester B.Tech CSE project, Shri Mata Vaishno Devi University, Katra.

---

## What this actually studies

Multi-agent refinement is not new, and neither is adaptive orchestration — there
is a published survey of it. This project claims novelty in neither.

What is genuinely unresolved is this: budget-matched studies (Tran & Kiela, 2025)
show that when you hold the token budget equal, a single agent matches or beats
multi-agent systems on reasoning tasks — yet adaptive-orchestration papers report
large gains without ever running that budget-matched comparison, despite compute
efficiency being their entire argument.

**So we run it.** ARBITER compares five conditions under a matched token budget
across three task families chosen to differ in how strong their automatic verifier
is. A negative result is a valid result.

| Condition | Description |
|---|---|
| `A` | Single agent, one shot |
| `A+` | Single agent given the **same token budget** as `D` |
| `B` | Generator ↔ validator loop |
| `C` | Fixed pipeline: generator → critic → repair |
| `D` | Adaptive: a planner chooses roles and iterations per task |

| Family | Verifier | Strength |
|---|---|---|
| Code | executed unit tests | strong (per-test partial credit) |
| SQL | execution-result match | medium (final only) |
| Math | exact answer match | weak (no intermediate signal) |

## How it works

An agent is a role prompt, one LLM call, and a typed parse. Nothing more —
see `arbiter/agents/roles.py`. The orchestrator is a bounded `while` loop over a
state object (`arbiter/orchestrator/loop.py`). Validation for code contains no
LLM at all: it runs the code in a sandboxed subprocess and reports which tests
failed (`arbiter/validators/python_exec.py`). That subprocess is the external
feedback signal the whole refinement loop depends on.

```
Task → Planner → ┌─ Generator ─→ Validators (tools first, critic second) ─┐
                 │        ▲                                               │
                 │     feedback ←──────── Decision policy ────────────────┘
                 └─ accept / refine / add agent / stop (budget-governed)
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then add your API keys
```

Three Gemini keys can be listed in `ARBITER_GEMINI_KEYS`; the router round-robins
them so three free-tier accounts behave like one with triple the daily quota.
`ARBITER_DEMO_KEY` is reserved for the live demo and is never touched by the
experiment runner, so demo-day quota is always fresh.

## Running

```bash
pytest -q                                    # 39 offline tests, no API key needed

# live demo UI  ->  http://127.0.0.1:8000
python -m uvicorn arbiter.web.app:app --reload

# experiments
python -m arbiter.bench.runner --dataset smoke --conditions A B C
python -m arbiter.bench.runner --dataset smoke --conditions D --adaptive
python -m arbiter.bench.runner --dataset smoke --conditions A+     # run D first
python -m arbiter.bench.metrics traces/smoke.jsonl --by-family
```

### The demo

Type any task into the UI and watch the agents work: roles chosen, solution generated, tests
executed, failures fed back, solution revised. For an unseen task the **test-designer agent**
writes the tests first, so the system is not limited to problems it already had answers for.

`Offline demo` runs the whole loop with a scripted provider and no API key - useful for
development and for showing the interface, but runs made this way are tagged `mock` and the
metrics module refuses to aggregate them into results.

If the API is unavailable mid-demo, `/api/replay?trace=smoke.jsonl` re-streams a stored run
with its original timing, clearly labelled as a replay.

The runner is **resumable**: every finished task-run is appended to
`traces/*.jsonl` immediately and skipped on the next invocation. If the daily
quota runs out mid-sweep, rerun the same command after it resets and it continues
where it stopped.

Every metric in the report is computed from those JSONL traces. There is no
separate metrics pipeline.

## Layout

```
arbiter/
├── core/          schemas.py, state.py     ← frozen contracts + budget governor
├── llm/           base, cache, gemini, router
├── agents/        roles.py, test_designer.py ← fixed role library
├── validators/    python_exec, answer_match
├── sandbox/       runner.py                ← isolated subprocess execution
├── orchestrator/  loop.py, planner.py, baselines.py  ← loop + condition A+
├── web/           app.py, templates/       ← FastAPI + SSE live demo
└── bench/         runner.py, metrics.py, datasets/
docs/              plan, brief
tests/
```

## Safety

Generated code runs in a separate process with no inherited environment (so it
cannot read API keys), a temp working directory, and a wall-clock timeout. POSIX
CPU/memory limits are applied where available; Windows lacks them, so final
experiment runs should be done under WSL or Docker. **Arbitrary code execution is
never exposed on the public deployment** — the hosted demo serves the SQL and math
families live and replays stored traces for code tasks.

## Team

| | |
|---|---|
| Gautam Lasgotra (23BCS032) | Orchestration, budget governor, provider layer, API/UI, deployment |
| Chirag Attri (23BCS024) | Agent roles, prompt design, structured outputs, provider integrations |
| Aniket Kundal (23BCS015) | Benchmark datasets, validators, experiment runner, metrics, error taxonomy |
