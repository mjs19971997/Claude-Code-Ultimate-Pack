# Access Control Models: RBAC, ABAC, ReBAC

Reference for choosing and implementing an authorization model, with OpenFGA and SpiceDB examples for relationship-based access control. Verified against OpenFGA 1.22.x (JS SDK `@openfga/sdk` 0.9.x), SpiceDB 1.57.x, `@casl/ability` 7.1.x and the OWASP API Security Top 10 2023 (2026-10).

## 1. Choosing a model

| Model | Question it answers | Fits | Breaks down when |
|---|---|---|---|
| ACL | Is this user on this object's list? | Few objects, manual sharing | Many objects, inherited access |
| RBAC | Does the user hold a role that grants the action? | Back-office tools, fixed job functions, coarse feature access | Per-object access, "owner" rules, role explosion (one role per team per project) |
| ABAC | Do attributes of user, resource, action and environment satisfy a rule? | Rules such as "same department and amount below limit", time or device conditions | Rules scattered across code, attributes not reliably available at decision time |
| ReBAC | Is there a path of relationships from user to object? | Sharing, folders and nesting, teams and organizations, "viewer of parent is viewer of child" | Purely numeric or contextual rules (combine with conditions or ABAC) |

Most products end up hybrid: RBAC for coarse capabilities, ownership or relationship checks for objects, attribute rules for exceptions. Keep one decision point per resource type so the mix stays readable.

## 2. RBAC

- A role is a named set of permissions; permissions are `resource:action` strings (`invoice:update`). Check permissions in code, never role names, so roles can change without code changes.
- Scope roles. A global `admin` flag is rarely right; store the role together with its scope: `(user_id, role, tenant_id)` or `(user_id, role, project_id)`.
- Keep role-to-permission mapping in data or a versioned policy file, not scattered `if (role === ...)` checks.
- Role hierarchies (`admin` includes `editor` includes `viewer`) are flattened at load time or modeled as permission supersets; avoid cycles.
- Role explosion is the signal to move per-object access into ReBAC or attributes.

```sql
CREATE TABLE memberships (
  user_id    uuid NOT NULL,
  tenant_id  uuid NOT NULL,
  role       text NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
  PRIMARY KEY (user_id, tenant_id, role)
);
```

## 3. ABAC

- Subject attributes (department, clearance, suspended), resource attributes (owner, status, sensitivity, tenant), action, and environment (time, network, device posture).
- Treat attributes used for decisions as security data: load them from the system of record on the server, never from request bodies or client-supplied claims that the user can edit.
- Write rules as pure functions of `(principal, action, resource, context)`; this makes them testable with tables and loggable as a decision with a reason.
- Deny rules need explicit precedence. A common convention: any matching deny wins over any allow; otherwise a single allow is enough; otherwise deny.

## 4. ReBAC and Zanzibar style systems

Google's Zanzibar paper (2019) describes storing relationships as tuples `object#relation@subject` and computing permissions by walking them. OpenFGA and SpiceDB implement this model. Both keep the relationship store separate from your application database, so it must be kept in sync (write tuples in the same flow that creates, shares or deletes the object, and handle failure with an outbox or retry).

### OpenFGA (v1.22.x)

Model in the DSL (schema 1.1):

```
model
  schema 1.1

type user

type organization
  relations
    define member: [user]
    define admin: [user]

type folder
  relations
    define organization: [organization]
    define parent: [folder]
    define owner: [user]
    define editor: [user, organization#member] or owner or editor from parent
    define viewer: [user, user:*, organization#member] or editor or viewer from parent
    define can_delete: owner or admin from organization

type document
  relations
    define parent: [folder]
    define owner: [user]
    define editor: [user, organization#member] or owner
    define viewer: [user, organization#member] or editor or viewer from parent
    define can_view: viewer
    define can_edit: editor or editor from parent
    define can_delete: owner
```

Tuples (written through the Write API) look like `user:anne owner document:roadmap` and `folder:q3 parent document:roadmap`. Calling the API from Node:

