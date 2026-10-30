# Search, Relevance, ES|QL and Vector Search

Reference for writing Elasticsearch queries: Query DSL recipes, relevance tuning, aggregations, pagination, ES|QL, vector and hybrid search, and query safety. Verified against Elasticsearch 9.5.5 reference documentation (2026-10). Requests use Kibana Console syntax. Features that depend on an inference service, a license tier or a specific minor version are marked; check the current docs before relying on them.

## 1. Query and filter context

- **Query context** (`must`, `should`, and full-text clauses) computes a relevance `_score`.
- **Filter context** (`filter`, `must_not`, `constant_score.filter`) only includes or excludes documents; results are cacheable and cheaper.

```json
GET orders/_search
{
  "size": 20,
  "track_total_hits": false,
  "_source": ["title", "totalCents", "createdAt"],
  "query": {
    "bool": {
      "must":     [ { "match": { "title": { "query": "running shoes", "operator": "and" } } } ],
      "filter":   [ { "term":  { "tenantId": "acme" } },
                    { "term":  { "status": "paid" } },
                    { "range": { "createdAt": { "gte": "now-30d/d" } } } ],
      "must_not": [ { "term": { "flagged": true } } ],
      "should":   [ { "term": { "featured": { "value": true, "boost": 2 } } } ]
    }
  },
  "sort": [ { "_score": "desc" }, { "createdAt": "desc" } ]
}
```

- Without a `must` or `filter`, `should` clauses are required to match at least one (`minimum_should_match` defaults to 1); with `must`/`filter` present, `should` is optional and only boosts. Set `minimum_should_match` explicitly when the intent matters.
- Put the tenant condition in `filter` of every query, including each child of compound queries.

## 2. Common queries

| Query | Use | Caveat |
|---|---|---|
| `match` | Analyzed full-text on one field | `operator`, `minimum_should_match`, `fuzziness` |
| `match_phrase` | Words in order | `slop` allows gaps |
| `multi_match` | One text over several fields | `type`: `best_fields` (default), `most_fields`, `cross_fields`, `phrase`, `phrase_prefix`; use `tie_breaker` with `best_fields`; field boosts such as `title^3` |
| `term` / `terms` | Exact value(s) on `keyword`, numbers, dates | Do not use on analyzed `text` fields (the indexed tokens are lowercased pieces) |
| `range` | Numbers and dates | Use date math (`now-7d/d`) and `format` |
| `exists` | Field has a value | |
| `prefix`, `wildcard`, `regexp` | Pattern match on keyword | Leading wildcards and complex regexps are expensive; avoid on large indices and untrusted input |
| `ids` | Specific ids | |
| `nested` | Per-element match of object arrays | Needs `nested` mapping |
| `simple_query_string` | End-user search box with operators | Never throws on bad syntax; limit `fields` |
| `query_string` | Lucene syntax | Powerful and risky; trusted input only |
| `function_score`, `script_score`, `rank_feature` | Custom ranking | `script_score` is costly; prefer `rank_feature` for popularity-style signals |

Highlighting: `"highlight": { "fields": { "body": {} } }` returns fragments; keep it to fields shown in the UI.

Suggestions: `completion` suggester for prefix autocomplete over curated inputs, `phrase`/`term` suggesters for "did you mean". For type-ahead on arbitrary text, `search_as_you_type` or edge n-grams are simpler.

## 3. Relevance tuning

- Scoring is BM25 by default. Rank is affected by term frequency, field length and document frequency, so scores are not comparable across queries.
- Improve relevance with, in this order: correct mappings and analyzers; field boosts in `multi_match`; phrase and proximity boosts (`should` with `match_phrase`); filters to cut noise; synonyms; business signals via `rank_feature` or `function_score`; reranking.
- `_explain` (`GET index/_explain/<id>`) and `"explain": true` show how a score was computed; `"profile": true` shows time per clause.
- Rescoring (`rescore`) re-ranks the top `window_size` hits with a costlier query; the `rescorer` and `text_similarity_reranker` retrievers do similar jobs inside the retriever framework.
- Pinned results and query rules (`pinned` retriever, `rule` retriever) let editors promote documents.
- Measure instead of guessing: the `_rank_eval` API computes metrics (precision, recall, MRR, nDCG) for a set of judged queries; keep a small judged set in version control and run it in CI after analyzer or boost changes.
- Fuzzy matching: `"fuzziness": "AUTO"` on `match` tolerates typos; set `prefix_length` to keep it cheap.

## 4. Aggregations

