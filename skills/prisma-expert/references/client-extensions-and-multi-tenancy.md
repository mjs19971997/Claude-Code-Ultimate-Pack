# Client Extensions and Multi-Tenancy (Prisma ORM 7.10)

`$extends` and tenant isolation that covers reads and writes, with PostgreSQL RLS as the enforcing layer. The tenant extension and `withTenant` helper are in SKILL.md section 14 (type-checked against the 7.10.1 client and exercised against PostgreSQL with RLS); this file explains the design and what it does not cover.

## $extends components

```ts
import { Prisma } from '../generated/prisma/client'

export const audit = Prisma.defineExtension({
  name: 'extras',
  result: {                                   // computed fields on query results
    customer: {
      label: { needs: { name: true, id: true }, compute: (c) => `${c.name} (${c.id.slice(0, 8)})` },
    },
  },
  model: {                                    // new methods on a model
    invoice: {
      async markPaid(id: string) {
        const ctx = Prisma.getExtensionContext(this)
        return ctx.update({ where: { id }, data: { status: 'PAID' } })
      },
    },
  },
  client: {                                   // new methods on the client
    async $healthcheck() {
      const ctx = Prisma.getExtensionContext(this)
      await ctx.$queryRaw`SELECT 1`
    },
  },
})
// const db = prisma.$extends(audit)
```

- `query` intercepts model operations (`$allModels.$allOperations`, `$allModels.findMany`, `invoice.create`, ...). `result` adds computed fields. `model` adds methods. `client` adds client-level methods.
- Extensions compose: `prisma.$extends(a).$extends(b)`. Each call returns a new client sharing the underlying pool.
- `$extends` is not available on an interactive-transaction client: extend first, then open the transaction (as `withTenant` does).
- Query extensions see only the top-level operation. Nested writes inside `data` (for example `create: { invoices: { create: [...] } }`) and raw SQL (`$queryRaw`, `$executeRaw`, typed SQL) are not intercepted.

## Isolation layers

1. **Application layer (extension)**: scopes `where`, injects `tenantId`, blocks tenant changes. Catches mistakes early with readable errors, and gives `P2025` instead of silent cross-tenant matches.
2. **Database layer (RLS)**: policies with `USING` and `WITH CHECK` read the tenant from a transaction-local setting that the server sets. This protects nested writes, raw SQL, typed SQL, other services and ad hoc scripts.
3. **Schema layer**: composite foreign keys `(tenant_id, parent_id)` and unique keys including `tenant_id` so references cannot span tenants.

Use all three for tenant-owned data. The extension alone is not sufficient: it does not see nested writes or raw queries.

### What the extension does per operation

| Operation | Behavior |
|---|---|
| `findUnique`, `findUniqueOrThrow`, `findFirst`, `findFirstOrThrow`, `findMany`, `count`, `aggregate`, `groupBy` | `where` gets `tenantId` (unique selectors accept extra filter fields, so `findUnique({ where: { id } })` becomes `{ id, tenantId }`) |
| `create`, `createMany`, `createManyAndReturn` | `tenantId` injected into each row; an input `tenantId` that differs from the current tenant throws |
| `update`, `updateMany`, `updateManyAndReturn` | `where` scoped; a `tenantId` in `data` that differs throws, so a row cannot be moved to another tenant |
| `delete`, `deleteMany` | `where` scoped; another tenant's id yields `P2025` (`delete`) or count 0 (`deleteMany`) |
| `upsert` | `where` scoped, `create` gets `tenantId`; `update` cannot change it. Another tenant's id does not match, so the create branch runs for the current tenant |
| anything else | throws (fail closed), so a newly added operation is never silently unscoped |

Adjust `TENANT_MODELS` to the models that carry `tenantId`. Models that are global (plans, countries) pass through unchanged.

### Type ergonomics

`tenantId` is a required scalar in create inputs, so callers must pass it even though the extension injects it. To make it optional in the types, give the column a database default from the transaction setting, then the extension (and RLS `WITH CHECK`) still enforce the value:

```sql
-- hand-written migration, created before the tables that use it
CREATE SCHEMA IF NOT EXISTS app;
CREATE FUNCTION app.current_tenant() RETURNS uuid
LANGUAGE sql STABLE
AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$;
```

