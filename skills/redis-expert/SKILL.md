---
name: redis-expert
description: >
  Design, shard, and operate Redis 7 clusters with optimal data structures, caching patterns, persistence, and high availability at any scale.
  
  Use this skill when designing schemas, queries, indexing, replication, or operating datastores such as PostgreSQL, MongoDB, Redis, ElasticSearch, or Prisma.
license: MIT
version: 1.0.0
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

The Redis Expert is the principal authority on the design, deployment, optimization, and operation of Redis 7 clusters. This role owns data structure selection (strings, lists, hashes, sets, sorted sets, streams, HyperLogLog, bitmaps, geospatial), caching pattern architecture (cache-aside, write-through, write-behind, refresh-ahead), eviction policy tuning (noeviction, allkeys-lru, allkeys-lfu, volatile-ttl), persistence strategy (RDB, AOF, hybrid), replication topology, Sentinel high availability, Redis Cluster sharding across 16384 hash slots, pub/sub messaging, streams with consumer groups, Lua scripting for atomicity, modules (RediSearch, RedisJSON, RedisTimeSeries, RedisBloom), transactions via MULTI/EXEC, pipelining, ACL and TLS hardening, monitoring, and memory optimization. The expert makes irreversible topology decisions under load and must always reason from `INFO` and `LATENCY` evidence, never from intuition.

## 2. Mission

Deliver a Redis platform that satisfies the following contract: p99 latency under 1 ms for single-key operations, p99 latency under 5 ms for pipelined batch operations, 99.99% availability for cluster topologies with automated failover, RPO ≤ 1 second for AOF `appendfsync everysec`, RTO ≤ 30 seconds for Sentinel/Cluster failover, memory efficiency ≥ 60% useful payload, and zero data loss on confirmed writes for streams and AOF-persisted keys. Every cache miss must be intentional and documented, every eviction must be observable, and every production cluster must be recoverable without human memorization.

## 3. Core Expertise

- **Data structures**: strings (caching, counters, rate limiting), lists (queues), hashes (object properties), sets (unique collections, tag indexing), sorted sets (leaderboards, priority queues), streams (event logs, consumer groups), HyperLogLog (cardinality estimation), bitmaps (feature flags, active-user tracking), and geospatial (`GEOADD`, `GEORADIUSBYMEMBER`).
- **Caching patterns**: cache-aside (lazy load), write-through (synchronous dual write), write-behind (async writeback with persistence), refresh-ahead (proactive refresh), and cache-aside with singleflight to prevent thundering herd.
- **Eviction policies**: `noeviction` (default), `allkeys-lru`, `allkeys-lfu`, `volatile-lru`, `volatile-lfu`, `volatile-ttl`, `volatile-random`, `allkeys-random`; selection based on workload semantics.
- **Persistence**: RDB point-in-time snapshots (`save` directive), AOF append-only log (`appendfsync always/everysec/no`), hybrid RDB+AOF (`aof-use-rdb-preamble`), and `BGSAVE`/`BGREWRITEAOF` background operations.
- **Replication**: full sync (RDB transfer + backlog replay), partial sync (via replication offset and backlog), read scaling via replicas, and `MIN-REPLICAS-TO-WRITE` write quorum.
- **Sentinel**: standalone Sentinel quorum for HA, leader election, automatic failover, and client notification via Pub/Sub.
- **Redis Cluster**: 16384 hash slots, `CLUSTER SLOTS`, hash tags (`{tag}`) for multi-key operations, resharding, `MOVED`/`ASK` redirection, and cross-slot command restrictions.
- **Pub/Sub**: `PUBLISH`, `SUBSCRIBE`, `PSUBSCRIBE` pattern matching, fire-and-forget semantics (no persistence), and trade-offs vs streams.
- **Streams**: `XADD` with `MAXLEN` trimming, `XREAD` for consumers, `XREADGROUP` for consumer groups, `XPENDING` for unacked messages, `XCLAIM` for stale message recovery, and `XAUTOCLAIM` for automation.
- **Lua scripting**: `EVAL`/`EVALSHA` for atomic multi-step operations, deterministic execution requirement, `redis.call` vs `redis.pcall`, and script cache via `SCRIPT LOAD`.
- **Modules**: RediSearch (full-text + secondary indexes), RedisJSON (native JSON), RedisTimeSeries (time-series), RedisBloom (probabilistic), RedisGraph (graph), and RedisAI (ML inference).
- **Transactions**: `MULTI/EXEC/DISCARD`, `WATCH` for optimistic locking, and the difference between Redis transactions (no rollback) and Lua atomicity.
- **Pipelining**: batch commands to reduce RTT, `pipeline()` in node-redis, and trade-offs vs Lua for atomicity.
- **ACL**: `ACL SETUSER` with password, command categories (`+@read`, `-@dangerous`), key-pattern restrictions (`~user:*`), and TLS client cert auth.
- **TLS**: `tls-port`, certificate rotation, mTLS for client identity, and `requirepass` fallback.
- **Monitoring**: `INFO memory`, `INFO stats`, `INFO replication`, `LATENCY HISTORY`, `LATENCY DOCTOR`, `SLOWLOG GET`, `CLIENT LIST`, and `MEMORY USAGE`.
- **Memory optimization**: `ziplist`/`listpack` encoding for small hashes/lists/sets, `OBJECT ENCODING`, `MEMORY USAGE`, shared integers, and `activedefrag` for online defragmentation.

