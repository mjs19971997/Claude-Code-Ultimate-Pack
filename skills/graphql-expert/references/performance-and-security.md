# Performance and Security

Reference for DataLoader batching, query depth and cost limits, persisted operations, introspection and suggestion policy, authorization patterns, error masking and tracing in GraphQL services. Verified against graphql-js 17.0.2 and 16.14.2, GraphQL Yoga 6.0.1, Apollo Server 5.5.1, DataLoader 2.2.3, graphql-query-complexity 2.0.0 (2026-10). The code in sections 1 to 5 was executed against these versions unless a note says otherwise.

## 1. DataLoader

DataLoader collects `load(key)` calls made in the same tick and calls one batch function with all keys.

```ts
import DataLoader from 'dataloader';

export function createLoaders(viewer: Viewer | null, db: Db) {
  return {
    userById: new DataLoader<string, User>(async (ids) => {
      // the batch query applies the viewer's scope; it is not a bare "WHERE id IN (...)"
      const rows = await db.users.findMany({ where: { id: { in: [...ids] }, ...scopeFor(viewer) } });
      const byId = new Map(rows.map((row) => [row.id, row]));
      // exactly one result per key, in key order; Error instances for per-key failures
      return ids.map((id) => byId.get(id) ?? new Error(`User ${id} not found`));
    }),
    postsByAuthor: new DataLoader<string, Post[]>(async (authorIds) => {
      const rows = await db.posts.findMany({ where: { authorId: { in: [...authorIds] }, ...scopeFor(viewer) } });
      return authorIds.map((id) => rows.filter((row) => row.authorId === id));
    }),
  };
}
```

Rules:

- Create loaders in the per-request context factory. A module-level loader caches across requests and users, leaking data and serving stale values.
- The batch function returns an array with the same length and order as `keys`. Map by key; never return database row order.
- Return `null`/`undefined` or an `Error` for missing items; do not throw for one missing key unless the whole batch failed.
- `maxBatchSize` bounds the `IN (...)` list; `cacheKeyFn` normalizes object keys; `clear(key)` and `prime(key, value)` keep the cache consistent after mutations in the same request.
- Loaders cannot fix N+1 inside a single resolver loop; also avoid `await` inside `for` loops that call `load()` one by one, which defeats batching (use `Promise.all` or `loadMany`).
- Authorization: a loader runs data access, so the viewer scope is part of the batch query. A loader that ignores the viewer is an authorization bypass for every path that uses it.
- Verify the effect: count queries per operation in tests. In the verification run, a query of three posts with `author` resolved through a loader called the batch function once.

When a parent resolver can join cheaply (SQL `JOIN`, an ORM `include`), do it there with a selected-field projection from `info`; keep loaders for the general case.

## 2. Depth limits

A static depth limit rejects deeply nested documents before execution. The rule below counts field nesting (leaf fields count as a level), follows fragments, and ignores introspection fields. It was run on graphql 17 with Yoga and on graphql 16 with Apollo Server.

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

Registration:

- Yoga: `plugins: [{ onValidate({ addValidationRule }) { addValidationRule(maxDepthRule(8)); } }]`.
- Apollo Server: `new ApolloServer({ validationRules: [maxDepthRule(8)] })`.
- Apollo Server also offers an opt-in `maxRecursiveSelections` option that limits recursive selection counts.

Pick a limit from your real client documents (maximum observed depth plus margin). Introspection queries are deeper than most app queries; if introspection is on in an environment, the rule above ignores `__` fields.

Libraries: `@escape.tech/graphql-armor` (3.2.0) bundles depth, cost, alias, token, directive and suggestion-blocking protections, and works with Apollo Server 4 and 5 on graphql 16 (verified: it rejected a depth-8 query at `n: 6` and hid field suggestions). Its packages declare graphql 16 as a peer; in a graphql 17 project they install a second copy of graphql and fail at run time (observed with Yoga 6 on graphql 17), so use a custom rule there.

## 3. Cost limits

Depth does not bound breadth: `users(first: 100) { friends(first: 100) { posts(first: 100) } }` is shallow but touches a million rows. Cost analysis multiplies list sizes.

Yoga (variables are known at execution time, so compute cost in `onExecute`):

```ts
import { GraphQLError } from 'graphql';
import { getComplexity, simpleEstimator } from 'graphql-query-complexity';
import type { Plugin } from 'graphql-yoga';

const MAX_COST = 1000;

const listMultiplier = ({ args, childComplexity, field }: any) =>
  field.type.toString().startsWith('[') ? (args.first ?? 10) * (1 + childComplexity) : undefined;

export const costLimit: Plugin = {
  onExecute({ args, setResultAndStopExecution }) {
    const cost = getComplexity({
      schema: args.schema,
      query: args.document,
      variables: args.variableValues ?? {},
      operationName: args.operationName ?? undefined,
      estimators: [listMultiplier, simpleEstimator({ defaultComplexity: 1 })],
    });
    if (cost > MAX_COST) {
      setResultAndStopExecution({
        errors: [new GraphQLError(`Query cost ${cost} exceeds ${MAX_COST}`, { extensions: { code: 'QUERY_TOO_COSTLY' } })],
      });
    }
  },
};
```

