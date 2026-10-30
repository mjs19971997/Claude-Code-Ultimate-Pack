---
name: anthropic-sdk-expert
description: >-
  Builds applications on the Claude API with the official SDKs (Python `anthropic` 2.x, TypeScript `@anthropic-ai/sdk` 1.x): Messages API, streaming, tool use and the tool runner, adaptive thinking and effort, prompt caching, token counting, Message Batches, Files API, structured outputs, error handling, retries and rate limits. Use when writing or reviewing code that calls claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5 or claude-fable-5-1, or when a request fails with a 400, 429, 529 or a thinking, prefill or tool_choice error. Not for provider-neutral prompt wording (use prompt-engineering-expert), OpenAI or Gemini SDK code (use openai-sdk-expert or gemini-sdk-expert), or multi-agent system design (use ai-agent-architect).
license: MIT
metadata:
  version: "3.0.0"
---

# Anthropic SDK Expert

This skill covers calling Claude through the Claude API with the official Python and TypeScript SDKs: request shape, model and parameter choices, tool-use loops, caching, streaming, batch and file workflows, and failure handling. Several parameters taught in older tutorials (`thinking.budget_tokens`, assistant prefill, forced `tool_choice`, `temperature`/`top_k`) are rejected by the current models, so the rules below follow the current documentation, not older habits.

