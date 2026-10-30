# LangGraph

Reference for LangGraph 1.x, absorbed from the former langgraph-expert skill: state graphs, reducers, control flow, persistence and durable execution, interrupts, streaming, subgraphs, stores and the Functional API. Verified against langgraph 1.2.18, langgraph-prebuilt 1.1.1, langgraph-checkpoint 4.3.1, langgraph-checkpoint-postgres 3.2.0, langgraph-checkpoint-sqlite 3.1.2 (Python 3.10+) and @langchain/langgraph 1.5.3 on npm (2026-10). The code blocks marked "run" were executed against these versions with fake models.

## 1. State and reducers

```python
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import MessagesState, add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]   # merge by message id; supports RemoveMessage
    steps: Annotated[list[str], operator.add] # append-only
    plan: list[str]                           # no reducer: last write wins
    approved: bool

class Chat(MessagesState):                    # messages + add_messages already wired
    summary: str
```

- State schema can be a `TypedDict`, a dataclass or a Pydantic model. Pydantic validates inputs but adds cost; `TypedDict` is the default choice.
- A node returns a dict of the keys it changes. Each key's reducer merges the update into the stored value. Without a reducer the value is overwritten; two nodes writing the same reducer-less key in one step raise `InvalidUpdateError`.
- `Overwrite(value=...)` from `langgraph.types` bypasses a reducer for one update (for example to reset a list). Do not send more than one `Overwrite` for a channel in a step.
- `StateGraph(State, context_schema=Ctx, input_schema=In, output_schema=Out)`: separate input and output schemas narrow the public API of the graph; private channels can live in the main schema. `config_schema` is deprecated in favor of `context_schema`.
- `MessageGraph` is deprecated; use `StateGraph` with a `messages` key.
- Remove or trim history with `RemoveMessage(id=...)` returned from a node, or `trim_messages` before the model call.

## 2. Nodes, edges, Command and Send

```python
from typing import Literal
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, Send

def router(state: State) -> Literal["research", "answer"]:
    return "research" if state["plan"] else "answer"

builder = StateGraph(State)
builder.add_node("plan", plan_node)
builder.add_node("research", research_node)
builder.add_node("answer", answer_node)
builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", router)          # return value is the next node name
builder.add_edge("research", "answer")
builder.add_edge("answer", END)
graph = builder.compile()
```

- Node signature: `fn(state)`, `fn(state, config)`, `fn(state, runtime)` where `runtime: Runtime[Ctx]` exposes `context`, `store`, `stream_writer`. Nodes can be sync or async.
- Conditional edges: the path function returns a node name, a list of names (parallel), or a key mapped through `path_map`. Annotate return types with `Literal[...]` so graph drawing and validation work.
- `Command(update={...}, goto="node")` returned from a node updates state and routes in one step. Annotate the node's return as `Command[Literal["a", "b"]]` so the graph knows the possible targets. A tool can also return a `Command`.
- `Command(graph=Command.PARENT, goto="node", update={...})` routes in the closest parent graph from inside a subgraph.
- `Send("node", payload)` runs a node with a payload that differs from the main state; return a list of `Send` objects (as `goto` or from a conditional edge) for map-reduce. The target node receives the payload as its input; results merge through reducers.
- Parallel branches start in the same superstep when several edges leave a node; a node with several incoming edges runs after all of them only when declared with `add_edge(["a", "b"], "join")`. `add_node(..., defer=True)` postpones a node until the run is about to end.
- Execution is in supersteps; each step is a checkpoint when a checkpointer is set.

## 3. Compile and run configuration

```python
graph = builder.compile(checkpointer=saver, store=store, cache=cache, name="support")

config = {
    "configurable": {"thread_id": "conv-1"},   # required when a checkpointer is used
    "recursion_limit": 25,                     # run config, NOT a compile() argument
    "tags": ["prod"], "metadata": {"user": "u1"}, "max_concurrency": 8,
}
graph.invoke(inputs, config, context=Ctx(user_id="u1"))

limited = graph.with_config(recursion_limit=25)   # bake defaults into a copy
```

