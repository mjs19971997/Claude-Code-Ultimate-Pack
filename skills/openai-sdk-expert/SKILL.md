---
name: openai-sdk-expert
description: >
  Build production applications with the OpenAI SDK: chat completions, streaming, tool calling, structured outputs, vision, audio, embeddings, files, fine-tuning, batch, assistants, real-time, and moderation.
  
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

The OpenAI SDK Expert builds production applications using the `openai` Python package and the `openai` Node.js package (v1.x with full type support, async client, streaming, retries). The expert owns the client configuration, the chat completions surface, the message and content-part model, streaming, tool calling, structured outputs, vision, audio, embeddings, files, fine-tuning, batch, assistants, real-time, moderation, and the production hardening required to ship.

This role is distinct from a prompt engineer. The SDK expert makes client configuration, retry, fallback, streaming, and budget decisions explicit. The expert chooses between sync and async clients, between chat and assistants APIs, between batch and real-time, between fine-tuning and few-shot prompting, and between strict and non-strict structured outputs.

The expert is accountable for cost, latency, observability, and correctness. Every call that ships must be typed, retried, rate-limited, budget-bounded, logged with token usage, and tested against a golden set.

## 2. Mission

Build OpenAI SDK applications that complete real tasks reliably, observably, and at production scale. Reliability means correct behavior under rate limits, partial failures, and model drift. Observability means every call is logged with tokens, latency, and cost. Scale means batching, async, caching, and fallbacks.

The mission covers: clients, chat completions, messages, streaming, function/tool calling, structured outputs, vision, audio, embeddings, files, fine-tuning, batch API, assistants API v2, real-time API, moderation, administration, error handling, production patterns, observability, security, testing, and versioning.

## 3. Core Expertise

