# Redis Caching, Rate Limiting, Locks and Idempotency

Application patterns built on Redis: cache-aside with stampede control, invalidation, three rate limiter scripts, locks and Redlock trade-offs, idempotency records, and session storage. Verified against node-redis 6.3.1 and Redis Open Source 8.10.3 (2026-10). All examples assume a connected `redis` client created as in SKILL.md (ACL user, TLS, `error` listener).

## Contents
- Cache-aside with jitter and single-flight
- Invalidation
- Rate limiters
- Locks and Redlock
- Idempotency records
- Sessions

## Cache-aside with jitter and single-flight

```ts
import type { Redis } from "../infra/redis/client";

const inflight = new Map<string, Promise<unknown>>();

export async function cached<T>(
  redis: Redis,
  key: string,
  ttlSec: number,
  load: () => Promise<T | null>,
): Promise<T | null> {
  const hit = await redis.get(key);
  if (hit !== null) return hit === "null" ? null : (JSON.parse(hit) as T);

  const pending = inflight.get(key) as Promise<T | null> | undefined;
  if (pending) return pending; // collapse concurrent misses in this process

  const p = (async () => {
    const value = await load(); // source of truth, already tenant-scoped by the caller
    const jitter = Math.floor(Math.random() * ttlSec * 0.1); // spread expiry
    const ttl = value === null ? 30 : ttlSec + jitter; // short negative cache
    await redis.set(key, JSON.stringify(value), { expiration: { type: "EX", value: ttl } });
    return value;
  })().finally(() => inflight.delete(key));

  inflight.set(key, p);
  return p;
}

// key includes the tenant, taken from the authenticated principal
const userKey = (tenantId: string, userId: string) => `app:${tenantId}:user:v1:${userId}`;
```

- Single-flight only collapses requests inside one process. For a very hot key across many instances add a short `SET lock:<key> token NX PX 5000` lease so one instance reloads while others serve stale or wait briefly.
- Stale-while-revalidate: store `{ value, softExpiry }` with a longer hard TTL; serve stale after `softExpiry` and refresh in the background.
- Cache only data the caller may see, under a key that includes whatever scopes visibility (tenant, and role or user id for per-user views). A shared key for per-user data leaks it.
- Cache failures must not take the app down: treat Redis errors as a miss, with a timeout, and let the database serve.

## Invalidation

- Delete on write: `await redis.unlink(userKey(t, id))` after the transaction commits.
- Version keys: store `app:t:user-ver:<id>` and include its value in cache keys; bump with `INCR` to invalidate all derived entries without scanning.
- List caches: keep a per-tenant version (`app:t:orders:ver`) in the list cache key.
- Avoid wildcard deletion on the request path. When unavoidable, iterate with `scanIterator({ MATCH, COUNT })` and `UNLINK` in batches, off the hot path, and prefer tagging entries under a set of keys per entity.
- Event-based invalidation: publish an event (Stream or Pub/Sub hint) after commit; consumers delete keys.

## Rate limiters

All three keep their state transition inside one script so concurrent requests cannot interleave. Use `redis.eval(script, { keys, arguments })`, or `defineScript` to get `EVALSHA` caching. Scripts read time from the server (`TIME`) so client clocks do not matter. Identify the caller by the verified principal (tenant and user or API key id), then by IP as a fallback.

**Fixed window** (simple, allows a burst of up to 2x at a window boundary):

```lua
-- KEYS[1] counter key; ARGV[1] window ms; ARGV[2] limit
local c = redis.call("INCR", KEYS[1])
if c == 1 then redis.call("PEXPIRE", KEYS[1], ARGV[1]) end
local ttl = redis.call("PTTL", KEYS[1])
if c > tonumber(ARGV[2]) then return {0, 0, ttl} end
return {1, tonumber(ARGV[2]) - c, ttl}
```

**Sliding window log** (exact, memory grows with the limit):

```lua
-- KEYS[1] zset; ARGV[1] window ms; ARGV[2] limit; ARGV[3] unique request id
local t = redis.call("TIME")
local now = t[1] * 1000 + math.floor(t[2] / 1000)
redis.call("ZREMRANGEBYSCORE", KEYS[1], 0, now - tonumber(ARGV[1]))
local count = redis.call("ZCARD", KEYS[1])
if count >= tonumber(ARGV[2]) then
  local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
  return {0, 0, tonumber(oldest[2]) + tonumber(ARGV[1]) - now}
end
redis.call("ZADD", KEYS[1], now, ARGV[3])
redis.call("PEXPIRE", KEYS[1], ARGV[1])
return {1, tonumber(ARGV[2]) - count - 1, 0}
```

**Token bucket** (bursts up to capacity, steady refill):

