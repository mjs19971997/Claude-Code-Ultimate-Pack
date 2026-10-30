# Batches, Files and Structured Outputs

Reference for the Message Batches API, the Files API and structured-output schema rules. Verified against the Claude API docs, Python SDK `anthropic` 2.3.x and TypeScript SDK `@anthropic-ai/sdk` 1.3.x, models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` (2026-10). Prices are not repeated here: batch requests are discounted versus synchronous calls, and the exact discount per model is on the pricing page.

## 1. Message Batches: limits and lifecycle

- A batch holds up to 100,000 requests or 256 MB, whichever comes first (larger bodies return 413). Each request has a `custom_id` matching `^[a-zA-Z0-9_-]{1,64}$` (unique in the batch) and `params` identical to Messages API parameters.
- Requests are processed independently and asynchronously; most batches finish within an hour, and a batch expires if not finished within 24 hours. Results stay downloadable for 29 days after creation. One failed request does not affect the others.
- Batches are scoped to a workspace. They may slightly overshoot the workspace spend limit because of concurrency.
- Not allowed in batch requests: `stream: true`, `speed`, `fallbacks`, `max_tokens: 0`. Each request needs `max_tokens` of at least 1. Tool use, vision, system prompts, multi-turn, thinking and most beta features work, as do structured outputs and server tools.
- `processing_status` is `in_progress`, then `canceling` (after cancel), then `ended`. `request_counts` breaks down processing, succeeded, errored, canceled and expired.
- Result types per request: `succeeded` (message included), `errored` (invalid request or server error, not billed), `canceled`, `expired` (not billed). Result order does not match input order: match on `custom_id`.
- On the Message Batches API, the `output-300k-2026-03-24` beta header raises the output ceiling to 300K tokens on the models listed as supporting it (Opus 5.5, Sonnet 5.5 and Haiku 5.5 are; Fable 5.1 is not). Check the docs before relying on it.
- Prompt caching works in batches on a best-effort basis (hit rates vary widely with traffic). Use identical `cache_control` blocks in every request, keep a steady request stream so entries do not expire, and share as much prefix as possible.

## 2. Batch workflow in Python

```python
import time
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

client = anthropic.Anthropic()

documents = {"doc-001": "First text ...", "doc-002": "Second text ..."}

batch = client.messages.batches.create(
    requests=[
        Request(
            custom_id=doc_id,
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-5-5",
                max_tokens=512,
                system="Summarize the document in two sentences.",
                messages=[{"role": "user", "content": text}],
            ),
        )
        for doc_id, text in documents.items()
    ]
)

while True:
    batch = client.messages.batches.retrieve(batch.id)
    if batch.processing_status == "ended":
        break
    time.sleep(60)  # poll sparingly; batches take minutes to hours

retry_ids = []
for entry in client.messages.batches.results(batch.id):  # streamed, memory-friendly
    outcome = entry.result
    if outcome.type == "succeeded":
        text = "".join(b.text for b in outcome.message.content if b.type == "text")
        save_summary(entry.custom_id, text)
    elif outcome.type == "errored":
        if outcome.error.error.type == "invalid_request_error":
            log_bad_request(entry.custom_id, outcome.error)  # fix the request; do not resend as is
        else:
            retry_ids.append(entry.custom_id)  # transient; safe to resubmit
    else:  # "expired" or "canceled"
        retry_ids.append(entry.custom_id)
