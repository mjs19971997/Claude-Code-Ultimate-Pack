# Data and Traffic Scaling

Reference for scaling the data and traffic layers: caching and invalidation, connection pooling, read replicas, partitioning, sharding, queues and backpressure, CDN and rate limiting, with TypeScript, SQL and configuration examples. Verified against PostgreSQL declarative partitioning, PgBouncer 1.26.1 configuration reference, HTTP caching (RFC 9111 and RFC 5861 extensions), TypeScript 7.0 with `strict` (TypeScript blocks marked `// file:` were type-checked) and KEDA 2.21 scaler documentation (2026-10).

## 1. Order of operations

1. Fix queries, indexes and N+1 patterns; measure with the database's own statistics.
2. Pool connections so instance count does not translate into connection count.
3. Cache what is read often, changes rarely and tolerates staleness.
4. Offload to the edge (CDN) for public and cacheable content.
5. Move non-urgent work to queues; protect the system with limits.
6. Add read replicas for read-heavy load.
7. Partition large tables for pruning and maintenance.
8. Shard only when a single primary cannot handle writes or data volume after all of the above.

Each step adds consistency questions and operational load; stop when the goal is met.

## 2. Caching layers

| Layer | Examples | Notes |
|---|---|---|
| Browser | `Cache-Control`, ETag | Cheapest; controls client behavior |
| CDN / edge | Static assets, cacheable API GETs | Key by URL (and selected headers); purge by tag or key |
| Reverse proxy | nginx, Varnish | Micro-caching of hot, public responses for 1-5 s absorbs spikes |
| Application memory | In-process LRU | Fastest; per instance, so consistency is weaker |
| Shared cache | Redis, Memcached | Cross-instance; network hop; needs eviction and memory policy |
| Database | Buffer pool, materialized views | Automatic or explicit precomputation |

Strategies:

- Cache-aside (lazy): application reads cache, on miss loads from the source and writes the cache. Default choice; the application handles invalidation.
- Read-through / write-through: the cache layer loads or writes to the store; simpler for readers, ties the cache to the store.
- Write-behind: writes go to the cache and are persisted asynchronously; fast, risks loss on failure; use only with durable queues.
- Refresh-ahead: reload hot keys before expiry.

Invalidation options, from simplest to most precise: short TTLs; delete on write; versioned keys (`product:42:v17`, bump version on change); event-driven invalidation from a change stream; tag-based purge at the CDN. "There are only two hard things": decide who owns invalidation and what staleness the product accepts.

Stampede (thundering herd) protection: single-flight per key, TTL jitter, locks with short timeouts for expensive loads, stale-while-revalidate (serve stale while one request refreshes), negative caching for not-found with a short TTL, and early probabilistic refresh.

HTTP caching headers:

```text
Cache-Control: public, max-age=60, stale-while-revalidate=300, stale-if-error=86400
Cache-Control: private, no-store            # personalized or sensitive responses
Vary: Accept-Encoding, Accept-Language      # keys the cache by those request headers
ETag: "v17"                                 # conditional requests with If-None-Match
```

`stale-while-revalidate` and `stale-if-error` are defined in RFC 5861 and are supported by many CDNs and browsers; confirm support in your CDN. Never cache responses that depend on `Authorization` or cookies in a shared cache unless the key includes the identity and the response is marked appropriately.

Memory and eviction: set a maximum memory and an eviction policy (for Redis, `allkeys-lru` or `allkeys-lfu` for pure caches); track hit ratio, evictions, and latency; size by working set, not total data.

## 3. Connection pooling

Every database connection costs memory and process or thread resources. Many application instances with large pools can exceed the server's limit and degrade throughput even before the limit.

- Size application pools from Little's law: connections in use = queries per second × average query time. Keep them small (tens, not hundreds) per database.
- Put a pooler between many clients and the database. For PostgreSQL, PgBouncer in `transaction` pool mode lets thousands of client connections share a small server pool.

```ini
[databases]
app = host=10.0.0.5 port=5432 dbname=app

[pgbouncer]
listen_addr = 10.0.0.10
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 2000
default_pool_size = 20
max_prepared_statements = 200
```

