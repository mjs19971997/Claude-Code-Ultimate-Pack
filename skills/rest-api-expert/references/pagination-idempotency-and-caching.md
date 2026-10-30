# Pagination, Idempotency, Rate Limit Signaling and Caching

Recipes for collections, retry-safe writes, limit signaling, ETag handling and long-running operations. Examples use TypeScript, Express 5 and PostgreSQL (`pg`), always scoped by the authenticated tenant. Verified 2026-10: the `Idempotency-Key` header (draft-ietf-httpapi-idempotency-key-header, revision 07 seen) and the `RateLimit`/`RateLimit-Policy` header fields (draft-ietf-httpapi-ratelimit-headers, revision 11 seen) are IETF drafts: check status before depending on them.

## Contents
- Keyset pagination and filtering
- Link headers
- Idempotency records
- Rate limit signaling
- ETag recipes
- Long-running operations
- Bulk and partial responses

## Keyset pagination and filtering

- Offset pagination (`?offset=1000&limit=25`) is simple but slow deep into a table and unstable when rows change between requests. Use it only for small, stable collections.
- Keyset (cursor) pagination filters on the last seen sort key: `WHERE tenant_id = $1 AND (created_at, id) < ($2, $3) ORDER BY created_at DESC, id DESC LIMIT $4`. The sort needs a unique tiebreaker (`id`) and a matching composite index starting with `tenant_id`.
- Fetch `limit + 1` rows to know whether a next page exists without a count query.
- The cursor is opaque to clients (base64url of JSON). It carries only a position; the tenant filter is always applied from the credential, so a forged cursor cannot cross a tenant boundary. Validate its shape with a schema; return `400` for a malformed one.
- Changing the sort or filter invalidates the cursor; include the sort in the cursor payload and reject mismatches.
- Cap `limit` (for example 100) and default it (for example 25); document both in the contract.
- Total counts are expensive; offer them only on request (`?include=total`) or as an approximate estimate.
- Filtering: allowlisted fields and a small operator set (`?status=open&created_after=2026-01-01T00:00:00Z`). Map public names to columns through an object, never interpolate input into SQL.
- Sorting: `?sort=-created_at,id` parsed against an allowlist; always append the unique tiebreaker.

```ts
const SORTABLE = { created_at: "created_at", total: "total_cents" } as const; // public name -> column
type SortKey = keyof typeof SORTABLE;

export function orderBy(sort: string | undefined) {
  const [raw = "-created_at"] = (sort ?? "").split(",");
  const desc = raw.startsWith("-");
  const key = raw.replace(/^-/, "") as SortKey;
  if (!(key in SORTABLE)) throw new Error("unsupported sort"); // map to a 400 Problem Details response
  return `${SORTABLE[key]} ${desc ? "DESC" : "ASC"}, id ${desc ? "DESC" : "ASC"}`; // value comes from the allowlist only
}
```

## Link headers

RFC 8288 `Link` headers carry pagination without changing the body:

```
Link: <https://api.example.com/v1/orders?cursor=eyJjIjoi...&limit=25>; rel="next"
```

- Use `rel="next"` and `rel="prev"`; `first` and `last` only when cheap to compute (rarely with keyset).
- Keep a `next_cursor` field in the JSON body as well when clients commonly ignore headers; pick one primary mechanism and document it.

## Idempotency records

`POST` is not idempotent by definition. A retry after a timeout can create duplicates. The `Idempotency-Key` request header (IETF draft, check status) lets a client supply a unique key per logical operation; the server returns the stored result for repeats.

Design:
- Scope the key by tenant and authenticated principal, so keys from different callers never collide or leak responses.
- Store the key with a hash of the method, path and body, the state, the response status and body, and an expiry (24 hours is a common choice; document yours).
- Same key and same request hash after completion: replay the stored response. Same key, different request hash: reject (`422` or `409`, documented). Same key while the first request is still running: `409` with `Retry-After`. Missing key where you require it: `400`.
- Insert the record in the same database transaction as the business write when possible, so both commit or neither does.
- Keys are client-generated random values (UUIDv4 or similar), length-limited and validated.

```sql
CREATE TABLE idempotency_keys (
  tenant_id     uuid        NOT NULL,
  principal_id  uuid        NOT NULL,
  key           text        NOT NULL CHECK (char_length(key) <= 128),
  request_hash  bytea       NOT NULL,
  state         text        NOT NULL CHECK (state IN ('in_progress', 'done')),
  status_code   integer,
  response_body jsonb,
  expires_at    timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, principal_id, key)
);
```

