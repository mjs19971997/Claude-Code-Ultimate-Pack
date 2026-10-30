# Redis Data Structures and Patterns

Type selection, key design, Redis 8 built-in types, hash field expiration, Streams details, and the atomicity toolbox. Verified against Redis Open Source 8.10.3, node-redis 6.3.1, ioredis 6.0.0 (2026-10). Command availability notes ("since X") come from the Redis command docs and node-redis typings; check the current docs for newer additions.

## Contents
- Type selection
- Key design
- Redis 8 built-in types
- Hash field expiration
- Sorted sets, HyperLogLog, bitmaps, geo
- Streams in detail
- Pub/Sub
- Pipelines, transactions, scripts, Functions
- Memory and encodings

## Type selection

| Need | Type | Notes |
|---|---|---|
| Cached blob, counter, flag, lock | string | `INCR`/`INCRBY` are atomic; values up to 512 MB but keep them small |
| Object with independent fields | hash | `HSET`, `HGET`, `HINCRBY`; per-field TTL with `HEXPIRE` |
| FIFO buffer, recent items | list | `LPUSH`/`RPOP`, `LMOVE`, `LTRIM`; no acknowledgement |
| Unique members, tags | set | `SADD`, `SISMEMBER`, `SINTER`; use `SSCAN` for large sets |
| Ranking, ranges by score, delayed jobs | sorted set | `ZADD`, `ZRANGE ... BYSCORE`, `ZREM`, `ZPOPMIN` |
| Durable event log, work queue | stream | consumer groups, at-least-once |
| Unique count, approximate | HyperLogLog | `PFADD`, `PFCOUNT`, about 12 KB per key |
| Flags by integer id | bitmap | `SETBIT`, `BITCOUNT`, `BITFIELD` |
| Nearby search | geo (sorted set) | `GEOADD`, `GEOSEARCH` |
| Nested documents, partial updates | JSON | `JSON.SET`, `JSON.GET` with paths (built in since Redis 8) |
| Search and secondary indexes | Query Engine | `FT.CREATE`, `FT.SEARCH`, `FT.AGGREGATE` over hashes or JSON |
| Metrics over time | time series | `TS.ADD`, `TS.RANGE`, retention and compaction rules |
| Membership, frequency, heavy hitters | probabilistic | Bloom, cuckoo, count-min sketch, top-k, t-digest |
| Similarity search | vector sets (beta) or Query Engine vector fields | check the current docs for stability |

## Key design

- Pattern: `<app>:<tenant>:<entity>:<id>[:<facet>]`, for example `shop:t_42:cart:u_981`. The tenant segment is mandatory for tenant-scoped data and is derived from the verified principal, never from request input alone.
- Hash tags for Cluster: `{t_42:u_981}:cart` and `{t_42:u_981}:profile` land in the same slot, so a script or `MULTI` can touch both. Tag only what must be together; a tag shared by everything creates a hot slot.
- Put a version in cached value formats (`v2`) or in the key (`user:v2:...`) so rollouts can coexist.
- Avoid user-controlled raw strings in keys when they can contain `:` or glob characters used with `MATCH`; encode or hash them.
- Do not put secrets or personal data in key names; names appear in `SLOWLOG`, `MONITOR`, `INFO keyspace` tooling and logs.

## Redis 8 built-in types

Redis Open Source 8 bundles what used to be Redis Stack modules: JSON, the Query Engine, time series, and the probabilistic types. Vector sets arrived as a beta type in 8.0. With node-redis, the `redis` package exposes these commands (`client.json.set`, `client.ft.search`, `client.ts.add`, `client.bf.add`); `@redis/client` alone has the core commands only.

```ts
import { createClient } from "redis";
const redis = createClient({ url: process.env.REDIS_URL }); // rediss:// URL from the secret store
redis.on("error", (e) => console.error(e.message));
await redis.connect();

await redis.json.set("shop:t_42:order:1001", "$", { status: "paid", items: [{ sku: "A1", qty: 2 }] });
await redis.json.numIncrBy("shop:t_42:order:1001", "$.items[0].qty", 1);
const order = await redis.json.get("shop:t_42:order:1001", { path: "$.status" });
```

Query Engine notes:
- Index definitions are part of the schema: create them with `FT.CREATE ... ON JSON PREFIX 1 shop:t_42:order:`; use one prefix per tenant or a TAG field plus a mandatory tenant filter on every query. Never build the query string from raw user input without escaping.
- Indexes consume memory and add write cost; index only queried fields.
- In Cluster, check the current docs for how the Query Engine distributes indexes and queries.

## Hash field expiration

`HEXPIRE key seconds [NX|XX|GT|LT] FIELDS numfields field [field ...]` sets a TTL on individual hash fields (since 7.4); `HPEXPIRE`, `HEXPIREAT`, `HPEXPIREAT`, `HTTL`, `HPTTL`, `HPERSIST` complete the family. When the last field expires the hash is removed. `HGETEX`, `HSETEX` and `HGETDEL` (since 8.0) read or write fields and adjust their expiry in one call.

```ts
// one hash per user holding session fields, each session with its own TTL
await redis.hSet("app:t_42:sessions:u_981", { "s_abc": sessionJson });
const codes = await redis.hExpire("app:t_42:sessions:u_981", "s_abc", 3600);
// per field: -2 no such field, 0 condition not met, 1 TTL set, 2 deleted (TTL in the past)
```

