---
name: langchain-expert
description: >-
  Builds LLM applications and agents with LangChain 1.x (create_agent, middleware, tools, structured output, LCEL runnables, init_chat_model) and LangGraph 1.x (StateGraph, reducers, checkpointers and durable execution, interrupts and human-in-the-loop, Command and Send, streaming modes, subgraphs), traced and evaluated with LangSmith. Absorbs the former langgraph-expert skill. Use when writing or migrating code that imports langchain, langchain_core or langgraph, designing agent graphs, adding approvals or persistence, or debugging recursion limits, state reducers and resume behavior. Not for retrieval pipeline design (use rag-expert), MCP servers (use mcp-expert), prompt wording (use prompt-engineering-expert), or CrewAI crews (use crewai-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# LangChain Expert

This skill covers building LLM applications with LangChain 1.x and LangGraph 1.x in Python (with notes for the JavaScript packages): the `create_agent` loop and its middleware, chat models and tools, LCEL runnables for non-agent pipelines, structured output, and the LangGraph runtime for custom graphs, persistence, interrupts and streaming. It absorbs the former langgraph-expert skill; the full graph material lives in a dedicated reference. Tracing and evaluation use LangSmith.

> Verified against langchain 1.4.7, langchain-core 1.7.3, langgraph 1.2.18, langgraph-prebuilt 1.1.1, langgraph-checkpoint 4.3.1, langgraph-checkpoint-postgres 3.2.0, langsmith 0.14.16 (Python 3.10+), and on npm langchain 1.6.0 and @langchain/langgraph 1.5.3 (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: `langchain` (`create_agent`, `langchain.agents.middleware`, `langchain.tools`, `langchain.messages`, `init_chat_model`), `langchain-core` (runnables, LCEL, prompts, output parsers, caches, rate limiters), `langgraph` (StateGraph, Functional API, checkpointers, stores, interrupts, Command, Send, streaming, subgraphs, RetryPolicy), the `langgraph` CLI for local dev, and LangSmith tracing, datasets and evals.
- Legacy: classic chains, `ConversationBufferMemory` style memory, `initialize_agent` and `AgentExecutor` are not part of `langchain` 1.x; they live in the separate `langchain-classic` package. `langgraph.prebuilt.create_react_agent` is deprecated in favor of `langchain.agents.create_agent`.
- Not covered: retriever and vector store design, chunking, hybrid search and RAG evaluation (rag-expert), writing MCP servers (mcp-expert), prompt wording and few-shot design (prompt-engineering-expert), provider SDK specifics (anthropic-sdk-expert, openai-sdk-expert, gemini-sdk-expert), CrewAI (crewai-expert), general agent system architecture (ai-agent-architect).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Packages | `langchain` (agents, middleware, tools, messages, model init), `langchain-core` (runnables and base types), `langgraph` (runtime), provider packages such as `langchain-openai` and `langchain-anthropic`, `langchain-classic` (legacy) |
| `create_agent` | `create_agent(model, tools, *, system_prompt, middleware, response_format, state_schema, context_schema, checkpointer, store, name, ...)` returns a compiled LangGraph graph; `model` is a `"provider:model"` string or a chat model instance |
| Middleware | Hooks `before_agent`, `before_model`, `wrap_model_call`, `wrap_tool_call`, `after_model`, `after_agent`; built-ins include `HumanInTheLoopMiddleware`, `SummarizationMiddleware`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware`, `ModelRetryMiddleware`, `ToolRetryMiddleware`, `ModelFallbackMiddleware`, `PIIMiddleware`, `ContextEditingMiddleware`, `TodoListMiddleware`, `LLMToolSelectorMiddleware` |
| Structured output | `response_format=Schema` (auto: provider-native when supported, else tool calling), `ToolStrategy(Schema)`, `ProviderStrategy(Schema)`; result in `result["structured_response"]`; outside agents use `model.with_structured_output(Schema)` |
| Runtime context | `context_schema` (a dataclass) plus `invoke(..., context=...)`; read it from `runtime.context` in middleware and `ToolRuntime` in tools; keep per-request identity out of model-visible arguments |
| LCEL | `prompt | model | parser`, `RunnableParallel`, `RunnableLambda`, `RunnablePassthrough`, `.with_retry()`, `.with_fallbacks()`, `.batch(..., config={"max_concurrency": n})` |
| StateGraph | State as `TypedDict` (or dataclass or Pydantic), reducers via `Annotated[T, reducer]`, nodes return partial updates, `compile(checkpointer=..., store=...)` |
| Run config | `recursion_limit`, `configurable.thread_id`, `tags`, `metadata`, `max_concurrency` go in the config passed to `invoke`/`stream` (or `graph.with_config(...)`); `compile()` does not accept `recursion_limit` |
| Persistence | Checkpointers: `InMemorySaver` (tests), `SqliteSaver`, `PostgresSaver`/`AsyncPostgresSaver`; stores for cross-thread memory; durability modes `"sync"`, `"async"` (default), `"exit"` |
| Interrupts | `interrupt(value)` pauses (needs a checkpointer), resume with `Command(resume=...)` on the same `thread_id`; the node restarts from its beginning on resume |
| Control flow | `Command(update=..., goto=...)` from a node or tool, `Send(node, input)` for dynamic fan-out, conditional edges, subgraphs as nodes |
| Streaming | `stream_mode` values `values`, `updates`, `messages`, `custom`, `checkpoints`, `tasks`, `debug`; `version="v2"` returns typed parts with `type`, `ns`, `data` |
| LangSmith | `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`; `@traceable`, `tracing_context`, datasets and `evaluate()` |

## 3. Workflow

1. Classify the task: one model call or fixed pipeline (LCEL), a model-plus-tools loop (`create_agent`), or custom control flow with branches, parallel work, approvals or long-running state (LangGraph).
2. Pin versions: `langchain>=1.0`, a provider package, and `langgraph` when graphs are hand-built. Read the current docs for provider-specific model options.
3. Define the contract first: tool signatures with typed arguments and docstrings, the structured output schema, the state or `context_schema`, and which actions are destructive.
4. Build the smallest working version with `create_agent` or a two-node graph and a fake model (see Testing), then add middleware, persistence and streaming one concern at a time.
5. Decide the memory model: short-term per `thread_id` through a checkpointer, long-term across threads through a store, and a context-size policy for long conversations.
6. Put limits in place before the first real run: `recursion_limit` in the run config, `ModelCallLimitMiddleware`/`ToolCallLimitMiddleware`, tool timeouts, and human approval for irreversible tools.
7. Turn on LangSmith tracing, build a small dataset from real failures, and add an evaluator before tuning prompts or models.
8. Switch to a durable checkpointer (Postgres), run the graph under `langgraph dev` or your own server, and test resume after a process restart.

## 4. Decision Rules

- One call, fixed steps, no loop: use LCEL or call the model directly. A loop where the model chooses tools: `create_agent`. Custom branching, human gates, fan-out or multiple agents: `StateGraph`. Mostly ordinary Python control flow that needs persistence and interrupts: the Functional API (`@entrypoint`, `@task`).
- Start with `create_agent` and extend it with middleware before dropping to a hand-built graph; an agent is already a compiled LangGraph graph and can be a node or subgraph in a larger one.
- Structured output inside an agent: `response_format`. For a single non-agent call: `model.with_structured_output(Schema)`. Prefer Pydantic models, dataclasses or `TypedDict`; raw JSON-schema dicts are not validated on the tool strategy.
- Reducers: `add_messages` for chat history (merges by message ID, supports `RemoveMessage`), `operator.add` for plain append-only lists, a custom function for merges, no reducer for last-write-wins. Two parallel nodes writing a key without a reducer raise `InvalidUpdateError`.
- Human approval of a tool call: `HumanInTheLoopMiddleware` on an agent, `interrupt()` inside a custom node. Prefer these over `interrupt_before`/`interrupt_after` node lists, which pause without carrying a typed question.
- Checkpointer: `InMemorySaver` only in tests and notebooks; `PostgresSaver` or `AsyncPostgresSaver` for production; `SqliteSaver` for single-process tools. Anything with `interrupt` or resumability needs one.
- Conversation too long: `SummarizationMiddleware` for lossy compression, `ContextEditingMiddleware` to clear old tool outputs, `trim_messages` for a hard window.
- Multi-agent: start with one agent and tools; use subagents-as-tools or `Command(goto=..., graph=Command.PARENT)` handoffs only when separate prompts, tools or context windows are needed.
- Retries: model and tool retries through `ModelRetryMiddleware`/`ToolRetryMiddleware`, node retries through `RetryPolicy`, plain runnables through `.with_retry()`. Retry only idempotent operations.
- Streaming to a UI: `stream_mode="messages"` for tokens, `"updates"` for node progress, `"custom"` with `get_stream_writer()` for domain events; combine modes in a list.

## 5. Coding Standards

- Import from the 1.x locations: `from langchain.agents import create_agent`, `from langchain.agents.middleware import ...`, `from langchain.tools import tool, ToolRuntime`, `from langchain.messages import AIMessage, HumanMessage, ToolMessage`, `from langchain.chat_models import init_chat_model`.
- Type the state: `TypedDict` with `Annotated` reducers, or Pydantic when input validation is needed. Nodes return only the keys they change.
- Tools: type-hinted arguments, a docstring that states what the tool does and its side effects, a Pydantic `args_schema` for non-trivial inputs, and return concise strings or small JSON, not raw API dumps.
- Do not put request identity (user id, tenant id) in model-controlled tool arguments. Read it from `runtime.context` (`ToolRuntime[Context]`) or injected state.
- Name nodes explicitly with `add_node("name", fn)`; keep nodes small and free of hidden global state. Build and compile the graph once at import time, not per request.
- Use `async` nodes and `ainvoke`/`astream` in servers; do not call blocking code inside async nodes.
- Put models, prompts and settings behind small factory functions so tests can inject fakes; read secrets from the environment, never from state.
- Set `run_name`, `tags` and `metadata` on runs that matter so traces are searchable.

## 6. Project Structure

```
.
├── pyproject.toml
├── langgraph.json            # graph entrypoints for `langgraph dev` / deployment
├── .env.example              # variable names only
├── src/app/
│   ├── agent.py              # create_agent(...) assembly, exports `agent`
│   ├── graph.py              # StateGraph workflows when custom control flow is needed
│   ├── state.py              # State, Context and structured output schemas
│   ├── models.py             # init_chat_model wrappers, retries, rate limiter
│   ├── tools/                # one module per tool group, typed and documented
│   ├── middleware/           # custom AgentMiddleware subclasses and decorators
│   └── prompts/              # system prompts as constants or templates
└── tests/
    ├── fakes.py              # fake chat models with scripted tool calls
    ├── test_tools.py
    ├── test_graph.py         # in-memory checkpointer, resume and interrupt tests
    └── evals/                # LangSmith datasets and evaluators
```

## 7. Design Patterns

- **Agent with middleware stack**: `create_agent` plus ordered middleware (guardrails, retries, limits, summarization, approvals). The first middleware in the list is the outermost wrapper for `wrap_*` hooks.
- **Dynamic prompt and model selection**: `@dynamic_prompt` builds the system prompt from `request.runtime.context`; `@wrap_model_call` can swap `request.override(model=...)` or tools per request.
- **Custom state through middleware**: a middleware declares a `state_schema` extending `AgentState`, so its fields are scoped to its hooks; `before_model` can return `{"jump_to": "end"}` when decorated with `@hook_config(can_jump_to=["end"])`.
- **Tool returning `Command`**: a tool updates agent state (and must include its `ToolMessage`) by returning `Command(update={...})`.
- **Approval gate**: `HumanInTheLoopMiddleware(interrupt_on={"tool": True})` with decisions `approve`, `edit`, `reject`, `respond`, resumed through `Command(resume={"decisions": [...]})`.
- **Map-reduce with `Send`**: a router returns `Command(goto=[Send("worker", payload), ...])`; workers write to a reducer-backed list and a join node consumes it.
- **Supervisor and workers**: a supervisor agent exposes worker agents as tools, or a graph routes with `Command(goto=...)`; each worker has its own tools and prompt.
- **Plan, execute, review**: a planner node writes steps to state, an executor loops over them, a reviewer node decides `Command(goto="executor")` or end, bounded by `recursion_limit`.
- **Subgraph**: compile a graph and add it as a node; use `Command(graph=Command.PARENT, ...)` to hand control to the parent. Details in [references/langgraph.md](references/langgraph.md).
- **LCEL pipeline**: `prompt | model.with_structured_output(Schema)` with `.with_retry()` and `.with_fallbacks()`. Details in [references/lcel-and-models.md](references/lcel-and-models.md).

## 8. Best Practices

- Keep tool sets small and well named; use `LLMToolSelectorMiddleware` only when dozens of tools make selection unreliable.
- Let the model recover from expected tool failures: `ToolRetryMiddleware(on_failure="continue")` or `ToolErrorMiddleware(on_error=...)`, which returns selected exceptions as error `ToolMessage`s. Name the exception type rather than echoing raw messages that may carry internal detail, and let programmer errors propagate.
- Make side-effecting nodes idempotent: on resume after an interrupt or crash a node runs again from its start. Put side effects after the `interrupt()` call, or in a separate node or `@task`.
- Place `interrupt()` first in the node or keep pre-interrupt code free of side effects; do not wrap `interrupt()` in a bare `try/except`, which swallows the pause.
- Keep state small and serializable. Store large documents in external storage and keep ids in state, since every step is checkpointed.
- Use one `thread_id` per conversation: reuse the id to continue, a new id to start fresh.
- Version prompts and schemas with the code; record the model name and prompt version in run `metadata`.
- Use `Runtime`/`context_schema` for static run data (user, locale, feature flags) instead of stuffing it into messages.

## 9. Performance

- Run independent calls in parallel: `RunnableParallel`, `.batch(..., config={"max_concurrency": n})`, parallel edges or `Send` in graphs, and parallel tool calls from the model.
- Stream tokens (`stream_mode="messages"`) so users see progress; time to first token matters more than total time for chat.
- Cap context: summarize or clear old tool results before they dominate the window; large tool outputs are the usual cause of cost and latency growth.
- Cache deterministic work: node `cache_policy=CachePolicy(ttl=...)` with a cache passed to `compile(cache=...)`, and a model cache (`set_llm_cache`) only for repeatable offline workloads.
- Throttle provider calls with `langchain_core.rate_limiters.InMemoryRateLimiter` passed to the chat model, and use `ModelRetryMiddleware` with backoff and jitter for 429s.
- Choose durability per workload: `"exit"` is fastest but loses mid-run progress on a crash, `"sync"` is safest, `"async"` is the default compromise.
- Reuse compiled graphs, model clients and database connection pools across requests; construct a Postgres pool once at startup.

## 10. Security

- Treat tool outputs, retrieved documents and user input as untrusted: they can contain instructions aimed at the model. Do not give an agent that reads untrusted content tools that can both read private data and send it out (email, HTTP POST, file write); gate those with `HumanInTheLoopMiddleware`.
- Apply least privilege per tool: read-only database users, scoped API tokens, allowlisted URLs and commands. For file tools, resolve and normalize paths and reject anything outside an allowed root before touching the disk.
- Enforce tenancy on every read and write path: derive `user_id`/`tenant_id` from authenticated `context`, not from model output, and scope store namespaces and `thread_id` ownership checks to that identity when loading and when updating state.
- `ShellToolMiddleware` runs commands for the model: use a sandboxed execution policy (container or sandbox policy) rather than the host policy, and never expose it to untrusted users.
- Checkpoints are deserialized with a msgpack-based serializer. Anyone who can write to the checkpoint database can influence what is loaded; restrict database access and set `LANGGRAPH_STRICT_MSGPACK=true` to limit deserialization to an allowlist of safe types (register custom types explicitly).
- State, stores and traces persist what you put into them. Keep secrets out of state and messages; use `PIIMiddleware` (`redact`, `mask`, `hash` or `block`) for emails, card numbers and similar, and LangSmith `hide_inputs`/`hide_outputs` or an anonymizer when traces must not contain content.
- Load API keys from environment or a secret manager; never commit `.env`, and never place provider keys in frontend bundles or `NEXT_PUBLIC_*` variables. Browsers call your server, which calls the model.
- Bound cost and loops: `recursion_limit`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware`, request timeouts and per-user rate limits.
- Validate model output before using it in privileged code (SQL, shell, file paths); structured output gives shape, not safety.

## 11. Testing

- Unit-test tools and nodes as plain functions. A node takes state and returns an update, so assert on the dict.
- Test agents offline with a fake chat model: subclass `GenericFakeChatModel` from `langchain_core.language_models.fake_chat_models`, override `bind_tools` to return `self`, and feed it scripted `AIMessage(tool_calls=[...])` values.
- Test graphs with `InMemorySaver`: invoke to the interrupt, assert `result.interrupts` (with `version="v2"`) or `graph.get_state(config).next`, resume with `Command(resume=...)`, and assert the final state.
- Test limits: a loop graph with `{"recursion_limit": 5}` must raise `GraphRecursionError`.
- Use `graph.get_state_history(config)` to assert checkpoints and `update_state` to set up scenarios.
- Evaluate behavior with LangSmith datasets: `langsmith.evaluate(target, data=dataset, evaluators=[...])` on real failures, with deterministic checks (tool called, schema valid) before LLM-as-judge scoring.
- Keep live-model tests few, marked, and run on a schedule; they are slow and nondeterministic.

## 12. Review Checklist

- [ ] Imports use `langchain.agents`, `langchain.tools`, `langchain.messages`; no `initialize_agent`, `LLMChain` or deprecated memory classes in new code.
- [ ] `recursion_limit` is passed in the run config (not to `compile`), and model/tool call limits exist.
- [ ] State has reducers where parallel branches or message history write the same key.
- [ ] Persistent checkpointer in production, `thread_id` supplied on every call, `setup()` run for Postgres.
- [ ] Destructive or external-effect tools are behind approval; side effects are idempotent on resume.
- [ ] Identity comes from authenticated `context`, not from tool arguments the model fills.
- [ ] No secrets in state, prompts, traces or client bundles; PII handling chosen.
- [ ] Tools have typed arguments, docstrings and bounded outputs.
- [ ] Graph compiled once, async used in servers, connection pools reused.
- [ ] Tracing is on, runs have names and metadata, and an eval dataset exists for the main flow.
- [ ] Tests cover tools, a scripted agent run, interrupt and resume, and the recursion limit.

## 13. Production Notes

- Run the Postgres checkpointer with a connection pool and call `setup()` once (migrations) at deploy time, not per request. Plan checkpoint retention: every step is stored, so prune old threads.
- Resumed runs re-execute the interrupted node from its start; design for at-least-once execution of that node.
- LangGraph's default `recursion_limit` is very high in langgraph 1.2.x (10007 in the source) while the JavaScript default is 25; set an explicit limit appropriate to each graph.
- `langgraph dev` (from `langgraph-cli[inmem]`) serves graphs listed in `langgraph.json` with an in-memory backend for local development; use a real deployment or your own server with Postgres for production.
- Pin `langchain`, `langchain-core`, `langgraph` and provider packages together and upgrade them as a set; deprecation warnings from `langgraph.warnings` signal API moves.
- Handle provider outages with `ModelFallbackMiddleware` or `.with_fallbacks()` and surface partial progress with streaming.
- Sample or redact traces at volume: `LANGSMITH_TRACING_SAMPLING_RATE` controls the fraction traced.
- Details: [references/production-and-langsmith.md](references/production-and-langsmith.md).

## 14. Examples

Agent with per-request context, a tool that reads it, structured output, limits and an approval gate (verified with a scripted fake model; swap `MODEL` for a real id):

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolRetryMiddleware,
    ModelRequest,
    dynamic_prompt,
)
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver  # tests only; use Postgres in production
from langgraph.types import Command
from pydantic import BaseModel, Field

MODEL = "anthropic:claude-sonnet-5-5"  # any "provider:model" accepted by init_chat_model


@dataclass
class Context:
    user_id: str


@tool
def lookup_order(order_id: str, runtime: ToolRuntime[Context]) -> str:
    """Look up an order that belongs to the current user."""
    user = runtime.context.user_id  # identity comes from the server, not from the model
    return f"order {order_id} for {user}: shipped"


@tool
def refund_order(order_id: str) -> str:
    """Refund an order. Irreversible."""
    return f"refunded {order_id}"


class Answer(BaseModel):
    summary: str = Field(description="One-sentence answer for the customer")
    refunded: bool


@dynamic_prompt
def prompt(request: ModelRequest[Context]) -> str:
    return f"You are a support agent for user {request.runtime.context.user_id}."


agent = create_agent(
    model=MODEL,
    tools=[lookup_order, refund_order],
    middleware=[
        prompt,
        ModelCallLimitMiddleware(run_limit=6, exit_behavior="end"),
        ToolRetryMiddleware(max_retries=2),
        HumanInTheLoopMiddleware(
            interrupt_on={"refund_order": {"allowed_decisions": ["approve", "reject"]}}
        ),
    ],
    response_format=Answer,
    context_schema=Context,
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": "ticket-42"}, "recursion_limit": 25}
ctx = Context(user_id="u1")
first = agent.invoke(
    {"messages": [{"role": "user", "content": "Refund order A1"}]},
    config, context=ctx, version="v2",
)
# first.interrupts[0].value["action_requests"] lists the pending refund_order call
final = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}), config, context=ctx, version="v2",
)
print(final.value["structured_response"])
```

Custom graph with parallel fan-out, a reducer, a human gate and a bounded loop (verified end to end with `InMemorySaver`):

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send, interrupt


class State(TypedDict):
    topic: str
    sections: Annotated[list[str], operator.add]  # parallel workers append
    draft: str


def plan(state: State) -> Command[Literal["write_section"]]:
    return Command(goto=[Send("write_section", {"topic": state["topic"], "index": i}) for i in range(3)])


def write_section(inp: dict) -> dict:
    return {"sections": [f"{inp['topic']} part {inp['index']}"]}


def assemble(state: State) -> dict:
    return {"draft": "\n".join(sorted(state["sections"]))}


def review(state: State) -> Command[Literal["publish", "revise"]]:
    approved = interrupt({"question": "Publish this draft?", "draft": state["draft"]})
    return Command(goto="publish" if approved else "revise")


def revise(state: State) -> dict:
    return {"draft": state["draft"] + "\n(revised)"}


builder = StateGraph(State)
builder.add_node("plan", plan)
builder.add_node("write_section", write_section, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node("assemble", assemble)
builder.add_node("review", review)
builder.add_node("publish", lambda s: {})
builder.add_node("revise", revise)
builder.add_edge(START, "plan")
builder.add_edge("write_section", "assemble")
builder.add_edge("assemble", "review")
builder.add_edge("revise", "review")      # loop, bounded by recursion_limit
builder.add_edge("publish", END)
graph = builder.compile(checkpointer=InMemorySaver())

cfg = {"configurable": {"thread_id": "doc-1"}, "recursion_limit": 25}   # limit lives in the run config
graph.invoke({"topic": "x", "sections": []}, cfg)   # pauses at review
graph.invoke(Command(resume=True), cfg)             # approved -> publish
```