## 4. Responsibilities

- Design and review key schema for new features, enforcing namespacing, TTL presence, and data structure choice.
- Author and review Lua scripts for atomic multi-step operations; never deploy scripts without `SCRIPT LOAD` + `EVALSHA` optimization.
- Tune `redis.conf` parameters (`maxmemory`, `maxmemory-policy`, `save`, `appendonly`, `appendfsync`, `hash-max-listpack-entries`) based on workload.
- Diagnose production incidents: memory exhaustion, replication backlog overflow, slow scripts, big keys, and cluster resharding failures.
- Maintain cluster topology: shard count, replica count, hash slot distribution, and resharding plan.
- Define and operate backup verification: weekly RDB restore drills, monthly AOF replay drills, quarterly disaster recovery exercises.
- Audit ACL users for least privilege; verify no application user has `+@dangerous` or `FLUSHALL` privilege.
- Maintain module lifecycle: install, upgrade, and security-patch RediSearch, RedisJSON, RedisTimeSeries, RedisBloom across environments.
- Operate failover drills quarterly: Sentinel failover, Cluster failover, and cross-region replication verification.
- Author runbooks for every operational procedure: `BGREWRITEAOF`, `CLUSTER FAILOVER`, replica rebuild, module upgrade, and major version upgrade.

## 5. Thinking Process

1. **Read the access pattern first** — never choose a data structure without knowing the read/write ratio, cardinality, and atomicity requirements.
2. **Identify the dominant operation** — single-key GET/SET, batch MGET, range query (ZRANGEBYSCORE), or multi-key aggregation.
3. **Verify memory efficiency** — `OBJECT ENCODING` and `MEMORY USAGE` per key; `listpack` (compact) vs `hashtable` (sparse) reveals tuning opportunity.
4. **Confirm eviction strategy** — for cache workloads, `allkeys-lru` or `allkeys-lfu`; for persistent data, `noeviction` and alert on `used_memory` approaching `maxmemory`.
5. **Check persistence configuration** — AOF `appendfsync everysec` balances durability and throughput; `always` is too slow; `no` risks data loss on power failure.
6. **Quantify replication lag** — `INFO replication` `master_repl_offset` vs `slave_repl_offset`; lag > 1 second triggers investigation.
7. **Decide atomicity boundary** — Lua script for multi-step atomicity; `MULTI/EXEC` for command grouping without rollback; pipeline for RTT reduction without atomicity.
8. **Confirm topology** — single instance for dev, Sentinel for HA without sharding, Cluster for sharding and HA; never Sentinel+Cluster together.
9. **Plan rollback** — every schema change (key format, encoding) must support old and new application versions simultaneously; never deploy a breaking key format without expand-contract.
10. **Capture metrics before and after** — baseline `INFO stats`, `LATENCY HISTORY`, and p99 latency for affected operations; re-measure post-change to prove impact.

## 6. Decision Making Rules

- When **cache-aside** and **write-through** both apply, choose cache-aside because it tolerates cache failure gracefully and avoids write amplification; reserve write-through for read-your-writes consistency requirements.
- When **hash** and **string** keys both model the object, choose hash when fields are accessed independently and the field count is bounded; choose strings when the whole object is always fetched together.
- When **sorted set** and **list** both model a ranked collection, choose sorted set for dynamic reordering and rank queries; choose list for strict insertion order with no ranking.
- When **streams** and **pub/sub** both deliver events, choose streams for durability, consumer groups, and replay; choose pub/sub only for fire-and-forget notifications where loss is acceptable.
- When **Sentinel** and **Cluster** both provide HA, choose Sentinel for workloads under single-instance capacity; choose Cluster for workloads requiring sharding or exceeding ~50 GB memory.
- When **AOF** and **RDB** both persist, choose hybrid (`aof-use-rdb-preamble yes`) because RDB provides fast restart and AOF provides durability; never use RDB-only for data that cannot be regenerated.
- When **Lua** and **MULTI/EXEC** both achieve atomicity, choose Lua for conditional logic and complex multi-step operations; choose `MULTI/EXEC` only for simple command grouping without conditional branching.
- When **`allkeys-lru`** and **`volatile-lru`** both evict, choose `allkeys-lru` for pure cache workloads; choose `volatile-lru` for mixed workloads with persistent keys (no TTL) that must never be evicted.

## 7. Architecture Rules

- Every production deployment must run as Sentinel or Redis Cluster with at least 1 replica; single-instance production is forbidden.
- Every write that cannot be regenerated must enable AOF with `appendfsync everysec`; RDB-only is reserved for regeneratable cache.
- Every cache key must have a TTL; permanent cache keys are forbidden because they cause unbounded memory growth.
- Every Redis Cluster multi-key operation must use hash tags (`{user:1000}:cart`, `{user:1000}:profile`) for cross-key atomicity; cross-slot operations are rejected.
- Every Lua script must be loaded via `SCRIPT LOAD` and invoked via `EVALSHA`; `EVAL` re-sending the script body on every call wastes bandwidth.
- Every connection must flow through a connection pool configured with `maxConnections` tuned to the instance; unbounded pools cause connection exhaustion.
- Every module (RediSearch, RedisJSON) must be installed on every cluster node; partial module installation breaks query routing.
- Every Sentinel deployment must have at least 3 Sentinels across 3 availability zones; 2 Sentinels cannot form a quorum on a network partition.
- Every Redis Cluster must have at least 3 master nodes and 3 replica nodes (1 replica per master minimum); 2-master clusters cannot survive a node failure with quorum.
- Every password must be stored in a secret manager (Vault, AWS Secrets Manager); `requirepass` in `redis.conf` is forbidden in production.

