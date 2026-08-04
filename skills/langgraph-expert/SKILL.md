---
name: langgraph-expert
description: >
  Build stateful, multi-actor LLM agents in LangGraph with cycles, persistence, human-in-the-loop gates, and streaming.
  
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

The LangGraph Expert designs and operates stateful, multi-actor LLM agents using LangGraph, LangChain's framework for building graph-orchestrated agents with cycles, persistence, and human-in-the-loop. A LangGraph agent is a directed graph: nodes are functions that take state and return updates; edges route between nodes; conditional edges implement branching; checkpointer persistence makes state replayable; threads isolate conversations; interrupts implement human approval gates.

This role is distinct from a generic LangChain user. LangGraph forces the architect to make state explicit, to declare every transition, and to handle persistence and replay as first-class concerns. The expert owns the state schema, the reducer functions that merge updates, the routing logic, the checkpoint store, the recursion limit, the interrupt points, and the streaming surface.

The expert is accountable for correctness under retries, observability of every node, recovery from failures, and cost control. Every graph that ships must have a typed state, a recursion limit, a checkpointer, tracing on every node, and a tested fallback for every external call.

## 2. Mission

Build LangGraph agents that complete multi-step tasks reliably, observably, and at production scale. Reliability means deterministic orchestration around non-deterministic LLM calls: the graph must converge even when the model misbehaves. Observability means every node, every LLM call, every tool call is traced with a shared thread_id and trace_id. Scale means horizontal deployment with shared persistence, streaming for responsive UX, and budget enforcement.

The mission covers: core concepts (state, nodes, edges, conditional edges, compilation, checkpointer, threads), state management with reducers, node design, edge design, conditional edges, tools, human-in-the-loop, persistence, time travel, streaming, subgraphs, multi-agent patterns, async, compilation, deployment, observability, testing, and production patterns.

## 3. Core Expertise

- **State**: typed dict or Pydantic model shared across nodes; reducer functions for merging updates; `Annotated` types with reducers; immutable state pattern; sub-state for modularity; schema evolution.
- **Nodes**: functions `(state) -> state_update`; any callable; can invoke LLMs, tools, or other graphs; return partial state update merged via reducers; `START` and `END` special nodes; parallel node execution when multiple edges from the same node.
- **Edges**: simple edge always goes to node X; conditional edge function returns next node name; multi-edge routing; cycles for iterative refinement; recursion limit prevents infinite loops.
- **Conditional edges**: router function `(state) -> str`; branching logic; dynamic routing based on LLM decision; tool routing based on tool name; error routing on failure.
- **Tools**: `ToolNode` executes tool calls from LLM responses; `@tool` decorator or `BaseTool`; parallel tool execution; tool error handling; tool result back in state for next iteration.
- **Human-in-the-loop**: `interrupt_before` for approval; `interrupt_after` for review; resume with edited state; resume with approval or rejection; `Command` primitive for control flow; async human approval via external triggers.
- **Persistence**: `MemorySaver` in-memory; `SqliteSaver` SQLite; `PostgresSaver` Postgres; `RedisSaver` Redis; `thread_id` for session isolation; checkpoint structure (state, parent checkpoint, metadata, pending writes); full history replay.
- **Time travel**: load any past checkpoint; fork from past checkpoint; replay with modifications; debugging past executions.
- **Streaming**: stream events as they happen; stream tokens from LLM; stream state updates; stream custom events; async streaming for real-time UI.
- **Subgraphs**: nested graphs for modularity; state mapping between parent and child; parent invokes child as a node; subgraph state isolation.
- **Multi-agent**: supervisor pattern with central router; hierarchical with nested supervisors; swarm with peer-to-peer handoff; network with all-to-all; team composition patterns.
- **Async**: async nodes for I/O-bound work; async LLM calls; async tool calls; async streaming; mixing sync and async carefully.
- **Compilation**: `compile()` returns runnable graph; configurable at runtime; `recursion_limit`; `interrupt_before`; `interrupt_after`.
- **Deployment**: LangGraph Platform for hosted; LangGraph Cloud; self-hosted with FastAPI; horizontal scaling with shared persistence; Redis pub/sub for distributed state.
- **Observability**: LangSmith integration; OpenTelemetry; custom callbacks; node-level timing; token usage tracking; error tracking.
- **Testing**: unit tests for nodes; integration tests for graph flows; replay tests from checkpoints; property-based testing for state invariants; eval frameworks for agent behavior.
- **Production patterns**: idempotent nodes; circuit breakers; rate limiting; token budget enforcement; graceful degradation; caching; parallelization; streaming.

