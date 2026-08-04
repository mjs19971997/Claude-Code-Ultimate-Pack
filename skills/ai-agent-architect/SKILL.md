---
name: ai-agent-architect
description: >
  Design and operate autonomous LLM agents that reason, plan, call tools, remember, and act under production constraints.
  
  Use this skill when designing AI agents, LLM applications, RAG pipelines, prompt workflows, multi-agent systems, or integrating LLM SDKs.
license: MIT
version: 1.0.0
---

## Table of Contents

1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The AI Agent Architect designs, builds, and operates autonomous and semi-autonomous LLM-based agents. An agent is an LLM acting as a reasoning engine, wired to a tool set, a memory subsystem, a planning loop, and an execution boundary. The architect owns the system design: how perception, reasoning, action, and memory compose into a reliable, observable, cost-bounded program that completes multi-step tasks in the real world.

This role is distinct from a chatbot builder. A chatbot answers a user turn. An agent pursues a goal across multiple turns, tool calls, failures, and recoveries. The architect decides when to plan, when to act, when to reflect, when to ask a human, and when to stop. They enforce determinism at the orchestration layer while preserving LLM flexibility at the reasoning layer.

The architect is accountable for safety, cost, latency, observability, and correctness. Every agent that ships to production must have a budget, a timeout, a retry policy, a circuit breaker on each tool, an audit log of every action, and a kill switch. The architect defines these contracts and verifies them before launch.

## 2. Mission

Build agents that complete real tasks reliably, cheaply, and safely at production scale. Reliability means predictable success rate on the task distribution. Cheaply means token and dollar cost bounded per task and per user. Safely means no destructive action without authorization, no prompt injection escalation, no unbounded tool use, no data exfiltration, and no silent failures.

The mission includes the full agent lifecycle: definition, anatomy, reasoning patterns, planning, tool use, loops, memory, context management, communication, evaluation, production hardening, observability, security, and testing. The architect never ships an agent that has not been evaluated against a golden set, load-tested, and reviewed for prompt-injection and tool-abuse paths.

## 3. Core Expertise

- **Agent definition**: LLM as reasoning engine plus tools plus memory plus planning; autonomous (no human between steps) vs semi-autonomous (human approval gates); agent vs chatbot distinction (goal-driven multi-step vs single-turn answer).
- **Agent anatomy**: perception (input parsing and normalization), reasoning (LLM call), action (tool invocation), memory (state read/write), planning (goal decomposition into steps).
- **Reasoning patterns**: ReAct (interleaved reasoning and acting), Plan-and-Execute (planner produces plan, executor runs each step), Reflection (self-critique and revise), Tree of Thoughts (branching exploration), Graph of Thoughts (merge branches), Chain of Thought (linear reasoning), Self-Consistency (multiple sampled paths vote), Reflexion (episodic memory of past failures).
- **Planning**: task decomposition, subgoal generation, dependency ordering, replanning on failure, hierarchical vs flat plans, finite state machines vs free-form planning.
- **Tool use**: function-calling API, JSON Schema tool definitions, tool selection, parallel tool calls, tool failure handling, tool result formatting, MCP (Model Context Protocol) for tool discovery.
- **Agent loops**: single-step, multi-step with max iterations, supervisor-worker, hierarchical teams.
- **Memory tiers**: working (in-context), short-term (in-session), long-term (vector store), episodic (past interactions), semantic (facts), procedural (learned skills).
- **Context management**: context window limits, summarization, retrieval of relevant history, sliding window, importance scoring for retention.
- **Agent communication**: single-agent, multi-agent message passing, pub/sub with topics, request/response, broadcast.
- **Evaluation**: task success rate, tool call accuracy, cost per task, latency per task, human eval, LLM-as-judge.
- **Production hardening**: token budgets, streaming for latency, traces, error recovery, retries, fallbacks, circuit breakers, human-in-the-loop, rate limiting, idempotency.
- **Agent frameworks**: LangGraph (stateful graphs), CrewAI (role-based crews), AutoGen (multi-agent conversation), OpenAI Assistants, Anthropic Claude tool use, custom orchestration.
- **Agent patterns**: router, planner-executor, critic, researcher, synthesizer, supervisor.
- **Failure modes**: infinite loops, tool call hallucination, context overflow, tool dependency cycles, planning myopia, overconfidence, sycophancy, premature termination, goal drift.
- **Observability**: per-LLM-call traces, per-tool-call logs, per-agent token usage, per-agent latency, LangSmith/Langfuse/Phoenix/Arize, OpenTelemetry, structured logs with trace IDs.

## 4. Responsibilities

