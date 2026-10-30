# Streaming and Errors

Reference for streaming, stop reasons, error handling, retries, timeouts and SDK upgrade notes. Verified against the Claude API docs, Python SDK `anthropic` 2.3.x and TypeScript SDK `@anthropic-ai/sdk` 1.3.x, API version `2026-10-21`, models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` (2026-10).

## 1. Streaming with the SDKs

Two forms exist in both SDKs.

- Helper with accumulation: Python `client.messages.stream(...)` as a context manager; TypeScript `client.messages.stream({...})` with `.on("text", cb)` and `await stream.finalMessage()`.
- Raw events: `client.messages.create(..., stream=True)` (Python) or `{ stream: true }` (TypeScript) returns an iterable of events and uses less memory because it does not build the final message.

```python
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-opus-5-5",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Explain TCP slow start in one paragraph."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final = stream.get_final_message()  # full Message, identical to a non-streaming result

print(final.stop_reason, final.usage.output_tokens, final._request_id)
```

Async: `async with client.messages.stream(...) as stream:` then `async for text in stream.text_stream:` and `await stream.get_final_message()`.

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const stream = client.messages
  .stream({
    model: "claude-opus-5-5",
    max_tokens: 4096,
    messages: [{ role: "user", content: "Explain TCP slow start in one paragraph." }]
  })
  .on("text", text => process.stdout.write(text));
const final = await stream.finalMessage();
console.log(final.stop_reason, final.usage.output_tokens);
```

To cancel a raw TypeScript stream, `break` out of the `for await` loop or call `stream.controller.abort()`.

When you do not need incremental output but the request is long, still use the stream helper and take the final message: the SDKs refuse non-streaming requests expected to run longer than about 10 minutes (the docs state streaming is required when `max_tokens` exceeds 21,333), and idle connections can be dropped by networks. Messages above roughly 32k thinking tokens belong in Message Batches.

## 2. Event flow and delta types

Order of events in one stream:

1. `message_start`: a `Message` with empty `content`; `usage` starts here (cache fields appear here).
2. For each content block: `content_block_start`, one or more `content_block_delta`, `content_block_stop`. Each block has an `index` matching the final `content` array.
3. One or more `message_delta`: top-level changes such as `stop_reason`; its `usage` token counts are cumulative.
4. `message_stop`.

`ping` events can appear anywhere. New event types may be added; ignore unknown types. An error can arrive as an `error` event after a 200 response (for example `overloaded_error`); handle it separately from HTTP errors.

Delta types:

- `text_delta`: `text`.
- `input_json_delta`: partial JSON string for a `tool_use` block's `input`. Accumulate strings and parse at `content_block_stop`, or use the SDK helpers that expose parsed input incrementally. Tool inputs stream one complete key and value at a time, so pauses between events are normal.
- `thinking_delta` then a `signature_delta` just before `content_block_stop`. With `display: "omitted"` the block opens, receives an empty `thinking_delta` and one `signature_delta`, and closes; no thinking text streams, which lowers time to first text token.

Interrupted streams: there is no resume by event id. Keep the partial text received so far. For Claude 4.6 and later, start a new request whose last message is a user message containing the partial output and an instruction to continue from where it stopped (a partial assistant message is prefill and is rejected). `tool_use` and `thinking` blocks cannot be partially recovered; resume from the last complete text block.

## 3. Stop reasons

| `stop_reason` | Meaning | Action |
|---|---|---|
| `end_turn` | Natural end | Use the response |
| `max_tokens` | Hit `max_tokens` (thinking counts toward it) | Raise the limit or ask Claude to continue; structured output may be incomplete |
| `stop_sequence` | One of your `stop_sequences` fired | Read `stop_sequence` |
| `tool_use` | Client tool call requested | Run tools, send `tool_result` blocks |
| `pause_turn` | Server-tool loop hit its iteration limit | Send the assistant content back unchanged to continue |
| `refusal` | Safety classifier declined (HTTP 200) | Read `stop_details`; retry on a fallback model or surface a message; tokens are billed |
| `model_context_window_exceeded` | Response filled the context window | Treat as truncated |

Always branch on `stop_reason`; a 200 status does not mean a complete answer.

## 4. HTTP errors and SDK exceptions

| Status | `error.type` | Meaning and handling |
|---|---|---|
| 400 | `invalid_request_error` | Malformed or unsupported request; also user-set spend limit reached. Fix the request; do not retry |
| 401 | `authentication_error` | Missing, malformed, revoked or expired key |
| 402 | `billing_error` | Billing or payment problem |
| 403 | `permission_error` | Key lacks access to the resource |
| 404 | `not_found_error` | Wrong path, model id or resource id |
| 409 | `conflict_error` | Concurrent modification or unique-value conflict; resolve and retry |
| 413 | `request_too_large` | Over 128 MB (Messages, token counting), 256 MB (Batches), 500 MB (Files) |
| 429 | `rate_limit_error` | Rate limit, acceleration limit, or spend cap. Use `retry-after` when present; spend-cap 429s have none and keep failing |
| 500 | `api_error` | Server error; retry with backoff |
| 504 | `timeout_error` | Request timed out; stream long requests |
| 529 | `overloaded_error` | Temporarily overloaded; retry with backoff, consider fallback |

Error bodies have a top-level `error` object with `type` and `message` plus a `request_id`. Every response has a `request-id` header; the SDK objects expose it as `_request_id`. Include it in support tickets.

