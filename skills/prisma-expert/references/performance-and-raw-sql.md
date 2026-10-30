# Performance and Raw SQL (Prisma ORM 7.10)

Query shaping, transactions, pooling, typed SQL and diagnosing slow queries. Index design and plan reading are covered in postgresql-expert (`references/indexing-and-query-plans.md`).

## Shape queries

```ts
// Only the needed columns, bounded, stable order
const page = await prisma.invoice.findMany({
  where: { tenantId, status: 'PAID' },
  select: { id: true, number: true, totalCents: true, createdAt: true },
  orderBy: [{ createdAt: 'desc' }, { id: 'desc' }],
  take: 50,
})

// Hide sensitive columns from a query (convenience, not access control)
await prisma.user.findMany({ omit: { passwordHash: true } })
```

- `select` and `omit` cannot be combined in one query. `omit` can also be set globally in the `PrismaClient` constructor (`omit: { user: { passwordHash: true } }`); note that a global `omit` changes the client type, so verify helper types that accept a generic transaction client (the tenant `TenantTx` type is derived from the actual client for this reason).
- Avoid `include` on to-many relations of large parents; select the relation with its own `take` and `select`, or query the child table with `where: { parentId: { in: ids } }`.
- Relation loading strategy (`relationLoadStrategy`) can load relations with a database join or separate queries; check the current docs for its status and default in your version, then measure both for the query at hand.

## N+1

```ts
// Bad: one query per user
for (const u of users) u.orders = await prisma.order.findMany({ where: { userId: u.id } })

// Good: one query for all, grouped in memory
const orders = await prisma.order.findMany({ where: { userId: { in: users.map((u) => u.id) } } })

// Good: aggregates in the database
const totals = await prisma.order.groupBy({ by: ['userId'], _sum: { totalCents: true }, _count: true })
```

## Pagination

Cursor pagination needs a unique, stable sort and a matching index:

```ts
const rows = await prisma.invoice.findMany({
  where: { tenantId },
  orderBy: [{ createdAt: 'desc' }, { id: 'desc' }],
  take: 51,                                       // one extra row tells you whether there is a next page
  ...(cursorId ? { cursor: { id: cursorId }, skip: 1 } : {}),
})
const hasNext = rows.length > 50
const items = rows.slice(0, 50)
const nextCursor = hasNext ? items[items.length - 1].id : null
```

`skip`/`take` offsets get slower with depth because the database still reads and discards skipped rows.

## Writes

- `createMany` and `createManyAndReturn` batch inserts; `updateMany` and `deleteMany` run as one statement.
- Atomic updates avoid read-modify-write races: `data: { balanceCents: { decrement: 100 } }`.
- For guarded updates use a condition in `where` and check the count: `updateMany({ where: { id, status: 'DRAFT' }, data: { status: 'PAID' } })`; `count === 0` means a conflict.
- Very large imports: use `COPY` through a PostgreSQL client or chunked `createMany` (chunks of a few thousand rows); parameter limits apply to a single statement.

## Transactions

```ts
// Sequential: independent writes executed atomically in one round trip
await prisma.$transaction([
  prisma.invoice.update({ where: { id }, data: { status: 'PAID' } }),
  prisma.auditLog.create({ data: { invoiceId: id, action: 'PAID' } }),
])

// Interactive: later steps depend on earlier results
await prisma.$transaction(
  async (tx) => {
    const acc = await tx.account.findUniqueOrThrow({ where: { id: accountId } })
    if (acc.balanceCents < amount) throw new Error('insufficient funds')
    await tx.account.update({ where: { id: accountId }, data: { balanceCents: { decrement: amount } } })
  },
  { maxWait: 2_000, timeout: 5_000, isolationLevel: Prisma.TransactionIsolationLevel.Serializable },
)
```

- Keep interactive transactions short: they hold a pooled connection and locks for their duration. No HTTP calls or user waits inside.
- Under `Serializable` (or on deadlocks) PostgreSQL aborts with serialization failures; Prisma surfaces them as `P2034`. Retry the whole transaction with a small backoff (see `retryable` in SKILL.md section 14).
- Pessimistic locks need raw SQL: `` tx.$queryRaw`SELECT id FROM jobs WHERE state = 'queued' ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED` ``.