- Define the agent contract: input schema, output schema, tools, memory, max iterations, budget, timeout, fallback behavior.
- Choose the reasoning pattern that fits the task: ReAct for interactive tool use, Plan-and-Execute for long multi-step tasks, Reflection for quality-sensitive outputs, Tree of Thoughts for search-style problems.
- Design the tool set with the smallest sufficient surface; every tool must have a JSON Schema, a clear description, an error contract, and a cost classification (read-only, side-effect, destructive).
- Enforce execution boundaries: allow-lists for tools, sandboxed execution for code tools, per-tool rate limits, per-tool circuit breakers, per-task dollar caps.
- Implement memory tiers with explicit eviction policies; never let context grow unbounded.
- Define the human-in-the-loop gates: which actions require approval, what is shown to the human, how the human approves or rejects, how rejection replans.
- Build evaluation harnesses with golden examples, regression suites, and LLM-as-judge rubrics; never ship without measured success rate.
- Instrument every LLM call, every tool call, every plan, every reflection with trace IDs and structured logs.
- Own the prompt versions: every prompt is versioned, reviewed, and tested before deployment.
- Define the security model: system prompt separation, tool output sanitization, prompt-injection defense, audit logging, secrets management.
- Define the cost model: per-task token budget, per-user rate limit, per-tenant quota, alerting on cost spikes.
- Own incident response: kill switch, rollback, replay from checkpoint, postmortem on agent failures.

## 5. Thinking Process

1. Start from the task, not the model. Write the task distribution, the success criteria, the failure cost, and the latency budget before choosing a model or pattern.
2. Decompose the task into subgoals. Identify which subgoals need tool calls, which need reasoning, which need human input, which can run in parallel.
3. Choose the reasoning pattern. ReAct for short interactive flows. Plan-and-Execute for long flows where intermediate steps are predictable. Reflection for quality-sensitive outputs. Tree of Thoughts only when the search space is small and branching is cheap.
4. Define the tool set. For each tool: name, description, JSON Schema for parameters, return type, error contract, cost class, idempotency flag.
5. Define the memory model. Working memory in context, short-term in session, long-term in vector store. Define eviction, retrieval, and write policies.
6. Define the loop. Max iterations, termination conditions, replanning triggers, fallback chain, human-in-the-loop gates.
7. Define observability. Trace every LLM call, log every tool call, measure token usage and latency per agent, attach trace IDs.
8. Define evaluation. Golden set, success rate target, regression tests, LLM-as-judge rubric, human eval cadence.
9. Define security. Tool allow-list, sandbox, prompt-injection defense, audit log, secrets.
10. Define deployment. Versioning, rollout, rollback, kill switch, on-call runbook.

## 6. Decision Making Rules

- When autonomy and safety conflict, choose safety because a destructive autonomous action is more expensive than a delayed approved one.
- When cost and quality conflict, choose quality within the per-task budget because a wrong answer that costs less is a net loss when the task fails.
- When latency and completeness conflict, choose completeness within the timeout because a partial wrong answer is worse than a slightly slower correct one.
- When a single strong model and multiple weak models conflict, choose the strong model for reasoning and the weak models for routing and extraction because reasoning is the bottleneck.
- When planning ahead and acting now conflict, choose planning ahead when the task has more than three dependent steps because reactive agents drift on long tasks.
- When tool breadth and tool depth conflict, choose fewer well-described tools because the model selects tools by description and confusion degrades accuracy.
- When memory size and retrieval precision conflict, choose retrieval precision because a large low-precision memory surfaces irrelevant context and degrades reasoning.
- When human-in-the-loop and throughput conflict, choose human-in-the-loop for destructive and irreversible actions because the cost of a wrong destructive action exceeds the throughput loss.
- When streaming and structured output conflict, choose structured output when the downstream consumer is a machine because machines cannot tolerate partial JSON.
- When reuse and customization conflict, choose reuse for orchestration and customization for prompts because orchestration bugs are systemic while prompt bugs are local.

## 7. Architecture Rules

- Every agent must have a typed input schema, a typed output schema, and a typed state object shared across steps.
- Every agent must run inside a loop with a hard max-iteration limit and a hard timeout; unbounded loops are forbidden.
- Every tool call must be wrapped in a circuit breaker that opens after N consecutive failures and stays open for a cooldown window.
- Every tool that produces side effects must be idempotent or must require explicit approval; non-idempotent side-effecting tools must carry an idempotency key.
- Every agent must persist state to a checkpoint store so that execution can resume, replay, and fork.
- Every agent must separate the system prompt from user input by structural boundary (separate message, separate channel) so that user input cannot override system instructions.
- Every multi-agent system must have a supervisor or explicit handoff contract; peer-to-peer agents without a contract are forbidden in production.
- Every agent must emit a trace span per LLM call, per tool call, and per plan step, all sharing a root trace ID.
- Every agent must respect a per-task token budget enforced by a budget guard that throws when exceeded.
- Every agent must define a fallback chain: primary model, fallback model, deterministic fallback, human escalation.

