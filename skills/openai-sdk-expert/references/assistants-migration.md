# Migrating to Responses

Guide for moving code from the Assistants API (assistants, threads, messages, runs) and from Chat Completions to the Responses API. Verified against openai-python 3.41.0 and openai-node 7.45.1 (2026-10): every Assistants method in the Python SDK carries a deprecation marker pointing to the Responses API, and the SDK's Assistants documentation links all lead to the Assistants migration page. The exact shutdown date for Assistants endpoints is published on the deprecations page, which could not be fetched during verification; read it before planning, and treat any remaining Assistants code as urgent migration work.

## 1. Status

- Assistants (`client.beta.assistants`), Threads (`client.beta.threads`), Messages and Runs are deprecated in favor of Responses and Conversations.
- Chat Completions is not deprecated: the SDK README says it is supported indefinitely, and Responses is the primary API for new work.
- The SDK still ships the Assistants resources and streaming helpers so existing code can run until the shutdown; do not start new features on them.

## 2. Concept mapping

| Assistants API | Responses API |
|---|---|
| Assistant (`model`, `instructions`, `tools`, `tool_resources`) | Request fields `model`, `instructions`, `tools` on each call, or a stored prompt referenced with `prompt={"id": ..., "version": ..., "variables": {...}}` |
| Thread | Conversation (`client.conversations.create`) or a chain via `previous_response_id` |
| Message | Item (input message item or output `message` item) |
| Run | Response (`client.responses.create`) |
| Run steps | Items in `response.output` (tool calls, reasoning, messages) |
| `requires_action` plus `submit_tool_outputs` | `function_call` output items answered with `function_call_output` input items |
| Polling a run until `completed` | Synchronous call, `stream=True`, or `background=True` with retrieve or webhook |
| `file_search` with vector stores attached to assistant or thread | `{"type": "file_search", "vector_store_ids": [...]}` in `tools`; vector stores remain (`client.vector_stores`) |
| `code_interpreter` with file IDs | `{"type": "code_interpreter", "container": {"type": "auto", "file_ids": [...]}}` |
| `response_format` on assistant or run | `text={"format": {...}}` |
| `tool_choice`, `parallel_tool_calls`, `reasoning_effort` | same ideas: `tool_choice`, `parallel_tool_calls`, `reasoning={"effort": ...}` |
| `max_prompt_tokens`, `max_completion_tokens` | `max_output_tokens`, `truncation` |
| Thread truncation strategy | `truncation="auto"` or compaction (`context_management`) |
| Metadata on objects | `metadata` on responses and conversations |

## 3. Migration steps

1. **Inventory**: list assistants (`client.beta.assistants.list()`), their instructions, tools, models, and which threads they serve. Export instructions into files under version control.
2. **Choose the state model**: if threads are short and linear, use `previous_response_id`; if multiple workers or users append to one history, create a Conversation per thread; if you must not store data, go stateless with replay.
3. **Move assistant config into code**: instructions become a prompt file, tools become a tools module, and model/effort come from settings. Or create a stored prompt and reference it by ID and version.
4. **Move thread history**: for each active thread, create a Conversation and copy messages with `client.conversations.items.create(conversation_id, items=[...])` (batches of up to 20 items on create). Convert Assistants message content into input items with `role` and `content` parts (`input_text`, `input_image`, `input_file`). Archive finished threads instead of migrating them.
5. **Replace the run loop**: delete create-run and polling code. Call `responses.create(..., conversation=conv_id)` (or chain IDs) and handle `function_call` items in a loop (see the tools reference).
6. **Port tools**: custom functions become flat function tools with `strict: True`; `file_search` keeps its vector stores; `code_interpreter` gets a container definition.
7. **Port streaming**: replace Assistants event handlers (`thread.message.delta` and similar) with Responses events such as `response.output_text.delta`, or use `client.responses.stream()`.
8. **Port outputs**: replace "latest message in thread" reads with `response.output_text` or structured outputs.
9. **Cut over per tenant or feature flag**, compare outputs on a fixed eval set, then delete threads and assistants you no longer need.
10. **Remove** every `client.beta.assistants`, `client.beta.threads` import and the polling helpers (`create_and_poll` and similar).

## 4. Before and after

Assistants (deprecated):

```python
# Deprecated pattern: shown only so it can be recognized and removed.
thread = client.beta.threads.create()
client.beta.threads.messages.create(thread.id, role="user", content=question)
run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=ASSISTANT_ID)
messages = client.beta.threads.messages.list(thread.id)
```

Responses with a Conversation:

```python
conversation = client.conversations.create(metadata={"user": "u-123"})  # once per thread
response = client.responses.create(
    model=MODEL,
    instructions=INSTRUCTIONS,
    input=question,
    tools=TOOLS,
    conversation=conversation.id,
)
print(response.output_text)
```

Chat Completions to Responses:

```python
# before
completion = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "developer", "content": INSTRUCTIONS},
        {"role": "user", "content": question},
    ],
    max_completion_tokens=1000,
)
text = completion.choices[0].message.content

# after
response = client.responses.create(
    model=MODEL, instructions=INSTRUCTIONS, input=question, max_output_tokens=1000
)
text = response.output_text
```

## 5. Behavior differences to plan for

- **Storage**: responses are stored by default (at least 30 days); Assistants objects lived until deleted. Set `store=False` where retention is not acceptable and replay history yourself.
- **Instructions are per request**, not an attribute of a server-side assistant. Version them in your repo and send them each time.
- **Tool results are explicit items**: you send `function_call_output` items; there is no `submit_tool_outputs` endpoint.
- **No run object to poll** unless you opt into `background=True`.
- **History growth**: you control it with `truncation`, compaction, or by starting new conversations; Assistants applied a thread truncation strategy server-side.
- **Cost visibility**: each Responses call reports `usage`; the whole conversation history is billed as input on every turn unless caching applies, so keep stable prefixes first.
- **Model names**: Assistants configs pin models; confirm each model is still on the active list before cutting over.
- **Chat Completions code** that only uses `messages` and `choices[0].message.content` can stay as is; migrate it when you need built-in tools, Conversations, background mode or encrypted reasoning replay.

## 6. Verification checklist

- [ ] No `client.beta.assistants` or `client.beta.threads` calls remain.
- [ ] Each former assistant has a versioned instructions file, a tools list and a model setting.
- [ ] Active threads are migrated or intentionally archived.
- [ ] Tool handlers use `call_id` correctly and have a turn cap.
- [ ] Streaming consumers use Responses event names.
- [ ] An eval set shows no regression on representative conversations.
- [ ] Webhooks or polling cover long-running work.
- [ ] Data retention settings (`store`) match policy.
