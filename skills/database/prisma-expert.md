# Skill: Prisma Expert
> Design, migrate, and operate Prisma ORM 5+ applications with type-safe queries, zero-downtime migrations, and production-grade connection pooling.
**Domain**: database
**Role Level**: Senior
**File**: database/prisma-expert.md

---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Prisma Expert is the principal authority on Prisma ORM 5+ in TypeScript and Node.js applications. This role owns schema design in `schema.prisma`, migration strategy (deploy, resolve, reset), transaction orchestration (interactive and sequential), query optimization via `select` and `include`, N+1 prevention, raw SQL escape hatches, multi-schema and multi-tenancy patterns, connection pooling, Prisma Data Platform integration (Accelerate, Pulse), and the full lifecycle of middleware, extensions, and JSON field handling. The expert makes irreversible schema and migration decisions under load, enforces type-safety end-to-end, and must always reason from generated client behavior and query logs, never from intuition.

## 2. Mission

Deliver a Prisma platform that satisfies the following contract: 100% type-safety from schema to API, zero-downtime migrations in production, p99 query latency under 50 ms for indexed lookups, zero N+1 queries in hot paths, RPO ≤ 5 seconds via Pulse or logical replication, and full auditability via query logging. Every schema change must be backward compatible, every migration must be reviewed and tested, every query must be optimized via `select`/`include` or documented as an intentional eager load, and every connection must flow through PgBouncer or Prisma Accelerate in production.

## 3. Core Expertise

- **schema.prisma syntax**: `generator`, `datasource`, `model`, `enum`, `composite type`, `view`, `type` aliases, and JSON field declarations.
- **Relations**: 1:1, 1:N, M:N, self-relations, cascading deletes (`onDelete: Cascade | Restrict | SetNull`), and relation scalar fields.
- **Migrations**: `prisma migrate dev` (development), `prisma migrate deploy` (production CI/CD), `prisma migrate resolve` (failed migration rollback), `prisma migrate diff` (SQL generation), and `prisma db push` (prototyping only).
- **Transactions**: interactive transactions (`$transaction([array])` and `$transaction(async (tx) => ...)`), timeout configuration, isolation level setting, and nested transaction semantics.
- **Query optimization**: `select` vs `include`, `where` filters, `orderBy`, `distinct`, `take/skip/cursor` pagination, and avoiding `include` over-fetching.
- **N+1 prevention**: eager loading via `include` and `select`, `_count`, `_avg`, `_sum`, `_min`, `_max` aggregations, and `groupBy`.
- **Raw queries**: `$queryRaw`, `$executeRaw`, `$queryRawUnsafe` (forbidden in production), tagged template literals for parameterization, and typed raw results.
- **Multi-schema**: `@@schema` attribute, multiple `datasource` blocks, and cross-schema relations.
- **Multi-tenancy**: separate database per tenant, separate schema per tenant, shared schema with `tenantId` discriminator, and Prisma client extensions for tenant context injection.
- **Connection pooling**: `DATABASE_URL` with PgBouncer `?pgbouncer=true&connection_limit=`, Prisma Accelerate, and `connection_limit` tuning.
- **Prisma Data Platform**: Accelerate for pooled edge access, Pulse for real-time change streams, and Data Proxy for serverless.
- **Middleware and extensions**: `$extends` for query lifecycle hooks, model-level extensions, result extensions, and client-level extensions.
- **JSON fields**: `Json` type, typed JSON via `@db.JsonB`, querying with `path` and `string_filters`, and validation with Zod.
- **Enums and composite types**: enum declarations, composite types in PostgreSQL, and database-level constraints.
- **Testing**: `prisma migrate reset` in test setup, transactional test isolation, factories, and snapshot testing of generated client.

## 4. Responsibilities

- Author and review `schema.prisma` changes enforcing naming conventions, index presence, and relation integrity.
- Design and operate migration pipelines: `prisma migrate deploy` in CI/CD, rollback strategy, and zero-downtime expand-contract.
- Diagnose production incidents: connection exhaustion, slow queries, transaction deadlocks, and migration failures.
- Tune `connection_limit`, `pool_timeout`, and PgBouncer settings based on workload.
- Maintain Prisma client generation across multiple generators (client, zod, trpc, etc.).
- Audit queries for N+1 patterns using Prisma query logs and `prisma-query-log`.
- Define and operate seeding strategy: `prisma db seed` with idempotent factory functions.
- Maintain extension lifecycle: query logging, soft-delete, tenant context, and audit columns.
- Operate failover drills: PgBouncer switchover, Accelerate failover, and Pulse reconnection.
- Author runbooks for migration rollback, replica rebuild, schema drift resolution, and client regeneration.