> Verified against the Claude API docs (platform.claude.com), Python SDK `anthropic` 2.3.x (Python 3.10+), TypeScript SDK `@anthropic-ai/sdk` 1.3.x (Node.js 20+), API version `2026-10-21`, models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` (2026-10).

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

- Covered: `client.messages.create` and `.stream`, content blocks, system prompts, adaptive thinking and `output_config.effort`, client tools and the SDK tool runner, strict tool use, structured outputs, prompt caching, token counting, Message Batches, Files API, stop reasons, error classes, retries, timeouts, rate-limit headers, the MCP connector parameter, SDK upgrades (Python 2.x, TypeScript 1.x).
- Not covered: wording and evaluation of prompts (prompt-engineering-expert), architecture of multi-agent systems (ai-agent-architect), building MCP servers (mcp-expert), other vendors' SDKs (openai-sdk-expert, gemini-sdk-expert), cloud-provider setup beyond the client class names.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Model ids | `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`. Every id is a pinned snapshot (dateless ids included). All four list a 1M-token context window and 128K max output tokens; check the models overview before relying on limits |
| Thinking | Adaptive only. Omit `thinking` (adaptive is the default on these models) or send `{"type": "adaptive", "display": "summarized"}`. `{"type": "enabled", "budget_tokens": N}` returns 400 on these models. `display` defaults to `"omitted"` on 5.x models (empty `thinking` text, signature still returned) |
| Effort | `output_config={"effort": "high"}` with one of `low`, `medium`, `high`, `xhigh`, `max`. Default is `medium` on Opus 5.5 and Haiku 5.5, `high` on Sonnet 5.5 and Fable 5.1. Effort is soft guidance; `max_tokens` is the hard cap |
| Thinking off | Opus 5.5 and Fable 5.1 reject `{"type": "disabled"}`. Sonnet 5.5 rejects it too; its lowest setting is `{"type": "between_tools"}`. Haiku 5.5 accepts `disabled` at `high` effort or below |
| Sampling params | `temperature`, `top_p`, `top_k` return 400 on the current models. From API version `2026-10-21` (Python 2.x, TypeScript 1.x SDKs) any value returns 400 on every model and the SDK types no longer have them. Steer with prompts and effort |
| Prefill | A final assistant message (prefill) returns 400 on Claude 4.6 and later. Use structured outputs or system-prompt instructions |
| tool_choice | `auto` (default) and `none` work everywhere. `any` and `tool` return 400 on Opus 5.5, Sonnet 5.5 and Fable 5.1. Use `auto` with `strict: true` tools or `output_config.format` |
| Tools | Client tools run in your code (`stop_reason: "tool_use"`, reply with `tool_result` blocks first in the next user message). Server tools (web search, code execution, web fetch) run on Anthropic infrastructure |
| Tool runner | Beta. Python `client.beta.messages.tool_runner` with `@beta_tool`; TypeScript `client.beta.messages.toolRunner` with `betaZodTool` or `betaTool` |
| Structured outputs | `output_config.format` with a JSON schema; SDK helper `client.messages.parse(..., output_format=PydanticModel)` (Python) or `zodOutputFormat(schema)` (TypeScript). Grammar-constrained, so output matches the schema unless `stop_reason` is `refusal` or `max_tokens` |
| Prompt caching | Top-level `cache_control` (automatic) or `cache_control` on blocks (up to 4 breakpoints). Order is tools, system, messages. Default 5-minute lifetime, `{"type": "ephemeral", "ttl": "1h"}` for one hour. Minimum cacheable prompt is 512 tokens on the 5.x models |
| Batches | `client.messages.batches`: up to 100,000 requests or 256 MB per batch, finishes within 24 hours, results kept 29 days, discounted versus synchronous calls (check the pricing page) |
| Files API | `client.files.upload`, then reference a `file_id` in `document` or `image` blocks. 500 MB per file, workspace-scoped, no beta header |
| Errors | 400, 401, 402, 403, 404, 409, 413, 429, 500, 504, 529; typed SDK exceptions; two automatic retries by default; `request-id` header exposed as `_request_id` |
| Mid-conversation system messages | `{"role": "system"}` entries after a user turn are supported on Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1; they do not invalidate the cached prefix |

## 3. Workflow

1. Pick the model from the task (section 4) and put its id in one config constant; do not scatter literals.
2. Write the smallest request: `model`, `max_tokens`, top-level `system`, `messages`. Leave sampling parameters, `thinking` and `effort` unset until a measurement says otherwise.
3. Parse the response by content block `type` and branch on `stop_reason` (`end_turn`, `max_tokens`, `tool_use`, `refusal`, `pause_turn`, `model_context_window_exceeded`).
4. If the request is long (large `max_tokens`, thinking at high effort, big inputs), stream it and take `get_final_message()` / `finalMessage()`.
5. Add tools: precise descriptions, `strict: true` on tools whose inputs feed code, the manual loop or the tool runner, an iteration cap.
6. Add caching: stable content first, breakpoint on the last block that is identical across requests, then read `usage.cache_read_input_tokens` to confirm hits.
7. Add error handling: catch the SDK's typed exceptions, keep default retries, log `_request_id`, treat 400s as bugs to fix, not to retry.
8. For bulk work that is not interactive, move to Message Batches; for large reusable inputs, use the Files API.
9. Before shipping, run section 12 and a gated live smoke test against the cheapest suitable model.

## 4. Decision Rules

- Model: start with `claude-opus-5-5` for most workloads per the docs; `claude-fable-5-1` for demanding reasoning and long-horizon agent work, or when Opus 5.5 at higher effort still fails your evals; `claude-sonnet-5-5` for speed and quality balance; `claude-haiku-5-5` for high-volume, latency-sensitive classification, extraction and routing. Decide by evals on your data, and see the pricing page for costs.
- Reduce cost or latency: lower `effort` first, then pick a smaller model, then cache, then batch. Do not try to lower `temperature`; it is rejected.
- Need schema-valid JSON: use `output_config.format` (final answer) or `strict: true` tools (tool inputs). Do not prefill and do not force a tool on models that reject it.
- Need a tool to run on every turn: describe when to call it in the system prompt with `tool_choice: {"type": "auto"}`; if the model must produce one specific object, use structured outputs instead.
- Streaming vs not: stream when output may be long or users watch it. The SDKs refuse non-streaming requests expected to exceed roughly 10 minutes (the docs state streaming is required above `max_tokens` 21,333); batches suit anything above about 32k thinking-heavy tokens per request.
- Cache lifetime: 5 minutes when requests repeat within minutes; `ttl: "1h"` for agent sessions or thinking-heavy turns that pause longer; neither when each prompt is unique.
- Sync vs batch: batch when no one waits for the answer and a few hours is acceptable; synchronous otherwise.
- SDK major: new projects use Python `anthropic` 2.x and `@anthropic-ai/sdk` 1.x. Staying on older majors keeps API version `2023-06-01` and the old sampling parameters, and is only worth it for models that accept them.
- Thinking display: set `display: "omitted"` when the UI does not show reasoning (faster first text token when streaming); `"summarized"` when you show or log it.

## 5. Coding Standards

- Construct one client per process and reuse it: `anthropic.Anthropic()` / `anthropic.AsyncAnthropic()` / `new Anthropic()`. Use the async client inside async code; a sync call blocks the event loop.
- Read the key from `ANTHROPIC_API_KEY` (the default) or a secret manager; never from source files. A client holds one credential: passing both `api_key` and `auth_token` raises in the 2.x/1.x SDKs.
- Always set `max_tokens`; size it for thinking plus the answer, because thinking tokens count toward it.
- Pass instructions in the top-level `system` parameter (string or text blocks), not as a `{"role": "system"}` first message.
- Iterate `response.content` blocks by `block.type`; never assume `content[0]` is text (thinking blocks and tool_use blocks come first).
- Send assistant turns back exactly as received, including `thinking` and `redacted_thinking` blocks. Edited, reordered or dropped thinking blocks in the latest assistant turn return 400.
- Do not send `temperature`, `top_p`, `top_k`, `budget_tokens` or a final assistant message to the current models.
- Keep tool definitions and their JSON key order stable between requests; reordering breaks cache prefixes.
- Use SDK helpers (`messages.stream`, `messages.parse`, tool runner) before hand-rolling SSE parsing or JSON repair.
- Type models as constants or an enum in one module; log the model id with every request.

## 6. Project Structure

```
.
├── pyproject.toml              # anthropic>=2,<3 (or package.json: @anthropic-ai/sdk ^1)
├── src/app/
│   ├── llm/
│   │   ├── client.py           # one shared client, timeouts, max_retries, base_url
│   │   ├── models.py           # model id constants, effort defaults per task
│   │   ├── prompts/            # system prompts as files, versioned
│   │   ├── tools/              # tool schemas + handlers, one module per tool group
│   │   ├── loop.py             # tool loop with iteration cap and stop_reason handling
│   │   └── errors.py           # mapping of SDK exceptions to app errors
│   ├── batch/                  # batch builders and result readers (custom_id scheme)
│   └── api/                    # HTTP layer; streams events to browsers, never holds the key client-side
└── tests/
    ├── fakes.py                # fake LLM gateway returning canned content blocks
    ├── fixtures/               # recorded response JSON (tool_use, thinking, refusal)
    └── live/                   # opt-in smoke tests, skipped without ANTHROPIC_API_KEY
