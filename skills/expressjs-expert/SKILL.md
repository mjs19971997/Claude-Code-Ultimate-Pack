---
name: expressjs-expert
description: >-
  Builds and reviews Express 5 applications: middleware order, routing with path-to-regexp v8 syntax, async error handling, request validation, helmet, CORS, express-rate-limit, trust proxy, multer uploads and graceful shutdown, plus Express 4 to 5 migration. Use when working on app.use, Router, error middleware, express.json limits, req.query or req.body behavior, wildcard routes such as /*splat, reverse-proxy deployments, or upgrading an Express 4 codebase. Not for framework-agnostic Node runtime topics such as streams, workers or the event loop (use nodejs-architect), opinionated NestJS modules (use nestjs-expert), or REST resource and status-code design (use rest-api-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Express.js Expert

This skill covers the HTTP layer of Express 5: how middleware is ordered, how errors travel, how routes are written in the current path syntax, and which security middleware belongs in front of the handlers. It also covers moving an Express 4 codebase to 5. Examples use TypeScript and scope every read and write to the authenticated tenant.

> Verified against Express 5.3.0, helmet 8.3.0, express-rate-limit 8.7.2, multer 2.5.0, zod 4.6, cors 2.8.6, Node.js 22, 24 and 26 LTS (2026-10).

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

- Covered: application composition, `Router`, middleware order, error middleware, body parsers and limits, route syntax, validation at the boundary, helmet, CORS, rate limiting, `trust proxy`, multipart uploads, Express 4 to 5 migration, graceful shutdown of the HTTP server.
- Not covered: Node internals and concurrency (nodejs-architect), NestJS (nestjs-expert), login, sessions, JWT and OAuth design (authentication-expert), roles and policies (authorization-expert), API-wide threats such as BOLA and signing (api-security-expert), resource modeling (rest-api-expert), reverse proxy configuration (nginx-expert).

## 2. Core Expertise

- **Express 5.x** requires Node.js 18 or later (`engines` of express 5.3.0). Node.js 20 reached end of life on 2026-04-30; the supported lines are 22 (Jod), 24 (Krypton) and 26 (LTS since 2026-10-28). Express 4 is still published under the `latest-4` dist-tag (4.22.3) for legacy apps.
- **Async handlers**: a rejected promise or a thrown error in an `async` handler or middleware is passed to `next(err)` automatically. No `express-async-errors` or wrapper is needed.
- **Routing** uses path-to-regexp v8: named wildcard `/*splat` (value is an array in `req.params.splat`), optional segment `{/:id}`, no `?`, `*`, `+` or inline regex groups; reserved characters `()[]?+!` need escaping with a backslash.
- **Request object**: `req.query` is a getter and cannot be assigned; the default `query parser` is `"simple"` (node `querystring`, so `a[b]=1` stays the flat key `a[b]`); `req.body` is `undefined` until a parser matches; `express.urlencoded` defaults `extended` to `false`.
- **Middleware pipeline**: `app.use` order is execution order. A handler either responds or calls `next()`; an error middleware has exactly four parameters `(err, req, res, next)`.
- **Security middleware**: `helmet` (default CSP has `script-src 'self'` and no `unsafe-inline` for scripts), `cors`, `express-rate-limit`, `express.json({ limit })`, `multer` for multipart.
- **Typing**: `@types/express` 5.x; extend `Request` through `declare module 'express-serve-static-core'`.

## 3. Workflow

1. Decide the version target. New projects start on Express 5. For an existing Express 4 app follow [references/express-5-migration.md](references/express-5-migration.md) and run the codemod first.
2. Write `createApp(deps)` that builds and returns the app without listening, so tests can use it directly.
3. Order the stack: `trust proxy`, helmet, rate limit, CORS (only if browsers from other origins call the API), body parsers with limits, routers, 404, error middleware.
4. For each route: validate `params`, `query` and `body` with a schema, derive the tenant and user from the verified principal, call a service or repository that takes the tenant id, return an explicit response shape.
5. Normalize errors in one place; decide which errors expose their message to the client.
6. Add the production entry point: `server.listen`, server timeouts, `SIGTERM` handling.
7. Test through `supertest` against `createApp`, including a second tenant's credentials against every id-bearing route.

## 4. Decision Rules

- New code on Express 5. Stay on Express 4 only when a dependency blocks the upgrade, and plan the migration; see the reference for the checklist.
- One `Router` per resource, mounted with `app.use('/v1/orders', ...)`. Put authentication on the mount, not inside each handler.
- Validate with a schema library (Zod 4, Valibot, or express-validator) at the router boundary; use strict objects for request bodies so unknown fields are rejected.
- `trust proxy`: set a hop count (`1` behind one load balancer) or a list of subnets. `true` trusts the leftmost `X-Forwarded-For` value, which a client can forge, and express-rate-limit reports it as a permissive setting. Leave it unset (the default `false`) when no proxy is in front.
- Sessions in cookies need a shared store when more than one instance runs; the built-in `MemoryStore` leaks memory and is not for production (authentication-expert covers the session design).
- Use `cors` only for browsers on other origins; list exact origins. `origin: '*'` together with `credentials: true` is rejected by browsers, and reflecting the request origin is equivalent to allowing everyone.
- Prefer `helmet()` defaults and relax one directive at a time. Use nonces or hashes for inline scripts rather than `'unsafe-inline'`.
- Return 404 for objects the caller may not see (another tenant's id) so ids cannot be probed.

## 5. Coding Standards

- Handlers are `async (req, res) => {}`; throw `HttpError` or let validation errors propagate. Do not wrap in try/catch only to call `next(err)`.
- Every handler either sends exactly one response or throws; never `res.send()` and then `next()`.
- Use `res.status(code).json(body)` and `res.status(204).end()`. `res.sendStatus(code)` sends the status text as the body, so prefer it only for plain text endpoints.
- Do not mutate `req.query`; read it through the schema and keep the parsed copy in a local variable.
- Keep Express out of services and repositories: they take plain values (`tenantId`, `id`, DTOs) and return plain data.
- Name middleware by what it enforces: `authenticate`, `requireRole('admin')`, `validate(schema)`.
- Export a factory per module (`orderRouter(repo)`) so dependencies are injected rather than imported as singletons.

## 6. Project Structure

```
src/
  app.ts            # createApp(deps): middleware stack, router mounts, 404, error handler
  server.ts         # listen, timeouts, graceful shutdown
  http-errors.ts    # HttpError, notFound, errorHandler
  auth.ts           # authenticate middleware, Request augmentation
  orders.ts         # orderRouter(repo): validation + handlers
  orders.repo.ts    # data access, every method takes tenantId
tests/
  orders.test.ts    # supertest against createApp with an in-memory repo
```

Group by feature once the app grows (`orders/`, `billing/`); each feature exports its router factory.

## 7. Design Patterns

- **App factory**: `createApp(deps)` returns an `Express`; `server.ts` is the only file that listens.
- **Router per resource** with the tenant taken from `req.auth`, never from the URL or body.
- **Error normalization**: one error class, one `errorHandler`; everything else throws.
- **Validation at the boundary**: parse `req.params`, `req.query`, `req.body` into typed values before any logic.
- **Content negotiation**: `res.format()` or `req.accepts()` only when an endpoint really serves several types; otherwise JSON only.
- **Sub-app mounting** for versioning: `app.use('/v1', v1Router)`; mark old versions with `Deprecation` and `Sunset` headers before removal.

## 8. Best Practices

- Mount body parsers per router when only some routes need them (a webhook route needs `express.raw`, an upload route needs multer).
- Give each parser an explicit `limit`; the default for `express.json` is `100kb`, and stating it makes the intent reviewable.
- Set `app.disable('x-powered-by')` or rely on helmet, which removes it.
- Use `app.set('etag', 'strong')` or keep the default weak ETags for JSON; do not disable them unless a proxy handles caching.
- Use `res.locals` for per-request values that views or later middleware need; use a `Request` augmentation for typed values like `req.auth`.
- Keep route files thin; return DTOs from mappers (`toOrderView`) rather than ORM entities.

## 9. Performance

- Body parsing and JSON serialization run on the event loop; keep limits low and stream large payloads (multer disk storage, `res.sendFile`, `stream.pipeline`) instead of buffering.
- Serve static assets and compression from the reverse proxy or CDN when one exists; `compression` middleware is for deployments without one.
- Do not put expensive work in middleware that runs on every request; mount it on the routers that need it.
- `express.static` and `res.sendFile` handle conditional requests and ranges; do not re-implement them.
- Pool database connections per process; Express adds no pooling of its own.

## 10. Security

- Order matters: rate limit and helmet before parsers so abusive requests are rejected before bodies are read.
- Authenticate at the router mount; authorize inside the data access layer by passing `tenantId` into every `WHERE`, on writes (`UPDATE ... WHERE id = $1 AND tenant_id = $2`) as well as reads.
- Reject unknown body fields (`z.strictObject`) so clients cannot set `tenantId`, `role` or `ownerId`.
- Error bodies for 5xx carry a generic message; never serialize `err.stack`, SQL or file paths. See [references/middleware-and-errors.md](references/middleware-and-errors.md).
- Uploads: `limits.fileSize`, `limits.files`, a `fileFilter`, server-generated file names, storage outside the web root. Never use `file.originalname` in a path.
- `res.redirect(url)` with a user-supplied URL is an open redirect; allow only relative paths or an allowlist of hosts.
- Mount no debug, seed or test routes in the production app; if a test needs data, build it through the repository in the test.
- Helmet, CORS and rate-limit specifics: [references/security-middleware.md](references/security-middleware.md).

## 11. Testing

- Use `supertest` with `request(createApp(fakeDeps))`; no port, no network.
- For every route that takes an id, add a test where tenant B requests tenant A's object and expects 404 for reads, updates and deletes.
- Test the error path: invalid JSON, schema failure, thrown `HttpError`, an unexpected `Error` (expect a generic 500 body), and an error after headers were sent.
- Test the rate limiter with a small `limit` and assert the 429 and the headers you rely on.
- Test with `NODE_ENV=production` for anything that branches on it.

## 12. Review Checklist

- [ ] `trust proxy` matches the real number of proxies; `req.ip` is the client address.
- [ ] Parsers have explicit limits and are mounted before the routes that read `req.body`; handlers tolerate `req.body === undefined`.
- [ ] Every id-bearing route filters by tenant on reads and writes.
- [ ] Request bodies use strict schemas; responses use explicit mappers.
- [ ] An error middleware with four parameters is mounted last; 404 handler before it.
- [ ] No wildcard route uses Express 4 syntax (`*`, `:id?`, `(.*)`).
- [ ] CORS lists exact origins; helmet is mounted; rate limits exist on auth and write routes.
- [ ] No test, seed or debug route is reachable when `NODE_ENV=production`.
- [ ] `server.ts` handles `SIGTERM` and sets server timeouts.

## 13. Production Notes

- Node's HTTP server has `headersTimeout`, `requestTimeout` and `keepAliveTimeout`. When a load balancer reuses connections, set `keepAliveTimeout` above the balancer's idle timeout (and `headersTimeout` above `keepAliveTimeout`) to avoid sporadic 502s from reused sockets.
- Graceful shutdown: on `SIGTERM`, stop accepting (`server.close()`), call `server.closeIdleConnections()`, wait for in-flight requests with a hard deadline, then close database and Redis clients.
- Make `/healthz` cheap and dependency-free; a separate readiness route may check the database.
- Run one process per container and scale with replicas; use `node:cluster` only on a single large host.
- Rate limit state is per process with the default `MemoryStore`; use a shared store (a Redis store package for express-rate-limit) when several instances serve traffic. Check the store's current docs for its options.
- Node version: run an LTS line that is still supported (22, 24 or 26); do not deploy on 20 or older.

## 14. Examples

### Example 1: App factory with the full stack

```typescript
import express, { type Express } from 'express';
import helmet from 'helmet';
import { rateLimit } from 'express-rate-limit';
import { errorHandler, notFound } from './http-errors.js';
import { orderRouter, type OrderRepo } from './orders.js';
import { authenticate } from './auth.js';

export interface Deps {
  orders: OrderRepo;
  verifyToken: (token: string) => Promise<{ sub: string; tenantId: string } | null>;
}

export function createApp(deps: Deps): Express {
  const app = express();
  app.set('trust proxy', 1);            // exactly one proxy (the load balancer) in front
  // helmet's default style-src allows 'unsafe-inline'; tighten it so the CSP has no unsafe-inline at all
  app.use(helmet({ contentSecurityPolicy: { directives: { 'style-src': ["'self'"] } } }));
  app.use(rateLimit({ windowMs: 60_000, limit: 300, standardHeaders: 'draft-8', legacyHeaders: false }));
  app.use(express.json({ limit: '100kb' }));

  app.get('/healthz', (_req, res) => { res.json({ status: 'ok' }); });
  app.use('/v1/orders', authenticate(deps.verifyToken), orderRouter(deps.orders));

  app.use(notFound);
  app.use(errorHandler);
  return app;
}
```

### Example 2: Tenant-scoped router with strict validation

```typescript
import { Router, type Request } from 'express';
import { z } from 'zod';
import { HttpError } from './http-errors.js';

export interface Order { id: string; tenantId: string; sku: string; quantity: number }

// Every method takes tenantId and puts it in the WHERE clause of reads AND writes.
export interface OrderRepo {
  list(tenantId: string, opts: { limit: number; after?: string }): Promise<Order[]>;
  get(tenantId: string, id: string): Promise<Order | null>;
  create(tenantId: string, data: { sku: string; quantity: number }): Promise<Order>;
  update(tenantId: string, id: string, data: { quantity: number }): Promise<Order | null>;
  remove(tenantId: string, id: string): Promise<boolean>;
}

const idParam = z.object({ id: z.uuid() });
const listQuery = z.object({ limit: z.coerce.number().int().min(1).max(100).default(25), after: z.uuid().optional() });
const createBody = z.strictObject({ sku: z.string().min(1).max(64), quantity: z.number().int().min(1).max(1000) });
const updateBody = z.strictObject({ quantity: z.number().int().min(1).max(1000) });

const tenantOf = (req: Request): string => {
  if (!req.auth) throw new HttpError(401, 'Unauthorized');
  return req.auth.tenantId;
};

export function orderRouter(repo: OrderRepo): Router {
  const r = Router();
  r.get('/', async (req, res) => {
    res.json(await repo.list(tenantOf(req), listQuery.parse(req.query))); // req.query is read-only in Express 5
  });
  r.post('/', async (req, res) => {
    res.status(201).json(await repo.create(tenantOf(req), createBody.parse(req.body))); // undefined body fails the schema
  });
  r.get('/:id', async (req, res) => {
    const order = await repo.get(tenantOf(req), idParam.parse(req.params).id);
    if (!order) throw new HttpError(404, 'Not found'); // 404, not 403: do not confirm other tenants' ids
    res.json(order);
  });
  r.patch('/:id', async (req, res) => {
    const order = await repo.update(tenantOf(req), idParam.parse(req.params).id, updateBody.parse(req.body));
    if (!order) throw new HttpError(404, 'Not found');
    res.json(order);
  });
  r.delete('/:id', async (req, res) => {
    if (!(await repo.remove(tenantOf(req), idParam.parse(req.params).id))) throw new HttpError(404, 'Not found');
    res.status(204).end();
  });
  return r;
}
```

`authenticate` sets `req.auth` from a verified token (see [references/middleware-and-errors.md](references/middleware-and-errors.md) for it and the `Request` augmentation).

### Example 3: Server entry point with graceful shutdown

```typescript
import { createApp } from './app.js';
import { deps, closeDeps } from './deps.js'; // your wiring: database pool, Redis, token verifier

const server = createApp(deps).listen(Number(process.env.PORT ?? 3000));
server.keepAliveTimeout = 65_000;   // above a typical 60 s load balancer idle timeout
server.headersTimeout = 66_000;

let closing = false;
process.on('SIGTERM', () => {
  if (closing) return;
  closing = true;
  const deadline = setTimeout(() => process.exit(1), 25_000).unref();
  server.close(async () => {           // fires when all connections have ended
    await closeDeps();
    clearTimeout(deadline);
    process.exit(0);
  });
  server.closeIdleConnections();       // do not wait on idle keep-alive sockets
});
```

## 15. Common Mistakes

- **Express 4 route syntax in Express 5**: `app.get('*', ...)`, `'/:id?'` and `'/(.*)'` throw at startup. Use `'/*splat'`, `'/{*splat}'` (also matches the root), `'/files{/:id}'`.
- **Assigning `req.query = ...`**: throws in Express 5 because it is a getter. Parse into a new variable.
- **Reading `req.body` without a parser, or on a GET**: it is `undefined`, so `req.body.x` throws. Validate with a schema that rejects `undefined`.
- **Expecting nested form fields**: `express.urlencoded()` defaults to `extended: false`; `a[b]=1` stays a flat key. Set `extended: true` only if nested keys are required, and validate the result.
- **`app.set('trust proxy', true)`**: trusts any client-supplied `X-Forwarded-For`; rate limits and logs then key on a forged address. Use a hop count or subnet list.
- **`res.redirect('back')`**: no longer special; it redirects to the relative URL `back`. Redirect to an explicit, validated path.
- **Using `app.del`, `req.param()`, `res.sendfile`, `res.json(obj, status)`**: removed in 5; see the migration reference.
- **Three-parameter error handlers**: Express treats them as normal middleware and never calls them with an error.
- **Sending a response, then calling `next()`** or throwing afterwards: causes "headers already sent" and a second error path.
- **Tenant filter only on reads**: updates and deletes by bare id let one tenant modify another's rows.
- **`express.json()` mounted after the routes** it should protect, or a second parser reading an already consumed stream.
- **Exposing `err.message` for every error**: leaks driver and file details; expose only for 4xx.

## 16. References

- [references/express-5-migration.md](references/express-5-migration.md): Express 4 to 5 breaking changes, codemod, route syntax conversion table.
- [references/middleware-and-errors.md](references/middleware-and-errors.md): middleware order, error middleware details, request typing, async patterns, the `authenticate` middleware.
- [references/security-middleware.md](references/security-middleware.md): helmet, CORS, express-rate-limit, trust proxy, multer configuration.
- Express docs: https://expressjs.com/ (migration guide: `/en/guide/migrating-5.html`)
- helmet: https://helmetjs.github.io/ and express-rate-limit: https://express-rate-limit.mintlify.app/
