---
name: cloudflare-expert
description: >-
  Builds and reviews applications on the Cloudflare developer platform: Workers (module syntax, bindings, compatibility dates), Wrangler 4 with wrangler.jsonc, R2, D1, KV, Durable Objects, Queues, static assets, the Cloudflare Vite plugin and Vitest tests. Use when editing wrangler.jsonc or wrangler.toml, .dev.vars, src/index.ts with fetch(request, env, ctx), or running wrangler dev, deploy, types, secret, d1 migrations or tail. Not for AWS (use aws-expert), nginx or reverse proxies (use nginx-expert), Next.js internals (use nextjs-15-architect), Terraform (use terraform-expert), or general Node.js runtime work (use nodejs-architect).
license: MIT
metadata:
  version: "3.2.0"
---

# Cloudflare Expert

This skill covers building on the Cloudflare developer platform with the Workers runtime as the center: Worker handlers, Wrangler configuration and commands, storage bindings (R2, D1, KV, Durable Objects), Queues and Hyperdrive in outline, static assets and framework deployment, testing in the Workers runtime, observability and security. It favours module Workers, a JSON Wrangler config and generated types. Other clouds, reverse proxies, Terraform-managed infrastructure and framework internals belong to other skills.

> Verified against Wrangler 4.156.0, miniflare 4.20260730.0, @cloudflare/workers-types 5.20261031.1, @cloudflare/vite-plugin 1.66.0, @cloudflare/vitest-plugin 1.4.11 (requires Vitest 4.1 or later; Vitest 5.0.5 on npm) and the Cloudflare developer documentation sources for Workers, R2, D1, KV and Durable Objects (2026-10).

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

- Covered: Workers fetch, scheduled and queue handlers; `ctx.waitUntil`; bindings through `env`; `compatibility_date` and `compatibility_flags`; Wrangler configuration, environments, types, secrets, deploy, versions, rollback and tail; R2 binding API, S3 API, presigned URLs, CORS and public access; D1 queries, batches, migrations, Time Travel and read replication; KV consistency; Durable Objects with SQLite storage, Queues and Hyperdrive in outline; Workers static assets, Pages migration, the Cloudflare Vite plugin; Vitest tests in the Workers runtime; Workers Logs and observability settings; rate limiting binding and secret handling.
- Not covered: AWS services (aws-expert); nginx and generic reverse proxy configuration (nginx-expert); Next.js application architecture (nextjs-15-architect); Terraform modules and state (terraform-expert); general Node.js event loop and server design (nodejs-architect); Redis (redis-expert); HTTP API design (rest-api-expert); CI pipeline structure (cicd-expert).
- Out of date quickly: product limits, prices, beta status and the exact CLI surface. Re-check the linked limits pages before quoting a number to a user.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Worker shape | ES module default export with `fetch(request, env, ctx)`. Bindings arrive on `env`; `ctx.waitUntil(promise)` keeps work alive after the response is sent. `import { env } from "cloudflare:workers"` gives global access to bindings. |
| Config file | Wrangler accepts `wrangler.jsonc`, `wrangler.json` and `wrangler.toml`. The docs recommend `wrangler.jsonc` for new projects and note that some newer features only work with a JSON config. At minimum `name`, `main` and `compatibility_date` are required for a code Worker. |
| Compatibility | `compatibility_date` pins runtime behaviour. For dates of 2026-08-04 or later, `nodejs_compat` and `nodejs_compat_v2` are on by default; older dates need `"compatibility_flags": ["nodejs_compat"]` to use Node built-ins. |
| Types | `wrangler types` writes `worker-configuration.d.ts` with runtime types and a global `Env` interface derived from the config. `--check` verifies the file is current. Prefer it over hand-written `Env`. |
| Secrets | `wrangler secret put KEY` stores a per-Worker secret and deploys a new version immediately; `wrangler versions secret put` only creates a version. Locally use `.dev.vars` or `.env` (not both) next to the config and gitignore them. Never put secrets in `vars`. |
| Environments | `--env` or `CLOUDFLARE_ENV` selects `env.<name>` blocks. Bindings and vars are non-inheritable and must be repeated per environment. |
| R2 | S3-compatible object storage with no egress fees for reads through the platform. Workers binding for put, get, head, delete, list and multipart; S3 API and presigned URLs for browsers and external clients. The binding cannot create presigned URLs. |
| D1 | SQLite-based database. `prepare().bind()` with `?` or `?NNN` parameters, `first`, `all`, `run`, `raw`, `batch` (transactional) and `exec`. Migrations as SQL files applied with `wrangler d1 migrations`. Time Travel restores to any minute within the retention window. Read replication is in beta and used through the Sessions API. |
| KV | Eventually consistent edge key-value store for read-heavy data. Changes can take 60 seconds or more to be visible in other locations; the default `cacheTtl` is 60 seconds. |
| Durable Objects | Compute with private, strongly consistent storage. New classes should use SQLite storage (`new_sqlite_classes` in a migration). |
| Static assets | Workers can serve a directory declared in `assets`. Pages is still available but Workers is the documented starting point for new projects. |
| Testing | `@cloudflare/vitest-plugin` (successor of `@cloudflare/vitest-pool-workers`) runs Vitest tests inside the Workers runtime with Miniflare. |
| Observability | `observability.enabled` turns on Workers Logs; `wrangler tail` streams live logs; source maps are uploaded by default in current Wrangler. |