```

## 7. Design Patterns

- **LLM gateway**: one module owns the client, retries, logging and usage accounting; the rest of the code calls `complete()` / `stream()` with domain types.
- **Manual agent loop**: call, append `response.content` as the assistant turn, run every `tool_use`, append one user message of `tool_result` blocks, repeat until `stop_reason != "tool_use"` or the iteration cap is hit. Details in [references/tool-use.md](references/tool-use.md).
- **Tool runner**: let the SDK run the loop when no custom approval, logging or conditional execution is needed.
- **Cache-first prompt layout**: tools, then a long static system prompt and reference documents, breakpoint, then the volatile per-request part. See [references/prompt-caching-and-cost.md](references/prompt-caching-and-cost.md).
- **Extraction with a schema**: `messages.parse` with a Pydantic or Zod type; check `stop_reason` before trusting the parsed object.
- **Batch pipeline**: build requests with a deterministic `custom_id`, submit, poll `processing_status == "ended"`, stream results, resubmit only `errored` and `expired` entries. See [references/batches-and-files.md](references/batches-and-files.md).
- **Router and worker**: a `claude-haiku-5-5` classification call chooses the prompt or model for the expensive call.
- **Streaming relay**: server streams text deltas to the browser over SSE or WebSocket; the key stays on the server.

## 8. Best Practices

- Keep prompts in files, version them, and put dates and per-request data after the cache breakpoint.
- Write tool descriptions as documentation: what it does, when to use it and when not to, what each parameter means, what it returns. The docs call this the most important factor in tool quality. Prefer fewer, consolidated tools with namespaced names.
- Return only high-signal fields from tools (stable ids, not opaque internals); cap result size.
- Report tool failures with `is_error: true` and a message the model can act on; do not return error text as a normal result.
- Return exactly one `tool_result` per `tool_use` block, all in the next user message, with `tool_result` blocks before any text.
- Handle `max_tokens` (raise the limit or continue), `refusal` (read `stop_details`, fall back or surface), and `pause_turn` (send the response back to continue).
- Keep conversation state append-only. Editing earlier turns invalidates the cache and, on Claude 5.1 and later models, can invalidate thinking blocks sent back.
- Use `client.messages.count_tokens` for budgeting and routing; treat the count as an estimate. Claude 4.7 and later use a newer tokenizer that produces roughly 30 percent more tokens for the same text than older models, so recount per model.
- Set `max_retries` and `timeout` explicitly in production clients; keep retries on for 429 and 5xx.

## 9. Performance

- Prompt caching is the largest lever on repeated prefixes: cache reads cost a fraction of base input (the fraction is per model; check the pricing page) and, for most models, cache reads do not count toward input-tokens-per-minute limits.
- Lower `effort` to cut thinking and tool-call volume; hold effort constant inside a cached conversation, since changing it (or the thinking configuration) starts a new cache prefix. Per-message effort changes via system messages preserve the cache on models that support them.
- Stream to cut time to first token; with `display: "omitted"` the server skips streaming thinking text.
- Parallelize independent tool calls (`asyncio.gather` / `Promise.all`) when they are read-only; keep side-effecting calls sequential.
- Bound concurrency with a semaphore and honor `retry-after`; the API uses token-bucket limits, so bursts above the bucket 429 even when the average is fine.
- Pre-warm a cache before a user arrives with `max_tokens: 0` (not allowed with streaming, structured outputs, forced tools or inside batches).
- Use Batches for offline volume; use the Files API instead of re-uploading the same document.
- For long-running agent contexts, use server-side compaction or context editing (both beta; check the docs for headers) instead of client-side summarizers.

## 10. Security

- API keys belong on servers only. The TypeScript SDK refuses browser use unless `dangerouslyAllowBrowser` is set; do not set it in shipped front-end code. Proxy through your backend.
- Never log keys or full Authorization headers. The 2.x/1.x SDKs send the key as `Authorization: Bearer`; update gateways, log filters and stubs that read `X-Api-Key`.
- Treat everything inside tool results, retrieved documents and user uploads as untrusted data (indirect prompt injection). Keep it inside `tool_result` blocks, not in `system`, and restrict what tools can do.
- Validate tool inputs in your handler even with `strict: true`: strict guarantees schema shape, not that the caller may access that record. Check authorization on the server for every tool call, including `tenant_id` filters on writes as well as reads.
- Require human confirmation for destructive or irreversible tools; apply least privilege to credentials the tools use.
- Files uploaded to the Files API are visible to every key in the workspace. Never accept a `file_id` from an end user; use one workspace per tenant for isolation.
- Cap loop iterations, tool output size and `max_tokens` to bound spend from runaway or injected loops; set a workspace spend limit in the Console.
- Do not log full prompts or completions when they contain personal data; log `_request_id`, model, token usage and stop reason.
- Keep thinking text out of end-user views unless intended; ask tools for short explanations, not "your reasoning", since a `reasoning_extraction` refusal can result.

## 11. Testing

- Hide the SDK behind a narrow gateway interface and unit-test business logic with a fake that returns canned content blocks, including `tool_use`, `thinking`, `refusal` and `max_tokens` cases.
- Replay recorded response JSON as fixtures to test loop code; assert that assistant content is passed back unmodified and every `tool_use` gets a matching `tool_result`.
- Test error mapping with a mocked HTTP layer (Python: pass an `httpx2` client via `http_client`; TypeScript: pass a custom `fetch`). Cover 400, 401, 429 with and without `retry-after`, 529 and connection errors.
- Assert request shape, not model text: required `max_tokens`, no sampling parameters, `system` at top level, stable tool order.
- Run live smoke tests only when `ANTHROPIC_API_KEY` is set, on the cheapest suitable model, with tiny `max_tokens`; never in default CI.
- Use `count_tokens` in tests to guard against prompts growing past budgets or below the minimum cacheable length.
- Evaluate model changes with a fixed eval set before switching model ids; effort and model defaults differ per model.

## 12. Review Checklist

- [ ] Model id comes from config; one of the current ids, not a retired one.
- [ ] `max_tokens` set; response parsed by block type; `stop_reason` handled.
- [ ] No `temperature`, `top_p`, `top_k`, `thinking.budget_tokens`, prefill, or forced `tool_choice` on models that reject them.
- [ ] Thinking blocks round-tripped unmodified in tool loops.
- [ ] Tool results: one per `tool_use`, results first, `is_error` used, output size capped, loop capped.
- [ ] Cache breakpoint on the last stable block; prompt above the minimum length; `cache_read_input_tokens` observed.
- [ ] Long requests stream; timeouts and `max_retries` set intentionally.
- [ ] Errors: typed exceptions caught, `_request_id` logged, 400s not retried blindly, spend-cap 429 recognized.
- [ ] Key only on the server; no key in front-end bundles, logs or VCS.
- [ ] Untrusted content stays in tool results; tool handlers re-check authorization; writes are tenant-scoped.
- [ ] Tests cover fake gateway, fixtures and a gated live smoke test.

## 13. Production Notes

- Models retire on a published schedule (see the model deprecations page); pin ids, subscribe to deprecation notices, and plan migrations with evals. The models overview lists the earliest retirement date for each current model.
- Rate limits are per organization and model class: requests, input tokens and output tokens per minute. Read the `anthropic-ratelimit-*` response headers and `retry-after`; request higher limits through the Console when needed.
- A 429 without `retry-after` and with `error.details.error_code` of `enforced_spend_limit_reached` means a spend cap: retries (including the SDK's) fail until access resumes or limits change. A spend limit you set yourself returns 400 instead.
- 529 means overloaded: retry with backoff, and consider a fallback model for user-facing paths. Streaming responses can carry an error event after a 200 status; handle it.
- Interrupted streams cannot be resumed from an event id. On Claude 4.6 and later, continue by sending a new user message containing the partial text and an instruction to continue; tool_use and thinking blocks cannot be partially recovered.
- Cloud platforms (Amazon Bedrock, Google Cloud, Microsoft Foundry, Claude Platform on AWS) use their own client classes and, in some cases, different model ids and feature sets; check the platform page before copying API-direct code.
- Python 2.x uses `httpx2` (not `httpx`) and the operating-system trust store for TLS; minimal containers need CA certificates or `SSL_CERT_FILE`.
- Upgrading from Python 1.x or TypeScript 0.x: change `anthropic-version` assumptions, remove sampling parameters, update proxies that read `X-Api-Key`, and follow the API-version migration guide.
- Check the pricing page for token and cache prices; never hard-code prices in code.

## 14. Examples

Manual tool loop with a cached prefix, strict tool, iteration cap and error reporting (Python, async):

```python
import json
import anthropic

