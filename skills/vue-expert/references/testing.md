# Testing Vue with Vitest

Reference for component, composable, store, and router tests, plus type checking and linting. Verified against Vitest 5.0.5 (Node `^22.12.0 || ^24.0.0 || >=26.0.0`, Vite `^6.4 || ^7 || ^8`), Vue Test Utils 2.5.1, `@pinia/testing` 2.0.2 (requires `pinia >=4.1.0`), Vite 8.3.5 (Node `^20.19.0 || >=22.12.0`), `@vitejs/plugin-vue` 6.0.10, vue-tsc 3.3.14, eslint-plugin-vue 10.12.0 and ESLint 10.14 (2026-10). The examples below were executed against those versions.

## Contents

1. [Setup](#1-setup)
2. [Component tests](#2-component-tests)
3. [Pinia in tests](#3-pinia-in-tests)
4. [Router in tests](#4-router-in-tests)
5. [Composables, timers and mocks](#5-composables-timers-and-mocks)
6. [ESLint and type checking](#6-eslint-and-type-checking)
7. [CI commands](#7-ci-commands)

## 1. Setup

```bash
npm i -D vitest @vue/test-utils jsdom @pinia/testing @vitejs/plugin-vue vue-tsc typescript
```

```ts
// vite.config.ts (or vitest.config.ts)
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom', // or 'happy-dom'; both are optional peers that must be installed
    restoreMocks: true,
  },
})
```

- Reusing the Vite config means aliases (`@/`), the Vue plugin, and `define` constants behave the same in tests.
- Tests import `describe`, `it`, `expect`, `vi` explicitly from `vitest`; this works without enabling globals and keeps `tsc` happy.
- Coverage uses the `@vitest/coverage-v8` package at the same version as Vitest.
- Real-browser component tests use Vitest browser mode with a provider package such as `@vitest/browser-playwright`; check the current Vitest docs for the Vue setup. Browser end-to-end flows belong to playwright-expert.

## 2. Component tests

Test what the user sees and does: rendered text, roles, emitted events, and calls to collaborators. Avoid asserting on internal refs or private methods.

```ts
import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserCard from './UserCard.vue'

afterEach(() => vi.unstubAllGlobals())

it('renders the loaded name', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ name: 'Ada' }) }))
  const wrapper = mount(UserCard, { props: { id: '1' } })
  await flushPromises() // let the fetch promise chain and the re-render finish
  expect(wrapper.get('[data-test="name"]').text()).toBe('Ada')
  expect(fetch).toHaveBeenCalledWith('/api/users/1')
})

it('shows an error when the request fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
  const wrapper = mount(UserCard, { props: { id: '1' } })
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Could not load')
})
```

- `mount` renders the component and its children; `shallowMount` stubs child components. Prefer `mount` and stub only expensive or network-bound children with `global.stubs`.
- `await wrapper.get('button').trigger('click')` awaits the next DOM update. `await flushPromises()` waits for pending promises such as fetch or router navigation. `await nextTick()` waits for one render only.
- `wrapper.get(selector)` throws when missing; `wrapper.find(selector)` returns an empty wrapper. Use `get` for things that must exist, and `find(...).exists()` for absence checks.
- `wrapper.emitted('event')` returns an array of argument arrays, in order.
- `defineModel` tests: pass `modelValue` and `'onUpdate:modelValue'` in `props`; call `wrapper.setProps({ modelValue })` inside that handler to simulate a parent `v-model`.
- Slots: `mount(C, { slots: { default: '<span>x</span>' } })`; scoped slots take a function or a template string using `params`.
- Teleported content is outside `wrapper`; query `document.body` or stub with `global.stubs: { teleport: true }`.
- Cover failure paths (rejected request, empty list, invalid prop) as often as the happy path.

## 3. Pinia in tests

Test a store directly with a fresh Pinia per test:

```ts
import { beforeEach, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCounterStore } from './counter'

beforeEach(() => setActivePinia(createPinia()))

it('increments', () => {
  const store = useCounterStore()
  store.increment(2)
  expect(store.doubled).toBe(4)
})
```

Test a component with a stubbed store:

```ts
import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import QtyInput from './QtyInput.vue'
import { useCounterStore } from '../stores/counter'

it('calls the action without running it', async () => {
  const wrapper = mount(QtyInput, {
    props: { label: 'Qty', modelValue: 5 },
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn, initialState: { counter: { count: 3 } } })],
    },
  })
  const store = useCounterStore() // call after mount so it uses the testing Pinia
  await wrapper.get('[data-test="inc"]').trigger('click')
  expect(store.increment).toHaveBeenCalledTimes(1)
})
```

| `createTestingPinia` option | Effect |
|---|---|
| `createSpy` | Required when Vitest globals are off: pass `vi.fn`. Every action becomes a spy |
| `stubActions` | `true` (default) replaces actions with spies that do nothing; `false` runs real actions; an array or function selects which to stub |
| `initialState` | Seed state per store id before the test |
| `stubPatch`, `stubReset` | Stub `$patch` and `$reset` |
| `plugins` | Pinia plugins to install before the testing plugin |
| `fakeApp` | Create a fake app so plugins run without a mounted app |

- Getters in a testing Pinia are writable for the test: `store.doubled = 10` overrides the computed value (TypeScript marks getters readonly, so the assignment needs a `@ts-expect-error` comment).
- Use `stubActions: false` when the test is about the action's effect on state, and keep the network mocked.
- Match versions: `@pinia/testing` 2.0.2 has `pinia >=4.1.0` as a peer.

## 4. Router in tests

```ts
import { expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import Nav from './Nav.vue'

it('navigates when a link is clicked', async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/about', component: { template: '<div>about</div>' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(Nav, { global: { plugins: [router] } })
  await wrapper.get('a').trigger('click')
  await flushPromises()
  expect(wrapper.get('[data-test="path"]').text()).toBe('/about')
})
```

- Use `createMemoryHistory()` in tests; `createWebHistory` touches `window.location`.
- Await `router.push` and `router.isReady()` before mounting so the initial route is resolved.
- For a component that only reads `useRoute()`, a minimal router with that one route is enough; a mock with `vi.mock('vue-router')` hides integration bugs and is a last resort.
- Test guards as plain functions or by pushing to a router that has the guard, then asserting `router.currentRoute.value.fullPath`.

## 5. Composables, timers and mocks

Composables that use lifecycle hooks or `inject` need an app. A small helper mounts one:

```ts
import { createApp, type App } from 'vue'

export function withSetup<T>(composable: () => T): [T, App] {
  let result!: T
  const app = createApp({
    setup() {
      result = composable()
      return () => null
    },
  })
  app.mount(document.createElement('div'))
  return [result, app]
}
```

- Call `app.unmount()` at the end to run `onUnmounted` and `onScopeDispose` cleanup, and assert that timers and listeners are gone.
- Pure composables (only `ref`, `computed`, `watch`) can run inside `effectScope().run(() => ...)` without an app. `watch` callbacks run on the next tick: `await nextTick()` before asserting.
- Timers: `vi.useFakeTimers()` in `beforeEach`, `vi.advanceTimersByTime(ms)` to move time, `vi.useRealTimers()` in `afterEach`.
- Modules: `vi.mock('./api')` is hoisted to the top of the file; use `vi.hoisted` for values the factory needs. Reset between tests with `restoreMocks: true` or `vi.restoreAllMocks()`.
- Network: stub `fetch` with `vi.stubGlobal` as above, or run a mock server layer such as MSW (check the current docs for the version that matches your Node). Never call real services from unit tests.
- Time and randomness: freeze with `vi.setSystemTime(...)` and inject IDs so snapshots stay stable.
- Snapshots: keep them small and targeted; a large `wrapper.html()` snapshot hides real changes.
- Accessibility queries (`getByRole`) come from Testing Library for Vue (`@testing-library/vue`), which is optional; Vue Test Utils works with CSS selectors and `data-test` attributes.

## 6. ESLint and type checking

```js
// eslint.config.js (a .js or .mjs file; a .ts config needs the jiti package)
import pluginVue from 'eslint-plugin-vue'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'

export default defineConfigWithVueTs(
  { ignores: ['dist/**', '.output/**', '.nuxt/**', 'typed-router.d.ts'] },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  {
    files: ['src/pages/**/*.vue'],
    rules: { 'vue/multi-word-component-names': 'off' }, // index.vue, [id].vue
  },
)
```

- `eslint-plugin-vue` 10.12.0 exposes `flat/essential`, `flat/strongly-recommended` and `flat/recommended` (each cumulative); `flat/essential` leaves out formatting-style rules, which suits projects that already format with Prettier or another formatter.
- `@vue/eslint-config-typescript` 14.9.0 supplies `defineConfigWithVueTs` and `vueTsConfigs`; its peers are ESLint 9 or 10, TypeScript 4.8.4+ and `eslint-plugin-vue` 9.28+ or 10.
- `vue/no-v-html` is part of `flat/recommended` and warns "v-html directive can lead to XSS attack"; keep it enabled and justify each disable comment with the sanitizer used.
- Type check templates and scripts with `vue-tsc --noEmit` (`vue-tsc -b --noEmit` for solution-style tsconfigs such as Nuxt's). The plain `tsc` does not understand `.vue` files.
- Recommended `tsconfig` options: `strict`, `moduleResolution: "Bundler"`, `verbatimModuleSyntax`, `types: ["vite/client"]`, `noEmit`. For typed routes add `rootDir` and the `vue-router/volar/sfc-typed-router` Volar plugin (see [pinia-router.md](pinia-router.md#8-typed-file-based-routes)).
- Stricter template checks are configured under `vueCompilerOptions` in `tsconfig.json`; check the vue-tsc docs for the option names in your version before enabling them.

## 7. CI commands

```json
{
  "scripts": {
    "lint": "eslint .",
    "typecheck": "vue-tsc --noEmit",
    "test": "vitest run",
    "test:coverage": "vitest run --coverage",
    "build": "vite build"
  }
}
```

- Run `lint`, `typecheck`, `test` and `build` as separate CI steps so a failure names its cause.
- `vitest run` runs once and exits; plain `vitest` stays in watch mode on a developer machine.
- Pin the Node version in CI to one that satisfies Vite, Vitest and Nuxt engines (Node 22.22.3 or 24.15 and later satisfy all three versions listed above).
