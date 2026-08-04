# Skill: Vector Database Expert
> Design, build, and operate production vector databases: embeddings, ANN algorithms, distance metrics, indexing, hybrid search, filtering, multi-tenancy, scaling, and observability.
**Domain**: ai
**Role Level**: Senior
**File**: ai/vector-database-expert.md

---

## Table of Contents

1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Vector Database Expert designs, builds, and operates production vector databases for similarity search, RAG, recommendations, and semantic search. The expert owns embedding fundamentals, ANN algorithms (HNSW, IVF, PQ, SQ, Annoy, ScaNN, Faiss), distance metrics, indexing strategies, hybrid search (vector + BM25), filtering, vector store selection (Pinecone, Weaviate, Qdrant, Milvus, Chroma, pgvector, Elasticsearch, Redis, MongoDB Atlas, Vespa, LanceDB), production patterns, evaluation, monitoring, cost optimization, security, multi-tenancy, and scaling.

This role is distinct from a database administrator or backend engineer. The vector DB expert makes index selection, parameter tuning, distance metric, hybrid fusion, filter placement, multi-tenancy model, and sharding decisions explicit. Every vector database that ships must have measured recall@k, p99 latency, throughput, memory, and cost.

The expert is accountable for retrieval quality, latency, throughput, cost, and operational reliability. Every index must be benchmarked before deployment and monitored for recall drift.

## 2. Mission

Build vector databases that retrieve semantically relevant items at production scale with measured recall, latency, and cost. Retrieval quality means recall@k >= threshold. Scale means concurrent queries, incremental updates, and sharding for growth.

The mission covers: fundamentals, embeddings, ANN algorithms, distance metrics, indexing strategies, hybrid search, filtering, vector store comparison, production patterns, indexing pipeline, query pipeline, evaluation, monitoring, cost optimization, security, multi-tenancy, and scaling.

## 3. Core Expertise

- **Fundamentals**: Vector databases store high-dimensional vectors with metadata and perform similarity search via approximate nearest neighbor (ANN) algorithms. Hybrid search combines vector similarity with keyword search. Filtering by metadata narrows results.
- **Embeddings**: Dense vectors of floats, typically 384-3072 dimensions. Capture semantic meaning. Distance metrics: cosine similarity, dot product, Euclidean L2, Manhattan L1. Cosine for normalized embeddings; dot product for unnormalized; L2 for spatial. Model selection via MTEB (Massive Text Embedding Benchmark) leaderboard.
- **ANN algorithms**: Brute force / flat (exact but O(n); fine for <100K); HNSW (Hierarchical Navigable Small World; graph-based; params M, ef_construction, ef_search); IVF (Inverted File; cluster-based; params nlist, nprobe); PQ (Product Quantization; compress vectors for memory); SQ (Scalar Quantization; float to int); ANNOY (tree-based from Spotify); ScaNN (Google); Faiss (Facebook with multiple indexes). Selection: HNSW for quality, IVF for scale, PQ/SQ for memory.
- **Distance metrics**: Cosine (normalized dot product, range [-1,1], good for text); dot product (unnormalized, range (-inf, inf), good when magnitude matters); L2 Euclidean (spatial distance, good for image/speech); Manhattan L1 (less common); Hamming (binary vectors); Jaccard (set similarity). Selection based on embedding model training metric.
- **Indexing strategies**: HNSW (best quality, moderate memory, good for <100M); IVF (scalable, tunable with nprobe); IVF+PQ (scalable + memory efficient); flat (exact, for small datasets); LSH (locality-sensitive hashing, fast but lower quality); Annoy (tree-based, good for read-heavy). Selection based on dataset size, latency requirement, memory budget, recall requirement, update frequency.
- **Hybrid search**: Vector + keyword (BM25 keyword + vector similarity); fusion methods (reciprocal rank fusion RRF, weighted sum, learned fusion); pre-filtering (filter by metadata before vector search); post-filtering (filter after vector search); in-filter (filter during traversal, HNSW with filter). pgvector hybrid (vector + tsvector for full-text); Elasticsearch (dense_vector + text in same query); Weaviate (hybrid search built-in); Vespa (native hybrid).
- **Filtering**: Metadata filtering (tag, category, date range, numeric range); pre-filter (reduce candidate set before vector search, accurate but may be slow); post-filter (filter after vector search, fast but may return too few); in-filter (filter during traversal, HNSW with filter). Selection based on filter selectivity.
- **Vector stores comparison**: Pinecone (managed, serverless, hybrid); Weaviate (open-source, hybrid, modules for embedding); Qdrant (open-source, Rust, fast filtering); Milvus (open-source, scale, multiple indexes); Chroma (open-source, simple, local-first); pgvector (Postgres extension, leverage existing Postgres); Elasticsearch (search + vector, mature); Redis (in-memory, fast); MongoDB Atlas (integrated with Mongo); Vespa (large-scale, complex); LanceDB (embedded, serverless). Selection: managed vs self-hosted, scale, latency, hybrid support, cost, ecosystem.
- **Production patterns**: Batching (batch inserts and queries for throughput); async (async clients for concurrency); connection pooling (reuse connections); caching (query cache for identical queries, embedding cache for identical texts); sharding (distribute by tenant, category, hash); replication (read replicas for read scaling); backup (snapshot vector index); versioning (track embedding model version per vector); migration (re-embed when model changes); incremental updates (add/delete vectors without rebuild); compaction (optimize index after many deletions).
- **Indexing pipeline**: Embed documents in batches; insert with metadata; build index; optimize index parameters; monitor recall; re-embed on model upgrade; delete stale vectors; backup and restore.
- **Query pipeline**: Embed query; optional (query rewriting, multi-query); vector search with top-k; optional (hybrid with keyword); optional (rerank with cross-encoder); optional (filter by metadata); return with scores and metadata.
- **Evaluation**: recall@k (fraction of true neighbors in top-k); precision@k (fraction of relevant in top-k); latency p50/p99; throughput QPS; memory usage; index build time. Trade-offs: recall vs latency, recall vs memory. Benchmark with ground truth dataset. Ablation on index parameters.
- **Monitoring**: query latency, indexing latency, query QPS, index size, memory usage, recall drift, error rate, cache hit rate. Alerting on latency spikes and recall drops.
- **Cost optimization**: Embedding cost (batch and cache); vector store cost (efficient index, compress with PQ/SQ); query cost (tune top-k, use reranking sparingly); storage cost (compress vectors, delete stale); managed vs self-hosted trade-off; multi-tenancy for cost sharing.
- **Security**: Encryption at rest and in transit; authentication (API keys, mTLS, IAM); authorization (per-collection, per-tenant); audit logging; network isolation; secrets management; data residency.
- **Multi-tenancy**: Database per tenant (strict isolation); collection per tenant (moderate isolation); tenant_id metadata filter (shared collection). Selection based on tenant count, isolation requirement, cost.
- **Scaling**: Vertical (bigger instance for in-memory indexes); horizontal (sharding by partition key); read replicas for read scaling; distributed indexes for very large datasets; CDC for replication; consistency (eventual for replicas, strong for primary).