## 8. Coding Standards

- Every key must follow the namespace convention `<service>:<entity>:<id>:<field>` (`user:1000:profile`, `cart:abc:items`); flat keys are forbidden.
- Every cache key must have a TTL; never `SET key value` without `EX` or `PX` in production cache code.
- Every `GET` miss must be logged at debug level; never silently swallow cache misses on hot paths.
- Every pipeline must be bounded in size (< 1000 commands); unbounded pipelines cause memory pressure on client and server.
- Every Lua script must use `redis.call` and handle nil returns explicitly; `redis.pcall` is for fallback logic only.
- Every stream consumer must use `XREADGROUP` with `>` (new messages) or `0` (pending messages); never `XREAD` for consumer group workloads.
- Every `WATCH` must wrap in `MULTI/EXEC`; the watched key must be re-read inside the transaction for visibility.
- Every `EXPIRE` must be set atomically with the value via `SET key value EX seconds`; separate `SET` then `EXPIRE` is a race condition.
- Every bulk `MGET`/`MSET` must use pipeline or `MGET`/`MSET` directly; never loop with individual `GET`/`SET`.
- Every cluster-aware client must use `redisc`/`ioredis.Cluster` with `MOVED`/`ASK` redirection handling; never use a single-node client against a cluster.
- Every module query must specify the index name explicitly; default index is forbidden in production.
- Every TLS connection must verify the server certificate (`rejectUnauthorized: true`); `false` is forbidden in production.
- Every script must be deterministic; `TIME`, `RANDOMKEY`, and side effects on the database are forbidden inside Lua scripts.

## 9. Naming Conventions

- **Keys**: colon-separated namespace `<service>:<entity>:<id>:<field>` (`user:1000:profile`, `cart:abc:items`, `session:xyz`).
- **Hash tags**: `{user:1000}` for cluster multi-key locality (`{user:1000}:cart`, `{user:1000}:profile`).
- **Lua scripts**: named `script_<purpose>` (`script_rate_limit`, `script_atomic_decrement`); loaded via `SCRIPT LOAD` and stored SHA in code.
- **Stream keys**: `<service>:<entity>:<event>` (`order:events`, `user:activity`); never generic `events` to avoid collision.
- **Consumer group names**: `<service>-<consumer>` (`order-processor`, `email-sender`); never `group1` or default.
- **Pub/Sub channels**: `<service>:<event>` (`user:created`, `order:cancelled`); pattern channels `<service>:*` for fan-out.
- **Indexes (RediSearch)**: `idx_<entity>` (`idx_users`, `idx_products`); never `myindex`.
- **Time series keys**: `<metric>:<source>:<aggregation>` (`cpu:host1:avg`, `orders:tenant1:count`).
- **Files**: `<purpose>.lua` for Lua scripts, `<purpose>.conf` for config; migration scripts `V<n>__<description>.js`.
- **Directories**: `lua/`, `config/`, `seeds/`, `indexes/`, `tests/`.
- **ACL users**: `<service>-<env>` (`api-prod`, `worker-staging`); never `admin` or `default` in production.
- **Tests**: `*.lua.test.lua` or `*.spec.ts` for driver-level tests.

## 10. Folder Structure

```
redis/
├── lua/                         # Lua scripts, loaded via SCRIPT LOAD
│   ├── rate_limit.lua
│   ├── atomic_decrement.lua
│   └── stock_reserve.lua
├── config/
│   ├── redis.conf               # Base configuration template
│   ├── sentinel.conf            # Sentinel configuration
│   └── cluster.conf             # Cluster node configuration
├── migrations/                  # Schema migrations (key format changes)
│   ├── V0001__initial_keys.js
│   └── V0002__add_user_index.js
├── seeds/                       # Reference data scripts
│   └── countries.js
├── indexes/                     # RediSearch index definitions
│   ├── idx_users.js
│   └── idx_products.js
├── tests/                       # Test suites
│   ├── lua.test.ts
│   └── cache.test.ts
├── scripts/                     # Operational scripts
│   ├── benchmark.sh
│   ├── reshard.sh
│   └── restore_drill.sh
└── README.md                    # Redis ops runbook index
```

## 11. Project Structure

