# OpenAPI and API Versioning

Authoring OpenAPI documents, linting and diffing them, and evolving an API with versions, deprecation and sunset. Verified against OpenAPI Specification 3.2.1 (latest on the releases page) and 3.1.2, RFC 9745 and RFC 8594 (2026-10). Tool versions seen on npm: @redocly/cli 2.72.1, @stoplight/spectral-cli 6.17.0.

## Contents
- Choosing 3.1 or 3.2
- Document skeleton
- Schema tips
- Security schemes
- Linting, diffing and codegen
- Versioning strategies
- What counts as breaking
- Deprecation and sunset

## Choosing 3.1 or 3.2

- 3.1 aligns schemas with JSON Schema 2020-12: `type: ["string", "null"]` instead of `nullable`, `examples` as an array, `$ref` with sibling keywords, `webhooks` at the top level, `const`, `unevaluatedProperties`.
- 3.2 (released after 3.1.x as a minor version) adds, per its release notes: the `query` operation for the HTTP QUERY method, `additionalOperations` for other methods, nested tags with `summary`, `parent` and `kind`, sequential media types for streaming (server-sent events, JSON Lines, `multipart/mixed`) described with `itemSchema`, and a top-level `$self` for base URI resolution.
- Choose the version your generators, linters, gateways and documentation tools all support; many toolchains lag the newest minor version. A 3.1 document remains a valid target; 3.0 needs `nullable` and a restricted schema dialect and is best left only for legacy tooling.
- Set `openapi:` to the exact version you validate against, and pin the validator version in CI.

## Document skeleton

```yaml
openapi: 3.1.0
info:
  title: Orders API
  version: 1.4.0            # contract version, not the URL major version
  license: { name: Apache-2.0, identifier: Apache-2.0 }
servers:
  - url: https://api.example.com
paths:
  /v1/orders:
    get:
      operationId: listOrders
      parameters:
        - { name: limit, in: query, schema: { type: integer, minimum: 1, maximum: 100, default: 25 } }
        - { name: cursor, in: query, schema: { type: string, maxLength: 200 } }
      responses:
        "200":
          description: A page of orders
          content:
            application/json:
              schema: { $ref: "#/components/schemas/OrderPage" }
        "default": { $ref: "#/components/responses/Problem" }
      security: [{ bearerAuth: [] }]
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
  responses:
    Problem:
      description: Error
      content:
        application/problem+json:
          schema: { $ref: "#/components/schemas/Problem" }
  schemas:
    Problem:
      type: object
      required: [type, title, status]
      properties:
        type: { type: string, format: uri-reference }
        title: { type: string }
        status: { type: integer }
        detail: { type: string }
        instance: { type: string, format: uri-reference }
      additionalProperties: true
    OrderPage:
      type: object
      required: [data, next_cursor]
      properties:
        data: { type: array, items: { $ref: "#/components/schemas/Order" } }
        next_cursor: { type: ["string", "null"] }
    Order:
      type: object
      required: [id, status, total_cents, version]
      properties:
        id: { type: string, format: uuid, readOnly: true }
        status: { type: string, enum: [open, paid, cancelled] }
        total_cents: { type: integer, minimum: 0 }
        version: { type: integer, readOnly: true }
```

## Schema tips

- Set `additionalProperties: false` (or `unevaluatedProperties: false`) on request bodies to document strict validation; leave response objects open for additive evolution, and tell clients to ignore unknown fields.
- Use `readOnly` and `writeOnly` for server-managed and secret fields; keep separate request and response schemas when shapes differ (`OrderCreate`, `Order`).
- Reuse via `components`; avoid deep `allOf` chains that generators handle badly. Use `oneOf` with a `discriminator` for polymorphism.
- Declare `maxLength`, `maxItems`, `minimum`, `maximum` and patterns; they feed validation, fuzzing and documentation.
- Enums are part of the contract: adding a value can break clients with exhaustive switches. Document that clients must tolerate unknown enum values for response fields.
- Describe response headers (`ETag`, `Location`, `Retry-After`, `Deprecation`, `Sunset`) so clients and mocks know about them.
- Add examples to every schema and operation; they power docs, mocks and contract tests.
- Webhooks (3.1+): describe outgoing callbacks under `webhooks`; see api-security-expert for signature verification.

