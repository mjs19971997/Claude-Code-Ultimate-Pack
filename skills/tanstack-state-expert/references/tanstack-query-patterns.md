# TanStack Query Patterns

Read-side patterns for `@tanstack/react-query` v5: defaults, key factories, `queryOptions`, infinite and parallel queries, dependent queries, cancellation, prefetching, Suspense and error boundaries, TypeScript registration, the ESLint plugin and devtools. The code blocks were type-checked against `@tanstack/react-query` 5.105.0 with TypeScript 6.0.3 and React 19 types (2026-10).

## Contents

1. [Defaults worth knowing](#1-defaults-worth-knowing)
2. [Query keys and key factories](#2-query-keys-and-key-factories)
3. [queryOptions and infiniteQueryOptions](#3-queryoptions-and-infinitequeryoptions)
4. [Infinite queries](#4-infinite-queries)
5. [Parallel and dependent queries](#5-parallel-and-dependent-queries)
6. [Cancellation with AbortSignal](#6-cancellation-with-abortsignal)
7. [Prefetching and imperative fetches](#7-prefetching-and-imperative-fetches)
8. [Suspense and error boundaries](#8-suspense-and-error-boundaries)
9. [TypeScript registration](#9-typescript-registration)
10. [ESLint plugin and devtools](#10-eslint-plugin-and-devtools)
11. [Other framework adapters](#11-other-framework-adapters)

## 1. Defaults worth knowing

| Option | Default | Meaning |
|---|---|---|
| `staleTime` | `0` | Data is stale immediately; a new observer, window focus or reconnect triggers a background refetch |
| `gcTime` | 5 minutes | How long an inactive query stays in the cache before garbage collection |
| `retry` | `3` in the browser, `0` on the server | Failed queries retry with exponential backoff; mutations do not retry by default |
| `refetchOnWindowFocus` | `true` | Refetches stale active queries on focus |
| `structuralSharing` | on | Keeps object references stable when the JSON-compatible data did not change |

- `staleTime` is how long data counts as fresh; `gcTime` is how long unused data is kept. They are independent. Raise `staleTime` (for example 30 seconds to a few minutes) instead of disabling `refetchOnWindowFocus` globally.
- `staleTime: Infinity` still allows `invalidateQueries` to refetch. `staleTime: 'static'` blocks even manual invalidation; use it only for data that cannot change while the app runs (feature flags loaded at boot).
- v5 status names: `status` is `'pending' | 'error' | 'success'`; `isPending` replaces v4 `isLoading`; `isLoading` now means `isFetching && isPending`. `cacheTime` is `gcTime`. `useQuery` no longer accepts `onSuccess`, `onError` or `onSettled`; use effects, `select`, or the cache-level `QueryCache({ onError })`.
- Set `retry: false` (or a small number) in tests and for 4xx responses: `retry: (count, error) => !isClientError(error) && count < 3`.

```ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
})
```

## 2. Query keys and key factories

Keys are arrays, hashed deterministically; object key order does not matter, array order does. Everything the `queryFn` reads must be in the key.

```ts
type Filters = { status?: 'open' | 'done' }

export const todoKeys = {
  all: ['todos'] as const,
  lists: () => [...todoKeys.all, 'list'] as const,
  list: (f: Filters) => [...todoKeys.lists(), f] as const,
  details: () => [...todoKeys.all, 'detail'] as const,
  detail: (id: number) => [...todoKeys.details(), id] as const,
}
```

- Hierarchy gives cheap invalidation: `invalidateQueries({ queryKey: todoKeys.lists() })` hits every list and no detail; `todoKeys.all` hits everything. Matching is by prefix unless `exact: true`.
- Keep keys serializable (no functions, class instances, `Date` objects that you mutate). Use ids, strings and plain objects.
- Never put secrets or tokens in a key: keys appear in devtools, dehydrated state and persisted caches.
- Per-user data needs the user id (or tenant) in the key, so a logout and login as another user cannot show the previous cache. Also call `queryClient.clear()` on logout.

## 3. queryOptions and infiniteQueryOptions

`queryOptions` returns its argument unchanged at runtime and tags the key with the data type, so the same object works in `useQuery`, `useSuspenseQuery`, `useQueries`, `queryClient.query` and `queryClient.setQueryData` with full inference.

```ts
import { queryOptions } from '@tanstack/react-query'

type Todo = { id: number; title: string; done: boolean }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export const todoQueries = {
  list: (f: Filters) =>
    queryOptions({
      queryKey: todoKeys.list(f),
      queryFn: ({ signal }) => api<Todo[]>(`/todos?status=${f.status ?? ''}`, { signal }),
      staleTime: 30_000,
    }),
  detail: (id: number) =>
    queryOptions({
      queryKey: todoKeys.detail(id),
      queryFn: ({ signal }) => api<Todo>(`/todos/${id}`, { signal }),
    }),
}

// Component-level overrides keep inference: data is string[] here
// useQuery({ ...todoQueries.list({}), select: (d) => d.map((t) => t.title) })
// Typed cache access: queryClient.setQueryData(todoQueries.detail(1).queryKey, next)
```

- Only components that need a different shape add `select`; a stable, defined-outside-render function (or `useCallback`) avoids re-running it every render.
- `mutationOptions` exists as the mutation counterpart (see mutations-and-optimistic-updates.md).

## 4. Infinite queries

`initialPageParam` is required in v5. `getNextPageParam` returning `undefined` or `null` ends the list.

```ts
import { infiniteQueryOptions, useInfiniteQuery } from '@tanstack/react-query'

type Page = { items: Todo[]; nextCursor: number | null }

export const todoPages = () =>
  infiniteQueryOptions({
    queryKey: [...todoKeys.all, 'infinite'] as const,
    queryFn: ({ pageParam, signal }) => api<Page>(`/todos?cursor=${pageParam}`, { signal }),
    initialPageParam: 0,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    maxPages: 5, // optional: keep at most 5 pages in memory (needs getPreviousPageParam to refetch earlier pages)
  })

// const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery(todoPages())
// const all = data?.pages.flatMap((p) => p.items) ?? []
```

- `data` is `{ pages, pageParams }`. Refetching refetches pages sequentially from the first one, so very long lists are expensive; use `maxPages` or a server-side cursor design that keeps lists short.
- Trigger `fetchNextPage` from an intersection observer; guard with `hasNextPage && !isFetchingNextPage`.
- Use `isFetchingNextPage` (not `isFetching`) for the "load more" spinner.

## 5. Parallel and dependent queries

```ts
import { skipToken, useQueries, useQuery } from '@tanstack/react-query'

// Parallel, dynamic number of queries, with combine to produce a stable derived value
const result = useQueries({
  queries: ids.map((id) => todoQueries.detail(id)),
  combine: (results) => ({
    data: results.map((r) => r.data),
    pending: results.some((r) => r.isPending),
  }),
})

// Dependent: the second query waits for the first
const user = useQuery(userQueries.me())
const projects = useQuery({
  queryKey: ['projects', user.data?.id],
  queryFn: user.data ? ({ signal }) => api<Project[]>(`/users/${user.data.id}/projects`, { signal }) : skipToken,
})
```

- `enabled: !!id` also works. `skipToken` is the type-safe alternative: the `queryFn` type does not need a non-null assertion. Neither is allowed in `useSuspenseQuery` (it rejects `enabled` and `skipToken` at the type level); render the dependent component only once the parent data exists, or nest it below a Suspense boundary.
- A disabled query has `status: 'pending'` and `fetchStatus: 'idle'`; `isLoading` is `false`. Use `isPending` plus `fetchStatus` if the distinction matters.
- Several independent `useSuspenseQuery` calls in one component run sequentially (each suspends in turn). Use `useSuspenseQueries` or prefetch in the route to avoid a waterfall.
- `placeholderData: keepPreviousData` (imported from the package) keeps the old page visible while a new page key loads; it replaces the v4 `keepPreviousData` flag.

## 6. Cancellation with AbortSignal

Every `queryFn` receives `{ signal }`. Pass it to `fetch` (or any client that accepts an `AbortSignal`). If the signal is consumed, TanStack Query aborts the request when the query becomes inactive or is cancelled; if it is not consumed, the request continues and its result is cached when it resolves.

```ts
const q = useQuery({
  queryKey: ['search', term],
  queryFn: ({ signal }) => api<Hit[]>(`/search?q=${encodeURIComponent(term)}`, { signal }),
  enabled: term.length > 1,
})
// manual: queryClient.cancelQueries({ queryKey: ['search'] })
```

- `cancelQueries` before an optimistic cache write prevents an in-flight refetch from overwriting it.
- Debounce the input, not the query: derive `term` from a debounced value so keys do not churn.
- Always `encodeURIComponent` user text placed in URLs; send structured filters as query params or a POST body.

## 7. Prefetching and imperative fetches

- `queryClient.prefetchQuery(opts)` warms the cache (for hover, route loaders). In 5.105 the type definitions mark `fetchQuery`, `prefetchQuery`, `ensureQueryData`, `fetchInfiniteQuery`, `prefetchInfiniteQuery` and `ensureInfiniteQueryData` as deprecated in favour of `queryClient.query(opts)` and `queryClient.infiniteQuery(opts)`; they still work in 5.x. Check the current docs before choosing.
- `queryClient.query(opts)` returns a promise of the data, resolves from the cache when the data is fresh (honouring `staleTime`), and rejects on error. Unlike observers it does not retry unless `retry` is set. Use `.catch(noop)` when you only want to warm the cache.
- `queryClient.query({ ...opts, staleTime: 'static' })` replaces `ensureQueryData` (return cached data, fetch only if absent).
- Route loaders: await the critical queries and start the rest without `await`; then the component calls `useSuspenseQuery` or `useQuery` and finds the data already in the cache.

## 8. Suspense and error boundaries

```tsx
import { QueryErrorResetBoundary, useSuspenseQuery } from '@tanstack/react-query'
import { Suspense } from 'react'
import { ErrorBoundary } from 'react-error-boundary'

function Detail({ id }: { id: number }) {
  const { data } = useSuspenseQuery(todoQueries.detail(id)) // data is never undefined
  return <h1>{data.title}</h1>
}

export function Screen({ id }: { id: number }) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary onReset={reset} fallbackRender={({ resetErrorBoundary }) => (
          <button onClick={resetErrorBoundary}>Retry</button>
        )}>
          <Suspense fallback={<p>Loading</p>}>
            <Detail id={id} />
          </Suspense>
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  )
}
```

- `useSuspenseQuery`, `useSuspenseInfiniteQuery` and `useSuspenseQueries` guarantee defined `data`. They omit `enabled`, `throwOnError` and `placeholderData`.
- Suspense hooks throw errors to the nearest boundary only when the query has no data; a background refetch error on already-cached data does not unmount the UI (the documented default is `throwOnError: (error, query) => typeof query.state.data === 'undefined'`).
- With `useQuery`, opt in per query: `throwOnError: true` or a predicate such as `(error) => error.status >= 500`. Mutations accept `throwOnError` too.
- `react-error-boundary` is a separate package; any error boundary component works. Wrap the Suspense boundary, not the other way around, and reset the query error state with `QueryErrorResetBoundary` so a retry refetches.
- Transitions: updating a key inside `startTransition` keeps the old UI while the new suspending query loads.

## 9. TypeScript registration

```ts
import '@tanstack/react-query'

declare module '@tanstack/react-query' {
  interface Register {
    defaultError: unknown // call sites must narrow; the default is Error
    queryMeta: { errorMessage?: string }
    mutationMeta: { errorMessage?: string }
  }
}
```

- `Register` also accepts `queryKey` and `mutationKey` types (must extend `Array`) to enforce key structure across the app.
- Rely on inference from `queryFn` and `queryOptions`; avoid passing generics by hand. If you need a type for the data, use `ReturnType`/`Awaited` on the `queryFn` or `Todo[]` as the function return type.
- `data` for `useQuery` is `T | undefined`; do not widen with `as T`. Use `useSuspenseQuery`, an `if (!data)` guard, or `select`.
- `fetch` does not reject on HTTP errors: throw inside the `queryFn` (as `api` does above) or the error state never happens.
- Validate untrusted JSON at the boundary (a schema library in the `queryFn`) rather than asserting `as T` for external APIs.

## 10. ESLint plugin and devtools

`@tanstack/eslint-plugin-query` (5.105.0) ships flat-config presets `flat/recommended` and `flat/recommended-strict`. Rules present in the package: `exhaustive-deps`, `stable-query-client`, `no-rest-destructuring`, `no-unstable-deps`, `infinite-query-property-order`, `mutation-property-order`, `no-void-query-fn`.

```js
// eslint.config.js
import pluginQuery from '@tanstack/eslint-plugin-query'

export default [...pluginQuery.configs['flat/recommended']]
```

- `exhaustive-deps` finds `queryFn` variables missing from the key; `stable-query-client` flags `new QueryClient()` created inside a component body; the property-order rules keep `onMutate` before `onError`/`onSettled` so inference of the context type works.
- Devtools: `import { ReactQueryDevtools } from '@tanstack/react-query-devtools'` and render `<ReactQueryDevtools initialIsOpen={false} />` inside the `QueryClientProvider`. The default export is intended for development and is dropped from production builds; the package also exposes a `/production` entry for lazy-loading it deliberately.
- Devtools show keys and cached data; do not enable the production build for end users.

## 11. Other framework adapters

The core (`@tanstack/query-core`) is shared. Adapter packages at the time of writing: `@tanstack/vue-query` 5.105.0, `@tanstack/solid-query` 5.105.0, `@tanstack/angular-query-experimental` 5.105.0 and `@tanstack/svelte-query` 6.3.6 (a different major from the React one; read its migration notes). Concepts (keys, `staleTime`, invalidation, optimistic updates) transfer; hook names, reactivity (getters, refs, signals, stores) and SSR guidance differ, so use each adapter's own docs. For Vue and Svelte projects, prefer the vue-expert and svelte-expert skills for framework details.
