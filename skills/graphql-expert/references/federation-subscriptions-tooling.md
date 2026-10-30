# Federation, Subscriptions and Tooling

Reference for Apollo Federation 2 subgraphs, routers, subscription transports, Apollo Server 5 integration and code generation. Verified against `@apollo/subgraph` 2.15.1 (supports federation spec versions up to v2.15), `@apollo/gateway` 2.14.4, Apollo Router 2.19, Apollo Server 5.5.1, GraphQL Yoga 6.0.1, graphql-ws 6.4.1, `@graphql-codegen/cli` 7.4.6, `client-preset` 6.2.3 and `typescript-resolvers` 6.1.1 (2026-10). The subgraph, subscription and codegen samples were executed.

## 1. Federation 2 overview

A federated graph is a supergraph composed from subgraph schemas. A router (Apollo Router 2.x, a Rust binary; or Hive Gateway) plans each client operation across subgraphs. Composition happens in CI with Rover, or in a managed federation service (GraphOS), and produces the supergraph schema the router loads.

When to federate: several teams own distinct parts of the graph and deploy independently. Otherwise a modular single schema is simpler. Service boundary questions are covered by microservices-expert.

JavaScript package notes:

- `@apollo/subgraph` 2.15 and `@apollo/gateway` 2.14 declare graphql 16 as a peer. The router is not a JavaScript process, so it does not constrain the graphql-js version of a subgraph in other stacks.
- Subgraph schemas can be built with `@apollo/subgraph` for Apollo Server and GraphQL Yoga (a subgraph schema is an ordinary `GraphQLSchema`), through the NestJS Apollo federation driver in `@nestjs/apollo`, with Pothos federation support, and with non-JavaScript servers.

## 2. A subgraph with Apollo Server 5

```ts
import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { buildSubgraphSchema } from '@apollo/subgraph';
import { parse } from 'graphql';

const typeDefs = parse(`#graphql
  extend schema
    @link(url: "https://specs.apollo.dev/federation/v2.9", import: ["@key", "@shareable"])

  type Product @key(fields: "id") {
    id: ID!
    name: String!
  }

  type Query {
    product(id: ID!): Product
  }
`);

const resolvers = {
  Query: {
    product: (_: unknown, { id }: { id: string }, ctx: Context) => ctx.loaders.product.load(id),
  },
  Product: {
    // called by the router with the representation { __typename: "Product", id: "..." }
    __resolveReference: ({ id }: { id: string }, ctx: Context) => ctx.loaders.product.load(id),
  },
};

const server = new ApolloServer<Context>({
  // note the array: buildSubgraphSchema takes a document or an array of { typeDefs, resolvers } modules
  schema: buildSubgraphSchema([{ typeDefs, resolvers }]),
  introspection: false,
});

await startStandaloneServer(server, {
  listen: { port: 4001 },
  context: async ({ req }) => createContext(req), // per-request loaders and the verified router identity
});
```

Verified behavior: with the schema above, `_entities(representations: [{__typename: "Product", id: "1"}])` resolved through `__resolveReference`, and introspection returned "GraphQL introspection is not allowed" when disabled. The `@link` URL names a federation spec version; use one that the `@apollo/subgraph` build and your composition and router versions all support (versions are listed in the Federation changelog; 2.15.1 accepts up to v2.15).

## 3. Directives and what introduced them

Federation spec versions that added each directive (from the `@apollo/subgraph` 2.15.1 definitions):

| Directive | Purpose | Since |
|---|---|---|
| `@key(fields)` | Declares an entity and its key | 2.0 |
| `@shareable` | Field resolvable by more than one subgraph (repeatable since 2.2) | 2.0 |
| `@external`, `@requires`, `@provides` | Fields owned elsewhere, needed inputs, and fields this subgraph can supply on a path | 2.0 |
| `@override(from, label)` | Move a field's ownership between subgraphs; `label` enables progressive rollout | 2.0, `label` 2.7 |
| `@inaccessible` | Hide schema elements from the public API schema | 2.0 |
| `@tag` | Attach metadata for contracts and filtering | 2.0 |
| `@composeDirective` | Carry a custom directive into the supergraph | 2.1 |
| `@interfaceObject` | Contribute fields to an interface owned by another subgraph | 2.3 |
| `@authenticated`, `@requiresScopes` | Router-enforced authentication and scope checks per schema element | 2.5 |
| `@policy` | Router-enforced custom policy checks | 2.6 |
| `@context`, `@fromContext` | Share context values between types within a subgraph | 2.8 |
| `@cost`, `@listSize` | Hints for demand control in the router | 2.9 |
| `@cacheTag` | Cache invalidation tags | 2.12 |

