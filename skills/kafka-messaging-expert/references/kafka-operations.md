# Kafka Operations: KRaft, Replication, Retention, Security, Monitoring

Running Apache Kafka 4.x: KRaft clusters, local development with the official Docker images, topic and replication settings, retention and compaction, TLS and SASL and ACLs, upgrades, monitoring and lag. Facts come from the Kafka 4.0 to 4.4 upgrade notes, the 4.4 Docker documentation and example compose files, and the 4.4 client sources (2026-10). Broker setting names not mentioned there are standard Kafka names; check the current docs before copying values into production.

## Contents

1. [KRaft cluster basics](#1-kraft-cluster-basics)
2. [Local development with Docker](#2-local-development-with-docker)
3. [Topics, replication and durability](#3-topics-replication-and-durability)
4. [Retention and compaction](#4-retention-and-compaction)
5. [Security: TLS, SASL and ACLs](#5-security-tls-sasl-and-acls)
6. [Command line tools](#6-command-line-tools)
7. [Upgrades](#7-upgrades)
8. [Monitoring and consumer lag](#8-monitoring-and-consumer-lag)
9. [Sizing and tuning](#9-sizing-and-tuning)

## 1. KRaft cluster basics

- ZooKeeper mode was removed in Kafka 4.0; every 4.x cluster runs KRaft. A ZooKeeper cluster must be migrated to KRaft on 3.9.x before upgrading to 4.x, and the cluster must already be on 3.3 or newer.
- A node has `process.roles` of `broker`, `controller` or both. Production clusters usually run 3 dedicated controller nodes (an odd number, a majority must stay up) plus separate brokers; combined mode suits development and small clusters.
- Key settings: `node.id` (4.4 deprecates `broker.id` in favour of it), `process.roles`, `controller.quorum.voters` (static) or `controller.quorum.bootstrap.servers` (dynamic quorum, KIP-853), `controller.listener.names`, `listeners`, `advertised.listeners`, `inter.broker.listener.name`, `listener.security.protocol.map`, `log.dirs`.
- Format storage once per node before first start with `kafka-storage.sh` (a cluster id from `kafka-storage.sh random-uuid`). Since 4.4 a broker must be the same version as, or newer than, the `kafka-storage` tool that formatted its directory.
- `advertised.listeners` is the most common client connection failure: the address returned in metadata must be reachable from the client, not just from the broker. Use separate listeners for in-cluster and external clients.
- Eligible Leader Replicas (KIP-966 part 1, 4.0) let the controller track out-of-sync replicas that are still safe to elect, reducing the need for unclean elections. With ELR enabled by default on new 4.1 clusters, set `min.insync.replicas` at the cluster level rather than as a broker config (per the 4.1 notes).
- Dynamic quorum changes: `kafka-metadata-quorum.sh describe --status` shows the leader and voters; 4.4 adds unregistering controllers (`kafka-cluster.sh unregister-controller`).

## 2. Local development with Docker

Official images on Docker Hub: `apache/kafka` (JVM, available from 3.7.0) and `apache/kafka-native` (GraalVM native, from 3.8.0; SASL support in the native image arrived in 4.4.0). Pin a version tag rather than `latest`.

```bash
docker run --rm -p 9092:9092 apache/kafka:4.4.0
```

The default image starts a single combined broker and controller listening on `localhost:9092`. For a compose file, the settings below follow the single-node example shipped in the Kafka repository (4.4 branch); replication factors are 1 because there is one broker.

```yaml
services:
  broker:
    image: apache/kafka:4.4.0
    hostname: broker
    ports:
      - "127.0.0.1:9092:9092"        # bind to loopback only
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: CONTROLLER://:29093,PLAINTEXT_HOST://:9092,PLAINTEXT://:19092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT_HOST://localhost:9092,PLAINTEXT://broker:19092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@broker:29093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_SHARE_COORDINATOR_STATE_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_SHARE_COORDINATOR_STATE_TOPIC_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
```

- Container env vars map to broker properties: prefix `KAFKA_`, upper case, dots become underscores. Containers on the compose network use `broker:19092`; the host uses `localhost:9092`.
- The example compose files in the Kafka repository also cover multi-node, SSL and SASL setups (docker/examples). Use them as the starting point for a secured local stack.
- Schema Registry for local work: `confluentinc/cp-schema-registry` (tag 8.4.0 existed on Docker Hub at the time of checking) needs `SCHEMA_REGISTRY_HOST_NAME`, `SCHEMA_REGISTRY_LISTENERS` and `SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS`; Apicurio Registry (`apicurio/apicurio-registry`) is an alternative. Check each project's license and docs before standardising on one.
- Data in `/tmp` inside the container is lost with the container; mount a named volume only if the data matters.
- Tests: use Testcontainers' Kafka module against the same image tag as development, or an embedded broker from the Kafka test utilities; see integration-testing-expert for general strategy.

## 3. Topics, replication and durability

The durable baseline for a production topic: `replication.factor=3`, `min.insync.replicas=2`, producers with `acks=all`, and `unclean.leader.election.enable=false` (the default).

| Setting | Effect |
|---|---|
| `replication.factor` | Copies of each partition; set at creation (change later with a reassignment) |
| `min.insync.replicas` | With `acks=all`, writes fail with NOT_ENOUGH_REPLICAS when the ISR is smaller. The RF=3, min ISR=2 pair tolerates one broker down for writes and reads |
| `unclean.leader.election.enable` | `true` allows an out-of-sync replica to lead, trading data loss for availability. Leave `false` for data that matters |
| `replica.lag.time.max.ms` | How long a follower may lag before leaving the ISR |
| `broker.rack`, `client.rack` | Spread replicas over zones; consumers can fetch from the closest replica (KIP-392) with a rack-aware replica selector |
| `auto.create.topics.enable` | Keep `false` in production; create topics with code or `kafka-topics.sh` so partitions and configs are deliberate |

```bash
kafka-topics.sh --bootstrap-server broker:9092 --create --topic orders.v1 \
  --partitions 12 --replication-factor 3 \
  --config min.insync.replicas=2 --config retention.ms=604800000
kafka-topics.sh --bootstrap-server broker:9092 --describe --topic orders.v1
```

- `--describe` shows leader, replicas and ISR per partition; a shrinking ISR is the earliest warning sign.
- Do not decrease partitions; increase them only knowing that key-to-partition mapping changes (see [kafka-producers-consumers.md](kafka-producers-consumers.md)).
- Name topics with a stable convention (domain.entity.event.version) and manage them as code (Admin API, Terraform or a topic-as-code tool) with review.
- Internal topics `__consumer_offsets`, `__transaction_state` and (with share groups) `__share_group_state` need their own replication settings; the dev compose above sets them to 1, production keeps the defaults of 3 and min ISR 2.

## 4. Retention and compaction

- `cleanup.policy=delete` (default) removes segments by `retention.ms` (7 days by default) and `retention.bytes`. Retention applies per closed segment, so `segment.bytes` and `segment.ms` influence how soon data disappears. The minimum `segment.bytes` is 1 MB since 4.0.
- `cleanup.policy=compact` keeps at least the latest record per key; a record with a null value (tombstone) deletes the key after `delete.retention.ms`. Compaction does not run on the active segment, so the topic is not a strict "latest only" view. Tune `min.cleanable.dirty.ratio`, `segment.ms` and `max.compaction.lag.ms` when freshness matters.
- `cleanup.policy=compact,delete` combines both. Since 4.2 an empty `cleanup.policy` means infinite retention, equivalent to `retention.ms=-1` and `retention.bytes=-1`.
- Compacted topics need a non-null key on every record. Use them for changelogs, config and entity state, not for event history.
- Tiered storage (remote log) is available through `remote.storage.enable` with a plugin; 4.4 adds delayed upload settings. Treat it as an operations project and read the current docs.
- Consumers can only read what is retained: a consumer group that is down longer than retention loses data, and `auto.offset.reset` decides what happens next.
- Compression and `max.message.bytes` interact with retention sizing; measure the actual on-disk size per partition.

## 5. Security: TLS, SASL and ACLs

Use `SASL_SSL` (or `SSL` with mutual TLS) on every client and inter-broker listener outside local development. `PLAINTEXT` listeners are acceptable only on an isolated development network.

Broker sketch (SCRAM over TLS, KRaft authorizer):

```properties
listeners=SASL_SSL://:9093,CONTROLLER://:9094
advertised.listeners=SASL_SSL://kafka-1.example.internal:9093
inter.broker.listener.name=SASL_SSL
sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
ssl.keystore.location=/etc/kafka/tls/broker.p12
ssl.keystore.type=PKCS12
ssl.truststore.location=/etc/kafka/tls/ca.p12
ssl.truststore.type=PKCS12
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
allow.everyone.if.no.acl.found=false
super.users=User:admin
```

Keystore and key passwords come from a secret store, a protected file or a config provider, never from the repository. Keep the controller listener on its own secured listener too.

- SCRAM credentials are stored in cluster metadata and managed with `kafka-configs.sh --alter --add-config 'SCRAM-SHA-512=[password=<from-secret-store>]' --entity-type users --entity-name <user>`. A password on the command line is visible to other users on the host; prefer the Admin API from a script, or provision during storage formatting as the docs describe. PLAIN sends passwords as-is and is acceptable only over TLS; OAUTHBEARER suits environments with an identity provider.
- OAUTHBEARER on 4.x: allowed token and JWKS URLs must be listed in the `org.apache.kafka.sasl.oauthbearer.allowed.urls` system property (default empty), and 4.4 brokers refuse to start with a JWKS endpoint unless the expected audience and issuer are set.
- ACLs are least-privilege grants per principal, resource and operation. A producer needs Write (and Describe) on its topic, plus Write on its `transactional.id` resource when transactional (check the authorization docs for older brokers and idempotent producers). A consumer needs Read on the topic and Read on the group.

```bash
kafka-acls.sh --bootstrap-server broker:9093 --command-config admin.properties \
  --add --allow-principal User:billing --operation Read --operation Describe \
  --topic orders.v1 --group billing-v1
```

- Client side with librdkafka: `security.protocol=SASL_SSL`, `sasl.mechanism=SCRAM-SHA-512`, `sasl.username`, `sasl.password` (read from the environment or secret manager), `ssl.ca.location`. Leave certificate verification on; never disable hostname checks to silence an error.
- 4.4 adds CIDR-based host patterns for ACLs. Use group ACLs and topic prefix ACLs (`--resource-pattern-type prefixed`) to keep rule counts manageable.
- Rotate certificates and credentials on a schedule; dynamic broker configs allow keystore reload without a restart (`kafka-configs.sh --alter` on the broker entity).

## 6. Command line tools

All live in the distribution `bin/` directory (and in the Docker image under `/opt/kafka/bin`). Flags were renamed for consistency in 4.2 (KIP-1147): `--command-config` and `--command-property` replace older per-tool names, and the old names are deprecated until 5.0.

| Task | Tool |
|---|---|
| Topics: create, describe, alter, delete | `kafka-topics.sh --bootstrap-server ...` |
| Dynamic configs of topics, brokers, users | `kafka-configs.sh --alter --add-config ...` |
| Consumer groups, lag, offset reset | `kafka-consumer-groups.sh --describe --group G`, `--reset-offsets ... --dry-run` then `--execute` |
| Share groups | `kafka-share-groups.sh` (4.4 can initialise offsets from a file) |
| ACLs | `kafka-acls.sh` |
| Quorum status | `kafka-metadata-quorum.sh --bootstrap-server ... describe --status` |
| Feature levels, upgrade finalisation | `kafka-features.sh describe`, `upgrade --release-version 4.4` |
| API versions | `kafka-cluster.sh api-versions` (4.4; `kafka-broker-api-versions.sh` is deprecated) |
| Smoke tests | `kafka-console-producer.sh`, `kafka-console-consumer.sh`, `kafka-producer-perf-test.sh` |
| Inspect log segments | `kafka-dump-log.sh` |

Resetting offsets example (group must be inactive):

```bash
kafka-consumer-groups.sh --bootstrap-server broker:9092 --group billing-v1 \
  --topic orders.v1 --reset-offsets --to-datetime 2026-10-30T00:00:00.000 --dry-run
```

## 7. Upgrades

- Read the "Upgrading" page for every release between the current and target version, including the notes for the clients.
- Order for a rolling upgrade from 3.3.x or newer: upgrade brokers one at a time, verify, then finalise with `kafka-features.sh upgrade --release-version <X.Y>`. Metadata downgrade is possible only when the target version has no metadata changes (the notes say per release).
- Java clients, Connect and Streams must be on 2.1 or newer before upgrading to 4.0 because old protocol versions were removed.
- 4.0 requires Java 17 for brokers, Connect and tools, and Java 11 for clients and Streams; log4j was replaced by log4j2, so migrate logging configs.
- Kafka 4.1.0 shipped a Streams memory leak (KAFKA-19748); the notes advise going straight to 4.1.1 or newer for Streams users.
- Test the consumer-protocol and group-version features in a staging cluster first; after groups use the new protocol, downgrades are constrained.
- Keep one patch line current: at the time of checking, the ASF distribution directory listed 4.2.2, 4.3.2 and 4.4.0.

## 8. Monitoring and consumer lag

Export broker JMX through a Prometheus JMX exporter or the Kafka metrics reporter of your platform, and collect client metrics from producers and consumers.

| Signal | Metric or tool | Why |
|---|---|---|
| Under-replicated partitions | `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` | Followers falling behind; alert when non-zero for several minutes |
| Under min ISR | `kafka.server:type=ReplicaManager,name=UnderMinIsrPartitionCount` | Producers with `acks=all` are failing |
| Offline partitions | `kafka.controller:type=KafkaController,name=OfflinePartitionsCount` | Data unavailable |
| Active controller | `kafka.controller:type=KafkaController,name=ActiveControllerCount` | Exactly one across the cluster |
| Request latency | `kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce` (and `FetchConsumer`) | Broker saturation, slow disks |
| Throughput | `kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec` | Capacity and skew per topic |
| Disk usage | OS metrics per `log.dirs` | Retention misconfiguration fills disks |
| Consumer lag | `kafka-consumer-groups.sh --describe`, client `records-lag-max`, or a lag exporter | Processing falling behind |
| Producer errors | `record-error-rate`, `record-retry-rate`, `request-latency-avg` | Delivery trouble |

- Lag is the log end offset minus the committed offset per partition. Alert on sustained growth or on time-to-drain, not on a fixed number; a stopped consumer shows constant lag with no commits.
- Group-coordinator metrics moved in 4.4: use `kafka.server:type=group-coordinator-metrics,name=group-count,protocol=classic` and related names instead of the deprecated `kafka.coordinator.group:type=GroupMetadataManager` Yammer metrics (removed in 5.0).
- Alert on the user-visible symptom (end-to-end latency, DLT growth) in addition to broker health.
- Enable client telemetry (KIP-714) with a broker-side plugin if you need client metrics centrally; check the docs for the plugin interface.

## 9. Sizing and tuning

- Throughput scales with partitions, but each partition costs file handles, memory, controller work and failover time. Start with the consumer parallelism you need (with headroom) rather than thousands of partitions per topic.
- Disks: sequential I/O, XFS or ext4, JBOD or RAID is a capacity-planning decision; page cache is used heavily, so leave RAM for it rather than a large JVM heap (a few GB heap is typical).
- Network: replication multiplies ingress (RF 3 means each byte is written three times); budget inter-broker and cross-zone traffic.
- Rebalance reassignments (`kafka-reassign-partitions.sh`) move data; throttle them (`--throttle`) during business hours.
- Quotas protect shared clusters: producer and consumer byte-rate quotas per user or client id via `kafka-configs.sh`.
- Benchmark with `kafka-producer-perf-test.sh` and your real message size and compression before settling on `linger.ms`, `batch.size` and partition counts.
