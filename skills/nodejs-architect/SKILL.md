---
name: nodejs-architect
description: >-
  Designs and reviews server-side Node.js services on the current LTS lines: event loop and blocking work, async patterns with AbortSignal, streams with pipeline, worker_threads, cluster versus multiple processes, ESM and require(esm), the built-in test runner, --env-file, the permission model, native TypeScript type stripping, fetch and undici, diagnostics_channel and OpenTelemetry, graceful shutdown, memory leaks and heap snapshots, and security (path traversal, prototype pollution, ReDoS, child_process injection). Use when writing or reviewing Node.js backend code, choosing a Node version, debugging latency or memory, or hardening a Node process. Not for Express routing and middleware (use expressjs-expert) or NestJS modules and DI (use nestjs-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Node.js Architect

This skill covers the Node.js runtime as used for backend services: how the event loop schedules work, how to structure async code, streams and worker threads, how to run and shut down a process, which built-in features replace common dependencies, and which runtime-level security mistakes recur. Framework-specific guidance belongs in the framework skills.

> Verified against Node.js 26.13 "Lithium" (LTS since 2026-10-28), 24.22 "Krypton" and 22.23 "Jod" (both Maintenance), Node.js 27 (alpha), Undici 8.x, OpenTelemetry JS `@opentelemetry/sdk-node` 0.300 and `@opentelemetry/api` 1.10 (2026-10).

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

- Covered: release lines and support windows, event loop phases and blocking, promises and cancellation, streams, worker threads, cluster and multi-process deployment, ESM and CommonJS interop, type stripping, built-in test runner, environment loading, permission model, HTTP server limits, `fetch`/undici, tracing and metrics hooks, graceful shutdown, memory diagnostics, runtime security.
- Not covered: Express routing and middleware (expressjs-expert), NestJS modules, DI and pipes (nestjs-expert), REST contract design (rest-api-expert), authentication and authorization design (authentication-expert, authorization-expert), container images (docker-expert), Kubernetes probes and rollout (kubernetes-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Release lines | Even-numbered majors become LTS. 26 "Lithium" is Active LTS from 2026-10-28 (security support to 2029-04-30). 24 "Krypton" is in Maintenance since 2026-10-20 (to 2028-04-30). 22 "Jod" is in Maintenance (to 2027-04-30). 20 is end-of-life since 2026-04-30. 25 reached end-of-life in 2026-06. Node 27 is in alpha; its Current phase is scheduled for 2027-04-22 |
| New in 26 | Temporal API enabled by default, V8 14.6, Undici 8, `module.register()` runtime-deprecated, `--experimental-transform-types` removed |
| Event loop | libuv phases: timers, pending callbacks, idle/prepare, poll, check (`setImmediate`), close callbacks. `process.nextTick` and promise microtasks run between callbacks, nextTick queue first |
| Thread pool | libuv pool (default 4 threads, `UV_THREADPOOL_SIZE`) serves `fs`, `dns.lookup`, `zlib`, and async `crypto` such as `pbkdf2`, `scrypt`. Network I/O does not use it |
| Cancellation | `AbortController`, `AbortSignal.timeout(ms)`, `AbortSignal.any([...])`; accepted by `fetch`, `timers/promises`, `events.once`, `stream/promises`, `fs/promises`, `child_process`, `http` requests |
| Streams | `stream/promises` `pipeline()` propagates errors, destroys all streams and supports `signal`; `.pipe()` does neither. Web Streams are available globally and convert with `Readable.fromWeb` / `toWeb` |
| Workers | `worker_threads` run JS in separate isolates in the same process; share memory only through `SharedArrayBuffer`; `resourceLimits` caps heap per worker |
| Modules | `require(esm)` works without a flag in 20.19+ and 22.12+ for modules without top-level `await`, and is no longer experimental since 25.4; `import.meta.dirname` and `import.meta.filename` replace `__dirname` |
| TypeScript | Type stripping is on by default (22.18+, 23.6+) and stable since 24.12 and 25.2; only erasable syntax, `tsconfig.json` is ignored, files under `node_modules` are refused |
| Config | `--env-file=.env` and `--env-file-if-exists` (stable since 24.10 and 22.21); real environment variables win over file values; `--config-file` loads a JSON config |
| Permission model | `--permission` is stable (since 22.13 and 23.5) with `--allow-fs-read`, `--allow-fs-write`, `--allow-child-process`, `--allow-worker`, `--allow-addons`, `--allow-wasi`; `--allow-net` (25+) is under active development; `--permission-audit` logs instead of denying |
| Test runner | `node --test`, `node:test` (`describe`, `it`, `mock`, snapshots), `node:assert/strict`; coverage still behind `--experimental-test-coverage`; `.ts` test files are discovered when type stripping is on |
| HTTP server | `requestTimeout` defaults to 300000 ms, `headersTimeout` to 60000 ms (or `requestTimeout` if lower), `keepAliveTimeout` to 5000 ms; `server.close()` also closes idle connections since 19 |
| Observability | `diagnostics_channel` (stable) with `TracingChannel` (stable since 26.8); OpenTelemetry NodeSDK loaded with `--import` before application code |

## 3. Workflow

1. Pin the runtime: read `engines`, `.nvmrc` or the Dockerfile base image; confirm the version is a supported LTS and note which features it has (type stripping, `require(esm)`, permission flags).
2. Classify each hot path as I/O-bound, CPU-bound or memory-bound. Event loop delay (`perf_hooks.monitorEventLoopDelay`) separates the first from the other two.
3. Choose the concurrency unit: async I/O in one process by default; `worker_threads` for CPU work or parsing large payloads; extra processes (orchestrator replicas, or `cluster` on a single host) for using all cores.
4. Design cancellation first: every outbound call and long operation takes an `AbortSignal` derived from the request or a timeout.
5. Define the process lifecycle: startup validation of configuration, readiness, signal handling, drain, forced-exit timer.
6. Add telemetry through `--import` preloading so it wraps application imports.
7. Test with `node:test`; run integration tests against real dependencies where cheap.
8. Before release: heap and CPU profile under load, check shutdown under in-flight requests, run `npm audit` and lockfile review.

## 4. Decision Rules

- Version: new services start on the newest Active LTS (26); Maintenance lines (24, 22) are acceptable for existing fleets. Never run an odd-numbered or end-of-life line in production.
- CPU work over roughly 10-50 ms per call (hashing with `pbkdf2`/`scrypt` is already off-thread; image or PDF processing, big JSON or CSV parsing, compression of large buffers, regex over untrusted input) moves to a worker pool (Piscina or a hand-written pool) with bounded queue size.
- `cluster` versus processes: under an orchestrator run one process per container and scale replicas; use `cluster` (or a process manager) only on a single machine where you own the process model. Both give separate heaps, so shared state needs an external store.
- Streams versus buffers: stream when payloads can exceed a few MB or arrive incrementally; buffer small bodies and set explicit size limits.
- ESM for new code (`"type": "module"`). Keep CommonJS only where a toolchain demands it. A CommonJS file can `require()` an ESM module that has no top-level `await`.
- TypeScript: run `.ts` directly with type stripping for apps and scripts on 22.18+ if the code uses only erasable syntax (no `enum`, runtime `namespace`, parameter properties); type-check with `tsc --noEmit`. Use a build step for published libraries, decorators, `paths` aliases, or when `enum` is needed (the transform flag is gone in 26).
- Configuration: `--env-file` for local development and simple deployments; production secrets come from the platform (injected environment, mounted files), validated at startup.
- HTTP client: global `fetch` for ordinary calls. Install `undici` only when a custom `Agent`/`Pool`, interceptors or a newer version than the bundled one is needed, and then import `fetch` from that same package so dispatcher and fetch versions match.
- Permission model is defense in depth for trusted code (it is a seat belt, not a sandbox for malicious code). Use it for scripts and CLI tooling; for untrusted code use OS-level isolation.

## 5. Coding Standards

- ESM with explicit extensions in relative imports (`./db.js`, or `./db.ts` when running type-stripped code), `node:` prefix for built-ins.
- `async`/`await` everywhere; no callbacks except at API boundaries. Use `node:fs/promises`, `node:timers/promises`, `node:stream/promises`.
- Never leave a promise floating: `await` it, return it, or attach `.catch` with logging. The default for unhandled rejections is to throw; keep it.
- Concurrency over collections is bounded (a small semaphore or a pool); `Promise.all` over an unbounded array opens unbounded connections. Use `Promise.allSettled` when partial failure is acceptable.
- Pass `signal` as an option, not as a global. Create timeouts with `AbortSignal.timeout(ms)` and combine with `AbortSignal.any`.
- Errors: throw `Error` subclasses with a stable `code` and `cause` (`new Error('msg', { cause: err })`). Do not throw strings.
- Do not use synchronous `fs`, `crypto.pbkdf2Sync`, `child_process.execSync` or `JSON.parse` of untrusted large input on request paths. Sync APIs are fine during startup.
- Use `Map` and `Set` for dictionaries keyed by external input, or `Object.create(null)`.
- Use `structuredClone` for deep copies; avoid `JSON.parse(JSON.stringify(x))`.
- Format with Prettier or Biome, lint with ESLint or Biome; enable `no-floating-promises` when using typescript-eslint.

## 6. Project Structure

```
.
├── package.json              # "type": "module", "engines": { "node": ">=24" }, scripts
├── .nvmrc                    # pinned runtime for local development
├── .env.example              # variable names only; real .env is gitignored
├── tsconfig.json             # noEmit, erasableSyntaxOnly, verbatimModuleSyntax
├── src/
│   ├── instrumentation.ts    # OpenTelemetry bootstrap, preloaded with --import
│   ├── main.ts               # composition root: config, wiring, listen, signals
│   ├── config.ts             # reads and validates process.env once
│   ├── server.ts             # HTTP server factory, timeouts, shutdown
│   ├── lib/                  # small shared utilities (safe-path, pool, logger)
│   ├── modules/<feature>/    # routes, service, repository per feature
│   └── workers/              # worker entry points (CPU-bound tasks)
└── test/                     # *.test.ts run by node --test
```

## 7. Design Patterns

- **Composition root**: `main.ts` builds config, clients and servers and passes them down; modules receive dependencies, they do not import singletons that read `process.env`.
- **Pipeline**: `pipeline(source, ...transforms, destination, { signal })` for file, network and compression flows; async generators as transform stages.
- **Worker pool**: a fixed set of long-lived workers behind `pool.run(task, { signal })` with a bounded queue and per-task timeout.
- **Request context**: `AsyncLocalStorage` carries request id and trace context to logs without threading parameters.
- **Supervisor/drain**: a single shutdown function that stops accepting work, waits for in-flight work with a deadline, closes pools and clients in reverse order, then exits.
- **Circuit breaker and retry with jitter** for flaky dependencies, with every retry bounded by the same overall `AbortSignal`.
- **Outbox/idempotency keys** when work must survive restarts (queue consumers, webhooks); deep treatment belongs to system-design-expert.

## 8. Best Practices

- Validate configuration at startup and fail fast with a readable message; keep the parsed object immutable.
- Log structured JSON to stdout with a request id; redact secrets and tokens at the logger (Pino `redact`).
- Set explicit server limits: `server.requestTimeout`, `headersTimeout`, `keepAliveTimeout` larger than the load balancer idle timeout, `maxHeaderSize` default is 16 KiB, body size limits in the parser.
- Prefer Node built-ins over packages when equal: `fetch`, `node:test`, `--watch`, `--env-file`, `util.parseArgs`, `util.styleText`, `crypto.randomUUID`, `fs.glob`, `structuredClone`, `AbortSignal.timeout`.
- Run the process as a non-root user, one process per container, with `node` as PID 1 only if signals are handled, or use an init (`docker run --init`).
- Keep `package-lock.json` committed, install with `npm ci`, and review install scripts of new dependencies (`npm config set ignore-scripts true` for CI jobs that do not need them).
- Use `process.getBuiltinModule()` only for code that must run in both Node and other runtimes.

## 9. Performance

- Measure first: `--cpu-prof`, `--heap-prof`, `node --inspect`, `perf_hooks.monitorEventLoopDelay()`, `performance.eventLoopUtilization()`. An event loop delay p99 above tens of milliseconds means something blocks.
- Avoid blocking: large `JSON.parse`/`stringify`, synchronous regex on long strings, `fs.*Sync`, big `Array.sort`, template rendering. Chunk the work (yield with `setImmediate`) or move it to a worker.
- Keep-alive: reuse HTTP connections (undici does by default); size pools (database, HTTP agents) to the downstream limit divided by process count.
- Bound memory: stream, set `highWaterMark` deliberately, use `Buffer.allocUnsafe` only when the buffer is fully overwritten.
- Set heap relative to the container: `--max-old-space-size-percentage` or an explicit `--max-old-space-size` below the container limit (leave room for buffers, stacks and native memory).
- Tune `UV_THREADPOOL_SIZE` only when profiling shows fs, zlib or crypto calls queuing; set it in the environment before start.
- `cluster` uses round-robin distribution on all platforms except Windows; uneven load usually comes from long-lived connections pinned to one worker.
- Details and measurement recipes: [references/event-loop-and-performance.md](references/event-loop-and-performance.md).

## 10. Security

- **Path traversal**: never join user input onto a base path directly. Resolve against the root with `path.resolve`, compute `path.relative(root, candidate)`, reject results that are empty, equal `..`, start with `..` plus a separator, or are absolute; then `realpath` and check again to defeat symlinks. Reject NUL bytes. Prefer opaque ids mapped to files over user-supplied names (example in section 14).
- **child_process**: use `execFile`/`spawn` with an argument array and `shell: false`; never interpolate input into a command string; allowlist executables and options; on Windows, running `.bat`/`.cmd` requires a shell, so avoid spawning them from user input.
- **Prototype pollution**: do not merge untrusted objects recursively into plain objects; use `Map`, `Object.create(null)`, schema validation that strips unknown keys, and `Object.hasOwn`. `--disable-proto=delete` removes `Object.prototype.__proto__`; treat it as hardening, not a fix.
- **ReDoS**: avoid nested quantifiers and ambiguous alternation on user input; cap input length before matching; run untrusted patterns in a worker with a deadline or use a linear-time engine such as the `re2` package.
- **Dynamic code**: no `eval`, `new Function`, or `vm` as a sandbox (`vm` is not a security boundary).
- **Secrets**: read from the environment or mounted files, never log them, never commit `.env`; `--env-file` values are visible to child processes through `process.env`.
- **Permission model**: `node --permission --allow-fs-read=/app --allow-fs-write=/tmp/app` restricts a trusted process; `fs` access, child processes, workers, addons and (newer lines) network need explicit grants. It does not protect against malicious code.
- **Supply chain**: lockfile, `npm ci`, `npm audit signatures`, pinned versions for critical packages, no `postinstall` surprises, provenance checks.
- **HTTP**: set request, header and body limits; reject unexpected content types; behind a proxy configure trust explicitly (do not trust `X-Forwarded-*` from clients); keep Node patched, since runtime CVEs are fixed in security releases of every supported line.
- **Outbound requests**: validate and resolve destinations before fetching user-supplied URLs (SSRF): block private, loopback and link-local ranges after DNS resolution, disable redirects or revalidate each hop, set timeouts and a response size cap.
- Wider API concerns: api-security-expert and secure-coding-expert.

## 11. Testing

- `node --test` discovers `*.test.{js,mjs,cjs}` and, with type stripping, `*.test.{ts,mts,cts}` plus files under `test/`. Use `describe`/`it` or flat `test()`.
- Use `node:assert/strict`; `t.mock.fn()`, `t.mock.method()`, `mock.module()` (early development) and `t.mock.timers` for deterministic time.
- Coverage: `node --test --experimental-test-coverage` (experimental; the flag name may change). Reporters: `--test-reporter=spec|tap|junit|lcov` with `--test-reporter-destination`.
- Run serial integration suites with `--test-concurrency=1` when they share a database or port; use port `0` and read the assigned port.
- Always close servers, pools and timers in `after()` hooks; leaked handles keep the runner alive. `server.close()` plus `closeAllConnections()` for HTTP servers.
- Test shutdown: start the server, open a slow request, send `SIGTERM` to a child process, assert the response completes and the exit code is 0.
- Frameworks such as Vitest or Jest remain fine for large codebases; choose by ecosystem needs (mocks, snapshots, watch UI), not by default.

## 12. Review Checklist

- [ ] Runtime version is a supported LTS and is pinned (`engines`, `.nvmrc`, base image tag).
- [ ] No synchronous or CPU-heavy work on request paths; heavy work is in workers with bounded queues.
- [ ] Every outbound call and long operation receives an `AbortSignal` with a timeout.
- [ ] No floating promises; unhandled rejections are not suppressed.
- [ ] Streams use `pipeline()` with error handling; no unbounded buffering of request or response bodies.
- [ ] Server timeouts, body limits and header limits are set; `keepAliveTimeout` exceeds the load balancer idle timeout.
- [ ] `SIGTERM`/`SIGINT` handled once, drain with deadline, forced-exit timer unref'd.
- [ ] Configuration validated at startup; no secrets in logs or the repository.
- [ ] File paths from users are normalized and checked against a root; `child_process` uses argument arrays.
- [ ] Untrusted objects are not merged into plain objects; regexes on untrusted input are bounded.
- [ ] Telemetry preloaded with `--import`; request id propagates to logs.
- [ ] Tests close all handles; CI runs on the production Node line.

## 13. Production Notes

- Readiness and liveness are different: liveness should not depend on downstream services; readiness flips to failing at the start of shutdown so the load balancer drains first.
- Shutdown sequence: mark not ready, wait a short grace period for endpoint removal, `server.close()`, wait for in-flight requests, close queues and database pools, flush telemetry (`sdk.shutdown()`), exit. Set the orchestrator grace period above your internal deadline.
- Node does not restart itself; rely on the orchestrator or process manager. After `uncaughtException` the process state is undefined: log and exit.
- Memory leaks: watch RSS and heap used over days. Use `--heapsnapshot-signal=SIGUSR2` or `v8.writeHeapSnapshot()` (blocks the main thread and needs memory roughly equal to the heap) and diff two snapshots in Chrome DevTools; `--heapsnapshot-near-heap-limit=N` captures before an out-of-memory crash. Common retainers: unbounded caches or maps, listeners added per request, closures holding request objects, uncleared timers.
- Diagnostic report: `--report-on-signal` and `--report-uncaught-exception` write JSON reports for hangs and crashes.
- When behind a CDN or proxy, tune `keepAliveTimeout` and `headersTimeout` together to avoid sporadic 502s from reused sockets.
- Upgrade path: move one LTS at a time, run the test suite on the target line in CI first, and read the deprecations list for removed APIs.
- Details on streams, workers and cluster: [references/streams-and-workers.md](references/streams-and-workers.md); module, TypeScript, permission and test-runner specifics: [references/runtime-features.md](references/runtime-features.md).

## 14. Examples

Graceful shutdown with a deadline (HTTP server; add pools and telemetry flush where marked):

```ts
import { createServer } from 'node:http';

const server = createServer((req, res) => {
  res.end('ok');
});
server.requestTimeout = 30_000;
server.headersTimeout = 10_000;
server.keepAliveTimeout = 65_000; // above a typical 60 s load balancer idle timeout

let shuttingDown = false;

async function shutdown(signal: NodeJS.Signals): Promise<void> {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(JSON.stringify({ msg: 'shutdown', signal }));

  const forced = setTimeout(() => process.exit(1), 25_000);
  forced.unref();

  await new Promise<void>((resolve, reject) => {
    server.close((err) => (err ? reject(err) : resolve())); // stops accepting and closes idle sockets
  });
  // await pool.close(); await db.end(); await sdk.shutdown();
}

for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => {
    shutdown(signal).then(
      () => process.exit(0),
      (err) => { console.error(err); process.exit(1); },
    );
  });
}

server.listen(Number(process.env.PORT ?? 3000));
```

Path traversal defense (validate lexically, then after resolving symlinks):

```ts
import { realpath } from 'node:fs/promises';
import path from 'node:path';

function isOutside(rel: string): boolean {
  return rel === '' || rel === '..' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel);
}

export async function resolveInside(root: string, userPath: string): Promise<string> {
  if (userPath.includes('\0')) throw new RangeError('invalid path');
  const candidate = path.resolve(root, userPath);
  if (isOutside(path.relative(root, candidate))) throw new RangeError('path escapes root');
  const [real, realRoot] = await Promise.all([realpath(candidate), realpath(root)]);
  if (isOutside(path.relative(realRoot, real))) throw new RangeError('path escapes root');
  return real; // still open with care: a race between check and use is possible for writable roots
}
```

OpenTelemetry bootstrap, preloaded so it patches modules before the application imports them:

```ts
// src/instrumentation.ts
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';

// Exporter, endpoint and service name come from OTEL_* environment variables
// (OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, ...).
const sdk = new NodeSDK({ instrumentations: [getNodeAutoInstrumentations()] });
sdk.start();

process.once('SIGTERM', () => { void sdk.shutdown(); });
```

```bash
node --env-file-if-exists=.env --import ./src/instrumentation.ts ./src/main.ts
```

ESM applications may also need the OpenTelemetry loader hook (`--experimental-loader=@opentelemetry/instrumentation/hook.mjs`); read the OpenTelemetry JS ESM support document before relying on auto-instrumentation.

## 15. Common Mistakes

- **Blocking the loop with "just a little" sync work**: a 200 ms `JSON.parse` stalls every connection. Measure event loop delay and offload.
- **`Promise.all` over thousands of items**: opens thousands of sockets or queries at once. Limit concurrency.
- **`.pipe()` without error handlers**: leaks file descriptors when a stream errors. Use `pipeline()`.
- **No timeout on `fetch`**: a stalled upstream holds the request forever. Pass `AbortSignal.timeout(ms)`.
- **Ignoring non-2xx from `fetch`**: it only rejects on network errors. Check `res.ok` and consume or cancel the body so the connection returns to the pool.
- **`process.exit()` in libraries or right after `server.close()`**: cuts in-flight responses. Let the event loop drain; exit from the top level only.
- **Handling `SIGTERM` with `process.on` repeatedly**: duplicate shutdowns. Use `once` and a guard flag.
- **`__dirname` in ESM**: undefined. Use `import.meta.dirname`.
- **Enum, parameter properties or `paths` aliases with type stripping**: `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` or unresolved imports. Use erasable syntax, subpath imports (`#internal/*`), or a build step.
- **Importing a type without `import type`** under type stripping: the import is kept and fails at run time. Enable `verbatimModuleSyntax`.
- **Trusting `path.join(root, userInput)`**: `..` segments escape the root. Use the resolve-and-check pattern.
- **Shell strings for `exec`**: command injection. Use `execFile` with an array.
- **Merging request JSON into config objects**: prototype pollution. Validate and copy known keys.
- **Mixing a separately installed `undici` dispatcher with global `fetch`**: version mismatches cause confusing errors. Import `fetch` from the same `undici`.
- **Unbounded in-memory caches and per-request listeners**: slow heap growth that only shows in production. Bound caches and remove listeners.
- **Relying on `--permission` against untrusted code**: it is not a sandbox.

## 16. References

- [references/event-loop-and-performance.md](references/event-loop-and-performance.md): event loop phases and ordering, blocking diagnosis, thread pool, profiling, heap snapshots and leak hunting, HTTP server tuning, `fetch`/undici.
- [references/streams-and-workers.md](references/streams-and-workers.md): streams and `pipeline`, backpressure, Web Streams interop, `worker_threads`, worker pools, `SharedArrayBuffer`, `cluster` versus processes, `child_process` safety.
- [references/runtime-features.md](references/runtime-features.md): ESM and `require(esm)`, type stripping, `--env-file`, permission model, test runner, `diagnostics_channel`, OpenTelemetry.
- Official docs: https://nodejs.org/api/ , https://nodejs.org/en/about/previous-releases , https://nodejs.org/en/learn/ , https://github.com/nodejs/Release , https://undici.nodejs.org/ , https://opentelemetry.io/docs/languages/js/
