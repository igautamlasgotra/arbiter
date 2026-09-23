# MASTER PROJECT RESET & PLANNING PROMPT — ADAPTIVE MULTI-AGENT AI RESEARCH PROJECT

## IMPORTANT: PROJECT RESET

Forget and ignore ALL previous project discussions, plans, architecture, code, repository assumptions, technology decisions, scope decisions, database ideas, UI ideas, and implementation instructions related to the previous project **VYAPARI / retail management / inventory / billing**.

That previous project is no longer the project to plan or build.

This document is now the authoritative project context.

**DO NOT IMPLEMENT ANYTHING YET.**
Do not create the application, do not create production code, do not install dependencies, do not initialize repositories/services, do not create cloud resources, and do not start building screens.

Your task in this phase is to perform a full research-grade analysis, literature review, architecture design, research-gap analysis, experiment design, implementation roadmap, and deployment plan. Wait for explicit approval before implementation.

---

# 1. PROJECT / COURSE CONTEXT

Project type:
- 7th Semester B.Tech CSE Project
- 4 credits
- Shri Mata Vaishno Devi University (SMVDU), Katra

Students:
- Gautam Lasgotra — 23BCS032
- Chirag Attri — 23BCS024
- Aniket Kundal — 23BCS015

Project mentor:
- Faculty mentor at SMVDU / SoCSE

IMPORTANT: The project must genuinely justify work by all three students. It must not be a single-person project with two nominal contributors.

Timeline:
- Current planning date: 22 September 2026
- INTERNAL 50% completion target: 10 October 2026
- Mid-sem evaluation: 19–21 October 2026
- INTERNAL 100% completion target: 10 November 2026
- Final evaluation: 23–27 November 2026

The internal targets are strict. We want a comfortable buffer before the formal evaluations.

---

# 2. WHY THE PROJECT IDEA CHANGED

The previous project was a smartphone-based retail management / inventory / billing system. During mentor review, an important question was raised: whether a 3-person B.Tech project was genuinely justified if much of the functionality already existed in established commercial products.

The team reviewed existing solutions and decided not to spend a semester reproducing an already crowded product category.

The mentor then suggested changing direction toward:

- studying Agentic AI / AI Agents
- understanding how agents are built
- understanding how agents collaborate
- designing systems in which one agent produces work, another agent validates/tests/reviews it, feedback is returned to the first agent, and the process repeats until the output satisfies acceptance criteria
- allowing more than two agents where task complexity requires it
- making research the primary objective rather than merely building a conventional application
- referring to and studying research papers
- preferably identifying a research problem / contribution that is not simply a clone of an existing paper or framework
- potentially publishing a research paper if the results are sufficiently novel and rigorous

The mentor's calculator example is only an intuition for the architecture. It is NOT the final project scope and the project must NOT become a hard-coded calculator demo.

---

# 3. CORE PROJECT VISION

The project should investigate and implement an **adaptive multi-agent system for iterative task generation, validation, feedback, refinement, and finalization**.

The central idea is:

User gives a task at runtime.

The system analyzes the task.

The system decides what kind of work is required and what validation is appropriate.

One or more specialized LLM agents perform the work.

Other agents and/or tools independently validate the work.

Validation feedback is returned to the relevant agent(s).

The system refines the solution.

The system can repeat the process for multiple iterations.

The system terminates when:
- acceptance criteria are satisfied, OR
- the solution converges / no meaningful improvement occurs, OR
- a maximum iteration / budget limit is reached, OR
- the system determines that further agent creation is not beneficial.

The final result is returned to the user together with an execution trace / provenance showing how the solution was produced and validated.

The system MUST accept previously unseen runtime tasks. It must NOT depend on a collection of pre-written task-specific programs such as `if task == calculator`.

---

# 4. IMPORTANT RESEARCH POSITIONING

We must NOT claim that multi-agent collaboration itself is new.

