# Schema Design Patterns

Reference for modeling MongoDB documents: when to embed or reference, the common design patterns, anti-patterns, schema validation with `$jsonSchema` (including the `constraint` level added in 9.0), time series collections and multi-tenant models. Verified against MongoDB Server 9.0.4 and the MongoDB data modeling documentation (2026-10). The pattern names follow the MongoDB documentation and the MongoDB patterns series; "extended reference" is a widely used pattern from that series that is not listed on the current docs pages.

## 1. Embed or reference

| Question | Embed | Reference |
|---|---|---|
| Read together on most requests? | Yes | No, or only sometimes |
| Child count bounded and small? | Yes (tens, not thousands) | No (unbounded or large) |
| Child shared by many parents? | No | Yes |
| Child updated independently and often? | No | Yes |
| Need atomic update of parent and child? | Yes (one-document write) | Needs a transaction |
| Child large (images, long text)? | No | Yes |

Rules of thumb:

- Cardinality one-to-few: embed an array of subdocuments.
- One-to-many (hundreds to thousands): reference from the many side (store the parent id on each child), or embed only a subset (section 3).
- One-to-squillions (logs, events, readings): children in their own collection (or a time series collection) with the parent id; never an array on the parent.
- Many-to-many: store an array of ids on the side that is smaller and bounded, or a link collection when relationships carry attributes.
- Optimize for the dominant read. A write that touches two collections and a read that needs one is usually a good trade.
- Every document has a ceiling of 16 MiB; design far below it. A document that grows over its lifetime (arrays that only append) is a design smell.

## 2. Pattern catalog

### Subset

Keep the working subset in the main document and the rest in another collection.

```js
// products: latest 5 reviews embedded; all reviews in "reviews"
{ _id, tenantId, name, ratingAvg: 4.6, ratingCount: 1873,
  recentReviews: [ { reviewId, author: "Sam", stars: 5, text: "...", at: ISODate("2026-10-12") } /* up to 5 */ ] }
```

Maintain `recentReviews` on write: `$push` with `$each`, `$sort` and `$slice`:

```js
db.products.updateOne(
  { _id: pid, tenantId },
  { $push: { recentReviews: { $each: [review], $sort: { at: -1 }, $slice: 5 } },
    $inc: { ratingCount: 1 } }
)
```

### Extended reference

Copy the few fields of a referenced document that reads need, to avoid a join.

```js
{ _id, tenantId, customerId, customer: { name: "Acme Ltd", tier: "gold" }, totalCents: 4200 }
```

Update copies when the source changes (a background job or change stream) and accept bounded staleness; copy only stable fields.

### Computed

Precompute values that are expensive to derive and read often (totals, counts, averages). Update on write with `$inc`, or recompute periodically. Keep the source data as the truth so the computed field can be rebuilt. The approximation variant keeps counts approximate (for example, update a view counter every Nth event) when exactness is not needed.

### Bucket

Group many small time-ordered records into one document to reduce document and index count.

```js
{ _id, tenantId, sensorId: "s-17", start: ISODate("2026-10-30T10:00:00Z"), end: ISODate("2026-10-30T10:59:59Z"),
  count: 3, sum: 66.9,
  readings: [ { t: 0, v: 21.4 }, { t: 60, v: 22.1 }, { t: 120, v: 23.4 } ] }
```

Cap the bucket (by count or time span) and open a new one when it is full: `updateOne({ sensorId, tenantId, count: { $lt: 200 }, start: hourStart }, { $push: ..., $inc: ..., $setOnInsert: ... }, { upsert: true })`. For pure time series data, prefer a time series collection (section 6), which buckets automatically.

### Outlier

A few documents (a viral post with a million likes) exceed the normal shape. Keep the common design for the 99% and flag the outliers: `hasOverflow: true` plus an overflow collection that code reads only when the flag is set.

### Attribute

Many sparse or varying fields that you need to search together become an array of key/value pairs with one multikey index.

```js
{ _id, name: "Boot", attrs: [ { k: "color", v: "black" }, { k: "size", v: 42 } ] }
db.items.createIndex({ "attrs.k": 1, "attrs.v": 1 })
db.items.find({ attrs: { $elemMatch: { k: "color", v: "black" } } })
```

Use `$elemMatch` so key and value match in the same element. (Wildcard indexes are an alternative for arbitrary dynamic fields.)

### Schema versioning

Add `schemaVersion: 2` to documents. Readers handle old versions (upconvert on read) while a background job migrates; or migrate eagerly with batched `updateMany` and a validator that allows both versions during the transition.

### Document versioning

Keep a history collection of previous versions (`{ docId, version, changedAt, snapshot }`) while the main collection stores only the current document, so the hot path stays small.

### Archive

Move old data to cheaper storage or another collection (`$merge` into an archive collection, then delete by range or drop an old time-partitioned collection); keep recent data in the primary collection with a partial or TTL index strategy.

### Polymorphic and inheritance

Store different shapes of related entities in one collection with a `type` discriminator and shared fields (for example `payments` with `card`, `bank`, `wallet`), so one query covers them. Validate per type with `oneOf` in `$jsonSchema`.