- In transaction mode, session state does not persist across transactions: session-level `SET`, advisory locks held across transactions, `LISTEN/NOTIFY`, temporary tables and `WITH HOLD` cursors do not behave as in direct connections. Protocol-level prepared statements are supported when `max_prepared_statements` is non-zero; SQL-level `PREPARE` and `EXECUTE` are not tracked (see the PgBouncer docs).
- Bind the pooler to a private interface, use TLS between client and pooler where required, and keep `auth_file` out of version control.
- Monitor pool wait time and `cl_waiting`; a growing queue means the server-side pool is too small or queries are too slow.
- Serverless and short-lived functions need a pooler or a managed proxy; otherwise each invocation opens a connection.

## 4. Read replicas

- Replicas scale reads, not writes. Replication is asynchronous in most setups, so replicas lag the primary.
- Route by consistency need: reads after a user's own write go to the primary (or to a replica known to have caught up); reports, search pages and lists can use replicas.
- Techniques for read-your-writes: pin the session to the primary for a few seconds after a write, pass a position token (LSN) and wait on the replica, or read from the primary on first request after login or mutation.
- Monitor lag in seconds and bytes; fail reads over to the primary or return an error when lag exceeds a limit for correctness-critical paths.
- Replicas can serve long analytic queries; set conflict and timeout settings deliberately (in PostgreSQL, long queries on a hot standby can be canceled by replication conflicts).
- Use replicas as failover targets only if they are sized for the full load.

## 5. Partitioning

Partitioning splits one logical table into pieces inside one database. Benefits: partition pruning for queries that filter on the key, fast data retirement (drop or detach a partition instead of a huge `DELETE`), smaller indexes, parallel maintenance. It does not by itself add write capacity beyond one server.

PostgreSQL declarative range partitioning by time:

```sql
CREATE TABLE events (
    id         bigint GENERATED ALWAYS AS IDENTITY,
    tenant_id  bigint      NOT NULL,
    created_at timestamptz NOT NULL,
    payload    jsonb       NOT NULL,
    PRIMARY KEY (id, created_at)          -- the partition key must be part of the primary key
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2026_11 PARTITION OF events
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

CREATE INDEX ON events (tenant_id, created_at);   -- created on each partition

-- Retire old data without a long-running DELETE:
ALTER TABLE events DETACH PARTITION events_2026_11 CONCURRENTLY;
```

Guidelines: pick a key that appears in most queries' filters; keep partition counts moderate (hundreds, not tens of thousands); create future partitions ahead of time (cron job or the `pg_partman` extension); queries without the key scan all partitions. LIST and HASH partitioning also exist.

## 6. Sharding

Sharding spreads data and writes across independent databases. It is a last resort because it complicates joins, transactions, schema changes, backups and operations.

Shard key rules:

- High cardinality and even access distribution (tenant id with a skewed tenant is a hot shard; consider splitting large tenants).
- Most transactions touch one shard. Cross-shard queries are slow and cross-shard transactions need two-phase commit or sagas.
- Stable: changing a row's key means moving it.

Routing strategies: hash of key modulo N (simple, painful to resize), consistent or rendezvous hashing (minimal movement on change), range (good for scans, hot at the tail for monotonic keys), directory/lookup table (flexible, an extra hop and a component to protect).

Rendezvous (highest random weight) hashing needs no ring and moves only the keys belonging to an added or removed node:

```ts
// file: rendezvous.ts
import { createHash } from "node:crypto";

export class ShardRouter {
  constructor(private readonly shards: readonly string[]) {
    if (shards.length === 0) throw new Error("At least one shard is required");
  }

  shardFor(key: string): string {
    let best = this.shards[0]!;
    let bestScore = -1n;
    for (const shard of this.shards) {
      const digest = createHash("sha256").update(`${shard}:${key}`).digest();
      const score = digest.readBigUInt64BE(0);
      if (score > bestScore) {
        bestScore = score;
        best = shard;
      }
    }
    return best;
  }
}

// const router = new ShardRouter(["db-a", "db-b", "db-c"]);
// router.shardFor("tenant-42") -> "db-b" (stable until the shard list changes)
```

Resharding procedure: add the new shards, dual-write or capture changes, backfill moved keys, verify counts and checksums, switch reads, switch writes, retire old copies. Rehearse with production-sized data and keep the routing layer versioned so a rollback is possible.

