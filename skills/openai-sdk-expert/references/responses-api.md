# Responses API

Reference for requests, output items, conversation state, streaming, background mode and reasoning controls in the Responses API through the official SDKs. Verified against openai-python 3.41.0 and openai-node 7.45.1 type definitions and READMEs (2026-10). Parameter names below are the Python spelling; Node uses the same snake_case request fields inside an options object.

## 1. Request anatomy

```python
response = client.responses.create(
    model=MODEL,
    instructions="Stable rules for the assistant.",
    input="Per-request user text",           # str or a list of input items
    tools=[...],                              # optional
    tool_choice="auto",                       # or a specific tool selection
    text={"format": {"type": "text"}, "verbosity": "medium"},
    reasoning={"effort": "medium", "summary": "auto"},
    max_output_tokens=2000,
    store=True,                               # default when omitted
    metadata={"request_id": "r-123"},         # 16 pairs, keys <= 64, values <= 512 chars
    safety_identifier="hashed-user-id",       # <= 128 chars, hash the raw identity
    prompt_cache_key="support-bot-v3",
)
```

- `input` as a string is one user message. As a list it holds message items (`{"role": "user", "content": ...}`), prior output items, and `function_call_output` items.
- Message content parts: `input_text`, `input_image` (`image_url` can be a URL or a `data:` URL), `input_file`, `input_audio`.
- `instructions` is a system or developer message for this request only. With `previous_response_id`, earlier instructions are not carried over, which makes swapping them per request simple.
- `truncation`: `"disabled"` (default) fails with 400 when the input exceeds the context window; `"auto"` drops items from the start of the conversation.
- `include` adds optional output data. Values documented in the SDK: `web_search_call.action.sources`, `code_interpreter_call.outputs`, `file_search_call.results`, `message.output_text.logprobs`, `message.input_image.image_url`, `computer_call_output.output.image_url`, `reasoning.encrypted_content`.
- `max_tool_calls` caps the total number of built-in tool calls in one response; `parallel_tool_calls` allows parallel calls.
- `service_tier`: `auto`, `default`, `flex`, `scale`, `priority`, `fast` and `ultrafast` are accepted by the SDK types; `fast` and `priority` are reported back as `priority`, and `ultrafast` is access-controlled and model-specific. The response reports the tier actually used.

## 2. Output items

`response.output` is a list. Common item `type` values:

| type | Meaning |
|---|---|
| `message` | Assistant message; `content` holds `output_text` (with `annotations` such as citations) or `refusal` parts |
| `reasoning` | Reasoning item; may carry a summary when `reasoning.summary` is set, and `encrypted_content` when requested |
| `function_call` | Your function: `name`, `arguments` (JSON string), `call_id` |
| `web_search_call`, `file_search_call`, `code_interpreter_call`, `image_generation_call` | Built-in tool activity |
| `mcp_list_tools`, `mcp_call`, `mcp_approval_request` | Remote MCP activity |
| `custom_tool_call` | A `custom` tool call with free-form input |

- `response.output_text` joins every `output_text` part; it is an empty string if there are none.
- `response.status` is one of `completed`, `failed`, `in_progress`, `cancelled`, `queued`, `incomplete`. Read `incomplete_details` and `error` for the reason.
- `response.usage` has `input_tokens`, `output_tokens`, `total_tokens` and detail objects (cached and reasoning tokens).
- Never index `output[0]` for the answer; reasoning items can precede the message.

## 3. Conversation state

Three options:

1. **Chain by ID**: `previous_response_id=prev.id`. Requires the previous response to be stored. Resend `instructions` on each call.
2. **Conversation object**: `conv = client.conversations.create(items=[...], metadata={...})` (up to 20 initial items per call), then `client.responses.create(..., conversation=conv.id)`. Items from the conversation are prepended to the request, and the request's input and output items are appended after the response completes. `previous_response_id` and `conversation` cannot be used together. Add items with `client.conversations.items.create(conv.id, items=[...])`.
3. **Manual replay**: keep the list of input and output items yourself and send it as `input`. Keep every output item in order (reasoning, tool calls, messages). Node provides `toResponseInputItems(response.output)` from the package to normalize items for replay.

Stateless operation (zero data retention, or no server-side storage wanted): `store=False`, `include=["reasoning.encrypted_content"]`, and manual replay so reasoning context survives between turns.

`store` defaults to true; stored responses are kept for at least 30 days subject to the data-retention rules in the docs. Delete explicitly with `client.responses.delete(id)`.

`reasoning.context` (`auto`, `current_turn`, `all_turns`) controls which reasoning items are shown to the model on later turns; the SDK documents `all_turns` as the default for the `gpt-5.6` family and `current_turn` for earlier models.

Long histories: `context_management=[{"type": "compaction", "compact_threshold": 100000}]` asks the server to compact when the threshold is reached, and `client.responses.compact(...)` compacts explicitly. Both appear in the SDK 3.41 types; read the current guide before relying on them.

