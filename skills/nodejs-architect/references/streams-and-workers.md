# Streams and Workers

Reference for stream composition and backpressure, Web Streams interop, `worker_threads` and worker pools, `cluster` versus multiple processes, and safe use of `child_process`. Verified against Node.js 26.13 LTS, 24.22 and 22.23, Piscina 5.3 (2026-10).

## 1. Streams with pipeline

Use `pipeline` from `node:stream/promises`. It connects the streams, forwards errors, destroys every stream on failure or abort, and resolves when the destination finishes. `.pipe()` does none of the cleanup and silently loses errors.

```js
import { createReadStream, createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { createGzip } from 'node:zlib';

try {
  await pipeline(
    createReadStream('access.log'),
    createGzip(),
    createWriteStream('access.log.gz'),
    { signal: AbortSignal.timeout(60_000) },
  );
} catch (err) {
  if (err.name === 'AbortError' || err.name === 'TimeoutError') {
    // cancelled or too slow; partial output file should be removed by the caller
  }
  throw err;
}
```

Notes:

- On failure the destination file is left partially written; write to a temporary name and rename on success.
- `pipeline` accepts async generator functions as transform stages; they take an async iterable and yield chunks:

```js
import { createReadStream, createWriteStream } from 'node:fs';
import { createInterface } from 'node:readline';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';

async function* upper(source) {
  for await (const line of source) yield `${line.toUpperCase()}\n`;
}

const lines = createInterface({ input: createReadStream('in.txt'), crlfDelay: Infinity });
await pipeline(Readable.from(lines), upper, createWriteStream('out.txt'));
```

- `stream.finished(stream)` (promise form in `stream/promises`) waits for end or error of a single stream; `stream.compose()` builds a duplex from several streams (check the docs for its stability on your line).
- `Readable.from(iterable)` turns arrays, generators and async iterables into readable streams.

## 2. Backpressure

- `writable.write(chunk)` returns `false` when the internal buffer exceeds `highWaterMark`. Stop writing until `'drain'` is emitted. `pipeline` and `for await ... of readable` do this automatically.
- Default `highWaterMark` for byte streams is 64 KiB on non-Windows platforms (16 KiB on Windows); 16 objects in object mode.
- Manual loop:

```js
import { once } from 'node:events';

for (const chunk of chunks) {
  if (!writable.write(chunk)) await once(writable, 'drain');
}
writable.end();
await once(writable, 'finish');
```

- Never collect an unbounded stream into an array or string. Enforce size limits by counting bytes in a transform and destroying the stream with an error when the limit is exceeded.
- HTTP: `await pipeline(upstreamBody, res)` for proxying; the response ends when the stream ends, and a client disconnect destroys the pipeline.

## 3. Web Streams interop

- `ReadableStream`, `WritableStream`, `TransformStream`, `CompressionStream`, `TextDecoderStream` are globals. `fetch` response bodies are web `ReadableStream`s.
- Convert with `Readable.fromWeb(webStream)`, `Readable.toWeb(nodeStream)`, `Writable.fromWeb`, `Writable.toWeb`, and feed Node streams into `pipeline`:

```js
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createWriteStream } from 'node:fs';

const res = await fetch('https://example.com/big.bin', { signal: AbortSignal.timeout(120_000) });
if (!res.ok || !res.body) throw new Error(`download failed: ${res.status}`);
await pipeline(Readable.fromWeb(res.body), createWriteStream('big.bin'));
```

- Use Node streams for file and socket work inside Node and Web Streams for code shared with browsers or other runtimes.

## 4. worker_threads

Workers run JavaScript in separate V8 isolates inside the same process, each with its own event loop and heap. Data crosses by structured clone (copy), by transfer (`ArrayBuffer`, `MessagePort` in the `transferList`, moved not copied), or by shared memory (`SharedArrayBuffer` with `Atomics`).

Use for: CPU-bound transforms, parsing, compression, image or PDF processing, running untrusted-regex matching with a deadline. Do not use for: I/O concurrency (async I/O is already concurrent), or tiny tasks where messaging cost exceeds the work.

Minimal one-shot worker (single file, branching on `isMainThread`):

```js
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';

if (isMainThread) {
  const worker = new Worker(import.meta.filename, {
    workerData: { n: 40 },
    resourceLimits: { maxOldGenerationSizeMb: 64 }, // a runaway worker fails alone
  });
  worker.once('message', (value) => console.log('result', value));
  worker.once('error', (err) => console.error('worker failed', err));
  worker.once('exit', (code) => console.log('exit', code));
} else {
  const fib = (n) => (n < 2 ? n : fib(n - 1) + fib(n - 2));
  parentPort.postMessage(fib(workerData.n));
}
```

Shared counters with `Atomics`:

```js
import { Worker, isMainThread, workerData } from 'node:worker_threads';

if (isMainThread) {
  const sab = new SharedArrayBuffer(4);
  const counter = new Int32Array(sab);
  const workers = Array.from({ length: 4 }, () => new Worker(import.meta.filename, { workerData: sab }));
  await Promise.all(workers.map((w) => new Promise((resolve) => w.once('exit', resolve))));
  console.log(Atomics.load(counter, 0)); // 4000
} else {
  const counter = new Int32Array(workerData);
  for (let i = 0; i < 1000; i++) Atomics.add(counter, 0, 1);
}
```