client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
MODEL = "claude-sonnet-5-5"
SYSTEM = "You are a support assistant. Use tools for order data. ..."  # keep above 512 tokens to be cacheable

TOOLS = [
    {
        "name": "get_order_status",
        "description": (
            "Look up the shipping status of one order by id. Use it whenever the user asks "
            "where an order is. Returns JSON with status and carrier. Does not modify the order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order id, e.g. A-10293"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


async def run_tool(name: str, args: dict, tenant_id: str) -> tuple[str, bool]:
    if name == "get_order_status":
        # Re-check that this tenant may read this order before returning anything.
        return json.dumps({"order_id": args["order_id"], "status": "shipped"}), False
    return f"Unknown tool: {name}", True


async def answer(question: str, tenant_id: str) -> str:
    messages = [{"role": "user", "content": question}]
    for _ in range(8):  # hard cap on loop iterations
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
            cache_control={"type": "ephemeral"},  # automatic caching; breakpoint moves forward
        )
        messages.append({"role": "assistant", "content": response.content})  # unmodified
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output, is_error = await run_tool(block.name, block.input, tenant_id)
                results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output, "is_error": is_error}
                )
        messages.append({"role": "user", "content": results})  # tool_result blocks only, one per call
    raise RuntimeError("tool loop exceeded iteration cap")
