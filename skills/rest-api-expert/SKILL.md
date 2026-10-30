---
name: rest-api-expert
description: >-
  Designs and reviews HTTP/REST APIs: resource modeling, method and status code semantics (RFC 9110), Problem Details errors (RFC 9457), OpenAPI 3.1 and 3.2 contracts, cursor pagination, filtering, conditional requests with ETag and If-Match, idempotency keys, rate limit headers, versioning and Deprecation/Sunset headers. Use when defining endpoints, writing or linting openapi.yaml, choosing status codes, handling 409, 412, 422 and 429, paginating collections, retrying POST safely, or evolving an API without breaking clients. Not for GraphQL schemas (use graphql-expert), OWASP API risks and signing (use api-security-expert), or Express or NestJS framework wiring (use expressjs-expert or nestjs-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# REST API Expert

This skill covers designing HTTP APIs that behave predictably for clients and intermediaries: resources and URLs, correct method and status semantics, a consistent error format, conditional requests, pagination, retry safety, and a machine-readable contract that can be linted, mocked and tested. Examples use TypeScript with Express 5, Zod 4 and PostgreSQL (`pg`), and every read and write is scoped by the authenticated tenant.

> Verified against RFC 9110 (HTTP Semantics), RFC 9111 (Caching), RFC 9457 (Problem Details, obsoletes RFC 7807), RFC 9745 (Deprecation header), RFC 8594 (Sunset header), OpenAPI Specification 3.2.1 and 3.1.2, Express 5.3.0, Zod 4.6.7, pg 8.23.1 (2026-10). The `Idempotency-Key` and `RateLimit` header fields are IETF drafts: check status before depending on them.

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

- Covered: resource and URL design, HTTP methods, status codes, headers, Problem Details, validation, pagination, filtering and sorting, conditional requests and optimistic concurrency, idempotency, long-running operations, rate limit signaling, versioning and deprecation, OpenAPI documents, contract tests.
- Not covered: GraphQL (graphql-expert); threat modeling, BOLA, mass assignment, webhook signing and gateway policy in depth (api-security-expert); token issuance and sessions (authentication-expert); framework-specific wiring (expressjs-expert, nestjs-expert); cache internals of Redis (redis-expert).

## 2. Core Expertise

- **HTTP semantics (RFC 9110)**: safe and idempotent methods, status code classes, `Allow`, `Location`, `Retry-After`, content negotiation, conditional requests (`ETag`, `If-Match`, `If-None-Match`, `If-Modified-Since`).
- **Caching (RFC 9111)**: `Cache-Control`, `Vary`, validators, shared vs private caches.
- **Errors**: RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, `instance` and extension members.
- **Contracts**: OpenAPI 3.1 (JSON Schema 2020-12 aligned) and 3.2 (adds the `query` method, `additionalOperations`, nested tags, `itemSchema` for streaming media types, `$self`). Pick the version your tooling supports.
- **Evolution**: additive changes, versioning, `Deprecation` (RFC 9745, structured-field date such as `@1688169599`) and `Sunset` (RFC 8594, HTTP date) headers, `Link` relations (RFC 8288).
- **Reliability**: idempotent retries (`Idempotency-Key` draft), optimistic concurrency, `429` with `Retry-After`, `202 Accepted` job resources.
- **Patching**: JSON Merge Patch (RFC 7396, `application/merge-patch+json`), JSON Patch (RFC 6902), and plain `PATCH` (RFC 5789) with a documented body format.

## 3. Workflow

1. List the resources (nouns) and relationships; decide ownership, the tenant boundary, and which identifiers are public.
2. For each resource define collection and item URLs, the supported methods, and the representation (fields, types, read-only fields).
3. Choose status codes per outcome (see decision rules) and the Problem Details `type` URIs for domain errors.
4. Decide pagination, filtering and sorting for every collection before the first release; add a hard maximum page size.
5. Decide concurrency control (`ETag` plus `If-Match`) and retry safety (idempotency) for each mutating operation.
6. Write or update the OpenAPI document first (spec-first) or generate it from code, then lint it in CI.
7. Implement with schema validation at the edge, tenant scoping in every query, and a single error-mapping layer.
8. Add contract and negative tests (wrong tenant, bad input, stale ETag, duplicate request, over-limit page size).
9. Plan evolution: what is additive, what needs a new version, and how deprecation is announced.

## 4. Decision Rules

- **URLs**: plural nouns, lowercase, hyphenated (`/v1/purchase-orders/{id}`); nest at most one level (`/orders/{id}/items`); identify the tenant from the credential, not the path or a client-supplied header.
- **Methods**: `GET` and `HEAD` safe; `PUT` and `DELETE` idempotent; `POST` for create-in-collection and actions; `PATCH` for partial update. Do not tunnel mutations through `GET`.
- **Create**: `201 Created` with `Location` and the representation; `202 Accepted` plus a status resource when work is asynchronous; `204 No Content` when there is nothing to return.
- **Validation errors**: `400` for malformed syntax (invalid JSON, bad query parameter format); `422` for well-formed but semantically invalid bodies; use one rule consistently and document it.
- **Authentication and authorization**: `401` (with `WWW-Authenticate`) for missing or invalid credentials; `403` when authenticated but not allowed; `404` for objects the caller may not know exist, including other tenants' objects.
- **Conflicts**: `409` for state conflicts (duplicate unique value, wrong state transition); `412` when an `If-Match`/`If-Unmodified-Since` precondition fails; `428` when a required precondition header is missing.
- **Rate limits**: `429` with `Retry-After`; `503` with `Retry-After` for planned unavailability.
- **Media type errors**: `415` unsupported request `Content-Type`; `406` when `Accept` cannot be satisfied; `405` with `Allow`.
- **Pagination**: cursor-based for large or changing collections; offset only for small, stable ones. Always cap `limit`.
- **Versioning**: avoid versions as long as changes are additive; when a break is unavoidable use a major version in the URL (`/v2/`) or a media type, and keep both in the contract.
- **Idempotency**: `PUT` and `DELETE` are idempotent by definition; require an idempotency key for non-idempotent `POST` that creates money-like or externally visible effects.
- **Errors in a 2xx body**: never; errors use 4xx or 5xx with Problem Details.

## 5. Coding Standards

- Validate every request at the edge with a strict schema (reject unknown fields on writes) and parse query parameters as typed values with bounds.
- Separate request and response schemas from database rows; return explicit fields only.
- Use one error type that maps to Problem Details; unexpected errors become a generic `500` with no stack trace, SQL or hostnames.
- JSON naming consistent across the API (`snake_case` or `camelCase`, not both); timestamps as RFC 3339 UTC strings; money as integer minor units plus a currency code; identifiers as strings.
- Use `Content-Type: application/json` for success, `application/problem+json` for errors; set `Cache-Control` explicitly on every response.
- Parameterize all SQL; never interpolate sort fields or identifiers from input, map them through an allowlist.
- Make handlers async and let a central error handler format failures (Express 5 forwards rejected promises to error middleware).

## 6. Project Structure

```
openapi/
  openapi.yaml            # source of truth, or generated and committed
src/
  http/
    app.ts                # Express app, security headers, body limits, routing
    errors.ts             # ApiError, Problem Details mapping, error middleware
    auth.ts               # populates req.auth { tenantId, userId, scopes }
    validate.ts           # Zod parsing helpers
    pagination.ts         # cursor encode/decode, limit bounds
  modules/orders/
    routes.ts             # route definitions
    schemas.ts            # Zod request and response schemas
    repository.ts         # SQL, always filtered by tenant_id
tests/
  contract/               # tests against the OpenAPI document
  api/                    # request-level tests incl. cross-tenant and negative cases
```

## 7. Design Patterns

- **Resource plus action**: model state transitions as sub-resources or action endpoints that return the updated resource (`POST /orders/{id}/cancellations`), not as arbitrary verbs on collections.
- **Optimistic concurrency**: return a strong `ETag` (for example the row version); require `If-Match` on `PUT`/`PATCH`/`DELETE`; return `412` on mismatch and `428` when absent.
- **Cursor pagination**: opaque cursor encoding the sort key and a tiebreaker; query with a keyset condition; return `next_cursor` or a `Link: <...>; rel="next"` header.
- **Idempotent create**: unique constraint on `(tenant_id, principal, idempotency_key)`; store the request hash and the response; replay on retry; `422` or `409` when the same key arrives with a different payload.
- **Async operations**: `202 Accepted` with `Location: /v1/operations/{id}`; the operation resource reports `pending`, `succeeded` or `failed` and links to the result.
- **Sparse and expanded representations**: `?fields=` for projection and `?expand=` for related resources, both allowlisted.
- **Bulk operations**: a dedicated endpoint with per-item results (`207`-style envelope in a normal JSON body is acceptable; document the semantics) and a hard item limit.
- **Hypermedia-lite**: include `Link` headers or `links` objects for pagination and the next valid actions, without requiring full HATEOAS.

## 8. Best Practices

- Keep responses stable: only add optional response fields and optional request parameters; never change types, meaning or defaults in place.
- Return the full updated representation from `POST`, `PUT` and `PATCH` so clients do not need a follow-up `GET`.
- Document every status code an operation can return, with its Problem Details `type`.
- Use `HEAD` and conditional `GET` (`If-None-Match` returning `304`) for expensive resources.
- Make list endpoints deterministic: explicit default sort with a unique tiebreaker.
- Treat filters as an allowlist of documented fields and operators; do not expose a free-form query language over the database.
- Support request correlation with a standard header your gateway already uses, and return it; do not invent per-service formats.
- Publish limits (page size, body size, rate) in the documentation and in the contract where possible.

## 9. Performance

- Keyset pagination keeps query cost constant; `OFFSET` scans and discards rows, and gets slower with depth. Avoid total counts on large tables, or make them optional and approximate.
- Index the filter and sort columns, starting with `tenant_id`, matching the keyset order.
- Use `ETag` and `Cache-Control` (`private` for per-user data, `public` only for data identical for everyone, `no-store` for sensitive data) and `Vary` for any header that changes the response.
- Compress responses (gzip or br) at the proxy; cap request body sizes.
- Avoid N+1 queries behind `expand`; load related rows in one query per relation.
- Prefer `HTTP/2` or `HTTP/3` at the edge; do not rely on connection-per-request patterns.
- Return `429` early from a cheap check, before doing expensive work.

## 10. Security

- Scope every read and every write by the tenant from the verified credential: `WHERE id = $1 AND tenant_id = $2`, including `UPDATE` and `DELETE`. Never trust a tenant id from the body, path or a header.
- Authorize per object and per field: strict write schemas (no mass assignment of `role`, `tenant_id`, `owner_id`), explicit response fields.
- Return `404` rather than `403` for objects in other tenants to avoid existence leaks.
- Validate and bound all input: body size, array lengths, string lengths, `limit`, nesting depth.
- Send `Cache-Control: no-store` on responses with credentials or personal data; never cache authenticated responses in shared caches without `Vary` and `private`.
- Avoid secrets and tokens in URLs and query strings; they end up in logs and referrers.
- CORS: allowlist exact origins; do not reflect arbitrary origins with credentials.
- Do not expose test, seed or debug endpoints in production builds.
- Error bodies must not reveal internals (stack traces, SQL, internal hostnames); `detail` is for safe, user-facing text.
- Rate limiting, request signing and gateway policy details: api-security-expert.

## 11. Testing

- Contract: validate responses against the OpenAPI schemas in tests, and lint the document in CI (Redocly CLI or Spectral).
- Property-based or schema-driven fuzzing against the running API (for example Schemathesis) to find 500s and schema drift.
- Negative cases for every endpoint: another tenant's id (expect 404), unknown fields, oversized page limit, malformed cursor, stale `If-Match`, missing `If-Match`, repeated idempotency key with a different body.
- Request-level tests with `supertest` against the Express app and a real PostgreSQL (Testcontainers or a CI service), not a mocked repository.
- Backward-compatibility check: diff the OpenAPI document against the released one (for example `oasdiff` or Redocly's changelog tooling) and fail on breaking changes.

## 12. Review Checklist

- [ ] Resource URLs are nouns; the tenant comes from the credential.
- [ ] Each operation lists its success and error statuses; errors use Problem Details.
- [ ] Mutations validate strictly and return the updated representation; `POST` create returns `201` and `Location`.
- [ ] Every collection has a default sort, a unique tiebreaker, a max page size and cursor pagination if it can grow.
- [ ] Updates use `If-Match`; non-idempotent creates have an idempotency story.
- [ ] Cross-tenant tests exist for read, update and delete.
- [ ] Cache headers are explicit and correct for the data's sensitivity.
- [ ] Changes are additive, or a new version plus `Deprecation`/`Sunset` plan exists.
- [ ] The OpenAPI document matches the implementation and passes lint.

## 13. Production Notes

- Deprecation: send `Deprecation: @<unix-seconds>` (RFC 9745) once an endpoint or version is deprecated, `Sunset: <HTTP date>` (RFC 8594) with the retirement time (not earlier than the deprecation time), and a `Link` with `rel="deprecation"` to the migration guide. Retire on the announced date.
- Keep old versions running with their own contract until the sunset date; monitor per-version traffic to know who is still calling.
- Rate limit signaling: `Retry-After` is the stable mechanism; the `RateLimit` and `RateLimit-Policy` fields are an IETF draft whose syntax has changed between revisions (draft-ietf-httpapi-ratelimit-headers-11 at the time of writing), so check its status before emitting them, and avoid new `X-RateLimit-*` conventions unless clients already rely on them.
- `Idempotency-Key` is an IETF draft (draft-ietf-httpapi-idempotency-key-header, check status); the semantics in this skill follow its general approach but document your own behavior in the API reference.
- Behind proxies, make sure the app sees the real scheme and client address (trust proxy settings) and that gateways do not strip `ETag`, `Location` or `Retry-After`.
- Details: [references/http-semantics-and-status-codes.md](references/http-semantics-and-status-codes.md), [references/openapi-and-versioning.md](references/openapi-and-versioning.md), [references/pagination-idempotency-and-caching.md](references/pagination-idempotency-and-caching.md).

## 14. Examples

Problem Details error type and central handler (Express 5, Zod 4):

```ts
import type { NextFunction, Request, Response } from "express";
import { ZodError } from "zod";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly type: string, // URI that documents this problem type
    readonly title: string,
    readonly detail?: string,
    readonly extensions: Record<string, unknown> = {},
  ) {
    super(title);
  }
}

export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction) {
  let problem: Record<string, unknown>;
  if (err instanceof ApiError) {
    problem = { type: err.type, title: err.title, status: err.status, detail: err.detail, ...err.extensions };
  } else if (err instanceof ZodError) {
    problem = {
      type: "https://api.example.com/problems/validation-error",
      title: "Validation failed",
      status: 422,
      errors: err.issues.map((i) => ({ pointer: "/" + i.path.join("/"), message: i.message })),
    };
  } else {
    problem = { type: "about:blank", title: "Internal Server Error", status: 500 }; // no internals
  }
  res.status(problem.status as number).type("application/problem+json").json({ ...problem, instance: req.originalUrl.split("?")[0] });
}
```

Tenant-scoped item and list routes with ETag, `If-Match` and keyset pagination:

```ts
import { Router } from "express";
import { z } from "zod";
import { Pool } from "pg";
import { ApiError } from "./errors";

declare module "express-serve-static-core" {
  interface Request { auth?: { tenantId: string; userId: string } } // set by the auth middleware
}

const pool = new Pool(); // connection settings from PG* environment variables
export const orders = Router();

const idParam = z.object({ id: z.uuid() });
const listQuery = z.strictObject({
  limit: z.coerce.number().int().min(1).max(100).default(25),
  cursor: z.string().max(200).optional(),
  status: z.enum(["open", "paid", "cancelled"]).optional(),
});
const patchBody = z.strictObject({ status: z.enum(["open", "paid", "cancelled"]) }); // no tenant_id, no total

const need = (req: { auth?: { tenantId: string; userId: string } }) => {
  if (!req.auth) throw new ApiError(401, "about:blank", "Unauthorized");
  return req.auth;
};

orders.get("/", async (req, res) => {
  const { tenantId } = need(req);
  const q = listQuery.parse(req.query);
  let after: { c: string; i: string } | null = null;
  if (q.cursor) {
    try { after = z.object({ c: z.iso.datetime(), i: z.uuid() }).parse(JSON.parse(Buffer.from(q.cursor, "base64url").toString())); }
    catch { throw new ApiError(400, "https://api.example.com/problems/invalid-cursor", "Invalid cursor"); }
  }
  const { rows } = await pool.query(
    `SELECT id, status, total_cents, version, created_at FROM orders
      WHERE tenant_id = $1
        AND ($2::text IS NULL OR status = $2)
        AND ($3::timestamptz IS NULL OR (created_at, id) < ($3::timestamptz, $4::uuid))
      ORDER BY created_at DESC, id DESC LIMIT $5`,
    [tenantId, q.status ?? null, after?.c ?? null, after?.i ?? null, q.limit + 1],
  );
  const page = rows.slice(0, q.limit);
  const last = page[page.length - 1];
  const next = rows.length > q.limit && last
    ? Buffer.from(JSON.stringify({ c: last.created_at.toISOString(), i: last.id })).toString("base64url")
    : null;
  res.set("Cache-Control", "private, no-cache").json({ data: page, next_cursor: next });
});

orders.patch("/:id", async (req, res) => {
  const { tenantId } = need(req);
  const { id } = idParam.parse(req.params);
  const match = /^"(\d+)"$/.exec(req.get("If-Match") ?? "");
  if (!match) throw new ApiError(428, "https://api.example.com/problems/precondition-required", "If-Match header required");
  const body = patchBody.parse(req.body);
  const { rows } = await pool.query(
    `UPDATE orders SET status = $3, version = version + 1
      WHERE id = $1 AND tenant_id = $2 AND version = $4
      RETURNING id, status, total_cents, version, created_at`,
    [id, tenantId, body.status, Number(match[1])],
  );
  if (rows.length === 0) {
    const exists = await pool.query("SELECT 1 FROM orders WHERE id = $1 AND tenant_id = $2", [id, tenantId]);
    if (exists.rowCount === 0) throw new ApiError(404, "about:blank", "Not Found");
    throw new ApiError(412, "https://api.example.com/problems/stale-version", "Resource changed since it was read");
  }
  res.set("ETag", `"${rows[0].version}"`).set("Cache-Control", "private, no-cache").json(rows[0]);
});
```

OpenAPI 3.1 fragment for the same operation:

```yaml
openapi: 3.1.0
info: { title: Orders API, version: 1.0.0 }
paths:
  /v1/orders/{id}:
    patch:
      operationId: updateOrder
      parameters:
        - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
        - { name: If-Match, in: header, required: true, schema: { type: string } }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/OrderPatch" }
      responses:
        "200": { description: Updated, headers: { ETag: { schema: { type: string } } }, content: { application/json: { schema: { $ref: "#/components/schemas/Order" } } } }
        "404": { $ref: "#/components/responses/Problem" }
        "412": { $ref: "#/components/responses/Problem" }
        "422": { $ref: "#/components/responses/Problem" }
        "428": { $ref: "#/components/responses/Problem" }
      security: [{ bearerAuth: [] }]
```

## 15. Common Mistakes

- Returning `200` with an error payload, or using `500` for client mistakes.
- `403` vs `404` confusion that leaks whether another tenant's object exists.
- Loading by id and checking ownership afterwards, or `UPDATE ... WHERE id = $1` without the tenant condition.
- Accepting `tenant_id`, `role` or `owner_id` in write bodies (mass assignment).
- Offset pagination on large tables, unbounded `limit`, or cursors that are not tied to a stable unique sort key.
- Using `PUT` for partial updates, or `POST` for everything.
- Retrying non-idempotent `POST` without an idempotency mechanism, creating duplicates.
- Ignoring `Vary` and `Cache-Control` so shared caches serve one user's data to another.
- Breaking changes inside a version: renamed fields, changed types, tightened validation, new required parameters.
- Treating `Idempotency-Key`, `RateLimit` or QUERY as finished standards without checking draft status.
- Citing obsolete RFCs (7807, 7231, 7232) instead of RFC 9457 and RFC 9110/9111.
- Putting secrets, tokens or personal data in URLs.
- Exposing stack traces or database errors in Problem Details.

## 16. References

- [references/http-semantics-and-status-codes.md](references/http-semantics-and-status-codes.md): method properties, status code decision table, headers, conditional requests, caching, Problem Details.
- [references/openapi-and-versioning.md](references/openapi-and-versioning.md): OpenAPI 3.1 and 3.2, document skeleton, linting and diffing, versioning strategies, deprecation and sunset.
- [references/pagination-idempotency-and-caching.md](references/pagination-idempotency-and-caching.md): keyset pagination and filtering, idempotency record design, rate limit signaling, ETag and caching recipes, async operations.
- Official specs: https://www.rfc-editor.org/rfc/rfc9110 , https://www.rfc-editor.org/rfc/rfc9457 , https://spec.openapis.org/oas/latest.html , https://www.rfc-editor.org/rfc/rfc9745