## 3. Workflow

1. Identify the shape of the project: a standalone Worker, a Worker with static assets, a framework app, or storage only. Check for an existing `wrangler.jsonc` or `wrangler.toml` and keep its format unless migrating is requested.
2. Scaffold or inspect: new projects start with `npm create cloudflare@latest`; existing ones are inspected with `npx wrangler --version` and by reading the config. Pin Wrangler as a dev dependency and run it with `npx wrangler`.
3. Declare bindings in the config first, then run `npx wrangler types` and commit the generated declaration file (or generate it in a pre-test script).
4. Write the handler against `Env`. Validate input at the edge, return explicit status codes, and push non-critical work into `ctx.waitUntil`.
5. Develop with `npx wrangler dev`, which runs locally with local simulations of storage bindings. Seed local D1 with `wrangler d1 migrations apply <db> --local`.
6. Test with Vitest in the Workers runtime (section 11) and type check with `tsc --noEmit`.
7. Create remote resources once (`wrangler d1 create`, `wrangler r2 bucket create`, `wrangler kv namespace create`), copy the IDs into the config, set secrets, apply remote migrations, then `npx wrangler deploy`.
8. Verify with `npx wrangler tail` or Workers Logs, and keep `wrangler rollback` or `wrangler versions` in reach for a bad release.

## 4. Decision Rules

- If starting a new project, use Workers with `wrangler.jsonc`; do not start a new project on Pages unless a Pages-only feature is required. See [references/pages-assets-testing.md](references/pages-assets-testing.md).
- If an existing project uses `wrangler.toml` and works, keep it; convert to JSON only when asked, since the two formats are equivalent for most keys.
- If the data is relational, needs transactions or SQL queries, use D1. If it is a small per-user, per-room or per-tenant stateful unit needing strong consistency or coordination, use a Durable Object with SQLite. If it is read-mostly configuration or cached lookups tolerant of 60-second staleness, use KV. If it is blobs, uploads or exports, use R2.
- If a read after a write must see the write, do not use KV; use D1 (primary), a Durable Object, or D1 Sessions with a bookmark.
- If a browser must upload or download an R2 object directly, issue a presigned URL from server code with a short expiry; if the Worker can proxy the body, use the binding. Large uploads over 5 GiB need multipart.
- If a public read-only bucket is needed for production, attach a custom domain; the `r2.dev` URL is for non-production use and has no WAF or cache controls.
- If work should survive a failed request or needs retries, enqueue it on Queues instead of using `ctx.waitUntil` alone; `waitUntil` has no retry and no durability.
- If the app is a framework app (React Router, TanStack Start, Vue, SvelteKit, Astro and others), follow the framework guide and the Cloudflare Vite plugin or adapter named there; do not hand-write a bundler setup.
- If a value is sensitive, use `wrangler secret put` (or the `secrets` config property to declare required names); if it is non-sensitive configuration, use `vars`.
- If a single rate limit must be strict across all locations, do not rely on the Rate Limiting binding (approximate, per location); use a Durable Object counter.
- If exceeding 10 ms CPU on the Free plan is likely, check the current Workers limits page before choosing the plan.

## 5. Coding Standards