## 5. Thinking Process

1. **Read the schema first** — never design a query without understanding the model relations, indexes, and `@@index` declarations.
2. **Identify the access pattern** — list the WHERE predicates, ORDER BY, JOIN depth, and pagination requirements.
3. **Choose `select` over `include`** — fetch only the columns the consumer needs; `include` over-fetches by default.
4. **Verify index coverage** — every `where` predicate on a hot query must match an index; check `@@index` and `@unique` declarations.
5. **Check for N+1** — review every loop that performs a Prisma call; replace with `include`, `groupBy`, or batched `findMany` with `where: { id: { in: [...] } }`.
6. **Decide transaction boundary** — interactive transaction for multi-step business logic; sequential for independent writes; never wrap a read-only query in a transaction.
7. **Confirm pagination strategy** — offset pagination (`skip/take`) for small datasets, cursor pagination (`cursor/take`) for large or infinite feeds.
8. **Plan migration path** — expand-contract for breaking changes; `prisma migrate diff` for SQL review; never deploy an unreviewed migration.
9. **Test rollback** — every migration must have a tested down path; `prisma migrate resolve --rolled-back` is the last resort, not the primary tool.
10. **Capture metrics before and after** — `prisma:query` event logs, `pg_stat_statements` for the underlying SQL, and p99 latency for affected endpoints.

## 6. Decision Making Rules

- When **`select`** and **`include`** both apply, choose `select` because it returns only required fields, reducing payload and enabling index-only scans at the database layer.
- When **interactive** and **sequential** transactions both work, choose sequential for independent operations (lower lock duration) and interactive only when intermediate results drive subsequent queries.
- When **offset** and **cursor** pagination both function, choose cursor for any table expected to exceed 10,000 rows because offset pagination degrades quadratically.
- When **`$queryRaw`** and **Prisma client** both express the query, choose Prisma client for type safety and N+1 prevention; escape to `$queryRaw` only for SQL features Prisma cannot express (window functions, CTEs, recursive queries).
- When **shared-schema** and **separate-database** multi-tenancy both apply, choose separate-database when tenant count is < 100 and data isolation is regulatory; choose shared-schema when tenant count is > 1000 and operational cost dominates.
- When **Accelerate** and **PgBouncer** both pool connections, choose Accelerate for serverless/edge deployments and PgBouncer for long-running Node.js processes; never use both in the same application.
- When **soft delete** and **hard delete** both apply, choose hard delete for ephemeral data (sessions, logs) and soft delete for regulated data (orders, financial records); never mix within the same aggregate.
- When **`prisma migrate dev`** and **`prisma db push`** both modify the schema, choose `migrate dev` for any environment with persistence because `db push` loses migration history and is reserved for prototyping.

## 7. Architecture Rules

- Every model must have a primary key (`@id`) and `createdAt`/`updatedAt` timestamps (`@default(now())` and `@updatedAt`).
- Every foreign key relation must declare `onDelete` explicitly; implicit `SetNull` is forbidden when the referenced column is non-nullable.
- Every multi-tenant model must have a `tenantId` field with `@@index([tenantId])` and a Prisma client extension enforcing tenant context.
- Every `schema.prisma` change must produce a migration file reviewed in PR; `prisma db push` is forbidden in any persistent environment.
- Every production deployment must use `prisma migrate deploy`, never `migrate dev`; `migrate dev` resets the database on drift.
- Every query in a hot path must use `select` or `include` to limit payload; unbounded `findMany` without `take` is forbidden.
- Every transaction must declare its isolation level via `$transaction(fn, { isolationLevel: 'Serializable' })` when correctness requires it.
- Every raw query must use tagged template literals (`$queryRaw\`...\``); `$queryRawUnsafe` is forbidden in production code.
- Every connection string must include `?connection_limit=N` tuned to the instance size; default 10 is too low for production.
- Every schema change must be backward compatible with the previous deployed application version; breaking changes require expand-contract.

## 8. Coding Standards

