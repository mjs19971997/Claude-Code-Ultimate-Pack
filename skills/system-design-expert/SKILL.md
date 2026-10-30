---
name: system-design-expert
description: >-
  Designs the internals of distributed systems: consistency models, CAP and PACELC trade-offs, partitioning, replication and quorums, consensus (Raft, Paxos), isolation levels, distributed transactions (saga, outbox), idempotency and exactly-once effects, queues vs logs, cache correctness and failure-mode analysis, with back-of-envelope estimates. Use when answering a system design question, choosing a datastore or replication scheme, picking a partition key, reasoning about stale reads or lost writes, designing an idempotent consumer, configuring Kafka durability, or enumerating failure modes. Not for org-wide or vendor-level solution design (use solution-architect), service boundaries and inter-service contracts (use microservices-expert), capacity, autoscaling and profiling (use scalability-expert), or domain modeling (use ddd-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# System Design Expert

This skill covers how distributed systems behave under concurrency and partial failure, and how to choose consistency, partitioning, replication and messaging so a design meets its correctness, availability, latency and durability targets. It includes estimation and failure-mode analysis for design interviews and real design reviews. It does not cover vendor selection and cost (solution-architect), service decomposition (microservices-expert) or load testing and autoscaling (scalability-expert).

> Verified against Kleppmann, Designing Data-Intensive Applications; Abadi's PACELC formulation; the Raft paper (Ongaro and Ousterhout); the PostgreSQL 18 documentation on transaction isolation; and the Apache Kafka documentation on producer and broker durability settings (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Design Standards](#5-design-standards)
6. [Design Document Structure](#6-design-document-structure)
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

- Requirements and estimation: traffic, data volume, read/write ratio, latency and durability targets.
- Data distribution: partitioning, replication, quorums, rebalancing, hot keys.
- Coordination: consensus, leader election, leases, fencing tokens, distributed locks.
- Consistency: models, isolation levels, anomalies, transactions across services.
- Messaging: queues vs logs, delivery semantics, ordering, idempotency.
- Failure: partitions, crashes, slow nodes, clock skew, retries and their side effects.

## 2. Core Expertise

- **CAP and PACELC.** During a network partition (P) a system chooses availability (A) or consistency (C); else (E), in normal operation, it trades latency (L) against consistency (C). PACELC is the more useful lens because partitions are rare and latency is constant.
- **Consistency models**, strongest to weakest: linearizable, sequential, causal, then session guarantees (read-your-writes, monotonic reads, monotonic writes, writes-follow-reads), then eventual. State which one each client-facing operation gets.
- **Isolation levels and anomalies:** read committed prevents dirty reads and writes; snapshot isolation (PostgreSQL REPEATABLE READ) also prevents non-repeatable reads and read skew but allows write skew; SERIALIZABLE (PostgreSQL uses serializable snapshot isolation) prevents write skew at the cost of retryable serialization failures.
- **Partitioning:** hash (even spread, no range scans), range (range scans, hot spots on sequential keys), consistent hashing with virtual nodes (adding a node moves about 1/N of the keys), directory or lookup table (flexible, extra hop and a component to keep available).
- **Replication:** single-leader (simple, write bottleneck, failover risk), multi-leader (local writes, conflict resolution), leaderless with quorums (W + R > N gives read/write overlap, but sloppy quorums and concurrent writes still need conflict handling such as version vectors or last-writer-wins with its data loss).
- **Consensus:** Raft and Multi-Paxos replicate a log across 2f + 1 nodes to tolerate f failures. Use a consensus-backed store (etcd, ZooKeeper, a Raft-based database) for leader election, configuration and locks rather than writing your own.
- **Leases and fencing:** a lock holder can pause (GC, VM migration) past its lease; protect the resource with a monotonically increasing fencing token that the storage layer checks.
- **Clocks:** wall clocks jump and drift; do not order events across machines by wall-clock timestamps. Use logical clocks, version numbers, or a database sequence.
- **Distributed transactions:** two-phase commit blocks if the coordinator fails and couples availability of all participants; sagas use local transactions plus compensations; the transactional outbox makes "change state and publish event" atomic.
- **Delivery semantics:** networks give at-most-once or at-least-once; "exactly once" in practice means at-least-once delivery plus idempotent processing (deduplication or idempotent writes).
- **Queues vs logs:** queues (SQS, RabbitMQ) distribute work and delete on acknowledge; logs (Kafka, Pulsar, Kinesis) retain ordered records per partition and support replay and multiple independent consumer groups.

## 3. Workflow

1. **Clarify functional scope** and the top three or four use cases; say what is out of scope.
2. **Quantify:** daily active users, requests per second (average and peak), read/write ratio, object sizes, retention, growth. Do the arithmetic out loud (see Examples).
3. **State the targets:** latency percentiles per operation, availability, RPO and RTO, and the consistency each operation needs.
4. **Sketch the high-level design:** clients, edge, services, datastores, queues, caches; then the request path for each main use case.
5. **Choose the data model and datastore** from access patterns, not habit; pick partition keys that keep each request on one partition.
6. **Choose replication and consistency** per dataset; write down what a client can observe during failover.
7. **Design messaging:** which interactions are synchronous, which are events; ordering keys; idempotency keys.
8. **Enumerate failure modes** per component (crash, slow, partitioned, corrupted, overloaded) and the system's response to each; check that retries cannot duplicate side effects.
9. **Identify bottlenecks and hot spots;** hand detailed capacity planning to scalability-expert.
10. **Write it up** with the trade-offs and the alternatives rejected; verify with failure-injection and consistency tests.

## 4. Decision Rules

- Choose the **weakest consistency that the business rule tolerates,** per operation: balances and inventory reservations often need linearizable writes; feeds and counters rarely do.
- **Single-leader relational database first.** It covers a large range of workloads; move to partitioned or leaderless stores when write volume, data size or availability targets exceed what one primary with replicas can deliver.
- **Hash partitioning** for point lookups with uniform access; **range partitioning** when range scans dominate, combined with a prefix or bucket to avoid sequential hot spots.
- **Saga over two-phase commit** across services; keep 2PC to a single database or tightly coupled resources that support XA and accept its blocking behaviour.
- **Log (Kafka-style)** when multiple consumers need the same events, ordering per key matters, or replay is needed; **queue** for task distribution with independent jobs.
- **Synchronous call** when the caller needs the result to answer its own client; otherwise publish an event and let consumers react.
- **Cache** only data whose staleness bound is known and acceptable; write down the bound.
- **Leader election and locks** come from a consensus system with fencing; never from a TTL key alone when correctness depends on mutual exclusion.

## 5. Design Standards

- Every write that crosses a process boundary carries an idempotency key or is naturally idempotent (upsert by key, conditional update on version).
- Every remote call has a deadline; deadlines propagate so downstream work stops when the caller has given up.
- Retries are bounded, use exponential backoff with jitter, and only target operations that are safe to retry.
- Every datastore has a documented partition key, replication factor and consistency setting.
- Every consumer commits its position only after its side effects are durable.
- Event schemas are versioned and evolve compatibly (add optional fields; never reuse or repurpose a field).
- Ordering guarantees are stated per key, never assumed globally.
- Names: topics `<domain>.<entity>.<event>.v<N>` (`orders.order.placed.v1`); metrics follow Prometheus conventions with base-unit suffixes (`_seconds`, `_bytes`, `_total`); span names follow OpenTelemetry semantic conventions.

## 6. Design Document Structure

```
system-design.md
  1. Problem and scope            # Use cases in and out of scope
  2. Requirements                 # Functional; NFR targets per operation
  3. Estimates                    # Traffic, storage, bandwidth, concurrency
  4. API                          # Main endpoints or RPCs and events
  5. Data model                   # Entities, access patterns, partition keys
  6. High-level design            # Diagram and request paths
  7. Consistency and replication  # Per dataset; behaviour during failover
  8. Failure modes                # Table: component, failure, detection, response
  9. Bottlenecks and evolution    # What breaks first at 10x and what we do then
  10. Alternatives considered     # And why they were rejected
```

## 7. Design Patterns

| Pattern | Problem it solves | Watch out for |
|---------|-------------------|---------------|
| Transactional outbox | Atomically change state and publish an event | Relay must be idempotent; consumers deduplicate |
| Idempotent consumer | At-least-once delivery without duplicate effects | Deduplication table growth; scope keys per consumer |
| Saga (orchestrated or choreographed) | Business transaction across services | Compensations are business actions, not rollbacks; isolation is lost between steps |
| Consistent hashing with virtual nodes | Rebalancing with minimal key movement | Hot keys still land on one node |
| Quorum reads and writes | Tunable consistency in leaderless stores | Not linearizable under sloppy quorums or concurrent writes |
| Read repair and anti-entropy | Converging divergent replicas (Merkle trees in Dynamo-style stores) | Background repair load |
| Fencing tokens | Safe mutual exclusion despite paused lock holders | Storage must check the token |
| Change data capture | Derive search indexes, caches and analytics from the database log | Schema changes propagate downstream |
| CQRS read models | Read shapes that differ from the write model | Eventual consistency; projection rebuilds |
| Circuit breaker and bulkhead | Stop cascading failure from a slow dependency | Tune thresholds from real latency data |

## 8. Best Practices

- Do the estimate before choosing technology; one order of magnitude changes the design.
- Keep the request path short: every synchronous hop multiplies failure probability and adds tail latency.
- Make ordering explicit with a partition key; one key per entity whose events must stay in order.
- Prefer conditional writes (`UPDATE ... WHERE version = $n`) or database constraints to application-level check-then-act.
- Treat replicas as stale by default; route read-your-writes reads to the leader or wait for the replica to reach the client's last written position.
- Design for replay: consumers rebuild state from the log, so handlers must be deterministic and idempotent.
- Keep the deduplication window at least as long as the maximum redelivery delay.

## 9. Performance

- Tail latency compounds with fan-out: if one backend call has a 1% chance of being slow, a request that calls 100 backends in parallel is slow most of the time. Use hedged or backup requests and timeouts for fan-out paths.
- Batch small writes and use pipelining on the wire; one round trip per item dominates at scale.
- Choose replication acknowledgment deliberately: waiting for more replicas raises durability and write latency together.
- Cross-region synchronous replication adds at least one inter-region round trip to every write.
- Detailed profiling, load testing and autoscaling are covered in scalability-expert.

## 10. Security

- Authenticate service-to-service calls (mTLS or signed workload tokens) and authorize per operation.
- Authenticate producers and consumers on brokers; restrict topics with ACLs.
- Treat messages as untrusted input: validate schemas at the consumer, bound sizes, and reject unknown versions safely.
- Idempotency keys must be scoped to the caller (tenant or user) so one client cannot replay or block another's operations.
- Encrypt replicas, backups and logs; deleting personal data must reach every replica, log and derived store.

## 11. Testing

- Failure injection: kill leaders, partition the network, add latency, skew clocks, and fill disks in a staging environment; check the documented response for each failure mode.
- Consistency checks: run concurrent clients and verify the stated model with a history checker (Jepsen-style tooling and its Elle checker are the reference approach).
- Duplicate and reorder messages deliberately in consumer tests; assert the end state is unchanged.
- Test failover end to end and measure the achieved RTO and RPO.
- Use real infrastructure in integration tests (Testcontainers) for brokers and databases; mocks hide delivery and isolation behaviour.

## 12. Review Checklist

- [ ] Estimates are written down and drive the choices.
- [ ] Consistency is stated per operation, including what clients see during failover.
- [ ] Partition keys keep hot paths on one partition; hot keys have a mitigation.
- [ ] Every cross-boundary write is idempotent; retries cannot double-charge, double-ship or double-email.
- [ ] Consumers commit offsets after side effects; a crash mid-processing is safe.
- [ ] No mutual exclusion relies on a TTL lock without fencing.
- [ ] No ordering relies on wall-clock timestamps across machines.
- [ ] Every remote call has a deadline and a bounded retry policy.
- [ ] The failure-mode table covers crash, slowness, partition and overload for each component.
- [ ] Alternatives and trade-offs are recorded.

## 13. Production Notes

- Monitor replication lag, consumer lag, in-sync replica count, leader elections, retry rates and dead-letter queue depth; they are the early signals of the failure modes in the design.
- Keep deduplication and outbox tables pruned on a schedule with an index on the age column.
- Run failover exercises regularly; leader election timing and client reconnection behaviour change with versions and configuration.

## 14. Examples

### Back-of-envelope estimate

```text
10M daily active users x 20 requests/day   = 200M requests/day
200M / 86,400 s                             ~ 2,300 requests/s average
Peak factor 3                               ~ 7,000 requests/s
Writes are 10% of requests                  ~ 700 writes/s at peak
Object size 1 KB, 20M new objects/day       ~ 20 GB/day ~ 7.3 TB/year before replication
Replication factor 3                        ~ 22 TB/year raw
Concurrency at peak (Little's Law, 50 ms)   7,000 x 0.05 = 350 requests in flight
```

### Kafka durability for order events

```properties
# Topic: replication factor 3, at least 2 in-sync replicas must acknowledge
replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false

# Producer
acks=all
enable.idempotence=true
# Consumer
enable.auto.commit=false
```

```text
1 broker down:  writes and reads continue (2 in-sync replicas remain).
2 brokers down: writes fail with NotEnoughReplicas; reads continue only if the
                surviving replica is in sync and becomes leader.
Trade-off:      acks=1 or min.insync.replicas=1 keeps writes available with one
                broker left, but a leader failure can lose acknowledged writes.
Decision:       orders are financial records; durability over write availability.
```

### Idempotent consumer with PostgreSQL

```sql
CREATE TABLE processed_events (
  consumer     text        NOT NULL,
  event_id     uuid        NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (consumer, event_id)
);
```

```typescript
import { Pool } from 'pg';

const pool = new Pool(); // connection settings from PG* environment variables

export async function onPaymentCaptured(event: { eventId: string; orderId: string }): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const dedup = await client.query(
      'INSERT INTO processed_events (consumer, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING',
      ['order-service', event.eventId],
    );
    if (dedup.rowCount === 1) {
      // First delivery: apply the effect. Conditional update keeps it safe even without dedup.
      await client.query(
        "UPDATE orders SET status = 'paid' WHERE id = $1 AND status = 'placed'",
        [event.orderId],
      );
    }
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err; // the caller does not commit the offset, so the message is redelivered
  } finally {
    client.release();
  }
}
```

The consumer commits its Kafka offset only after `onPaymentCaptured` resolves.

## 15. Common Mistakes

- **Assuming a reliable network.** No deadlines, unbounded retries, no failure handling. Every call needs a deadline, bounded retries and a defined fallback.
- **Strong consistency everywhere.** It costs latency and availability for operations that do not need it. Decide per operation.
- **Two-phase commit across microservices.** It blocks on coordinator failure and couples availability. Use a saga with an outbox.
- **Dual writes.** Writing to the database and then publishing to the broker loses or duplicates events on crash. Use an outbox or change data capture.
- **Auto-committed consumer offsets.** A crash after commit but before processing loses messages. Commit after the side effect is durable.
- **Retrying non-idempotent operations.** Retries turn timeouts into duplicate payments. Add idempotency keys first.
- **TTL locks for correctness.** A paused process outlives its lease and two writers proceed. Use fencing tokens or a conditional write.
- **Ordering by wall-clock time.** Clock skew reorders events and last-writer-wins drops data. Use versions or sequences.
- **Modulo hashing for a growing cluster.** Changing N remaps almost every key. Use consistent hashing or a fixed large number of logical partitions mapped to nodes.
- **Shared database across services.** It couples schemas and deployments. Each service owns its data and exposes it through an API or events.
- **No failure-mode table.** Unanticipated failures cascade. Enumerate them per component and test them.

## 16. References

- [references/consistency-and-replication.md](references/consistency-and-replication.md): isolation anomalies table, replication lag guarantees, quorum math, outbox relay and saga sketches, consistent hashing implementation.
