# Scenarios and Thresholds

Executors, workload models, VU sizing, thresholds and configuration profiles for each test type in Grafana k6 v2.3.0. Option names below were parsed by `k6 run` and `k6 inspect` on v2.3.0 (2026-10).

## Contents

1. [Scenario basics](#1-scenario-basics)
2. [Executors](#2-executors)
3. [Open versus closed models](#3-open-versus-closed-models)
4. [Sizing VUs for arrival-rate executors](#4-sizing-vus-for-arrival-rate-executors)
5. [Thresholds](#5-thresholds)
6. [Test type profiles](#6-test-type-profiles)
7. [Running subsets and overrides](#7-running-subsets-and-overrides)

## 1. Scenario basics

```js
export const options = {
  scenarios: {
    browse: {
      executor: 'constant-arrival-rate',
      rate: 30, timeUnit: '1s', duration: '10m',
      preAllocatedVUs: 40, maxVUs: 120,
      exec: 'browse',                 // exported function to run
      startTime: '0s',                // delay before this scenario starts
      gracefulStop: '30s',            // time to let in-flight iterations finish
      env: { JOURNEY: 'browse' },     // per-scenario environment
      tags: { journey: 'browse' },    // tags added to every sample
    },
    checkout: {
      executor: 'constant-arrival-rate',
      rate: 3, timeUnit: '1s', duration: '10m',
      preAllocatedVUs: 20, maxVUs: 60,
      exec: 'checkout',
      tags: { journey: 'checkout' },
    },
  },
};
```

- Scenarios run in parallel by default; use `startTime` to sequence them (for example warm-up first, then main load).
- Common options on all executors: `exec`, `startTime`, `gracefulStop`, `env`, `tags`.
- Top-level shortcuts (`vus`, `duration`, `stages`, `iterations`) are syntax sugar for a single scenario. Do not mix them with `scenarios`.
- Per-scenario thresholds use the scenario tag that k6 adds automatically: `'http_req_duration{scenario:browse}': ['p(95)<400']`.

## 2. Executors

| Executor | Model | Main options | Use for |
|---|---|---|---|
| `constant-vus` | Closed | `vus`, `duration` | Fixed concurrency, simple soak or baseline |
| `ramping-vus` | Closed | `startVUs`, `stages` (`duration`, `target`), `gracefulRampDown` | Ramp concurrency up and down, stress |
| `per-vu-iterations` | Closed | `vus`, `iterations`, `maxDuration` | Each VU runs exactly N iterations (per-user data) |
| `shared-iterations` | Closed | `vus`, `iterations`, `maxDuration` | A fixed total number of iterations split across VUs (smoke, data processing) |
| `constant-arrival-rate` | Open | `rate`, `timeUnit`, `duration`, `preAllocatedVUs`, `maxVUs` | Fixed requests (iterations) per time unit |
| `ramping-arrival-rate` | Open | `startRate`, `timeUnit`, `stages`, `preAllocatedVUs`, `maxVUs` | Ramp the arrival rate: spike, breakpoint |

Examples:

```js
// Closed: ramp concurrency
{ executor: 'ramping-vus', startVUs: 0, gracefulRampDown: '30s',
  stages: [{ duration: '5m', target: 100 }, { duration: '10m', target: 100 }, { duration: '2m', target: 0 }] }

// Closed: 50 users, 10 iterations each, at most 10 minutes
{ executor: 'per-vu-iterations', vus: 50, iterations: 10, maxDuration: '10m' }

// Closed: 1000 iterations shared among 20 VUs
{ executor: 'shared-iterations', vus: 20, iterations: 1000, maxDuration: '10m' }

// Open: 100 iterations per second for 15 minutes
{ executor: 'constant-arrival-rate', rate: 100, timeUnit: '1s', duration: '15m',
  preAllocatedVUs: 150, maxVUs: 500 }

// Open: ramp the rate from 10 to 300 per second
{ executor: 'ramping-arrival-rate', startRate: 10, timeUnit: '1s',
  preAllocatedVUs: 100, maxVUs: 1000,
  stages: [{ target: 100, duration: '5m' }, { target: 300, duration: '10m' }] }
```

- `externally-controlled` was removed in v2.0.0, along with `k6 scale`, `k6 pause` and `k6 resume`. Use scripts with `ramping-*` executors instead.
- `rate` is iterations per `timeUnit`, not HTTP requests; one iteration with three requests at rate 10 means 30 requests per second.
- `gracefulStop` (default 30s) lets running iterations complete after the duration; `gracefulRampDown` does the same for VUs removed during a ramp-down.

## 3. Open versus closed models

- Closed model (VU-based): a fixed number of VUs each loop "request, wait for response, think, repeat". When the server slows down, each VU completes fewer iterations, so the offered load falls exactly when the system is struggling.
- Open model (arrival-rate): new iterations start on a schedule, independent of how fast previous ones finish, like independent users arriving at a site. If the server slows down, iterations overlap and more VUs are in use, so queues and tail latency become visible.
- Coordinated omission: a measurement bias in closed loops where a stall delays the next request, so the long wait is recorded as one slow sample instead of the many slow samples that real arrivals during the stall would have experienced. The reported tail looks better than reality. Arrival-rate executors avoid it because the schedule does not wait for responses.
- Use the open model for public sites and APIs with many independent clients. Use the closed model when the real population is bounded (a pool of workers, a few batch clients), or to find the throughput at fixed concurrency.
- An open-model test at a rate above capacity does not stabilise: VUs grow until `maxVUs` is reached, and then `dropped_iterations` counts what k6 could not start. Treat dropped iterations as a failed test run unless it is a deliberate breakpoint test.
- A closed test shows the throughput the system can sustain at a given concurrency; an open test shows the latency users experience at a given arrival rate. Both are useful; do not compare their numbers directly.

## 4. Sizing VUs for arrival-rate executors

- VUs needed (Little's law) is approximately: arrival rate per second multiplied by the iteration duration in seconds (including think time).
- Example: rate 50 per second, iteration with 2 s of think time and 0.3 s of requests: 50 * 2.3 = 115 VUs. Set `preAllocatedVUs` near 115 and `maxVUs` at 150 to 200.
- `preAllocatedVUs` are initialised before the test starts; VUs added up to `maxVUs` are initialised mid-test, which costs CPU and can distort timings. Prefer a generous `preAllocatedVUs`.
- Watch `vus`, `vus_max` and `dropped_iterations` in the summary. If `vus` equals `maxVUs` and `dropped_iterations` is above zero, either the server is saturated or `maxVUs` is too low; check server metrics to tell which.
- Add `dropped_iterations: ['count==0']` as a threshold (or `rate<0.01` style limits on a ratio you compute) when the target rate must hold.
- Reduce think time in arrival-rate scenarios if you need fewer VUs and the model allows it; think time still affects open-model realism through connection and session lifetime.

## 5. Thresholds

```js
export const options = {
  thresholds: {
    // built-in metrics
    http_req_failed: ['rate<0.01'],                    // under 1 percent errors
    http_req_duration: ['p(90)<300', 'p(95)<500', 'p(99)<1500', 'max<5000'],
    checks: ['rate>0.99'],
    dropped_iterations: ['count==0'],

    // sub-metrics by tag
    'http_req_duration{name:GET /items/:id}': ['p(95)<250'],
    'http_req_duration{scenario:browse}': ['p(95)<400'],
    'http_req_duration{expected_response:true}': ['p(95)<400'],

  },
};
```

Strings and objects can be mixed in one metric's array, and each metric key must appear once. To abort the whole test early, use the object form:

```js
export const options = {
  thresholds: {
    http_req_duration: [
      'p(95)<500',
      { threshold: 'p(99)<3000', abortOnFail: true, delayAbortEval: '1m' },
    ],
  },
};
```

- Syntax: `<aggregation> <operator> <value>`. Aggregations by metric type: Counter `count`, `rate`; Gauge `value`; Rate `rate`; Trend `avg`, `min`, `med`, `max`, `p(N)`. Operators: `<`, `<=`, `>`, `>=`, `==`, `!=`.
- Crossing any threshold makes the run fail with exit code 99 (run locally: `p(95)<1` on a real request returned 99 and printed "thresholds on metrics 'http_req_duration' have been crossed").
- `abortOnFail: true` stops the test as soon as the threshold fails; `delayAbortEval` waits before the first evaluation to avoid aborting on start-up noise. Useful for breakpoint tests and for protecting shared environments.
- Checks versus thresholds: a check records a boolean per assertion and never fails the run alone; a threshold is evaluated on aggregated metrics at the end (or continuously with `abortOnFail`) and decides the exit code. Convert checks into a gate with a threshold on the `checks` metric.
- `http_req_failed` counts responses outside the expected status range (default 200-399) and transport errors. Failed requests still contribute to `http_req_duration` unless filtered with `{expected_response:true}`.
- Derive thresholds from SLOs: if the SLO says "95 percent of checkout requests under 800 ms and under 0.5 percent errors", write exactly those two thresholds, scoped to the checkout tag.
- A threshold on a tag that never appears passes silently in some setups; verify in the summary that the sub-metric line is printed.

## 6. Test type profiles

| Type | Question | Shape | Typical thresholds |
|---|---|---|---|
| Smoke | Does the script and the system work at all? | 1-5 VUs, 30 s to 2 min | Strict: error rate 0, normal latency |
| Load | Does it meet the SLO at expected peak? | Ramp to expected rate, hold 15-60 min | SLO latency percentiles and error rate |
| Stress | Where does it degrade, and how does it fail? | Step up to 150-300 percent of peak | Looser; observe, not gate |
| Spike | Does it survive and recover from a sudden surge? | Jump to many times normal in seconds, return | Recovery: latency back to baseline after the spike |
| Soak | Does it leak or degrade over hours? | 60-80 percent of peak for 4-24 hours | Stable latency, memory flat, no error growth |
| Breakpoint | What is the maximum sustainable rate? | `ramping-arrival-rate` rising until failure | `abortOnFail` on error rate or latency |

```js
// Load: ramp to 100/s, hold, ramp down (open model)
const load = {
  executor: 'ramping-arrival-rate', startRate: 10, timeUnit: '1s',
  preAllocatedVUs: 150, maxVUs: 400,
  stages: [
    { target: 100, duration: '5m' },   // ramp-up
    { target: 100, duration: '30m' },  // hold: measure here
    { target: 0, duration: '2m' },     // ramp-down
  ],
};

// Spike
const spike = {
  executor: 'ramping-arrival-rate', startRate: 10, timeUnit: '1s',
  preAllocatedVUs: 300, maxVUs: 1500,
  stages: [
    { target: 10, duration: '2m' },
    { target: 500, duration: '30s' },  // surge
    { target: 500, duration: '2m' },
    { target: 10, duration: '30s' },
    { target: 10, duration: '5m' },    // recovery window
  ],
};

// Breakpoint: climb until the threshold aborts the run
const breakpoint = {
  executor: 'ramping-arrival-rate', startRate: 10, timeUnit: '1s',
  preAllocatedVUs: 500, maxVUs: 2000,
  stages: [{ target: 1000, duration: '30m' }],
};
// thresholds: http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '1m' }]
```

- Warm-up: add a low-rate first stage or a separate scenario with `startTime` offsets and its own tag, and exclude it from thresholds with tag-scoped metrics.
- The numbers above are illustrations; derive real rates from production traffic and the SLO, not from these examples.
- Run a stress test only after a load test passes, and a soak only after the system is stable at peak.

## 7. Running subsets and overrides

```bash
k6 run --once tests/load.ts                       # 1 VU, 1 iteration, check the script
k6 run --scenario browse tests/load.ts            # run only named scenarios (comma-separated)
k6 run -e PROFILE=stress tests/load.ts            # profile switch via __ENV
k6 run --summary-mode=full tests/load.ts          # compact (default), full or disabled
k6 inspect tests/load.ts                          # print resolved options as JSON
```

- `--scenario` overrides options such as `vus` and `iterations` from the script; v2.3.0 printed a warning saying so, and an unknown name fails with "scenario not found".
- A profile switch keeps one script for smoke, load and stress:

```ts
const profiles: Record<string, Options> = {
  smoke: { vus: 1, duration: '30s', thresholds: { http_req_failed: ['rate<0.01'] } },
  load: { scenarios: { main: load } },
};
export const options: Options = profiles[__ENV.PROFILE ?? 'smoke'];
```

- `k6 run --paused` starts paused and needs the REST API (`--address`), which is off by default in v2. Prefer scripted stages to interactive control.
- Always run `k6 inspect` after editing scenarios: typos in executor options produce an error at start-up rather than mid-test.