Relevant existing work includes, at minimum:
- AgentCoder — multi-agent code generation with programmer, test designer and test executor, using iterative testing and feedback.
- Self-Refine — iterative generation, feedback and refinement.
- Reflexion — language agents that use verbal feedback and episodic reflection/memory.
- AutoGen and successor frameworks — multi-agent orchestration.
- ChatDev / MetaGPT — role-specialized agent collaboration for software work.
- Recent research on adaptive workflows, dynamic agent selection, adaptive verification, and dynamic agent spawning.

These papers/frameworks must be treated as baselines and prior art, not as inventions by the project team.

The main research task is to identify a defensible gap after studying the literature.

Potential direction to investigate (NOT to assume as already novel):

> **Adaptive task-specific workflow construction and validation**: instead of always using a fixed set of agents, the system dynamically decides which agent roles are required, how many agents are useful, what validation mechanism should be used, and when to create/remove/escalate agents, while measuring the trade-off between correctness, latency, token usage and cost.

This is a research hypothesis, not a novelty claim. Validate it against recent literature before finalizing the problem statement.

Possible research questions:

RQ1. Does multi-agent iterative refinement improve final task correctness relative to a single-agent baseline?

RQ2. Does task-specific role specialization improve reliability over a fixed multi-agent pipeline?

RQ3. Does dynamic agent selection / creation improve the accuracy-cost-latency trade-off?

RQ4. Does independently generated validation reduce undetected errors?

RQ5. How many refinement iterations are useful before additional iterations become inefficient?

RQ6. Does heterogeneous validation (LLM critic + executable/tool-based checks, where possible) outperform LLM-only validation?

Do not force all questions into the final project. Select only those that are realistically measurable within the semester.

---

# 5. THE SYSTEM MUST BE A REAL LLM SYSTEM

This is non-negotiable.

At runtime:

User enters a new natural-language task.
↓
Actual LLM calls are made.
↓
Agents reason over the task and current state.
↓
Agents produce actual outputs.
↓
Validators/critics inspect those outputs.
↓
Feedback is returned.
↓
Agents refine their work.
↓
Final output is produced.

Do NOT create a demo based on pre-written responses, fixed calculator logic, or task-specific hard-coded flows.

The system should work on multiple task categories, for example:
- code generation / code modification
- SQL / schema generation
- data-analysis tasks
- structured document/report generation
- reasoning/problem-solving tasks

Keep the task space bounded enough to evaluate rigorously. Do not claim universal task solving.

---

# 6. PROPOSED HIGH-LEVEL ARCHITECTURE TO EVALUATE

Start by evaluating this architecture, then improve it if the literature or feasibility analysis suggests a better design.

User Task
  ↓
Task Analyzer / Router
  ↓
Workflow Planner
  ↓
Dynamic Agent Workflow
  ├── Generator / Executor / Builder agent(s)
  ├── Specialist agent(s)
  ├── Test / Evaluation agent(s)
  ├── Critic / Reviewer agent(s)
  └── Tool-based validators where applicable
  ↓
Evidence / Validation Results
  ↓
Decision Agent / Orchestrator
  ├── ACCEPT → Final Output
  ├── REFINE → send feedback to selected agent(s)
  ├── ADD AGENT → create/select another specialist/validator
  ├── REMOVE / SKIP AGENT → reduce unnecessary work
  └── STOP → budget / convergence / failure condition

A key research question is whether the workflow itself should be dynamically constructed rather than fixed.

Do not assume that every task needs the same number of agents.

Example:
- Simple task: Generator → Validator → Final
- Medium task: Planner → Generator → Tester → Reviewer → Final
- Complex task: Planner → multiple specialists → Generator → tool-based tests → critics → refinement → final

---

# 7. VERY IMPORTANT: AGENT INDEPENDENCE

Study whether independent validation should use:
- the same model with a different role prompt,
- the same model with different context,
- a second model/provider,
- deterministic tools/tests,
- or a combination.

Do not simply assume that an agent validating its own output is independent.

Discuss correlated model errors as a research limitation.

Where practical, design experiments that compare:
- same-model reviewer
- different-model reviewer
- tool/execution-based validator
- hybrid validation

---

# 8. RESEARCH METHODOLOGY

The project should not be judged only by whether the final demo produces answers.

It should have controlled experiments.

At minimum, investigate these baselines:

