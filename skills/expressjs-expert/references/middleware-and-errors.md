# Middleware Order and Error Handling

Express runs middleware in registration order, and an error skips every non-error middleware until it reaches one with four parameters. This file covers the order of the stack, the error pipeline in Express 5, request typing and the supporting middleware used by the examples in SKILL.md.

## 1. Order of the stack

1. `app.set('trust proxy', ...)`, settings.
2. Cheap global protection: `helmet()`, `rateLimit(...)`, optional `cors(...)`.
3. Body parsers with limits, either globally or on the routers that need them.
4. Public routes (health), then `authenticate`, then protected routers.
5. 404 middleware (`notFound`).
6. Error middleware (`errorHandler`), always last.

Why: rate limiting before parsing rejects abusive callers before bodies are read; CORS before authentication lets preflight `OPTIONS` requests succeed without credentials; the 404 handler must follow every router or it would shadow them.

Webhook routes that verify a signature need the raw bytes: mount `express.raw({ type: 'application/json', limit: '256kb' })` on that route only and do not let a global `express.json()` consume the stream first. Signature schemes and replay windows are in api-security-expert.

## 2. Async handlers and `next`

In Express 5 a rejected promise from a handler or middleware is forwarded to `next(err)`:

```typescript
r.get('/:id', async (req, res) => {
  const row = await repo.get(tenantId, id);   // a rejection here reaches errorHandler
  if (!row) throw new HttpError(404, 'Not found');
  res.json(row);
});
```

Rules:
- Throw or reject; do not catch an error only to call `next(err)`.
- A middleware that continues the chain calls `next()` once and returns; code after `next()` runs after downstream handlers started.
- Callback-style APIs (streams, event emitters, timers) are not covered by promise forwarding. Errors thrown inside a `setTimeout` or an event listener are uncaught exceptions; convert them to promises (`util.promisify`, `events.once`, `stream/promises`) or call `next(err)` explicitly.
- `next('route')` skips the remaining handlers of the current route; `next('router')` leaves the current router.

## 3. Error middleware

```typescript
import type { ErrorRequestHandler, RequestHandler } from 'express';
import { ZodError } from 'zod';

export class HttpError extends Error {
  constructor(readonly status: number, message: string, readonly expose = status < 500) {
    super(message);
  }
}

export const notFound: RequestHandler = (_req, _res, next) => {
  next(new HttpError(404, 'Not found'));
};

// Express identifies error middleware by its four parameters; keep all four.
export const errorHandler: ErrorRequestHandler = (err, req, res, _next) => {
  if (res.headersSent) {
    req.socket.destroy();            // the response is already streaming; closing is the only safe move
    return;
  }
  if (err instanceof ZodError) {
    res.status(400).json({ error: 'invalid_request', issues: err.issues.map((i) => ({ path: i.path, message: i.message })) });
    return;
  }
  // body-parser and http-errors attach `status` and `expose` to their errors.
  const status = Number.isInteger(err?.status) && err.status >= 400 && err.status < 600 ? err.status : 500;
  const expose = status < 500 || err?.expose === true;
  if (status >= 500) console.error(err);   // replace with the app's logger
  res.status(status).json({ error: expose ? String(err.message) : 'Internal Server Error' });
};
```

Notes:
- `res.headersSent` is true once the status line and headers were written (for example a streamed download that fails midway); calling `res.status()` then throws. Express's default handler also closes the connection in that case.
- body-parser errors (`entity.too.large` 413, `entity.parse.failed` 400, unsupported charset or encoding 415) carry `status`, so oversized and malformed bodies map correctly. The message may quote parser internals; replace it with a fixed string if that matters for your clients.
- The default Express handler prints the stack when `NODE_ENV` is not `production`. A custom handler should never include `err.stack` in a response.
- Errors thrown while the error middleware itself runs fall to the default handler; keep the handler free of I/O that can fail.
- A route-level handler can have its own error middleware by passing it after the handlers: `r.post('/x', handler, (err, req, res, next) => {...})`.

## 4. Authentication middleware and request typing

Token issuance and verification rules belong to authentication-expert; the Express side only stores the verified principal on the request.

```typescript
import type { RequestHandler } from 'express';
import { HttpError } from './http-errors.js';

declare module 'express-serve-static-core' {
  interface Request {
    auth?: { userId: string; tenantId: string };
  }
}

export function authenticate(
  verify: (token: string) => Promise<{ sub: string; tenantId: string } | null>,
): RequestHandler {
  return async (req, _res, next) => {
    const match = /^Bearer (.+)$/.exec(req.get('authorization') ?? '');
    const claims = match ? await verify(match[1]) : null;
    if (!claims) throw new HttpError(401, 'Unauthorized');
    req.auth = { userId: claims.sub, tenantId: claims.tenantId };
    next();
  };
}
```

`tenantId` comes from the verified claims or a server-side lookup, never from a header, body or query parameter the client controls.

## 5. Validation middleware

When many routes share the same pattern, a small generic helper keeps handlers short. Parse into a new object; `req.query` cannot be assigned in Express 5.

```typescript
import type { Request } from 'express';
import type { ZodType } from 'zod';

export const parsed = <T>(schema: ZodType<T>, source: 'body' | 'query' | 'params') =>
  (req: Request): T => schema.parse(req[source]);
```

Use it inside handlers (`const body = parsed(createBody, 'body')(req)`), which keeps the types flowing without mutating the request. Zod errors reach `errorHandler` through async propagation.

## 6. Router details

- `Router({ mergeParams: true })` is needed for a child router to see params declared on its mount path (`app.use('/tenants/:tenantId/orders', ...)`). Do not take the tenant from such a param without comparing it to `req.auth.tenantId`.
- `router.param('id', fn)` runs once per request per param value; use it for shared lookup, and scope the lookup by tenant.
- `app.route('/x').get(...).post(...)` groups methods on one path.
- Registration order inside a router matters: put `'/export'` before `'/:id'`.
- HEAD requests fall through to GET handlers; `OPTIONS` is answered automatically with the allowed methods unless CORS middleware answers first.