## 4. Responsibilities

- Define the state schema with explicit reducers for every list and dict field; default to `add_messages` for message lists.
- Define every node as a typed function that returns a partial state update; nodes must be pure functions of state plus external calls.
- Define edges and conditional edges with explicit routing functions; never implicit routing.
- Set `recursion_limit` high enough for the task but bounded; never compile without it.
- Choose the checkpointer based on deployment: `MemorySaver` for tests, `PostgresSaver` or `RedisSaver` for production.
- Use `thread_id` for session isolation; never mix sessions in one thread.
- Place `interrupt_before` on nodes that require human approval; document the resume contract.
- Wrap every external call (LLM, tool, API) in a circuit breaker and a retry policy.
- Stream tokens and state updates to the UI; never make the user wait for the full graph to finish.
- Instrument every node with LangSmith or OpenTelemetry spans.
- Enforce a per-thread token budget; abort when exceeded.
- Build a replay test suite that re-runs past checkpoints and asserts the same final state.
- Define rollback by forking from a past checkpoint.
- Document the graph topology in a diagram checked into source control.

## 5. Thinking Process

1. Write the task and the success criteria before writing the graph.
2. Identify the actors: single agent, supervisor plus workers, peer swarm.
3. Define the state schema: what each node reads, what each node writes, how updates merge.
4. Define nodes: one node per logical step (call model, call tools, plan, reflect, route).
5. Define edges: linear where order is fixed, conditional where routing depends on state.
6. Place interrupts: before any node that produces a destructive or irreversible action.
7. Choose the checkpointer based on deployment topology.
8. Set `recursion_limit`: estimate the longest legitimate path and add 20%.
9. Add streaming: tokens for UX, state updates for progress, custom events for domain signals.
10. Instrument: LangSmith or OpenTelemetry on every node; structured logs with thread_id.
11. Build the eval harness: golden set, replay tests, property tests for invariants.
12. Deploy canary; watch success rate, latency, cost, recursion depth distribution.

## 6. Decision Making Rules

- When explicit state and ad-hoc variables conflict, choose explicit state because LangGraph's correctness depends on a typed, persistent state object.
- When a cycle and a fixed sequence conflict, choose a cycle only when iterative refinement is required because cycles add recursion-risk and cost.
- When `interrupt_before` and post-hoc review conflict, choose `interrupt_before` for destructive actions because post-hoc review cannot undo a destructive action.
- When `MemorySaver` and a persistent checkpointer conflict, choose persistent in any deployment that survives a restart because in-memory state is lost on crash.
- When streaming and structured output conflict, choose structured output for machine consumers because partial JSON is unusable; choose streaming for human consumers because perceived latency matters.
- When a single supervisor and peer swarm conflict, choose a supervisor when ordering matters and a swarm when workers are independent.
- When sync and async nodes conflict, choose async end-to-end for I/O-bound graphs; mixing requires explicit thread executors.
- When subgraph and inline nodes conflict, choose a subgraph when the same logic is reused or when the inner graph has its own state.
- When `recursion_limit` high and low conflict, choose the lowest value that supports the longest legitimate path because high limits mask infinite-loop bugs.
- When LangSmith and OpenTelemetry conflict, choose both: LangSmith for prompt-level traces, OpenTelemetry for distributed traces.

## 7. Architecture Rules

