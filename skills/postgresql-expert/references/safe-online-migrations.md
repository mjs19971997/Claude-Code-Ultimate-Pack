# Safe Online Migrations (PostgreSQL 18)

Schema changes that keep reads and writes flowing. The danger is rarely the DDL's own run time; it is the lock queue: an `ACCESS EXCLUSIVE` request that waits behind one long transaction blocks every query that arrives after it.

## Ground rules

1. Set `lock_timeout` (and usually `statement_timeout`) at the top of every migration, and retry on failure instead of waiting.
2. One logical change per migration; keep transactions short.
3. Never hold a lock while doing slow work (backfill, validation) when a weaker-lock path exists.
4. Make each step backward compatible with the application version currently deployed (expand, then contract in a later release).
5. Check for long-running transactions before DDL: `SELECT pid, now() - xact_start AS age, state, left(query, 80) FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start;`

```sql
SET lock_timeout = '3s';
SET statement_timeout = '60s';
ALTER TABLE orders ADD COLUMN note text;
-- on lock_timeout failure: wait a moment and retry the migration step (the tool or a wrapper loop retries)
```

`SET` here lasts for the session. Inside a transaction use `SET LOCAL`. Do not set a short `statement_timeout` for `CREATE INDEX CONCURRENTLY` or `VALIDATE CONSTRAINT`; use `SET statement_timeout = 0` for those steps.

## What is cheap and what is not

| Change | Behavior |
|---|---|
| `ADD COLUMN` nullable, no default | metadata only; brief `ACCESS EXCLUSIVE` |
| `ADD COLUMN ... DEFAULT <constant or stable expr>` (with or without NOT NULL) | no rewrite since PostgreSQL 11; the default is stored in the catalog |
| `ADD COLUMN ... DEFAULT <volatile expr>` (`random()`, `uuidv7()`, `clock_timestamp()`) | rewrites the table; avoid, add nullable then backfill |
| `ADD COLUMN ... GENERATED ALWAYS AS (...) STORED` | rewrites the table |
| `ADD COLUMN ... GENERATED ALWAYS AS (...) VIRTUAL` (18 default) | no rewrite, computed on read |
| `ALTER COLUMN TYPE` | usually rewrites (some binary-coercible changes do not, for example widening `varchar(n)` limit); plan an expand and contract copy |
| `CREATE INDEX` | blocks writes; use `CONCURRENTLY` |
| `ADD FOREIGN KEY` / `ADD CHECK` | scans the table under a strong lock unless added `NOT VALID` |
| `SET NOT NULL` | scans unless a valid CHECK proves it (or a valid NOT NULL constraint exists) |
| `DROP COLUMN` | metadata only, but needs `ACCESS EXCLUSIVE` briefly and breaks old code |
| `RENAME` column or table | instant, but breaks old code: use expand and contract |

## Indexes

```sql
-- Not inside BEGIN ... COMMIT (CONCURRENTLY cannot run in a transaction block)
SET lock_timeout = '3s';
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_customer_idx ON orders (customer_id);

-- A failed or cancelled concurrent build leaves an INVALID index: find, drop, retry
SELECT c.relname FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid WHERE NOT i.indisvalid;
DROP INDEX CONCURRENTLY IF EXISTS orders_customer_idx;

-- Replace an index without downtime
CREATE INDEX CONCURRENTLY orders_customer_idx2 ON orders (customer_id, created_at);
DROP INDEX CONCURRENTLY orders_customer_idx;
-- or: REINDEX INDEX CONCURRENTLY orders_customer_idx;

-- Unique constraint or primary key from a prebuilt unique index
CREATE UNIQUE INDEX CONCURRENTLY orders_ref_uq ON orders (external_ref);
ALTER TABLE orders ADD CONSTRAINT orders_external_ref_key UNIQUE USING INDEX orders_ref_uq;
```

Many migration tools wrap each file in a transaction; configure that file to run outside one (each tool has a per-migration switch; check its documentation).

## Constraints without long locks

```sql
-- Foreign key
ALTER TABLE orders
  ADD CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_customer_fk;   -- SHARE UPDATE EXCLUSIVE: reads and writes continue

-- CHECK
ALTER TABLE orders ADD CONSTRAINT orders_total_chk CHECK (total_cents >= 0) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_total_chk;
```

