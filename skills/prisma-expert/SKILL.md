---
name: prisma-expert
description: >-
  Designs Prisma ORM 7 data layers on PostgreSQL: schema.prisma, the prisma-client generator, driver adapters (@prisma/adapter-pg), prisma.config.ts, Prisma Migrate, queries and transactions, $extends client extensions, typed SQL, raw queries and multi-tenant isolation. Use when editing schema.prisma or prisma.config.ts, creating or deploying migrations, setting up PrismaClient, fixing N+1 or slow Prisma queries, writing interactive transactions or tenant-scoped clients, or upgrading from Prisma 6 to 7. Not for SQL design, index tuning or RLS policies themselves (use postgresql-expert), MongoDB (use mongodb-expert; Prisma 7 does not support it), or GraphQL schemas (use graphql-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Prisma Expert

This skill covers Prisma ORM 7 in TypeScript services backed by PostgreSQL: the schema and generator, the driver-adapter client, migrations, query shaping, transactions, client extensions and tenant isolation. Prisma 7 changed project setup substantially compared with Prisma 6 (no Rust engine, required `output` and adapter, `prisma.config.ts`), so the setup steps below are the current ones. Deep material is in three reference files.

> Verified against Prisma ORM 7.10.1 (latest stable 7.x, published 2026-10-19; Prisma 8 is in release-candidate stage, and npm's `latest` tag already points to an 8.0 RC, so pin `7.10.1` explicitly), @prisma/adapter-pg 7.10.1, Node.js 22, TypeScript 5.9; code examples type-checked against a generated 7.10.1 client and tested on PostgreSQL 16 with RLS (2026-10).

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

- Covered: Prisma ORM 7 setup, `schema.prisma`, Prisma Migrate, PrismaClient queries, transactions, `$extends`, typed SQL and raw queries, tenant scoping, testing, upgrade notes from 6.
- Not covered: PostgreSQL index design, query plans, RLS policy design and online DDL (postgresql-expert); MongoDB (Prisma 7 does not support it; stay on Prisma 6 or use mongodb-expert); API layer concerns (graphql-expert, rest-api-expert, nestjs-expert).
- Prisma 8 is pre-release at the time of writing; check its upgrade guide before moving off 7.x.

## 2. Core Expertise

- **Prisma 7 setup changes** (from 6):
  - The Rust query engine is gone; the `prisma-client` generator produces TypeScript client code, and `output` is required (no more generation into `node_modules`). `prisma-client-js` is the legacy generator.
  - `PrismaClient` needs a driver adapter (for PostgreSQL `@prisma/adapter-pg`) or an `accelerateUrl`; `datasources` and `datasourceUrl` constructor options and `directUrl` are removed.
  - `prisma.config.ts` (with `defineConfig` from `prisma/config`) holds `schema`, `datasource.url`, `datasource.shadowDatabaseUrl`, `migrations.path`, `migrations.seed` and `typedSql.path`; the `prisma` key in `package.json` is removed.
  - The CLI no longer loads `.env` files (import `dotenv/config` or use `--env-file`); `generate` and seeding do not run implicitly after `install` or `migrate`.
  - ESM package: Node.js 20.19+ and TypeScript 5.4+ are required (the upgrade guide recommends Node 22.x and TypeScript 5.9.x); set `"type": "module"` and an ESM-compatible `tsconfig`.
  - Mapped enums (`@map` on members, `@@map` on the enum), and the `metrics` preview feature is removed.
- **Schema**: models, relations (including composite keys), enums, `@@index`, `@@unique`, `@db.*` native types, `@default(dbgenerated("uuidv7()"))` for PostgreSQL 18 time-ordered ids. See [references/schema-and-migrations.md](references/schema-and-migrations.md).
- **Migrations**: `migrate dev` (development), `migrate deploy` (CI and production), `migrate status`, `migrate resolve`, `migrate diff`, `db push` (prototypes only), hand-edited SQL via `migrate dev --create-only`.
- **Queries**: `select`, `omit`, `include`, filters, cursor pagination, `groupBy`, aggregates, nested writes, `createMany`, `upsert`, atomic operators (`increment`).
- **Transactions**: sequential `$transaction([...])` and interactive `$transaction(async (tx) => ...)` with `maxWait`, `timeout` and `isolationLevel`; error `P2034` for write conflicts and deadlocks.
- **Client extensions**: `$extends` with `query`, `result`, `model` and `client` components; `Prisma.defineExtension`. See [references/client-extensions-and-multi-tenancy.md](references/client-extensions-and-multi-tenancy.md).
- **Raw SQL**: `$queryRaw`/`$executeRaw` tagged templates, `Prisma.sql`, typed SQL (`prisma/sql/*.sql`, `prisma generate --sql`, `$queryRawTyped`). See [references/performance-and-raw-sql.md](references/performance-and-raw-sql.md).
- **Error codes**: `P2002` unique violation, `P2003` foreign key, `P2025` record not found, `P2034` transaction conflict, thrown as `Prisma.PrismaClientKnownRequestError` with `code` and `meta`.

## 3. Workflow

1. Model the domain in `schema.prisma`, mirroring the database design (types, constraints, indexes). Keep database-specific features (RLS, partial indexes, CHECK constraints) in SQL migrations.
2. Run `prisma migrate dev --name <change>` locally; inspect the generated SQL; use `--create-only` when the SQL needs hand edits (concurrent indexes, backfills, constraints).
3. Run `prisma generate` explicitly (it no longer runs implicitly) and commit or build the output according to the project's convention.
4. Write queries with explicit `select` (or `omit`), bounded `take`, and indexes that match the `where` and `orderBy`.
5. Wrap multi-step invariants in a transaction; keep interactive transactions short and free of network calls.
6. Test against a real PostgreSQL instance with migrations applied (`migrate deploy`), including tenant isolation tests.
7. Deploy by running `prisma migrate deploy` as a separate release step before starting the new application version.
8. Review the SQL for risky operations (table rewrites, non-concurrent indexes, new NOT NULL) with the postgresql-expert online-migration rules.

## 4. Decision Rules

- Use `select`/`omit` for anything returned over an API; use `include` only when the full related rows are needed.
- Use cursor pagination (`cursor`, `take`, stable unique `orderBy`) for large or growing tables; `skip/take` only for small, bounded result sets.
- Use a sequential `$transaction([...])` for independent writes; use the interactive form when later statements depend on earlier results.
- Use Prisma Client for CRUD and relation loading; use typed SQL or `$queryRaw` for window functions, CTEs, bulk upserts with `ON CONFLICT` semantics Prisma cannot express, and reporting queries.
- Use `migrate dev` locally, `migrate deploy` everywhere else; `db push` only for throwaway prototypes (it records no history).
- Prefer shared tables with `tenantId` plus PostgreSQL RLS for many small tenants; schema-per-tenant or database-per-tenant only for strict isolation or per-tenant restore requirements (each additional database needs its own client and adapter).
- Prefer a database default or generated id (`uuidv7()`, `autoincrement()`) over client-generated ids unless ids must exist before the insert.
- Keep the pooled runtime connection and the direct migration connection separate: the adapter gets the pooled URL at runtime, `prisma.config.ts` gets the direct URL for the CLI.

## 5. Coding Standards

- One `PrismaClient` per process, exported from a single module; never construct it per request.
- Import the client and `Prisma` namespace from the generated `output` directory, not from `@prisma/client` (when using the `prisma-client` generator).
- Name models in PascalCase singular, fields in camelCase, and map to snake_case tables and columns with `@@map` and `@map` when the database convention differs.
- Declare `onDelete` explicitly on every relation. Use `Restrict` unless cascading is a deliberate rule.
- Use `@db.Timestamptz(6)` for instants, `BigInt` or integer minor units for money (never `Float`), `@db.Uuid` for uuid columns.
- Validate input at the boundary (for example with Zod) before passing it to Prisma; never pass request bodies directly as `data` or `where`.
- Catch `Prisma.PrismaClientKnownRequestError` by `code` and map to domain errors; do not expose raw Prisma messages to clients.
- Reuse shared selections with `Prisma.validator` or `satisfies Prisma.UserSelect`, and derive result types with `Prisma.UserGetPayload<...>`.

## 6. Project Structure

```
prisma/
  schema.prisma
  migrations/            # generated SQL plus hand edits, committed
  sql/                   # typed SQL files (invoiceTotals.sql)
  seed.ts                # development seed (never run in production)
prisma.config.ts         # schema path, datasource.url, migrations.seed, typedSql.path
src/
  generated/prisma/      # generator output (commit or build in CI, per team convention)
  db/
    client.ts            # adapter + PrismaClient singleton
    tenant.ts            # tenant extension, withTenant(), retry helper
  modules/<feature>/     # repositories or services calling the client
```

## 7. Design Patterns

- **Repository per aggregate** that takes a client or transaction handle, so the same code runs inside and outside transactions.
- **Unit of work**: a service opens one transaction, passes `tx` to repositories, commits once.
- **Tenant-scoped client**: `prisma.$extends(tenantScope(tenantId))` plus a per-transaction `set_config` for RLS (section 14).
- **Result extensions** for computed fields (`fullName`) and to hide sensitive fields from every query of a model.
- **Outbox**: write domain rows and an `OutboxEvent` row in one transaction; a worker publishes events afterwards.
- **Optimistic concurrency**: a `version Int` column, `updateMany({ where: { id, version }, data: { ..., version: { increment: 1 } } })`, treat `count === 0` as a conflict.
- **Idempotent writes**: unique key plus `upsert` or catch `P2002`.

## 8. Best Practices

- Review migration SQL in pull requests; commit the `migrations` folder and `migration_lock.toml`.
- Make schema changes backward compatible with the running application version (expand, deploy, contract).
- Back every `where`, `orderBy` and relation foreign key used in hot paths with an index (`@@index`).
- Keep interactive transactions under a few seconds and do not call external services inside them.
- Prefer `createMany`/`createManyAndReturn` and `updateMany` over loops of single writes.
- Use `findUniqueOrThrow` and `findFirstOrThrow` when absence is an error, so callers handle `P2025` once.
- Log `warn` and `error` in production; enable `query` logging only temporarily and never log bound parameters of sensitive data.
- Pin `prisma`, `@prisma/client` and `@prisma/adapter-pg` to the same version.

## 9. Performance

- Avoid N+1: load relations with `include`/`select` in one call, or batch with `findMany({ where: { id: { in: ids } } })`. Never `await` queries inside `.map` or `for` loops over rows.
- Select only the columns needed; deep or wide `include` trees multiply rows and payload.
- Set an explicit `take` limit on every `findMany` that serves user traffic.
- Use `groupBy`, `aggregate` and `_count` in the database instead of loading rows to aggregate in JavaScript.
- Pool size is configured on the adapter (`new PrismaPg({ connectionString, max })`, the options of the `pg` pool), not with the old engine's URL parameters such as `connection_limit` (check the adapter docs for the options your version supports); size it to the database's connection budget across all instances, and use PgBouncer or the managed pooler for many short-lived instances.
- Use `EXPLAIN (ANALYZE, BUFFERS)` on the SQL Prisma logs (`log: ['query']` in a test environment) to verify index use; details in [references/performance-and-raw-sql.md](references/performance-and-raw-sql.md).
- Use `$queryRawTyped` or `$queryRaw` for heavy reporting queries and bulk operations that the query API would split into many statements.

## 10. Security

- Use tagged templates for raw SQL (`` $queryRaw`... ${value}` ``). `$queryRawUnsafe` and `$executeRawUnsafe` accept only static SQL text with `$1` placeholders and separate parameters; never concatenate input into the string.
- Tenant isolation covers writes as well as reads: inject `tenantId` on create, scope `where` on update, updateMany, upsert, delete and deleteMany, and back it with PostgreSQL RLS driven by a per-transaction `set_config` (section 14 and the multi-tenancy reference). Raw queries bypass client extensions, so RLS is the layer that protects them.
- The application database role must not own the tables and must not have `BYPASSRLS`; migrations run with a separate owner role.
- Never put `DATABASE_URL` or credentials in client bundles, logs or committed `.env` files; load from the environment or a secret manager. Do not import the generated client into browser code.
- Whitelist sortable and filterable fields; do not spread user-supplied objects into `where`, `orderBy`, `select` or `data` (mass assignment and operator injection such as `{ contains }` or relation filters).
- Use TLS to the database (`ssl` in the adapter's pool options, with certificate verification) in production.
- Treat `omit` and result extensions as a convenience, not an access control; enforce field-level access in the service layer.

## 11. Testing

- Run integration tests against real PostgreSQL (container or CI service) with `prisma migrate deploy`; SQLite or mocks hide constraint, transaction and RLS behavior.
- Isolate tests with one database per worker, truncation between tests, or a transaction rolled back per test; do not use `migrate reset` outside development.
- Unit-test services with the client behind an interface or a mocked repository; keep Prisma-specific behavior (constraints, P-codes) in integration tests.
- Test tenant isolation explicitly: tenant B cannot read, update, delete or upsert tenant A's rows, cannot create rows with A's `tenantId`, and a query without tenant context returns nothing under RLS.
- Test error mapping for `P2002`, `P2003`, `P2025` and `P2034` retries.

## 12. Review Checklist

- [ ] `prisma-client` generator has `output`; client built with `PrismaPg` adapter; one client instance per process.
- [ ] `prisma.config.ts` provides `datasource.url` from the environment; no secrets committed.
- [ ] Migration SQL reviewed (no table rewrite, concurrent indexes, `NOT VALID` constraints for large tables).
- [ ] Queries use `select`/`omit`, bounded `take`, indexed filters; no queries in loops.
- [ ] Transactions are short; `P2034` is retried where serializable isolation is used.
- [ ] Tenant-owned models: all write operations scoped, `tenantId` indexed, RLS policies with `USING` and `WITH CHECK`.
- [ ] No `$queryRawUnsafe` with interpolated input; no user objects spread into `where` or `data`.
- [ ] Error handling maps Prisma codes to domain errors.

## 13. Production Notes

- Release order: `prisma migrate deploy` (one runner, not on every instance start), then roll out the application. Failed migrations are resolved with `prisma migrate resolve --applied` or `--rolled-back` after manual repair.
- Pooling: the application uses the pooled URL through the adapter; `prisma.config.ts` uses the direct connection for CLI commands (`migrate`, `db pull`), which need session features and advisory locks.
- Serverless and edge: use an adapter that matches the runtime (the `pg` adapter needs TCP; check the Prisma docs for the HTTP and edge adapters) and create the client once per instance outside the handler.
- Graceful shutdown: call `await prisma.$disconnect()` on `SIGTERM` after in-flight requests finish.
- Monitor query latency and pool wait time from the adapter's pool, slow query logs in PostgreSQL (`pg_stat_statements`), and `P2034` rates.
- Upgrade path from 6: switch the generator to `prisma-client` with `output`, add the adapter, move URLs into `prisma.config.ts`, load environment variables yourself, make the package ESM, and run `prisma generate` and `migrate` explicitly (see [references/schema-and-migrations.md](references/schema-and-migrations.md)).

## 14. Examples

Client setup (`src/db/client.ts`). The URL comes from the environment; the pool is configured on the adapter:

```ts
import { PrismaPg } from '@prisma/adapter-pg'
import { PrismaClient } from '../generated/prisma/client'

const connectionString = process.env.DATABASE_URL
if (!connectionString) throw new Error('DATABASE_URL is not set')

const adapter = new PrismaPg({ connectionString, max: 10 })

export const prisma = new PrismaClient({ adapter, log: ['warn', 'error'] })
```

Tenant scoping that covers reads and writes (`src/db/tenant.ts`). Every operation is handled explicitly and unknown operations fail closed; nested writes and raw SQL are not intercepted, which is why RLS backs it:

```ts
import { Prisma } from '../generated/prisma/client'
import { prisma } from './client'

const TENANT_MODELS = new Set<string>(['Customer', 'Invoice'])

type Args = { where?: Record<string, unknown>; data?: unknown; create?: Record<string, unknown>; update?: unknown }

function forbidTenantChange(data: unknown, tenantId: string): void {
  for (const item of Array.isArray(data) ? data : [data]) {
    if (item && typeof item === 'object' && 'tenantId' in item && item.tenantId !== tenantId) {
      throw new Error('tenant-scope: tenantId in input does not match the current tenant')
    }
  }
}

const withTenantId = <T>(data: T, tenantId: string): T =>
  (Array.isArray(data) ? data.map((d) => ({ ...d, tenantId })) : { ...(data as object), tenantId }) as T

export const tenantScope = (tenantId: string) =>
  Prisma.defineExtension({
    name: 'tenant-scope',
    query: {
      $allModels: {
        async $allOperations({ model, operation, args, query }) {
          if (!TENANT_MODELS.has(model)) return query(args)
          const a = args as unknown as Args
          switch (operation) {
            case 'findUnique': case 'findUniqueOrThrow': case 'findFirst': case 'findFirstOrThrow':
            case 'findMany': case 'count': case 'aggregate': case 'groupBy':
            case 'delete': case 'deleteMany':
              a.where = { ...a.where, tenantId }                  // update/delete by id also match on tenant
              break
            case 'update': case 'updateMany': case 'updateManyAndReturn':
              forbidTenantChange(a.data, tenantId)                // cannot move rows to another tenant
              a.where = { ...a.where, tenantId }
              break
            case 'create': case 'createMany': case 'createManyAndReturn':
              forbidTenantChange(a.data, tenantId)
              a.data = withTenantId(a.data, tenantId)             // inject tenantId on insert
              break
            case 'upsert':
              forbidTenantChange(a.create, tenantId)
              forbidTenantChange(a.update, tenantId)
              a.where = { ...a.where, tenantId }
              a.create = { ...a.create, tenantId }
              break
            default:
              throw new Error(`tenant-scope: unsupported operation ${operation}`)
          }
          return query(args)
        },
      },
    },
  })
```

Per-transaction database context and retry (same file). `set_config(..., true)` is local to the transaction, so a pooled connection never carries a tenant over; the RLS policies are in the multi-tenancy reference:

```ts
const scoped = (tenantId: string) => prisma.$extends(tenantScope(tenantId))
export type TenantTx = Omit<ReturnType<typeof scoped>, '$connect' | '$disconnect' | '$on' | '$transaction' | '$extends'>
type TxOptions = { maxWait?: number; timeout?: number; isolationLevel?: Prisma.TransactionIsolationLevel }

export async function withTenant<T>(
  tenantId: string,                                  // from the verified session, never from the request body
  work: (db: TenantTx) => Promise<T>,
  options: TxOptions = { maxWait: 2_000, timeout: 10_000 },
): Promise<T> {
  return scoped(tenantId).$transaction(async (tx) => {
    await tx.$queryRaw`SELECT set_config('app.tenant_id', ${tenantId}, true)`
    return work(tx)
  }, options)
}

export async function retryable<T>(fn: () => Promise<T>, attempts = 3): Promise<T> {
  for (let i = 1; ; i++) {
    try {
      return await fn()
    } catch (e) {
      const again = e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2034'
      if (!again || i >= attempts) throw e
      await new Promise((r) => setTimeout(r, 25 * 2 ** i))
    }
  }
}

// usage: update({ where: { id } }) is scoped to the tenant, so another tenant's id yields P2025
// await withTenant(tenantId, (db) => db.invoice.update({ where: { id }, data: { status: 'PAID' } }))
```

## 15. Common Mistakes

- Tenant filter on reads only, or `update({ where: { id } })` without the tenant: writes and deletes by id cross tenants. Scope every operation and add RLS.
- Trusting the tenant id from the request body or a caller-supplied parameter instead of the verified session.
- Application role that owns the tables or has `BYPASSRLS`, which makes RLS a no-op.
- Using the Prisma 6 setup on Prisma 7: `prisma-client-js` without `output`, `url` in the datasource block, `new PrismaClient()` without an adapter, relying on `.env` autoload, or expecting `migrate dev` to run `generate` and seed.
- `db push` against a shared or production database instead of reviewed migrations (no history, and it can drop data).
- Creating a `PrismaClient` per request or per module (connection pool exhaustion); forgetting `$disconnect` in scripts and tests.
- `include` for everything, unbounded `findMany`, queries inside loops (N+1).
- Interactive transactions that call external APIs or wait on user input, exceeding `timeout` and holding locks.
- Interpolating input into `$queryRawUnsafe`; spreading request bodies into `where` or `data`.
- Plain index creation in a migration on a large live table; use a hand-edited `CREATE INDEX CONCURRENTLY` migration.
- `dbgenerated("uuidv7()")` (or a custom function default) on a database older than PostgreSQL 18, or a default referencing a function created in a later migration.
- Floating-point money, `DateTime` without `@db.Timestamptz`, missing `onDelete` rules.
- Mixing Prisma 7 CLI with a Prisma 8 pre-release in the same repo without reading the upgrade guide.

## 16. References

- [references/schema-and-migrations.md](references/schema-and-migrations.md): schema example, `prisma.config.ts`, migrate commands, hand-edited SQL, expand and contract, Prisma 6 to 7 upgrade.
- [references/client-extensions-and-multi-tenancy.md](references/client-extensions-and-multi-tenancy.md): `$extends` components, tenant extension details, RLS wiring, tests, nested-write caveats, other isolation models.
- [references/performance-and-raw-sql.md](references/performance-and-raw-sql.md): query shaping, pagination, transactions, pooling, typed SQL, raw queries, diagnosing slow queries.
- Prisma docs: https://www.prisma.io/docs ; release notes: https://github.com/prisma/prisma/releases
