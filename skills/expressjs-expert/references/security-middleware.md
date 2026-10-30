# Security Middleware: helmet, CORS, Rate Limiting, trust proxy, Uploads

Configuration notes for the middleware that sits in front of Express handlers. Versions checked: helmet 8.3.0, express-rate-limit 8.7.2, cors 2.8.6, multer 2.5.0, Express 5.3.0 (2026-10). All option names below exist in those versions' type definitions or source.

## 1. trust proxy

`trust proxy` tells Express which `X-Forwarded-*` headers to believe. It changes `req.ip`, `req.ips`, `req.protocol`, `req.secure` and `req.hostname`, so it also affects secure cookies, redirects built from the host, and every IP-keyed rate limit.

| Setting | Meaning |
|---|---|
| `false` (default) | Ignore forwarded headers; `req.ip` is the socket address. |
| number `n` | Trust the `n` nearest hops; `req.ip` is the address `n` hops from the app in `X-Forwarded-For`. |
| `true` | Trust every hop; `req.ip` is the leftmost entry, which the client can set. Avoid. |
| string or array | A subnet, an IP or a list (`'10.0.0.0/8'`, `['loopback', 'uniquelocal']`); the nearest untrusted address becomes `req.ip`. Named shortcuts: `loopback`, `linklocal`, `uniquelocal`. |
| function `(ip, hopIndex) => boolean` | Custom trust decision per hop. |

Pick the value from the real topology: `1` behind one load balancer or one nginx; `2` behind a CDN plus a load balancer; a subnet list when proxy addresses are stable. After changing the infrastructure, check `req.ip` with a request that sends a forged `X-Forwarded-For` and confirm the forged value is not returned. The proxy must overwrite or append `X-Forwarded-For` rather than pass client values through unchanged.

express-rate-limit runs validation checks at startup and warns about an unset `trust proxy` when forwarded headers arrive (`ERR_ERL_UNSET_TRUST_PROXY`) and about `true` (`ERR_ERL_PERMISSIVE_TRUST_PROXY`); treat both as configuration bugs.

## 2. helmet

`helmet()` sets these headers by default (8.3.0): `Content-Security-Policy`, `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`, `Origin-Agent-Cluster`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`, `X-DNS-Prefetch-Control: off`, `X-Download-Options: noopen`, `X-Frame-Options: SAMEORIGIN`, `X-Permitted-Cross-Domain-Policies: none`, `X-XSS-Protection: 0`, and it removes `X-Powered-By`.

The default CSP is:

```
default-src 'self'; base-uri 'self'; font-src 'self' https: data:; form-action 'self';
frame-ancestors 'self'; img-src 'self' data:; object-src 'none'; script-src 'self';
script-src-attr 'none'; style-src 'self' https: 'unsafe-inline'; upgrade-insecure-requests
```

`script-src` has no `'unsafe-inline'`; only `style-src` allows inline styles. For a JSON API the CSP is mostly irrelevant, but the other headers still apply. For pages that load a CDN script or call another origin, extend the specific directive:

```typescript
app.use(helmet({
  contentSecurityPolicy: {
    directives: {                       // merged with the defaults (useDefaults is true)
      'script-src': ["'self'", 'https://cdn.example.com'],
      'connect-src': ["'self'", 'https://api.example.com'],
    },
  },
  hsts: { maxAge: 31_536_000, includeSubDomains: true },
}));
```

- Values in a directive array are quoted keywords (`"'self'"`, `"'none'"`) or sources; helmet throws on unquoted keywords such as `self`.
- For an unavoidable inline script, helmet accepts a function as a directive value, evaluated per request, so a nonce generated in an earlier middleware and stored in `res.locals` can be added to `script-src`; prefer external scripts. Avoid `'unsafe-inline'` in `script-src`.
- `useDefaults: false` requires you to list every directive yourself, including `default-src`.
- Set `contentSecurityPolicy: false` or `hsts: false` only when the reverse proxy already sends that header.
- HSTS is cached by browsers for `maxAge`; enable `preload` only after every subdomain serves HTTPS.

## 3. CORS

CORS is a browser-side relaxation of the same-origin policy; it does not protect an API from non-browser clients.

```typescript
import cors from 'cors';

