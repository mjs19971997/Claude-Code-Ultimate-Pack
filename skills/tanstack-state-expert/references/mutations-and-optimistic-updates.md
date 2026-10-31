# Mutations and Optimistic Updates

Writing data with `useMutation` in `@tanstack/react-query` v5: lifecycle callbacks, invalidation, the two optimistic-update styles (UI via `variables`, cache via `onMutate` with rollback), mutation scopes, retries and offline behaviour. Callback signatures were checked against the 5.105.0 type definitions and the code type-checked with TypeScript 6.0.3 (2026-10).

## Contents

1. [Mutation basics](#1-mutation-basics)
2. [Invalidate or write to the cache](#2-invalidate-or-write-to-the-cache)
3. [Optimistic update via the UI](#3-optimistic-update-via-the-ui)
4. [Optimistic update via the cache with rollback](#4-optimistic-update-via-the-cache-with-rollback)
5. [Scopes, ordering and retries](#5-scopes-ordering-and-retries)
6. [Errors and user feedback](#6-errors-and-user-feedback)
7. [Server Actions and forms](#7-server-actions-and-forms)

## 1. Mutation basics

```ts
import { mutationOptions, useMutation, useQueryClient } from '@tanstack/react-query'

type Todo = { id: number; title: string; done: boolean }

export const updateTodoMutation = () =>
  mutationOptions({
    mutationKey: ['updateTodo'],
    mutationFn: (t: Todo) =>
      api<Todo>(`/todos/${t.id}`, { method: 'PUT', body: JSON.stringify(t), headers: { 'content-type': 'application/json' } }),
  })

// const m = useMutation(updateTodoMutation())
// m.mutate(todo)            // fire and forget; callbacks passed here run only if the component is still mounted
// await m.mutateAsync(todo) // promise; remember try/catch
```

- Status: `idle`, `pending`, `error`, `success` (`isPending`, `isError`, `isSuccess`); `variables` holds the last argument and survives an error, which makes retry buttons easy: `m.mutate(m.variables)`.
- `mutate(vars, { onSuccess })` callbacks are per call and are skipped if the component unmounted; `useMutation({ onSuccess })` callbacks always run. Put cache work in the hook-level callbacks.
- The callback order is `onMutate`, then `mutationFn`, then `onSuccess` or `onError`, then `onSettled`. A returned promise is awaited, so the mutation stays `pending` until it settles.
- In current 5.x the callbacks receive a context object as the last argument with the `QueryClient` on `context.client`: `onMutate(variables, context)`, `onSuccess(data, variables, onMutateResult, context)`, `onError(error, variables, onMutateResult, context)`, `onSettled(data, error, variables, onMutateResult, context)`. The value returned by `onMutate` is the `onMutateResult`. Using `context.client` lets you define mutation options outside components without capturing a client. If your installed version has the older signature (no context), use `useQueryClient()`; check the type definitions.
- `mutationOptions()` gives inference when mutation options live in a separate module, like `queryOptions`.

## 2. Invalidate or write to the cache

After a successful write, either invalidate, or write the response into the cache and then invalidate what you cannot patch:

```ts
const qc = useQueryClient()

useMutation({
  mutationFn: createTodo,
  // 1. Invalidate: mark stale and refetch active queries. Return the promise so the mutation stays pending until fresh data arrives.
  onSuccess: () => qc.invalidateQueries({ queryKey: todoKeys.lists() }),
})

useMutation({
  mutationFn: updateTodo,
  // 2. Write the server response straight into the detail cache (no extra request), and invalidate lists
  onSuccess: (saved) => {
    qc.setQueryData(todoKeys.detail(saved.id), saved)
    return qc.invalidateQueries({ queryKey: todoKeys.lists() })
  },
})
```

- `invalidateQueries` refetches active queries immediately and only marks inactive ones stale (`refetchType` controls this). A prefix key invalidates all matching keys.
- `setQueryData` with an updater must return a new value and treat the old one as immutable (no `push`, no field assignment). Returning `undefined` from the updater leaves the cache unchanged.
- Plain invalidation with no optimistic step is the least code and cannot drift; prefer it unless the latency is visible.
- Write the response into the cache only when the endpoint returns the full entity in the same shape the query uses.

## 3. Optimistic update via the UI

Simplest and safest: render the pending mutation's `variables` next to the real data. No cache writes, no rollback.

```tsx
const add = useMutation({
  mutationFn: (title: string) => api<Todo>('/todos', { method: 'POST', body: JSON.stringify({ title }) }),
  onSettled: () => qc.invalidateQueries({ queryKey: todoKeys.lists() }), // returned, so isPending covers the refetch
})

<ul>
  {todos.data?.map((t) => <li key={t.id}>{t.title}</li>)}
  {add.isPending && <li style={{ opacity: 0.5 }}>{add.variables}</li>}
  {add.isError && <li>{add.variables} <button onClick={() => add.mutate(add.variables)}>Retry</button></li>}
</ul>
```

When the mutation and the list live in different components, give the mutation a `mutationKey` and read it elsewhere:

```ts
import { useMutationState } from '@tanstack/react-query'

const pendingTitles = useMutationState({
  filters: { mutationKey: ['addTodo'], status: 'pending' },
  select: (m) => m.state.variables as string,
})
```

- The result is an array because several mutations can be pending; use `m.state.submittedAt` as a key when you need unique React keys.
- Choose this style when one place shows the optimistic state. Choose the cache style when several screens must reflect the change.

## 4. Optimistic update via the cache with rollback

```ts
useMutation({
  mutationFn: updateTodo,
  onMutate: async (next, context) => {
    // 1. stop in-flight refetches from overwriting the optimistic value
    await context.client.cancelQueries({ queryKey: todoKeys.detail(next.id) })
    // 2. snapshot
    const previous = context.client.getQueryData(todoKeys.detail(next.id))
    // 3. write
    context.client.setQueryData(todoKeys.detail(next.id), next)
    // 4. hand the snapshot to onError/onSettled
    return { previous }
  },
  onError: (_err, next, result, context) => {
    if (result) context.client.setQueryData(todoKeys.detail(next.id), result.previous)
  },
  onSettled: (_data, _err, next, _result, context) =>
    context.client.invalidateQueries({ queryKey: todoKeys.detail(next.id) }),
})
```

Checklist for correct cache-style updates:

- Always `cancelQueries` first, snapshot second, write third.
- Always invalidate in `onSettled` (success or error) so the cache converges on server truth even if the rollback is imperfect.
- Update every cache entry that shows the item: the detail entry, plus lists via `qc.setQueriesData({ queryKey: todoKeys.lists() }, (old) => old?.map((t) => (t.id === next.id ? next : t)))`. Snapshot them with `qc.getQueriesData({ queryKey: todoKeys.lists() })` and restore each pair on error.
- Concurrent mutations on the same entity: a rollback to an older snapshot can erase a later optimistic change. Serialize them with a `scope` (next section), or skip the rollback and rely on the final invalidation when only the last write matters.
- Infinite queries store `{ pages, pageParams }`; map over `pages` when patching.
- For new items, generate a temporary client id (`crypto.randomUUID()`) and replace it with the server id on success; never use the temporary id in a request path.

## 5. Scopes, ordering and retries

```ts
useMutation({
  mutationFn: saveDraft,
  scope: { id: 'draft-42' }, // mutations with the same scope id run one after another
})
```

- By default mutations run in parallel, even when `mutate` is called repeatedly. A `scope` queues them: later ones start in `isPaused` state and resume in order.
- Mutations do not retry by default. Retry only idempotent operations (`retry: 3`), and send an idempotency key for non-idempotent POSTs so a retry cannot create duplicates.
- `networkMode` defaults to `'online'`: offline mutations pause and resume when the connection returns. Persisting paused mutations across reloads needs `setMutationDefaults` for each `mutationKey` plus the persist client (see the persister docs) because functions cannot be serialized.

## 6. Errors and user feedback

- Surface failures globally with a cache-level handler instead of repeating `onError` in every hook:

```ts
import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'

export const client = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.state.data !== undefined) toast(`Background refresh failed: ${error.message}`)
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _vars, _result, mutation) => {
      if (mutation.meta?.errorMessage) toast(String(mutation.meta.errorMessage))
    },
  }),
})
```

- `meta` (typed through `Register`) carries per-mutation flags such as a user-facing message.
- Do not show raw server error bodies to users; map status codes to messages.
- Form validation errors (422) belong in the form state; keep them out of the global handler.
- `throwOnError: true` on a mutation sends the error to an error boundary; use it only for failures with no local recovery.

## 7. Server Actions and forms

- In Next.js, a Server Action is a good `mutationFn` (call it, do not pass the reference through other APIs), but do not use Server Actions as `queryFn`: client-called actions run one at a time, which conflicts with parallel fetching.
- Server Actions are public HTTP endpoints. Authenticate, authorize and validate their input inside the action regardless of the client's optimistic logic.
- React 19's `useActionState` and `useOptimistic` solve form-local pending and optimistic state without a cache (use senior-react-19-engineer for those). Reach for TanStack mutations when the result must update shared cached data or be retried, scoped or observed elsewhere.
- Form libraries (React Hook Form, TanStack Form) own field state; call `mutate` from their submit handler and reset the form in `onSuccess`.
