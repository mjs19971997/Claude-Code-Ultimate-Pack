---
name: api-security-expert
description: >-
  Secures REST, GraphQL and gRPC APIs against the OWASP API Security Top 10 (2023): object- and property-level authorization (BOLA, mass assignment), rate limiting and resource caps, webhook and request signing, replay prevention, API keys, mTLS, CORS, gateways and API inventory. Use when designing or reviewing API endpoints, DTOs and response shapes, pagination limits, Redis rate limiters, webhook receivers, HMAC signatures, GraphQL depth and cost limits, API gateway (Kong, AWS API Gateway, Cloudflare) policies, or third-party API consumption. Not for general code-level flaws such as injection, XSS or path traversal (use secure-coding-expert), login, sessions, JWT or OAuth flows (use authentication-expert), designing roles and policy engines (use authorization-expert), or REST resource design (use rest-api-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# API Security Expert

This skill covers the controls that are specific to APIs: authorizing every object and property an endpoint touches, bounding the resources a caller can consume, protecting business flows, verifying signed requests and webhooks, and keeping an inventory of what is exposed. It applies to REST, GraphQL and gRPC. It assumes the caller is already authenticated (authentication-expert) and that a permission model exists (authorization-expert); here the focus is enforcing them correctly at the API layer.

> Verified against OWASP API Security Top 10 2023 (still the current edition), Express 5, Zod 4, ioredis, Apollo Server 5 and GraphQL Armor (2026-10).

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

- Covered: OWASP API Security Top 10 2023, rate limiting and quotas, pagination and payload caps, webhook verification, HMAC request signing, replay windows, API keys, mTLS between services, CORS for APIs, gateway policies, GraphQL hardening, API inventory and deprecation.
- Not covered: injection, XSS, SSRF mechanics and upload handling in general (secure-coding-expert); credential, session and token issuance (authentication-expert); role and policy design, Row-Level Security (authorization-expert); URL and resource modeling, status code semantics (rest-api-expert).

## 2. Core Expertise

OWASP API Security Top 10 2023:

| ID | Risk | Primary defense |
|---|---|---|
| API1 | Broken Object Level Authorization (BOLA) | Scope every query by owner or tenant from the verified principal; never trust an id alone |
| API2 | Broken Authentication | Strict token validation, credential stuffing protection on auth endpoints (authentication-expert) |
| API3 | Broken Object Property Level Authorization | Strict input DTOs (no mass assignment) and explicit response shapes (no excessive data exposure) |
| API4 | Unrestricted Resource Consumption | Rate limits, quotas, page-size caps, body-size caps, timeouts, GraphQL cost limits, spend limits on paid downstream APIs |
| API5 | Broken Function Level Authorization | Deny-by-default route permissions; admin routes separated and checked |
| API6 | Unrestricted Access to Sensitive Business Flows | Per-flow limits, device and behavior signals, idempotency, server-side state machines |
| API7 | Server Side Request Forgery | Allowlists and dial-time IP checks for any URL the API fetches (secure-coding-expert) |
| API8 | Security Misconfiguration | Strict CORS, TLS, no verbose errors, consistent gateway policy, disabled unused methods |
| API9 | Improper Inventory Management | OpenAPI or schema as source of truth, discovered vs documented diff, retired versions actually shut down |
| API10 | Unsafe Consumption of APIs | Validate third-party responses, TLS, timeouts, size caps, no blind redirects |

Other areas:
- **Rate limiting algorithms**: fixed window (simple, bursty at edges), sliding window log or counter (smoother), token bucket (allows bursts up to a capacity), GCRA. Distributed state in Redis or at the gateway.
- **Request signing**: HMAC-SHA256 over a canonical string (method, path, query, body hash, timestamp, nonce), constant-time comparison, a short timestamp window and a nonce cache.
- **Webhooks**: verify the provider's signature over the raw body before parsing; check the timestamp; deduplicate by event id; respond fast and process asynchronously.
- **Service identity**: mTLS (often via a service mesh) or signed workload tokens; API keys only for identifying a calling application, not a user.
- **GraphQL**: depth, alias, token and cost limits; introspection and field suggestions off in production for private APIs; operation safelisting; field-level authorization in resolvers; batched-query limits.

## 3. Workflow

1. Inventory the surface: every route, method, GraphQL operation and gRPC method, with its auth requirement, from the OpenAPI document or schema.
2. For each endpoint, name the object(s) it reads or writes and how ownership or tenancy is derived from the verified principal (API1).
3. Define the input DTO (allowed fields only) and the response DTO (fields this caller may see) (API3).
4. Assign the function-level permission and confirm deny by default for anything unlisted (API5).
5. Set limits: rate per principal and per IP, page size, body size, timeouts, and for GraphQL depth and cost (API4).
6. Identify sensitive business flows (checkout, signup, coupon redeem, OTP send) and add flow-specific limits and idempotency (API6).
7. For inbound callbacks and service calls, define signature or mTLS verification and the replay window.
8. For outbound calls to third parties, define validation, timeouts and size caps of the responses (API10).
9. Write negative tests (another user's id, extra fields, over-limit pages, replayed signatures) before shipping.
10. Register the endpoint in the inventory with owner, version and deprecation date (API9).

## 4. Decision Rules

- Scope queries by owner or tenant in the data access layer (`WHERE id = $1 AND tenant_id = $2`) rather than loading by id and checking afterwards; it also prevents leaking existence through timing.
- Return 404 for objects the caller may not see; 403 when the caller may know the object exists but cannot act on it.
- Unguessable ids (UUIDv4/v7, random strings) reduce enumeration but never replace the authorization check.
- Token bucket for interactive APIs that tolerate bursts; fixed or sliding window for simple quotas; enforce coarse limits at the gateway and fine-grained per-principal limits in the service.
- Rate-limit identity order: authenticated principal, then API key, then client IP (with the proxy chain configured so `req.ip` is the real client).
- mTLS for service-to-service inside infrastructure you control; HMAC signing when the caller cannot hold a client certificate; OAuth 2.0 client credentials when a central authorization server already exists.
- API keys go in a header, never in the URL; store only a hash of the key and show it once at creation.
- Cursor pagination for large or fast-changing collections; enforce a hard `maxPageSize` either way.
- GraphQL on a private API: introspection off in production and an operation safelist. Public GraphQL APIs keep introspection but must enforce cost limits and field authorization.
- Version breaking changes explicitly and publish `Deprecation`/`Sunset` headers before retiring a version; retired versions are removed, not just undocumented.

## 5. Coding Standards

- Input DTOs use `z.strictObject` (Zod 4) or equivalent so unknown properties fail; never pass `req.body` to an ORM `create`/`update`.
- Response DTOs are explicit mappers (`toOrderView(order)`), never `res.json(entity)`.
- Every handler derives `userId` and `tenantId` from the verified principal (`req.auth`), never from the body, query or a client header.
- Every list endpoint takes `limit` with a default and a hard maximum, validated by the schema.
- Every outbound call has a timeout and a response size cap; third-party responses are validated with a schema before use.
- Webhook routes read the raw body (`express.raw`) and verify before `JSON.parse`.
- Error bodies follow one shape (for example RFC 9457 problem details) and never include stack traces, SQL or internal hostnames.
- Name middleware by purpose: `requirePermission('order:read')`, `rateLimit({ scope: 'user' })`, `verifyWebhook('stripe')`.

## 6. Project Structure

```
src/
├── api/
│   ├── orders/
│   │   ├── orders.routes.ts       # route + requirePermission + rateLimit
│   │   ├── orders.schema.ts       # strict input DTOs, response mappers
│   │   └── orders.repository.ts   # tenant/owner-scoped queries
│   └── webhooks/
│       └── payments.routes.ts     # raw body + signature + replay check
├── middleware/
│   ├── auth.ts                    # attaches verified req.auth (authentication-expert)
│   ├── permissions.ts             # function-level checks (authorization-expert)
│   └── rate-limit.ts              # Redis-backed limiter
├── graphql/
│   ├── server.ts                  # Apollo Server + GraphQL Armor + safelist
│   └── safelist.json              # approved operation hashes
└── openapi/
    └── openapi.yaml               # inventory source of truth
tests/api-security/                # BOLA, BOPLA, limits, webhook replay
```

## 7. Design Patterns

- **Scoped repository**: repository methods require a `Principal` argument and always add the owner or tenant predicate, for reads and writes alike.
- **Input and output DTOs**: separate schemas per operation (`orderCreate`, `orderUpdate`, `orderView`, `orderAdminView`) so writable and readable fields are explicit per role.
- **Layered limits**: gateway (per IP, global), service (per principal and per route), business flow (per account per action per day).
- **Idempotency keys**: `Idempotency-Key` header stored with the response for unsafe operations such as payments, so retries cannot double-execute.
- **Signed requests**: canonical string plus HMAC plus timestamp plus nonce; see [references/request-signing.md](references/request-signing.md).
- **Verify, then enqueue**: webhook handlers verify and store the event id, return 2xx quickly and process from a queue.

## 8. Best Practices

- Generate and lint the OpenAPI document in CI; diff it against observed traffic (gateway logs, API discovery tools) to find shadow endpoints.
- Configure CORS with an explicit origin allowlist, `Vary: Origin`, and credentials only for origins that need them; CORS is not an access control for non-browser clients.
- Set body-size limits in the framework (`express.json({ limit: '100kb' })`) and at the proxy.
- Use `Retry-After` on 429 responses. Rate-limit header names are being standardized by the IETF HTTP API working group; check the current draft before choosing `RateLimit` header formats.
- Cap the cost of calls to paid downstream services (SMS, email, LLM APIs) per account, not only per request.
- Do not expose internal ids, flags or audit fields in responses just because the ORM returned them.
- Keep admin and internal APIs on a separate host or network path with stronger authentication.

## 9. Performance

- One atomic Redis round trip per rate-limit check (Lua script or a single `MULTI`); avoid read-then-write races.
- Push ownership filters into SQL so authorization does not need a second query; index `(tenant_id, id)`.
- GraphQL cost analysis runs once per operation at validation time; cache parsed and validated safelisted operations.
- Signature verification is cheap (HMAC); nonce caches need a TTL equal to the timestamp window so memory stays bounded.

## 10. Security

- Fail closed when the rate-limit store is unavailable for sensitive routes (login, OTP, payment); for low-risk reads, a documented fail-open with gateway limits still in place is acceptable.
- Trust `X-Forwarded-For` only from known proxies (`app.set('trust proxy', ...)` with explicit hops or addresses).
- Store webhook secrets and HMAC keys in a secret manager; support two active secrets during rotation.
- Log BOLA-shaped denials (valid principal, foreign object id) and alert on bursts; they indicate enumeration.
- gRPC: enable TLS, apply per-method authorization in interceptors, and cap message size (`grpc.max_receive_message_length` or the language equivalent).

## 11. Testing

- BOLA: user A requests, updates and deletes user B's object by id, including through nested routes, batch endpoints and GraphQL node lookups; all must fail.
- BOPLA: send extra fields (`role`, `tenantId`, `isVerified`, `price`) on create and update; they must be rejected. Assert responses do not contain non-whitelisted fields.
- BFLA: call admin routes with a normal user token and with tokens from another tenant.
- Limits: `limit=1000000`, oversized bodies, deep and aliased GraphQL queries, many operations in one batch; expect 400/413/429.
- Webhooks: wrong signature, missing timestamp, timestamp outside the window, replayed valid request, modified body; all rejected.
- Run these as integration tests against a real database and Redis (for example with Testcontainers), plus DAST against staging.

## 12. Review Checklist

- [ ] Every object access is scoped by owner or tenant from the verified principal, for reads, updates, deletes and batch operations.
- [ ] Input DTOs reject unknown fields; responses are mapped explicitly per role.
- [ ] Function-level permissions are declared for every route and default to deny.
- [ ] Rate limits exist per principal and per IP; sensitive flows have their own limits.
- [ ] Page size, body size, timeouts and GraphQL depth/cost are capped.
- [ ] Webhooks verify the signature over the raw body, check the timestamp and deduplicate events.
- [ ] Signed service requests use constant-time comparison and a nonce cache.
- [ ] API keys are sent in headers, stored hashed, scoped and rotatable.
- [ ] CORS uses an explicit allowlist; no `*` with credentials.
- [ ] Third-party responses are validated, size-capped and time-limited.
- [ ] The endpoint is in the OpenAPI inventory with an owner; deprecated versions have a sunset date.
- [ ] Negative tests for BOLA, BOPLA, BFLA, limits and replay are present and pass.

## 13. Production Notes

- Watch 401/403/404 ratios per principal; a single account producing many 404s across sequential ids is an enumeration signal.
- Track 429s by route and principal so limits can be tuned without disabling them.
- Keep gateway and service limits in configuration with change review; emergency overrides expire automatically.
- Alert on webhook signature failures from a provider's IP ranges; they usually mean a rotated secret or an attack.
- Remove retired API versions at the gateway on the sunset date and monitor for remaining callers beforehand.

## 14. Examples

### Example 1: BOLA- and BOPLA-safe order endpoints (Express 5, Zod 4, pg)

```typescript
import { Router, type Request } from 'express';
import { z } from 'zod';
import type { Pool } from 'pg';

type Principal = { userId: string; tenantId: string };
declare module 'express-serve-static-core' {
  interface Request { auth?: Principal } // set by the authentication middleware after token verification
}

const orderUpdate = z.strictObject({            // unknown keys such as status or tenantId fail
  shippingAddress: z.string().min(1).max(500),
  note: z.string().max(1000).optional(),
});
const listQuery = z.strictObject({ limit: z.coerce.number().int().min(1).max(100).default(20) });

const toOrderView = (row: { id: string; total_cents: number; status: string; shipping_address: string }) => ({
  id: row.id, totalCents: row.total_cents, status: row.status, shippingAddress: row.shipping_address,
});

function principal(req: Request): Principal {
  if (!req.auth) throw Object.assign(new Error('unauthenticated'), { status: 401 });
  return req.auth;
}

export function ordersRouter(db: Pool): Router {
  const r = Router();

  r.get('/orders', async (req, res) => {
    const p = principal(req);
    const { limit } = listQuery.parse(req.query);
    const { rows } = await db.query(
      `SELECT id, total_cents, status, shipping_address FROM orders
        WHERE tenant_id = $1 AND user_id = $2 ORDER BY created_at DESC LIMIT $3`,
      [p.tenantId, p.userId, limit],
    );
    res.json({ items: rows.map(toOrderView) });
  });

  r.patch('/orders/:id', async (req, res) => {
    const p = principal(req);
    const id = z.uuid().parse(req.params.id);
    const input = orderUpdate.parse(req.body);
    // Ownership is part of the write itself, so there is no check-then-update gap.
    const { rows } = await db.query(
      `UPDATE orders SET shipping_address = $1, note = $2, updated_at = now()
        WHERE id = $3 AND tenant_id = $4 AND user_id = $5 AND status = 'pending'
        RETURNING id, total_cents, status, shipping_address`,
      [input.shippingAddress, input.note ?? null, id, p.tenantId, p.userId],
    );
    if (rows.length === 0) return res.status(404).json({ error: 'not_found' });
    res.json(toOrderView(rows[0]));
  });

  return r;
}
```

Express 5 forwards rejected promises (including `ZodError`) to the error middleware, which maps them to 400 problem responses without echoing internals.

### Example 2: Atomic Redis rate limiter (fixed window, ioredis)

```typescript
import type { RequestHandler } from 'express';
import type { Redis } from 'ioredis';

const SCRIPT = `
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('PTTL', KEYS[1])}
`;

export function rateLimit(redis: Redis, opts: { name: string; max: number; windowMs: number; failOpen?: boolean }): RequestHandler {
  return async (req, res, next) => {
    const who = req.auth?.userId ?? `ip:${req.ip}`; // req.ip is correct only with 'trust proxy' configured
    const key = `rl:${opts.name}:${who}`;
    let count: number;
    let ttl: number;
    try {
      [count, ttl] = (await redis.eval(SCRIPT, 1, key, opts.windowMs)) as [number, number];
    } catch (err) {
      if (opts.failOpen) return next();
      return next(err); // fail closed by default
    }
    if (count > opts.max) {
      res.setHeader('Retry-After', String(Math.ceil(Math.max(ttl, 0) / 1000)));
      return res.status(429).json({ error: 'rate_limited' });
    }
    next();
  };
}

// app.post('/auth/otp', rateLimit(redis, { name: 'otp', max: 5, windowMs: 15 * 60_000 }), sendOtp);
```

A fixed window allows up to twice `max` across a window boundary; use a sliding-window or token-bucket script, or the gateway's limiter, when that matters.

### Example 3: Webhook verification with timestamp and replay protection

The scheme below (`t=<unix>,v1=<hex hmac>` over `"<t>.<raw body>"`) is a common provider pattern; follow the provider's own documented format and prefer its official SDK verifier when one exists.

```typescript
import express, { Router } from 'express';
import { createHmac, timingSafeEqual } from 'node:crypto';
import type { Redis } from 'ioredis';

const TOLERANCE_S = 300;

function verify(header: string | undefined, raw: Buffer, secrets: string[], now = Date.now()): boolean {
  const parts = Object.fromEntries((header ?? '').split(',').map((kv) => kv.split('=', 2) as [string, string]));
  const t = Number(parts.t);
  if (!Number.isInteger(t) || Math.abs(now / 1000 - t) > TOLERANCE_S || !/^[0-9a-f]{64}$/.test(parts.v1 ?? '')) return false;
  const received = Buffer.from(parts.v1, 'hex');
  return secrets.some((secret) => {   // two secrets are active during rotation
    const expected = createHmac('sha256', secret).update(`${t}.`).update(raw).digest();
    return timingSafeEqual(expected, received);
  });
}

export function paymentsWebhook(redis: Redis, secrets: string[], enqueue: (e: unknown) => Promise<void>): Router {
  const r = Router();
  r.post('/webhooks/payments', express.raw({ type: 'application/json', limit: '256kb' }), async (req, res) => {
    const raw = req.body as Buffer;
    if (!verify(req.get('Webhook-Signature'), raw, secrets)) return res.status(400).end();
    const event = JSON.parse(raw.toString('utf8')) as { id?: unknown };
    if (typeof event.id !== 'string') return res.status(400).end();
    // Deduplicate: SET NX with a TTL longer than the tolerance window.
    const first = await redis.set(`wh:payments:${event.id}`, '1', 'EX', 24 * 3600, 'NX');
    if (first === 'OK') {
      try {
        await enqueue(event);
      } catch (err) {
        await redis.del(`wh:payments:${event.id}`); // let the provider's retry be processed
        throw err;
      }
    }
    res.status(204).end();
  });
  return r;
}
```

## 15. Common Mistakes

- **Loading by id and returning it** (`findById(req.params.id)`) without an owner or tenant predicate: classic BOLA.
- **Checking ownership on read but not on update, delete or batch endpoints**.
- **`Object.assign(user, req.body)` or `prisma.user.update({ data: req.body })`**: mass assignment of `role`, `tenantId`, `emailVerified`.
- **Returning whole entities** and filtering fields in the front end: excessive data exposure.
- **No maximum on `limit`**, or limits only at the gateway while internal routes are reachable directly.
- **Non-atomic rate limiting** (`GET` then `SET`): concurrent requests slip through.
- **Rate-limiting by `X-Forwarded-For` taken from the client** without a trusted proxy configuration.
- **Parsing the webhook body before verifying the signature**, or verifying a re-serialized body instead of the raw bytes.
- **No timestamp window or event-id deduplication**: valid signed requests can be replayed.
- **API keys in query strings**: they end up in logs, browser history and referrers.
- **Treating automatic persisted queries as a safelist**: APQ caches any operation a client sends; a safelist rejects unknown operations.
- **Old API versions left running** after the new version ships, without the new authorization fixes.
- **Trusting partner API responses** and passing them to SQL, HTML or redirects without validation.

## 16. References

- [references/graphql.md](references/graphql.md): GraphQL hardening with Apollo Server 5 and GraphQL Armor, safelisting, introspection, field-level authorization and error masking.
- [references/request-signing.md](references/request-signing.md): HMAC request signing, replay windows, API key lifecycle, mTLS and sender-constrained tokens.
- OWASP API Security Top 10 2023: https://owasp.org/API-Security/