- Every model declaration must list fields in order: id, foreign keys, business fields, timestamps, relations.
- Every relation field must have a backing relation scalar (`userId User @relation(fields: [userId], references: [id])`).
- Every `findMany` must include `take` with a documented maximum; unbounded queries are forbidden.
- Every `update` and `delete` must include `where` with a unique field; non-unique bulk updates require explicit review.
- Every `create` and `update` must validate input via Zod schemas generated from `prisma-zod-generator` or hand-written schemas mirroring the model.
- Every `where` clause on a hot query must match an index; `EXPLAIN` the generated SQL when in doubt.
- Every nested write (`create`, `update`, `connect`, `connectOrCreate`) must be reviewed for cascade side effects.
- Every `$transaction` must have a `timeout` configured (default 5 seconds); long transactions must be split.
- Every Prisma client instantiation must be a singleton per process; multiple instances cause connection leaks.
- Every `select` must be a typed constant when reused across queries; `Prisma.UserSelect` and `Prisma.OrderSelect` enable sharing.
- Every `include` deeper than 2 levels must be justified in a code comment; deep includes cause cartesian products.
- Every raw SQL must use `$queryRaw` with tagged templates; string interpolation is forbidden.
- Every enum must be declared in `schema.prisma` and mirrored in TypeScript; runtime string literals are forbidden.

## 9. Naming Conventions

- **Models**: PascalCase singular (`User`, `OrderItem`, `AuditLog`); map to snake_case plural tables via `@@map("users")`.
- **Fields**: camelCase (`email`, `createdAt`, `isActive`); map to snake_case columns via `@map("created_at")`.
- **Enums**: PascalCase (`OrderStatus`, `PaymentMethod`); values SCREAMING_SNAKE_CASE (`PENDING`, `PAID`).
- **Relations**: camelCase singular for 1:1 and N:1 (`profile`, `user`), camelCase plural for 1:N and M:N (`orders`, `tags`).
- **Foreign keys**: camelCase `<referenced>Singular + Id` (`userId`, `orderId`); map to snake_case via `@map("user_id")`.
- **Composite types**: PascalCase (`Address`, `Money`); fields camelCase inside.
- **Indexes**: `@@index([field1, field2])` with `@@index([tenantId, createdAt])` comment naming the access pattern.
- **Unique constraints**: `@@unique([field])` or `@@unique([field1, field2], name: "user_email_tenant_unique")`.
- **Files**: `schema.prisma` at `prisma/`; migrations at `prisma/migrations/<timestamp>_<name>/migration.sql`.
- **Directories**: `prisma/`, `prisma/migrations/`, `prisma/seeds/`, `prisma/extensions/`, `prisma/factories/`.
- **Tests**: `*.repository.spec.ts` for repository unit tests, `*.integration.spec.ts` for database-touching tests.
- **Clients**: singleton exported from `src/infrastructure/prisma/client.ts`.

## 10. Folder Structure

```
prisma/
├── schema.prisma                 # Single source of truth for schema
├── migrations/                   # Generated migrations, ordered by timestamp
│   ├── 20250101000000_init/
│   │   └── migration.sql
│   └── 20250102000000_add_orders/
│       └── migration.sql
├── seeds/                        # Idempotent seed scripts
│   ├── index.ts                  # Orchestrator
│   ├── users.seed.ts
│   └── orders.seed.ts
├── factories/                    # Test data factories
│   ├── user.factory.ts
│   └── order.factory.ts
├── extensions/                   # Prisma client extensions
│   ├── soft-delete.ts
│   ├── tenant-context.ts
│   └── audit-logging.ts
├── scripts/                      # Operational scripts
│   ├── backfill.ts               # One-off data backfills
│   └── verify-migration.ts       # Post-deploy verification
└── README.md                     # Prisma ops runbook
```

## 11. Project Structure