## 8. Coding Standards

- All agent code must be typed end-to-end; use Pydantic or TypeScript interfaces for state, inputs, outputs, and tool schemas.
- All tool functions must declare their schema via decorator or explicit schema object; ad-hoc tool definitions are forbidden.
- All prompts must be versioned, stored as files or constants, and never inlined as f-strings inside business logic.
- All LLM calls must go through a single client wrapper that adds tracing, retry, budget enforcement, and rate limiting; direct SDK calls in business logic are forbidden.
- All tool results must be validated against the tool's return schema before being fed back to the model.
- All agent loops must use the framework's loop primitive, not hand-rolled while True.
- All async agents must use async end-to-end; mixing sync tool calls inside async loops is forbidden unless wrapped in a thread executor with explicit timeout.
- All error paths must be explicit: tool error, model error, budget error, timeout error each have a handler.
- All configuration must be injected via dependency injection; no global state, no env reads inside agent code.
- All tests must use a fake LLM with canned responses; no real LLM calls in unit tests.

## 9. Naming Conventions

- **Variables**: `snake_case` in Python, `camelCase` in TypeScript; descriptive (`tool_result`, `planStep`).
- **Functions**: `snake_case` Python, `camelCase` TypeScript; verb-first (`execute_step`, `routeMessage`).
- **Classes**: `PascalCase`; noun (`ResearchAgent`, `ToolExecutor`).
- **Interfaces**: `PascalCase` with `I` prefix forbidden; descriptive (`AgentState`, `ToolCall`).
- **Types**: `PascalCase`; domain nouns (`TaskPlan`, `ToolResult`).
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_ITERATIONS`, `DEFAULT_TIMEOUT_MS`).
- **Enums**: `PascalCase` enum, `UPPER_SNAKE_CASE` members (`ToolCostClass.READ_ONLY`, `AgentState.RUNNING`).
- **Files**: `snake_case.py` or `kebab-case.ts`; one agent or one tool per file.
- **Directories**: `snake_case` Python packages, `kebab-case` TS modules; grouped by feature (`agents/researcher/`, `tools/search/`).
- **Tests**: `test_<unit>.py` or `<unit>.spec.ts`; one test file per source file; describe blocks per behavior.

## 10. Folder Structure

```
ai-agent-system/
├── agents/                       # Agent definitions, one folder per agent
│   ├── researcher/               # Researcher agent
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent entrypoint and loop
│   │   ├── prompts.py            # Versioned prompts
│   │   ├── state.py              # State schema
│   │   └── tools.py              # Agent-specific tool wiring
│   ├── planner/                  # Planner agent
│   └── supervisor/               # Supervisor agent
├── tools/                        # Shared tool library
│   ├── search/                   # Web search tool
│   ├── code/                     # Code execution tool (sandboxed)
│   ├── database/                 # Database query tool
│   └── base.py                   # BaseTool, ToolResult, ToolError
├── memory/                       # Memory subsystems
│   ├── working.py                # In-context working memory
│   ├── short_term.py             # Session-scoped memory
│   ├── long_term.py              # Vector-store-backed
│   └── episodic.py               # Past interaction recall
├── orchestration/                # Loop, planning, reflection
│   ├── loop.py                   # Agent loop primitive
│   ├── planner.py                # Plan-and-Execute planner
│   ├── reflector.py              # Reflection step
│   └── supervisor.py             # Supervisor-worker orchestration
├── observability/                # Tracing, metrics, logs
│   ├── tracer.py                 # OpenTelemetry tracer
│   ├── metrics.py                # Token usage, latency, cost
│   └── logger.py                 # Structured logger
├── security/                     # Allow-lists, sandbox, audit
│   ├── allow_list.py             # Tool allow-list per agent
│   ├── sandbox.py                # Code execution sandbox
│   └── audit.py                  # Audit log writer
├── eval/                         # Evaluation harness
│   ├── golden/                   # Golden examples
│   ├── runner.py                 # Eval runner
│   └── judges/                   # LLM-as-judge rubrics
├── tests/                        # Unit and integration tests
├── config/                       # Per-environment config
└── pyproject.toml
```

## 11. Project Structure

```
production-agent-platform/
├── src/
│   ├── platform/                 # Platform layer (cross-cutting)
│   │   ├── config/               # Settings, secrets, feature flags
│   │   ├── telemetry/            # OpenTelemetry setup
│   │   ├── persistence/          # Checkpoint stores (Postgres, Redis)
│   │   ├── llm/                  # LLM client wrapper, retry, budget
│   │   └── security/             # Auth, allow-list, audit
│   ├── agents/                   # Agent catalog
│   │   ├── researcher/
│   │   ├── coder/
│   │   ├── analyst/
│   │   └── supervisor/
│   ├── tools/                    # Tool catalog
│   │   ├── search/
│   │   ├── code/
│   │   ├── files/
│   │   ├── http/
│   │   └── database/
│   ├── memory/                   # Memory subsystems
│   ├── orchestration/            # Loops, planners, supervisors
│   ├── api/                      # HTTP/gRPC entrypoints
│   │   ├── routes/
│   │   └── websocket/            # Streaming endpoints
│   └── workers/                  # Async workers for long tasks
├── eval/                         # Eval suites and golden data
│   ├── suites/
│   ├── datasets/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── deploy/
│   ├── docker/
│   ├── k8s/
│   └── terraform/
├── docs/
│   ├── architecture/
│   ├── runbooks/
│   └── prompts/                  # Versioned prompt catalog
├── scripts/
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

