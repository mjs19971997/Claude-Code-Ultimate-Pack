# Agents and Middleware

Reference for `langchain.agents.create_agent`, tools, structured output and the agent middleware system in LangChain 1.x. Verified against langchain 1.4.7, langchain-core 1.7.3, langgraph 1.2.18 (Python) and langchain 1.6.0 on npm (2026-10). Signatures below come from the package source; for provider-specific model options and newer middleware, check the current docs.

## 1. create_agent

```python
from langchain.agents import create_agent

agent = create_agent(
    model,                       # "provider:model" string or a BaseChatModel instance
    tools=[...],                 # BaseTool, plain callables, or provider tool dicts
    system_prompt="...",         # str or SystemMessage
    middleware=[...],            # ordered AgentMiddleware instances
    response_format=None,        # Schema, ToolStrategy(...), ProviderStrategy(...)
    state_schema=None,           # TypedDict extending AgentState
    context_schema=None,         # type of runtime context (a dataclass works well)
    checkpointer=None,           # BaseCheckpointSaver for per-thread memory
    store=None,                  # BaseStore for cross-thread memory
    name=None,                   # used when the agent is a subgraph node
    cache=None, debug=False,
)
```

- The result is a compiled LangGraph graph: it supports `invoke`, `ainvoke`, `stream`, `astream`, `get_state` and can be added as a node to another graph.
- Loop: the model node runs; if the `AIMessage` has `tool_calls`, the tools node runs them and appends `ToolMessage`s; this repeats until the model answers without tool calls. With no tools, the agent is a single model node.
- Input is `{"messages": [...]}` (dicts with `role` and `content`, or message objects). Output is the final state: `result["messages"]` and, with `response_format`, `result["structured_response"]`.
- Pass `config={"configurable": {"thread_id": "..."}, "recursion_limit": N}` and, for a `context_schema`, `context=Context(...)` on each call. `version="v2"` returns a `GraphOutput` with `.value` and `.interrupts`.
- `interrupt_before`/`interrupt_after` accept node names; prefer `HumanInTheLoopMiddleware` for tool approval.
- `create_react_agent` from `langgraph.prebuilt` is deprecated in favor of `create_agent`; its `prompt` argument is `system_prompt` here, and hooks that used `pre_model_hook`/`post_model_hook` become middleware.

## 2. Models

- `init_chat_model("provider:model", **kwargs)` returns a chat model for the matching installed provider package (for example `langchain-openai`, `langchain-anthropic`). Install the provider package and set its API key environment variable. `configurable_fields` makes parameters switchable at call time through `config["configurable"]`.
- Messages come from `langchain.messages`: `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`, `RemoveMessage`, and content block types. `AIMessage.tool_calls` holds parsed tool calls and `AIMessage.usage_metadata` token usage.
- Model strings in examples are placeholders; use a model id your provider currently serves.
- Chat models take a `rate_limiter` (`langchain_core.rate_limiters.InMemoryRateLimiter(requests_per_second=...)`) to throttle calls within one process.

## 3. Tools

```python
from langchain.tools import tool, ToolRuntime
from pydantic import BaseModel, Field

class SearchArgs(BaseModel):
    query: str = Field(description="Search terms")
    limit: int = Field(default=5, ge=1, le=20)

@tool(args_schema=SearchArgs)
def search_docs(query: str, limit: int = 5) -> str:
    """Search internal documentation and return the top matches as plain text."""
    ...
```

- The docstring is the tool description the model sees; write what it does, when to use it and side effects.
- `ToolRuntime` is injected when a parameter is named `runtime` and typed `ToolRuntime`; it is not part of the model-visible schema. Attributes: `state`, `context`, `store`, `stream_writer`, `config`, `tool_call_id`, `tools`.
- Tools can update state by returning `Command(update={...})`; include a `ToolMessage(content=..., tool_call_id=runtime.tool_call_id)` in `messages` so the model sees a result.
- `InjectedState` and `InjectedStore` (from `langchain.tools`) inject state or the store into a parameter by annotation, hidden from the model.
- Raise `ToolException` for tool-level failures; configure how errors reach the model with `ToolErrorMiddleware` or `ToolRetryMiddleware`.
- Provider server-side tools (web search, code execution) are passed as dicts in `tools`; their shapes are provider-specific, check the provider docs.
- Tool arguments from the model are untrusted input. Validate ranges, enums and paths in the tool or in the Pydantic schema.

## 4. Structured output