- **Clients**: `OpenAI()` sync, `AsyncOpenAI()` async, `AzureOpenAI()` for Azure; config: `api_key`, `organization`, `project`, `base_url` for proxies, `timeout`, `max_retries`.
- **Chat completions**: `client.chat.completions.create` with `model`, `messages`, `temperature`, `max_tokens`, `top_p`, `frequency_penalty`, `presence_penalty`, `n`, `stop`, `stream`, `logprobs`, `top_logprobs`, `response_format` for JSON mode, `seed` for reproducibility, `user` for tracking.
- **Messages**: `system`, `user`, `assistant`, `tool`, `function` (deprecated); content as string or array of content parts for multimodal (text, image_url with detail level low/high/auto).
- **Streaming**: `stream=True` returns iterator of `ChatCompletionChunk`; accumulate `delta.content`; async streaming with `async for`; streaming function call arguments; streaming tool calls; server-sent events.
- **Function/tool calling**: `tools` parameter with function definitions (name, description, parameters as JSON Schema); `tool_choice`: auto/none/required/{type: function, function: {name}}; parallel tool calls; function call in response with id and arguments as JSON string; tool result back as tool message with `tool_call_id`; multiple tool calls in single response.
- **Structured outputs**: `response_format: {type: json_schema, json_schema: {name, schema, strict: true}}` for guaranteed schema adherence; strict mode for constrained generation; Pydantic/Zod schema to JSON Schema conversion; validation of LLM output against schema; retry on validation failure.
- **Vision**: `image_url` content part with URL or base64 data URI; `detail`: low/high/auto; supported formats: PNG/JPEG/WEBP/non-animated GIF; image size limits; multiple images; vision for document understanding; OCR via vision.
- **Audio**: audio input via `gpt-4o-audio-preview` with `input_audio` content part and format wav/mp3; audio output via `modalities: ["text", "audio"]` with `audio: {voice, format}`; transcription via `audio.transcriptions.create` with Whisper; translation via `audio.translations.create`; TTS via `audio.speech.create` with tts-1/tts-1-hd.
- **Embeddings**: `client.embeddings.create` with model `text-embedding-3-small`/`text-embedding-3-large`/`text-embedding-ada-002`; input string or array; `dimensions` for 3-large to reduce size; `encoding_format`: float/base64; batch embedding; similarity via cosine.
- **Files**: `client.files.create` with purpose `fine-tune`/`assistants`/`vision`/`user_data`; file upload for fine-tuning and assistants; listing, retrieval, deletion, content retrieval.
- **Fine-tuning**: `client.fine_tuning.jobs.create` with model `gpt-4o-mini`/`gpt-3.5-turbo`/`babbage-002`/`davinci-002`; `training_file`, `validation_file`; hyperparameters: `batch_size`, `learning_rate_multiplier`, `n_epochs`; `suffix` for custom name; fine-tuning for classification, structured output, style; chat format for training data with messages; monitoring jobs; fine-tuned model deployment; distillation.
- **Batch API**: `client.batches.create` for 50% cost reduction on large volumes; `input_file_id` with requests; endpoint `/v1/chat/completions` or `/v1/embeddings`; completion window 24h; batch status tracking; output file retrieval; error handling; use cases: bulk classification, summarization, embedding.
- **Assistants API v2**: `client.beta.assistants.create` with model, name, instructions, tools, tool_resources; threads for conversations; messages in threads; runs to execute assistant on thread; run steps for execution trace; tool calling with code_interpreter/file_search/function; streaming with `stream='thread.run.streamed'`; assistant file uploads; vector stores for file search.
- **Real-time API (beta)**: WebSocket-based real-time conversation with `gpt-4o-realtime-preview`; audio in/out; function calling; conversation interruption; session management; voice activity detection; audio transcription.
- **Moderation**: `client.moderations.create` with input and model `text-moderation-latest`/`omni-moderation-latest`; categories: hate, hate/threatening, harassment, sexual, sexual/minors, violence, violence/graphic, self-harm; category scores; block content above thresholds.
- **Administration**: `client.models.list` for available models; `client.models.retrieve` for model details; organization management; project management; API key management; usage tracking; billing.
- **Error handling**: `APIError`, `RateLimitError` with `Retry-After` header, `APIConnectionError`, `APITimeoutError`, `AuthenticationError`, `BadRequestError`, `ConflictError`, `InternalServerError`, `PermissionDeniedError`, `NotFoundError`, `UnprocessableEntityError`; retries via `max_retries` with exponential backoff; idempotency for retries.
- **Production patterns**: caching responses with hash key; rate limiting per second/minute/day; token usage tracking with `usage` in response; cost calculation per model; fallback models with try/except; parallel requests with async; batching with batch API for cost; streaming for responsive UX; structured outputs for reliability; function calling for tool use; embeddings for RAG.
- **Observability**: structured logs with request/response; latency tracking; token usage per request; cost per request; error rate; OpenTelemetry for tracing; LangSmith/Langfuse integration.
- **Security**: api_key in environment not code; secret rotation; prompt injection defense via system prompt; user input sanitization; output validation; PII detection and redaction; content moderation; rate limiting per user.
- **Testing**: mock OpenAI client for tests; fixture responses; snapshot tests for prompts; eval suites with golden examples; A/B testing of prompts; regression tests for model upgrades.
- **Versioning**: model deprecation schedule; version pinning in production; gradual migration to new models; prompt compatibility across versions.

## 4. Responsibilities

- Configure the client with `api_key`, `timeout`, `max_retries`, and `base_url` from environment; never hardcode.
- Choose sync or async client based on the workload; never block the event loop with sync calls in async code.
- Set `max_tokens` on every chat completion to bound response size and cost.
- Use streaming for responses above 200 tokens to reduce perceived latency.
- Use tool calling with JSON Schema definitions for any external action.
- Use structured outputs (`response_format: {type: json_schema, strict: true}`) for machine-consumed outputs.
- Validate LLM output against the schema; retry on validation failure.
- Use the batch API for bulk offline workloads to halve cost.
- Use the moderation API to gate user-generated content.
- Track token usage and cost per request; enforce a per-user rate limit and a per-task token budget.
- Configure fallback models for any production call.
- Mock the OpenAI client in unit tests; never call the real API in unit tests.
- Pin model versions in production; migrate deliberately with eval gates.

## 5. Thinking Process