```json
GET orders/_search
{
  "size": 0,
  "query": { "bool": { "filter": [ { "term": { "tenantId": "acme" } }, { "range": { "createdAt": { "gte": "now-90d/d" } } } ] } },
  "aggs": {
    "by_day": {
      "date_histogram": { "field": "createdAt", "calendar_interval": "day" },
      "aggs": { "revenue": { "sum": { "field": "totalCents" } } }
    },
    "top_customers": { "terms": { "field": "customerId", "size": 10 } },
    "unique_customers": { "cardinality": { "field": "customerId" } }
  }
}
```

- Use `"size": 0` when only aggregations are needed.
- `terms` returns the top `size` buckets and counts per shard are approximate when the field has many values; `cardinality` is approximate (HyperLogLog++). For exact paging through all buckets use `composite` with `after`.
- Aggregations need doc values (default for `keyword`, numeric, `date`); not available on `text`.
- Intervals: `calendar_interval` (`day`, `month`, ...) respects calendars; `fixed_interval` (`30m`, `7d`) is a fixed length.
- High-cardinality `terms`, deep sub-aggregation trees and `nested` aggregations are memory-heavy; filter first and bound sizes. Use `filter`/`filters` aggregations for faceted counts.
- Aggregations run on the query's matching documents; the tenant filter in the query protects them. A `global` aggregation ignores the query, so add the tenant filter inside it.

## 5. Pagination

| Technique | Use | Notes |
|---|---|---|
| `from` + `size` | First pages of user-facing lists | Limited by `index.max_result_window` (default 10,000 hits); cost grows with depth because every shard builds `from + size` entries |
| `search_after` + PIT | Deep paging, exports, stable results | Pass the same `query` and `sort`; a PIT adds an implicit `_shard_doc` tiebreaker |
| `composite` aggregation | Paging through buckets | Use `after_key` |
| Scroll | Legacy bulk reads | No longer recommended for deep pagination; use `search_after` with PIT |

```json
POST /orders/_pit?keep_alive=1m

POST /_search
{
  "size": 500,
  "track_total_hits": false,
  "query": { "bool": { "filter": [ { "term": { "tenantId": "acme" } } ] } },
  "pit": { "id": "<pit id>", "keep_alive": "1m" },
  "sort": [ { "createdAt": "asc" } ],
  "search_after": [ "2026-10-30T12:00:00.000Z", 4294967298 ]
}

DELETE /_pit
{ "id": "<pit id>" }
```

- Omit the index from the path when using a PIT (the PIT fixes the target).
- Use the sort values of the last hit as `search_after` for the next request, and keep the latest `pit_id` returned by each response.
- Without a PIT, include a tiebreaker field with a unique value in the sort; refreshes between pages can reorder results.
- If the sort field is `date` in some indices and `date_nanos` in others, use `numeric_type` to convert.
- Close PITs when finished; open PITs hold segment files.

## 6. ES|QL

ES|QL is a piped query language run through `POST /_query` (and `POST /_query/async` for long queries). It is generally available in the stack; individual commands and functions carry their own availability tag in the reference (for example `LOOKUP JOIN` is GA from 9.1, with newer options in preview), so check the page of any command you use.

```json
POST /_query
{
  "query": """
    FROM orders
    | WHERE status == ?status AND createdAt >= ?since
    | STATS orders = COUNT(*), revenue = SUM(totalCents) BY day = DATE_TRUNC(1 day, createdAt)
    | SORT day DESC
    | LIMIT 31
  """,
  "params": [ { "status": "paid" }, { "since": "2026-10-01T00:00:00Z" } ],
  "filter": { "term": { "tenantId": "acme" } }
}
```

- Parameters (`?name`, positional `?1`, anonymous `?`) keep user values out of the query string and prevent injection; identifier parameters (`??`) exist for field and function names (check the availability tag in the docs for your version). Do not mix parameter styles in one query.
- The request `filter` (Query DSL) limits the documents ES|QL runs on: use it for tenant scoping and the other mandatory conditions. Index patterns and `FROM` sources come from your code, not from user input.
- A query without `LIMIT` uses an implicit limit (1000 rows); always write `LIMIT` explicitly and design exports with `search_after` instead.
- Strengths: ad hoc analytics, joins with `LOOKUP JOIN` to a lookup-mode index, time series (`TS` command), search functions (`MATCH`, `KQL`, `QSTR`), and aggregations without nested JSON. Limitations: not all Query DSL features (for example some relevance controls and highlighting) have equivalents; see the ES|QL limitations page.
- Result formats: JSON, CSV/TSV, text, and others via `format` or `Accept`.