- `compile()` accepts `checkpointer`, `cache`, `store`, `interrupt_before`, `interrupt_after`, `debug`, `name`. It raises `TypeError` for `recursion_limit`.
- `recursion_limit` counts supersteps. Exceeding it raises `GraphRecursionError`. The default in langgraph 1.2.18 is 10007 (overridable with the `LANGGRAPH_DEFAULT_RECURSION_LIMIT` environment variable); set a deliberate limit per graph. Pregel-style cycles need it; a limit is also the cheapest runaway-cost guard.
- `invoke(..., durability="sync" | "async" | "exit")` controls when checkpoints are written. `version="v2"` returns a `GraphOutput(value, interrupts)` and typed stream parts.
- Per-node resilience: `add_node("n", fn, retry_policy=RetryPolicy(max_attempts=3), cache_policy=CachePolicy(ttl=60), timeout=30.0)`. `RetryPolicy` defaults: `initial_interval=0.5`, `backoff_factor=2.0`, `max_interval=128.0`, `max_attempts=3`, `jitter=True`, `retry_on` defaults to `default_retry_on`, which retries connection errors and HTTP 5xx responses but not common programming errors such as `ValueError` or `TypeError`. `timeout` accepts seconds, a `timedelta` or a `TimeoutPolicy(run_timeout=..., idle_timeout=...)` and relies on async cancellation, so blocking sync code is not interrupted promptly.
- Retry only idempotent nodes; a retried node runs again from its start.

## 4. Checkpointers and durable execution

| Package | Class | Use |
|---|---|---|
| `langgraph-checkpoint` (bundled) | `InMemorySaver` (alias `MemorySaver`) | Tests, notebooks |
| `langgraph-checkpoint-sqlite` | `SqliteSaver`, `AsyncSqliteSaver` | Local tools, single process |
| `langgraph-checkpoint-postgres` | `PostgresSaver`, `AsyncPostgresSaver` | Production |

```python
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string(DB_URI) as saver:   # DB_URI from the environment
    saver.setup()                                       # create tables and run migrations once
    graph = builder.compile(checkpointer=saver)
    graph.invoke(inputs, {"configurable": {"thread_id": "conv-1"}})
```

- `setup()` must be called the first time (deploy step). Async code uses `AsyncPostgresSaver.from_conn_string(...)` with `await saver.setup()`; for long-running servers build the saver from a shared connection pool instead of a per-request connection.
- Durable execution: after a crash or restart, invoking the same `thread_id` with `None` input (or `Command(resume=...)` after an interrupt) continues from the last checkpoint. Work in a node is not resumed mid-node, so wrap non-deterministic or side-effecting steps in separate nodes or `@task` functions to avoid repeating them.
- Inspect: `graph.get_state(config)` returns a `StateSnapshot` (`values`, `next`, `tasks`, `config`, `metadata`); `graph.get_state_history(config)` lists checkpoints newest first.
- Time travel: pick a snapshot from history and call `graph.invoke(None, snapshot.config)` to replay from that checkpoint (it forks a new branch). Edit state with `graph.update_state(config, values, as_node="node_name")`, which writes as if that node had run.
- Serialization: the default `JsonPlusSerializer` uses msgpack and by default allows all types with a warning. It is not for untrusted data: someone with write access to the checkpoint database may trigger code execution on load. Set `LANGGRAPH_STRICT_MSGPACK=true` (or pass `allowed_msgpack_modules`) to restrict to an allowlist and register your own state types explicitly. `pickle_fallback` is off by default; keep it off.
- Keep state compact; each step stores a checkpoint. Delete finished threads on a schedule.

## 5. Interrupts and human-in-the-loop

```python
from langgraph.types import Command, interrupt

def approve_payment(state: State) -> Command[Literal["pay", "cancel"]]:
    decision = interrupt({"question": "Approve payment?", "amount": state["amount"]})
    return Command(goto="pay" if decision["approved"] else "cancel")

graph = builder.compile(checkpointer=saver)
cfg = {"configurable": {"thread_id": "pay-1"}}
result = graph.invoke({"amount": 50}, cfg)                    # stops at the interrupt
# result["__interrupt__"] (default format) or result.interrupts with version="v2"
graph.invoke(Command(resume={"approved": True}), cfg)         # same thread_id
```

