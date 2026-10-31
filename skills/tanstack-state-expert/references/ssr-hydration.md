# SSR and Hydration

Server rendering with TanStack Query in the Next.js App Router (and the same ideas elsewhere): a per-request `QueryClient`, `dehydrate` and `HydrationBoundary`, streaming pending queries, serialization, persistence and the Zustand per-request store. Based on the TanStack Query advanced-SSR guide (docs main branch) and the 5.105.0 type definitions; the provider and page code type-checked with TypeScript 6.0.3 (2026-10). Next.js caching and Server Component rules belong to nextjs-15-architect.

## Contents

1. [The rule: one QueryClient per request](#1-the-rule-one-queryclient-per-request)
2. [Client factory and provider](#2-client-factory-and-provider)
3. [Prefetch in a Server Component](#3-prefetch-in-a-server-component)
4. [Streaming pending queries](#4-streaming-pending-queries)
5. [Data ownership and revalidation](#5-data-ownership-and-revalidation)
6. [Serialization and non-JSON data](#6-serialization-and-non-json-data)
7. [Persistence on the client](#7-persistence-on-the-client)
8. [Zustand with SSR](#8-zustand-with-ssr)
9. [Troubleshooting hydration](#9-troubleshooting-hydration)

## 1. The rule: one QueryClient per request

- A module-level `new QueryClient()` on the server is shared by every request and every user. Cached data from one user can be dehydrated into another user's HTML. Create a client per request on the server.
- In the browser, keep a single client for the life of the page. Do not create it with `useState` or `useRef` directly above code that can suspend without a Suspense boundary in between: React discards that state if the first render suspends, and the cache is lost.
- Set a default `staleTime` above `0` (the guide uses 60 seconds). With the default of `0`, data fetched on the server is stale on the first client render and refetches immediately, which defeats prefetching.
- `retry` defaults to `0` on the server.

## 2. Client factory and provider

```ts
// app/get-query-client.ts
import { defaultShouldDehydrateQuery, environmentManager, QueryClient } from '@tanstack/react-query'

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 60_000 },
      dehydrate: {
        // also send queries that are still pending so their promises stream to the client
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) || query.state.status === 'pending',
      },
    },
  })
}

let browserQueryClient: QueryClient | undefined

export function getQueryClient() {
  if (environmentManager.isServer()) return makeQueryClient() // new client for every call on the server
  return (browserQueryClient ??= makeQueryClient())
}
```

```tsx
// app/providers.tsx
'use client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { getQueryClient } from './get-query-client'

export function Providers({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

- `environmentManager.isServer()` is the current way to detect the server; the old `isServer` export is marked deprecated in 5.105.
- The provider wraps `children` in `app/layout.tsx`. `QueryClientProvider` uses context, so the file needs `'use client'`.
- The Next.js Server Component helper alternative is `cache(() => new QueryClient())` from React: one client per request, shared by all Server Components, at the cost of `dehydrate` serializing the whole cache each time.

## 3. Prefetch in a Server Component

```tsx
// app/todos/page.tsx  (Server Component, no 'use client')
import { dehydrate, HydrationBoundary } from '@tanstack/react-query'
import { getQueryClient } from '../get-query-client'
import { todoQueries } from './queries'
import { TodoList } from './todo-list'

export default async function TodosPage() {
  const queryClient = getQueryClient()
  await queryClient.query(todoQueries.list({ status: 'open' })) // errors reject; catch to degrade gracefully

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TodoList />
    </HydrationBoundary>
  )
}
```

```tsx
// app/todos/todo-list.tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { todoQueries } from './queries'

export function TodoList() {
  // same options object as the server: key, queryFn and staleTime are shared
  const { data } = useQuery(todoQueries.list({ status: 'open' }))
  return <ul>{data?.map((t) => <li key={t.id}>{t.title}</li>)}</ul>
}
```

- Share the `queryOptions` between server prefetch and client hook so keys can never diverge. A key mismatch means the client misses the cache and fetches again.
- `HydrationBoundary` is a Client Component and can appear at several levels; each Server Component may create its own client and dehydrate it. Nested awaiting Server Components create a server waterfall; use parallel routes, `Promise.all`, or start the fetch without awaiting (next section).
- On 5.105 the docs show `queryClient.query(...)` for the prefetch; older code uses `await queryClient.prefetchQuery(...)`, which still works but is marked deprecated. `prefetchQuery` swallows errors; `query` rejects, so wrap with `.catch(noop)` when the page should still render.
- Do not fetch with Server Actions inside a `queryFn` (client-called actions run serially); call a route handler or your API client.

## 4. Streaming pending queries

With `shouldDehydrateQuery` including pending queries (section 2), the server does not need to await:

```tsx
// app/todos/page.tsx
import { dehydrate, HydrationBoundary } from '@tanstack/react-query'
import { getQueryClient } from '../get-query-client'

export default function TodosPage() {
  const queryClient = getQueryClient()
  void queryClient.query(todoQueries.list({ status: 'open' })).catch(() => {}) // start, do not await

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TodoList />
    </HydrationBoundary>
  )
}
```

- The promise is serialized over the wire and placed in the client cache. In the client component use `useSuspenseQuery`: it suspends on that promise and the server streams the data when the query resolves. With plain `useQuery`, Next.js does not suspend and the component renders in `pending`, which opts that part out of server-rendered content.
- This streaming of pending queries relies on React serializing promises to Client Components; it works in the Next.js App Router. Check the guide for other frameworks.
- Wrap the consumer in `<Suspense>` (or a `loading.tsx`) so the rest of the page streams first.
- `dehydrate` has a `shouldRedactErrors` option for errors of dehydrated queries. The guide returns `false` for Next.js so framework errors that signal dynamic rendering are not redacted; check the docs for the default in your version and do not disable redaction elsewhere, so internal error text does not reach the browser.
- `@tanstack/react-query-next-experimental` (5.105.0) offers `ReactQueryStreamedHydration` to stream without prefetching, calling `useSuspenseQuery` in client components during SSR. It is experimental; prefer explicit prefetching, which avoids request waterfalls on navigation as well.

## 5. Data ownership and revalidation

- Rendering `queryClient.query` results in a Server Component and also reading the same query in a Client Component leads to drift: a client refetch cannot re-render the Server Component, so the two show different data.
- Rule of thumb from the guide: in Server Components, treat the QueryClient as a place to prefetch only. Do not render or pass down the awaited value. Let Client Components read from the cache.
- If you only need server-rendered, cached data with no client interactivity, skip TanStack Query and use the framework's data fetching and caching. Add Query when you need mutations with optimistic updates, polling, infinite scroll or shared client cache.
- After a mutation, `invalidateQueries` refreshes the client cache; Server Component output needs the framework's own revalidation (for example `router.refresh()` or revalidation tags in Next.js).

## 6. Serialization and non-JSON data

- Dehydrated state is serialized into the HTML or RSC payload. Plain JSON works. `Date`, `Map`, `BigInt` or `undefined` fields need a transformer.
- `dehydrate.serializeData` and `hydrate.deserializeData` (QueryClient `defaultOptions`) run on each side; serialize inside the server `queryFn` result as shown in the guide and deserialize on hydration so the cache has one shape on both sides.
- Never put secrets, tokens or other users' data in prefetched queries: everything dehydrated is visible in page source.
- Prefetch user-specific data only in dynamic, uncached routes, or the HTML containing it may be cached and served to others (a Next.js route cache concern; see nextjs-15-architect).

## 7. Persistence on the client

```tsx
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'
import { defaultShouldDehydrateQuery } from '@tanstack/react-query'

const persister = createSyncStoragePersister({ storage: window.localStorage })

<PersistQueryClientProvider
  client={queryClient}
  persistOptions={{
    persister,
    maxAge: 24 * 60 * 60 * 1000,
    buster: APP_VERSION,
    // only save successful queries; never persist pending promises
    dehydrateOptions: { shouldDehydrateQuery: defaultShouldDehydrateQuery },
  }}
>
  {children}
</PersistQueryClientProvider>
```

- Persisted caches live in `localStorage` or IndexedDB and are readable by any script on the origin. Do not persist tokens or sensitive personal data; filter with `shouldDehydrateQuery` (for example by a `meta.persist` flag) and clear the cache on logout.
- Set `gcTime` at least as long as `maxAge`, otherwise restored queries are garbage collected early. Change `buster` when the data shape changes.
- Persister packages are 5.105.0 (`@tanstack/react-query-persist-client`, `@tanstack/query-sync-storage-persister`, `@tanstack/query-async-storage-persister`); read their README for the current options.
- Create the persister only in the browser (guard `window`).

## 8. Zustand with SSR

- A module-level Zustand store on the server is shared across requests. For anything user-specific, create the store per request or per provider with `createStore` and share it through context (see zustand.md section 6).
- Server Components must not read or write the store; only Client Components use it.
- Initialize the store from props passed by the Server Component so server and client render the same output; otherwise React reports a hydration mismatch.
- `persist` reads storage on the client only; either render a neutral value until `persist.hasHydrated()` or use `skipHydration` and call `rehydrate()` in an effect.

## 9. Troubleshooting hydration

| Symptom | Likely cause | Fix |
|---|---|---|
| Client refetches right after load | `staleTime` is `0` | Set a default `staleTime` in the shared factory |
| Data fetched twice (server and client) | Key mismatch between prefetch and hook | Share `queryOptions`; check key factories |
| Page stuck in loading with streaming | `useQuery` instead of `useSuspenseQuery`, or no Suspense boundary | Use `useSuspenseQuery` inside `<Suspense>` |
| Cache empty after first render | Client created in `useState` above a suspending child with no boundary | Use the module-level browser singleton from section 2 |
| Hydration mismatch on dates | Non-JSON values or locale-dependent formatting | Serialize/deserialize; format in an effect or with a fixed locale and time zone |
| One user sees another user's data | Shared server-side `QueryClient`, or cached dynamic HTML | New client per request; do not cache user-specific routes |
| Error text visible to users | Redaction disabled or server errors passed through | Keep error redaction on; map errors to safe messages |