## 7. Vector search

### dense_vector and kNN

```json
PUT products-v1
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "tenantId":  { "type": "keyword" },
      "title":     { "type": "text" },
      "embedding": { "type": "dense_vector", "dims": 768, "index_options": { "type": "bbq_hnsw" } }
    }
  }
}

POST products/_search
{
  "size": 10,
  "knn": {
    "field": "embedding",
    "query_vector": [0.12, -0.03, 0.44],
    "k": 10,
    "num_candidates": 100,
    "filter": [ { "term": { "tenantId": "acme" } } ]
  },
  "_source": ["title"]
}
```

(The example shows a truncated `query_vector`; its length must equal `dims`.)

- `index_options.type` selects the index structure and quantization: `hnsw`, `int8_hnsw`, `int4_hnsw`, `bbq_hnsw`, `bbq_disk` and flat variants. Defaults for float vectors: `int8_hnsw` in 9.0; from 9.1 `bbq_hnsw` for 384 or more dimensions and `int8_hnsw` below; from 9.4 `bbq_disk` when available under the license. `byte` and `bit` vectors default to `hnsw` without quantization.
- Similarity defaults to `cosine` for float vectors (`l2_norm` for `bit`); the vectors must be produced by the same model for index and query.
- `k` is the number of results; `num_candidates` is the number of candidates considered per shard (maximum 10,000), trading speed for recall.
- Filtering: a `filter` inside `knn` is a pre-filter, applied during the approximate search so `k` matching documents are returned. A filter placed elsewhere in the query tree (for example a `bool.filter` next to a `knn` query) is a post-filter and can return fewer than `k` hits. Put tenant and access filters inside the `knn` filter (and, for belt and braces, also in the surrounding query).
- By default `dense_vector` values are not returned in `_source`; reindexing and retrieving vectors need the documented options.
- The `knn` query (inside `query`) and `knn` section of `_search` both exist; the `knn` retriever composes with other retrievers.

### semantic_text

`semantic_text` fields (GA since 9.0) call an inference endpoint at index time, chunk long text and store embeddings; query with the `match` query, which is the recommended method.

```json
PUT articles-v1
{
  "mappings": { "properties": {
    "tenantId": { "type": "keyword" },
    "body":     { "type": "semantic_text" }          // default inference endpoint for your deployment
  } }
}

GET articles/_search
{ "query": { "bool": {
    "must":   [ { "match": { "body": "how do I rotate an API key" } } ],
    "filter": [ { "term": { "tenantId": "acme" } } ] } } }
```

- The default inference endpoint depends on the deployment and version (documented defaults include ELSER and Jina models on the Elastic Inference Service); queries across indices created with different default endpoints can rank oddly, so pin `inference_id` explicitly for production data.
- Inference endpoints can require a paid subscription or trial; the mapping can be added regardless of license state but indexing calls the inference API. Check licensing before designing around it.
- The older `semantic` query still works but the docs do not recommend it for new projects.

### Retrievers and hybrid search

Retrievers describe how top documents are produced and combined: `standard`, `knn`, `rrf` (reciprocal rank fusion), `linear` (weighted score combination), `rescorer`, `text_similarity_reranker`, `pinned`, `rule`, `diversify`.

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
  "size": 10
}
```

- RRF combines rankings by position, so it needs no score normalization; `rank_window_size` is the number of top hits taken from each child (it must be at least `size`).
- Add a reranker (`text_similarity_reranker`) over the fused top results when quality matters more than latency.
- Put the tenant filter in every child retriever, or use the compound retriever's top-level `filter` (the `rrf` retriever applies it to all sub-retrievers); a `post_filter` or a filter outside the retriever tree does not behave the same way, so test it.

## 8. Query safety

- Treat all search input as untrusted: validate types and lengths, allowlist fields, sort keys and filter names, and cap `size`, page depth and aggregation `size`.
- Build queries in server code from typed values; never forward a client-supplied DSL body, script, index name or ES|QL fragment.
- Use `simple_query_string` or `match` for free text; avoid `query_string` and leading wildcards on user input.
- Apply the mandatory tenant filter in a single query-builder function that all code paths use, and test it (including aggregations, suggesters, ES|QL and vector queries).
- Set request `timeout`, and use `allow_partial_search_results: false` when partial data would be misleading.
- Do not expose `_search` to browsers with a broad key. If a front end needs direct access, restrict the key's role to a read-only alias with a document-level-security filter (a subscription feature) and still prefer a backend proxy.
