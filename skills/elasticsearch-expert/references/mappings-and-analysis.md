# Mappings, Analysis, Lifecycle and Ingestion

Reference for Elasticsearch field types, multi-fields, dynamic mapping control, analyzers and normalizers, index templates, data streams and lifecycle policies, shard sizing, reindex and alias swap procedures, and bulk ingestion. Verified against Elasticsearch 9.5.5 reference documentation, `@elastic/elasticsearch` 9.5.1 and the Elastic shard sizing guidance (2026-10). Requests use Kibana Console syntax; the same bodies work with any client. OpenSearch is a separate fork with different APIs; this file does not apply to it unchanged.

## 1. Field types and when to use them

| Need | Type | Notes |
|---|---|---|
| Exact match, filter, sort, terms aggregation | `keyword` | Ids, enums, tags, emails, codes; `ignore_above` limits indexed length |
| Full-text search on prose | `text` | Analyzed into tokens; no sorting or aggregations (needs fielddata, avoid) |
| Both | `text` with a `keyword` multi-field | Dynamic mapping creates this for strings with `ignore_above: 256` |
| Whole numbers, decimals | `long`, `integer`, `double`, `scaled_float` | Use for range queries and math, not for identifiers |
| Dates | `date` (and `date_nanos`) | Set `format` explicitly if not ISO 8601 |
| Booleans | `boolean` | |
| IP addresses | `ip` | CIDR queries |
| Arbitrary key sets | `flattened` | One field for many keys; limited query features, avoids mapping explosion |
| Arrays of objects needing per-element matching | `nested` | Each element is a hidden document; costs more |
| Autocomplete | `search_as_you_type` or edge n-gram analyzer | |
| Geo | `geo_point`, `geo_shape` | |
| Embeddings | `dense_vector`, `sparse_vector`, `semantic_text` | See the search reference |
| Counters for ranking | `rank_feature` | Used with `rank_feature` queries |

Rules:

- A field type cannot be changed after creation; new fields can be added to an existing mapping with `PUT index/_mapping`.
- Arrays are not a separate type; any field may hold multiple values of its type.
- Objects are flattened to dotted fields internally; arrays of objects lose per-element correlation unless `nested`.
- Fields default to being indexed and having doc values; set `"index": false` for display-only fields and `"doc_values": false` for fields never sorted or aggregated.
- `ignore_above` on `keyword` skips indexing of long values (the value stays in `_source`).
- Limit fields: `index.mapping.total_fields.limit` defaults to 1000 and counts all mapped fields, object mappings, aliases and runtime fields. If you must raise it, also review `indices.query.bool.max_clause_count`; for arbitrary keys use `flattened`.
- `_source` is stored by default and used for reindex, update and display; disabling it breaks those features. Use source filtering in mappings or requests to limit size, not removal.

## 2. Mapping control

```json
PUT products-v1
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "tenantId": { "type": "keyword" },
      "sku":      { "type": "keyword" },
      "name":     { "type": "text", "fields": { "raw": { "type": "keyword", "ignore_above": 256 } } },
      "price":    { "type": "scaled_float", "scaling_factor": 100 },
      "attrs":    { "type": "flattened" },
      "updatedAt":{ "type": "date" }
    }
  }
}
```

- `dynamic`: `true` (map new fields automatically), `runtime` (new fields as runtime fields), `false` (ignore unknown fields in the index but keep them in `_source`), `strict` (reject documents with unknown fields). Use `strict` for application data.
- Dynamic templates control automatic mapping of new fields when you must allow them:

```json
"dynamic_templates": [
  { "strings_as_keywords": { "match_mapping_type": "string", "mapping": { "type": "keyword", "ignore_above": 256 } } }
]
```

- Adding a multi-field to an existing field applies only to documents indexed afterwards unless you run `_update_by_query` on the index.
- `copy_to` combines several fields into one search field without a second copy in `_source`.
- Runtime fields (computed at query time) let you add fields without reindexing, at a query-time cost; promote them to indexed fields when they become hot.

## 3. Analysis

Text analysis turns a string into tokens: character filters, one tokenizer, then token filters. The same analyzer is normally used at index and search time.

