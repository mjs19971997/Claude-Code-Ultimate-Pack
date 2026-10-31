---
name: tanstack-state-expert
description: >-
  Designs and reviews client and server state in React apps with TanStack Query v5 and Zustand v5: query keys, queryOptions, mutations and optimistic updates, infinite and dependent queries, SSR hydration, selectors, middleware and slices. Use when editing code that imports @tanstack/react-query or zustand, QueryClient defaults, useQuery, useMutation, HydrationBoundary, create or createStore, or when deciding between server, client, URL and form state. Not for React itself (use senior-react-19-engineer), Next.js caching and Server Components (use nextjs-15-architect), Svelte (use svelte-expert), Vue and Pinia (use vue-expert), or API design (use rest-api-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# TanStack State Expert

This skill covers the split between server state (data owned by a backend, cached and synchronised by TanStack Query) and client state (UI-only state, held in React or Zustand). It includes QueryClient configuration, key design, reads and writes, optimistic updates, server rendering and hydration, Zustand stores and middleware, TypeScript usage, testing, and the rules for choosing where each piece of state lives. TanStack Router and Table appear only as pointers.

> Verified against @tanstack/react-query 5.105.0 (with query-core, devtools, eslint-plugin-query, persist and next-experimental packages at 5.105.0), zustand 5.0.16, immer 11.2.9, React 19.3 and TypeScript 6.0.3 type checks, plus the TanStack Query and zustand documentation on GitHub (2026-10).

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

- Covered: `@tanstack/react-query` v5 (QueryClient, `useQuery`, `useSuspenseQuery`, `useInfiniteQuery`, `useQueries`, `useMutation`, `queryOptions`, cache APIs, prefetching, hydration, devtools, persisters, ESLint plugin), Zustand v5 (`create`, `createStore`, `useStore`, selectors, `useShallow`, middleware, slices), TypeScript patterns for both, testing, and state-placement decisions (server, client, URL, form).
- Brief notes only: the Vue, Solid, Angular and Svelte adapters of TanStack Query; TanStack Router (typed routes, search-param validation, loaders that call `queryClient`) and TanStack Table (headless tables); other client-state libraries (Jotai, Redux Toolkit, Valtio) are not covered.
- Not covered: React rendering, hooks, Suspense and `use` internals (senior-react-19-engineer); Next.js route caching, Server Components and Server Actions in depth (nextjs-15-architect); Svelte stores and runes (svelte-expert); Vue and Pinia (vue-expert); HTTP API and pagination design on the server (rest-api-expert, graphql-expert); end-to-end browser tests (playwright-expert, e2e-testing-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Cache model | Queries are cached by hashed key. `staleTime` (default 0) decides freshness; `gcTime` (default 5 minutes) decides how long unused data is kept. Stale data refetches on new mount, window focus and reconnect |
| v5 API shape | One object argument for every hook. `isPending` replaces v4 `isLoading`; `gcTime` replaces `cacheTime`; `throwOnError` replaces `useErrorBoundary`; `useQuery` has no `onSuccess`/`onError`; `initialPageParam` is required for infinite queries; React 18 or newer is required |
| Imperative fetching | In 5.105 `queryClient.query()` and `queryClient.infiniteQuery()` are the preferred fetchers; `fetchQuery`, `prefetchQuery`, `ensureQueryData` and the infinite variants are marked deprecated in the types and still work in 5.x |
| Mutation callbacks | In 5.105 callbacks receive a context as the last argument: `onMutate(variables, context)`, `onError(error, variables, onMutateResult, context)`, with `context.client` as the `QueryClient` |
| SSR | New `QueryClient` per request on the server, one singleton in the browser, default `staleTime` above 0, `dehydrate` plus `HydrationBoundary`. Detect the server with `environmentManager.isServer()` (the old `isServer` export is deprecated) |
| Suspense | `useSuspenseQuery` returns defined `data`; it rejects `enabled`, `skipToken`, `throwOnError` and `placeholderData`. Pair with `<Suspense>` and an error boundary |
| Zustand v5 | Curried `create<T>()(...)`; no default exports; `create` takes no equality function; selectors must return stable references (use `useShallow` for objects and arrays); `persist` no longer writes initial state on creation |
| Middleware | `devtools`, `persist`, `subscribeWithSelector` from `zustand/middleware`; `immer` from `zustand/middleware/immer` (needs the `immer` package) |
| Tooling | `@tanstack/eslint-plugin-query` flat presets `flat/recommended` and `flat/recommended-strict`; `@tanstack/react-query-devtools` |
| Peer ranges | react-query: React `^18 || ^19`; zustand: React `>=18`; immer `>=9.0.6` for the immer middleware |

## 3. Workflow

1. Classify each piece of state with the decision rules in section 4 before choosing a tool. Most "global state" is server state.
2. Inspect the project: package versions (`npm ls @tanstack/react-query zustand`), existing key conventions, the `QueryClient` location, SSR framework, and whether the ESLint plugin is installed.
3. Define keys and options first: a key factory plus `queryOptions` per resource, then hooks that spread those options.
4. Write reads, then writes: set `staleTime` deliberately, pass `signal` to `fetch`, throw on non-2xx responses, and decide per mutation between invalidation, cache write and optimistic update.
5. For server rendering, create the per-request client factory and provider before adding prefetches; verify there is no second fetch on the client.
6. Add client state to Zustand only for UI concerns; start with one small store and typed selectors.
7. Verify: type check, ESLint with the query plugin, tests with a fresh `QueryClient` per test and reset stores, and a manual check in the devtools (fetch counts, stale state, key shapes).

## 4. Decision Rules

Where state lives:

| State | Home | Why |
|---|---|---|
| Data from an API (lists, entities, search results, permissions) | TanStack Query | Caching, dedupe, retry, invalidation, background refresh |
| Shareable view state (filters, sort, page, selected tab, open modal that should survive reload) | URL (router search params) | Linkable, back button works, SSR-friendly |
| Form field values and validation | Local state or a form library | Short-lived, per form; submit through a mutation |
| UI state in one component | `useState` or `useReducer` | No sharing needed |
| UI state shared by distant components (sidebar, theme, wizard step, draft cart) | Zustand or context | Needs a store, not a cache |
| Derived data | Computed in render, `select`, or selectors | Storing it duplicates truth |

Rules:

- If the data has an owner on a server, use TanStack Query; if you are writing `isLoading`, `error` and `data` into a Zustand store, stop and move it to a query.
- If a value must survive reload or be shared as a link, put it in the URL; if it must survive reload but not be shared, use Zustand `persist` or local storage.
- If two components read the same server entity, give them the same key through `queryOptions`; do not pass the data through props or a store.
- If the data changes rarely (reference data), raise `staleTime` (minutes, or `'static'` for data that cannot change during the session); if it changes often or is user-visible, keep the default and use `refetchInterval` only when polling is intended.
- If the user must see the result of a write immediately: one screen shows it, use the optimistic `variables` approach; several screens show it, use `onMutate` with cache writes and rollback; otherwise invalidate on `onSettled` and wait.
- If the list is paginated by page number and users jump around, use a normal query with the page in the key and `placeholderData: keepPreviousData`; if it is a feed, use `useInfiniteQuery` with a cursor.
- If a component can render only with data and a Suspense boundary exists above it, use `useSuspenseQuery`; if the query may be disabled or needs a placeholder, use `useQuery` with `enabled` or `skipToken`.
- If a query depends on another query's result, use `enabled` or `skipToken`; if the dependency is only the route parameter, prefetch both in the loader so they run in parallel.
- If errors should reset the UI, use an error boundary with `QueryErrorResetBoundary`; if errors only need a toast, handle them in `QueryCache`/`MutationCache` `onError`.
- If the app is server-rendered, create the client per request and prefetch in the server component or loader; if it is a single-page app, a module-level client is enough.
- If a Zustand store is read by SSR-rendered components with per-user data, create it per request with `createStore` and context; if it is a client-only SPA, a module-level `create` store is fine.
- If a selector returns a new object or array, wrap it in `useShallow`; if it returns a primitive or an existing reference, do not.
- If you only need server-cached data in a framework that already caches (Next.js Server Components with no client interactivity), use the framework; add TanStack Query when client-side mutations, polling or infinite lists are needed.
- If a table needs sorting, filtering and column logic, use TanStack Table (check the current major version and docs first); if routing needs typed search params and loaders, evaluate TanStack Router. Both are optional.

## 5. Coding Standards

- Keys are arrays of serializable values, built only by key factories: `['todos', 'list', filters] as const`. Everything the `queryFn` reads belongs in the key.
- Define `queryOptions` per resource in one module and spread them into hooks, prefetches and cache writes. Do not repeat key and `queryFn` pairs inline.
- `queryFn` takes `{ signal }` and forwards it to `fetch`. A wrapper must throw on non-2xx responses (`fetch` does not reject on HTTP errors).
- Let TypeScript infer the data type from `queryFn`; avoid explicit generics and `as` casts on `data`. Register a global error type with `declare module '@tanstack/react-query' { interface Register { ... } }` when the app has one error shape.
- Mutations: return the `invalidateQueries` promise from the callback so the mutation stays pending until the cache is fresh. Keep cache work in hook-level callbacks, not only in `mutate(..., { onSuccess })`.
- Never mutate cached data in `setQueryData` updaters; return new values.
- Zustand: `create<State>()(...)` with actions in the state type; one selector per field or `useShallow` for several; no `useStore()` without a selector in components; no store reads during render outside hooks.
- Create `QueryClient` once (module scope, or the SSR factory); never inside a component body without memoization. The `stable-query-client` ESLint rule catches this.
- Name hooks after the domain (`useTodos`), not the library, and keep components free of key strings.

## 6. Project Structure

```text
src/
  lib/
    query-client.ts        # makeQueryClient / getQueryClient (SSR-safe), global defaults, cache-level onError
    api.ts                 # fetch wrapper: base URL, JSON, throws on non-2xx, passes signal
  features/todos/
    keys.ts                # todoKeys factory
    queries.ts             # todoQueries = { list, detail, infinite } using queryOptions
    mutations.ts           # mutationOptions (or hooks) with cache updates
    todo-list.tsx          # components use useQuery(todoQueries.list(...))
  stores/
    ui-store.ts            # Zustand: sidebar, theme, selection (client state only)
    cart-store.ts          # Zustand with persist + partialize
  app/                     # framework routing; providers.tsx holds QueryClientProvider and devtools
```

- Group by feature; keep keys, options and mutations together so invalidation targets are easy to find.
- One provider file wraps the app; stores that need context (SSR) get their own `*-provider.tsx`.
- Do not export the raw `QueryClient` to components; use `useQueryClient()` or `context.client` in mutation callbacks.

## 7. Design Patterns

- **Key factory**: hierarchical keys (`all > lists > list(filters)`, `details > detail(id)`) so invalidation by prefix is precise. See [references/tanstack-query-patterns.md](references/tanstack-query-patterns.md).
- **Options factory**: `queryOptions` and `infiniteQueryOptions` objects reused by hooks, loaders and `queryClient.query`.
- **Select for views**: `select` derives the shape a component needs without another request; structural sharing keeps unchanged results referentially equal.
- **Optimistic UI via variables**: render `mutation.variables` while pending; no cache writes. **Optimistic cache**: `cancelQueries`, snapshot, `setQueryData`, return the snapshot, roll back in `onError`, invalidate in `onSettled`. See [references/mutations-and-optimistic-updates.md](references/mutations-and-optimistic-updates.md).
- **Prefetch then hydrate**: server component prefetches with the shared options, `dehydrate`, `HydrationBoundary`; client hook reads the cache. See [references/ssr-hydration.md](references/ssr-hydration.md).
- **Slices**: split a large Zustand store into slice creators typed with `StateCreator` and combine them once. See [references/zustand.md](references/zustand.md).
- **Store per provider**: `createStore` in `useState`, context to share, `useStore(store, selector)` to read; use for SSR and for multi-instance components.
- **IDs in the store, entities in the cache**: Zustand holds `selectedId`; components read the entity with `useQuery(todoQueries.detail(selectedId))`.

## 8. Best Practices

- Set a global `staleTime` that matches your freshness needs (for example 30 to 60 seconds) instead of turning off `refetchOnWindowFocus` everywhere.
- Prefer `invalidateQueries` after writes; add optimistic updates only where latency is visible.
- Prefetch on intent (hover, route transition) with `queryClient.query(opts).catch(noop)` or `prefetchQuery` while it remains available.
- Treat `fetchStatus` and `status` as separate: `pending` with `idle` means disabled, not loading.
- Use `meta` and cache-level `onError` for toasts; keep components free of error plumbing.
- Keep Zustand stores small and feature-scoped; export hooks and selectors, not the raw store, when you want to control the API.
- Use `getState()` and `setState()` only outside render (handlers, tests, subscriptions).
- In Zustand, keep actions as stable functions in state (they are created once), so selecting them never causes rerenders.
- Upgrade in small steps and read the release notes first: `@tanstack/react-query` ships frequent minor releases that deprecate APIs before removal; zustand v5 has strict selector stability.

## 9. Performance

- Selecting whole stores or returning fresh objects from selectors is the main Zustand rerender cost; select primitives, or use `useShallow`.
- For Query, `select` with a stable function and structural sharing limit rerenders. Destructure only what the component uses (the `no-rest-destructuring` lint rule warns about tracked-prop pitfalls with rest spreads on query results).
- Avoid waterfalls: prefetch in loaders, fetch independent queries in parallel with `useQueries` or `useSuspenseQueries`, and do not nest dependent `useSuspenseQuery` calls when the keys are known up front.
- Infinite lists: `maxPages` bounds memory; virtualise long lists; remember that refetch reloads pages sequentially.
- Reduce payload: request only needed fields, paginate on the server, and avoid putting large responses into frequently re-rendered components.
- Raise `staleTime` for slow-changing data to cut requests; lower `gcTime` for memory-heavy queries (large lists, images as data).
- `structuralSharing: false` can help for very large responses where comparison cost dominates; measure first with the React profiler and devtools.
- For high-frequency updates (cursor position, drag), keep state in refs or local state, not in a store that many components subscribe to.

## 10. Security

- Never keep access tokens or secrets in query keys, Zustand `persist` storage, or dehydrated state. Keys show up in devtools and caches; storage is readable by any script on the origin.
- On the server, create a `QueryClient` and any Zustand store per request. Shared module-level instances can leak one user's data to another.
- Everything passed to `dehydrate` is serialized into the page. Prefetch only data the viewer is allowed to see, and do not cache HTML that contains user-specific dehydrated state.
- Include the user or tenant id in the keys of per-user data; call `queryClient.clear()` (and reset persisted stores) on logout or user switch.
- Persisted query caches and stores: use `partialize`/`shouldDehydrateQuery` to whitelist, set `maxAge` and a `buster`/`version`, and never persist PII without a reason.
- Optimistic updates are not authorization: the server must validate every mutation. Server Actions are public endpoints; authenticate, authorize and validate inside them.
- Encode user text placed in URLs (`encodeURIComponent`) and validate API responses at the boundary instead of trusting `as T`.
- Disable `devtools` middleware and the Query devtools in production builds shown to end users.

## 11. Testing

- Create a new `QueryClient` for every test with `retry: false` and wrap the component in a provider; shared clients leak cache between tests.
- Mock at the network layer (Mock Service Worker or a fetch mock) rather than mocking `useQuery`; assertions then cover keys, loading and error paths.
- Await states with `findBy*`/`waitFor`; for hooks, `renderHook` with the wrapper.
- Test optimistic updates by delaying the mocked response, asserting the optimistic UI, then rejecting it and asserting the rollback.
- Zustand: reset with `store.setState(store.getInitialState(), true)` in `beforeEach`, or mock the `zustand` module to reset all stores; context-scoped stores are fresh per provider.
- Wrap store updates triggered outside event handlers in `act()`.
- Assert fetch counts (a dedupe or hydration regression shows as an extra request).
- Run the ESLint query plugin in CI; it catches missing key dependencies and unstable clients.

Details and snippets: [references/zustand.md](references/zustand.md) section 8 and [references/tanstack-query-patterns.md](references/tanstack-query-patterns.md).

## 12. Review Checklist

- [ ] Every piece of state has a justified home (server cache, URL, form, local, Zustand); no server data in Zustand.
- [ ] Keys come from a factory, include every `queryFn` input, and contain no secrets.
- [ ] `queryOptions` are shared between components, loaders and prefetches.
- [ ] `queryFn` forwards `signal` and throws on non-2xx.
- [ ] `staleTime` is set deliberately; SSR default is above 0.
- [ ] Mutations invalidate or update every affected key; promises are returned from callbacks; optimistic updates cancel, snapshot, roll back and invalidate.
- [ ] No `QueryClient` created in render; server uses one client per request.
- [ ] Zustand selectors return primitives or are wrapped in `useShallow`; no `useStore()` without a selector.
- [ ] `persist` uses `partialize`, `version` and has an SSR hydration plan; nothing sensitive is stored.
- [ ] Suspense hooks sit below a `<Suspense>` and an error boundary.
- [ ] Tests use a fresh client with `retry: false` and reset stores.
- [ ] The ESLint query plugin passes; no deprecated v4 options (`cacheTime`, `isLoading` for first load, `onSuccess` on queries).

## 13. Production Notes

- Check `npm view @tanstack/react-query version` and the release notes before upgrading; minor releases in the 5.x line have deprecated APIs (for example the `fetchQuery` family in favour of `query`) while keeping them working until the next major.
- All `@tanstack/*` query packages (react-query, devtools, persist, eslint-plugin, next-experimental) should be on the same minor; the devtools and next-experimental packages peer-depend on `@tanstack/react-query ^5.105.0`.
- `@tanstack/svelte-query` is on a different major (6.x) from the React adapter (5.x); do not copy React upgrade notes across adapters.
- Add the devtools only in development, or load the production build lazily behind a flag for internal debugging.
- Observe production behaviour: global `QueryCache.onError` to your error reporter, request counts per route, and slow queries; watch for refetch storms after raising or removing `staleTime`.
- Offline and mobile: queries default to `networkMode: 'online'` and pause when offline; mutations pause and resume. Persist only if the product needs offline start, and set `buster` to invalidate on releases.
- Pin the Zustand major (v5) and review `persist` `version` and `migrate` whenever the stored shape changes; old clients keep old data in storage for a long time.
- Deleting a store field is a breaking change for persisted data; bump `version` and write a `migrate`.

## 14. Examples

Query options, a list query and an optimistic toggle with rollback (types checked against react-query 5.105.0):

```tsx
import { queryOptions, useMutation, useQuery } from '@tanstack/react-query'

type Todo = { id: number; title: string; done: boolean }

const todoKeys = {
  all: ['todos'] as const,
  lists: () => [...todoKeys.all, 'list'] as const,
  detail: (id: number) => [...todoKeys.all, 'detail', id] as const,
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

const todosList = () =>
  queryOptions({
    queryKey: todoKeys.lists(),
    queryFn: ({ signal }) => api<Todo[]>('/todos', { signal }),
    staleTime: 30_000,
  })

export function Todos() {
  const { data, isPending, error } = useQuery(todosList())

  const toggle = useMutation({
    mutationFn: (t: Todo) =>
      api<Todo>(`/todos/${t.id}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ ...t, done: !t.done }),
      }),
    onMutate: async (t, context) => {
      await context.client.cancelQueries({ queryKey: todoKeys.lists() })
      const previous = context.client.getQueryData(todosList().queryKey)
      context.client.setQueryData(todosList().queryKey, (old) =>
        old?.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)),
      )
      return { previous }
    },
    onError: (_err, _t, result, context) => {
      if (result?.previous) context.client.setQueryData(todosList().queryKey, result.previous)
    },
    onSettled: (_d, _e, _t, _r, context) =>
      context.client.invalidateQueries({ queryKey: todoKeys.lists() }),
  })

  if (isPending) return <p>Loading</p>
  if (error) return <p>Something went wrong</p>
  return (
    <ul>
      {data.map((t) => (
        <li key={t.id}>
          <label>
            <input type="checkbox" checked={t.done} onChange={() => toggle.mutate(t)} /> {t.title}
          </label>
        </li>
      ))}
    </ul>
  )
}
```

A Zustand store for UI state with persistence of one field, and a selector that avoids rerenders:

```tsx
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useShallow } from 'zustand/shallow'

