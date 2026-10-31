---
name: load-testing-expert
description: >-
  Designs, writes and runs load and performance tests with Grafana k6 (scenarios, executors, thresholds, checks, custom metrics, TypeScript scripts, CI gating) and, briefly, Locust. Use when editing k6 scripts (.js, .ts), running k6 run or k6 cloud, choosing open or closed workload models, setting SLO thresholds, planning smoke, stress, spike, soak or breakpoint tests, or reading latency percentiles. Not for Core Web Vitals or front-end speed (use core-web-vitals-expert), backend scaling design (use scalability-expert), metrics and tracing setup (use observability-expert), statistical analysis (use statistics-expert) or functional browser tests (use playwright-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Load Testing Expert

This skill covers load, stress and performance testing of HTTP, gRPC and WebSocket services with Grafana k6, plus a short Locust section. It includes script structure, workload modelling with scenarios and executors, thresholds as pass/fail criteria, CI gating, result outputs, and the methodology that makes a test meaningful (SLOs first, realistic workload, warm-up, monitoring the system under test). Load may only be directed at systems the operator owns or is authorised to test.

> Verified against Grafana k6 v2.3.0 (linux-amd64 release binary, SHA-256 checked against the published checksums file, scripts run locally against a loopback server), k6 v2.0.0 release notes, grafana/setup-k6-action and grafana/run-k6-action README (major tag v1) and Locust 2.47.0 (installed from PyPI, headless run executed) (2026-10).

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

- Covered: k6 script lifecycle (init, `setup`, default function, `teardown`, `handleSummary`), `options` with scenarios and executors, open and closed workload models, thresholds, checks, tags, groups, custom metrics, `SharedArray` data, `__ENV`, outputs, CI usage, Grafana Cloud k6 and k6-operator at overview level, test types and load-test methodology, and Locust basics.
- Not covered: Core Web Vitals and browser rendering performance (core-web-vitals-expert); designing a system to scale (scalability-expert); dashboards, tracing and alerting setup for the system under test (observability-expert); significance testing and distribution analysis of results (statistics-expert); functional end-to-end browser tests (playwright-expert, e2e-testing-expert); pipeline structure in general (cicd-expert); gRPC service design (grpc-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| k6 versions | Latest release checked: v2.3.0 (Sep 2026), with v2.0.0 released in May 2026 and a v1.8.x line still receiving fixes. The Go module path is `go.k6.io/k6/v2`. Scripts written for 1.x run unchanged unless they use removed features (see below) |
| v2 removals | `externally-controlled` executor, `k6 login`, `k6 pause`, `k6 resume`, `k6 scale`, `k6 status`, `--no-summary` (use `--summary-mode=disabled`), `options.ext.loadimpact` (use `options.cloud`). The REST API server is off unless `--address` or `K6_ADDRESS` is set. `k6 cloud script.js` became `k6 cloud run script.js` |
| TypeScript | k6 runs `.ts` files directly (`k6 run test.ts`); no bundler is needed. Types for options come from `import type { Options } from 'k6/options'`. Type checking is not performed by k6, so run `tsc --noEmit` separately if wanted |
| Script lifecycle | Init code runs once per VU (top-level, imports, `open()`, `SharedArray`); `setup()` runs once and returns data; the default function (or an `exec` function) runs per iteration; `teardown(data)` runs once; `handleSummary(data)` runs at the end and can write files |
| Executors | `constant-vus`, `ramping-vus`, `per-vu-iterations`, `shared-iterations` (closed model); `constant-arrival-rate`, `ramping-arrival-rate` (open model). `externally-controlled` no longer exists |
| Thresholds | Pass/fail rules on metrics, for example `http_req_duration: ['p(95)<500']`. A crossed threshold makes `k6 run` exit with code 99. Checks never fail a run by themselves |
| Built-in outputs | `--out` accepts `cloud`, `csv`, `experimental-opentelemetry`, `experimental-prometheus-rw`, `influxdb`, `json`, `opentelemetry`, `statsd`, `web-dashboard` (list taken from the v2.3.0 error message for an unknown type) |
| CLI helpers | `k6 new` scaffolds a script, `k6 run --once` runs 1 VU and 1 iteration, `k6 run --scenario a,b` selects named scenarios, `k6 inspect` prints resolved options, `k6 deps` lists dependencies, `--summary-mode` takes `compact`, `full` or `disabled` |
| Protocol modules | `k6/http`, `k6/net/grpc`, `k6/websockets`, `k6/browser` (import `{ browser } from 'k6/browser'`), `k6/data`, `k6/metrics`, `k6/crypto`, `k6/encoding`; extensions load as `k6/x/<name>` |
| Locust | Python load tool: `HttpUser`, `@task`, `wait_time`; headless via `--headless -u -r -t`; distributed via `--master` and `--worker`. Latest on PyPI checked: 2.47.0 |

## 3. Workflow

1. Confirm authorisation and the target: a staging or dedicated performance environment owned by the requester, never third-party production. Record who approved and the time window.
2. Define the question and SLOs before writing code: which user journeys, which percentile of latency, which error rate, which throughput, under what data volume.
3. Build the workload model from production analytics or access logs: arrival rate per journey, mix, think time, data variety. Choose an open model (arrival rate) for public traffic.
4. Write a smoke script first (`--once` or 1 VU, a few iterations) and fix correctness: auth, checks, data, correct status codes.
5. Add thresholds that encode the SLOs, then scenarios for the test type (load, stress, spike, soak, breakpoint). Keep configuration in `options`, environment-specific values in `__ENV`.
6. Make sure the system under test is observed (CPU, memory, saturation, connection pools, GC, queue depth, errors) and that load generator capacity is not the bottleneck.
7. Warm up, run, and collect results with `--out` or `handleSummary`. Keep the exact script revision, k6 version, environment build and data set with the results.
8. Report percentiles, error rate, throughput and the limiting resource, with the SLO verdict. Do not report averages alone.
9. Wire the smoke or a short load profile into CI with thresholds as the gate; run long tests on a schedule or on demand.

## 4. Decision Rules

- If traffic comes from independent users (public web, API clients), use an arrival-rate executor (`constant-arrival-rate`, `ramping-arrival-rate`): the request rate stays fixed when the server slows down, and queueing shows up as latency. If the real system has a fixed pool of clients (workers, a few integrations), use VU-based executors.
- If a VU-based test shows flat latency while the server is saturated, suspect coordinated omission: slow responses reduce the offered load. Switch to an arrival-rate executor.
- If an arrival-rate scenario reports `dropped_iterations`, `preAllocatedVUs` or `maxVUs` is too low, or the generator is saturated. Raise `maxVUs` or add generator capacity before trusting results.
- If the goal is a pass/fail gate in CI, use thresholds. If the goal is to flag functional problems inside a run, use checks. Combine them with a threshold on `checks` (`checks: ['rate>0.99']`).
- If each iteration must fail fast on an overloaded system, add `abortOnFail: true` (optionally `delayAbortEval`) on the threshold that defines unacceptable.
- If data varies per user, load it once with `SharedArray` in init code; never `JSON.parse(open(...))` at top level of a large file in every VU.
- If a test needs secrets (tokens, passwords), pass them with `-e NAME=value` from the CI secret store or through `K6_`-style environment, never in the script or repository.
- If the question is "how much can it take", run a breakpoint test (ramping arrival rate with `abortOnFail` thresholds). If it is "does it meet the SLO at expected peak", run a load test at a fixed rate. If it is "does it leak or degrade over time", run a soak.
- If a single generator cannot produce the load (CPU above about 80 percent, rising `dropped_iterations`, noisy timings), distribute with k6-operator, Grafana Cloud k6, or several generators with split rates.
- If the team needs a browser-level scenario, use `k6/browser` sparingly and at low VU counts; protocol-level tests carry the load.

## 5. Coding Standards

- One scenario per user journey, named for the journey (`checkout`, `search`), each with its own `exec` function and tags.
- Keep `options` at the top of the file, typed as `Options` in TypeScript. Do not compute options from random values.
- Name requests with `tags: { name: 'GET /items/:id' }` when the URL contains ids, so metrics group by route and cardinality stays low.
- Always `check` the status and one body property that proves correctness; a fast 500 is not a fast success.
- Use `http.batch()` only when a real client issues the requests in parallel.
- Use `sleep()` for think time with randomisation (`sleep(1 + Math.random() * 2)`); in arrival-rate scenarios think time only holds VUs longer, so size `preAllocatedVUs` accordingly.
- Keep per-iteration allocations small; avoid building large strings or arrays in the default function.
- Put shared helpers in modules imported with relative paths; local files are bundled for cloud and archive runs.
- Remote imports (for example from jslib.k6.io) need network access at start-up; pin the version in the URL, or vendor the file for offline CI.
- Use `discardResponseBodies: true` globally and `responseType: 'text'` only on requests that read the body.

## 6. Project Structure

```text
perf/
+-- README.md             # purpose, environments, how to run, who approves
+-- tests/
|   +-- smoke.ts          # 1 VU, 30 s, CI gate
|   +-- load.ts           # expected peak, 15-30 min
|   +-- stress.ts         # above peak, find the knee
|   +-- spike.ts          # sudden surge and recovery
|   +-- soak.ts           # moderate load, hours
|   +-- breakpoint.ts     # ramp until thresholds abort
+-- lib/
|   +-- config.ts         # env parsing, scenario builders
|   +-- auth.ts           # token acquisition from __ENV
|   +-- checks.ts         # shared checks
+-- data/
|   +-- users.json        # synthetic data only, no real personal data
+-- .github/workflows/perf.yml
```

- Scenario builders in `lib/config.ts` let smoke, load and stress reuse the same journeys with different rates.
- Keep synthetic data in the repository and sensitive values out of it.
- Store results (JSON summary, run metadata) as CI artefacts or in the metrics backend, not in git.

## 7. Design Patterns

- **Journey per scenario**: each scenario runs one exported function through `exec`, so rates per journey can follow production mix. Cost: more scenarios to size.
- **Profile switch by env**: `const PROFILE = __ENV.PROFILE ?? 'smoke'` selects a prebuilt `options` object. Cost: profiles can drift; keep them in one file.
- **Setup returns a token or fixtures**: `setup()` logs in once and returns data to each VU. Cost: the token may expire in soak tests; refresh inside the iteration when needed.
- **Per-VU login**: authenticate in the first iteration of each VU (check `vu.iterationInScenario` imported from `k6/execution`) when each user needs its own session.
- **Threshold per tag**: `'http_req_duration{name:GET /items/:id}': ['p(95)<300']` gives per-endpoint SLOs. Thresholds on a tag only evaluate if requests carry that tag (add a looser guard threshold so a typo does not silently pass).
- **Custom metrics for business timing**: a `Trend` for checkout time, a `Counter` for orders, a `Rate` for business failures, a `Gauge` for queue depth read from an API.
- **Staged rollout of load**: ramp over minutes, hold, ramp down, so autoscaling, caches and connection pools behave as in reality.

## 8. Best Practices

- Test against an environment that matches production in topology, instance sizes, data volume, indexes, cache configuration, TLS and network path. If it does not, state the difference in the report and avoid extrapolating.
- Warm up caches, JIT and connection pools before measuring; discard or tag the warm-up window (`startTime` on later scenarios, or a separate warm-up scenario with its own tag).
- Isolate the test: no unrelated traffic, no shared noisy neighbours, stable dependencies (or mock the third parties that must not be hit).
- Hold one variable constant at a time; change one thing between runs and keep the run log.
- Repeat important runs at least three times and compare, since single runs can differ because of noise.
- Read p50, p90, p95, p99 and max together with throughput and error rate; the average hides tail latency.
- Correlate k6 metrics with server-side resource metrics on the same time axis; the cause of a latency knee is a saturated resource.
- Keep the generator healthy: watch its CPU, memory, network and `dropped_iterations`. Run it in the same region as the target unless geography is part of the test.
- Prefer `ramping-arrival-rate` for finding limits and `constant-arrival-rate` for verifying an SLO.

## 9. Performance

- Generator cost: each VU holds a JavaScript runtime; thousands of VUs need memory. Use `discardResponseBodies`, `SharedArray`, and avoid large per-VU state.
- Open-model sizing: `preAllocatedVUs` is roughly rate multiplied by expected iteration duration in seconds, with headroom; set `maxVUs` above it, and treat any growth beyond `preAllocatedVUs` as an allocation cost during the run.
- Metric volume: high-cardinality tags (raw URLs, ids, timestamps) inflate memory and output size. Use the `name` tag, and tune `systemTags` if needed.
- Output cost: streaming every point to JSON or CSV for long soak tests produces large files; prefer aggregated outputs (Prometheus remote write, cloud) or `handleSummary` for long runs.
- Connection behaviour: k6 reuses connections per VU by default. `--no-vu-connection-reuse` models clients that reconnect every time and costs more TLS handshakes.
- Percentiles are computed from trend metrics in memory; `summaryTrendStats` selects the displayed statistics (for example `['avg', 'p(90)', 'p(95)', 'p(99)', 'max']`).
- Locust: use `FastHttpUser` when a single process cannot generate enough requests, and `--processes` to use multiple cores.

## 10. Security

- Authorisation first: only test systems you own or have written permission to test. Many providers require advance notice for load tests; third-party production endpoints, shared SaaS and public sites you do not control are out of bounds.
- Keep credentials out of scripts and git. Supply them with `-e NAME=value` from CI secrets or a secret manager; never print them with `console.log`; avoid putting them in URLs or tags, since tags appear in outputs.
- Use dedicated test accounts and synthetic data. Do not replay production personal data into a test environment.
- Mask sensitive headers when using `--http-debug`, and do not upload debug output to shared locations.
- Set `insecureSkipTLSVerify` only for internal test environments with private CAs, never as a default.
- Protect the target: apply a hard cap (`maxVUs`, `abortOnFail`) so a mistaken rate cannot overwhelm shared infrastructure; coordinate with dependencies that will receive traffic (payment sandboxes, email senders, SMS gateways) and stub them.
- Treat third-party extensions and remote script imports as supply-chain inputs: pin versions, review sources.
- Scope CI tokens (cloud tokens, remote-write credentials) to the minimum, store them as repository secrets, and give workflows `contents: read` only.

## 11. Testing

- Test the test: run `k6 run --once script.ts` and read the output before scaling; confirm checks fail when the service returns an error.
- Verify option syntax with `k6 inspect script.ts` and run a 10-second version of each scenario to confirm executor settings parse.
- Validate threshold wiring by lowering a limit to an impossible value and confirming exit code 99.
- Validate the workload model: compare achieved `http_reqs` per second and per route against the target mix.
- Check the generator against a trivial local endpoint to measure its own overhead and ceiling.
- Keep a smoke test in CI on every change to the service or the test suite; keep load tests on a schedule or on demand.

## 12. Review Checklist

- Is the target an environment the team owns or is authorised to test, and is the window approved?
- Are SLOs written down, and do thresholds encode them (latency percentile, error rate, throughput)?
- Is the executor choice justified (open versus closed), with `preAllocatedVUs` and `maxVUs` sized?
- Do checks verify correctness, and is there a threshold on `checks` or `http_req_failed`?
- Are requests named so URLs with ids do not explode metric cardinality?
- Are secrets provided by environment variables and absent from the repository and logs?
- Is test data synthetic, sufficiently varied (no single cached record), and loaded via `SharedArray`?
- Is warm-up handled, and is the measurement window clear?
- Is the system under test monitored, and are generator metrics watched?
- Does the report give p95 and p99, error rate, throughput, the bottleneck and the environment differences?
- Does CI fail on exit code 99 and keep the summary as an artefact?

## 13. Production Notes

- Thresholds are the pass/fail contract: `k6 run` exits non-zero (99) when any threshold is crossed. Other non-zero codes cover script and configuration errors (a failed module load returned 107 in the v2.3.0 check); cloud runs aborted for reasons other than thresholds exit with 97 since v2.0.0. Check the docs for the full table before scripting around specific codes.
- Grafana Cloud k6 runs the same scripts from managed load zones (`k6 cloud run script.ts`), or streams local runs to the cloud. v2 requires a stack for all `k6 cloud` commands, set through `K6_CLOUD_STACK_ID`, a flag, or `options.cloud`. Tokens come from `K6_CLOUD_TOKEN`.
- k6-operator runs distributed tests on Kubernetes through a `TestRun` custom resource whose parallelism splits the load across runner pods; see the repository samples and CRD documentation for the current schema.
- Extensions add protocols and outputs (`k6/x/...`); custom binaries are built with xk6, and v2 changed the extension Go module path. Check the extension docs for automatic provisioning and version support.
- Built-in web dashboard: `k6 run --out web-dashboard script.ts` serves live charts without a separate extension in v2.
- Keep the k6 version pinned in CI (`k6-version` input of the setup action) so results compare across runs, and upgrade deliberately.
- Run long tests from a stable machine in the target's network zone, with the CPU and network of the generator monitored.
- A scheduled nightly load test against a stable environment gives a trend line; alert on regression against a baseline, not just on absolute thresholds.

## 14. Examples

A typed script with an open-model scenario, thresholds, checks and a custom metric. The same constructs (typed `Options`, arrival-rate scenario, tag thresholds, `SharedArray`, `Trend`) ran on k6 v2.3.0 against a local server.

```ts
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import type { Options } from 'k6/options';

const BASE_URL = __ENV.BASE_URL ?? 'http://localhost:8080';
const waiting = new Trend('waiting_custom', true);
const items = new SharedArray('items', () => JSON.parse(open('./data/items.json')));

export const options: Options = {
  scenarios: {
    browse: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 50,
      maxVUs: 200,
      exec: 'browse',
      tags: { journey: 'browse' },
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: [{ threshold: 'p(95)<500', abortOnFail: true, delayAbortEval: '30s' }],
    checks: ['rate>0.99'],
    dropped_iterations: ['count==0'],
  },
};

export function browse(): void {
  const item = items[Math.floor(Math.random() * items.length)];
  const res = http.get(`${BASE_URL}/items/${item.id}`, { tags: { name: 'GET /items/:id' } });
  waiting.add(res.timings.waiting);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has id': (r) => (r.json('id') as number) === item.id,
  });
  sleep(1 + Math.random() * 2);
}
```

Run it with the secret and target supplied from the environment:

```bash
k6 run -e BASE_URL=https://staging.example.test tests/load.ts
echo "exit code: $?"   # 0 pass, 99 when a threshold is crossed
```

More examples (executors, stress, spike, soak, CI, Locust) are in the reference files.

## 15. Common Mistakes

- Using a closed model for public traffic, so a slowing server automatically receives less load and tail latency looks fine (coordinated omission).
- Reporting the average or p50 and ignoring p95, p99 and max.
- Treating `check` failures as test failures: checks only count; without a threshold on `checks` the exit code stays 0.
- Leaving `dropped_iterations` unwatched in arrival-rate tests, so the achieved rate is below the target.
- Hitting one cached record for every request, then reporting cache latency as service latency.
- Putting raw URLs with ids into metrics, creating thousands of series.
- Running the generator on a laptop on Wi-Fi, or on a saturated CI runner, and attributing noise to the service.
- Skipping warm-up, or including a cold start in the measured window without saying so.
- Hardcoding tokens in the script or committing them with a results file.
- Pointing load at third-party or production systems without permission.
- Comparing runs made with different data sizes, environment builds or k6 versions.
- Using `externally-controlled` or the removed `k6 login` and `k6 scale` commands from older tutorials on k6 v2.

## 16. References

- [references/k6-scripting.md](references/k6-scripting.md): script lifecycle, TypeScript, http and batch, checks, groups and tags, custom metrics, SharedArray, __ENV and secrets, auth and cookies, handleSummary, browser, gRPC, WebSocket, extensions.
- [references/scenarios-and-thresholds.md](references/scenarios-and-thresholds.md): all six executors with options, open versus closed models and coordinated omission, sizing VUs, threshold syntax, abortOnFail, per-tag thresholds, profiles for each test type.
- [references/ci-and-reporting.md](references/ci-and-reporting.md): exit codes, GitHub Actions workflow, outputs (JSON, CSV, Prometheus, OpenTelemetry, InfluxDB, web dashboard), Grafana Cloud k6, k6-operator, methodology, SLOs and report structure.
- [references/locust.md](references/locust.md): HttpUser, tasks, wait_time, headless flags, distributed mode, FastHttpUser, CI use and a comparison with k6.
- k6 documentation: https://grafana.com/docs/k6/latest/ and release notes https://github.com/grafana/k6/releases
- k6 GitHub Action repositories: https://github.com/grafana/setup-k6-action and https://github.com/grafana/run-k6-action
- k6-operator: https://github.com/grafana/k6-operator
- Locust documentation: https://docs.locust.io/