## Pooling and connections

- One client (and thus one pool) per process. The pool belongs to the `pg` driver behind `@prisma/adapter-pg`: configure it with the pool options passed to `new PrismaPg({ connectionString, max, ... })`; the old engine's URL parameters (`connection_limit`, `pool_timeout`) do not apply, so check the adapter docs for the options in your version.
- Total connections = instances x `max`. Keep it below PostgreSQL's `max_connections` minus reserved capacity, or put PgBouncer (transaction mode) in front.
- Run CLI commands against the direct URL (`prisma.config.ts`) and the application against the pooled URL (adapter).
- In serverless, create the client outside the handler, keep `max` small, and prefer an external pooler.

## Raw SQL

```ts
import { Prisma } from '../generated/prisma/client'

// Tagged template: values are bound as parameters
const rows = await prisma.$queryRaw<{ id: string; n: bigint }[]>`
  SELECT customer_id AS id, count(*) AS n FROM invoices WHERE tenant_id = ${tenantId}::uuid GROUP BY customer_id`

// Dynamic fragments: compose with Prisma.sql / Prisma.join, never string concatenation
const ids = [id1, id2]
await prisma.$queryRaw(Prisma.sql`SELECT * FROM invoices WHERE id IN (${Prisma.join(ids)})`)

// Allow-list identifiers, then use Prisma.raw only for the allow-listed value
const SORT = { created: 'created_at', total: 'total_cents' } as const
const col = SORT[input.sort as keyof typeof SORT] ?? 'created_at'
await prisma.$queryRaw(Prisma.sql`SELECT id FROM invoices ORDER BY ${Prisma.raw(col)} LIMIT 50`)
```

- Postgres returns `bigint` for `count(*)` and `sum` of integers; Prisma returns `BigInt` values, so cast in SQL (`::int`) or convert before JSON serialization.
- `$queryRawUnsafe` and `$executeRawUnsafe` take a plain string; use them only with static SQL text and `$1, $2` placeholders plus separate parameters.
- Raw queries are not intercepted by client extensions (including tenant scoping); run them inside `withTenant` so RLS applies, and keep an explicit tenant predicate.

## Typed SQL

Typed SQL generates typed functions from `.sql` files. In 7.10.1 it still required the `typedSql` preview feature in the generator and a reachable database at generate time (check the current docs for changes).

```prisma
generator client {
  provider        = "prisma-client"
  output          = "../src/generated/prisma"
  previewFeatures = ["typedSql"]
}
```

```sql
-- prisma/sql/invoiceTotals.sql
-- @param {String} $1:tenantId
-- @param {Int} $2:limit
SELECT status::text AS status, count(*)::int AS n, sum(total_cents)::bigint AS cents
FROM invoices
WHERE tenant_id = $1::uuid
GROUP BY status
ORDER BY cents DESC
LIMIT $2
```

```bash
prisma generate --sql      # needs prisma.config.ts typedSql.path and a reachable database
```

```ts
import { prisma } from './db/client'
import { invoiceTotals } from './generated/prisma/sql'

export const totals = (tenantId: string) => prisma.$queryRawTyped(invoiceTotals(tenantId, 10))
```

Typed SQL bypasses client extensions like any raw query; rely on RLS and run it in the tenant transaction.

## Diagnosing slow queries

1. Log queries in a non-production environment (`new PrismaClient({ adapter, log: [{ emit: 'event', level: 'query' }] })` and `prisma.$on('query', ...)`), or use `pg_stat_statements` in PostgreSQL to find the heaviest statements.
2. Take the SQL, bind realistic parameters, and run `EXPLAIN (ANALYZE, BUFFERS)`.
3. Typical causes: a missing composite index for `where` + `orderBy`, `include` multiplying rows, offset pagination on deep pages, sorting by a non-indexed column, a missing `take`, functions on indexed columns, an interactive transaction waiting on locks.
4. Fix in the schema (`@@index`, hand-written concurrent index migration) or the query shape, then re-measure.
5. Check pool wait time and connection counts when latency is high but statements are fast.