- `interrupt(value)` raises on first execution, surfacing `value` to the caller. On resume the node re-executes from its start and `interrupt()` returns the resume value.
- A checkpointer and `thread_id` are mandatory. The value must be JSON-serializable.
- Several `interrupt()` calls in one node are matched to resume values by order; in parallel branches each interrupt has an id (`Interrupt.id`), and `Command(resume={interrupt_id: value})` answers specific ones.
- `interrupt(value, response_schema=Model)` validates the resume value (Pydantic model, `TypedDict` or dataclass) and publishes its JSON schema to clients; an invalid answer raises a validation error and nothing is saved, so the caller can answer again.
- Do side effects after the `interrupt()` call or in a later node. Do not wrap `interrupt()` in `try/except Exception`.
- Static `interrupt_before=["node"]` / `interrupt_after=["node"]` (at compile or call time) pause around nodes without a typed question; fine for debugging, prefer `interrupt()` in product flows.
- Common uses: approve or edit a tool call, request missing input, review a draft, then continue with `Command(update=..., goto=...)`.

## 6. Streaming

| `stream_mode` | Emits |
|---|---|
| `values` | Full state after each step |
| `updates` | `{node_name: update}` per node, plus `__interrupt__` entries |
| `messages` | `(message_chunk, metadata)` tokens from model calls inside nodes; metadata has `langgraph_node`, `langgraph_step`, ... |
| `custom` | Anything a node writes with `get_stream_writer()` (or `runtime.stream_writer`) |
| `checkpoints` | Checkpoint creation events |
| `tasks` | Task start and finish events with results and errors |
| `debug` | Detailed trace events |

```python
for part in graph.stream(inputs, cfg, stream_mode=["updates", "custom"], subgraphs=True, version="v2"):
    # part = {"type": "updates" | "custom" | ..., "ns": (...), "data": ...}
    handle(part["type"], part["ns"], part["data"])
```

- With a list of modes and `version="v1"` (default) chunks are `(mode, data)` tuples; with `version="v2"` they are typed dicts with `type`, `ns` and `data`.
- `subgraphs=True` includes events from nested graphs; `ns` identifies the path (for example `("child:<task id>",)`).
- Async: `async for part in graph.astream(...)`. Use `astream_events` only when you need LangChain callback-style events.

## 7. Subgraphs

- Add a compiled graph as a node: `parent.add_node("child", child_graph)`. When schemas share keys, state flows through those keys; when they differ, wrap the subgraph in a function that maps parent state to child input and back.
- A subgraph inherits the parent's checkpointer by default. `compile(checkpointer=False)` disables persistence for it; `True` gives it its own checkpoint namespace (useful for agents that keep private memory).
- Interrupts inside a subgraph pause the whole run; resume on the parent thread.
- `create_agent(..., name="worker")` produces a graph that is ready to be used as a node.
- Use `Command(graph=Command.PARENT, goto="next", update={...})` for a handoff that continues in the parent.

## 8. Stores and long-term memory

```python
from langgraph.store.memory import InMemoryStore          # development
# from langgraph.store.postgres import PostgresStore     # production (langgraph-checkpoint-postgres)

store = InMemoryStore()
graph = builder.compile(checkpointer=saver, store=store)

def remember(state: State, runtime: Runtime[Ctx]) -> dict:
    ns = ("memories", runtime.context.user_id)            # namespace per authenticated user
    runtime.store.put(ns, "preferences", {"language": "en"})
    item = runtime.store.get(ns, "preferences")           # item.value
    hits = runtime.store.search(ns, query="language")     # semantic search needs an index config
    return {}
```

- A checkpointer holds per-thread state; a store holds data shared across threads (user profiles, learned facts). Namespaces are tuples; build them from authenticated identity, never from model output, and apply the same scoping to puts, deletes and searches.
- `PostgresStore` needs `setup()` once, like the checkpointer. Semantic search requires configuring an embedding index; check the current docs for the exact option shape.

## 9. Functional API