- Default analyzer: `standard` (Unicode word boundaries, lowercase). Language analyzers (`english`, `german`, ...) add stop words and stemming.
- Test with `_analyze` using real text:

```json
POST products-v1/_analyze
{ "analyzer": "standard", "text": "Trail-Running Shoes, size 42" }
```

- Custom analyzer example for accent-insensitive, stemmed English text:

```json
PUT articles-v1
{
  "settings": {
    "analysis": {
      "filter": { "en_stem": { "type": "stemmer", "language": "english" } },
      "analyzer": {
        "en_folded": { "type": "custom", "tokenizer": "standard", "filter": ["lowercase", "asciifolding", "en_stem"] }
      }
    }
  },
  "mappings": { "properties": { "body": { "type": "text", "analyzer": "en_folded" } } }
}
```

- Autocomplete: index with edge n-grams and search with a plain analyzer (see the main SKILL.md example), or use `search_as_you_type`. Keep `min_gram`/`max_gram` tight; wide n-gram ranges inflate the index.
- Synonyms: use a `synonym_graph` filter in the search analyzer, loaded from a synonym set (`synonyms_set`, managed through the synonyms APIs) or a file with `updateable: true`, so synonym changes are picked up by reloading search analyzers without reindexing; index-time synonyms do require reindexing.
- Normalizers are analyzers for `keyword` fields (no tokenizer): lowercase and fold for case-insensitive exact matching.

```json
"settings": { "analysis": { "normalizer": { "lc_fold": { "type": "custom", "filter": ["lowercase", "asciifolding"] } } } },
"mappings": { "properties": { "email": { "type": "keyword", "normalizer": "lc_fold" } } }
```

- Changing analysis settings on an existing index requires closing it or, more commonly, a new index and reindex, because existing tokens were produced by the old analyzer.

## 4. Index templates, data streams and lifecycle

Composable index templates apply settings, mappings and aliases to new indices matching a pattern. Component templates are reusable pieces.

```json
PUT _ilm/policy/logs-app-policy
{
  "policy": { "phases": {
    "hot":    { "actions": { "rollover": { "max_primary_shard_size": "50gb", "max_age": "30d" } } },
    "delete": { "min_age": "90d", "actions": { "delete": {} } }
  } }
}

PUT _index_template/logs-app
{
  "index_patterns": ["logs-app-*"],
  "data_stream": {},
  "priority": 200,
  "template": {
    "settings": { "index.lifecycle.name": "logs-app-policy", "number_of_shards": 1 },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": { "type": "date" },
        "message":    { "type": "text" },
        "level":      { "type": "keyword" },
        "service":    { "type": "keyword" },
        "tenantId":   { "type": "keyword" }
      }
    }
  }
}
```

- A data stream requires a `@timestamp` field, accepts appends (use the `create` action in bulk), and writes to the current backing index; reads span all backing indices. Updates and deletes target a specific backing index; use data streams for append-only data.
- Rollover thresholds: `max_primary_shard_size` (for example `50gb`), `max_age`, `max_docs`. A shard is rolled over implicitly at 200 million documents.
- ILM (index lifecycle management) and the data stream lifecycle both automate rollover and retention; ILM offers phases (hot, warm, cold, frozen, delete) and actions such as shrink and force merge. Check the docs for which fits your version and tiers.
- Custom template patterns must not collide with built-in templates at the same priority (built-in templates exist for patterns such as `logs-*-*`); pick a higher `priority` or a more specific pattern.
- Delete retention by removing indices (ILM delete phase or `DELETE index`), not with delete-by-query.

## 5. Shard sizing

Guidance from the Elastic documentation:

