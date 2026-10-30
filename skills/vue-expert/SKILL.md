---
name: vue-expert
description: >-
  Builds and reviews Vue 3 apps with the Composition API and script setup: reactivity, props and defineModel, composables, Pinia, Vue Router (typed file-based routes, guards), Nuxt data fetching and server routes, Vite, and tests with Vitest and Vue Test Utils. Use when working with .vue files, vue-tsc errors, defineProps or defineEmits, ref versus reactive bugs, storeToRefs, createTestingPinia, nuxt.config.ts, runtimeConfig, useFetch or useAsyncData, or v-html and CSP questions. Not for React (use senior-react-19-engineer), Next.js (use nextjs-15-architect), Tailwind (use tailwindcss-master), advanced TypeScript types (use typescript-master), or browser E2E (use playwright-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Vue Expert

This skill covers Vue 3 application work: single-file components with `<script setup>`, the reactivity system, composables, Pinia state, Vue Router, Nuxt basics, Vite configuration, and unit and component tests. It focuses on version-sensitive behavior and on mistakes that show up in review: lost reactivity, unsafe `v-html`, secrets in client bundles, and tests that do not exercise the component. Deep material is split into reference files that are read on demand.

> Verified against Vue 3.5.44, Pinia 4.1.0, Vue Router 5.4.0, Nuxt 4.6.3, Vite 8.3.5, Vitest 5.0.5, Vue Test Utils 2.5.1, @pinia/testing 2.0.2, vue-tsc 3.3.14, eslint-plugin-vue 10.12.0 (2026-10).

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

- Covered: Vue 3 Composition API and `<script setup>`; `ref`, `reactive`, `computed`, `watch`, `watchEffect`; reactive props destructure, `useTemplateRef`, `defineModel`, typed `defineProps` and `defineEmits`; composables; `provide`/`inject` with `InjectionKey`; Pinia setup stores and `storeToRefs`; Vue Router including typed file-based routes, guards and lazy routes; Nuxt `app/` structure, `useFetch`, `useAsyncData`, server routes and `runtimeConfig`; Vite configuration; Vitest with Vue Test Utils and `@pinia/testing`; `vue-tsc` and `eslint-plugin-vue`; XSS, secret handling and CSP in Vue apps.
- Not covered: React (senior-react-19-engineer), Next.js (nextjs-15-architect), Tailwind CSS styling (tailwindcss-master), advanced TypeScript type design (typescript-master), browser end-to-end tests (playwright-expert), general web accessibility audits (accessibility-expert).
- Vue 2 and the Options API are mentioned only where migration or interop matters. Vue 3.6 and Vapor mode are published as release candidates (npm tag `rc`, 3.6.0-rc.14 when checked), not as the stable `latest` (3.5.44); treat them as experimental and check the current docs before use.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Reactive props destructure | Stable in Vue 3.5: `const { max = 10 } = defineProps<{ max?: number }>()` keeps reactivity; the compiler rewrites reads to `props.max`. Pass `() => max` to `watch` or composables, not the bare value |
| `defineModel` | `const model = defineModel<string>({ required: true })`; creates a prop plus `update:modelValue`; named form `defineModel<boolean>('open')` for `v-model:open` |
| `useTemplateRef` | Vue 3.5+: `useTemplateRef<HTMLInputElement>('input')` matches `ref="input"`; value is `null` before mount; vue-tsc infers component types |
| Typed emits | Named tuples: `defineEmits<{ select: [id: string]; close: [] }>()` |
| `ref` vs `reactive` | Default to `ref`; `reactive` cannot hold primitives and loses reactivity on reassignment or destructuring; `shallowRef` for large or third-party objects |
| `watch` options | `immediate`, `once` (3.4+), `deep: true` or a depth number (3.5+), `flush: 'post'`; `onWatcherCleanup()` (3.5+) must be called synchronously in the callback |
| Other 3.5 APIs | `useId()` for SSR-stable IDs; `Teleport` `defer`; lazy hydration with `defineAsyncComponent({ hydrate: hydrateOnVisible() })` |
| Pinia 4.1 | ESM only; `@vue/devtools-api` is a peer dependency; peers Vue 3.5.11+ and TypeScript 5.6+; `storeToRefs` skips nullish values; `$reset()` is not available on setup stores |
| `@pinia/testing` 2.0.2 | `createTestingPinia({ createSpy: vi.fn, initialState, stubActions })`; requires `pinia >=4.1.0` |
| Vue Router 5.4 | Transition release that merges `unplugin-vue-router` into core with no breaking changes for v4 users; plugin import is `vue-router/vite`, generated routes come from `vue-router/auto-routes`, Volar plugin is `vue-router/volar/sfc-typed-router` |
| Typed routes | Plugin writes `typed-router.d.ts`; set `rootDir` in tsconfig; `router.push({ name: '/users/[id]', params: { id } })` is checked by vue-tsc; `definePage({ meta })` sets route fields |
| Nuxt 4.6 | `app/` holds `app.vue`, `pages/`, `components/`, `composables/`, `middleware/`; `server/` stays at the root; root `tsconfig.json` references `.nuxt/tsconfig.*.json`; `nuxt typecheck` needs `vue-tsc` and `typescript` |
| Nuxt data | `useAsyncData` and `useFetch` return `data` (shallow ref by default, `DataT \| undefined`), `status` (`idle`, `pending`, `success`, `error`), `error`, `refresh`; `dedupe` defaults to `'cancel'` |
| `runtimeConfig` | Keys outside `public` are server only; override with `NUXT_` plus the upper snake case path (`NUXT_API_SECRET`, `NUXT_PUBLIC_API_BASE`); only declared keys can be overridden |
| Vite 8.3 | Bundles with Rolldown; Node `^20.19.0 \|\| >=22.12.0`; `build.rolldownOptions` replaces the deprecated `rollupOptions`; only variables matching `envPrefix` (default `VITE_`) reach client code |
| Vitest 5 | Node `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; config from `vitest/config`; `jsdom` and `happy-dom` are optional peers that must be installed |
| Type checking | `vue-tsc --noEmit` checks `.vue` files; `vue-tsc -b --noEmit` for solution-style tsconfigs such as Nuxt's |
| ESLint | Flat config: `pluginVue.configs['flat/recommended']` plus `defineConfigWithVueTs` and `vueTsConfigs.recommended` from `@vue/eslint-config-typescript`; `vue/no-v-html` warns about XSS; a `.ts` config file needs the `jiti` package |

## 3. Workflow

1. Read `package.json`, `vite.config.*` or `nuxt.config.ts`, `tsconfig.json`, and the lockfile to learn the Vue, router, Pinia and test versions. Do not apply 3.5 APIs to a project pinned to an older minor.
2. Reproduce the problem: run the dev server, the failing test (`npx vitest run path/to/file.test.ts`), or `npx vue-tsc --noEmit`. For reactivity bugs, find where a value was destructured, reassigned or read after an `await`.
3. Locate ownership of the state: local `ref`, a prop and event pair or `defineModel`, `provide`/`inject`, a Pinia store, the route, or server data (`useAsyncData`). Change the owner, not a copy.
4. Make the smallest change that follows the existing style (Options API files stay Options API unless asked to migrate).
5. Add or update a test that fails before the change: component test with `mount`, store test with `setActivePinia(createPinia())`, composable test inside an app or `effectScope`.
6. Run the project's checks: `eslint .`, `vue-tsc --noEmit`, `vitest run`, and `vite build` or `nuxt build` when config, routes or dependencies changed.
7. Summarize what changed, which checks ran, and any follow-up (version bumps, regenerated `typed-router.d.ts`, environment variables to set).

## 4. Decision Rules

- If a value is a primitive, an array that gets replaced, or must be passed around, use `ref`. Use `reactive` only for a local object that is never reassigned or destructured.
- If a child edits a value that the parent owns, use `defineModel`. If it only reports an event, use `defineEmits`. Never mutate a prop.
- If state is used by one component, keep it local; by a subtree, use `provide`/`inject` with an `InjectionKey`; by unrelated parts of the app, or needs devtools and SSR transfer, use a Pinia store.
- If logic mixes reactive state with lifecycle or watchers and is reused, extract a `useX` composable. If it is a pure function, keep it a plain function.
- If a value derives from other state with no side effects, use `computed`. Use `watch` only for side effects (requests, storage, DOM), and `watchEffect` only when the dependencies are everything read synchronously.
- If an object is large, immutable-style or owned by a library (map, chart, editor), use `shallowRef` or `markRaw`.
- If the project uses Pinia, use setup stores for new code unless the codebase already standardizes on options stores. Read state with `storeToRefs`, call actions directly.
- If routes are many and follow folders, use the file-based plugin in `vue-router/vite`; otherwise declare routes by hand. Do not mix both without a reason.
- If data is needed to render a Nuxt page, use `useFetch` (single URL) or `useAsyncData` (custom key or source), awaited at the top of `<script setup>`. Use `$fetch` for actions triggered by users.
- If a value must stay private, put it in `runtimeConfig` outside `public` and read it only under `server/`.
- If the same check is needed in the UI and for security, implement it on the server and treat the client check as UX.
- If a test needs a store, use `createTestingPinia` for components and a real store with a fresh Pinia for store logic.

## 5. Coding Standards

- Use `<script setup lang="ts">` with the order: imports, props/emits/model, state, computed, watchers, functions, lifecycle hooks.
- Component files use PascalCase names of two or more words (`UserCard.vue`); route files under `pages/` are exempt from `vue/multi-word-component-names`.
- Type props with the type-based form and a named `interface`; derive emits from named-tuple types.
- Use `v-for` with a stable `:key` (an id, not the index when the list can reorder) and never put `v-if` and `v-for` on the same element.
- Use `:prop` and `@event` shorthands, kebab-case events in templates, and `camelCase` in script.
- Name composables `useX`, return refs, accept `MaybeRefOrGetter` and read with `toValue`.
- Register cleanup with `onScopeDispose` or `onUnmounted` for timers, listeners, observers and requests.
- Keep templates declarative: move long expressions into `computed` or functions.
- Use `import type` for type-only imports (`verbatimModuleSyntax`).
- Do not add a second linter or formatter; follow the repository's configuration.

## 6. Project Structure

Vite SPA:

```text
src/
├── main.ts
├── App.vue
├── router/index.ts          # or pages/ with vue-router/vite
├── stores/                  # one Pinia store per domain: cart.ts, auth.ts
├── composables/             # useDebounced.ts, useFetchJson.ts
├── components/              # presentational and shared components
├── pages/                   # route-level components
├── api/                     # typed fetch wrappers
└── types/                   # shared types, route-meta.d.ts
```

Nuxt 4:

```text
app/                         # app.vue, pages/, components/, composables/, middleware/
server/                      # api/, routes/, middleware/, utils/
public/
nuxt.config.ts
tsconfig.json                # references .nuxt/tsconfig.*.json
```

## 7. Design Patterns

- **Composable with injected inputs**: accept `MaybeRefOrGetter`, return refs, clean up in `onScopeDispose`. Cost: callers must be inside setup or an effect scope.
- **Setup store per domain**: state as `ref`, getters as `computed`, actions as functions; return everything public. Cost: no `$reset()`; write a `reset()` action.
- **Typed provide/inject**: a `keys.ts` exports `InjectionKey<T>`, with a `useX()` wrapper that throws when missing. Cost: implicit dependency; document the provider.
- **Container and presentational split**: pages fetch and own state; leaf components take props and emit events, which makes them easy to test.
- **Renderless or slot-driven components**: expose state through scoped slots (`defineSlots`) when markup varies by caller.
- **Route-level lazy loading**: `component: () => import('./Page.vue')` per route; cost is a request per first visit, mitigated by prefetching on intent.
- **Server routes as the trust boundary** (Nuxt): validate input with a schema, authorize, filter by owner on reads and writes, return minimal fields.
- Details and full examples: [references/reactivity-composables.md](references/reactivity-composables.md), [references/pinia-router.md](references/pinia-router.md), [references/nuxt.md](references/nuxt.md).

## 8. Best Practices

- Keep one source of truth per piece of state; derive the rest with `computed` instead of syncing refs with watchers.
- Make props immutable in children and emit changes; this keeps data flow traceable.
- Await data once at the page level and pass results down as props; this avoids request waterfalls.
- Use `watch(() => props.x, ...)` or destructure with defaults rather than copying props into local refs at setup time.
- Type `inject` through `InjectionKey` and handle `undefined`.
- Prefer `defineModel` to hand-written `modelValue` plus `update:modelValue` pairs.
- Use `useId()` for `for`/`id` pairs so server and client markup match.
- Avoid module-level mutable state in code that runs on the server; it is shared between requests.
- Commit `typed-router.d.ts` and lockfiles; regenerate types in CI before `vue-tsc`.
- Keep `.env.example` with variable names only and ignore real `.env*` files.

## 9. Performance

- Measure first: Vue Devtools performance and component render timeline, browser Performance panel, and `vite build` output sizes. Optimize what the measurements show.
- Split by route with dynamic `import()`; check the chunk report after `vite build` for large shared chunks.
- Use `shallowRef` and `shallowReactive` for big objects replaced as a whole; deep reactivity on thousands of nested fields is the usual cost.
- Keep `v-for` keys stable and lists virtualized (a virtual scroller library) when rows number in the thousands.
- `computed` caches; methods in templates rerun on every render. Move heavy work into `computed`.
- `v-once` and `v-memo` skip updates for static or rarely changing subtrees; use them only after profiling shows re-render cost.
- `watch` with `deep: true` traverses the whole structure; prefer a getter for the exact field or a depth number.
- In Nuxt, use `pick` or `transform` in `useFetch` so unused fields are not serialized into the payload, and use lazy variants or `defineAsyncComponent` with lazy hydration for below-the-fold components.
- Avoid importing whole icon or utility libraries; import named modules so the bundler can drop the rest.

## 10. Security

- **XSS through `v-html`**: it inserts raw HTML. Use it only with content sanitized by a maintained sanitizer (for example DOMPurify) at the point of rendering, and keep `vue/no-v-html` enabled with a justified disable comment. Prefer text interpolation (`{{ }}`), which escapes by default. Never bind user input to `:href`/`:src` without allowing only `http:`, `https:` and `mailto:` schemes (`javascript:` URLs execute).
- **Secrets in the client bundle**: everything imported by client code and every `VITE_*` variable (or any variable matching `envPrefix`) is public. API keys with write power, database URLs and signing secrets belong on a server. In Nuxt, secrets go in `runtimeConfig` outside `public` and are read in `server/` only; the generated types still list private keys on the client, so review code, not just types.
- **Never widen `envPrefix`** to `''` or to a prefix that matches secrets.
- **Content Security Policy**: use `script-src 'self'` with nonces or hashes, not `'unsafe-inline'`. Vite supports a nonce placeholder through `html.cspNonce` that the server must replace per request. For `style-src`, prefer extracted CSS files over inline styles. For Nuxt, check the current docs for the supported CSP option or module.
- **Auth and authorization**: route guards hide pages, they do not protect data. Authorize on the server, and filter by owner or tenant on writes as well as reads.
- **Token storage**: avoid keeping long-lived tokens in `localStorage`; prefer `HttpOnly`, `Secure`, `SameSite` cookies set by the server.
- **Open redirects**: validate a `redirect` query parameter (same-origin path starting with a single `/`) before navigating.
- **SSR**: no per-user data in module scope; create the app and Pinia per request.
- **Dependencies**: keep a lockfile, run `npm audit` or the equivalent in CI, and review postinstall scripts of new packages.

## 11. Testing

- Component tests with Vitest and Vue Test Utils: `mount`, `await trigger(...)`, `await flushPromises()` for fetch and router work, assertions on text, roles, emitted events.
- Store tests with `setActivePinia(createPinia())` per test; component tests with `createTestingPinia({ createSpy: vi.fn })` (actions are stubbed unless `stubActions: false`).
- Router tests with `createMemoryHistory()`, awaiting `router.push` and `router.isReady()` before `mount`.
- Composable tests: pure ones in `effectScope().run`, lifecycle-dependent ones inside a small app helper; call `app.unmount()` to check cleanup.
- Mock the network with `vi.stubGlobal('fetch', ...)` or a mock server; never call real services.
- Cover failure paths: rejected request, empty data, invalid props, guard redirect.
- Commands: `npx vitest run`, `npx vitest run --coverage` (needs `@vitest/coverage-v8`), `npx vue-tsc --noEmit`, `npx eslint .`.
- Browser end-to-end flows belong to playwright-expert; generic unit-test practice to unit-testing-expert.
- Details and executable samples: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] APIs used exist in the project's Vue, Pinia, Vue Router and Nuxt versions.
- [ ] No reactivity lost by destructuring `reactive`, store state, or props passed as bare values to `watch` or composables.
- [ ] Props are not mutated; two-way bindings use `defineModel` or an event.
- [ ] Watchers and composables clean up timers, listeners and in-flight requests.
- [ ] `v-html` appears only with sanitized content; no user-controlled `href` or `src` schemes.
- [ ] No secrets in `VITE_*` variables, `public` runtime config, `app.config.ts`, or client code.
- [ ] Server routes validate input, authorize, and filter by owner on reads and writes.
- [ ] Pinia state is read through `storeToRefs` (or the store), not destructured.
- [ ] Routes are lazy where sensible; guards return values; redirects are validated.
- [ ] `vue-tsc --noEmit`, ESLint and the test suite pass; new behavior has a test, including a failure path.
- [ ] CSP changes do not add `unsafe-inline`.
- [ ] No module-level per-user state in SSR code.

## 13. Production Notes

- Build with `vite build` (or `nuxt build`), serve `dist/` or `.output/` from a server that rewrites unknown paths to `index.html` for history mode.
- Set runtime secrets through the host's environment or secret manager at start time. In a Nuxt test build, setting `NUXT_API_SECRET` at build time did not embed the value, and setting it when starting the server made it available to handlers.
- Upload source maps to the error tracker and do not serve them publicly if the source is private.
- Add error reporting with `app.config.errorHandler` and, in Nuxt, `app/error.vue` and `onErrorCaptured`; track Core Web Vitals in real-user monitoring.
- Upgrade notes: Pinia 4 is ESM only and needs `@vue/devtools-api` installed; `@pinia/nuxt` and `@pinia/testing` must accept the installed `pinia`. Vue Router 5 moves `unplugin-vue-router` imports to `vue-router/vite`, `vue-router/auto-routes` and `vue-router/volar/...` paths. Vite 8 uses `rolldownOptions`. Vitest 5 and Nuxt 4.6 require recent Node 22 or 24 releases.
- Vue 3.6 and Vapor mode are pre-release; pin versions and test thoroughly before trying them, and read the release notes of each release candidate.
- Keep Node, package manager and lockfile versions pinned in CI so builds match local machines.

## 14. Examples

A form field component using reactive props destructure, `defineModel`, typed emits and a template ref:

```vue
<script setup lang="ts">
import { onMounted, useTemplateRef } from 'vue'

const { label, min = 0 } = defineProps<{ label: string; min?: number }>()
const model = defineModel<number>({ required: true })
const emit = defineEmits<{ reset: [reason: string] }>()
const input = useTemplateRef<HTMLInputElement>('input')

onMounted(() => input.value?.focus())

function reset() {
  model.value = min
  emit('reset', 'user')
}
</script>

<template>
  <label>{{ label }} <input ref="input" v-model.number="model" type="number" :min="min" /></label>
  <button type="button" @click="reset">Reset</button>
</template>
```

A Pinia setup store and a component test that stubs its actions:

```ts
// stores/counter.ts
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const doubled = computed(() => count.value * 2)
  function increment(by = 1) {
    count.value += by
  }
  return { count, doubled, increment }
})
```

```ts
// Counter.test.ts
import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Counter from './Counter.vue'
import { useCounterStore } from './stores/counter'