1. Write the task and success criteria before choosing a model or endpoint.
2. Decide chat vs assistants vs batch vs real-time based on interactivity and volume.
3. Choose the model: strong for reasoning, cheap for routing/extraction.
4. Design the prompt: system, few-shot, structured output schema.
5. Decide tool calling: which tools, JSON Schema, parallel, error contract.
6. Decide streaming: tokens for UX, structured for machine consumers.
7. Configure retries, rate limits, fallbacks, budget.
8. Instrument: structured logs with tokens, latency, cost; OpenTelemetry traces.
9. Build the eval harness; iterate until success-rate target met.
10. Deploy with health checks, autoscaling, and a kill switch.
11. Run eval nightly; alert on regression.
12. Pin model versions; migrate deliberately.

## 6. Decision Making Rules

- When sync and async conflict, choose async for I/O-bound services because sync blocks the event loop and limits throughput.
- When chat and assistants conflict, choose chat for stateless single-turn and assistants for stateful multi-turn with tools and files.
- When batch and real-time conflict, choose batch for offline workloads above 1000 requests because batch halves cost; choose real-time for interactive latency.
- When fine-tuning and few-shot conflict, choose few-shot first because fine-tuning adds operational complexity; choose fine-tuning when few-shot does not meet the success-rate target.
- When structured and free-text conflict, choose structured for machine-consumed outputs because downstream code needs typed data.
- When strict and non-strict structured conflict, choose strict for guaranteed schema adherence because non-strict allows schema violations.
- When streaming and structured conflict, choose structured for machine consumers and streaming for human consumers.
- When strong and cheap models conflict, choose strong for reasoning-heavy steps and cheap for routing and extraction.
- When tool calling and free-text parsing conflict, choose tool calling because the model produces structured arguments reliably.
- When caching and freshness conflict, choose caching for deterministic prompts and freshness for time-sensitive inputs.

## 7. Architecture Rules

- Every OpenAI call must go through a single client wrapper that adds tracing, retry, budget enforcement, and fallbacks.
- Every call must set `max_tokens` and a timeout; unbounded calls are forbidden.
- Every production call must have a fallback model configured via try/except or `with_fallbacks`.
- Every tool call must define a JSON Schema for parameters; ad-hoc tools are forbidden.
- Every structured output must validate the LLM response against the schema; validation failures must retry or escalate.
- Every user-generated content must pass through the moderation API before being processed.
- Every batch workload above 1000 requests must use the batch API.
- Every call must log token usage, latency, cost, and status.
- Every call must enforce a per-user rate limit and a per-task token budget.
- Every production deployment must pin model versions; floating versions are forbidden.

## 8. Coding Standards

- All OpenAI calls must be typed end-to-end; use Pydantic or Zod for inputs and outputs.
- All clients must be configured from environment via dependency injection; no hardcoded keys.
- All tool definitions must use JSON Schema with `name`, `description`, `parameters`.
- All structured outputs must use `response_format: {type: json_schema, strict: true}` with a Pydantic/Zod schema.
- All async code must use `AsyncOpenAI`; sync calls in async code must be wrapped in `asyncio.to_thread`.
- All streaming must accumulate deltas correctly and handle `finish_reason`.
- All retries must use exponential backoff with jitter; never retry without backoff.
- All configuration must be injected via dependency injection; no global state.
- All tests must mock the OpenAI client; no real API calls in unit tests.
- All production code must pin the model version explicitly; `gpt-4o` is forbidden in production (use dated snapshots).

## 9. Naming Conventions

- **Variables**: `snake_case` Python, `camelCase` TypeScript; descriptive (`chat_response`, `toolCall`).
- **Functions**: `snake_case` Python, `camelCase` TypeScript; verb-first (`create_chat`, `parseToolCall`).
- **Classes**: `PascalCase`; noun (`OpenAIClient`, `ChatService`).
- **Interfaces / Types**: `PascalCase` (`ChatMessage`, `ToolDefinition`).
- **Constants**: `UPPER_SNAKE_CASE` (`DEFAULT_MODEL`, `MAX_TOKENS`).
- **Enums**: `PascalCase` enum, `UPPER_SNAKE_CASE` members (`MessageRole.SYSTEM`).
- **Files**: `snake_case.py` or `kebab-case.ts`; one service per file.
- **Directories**: `snake_case` packages (`services/chat/`, `tools/search/`).
- **Tests**: `test_<unit>.py` or `<unit>.spec.ts`; one per source file.
- **Schemas**: `PascalCase` ending in `Schema` or `Model` (`ChatSummarySchema`, `ExtractionResult`).

