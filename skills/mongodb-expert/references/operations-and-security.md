# Operations and Security

Reference for read and write concerns, transactions, change streams, shard key selection, in-use encryption, MongoDB Search and Vector Search, query injection defenses, and Node.js driver pooling and timeouts. Verified against MongoDB Server 9.0.4 manual, Node.js driver 7.8.0 documentation and the MongoDB Vector Search documentation (2026-10).

## 1. Read and write concerns

- **Write concern** `w`: `1` acknowledges after the primary applies the write; `"majority"` acknowledges after a majority of data-bearing voting members have it, so it survives failover. The default is `majority` for most deployments (the implicit default depends on topology, for example arbiters; check the write concern page). Add `j: true` only if the journal commit must be confirmed beyond majority semantics; set `wtimeout`/`timeoutMS` to avoid indefinite waits.
- **Read concern**: `local` (default for primary reads) returns the node's latest data, which can later be rolled back; `majority` returns majority-committed data; `snapshot` provides a consistent snapshot inside transactions; `linearizable` guarantees up-to-date majority-committed reads for single-document reads on the primary at a latency cost; `available` is for sharded clusters where orphaned documents are acceptable.
- **Read preference**: `primary` (default), `primaryPreferred`, `secondary`, `secondaryPreferred`, `nearest`. Secondary reads can be stale; use them for reports, not for read-your-writes flows.
- **Causal consistency**: sessions give read-your-writes and monotonic reads when reads use `majority` and writes use `majority` in the same causally consistent client session (enable it explicitly on the session; check the guarantees table in the manual for the combinations that apply).
- Set client-wide defaults in the connection string or `MongoClient` options (`w=majority`, `readConcernLevel`, `readPreference`) and override per operation only with a reason.

```ts
const client = new MongoClient(uri, { writeConcern: { w: "majority" }, readConcern: { level: "majority" }, retryWrites: true });
```

## 2. Transactions

- Multi-document transactions run on replica sets and sharded clusters, not standalone servers. They are ACID with snapshot isolation.
- Limits and defaults: a transaction must finish within 60 seconds by default (`transactionLifetimeLimitSeconds`); locks are waited for 5 ms before the transaction aborts; the server creates as many oplog entries as needed (each limited to 16 MiB); a transaction too large for the WiredTiger cache aborts with `TransactionTooLargeForCache`. From 9.0 the server also limits concurrently open multi-document transactions for external clients (`maxConcurrentMultiDocumentTransactions`, default 10,000) and rejects new ones with `TooManyOpenTransactions`.
- Model first: a single-document update is atomic across embedded data; use a transaction only for invariants spanning documents (transfer between accounts, order plus stock).
- Use the convenient API (`session.withTransaction(callback, options)`); the driver retries on `TransientTransactionError` and retries the commit on `UnknownTransactionCommitResult`. The callback may run more than once, so it must be idempotent and must not perform external side effects (emails, HTTP calls) inside.
- Rules for the callback: pass the session to every operation (`{ session }`), await operations sequentially (no `Promise.all` on one session), catch only errors you can handle (swallowing errors can cause infinite retries), and do not hold user interaction or slow network calls inside.
- Collections and indexes must exist before the transaction touches them (create them outside it).
- In sharded clusters, a transaction spanning shards uses two-phase commit and costs more; keep common transactions within one shard via the shard key.
- Always include the tenant in every operation inside the transaction; a transaction does not add authorization.

## 3. Change streams

- Available on replica sets and sharded clusters. Open with `collection.watch(pipeline, options)`, `db.watch()` or `client.watch()`. Filter in the pipeline (`$match` on `operationType`, `ns`, fields) so the server does the filtering.
- Events carry a resume token in `_id`. Persist it after the event is handled and resume with `resumeAfter` (or `startAfter` after an invalidate event). Resuming requires the token's position to still be in the oplog; otherwise the server returns `ChangeStreamHistoryLost` and the consumer must resynchronize from the collection and open a new stream.
- `fullDocument: "updateLookup"` returns the current document for updates (it may differ from the state at the time of the event). For before/after images enable `changeStreamPreAndPostImages: { enabled: true }` on the collection (`collMod`) and use `fullDocumentBeforeChange: "whenAvailable"` / `fullDocument: "whenAvailable"`; pre-images consume storage and have retention settings.
- Delivery is at least once across restarts; consumers must be idempotent. Order is the order of the oplog for the stream (per shard merged by cluster time on sharded clusters).
- From 9.0, a stream opened with a `primary` or `secondary` read preference can return the resumable error `InterruptedDueToReplStateChange` after an election; drivers resume automatically, hand-written `getMore` loops and `mongosh` must resume with `resumeAfter`.
- Change streams are not a message queue with consumer groups; run one consumer per stream, or fan out through a broker. Keep oplog size and retention larger than the worst-case consumer downtime.
- Use change streams for cache invalidation, projections to search indexes, and outbox publishing; for multi-tenant data filter by tenant when the consumer serves one tenant (`fullDocument.tenantId` requires the full document).

