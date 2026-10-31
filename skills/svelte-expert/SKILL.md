---
name: svelte-expert
description: >-
  Builds, reviews and migrates Svelte 5 and SvelteKit 3 apps: runes, snippets, event attributes, context, reactive .svelte.ts modules, routing and load functions, form actions with use:enhance, experimental remote functions, hooks, env modules, adapters and Vitest tests. Use when editing .svelte files, +page.ts, +page.server.ts, +layout.svelte, +server.ts, hooks.server.ts or vite.config.js, running sv create, sv add or sv migrate, or fixing reactivity, hydration and SSR errors. Not for React (use senior-react-19-engineer), Vue (use vue-expert), Tailwind setup (use tailwindcss-master), data-fetching libraries (use tanstack-state-expert) or e2e test design (use playwright-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Svelte Expert

This skill covers application work in Svelte 5 (runes mode) and SvelteKit 3: component syntax, reactive state, routing, data loading, forms, remote functions, hooks, environment variables, deployment adapters and testing. It also covers migration from Svelte 4 and SvelteKit 2 with the `sv` CLI. Styling systems, React and Vue, data-fetching libraries and end-to-end test design belong to other skills.

> Verified against Svelte 5.57.3, SvelteKit 3.1.1, sv 1.1.1, @sveltejs/vite-plugin-svelte 7.3.1, Vite 8 (peer range ^8.0.12), Vitest 5.0.5, @testing-library/svelte 5.4.2, vitest-browser-svelte 3.1.0, @playwright/test 1.64.1, @sveltejs/adapter-auto 8.0.0, adapter-node 6.0.1, adapter-static 4.0.1, adapter-vercel 7.0.2, adapter-cloudflare 8.0.2 (npm registry, package changelogs and the official docs sources, 2026-10).

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

- Covered: `.svelte` and `.svelte.js/.svelte.ts` files, runes, snippets, context, `svelte/reactivity`, `<svelte:boundary>`, `await` expressions, SvelteKit routing, `load`, form actions, remote functions, hooks, `$app/*` modules, env modules, page options, adapters, `sv create/add/migrate/check`, Vitest component tests, accessibility compiler warnings.
- Not covered: React (senior-react-19-engineer), Vue (vue-expert), Tailwind configuration and design tokens (tailwindcss-master), client data-fetching and caching libraries (tanstack-state-expert), end-to-end test design and Playwright patterns (playwright-expert, e2e-testing-expert), general TypeScript typing (typescript-master), container images (docker-expert), site-wide accessibility audits (accessibility-expert).
- Legacy Svelte 4 syntax (`export let`, `$:`, `on:click`, slots, stores) still compiles in Svelte 5 outside runes mode. Treat it as migration input, not as the target style.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | Svelte 5.57.x and SvelteKit 3.1.x are current. SvelteKit 3 requires Node >=22.17, TypeScript 6, Svelte >=5.57.1, Vite >=8.0.12 and `@sveltejs/vite-plugin-svelte` 7. Svelte 6 had not shipped at the time of checking (latest on npm was 5.57.3); the docs say the `experimental.async` flag will be removed in Svelte 6 |
| Runes | `$state`, `$state.raw`, `$state.snapshot`, `$state.eager`, `$derived`, `$derived.by`, `$effect`, `$effect.pre`, `$effect.root`, `$effect.tracking`, `$props`, `$props.id()`, `$bindable`, `$inspect`, `$host`. Runes are compiler syntax, not imports, and work in `.svelte` and `.svelte.js/.svelte.ts` files |
| Templates | `{#snippet name(args)}` plus `{@render name(args)}` replace slots; `children` is the implicit default snippet prop. Events are plain attributes (`onclick`, `oninput`); `{@attach fn}` attachments are the successor to many actions; declaration tags `{const x = ...}` (5.56+) supersede `{@const}` |
| Context | `createContext<T>()` (Svelte 5.40+) returns a `[get, set]` pair typed end to end; 5.57 added a `has` function to the result. `setContext/getContext` with a key still work. Context must be set during component initialisation |
| Reactive classes | Class fields declared with `$state`/`$derived` become reactive properties. `svelte/reactivity` ships `SvelteMap`, `SvelteSet`, `SvelteDate`, `SvelteURL`, `SvelteURLSearchParams`, `MediaQuery`, `createSubscriber` and a window-state module |
| Async | `await` in `<script>` top level, in `$derived(...)` and in markup (since 5.36) is experimental behind `compilerOptions.experimental.async`. Pair with `<svelte:boundary pending>` and `failed` snippets |
| Routing | Files under `src/routes`: `+page.svelte`, `+page.ts`, `+page.server.ts`, `+layout.svelte`, `+layout.ts`, `+layout.server.ts`, `+server.ts`, `+error.svelte`. Params: `[id]`, `[[optional]]`, `[...rest]`, matchers, `(group)` folders |
| Data | Universal `load` (`+page.ts`) runs on server and client; server `load` (`+page.server.ts`) runs only on the server and may use secrets and databases. Return values are serialised with devalue (Date, Map, Set, BigInt allowed; class instances are not without a `transport` hook) |
| Forms | `export const actions` in `+page.server.ts`, `fail()`, `redirect()`, `use:enhance` from `$app/forms`, `form` prop and `page.form`. Works without JavaScript |
| Remote functions | `query`, `query.batch`, `query.live`, `form`, `command`, `prerender` from `$app/server`, in `*.remote.ts` files. Still experimental in 3.1: needs `experimental.remoteFunctions` in the `sveltekit()` plugin options and `compilerOptions.experimental.async` |
| Hooks | `handle`, `handleFetch`, `handleError` (server and client), `init`, `reroute`, `transport`. In SvelteKit 3 hook types come from `@sveltejs/kit/hooks`; `handleError` receives a `kind` of `app`, `framework`, `validation` or `unknown` |
| Config | SvelteKit 3 no longer reads `svelte.config.js`: options go into `sveltekit({ ... })` in `vite.config.js` (`adapter`, `compilerOptions`, `csrf`, `paths`, `experimental`, ...) |
| Env | New explicit model: declare variables in `src/env.ts` with `defineEnvVars` from `@sveltejs/kit/env`; import from `$app/env/private` or `$app/env/public`. `$env/static/*`, `$env/dynamic/*` and `$app/environment` still work as deprecated aliases and go away in SvelteKit 4 |
| Aliases | `$lib` is gone in SvelteKit 3. Declare `#lib` in `package.json` `imports` (`"#lib": "./src/lib/index.js"`, `"#lib/*": "./src/lib/*"`) and import with file extensions. SvelteKit 2 projects still use `$lib` |
| State modules | `$app/state` (`page`, `navigating`, `updated`) replaces `$app/stores`, which SvelteKit 3 removed. Read `page.url.pathname`, not `$page.url.pathname` |
| CLI | `npx sv create`, `npx sv add <addon>` (eslint, prettier, vitest, playwright, tailwindcss, drizzle, better-auth, paraglide, mdsvex, storybook, sveltekit-adapter, enhanced-img, ai-tools), `npx sv check`, `npx sv migrate <name>` (`svelte-5`, `sveltekit-3`, `sveltekit-2`, `svelte-4`, `self-closing-tags`) |
| Adapters | adapter-auto (default, picks Vercel, Netlify, Cloudflare), adapter-node, adapter-static, adapter-vercel, adapter-cloudflare, adapter-netlify; adapter-bun is documented as well. Options live in the `adapter` call |

## 3. Workflow

1. Read `package.json`, `vite.config.*`, `svelte.config.*` (if present), `src/hooks.*`, `src/app.d.ts` and the lockfile. Establish the Svelte and SvelteKit majors before suggesting syntax: SvelteKit 2 uses `svelte.config.js`, `$lib`, `$env/*`; SvelteKit 3 uses the Vite plugin options, `#lib`, `$app/env/*`.
2. Check whether components use runes. A component that uses any rune is in runes mode; mixing `$:` or `export let` into it is a compile error.
3. Reproduce with the project scripts (`npm run dev`, `npm run check`, `npm run test`, `npm run build && npm run preview`). Many SSR and adapter problems appear only after a build.
4. Decide where code runs: browser only, server only, or both. Put secrets, database clients and private env imports in `+page.server.ts`, `+server.ts`, `hooks.server.ts` or a `server/` directory.
5. Make the smallest change. Prefer a native form action or `load` before reaching for client-side fetches or remote functions.
6. Run `npx sv check` (svelte-check), the linter, unit and component tests, then a production build with the target adapter. Report which commands ran.
7. For upgrades, commit first, run `npx sv migrate <name>`, read the full diff, and fix what the codemod reports as manual work.

## 4. Decision Rules

- If state is only used inside one component, use `$state` there; if it is shared between components, put it in a `.svelte.ts` module or class; if it is tree-scoped (per request or per subtree), use context. Never keep per-request data in module-level state on the server: modules are shared across requests.
- If an object is large and replaced wholesale (API response, parsed file), use `$state.raw`; if you mutate fields or push to arrays, use `$state` (deep proxy). Use `$state.snapshot(x)` before passing a proxy to `structuredClone`, `postMessage` or a library.
- If a value can be computed from other state, use `$derived` or `$derived.by`. Do not write to state inside `$effect` to keep two values in sync. Use `$effect` only for side effects against the outside world (DOM APIs, timers, subscriptions, logging); the return function is the teardown.
- If a child must notify its parent, accept a callback prop (`onsave`). Do not use `createEventDispatcher` (deprecated). If the parent must write into the child, use `$bindable` and `bind:`, sparingly.
- If content is passed into a component, use `children` or named snippet props (`header`, `row`), and declare their types with `Snippet<[Args]>` from `svelte`.
- If data is needed to render a route, use `load`. If it needs secrets, a database, or private env, use `+page.server.ts`. If it must run client-side on navigation (browser-only API, third-party SDK), use `+page.ts`.
- If a page changes data, prefer a form action (`<form method="POST">` with `use:enhance`). Use `+server.ts` for JSON APIs consumed by other clients, webhooks and file downloads.
- If the team accepts experimental APIs and wants colocated typed server calls, use remote functions (`query`, `form`, `command`); otherwise use `load` and form actions. Remote functions can change without notice; pin SvelteKit exactly when relying on them.
- If a route is the same for everyone, set `export const prerender = true`; if it needs per-request data, keep SSR. Use `ssr = false` only for pages that cannot render on a server (SPA pages), and treat it as a trade-off for first paint and SEO.
- If you deploy to a known platform, install that adapter explicitly instead of relying on adapter-auto. Use adapter-static only when every route is prerendered or a SPA `fallback` is configured.
- If a store from `svelte/store` is part of a library API, keep it; for new app code use runes. Mixed use is fine: `$store` auto-subscription still works in components.
- If an accessibility warning (`a11y_*`) appears, fix the markup. Add a `<!-- svelte-ignore a11y_... -->` comment only with a written reason.

## 5. Coding Standards

- Use runes mode for all new components; enable it project wide with `compilerOptions: { runes: true }` in the plugin options once all dependencies support it.
- Declare props with a single destructuring: `let { title, items = [], onselect, ...rest }: Props = $props();`. Type `Props` as an interface in `<script lang="ts">`.
- Use event attributes: `onclick={handler}`. Modifiers such as `|preventDefault` no longer exist; call `event.preventDefault()` in the handler. Spread `{...rest}` can carry handlers.
- Use `bind:value`, `bind:checked`, `bind:group`, `bind:this` for form state and element refs; keep `bind:this` refs `$state(null)` and use them only after mount.
- Each blocks need a key when items reorder or hold state: `{#each items as item (item.id)}`.
- Name reactive module files `*.svelte.ts` (or `.svelte.js`); runes do not compile in plain `.ts`. Export objects or classes with getters, not bare reassigned `let` values (a module-level `export let count = $state(0)` cannot be reassigned by importers).
- Use `import type` and `satisfies` where it helps; `verbatimModuleSyntax` is on in the generated tsconfig. Types for `load` and actions come from the generated `./$types` (`PageLoad`, `PageServerLoad`, `Actions`, `PageProps`).
- In SvelteKit 3, extend `$app/tsconfig` in `tsconfig.json` (with `include` and `exclude` arrays) rather than `./.svelte-kit/tsconfig.json`.
- Use `resolve()` and `asset()` from `$app/paths` for base-aware URLs; `base`, `assets` and `resolveRoute` were removed in SvelteKit 3.
- Use `Response.json(...)` in `+server.ts`; the `json()` and `text()` helpers from `@sveltejs/kit` are deprecated in 3.
- Throw errors with `error(status, message)` (message is a string) and redirect with `redirect(status, location)`; both are called, not thrown, in current SvelteKit. External redirects are blocked by default in SvelteKit 3.

## 6. Project Structure

```text
my-app/
  package.json            # "imports": { "#lib": ..., "#lib/*": ... } in SvelteKit 3
  vite.config.ts          # sveltekit({ adapter, compilerOptions, csrf, paths, ... })
  tsconfig.json           # extends "$app/tsconfig"
  src/
    app.html              # page shell with %sveltekit.head% and %sveltekit.body%
    app.d.ts              # App.Locals, App.PageData, App.Error, App.Platform
    env.ts                # defineEnvVars({ ... }) declarations
    hooks.server.ts       # handle, handleFetch, handleError, init
    hooks.client.ts       # client handleError, init
    hooks.ts              # reroute, transport
    params.ts             # defineParams matchers (SvelteKit 3)
    lib/
      components/         # shared .svelte components
      state/              # *.svelte.ts reactive modules and classes
      server/             # server-only code: db, auth, mail
    routes/
      +layout.svelte
      +page.svelte
      blog/
        [slug]/
          +page.server.ts
          +page.svelte
      api/
        health/+server.ts
  static/                 # copied as is
  tests/                  # Playwright specs; unit tests sit next to sources
```

- Files in any `server/` directory (outside `src/routes` and the assets dir) and `*.server.ts` files cannot be imported into browser code; the build fails if that happens.
- Files starting with `+` that contain `test`, `spec` or `stories` in the name are ignored by the router in SvelteKit 3.
- A `.remote.ts` file (name contains a `remote` segment) is a remote module and cannot live in a `server/` directory.

## 7. Design Patterns

- **Reactive class**: `class Cart { items = $state<Item[]>([]); total = $derived(this.items.reduce((s, i) => s + i.price, 0)); add(i: Item) { this.items.push(i); } }` in a `.svelte.ts` file. Cost: methods passed as callbacks lose `this`; use arrow properties or `() => cart.add(i)`.
- **Context-scoped store**: create the instance in the root layout, publish it with `createContext`, and read it in descendants. This avoids cross-request leaks on the server that a module singleton would cause.
- **Callback props over events**: `onsave`, `onclose`, `onchange` with typed signatures. Easy to forward through `{...rest}`.
- **Snippet-based composition**: generic list components take `row: Snippet<[T]>` and `empty?: Snippet`; the parent decides markup. Snippets can also be exported from `<script module>`.
- **Layout data**: shared data (session user, feature flags) is loaded once in `+layout.server.ts`; child `load` functions call `await parent()` only when they need it, since it serialises waterfalls.
- **Progressive enhancement**: write the form so it works as a plain POST, add `use:enhance` for in-place updates and pending UI, and return `fail(400, { values, errors })` to repopulate fields.
- **Hooks as the trust boundary**: authenticate in `handle`, put the user in `event.locals`, and re-check authorization inside every server `load`, action, endpoint and remote function. Layout `load` does not protect child routes from direct action POSTs.
- **Error boundaries**: wrap risky subtrees in `<svelte:boundary>` with a `failed` snippet; use `+error.svelte` for route-level errors.

## 8. Best Practices

- Keep `$effect` rare. Before adding one, check whether `$derived`, an event handler, an attachment, a snippet or `{#await}` expresses the same thing declaratively.
- Read state before an `await` inside an effect or derived if it must be a dependency: reads after the first `await` are not tracked.
- Use `untrack(() => ...)` to read state without subscribing; use `$effect.pre` only for work that must run before DOM updates (scroll position preservation).
- Mutate `$state` objects and arrays in place (`items.push(x)`) or reassign; both work for deep state. For `$state.raw`, always reassign.
- Do not destructure reactive objects when you need to keep reactivity (`let { count } = counter` copies the value). Use getters or `$derived`.
- Pass reactive values across function boundaries as functions or objects with getters: `useTimer(() => interval)`.
- Prefer `onclick` on real `<button>` and `<a>` elements. Adding handlers to `div` triggers `a11y_click_events_have_key_events` and `a11y_no_static_element_interactions`.
- Use `page` from `$app/state` for current URL, params, status, form and error; use `navigating` for pending navigation UI.
- Use `<svelte:head>` for per-page `<title>` and meta tags; every page needs a title.
- Use `data-sveltekit-preload-data="hover"` (already in the default `app.html`) and `data-sveltekit-reload` to opt single links out of client routing.
- Keep `load` functions free of side effects other than `setHeaders`; use the provided `fetch` so cookies and relative URLs resolve and responses are inlined into the SSR payload.
- Call `depends('app:thing')` or rely on tracked `url`/`params` reads, then `invalidate('app:thing')` or `refreshAll()` (SvelteKit 3; `invalidateAll` is deprecated) to re-run loads.

## 9. Performance

- Svelte compiles to targeted DOM updates; typical wins come from less work, not micro-tuning: fewer effects, smaller payloads, keyed each blocks, no giant deep-proxied arrays (use `$state.raw` for read-mostly data).
- Stream slow, non-critical data from server `load` by returning an un-awaited promise inside an object; await only what the first paint needs. Beware that a rejected streamed promise needs a handler in the template (`{#await}` or `<svelte:boundary>`).
- Run independent requests in parallel with `Promise.all`; avoid `await parent()` before them.
- Prerender everything that can be static; use `prerender` remote functions for static data on otherwise dynamic pages.
- Use `@sveltejs/enhanced-img` (`npx sv add enhanced-img`) for responsive images; set `width`/`height` to avoid layout shift.
- Code splitting is per route. Load heavy client-only libraries with dynamic `import()` inside `onMount` or an event handler.
- Check bundle size with `vite build` output and a visualizer plugin before and after dependency changes.
- SvelteKit 3 emits `<link rel="modulepreload">` elements by default; `output.linkHeaderPreload` switches to `Link` headers, which can overflow header limits on large apps.

## 10. Security

- Never import `$app/env/private`, `$env/static/private`, `$env/dynamic/private`, `*.server.ts` modules or `server/` directory code from client code. SvelteKit fails the build when it detects this; do not work around it by re-exporting.
- Only variables declared `public: true` (or, in the legacy modules, prefixed `PUBLIC_`) are exposed to the browser. Treat everything in `$app/env/public` as visible to every visitor.
- Validate every remote function, form action and `+server.ts` input on the server with a schema library (Valibot, Zod or any Standard Schema implementation). Client checks are convenience only.
- Authenticate in `handle`; check authorization in each server entry point. In remote functions and `handle`, `event.url`, `route` and `params` describe the calling page, not the endpoint, so never base authorization on them.
- CSRF: form submissions are checked against the origin. SvelteKit 3 removed `csrf.checkOrigin`; allow extra origins with `csrf.trustedOrigins`, and set `paths.origin` when behind a reverse proxy.
- `{@html}` renders raw HTML. Sanitize with a vetted library on the server or avoid it for user content. Do not interpolate user input into `href` values with a `javascript:` scheme.
- Cookies: set `httpOnly`, `secure` and `sameSite` explicitly for session cookies. `cookies.set` requires a `path` in SvelteKit 2 and defaults it to `/` in 3.
- Return generic messages from `handleError`; log details server side. Never return stack traces or `issues` from validation unless intended.
- Set CSP through the `csp` plugin option (with nonces or hashes) rather than hand-written headers when using inline scripts.
- Do not put secrets in `+page.ts` or `+layout.ts`: universal load results and code ship to the browser.

## 11. Testing

- Unit tests of `.svelte.ts` modules and pure functions: Vitest. `npx sv add vitest` (with `usages:unit,component` for both kinds) installs the packages, adds scripts and a client/server-aware setup in the Vite config; read the generated config.
- Component tests: Vitest with `@testing-library/svelte` (jsdom or happy-dom, with the `browser` resolve condition, per the Svelte testing docs) or Vitest browser mode with the `vitest-browser-svelte` package. Check each package's README for the current setup.
- Test files that use runes must be named `*.svelte.test.ts` (or `.svelte.js`) so the compiler processes them. Wrap effects in `$effect.root` and call `flushSync()` from `svelte` to apply updates before asserting.
- Wrapper components are the reliable way to test context, snippets and bindable props: render a small test component that supplies them.
- Load functions and actions are plain functions: call them with a hand-built event (`{ locals, params, fetch, url, request, cookies }` as needed) or test through Playwright.
- End-to-end: `npx sv add playwright` adds `@playwright/test`, a config and a demo test; check that the generated `webServer` entry builds and previews the app. Test against the production build, not only `dev`. For test design see playwright-expert.
- Run `npx sv check` in CI; it reports TypeScript errors, template type errors and a11y warnings.
- Mock `$app/*` modules only when unavoidable; prefer testing pure logic outside SvelteKit imports.

## 12. Review Checklist

- Components use runes; no `$:`, `export let`, `on:click`, `<slot>` or `createEventDispatcher` in new code.
- No `$effect` that only copies state into other state.
- `$state` is not read after `await` where tracking is expected; `$state.raw` objects are reassigned, not mutated.
- Each blocks have keys when the list can reorder.
- Server-only imports stay out of client files; private env is not referenced in `+page.ts` or components.
- Every action, endpoint and remote function validates input and checks authorization.
- `fail()` returns values for repopulation but never passwords or tokens.
- Forms work with JavaScript disabled; `use:enhance` is an addition.
- `load` uses the provided `fetch`; no module-level mutable state holds per-request data.
- Links use `<a href>`; buttons are `<button>`; images have `alt`; inputs have labels; no a11y warnings are silenced without a reason.
- Page options (`prerender`, `ssr`, `csr`, `trailingSlash`) match the adapter.
- `sv check`, tests and a production build pass with the real adapter.

## 13. Production Notes

- adapter-node: `npm run build` writes `build/`; run `node build`. It reads `PORT`, `HOST`, `SOCKET_PATH`, `BODY_SIZE_LIMIT`, `SHUTDOWN_TIMEOUT` and proxy header variables (`PROTOCOL_HEADER`, `HOST_HEADER`, `PORT_HEADER`, `ADDRESS_HEADER`, `XFF_DEPTH`); set the header variables only behind a trusted proxy; in SvelteKit 3 the `ORIGIN` variable is gone, use `paths.origin`. Static assets are served from a list recorded at build time. The adapter shuts down gracefully on SIGTERM and SIGINT; add a health endpoint.
- adapter-static: set `prerender = true` in the root layout; for SPA mode set the adapter option `fallback` (commonly `200.html`, not `index.html`) and `ssr = false` in the root layout. Dynamic routes need `entries` or crawlable links.
- adapter-vercel: the `edge` runtime is no longer supported in SvelteKit 3; set `runtime` (for example `'nodejs22.x'`), `regions` and `maxDuration` through the adapter or route `config`; check the adapter docs for supported runtime strings.
- adapter-cloudflare: in SvelteKit 3 use `import { env, waitUntil } from 'cloudflare:workers'` instead of `platform.env`; install `wrangler` (>=4.67) and run `wrangler types`. `cf` lives on `request.cf`.
- Version skew: SvelteKit 3 polls for new deployments (`version.pollInterval` defaults to one hour) and sets `updated.current`; use it to prompt a reload or let navigation fall back to a full page load.
- Observability: add `src/instrumentation.server.js` and `tracing: { server: true }` in plugin options for OpenTelemetry spans.
- Sourcemaps are on by default in SvelteKit 3; upload them to the error tracker and do not serve them publicly unless intended.
- Run `npm ci`, `npm run check`, `npm test`, `npm run build` in CI with the same Node version as production (>=22.17 for SvelteKit 3).

## 14. Examples

Runes component with callback prop and snippet:

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    items: { id: string; label: string }[];
    onselect?: (id: string) => void;
    empty?: Snippet;
  }

  let { items, onselect, empty }: Props = $props();
  let query = $state('');
  const visible = $derived(
    items.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()))
  );
