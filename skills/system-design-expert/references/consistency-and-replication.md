# Consistency and Replication

Detail behind the decision rules in the main skill: what each isolation level allows, what replicas can show clients, how quorums behave, and sketches for the outbox, sagas and consistent hashing.

## Isolation levels in PostgreSQL

| Level | Dirty read | Non-repeatable read | Phantom read | Serialization anomaly (e.g. write skew) |
|-------|------------|---------------------|--------------|------------------------------------------|
| Read uncommitted (behaves as read committed) | No | Possible | Possible | Possible |
| Read committed (default) | No | Possible | Possible | Possible |
| Repeatable read (snapshot isolation) | No | No | No | Possible |
| Serializable (serializable snapshot isolation) | No | No | No | No |

Notes:
- Under read committed, an application-level read-modify-write (`SELECT balance` then `UPDATE balance = <computed>`) can lose updates. Use `UPDATE ... SET balance = balance - $1 WHERE ...`, `SELECT ... FOR UPDATE`, or a version column.
- Under repeatable read and serializable, PostgreSQL aborts conflicting transactions with a serialization failure (SQLSTATE `40001`). The application must retry the whole transaction.
- Write skew example: two doctors each check "at least one other doctor is on call" and both go off call. Only serializable, or an explicit lock on the rows that the check reads, prevents it.
- Other databases use the same names with different guarantees; check the specific engine's documentation.

## What replicas can show clients

Asynchronous replicas lag. Without extra measures a client can observe:

| Problem | Example | Mitigation |
|---------|---------|-----------|
| Read-your-writes violation | User saves a profile, reload shows the old one | Read from the leader for a short window after a write, or wait until the replica has replayed the client's last write position |
| Monotonic reads violation | Refresh shows a comment, next refresh hides it | Pin a session to one replica, or track the highest position seen |
| Consistent prefix violation | An answer appears before its question | Keep causally related writes in one partition, or carry causal metadata |

Synchronous replication to at least one replica removes data loss on leader failure at the cost of write latency and availability when that replica is slow.

## Quorums

With N replicas, writes wait for W acknowledgments and reads query R replicas.

- W + R > N means every read set overlaps every write set, so a read sees at least one copy of the latest acknowledged write.
- Typical choice: N = 3, W = 2, R = 2. Tolerates one unavailable replica for both reads and writes.
- W = N, R = 1 favours reads; W = 1, R = N favours writes; both lose availability when any replica is down for the side that needs all N.
- Quorums alone are not linearizable: concurrent writes, sloppy quorums with hinted handoff, and a write that fails on some replicas but succeeds on others can all produce stale or conflicting reads. Use version vectors, conflict-free replicated data types, or a consensus-based store when linearizability matters.

## Consensus sizing

| Nodes | Majority | Failures tolerated |
|-------|----------|--------------------|
| 3 | 2 | 1 |
| 5 | 3 | 2 |
| 7 | 4 | 3 |

Even numbers add cost without adding tolerance. Spread members across failure domains (availability zones). Every write needs a majority round trip, so cross-region consensus groups pay inter-region latency on every commit.

## Transactional outbox

```sql
CREATE TABLE outbox (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  aggregate_id uuid        NOT NULL,
  event_type   text        NOT NULL,
  payload      jsonb       NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
CREATE INDEX outbox_unpublished ON outbox (id) WHERE published_at IS NULL;
```

The business change and the `INSERT INTO outbox` run in the same transaction. A relay publishes pending rows:

```typescript
import type { Pool } from 'pg';

export interface OutboxRow {
  id: string; // bigint arrives as a string from node-postgres
  aggregate_id: string;
  event_type: string;
  payload: unknown;
}

export async function relayBatch(
  pool: Pool,
  publish: (row: OutboxRow) => Promise<void>, // e.g. a Kafka producer send keyed by aggregate_id
): Promise<number> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const { rows } = await client.query<OutboxRow>(
      `SELECT id, aggregate_id, event_type, payload
         FROM outbox
        WHERE published_at IS NULL
        ORDER BY id
        LIMIT 100
        FOR UPDATE SKIP LOCKED`,
    );
    for (const row of rows) {
      await publish(row);
    }
    if (rows.length > 0) {
      await client.query('UPDATE outbox SET published_at = now() WHERE id = ANY($1::bigint[])', [
        rows.map((r) => r.id),
      ]);
    }
    await client.query('COMMIT');
    return rows.length;
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
```

- A crash after `publish` and before `COMMIT` republishes the batch: delivery is at least once, so consumers deduplicate by event id.
- Several relays with `SKIP LOCKED` scale throughput but can reorder events for the same aggregate. Run one relay, or shard relays by `aggregate_id` hash, when per-aggregate ordering matters.
- Change data capture (for example Debezium reading the write-ahead log) is an alternative relay that avoids polling.

## Sagas

An order saga with orchestration:

| Step | Action | Compensation |
|------|--------|--------------|
| 1 | Create order (pending) | Mark order cancelled |
| 2 | Reserve inventory | Release reservation |
| 3 | Authorize payment | Void authorization |
| 4 | Confirm order | (none; final step) |

- Persist saga state (current step, data, status) so the orchestrator resumes after a crash.
- Every step and compensation is idempotent and keyed by saga id.
- Order steps so the hardest-to-compensate action (charging money, sending email) comes last.
- Intermediate states are visible to other transactions; use semantic locks (a `pending` status) or commutative updates where that matters.
- Choreography (each service reacts to the previous event) suits short flows; orchestration suits longer flows that need visibility and timeouts. Workflow engines such as Temporal provide durable orchestration.

## Consistent hashing with virtual nodes

```typescript
import { createHash } from 'node:crypto';

function hash32(value: string): number {
  return createHash('md5').update(value).digest().readUInt32BE(0);
}

export class HashRing {
  private ring: { point: number; node: string }[] = [];

  constructor(private readonly virtualNodes = 128) {}

  add(node: string): void {
    for (let i = 0; i < this.virtualNodes; i++) {
      this.ring.push({ point: hash32(`${node}#${i}`), node });
    }
    this.ring.sort((a, b) => a.point - b.point);
  }

  remove(node: string): void {
    this.ring = this.ring.filter((entry) => entry.node !== node);
  }

  nodeFor(key: string): string {
    if (this.ring.length === 0) throw new Error('hash ring is empty');
    const h = hash32(key);
    let lo = 0;
    let hi = this.ring.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (this.ring[mid]!.point < h) lo = mid + 1;
      else hi = mid;
    }
    return this.ring[lo === this.ring.length ? 0 : lo]!.node;
  }
}
```

- MD5 is used here only for distribution, not security.
- Adding a node to an N-node ring moves about 1/(N + 1) of the keys; more virtual nodes give a more even spread.
- An alternative used by many databases: a fixed, large number of logical partitions (for example 4,096) assigned to nodes through a directory; rebalancing moves whole partitions.