## 3. Anti-patterns

- **Unbounded arrays**: arrays that grow forever slow updates, bloat documents and multikey indexes. Use references, buckets or the subset pattern.
- **Bloated documents**: large rarely-used fields in hot documents increase cache pressure; split them out and project only what is needed.
- **Too many collections for the same shape** (one collection per tenant or per day): metadata and index overhead grows; use one collection with a tenant key (or time series collections), unless isolation requirements demand separate databases.
- **Too many `$lookup`s**: if reads routinely join three collections, the model fights the database; embed or copy fields.
- **Unnecessary indexes**: each index slows writes and consumes RAM; drop those with no use in `$indexStats`.
- **Case-insensitive duplicates and inconsistent types**: pick one type per field (dates as `Date`, ids as `ObjectId`); a validator prevents mixed types that make comparisons and indexes unreliable.
- **Dynamic keys**: using user data as field names (`{ "john@x.com": {...} }`) makes indexing and querying awkward and invites key characters that conflict with operators; use arrays of key/value pairs.

## 4. Schema validation

```js
db.createCollection("orders", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tenantId", "customerId", "status", "totalCents", "createdAt"],
      properties: {
        _id: { bsonType: "objectId" },
        tenantId: { bsonType: "string", minLength: 1 },
        customerId: { bsonType: "string" },
        status: { enum: ["pending", "paid", "cancelled"] },
        totalCents: { bsonType: "number", minimum: 0 },
        createdAt: { bsonType: "date" },
        paidAt: { bsonType: "date" },
        items: {
          bsonType: "array", maxItems: 200,
          items: { bsonType: "object", required: ["sku", "qty"],
                   properties: { sku: { bsonType: "string" }, qty: { bsonType: "number", minimum: 1 } } }
        }
      },
      additionalProperties: false
    }
  },
  validationLevel: "strict",
  validationAction: "error"
})
```

Notes:

- `additionalProperties: false` rejects unlisted fields, including `_id` unless listed; remove it if the schema must tolerate new fields during rollouts.
- Numeric types: the Node.js driver writes integral numbers within the 32-bit range as `int` and all other JavaScript numbers as `double`; use `bsonType: "number"` (any numeric type) unless a specific BSON type is required, and wrap values in `Int32`, `Long` or `Decimal128` from the driver when you need one.
- Levels: `strict` (default) validates all inserts and updates; `moderate` skips updates to existing documents that were already invalid; `constraint` (9.0+) validates all inserts and updates and guarantees that every document is valid, cannot be bypassed with `bypassDocumentValidation`, and requires `validationAction` of `error` or `errorAndLog`.
- Upgrading an existing collection to `constraint`: set the validator and `strict` first, then run `db.runCommand({ collMod: "orders", prepareConstraintValidationLevel: true })`, then `db.runCommand({ collMod: "orders", validationLevel: "constraint", validationAction: "error" })`. MongoDB scans the collection, and the upgrade fails if any existing document is invalid. To change rules later, set the level back to `strict`, change the validator, and upgrade again.
- Validation is a safety net for invariants, not a replacement for application validation and authorization.

## 5. Multi-tenant models

- **Shared collections with a `tenantId` field** (default choice): leading equality field in every index; unique constraints per tenant (`{ tenantId: 1, email: 1 }` unique); tenant in every query and write (see the repository example in SKILL.md). Best resource efficiency; isolation is enforced by code and review, so test it.
- **Database or cluster per tenant**: strong isolation, per-tenant backup and key management, but metadata overhead and operational cost grow with tenant count; suitable for few large or regulated tenants.
- **Hybrid**: shared collections for most tenants, dedicated databases for the largest or regulated ones, routed by a tenant registry.
- Sharded multi-tenant collections: shard key `{ tenantId: 1, _id: 1 }` targets queries to the tenant's chunks; a single very large tenant can create a hot range, so consider a finer second field or isolating that tenant.
- Per-tenant encryption keys with Queryable Encryption or CSFLE data encryption keys (one DEK per tenant) allow cryptographic deletion of a tenant.

## 6. Time series collections

```js
db.createCollection("readings", {
  timeseries: { timeField: "ts", metaField: "meta", granularity: "minutes" },
  expireAfterSeconds: 60 * 60 * 24 * 90      // optional automatic expiry
})
db.readings.insertOne({ ts: new Date(), meta: { tenantId: "acme", sensorId: "s-17" }, value: 21.4 })
```

- `timeField` is required; `metaField` holds labels that rarely change (sensor id, tenant); keep per-measurement data outside the meta field.
- `granularity` (`seconds`, `minutes`, `hours`) hints how data is bucketed; newer versions also allow custom bucketing parameters (`bucketMaxSpanSeconds`, `bucketRoundingSeconds`).
- Secondary indexes on `metaField` subfields and `timeField` are supported; check the time series limitations page for the operations (updates, deletes, transactions) supported by your server version.
- Include the tenant in `metaField` and in queries.
