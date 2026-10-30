# HTTP Semantics, Status Codes and Problem Details

Reference for method properties, status code choice, headers, conditional requests, caching and error formatting. Based on RFC 9110 (HTTP Semantics), RFC 9111 (HTTP Caching) and RFC 9457 (Problem Details), verified 2026-10. RFC 9110 obsoletes RFC 7231 to 7235; RFC 9457 obsoletes RFC 7807.

## Contents
- Method properties
- Status code decision table
- Headers worth knowing
- Conditional requests
- Caching
- Problem Details
- Content negotiation and media types
- PATCH formats

## Method properties

| Method | Safe | Idempotent | Typical use | Notes |
|---|---|---|---|---|
| GET | yes | yes | Read a resource or collection | No request body semantics; cacheable |
| HEAD | yes | yes | Headers of a GET | Same headers as GET, no body |
| OPTIONS | yes | yes | Capabilities, CORS preflight | Respond with `Allow` |
| POST | no | no | Create in a collection, run an action | Make retries safe with an idempotency mechanism |
| PUT | no | yes | Replace a resource at a known URL | Send the full representation |
| PATCH | no | no (by default) | Partial update (RFC 5789) | Idempotent only if you design it so; document the patch format |
| DELETE | no | yes | Remove | Repeat calls may return `404` or `204`; pick one and document it |

Safe means no state change requested by the client. Idempotent means repeating the request has the same intended effect as sending it once. The HTTP QUERY method (safe request with a body, for complex searches) is an IETF draft at the time of writing: check its status before using it; OpenAPI 3.2 can describe a `query` operation.

## Status code decision table

| Situation | Status | Notes |
|---|---|---|
| Read OK | 200 | Body is the representation |
| Created | 201 | `Location` of the new resource; include the representation |
| Accepted for async processing | 202 | `Location` of an operation or status resource |
| Success, no body | 204 | Typical for `DELETE` and some `PUT` |
| Not modified | 304 | Response to a conditional `GET`/`HEAD`; no body |
| Partial content | 206 | Range requests; `Content-Range` |
| Resource permanently moved | 308 (method preserved) or 301 | Prefer 308 for APIs; 301 may be rewritten to `GET` by clients |
| Temporary redirect | 307 (method preserved) or 302 | 303 sends the client to a `GET` of another resource |
| Malformed request syntax, invalid parameter format | 400 | Also invalid cursor, unparsable JSON |
| Missing or invalid credentials | 401 | Include `WWW-Authenticate` |
| Authenticated but not permitted | 403 | When revealing the object exists is acceptable |
| Not found, or hidden from this caller | 404 | Use for cross-tenant objects |
| Method not allowed on this resource | 405 | Include `Allow` |
| Cannot satisfy `Accept` | 406 | |
| Request timeout (client too slow) | 408 | |
| State conflict (duplicate, invalid transition, in-flight idempotent request) | 409 | Explain in Problem Details |
| Resource permanently gone | 410 | Deliberately removed resources and retired versions |
| Precondition failed (`If-Match`, `If-Unmodified-Since`) | 412 | Client holds a stale version |
| Body too large | 413 | |
| URI too long | 414 | |
| Unsupported request `Content-Type` | 415 | |
| Range not satisfiable | 416 | |
| Well-formed but semantically invalid | 422 | Field-level `errors` extension |
| Precondition header required but missing | 428 | RFC 6585 |
| Rate limited | 429 | `Retry-After`; RFC 6585 |
| Request header fields too large | 431 | RFC 6585 |
| Unavailable for legal reasons | 451 | RFC 7725 |
| Server error | 500 | Generic Problem Details, no internals |
| Upstream failure | 502 / 504 | Proxy or gateway context |
| Overloaded or maintenance | 503 | `Retry-After` |

Rules of thumb:
- 4xx means the client can change something to succeed; 5xx means the server failed. Do not return 5xx for validation failures.
- 401 vs 403: no or bad credentials versus insufficient permission. For tenant isolation prefer 404.
- 400 vs 422: pick one convention for field validation and apply it everywhere. A common split: 400 for syntax and parameter format, 422 for body semantics.
- 409 vs 412: 409 for conflicts with current state; 412 only when a client-sent precondition fails.
- Do not invent custom status codes; put detail into the Problem Details `type` instead.

## Headers worth knowing

