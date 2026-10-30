# Event Loop and Performance

Reference for how Node.js schedules work, how to find and remove blocking code, how to profile CPU and memory, and how to tune the HTTP server and client. Verified against Node.js 26.13 LTS, 24.22 and 22.23, Undici 8.12 (Node 22.19+ required by the standalone package) (2026-10).

## 1. Event loop phases and ordering

libuv runs these phases in a loop; each phase has a FIFO queue of callbacks:

1. **timers**: `setTimeout` and `setInterval` callbacks whose threshold has passed.
2. **pending callbacks**: deferred system-level callbacks (some TCP errors).
3. **idle, prepare**: internal.
4. **poll**: retrieves new I/O events and runs their callbacks; blocks here when nothing else is scheduled.
5. **check**: `setImmediate` callbacks.
6. **close callbacks**: `'close'` events such as `socket.destroy()`.

Between every callback, Node drains `process.nextTick` callbacks and then promise microtasks (`queueMicrotask`, `.then`). A timer threshold is a minimum, not a guarantee: a busy loop delays every timer.

Observed ordering (run it on your target version):

```js
import { readFile } from 'node:fs';
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));
process.nextTick(() => console.log('nextTick'));
Promise.resolve().then(() => console.log('promise'));
readFile(import.meta.filename, () => {
  setTimeout(() => console.log('io: timeout'), 0);
  setImmediate(() => console.log('io: immediate'));
});
console.log('sync');
```

- In an ES module the output starts `sync, promise, nextTick`, because module evaluation itself runs inside a promise job, so the microtask queue drains before the nextTick queue. In a CommonJS file it starts `sync, nextTick, promise`. Do not depend on the relative order of `nextTick` and promises across module systems.
- `timeout` versus `immediate` from the main module depends on process performance and can vary between runs.
- Inside an I/O callback, `setImmediate` always runs before a `setTimeout(0)`.
- A recursive `process.nextTick` or a never-ending microtask chain starves I/O. Use `setImmediate` to yield between chunks of a long job.

## 2. Finding blocking work

Symptoms: p99 latency spikes for unrelated endpoints, health checks timing out, timers firing late.

```js
import { monitorEventLoopDelay, performance } from 'node:perf_hooks';

const delay = monitorEventLoopDelay({ resolution: 20 });
delay.enable();
let last = performance.eventLoopUtilization();

setInterval(() => {
  const now = performance.eventLoopUtilization();
  const { utilization } = performance.eventLoopUtilization(now, last);
  last = now;
  console.log(JSON.stringify({
    msg: 'event-loop',
    delayP99Ms: delay.percentile(99) / 1e6,
    delayMaxMs: delay.max / 1e6,
    utilization,
  }));
  delay.reset();
}, 10_000).unref();
```

- `monitorEventLoopDelay` reports a histogram in nanoseconds. Export p99 and max as metrics and alert on sustained growth.
- `eventLoopUtilization()` is the fraction of time the loop was busy; sustained values near 1 mean the process is saturated and more instances or offloading is needed.
- Find the culprit with a CPU profile (section 4). Typical offenders: `JSON.parse`/`stringify` of multi-MB bodies, synchronous regex on long input, large sorts, template rendering, synchronous `fs` or `crypto` calls, tight loops over big arrays, logging of large objects.
- Fix options in order of cost: stream or paginate the data, chunk the work and yield with `setImmediate`, move it to a worker (see streams-and-workers.md), or move it to another service.

## 3. The libuv thread pool

- Default size is 4 threads; set `UV_THREADPOOL_SIZE` in the environment before the process starts (changing `process.env` at run time is not guaranteed to take effect).
- Used by: `fs` operations, `dns.lookup` (`getaddrinfo`), `zlib`, and CPU-heavy `crypto` functions such as `pbkdf2`, `scrypt`, `randomBytes`.
- Not used by: TCP/UDP sockets, `fetch` network I/O, `dns.resolve*` (c-ares).
- Symptoms of exhaustion: many concurrent password hashes or file reads make unrelated `fs` or DNS calls slow. Raise the size moderately or move hashing into a dedicated worker pool, and cap concurrent hashes with a semaphore.