it('calls increment without running it', async () => {
  const wrapper = mount(Counter, {
    global: { plugins: [createTestingPinia({ createSpy: vi.fn, initialState: { counter: { count: 3 } } })] },
  })
  const store = useCounterStore()
  await wrapper.get('button').trigger('click')
  expect(store.increment).toHaveBeenCalledTimes(1)
})
```

A Nuxt server route that validates input, plus private and public runtime config (Zod is a separate dependency):

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  compatibilityDate: '2026-10-01',
  runtimeConfig: {
    apiSecret: '', // server only, set NUXT_API_SECRET in the environment
    public: { apiBase: '/api' },
  },
})
```

```ts
// server/api/notes.post.ts
import { z } from 'zod'

const bodySchema = z.object({ title: z.string().min(1).max(120) })

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, bodySchema.parse)
  setResponseStatus(event, 201)
  return { id: crypto.randomUUID(), title: body.title }
})
```

Rendering untrusted HTML safely (DOMPurify is a separate dependency):

```vue
<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'

const { html } = defineProps<{ html: string }>()
const clean = computed(() => DOMPurify.sanitize(html, { USE_PROFILES: { html: true } }))
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify above -->
  <div v-html="clean" />
</template>
```

## 15. Common Mistakes

- **Destructuring `reactive` or store state** (`const { count } = store`): the value is copied and never updates. Use `storeToRefs(store)` or `toRefs`.
- **Reassigning a `reactive` variable**: the new object is not tracked by existing effects. Use `ref`, or mutate fields.
- **`watch(state.id, ...)`**: passes a plain value. Use `watch(() => state.id, ...)`.
- **Passing a destructured prop to a composable**: the composable sees a constant. Pass `() => prop` or `toRef(() => prop)`.
- **`await` before a reactive read in `watchEffect`**: reads after the first `await` are not tracked. Use `watch` with explicit sources.
- **Mutating a prop**: Vue warns, and the parent state diverges. Emit an event or use `defineModel`.
- **`v-if` with `v-for` on one element**: precedence confusion and wasted work. Filter in a `computed` or wrap in `<template v-for>`.
- **Index as `:key` on reorderable lists**: state sticks to the wrong row. Use a stable id.
- **`v-html` with unsanitized strings**: stored or reflected XSS. Sanitize, or render text.
- **Secrets in `VITE_*` or `runtimeConfig.public`**: shipped to every visitor. Move to a server and read with `useRuntimeConfig(event)`.
- **Calling `useXStore()` at module top level before `app.use(pinia)`**: "no active Pinia" error. Call inside setup, guards or actions.
- **Module-level `createPinia()` or `ref` in SSR**: state leaks between users. Create per request; use `useState` in Nuxt.
- **`useAsyncData` with a shared key for different data**: results overwrite each other. Use unique, reactive keys.
- **Mutating `data.value.nested` in Nuxt expecting reactivity**: `data` is a shallow ref by default. Replace the value or pass `deep: true`.
- **Route guard as the only access control**: the API stays open. Authorize on the server.
- **Using `tsc` for `.vue` files**: templates and SFC types are not checked. Run `vue-tsc`.
- **Missing `rootDir` with typed routes**: the Volar plugin warns and param types degrade. Set `compilerOptions.rootDir`.
- **Skipping `flushPromises()` in tests**: assertions run before async updates. Await it after triggering async work.
- **Mixing `@pinia/testing` or `@pinia/nuxt` with a `pinia` outside their peer range**: install fails with `ERESOLVE` or runtime errors. Upgrade them together.

## 16. References

- [references/reactivity-composables.md](references/reactivity-composables.md): `ref`/`reactive`/`shallowRef`, `computed`, `watch` options and cleanup, props destructure, `defineModel`, template refs, composable design, `provide`/`inject`, slots and macros.
- [references/pinia-router.md](references/pinia-router.md): Pinia setup stores, `storeToRefs`, plugins and SSR, Vue Router 5 typed file-based routes, navigation guards, lazy routes and scroll behavior.
- [references/nuxt.md](references/nuxt.md): Nuxt 4 layout, `runtimeConfig`, `useFetch`/`useAsyncData`, server routes with validation, middleware, `routeRules`, type checking and security notes.
- [references/testing.md](references/testing.md): Vitest setup, Vue Test Utils patterns, `createTestingPinia`, router and composable tests, ESLint flat config, `vue-tsc`, CI scripts.
- Official docs: https://vuejs.org/guide/introduction.html , https://vuejs.org/api/ , https://pinia.vuejs.org/ , https://router.vuejs.org/ , https://nuxt.com/docs , https://vite.dev/guide/ , https://vitest.dev/guide/ , https://test-utils.vuejs.org/ , https://eslint.vuejs.org/