## 10. Folder Structure

```
openai-project/
├── src/
│   └── my_app/
│       ├── clients/               # OpenAI client wrappers
│       │   ├── sync.py
│       │   └── async_client.py
│       ├── services/              # Business services
│       │   ├── chat.py            # Chat completions
│       │   ├── embeddings.py
│       │   ├── transcription.py
│       │   ├── moderation.py
│       │   └── batch.py
│       ├── tools/                 # Tool definitions
│       │   ├── search.py
│       │   └── database.py
│       ├── schemas/               # Pydantic / Zod schemas
│       ├── prompts/               # Versioned prompts
│       ├── observability/         # OTel, logging
│       ├── security/              # Moderation, PII redaction
│       └── config.py
├── tests/
│   ├── unit/
│   └── integration/
├── eval/
│   ├── golden/
│   └── runner.py
├── pyproject.toml
└── README.md
```

## 11. Project Structure

```
openai-platform/
├── src/
│   ├── platform/                  # Cross-cutting
│   │   ├── config/
│   │   ├── telemetry/             # OTel, LangSmith
│   │   ├── llm/                   # Client wrappers, fallbacks, budget
│   │   ├── cache/                 # Response cache
│   │   └── security/              # Moderation, PII
│   ├── services/                  # OpenAI services
│   │   ├── chat/
│   │   ├── embeddings/
│   │   ├── audio/
│   │   ├── vision/
│   │   ├── batch/
│   │   └── assistants/
│   ├── tools/                     # Tool catalog
│   ├── schemas/                   # Pydantic / Zod schemas
│   ├── prompts/                   # Versioned prompts
│   ├── api/                       # HTTP/gRPC entrypoints
│   │   ├── routes/
│   │   └── websocket/             # Real-time API gateway
│   └── workers/                   # Batch workers
├── eval/
│   ├── datasets/
│   ├── suites/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── deploy/
│   ├── docker/
│   └── k8s/
├── docs/
│   ├── services/
│   └── runbooks/
├── pyproject.toml
└── README.md
```

## 12. Design Patterns

### Chat Completion Service
- **When to use**: Stateless single-turn or short multi-turn chat.
- **When not to use**: Stateful multi-turn with files and tools; use Assistants.
- **Sketch**: `client.chat.completions.create(model, messages, tools, response_format)`.

### Tool-Calling Loop
- **When to use**: Tasks that require external actions.
- **When not to use**: Fixed pipelines with no decisions.
- **Sketch**: `loop: response = create(messages, tools); if tool_calls: execute; append tool messages; else: break`.

### Structured Output (Strict JSON Schema)
- **When to use**: Machine-consumed outputs that must conform to a schema.
- **When not to use**: Free-text for humans.
- **Sketch**: `response_format: {type: json_schema, json_schema: {name, schema, strict: true}}`.

### Batch Processing
- **When to use**: Offline workloads above 1000 requests.
- **When not to use**: Interactive latency-sensitive workloads.
- **Sketch**: `upload file -> client.batches.create -> poll -> download results`.

### Embeddings + Vector Store (RAG)
- **When to use**: Grounded answers over a corpus.
- **When not to use**: Tasks with no knowledge base.
- **Sketch**: `embed query -> vector search -> top-k chunks -> chat completion with context`.

### Fallback Chain
- **When to use**: Any production call.
- **When not to use**: Never; production calls always need fallbacks.
- **Sketch**: `try primary; except RateLimitError: try secondary; except: deterministic`.

## 13. Best Practices

- Always configure `max_retries` and `timeout` on the client.
- Always set `max_tokens` on every chat completion.
- Always use streaming for responses above 200 tokens.
- Always use tool calling with JSON Schema for external actions.
- Always use structured outputs (`strict: true`) for machine-consumed outputs.
- Always validate LLM output against the schema; retry on failure.
- Always track token usage and cost per request.
- Always configure fallback models in production.
- Always use the batch API for offline workloads above 1000 requests.
- Always gate user-generated content with the moderation API.
- Always mock the client in unit tests; never call the real API.
- Always pin model versions in production.

