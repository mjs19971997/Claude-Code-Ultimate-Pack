# GraphQL API Hardening

GraphQL moves the shape and cost of a request into the client's hands, so OWASP API1, API3 and API4 need GraphQL-specific controls. This file uses Apollo Server 5 (Apollo Server 4 reached end of life on 2026-01-26) and GraphQL Armor; the same ideas apply to GraphQL Yoga (Envelop plugins) and other servers.

## 1. Resource limits

GraphQL Armor bundles validation rules and plugins for depth, cost, aliases, directives, tokens and field-suggestion blocking. Defaults are reasonable starting points (for example depth 6 and cost 5000); tune them against the real operations your clients send.

```typescript
import { ApolloServer } from '@apollo/server';
import { ApolloArmor } from '@escape.tech/graphql-armor';
import { typeDefs, resolvers } from './schema';
import { safelist } from './safelist-plugin';

const armor = new ApolloArmor({
  maxDepth: { n: 8 },
  costLimit: { maxCost: 5000 },
  maxAliases: { n: 15 },
  blockFieldSuggestion: { enabled: true },  // "Did you mean ...?" hints leak schema
});
const protection = armor.protect();
const isProd = process.env.NODE_ENV === 'production';

export const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: !isProd,                   // private API: off in production
  plugins: [...protection.plugins, ...(isProd ? [safelist] : [])],
  validationRules: [...protection.validationRules],
  formatError: (formatted) => {
    // Unexpected resolver errors become INTERNAL_SERVER_ERROR; do not leak their messages.
    if (formatted.extensions?.code === 'INTERNAL_SERVER_ERROR') {
      return { message: 'Internal server error', extensions: { code: 'INTERNAL_SERVER_ERROR' } };
    }
    return formatted;
  },
});
```

Check the GraphQL Armor documentation for the exact option names of the plugin version you install, and spread `protection.allowBatchedHttpRequests` or similar fields if the version returns them.

Also limit:
- HTTP body size at the framework and proxy.
- Batched operations per HTTP request (disable batching unless clients need it).
- List sizes through required `first`/`last` arguments with a maximum, enforced in resolvers and reflected in the cost model.
- Resolver timeouts and DataLoader batching to avoid N+1 fan-out to the database.

## 2. Operation safelisting

Automatic persisted queries (APQ) are a caching optimization: any client can register any operation. A safelist is different: the server accepts only operations that were extracted from your own clients at build time.

```typescript
import { createHash } from 'node:crypto';
import { GraphQLError } from 'graphql';
import type { ApolloServerPlugin } from '@apollo/server';
import approved from './safelist.json' with { type: 'json' }; // array of sha256 hex hashes

const allowed = new Set<string>(approved);

export const safelist: ApolloServerPlugin = {
  async requestDidStart() {
    return {
      async didResolveOperation({ source }) {
        const hash = createHash('sha256').update(source).digest('hex');
        if (!allowed.has(hash)) {
          throw new GraphQLError('Operation not allowed', {
            extensions: { code: 'OPERATION_NOT_ALLOWED', http: { status: 400 } },
          });
        }
      },
    };
  },
};
```

Generate `safelist.json` in the client build (for example with a GraphQL code generator or your client's persisted-document tooling) and deploy it before the client release. Managed alternatives exist (for example GraphOS persisted queries); check the vendor docs.

## 3. Authorization in GraphQL

- Authenticate once in the context function; resolvers read `context.principal`.
- Authorize in resolvers or in the data layer, not only at the root field: `user(id)` and `node(id)` must apply the same ownership rules as REST endpoints (BOLA).
- Field-level rules for sensitive fields (`email`, `salary`, `internalNotes`): a resolver or schema directive returns `null` or an error for callers without the permission (BOPLA).
- Mutations take dedicated input types with only writable fields; never map an input object straight into an ORM update.
- Batch permission checks with DataLoader keyed by `(principal, resourceId)` per request to avoid N+1 policy calls.

## 4. Other notes

- Apollo Server enables its CSRF prevention by default; keep it on when cookies authenticate GraphQL requests.
- Subscriptions over WebSocket need authentication at connection time and re-checks when permissions change; close connections on logout.
- Errors: keep stack traces off in production (Apollo includes them only when `includeStacktraceInErrorResponses` is enabled or outside production) and mask unexpected errors as above.
- Public GraphQL APIs that must keep introspection rely more heavily on cost limits, per-principal rate limits weighted by query cost, and field authorization.

## 5. Tests

- Depth bomb (`a { b { a { b ... } } }`), alias flood (`q1: field, q2: field, ...`), wide list requests without `first`, and large batched arrays all return validation errors.
- An operation not in the safelist is rejected in production mode.
- Node lookups with another tenant's global id return `null` or an authorization error.
- Field-level rules: a viewer without permission never sees the protected field in the response.
