# Vitest 5 Reference

Verified against Vitest 5.0.5, @vitest/coverage-v8 5.0.5, @vitest/browser-playwright 5.0.5 and the Vitest v5.0.5 docs (2026-10). Companion to [../SKILL.md](../SKILL.md). Example snippets were executed or type-checked on these versions.

## Install and requirements

```bash
npm i -D vitest @vitest/coverage-v8        # coverage provider package matches the vitest version
npm i -D jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom   # DOM tests (or happy-dom)
```

- Vitest 5 needs Node 22.12 or newer and Vite 6.4 or newer. `vite` is a required peer dependency; Yarn does not install peers automatically, so run `yarn add -D vite`.
- `vitest init browser` scaffolds browser mode.
- TypeScript, ESM and JSX work through Vite; no transformer setup.

## Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',                       // component files opt in with `// @vitest-environment jsdom`
    setupFiles: ['./vitest.setup.ts'],         // runs before each test file, in the same process
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,                        // restore vi.spyOn originals before each test
    unstubEnvs: true,                          // undo vi.stubEnv automatically
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.*'],
      reporter: ['text', 'lcov'],
      thresholds: { lines: 80, branches: 80 },
    },
  },
});
```

```typescript
// vitest.setup.ts
import '@testing-library/jest-dom/vitest';
```

Keys (each verified in the v5.0.5 docs):

| Key | Notes |
|---|---|
| `include`, `exclude` | Test file globs; default include `**/*.{test,spec}.?(c\|m)[jt]s?(x)` |
| `environment` | `node` (default), `jsdom`, `happy-dom`, `edge-runtime`; per file via `@vitest-environment` docblock |
| `globals` | Default `false`. When `true`, add `vitest/globals` to `tsconfig` `types`; Testing Library auto-cleanup needs globals, otherwise call `cleanup` in `afterEach` |
| `setupFiles` | Run before each test file in the test process; editing one reruns all tests. `globalSetup` runs once in the main process |
| `clearMocks` | Default `true` in Vitest 5 (calls `vi.clearAllMocks()` before each test) |
| `mockReset`, `restoreMocks` | Default `false`; reset history and implementation / restore `vi.spyOn` originals |
| `unstubEnvs`, `unstubGlobals` | Default `false`; undo `vi.stubEnv` and `vi.stubGlobal` |
| `pool` | `forks` (default), `threads`, `vmThreads`, `vmForks`; `poolOptions` and `minWorkers` no longer exist |
| `maxWorkers` | Number or percentage string; defaults to all available parallelism (half in watch mode) |
| `fileParallelism` | Default `true`; `false` forces one worker |
| `isolate` | Per-file isolation; `false` is faster when tests are side-effect free |
| `sequence.shuffle` | Boolean, or `{ files, tests }` (`sequence.shuffle.files` is root-only); `sequence.seed` reproduces an order; `sequence.hooks` is `stack` by default (`list` matches Jest) |
| `testTimeout`, `retry` | Defaults and per-test options |
| `projects` | Inline configs, config files or globs (the old `workspace` is removed) |
| `typecheck` | `--typecheck` runs type tests; default include `**/*.{test,spec}-d.?(c\|m)[jt]s?(x)` |

## Projects

`test.projects` replaces `workspace` (deprecated in 3.2, now removed). A config that declares `projects` only provides them; it does not run tests itself.

```typescript
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';