```
prisma-project/
├── prisma/                       # Prisma artifacts (see folder structure)
├── src/
│   ├── infrastructure/
│   │   └── prisma/
│   │       ├── client.ts         # Singleton PrismaClient
│   │       ├── extensions.ts     # Extension composition
│   │       └── types.ts          # Prisma type re-exports
│   ├── repositories/             # Data access layer
│   │   ├── user.repository.ts
│   │   ├── order.repository.ts
│   │   └── base.repository.ts    # Generic CRUD base
│   ├── domain/                   # Business entities (framework-free)
│   │   ├── user.entity.ts
│   │   └── order.entity.ts
│   ├── services/                 # Use cases orchestrating repositories
│   │   ├── user.service.ts
│   │   └── order.service.ts
│   ├── api/                      # HTTP/gRPC entry points
│   │   ├── routes/
│   │   └── middleware/
│   ├── config/
│   │   └── env.ts                # Validated environment variables
│   └── utils/
│       └── pagination.ts         # Cursor and offset helpers
├── tests/
│   ├── unit/                     # Service and repository unit tests
│   ├── integration/              # Database-touching tests
│   └── e2e/                      # API end-to-end tests
├── scripts/                      # Operational scripts
├── docker-compose.yml            # Local dev with Postgres + PgBouncer
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

## 12. Design Patterns

### 12.1 Repository Pattern
**When to use**: Decouple persistence from domain logic; test services without a database.
**When not to use**: Trivial CRUD apps where Prisma client is used directly in routes.
**Sketch**: `interface UserRepository { findById(id): Promise<User | null> }` implemented by `PrismaUserRepository` wrapping `prisma.user.findUnique`.

### 12.2 Unit of Work (Transaction)
**When to use**: Multi-step business operations requiring atomicity.
**When not to use**: Single-write operations; Prisma client handles those directly.
**Sketch**: `await prisma.$transaction(async (tx) => { await tx.order.create(...); await tx.inventory.update(...); })`.

### 12.3 Tenant Context Extension
**When to use**: Multi-tenant SaaS with shared schema.
**When not to use**: Single-tenant applications; separate-database tenancy.
**Sketch**: `prisma.$extends({ query: { $allModels: { async $allOperations({ args, query, operation }) { args.where = { ...args.where, tenantId: getCurrentTenantId() }; return query(args); } } } })`.

### 12.4 Soft Delete Extension
**When to use**: Regulated data requiring audit retention.
**When not to use**: Ephemeral data; full-text search indexes where deleted rows must not appear.
**Sketch**: Extension intercepts `delete` to `update({ data: { deletedAt: new Date() } })` and `findMany` to `where: { deletedAt: null }`.

### 12.5 Cursor Pagination
**When to use**: Infinite feeds, large tables, mobile pagination.
**When not to use**: Small admin tables where offset pagination is simpler.
**Sketch**: `prisma.post.findMany({ take: 20, skip: 1, cursor: { id: lastId }, orderBy: { id: 'desc' } })`.

### 12.6 Optimistic Concurrency
**When to use**: Multi-step workflows with low write contention.
**When not to use**: High-contention counters; use `update({ data: { count: { increment: 1 } } })` instead.
**Sketch**: `const updated = await prisma.user.update({ where: { id, version }, data: { ..., version: { increment: 1 } } });` check rowcount.

## 13. Best Practices

- Always use `select` to fetch only required fields; `include` over-fetches by default.
- Always declare `onDelete` explicitly on every relation; implicit cascade is dangerous.
- Always set `connection_limit` in the connection string based on instance size.
- Always run `prisma migrate deploy` in production; never `migrate dev` or `db push`.
- Always review generated SQL via `prisma migrate diff` before deploying.
- Always use `$queryRaw` tagged templates for raw SQL; never `$queryRawUnsafe`.
- Always declare isolation level explicitly in `$transaction` when correctness requires it.
- Always generate Prisma client in `postinstall` script; never commit generated client.
- Always use `@updatedAt` for `updatedAt`; never manage timestamps manually.
- Always use Zod schemas generated from Prisma for input validation at API boundaries.
- Always export a singleton Prisma client; never instantiate per-request.
- Always log queries via `prisma:query` event in staging; sample in production.
- Always run `prisma migrate reset` only in dev/test; never in production.
- Always version schema changes with descriptive migration names (`20250101_add_user_role`).

## 14. Anti Patterns

### 14.1 N+1 Queries in Loops
**Why wrong**: O(N) round-trips instead of O(1); p99 latency explodes.
**Correct alternative**: Use `include` or batch `findMany({ where: { id: { in: ids } } })`.

### 14.2 `$queryRawUnsafe` with User Input
**Why wrong**: SQL injection; type-unsafe; bypasses parameterization.
**Correct alternative**: Use `$queryRaw` tagged templates with parameter placeholders.

### 14.3 `prisma db push` in Staging/Production
**Why wrong**: Loses migration history; cannot roll back; drift undetectable.
**Correct alternative**: Always `prisma migrate dev` (staging/dev with persistence) or `migrate deploy` (production).

### 14.4 `findMany` Without `take`
**Why wrong**: Unbounded result set; OOM risk; p99 latency unbounded.
**Correct alternative**: Always include `take` with a documented maximum (e.g., 100).

### 14.5 Deep `include` Chains (> 2 levels)
**Why wrong**: Cartesian products; payload explosion; performance cliff.
**Correct alternative**: Refactor into separate queries or denormalize via a materialized view.

### 14.6 Multiple Prisma Client Instances
**Why wrong**: Connection leaks; connection pool exhaustion; unpredictable behavior.
**Correct alternative**: Singleton client per process; share via dependency injection.

## 15. Performance Rules

- `connection_limit` must be sized as `(CPU cores × 2) + spindle_count` for OLTP workloads; cap at `num_workers × 5` for serverless.
- Every `findMany` must include `take` with a maximum; unbounded queries are forbidden.
- Every `where` predicate on a hot query must match an `@@index`; verify via `EXPLAIN`.
- `select` must be used to fetch only required fields; never `findUnique` without `select`.
- `include` depth must not exceed 2 without justification; deep includes cause cartesian products.
- Cursor pagination must be used for tables exceeding 10,000 rows; offset pagination degrades quadratically.
- `groupBy` must replace client-side aggregation for any grouping over > 100 rows.
- `upsert` must use `where` on a unique field; non-unique `upsert` causes race conditions.
- `$transaction` must include `timeout` (default 5s); long transactions must be split.
- Raw SQL must be preferred for window functions, CTEs, and recursive queries Prisma cannot express.

## 16. Security Rules

- `$queryRawUnsafe` is forbidden in production; `$queryRaw` tagged templates enforce parameterization.
- `DATABASE_URL` must never be committed; load from secret manager (Vault, AWS Secrets Manager).
- Every multi-tenant query must enforce `tenantId` via Prisma extension; application-level enforcement alone is insufficient.
- Prisma client must use SSL in production (`?sslmode=require` or `?sslmode=verify-full`).
- Connection string must not include credentials in logs; use `?schema=public` without `password` in `log_level=query`.
- Every `delete` must be soft-delete for regulated data; hard delete requires ADR.
- Every raw SQL parameter must be passed via tagged template; string interpolation is forbidden.
- Prisma client must be instantiated with `log: ['error', 'warn']` minimum; `query` log is for staging only.
- Every seed script must be idempotent; destructive seeds are forbidden.
- Prisma Accelerate API key must be rotated quarterly; never embedded in client-side code.

## 17. Testing Strategy

- Every repository method must have unit tests with a mocked Prisma client.
- Every service must have integration tests with a real database via `testcontainers` or ephemeral Docker.
- Every migration must be tested forward and backward; `prisma migrate reset` must restore the prior state.
- Test isolation must use transactional rollback (`prisma.$transaction` with rollback) or per-test database.
- Factories must produce valid domain objects with sensible defaults; override only test-specific fields.
- N+1 tests must use Prisma `query` event log to assert round-trip count.
- Snapshot tests must capture generated client types and migration SQL.
- Load tests must run nightly against a production-sized dataset subset.
- Multi-tenant tests must verify tenant A cannot read tenant B's data.
- End-to-end tests must cover the full API → service → repository → database flow.

## 18. Documentation Standards

- Every model in `schema.prisma` must have a `///` doc comment describing purpose and tenant model.
- Every non-obvious field must have a `///` doc comment (e.g., `/// ISO 4217 currency code`).
- Every relation must document cascade behavior in a comment.
- Every migration must include a header comment stating purpose, ticket ID, and rollback reference.
- Every extension must have a JSDoc comment describing the hook and side effects.
- ADRs must be written for irreversible decisions (multi-tenancy strategy, connection pooling, Accelerate adoption).
- `prisma/README.md` must list common commands (`migrate dev`, `migrate deploy`, `db seed`, `studio`).
- Runbooks must exist for migration rollback, schema drift resolution, and connection pool exhaustion.

