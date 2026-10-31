# SvelteKit Routing, Load, Hooks and Page Options

Route files, params and matchers, layouts, universal and server `load`, streaming, invalidation, page options, hooks, error handling and the `$app/*` modules. Written for SvelteKit 3.1.x; differences from SvelteKit 2 are marked.

## Contents

1. [Route files](#1-route-files)
2. [Params and matchers](#2-params-and-matchers)
3. [Layouts and groups](#3-layouts-and-groups)
4. [Load functions](#4-load-functions)
5. [Streaming and parallel loading](#5-streaming-and-parallel-loading)
6. [Invalidation](#6-invalidation)
7. [Endpoints](#7-endpoints)
8. [Page options](#8-page-options)
9. [Hooks](#9-hooks)
10. [Errors](#10-errors)
11. [App modules](#11-app-modules)
12. [SvelteKit 3 changes at a glance](#12-sveltekit-3-changes-at-a-glance)

## 1. Route files

| File | Runs | Purpose |
|---|---|---|
| `+page.svelte` | server (SSR) and browser | the page component; receives `data` and `form` props |
| `+page.ts` | server and browser | universal `load`, page options |
| `+page.server.ts` | server only | server `load`, form `actions`, page options |
| `+layout.svelte` | server and browser | wraps children; must render `{@render children()}` |
| `+layout.ts` / `+layout.server.ts` | as above | layout `load` and options |
| `+server.ts` | server only | HTTP handlers `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`, `fallback` |
| `+error.svelte` | server and browser | error page for the nearest segment; receives `error` with `status` and `message` |

- A route directory needs a `+page` or `+server` file to be routable. Files whose names include `test`, `spec` or `stories` after the `+` prefix are ignored by the router in SvelteKit 3.
- Page components in runes mode: `let { data, form }: PageProps = $props();`.

## 2. Params and matchers

```text
src/routes/blog/[slug]/+page.svelte           /blog/hello
src/routes/files/[...path]/+page.svelte       /files/a/b/c
src/routes/[[lang]]/about/+page.svelte        /about and /de/about
src/routes/items/[id=integer]/+page.svelte    id passes the "integer" matcher
src/routes/(app)/dashboard/+page.svelte       group folder: not part of the URL
```

SvelteKit 3 declares all matchers in one file, `src/params.ts` (the old one-file-per-matcher `src/params/` directory is gone):

```ts
// src/params.ts
import { defineParams } from '@sveltejs/kit/params';
import * as v from 'valibot';

export const params = defineParams({
  integer: v.pipe(v.string(), v.toNumber()),               // Standard Schema variant
  fruit: (param) => (param === 'apple' || param === 'orange' ? param : undefined)
});
```

- A function matcher returns the parsed value or `undefined` when the param does not match; a Standard Schema must output `string`, `boolean`, `number` or `bigint`. A failed match falls through to other routes and then 404.
- Parsed values arrive typed in `params`. Transformations should be symmetrical so `resolve('/items/[id=integer]', { id: 1 })` can rebuild the URL.

## 3. Layouts and groups

```svelte
<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import { page, navigating } from '$app/state';
  let { children } = $props();
</script>

<nav aria-label="Main">
  <a href="/" aria-current={page.url.pathname === '/' ? 'page' : undefined}>Home</a>
</nav>

{#if navigating.to}<p role="status">Loading</p>{/if}

<main>{@render children()}</main>
```

- Do not rely on a layout `load` alone for authorization: form actions and endpoints are reached by direct POST. Check in each.

## 4. Load functions

```ts
// src/routes/blog/[slug]/+page.server.ts
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import * as db from '#lib/server/db.js';

export const load: PageServerLoad = async ({ params, locals, setHeaders, depends }) => {
  depends('app:post');
  const post = await db.getPost(params.slug, locals.user?.id);
  if (!post) error(404, 'Post not found');
  setHeaders({ 'cache-control': 'public, max-age=60' });
  return { post };
};
```

| | Universal (`+page.ts`) | Server (`+page.server.ts`) |
|---|---|---|
| Runs | server on first load, browser on client navigation | server only (browser calls it through an internal request) |
| Input | `params`, `url`, `route`, `fetch`, `data`, `parent`, `depends`, `setHeaders`, `untrack` | the same plus `locals`, `cookies`, `request`, `platform`, `getClientAddress` |
| Output | any value (classes, functions allowed) | must be serialisable by devalue |
| Use for | public APIs, browser-only SDKs, returning components | databases, secrets, private env, session cookies |

- Both can exist for one route: the server `load` result arrives as `data` in the universal `load`.
- Always use the `fetch` argument. It forwards cookies and `Authorization` for same-origin requests on the server, resolves relative URLs, and inlines responses into the HTML so hydration does not refetch.
- Cookies: `cookies.get/set/delete/serialize`. Set `httpOnly`, `secure`, `sameSite` for sessions. SvelteKit 3 defaults the cookie `path` to `/` and requires ASCII cookie names.
- `await parent()` returns merged data from layouts above; call it after starting other requests, not before, to avoid waterfalls.
- `getRequestEvent()` from `$app/server` returns the current server event inside helper functions called from `load`, actions and remote functions, which keeps auth guards such as `requireLogin()` argument free.
- Errors: `error(404, 'Not found')` renders the nearest `+error.svelte`; `redirect(303, '/login')` redirects. In SvelteKit 3 the message is the second argument and extra `App.Error` fields go in a third; external redirects are blocked by default.

## 5. Streaming and parallel loading

```ts
export const load: PageServerLoad = async ({ params }) => {
  return {
    comments: loadComments(params.slug), // not awaited: streamed when it resolves
    post: await loadPost(params.slug)    // awaited: needed for first paint
  };
};
```

```svelte
{#await data.comments}
  <p>Loading comments</p>
{:then comments}
  {#each comments as c (c.id)}<p>{c.text}</p>{/each}
{:catch}
  <p>Could not load comments.</p>
{/await}
```

- Streaming works from server `load`. Start slow promises before awaiting fast ones. Streamed promises need `{#await}` handling for rejections, or the error surfaces as an unhandled rejection.
- Streaming needs a platform that does not buffer responses; check the adapter and any proxy in front of the app. Prerendered pages cannot stream.

## 6. Invalidation

- A `load` reruns when a value it read from `params`, `url` (including individual `searchParams`), `route` changes, when a `fetch` URL or `depends()` key it used is invalidated, or after `invalidate*`/`refreshAll`.
- `invalidate('app:post')` or `invalidate((url) => ...)` targets keys; `invalidateAll()` is deprecated in SvelteKit 3 in favour of `refreshAll()` from `$app/navigation`, which also refreshes remote queries and does not reset `page.state`.
- After a successful enhanced form action, `update()` refreshes data by default; pass `update({ refreshAll: false })` to skip it and `update({ reset: false })` to keep field values (the older `invalidateAll` option is deprecated).
- Opt out of tracking with `untrack(() => url.pathname)`.

## 7. Endpoints

```ts
// src/routes/api/items/+server.ts
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import * as v from 'valibot';
import * as db from '#lib/server/db.js';

const Body = v.object({ name: v.pipe(v.string(), v.minLength(1), v.maxLength(100)) });

export const POST: RequestHandler = async ({ request, locals }) => {
  if (!locals.user) error(401, 'Sign in required');
  const parsed = v.safeParse(Body, await request.json());
  if (!parsed.success) error(400, 'Invalid body');
  const item = await db.createItem(locals.user.id, parsed.output.name);
  return Response.json(item, { status: 201 });
};
```

- Return a standard `Response`. The `json()` and `text()` helpers are deprecated in SvelteKit 3; `Response.json()` works everywhere.
- Cross-origin mutating requests are checked by the CSRF origin check; add trusted origins with `csrf.trustedOrigins`. Requests without a `Content-Type` header from other origins are rejected.

## 8. Page options

```ts
// +layout.ts or +layout.server.ts or +page.ts
export const prerender = true;       // true | false | 'auto'
export const ssr = true;
export const csr = true;
export const trailingSlash = 'never'; // 'never' | 'always' | 'ignore'
export const entries = () => [{ slug: 'a' }, { slug: 'b' }]; // dynamic prerender targets
```

- `prerender = true` renders at build time. A prerendered route cannot use `url.searchParams`, `cookies` or form actions at request time. `'auto'` prerenders but keeps the route in the SSR manifest.
- `csr = false` ships no JavaScript for the page: forms need to work as plain POSTs, and `onMount`, `use:enhance` and client routing are disabled.
- `export const config = { ... }` is adapter specific (runtime, regions, memory); top-level keys merge across layouts.

## 9. Hooks

```ts
// src/hooks.server.ts
import type { Handle, HandleServerError, HandleFetch, ServerInit } from '@sveltejs/kit/hooks';
import { sequence } from '@sveltejs/kit/hooks';
import * as auth from '#lib/server/auth.js';

export const init: ServerInit = async () => { /* open db pool once */ };

const authenticate: Handle = async ({ event, resolve }) => {
  event.locals.user = await auth.userFromCookie(event.cookies.get('session'));
  return resolve(event);
};

const securityHeaders: Handle = async ({ event, resolve }) => {
  const response = await resolve(event);
  response.headers.set('x-content-type-options', 'nosniff');
  return response;
};

export const handle = sequence(authenticate, securityHeaders);

export const handleFetch: HandleFetch = async ({ request, fetch }) => fetch(request);

export const handleError: HandleServerError = ({ error, event, status, message }) => {
  console.error(error);
  return { message: status === 500 ? 'Internal Error' : message };
};
```

- In SvelteKit 3 hook types come from `@sveltejs/kit/hooks` (SvelteKit 2: `@sveltejs/kit`). `resolve` is typed as returning a Promise.
- `handle` also sees prerender requests and remote function requests. For remote functions, `event.url`, `event.route` and `event.params` describe the calling page; do not authorize on them.
- `handleError` runs for every error in SvelteKit 3, including expected `error()` calls. It receives a `kind` (`app`, `framework`, `validation`, `unknown`) and may return `status` to change the response code. Validation errors from remote functions arrive here with `kind: 'validation'`; `handleValidationError` no longer exists.
- `handleFetch` rewrites server-side `fetch` calls made in `load` and actions, for example to hit an internal service URL. Never forward user cookies to third-party origins.
- `reroute` (in `src/hooks.ts`, runs on server and client) maps incoming URLs to route paths without changing the browser URL. Keep it pure and fast; a malformed rewritten pathname returns 400 in SvelteKit 3.1.1.
- `transport` (in `src/hooks.ts`) registers `encode`/`decode` pairs so custom classes cross the server/client boundary in `load` data and remote function values.

## 10. Errors

- Expected errors: `error(status, message)`; rendered by `+error.svelte` with `status` and `message`. SvelteKit 3 guarantees `App.Error` has a `status`.
- Errors during rendering in SvelteKit 3 pass through `handleError` and then the nearest boundary; each `+error.svelte` becomes an error boundary. An async `handleError` in `hooks.client.ts` needs the experimental async compiler option.
- Form actions return `fail(status, data)` for validation problems; that status is the real HTTP status for enhanced submissions in SvelteKit 3.

## 11. App modules

| Module | Exports |
|---|---|
| `$app/state` | `page` (url, params, route, status, error, data, form, state), `navigating`, `updated` |
| `$app/navigation` | `goto`, `invalidate`, `invalidateAll` (deprecated), `refreshAll`, `preloadData`, `preloadCode`, `beforeNavigate`, `onNavigate`, `afterNavigate`, `disableScrollHandling` |
| `$app/forms` | `enhance`, `applyAction`, `deserialize` and the `ActionResult`, `SubmitFunction` types |
| `$app/paths` | `resolve`, `asset` (SvelteKit 3); `base`/`assets` removed |
| `$app/server` | `getRequestEvent`, `read`, remote function builders `query`, `form`, `command`, `prerender` |
| `$app/env` | `browser`, `dev`, `building`, `version` (replaces `$app/environment`) |
| `$app/env/private`, `$app/env/public` | variables declared in `src/env.ts` |
| `$app/manifest` | `immutable`, `assets`, `prerendered`, `routes` (SvelteKit 3) |
| `@sveltejs/kit` | `error`, `redirect`, `fail`, `isHttpError`, `isRedirect`, `isActionFailure`, `invalid`, `Response` helpers |

- `goto(url, { shallow: true, state })` replaces `pushState` and `replaceState` for shallow routing in SvelteKit 3; its `replace`, `reset` and `refreshAll` options replace `replaceState`, `keepFocus`/`noScroll` and `invalidateAll`.

## 12. SvelteKit 3 changes at a glance

- Requirements: Node >=22.17, TypeScript 6, Svelte >=5.57.1, Vite >=8.0.12, vite-plugin-svelte 7.
- Config moves from `svelte.config.js` into `sveltekit({ ... })` in `vite.config.js`.
- `$lib` becomes `#lib` via `package.json` `imports`; extensions are required in imports.
- `$app/stores` removed; `$app/environment` renamed `$app/env`; `$env/*` deprecated in favour of `$app/env/private|public`.
- `$service-worker` removed; use `$app/service-worker`, `$app/manifest`, `$app/paths`.
- Types moved: hooks types to `@sveltejs/kit/hooks`, env types to `@sveltejs/kit/env`, `defineParams` to `@sveltejs/kit/params`, `Page`/navigation types to `$app/state` and `$app/navigation`.
- `csrf.checkOrigin` replaced by `csrf.trustedOrigins`; `paths.origin` replaces `prerender.origin` and adapter-node `ORIGIN`.
- Run `npx sv migrate sveltekit-3` on a SvelteKit 2 project after upgrading to the latest 2.x; it has prerequisite tasks (`package-json`, `tsconfig`) and selectable ones (`svelte-config`, `environment`, and others listed by the command).
