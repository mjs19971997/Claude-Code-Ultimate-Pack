# Autoscaling and Capacity

Reference for capacity planning, Kubernetes HorizontalPodAutoscaler and KEDA configuration, tail latency controls (timeouts, retries, hedging) and cost/performance trade-offs. Verified against Kubernetes 1.37 (HPA `autoscaling/v2`: scaling formula, behavior, tolerance), KEDA 2.21 (`ScaledObject` spec, kafka, cron, prometheus and aws-sqs-queue scalers) and TypeScript 7.0 with `strict` (blocks marked `// file:` were type-checked) (2026-10).

## 1. Capacity planning method

1. Forecast demand: peak requests per second, daily and weekly shape, growth rate, events (campaigns, launches, month-end), and read/write mix. Use the peak of a representative period, not the mean.
2. Measure supply: from load tests, the maximum sustainable throughput per instance at the latency goal (stay below the knee), plus the resource that saturates first (CPU, memory, connections, IOPS).
3. Add headroom: failure of a zone or node, deploys (rolling updates reduce capacity), growth buffer, and autoscaling lag.
4. Compute instances, then check the shared dependencies (database, cache, queue, third-party limits) against the same peak; the weakest tier sets the ceiling.
5. Validate with a load test at forecast peak plus margin, then repeat on a schedule.

Worked example. Peak forecast 3,000 requests/s; add 25% growth buffer: 3,750 requests/s. A load test shows one pod sustains 250 requests/s at p99 under 300 ms (about 65% CPU). Three zones must survive the loss of one zone, so two thirds of the pods must carry the whole peak:

- pods needed = 3,750 / (250 × 2/3) = 22.5, rounded up to 24 (8 per zone).
- Normal utilization of tested capacity = 3,000 / (24 × 250) = 50%.
- Concurrency per pod by Little's law at 0.2 s average latency: 250 × 0.2 = 50 requests in flight. Set worker threads, event-loop limits and downstream pool sizes accordingly.
- Database connections: 24 pods × pool of 10 = 240 connections; with a pooler in front, server-side connections stay in the tens.

## 2. Queueing intuition

- Response time rises sharply with utilization: in a simple single-server queue it behaves like `service time / (1 - utilization)`. Real systems have variance and bursts, so keep latency-sensitive tiers around 50-70% utilization at peak.
- Variability matters as much as the average: bursty arrivals and long-tail service times need more headroom.
- Multiple servers behind one queue (a shared work queue) handle variance better than separate queues per server.
- The Universal Scalability Law `C(N) = N / (1 + α(N-1) + βN(N-1))` fits throughput against concurrency or node count from several measurements; a fitted β greater than zero predicts a peak beyond which adding nodes reduces throughput, usually from coordination (locks, consensus, cache coherence, chatty protocols).
- Amdahl's law: if 5% of the work is serial, the maximum speedup is 20x however many processors are added. Find the serial part (a lock, a single primary, a leader) and shrink or shard it.

## 3. HorizontalPodAutoscaler

The HPA controller computes `desiredReplicas = ceil(currentReplicas × currentMetricValue / desiredMetricValue)`. It skips changes when the ratio is within a tolerance (10% by default) and uses stabilization windows and policies to avoid flapping. Metric types: `Resource` (CPU, memory), `ContainerResource` (per container), `Pods` (custom per-pod metric), `Object`, and `External` (custom and external metrics need a metrics adapter, such as KEDA or Prometheus Adapter).

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 6
  maxReplicas: 40
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      selectPolicy: Max
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

Practices:

- `Utilization` targets are relative to the container's resource requests, so requests must be set realistically.
- Pick a metric proportional to load per pod. CPU works for CPU-bound services; for I/O-bound services, scale on requests per pod, in-flight requests, or queue lag.
- Set `minReplicas` to cover the predictable base and the zone-loss case, not to 1.
- Readiness probes and startup time determine real scale-out lag. Add `startupProbe` for slow starts and keep images small.
- Scale up fast and scale down slowly (stabilization window of 5-10 minutes) to avoid oscillation.
- Combine with a PodDisruptionBudget and topology spread constraints so zone loss and node drains do not remove too much capacity at once.
- The cluster must have room: use Cluster Autoscaler or Karpenter (or equivalent) with headroom pods or overprovisioning for the fastest scale-out; node provisioning often takes longer than pod scaling.
- Do not run an HPA and a KEDA ScaledObject against the same workload; KEDA creates and manages its own HPA.
- Vertical autoscaling (VPA) is useful for right-sizing requests in recommendation mode; do not let it fight an HPA on the same CPU or memory metric.

