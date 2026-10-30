---
name: scalability-expert
description: >-
  Makes systems fast and able to grow under load: capacity planning (Little's law, utilization, Amdahl and the Universal Scalability Law), performance profiling (USE and RED methods, flame graphs), load testing with k6, Locust and Gatling, caching and invalidation, database scaling (indexes, pooling, read replicas, partitioning, sharding), queues and backpressure, autoscaling (HPA, KEDA), CDN, rate limiting, tail latency (p99, timeouts, hedging) and cost trade-offs. Absorbs the former performance-optimization-expert skill. Use when a service is slow, a load test or capacity estimate is needed, a bottleneck must be found, or an architecture must handle ten times the traffic. Not for the architecture of the whole product (use system-design-expert) or frontend vitals (use core-web-vitals-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Scalability Expert

This skill covers how to find and remove bottlenecks and how to design for growth: measuring first, modeling capacity, testing load, and choosing among caching, data-layer scaling, asynchronous processing and autoscaling, with cost in view. It absorbs the former performance-optimization-expert skill; profiling and single-service tuning live in a dedicated reference, alongside references for load testing, data and traffic scaling, and capacity and autoscaling.

> Verified against k6 2.3.0, Locust 2.47.0, Gatling 3.15.1, KEDA 2.21.0, Kubernetes 1.37 (HPA `autoscaling/v2`), PgBouncer 1.26.1, PostgreSQL declarative partitioning (2026-10).

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

- Covered: performance diagnosis and tuning of services, capacity planning, load and stress testing, caching layers, database and queue scaling, autoscaling policy, rate limiting and load shedding, tail latency, CDN offload, and cost/performance trade-offs.
- Not covered: choosing the overall system architecture (system-design-expert), splitting into services (microservices-expert), PostgreSQL internals and query planning in depth (postgresql-expert), Redis data structures and clustering (redis-expert), Kubernetes object details (kubernetes-expert), browser performance and Core Web Vitals (core-web-vitals-expert).
- Scaling is the last step, not the first: remove waste, then add capacity. A tenfold algorithmic fix beats ten more servers.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Little's law | `L = λ × W`: average items in the system equals arrival rate times average time in system. 200 req/s at 0.25 s means about 50 requests in flight, which sizes thread pools, connection pools and queues |
| Utilization | `U = λ × S` (arrival rate times service time). In a single-server queue, response time grows like `S / (1 - U)`: at 50% busy the wait is about S, at 90% about 9S. Plan steady state at 60-70% for latency-sensitive paths |
| Amdahl / USL | Amdahl: speedup `1 / ((1 - p) + p / N)` is capped by the serial fraction. Universal Scalability Law: `C(N) = N / (1 + α(N-1) + βN(N-1))`, with contention α and coherency (crosstalk) β; β makes throughput fall past a peak |
| USE method | For every resource (CPU, memory, disk, network, pools): Utilization, Saturation, Errors |
| RED method | For every service: Rate, Errors, Duration (histograms, not averages). Google's four golden signals add saturation: latency, traffic, errors, saturation |
| Percentiles | Report p50, p95, p99, p99.9 from histograms; never average percentiles across instances; merge histograms instead |
| Tail at scale | A request that fans out to N backends sees a slow one often: with a 1% slow rate per backend, 100 calls give `1 - 0.99^100 ≈ 63%` slow requests |
| Open vs closed load | Closed model (fixed virtual users) slows down when the system slows, hiding overload and coordinated omission. Open model (fixed arrival rate) is the honest model for public services |
| Autoscaling | HPA: `desired = ceil(current × currentMetric / targetMetric)`, with tolerance (default 10%) and stabilization windows; KEDA scales on events (queue length, lag, cron) and can scale to zero |
| Data scaling | In order: query and index fixes, pooling, caching, read replicas, partitioning, sharding. Each step adds consistency and operational cost |
| Caching | Cache-aside is the default; invalidation by TTL, explicit delete, or events; protect against stampedes with single-flight, jittered TTLs, stale-while-revalidate |
| Backpressure | Bounded queues, concurrency limits, timeouts with deadlines, retry budgets with jitter, load shedding with 429/503 and `Retry-After` |

## 3. Workflow

1. State the goal as a number with a unit and a percentile: "p99 under 300 ms at 2,000 req/s with 1% errors at most", plus the cost ceiling.
2. Establish a baseline in a production-like environment: build, config, data volume, dependencies. Record throughput, latency histograms, error rate, and resource usage per component.
3. Locate the bottleneck with USE on resources and RED on services, then profile the saturated component (CPU, allocation, locks, I/O wait). Reference: [references/performance-optimization.md](references/performance-optimization.md).
4. Form one hypothesis, change one thing, re-measure under the same load. Keep or revert based on numbers.
5. Fix in this order: avoid the work, make the work cheaper (algorithm, query, serialization), cache, parallelize or batch, then add capacity.
6. Model capacity from measurements: per-instance max throughput at the latency goal, headroom for failure of one zone, growth forecast. Reference: [references/autoscaling-capacity.md](references/autoscaling-capacity.md).
7. Load test the change and the system limits (load, stress, spike, soak). Reference: [references/load-testing.md](references/load-testing.md).
8. Add autoscaling, rate limits and backpressure so overload degrades gracefully; define SLOs and alerts.
9. Record results and the remaining ceiling; repeat when traffic or architecture changes.

## 4. Decision Rules

- Do not optimize without a measurement showing where the time goes. Profile before touching code; benchmark before and after.
- A slow query, N+1 pattern, or missing index is fixed before adding replicas or caches.
- Cache only when the read-to-write ratio and tolerance for staleness justify it, and when hit ratio can be measured. Define the invalidation rule before the cache.
- Prefer stateless services behind a load balancer so scale-out is cloning; move session state to a shared store or to signed tokens.
- Use asynchronous processing (queues) when work can complete after the response, when load is spiky, or when downstream capacity is lower than the peak arrival rate.
- Add read replicas for read-heavy workloads that tolerate replication lag; partition large tables for maintenance and pruning; shard only when a single primary cannot handle writes or data size even after tuning.
- Choose the shard key for even distribution and for keeping common transactions within one shard; avoid designs that need cross-shard joins on hot paths.
- Autoscale on a metric that tracks load per instance (requests in flight, queue lag, CPU for CPU-bound work); not on a lagging or noisy proxy.
- Set timeouts everywhere, shorter at each deeper layer; retry only idempotent calls, with exponential backoff, jitter and a retry budget.
- Pay for latency or throughput only where users or the business value it: tier SLOs by endpoint.

## 5. Coding Standards

- Every network call has a timeout and a cancellation path; propagate a deadline from the edge down.
- Every queue, buffer, pool and cache has a bound; every unbounded collection fed by external input is a defect.
- Use streaming and pagination for large results; do not materialize whole result sets.
- Make hot paths allocation-light: reuse buffers, avoid per-request regex compilation and repeated parsing, avoid needless serialization round trips.
- Batch small operations (bulk insert, multi-get, pipelining) instead of one call per item.
- Keep handlers idempotent so retries and at-least-once queues are safe.
- Emit metrics with bounded label cardinality (route template, not raw URL; no user ids).
- Make configuration of pool sizes, timeouts, and concurrency limits explicit and environment-specific, not defaults copied from examples.

## 6. Project Structure

```
.
├── load/
│   ├── smoke.js              # 1 VU, correctness under the test harness
│   ├── load.js               # expected peak, open model
│   ├── stress.js             # beyond peak to find the knee and failure mode
│   ├── soak.js               # hours at normal load for leaks and drift
│   ├── lib/                  # shared helpers, data loaders
│   └── data/                 # anonymized test data (never production PII)
├── perf/
│   ├── baselines/            # recorded results per release (json/csv)
│   └── profiles/             # saved flame graphs and pprof files for comparison
├── deploy/
│   ├── hpa.yaml              # HorizontalPodAutoscaler
│   └── keda-scaledobject.yaml
└── docs/
    ├── slo.md                # targets by endpoint, error budgets
    └── capacity.md           # model, assumptions, headroom, forecast
```

## 7. Design Patterns

- **Cache-aside with single-flight**: check the cache, on miss one caller loads while others wait on the same promise; TTL with jitter; optional stale-on-error.
- **Read replicas with read-your-writes**: route a user's reads to the primary for a short window after a write, or pass a replication position token.
- **Partitioning and sharding**: range or hash partitions inside one database for pruning and maintenance; hash or directory-based shards across databases for write scale.
- **Queue-based load leveling**: a durable queue between a bursty producer and a worker pool sized for average load; scale workers by queue lag.
- **Bulkhead**: separate pools per dependency or tenant class so one slow dependency cannot exhaust all threads.
- **Circuit breaker, timeout, retry budget**: fail fast when a dependency is down; retries limited to a small fraction of traffic.
- **Hedged requests**: for idempotent reads with a heavy tail, send a second request to another replica after a delay near the p95 and use the first answer; cancel the loser.
- **Load shedding and priority**: reject low-priority work early (429/503) when queue delay or concurrency passes a limit.
- **CDN and edge caching**: cache static assets and cacheable API responses by URL; purge by tag or key; use an origin shield to protect the origin.
- **Precompute and materialize**: compute expensive aggregates in background and serve from a table or cache.
- Deep dives: [references/data-scaling.md](references/data-scaling.md) for databases, caches, queues and CDN.

## 8. Best Practices

- Define SLOs per endpoint and watch error-budget burn; use them to decide between performance work and features.
- Keep a performance budget in CI: a smoke-scale load test with thresholds that fail the build on regressions.
- Look at distributions: histograms with exemplars link a slow bucket to a trace.
- Profile in production with low-overhead continuous profiling where available; compare profiles between releases.
- Right-size resource requests and limits from measured usage; keep headroom for zone loss and deploys.
- Test failure modes along with capacity: kill an instance during load, slow a dependency, fill a queue.
- Keep a runbook of the top three bottlenecks and their known mitigations.
- Re-run capacity tests after major dependency, runtime or schema changes.

## 9. Performance

Quick wins to look for, in rough order of payoff:

- Queries: missing indexes, N+1, `SELECT *`, unbounded `OFFSET` pagination (use keyset pagination), long transactions, lock waits.
- Serialization and payload size: compress responses (gzip or Brotli at the proxy), trim fields, use binary formats on internal hot paths where measured.
- Connection management: reuse HTTP and database connections (keep-alive, pools), avoid per-request TLS handshakes to dependencies.
- Concurrency: parallelize independent calls; avoid blocking the event loop or request thread; size pools using Little's law.
- Memory and GC: reduce allocation rate before tuning the collector; watch heap growth and pause times.
- Algorithmic complexity: replace quadratic scans with indexed or hashed lookups.
- Caching at the right layer: HTTP caching and CDN first for public data, application cache for computed data, database cache is automatic.
- Details and per-runtime tools: [references/performance-optimization.md](references/performance-optimization.md).

## 10. Security

- Rate limiting and quotas are security controls as well as capacity controls: limit per user, per IP and per API key; return 429 with `Retry-After`; keep limiter state in a shared store when running several instances.
- Load tests must not hit production with real customer data or third-party systems without agreement; use synthetic, anonymized data and dedicated test tenants.
- Never put credentials in test scripts or CI logs; read them from environment variables or the CI secret store.
- Caches can leak data across users: include tenant, user or authorization context in the cache key for personalized content, and mark private responses `Cache-Control: private` or `no-store`.
- Unbounded work from untrusted input (large bodies, deep JSON, regex backtracking, expensive queries) is a denial-of-service vector; cap sizes, depth, page size and query cost.
- Autoscaling can be abused to run up cost; set maximum replicas and budget alerts.
- Profilers and debug endpoints (pprof, heap dumps) expose internals; bind to localhost or protect with authentication.

## 11. Testing

- Smoke test: one virtual user checks the scripts and the system before every larger run.
- Load test: expected peak at a steady arrival rate; verify SLO thresholds.
- Stress test: ramp past peak to find the knee, the saturation point and the failure mode (graceful rejection versus collapse).
- Spike test: sudden jump (for example 10x within seconds) to check autoscaling lag and queue behavior.
- Soak test: hours to days at normal load for leaks, connection exhaustion, log growth and drift.
- Use an open workload model (arrival-rate executors) for services receiving independent requests; use closed models only for fixed-concurrency clients.
- Keep the test environment representative: same instance types, data volume and indexes, realistic think time and data skew; check the load generator itself is not the bottleneck.
- Tests that count: thresholds on p95/p99 latency and error rate, and automatic abort on failure.
- Reference: [references/load-testing.md](references/load-testing.md).

## 12. Review Checklist

- [ ] A numeric goal exists (percentile, rate, error budget, cost).
- [ ] Bottleneck evidence: profile, trace or metric, not intuition.
- [ ] Every pool, queue, cache and retry has a bound, a timeout and a metric.
- [ ] N+1, unbounded queries and missing indexes are checked on new endpoints.
- [ ] Cache has an invalidation rule, a stampede guard, and a tenant-safe key.
- [ ] Idempotency exists for retried and queued operations.
- [ ] Autoscaling metric, min/max, stabilization and headroom are defined and tested.
- [ ] Overload behavior is defined (shed, queue, degrade) and tested.
- [ ] Load test uses an open model, realistic data, thresholds and a baseline comparison.
- [ ] Cost impact is estimated (instances, storage, egress, cache memory).

## 13. Production Notes

- Keep 30-40% headroom on latency-critical tiers so a zone failure or deploy does not push utilization past the knee. Compute N+1 capacity: after losing one zone, remaining zones must carry peak.
- Scale-out lag matters: image pull, startup, warm-up of caches and JIT, and readiness checks add minutes. Set `minReplicas` for the predictable base, use scheduled or predictive scaling for known peaks, and pre-warm.
- Roll out performance changes behind flags and compare real traffic with canary metrics.
- During incidents prefer reversible mitigations first: shed load, raise cache TTLs, disable expensive features, add replicas, roll back.
- Database changes (new index, partitioning, resharding) need their own rehearsal on production-sized data and a rollback path.
- Watch saturation signals that are easy to miss: connection pool wait time, file descriptors, ephemeral ports, thread pool queue depth, disk IOPS and burst credits, cloud API rate limits, DNS.
- Cost view: track cost per request or per tenant next to latency; scaling out is not free and caches have memory cost.
- Review capacity quarterly and before launches and campaigns.

## 14. Examples

k6 open-model load test with thresholds (TypeScript also runs natively in current k6; this is plain JavaScript). The arrival rate stays fixed even when the service slows, so overload shows up in latency and errors:

```js
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    api_peak: {
      executor: "ramping-arrival-rate",
      startRate: 50,
      timeUnit: "1s",
      preAllocatedVUs: 200,
      maxVUs: 1000,
      stages: [
        { target: 500, duration: "2m" }, // ramp to expected peak
        { target: 500, duration: "10m" }, // hold
        { target: 0, duration: "1m" },
      ],
    },
  },
  thresholds: {
    http_req_failed: [{ threshold: "rate<0.01", abortOnFail: true }],
    http_req_duration: ["p(95)<300", "p(99)<800"],
    dropped_iterations: ["count==0"], // generator or VU limit reached means the result is invalid
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8080";

export default function () {
  const res = http.get(`${BASE}/api/products?limit=20`, { tags: { route: "/api/products" } });
  check(res, { "status is 200": (r) => r.status === 200 });
}
```

Run with `k6 run -e BASE_URL=https://staging.example.com load/load.js`. A rising `dropped_iterations` count means the load generator ran out of VUs, so raise `maxVUs` or distribute the generator.

KEDA ScaledObject scaling a worker Deployment on Kafka consumer lag, with HPA behavior tuned for slow scale-down. Replicas never exceed the partition count unless `allowIdleConsumers` is set:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: invoice-worker
spec:
  scaleTargetRef:
    name: invoice-worker
  pollingInterval: 15
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 24
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
            - type: Percent
              value: 25
              periodSeconds: 60
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka.messaging.svc:9092
        consumerGroup: invoice-workers
        topic: invoices
        lagThreshold: "100"
```

Cache-aside with single-flight and jittered TTL (in-process coalescing; add a distributed lock only if the load on the origin from many instances is still too high):

```ts
export interface Cache {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
}

export class SingleFlightCache<T> {
  private readonly inflight = new Map<string, Promise<T>>();

  constructor(
    private readonly cache: Cache,
    private readonly ttlSeconds: number,
    private readonly jitterRatio = 0.1,
  ) {}

  async get(key: string, load: () => Promise<T>): Promise<T> {
    try {
      const hit = await this.cache.get(key);
      if (hit !== null) return JSON.parse(hit) as T;
    } catch {
      // cache outage: fall through to the origin instead of failing the request
    }
    const pending = this.inflight.get(key);
    if (pending) return pending;

    const p = (async () => {
      try {
        const value = await load();
        const jitter = 1 + (Math.random() * 2 - 1) * this.jitterRatio;
        const ttl = Math.max(1, Math.round(this.ttlSeconds * jitter));
        await this.cache.set(key, JSON.stringify(value), ttl).catch(() => undefined);
        return value;
      } finally {
        this.inflight.delete(key);
      }
    })();
    this.inflight.set(key, p);
    return p;
  }
}
```

## 15. Common Mistakes

- **Optimizing by intuition**: changing code without a profile. Measure, then change one thing.
- **Averages instead of percentiles**: a good mean hides a bad p99. Use histograms.
- **Averaging percentiles across instances**: mathematically meaningless; merge histograms.
- **Closed-model load tests only**: the generator slows down with the system (coordinated omission) and the test reports good latency during collapse.
- **Load testing a different system**: tiny database, no indexes, warm caches only, or the generator on the same host.
- **Scaling out a stateful or serialized bottleneck**: more app servers against one saturated database or lock only add contention.
- **Unbounded retries**: retry storms multiply load on a struggling dependency. Use budgets, backoff and jitter.
- **No timeout, or the same timeout at every layer**: callers time out before callees, leaving orphaned work. Shorten deeper timeouts.
- **Cache with no invalidation story or stampede protection**: stale data and thundering herds on expiry.
- **Caching personalized data under a shared key**: leaks one user's data to another.
- **Autoscaling on CPU for an I/O-bound or queue-driven service**: it reacts late or never; scale on in-flight requests or lag.
- **Sharding too early**: it removes joins and transactions for a problem that an index or a replica would have solved.
- **Hot shard keys** (monotonic ids, tenant with 50% of traffic): spread writes with hashing or key salting and watch per-shard load.
- **Ignoring pool sizes**: more app instances multiply database connections; use a pooler and cap per-instance pools.
- **Premature micro-optimization** of code that is not on the critical path, at the cost of readability.

## 16. References

- [references/performance-optimization.md](references/performance-optimization.md): the former performance-optimization-expert skill: methodology, USE/RED analysis, profiling by runtime, flame graphs, common bottlenecks, concurrency and memory tuning, benchmarking pitfalls.
- [references/load-testing.md](references/load-testing.md): workload models, k6 scenarios and thresholds, Locust and Gatling, test data, CI use, reading results, capacity from test results.
- [references/data-scaling.md](references/data-scaling.md): caching layers and invalidation, database pooling, replicas, partitioning, sharding, queues and backpressure, CDN, rate limiting.
- [references/autoscaling-capacity.md](references/autoscaling-capacity.md): capacity planning math, HPA and KEDA configuration, headroom, tail latency, hedging, cost and performance trade-offs.
- Official docs: https://grafana.com/docs/k6/latest/ , https://docs.locust.io/ , https://docs.gatling.io/ , https://keda.sh/docs/ , https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ , https://www.pgbouncer.org/config.html
