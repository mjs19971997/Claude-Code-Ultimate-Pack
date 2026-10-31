# Static Assets, Pages, Frameworks and Testing

Workers static assets, the move from Pages, the Cloudflare Vite plugin and framework deployment, and testing Workers with Vitest inside the Workers runtime. Facts were taken from the Workers, Pages and Vitest integration documentation sources and npm (2026-10).

## Contents

1. [Workers or Pages](#1-workers-or-pages)
2. [Static assets configuration](#2-static-assets-configuration)
3. [Routing and the Worker in front of assets](#3-routing-and-the-worker-in-front-of-assets)
4. [Migrating from Pages](#4-migrating-from-pages)
5. [Cloudflare Vite plugin](#5-cloudflare-vite-plugin)
6. [Frameworks](#6-frameworks)
7. [Vitest setup](#7-vitest-setup)
8. [Writing tests](#8-writing-tests)
9. [Testing bindings](#9-testing-bindings)
10. [CI order](#10-ci-order)

## 1. Workers or Pages

- The Pages documentation carries a note that Workers supports most Pages use cases, offers a broader feature set and is Cloudflare's primary platform for building applications, and tells readers to start new projects with Workers.
- Workers has features Pages lacks, including Durable Objects, Cron Triggers and fuller observability. The migration guide contains a compatibility matrix; consult it for a specific feature.
- Requests for static assets on Workers are free, and Worker invocations are billed at Workers rates, so cost structure is similar to Pages according to the migration guide.
- Keep an existing Pages project running if it works; plan the migration when a Workers-only feature is needed or when the framework adapter moves to Workers.
- Pages Functions (the `functions/` directory with file-based routing, or an advanced mode `_worker.js`) remain supported on Pages. The migration guide suggests another framework such as HonoX for projects that want file-based routing on Workers.
- Durable Objects can be used from Pages only through a separate Worker; using them directly with Workers is simpler and recommended.

## 2. Static assets configuration

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "my-site",
  "compatibility_date": "2026-10-01",
  "assets": {
    "directory": "./dist",
    "not_found_handling": "single-page-application"
  }
}
```

```bash
npx wrangler deploy
```

Keys of the `assets` object (from the configuration reference):

| Key | Meaning |
|---|---|
| `directory` | Folder of assets to serve. Not needed when the Cloudflare Vite plugin points it at the client build output. |
| `binding` | Name of an `env` binding for fetching assets from code; useful only when `main` is set. |
| `base_path` | URL path prefix under which assets are served (default `/`). |
| `run_worker_first` | Boolean or array of route patterns (globs with `*`, exceptions with `!`, patterns start with `/` or `!/`, at most 100 entries). Default false. |
| `html_handling` | `auto-trailing-slash` (default), `force-trailing-slash`, `drop-trailing-slash` or `none`. |
| `not_found_handling` | `none` (default), `404-page` or `single-page-application`. |

- A Worker with only `assets` and no `main` serves files directly. Add `main` to run code for dynamic routes; Wrangler uploads the assets and the Worker together as one deployment unit.
- Limits: 20,000 asset files per Worker version on Free and 100,000 on Paid; 25 MiB per file.
- Use an `.assetsignore` file in the assets directory to exclude files from upload (for example `_worker.js` when migrating advanced-mode Pages). Prefer moving such files out of the directory.
- `wrangler deploy --assets <dir>` serves a directory without a config file, but a config file is better for review and repeatability.

## 3. Routing and the Worker in front of assets

```ts
export default {
  async fetch(request, env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      return Response.json({ ok: true });
    }
    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
```

```jsonc
{
  "main": "src/index.ts",
  "assets": {
    "directory": "./dist",
    "binding": "ASSETS",
    "not_found_handling": "single-page-application",
    "run_worker_first": ["/api/*"]
  }
}
```

- By default a request matching an asset is served directly without invoking the Worker; the Worker runs for requests that match no asset (subject to `not_found_handling`). With `run_worker_first: ["/api/*"]` only API routes invoke the Worker first and everything else is served from assets, which keeps asset traffic out of Worker code.
- `run_worker_first: true` sends every request through the Worker; the Worker then calls `env.ASSETS.fetch(request)` to serve files and can add headers, authentication or rewrites.
- For single-page applications set `not_found_handling` to `single-page-application` so unknown paths return `index.html`.
- Add security headers either in the Worker or with a `_headers` file in the assets directory (check the headers and redirects docs for the supported syntax).
- Serve a subdirectory with `base_path` when the site shares a hostname with other apps.

## 4. Migrating from Pages

1. Replace any Pages-specific framework adapter with the Workers adapter or Vite plugin named in the framework guide.
2. Add `wrangler.jsonc` with `name` and `compatibility_date` (use the date from the Pages Functions config if one existed).
3. Replace `pages_build_output_dir` with `assets.directory`.
4. If using Pages Functions, move the logic into a Worker entry (`main`). For `_worker.js` advanced mode, move the script out of the assets directory or list it in `.assetsignore`.
5. Recreate bindings, variables and secrets in the Worker config and with `wrangler secret put`; Pages environment variables do not carry over automatically.
6. Move custom domains and routes to the Worker, then deploy with `wrangler deploy` and verify before removing the Pages project.
7. Update CI from `wrangler pages deploy` to `wrangler deploy`.

- `wrangler pages` commands still exist in Wrangler 4.156.0 for projects that remain on Pages.
- Workers Builds (git integration) and Wrangler in your own CI are the two deployment routes for Workers.

## 5. Cloudflare Vite plugin

`@cloudflare/vite-plugin` (1.66.0 on npm) integrates Vite with the Workers runtime: the Worker code runs in a local `workerd` process during `vite dev`, with HMR for the client, and `vite build` produces both client assets and the Worker bundle for deployment.

```bash
npm install --save-dev vite @cloudflare/vite-plugin wrangler
```

```ts
// vite.config.ts
import { defineConfig } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [cloudflare({ viteEnvironment: { name: "worker" } })],
  environments: {
    worker: { build: { sourcemap: true } },
  },
});
```

```json
{
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "npm run build && vite preview",
    "deploy": "npm run build && wrangler deploy"
  }
}
```

- The plugin reads `wrangler.jsonc`, `wrangler.json` or `wrangler.toml` from the project root. `assets.directory` is filled automatically from the client build output.
- `vite preview` runs the built output in the Workers runtime before deployment.
- The docs list TanStack Start and React Router (v8) with server-side rendering as officially supported use cases, plus static sites and single-page applications with or without an API, standalone Workers and multi-Worker applications.
- The docs mention `cf build` and `cf deploy` as consumers of the plugin's build output; check the current docs before relying on those commands.
- Use the plugin for new framework projects instead of calling `wrangler dev` against a framework dev server.

## 6. Frameworks

- The Workers framework guides cover web apps (React, React Router, TanStack Start, Vue and others) and a wider list of frameworks with their own adapters. Open the guide for the framework in use and follow its commands.
- Scaffold with `npm create cloudflare@latest <name> -- --framework=<framework>`; the example in the docs uses `--framework=react`.
- A framework that needs Node built-ins relies on `nodejs_compat` (on by default for compatibility dates of 2026-08-04 or later).
- For SSR, bindings are available through the framework adapter's request context or by importing `env` from `cloudflare:workers`; read the adapter docs for the supported pattern.
- Run `wrangler types` so `Env` includes bindings, and check that the framework build emits source maps if exception stacks matter.
- Next.js on Workers has its own adapter and caveats; see nextjs-15-architect for application architecture and consult the Cloudflare Next.js guide for deployment.

## 7. Vitest setup

The documented package is `@cloudflare/vitest-plugin`. It replaces `@cloudflare/vitest-pool-workers` with the same API and configuration; it requires Vitest 4.1 or later (peer range `^4.1.0 || ^5.0.0`).

```bash
npm install --save-dev vitest@^4.1.0 @cloudflare/vitest-plugin
```

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";
import { cloudflareTest } from "@cloudflare/vitest-plugin";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        kvNamespaces: ["TEST_NAMESPACE"],
      },
    }),
  ],
});
```

```jsonc
// test/tsconfig.json
{
  "extends": "../tsconfig.json",
  "compilerOptions": {
    "moduleResolution": "bundler",
    "types": ["@cloudflare/vitest-plugin/types"]
  },
  "include": ["./**/*.ts", "../worker-configuration.d.ts"]
}
```

- Requirements: compatibility date of 2022-10-31 or later; the Worker uses ES modules.
- `miniflare` options override the Wrangler config for test-only resources; see the Miniflare `WorkersOptions` documentation for the full list.
- To migrate from the old package, run `npx @cloudflare/codemods vitest:pool-workers-to-vitest-plugin` (supports `--dry-run` and `--files <glob>`); the manual change renames the dependency, the `cloudflareTest` import and the types entry.
- For outbound request mocking the docs point to `@msw/cloudflare`.
- Tests run fully locally with Miniflare. Storage is isolated per test file.

## 8. Writing tests

Unit test calling the handler directly:

```ts
// test/unit.spec.ts
import { env } from "cloudflare:workers";
import { createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { describe, it, expect } from "vitest";
import worker from "../src";

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

describe("worker", () => {
  it("returns 404 for unknown paths", async () => {
    const request = new IncomingRequest("http://example.com/404");
    const ctx = createExecutionContext();
    const response = await worker.fetch(request, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(response.status).toBe(404);
  });
});
```

Integration test through the exported default handler:

```ts
// test/integration.spec.ts
import { exports } from "cloudflare:workers";
import { describe, it, expect } from "vitest";

describe("worker", () => {
  it("responds over fetch", async () => {
    const response = await exports.default.fetch("http://example.com/health");
    expect(response.status).toBe(200);
  });
});
```

- `waitOnExecutionContext(ctx)` waits for everything passed to `ctx.waitUntil()`, so assertions run after background work.
- `exports.default.fetch()` runs the Worker in the same context as the test runner, so global mocks apply, but module resolution follows Vite. For an environment closer to production, the docs describe auxiliary Workers, which come with limitations.
- Test failure paths: invalid JSON, wrong method, missing auth, rate limit exceeded, storage errors.
- Assert on status, headers (`Content-Type`, CORS, caching) and body, not on logs.

## 9. Testing bindings

```ts
import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";

describe("notes in D1", () => {
  beforeEach(async () => {
    await env.DB.exec("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL)");
    await env.DB.prepare("DELETE FROM notes").run();
  });

  it("inserts with bound parameters", async () => {
    await env.DB.prepare("INSERT INTO notes (title) VALUES (?1)").bind("it's fine").run();
    const row = await env.DB.prepare("SELECT title FROM notes").first<{ title: string }>();
    expect(row?.title).toBe("it's fine");
  });
});

describe("R2", () => {
  it("round-trips an object", async () => {
    await env.BUCKET.put("a.txt", "hello", { httpMetadata: { contentType: "text/plain" } });
    const object = await env.BUCKET.get("a.txt");
    expect(await object?.text()).toBe("hello");
  });
});
```

- Bindings declared in the Wrangler config are available in tests as local simulations, so tests never touch production resources.
- Prefer applying the real migration files in a setup step so tests exercise the production schema; the Vitest integration recipes in the docs cover test setup patterns.
- Mock outbound requests with the documented `@msw/cloudflare` package; do not make live network calls in tests.
- Durable Objects can be tested through stubs from `env.ROOM.get(id)` or with the runner helpers listed in the test APIs reference.
- Keep secrets out of test config: give tests dummy values through `miniflare` bindings or `.dev.vars`-style files that are gitignored.

## 10. CI order

1. `npm ci`
2. `npx wrangler types --check`
3. `npx tsc --noEmit`
4. `npx vitest run`
5. `npx wrangler deploy --dry-run`
6. Deploy job on the main branch only: `npx wrangler deploy` with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` from CI secrets; D1 migrations (`npx wrangler d1 migrations apply <db> --remote`) run before the deploy step.

- Scope the API token to the account and the permissions the deployment needs; never echo it in logs and never expose it to pull requests from forks.
- Keep deployment jobs separate from test jobs so untrusted code from forks cannot read deploy credentials.
- Pin the Wrangler version in `package.json` so CI and local machines agree.