## 4. KEDA

KEDA scales workloads from event sources and can scale to zero. A `ScaledObject` references the target (`scaleTargetRef`), polls triggers (`pollingInterval`, default 30 s), applies `cooldownPeriod` (default 300 s) before scaling to zero, honors `minReplicaCount` and `maxReplicaCount`, and can set a `fallback` replica count when a trigger source fails. Under the hood it manages an HPA, and `advanced.horizontalPodAutoscalerConfig.behavior` customizes scaling behavior.

Cron plus Prometheus triggers: a scheduled floor for a known daily peak, and a request-rate trigger above it (KEDA scales to the highest result across triggers):

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: api
spec:
  scaleTargetRef:
    name: api
  minReplicaCount: 6
  maxReplicaCount: 40
  fallback:
    failureThreshold: 3
    replicas: 12
  triggers:
    - type: cron
      metadata:
        timezone: Europe/Berlin
        start: 0 8 * * 1-5
        end: 0 19 * * 1-5
        desiredReplicas: "16"
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(rate(http_requests_total{service="api"}[2m]))
        threshold: "200"
```

Notes:

- For a queue worker, scale on lag or length: the Kafka scaler (`lagThreshold`) or the AWS SQS scaler (`queueURL`, `queueLength`, `awsRegion`). Replicas are capped by partition count for Kafka unless `allowIdleConsumers` is set. Authentication for scalers uses `TriggerAuthentication` or workload identity; do not put credentials in trigger metadata.
- The `threshold` is the target per replica: the metric value divided by threshold gives the replica count (rounded up).
- Use `ScaledJob` for batch work where each message should run as its own Job.
- Test activation thresholds (`activationLagThreshold`, `activationQueueLength`) so scaling from zero happens at the intended backlog.
- Scale-from-zero adds cold-start latency; keep `minReplicaCount` at 1 or more for latency-sensitive HTTP services.

## 5. Scaling schedules and warm-up

- Known peaks (business hours, campaigns, batch windows): scheduled scaling (KEDA cron or the platform's scheduler) before the peak; reactive scaling alone arrives late.
- Warm-up: new instances need caches, JIT warm-up, connection pools and TLS sessions before taking full traffic. Use slow start in load balancers where available, and readiness gates that include warm-up.
- Deploy strategy: rolling update with `maxSurge` so capacity does not dip; avoid deploying at peak.
- Game days: practice losing a zone and scaling up from a cold state at least once per quarter.

## 6. Timeouts, retries and deadlines

Principles for tail latency:

- Propagate a deadline from the edge. Each hop uses the remaining budget minus a margin, so inner calls time out before outer ones.
- Retry only idempotent operations, a small number of times, with exponential backoff and full jitter. Limit total retry volume with a retry budget (for example retries may add at most about 10% extra requests) so outages do not trigger storms. Do not retry on client errors.
- Add circuit breaking and bulkheads so one slow dependency does not exhaust shared pools.

Retry with full jitter:

```ts
// file: retry.ts
export interface RetryOptions {
  readonly attempts: number;
  readonly baseMs: number;
  readonly capMs: number;
  readonly isRetryable: (error: unknown) => boolean;
}