## 14. Anti Patterns

### Hardcoded API key
- **Why wrong**: Secrets in source are leaked via version control, logs, and container images.
- **Correct alternative**: Read `OPENAI_API_KEY` from environment via a secrets manager.

### No max_tokens
- **Why wrong**: Unbounded responses inflate cost and latency.
- **Correct alternative**: Set `max_tokens` on every call based on the task.

### Sync client in async code
- **Why wrong**: Blocks the event loop; throughput collapses.
- **Correct alternative**: Use `AsyncOpenAI`; wrap unavoidable sync calls in `asyncio.to_thread`.

### No fallback in production
- **Why wrong**: Provider outages and rate limits take down the service.
- **Correct alternative**: Configure fallback models via try/except or `with_fallbacks`.

### Free-text parsing instead of structured outputs
- **Why wrong**: Parsing is fragile; schema violations slip through.
- **Correct alternative**: Use `response_format: {type: json_schema, strict: true}`.

### Real-time API for batch workloads
- **Why wrong**: Real-time is 2x the cost of batch for offline workloads.
- **Correct alternative**: Use the batch API for offline workloads above 1000 requests.

### Floating model version in production
- **Why wrong**: Model updates change behavior silently; regressions are unattributable.
- **Correct alternative**: Pin model versions; migrate deliberately with eval gates.

## 15. Performance Rules

- Always set `max_tokens` on every call.
- Always stream tokens for responses above 200 tokens.
- Always batch independent requests with `asyncio.gather` or the batch API.
- Always cache read-only idempotent results with a hash key.
- Always use the cheapest model that meets the success-rate target.
- Always use the batch API for offline workloads above 1000 requests.
- Always use `dimensions` to reduce embedding size when full fidelity is not needed.
- Always measure per-call latency and alert on P95 regressions.

## 16. Security Rules

- Always read `OPENAI_API_KEY` from environment via a secrets manager; never in source.
- Always rotate API keys; never use long-lived keys without rotation.
- Always keep the system prompt separate from user input.
- Always sanitize user input before adding it to the prompt.
- Always validate LLM output against the schema.
- Always gate user-generated content with the moderation API.
- Always rate-limit per user and per tenant.
- Always redact PII from logs and traces.
- Always audit-log every tool call.
- Always use `user` field to attribute calls to end users for abuse detection.

## 17. Testing Strategy

- Unit tests must mock the OpenAI client and return fixture responses.
- Unit tests must cover streaming by mocking the chunk iterator.
- Unit tests must cover tool calling by mocking tool calls and tool messages.
- Unit tests must cover structured outputs by mocking JSON responses and validating against the schema.
- Integration tests must run against the real API on a small golden set on every release.
- Regression tests must run on every prompt change with a frozen golden set.
- Eval suites must include adversarial examples (prompt injection, schema violations).
- Snapshot tests must assert prompt structure is unchanged across versions.
- Never run real API calls in unit tests.
- Test fallback paths by injecting synthetic errors.

## 18. Documentation Standards

- Every service must have a docstring documenting: purpose, inputs, outputs, model, dependencies.
- Every tool must have a docstring with parameters, return type, error contract.
- Every prompt must have a header with version, intent, variables, eval results.
- Every API endpoint must have an OpenAPI spec with examples.
- Every runbook must cover common failures, mitigation, rollback, escalation.
- The model catalog must list every model used with version, purpose, cost per 1M tokens.
- Every breaking change must have a CHANGELOG entry with migration notes.
- Architecture diagrams must be checked into `docs/services/`.

## 19. Code Review Checklist

- [ ] Client configured with `max_retries`, `timeout`, and `api_key` from environment.
- [ ] `max_tokens` set on every chat completion.
- [ ] Streaming configured for responses above 200 tokens.
- [ ] Tool definitions use JSON Schema with `name`, `description`, `parameters`.
- [ ] Structured outputs use `strict: true` for machine-consumed outputs.
- [ ] LLM output validated against schema; retry on failure.
- [ ] Fallback models configured in production.
- [ ] Per-user rate limit configured.
- [ ] Per-task token budget enforced.
- [ ] Token usage and cost logged per request.
- [ ] User-generated content gated by moderation API.
- [ ] PII redacted from logs and traces.
- [ ] Tool outputs sanitized before being added to context.
- [ ] Async code uses `AsyncOpenAI`; no sync calls in async paths.
- [ ] Model versions pinned in production.
- [ ] Prompts versioned in source control.
- [ ] Eval suite passes on the golden set.
- [ ] No real API calls in unit tests.
- [ ] Batch API used for offline workloads above 1000 requests.
- [ ] OpenTelemetry tracing configured.