Baseline A — Single Agent
User Task → LLM → Final Output

Baseline B — Fixed Two-Agent Loop
Generator ↔ Validator

Baseline C — Fixed Multi-Agent Pipeline
Planner → Generator → Tester → Reviewer

Proposed System — Adaptive Multi-Agent Workflow
Task Analysis → dynamic agent selection/workflow → iterative refinement → termination

Use a benchmark task set that is fixed before final experiments and not manually tuned to produce positive results.

Measure, as applicable:
- correctness / task success
- test-case pass rate
- validation success rate
- number of iterations
- number of agents used
- number of LLM calls
- token usage
- latency
- estimated API cost
- failure categories
- convergence / non-convergence
- quality of the final artifact

Do not fabricate metrics. The system must log the data needed to calculate them.

---

# 9. TERMINATION AND SAFETY

The orchestration must have explicit stop conditions.

Examples:
- validator PASS
- reviewer ACCEPT
- objective tests pass
- no improvement for N iterations
- maximum iterations reached
- maximum LLM calls reached
- maximum token budget reached
- maximum estimated cost reached
- repeated identical state / cycle detected

The system must never run an unbounded agent loop.

The system must also log every iteration and decision so that the final output is reproducible and explainable.

---

# 10. CODE EXECUTION / TOOL USE

If code generation is part of the benchmark, actual execution/testing is strongly preferred over purely LLM-based claims of correctness.

However, arbitrary generated code must NOT be executed unsafely on a public web server.

Design a sandbox boundary.

Recommended approach to evaluate:
- local development/research runner: isolated Docker/subprocess sandbox with strict CPU, memory and timeout limits
- public deployment: do NOT expose unrestricted arbitrary code execution from the public server unless a genuinely safe isolated execution service is used
- if public safe execution is not feasible within budget/time, the deployed demo can support safe artifact types and/or validation without arbitrary server-side code execution, while the research benchmark runs in a controlled local environment

Do not compromise security merely for a demo.

---

# 11. TECHNOLOGY DIRECTION — MAKE A FINAL DECISION AFTER EVALUATION

Preferred implementation language:
**Python 3.12+**

Reason:
- strongest practical ecosystem for LLM/agent research
- fast iteration
- excellent data/evaluation libraries
- easy API/backend deployment

Application/backend:
**FastAPI**

Data models / validation:
**Pydantic**

Experiment storage:
- local JSONL / SQLite during research
- optional hosted Postgres/Supabase only if persistent cloud experiment logs are truly required

Frontend:
- Keep it intentionally lightweight.
- Prefer a simple web UI served by the same FastAPI application (HTML/CSS/JS) or a very small React/Vite frontend only if the UX benefit clearly justifies it.
- The interface should show the user task, live agent events, iterations, validation results, current state, and final artifact.

Orchestration:
**Prefer a small custom orchestration/state-machine/graph layer for the research core rather than hiding the main contribution inside a large framework.**

Frameworks such as Microsoft Agent Framework / LangGraph may be studied and optionally used where they clearly reduce boilerplate, but the system must keep its orchestration logic understandable and observable. AutoGen should NOT be blindly selected: current Microsoft documentation places AutoGen in maintenance mode and points new projects toward Microsoft Agent Framework.

LLM provider:
**Primary candidate: Google Gemini API, using a current low-cost/free-tier model suitable for agentic workloads.** As of September 2026, Gemini 3.1 Flash-Lite is listed by Google as optimized for high-volume agentic tasks and is shown with free-tier input/output pricing; Gemini 2.5 Flash-Lite is also listed as a cost-efficient low-latency model with a free tier. Verify the exact model and quotas again at implementation time.

IMPORTANT: build a provider abstraction from day one so another provider can be used for experiments or if limits change.

Potential secondary providers for experiments:
- Groq/open-weight models
- OpenRouter/free models

Do not hard-code the architecture to a single provider.

---

# 12. DEPLOYMENT DECISION

Assume the team does not want a paid production cloud deployment for a university project.

Recommended default deployment:
**Render free web service** for the FastAPI web application/API, subject to its current free-plan limitations.