## 4. Streaming

```python
stream = client.responses.create(model=MODEL, input="Write a haiku.", stream=True)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.completed":
        usage = event.response.usage
```

Frequently used event types:

- Lifecycle: `response.created`, `response.in_progress`, `response.queued`, `response.completed`, `response.incomplete`, `response.failed`, `error`.
- Items and content: `response.output_item.added`, `response.output_item.done`, `response.content_part.added`, `response.content_part.done`.
- Text: `response.output_text.delta`, `response.output_text.done`, `response.refusal.delta`, `response.refusal.done`.
- Function calls: `response.function_call_arguments.delta`, `response.function_call_arguments.done`.
- Reasoning: `response.reasoning_summary_text.delta`, `response.reasoning_summary_text.done`.
- Built-in tools: `response.web_search_call.searching`, `response.file_search_call.searching`, `response.code_interpreter_call_code.delta`, `response.mcp_call_arguments.delta`, `response.image_generation_call.partial_image`.

Helper that returns a typed final response (Python):

```python
with client.responses.stream(model=MODEL, input="Summarize the report.") as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="")
    final = stream.get_final_response()
```

Node:

```ts
const stream = client.responses.stream({ model, input: 'Summarize the report.' });
for await (const event of stream) {
  if (event.type === 'response.output_text.delta') process.stdout.write(event.delta);
}
const final = await stream.finalResponse();
```

Notes:

- Accumulate function-call argument deltas per `item_id` and only parse JSON after the `done` event; partial JSON is not valid.
- When a stream is aborted early, the request is cancelled client-side; use `background=True` if the work must survive disconnects.
- With `background=True` and `stream=True`, a dropped connection can be resumed by retrieving the response with the last `sequence_number` seen (`starting_after`). Check the background guide for the exact flow.
- `stream_options` accepts `include_obfuscation`; leave defaults unless you have a reason.

## 5. Background mode and webhooks

```python
job = client.responses.create(model=MODEL, input=long_task, background=True)
# store job.id; status starts as "queued" or "in_progress"
result = client.responses.retrieve(job.id)
if result.status == "completed":
    use(result.output_text)
# cancel if needed
client.responses.cancel(job.id)
```

- Prefer a webhook to polling. Event types in the SDK include `response.completed`, `response.failed`, `response.incomplete` and `response.cancelled`.
- Verify and parse in one step with the raw body: `event = client.webhooks.unwrap(raw_body, headers)`; the secret defaults to `OPENAI_WEBHOOK_SECRET`. Return a 2xx quickly, dedupe by event or response ID, and fetch the response with `retrieve`.
- Batch jobs also emit webhook events (`batch.completed`, `batch.failed`, `batch.expired`, `batch.cancelled`).
- Background responses need server-side state; check the background guide for how it interacts with `store` and data-retention settings.

## 6. Reasoning and output controls

- `reasoning.effort`: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Not every model supports every value, so read the model page. Lower effort means faster responses and fewer reasoning tokens.
- `reasoning.summary`: `auto`, `concise`, `detailed`; `concise` is for `computer-use-preview` and reasoning models after `gpt-5`. Summaries are for debugging or display, not a transcript of internal reasoning.
- `reasoning.mode`: `standard` or `pro` on models that expose it.
- `text.verbosity`: `low`, `medium` (default), `high`.
- `max_output_tokens` bounds visible output plus reasoning tokens.
- Sampling parameters (`temperature`, `top_p`) can be restricted on reasoning models; read the model page before tuning them.

## 7. Prompt caching and stored prompts

- Cache hits need an identical leading prefix. Put instructions, tool definitions and few-shot examples first and variable data last.
- `prompt_cache_key` groups similar requests for better hit rates (it replaces the `user` field for that purpose).
- `prompt_cache_options` (documented for `gpt-5.6` and later) selects implicit or explicit cache breakpoints with a `30m` TTL. `prompt_cache_retention` (`in_memory`, `24h`) is deprecated.
- `prompt={"id": "pmpt_...", "variables": {...}}` references a stored prompt template instead of inline `instructions`; version it in your code and review changes like code.

## 8. Chat Completions differences

| Chat Completions | Responses |
|---|---|
| `messages=[{"role": "system" \| "developer", ...}]` | `instructions=` plus `input=` |
| `choices[0].message.content` | `response.output_text` |
| `max_tokens` / `max_completion_tokens` | `max_output_tokens` |
| `response_format={...}` | `text={"format": {...}}` |
| `tools=[{"type": "function", "function": {...}}]` | `tools=[{"type": "function", "name": ..., "parameters": ..., "strict": ...}]` |
| `reasoning_effort="low"` | `reasoning={"effort": "low"}` |
| Stateless by default (you resend messages) | Stored by default; chain with `previous_response_id` or Conversations |

The SDK README states Chat Completions is supported indefinitely; Responses is described as the primary API.
