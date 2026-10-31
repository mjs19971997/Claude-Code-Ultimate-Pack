# CI, Outputs and Reporting

Running k6 in CI, exit codes, result outputs, Grafana Cloud k6, k6-operator, and the methodology and reporting that make results usable. Facts checked against k6 v2.3.0 (local runs, help text), the v2.0.0 release notes and the GitHub Action READMEs (2026-10).

## Contents

1. [Exit codes and gating](#1-exit-codes-and-gating)
2. [GitHub Actions](#2-github-actions)
3. [Outputs](#3-outputs)
4. [Grafana Cloud k6](#4-grafana-cloud-k6)
5. [Distributed runs with k6-operator](#5-distributed-runs-with-k6-operator)
6. [Methodology](#6-methodology)
7. [Monitoring the system under test](#7-monitoring-the-system-under-test)
8. [Reporting](#8-reporting)

## 1. Exit codes and gating

- Exit code 0: the run finished and all thresholds passed.
- Exit code 99: one or more thresholds were crossed (run locally). CI treats any non-zero code as a failed step, so no extra scripting is needed.
- Exit code 107: the script could not be initialised (observed when a remote import was blocked). Other non-zero codes cover script errors and aborted runs; since v2.0.0 a cloud run aborted for a reason other than thresholds exits with 97. The docs hold the full table.
- A failed `check` does not change the exit code. Add `checks: ['rate>0.99']` or `http_req_failed: ['rate<0.01']` so errors gate the build.
- `abortOnFail` ends the run early and still exits 99.
- Keep the gate stable: use a fixed rate, a fixed data set and a dedicated environment. A flaky gate trains people to ignore it; use a short smoke profile for pull requests and a longer load profile on a schedule.
- Always upload the summary file as an artefact even when the step fails (`if: always()` on the upload step).

## 2. GitHub Actions

`grafana/setup-k6-action` installs k6 (inputs `k6-version`, and `browser: true` to install Chrome for browser tests). `grafana/run-k6-action` runs scripts from a glob (`path`) with `flags`, and by default (`cloud-run-locally: true`) uploads results to Grafana Cloud k6, which needs cloud credentials. For a plain local run with predictable exit code behaviour, a `run:` step with `k6 run` is simpler.

```yaml
name: perf-smoke

on:
  pull_request:
  schedule:
    - cron: "17 3 * * *"   # nightly load profile

permissions:
  contents: read

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      # Pin third-party actions to full commit SHAs; the SHAs below are placeholders.
      - uses: actions/checkout@<FULL_COMMIT_SHA>              # v4
        with:
          persist-credentials: false
      - uses: grafana/setup-k6-action@<FULL_COMMIT_SHA>       # v1
        with:
          k6-version: "2.3.0"
      - name: Run smoke test
        env:
          BASE_URL: ${{ vars.PERF_BASE_URL }}
          API_TOKEN: ${{ secrets.PERF_API_TOKEN }}
        run: k6 run --summary-export=summary.json perf/tests/smoke.ts
      - name: Upload summary
        if: always()
        uses: actions/upload-artifact@<FULL_COMMIT_SHA>       # v4
        with:
          name: k6-summary
          path: summary.json
```

- Secrets and variables are passed through `env:` and read in the script as `__ENV.BASE_URL` and `__ENV.API_TOKEN`; no `${{ }}` expression appears inside the `run:` command text.
- The README examples reference the actions by the major tag `@v1`; the commit SHAs in the example are placeholders. Resolve the real SHA of the release you reviewed (`gh api repos/grafana/setup-k6-action/git/ref/tags/v1`) and keep the tag in a trailing comment.
- Permissions are `contents: read` for the whole workflow; add more only to the job that needs them (for example `pull-requests: write` if a step comments on the PR).
- Running with `run-k6-action` instead (cloud features):

```yaml
      - uses: grafana/run-k6-action@<FULL_COMMIT_SHA>         # v1
        env:
          K6_CLOUD_TOKEN: ${{ secrets.K6_CLOUD_TOKEN }}
          K6_CLOUD_PROJECT_ID: ${{ secrets.K6_CLOUD_PROJECT_ID }}
        with:
          path: ./perf/tests/smoke.ts
          flags: --vus 5 --duration 30s
          fail-fast: true
```

  Inputs listed in the README: `path` (glob, one pattern per line), `flags`, `cloud-run-locally`, `cloud-comment-on-pr`, `parallel`, `fail-fast`, `debug`. With k6 v2, cloud commands also need a stack: `K6_CLOUD_STACK_ID`, a flag, or `options.cloud.stackID`.
- Only run load tests from CI against environments that tolerate them; pull-request workflows from forks must not receive secrets or point at shared infrastructure.
- Use `concurrency:` to prevent two load tests hitting the same environment simultaneously.
- Pull request smoke tests: 30 to 60 seconds, a handful of VUs, strict thresholds. Scheduled workflows: the full load profile with the artefact retained for trend comparison.

## 3. Outputs

Built-in `--out` types in v2.3.0 (from the CLI error for an unknown type): `cloud`, `csv`, `experimental-opentelemetry`, `experimental-prometheus-rw`, `influxdb`, `json`, `opentelemetry`, `statsd`, `web-dashboard`.

```bash
k6 run --out json=results.json tests/load.ts
k6 run --out csv=results.csv tests/load.ts
k6 run --out web-dashboard tests/load.ts            # live dashboard served by k6
k6 run --out json=results.json --out csv=results.csv tests/load.ts   # several outputs (run locally)
```

- JSON and CSV write one line per metric sample; files get large on long or high-rate runs. Use them for post-processing short tests, not for 12-hour soaks.
- Prometheus remote write (`--out experimental-prometheus-rw`) sends metrics to a Prometheus-compatible endpoint; the server URL is set with `K6_PROMETHEUS_RW_SERVER_URL`, and v2.3.0 accepts static labels through `K6_PROMETHEUS_RW_LABELS`. Check the docs for the trend-handling options (native histograms or computed stats) before building dashboards.
- OpenTelemetry output (`opentelemetry`) exports to an OTLP endpoint; v2 uses `K6_OTEL_EXPORTER_PROTOCOL` to choose the protocol and exports rate metrics as one counter. The `experimental-opentelemetry` name is also listed; check which one the docs recommend.
- InfluxDB (`influxdb`) and `statsd` are listed as built in on v2.3.0; the InfluxDB output targets v1-style endpoints in earlier versions, so check the docs for supported server versions before use.
- Tag outputs with the run: `--tag testid=2026-10-31-load-a`, so Grafana panels can filter by run and compare runs.
- `handleSummary` and `--summary-export` need no output backend and suit CI.
- Avoid high-cardinality tags in streamed outputs; they raise memory and cost.

## 4. Grafana Cloud k6

- Runs the same script on managed generators in chosen load zones, or streams results from a local run (`--out cloud`).
- v2 commands: `k6 cloud run script.ts` (replaces `k6 cloud script.ts`), `k6 cloud upload` (replaces `--upload-only`), `k6 cloud login` (replaces `k6 login cloud`), `k6 cloud project list`. A stack is required for every `k6 cloud` command.
- Configuration goes under `options.cloud` (the `ext.loadimpact` block was removed). Authentication uses `K6_CLOUD_TOKEN`; the project through `K6_CLOUD_PROJECT_ID`.
- `k6 cloud run --local-execution` runs the test locally but stores results in the cloud and can read cloud secrets via `secrets.get()` (v2.0.0 release notes).
- Benefits: no generator to manage, geographic distribution, stored run history and comparison. Costs: quota, plan limits, scripts leave your network. Check current limits in the docs.

## 5. Distributed runs with k6-operator

- k6-operator is a Kubernetes operator from Grafana. A `TestRun` custom resource names the script (typically stored in a ConfigMap or volume) and a `parallelism` value; the operator starts that many runner pods and each runs a segment of the load.
- Segments split VUs and arrival rates, so a script with `rate: 1000` and parallelism 4 produces about 250 per second per pod. Size `preAllocatedVUs` and `maxVUs` for the total; k6 divides them.
- Not every feature distributes the same way: thresholds are evaluated per runner in some setups, so send metrics to a shared backend (Prometheus remote write, cloud) and evaluate SLOs there. Check the operator docs for current behaviour.
- The CRD schema changes between versions; read `config/samples/` and `docs/crd-generated.md` in the repository for the release you install, and pin the operator version.
- Run generators in the same cluster or zone as the target only when that matches the real traffic path; otherwise use a separate cluster to avoid sharing noisy neighbours with the target.

## 6. Methodology

1. Write the SLOs first: example "p95 of `GET /search` under 400 ms and error rate under 0.5 percent at 200 requests per second, for 30 minutes".
2. Derive the workload model from production data: requests per second per route, journey mix, session length, think time distribution, data skew (hot and cold records), payload sizes.
3. Choose the test type per question (smoke, load, stress, spike, soak, breakpoint); do not run a stress test to prove an SLO.
4. Match the environment to production in size, topology, data volume, configuration and dependencies; if smaller, scale the load and state that results are indicative.
5. Warm up before measuring: caches, connection pools, JIT, autoscaling pre-warm. Mark the measurement window.
6. Baseline first: measure the current version under a fixed profile and keep the numbers; later runs compare against it.
7. Change one variable per run (code, config, instance type, load) and record it.
8. Repeat to see run-to-run variation; if three runs differ by more than the effect you want to detect, fix the noise first. Formal significance testing is the domain of statistics-expert.
9. Stop on safety limits: `abortOnFail` thresholds, a maximum `maxVUs`, and an operator who can cut traffic.
10. Clean up: remove test data, reset the environment, record the final state.

## 7. Monitoring the system under test

Collect, on one time axis with the k6 results:

- Saturation and utilisation: CPU, memory, disk and network I/O, thread and connection pool usage, file descriptors.
- Application signals: request rate, error rate, latency histograms per route, queue depth, GC pauses, lock contention.
- Datastores: query latency, slow queries, connection counts, replication lag, cache hit ratio.
- Downstream dependencies: latency and errors to third-party services or sandboxes.
- Platform: autoscaler decisions, pod restarts, throttling, load balancer 5xx and active connections.
- The generator itself: CPU, memory, network, `dropped_iterations`, `vus` against `vus_max`.

A latency knee usually coincides with one resource reaching saturation; the report should name it. Setting up the dashboards and alerting is the work of observability-expert.

## 8. Reporting

- Header: system version or commit, environment and its differences from production, k6 version, script revision, test type, profile, date and duration.
- Workload: executors, achieved versus target rate per journey, data set size, think time.
- Results: p50, p90, p95, p99 and max latency per key route; error rate by class; throughput; `dropped_iterations`; achieved concurrency.
- Verdict per SLO: pass or fail with the measured value and the threshold.
- Findings: where latency or errors began to grow, which resource saturated, and the evidence (graph or metric excerpt).
- Percentiles over averages: a mean of 120 ms can hide a p99 of 4 s. Never average percentiles across runs or routes; recompute from raw samples or histograms.
- Include the comparison to the baseline and the previous run, with the one variable that changed.
- Include caveats: environment differences, generator limits, warm-up handling, known noise.
- Recommendations: ranked by expected effect, with the next test to confirm each.
- Store raw artefacts (summary JSON, dashboards export, the script) with the report so the run is reproducible.
- Keep a short ethics and scope line: the environment was owned or authorised, window and approver noted.