Why:
- straightforward Python/FastAPI deployment
- public HTTPS URL for mentor demonstration
- simple Git-based deployment
- no need for a complicated cloud architecture

Important limitations:
- free compute may be limited/sleeping
- persistent local filesystem must NOT be relied upon
- secrets/API keys must be stored as environment variables
- long-running background jobs should not be assumed on a free web service

Research execution can remain local for reproducible experiments, while the hosted demo exposes the interactive agent workflow.

Alternative to evaluate if Render is unsuitable:
- Hugging Face Spaces for a simple UI/demo
- another free container/web-service provider

Do not use Firebase for this new project unless there is a concrete requirement for it.

---

# 13. UI / DEMO REQUIREMENTS

The live demo should visibly show that real agents are working.

Suggested screen:

1. User task input
2. Start Task button
3. Live execution timeline
4. Agent cards showing:
   - agent role
   - input summary
   - output summary
   - status
   - time
   - iteration
5. Validation results
6. Feedback sent to previous agent
7. Agent added/removed decisions if adaptive mode is used
8. Final result
9. Metrics:
   - agents used
   - iterations
   - LLM calls
   - latency
   - estimated tokens/cost
10. Expandable execution trace for research transparency

Do NOT spend disproportionate time on visual polish. Research functionality and observability come first.

---

# 14. THREE-PERSON WORK DISTRIBUTION

The contribution must be real and defensible.

## Gautam Lasgotra — 23BCS032 — largest workload (~50%)
Lead: system architecture and orchestration

Responsibilities:
- project architecture
- task analyzer/router
- workflow planner
- adaptive agent orchestration
- iteration/termination logic
- workflow state and execution trace
- provider abstraction
- web/API integration
- demo interface and integration
- deployment
- overall integration/testing
- final experimental integration

## Chirag Attri — 23BCS024 — medium workload (~30%)
Lead: agent/LLM pipeline

Responsibilities:
- generator/worker agents
- critic/reviewer agents
- prompt and role design
- structured outputs
- model/provider integration
- agent context packaging
- agent communication contracts
- prompt/version experiments
- selected specialist agents/tools

## Aniket Kundal — 23BCS015 — lighter but genuine workload (~20%)
Lead: evaluation/validation/research measurement

Responsibilities:
- benchmark task dataset
- test/validation specifications
- evaluation runner
- metrics collection
- baseline implementation support
- experiment configuration
- result tables/plots
- error taxonomy
- reproducibility/logging
- literature survey support

All three members must understand the end-to-end system and defend their technical contribution in viva.

Do not describe contribution merely as PPT/report/design work.

---

# 15. TIMELINE / MILESTONES

## Phase 0 — 22–28 Sep
Research & freeze direction

Deliver:
- literature matrix
- research gap candidates
- final problem statement
- research questions
- proposed system architecture
- benchmark/task categories
- evaluation plan
- technology decision

NO production implementation yet.

## Phase 1 — 29 Sep–10 Oct
50% prototype

Target:
- runtime user task input
- real LLM call
- at least two specialized agents
- generation → validation → feedback → refinement loop
- explicit stopping condition
- execution trace
- baseline single-agent mode
- basic logging
- convincing end-to-end demo

The system must already solve unseen runtime tasks within the selected evaluation scope.

## 19–21 Oct
Mid-sem evaluation

Show:
- research motivation
- literature basis
- architecture
- working agent loop
- baseline comparison setup
- initial results
- plan for remaining work

## Phase 2 — 11 Oct–31 Oct
Research-depth implementation

Add as justified:
- adaptive agent selection
- dynamic workflow planning
- heterogeneous validators
- tools / safe execution
- memory/reflection
- budget-aware termination
- additional task categories

## Phase 3 — 1–10 Nov
Final experiments + hardening

Deliver:
- controlled benchmark
- baseline comparisons
- metrics
- ablations where feasible
- final demo
- reproducible experiment logs
- research findings
- architecture documentation

## 23–27 Nov
Final evaluation

Report + demo + viva + research discussion.

---

# 16. REQUIRED LITERATURE REVIEW