export async function retry<T>(fn: (attempt: number) => Promise<T>, opts: RetryOptions): Promise<T> {
  for (let attempt = 1; ; attempt++) {
    try {
      return await fn(attempt);
    } catch (error) {
      if (attempt >= opts.attempts || !opts.isRetryable(error)) throw error;
      const ceiling = Math.min(opts.capMs, opts.baseMs * 2 ** (attempt - 1));
      await new Promise<void>((resolve) => setTimeout(resolve, Math.random() * ceiling));
    }
  }
}
```

## 7. Hedged requests

When a read has a heavy tail and is idempotent, send the request to one replica and, if no answer arrives within a delay near the p95 latency, send a second request to another replica; use the first answer and cancel the other. This trims the tail at the cost of a few percent extra load (about 5% when the delay equals the p95). Limit hedging to safe, cheap reads, never to non-idempotent writes, and make sure replicas are independent (different hosts or zones).

```ts
// file: hedged.ts
export function hedged<T>(call: (signal: AbortSignal) => Promise<T>, hedgeAfterMs: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const controllers: AbortController[] = [];
    let pending = 0;
    let settled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const launch = (): void => {
      const ac = new AbortController();
      controllers.push(ac);
      pending++;
      call(ac.signal).then(
        (value) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          for (const c of controllers) if (c !== ac) c.abort();
          resolve(value);
        },
        (error: unknown) => {
          pending--;
          if (settled) return;
          if (controllers.length === 1) {
            // First attempt failed before the hedge fired: start the second one now.
            clearTimeout(timer);
            launch();
          } else if (pending === 0) {
            settled = true;
            reject(error);
          }
        },
      );
    };

    launch();
    timer = setTimeout(() => {
      if (!settled && controllers.length === 1) launch();
    }, hedgeAfterMs);
  });
}
```

Related tail techniques: tied requests (send to two replicas and cancel on first start), micro-partitions so load balances finely, canary or shadow replicas for slow nodes, and ejecting slow instances from the load balancer (outlier detection).

Fan-out math: if each of N parallel calls is slow with probability p, the request is slow with probability `1 - (1 - p)^N`. With p = 1% and N = 100 it is about 63%. Reduce N, set tight per-call timeouts with partial results, or hedge.

## 8. Load shedding and degradation

- Shed early and cheaply: reject at the edge when queue delay or concurrency exceeds a limit, with `503` or `429` and `Retry-After`. Prioritize by request class (health checks, authenticated writes, anonymous reads).
- Degrade features before failing: serve cached or stale data, skip personalization or recommendations, disable expensive search facets.
- Use adaptive concurrency limits (limit grows when latency is stable and shrinks when it rises) for services with variable cost per request.
- Make sure autoscaling and shedding work together: shedding protects the system during the minutes it takes to scale out.

## 9. Cost and performance trade-offs

| Lever | Performance effect | Cost effect |
|---|---|---|
| Run at higher utilization | Higher latency and less failure headroom | Lower cost per request |
| Add caches (memory) | Large latency and origin-load reduction | Memory cost, invalidation complexity |
| Add read replicas | Read capacity | Linear instance cost, replication lag |
| Reserved or committed capacity for baseline, on-demand or spot for burst | Same | Often 30-60% lower for steady base load (check current provider pricing) |
| Spot or preemptible instances for stateless workers | Interruptions need graceful handling | Large discount |
| Smaller images, faster startup | Faster scale-out | Less overprovisioning |
| Right-size requests from measured usage | Fewer throttles and fewer idle resources | Lower node count |
| ARM-based instances (where the stack supports them) | Often better price/performance | Lower cost; test first |
| Compression and CDN offload | Lower latency and egress | Lower egress, origin and instance cost |
| Tiered storage and retention limits for logs, metrics, events | Faster queries on hot data | Large storage savings |
| Autoscale to zero for idle environments | Cold start delay | Pays only for use |

Track unit economics: cost per thousand requests, per tenant, per transaction, next to latency and error rate. Set budgets and alerts, cap `maxReplicas`, and review the top cost drivers monthly. Optimize only the components that dominate the bill after measuring.

## 10. Capacity document

Keep a short, versioned document next to the code:

- Demand model and forecast with sources and date.
- Per-component capacity numbers with the test run that produced them.
- Headroom policy (zone loss, growth buffer, deploys).
- Scaling rules (min/max, metrics, schedules) and the reasons.
- Known ceilings and the next scaling step for each (for example "primary database write rate: shard by tenant before 8k writes/s").
- Review date and owner.