```ts
import { OpenFgaClient } from "@openfga/sdk";

// Create the client once and reuse it: it keeps connections and credentials.
export const fga = new OpenFgaClient({
  apiUrl: process.env.FGA_API_URL!,
  storeId: process.env.FGA_STORE_ID!,
  authorizationModelId: process.env.FGA_MODEL_ID, // pin the model version in production
});

export async function canEdit(userId: string, documentId: string): Promise<boolean> {
  const { allowed } = await fga.check({
    user: `user:${userId}`,
    relation: "can_edit",
    object: `document:${documentId}`,
  });
  return allowed === true; // anything else, including errors, is a deny
}

// List endpoints: ask which objects the user may see, then query your database with that id list.
export async function viewableDocumentIds(userId: string): Promise<string[]> {
  const { objects } = await fga.listObjects({
    user: `user:${userId}`,
    relation: "can_view",
    type: "document",
  });
  return objects.map((o) => o.replace(/^document:/, ""));
}
```

Notes from the docs and SDK:
- `batchCheck` runs many checks in one call; result order is not guaranteed, so pair responses with requests via `correlationId`.
- Consistency can be requested per call (`MINIMIZE_LATENCY` default, `HIGHER_CONSISTENCY` for read-after-write).
- Contextual tuples let a request supply temporary relationships; they are evaluated only for that call and are not stored.
- Conditions (CEL expressions attached to a relation) add attribute checks to tuples.
- `ListObjects` has result and time limits; for very large result sets prefer checking per row or per page, or use a data-filtering pattern. Check the current docs for limits.

### SpiceDB (v1.57.x)

```zed
definition user {}

definition organization {
    relation admin: user
    relation member: user
    permission manage = admin
    permission view = admin + member
}

definition document {
    relation org: organization
    relation owner: user
    relation editor: user
    relation viewer: user | user:*
    permission edit = owner + editor + org->admin
    permission view = viewer + edit + org->member
    permission delete = owner
}
```

- Permissions are computed with `+` (union), `&` (intersection), `-` (exclusion) and `->` (arrow: follow a relation, then evaluate a permission on the target).
- Every request can choose a consistency level: `minimize_latency`, `at_least_as_fresh` (with a ZedToken), `at_exact_snapshot`, or `fully_consistent`. Store the ZedToken returned by a write next to the object and send it with later checks to avoid the "new enemy problem" (checking with a stale snapshot after access was revoked). `WriteRelationships` and `DeleteRelationships` default to `fully_consistent`; most other calls default to `minimize_latency`.
- API calls to use: `CheckPermission`, `LookupResources` (which objects), `LookupSubjects` (who can), `WriteRelationships`, `ExpandPermissionTree` for debugging.
- Caveats attach CEL conditions to relationships for attribute rules.

### In-process alternative

For a single JavaScript service where a separate authorization service is excessive, `@casl/ability` (7.1.x) builds an ability object per request from the user's grants and checks `ability.can('update', subject('Invoice', invoice))`. It can also translate rules to query conditions through adapters; verify the adapter for your ORM in its docs.

## 5. Field level authorization BOPLA

OWASP API3:2023 Broken Object Property Level Authorization covers two failures: returning properties the caller may not see (excessive data exposure) and accepting properties the caller may not set (mass assignment).

- Use explicit response DTOs or serializers per audience; never serialize the database row.
- Use explicit input allowlists (schema validation that rejects unknown keys); fields such as `role`, `tenant_id`, `owner_id`, `is_admin`, `status`, `price` are server-controlled unless a rule says otherwise.
- For field-level rules that depend on the viewer (salary visible to HR), apply the same policy function with `action = "employee:read:salary"`.

## 6. OAuth scopes are not permissions

- A scope limits what a client (token) may do on behalf of a user. It does not say what the user may do.
- Effective access is the intersection: the token must carry the scope for the endpoint AND the user must hold the permission for the specific object.
- A token with `invoices:write` still gets a 403 or 404 on an invoice in another tenant or one the user cannot edit.
- Machine-to-machine tokens (client credentials) have no user: model the client itself as a principal with its own permissions, scoped to a tenant where applicable.
- Do not copy user roles into long-lived token claims and trust them until expiry for sensitive actions; either keep tokens short-lived or look up current grants on the server for high-risk operations. Token issuance and validation belong to authentication-expert.

## 7. Delegation impersonation and break glass

- Support access on behalf of another user as an explicit concept: record both `actor` and `subject` in the audit log, restrict who may impersonate, and exclude sensitive actions (changing credentials, exporting data) unless approved.
- Time-box elevated access (just-in-time roles with expiry) instead of permanent admin grants.
- Break-glass access needs a reason, an alert and a review trail.
