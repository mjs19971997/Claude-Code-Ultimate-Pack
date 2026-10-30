# Indexing and Aggregation

Reference for MongoDB index design (types, properties, the ESR guideline, covered queries), reading `explain()` output, index builds, and aggregation pipelines (stage order, `$lookup`, `$merge`, windows, memory limits). Verified against MongoDB Server 9.0.4 manual and Node.js driver 7.8.0 (2026-10). Shell examples run in `mongosh`.

## 1. Index types and properties

| Type | Use | Notes |
|---|---|---|
| Single field | Equality and range on one field, sort on one field | `{ createdAt: -1 }` |
| Compound | Queries on several fields; sort | Up to 32 fields; field order matters (ESR) |
| Multikey | Fields holding arrays | Automatic when an indexed field contains an array; at most one array field per compound index entry |
| Text | Simple relevance search | One text index per collection; for richer search use MongoDB Search or Elasticsearch |
| Hashed | Equality lookups, hashed sharding | No range queries |
| Geospatial (`2dsphere`, `2d`) | Location queries | Use GeoJSON with `2dsphere` |
| Wildcard | Unpredictable field names | Not a replacement for planned compound indexes |
| Clustered collection | Documents stored in `_id` order | Specify at collection creation; check limitations |
| Vector / Search indexes | `$vectorSearch`, `$search` | Managed by Atlas or `mongot`, not by `createIndex` |

Properties:

- **Unique**: enforces uniqueness; for multi-tenant data use a compound unique index that includes `tenantId`.
- **Partial** (`partialFilterExpression`): indexes only matching documents; the query must include the filter condition to use it. Combine with unique to enforce uniqueness only among active rows.
- **Sparse**: skips documents missing the field; prefer partial indexes, which are more expressive.
- **TTL** (`expireAfterSeconds` on a date field): a background task deletes expired documents; deletion is not instantaneous.
- **Hidden**: makes an index invisible to the planner without dropping it, to test the effect of removing it.
- **Collation**: an index with a collation serves only queries with the same collation (for case-insensitive search).
- Limits: 64 indexes per collection, 32 fields per compound index.

```js
// per-tenant uniqueness, only for non-deleted users
db.users.createIndex(
  { tenantId: 1, email: 1 },
  { unique: true, name: "tenant_email_unique", partialFilterExpression: { deletedAt: { $exists: false } } }
)
// expire sessions 24h after lastSeen
db.sessions.createIndex({ lastSeen: 1 }, { expireAfterSeconds: 86400, name: "sessions_ttl" })
```

## 2. The ESR guideline

Order compound index fields as **E**quality, **S**ort, **R**ange.

- Equality: exact matches (`tenantId`, `status`). All equality fields precede sort and range fields, in any relative order. Place the most selective, most commonly present field in front when queries sometimes omit others.
- Sort: fields in the `sort()` with the same direction pattern as the index (or exactly reversed). Sort fields before range fields let the index return results in order without a blocking `SORT` stage.
- Range: `$gt`, `$gte`, `$lt`, `$lte`, `$in` on many values, `$ne`, `$regex` prefix. Range predicates scan an interval and do not preserve the order of later fields.
- ERS variant: if the range predicate is highly selective (it eliminates most documents), putting the range before the sort can be faster even though it requires an in-memory sort of a small set. Measure with `explain()`.
- A sort on a non-prefix subset of an index works only if the query has equality conditions on all the preceding keys.
- `$in` with several values behaves like multiple equalities followed by a merge sort; with a sort on a later field it can still require a `SORT_MERGE`. Check the plan.

Worked example:

```js
// Query: tenant's paid orders over 5000, newest first
db.orders.find({ tenantId: "acme", status: "paid", totalCents: { $gte: 5000 } }).sort({ createdAt: -1 })
// ESR index: E = tenantId, status; S = createdAt; R = totalCents
db.orders.createIndex({ tenantId: 1, status: 1, createdAt: -1, totalCents: 1 }, { name: "tenant_status_created_total" })
```

Redundancy: an index on `{ a: 1, b: 1 }` already serves queries on `a`; drop a separate `{ a: 1 }` index (verify with `$indexStats` and `hint()` first).

## 3. Reading explain output

```js
db.orders.find(q).sort({ createdAt: -1 }).explain("executionStats")
```

Verbosity: `queryPlanner` (plan only), `executionStats` (runs the winning plan and returns counts), `allPlansExecution` (also the rejected candidates). The plan tree appears under `queryPlanner.winningPlan`; with the slot-based execution engine the classic stage tree may be nested under `queryPlan`.

| Field or stage | What to look for |
|---|---|
| `IXSCAN` | An index is used; check `indexName`, `indexBounds` (tight bounds on every key means good ESR fit) |
| `COLLSCAN` | Full collection scan; acceptable only for tiny collections or rare admin queries |
| `FETCH` | Documents are read; absent in a covered query |
| `SORT` / blocking sort | Order not provided by the index; large inputs risk memory limits |
| `SORT_MERGE` | Merge of ordered index scans (for `$in`) |
| `executionStats.nReturned` | Documents returned |
| `totalKeysExamined` | Index entries scanned; should be close to `nReturned` |
| `totalDocsExamined` | Documents read; close to `nReturned`, or 0 for covered queries |
| `executionTimeMillis` | Total time |

Rules: keys examined much larger than returned means the index leaves work to a later filter (wrong order or missing field); docs examined larger than keys examined means a residual filter on non-indexed fields. Use `hint({ name })` in tests to compare candidate indexes. In 9.0, classic-engine explain also reports `expressionEvaluationPeakMemoryBytes` for some stages at `executionStats` verbosity.

