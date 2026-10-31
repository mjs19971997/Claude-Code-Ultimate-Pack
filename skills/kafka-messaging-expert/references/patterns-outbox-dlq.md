# Messaging Patterns: Outbox, Idempotent Consumers, Retries, Dead Letters, Schemas

Patterns that make event-driven systems reliable on Kafka and RabbitMQ: the transactional outbox, idempotent consumers, retry and dead-letter topologies, schema management with a registry, and a short note on Kafka Connect and Kafka Streams. Library names and signatures were checked against confluent-kafka 2.16.1; Debezium field names are not verified here, so check the Debezium outbox documentation (3.7.0.Final was the newest release on Maven Central at the time of checking, 2026-10). Saga design and service boundaries belong to microservices-expert.

## Contents

1. [Dual writes and the transactional outbox](#1-dual-writes-and-the-transactional-outbox)
2. [Idempotent consumers](#2-idempotent-consumers)
3. [Retries and dead-letter topics on Kafka](#3-retries-and-dead-letter-topics-on-kafka)
4. [Poison messages and replay](#4-poison-messages-and-replay)
5. [Schema management](#5-schema-management)
6. [Event design](#6-event-design)
7. [Kafka Connect and Kafka Streams](#7-kafka-connect-and-kafka-streams)
8. [Choosing Kafka or RabbitMQ](#8-choosing-kafka-or-rabbitmq)

## 1. Dual writes and the transactional outbox

Updating a database and publishing a message in two steps loses one of them when the process fails between the steps. The outbox pattern writes the event to an `outbox` table in the same database transaction as the state change, and a separate relay publishes rows to the broker.

```sql
CREATE TABLE outbox (
    id             uuid        PRIMARY KEY,
    aggregate_type text        NOT NULL,
    aggregate_id   text        NOT NULL,
    event_type     text        NOT NULL,
    payload        jsonb       NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    published_at   timestamptz
);
CREATE INDEX outbox_unpublished ON outbox (created_at) WHERE published_at IS NULL;
```

```python
def place_order(conn, order):          # psycopg 3 connection; Jsonb is psycopg.types.json.Jsonb
    with conn.transaction():                       # one transaction
        conn.execute("INSERT INTO orders (id, total) VALUES (%s, %s)", (order.id, order.total))
        conn.execute(
            "INSERT INTO outbox (id, aggregate_type, aggregate_id, event_type, payload)"
            " VALUES (%s, 'order', %s, 'OrderPlaced', %s)",
            (new_event_id(), order.id, Jsonb(order.to_event())),
        )
```

Two relay options:

- Polling publisher: a worker selects unpublished rows in batches with `FOR UPDATE SKIP LOCKED`, produces them with idempotence enabled, waits for delivery reports, then marks them published. Simple, adds a little latency and database load; use the index above and delete or archive old rows.
- Change data capture: Debezium reads the database log and its outbox event router transformation (`io.debezium.transforms.outbox.EventRouter`) turns outbox rows into messages routed by aggregate type, with the aggregate id as key. It runs on Kafka Connect. Field-mapping options and defaults differ by version; read the outbox page of the Debezium documentation for the one you deploy.

Guarantees and limits:

- Delivery from the outbox is at-least-once: a crash after publish and before marking leads to a duplicate, so consumers must be idempotent (section 2). Put a stable `event_id` in a message header or payload.
- Per-aggregate ordering holds if the relay publishes an aggregate's events in order with the aggregate id as the key. Polling with several workers needs partitioning of rows by aggregate to keep that.
- The outbox table is part of the service schema; monitor its size and the oldest unpublished row as a health metric.
- The mirror pattern for the inbound side is the inbox table (section 2).

## 2. Idempotent consumers

Brokers deliver at-least-once in practice (rebalances, redeliveries, outbox duplicates, retries). Make handlers safe to run twice.

```sql
CREATE TABLE processed_events (
    consumer   text        NOT NULL,
    event_id   uuid        NOT NULL,
    handled_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer, event_id)
);
```

```python
def handle(conn, event):
    with conn.transaction():
        inserted = conn.execute(
            "INSERT INTO processed_events (consumer, event_id) VALUES (%s, %s)"
            " ON CONFLICT DO NOTHING",
            ("billing", event.id),
        ).rowcount
        if inserted == 0:
            return                                   # duplicate, skip side effects
        apply_business_change(conn, event)           # same transaction as the marker
```

Commit the broker offset or acknowledge only after the transaction commits. Alternatives: natural idempotency (upsert by key, set-state not increment), version numbers (ignore events older than the stored version), and idempotency keys for outbound HTTP calls. Expire dedupe rows after a window longer than the maximum redelivery delay.

## 3. Retries and dead-letter topics on Kafka

Kafka has no per-message acknowledgement or built-in dead-letter handling for classic consumer groups, so the application builds them. A blocked partition cannot skip a bad record without a decision.

Classify failures first:

| Failure | Action |
|---|---|
| Transient (timeout, 503, lock conflict) | Retry in place a few times with backoff and jitter |
| Still failing after in-place retries | Publish to a retry topic with a delay, or pause the partition |
| Permanent (schema violation, validation, unknown type) | Publish to the dead-letter topic (DLT) immediately |
| Poison pill that cannot be deserialised | Catch the deserialisation error, send raw bytes to the DLT, continue |

Retry-topic design (non-blocking): `orders.v1` -> `orders.v1.retry-1m` -> `orders.v1.retry-10m` -> `orders.v1.dlt`. A retry consumer reads its topic, waits until the record's due time (a header), pauses the partition rather than sleeping past `max.poll.interval.ms`, and re-processes. This keeps the main topic flowing at the cost of ordering for the failed key.

```python
import json
from confluent_kafka import Producer

def send_to_dlt(producer: Producer, msg, error: Exception, attempts: int) -> None:
    headers = [
        ("dlt.original.topic", msg.topic().encode()),
        ("dlt.original.partition", str(msg.partition()).encode()),
        ("dlt.original.offset", str(msg.offset()).encode()),
        ("dlt.error.class", type(error).__name__.encode()),
        ("dlt.error.message", str(error)[:500].encode()),
        ("dlt.attempts", str(attempts).encode()),
    ]
    producer.produce(msg.topic() + ".dlt", key=msg.key(), value=msg.value(), headers=headers)
    producer.flush(10)   # wait before committing the source offset
```

- Commit the source offset only after the DLT write is confirmed, or the record is lost.
- Keep the original key, value bytes and headers so the record can be replayed unchanged; do not log full payloads that hold personal data.
- Give the DLT the same partition count or key so per-key order is preserved on replay, and a longer retention than the main topic.
- Spring Kafka offers `DefaultErrorHandler`, `DeadLetterPublishingRecoverer` and `@RetryableTopic` for this; Kafka Connect sink connectors have `errors.tolerance`, `errors.deadletterqueue.topic.name` and `errors.deadletterqueue.context.headers.enable`. See java-spring-expert for the Spring side.
- Share groups (Kafka 4.2 production-ready) acknowledge per record with a delivery count; 4.4 adds a dead-letter topic for released-over-limit and rejected records, enabled with the `share.version` feature at level 2 and the group config `errors.deadletterqueue.topic.name`. Use them when a work-queue model fits better than building retry topics.
- For RabbitMQ the same ideas use dead-letter exchanges, delivery limits and a TTL wait queue; see [rabbitmq.md](rabbitmq.md).

## 4. Poison messages and replay

- Alert on DLT growth rate and age of the oldest record; an unwatched DLT is a silent data-loss mechanism.
- Provide a replay tool: read the DLT, optionally fix or filter, and republish to the original topic (or a retry topic) with a replay counter header so loops are bounded.
- Replay needs idempotent consumers; a record can be replayed after a partial earlier success.
- After fixing a bug, replaying from the main topic by resetting the consumer group offsets (`kafka-consumer-groups.sh --reset-offsets`, group stopped) is an alternative to the DLT when retention still holds the data.
- Never use the DLT as a general error log; keep structured logs and metrics for diagnosis.

## 5. Schema management

Raw JSON without a contract breaks consumers silently. A schema registry stores versioned schemas and enforces compatibility on registration. Confluent Schema Registry (a service with a REST API; Avro, Protobuf and JSON Schema) is the common choice; Apicurio Registry is another. Check licensing of the image you pick.

- Wire format with the Confluent serialisers: a magic byte, a 4-byte schema id, then the payload. Consumers need the registry reachable (they cache ids).
- Subject naming: `TopicNameStrategy` (default, subject `<topic>-value` and `<topic>-key`), `RecordNameStrategy`, `TopicRecordNameStrategy` (several event types per topic). The Python package exposes `topic_subject_name_strategy`, `record_subject_name_strategy` and `topic_record_subject_name_strategy`.
- Compatibility modes: `BACKWARD` (the registry default: new schema reads data written with the previous one), `BACKWARD_TRANSITIVE`, `FORWARD`, `FORWARD_TRANSITIVE`, `FULL`, `FULL_TRANSITIVE`, `NONE`. Pick per subject.
  - BACKWARD: upgrade consumers first. Allowed: add a field with a default, remove a field.
  - FORWARD: upgrade producers first. Allowed: add a field, remove a field that had a default.
  - FULL: both; allowed changes are adding or removing fields that have defaults.
  - Use the `_TRANSITIVE` variants when old data stays in the topic and must remain readable by every schema version.
- Safe evolution (Avro): add optional fields with defaults, never reuse a field name with another meaning, never change a type incompatibly, never rename without aliases. Protobuf: never reuse or renumber field numbers; reserve removed numbers and names.
- Register schemas from CI (not from application start in production): set `auto.register.schemas=False` and `use.latest.version=True` on the serialiser, and check compatibility in the pipeline against the registry.

```python
import os
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

sr = SchemaRegistryClient({"url": os.environ["SCHEMA_REGISTRY_URL"]})
schema_str = """
{"type": "record", "name": "OrderPlaced", "namespace": "shop.orders",
 "fields": [{"name": "id", "type": "string"},
            {"name": "total_cents", "type": "long"},
            {"name": "coupon", "type": ["null", "string"], "default": null}]}
"""
value_ser = AvroSerializer(
    sr, schema_str, to_dict=lambda obj, ctx: obj,
    conf={"auto.register.schemas": False, "use.latest.version": True},
)
producer = SerializingProducer({
    "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
    "key.serializer": StringSerializer("utf_8"),
    "value.serializer": value_ser,
})
producer.produce("orders.v1", key="42", value={"id": "42", "total_cents": 1999, "coupon": None})
producer.flush()
```

- Registry authentication goes in the client config (`basic.auth.user.info` or bearer settings) from a secret store; check the client docs for the exact keys of your version.
- Keep the schema in the repository next to the producer; consumers should depend on a published artifact or the registry, not copy files.

## 6. Event design

- Name events in the past tense by business fact (`OrderPlaced`), not by CRUD operation. Carry an `event_id`, `event_type`, `occurred_at` (UTC), a schema or version marker, and a correlation id.
- Decide between thin events (id only; consumers call back) and fat events (state needed by consumers). Fat events avoid chatty callbacks but couple consumers to the payload; do not include secrets or unneeded personal data.
- Use the entity id as the key; use compacted topics for "current state" streams and delete-policy topics for history.
- Version breaking changes with a new topic (`orders.v2`) and a migration period, not an in-place incompatible change.
- Large payloads belong in object storage with a reference in the event.

## 7. Kafka Connect and Kafka Streams

- Kafka Connect runs source and sink connectors (JDBC, Debezium CDC, S3, search and many more) as a scalable service configured through a REST API. Distributed mode stores offsets, configs and status in internal topics (4.4 can disable automatic creation of them with `internal.topics.automatic.creation.enable=false` and ships `connect-internal-topics.sh`). Secure the REST API, keep credentials in config providers and set a dead-letter policy per sink. Exactly-once source support exists for some connectors; check the connector docs.
- Kafka Streams is a Java library (no cluster) for stateful stream processing with local RocksDB state and changelog topics. Use `processing.guarantee=exactly_once_v2` for exactly-once inside Kafka. The Streams rebalance protocol (KIP-1071, `group.protocol=streams`) is production-ready for its core feature set from 4.2 and gains static membership and custom broker-side assignors in 4.4; opt in deliberately and read the Streams upgrade guide. The Scala wrapper `kafka-streams-scala` is deprecated from 4.3.
- For stream processing outside the JVM, evaluate Flink or a consumer-based service; Python's Faust-style libraries are community projects, so check maintenance before relying on them.
- Streams state and changelogs make topic naming and partition counts part of the application's contract; changing the topology needs an upgrade plan.

## 8. Choosing Kafka or RabbitMQ

| Need | Kafka | RabbitMQ |
|---|---|---|
| Durable event log, replay, many independent consumer groups | Strong fit (retention, offsets) | Streams provide a log; classic and quorum queues delete on ack |
| Work queue with per-message ack, retries, priorities, TTL | Possible with share groups (4.2+) or app-built retry topics | Strong fit (queues, DLX, delivery limit, priorities on quorum queues) |
| Flexible routing (topic/headers exchanges), request/reply | Not built in | Strong fit (exchanges, Direct Reply-To) |
| Very high throughput, large partitioned pipelines | Strong fit | Streams scale well; queues are lower throughput per queue |
| Ordering | Per partition, by key | Per queue with one consumer (or single active consumer) |
| Stream processing, CDC, connector ecosystem | Kafka Streams, Connect, Flink | Limited; use external tools |
| Operational model | KRaft cluster, partitions, disk and retention planning | Cluster of 3 or 5 nodes, queue types, memory and disk alarms |
| Protocols | Kafka protocol | AMQP 0-9-1, AMQP 1.0, MQTT, STOMP, streams |

- Default to Kafka for event streaming and data integration across teams; default to RabbitMQ for task queues, command messaging and rich routing in a modest-scale system.
- Many systems use both: RabbitMQ for commands between services, Kafka for the event backbone. Avoid bridging them without a clear owner and a duplicate-safe design.
- If the team already operates one of them well and the workload fits, that usually outweighs marginal feature differences. Managed offerings change the operational trade-off; compare on current pricing and limits.