```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

@task
def fetch(url: str) -> str:            # task results are checkpointed and not re-run on resume
    return http_get(url)

@entrypoint(checkpointer=InMemorySaver())
def flow(urls: list[str]) -> dict:     # run
    bodies = [f.result() for f in [fetch(u) for u in urls]]   # tasks run in parallel
    ok = interrupt({"approve": len(bodies)})
    return {"bodies": bodies, "ok": ok}

cfg = {"configurable": {"thread_id": "f1"}}
flow.invoke(["a", "b"], cfg)           # pauses at interrupt
flow.invoke(Command(resume=True), cfg)
```

- Use it when the workflow is plain Python control flow (loops, conditionals) but needs persistence, interrupts, streaming and retries. `@entrypoint(retry_policy=..., timeout=...)` and `@task(retry_policy=...)` take the same policies as graph nodes.
- Keep task inputs and outputs serializable; deterministic code between tasks is required for correct replay.

## 10. Agent and multi-agent patterns

- **Prebuilt agent**: `create_agent` from `langchain.agents` (see [agents-and-middleware.md](agents-and-middleware.md)). `langgraph.prebuilt` still exports `ToolNode`, `tools_condition` and the deprecated `create_react_agent`.
- **Hand-built ReAct loop**: model node binds tools (`model.bind_tools(tools)`), `ToolNode(tools)` executes them, `add_conditional_edges("model", tools_condition)` routes to `"tools"` or `END`, `add_edge("tools", "model")`. Set the run `recursion_limit`.
- **Supervisor**: a router node (or an agent with worker agents wrapped as tools) chooses the next worker; workers return to the supervisor via `Command(goto="supervisor", update=...)` and a `FINISH` route ends the run. Give each worker only its tools.
- **Plan and execute**: planner writes `plan: list[str]`; executor pops one step per iteration; replanner decides to continue or finish. Bound steps in state (`max_steps`) in addition to `recursion_limit`.
- **Reflection**: generator and critic nodes loop until the critic passes or a `revisions` counter in state reaches its cap.
- **Map-reduce**: `Send` per item, reducer-backed list, join node (see the example in SKILL.md).
- **Human gate**: `interrupt()` before irreversible steps; or `HumanInTheLoopMiddleware` for agent tools.

## 11. Migration notes (0.x to 1.x)

- `create_react_agent` (`langgraph.prebuilt`) and `AgentState` there are deprecated; use `langchain.agents.create_agent` and `langchain.agents.AgentState`.
- `config_schema` is deprecated for `context_schema`; per-run static data goes in `context=` rather than `config["configurable"]`.
- `MessageGraph` is deprecated; use `StateGraph` with `MessagesState`.
- `compile(recursion_limit=...)` never existed; the limit is a run config key.
- Static `interrupt_before`/`interrupt_after` still work; dynamic `interrupt()` is the documented approach for human input.

## 12. JavaScript API notes

- Package `@langchain/langgraph` (1.5.3): `StateGraph`, `Annotation.Root({...})` with `reducer` and `default`, `MessagesAnnotation`, `START`, `END`, `Command`, `Send`, `interrupt`, `MemorySaver`, `InMemoryStore`. A newer `StateSchema` with `ReducedValue` and Standard Schema / Zod fields also exists; check the current docs before choosing.
- Run config uses camelCase `recursionLimit` (default 25) and `configurable: { thread_id }`.
- Persistent checkpointers ship as separate npm packages: `@langchain/langgraph-checkpoint-postgres` (1.1.2) and `@langchain/langgraph-checkpoint-sqlite` (1.1.0).

```typescript
import { Annotation, Command, END, interrupt, MemorySaver, START, StateGraph } from "@langchain/langgraph";

const State = Annotation.Root({
  items: Annotation<string[]>({ reducer: (a, b) => a.concat(b), default: () => [] }),
  approved: Annotation<boolean>(),
});

const graph = new StateGraph(State)
  .addNode("collect", () => ({ items: ["a"] }))
  .addNode("review", (state) => {
    const ok = interrupt({ question: "Approve?", items: state.items });
    return { approved: Boolean(ok) };
  })
  .addEdge(START, "collect")
  .addEdge("collect", "review")
  .addEdge("review", END)
  .compile({ checkpointer: new MemorySaver() });

const config = { configurable: { thread_id: "t1" }, recursionLimit: 25 };
await graph.invoke({ items: [] }, config);
await graph.invoke(new Command({ resume: true }), config);
```