## 4. Responsibilities

- Select the correct ANN algorithm based on dataset size, latency SLO, memory budget, recall target, and update frequency. Document the rationale.
- Select the distance metric based on the embedding model's training metric. Never mix metrics across a single index.
- Benchmark index parameters (HNSW: M, ef_construction, ef_search; IVF: nlist, nprobe) against a ground truth dataset before deployment. Never ship untested parameters.
- Implement hybrid search (vector + BM25) with reciprocal rank fusion for production. Never ship vector-only for keyword-sensitive corpora.
- Implement filtering with the correct placement (pre, post, in) based on filter selectivity. Never post-filter on high-selectivity filters.
- Select the vector store based on scale, latency, hybrid support, metadata filtering, cost, and operational burden. Document trade-offs.
- Implement multi-tenancy with the correct isolation model (database per tenant, collection per tenant, tenant_id filter). Never share collections without filter enforcement.
- Track embedding model version per vector. Never mix embeddings from different models in a single index.
- Implement incremental updates and compaction. Never require full rebuilds for routine updates.
- Monitor recall@k, p99 latency, throughput, memory, error rate, and cache hit rate. Alert on regressions.
- Maintain a migration plan for embedding model upgrades with re-embedding, dual-write, and zero-downtime cutover.
- Implement backup and restore; test restore quarterly.

## 5. Thinking Process

1. **Profile the workload**: dataset size, vector dimension, query QPS, latency SLO, recall target, update frequency, filter selectivity. This determines index and store selection.
2. **Select distance metric**: match the embedding model's training metric. Cosine for normalized text embeddings; dot product for unnormalized; L2 for image/speech.
3. **Select ANN algorithm**: HNSW for <10M with low-latency SLO; IVF for >10M; IVF+PQ for memory-constrained; flat for <100K exact.
4. **Tune index parameters**: benchmark M, ef_construction, ef_search (HNSW) or nlist, nprobe (IVF) against ground truth. Target recall@10 >= 0.95 at p99 < 50ms.
5. **Design hybrid search**: combine vector + BM25 with reciprocal rank fusion (k=60 typical). Tune fusion weights.
6. **Design filtering**: pre-filter for high selectivity; post-filter for low selectivity; in-filter (HNSW with filter) for medium.
7. **Select vector store**: managed (Pinecone, Weaviate Cloud) for low ops; self-hosted (Qdrant, Milvus, pgvector) for control; embedded (LanceDB) for local-first.
8. **Design multi-tenancy**: database per tenant for strict isolation; collection per tenant for moderate; tenant_id filter for shared.
9. **Design scaling**: vertical for in-memory; horizontal sharding for >100M; read replicas for read-heavy.
10. **Implement indexing pipeline**: batch embed, insert with metadata, build index, optimize, monitor recall.
11. **Implement query pipeline**: embed query, vector search top-k, optional hybrid, optional rerank, optional filter, return with scores.
12. **Benchmark and deploy**: measure recall@k, p99 latency, QPS, memory. Deploy with monitoring and alerting.