Covered query: the filter and projection use only indexed fields and exclude `_id` unless it is in the index.

```js
db.orders.find({ tenantId: "acme", status: "paid" }, { _id: 0, tenantId: 1, status: 1, createdAt: 1 }).hint("tenant_status_created_total")
```

## 4. Index builds and maintenance

- Use `createIndex`. Builds use an optimized process that takes an exclusive lock on the collection only briefly at the start and end; reads and writes proceed in between. The old `background` option is ignored and should not be written in new code.
- On replica sets and sharded clusters, builds run on all data-bearing members; the commit quorum (`commitQuorum`) controls how many voting members must finish before the index is marked ready. Rolling builds are a manual procedure for very large collections; consult the rolling index build documentation.
- Watch progress with `db.currentOp({ "command.createIndexes": { $exists: true } })`.
- Removing an index: first hide it (`db.coll.hideIndex("name")`), observe for a full traffic cycle, then drop.
- Usage statistics: `db.coll.aggregate([{ $indexStats: {} }])` lists operations per index since restart; reset on restart, so observe long enough.
- Use migrations or an `ensureIndexes` step with explicit names; `createIndex` with the same name and different options errors, which flags drift.
- Memory: indexes compete with data for cache; large, rarely used indexes cost write throughput and RAM.

## 5. Aggregation pipelines

A pipeline is an ordered list of stages. The optimizer reorders some stages, but write the pipeline in the efficient order.

Guidelines:

- Start with `$match` (and `$sort`) on indexed fields so an index narrows the input; `$match` on the tenant first. `$search` and `$vectorSearch` must be the first stage of a pipeline.
- Reduce width early with `$project` / `$unset` (or let the optimizer infer dependencies) and reduce rows with `$limit` after `$sort` (a `$sort` + `$limit` pair is executed as a top-k sort with bounded memory).
- `$group` accumulators run in memory per stage (limit 100 MB per stage by default; stages can spill to disk; `allowDiskUseByDefault` is true by default). From 9.0 a per-operation memory limit also applies (default: the greater of 1 GB and 20% of memory available to the server process), and exceeding it fails the operation with `ExceededMemoryLimit`.
- Each document passing between stages is limited to 16 MiB; `$push`/`$addToSet` in `$group` over unbounded data can exceed it.
- `$unwind` multiplies documents; use `$filter`, `$map` and `$reduce` array expressions when you do not need rows.
- `$facet` runs sub-pipelines on the same input, cannot use indexes inside the facets, and its output is one document limited to 16 MiB; use separate queries when large.
- Time bucketing: `$dateTrunc`, `$dateAdd`, `$dateDiff`; ranking and running totals: `$setWindowFields`; gap filling: `$densify` and `$fill`; combining collections: `$unionWith`.

### `$lookup`

```js
// Equality join: index the foreign field
{ $lookup: { from: "customers", localField: "customerId", foreignField: "_id", as: "customer" } }

// Pipeline form with extra conditions; keep tenant isolation inside the sub-pipeline
{ $lookup: {
    from: "invoices",
    let: { oid: "$_id", t: "$tenantId" },
    pipeline: [
      { $match: { $expr: { $and: [ { $eq: ["$orderId", "$$oid"] }, { $eq: ["$tenantId", "$$t"] } ] } } },
      { $project: { number: 1, totalCents: 1 } }
    ],
    as: "invoices" } }
```

- Index the foreign collection on the fields used in the join (`invoices: { tenantId: 1, orderId: 1 }`).
- `$lookup` runs per input document; limit the input first. Follow with `$unwind` only if you need rows.
- In sharded clusters, joined collections may be sharded, with performance caveats; check the `$lookup` documentation for your version.

### Materializing results

```js
db.orders.aggregate([
  { $match: { tenantId: "acme", status: "paid" } },
  { $group: { _id: { tenantId: "$tenantId", day: { $dateTrunc: { date: "$createdAt", unit: "day" } } },
              revenueCents: { $sum: "$totalCents" } } },
  { $merge: { into: "daily_revenue", on: "_id", whenMatched: "replace", whenNotMatched: "insert" } }
])
```

- `$merge` upserts into a collection (it can write to a different database) and requires a unique index on the `on` fields (`_id` by default). Use it for incremental summaries; `$out` replaces the whole target collection.
- Restrict who may run `$merge` and `$out` with roles, and keep the target inside the same tenant scope.

### Window functions

```js
db.orders.aggregate([
  { $match: { tenantId: "acme", status: "paid" } },
  { $setWindowFields: {
      partitionBy: "$customerId",
      sortBy: { createdAt: 1 },
      output: { runningTotalCents: { $sum: "$totalCents", window: { documents: ["unbounded", "current"] } } } } }
])
```

## 6. Driver usage

- `collection.aggregate(pipeline, { maxTimeMS: 5000, allowDiskUse: true })` returns a cursor; iterate with `for await` or `toArray()` for small results.
- Build pipelines from constants and validated values only. Never splice user-supplied objects into a stage; a `$`-prefixed key in user JSON can change the stage's meaning.
- Use cursor `batchSize` for large streams and close cursors (`await cursor.close()`) when stopping early.
- Pagination: keyset on the index (`{ createdAt: { $lt: lastCreatedAt } }` plus `_id` tiebreaker); `skip` costs grow with the offset.
- For `find` with `sort`, the sort must be deterministic: add `_id` as the last sort key.
