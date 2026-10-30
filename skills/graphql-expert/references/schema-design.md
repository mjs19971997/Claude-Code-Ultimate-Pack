# Schema Design

Reference for modeling a GraphQL schema: nullability, naming, identifiers, pagination, input types, mutation results, errors as data, polymorphism, scalars and evolution. Verified against the GraphQL specification September 2025 Edition and graphql-js 17.0.2; code samples that execute were run on graphql 17 with GraphQL Yoga 6.0.1 (2026-10).

## 1. Errors and nullability in the specification

The September 2025 Edition distinguishes two kinds of errors:

- **Request error**: raised before execution (syntax, validation, variable coercion, missing information). The response contains `errors` and must not contain `data`.
- **Execution error**: raised while resolving a field. The response contains `data` (possibly partial) and a non-empty `errors` list; each error has `message`, and usually `locations`, `path` and `extensions`.

Null propagation: if a position with a non-null type raises an execution error, the error propagates to the parent position, which becomes `null` if its type allows it, otherwise it propagates further up to the nearest nullable position, or to `data: null`. Sibling positions that have not finished may be cancelled.

Consequences for design:

- A non-null field is a promise that it will resolve. Fields backed by an unreliable remote service, an optional join, or an authorization decision should be nullable.
- Put non-null on identifiers, required scalars of the same row (`id`, `title`), list containers (`posts: [Post!]!`), and payload fields that always exist.
- For lists use `[T!]!` unless null items carry meaning. `[T]` forces clients to null-check each item.
- Input types: required fields are `T!`; an omitted optional argument and an explicit `null` are different inputs, which matters for partial updates. In update inputs, make fields nullable, and decide whether `null` means "clear" or "invalid".
- Never use a non-null return type on a mutation field whose failure should not wipe the entire response: a failed non-null mutation field sets `data` to `null`.

## 2. Naming and documentation

- Types `PascalCase`, fields and arguments `camelCase`, enum values `UPPER_SNAKE_CASE`, input types end in `Input`, mutation payloads end in `Payload` or `Result`, connections end in `Connection`, edges in `Edge`.
- Fields describe domain concepts, not storage (`publishedAt`, not `pub_ts`; `author`, not `user_id`).
- Boolean fields read as predicates (`isArchived`, `hasNextPage`). Avoid negatives (`isNotActive`).
- Mutation names are verbs plus object (`createPost`, `archivePost`, `addMemberToTeam`), organized by domain action rather than CRUD where it clarifies intent.
- Add a description string (`"""..."""` or `"..."`) to types, fields and arguments that are not self-evident; descriptions appear in introspection and generated docs.

## 3. Identifiers and the Node interface

- Use the `ID` scalar; it serializes as a string. Treat IDs as opaque: clients must not parse them.
- Globally unique ids encode the type and key (`base64("Post:42")`) when the `Node` pattern is used:

```graphql
interface Node { id: ID! }
type Query { node(id: ID!): Node }
type Post implements Node { id: ID! title: String! }
```

- Implement `node(id)` only when clients need generic refetch (Relay-style caches). Authorize inside it like any other entry point.
- Sequential integer ids exposed to the public make enumeration trivial; if enumeration matters, use random or encoded ids, and still authorize every fetch.

## 4. Pagination with connections

Use the Relay cursor connection shape for lists that can grow:

```graphql
type Query {
  posts(first: Int! = 20, after: String, filter: PostFilter): PostConnection!
}

type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
}

type PostEdge {
  cursor: String!
  node: Post!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

Rules:

- Forward pagination uses `first`/`after`; add `last`/`before` only when backward paging is needed. Enforce a maximum for `first` in the resolver (and reject non-positive values).
- Cursors are opaque (base64url of a keyset position), stable across inserts, and tied to a deterministic sort with a unique tie-breaker (`createdAt, id`). Keyset (`WHERE (created_at, id) < ($1, $2)`) scales better than `OFFSET`.
- Fetch `first + 1` rows; if an extra row exists, `hasNextPage` is true.
- `totalCount` is expensive on large tables; expose it only when needed, and consider an estimate.
- Edge fields can hold relationship data (`role` on a membership edge).
- Filters and ordering are explicit input types (`PostFilter`, `PostOrder`), not free-form strings.

Resolver sketch (executed on graphql 17):

```ts
const encode = (n: number) => Buffer.from(String(n)).toString('base64url');
const decode = (cursor: string) => Number(Buffer.from(cursor, 'base64url').toString());

