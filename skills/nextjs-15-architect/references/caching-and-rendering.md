# Caching and Rendering in Next.js 16 (with Next.js 15 differences)

Verified against Next.js 16.4.3 and 15.5.x (2026-10). Cache Components requires Next.js 16; on 15 use the previous model described at the end.

## Enabling Cache Components

```typescript
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true, // set explicitly; unset logs a warning, requires cacheComponents
}

export default nextConfig
```

- Data fetching is dynamic by default; you opt in to caching per function, component or file.
- `cacheComponents` implements Partial Prerendering as the default: the prerendered static shell contains static JSX plus `use cache` output, and `<Suspense>` boundaries stream request-time content.
- It needs the Node.js runtime and rejects a `runtime` route segment export. The segment configs `dynamic`, `revalidate` and `fetchCache` error once the flag is on; replace them with `use cache` and `cacheLife`.
- `experimental.ppr`, `experimental_ppr`, `experimental.dynamicIO` and `experimental.useCache` are removed in 16.
- Navigation keeps previous routes mounted in `<Activity>` (hidden, effects cleaned up), so state survives back navigation.

## The three cache directives

| Directive | Stored | Can read `cookies()` / `headers()` | Use when |
|---|---|---|---|
| `"use cache"` | in memory by default, or a configured `cacheHandlers` entry | no; pass values as arguments | Shared or per-key data, static shell content |
| `"use cache: remote"` | a remote cache handler shared by all instances | no | In-memory entries are evicted or not reused (serverless) and upstream load matters; costs a network lookup |
| `"use cache: private"` | browser memory only, never a server cache | yes | A session helper or compliance rule prevents passing runtime values as arguments; needs `cacheLife`; cannot use custom handlers |

Placement: top of an async function or component, or top of a file (every export becomes cached and must be async). Cached scopes must be `async`.

### Cache keys and serialization

- Key = build id (or `deploymentId` when configured) + function id + serializable arguments (props for components) + captured closure variables. Different `tenantId` or `userId` arguments produce separate entries.
- Arguments: primitives, plain objects, arrays, Date, Map, Set, typed arrays, ArrayBuffer; React elements only as pass-through. Return values: the same plus JSX.
- Not serializable: class instances, functions (except pass-through), symbols, WeakMap, WeakSet, `URL`.
- Pass-through: accept `children` or a Server Action and render or forward it without reading it.
- `React.cache` is isolated inside `use cache`; values set outside are not visible inside. Pass data via arguments.
- Request-time APIs (`cookies()`, `headers()`, `searchParams`) fail inside a cached scope, including through helpers on the call stack. `draftMode().isEnabled` can be read; `enable()`/`disable()` cannot be called there.

```tsx
import { cookies } from 'next/headers'
import { Suspense } from 'react'

export default function Page() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <Profile />
    </Suspense>
  )
}

// Not cached: reads the cookie at request time.
async function Profile() {
  const sessionId = (await cookies()).get('__Host-session')?.value
  if (!sessionId) return <p>Signed out</p>
  return <ProfileCard sessionId={sessionId} />
}

// Cached: sessionId is part of the key. Look up the user from the session id on the server;
// the output is only ever reused for the same session id.
async function ProfileCard({ sessionId }: { sessionId: string }) {
  'use cache'
  const user = await loadUserBySession(sessionId)
  return <p>{user.displayName}</p>
}

declare function loadUserBySession(sessionId: string): Promise<{ displayName: string }>
```

Prefer a stable opaque id (user id or tenant id) as the argument over a raw session token, so cache keys do not contain credentials.

## cacheLife

Import from `next/cache`. Call inside the cached scope, once per invocation (different branches may each call it). Cannot be called at module scope.

| Profile | stale (client) | revalidate (server) | expire |
|---|---|---|---|
| `default` | 5 minutes | 15 minutes | never |
| `seconds` | 30 seconds | 1 second | 1 minute |
| `minutes` | 5 minutes | 1 minute | 1 hour |
| `hours` | 5 minutes | 1 hour | 1 day |
| `days` | 5 minutes | 1 day | 1 week |
| `weeks` | 5 minutes | 1 week | 30 days |
| `max` | 5 minutes | 30 days | 1 year |

