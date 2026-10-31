# Zustand

Client state with Zustand v5: `create`, selectors and `useShallow`, TypeScript usage, middleware order (devtools, persist, subscribeWithSelector, immer), slices, vanilla stores with `createStore` and `useStore`, per-request stores for SSR, testing and resetting, and what not to store. The code blocks type-checked against zustand 5.0.16, immer 11.2.9 and React 19 types (2026-10).

## Contents

1. [Creating a store](#1-creating-a-store)
2. [Selectors and rerenders](#2-selectors-and-rerenders)
3. [TypeScript usage](#3-typescript-usage)
4. [Middleware](#4-middleware)
5. [Slices pattern](#5-slices-pattern)
6. [Vanilla stores and per-request stores](#6-vanilla-stores-and-per-request-stores)
7. [Persist details](#7-persist-details)
8. [Testing and resetting](#8-testing-and-resetting)
9. [What not to put in Zustand](#9-what-not-to-put-in-zustand)
10. [Migrating from v4](#10-migrating-from-v4)

## 1. Creating a store

```ts
import { create } from 'zustand'

interface BearState {
  bears: number
  addBear: () => void
  reset: () => void
}

export const useBearStore = create<BearState>()((set) => ({
  bears: 0,
  addBear: () => set((s) => ({ bears: s.bears + 1 })),
  reset: () => set({ bears: 0 }),
}))
```

- `set` merges the returned object shallowly into state; `set(partial, true)` replaces the whole state. `get()` reads current state inside actions.
- Actions live in the store next to the data. Components select what they need; there are no providers for a module-level store.
- Outside React: `useBearStore.getState()`, `useBearStore.setState(...)`, `useBearStore.subscribe(listener)`. Use these in event handlers, timers and tests, never during render.
- Do not mutate state objects in place with plain `set`; return new objects (or use the immer middleware).

## 2. Selectors and rerenders

A component rerenders when its selector's result changes by `Object.is`. Selecting the whole store (`useBearStore()`) rerenders on every change.

```tsx
import { useShallow } from 'zustand/shallow'

const bears = useBearStore((s) => s.bears) // primitive: fine
const addBear = useBearStore((s) => s.addBear) // function reference is stable

// object or array result: wrap in useShallow so equal contents give a stable reference
const { bears: b, fish } = useBoundStore(useShallow((s) => ({ bears: s.bears, fish: s.fish })))
const [x, y] = useBoundStore(useShallow((s) => [s.x, s.y]))
```

- In v5 a selector that returns a new object or array on every call (`(s) => ({ ... })`, `(s) => s.items.filter(...)`, `(s) => s.value ?? []`) can cause the error "Maximum update depth exceeded". Fix by `useShallow`, by selecting the raw field and deriving with `useMemo`, or by returning a module-level constant for fallbacks.
- Select the smallest slice; derive inside the component or in a selector that returns a primitive (`(s) => s.items.length`).
- Selectors of parameters: `useStore((s) => s.byId[id])` is fine; keep the function inline or in `useCallback` only if it is expensive.
- Multiple stores are fine. Prefer several small stores (cart, ui, session) over one global object when slices have different lifetimes.

## 3. TypeScript usage

- Use the curried form `create<State>()(...)`. The extra `()` lets TypeScript infer middleware types while you supply `State` explicitly.
- Put actions in the state interface; keep state and actions in one type so selectors see both.
- With middleware, the order of generic mutators matters; letting middleware wrap the creator (as below) keeps inference working. Annotate slice creators with `StateCreator<Full, Mutators, [], Slice>`.
- Derive hook types: `type Store = ReturnType<typeof useBearStore.getState>`.
- `store.getInitialState()` returns the initial state object (v4.5+); used for resets.

## 4. Middleware

Order from outside in: `devtools` outermost, then `persist`, then `subscribeWithSelector`, then `immer`, then your creator. Each middleware wraps the one inside.

```ts
import { create } from 'zustand'
import { createJSONStorage, devtools, persist, subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface CartState {
  items: { id: string; qty: number }[]
  add: (id: string) => void
  clear: () => void
}

export const useCart = create<CartState>()(
  devtools(
    persist(
      subscribeWithSelector(
        immer((set) => ({
          items: [],
          add: (id) =>
            set((s) => {
              const line = s.items.find((i) => i.id === id)
              if (line) line.qty += 1
              else s.items.push({ id, qty: 1 })
            }),
          clear: () => set({ items: [] }),
        })),
      ),
      {
        name: 'cart',
        version: 1,
        storage: createJSONStorage(() => localStorage),
        partialize: (s) => ({ items: s.items }),
      },
    ),
    { name: 'CartStore', enabled: process.env.NODE_ENV !== 'production' },
  ),
)

// subscribeWithSelector: listen to one field with previous value
useCart.subscribe(
  (s) => s.items.length,
  (len, prev) => console.log('cart size', prev, '->', len),
)
```

- `immer` needs the `immer` package installed (peer dependency, `>=9.0.6`); inside `set` you can mutate the draft. Without immer keep updates immutable.
- `devtools` connects to the Redux DevTools extension; pass an action name as the third argument to `set` for readable traces (`set(fn, undefined, 'cart/add')`). Disable it in production builds.
- `subscribeWithSelector` adds the `subscribe(selector, listener, { equalityFn, fireImmediately })` overload. Use it for side effects outside React (analytics, syncing to another system).
- Import middleware from `zustand/middleware` and immer from `zustand/middleware/immer`.

## 5. Slices pattern

Split a large store into slice creators and combine them. Each slice sees the full store type.

```ts
import { create, type StateCreator } from 'zustand'

interface BearSlice { bears: number; addBear: () => void }
interface FishSlice { fish: number; addFish: () => void }
type Store = BearSlice & FishSlice

const createBearSlice: StateCreator<Store, [], [], BearSlice> = (set) => ({
  bears: 0,
  addBear: () => set((s) => ({ bears: s.bears + 1 })),
})
const createFishSlice: StateCreator<Store, [], [], FishSlice> = (set) => ({
  fish: 0,
  addFish: () => set((s) => ({ fish: s.fish + 1 })),
})

export const useStore = create<Store>()((...a) => ({
  ...createBearSlice(...a),
  ...createFishSlice(...a),
}))
```

- With middleware on the combined store, replace the `[]` mutator tuples in `StateCreator` with the middleware's mutators (for example `[['zustand/devtools', never]]`), or apply middleware once at the combine step. Check the TypeScript guide for the exact tuple.
- Slices that need each other call `get()` for the other slice's data; avoid circular knowledge by passing values as arguments.

## 6. Vanilla stores and per-request stores

`createStore` (from `zustand` or `zustand/vanilla`) builds a store with no React binding; `useStore(store, selector)` binds it. This is the basis for context-scoped and per-request stores.

```tsx
'use client'
import { createContext, useContext, useState, type ReactNode } from 'react'
import { createStore, useStore } from 'zustand'

type Counter = { count: number; inc: () => void }

export const createCounterStore = (init: Partial<Counter> = {}) =>
  createStore<Counter>()((set) => ({
    count: 0,
    inc: () => set((s) => ({ count: s.count + 1 })),
    ...init,
  }))

type CounterApi = ReturnType<typeof createCounterStore>
const CounterContext = createContext<CounterApi | null>(null)

export function CounterProvider({ children, initial }: { children: ReactNode; initial?: Partial<Counter> }) {
  const [store] = useState(() => createCounterStore(initial)) // one store per provider instance
  return <CounterContext.Provider value={store}>{children}</CounterContext.Provider>
}

export function useCounter<T>(selector: (s: Counter) => T): T {
  const store = useContext(CounterContext)
  if (!store) throw new Error('useCounter must be used inside CounterProvider')
  return useStore(store, selector)
}
```

- Use this pattern when the store holds per-request or per-subtree data: Next.js (server and client render the same initial props, no cross-request sharing), component libraries with multiple instances, and tests that want a fresh store.
- The official Next.js guide recommends no module-level global stores for SSR and no store access from Server Components. Server Components can pass fetched values to the provider's `initial` prop.
- The Next.js guide example declares `CounterStore = CounterState | CounterActions`; use an intersection (`&`) as above.
- For purely client-side apps (Vite SPA) a module-level `create` store is simpler and correct.

## 7. Persist details

- `name` is the storage key. `storage` defaults to `createJSONStorage(() => localStorage)`; pass `sessionStorage`, IndexedDB wrappers or React Native `AsyncStorage` the same way.
- `partialize` selects what is saved. Never persist functions (they are dropped anyway), tokens, or sensitive personal data: storage is readable by any script on the origin.
- `version` and `migrate(persisted, version)` handle shape changes; without `migrate`, a version mismatch discards the stored state.
- `merge` customizes how persisted and current state combine (the default is a shallow merge, which overwrites nested objects).
- Hydration: in SSR apps the server render has no storage, so the first client render can differ. Either set `skipHydration: true` and call `useStore.persist.rehydrate()` in an effect, or gate UI with `useStore.persist.hasHydrated()` / `onRehydrateStorage`. Other API: `persist.clearStorage()`, `persist.getOptions()`, `persist.setOptions()`.
- Since v5 the middleware no longer writes the initial state to storage at store creation; it writes after the first `set`.

## 8. Testing and resetting

```ts
import { beforeEach, expect, test } from 'vitest'
import { useCart } from './cart'

beforeEach(() => {
  useCart.setState(useCart.getInitialState(), true) // replace=true resets to initial state
})

test('adds a line', () => {
  useCart.getState().add('sku-1')
  expect(useCart.getState().items).toEqual([{ id: 'sku-1', qty: 1 }])
})
```

- Module-level stores persist between tests in one file; reset in `beforeEach`. For many stores, the official testing guide mocks the `zustand` module (`__mocks__/zustand.ts`) to register every created store and reset them all after each test; for Vitest the `__mocks__` folder must sit next to the configured root.
- Wrap React updates in `act()` when asserting rendered output after calling store actions outside event handlers.
- Test with `persist`: stub `localStorage` (jsdom provides it), clear it in `beforeEach`, and call `persist.rehydrate()` when you need to observe hydration.
- Context-scoped stores (section 6) need no reset: render a new provider per test.
- Test pure logic by exporting the slice creators or the `createStore` factory and calling `getState()` directly, without React.

## 9. What not to put in Zustand

- Server data (lists, entities, search results) with loading and error flags. Zustand has no cache, deduplication, retry, invalidation or staleness; reimplementing them is the usual source of bugs. Use TanStack Query and keep only client concerns (selected id, open panels, draft input, wizard step) in Zustand.
- URL state (filters, pagination, tabs that should be shareable): keep it in the router's search params.
- Form field state: keep it in a form library or local state; push to a store only on submit or when other screens need it.
- Derived values: compute in selectors or `useMemo`.
- If you must combine, store ids in Zustand and read entities from the query cache: `useQuery(todoQueries.detail(selectedId))`.

## 10. Migrating from v4

- No default exports: `import { create } from 'zustand'`.
- `create` no longer takes an equality function. Use `useShallow`, or `createWithEqualityFn` from `zustand/traditional` (needs the `use-sync-external-store` package).
- Selectors must return stable references (section 2).
- Minimum React 18 and TypeScript 4.5; the `persist` initial-state write was removed.
- Deprecated v4 features are gone. Upgrade to the latest v4 first to see the warnings.