## 4. Sharding

- Shard when one replica set cannot hold the data, working set or write rate after vertical scaling and index/model fixes.
- Shard key quality: **cardinality** (many distinct values), **frequency** (no value dominates), **monotonicity** (avoid always-increasing values such as `ObjectId`, timestamps: all inserts go to the last chunk), and **query targeting** (most queries include the key so `mongos` targets one or few shards instead of broadcasting).
- Choices: hashed key (even writes, no range targeting), ranged compound key with a well-distributed prefix (`{ tenantId: 1, _id: 1 }` for multi-tenant data), `{ customerId: 1, createdAt: 1 }` for per-customer time queries.
- You can change the key later (`reshardCollection`, available since 5.0; reshard to the same key with `forceRedistribution` since 8.0), refine it by adding suffix fields (`refineCollectionShardKey`), and unshard or move collections (`unshardCollection`, `moveCollection`). Resharding is a heavy operation that needs spare capacity, so choose carefully anyway. Use `analyzeShardKey` with `configureQueryAnalyzer` on sampled traffic to evaluate candidates.
- A document's shard key value can be updated (except `_id`), but frequent changes that move documents between shards are expensive.
- Unique indexes on sharded collections must include the shard key as a prefix; per-tenant uniqueness fits well with a tenant-prefixed shard key.
- Zone sharding can pin tenant or region data to specific shards for locality and residency.

## 5. Queryable Encryption and CSFLE

| Aspect | Queryable Encryption (QE) | Client-Side Field Level Encryption (CSFLE) |
|---|---|---|
| Server query on encrypted fields | Equality and range; prefix, suffix and substring on strings (GA in 9.0) | Deterministic encryption allows equality only |
| Randomized encryption | Yes (queries use encrypted metadata) | Randomized fields are not queryable |
| Automatic encryption | Atlas and Enterprise Advanced; Community supports manual encryption with `bypassQueryAnalysis` | Atlas and Enterprise Advanced; Community supports manual encryption |
| Server requirement | 7.0+ replica set or sharded cluster (not standalone) | 4.2+ (Enterprise and Community), replica set or sharded cluster (not standalone) |

- Both encrypt on the client; the server never sees plaintext or the keys. Neither protects against an adversary who holds your customer master key and data keys or who can arbitrarily write to the encrypted collections.
- Keys: a customer master key (CMK) in a KMS (AWS KMS, Azure Key Vault, GCP KMS, KMIP); data encryption keys (DEKs) in a key vault collection (`encryption.__keyVault`) protected by strict roles. Use one DEK per tenant to allow per-tenant key rotation and cryptographic deletion.
- Define the encrypted fields map at collection creation (`encryptedFields` with `queries: { queryType: "equality" }` or `"range"`, `"prefix"`, `"suffix"`, `"substring"` with their options). Range fields need `min`, `max` (and optionally `sparsity`, `precision`) set before data is written.
- Prefix, suffix and substring queries became GA in 9.0 with the `string` algorithm; the earlier `prefixPreview`, `suffixPreview`, `substringPreview` query types from the 8.2/8.3 preview were removed and need migration (create new collections or follow the migration procedure in the 9.0 compatibility notes).
- Encrypted fields cannot be used in server-side aggregation stages that need plaintext, and QE is not compatible with MongoDB Search indexes; check the limitations page for the current list.
- Avoid putting low-entropy sensitive values behind deterministic or equality encryption without considering frequency analysis.

## 6. MongoDB Search and Vector Search

- **MongoDB Search** (`$search`, `$searchMeta`) provides Lucene-based full-text search, facets, autocomplete, fuzzy matching and scoring. **MongoDB Vector Search** (`$vectorSearch`) provides approximate (ANN) and exact (ENN) nearest-neighbor search over embeddings. Both run in MongoDB Atlas; the `mongot` search process for self-managed Community and Enterprise deployments is documented as Preview, so check the current status before relying on it in production.
- Search indexes are created with `createSearchIndex`, not `createIndex`. A vector index declares the vector field and any pre-filter fields:

```ts
await collection.createSearchIndex({
  name: "chunks_vector",
  type: "vectorSearch",
  definition: {
    fields: [
      { type: "vector", path: "embedding", numDimensions: 1536, similarity: "cosine" },
      { type: "filter", path: "tenantId" },
    ],
  },
});
```

