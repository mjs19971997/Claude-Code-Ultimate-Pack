---
name: graphql-expert
description: >-
  Designs, secures and tunes GraphQL APIs on graphql-js 17 (and 16), Apollo Server 5, GraphQL Yoga 6 and Apollo Federation 2: schema design (nullability, Relay connections, input types, mutation payloads, errors as data with union results), resolvers, DataLoader batching against N+1, persisted operations and trusted documents, depth and cost limits, introspection policy, field-level authorization in the business layer, federation subgraphs, subscriptions over graphql-ws, and code generation. Use when writing or reviewing a GraphQL schema or resolvers, diagnosing slow queries, hardening a public GraphQL endpoint, or choosing a server. Not for REST contract design (use rest-api-expert) or general API threat modeling beyond GraphQL (use api-security-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# GraphQL Expert

This skill covers building GraphQL services end to end: schema modeling, resolver and loader structure, error design, abuse protection, authorization placement, federation, subscriptions and tooling. It is organized around the GraphQL specification and the JavaScript server stacks. NestJS hosting details live in nestjs-expert.

> Verified against the GraphQL specification September 2025 Edition (latest published edition; later work is the Working Draft), graphql-js 17.0.2 and 16.14.2, Apollo Server 5.5.1, GraphQL Yoga 6.0.1, `@apollo/subgraph` 2.15.1 (federation spec up to v2.15), Apollo Router 2.19, graphql-ws 6.4.1, DataLoader 2.2.3, `@graphql-codegen/cli` 7.4 (2026-10).

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

- Covered: SDL design, resolvers and context, DataLoader, pagination, mutations and errors, input validation, persisted operations, query cost and depth control, introspection policy, authorization, Apollo Federation 2 subgraphs and routers, subscriptions, schema evolution, codegen, GraphQL testing and observability.
- Not covered: REST design (rest-api-expert), cross-protocol API security (api-security-expert), authentication mechanics such as OAuth and sessions (authentication-expert), NestJS module wiring (nestjs-expert), database schema design (postgresql-expert, prisma-expert), React client patterns (senior-react-19-engineer).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Specification | The September 2025 Edition is the current release. It includes `@oneOf` input objects, `@specifiedBy`, `@deprecated` on arguments and input fields, and the "request error" versus "execution error" terminology. `@defer` and `@stream` are not in it |
| graphql-js 17 | Released 2026-06; needs Node 22, 24, 25 or 26+; uses package `exports` (import from `graphql` or documented subpaths); `ExecutionArgs.abortSignal`, `info.getAbortSignal()`, `hideSuggestions`; `variableValues` in `info` carries `coerced` values; `graphql:*` TracingChannel diagnostics; incremental delivery via `experimentalExecuteIncrementally` (experimental) |
| Server peers | Yoga 6 accepts graphql 16 or 17 (Node 22.15+). Apollo Server 5.5 declares graphql 16.11+ only (Node 20+), as do `@apollo/subgraph` 2.15 and `@apollo/gateway` 2.14; an Apollo Server project stays on graphql 16 until that changes. `@graphql-tools/schema` 11, `graphql-ws` 6, `graphql-query-complexity` 2 and `@pothos/core` 4 accept both |
| Apollo Server 5 | `introspection` defaults to on outside production and off when `NODE_ENV=production`; CSRF prevention on; `status400ForVariableCoercionErrors` true; `includeStacktraceInErrorResponses` for development; `hideSchemaDetailsFromClientErrors`; opt-in `maxRecursiveSelections`; Express integration is the separate `@as-integrations/express5` (or `express4`) package |
| GraphQL Yoga 6 | Fetch-API based; `maskedErrors` on by default; plugins `@graphql-yoga/plugin-persisted-operations`, `-disable-introspection`, `-csrf-prevention`, `-response-cache`; SSE subscriptions built in; Envelop plugin model |
| Federation 2 | Subgraphs declare `@link` to a federation spec version and use `@key`, `@shareable`, `@external`, `@requires`, `@provides`, `@override`, `@inaccessible`, `@interfaceObject`; Apollo Router 2.x (Rust) composes and serves the supergraph; `@apollo/subgraph` builds subgraph schemas |
| Subscriptions | Use the `graphql-ws` protocol (`graphql-ws` 6.x server and client). `subscriptions-transport-ws` is unmaintained and deprecated on npm |
| Persisted operations | Allowlisted documents identified by hash or id (trusted documents) block arbitrary queries; Automatic Persisted Queries (APQ) only save bandwidth and do not restrict operations |
| Codegen | `@graphql-codegen/cli` with `client-preset` for typed documents (supports persisted documents) and `typescript-resolvers` for resolver types |

## 3. Workflow

1. Gather the consumers and use cases; list the entities and the relationships clients traverse.
2. Draft the schema in SDL first; review names, nullability, pagination and error shapes before writing resolvers.
3. Choose the server stack from the peer constraints above (graphql version, Node version, subscriptions, federation).
4. Build resolvers thin: parse arguments, call a service with the viewer from context, return data. Create DataLoaders per request.
5. Add protections before exposure: depth and cost limits, body size limit, persisted operations or allowlist for first-party clients, introspection policy, masked errors.
6. Add observability: operation name, duration, error codes, resolver timings, trace context.
7. Generate types from the schema and operations; fail CI on breaking schema changes (schema diff or registry check).
8. Load test with realistic queries; verify the number of database queries per operation.

## 4. Decision Rules

- Nullability: make a field non-null only if it can never fail independently of its parent. A failure in a non-null field nulls the nearest nullable ancestor, so a non-null field backed by a flaky remote call widens the blast radius.
- Lists: `[Item!]!` for lists that are always present with no null items; prefer connections for anything that can grow.
- Pagination: cursor connections (`edges`, `node`, `cursor`, `pageInfo`) for unbounded lists; simple `[Item!]!` with a hard limit only for small bounded sets. Offset pagination is acceptable only for small, stable data.
- Errors: unexpected failures (bugs, outages, authentication) go to the top-level `errors`; expected business outcomes (validation, conflict, not found by user input, insufficient funds) are returned as data, either a union result type or a `userErrors` field on a payload.
- Union results versus `userErrors`: unions give exhaustive typing and let each error carry its own fields; `userErrors` is simpler for form validation. Choose one convention per schema.
- Input: one `input` argument per mutation; use `@oneOf` input objects for "exactly one of" (look up by `id` or `email`); use enums for closed sets and custom scalars (with `@specifiedBy`) for dates, URLs and money.
- Query cost: static depth limit for all deployments; cost analysis when lists multiply (first/limit arguments); persisted operations when all clients are first-party.
- Introspection off in production is defense in depth: it removes a convenience for attackers, not a protection. Authorization, cost limits and field suggestion hiding do the actual work.
- Server: Yoga for Fetch-API runtimes, graphql 17 and built-in subscriptions; Apollo Server 5 for Apollo's ecosystem and GraphOS federation, on graphql 16.
- Federation when several teams own parts of one graph; a single schema with modules otherwise. See microservices-expert for service boundaries.
- Subscriptions only for real push needs; polling or SSE through a normal query may be simpler. Use `graphql-ws`, authenticate at connection and per operation.
- Rate limiting by operation cost or by identity, not only per HTTP request, since one request can carry batched or aliased operations.

## 5. Coding Standards

- SDL names: types `PascalCase`, fields and arguments `camelCase`, enum values `SCREAMING_SNAKE_CASE`, mutation fields as verbs (`createPost`, `publishPost`), inputs `CreatePostInput`, payloads `CreatePostPayload`.
- Every type, field and argument that is not obvious has a description string. Use `@deprecated(reason: "Use X")` instead of removing.
- IDs are opaque strings (`ID`); never expose internal sequential database ids as the only identity if enumeration matters.
- Resolver signature `(parent, args, context, info)`; never mutate `parent` or `args`; keep side effects in mutations only.
- Context is created per request: viewer identity, loaders, services, request id, and an `AbortSignal`. Never cache context across requests.
- Throw `GraphQLError` with `extensions.code` (`UNAUTHENTICATED`, `FORBIDDEN`, `BAD_USER_INPUT`, `NOT_FOUND`) for expected top-level errors; do not leak internals.
- Do not write resolvers for plain property reads; rely on default resolvers.
- Use generated resolver types; run schema lint (`@graphql-eslint/eslint-plugin`) in CI.

## 6. Project Structure

```
.
├── schema/
│   ├── schema.graphql            # or one file per domain: user.graphql, post.graphql
│   └── persisted-documents.json  # generated allowlist for first-party clients
├── src/
│   ├── server.ts                 # server factory: schema, plugins, limits
│   ├── context.ts                # per-request context: viewer, loaders, services
│   ├── resolvers/
│   │   ├── query.ts
│   │   ├── mutation.ts
│   │   └── post.ts               # type resolvers (field resolvers)
│   ├── loaders/                  # DataLoader factories, one per access pattern
│   ├── services/                 # business logic and authorization
│   ├── security/                 # depth rule, cost estimator, error masking
│   └── generated/                # codegen output (resolver types)
├── codegen.ts
└── test/                         # executes operations against the schema
```

## 7. Design Patterns

- **Mutation payloads**: `type CreatePostPayload { post: Post userErrors: [UserError!]! }` or a union `CreatePostResult = CreatePostSuccess | ValidationError | NotAuthorized`.
- **Relay connections**: `PostConnection { edges: [PostEdge!]! pageInfo: PageInfo! }`; opaque base64url cursors; fetch `first + 1` rows to compute `hasNextPage`; cap `first`.
- **DataLoader per request**: a factory returns a new set of loaders for each request; batch functions return results in key order and `Error` instances for per-key failures.
- **Viewer-aware loaders**: keys include what the authorization decision depends on, or the batch query itself applies the viewer's scope.
- **Node interface** with a global `node(id: ID!)` lookup when clients need refetching; implement only if used.
- **Entity references in federation**: `@key` entities with `__resolveReference` backed by a loader.
- **Unions and interfaces** for polymorphic results (`SearchResult = Post | User`), resolved with `__resolveType` or `isTypeOf`.
- **Errors as data**: expected failures are typed so clients branch with `__typename` rather than parsing messages.
- **Persisted operations**: build step extracts documents, stores hash to document, server maps the id.

## 8. Best Practices

- Evolve the schema additively: add fields, add optional arguments, deprecate before removal, and avoid changing nullability of output fields from non-null to nullable without a migration plan. Adding an enum value can break clients with exhaustive handling.
- Keep mutations coarse-grained and domain-named; avoid generic `update(input: JSON)`.
- Prefer specific types over `JSON` scalars; if you add custom scalars, validate and serialize strictly.
- Return the changed object from mutations so clients can update caches.
- Make list ordering deterministic (stable sort key plus tie-breaker) so cursors are stable.
- Name every operation on the client; operation names feed logs, metrics and persisted documents.
- Treat the supergraph schema as a contract: run composition checks and client-usage checks before deploy.
- Use `@defer` and `@stream` only after confirming server, router and client support; they are not in the September 2025 specification edition.

## 9. Performance

- N+1: each list-item field resolver that hits storage needs a DataLoader or a join in the parent query. Verify with query logging that a nested query issues a constant number of statements per level.
- DataLoader caches per instance: creating it at module level leaks data between users and requests. Create in the context factory.
- Batch functions must return exactly one result per key in the same order; map by key rather than relying on database row order.
- Look ahead only when profiling shows loaders are insufficient: use `info` to select only needed columns; avoid generic field-by-field projection libraries without limits.
- Use `info.getAbortSignal()` (graphql-js 17) or an abort signal in context to cancel downstream queries when the client disconnects or the operation times out.
- Cap page sizes, alias counts and query depth; bound batching of operations in one HTTP request.
- Cache at the right layer: HTTP caching for persisted GET queries, response cache plugins for public data, per-field `@cacheControl` hints in Apollo, and application caches behind loaders. Never share cached responses across viewers when results depend on the viewer.
- Prefer persisted operations: smaller requests, precomputed validation, and a fixed set of query shapes to load test.
- Details: [references/performance-and-security.md](references/performance-and-security.md).

## 10. Security

- **Authorization belongs in the business layer.** Resolvers call services that take the viewer and enforce access for each object and each field; a gateway check or an `@auth` directive on the route is not enough because the same object is reachable through many paths. Apply the same checks to loaders (a loader that fetches by id without the viewer's scope bypasses them).
- Authorize writes as strictly as reads. A tenant or owner condition must be part of every read query and every update and delete query, not only list queries.
- Field-level rules: sensitive fields (`email`, `phone`, `role`, pricing) check the viewer in the service or in a field resolver; return `null` for nullable fields or an authorization error depending on the schema contract. Use the same code path for all entry points (queries, mutations, subscriptions, federation entity resolvers).
- **Introspection**: disable in production (`introspection: false`, Apollo does so when `NODE_ENV=production`; Yoga `useDisableIntrospection`) but do not rely on it. Also hide "Did you mean" suggestions (Apollo `hideSchemaDetailsFromClientErrors`, graphql-js `hideSuggestions`, or a block-suggestions plugin), because suggestions reveal schema names.
- **Abuse limits**: maximum body size, maximum depth, query cost, alias and directive counts, token limit, per-identity rate limit, timeouts. Batching and aliases multiply cost inside one request.
- **Persisted operations (trusted documents)**: when all clients are first-party, reject arbitrary documents in production. APQ does not provide this protection.
- **CSRF**: Apollo Server 5 has CSRF prevention on by default (requests must be of a kind browsers preflight, such as `application/json` or carrying a custom header); keep it. Yoga offers `@graphql-yoga/plugin-csrf-prevention`. GET requests must not run mutations.
- **Errors**: mask unexpected errors (Yoga `maskedErrors`, Apollo `formatError`); never return stack traces or SQL in production; log the original with the request id.
- **Input validation**: validate lengths and formats in services; custom scalars reject malformed values; bound list inputs.
- **Subscriptions**: authenticate in `onConnect` or context with the connection parameters, re-check authorization on each event for long-lived streams, and limit subscriptions per connection.
- **Federation**: subgraphs must not be reachable except from the router; authenticate router to subgraph; repeat authorization in subgraphs because they trust only validated input; keep `_entities` and `_service` unreachable from public networks.
- **Query logging**: do not log variables containing secrets; redact.
- Wider topics: api-security-expert and authorization-expert.

## 11. Testing

- Execute operations against the schema without HTTP: `graphql({ schema, source, contextValue, variableValues })`, `yoga.fetch(...)`, or Apollo's `server.executeOperation()`. Assert on `data` and `errors[].extensions.code`.
- Unit test services and loaders directly; integration test resolvers with a real database transaction.
- Assert query counts: wrap the data layer and verify a nested list query does not scale with list length.
- Test authorization for each role, including cross-tenant ids, on queries, mutations, subscriptions and nested fields.
- Contract tests: schema snapshot or `graphql-inspector`-style diff checks block breaking changes; for federation, run composition in CI.
- Test limits: send an over-deep query, an alias flood and an oversized body; assert rejection and status codes.
- Use `@graphql-tools/mock` or generated factories for client tests.

## 12. Review Checklist

- [ ] Every list is paginated with an enforced maximum; connection cursors are opaque and stable.
- [ ] Nullability reflects failure modes; remote-backed fields are nullable.
- [ ] Mutations take one `input` and return a payload or union; expected errors are data.
- [ ] No resolver issues a query per parent item without a loader; loaders are created per request.
- [ ] Authorization is enforced in services and loaders for reads and writes, including tenant filters on updates and deletes.
- [ ] Depth, cost, body size, alias and rate limits are configured; timeouts exist.
- [ ] Production introspection is off and suggestions are hidden; unexpected errors are masked.
- [ ] Arbitrary documents are blocked in production when clients are first-party.
- [ ] Subscriptions use `graphql-ws` with authentication and per-event authorization.
- [ ] Schema changes are additive or deprecated first; CI checks breaking changes.
- [ ] Types are generated; the lint step passes.
- [ ] Logs carry operation name, request id and error codes without secrets.

## 13. Production Notes

- Version choices: pin graphql to one copy (`npm ls graphql`); duplicate copies cause "Cannot use GraphQLSchema from another module or realm" errors. Plugins built for graphql 16 may misbehave on 17 (for example `graphql-armor` packages install their own graphql 16); check peer ranges.
- Apollo Server 5 does not ship Express middleware; install `@as-integrations/express5`, add `express.json({ limit })` before it, and drain the HTTP server with `ApolloServerPluginDrainHttpServer`.
- Router: put Apollo Router (or Hive Gateway) in front of subgraphs; configure timeouts, query planning cache, introspection and persisted queries at the router.
- Observe: expose metrics per operation name and error code; trace with OpenTelemetry; graphql-js 17 publishes `graphql:parse`, `graphql:validate`, `graphql:execute` and `graphql:resolve` events on `node:diagnostics_channel` for APM tools.
- Rollout: deploy schema additions first, clients second, removals last after usage reaches zero.
- WebSocket gateways and load balancers need sticky behavior only for connection lifetime; set idle timeouts above the ping interval.
- Subscription fan-out needs a pub/sub backend (Redis, Kafka, NATS) shared by all instances.

## 14. Examples

Schema fragment with a connection, a `@oneOf` lookup and errors as data:

```graphql
type Query {
  me: User
  user(by: UserBy!): User
  posts(first: Int! = 20, after: String): PostConnection!
}

input UserBy @oneOf {
  id: ID
  email: String
}

type Mutation {
  createPost(input: CreatePostInput!): CreatePostResult!
}

input CreatePostInput {
  title: String!
  body: String!
}

union CreatePostResult = CreatePostSuccess | ValidationError | NotAuthorized

type CreatePostSuccess { post: Post! }
type ValidationError { field: String!, message: String! }
type NotAuthorized { message: String! }

type Post {
  id: ID!
  title: String!
  author: User!
}

type User {
  id: ID!
  name: String!
  "Visible to the user and to staff."
  email: String
}

type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
}
type PostEdge { cursor: String!, node: Post! }
type PageInfo { hasNextPage: Boolean!, endCursor: String }
```

Yoga server on graphql 17 with per-request loaders, service-level authorization, a depth rule and production introspection policy (run with `node --import` TypeScript support or compile):

```ts
import { createServer } from 'node:http';
import { createSchema, createYoga, type Plugin } from 'graphql-yoga';
import { useDisableIntrospection } from '@graphql-yoga/plugin-disable-introspection';
import DataLoader from 'dataloader';
import { typeDefs } from './schema.js';
import { maxDepthRule } from './security/max-depth.js';
import { services } from './services.js';

interface Context {
  viewer: { id: string; roles: string[] } | null;
  authorLoader: DataLoader<string, { id: string; name: string }>;
}

const depthLimit: Plugin = {
  onValidate({ addValidationRule }) {
    addValidationRule(maxDepthRule(8));
  },
};

const yoga = createYoga<Record<string, never>, Context>({
  schema: createSchema({
    typeDefs,
    resolvers: {
      Query: {
        posts: (_, { first, after }, ctx) => services.posts.page(ctx.viewer, { first: Math.min(first, 50), after }),
      },
      Post: {
        author: (post, _args, ctx) => ctx.authorLoader.load(post.authorId),
      },
      User: {
        // field-level rule enforced by the service, not by the route or gateway
        email: (user, _args, ctx) => services.users.visibleEmail(ctx.viewer, user),
      },
    },
  }),
  context: async ({ request }) => {
    const viewer = await services.auth.viewerFromHeader(request.headers.get('authorization'));
    return {
      viewer,
      // created per request; the batch query applies the viewer's scope
      authorLoader: new DataLoader((ids) => services.users.byIds(viewer, ids)),
    };
  },
  plugins: [
    depthLimit,
    ...(process.env.NODE_ENV === 'production' ? [useDisableIntrospection()] : []),
  ],
  maskedErrors: true, // default; unexpected errors become "Unexpected error."
  graphiql: process.env.NODE_ENV !== 'production',
});

createServer(yoga).listen(4000);
```

Validation rule that limits operation depth (works with graphql 16 and 17; fragments are followed):

```ts
import { GraphQLError, Kind, type ASTVisitor, type SelectionSetNode, type ValidationContext } from 'graphql';

export function maxDepthRule(max: number) {
  return (context: ValidationContext): ASTVisitor => {
    const fragments = new Map<string, SelectionSetNode>();
    for (const def of context.getDocument().definitions) {
      if (def.kind === Kind.FRAGMENT_DEFINITION) fragments.set(def.name.value, def.selectionSet);
    }
    const memo = new Map<string, number>();
    const depthOf = (set: SelectionSetNode | undefined, seen: Set<string>): number => {
      let deepest = 0;
      for (const sel of set?.selections ?? []) {
        let d = 0;
        if (sel.kind === Kind.FIELD) {
          if (sel.name.value.startsWith('__')) continue;
          d = 1 + depthOf(sel.selectionSet, seen);
        } else if (sel.kind === Kind.INLINE_FRAGMENT) {
          d = depthOf(sel.selectionSet, seen);
        } else if (!seen.has(sel.name.value)) {
          if (!memo.has(sel.name.value)) {
            memo.set(sel.name.value, depthOf(fragments.get(sel.name.value), new Set([...seen, sel.name.value])));
          }
          d = memo.get(sel.name.value)!;
        }
        deepest = Math.max(deepest, d);
      }
      return deepest;
    };
    return {
      OperationDefinition(node) {
        const depth = depthOf(node.selectionSet, new Set());
        if (depth > max) {
          context.reportError(new GraphQLError(`Operation depth ${depth} exceeds the limit of ${max}`, { nodes: [node] }));
        }
      },
    };
  };
}
```

## 15. Common Mistakes

- **Unbounded lists** (`users: [User!]!` with no pagination): memory and latency grow with data. Use connections and a maximum page size.
- **N+1 queries**: a field resolver that queries per parent. Use a DataLoader or a join.
- **Module-level DataLoader**: caches across users and requests; data leaks and staleness. Create per request.
- **Batch function returns rows in database order**: results get matched to wrong keys. Map by key and return in key order.
- **Mutations returning `Boolean`**: clients cannot update caches. Return the object or a payload.
- **Business errors as top-level errors**: clients must parse messages. Use union results or `userErrors`.
- **Non-null everywhere**: one failed field nulls a large part of the response. Reserve `!` for guaranteed fields.
- **Authorization only at the gateway or route**: other paths to the same object are unprotected. Enforce in services and loaders, for reads and writes.
- **Tenant filter only on list queries**: updates and deletes by id can cross tenants. Scope every query.
- **Introspection off treated as security**: field suggestions and leaked clients still reveal the schema. Combine with real authorization and limits.
- **APQ mistaken for a security control**: it caches documents but accepts any query. Use trusted documents to restrict.
- **No depth or cost limit**: cyclic relations (`user.friends.friends...`) allow cheap, expensive queries. Limit depth and cost.
- **Returning stack traces or SQL errors**: leaks internals. Mask and log.
- **`subscriptions-transport-ws` for new work**: unmaintained. Use `graphql-ws`.
- **Two copies of graphql installed**: type checks fail across copies. Dedupe and match peer ranges.
- **Mixing armor or validation packages built for graphql 16 into a graphql 17 server**: nested duplicate installs break at run time. Prefer plugins whose peer range includes 17, or a small custom rule.
- **Using `buildSubgraphSchema({ typeDefs, resolvers })`** with `@apollo/subgraph` 2.15: the argument must be a document or an array of modules, `buildSubgraphSchema([{ typeDefs, resolvers }])`.

## 16. References

- [references/schema-design.md](references/schema-design.md): nullability, naming, IDs and Node, connections, input and `@oneOf`, mutation payloads and errors as data, interfaces and unions, scalars, deprecation and evolution.
- [references/performance-and-security.md](references/performance-and-security.md): DataLoader, cost and depth limits, persisted operations in Yoga and Apollo, introspection and suggestions, authorization patterns, error masking, tracing.
- [references/federation-subscriptions-tooling.md](references/federation-subscriptions-tooling.md): Federation 2 subgraphs, routers, graphql-ws servers and clients, Apollo Server 5 with Express 5, codegen configuration.
- Official docs: https://spec.graphql.org/September2025/ , https://graphql.org/learn/ , https://www.graphql-js.org/docs/ , https://www.apollographql.com/docs/apollo-server , https://the-guild.dev/graphql/yoga-server , https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/federation , https://the-guild.dev/graphql/ws , https://the-guild.dev/graphql/codegen
