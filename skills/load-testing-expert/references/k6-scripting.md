# k6 Scripting

Script structure and APIs for Grafana k6 v2.3.0: lifecycle, TypeScript, HTTP, checks, groups, tags, custom metrics, data, environment variables, secrets, summaries, protocol modules and extensions. Snippets marked "run locally" were executed on v2.3.0 against a loopback server (2026-10).

## Contents

1. [Lifecycle](#1-lifecycle)
2. [TypeScript](#2-typescript)
3. [HTTP requests and batch](#3-http-requests-and-batch)
4. [Checks, groups and tags](#4-checks-groups-and-tags)
5. [Custom metrics](#5-custom-metrics)
6. [Data and parameterisation](#6-data-and-parameterisation)
7. [Environment variables and secrets](#7-environment-variables-and-secrets)
8. [Authentication, cookies and think time](#8-authentication-cookies-and-think-time)
9. [handleSummary](#9-handlesummary)
10. [Browser, gRPC and WebSocket](#10-browser-grpc-and-websocket)
11. [Extensions](#11-extensions)

## 1. Lifecycle

```js
import http from 'k6/http';

// 1. init: runs once per VU. Imports, open(), SharedArray, metric definitions.
export const options = { vus: 2, iterations: 4 };

// 2. setup: runs once before the test. Return value is passed to default and teardown.
export function setup() {
  return { startedAt: Date.now() };
}

// 3. default: runs once per iteration, per VU.
export default function (data) {
  http.get('http://localhost:8080/health');
}

// 4. teardown: runs once after the test.
export function teardown(data) {
  console.log(`ran for ${Date.now() - data.startedAt} ms`);
}

// 5. handleSummary: runs once at the end, can write files.
export function handleSummary(data) {
  return { 'summary.json': JSON.stringify(data) };
}
```

- `open()` and `SharedArray` are only available in init context, not inside `default`.
- `setup()` data must be JSON-serialisable; functions and class instances are lost.
- With scenarios, `exec` names the exported function a scenario runs instead of `default`.
- `import { vu, scenario } from 'k6/execution'` exposes the VU id, iteration counters and scenario name for per-VU logic.
- `k6 run --once script.js` runs 1 VU and 1 iteration (smoke); `--iterations N --vus M` override quickly.

## 2. TypeScript

k6 v2.3.0 runs `.ts` files directly (run locally with `k6 run test.ts`):

```ts
import http from 'k6/http';
import { check } from 'k6';
import type { Options } from 'k6/options';

export const options: Options = { vus: 1, iterations: 3 };

export default function (): void {
  const res = http.get(`${__ENV.BASE_URL}/health`);
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

- k6 transpiles types away; it does not type check. For editor support and CI checks install type definitions (`@types/k6` from npm) and run `tsc --noEmit`; check the current docs for the recommended package.
- Relative imports work between `.ts` and `.js` files. Keep imports explicit with extensions when in doubt.
- `__ENV` is available as a global; declare its type if the compiler complains.
- Older guidance about bundling with webpack or esbuild to get TypeScript is no longer required for plain scripts; bundlers remain useful for npm packages that need resolving.

## 3. HTTP requests and batch

```js
import http from 'k6/http';

const params = {
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
  tags: { name: 'POST /orders' },     // groups URLs with ids under one name
  timeout: '10s',
};

export default function () {
  const res = http.post(
    `${__ENV.BASE_URL}/orders`,
    JSON.stringify({ sku: 'A-1', qty: 1 }),
    params,
  );
  console.log(res.status, res.timings.duration, res.timings.waiting);
}
```

- Methods: `http.get`, `post`, `put`, `patch`, `del`, `head`, `options`, `request`. `http.get` takes `(url, params)`; `post` takes `(url, body, params)`.
- `res.timings` has `blocked`, `connecting`, `tls_handshaking`, `sending`, `waiting` (time to first byte), `receiving`, `duration`.
- Batch sends requests in parallel, as a browser would:

```js
const responses = http.batch([
  ['GET', `${base}/api/a`, null, { tags: { name: 'a' } }],
  ['GET', `${base}/api/b`, null, { tags: { name: 'b' } }],
]);
```

- `http.batch` also accepts an object keyed by name. Use it only when a real client issues parallel requests; otherwise sequential calls match real behaviour.
- `http.setResponseCallback(http.expectedStatuses(200, { min: 300, max: 399 }))` changes which statuses count as success for `http_req_failed`.
- Global tuning options: `discardResponseBodies`, `batch`, `batchPerHost`, `noConnectionReuse`, `userAgent`, `insecureSkipTLSVerify`, `throw`, `maxRedirects`.

## 4. Checks, groups and tags

```js
import { check, group } from 'k6';
import http from 'k6/http';

export default function () {
  group('login flow', () => {
    const res = http.post(`${__ENV.BASE_URL}/login`, JSON.stringify({ user: __ENV.USER_NAME }));
    check(res, {
      'status is 200': (r) => r.status === 200,
      'has token': (r) => typeof r.json('token') === 'string',
    });
  });
}
```

- A failed check increments the `checks` Rate metric and does not stop the iteration or change the exit code. Gate with a threshold: `checks: ['rate>0.99']`.
- `group()` adds a `group` tag (`::login flow`) and produces the `group_duration` Trend. A threshold on it is written `'group_duration{group:::login flow}': ['p(95)<2000']` (the `:::` is verified syntax: the group tag value starts with `::`). Groups are not for dynamic or async code; keep them synchronous.
- Tags: `tags` in request params, `tags` in scenarios, and `--tag name=value` for the whole run. Use `name` for route patterns. Tagged sub-metrics can carry thresholds: `'http_req_duration{journey:browse}': ['p(95)<400']`.
- Avoid high-cardinality tags (ids, timestamps); they create many series and slow outputs.
- Tag thresholds only evaluate when at least one sample has that tag; add a guard threshold on the base metric.

## 5. Custom metrics

```js
import { Counter, Gauge, Rate, Trend } from 'k6/metrics';

const orders = new Counter('orders_created');
const queueDepth = new Gauge('queue_depth');
const businessErrors = new Rate('business_errors');
const checkoutTime = new Trend('checkout_time', true); // true: values are time, shown as ms

export default function () {
  const t0 = Date.now();
  // ... perform checkout ...
  checkoutTime.add(Date.now() - t0, { step: 'total' });
  orders.add(1);
  businessErrors.add(false);   // Rate: add(true) counts a hit
  queueDepth.add(12);
}
```

- Create metrics in init context. Names must be unique and use letters, digits and underscores.
- Types: `Counter` (cumulative sum), `Gauge` (last value, min, max), `Rate` (fraction of non-zero), `Trend` (distribution with avg, min, max, med, percentiles).
- Threshold examples: `orders_created: ['count>100']`, `business_errors: ['rate<0.02']`, `checkout_time: ['p(95)<1500']`, `queue_depth: ['value<100']`.
- `summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max']` controls which statistics the end-of-test summary prints.

## 6. Data and parameterisation

```js
import { SharedArray } from 'k6/data';
import { scenario } from 'k6/execution';

const users = new SharedArray('users', function () {
  return JSON.parse(open('./data/users.json'));   // parsed once, shared read-only across VUs
});

export default function () {
  const user = users[scenario.iterationInTest % users.length];       // unique per iteration
  // or: users[Math.floor(Math.random() * users.length)]             // random pick
}
```

- `SharedArray` stores one copy in memory for all VUs; a plain top-level `JSON.parse(open(...))` duplicates the data per VU.
- The array is read-only. Use `scenario.iterationInTest` (from `k6/execution`) or `vu.idInTest` for deterministic distribution; random picks can repeat.
- For CSV, parse with the `papaparse` module from jslib (a remote import, pin the version) inside the `SharedArray` callback.
- Use enough distinct records to defeat caches; one record repeated measures the cache.
- `open()` paths are relative to the script file; with remote execution, files are bundled into the archive (`k6 archive`).

## 7. Environment variables and secrets

```bash
k6 run -e BASE_URL=https://staging.example.test -e PROFILE=load tests/load.ts
```

```js
const BASE_URL = __ENV.BASE_URL;
if (!BASE_URL) {
  throw new Error('BASE_URL is required');
}
const TOKEN = __ENV.API_TOKEN;   // supplied by the CI secret store, never committed
```

- `-e NAME=value` (or `--env`) sets variables; system environment variables are visible through `__ENV` too (`--include-system-env-vars` defaults to true in the v2.3.0 help output).
- Fail fast on missing required variables so a run never targets a default by accident.
- Do not log tokens. Do not put them in tags, URLs or `group` names, since those reach outputs.
- Prefer short-lived tokens obtained in `setup()` from a service account whose credentials come from the environment.
- k6 also has a secrets API (`secrets.get()` with secret sources, including cloud secrets with `k6 cloud run --local-execution` in v2). Check the current docs for its configuration before use.
- Options can also come from `K6_`-prefixed environment variables (for example `K6_VUS`) and a JSON config file; the precedence is CLI flags, environment, script `options`, config file. Check the docs for the exact order.

## 8. Authentication, cookies and think time

```js
import http from 'k6/http';
import { sleep } from 'k6';

export function setup() {
  const res = http.post(
    `${__ENV.BASE_URL}/auth/token`,
    JSON.stringify({ client_id: __ENV.CLIENT_ID, client_secret: __ENV.CLIENT_SECRET }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'auth' } },
  );
  return { token: res.json('access_token') };
}

export default function (data) {
  const res = http.get(`${__ENV.BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
  sleep(1 + Math.random() * 2);   // think time, 1-3 s
}
```

- Each VU has its own cookie jar, kept across iterations. Inspect with `http.cookieJar()`; clear per iteration with `jar.clear(url)` if needed. Cookies set by the server are sent automatically.
- Session login per VU: log in on the first iteration (`vu.iterationInScenario === 0`, with `import { vu } from 'k6/execution'`) and keep the token in a module-level variable (VU-local).
- OAuth refresh: for soak tests longer than the token lifetime, refresh when `Date.now()` passes the expiry.
- Think time models users reading and typing. Without it, closed-model VUs hammer the server far above human rates.
- In an arrival-rate scenario think time does not change the arrival rate; it lengthens each iteration and so needs more VUs.
- `--min-iteration-duration` paces iterations in VU-based tests.

## 9. handleSummary

```js
export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  return {
    stdout: `p95 = ${p95.toFixed(1)} ms\n`,
    'summary.json': JSON.stringify(data, null, 2),
  };
}
```

- Return an object mapping destinations (file names, `stdout`, `stderr`) to strings. When `handleSummary` is defined, the default console summary is replaced by what it returns (run locally: custom text printed, `summary.json` written).
- `textSummary` from the jslib `k6-summary` module reproduces the standard text report; it is a remote import and needs network access at start-up. Pin the version.
- `--summary-export file.json` writes a JSON summary without code, and `--summary-mode` accepts `compact`, `full` and `disabled`.
- Common uses: JUnit or HTML reports, posting a verdict to chat, saving results with run metadata (commit SHA, environment).
- The exit code is decided by thresholds, not by `handleSummary`.

## 10. Browser, gRPC and WebSocket

```js
import { browser } from 'k6/browser';

export const options = {
  scenarios: {
    ui: {
      executor: 'shared-iterations',
      options: { browser: { type: 'chromium' } },
    },
  },
};

export default async function () {
  const page = await browser.newPage();
  try {
    await page.goto(`${__ENV.BASE_URL}/`);
  } finally {
    await page.close();
  }
}
```

- `import { browser } from 'k6/browser'` loads in v2.3.0; the module needs a Chromium install on the runner. Keep browser VUs few: they are heavy. Use them to measure real rendering under protocol-level background load, and leave front-end metrics analysis to core-web-vitals-expert. v2 removed the `browser_web_vital_fid` metric in favour of `browser_web_vital_inp`.
- gRPC: `import grpc from 'k6/net/grpc'` provides `grpc.Client` (`load`, `connect`, `invoke`, `close`) and streaming support. Create the client in init context, load proto definitions with `client.load(['./proto'], 'service.proto')`, and `connect` inside the iteration. For service design questions see grpc-expert.
- WebSocket: `import ws from 'k6/websockets'` provides a browser-like `WebSocket` class (`onopen`, `onmessage`, `onclose`, `send`, `close`) that runs on the event loop. Both module imports were verified to load in v2.3.0; read the docs for the method signatures before use.
- Other built-in modules: `k6/crypto`, `k6/encoding`, `k6/html`, `k6/timers`.

## 11. Extensions

- Extensions add JavaScript modules (`k6/x/<name>`) or outputs, written in Go against `go.k6.io/k6/v2`. A custom binary is built with the xk6 tool; check the xk6 README for current `xk6 build --with` syntax.
- v2 records extension dependencies in archives and offers tab completion that can provision extension binaries; `k6 deps` lists a test's dependencies, `k6 x explore` lists official and community extensions. The `K6_BINARY_PROVISIONING` and `K6_ENABLE_COMMUNITY_EXTENSIONS` variables were removed in v2.0.0. Check the docs for the current provisioning behaviour.
- `k6/experimental/redis` was removed; use `k6/x/redis`.
- Treat extensions as untrusted code: pin versions, build in CI from reviewed sources, and keep the resulting binary out of shared images unless scanned.
- Typical needs: SQL, Kafka, Redis, MQTT, browser-like protocols, custom outputs. Check whether a built-in module covers the case first.