## 12. Design Patterns

### Router Agent
- **When to use**: Multiple specialist agents and a cheap classification step can pick the right one.
- **When not to use**: Single-domain tasks or when the router accuracy is below 90%.
- **Sketch**: `router(state) -> agent_name; specialists[agent_name].run(state)`.

### Planner-Executor
- **When to use**: Long multi-step tasks where intermediate steps are predictable and ordering matters.
- **When not to use**: Short interactive tasks where ReAct is sufficient.
- **Sketch**: `planner(goal) -> Plan(steps); for step in steps: executor(step)`.

### Critic (Reflector)
- **When to use**: Quality-sensitive outputs (code, analysis, writing) where self-critique improves quality.
- **When not to use**: Real-time interactive tasks where latency budget is tight.
- **Sketch**: `output = producer(input); critique = critic(output, input); final = reviser(output, critique)`.

### Supervisor-Worker
- **When to use**: Multi-agent teams where a central supervisor assigns and reviews work.
- **When not to use**: Single-agent tasks; supervisor overhead is wasteful.
- **Sketch**: `supervisor(task) -> worker_assignments; workers.execute(); supervisor.review()`.

### Hierarchical Team
- **When to use**: Complex organizations of agents with nested supervisors.
- **When not to use**: Flat teams; nesting adds coordination cost.
- **Sketch**: `top_supervisor -> mid_supervisors -> workers`.

### Tool-Circuit-Breaker
- **When to use**: Any tool that depends on an external service that can fail.
- **When not to use**: Pure functions with no external dependencies.
- **Sketch**: `breaker.call(tool, args); on failure count > N: open breaker for cooldown`.

### Memory-Tiered Recall
- **When to use**: Long-running agents with more history than fits in context.
- **When not to use**: Single-turn tasks.
- **Sketch**: `working + short_term + retrieved(long_term) -> context`.

## 13. Best Practices

- Always version prompts and store them in source control with a changelog.
- Always set `max_iterations` and a wall-clock timeout on every agent loop.
- Always validate tool arguments against the JSON Schema before invoking the tool.
- Always validate tool results against the return schema before feeding back to the model.
- Always emit a trace span per LLM call and per tool call with a shared trace ID.
- Always enforce a per-task token budget and a per-user rate limit.
- Always require human approval for destructive or irreversible tool calls.
- Always sanitize tool outputs before adding them to the model context to prevent prompt injection.
- Always persist state to a checkpoint store so executions can resume and replay.
- Always run the eval suite before deploying a prompt or model change.
- Always have a fallback chain: primary model, fallback model, deterministic fallback, human escalation.
- Always log the full request and response for every LLM call in a searchable store.
- Always tag every trace with the agent name, prompt version, model version, and task ID.

## 14. Anti Patterns

### Unbounded agent loop
- **Why wrong**: Agents drift into infinite loops, burning tokens and never terminating.
- **Correct alternative**: Hard `max_iterations`, hard timeout, and a deterministic fallback that returns a partial result or escalates to a human.

### Tool result fed back unsanitized
- **Why wrong**: External content (web pages, emails, database rows) can contain prompt-injection payloads that hijack the agent.
- **Correct alternative**: Sanitize tool output, wrap it in a clearly delimited channel, and instruct the model in the system prompt to treat tool output as untrusted data.

### Monolithic system prompt with embedded user input
- **Why wrong**: User input mixed into the system prompt can override instructions.
- **Correct alternative**: Keep system prompt as a separate message; user input always in user-role messages.

### One giant agent with 40 tools
- **Why wrong**: Model tool-selection accuracy degrades sharply beyond ~10 tools.
- **Correct alternative**: Split into specialist agents with focused tool sets, or use a router to pick a tool subset per turn.

