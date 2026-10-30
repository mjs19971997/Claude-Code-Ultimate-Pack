# Multi-Tenant Isolation

Reference for isolating tenants in an application and database so that reads AND writes are confined to the caller's tenant. Verified against PostgreSQL 16 to 18 row-level security semantics (`CREATE POLICY` with `USING` and `WITH CHECK`), `node-postgres` 8.x and the OWASP API Security Top 10 2023 (2026-10).

## 1. Isolation strategies

| Strategy | Isolation | Cost | Notes |
|---|---|---|---|
| Shared tables, `tenant_id` column | Logical, enforced by queries and RLS | Lowest | Needs discipline on every statement; add RLS as a second layer |
| Schema per tenant | Stronger namespace separation | Migrations run per schema, catalog bloat at thousands of tenants | Easy per-tenant backup and restore |
| Database per tenant | Strong | Highest operational cost | Fits regulated or very large tenants |
| Dedicated deployment | Strongest | Highest | Contractual isolation, data residency |

Pick per tier: many small tenants on shared tables with RLS, a few large or regulated tenants on dedicated databases.

## 2. Tenant context

- Derive the tenant from the authenticated principal on the server (membership lookup or a validated token claim), not from a header, query string or body field the client controls. If a user belongs to several tenants, the client may select one, and the server verifies membership for that selection on every request.
- Carry the tenant in a request-scoped context object (for example `AsyncLocalStorage` in Node) so that data access code cannot be called without it. A repository function that takes `tenantId` as a required parameter is better than one that reads a global.
- Include `tenant_id` in every table that holds tenant data, in primary or unique keys where uniqueness is per tenant (`UNIQUE (tenant_id, number)`), and in composite foreign keys (`FOREIGN KEY (tenant_id, customer_id) REFERENCES customers (tenant_id, id)`) so a row cannot reference another tenant's parent.

## 3. Reads AND writes

A tenant predicate on SELECT only is a classic hole: an attacker who guesses an id can UPDATE or DELETE another tenant's row, or INSERT/UPDATE a row so that it lands in another tenant.

```sql
-- every statement carries the predicate
SELECT * FROM invoices WHERE id = $1 AND tenant_id = $2;
UPDATE invoices SET amount = $3 WHERE id = $1 AND tenant_id = $2;
DELETE FROM invoices WHERE id = $1 AND tenant_id = $2;
INSERT INTO invoices (tenant_id, number, amount) VALUES ($1, $2, $3); -- tenant from context, never from the body
```

- UPDATE must not allow changing `tenant_id`; omit it from the SET list and, with RLS, let `WITH CHECK` reject it.
- Bulk operations, `INSERT ... SELECT`, `MERGE`, upserts (`ON CONFLICT DO UPDATE ... WHERE tenant_id = ...`), background jobs, exports, search indexes, caches and file storage paths need the same scoping. Cache keys include the tenant id.
- Raw queries, reports and admin scripts bypass ORM-level scoping. Review them as a class.
- Return 404 for objects in another tenant so existence is not revealed.

## 4. PostgreSQL row level security

RLS makes the database refuse cross-tenant access even when application code forgets a predicate. Facts from the PostgreSQL documentation:
- Once RLS is enabled on a table, all normal access must be allowed by a policy; with no policy, a default-deny applies and no rows are visible or modifiable.
- `USING` filters existing rows (SELECT, UPDATE, DELETE targets). `WITH CHECK` validates new or changed rows (INSERT, UPDATE). For `FOR ALL` policies with only `USING`, that expression is also used as `WITH CHECK`; write both explicitly for clarity.
- Superusers and roles with `BYPASSRLS` always bypass RLS. Table owners bypass it too unless `ALTER TABLE ... FORCE ROW LEVEL SECURITY` is set.
- `TRUNCATE` and `REFERENCES` checks are not subject to row security.
- Multiple permissive policies combine with OR; restrictive policies (`AS RESTRICTIVE`) combine with AND.

Setup (tested on PostgreSQL 16):