export default defineConfig({
  test: {
    coverage: { provider: 'v8', include: ['src/**/*.{ts,tsx}'], exclude: ['**/*.test.*'] },
    projects: [
      { extends: true, test: { name: 'unit', environment: 'node', include: ['src/**/*.test.ts'] } },
      {
        extends: true, // inline projects inherit the root config by default in Vitest 5
        test: {
          name: 'components',
          include: ['src/**/*.browser.test.tsx'],
          browser: { enabled: true, provider: playwright(), headless: true, instances: [{ browser: 'chromium' }] },
        },
      },
    ],
  },
});
```

- Folder or file entries (`'packages/*'`) are separate projects that do not inherit the root config; a file must be named `vitest.config.*`, `vite.config.*`, `vitest.<name>.config.*` or `vite.<name>.config.*`.
- Arrays are merged: root `setupFiles` plus the project's own. Set `extends: false` to opt out.
- Inline projects share the root Vite server in Vitest 5 (`sharedViteServer: false` restores separate servers).
- Run one project with `vitest --project unit`.
- Merging the root config into a project config with `mergeConfig` can turn the project into a container (it inherits `projects`); share a separate base config instead.

## Browser mode

- Run tests in a real browser. Install a provider: `@vitest/browser-playwright` (recommended), `@vitest/browser-preview` (local preview only), or `@vitest/browser-webdriverio` (moved to the vitest-community organization in 5.0 and community-maintained).
- Configure `test.browser` with `enabled`, `provider: playwright()` and at least one entry in `instances` (see the projects example). The v5.0.5 docs carry no experimental label for browser mode.
- Vitest 5 changes: locators are strict by default, `toHaveTextContent` uses strict equality, automocked modules stay automocked, `render` is async in `vitest-browser-vue` and `vitest-browser-svelte`, failure screenshots go to `.vitest/attachments/failure-screenshots/`.
- Prefer browser mode for component tests that need real layout or events; keep logic tests in `node`. Cross-page user journeys belong in Playwright Test (playwright-expert).

## Mocking

```typescript
import { vi } from 'vitest';

const { sendMail } = vi.hoisted(() => ({ sendMail: vi.fn() })); // runs before imports
vi.mock('./mailer', () => ({ sendMail }));                         // hoisted to the top of the file
```

Rules:
- `vi.mock`, `vi.unmock` and `vi.hoisted` are hoisted. In Vitest 5 they must be at the top level of the file; inside `describe`, `test` or functions they throw an error that lists each offending call. Use `vi.doMock`/`vi.doUnmock` (not hoisted) for per-test mocks, followed by a dynamic `await import(...)`.
- They work only for modules loaded with `import`, not `require`, and `vi` must come from `vitest` (or `globals: true`) so Vitest can find the call statically.
- Modules already imported by a setup file are cached and will not be mocked; call `vi.resetModules()` inside `vi.hoisted` to clear caches first.
- The factory runs once and its result is cached. It may be async and receives `importOriginal`: `vi.mock(import('./mailer'), async (importOriginal) => ({ ...(await importOriginal()), sendMail: vi.fn() }))`.
- A factory must return an object with every export named explicitly (`default: ...` for the default export). Returning a bare value works in Jest but not here.
- `vi.mock('./calc', { spy: true })` keeps the real implementation but records calls.
- `vi.mock('./x')` with no factory automocks; `__mocks__` folders next to the module or at the project root are used only when `vi.mock` is called for that path.
- `vi.importActual` replaces Jest's `requireActual`; `vi.mocked(fn)` is a type helper.
- `vi.restoreAllMocks()` only restores spies created with `vi.spyOn`; it does not reset `vi.fn()` mocks or automocks. `mockReset()` on `vi.fn(impl)` restores `impl`, not an empty function.
- `vi.stubEnv('NAME', 'value')` and `vi.stubGlobal('fetch', fn)` with `unstubEnvs`/`unstubGlobals` in config keep tests isolated.
- Class mocks keep prototype methods in v5 and instances behave like instances of the implementation class.
- `vi.when(...)` was added in 5.0.0 for argument-based stubbing; check the current API page before use.
- Libraries that import a mocked module internally need `server.deps.inline: ['lib-name']`.

## Fake timers and time

```typescript
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