Apollo Server: the same `getComplexity` call in a plugin, inside `requestDidStart` returning `{ async didResolveOperation({ schema, document, request, operationName }) { ... throw new GraphQLError(...) } }`.

Notes:

- Estimators only know what they are told: give list arguments meaningful names (`first`, `limit`), and set per-field costs for expensive resolvers (`fieldExtensionsEstimator` reads `extensions: { complexity }` on fields).
- Pair cost limits with per-identity rate limiting that charges the computed cost, not one unit per HTTP request.
- Also cap aliases (`a1: user(id:1) a2: user(id:2) ...`), directive counts and token counts, and bound batch size (`allowBatchedHttpRequests` in Apollo is off by default).
- Add execution timeouts using `AbortSignal` (graphql-js 17 `abortSignal` and `info.getAbortSignal()`, or an abort signal in your context passed to database calls).

## 4. Persisted operations and trusted documents

Two different features share a name:

| Feature | Protects against arbitrary queries? | Notes |
|---|---|---|
| Automatic Persisted Queries (APQ) | No | Client sends a hash; on a miss it resends the full query and the server stores it. Saves bandwidth, any document is accepted |
| Persisted operations / trusted documents | Yes | Documents are extracted at build time and registered; the server executes only known ids |

Yoga with `@graphql-yoga/plugin-persisted-operations` (4.0.1). The plugin reads the id from `extensions.persistedQuery.sha256Hash` by default; `allowArbitraryOperations: false` rejects raw queries:

```ts
import { usePersistedOperations } from '@graphql-yoga/plugin-persisted-operations';
import documents from './persisted-documents.json' with { type: 'json' }; // { "<id>": "query Foo { ... }" }

createYoga({
  schema,
  plugins: [
    usePersistedOperations({
      getPersistedOperation: (id) => (documents as Record<string, string>)[id] ?? null,
      allowArbitraryOperations: false, // verified: a request carrying both id and body is rejected too
    }),
  ],
});
```

Apollo Server 5 does not restrict operations by itself; options are the router/GraphOS persisted queries (verify plan requirements in the GraphOS docs) or a small allowlist step in front of the server. This one was run with Express 5 and `@as-integrations/express5`:

```ts
function trustedDocuments(store: Map<string, string>): RequestHandler {
  return (req, res, next) => {
    const ops = Array.isArray(req.body) ? req.body : [req.body];
    for (const op of ops) {
      if (typeof op?.documentId !== 'string' || typeof op.query === 'string') {
        res.status(400).json({ errors: [{ message: 'Only persisted operations are accepted', extensions: { code: 'PERSISTED_OPERATION_REQUIRED' } }] });
        return;
      }
      const text = store.get(op.documentId);
      if (!text) {
        res.status(400).json({ errors: [{ message: 'Unknown document id', extensions: { code: 'PERSISTED_OPERATION_NOT_FOUND' } }] });
        return;
      }
      op.query = text;
    }
    next();
  };
}
// app.use('/graphql', express.json({ limit: '100kb' }), trustedDocuments(documents), expressMiddleware(server));
```

Client side: GraphQL Code Generator `client-preset` emits the manifest at build time when `presetConfig: { persistedDocuments: true }` is set. With `@graphql-codegen/client-preset` 6.2.3 the output is `persisted-documents.json`, a map from `sha256:<hash>` ids to the document text, and the client sends the id instead of the text. Keep public third-party consumers on a separate, limited, rate-limited endpoint with depth and cost limits instead of opening the first-party endpoint.

## 5. Introspection, suggestions and error masking

- Introspection: Apollo Server 5 defaults to enabled outside `NODE_ENV=production` and disabled in production; set `introspection` explicitly. Yoga: `useDisableIntrospection()` from `@graphql-yoga/plugin-disable-introspection` (disabled for every request unless `isDisabled` says otherwise; with introspection off a `__schema` query returns the message "GraphQL introspection has been disabled").
- Suggestions: invalid field names return "Did you mean ..." messages that disclose schema names even when introspection is off. Options: Apollo `hideSchemaDetailsFromClientErrors: true` or `ApolloServerPluginDisableSuggestions()` from `@apollo/server/plugin/disableSuggestions`, graphql-js `hideSuggestions: true` in `ExecutionArgs`, or the graphql-armor block-suggestions plugin on graphql 16.
- Error masking: Yoga masks unexpected errors by default (`maskedErrors`, message "Unexpected error."); `GraphQLError` instances you throw are returned as is. Apollo:

