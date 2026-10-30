# Row-Level Security and Multi-Tenancy (PostgreSQL 18)

Pattern for shared-table multi-tenancy where the database enforces isolation, so a missing `WHERE tenant_id = ...` in application code cannot leak data.

## Trust model

- The **tenant id comes from the server**: the authenticated session or verified token, resolved by your backend. It is never taken from a request body, header or function argument supplied by the caller.
- The backend sets it **per transaction** with `set_config('app.tenant_id', <id>, true)` (the third argument `true` makes it local to the transaction, equivalent to `SET LOCAL`). Transaction scope is what makes this safe behind PgBouncer transaction pooling: nothing survives `COMMIT` or `ROLLBACK`, so a pooled connection cannot carry one tenant's context into the next request.
- The application connects as an **unprivileged role** that is not the table owner, not a superuser, and not `BYPASSRLS`. Superusers and `BYPASSRLS` roles skip policies entirely; table owners skip them unless the table is `FORCE`d.

## Setup

```sql
-- Roles: the owner runs migrations; the app role only gets DML
CREATE ROLE app_owner NOLOGIN;
CREATE ROLE app_user  LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;   -- set its password outside the repo

CREATE SCHEMA app AUTHORIZATION app_owner;
GRANT USAGE ON SCHEMA app TO app_user;

-- Helper: reads the trusted setting; returns NULL (no rows match) when unset or empty
CREATE FUNCTION app.current_tenant() RETURNS uuid
LANGUAGE sql STABLE
AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$;
```

`current_setting(name, true)` returns NULL instead of raising when the setting was never defined; after a transaction that used `set_config(..., true)` ends, the setting may read back as an empty string, hence `nullif(..., '')`. With NULL, `tenant_id = NULL` is never true, so the policy fails closed.

```sql
CREATE TABLE app.invoices (
  id          uuid PRIMARY KEY DEFAULT uuidv7(),
  tenant_id   uuid NOT NULL,
  number      text NOT NULL,
  total_cents bigint NOT NULL CHECK (total_cents >= 0),
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, number)
);
CREATE INDEX invoices_tenant_created_idx ON app.invoices (tenant_id, created_at DESC);

ALTER TABLE app.invoices OWNER TO app_owner;
ALTER TABLE app.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.invoices FORCE ROW LEVEL SECURITY;      -- owner is also subject to policies (not superusers or BYPASSRLS)

CREATE POLICY tenant_isolation ON app.invoices
  FOR ALL                                                 -- no TO clause: applies to every role, including the forced owner
  USING      (tenant_id = (SELECT app.current_tenant()))   -- which existing rows are visible / updatable / deletable
  WITH CHECK (tenant_id = (SELECT app.current_tenant()));  -- which rows may be inserted or result from an update

GRANT SELECT, INSERT, UPDATE, DELETE ON app.invoices TO app_user;
```

Because the policy also binds the forced owner, maintenance that must see every tenant (cross-tenant backfills, data fixes) runs as a dedicated `BYPASSRLS` role used only for that job, not as the application role.

- `USING` filters rows for SELECT, UPDATE and DELETE. `WITH CHECK` validates new row versions on INSERT and UPDATE. For `FOR ALL`, omitting `WITH CHECK` makes PostgreSQL reuse `USING`, but state both explicitly so the intent is visible and a later per-command split does not drop it.
- Wrapping the helper in `(SELECT ...)` lets the planner evaluate it once per statement (an initplan) instead of per row.
- With RLS enabled and no matching policy, the default is deny: no rows visible, writes rejected.
- Index `tenant_id` first in indexes that serve tenant queries; policies add the predicate to every query.
- Prefer one policy per command when rules differ (for example read broadly, write narrowly); policies for the same command are combined with OR unless declared `AS RESTRICTIVE` (combined with AND).

## Application side

```sql
BEGIN;
SELECT set_config('app.tenant_id', $1, true);        -- $1 from the verified session, bound as a parameter
INSERT INTO app.invoices (tenant_id, number, total_cents)
VALUES ((SELECT app.current_tenant()), $2, $3)
RETURNING id;
COMMIT;
```

An insert with a different `tenant_id` fails with `new row violates row-level security policy`; an update or delete of another tenant's row simply matches zero rows.

For application code, open one transaction per request or unit of work, run `set_config` as its first statement, and run all queries on that same connection and transaction. Queries outside a transaction block have no tenant set and therefore see nothing.

## SECURITY DEFINER done safely

