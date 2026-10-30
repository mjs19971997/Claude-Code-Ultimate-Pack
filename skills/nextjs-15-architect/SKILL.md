---
name: nextjs-15-architect
description: >-
  Architects Next.js App Router applications for Next.js 15 and 16: Server and Client Component boundaries, Cache Components (use cache, cacheLife, cacheTag, updateTag, revalidateTag), streaming with Suspense, Server Actions, proxy.ts (formerly middleware.ts), route handlers, async params/searchParams/cookies()/headers(), and Turbopack. Use when working with next.config.ts, app/ routes, layout.tsx, page.tsx, proxy.ts or middleware.ts, "use server" and "use cache" files, data access layers, CSP nonces, or upgrading from Next.js 15 to 16. Not for React-only concerns such as hooks, Actions and the React Compiler (use senior-react-19-engineer), Core Web Vitals tuning (use core-web-vitals-expert), or login, session and OAuth design (use authentication-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Next.js Architect

This skill covers App Router architecture in Next.js: where code runs (server or client), how data is cached and revalidated, how mutations are authorized, and what the request-boundary file (`proxy.ts`) should and should not do. It is written for the current major, Next.js 16, and notes where Next.js 15 behaves differently (the folder name keeps the old "15" for compatibility). The Pages Router is out of scope.

> Verified against Next.js 16.4.3 (current) and 15.5.x, React 19.3.1, Zod 4.6.7, Node.js 20.9+ (2026-10). The docs bundled in `node_modules/next/dist/docs/` match the installed version.

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

- Covered: App Router file conventions, Server and Client Components, Cache Components and the previous fetch-based caching model, streaming, Server Actions and route handlers, `proxy.ts`, metadata, Turbopack, version differences between 15 and 16.
- Not covered: hooks, Actions state and Compiler details (senior-react-19-engineer); bundle and Web Vitals tuning (core-web-vitals-expert); credential, session and token design (authentication-expert); role and policy modeling (authorization-expert); Tailwind, shadcn/ui and animation libraries (their own skills).

Differences that matter when the project is still on 15:

| Topic | Next.js 15 | Next.js 16 |
|---|---|---|
| Request boundary file | `middleware.ts` (Edge by default) | `proxy.ts`, export `proxy`, Node.js runtime only; `middleware.ts` is deprecated and still the only option for Edge |
| Caching model | `fetch` is uncached by default; `unstable_cache`, route segment config (`dynamic`, `revalidate`) | Cache Components (`cacheComponents: true`): `"use cache"`, `cacheLife`, `cacheTag`; the old model still works when the flag is off |
| `"use cache"` | experimental, canary only (`experimental.useCache`, `dynamicIO`) | stable behind `cacheComponents`; the experimental flags are removed |
| `revalidateTag` | `revalidateTag(tag)` | `revalidateTag(tag, profile)`, second argument required; new `updateTag` and `refresh` |
| Bundler | webpack; Turbopack opt-in (`--turbopack`) | Turbopack default for `dev` and `build`; `--webpack` to opt out; a custom `webpack` config fails the build unless a flag is passed |
| `params`, `searchParams`, `cookies()`, `headers()`, `draftMode()` | async, synchronous access still works with a warning | async only |
| Lint | `next lint` | removed; run ESLint or Biome directly |
| Node.js / TypeScript | 18.18+ | Node.js 20.9+, TypeScript 5.1+ |

## 2. Core Expertise

- **Rendering model**: Server Components by default; `'use client'` marks the start of a client subtree. With Cache Components the page is a static shell (static JSX plus `use cache` output) with `<Suspense>` holes that stream at request time.
- **Caching**: `use cache` on a function, component or file; lifetime via `cacheLife` (`seconds`, `minutes`, `hours`, `days`, `weeks`, `max`, or `{ stale, revalidate, expire }`); on-demand invalidation via `cacheTag` plus `updateTag` / `revalidateTag` / `revalidatePath`. Variants: `'use cache: remote'` (shared cache handler) and `'use cache: private'` (may read `cookies()` and `headers()`, kept in the browser only). Details in [references/caching-and-rendering.md](references/caching-and-rendering.md).
- **Mutations**: Server Functions invoked from forms (`<form action>`), `useActionState` and event handlers; each is a public POST endpoint. Details in [references/server-actions-and-mutations.md](references/server-actions-and-mutations.md).
- **Request boundary**: `proxy.ts` for redirects, rewrites, header injection and optimistic checks. Details in [references/proxy-auth-and-security.md](references/proxy-auth-and-security.md).
- **Routing**: nested layouts, route groups `(group)`, parallel routes `@slot` (each slot needs `default.js` in 16), intercepting routes, `loading.tsx`, `error.tsx`, `not-found.tsx`, `generateStaticParams`.
- **Typed route props**: run `npx next typegen` (15.5+) to get global `PageProps<'/blog/[slug]'>`, `LayoutProps` and `RouteContext` helpers.
- **Deferred work**: `after()` for work after the response, `connection()` to opt a component into request-time rendering.

## 3. Workflow

1. Check the installed major (`next --version`) and read the matching docs in `node_modules/next/dist/docs/` before relying on memory; APIs differ between 15 and 16.
2. Draw the boundaries: which components need state, effects or browser APIs (client) and which only render data (server). Push `'use client'` to leaf components.
3. Decide the data path: a server-only data access layer (DAL) that authenticates, authorizes, scopes by tenant and returns DTOs.
4. Classify each piece of data: shared and slow-changing (cache with `use cache`), per-user (stream behind Suspense, or cache with the user id as an argument), per-request (stream).
5. Wrap every runtime read (`cookies()`, `headers()`, `searchParams`, uncached fetches) in `<Suspense>` with a meaningful fallback.
6. Design mutations as Server Actions that validate input, re-authenticate, authorize on the specific resource, write with tenant scoping, then invalidate tags.
7. Keep `proxy.ts` thin: optimistic redirect, CSP nonce, header injection. No database calls.
8. Run `next build`; with Cache Components the build and dev overlay report blocking routes and uncached reads outside Suspense.
9. Test the DAL and actions directly, and routes end to end.

## 4. Decision Rules

- Default to a Server Component; add `'use client'` only for state, effects, event handlers, browser APIs or client-only libraries.
- Cache Components enabled: shared data uses `use cache` + `cacheLife` + `cacheTag`; anything depending on the request streams under `<Suspense>`.
- Cache Components off (or Next.js 15): use `fetch(url, { cache: 'force-cache', next: { tags } })` or `unstable_cache` for non-fetch calls, and revalidate with `revalidateTag`.
- Need fresh data right after the user's own write: `updateTag(tag)` (Server Actions only). Stale content is acceptable, or the caller is a route handler or webhook: `revalidateTag(tag, 'max')`. One affected path and no tags: `revalidatePath`. Only client router state is stale: `refresh()`.
- Request-time values inside cached code: read `cookies()`/`headers()` outside the cached scope and pass the needed value as an argument. Use `'use cache: private'` only when that refactor is impractical (for example a session helper that reads the cookie internally).
- Server cache entries must not be shared across tenants or users: put `tenantId` and `userId` in the function arguments so they become part of the cache key.
- `use cache: remote` only when the in-memory handler measurably causes repeated upstream load (serverless instances are ephemeral); it adds network latency to each lookup.
- Mutation from a form or event handler: Server Action. Endpoint called by third parties or webhooks: route handler (`route.ts`).
- Auth in `proxy.ts` is an optimistic pre-filter (cookie present, signature valid). The authoritative check lives in the DAL and in each action.
- Edge runtime needed: keep `middleware.ts` (Next.js 16 `proxy` is Node.js only). Cache Components also requires the Node.js runtime and rejects a `runtime` segment export.
- Avoid `useEffect` data fetching for first render; fetch on the server and pass DTOs as props.

## 5. Coding Standards

- TypeScript strict. `next.config.ts` typed with `NextConfig`.
- Always `await` the request APIs: `const { slug } = await props.params`, `await cookies()`, `await headers()`. Use `PageProps<'/route'>` helpers after `next typegen`.
- Every `use cache` scope sets an explicit `cacheLife`; do not rely on the implicit `default` profile (5 min stale, 15 min revalidate, never expires).
- Cached functions and components are `async`; arguments and return values must be serializable (no class instances, functions, symbols or `URL`). `children` and Server Actions may pass through unread.
- Put `import 'server-only'` at the top of every module that touches the database, secrets or session. Put `import 'client-only'` on browser-only modules if needed.
- Props passed from a Server to a Client Component are public: pass DTOs with only the fields the UI needs, never raw rows.
- Environment variables: only `NEXT_PUBLIC_*` reaches the browser and is inlined at build time. It is for public identifiers only, never keys or tokens. Read secrets through the DAL.
- Name files by convention: `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, `route.ts`, `proxy.ts`. Co-locate private code in `_folders` or outside `app/`.
- Use `next/link`, `next/image` (configure `images.remotePatterns`, not the deprecated `images.domains`) and `next/font`.

## 6. Project Structure

```
.
├── next.config.ts                  # cacheComponents, reactCompiler, serverActions (under experimental)
├── proxy.ts                        # optimistic checks, CSP nonce (Node.js runtime)
├── src/
│   ├── app/
│   │   ├── layout.tsx              # shell, fonts, providers (client providers in own files)
│   │   ├── (marketing)/page.tsx    # static or cached
│   │   ├── (app)/
│   │   │   ├── layout.tsx
│   │   │   └── orders/
│   │   │       ├── page.tsx        # Suspense around request-time reads
│   │   │       ├── actions.ts      # "use server": validate, authorize, write, invalidate
│   │   │       └── _components/    # private to this route
│   │   └── api/webhooks/payments/route.ts
│   ├── lib/
│   │   ├── auth.ts                 # server-only: requireSession(), permission checks
│   │   ├── db.ts                   # server-only: pool or ORM client
│   │   └── data/orders.ts          # server-only DAL: scoped queries, DTOs, use cache
│   └── components/ui/              # shared presentational components
└── tests/                          # unit (DAL, actions) and e2e (routes)
```

## 7. Design Patterns

- **Data access layer**: one server-only module per domain; functions take the verified principal (or tenant and user ids) and return DTOs. Authentication, authorization and `process.env` access live here.
- **Static shell plus streamed holes**: static layout and cached content around `<Suspense>` boundaries for personalised parts.
- **Thin actions**: `"use server"` file contains parse, authorize, call DAL, invalidate. Business logic lives in the DAL so it is testable without Next.js.
- **Action state**: `useActionState(action, initialState)` for validation errors; the action returns serializable state instead of throwing for expected failures.
- **Tag per entity and per list**: `orders:{tenantId}:{userId}` for lists, `order:{id}` for details; invalidate both on write.
- **Slot-based layouts**: parallel routes for dashboards and modals via intercepting routes.
- **Preserved UI state**: with Cache Components, previous routes stay mounted in React `<Activity>` as `hidden`; effects are cleaned up while hidden. Components relying on unmount to reset state need explicit resets.

## 8. Best Practices

- Hoist the dynamic part, not the whole page: wrap the smallest component that reads `cookies()` in `<Suspense>`, so the shell stays static.
- Use `loading.tsx` for route-level fallbacks and `<Suspense>` for component-level ones; use `error.tsx` or an error boundary around failure-prone subtrees.
- For non-deterministic values (`Math.random()`, `Date.now()`, `crypto.randomUUID()`), call `await connection()` first under Suspense, or compute inside a cached scope when one value per cache entry is intended.
- `generateMetadata` and `generateViewport` have their own rules for uncached fetches and runtime APIs under Cache Components; check the "with Cache Components" sections of their docs.
- Use `next/form` or a plain `<form action={serverAction}>` so submissions work before hydration.
- Route handlers: `GET` follows the same prerendering model as pages when Cache Components is on. Handlers for mutations still authenticate and validate.
- Migrate incrementally: enable `cacheComponents`, convert each route segment `dynamic`/`revalidate`/`fetchCache` export, and use `export const instant = false` on segments that are not ready (per the migration guide); fix synchronous IO such as `Date.now()` first since it cannot be deferred.

## 9. Performance

- Turbopack is the default in 16 with file-system caching for dev and build; remove `--turbopack` flags and migrate custom webpack config or pass `--webpack`.
- Enable `partialPrefetching: true` next to `cacheComponents: true` (new apps from `create-next-app` have both); it prefetches one reusable app shell per route.
- React Compiler: `reactCompiler: true` in `next.config.ts` plus `babel-plugin-react-compiler`; stable in 16, not on by default, increases compile time. Next.js applies it only to relevant files.
- Stream slow components instead of blocking the shell; start independent fetches in parallel (`Promise.all` in a server component) to avoid waterfalls.
- Use `React.cache` to dedupe the same fetch within one render pass (it is isolated inside `use cache` scopes, so pass data in as arguments).
- Defaults changed in 16 for images: `minimumCacheTTL` 4 hours, `qualities` `[75]`, no `16` in `imageSizes`; local images with query strings need `images.localPatterns`.
- Large Server Action payloads: default body limit is 1 MB; raise `serverActions.bodySizeLimit` only when needed and validate sizes server-side.

## 10. Security

- Every Server Action is a public POST endpoint even if no UI references it. Validate input with a schema, call `requireSession()` inside the action, authorize against the specific resource, and scope the write by tenant and owner. A page-level or `proxy.ts` check does not protect the action.
- Never trust ids, roles or tenant ids from the client; derive identity from the verified session.
- Server Actions get built-in protection: encrypted action ids, dead-code elimination of unused actions, an `Origin` versus `Host` check, a 1 MB body cap, and encrypted closure variables. Behind a proxy that rewrites the host, forward `x-forwarded-host` or add `serverActions.allowedOrigins`. These reduce risk; they do not replace authorization.
- Self-hosted multi-instance deployments: set a stable `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` shared by all instances.
- Keep `next` and `react` patched. In December 2025 React Server Components had a critical unauthenticated RCE (CVE-2025-55182) followed by DoS and source exposure advisories (CVE-2025-55183, CVE-2025-55184, CVE-2025-67779, CVE-2026-23864); fixed releases exist for each supported line, so stay on the latest patch of your minor.
- `import 'server-only'` on DAL, session and secret-bearing modules so an accidental client import fails the build. Optionally enable `experimental.taint` and the React taint APIs as an extra layer; filter data in the DAL regardless.
- No secrets in `NEXT_PUBLIC_*` or client components. Only the DAL reads `process.env` secrets.
- CSP: use nonces generated per request in `proxy.ts` with `script-src 'self' 'nonce-...' 'strict-dynamic'` and `style-src 'self' 'nonce-...'`; never `unsafe-inline`. `unsafe-eval` is only needed in development. Nonces require dynamic rendering of the pages that carry them. See [references/proxy-auth-and-security.md](references/proxy-auth-and-security.md).
- No `dangerouslySetInnerHTML` with unsanitized input; sanitize with a maintained sanitizer on the server or render structured data.
- `redirect()` targets from user input must be validated against an allowlist of relative paths.
- Remote images: `images.remotePatterns` with exact hosts; `images.dangerouslyAllowLocalIP` stays off except on private networks.

## 11. Testing

- Unit-test the DAL and action logic as plain async functions (Vitest or Jest) with a real or containerised database where tenant scoping matters.
- Async Server Components are not supported by Vitest or Jest renderers; cover them with end-to-end tests (Playwright) and keep logic in testable modules.
- Negative tests for actions: unauthenticated call, wrong tenant, foreign object id, extra form fields, oversized input.
- Assert caching behaviour at the route level: after a mutation the next navigation shows fresh data (`updateTag`), and tenant A never sees tenant B's cached output.
- Run `next build` in CI; Cache Components turns blocking reads and synchronous IO into build or dev-overlay errors.

## 12. Review Checklist

- [ ] Server Components by default; `'use client'` only on leaves that need it, with narrow DTO props.
- [ ] Every runtime read (`cookies`, `headers`, `searchParams`, uncached fetch) sits under `<Suspense>`.
- [ ] Every `use cache` scope has an explicit `cacheLife`, serializable arguments, and tenant/user ids as arguments when data is scoped.
- [ ] No `cookies()` or `headers()` inside `use cache` (except `use cache: private`).
- [ ] Each Server Action validates input, calls `requireSession()`, authorizes the resource and scopes the write.
- [ ] Correct invalidation API: `updateTag` in actions for read-your-writes, `revalidateTag(tag, 'max')` elsewhere.
- [ ] `proxy.ts` holds no database calls and is not the only auth layer; matcher excludes static assets.
- [ ] `server-only` on server modules; no secrets in client code or `NEXT_PUBLIC_*`.
- [ ] CSP uses nonces, without `unsafe-inline`.
- [ ] `params`, `searchParams`, `cookies()`, `headers()` are awaited.
- [ ] `next`/`react` on a patched release.

## 13. Production Notes

- Serverless: the default in-memory cache handler rarely survives between requests, so `use cache` mostly benefits the build-time shell and client prefetch; use `use cache: remote` or a platform cache handler (`cacheHandlers`) where reuse matters. Self-hosted instances keep in-memory entries (`cacheMaxMemorySize` bounds them).
- Cache keys include the build id (or `deploymentId` when set), so entries do not carry over to a new deploy.
- Draft Mode re-executes cached functions on every request and does not store results.
- On the client the router enforces a minimum 30 second stale time regardless of `cacheLife`.
- Next.js 16 needs Node.js 20.9+; `next dev` and `next build` write to separate directories and can run concurrently.
- Upgrade path: `npx @next/codemod@canary upgrade latest` (also migrates `middleware` to `proxy`); if sync request API usage remains, run the `next-async-request-api` codemod separately.

## 14. Examples

### Example 1: Tenant-scoped cached data, streamed per request

```typescript
// src/lib/data/orders.ts
import 'server-only'
import { cacheLife, cacheTag } from 'next/cache'
import { pool } from '@/lib/db'

export type OrderDTO = { id: string; totalCents: number; status: string }

// tenantId and userId are arguments, so they are part of the cache key:
// one tenant or user can never read another's entry.
export async function listOrders(tenantId: string, userId: string): Promise<OrderDTO[]> {
  'use cache'
  cacheLife('minutes')
  cacheTag(`orders:${tenantId}:${userId}`)
  const { rows } = await pool.query<{ id: string; total_cents: number; status: string }>(
    `SELECT id, total_cents, status FROM orders
      WHERE tenant_id = $1 AND user_id = $2
      ORDER BY created_at DESC LIMIT 50`,
    [tenantId, userId],
  )
  return rows.map((r) => ({ id: r.id, totalCents: r.total_cents, status: r.status }))
}
```

```tsx
// src/app/(app)/orders/page.tsx
import { Suspense } from 'react'
import { requireSession } from '@/lib/auth'
import { listOrders } from '@/lib/data/orders'

async function Orders() {
  const session = await requireSession()           // reads cookies: request-time, so it sits under Suspense
  const orders = await listOrders(session.tenantId, session.userId)
  return (
    <ul>
      {orders.map((o) => (
        <li key={o.id}>{o.id}: {(o.totalCents / 100).toFixed(2)} ({o.status})</li>
      ))}
    </ul>
  )
}

export default function Page() {
  return (
    <>
      <h1>Orders</h1>
      <Suspense fallback={<p>Loading orders...</p>}>
        <Orders />
      </Suspense>
    </>
  )
}
```

### Example 2: Server Action with validation, authorization, scoped write and read-your-writes

```typescript
// src/app/(app)/orders/actions.ts
'use server'
import { z } from 'zod'
import { updateTag } from 'next/cache'
import { requireSession } from '@/lib/auth'
import { pool } from '@/lib/db'

export type FormState = { ok: boolean; message?: string; fieldErrors?: Record<string, string[]> }

const schema = z.object({
  orderId: z.uuid(),
  shippingAddress: z.string().trim().min(1).max(500),
})

export async function updateShipping(_prev: FormState, formData: FormData): Promise<FormState> {
  const session = await requireSession()                       // re-verified here, not only in proxy.ts
  if (!session.permissions.includes('orders:update')) return { ok: false, message: 'Forbidden' }

  // Pick fields explicitly: the form also carries framework-internal hidden fields.
  const parsed = schema.safeParse({
    orderId: formData.get('orderId'),
    shippingAddress: formData.get('shippingAddress'),
  })
  if (!parsed.success) return { ok: false, fieldErrors: z.flattenError(parsed.error).fieldErrors }

  // Tenant and owner are part of the write, never taken from the client.
  const { rowCount } = await pool.query(
    `UPDATE orders SET shipping_address = $1, updated_at = now()
      WHERE id = $2 AND tenant_id = $3 AND user_id = $4 AND status = 'pending'`,
    [parsed.data.shippingAddress, parsed.data.orderId, session.tenantId, session.userId],
  )
  if (rowCount === 0) return { ok: false, message: 'Order not found or not editable' }

  updateTag(`orders:${session.tenantId}:${session.userId}`)    // next read waits for fresh data
  return { ok: true }
}
```

```tsx
// src/app/(app)/orders/shipping-form.tsx
'use client'
import { useActionState } from 'react'
import { updateShipping, type FormState } from './actions'

const initial: FormState = { ok: false }

export function ShippingForm({ orderId }: { orderId: string }) {
  const [state, formAction, pending] = useActionState(updateShipping, initial)
  return (
    <form action={formAction}>
      <input type="hidden" name="orderId" value={orderId} />
      <label htmlFor="addr">Shipping address</label>
      <input id="addr" name="shippingAddress" required maxLength={500} />
      {state.fieldErrors?.shippingAddress && <p role="alert">{state.fieldErrors.shippingAddress[0]}</p>}
      {state.message && <p role="alert">{state.message}</p>}
      <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
    </form>
  )
}
```

### Example 3: `proxy.ts` as an optimistic pre-filter

```typescript
// proxy.ts (Next.js 16; on 15 name the file middleware.ts and the export middleware)
import { NextResponse, type NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  // Cookie presence only: no database call, no authorization decision.
  if (!request.cookies.has('__Host-session')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/app/:path*'],
}
```

The DAL and every action still call `requireSession()`; the proxy only saves an unauthenticated visitor a round trip.

## 15. Common Mistakes

- Treating `proxy.ts` or a page-level redirect as the only authorization layer; Server Actions remain directly callable.
- Passing whole database rows to Client Components; every prop is serialized into the HTML or RSC payload.
- Reading `cookies()` inside `use cache` (build error) instead of passing the extracted value as an argument.
- Caching per-user data in a shared `use cache` function without the user or tenant id in the arguments.
- Omitting `cacheLife`, then being surprised by the implicit 15 minute revalidation, or nesting a short-lived `use cache` inside one without an explicit lifetime (fails prerendering).
- Calling `updateTag` from a route handler (it throws; use `revalidateTag(tag, 'max')`) or `revalidateTag(tag)` with one argument on 16 (deprecated, a type error).
- Using `Object.fromEntries(formData)` with a strict schema; hidden framework fields make it fail. Pick fields explicitly.
- Forgetting `await` on `params`, `searchParams`, `cookies()` or `headers()` in 16 (synchronous access is removed).
- Running `Date.now()` or `Math.random()` in a prerendered component; defer with `await connection()` under Suspense.
- Putting a large `'use client'` boundary at the layout root, pulling entire trees into the client bundle.
- Relying on `Promise.all` to parallelise Server Actions from the client; they are dispatched one at a time.
- Matching `proxy.ts` against every request including static assets and prefetches without a `matcher`.
- Using `images.domains` (deprecated) or leaving `dangerouslyAllowLocalIP` on in public deployments.
- Setting `unsafe-inline` in the CSP instead of using nonces.

## 16. References

- [references/caching-and-rendering.md](references/caching-and-rendering.md): Cache Components model, directives, `cacheLife` profiles, invalidation APIs, streaming, the previous caching model.
- [references/server-actions-and-mutations.md](references/server-actions-and-mutations.md): action anatomy, validation and error state, authorization, DAL for writes, forms, optimistic UI, route handlers.
- [references/proxy-auth-and-security.md](references/proxy-auth-and-security.md): `proxy.ts` rules, migration from middleware, session reads with Cache Components, CSP nonce setup, hardening settings.
- Official docs: https://nextjs.org/docs/app, upgrade guide https://nextjs.org/docs/app/guides/upgrading/version-16, data security guide https://nextjs.org/docs/app/guides/data-security, Content Security Policy guide https://nextjs.org/docs/app/guides/content-security-policy.