- Use the module syntax and type the default export with `satisfies ExportedHandler<Env>`.
- Take bindings from `env` or from `import { env } from "cloudflare:workers"`; never read bindings from module-level mutable state captured across requests, except clients that are safe to reuse.
- Always `await` or `ctx.waitUntil()` a promise. A floating promise can be cancelled when the response completes.
- Always use parameterised D1 statements: `prepare("... WHERE id = ?1").bind(id)`. Never concatenate user input into SQL.
- Return `Response` objects with explicit `status` and `Content-Type`; use `Response.json(body, { status })`.
- Stream bodies (`request.body`, `object.body`) instead of buffering with `arrayBuffer()` or `text()` for large payloads; memory per isolate is limited.
- Use `new URL(request.url)` and compare methods explicitly; return 405 with an `Allow` header for unsupported methods.
- Keep `compatibility_date` explicit and update it deliberately; test after bumping it.
- Use `wrangler.jsonc` with `"$schema": "./node_modules/wrangler/config-schema.json"` for editor validation (the path shown in the current docs sample).
- Name bindings in upper snake case (`DB`, `BUCKET`, `CACHE_KV`, `JOBS_QUEUE`) and keep the same names in every environment.

## 6. Project Structure

```text
my-worker/
|-- wrangler.jsonc               # name, main, compatibility_date, bindings, observability
|-- worker-configuration.d.ts    # generated by `wrangler types`
|-- package.json
|-- tsconfig.json
|-- .dev.vars                    # local secrets, gitignored
|-- .gitignore                   # .dev.vars*, .env*, .wrangler/, node_modules/
|-- migrations/                  # D1 SQL files, e.g. 0001_init.sql
|-- src/
|   |-- index.ts                 # export default { fetch, scheduled, queue }
|   |-- routes/                  # small handlers per route group
|   `-- lib/                     # validation, response helpers
|-- public/                      # static assets (optional)
`-- test/
    |-- tsconfig.json
    |-- unit.spec.ts
    `-- integration.spec.ts
