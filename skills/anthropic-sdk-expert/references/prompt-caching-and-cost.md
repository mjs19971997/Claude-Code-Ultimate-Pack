# Prompt Caching and Cost

Reference for prompt caching, token counting, effort as a cost lever, and rate-limit accounting. Verified against the Claude API docs, Python SDK `anthropic` 2.3.x and TypeScript SDK `@anthropic-ai/sdk` 1.3.x, models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` (2026-10). No prices appear here: check the pricing page for token, cache write, cache read and batch prices, which differ per model.

## 1. How caching works

- The cache covers the whole prefix in this order: `tools`, `system`, `messages`, up to and including the block marked with `cache_control`.
- A hit needs a 100 percent identical prefix (text, images, tool definitions, key order). Any change at or before the breakpoint changes the hash.
- Cache writes happen only at breakpoints. A request reads by hashing the prefix at its breakpoint and, if nothing matches, walking backward block by block (at most 20 positions, counting the breakpoint) looking for entries that earlier requests wrote.
- A cache entry becomes readable after the first response starts; for parallel requests wait for the first response if you need hits.
- Default lifetime is 5 minutes, refreshed free on each use; lifetime counts from the start of the request that wrote or read the entry. A one-hour lifetime costs more to write (see the pricing page).
- Only `ephemeral` exists as a cache type. Caches are isolated by organization and, on the Claude API, Claude Platform on AWS and Microsoft Foundry, by workspace.
- Caching does not change output; it only changes what is billed and how fast the prefix is processed.

## 2. Two ways to enable it

Automatic caching: one top-level `cache_control`; the breakpoint is placed on the last cacheable block and moves forward as the conversation grows. Best for multi-turn chat and agent loops.

```python
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},          # {"type": "ephemeral", "ttl": "1h"} for one hour
    system=LONG_SYSTEM_PROMPT,
    messages=messages,
)
```

Explicit breakpoints: put `cache_control` on a content block for fine control. Up to 4 breakpoints per request; an automatic breakpoint uses one slot.

```python
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    tools=TOOLS,  # cached as part of the prefix before system
    system=[
        {"type": "text", "text": STATIC_INSTRUCTIONS},
        {"type": "text", "text": REFERENCE_DOCS, "cache_control": {"type": "ephemeral"}},  # last stable block
    ],
    messages=[{"role": "user", "content": f"Today is {today}. {question}"}],  # volatile, after breakpoint
)
```

Edge cases for automatic caching: same explicit TTL on the last block is a no-op; a different TTL on the last block returns 400; with 4 explicit breakpoints already present it returns 400; if the last block is ineligible the system walks backward to the nearest eligible block. The legacy Bedrock integration for Opus 4.6 and earlier rejects top-level `cache_control` (use block-level).

## 3. Where to place the breakpoint

- Put it on the last block that is identical across the requests that should share a cache. A breakpoint on a block that contains a timestamp or the user message writes a new entry every request and never reads.
- In a growing conversation, the final block works as long as each turn adds fewer than 20 blocks. If a turn can add 20 or more, add a second breakpoint closer to the previous write.
- A run of consecutive `tool_use` blocks counts as one position in the lookback, and so does a run of consecutive `tool_result` blocks.
- Keep tools and system prompt first and stable; keep tool definitions in a fixed order. Languages that randomize map key order during JSON serialization (Go, Swift) break caches for `tool_use` inputs.

## 4. Minimum length and what can be cached

- Minimum cacheable prompt on the Claude API: 512 tokens for Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1; other generations differ (the cache page lists them). Shorter prompts are processed without caching and without an error: check usage.
- Cacheable: tool definitions, system blocks, text, images and documents in user turns, `tool_use` and `tool_result` blocks.
- Not cacheable directly: thinking blocks (they are cached with other content from previous assistant turns and count as input when read), citation sub-blocks (cache the top-level document), empty text blocks.

## 5. What invalidates the cache

| Change | Tools | System | Messages |
|---|---|---|---|
| Tool definitions (names, descriptions, parameters) | invalid | invalid | invalid |
| Web search or citations toggle | valid | invalid | invalid |
| `speed` setting (fast mode) | valid | invalid | invalid |
| `tool_choice`, adding or removing images | valid | valid | invalid |
| Thinking configuration or `output_config.effort` | model-specific | model-specific | invalid |

Rules of thumb:

- Treat any change of thinking mode or top-level effort as starting the cache over. Setting effort explicitly to the model default equals omitting it.
- On models that support per-message effort, an effort change carried in a `role: "system"` message inside `messages` leaves the prefix intact. Mid-conversation system messages are appended at the end and do not invalidate earlier cache.
- Thinking blocks are preserved by default on Opus 4.5 and later Opus, Sonnet 4.6 and later Sonnet, Haiku 5.5 and Fable 5.1; on those models adding a normal user turn keeps the cache valid. On older Opus/Sonnet/Haiku, earlier thinking blocks are stripped and later messages drop out of the cache.
- Changing `output_config.format` (structured outputs) invalidates the prompt cache for that conversation thread.
- Do not edit earlier turns. Append only.
- The API offers cache diagnostics (compare consecutive requests and report where the prefix diverged); see the cache diagnostics page.

## 6. Reading usage

`usage` (and the `message_start` event when streaming) reports:

- `cache_creation_input_tokens`: tokens written to cache.
- `cache_read_input_tokens`: tokens read from cache.
- `input_tokens`: tokens after the last breakpoint only, not the total.
- When 1-hour entries are used, a `cache_creation` object splits 5-minute and 1-hour writes.

Total input = `cache_read_input_tokens` + `cache_creation_input_tokens` + `input_tokens`. Both cache fields at 0 means the prompt was not cached (usually below the minimum length, or a changing breakpoint block).

```python
u = response.usage
total_in = u.input_tokens + (u.cache_creation_input_tokens or 0) + (u.cache_read_input_tokens or 0)
hit_rate = (u.cache_read_input_tokens or 0) / total_in if total_in else 0.0
log.info("llm_usage", extra={"model": response.model, "in": total_in, "out": u.output_tokens, "cache_hit": round(hit_rate, 3)})
```

## 7. One-hour cache and pre-warming

- Use `{"type": "ephemeral", "ttl": "1h"}` for sessions with gaps longer than five minutes, thinking-heavy turns, or shared prefixes hit less often than every five minutes. Mixing TTLs in one request is allowed; a one-hour entry must appear before any five-minute entries in the prompt.
- Pre-warm a cache before a user arrives with `max_tokens=0`: the API processes the prompt, writes the cache at your breakpoints, and returns an empty `content` array with `stop_reason: "max_tokens"` and zero output tokens billed. Put the breakpoint on the last block shared with the real request (system or tools), and use the same thinking and effort configuration. `max_tokens=0` is rejected with streaming, `thinking.type: "enabled"`, `output_config.format`, forced `tool_choice`, and inside Message Batches.

```python
client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=0,
    system=[{"type": "text", "text": LONG_SYSTEM, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": "warm-up"}],
)
```

## 8. Token counting

`client.messages.count_tokens(...)` takes the same inputs as `messages.create` (system, tools, images, PDFs) and returns `input_tokens`. It is an estimate; billing reflects only your content. It rejects server tools, the MCP connector and `url` or `file` sources for image and document blocks (send base64 to count them). Claude 4.7 and later use a newer tokenizer that yields roughly 30 percent more tokens than earlier models for the same text, so recount per model.

```python
count = client.messages.count_tokens(
    model="claude-opus-5-5",
    system=SYSTEM,
    tools=TOOLS,
    messages=[{"role": "user", "content": question}],
)
if count.input_tokens > BUDGET:
    raise ValueError("prompt exceeds budget")
```

TypeScript: `await client.messages.countTokens({ model, system, tools, messages })`.

Uses: guard prompt size, route short prompts to a smaller model, verify a cached prefix is above the minimum length, estimate batch cost before submission.

## 9. Cost levers in order of effect

1. Cache the stable prefix (tools, system prompt, documents, history). Cache reads are a fraction of base input price; the fraction differs by model, so read the pricing page.
2. Lower `output_config.effort`: it scales thinking, tool-call volume and answer length. Hold it constant within a cached conversation.
3. Choose the smallest model that passes your evals (Haiku 5.5 for high-volume simple tasks).
4. Use Message Batches for non-interactive work (discount versus synchronous; see the pricing page).
5. Return compact tool results; clear old tool results or thinking via context editing, or compact long conversations with server-side compaction (beta).
6. Cap `max_tokens` to what the task needs; it is a hard limit that also bounds worst-case spend.
7. Avoid resending large files: upload once with the Files API.

Cost accounting: thinking tokens are billed as output tokens even when `display` is `omitted`, and count toward `max_tokens`.

## 10. Rate limits and caching

- Limits are measured in requests, input tokens and output tokens per minute per model class, enforced as a token bucket at organization level. Short bursts can trigger 429 even below the per-minute average.
- For most models only uncached input counts toward input-tokens-per-minute: `input_tokens` and `cache_creation_input_tokens` count, `cache_read_input_tokens` does not.
- Response headers: `retry-after`, `anthropic-ratelimit-requests-*`, `anthropic-ratelimit-tokens-*`, `anthropic-ratelimit-input-tokens-*`, `anthropic-ratelimit-output-tokens-*` (limit, remaining, reset in RFC 3339). Token remaining values are rounded to the nearest thousand.
- Sharp traffic increases can hit acceleration limits and return 429; ramp traffic gradually.
- Each tier has a monthly spend cap; reaching it returns 429 without `retry-after` and with `error.details.error_code` `enforced_spend_limit_reached`. A spend limit you set yourself returns 400 with a message starting "You have reached your specified API usage limits".
- Batches have their own limits on HTTP requests and queued requests.