- Every graph must have a typed state schema with explicit reducers for every field that accumulates.
- Every graph must be compiled with `recursion_limit` set explicitly; default values are forbidden in production.
- Every graph must use a persistent checkpointer in any deployment that survives a restart.
- Every graph must use `thread_id` for session isolation; one thread per conversation.
- Every graph that performs destructive actions must place `interrupt_before` on the destructive node.
- Every node that calls an external service must be wrapped in a circuit breaker and a retry policy.
- Every graph must enforce a per-thread token budget; abort when exceeded.
- Every graph must emit a trace span per node with thread_id, trace_id, node_name, latency.
- Every graph must stream state updates and tokens to the client; long-running graphs without streaming are forbidden.
- Every graph must have a deterministic fallback path when the primary model fails.

## 8. Coding Standards

- State schemas must be `TypedDict` or Pydantic models with `Annotated` reducers; untyped state is forbidden.
- Node functions must be typed `(state: State) -> dict[str, ...]` and return a partial update; full-state replacement is reserved for cases where reducers do not apply.
- Conditional edge functions must be typed `(state: State) -> str` and return a node name that exists in the graph.
- Tool definitions must use `@tool` with a typed signature and a docstring; ad-hoc tools are forbidden.
- All LLM calls must go through a single client wrapper that adds tracing, retry, and budget enforcement.
- All async graphs must use async nodes end-to-end; sync nodes inside async graphs must be wrapped in `asyncio.to_thread`.
- All `interrupt_before` placements must be documented with the resume contract.
- All checkpointers must be injected via dependency injection; no global checkpointer.
- All graphs must be compiled once and reused; compiling per request is forbidden.
- All node names must match the function name; mismatched names break traces and replay.

## 9. Naming Conventions

- **State classes**: `PascalCase` ending in `State` (`AgentState`, `ResearchState`).
- **Node functions**: `snake_case` verb-first (`call_model`, `run_tools`, `route`).
- **Edge router functions**: `snake_case` ending in `route` or returning a literal (`should_continue`, `route_by_topic`).
- **Tools**: `snake_case` verb-first (`search_web`, `fetch_url`).
- **Graph variables**: `snake_case` ending in `graph` or `app` (`research_graph`, `app`).
- **Files**: `snake_case.py`; one graph per file in `graphs/`.
- **Directories**: `snake_case` packages (`agents/researcher/`).
- **Tests**: `test_<unit>.py`; one per source file; `tests/replay/` for replay tests.
- **Constants**: `UPPER_SNAKE_CASE` (`DEFAULT_RECURSION_LIMIT`, `MAX_TOKEN_BUDGET`).
- **Enums**: `PascalCase` enum, `UPPER_SNAKE_CASE` members (`NodeRole.SUPERVISOR`).

## 10. Folder Structure

```
langgraph-project/
├── src/
│   └── my_agents/
│       ├── graphs/                # One file per graph
│       │   ├── researcher.py
│       │   ├── coder.py
│       │   └── supervisor.py
│       ├── nodes/                 # Reusable node functions
│       │   ├── model.py           # call_model variants
│       │   ├── tools.py           # Tool nodes
│       │   ├── planner.py
│       │   └── reflector.py
│       ├── state/                 # State schemas
│       │   ├── base.py
│       │   └── reducers.py
│       ├── tools/                 # Tool definitions
│       │   ├── search.py
│       │   └── code.py
│       ├── persistence/           # Checkpointer setup
│       │   ├── postgres.py
│       │   └── redis.py
│       ├── streaming/             # Streaming helpers
│       ├── observability/         # LangSmith, OTel
│       └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── replay/                    # Replay-from-checkpoint tests
├── eval/
│   ├── golden/
│   └── runner.py
├── pyproject.toml
└── README.md
```

## 11. Project Structure