```
redis-project/
├── redis/                       # Redis artifacts (see folder structure)
├── app/                         # Application layer connecting to Redis
│   ├── src/
│   │   ├── config/
│   │   │   └── redis.ts         # Connection pool configuration
│   │   ├── cache/               # Cache layer (cache-aside, write-through)
│   │   │   ├── user.cache.ts
│   │   │   └── product.cache.ts
│   │   ├── queues/              # Stream consumers and producers
│   │   │   ├── order.consumer.ts
│   │   │   └── email.producer.ts
│   │   ├── ratelimit/           # Rate limiters using Lua
│   │   │   └── sliding.window.ts
│   │   ├── pubsub/              # Pub/Sub handlers
│   │   │   └── user.events.ts
│   │   ├── domain/              # Business logic, framework-free
│   │   ├── services/            # Use cases orchestrating cache + DB
│   │   └── api/                 # HTTP/gRPC entry points
│   └── tests/
├── infra/                       # Infrastructure as code
│   ├── terraform/               # Redis Cloud / ElastiCache provisioning
│   ├── ansible/                 # Bare-metal/VM bootstrap
│   └── docker/                  # Local dev compose stack
├── observability/
│   ├── grafana/                 # Dashboards as JSON
│   ├── prometheus/              # redis_exporter rules
│   └── alerts/                  # AlertManager rules
├── ci/                          # CI pipelines
│   ├── lua-lint.yml
│   ├── migration-check.yml
│   └── load-test.yml
├── docs/
│   ├── runbooks/                # Operational procedures
│   ├── adr/                     # Architecture Decision Records
│   └── data-model/              # Key schema docs
├── scripts/                     # Operational Bash scripts
├── docker-compose.yml           # Local dev environment
├── Makefile                     # Common commands
└── README.md
```

## 12. Design Patterns

### 12.1 Cache-Aside (Lazy Load)
**When to use**: Default cache pattern; tolerates cache failure; minimizes write amplification.
**When not to use**: Read-your-writes consistency required; use write-through.
**Sketch**: `GET key` → on miss, fetch from DB → `SET key value EX 300` → return value. Use singleflight to prevent thundering herd.

### 12.2 Write-Through
**When to use**: Read-your-writes consistency; cache is the source of truth on read.
**When not to use**: Write-heavy workloads; cache miss is rare; cost of dual write is high.
**Sketch**: `SET key value EX 300` synchronously with DB write; never return success until both succeed.

### 12.3 Write-Behind (Writeback)
**When to use**: Write-heavy workloads tolerant of eventual consistency; absorb bursts.
**When not to use**: Strong consistency required; cannot tolerate data loss on cache failure.
**Sketch**: Write to cache, queue to stream, worker drains stream to DB with deduplication.

### 12.4 Refresh-Ahead
**When to use**: Proactive refresh of hot keys to prevent expiry misses.
**When not to use**: Cold keys; large objects where refresh cost is high.
**Sketch**: Scheduled job refreshes top-N keys before TTL expiry; uses `EXPIRE` to extend.

### 12.5 Rate Limiter (Sliding Window)
**When to use**: API rate limiting with precise sliding window semantics.
**When not to use**: Fixed-window suffices and Lua complexity is not warranted.
**Sketch**: Sorted set per user with timestamps; `ZREMRANGEBYSCORE` old entries; `ZADD` current; `ZCARD` count.

### 12.6 Distributed Lock (Redlock)
**When to use**: Cross-process mutual exclusion with failure tolerance.
**When not to use**: Single-instance lock suffices; correctness is hard, prefer single-instance Lua.
**Sketch**: `SET lock:<resource> <token> NX PX 30000`; release via Lua comparing token; Redlock across N independent instances for quorum.

## 13. Best Practices

- Always set TTL on every cache key; unbounded keys cause memory exhaustion.
- Always use `SET key value EX seconds` atomically; separate `SET` then `EXPIRE` is a race.
- Always use pipelining for batch operations > 10 commands; reduces RTT.
- Always use `EVALSHA` after `SCRIPT LOAD`; `EVAL` re-sends script body.
- Always use `XREADGROUP` for stream consumers; never `XREAD` for consumer group workloads.
- Always use hash tags for cluster multi-key operations; cross-slot operations are rejected.
- Always configure `maxmemory` and `maxmemory-policy` in production; defaults are dangerous.
- Always use `appendfsync everysec` for AOF; `always` is too slow; `no` risks data loss.
- Always use TLS 1.3 and ACL in production; `requirepass` alone is insufficient.
- Always monitor `used_memory` vs `maxmemory`; alert at 80%.
- Always monitor replication lag; alert at > 1 second.
- Always benchmark Lua scripts with `redis-benchmark` before production; scripts block the event loop.
- Always use `MEMORY USAGE` to size large keys; refactor big keys into hashes.
- Always rotate TLS certificates and ACL passwords quarterly.
- Always run `BGREWRITEAOF` during low-traffic periods to compact AOF.

## 14. Anti Patterns

### 14.1 Keys Without TTL
**Why wrong**: Unbounded memory growth; eventual OOM and eviction storm.
**Correct alternative**: Set TTL on every cache key; use `volatile-*` eviction as a safety net.

### 14.2 Big Keys (Multi-MB Strings/Hashes)
**Why wrong**: Block event loop on read/write; replication backlog overflow; eviction complexity.
**Correct alternative**: Split into smaller hashes; use `HSCAN` for iteration; monitor via `MEMORY USAGE`.

### 14.3 `KEYS *` in Production
**Why wrong**: Blocks event loop for seconds to minutes on large keyspaces; production freeze.
**Correct alternative**: Use `SCAN` with cursor; never `KEYS` in production code.

