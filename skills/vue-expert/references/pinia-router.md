# Pinia and Vue Router

Reference for Pinia stores and Vue Router configuration, including typed file-based routes and navigation guards. Verified against Pinia 4.1.0 (peer: Vue 3.5.11+, TypeScript 5.6+, `@vue/devtools-api` 8.2.1+) and Vue Router 5.4.0 (2026-10). Both packages are ESM-first; Pinia 4 is ESM only.

## Contents

1. [Pinia setup](#1-pinia-setup)
2. [Setup stores](#2-setup-stores)
3. [Options stores and when to use them](#3-options-stores-and-when-to-use-them)
4. [Using stores in components](#4-using-stores-in-components)
5. [Stores outside components and SSR](#5-stores-outside-components-and-ssr)
6. [Plugins, subscriptions and HMR](#6-plugins-subscriptions-and-hmr)
7. [Vue Router basics](#7-vue-router-basics)
8. [Typed file-based routes](#8-typed-file-based-routes)
9. [Navigation guards](#9-navigation-guards)
10. [Lazy loading and scroll behavior](#10-lazy-loading-and-scroll-behavior)

## 1. Pinia setup

```ts
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'

createApp(App).use(createPinia()).use(router).mount('#app')
```

- Install order matters only for code that uses a store before `app.use(pinia)`; stores need an active Pinia instance.
- Pinia 4 changes from 3: ESM only, `@vue/devtools-api` is a peer dependency to install next to `pinia`, error and warning messages were reworked, and `storeToRefs` skips nullish values without throwing. `@pinia/nuxt` and `@pinia/testing` must be on versions whose peer range accepts the installed Pinia (`@pinia/testing` 2.0.2 requires `pinia >=4.1.0`).
- Pinia 3 removed the `PiniaStorePlugin` type (use `PiniaPlugin`) and the `defineStore({ id })` form (use `defineStore('id', ...)`).

## 2. Setup stores

A setup store is a function that returns what should be public: `ref` becomes state, `computed` becomes getters, functions become actions.

```ts
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export interface CartLine { sku: string; qty: number; unitCents: number }

export const useCartStore = defineStore('cart', () => {
  const lines = ref<CartLine[]>([])
  const totalCents = computed(() => lines.value.reduce((sum, l) => sum + l.qty * l.unitCents, 0))

  function add(line: CartLine) {
    const existing = lines.value.find((l) => l.sku === line.sku)
    if (existing) existing.qty += line.qty
    else lines.value.push({ ...line })
  }

  function clear() {
    lines.value = []
  }

  return { lines, totalCents, add, clear }
})
```

Rules for setup stores:

- Return every piece of state, or it is invisible to devtools, SSR serialization, and plugins. Private helpers stay unreturned.
- `$reset()` is not available on setup stores; write a `reset()` action that assigns the initial values.
- Other composables can be used inside; `useRoute()`-style injections need to be called where an app context exists (see section 5).
- Use `shallowRef` for large collections that are replaced wholesale.
- Do not return the whole store of another store; call `useOtherStore()` inside the action that needs it, which avoids circular imports at module evaluation.

## 3. Options stores and when to use them

```ts
export const useSettingsStore = defineStore('settings', {
  state: () => ({ locale: 'en' as 'en' | 'de' }),
  getters: { isGerman: (s) => s.locale === 'de' },
  actions: { setLocale(l: 'en' | 'de') { this.locale = l } },
})
```

- Options stores suit small flat stores and teams that already use them; they provide `$reset()`.
- Setup stores compose better with other composables and have simpler typing. Pick one style per project.

## 4. Using stores in components

```vue
<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useCartStore } from '@/stores/cart'

const cart = useCartStore()
const { lines, totalCents } = storeToRefs(cart) // state and getters as refs
const { add, clear } = cart // actions are plain functions; destructure directly
</script>
```

- Destructuring state or getters directly (`const { lines } = cart`) copies the current value and loses reactivity; use `storeToRefs`.
- Mutate through actions; direct assignment (`cart.lines = []`) works but spreads write logic across components.
- `cart.$patch({ ... })` or `cart.$patch((state) => { ... })` batches several mutations into one devtools entry.
- Do not put form-draft state that dies with a component into a store.
- Persist selected state (for example a theme) with a plugin or a small `watch` writing to `localStorage` inside `try/catch`; never persist tokens that grant API access in `localStorage` without weighing XSS exposure (prefer `HttpOnly` cookies set by the server).

## 5. Stores outside components and SSR

```ts
// router guard or utility file
import { useAuthStore } from '@/stores/auth'

router.beforeEach((to) => {
  const auth = useAuthStore() // call inside the callback, after app.use(pinia)
  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
})
```

- Calling `useXStore()` at module top level in a file imported before `app.use(pinia)` fails with "getActivePinia() was called but there was no active Pinia".
- Outside components pass the instance when it is needed before install: `useXStore(pinia)`.
- SSR: create one Pinia per request (`createPinia()` inside the app factory). A module-level `createPinia()` shares state between users. In Nuxt use `@pinia/nuxt`, which handles this.
- Never put secrets or per-user private data in state that is serialized into the HTML payload for other audiences.

## 6. Plugins, subscriptions and HMR

```ts
import type { PiniaPlugin } from 'pinia'

export const lastActionPlugin: PiniaPlugin = ({ store }) => {
  store.$onAction(({ name, after, onError }) => {
    after(() => console.debug(`[${store.$id}] ${name} done`))
    onError((err) => console.error(`[${store.$id}] ${name} failed`, err))
  })
}
```

- Register with `pinia.use(lastActionPlugin)` before the stores are first used.
- `store.$subscribe((mutation, state) => ...)` observes state changes; it is removed with the component unless `{ detached: true }`.
- HMR for a store file: `if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useCartStore, import.meta.hot))`.

## 7. Vue Router basics

```ts
import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue') },
    { path: '/users/:id', name: 'user', component: () => import('@/pages/UserPage.vue'), props: true },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/NotFound.vue') },
  ],
})
```

- Use `useRoute()` for reactive current route and `useRouter()` for navigation in `<script setup>`. A destructured `route.params` loses reactivity; read `route.params.id` inside `computed` or `watch(() => route.params.id, ...)`.
- `props: true` passes route params as props, which decouples pages from the router and simplifies tests.
- Navigating to the same route with different params reuses the component; react to the param change with `watch`, or use `onBeforeRouteUpdate`.
- `router.push` returns a promise that resolves to a navigation failure (or `undefined`); check with `isNavigationFailure`.
- Vue Router 5 is a transition release that merges `unplugin-vue-router` into the core package and has no breaking changes for v4 users. Vue Router 6 is announced as ESM only with deprecated APIs removed (check the current docs for its status).

## 8. Typed file-based routes

Vue Router 5 includes the file-based routing plugin; use it instead of the separate `unplugin-vue-router` package.

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueRouter from 'vue-router/vite'

export default defineConfig({
  plugins: [VueRouter({ routesFolder: 'src/pages' }), vue()], // VueRouter before vue()
})
```

```ts
// router.ts
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from 'vue-router/auto-routes'

export const router = createRouter({ history: createWebHistory(), routes })
```

```json
{
  "compilerOptions": { "rootDir": ".", "moduleResolution": "Bundler", "strict": true },
  "include": ["src/**/*.ts", "src/**/*.vue", "typed-router.d.ts", "env.d.ts"],
  "vueCompilerOptions": { "plugins": ["vue-router/volar/sfc-typed-router"] }
}
```

- The plugin writes `typed-router.d.ts` (commit it; include it in `tsconfig.json`). Run the dev server or a build once to generate it.
- With the Volar plugin and `rootDir` set, `useRoute()` in `src/pages/users/[id].vue` is typed with `params.id: string`. Without `rootDir` the plugin prints a warning and param types fall back to a union with an empty record.
- `router.push({ name: '/users/[id]', params: { id: '1' } })` is checked: an unknown name or a wrong param key is a type error under `vue-tsc`.
- File names map to paths: `index.vue` is `/`, `users/[id].vue` is `/users/:id`, `opt/[[id]].vue` is the optional param `/opt/:id?`, `[...path].vue` is the catch-all `/:path(.*)`.
- `definePage({ name: 'admin-home', meta: { requiresAuth: true } })` inside `<script setup>` of a page sets route fields; it is a compile-time macro.
- Type custom `meta` once:

```ts
// src/route-meta.d.ts
import 'vue-router'
declare module 'vue-router' {
  interface RouteMeta { requiresAuth?: boolean }
}
```

- The ESLint rule `vue/multi-word-component-names` flags `index.vue` and `[id].vue`; disable it for the pages folder.
- Importing from `vue-router/auto` is marked deprecated in the package; import from `vue-router/auto-routes`.

## 9. Navigation guards

```ts
router.beforeEach(async (to, from) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})
```

| Return value | Effect |
|---|---|
| `undefined` or `true` | Continue |
| `false` | Cancel the navigation |
| A route location | Redirect |
| Throwing an error | Cancel and call `router.onError` handlers |

- Prefer returning values over the `next` callback. If `next` is used it must be called exactly once.
- Order: `onBeforeRouteLeave` in components being left, global `beforeEach`, `beforeRouteUpdate` in reused components, per-route `beforeEnter`, `beforeResolve`, then `afterEach`. `afterEach` cannot change navigation; use it for analytics and focus handling.
- In components: `onBeforeRouteLeave((to, from) => ...)` returns `false` to block (for unsaved changes).
- Client guards are UX, not security. The server must authorize every API call; hiding a route does not protect data.
- Validate the `redirect` query parameter before following it: allow only same-origin paths that start with `/` and not `//`.
- Keep guards fast and avoid fetching large data in them; fetch in the page, or in Nuxt use `useAsyncData`.

## 10. Lazy loading and scroll behavior

- `component: () => import('./Page.vue')` splits the page into its own chunk. Group related routes with a shared chunk name through `build.rolldownOptions` only when measurements justify it (Vite 8 bundles with Rolldown; `build.rollupOptions` is deprecated in its types).
- Keep the first-paint routes (home, login) eager only when they are tiny.
- Prefetch on intent: call the loader on hover or when a link becomes visible; the browser caches the module.
- `scrollBehavior(to, from, saved)` returns `saved` for back and forward, `{ el: to.hash, behavior: 'smooth' }` for hashes, and `{ top: 0 }` otherwise.
- Use `createWebHashHistory` only when the server cannot rewrite unknown paths to `index.html`; otherwise use `createWebHistory` with a fallback rule on the server.