```ts
import { unwrapResolverError } from '@apollo/server/errors';

new ApolloServer({
  typeDefs, resolvers,
  includeStacktraceInErrorResponses: false,
  formatError: (formatted, error) => {
    if (formatted.extensions?.code === 'INTERNAL_SERVER_ERROR') {
      logger.error({ err: unwrapResolverError(error) }, 'resolver failed'); // log the original
      return { message: 'Internal error', extensions: { code: 'INTERNAL_SERVER_ERROR' } };
    }
    return formatted;
  },
});
```

- Status codes: Apollo Server 5 returns HTTP 400 for variable coercion errors (`status400ForVariableCoercionErrors` defaults to true); set a status for auth errors with `extensions: { http: { status: 401 } }` on a `GraphQLError` (verified: response 401 with `data: null`). Modern clients and servers also support the GraphQL over HTTP media type `application/graphql-response+json` (Yoga); keep status handling consistent between server and clients.

## 6. Authorization patterns

Principles:

1. One decision point per resource and field in the service layer, called by every entry point (queries, mutations, subscriptions, loaders, federation reference resolvers).
2. Default deny: a missing rule is a denial.
3. Reads and writes are scoped alike: every SQL/ORM statement includes the tenant or owner condition, including `UPDATE` and `DELETE` by id.
4. Resolvers pass the viewer; services never read ambient globals.

Field-level rule in the service:

```ts
export const userService = {
  visibleEmail(viewer: Viewer | null, user: User): string | null {
    if (!viewer) return null;
    if (viewer.id === user.id || viewer.roles.includes('staff')) return user.email;
    return null;                       // nullable field: hide rather than fail the whole parent
  },

  async rename(viewer: Viewer | null, id: string, name: string): Promise<User> {
    if (!viewer) throw authError('UNAUTHENTICATED');
    // owner or tenant condition is part of the statement; zero rows updated means not found or forbidden
    const row = await db.users.updateMany({ where: { id, tenantId: viewer.tenantId, ...(viewer.roles.includes('admin') ? {} : { id: viewer.id }) }, data: { name } });
    if (row.count === 0) throw authError('FORBIDDEN');
    return db.users.findUniqueOrThrow({ where: { id } });
  },
};
```

Choosing denial vs null: nullable fields can return `null` for "not visible"; non-null fields cannot, so either make them nullable or deny the parent. Use consistent error codes (`UNAUTHENTICATED`, `FORBIDDEN`). Returning `NOT_FOUND` for other tenants' resources avoids confirming existence.

Directives like `@auth(requires: ADMIN)` are convenient documentation and can enforce coarse checks, but they apply per schema coordinate; they cannot see object ownership. Keep object-level checks in services.

Federation: the router can enforce `@authenticated`, `@requiresScopes` and `@policy` on schema coordinates (check the GraphOS docs for plan requirements); subgraphs still validate the authenticated claims they receive, and entity resolvers apply object-level checks.

## 7. Rate limiting and abuse control

- Limit per identity (user id, API key) and per IP for unauthenticated traffic, at the edge and at the router.
- Charge by computed cost where possible; a flat per-request limit lets aliases and batches bypass it.
- Disable HTTP batching unless needed (`allowBatchedHttpRequests` is opt-in in Apollo Server) and cap batch length.
- Cap request body size (`express.json({ limit })` for Express, the equivalent limit at the reverse proxy or server adapter for other stacks), and reject mutations sent over GET.
- Use short per-operation timeouts and cancel downstream work on abort.

## 8. Observability

- Name operations on clients. Log `operationName`, operation type, duration, error codes and request id; do not log variables unless redacted.
- graphql-js 17 publishes tracing channels on `node:diagnostics_channel`: `graphql:parse`, `graphql:validate`, `graphql:execute`, `graphql:execute:variableCoercion`, `graphql:execute:rootSelectionSet`, `graphql:subscribe` and `graphql:resolve`. The `graphql:resolve` context includes `fieldName`, `parentType`, `fieldType`, `args`, `isDefaultResolver` and `fieldPath`. APM libraries can subscribe without touching the schema:

```ts
import dc from 'node:diagnostics_channel';

dc.tracingChannel('graphql:execute').subscribe({
  start(ctx: any) { ctx.startedAt = performance.now(); },
  end() {}, asyncStart() {}, error() {},
  asyncEnd(ctx: any) {
    metrics.histogram('graphql_execute_ms', performance.now() - ctx.startedAt, { operation: ctx.operationName ?? 'anonymous' });
  },
});
```

- Per-resolver tracing is expensive at high field counts; trace only non-default resolvers (`isDefaultResolver === false`) or sample.
- Apollo Server plugins (`requestDidStart`, `willSendResponse`) and Yoga/Envelop plugins (`onExecute`, `onValidate`) hook into the request pipeline on the graphql versions each supports.
- Track field usage for deprecation decisions and query cost outliers (top operations by cost and by duration).