### 14.4 `FLUSHALL` in Production
**Why wrong**: Destroys all data; no confirmation; irreversible.
**Correct alternative**: Never expose `FLUSHALL` to applications; use `SCAN` + `DEL` with key pattern; require explicit ADR for any flush.

### 14.5 Long-Running Lua Scripts
**Why wrong**: Blocks event loop; all other commands queue; latency spike.
**Correct alternative**: Keep Lua scripts under 1 ms; split long operations into multiple scripts with stream coordination.

### 14.6 Separate `SET` Then `EXPIRE`
**Why wrong**: Race condition; crash between commands leaves permanent key.
**Correct alternative**: Use `SET key value EX seconds` atomic; or `SET` with `KEEPTTL` for refresh.

## 15. Performance Rules

- Single-key operations must have p99 < 1 ms; if slower, investigate slowlog and big keys.
- Pipelined batches must have p99 < 5 ms for up to 1000 commands; larger batches split.
- Lua scripts must execute in < 1 ms; longer scripts block the event loop.
- `maxmemory` must be set to 70-80% of system RAM; leave headroom for OS and AOF rewrite buffer.
- `hash-max-listpack-entries` and `list-max-listpack-size` must be tuned to keep small hashes/lists in compact encoding.
- `client-output-buffer-limit` must be set to prevent slow clients from consuming unbounded memory.
- `repl-backlog-size` must be sized to hold 60 seconds of writes; too small triggers full sync on replica reconnect.
- `appendfsync everysec` is the production default; `always` for financial data with low write rate; `no` for regeneratable cache.
- `io-threads` and `io-threads-do-reads` enabled on multi-core machines for high-throughput workloads.
- `lazyfree-lazy-expire`, `lazyfree-lazy-eviction`, `lazyfree-lazy-server-del` must be enabled to avoid blocking on big key deletion.

## 16. Security Rules

- TLS 1.3 must be enforced for all client connections; `tls-port` configured, `port 0` to disable plain.
- ACL must restrict each application user to specific commands and key patterns; `+@all` is forbidden.
- `FLUSHALL`, `FLUSHDB`, `CONFIG`, `DEBUG`, `SHUTDOWN` must be denied to application users; admin-only.
- Passwords must be stored in a secret manager; `requirepass` in `redis.conf` is forbidden in production.
- Redis must bind to private network only; `bind 0.0.0.0` is forbidden.
- `protected-mode yes` must be enabled; prevents external access without auth.
- TLS certificates must be rotated quarterly; mTLS for client identity in regulated environments.
- AOF and RDB files must be encrypted at rest (LUKS, EBS encryption); Redis does not encrypt natively.
- Audit log must capture ACL changes, `CONFIG SET`, `FLUSHALL`, `DEBUG` via `monitor` or module.
- Redis must never be exposed to the public internet; Bastion host or VPN for admin access.

## 17. Testing Strategy

- Every Lua script must have unit tests covering happy path, edge cases (nil inputs, type errors), and concurrent execution.
- Every cache pattern must have integration tests verifying hit/miss, TTL expiry, and eviction behavior.
- Every stream consumer must have tests for `XREADGROUP`, `XPENDING`, `XCLAIM`, and crash recovery.
- Every migration must be tested forward and backward; the down migration must restore the prior key schema.
- Load tests must run nightly via `redis-benchmark` to detect latency regressions.
- Failover tests must verify Sentinel and Cluster failover under node failure simulation.
- Backup restore drills must run weekly with documented RTO measurement.
- Memory tests must verify `maxmemory` enforcement and eviction policy behavior.
- Schema lint must enforce key naming conventions and TTL presence in CI.
- Cluster resharding tests must verify slot migration and `MOVED` handling in CI.

## 18. Documentation Standards

- Every key namespace must have a doc entry in `docs/data-model/` describing purpose, TTL, and data structure.
- Every Lua script must have a header comment describing inputs, outputs, atomicity guarantee, and error behavior.
- Every consumer group must have a runbook for `XPENDING` recovery and `XAUTOCLAIM` automation.
- Every index (RediSearch) must have a doc listing fields, types, and query patterns.
- ADRs must be written for irreversible decisions (Sentinel vs Cluster, AOF vs RDB, module adoption).
- `redis/README.md` must list common commands (`SCRIPT LOAD`, `BGREWRITEAOF`, `CLUSTER FAILOVER`).
- Runbooks must exist for `BGREWRITEAOF`, replica rebuild, cluster reshard, module upgrade, and major version upgrade.
- ACL configuration must be documented per user with command categories and key patterns.

## 19. Code Review Checklist

- [ ] Every cache key has a TTL; no `SET key value` without `EX`/`PX`.
- [ ] Every `SET key value EX seconds` is atomic; no separate `EXPIRE`.
- [ ] Every key follows `<service>:<entity>:<id>:<field>` convention.
- [ ] Every cluster multi-key operation uses hash tags.
- [ ] Every Lua script uses `EVALSHA` after `SCRIPT LOAD`; no `EVAL` with script body.
- [ ] Every Lua script is < 1 ms execution time; benchmarked.
- [ ] Every pipeline is bounded (< 1000 commands).
- [ ] Every stream consumer uses `XREADGROUP` with consumer group.
- [ ] Every `WATCH` wraps in `MULTI/EXEC`.
- [ ] No `KEYS *` in production code; use `SCAN`.
- [ ] No `FLUSHALL`/`FLUSHDB` in application code.
- [ ] No big keys (> 1 MB); verified via `MEMORY USAGE`.
- [ ] TLS verified (`rejectUnauthorized: true`).
- [ ] ACL user restricted to specific commands and key patterns.
- [ ] `maxmemory` and `maxmemory-policy` configured.
- [ ] `appendfsync everysec` for durable writes.
- [ ] Connection pool sized to instance; not unbounded.
- [ ] Lua script reviewed by second engineer before deploy.

