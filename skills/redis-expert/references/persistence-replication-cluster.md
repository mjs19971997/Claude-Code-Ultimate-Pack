# Redis Persistence, Replication, Sentinel and Cluster

Durability settings, replication, high availability, sharding, eviction, ACL and TLS configuration, Valkey notes, and day-two operations. Verified against Redis Open Source 8.10.3 and Valkey 9.1.3 (2026-10). Config directive names below are long-standing; check the docs for your exact version before copying values.

## Contents
- Persistence
- Replication
- Sentinel
- Cluster
- Memory and eviction
- ACL and TLS configuration
- Valkey notes
- Operations

## Persistence

| Mode | Directives | Behavior |
|---|---|---|
| RDB snapshot | `save <seconds> <changes>`, `dbfilename`, `dir`, `rdbcompression` | Point-in-time file written by a forked child (`BGSAVE`); fast restart, loses writes since the last snapshot |
| AOF | `appendonly yes`, `appendfsync always\|everysec\|no`, `auto-aof-rewrite-percentage`, `auto-aof-rewrite-min-size` | Logs every write; `everysec` risks about one second of writes, `always` is slowest |
| Hybrid | `aof-use-rdb-preamble yes` | AOF rewrite starts with an RDB-format preamble, then appends commands; faster loading |
| None | `save ""`, `appendonly no` | Pure cache; data is gone on restart |

- Since Redis 7.0 the AOF is a set of files (base plus incremental plus a manifest) under `appenddirname`; back up the whole directory, not single files.
- Fork time and copy-on-write memory grow with data set size and write rate; keep `maxmemory` well below host memory, and monitor `latest_fork_usec`.
- Test restore regularly: start a throwaway instance from the backup and check key counts and a sample of values. A backup that has never been restored is unverified.
- Use `redis-check-aof` and `redis-check-rdb` to inspect damaged files.
- Disk full, slow disks and `no-appendfsync-on-rewrite` choices affect latency; read the persistence docs before changing them.

## Replication

- Asynchronous primary to replica streaming; replicas use `replicaof <host> <port>`, `masterauth`/`masteruser` for ACL authentication, and `tls-replication yes` when TLS is on.
- Partial resync uses the replication backlog (`repl-backlog-size`); a replica offline longer than the backlog covers triggers a full sync (RDB transfer).
- `min-replicas-to-write N` and `min-replicas-max-lag S` make the primary refuse writes when too few replicas are in sync (more safety, less availability).
- `WAIT numreplicas timeout` blocks until replicas acknowledge earlier writes in this connection. It reduces the loss window but does not make Redis strongly consistent; `WAITAOF` does the equivalent for fsync on local and replica AOFs.
- Replicas are read-only by default (`replica-read-only yes`); reads from replicas may be stale.
- Diskless replication (`repl-diskless-sync`) avoids writing the RDB to disk on the primary.

## Sentinel

- Monitors a primary, performs automatic failover, and serves as the discovery endpoint for clients.
- Run an odd number of Sentinels, at least three, in separate failure domains. Quorum decides failure detection; a majority of Sentinels authorizes failover.
- Configuration: `sentinel monitor <name> <host> <port> <quorum>`, `sentinel auth-pass`/`sentinel auth-user`, `down-after-milliseconds`, `failover-timeout`.
- Sentinel does not shard. Clients connect through the Sentinel list: ioredis `new Redis({ sentinels: [...], name: "mymaster" })`; node-redis exposes a Sentinel client (see its docs).
- Secure Sentinel with its own ACL/password and TLS; it should not be reachable from untrusted networks.
- Do not run Sentinel and Cluster for the same data set.

## Cluster

- Keyspace split into 16384 hash slots; slot = CRC16(key) mod 16384, or of the hash tag content inside the first `{...}`.
- Minimum production layout: three primaries, each with at least one replica, spread across failure domains. Nodes talk over a cluster bus on port + 10000.
- Multi-key commands, `MULTI`, and scripts require all keys in one slot, otherwise `CROSSSLOT`. Cluster mode has one database (db 0).
- Redirections: `MOVED` (permanent slot move; the client updates its slot map) and `ASK` (temporary during migration). Use cluster-aware clients: node-redis `createCluster`, ioredis `Redis.Cluster`.
- Reshard with `redis-cli --cluster reshard`/`rebalance`; add nodes with `--cluster add-node`; use `CLUSTER FAILOVER` for planned failovers on a replica.
- `cluster-require-full-coverage yes` (default) stops serving when any slot is uncovered; `no` keeps serving covered slots, at the price of partial availability.
- Pub/Sub messages are broadcast across the cluster; sharded Pub/Sub (`SPUBLISH`/`SSUBSCRIBE`) scopes them to the slot's shard.
- Avoid hot slots: a few very hot keys or one shared hash tag defeats sharding.