posts: (_: unknown, { first, after }: { first: number; after?: string }) => {
  const limit = Math.min(Math.max(first, 1), 50);
  const start = after ? decode(after) + 1 : 0;
  const rows = db.slice(start, start + limit + 1);       // fetch one extra row
  const page = rows.slice(0, limit);
  return {
    edges: page.map((node, i) => ({ cursor: encode(start + i), node })),
    pageInfo: {
      hasNextPage: rows.length > limit,
      hasPreviousPage: start > 0,
      startCursor: page.length ? encode(start) : null,
      endCursor: page.length ? encode(start + page.length - 1) : null,
    },
  };
},
```

In production, replace the array index cursor with a keyset cursor over the sort columns and validate that `decode` returns a finite number or a well-formed tuple; reject malformed cursors with a `BAD_USER_INPUT` error.

## 5. Input types

- One `input` argument per mutation keeps the mutation field stable when options are added.
- Use `@oneOf` input objects for exactly-one-of semantics. Introduced in the specification and part of the September 2025 Edition:

```graphql
input UserBy @oneOf {
  id: ID
  email: String
}
type Query { user(by: UserBy!): User }
```

graphql-js validates that exactly one field is set and non-null (the error reads: exactly one field must be specified, and the value for that field must be non-null).

- Default values (`first: Int! = 20`) are part of the schema contract; changing them changes behavior for existing clients.
- Enums model closed sets. Adding a value is additive for the server but can break clients with exhaustive handling; document an `UNKNOWN`-tolerant client policy.
- Avoid `JSON` scalars for structured input; model the shape. When unavoidable, validate in the service against a schema.
- Input objects cannot be recursive without a nullable or list break; avoid deeply nested inputs and bound list sizes in the service.
- Arguments and input fields can be deprecated with `@deprecated(reason:)` in this edition (non-null required ones cannot be deprecated).

## 6. Mutation results and errors as data

Pattern A, payload with `userErrors`:

```graphql
type Mutation { createPost(input: CreatePostInput!): CreatePostPayload! }
type CreatePostPayload { post: Post, userErrors: [UserError!]! }
type UserError { field: [String!], code: ErrorCode!, message: String! }
```

Pattern B, union result (each outcome is a type):

```graphql
union CreatePostResult = CreatePostSuccess | ValidationError | NotAuthorized | QuotaExceeded
type CreatePostSuccess { post: Post! }
type ValidationError { field: String!, message: String! }
type NotAuthorized { message: String! }
type QuotaExceeded { limit: Int!, message: String! }
```

Client query for B:

```graphql
mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on CreatePostSuccess { post { id title } }
    ... on ValidationError { field message }
    ... on NotAuthorized { message }
  }
}
```

Guidance:

- Expected, user-correctable outcomes are data. Unexpected failures (bugs, dependency outages, unauthenticated requests when the contract says so) use top-level errors with `extensions.code`.
- Choose one convention per schema and apply it everywhere.
- Union resolution: return objects with `__typename` or implement `__resolveType`. In graphql-tools executable schemas, resolvers for `CreatePostResult` need `__resolveType` unless every returned object has `__typename`.
- Mutation payloads return the affected objects (and parents when lists change) so clients can update caches without refetching.
- Mutations execute serially at the top level; keep each mutation field atomic from the client's point of view (a database transaction in the service).
- Make mutations idempotent where retries are likely: accept a client-generated `clientMutationId` or idempotency key in the input.

## 7. Interfaces, unions and polymorphism

- Interface: shared fields across types that clients treat uniformly (`Node`, `Timestamped`). Types must implement every interface field with compatible nullability.
- Union: alternative shapes without shared fields (`SearchResult = Post | User`, mutation outcomes).
- Return the concrete type through `__resolveType` (or `isTypeOf`); never leave abstract types to guess from field presence.
- Avoid deep interface hierarchies; clients must write inline fragments for each concrete type.

## 8. Scalars

- Built-ins: `Int` (32-bit signed), `Float`, `String`, `Boolean`, `ID`. Money, big integers and timestamps need custom scalars or structured types (`Money { amount: String!, currency: String! }` avoids float errors).
- Custom scalars declare their specification with `@specifiedBy(url: "...")` so clients know the format:

```graphql
scalar DateTime @specifiedBy(url: "https://scalars.graphql.org/andimarek/date-time")
scalar URL @specifiedBy(url: "https://tools.ietf.org/html/rfc3986")
```

- The `graphql-scalars` package (2.0.1, peer graphql 16 or 17) ships common scalar implementations; check the validation and serialization rules before adopting each.
- A scalar must implement `serialize`, `parseValue` and `parseLiteral`, and reject malformed input with a `GraphQLError`.

## 9. Evolution

Non-breaking: new types, new fields, new optional arguments, new optional input fields, new enum values (for output enums, with caution), new union members (with caution: clients with exhaustive handling).

Breaking: removing or renaming fields, types or arguments; making an output field nullable when it was non-null (clients may not null-check); making an input field required; changing a field's type; removing enum values; changing default values.

Process:

1. Add the replacement field.
2. Mark the old one `@deprecated(reason: "Use newField")`.
3. Measure usage per field by operation (router/server usage reporting or your own execution hooks).
4. Remove once usage is zero for a full release cycle of the slowest client (mobile apps lag).

Guard in CI with a schema diff against the published schema or registry; require an explicit override for intentional breaking changes.

## 10. Subscriptions in the schema

- Define `type Subscription { postCreated(authorId: ID): Post! }`; the payload type is the event; filter arguments narrow the stream.
- Each event is authorized for the subscriber at delivery time as well as at subscribe time; resolve with the same services as queries.
- Prefer narrow, domain-level events over "something changed" streams; clients can refetch via queries if needed.

## 11. Large schemas

- Split SDL by domain; compose with `extend type Query` in separate modules (graphql-tools `mergeTypeDefs`, Pothos, or federation across subgraphs).
- Keep the top-level `Query` focused: `me`, entity lookups, and a small number of root collections.
- Avoid exposing storage joins as fields; expose domain relationships with their access rules.
- Document ownership per type and per field when several teams contribute (federation `@key`, `@shareable`, `@override`, or CODEOWNERS on schema files).