```js
// $vectorSearch must be the first stage; pre-filter by tenant inside the stage
db.chunks.aggregate([
  { $vectorSearch: {
      index: "chunks_vector",
      path: "embedding",
      queryVector: queryEmbedding,      // same model and dimensions as the indexed vectors
      numCandidates: 200,               // candidates considered for ANN; must be >= limit
      limit: 10,
      filter: { tenantId: "acme" }      // filter fields must be indexed with type "filter"
  } },
  { $project: { _id: 0, text: 1, score: { $meta: "vectorSearchScore" } } }
])
```

- Tenant isolation: always use a `filter` on the tenant field in `$vectorSearch` and `$search` (a compound/`equals` filter); post-filtering after the search can return too few results and leaks existence through scores.
- Keep embeddings in the same document or a linked one; changing the embedding model requires re-embedding and re-indexing all vectors.
- If you need richer relevance tuning at large scale, a dedicated engine may fit better (see elasticsearch-expert).

## 7. Injection defenses

Operator injection happens when user-controlled objects reach a query.

```ts
// Vulnerable: body = { "email": { "$ne": null }, "password": { "$ne": null } }
const user = await users.findOne({ email: req.body.email, password: req.body.password });
```

Defenses:

1. Validate types at the boundary with a schema library (for example Zod, Valibot or JSON Schema): `email: z.string().email()`, `id: z.string().regex(/^[0-9a-f]{24}$/)`. A string schema rejects objects, which removes operator keys.
2. Build the filter from named fields, never by passing the parsed body, query string or a user-supplied "filter" object through. Express's extended query parser turns `?email[$ne]=x` into an object, so validate query parameters too.
3. Compare password hashes in application code after looking up by a validated identifier; never query by password.
4. Do not use `$where`, `$function` or `$accumulator` with user data. In 9.0 these are re-enabled on a WebAssembly engine with stronger sandboxing, but arbitrary user JavaScript is still a risk; disable with `security.javascriptEnabled: false` if unused.
5. For `$regex`, escape user text (`s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")`), anchor it, bound length, and prefer indexed prefix matching or Search.
6. Restrict sort/projection keys to an allowlist; do not let users choose arbitrary field names or `$`-prefixed keys.
7. Mongoose: enable `mongoose.set("sanitizeFilter", true)` as defense in depth (it wraps nested `$` operators in `$eq`), but still validate input types.
8. Allow-list update paths: never pass `req.body` to `$set`; pick fields explicitly (mass assignment, including `tenantId`, `role`, `isAdmin`).

## 8. Driver configuration (Node.js driver 7.x)

| Option | Default | Guidance |
|---|---|---|
| `maxPoolSize` | 100 | Per server; total connections = instances x pool size x servers; keep under the server limit |
| `minPoolSize` | 0 | Raise to keep warm connections for latency-sensitive services |
| `maxIdleTimeMS` | 0 (no limit) | Set below firewall or load balancer idle timeouts |
| `waitQueueTimeoutMS` | 0 (no limit) | Set a bound so requests fail instead of queuing forever |
| `serverSelectionTimeoutMS` | 30000 | Lower (for example 5000) so a down cluster fails fast |
| `connectTimeoutMS`, `socketTimeoutMS` | driver defaults | Prefer operation-level limits (`maxTimeMS`) |
| `retryWrites`, `retryReads` | true | Keep on; one automatic retry for transient errors |
| `timeoutMS` | unset | Client-side operation timeout covering server selection, checkout and execution; experimental in this driver, so prefer `maxTimeMS` for stability |
| `serverApi` | unset | `{ version: "1", strict: true, deprecationErrors: true }` pins command behavior |

- Create the client once; reuse it across requests and across serverless invocations; call `client.close()` at shutdown. The driver monitors topology and handles failover.
- Use `mongodb+srv://` URIs with TLS, a dedicated least-privilege user, and credentials from a secret manager.
- Connection pool events (`connectionPoolCreated`, `connectionCheckOutFailed`) and command monitoring (`monitorCommands: true`) support observability; do not log full commands containing sensitive data.
- Mongoose 9 uses the Node.js driver 7.x line underneath; check its compatibility page for the server version you run.

## 9. Server hardening checklist

- `security.authorization: enabled`; create users per application with roles scoped to a database; avoid `root` and `__system` for applications.
- `net.bindIp` limited to private interfaces; network ACLs or private endpoints; TLS (`net.tls.mode: requireTLS`).
- Disable features you do not use (server-side JavaScript, unused ports); keep the server and drivers patched, since each patch release lists security fixes.
- Enable audit logs where required; redact client log data (`security.redactClientLogData`) when logs may contain sensitive values.
- Encrypt at rest (storage-layer or cloud disk encryption, or Enterprise encrypted storage engine) and encrypt backups.
- Test restore procedures and monitor replica set health; a backup that has never been restored is unverified.