- Custom: `cacheLife({ stale: 300, revalidate: 900, expire: 3600 })`; `expire` must exceed `revalidate`. Omitted values fall back to the `default` profile.
- Named profiles can be redefined in `next.config.ts` (including `default` and `max`); document any redefinition because `'hours'` then no longer means one hour.
- `stale` also decides whether content can be part of the route's app shell; the client router enforces at least 30 seconds.
- Short lifetimes change prerendering: `revalidate: 0` or `expire` under 5 minutes is excluded from prerenders (a dynamic hole resolved at request time; of the presets only `seconds`); `stale` under 30 seconds is also excluded; `stale` from 30 seconds to under 5 minutes is prerendered but kept out of the app shell. Put a `<Suspense>` boundary around dynamic caches.
- Nested caches: an explicit outer `cacheLife` always wins, whether longer or shorter than inner lifetimes. Without one, a short-lived inner cache would shorten the outer one, so Next.js throws during prerender; set an explicit outer `cacheLife`.
- Set `cacheLife` in every cached scope so the lifetime is visible at the call site.

## cacheTag and invalidation

```typescript
import { cacheTag } from 'next/cache'
// inside a cached scope
cacheTag('posts', `post:${id}`) // up to 128 tags per call, each at most 256 characters
```

| API | Where | Behavior |
|---|---|---|
| `updateTag(tag)` | Server Actions only | Expires the tag immediately; the action response re-renders with fresh data (read-your-writes). Throws elsewhere. |
| `revalidateTag(tag, profile)` | Server Actions and route handlers | Marks stale; with `'max'` serves stale while refreshing in the background. `profile` is a `cacheLife` profile name or object. One-argument form is deprecated in 16 and a type error. |
| `revalidatePath(path, type?)` | Server Actions and route handlers | Invalidates by URL; `type` is `'layout'` or `'page'`. |
| `refresh()` | Server Actions | Re-fetches the current route's RSC payload without invalidating cached data. |

Tags also work for `fetch(url, { next: { tags: ['posts'] } })` calls.

## Streaming and runtime data

- Uncached async work and runtime APIs must be under `<Suspense>`; otherwise the dev overlay reports a blocking route and the build fails to prerender.
- `<Suspense>` itself does not make a component dynamic; synchronous work still finishes during prerender.
- Non-deterministic values (`Math.random()`, `Date.now()`, `crypto.randomUUID()`): call `await connection()` from `next/server` first under Suspense for per-request values, or compute inside a cached scope for one value per entry. These cannot be deferred with `instant = false`.
- `after()` from `next/server` runs work after the response is sent.
- Error boundaries (`error.tsx`, `catchError`) contain failures per subtree.

## Params and prerendering

- With Cache Components `generateStaticParams` must return at least one param (an empty array errors); other values render at request time. Removing the export opts the route out of ISR. See the ISR with Cache Components guide.
- Delete `export const dynamicParams`; it is not compatible with `cacheComponents`. To reject unknown params call `notFound()` when the param does not resolve to real data.
- `params` and `searchParams` are Promises; with Cache Components `searchParams` is runtime data and belongs under Suspense.
- Root params: use `next/root-params` (replaces removed `unstable_rootParams`).

## Migration: Next.js 15 model to Cache Components

1. Upgrade to 16 (`npx @next/codemod@canary upgrade latest`), then run `next-async-request-api` if synchronous request API use remains.
2. Enable `cacheComponents` and `partialPrefetching`.
3. Replace each segment config: remove `dynamic = 'force-dynamic'` (uncached data and request APIs already run at request time); turn `dynamic = 'force-static'` into explicit `use cache` with a `cacheLife` such as `'max'`; replace `revalidate = N` with `cacheLife` around the data or UI to cache; follow the migration guide for `fetchCache` and `fetch` cache options.
4. Opt unfinished routes out with `export const instant = false` (the `cache-components-instant-false` codemod applies it app-wide), fix synchronous IO, then convert one route at a time.
5. Existing `fetch` caching and `unstable_cache` keep working; migrating them is optional.

## The previous model (Next.js 15, or 16 without the flag)

- `fetch` is not cached by default. Opt in with `cache: 'force-cache'`, `next: { revalidate: seconds }` and `next: { tags: [...] }`.
- Non-fetch functions: `unstable_cache(fn, keyParts, { tags, revalidate })`. Include user or tenant ids in `keyParts` or arguments for scoped data.
- Segment config: `export const dynamic`, `revalidate`, `fetchCache`.
- `GET` route handlers are uncached by default.
- On-demand: `revalidateTag(tag)` (one argument on 15), `revalidatePath`. `updateTag` and `refresh` do not exist on 15.
- `"use cache"` on 15 exists only on canary behind `experimental.useCache` / `dynamicIO`; do not use it in production on 15 stable.