test('retries', async () => {
  const p = run();                           // code that awaits setTimeout
  await vi.advanceTimersByTimeAsync(1000);   // flushes promises between timers
  await expect(p).resolves.toBe('ok');
});
```

- `vi.useFakeTimers()` fakes `setTimeout`, `setInterval`, `setImmediate`, their clear functions and `Date`. It does not fake `process.nextTick` or `queueMicrotask`; add `toFake: ['nextTick', 'queueMicrotask']` if needed (not supported with `--pool=forks` for `nextTick`). `toFake` and `toNotFake` cannot be combined.
- In Vitest 5 fake timers and `vi.setSystemTime` also mock `Temporal`; add `Temporal` to `fakeTimers.toNotFake` to keep it real.
- `vi.advanceTimersByTime(Async)`, `vi.runAllTimers(Async)`, `vi.runOnlyPendingTimers(Async)`, `vi.advanceTimersToNextTimer`, `vi.getTimerCount`, `vi.setSystemTime`, `vi.useRealTimers`. `vi.runAllTimers` throws after 10,000 iterations by default (infinite intervals); the limit is `fakeTimers.loopLimit`.
- `vi.waitFor(fn, { timeout, interval })` retries a callback until it stops throwing; `expect.poll(fn)` retries an assertion. In Vitest 5 `expect.poll` rejects when it times out and its callback receives an `AbortSignal` (`async ({ signal }) => ...`).

## Concurrency, ordering, fixtures

- Tests in a file run sequentially by default; files run in parallel across workers.
- `describe.concurrent`, `test.concurrent` or `{ concurrent: true }` run tests of a group together with `Promise.all`; this only helps when tests await I/O. In concurrent tests use the `expect` from the test context (`async ({ expect }) => ...`) so snapshots and counts attribute correctly. Mock auto-reset options (`clearMocks`, `mockReset`, `restoreMocks`, `unstubGlobals`) affect tests running at the same time.
- Opt out of inherited concurrency with `describe('x', { concurrent: false }, ...)` or `test('x', { concurrent: false }, ...)`. `describe.sequential`, `test.sequential` and the `sequential` option were removed in 5.0; `describe.serial` never existed.
- `describe.shuffle` (or `{ shuffle: true }`) randomizes order within a suite; `sequence.shuffle` or `--sequence.shuffle` does it globally; `--sequence.seed=N` reproduces.
- `testNamePattern` (`-t`) matches the full name joined with ` > ` in v5: `vitest -t 'math > adds'`.

Fixtures and tables (executed):

```typescript
import { describe, expect, test as base } from 'vitest';

const test = base.extend<{ cart: { sku: string; unitCents: number; qty: number }[] }>({
  cart: async ({}, use) => {
    await use([{ sku: 'a', unitCents: 500, qty: 2 }]);   // code after use() is teardown
  },
});

test('uses the fixture', ({ cart }) => {
  expect(totalCents(cart, 10)).toBe(900);
});

test.for([
  [[{ sku: 'a', unitCents: 100, qty: 1 }], 0, 100],
  [[{ sku: 'a', unitCents: 100, qty: 3 }], 50, 150],
] as const)('table %#', ([items, percent, expected]) => {
  expect(totalCents([...items], percent)).toBe(expected);
});
```

Other test-context items: `skip`, `annotate`, `signal`, `onTestFailed`, `onTestFinished`, and in 5.0 a `bench` fixture (the benchmarking API was rewritten and top-level `bench` was removed; check the benchmarking guide).

Asynchronous assertions (`resolves`, `rejects`, `toMatchFileSnapshot`) must be awaited in v5 or the test fails.

## Coverage

- Providers: `v8` (default, install `@vitest/coverage-v8`) and `istanbul` (install `@vitest/coverage-istanbul`). The v8 provider uses AST-aware remapping since 3.2, giving Istanbul-like accuracy with v8 speed; it needs a V8 runtime (not Firefox or Bun).
- `coverage.include` lists the files to report; by default only files imported during the run appear, so set it (for example `['src/**/*.{ts,tsx}']`) to expose untested files. There is no `coverage.all` option in the v5 docs. In Vitest 5 patterns match paths relative to the project root and a pattern without a glob wildcard is a directory (`include: ['src']` equals `src/**`).
- `coverage.exclude` uses the same matching; test files are excluded automatically.
- Thresholds: `coverage.thresholds.lines|functions|branches|statements`, negative numbers mean "at most N uncovered". `perFile` is not inherited by glob-pattern thresholds in v5; set it on each glob.
- Reporters: `text`, `html`, `lcov`, `json`, `text-summary`, `clover`, Istanbul-compatible names. Output goes to `coverage/` by default; `coverage.clean` empties it before a run; `coverage.reportOnFailure` writes reports even when tests fail.
- Run with `vitest run --coverage` (or `coverage.enabled: true`).

## In-source tests

Colocate small tests with code using `import.meta.vitest`:

```typescript
export const add = (a: number, b: number) => a + b;

if (import.meta.vitest) {
  const { test, expect } = import.meta.vitest;
  test('add', () => expect(add(1, 2)).toBe(3));
}
```

Add `includeSource: ['src/**/*.ts']` to `test`, add `vitest/importMeta` to tsconfig `types`, and set `define: { 'import.meta.vitest': 'undefined' }` in the production build config so the blocks are removed.