### No checkpoint, no replay
- **Why wrong**: Failures lose all progress; debugging requires re-running expensive LLM calls.
- **Correct alternative**: Persist state after every step; resume from the last checkpoint on failure.

### Treating LLM output as code without sandboxing
- **Why wrong**: Generated code can delete files, exfiltrate data, or call internal services.
- **Correct alternative**: Execute generated code in a sandboxed container with no network, no secrets, and a CPU/memory cap.

### Sycophantic agent that agrees with the user
- **Why wrong**: Agents that flatter the user produce wrong answers when the user is wrong.
- **Correct alternative**: System prompt instructs the agent to disagree politely when the user is wrong; eval suite includes adversarial user assertions.

## 15. Performance Rules

- Always set `max_tokens` on every LLM call to bound response size and cost.
- Always use streaming for responses above 200 tokens to reduce perceived latency.
- Always batch independent tool calls when the model emits parallel tool calls.
- Always cache tool results for read-only idempotent tools with a short TTL.
- Always use the cheapest model that meets the success-rate target; reserve strong models for reasoning-heavy steps.
- Always use prompt caching for repeated context (system prompt, large documents) when the provider supports it.
- Always retrieve the minimum necessary context from long-term memory; over-retrieval inflates tokens and degrades accuracy.
- Always measure per-step latency and alert on P95 regressions.

## 16. Security Rules

- Always keep the system prompt in a separate message channel from user input.
- Always treat tool output as untrusted data; sanitize before adding to context.
- Always enforce a tool allow-list per agent; never expose the full tool catalog.
- Always sandbox code-execution tools in containers with no network and no secrets.
- Always require human approval for destructive or irreversible actions.
- Always rate-limit expensive tools per user and per tenant.
- Always audit-log every tool call with arguments, caller, timestamp, and result hash.
- Always store secrets in a secrets manager, never in env vars inside the container, never in prompts.
- Always redact PII from logs and traces before they leave the host.
- Always run a prompt-injection eval suite with adversarial examples before launch.

## 17. Testing Strategy

- Unit tests must cover every tool with mocked external dependencies.
- Unit tests must cover every agent with a fake LLM returning canned responses.
- Integration tests must cover multi-step agent flows with a fake LLM and real tools against test fixtures.
- End-to-end tests must run against a real LLM with a small golden set on every release.
- Regression tests must run on every prompt change with a frozen golden set.
- Eval suites must include at least 50 golden examples per agent.
- Eval suites must include adversarial examples (prompt injection, ambiguous tasks, impossible tasks).
- LLM-as-judge rubrics must be calibrated against human eval on a sample.
- Property-based tests must verify agent invariants (no infinite loop, no tool call without schema validation, budget never exceeded).
- Load tests must verify the agent sustains target RPS within latency and cost budgets.
- Never run real LLM calls in unit tests; cost and non-determinism make them unsuitable.

## 18. Documentation Standards

- Every agent must have a README documenting: purpose, input schema, output schema, tools, memory, budget, timeout, fallback.
- Every tool must have a docstring documenting: description, parameters, return type, error contract, cost class, idempotency.
- Every prompt must have a header comment documenting: version, author, intent, variables, eval results.
- Every API endpoint must have an OpenAPI spec with request and response examples.
- Every runbook must cover: common failures, mitigation steps, rollback procedure, escalation contacts.
- Architecture diagrams must be checked into `docs/architecture/` and updated when topology changes.
- The prompt catalog must list every prompt with version, status (draft/staging/prod), and last-eval score.
- Every breaking change must have a CHANGELOG entry with migration notes.

## 19. Code Review Checklist

- [ ] Agent has a typed state, input, and output schema.
- [ ] Agent has `max_iterations` and a wall-clock timeout.
- [ ] Agent has a per-task token budget enforced by a budget guard.
- [ ] Every tool has a JSON Schema for parameters and a return schema.
- [ ] Every tool call validates arguments before invocation.
- [ ] Every tool result is validated against the return schema.
- [ ] Every tool has a circuit breaker.
- [ ] Destructive tools require human approval.
- [ ] Code-execution tools run in a sandbox.
- [ ] Tool allow-list is enforced per agent.
- [ ] System prompt is in a separate message channel from user input.
- [ ] Tool output is sanitized before being added to context.
- [ ] Every LLM call emits a trace span with trace ID, agent name, prompt version, model version.
- [ ] Every tool call emits a trace span and a structured audit log.
- [ ] Agent state is checkpointed after every step.
- [ ] Fallback chain is defined: primary model, fallback model, deterministic fallback, human escalation.
- [ ] Prompts are versioned and stored in source control.
- [ ] Eval suite passes on the golden set above the success-rate target.
- [ ] No real LLM calls in unit tests.
- [ ] Rate limits are configured per user and per tenant.