```sql
CREATE ROLE app_owner NOLOGIN;                                  -- owns the schema, runs migrations
CREATE ROLE app_user LOGIN NOSUPERUSER NOBYPASSRLS;             -- runtime role; set its password out of band

CREATE TABLE app.invoices (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id  uuid NOT NULL,
  number     text NOT NULL,
  amount     numeric(12,2) NOT NULL,
  UNIQUE (tenant_id, number)
);

ALTER TABLE app.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.invoices FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON app.invoices
  AS PERMISSIVE FOR ALL TO app_user
  USING      (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

GRANT USAGE ON SCHEMA app TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.invoices TO app_user;
```

`current_setting('app.tenant_id', true)` returns NULL when the setting is absent, and `tenant_id = NULL` is never true, so a connection without a tenant context sees and changes nothing. The `nullif(..., '')` guards the empty string left behind after a transaction-local setting ends.

Observed behavior with the policy above, for a session whose tenant is B:
- `SELECT` shows only tenant B rows.
- `UPDATE invoices SET amount = 1 WHERE number = 'INV-1'` changes only B's row.
- `DELETE FROM invoices WHERE tenant_id = '<A>'` deletes 0 rows.
- `INSERT ... tenant_id = '<A>'` fails with "new row violates row-level security policy".
- `UPDATE invoices SET tenant_id = '<A>'` fails the same way, so rows cannot be moved to another tenant.
- With no tenant set, queries return 0 rows.

Setting the tenant per transaction with a pooled connection:

```ts
import type { Pool } from "pg";

export async function withTenant<T>(
  pool: Pool,
  tenantId: string,
  fn: (client: import("pg").PoolClient) => Promise<T>,
): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    // is_local = true: the setting disappears at COMMIT or ROLLBACK, so it cannot leak to the next pool user.
    await client.query("SELECT set_config('app.tenant_id', $1, true)", [tenantId]);
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
```

Pitfalls:
- Session-level `SET app.tenant_id` on a pooled connection leaks the tenant to the next request. Use `set_config(..., true)` inside a transaction (or `SET LOCAL`). With PgBouncer in transaction pooling mode this is the only safe form.
- Values in `current_setting` are user-settable by anyone who can run SQL as that role. RLS defends against application bugs, not against a caller who can execute arbitrary SQL as `app_user`; do not expose raw SQL execution to tenants.
- Connecting as the owner or a superuser silently disables RLS (unless `FORCE`). Verify in a test that the runtime role is not exempt: `SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user` must return false for both.
- Policy expressions run for every row; index `tenant_id` (usually as the leading column of composite indexes) and avoid subqueries that hit other RLS-protected tables on hot paths.
- Views run with the view owner's privileges and may bypass RLS; define them with `security_invoker = true` (PostgreSQL 15 and later).
- Functions marked `SECURITY DEFINER` run as their owner; keep them minimal and set `search_path`.
- Admin and support access: use a separate role with `BYPASSRLS` used only by audited tooling, never the application role.

## 5. Application level scoping without RLS

When RLS is not available (other databases), enforce scoping in a single data-access layer:
- A repository base class or query builder wrapper that appends the tenant predicate and refuses to run without a tenant context.
- ORM global filters (for example Prisma client extensions) are convenient but are skipped by raw queries; test that raw paths are also scoped. See prisma-expert for the extension mechanism.
- Lint or code-review rules that flag raw SQL touching tenant tables.

## 6. Testing isolation

- Create two tenants with overlapping data. For every endpoint, call it as tenant A with ids that belong to tenant B and assert 404 (reads) and no change (writes, deletes). Verify in the database that tenant B's rows are unchanged.
- Test list endpoints, search, exports and counts for leakage.
- Run the same tests with the application role to prove that RLS alone blocks the statements when the application predicate is removed (a test-only repository that omits the predicate).
- Test the failure path: no tenant context should produce an error or zero rows, never all rows.
- Test background jobs and queue consumers with a tenant context taken from the message, validated against the object.
