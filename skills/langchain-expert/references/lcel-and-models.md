# LCEL, Models and Messages

Reference for the `langchain-core` runnable layer (LCEL), chat models, prompts, parsers, structured output, resilience wrappers and migration from legacy LangChain APIs. Verified against langchain-core 1.7.3, langchain 1.4.7 and langchain-classic 1.0.8 (Python 3.10+) (2026-10). Snippets using a fake model were executed; snippets that call a provider need that provider's package and API key.

## 1. Runnables and LCEL

Every component (prompt, model, parser, retriever, compiled graph, plain function) implements `Runnable`: `invoke`, `ainvoke`, `stream`, `astream`, `batch`, `abatch`, plus `astream_events`. LCEL composes them with `|`.

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer briefly."),
    MessagesPlaceholder("history", optional=True),
    ("human", "{question}"),
])
chain = prompt | model | StrOutputParser()       # model: any chat model
chain.invoke({"question": "What is LCEL?", "history": [HumanMessage("hi")]})
for token in chain.stream({"question": "Explain streaming"}):
    print(token, end="")
```

- A dict of runnables becomes a `RunnableParallel`: `{"context": retriever, "question": RunnablePassthrough()} | prompt | model`. Each branch receives the same input.
- `RunnableLambda(fn)` wraps a function; the `@chain` decorator (from `langchain_core.runnables`) does the same for a function that composes other runnables.
- `RunnableBranch((condition, runnable), ..., default)` routes by input; for anything stateful or looping, use a LangGraph graph instead.
- `RunnableParallel(a=..., b=...)` returns a dict of results; `batch(inputs, config={"max_concurrency": n})` bounds parallelism.
- `.with_config(run_name="qa", tags=[...], metadata={...})` names the run in traces; `.with_types(...)` sets schemas.
- LCEL fits linear or fan-out/fan-in pipelines. Loops, human approval, durable state and tool-calling agents belong in `create_agent` or LangGraph.
- Use `astream_events(..., version="v2")` for fine-grained events when a UI needs them; for agents prefer `stream_mode="messages"`.

## 2. Chat models

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("anthropic:claude-sonnet-5-5", temperature=0, timeout=30, max_retries=2)
```

- `init_chat_model("provider:model", **kwargs)` resolves the provider integration package (`langchain-openai`, `langchain-anthropic`, and others). Model names change often; read the provider docs for current ids.
- `configurable_fields` makes selected parameters switchable per call through `config={"configurable": {...}}`; `config_prefix` namespaces them.
- `model.bind_tools(tools)` returns a model that can emit `tool_calls`; `create_agent` does this for you.
- Common instance options (provider dependent): `temperature`, `max_tokens`, `timeout`, `max_retries`, `rate_limiter`. Set `timeout` explicitly; the default may be unbounded for some providers.
- `AIMessage.usage_metadata` carries token counts; `AIMessage.content_blocks` gives a provider-neutral list of typed content blocks (text, reasoning, tool calls, citations), while `content` may be a string or provider-shaped list.
- Multimodal inputs go in message content blocks (image, audio, file); check the provider for supported types and size limits.

## 3. Structured output outside agents

```python
from pydantic import BaseModel, Field

class Ticket(BaseModel):
    category: str = Field(description="billing, bug or question")
    urgent: bool

classifier = model.with_structured_output(Ticket)       # returns a Ticket instance
ticket = classifier.invoke("Site is down for all users!")

raw = model.with_structured_output(Ticket, include_raw=True)   # dict with raw, parsed, parsing_error
```

- Pydantic models return validated instances; `TypedDict` or a JSON-schema dict return dicts.
- The method used underneath (native JSON schema, tool calling, JSON mode) depends on the provider; some accept `method=` and `strict=` options, check the provider integration docs.
- Validate semantically after parsing (allowed values, ranges); structured output guarantees shape, not truth.
- Inside `create_agent` use `response_format` instead (see [agents-and-middleware.md](agents-and-middleware.md)).

## 4. Prompts and parsers

