---
name: kafka-messaging-expert
description: >-
  Designs, operates and debugs event streaming and messaging with Apache Kafka 4.x (KRaft, topics, partitions, producers, consumer groups, transactions, Schema Registry, share groups) and RabbitMQ 4.x (exchanges, quorum queues, streams, publisher confirms, dead-letter exchanges). Use when editing Kafka or AMQP client code, server.properties or compose files for apache/kafka or rabbitmq, running kafka-topics.sh or rabbitmqctl, or fixing consumer lag, rebalances and duplicate or lost messages. Not for service boundaries and sagas (use microservices-expert), Redis streams (use redis-expert), Node.js runtime topics (use nodejs-architect) or Kubernetes operators (use kubernetes-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Kafka and Messaging Expert

This skill covers message brokers for application developers and operators: Apache Kafka 4.x (KRaft-only clusters, producers and consumers, delivery guarantees, group protocols, retention and compaction, schemas, security, monitoring) and RabbitMQ 4.x (exchanges, queue types, reliable publishing and consuming, dead-lettering, streams). It also covers reliability patterns (outbox, idempotent consumers, retry and dead-letter topics) and the choice between the two brokers. Service decomposition, saga design, Redis streams, the Node.js runtime and Kubernetes operators belong to other skills.

> Verified against Apache Kafka 4.4.0 (release notes, upgrade notes and client sources of the 4.4 branch; Docker images apache/kafka:4.4.0), RabbitMQ 4.4.0 (release notes 4.0 to 4.4, Docker Hub tags), confluent-kafka 2.16.1 with librdkafka 2.16.0, pika 1.4.4, aio-pika 10.2.1, aiokafka 0.15.0, kafka-python 3.0.12, kafkajs 2.2.4, @confluentinc/kafka-javascript 1.11.0 and @platformatic/kafka 2.14.0 (2026-10).

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

- Covered: Kafka topics, partitions, keys, replication, `acks` and `min.insync.replicas`, idempotent producers, transactions and exactly-once limits, consumer groups (classic and KIP-848 protocols), offsets and commits, rebalancing, share groups (KIP-932), retention and compaction, Schema Registry with Avro and Protobuf, Kafka Connect and Kafka Streams in brief, KRaft operations, TLS, SASL and ACLs, monitoring and lag; RabbitMQ exchanges, quorum queues, classic queues, streams, confirms, acknowledgements, prefetch, dead-letter exchanges, AMQP 0-9-1 and AMQP 1.0, TLS and permissions; client libraries; Docker images for local development.
- Not covered: microservice boundaries, saga and choreography design (microservices-expert); Redis Streams and pub/sub (redis-expert); Node.js event loop and runtime topics (nodejs-architect); Kubernetes operators and Helm charts for brokers (kubernetes-expert); container image authoring (docker-expert); cloud-managed offerings in detail (aws-expert, azure-expert, gcp-expert); general observability stacks (observability-expert); SQL and database tuning for outbox tables (postgresql-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Kafka release line | 4.4.0 is the newest release seen (October 2026); 4.2.x and 4.3.x patch lines are also published. Kafka 4.0 removed ZooKeeper (KRaft only), removed old protocol API versions (clients must be 2.1+), requires Java 17 for brokers and Java 11 for clients. Check kafka.apache.org/downloads for the current line |
| Group protocols | KIP-848 (`group.protocol=consumer`) is generally available since 4.0 and runs broker-side incremental rebalancing. The Java consumer default is still `classic` in 4.4. Streams rebalance protocol (KIP-1071) is production-ready for its core feature set since 4.2 |
| Share groups (queues) | KIP-932: preview in 4.1, production-ready in 4.2. Cooperative consumption of partitions with per-record acknowledgement and delivery counts; 4.4 adds dead-letter topics for share groups. No ordering or exactly-once. Client support outside Java lags (confluent-kafka `ShareConsumer` logs a Preview warning) |
| Producer defaults (4.4 Java) | `acks=all`, `enable.idempotence=true`, `linger.ms=5` (was 0 before 4.0), `delivery.timeout.ms=120000`, `batch.size=16384` |
| Consumer defaults (4.4 Java) | `enable.auto.commit=true`, `auto.offset.reset=latest`, `isolation.level=read_uncommitted`, `session.timeout.ms=45000`, `max.poll.interval.ms=300000` |
| Durability recipe | `replication.factor=3`, `min.insync.replicas=2`, `acks=all`, `unclean.leader.election.enable=false`. Eligible leader replicas (KIP-966) are on by default for new clusters from 4.1 |
| Exactly-once | Atomic across Kafka topics and offsets only (transactions, `read_committed`, or Streams `exactly_once_v2`). External side effects need idempotency or an outbox |
| Retention | `delete` by time and size (7 days default), `compact` by key with tombstones, or both; empty `cleanup.policy` means infinite retention (4.2+) |
| Schemas | Registry subjects, compatibility modes `BACKWARD` (default) to `FULL_TRANSITIVE` and `NONE`; wire format is magic byte plus 4-byte schema id |
| Local images | `apache/kafka` (JVM) and `apache/kafka-native` (GraalVM; SASL in the native image from 4.4.0). `docker run -p 9092:9092 apache/kafka:4.4.0` starts a single node |
| RabbitMQ 4.x | AMQP 1.0 is a core protocol since 4.0; classic queue mirroring removed in 4.0; Khepri is the only metadata store from 4.3 (a majority of nodes must be up); quorum queues have a default delivery limit of 20; 4.4 adds delayed messages on quorum queues; Erlang 28 and 29 supported |
| RabbitMQ queue types | Quorum (replicated, default choice), classic (single node, non-replicated), stream (append-only log, port 5552 for the stream protocol). Transient non-exclusive queues and global QoS are denied by default from 4.3 |
| Client libraries | Java `kafka-clients` 4.4.0; Python `confluent-kafka` (librdkafka), `aiokafka`, `kafka-python`; Node: KafkaJS has had no release since February 2023, alternatives are `@confluentinc/kafka-javascript` and `@platformatic/kafka`; RabbitMQ Python `pika`, `aio-pika` |

## 3. Workflow

1. Identify the broker, version and deployment (managed service, self-hosted, Docker) from compose files, `server.properties`, client dependencies and CI config. Kafka 4.x behaviour differs from 3.x (no ZooKeeper, new defaults); RabbitMQ 4.3 and later differ from 3.13.
2. State the delivery requirement before designing: loss tolerance, duplicate tolerance, ordering scope (per key, per queue), latency, retention or replay need, throughput and consumer parallelism.
3. For a failure report, gather evidence first: `kafka-topics.sh --describe`, `kafka-consumer-groups.sh --describe`, broker logs, client logs with the error code, RabbitMQ `rabbitmq-diagnostics` and queue stats. Do not guess at config changes.
4. Pick the smallest design that meets the requirement: partitions and key, queue type and exchange, acknowledgement mode, retry and dead-letter route, schema and compatibility mode.
5. Write explicit client configuration for durability and error handling (see section 5); never rely on silent defaults for guarantees.
6. Add tests: an integration test against the same broker image as production (see section 11), including a duplicate-delivery case and a failure path.
7. Plan operations with the change: metrics, lag or queue-depth alerts, dead-letter monitoring, retention sizing, and a replay procedure.
8. When facts may have moved (versions, deprecations, KIP status), read the release or upgrade notes for the target version rather than relying on memory.

## 4. Decision Rules

- If the system needs a replayable event log, multiple independent consumers, high throughput or stream processing, use Kafka. If it needs task queues with per-message acknowledgement, flexible routing, TTL, priorities or request/reply at modest scale, use RabbitMQ. Details in [references/patterns-outbox-dlq.md](references/patterns-outbox-dlq.md).
- If a Kafka work queue needs per-record acknowledgement and consumers exceeding the partition count, evaluate share groups on 4.2 or later with a Java client; otherwise use consumer groups with retry topics.
- If ordering matters, key by the entity id and keep one partition per key; do not rely on global order across partitions. If the partition count must change, plan a new topic and migration.
- If data must not be lost, require `acks=all`, replication factor 3, `min.insync.replicas=2`, `unclean.leader.election.enable=false` and publisher-side error handling.
- If duplicates are unacceptable, make the consumer idempotent; use Kafka transactions only for Kafka-to-Kafka pipelines. "Exactly-once" end to end into a database or API is idempotency, not a broker setting.
- If a service must update its database and emit an event, use the transactional outbox, not two independent writes.
- If a consumer is slow or long-running per record, lower `max.poll.records`, move work to a bounded pool with `pause`/`resume`, or use a share group; do not raise `max.poll.interval.ms` indefinitely.
- If you start a new consumer group on an existing topic, choose `auto.offset.reset` consciously (`earliest` replays all, `latest` skips the backlog).
- If a RabbitMQ queue must survive node loss, use a quorum queue (3 or 5 nodes); use a classic queue only for transient, exclusive or non-critical work; use a stream for replay and fan-out.
- If a Node.js service needs Kafka and KafkaJS is proposed, check the maintenance state first and consider `@confluentinc/kafka-javascript` or `@platformatic/kafka`.
- If schemas are shared across teams, use a registry with `BACKWARD` or `FULL` (transitive when old data is kept) and register from CI, not at runtime.
- If a message can never succeed (bad schema, validation), send it to a dead-letter destination immediately; retry only transient failures, with backoff and a cap.
- If you are tempted to put large payloads (megabytes) in messages, store the blob elsewhere and send a reference.

## 5. Coding Standards

- Set durability and delivery options explicitly in code or config: `acks`, `enable.idempotence`, `delivery.timeout.ms`, `enable.auto.commit`, `auto.offset.reset`, `isolation.level`, prefetch, confirms.
- Always handle producer results: delivery callbacks or futures (Kafka), publisher confirms and `mandatory` returns (RabbitMQ). Flush or close producers on shutdown.
- Poll loops: call `poll` frequently, keep per-batch work bounded, commit after processing, and close the consumer in a `finally` or try-with-resources so it leaves the group.
- Treat messages as untrusted input: validate against a schema, catch deserialisation errors per record, and never `eval`, unpickle or deserialise polymorphic Java objects from message bytes.
- Use a stable, documented topic and queue naming scheme (`domain.entity.event.v1`); create topics and queues from code or infrastructure files, not on first publish.
- Use one client instance per process for producers (they are thread-safe in Java and librdkafka); consumers are not thread-safe, so use one per thread. Pika's blocking connection is not thread-safe.
- Put event metadata in headers (event id, type, correlation id, schema version); keep the payload to business data.
- Configuration comes from the environment or a secret manager; credentials, keystore passwords and registry keys never appear in code, images or compose files in the repository.
- Log topic, partition, offset (Kafka) or delivery tag and message id (RabbitMQ) with every error; do not log whole payloads containing personal data.
- Name consumer groups per service and purpose with a version suffix (`billing-v1`), and treat the group id as part of the deployment contract.

## 6. Project Structure

```text
orders-service/
|-- pyproject.toml / pom.xml     # client dependencies pinned
|-- schemas/
|   |-- order_placed.avsc        # versioned schema files, registered from CI
|   `-- README.md                # compatibility mode per subject
|-- src/
|   |-- messaging/
|   |   |-- producer.py          # one place that configures durability and callbacks
|   |   |-- consumer.py          # poll loop, commit policy, shutdown handling
|   |   |-- dlt.py               # dead-letter publishing and replay helpers
|   |   `-- topology.py          # topics / exchanges / queues declared idempotently
|   |-- handlers/                # idempotent business handlers, broker-agnostic
|   `-- outbox/                  # outbox writer and relay worker
|-- infra/
|   |-- compose.yaml             # apache/kafka and rabbitmq images, pinned tags, loopback ports
|   `-- topics.yaml              # topic names, partitions, configs (reviewed like code)
`-- tests/
    |-- integration/             # real broker via containers
    `-- unit/                    # handlers with fake messages
```

- Keep broker details in `messaging/` and business logic in broker-agnostic handlers so handlers are testable without a broker.
- Keep schema files and topic definitions in version control and review changes like API changes.

## 7. Design Patterns

- **Transactional outbox**: write the event row in the same database transaction as the state change; relay by polling (`FOR UPDATE SKIP LOCKED`) or change data capture. At-least-once, so pair with idempotent consumers. See [references/patterns-outbox-dlq.md](references/patterns-outbox-dlq.md).
- **Idempotent consumer / inbox**: a `(consumer, event_id)` primary key inserted in the same transaction as the effect; duplicates are skipped.
- **Retry topics plus dead-letter topic**: tiered delay topics for transient failures, a DLT for permanent ones, with original coordinates and error class in headers. RabbitMQ equivalent: wait queue with TTL and a dead-letter exchange.
- **Consume-transform-produce transaction**: Kafka transactions with `sendOffsetsToTransaction` and `read_committed` consumers for Kafka-to-Kafka steps. Cost: latency and transaction overhead.
- **Compacted topic as table**: key by entity, tombstones for deletes, consumers rebuild state at start. Not an event history.
- **Competing consumers**: many workers on one queue (RabbitMQ) or one group (Kafka, up to the partition count) or one share group.
- **Pub/sub fan-out**: one exchange with a queue per subscriber (RabbitMQ), or one topic with a consumer group per subscriber (Kafka).
- **Request/reply**: RabbitMQ Direct Reply-To (also available for AMQP 1.0 since 4.2) or a reply topic with correlation ids; avoid it on Kafka unless necessary.
- **Event-carried state transfer**: events include the data consumers need, so they keep local read models; cost is payload coupling and schema discipline.
- **Schema registry with compatibility gates**: CI checks compatibility before a producer is deployed.

## 8. Best Practices

- Decide and document per topic: key, partition count, retention or compaction, replication, owner, schema subject and compatibility mode.
- Prefer `acks=all` with idempotence over application-level retry loops; tune `delivery.timeout.ms` instead of retrying forever.
- Commit offsets after the side effect is durable; commit per batch with a synchronous commit on shutdown.
- Use cooperative or KIP-848 rebalancing and static membership (`group.instance.id`) for stateful or slow-starting consumers.
- Keep consumers fast and bounded; scale by adding partitions up front, consumers (up to partition count) or share groups, not by long processing inside `poll`.
- Alert on consumer lag trend, under-replicated and under-min-ISR partitions, dead-letter growth, queue depth and age, connection and channel counts.
- Use separate listeners or networks for clients and inter-broker traffic; bind development brokers to loopback.
- Pin broker and client versions; read upgrade notes for each release between current and target, especially across a major version.
- Keep retention longer than the worst-case consumer outage plus replay window; verify disk sizing with real compression ratios.
- Give every dead-letter destination an owner, an alert and a documented replay procedure.
- Prefer a managed service or an operator-run cluster for production unless the team can staff on-call for brokers.

## 9. Performance

- Producer throughput comes from batching and compression: raise `linger.ms` (5 ms default in 4.x) and `batch.size`, use `lz4` or `zstd`, and avoid one `flush()` per record.
- Partition count bounds consumer parallelism and per-key ordering; more partitions cost memory, file handles, controller work and failover time. Size for target throughput with headroom, and measure.
- Consumer throughput: raise `max.poll.records` and `fetch.min.bytes` carefully, process batches, commit per batch, and avoid synchronous per-record external calls (use bounded concurrency).
- Skew: a hot key creates a hot partition. Check per-partition bytes; change the key or add a salt only if ordering allows.
- Large messages hurt: check `message.max.bytes` / `max.message.bytes`, `max.request.size` and `max.partition.fetch.bytes`, and prefer references to blobs.
- RabbitMQ: use publisher confirms in batches or asynchronously, bounded prefetch, short queues, quorum queues for safety (expect lower throughput than classic), and streams for very high fan-out.
- Many short-lived connections or channels harm RabbitMQ; keep long-lived connections and few channels.
- Always benchmark with the real message size, compression and replication settings (`kafka-producer-perf-test.sh`, RabbitMQ PerfTest) before tuning by folklore.

## 10. Security

- Kafka: use `SASL_SSL` (SCRAM-SHA-512 or OAUTHBEARER) or mutual TLS on every non-development listener, an authorizer (`StandardAuthorizer` in KRaft) with `allow.everyone.if.no.acl.found=false`, least-privilege ACLs per principal, topic and group, and a secured controller listener. See [references/kafka-operations.md](references/kafka-operations.md).
- RabbitMQ: TLS on 5671, per-application users with configure/write/read regexes per vhost, no remote `guest`, management UI behind TLS and a restricted network, a secret Erlang cookie. See [references/rabbitmq.md](references/rabbitmq.md).
- Never disable certificate or host name verification to fix a TLS error; fix the certificate chain or `advertised.listeners` name.
- Credentials come from a secret store or environment variables injected at runtime. Do not put passwords in `docker-compose.yaml` committed to the repository, in client code or in `kafka-configs.sh` command lines on shared hosts.
- Encrypt sensitive fields at the application level when the data should not be readable by broker operators; brokers store payloads in clear text at rest unless disks are encrypted.
- Do not deserialise untrusted bytes into arbitrary object graphs (Java serialisation, pickle). Use Avro, Protobuf or JSON with schemas.
- Restrict who can create topics, change ACLs and read the dead-letter topics; they often contain the data that failed validation.
- Do not expose broker, controller, management or Erlang distribution ports to the internet. In 4.4, brokers refuse an OAUTHBEARER JWKS configuration without expected audience and issuer; keep it that way.
- Keep client libraries patched; the Kafka 4.3.2 release notes list dependency CVE bumps, which shows why running a current patch release matters.

## 11. Testing

- Unit-test handlers with fake message objects; keep broker I/O out of them.
- Integration-test against the production broker image with Testcontainers or a compose stack (`apache/kafka:4.4.0`, `rabbitmq:4.4-management`), using unique topic or queue names and a unique consumer group per test run.
- Test the failure paths: broker unavailable at publish, deserialisation failure, handler exception, duplicate delivery (send the same event twice), consumer restart mid-batch, rebalance, and dead-letter routing.
- Assert on outcomes with bounded polling and timeouts; never `sleep` for a fixed time. Clean up topics and queues.
- Contract-test schemas: check new schema versions against the registry compatibility endpoint in CI, and keep sample payloads for every event version.
- Run a load test of a representative workload before launch (consumer lag stays bounded at peak). See load-testing-expert.
- Chaos-test in staging: kill a broker, partition the network, pause a consumer, and confirm lag recovers and no acknowledged message is lost.
- General test strategy lives in integration-testing-expert and unit-testing-expert.

## 12. Review Checklist

- [ ] Delivery requirement (loss, duplicates, ordering) is written down and the config matches it.
- [ ] Producers: `acks=all`, idempotence on, delivery results handled, flush on shutdown. RabbitMQ: confirms, persistent messages, durable quorum queues, `mandatory` or alternate exchange.
- [ ] Topic or queue created explicitly with replication factor 3, `min.insync.replicas=2` (Kafka) or 3 to 5 quorum members (RabbitMQ).
- [ ] Key chosen for the ordering requirement; partition count justified.
- [ ] Consumers commit or ack after processing, handlers are idempotent, `max.poll.interval.ms` is respected, shutdown closes the consumer.
- [ ] `auto.offset.reset` is a deliberate choice; `isolation.level=read_committed` where transactional producers exist.
- [ ] Retries are bounded with backoff; permanent failures go to a dead-letter destination with an alert and a replay path.
- [ ] Events have a schema, a compatibility mode and an id; schemas are registered from CI.
- [ ] Database change and event emission use an outbox, not dual writes.
- [ ] TLS, authentication, authorization and least-privilege ACLs or permissions are in place; no secrets in the repository.
- [ ] Metrics and alerts exist: lag, under-replicated partitions, queue depth and age, dead-letter size.
- [ ] Docker and client versions are pinned; versions match the broker's supported range.

## 13. Production Notes

- Run 3 dedicated KRaft controllers (or a combined 3-node setup for small clusters) and at least 3 brokers across zones. Never run production with replication factor 1.
- Finish upgrades with `kafka-features.sh upgrade --release-version <X.Y>` after verifying the rolling restart; know whether the target metadata version allows a downgrade. Review the 4.4 notes before upgrading: for example storage directories formatted by the 4.4 tool need a broker of the same or newer version.
- Kafka 4.0 removed old protocol versions, log4j (now log4j2), Scala 2.12 and the classic MirrorMaker 1; migrate configs and tooling before upgrading.
- `auto.create.topics.enable=false` in production; manage topics as code.
- Monitor disk, network, request latency, under-replicated partitions and consumer lag; practise broker replacement and partition reassignment with throttling.
- Plan RabbitMQ upgrades one minor line at a time (4.3 upgrades in place only from 4.2.x), enable feature flags between steps, and keep a majority of nodes up (Khepri and Raft).
- Handle memory and disk alarms in RabbitMQ before they block publishers; keep queues short and monitor oldest message age.
- Keep a documented runbook: replay from the dead-letter topic, reset consumer offsets (`--dry-run` first, group stopped), recover a broker, rotate credentials and certificates.
- Check KRaft metadata and quorum health with `kafka-metadata-quorum.sh describe --status` during incidents.
- Multi-region replication uses MirrorMaker 2 (Connect-based) or managed equivalents; define failover and offset translation before you need them.

## 14. Examples

Durable topic and explicit Java producer settings (Kafka 4.x):

```bash
kafka-topics.sh --bootstrap-server broker:9092 --create --topic orders.v1 \
  --partitions 12 --replication-factor 3 --config min.insync.replicas=2
```

```java
Properties p = new Properties();
p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, System.getenv("KAFKA_BOOTSTRAP"));
p.put(ProducerConfig.ACKS_CONFIG, "all");
p.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
p.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, "120000");
p.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "lz4");
p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

try (KafkaProducer<String, String> producer = new KafkaProducer<>(p)) {
    producer.send(new ProducerRecord<>("orders.v1", "order-42", "{\"id\":42}"),
        (metadata, ex) -> {
            if (ex != null) {
                log.error("publish failed for key order-42", ex);   // alert or fall back
            }
        });
    producer.flush();
}
```

At-least-once consumer with manual commit and the KIP-848 group protocol:

```java
Properties p = new Properties();
p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, System.getenv("KAFKA_BOOTSTRAP"));
p.put(ConsumerConfig.GROUP_ID_CONFIG, "billing-v1");
p.put(ConsumerConfig.GROUP_PROTOCOL_CONFIG, "consumer");     // default is "classic" in 4.4
p.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
p.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
p.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
p.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
p.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());

try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(p)) {
    consumer.subscribe(List.of("orders.v1"));
    while (running) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));
        for (ConsumerRecord<String, String> r : records) {
            handleIdempotently(r);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();         // after the whole batch is durable
        }
    }
}
```

With the `consumer` protocol, classic-only settings such as `partition.assignment.strategy` do not apply, and session timing is a broker-side group setting; check the client docs before migrating configs.

Inspect lag and group state:

```bash
kafka-consumer-groups.sh --bootstrap-server broker:9092 --describe --group billing-v1
```

RabbitMQ quorum queue with a dead-letter exchange, publishing with confirms, and manual acknowledgements are shown in full in [references/rabbitmq.md](references/rabbitmq.md). Outbox SQL, idempotent consumer, dead-letter publishing and a Schema Registry producer are in [references/patterns-outbox-dlq.md](references/patterns-outbox-dlq.md). Transactions, commit strategies and share groups are in [references/kafka-producers-consumers.md](references/kafka-producers-consumers.md).

## 15. Common Mistakes

- **Treating `enable.auto.commit=true` as safe**: offsets are committed on a timer from the previous poll, so a crash can skip records. Commit manually after processing.
- **Assuming "exactly-once" covers the database or HTTP call**: it covers Kafka reads and writes only. Make external effects idempotent or use an outbox.
- **Dual write (DB then publish)**: a crash between the two loses the event. Use the transactional outbox.
- **Wrong `advertised.listeners`**: clients connect to bootstrap, then fail on the returned address. Advertise a name reachable by clients; use separate listeners for containers and host.
- **Increasing partitions on a keyed topic without a plan**: keys remap and per-key order breaks across the change. Create a new topic and migrate.
- **Mixed Java and librdkafka producers with different default partitioners**: the same key lands in different partitions. Set `partitioner=murmur2_random` on librdkafka clients.
- **Consumer blocked longer than `max.poll.interval.ms`**: the member is removed and the group rebalances, causing duplicates. Bound batch work, pause partitions or use a worker pool.
- **`auto.offset.reset=latest` on a new group**: the backlog is skipped silently. Use `earliest` when the history matters.
- **`min.insync.replicas=1` with replication factor 3 and `acks=all`**: gives no protection against losing the only in-sync copy. Use 2.
- **Enabling `unclean.leader.election.enable` for availability**: allows silent data loss. Keep it `false` for important data.
- **Using a compacted topic for events with null keys**, or expecting compaction to be immediate: compaction needs keys and skips the active segment.
- **Unbounded retry loops or requeue storms**: a poison message blocks a partition or spins a RabbitMQ consumer. Cap retries and dead-letter.
- **Ignoring publisher confirms and `mandatory` in RabbitMQ**: unroutable or unconfirmed messages vanish silently.
- **`auto_ack=True` for important work**: messages are lost on consumer crash. Use manual acknowledgement with a bounded prefetch.
- **Default (unbounded) prefetch**: one consumer hoards messages while others idle. Set `basic_qos`.
- **Using classic queues for critical data on 4.x**: classic queues are not replicated since 4.0. Use quorum queues.
- **Using `latest` image tags**: a pull changes the broker version. Pin `apache/kafka:4.4.0` and `rabbitmq:4.4-management` style tags.
- **Starting a new project on KafkaJS without checking maintenance**: the last npm release is from February 2023. Evaluate maintained alternatives.
- **Registering schemas from every application instance in production**: races and surprise versions. Register from CI and disable auto-registration.
- **Leaving dead-letter topics unmonitored**: failures accumulate unseen. Alert on size and age and keep a replay tool.

## 16. References

- [references/kafka-producers-consumers.md](references/kafka-producers-consumers.md): producer durability and batching settings, keys and ordering, idempotence, transactions, exactly-once limits, classic vs KIP-848 consumer groups, offset commit strategies, share groups, client library status.
- [references/kafka-operations.md](references/kafka-operations.md): KRaft basics, Docker setups with apache/kafka, replication and min ISR, retention and compaction, TLS and SASL and ACLs, CLI tools, upgrades, monitoring and lag, sizing.
- [references/rabbitmq.md](references/rabbitmq.md): RabbitMQ 4.x changes, exchanges and queue types, confirms, acknowledgements and prefetch, dead-letter exchanges, streams, protocols and clients, security, operations, local Docker.
- [references/patterns-outbox-dlq.md](references/patterns-outbox-dlq.md): transactional outbox, idempotent consumers, retry and dead-letter topics, Schema Registry and compatibility, Connect and Streams in brief, Kafka vs RabbitMQ.
- Apache Kafka documentation: https://kafka.apache.org/documentation/ ; downloads and release notes: https://kafka.apache.org/downloads
- Kafka improvement proposals: https://cwiki.apache.org/confluence/display/KAFKA/Kafka+Improvement+Proposals (KIP-848, KIP-932, KIP-890, KIP-966, KIP-1071)
- Kafka Docker images: https://hub.docker.com/r/apache/kafka and https://hub.docker.com/r/apache/kafka-native
- RabbitMQ documentation: https://www.rabbitmq.com/docs ; release notes: https://github.com/rabbitmq/rabbitmq-server/tree/main/release-notes
- confluent-kafka-python: https://github.com/confluentinc/confluent-kafka-python ; librdkafka configuration: https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md
- Debezium outbox event router: https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html