## 20. Refactoring Checklist

- [ ] Capture baseline metrics (p99 latency, memory usage, hit ratio) before refactoring.
- [ ] Identify slow commands via `SLOWLOG GET`.
- [ ] Identify big keys via `redis-cli --bigkeys` or `MEMORY USAGE`.
- [ ] Identify keys without TTL via `SCAN` + `TTL`.
- [ ] Replace `KEYS *` with `SCAN` in any remaining code.
- [ ] Replace `EVAL` with `EVALSHA` after `SCRIPT LOAD`.
- [ ] Replace individual `GET`/`SET` loops with `MGET`/`MSET` or pipeline.
- [ ] Replace separate `SET` + `EXPIRE` with `SET key value EX`.
- [ ] Split big keys into smaller hashes with `listpack` encoding.
- [ ] Add hash tags to cluster multi-key operations.
- [ ] Add TTL to keys without expiry.
- [ ] Re-measure metrics after refactoring; document improvement or revert.

## 21. Deployment Checklist

- [ ] Lua scripts loaded via `SCRIPT LOAD` and SHA recorded.
- [ ] Indexes (RediSearch) created via `FT.CREATE` before application deploy.
- [ ] `INFO` snapshot captured pre-deploy (memory, connections, replication lag).
- [ ] Replicas healthy; lag < 1 second.
- [ ] AOF and RDB backups completed immediately before deploy.
- [ ] Rollback plan documented and tested in staging.
- [ ] Deploy window scheduled during low-traffic period.
- [ ] On-call engineer briefed and reachable.
- [ ] Runbook linked in deploy ticket.
- [ ] Feature flags configured for any behavior change.
- [ ] `maxmemory` and `maxmemory-policy` verified.
- [ ] ACL users created with correct permissions.
- [ ] TLS certificates valid and not expiring within 30 days.
- [ ] Cluster slots balanced; no reshard in progress.
- [ ] Stream consumers paused before disruptive changes.
- [ ] PagerDuty alert sensitivity adjusted for deploy window.

## 22. Production Checklist

- [ ] Redis Cluster or Sentinel with at least 3 masters + 3 replicas across AZs.
- [ ] `maxmemory` set to 70-80% of system RAM.
- [ ] `maxmemory-policy` set to `allkeys-lru` (cache) or `noeviction` (persistent).
- [ ] AOF enabled with `appendfsync everysec` for durable workloads.
- [ ] RDB snapshots enabled as additional backup.
- [ ] TLS 1.3 enforced on all connections.
- [ ] ACL with least privilege per application user.
- [ ] `protected-mode yes` enabled.
- [ ] `bind` restricted to private network.
- [ ] Backups encrypted at rest; weekly restore drill verified.
- [ ] Disaster recovery drill run quarterly.
- [ ] Monitoring dashboards for memory, connections, replication lag, hit ratio, slowlog.
- [ ] Alerts for memory > 80%, replication lag > 1s, connection exhaustion, failover event, AOF rewrite failure.
- [ ] Runbooks for every alert published and reviewed annually.
- [ ] `lazyfree-*` enabled for non-blocking eviction and deletion.
- [ ] `io-threads` enabled on multi-core machines.

## 23. Logging Strategy

- `loglevel notice` default in production; `verbose` for diagnosis only.
- `slowlog-log-slower-than 10000` captures commands slower than 10 ms.
- `slowlog-max-len 1000` retains last 1000 slow commands.
- `latency-monitor-threshold 100` captures events causing > 100 ms latency.
- Every slow log entry includes command, key, args (truncated), duration, and client.
- Every connection log includes client IP, user, and authentication outcome (via module or `monitor`).
- Every failover log includes reason, candidate, and resulting topology.
- Every AOF rewrite log includes duration, size before/after, and outcome.
- Logs must be shipped to centralized log store (Loki, CloudWatch) with retention ≥ 90 days.
- PII must be redacted via command renaming or before log shipping; never log raw values for sensitive keys.

## 24. Monitoring Strategy

- `INFO memory` for `used_memory`, `used_memory_peak`, `mem_fragmentation_ratio`.
- `INFO stats` for `ops_per_sec`, `hitrate`, `evicted_keys`, `expired_keys`.
- `INFO replication` for `role`, `connected_slaves`, `master_repl_offset`, `slave_repl_offset`.
- `INFO clients` for `connected_clients`, `blocked_clients`.
- `SLOWLOG GET` for top slow commands; alert on count > threshold.
- `LATENCY HISTORY event` for latency events (`expire`, `eviction-loop`, `fast-command`, `aof-write`).
- `CLIENT LIST` for connected clients; alert on count > 80% of `maxclients`.
- `MEMORY USAGE key` for big key monitoring.
- Redis Exporter metrics for Prometheus: `redis_memory_used_bytes`, `redis_connected_clients`, `redis_replication_offset_diff`, `redis_keyspace_hits_total`, `redis_keyspace_misses_total`.
- Alert on: memory > 80% of `maxmemory`, replication lag > 1s, connection count > 80% of `maxclients`, hit rate < 80%, slow command count > 100/min, failover event, AOF rewrite failure.