`SECURITY DEFINER` runs a function with its owner's privileges. If the owner bypasses RLS, a function that accepts a tenant id from the caller turns into a cross-tenant read. Rules:

- Do not pass the tenant id (or any value that selects whose data to return) as a parameter. Derive it from the trusted setting via `app.current_tenant()`, or avoid `SECURITY DEFINER` and let RLS apply to the caller.
- Always pin `search_path` on the function and schema-qualify objects, so a caller cannot shadow functions or tables with their own schema.
- `REVOKE EXECUTE ... FROM PUBLIC`, then grant to the specific role.
- Keep the function narrow: one query, no dynamic SQL built from arguments.

```sql
-- Owned by app_owner; FORCE ROW LEVEL SECURITY keeps the policy in effect for the owner, and the
-- explicit WHERE keeps the tenant filter visible in the function body
CREATE FUNCTION app.invoice_total() RETURNS bigint
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, app
AS $$
  SELECT COALESCE(sum(total_cents), 0)::bigint
    FROM app.invoices
   WHERE tenant_id = app.current_tenant()
$$;
REVOKE ALL ON FUNCTION app.invoice_total() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.invoice_total() TO app_user;
```

Anti-pattern to avoid: `CREATE FUNCTION get_invoices(p_tenant uuid) ... SECURITY DEFINER` with no `search_path` and no check that `p_tenant` is the caller's tenant.

Cross-tenant administrative access (support tooling, reporting) uses a separate role with its own, audited policies or a `BYPASSRLS` role used only by a separate, restricted service, never by the tenant-facing app.

## Pitfalls

- **Views**: a view runs with its owner's privileges, so it can bypass RLS on underlying tables. Create it with `WITH (security_invoker = true)` so the caller's rights and policies apply.
- **Functions in policies** must be cheap and `STABLE` or `IMMUTABLE` where possible; slow policy expressions slow every query. Mark helpers `LEAKPROOF` only when truly safe (superuser only).
- **Constraint side channels**: unique and foreign key checks can reveal that a row exists in another tenant (an error for a duplicate key). Include `tenant_id` in unique keys and foreign keys so references stay within a tenant (`FOREIGN KEY (tenant_id, customer_id) REFERENCES customers (tenant_id, id)`).
- **Session-level settings**: `SET app.tenant_id = ...` (without `LOCAL`) persists on a pooled connection across clients. Use `set_config(..., true)` inside a transaction only.
- **Superuser, `BYPASSRLS`, table owner (without `FORCE`)** are not restricted. Check with `SELECT rolname, rolsuper, rolbypassrls FROM pg_roles;` and `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'invoices';`.
- **pg_dump** and logical replication use roles that typically bypass RLS; protect those credentials accordingly. `pg_dump --enable-row-security` applies policies.
- **Partitioned tables**: enable RLS and policies on the parent; policies of partitions apply only when the partition is queried directly.
- **Performance**: add `tenant_id` to every index that serves tenant queries; verify with `EXPLAIN` as the app role (`SET ROLE app_user;` then `SELECT set_config('app.tenant_id', '<uuid>', false);`, remembering to `RESET ROLE`).

## Tests (SQL or pgTAP)

```sql
BEGIN;
SET LOCAL ROLE app_user;
SELECT set_config('app.tenant_id', '11111111-1111-1111-1111-111111111111', true);
-- sees only tenant A rows
SELECT count(*) FROM app.invoices WHERE tenant_id <> '11111111-1111-1111-1111-111111111111';     -- expect 0
-- cannot write into another tenant
INSERT INTO app.invoices (tenant_id, number, total_cents)
VALUES ('22222222-2222-2222-2222-222222222222', 'X-1', 100);                                      -- expect ERROR (RLS)
ROLLBACK;

BEGIN;
SET LOCAL ROLE app_user;
SELECT count(*) FROM app.invoices;                                                               -- unset tenant: expect 0
ROLLBACK;
```

Also test: `UPDATE` that tries to change `tenant_id` to another tenant (blocked by `WITH CHECK`), the `SECURITY DEFINER` functions under two tenants, and a pooled-connection reuse sequence (tenant A request, then tenant B request on the same connection).

## Other isolation models

- **Schema per tenant**: strong logical separation and per-tenant restore, but migrations run N times and catalog size grows; set `search_path` per transaction with `SET LOCAL`.
- **Database per tenant**: strongest isolation, highest operational cost; use for regulated or very large tenants.
- Combine: RLS for the long tail of small tenants, dedicated databases for large or regulated ones.