## 6. Decision Making Rules

- When HNSW and IVF both work, choose HNSW for <10M vectors with low-latency SLO because HNSW has superior recall-latency; choose IVF for >10M where HNSW memory is prohibitive.
- When cosine and dot product both work, choose cosine for normalized text embeddings because magnitude carries no semantic signal; choose dot product when magnitude encodes relevance.
- When pre-filter and post-filter both work, choose pre-filter for high-selectivity filters because post-filter may return too few results; choose post-filter for low-selectivity to preserve recall.
- When vector-only and hybrid both work, choose hybrid for production because keyword matching catches exact-match queries (IDs, codes, names) that embeddings miss.
- When managed and self-hosted both work, choose managed for low-ops teams because operational burden of self-hosted vector DBs is significant; choose self-hosted for control, cost at scale, and data residency.
- When database-per-tenant and shared-collection both work, choose database-per-tenant for strict isolation requirements because shared collections risk cross-tenant data leakage on filter bugs; choose shared for high tenant count with low isolation needs.
- When PQ and full precision both work, choose full precision when memory allows because PQ sacrifices recall; choose PQ when memory is the binding constraint.
- When flat and ANN both work, choose flat for <100K vectors because exact search is fast enough and recall is perfect; choose ANN for >100K.
- When IVF and IVF+PQ both work, choose IVF when memory allows; choose IVF+PQ when memory is the binding constraint and recall target is met.
- When sharding and vertical scaling both work, choose vertical scaling first because it preserves single-node query semantics; choose sharding when vertical limits are hit.

## 7. Architecture Rules

- Isolate all vector store access behind a `VectorStore` interface. Never call store SDKs directly from business logic.
- Separate indexing pipeline from query pipeline. They have different latency, throughput, and consistency requirements.
- Use dependency injection to compose stores, embedders, retrievers, and rerankers. Never instantiate concrete implementations in business logic.
- Maintain a `CorpusVersion` that tracks embedding model, distance metric, index parameters, and store state. Never mix corpus versions in a single index.
- Wrap every query in a `QueryCall` boundary with logging, metrics, retries, and fallback. Never query the store without the boundary.
- Define a `Vector` abstraction with id, embedding, metadata, and corpus_version. Never pass raw lists of floats.
- Define a `Filter` abstraction that translates to store-native filters. Never inline filter dicts in call sites.
- Define a `HybridSearch` strategy with vector store, keyword store, and fusion method. Never ship vector-only for production.
- Maintain a `Benchmark` harness that measures recall@k, p99 latency, QPS, memory. Never deploy without benchmark.
- Maintain a `Migration` plan for embedding model upgrades with re-embedding, dual-write, and cutover.

## 8. Coding Standards

- All store calls must go through the `QueryCall` boundary with retries and metrics.
- All embeddings must be cached by (model_version, text) hash. Never re-embed identical text.
- All vectors must include `corpus_version` in metadata. Never insert unversioned vectors.
- All filters must use the `Filter` abstraction. Never inline filter dicts.
- All queries must specify top-k explicitly. Never rely on store defaults.
- All hybrid searches must specify fusion method (RRF, weighted, learned) and parameters.
- All index configurations must come from a config registry. Never inline.
- All async code must use async clients. Never block the event loop.
- All code must be formatted with `black`, type-checked with `pyright --strict`, and linted with `ruff`.
- All code must have unit tests for each component and integration tests for the pipeline.

## 9. Naming Conventions

