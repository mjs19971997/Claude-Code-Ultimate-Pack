---
name: mongodb-expert
description: >-
  Designs, queries, secures and tunes MongoDB: document schema design (embedding versus referencing, bucket, computed, subset, extended reference, outlier), compound indexes with the ESR guideline, explain() analysis, aggregation pipelines, transactions and their limits, read and write concerns, change streams, $jsonSchema validation, shard key choice, Queryable Encryption and CSFLE, MongoDB Search and Vector Search, NoSQL operator injection, and Node.js driver connection pooling. Use when modeling collections, creating or reviewing indexes, reading explain output, writing aggregations, building multi-tenant data access, configuring replica sets or sharding, or reviewing MongoDB queries for injection and tenant isolation. Not for relational schema design (use postgresql-expert), caching and data structures (use redis-expert), or full-text search clusters (use elasticsearch-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# MongoDB Expert

This skill covers application-level MongoDB engineering: how to shape documents around access patterns, how to index and verify with `explain()`, how to write safe and efficient queries and aggregations, when to use transactions, change streams and sharding, and how to keep data access secure and tenant-isolated. Examples use the official Node.js driver in TypeScript and `mongosh`. Deep material is in the reference files.

> Verified against MongoDB Server 9.0.4 (general availability 2026-09-28; 8.3.13 is the latest 8.x minor and 8.0.34 the 8.0 patch), MongoDB Node.js driver 7.8.0 (Node.js 20.19+, bson 7), mongosh 2.14.x, Mongoose 9.11.x and PyMongo 4.19 (2026-10).

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

- Covered: schema design, indexes, `explain()`, CRUD and aggregation, transactions, read/write concerns, change streams, schema validation, sharding keys, in-use encryption, Search and Vector Search basics, query injection, and driver configuration.
- Not covered: relational modeling and SQL tuning (postgresql-expert), Redis structures and caching (redis-expert), Elasticsearch clusters (elasticsearch-expert), Prisma schema and client (prisma-expert), generic API security design (api-security-expert), cloud networking and backups (aws-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | Server 9.0 is the current major (9.0.4); 8.0 and 8.3 are still current in many deployments. Check the support policy and the compatibility page of your driver before upgrading |
| Document model | Max BSON document size 16 MiB; data accessed together is stored together; arrays must be bounded |
| Indexes | Max 64 per collection, max 32 fields in a compound index; build with `createIndex`; the `background` option is ignored (all builds use the optimized process since 4.2) |
| ESR | Compound key order: Equality fields, then Sort fields, then Range fields (use ERS when the range is very selective) |
| Transactions | Replica set or sharded cluster only; default lifetime 60 s (`transactionLifetimeLimitSeconds`); 5 ms default lock wait; per-oplog-entry limit 16 MiB |
| Concerns | Default write concern is `majority` for most deployments; default read concern is `local`; use `snapshot` in transactions, `majority` for read-after-write across failover |
| Change streams | Need a replica set or sharded cluster; resume with `resumeAfter`/`startAfter`; `fullDocument: "updateLookup"`; pre-images need collection-level enablement |
| Validation | `$jsonSchema` validators; levels `strict` (default), `moderate`, and `constraint` (new in 9.0, guarantees every document is valid) |
| Sharding | Shard key choice dominates scale: cardinality, frequency, monotonicity, query targeting; `reshardCollection`, `refineCollectionShardKey`, `unshardCollection` exist |
| In-use encryption | Queryable Encryption (equality and range; prefix, suffix and substring are GA in 9.0 after a preview in 8.2/8.3) and CSFLE; QE automatic encryption needs Atlas or Enterprise Advanced, Community supports manual encryption |
| Search | MongoDB Search (`$search`) and Vector Search (`$vectorSearch`) run in Atlas; the `mongot` process for self-managed Community and Enterprise is in Preview |
| Server-side JS | `$where`, `$function`, `$accumulator` were deprecated in 8.0 and re-enabled in 9.0 on a WebAssembly engine; avoid them and consider `security.javascriptEnabled: false` |

## 3. Workflow

1. List the application's queries and writes with frequency and latency targets; list entity relationships and growth rates.
2. Model documents for those access patterns: embed what is read together and bounded; reference what is large, unbounded, shared or updated independently.
3. Define indexes from the query list using ESR, including the tenant key as the leading equality field in multi-tenant collections.
4. Add a `$jsonSchema` validator for the invariants the application relies on.
5. Implement data access behind a repository that injects tenant scoping and builds filters from validated, typed inputs.
6. Verify each query with `explain("executionStats")`: index used, no in-memory sort, keys examined close to documents returned.
7. Choose write and read concerns per operation type; use transactions only for multi-document invariants that cannot be modeled in one document.
8. Plan operations: monitoring, backups with tested restore, index maintenance, and the shard key before the data volume forces it.

## 4. Decision Rules

- Embed when the child is read with the parent, bounded in size, and owned by the parent (address, line items of an order). Reference when the child is unbounded, large, shared by many parents, or updated independently.
- Prefer one document per aggregate that is updated atomically; single-document writes are atomic, which removes most needs for transactions.
- Duplicate small, stable fields to avoid joins (extended reference pattern); accept the update cost when the source changes rarely.
- Use `$lookup` for occasional joins and reporting, not as the hot path of every request; if every read needs a join, remodel.
- Time series data: use a time series collection (`timeseries: { timeField, metaField, granularity }`) before hand-rolling buckets.
- Use a partial index when most queries target a subset (for example `status: "open"`); use a TTL index for expiring data; use a unique compound index including `tenantId` for per-tenant uniqueness.
- Sharding: delay until a single replica set no longer fits storage, working set or write throughput; scale up and add read replicas first. Never shard on a monotonically increasing key (an `ObjectId` or timestamp) alone; use a hashed key or a compound key with a well-distributed prefix.
- Multi-tenant sharding: a compound key `{ tenantId: 1, _id: 1 }` (or a hashed tenant id for many small tenants) keeps a tenant's queries targeted; one huge tenant needs a finer second field.
- Transactions: keep them short, touch few documents, retry on `TransientTransactionError`, and never hold user interaction inside one.
- Pick `w: "majority"` for data that must survive failover; `w: 1` only for loss-tolerant writes. Use `readConcern: "majority"` or causal consistency sessions when a read must see a prior write.
- Full-text needs: simple cases use a text index; relevance-tuned search, facets, fuzzy or semantic search use MongoDB Search and Vector Search, or an external engine (elasticsearch-expert).
- Use the ODM (Mongoose) only if its schema and middleware features are wanted; otherwise the native driver with TypeScript types is simpler and avoids query-casting surprises.

## 5. Coding Standards

- One `MongoClient` per process, created at startup and reused; close it on shutdown. Never create a client per request.
- Type collections: `db.collection<Order>("orders")`. Convert ids with `new ObjectId(id)` after checking `ObjectId.isValid`.
- Build filters from explicitly validated fields. Never pass a parsed request body (or any object with user-controlled keys) as a filter, update or aggregation stage.
- Use update operators (`$set`, `$inc`, `$push`) for partial updates; avoid `replaceOne` for hot documents unless replacing is intended.
- Always bound result sets: `limit`, `projection`, and a deterministic `sort` including `_id` as tiebreaker for pagination.
- Prefer range-based (keyset) pagination (`createdAt < lastSeen`) over large `skip`.
- Name indexes explicitly (`name: "tenant_status_created"`) so migrations are idempotent.
- Use `bulkWrite` / `insertMany` with `ordered: false` for batch loads where order does not matter.
- Use field names in camelCase; store dates as BSON `Date`, money as integer minor units or `Decimal128`, ids as `ObjectId` or UUID (binary subtype 4).
- Handle driver errors by code: duplicate key (11000), `TransientTransactionError` and `UnknownTransactionCommitResult` labels, and `MongoServerSelectionError`.

## 6. Project Structure

```
src/
├── db/
│   ├── client.ts              # single MongoClient, pool options, shutdown hook
│   ├── indexes.ts             # ensureIndexes(): idempotent createIndex calls with names
│   └── validators/            # $jsonSchema per collection, applied by migrations
├── modules/
│   └── orders/
│       ├── orders.types.ts    # TypeScript document types
│       ├── orders.repo.ts     # tenant-scoped data access (the only place that touches the collection)
│       └── orders.service.ts
├── migrations/                # versioned scripts: collMod validators, index changes, backfills
└── test/
    └── integration/           # tests against a real mongod replica set in a container
```

## 7. Design Patterns

- **Embedding vs referencing**: see decision rules; the details and examples are in [references/schema-design-patterns.md](references/schema-design-patterns.md).
- **Subset**: keep the most-used part of a large related set (latest 10 reviews) in the parent and the full set in another collection.
- **Bucket**: group many small time-ordered records (sensor readings) into one document per time window; prefer a time series collection when available.
- **Computed**: store derived values (counters, totals) updated on write or by a scheduled job when reads dominate.
- **Extended reference**: copy a few fields of a referenced document (customer name) into the referencing one.
- **Outlier**: handle the rare document that exceeds normal size with an overflow flag and a separate collection.
- **Schema versioning**: a `schemaVersion` field plus lazy migration on read or a background backfill.
- **Outbox with change streams**: write business data and an outbox document in one transaction, publish from a change stream consumer (microservices-expert covers the broker side).
- **Tenant-scoped repository**: every query, update, delete, aggregation and `$lookup` takes the tenant from the authenticated context (example below).

## 8. Best Practices

- Model first from queries, then validate the model with realistic data volumes and `explain()`.
- Keep documents well below 16 MiB; large arrays that grow without bound are the most common design failure.
- Use `$jsonSchema` validation with `validationAction: "error"` for invariants; add `additionalProperties: false` only when you list `_id` and every field.
- Create indexes in a deployment step, not lazily on first request; build on the primary with the default process and monitor with `db.currentOp()`.
- Use projections to return only needed fields; covered queries (all fields in the index) avoid fetching documents.
- Use `$set` with dotted paths or `arrayFilters` for in-place array element updates rather than read-modify-write in the client.
- Add `maxTimeMS` (or the driver's `timeoutMS`, which is experimental in the Node.js driver) to queries that serve user requests.
- Review slow query logs and the profiler periodically; remove unused indexes (`$indexStats`) because each index costs every write.
- Keep the replica set topology in the connection string (`mongodb+srv://` for Atlas) so the driver follows failover.

## 9. Performance

- The target for a query: `IXSCAN` in the winning plan, `totalKeysExamined` close to `nReturned`, `totalDocsExamined` close to `nReturned` (or 0 for covered), and no `SORT` stage on large inputs.
- Leading equality fields first, then the sort, then range (ESR). A `SORT` stage in the plan means the index does not provide the order; a blocking in-memory sort over 100 MB fails unless it can spill.
- In aggregation, put `$match` and `$sort` (on indexed fields) first so they use indexes, project early, and use `$limit` before expensive stages when semantics allow.
- Version 9.0 adds a per-operation memory limit (default: the greater of 1 GB and 20% of the memory available to the server process); the older 100 MB per-stage limit and spill-to-disk behavior are unchanged.
- Avoid unanchored or case-insensitive `$regex` on large collections; use a collation-aware index, a text index, or Search.
- Avoid `$lookup` against unindexed foreign fields; make the `foreignField` (or the pipeline `$match` fields) indexed.
- Batch writes and use unordered bulk operations; keep transactions small.
- Connection pool: the Node.js driver defaults to `maxPoolSize` 100 and `minPoolSize` 0 per server; size it against the server's connection limit multiplied by the number of application instances, and keep `maxIdleTimeMS` below firewall idle timeouts.
- Working set (indexes plus hot documents) should fit in RAM; add memory or shard before the storage cache thrashes.

## 10. Security

- Enable authentication and authorization (`security.authorization: enabled`), use SCRAM or x.509 / cloud IAM, bind to private interfaces, require TLS, and give each application a user with a least-privilege role on its database. A `mongod` reachable from the internet without authentication is a standing incident.
- NoSQL operator injection: if request JSON reaches a filter unvalidated, `{"email": {"$ne": null}, "password": {"$ne": null}}` matches any user. Validate each field as a string (or number, boolean) with a schema validator before building the filter, and reject objects where scalars are expected. Do not use `JSON.parse` output as a filter.
- Never pass user text to `$where`, `$function` or `$accumulator`; they execute JavaScript on the server (sandboxed on a WebAssembly engine in 9.0, still a risk and a performance cost). Turn server-side JavaScript off with `security.javascriptEnabled: false` if unused.
- Escape user text used in `$regex` (and prefer anchored, indexed prefix patterns); an unescaped pattern can be a denial-of-service vector.
- With Mongoose, set `sanitizeFilter` and keep `strictQuery` behavior in mind; Mongoose does not make arbitrary objects safe to use as filters.
- Tenant isolation applies to writes as well as reads: every `insertOne` sets `tenantId` from the authenticated context (ignoring any client-supplied value), every `updateOne`, `updateMany`, `deleteOne`, `deleteMany`, `findOneAndUpdate` and each `bulkWrite` operation includes `tenantId` in its filter, and every `$lookup`, `$unionWith`, `$merge` and `$out` stays inside the tenant. Add a unique index on `{ tenantId, naturalKey }`.
- Encrypt sensitive fields in the client with Queryable Encryption or CSFLE when the database operator should not see plaintext; protect the customer master key in a KMS and restrict the key vault.
- Encrypt data at rest and in backups, restrict who can run `$out`/`$merge` and read the oplog, and enable auditing where compliance requires it.
- Keep connection strings and KMS credentials in a secret manager; never in source control or client-side bundles.

## 11. Testing

- Run integration tests against a real `mongod` started as a single-node replica set (transactions and change streams need one), in a container or with an in-memory test server; avoid mocking the driver for query logic.
- Seed realistic volumes for performance tests; assert query shape with `explain()` (stage names, `totalDocsExamined`) so index regressions fail CI.
- Test validators with valid and invalid documents; test migrations on a copy of production-shaped data.
- Test tenant isolation negatively: with documents for tenants A and B, every repository method called as A must not read, update or delete B's documents, including `updateMany`, `deleteMany`, aggregations and `$lookup`.
- Test injection: send `{ "$ne": null }` and `{ "$gt": "" }` objects where strings are expected and assert a validation error.
- Test transaction retry: inject a `TransientTransactionError` (or use a failpoint) and assert the callback is idempotent when re-run.

## 12. Review Checklist

- [ ] Each collection's documents are bounded; no unbounded arrays; documents stay far below 16 MiB.
- [ ] Every query has a supporting index justified by ESR; `explain()` output was checked.
- [ ] Indexes are named and created by migrations; no `background` option; no redundant prefixes.
- [ ] Filters are built from validated typed values; no request object reaches a filter, update or pipeline; no `$where`.
- [ ] Every read and write (insert, update, delete, bulk, `$lookup`, `$merge`) is scoped by tenant.
- [ ] Write concern `majority` for important data; read concern chosen deliberately.
- [ ] Transactions are short, retried on transient errors, and only used where multi-document atomicity is required.
- [ ] A `$jsonSchema` validator covers required fields and types.
- [ ] Pagination is keyset-based with a deterministic sort.
- [ ] Authentication, TLS and least-privilege users are configured; secrets are not in the repository.
- [ ] Shard key (if sharded) has high cardinality, no monotonic prefix, and matches the main query filter.
- [ ] One shared `MongoClient`; pool and timeout options set.

## 13. Production Notes

- Run at least a three-member replica set across failure domains; use `retryWrites` and `retryReads` (on by default in modern drivers) and `w: "majority"`.
- Upgrade one major at a time through the documented path, set the feature compatibility version only after verifying the new binaries, and read the compatibility changes of the target release (9.0 changes include BSON validation on by default, a per-operation memory limit, indexed queries that can fail with `QueryKilledError` when a field becomes multikey mid-query, change streams that resume after an election changes the node's role, and a limit on concurrent multi-document transactions, default 10,000).
- Monitor replication lag, oplog window, cache usage, connections, queued operations, slow queries, index usage and disk. A change stream consumer needs an oplog window longer than its worst-case downtime.
- Back up with snapshots or `mongodump`-based tools and test restores regularly; document RPO and RTO.
- Index builds on large collections: schedule, watch with `db.currentOp()`, and expect extra load; for sharded clusters build before data grows.
- Use the Stable API (`serverApi: { version: "1", strict: true }`) when you want server upgrades not to change command behavior for the application.
- Transactions across shards cost more than on a single shard; design the shard key so common transactions stay on one shard.

## 14. Examples

Tenant-scoped repository with typed, validated inputs. Every operation includes the tenant, including update and delete, and the tenant on insert comes from the context, not from the caller's data.

```ts
import { ObjectId, type Collection } from "mongodb";

export type OrderStatus = "pending" | "paid" | "cancelled";
export interface Order {
  _id: ObjectId;
  tenantId: string;
  customerId: string;
  status: OrderStatus;
  totalCents: number;
  createdAt: Date;
  paidAt?: Date;
}
const STATUSES: readonly OrderStatus[] = ["pending", "paid", "cancelled"];

function oid(id: string): ObjectId {
  if (!ObjectId.isValid(id)) throw new Error("invalid id");
  return new ObjectId(id);
}

export class TenantOrders {
  constructor(private readonly col: Collection<Order>, private readonly tenantId: string) {}

  async create(input: { customerId: string; totalCents: number }) {
    if (typeof input.customerId !== "string" || !Number.isInteger(input.totalCents) || input.totalCents < 0) {
      throw new Error("invalid input");
    }
    const doc = {
      customerId: input.customerId,
      totalCents: input.totalCents,
      status: "pending" as const,
      createdAt: new Date(),
      tenantId: this.tenantId,            // set last, from the authenticated context
    };
    const r = await this.col.insertOne(doc);
    return r.insertedId;
  }

  findById(id: string) {
    return this.col.findOne({ _id: oid(id), tenantId: this.tenantId });
  }

  async markPaid(id: string) {
    const r = await this.col.updateOne(
      { _id: oid(id), tenantId: this.tenantId, status: "pending" },     // tenant and state guard on the write
      { $set: { status: "paid", paidAt: new Date() } },
    );
    return r.modifiedCount === 1;
  }

  async remove(id: string) {
    const r = await this.col.deleteOne({ _id: oid(id), tenantId: this.tenantId });
    return r.deletedCount === 1;
  }

  list(status: string, before?: Date, limit = 50) {
    if (!STATUSES.includes(status as OrderStatus)) throw new Error("invalid status");  // rejects objects like { $ne: null }
    return this.col
      .find({ tenantId: this.tenantId, status: status as OrderStatus, ...(before ? { createdAt: { $lt: before } } : {}) })
      .sort({ createdAt: -1, _id: -1 })
      .limit(Math.min(limit, 200))
      .toArray();
  }
}
```

Index by ESR, verify with explain, and aggregate with a tenant-safe `$lookup` (mongosh):

```js
// Equality: tenantId, status. Sort: createdAt. Range: totalCents.
db.orders.createIndex(
  { tenantId: 1, status: 1, createdAt: -1, totalCents: 1 },
  { name: "tenant_status_created_total" }
)

const q = { tenantId: "acme", status: "paid", totalCents: { $gte: 5000 } }
const plan = db.orders.find(q).sort({ createdAt: -1 }).limit(20).explain("executionStats")
// Expect IXSCAN on tenant_status_created_total, no SORT stage,
// executionStats.totalKeysExamined close to nReturned.

db.orders.aggregate([
  { $match: { tenantId: "acme", status: "paid", createdAt: { $gte: ISODate("2026-10-01"), $lt: ISODate("2026-11-01") } } },
  { $group: { _id: { $dateTrunc: { date: "$createdAt", unit: "day" } }, revenueCents: { $sum: "$totalCents" }, orders: { $sum: 1 } } },
  { $sort: { _id: 1 } }
])

db.orders.aggregate([
  { $match: { tenantId: "acme", status: "pending" } },
  { $limit: 100 },
  { $lookup: {
      from: "customers",
      let: { cid: "$customerId", t: "$tenantId" },
      pipeline: [
        { $match: { $expr: { $and: [ { $eq: ["$_id", "$$cid"] }, { $eq: ["$tenantId", "$$t"] } ] } } },
        { $project: { name: 1 } }
      ],
      as: "customer" } }
])
```

Transaction with the convenient API and a resumable change stream consumer (Node.js driver 7.x):

```ts
import { MongoClient, type ResumeToken } from "mongodb";

const client = new MongoClient(process.env.MONGODB_URI!, { maxPoolSize: 50, serverSelectionTimeoutMS: 5000 });

export async function transfer(tenantId: string, from: string, to: string, cents: number) {
  await client.withSession((session) =>
    session.withTransaction(
      async (s) => {
        const accounts = client.db("bank").collection<{ _id: string; tenantId: string; balanceCents: number }>("accounts");
        const debit = await accounts.updateOne(
          { _id: from, tenantId, balanceCents: { $gte: cents } },
          { $inc: { balanceCents: -cents } },
          { session: s },
        );
        if (debit.modifiedCount !== 1) throw new Error("insufficient funds");     // aborts the transaction
        const credit = await accounts.updateOne({ _id: to, tenantId }, { $inc: { balanceCents: cents } }, { session: s });
        if (credit.modifiedCount !== 1) throw new Error("unknown destination");
      },
      { readConcern: { level: "snapshot" }, writeConcern: { w: "majority" } },
    ),
  );
}

export async function consume(loadToken: () => Promise<ResumeToken | undefined>, saveToken: (t: ResumeToken) => Promise<void>) {
  const token = await loadToken();
  const stream = client.db("shop").collection("orders").watch(
    [{ $match: { operationType: { $in: ["insert", "update"] } } }],
    { fullDocument: "updateLookup", ...(token ? { resumeAfter: token } : {}) },
  );
  for await (const change of stream) {
    await handleIdempotently(change);       // at-least-once: handler must tolerate repeats
    await saveToken(change._id);            // persist after handling
  }
}
```

If resuming fails because the token has fallen out of the oplog window (`ChangeStreamHistoryLost`), rebuild state from a collection scan and start a new stream.

## 15. Common Mistakes

- **Unbounded arrays** (comments, events pushed forever): documents grow toward 16 MiB and updates slow down. Use references, buckets or the subset pattern.
- **Indexing every field**: each index slows writes and uses RAM. Index for real queries and review `$indexStats`.
- **Wrong compound order**: range before sort produces an in-memory sort. Apply ESR and verify with `explain()`.
- **Teaching or using `background: true`**: ignored since 4.2; all builds use the optimized process.
- **Request body used as filter**: `{ $ne: null }` injection. Validate scalar types per field.
- **`$where` or `$function` with user input**: server-side code execution path; avoid.
- **Tenant filter on reads only**: `updateOne({ _id })` and `deleteOne({ _id })` without `tenantId` let one tenant change another's data. Scope every operation.
- **Monotonic shard key** (`_id`, timestamp): all inserts hit one shard. Hash it or add a distributed prefix.
- **`skip` for deep pagination**: cost grows with the offset. Use keyset pagination.
- **Long or large transactions**: abort after 60 s by default and strain the cache. Remodel into single-document updates or shorten.
- **`w: 1` for critical writes**: acknowledged writes can roll back after failover. Use `majority`.
- **A new `MongoClient` per request**: exhausts connections. Share one client.
- **Assuming `$lookup` is a join engine**: it is per-document and slow without indexes; denormalize or precompute.
- **Resuming change streams from stale tokens** without handling `ChangeStreamHistoryLost`: the consumer crashes in a loop.
- **Skipping validation**: without a validator, application bugs write malformed documents that every reader must tolerate.

## 16. References

- [references/schema-design-patterns.md](references/schema-design-patterns.md): embedding versus referencing rules, pattern catalog (bucket, computed, subset, extended reference, outlier, attribute, schema versioning, archive), anti-patterns, schema validation with `$jsonSchema` and the `constraint` level, multi-tenant models, time series.
- [references/indexing-and-aggregation.md](references/indexing-and-aggregation.md): index types and properties, ESR with worked explain output, index builds, aggregation stages and optimization, `$lookup`, `$merge`, windows, memory limits.
- [references/operations-and-security.md](references/operations-and-security.md): transactions, read and write concerns, change streams, sharding key selection, Queryable Encryption and CSFLE, Search and Vector Search, injection defenses, driver pooling and timeouts.
- Official docs: https://www.mongodb.com/docs/manual/ , https://www.mongodb.com/docs/drivers/node/current/ , https://www.mongodb.com/docs/manual/release-notes/ , https://www.mongodb.com/docs/manual/data-modeling/ , https://www.mongodb.com/docs/manual/core/queryable-encryption/
