# Locust

Python-based load testing with Locust 2.47.0 (PyPI, installed into a fresh virtual environment on Python 3.13; a headless run against a local server was executed and the CLI flags below were read from `locust --help`, 2026-10). Locust suits teams that prefer Python for scripting user behaviour; k6 is the main tool in this skill.

## Contents

1. [When to choose Locust](#1-when-to-choose-locust)
2. [A minimal locustfile](#2-a-minimal-locustfile)
3. [Users, tasks and wait times](#3-users-tasks-and-wait-times)
4. [Running headless](#4-running-headless)
5. [Distributed mode](#5-distributed-mode)
6. [Thresholds and CI](#6-thresholds-and-ci)
7. [Performance and limits](#7-performance-and-limits)
8. [Locust versus k6](#8-locust-versus-k6)

## 1. When to choose Locust

- The team writes Python and wants to reuse client libraries, data generators or internal SDKs in the load script.
- The workload is easier to express as stateful user behaviour with plain Python code than as a JavaScript script.
- A web UI for live control during exploratory runs is useful (Locust serves one by default).
- Choose k6 when you need arrival-rate (open model) executors with built-in thresholds and exit codes, very high request rates per generator, or Grafana Cloud integration.
- Locust spawns users at a given rate and each user loops through tasks with waits: it is a closed model by default. Constant-throughput and pacing helpers exist (`constant_throughput`, `constant_pacing`), but check the docs for how they interact with user counts before using them to emulate an arrival rate.

## 2. A minimal locustfile

```python
import os

from locust import HttpUser, between, task


class ShopUser(HttpUser):
    wait_time = between(1, 3)          # think time in seconds between tasks

    def on_start(self) -> None:
        # runs once per simulated user: log in, fetch a token from the environment
        token = os.environ["API_TOKEN"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)                            # weight: 5 of every 7 task runs
    def browse(self) -> None:
        self.client.get("/items", name="GET /items")

    @task(2)
    def view_item(self) -> None:
        item_id = 42
        with self.client.get(
            f"/items/{item_id}", name="GET /items/:id", catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"unexpected status {resp.status_code}")
            elif "id" not in resp.json():
                resp.failure("missing id in body")
```

- `self.client` is a `requests`-based session that records timing for each request; `name=` groups URLs with ids so statistics do not explode in cardinality.
- `catch_response=True` lets the task mark a response as failed or successful based on content, like a k6 check.
- Credentials come from environment variables, never from the file.
- `host` can be set on the class or with `-H`/`--host` at run time. Keep it explicit so a run never targets a default by accident.

## 3. Users, tasks and wait times

- `HttpUser` simulates one client with an HTTP session. `User` is the base class for non-HTTP protocols (write your own client and fire request events), and `FastHttpUser` uses a faster HTTP client for higher per-process throughput.
- `@task` marks a method as a task; `@task(n)` sets a weight. `TaskSet` and `SequentialTaskSet` group tasks into ordered flows. Plain methods with explicit calls are often clearer than nested task sets.
- `wait_time` options: `between(min, max)`, `constant(seconds)`, `constant_pacing(seconds)` (fixed cycle time), `constant_throughput(tasks_per_second)`.
- `on_start` and `on_stop` run when a user begins and ends; use them for login and cleanup.
- `@tag("smoke")` on tasks plus `--tags smoke` selects subsets at run time (check `locust --help` for `--tags` and `--exclude-tags`).
- Multiple user classes in one file are allowed; `weight` on a class sets the mix of user types, and `--class-picker` exposes a selection box in the web UI.
- Stop a user early with `self.environment.runner.quit()` or `raise StopUser()` from `locust.exception`.
- Share read-only data at module level; per-user data from a queue or a counter keyed to users avoids repeating a single record.
- Events: `from locust import events` provides hooks such as `events.test_start`, `events.test_stop` and `events.quitting`. A quit hook can set `environment.process_exit_code` to enforce thresholds (see section 6).

## 4. Running headless

```bash
locust -f locustfile.py --headless -u 100 -r 10 -t 15m -H https://staging.example.test \
  --csv results/run1 --html results/run1.html
```

Flags confirmed in the 2.47.0 help output:

| Flag | Meaning |
|---|---|
| `-f`, `--locustfile` | Path to the locustfile |
| `-H`, `--host` | Base URL of the target |
| `-u`, `--users` | Peak number of concurrent users |
| `-r`, `--spawn-rate` | Users started per second |
| `-t`, `--run-time` | Stop after this time (for example `30s`, `15m`, `2h`); needs `--headless` or `--autostart` |
| `--headless` | No web UI, start immediately |
| `--autostart` | Start immediately but keep the web UI |
| `--autoquit <seconds>` | Quit this many seconds after the run ends (with the web UI) |
| `--csv <prefix>` | Write request statistics CSV files |
| `--csv-full-history` | Also write time-series statistics |
| `--html <file>` | Write an HTML report |
| `--exit-code-on-error <int>` | Exit code to use when there are failed requests |
| `--processes <n>` | Fork n worker processes on one machine |
| `--class-picker` | Select user classes in the web UI |

- Run `locust --help` on the installed version for the full list (tags, logging, stop timeout, web UI options).
- The end-of-run table prints request counts, failures and response-time percentiles (50 to 99.99 percent) per name and an aggregate row; the test above showed these for 58 requests against a local server.
- Spawn rate is how fast users are added; with `-u 100 -r 10` it takes about 10 seconds to reach peak. Treat that ramp as warm-up and exclude it when reading results if the SLO covers steady state.

## 5. Distributed mode

```bash
# one coordinator
locust -f locustfile.py --master --headless -u 2000 -r 50 -t 20m --expect-workers 4 -H https://staging.example.test

# on each generator machine
locust -f locustfile.py --worker --master-host <master-address>
```

- `--master` coordinates and aggregates; `--worker` generates load and connects to `--master-host` (and `--master-port`, default 5557 in the docs; check the version in use). `--master-bind-host` and `--master-bind-port` control the coordinator's listener.
- `--expect-workers N` makes a headless master wait for N workers before starting; `--expect-workers-max-wait` caps that wait.
- Every worker needs the same locustfile and data. Ship files with the image or a shared volume and pin the Locust version on all nodes.
- On one machine, `--processes N` forks N workers (use `-1` for one per core; check the help text of the installed version) and avoids the single-core limit of Python.
- Restrict network access to the master port to the generator network; the master and worker protocol is not for public exposure.
- On Kubernetes, run the master and workers as a Deployment pair with a Service for the master; Helm charts exist, so review any chart before using it.

## 6. Thresholds and CI

Locust has no built-in threshold language; enforce SLOs in a quit hook:

```python
from locust import events


@events.quitting.add_listener
def enforce_slo(environment, **kwargs):
    stats = environment.stats.total
    if stats.fail_ratio > 0.01:
        environment.process_exit_code = 1
        print("FAIL: error ratio above 1 percent")
    elif stats.get_response_time_percentile(0.95) > 500:
        environment.process_exit_code = 1
        print("FAIL: p95 above 500 ms")
```

- A non-zero `process_exit_code` fails the CI step. `--exit-code-on-error` covers the simple "any failure" case.
- GitHub Actions: set up Python, install Locust from a pinned requirements file (hash-checked if possible), run headless with `-t 2m`, upload `--csv` and `--html` outputs as artefacts. Pass secrets through `env:` like the k6 workflow in the CI reference.
- Pin Locust and its dependencies in `requirements.txt` so results compare across runs.

## 7. Performance and limits

- Locust runs on gevent; one process uses one core. Use `--processes` or workers to scale; watch generator CPU, as above 90 percent timings become unreliable.
- `FastHttpUser` raises throughput per process but supports fewer `requests` features; test that your authentication and cookie handling work with it.
- Avoid blocking calls (CPU loops, synchronous database drivers) inside tasks; they block the gevent loop for every user in that process.
- Closed-model behaviour applies: if the server slows, each user waits longer and the offered rate falls. See the open versus closed discussion in the scenarios reference.
- For very high request rates or arrival-rate shaping, k6 is generally the better tool; Locust load shapes (`LoadTestShape`) can script user count over time but still drive users, not arrivals.

## 8. Locust versus k6

| Aspect | k6 | Locust |
|---|---|---|
| Script language | JavaScript or TypeScript | Python |
| Workload model | Open and closed executors | Closed (users with waits); shapes for ramps |
| Pass/fail gates | Built-in thresholds, exit code 99 | Custom code in quit hook, exit code |
| Live UI | Optional web dashboard output | Built-in web UI |
| Distributed | k6-operator, Grafana Cloud | Master and workers, `--processes` |
| Protocols | HTTP, gRPC, WebSocket, browser, extensions | HTTP built in; others via custom clients |
| Resource use per request | Low (Go runtime) | Higher (Python), mitigated by `FastHttpUser` |

- The same safety rules apply: only target systems you own or are authorised to test, and never point either tool at third-party production.
