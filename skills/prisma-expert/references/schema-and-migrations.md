# Schema and Migrations (Prisma ORM 7.10)

Setup and schema reference for Prisma 7 with PostgreSQL. The schema and config below were generated and validated with Prisma 7.10.1.

## Install

```bash
npm install @prisma/client @prisma/adapter-pg pg dotenv
npm install -D prisma typescript tsx @types/node @types/pg
```

Requirements: Node.js 20.19+ and TypeScript 5.4+ (Node 22 and TypeScript 5.9 recommended), an ESM project (`"type": "module"` in `package.json`, `"module": "ESNext"` and a modern `moduleResolution` such as `bundler` or `nodenext` in `tsconfig.json`). Keep `prisma`, `@prisma/client` and `@prisma/adapter-pg` on the same version.

## prisma.config.ts

The CLI reads its datasource and paths from this file; it does not load `.env` by itself, so import `dotenv/config` (or pass variables through the shell or `--env-file`).

```ts
import 'dotenv/config'
import { defineConfig, env } from 'prisma/config'

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: {
    path: 'prisma/migrations',
    seed: 'tsx prisma/seed.ts',
  },
  typedSql: { path: 'prisma/sql' },       // only if you use typed SQL
  datasource: {
    url: env('DATABASE_URL'),             // direct (non-pooled) connection for CLI commands
    // shadowDatabaseUrl: env('SHADOW_DATABASE_URL'),
  },
})
```

- `datasource.url` is no longer allowed inside `schema.prisma`; `directUrl` is removed. The CLI uses the config URL, the application runtime uses the URL you pass to the adapter, so the two can point at different endpoints (direct and pooled).
- `prisma7.config.*` files are looked up before `prisma.config.*` by 7.10 (used when running Prisma 7 beside a newer Prisma); ordinary projects use `prisma.config.ts`.

## schema.prisma

```prisma
generator client {
  provider        = "prisma-client"
  output          = "../src/generated/prisma"
  previewFeatures = ["typedSql"]          // remove if typed SQL is not used
}

datasource db {
  provider = "postgresql"                 // the URL lives in prisma.config.ts
}

enum InvoiceStatus {
  DRAFT     @map("draft")
  PAID      @map("paid")
  CANCELLED @map("cancelled")

  @@map("invoice_status")
}

model Customer {
  id       String    @id @default(dbgenerated("uuidv7()")) @db.Uuid     // PostgreSQL 18; time-ordered
  tenantId String    @map("tenant_id") @db.Uuid
  name     String
  invoices Invoice[]

  @@unique([tenantId, id])                // target for composite foreign keys
  @@map("customers")
}

model Invoice {
  id         String        @id @default(dbgenerated("uuidv7()")) @db.Uuid
  tenantId   String        @map("tenant_id") @db.Uuid
  customerId String        @map("customer_id") @db.Uuid
  number     String
  totalCents BigInt        @map("total_cents")
  status     InvoiceStatus @default(DRAFT)
  createdAt  DateTime      @default(now()) @map("created_at") @db.Timestamptz(6)
  customer   Customer      @relation(fields: [tenantId, customerId], references: [tenantId, id], onDelete: Restrict)

  @@unique([tenantId, number])
  @@index([tenantId, createdAt(sort: Desc)])
  @@map("invoices")
}
```

Notes:

- `output` is mandatory with the `prisma-client` generator. Choose a folder inside `src` and decide whether to commit it or generate in CI and in `postinstall`/build scripts (`prisma generate` is explicit now).
- The composite relation `[tenantId, customerId] -> [tenantId, id]` guarantees an invoice can only reference a customer of the same tenant, in the database.
- `dbgenerated("uuidv7()")` needs PostgreSQL 18. Use `@default(uuid(7))` to let Prisma generate the value client-side on older servers, or `autoincrement()` for integer keys.
- A default that calls a custom SQL function (for example `dbgenerated("app.current_tenant()")`, to let the database fill `tenant_id` from the transaction setting) requires the function to exist before the table's migration runs; create it in an earlier, hand-written migration.
- Prisma cannot express partial indexes, CHECK constraints, RLS or `CONCURRENTLY`; put them in hand-written SQL migrations and keep `@@index` for indexes Prisma can express so schema and database stay aligned.

## Client

```ts
import { PrismaPg } from '@prisma/adapter-pg'
import { PrismaClient } from '../generated/prisma/client'   // from the generator output

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL!, max: 10 })
export const prisma = new PrismaClient({ adapter })
```

Adjust the import suffix (`.js`) if your `moduleResolution` requires explicit extensions.

