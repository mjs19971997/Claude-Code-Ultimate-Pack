# Nuxt Basics

Reference for Nuxt 4 application structure, data fetching, server routes, runtime configuration, and type checking. Verified against Nuxt 4.6.3 (Node `^22.22.3 || ^24.15.0 || >=26` per its package metadata), Vue 3.5.44, Vue Router 5.4.0 and vue-tsc 3.3.14 (2026-10). Items marked "check the current docs" were not confirmed.

## Contents

1. [Directory layout](#1-directory-layout)
2. [Configuration and runtimeConfig](#2-configuration-and-runtimeconfig)
3. [Data fetching](#3-data-fetching)
4. [Server routes](#4-server-routes)
5. [Middleware, state and cookies](#5-middleware-state-and-cookies)
6. [Rendering modes and routeRules](#6-rendering-modes-and-routerules)
7. [Type checking and linting](#7-type-checking-and-linting)
8. [Security notes](#8-security-notes)

## 1. Directory layout

Nuxt 4 uses an `app/` directory for client and universal code, and keeps `server/` at the project root.

```text
my-app/
├── app/
│   ├── app.vue
│   ├── pages/            # file-based routes
│   ├── components/       # auto-imported
│   ├── composables/      # auto-imported
│   ├── layouts/
│   ├── middleware/       # route middleware
│   └── plugins/
├── server/
│   ├── api/              # /api/* handlers: hello.get.ts, notes.post.ts, items/[id].get.ts
│   ├── routes/           # handlers outside /api
│   ├── middleware/       # run on every request
│   └── utils/            # auto-imported in server code
├── public/               # static files served as-is
├── nuxt.config.ts
├── tsconfig.json         # references the generated .nuxt/tsconfig.*.json files
└── .env                  # local only, gitignored
```

- Auto-imports cover Vue APIs, Nuxt composables, `app/components`, `app/composables`, and `server/utils`. Explicit imports remain valid and make files easier to test.
- Route params use the same bracket syntax as Vue Router file-based routing: `pages/users/[id].vue`.

## 2. Configuration and runtimeConfig

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  compatibilityDate: '2026-10-01',
  runtimeConfig: {
    apiSecret: '', // server only; override at run time with NUXT_API_SECRET
    public: {
      apiBase: '/api', // sent to the browser; override with NUXT_PUBLIC_API_BASE
    },
  },
})
```

- Keys outside `public` are available only on the server (`useRuntimeConfig(event)` in `server/`). Keys under `public` are serialized into the client payload.
- Declare every key in `nuxt.config.ts` with a default (an empty string is fine); only declared keys can be overridden by environment variables. The override name is `NUXT_` plus the path in upper snake case: `runtimeConfig.apiSecret` becomes `NUXT_API_SECRET`, `runtimeConfig.public.apiBase` becomes `NUXT_PUBLIC_API_BASE`.
- Verified in a test build: setting `NUXT_API_SECRET` at build time did not put the value into `.output`, and setting it at start time made it visible to server handlers.
- The generated types list private keys on `useRuntimeConfig()` in app code as well, so TypeScript does not stop client code from naming one. At run time the client receives only `public` and `app`. Review diffs for private keys used in components and pages.
- Do not read secrets in `app/` code or compute them at build time into `app.config.ts`; `app.config.ts` values are bundled.
- Use `.env` only for local development; production values come from the host's environment or secret store.

## 3. Data fetching

| API | Use when |
|---|---|
| `useFetch(url, opts)` | A request to one URL whose key can be derived from the URL and options |
| `useAsyncData(key, handler, opts)` | Several calls, a non-HTTP source, or custom keys; the handler returns the data |
| `useLazyFetch`, `useLazyAsyncData` | Navigate immediately and show a pending state instead of blocking |
| `$fetch` | Event handlers, actions and server code, not for initial page data (it would run on server and again on client) |
| `useRequestFetch()` | Forward the incoming request's cookies and headers during SSR |

```vue
<script setup lang="ts">
const route = useRoute()
const id = computed(() => String(route.params.id))

const { data, status, error, refresh } = await useAsyncData(
  () => `item-${id.value}`,
  () => $fetch(`/api/items/${id.value}`),
  { watch: [id] },
)
</script>

<template>
  <p v-if="status === 'pending'">Loading</p>
  <p v-else-if="error">{{ error.message }}</p>
  <p v-else>{{ data?.id }}</p>
</template>
```

- `data` is a shallow ref by default (`deep` defaults to `false` in the Nuxt 4 types). Assign a new value instead of mutating nested fields, or pass `deep: true`.
- `dedupe` defaults to `'cancel'`: a new request for the same key cancels the pending one. `'defer'` keeps the first request and shares its result.
- Use reactive keys or `watch` so a changed param refetches. Reusing a key with different handlers is a bug; keys must be unique per data source.
- `pick` and `transform` reduce what is stored in the payload; large unused fields are serialized into the HTML otherwise.
- `getCachedData(key, nuxtApp, ctx)` customizes cache reuse between navigations.
- Run `await` on `useFetch` and `useAsyncData` at the top level of `<script setup>`; do not call them inside event handlers or timers.
- `status` is `'idle' | 'pending' | 'success' | 'error'`. `error` is a `NuxtError`; `data` is typed `DataT | undefined`, so guard before use.
- `callOnce(() => ...)` runs a function once per server render or navigation, useful for seeding stores.

## 4. Server routes

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

```ts
// server/api/items/[id].get.ts
export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id')
  if (!id || !/^[a-z0-9-]{1,36}$/.test(id)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid id' })
  }
  return { id }
})
```

- The file name sets the method (`.get.ts`, `.post.ts`) and the path (`[id]` is a param). Returned objects are sent as JSON.
- Validate bodies, queries and params with `readValidatedBody`, `getValidatedQuery`, `getValidatedRouterParams` and a schema library (Zod 4.6 is used above; any parser that throws on invalid input works). An invalid body returned `400` in a test build.
- `zod` is an example dependency, not part of Nuxt; add it to the project to use the sample.
- Throw `createError({ statusCode, statusMessage })` for expected failures; do not return stack traces or database errors to clients.
- Authorize inside the handler: read the session from a cookie or header, then filter every read and write by the owner id (`WHERE id = ? AND owner_id = ?`), not only the read.
- Use `useRuntimeConfig(event)` for private values, parameterized queries for databases, and `getRequestIP` / rate limiting for abuse-prone routes (check the current docs for the recommended rate-limit approach).
- Shared logic goes in `server/utils/`, which is auto-imported on the server only and never bundled for the browser.

## 5. Middleware, state and cookies

```ts
// app/middleware/auth.ts
export default defineNuxtRouteMiddleware((to) => {
  const user = useState<{ id: string } | null>('user', () => null)
  if (!user.value) return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
})
```

```vue
<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
</script>
```

- Route middleware runs on the server for the first request and on the client for later navigations. Treat it as UX; enforce access in `server/` handlers.
- `useState(key, init)` is SSR-safe shared state. Do not use a bare module-level `ref` for per-user data; it is shared across requests on the server.
- `useCookie('name', { httpOnly })` cannot set `HttpOnly` from the browser; set session cookies from a server route with `setCookie(event, name, value, { httpOnly: true, secure: true, sameSite: 'lax' })`.
- Pinia works through `@pinia/nuxt`; its version must accept the installed `pinia` (see [pinia-router.md](pinia-router.md)).

## 6. Rendering modes and routeRules

```ts
export default defineNuxtConfig({
  routeRules: {
    '/': { prerender: true },
    '/blog/**': { isr: 3600 },
    '/admin/**': { ssr: false },
    '/api/**': { headers: { 'cache-control': 'no-store' } },
  },
})
```

- `prerender: true` builds the page at build time; `ssr: false` renders the route as an SPA; `isr` and `swr` caching require a host that supports them (check the current docs for your target preset).
- Per-route rules keep a hybrid app in one codebase. Authenticated or per-user pages must never be prerendered or cached by a shared cache.
- Hydration mismatches come from `Date.now()`, `Math.random()`, `window` access, and locale-dependent formatting in the render path. Use `useId()`, `<ClientOnly>`, or compute values in `onMounted`.

## 7. Type checking and linting

```json
{
  "files": [],
  "references": [
    { "path": "./.nuxt/tsconfig.app.json" },
    { "path": "./.nuxt/tsconfig.server.json" },
    { "path": "./.nuxt/tsconfig.shared.json" },
    { "path": "./.nuxt/tsconfig.node.json" }
  ]
}
```

- Run `npx nuxt prepare` to generate `.nuxt/`, then `npx nuxt typecheck` or `npx vue-tsc -b --noEmit`. `vue-tsc` and `typescript` must be installed as dev dependencies. Without the root `tsconfig.json` above, `vue-tsc -b` reports "Cannot read file tsconfig.json".
- Nuxt has an official ESLint module (`@nuxt/eslint`); check the current docs for its flat-config setup before adding it. Without it, use `eslint-plugin-vue` flat configs as in [testing.md](testing.md#6-eslint-and-type-checking).
- Test Nuxt-specific behavior (auto-imports, `useFetch`, server routes) with `@nuxt/test-utils` (latest 4.3.4 on npm at the time of writing); check its docs for the Vitest 5 setup.

## 8. Security notes

- Private runtime keys never go under `public`. Anything in `public`, `app.config.ts`, `NUXT_PUBLIC_*` variables or a `useState` value that was set on the server is visible to every visitor.
- Do not forward arbitrary user-supplied URLs to `$fetch` in server routes (SSRF); allow-list hosts and schemes.
- Sanitize any string rendered with `v-html` (see the SKILL.md security section).
- Set a Content Security Policy without `unsafe-inline`. Nuxt emits inline hydration and payload scripts, so a nonce-based or hash-based policy is needed; check the current docs for the supported CSP option or module in this Nuxt version before choosing one.
- Cookies: `HttpOnly`, `Secure`, `SameSite=Lax` or `Strict`, short lifetime for sessions. Protect state-changing routes against CSRF when using cookie sessions.