```

- Keep one Worker per deployable unit. Multiple Workers can call each other with service bindings (`services` in the config).
- Commit `wrangler.jsonc`, migrations and the generated types; never commit `.dev.vars`, `.env` files or the `.wrangler/` local state directory.
- For a framework app, the framework template owns the layout; add `wrangler.jsonc` at the project root.

## 7. Design Patterns

- **Thin router over small handlers**: dispatch on `URL.pathname` and method, or use a small router library such as Hono (4.13.14 on npm); keep business logic in plain functions that take `env` pieces as parameters so they are unit-testable.
- **Respond fast, finish later**: return the response, then `ctx.waitUntil(logEvent(env, data))` for non-critical work. Use Queues when the work needs retries or must outlive a failure.
- **Cache-aside with KV or the Cache API**: read KV, fall back to D1 or an origin, write back with `expirationTtl`. Accept staleness up to the KV propagation window.
- **Presigned upload flow**: client asks the Worker for a URL, the Worker authenticates, validates size and type intent, signs a short-lived PUT URL, the client uploads straight to R2, and an R2 event notification or a client callback records the object.
- **Single-writer Durable Object**: route all writes for one key (room, tenant, counter) to one object and keep its state in SQLite; read-heavy consumers read a projection from KV or D1.
- **Service bindings for internal calls**: call another Worker through `env.OTHER.fetch()` instead of a public URL, which avoids public exposure of internal APIs.
- **Migrations as the only schema path**: every D1 schema change is a numbered SQL file applied locally, then to production; no ad hoc `ALTER` from application code.

## 8. Best Practices

- Declare `"observability": { "enabled": true }` so Workers Logs capture invocation logs, `console.log` output and exceptions. Set `head_sampling_rate` below 1 for very high traffic.
- Use structured logging: `console.log(JSON.stringify({ event, id }))` so logs can be filtered by field.
- Use environments (`env.staging`, `env.production`) with separate D1, KV and R2 resources; repeat bindings in each environment block.
- Run `wrangler types --check` in CI to catch drift between config and `Env`.
- Use `wrangler deploy --dry-run` in CI to compile and check without uploading.
- Use gradual rollouts with `wrangler versions upload` and `wrangler versions deploy` for risky changes; use `wrangler rollback` to return to an earlier deployment.
- Prefer `ctx.waitUntil` over unawaited promises, and bound the work: a never-resolving promise keeps the invocation alive until a runtime limit.
- Document each binding and required secret in the README; use the `secrets.required` config property so deploys fail fast when a secret is missing.
- Pin `wrangler` in `devDependencies` so local and CI behave the same; update on a schedule and read the release notes.

## 9. Performance

- CPU time counts execution only; waiting on `fetch`, KV, R2 or D1 does not count. Heavy JSON parsing, crypto and rendering do. Profile with DevTools CPU profiling before raising `limits.cpu_ms`.
- Memory is limited per isolate, shared by concurrent requests. Stream large bodies; avoid building large arrays from R2 listings or D1 results.
- Batch D1 statements with `batch()` to cut round trips; keep result sets small with `LIMIT` and indexed predicates.
- Read-heavy D1 apps with global users can use read replication through the Sessions API (beta). Writes still go to the primary.
- Raise KV `cacheTtl` for rarely changing keys; the default is 60 seconds.
- Use the Cache API or the CDN cache with custom domains for R2 objects that are read often.
- Place work near data: Durable Objects and D1 primaries live in one location; a user far from it pays round-trip latency on every uncached call. D1 location hints can be set at creation.
- Cold starts are small because Workers use isolates, but module top-level code runs at startup and has a startup time limit; keep global scope cheap.
- Check the Workers limits page for CPU, memory, subrequest and size limits for the plan in use before designing around them.

## 10. Security

- Secrets: set with `wrangler secret put` or the dashboard; local values live in `.dev.vars` or `.env`, listed in `.gitignore` as `.dev.vars*` and `.env*`. Never place secrets in `vars`, in `wrangler.jsonc`, or in client bundles. Anything exposed to the browser is public.
- Validate every input at the edge: parse JSON in try/catch, check types and lengths, whitelist enum values, cap body size with `Content-Length` checks and streaming limits.
- SQL: bind parameters in D1 always; for dynamic identifiers (column names, sort order) map from a whitelist.
- CORS: respond to preflight explicitly, echo only allowed origins from a list, avoid `*` with credentials, and set `Vary: Origin`. For R2 browser access, configure the bucket CORS policy with exact origins, methods and headers.
- Authentication: verify tokens (JWT signature, issuer, audience, expiry) in the Worker or put the application behind Cloudflare Access; do not trust headers a client can set.
- Rate limiting: the Rate Limiting binding (`ratelimits` config, Wrangler 4.36.0 or later) is approximate and per location. Key by user, API key or tenant, not by IP. Use WAF rate limiting rules or a Durable Object when stricter control is required.
- R2: keep buckets private by default; use presigned URLs with the shortest workable expiry (range is 1 second to 7 days) and restrict method and content type; scope R2 API tokens to specific buckets; store S3 credentials as secrets.
- SSRF: do not `fetch()` arbitrary user-supplied URLs without an allowlist.
- Dependencies: audit with `npm audit`, lock versions, and avoid packages that rely on unsupported Node APIs.
- Do not log secrets, tokens or full request bodies with personal data.
- Service bindings and Durable Objects are not reachable from the public internet unless a public Worker forwards to them; authenticate at the public edge.

## 11. Testing

- Use `@cloudflare/vitest-plugin` with Vitest 4.1 or later. It runs tests inside the Workers runtime with Miniflare, gives per-test-file isolated storage, and exposes `cloudflare:test` and `cloudflare:workers`. `@cloudflare/vitest-pool-workers` is the older package name; the docs provide a codemod (`@cloudflare/codemods`, `vitest:pool-workers-to-vitest-plugin`) for migrating.
- Configure with `cloudflareTest({ wrangler: { configPath: "./wrangler.jsonc" } })` in `vitest.config.ts`; add `miniflare` overrides for test-only bindings.
- Unit tests call `worker.fetch(request, env, ctx)` with `createExecutionContext()` and `waitOnExecutionContext(ctx)`; integration tests use `exports.default.fetch(url)`.
- Add `@cloudflare/vitest-plugin/types` to the test `tsconfig.json` and include the output of `wrangler types`.
- Test D1 against a migrated local database; apply migrations in a setup file rather than using production data.
- Mock outbound requests with `@msw/cloudflare` (the documented approach) instead of calling real third-party APIs.
- Keep `tsc --noEmit` and `wrangler types --check` in the same CI job as the tests.
- Details and a worked configuration are in [references/pages-assets-testing.md](references/pages-assets-testing.md).

## 12. Review Checklist

- [ ] `compatibility_date` is set, recent, and `nodejs_compat` is present only when needed for dates before 2026-08-04.
- [ ] Config format is consistent (`wrangler.jsonc` for new projects) and `$schema` is set.
- [ ] Every binding is declared in each environment block that needs it.
- [ ] `worker-configuration.d.ts` is current (`wrangler types --check`).
- [ ] No secrets in `vars`, source, config, tests or client bundles; `.dev.vars*` and `.env*` are gitignored.
- [ ] D1 queries use `bind()`; migrations are numbered SQL files; no destructive migration without a Time Travel note.
- [ ] Promises are awaited or passed to `ctx.waitUntil`.
- [ ] Large bodies are streamed; request size is bounded.
- [ ] CORS, authentication and rate limiting are explicit for public endpoints.
- [ ] R2 buckets are private unless intentionally public; presigned URLs are short-lived.
- [ ] KV is not used where read-after-write consistency is required.
- [ ] Observability is enabled and errors are logged without sensitive data.
- [ ] Tests run in the Workers runtime and cover error paths.
- [ ] Limits and prices quoted come from the current docs pages.

## 13. Production Notes

- Deploy: `npx wrangler deploy` uploads the Worker and any assets. Use `--env <name>` for a named environment. `wrangler deploy` deletes dashboard-set `vars` unless `--keep-vars` is passed; secrets are never deleted by deployments.
- Gradual rollout: `wrangler versions upload` creates a version without routing traffic; `wrangler versions deploy` shifts traffic. `wrangler versions secret put` is the matching secret command.
- Rollback: `wrangler rollback [version-id]`; list history with `wrangler deployments`.
- Logs: `wrangler tail` supports `--format`, `--status`, `--method`, `--search`, `--ip` and `--sampling-rate` filters. Workers Logs store and query logs in the dashboard; OpenTelemetry export is the documented route to third-party tools.
- Durable Object code updates default to a deferred strategy with a maximum delay of 300 seconds; persist state to storage rather than relying on in-memory state across deploys.
- D1 recovery: Time Travel restores to any minute within the retention window (30 days on Workers Paid, 7 days on Free per the D1 limits page); bookmarks come from `wrangler d1 time-travel info`. Databases with `version: alpha` in `wrangler d1 info` use the older snapshot API.
- Costs: Workers, R2, D1, KV, Queues and Durable Objects each bill on their own metrics. R2 has no egress fees for reads; D1 bills on rows read and written and on storage. Check the pricing pages of each product before estimating; do not quote prices from memory.
- Limits to know (from the Workers limits page): Free plan 100,000 requests per day and 10 ms CPU per request; Paid plan CPU up to 5 minutes (30 seconds default), 10,000 subrequests per request versus 50 on Free, 128 MB memory per isolate, 6 simultaneous outgoing connections per request, 64 MiB Worker size.
- Local state lives in `.wrangler/state`; delete it to reset local D1, KV and R2.
- CI: authenticate with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` stored as CI secrets, with a token scoped to the needed permissions.