| Option | Behavior |
|---|---|
| `response_format=Schema` | Auto: uses provider-native structured output when the model supports it, otherwise tool calling |
| `ToolStrategy(Schema, handle_errors=True, tool_message_content=None)` | Model "calls" an artificial tool whose arguments are the schema; validation errors are fed back to the model for a retry (`handle_errors` also accepts a message string, exception types or a callable; `False` re-raises) |
| `ProviderStrategy(Schema, strict=None)` | Provider-native JSON-schema response format; `strict` requests strict enforcement where supported |
| `ToolStrategy(Union[A, B])` | Model picks one of several schemas; multiple structured outputs in one turn raise `MultipleStructuredOutputsError` unless handled |

- Import strategies from `langchain.agents.structured_output`.
- Schemas can be Pydantic models, dataclasses or `TypedDict`. A raw JSON-schema dict is passed through unvalidated, so use a typed schema when you need validation and automatic retries.
- Read the result from `result["structured_response"]`; the final `messages` still contain the conversation.
- Outside agents use `model.with_structured_output(Schema, include_raw=False)`; see [lcel-and-models.md](lcel-and-models.md).

## 5. Middleware model

Middleware wraps the agent loop. Each middleware subclasses `AgentMiddleware` (or is built from a decorator) and may implement:

| Hook | Runs | Typical use |
|---|---|---|
| `before_agent(state, runtime)` | Once per invocation, before the loop | Load user data, validate input |
| `before_model(state, runtime)` | Before each model call | Trim or summarize messages, budget checks, `jump_to` |
| `wrap_model_call(request, handler)` | Around each model call | Retry, fallback, swap model or tools, cache, edit the system prompt |
| `after_model(state, runtime)` | After each model response | Output guardrails, approval checks |
| `wrap_tool_call(request, handler)` | Around each tool call | Retry, audit, argument rewriting, error mapping |
| `after_agent(state, runtime)` | Once at the end | Persist results, cleanup |

- `before_*`/`after_*` return a dict of state updates or `None`. `wrap_*` return the handler's result (or a replacement); `wrap_model_call` may return a `ModelResponse` or an `AIMessage`, `wrap_tool_call` returns a `ToolMessage` or `Command`.
- Async variants are `abefore_model`, `awrap_model_call`, and so on. If only an async hook is defined, the agent must be invoked with `ainvoke`/`astream`; a sync call raises `NotImplementedError`.
- Ordering: for `wrap_*` hooks the first middleware in the list is the outermost; `before_*` hooks run in list order and `after_*` hooks in reverse order.
- Custom state: set `state_schema` on the middleware to a `TypedDict` extending `AgentState`; fields are merged into the agent state.
- To end early from `before_model` or `after_model`, return `{"jump_to": "end"}` and declare `@hook_config(can_jump_to=["end"])` (allowed targets: `"tools"`, `"model"`, `"end"`).
- `ModelRequest` carries `model`, `messages`, `system_message`, `tools`, `tool_choice`, `response_format`, `state`, `runtime`, `model_settings`; build changed requests with `request.override(...)`. Do not mutate the request in place.

Decorators for small middleware: `@before_agent`, `@before_model`, `@after_model`, `@after_agent`, `@dynamic_prompt`, `@wrap_model_call`, `@wrap_tool_call`.

```python
from typing import Any
from typing_extensions import NotRequired
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime


class CounterState(AgentState):
    model_calls: NotRequired[int]


class BudgetGuard(AgentMiddleware):
    state_schema = CounterState

    def __init__(self, max_calls: int) -> None:
        self.max_calls = max_calls

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: CounterState, runtime: Runtime) -> dict[str, Any] | None:
        n = state.get("model_calls", 0)
        if n >= self.max_calls:
            return {"messages": [AIMessage(content="Call budget exhausted.")], "jump_to": "end"}
        return {"model_calls": n + 1}
```

## 6. Built-in middleware

All are exported from `langchain.agents.middleware`.