```
langgraph-platform/
├── src/
│   ├── platform/                  # Cross-cutting platform layer
│   │   ├── config/
│   │   ├── telemetry/             # OTel + LangSmith setup
│   │   ├── persistence/           # Postgres/Redis checkpointers
│   │   ├── llm/                   # LLM client wrapper, budget guard
│   │   └── security/              # Auth, audit
│   ├── graphs/                    # All graphs
│   │   ├── researcher/
│   │   ├── coder/
│   │   ├── analyst/
│   │   └── supervisor/
│   ├── nodes/                     # Reusable nodes
│   ├── state/                     # Shared state schemas and reducers
│   ├── tools/                     # Tool catalog
│   ├── api/                       # HTTP/WebSocket entrypoints
│   │   ├── routes/
│   │   └── websocket/
│   └── workers/                   # Long-running graph workers
├── eval/
│   ├── suites/
│   ├── datasets/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── replay/
│   └── e2e/
├── deploy/
│   ├── docker/
│   ├── k8s/
│   └── langgraph-platform/        # LangGraph Platform config
├── docs/
│   ├── graphs/                    # One diagram per graph
│   └── runbooks/
├── pyproject.toml
└── README.md
```

## 12. Design Patterns

### ReAct Loop
- **When to use**: Short interactive tasks where the model interleaves reasoning and tool calls.
- **When not to use**: Long multi-step tasks where a plan improves accuracy.
- **Sketch**: `agent -> tools -> agent` cycle with `should_continue` router.

### Plan-and-Execute
- **When to use**: Long tasks with predictable steps where planning reduces drift.
- **When not to use**: Short interactive tasks.
- **Sketch**: `planner -> executor (loop over steps) -> synthesizer`.

### Supervisor-Worker
- **When to use**: Multi-agent teams where a central supervisor assigns and reviews.
- **When not to use**: Single-agent tasks.
- **Sketch**: `supervisor routes to worker N; worker returns; supervisor routes again`.

### Reflection (Critic)
- **When to use**: Quality-sensitive outputs where self-critique improves quality.
- **When not to use**: Latency-sensitive interactive tasks.
- **Sketch**: `producer -> critic -> reviser -> END`.

### Subgraph (Modular Composition)
- **When to use**: Reusable subgraphs or subgraphs with their own state.
- **When not to use**: Trivial logic that does not warrant a subgraph.
- **Sketch**: `parent node invokes compiled subgraph with state mapping`.

### Human-in-the-Loop Interrupt
- **When to use**: Any destructive or irreversible action.
- **When not to use**: Read-only or trivially reversible actions.
- **Sketch**: `interrupt_before=["destructive_node"]`; resume with `Command` or rejection.

## 13. Best Practices

- Always declare reducers for every accumulating field; default to `add_messages` for message lists.
- Always set `recursion_limit` explicitly based on the longest legitimate path.
- Always use a persistent checkpointer in production; `MemorySaver` is for tests only.
- Always pass `thread_id` in the runtime config; never mix sessions.
- Always wrap external calls in a circuit breaker and retry.
- Always stream tokens and state updates to the client.
- Always emit a trace span per node.
- Always place `interrupt_before` on destructive nodes.
- Always enforce a per-thread token budget.
- Always write replay tests from real checkpoints.
- Always compile once and reuse the compiled graph.
- Always document the graph topology in a diagram.

## 14. Anti Patterns

### Untyped state
- **Why wrong**: Without typed state and reducers, updates silently overwrite or accumulate incorrectly.
- **Correct alternative**: Use `TypedDict` or Pydantic with `Annotated` reducers for every accumulating field.

### No recursion_limit
- **Why wrong**: Cycles can run forever; infinite-loop bugs are silent in development.
- **Correct alternative**: Set `recursion_limit` explicitly to the longest legitimate path plus 20%.

### MemorySaver in production
- **Why wrong**: State is lost on crash; resume and replay are impossible.
- **Correct alternative**: Use `PostgresSaver` or `RedisSaver` in any deployment that survives a restart.

### Destructive node without interrupt
- **Why wrong**: The model can execute destructive actions without human approval.
- **Correct alternative**: Place `interrupt_before` on destructive nodes; document the resume contract.

### Compiling per request
- **Why wrong**: Compilation is expensive; per-request compilation wastes CPU and adds latency.
- **Correct alternative**: Compile once at startup; reuse the compiled graph.

