# Runtime Features

Reference for built-in capabilities that replace common dependencies or change how a Node.js project is set up: ES modules and `require(esm)`, native TypeScript type stripping, environment loading, the permission model, the test runner, `diagnostics_channel` and OpenTelemetry. Verified against Node.js 26.13 LTS, 24.22 and 22.23 (2026-10). Where a feature differs by line, the minimum versions come from the Node.js API docs change history.

## 1. ES modules and require(esm)

- A file is ESM when it ends in `.mjs`, or ends in `.js` and the nearest `package.json` has `"type": "module"`. `.cjs` is always CommonJS. `.js` files without `"type"` that contain ESM syntax are detected as ESM by syntax detection.
- Relative imports need the file extension (`./db.js`); built-ins use the `node:` prefix; directory imports and extensionless specifiers are not resolved.
- `__dirname` and `__filename` do not exist. Use `import.meta.dirname` and `import.meta.filename` (or `fileURLToPath(import.meta.url)`). `require` is not defined; create one with `createRequire(import.meta.url)` from `node:module` when needed.
- `require(esm)`: a CommonJS module can `require()` an ES module if the graph has no top-level `await`. The result is the module namespace object (default export under `.default`, with `__esModule: true` added when a default export exists). A module can export `"module.exports"` to customize what `require()` returns. Available without a flag in 20.19+ and 22.12+; no longer experimental since 25.4; disable with `--no-require-module`; trace use with `--trace-require-module`.
- Top-level `await` is allowed in ESM entry points, not in modules loaded through `require(esm)`.
- `import()` loads ESM from CommonJS asynchronously at any time.
- Dual packages: publish ESM with an `exports` map; CommonJS consumers on current LTS lines can use `require(esm)` instead of a second build.
- Subpath imports (`"imports": { "#lib/*": "./src/lib/*.js" }` in `package.json`) give alias-like specifiers that work in Node and in type-stripping mode, unlike `tsconfig` `paths`.
- JSON imports need an attribute: `import data from './data.json' with { type: 'json' }`.
- `module.register()` is runtime-deprecated in Node 26; use `module.registerHooks()` (synchronous in-thread hooks, release candidate since 25.4 and 24.13.1) when writing loader hooks.

## 2. Native TypeScript (type stripping)

Status: stable since 25.2 and 24.12; enabled by default since 22.18 and 23.6 (without an experimental warning since 24.3 and 22.18). The runtime erases type annotations by replacing them with whitespace; it performs no type checking.

Supported: `.ts`, `.mts`, `.cts`; module system is chosen the same way as for `.js`/`.mjs`/`.cjs`. Import specifiers keep the real extension (`./db.ts`). Not supported: `.tsx`.

Unsupported syntax (error `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`): `enum`, `namespace` with runtime code, parameter properties (`constructor(private x: number)`), import aliases (`import x = require()`), and decorators. `--experimental-transform-types`, which enabled `enum` and similar, was removed in Node 26.

Other limits:

- `tsconfig.json` is ignored, so `paths`, `target` downleveling, `jsx` and `experimentalDecorators` have no effect.
- TypeScript files under `node_modules` are refused, so packages must ship JavaScript.
- Type imports need `type` (`import type { X }` or `import { fn, type X }`); otherwise the import is kept and fails at run time.
- The built-in parser needs WebAssembly. `--no-strip-types` disables the feature.
- TypeScript syntax is not supported in the REPL, `--check` and `node inspect`.

Recommended `tsconfig.json` (Node docs recommend TypeScript 5.8 or newer):

```json
{
  "compilerOptions": {
    "noEmit": true,
    "target": "esnext",
    "module": "nodenext",
    "rewriteRelativeImportExtensions": true,
    "erasableSyntaxOnly": true,
    "verbatimModuleSyntax": true
  }
}
```

Workflow: run `node src/main.ts`, type-check in CI with `tsc --noEmit`, and publish libraries as compiled JavaScript plus `.d.ts` files. For stacks that need decorators, `paths` or `enum` (for example NestJS), keep a build step or a runner such as `tsx`.

