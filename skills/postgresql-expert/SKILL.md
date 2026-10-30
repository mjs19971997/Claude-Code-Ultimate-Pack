---
name: postgresql-expert
description: >-
  Designs, tunes and operates PostgreSQL 18 databases: schema and constraint design, indexing and EXPLAIN analysis, zero-downtime migrations, Row-Level Security for multi-tenancy, transactions and locking, VACUUM, partitioning, replication and pooling (PgBouncer). Use when writing or reviewing SQL, migrations, indexes, RLS policies, slow-query investigations, pg_stat_statements output, postgresql.conf settings, or upgrades to 18 (async I/O, uuidv7, virtual generated columns, RETURNING OLD/NEW, skip scan). Not for Prisma schema or Client code (use prisma-expert), document stores (use mongodb-expert), or caching (use redis-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# PostgreSQL Expert

This skill covers day-to-day PostgreSQL engineering: modeling data with constraints that enforce invariants, choosing indexes from query plans, shipping schema changes without blocking traffic, isolating tenants with Row-Level Security, and operating the server (vacuum, pooling, replication, upgrades). Deep material lives in three reference files: indexing and query plans, safe online migrations, and RLS with multi-tenancy.

> Verified against PostgreSQL 18.6 (latest 18.x, released 2026-08-13; PostgreSQL 19 is in pre-release, check its status before upgrading) and PgBouncer 1.26.1 (2026-10).

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

- Covered: SQL and schema design, indexes, query plans, migrations, RLS, locking and isolation, VACUUM and bloat, partitioning, JSONB and full-text search, pooling, replication and upgrade notes, PostgreSQL 18 features.
- Not covered: Prisma schema, Client and migrations (prisma-expert); MongoDB, Redis, Elasticsearch modeling (mongodb-expert, redis-expert, elasticsearch-expert); cloud provisioning of managed instances (aws-expert, terraform-expert); application-level authorization models (authorization-expert).

## 2. Core Expertise

- **MVCC and vacuum**: tuple versions, HOT updates, autovacuum thresholds, transaction ID wraparound, bloat, `VACUUM (VERBOSE)` and `pg_stat_user_tables`.
- **Schema design**: normalize first, denormalize with evidence; identity columns or `uuidv7()` keys; `timestamptz`; `numeric` for money; CHECK, UNIQUE, FK and EXCLUDE constraints as the source of truth.
- **Indexes**: B-tree (with skip scan in 18), GIN, GiST, BRIN, partial, expression and covering (`INCLUDE`) indexes. See [references/indexing-and-query-plans.md](references/indexing-and-query-plans.md).
- **Migrations**: lock levels, `lock_timeout`, `CREATE INDEX CONCURRENTLY`, `NOT VALID` then `VALIDATE`, batched backfills. See [references/safe-online-migrations.md](references/safe-online-migrations.md).
- **Row-Level Security**: `USING` and `WITH CHECK`, session-scoped tenant setting, `FORCE ROW LEVEL SECURITY`, safe `SECURITY DEFINER`. See [references/rls-and-multi-tenancy.md](references/rls-and-multi-tenancy.md).
- **Concurrency**: Read Committed default, Repeatable Read, Serializable with retry on `40001`, `SELECT ... FOR UPDATE [SKIP LOCKED | NOWAIT]`, advisory locks, deadlock avoidance by consistent lock order.
- **Partitioning**: declarative RANGE, LIST and HASH; pruning; per-partition retention by `DETACH PARTITION [CONCURRENTLY]`.
- **Replication and HA**: streaming (physical) replicas, logical replication (publications, subscriptions), failover managers (Patroni or managed service), PITR with WAL archiving.
- **JSONB and search**: `jsonb_path_ops` GIN, `tsvector` full-text search, `pg_trgm`, `pgvector` for embeddings.
- **PostgreSQL 18 additions**:
  - Asynchronous I/O subsystem, selected by `io_method` (`worker` default, `io_uring` on Linux builds with liburing, `sync`); view `pg_aios`.
  - `uuidv7()` for time-ordered UUIDs (optional interval shift); `uuidv4()` is an alias of `gen_random_uuid()`.
  - Generated columns are `VIRTUAL` by default (computed on read, no storage); `STORED` must be written explicitly if wanted.
  - `RETURNING old.*, new.*` for INSERT, UPDATE, DELETE and MERGE.
  - Skip scan on multicolumn B-tree indexes; `pg_upgrade` retains optimizer statistics.
  - `NOT NULL` constraints can be added `NOT VALID` and validated later.
  - `EXPLAIN ANALYZE` includes `BUFFERS` by default; `initdb` enables data checksums by default; OAuth authentication; MD5 password auth deprecated.
  - Temporal constraints: `WITHOUT OVERLAPS` in PRIMARY KEY and UNIQUE, `PERIOD` in foreign keys.

## 3. Workflow

1. Write down the access patterns first: the top queries, their filters, sort order, row counts and write rates.
2. Model with constraints (types, NOT NULL, CHECK, UNIQUE, FK). Index every foreign key column that is joined or cascaded.
3. Load representative data (or production-sized statistics), run `ANALYZE`, then `EXPLAIN (ANALYZE, BUFFERS)` each hot query. Add or change one index at a time and re-measure.
4. Write migrations as small, separately deployable steps (expand, backfill, contract) and set `lock_timeout` on each. Test them against a production-sized copy.
5. Deploy: apply the migration first, then the code that needs it; remove old structure only after no code reads it.
6. Watch `pg_stat_statements`, `pg_stat_activity`, locks, replication lag and autovacuum after release; revisit indexes that show zero scans.
7. When a query is slow, check in this order: plan shape and row estimates, missing or unusable index, stale statistics, lock waits, then configuration.

## 4. Decision Rules

- Prefer an index change over partitioning; partition when retention or maintenance (drop old data, vacuum per partition) justifies it, not just row count.
- Prefer relational columns for anything in `WHERE`, `JOIN` or `ORDER BY`; use JSONB for sparse or evolving attributes, and index the paths you query.
- Prefer a partial index when every query carries the same stable predicate (`WHERE deleted_at IS NULL`, `WHERE status = 'open'`).
- Primary keys: `bigint GENERATED ALWAYS AS IDENTITY` for internal tables; `uuidv7()` when ids are generated across services or exposed externally (time-ordered keys keep B-tree inserts local, unlike random UUIDv4).
- Prefer Read Committed with explicit row locks for queue and counter patterns; Serializable only when the application retries on SQLSTATE `40001`.
- Use physical streaming replication for HA and read replicas; logical replication for cross-version migration, selective tables or change feeds. Neither replaces backups.
- Use PgBouncer transaction pooling for many short-lived clients. In that mode session state (plain `SET`, session advisory locks, `LISTEN`) does not persist between transactions; use `SET LOCAL` and `set_config(..., true)` inside a transaction. PgBouncer 1.21 and later track protocol-level prepared statements (`max_prepared_statements`, non-zero by default).
- Use a virtual generated column for cheap derived values that are read rarely; use `STORED` (or an expression index) when the value must be indexed or replicated logically.

## 5. Coding Standards

- Parameterize every query. Dynamic SQL in PL/pgSQL uses `format('%I', ident)` or `quote_ident` for identifiers and `EXECUTE ... USING` for values.
- Name constraints and indexes explicitly (`orders_customer_id_fkey`, `orders_status_idx`) so migrations can reference them.
- Use `snake_case`, singular or plural table names consistently, `timestamptz` (never `timestamp` for instants), `text` over `varchar(n)` unless a limit is a real rule, `numeric(p,s)` or integer minor units for money.
- List columns explicitly in `INSERT` and in application `SELECT`s; add `ORDER BY` with a unique tiebreaker wherever order matters; bound user-facing lists with `LIMIT` and keyset pagination.
- Use `INSERT ... ON CONFLICT (cols) DO UPDATE` (or `MERGE`) for upserts, and `RETURNING` instead of a follow-up `SELECT`.
- `UPDATE` and `DELETE` have no `LIMIT`. To cap a statement, select keys in a subquery (see section 14).
- Keep transactions short; no network calls or user waits inside a transaction; set `idle_in_transaction_session_timeout` for application roles.
- Run `ANALYZE` after bulk loads and large backfills.

## 6. Project Structure

```
db/
  migrations/        # ordered, immutable, one change set per file (0007_orders_status_add.sql)
  roles.sql          # roles and grants (app, migrator, readonly); no passwords in the repo
  policies/          # RLS policies and helper functions, versioned with migrations
  seeds/dev/         # development-only seed data; never part of the production path
  tests/             # pgTAP or SQL assertions for constraints, policies and migrations
```

Migrations run as a dedicated owner role; the application connects as a different, unprivileged role.

## 7. Design Patterns

- **Expand, backfill, contract**: add nullable column, dual-write, backfill in batches, add the constraint with `NOT VALID` then `VALIDATE`, switch reads, drop the old column in a later release.
- **Job queue**: `SELECT ... FROM jobs WHERE state = 'queued' ORDER BY id LIMIT n FOR UPDATE SKIP LOCKED` inside the worker's transaction.
- **Idempotency key**: a UNIQUE constraint on the key plus `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
- **Audit with old and new values**: `RETURNING old.col, new.col` or a trigger writing to an append-only table (PostgreSQL 18).
- **Soft delete**: `deleted_at timestamptz` with partial unique indexes (`UNIQUE (email) WHERE deleted_at IS NULL`) and a view or RLS policy hiding deleted rows.
- **Time-series and retention**: RANGE partitions by time, a BRIN or small B-tree per partition, `DETACH PARTITION ... CONCURRENTLY` then drop.
- **Multi-tenancy**: shared tables with `tenant_id` plus RLS driven by a per-transaction setting; schema or database per tenant only when isolation or per-tenant restore is a requirement.

## 8. Best Practices

- Enforce rules in the database (NOT NULL, CHECK, FK, UNIQUE, EXCLUDE) in addition to the application; the database sees every writer.
- Use `EXCLUDE USING gist` (or `WITHOUT OVERLAPS` in 18) for non-overlapping ranges such as bookings, instead of application checks.
- Use `CREATE INDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY` on live tables; check `pg_index.indisvalid` afterwards.
- Prefer `EXISTS` over `IN (subquery)` for correlated checks and `NOT EXISTS` over `NOT IN` (NULL semantics).
- CTEs are inlined by default when referenced once and side-effect free; use `MATERIALIZED` only when you want an optimization fence.
- Keep statistics current: raise `default_statistics_target` per column when estimates are off, and add `CREATE STATISTICS` for correlated columns.
- Store large blobs outside the database unless transactional coupling is needed; TOAST handles values up to 1 GB but bloats WAL and backups.

## 9. Performance

- Read plans with `EXPLAIN (ANALYZE, BUFFERS)`: compare estimated and actual rows, look at `Rows Removed by Filter`, sort spills (`Sort Method: external merge`), `Heap Fetches` on index-only scans and nested loops with large outer sides. Details in [references/indexing-and-query-plans.md](references/indexing-and-query-plans.md).
- Enable `pg_stat_statements` (in `shared_preload_libraries`) and rank by total time, then by mean time and calls.
- Starting points (measure, then adjust): `shared_buffers` about 25% of RAM, `effective_cache_size` about 50-75% of RAM, `work_mem` small and raised per role or per query (it applies per sort or hash node, per connection), `maintenance_work_mem` larger for index builds, `random_page_cost` near 1.1 on SSD or NVMe.
- Asynchronous I/O (18): `io_method = worker` is the default and works everywhere; `io_uring` needs Linux and a build with liburing and is set at server start. Reads (sequential and bitmap heap scans, vacuum) benefit; benchmark on the real workload before switching, and tune `io_workers` and `effective_io_concurrency` only with measurements.
- Checkpointing: size `max_wal_size` so checkpoints are timed rather than forced (`pg_stat_checkpointer`), and spread them with `checkpoint_completion_target`.
- Bulk load with `COPY`, and create indexes after loading. Use unlogged tables only for data you can lose.
- Autovacuum: lower `autovacuum_vacuum_scale_factor` (per table with `ALTER TABLE ... SET (...)`) on large, hot tables; investigate long-running transactions and abandoned replication slots that hold back vacuum.
- Deep `OFFSET` pagination scans and discards rows; use keyset pagination (`WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT n`) backed by a matching index.

## 10. Security

- Authentication: SCRAM-SHA-256 (`password_encryption = scram-sha-256`); migrate off MD5 (deprecated in 18). `pg_hba.conf` uses `hostssl ... scram-sha-256` (or `cert`, or `oauth` in 18), never `trust` for network connections.
- TLS on all client and replication connections; verify the server certificate from clients (`sslmode=verify-full`).
- Roles: owner (runs migrations), app (DML only), read-only. Application roles are not superusers, not table owners and do not have BYPASSRLS. Grant on specific tables and sequences; `REVOKE ALL ON SCHEMA public FROM PUBLIC` and `REVOKE CONNECT ON DATABASE ... FROM PUBLIC` where appropriate.
- RLS: tenant identity comes from a trusted server-set transaction setting, never from a function argument or request value; policies carry both `USING` and `WITH CHECK`. Full pattern in [references/rls-and-multi-tenancy.md](references/rls-and-multi-tenancy.md).
- `SECURITY DEFINER` functions set `search_path` explicitly (`SET search_path = pg_catalog, app`), schema-qualify objects, have `EXECUTE` revoked from `PUBLIC`, and never accept a tenant or user id that grants more access.
- Views run with the owner's privileges by default; create views over RLS tables with `WITH (security_invoker = true)`.
- Secrets: no passwords in migrations or seeds; use a secret manager. Use `pgcrypto` or application-level encryption for sensitive columns and manage keys outside the database.
- Audit: `pgaudit` for DDL, role changes and sensitive-table access; `log_connections`, `log_min_duration_statement` and `log_lock_waits` for diagnostics.

## 11. Testing

- Run migrations from an empty database and from the previous release's schema in CI; keep a production-sized data set for lock and duration checks.
- Test constraints and RLS with real roles: `SET ROLE app_user` (or connect as it), set `app.tenant_id` with `set_config(..., true)`, and assert that cross-tenant reads return zero rows and cross-tenant writes fail. Also assert that an unset tenant sees nothing.
- Assert plans for critical queries (index used, no sort spill) with `EXPLAIN (FORMAT JSON)` on representative data.
- Test concurrency (two sessions, `FOR UPDATE SKIP LOCKED`, serialization failures and retries) with scripted sessions or a driver-level harness.
- Rehearse restores and the upgrade path (`pg_upgrade --check`, logical replication cutover) on a copy.

## 12. Review Checklist

- [ ] Every migration step is safe under load: `lock_timeout` set, no table rewrite, indexes `CONCURRENTLY`, constraints `NOT VALID` then validated.
- [ ] No `UPDATE ... LIMIT` or unbounded backfill; backfills run in committed batches.
- [ ] New foreign keys have a supporting index; new queries have a plan reviewed with `BUFFERS`.
- [ ] Tables have a primary key, `timestamptz` instants, named constraints, correct `ON DELETE` actions.
- [ ] Multi-tenant tables have RLS enabled (and forced if the app role could own them), `USING` and `WITH CHECK`, and an index leading with `tenant_id`.
- [ ] `SECURITY DEFINER` functions set `search_path` and do not take tenant ids from callers.
- [ ] Dynamic SQL uses `format('%I')`, `quote_literal` or `USING`; no string concatenation of user input.
- [ ] Autovacuum settings, retention and partition maintenance are covered for large tables.

## 13. Production Notes

- Backups: continuous WAL archiving plus periodic base backups (pgBackRest, Barman or the managed service's PITR); test restores on a schedule. Replicas are not backups.
- Upgrades: minor releases (18.x) are drop-in restarts; majors use `pg_upgrade` (18 retains optimizer statistics, so plan quality survives) or logical replication for near-zero downtime. Run `pg_upgrade --check` first and rebuild extension-dependent objects as each extension documents.
- Data checksums are on by default for new clusters in 18; an existing cluster being upgraded must match the old cluster's setting (`initdb --no-data-checksums` for the target if the old cluster has none).
- Monitor: replication lag, `pg_stat_activity` (idle in transaction, long queries), lock waits, autovacuum progress, XID age (`age(datfrozenxid)`), cache hit ratio, checkpoint stats, disk and WAL growth, replication slot lag.
- Set `statement_timeout`, `lock_timeout` and `idle_in_transaction_session_timeout` per role rather than globally on the owner/migration role.
- Connection limits: each connection is a process; size pools to cores rather than to client count and put PgBouncer (or the managed proxy) in front.

## 14. Examples

Schema with constraints, a time-ordered key and a supporting index:

```sql
CREATE TABLE orders (
  id           uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id    uuid NOT NULL,
  customer_id  bigint NOT NULL REFERENCES customers (id) ON DELETE RESTRICT,
  status       text NOT NULL DEFAULT 'new'
               CONSTRAINT orders_status_chk CHECK (status IN ('new', 'paid', 'shipped', 'cancelled')),
  total_cents  bigint NOT NULL CONSTRAINT orders_total_chk CHECK (total_cents >= 0),
  created_at   timestamptz NOT NULL DEFAULT now(),
  total_eur    numeric GENERATED ALWAYS AS (total_cents / 100.0) VIRTUAL   -- 18: virtual by default
);
CREATE INDEX orders_tenant_customer_idx ON orders (tenant_id, customer_id);
```

Capped batch update. `UPDATE ... LIMIT` is a syntax error; select the keys in a subquery and commit between batches (a procedure called with `CALL` outside an explicit transaction can `COMMIT`):

```sql
CREATE PROCEDURE backfill_order_status(batch_size int DEFAULT 5000)
LANGUAGE plpgsql AS $$
DECLARE
  n int;
BEGIN
  LOOP
    UPDATE orders
       SET status = 'new'
     WHERE id IN (SELECT id FROM orders
                   WHERE status IS NULL
                   ORDER BY id
                   LIMIT batch_size
                   FOR UPDATE SKIP LOCKED);
    GET DIAGNOSTICS n = ROW_COUNT;
    EXIT WHEN n = 0;
    COMMIT;
    PERFORM pg_sleep(0.05);   -- let replicas and vacuum keep up
  END LOOP;
END $$;
-- CALL backfill_order_status(5000);  then verify: SELECT count(*) FROM orders WHERE status IS NULL;
```

Old and new values in one statement (PostgreSQL 18), tenant-scoped through RLS:

```sql
UPDATE accounts
   SET balance_cents = balance_cents - $2
 WHERE id = $1
RETURNING old.balance_cents AS balance_before, new.balance_cents AS balance_after;
```

Tenant context set per transaction by the server (the tenant id comes from the authenticated session, not from the request body); the policies are in the RLS reference:

```sql
BEGIN;
SELECT set_config('app.tenant_id', $1, true);   -- true = local to this transaction
SELECT id, total_cents FROM orders WHERE status = 'paid' ORDER BY created_at DESC LIMIT 50;
COMMIT;
```

## 15. Common Mistakes

- `UPDATE ... LIMIT n`: not valid PostgreSQL. Use `WHERE id IN (SELECT id ... LIMIT n FOR UPDATE SKIP LOCKED)` or key ranges.
- Plain `CREATE INDEX` on a live table (blocks writes), or `CREATE INDEX CONCURRENTLY` inside a transaction block (error). Leaving an `INVALID` index after a failed concurrent build.
- Adding a CHECK, FK or NOT NULL in one step on a big table: the validation scan holds a lock. Add `NOT VALID`, then `VALIDATE CONSTRAINT`.
- Rewriting migrations with volatile defaults: `ADD COLUMN ... DEFAULT <non-volatile>` is fast (since PostgreSQL 11), but a volatile default (for example `uuidv7()` or `random()`) or a `STORED` generated column rewrites the table.
- DDL without `lock_timeout`: a queued `ACCESS EXCLUSIVE` request blocks every later query behind it.
- Tenant id passed as a parameter to a `SECURITY DEFINER` function, or RLS policies with only `USING` (writes unchecked), or an app role that owns the table or has BYPASSRLS.
- `current_setting('app.tenant_id')` without the `true` missing-ok flag, or casting an empty string, which raises errors instead of failing closed.
- Using `timestamp` instead of `timestamptz`, `float` for money, `NOT IN` with nullable subqueries, `OFFSET` for deep pagination.
- Session-level `SET` behind a transaction-mode pooler: the setting leaks to the next client or vanishes. Use `SET LOCAL` or `set_config(..., true)`.
- Idle-in-transaction connections and forgotten replication slots that block vacuum and bloat tables.
- Indexes on every column "just in case": each index costs write throughput and vacuum time; drop ones with zero scans after observing a full business cycle.
- Assuming 18 features on older servers (`uuidv7()`, `io_method`, `RETURNING old/new`, virtual generated columns, `NOT NULL ... NOT VALID`); check `server_version_num` in portable migrations.

## 16. References

- [references/indexing-and-query-plans.md](references/indexing-and-query-plans.md): index types, multicolumn and skip scan, partial and covering indexes, reading EXPLAIN, statistics, slow-query workflow.
- [references/safe-online-migrations.md](references/safe-online-migrations.md): lock levels, `lock_timeout` retries, concurrent indexes, `NOT VALID` constraints, NOT NULL, batched backfills, renames, partition changes.
- [references/rls-and-multi-tenancy.md](references/rls-and-multi-tenancy.md): tenant setting, policies with `USING` and `WITH CHECK`, `FORCE ROW LEVEL SECURITY`, safe `SECURITY DEFINER`, pooling and testing.
- PostgreSQL 18 documentation: https://www.postgresql.org/docs/18/ (release notes: https://www.postgresql.org/docs/18/release-18.html); versioning policy: https://www.postgresql.org/support/versioning/
