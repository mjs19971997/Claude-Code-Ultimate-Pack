---
name: elasticsearch-expert
description: >-
  Designs, queries, secures and operates Elasticsearch 9.x for search and analytics: explicit mappings (keyword versus text, multi-fields), analyzers, Query DSL (bool, filter context), ES|QL, aggregations, search_after pagination with point in time, data streams and index lifecycle, shard sizing, reindex with aliases for zero-downtime mapping changes, bulk indexing, vector search (dense_vector, kNN, semantic_text, hybrid retrievers) and security (API keys, TLS, no browser access). Use when writing mappings or queries, tuning relevance or performance, planning index lifecycle, loading data, or reviewing Elasticsearch client code with the official JavaScript or Python clients. Not for OpenSearch-specific APIs (a fork with diverging APIs), MongoDB Search (use mongodb-expert), or Redis search features (use redis-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Elasticsearch Expert

This skill covers building search and analytics on Elasticsearch: modeling documents with explicit mappings, writing efficient and safe queries, paginating correctly, managing index lifecycle and shard sizes, changing mappings without downtime, ingesting in bulk, adding vector and hybrid search, and keeping the cluster secure and tenant-isolated. Examples use the REST API (Kibana Console syntax) and the official JavaScript client. Deep material is in the reference files.

> Verified against Elasticsearch 9.5.5 (9.4.8 is the previous minor; 8.19.23 is the latest 8.x), `@elastic/elasticsearch` 9.5.1 (Node.js 22+), `elasticsearch` Python client 9.5.1 (Python 3.10+), and OpenSearch 3.9.0 as a separate fork whose APIs differ (2026-10).

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

- Covered: mappings and analysis, Query DSL, ES|QL, aggregations, pagination, templates, data streams and lifecycle, shard sizing, reindex and aliases, bulk indexing, vector and hybrid search, security and tenant isolation, and the official JS and Python clients.
- Not covered: Kibana dashboards and Elastic Observability or Security solutions, Logstash and Beats pipelines, OpenSearch-specific features (the fork has different APIs, client packages and security plugins), cloud networking and deployment (aws-expert, kubernetes-expert), MongoDB Search (mongodb-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | Server 9.5.x current; client major version should match the server major (client 9 for server 9, client 8 for server 8). OpenSearch forked from Elasticsearch 7.10 and has diverged: do not mix clients or API assumptions |
| Mappings | Define explicitly; a field type cannot be changed in place. `text` is analyzed for full-text search, `keyword` is exact match, sort and aggregation; dynamic string mapping creates `text` plus a `.keyword` subfield with `ignore_above: 256` |
| Query DSL | `bool` with `must`/`should` (scored) and `filter`/`must_not` (unscored, cacheable); `match`, `term`, `range`, `multi_match`, `nested` |
| ES\|QL | Piped query language run with `POST /_query`; generally available in the stack, with individual commands tagged preview or GA in the docs; supports `params` for safe values and a Query DSL `filter` |
| Pagination | `from`/`size` limited to 10,000 hits (`index.max_result_window`); use `search_after` with a point in time (PIT) for deep paging; scroll is no longer recommended for deep pagination |
| Lifecycle | Data streams plus ILM or data stream lifecycle for time series; rollover by `max_primary_shard_size` |
| Shards | Aim for 10 GB to 50 GB per shard and under 200 million documents per shard; avoid oversharding |
| Zero downtime | Versioned indices (`orders-v1`, `orders-v2`), an alias for reads and writes, `_reindex`, atomic `_aliases` swap |
| Vector search | `dense_vector` (default index type for float vectors: `int8_hnsw` in 9.0; from 9.1 `bbq_hnsw` at 384+ dimensions and `int8_hnsw` below; 9.4+ defaults to `bbq_disk` when the license allows), `knn` query and retriever, `semantic_text` (GA since 9.0), RRF retriever for hybrid |
| Security | Security enabled by default on self-managed 8.0+ with generated TLS certificates and an `elastic` password; anonymous requests are rejected by default; API keys for applications |
| Clients | JS `@elastic/elasticsearch` 9.x (top-level request params, `client.helpers.bulk`); Python `elasticsearch` 9.x (keyword args, `helpers.bulk`) |

## 3. Workflow

1. List search use cases: fields searched, filters, sorts, facets, freshness, volume, retention, and tenant model.
2. Design the document: one flat, denormalized document per searchable entity; avoid joins (`nested` only when array elements must match together).
3. Write explicit mappings with `dynamic: "strict"` (or `false`), choosing `keyword`, `text`, numeric and `date` types deliberately; add multi-fields only where both behaviors are needed.
4. Define analyzers from `_analyze` experiments with real text; keep index and search analyzers consistent unless doing autocomplete.
5. Create an index template (and a data stream for time series), an alias for reads and writes, and a lifecycle policy.
6. Index with the bulk API (or helper), then tune: filters in filter context, `_source` filtering, `track_total_hits`, pagination strategy.
7. Measure with the Profile API, slow log and realistic data; adjust shard count and size before data grows.
8. Plan mapping evolution: new versioned index, reindex, alias swap.
9. Secure: TLS, API keys with least privilege, backend-only access, tenant scoping on reads and writes.

## 4. Decision Rules

- Use `keyword` for ids, enums, tags, emails and anything filtered, sorted or aggregated exactly; use `text` for prose searched by words; use both through a multi-field when you need both (`title` as `text` with `title.raw` as `keyword`).
- Numbers that are identifiers (zip codes, phone numbers) are `keyword`, not numeric; numeric types are for range queries and math.
- `dynamic: "strict"` for application indices so unexpected fields fail loudly; `dynamic: false` to store but not index unknown fields; leave `true` only for exploratory logs, and cap `index.mapping.total_fields.limit` (default 1000).
- Use `flattened` for large sets of arbitrary keys; use `nested` only when you must query an object array with per-element correlation (it costs more); otherwise flatten.
- Put every non-scoring condition in `filter` (tenant, status, ranges); only the relevance part belongs in `must`/`should`.
- Search a user's text with `match`, `multi_match` or `simple_query_string`; use `query_string` only on trusted input because its syntax exposes fields, wildcards and regular expressions.
- Pagination: `from`/`size` for the first few pages; `search_after` with PIT for exports and deep paging; `composite` aggregation to page through buckets.
- Time series, logs, events: a data stream with rollover; delete old data by dropping indices, not by delete-by-query.
- Mutable documents with a fixed key set: regular index behind an alias; updates are reindex operations internally, so avoid very high update rates on large documents.
- Primary shard count: choose from expected index size (target 10 to 50 GB per shard); replicas for availability and read throughput (at least 1 in production); change primary count only by reindex, split or shrink.
- Vector search: use `semantic_text` when you want Elasticsearch to manage embeddings and chunking through an inference endpoint; use `dense_vector` with your own embeddings when you control the model; combine lexical and vector with the RRF retriever for hybrid search.
- ES|QL for analytics and ad hoc exploration; Query DSL for application search with scoring features, highlighting and aggregations you already rely on.
- If the same data must be transactional or relational, keep the source of truth in a database and treat Elasticsearch as a rebuildable index.

## 5. Coding Standards

- One client instance per process; configure the node URL, API key, and the CA certificate; never disable certificate verification.
- Use the top-level request parameters of the 8/9 clients (`client.search({ index, query, size })`), not the removed `body` wrapper; check the client docs for the exact signature of the helper you use.
- Pass user input only as values: `match.query`, `term.value`, ES|QL `params`. Never concatenate user text into an ES|QL string or build DSL from raw user JSON.
- Always set `size`, `_source` includes (or `fields`), `timeout`, and `track_total_hits` appropriate to the use case.
- Use aliases in application code (`orders`), not concrete index names (`orders-v3`).
- Generate document ids deliberately: natural ids (tenant-prefixed) for idempotent upserts, auto ids for append-only logs.
- Check bulk responses per item: the HTTP status is 200 even when items fail; read `errors` and each item's `status`.
- Name indices, templates and pipelines with a convention (`<domain>-<entity>-v<N>`, `<domain>-<entity>@template`).
- Keep mapping, template and ILM definitions in version control and apply them with a migration step.

## 6. Project Structure

```
search/
├── mappings/
│   ├── orders.v1.json         # settings + mappings for a versioned index
│   └── orders.v2.json
├── templates/
│   └── logs.template.json     # composable index template for data streams
├── lifecycle/
│   └── logs.ilm.json
├── src/
│   ├── client.ts              # Elasticsearch client factory (API key, CA, timeouts)
│   ├── indexer.ts             # bulk helper, id and tenant stamping
│   ├── queries/               # query builders: typed inputs, tenant filter always applied
│   └── migrate.ts             # create vN+1, reindex, verify, swap alias
└── test/
    └── integration/           # tests against a disposable single-node container
```

## 7. Design Patterns

- **Versioned index plus alias**: applications read and write through `orders`; `orders-v1` and `orders-v2` are implementation details swapped atomically.
- **Data stream per signal**: append-only events in `logs-<app>-<env>`; rollover by size and age; delete by lifecycle.
- **Denormalized document**: copy needed fields from related entities at index time; reindex when the source changes (event-driven).
- **Multi-fields**: `text` for search plus `keyword` for sort/aggregate; `search_as_you_type` or an edge n-gram analyzer for autocomplete.
- **Tenant scoping**: a mandatory `filter` on `tenantId` in every query builder, tenant-prefixed document ids, tenant stamped server-side at index time, and the same filter on update/delete by query. Filtered aliases per tenant help for search but are not applied when getting a document by id.
- **Hybrid retrieval**: lexical `standard` retriever plus `knn` retriever combined by `rrf`, with the tenant filter inside each child.
- **Dual-read migration**: during a rebuild, write to both indices (or replay from the source) before swapping the alias.
- **Search as projection**: build the index from database change events with idempotent upserts; keep a full rebuild job.
- Detailed mapping and analysis recipes: [references/mappings-and-analysis.md](references/mappings-and-analysis.md). Query, relevance and vector recipes: [references/search-and-relevance.md](references/search-and-relevance.md).

## 8. Best Practices

- Prefer `filter` context for exact conditions: not scored, cached, and faster.
- Use `fields` or `_source` filtering to fetch only needed data; avoid returning large `_source` for list pages.
- Use `search_after` with a unique tie-breaker (PIT adds `_shard_doc` implicitly) so pages are stable.
- Use `refresh=false` (default) during indexing; use `refresh=wait_for` only when a user must see their own write immediately.
- Limit aggregation cost: set `size` on `terms`, use `composite` for paging buckets, avoid high-cardinality `terms` on large ranges, accept approximate `cardinality`.
- Highlight and suggest only where the UI needs them.
- Run `_analyze` against the actual analyzer for sample text before shipping a mapping.
- Keep the number of fields per index small and stable; avoid user-controlled field names.
- Use the `_search` timeout and cancel long requests; use async search for heavy queries.
- Monitor cluster health, shard sizes, rejected thread pool tasks, JVM heap and disk watermarks.

## 9. Performance

- Shards: 10 to 50 GB each, under 200 million documents; too many small shards waste heap and slow searches because each shard is searched on one thread per request.
- Bulk indexing: send batches of a few thousand documents or roughly 5 to 15 MB per request, run a few concurrent requests, back off on `429`. For a large initial load, set `refresh_interval` to `-1` and `number_of_replicas` to `0`, then restore both and force a refresh.
- Query speed: filters before scoring, keyword for exact matches, avoid leading wildcards and expensive regexps, avoid `script` and `script_score` on hot paths, prefer `match_phrase` on indexed positions over wildcard hacks.
- Pagination: avoid `from + size` beyond a few thousand; `search_after` avoids per-shard deep sorts.
- Set `track_total_hits` to `false` (or a number) when the exact total is not needed; this allows early termination.
- Use doc values (default) for sorting and aggregations on keyword and numeric fields; disable `index` on fields that are never searched and `doc_values` on fields never sorted or aggregated to save disk.
- Use index sorting, `routing` by tenant, or a dedicated index per large tenant to narrow the shards searched; routing risks hot shards, so measure.
- Use the Profile API (`"profile": true`) to find slow query clauses; use the slow log for production.
- Vector search: choose quantization (`bbq_hnsw`, `int8_hnsw`, `bbq_disk`) by memory budget; keep `num_candidates` as small as recall allows; vectors are excluded from `_source` by default.
- Reindex with `slices: "auto"` and a throttle (`requests_per_second`) to limit impact.

## 10. Security

- Self-managed 8.0+ starts with security enabled: TLS on the HTTP and transport layers, a generated `elastic` password, and enrollment for Kibana and nodes. Do not turn security off outside disposable test containers. Anonymous access is off by default (requests without credentials get 401); do not enable it for application indices.
- Never expose Elasticsearch directly to browsers or the internet. Browsers talk to your backend, and the backend queries Elasticsearch with a restricted API key. A public cluster endpoint with a key in client code gives every visitor that key.
- Applications use API keys (or dedicated users), not the `elastic` superuser. Create keys with `role_descriptors` limited to the needed indices and privileges (`read` on an alias, `write` on another), an expiration, and metadata; rotate them. Keep keys in a secret manager.
- Tenant isolation covers reads and writes. Reads: a mandatory `term` filter on `tenantId` in every query, including nested sub-queries, aggregations, `_count`, `_msearch`, and ES|QL (use the request `filter`). Writes: stamp `tenantId` server-side (ignore any client value), prefix document ids with the tenant so an id can never overwrite another tenant's document, and include the tenant term in every `_update_by_query` and `_delete_by_query`. Alias filters do not apply to get-by-id, so check the tenant on fetched documents. Document-level security in roles can enforce tenant filters at the cluster level but is a subscription feature; check the subscription page.
- Prevent query abuse: allow only a fixed set of fields and sort keys from the UI, cap `size`, page depth and aggregation size, use `timeout`, and avoid `query_string`/`regexp`/`wildcard` on untrusted input. Do not accept user-supplied `index` names or scripts; map user choices to known aliases.
- ES|QL: pass user values as `params` (`?name`), never by string concatenation.
- Clients verify the server certificate with the cluster CA (`tls.ca` in JS, `ca_certs` in Python) or a CA fingerprint pin; never set `rejectUnauthorized: false` or `verify_certs=False` in production.
- Keep ports 9200 and 9300 on private networks, restrict by security group, and enable audit logging where compliance requires it. Secure Kibana separately.
- Snapshot repositories hold all data; protect their credentials and test restores.

## 11. Testing

- Integration tests against a real Elasticsearch in a container (single node with `discovery.type=single-node`), same major version as production. Disabling security is acceptable only for the throwaway test container; test the real authentication path in a staging environment.
- Create indices from the same mapping files as production; call `_refresh` (or use `refresh: "wait_for"`) before asserting search results.
- Test analyzers with `_analyze` fixtures (input text to expected tokens); test relevance with a small judged set and the `_rank_eval` API.
- Test tenant isolation: index documents for two tenants, then assert that searches, aggregations, get-by-id helpers, updates and deletes issued as tenant A never touch tenant B documents, including the case where both use the same business id.
- Test migrations: create v2, reindex, compare counts and sampled documents, swap the alias, and roll back.
- Test failure handling: bulk responses with failed items, `429` backoff, and timeouts.

## 12. Review Checklist

- [ ] Mappings are explicit, `dynamic` is `strict` or `false`, and field types match usage (keyword vs text).
- [ ] No in-place type change plans; evolution uses a new index, reindex and an alias swap.
- [ ] Queries use `filter` for non-scoring conditions; sizes and timeouts are set.
- [ ] Deep pagination uses `search_after` with PIT, not `from + size` beyond 10,000.
- [ ] Shard count and size follow the 10 to 50 GB guidance; time series use data streams with rollover.
- [ ] Bulk code checks per-item errors and handles `429` with backoff.
- [ ] Tenant filter applied to every read and to every write path (index, update, delete, by-query).
- [ ] Clients use TLS verification and a least-privilege API key; Elasticsearch is not reachable from browsers.
- [ ] User input never builds raw DSL, scripts, index names or ES|QL strings.
- [ ] Application code uses aliases; templates, mappings and lifecycle policies are in version control.
- [ ] Monitoring covers heap, disk watermarks, rejected tasks and shard sizes.

## 13. Production Notes

- Run at least three master-eligible nodes (dedicated for larger clusters), replicas of at least 1, and data tiers matching access patterns; spread shards across zones with allocation awareness.
- Snapshot regularly to a repository and restore-test; snapshots are the backup, replicas are not.
- Upgrade rolling within a major; read the breaking changes and deprecation notes of the target version; for 8.x to 9.x use the upgrade assistant and check deprecations first. Upgrade clients with the server major.
- Capacity: watch shard counts per node, heap usage, disk watermarks, pending tasks and thread pool rejections; plan rollover and retention so growth is bounded.
- Use data stream lifecycle or ILM to automate rollover, merge, tiering and deletion; test the policy on a copy.
- Mapping changes are code changes: review, test and roll out like database migrations.
- If compliance requires isolation per tenant, separate indices or clusters are simpler to audit than shared indices with filters.

## 14. Examples

Strict mapping with a custom autocomplete analyzer, an alias, and a zero-downtime change to v2 (Console syntax):

```json
PUT orders-v1
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "analysis": {
      "filter": { "edge_2_15": { "type": "edge_ngram", "min_gram": 2, "max_gram": 15 } },
      "analyzer": {
        "autocomplete_index":  { "type": "custom", "tokenizer": "standard", "filter": ["lowercase", "asciifolding", "edge_2_15"] },
        "autocomplete_search": { "type": "custom", "tokenizer": "standard", "filter": ["lowercase", "asciifolding"] }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "tenantId":   { "type": "keyword" },
      "orderId":    { "type": "keyword" },
      "customerId": { "type": "keyword" },
      "status":     { "type": "keyword" },
      "title":      { "type": "text", "analyzer": "autocomplete_index", "search_analyzer": "autocomplete_search",
                      "fields": { "raw": { "type": "keyword", "ignore_above": 256 } } },
      "totalCents": { "type": "long" },
      "createdAt":  { "type": "date" }
    }
  },
  "aliases": { "orders": {} }
}
```

```json
// Later: change a mapping. 1) create orders-v2 with the new mapping (no alias yet)
// 2) copy data (writes arriving meanwhile must also reach orders-v2: dual-write or a second catch-up reindex)
POST _reindex?wait_for_completion=false
{ "source": { "index": "orders-v1" }, "dest": { "index": "orders-v2" } }

// 3) check progress with GET _tasks/<task_id>, compare counts, then swap atomically
POST _aliases
{
  "actions": [
    { "remove": { "index": "orders-v1", "alias": "orders" } },
    { "add":    { "index": "orders-v2", "alias": "orders" } }
  ]
}
```

Tenant-safe search with `search_after` and a point in time, plus tenant-safe bulk writes (JavaScript client 9.x):

```ts
import { Client } from "@elastic/elasticsearch";
import { readFileSync } from "node:fs";

export const es = new Client({
  node: process.env.ES_URL!,                                   // https://...
  auth: { apiKey: process.env.ES_API_KEY! },                   // scoped key, not the elastic user
  tls: { ca: readFileSync(process.env.ES_CA_PATH!) },          // verify the server certificate
  requestTimeout: 10_000,
});

const STATUSES = new Set(["pending", "paid", "cancelled"]);

export async function* exportOrders(tenantId: string, status: string) {
  if (!STATUSES.has(status)) throw new Error("invalid status");           // user text never becomes DSL
  const pit = await es.openPointInTime({ index: "orders", keep_alive: "1m" });
  let pitId = pit.id;
  let searchAfter: (string | number)[] | undefined;
  try {
    for (;;) {
      const res = await es.search({
        size: 500,
        track_total_hits: false,
        pit: { id: pitId, keep_alive: "1m" },
        query: { bool: { filter: [{ term: { tenantId } }, { term: { status } }] } },   // tenant first, always
        sort: [{ createdAt: "asc" }],                                    // PIT adds an implicit _shard_doc tiebreaker
        _source: ["title", "totalCents", "createdAt"],
        ...(searchAfter ? { search_after: searchAfter } : {}),
      });
      pitId = res.pit_id ?? pitId;                                       // use the latest PIT id
      const hits = res.hits.hits;
      if (hits.length === 0) return;
      for (const h of hits) yield h._source;
      searchAfter = hits[hits.length - 1].sort as (string | number)[];
    }
  } finally {
    await es.closePointInTime({ id: pitId });
  }
}

export async function indexOrders(tenantId: string, orders: { orderId: string; title: string; status: string; totalCents: number; customerId: string; createdAt: string }[]) {
  const stats = await es.helpers.bulk({
    datasource: orders.map((o) => ({ ...o, tenantId })),                 // tenantId set last: overrides any client value
    onDocument: (doc) => ({ index: { _index: "orders", _id: `${tenantId}:${doc.orderId}` } }),   // tenant-prefixed id
    onDrop: (d) => console.error("dropped document", d.status, d.error?.type),
    flushBytes: 5_000_000,
  });
  if (stats.failed > 0) throw new Error(`${stats.failed} documents failed to index`);
  return stats;
}

// Writes by query also carry the tenant.
export const closeStale = (tenantId: string) =>
  es.updateByQuery({
    index: "orders",
    query: { bool: { filter: [{ term: { tenantId } }, { term: { status: "pending" } }, { range: { createdAt: { lt: "now-30d" } } }] } },
    script: { lang: "painless", source: "ctx._source.status = 'cancelled'" },
    conflicts: "proceed",
  });
```

Hybrid search with the RRF retriever, and an ES|QL aggregation with parameters and a tenant filter:

```json
POST products/_search
{
  "retriever": {
    "rrf": {
      "retrievers": [
        { "standard": { "query": { "bool": {
            "must":   [ { "match": { "title": "trail running shoes" } } ],
            "filter": [ { "term": { "tenantId": "acme" } } ] } } } },
        { "knn": { "field": "embedding", "query_vector": [0.12, -0.03, 0.44],
                   "k": 50, "num_candidates": 200,
                   "filter": [ { "term": { "tenantId": "acme" } } ] } }
      ],
      "rank_window_size": 100,
      "rank_constant": 60
    }
  },
  "size": 10,
  "_source": ["title", "price"]
}

POST /_query
{
  "query": "FROM orders | WHERE status == ?status | STATS revenue = SUM(totalCents) BY day = DATE_TRUNC(1 day, createdAt) | SORT day | LIMIT 31",
  "params": [ { "status": "paid" } ],
  "filter": { "term": { "tenantId": "acme" } }
}
```

## 15. Common Mistakes

- **Relying on dynamic mapping in production**: a stray field or a numeric-looking string fixes a wrong type forever, and field counts explode. Use `dynamic: "strict"`.
- **Trying to change a field type in place**: not possible. Create a new index and reindex behind an alias.
- **`text` where `keyword` is needed** (or the reverse): exact filters on analyzed text return surprising matches; sorting or aggregating on `text` fails or is disabled. Use multi-fields.
- **`from`/`size` for deep pages**: hits beyond 10,000 are rejected and deep pages are expensive. Use `search_after` with PIT.
- **Everything in `must`**: scoring and caching are wasted on structured conditions. Use `filter`.
- **Oversharding**: hundreds of tiny shards per node hurt heap and search latency. Size shards 10 to 50 GB.
- **Deleting old documents with delete-by-query** in time series data: slow and leaves deleted docs until merges. Roll over and drop indices.
- **One `index` call per document**: use bulk and check item errors.
- **Ignoring bulk `errors: true`**: failed items are silent unless inspected.
- **Exposing Elasticsearch to browsers** or embedding an API key in front-end code. Proxy through a backend.
- **Running as the `elastic` superuser** in applications, or disabling TLS verification to "make it work".
- **Tenant filter only on search**: update-by-query, delete-by-query, non-prefixed ids and get-by-id on filtered aliases let tenants overwrite or read each other's documents. Scope every path.
- **`query_string` with raw user input**: exposes field names, wildcards and regexps. Use `simple_query_string` or `match` with a field allowlist.
- **Assuming OpenSearch compatibility**: APIs, clients, security plugins and ML features diverge; do not share client code between the two.
- **Mixed client and server majors**: use client 9 with server 9.

## 16. References

- [references/mappings-and-analysis.md](references/mappings-and-analysis.md): field types, multi-fields, dynamic templates, analyzers and normalizers, templates, data streams and lifecycle, shard sizing, reindex and alias swap procedures, bulk ingestion.
- [references/search-and-relevance.md](references/search-and-relevance.md): Query DSL recipes, relevance tuning, aggregations, pagination (search_after and PIT), ES|QL, vector search with `dense_vector`, kNN, `semantic_text`, retrievers and hybrid search, query safety.
- Official docs: https://www.elastic.co/docs/reference/elasticsearch/ , https://www.elastic.co/docs/solutions/search , https://www.elastic.co/docs/reference/query-languages/esql , https://www.elastic.co/docs/deploy-manage/production-guidance/optimize-performance/size-shards , https://www.elastic.co/docs/reference/elasticsearch/clients/javascript , https://www.elastic.co/docs/reference/elasticsearch/clients/python