- Aim for shard sizes between 10 GB and 50 GB, and keep each shard below 200 million documents.
- Too many shards ("oversharding") degrade search performance and make the cluster unstable; very large shards slow searches and lengthen recovery. A thousand 50 MB shards cost far more to search than one 50 GB shard with the same data.
- Each search request runs on a single thread per shard; many shards per request can exhaust the search thread pool.
- Every index, shard, segment and mapped field has overhead in heap and CPU; fewer, larger shards use fewer resources.
- Use data streams and ILM for time series so shard size is controlled by rollover (`max_primary_shard_size` of 50 GB, optionally `min_primary_shard_size` of 10 GB).
- Delete indices rather than documents to reclaim space immediately.
- Check shard sizes with `GET _cat/shards?v=true&h=index,prirep,shard,store&s=prirep,store&bytes=gb`.
- The right numbers depend on hardware and workload; benchmark with production data and queries. Change primary shard count of an existing index with the split or shrink APIs or a reindex.
- Default settings give one primary shard and one replica per index; set `number_of_replicas` to at least 1 for availability, more for read throughput.

## 6. Zero-downtime mapping changes

Procedure for changing a mapping or analyzer:

1. Applications use the alias `orders` for reads and writes; the concrete index is `orders-v1`. (An alias must not share a name with an index.)
2. Create `orders-v2` with the new settings and mappings and no alias.
3. Copy data:

```json
POST _reindex?wait_for_completion=false
{
  "source": { "index": "orders-v1", "size": 1000 },
  "dest":   { "index": "orders-v2" },
  "conflicts": "proceed"
}
```

   Add `?slices=auto` for parallelism and `requests_per_second` to throttle. Use `"script"` in the request to transform documents (for example renamed fields). Poll `GET _tasks/<task_id>`.
4. Handle changes during the copy: dual-write to both indices from the application, or after the first pass run a second reindex limited by `source.query` to documents modified since the start (needs an `updatedAt` field), or briefly pause writers.
5. Verify: compare `_count`, sample documents, run representative queries against `orders-v2` directly.
6. Swap atomically:

```json
POST _aliases
{
  "actions": [
    { "remove": { "index": "orders-v1", "alias": "orders" } },
    { "add":    { "index": "orders-v2", "alias": "orders", "is_write_index": true } }
  ]
}
```

7. Keep `orders-v1` until confident, then delete it. Rolling back is another alias swap.

Notes: reindex needs `_source` enabled for all fields; it creates documents with the destination mapping; `dest.op_type: "create"` avoids overwriting documents already written by dual-writes. When the alias covers several indices, exactly one should be the write index. Filtered aliases and routing can be attached to the alias in the same `add` action.

## 7. Bulk ingestion

NDJSON format: an action line (`index`, `create`, `update`, `delete`) followed by the source line (except `delete`), each terminated by a newline including the last.

```
POST _bulk
{ "index":  { "_index": "orders", "_id": "acme:1001" } }
{ "tenantId": "acme", "orderId": "1001", "status": "paid", "totalCents": 4200, "createdAt": "2026-10-30T12:00:00Z" }
{ "update": { "_index": "orders", "_id": "acme:1002" } }
{ "doc": { "status": "cancelled" } }
{ "delete": { "_index": "orders", "_id": "acme:1003" } }
```

- The response has `errors` (true if any item failed) and per-item `status`; HTTP 200 does not mean every item succeeded. Retry items with status `429` (and `5xx`) with exponential backoff; do not retry mapping or validation errors (`400`).
- Batch size: start at a few thousand documents or 5 to 15 MB per request and tune; use a few concurrent requests rather than one huge one.
- The JavaScript `client.helpers.bulk` accepts a datasource (array, async generator or stream), `onDocument` returning the action, `flushBytes` (default 5 MB), retries, and `onDrop` for documents that exhausted retries; the Python `helpers.bulk`, `streaming_bulk` and `parallel_bulk` helpers play the same role. Check the helper's returned statistics for failures.
- Idempotent upserts: use deterministic `_id` values (tenant-prefixed) with `index`; for conflict control use `if_seq_no` and `if_primary_term`, or `version_type=external` with a source version.
- Do not call refresh per request. Use `refresh=wait_for` only when a caller needs to read its own write; for large loads set `refresh_interval: "-1"` and `number_of_replicas: 0`, load, then restore the settings and refresh.
- Ingest pipelines (`pipeline` parameter or `default_pipeline` setting) can enrich or normalize documents; keep them light and tested.
- Tenant safety: build the action and source server-side; set the tenant field from the authenticated context and prefix the `_id`, so client data cannot change the tenant or collide with another tenant's id.