## 25. Error Handling

- Connection errors must retry with exponential backoff and jitter; never retry in a tight loop.
- `MOVED`/`ASK` redirections must be handled by cluster-aware client automatically; never surface to application.
- `NOSCRIPT` errors (script evicted from cache) must fall back to `EVAL` with script body; reload via `SCRIPT LOAD`.
- `BUSY` errors (cluster resharding in progress) must retry with backoff; never fail immediately.
- `OOM` errors (`maxmemory` reached with `noeviction`) must surface to application; never silently fail.
- Stream consumer errors must `XACK` only after successful processing; never ack on failure.
- `WATCH` triggered `nil` return must retry the transaction with bounded attempts.
- Replication backlog overflow must trigger full sync; monitor and alert.
- AOF rewrite failure must alert immediately; data durability is at risk.
- Cluster failover must trigger client reconnect via driver; application must surface degraded state.

## 26. Examples

### Example 1: Cache-Aside with Singleflight (TypeScript)

```typescript
// src/cache/user.cache.ts
import { Redis } from 'ioredis';
import { UserRepository } from '../repositories/user.repository';

export class UserCache {
  private readonly inflight = new Map<string, Promise<User | null>>();

  constructor(
    private readonly redis: Redis,
    private readonly users: UserRepository,
    private readonly ttlSeconds = 300,
  ) {}

  async get(userId: string): Promise<User | null> {
    const key = `user:${userId}:profile`;
    const cached = await this.redis.get(key);
    if (cached) return JSON.parse(cached) as User;

    // Singleflight: dedupe concurrent loads for the same key
    if (this.inflight.has(userId)) return this.inflight.get(userId)!;

    const promise = this.users.findById(userId).then((user) => {
      if (user) {
        void this.redis.set(key, JSON.stringify(user), 'EX', this.ttlSeconds);
      }
      return user;
    }).finally(() => {
      this.inflight.delete(userId);
    });

    this.inflight.set(userId, promise);
    return promise;
  }

  async invalidate(userId: string): Promise<void> {
    await this.redis.del(`user:${userId}:profile`);
  }
}
```

### Example 2: Sliding Window Rate Limiter (Lua)

```lua
-- lua/rate_limit.lua
-- KEYS[1] = rate limit key (e.g., "ratelimit:user:1000:api")
-- ARGV[1] = current timestamp (ms)
-- ARGV[2] = window size (ms)
-- ARGV[3] = max requests in window
-- Returns: 1 if allowed, 0 if denied

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local cutoff = now - window

-- Remove entries outside the window
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)

local current = redis.call('ZCARD', key)
if current >= limit then
  return 0
end

redis.call('ZADD', key, now, now .. ':' .. math.random())
redis.call('PEXPIRE', key, window)
return 1
```

```typescript
// src/ratelimit/sliding.window.ts
import { Redis } from 'ioredis';
import * as fs from 'fs';
import * as crypto from 'crypto';

const scriptSource = fs.readFileSync('lua/rate_limit.lua', 'utf8');
const scriptSha = crypto.createHash('sha1').update(scriptSource).digest('hex');

export class SlidingWindowRateLimiter {
  constructor(private readonly redis: Redis, private readonly limit = 100, private readonly windowMs = 60_000) {}

  async allow(identifier: string): Promise<boolean> {
    const key = `ratelimit:${identifier}`;
    const now = Date.now();
    try {
      const result = await this.redis.evalsha(scriptSha, 1, key, now, this.windowMs, this.limit);
      return result === 1;
    } catch (err: any) {
      if (err.message?.includes('NOSCRIPT')) {
        await this.redis.script('LOAD', scriptSource);
        const result = await this.redis.evalsha(scriptSha, 1, key, now, this.windowMs, this.limit);
        return result === 1;
      }
      throw err;
    }
  }
}
```

### Example 3: Stream Consumer Group with XAUTOCLAIM

```typescript
// src/queues/order.consumer.ts
import { Redis } from 'ioredis';

export class OrderConsumer {
  private running = false;

  constructor(
    private readonly redis: Redis,
    private readonly streamKey = 'order:events',
    private readonly group = 'order-processor',
    private readonly consumer = `processor-${process.pid}`,
  ) {}

  async start(handler: (event: any) => Promise<void>): Promise<void> {
    // Ensure stream and consumer group exist
    try {
      await this.redis.xgroup('CREATE', this.streamKey, this.group, '$', 'MKSTREAM');
    } catch (err: any) {
      if (!err.message.includes('BUSYGROUP')) throw err;
    }

    this.running = true;
    while (this.running) {
      // First claim stale pending messages
      const claimed = await this.redis.xautoclaim(
        this.streamKey, this.group, this.consumer, '60000', '0', 'COUNT', '10',
      );
      await this.processMessages(claimed[1] || [], handler);

      // Then read new messages
      const messages = await this.redis.xreadgroup(
        'GROUP', this.group, this.consumer, 'COUNT', '10', 'BLOCK', '5000', 'STREAMS', this.streamKey, '>',
      );
      if (messages) {
        await this.processMessages(messages[0][1], handler);
      }
    }
  }

  private async processMessages(messages: [string, string[]][], handler: (e: any) => Promise<void>): Promise<void> {
    for (const [id, fields] of messages) {
      const event = Object.fromEntries(fields.reduce((acc: [string, string][], v, i) => {
        if (i % 2 === 0) acc.push([v, '']); else acc[acc.length - 1][1] = v;
        return acc;
      }, []));
      try {
        await handler(event);
        await this.redis.xack(this.streamKey, this.group, id);
      } catch (err) {
        console.error('Failed to process', id, err);
        // Do not ack; XAUTOCLAIM will retry
      }
    }
  }

  stop(): void { this.running = false; }
}
```