Managed or built-in options exist (for example Citus for PostgreSQL, Vitess for MySQL, native sharding in MongoDB and distributed SQL databases); evaluate them before writing your own router, and check the current docs for each product's constraints.

Multi-tenant models: shared tables with a tenant column (densest; enforce the tenant predicate on reads and writes, optionally with row-level security), schema per tenant (middle), database per tenant (strong isolation, costly operations). Large tenants can move to their own shard.

## 7. Queues and backpressure

Use queues to decouple producers from consumers, absorb bursts and retry work. They shift load in time; they do not remove it, so consumer capacity must exceed average arrival rate.

- Choose delivery semantics: at-least-once is the norm, so consumers are idempotent (dedupe key or natural idempotency).
- Bound everything: queue length or age alerts, per-message size, retry count, and a dead-letter queue with an owner and a replay tool.
- Parallelism limits: in Kafka the number of partitions caps consumer parallelism per group; in SQS, concurrency is set by consumers and the visibility timeout must exceed processing time; use FIFO or ordering keys only when ordering is required, since they reduce throughput.
- Scale workers on queue depth or lag (KEDA, section 8 of [autoscaling-capacity.md](autoscaling-capacity.md)).
- Backpressure: when downstream is slower, signal upstream with bounded buffers, 429/503 with `Retry-After`, or pull-based consumption; do not buffer without limit.
- Poison messages: cap retries, move to the DLQ, alert.

Bulkhead with a bounded queue that sheds load when full:

```ts
// file: bulkhead.ts
export class OverloadedError extends Error {}

export class Bulkhead {
  private active = 0;
  private readonly waiters: Array<() => void> = [];

  constructor(
    private readonly maxConcurrent: number,
    private readonly maxQueue: number,
  ) {}

  async run<T>(fn: () => Promise<T>): Promise<T> {
    if (this.active < this.maxConcurrent) {
      this.active++;
    } else {
      if (this.waiters.length >= this.maxQueue) throw new OverloadedError("queue full");
      await new Promise<void>((resolve) => this.waiters.push(resolve)); // slot is handed over by release
    }
    try {
      return await fn();
    } finally {
      const next = this.waiters.shift();
      if (next) next();
      else this.active--;
    }
  }
}
```

Map `OverloadedError` to `503` with `Retry-After`, and export queue depth and rejection counters.

## 8. Rate limiting

Algorithms: fixed window (simple, bursty at boundaries), sliding window (smoother, more state), token bucket (allows controlled bursts), leaky bucket (smooth output), concurrency limits (cap in-flight requests; good for expensive endpoints).

In-process token bucket (per instance; for a global limit across instances keep state in a shared store such as Redis and perform the update atomically, for example with a Lua script or the store's atomic primitives):

```ts
// file: token-bucket.ts
export class TokenBucket {
  private tokens: number;
  private last: number;

  constructor(
    private readonly capacity: number,
    private readonly refillPerSecond: number,
    now: number = Date.now(),
  ) {
    this.tokens = capacity;
    this.last = now;
  }

  tryTake(cost = 1, now: number = Date.now()): boolean {
    const elapsed = Math.max(0, now - this.last) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsed * this.refillPerSecond);
    this.last = now;
    if (this.tokens < cost) return false;
    this.tokens -= cost;
    return true;
  }
}
```

Practices: limit by authenticated identity first and IP second; different limits per route cost; return `429 Too Many Requests` with `Retry-After`; publish limits to clients (the IETF `RateLimit` header fields are a draft; check the current status before depending on them); apply limits at the edge or gateway and again for expensive internal operations; exempt health checks deliberately; test limits under load.

## 9. CDN

- Cache static assets with long `max-age` and content-hashed file names (`app.3f9a1c.js`) plus `immutable`.
- Cache public API responses with short TTLs and `stale-while-revalidate`; normalize the cache key (ignore tracking query parameters, sort parameters, vary only on headers that matter).
- Use an origin shield or tiered cache so many edge locations do not all hit the origin on a miss.
- Purge by surrogate key or tag at content change; rate-limit purge calls.
- Protect the origin: allow only CDN traffic (authenticated origin pulls or allowlisted IP ranges and a shared header), and keep the origin able to handle a cold cache if the CDN fails.
- Measure cache hit ratio by route, bytes saved and origin load, not only overall hit ratio.
