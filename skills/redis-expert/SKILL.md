---
name: redis-expert
description: >-
  Designs and operates Redis and Valkey: data structure choice, key design, caching, rate limiting, distributed locks, Streams consumer groups, Lua scripts and Functions, persistence, replication, Sentinel, Cluster, eviction, ACLs and TLS, with node-redis and ioredis. Use when working with redis.conf, redis-cli, SET NX PX, EVAL, XREADGROUP, HEXPIRE, SCAN, hash tags, memory or latency problems, or Redis JSON, Query Engine, time series and probabilistic types. Not for relational schemas (use postgresql-expert), document stores (use mongodb-expert), search clusters (use elasticsearch-expert), or HTTP caching headers (use rest-api-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Redis Expert

This skill covers using Redis (and the Valkey fork) as a cache, a data structure server, a coordination layer and a stream broker: choosing types and key layouts, bounding memory, keeping multi-step operations atomic, and running it safely with persistence, replication and access control. Examples use TypeScript with node-redis, with ioredis noted where the API differs.

> Verified against Redis Open Source 8.10.3 (latest 8.x; 8.12 RC1 pre-release), Valkey 9.1.3, node-redis 6.3.1 (`redis` and `@redis/client`, Node.js 20+), ioredis 6.0.0 (Node.js 20+, RESP3 default) (2026-10).

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

- Covered: data types and key design, TTLs and eviction, cache-aside and stampede control, rate limiters, locks, idempotency keys, Streams and Pub/Sub, Lua and Functions, pipelines and transactions, RDB/AOF, replication, Sentinel, Cluster, ACL and TLS, memory and latency diagnosis, Valkey differences.
- Not covered: relational modeling (postgresql-expert), document databases (mongodb-expert), full-text search clusters (elasticsearch-expert), HTTP cache headers and ETags (rest-api-expert), rate limiting policy at the API level (api-security-expert).

## 2. Core Expertise

- **Types**: string, hash, list, set, sorted set, stream, bitmap, HyperLogLog, geo. Redis Open Source 8 also ships JSON, the Query Engine (full-text, secondary index, vector, geo), time series, probabilistic types (Bloom, cuckoo, count-min, top-k, t-digest) and vector sets (beta) in the default build, so Redis Stack is no longer a separate package.
- **Hash field expiration**: `HEXPIRE`, `HPEXPIRE`, `HTTL`, `HPERSIST` (since 7.4); `HGETEX`, `HSETEX`, `HGETDEL` arrived in 8.0. Use them for per-field TTLs (sessions, tokens) instead of splitting one hash into many keys.
- **Atomicity tools**: single commands, `MULTI/EXEC` (queued, no rollback, `WATCH` for optimistic checks), Lua `EVAL`/`EVALSHA`, and Functions (`FUNCTION LOAD`, `FCALL`; named libraries that persist and replicate with the data set).
- **Streams**: `XADD`, `XGROUP CREATE`, `XREADGROUP`, `XACK`, `XPENDING`, `XAUTOCLAIM` (and `XCLAIM`), trimming with `MAXLEN`/`MINID`. Delivery is at-least-once; consumers must be idempotent.
- **Persistence**: RDB snapshots, AOF with `appendfsync everysec`, and the default RDB-preamble AOF. Replication is asynchronous; `WAIT` narrows but does not remove the loss window.
- **Topologies**: standalone, primary plus replicas with Sentinel, Redis Cluster (16384 slots, hash tags, `MOVED`/`ASK`).
- **Licensing and forks**: Redis 7.2 and earlier are BSD-3; 7.4 to 7.8 are RSALv2 or SSPLv1; 8.0 and later are RSALv2, SSPLv1 or AGPLv3 at your option. Valkey (Linux Foundation fork of Redis 7.2.4) is BSD-3 and versions independently (9.x). Check license fit before choosing a version.

## 3. Workflow

1. State the access pattern first: read/write ratio, value size, cardinality, whether the data can be regenerated, and what happens on loss.
2. Pick the type that makes the dominant operation a single command (see decision rules), then design the key: `<app>:<tenant>:<entity>:<id>`.
3. Decide lifetime: every cache key gets a TTL with jitter; durable data gets a documented persistence and replication setting.
4. Decide the atomicity boundary: single command, `MULTI`, script/Function, or a pipeline when atomicity is not needed.
5. Decide the topology and key placement (hash tags for multi-key operations in Cluster) before writing scripts.
6. Create least-privilege ACL users and TLS config before the first deploy.
7. Measure: `OBJECT ENCODING`, `MEMORY USAGE`, `SLOWLOG`, `LATENCY DOCTOR`, `INFO` sections; compare against a baseline after each change.
8. Write failure-path tests: eviction, failover, reconnect, duplicate delivery, expired lock.

## 4. Decision Rules

- **Cache vs store**: if Redis loses the key and the app can rebuild it, use cache settings (`maxmemory` plus an eviction policy, TTLs, optional no persistence). If not, treat Redis as a primary store: AOF, replicas, backups, `noeviction`.
- **Hash vs string**: hash for objects whose fields are read or updated separately and are bounded; string (JSON text) when the whole value is always read and written together. Redis JSON when you need partial updates or indexing of nested documents.
- **Sorted set vs list**: sorted set for ranking, ranges by score, and scheduling (score = timestamp); list for plain FIFO.
- **Streams vs Pub/Sub vs list**: Streams for durable work with consumer groups and replay; Pub/Sub only when losing messages for disconnected subscribers is acceptable; avoid list-as-queue when you need acknowledgement.
- **Lua vs `MULTI/EXEC`**: scripts when later commands depend on earlier replies; `MULTI` for fixed command batches; pipeline when only round trips matter.
- **Scripts vs Functions**: Functions for logic that is deployed with the data set and versioned; `EVAL` for small, self-contained scripts shipped with the client.
- **Sentinel vs Cluster**: Sentinel (HA, one shard) while the data set and write rate fit one primary; Cluster to scale memory or writes. Do not combine them.
- **Eviction**: `allkeys-lru` or `allkeys-lfu` for pure caches; `volatile-*` only when some keys (without TTL) must never be evicted; `noeviction` for primary data, with alerts before `maxmemory`.
- **Locks**: a single-instance lock is fine for efficiency (avoid duplicate work); use a consensus system or fencing tokens when correctness depends on mutual exclusion.
- **Redis vs Valkey**: both speak the same core protocol for 7.2-era commands; Redis 8 modules (JSON, Query Engine, time series) are Redis features, and Valkey ships its own module projects. Check feature parity for each command before assuming it exists on both.

## 5. Coding Standards

- One shared client per process (node-redis multiplexes one connection); never create a client per request. Use `duplicate()` for blocking commands (`XREADGROUP ... BLOCK`, `BLPOP`) and for subscribers.
- Register an `error` listener on every client; without one an error event crashes the Node process.
- Build keys only through helper functions in one module; include the tenant id in every tenant-scoped key.
- Namespace with `:`; use `{...}` hash tags only where several keys must share a slot, and keep the tagged group small.
- Set expiry in the same command that creates the value (`SET key v NX PX 30000`), never as a separate `EXPIRE` that can be skipped by a crash.
- Use `SCAN`-family iterators (`scanIterator`, `hScanIterator`) with `MATCH` and `COUNT`; never `KEYS` in production.
- Use `UNLINK` instead of `DEL` for large values.
- Pass user data as arguments (`KEYS[]`/`ARGV[]` in scripts), never concatenate it into Lua source; declare every key a script touches in `KEYS`.
- Serialize with JSON and a version field, or use Redis JSON; keep values small (a few KB) and avoid single keys holding millions of members.

## 6. Project Structure

```
src/
  infra/redis/
    client.ts        # createClient, TLS and ACL credentials from config, error handler, shutdown
    keys.ts          # key builders, tenant prefix, TTL constants
    scripts.ts       # Lua sources and defineScript wrappers (lock release, limiter)
  cache/
    user-cache.ts    # cache-aside with jitter and single-flight
  locks/lock.ts      # single-instance lock helper
  jobs/
    stream-consumer.ts   # XREADGROUP loop, XAUTOCLAIM sweep, XACK
tests/
  redis/             # integration tests against a real server (Testcontainers or CI service)
```

## 7. Design Patterns

- **Cache-aside**: read cache, on miss load from the source of truth, write with TTL plus jitter. Single-flight (in-process promise map, or a short `SET NX` lease) stops a stampede on hot keys.
- **Write invalidation**: delete (`UNLINK`) on write, or bump a per-entity version key and embed the version in cache keys; avoid wildcard deletes.
- **Negative caching**: cache "not found" briefly so missing ids do not hit the database.
- **Rate limiting**: fixed window (`INCR` + `PEXPIRE` in a script), sliding window (sorted set), token bucket (hash + script). All state transitions in one script.
- **Lock with lease**: `SET key token NX PX ttl`; release with a compare-and-delete script; extend only while holding the token; pair with a fencing token for writes to shared resources.
- **Idempotency record**: `SET idem:<tenant>:<key> in_progress NX PX ttl`, store the result under the same key when done, replay the stored result on retry.
- **Work queue**: Stream plus consumer group; periodic `XAUTOCLAIM` to reclaim entries idle past a threshold; dead-letter stream after N deliveries (read the delivery count from `XPENDING`).
- **Leaderboard and scheduling**: sorted set with `ZADD`, `ZRANGE ... REV`, `ZRANGEBYSCORE`; delayed jobs with score = due time.
- **Approximate counting**: HyperLogLog for unique counts, Bloom filter for membership pre-checks, top-k for heavy hitters.

## 8. Best Practices

- Keep keys human-readable and short enough that billions of copies do not dominate memory, but never encode secrets in them.
- Prefer many small hashes over one huge hash; small hashes, sets and sorted sets use compact listpack encoding.
- Batch with pipelines (node-redis auto-pipelines commands issued in the same tick; use `Promise.all`) and `MGET`/`HMGET`.
- Cap stream length at write time (`XADD ... MAXLEN ~ N` or `MINID ~`) so a stalled consumer cannot fill memory.
- Keep one logical operation within one slot in Cluster; design keys for that up front.
- Make consumers idempotent and acknowledge only after the side effect is durable.
- Version key formats and values so old and new application versions can coexist during rollout.
- Pin the server image to an exact version and read release notes before upgrading across minor versions.

## 9. Performance

- Redis executes commands on one main thread: one slow command blocks everyone. Avoid O(N) commands on large collections (`SMEMBERS`, `HGETALL`, `LRANGE 0 -1`, `SORT`) and long scripts.
- Round trips dominate: pipeline, use multi-key commands, or move logic server-side.
- Find big keys and hot keys (`redis-cli --bigkeys`, `--memkeys`, `MEMORY USAGE key`), and split them.
- Inspect `SLOWLOG GET`, `LATENCY DOCTOR`, `INFO commandstats`; investigate fork latency (`latest_fork_usec`) when RDB or AOF rewrites run.
- Set `maxmemory` below host memory to leave room for fork copy-on-write and buffers; watch `mem_fragmentation_ratio` and `evicted_keys`.
- Use `activedefrag` only after measuring fragmentation.
- RESP3 (default in ioredis 6, optional in node-redis) gives richer reply types and enables client-side caching; test your type mappings before switching.
- Client-side caching (node-redis `clientSideCache` with `RESP: 3`) suits read-heavy, rarely changing keys; the server invalidates entries.

## 10. Security

- Never expose Redis to the internet. Bind to private interfaces, keep `protected-mode yes`, firewall the port, and use TLS (`tls-port`, `tls-cert-file`, `tls-key-file`, `tls-ca-cert-file`; `tls-auth-clients yes` for mutual TLS) for any traffic leaving the host.
- Disable passwordless access: set `ACL SETUSER default off` (or give it a strong secret) and create one ACL user per application with only the commands and key patterns it needs. Manage users in an `aclfile` with hashed passwords (`#<sha256>`).
- Deny dangerous categories to application users (`-@dangerous`; this includes `FLUSHALL`, `CONFIG`, `KEYS`, `DEBUG`) and grant `+eval`/`+evalsha`/`+fcall` only to users that run scripts.
- Restrict pub/sub channels with `&pattern` rules and keys with `~pattern`, or read/write-specific `%R~` and `%W~` patterns.
- Keep credentials in a secret manager and inject through environment or mounted files; never commit them or put them in logs, URLs in error messages, or client bundles.
- Tenant isolation in a shared instance: key prefix per tenant plus an ACL key pattern per service, or separate instances for strong isolation. Do not rely on numbered databases (not available in Cluster, not an access boundary).
- Lua is sandboxed but has had serious vulnerabilities; keep Redis on patched releases and limit script rights.
- Treat cached data as untrusted on read: validate shape after `JSON.parse`; do not cache secrets or personal data longer than their source allows.
- `rename-command` is deprecated; use ACLs.

## 11. Testing

- Run integration tests against a real Redis or Valkey (Testcontainers or a CI service container), not a mock; scripts, expiry and Cluster slot rules cannot be mocked faithfully.
- Test TTL behavior with short real TTLs (for example `PEXPIRE` with a few hundred milliseconds), not fake timers around the client.
- Test failure paths: server restart (client reconnects), `maxmemory` eviction of cache keys, duplicate stream delivery, `XAUTOCLAIM` after a consumer crash, lock expiry mid-work.
- Test Cluster behavior with a real cluster (3 primaries) when using multi-key commands or scripts.
- Load-test with `redis-benchmark` or your app's traffic shape and look at latency percentiles, not averages.

## 12. Review Checklist

- [ ] Every key has an owner module, a tenant segment where applicable, and a TTL or a stated reason for none.
- [ ] No `KEYS`, `FLUSHALL`, unbounded `SMEMBERS`/`HGETALL`/`LRANGE` on user-growth data.
- [ ] Scripts take keys via `KEYS[]`, are small, and are slot-safe in Cluster.
- [ ] Locks use a token and compare-and-delete release; the caveats are documented where correctness matters.
- [ ] Stream consumers ack after success, reclaim stuck entries, and cap delivery attempts.
- [ ] Application ACL user has the minimum commands and key patterns; TLS enabled; no secret in code.
- [ ] `maxmemory` and the eviction policy match the cache-or-store decision.
- [ ] Client has an `error` handler, reconnect strategy, timeouts and graceful shutdown.

## 13. Production Notes

- Primary data: at least one replica, AOF `everysec`, Sentinel or Cluster, and tested restores of RDB or AOF files. Replication is asynchronous, so failover can lose recent writes.
- `min-replicas-to-write` and `min-replicas-max-lag` trade availability for a smaller loss window.
- Sentinel needs at least three Sentinels in separate failure domains; Cluster needs at least three primaries, each with a replica.
- Clients must follow redirects and topology changes (node-redis and ioredis cluster modes do); connect through the Sentinel or cluster seed list, not a single node.
- Upgrade replicas first, then fail over; read the release notes for command and config changes. Redis 8.x and Valkey 9.x have separate release lines and different config additions.
- Backups: copy RDB snapshots (or use AOF archives) off-host and restore them regularly.
- Persistence and replication details: [references/persistence-replication-cluster.md](references/persistence-replication-cluster.md).

## 14. Examples

Client with ACL user and TLS, credentials from the environment:

```ts
import { createClient } from "redis";

export type Redis = ReturnType<typeof createClient>;

export function makeRedis(): Redis {
  const client = createClient({
    username: process.env.REDIS_USER, // ACL user, e.g. "app-cache"
    password: process.env.REDIS_PASSWORD, // injected by the secret manager
    socket: {
      host: process.env.REDIS_HOST,
      port: Number(process.env.REDIS_PORT ?? 6379),
      tls: true,
      connectTimeout: 5_000,
      reconnectStrategy: (retries) => Math.min(retries * 100, 2_000) + Math.random() * 100,
    },
  });
  client.on("error", (err) => console.error("redis error", err.message)); // required: no listener = crash
  return client;
}
```

Single-instance lock: `SET NX PX` to acquire, token check-and-delete in Lua to release:

```ts
import { randomUUID } from "node:crypto";
import type { Redis } from "./client";

const RELEASE = `
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
end
return 0`;

export async function withLock<T>(
  redis: Redis, tenantId: string, name: string, ttlMs: number, fn: () => Promise<T>,
): Promise<T | null> {
  const key = `lock:${tenantId}:${name}`;
  const token = randomUUID();
  const ok = await redis.set(key, token, { condition: "NX", expiration: { type: "PX", value: ttlMs } });
  if (ok !== "OK") return null; // someone else holds it
  try {
    return await fn(); // must finish well within ttlMs; the lock can expire underneath you
  } finally {
    await redis.eval(RELEASE, { keys: [key], arguments: [token] });
  }
}
```

Caveats: if `fn` outlives the TTL, a second holder can enter (use a fencing token checked by the protected resource when that matters); a failover can lose the lock before replication; Redlock across several independent primaries narrows but does not remove clock and pause assumptions, so use a consensus store when correctness, not efficiency, depends on it. On Redis 8.4+ `SET ... IFEQ` can compare before overwriting, but the Lua release is portable across versions and Valkey.

Stream consumer group with reclaim and ack:

```ts
import type { Redis } from "./client";

const STREAM = "orders:events";
const GROUP = "billing";

export async function runConsumer(base: Redis, consumer: string, signal: AbortSignal) {
  const redis = base.duplicate(); // blocking reads need their own connection
  redis.on("error", (e) => console.error("redis error", e.message));
  await redis.connect();
  try {
    await redis.xGroupCreate(STREAM, GROUP, "$", { MKSTREAM: true });
  } catch (e) {
    if (!String(e).includes("BUSYGROUP")) throw e; // group already exists
  }
  let lastSweep = 0;
  while (!signal.aborted) {
    if (Date.now() - lastSweep > 30_000) {
      lastSweep = Date.now();
      // reclaim entries a crashed consumer left pending for over 60 s
      const claimed = await redis.xAutoClaim(STREAM, GROUP, consumer, 60_000, "0-0", { COUNT: 50 });
      for (const msg of claimed.messages) if (msg) await handle(redis, msg.id, msg.message);
    }
    const res = await redis.xReadGroup(GROUP, consumer, { key: STREAM, id: ">" }, { COUNT: 20, BLOCK: 5_000 });
    for (const stream of res ?? []) {
      for (const msg of stream.messages) await handle(redis, msg.id, msg.message);
    }
  }
  redis.destroy();
}

async function handle(redis: Redis, id: string, fields: Record<string, string>) {
  await processIdempotently(id, fields); // application code keyed by entry id
  await redis.xAck(STREAM, GROUP, id); // ack only after the effect is durable
}
declare function processIdempotently(id: string, fields: Record<string, string>): Promise<void>;
```

More examples (cache-aside, limiter scripts, hash field expiration, Functions) are in [references/caching-and-rate-limiting.md](references/caching-and-rate-limiting.md) and [references/data-structures-and-patterns.md](references/data-structures-and-patterns.md).

## 15. Common Mistakes

- `KEYS *` or `SMEMBERS` on large data in production; use `SCAN` and bounded reads.
- Caching without TTL or without `maxmemory`, then discovering unbounded growth or an OOM kill.
- `SET` followed by `EXPIRE` as two commands; a crash between them leaves a permanent key (and a permanent lock).
- Releasing a lock with a plain `DEL`, which can delete another client's lock after expiry.
- Treating a single-instance lock as a guarantee of mutual exclusion for correctness-critical writes.
- Using Pub/Sub for work that must not be lost, or a Stream consumer that acks before processing.
- Forgetting that a blocking command monopolizes the shared connection.
- Scripts that touch keys not passed in `KEYS`, which fail or misroute in Cluster.
- Wildcard invalidation with `KEYS`/`SCAN` + `DEL` on the request path.
- One giant hash or sorted set (big key) and `DEL` on it instead of `UNLINK`.
- Multi-key commands across slots in Cluster (`CROSSSLOT`) because hash tags were not planned.
- Running with the `default` user open, no TLS, or `+@all` for the application.
- Assuming replicas are consistent: reads from replicas can be stale, and failover can drop acknowledged writes.
- Assuming Redis 8 modules or hash-field commands exist on every server version or on Valkey without checking.

## 16. References

- [references/data-structures-and-patterns.md](references/data-structures-and-patterns.md): type selection, key design, Redis 8 built-in types, hash field expiration, Streams details, pipelines, transactions and scripts.
- [references/persistence-replication-cluster.md](references/persistence-replication-cluster.md): RDB and AOF, replication, Sentinel, Cluster, eviction, ACL and TLS configuration, Valkey notes, ops commands.
- [references/caching-and-rate-limiting.md](references/caching-and-rate-limiting.md): cache-aside with stampede control, invalidation, three rate-limiter scripts, locks and Redlock trade-offs, idempotency records, sessions.
- Official docs: https://redis.io/docs/latest/ , https://valkey.io/ , https://github.com/redis/node-redis , https://github.com/redis/ioredis