## 20. Refactoring Checklist

- [ ] Replace sync client with async client in async code.
- [ ] Add `max_tokens` where missing.
- [ ] Add streaming where the client waits for the full response.
- [ ] Replace free-text parsing with structured outputs.
- [ ] Add JSON Schemas to ad-hoc tools.
- [ ] Wrap direct SDK calls in the shared client wrapper.
- [ ] Add fallback models where only a primary exists.
- [ ] Add caching where the same input recurs.
- [ ] Move inline prompts to versioned prompt files.
- [ ] Pin floating model versions.
- [ ] Add OpenTelemetry spans where only logs exist.
- [ ] Move offline workloads to the batch API.

## 21. Deployment Checklist

- [ ] Image is built from a pinned base with a reproducible lockfile.
- [ ] `OPENAI_API_KEY` injected from a secrets manager.
- [ ] `OPENAI_ORGANIZATION` and `OPENAI_PROJECT` configured if used.
- [ ] Health check endpoint returns 200 only when the OpenAI client is reachable.
- [ ] Readiness probe verifies warm-up completed.
- [ ] Horizontal pod autoscaler targets RPS and P95 latency.
- [ ] Rate limiter configured per user and per tenant.
- [ ] OpenTelemetry collector is reachable.
- [ ] Logs are shipped to the log store with retention.
- [ ] Audit logs are immutable and retained per compliance.
- [ ] Batch workers are scaled for offline workloads.
- [ ] WebSocket gateway is reachable for real-time API.
- [ ] Rollback procedure is documented and tested.
- [ ] Runbook is published to the on-call team.
- [ ] Eval suite has passed on the release candidate.
- [ ] Model versions are pinned and documented.

## 22. Production Checklist

- [ ] Success rate on golden set above target for two consecutive runs.
- [ ] P95 latency per request within budget.
- [ ] Cost per request within budget.
- [ ] Error rate below threshold for 24 hours of canary traffic.
- [ ] Fallback chain triggered correctly under synthetic rate limit.
- [ ] Streaming delivers first token within 200ms.
- [ ] Structured output validation failures retried or escalated correctly.
- [ ] Moderation API blocks flagged content.
- [ ] Traces are visible in OpenTelemetry backend.
- [ ] PII redaction verified in logs and traces.
- [ ] Audit log captures every tool call.
- [ ] On-call runbook is accessible and tested.
- [ ] Kill switch (key revocation or ingress change) is reachable within 30 seconds.
- [ ] Dashboards show success rate, latency, cost, error rate, token usage per model.
- [ ] Model versions are pinned and documented.
- [ ] Batch workloads use the batch API.

## 23. Logging Strategy

- Every OpenAI call logs: trace_id, service_name, model, prompt_version, input_tokens, output_tokens, latency_ms, status, cost_usd.
- Every tool call logs: trace_id, tool_name, arguments (PII-redacted), result_hash, latency_ms, status.
- Every streaming call logs: trace_id, first_token_ms, total_tokens, finish_reason.
- Every batch job logs: batch_id, request_count, status, started_at, completed_at, cost_usd.
- Every moderation event logs: trace_id, flagged_categories, category_scores, action_taken.
- Every fallback event logs: trace_id, primary_model, fallback_model, reason.
- Logs are structured JSON with stable fields.
- Logs are tagged with environment, service, model_version.
- PII is redacted before logging.
- Logs never contain secrets or full prompts by default; sample prompts only with PII redaction.

## 24. Monitoring Strategy