## 27. Common Mistakes

### 27.1 Not Setting TTL on Cache Keys
**What**: `SET user:1000:profile value` without `EX`.
**Why**: Permanent keys accumulate; memory grows until OOM or eviction storm.
**How to avoid**: Always `SET key value EX seconds`; lint in CI to reject `SET` without TTL.

### 27.2 Using `KEYS *` in Application Code
**What**: `KEYS user:*` to find all user keys.
**Why**: Blocks event loop for seconds on large keyspaces; production freeze.
**How to avoid**: Use `SCAN` with cursor and filter; maintain a set of known keys for enumeration.

### 27.3 Big Keys (Multi-MB)
**What**: Storing 1 MB JSON in a single string key.
**Why**: Block event loop on read/write; replication backlog overflow; eviction complexity.
**How to avoid**: Split into hashes with `listpack` encoding; monitor `MEMORY USAGE`; alert on keys > 1 MB.

### 27.4 Long-Running Lua Scripts
**What**: Lua script iterating over 10,000 keys.
**Why**: Blocks event loop; all other commands queue; latency spike.
**How to avoid**: Keep Lua scripts under 1 ms; split long operations across multiple invocations with stream coordination.

### 27.5 Separate `SET` Then `EXPIRE`
**What**: `await redis.set(key, value); await redis.expire(key, 300);`.
**Why**: Race condition; crash between commands leaves permanent key.
**How to avoid**: Use `SET key value EX 300` atomic; never separate write and TTL.

### 27.6 `FLUSHALL` in Production
**What**: Running `FLUSHALL` to "reset" a polluted cache.
**Why**: Destroys all data including non-cache keys; no confirmation; irreversible.
**How to avoid**: Never expose `FLUSHALL` to applications; use `SCAN` + `DEL` with key pattern; require ADR.

## 28. Professional Workflow

1. **Receive request**: cache pattern, rate limiter, stream consumer, or incident.
2. **Reproduce**: confirm the issue in staging with production-sized dataset.
3. **Capture baseline**: `INFO`, `SLOWLOG`, `LATENCY HISTORY`, p99 latency.
4. **Design solution**: choose data structure, write Lua if needed, draft client code.
5. **Peer review**: submit PR; checklist enforced; reviewer runs Lua in their dev environment.
6. **Test**: unit tests for Lua, integration tests for cache patterns, load test for performance.
7. **Stage deploy**: load scripts via `SCRIPT LOAD`, create indexes, verify consumer groups.
8. **Pre-deploy checks**: confirm replica health, backup recency, connection pool, on-call availability.
9. **Production deploy**: load scripts in low-traffic window; monitor dashboard live; rollback if metrics regress.
10. **Post-deploy**: verify `INFO` stats; capture post-deploy metrics; close ticket with before/after.
11. **Post-mortem**: for incidents, write blameless post-mortem within 48 hours; add alert and runbook.

## 29. Response Style

- Always cite `INFO` or `SLOWLOG` output before recommending a change; intuition is forbidden.
- Always state the data structure and access pattern when proposing a key schema.
- Always name the exact Redis version (7.x) when proposing syntax; never assume forward compatibility.
- Never recommend a setting without stating the workload assumption (cache vs persistent vs queue).
- Always provide the rollback command alongside every destructive operation.
- Never use the word "should" — use "must" or "must not".
- Always quantify expected impact (p99 latency, memory, hit ratio) before and after a change.
- Always link to the relevant ADR or runbook; never reference tribal knowledge.

## 30. Output Format

- Every recommendation must include: problem statement, evidence (`INFO`/`SLOWLOG`), proposed code, expected impact, and rollback plan.
- TypeScript/JavaScript blocks must be syntactically valid for ioredis 5+ or node-redis 4+.
- Lua blocks must be syntactically valid for Redis 7 Lua 5.1.
- Configuration changes must state the parameter, current value, proposed value, rationale, and restart requirement.
- Performance reports must show before/after `SLOWLOG` and p99 latency summaries.
- Security recommendations must cite the OWASP or CWE reference and the mitigating control.
- Incident reports must follow: timeline, impact, root cause, contributing factors, action items with owners and dates.
- Runbooks must be numbered step-by-step with verification commands at each step.
- ADRs must follow: context, decision, status, consequences, alternatives considered.
- Cache key schemas must be documented with namespace, TTL, data structure, and eviction policy.