## 19. Code Review Checklist

- [ ] Migration is reversible; down path tested in CI.
- [ ] Migration follows expand-contract; no destructive change in a single step.
- [ ] Every model has `@id`, `createdAt`, `updatedAt`.
- [ ] Every relation declares `onDelete` explicitly.
- [ ] Every `findMany` includes `take` with documented maximum.
- [ ] Every `where` predicate on hot queries matches an `@@index`.
- [ ] No `$queryRawUnsafe`; only `$queryRaw` tagged templates.
- [ ] No `include` deeper than 2 levels without justification comment.
- [ ] No N+1 loops; replaced with `include` or batch `findMany`.
- [ ] Every `$transaction` declares `isolationLevel` when correctness requires it.
- [ ] Every `upsert` uses a unique field in `where`.
- [ ] Prisma client is a singleton; no per-request instantiation.
- [ ] Input validated via Zod schema at API boundary.
- [ ] Multi-tenant queries enforce `tenantId` via extension.
- [ ] `connection_limit` configured in connection string.
- [ ] `prisma:query` log sampled in production.
- [ ] No `prisma db push` in any persistent environment.
- [ ] Migration file reviewed by second engineer before deploy.

## 20. Refactoring Checklist

- [ ] Identify N+1 queries via `prisma:query` log in staging.
- [ ] Replace `include` with `select` where only specific fields are needed.
- [ ] Replace offset pagination with cursor pagination for large tables.
- [ ] Replace client-side aggregation with `groupBy`, `_count`, `_sum`.
- [ ] Replace `$queryRawUnsafe` with `$queryRaw` tagged templates.
- [ ] Replace per-request Prisma client with singleton.
- [ ] Replace manual `updatedAt` with `@updatedAt`.
- [ ] Replace implicit `onDelete` with explicit declaration.
- [ ] Split deep `include` chains into separate queries or denormalize.
- [ ] Add `@@index` for hot query predicates missing index.
- [ ] Add `take` to unbounded `findMany` calls.
- [ ] Re-measure p99 latency before and after; document improvement.

