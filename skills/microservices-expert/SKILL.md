---
name: microservices-expert
description: >-
  Designs and reviews microservice systems: service boundaries from bounded contexts, synchronous versus asynchronous communication, sagas (orchestration and choreography), the transactional outbox with idempotent inbox consumers, event schema evolution, API gateway and BFF, service discovery, resilience (timeouts, retries with backoff and jitter, circuit breakers, bulkheads), OpenTelemetry tracing, database per service, consumer-driven contract testing with Pact, and strangler fig migration. Use when splitting a monolith, deciding who owns which data, choosing REST, gRPC or events, designing a distributed workflow, hardening inter-service calls, or deciding whether microservices are warranted at all (modular monolith first). Not for the internals of a single system or capacity planning (use system-design-expert) or for domain modeling inside a context (use ddd-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Microservices Expert

This skill covers the decisions that only exist once a system is split into independently deployed services: where the boundaries go, who owns which data, how services talk, how multi-service workflows stay consistent without distributed transactions, how calls fail safely, and how the whole thing is observed and tested. It also covers the opposite decision: staying with a modular monolith. Examples use TypeScript on Node.js with PostgreSQL, but the patterns are language-neutral. Deep material is in the reference files.

> Verified against OpenTelemetry (traces, metrics and logs stable in the specification; OTLP profiles still in development), `@opentelemetry/api` 1.10.0, `@opentelemetry/sdk-node` 0.300.0, `@pact-foundation/pact` 17.1.x (Pact specification up to v4), `pact-broker-cli`, `opossum` 10.0.0 (Node.js 22+), Apache Kafka producer defaults (`enable.idempotence=true`), Debezium outbox event router and CloudEvents 1.0 attribute naming (2026-10).

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

- Covered: service decomposition, bounded contexts as boundaries, data ownership, REST/gRPC versus messaging, sagas, outbox/inbox, event contracts and schema evolution, gateway and BFF, discovery, resilience, distributed tracing, contract testing, migration from a monolith, and the case against microservices.
- Not covered: internal design of one service or capacity math (system-design-expert), tactical and strategic domain modeling (ddd-expert), layering inside a service (clean-architecture-expert), Kubernetes manifests (kubernetes-expert), REST resource design (rest-api-expert), token and permission design (authentication-expert, authorization-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Boundaries | A service maps to one bounded context and one owning team; the boundary is a business capability, not a table or a layer |
| Data ownership | Database per service (separate schema or instance with separate credentials); no cross-service joins or shared tables; share data through APIs or events |
| Communication | Synchronous (REST, gRPC) for queries that need an answer now; asynchronous events or commands for state propagation and workflows |
| Consistency | No distributed ACID across services; use sagas with compensations and eventual consistency |
| Reliable messaging | Outbox on the producer side, idempotent consumer (inbox or natural idempotency) on the consumer side; delivery is at-least-once |
| Schema evolution | Additive changes, tolerant readers, versioned event types, a compatibility rule enforced in CI (schema registry or contract tests) |
| Edge | API gateway for routing, authentication and rate limits; BFF per client type for aggregation and shaping |
| Resilience | Deadline on every call, bounded retries with exponential backoff and jitter on idempotent operations, circuit breaker, bulkhead, load shedding |
| Observability | W3C Trace Context (`traceparent`) across HTTP and messages, OpenTelemetry SDK, RED metrics per service, correlated logs |
| Migration | Strangler fig: route a slice of traffic to the new service behind a facade, grow, then remove the old code path |

## 3. Workflow

1. Start from the problem: team structure, deployment independence needed, scaling or compliance differences. If none applies, recommend a modular monolith (section 4).
2. Find boundaries with event storming or by mapping business capabilities; check each candidate against the ownership test (one team, one reason to change, one data owner).
3. For every pair of services, write down who calls whom and why. Replace chains of synchronous calls with local data (events) or merge the services.
4. Assign each fact to one owner. Define how other services learn about it (API read, event, or replicated read model).
5. Design each cross-service workflow as a saga: steps, compensations, timeouts, and the state that records progress.
6. Define contracts first: OpenAPI or protobuf for APIs, event schemas for messages, then consumer-driven contract tests.
7. Add the resilience policy per call (deadline, retry rule, breaker, bulkhead) and the observability baseline (traces, RED metrics, structured logs with trace ids).
8. Plan delivery: independent pipelines, backward-compatible rollout order, and a migration path (strangler) if replacing a monolith.

## 4. Decision Rules

- Default to a modular monolith: one deployable, strict module boundaries, one database schema per module, communication through module interfaces or in-process events. Extract a service only when a concrete need exists: independent release cadence for separate teams, a different scaling profile, a different runtime or compliance boundary, or fault isolation of a risky component.
- Do not split when the team is small, the domain is not yet understood, or the same people deploy everything anyway. Premature splitting yields a distributed monolith: services that must be released together.
- Boundary test: if a change to one service routinely requires changes to another, the boundary is wrong. If two services always call each other for every request, merge them.
- Synchronous when the caller cannot proceed without the answer and the callee is a stable, low-latency dependency. Asynchronous when the result can arrive later, when several services react to one fact, or when the caller should not fail because a downstream is down.
- Commands go to one owner (a queue or a request); events announce a fact that already happened and may have zero or many consumers. Do not use events as disguised remote procedure calls.
- Event content: a thin notification (ids only, consumer calls back) keeps the owner in control but adds coupling at read time; event-carried state transfer (the data consumers need) removes the callback but makes the schema a contract. Pick per event, not globally.
- Saga style: choreography (services react to each other's events) for two or three participants with simple compensation; orchestration (one coordinator holds the state machine) when there are many steps, branching, deadlines, or a need to see progress in one place.
- Two-phase commit across services is not an option on most brokers and managed databases; model the process as a saga.
- Retry only operations that are idempotent or protected by an idempotency key, and only at one layer of the stack; stacked retries multiply load (3 layers with 3 attempts is 27 calls).
- Service discovery: use the platform's DNS and load balancing (for example Kubernetes Services); add client-side discovery or a mesh only when needed for features such as mTLS, locality-aware routing, or fine-grained traffic shifting.
- Gateway versus BFF: one gateway for cross-cutting edge concerns; one BFF per distinct client experience (web, mobile, partner API) when payload shaping diverges. Keep business rules out of both.
- Tenant isolation is a property of every operation: reads, inserts, updates, deletes, cache keys, message keys, and search or analytics sinks all carry and enforce the tenant.

## 5. Coding Standards

- Every outbound call has a deadline derived from the caller's remaining time; pass the deadline or timeout downstream rather than starting a fresh one.
- Handlers for messages are idempotent by construction: dedupe on a message id stored in the same transaction as the side effect.
- Never publish to a broker inside a database transaction expecting atomicity; write an outbox row instead.
- Event names are past-tense facts with a version suffix (`order.placed.v1`); commands are imperative (`reserve-stock`). Use a stable envelope with id, type, source, time, tenant, trace context, and schema version.
- Validate every inbound message and request at the service boundary with a schema; reject unknown versions to a dead-letter queue instead of guessing.
- Use opaque string ids (UUID or ULID) generated by the owner; never expose database sequences across contexts.
- Pass tenant and caller identity from verified credentials (token claims or authenticated message metadata), never from a request body or an unverified header.
- Log structured JSON with `trace_id`, `span_id`, `tenant_id`, service name and version; never log secrets or full payloads containing personal data.

## 6. Project Structure

```
services/
├── orders/                      # one bounded context, one owning team
│   ├── src/
│   │   ├── api/                 # HTTP/gRPC handlers, request validation
│   │   ├── domain/              # entities, domain events, business rules
│   │   ├── app/                 # use cases, saga steps
│   │   ├── infra/
│   │   │   ├── db/              # repositories, migrations, outbox/inbox tables
│   │   │   ├── messaging/       # outbox relay, consumers, DLQ handling
│   │   │   └── http/            # outbound clients with resilience policy
│   │   └── telemetry.ts         # OpenTelemetry bootstrap (loaded first)
│   ├── contracts/
│   │   ├── openapi.yaml
│   │   ├── events/              # JSON Schema or protobuf for published events
│   │   └── pacts/               # generated consumer pacts (gitignored if published to a broker)
│   └── Dockerfile
├── payments/
├── inventory/
platform/
├── gateway/                     # routes, authN, rate limits
└── bff-web/
```

## 7. Design Patterns

- **Database per service**: each service owns its schema and migrations; other services never connect to it. Reporting uses events or a replicated read model.
- **Saga**: a sequence of local transactions, each with a compensating action, plus a durable saga state. Compensation is a business reversal (refund, release stock), not a rollback. See [references/messaging-patterns.md](references/messaging-patterns.md).
- **Transactional outbox**: write the state change and the event row in one local transaction; a relay (poller or change-data-capture such as the Debezium outbox event router) publishes later.
- **Inbox / idempotent consumer**: record the message id with the side effect in one transaction; a redelivered message hits the unique key and is skipped.
- **Event-carried state transfer and read models**: consumers keep a local projection of data they need, so queries do not call the owner on the hot path.
- **API composition and BFF**: aggregate several service reads for a client; accept partial results with explicit degraded fields.
- **Anti-corruption layer**: translate a legacy or external model at the edge so it does not leak into the new context.
- **Strangler fig**: a routing facade sends selected routes or tenants to the new service while the monolith serves the rest; migrate data with dual-write avoidance (outbox or CDC), not ad hoc dual writes.
- **Resilience set**: timeout, retry with backoff and jitter, circuit breaker, bulkhead, load shedding. See [references/resilience.md](references/resilience.md).

## 8. Best Practices

- Version APIs and events; run old and new consumers side by side. Deploy order is producer-compatible-first: add fields, then update consumers, then remove old fields after all consumers moved.
- Make breaking changes by adding a new event type or API version, not by changing meaning in place.
- Keep one source of truth per fact; replicated copies are caches with a known staleness and an owner who can rebuild them.
- Prefer coarse-grained APIs over chatty ones; measure calls per request across the call graph.
- Use a dead-letter queue with alerting and a replay tool; a message that always fails must not block the partition.
- Give every saga a timeout and a terminal state; surface stuck sagas through metrics.
- Own the runbook: each service documents its SLOs, dependencies, dashboards and on-call contact next to the code.
- Propagate trace context in HTTP headers and in message headers so one trace covers the whole workflow.

## 9. Performance

- Latency adds up across synchronous hops; budget the end-to-end deadline and give each hop a slice. Parallelize independent calls with a bound on concurrency.
- Replace read-time fan-out with local read models fed by events.
- Cache with explicit keys that include the tenant and the version of the data; define invalidation by event, not only by TTL.
- Bound everything: connection pools, in-flight requests per downstream (bulkhead), queue depth, batch sizes, and consumer concurrency per partition.
- Keep messages small; put large blobs in object storage and send a reference with an integrity hash.
- Partition message keys so that ordering is required only per aggregate (for example `tenantId:orderId`); more partitions raise parallelism but not per-key ordering.
- Reuse HTTP connections (keep-alive, HTTP/2 or gRPC) to avoid handshake cost on every call.

## 10. Security

- Authenticate service-to-service traffic (mutual TLS or signed workload identity) and authorize each call in the receiving service; a network perimeter or a gateway alone is not authorization.
- Verify end-user identity in every service that acts on user data: pass a short-lived signed token with audience restriction, or exchange tokens per hop. Do not forward long-lived credentials.
- Enforce tenant isolation on every operation: derive `tenant_id` from the verified token or message metadata, include it in every `SELECT`, `INSERT`, `UPDATE` and `DELETE` predicate, in unique keys (inbox, idempotency), in cache and message keys. Add database row-level security as a second layer where the database supports it.
- Do not expose internal services; only the gateway or BFF is reachable from outside. Rate limit and size-limit at the edge, and validate again inside.
- Treat messages as untrusted input: validate schema and authorization claims, bound sizes, and avoid deserializing arbitrary types.
- Protect brokers and topics with authentication, per-service ACLs (produce and consume only what the service needs), and TLS. Dead-letter queues hold the same sensitive data as the original messages; restrict access.
- Keep secrets in a secret manager injected at runtime, never in images, repositories, environment files in version control, or build arguments.
- Do not log tokens or personal data; propagate correlation ids instead. Redact sensitive attributes in spans.

## 11. Testing

- Unit-test domain logic in each service; integration-test adapters (database, broker) against real instances in containers.
- Consumer-driven contract tests: consumers publish pacts (HTTP and message), providers verify them in CI, and a broker check (`can-i-deploy`) gates releases. Details in [references/observability-and-testing.md](references/observability-and-testing.md).
- Test sagas with failure injection: step failure at each point, compensation failure, duplicate and out-of-order messages, timeouts.
- Test idempotency by delivering every message twice and in a shuffled order; assert one side effect.
- Test resilience policies with fault injection (latency, errors, dropped connections) and verify breakers open and recover.
- Keep end-to-end tests few and focused on critical journeys; they are slow and flaky in distributed systems.
- Test tenant isolation negatively: a request or message for tenant A must not read or change tenant B rows, including through update and delete paths.

## 12. Review Checklist

- [ ] Each service maps to one bounded context and one owning team; no shared database tables.
- [ ] A modular monolith was considered and the reason for splitting is written down.
- [ ] No synchronous call chains deeper than necessary; no circular dependencies.
- [ ] Every outbound call has a deadline; retries are bounded, jittered, limited to idempotent operations and done at one layer.
- [ ] State change and event publication go through an outbox; consumers are idempotent.
- [ ] Event and API changes are backward compatible; compatibility is checked in CI.
- [ ] Sagas have compensations, timeouts and a visible terminal state.
- [ ] Tenant and identity come from verified credentials and are applied to reads and writes.
- [ ] Trace context propagates across HTTP and messages; each service exposes RED metrics.
- [ ] Contract tests exist for every consumer-provider pair and run in CI.
- [ ] Dead-letter handling, alerts and a replay procedure exist.

## 13. Production Notes

- Roll out with backward-compatible steps and per-service canaries; keep feature flags for behavior that spans services.
- Define SLOs per user journey, not only per service; alert on error budget burn and on saga age and DLQ depth.
- Capacity: consumer lag, partition count, connection pool saturation and breaker state are first-class dashboards.
- Run chaos or game-day exercises for the dependencies that have fallbacks; an untested fallback is a guess.
- Outbox tables grow: delete or archive published rows on a schedule, and monitor the age of the oldest unpublished row.
- Schema registries and shared libraries create coupling; version shared client libraries and avoid shared domain libraries between services.
- Be explicit about ordering and delivery guarantees per topic; document them with the event contract.
- Operational cost grows with service count (pipelines, dashboards, on-call). Revisit merges when a split no longer pays for itself.

## 14. Examples

Outbox write, relay and tenant-safe idempotent consumer on PostgreSQL. The relay is a trusted platform component that reads across tenants; every service-side write carries the tenant.

```sql
CREATE TABLE outbox (
  id             uuid PRIMARY KEY,
  tenant_id      uuid NOT NULL,
  aggregate_type text NOT NULL,
  aggregate_id   text NOT NULL,
  type           text NOT NULL,           -- e.g. order.placed.v1
  payload        jsonb NOT NULL,
  traceparent    text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  published_at   timestamptz
);
CREATE INDEX outbox_unpublished ON outbox (created_at, id) WHERE published_at IS NULL;

CREATE TABLE inbox (
  tenant_id    uuid NOT NULL,
  consumer     text NOT NULL,
  message_id   text NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, consumer, message_id)
);
```

```ts
import { randomUUID } from "node:crypto";
import type { Pool } from "pg";

interface Publisher {
  publish(m: { topic: string; key: string; value: string; headers: Record<string, string> }): Promise<void>;
}
interface Ctx { tenantId: string; traceparent?: string }

// Producer: state change and event row commit together or not at all.
export async function placeOrder(pool: Pool, ctx: Ctx, orderId: string, totalCents: number) {
  const c = await pool.connect();
  try {
    await c.query("BEGIN");
    await c.query(
      "INSERT INTO orders (id, tenant_id, status, total_cents) VALUES ($1, $2, 'PENDING', $3)",
      [orderId, ctx.tenantId, totalCents],
    );
    await c.query(
      `INSERT INTO outbox (id, tenant_id, aggregate_type, aggregate_id, type, payload, traceparent)
       VALUES ($1, $2, 'order', $3, 'order.placed.v1', $4, $5)`,
      [randomUUID(), ctx.tenantId, orderId, JSON.stringify({ orderId, totalCents }), ctx.traceparent ?? null],
    );
    await c.query("COMMIT");
  } catch (e) {
    await c.query("ROLLBACK");
    throw e;
  } finally {
    c.release();
  }
}

// Relay: at-least-once. Run one instance per partition of the outbox (or use CDC)
// when per-aggregate ordering matters; SKIP LOCKED alone does not preserve order across workers.
export async function relayOnce(pool: Pool, pub: Publisher, batch = 100): Promise<number> {
  const c = await pool.connect();
  try {
    await c.query("BEGIN");
    const { rows } = await c.query(
      `SELECT id, tenant_id, aggregate_id, type, payload, traceparent
         FROM outbox WHERE published_at IS NULL
        ORDER BY created_at, id LIMIT $1 FOR UPDATE SKIP LOCKED`,
      [batch],
    );
    for (const r of rows) {
      await pub.publish({
        topic: "orders.events",
        key: `${r.tenant_id}:${r.aggregate_id}`,
        value: JSON.stringify(r.payload),
        headers: { id: r.id, type: r.type, tenantid: r.tenant_id, ...(r.traceparent ? { traceparent: r.traceparent } : {}) },
      });
    }
    if (rows.length) {
      await c.query("UPDATE outbox SET published_at = now() WHERE id = ANY($1::uuid[]) AND published_at IS NULL", [
        rows.map((r) => r.id),
      ]);
    }
    await c.query("COMMIT");
    return rows.length;
  } catch (e) {
    await c.query("ROLLBACK");
    throw e;
  } finally {
    c.release();
  }
}

// Consumer: dedupe and side effect in one transaction; tenant is in every predicate.
export async function onPaymentCaptured(pool: Pool, msg: { id: string; tenantId: string; orderId: string }) {
  const c = await pool.connect();
  try {
    await c.query("BEGIN");
    const seen = await c.query(
      "INSERT INTO inbox (tenant_id, consumer, message_id) VALUES ($1, 'orders', $2) ON CONFLICT DO NOTHING",
      [msg.tenantId, msg.id],
    );
    if (seen.rowCount === 1) {
      await c.query(
        "UPDATE orders SET status = 'PAID' WHERE id = $1 AND tenant_id = $2 AND status = 'PENDING'",
        [msg.orderId, msg.tenantId],
      );
    }
    await c.query("COMMIT");
  } catch (e) {
    await c.query("ROLLBACK");
    throw e;
  } finally {
    c.release();
  }
}
```

Outbound call with a deadline, a jittered retry limited to safe failures, and a circuit breaker. The breaker wraps a single attempt; the retry loop stops when the breaker is open.

```ts
import CircuitBreaker from "opossum";

class HttpError extends Error {
  constructor(readonly status: number, readonly retryAfterMs?: number) { super(`HTTP ${status}`); }
}
const RETRYABLE = new Set([429, 502, 503, 504]);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function attempt(url: string, timeoutMs: number): Promise<unknown> {
  const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs), headers: { accept: "application/json" } });
  if (!res.ok) {
    const ra = Number(res.headers.get("retry-after"));
    throw new HttpError(res.status, Number.isFinite(ra) && ra > 0 ? ra * 1000 : undefined);
  }
  return res.json();
}

const breaker = new CircuitBreaker(attempt, {
  timeout: false,                 // the fetch signal already enforces the per-attempt deadline
  errorThresholdPercentage: 50,
  volumeThreshold: 20,            // do not trip on a tiny sample
  resetTimeout: 10_000,           // then half-open and probe
  capacity: 50,                   // bulkhead: at most 50 concurrent calls to this dependency
  errorFilter: (e: unknown) => e instanceof HttpError && e.status >= 400 && e.status < 500 && e.status !== 429, // client errors are not dependency failures
});

export async function getWithRetry(url: string, deadlineMs = 2000, maxAttempts = 3): Promise<unknown> {
  const start = Date.now();
  for (let n = 0; ; n++) {
    const left = deadlineMs - (Date.now() - start);
    if (left <= 0) throw new Error("deadline exceeded");
    try {
      return await breaker.fire(url, Math.min(left, 800));
    } catch (e) {
      const retryable = (e instanceof HttpError && RETRYABLE.has(e.status)) || (e as any)?.name === "TimeoutError" || (e as any)?.name === "TypeError";
      if ((e as any)?.code === "EOPENBREAKER" || (e as any)?.code === "ESEMLOCKED" || !retryable || n + 1 >= maxAttempts) throw e;
      const backoff = Math.random() * Math.min(1000, 100 * 2 ** n);         // full jitter
      await sleep(Math.min(Math.max(backoff, (e as HttpError).retryAfterMs ?? 0), Math.max(left - 50, 0)));
    }
  }
}
```

CloudEvents-style envelope for an event, with additive evolution (new optional fields only, same major version):

```json
{
  "specversion": "1.0",
  "id": "6f1c1d1e-7a0f-4a53-9c1b-0c6a0f9d7e11",
  "source": "/services/orders",
  "type": "com.example.order.placed.v1",
  "time": "2026-10-30T12:00:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.example.com/orders/order-placed/1.2.json",
  "subject": "order/9d2b",
  "tenantid": "2f0a8c70-1c6e-4b5b-8f4e-5c0c4e9d1a21",
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "data": { "orderId": "9d2b", "totalCents": 4200, "currency": "EUR" }
}
```

## 15. Common Mistakes

- **Distributed monolith**: services released together, sharing a database or a "common" domain library. Merge them or fix the boundary and the data ownership.
- **Splitting by technical layer or by table**: a "user table service" produces chatty calls. Split by business capability.
- **Shared database**: a migration in one service breaks another. Each service owns its schema; integrate through APIs and events.
- **Dual write**: updating the database and publishing to a broker in separate steps loses events on a crash between them. Use an outbox or CDC.
- **Assuming exactly-once delivery**: brokers deliver at least once; Kafka idempotent producers and transactions cover Kafka-internal flows, not your database side effects. Make consumers idempotent.
- **Retries everywhere**: retries at the client, the mesh and the gateway multiply into a retry storm. Retry at one layer, with jitter and a budget, and honor `Retry-After`.
- **Retrying non-idempotent calls** (payments, order creation) without an idempotency key creates duplicates.
- **No timeout, or a timeout longer than the caller's**: threads and connections pile up and the failure cascades. Propagate a shrinking deadline.
- **Tenant filter on reads only**: `UPDATE orders SET ... WHERE id = $1` lets one tenant modify another's row. Put `tenant_id` in every write predicate, unique key and cache key.
- **Trusting the gateway only**: internal services that skip authorization are one misrouted request away from a breach.
- **Orchestrator that owns business rules**: the saga coordinator sequences steps; the rules stay in the services.
- **Breaking event changes in place** (rename a field, change a unit): add a new version and migrate consumers.
- **Synchronous call from an event handler to the producer** for data the event could have carried: re-creates temporal coupling.
- **Unbounded outbox or DLQ**: nobody watches it until the disk is full. Alert on age and size, purge on schedule.
- **Ignoring the organization**: more services than teams to own them leads to orphaned services. Match service count to ownership capacity.

## 16. References

- [references/messaging-patterns.md](references/messaging-patterns.md): sagas (orchestration and choreography with a worked orchestrator), outbox variants (polling and CDC), inbox and idempotency keys, ordering, DLQ and replay, event schema evolution, API gateway and BFF.
- [references/resilience.md](references/resilience.md): deadlines, retry rules with backoff and jitter, retry budgets, circuit breaker states, bulkheads, load shedding, fallbacks, service discovery and health checks.
- [references/observability-and-testing.md](references/observability-and-testing.md): OpenTelemetry signal status and Node.js bootstrap, trace propagation through messages, RED metrics, Pact consumer and provider tests with `can-i-deploy`, and strangler fig migration steps.
- Official docs: https://opentelemetry.io/docs/ , https://docs.pact.io/ , https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html , https://kafka.apache.org/documentation/ , https://cloudevents.io/ , https://microservices.io/patterns/