</script>

<label>
  Filter
  <input bind:value={query} />
</label>

<ul>
  {#each visible as item (item.id)}
    <li><button type="button" onclick={() => onselect?.(item.id)}>{item.label}</button></li>
  {:else}
    {#if empty}{@render empty()}{:else}<li>No matches</li>{/if}
  {/each}
</ul>
```

Server `load` plus form action with `use:enhance`:

```ts
// src/routes/todos/+page.server.ts
import { fail, error } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import * as db from '#lib/server/db.js';

export const load: PageServerLoad = async ({ locals }) => {
  if (!locals.user) error(401, 'Sign in required');
  return { todos: await db.listTodos(locals.user.id) };
};

export const actions: Actions = {
  add: async ({ request, locals }) => {
    if (!locals.user) error(401, 'Sign in required');
    const form = await request.formData();
    const title = String(form.get('title') ?? '').trim();
    if (!title) return fail(400, { title, missing: true });
    await db.addTodo(locals.user.id, title);
    return { success: true };
  }
};
```

```svelte
<!-- src/routes/todos/+page.svelte -->
<script lang="ts">
  import { enhance } from '$app/forms';
  let { data, form } = $props();
  let pending = $state(false);
</script>

<form
  method="POST"
  action="?/add"
  use:enhance={() => {
    pending = true;
    return async ({ update }) => {
      await update();
      pending = false;
    };
  }}
>
  <input name="title" value={form?.title ?? ''} aria-invalid={form?.missing} />
  <button disabled={pending}>Add</button>
</form>

<ul>
  {#each data.todos as todo (todo.id)}<li>{todo.title}</li>{/each}
</ul>
```

More runnable patterns (reactive classes, context, remote functions, hooks, env, tests) are in the reference files.

## 15. Common Mistakes

- Using `$state` in a plain `.ts` file: the rune is not compiled. Rename to `.svelte.ts`.
- Exporting a reassigned module-level `$state` primitive; importers cannot assign to it. Export an object or class.
- Reading state after `await` inside `$derived.by` or `$effect` and expecting a dependency.
- Mutating a `$state.raw` value or a `$derived` result expecting an update.
- Writing `$effect(() => { b = a * 2 })`: use `const b = $derived(a * 2)`.
- Keeping per-user data in a module-level variable on the server; it leaks between requests.
- Calling `getContext`/`setContext`/`createContext` getters after an `await` or in an event handler; they only work during initialisation.
- Using `on:click` together with `onclick` in one component; mixing both syntaxes is an error in runes mode.
- Forgetting `{@render children?.()}` in a layout, so nested pages render nothing.
- Calling `goto` or `fetch` to the app's own endpoints during SSR with global `fetch` instead of the `fetch` passed to `load`.
- Returning class instances or functions from server `load` (not serialisable); return plain data or add a `transport` hook.
- Wrapping `redirect()` or `error()` in a `try/catch` that swallows it; rethrow when `isRedirect(e)` or `isHttpError(e)` from `@sveltejs/kit` is true.
- Leaving `$lib` imports after upgrading to SvelteKit 3, or `$page` from `$app/stores`, which was removed.
- Using the `ORIGIN` environment variable with adapter-node on SvelteKit 3.
- Writing remote functions without a schema argument for user input, or committing a schema export from a `.remote.ts` file (not allowed; share it from a plain module).
- Testing only in `dev`; adapter, env and prerender differences appear in `build` plus `preview`.

## 16. References

- [references/runes.md](references/runes.md): `$state` variants, `$derived`, effects and their pitfalls, props and bindables, snippets, attachments, context, reactive classes and modules, stores interop, async expressions and boundaries, Svelte 4 to 5 migration table.
- [references/sveltekit-routing-load.md](references/sveltekit-routing-load.md): route files, params and matchers, layouts, universal vs server load, streaming, invalidation, page options, hooks, errors, `$app/*` modules, SvelteKit 3 changes.
- [references/forms-actions-remote-functions.md](references/forms-actions-remote-functions.md): form actions, `use:enhance`, validation patterns, remote `query`, `query.batch`, `query.live`, `form`, `command`, `prerender`, single-flight mutations, experimental flags.
- [references/testing-and-deployment.md](references/testing-and-deployment.md): `sv` CLI, env modules, Vitest setups, Playwright, adapters, config in `vite.config.js`, migrations, CI order.
- Svelte docs: https://svelte.dev/docs/svelte and changelog https://github.com/sveltejs/svelte/blob/main/packages/svelte/CHANGELOG.md
- SvelteKit docs: https://svelte.dev/docs/kit and changelog https://github.com/sveltejs/kit/blob/main/packages/kit/CHANGELOG.md
- Migration guides: https://svelte.dev/docs/svelte/v5-migration-guide and https://svelte.dev/docs/kit/migrating-to-sveltekit-3
- Svelte CLI: https://svelte.dev/docs/cli
- Vitest: https://vitest.dev/ ; Playwright: https://playwright.dev/