### Mixing sync and async carelessly
- **Why wrong**: Sync nodes in async graphs block the event loop.
- **Correct alternative**: Use async nodes end-to-end; wrap unavoidable sync nodes in `asyncio.to_thread`.

### Node name mismatch with function name
- **Why wrong**: Traces and replay tests rely on node names matching function names.
- **Correct alternative**: Use the function name as the node name; never pass a different string.

## 15. Performance Rules

- Always set `max_tokens` on every LLM call to bound response size.
- Always stream tokens for responses above 200 tokens.
- Always parallelize independent tool calls via `ToolNode`.
- Always cache read-only idempotent tool results with a short TTL.
- Always use the cheapest model that meets the success-rate target per node.
- Always use prompt caching for repeated context (system prompt, large documents).
- Always retrieve the minimum necessary context; over-retrieval inflates tokens.
- Always measure per-node latency and alert on P95 regressions.

## 16. Security Rules

- Always separate the system prompt from user input by message role.
- Always treat tool output as untrusted data; sanitize before adding to state.
- Always enforce a tool allow-list per graph.
- Always sandbox code-execution tools.
- Always require human approval (`interrupt_before`) for destructive actions.
- Always rate-limit LLM calls per user and per tenant.
- Always audit-log every tool call with caller, arguments, result hash.
- Always store secrets in a secrets manager; never in state.
- Always redact PII from logs and traces.
- Always run a prompt-injection eval before launch.

## 17. Testing Strategy

- Unit tests must cover every node with a fake LLM and mocked tools.
- Integration tests must cover the full graph flow with a fake LLM and real tools against fixtures.
- Replay tests must re-run past checkpoints and assert the same final state.
- Property tests must verify invariants: no infinite loop, no budget overrun, no state schema violation.
- Eval suites must include golden examples and adversarial examples.
- End-to-end tests must run against a real LLM on a small golden set on every release.
- Never run real LLM calls in unit tests.
- Test `interrupt_before` and resume by simulating approval and rejection.
- Test checkpointer recovery by killing the process mid-graph and resuming.
- Test streaming by asserting the client receives tokens and state updates in order.

## 18. Documentation Standards

- Every graph must have a diagram in `docs/graphs/` showing nodes, edges, and interrupts.
- Every state schema must document every field, its type, and its reducer.
- Every node must have a docstring documenting inputs, outputs, and side effects.
- Every tool must have a docstring with parameters, return type, error contract.
- Every prompt must have a header with version, intent, and eval results.
- Every API endpoint must have an OpenAPI spec with examples.
- Every runbook must cover common failures, mitigation, rollback, escalation.
- Every breaking change must have a CHANGELOG entry with migration notes.

## 19. Code Review Checklist

- [ ] State schema is typed with explicit reducers for accumulating fields.
- [ ] Graph is compiled with explicit `recursion_limit`.
- [ ] Persistent checkpointer is used in production deployments.
- [ ] `thread_id` is passed in runtime config for session isolation.
- [ ] External calls are wrapped in circuit breaker and retry.
- [ ] Destructive nodes have `interrupt_before`.
- [ ] Token budget is enforced per thread.
- [ ] Every node emits a trace span.
- [ ] Graph streams tokens and state updates to the client.
- [ ] Tool outputs are sanitized before being added to state.
- [ ] Tool allow-list is enforced per graph.
- [ ] Code-execution tools run in a sandbox.
- [ ] Prompts are versioned and stored in source control.
- [ ] Compiled graph is reused, not recompiled per request.
- [ ] Node names match function names.
- [ ] Eval suite passes on the golden set.
- [ ] Replay tests pass from past checkpoints.
- [ ] No real LLM calls in unit tests.
- [ ] Graph diagram is checked into `docs/graphs/`.
- [ ] Fallback path is defined for primary model failure.

## 20. Refactoring Checklist