SDK classes (Python names; TypeScript uses `Anthropic.<Name>`): `APIConnectionError` (no response), `APITimeoutError` (TypeScript: `APIConnectionTimeoutError`), `BadRequestError` 400, `AuthenticationError` 401, `PermissionDeniedError` 403, `NotFoundError` 404, `ConflictError` 409, `UnprocessableEntityError` 422, `RateLimitError` 429, `InternalServerError` for status 500 and above, all under `APIStatusError` / `APIError`. Catch the most specific class first; do not string-match messages.

```python
import logging
import anthropic

log = logging.getLogger("llm")


def call(client: anthropic.Anthropic, **params):
    try:
        return client.messages.create(**params)
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after")
        log.warning("rate limited request_id=%s retry_after=%s", e.response.headers.get("request-id"), retry_after)
        raise  # SDK already retried twice; surface a 503 or enqueue for later
    except anthropic.BadRequestError as e:
        log.error("invalid request status=%s body=%s", e.status_code, e.body)  # a bug: fix the request
        raise
    except anthropic.APIConnectionError as e:
        log.warning("network problem: %s", e.__cause__)
        raise
    except anthropic.APIStatusError as e:
        log.error("api error status=%s", e.status_code)
        raise
```

## 5. Retries, timeouts, long requests

- Retried by default, twice, with short exponential backoff, honoring `retry-after`: connection errors, 408, 409, 429 and 5xx. Configure with `max_retries` / `maxRetries`, on the client or per request (`client.with_options(max_retries=5)`; TypeScript second argument `{ maxRetries: 5 }`; `0` disables).
- Default timeout is 10 minutes. The TypeScript SDK scales the default for large non-streaming `max_tokens` (up to 60 minutes) unless you set `timeout`. Python raises `ValueError` and TypeScript throws an error for non-streaming requests expected to exceed roughly 10 minutes; passing `stream=True` or an explicit timeout disables that check.
- On timeout Python raises `APITimeoutError`, TypeScript `APIConnectionTimeoutError`; timed-out requests are retried twice by default, so a request that cannot finish within the timeout will be sent three times. Stream long work instead.
- The SDKs set TCP keep-alive to reduce idle-connection drops.
- Application-level retries on top of the SDK multiply: keep a single layer, or set `max_retries=0` and own the policy (with jitter and a total deadline).
- A 429 without `retry-after` and with `error.details.error_code == "enforced_spend_limit_reached"` is a spend cap: stop retrying, alert, and raise limits.

## 6. Client configuration that matters

- Python: `anthropic.Anthropic(api_key=None, max_retries=2, timeout=600.0, base_url=None, default_headers=None, http_client=None)`; `DefaultHttpxClient` / `DefaultAsyncHttpxClient` keep SDK defaults when you supply proxies or transports. Python 2.x uses `httpx2`; a plain `httpx` client raises `TypeError`. Tracing or mocking tools that patch `httpx` need `httpx2.alias_httpx()` at startup.
- TypeScript: `new Anthropic({ apiKey, maxRetries, timeout, baseURL, fetch, fetchOptions })`; per-request options (`signal`, `timeout`, `maxRetries`) are the second argument. Runtimes: Node.js 20+, Deno, Bun, Cloudflare Workers, Vercel Edge; browsers need `dangerouslyAllowBrowser` and should not hold real keys.
- Logging: set `ANTHROPIC_LOG=debug` (Python, TypeScript, Java) for request and response detail; never enable debug logging with real prompts in production.
- OpenTelemetry: both SDKs emit a span per call once a tracer provider is registered; prompt and completion content is off by default and enabled through the client `open_telemetry` / `openTelemetry` option or `ANTHROPIC_OPEN_TELEMETRY_*` environment variables.
- Cloud variants: `AnthropicBedrock`, `AnthropicBedrockMantle`, `AnthropicVertex`, `AnthropicFoundry`, `AnthropicAWS` (Python extras such as `anthropic[bedrock]`, `anthropic[vertex]`, `anthropic[aws]`); model ids and feature support differ per platform.

## 7. SDK and API version upgrade notes

- Python `anthropic` 2.0 and TypeScript `@anthropic-ai/sdk` 1.0 are the first majors to send API version `2026-10-21` (set the `anthropic-version` header yourself when calling without an SDK).
- Breaking changes at `2026-10-21`: `temperature`, `top_p`, `top_k` return 400 at any value on every model and are removed from SDK types; `document` blocks in assistant messages and `citations` on text blocks in user messages return 400; Admin API fields renamed.
- SDK changes: `MessageParam` is a union of per-role types (`UserMessageParam`, `AssistantMessageParam`, `SystemMessageParam`); calling or subclassing the old name raises `TypeError` in Python (dict literals still work); API keys are sent as `Authorization: Bearer` (proxies reading `X-Api-Key` need updating, or send the header yourself via default headers); a client holds exactly one credential (`api_key`, `auth_token`, `credentials`, `config` or `profile`; passing two raises); Text Completions removed from the TypeScript SDK; `compactionControl` removed from the TypeScript tool runner (use server-side compaction).
- Files API: out of beta; use `client.files`, not `client.beta.files`, and no `files-api-2025-04-14` header (still accepted, but returns older response shapes).
- On Amazon Bedrock, API version `2026-10-21` applies only to Claude 4.7 and later; older models there stay on older SDK versions.
- Python 1.x projects upgrading from 0.x have their own migration guide; read it before jumping two majors.