## 3. Environment and configuration

- `node --env-file=.env app.js` loads variables into `process.env` (stable since 24.10 and 22.21). Several flags can be combined; later files override earlier files. Variables already set in the real environment take precedence over file values. A missing file is an error; use `--env-file-if-exists=.env.local` for optional files.
- Multi-line quoted values are supported (20.12+, 21.7+). `process.loadEnvFile(path)` loads a file at run time and `util.parseEnv(string)` parses text without touching `process.env`; check their stability in the docs before relying on them.
- The file format is not full dotenv: no variable expansion, and a few quoting edge cases differ.
- `--config-file=node.config.json` (stable) can carry flags; the `permission` block enables the permission model.
- Validate once at startup:

```ts
// src/config.ts
const required = ['DATABASE_URL'] as const;

function read(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}

export const config = Object.freeze({
  port: Number(process.env.PORT ?? 3000),
  databaseUrl: read(required[0]),
});
```

For richer validation use a schema library (Zod, Valibot, ArkType) and fail fast with all errors listed. `.env` files are for development; in production inject variables through the platform, and keep secrets out of the image and repository.

## 4. Permission model

Enable with `--permission`. Stable since 22.13 and 23.5. By default it denies file system access, network (where supported), child processes, worker threads, native addons, WASI, FFI and the inspector; grant what is needed:

```bash
node --permission \
  --allow-fs-read=/app --allow-fs-write=/tmp/app \
  src/main.ts
```

| Flag | Grants |
|---|---|
| `--allow-fs-read=<path>` / `--allow-fs-write=<path>` | Read or write of a path (repeatable; `*` wildcard allowed as a suffix pattern; directory grants cover contents) |
| `--allow-child-process` | `child_process` |
| `--allow-worker` | `worker_threads` |
| `--allow-addons` | Native addons |
| `--allow-wasi` | WASI |
| `--allow-net` | Network access; added in 25.0, under active development, check the docs |
| `--allow-ffi`, `--allow-openssl-store` | See the CLI docs; the OpenSSL store flag grants broad authority |

- Denied operations throw `ERR_ACCESS_DENIED` with the permission and resource. At run time `process.permission.has('fs.read', path)` checks and `process.permission.drop(scope, ref)` irreversibly drops a grant (open descriptors stay open).
- `--permission-audit` reports violations (through the `node:permission-model:fs` diagnostics channel and similar) without denying access, which helps size the allowlist; `--permission` wins if both are set.
- The model is a "seat belt" against mistakes in trusted code, not a boundary against malicious code. Symlinks, granted directories and already-open resources can widen access. Pair it with containers and least-privilege OS users.
- Under `--permission` the application must be granted read access to its own entry file and `node_modules`. Run package tooling with `npx --node-options="--permission --allow-fs-read=..."` as described in the docs.
- Permission options can also be stored in `node.config.json` under a `permission` key and loaded with `--config-file`.

## 5. Test runner

```ts
// test/slug.test.ts
import { describe, it, mock } from 'node:test';
import assert from 'node:assert/strict';
import { slugify } from '../src/slug.ts';

describe('slugify', () => {
  it('lowercases and hyphenates', () => {
    assert.equal(slugify('Hello World'), 'hello-world');
  });

  it('retries with fake timers', async (t) => {
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const fn = mock.fn();
    setTimeout(fn, 1000);
    t.mock.timers.tick(1000);
    assert.equal(fn.mock.callCount(), 1);
  });
});
```

```bash
node --test                      # discovers *.test.*, *-test.*, test-*.*, files in test/
node --test --watch              # re-run on change
node --test --test-name-pattern="slugify"
node --test --experimental-test-coverage --test-reporter=spec
node --test --test-concurrency=1 # serialize files that share resources
```