Rules:

- Creating a worker costs tens of milliseconds and memory for a new isolate; reuse workers through a pool instead of one per task.
- Handle `'error'` and `'exit'` on every worker; an uncaught exception in a worker terminates that worker, not the process.
- `worker.terminate()` stops a worker; in-flight work is lost, so give tasks idempotent semantics.
- Shared memory needs `Atomics` for coordination; plain reads and writes race.
- `process.env` is copied into workers by default (`env` option controls it); `process.exit()` in a worker ends the worker only.
- Under the permission model, workers need `--allow-worker`.

### Worker pool with Piscina

```js
// pool.js
import { Piscina } from 'piscina';

export const hashPool = new Piscina({
  filename: new URL('./hash-worker.js', import.meta.url).href,
  maxThreads: 4,
  maxQueue: 100, // beyond this, run() rejects instead of buffering without bound
});
```

```js
// hash-worker.js
import { pbkdf2Sync } from 'node:crypto';

export default function hash({ password, salt }) {
  return pbkdf2Sync(password, salt, 600_000, 32, 'sha256').toString('hex');
}
```

```js
// caller
import { hashPool } from './pool.js';

const controller = new AbortController();
const digest = await hashPool.run({ password, salt }, { signal: controller.signal });
// on shutdown: await hashPool.close();
```

Choose `maxThreads` near the number of physical cores minus the cores used by the main event loop. For password hashing prefer the async `crypto.pbkdf2`/`scrypt` (libuv pool) with a concurrency cap unless you need to isolate memory-hard work; a dedicated pool gives control over queue size.

The snippet demonstrates dispatch only; in real code generate a random salt per user (`crypto.randomBytes(16)`) and store the algorithm parameters with the digest.

## 5. cluster versus multiple processes

| Question | Answer |
|---|---|
| What does `cluster` do? | The primary forks worker processes that share server ports; connections are distributed round-robin on every platform except Windows (`cluster.schedulingPolicy`, `SCHED_RR` default) |
| Memory | Each worker has its own heap; no shared state except through IPC or external stores |
| When to use | A single host or VM where you manage the process model and want all cores behind one port |
| When to avoid | Containers with an orchestrator (run one process per container, scale replicas), or when you need independent resource limits per process |
| Restart policy | The primary must re-fork on `'exit'` with backoff and not restart-loop on boot errors |

```js
import cluster from 'node:cluster';
import { availableParallelism } from 'node:os';
import process from 'node:process';

if (cluster.isPrimary) {
  for (let i = 0; i < availableParallelism(); i++) cluster.fork();
  cluster.on('exit', (worker, code, signal) => {
    if (!worker.exitedAfterDisconnect) cluster.fork(); // add backoff in real use
  });
  process.once('SIGTERM', () => {
    for (const w of Object.values(cluster.workers ?? {})) w?.disconnect(); // workers drain and exit
  });
} else {
  const { startServer } = await import('./server.js');
  await startServer(); // each worker installs its own SIGTERM handling
}
```

Alternatives: orchestrator replicas (Kubernetes Deployment, ECS tasks), a process manager on a VM, or one process plus a worker pool for CPU tasks. Sticky sessions and WebSocket affinity are not provided by `cluster`; keep session state outside the process.

## 6. child_process safety

- Use `execFile`/`spawn` with an argument array. They do not start a shell unless `shell: true`. `exec` and `execSync` take a command string interpreted by a shell and are injectable.
- Never put user input in the executable name, and allowlist both executable and allowed options. A leading `-` in user input can become an option; separate with `--` when the tool supports it.
- Set `timeout`, `killSignal`, `maxBuffer` and an `AbortSignal` (`signal` option) so a stuck child does not hang the request.
- Stream large output (`spawn` with `stdio` pipes into `pipeline`) instead of buffering with `execFile`.
- Pass a minimal explicit `env` instead of inheriting every secret in `process.env`.
- Windows: `.bat` and `.cmd` files are not directly executable; running them needs a shell (`cmd.exe /c`), which brings back quoting risks. Avoid spawning them with user-influenced arguments.
- Do not call `execSync`/`spawnSync` on request paths: they block the event loop.

```js
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const run = promisify(execFile);

export async function gitRevision(cwd) {
  const { stdout } = await run('git', ['rev-parse', 'HEAD'], {
    cwd,
    timeout: 5_000,
    maxBuffer: 64 * 1024,
    env: { PATH: process.env.PATH },
    signal: AbortSignal.timeout(6_000),
  });
  return stdout.trim();
}
```

## 7. Choosing between the options

| Need | Pick |
|---|---|
| Move bytes through transforms with bounded memory | `pipeline` with streams or async generators |
| CPU-bound function called often | Worker pool (Piscina) with bounded queue |
| One-off heavy job at startup or from a CLI | Single `Worker`, or a separate script run by a job runner |
| Use all cores on one VM | `cluster` or a process manager running N copies |
| Isolate untrusted or flaky native tooling | `child_process` (or a container) with `timeout` and limited `env` |
| Cross-service work distribution | A queue plus consumers; see system-design-expert and scalability-expert |
