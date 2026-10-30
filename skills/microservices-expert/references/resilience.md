# Resilience

Reference for keeping a call graph of services healthy when dependencies are slow or failing: deadlines, retries with backoff and jitter, retry budgets, circuit breakers, bulkheads, load shedding, fallbacks, health checks, service discovery and graceful shutdown. Verified against `opossum` 10.0.0 (Node.js 22+; options `timeout`, `errorThresholdPercentage`, `volumeThreshold`, `resetTimeout`, `capacity`, `errorFilter`), gRPC retry service-config semantics and Kubernetes probe semantics (2026-10). Concepts apply to any language; JVM and .NET ecosystems have equivalents (Resilience4j, Polly).

## 1. Deadlines and timeouts

- Every network call has a timeout, including database and cache calls. The default of many HTTP clients is "wait forever".
- Think in deadlines, not timeouts. The request enters with a total budget (for example 2 seconds); each hop subtracts elapsed time and passes the remainder. gRPC propagates deadlines natively; for HTTP, pass the remaining budget in a header agreed by your services and enforce it with `AbortSignal.timeout()` or the client equivalent.
- A downstream timeout must be shorter than the caller's. If the caller waits 1 s and the callee works for 3 s, the work is wasted and the load keeps coming.
- Separate connect timeout from request timeout where the client supports it; connection failures are cheap to detect.
- Cancel work when the caller goes away: pass the abort signal into database queries and downstream calls so abandoned requests release resources.

## 2. Retries

Retry when all of these hold:

1. The failure is transient: connection reset, timeout, `429`, `502`, `503`, `504`, or a gRPC `UNAVAILABLE`. Do not retry `400`, `401`, `403`, `404`, `409`, `422` or validation errors.
2. The operation is idempotent (GET, PUT, DELETE, or a POST protected by an idempotency key stored by the receiver).
3. Time is left in the deadline.
4. No other layer already retries the same call.

Backoff with jitter. Plain exponential backoff synchronizes clients and creates waves. Full jitter spreads them:

```
sleep = random(0, min(cap, base * 2^attempt))
```

Typical values: base 100 ms, cap 1-5 s, 2-3 attempts for user-facing calls, more for background jobs. Honor `Retry-After` when the server sends it (use the larger of the two values).

Retry budgets and throttling. Fixed attempt counts still amplify load during an outage: a service whose dependency fails at 100% sends `attempts` times the traffic. Limit retries to a fraction of normal traffic (for example retries may add at most 10% extra requests per client) or use a token bucket that refills on success. gRPC offers `retryPolicy` (`maxAttempts`, `initialBackoff`, `maxBackoff`, `backoffMultiplier`, `retryableStatusCodes`) and `retryThrottling` (`maxTokens`, `tokenRatio`) in the service config; `maxAttempts` is capped at 5.

Hedged requests (send a second request after a latency percentile) reduce tail latency for idempotent reads at the cost of extra load; use only with a budget.

Where to retry. Pick one layer: the client library, the service mesh, or the gateway. Retries at the edge, in each service and in the mesh multiply: three layers with three attempts each is up to 27 calls for one user request.

## 3. Circuit breaker

States:

- **Closed**: calls pass; failures are counted in a rolling window.
- **Open**: calls fail immediately without touching the dependency, for `resetTimeout`. This sheds load and gives the dependency room to recover.
- **Half-open**: after the timeout, a limited number of probe calls are allowed; success closes the breaker, failure reopens it.

Configuration guidance:

- Trip on error rate over a minimum volume (`volumeThreshold`), not on a single failure. Count timeouts and `5xx`; do not count client errors (`4xx` other than `429`) as dependency failures.
- Per dependency (and per route when routes have different failure modes), not one global breaker.
- Treat an open breaker as non-retryable inside the retry loop; retrying into an open breaker only adds latency.
- Expose breaker state as a metric and log state changes. An open breaker is a user-visible degradation and must alert.
- With a fallback, decide what the user sees: cached data, a default, a reduced feature, or an explicit error. A fallback that calls another unreliable dependency is a new failure path.