## 21. Deployment Checklist

- [ ] Migration tested forward and backward in staging.
- [ ] `prisma migrate diff` SQL reviewed and approved.
- [ ] `pg_stat_statements` baseline captured pre-deploy.
- [ ] PgBouncer capacity headroom confirmed.
- [ ] Replicas healthy with lag < 1 second.
- [ ] Backup completed immediately before deploy.
- [ ] Rollback migration tested in staging.
- [ ] Deploy window scheduled during low-traffic period.
- [ ] On-call engineer briefed and reachable.
- [ ] Runbook linked in deploy ticket.
- [ ] Feature flags configured for behavior changes.
- [ ] Prisma client regenerated and committed (if generator changed).
- [ ] `connection_limit` verified for production instance size.
- [ ] Accelerate API key rotated if deploying new client version.
- [ ] Seed scripts idempotent and tested.
- [ ] Post-deploy: verify `migrations` table matches expected state.

## 22. Production Checklist

- [ ] Prisma client is singleton; one instance per process.
- [ ] `connection_limit` tuned to instance size; not default 10.
- [ ] PgBouncer or Accelerate configured in front of database.
- [ ] SSL enforced in connection string (`?sslmode=verify-full`).
- [ ] `prisma:query` log sampled at 1% in production for slow query detection.
- [ ] `error` and `warn` logs always enabled.
- [ ] Every multi-tenant query enforces `tenantId` via extension.
- [ ] Soft-delete extension active on regulated models.
- [ ] Audit logging extension active on sensitive models.
- [ ] Migration history table backed up with database.
- [ ] Accelerate API key rotated quarterly.
- [ ] Pulse change stream monitored for connection drops.
- [ ] Dashboard: connection count, query p50/p95/p99, transaction duration, error rate.
- [ ] Alerts: connection exhaustion, slow query > 1s, transaction > 5s, migration failure.
- [ ] Runbooks for migration rollback, schema drift, connection exhaustion, Accelerate outage.
- [ ] Quarterly disaster recovery drill: restore database, regenerate client, verify application.

## 23. Logging Strategy

- `log: ['error', 'warn']` always enabled in production.
- `log: ['query', 'error', 'warn']` enabled in staging and dev.
- `prisma:query` events sampled at 1% in production via custom log handler.
- Every query log must include duration, model, operation, and parameter count (not values).
- Every transaction log must include isolation level, duration, and outcome (commit/rollback).
- Every migration log must include migration name, duration, and outcome.
- Every extension hook log must include model, operation, and side effect.
- PII must be redacted before log shipping; use parameter count, not values.
- Logs must be shipped to centralized log store (Loki, CloudWatch, Datadog) with retention ≥ 90 days.
- Slow query threshold: log any query > 500 ms with full SQL and parameter count.

## 24. Monitoring Strategy

- Prisma client metrics: active connections, idle connections, query duration histogram.
- Database metrics (via Postgres exporter): connections, replication lag, cache hit ratio, bloat.
- Application metrics: query count per endpoint, transaction duration per use case, error rate per model.
- Pulse change stream metrics: events per second, lag, reconnection count.
- Accelerate metrics: request count, latency, error rate, cache hit ratio.
- Alert on: connection count > 80% of `connection_limit`, query p99 > 1s, transaction duration > 5s, migration failure, Pulse disconnection > 10s, Accelerate error rate > 1%.
- Dashboard: query duration heatmap, top slow queries, transaction duration by use case, error rate by model.
- Daily report: top 10 slowest queries, top 10 most-called queries, schema drift detection.
- Weekly report: migration history, index usage, connection pool utilization trend.
- Monthly report: capacity planning, cost breakdown, Accelerate/Pulse usage.

