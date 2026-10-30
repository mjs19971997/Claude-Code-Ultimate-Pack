# Embeddings, Batch and Error Handling

Reference for embeddings, the Batch API, and the SDK error, retry and timeout behavior. Verified against openai-python 3.41.0 and openai-node 7.45.1 type definitions and READMEs (2026-10). Limits quoted from SDK docstrings can change, so confirm them in the current Batch and embeddings guides.

## 1. Embeddings

```python
result = client.embeddings.create(
    model="text-embedding-3-small",
    input=["first text", "second text"],   # str, list of str, or token arrays
    dimensions=512,                          # optional, shrinks the vector where supported
)
vectors = [item.embedding for item in result.data]
```

- Model IDs in the SDK type: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`.
- Parameters: `input`, `model`, `dimensions`, `encoding_format` (`float` or `base64`), `user`.
- Send many inputs per request to reduce overhead; respect the per-request input and token limits listed in the guide.
- Store the model name and `dimensions` next to every vector. Vectors from different models or dimensions are not comparable, so a model change means re-embedding the corpus.
- Normalize or use cosine similarity consistently with your vector store configuration.
- `encoding_format="base64"` reduces payload size; check what your SDK version returns before indexing.
- Use Batch (section 2) for large offline indexing jobs.
- Embeddings batches are limited to 50,000 embedding inputs across all requests in the batch (SDK docstring).

## 2. Batch API

Use Batch for work that can wait up to 24 hours.

Lifecycle:

1. Build a JSONL file; each line is one request: `custom_id` (unique), `method` (`POST`), `url` (matches the batch endpoint), `body` (the normal request body).
2. Upload with purpose `batch`.
3. Create the batch with `completion_window="24h"` and the endpoint.
4. Poll or use webhooks (`batch.completed`, `batch.failed`, `batch.expired`, `batch.cancelled`).
5. Download the output file and the error file; match results by `custom_id`, not by line order.

Limits from the SDK docstring: the input file can hold up to 50,000 requests and be up to 200 MB. Supported endpoints in the type: `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/completions`, `/v1/moderations`, `/v1/images/generations`, `/v1/images/edits`, `/v1/videos`. Only `24h` is accepted for `completion_window`.

```python
import json
from pathlib import Path

from openai import OpenAI

client = OpenAI()
MODEL = "gpt-5.5"  # read from settings in real code

def build_jsonl(items: dict[str, str], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for custom_id, text in items.items():
            line = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": MODEL,
                    "instructions": "Classify the text as positive, negative or neutral. Reply with one word.",
                    "input": text,
                    "max_output_tokens": 200,
                },
            }
            fh.write(json.dumps(line) + "\n")

build_jsonl({"a1": "Great product", "a2": "Arrived broken"}, Path("batch.jsonl"))
with open("batch.jsonl", "rb") as fh:
    uploaded = client.files.create(file=fh, purpose="batch")
batch = client.batches.create(
    input_file_id=uploaded.id,
    endpoint="/v1/responses",
    completion_window="24h",
    metadata={"job": "sentiment-2026-10"},
)
print(batch.id, batch.status)
```

Reading results later:

```python
batch = client.batches.retrieve(batch.id)
if batch.status == "completed":
    content = client.files.content(batch.output_file_id).text
    for raw in content.splitlines():
        row = json.loads(raw)
        custom_id = row["custom_id"]
        body = row["response"]["body"]        # same shape as a normal response
        # error rows are in batch.error_file_id
```

Other notes:

- Queue and rate limits for Batch are documented in the Batch guide; split very large jobs across several batches.
- Batch output expiry can be set with `output_expires_after`.
- Make processing idempotent: a retried job must not double-apply results.
- Cancel with `client.batches.cancel(batch.id)`; check the Batch guide for how partially completed work is handled.

## 3. Error classes

Python (`openai`):

| Class | Cause |
|---|---|
| `APIConnectionError` | Network problem, no HTTP response |
| `APITimeoutError` | Request exceeded the timeout (subclass of connection errors) |
| `APIStatusError` (base for below) | Any 4xx or 5xx; has `status_code`, `response`, `request_id` |
| `BadRequestError` 400 | Invalid parameters, schema rejected, context too long |
| `AuthenticationError` 401 | Missing or invalid key |
| `PermissionDeniedError` 403 | Key lacks access to the model or feature |
| `NotFoundError` 404 | Unknown model or object ID |
| `UnprocessableEntityError` 422 | Valid JSON but unprocessable |
| `RateLimitError` 429 | Rate limit or quota |
| `InternalServerError` 5xx | Server-side error |

Node adds `ConflictError` (409) and `APIConnectionTimeoutError`; all extend `OpenAI.APIError`, which exposes `status`, `headers`, `requestID`.

```python
import openai

try:
    response = client.responses.create(model=MODEL, input="hi")
except openai.RateLimitError as exc:
    log.warning("rate limited", extra={"request_id": exc.request_id})
    raise
except openai.APIStatusError as exc:
    log.error("api error", extra={"status": exc.status_code, "request_id": exc.request_id})
    raise
except openai.APIConnectionError as exc:
    log.error("connection error: %s", exc.__cause__)
    raise
```

Stream failures surface as SDK exceptions with the original exception in `__cause__`. In-band failures arrive as `error` or `response.failed` events, or as `response.status == "failed"` with `response.error`.

## 4. Retries and timeouts

- Both SDKs retry connection errors, 408, 409, 429 and 5xx twice by default with exponential backoff, only when the request body can be resent safely.
- Configure per client or per call:

```python
client = OpenAI(max_retries=3, timeout=30.0)
slow = client.with_options(timeout=300.0, max_retries=0)
slow.responses.create(model=MODEL, input=long_prompt)
```

```ts
const client = new OpenAI({ maxRetries: 3, timeout: 30_000 });
await client.responses.create({ model, input }, { timeout: 300_000, maxRetries: 0, signal });
```

- The default timeout is 10 minutes. A shorter timeout for interactive paths is usually better; use background mode for long work instead of a very long timeout.
- A timed-out request is retried by default, which can double the wait. Combine the timeout with the retry count when computing your worst-case latency.
- 429 handling beyond SDK retries: reduce concurrency, queue requests, honor `Retry-After` when present, and move bulk work to Batch.
- Do not retry 400, 401, 403, 404 or 422; fix the request.
- Make application-level retries idempotent: a retried tool-using workflow can repeat side effects unless handlers check for duplicates.
- Cancel Node requests with an `AbortSignal` in request options; in Python, close the stream or use asyncio cancellation.

## 5. Observability

- Record `response.id`, `usage` (input, output, cached and reasoning tokens), model, latency, status, and `request_id` from errors; the raw response headers are available via `client.responses.with_raw_response.create(...)`.
- Alert on rising `incomplete` rates, 429 rates and tool-loop cap hits.
- Redact prompts and outputs that contain personal data before logging, or log only hashes and sizes.