## 14. Examples

Wrangler configuration with several bindings and observability:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "notes-api",
  "main": "src/index.ts",
  "compatibility_date": "2026-10-01",
  "observability": { "enabled": true },
  "d1_databases": [
    { "binding": "DB", "database_name": "notes", "database_id": "<D1_DATABASE_ID>" }
  ],
  "r2_buckets": [
    { "binding": "BUCKET", "bucket_name": "notes-attachments" }
  ],
  "kv_namespaces": [
    { "binding": "CACHE_KV", "id": "<KV_NAMESPACE_ID>" }
  ],
  "ratelimits": [
    { "name": "LIMITER", "namespace_id": "1001", "simple": { "limit": 100, "period": 60 } }
  ],
  "secrets": { "required": ["API_TOKEN"] }
}
```

Worker with routing, validation, parameterised D1 and `waitUntil`:

```ts
interface NewNote {
  title: string;
  body: string;
}

function parseNote(value: unknown): NewNote | null {
  if (typeof value !== "object" || value === null) return null;
  const { title, body } = value as Record<string, unknown>;
  if (typeof title !== "string" || title.length < 1 || title.length > 200) return null;
  if (typeof body !== "string" || body.length > 10_000) return null;
  return { title, body };
}

export default {
  async fetch(request, env, ctx): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/notes" && request.method === "POST") {
      const key = request.headers.get("Authorization") ?? "anonymous";
      const { success } = await env.LIMITER.limit({ key });
      if (!success) return new Response("Too Many Requests", { status: 429 });

      let json: unknown;
      try {
        json = await request.json();
      } catch {
        return Response.json({ error: "invalid JSON" }, { status: 400 });
      }
      const note = parseNote(json);
      if (!note) return Response.json({ error: "invalid note" }, { status: 422 });

      const result = await env.DB.prepare(
        "INSERT INTO notes (title, body) VALUES (?1, ?2) RETURNING id",
      )
        .bind(note.title, note.body)
        .first<{ id: number }>();

      ctx.waitUntil(env.CACHE_KV.delete("notes:list"));
      return Response.json({ id: result?.id }, { status: 201 });
    }

    if (url.pathname === "/notes" && request.method === "GET") {
      const cached = await env.CACHE_KV.get("notes:list", "json");
      if (cached) return Response.json(cached);
      const { results } = await env.DB.prepare(
        "SELECT id, title FROM notes ORDER BY id DESC LIMIT 50",
      ).all();
      ctx.waitUntil(env.CACHE_KV.put("notes:list", JSON.stringify(results), { expirationTtl: 60 }));
      return Response.json(results);
    }

    return new Response("Not Found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

Command sequence for a first deployment:

```bash
npm create cloudflare@latest notes-api
cd notes-api
npx wrangler d1 create notes
npx wrangler d1 migrations create notes init
npx wrangler d1 migrations apply notes --local
npx wrangler types
npx wrangler dev
npx wrangler secret put API_TOKEN
npx wrangler d1 migrations apply notes --remote
npx wrangler deploy
```

Further worked examples (R2 uploads and presigned URLs, D1 sessions, Queues, Vitest, assets) are in the reference files.

## 15. Common Mistakes

- **Secrets in `vars` or committed config**: `vars` are plain text in the config and the dashboard. Use `wrangler secret put` and `.dev.vars` (gitignored).
- **Committing `.dev.vars` or `.env`**: add `.dev.vars*` and `.env*` to `.gitignore` before the first commit.
- **Defining both `.dev.vars` and `.env`**: when `.dev.vars` exists, `.env` values are not loaded into `env` locally. Choose one.
- **Missing `nodejs_compat` on an old compatibility date**: imports of `node:` modules fail. Add the flag, or use a compatibility date of 2026-08-04 or later where it is on by default.
- **Hand-written `Env` interface**: drifts from the config. Run `wrangler types`.
- **Expecting bindings to inherit into `env.<name>` blocks**: bindings and vars are non-inheritable; repeat them per environment.
- **Floating promises**: work after `return` can be cancelled. Use `ctx.waitUntil`.
- **Using KV for read-after-write data**: KV is eventually consistent. Use D1, a Durable Object or sessions with bookmarks.
- **String-built SQL in D1**: SQL injection. Use `bind()` and whitelist identifiers.
- **Comparing R2 `list()` result count to `limit`**: use the `truncated` flag and `cursor` to paginate.
- **Trying to presign URLs with the R2 binding**: unsupported; sign with `aws4fetch` or an AWS SDK using S3 credentials stored as secrets.
- **Using the `r2.dev` URL in production**: it has no WAF, caching or access controls; use a custom domain.
- **Rate limiting by IP address**: shared NATs cause collateral blocking. Key by user, token or tenant.
- **Buffering large bodies with `await response.arrayBuffer()`**: memory errors (Error 1102). Stream.
- **Assuming `wrangler dev` hits production data**: it uses local simulated storage by default. Seed local data deliberately and check the local development docs before pointing a binding at a remote resource.
- **Running destructive D1 SQL on remote without a restore plan**: note a Time Travel bookmark first (`wrangler d1 time-travel info`).
- **Pinning to `@cloudflare/vitest-pool-workers` in new projects**: the documented package is now `@cloudflare/vitest-plugin`.

## 16. References

- [references/workers-wrangler.md](references/workers-wrangler.md): handler types, compatibility settings, Wrangler config keys, environments, commands, secrets, types, versions and rollback, observability and tail.
- [references/r2-storage.md](references/r2-storage.md): R2 binding API, conditional and ranged reads, multipart, listing, S3 API and presigned URLs, CORS, public access and custom domains, limits.
- [references/d1-database.md](references/d1-database.md): D1 queries and batches, migrations, Time Travel, read replication and Sessions API, limits, plus KV, Durable Objects with SQLite, Queues and Hyperdrive in outline.
- [references/pages-assets-testing.md](references/pages-assets-testing.md): Workers static assets configuration, Pages migration, Cloudflare Vite plugin and framework deployment, Vitest plugin setup and test patterns.
- Cloudflare developer docs: https://developers.cloudflare.com/ (Workers, Wrangler, R2, D1, KV, Durable Objects, Queues)
- Documentation source: https://github.com/cloudflare/cloudflare-docs
- Wrangler and tooling source and changelogs: https://github.com/cloudflare/workers-sdk
- Workers limits: https://developers.cloudflare.com/workers/platform/limits/ ; D1 limits: https://developers.cloudflare.com/d1/platform/limits/ ; R2 limits: https://developers.cloudflare.com/r2/platform/limits/