`NOT VALID` enforces the constraint for new and updated rows immediately; `VALIDATE CONSTRAINT` checks existing rows with a weaker lock. Fix violating rows before validating.

### NOT NULL on a populated column

Portable route (works on all supported versions): a validated CHECK lets `SET NOT NULL` skip the table scan.

```sql
ALTER TABLE orders ADD CONSTRAINT orders_status_nn CHECK (status IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_status_nn;
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;          -- no scan, the CHECK proves it
ALTER TABLE orders DROP CONSTRAINT orders_status_nn;
```

PostgreSQL 18 route: a not-null constraint can itself be added `NOT VALID` and validated later.

```sql
ALTER TABLE orders ADD CONSTRAINT orders_status_nn NOT NULL status NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_status_nn;
```

Check the `ALTER TABLE` page for the exact behavior of your minor version before relying on it in a runbook.

## Add a column and backfill in batches

1. Deploy the column nullable (no default, or a constant default when new rows should get one).
2. Deploy code that writes the new column for new rows.
3. Backfill existing rows in small committed batches.
4. Add the constraint `NOT VALID`, validate, then deploy code that relies on it.

`UPDATE ... LIMIT` does not exist. Use a keyed subquery with `FOR UPDATE SKIP LOCKED`:

```sql
-- Run repeatedly from a script or job until it updates 0 rows; one transaction per batch
UPDATE orders
   SET status = 'new'
 WHERE id IN (SELECT id FROM orders WHERE status IS NULL ORDER BY id LIMIT 5000 FOR UPDATE SKIP LOCKED);
```

Or a key-range sweep that needs no locking subquery (works with any monotonically increasing key):

```sql
-- $1 = last processed id (start at 0), batch size 5000; next iteration continues from the max id handled
WITH batch AS (
  SELECT id FROM orders WHERE id > $1 ORDER BY id LIMIT 5000
)
UPDATE orders o SET status = COALESCE(o.status, 'new')
  FROM batch b WHERE o.id = b.id
RETURNING o.id;   -- the application takes the max returned id as the next $1
```

Notes:

- Commit between batches (separate statements in autocommit mode, or a procedure that `COMMIT`s, shown in SKILL.md section 14). Sleep briefly between batches; watch replication lag and autovacuum.
- Update only rows that need it (`WHERE status IS NULL`), so reruns are cheap and idempotent, and avoid touching indexed columns to keep updates HOT.
- Each batch rewrites rows (dead tuples): run `VACUUM` or let autovacuum catch up, and `ANALYZE` afterwards.

## Changing a column type or renaming (expand and contract)

1. Add the new column; keep both in sync with a trigger or dual writes in the application.
2. Backfill in batches; create indexes `CONCURRENTLY`; validate constraints.
3. Switch reads to the new column; deploy.
4. Stop writing the old column; deploy.
5. Drop the old column in a later migration. A rename can be done with a view or by exposing both names for a release.

## Partitioning and large tables

- Attach a partition without a long lock: create the table, add a CHECK matching the partition bound (`NOT VALID`, then `VALIDATE`), then `ALTER TABLE parent ATTACH PARTITION ...`; the existing validated constraint lets the attach skip the scan.
- Retire data with `ALTER TABLE parent DETACH PARTITION child CONCURRENTLY;` then drop or archive the child. `DETACH ... CONCURRENTLY` cannot run in a transaction block.
- Converting a large table to a partitioned one: create the partitioned table, copy in batches (or attach the old table as a partition), switch over in a short transaction under `lock_timeout`.

## Locks cheat sheet

- `ACCESS EXCLUSIVE`: most `ALTER TABLE` forms, `DROP`, `TRUNCATE`; blocks everything including `SELECT`.
- `SHARE ROW EXCLUSIVE`: adding foreign keys; `SHARE`: plain `CREATE INDEX` (blocks writes).
- `SHARE UPDATE EXCLUSIVE`: `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`, vacuum; does not block normal reads and writes.
- See what is blocked: `SELECT pid, pg_blocking_pids(pid) AS blocked_by, wait_event_type, wait_event, left(query, 80) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;`

## Rollback and release order

- Migrations that only add are safe to leave applied when the code rolls back; contract steps (drops, NOT NULL, type changes) happen only after the previous code version is gone.
- Prefer forward fixes over down-migrations in production; keep down scripts for development databases.
- Run the full sequence against a production-sized copy and record duration and lock waits before the real run.
