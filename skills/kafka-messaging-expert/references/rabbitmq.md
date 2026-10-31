# RabbitMQ 4.x

Broker model, queue types, reliable publishing and consuming, dead-lettering, streams, protocols, security, operations and local development for RabbitMQ 4.x. Facts come from the RabbitMQ 4.0.1, 4.2.0, 4.3.0 and 4.4.0 release notes in the rabbitmq-server repository and Docker Hub tag listings (2026-10). The Python code was written against pika 1.4.4 and checked for syntax and API names, not run against a broker.

## Contents

1. [Versions and what changed in 4.x](#1-versions-and-what-changed-in-4x)
2. [Exchanges, queues and bindings](#2-exchanges-queues-and-bindings)
3. [Queue types](#3-queue-types)
4. [Reliable publishing and consuming](#4-reliable-publishing-and-consuming)
5. [Dead-letter exchanges and retries](#5-dead-letter-exchanges-and-retries)
6. [Streams](#6-streams)
7. [Protocols and client libraries](#7-protocols-and-client-libraries)
8. [Security](#8-security)
9. [Operations and monitoring](#9-operations-and-monitoring)
10. [Local development](#10-local-development)

## 1. Versions and what changed in 4.x

The Docker Hub `rabbitmq` image listed 4.4.0 as the newest feature release, with patch lines 4.3.7, 4.2.9, 4.1.8 and 4.0.9 alongside it. Check the RabbitMQ release and support pages for which lines receive fixes before choosing one.

- 4.0: AMQP 1.0 became a core protocol that is always enabled; classic queue mirroring was removed (classic queues are single-node, non-replicated); quorum queues gained priorities and a default redelivery (delivery) limit of 20; Khepri became fully supported as a metadata store.
- 4.2: Khepri became the default metadata store for new clusters; Direct Reply-To for AMQP 1.0; AMQP 1.0 messages without a header section are treated as non-durable (`durable` defaults to false per the spec), so AMQP 1.0 senders must set `durable=true` explicitly (the RabbitMQ-maintained AMQP 1.0 clients do by default).
- 4.3: Khepri is the only metadata store (Mnesia removed); a majority of nodes must be online for the cluster to be available; partition handling settings no longer apply; classic queue storage v1 (CQv1) was removed; deprecated features `amqp_address_v1`, `global_qos`, `queue_master_locator` and `transient_nonexcl_queues` became denied by default (declaring a transient non-exclusive queue is rejected); only 4.2.x clusters upgrade in place to 4.3.
- 4.4: quorum queues support delayed messages through an `x-opt-delivery-time` annotation or header (milliseconds since the Unix epoch); a changed `delivery-limit` policy applies to existing quorum queues; Erlang 28 and 29 are supported; stricter OpenID Connect discovery validation.

Upgrades must follow the documented path (usually one minor line at a time) with feature flags enabled between steps; read the release notes of every line you cross.

## 2. Exchanges, queues and bindings

Publishers send to an exchange with a routing key; the exchange routes copies to bound queues; consumers read from queues.

| Exchange type | Routing rule |
|---|---|
| default (nameless) | Routes to the queue whose name equals the routing key |
| `direct` | Exact routing key match |
| `fanout` | All bound queues; the key is ignored |
| `topic` | Pattern match on dot-separated keys, `*` for one word, `#` for zero or more |
| `headers` | Match on message headers (`x-match` any or all) |
| consistent hash, local random | Plugin or core types for sharding and local routing; see the exchange docs |

- Declare topology idempotently at application start (exchange, queue, binding) with the same arguments; a redeclaration with different arguments fails.
- Prefer one exchange per bounded context or event family and bind queues per consumer service; queues are the unit of load balancing (competing consumers) and of backlog.
- An unroutable message is dropped silently unless the publisher sets `mandatory` (returned with `basic.return`) or the exchange has an `alternate-exchange` argument.
- Use topic exchanges for pub/sub with filtering, direct for task routing, and avoid putting business payload in routing keys.

## 3. Queue types

| Type | Use when | Notes |
|---|---|---|
| Quorum (`x-queue-type: quorum`) | Default choice for durable, replicated queues | Raft-replicated across nodes (odd replica count, typically 3); safe under node loss; poison-message handling via delivery limit (default 20); at-least-once dead-lettering |
| Classic (`x-queue-type: classic`) | Transient or exclusive queues, very large non-critical backlogs on one node, low overhead | Not replicated in 4.x. Storage v2 only (v1 removed in 4.3) |
| Stream (`x-queue-type: stream`) | Append-only log, replay, many consumers, high fan-out | Section 6; consumption does not delete messages |

- Quorum queues must be durable and cannot be exclusive or auto-delete; declare them with `x-queue-type: quorum` as an argument. Client libraries that omit the argument create classic queues by default (the default type can also be set per vhost).
- Quorum queues trade some throughput and memory for safety; plan disk and a cluster of 3 or 5 nodes. Long queues are not a goal: keep backlogs short and monitor length.
- Single active consumer (`x-single-active-consumer: true`) keeps order for one logical consumer with failover.
- Message and queue TTL, max length with `x-overflow` (`drop-head`, `reject-publish`), and priorities exist; confirm per-queue-type support in the docs (quorum priorities are not identical to classic).
- Classic mirrored queue policies from 3.x have no effect in 4.x; migrate to quorum queues or streams.

## 4. Reliable publishing and consuming

Publisher side: declare durable queues, publish persistent messages (`delivery_mode=2`), enable publisher confirms, and use `mandatory` to detect unroutable messages. A confirm means the broker took responsibility (for quorum queues, after a majority replicated the message).

```python
import os
import ssl

import pika
from pika.exceptions import NackError, UnroutableError

params = pika.ConnectionParameters(
    host=os.environ["RABBIT_HOST"],
    port=5671,
    virtual_host="shop",
    credentials=pika.PlainCredentials(os.environ["RABBIT_USER"], os.environ["RABBIT_PASS"]),
    ssl_options=pika.SSLOptions(
        ssl.create_default_context(cafile=os.environ["RABBIT_CA"]),
        os.environ["RABBIT_HOST"],
    ),
    heartbeat=30,
)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.confirm_delivery()

channel.exchange_declare("orders", exchange_type="topic", durable=True)
channel.queue_declare(
    "billing.orders",
    durable=True,
    arguments={"x-queue-type": "quorum"},
)
channel.queue_bind("billing.orders", "orders", routing_key="order.created")

try:
    channel.basic_publish(
        exchange="orders",
        routing_key="order.created",
        body=b'{"id": 42}',
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent,
            content_type="application/json",
            message_id="evt-42-1",
        ),
        mandatory=True,
    )
except (UnroutableError, NackError):
    ...  # retry later or store for re-send; do not drop silently
```

Consumer side: manual acknowledgements, a bounded prefetch, idempotent handlers.

```python
def handle(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except TransientError:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # dead-letter


channel.basic_qos(prefetch_count=20)
channel.basic_consume("billing.orders", on_message_callback=handle, auto_ack=False)
channel.start_consuming()
```

- Prefetch (`basic.qos`) bounds unacknowledged messages per consumer. Start at 10 to 50 for short tasks, 1 for long ones, and tune with throughput measurements. Global (per-channel) QoS is a deprecated feature that is denied by default from 4.3; use per-consumer prefetch.
- `auto_ack=True` loses messages on crash; use it only for data you can lose.
- Acknowledge only after the side effect is durable. A message delivered but not acknowledged is redelivered after the channel closes, and quorum queues count deliveries against the delivery limit.
- The consumer acknowledgement timeout (30 minutes by default for queue types that enforce it; check the docs) closes a channel that holds a delivery too long.
- Requeueing a poison message in a tight loop starves the queue; dead-letter it or use a retry delay (section 5).
- Pika's `BlockingConnection` is not thread-safe: use one connection per thread or use `aio-pika` (10.2.1 on PyPI) for asyncio. Reconnect with backoff on connection errors; heartbeats detect dead peers.
- Java and other languages: use the official clients and prefer the confirm APIs with batching rather than waiting per message.

## 5. Dead-letter exchanges and retries

A queue with `x-dead-letter-exchange` (or a policy) sends rejected (`requeue=false`), expired (TTL), overflowed and delivery-limit-exceeded messages to that exchange, with `x-death` headers recording the reason and count.

```python
channel.exchange_declare("billing.dlx", exchange_type="direct", durable=True)
channel.queue_declare("billing.orders.dead", durable=True, arguments={"x-queue-type": "quorum"})
channel.queue_bind("billing.orders.dead", "billing.dlx", routing_key="billing.orders")
channel.queue_declare(
    "billing.orders",
    durable=True,
    arguments={
        "x-queue-type": "quorum",
        "x-dead-letter-exchange": "billing.dlx",
        "x-dead-letter-routing-key": "billing.orders",
        "x-dead-letter-strategy": "at-least-once",
        "x-overflow": "reject-publish",   # required for at-least-once dead-lettering
        "x-delivery-limit": 5,
    },
)
```

- Dead-lettering from quorum queues defaults to `at-most-once`; `at-least-once` needs `x-overflow: reject-publish` and a quorum target, and buffers messages until the DLX target confirms. Verify the argument names and prerequisites in the quorum queue docs for your version.
- Prefer a policy for `dead-letter-*` and `delivery-limit` so operators can change them without redeclaring queues.
- Delayed retry: dead-letter into a wait queue with a per-queue TTL whose own DLX points back at the work exchange, or use 4.4 quorum queue delayed delivery (`x-opt-delivery-time`). Cap retries (count in a header) and finish in a parking-lot queue that people look at.
- Messages in the dead-letter queue need a replay tool (shovel or a script) and an alert on queue length.

## 6. Streams

Streams are an append-only, replicated log (non-destructive reads, replay from an offset, many consumers, high throughput), similar in spirit to a Kafka partition.

- Declare with `x-queue-type: stream`, and set retention via `x-max-length-bytes` and `x-max-age`. Streams are not for per-message routing or priorities.
- Two ways to use them: AMQP 0-9-1 or AMQP 1.0 clients consume with a prefetch, manual acks and an `x-stream-offset` consumer argument (first, last, next, an offset or a timestamp); or the dedicated stream protocol (default port 5552, `rabbitmq_stream` plugin) with the stream clients, which supports deduplicating producers, super streams (partitioned streams) and single active consumer.
- AMQP 1.0 clients can filter streams server-side with SQL-like filter expressions (added in 4.2).
- Choose a stream over Kafka when the rest of the system is already RabbitMQ and the volume fits a few nodes; choose Kafka for large partitioned pipelines, a connector ecosystem and stream processing.

## 7. Protocols and client libraries

- AMQP 0-9-1 (port 5672, 5671 for TLS) is the long-standing protocol and remains supported on 4.x. Python: `pika` 1.4.4, `aio-pika` 10.2.1.
- AMQP 1.0 is a core protocol in 4.x with its own address format and topology management, and was benchmarked at more than twice the 3.13 throughput on some workloads per the 4.0 notes. The RabbitMQ team maintains AMQP 1.0 client libraries; see the RabbitMQ client libraries page for the current languages.
- Do not mix assumptions between protocols: AMQP 1.0 durability is per-message `durable` header, addresses use the `/exchanges/...` and `/queues/...` conventions, and flow control uses link credit.
- Other protocols via plugins: MQTT, STOMP, and the stream protocol. Native MQTT 5 and AMQP 1.0 message interceptors exist in 4.2 for policy-style processing.
- `faststream` (0.7.8 on PyPI) offers a framework layer over RabbitMQ and Kafka for Python; check its docs for supported features before adopting.
- JavaScript: `amqplib` 2.2.0 on npm for AMQP 0-9-1; check its README for the current API shape.

## 8. Security

- Disable or restrict the default `guest` account: it is limited to loopback connections by default; create dedicated users per application with least-privilege permissions per vhost: `configure`, `write`, `read` regexes, for example `^orders\.` for each.
- Use TLS (`listeners.ssl.default = 5671`, `ssl_options.cacertfile`, `ssl_options.certfile`, `ssl_options.keyfile`, `ssl_options.verify = verify_peer`, `ssl_options.fail_if_no_peer_cert = true` for mutual TLS) and disable the plain listener where possible. Clients verify the server certificate and host name.
- Authentication backends: internal database, LDAP, HTTP, OAuth 2.0 / OpenID Connect (4.4 validates discovery documents more strictly; set `auth_oauth2.discovery.verify_issuer` / `verify_https_endpoints` only if you must accommodate a non-compliant provider).
- Management UI and HTTP API: put behind TLS, restrict network access, and use dedicated monitoring users with the `monitoring` tag only. The 4.4 hashing endpoint changed to `POST /api/auth/hash_password` with a JSON body.
- Passwords on a `rabbitmqctl add_user` command line are visible in process listings; prefer definitions import with password hashes or an identity provider.
- A passive queue or exchange declaration needs at least one of configure, write or read permission on that entity from 4.4 on.
- Never expose 5672, 15672, 25672 or the Erlang distribution port range to the internet; restrict inter-node ports to the cluster network, and keep the Erlang cookie secret.

## 9. Operations and monitoring

- Cluster size: 3 nodes (or 5) for quorum queues and Khepri; spread across failure zones; a majority must stay up (Khepri and Raft). Two-node clusters cannot tolerate a failure.
- Tools: `rabbitmqctl` (cluster status, users, permissions, policies, feature flags), `rabbitmq-diagnostics` (health checks, `check_running`, `check_local_alarms`), `rabbitmq-plugins`, `rabbitmq-queues` (quorum queue operations), `rabbitmqadmin` (HTTP API client; the v1 download endpoint was removed in 4.3).
- Metrics: `rabbitmq_prometheus` plugin (HTTP port 15692) with the Grafana dashboards from the RabbitMQ project. Watch queue length and age, unacknowledged messages, consumer count and utilisation, publish and confirm rates, connection and channel counts, memory and disk alarms, Raft log growth.
- Alarms: a memory or disk alarm blocks publishers cluster-wide; set `vm_memory_high_watermark` and `disk_free_limit` deliberately and alert before they trigger.
- Avoid thousands of short-lived connections and channels; use long-lived connections with a few channels. Connection storms hurt more than throughput.
- Queue length limits and TTLs are safety valves, not substitutes for consumers that keep up.
- Definitions (users, vhosts, queues, policies) can be exported and imported; keep them in version control without secrets.

## 10. Local development

The official Docker image is `rabbitmq`; the `-management` tag adds the management UI (tags such as `4.4.0-management` and `4-management` existed at the time of checking). Ports: 5672 AMQP, 15672 management, 5552 streams (if the plugin is enabled).

```yaml
services:
  rabbitmq:
    image: rabbitmq:4.4-management
    ports:
      - "127.0.0.1:5672:5672"
      - "127.0.0.1:15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBIT_USER:?set RABBIT_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBIT_PASS:?set RABBIT_PASS}
    volumes:
      - rabbit-data:/var/lib/rabbitmq
volumes:
  rabbit-data:
```

- Take the credentials from an untracked `.env` file or the shell, not from the compose file; bind ports to loopback.
- Enable extra plugins at start with an `enabled_plugins` file or `rabbitmq-plugins enable` in a derived image.
- For tests use Testcontainers' RabbitMQ module against the same tag as production; wait for readiness with `rabbitmq-diagnostics check_running`, and use a fresh vhost or unique queue names per test.