```ts
import CircuitBreaker from "opossum";

const breaker = new CircuitBreaker(callPricing, {
  timeout: 800,                   // per-call timeout in ms
  errorThresholdPercentage: 50,   // open when 50% of calls in the window fail
  volumeThreshold: 20,            // ... but only after 20 calls
  resetTimeout: 10_000,           // try half-open after 10 s
  capacity: 50,                   // concurrent calls allowed
});
breaker.fallback(() => ({ price: null, source: "unavailable" }));
breaker.on("open", () => logger.warn({ dependency: "pricing" }, "circuit open"));
breaker.on("halfOpen", () => logger.info({ dependency: "pricing" }, "circuit half-open"));
breaker.on("close", () => logger.info({ dependency: "pricing" }, "circuit closed"));
```

## 4. Bulkheads

Isolate resources so one slow dependency cannot exhaust everything.

- Separate connection pools and concurrency limits per downstream. With `opossum`, the `capacity` option limits concurrent executions of the wrapped function; excess calls are rejected with code `ESEMLOCKED`.
- Separate worker pools or queues for different workloads (interactive versus batch, tenants of different tiers).
- Per-tenant limits prevent one tenant from consuming all capacity: a per-tenant concurrency cap and rate limit, keyed by the verified tenant id.
- At the infrastructure level, set CPU and memory limits per service and separate node pools for critical services.

## 5. Load shedding and rate limiting

- Rate limit at the edge by client identity and tenant; respond `429` with `Retry-After`.
- Inside a service, bound the in-flight request count and queue length; when the limit is reached, reject quickly with `503` (or gRPC `RESOURCE_EXHAUSTED`) rather than queueing without bound. A short fast failure is better than a long slow one.
- Prioritize: drop low-priority work (analytics, prefetch, background sync) before user-facing requests.
- Autoscaling reacts in minutes; shedding and breakers act in milliseconds. Use both.
- Consumers: bound concurrency per partition and pause consumption when downstream is unhealthy rather than failing every message into the DLQ.

## 6. Fallbacks and graceful degradation

- Define per dependency whether it is critical (fail the request) or optional (degrade). Document it in the service README so on-call knows the expected behavior.
- Common fallbacks: serve stale cached data with a visible age, return a default, skip the personalization, queue the action for later (accept and process asynchronously).
- Mark degraded responses explicitly in the payload or headers so clients do not treat defaults as truth.
- Test every fallback regularly; an untested fallback often fails when first needed.

## 7. Health checks and service discovery

- Liveness answers "should the process be restarted"; keep it cheap and independent of dependencies, otherwise a dependency outage restarts every pod and makes things worse.
- Readiness answers "should this instance receive traffic": true once initialized and able to serve. Include only local readiness and critical hard dependencies; failing readiness on a shared optional dependency removes all instances at once.
- Startup probes protect slow-starting applications from being killed by liveness checks.
- Discovery: prefer the platform (Kubernetes Service DNS and kube-proxy or a mesh). Clients should re-resolve DNS and not cache addresses forever. Client-side load balancing (gRPC with a headless service, or a mesh sidecar) is needed when connections are long-lived and multiplexed, since connection-level balancing would pin all requests to one pod.
- Use deployment strategies with readiness gates (rolling, canary) and a pod disruption budget so discovery never points at zero healthy instances during upgrades.

## 8. Graceful shutdown

- On `SIGTERM`: fail readiness first, stop accepting new work, finish in-flight requests within a bounded time, close consumers (commit offsets), flush telemetry, then exit. Make the termination grace period longer than the drain time.
- Allow time for load balancers to stop sending traffic (a short pre-stop delay) so requests do not hit a closing instance.
- Messages in flight at shutdown are redelivered; consumers must be idempotent.

## 9. Library or mesh

- A service mesh gives uniform timeouts, retries, mTLS and traffic shifting without code changes, but applies the same policy to all calls and cannot know which operations are idempotent. Use mesh retries only for routes you have marked safe.
- Library policies are per call site and can use application knowledge (idempotency keys, domain-specific fallbacks).
- Whichever is chosen, document ownership of retries and timeouts per call path so layers do not stack.