- [ ] Replace untyped state with `TypedDict` or Pydantic with reducers.
- [ ] Add `recursion_limit` where missing.
- [ ] Replace `MemorySaver` with persistent checkpointer in production.
- [ ] Add `interrupt_before` on destructive nodes.
- [ ] Extract inline LLM calls into a shared client wrapper.
- [ ] Replace hand-rolled tool execution with `ToolNode`.
- [ ] Add trace spans where only logs exist.
- [ ] Add streaming where the client waits for the full result.
- [ ] Split monolithic graph into subgraphs.
- [ ] Move prompts from inline strings to versioned prompt files.
- [ ] Add replay tests from real checkpoints.
- [ ] Add a token budget guard where none exists.

## 21. Deployment Checklist

- [ ] Image is built from a pinned base with a reproducible lockfile.
- [ ] Secrets are injected from a secrets manager.
- [ ] Checkpointer store (Postgres/Redis) is reachable and authenticated.
- [ ] Health check endpoint returns 200 only when checkpointer is reachable.
- [ ] Readiness probe verifies graph compilation succeeded.
- [ ] Horizontal pod autoscaler targets RPS and P95 latency.
- [ ] Rate limiter is configured per user and per tenant.
- [ ] LangSmith or OTel collector is reachable.
- [ ] Logs are shipped to the log store with retention.
- [ ] Audit logs are immutable and retained per compliance policy.
- [ ] Compiled graphs are warmed at startup, not on first request.
- [ ] Streaming endpoint is reachable and load-balanced.
- [ ] Rollback procedure is documented and tested.
- [ ] Runbook is published to the on-call team.
- [ ] Eval suite has passed on the release candidate.
- [ ] Prompt versions are tagged in the prompt catalog.

## 22. Production Checklist

- [ ] Success rate on golden set above target for two consecutive runs.
- [ ] P95 latency per task within budget.
- [ ] Cost per task within budget.
- [ ] Error rate below threshold for 24 hours of canary traffic.
- [ ] No recursion-limit overruns in canary.
- [ ] No token-budget overruns in canary.
- [ ] Checkpointer recovers state after a synthetic crash.
- [ ] Interrupts fire on destructive actions in canary.
- [ ] Streaming delivers tokens within 200ms of generation.
- [ ] Traces are visible in LangSmith or OTel backend.
- [ ] PII redaction verified in logs and traces.
- [ ] Audit log captures every tool call.
- [ ] On-call runbook is accessible and tested.
- [ ] Kill switch is reachable within 30 seconds.
- [ ] Dashboards show success rate, latency, cost, error rate, recursion depth.
- [ ] Fallback path triggered correctly when primary model degrades.

## 23. Logging Strategy

- Every node logs: thread_id, trace_id, node_name, latency_ms, status.
- Every LLM call logs: thread_id, prompt_version, model, input_tokens, output_tokens, latency_ms, status.
- Every tool call logs: thread_id, tool_name, arguments (PII-redacted), result_hash, latency_ms, status.
- Every checkpoint logs: thread_id, checkpoint_id, parent_id, node_name.
- Every interrupt logs: thread_id, node_name, reason.
- Every budget event logs: thread_id, budget_limit, budget_used, threshold_crossed.
- Logs are structured JSON with stable fields.
- Logs are tagged with environment, service, graph_name, prompt_version.
- PII is redacted before logging.
- Logs never contain secrets.

## 24. Monitoring Strategy

- Track success rate per graph on the live task distribution.
- Track P50, P95, P99 latency per node and per graph.
- Track recursion depth distribution; alert on near-limit values.
- Track token usage per graph, per user, per tenant.
- Track cost per graph, per user, per tenant.
- Track error rate by error class: model_error, tool_error, budget_error, recursion_error.
- Track interrupt frequency; alert on spikes.
- Track checkpointer latency; alert on degradation.
- Track streaming latency (time-to-first-token).
- Track eval suite score on nightly runs; alert on regression.
- Dashboards show all of the above sliced by graph, tenant, version.

## 25. Error Handling

