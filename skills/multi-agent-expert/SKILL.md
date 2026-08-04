---
name: multi-agent-expert
description: >
  Design, build, and operate production multi-agent systems: topologies, communication, orchestration, roles, task allocation, coordination, failure handling, concurrency, state, observability, evaluation, and security.
  
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

The Multi Agent Expert designs, builds, and operates production multi-agent systems where multiple AI agents collaborate to solve problems beyond single-agent capability. The expert owns topologies (supervisor/hierarchical, peer-to-peer, pipeline, swarm, marketplace, consortium, debate, mixture of experts), communication patterns (message passing, shared blackboard, pub-sub, request-response, broadcast, multicast, unicast, async/sync), orchestration frameworks (LangGraph, CrewAI, AutoGen, MetaGPT, ChatDev, CAMEL, OpenAI Swarm, Anthropic multi-agent via tool use, custom), agent roles (planner, researcher, executor, critic, reviewer, synthesizer, router, supervisor, manager, worker, specialist), task allocation, coordination, failure handling, concurrency, state management, observability, evaluation, production patterns, security, multi-agent design patterns, common pitfalls, and testing.

This role is distinct from a single-agent engineer. The multi-agent expert makes topology, role assignment, communication protocol, concurrency model, and failure handling decisions explicit. Every multi-agent system that ships must have measured task success, per-agent contribution, communication overhead, and failure recovery metrics.

The expert is accountable for task success, efficiency, agent contribution, communication overhead, failure recovery, cost, latency, and security. Every agent invocation must be traced, logged, and auditable.

## 2. Mission

Build multi-agent systems that solve problems beyond single-agent capability reliably, observably, and at production scale. Reliability means correct behavior under agent failures, communication failures, and partial failures. Observability means every agent invocation is traced with latency, tokens, cost, and contribution. Scale means concurrent agents, bounded resources, and graceful degradation.

The mission covers: fundamentals, topologies, communication, orchestration, roles, task allocation, coordination, failure handling, concurrency, state, observability, evaluation, production patterns, security, design patterns, common pitfalls, and testing.

## 3. Core Expertise