interface UiState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  selectedTodoId: number | null
  toggleSidebar: () => void
  select: (id: number | null) => void
}

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      selectedTodoId: null,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      select: (id) => set({ selectedTodoId: id }),
    }),
    { name: 'ui', version: 1, partialize: (s) => ({ sidebarOpen: s.sidebarOpen, theme: s.theme }) },
  ),
)

export function Header() {
  const { sidebarOpen, toggleSidebar } = useUi(
    useShallow((s) => ({ sidebarOpen: s.sidebarOpen, toggleSidebar: s.toggleSidebar })),
  )
  return <button onClick={toggleSidebar}>{sidebarOpen ? 'Hide' : 'Show'}</button>
}
```

Server-rendered prefetch (per-request client, shared options): see [references/ssr-hydration.md](references/ssr-hydration.md) sections 2 to 4.

## 15. Common Mistakes

- Copying server responses into Zustand or `useState` in an effect: it duplicates the cache, loses invalidation and creates stale copies. Read from the query.
- Setting `staleTime: 0` (the default) in SSR apps: data is refetched immediately after hydration. Set a default above 0.
- Creating `new QueryClient()` in a component body or at module level on the server: cache resets on every render, or users share data.
- Missing a dependency in the key (`queryKey: ['todos']` with a filter in the `queryFn`): every filter shares one cache entry.
- Forgetting that `fetch` does not reject on 4xx and 5xx: the query succeeds with an error body. Throw in the wrapper.
- Using v4 names: `isLoading` for first load (use `isPending`), `cacheTime`, `keepPreviousData: true`, `useErrorBoundary`, query `onSuccess`. They are removed in v5.
- Combining `useSuspenseQuery` with `enabled` or `skipToken`: not allowed; restructure with a parent component.
- Optimistic update without `cancelQueries`: an in-flight refetch overwrites the optimistic value.
- Rolling back to a snapshot with several concurrent mutations on the same entity: use a `scope` or rely on final invalidation.
- Using `useBearStore()` with no selector, or a selector returning `{ a: s.a, b: s.b }`: needless rerenders, or in v5 a "Maximum update depth exceeded" loop. Use `useShallow`.
- Mutating state inside `set` without immer: subscribers do not see the change.
- Module-level Zustand store with per-user data in an SSR app: shared across requests. Use `createStore` per provider.
- Persisting the whole store (functions, tokens, derived data): use `partialize`, and plan versioning with `migrate`.
- Using Server Actions as `queryFn`: client-called actions run serially and can stall queries; use a route handler or API client.
- Rendering server-fetched query data in a Server Component and reading the same query in a client component: the two drift after a client refetch.

## 16. References

- [references/tanstack-query-patterns.md](references/tanstack-query-patterns.md): defaults, key factories, `queryOptions`, infinite queries, parallel and dependent queries, cancellation, prefetching, Suspense and error boundaries, TypeScript registration, ESLint plugin, devtools, adapters.
- [references/mutations-and-optimistic-updates.md](references/mutations-and-optimistic-updates.md): mutation lifecycle and context argument, invalidation versus cache writes, optimistic updates via variables and via the cache with rollback, scopes, retries, global error handling.
- [references/ssr-hydration.md](references/ssr-hydration.md): per-request clients, Next.js App Router providers, `dehydrate` and `HydrationBoundary`, streaming pending queries, serialization, persistence, Zustand with SSR, troubleshooting.
- [references/zustand.md](references/zustand.md): `create`, selectors and `useShallow`, TypeScript, middleware order, slices, vanilla and per-request stores, persist, testing and resets, what not to store, v4 to v5 notes.
- TanStack Query docs: https://tanstack.com/query/latest ; source and docs: https://github.com/TanStack/query
- Zustand docs: https://zustand.docs.pmnd.rs/ ; source: https://github.com/pmndrs/zustand
- TanStack Router: https://tanstack.com/router ; TanStack Table: https://tanstack.com/table (check the current major version before starting)
- TkDodo's blog (maintainer articles on Query patterns): https://tkdodo.eu/blog/