```

Streaming with typed error handling (TypeScript):

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ maxRetries: 2, timeout: 5 * 60 * 1000 });

export async function summarize(text: string, onText: (t: string) => void): Promise<string> {
  try {
    const stream = client.messages
      .stream({
        model: "claude-haiku-5-5",
        max_tokens: 2048,
        system: "Summarize the user's text in five bullet points.",
        messages: [{ role: "user", content: text }]
      })
      .on("text", onText);
    const message = await stream.finalMessage();
    if (message.stop_reason === "max_tokens") {
      console.warn("summary truncated", message._request_id);
    }
    return message.content.flatMap(b => (b.type === "text" ? [b.text] : [])).join("");
  } catch (err) {
    if (err instanceof Anthropic.RateLimitError) {
      throw new Error("Rate limited; retry later"); // SDK already retried twice
    }
    if (err instanceof Anthropic.APIError) {
      console.error("Claude API error", err.status, err.name);
    }
    throw err;
  }
}
```

Structured extraction with a Pydantic model (Python):

```python
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic()


class Contact(BaseModel):
    name: str
    email: str
    wants_demo: bool


response = client.messages.parse(
    model="claude-haiku-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Extract the contact: Ana Ruiz (ana@example.com) asked for a demo."}],
    output_format=Contact,
)
if response.stop_reason in ("refusal", "max_tokens"):
    raise RuntimeError(f"no valid structured output: {response.stop_reason}")
contact = response.parsed_output  # a Contact instance
```

