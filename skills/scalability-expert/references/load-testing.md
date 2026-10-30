# Load Testing

Reference for designing, running and interpreting load tests with k6, Locust and Gatling. Verified against k6 2.3.0 (scenarios, executors, thresholds, `--scenario`, `--once`, outputs), Locust 2.47.0 and the Gatling 3.15 Java DSL (class and method names checked against the published artifacts) (2026-10). The k6 and Locust examples were loaded and parsed with those versions; the k6 script ran against a closed local port to check options and thresholds.

## 1. Test types

| Type | Question answered | Shape |
|---|---|---|
| Smoke | Does the script and the system work at all? | 1 virtual user, short; also usable with `--once` for a single iteration |
| Load | Does it meet the SLO at expected peak? | Ramp to peak, hold 10-30 min |
| Stress | Where is the knee, and how does it fail? | Ramp beyond peak in steps until errors or latency break the SLO |
| Spike | Does it survive sudden surges and recover? | Jump to several times normal within seconds, then back |
| Soak | Does it stay healthy over hours? | Normal load for 4-24 h, watch memory, connections, disk, latency drift |
| Breakpoint | What is the maximum capacity? | Continuously increasing arrival rate until a threshold aborts the run |

Run in a production-like environment: same instance types, data volume, indexes, configuration and dependencies (or realistic stubs with realistic latency). Seed data with realistic skew; an empty database makes every query fast.

## 2. Workload models