LCEL pipeline with structured output, retries and a fallback model (no agent loop needed):

```python
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel


class Ticket(BaseModel):
    category: str
    urgent: bool


primary = init_chat_model("anthropic:claude-sonnet-5-5", temperature=0)
backup = init_chat_model("openai:gpt-5.5", temperature=0)  # use any second provider you have access to
prompt = ChatPromptTemplate.from_messages(
    [("system", "Classify the support ticket."), ("human", "{text}")]
)
chain = (prompt | primary.with_structured_output(Ticket)).with_retry(stop_after_attempt=3)
chain = chain.with_fallbacks([prompt | backup.with_structured_output(Ticket)])

results = chain.batch(
    [{"text": "Site is down!"}, {"text": "Question about invoices"}],
    config={"max_concurrency": 4, "tags": ["triage"]},
)
```

## 15. Common Mistakes

- **`builder.compile(recursion_limit=25)`**: `compile()` has no such argument and raises `TypeError`. Pass `{"recursion_limit": 25}` in the config of `invoke`/`stream`, or `graph.with_config(recursion_limit=25)`.
- **Importing `create_react_agent` from `langgraph.prebuilt` in new code**: deprecated; use `langchain.agents.create_agent`.
- **Using `initialize_agent`, `LLMChain` or `ConversationBufferMemory`**: not in `langchain` 1.x. Use `create_agent` with a checkpointer, or install `langchain-classic` for temporary legacy code.
- **No checkpointer but using `interrupt` or `thread_id`**: nothing is saved and resume fails. Pass `checkpointer=` at `compile`/`create_agent` and a `thread_id` at call time.
- **`InMemorySaver` in production**: state is lost on restart and not shared across workers. Use Postgres.
- **Side effects before `interrupt()`**: the node re-runs from its start on resume, so emails and charges happen twice. Interrupt first or isolate the effect.
- **Resuming with a different `thread_id`**: starts a new run instead of continuing. Reuse the id and send `Command(resume=...)` as the input.
- **Parallel nodes writing the same key without a reducer**: `InvalidUpdateError`. Add `Annotated[list, operator.add]` or another reducer.
- **Returning the whole state from a node** or mutating state in place: return only changed keys.
- **Compiling the graph or creating the model per request**: slow and defeats caching. Build once.
- **Passing user id as a tool argument the model fills**: the model can be talked into another user's id. Read it from `ToolRuntime` context.
- **Catching `Exception` around `interrupt()`**: swallows `GraphInterrupt`. Narrow the except or move the call out.
- **Raw JSON-schema dict with `ToolStrategy`**: arguments are returned unvalidated and retry handling is inert; use Pydantic, dataclass or `TypedDict`.
- **Unbounded agent loops**: no call limits and the high default recursion limit mean a confused model can burn budget. Set `recursion_limit` and `ModelCallLimitMiddleware`.
- **Treating retrieved or tool text as instructions** with powerful tools attached: add approval gates and least-privilege tools.