| Middleware | Constructor highlights |
|---|---|
| `HumanInTheLoopMiddleware` | `interrupt_on={"tool": True \| False \| {"allowed_decisions": [...]}}`, `description_prefix`, `interrupt_mode="batched" \| "per_call"` |
| `SummarizationMiddleware` | `model`, `trigger=("tokens", n) \| ("messages", n) \| ("fraction", f)` (or a list), `keep=("messages", n)`, `summary_prompt` |
| `ContextEditingMiddleware` | `edits=[ClearToolUsesEdit(trigger=100_000, keep=3, exclude_tools=(), placeholder=...)]` |
| `ModelCallLimitMiddleware` | `thread_limit`, `run_limit`, `exit_behavior="end" \| "error"` |
| `ToolCallLimitMiddleware` | `tool_name=None`, `thread_limit`, `run_limit`, `exit_behavior="continue" \| "end" \| "error"` |
| `ModelRetryMiddleware` | `max_retries=2`, `retry_on`, `on_failure="continue" \| "error" \| callable`, `backoff_factor=2.0`, `initial_delay=1.0`, `max_delay=60.0`, `jitter=True` |
| `ToolRetryMiddleware` | same options plus `tools=[...]` to scope retries |
| `ToolErrorMiddleware` | `on_error(exc, request) -> str \| None`; return text to give the model an error `ToolMessage`, `None` to propagate |
| `ModelFallbackMiddleware` | `ModelFallbackMiddleware("model-a", "model-b", ...)`, tried in order after the primary fails |
| `PIIMiddleware` | `PIIMiddleware("email" \| "credit_card" \| "ip" \| "mac_address" \| "url" \| custom, strategy="redact" \| "mask" \| "hash" \| "block", detector=regex_or_callable, apply_to_input=True, apply_to_output=False, apply_to_tool_results=False)` |
| `TodoListMiddleware` | Adds a `write_todos` planning tool and prompt |
| `LLMToolSelectorMiddleware` | `model`, `max_tools`, `always_include` to pre-select tools for large tool sets |
| `LLMToolEmulator` | Emulates tool results with a model, for tests and prototypes |
| `FilesystemFileSearchMiddleware` | `root_path` (required); adds glob and grep style search tools over a directory; choose a narrow root |
| `ShellToolMiddleware` | Adds a persistent shell tool; `execution_policy` is `HostExecutionPolicy`, `DockerExecutionPolicy` or `CodexSandboxExecutionPolicy`; `redaction_rules` for output |
| `ProviderToolSearchMiddleware` | Provider-side tool search; check the current docs for supported providers |

Guidance:

- `ShellToolMiddleware` with the host policy runs model-chosen commands on the host. Use a container or sandbox policy, a throwaway workspace, no secrets in the environment, and approval for risky commands.
- `PIIMiddleware` with `strategy="block"` raises `PIIDetectionError`; `redact`, `mask` and `hash` rewrite content before the model sees it.
- Put cheap guards (limits, PII) outermost and retries closest to the call they retry. When combining `ToolRetryMiddleware` with `ToolErrorMiddleware`, place the retry inside and set `on_failure="error"` so exceptions reach the error middleware.

## 7. Human-in-the-loop

`HumanInTheLoopMiddleware` pauses with a LangGraph `interrupt`, so a checkpointer and `thread_id` are required.

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command

hitl = HumanInTheLoopMiddleware(
    interrupt_on={
        "send_email": True,                                        # approve, edit, reject, respond
        "delete_file": {"allowed_decisions": ["approve", "reject"]},
        "search": False,                                           # auto-approved
    },
)
# first call returns an interrupt; the value has action_requests and review_configs
agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}, {"type": "reject", "message": "Keep the file."}]}),
    config,
)
```

- Decisions are matched to the pending tool calls by position in `batched` mode (the default): one interrupt per model turn containing all gated calls.
- `interrupt_mode="per_call"` raises one interrupt per gated tool call (value type `tool_approval`); answer each with a single decision keyed by the interrupt id: `Command(resume={interrupt_id: {"type": "approve"}})`. The source notes `per_call` is planned to become the default in the next major release, so set the mode explicitly.
- Decision types: `approve`, `edit` (with `edited_action` holding the new `name` and `args`), `reject` (optional `message`), `respond` (human supplies the tool result and the tool does not run).
- Validate edited arguments like any other untrusted input; a reviewer's edit still runs your tool code.

## 8. Streaming and invocation

- `agent.stream(inputs, config, stream_mode="updates")` yields per-node updates; `stream_mode="messages"` yields `(message_chunk, metadata)` for token streaming; use a list of modes to combine them.
- With `version="v2"` each part is a dict with `type`, `ns` and `data`, which is easier to route in servers.
- `agent.invoke(..., context=Context(...))` supplies static run data; middleware reads `runtime.context`, tools read `runtime.context` through `ToolRuntime`.
- For multi-agent use, give an agent a `name` and add it as a node of a parent `StateGraph`, or wrap it in a tool that calls `sub_agent.invoke(...)` and returns the final message text.

## 9. JavaScript notes

- `langchain` (npm 1.6.0) exports `createAgent`, `tool`, `initChatModel`, message classes and middleware such as `humanInTheLoopMiddleware`, `summarizationMiddleware` and `createMiddleware`; tools typically use Zod schemas. `fakeModel` from `@langchain/core/testing` helps in tests.
- `@langchain/langgraph` (npm 1.5.3) exports `StateGraph`, `Annotation`, `MessagesAnnotation`, `START`, `END`, `Command`, `Send`, `interrupt`, `MemorySaver`, `InMemoryStore`. The JavaScript default `recursionLimit` is 25 and is set in the run config.
- API names follow camelCase; behavior (checkpointers, interrupts, streaming) matches the Python runtime. Check the JavaScript docs for exact option names before copying Python examples.