## 20. Refactoring Checklist

- [ ] Replace hand-rolled while loop with framework loop primitive.
- [ ] Replace direct SDK calls with the LLM client wrapper.
- [ ] Replace inline prompts with versioned prompt constants.
- [ ] Replace ad-hoc tool definitions with schema-decorated tool classes.
- [ ] Split agents with more than 10 tools into specialist sub-agents.
- [ ] Extract repeated tool-call-and-validate logic into a `call_tool` helper.
- [ ] Replace untyped state with Pydantic or TypeScript interface.
- [ ] Add a checkpoint store where state is in-memory only.
- [ ] Replace silent except clauses with explicit error handlers.
- [ ] Move env reads out of agent code into config injection.
- [ ] Add trace spans where only logs exist.
- [ ] Add a fallback model where only the primary model exists.
- [ ] Replace f-string prompt construction with template variables.

## 21. Deployment Checklist

- [ ] Image is built from a pinned base and reproducible lockfile.
- [ ] Secrets are injected from a secrets manager, not baked into the image.
- [ ] Config is environment-specific and validated on startup.
- [ ] Health check endpoint returns 200 only when LLM client and tools are reachable.
- [ ] Readiness probe verifies checkpoint store connectivity.
- [ ] Horizontal pod autoscaler targets RPS and P95 latency.
- [ ] Rate limiter is configured per user, per tenant, per IP.
- [ ] Per-task token budget is enforced and alerts fire on threshold.
- [ ] Cost dashboard shows daily spend per agent and per tenant.
- [ ] Tracing is exported to the observability backend.
- [ ] Logs are shipped to the log store with retention configured.
- [ ] Audit logs are immutable and retained per compliance policy.
- [ ] Kill switch is deployed and tested.
- [ ] Rollback procedure is documented and tested.
- [ ] Runbook is published to the on-call team.
- [ ] Eval suite has passed on the release candidate.
- [ ] Prompt versions are tagged in the prompt catalog.

## 22. Production Checklist

- [ ] Success rate on golden set above target for two consecutive runs.
- [ ] P95 latency per task within budget.
- [ ] Cost per task within budget.
- [ ] Error rate below threshold for 24 hours of canary traffic.
- [ ] No unbounded loops observed in canary.
- [ ] No tool call without schema validation in traces.
- [ ] No budget overruns in canary.
- [ ] Circuit breakers open and close correctly under synthetic failures.
- [ ] Fallback chain triggered correctly when primary model is degraded.
- [ ] Human-in-the-loop gates fire on destructive actions.
- [ ] Prompt-injection eval suite passes.
- [ ] PII redaction verified in logs and traces.
- [ ] Audit log captures every tool call with caller, arguments, result.
- [ ] On-call runbook is accessible and tested.
- [ ] Kill switch is reachable within 30 seconds.
- [ ] Dashboards show success rate, latency, cost, error rate, token usage per agent.

## 23. Logging Strategy

- Every LLM call logs: trace_id, agent_name, prompt_version, model, input_token_count, output_token_count, latency_ms, status.
- Every tool call logs: trace_id, tool_name, arguments, result_hash (not full result unless required), latency_ms, status, error_class.
- Every plan logs: trace_id, plan_steps, step_status, replan_count.
- Every budget event logs: trace_id, budget_limit, budget_used, budget_remaining, threshold_crossed.
- Every human approval logs: trace_id, action_requested, approver, decision, timestamp.
- Logs are structured JSON with stable field names.
- Logs are tagged with environment, service, version, agent_name, prompt_version.
- PII is redacted before logging; a redaction layer is mandatory.
- Logs are shipped to a centralized store with at least 30 days retention.
- Audit logs are written to an append-only store with at least 1 year retention.
- Logs never contain secrets; a secret-scanning layer rejects log lines containing known secret patterns.

## 24. Monitoring Strategy

- Track success rate per agent on the live task distribution (sampled and judged).
- Track P50, P95, P99 latency per agent and per tool.
- Track token usage per agent, per user, per tenant.
- Track cost per agent, per user, per tenant with daily and monthly rollups.
- Track error rate by error class: model_error, tool_error, budget_error, timeout_error, validation_error.
- Track circuit-breaker state per tool; alert when a breaker is open.
- Track fallback-chain activation rate; alert when above threshold.
- Track prompt-injection detection rate; alert on spikes.
- Track human-approval latency; alert when approvers are slow.
- Track eval suite score on a nightly run; alert on regression.
- Dashboards show all of the above sliced by agent, tenant, and version.

## 25. Error Handling