## 16. References

- [references/agents-and-middleware.md](references/agents-and-middleware.md): `create_agent` parameters, tools and `ToolRuntime`, structured output strategies, built-in and custom middleware, hook order, dynamic models and prompts, human-in-the-loop decisions, JavaScript notes.
- [references/langgraph.md](references/langgraph.md): absorbed langgraph-expert content: StateGraph, reducers, nodes and edges, Command and Send, checkpointers and durability, interrupts, streaming modes, subgraphs, Functional API, stores, retries and timeouts, JavaScript API notes.
- [references/lcel-and-models.md](references/lcel-and-models.md): runnables and LCEL composition, prompts and parsers, `init_chat_model`, messages, `with_structured_output`, retries, fallbacks, caching, rate limits, trimming, legacy migration.
- [references/production-and-langsmith.md](references/production-and-langsmith.md): LangSmith tracing configuration, privacy controls, datasets and evaluators, `langgraph` CLI and `langgraph.json`, Postgres checkpointer setup, serializer hardening, operational checklist.
- Official docs: https://docs.langchain.com/oss/python/langchain/overview , https://docs.langchain.com/oss/python/langgraph/overview , https://reference.langchain.com/python/langchain/langchain/ , https://github.com/langchain-ai/langchain , https://github.com/langchain-ai/langgraph , https://docs.langchain.com/langsmith/home