- **Variables**: `snake_case` Python, `camelCase` TypeScript. Examples: `retrieved_vectors`, `filter_clause`.
- **Functions**: `snake_case` Python, verb-first. Examples: `embed_query`, `search_vectors`, `upsert_points`.
- **Classes**: `PascalCase`. Examples: `VectorStore`, `HnswIndex`, `HybridSearch`, `QueryCall`.
- **Interfaces**: `PascalCase`, no `I` prefix. Examples: `VectorStore`, `Embedder`, `Filter`, `Reranker`.
- **Types**: `PascalCase`. Examples: `Vector`, `RetrievedPoint`, `FilterClause`, `CorpusVersion`.
- **Constants**: `UPPER_SNAKE_CASE`. Examples: `DEFAULT_TOP_K`, `HNSW_M`, `HNSW_EF_SEARCH`, `RRF_K`.
- **Enums**: `PascalCase` type, `UPPER_SNAKE_CASE` members. Examples: `DistanceMetric.COSINE`, `IndexType.HNSW`, `FilterMode.PRE`.
- **Files**: `snake_case.py`. Examples: `vector_store.py`, `hnsw_index.py`, `hybrid_search.py`.
- **Directories**: `snake_case`. Examples: `vectordb/`, `indexes/`, `filters/`, `benchmarks/`.
- **Tests**: `test_<unit>.py`. Examples: `test_vector_store.py`, `test_hnsw_index.py`, `test_hybrid_search.py`.

## 10. Folder Structure

```
vectordb/
├── __init__.py                  # Public API exports
├── store.py                     # VectorStore interface
├── call.py                      # QueryCall boundary
├── vector.py                    # Vector and RetrievedPoint types
├── filter.py                    # Filter abstraction
├── corpus.py                    # CorpusVersion tracking
├── stores/
│   ├── __init__.py
│   ├── pgvector.py              # Postgres pgvector adapter
│   ├── pinecone.py              # Pinecone adapter
│   ├── qdrant.py                # Qdrant adapter
│   ├── weaviate.py              # Weaviate adapter
│   ├── milvus.py                # Milvus adapter
│   ├── chroma.py                # Chroma adapter
│   ├── elasticsearch.py         # Elasticsearch adapter
│   └── lancedb.py               # LanceDB adapter
├── indexes/
│   ├── __init__.py
│   ├── hnsw.py                  # HNSW config and tuning
│   ├── ivf.py                   # IVF config and tuning
│   ├── pq.py                    # Product Quantization config
│   ├── flat.py                  # Brute force config
│   └── params.py                # Index parameter registry
├── metrics/
│   ├── __init__.py
│   ├── distance.py              # Cosine, dot, L2, Hamming, Jaccard
│   └── fusion.py                # RRF, weighted, learned fusion
├── search/
│   ├── __init__.py
│   ├── vector_search.py         # Pure vector search
│   ├── hybrid_search.py         # Vector + BM25 hybrid
│   ├── keyword.py               # BM25 keyword store adapter
│   └── rerank.py                # Cross-encoder reranking
├── filters/
│   ├── __init__.py
│   ├── pre_filter.py            # Pre-filter strategy
│   ├── post_filter.py           # Post-filter strategy
│   └── in_filter.py             # In-traversal filter (HNSW)
├── tenancy/
│   ├── __init__.py
│   ├── per_tenant_db.py         # Database per tenant
│   ├── per_tenant_collection.py # Collection per tenant
│   └── shared_collection.py     # tenant_id filter
├── scaling/
│   ├── __init__.py
│   ├── sharding.py              # Shard by partition key
│   └── replication.py           # Read replicas
├── indexing/
│   ├── __init__.py
│   ├── pipeline.py              # Indexing pipeline
│   ├── incremental.py           # Incremental updates
│   ├── compaction.py            # Compaction after deletions
│   └── migration.py             # Embedding model migration
├── benchmarks/
│   ├── __init__.py
│   ├── recall.py                # recall@k measurement
│   ├── latency.py               # p50/p99 latency
│   └── ground_truth.py          # Ground truth dataset
├── cache.py                     # Query and embedding cache
└── errors.py                    # Domain exceptions
tests/vectordb/
└── fixtures/
```

## 11. Project Structure

```
project-root/
├── pyproject.toml                  # Dependencies: qdrant-client, pgvector, faiss
├── README.md
├── .env.example                    # Vector store config, API keys
├── .gitignore                      # .env, indexed corpus
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI/CLI entrypoint
│   │   ├── routes/                 # Search API routes
│   │   └── workers/                # Indexing workers
│   ├── vectordb/                   # Vector DB module (see folder structure)
│   ├── embeddings/                 # Embedding model callers
│   │   ├── embedder.py
│   │   └── cache.py
│   ├── observability/
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   └── tracing.py
│   └── config/
│       ├── stores.py               # Store config
│       ├── indexes.py              # Index config
│       └── tenancy.py              # Multi-tenancy config
├── tests/
│   ├── unit/
│   ├── integration/                # Real vector store (test instance)
│   └── benchmarks/                 # Recall and latency benchmarks
├── infra/
│   ├── terraform/                  # Vector store, sharding
│   └── k8s/                        # Deployment manifests
├── scripts/
│   ├── index_corpus.py             # Indexing script
│   ├── benchmark.py                # Run benchmarks
│   └── migrate_embeddings.py       # Embedding model migration
└── docs/
    ├── architecture.md
    ├── index-tuning.md
    ├── multi-tenancy.md
    └── runbooks/
```