app.use(cors({
  origin: ['https://app.example.com', 'https://admin.example.com'],  // exact origins
  methods: ['GET', 'POST', 'PATCH', 'DELETE'],
  allowedHeaders: ['Authorization', 'Content-Type'],
  credentials: true,                                                 // only if cookies are used
  maxAge: 600,                                                       // seconds a preflight may be cached
}));
```

- Allow exact origins. A function `origin: (origin, cb) => cb(null, allowed.has(origin ?? ''))` is fine when it checks an allowlist; echoing the request origin back is not.
- `origin: '*'` cannot be combined with credentials in browsers. Bearer-token APIs that do not use cookies do not need `credentials: true`.
- Mount `cors` before authentication so preflight `OPTIONS` requests (which carry no credentials) get a response.
- Add `exposedHeaders` only for headers the browser client must read (for example rate limit headers).

## 4. express-rate-limit

Options used here exist in 8.7.2: `windowMs`, `limit` (replaces the older `max`), `standardHeaders` (`true`, `'draft-6'`, `'draft-7'` or `'draft-8'`), `legacyHeaders`, `keyGenerator`, `ipv6Subnet`, `skipSuccessfulRequests`, `skipFailedRequests`, `skip`, `handler`, `message`, `statusCode`, `store`, `passOnStoreError`, `identifier` and `validate`. `standardHeaders: 'draft-8'` emits a combined `RateLimit` header and a `RateLimit-Policy` header; clients that rely on a specific header format should be tested against the version in use.

```typescript
import { rateLimit, ipKeyGenerator } from 'express-rate-limit';

export const loginLimiter = rateLimit({
  windowMs: 15 * 60_000,
  limit: 10,
  standardHeaders: 'draft-8',
  legacyHeaders: false,
  skipSuccessfulRequests: true,          // only failed attempts count
  // Per account AND per client address; ipKeyGenerator masks IPv6 addresses to a subnet.
  keyGenerator: (req) => `${ipKeyGenerator(req.ip ?? '')}:${String(req.body?.email ?? '').toLowerCase()}`,
});
```

- Mount it after the JSON parser when the key uses `req.body`, and use a global limiter before parsers for volume protection.
- When writing a custom `keyGenerator` that falls back to the IP address, wrap it with `ipKeyGenerator`; a raw IPv6 address lets one client rotate through its /64 to evade the limit.
- The default `MemoryStore` is per process and resets on restart. With several instances use a shared store package (for example a Redis-backed store from the express-rate-limit ecosystem); check that package's current docs for its constructor options.
- `passOnStoreError: true` lets requests through when the store fails (availability over protection); the default rejects with an error. Pick per route.
- Limits belong to the principal as well as the IP: authenticated routes can use `keyGenerator: (req) => req.auth?.userId ?? ipKeyGenerator(req.ip ?? '')`.
- Credential-stuffing and business-flow limits (OTP sends, coupon redemption) are described in api-security-expert.

## 5. multer 2.x uploads

multer handles `multipart/form-data` only. Configure limits, a type filter and generated names:

```typescript
import multer from 'multer';
import { randomUUID } from 'node:crypto';

const ALLOWED = new Map([['image/png', '.png'], ['image/jpeg', '.jpg']]);

export const upload = multer({
  storage: multer.diskStorage({
    destination: '/var/app/uploads',          // outside any static-served directory
    filename: (_req, file, cb) => cb(null, `${randomUUID()}${ALLOWED.get(file.mimetype) ?? ''}`),
  }),
  limits: { fileSize: 2 * 1024 * 1024, files: 1, fields: 5 },
  fileFilter: (_req, file, cb) => cb(null, ALLOWED.has(file.mimetype)),
});

app.post('/v1/avatar', upload.single('avatar'), (req, res) => {
  if (!req.file) { res.status(400).json({ error: 'file_required' }); return; }
  res.status(201).json({ id: req.file.filename });
});
```

- The client-declared `mimetype` is not proof of content; check the file's magic bytes after upload (or re-encode images) before trusting it.
- Never build a path from `file.originalname`; the generated name above cannot traverse directories.
- Limit violations raise `MulterError` (for example `LIMIT_FILE_SIZE`); map it to 413 or 400 in the error middleware.
- Use `memoryStorage` only for small files; it holds the whole upload in RAM.
- Serve uploads through a handler that checks the tenant and sets `Content-Disposition` and `X-Content-Type-Options`, not through `express.static`.