```ts
import { createCluster } from "redis";

const cluster = createCluster({
  rootNodes: [{ url: "rediss://cache-0.internal:6379" }, { url: "rediss://cache-1.internal:6379" }],
  defaults: { username: process.env.REDIS_USER, password: process.env.REDIS_PASSWORD },
});
cluster.on("error", (e) => console.error("redis cluster error", e.message));
await cluster.connect();
// same slot thanks to the {t_42:u_981} tag, so multi-key operations are allowed
await cluster.mSet({ "{t_42:u_981}:cart": "[]", "{t_42:u_981}:wishlist": "[]" });
```

## Memory and eviction

- `maxmemory <bytes>` plus `maxmemory-policy`: `noeviction`, `allkeys-lru`, `allkeys-lfu`, `allkeys-random`, `volatile-lru`, `volatile-lfu`, `volatile-random`, `volatile-ttl`.
- Caches: `allkeys-lfu` or `allkeys-lru`. Mixed instances: `volatile-*` evicts only keys with TTL (keys without TTL then risk `OOM` write errors).
- Primary stores: `noeviction`; writes then fail with an OOM error when full, so alert on `used_memory / maxmemory`.
- Replication and client output buffers count toward memory; set `client-output-buffer-limit` for replica and pubsub classes deliberately.
- Expiry is lazy plus periodic sampling; expired keys can briefly stay in memory.
- Inspect with `INFO memory`, `INFO keyspace`, `MEMORY DOCTOR`, `MEMORY STATS`.

## ACL and TLS configuration

Keep users in an ACL file referenced from `redis.conf` with `aclfile /etc/redis/users.acl`. Passwords are stored as SHA-256 hashes (`#<hex>`); generate the hash outside the repository and inject the file from the secret store.

```
# /etc/redis/users.acl  (hashes shown as placeholders)
user default off
user app-cache on #<sha256-of-password> ~shop:* &shop:* +@read +@write +@connection -@dangerous
user app-worker on #<sha256-of-password> ~shop:* +@stream +@read +@write +@connection +eval +evalsha -@dangerous
user admin on #<sha256-of-password> ~* &* +@all
```

- Order matters: later rules override earlier ones; check the result with `ACL GETUSER <name>` and `ACL DRYRUN <name> <command> [args]`.
- `ACL LOG` lists denied commands and failed logins; review it after rollout.
- Key permissions can be split with `%R~pattern` (read) and `%W~pattern` (write); channels with `&pattern`.
- Restrict the admin user by network and use it only for operations.

TLS directives (server):

```
port 0
tls-port 6379
tls-cert-file /etc/redis/tls/server.crt
tls-key-file /etc/redis/tls/server.key
tls-ca-cert-file /etc/redis/tls/ca.crt
tls-auth-clients yes
tls-replication yes
tls-cluster yes
```

- Builds need TLS support compiled in (official packages and images include it).
- `tls-auth-clients yes` requires client certificates (mutual TLS); `optional` and `no` relax that.
- Rotate certificates with `CONFIG SET tls-cert-file ...` followed by reload settings per the docs, or restart replicas first.
- node-redis: `socket: { tls: true, ca: <PEM> }` (options of `tls.connect`); ioredis: `tls: { ca, servername }`. Verify server certificates; never set `rejectUnauthorized: false` in production.

## Valkey notes

- Valkey is a BSD-3 fork of Redis 7.2.4 hosted by the Linux Foundation; latest stable release line at the time of writing is 9.1 (9.1.3), with 9.0, 8.1 and 8.0 maintenance releases also current on its releases page.
- Core data types, replication, Sentinel, Cluster, ACL, TLS and the RESP protocol follow Redis 7.2 behavior. Features added in Redis 7.4 and later (such as hash field expiration, Redis 8 built-in modules, or new 8.x commands) exist in Valkey only if its release notes say so: check per command.
- JSON, search and probabilistic types are separate Valkey module projects rather than built-ins; check valkey.io for their current status.
- node-redis and ioredis connect to Valkey with the same URL and options; Valkey GLIDE is the Valkey project's own client library (check its docs for Node.js support).
- Pick by license, managed-service availability and required features, then pin the exact image tag.

## Operations

- Health: `PING`, `INFO server|memory|stats|replication|persistence|clients`, `CLIENT LIST`, `LATENCY LATEST`, `SLOWLOG GET 20`, `ROLE`.
- Safe key inspection: `SCAN 0 MATCH pattern COUNT 200 TYPE hash`, `TYPE`, `TTL`, `OBJECT FREQ` (with LFU policy), `OBJECT ENCODING`.
- Config changes at runtime: `CONFIG SET` then `CONFIG REWRITE`; keep `redis.conf` as the source of truth and restrict `CONFIG` to admins.
- Planned failover: on a replica run `CLUSTER FAILOVER` (Cluster), or `SENTINEL FAILOVER <name>` (Sentinel).
- Upgrade order: replicas first, fail over, then the old primary. Read the release notes for removed or changed commands and defaults between minor versions.
- Disable or protect expensive admin commands for application users through ACLs, not through renaming.
- `DEBUG`, `FLUSHALL`, `FLUSHDB`, `SHUTDOWN`, `CONFIG`, `REPLICAOF` belong to the admin user only.
