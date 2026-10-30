# Vector Databases

Reference for choosing and operating a vector database: pgvector, Qdrant, Weaviate, Milvus, Pinecone and OpenSearch/Elasticsearch kNN. pgvector facts were checked against the pgvector 0.8.7 README and pgvector-python 0.5.1; client method names for Qdrant, Weaviate, Milvus and Pinecone were checked against the installed SDKs (qdrant-client 1.20.0, weaviate-client 4.24.1, pymilvus 3.0.2, pinecone 10.2.0). Engine-side parameter names that could not be checked here are marked "check the current docs".

## Contents
1. [Choosing a store](#1-choosing-a-store)
2. [Index families: HNSW vs IVF](#2-index-families-hnsw-vs-ivf)
3. [pgvector](#3-pgvector)
4. [Qdrant](#4-qdrant)
5. [Weaviate](#5-weaviate)
6. [Milvus](#6-milvus)
7. [Pinecone](#7-pinecone)
8. [OpenSearch and Elasticsearch](#8-opensearch-and-elasticsearch)
9. [Quantization](#9-quantization)
10. [Filtering and tenant isolation](#10-filtering-and-tenant-isolation)
11. [Hybrid search](#11-hybrid-search)
12. [Measuring recall](#12-measuring-recall)

## 1. Choosing a store

| Situation | Reasonable choice |
|---|---|
| Data already in Postgres, transactions and joins with relational data, up to millions of vectors | pgvector |
| Heavy payload filtering, many tenants, rich hybrid queries, self-hosted | Qdrant, Weaviate or Milvus |
| Fully managed, minimal operations | Pinecone (or a managed offering of the others) |
| Existing OpenSearch or Elasticsearch cluster with keyword search already | kNN in that cluster |
| Local prototyping | Qdrant local mode (`QdrantClient(":memory:")`) or a Postgres container with pgvector |

Decide with a test on your own data: recall against an exact baseline, filtered-query behavior, ingestion rate, memory, operational cost. Do not choose on published benchmark numbers alone.

## 2. Index families: HNSW vs IVF

- **Exact (flat) scan**: perfect recall, cost linear in rows. Fine for small tables, and best when a filter leaves few candidate rows.
- **HNSW** (graph): best recall/latency trade-off in most workloads, higher memory, slower builds, supports inserts without retraining. Parameters: `m` (links per node), `ef_construction` (build-time candidate list), and a search-time candidate list (`ef_search` in pgvector, `hnsw_ef` in Qdrant, `ef` / `num_candidates` in OpenSearch and Elasticsearch). Higher values raise recall and cost.
- **IVF / IVFFlat** (clusters): builds faster and uses less memory than HNSW, recall depends on how many clusters are probed (`ivfflat.probes` in pgvector, `nprobe` in Milvus and Faiss-style engines). Needs representative data present when the index is built; rebuild if the distribution drifts.
- **PQ / SQ / binary quantization** reduce memory by compressing vectors; see section 9.
- Pick by constraint: recall and latency first, HNSW; memory or build time first, IVF family with quantization; tiny data, exact.

## 3. pgvector

Types: `vector` (up to 2,000 dimensions for indexing), `halfvec` (index up to 4,000), `sparsevec` (up to 1,000 non-zero elements), `bit`. Distance operators: `<->` L2, `<#>` negative inner product, `<=>` cosine, `<+>` L1, `<~>` Hamming, `<%>` Jaccard. Operator classes: `vector_l2_ops`, `vector_ip_ops`, `vector_cosine_ops`, `vector_l1_ops`, and the `halfvec_*` and `sparsevec_*` equivalents; the query operator must match the index's operator class.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW (defaults: m = 16, ef_construction = 64)
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- IVFFlat: create after loading data; lists is the number of clusters
CREATE INDEX ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Half-precision storage and index
CREATE TABLE docs (id bigserial PRIMARY KEY, embedding halfvec(1024));
CREATE INDEX ON docs USING hnsw (embedding halfvec_cosine_ops);

-- Index a half-precision cast of a full-precision column
CREATE INDEX ON items USING hnsw ((embedding::halfvec(1024)) halfvec_cosine_ops);
-- the query must use the same expression: ORDER BY embedding::halfvec(1024) <=> $1::halfvec(1024)
```

Query-time settings:

```sql
SET hnsw.ef_search = 100;          -- default 40; higher = better recall, slower
SET ivfflat.probes = 10;           -- IVFFlat clusters scanned
BEGIN;
SET LOCAL hnsw.ef_search = 100;    -- scoped to one transaction
SELECT ... ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

Filtering with approximate indexes: the filter is applied after the index scan, so a filter matching 10% of rows with the default `ef_search` of 40 returns about 4 rows on average. Options:

- **Iterative index scans (pgvector 0.8.0 and later)**: `SET hnsw.iterative_scan = strict_order;` (exact distance order) or `relaxed_order` (better recall, slightly out-of-order results; use a materialized CTE with `ORDER BY distance + 0` to restore strict ordering), and `SET ivfflat.iterative_scan = relaxed_order;`. The scan continues until enough rows are found or a limit is reached: `hnsw.max_scan_tuples` (default 20,000), `hnsw.scan_mem_multiplier` (default 1, a multiple of `work_mem`), `ivfflat.max_probes`.
- **B-tree or composite index** on the filter columns, so the planner can choose an exact scan when the filter is selective.
- **Partial indexes** (`WHERE category_id = 123`) for a few distinct values.
- **List partitioning** (`PARTITION BY LIST (tenant_id)`) for many values; also the recommended way to isolate tenants, because a shared approximate index lets one tenant's vectors affect another's recall.

Operations:

- Index build is much faster when the graph fits in `maintenance_work_mem`; the server emits a notice when it no longer fits. Do not set it so high that it exhausts server memory.
- Bulk-load with `COPY ... FROM STDIN WITH (FORMAT BINARY)` and create indexes after loading.
- Binary quantization by expression index: `CREATE INDEX ON items USING hnsw ((binary_quantize(embedding)::bit(1024)) bit_hamming_ops);` then re-rank candidates by full vectors in an outer query.
- Matryoshka-style truncation by expression: `subvector(embedding, 1, 256)::vector(256)`, with re-ranking by the full vector.
- Results are limited by `ef_search` and dead tuples and filters; if a query returns fewer rows than `LIMIT`, raise `ef_search` or enable iterative scans.
- Use `halfvec` to shrink the working set; check recall afterwards.
- Hybrid: combine with Postgres full-text search (`tsvector`, `websearch_to_tsquery`) and fuse by rank; see section 11.

Python (psycopg 3 with the `pgvector` package):

```python
import psycopg
from pgvector import HalfVector
from pgvector.psycopg import register_vector

with psycopg.connect(DSN) as conn:        # DSN from the server environment
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)                 # after the extension exists
    conn.execute("SELECT id FROM docs ORDER BY embedding <=> %s LIMIT 5", (HalfVector([0.1] * 1024),)).fetchall()
```

With a connection pool, call `register_vector` in the pool's `configure` callback; for async connections use `register_vector_async`.

## 4. Qdrant

- Client: `from qdrant_client import QdrantClient, models`. Search through `client.query_points(...)` (supports `prefetch`, `query_filter`, `search_params`, `limit`); hybrid fusion with `models.FusionQuery(fusion=models.Fusion.RRF)` (also `Fusion.DBSF`).
- Collections: named dense vectors via `vectors_config={"dense": models.VectorParams(size=..., distance=models.Distance.COSINE)}`, sparse vectors via `sparse_vectors_config={"sparse": models.SparseVectorParams()}`.
- HNSW config: `models.HnswConfigDiff(m=..., ef_construct=..., payload_m=..., full_scan_threshold=..., on_disk=...)`; search-time `models.SearchParams(hnsw_ef=..., exact=..., quantization=models.QuantizationSearchParams(...))`.
- Payload indexes: create an index on every field used in filters (`client.create_payload_index(collection, field, field_schema=...)`); filters on unindexed fields are slow.
- Filtering is part of the graph traversal, so filtered queries usually keep recall without the post-filter problem; very restrictive filters fall back to scanning the payload index.
- Multi-tenancy: one collection with a `tenant_id` keyword payload index created with `models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD, is_tenant=True)` (optimizes storage for tenant-grouped reads), with `HnswConfigDiff(payload_m=16, m=0)` to build per-tenant graphs instead of one global graph; every query and write carries the tenant filter. Create separate collections only for a modest number of large tenants. Check the current docs for shard-key and tiered multitenancy options.
- Ids: use deterministic UUIDs derived from tenant, document and chunk number so that identical ids from different tenants cannot overwrite each other.
- Deletes: `client.delete(collection, points_selector=models.FilterSelector(filter=...))` with the tenant condition included in the filter.
- Quantization: `quantization_config=models.ScalarQuantization(scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, always_ram=True))` at collection creation; the SDK also exposes product, binary and turbo quantization models (check the current docs for their parameters and trade-offs). Search with `oversampling` and rescoring through `QuantizationSearchParams`.
- Local mode (`QdrantClient(":memory:")`) is for tests; payload indexes have no effect there.

## 5. Weaviate

- Python client v4 (`import weaviate`; `weaviate.classes.config`, `weaviate.classes.query`). Hybrid search is built in (keyword plus vector, fusion configurable).
- Multi-tenancy is first-class: `Configure.multi_tenancy(enabled=True)` on the collection, tenants created explicitly, and every operation goes through `collection.with_tenant("tenant-id")`. Each tenant has its own shard and index, which gives strong isolation and cheap per-tenant deletion. Keep `auto_tenant_creation` off unless the tenant id comes only from a verified identity.
- Filters: `Filter.by_property("field")...` objects passed to queries; use them for ACL fields inside a tenant.
- Index types, vector compression (PQ, BQ, SQ, RQ) and their parameters change between releases; check the current docs.

## 6. Milvus

- Python client: `pymilvus.MilvusClient` with `create_collection`, `upsert`, `search`, `hybrid_search`, `delete`, `create_partition`.
- Multi-tenancy options, from lighter to heavier isolation: a partition key field (`FieldSchema(..., is_partition_key=True)`) that hashes tenants into partitions inside one collection; partition per tenant; collection per tenant; database per tenant. Filters on the tenant field are still mandatory with the partition-key approach.
- Index types include HNSW, IVF_FLAT, IVF_PQ, IVF_SQ8, DiskANN and others; parameter names (`M`, `efConstruction`, `ef`, `nlist`, `nprobe`) follow the families in section 2. Check the current docs for the index types available in your deployment mode (Lite, Standalone, Distributed, managed).

## 7. Pinecone

- Python: `from pinecone import Pinecone`; `pc = Pinecone(api_key=...)` (key from the server environment); `index = pc.Index(...)`; data operations `index.upsert`, `index.query`, `index.fetch`, `index.update`, `index.delete`.
- Namespaces are the tenant boundary: every upsert, query and delete passes `namespace=<tenant>` derived from the authenticated principal. Metadata filters apply within a namespace.
- Index types, sparse-dense hybrid, integrated embedding and rerank features, and limits change; check the current docs.

## 8. OpenSearch and Elasticsearch

- Elasticsearch: `dense_vector` field with `index_options` (HNSW family; scalar-quantized and binary-quantized variants exist, check the current docs for names) and a `knn` search clause with `field`, `query_vector`, `k`, `num_candidates` and a `filter` that restricts candidates during the search. Put tenant and ACL conditions in the `knn` clause's `filter` (and in the surrounding query), not only in a post-filter.
- Hybrid: combine a `match` query and a `knn` clause and fuse with reciprocal rank fusion (retrievers API; check the current docs for the syntax in your version).
- OpenSearch: enable `index.knn`, map `knn_vector` with `dimension` and a `method` (name `hnsw` or `ivf`, an engine such as `faiss` or `lucene`, `space_type`, `parameters`). Which engines support efficient filtering during the search varies by version; check the current docs and test that a restrictive filter still returns `k` results.
- Python clients: `elasticsearch` (9.5.1 on PyPI at time of writing) and `opensearch-py` (3.2.0). Use API keys or roles scoped to the index, and document-level security if the platform offers it for tenant isolation.

## 9. Quantization

- Scalar (int8): about a quarter of the memory of float32 with a small recall cost; usually the first step.
- Binary: 1 bit per dimension, large memory saving, a bigger recall cost; works best with models trained for it and with rescoring from full-precision vectors.
- Product quantization: strongest compression, trains codebooks, noticeable recall cost; common with IVF.
- Half precision (`halfvec`) halves storage versus float32 with usually little effect on ranking; measure.
- Dimension truncation (Matryoshka models only): keep the leading dimensions, then rescore.
- In every case retrieve extra candidates from the compressed index and rescore with full-precision vectors, then measure recall@k against an exact baseline (section 12).

## 10. Filtering and tenant isolation

- Tenant and ACL conditions are mandatory on reads, upserts and deletes, and come from the authenticated principal.
- Strategies, in order of isolation: separate database or cluster per tenant; collection, table or partition per tenant (Weaviate tenants, Milvus partitions, Pinecone namespaces, Postgres list partitions); shared collection with an indexed `tenant_id` filter and per-tenant graph building where the engine supports it.
- When a filtered query returns too few results: increase the search-time candidate list, enable iterative or filter-aware scanning (pgvector `hnsw.iterative_scan`), use partitions or per-tenant indexes, or return fewer results. Never remove the filter and never retry without it, and do not filter in the application after an unfiltered search.
- Writes: set `tenant_id` from the principal, ignore client-supplied tenant fields, derive ids from tenant and document, scope deletes and updates by tenant.
- Test with two tenants holding the same documents: search, upsert-over and delete from tenant A must never touch tenant B.
- Row-level security in Postgres adds a second line of defense for pgvector tables (postgresql-expert, authorization-expert).

## 11. Hybrid search

- Run a dense leg and a keyword or sparse leg with identical filters, then fuse by rank. Reciprocal rank fusion: `score(d) = sum over legs of 1 / (k + rank_leg(d))`, with `k` commonly 60; it needs no score normalization.
- Postgres: dense leg `ORDER BY embedding <=> $q LIMIT n`; keyword leg `WHERE tsv @@ websearch_to_tsquery('english', $text) ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('english', $text)) DESC LIMIT n`; fuse with `row_number()` ranks in SQL or in application code. Each leg includes the tenant condition.
- Qdrant: `query_points` with several `Prefetch` entries and `FusionQuery`. Weaviate: built-in hybrid. Elasticsearch and OpenSearch: `match` plus `knn` with rank fusion or a hybrid query (check the current docs).
- Sparse vectors from learned sparse models can be stored in `sparsevec` (pgvector) or sparse vector fields in Qdrant, Milvus and others.
- Rerank the fused list with a cross-encoder when precision at the top matters (retrieval-reranking.md).

## 12. Measuring recall

- Build ground truth with an exact scan (no index) over the same filtered set for a sample of real queries.
- Recall@k for the index: the fraction of the exact top-k that the approximate index returns. Compare configurations (`m`, `ef_construction`, `ef_search`, `lists`, `probes`, quantization) on the same queries, with and without filters, since filtered recall is usually the weak point.
- Record latency percentiles, memory, build time and throughput next to recall; choose the cheapest configuration that meets the recall target for the application.
- Re-measure after large data changes, deletes, upgrades and model changes.
- In pgvector, `EXPLAIN (ANALYZE)` shows whether the index is used; `SET enable_indexscan = off` gives the exact baseline for a session.