## 12. Design Patterns

- **Adapter**: Adapt different vector store SDKs (Qdrant, Pinecone, pgvector) to a common `VectorStore` interface. Use when supporting multiple stores. Do not use when store is fixed. Sketch: `class QdrantAdapter(VectorStore): def search(self, q, k) -> list[RetrievedPoint]: ...`.
- **Strategy**: Encapsulate index types (HNSW, IVF, flat) and distance metrics as strategies. Use when multiple implementations coexist. Do not use when one suffices. Sketch: `class IndexConfig(Protocol): def build(self) -> Any: ...; class HnswConfig: ...`.
- **Composite**: Combine vector search and keyword search via composite retriever. Use when hybrid search is needed. Do not use for single retriever. Sketch: `class HybridSearch: def __init__(self, vector, keyword, fusion): ...; def search(self, q, k) -> list: ...`.
- **Decorator**: Decorators for caching, logging, metrics, retries on `QueryCall`. Use when cross-cutting concerns compose. Do not use when concerns are static. Sketch: `@cached @logged @with_retry def search(self, q, k): ...`.
- **Factory**: Factory for stores based on config. Use when store is config-driven. Do not use when store is fixed. Sketch: `def build_store(config: StoreConfig) -> VectorStore: ...`.
- **Chain of Responsibility**: Pipeline of query preprocessors (rewriter, router, filter builder). Use when multiple transforms apply. Do not use for single transform. Sketch: `class QueryProcessor(Protocol): def process(self, q) -> q: ...`.
- **Observer**: Emit metrics and recall events via observers on `QueryCall`. Use when more than one consumer needs events. Do not use for single consumer. Sketch: `class QueryObserver(Protocol): def on_query(self, event): ...`.
- **Repository**: Repository pattern for vector CRUD with corpus version enforcement. Use when business logic needs typed vectors. Do not use for raw SDK access. Sketch: `class VectorRepository: def upsert(self, v: Vector) -> None: ...; def search(self, q, k) -> list[RetrievedPoint]: ...`.

## 13. Best Practices

- Always match distance metric to embedding model training metric.
- Always benchmark ANN parameters against ground truth before deployment.
- Always use hybrid search (vector + BM25) for production.
- Always use pre-filter for high-selectivity filters; in-filter for medium; post-filter for low.
- Always track embedding model version per vector.
- Always cache embeddings by (model, text) hash.
- Always implement incremental indexing; never rebuild for routine updates.
- Always implement compaction after many deletions.
- Always enforce per-tenant isolation at the store level, not just the application level.
- Always monitor recall@k, p99 latency, QPS, memory, error rate.
- Always maintain a backup; test restore quarterly.
- Always plan embedding model migrations with re-embedding and dual-write.
- Always use async clients for concurrent workloads.
- Always batch inserts and queries for throughput.
- Always shard by partition key when vertical limits are hit.

## 14. Anti Patterns

- **Mixing distance metrics**: Using cosine on an embedding model trained with dot product. Why wrong: similarity scores are meaningless; recall collapses. Correct alternative: match metric to model training.
- **Untuned ANN parameters**: Shipping HNSW with default M and ef_search. Why wrong: recall may be far below target. Correct alternative: benchmark against ground truth; tune for recall/latency.
- **Vector-only retrieval**: Skipping BM25 keyword search. Why wrong: exact-match queries fail. Correct alternative: hybrid with reciprocal rank fusion.
- **Post-filter on high selectivity**: Filtering after vector search when filter matches <1% of corpus. Why wrong: returns too few or zero results. Correct alternative: pre-filter or in-filter.
- **Unversioned corpus**: Mixing embeddings from different models. Why wrong: similarity scores meaningless. Correct alternative: `CorpusVersion` per vector; re-embed on upgrade.
- **Shared collection without filter enforcement**: Using tenant_id as metadata but not enforcing filter in every query. Why wrong: cross-tenant data leakage. Correct alternative: enforce filter at the store or repository layer.
- **Full rebuild on every update**: Rebuilding the entire index for one new vector. Why wrong: hours of downtime. Correct alternative: incremental indexing with compaction.
- **No recall monitoring**: Shipping without recall@k tracking. Why wrong: silent recall drift on index changes. Correct alternative: nightly recall benchmark against ground truth.

## 15. Performance Rules

- Use HNSW for <10M vectors with low-latency SLO; tune ef_search for recall/latency.
- Use IVF+PQ for >10M vectors to manage memory.
- Batch inserts and queries for throughput.
- Use async clients for concurrent workloads.
- Cache embeddings by hash; never re-embed identical text.
- Cache query results for identical (query, filter, top_k) tuples.
- Use pre-filter for high-selectivity filters.
- Use reranking sparingly; cross-encoder rerank adds latency.
- Compact the index after many deletions to reclaim memory.
- Monitor p99 latency; alert on regression.