- `ChatPromptTemplate.from_messages([...])` with `{variables}`; `MessagesPlaceholder("history")` for message lists; `partial()` pre-fills variables.
- Keep prompts in constants or template files, not built with f-strings around untrusted text; template variables keep user text separate from instructions.
- Prefer structured output over output parsers. `StrOutputParser` is the common parser; `JsonOutputParser` and `PydanticOutputParser` exist for models without structured output support.
- Few-shot examples and prompt wording are covered by the prompt-engineering-expert skill.

## 5. Resilience wrappers

```python
chain = (prompt | primary.with_structured_output(Ticket)).with_retry(stop_after_attempt=3)
chain = chain.with_fallbacks([prompt | backup.with_structured_output(Ticket)])
```

- `.with_retry(retry_if_exception_type=(...), wait_exponential_jitter=True, stop_after_attempt=3)` retries on the listed exceptions; restrict it to transient errors (rate limits, timeouts).
- `.with_fallbacks([...], exceptions_to_handle=(...))` tries alternatives in order. Fallbacks should use a different provider or model so a single outage does not take both down.
- Inside agents use `ModelRetryMiddleware` and `ModelFallbackMiddleware`; inside graphs use `RetryPolicy` on nodes.
- Throttle: `InMemoryRateLimiter(requests_per_second=..., max_bucket_size=...)` from `langchain_core.rate_limiters`, passed as `rate_limiter=` to the model. It limits one process only; a shared quota needs an external limiter.

## 6. Caching

- `set_llm_cache(InMemoryCache())` (from `langchain_core.globals` and `langchain_core.caches`) caches identical model calls in process. Use it for offline batch jobs and tests, not for conversational traffic where answers should vary or depend on private context.
- A cache key built from prompt text can leak one user's answer to another if prompts include private context; include tenant identity or do not cache.
- Graph node caching: `compile(cache=...)` with `add_node(..., cache_policy=CachePolicy(ttl=...))`.
- Provider prompt caching is a provider feature; see the provider docs and the relevant SDK skill.

## 7. Managing message history

- In agents and graphs, history is graph state persisted by a checkpointer under a `thread_id`. This replaces `ConversationBufferMemory` and similar classes.
- `trim_messages(messages, max_tokens=..., token_counter="approximate" | model, strategy="last", start_on="human", include_system=True)` keeps a window; `start_on="human"` avoids orphaned tool messages.
- `RemoveMessage(id=...)` returned from a graph node deletes stored messages; `SummarizationMiddleware` replaces old turns with a summary.
- `RunnableWithMessageHistory` still exists in `langchain-core` for LCEL chains that need per-session history without LangGraph; for new work with persistence, a graph with a checkpointer is the simpler option.

## 8. Testing with fake models

```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain.messages import AIMessage

class FakeToolModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):      # agents call bind_tools; scripted replies ignore it
        return self

model = FakeToolModel(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "lookup", "args": {"id": "1"}, "id": "call_1"}]),
    AIMessage(content="Done."),
]))
```

- `GenericFakeChatModel` yields the supplied messages in order; `FakeListChatModel` returns a list of strings. Both are in `langchain_core.language_models.fake_chat_models`.
- Tool call ids must be unique within a conversation.
- For structured output through `ToolStrategy`, script an `AIMessage` whose tool call is named after the schema class.
- JavaScript: `fakeModel` from `@langchain/core/testing`.

## 9. Migrating from pre-1.0 LangChain

| Old | Current |
|---|---|
| `initialize_agent`, `AgentExecutor`, `create_tool_calling_agent` | `langchain.agents.create_agent` |
| `langgraph.prebuilt.create_react_agent` | `langchain.agents.create_agent` (`prompt` becomes `system_prompt`, hooks become middleware) |
| `LLMChain`, `ConversationChain`, `RetrievalQA` | LCEL pipeline or `create_agent` with a retrieval tool |
| `ConversationBufferMemory` and other memory classes | Checkpointer with `thread_id`; summarization or trimming middleware |
| `from langchain.chat_models import ChatOpenAI` | `init_chat_model("openai:...")` or `from langchain_openai import ChatOpenAI` |
| `langchain_community` integrations | Provider packages (`langchain-openai`, ...) where available |
| `.run(...)`, `.predict(...)`, `__call__` | `.invoke(...)` |

Legacy chains and agents are kept in `langchain-classic` for gradual migration; plan to remove that dependency.