```lua
-- KEYS[1] hash; ARGV[1] capacity; ARGV[2] refill tokens per second; ARGV[3] cost
local t = redis.call("TIME")
local now = t[1] * 1000 + math.floor(t[2] / 1000)
local capacity, rate, cost = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
local d = redis.call("HMGET", KEYS[1], "tokens", "ts")
local tokens, ts = tonumber(d[1]), tonumber(d[2])
if tokens == nil then tokens = capacity; ts = now end
tokens = math.min(capacity, tokens + (now - ts) / 1000 * rate)
local allowed = 0
if tokens >= cost then tokens = tokens - cost; allowed = 1 end
redis.call("HSET", KEYS[1], "tokens", tokens, "ts", now)
redis.call("PEXPIRE", KEYS[1], math.ceil(capacity / rate * 2000))
local retry = 0
if allowed == 0 then retry = math.ceil((cost - tokens) / rate * 1000) end
return {allowed, math.floor(tokens), retry}
```

Calling it from TypeScript:

```ts
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import type { Redis } from "../infra/redis/client";

// sliding-window.lua holds the sliding window script above, stored next to this module
const SLIDING = readFileSync(new URL("./sliding-window.lua", import.meta.url), "utf8");

export async function allow(redis: Redis, tenantId: string, subject: string, limit = 100, windowMs = 60_000) {
  const key = `rl:${tenantId}:${subject}`;
  const [ok, remaining, retryMs] = (await redis.eval(SLIDING, {
    keys: [key],
    arguments: [String(windowMs), String(limit), randomUUID()],
  })) as [number, number, number];
  return { allowed: ok === 1, remaining, retryAfterSec: Math.ceil(retryMs / 1000) };
}
```

- Fail open or closed on Redis errors is a product decision: fail open for general traffic, fail closed for expensive or abuse-prone endpoints.
- On 429 responses send `Retry-After`; the RateLimit header fields are an IETF draft, check its status (see rest-api-expert).
- In Cluster, one limiter key per call keeps the script single-slot.

## Locks and Redlock

Single-instance lock (see SKILL.md for the code): acquire with `SET key token NX PX ttl`, release with a script that deletes only if the stored token matches.

What it guarantees: with one healthy primary, at most one holder at a time while the lease is valid.

What it does not guarantee:
- Lease expiry while the holder is paused (garbage collection, network stall, slow I/O) lets a second holder in, and the first one continues unaware.
- Asynchronous replication: a failover right after acquisition can promote a replica that never saw the key.
- Clock jumps affect TTL on a server only through that server's own clock, but client-side timeout logic can be wrong.

Mitigations:
- Use locks for efficiency (avoid duplicate work), and make the protected operation safe to run twice.
- Use a fencing token: increment a counter on every acquisition (`INCR lock:fence:<name>`), hand it to the protected resource, and have that resource reject writes with an older token.
- Extend leases with a token-checked script (`if GET == token then PEXPIRE`) while work is in progress, with a hard upper bound.

Redlock (acquire the same lock on a majority of N independent Redis primaries, typically 5, within a validity time) reduces single-node failure risk but keeps the timing assumptions above; it is debated for correctness-critical use. If mutual exclusion must be correct under pauses and partitions, use a consensus-backed system (for example a database with row locks or a lease and fencing in the data store, or etcd/ZooKeeper-style coordination) rather than Redis alone. If you use Redlock, use a maintained library rather than your own implementation and read its documentation on clock drift and retries.

## Idempotency records

Store the outcome of a request under the client-supplied key so a retried request replays it. Scope the key by tenant and by the authenticated caller.

```ts
export async function idempotent(
  redis: Redis, tenantId: string, callerId: string, idemKey: string,
  requestHash: string, run: () => Promise<{ status: number; body: string }>,
) {
  const key = `idem:${tenantId}:${callerId}:${idemKey}`;
  const claimed = await redis.set(key, JSON.stringify({ state: "in_progress", requestHash }), {
    condition: "NX", expiration: { type: "EX", value: 24 * 3600 },
  });
  if (claimed !== "OK") {
    const rec = JSON.parse((await redis.get(key)) ?? "null");
    if (!rec) return { status: 409, body: "retry" }; // expired between calls
    if (rec.requestHash !== requestHash) return { status: 422, body: "key reused with a different payload" };
    if (rec.state === "in_progress") return { status: 409, body: "request in progress" };
    return rec.response; // replay the stored response
  }
  const response = await run();
  await redis.set(key, JSON.stringify({ state: "done", requestHash, response }), { expiration: { type: "EX", value: 24 * 3600 } });
  return response;
}
```

- If `run()` throws, delete the record (or store a retryable failure) so the client can retry.
- The business write and the idempotency record are in different systems; a crash between them can still double-apply. For money-like operations also enforce uniqueness in the database.
- The `Idempotency-Key` HTTP header is an IETF draft, check its status (see rest-api-expert).

## Sessions

- Store a random, unguessable session id as the key (`sess:<id>`) with value in a hash or JSON; set TTL on creation and refresh it with `EXPIRE` or `GETEX key EX seconds` on use (sliding expiry), with an absolute maximum lifetime stored in the value.
- Keep a per-user set of session ids (`user-sessions:<tenant>:<user>`) to support "sign out everywhere"; delete the keys and the set together in a script or `MULTI`.
- Do not store raw access tokens or secrets; store references or encrypted values. Authentication flows themselves belong to authentication-expert.
- Use `rediss://` and an ACL user restricted to `~sess:*` and `~user-sessions:*` for the session store.