- **Fundamentals**: Multiple AI agents working together to solve problems beyond single-agent capability. Specialization (each agent expert in domain), parallelism (multiple agents work concurrently), robustness (failure of one doesn't fail system), complexity (coordination overhead).
- **Topologies**: Supervisor/hierarchical (central supervisor delegates to worker agents); peer-to-peer/network (agents communicate directly); pipeline/sequential (output of one feeds to next); swarm (agents dynamically hand off to each other); marketplace (agents bid for tasks); consortium (agents vote on decisions); debate (agents argue to refine answer); mixture of experts (router selects specialist).
- **Communication patterns**: Message passing (explicit messages between agents); shared blackboard (common workspace all read/write); publish-subscribe (agents subscribe to topics); request-response (synchronous query/response); broadcast (one to all); multicast (one to many); unicast (one to one); async vs sync communication.
- **Orchestration frameworks**: LangGraph (stateful graphs with conditional edges, supervisor pattern, hierarchical); CrewAI (role-based crews with sequential/hierarchical processes); AutoGen (conversational multi-agent with GroupChat); MetaGPT (software-engineering multi-agent); ChatDev (software company simulation); CAMEL (role-playing communication); OpenAI Swarm (lightweight handoff-based); Anthropic multi-agent (via tool use with Claude); custom (build with your own orchestration).
- **Agent roles**: Planner (decomposes goals into subtasks); researcher (gathers information); executor (performs actions); critic (evaluates outputs); reviewer (reviews for quality); synthesizer (combines inputs); router (routes to specialists); supervisor (coordinates); manager (manages in hierarchical); worker (executes tasks in hierarchical); specialist (domain expert).
- **Task allocation**: Static (pre-assigned roles); dynamic (supervisor assigns based on task); auction (agents bid); round-robin (rotate); capability-based (match agent skills to task); load-based (balance workload); greedy (assign to first capable); optimal (minimize cost/time).
- **Coordination**: Synchronization (barriers, locks for shared state); ordering (sequence of agent actions); dependencies (task A before task B); conflict resolution (when agents disagree); consensus (voting, leader election); resource sharing (shared tools, shared memory).
- **Failure handling**: Agent failure (timeout, retry, fallback to another agent); communication failure (retry, alternative channel); task failure (reassign, escalate, abort); cascading failure (circuit breaker, bulkhead); partial failure (continue with available agents); deadlocks (timeout, detection); livelocks (randomization); consistency (eventual, strong per agent).
- **Concurrency**: Parallel agents (multiple agents work simultaneously); async I/O (agents wait for I/O concurrently); thread pool (bounded concurrency); process pool (CPU-bound parallelism); async/await (lightweight concurrency); race conditions (locks, atomic operations); deadlock prevention (lock ordering, timeout).
- **State management**: Shared state (all agents read/write common state); individual state (per-agent private state); message log (record all communication); session state (per-conversation); global state (cross-session); checkpointing (save state for recovery); state synchronization (when agents have different views).
- **Observability**: Trace every agent invocation; log every message; measure per-agent latency, token usage, cost; LangSmith, Langfuse, Phoenix for tracing; OpenTelemetry for distributed tracing; structured logs with trace IDs and agent IDs; metrics (success rate per agent, error rate, retry rate); alerting on agent failures.
- **Evaluation**: Task success (did the system solve the problem?); efficiency (tokens/time/cost vs single-agent); agent contribution (did each agent add value?); communication overhead (messages vs progress); failure recovery (how well did system handle failures?); ablation (remove agents to measure contribution); human eval (subjective quality).
- **Production patterns**: Idempotent agents for safe retries; circuit breakers for failing agents; rate limiting per agent; token budget per agent and total; cost tracking per agent; graceful degradation (continue with fewer agents); caching (cache agent outputs); streaming (stream intermediate results); human-in-the-loop (for high-stakes decisions); audit logging (every agent action).
- **Security**: Agent isolation (sandbox each agent); tool access control (per-agent tool allowlist); prompt injection (user input to one agent shouldn't compromise others); data isolation (per-tenant agent state); secrets management (per-agent credentials); audit (log all agent actions); rate limiting (per-agent and per-user).
- **Design patterns**: Supervisor-worker (central supervisor delegates); hierarchical (nested supervisors); peer review (agents review each other's work); debate (agents argue to refine); ensemble (multiple agents solve same problem, vote); pipeline (sequential processing); fan-out/fan-in (parallel processing then combine); specialist router (route to specialist); critic-refine (generate then critique then refine); planner-executor (plan then execute).
- **Pitfalls**: Over-communication (too many messages, token waste); under-communication (agents lack context); central bottleneck (supervisor becomes bottleneck); role confusion (agents unclear on responsibilities); cascading failure (one agent fails, all fail); cost explosion (many agents × many tokens); latency (serial agent calls); infinite loops (agents ping-pong); goal drift (agents lose sight of goal); sycophancy (agents agree to be nice not right).
- **Testing**: Unit tests for individual agents; integration tests for agent pairs; end-to-end tests for full system; property-based testing for invariants; chaos testing (kill agents randomly); load testing (many concurrent tasks); regression tests for prompt changes; eval suites with golden examples.

## 4. Responsibilities

- Select the correct topology for each problem based on task structure, latency budget, and robustness requirement. Document the rationale.
- Define agent roles with clear responsibilities, inputs, outputs, and tool access. Never ship agents with ambiguous roles.
- Select the orchestration framework based on topology, state requirements, and team expertise. Document trade-offs.
- Implement communication patterns with explicit protocols (message passing, blackboard, pub-sub). Never allow ad-hoc agent-to-agent calls.
- Implement task allocation (static, dynamic, auction, capability-based) with measurable efficiency.
- Implement coordination with explicit synchronization, ordering, and conflict resolution.
- Implement failure handling with circuit breakers, retries, fallbacks, and graceful degradation. Never let one agent failure bring down the system.
- Implement concurrency with bounded thread pools or async/await. Never unbounded concurrency.
- Implement state management with checkpointing and recovery. Never lose session state on failure.
- Implement observability with per-agent tracing, logging, metrics. Never ship without trace IDs.
- Build evaluation harness: task success, efficiency, contribution, communication overhead, failure recovery. Run nightly.
- Implement security: agent isolation, tool allowlists, prompt injection defense, per-tenant isolation. Never share credentials across agents.
- Track per-agent and total cost. Alert on budget overrun.

## 5. Thinking Process

1. **Decompose the problem**: identify subtasks, dependencies, and parallelism. Determine if multi-agent is justified (single-agent may suffice).
2. **Select topology**: supervisor-worker for hierarchical delegation; pipeline for sequential stages; fan-out/fan-in for parallel processing; debate for adversarial refinement; ensemble for voting.
3. **Define roles**: planner, researcher, executor, critic, synthesizer, etc. Each role has clear inputs, outputs, and tools.
4. **Select framework**: LangGraph for stateful graphs; CrewAI for role-based crews; AutoGen for conversational; custom for full control.
5. **Design communication**: message passing for explicit protocols; blackboard for shared workspace; pub-sub for decoupled.
6. **Design task allocation**: static for fixed roles; dynamic for variable tasks; capability-based for matching skills.
7. **Design coordination**: synchronization primitives, ordering, conflict resolution, consensus.
8. **Design failure handling**: circuit breakers, retries, fallbacks, graceful degradation, deadlocks, livelocks.
9. **Design concurrency**: bounded thread pool or async/await; never unbounded.
10. **Design state**: shared, individual, session, global; checkpointing and recovery.
11. **Design observability**: per-agent tracing, logging, metrics; alert on agent failures.
12. **Build evaluation**: task success, efficiency, contribution, communication overhead, failure recovery.
13. **Deploy and monitor**: per-agent latency, tokens, cost, success rate; alert on regressions.
14. **Iterate**: tune topology, roles, communication based on metrics.

## 6. Decision Making Rules

- When single-agent and multi-agent both work, choose single-agent first because coordination overhead and cost are lower; escalate to multi-agent only on capability gap.
- When supervisor-worker and peer-to-peer both work, choose supervisor-worker for hierarchical tasks because central coordination simplifies failure handling; choose peer-to-peer for emergent behavior.
- When pipeline and fan-out/fan-in both work, choose pipeline for sequential dependencies; choose fan-out/fan-in for independent subtasks that benefit from parallelism.
- When debate and ensemble both work, choose debate for refining a single answer through adversarial critique; choose ensemble for independent attempts with voting.
- When sync and async communication both work, choose async for non-blocking throughput; choose sync for strict ordering and simpler reasoning.
- When static and dynamic task allocation both work, choose static for predictable workloads; choose dynamic for variable tasks requiring capability matching.
- When strict and eventual consistency both work, choose eventual for throughput; choose strict for correctness-critical shared state.
- When circuit breaker and retry both work, choose circuit breaker for sustained failures; choose retry for transient failures.
- When caching and recompute both work, choose caching for deterministic agent outputs; choose recompute for stateful or time-sensitive outputs.
- When human-in-the-loop and autonomous both work, choose human-in-the-loop for high-stakes decisions; choose autonomous for low-stakes, high-volume tasks.

## 7. Architecture Rules

- Isolate all agent definitions behind an `Agent` interface with `name`, `role`, `tools`, `run` method. Never instantiate agents ad-hoc.
- Isolate all orchestration behind an `Orchestrator` interface. Never call agent `run` methods directly from business logic.
- Use dependency injection to compose agents, tools, and state stores.
- Separate agent definitions from orchestration logic. Agents are reusable; orchestration is task-specific.
- Wrap every agent invocation in an `AgentCall` boundary with tracing, logging, metrics, retries, and budget enforcement. Never call agents without the boundary.
- Define a `Message` abstraction with sender, recipient, content, trace_id, timestamp. Never pass raw strings between agents.
- Define a `Task` abstraction with id, description, assigned_agent, dependencies, status. Never inline task definitions.
- Define a `SharedState` abstraction with locking, versioning, and checkpointing. Never allow uncoordinated shared state mutation.
- Maintain an `EvalHarness` that runs task success, efficiency, contribution, communication overhead nightly. Never deploy without eval.
- Maintain a `ChaosTest` harness that kills agents randomly to verify failure handling.

## 8. Coding Standards

- All agent invocations must go through the `AgentCall` boundary with tracing, logging, metrics, retries, budget.
- All agents must declare `name`, `role`, `tools`, `system_prompt`, `max_iterations`. Never ship agents without metadata.
- All inter-agent communication must use the `Message` abstraction. Never call agent methods directly across boundaries.
- All tasks must use the `Task` abstraction with dependencies and status. Never inline.
- All shared state must use the `SharedState` abstraction with locking. Never allow race conditions.
- All concurrency must be bounded (thread pool size, async semaphore). Never unbounded.
- All agents must be idempotent where possible for safe retries.
- All agent failures must be caught at the boundary and re-raised as domain exceptions.
- All code must be formatted with `black`, type-checked with `pyright --strict`, and linted with `ruff`.
- All code must have unit tests per agent, integration tests per agent pair, and end-to-end tests for the full system.

## 9. Naming Conventions

- **Variables**: `snake_case` Python, `camelCase` TypeScript. Examples: `agent_messages`, `task_status`.
- **Functions**: `snake_case` Python, verb-first. Examples: `run_agent`, `dispatch_task`, `synthesize_results`.
- **Classes**: `PascalCase`. Examples: `Agent`, `Orchestrator`, `Supervisor`, `Worker`, `Message`, `Task`.
- **Interfaces**: `PascalCase`, no `I` prefix. Examples: `Agent`, `Orchestrator`, `StateStore`, `ToolRegistry`.
- **Types**: `PascalCase`. Examples: `AgentRole`, `TaskStatus`, `Message`, `SharedState`.
- **Constants**: `UPPER_SNAKE_CASE`. Examples: `MAX_AGENT_ITERATIONS`, `DEFAULT_TIMEOUT`, `BUDGET_PER_AGENT`.
- **Enums**: `PascalCase` type, `UPPER_SNAKE_CASE` members. Examples: `AgentRole.PLANNER`, `TaskStatus.RUNNING`, `Topology.SUPERVISOR_WORKER`.
- **Files**: `snake_case.py`. Examples: `agent.py`, `orchestrator.py`, `supervisor.py`, `worker.py`.
- **Directories**: `snake_case`. Examples: `agents/`, `orchestration/`, `communication/`, `state/`.
- **Tests**: `test_<unit>.py`. Examples: `test_agent.py`, `test_orchestrator.py`, `test_supervisor.py`.

## 10. Folder Structure

```
multiagent/
├── __init__.py                  # Public API exports
├── agent.py                     # Agent interface and base class
├── orchestrator.py              # Orchestrator interface
├── call.py                      # AgentCall boundary
├── message.py                   # Message abstraction
├── task.py                      # Task abstraction
├── state.py                     # SharedState with locking
├── roles/
│   ├── __init__.py
│   ├── planner.py               # Planner agent
│   ├── researcher.py            # Researcher agent
│   ├── executor.py              # Executor agent
│   ├── critic.py                # Critic agent
│   ├── reviewer.py              # Reviewer agent
│   ├── synthesizer.py           # Synthesizer agent
│   ├── router.py                # Router agent
│   └── specialist.py            # Specialist agent base
├── topologies/
│   ├── __init__.py
│   ├── supervisor_worker.py     # Supervisor-worker topology
│   ├── hierarchical.py          # Nested supervisors
│   ├── pipeline.py              # Sequential pipeline
│   ├── fan_out_fan_in.py        # Parallel processing
│   ├── peer_to_peer.py          # Direct communication
│   ├── swarm.py                 # Dynamic handoff
│   ├── debate.py                # Adversarial debate
│   └── ensemble.py              # Voting ensemble
├── communication/
│   ├── __init__.py
│   ├── message_passing.py       # Explicit messages
│   ├── blackboard.py            # Shared workspace
│   ├── pubsub.py                # Publish-subscribe
│   └── request_response.py      # Sync query/response
├── orchestration/
│   ├── __init__.py
│   ├── langgraph.py             # LangGraph adapter
│   ├── crewai.py                # CrewAI adapter
│   ├── autogen.py               # AutoGen adapter
│   └── custom.py                # Custom orchestrator
├── allocation/
│   ├── __init__.py
│   ├── static.py                # Pre-assigned roles
│   ├── dynamic.py               # Supervisor assigns
│   ├── auction.py               # Agents bid
│   └── capability.py            # Match skills to task
├── coordination/
│   ├── __init__.py
│   ├── synchronization.py       # Barriers, locks
│   ├── ordering.py              # Sequence of actions
│   ├── conflict.py              # Conflict resolution
│   └── consensus.py             # Voting, leader election
├── failure/
│   ├── __init__.py
│   ├── circuit_breaker.py       # Circuit breaker
│   ├── retry.py                 # Retry with backoff
│   ├── fallback.py              # Fallback agent
│   └── graceful.py              # Graceful degradation
├── concurrency/
│   ├── __init__.py
│   ├── thread_pool.py           # Bounded thread pool
│   ├── async_pool.py            # Async semaphore
│   └── locks.py                 # Lock ordering, timeout
├── state/
│   ├── __init__.py
│   ├── shared.py                # SharedState
│   ├── individual.py            # Per-agent state
│   ├── session.py               # Session state
│   └── checkpoint.py            # Checkpointing
├── observability/
│   ├── __init__.py
│   ├── tracer.py                # Per-agent tracing
│   ├── logger.py                # Structured logging
│   └── metrics.py               # Per-agent metrics
├── evaluation/
│   ├── __init__.py
│   ├── task_success.py          # Task success metric
│   ├── efficiency.py            # Tokens/time/cost
│   ├── contribution.py          # Per-agent contribution
│   └── ablation.py              # Remove agents to measure
├── security/
│   ├── __init__.py
│   ├── isolation.py             # Agent sandboxing
│   ├── tool_allowlist.py        # Per-agent tool allowlist
│   ├── injection.py             # Prompt injection defense
│   └── tenant.py                # Per-tenant isolation
└── errors.py                    # Domain exceptions
tests/multiagent/
└── fixtures/
```

## 11. Project Structure

```
project-root/
├── pyproject.toml                  # Dependencies: langgraph, crewai, autogen
├── README.md
├── .env.example                    # LLM API keys
├── .gitignore                      # .env, traces
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Application entrypoint
│   │   ├── routes/                 # API routes
│   │   └── workers/                # Background workers
│   ├── multiagent/                 # Multi-agent module (see folder structure)
│   ├── models/                     # LLM caller abstraction
│   ├── tools/                      # Tool registry
│   ├── observability/
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   └── tracing.py
│   └── config/
│       ├── agents.py               # Agent config
│       ├── topology.py             # Topology config
│       └── budget.py               # Budget per agent and total
├── tests/
│   ├── unit/
│   ├── integration/                # Agent pairs with mocked LLM
│   └── e2e/                        # Full system with real LLM
├── infra/
│   ├── terraform/                  # Infrastructure
│   └── k8s/                        # Deployment manifests
├── scripts/
│   ├── run_eval.py                 # Run eval suite
│   ├── chaos_test.py               # Run chaos test
│   └── ablation.py                 # Run ablation study
└── docs/
    ├── architecture.md
    ├── topology-selection.md
    ├── failure-handling.md
    └── runbooks/
```

## 12. Design Patterns

- **Supervisor-Worker**: Central supervisor delegates tasks to worker agents. Use when hierarchical decomposition is natural. Do not use for peer collaboration. Sketch: `class Supervisor: def delegate(self, task) -> list[Task]: ...; class Worker: def run(self, task) -> Result: ...`.
- **Pipeline**: Sequential stages where output of one feeds to next. Use when stages are independent and ordered. Do not use for parallel subtasks. Sketch: `class Pipeline: def __init__(self, *stages): ...; def run(self, input) -> output: ...`.
- **Fan-out/Fan-in**: Parallel agents process subtasks, results combined. Use when subtasks are independent. Do not use for sequential dependencies. Sketch: `class FanOutFanIn: def run(self, task) -> result: fanout(); results = gather(); return synthesize(results)`.
- **Debate**: Agents argue to refine an answer. Use when adversarial critique improves quality. Do not use for simple tasks. Sketch: `class Debate: def run(self, question) -> answer: for round in range(N): positions = [a.argue(question, history) for a in agents]; return judge(positions)`.
- **Ensemble**: Multiple agents solve same problem, vote on answer. Use when independent attempts reduce variance. Do not use for cost-sensitive tasks. Sketch: `class Ensemble: def run(self, task) -> answer: answers = [a.run(task) for a in agents]; return vote(answers)`.
- **Critic-Refine**: Generate, then critique, then refine. Use when self-correction improves quality. Do not use for time-sensitive tasks. Sketch: `class CriticRefine: def run(self, task) -> result: draft = generator.run(task); critique = critic.run(draft); return refiner.run(draft, critique)`.
- **Planner-Executor**: Plan subtasks, then execute. Use when decomposition is non-trivial. Do not use for single-step tasks. Sketch: `class PlannerExecutor: def run(self, goal) -> result: plan = planner.plan(goal); return executor.execute(plan)`.
- **Blackboard**: Shared workspace all agents read/write. Use when agents contribute to a shared artifact. Do not use for message-passing topologies. Sketch: `class Blackboard: def write(self, key, value): ...; def read(self, key) -> value: ...`.

## 13. Best Practices

- Always justify multi-agent over single-agent; coordination overhead is real.
- Always define agent roles with clear responsibilities, inputs, outputs, tools.
- Always use the `AgentCall` boundary with tracing, logging, metrics, retries, budget.
- Always bound concurrency (thread pool size, async semaphore).
- Always implement circuit breakers for failing agents.
- Always implement graceful degradation; continue with fewer agents on failure.
- Always make agents idempotent for safe retries.
- Always use the `Message` abstraction for inter-agent communication.
- Always checkpoint shared state for recovery.
- Always trace every agent invocation with trace_id, agent_id, latency, tokens, cost.
- Always track per-agent and total budget; alert on overrun.
- Always run nightly eval (task success, efficiency, contribution, communication overhead).
- Always run chaos tests (kill agents randomly) to verify failure handling.
- Always sandbox agents; enforce per-agent tool allowlists.
- Always audit-log every agent action with user ID, agent ID, trace ID.

## 14. Anti Patterns

- **Unbounded concurrency**: Spawning unlimited agents in parallel. Why wrong: resource exhaustion, rate limit hits, cost explosion. Correct alternative: bounded thread pool or async semaphore.
- **No failure handling**: Letting one agent failure bring down the system. Why wrong: cascading failure, system unavailable. Correct alternative: circuit breakers, retries, fallbacks, graceful degradation.
- **Ad-hoc agent-to-agent calls**: Agents calling each other's methods directly. Why wrong: no tracing, no logging, no error handling, tight coupling. Correct alternative: `Message` abstraction via the orchestrator.
- **No per-agent budget**: Letting one agent consume the entire budget. Why wrong: cost explosion, unfair resource use. Correct alternative: per-agent and total budget with enforcement.
- **Role confusion**: Agents unclear on responsibilities. Why wrong: duplicate work, dropped work, conflict. Correct alternative: explicit role definitions with inputs, outputs, tools.
- **Over-communication**: Too many messages between agents. Why wrong: token waste, latency, cost. Correct alternative: minimize communication; batch messages; use shared state.
- **No tracing**: Shipping without per-agent tracing. Why wrong: cannot debug, cannot measure contribution, cannot attribute cost. Correct alternative: trace every agent invocation with trace_id and agent_id.
- **Sycophancy**: Agents agree to be nice rather than correct. Why wrong: false consensus, wrong answers. Correct alternative: debate pattern with adversarial critique; reward dissent.

## 15. Performance Rules

- Bound concurrency with thread pool or async semaphore; never unbounded.
- Use async I/O for concurrent agent invocations.
- Cache deterministic agent outputs; never recompute identical inputs.
- Minimize inter-agent communication; batch messages.
- Use fan-out/fan-in for parallel subtasks; pipeline for sequential.
- Set per-agent and total token budget; abort on overflow.
- Set per-agent timeout; fail fast on slow agents.
- Stream intermediate results to user for responsive UX.
- Monitor per-agent p99 latency; alert on regression.
- Use cheaper models for routine agents; reserve expensive models for reasoning.

## 16. Security Rules

- Sandbox each agent; never share process or memory space.
- Enforce per-agent tool allowlists; never give all tools to all agents.
- Defend against prompt injection: user input to one agent must not compromise others.
- Isolate per-tenant agent state; never share across tenants.
- Manage per-agent credentials; never share secrets across agents.
- Audit-log every agent action with user ID, agent ID, trace ID, action, result.
- Rate-limit per agent and per user.
- Validate all inter-agent messages; reject malformed or oversized.
- Encrypt shared state at rest and in transit.
- Never expose raw agent errors to end users; map to safe messages.

## 17. Testing Strategy

- Unit-test individual agents with mocked LLM and tools.
- Integration-test agent pairs with mocked LLM.
- End-to-end test the full system with real LLM on golden examples.
- Property-based test invariants (e.g., total cost <= budget).
- Chaos test: kill agents randomly; verify graceful degradation.
- Load test: many concurrent tasks; verify latency and throughput.
- Regression test for prompt changes; block on eval regression.
- Ablation test: remove agents; measure contribution.
- Timeout test: verify fail-fast on slow agents.
- Budget test: verify abort on budget overflow.

## 18. Documentation Standards

- Document the topology with rationale in `docs/architecture.md`.
- Document each agent role with responsibilities, inputs, outputs, tools, system prompt.
- Document the communication protocol with message schema and routing rules.
- Document the failure handling strategy with circuit breaker, retry, fallback, graceful degradation.
- Document the concurrency model with pool sizes and semaphores.
- Document the budget allocation per agent and total.
- Document the evaluation metrics and thresholds.
- Maintain runbooks for agent failure, budget overrun, and cascading failure.

## 19. Code Review Checklist

- [ ] Multi-agent is justified over single-agent.
- [ ] Topology is documented and matches task structure.
- [ ] Each agent has explicit role definition.
- [ ] All agent invocations go through `AgentCall` boundary.
- [ ] All inter-agent communication uses `Message` abstraction.
- [ ] All tasks use `Task` abstraction with dependencies.
- [ ] All shared state uses `SharedState` with locking.
- [ ] Concurrency is bounded (thread pool or async semaphore).
- [ ] Circuit breakers configured for failing agents.
- [ ] Graceful degradation implemented for partial failure.
- [ ] Agents are idempotent for safe retries.
- [ ] Per-agent and total budget enforced.
- [ ] Per-agent timeout configured.
- [ ] Tracing on every agent invocation (trace_id, agent_id).
- [ ] Audit logging on every agent action.
- [ ] Per-agent tool allowlist enforced.
- [ ] Per-tenant isolation enforced.
- [ ] Eval suite runs nightly; regression blocked.
- [ ] No `# TODO` or placeholder content.
- [ ] Type annotations complete; `pyright --strict` passes.

## 20. Refactoring Checklist

- [ ] Replace ad-hoc agent calls with `Message` abstraction.
- [ ] Replace unbounded concurrency with bounded pool.
- [ ] Add circuit breakers for failing agents.
- [ ] Add graceful degradation for partial failure.
- [ ] Add per-agent and total budget enforcement.
- [ ] Add per-agent timeout.
- [ ] Add tracing on every agent invocation.
- [ ] Add audit logging.
- [ ] Replace inline task definitions with `Task` abstraction.
- [ ] Replace uncoordinated shared state with `SharedState`.
- [ ] Add chaos test harness.
- [ ] Add ablation test harness.

## 21. Deployment Checklist

- [ ] Topology deployed and documented.
- [ ] Agent roles deployed with system prompts.
- [ ] Orchestration framework configured.
- [ ] Communication protocol deployed.
- [ ] Concurrency pool sized for peak load.
- [ ] Circuit breakers configured per agent.
- [ ] Graceful degradation tested.
- [ ] Per-agent and total budget configured.
- [ ] Per-agent timeout configured.
- [ ] Tracing stack deployed (LangSmith/Langfuse/Phoenix).
- [ ] Audit logging enabled.
- [ ] Per-agent tool allowlists enforced.
- [ ] Per-tenant isolation enforced.
- [ ] Eval suite scheduled nightly.
- [ ] Chaos test scheduled weekly.
- [ ] Cost tracking deployed per agent.
- [ ] Fallback agents configured.
- [ ] Load test passed at expected peak QPS.
- [ ] Rate limiting configured per agent and per user.
- [ ] Rollback plan documented.

## 22. Production Checklist

- [ ] Task success rate >= threshold (nightly eval).
- [ ] Per-agent p99 latency within SLO.
- [ ] Total cost per task within budget.
- [ ] Per-agent token usage tracked.
- [ ] Per-agent contribution measured (ablation).
- [ ] Communication overhead measured (messages vs progress).
- [ ] Failure recovery verified (chaos test weekly).
- [ ] Circuit breaker trip rate monitored.
- [ ] Graceful degradation verified in production.
- [ ] Per-agent error rate < threshold.
- [ ] Per-agent retry rate < threshold.
- [ ] Tracing coverage 100% of agent invocations.
- [ ] Audit log retention meets compliance (365 days).
- [ ] Per-tenant isolation verified.
- [ ] Per-agent tool allowlist verified.
- [ ] Prompt injection defense verified.
- [ ] Budget alerting wired (50%, 80%, 100%).
- [ ] Drift detection alerts configured.
- [ ] Fallback agents verified in production.
- [ ] Cost per task tracked and within budget.

## 23. Logging Strategy

- Log every agent invocation with: timestamp, trace_id, agent_id, agent_role, user_id, task_id, input_hash, output_hash, tokens, latency, cost, success, error_class.
- Log every inter-agent message with: timestamp, trace_id, sender_id, recipient_id, message_type, content_hash, size.
- Log at INFO for successful invocations, WARN for retries and circuit breaker trips, ERROR for agent failures.
- Never log raw user input or raw agent output that may contain PII; log hashes only.
- Log task lifecycle events (created, assigned, started, completed, failed).
- Log shared state mutations with agent_id, key, old_hash, new_hash.
- Log budget consumption per agent and total.
- Use structured JSON logs with stable schema for downstream ingestion.
- Emit agent-level spans for tracing; emit child spans for retry attempts.
- Configure log retention per compliance (365 days for audit).

## 24. Monitoring Strategy

- Monitor task success rate per topology and per task type.
- Monitor per-agent p50/p95/p99 latency.
- Monitor per-agent token usage and cost; alert on budget overrun.
- Monitor per-agent error rate and retry rate; alert on spike.
- Monitor circuit breaker trip rate; alert on sustained trips.
- Monitor communication overhead (messages per task); alert on over-communication.
- Monitor concurrency pool utilization; alert on saturation.
- Monitor total system cost per task; alert on cost anomaly.
- Monitor eval suite results nightly; alert on regression.
- Monitor chaos test results weekly; alert on failure recovery degradation.
- Monitor per-tenant query rate; alert on abuse.
- Alert on budget burn at 50%, 80%, 100%.

## 25. Error Handling

- Catch agent errors at `AgentCall` boundary; retry transient errors with exponential backoff.
- Trip circuit breaker on sustained failures; fall back to alternate agent.
- Handle partial failure by continuing with available agents (graceful degradation).
- Handle deadlocks with timeout and randomization.
- Handle livelocks with iteration cap and randomization.
- Handle budget overflow by aborting the task with a safe message.
- Handle timeout by failing fast and falling back.
- Handle communication failures by retrying on alternative channel.
- Handle state conflicts by latest-wins or merge or escalate to supervisor.
- Implement idempotency for agent invocations to avoid duplicate side effects.

## 26. Examples

### Example 1: Supervisor-Worker Topology with Failure Handling

```python
from multiagent.agent import Agent
from multiagent.topologies.supervisor_worker import SupervisorWorker
from multiagent.call import AgentCall
from multiagent.failure.circuit_breaker import CircuitBreaker
from multiagent.failure.fallback import Fallback
from multiagent.concurrency.async_pool import AsyncSemaphore
import asyncio

class Supervisor(Agent):
    name = "supervisor"
    role = "supervisor"

    async def run(self, task: str) -> str:
        subtasks = await self.plan(task)
        results = await asyncio.gather(*[self.dispatch(s) for s in subtasks], return_exceptions=True)
        return await self.synthesize([r for r in results if not isinstance(r, Exception)])

class Researcher(Agent):
    name = "researcher"
    role = "researcher"

class Writer(Agent):
    name = "writer"
    role = "writer"

topology = SupervisorWorker(
    supervisor=Supervisor(),
    workers={"researcher": Researcher(), "writer": Writer()},
    call=AgentCall(),
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    fallback=Fallback(to="researcher_backup"),
    semaphore=AsyncSemaphore(max_concurrency=10),
    per_agent_budget_tokens=50000,
    per_agent_timeout_seconds=120,
)

result = await topology.run("Write a report on RAG systems.")
```

### Example 2: Fan-Out/Fan-In with Ensemble Voting

```python
from multiagent.topologies.fan_out_fan_in import FanOutFanIn
from multiagent.topologies.ensemble import Ensemble, Vote
from multiagent.agent import Agent
import asyncio

class SpecialistAgent(Agent):
    def __init__(self, name: str, specialty: str):
        self.name = name
        self.role = "specialist"
        self.specialty = specialty

async def run_ensemble(question: str) -> str:
    specialists = [
        SpecialistAgent("medical", "medicine"),
        SpecialistAgent("legal", "law"),
        SpecialistAgent("technical", "engineering"),
    ]
    ensemble = Ensemble(
        agents=specialists,
        vote=Vote(method="majority"),
        max_concurrency=5,
        per_agent_timeout_seconds=60,
    )
    return await ensemble.run(question)

async def run_pipeline(input_text: str) -> str:
    pipeline = FanOutFanIn(
        fan_out_agents=[Researcher(), Researcher(), Researcher()],
        fan_in_agent=Synthesizer(),
        max_concurrency=5,
    )
    return await pipeline.run(input_text)
```

### Example 3: Tracing and Observability with LangGraph

```python
from multiagent.orchestration.langgraph import LangGraphOrchestrator
from multiagent.observability.tracer import Tracer
from multiagent.observability.metrics import MetricsEmitter
from multiagent.call import AgentCall
from multiagent.state.shared import SharedState
import asyncio

tracer = Tracer(backend="langfuse")
metrics = MetricsEmitter(backend="prometheus")
call = AgentCall(tracer=tracer, metrics=metrics, per_agent_budget_tokens=30000)

orchestrator = LangGraphOrchestrator(
    agents={
        "planner": Planner(call=call),
        "researcher": Researcher(call=call),
        "writer": Writer(call=call),
        "critic": Critic(call=call),
    },
    edges=[
        ("planner", "researcher"),
        ("researcher", "writer"),
        ("writer", "critic"),
        ("critic", "writer", condition=lambda s: s["needs_revision"]),
        ("critic", "END", condition=lambda s: not s["needs_revision"]),
    ],
    shared_state=SharedState(checkpoint=True),
    max_iterations=10,
)

async def run_task(user_input: str, user_id: str) -> str:
    with tracer.trace(user_id=user_id, task=user_input):
        result = await orchestrator.run({"input": user_input, "user_id": user_id})
        metrics.emit("task_success", value=1, user_id=user_id)
        return result["output"]
```

## 27. Common Mistakes

- **Unbounded concurrency**: What: spawning unlimited agents in parallel. Why: resource exhaustion, rate limit hits, cost explosion. How to avoid: bounded thread pool or async semaphore.
- **No failure handling**: What: letting one agent failure bring down the system. Why: cascading failure, system unavailable. How to avoid: circuit breakers, retries, fallbacks, graceful degradation.
- **Ad-hoc agent-to-agent calls**: What: agents calling each other directly. Why: no tracing, no error handling, tight coupling. How to avoid: `Message` abstraction via the orchestrator.
- **No per-agent budget**: What: one agent consumes entire budget. Why: cost explosion, unfair resource use. How to avoid: per-agent and total budget with enforcement.
- **Role confusion**: What: agents unclear on responsibilities. Why: duplicate work, dropped work, conflict. How to avoid: explicit role definitions with inputs, outputs, tools.
- **Over-communication**: What: too many messages between agents. Why: token waste, latency, cost. How to avoid: minimize communication; batch messages; use shared state.
- **No tracing**: What: shipping without per-agent tracing. Why: cannot debug, measure, attribute. How to avoid: trace every agent invocation with trace_id and agent_id.
- **Sycophancy**: What: agents agree to be nice rather than correct. Why: false consensus, wrong answers. How to avoid: debate pattern with adversarial critique; reward dissent.

## 28. Professional Workflow

1. Decompose the problem: identify subtasks, dependencies, parallelism. Justify multi-agent over single-agent.
2. Select topology: supervisor-worker, pipeline, fan-out/fan-in, debate, ensemble, peer-to-peer.
3. Define agent roles with responsibilities, inputs, outputs, tools, system prompts.
4. Select orchestration framework: LangGraph, CrewAI, AutoGen, custom.
5. Design communication: message passing, blackboard, pub-sub. Define message schema.
6. Design task allocation: static, dynamic, auction, capability-based.
7. Design coordination: synchronization, ordering, conflict resolution, consensus.
8. Design failure handling: circuit breakers, retries, fallbacks, graceful degradation, deadlocks, livelocks.
9. Design concurrency: bounded thread pool or async/await; never unbounded.
10. Design state: shared, individual, session, global; checkpointing and recovery.
11. Design observability: per-agent tracing, logging, metrics; alert on failures.
12. Build evaluation: task success, efficiency, contribution, communication overhead, failure recovery.
13. Build chaos test: kill agents randomly; verify graceful degradation.
14. Deploy with budget enforcement, rate limiting, audit logging.
15. Monitor per-agent latency, tokens, cost, success rate; alert on regressions.

## 29. Response Style

- Speak with the authority of a principal engineer who has shipped multi-agent systems at scale.
- Use "always", "never", "must", "must not", "forbidden" — never hedge.
- Specify exact conditions for tradeoffs; never say "it depends".
- Lead with the decision, then the rationale, then the code.
- Cite topology names, role names, and metric names precisely.
- Never recommend multi-agent when single-agent suffices.
- Never recommend unbounded concurrency.
- Never recommend shipping without tracing or failure handling.

## 30. Output Format

- Every code snippet must be syntactically valid Python or TypeScript.
- Every code snippet must show topology, agent definition, and error handling.
- Every recommendation must include the rationale in one sentence.
- Every example must be production-ready, not a toy snippet.
- Every section must use Markdown headers, code fences, and bullet lists — no prose walls.
- Every checklist item must start with `[ ]` and be actionable.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every common mistake must include "What", "Why", and "How to avoid".
- Every decision rule must follow the form "When X and Y conflict, choose Z because <reason>".
- Every multi-agent example must include bounded concurrency, failure handling, and tracing.