At minimum study and summarize:
- AgentCoder: Multi-Agent-based Code Generation with Iterative Testing and Optimisation (2023)
- Self-Refine: Iterative Refinement with Self-Feedback (2023)
- Reflexion: Language Agents with Verbal Reinforcement Learning (2023)
- AutoGen (and its current successor / migration path)
- ChatDev
- MetaGPT
- recent adaptive workflow / dynamic agent selection / adaptive verification / dynamic agent spawning papers from 2025–2026
- at least one recent survey of LLM-based multi-agent systems

For every paper record:
- problem
- architecture
- number/type of agents
- fixed vs dynamic workflow
- feedback mechanism
- memory
- tool use
- benchmark
- metrics
- main result
- limitation
- what is still open

Do NOT claim novelty until this table is complete.

---

# 17. REQUIRED OUTPUT FROM YOU NOW — PLANNING ONLY

Before writing implementation code, produce a complete planning package containing:

1. Executive summary
2. Final proposed project title (3–5 options, then one selected after literature)
3. Problem statement
4. Motivation
5. Why multi-agent rather than single-agent
6. What exactly counts as an agent in this project
7. Definitions: agent, workflow, tool, validator, critic, orchestrator, memory, iteration
8. Literature review matrix
9. Prior-art comparison
10. Research-gap analysis
11. Candidate research questions
12. Final research hypothesis / hypotheses
13. Scope boundaries
14. Task categories for benchmark
15. Proposed benchmark dataset construction method
16. Baselines
17. Proposed architecture
18. Detailed agent roles
19. Agent communication/state model
20. Adaptive workflow logic
21. Refinement loop
22. Validation strategy
23. Tool-use strategy
24. Safe code execution strategy
25. Termination policy
26. Failure handling
27. LLM provider strategy
28. Model selection and why
29. Cost/rate-limit strategy
30. Provider abstraction
31. Backend architecture
32. Frontend/demo architecture
33. Data/logging schema
34. Experiment logging format
35. Evaluation metrics
36. Ablation study plan
37. Threats to validity / limitations
38. Security considerations
39. Deployment plan
40. Local development plan
41. 50% milestone plan by 10 Oct
42. Final milestone plan by 10 Nov
43. Three-person work breakdown
44. Deliverables by student
45. Testing plan
46. Research paper structure
47. Expected results (clearly labelled as hypotheses, NOT fabricated results)
48. Possible publication contribution
49. Risks and fallbacks
50. Final stack recommendation
51. Final repository/folder structure
52. Step-by-step implementation plan for after approval

At the end, provide a section titled:

## FINAL ARCHITECTURE TO APPROVE

It must contain one unambiguous recommended architecture, stack, deployment approach, research scope, and evaluation plan.

---

# 18. HARD RULES

- Do not implement now.
- Do not create application files now.
- Do not install packages now.
- Do not build the UI now.
- Do not initialize cloud services now.
- Do not copy an existing paper's implementation and call it novel.
- Do not claim that multi-agent collaboration itself is novel.
- Do not fabricate benchmark results.
- Do not fabricate API quotas/costs; verify current provider documentation at implementation time.
- Do not build a fixed calculator demo and call it task-agnostic.
- Do not make the project dependent on a single hard-coded task.
- Do not create an unbounded agent loop.
- Do not run arbitrary generated code unsafely on a public server.
- Prefer a simple, observable custom orchestration core over hiding the research contribution behind a large framework.
- Keep the system understandable enough for a B.Tech viva.
- Optimize for research contribution and measurable experiments, not feature count.
- Every major design decision must state: purpose, alternative considered, trade-off, and reason for selection.

---

# 19. IMPORTANT DEVELOPMENT PHILOSOPHY

The end product should be a research prototype that demonstrates:

**A real user task → real LLM agents → dynamic/structured collaboration → validation → feedback → iterative refinement → measurable final result.**

The system should be useful as a research platform, not merely as a one-off demo.

The final contribution may be an architecture, adaptive strategy, evaluation methodology, empirical finding, or combination of these. Do not force a novelty claim before literature review.

WAIT FOR APPROVAL AFTER COMPLETING THE FULL PLANNING PACKAGE.