## CLI

```bash
vitest                       # watch mode in a TTY
vitest run                   # single run (CI)
vitest run --coverage
vitest --changed             # tests affected by changed files (or --changed=main)
vitest run --project unit
vitest run --sequence.shuffle --sequence.seed=42
vitest run --typecheck
vitest --ui                  # needs @vitest/ui; Vitest 5 UI requires an authenticated URL
vitest run --reporter=blob --shard=1/4      # shards split test files
vitest --merge-reports --reporter=junit     # merge .vitest/blob/ from all shards
```

Reporters include `default`, `agent`, `minimal`, `verbose`, `dot`, `tree`, `json`, `junit`, `tap`, `blob`, `github-actions`, `hanging-process`. `json` and `junit` write files under `.vitest/` by default in v5; use their `stdout` option to print instead. Add `.vitest` to `.gitignore`.

## Migrating from Jest

| Jest | Vitest |
|---|---|
| Globals on | Off; set `globals: true` or import from `vitest` (Testing Library cleanup needs globals) |
| `jest.fn`, `jest.spyOn`, `jest.mock` | `vi.fn`, `vi.spyOn`, `vi.mock` (explicit export names in factories) |
| `jest.requireActual` | `await vi.importActual(...)` |
| `jest.mock` factory returns the default export | Return `{ default: ... }` |
| `mockReset` empties the implementation | Restores the original `vi.fn(impl)` implementation |
| `__mocks__` auto-loaded | Loaded only when `vi.mock(path)` is called; call it in `setupFiles` for global mocks |
| Legacy timers | Not supported |
| `jest.setTimeout(ms)` | `vi.setConfig({ testTimeout: ms })` |
| `done` callbacks | Not supported; use async tests |
| `beforeEach(() => value)` returning a value | Returned function is a teardown; wrap in braces |
| Hooks run in order defined (`list`) | `sequence.hooks: 'stack'` by default; set `'list'` for Jest behavior |
| `JEST_WORKER_ID` | `VITEST_POOL_ID` (and `VITEST_WORKER_ID`) |
| `jest.Mock` types | `import type { Mock } from 'vitest'` |
| `-t 'a b'` | `-t 'a > b'` |
| `jest.replaceProperty` | `vi.stubEnv` or `vi.spyOn` |
| `jest-snapshot` composables | `Snapshots` from `vitest` (custom snapshot matchers are experimental) |

## Upgrading to Vitest 5 checklist

1. Node 22.12+, Vite 6.4+ (explicit `vite` for Yarn).
2. `clearMocks` is now `true`; code that read mock history across tests or recorded calls in `beforeAll` changes. Set it back to `false` if needed.
3. Move `vi.mock`, `vi.unmock`, `vi.hoisted` to the top level of the file.
4. Replace `describe.sequential`, `test.sequential` and `sequential` options with `{ concurrent: false }`.
5. Await every `resolves`, `rejects` and `toMatchFileSnapshot` assertion; check `expect.poll` timeouts.
6. Review `coverage.include` and `coverage.exclude` patterns and any per-glob `perFile` thresholds.
7. Inline projects now inherit the root config (`extends: true`) and share a Vite server.
8. Update reporter and artifact paths to `.vitest/`; `json` and `junit` reporters write files by default; `html` takes `outputDir`.
9. Replace removed entrypoints: `vitest/coverage` and `vitest/reporters` become `vitest/node`; `vitest/environments` and `vitest/snapshot` become `vitest/runtime`; `vitest/runners` and `vitest/suite` become `TestRunner` from `vitest`.
10. Config files are no longer looked up from parent directories.