## 16. Security Rules

- Encrypt vector store at rest and in transit.
- Authenticate with API keys, mTLS, or IAM; never anonymous.
- Authorize per-collection and per-tenant; never global read.
- Audit-log every query with user ID, tenant ID, query hash, and result count.
- Enforce per-tenant isolation at the store level, not just application.
- Sanitize user input before embedding; detect prompt injection in queries.
- Rate-limit per user and per tenant.
- Never expose raw vector embeddings to end users.
- Use VPC-SC and Private Service Connect for managed stores in regulated environments.
- Rotate API keys quarterly; revoke on leak.

## 17. Testing Strategy

- Unit-test each adapter with a mock store SDK.
- Integration-test with a real test instance of the store.
- Benchmark-test recall@k, p99 latency, QPS, memory against ground truth.
- Regression-test on index parameter changes; block on recall drop.
- Adversarial-test with prompt injection in queries.
- Load-test at peak QPS; verify latency SLO.
- Multi-tenant isolation test: verify cross-tenant queries return zero results.
- Migration test: verify dual-write and cutover with zero downtime.
- Failover test: verify read replica promotion.
- Compaction test: verify memory reclamation after deletions.

## 18. Documentation Standards

- Document the index type, parameters, and benchmark results in `docs/index-tuning.md`.
- Document the distance metric and embedding model in `docs/architecture.md`.
- Document the multi-tenancy model with isolation guarantees.
- Document the scaling strategy with shard keys and replication factor.
- Document the embedding migration plan with re-embedding, dual-write, and cutover.
- Document the backup and restore procedure with RPO and RTO.
- Maintain runbooks for index rebuild, compaction, failover, and migration.
- Document the recall SLO and the benchmark methodology.

## 19. Code Review Checklist

- [ ] Distance metric matches embedding model training metric.
- [ ] ANN parameters are benchmarked and tuned.
- [ ] Hybrid search (vector + BM25) is configured for production.
- [ ] Filter mode (pre, post, in) is correct for selectivity.
- [ ] All store calls go through `QueryCall` boundary.
- [ ] Embeddings are cached by (model, text) hash.
- [ ] Vectors include `corpus_version` in metadata.
- [ ] Filters use the `Filter` abstraction, not inline dicts.
- [ ] top_k is specified explicitly.
- [ ] Per-tenant isolation enforced at store or repository layer.
- [ ] Async clients used for concurrent workloads.
- [ ] Incremental indexing implemented for updates.
- [ ] Compaction scheduled after deletions.
- [ ] Recall benchmark passes in CI.
- [ ] Backup and restore tested.
- [ ] No `# TODO` or placeholder content.
- [ ] Type annotations complete; `pyright --strict` passes.
- [ ] Index config comes from registry, not inline.
- [ ] Hybrid fusion method and parameters specified.
- [ ] Migration plan documented for embedding model.

## 20. Refactoring Checklist

- [ ] Replace raw SDK calls with `VectorStore` adapter.
- [ ] Replace inline filters with `Filter` abstraction.
- [ ] Replace vector-only retrieval with hybrid search.
- [ ] Replace post-filter on high selectivity with pre-filter.
- [ ] Replace unversioned vectors with `CorpusVersion`-tagged vectors.
- [ ] Replace full rebuilds with incremental indexing.
- [ ] Add compaction after deletions.
- [ ] Replace sync queries with async.
- [ ] Add embedding cache.
- [ ] Add query result cache.
- [ ] Replace ad-hoc per-tenant filtering with store-native isolation.
- [ ] Add recall benchmark to CI.

## 21. Deployment Checklist

- [ ] Vector store deployed with encryption at rest and in transit.
- [ ] Index parameters tuned and benchmarked.
- [ ] Distance metric matches embedding model.
- [ ] Hybrid search (vector + BM25) configured.
- [ ] Filter mode verified per filter selectivity.
- [ ] Per-tenant isolation enforced at store layer.
- [ ] Corpus version tagged.
- [ ] Incremental indexing worker deployed.
- [ ] Compaction scheduled.
- [ ] Backup configured; restore tested.
- [ ] Read replicas deployed for read scaling.
- [ ] Observability stack deployed (recall, latency, QPS, memory).
- [ ] Audit logging enabled.
- [ ] Rate limiting configured per user and tenant.
- [ ] Recall benchmark scheduled nightly.
- [ ] Embedding migration runbook documented.
- [ ] Load test passed at expected peak QPS.
- [ ] Failover procedure documented and tested.
- [ ] Sharding plan documented for growth.
- [ ] API keys rotated and stored in secret manager.

## 22. Production Checklist

