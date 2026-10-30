# Indexing and Query Plans (PostgreSQL 18)

How to choose indexes and read plans. All statements assume PostgreSQL 18; notes mark what is new in 18.

## Index types

| Type | Use for | Notes |
|---|---|---|
| B-tree | equality, range, sort, `LIKE 'prefix%'` (with `text_pattern_ops` or C collation) | default; supports unique constraints and index-only scans |
| GIN | `jsonb` (`@>`, `?`), arrays, `tsvector`, `pg_trgm` | slower writes; `jsonb_path_ops` is smaller and supports `@>` only |
| GiST | ranges, geometry, exclusion constraints, nearest-neighbor | `EXCLUDE USING gist (room WITH =, during WITH &&)` |
| SP-GiST | non-balanced structures (prefixes, points) | niche |
| BRIN | very large, append-mostly tables correlated with physical order (time) | tiny; useless when values are randomly distributed |
| Hash | equality only | rarely better than B-tree |
| pgvector (extension) | embeddings: HNSW or IVFFlat | follow the extension docs for operator classes and parameters |

## Multicolumn B-tree indexes

- Column order: equality columns first, then the range or sort column. `(tenant_id, status, created_at)` serves `WHERE tenant_id = $1 AND status = $2 ORDER BY created_at`.
- Skip scan (18): the planner can use a multicolumn B-tree when the leading column has no condition, by probing each distinct leading value. It pays off when the leading column has few distinct values (for example a `region` or `is_active` flag). It does not rescue an index whose leading column has many distinct values; reorder or add an index in that case.
- A query filtering only on the second column of `(a, b)` used to need its own index; on 18 check the plan first (`EXPLAIN`) before adding one.

## Partial, covering and expression indexes

```sql
-- Partial: only the rows queries touch; the query must include the same predicate
CREATE INDEX CONCURRENTLY orders_open_idx ON orders (tenant_id, created_at)
  WHERE status IN ('new', 'paid');

-- Unique among live rows (soft delete)
CREATE UNIQUE INDEX CONCURRENTLY users_email_live_uq ON users (lower(email))
  WHERE deleted_at IS NULL;

-- Covering: enables index-only scans for this projection (INCLUDE columns are not searchable)
CREATE INDEX CONCURRENTLY orders_customer_cover_idx ON orders (customer_id) INCLUDE (status, total_cents);

-- Expression: the query must use the identical expression
CREATE INDEX CONCURRENTLY users_lower_email_idx ON users (lower(email));

-- JSONB containment
CREATE INDEX CONCURRENTLY events_payload_idx ON events USING gin (payload jsonb_path_ops);

-- Large append-only time series
CREATE INDEX CONCURRENTLY metrics_ts_brin ON metrics USING brin (recorded_at);
```

- Virtual generated columns (the 18 default) cannot be indexed; index the expression instead, or declare the column `STORED`.
- Index every foreign key column that is used for joins or for `ON DELETE`/`ON UPDATE` checks; the referenced side already has a unique index, the referencing side does not.
- Each index slows writes and consumes vacuum time. Find candidates for removal with `pg_stat_user_indexes` (`idx_scan = 0` over a full business cycle, excluding unique and constraint indexes).

## Reading EXPLAIN

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS) SELECT ...;   -- BUFFERS is included with ANALYZE by default in 18
EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON) SELECT ...; -- machine-readable, for tests and tooling
```

`EXPLAIN ANALYZE` executes the statement. Wrap writes in a transaction and roll back (`BEGIN; EXPLAIN ANALYZE UPDATE ...; ROLLBACK;`).

What to look at, in order:

1. **Estimated vs actual rows** at each node. A factor of 10 or more points at stale or insufficient statistics (see below), not at the wrong index.
2. **Scan type**: `Seq Scan` on a large table with a selective filter (look at `Rows Removed by Filter`); `Bitmap Heap Scan` with many `lossy` pages (work_mem too small); `Index Only Scan` with high `Heap Fetches` (visibility map stale, vacuum needed).
3. **Join method**: `Nested Loop` with a large outer side and no inner index; `Hash Join` with `Batches > 1` (spilling); `Merge Join` with an explicit sort.
4. **Sorts and aggregates**: `Sort Method: external merge Disk:` means spill to disk; raise `work_mem` for that role or add an index in the sort order.
5. **Buffers**: `shared read` versus `shared hit` shows cache behavior; `temp read/written` shows spills. `track_io_timing = on` adds I/O time.
6. **Planning vs execution time**: with prepared statements, `plan_cache_mode` and generic versus custom plans matter when a parameter has very skewed values.

## Statistics

```sql
ANALYZE orders;                                    -- after bulk loads and big backfills
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;  -- finer histogram/MCV list for skewed columns
CREATE STATISTICS orders_tenant_status (dependencies, ndistinct, mcv) ON tenant_id, status FROM orders;
ANALYZE orders;
```

Use extended statistics when filters on correlated columns are badly underestimated. After `pg_upgrade` to 18, optimizer statistics are retained; extended statistics and anything the upgrade notes call out still deserve an `ANALYZE` pass (check the `pg_upgrade` documentation for your path).

## Slow-query workflow

1. Identify: `pg_stat_statements` (`shared_preload_libraries = 'pg_stat_statements'`, then `CREATE EXTENSION pg_stat_statements`). Rank by `total_exec_time`, then look at `mean_exec_time`, `calls`, `rows`, `shared_blks_read`.
2. Reproduce with real parameter values; capture the plan with `EXPLAIN (ANALYZE, BUFFERS)`. For production-only slowness use `auto_explain` (`auto_explain.log_min_duration`) or `log_min_duration_statement`.
3. Fix in this order: query shape (remove functions on indexed columns, avoid `OR` across columns, use `EXISTS`), index, statistics, then configuration. Re-measure after each change.
4. If a query is fast alone but slow in production, check lock waits (`pg_locks`, `log_lock_waits`), connection pressure, and long transactions in `pg_stat_activity`.

Common rewrites:

- `WHERE date(created_at) = '2026-10-01'` becomes `WHERE created_at >= '2026-10-01' AND created_at < '2026-10-02'`.
- `WHERE col::text = $1` on a non-text column defeats the index; cast the parameter, not the column.
- `LIKE '%term%'` needs a `pg_trgm` GIN index; prefix search needs `text_pattern_ops` unless the column uses the C collation.
- `ORDER BY a, b` with mixed directions needs an index declared in the same directions (`(a ASC, b DESC)`).
- `COUNT(*)` of a large table is a scan; use an estimate (`reltuples`) for UI totals, or maintain a counter.

## Keyset pagination

```sql
SELECT id, created_at, title
  FROM posts
 WHERE tenant_id = $1
   AND (created_at, id) < ($2, $3)
 ORDER BY created_at DESC, id DESC
 LIMIT 50;
-- supported by: CREATE INDEX ON posts (tenant_id, created_at DESC, id DESC);
```

## Asynchronous I/O (18)

- `io_method` (server start only): `worker` (default, portable), `io_uring` (Linux, build with liburing), `sync` (disables async behavior). `io_workers` sizes the worker pool for `worker`.
- Reads benefit first: sequential scans, bitmap heap scans and vacuum. `effective_io_concurrency` and `maintenance_io_concurrency` values above zero now apply on systems without `fadvise()`.
- Inspect in-flight I/O with the `pg_aios` view. Benchmark on the real workload and storage before changing the default.