```prisma
tenantId String @default(dbgenerated("app.current_tenant()")) @map("tenant_id") @db.Uuid
```

With that default, `db.customer.create({ data: { name: 'Acme' } })` type-checks and receives the tenant from the transaction setting.

## RLS policies for the Prisma tables

The application connects as a role that is not the table owner and not `BYPASSRLS`; migrations run as the owner. Policy design details are in postgresql-expert (`references/rls-and-multi-tenancy.md`). For the tables mapped above:

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices
  FOR ALL
  USING      (tenant_id = (SELECT app.current_tenant()))
  WITH CHECK (tenant_id = (SELECT app.current_tenant()));
-- repeat for customers and every other tenant-owned table
GRANT SELECT, INSERT, UPDATE, DELETE ON invoices, customers TO app_user;
```

- The tenant id passed to `withTenant` comes from the verified session or token (see authorization-expert), never from request input.
- `set_config('app.tenant_id', $1, true)` inside the same transaction as the queries; behind a transaction-mode pooler, nothing leaks to the next client.
- Queries issued outside `withTenant` have no tenant set and return no rows, which is the safe failure.
- Interactive transactions run on one connection, so the setting applies to every statement in the callback. Sequential `$transaction([...])` arrays are also one transaction, but `withTenant` is simpler and keeps the setting first.
- `$transaction` options (`isolationLevel`, `timeout`, `maxWait`) are passed through `withTenant`'s third argument.

## Tests

```ts
// integration test (Vitest or similar), real PostgreSQL with migrations and RLS applied, app connects as app_user
const A = '11111111-1111-1111-1111-111111111111'
const B = '22222222-2222-2222-2222-222222222222'

it('isolates tenants on writes', async () => {
  const cust = await withTenant(A, (db) => db.customer.create({ data: { name: 'a' } }))
  const inv = await withTenant(A, (db) =>
    db.invoice.create({ data: { customerId: cust.id, number: '1', totalCents: 100n } }))

  await expect(withTenant(B, (db) => db.invoice.update({ where: { id: inv.id }, data: { status: 'PAID' } })))
    .rejects.toMatchObject({ code: 'P2025' })
  await expect(withTenant(B, (db) => db.invoice.delete({ where: { id: inv.id } })))
    .rejects.toMatchObject({ code: 'P2025' })
  expect((await withTenant(B, (db) => db.invoice.updateMany({ data: { status: 'PAID' } }))).count).toBe(0)
  expect(await withTenant(B, (db) => db.invoice.findMany())).toHaveLength(0)
})

it('RLS blocks what the extension cannot see', async () => {
  // raw SQL bypasses client extensions; RLS must still hide other tenants
  const rows = await withTenant(B, (db) => db.$queryRaw`SELECT id FROM invoices`)
  expect(rows).toHaveLength(0)
  // no tenant context at all
  expect(await prisma.$queryRaw`SELECT id FROM invoices`).toHaveLength(0)
})
```

(In the first test, `tenantId` is optional in the create input only when the column has the database default shown above; otherwise pass `tenantId: A`.)

Also test: nested create with a foreign tenant id fails (composite FK and `WITH CHECK`), and reusing one pooled connection for tenant A and then B does not leak.

## Soft delete and other model-level extensions

A soft-delete `query` extension must handle the same full operation set: `findMany` and friends add `deletedAt: null`, `delete` and `deleteMany` become `update` and `updateMany` that set `deletedAt`. Prefer partial unique indexes (`UNIQUE (email) WHERE deleted_at IS NULL`) in SQL, and consider an RLS policy or a view for hiding deleted rows consistently across raw and typed SQL.

## Other isolation models

- **Schema per tenant**: one database, one PostgreSQL schema per tenant; set the schema per transaction (`SET LOCAL search_path`) or use the adapter's schema option (check the adapter docs for your version). Migrations must run for every schema.
- **Database per tenant**: one adapter and one `PrismaClient` per tenant database, cached in an LRU map with a bounded size and closed on eviction (`$disconnect`); keep total connections within the server limit.
- Mixed: shared tables with RLS for small tenants; dedicated databases for large or regulated ones.
