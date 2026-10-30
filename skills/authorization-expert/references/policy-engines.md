# Policy Engines: OPA, Cedar, OpenFGA, SpiceDB

Reference for externalizing authorization decisions into a policy engine and for deciding between engines and in-code policy functions. Verified against Open Policy Agent 1.22.x (Rego v1 syntax), Cedar 4.14.x (`cedar-policy` crate, `@cedar-policy/cedar-wasm`, `cedarpy`), OpenFGA 1.22.x and SpiceDB 1.57.x (2026-10).

## 1. Engine comparison

| Engine | Model | Policy language | Typical deployment | Best for |
|---|---|---|---|---|
| OPA | Policy as code over JSON input and data | Rego | Sidecar, library (Go, WASM), or central server; REST at `/v1/data/<path>` | Cross-cutting rules across services, Kubernetes and API gateway checks, attribute-heavy policies |
| Cedar | Principal, action, resource, context with entity hierarchy | Cedar (`permit`, `forbid`) | Embedded library (Rust, WASM, Python bindings) or Amazon Verified Permissions | Application authorization with analyzable policies and schema validation |
| OpenFGA | Relationship tuples plus a model | DSL (schema 1.1) | Service with Postgres or MySQL datastore | Sharing, nesting, large object graphs |
| SpiceDB | Relationship tuples plus a schema | Schema language (`.zed`) | Service with Postgres, CockroachDB, MySQL or Spanner | Zanzibar-style systems needing consistency tokens |

Rule of thumb: decisions that depend mostly on who is related to what go to a ReBAC engine; decisions that depend mostly on attributes and context go to OPA or Cedar; small services keep a pure policy function in code.

## 2. Open Policy Agent and Rego

OPA 1.0 and later use the v1 Rego syntax by default: rule bodies require `if`, multi-value rules use `contains`, and `import rego.v1` is no longer needed. Policy:

```rego
package app.authz

# Deny by default: every request is refused unless a rule below allows it.
default allow := false

role_permissions := {
	"viewer": {"invoice:read"},
	"editor": {"invoice:read", "invoice:update"},
	"admin": {"invoice:read", "invoice:update", "invoice:delete"},
}

allow if {
	not deny
	input.principal.tenant_id == input.resource.tenant_id
	some role in input.principal.roles
	input.action in role_permissions[role]
}

# Owners may always read their own invoices.
allow if {
	not deny
	input.principal.tenant_id == input.resource.tenant_id
	input.action == "invoice:read"
	input.resource.owner_id == input.principal.id
}

# An explicit deny overrides every allow rule above.
deny if input.principal.suspended == true
```

Why `deny` is a separate rule: writing `allow := false if ...` next to `allow if ...` raises `eval_conflict_error` when both fire, because a complete rule cannot produce two values.

Tests (`opa test .`):

```rego
package app.authz_test

import data.app.authz

editor := {"id": "u1", "tenant_id": "t1", "roles": ["editor"]}
invoice := {"tenant_id": "t1", "owner_id": "u9"}

test_editor_can_update if {
	authz.allow with input as {"principal": editor, "action": "invoice:update", "resource": invoice}
}

test_other_tenant_denied if {
	not authz.allow with input as {"principal": editor, "action": "invoice:read", "resource": {"tenant_id": "t2", "owner_id": "u1"}}
}

test_missing_input_denied if {
	not authz.allow with input as {}
}
```

Querying a running OPA server (`opa run --server`) is `POST /v1/data/app/authz/allow` with body `{"input": {...}}`; the response is `{"result": true}` or, if the rule is undefined, an empty object. Treat anything other than an explicit `true` as deny, and treat transport errors as deny (fail closed).

Operational notes:
- Run `opa check --strict` and `opa test` in CI; use `opa fmt` for formatting.
- Policies and data are loaded as bundles; version them and record the bundle revision in decision logs.
- OPA's decision logs can be shipped to a collector; mask sensitive fields in them.
- Keep input small: pass the attributes the policy needs, not whole database rows. Fetching extra data from inside policies (`http.send`) adds latency and failure modes; prefer pushing data to OPA or passing it as input.
- Partial evaluation can compile a policy into data-store filters for list queries; treat it as advanced and test the generated filters carefully.

## 3. Cedar

Cedar policies are `permit` or `forbid` statements over principal, action and resource with optional `when` and `unless` conditions. Evaluation is deny by default: a request is allowed only if at least one `permit` matches and no `forbid` matches (forbid overrides permit). Policies can be validated against a schema, and Cedar is designed so that policy analysis is decidable.

```cedar
// Editors can read and update invoices of their own tenant.
permit (
  principal in Role::"editor",
  action in [Action::"read", Action::"update"],
  resource is Invoice
) when { principal.tenantId == resource.tenantId };

// Owners can read their own invoices.
permit (
  principal is User,
  action == Action::"read",
  resource is Invoice
) when { resource.owner == principal && principal.tenantId == resource.tenantId };

// Suspended accounts are refused whatever else matches.
forbid (principal, action, resource) when { principal.suspended };
```

Python binding example (`cedarpy`), where `entities` carry the attributes and parent roles that the policies reference:

```python
import cedarpy

decision = cedarpy.is_authorized(
    {
        "principal": 'User::"u1"',
        "action": 'Action::"update"',
        "resource": 'Invoice::"i1"',
        "context": {},
    },
    policies,   # the policy text above
    entities,   # list of {"uid": {...}, "attrs": {...}, "parents": [...]}
)
allowed = decision.decision == cedarpy.Decision.Allow
```

Notes:
- Entities (users, roles, resources with attributes) are supplied with each request or loaded by the engine from your data; stale or missing attributes lead to wrong decisions, so build them from the system of record.
- Policy templates (`?principal`, `?resource` slots) model per-share grants.
- Amazon Verified Permissions is the managed service that stores Cedar policies and evaluates requests; check its current docs for quotas and the integration with identity providers.
- Run schema validation in CI before deploying a policy set.

## 4. Where the check runs

- Enforcement (a PEP: policy enforcement point) lives next to the resource: middleware, service layer or database. Decision (a PDP: policy decision point) can be local code, an embedded library or a remote engine.
- Centralize the decision logic and the policy data; keep enforcement local and explicit in each service. A gateway can reject obvious violations (missing scope, unauthenticated), but it does not know whether `invoice 42` belongs to the caller, so object-level checks stay in the service.
- If the engine is remote, define timeouts, a circuit breaker and the failure mode. For authorization the failure mode is deny, with a clear error and an alert. Cached positive decisions need a short TTL and must be invalidated on role or relationship changes.

## 5. Decision logging

Every decision record should have: timestamp, request or trace id, principal id and tenant, action, resource type and id, decision, reason or matching policy id, policy or model version, and engine latency. Never log tokens or full resource bodies. Log denials at a level that can be alerted on; a burst of denials for sequential object ids is an enumeration attempt.

## 6. Testing policies

- Table tests per policy: every role crossed with every action, with owner and non-owner, same tenant and other tenant.
- Negative tests are mandatory: missing input, unknown role, unknown action, null attributes, malformed ids.
- Property-style checks: adding a `forbid` or `deny` never turns a deny into an allow; removing a grant never widens access.
- Policy diff review: render a before and after matrix for each policy change and review the cells that flipped.
- Cedar and OPA policies can run in unit tests with no server; OpenFGA and SpiceDB tests need a running instance (Testcontainers modules exist for OpenFGA in Python; for others use the official Docker images) or use the engines' own model test formats (check the current docs of each).