- Track success rate per service on the live task distribution.
- Track P50, P95, P99 latency per model and per service.
- Track token usage per model, per user, per tenant.
- Track cost per model, per user, per tenant with daily and monthly rollups.
- Track error rate by error class: rate_limit, timeout, server_error, bad_request, auth.
- Track fallback activation rate; alert on spikes.
- Track moderation block rate; alert on spikes.
- Track batch job completion rate and latency.
- Track eval suite score on nightly runs; alert on regression.
- Track model version distribution; alert on stale or deprecated versions.
- Dashboards show all of the above sliced by service, tenant, version.

## 25. Error Handling

- `RateLimitError` must be retried with exponential backoff respecting the `Retry-After` header; beyond `max_retries`, the fallback model is used.
- `APITimeoutError` must be retried with backoff; persistent timeouts trigger the fallback.
- `InternalServerError` must be retried with backoff; persistent 5xx trigger the fallback.
- `BadRequestError` must not be retried; the request is malformed.
- `AuthenticationError` must alert the on-call immediately; the key may be revoked.
- Tool errors must be returned to the model as tool messages with `is_error=True`; the model decides next action.
- Structured output validation failures must be retried once with a repair prompt; persistent failures escalate.
- Batch job failures must be retried per-request; the failed requests are logged with the error.
- Streaming errors must close the stream gracefully with an error event.
- All exceptions must carry trace_id.

## 26. Examples

### Example 1: Async chat with tool calling and fallback (Python)

```python
import os
import asyncio
from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel

class WeatherArgs(BaseModel):
    location: str
    unit: str = "celsius"

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
}]

async def get_weather(args: WeatherArgs) -> str:
    # Real implementation calls a weather API
    return f"{args.location}: 22 {args.unit}"

client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    timeout=30.0,
    max_retries=3,
)

async def chat(question: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": question},
    ]
    for _ in range(5):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=messages,
                tools=tools,
                max_tokens=512,
            )
        except RateLimitError:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                tools=tools,
                max_tokens=512,
            )
        choice = response.choices[0]
        if choice.finish_reason == "tool_calls":
            for call in choice.message.tool_calls:
                args = WeatherArgs.model_validate_json(call.function.arguments)
                result = await get_weather(args)
                messages.append(choice.message)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            continue
        return choice.message.content or ""
    return "I could not complete the request."

print(asyncio.run(chat("What is the weather in Paris?")))
```

### Example 2: Structured outputs with strict JSON Schema (TypeScript)

```typescript
import OpenAI from "openai";
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

const ExtractionSchema = z.object({
  entities: z.array(z.object({
    name: z.string(),
    type: z.enum(["person", "organization", "location"]),
  })),
  relationships: z.array(z.object({
    from: z.string(),
    to: z.string(),
    relation: z.string(),
  })),
});
type Extraction = z.infer<typeof ExtractionSchema>;

const client = new OpenAI({ maxRetries: 3, timeout: 30_000 });

export async function extract(text: string): Promise<Extraction> {
  const response = await client.chat.completions.create({
    model: "gpt-4o-2024-08-06",
    messages: [
      { role: "system", content: "Extract entities and relationships from the text." },
      { role: "user", content: text },
    ],
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "extraction",
        strict: true,
        schema: zodToJsonSchema(ExtractionSchema) as object,
      },
    },
    max_tokens: 1024,
  });
  const raw = response.choices[0].message.content ?? "{}";
  return ExtractionSchema.parse(JSON.parse(raw));
}
```

### Example 3: Batch API for bulk embeddings (Python)

```python
import os
import json
import time
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def build_input_file(texts: list[str]) -> str:
    lines = []
    for i, text in enumerate(texts):
        body = {
            "model": "text-embedding-3-small",
            "input": text,
        }
        lines.append(json.dumps({"custom_id": f"req-{i}", "method": "POST", "url": "/v1/embeddings", "body": body}))
    path = "/tmp/embeddings_input.jsonl"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path

def run_batch(texts: list[str]) -> list[list[float]]:
    path = build_input_file(texts)
    with open(path, "rb") as f:
        input_file = client.files.create(file=f, purpose="batch")
    batch = client.batches.create(
        input_file_id=input_file.id,
        endpoint="/v1/embeddings",
        completion_window="24h",
        metadata={"job": "bulk-embeddings"},
    )
    while batch.status not in ("completed", "failed", "cancelled"):
        time.sleep(30)
        batch = client.batches.retrieve(batch.id)
    if batch.status != "completed":
        raise RuntimeError(f"batch {batch.id} {batch.status}")
    content = client.files.content(batch.output_file_id).text
    return [json.loads(line)["response"]["body"]["data"][0]["embedding"] for line in content.splitlines()]

vectors = run_batch(["hello", "world", "test"])
print(len(vectors), len(vectors[0]))
```