```

`save_summary`, `log_bad_request` are placeholders for your own persistence. Plain dicts work for `requests` too (`{"custom_id": ..., "params": {...}}`); the typed helpers add static checking.

TypeScript equivalent: `client.messages.batches.create({ requests: [{ custom_id, params }] })`, poll with `client.messages.batches.retrieve(id)` until `processing_status === "ended"`, then `for await (const entry of await client.messages.batches.results(id))`.

Other operations: `client.messages.batches.list()` (auto-paginated), `client.messages.batches.cancel(id)` (status becomes `canceling`, then `ended` with partial results), and `delete` for finished batches.

Design notes:

- Derive `custom_id` from your record key (for example `doc-<id>-v<prompt-version>`) so reruns are idempotent and results map back without a side table.
- Split very large datasets into several batches for manageability and faster partial results.
- Dry-run one representative request through `messages.create` first to catch validation errors.
- Keep prompt, model and schema identical within a batch if you want caching to help.

## 3. Files API

Upload once, reference many times. No beta header is needed; use `client.files` (not `client.beta.files`).

- Limits: 500 MB per file, 1 TB storage per organization. Files cannot be modified or renamed after upload; upload a new file and delete the old one.
- Files are scoped to a workspace, not to an end user or session. Any API key with access to the workspace can read any file in it. Never accept a `file_id` from an end user or another untrusted source; keep your own mapping of user to file. For multitenant products, use one workspace per tenant (an organization can have up to 100 workspaces).
- Expiry: pass `expires_in_seconds` at upload (3,600 to 7,776,000, that is 1 hour to 90 days); the resulting `expires_at` cannot be changed. After expiry, downloads return 404 and messages referencing the file fail before inference; metadata stays readable for up to 30 days. Expiry is not a guaranteed-deletion control; delete explicitly with `DELETE /v1/files/{file_id}` when required.
- Files created by code execution or skills can be downloaded; uploaded files cannot be downloaded back.
- Listing returns `{data, next_page}`; pass `next_page` back as `page`, or use the SDK auto-pagination.

```python
from pathlib import Path
import anthropic

client = anthropic.Anthropic()

uploaded = client.files.upload(file=Path("contract.pdf"))  # content type is detected when omitted
file_id = uploaded.id

response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "List the termination clauses in this contract."},
                {"type": "document", "source": {"type": "file", "file_id": file_id}},
            ],
        }
    ],
)

client.files.delete(file_id)  # when no longer needed
```

TypeScript: `await client.files.upload({ file: await toFile(fs.createReadStream("contract.pdf"), undefined, { type: "application/pdf" }) })` (set the content type explicitly in TypeScript), then use the same `document` block with `source: { type: "file", file_id }`. Images use an `image` block with the same source shape. Code execution inputs use `container_upload` blocks.

## 4. Structured outputs

Two features share one constraint engine: `output_config.format` for the final answer and `strict: true` for tool inputs. They can be combined in one request.

Python (Pydantic model through the SDK helper):

```python
from pydantic import BaseModel
import anthropic

class Ticket(BaseModel):
    category: str
    urgent: bool
    summary: str

client = anthropic.Anthropic()
response = client.messages.parse(
    model="claude-haiku-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Classify: 'Site is down for all EU users!'"}],
    output_format=Ticket,
)
ticket = response.parsed_output
```

TypeScript (Zod through the SDK helper):

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";

const Ticket = z.object({ category: z.string(), urgent: z.boolean(), summary: z.string() });
const client = new Anthropic();

const response = await client.messages.parse({
  model: "claude-haiku-5-5",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Classify: 'Site is down for all EU users!'" }],
  output_config: { format: zodOutputFormat(Ticket) }
});
console.log(response.parsed_output);
```

Raw form: `output_config={"format": {"type": "json_schema", "schema": {...}}}`; the JSON arrives in the first text block.

Schema rules (a violation returns 400):

- Supported: object, array, string, integer, number, boolean, null; `enum` of primitives; `const`; `anyOf`, `allOf` (not with `$ref`); `$ref`, `$defs`, `definitions` (internal only); `default`; `required`; string formats `date-time`, `time`, `date`, `duration`, `email`, `hostname`, `uri`, `ipv4`, `ipv6`, `uuid`; array `minItems` of 0 or 1.
- Objects must set `additionalProperties: false` (SDK helpers add it).
- Not supported: recursive schemas, numeric constraints, `minLength`/`maxLength`, other array constraints, external `$ref`, regex backreferences, lookaround and word boundaries. SDK helpers can transform schemas with such constraints and validate them client-side.
- Required properties are emitted before optional ones regardless of schema order.
- Complexity limits exist (see the structured outputs page for explicit and internal limits); flatten large schemas.

Operational rules:

- Check `stop_reason` before trusting the parsed value: `refusal` (HTTP 200, billed, output may not match) and `max_tokens` (truncated output) can break the schema promise.
- Enum capitalization is not guaranteed; compare case-insensitively.
- The first request with a new schema pays compilation latency; compiled grammars are cached for 24 hours since last use. A schema change invalidates the compiled grammar and the prompt cache for that conversation.
- Incompatible with citations (400) and prefill. Works with batches, token counting, streaming and strict tools.
- Replace prefill-based JSON forcing with this feature; prefill returns 400 on Claude 4.6 and later.
