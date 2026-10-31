# Tooling, Testing and Deployment

The `sv` CLI, environment variables, Vitest and Playwright setups, adapters, build and CI order, and migration commands. Written for sv 1.1.x, SvelteKit 3.1.x and Svelte 5.57.x.

## Contents

1. [sv CLI](#1-sv-cli)
2. [Configuration in vite.config.js](#2-configuration-in-viteconfigjs)
3. [Environment variables](#3-environment-variables)
4. [Vitest](#4-vitest)
5. [Playwright](#5-playwright)
6. [Adapters](#6-adapters)
7. [CI order](#7-ci-order)
8. [Migrations](#8-migrations)

## 1. sv CLI

```sh
npx sv create my-app                       # interactive; prompts for template, types and add-ons
npx sv create --template minimal --types ts --no-add-ons --install npm my-app
npx sv add vitest playwright eslint prettier     # add features to an existing project
npx sv add sveltekit-adapter="adapter:node"      # option syntax: addon="option:value"
npx sv check                                     # needs the svelte-check package installed
npx sv migrate                                   # prompts; or name a migration
```

- `sv create` templates: `minimal`, `demo`, `library` (for `svelte-package`), `addon`. Type checking: `--types ts` or `--types jsdoc`; `--no-types` disables it.
- Official add-ons: `ai-tools`, `better-auth`, `drizzle`, `enhanced-img`, `eslint`, `mdsvex`, `paraglide`, `playwright`, `prettier`, `storybook`, `sveltekit-adapter`, `tailwindcss`, `vitest`. Community add-ons are not reviewed by the maintainers: review code before running them, and use `--no-download-check` only deliberately.
- `sv add` options: `-C/--cwd`, `--no-git-check`, `--install <npm|pnpm|yarn|bun|deno>`, `--no-install`. Commit before running it so the diff is reviewable.
- `sv check` reports TypeScript errors, template type errors, unused CSS and accessibility hints. Options include `--workspace`, `--output`, `--threshold` and `--fail-on-warnings`.
- `sv migrate` names: `svelte-5`, `sveltekit-3` (task based), `sveltekit-2`, `svelte-4`, `self-closing-tags`, plus a prompt when no name is given. Section 8 has details.
- Pin the CLI in scripts (`npx sv@1 ...`) when reproducibility of scaffolding matters.

## 2. Configuration in vite.config.js

```ts
// vite.config.ts (SvelteKit 3)
import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import adapter from '@sveltejs/adapter-node';

export default defineConfig({
  plugins: [
    sveltekit({
      adapter: adapter(),
      compilerOptions: { runes: true },
      csrf: { trustedOrigins: [] },
      paths: { origin: process.env.PUBLIC_ORIGIN },       // reverse-proxy deployments
      prerender: { handleHttpError: 'fail' }
    })
  ]
});
```

- SvelteKit 3 does not read `svelte.config.js`; options formerly under `config.kit` are plugin options. `vitePlugin` options moved: pass `vite-plugin-svelte` options such as `inspector` directly to the plugin.
- SvelteKit 2 keeps `svelte.config.js` with `kit: { adapter, ... }` and `vitePreprocess()`.
- In `package.json` for SvelteKit 3 add `"imports": { "#lib": "./src/lib/index.js", "#lib/*": "./src/lib/*" }` for the `#lib` alias; `tsconfig.json` extends `$app/tsconfig` and lists `include` and `exclude`.
- Use `process.env` in `vite.config` only for build-time values that are safe to inline; runtime configuration belongs in env modules.

## 3. Environment variables

```ts
// src/env.ts
import { defineEnvVars } from '@sveltejs/kit/env';
import * as v from 'valibot';

export const variables = defineEnvVars({
  DATABASE_URL: {},                                   // private by default
  SESSION_SECRET: { schema: v.pipe(v.string(), v.minLength(32)) },
  PUBLIC_SITE_NAME: { public: true }
});
```

```ts
// server code only
import { DATABASE_URL } from '$app/env/private';
// anywhere
import { PUBLIC_SITE_NAME } from '$app/env/public';
```

- Defined in `src/env.ts` or `src/env.js`; values come from the process environment and `.env`/`.env.local` files during development and build. Public variables can also be inlined in `app.html` as `%sveltekit.env.NAME%`.
- `$app/env/private` cannot be imported by code that reaches the browser; the build fails if it does. Do not weaken this by copying values into `load` return values or `PUBLIC_` variables.
- Validators accept a Standard Schema or a function (SvelteKit 3). Validate secrets for presence and shape at startup.
- Legacy modules `$env/static/private`, `$env/static/public`, `$env/dynamic/private`, `$env/dynamic/public` and `$app/environment` still work in SvelteKit 3 as deprecated aliases and are slated for removal in SvelteKit 4. In SvelteKit 2 projects the legacy modules are the only option: only names starting with `PUBLIC_` reach the client.
- Never commit `.env` files with real secrets; commit `.env.example`. Inject secrets from the platform's secret store.
- `$app/env` (renamed from `$app/environment`) exports `browser`, `dev`, `building`, `version`.

## 4. Vitest

Install via `npx sv add vitest` (usages `unit` and `component`, for example `npx sv add vitest="usages:unit,component"`). It installs packages, adds scripts and a client/server-aware setup in the Vite config. Read the generated config rather than copying one from elsewhere.

Plain unit test of a rune module (file name must contain `.svelte.` so the compiler runs on it):

```ts
// src/lib/state/counter.svelte.test.ts
import { flushSync } from 'svelte';
import { expect, test } from 'vitest';
import { createCounter } from './counter.svelte.js';

test('counter increments', () => {
  const counter = createCounter(1);
  counter.increment();
  expect(counter.count).toBe(2);
});

test('effects run after flush', () => {
  const seen: number[] = [];
  const cleanup = $effect.root(() => {
    const counter = createCounter();
    $effect(() => { seen.push(counter.count); });
    flushSync();
    counter.increment();
    flushSync();
  });
  expect(seen).toEqual([0, 1]);
  cleanup();
});
```

Component test with Testing Library (setup follows the Svelte testing docs: a DOM environment such as jsdom and the `browser` resolve condition when running under Vitest):

```ts
// src/lib/Counter.test.ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';
import Counter from './Counter.svelte';

test('increments', async () => {
  const user = userEvent.setup();
  render(Counter, { props: { initial: 0 } });
  const button = screen.getByRole('button');
  await user.click(button);
  expect(button).toHaveTextContent('1');
});
```

- The docs example without a library uses `mount`, `unmount` and `flushSync` from `svelte` against `document.body`.
- Vitest browser mode runs components in a real browser; the `vitest-browser-svelte` package provides a `render` for it. Check its README for the provider setup, because Vitest browser configuration changes between majors.
- For context, snippet props and two-way bindings, write a small wrapper component in the test directory and render that.
- Testing a `load` function: import it and call with a minimal event (`{ params, locals, fetch: vi.fn(), url: new URL('http://x') } as any`); assert on returned data and on thrown `error()`/`redirect()` values (`isHttpError`, `isRedirect`).
- Testing actions: build a `Request` with `FormData`, call `actions.default({ request, cookies, locals } as any)`, and assert `isActionFailure(result)`. Prefer a few Playwright tests for the full flow.
- Mock `$app/state` or `$app/navigation` with `vi.mock` only if the component needs them; otherwise prefer passing values as props.
- Run the unit and component projects separately in CI so slow browser tests do not hide fast failures.

## 5. Playwright

```sh
npx sv add playwright
```

```ts
// tests/todos.test.ts (the file extension and folder follow the generated config)
import { expect, test } from '@playwright/test';

test('add a todo', async ({ page }) => {
  await page.goto('/todos');
  await page.getByLabel('Title').fill('Buy milk');
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: 'Buy milk' })).toBeVisible();
});
```

- The add-on writes a Playwright config, scripts and an example test. Confirm the `webServer` entry builds the app and serves it with `vite preview` so tests exercise production output and the real adapter paths.
- Test with JavaScript disabled for key forms using `test.use({ javaScriptEnabled: false })` to prove progressive enhancement.
- Prefer role and label locators; they double as an accessibility check. For test design and CI sharding see playwright-expert.
- Seed test data through a test-only database or an API called in `beforeEach`; do not add test backdoors to production routes.

## 6. Adapters

```ts
// vite.config.ts
import adapter from '@sveltejs/adapter-static';
sveltekit({ adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, precompress: false, strict: true }) });
```

| Adapter | Use for | Notes |
|---|---|---|
| `adapter-auto` | zero-config on Cloudflare, Netlify, Vercel | takes no options; install the concrete adapter for options and CI speed |
| `adapter-node` | any Node host, containers, Cloud Run, Render | `node build`; env vars `PORT`, `HOST`, `SOCKET_PATH`, `BODY_SIZE_LIMIT`, `SHUTDOWN_TIMEOUT`, header vars behind proxies; options `out`, `precompress`, `envPrefix` |
| `adapter-static` | fully prerendered sites and SPAs | options `pages`, `assets`, `fallback`, `precompress`, `strict`; needs `prerender = true` or a `fallback` page |
| `adapter-vercel` | Vercel | route `config` for `runtime`, `regions`, `maxDuration`; the edge runtime is gone in SvelteKit 3; ISR and image optimization options exist |
| `adapter-cloudflare` | Workers and Pages | options `config`, `platformProxy`, `fallback`, `routes`; in SvelteKit 3 import `env` and `waitUntil` from `cloudflare:workers`, run `wrangler types`, `wrangler` >= 4.67 |
| `adapter-netlify` | Netlify | publish directory is an adapter option in SvelteKit 3 |
| `adapter-bun` | Bun runtime | listed in the SvelteKit docs; check its page for options |

- Node container sketch: multi-stage build that runs `npm ci` and `npm run build`, then copies `build/`, `package.json` and production dependencies into a slim Node 22 image running as a non-root user; set `PORT`, `HOST=0.0.0.0` and `paths.origin` or proxy header variables. For image details see docker-expert.
- adapter-node serves a static asset list recorded at build time; do not add files to `build/` afterwards. Only GET and HEAD are served as static assets.
- Put compression and TLS in the reverse proxy, or set `precompress: true` and let the proxy serve `.br` and `.gz` files.
- Prerender crawling fails the build on broken links by default; handle expected errors with `prerender.handleHttpError`.
- Cloudflare: Node API compatibility needs the `nodejs_compat` flag in Wrangler config; the worker size limit applies to the server bundle.
- `data-sveltekit-preload-data` and service workers interact with caching; do not cache `Cache-Control: no-store` responses (live queries, authenticated data).

## 7. CI order

```sh
npm ci
npx sv check --fail-on-warnings      # or: npm run check
npm run lint                         # eslint + prettier --check
npm run test:unit -- --run           # vitest, non-watch mode
npm run build                        # with the production adapter
npx playwright install --with-deps chromium
npm run test:e2e                     # runs against preview
```

- Use the same Node major as production (SvelteKit 3 needs >=22.17). Cache the package manager store, not `node_modules` or `.svelte-kit`.
- `.svelte-kit/` is generated (types, tsconfig, output); `npm run prepare` (`svelte-kit sync`) regenerates it after install and is a prerequisite for type checking.
- Fail the pipeline on `npm audit --omit=dev` findings above the team's threshold, and review lockfile changes.
- Upload sourcemaps to the error tracker in the build job; do not expose them publicly by accident.

## 8. Migrations

- Svelte 4 to 5: `npx sv migrate svelte-5`. It converts `let` to `$state`, `$:` to `$derived`/`$effect`, `export let` to `$props`, `on:` to attributes and slots to snippets where it can, and leaves `run()` from `svelte/legacy` and bubbling helpers for the rest. It is a legacy migration (via `svelte-migrate@1`) and no longer receives fixes for new patterns. Review every diff.
- SvelteKit 1 to 2: `npx sv migrate sveltekit-2` (legacy, same caveat).
- SvelteKit 2 to 3: first upgrade to the latest 2.x and fix deprecation warnings, then `npx sv migrate sveltekit-3`. Tasks: `package-json` and `tsconfig` (prerequisites), `svelte-config` (moves config into `vite.config`), `environment` (replaces legacy env modules with `$app/env` and creates `src/env.ts`), and further selectable tasks listed by the command. Run one selectable task at a time and commit between tasks.
- After the codemods: change `$lib` to `#lib` (with extensions), replace `$app/stores` with `$app/state`, update hook type imports, review `csrf` and `paths.origin`, replace `ORIGIN`, move Cloudflare `platform.env` use, and re-run build, tests and e2e.
- Leave Svelte 4 components as they are until touched when time is short: they keep working in a Svelte 5 app, and migration can be incremental.