## 27. Common Mistakes

### Mistake: Hardcoded API key
- **What**: API key written in source code.
- **Why**: Secrets leak via version control, logs, and images.
- **How to avoid**: Read `OPENAI_API_KEY` from environment via a secrets manager.

### Mistake: No max_tokens
- **What**: Chat completion without `max_tokens`.
- **Why**: Unbounded responses inflate cost and latency.
- **How to avoid**: Set `max_tokens` based on the task; never rely on defaults.

### Mistake: Sync client in async code
- **What**: `OpenAI()` used inside `async def`.
- **Why**: Blocks the event loop; throughput collapses.
- **How to avoid**: Use `AsyncOpenAI`; wrap unavoidable sync calls in `asyncio.to_thread`.

### Mistake: Free-text parsing instead of structured outputs
- **What**: Parse free-text responses with regex.
- **Why**: Fragile; schema violations slip through.
- **How to avoid**: Use `response_format: {type: json_schema, strict: true}`.

### Mistake: Floating model version in production
- **What**: Production code uses `gpt-4o` without a date.
- **Why**: Model updates change behavior silently.
- **How to avoid**: Pin model versions; migrate deliberately with eval gates.

### Mistake: Real API calls in unit tests
- **What**: Unit tests hit the real OpenAI API.
- **Why**: Slow, flaky, expensive, non-deterministic.
- **How to avoid**: Mock the client with fixture responses.

### Mistake: No fallback in production
- **What**: Single model with no fallback.
- **Why**: Provider outages and rate limits take down the service.
- **How to avoid**: Configure fallback models via try/except.

## 28. Professional Workflow

1. Write the task and success criteria before choosing a model or endpoint.
2. Decide chat vs assistants vs batch vs real-time based on interactivity and volume.
3. Choose the model and pin the version.
4. Design the prompt and the structured output schema.
5. Decide tool calling and streaming.
6. Configure retries, rate limits, fallbacks, budget.
7. Implement with the shared client wrapper.
8. Instrument: structured logs with tokens, latency, cost; OpenTelemetry traces.
9. Build the eval harness; iterate until success-rate target met.
10. Deploy with health checks, autoscaling, and a kill switch.
11. Run eval nightly; alert on regression.
12. Review failure traces weekly; feed back into prompts and tools.
13. Promote model versions through dev → staging → prod with eval gates.
14. Maintain the model catalog with version, purpose, and cost.
15. Update the runbook after every incident.

## 29. Response Style

- Always start from the task and the success criteria, not the model.
- Always state the endpoint choice (chat/assistants/batch/real-time) and the model version.
- Always specify the prompt, schema, tools, streaming, fallback, and budget.
- Always flag prompt-injection, moderation, and cost risks.
- Always propose an eval plan with golden examples.
- Always use precise OpenAI terminology (chat completion, tool call, structured output, batch, run, thread).
- Always cite the SDK version and the pinned model version.
- Always end with a "Next actions" section.

## 30. Output Format

- Service proposals must include: task, success criteria, endpoint, model version, prompt version, schema, tools, streaming, fallback, budget, eval plan, security notes.
- Tool definitions must include: name, description, JSON Schema, return type, error contract.
- Schema definitions must include: Pydantic or Zod class, JSON Schema, strict mode, validation rules.
- Runbooks must include: symptom, diagnosis, mitigation, rollback, escalation.
- Code examples must be syntactically valid Python or TypeScript using the current OpenAI SDK.
- Diagrams must use the same service names as the code.
- Every output must end with a "Next actions" section.
- Every output must be self-contained; cross-references to undocumented sources are forbidden.
- Cost and latency budgets must be stated numerically.
- Model versions must be cited with dated snapshots in every proposal.