- Closed model: a fixed number of virtual users, each sends the next request after the previous finishes (plus think time). When the system slows, arrival rate drops, which hides overload and understates latency (coordinated omission). Fits systems with a fixed number of clients (internal batch consumers, a few devices).
- Open model: requests arrive at a target rate regardless of response time, as with independent public users. If the system cannot keep up, in-flight requests pile up and latency grows, as in production. Use this for public APIs and websites.
- In k6: open model is `constant-arrival-rate` or `ramping-arrival-rate`; closed is `constant-vus` or `ramping-vus`. In Gatling: `injectOpen` versus `injectClosed`. In Locust: users with `wait_time` are closed by default; use `constant_throughput` or a custom `LoadTestShape` for rate control.
- Size the generator: arrival rate × expected latency gives needed in-flight VUs (Little's law); set `preAllocatedVUs` and `maxVUs` above that with margin and treat `dropped_iterations` as a sign that the test did not deliver the planned load.
- Add think time and realistic mix: ratio of read to write endpoints, search versus detail, authenticated versus anonymous.

## 3. k6

Executors (`options.scenarios.<name>.executor`): `shared-iterations`, `per-vu-iterations`, `constant-vus`, `ramping-vus`, `constant-arrival-rate`, `ramping-arrival-rate`. The `externally-controlled` executor was removed in k6 v2. Each scenario can define `exec` (function name), `startTime`, `gracefulStop`, `tags`, `env`.

Multi-scenario script with data from a file, a custom metric, checks and thresholds per route:

```js
import http from "k6/http";
import { check, group, sleep } from "k6";
import { SharedArray } from "k6/data";
import { Trend } from "k6/metrics";

const users = new SharedArray("users", () => JSON.parse(open("./data/users.json")));
const checkoutTime = new Trend("checkout_duration", true);

const BASE = __ENV.BASE_URL || "http://localhost:8080";

export const options = {
  scenarios: {
    browse: {
      executor: "ramping-arrival-rate",
      exec: "browse",
      startRate: 20,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { target: 300, duration: "3m" },
        { target: 300, duration: "10m" },
        { target: 0, duration: "1m" },
      ],
    },
    checkout: {
      executor: "constant-arrival-rate",
      exec: "checkout",
      rate: 20,
      timeUnit: "1s",
      duration: "14m",
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    "http_req_failed": [{ threshold: "rate<0.01", abortOnFail: true, delayAbortEval: "1m" }],
    "http_req_duration{route:/api/products}": ["p(95)<250", "p(99)<600"],
    "http_req_duration{route:/api/checkout}": ["p(95)<800", "p(99)<1500"],
    "checkout_duration": ["p(95)<1000"],
    "dropped_iterations": ["count==0"],
  },
};

function authHeaders() {
  const user = users[Math.floor(Math.random() * users.length)];
  // The token is minted ahead of time per test user; credentials are never hard-coded in the script.
  return { headers: { Authorization: `Bearer ${user.token}`, "Content-Type": "application/json" } };
}

export function browse() {
  group("browse", () => {
    const res = http.get(`${BASE}/api/products?limit=20`, { tags: { route: "/api/products" } });
    check(res, { "products 200": (r) => r.status === 200 });
  });
  sleep(Math.random() * 2);
}

export function checkout() {
  const params = authHeaders();
  const res = http.post(`${BASE}/api/checkout`, JSON.stringify({ cartId: "load-test-cart" }), {
    ...params,
    tags: { route: "/api/checkout" },
  });
  checkoutTime.add(res.timings.duration);
  check(res, { "checkout 2xx": (r) => r.status >= 200 && r.status < 300 });
}
```

Notes:

- `SharedArray` loads data once and shares it between VUs; reading a large file in each VU multiplies memory.
- Tag requests with a bounded set of route names; do not tag with raw URLs or ids (metric cardinality).
- `abortOnFail` stops a run that is already invalid; `delayAbortEval` avoids aborting during warm-up.
- Run one scenario of a multi-scenario script with `k6 run --scenario checkout script.js` (k6 2.3+). Run a script once with `--once` for a smoke or functional pass.
- Pass settings with `-e` or `__ENV`. Do not commit tokens; generate test credentials in the pipeline.
- Output and dashboards: end-of-test summary on stdout; `--out experimental-prometheus-rw` (Prometheus remote write), `--out opentelemetry`, `--out json=results.json`, `--out web-dashboard` (built in since k6 2.0), or Grafana Cloud k6. Check the current docs for each output's environment variables.
- TypeScript scripts run natively in current k6 (`k6 run script.ts`); types for the k6 modules are published as `@types/k6`.
- k6 does not execute in a browser or run Node modules; use k6's own modules, `jslib.k6.io` libraries, or extensions built with xk6.
- Run the generator on separate machines from the system under test; in Kubernetes, the k6 Operator distributes a test across pods (check its current docs).

## 4. Locust

Python-based, with tasks written as code and a web UI or headless mode. A user class with weighted tasks:

```python
from locust import HttpUser, between, task


class ShopUser(HttpUser):
    wait_time = between(1, 3)  # closed model: think time between tasks

    def on_start(self):
        # Credentials come from the environment or a test-data service, never from the repository.
        self.client.headers.update({"Accept": "application/json"})

    @task(8)
    def browse(self):
        with self.client.get("/api/products?limit=20", name="/api/products", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"unexpected status {resp.status_code}")

    @task(1)
    def view_product(self):
        self.client.get("/api/products/42", name="/api/products/[id]")
```

Run headless and export results:

```bash
locust -f locustfile.py --headless --host https://staging.example.com \
  -u 500 -r 25 -t 15m --csv results --html report.html
```

`-u` is peak users, `-r` the spawn rate per second, `-t` the duration. Distributed mode uses `--master` and `--worker` processes (Python limits one process to roughly one core, so use one worker per core). Group dynamic URLs with the `name=` parameter so statistics do not explode in cardinality. For a fixed request rate use `constant_throughput` or `constant_pacing` wait times, or a `LoadTestShape` subclass to script ramps and spikes. Locust can fail a run through `--exit-code-on-error` and by setting `environment.process_exit_code` in event hooks; check the docs for current behavior.

## 5. Gatling

JVM-based, with an event-driven engine that handles many users per core. Gatling 3.x offers Java, Kotlin, Scala and JavaScript/TypeScript SDKs (check the current docs for the SDK you use and its build tooling). A Java DSL simulation with an open injection profile and assertions:

```java
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

public class ApiSimulation extends Simulation {

  HttpProtocolBuilder httpProtocol =
      http.baseUrl("https://staging.example.com").acceptHeader("application/json");

  ScenarioBuilder browse =
      scenario("Browse")
          .exec(http("list products").get("/api/products?limit=20").check(status().is(200)))
          .pause(1, 3);

  {
    setUp(browse.injectOpen(
                rampUsersPerSec(10).to(200).during(120),
                constantUsersPerSec(200).during(600))
            .protocols(httpProtocol))
        .assertions(
            global().responseTime().percentile(99).lt(800),
            global().failedRequests().percent().lt(1.0));
  }
}
```

Gatling generates an HTML report with percentile distributions per request. Assertions make the build fail when thresholds are missed.

## 6. Test data and environment

- Generate synthetic, anonymized data. Never copy production personal data into test environments; if you must use production-derived data, mask it first.
- Unique-data operations (signups, orders) need per-VU unique values (VU id plus iteration) to avoid conflicts that skew the test.
- Warm up (caches, connection pools, JIT) and exclude warm-up from the measured window; also run a cold-start test separately.
- Keep the system under test isolated from other traffic; record versions, config, instance counts and data size with the result.
- Make external dependencies (payment, email) use sandboxes or stubs with realistic latency and error rates; do not load third-party production systems.
- Monitor the generator: CPU above about 70%, memory growth, or network saturation invalidate results.

## 7. CI usage

- Run a short smoke or small-scale load test on every merge or nightly, with thresholds that fail the job; run big tests on a schedule or before releases.
- Store results per build (JSON or CSV) and compare to a baseline; alert on a regression larger than the run-to-run noise (measure noise by repeating the same test).
- Pass secrets such as base URLs and tokens via CI secrets; never print them. Use dedicated test accounts and tenants.
- Example GitHub Actions step (the URL comes from an environment variable and not from an interpolated expression inside the script):

```yaml
- name: Smoke load test
  env:
    BASE_URL: ${{ vars.STAGING_URL }}
  run: ./k6 run --quiet -e BASE_URL="$BASE_URL" load/smoke.js
```

## 8. Reading results

- Start with errors and dropped iterations: a run with errors or generator limits is not a valid latency measurement.
- Look at latency percentiles over time, not only the final summary; correlate with throughput, CPU, GC, pool wait, queue depth and database metrics.
- Find the knee: the load at which latency begins to rise faster than throughput. Capacity at the SLO is below the knee.
- Compare against Little's law: in-flight requests = rate × latency. A mismatch means requests are queueing somewhere or the generator is limiting.
- Check failure modes in stress tests: does the system shed load with 429/503 quickly, or time out slowly and cascade? Does it recover after the load stops?
- Turn results into capacity numbers: max sustainable requests per second per instance at the latency goal, then divide expected peak by that figure (see [autoscaling-capacity.md](autoscaling-capacity.md)).
- Report the test design and limitations next to the numbers: data size, environment differences, load profile, dependency stubs.