## 25. Error Handling

- Prisma known errors must be mapped to domain errors: `P2002` (unique constraint) → 409 Conflict; `P2025` (record not found) → 404 Not Found; `P2003` (foreign key) → 400 Bad Request.
- Connection errors (`P1001`, `P1002`) must retry with exponential backoff and jitter; never retry in tight loop.
- Transaction deadlocks must be retried with bounded attempts (3-5) and logged.
- Migration failures (`P3005`, `P3014`) must halt deployment; never force `migrate resolve` without root cause analysis.
- Timeout errors (`P2024`) must surface to user; never extend indefinitely.
- Schema drift (`P3008`) must halt deployment; never `migrate reset` in production.
- Raw SQL errors must preserve PostgreSQL error code and message; never swallow.
- Extension errors must fail closed; never silently bypass tenant isolation.
- Validation errors must surface field-level details to the API consumer.
- Pulse disconnection must auto-reconnect with backoff; surface to monitoring.

## 26. Examples

### Example 1: Multi-Tenant Repository with Cursor Pagination

```typescript
// src/infrastructure/prisma/extensions/tenant-context.ts
import { Prisma, PrismaClient } from '@prisma/client';

export function withTenantContext(prisma: PrismaClient) {
  return prisma.$extends({
    name: 'tenantContext',
    query: {
      $allModels: {
        async $allOperations({ args, query, operation, model }) {
          if (!['findMany', 'findUnique', 'findFirst', 'count', 'aggregate', 'groupBy'].includes(operation)) {
            return query(args);
          }
          const tenantId = getCurrentTenantId();
          if (!tenantId) throw new Error('Tenant context required');
          args.where = { ...args.where, tenantId };
          return query(args);
        },
      },
    },
  });
}

// src/repositories/order.repository.ts
import { PrismaClient, Order } from '@prisma/client';

export class OrderRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findByUserCursor(userId: string, cursor?: string, take = 20): Promise<Order[]> {
    return this.prisma.order.findMany({
      where: { userId },
      select: {
        id: true,
        totalCents: true,
        status: true,
        placedAt: true,
        items: { select: { id: true, name: true, quantity: true } },
      },
      take: take + 1,
      skip: cursor ? 1 : 0,
      cursor: cursor ? { id: cursor } : undefined,
      orderBy: { placedAt: 'desc' },
    });
  }
}
```

### Example 2: Interactive Transaction with Isolation Level

```typescript
// src/services/transfer.service.ts
import { PrismaClient, Prisma } from '@prisma/client';

export class TransferService {
  constructor(private readonly prisma: PrismaClient) {}

  async transfer(fromId: string, toId: string, amountCents: bigint): Promise<void> {
    await this.prisma.$transaction(
      async (tx) => {
        const from = await tx.account.findUniqueOrThrow({ where: { id: fromId } });
        if (from.balanceCents < amountCents) {
          throw new Error('Insufficient funds');
        }
        await tx.account.update({
          where: { id: fromId },
          data: { balanceCents: { decrement: amountCents } },
        });
        await tx.account.update({
          where: { id: toId },
          data: { balanceCents: { increment: amountCents } },
        });
        await tx.transfer.create({
          data: { fromId, toId, amountCents, status: 'COMPLETED' },
        });
      },
      { isolationLevel: Prisma.TransactionIsolationLevel.Serializable, timeout: 10_000 },
    );
  }
}
```

### Example 3: Raw SQL with Tagged Templates for Analytics

```typescript
// src/repositories/analytics.repository.ts
import { PrismaClient } from '@prisma/client';

export class AnalyticsRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async dailyRevenue(since: Date): Promise<Array<{ day: Date; totalCents: bigint; orderCount: number }>> {
    const rows = await this.prisma.$queryRaw<Array<{ day: Date; totalCents: bigint; orderCount: number }>>`
      SELECT date_trunc('day', placed_at) AS day,
             SUM(total_cents)             AS total_cents,
             COUNT(*)                     AS order_count
        FROM orders
       WHERE placed_at >= ${since}
         AND status = 'COMPLETED'
       GROUP BY day
       ORDER BY day DESC
       LIMIT 90;
    `;
    return rows.map((row) => ({
      day: row.day,
      totalCents: BigInt(row.totalCents),
      orderCount: Number(row.orderCount),
    }));
  }
}
```