Notes: field TTLs are a Redis 7.4+ feature (check Valkey docs before using them there); keep the hash bounded; `SET`-style `KEEPTTL` semantics differ per command, so read the command page before overwriting fields.

## Sorted sets, HyperLogLog, bitmaps, geo

- Sorted set as scheduler: `ZADD jobs:due <epochMs> <jobId>`; workers `ZRANGE jobs:due 0 <now> BYSCORE LIMIT 0 50`, then claim each with `ZREM` (only the caller whose `ZREM` returns 1 owns the job) or a script.
- Leaderboards: `ZINCRBY`, `ZREVRANK`, `ZRANGE key 0 9 REV WITHSCORES`.
- HyperLogLog: unique visitors per day `PFADD uv:t_42:2026-10-30 <id>`; `PFMERGE` for ranges; about 0.81% standard error.
- Bitmaps: daily-active flags with `SETBIT` and `BITCOUNT`; offsets are user-id based, so large sparse ids waste memory.
- Geo: `GEOSEARCH places FROMLONLAT 2.35 48.85 BYRADIUS 5 km ASC COUNT 20`.

## Streams in detail

- `XADD key MAXLEN ~ 100000 * field value ...` appends and trims; use `MINID ~` for time-based retention. `~` allows approximate, cheaper trimming.
- `XGROUP CREATE key group $ MKSTREAM` starts at new entries; use `0` to process history. Create groups at deploy time, and treat `BUSYGROUP` as success.
- `XREADGROUP GROUP g c COUNT n BLOCK ms STREAMS key >` delivers new entries; reading with id `0` returns the consumer's own pending entries.
- `XACK key group id` removes an entry from the pending list. Entries not acked remain pending and are visible with `XPENDING`.
- `XAUTOCLAIM key group consumer min-idle-time start [COUNT n]` transfers entries idle longer than the threshold; loop with the returned next id until it is `0-0`. The reply includes ids of entries deleted from the stream.
- Delivery count is exposed by extended `XPENDING key group - + count`; after N attempts move the entry to a dead-letter stream and ack it.
- Redis 8.6 added idempotent producer options on `XADD` (`IDMP`, `IDMPAUTO`) according to the node-redis typings; check the Redis docs for semantics before relying on them.
- Delete or trim entries only after all groups have processed them; `XINFO GROUPS` shows lag.
- ioredis: `redis.xreadgroup("GROUP", group, consumer, "COUNT", 20, "BLOCK", 5000, "STREAMS", key, ">")`, with replies as raw nested arrays.

## Pub/Sub

- At-most-once, no history, no acknowledgement; a disconnected subscriber misses messages.
- A subscribing connection cannot run other commands (RESP2); use a dedicated connection (`client.duplicate()`).
- Sharded Pub/Sub (`SPUBLISH`, `SSUBSCRIBE`) keeps traffic within a slot's shard in Cluster.
- Use it for cache-invalidation hints and presence, with a Stream or database as the source of truth.

## Pipelines, transactions, scripts, Functions

- **Pipeline**: many commands in one round trip; no atomicity. node-redis auto-pipelines same-tick commands; explicit batches use `multi().execAsPipeline()`.
- **`MULTI/EXEC`**: commands run together without interleaving; a runtime error in one command does not roll back the others. `WATCH key` plus `MULTI` gives optimistic locking (EXEC returns null when a watched key changed).
- **`EVAL script numkeys key... arg...`**: atomic, runs on the main thread. Load once and call with `EVALSHA` (node-redis `defineScript` and ioredis `defineCommand` do this for you).
- **Functions** (Redis 7+): a library is loaded with `FUNCTION LOAD` and called with `FCALL name numkeys ...`; libraries are persisted and replicated, and `FUNCTION LIST`/`FUNCTION DUMP` manage them.

```lua
#!lua name=limits
local function incr_window(keys, args)
  local c = redis.call("INCR", keys[1])
  if c == 1 then redis.call("PEXPIRE", keys[1], args[1]) end
  return c
end
redis.register_function("incr_window", incr_window)
```

- Scripts and functions must not rely on non-declared keys; in Cluster all keys must hash to one slot.
- Keep scripts short; a long script blocks the server (`busy-reply-threshold`, formerly `lua-time-limit`, only lets other clients receive `BUSY` errors; it does not interrupt the script).
- `redis.call` raises on command errors; `redis.pcall` returns an error table.

## Memory and encodings

- Small hashes, lists, sets and sorted sets use compact listpack encoding under size and entry-count thresholds (`hash-max-listpack-entries`, `hash-max-listpack-value`, and the corresponding settings for other types); `OBJECT ENCODING key` shows what is in use.
- `MEMORY USAGE key SAMPLES 0` measures one key; `redis-cli --bigkeys` and `--memkeys` sample the keyspace (they use `SCAN`, but run them off-peak).
- Memory per key has overhead; millions of tiny keys can cost more than grouping fields into bounded hashes.
- `UNLINK` frees large values in a background thread; `lazyfree-lazy-*` settings extend that to evictions and expiry (check the current defaults).