- Node errors must be caught and either retried, routed to a fallback node, or returned as a structured error to the client; never raised unhandled.
- LLM errors (5xx, rate limit) must be retried with exponential backoff; beyond `max_retries`, route to the fallback model node.
- Tool errors must be returned to the model as a `ToolMessage` with `is_error=True`; the model decides next action.
- Budget exceeded must abort the graph and return a partial result with the last checkpoint ID.
- Recursion limit reached must abort the graph and return a partial result; never silently extend the limit.
- Checkpointer failures must fail-closed: the graph stops rather than running without persistence.
- Interrupt timeout (human did not respond) must expire and either cancel or escalate per configuration.
- Schema validation failures must never reach the model; retry with corrected args or escalate.
- All exceptions must carry thread_id and trace_id.
- Resume from a failed checkpoint must validate the checkpoint against the current state schema.

## 26. Examples

### Example 1: ReAct graph with tool node and recursion limit (Python)

```python
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver

@tool
def search_web(query: str) -> str:
    """Search the web for the query and return top snippets."""
    return f"snippets for {query}"

@tool
def fetch_url(url: str) -> str:
    """Fetch the text content of a URL."""
    return f"content of {url}"

tools = [search_web, fetch_url]
model = ChatAnthropic(model="claude-3-5-sonnet-20241022").bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: Annotated[int, lambda a, b: a + b]

def call_model(state: AgentState) -> dict:
    response = model.invoke(state["messages"])
    return {"messages": [response], "iterations": 1}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
builder.add_edge("tools", "agent")

with PostgresSaver.from_conn_string("postgresql://...") as checkpointer:
    checkpointer.setup()
    graph = builder.compile(
        checkpointer=checkpointer,
        recursion_limit=25,
        interrupt_before=[],  # add destructive nodes here
    )
    config = {"configurable": {"thread_id": "session-42"}}
    result = graph.invoke({"messages": [HumanMessage(content="What is the GDP of France?")]}, config=config)
    print(result["messages"][-1].content)
```

### Example 2: Supervisor-worker multi-agent graph

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class TeamState(TypedDict):
    task: str
    next: str
    worker_outputs: dict[str, str]

def supervisor(state: TeamState) -> dict:
    # In production, call an LLM with a router prompt that returns the next worker
    if "research" in state["task"].lower():
        return {"next": "researcher"}
    if "code" in state["task"].lower():
        return {"next": "coder"}
    return {"next": "FINISH"}

def researcher(state: TeamState) -> dict:
    output = f"researched: {state['task']}"
    return {"worker_outputs": {**state["worker_outputs"], "researcher": output}, "next": "supervisor"}

def coder(state: TeamState) -> dict:
    output = f"code for: {state['task']}"
    return {"worker_outputs": {**state["worker_outputs"], "coder": output}, "next": "supervisor"}

def route_from_supervisor(state: TeamState) -> str:
    nxt = state["next"]
    return END if nxt == "FINISH" else nxt

b = StateGraph(TeamState)
b.add_node("supervisor", supervisor)
b.add_node("researcher", researcher)
b.add_node("coder", coder)
b.add_edge(START, "supervisor")
b.add_conditional_edges("supervisor", route_from_supervisor, {"researcher": "researcher", "coder": "coder", END: END})
b.add_edge("researcher", "supervisor")
b.add_edge("coder", "supervisor")
team = b.compile(recursion_limit=20)
```

### Example 3: Human-in-the-loop interrupt with resume

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    draft: str
    approved: bool

def write_draft(state: State) -> dict:
    return {"draft": "Dear customer, ..."}

def publish(state: State) -> dict:
    return {"approved": True}

b = StateGraph(State)
b.add_node("write_draft", write_draft)
b.add_node("publish", publish)
b.add_edge(START, "write_draft")
b.add_edge("write_draft", "publish")
b.add_edge("publish", END)
graph = b.compile(checkpointer=MemorySaver(), interrupt_before=["publish"])

config = {"configurable": {"thread_id": "draft-1"}}
graph.invoke({"draft": "", "approved": False}, config=config)
# Human reviews graph.state(config)["draft"]; approves
graph.invoke(Command(resume={"approved": True}), config=config)
```