## Migration workflow

| Command | Use |
|---|---|
| `prisma migrate dev --name add_invoice_status` | local: create, apply and record a migration |
| `prisma migrate dev --create-only` | create the migration file without applying it, so you can edit the SQL |
| `prisma migrate deploy` | CI and production: apply pending migrations, never creates or resets |
| `prisma migrate status` | show applied and pending migrations and drift |
| `prisma migrate resolve --applied <name>` / `--rolled-back <name>` | repair history after a failed or manually applied migration |
| `prisma migrate diff --from-config-datasource --to-schema prisma/schema.prisma --script` | preview SQL between two sources (flags renamed in 7; `--from-migrations`, `--from-empty` also exist) |
| `prisma db push` | prototypes only: syncs the database without recording a migration |
| `prisma generate` | regenerate the client (run explicitly after schema changes and in CI) |
| `prisma validate` / `prisma format` | check and format the schema |

`migrate dev` may reset or prompt on drift: use it only against local databases. In CI and production use `migrate deploy` from a single runner step before the application rollout.

## Hand-edited migrations

Use `--create-only`, edit `migration.sql`, then apply with `migrate dev` (local) or `migrate deploy`.

```sql
-- prisma/migrations/20261101090000_invoices_status_idx/migration.sql
-- One statement per file keeps failures easy to reason about.
CREATE INDEX CONCURRENTLY IF NOT EXISTS "invoices_tenant_id_status_idx" ON "invoices" ("tenant_id", "status");
```

- In a test on 7.10.1, `migrate deploy` applied a migration containing `CREATE INDEX CONCURRENTLY`; verify the same on your tooling and PostgreSQL version in staging, and keep one concurrent statement per migration.
- Declare the matching `@@index([tenantId, status])` in `schema.prisma` so the next `migrate dev` does not try to create or drop it (Prisma's default index name is `<table>_<columns>_idx`; the example above uses that form).
- A failed `CREATE INDEX CONCURRENTLY` leaves an `INVALID` index; drop it (`DROP INDEX CONCURRENTLY`), fix and retry.
- For large tables apply the online rules from postgresql-expert: `lock_timeout`, `NOT VALID` then `VALIDATE CONSTRAINT`, batched backfills (never `UPDATE ... LIMIT`; select keys in a subquery with `FOR UPDATE SKIP LOCKED`), nullable column then backfill then constraint.

## Expand and contract with Prisma

1. Migration 1 (expand): add the new nullable column or table. Deploy application code that writes both old and new.
2. Backfill in batches from a script or SQL migration (commit per batch).
3. Migration 2: add constraints (`NOT VALID`, then validate in a following migration), indexes concurrently.
4. Deploy code that reads the new structure.
5. Migration 3 (contract): drop the old column, in a later release.

## Seeding

```ts
// prisma/seed.ts (development only; run with `prisma db seed` using migrations.seed in prisma.config.ts)
import { prisma } from '../src/db/client'
await prisma.customer.create({ data: { tenantId: '11111111-1111-1111-1111-111111111111', name: 'Acme' } })
await prisma.$disconnect()
```

Seeds are idempotent (`upsert` or unique keys), never create default admin accounts or known credentials, and are never part of the production release path. `migrate` no longer runs seeds automatically in Prisma 7.

## Upgrading from Prisma 6 to 7

1. Upgrade Node.js to 20.19+ and TypeScript to 5.4+; make the package ESM.
2. Install `prisma@7`, `@prisma/client@7` and `@prisma/adapter-pg`; install `dotenv` if you relied on `.env` loading.
3. Change `provider = "prisma-client-js"` to `provider = "prisma-client"` and add `output`; update imports to the generated path.
4. Remove `url` (and `directUrl`) from the `datasource` block; add `prisma.config.ts` with `datasource.url`, `schema`, `migrations.seed`; remove the `prisma` key from `package.json`.
5. Construct the client with an adapter: `new PrismaClient({ adapter })`; remove `datasources`/`datasourceUrl` options.
6. Replace removed engine environment variables and flags (for example `prisma generate --no-engine`, `--data-proxy`) and the `metrics` preview feature; adapter names such as `PrismaBetterSQLite3` were renamed (`PrismaBetterSqlite3`) for SQLite users.
7. Run `prisma generate` and `prisma migrate deploy` explicitly in scripts and CI.
8. MongoDB is not supported in Prisma 7; keep those projects on Prisma 6.
9. Prisma 8 is at release-candidate stage and npm's `latest` tag points to an RC, so pin the exact 7.x version; do not upgrade to it without reading its upgrade guide.