## 4. Profiling

| Goal | Tool |
|---|---|
| CPU hot spots | `node --cpu-prof app.js` writes a `.cpuprofile` on exit; open it in Chrome DevTools (Performance/Profiler) |
| Allocation sites | `node --heap-prof app.js` writes a `.heapprofile` (sampling) |
| Live inspection | `node --inspect=127.0.0.1:9229 app.js`; never expose the inspector port beyond localhost or an SSH tunnel |
| Trace GC | `node --trace-gc app.js` |
| Reports on hang or crash | `--report-on-signal`, `--report-uncaught-exception` write a JSON diagnostic report |
| Custom timing | `performance.mark()`, `performance.measure()`, `PerformanceObserver` |

Profile under realistic load with production-like data; a profile of an idle process shows nothing. Compare before and after each change with the same load script.

## 5. Memory and heap snapshots

Layout: V8 heap (young and old generation), plus off-heap memory (Buffers, native addons, stacks). `process.memoryUsage()` reports `rss`, `heapTotal`, `heapUsed`, `external`, `arrayBuffers`. A leak shows as `heapUsed` after garbage collection trending up over hours or days.

Capturing snapshots:

```bash
# write a snapshot when SIGUSR2 arrives
node --heapsnapshot-signal=SIGUSR2 app.js
kill -USR2 <pid>

# write up to 3 snapshots as the heap approaches its limit (no longer experimental in 24.13.1, 22.22.1 and 25.4+)
node --max-old-space-size=512 --heapsnapshot-near-heap-limit=3 app.js
```

```js
import v8 from 'node:v8';
const file = v8.writeHeapSnapshot(); // blocking, writes Heap-<timestamp>.heapsnapshot in the working directory
```

Procedure:

1. Take snapshot A after warm-up, run the suspected workload for a while, take snapshot B (and C).
2. Load them in Chrome DevTools Memory tab; use the Comparison view between A and B to see which constructors grew.
3. Open retainers of a growing object to see what holds it: a module-level `Map`, an event emitter listener array, a closure over a request, a timer.
4. Fix, redeploy, and compare the heap trend.

Notes: taking a snapshot pauses the main thread and needs roughly the heap size in extra memory, so capture on one instance behind the load balancer, not on all. Snapshots contain secrets present in memory; treat the files as sensitive.

Typical leak sources:

- Unbounded `Map`/array caches (use an LRU with a maximum size and TTL).
- `emitter.on` inside a request handler without `off`; the `MaxListenersExceededWarning` is an early signal.
- Timers or intervals not cleared (`unref()` background timers).
- Closures that capture large request or response objects and are stored globally.
- Buffers sliced from a large pooled `Buffer` that retain the parent.

Container sizing: set the V8 old-space limit below the container memory limit (explicit `--max-old-space-size=<MB>` or `--max-old-space-size-percentage=<n>`), leaving room for external memory, thread stacks and the runtime.

## 6. HTTP server tuning

```js
import { createServer } from 'node:http';

const server = createServer(handler);
server.requestTimeout = 30_000;   // whole request must arrive within this (default 300000)
server.headersTimeout = 10_000;   // default: min(60000, requestTimeout)
server.keepAliveTimeout = 65_000; // default 5000; keep above the load balancer idle timeout
server.maxRequestsPerSocket = 0;  // 0 = unlimited
```