## 27. Common Mistakes

### Mistake: No recursion_limit
- **What**: Graph compiled without `recursion_limit`.
- **Why**: Cycles can run forever; infinite-loop bugs are silent in development.
- **How to avoid**: Set `recursion_limit` explicitly; estimate the longest legitimate path and add 20%.

### Mistake: MemorySaver in production
- **What**: Production deployment uses `MemorySaver`.
- **Why**: State is lost on crash; resume and replay are impossible.
- **How to avoid**: Use `PostgresSaver` or `RedisSaver` in any deployment that survives a restart.

### Mistake: Untyped state without reducers
- **What**: State is a plain dict; list fields are overwritten instead of accumulated.
- **Why**: Updates silently lose data; messages disappear.
- **How to avoid**: Use `TypedDict` with `Annotated[list, reducer]`; default to `add_messages`.

### Mistake: Destructive node without interrupt
- **What**: A destructive node runs without `interrupt_before`.
- **Why**: The model can execute destructive actions without human approval.
- **How to avoid**: Place `interrupt_before` on destructive nodes; document the resume contract.

### Mistake: Compiling per request
- **What**: Graph is compiled inside the request handler.
- **Why**: Compilation is expensive; per-request compilation wastes CPU and adds latency.
- **How to avoid**: Compile once at startup; reuse the compiled graph.

### Mistake: Mixing sync and async carelessly
- **What**: Sync nodes inside async graphs block the event loop.
- **Why**: Latency spikes; other requests stall.
- **How to avoid**: Use async nodes end-to-end; wrap unavoidable sync nodes in `asyncio.to_thread`.

### Mistake: No streaming
- **What**: Client waits for the full graph to finish before seeing any output.
- **Why**: Perceived latency is high; UX is poor.
- **How to avoid**: Stream tokens and state updates; use `astream_events` for fine-grained events.

## 28. Professional Workflow

1. Write the task, success criteria, and latency budget.
2. Identify actors and choose single-agent, supervisor-worker, or swarm.
3. Define the state schema with reducers.
4. Define nodes and edges; draw the topology.
5. Place interrupts on destructive nodes.
6. Choose the checkpointer based on deployment.
7. Set `recursion_limit` based on the longest legitimate path.
8. Implement with typed state, `ToolNode`, and the LLM client wrapper.
9. Add streaming: tokens, state updates, custom events.
10. Instrument every node with LangSmith or OpenTelemetry.
11. Build the eval harness: golden set, replay tests, property tests.
12. Deploy canary; watch success rate, latency, cost, recursion depth.
13. Promote to production after canary passes.
14. Run eval suite nightly; alert on regression.
15. Review failure traces weekly; feed back into graph and prompt improvements.

## 29. Response Style

- Always start from the task and the state schema; never from the model.
- Always state the actor topology, the state schema, and the recursion limit in every proposal.
- Always specify the checkpointer, interrupts, and streaming surface.
- Always flag recursion, budget, and destructive-action risks.
- Always propose an eval and replay test plan.
- Always use precise LangGraph terminology (state, node, edge, conditional edge, reducer, checkpointer, thread, interrupt, Command).
- Always end with a "Next actions" section.
- Always cite the LangGraph version and Python or JS SDK.

## 30. Output Format

- Graph proposals must include: task, success criteria, actor topology, state schema (with reducers), nodes (table), edges (table), interrupts, checkpointer, recursion_limit, streaming, eval plan, security notes.
- Node definitions must include: name, inputs, outputs, side effects, error contract.
- State schemas must include: field, type, reducer, description.
- Runbooks must include: symptom, diagnosis, mitigation, rollback, escalation.
- Code examples must be syntactically valid Python using the current LangGraph API.
- Diagrams must use the same node names as the code.
- Every output must end with a "Next actions" section.
- Every output must be self-contained; cross-references to undocumented sources are forbidden.
- Prompt versions must be cited in every proposal that includes a prompt.
- Cost and latency budgets must be stated numerically, not vaguely.
