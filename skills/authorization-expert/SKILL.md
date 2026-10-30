---
name: authorization-expert
description: >-
  Designs and reviews access control: RBAC, ABAC and ReBAC (Zanzibar-style with OpenFGA or SpiceDB), policy engines (OPA/Rego, Cedar), deny-by-default enforcement on the server for every request, object-level (BOLA/IDOR) and function-level checks, field-level rules, multi-tenant isolation for reads and writes including PostgreSQL row-level security, decision auditing and authorization test matrices. Use when adding permission checks, roles, sharing or ownership rules, tenant isolation, policy files, or when reviewing an endpoint for broken access control. Not for login, sessions, password handling or token issuance (use authentication-expert), or general endpoint hardening such as rate limiting and input validation (use api-security-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Authorization Expert

This skill covers deciding what an already-identified caller may do: access-control models, where checks are enforced, how decisions are made and logged, tenant isolation, and how to test all of it. It rewrites the former authorization-expert skill from scratch. Authentication (who the caller is) is a separate concern.

> Verified against OpenFGA 1.22.x (`@openfga/sdk` 0.9.x), SpiceDB 1.57.x, Open Policy Agent 1.22.x (Rego v1 syntax), Cedar 4.14.x, PostgreSQL 16 to 18 row-level security, `@casl/ability` 7.1.x and the OWASP API Security Top 10 2023 (2026-10).

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

- Covered: access-control models (RBAC, ABAC, ReBAC), permission and policy design, enforcement points, object-level and function-level checks, field-level rules, multi-tenant isolation (application predicates and PostgreSQL RLS), OAuth scopes versus permissions, policy engines (OPA, Cedar, OpenFGA, SpiceDB), decision logging, authorization testing.
- Not covered: credential verification, sessions, MFA, JWT signing and validation, token issuance (authentication-expert); request hardening such as rate limits, schema validation and CORS (api-security-expert); general vulnerability classes (secure-coding-expert); modeling the domain itself (ddd-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Broken access control | OWASP API1:2023 BOLA (object ids), API3:2023 BOPLA (properties), API5:2023 BFLA (functions); the same classes appear as IDOR and as Broken Access Control in the OWASP Top 10 |
| Authorization vs authentication | Authentication produces a principal; authorization takes `(principal, action, resource, context)` and returns allow or deny |
| RBAC | Role maps to permission set; check permissions, not role names; scope roles to a tenant or project |
| ABAC | Rules over attributes of subject, resource, action, environment; pure functions are testable |
| ReBAC | Relationship tuples `object#relation@subject` and graph evaluation (Zanzibar paper, 2019); OpenFGA and SpiceDB implement it |
| Policy engines | OPA (Rego), Cedar (`permit`/`forbid`, forbid overrides permit, default deny), both embeddable or run as a service |
| Tenant isolation | `tenant_id` on every statement, including UPDATE and DELETE; PostgreSQL RLS with `USING` and `WITH CHECK` as a second layer |
| OAuth scopes | Limit a client or token; effective access is scopes intersected with the user's permissions on the object |
| Decision records | Principal, action, resource, decision, reason, policy version, request id |

## 3. Workflow

1. Inventory resources and actions: list every object type, every operation, and who legitimately performs it (a table of role x action x ownership).
2. Choose the model per resource type: roles for coarse features, relationships for sharing and nesting, attributes for conditions (see Decision Rules).
3. Define the principal shape (id, tenant, roles, relevant attributes) and the single decision interface `decide(principal, action, resource, context) -> {allow, reason}`.
4. Enforce at two levels on the server: a function-level check before the handler runs (is this action available to this caller at all) and an object-level check after the object is loaded (is this object accessible).
5. Scope data access by tenant in every statement and add database-level isolation (RLS) where available.
6. Handle lists and searches: filter in the query (tenant predicate plus permission filter), never fetch everything and filter in memory after paging.
7. Add decision logging and metrics for denials.
8. Write the matrix tests and negative tests before wiring the last endpoint; run them in CI.

## 4. Decision Rules

- Default is deny. A missing rule, unknown role, unknown action, missing attribute, engine timeout or thrown error results in deny.
- Enforce on the server, on every request, for every method (GET, POST, PUT, PATCH, DELETE), including internal endpoints, GraphQL resolvers, WebSocket messages, file downloads and background jobs. Hiding a button in the UI is usability, not security.
- Model choice: coarse capabilities and admin tools use RBAC; "owner can edit", sharing, folders, teams and organization hierarchies use ReBAC or ownership checks; conditions on amount, status, time or department use attributes; mixed needs use RBAC for the capability plus an object-level rule.
- Engine choice: one service and simple rules use a pure policy function in code; several services sharing rules use OPA or Cedar; large relationship graphs and sharing features use OpenFGA or SpiceDB. Do not adopt a separate engine for a handful of roles.
- Local enforcement, central decisions: every service calls the enforcement point itself; the policy data and logic live in one place (a shared module, a policy bundle or a relationship store). A gateway may do coarse checks but never replaces object-level checks.
- Not found versus forbidden: when the caller has no right to know an object exists (other tenant, private object), respond 404; when the object is visible but the action is not permitted, respond 403.
- Scopes are not permissions. A token scope is necessary for an endpoint but never sufficient for an object.
- Identity of tenant, owner and role comes from server-side data (session, verified token claims plus membership lookup), never from request bodies, query strings or editable headers.
- Authorization changes need a revocation story: how long a removed role or relationship stays effective (token lifetime, cache TTL, replication delay).

## 5. Coding Standards

- One decision function per resource type, pure, taking explicit inputs and returning a decision object with a reason string. Handlers do not contain role comparisons.
- Permissions are constants or a typed union (`"invoice:update"`), not free strings built from user input.
- Repository functions that read or write tenant data require `tenantId` as a parameter; do not give them a default.
- Write statements repeat the tenant predicate: `UPDATE ... WHERE id = $1 AND tenant_id = $2`, same for DELETE; INSERT takes the tenant from context.
- Use allowlists for writable fields and response fields; map to DTOs explicitly.
- Fail closed: wrap engine calls so that errors, timeouts and unexpected response shapes return deny.
- Use UUIDs or other non-sequential ids to reduce guessing, but do not rely on them as protection.
- Prefer middleware or decorators for function-level checks (declared next to the route) and service-layer calls for object-level checks.

## 6. Project Structure

```
src/
├── authz/
│   ├── policy.ts          # pure decide() functions per resource type
│   ├── permissions.ts     # Action union, role -> permission map
│   ├── principal.ts       # Principal type and builder from verified identity
│   ├── enforce.ts         # requirePermission() middleware, assertCan() helper
│   ├── audit.ts           # decision logging
│   └── engine/            # OPA, Cedar, OpenFGA or SpiceDB client wrappers (optional)
├── db/
│   ├── tenant-context.ts  # withTenant(): sets app.tenant_id per transaction
│   └── migrations/        # includes RLS policies
├── modules/invoices/
│   ├── routes.ts          # route + function-level check
│   ├── service.ts         # load object, assert decision, write
│   └── repository.ts      # tenant-scoped SQL
└── test/authz/
    ├── matrix.test.ts     # role x action x ownership x tenant
    └── isolation.test.ts  # cross-tenant read, update, delete
policies/                  # rego/ or cedar/ files, with tests, versioned
```

## 7. Design Patterns

- **Policy decision function**: `decide(principal, action, resource)` returns `{allow, reason}`; the reason feeds the audit log and error messages for operators.
- **Enforcement point at the service layer**: `assertCan(principal, action, resource)` throws; handlers cannot forget it if the service method needs a `Principal` argument.
- **Load-then-authorize with scoped load**: load the object with the tenant predicate, then run the decision with the loaded attributes (owner, status), then write with the tenant predicate again.
- **Permission filter for lists**: for ReBAC, ask the engine for accessible ids (`ListObjects` or `LookupResources`) and intersect with a tenant-scoped query; for RBAC and ABAC, translate the rule to SQL conditions.
- **Defense in depth**: application predicate plus database RLS; function-level check plus object-level check; engine decision plus SQL predicate.
- **Policy as data**: role-to-permission maps and policy bundles are versioned artifacts with tests and review, deployed independently of code when the engine supports it.
- **Break-glass and impersonation as explicit flows**: separate permissions, recorded actor and subject, time limit, alert.
- Model details and engine syntax: [references/models-rbac-abac-rebac.md](references/models-rbac-abac-rebac.md), [references/policy-engines.md](references/policy-engines.md).

## 8. Best Practices

- Write the permission table first (who may do what to which object type) and review it with the product owner; encode it in tests.
- Keep roles few and meaningful; model per-object access with relationships or ownership, not new roles.
- Treat every new endpoint as default-deny: a route without an explicit authorization declaration fails a lint or test.
- Centralize error mapping: authorization failures use one error type and one response shape, with no policy internals leaked.
- Re-check authorization at the point of use for multi-step flows (upload then attach, export job then download): the download request checks again.
- Authorize batch and bulk endpoints per item; one allowed id in a batch does not allow the rest.
- Authorize nested resources through the parent chain: `/projects/:pid/tasks/:tid` verifies that task `tid` belongs to project `pid` and that the caller may access the project.
- Re-authorize on read of shared links, signed URLs and cached results; signed URLs expire quickly and bind to the object.
- Keep group, role and relationship changes auditable (who changed what and when).

## 9. Performance

- Evaluate the cheap checks first (tenant match, role grant) and call remote engines only when needed.
- Batch checks (`batchCheck` in OpenFGA, bulk check APIs) for pages of objects instead of one call per row; for large lists use list-objects style queries to produce an id filter.
- Cache decisions only with a short TTL and a key that includes principal, action, resource and policy version; invalidate on role or relationship changes. Positive caches amplify revocation delay.
- With SpiceDB, choose consistency per call: `minimize_latency` by default, `fully_consistent` or a stored ZedToken right after a permission change.
- Index `tenant_id` first in composite indexes; RLS policies run per row and benefit from the same index.
- Load principal attributes once per request and pass them down; do not re-query roles in every check.
- Measure engine latency and set client timeouts (tens to a few hundred milliseconds) with deny on timeout.

## 10. Security

- BOLA/IDOR: every route taking an object id must check that the principal may access that specific object. Authentication plus a valid id is not authorization.
- BFLA: administrative and privileged functions (user management, export, impersonation, configuration) need explicit function-level checks; do not rely on an unlinked URL or a different path prefix.
- BOPLA/mass assignment: allowlist writable properties; never bind request bodies directly to models that include `role`, `tenant_id`, `owner_id`, `is_admin`, `status`.
- Multi-tenancy: the tenant predicate belongs in reads AND writes (UPDATE, DELETE, upsert, bulk); see [references/multi-tenancy.md](references/multi-tenancy.md) for RLS with `USING` and `WITH CHECK`.
- Database roles: the runtime role has no superuser and no `BYPASSRLS`, and is not the table owner (or the table uses `FORCE ROW LEVEL SECURITY`).
- Do not trust client-supplied role or tenant data, hidden form fields, or JWT claims that are not verified and freshly sourced for sensitive actions.
- Path and file access: resolve and normalize user-supplied paths, then check the result stays under the allowed base directory and belongs to the principal's tenant; prefer opaque ids mapped server-side to storage keys.
- Avoid enumeration: uniform responses for other-tenant objects, non-sequential ids, rate limits on repeated denials (api-security-expert).
- Secrets for engine access (OpenFGA API tokens, SpiceDB preshared keys) come from a secret store, not from source or client bundles.
- Audit log integrity: append-only storage, no tokens or PII beyond what is needed, retention aligned with policy.

## 11. Testing

- Matrix test: generate cases from the permission table, every role x action x (owner, non-owner) x (same tenant, other tenant) x object state. Assert both allows and denies.
- Negative tests: no credentials, no roles, unknown role, unknown action, null or missing attributes, malformed ids, deleted objects, expired grants, suspended user.
- Cross-tenant tests at the HTTP level: tenant A requests, updates and deletes tenant B ids; expect 404 and unchanged rows; check lists, search, counts and exports for leaks.
- Function-level tests: every route called with the lowest-privileged valid user; the test fails when a route is added without an authorization declaration.
- Mass assignment tests: send `role`, `tenant_id`, `owner_id` in create and update bodies and assert they are ignored or rejected.
- Policy unit tests: `opa test`, Cedar policy tests with fixture entities, OpenFGA model tests (`fga model test`) or tuples written to a test store; run them without the application.
- Database tests: connect as the runtime role and prove RLS blocks cross-tenant SELECT, UPDATE, DELETE and INSERT even without the application predicate.
- Revocation tests: remove a role or relationship and assert the next request is denied after the documented delay.
- Snapshot the effective permission matrix in CI and review changes in pull requests.

## 12. Review Checklist

- [ ] Every route has an explicit function-level check; the default for undeclared routes is deny.
- [ ] Every handler taking an object id checks access to that object (BOLA), including nested ids.
- [ ] Tenant, owner and roles come from server-side data, never from the request.
- [ ] UPDATE, DELETE, upsert and bulk statements include the tenant predicate, not only SELECT.
- [ ] RLS policies have both `USING` and `WITH CHECK`; runtime role cannot bypass RLS.
- [ ] Responses and writes use allowlists (no mass assignment, no excessive data exposure).
- [ ] Lists, search, counts and exports are filtered by tenant and permission in the query.
- [ ] OAuth scopes are checked in addition to, not instead of, user permissions.
- [ ] Engine failures and timeouts deny; decisions are logged with reason and policy version.
- [ ] Matrix tests, cross-tenant tests and negative tests exist and run in CI.

## 13. Production Notes

- Roll out new policies in shadow mode first: evaluate the new policy next to the old one, log differences, then switch.
- Version policies and models (OpenFGA `authorizationModelId`, OPA bundle revision, Cedar policy set hash) and log the version with each decision so incidents can be replayed.
- Plan for the engine being unavailable: deny with a clear error, alert, and keep a documented manual process for critical operations.
- Revocation latency is a requirement: write down the maximum time between removing access and it taking effect, and match caches and token lifetimes to it.
- Sync between the application database and a relationship store (OpenFGA, SpiceDB) needs a reconciliation job and an outbox so tuples do not drift from reality.
- Alert on bursts of denials, on sequences of denied ids from one principal, and on use of break-glass access.
- Periodic access reviews: list who holds admin roles and high-risk relationships, and remove stale grants.
- Migrating from roles to relationships: dual-write, compare decisions in shadow mode, then cut over per resource type.

## 14. Examples

Pure policy function with tenant, role, ownership and attribute rules (tested with Node 22 and `node --test`):

```ts
export type Action = "invoice:read" | "invoice:update" | "invoice:delete";

export interface Principal { id: string; tenantId: string; roles: readonly string[]; }
export interface InvoiceResource { tenantId: string; ownerId: string; status: "draft" | "sent" | "paid"; }
export interface Decision { allow: boolean; reason: string; }

const rolePermissions: Readonly<Record<string, ReadonlySet<Action>>> = {
  viewer: new Set<Action>(["invoice:read"]),
  editor: new Set<Action>(["invoice:read", "invoice:update"]),
  admin: new Set<Action>(["invoice:read", "invoice:update", "invoice:delete"]),
};

const deny = (reason: string): Decision => ({ allow: false, reason });
const allow = (reason: string): Decision => ({ allow: true, reason });

export function decide(p: Principal, action: Action, r: InvoiceResource): Decision {
  if (p.tenantId !== r.tenantId) return deny("tenant-mismatch");

  const granted = p.roles.some((role) => rolePermissions[role]?.has(action) ?? false);
  const isOwnerRead = action === "invoice:read" && r.ownerId === p.id;
  if (!granted && !isOwnerRead) return deny("no-matching-grant");

  // Attribute rule: paid invoices are immutable for everyone.
  if (action !== "invoice:read" && r.status === "paid") return deny("invoice-is-paid");

  return allow(isOwnerRead && !granted ? "owner-read" : "role-grant");
}
```

Service method: scoped load, decision, audited result, scoped write:

```ts
export async function updateAmount(db: Pool, principal: Principal, id: string, amount: string,
                                   audit: (e: Record<string, unknown>) => void) {
  const { rows } = await db.query(
    `SELECT id, tenant_id AS "tenantId", owner_id AS "ownerId", status
       FROM invoices WHERE id = $1 AND tenant_id = $2`,
    [id, principal.tenantId],
  );
  const invoice = rows[0];
  if (!invoice) throw new NotFoundError();                 // 404: do not reveal other tenants' ids

  const decision = decide(principal, "invoice:update", invoice);
  audit({ principal: principal.id, action: "invoice:update", resource: id, ...decision });
  if (!decision.allow) throw new ForbiddenError(decision.reason);

  const { rowCount } = await db.query(                     // the write repeats the tenant predicate
    `UPDATE invoices SET amount = $3
      WHERE id = $1 AND tenant_id = $2 AND status <> 'paid'`,
    [id, principal.tenantId, amount],
  );
  if (rowCount === 0) throw new NotFoundError();
}
```

Function-level check declared on the route (Express 5; the object-level check stays in the service):

```ts
function requirePermission(permission: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const principal = req.principal;                       // set by the authentication middleware
    if (!principal || !permissionsFor(principal.roles).has(permission)) {
      return res.status(403).json({ error: "forbidden" });
    }
    next();
  };
}

router.patch("/invoices/:id", requirePermission("invoice:update"), async (req, res) => {
  await invoices.updateAmount(db, req.principal!, req.params.id, parseAmount(req.body));
  res.status(204).end();
});
```

Database layer: RLS policy and per-transaction tenant context are in [references/multi-tenancy.md](references/multi-tenancy.md); OpenFGA model and SDK calls are in [references/models-rbac-abac-rebac.md](references/models-rbac-abac-rebac.md); Rego and Cedar policies with tests are in [references/policy-engines.md](references/policy-engines.md).

## 15. Common Mistakes

- **Authorizing only in the UI or gateway**: direct API calls skip it. Enforce in the service that owns the data.
- **Authenticated equals authorized**: handlers that load `/orders/:id` for any logged-in user are BOLA. Check the object.
- **Tenant filter on reads only**: `UPDATE invoices SET ... WHERE id = $1` or `DELETE ... WHERE id = $1` lets one tenant change another's rows. Add `AND tenant_id = $2` and RLS with `WITH CHECK`.
- **Trusting `tenantId`, `role` or `ownerId` from the body, query or a header**: derive from the verified session and membership.
- **Checking role names in handlers** (`if (user.role === "admin")`): scattered, untestable, and hard to change. Use a permission check through the policy function.
- **Treating OAuth scopes as user permissions**: a valid `invoices:write` token still needs a per-object decision.
- **Allow-by-default engine wrappers**: `catch { return true }`, or treating an undefined OPA result as allowed. Fail closed.
- **Fetch then filter in memory**: pagination leaks counts and exposes data to code that forgets to filter. Filter in the query.
- **Session-level tenant setting on pooled connections**: leaks tenant context to the next request. Use `set_config(..., true)` inside a transaction.
- **Connecting as the table owner or a `BYPASSRLS` role**: RLS silently does nothing. Test with the runtime role.
- **Guessing safety from unguessable ids**: UUIDs reduce enumeration but a leaked id still works. Check access.
- **Mass assignment**: spreading `req.body` into an update lets callers set `role` or `tenant_id`. Allowlist fields.
- **Caching decisions without invalidation**: removed access stays effective. Short TTL and explicit invalidation.
- **Logging nothing about denials**: attacks look like normal 403 traffic. Log decisions with reasons and alert on bursts.

## 16. References

- [references/models-rbac-abac-rebac.md](references/models-rbac-abac-rebac.md): model comparison, RBAC and ABAC rules, OpenFGA and SpiceDB models and calls, field-level rules, scopes versus permissions, delegation.
- [references/policy-engines.md](references/policy-engines.md): OPA/Rego and Cedar policies with tests, engine comparison, where decisions run, decision logs, policy testing.
- [references/multi-tenancy.md](references/multi-tenancy.md): isolation strategies, tenant context, tenant predicates on every statement, PostgreSQL RLS with `USING` and `WITH CHECK`, pooled connections, isolation tests.
- Official docs: https://owasp.org/API-Security/editions/2023/en/0x11-t10/ , https://openfga.dev/docs , https://authzed.com/docs/spicedb , https://www.openpolicyagent.org/docs , https://docs.cedarpolicy.com , https://www.postgresql.org/docs/current/ddl-rowsecurity.html