Availability of router-side features (authorization directives, demand control, entity caching) can depend on the GraphOS plan; check the router documentation for the version you deploy.

## 4. Federation practices

- Entities: pick stable keys (`@key(fields: "id")`); resolve references in `__resolveReference` through a per-request DataLoader to avoid N+1 across entity batches (the router sends many representations in one `_entities` call).
- Each subgraph is a full GraphQL service: authorize in the subgraph, since it receives representations from the router and cannot assume the router checked object-level rules. Pass the verified identity from the router to subgraphs through headers or a signed token and validate it.
- Subgraphs are not exposed to the public network; only the router is.
- Keep shared value types `@shareable` and identical across subgraphs; composition fails on conflicts.
- Move a field between subgraphs with `@override(from: "old")`, deploy the new owner, then remove the field from the old subgraph.
- Composition in CI: compose subgraph schemas on every change and run schema checks against the production supergraph and recorded client operations (Rover and GraphOS provide `subgraph check`; a self-hosted pipeline can compose with Rover and diff).
- Router configuration (timeouts, introspection, persisted queries or safelisting, rate limiting, CSRF, CORS, telemetry) lives in the router YAML; see the Apollo Router documentation for the keys of your version.
- Alternative gateways: Hive Gateway (`@graphql-hive/gateway` 2.15) supports federation in JavaScript runtimes; `@apollo/gateway` remains published for the JavaScript gateway path.

## 5. Apollo Server 5 with Express 5

Apollo Server 5 does not include Express middleware. Use `@as-integrations/express5` (also `express4` and `fastify` integrations exist):

```ts
import http from 'node:http';
import express from 'express';
import { ApolloServer } from '@apollo/server';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import { expressMiddleware } from '@as-integrations/express5';

const app = express();
const httpServer = http.createServer(app);

const server = new ApolloServer<Context>({
  typeDefs,
  resolvers,
  introspection: process.env.NODE_ENV !== 'production', // explicit; production default is off anyway
  includeStacktraceInErrorResponses: false,
  plugins: [ApolloServerPluginDrainHttpServer({ httpServer })],
});
await server.start();

app.use(
  '/graphql',
  express.json({ limit: '100kb' }),
  expressMiddleware(server, { context: async ({ req }) => createContext(req) }),
);
httpServer.listen(4000);
```

Verified behavior of this setup: an `UNAUTHENTICATED` `GraphQLError` with `extensions.http.status = 401` produced HTTP 401 with `data: null`; unexpected errors were masked in `formatError`; with `NODE_ENV=production` the introspection query was rejected.

`ApolloServer` handles `SIGINT`/`SIGTERM` by default (`stopOnTerminationSignals`); in a custom shutdown sequence set it deliberately.

## 6. Subscriptions

Transports:

| Transport | Notes |
|---|---|
| `graphql-ws` (protocol `graphql-transport-ws`) | The maintained WebSocket protocol; `graphql-ws` 6.4.1 provides server adapters (`graphql-ws/use/ws`, `/use/@fastify/websocket`, `/use/uWebSockets`, `/use/bun`, `/use/deno`, `/use/crossws`) and a client (`createClient`) |
| SSE | Built into GraphQL Yoga (`Accept: text/event-stream`); also `graphql-sse` |
| `subscriptions-transport-ws` | Unmaintained, marked deprecated on npm; do not use for new work; NestJS GraphQL 14 removed support for it |

Apollo Server 5 does not host subscriptions itself; pair it with a `graphql-ws` server on the same HTTP server, or use its callback-based subscription plugin for router-driven subscriptions.