```ts
import { createHash } from "node:crypto";

// returns the stored response when this is a safe replay, or null when the caller should run the operation
export async function claimIdempotency(
  pool: import("pg").Pool, tenantId: string, principalId: string, key: string, method: string, path: string, rawBody: Buffer,
) {
  const hash = createHash("sha256").update(method).update("\0").update(path).update("\0").update(rawBody).digest();
  const ins = await pool.query(
    `INSERT INTO idempotency_keys (tenant_id, principal_id, key, request_hash, state, expires_at)
     VALUES ($1, $2, $3, $4, 'in_progress', now() + interval '24 hours')
     ON CONFLICT DO NOTHING RETURNING 1`,
    [tenantId, principalId, key, hash],
  );
  if (ins.rowCount === 1) return { replay: null as null };
  const { rows } = await pool.query(
    "SELECT request_hash, state, status_code, response_body FROM idempotency_keys WHERE tenant_id = $1 AND principal_id = $2 AND key = $3 AND expires_at > now()",
    [tenantId, principalId, key],
  );
  const rec = rows[0];
  if (!rec) return { replay: null }; // expired between statements; caller retries the claim
  if (!hash.equals(rec.request_hash)) return { conflict: "key reused with a different request" as const };
  if (rec.state === "in_progress") return { conflict: "request in progress" as const };
  return { replay: { status: rec.status_code as number, body: rec.response_body } };
}
```

- Run a periodic job that deletes expired rows.
- Even with idempotency keys, enforce natural uniqueness in the database for money-like operations (unique order reference per tenant).
- Redis can hold idempotency records for high-throughput paths; see redis-expert.

## Rate limit signaling

- On limit exceeded return `429` with Problem Details and `Retry-After` (seconds). `Retry-After` is defined in RFC 9110 and is the stable signal.
- The `RateLimit` and `RateLimit-Policy` header fields are being standardized by the IETF HTTPAPI working group (draft-ietf-httpapi-ratelimit-headers); earlier drafts used `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`, and the syntax has changed between revisions. IETF draft, check status and the current syntax before implementing; if clients already rely on the legacy fields, keep them stable until you migrate with notice.
- Clients should treat these headers as hints, never as authorization controls.
- Limit by authenticated principal and tenant first, then by IP; algorithms and enforcement are in api-security-expert and redis-expert.
- Document limits per operation group and publish them in the API reference.

## ETag recipes

- Row-version ETag: `ETag: "<version>"`, updated with `version = version + 1` in the same `UPDATE` that checks `version = $n` (see SKILL.md). Strong and cheap.
- Content-hash ETag for read-only or computed resources: hash the serialized body; compute after serialization so the ETag matches the bytes sent.
- Conditional `GET`:

```ts
router.get("/:id", async (req, res) => {
  const { tenantId } = req.auth!; // set by the auth middleware
  const id = z.uuid().parse(req.params.id); // 422 via the central error handler
  const { rows } = await pool.query(
    "SELECT id, status, total_cents, version FROM orders WHERE id = $1 AND tenant_id = $2",
    [id, tenantId],
  );
  if (rows.length === 0) throw new ApiError(404, "about:blank", "Not Found");
  const etag = `"${rows[0].version}"`;
  res.set({ ETag: etag, "Cache-Control": "private, no-cache" });
  if (req.get("If-None-Match") === etag) return void res.status(304).end(); // simple exact match
  res.json(rows[0]);
});
```

- Express computes weak ETags for response bodies by default; disable or replace with your own for resources where update preconditions matter (`app.set("etag", false)` and set explicitly).
- For `If-None-Match` lists or `*`, parse per RFC 9110 rather than comparing exact strings when clients send multiple values.

## Long-running operations

1. `POST /v1/exports` returns `202 Accepted` with `Location: /v1/operations/{id}` and a small body `{ "id": ..., "state": "pending" }`.
2. `GET /v1/operations/{id}` returns `200` with `state` (`pending`, `running`, `succeeded`, `failed`), progress if known, `Retry-After` as a polling hint, and links to the result or a Problem Details object on failure.
3. Operation resources are tenant-scoped like everything else; return `404` for another tenant's operation id.
4. Provide `DELETE /v1/operations/{id}` to cancel when cancellation is supported.
5. Result resources expire; document how long and use `410 Gone` afterwards.
6. Webhook notifications are an optional complement; see api-security-expert for signing.

## Bulk and partial responses

- Bulk endpoints: accept a bounded array (document the maximum, for example 100), process items independently or atomically (document which), and return per-item results with their own status and Problem Details; use an overall `200` for per-item outcomes or `4xx` if the whole request is invalid.
- Partial responses: `?fields=id,status` with an allowlist; keep `fields` in the URL (query parameters are part of the cache key; `Vary` only covers headers) so cached variants stay distinct.
- Expansion: `?expand=customer` with an allowlist and a limit on depth; authorize each expanded object under the same tenant scope.
- `Prefer: return=minimal` can reduce response size for writes where clients already know the result; document support.