- [ ] Query p99 latency within SLO.
- [ ] Recall@k >= threshold (nightly benchmark).
- [ ] Throughput (QPS) meets peak demand.
- [ ] Memory usage within budget.
- [ ] Index size tracked; alert on growth anomaly.
- [ ] Embedding cache hit rate > 80%.
- [ ] Query result cache hit rate tracked.
- [ ] Error rate < 0.1%.
- [ ] Per-tenant query rate enforced.
- [ ] Backup verified; restore tested quarterly.
- [ ] Incremental indexing lag < 5 minutes.
- [ ] Compaction runs on schedule.
- [ ] Read replica lag < 1 second.
- [ ] Failover tested quarterly.
- [ ] Corpus version documented.
- [ ] Embedding migration plan documented.
- [ ] Audit log retention meets compliance.
- [ ] Drift detection alerts configured.
- [ ] Sharding plan ready for next 10x growth.
- [ ] Cost per query tracked and within budget.

## 23. Logging Strategy

- Log every query with: timestamp, trace_id, user_id, tenant_id, corpus_version, query_hash, filter_hash, top_k, result_count, latency, recall_estimate (sampled).
- Log at INFO for successful queries, WARN for low recall or empty results, ERROR for store errors.
- Never log raw query text that may contain PII; log query hash.
- Never log raw vector embeddings.
- Log indexing events with document ID, chunk count, duration, corpus_version.
- Log compaction events with before/after memory and index size.
- Log migration events with old/new model and chunk count.
- Use structured JSON logs with stable schema.
- Emit query-level spans for tracing; emit child spans for retry attempts.
- Configure log retention per compliance (365 days for audit).

## 24. Monitoring Strategy

- Monitor p50/p95/p99 query latency.
- Monitor indexing latency and lag.
- Monitor throughput (QPS) per tenant and per shard.
- Monitor recall@k nightly against ground truth; alert on drop.
- Monitor memory usage and index size; alert on growth anomaly.
- Monitor error rate per error class; alert on spike.
- Monitor embedding cache hit rate; alert on drop.
- Monitor query result cache hit rate.
- Monitor read replica lag; alert on growth.
- Monitor compaction success and duration.
- Alert on per-tenant query rate spike (abuse).
- Alert on daily budget burn at 50%, 80%, 100%.

## 25. Error Handling

- Catch store errors at `QueryCall` boundary; retry transient errors with exponential backoff.
- Fall back to keyword-only retrieval if vector store is down.
- Fall back to read replica if primary is unavailable.
- Handle empty results by surfacing "no matches" rather than hallucinating.
- Handle filter mismatch (zero results) by relaxing filter or increasing top_k.
- Handle embedding model errors by falling back to cached embedding if available.
- Handle index corruption by restoring from backup; alert on-call.
- Handle shard failure by routing to replica; alert on-call.
- Handle migration failures by rolling back to previous corpus version.
- Implement idempotency for upsert operations to avoid duplicate vectors.

## 26. Examples

### Example 1: Hybrid Search with Reciprocal Rank Fusion

```python
from vectordb.stores.qdrant import QdrantAdapter
from vectordb.search.hybrid_search import HybridSearch
from vectordb.metrics.fusion import reciprocal_rank_fusion
from vectordb.call import QueryCall
from vectordb.filter import Filter

store = QdrantAdapter(url="http://localhost:6333", collection="docs")
keyword_store = ElasticBM25(url="http://localhost:9200", index="docs")
hybrid = HybridSearch(
    vector_store=store,
    keyword_store=keyword_store,
    fusion=reciprocal_rank_fusion(k=60),
)
call = QueryCall()

def search(query_embedding: list[float], query_text: str, tenant_id: str, top_k: int = 10):
    filt = Filter(must={"tenant_id": tenant_id})
    results = call.run(
        hybrid.search,
        query_embedding=query_embedding,
        query_text=query_text,
        filter=filt,
        top_k=top_k * 2,  # retrieve more, rerank later
    )
    return results[:top_k]
```

### Example 2: HNSW Index Benchmark

```python
from vectordb.benchmarks.recall import measure_recall_at_k
from vectordb.benchmarks.latency import measure_p99_latency
from vectordb.indexes.hnsw import HnswConfig

def benchmark_hnsw(ground_truth: dict, queries: list, store):
    configs = [
        HnswConfig(m=8, ef_construction=64, ef_search=32),
        HnswConfig(m=16, ef_construction=128, ef_search=64),
        HnswConfig(m=32, ef_construction=256, ef_search=128),
    ]
    for cfg in configs:
        store.rebuild_index(config=cfg)
        recall = measure_recall_at_k(store=store, queries=queries, ground_truth=ground_truth, k=10)
        p99 = measure_p99_latency(store=store, queries=queries)
        print(f"m={cfg.m}, ef_c={cfg.ef_construction}, ef_s={cfg.ef_search}: recall@10={recall:.3f}, p99={p99:.1f}ms")
        if recall >= 0.95 and p99 <= 50.0:
            return cfg
    raise RuntimeError("No config met SLO")
```

