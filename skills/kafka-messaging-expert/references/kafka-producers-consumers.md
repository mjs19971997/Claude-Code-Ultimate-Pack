# Kafka Producers, Consumers and Delivery Guarantees

Client-side Kafka: producer durability and batching, idempotence, transactions, consumer groups (classic and KIP-848 protocols), offset commit strategies, rebalancing, share groups and the client libraries. Defaults were read from the Java client source of the 4.4 branch; Python snippets were checked against confluent-kafka 2.16.1 (librdkafka 2.16.0) for names and signatures but not run against a live broker (2026-10).

## Contents

1. [Producer durability and batching](#1-producer-durability-and-batching)
2. [Keys, partitions and ordering](#2-keys-partitions-and-ordering)
3. [Idempotence and transactions](#3-idempotence-and-transactions)
4. [Exactly-once semantics and its limits](#4-exactly-once-semantics-and-its-limits)
5. [Consumer groups and rebalancing](#5-consumer-groups-and-rebalancing)
6. [Offsets and commit strategies](#6-offsets-and-commit-strategies)
7. [Share groups (queues for Kafka)](#7-share-groups-queues-for-kafka)
8. [Client libraries](#8-client-libraries)

## 1. Producer durability and batching

Defaults in the 4.4 Java producer: `acks=all`, `enable.idempotence=true`, `linger.ms=5` (changed from 0 in 4.0), `batch.size=16384`, `delivery.timeout.ms=120000`, `transaction.timeout.ms=60000`. Set the values explicitly in code anyway so the intent survives a client change.

| Setting | Guidance |
|---|---|
| `acks=all` | Wait for the in-sync replicas. Durable only together with topic `min.insync.replicas=2` and `replication.factor=3` |
| `enable.idempotence=true` | Broker de-duplicates producer retries per partition; requires `acks=all`. Since 4.0 the client no longer silently falls back when `max.in.flight.requests.per.connection` exceeds 5 |
| `delivery.timeout.ms` | Upper bound on send plus retries; it must be at least `linger.ms + request.timeout.ms`. Retry by raising this, not by an application loop |
| `linger.ms`, `batch.size` | Larger batches raise throughput and compression ratio at the cost of latency. Tune with a benchmark of the real payload |
| `compression.type` | `lz4` or `zstd` are the usual choices; compress per batch, so batching matters |
| `max.request.size` | Default 1 MB; also check the topic `max.message.bytes` and the consumer `max.partition.fetch.bytes` together |

Always handle the delivery result. A fire-and-forget `send()` hides failures.

```python
import os
from confluent_kafka import Producer

producer = Producer({
    "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
    "acks": "all",
    "enable.idempotence": True,
    "compression.type": "lz4",
    "linger.ms": 10,
    "partitioner": "murmur2_random",  # match the Java client's key hashing
    "client.id": "orders-api",
})


def on_delivery(err, msg):
    if err is not None:
        # log with topic/key; alert or route to a fallback, never ignore
        print(f"delivery failed for key={msg.key()!r}: {err}")


producer.produce("orders.v1", key=b"order-42", value=b'{"id":42}', on_delivery=on_delivery)
producer.poll(0)      # serve delivery callbacks
producer.flush(30)    # on shutdown: wait for in-flight messages
```

## 2. Keys, partitions and ordering

- Order is guaranteed only within one partition. Records with the same key go to the same partition as long as the partition count does not change.
- Increasing partitions remaps keys; decreasing is not supported. Size partitions for the target consumer parallelism and growth up front, and treat a change as a migration.
- Java default partitioner: hash (murmur2) of the key; records without a key are spread by the built-in uniform sticky/adaptive logic. librdkafka's default partitioner is `consistent_random` (CRC32), so mixed Java and librdkafka producers need `partitioner=murmur2_random` on the librdkafka side to agree on key placement.
- Pick the key by the entity whose events must stay ordered (order id, account id). A skewed key (one hot tenant) produces a hot partition; check per-partition bytes in metrics.
- Per-partition order after a retry needs idempotence on (or `max.in.flight.requests.per.connection=1`).
- A consumer that fans out to worker threads loses order unless it dispatches by key or partition.

## 3. Idempotence and transactions

Idempotence removes duplicates caused by producer retries inside one producer session. It does not de-duplicate application-level re-sends, restarts that lose the producer id, or reprocessing by a consumer.

Transactions write to several partitions atomically and can commit consumer offsets in the same transaction (consume-transform-produce). Set `transactional.id` (stable and unique per producer instance, for example derived from the input partition or a pod ordinal) and `isolation.level=read_committed` on downstream consumers.

```java
Properties p = new Properties();
p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
p.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "enricher-" + instanceId);
p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);

try (KafkaProducer<String, String> producer = new KafkaProducer<>(p)) {
    producer.initTransactions();                       // fences older instances
    while (running) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));
        if (records.isEmpty()) continue;
        producer.beginTransaction();
        try {
            Map<TopicPartition, OffsetAndMetadata> offsets = new HashMap<>();
            for (ConsumerRecord<String, String> r : records) {
                producer.send(new ProducerRecord<>("out.v1", r.key(), transform(r.value())));
                offsets.put(new TopicPartition(r.topic(), r.partition()),
                            new OffsetAndMetadata(r.offset() + 1));
            }
            producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata());
            producer.commitTransaction();
        } catch (ProducerFencedException | OutOfOrderSequenceException | AuthorizationException e) {
            throw e;                                   // fatal: close the producer
        } catch (KafkaException e) {
            producer.abortTransaction();               // then reset consumer positions and retry
        }
    }
}
```

The input consumer must use `enable.auto.commit=false` and `isolation.level=read_committed`. After an abort, seek the consumer back to the last committed offsets before polling again.

Per the 4.0 upgrade notes, treat both `TimeoutException` and `TransactionAbortableException` during a transaction as a signal to abort, because retrying after a timeout risks duplicates. 4.0 also enables the strengthened transaction protocol (KIP-890) once the upgrade is finalized.

Python equivalent calls: `init_transactions()`, `begin_transaction()`, `produce(...)`, `send_offsets_to_transaction(offsets, consumer.consumer_group_metadata())`, `commit_transaction()`, `abort_transaction()`. Handle `KafkaException` and its `args[0].txn_requires_abort()` / `retriable()` / `fatal()` helpers (check the confluent-kafka docs for the exact semantics).

## 4. Exactly-once semantics and its limits

- Exactly-once in Kafka means: input offsets, output records and state changelogs commit atomically inside Kafka. Kafka Streams enables it with `processing.guarantee=exactly_once_v2`; plain clients need the transaction pattern above.
- It stops at the Kafka boundary. Writing to a database, calling an HTTP API or sending an email from the processing step is at-least-once; make those effects idempotent (natural key, unique constraint, idempotency key) or use the outbox pattern, see [patterns-outbox-dlq.md](patterns-outbox-dlq.md).
- A consumer with `read_uncommitted` (the default isolation level) sees aborted records. Use `read_committed` downstream of transactional producers.
- Transactions add latency (commit markers) and per-transaction overhead; batch many records per transaction rather than one.
- Participation in an external two-phase commit (KIP-939) is a separate, newer feature; confirm its status in the current release notes before relying on it.

## 5. Consumer groups and rebalancing

Two group protocols exist for the Java consumer:

- `group.protocol=classic` (the default in the 4.4 client): client-side assignment through `partition.assignment.strategy` (default list: RangeAssignor then CooperativeStickyAssignor), liveness by `session.timeout.ms` (45000) and `max.poll.interval.ms` (300000).
- `group.protocol=consumer` (KIP-848, generally available since Kafka 4.0): the broker computes assignments incrementally and members rebalance without a stop-the-world barrier. Select the server-side assignor with `group.remote.assignor`; session and heartbeat timing are then broker-side group settings. Client-side `partition.assignment.strategy` does not apply. Check the current docs for the list of settings that move to the broker before migrating.

Clusters accept both protocols at once; groups can move between them. Once new-protocol groups exist, a cluster downgrade is limited (see the 4.0 upgrade notes).

Rebalance hygiene (classic protocol):

- Keep the work done between `poll()` calls well below `max.poll.interval.ms`; lower `max.poll.records` or move long work to a bounded worker pool while polling continues with `pause()`/`resume()`.
- Use static membership (`group.instance.id`) for stateful or slow-starting consumers so a restart inside `session.timeout.ms` does not rebalance.
- Prefer the cooperative sticky assignor over eager ones. Commit processed offsets in `onPartitionsRevoked` (or `onPartitionsLost` handling) when committing manually.
- Parallelism is bounded by partition count: more consumers than partitions sit idle (share groups lift this limit, see section 7).

## 6. Offsets and commit strategies

Defaults: `enable.auto.commit=true`, `auto.offset.reset=latest`, `isolation.level=read_uncommitted`. Auto commit marks offsets from the previous `poll()` as done, so a crash mid-processing can skip or repeat records depending on timing.

| Strategy | Delivery | Notes |
|---|---|---|
| Auto commit | At-most-once or at-least-once, unpredictable | Acceptable only for tolerant workloads |
| Commit after processing (sync per batch) | At-least-once | Default recommendation; make the handler idempotent |
| Commit before processing | At-most-once | Records are lost if processing fails |
| Transactional offsets | Exactly-once inside Kafka | Section 3 |
| Offsets stored with the result in a database | Exactly-once effect for that database | Seek to stored offsets on assignment; rebalance listener required |

```python
import os
from confluent_kafka import Consumer, KafkaError

consumer = Consumer({
    "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
    "group.id": "billing-v1",
    "enable.auto.commit": False,
    "auto.offset.reset": "earliest",   # applies only when the group has no committed offset
    "isolation.level": "read_committed",
})
consumer.subscribe(["orders.v1"])
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            raise RuntimeError(msg.error())
        handle(msg)                      # idempotent business logic
        consumer.commit(message=msg, asynchronous=False)  # or batch: commit every N records
finally:
    consumer.close()                     # leaves the group and commits final offsets
```

- `auto.offset.reset` matters only when no committed offset exists or it is out of range. `latest` silently skips the backlog on a new group; `earliest` replays everything. Choose deliberately.
- Offsets expire from `__consumer_offsets` for groups inactive past the broker retention (`offsets.retention.minutes`); a long-idle group can lose its position.
- Reset offsets with `kafka-consumer-groups.sh --reset-offsets` only while the group is stopped; run with `--dry-run` first (see [kafka-operations.md](kafka-operations.md)).
- Commit per batch, not per record, with a synchronous commit on shutdown and an asynchronous commit in the loop.

## 7. Share groups (queues for Kafka)

Share groups (KIP-932) let several consumers read the same partitions cooperatively with per-record acknowledgement, which gives queue semantics on Kafka topics. Status: preview in 4.1, production-ready in 4.2 per the upgrade notes; 4.4 adds dead-letter topics for share groups (needs the `share.version` feature at level 2 and the `errors.deadletterqueue.topic.name` group config) and `kafka-share-groups.sh` can initialise offsets from a consumer group.

- Records are acquired with a lock (`group.share.record.lock.duration.ms`, 30 s by default); an unacknowledged record is released and redelivered, possibly to another consumer. Delivery is at-least-once with a delivery-count limit, after which the record is archived (or dead-lettered in 4.4).
- Acknowledge types: `ACCEPT`, `RELEASE`, `REJECT`; 4.2 adds `RENEW` in the Java API. Mode is chosen with `share.acknowledgement.mode` (`implicit` default, or `explicit`).
- There is no per-partition ordering guarantee and no exactly-once; use it for work queues where order does not matter and parallelism should exceed the partition count.
- Clusters with fewer than 3 brokers must set `share.coordinator.state.topic.replication.factor` and `share.coordinator.state.topic.min.isr` to 1 before first use (development setups).
- Java: `KafkaShareConsumer` (`subscribe`, `poll`, `acknowledge(record, AcknowledgeType)`, `commitSync`). Python: `confluent_kafka.ShareConsumer` exists in 2.16, but librdkafka 2.16.0 logs that the share consumer is in "Preview" and not recommended for production, so client maturity lags the broker.

```python
import os
from confluent_kafka import ShareConsumer, AcknowledgeType

with ShareConsumer({
    "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
    "group.id": "image-resize",
    "share.acknowledgement.mode": "explicit",
}) as sc:
    sc.subscribe(["jobs.v1"])
    while True:
        msg = sc.poll(1.0)
        if msg is None or msg.error():
            continue
        try:
            process(msg)
            sc.acknowledge(msg, AcknowledgeType.ACCEPT)
        except PermanentError:
            sc.acknowledge(msg, AcknowledgeType.REJECT)
        except Exception:
            sc.acknowledge(msg, AcknowledgeType.RELEASE)   # redeliver
        sc.commit_sync()
```

Share consumers are not thread-safe; use one instance per thread. Check the share-group docs for the auto offset reset group config and delivery limits before production use.

## 8. Client libraries

| Library | Version checked (2026-10) | Notes |
|---|---|---|
| Java `org.apache.kafka:kafka-clients` | 4.4.0 (Maven) | Reference client; clients need Java 11+, brokers Java 17+ as of 4.0 |
| confluent-kafka (Python) | 2.16.1 on PyPI | librdkafka bindings, includes Admin, Schema Registry, `ShareConsumer`, experimental asyncio classes in `confluent_kafka.aio` |
| librdkafka | 2.16.0 (bundled in the wheel) | C client behind Python, Go, .NET, Node (Confluent) clients |
| aiokafka | 0.15.0 | Pure-Python asyncio client; independent project |
| kafka-python | 3.0.12 | Pure-Python community client |
| KafkaJS (`kafkajs`) | 2.2.4, last published 2023-02-27 | No release for over three years; treat as unmaintained for new work |
| `@confluentinc/kafka-javascript` | 1.11.0 | librdkafka-based; includes a KafkaJS-compatible API (see its README) |
| `@platformatic/kafka` | 2.14.0 | Pure JavaScript, Node 22.22+ or 24.6+ per its engines field |

- Prefer a client built on librdkafka or the Java client for new services where a first-party feature (transactions, share groups) is needed; verify each pure-language client's support for the feature before depending on it.
- Pin client versions and test against the broker version in production; librdkafka lags the Java client on new KIPs.
- Python in an asyncio service: run the blocking confluent-kafka `poll()` in a thread, or evaluate `confluent_kafka.aio` / aiokafka, and keep one producer per process.