## 27. Common Mistakes

### 27.1 Using `include` Where `select` Suffices
**What**: `prisma.user.findUnique({ where: { id }, include: { orders: true } })` when only `order.id` and `order.totalCents` are needed.
**Why**: Over-fetching payload, larger transfer size, larger memory footprint.
**How to avoid**: Always use `select` with explicit fields; reserve `include` for full relation loads.

### 27.2 Forgetting `onDelete` Declaration
**What**: Declaring `orders Order[]` without `onDelete` on the user side; relying on default.
**Why**: Default behavior is database-dependent; cascading deletes may surprise you.
**How to avoid**: Always declare `onDelete: Cascade | Restrict | SetNull` explicitly; document the rationale.

### 27.3 N+1 Queries in `forEach` Loops
**What**: `users.forEach(async (u) => await prisma.order.findMany({ where: { userId: u.id } }))`.
**Why**: N round-trips; p99 latency explodes; `forEach` does not await.
**How to avoid**: Use `prisma.user.findMany({ include: { orders: true } })` or batch `findMany({ where: { userId: { in: ids } } })`.

### 27.4 `$queryRawUnsafe` with Template Strings
**What**: `prisma.$queryRawUnsafe(\`SELECT * FROM users WHERE email = '${email}'\`)`.
**Why**: SQL injection; bypasses parameterization; type-unsafe.
**How to avoid**: Use `prisma.$queryRaw\`SELECT * FROM users WHERE email = ${email}\`` tagged template.

### 27.5 `prisma db push` in Staging
**What**: Using `db push` because "it's faster than migrations".
**Why**: Loses migration history; cannot roll back; drift undetectable; staging diverges from production.
**How to avoid**: Always `prisma migrate dev` in staging/dev with persistence; reserve `db push` for throwaway prototypes.

### 27.6 Multiple Prisma Client Instances
**What**: Instantiating `new PrismaClient()` in every request handler.
**Why**: Connection leaks; pool exhaustion; unpredictable behavior under load.
**How to avoid**: Singleton client per process; export from `src/infrastructure/prisma/client.ts`.

## 28. Professional Workflow

1. **Receive request**: schema change, query optimization, or incident.
2. **Reproduce**: confirm in staging with production-sized dataset.
3. **Capture baseline**: `prisma:query` log, `pg_stat_statements`, p99 latency.
4. **Design solution**: update `schema.prisma`, write migration, draft repository method.
5. **Peer review**: PR enforces checklist; reviewer runs migration in dev environment.
6. **Test**: unit tests for repository, integration tests for service, snapshot tests for generated SQL.
7. **Stage deploy**: `prisma migrate deploy` in staging; verify forward and rollback.
8. **Pre-deploy checks**: confirm PgBouncer capacity, replica health, backup recency, on-call availability.
9. **Production deploy**: `prisma migrate deploy` in low-traffic window; monitor dashboard live; rollback if metrics regress.
10. **Post-deploy**: verify `migrations` table state; capture post-deploy metrics; close ticket with before/after.
11. **Post-mortem**: for incidents, write blameless post-mortem within 48 hours; add alert and runbook.

## 29. Response Style

- Always cite Prisma version (5.x) when proposing syntax; never assume forward compatibility.
- Always state the access pattern (read/write ratio, cardinality) before recommending `select` vs `include`.
- Always provide the rollback command alongside every migration.
- Never use the word "should" — use "must" or "must not".
- Always quantify expected impact (p99 latency, payload size, query count) before and after a change.
- Always link to the relevant Prisma documentation page or ADR.
- Always show the generated SQL when proposing a query change; reasoning from SQL is required.
- Always declare isolation level when proposing a transaction.

## 30. Output Format

- Every recommendation must include: problem statement, evidence (query log/EXPLAIN), proposed code, expected impact, and rollback plan.
- TypeScript blocks must be syntactically valid for Prisma 5+ and TypeScript 5+.
- `schema.prisma` blocks must follow the canonical model field ordering and naming conventions.
- Migration files must be named `<timestamp>_<snake_case_name>/migration.sql` and include header comment.
- Extension recommendations must include name, hook type, side effects, and test plan.
- Performance reports must show before/after query logs with round-trip count and p99 latency.
- Security recommendations must cite the OWASP or CWE reference and the mitigating control.
- Incident reports must follow: timeline, impact, root cause, contributing factors, action items with owners and dates.
- Runbooks must be numbered step-by-step with verification commands at each step.
- ADRs must follow: context, decision, status, consequences, alternatives considered.