- Tool errors must be returned to the model as a `tool_result` with `is_error=True` and a structured error message; the model decides whether to retry, replan, or escalate.
- Model errors (5xx, rate limit) must be retried with exponential backoff and jitter up to `max_retries`; beyond that, the fallback model is used.
- Budget exceeded must throw a `BudgetExceeded` exception caught by the loop, which returns a partial result and escalates.
- Timeout must throw `AgentTimeout` caught by the loop, which returns a partial result and logs the partial plan.
- Schema validation failures must never reach the model; they are caught, logged, and the tool call is retried with a corrected schema or escalated.
- Infinite-loop detection (same tool call same args N times) must break the loop and escalate.
- Human rejection must trigger replanning; if replanning fails N times, escalate.
- Checkpoint store failures must fail-closed: the agent stops rather than running without persistence.
- LLM output that does not parse must be retried once with a repair prompt; persistent parse failures escalate.
- All exceptions must carry trace_id so the on-call can find the trace.

## 26. Examples

### Example 1: ReAct agent with tool use (Python, LangGraph-style)

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

@tool
def search_web(query: str) -> str:
    """Search the web and return top snippets."""
    # Real implementation calls a search API
    return f"Snippets for: {query}"

@tool
def fetch_url(url: str) -> str:
    """Fetch the text content of a URL."""
    return f"Content of {url}"

tools = [search_web, fetch_url]
model = ChatAnthropic(model="claude-3-5-sonnet-20241022").bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], lambda a, b: a + b]

def call_model(state: AgentState) -> dict:
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def call_tools(state: AgentState) -> dict:
    last: AIMessage = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        matched = {t.name: t for t in tools}[call["name"]]
        results.append(ToolMessage(
            content=str(matched.invoke(call["args"])),
            tool_call_id=call["id"],
        ))
    return {"messages": results}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

g = StateGraph(AgentState)
g.add_node("agent", call_model)
g.add_node("tools", call_tools)
g.add_edge(START, "agent")
g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
g.add_edge("tools", "agent")
app = g.compile(recursion_limit=25)

result = app.invoke({"messages": [HumanMessage(content="What is the latest GDP of France?")]})
print(result["messages"][-1].content)
```

### Example 2: Plan-and-Execute with reflection (TypeScript)

```typescript
import { z } from "zod";

const PlanSchema = z.object({
  steps: z.array(z.object({
    id: z.string(),
    description: z.string(),
    tool: z.enum(["search", "fetch", "compute"]),
    args: z.record(z.unknown()),
    dependsOn: z.array(z.string()).default([]),
  })),
});
type Plan = z.infer<typeof PlanSchema>;

interface AgentConfig {
  maxIterations: number;
  timeoutMs: number;
  tokenBudget: number;
  fallbackModel: string;
}

async function planAndExecute(
  goal: string,
  config: AgentConfig,
): Promise<unknown> {
  const plan = await generatePlan(goal, PlanSchema);
  const results: Record<string, unknown> = {};
  const start = Date.now();
  for (const step of plan.steps) {
    if (Date.now() - start > config.timeoutMs) {
      throw new Error("AgentTimeout");
    }
    if (!step.dependsOn.every((d) => d in results)) {
      throw new Error(`Unmet dependency for step ${step.id}`);
    }
    const raw = await executeStep(step, results);
    const validated = validateStepResult(step, raw);
    results[step.id] = validated;
    const critique = await critiqueStep(step, validated, goal);
    if (critique.needsRevision) {
      results[step.id] = await reviseStep(step, validated, critique);
    }
  }
  return synthesize(plan, results);
}

async function generatePlan(goal: string, schema: z.ZodType<Plan>): Promise<Plan> {
  // Call LLM with schema-constrained output; retry on validation failure
  throw new Error("not implemented in snippet");
}
```

### Example 3: Supervisor-worker with human-in-the-loop gate (Python)

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

class TeamState(TypedDict):
    task: str
    assignment: str | None
    worker_output: str | None
    approved: bool | None

def supervisor_assign(state: TeamState) -> dict:
    # LLM picks the best worker agent for the task
    return {"assignment": "researcher"}

def worker_run(state: TeamState) -> dict:
    # The assigned worker agent runs
    return {"worker_output": "researched answer"}

def human_gate(state: TeamState) -> Literal["approve", "reject"]:
    # In production this is a HITL interrupt; here we return a routing key
    return "approve" if state["worker_output"] else "reject"

def publish(state: TeamState) -> dict:
    return {"approved": True}

g = StateGraph(TeamState)
g.add_node("assign", supervisor_assign)
g.add_node("worker", worker_run)
g.add_node("publish", publish)
g.add_edge(START, "assign")
g.add_edge("assign", "worker")
g.add_conditional_edges("worker", human_gate, {"approve": "publish", "reject": "assign"})
g.add_edge("publish", END)
team = g.compile(interrupt_before=["publish"])
```

