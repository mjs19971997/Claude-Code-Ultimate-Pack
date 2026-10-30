# Proxy, Authentication Boundaries and Security Hardening in Next.js

Verified against Next.js 16.4.3 and 15.5.x (2026-10). In 16 the request-boundary file is `proxy.ts`; in 15 it is `middleware.ts`. Session and credential design itself belongs to authentication-expert; this file covers where checks live in a Next.js app.

## proxy.ts (middleware.ts on 15)

- Location: project root, or `src/` next to `app/`. One file, one exported function: `export function proxy(request: NextRequest)` or a default export. With custom `pageExtensions`, name it accordingly (`proxy.page.ts`).
- Runs before routes render, on the Node.js runtime. The `edge` runtime is not supported in `proxy` and its runtime cannot be configured; keep `middleware.ts` if Edge is required (deprecated).
- Migration: `mv middleware.ts proxy.ts`, rename the export to `proxy`; flags such as `skipMiddlewareUrlNormalize` become `skipProxyUrlNormalize`. The 16 upgrade codemod does both.
- Without a `matcher` it runs on every request, including `_next/static`, `_next/image` and `public/` assets. Use a matcher; values must be static constants.
- It runs on prefetches too. Do not make database or network calls in it.
- Do not rely on shared modules or globals; the proxy may be deployed separately (for example on a CDN).
- Pass data to the app through request headers, cookies, rewrites or redirects. Optional second argument `event.waitUntil(promise)` keeps background work alive after the response starts.
- Good uses: redirects and rewrites, locale routing, setting a CSP nonce, adding or stripping headers, optimistic cookie-based gating, protecting static routes that share content between users (for example paywalled pages, which a DAL cannot protect because they are prerendered).
- Bad uses: the only authorization layer, per-request database queries, long-running work, parsing large bodies.

## Layers of an auth check

| Layer | What it can check | Cost | Authoritative? |
|---|---|---|---|
| `proxy.ts` | cookie present, signature or expiry valid (optimistic) | very low | no |
| Layout / page | session for rendering a section | one lookup per render (dedupe with `React.cache`) | for rendering only; does not cover actions |
| DAL function | session, permission, tenant and object scope | query-scoped | yes, for reads |
| Server Action / route handler | session, permission, resource, input validation | query-scoped | yes, for writes |

Rules:

- Re-verify in every action and route handler; a protected page does not protect an action defined in or imported by it.
- Layouts do not re-render on every navigation, so a layout-only check can be skipped by client-side navigation between sibling pages. Check close to the data.
- With Cache Components, a session read is request-time: render authenticated UI behind `<Suspense>`. If a session helper reads the cookie internally and must carry a cache lifetime, `'use cache: private'` is the variant for it (browser-only cache). To cache on the server, extract an opaque id (user id, tenant id) and pass it as an argument to a `use cache` function.
- Return 401/403 style outcomes with `redirect('/login')`, `notFound()` or, with `authInterrupts` (experimental), `unauthorized()` and `forbidden()`. Do not leak whether a resource exists to users who cannot see it.

## Optimistic gating example

```typescript
// proxy.ts
import { NextResponse, type NextRequest } from 'next/server'

const PROTECTED_PREFIXES = ['/app', '/settings']

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const needsSession = PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
  if (needsSession && !request.cookies.has('__Host-session')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

A forged cookie passes this check; the DAL and actions reject it when they verify the session.

## Content Security Policy with nonces

A nonce-based CSP without `unsafe-inline`. Next.js reads the nonce from the request's `Content-Security-Policy` header while rendering and applies it to framework scripts, page bundles, inline scripts and styles it generates, and `<Script nonce>`.

```typescript
// proxy.ts
import { NextResponse, type NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.getRandomValues(new Uint8Array(16))).toString('base64')
  const isDev = process.env.NODE_ENV === 'development'

  const csp = [
    `default-src 'self'`,
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    `style-src 'self' 'nonce-${nonce}'`,
    `img-src 'self' blob: data:`,
    `font-src 'self'`,
    `object-src 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `frame-ancestors 'none'`,
    `upgrade-insecure-requests`,
  ].join('; ')

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-nonce', nonce)
  requestHeaders.set('Content-Security-Policy', csp)

  const response = NextResponse.next({ request: { headers: requestHeaders } })
  response.headers.set('Content-Security-Policy', csp)
  return response
}

export const config = {
  matcher: [
    {
      source: '/((?!api|_next/static|_next/image|favicon.ico).*)',
      missing: [
        { type: 'header', key: 'next-router-prefetch' },
        { type: 'header', key: 'purpose', value: 'prefetch' },
      ],
    },
  ],
}
```

- `'unsafe-eval'` is only for development (React uses `eval` for debugging information); it is not needed in production.
- Nonces need dynamic rendering: static HTML is generated at build time with no request headers. Pages that carry a nonce must render per request (for example `await connection()` in the page). With Cache Components, check the current CSP guide before enabling a nonce policy on prerendered routes.
- Third-party scripts: `<Script src="..." nonce={nonce} />` where `nonce` comes from `(await headers()).get('x-nonce')` in a Server Component. Allow third-party hosts explicitly in `script-src` only when needed, and prefer Subresource Integrity where the vendor supports it.
- A policy that needs `'unsafe-inline'` for scripts means something injects inline code without a nonce; fix the source instead.
- Roll out with `Content-Security-Policy-Report-Only` first if existing pages have unknown inline code.

## Other hardening settings

- `images.remotePatterns` with exact protocol and hostname; avoid wildcards over broad domains. Leave `images.dangerouslyAllowLocalIP` off unless the image optimizer must reach a private network (this is an SSRF trade-off).
- `images.localPatterns` with the exact query strings you serve (required for local images with query strings in 16).
- Response headers via `headers()` in `next.config.ts`: `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, and `frame-ancestors` through CSP. HSTS belongs on the TLS-terminating layer.
- `poweredByHeader: false` to drop `X-Powered-By`.
- Environment variables: `NEXT_PUBLIC_*` is inlined into the client bundle at build time and visible to everyone. Keep keys, tokens and connection strings without that prefix and read them only in server-only modules.
- `import 'server-only'` fails the build if a client component imports the module; optional `experimental.taint` with `experimental_taintObjectReference` / `experimental_taintUniqueValue` adds a second guard against passing sensitive objects to the client.
- Server Action protections (encrypted ids, `Origin` check, 1 MB cap) are on by default; see [server-actions-and-mutations.md](server-actions-and-mutations.md).
- Redirects built from user input (`?next=`): accept only same-origin relative paths that start with a single `/`, never `//` or a scheme.
- Route handlers that accept cross-origin browser calls set CORS headers explicitly with an origin allowlist; Server Actions are not for cross-origin use.
- Keep `next`, `react` and `react-dom` on the latest patch of the supported line. The December 2025 React Server Components advisories (CVE-2025-55182 critical RCE; CVE-2025-55183, CVE-2025-55184, CVE-2025-67779 and CVE-2026-23864 for source exposure and denial of service) were fixed in patch releases of every supported Next.js line.

## Self-hosting notes

- Every instance needs the same `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` so action references decrypt everywhere.
- Forward `Host` or `X-Forwarded-Host` unchanged from the reverse proxy, or list the public host in `serverActions.allowedOrigins`.
- Next.js 16 requires Node.js 20.9 or later.
- The in-memory cache handler is per process; configure `cacheHandlers` (and `use cache: remote`) when several instances must share cache entries.