- `Location`: URL of a created resource (201) or an operation (202).
- `Allow`: required on 405; lists permitted methods.
- `Retry-After`: seconds or HTTP date; on 429, 503, and sometimes 202 or 3xx.
- `WWW-Authenticate`: required on 401.
- `Content-Type`, `Accept`, `Content-Language`, `Content-Location`.
- `Vary`: lists request headers that influence the response (`Accept`, `Accept-Encoding`, `Authorization` for shared caches).
- `Link` (RFC 8288): relations such as `next`, `prev`, `first`, `last`, `deprecation`, `sunset`, `describedby`.
- `Prefer` (RFC 7240): `return=minimal`, `return=representation`, `respond-async`.
- `Content-Digest` (RFC 9530) and HTTP Message Signatures (RFC 9421) for integrity and signing; see api-security-expert for webhook and request signing.

## Conditional requests

- Validators: `ETag` (strong `"abc"` or weak `W/"abc"`) and `Last-Modified`. Prefer strong ETags for update preconditions; weak ones are fine for caching.
- Read: client sends `If-None-Match: "v3"`; server returns `304` when unchanged.
- Update (lost update prevention): client sends `If-Match: "v3"`; server returns `412` if the current ETag differs; return `428` when a required `If-Match` is absent.
- Create-only `PUT`: `If-None-Match: *` makes the request fail with `412` when the resource exists.
- An ETag may be a row version, a content hash, or a version counter; it must change whenever the representation changes.

## Caching

- `Cache-Control: no-store` for credentials and sensitive data. `private` for per-user responses. `public, max-age=N` only for data identical for all callers. `no-cache` means "store but revalidate before reuse", which pairs well with ETags for API data.
- Authenticated API responses can be cached by browsers (`private`) but should not be reused by shared caches unless intended; set `Vary` for headers that change the representation (`Accept-Language`, `Accept`).
- `stale-while-revalidate` and `stale-if-error` are extensions defined for `Cache-Control` (RFC 5861); check support in your CDN.
- Responses to `POST` are rarely cached; design reads as `GET`.
- Explicitly set `Cache-Control` on error responses too; do not let intermediaries cache 5xx.

## Problem Details

Media type `application/problem+json`. Members:

- `type`: URI identifying the problem type (documented page); default `about:blank` means the problem has no meaning beyond the status code.
- `title`: short summary of the type, stable across occurrences.
- `status`: the HTTP status code (advisory; must match the real status).
- `detail`: explanation specific to this occurrence, safe for the client.
- `instance`: URI identifying this occurrence (for example the request path or a problem id).
- Extension members are allowed and should be documented; clients must ignore unknown ones.

```json
{
  "type": "https://api.example.com/problems/insufficient-credit",
  "title": "Insufficient credit",
  "status": 422,
  "detail": "Order total 5000 exceeds available credit 3000.",
  "instance": "/v1/orders",
  "available_cents": 3000
}
```

Validation errors usually add an `errors` array of `{ pointer, message }` objects (JSON Pointer to the offending field).

Guidance:
- Use one `type` URI per distinct, documented error class, and keep them stable.
- Do not put sensitive values, stack traces, SQL or internal hosts in `detail` or extensions.
- Return Problem Details for 4xx and 5xx from every layer (gateway errors too, where possible).
- Declare the problem response once in OpenAPI components and reference it from operations.

## Content negotiation and media types

- Respond with `Content-Type: application/json` (no `charset` parameter needed; JSON is UTF-8) and honor `Accept`; return `406` or a default representation, and document which.
- Vendor media types (`application/vnd.example.v2+json`) can carry versions; they complicate caching and tooling, so use them deliberately.
- Reject unexpected request media types with `415` before parsing bodies; enforce a body size limit.
- Use `Content-Language` and `Accept-Language` only if messages are localized; keep Problem Details `type` language-independent.

## PATCH formats

- JSON Merge Patch (RFC 7396), `Content-Type: application/merge-patch+json`: send only changed fields, `null` removes a field. Cannot express changes to array elements or set a literal null.
- JSON Patch (RFC 6902), `Content-Type: application/json-patch+json`: ordered operations (`add`, `remove`, `replace`, `move`, `copy`, `test`) with JSON Pointer paths. Validate paths against an allowlist; never apply patches to server-managed fields (`tenant_id`, `id`, `version`).
- A custom partial body with a strict schema (as in SKILL.md) is also valid; document it as the `PATCH` format.
- Combine any of them with `If-Match` for optimistic concurrency.