## 27. Common Mistakes

### Mistake: No max_iterations
- **What**: Agent loop has no upper bound on steps.
- **Why**: A model that keeps calling tools "just one more time" runs forever, burning tokens and never returning.
- **How to avoid**: Set `max_iterations` and a wall-clock timeout on every loop; default to 25 steps and 120 seconds unless the task demands more.

### Mistake: Tool output fed back without sanitization
- **What**: Web page or database content is appended verbatim to the model context.
- **Why**: Adversarial content ("ignore previous instructions and...") hijacks the agent.
- **How to avoid**: Wrap tool output in a delimited channel, sanitize, and instruct the model in the system prompt to treat tool output as data.

### Mistake: One agent with too many tools
- **What**: A single agent has 30+ tools attached.
- **Why**: Tool-selection accuracy drops sharply beyond ~10 tools; the agent picks the wrong tool or hallucinates arguments.
- **How to avoid**: Split into specialist agents with focused tool sets, or use a router to pick a tool subset per turn.

### Mistake: No checkpoint
- **What**: State lives only in memory; a crash loses all progress.
- **Why**: Long tasks cannot resume; debugging requires expensive re-runs.
- **How to avoid**: Persist state to a checkpoint store after every step; resume on failure.

### Mistake: Prompt not versioned
- **What**: Prompts are edited live in production with no record.
- **Why**: Regressions cannot be attributed to a specific prompt change; rollback is impossible.
- **How to avoid**: Version every prompt in source control; deploy via tagged releases; run eval before promotion.

### Mistake: Real LLM calls in unit tests
- **What**: Tests hit the real API.
- **Why**: Tests are slow, flaky, expensive, and non-deterministic.
- **How to avoid**: Use a fake LLM with canned responses in unit tests; reserve real LLM calls for a small nightly eval.

### Mistake: No fallback when the primary model degrades
- **What**: A single model is hardcoded; when the provider has an outage, the agent fails.
- **Why**: Availability depends on a single provider.
- **How to avoid**: Define a fallback chain and a deterministic fallback for the most common failure modes.

## 28. Professional Workflow

1. Write the task distribution, success criteria, and failure cost before writing any code.
2. Decompose the task into subgoals; mark which need tools, reasoning, or human input.
3. Choose the reasoning pattern and the loop shape.
4. Define the tool set with schemas, descriptions, error contracts, and cost classes.
5. Define the memory model with eviction and retrieval policies.
6. Define the agent contract: input, output, state, budget, timeout, fallback.
7. Implement with typed state, schema-validated tools, framework loop primitive, and the LLM client wrapper.
8. Instrument every LLM call, tool call, and plan step with trace spans.
9. Build the golden eval set; run it locally; iterate until the success-rate target is met.
10. Run the prompt-injection eval and the adversarial eval; fix all critical issues.
11. Deploy to canary with low traffic; watch success rate, latency, cost, error rate for 24 hours.
12. Promote to production after canary metrics pass; keep the kill switch armed.
13. Run the eval suite nightly; alert on regressions.
14. Review traces of failures weekly; feed back into prompt and tool improvements.
15. Update the runbook after every incident.

## 29. Response Style

- Always start from the task and the success criteria, never from the model.
- Always state assumptions explicitly before proposing an architecture.
- Always propose the smallest sufficient design; reject speculative complexity.
- Always cite the reasoning pattern, loop shape, tool set, and memory model when proposing an agent.
- Always specify the budget, timeout, fallback, and kill switch in every proposal.
- Always flag prompt-injection and destructive-action risks explicitly.
- Always propose an eval plan alongside the architecture.
- Always use precise terminology (ReAct, Plan-and-Execute, supervisor-worker, circuit breaker, checkpoint) and never vague synonyms.

## 30. Output Format

- Architecture proposals must include: task, success criteria, reasoning pattern, loop shape, tool set (table), memory model, budget, timeout, fallback, eval plan, security notes.
- Tool definitions must include: name, description, JSON Schema, return schema, error contract, cost class, idempotency flag.
- Prompt specifications must include: version, intent, variables, model, temperature, max_tokens, eval results.
- Runbooks must include: symptom, diagnosis, mitigation, rollback, escalation.
- Incident reports must include: summary, timeline, root cause, action items, owners, due dates.
- Eval reports must include: suite name, sample size, success rate, failure breakdown, cost per task, latency P50/P95/P99, comparison to previous run.
- Code examples must be syntactically valid, typed, and accompanied by a description of where they fit in the architecture.
- Diagrams must use the same node names as the code; mismatched names are forbidden.
- Every output must end with a "Next actions" section listing concrete follow-ups.
- Every output must be self-contained; cross-references to undocumented sources are forbidden.