`graphql-ws` server on a plain graphql-js schema (executed on graphql 17 with `ws`):

```ts
import { createServer } from 'node:http';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/use/ws';
import { makeExecutableSchema } from '@graphql-tools/schema';

const schema = makeExecutableSchema({
  typeDefs: 'type Query { ok: Boolean } type Subscription { tick: Int! }',
  resolvers: {
    Subscription: {
      tick: { subscribe: async function* () { for (let i = 1; i <= 3; i++) yield { tick: i }; } },
    },
  },
});

const httpServer = createServer();
const wss = new WebSocketServer({ server: httpServer, path: '/graphql' });

const cleanup = useServer(
  {
    schema,
    // reject the connection unless a valid token is supplied in connectionParams
    onConnect: async (ctx) => (await verifyToken(ctx.connectionParams?.token)) !== null,
    context: async (ctx) => ({ viewer: await verifyToken(ctx.connectionParams?.token) }),
  },
  wss,
);
httpServer.listen(4000);
// on shutdown: await cleanup.dispose();
```

Client:

```ts
import { createClient } from 'graphql-ws';
import { WebSocket } from 'ws'; // Node; browsers use the global WebSocket

const client = createClient({
  url: 'wss://api.example.com/graphql',
  webSocketImpl: WebSocket,
  connectionParams: async () => ({ token: await getAccessToken() }),
});
for await (const event of client.iterate({ query: 'subscription { tick }' })) {
  console.log(event.data);
}
```

Operational rules:

- Authenticate at connection time (`onConnect`), and authorize each event for the viewer; tokens expire while sockets stay open, so close or re-check long-lived connections.
- Use `wss://`; terminate TLS at the proxy and raise idle timeouts above the ping interval.
- Limit concurrent subscriptions per connection and connections per identity; apply depth and cost limits to subscription documents too.
- Fan out through a shared pub/sub (Redis, Kafka, NATS) so any instance can serve any subscriber; use `AsyncIterator` helpers from your pub/sub library.
- Yoga SSE example (executed): a `GET` with `accept: text/event-stream` returned `event: next` frames with `{"data":{"countdown":2}}` and a final `event: complete`.

## 7. Code generation

Resolver types from the schema (`codegen.ts`, executed with `@graphql-codegen/cli` 7.4.6):

```ts
import type { CodegenConfig } from '@graphql-codegen/cli';

const config: CodegenConfig = {
  schema: 'schema/schema.graphql',
  generates: {
    'src/generated/resolvers.ts': {
      plugins: ['typescript', 'typescript-resolvers'],
      config: {
        contextType: '../context.js#Context',
        useTypeImports: true,
        enumsAsTypes: true,
        mappers: { Post: '../models.js#PostModel', User: '../models.js#UserModel' },
      },
    },
  },
};
export default config;
```

- `contextType` types the third resolver argument; `mappers` map schema types to your database models so resolvers return model objects and the type system requires field resolvers for the rest.
- The generated `Resolvers` type gives compile-time checks for resolver maps; use `satisfies Resolvers` in server setup.

Typed client documents with the client preset, plus a persisted-document manifest:

```ts
const config: CodegenConfig = {
  schema: 'schema/schema.graphql',
  documents: ['src/**/*.ts'],
  generates: {
    './src/gql/': { preset: 'client', presetConfig: { persistedDocuments: true } },
  },
};
```

Generated files: `gql.ts`, `graphql.ts`, `fragment-masking.ts`, `index.ts`, and `persisted-documents.json` (ids of the form `sha256:<hash>` mapped to document text). Ship that manifest to the server as the allowlist.

Other tooling:

- `@graphql-eslint/eslint-plugin` (4.4.2, peer graphql 16) lints SDL and operations (naming, deprecation reasons, unused fields).
- `@graphql-tools/mock` mocks schemas for client tests; `@graphql-tools/schema` `makeExecutableSchema` builds executable schemas from SDL and resolvers.
- Schema diffing in CI: GraphQL Inspector or the GraphOS/Hive schema checks.
- Code-first alternatives: Pothos (`@pothos/core` 4.16, graphql 16.10+ or 17) and NestJS code-first decorators; the same security and loader rules apply.