- Defaults are generous; lower them for public endpoints to limit slow-request resource use.
- When a load balancer reuses connections longer than `keepAliveTimeout`, the server may close a socket as the balancer sends a request on it, which appears as sporadic 502 or connection reset errors. Set Node's value above the balancer's idle timeout.
- `server.close()` stops accepting connections and closes idle ones (since Node 19); `server.closeIdleConnections()` and `server.closeAllConnections()` are available for explicit control; use `closeAllConnections()` only after the drain deadline.
- Enforce body size limits in the framework or by counting bytes on the request stream; the default maximum header size is 16 KiB (`--max-http-header-size`).
- Respect backpressure when writing large responses: use `pipeline(readable, res)`.
- Use `AbortSignal` from the incoming request lifecycle (for example, listen for `req.on('close')` or use `res.on('close')`) to cancel downstream work when the client disconnects.

## 7. fetch and undici

- Global `fetch`, `Headers`, `Request`, `Response`, `FormData` and `WebSocket` come from the bundled Undici (8.x in Node 26).
- Always bound requests: `fetch(url, { signal: AbortSignal.timeout(5000) })`.
- `fetch` resolves on HTTP errors; check `res.ok`. Read the body (`await res.arrayBuffer()`, `res.json()`) or cancel it (`await res.body?.cancel()`) so the connection returns to the pool.
- Proxy support: set `NODE_USE_ENV_PROXY=1` (or `--use-env-proxy`) with `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` for `fetch` and `http`/`https` clients on versions that document it; check the CLI docs for your line.
- Custom pooling or timeouts need the `undici` package:

```js
import { Agent, fetch } from 'undici';

const agent = new Agent({
  connections: 50,          // max sockets per origin
  keepAliveTimeout: 10_000,
  headersTimeout: 10_000,
  bodyTimeout: 30_000,
});

const res = await fetch('https://api.example.com/items', {
  dispatcher: agent,
  signal: AbortSignal.timeout(15_000),
});
if (!res.ok) throw new Error(`upstream ${res.status}`, { cause: await res.text() });
const items = await res.json();
```

- Import `fetch` from `undici` when you pass a `dispatcher` from that package, so both come from the same version. Mixing the global `fetch` with a dispatcher from a different Undici version can fail in confusing ways.
- Retries need idempotency awareness: retry only safe/idempotent requests, with exponential backoff and jitter, and share one overall deadline through a single `AbortSignal`.

## 8. Async patterns

Bounded concurrency without a dependency:

```js
export async function mapLimit(items, limit, fn, signal) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      signal?.throwIfAborted();
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}
```

- `Promise.all` rejects on the first failure and leaves the rest running; pass the same `signal` into each task so they stop. `Promise.allSettled` collects every outcome; `Promise.any` resolves on the first success; `Promise.withResolvers()` creates a promise with exposed resolve/reject functions.
- `AbortSignal.timeout(ms)` aborts with a `TimeoutError` `DOMException`; `AbortSignal.any([a, b])` aborts when any input aborts; `signal.throwIfAborted()` checks inside loops; check `signal.reason`.
- `events.once(emitter, 'ready', { signal })` and `timers/promises` `setTimeout(ms, value, { signal })` are cancellable.
- `AsyncLocalStorage` (`node:async_hooks`, stable) propagates request-scoped data (request id, trace span) across awaits:

```js
import { AsyncLocalStorage } from 'node:async_hooks';
export const requestContext = new AsyncLocalStorage();
// server entry: requestContext.run({ requestId }, () => handle(req, res));
// logger: requestContext.getStore()?.requestId
```

- Unhandled promise rejections terminate the process by default (`--unhandled-rejections=throw`). Handle `process.on('unhandledRejection')` only to log and exit, never to continue.
- Event emitters: an `'error'` event with no listener throws. Attach error listeners or use `pipeline`/`finished` from `stream/promises`.

## 9. Measuring changes

- Load test with a fixed tool and script (`autocannon`, `k6`, `wrk`); record throughput, p50/p95/p99, event loop delay and memory.
- Change one thing at a time, run each variant for several minutes after warm-up (JIT compilation affects the first seconds).
- Use the same Node version and container limits as production.
