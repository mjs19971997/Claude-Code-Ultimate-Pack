# Workers and Wrangler

Worker handlers, compatibility settings, the Wrangler configuration file, environments, secrets, generated types, deployment commands, versions and observability. Command names and flags were checked against Wrangler 4.156.0 (`npx wrangler --help`) and the configuration docs (2026-10).

## Contents

1. [Handlers and the execution context](#1-handlers-and-the-execution-context)
2. [Compatibility date and flags](#2-compatibility-date-and-flags)
3. [Wrangler configuration](#3-wrangler-configuration)
4. [Environments](#4-environments)
5. [Secrets and variables](#5-secrets-and-variables)
6. [Types](#6-types)
7. [Commands](#7-commands)
8. [Versions, deployments and rollback](#8-versions-deployments-and-rollback)
9. [Observability and tail](#9-observability-and-tail)
10. [Limits worth knowing](#10-limits-worth-knowing)

## 1. Handlers and the execution context

```ts
export default {
  async fetch(request, env, ctx): Promise<Response> {
    ctx.waitUntil(recordHit(env, request));
    return new Response("ok");
  },

  async scheduled(controller, env, ctx): Promise<void> {
    ctx.waitUntil(cleanup(env));
  },

  async queue(batch, env, ctx): Promise<void> {
    for (const message of batch.messages) {
      await handle(env, message.body);
      message.ack();
    }
  },
} satisfies ExportedHandler<Env>;

async function recordHit(env: Env, request: Request): Promise<void> {
  const path = new URL(request.url).pathname;
  await env.DB.prepare("INSERT INTO hits (path) VALUES (?1)").bind(path).run();
}

async function cleanup(env: Env): Promise<void> {
  await env.DB.prepare("DELETE FROM hits WHERE created_at < datetime('now', '-30 days')").run();
}

async function handle(env: Env, body: unknown): Promise<void> {
  console.log(JSON.stringify({ event: "job", body }));
}
```

- The default export is an object of handlers. `fetch` serves HTTP; `scheduled` runs for Cron Triggers (`triggers.crons` in the config); `queue` consumes Queues batches.
- `ctx.waitUntil(promise)` extends the invocation so the promise can finish after the response. It has no retry and no durability; use Queues when the work must not be lost.
- `ctx.passThroughOnException()` falls back to the origin when the Worker throws; use it only for Workers placed in front of an origin.
- Bindings can also be imported anywhere with `import { env } from "cloudflare:workers"`. This is useful for module-level initialisation, but do not store per-request data in module globals, because one isolate serves many concurrent requests.
- Durable Object and Workflow classes are exported as named classes from the main module and referenced by name in the config.
- The service worker syntax (`addEventListener("fetch", ...)`) is the legacy form. Use modules for all new code.

## 2. Compatibility date and flags

- `compatibility_date` is required to deploy. It selects the runtime behaviour as of that date, so a Worker keeps working when the runtime changes. Wrangler can fill in the latest supported date with `--latest` on `deploy`; scaffolding writes the current date.
- `compatibility_flags` enable or disable specific behaviours. The flag most projects need is `nodejs_compat`, which makes Node.js built-ins such as `node:buffer`, `node:crypto` and `node:async_hooks` available.
- For compatibility dates of 2026-08-04 or later, Workers enables both `nodejs_compat` and `nodejs_compat_v2` by default, and the explicit flags are redundant (Wrangler, Miniflare, the Vite plugin and the Vitest plugin ignore them). To turn Node.js compatibility off on those dates, add both `no_nodejs_compat` and `no_nodejs_compat_v2`.
- For dates from 2024-09-23 through 2026-08-03, `nodejs_compat` also turns on `nodejs_compat_v2` unless `no_nodejs_compat_v2` is set; v2 bundles extra polyfills and globals and increases bundle size.
- With `nodejs_compat` and the `nodejs_compat_populate_process_env` flag (on by default for dates on or after 2025-04-01), variables and secrets are also visible on `process.env`.
- The Vitest integration requires a compatibility date of 2022-10-31 or later, and `r2_list_honor_include` behaviour requires a date of 2022-08-04 or later or the matching flag.
- Bump the date deliberately: read the compatibility dates page for the range being crossed, run the tests, then deploy.

## 3. Wrangler configuration

The docs recommend `wrangler.jsonc` for new projects. TOML and plain JSON are still read, and some newer features are only available with a JSON config. Wrangler has read JSON config since v3.91.0.

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "my-worker",
  "main": "src/index.ts",
  "compatibility_date": "2026-10-01",
  "workers_dev": false,
  "routes": [{ "pattern": "api.example.com", "custom_domain": true }],
  "triggers": { "crons": ["0 3 * * *"] },
  "vars": { "LOG_LEVEL": "info" },
  "observability": { "enabled": true, "head_sampling_rate": 1 },
  "limits": { "cpu_ms": 30000 },
  "kv_namespaces": [{ "binding": "CACHE_KV", "id": "<KV_NAMESPACE_ID>" }],
  "r2_buckets": [{ "binding": "BUCKET", "bucket_name": "my-bucket" }],
  "d1_databases": [
    { "binding": "DB", "database_name": "my-db", "database_id": "<D1_DATABASE_ID>" }
  ],
  "queues": {
    "producers": [{ "binding": "JOBS", "queue": "jobs" }],
    "consumers": [{ "queue": "jobs", "max_batch_size": 10, "dead_letter_queue": "jobs-dlq" }]
  },
  "durable_objects": { "bindings": [{ "name": "ROOM", "class_name": "Room" }] },
  "migrations": [{ "tag": "v1", "new_sqlite_classes": ["Room"] }],
  "hyperdrive": [{ "binding": "HYPERDRIVE", "id": "<HYPERDRIVE_ID>" }],
  "services": [{ "binding": "AUTH", "service": "auth-worker" }],
  "assets": { "directory": "./public", "binding": "ASSETS", "not_found_handling": "404-page" },
  "ratelimits": [{ "name": "LIMITER", "namespace_id": "1001", "simple": { "limit": 100, "period": 60 } }],
  "secrets": { "required": ["API_TOKEN"] }
}
```

- Required for deployment: `name`, `main` and `compatibility_date`. An assets-only Worker can omit `main`.
- Config files allow comments and trailing commas in `.jsonc`.
- `workers_dev` controls the `*.workers.dev` URL; set it to false for production Workers served from custom domains or routes. `routes` with `custom_domain: true` attach a hostname directly.
- `limits.cpu_ms` raises the per-request CPU limit on the Paid plan; the default is 30 seconds and the maximum 300,000 ms.
- `upload_source_maps` makes stack traces point at source files; `wrangler deploy --upload-source-maps` defaults to true in the current CLI.
- `placement`, `tail_consumers`, `send_email`, `ai`, `vectorize`, `browser`, `containers`, `workflows` and further bindings exist; check the configuration page for exact keys before using one.
- Wrangler can generate and validate against `config-schema.json` shipped in the package, so editors flag unknown keys.
- Secrets Store is a beta account-level store; per-Worker secrets are the default recommendation.

## 4. Environments

```jsonc
{
  "name": "my-worker",
  "main": "src/index.ts",
  "compatibility_date": "2026-10-01",
  "d1_databases": [{ "binding": "DB", "database_name": "my-db", "database_id": "<PROD_ID>" }],
  "env": {
    "staging": {
      "name": "my-worker-staging",
      "d1_databases": [
        { "binding": "DB", "database_name": "my-db-staging", "database_id": "<STAGING_ID>" }
      ],
      "vars": { "LOG_LEVEL": "debug" }
    }
  }
}
```

- Select an environment with `--env staging` (or `-e staging`) or the `CLOUDFLARE_ENV` variable; the flag wins.
- Bindings, `vars` and secrets are non-inheritable keys: they are configurable at the top level but not inherited by an environment, so each environment must list them. Other keys such as `main` and `compatibility_date` are inherited.
- Each environment deploys as a separate Worker, by default named `<name>-<env>`.
- Secrets are per environment: `wrangler secret put API_TOKEN --env staging`.
- Local secrets can be split per environment with `.dev.vars.<env>`; when that file exists, the plain `.dev.vars` is not loaded. With `.env` files, matching files are merged with the more specific file winning.
- The `-e` flag also selects which `.env` and `.dev.vars` files load for local commands.

## 5. Secrets and variables

- `vars` hold non-sensitive configuration and appear in the config and dashboard. Do not put secrets there.
- Secrets: `npx wrangler secret put NAME` (prompts for the value; do not pass it on the command line), `secret list`, `secret delete`, and `secret bulk <file>` for up to 100 per request from JSON or `.env` content.
- `secret put` creates a new Worker version and deploys it immediately. For gradual deployments use `npx wrangler versions secret put NAME`, then `versions deploy`.
- `wrangler deploy --secrets-file <path>` uploads secrets together with the code from a JSON or `.env` file. Keep that file out of git and delete it after use in CI.
- The `secrets.required` config property lists the names the Worker needs: deploy and version upload fail if any is missing, and local development loads only the listed keys from `.dev.vars` or `.env`.
- Local development: put values in `.dev.vars` or `.env` next to the config, in dotenv syntax, and gitignore `.dev.vars*` and `.env*`. Choose one of the two files, not both.
- A deploy without `--keep-vars` removes `vars` that exist only in the dashboard. Secrets are never deleted by a deploy.
- The limits page lists 64 environment variables per Worker on Free and 128 on Paid, 5 KB each.

## 6. Types

```bash
npx wrangler types                    # writes worker-configuration.d.ts
npx wrangler types --check            # exit non-zero if the file is stale
npx wrangler types ./src/env.d.ts     # custom output path
```

- Output includes the runtime types (`--include-runtime`, default true) and an `Env` interface from the bindings and vars (`--include-env`, default true). `--strict-vars` (default true) generates literal types for `vars`.
- `--env-interface` renames the generated interface from `Env`.
- Re-run after any change to bindings, vars or compatibility settings. Run it from a `postinstall` or a `cf-typegen` script and verify with `--check` in CI.
- The `@cloudflare/workers-types` package (5.20261031.1 on npm) is the older, manual route; the generated runtime types follow the compatibility date and flags and are preferred.

## 7. Commands

| Task | Command |
|---|---|
| Local dev server | `npx wrangler dev` (flags include `--port`, `--ip`, `--local-protocol`, `-e`) |
| Deploy | `npx wrangler deploy` (`--dry-run`, `--env`, `--keep-vars`, `--secrets-file`, `--message`, `--tag`, `--minify`) |
| Delete a Worker | `npx wrangler delete [name]` |
| Types | `npx wrangler types` |
| Tail logs | `npx wrangler tail [worker]` |
| Auth | `npx wrangler login`, `whoami`, `logout` (CI uses `CLOUDFLARE_API_TOKEN`) |
| KV | `npx wrangler kv namespace create NAME`, `kv key put/get/list/delete` |
| R2 | `npx wrangler r2 bucket create NAME`, `r2 object put/get/delete` |
| D1 | `npx wrangler d1 create/info/list/execute/export/migrations/time-travel` |
| Queues | `npx wrangler queues create NAME` |
| Hyperdrive | `npx wrangler hyperdrive create NAME --connection-string=...` (check the docs for current flags) |
| Versions | `npx wrangler versions upload`, `versions deploy`, `versions list` |
| Deployments | `npx wrangler deployments list`, `npx wrangler rollback [version-id]` |
| Project setup | `npx wrangler setup`, `npx wrangler init [name]` |

- Prefer `npm create cloudflare@latest` (create-cloudflare 2.74.5 on npm) for scaffolding; it offers templates and framework options.
- `wrangler deploy` also runs framework autoconfiguration when it detects a supported framework (`--autoconfig`, default true); review the changes it proposes.
- The CLI accepts `--install-skills` on commands to install Cloudflare skills for coding agents; it is optional and off by default.
- Run `npx wrangler <command> --help` to confirm flags for the installed version; commands and flags change between majors.

## 8. Versions, deployments and rollback

- A deployment routes traffic to one or two Worker versions. `wrangler deploy` uploads a version and deploys it at 100 percent in one step.
- `wrangler versions upload` uploads a version without sending traffic; `wrangler versions deploy` assigns percentages, which supports gradual rollouts and canaries.
- `wrangler deployments list` shows history; `wrangler rollback [version-id]` redeploys an earlier version. Rolling back does not undo D1 migrations or secret changes.
- Durable Object classes update on a deferred strategy by default (a maximum delay of 300 seconds); `wrangler deploy --durable-objects-code-update-mode` can select immediate or deferred with a delay.
- Use `--message` and `--tag` on deploy or upload to label versions with a commit hash.
- Bindings are part of a version: a deploy that adds a binding needs the resource to exist first.

## 9. Observability and tail

```jsonc
{
  "observability": {
    "enabled": true,
    "head_sampling_rate": 0.25,
    "logs": { "invocation_logs": true }
  }
}
```

- `observability.enabled` writes Workers Logs to the account; newly created Workers have it on by default. Logs include invocation logs, `console.*` output, errors and uncaught exceptions. `head_sampling_rate` (default 1) keeps a fraction of requests.
- Set `invocation_logs` to false under `observability.logs` to drop the automatic invocation entry while keeping custom logs; check the Workers Logs page for the exact nesting before relying on it.
- Environment blocks can set a different sampling rate for staging and production.
- Real-time viewing: `npx wrangler tail --format pretty --status error`, with filters `--method`, `--search`, `--ip` and `--sampling-rate`. Tail is for debugging, not retention.
- Export or retain logs with OpenTelemetry export (recommended in the docs), Workers Logpush or Tail Workers.
- Upload source maps (and make framework builds generate them) so exception stacks show original files and lines.
- Log structured JSON, keep secrets and personal data out of logs, and use request IDs to correlate entries.
- The dashboard reports error outcomes such as `exceededCpu` and `exceededMemory`; Error 1102 means resource limits were exceeded.

## 10. Limits worth knowing

Numbers below are from the Workers limits page (2026-10); re-read the page before quoting them.

| Limit | Free | Paid |
|---|---|---|
| Requests | 100,000 per day | no limit |
| CPU time per HTTP request | 10 ms | 5 min maximum (30 s default) |
| Subrequests per request | 50 | 10,000 |
| Memory per isolate | 128 MB | 128 MB |
| Simultaneous outgoing connections | 6 | 6 |
| Worker size | 64 MiB | 64 MiB |
| Startup time | 1 second | 1 second |
| Workers per account | 100 | 500 |
| Cron Triggers per account | 5 | 250 |
| Static asset files per Worker version | 20,000 | 100,000 |
| Static asset file size | 25 MiB | 25 MiB |

- Waiting on network I/O does not count toward CPU time.
- Request body size limits depend on the zone plan (100 MB on Free and Pro, 200 MB on Business), not on the Workers plan.
- URL size is limited to 16 KB and total request or response headers to 128 KB each.