- File discovery includes `.ts`, `.mts`, `.cts` variants unless `--no-strip-types` is set.
- Each test file runs in its own process by default (`--test-isolation`); module-level state does not leak between files.
- Features: `describe`/`it`/`test`, hooks (`before`, `after`, `beforeEach`, `afterEach`), subtests, `skip`/`todo`/`only`, `t.mock` for functions, methods and timers, snapshot testing, test tags, reporters (`spec`, `tap`, `dot`, `junit`, `lcov`, custom), rerun of failed tests, `run()` programmatic API.
- Stability notes (2026-10): the runner is stable; code coverage is behind `--experimental-test-coverage`; `mock.module()` and global setup/teardown (`--test-global-setup`) are early development. Pin behavior in CI and re-check on upgrades.
- Test HTTP servers on port `0`, read `server.address().port`, and close in `after()`.

## 6. diagnostics_channel

`node:diagnostics_channel` (stable) is a low-overhead publish/subscribe bus that libraries use to expose events without a dependency on a specific APM.

- `channel(name)`, `channel.publish(data)`, `channel.subscribe(fn)`, `hasSubscribers` for cheap guards.
- `tracingChannel(name)` publishes `start`, `end`, `asyncStart`, `asyncEnd` and `error` events around an operation (`traceSync`, `tracePromise`, `traceCallback`); TracingChannel is stable since 26.8.
- Node core and libraries (Undici, `http`, the permission model, newer GraphQL.js) publish on named channels. Subscribe to them for custom metrics or logs without monkey-patching.

```js
import dc from 'node:diagnostics_channel';

const queryChannel = dc.tracingChannel('app:db:query');

queryChannel.subscribe({
  start(ctx) { ctx.startedAt = performance.now(); },
  end() {},
  asyncStart() {},
  asyncEnd(ctx) { console.log(JSON.stringify({ sql: ctx.sql, ms: performance.now() - ctx.startedAt })); },
  error(ctx) { console.error(ctx.error); },
});

export function traced(sql, run) {
  return queryChannel.tracePromise(run, { sql });
}
```

## 7. OpenTelemetry

- Packages: `@opentelemetry/api` (stable API used by libraries), `@opentelemetry/sdk-node` (`NodeSDK`), `@opentelemetry/auto-instrumentations-node` (`getNodeAutoInstrumentations()`), and exporters such as `@opentelemetry/exporter-trace-otlp-http`. Versions as of 2026-10: api 1.10, sdk-node 0.300, auto-instrumentations-node 0.82.
- The SDK must start before application code loads, so preload it: `node --import ./instrumentation.mjs app.js` (ESM or TypeScript with type stripping) or `--require` for CommonJS.
- Configure through standard environment variables rather than code: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_TRACES_SAMPLER`, `OTEL_RESOURCE_ATTRIBUTES`.
- ESM and ESM-only dependencies: the OpenTelemetry JS documentation states that ESM applications need `--experimental-loader=@opentelemetry/instrumentation/hook.mjs` for instrumentation to patch modules, including CommonJS apps that depend on ESM packages such as `@nestjs/platform-express@12`. Read `doc/esm-support.md` in the opentelemetry-js repository for the current guidance, since it is expected to change.
- Call `sdk.shutdown()` during graceful shutdown so buffered spans and metrics are flushed.
- Correlate logs: add `trace_id` and `span_id` from `trace.getActiveSpan()?.spanContext()` to each log line.
- Avoid high-cardinality attributes (user ids, full URLs) on metrics; spans tolerate more detail.

## 8. Other built-ins worth knowing

- `fs.glob()` / `fs.globSync()` (stable since 22.17 and 24.0), `util.parseArgs`, `util.styleText`, `crypto.randomUUID()`, `structuredClone`, `AbortSignal.timeout()`, `Promise.withResolvers()`, `Array.fromAsync()`.
- `node --watch` restarts on change; `node --run <script>` runs `package.json` scripts with lower startup cost than `npm run`.
- `node:sqlite` is available in release-candidate state (stability 1.2); use it for local tooling and tests, and a real database server for production services.
- Temporal is enabled by default in Node 26; earlier lines need a polyfill. Check browser and tooling support before adopting it in shared code.