## Security schemes

- `http` with `scheme: bearer` for access tokens; `oauth2` flows for delegated access with scopes per operation; `apiKey` in a header for application identification (never in the query string); `mutualTLS` for service-to-service; `openIdConnect` for discovery.
- Apply `security` globally and override per operation; mark public operations with `security: []` explicitly so review can spot them.
- The document describes authentication; enforcement and tenant scoping live in code and are tested separately.

## Linting, diffing and codegen

- Lint in CI with Redocly CLI (`npx @redocly/cli lint openapi/openapi.yaml`) or Spectral (`npx @stoplight/spectral-cli lint openapi/openapi.yaml`) using a committed ruleset; fail on errors.
- Detect breaking changes by diffing against the last released document (for example the `oasdiff` tool or Redocly's change detection); check the tool's current docs for flags.
- Generate server stubs, typed clients or Zod/JSON Schema validators from the document, or generate the document from code; pick one source of truth and enforce it with a CI check that regenerated output is unchanged.
- Do not hand-edit generated files; do not publish generated clients with credentials baked in.
- Serve the document and rendered docs without enabling "try it out" against production by default.

## Versioning strategies

| Strategy | Example | Trade-offs |
|---|---|---|
| URL major version | `/v1/orders` | Visible, easy to route and cache; two live contracts to maintain |
| Media type version | `Accept: application/vnd.example.v2+json` | Clean URLs; harder to test and cache, needs `Vary: Accept` |
| Date-based version header | custom header with a date | Fine-grained pinning per client; you design and document the header |
| No version, additive only | none | Simplest; requires strict discipline and tolerant clients |

Guidance:
- Prefer additive change; version only for breaking ones. Use major versions only (`v1`, `v2`), not minor in the URL.
- Keep the contract version (`info.version`, semantic versioning) separate from the URL version.
- Every supported version has its own OpenAPI document, tests and deprecation date.
- Do not use query parameters for versioning; they fragment caches and are easy to omit.

## What counts as breaking

Breaking for consumers:
- Removing or renaming a field, path, operation, enum value in a request, or a response status/media type.
- Changing a field's type, format, nullability or meaning; changing defaults or ordering guarantees.
- Adding a new required request field or parameter; tightening validation (lengths, patterns, ranges).
- Changing authentication or authorization requirements; changing error `type` URIs clients match on.
- Changing pagination or sort defaults, or the meaning of cursors.

Usually non-breaking:
- Adding optional request fields or parameters, new response fields, new operations, new optional response headers.
- Adding enum values to responses only if clients are documented to tolerate them.

## Deprecation and sunset

- Mark the operation or field `deprecated: true` in OpenAPI and describe the replacement.
- At runtime, send on every response from the deprecated resource:
  - `Deprecation: @1788134400` (RFC 9745: an RFC 9651 structured-field Date, `@` plus Unix seconds, giving when the deprecation takes or took effect).
  - `Sunset: Wed, 30 Jun 2027 23:59:59 GMT` (RFC 8594: HTTP date when the resource is expected to stop responding; not earlier than the deprecation time).
  - `Link: <https://developer.example.com/migrate-v2>; rel="deprecation"; type="text/html"` pointing to migration documentation, and optionally `rel="sunset"` for the sunset policy.
- After the sunset date return `410 Gone` with Problem Details linking to the migration guide, rather than silently changing behavior.
- Track traffic by version and by client credential to notify the remaining callers before the date; announce through documentation, changelog and direct contact for large consumers.
- Allow a documented minimum overlap period (set by policy, for example six months or longer for enterprise clients) between announcement and removal.