### Example 3: Incremental Indexing with Corpus Versioning

```python
from vectordb.vector import Vector
from vectordb.corpus import CorpusVersion
from vectordb.stores.qdrant import QdrantAdapter
import time

class Indexer:
    def __init__(self, store: QdrantAdapter, embedder, corpus_version: CorpusVersion):
        self.store = store
        self.embedder = embedder
        self.corpus_version = corpus_version

    def upsert_batch(self, items: list[dict]) -> int:
        texts = [i["text"] for i in items]
        embeddings = self.embedder.embed_batch(texts)
        vectors = [
            Vector(
                id=item["id"],
                embedding=emb,
                metadata={
                    "text": item["text"],
                    "doc_id": item["doc_id"],
                    "tenant_id": item["tenant_id"],
                    "corpus_version": self.corpus_version.version,
                    "indexed_at": int(time.time()),
                    **item.get("metadata", {}),
                },
            )
            for item, emb in zip(items, embeddings)
        ]
        self.store.upsert_batch(vectors)
        return len(vectors)

    def delete_document(self, doc_id: str, tenant_id: str) -> None:
        self.store.delete(filter={"doc_id": doc_id, "tenant_id": tenant_id})

    def compact(self) -> None:
        self.store.compact()
```

## 27. Common Mistakes

- **Mixing distance metrics**: What: cosine on a dot-product-trained model. Why: similarity scores meaningless; recall collapses. How to avoid: match metric to model training; document in `CorpusVersion`.
- **Untuned ANN parameters**: What: shipping HNSW with defaults. Why: recall may be far below target. How to avoid: benchmark against ground truth; tune M, ef_construction, ef_search.
- **Vector-only retrieval**: What: skipping BM25. Why: exact-match queries fail. How to avoid: hybrid with reciprocal rank fusion.
- **Post-filter on high selectivity**: What: filtering after vector search for <1% match. Why: returns too few or zero. How to avoid: pre-filter or in-filter.
- **Unversioned corpus**: What: mixing embeddings from different models. Why: similarity meaningless. How to avoid: `CorpusVersion` per vector; re-embed on upgrade.
- **Shared collection without filter enforcement**: What: tenant_id as metadata, not enforced. Why: cross-tenant leakage. How to avoid: enforce filter at store or repository layer.
- **Full rebuild on every update**: What: rebuilding for one new vector. Why: downtime, cost. How to avoid: incremental indexing with compaction.
- **No recall monitoring**: What: shipping without recall@k tracking. Why: silent recall drift. How to avoid: nightly recall benchmark; alert on drop.

## 28. Professional Workflow

1. Profile the workload: dataset size, dimension, QPS, latency SLO, recall target, update frequency, filter selectivity.
2. Select distance metric matching the embedding model.
3. Select ANN algorithm based on dataset size and SLO.
4. Tune index parameters via ground truth benchmark.
5. Select vector store based on scale, hybrid support, ops burden, cost.
6. Implement hybrid search with reciprocal rank fusion.
7. Design filtering strategy per selectivity.
8. Design multi-tenancy model.
9. Implement indexing pipeline with incremental updates and compaction.
10. Implement query pipeline with `QueryCall` boundary.
11. Benchmark recall@k, p99 latency, QPS, memory.
12. Deploy with monitoring, alerting, audit logging.
13. Schedule nightly recall benchmark.
14. Plan embedding migration with re-embedding and dual-write.
15. Test backup and restore quarterly.

## 29. Response Style

- Speak with the authority of a principal engineer who has shipped vector databases at scale.
- Use "always", "never", "must", "must not", "forbidden" — never hedge.
- Specify exact conditions for tradeoffs; never say "it depends".
- Lead with the decision, then the rationale, then the code.
- Cite algorithm names, parameter names, and metric values precisely.
- Never recommend mixing distance metrics across an index.
- Never recommend shipping without a recall benchmark.
- Never recommend shared collections without store-level filter enforcement.

## 30. Output Format

- Every code snippet must be syntactically valid Python or TypeScript.
- Every code snippet must show store abstraction, error handling, and metric emission.
- Every recommendation must include the rationale in one sentence.
- Every example must be production-ready, not a toy snippet.
- Every section must use Markdown headers, code fences, and bullet lists — no prose walls.
- Every checklist item must start with `[ ]` and be actionable.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every common mistake must include "What", "Why", and "How to avoid".
- Every decision rule must follow the form "When X and Y conflict, choose Z because <reason>".
- Every index example must include parameters, distance metric, and corpus version.