## 15. Common Mistakes

- **`thinking={"type": "enabled", "budget_tokens": ...}`**: 400 on Claude 4.7 and later, including all four current models. Use adaptive thinking (default) and `output_config.effort`.
- **Passing `adaptive` as an effort value**: `adaptive` is a thinking mode; effort levels are `low`, `medium`, `high`, `xhigh`, `max`.
- **`thinking={"type": "disabled"}` on Opus 5.5, Sonnet 5.5 or Fable 5.1**: 400. Lower effort instead; Sonnet 5.5 offers `between_tools`.
- **Setting `temperature` or `top_k` "for determinism"**: 400 on current models, and removed from the 2.x/1.x SDKs. Reduce variance with clearer prompts and structured outputs.
- **Assistant prefill to force JSON or a prefix**: 400 on Claude 4.6 and later. Use `output_config.format`.
- **`tool_choice: {"type": "tool", ...}` on Opus 5.5, Sonnet 5.5, Fable 5.1**: 400. Use `auto` plus `strict: true`.
- **Dropping or editing thinking blocks when resending history**: 400 in tool turns and a broken prefix check on 5.1 models. Append-only history.
- **Text before `tool_result` blocks, or a missing result for a `tool_use` id**: 400 ("tool_use ids were found without tool_result blocks").
- **Reading `response.content[0].text`**: crashes when the first block is thinking or tool_use.
- **Retrying every 400**: validation errors do not fix themselves. Retry 429, 5xx, 529 and connection errors only; the SDK already does.
- **Treating `input_tokens` as total input with caching**: it counts only tokens after the last breakpoint; add cache read and creation tokens.
- **Breakpoint on a block that changes every request** (timestamp, user message): never reads from cache. Put it on the last stable block.
- **Large `max_tokens` without streaming**: the SDK raises or the connection drops. Use `.stream()` with `get_final_message()`.
- **Accepting a `file_id` from the client**: any workspace key can read any workspace file. Map your own ids server-side.
- **Putting the API key in a browser bundle** (`NEXT_PUBLIC_*`, `dangerouslyAllowBrowser`): exposes the key. Proxy through a backend.
- **Hard-coding prices or model limits in code**: they change; read the pricing page and the Models API (`max_input_tokens`, `capabilities`).

## 16. References

- [references/tool-use.md](references/tool-use.md): tool definitions, manual loop formatting rules, forced tool use per model, strict tools, the tool runner in Python and TypeScript, thinking with tools, MCP connector, prompt-injection handling.
- [references/prompt-caching-and-cost.md](references/prompt-caching-and-cost.md): automatic and explicit breakpoints, TTLs, lookback window, invalidation table, usage fields, pre-warming, token counting, effort and cost levers, rate-limit accounting.
- [references/streaming-and-errors.md](references/streaming-and-errors.md): streaming helpers and event flow, thinking deltas, error classes and HTTP codes, retries and timeouts, stop reasons, rate-limit headers, SDK upgrade notes.
- [references/batches-and-files.md](references/batches-and-files.md): Message Batches lifecycle, result handling, the Files API, structured output schema limits.
- Official docs: https://platform.claude.com/docs/en/about-claude/models/overview , https://platform.claude.com/docs/en/api/errors , https://platform.claude.com/docs/en/build-with-claude/thinking , https://platform.claude.com/docs/en/build-with-claude/prompt-caching , https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview , https://github.com/anthropics/anthropic-sdk-python , https://github.com/anthropics/anthropic-sdk-typescript
