# Jest 30 Reference

Verified against Jest 30.5.2, @swc/jest 0.2.39, ts-jest 29.4.15, jest-environment-jsdom 30.5.2, @testing-library/react 16.3.3 and the Jest docs (2026-10). Companion to [../SKILL.md](../SKILL.md). Example snippets below were executed.

## Install and requirements

```bash
npm i -D jest @swc/jest @types/jest                      # transformer without type-check
npm i -D jest-environment-jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom   # DOM tests
```

- Jest 30 needs Node 18 or newer; the type definitions need TypeScript 5.4 or newer.
- `jest-environment-jsdom` is a separate package (jsdom 26 in Jest 30).
- `npm init jest@latest` creates a config; `jest --init` was removed in 30.

## Configuration

`defineConfig` and `mergeConfig` are exported from `jest`. A `jest.config.ts` file needs a loader declared in a docblock (`/** @jest-config-loader ts-node */` or `/** @jest-config-loader esbuild-register */`) and that package installed; plain `jest.config.js` avoids the extra dependency.

```javascript
// jest.config.js
const { defineConfig } = require('jest');

module.exports = defineConfig({
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.test.{ts,tsx}'],
  transform: {
    '^.+\\.tsx?$': ['@swc/jest', { jsc: { transform: { react: { runtime: 'automatic' } } } }],
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  restoreMocks: true,
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/*.test.{ts,tsx}'],
  coverageProvider: 'v8',
  coverageThreshold: { global: { lines: 80, branches: 80 } },
});
```

```typescript
// jest.setup.ts: runs after the test framework is installed, once per test file
import '@testing-library/jest-dom';

afterEach(() => {
  jest.useRealTimers();
});
```

Keys that matter (all verified in the Jest 30 configuration docs):

| Key | Notes |
|---|---|
| `setupFiles` | Runs before the test framework is installed in the environment; no `expect` or hooks yet |
| `setupFilesAfterEnv` | Runs after the framework is installed, before each test file; use for `expect.extend`, jest-dom, global hooks. `setupFilesAfterEach` does not exist |
| `globalSetup` / `globalTeardown` | Once per run, in the parent process; globals set there are not visible to tests |
| `testEnvironment` | `node` (default) or `jsdom`; per file with a `@jest-environment jsdom` docblock |
| `injectGlobals` | Default `true`; if `false`, import from `@jest/globals` |
| `transform` | Default `babel-jest`; set `@swc/jest` or `ts-jest` for TypeScript |
| `moduleNameMapper` | Alias and asset stubs, for example `'^@/(.*)$': '<rootDir>/src/$1'` |
| `clearMocks`, `resetMocks`, `restoreMocks` | Automatic `mockClear`, `mockReset`, `restoreAllMocks` before each test; all default `false` |
| `fakeTimers` | Global fake timer config (`enableGlobally`, `doNotFake`, `now`, `advanceTimers`...) |
| `collectCoverage`, `collectCoverageFrom` | List source globs so untested files appear in reports |
| `coverageProvider` | `babel` (default) or `v8` |
| `coverageThreshold` | `global`, per-glob or per-path thresholds for `branches`, `functions`, `lines`, `statements`; negative numbers mean "at most N uncovered" |
| `projects` | Array of paths or inline project configs; each project can set `displayName` |
| `maxWorkers`, `workerIdleMemoryLimit` | Parallelism and worker recycling |
| `testTimeout`, `slowTestThreshold` | Default per-test timeout (5000 ms) and "slow" reporting |
| `randomize` | Same as `--randomize`: shuffles test order within each file; the seed is printed |
| `waitForUnhandledRejections` | Gives one event loop turn to handle rejections, avoiding false positives at some cost in speed |

Multiple projects (executed):

```javascript
const { defineConfig } = require('jest');

module.exports = defineConfig({
  projects: [
    { displayName: 'unit', testEnvironment: 'node', testMatch: ['<rootDir>/src/**/*.test.ts'], transform: { '^.+\\.tsx?$': '@swc/jest' } },
    {
      displayName: 'dom',
      testEnvironment: 'jsdom',
      testMatch: ['<rootDir>/src/**/*.test.tsx'],
      transform: { '^.+\\.tsx?$': ['@swc/jest', { jsc: { transform: { react: { runtime: 'automatic' } } } }] },
      setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
    },
  ],
});
```

Run a subset with `jest --selectProjects unit` (the flag needs a value in Jest 30).

## Transformers

- `@swc/jest` and `babel-jest` do not type-check; run `tsc --noEmit` in CI.
- `ts-jest` type-checks but requires the TypeScript JavaScript compiler API. At verification time it refused TypeScript 7.0.2 with an error telling you to install `@typescript/native` and alias `@typescript/typescript6` as `typescript`; pin a TypeScript version ts-jest supports (its peer range was `>=4.3 <7`) or use `@swc/jest`.
- Hoisting of `jest.mock` is done by the transformer. `babel-jest` and `ts-jest` hoist it. With `@swc/jest` 0.2.39 the call was hoisted when `jest` was the global and not hoisted when `jest` was imported from `@jest/globals`. If a module mock seems ignored, check this first.

## Mocking

```typescript
// Automock a boundary module and type the mocked function
import { sendMail } from './mailer';
jest.mock('./mailer');                      // hoisted; every export becomes a jest.fn()
const sendMailMock = jest.mocked(sendMail);
sendMailMock.mockResolvedValue({ id: 'm1' });
```

```typescript
// Partial mock: keep real exports, replace one
jest.mock('./mailer', () => ({
  ...jest.requireActual('./mailer'),
  sendMail: jest.fn().mockResolvedValue({ id: 'stub' }),
}));
```

Rules:
- `jest.mock` calls are hoisted above imports by the transformer. The factory may not reference out-of-scope variables unless their names start with `mock` (babel-plugin-jest-hoist rule); even then, a `const` declared below the imports is still uninitialized when the factory first runs, so prefer automock plus `jest.mocked`, build the mock inside the factory, or wrap access in a function.
- `jest.doMock` is not hoisted: pair it with `jest.resetModules()` and a `require` or dynamic `import()` after the call.
- `jest.mock` only applies to modules loaded through `require` (CommonJS or transformed ESM). Native ESM requires `jest.unstable_mockModule` and dynamic import (below).
- `jest.mock` paths are case-sensitive in Jest 30.
- `jest.spyOn(obj, 'method')` keeps the original implementation until you override it; `restoreAllMocks` (or `restoreMocks: true`) puts originals back. `jest.replaceProperty(obj, 'prop', value)` swaps a non-function property for the test and is undone by `restoreAllMocks`.
- Manual mocks live in a `__mocks__` folder next to the module (or adjacent to `node_modules` for packages).
- `mockReset` replaces the implementation with an empty function returning `undefined` (unlike Vitest, which restores the original `vi.fn(impl)` implementation).
- `jest.genMockFromModule` was removed in 30: use `jest.createMockFromModule`. Replace `jest.SpyInstance` with `jest.Spied`.

Native ESM (set `"type": "module"` or `.mjs`, run Node with `--experimental-vm-modules`, for example `NODE_OPTIONS="$NODE_OPTIONS --experimental-vm-modules" npx jest`):

```javascript
import { jest } from '@jest/globals';

jest.unstable_mockModule('node:child_process', () => ({ execSync: jest.fn() }));
const { execSync } = await import('node:child_process'); // import after registering the mock
```

The API is marked unstable; the factory is required and static imports are not hoisted.

## Timers

```typescript
beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

test('debounce fires once', async () => {
  const fn = jest.fn();
  const debounced = debounce(fn, 200);   // your code under test
  debounced(); debounced();
  await jest.advanceTimersByTimeAsync(200);
  expect(fn).toHaveBeenCalledTimes(1);
});
```

- `jest.useFakeTimers({ now: new Date('2026-01-31T10:00:00Z') })` fixes the clock; `jest.setSystemTime(...)` moves it.
- Use the `...Async` variants (`advanceTimersByTimeAsync`, `runAllTimersAsync`, `runOnlyPendingTimersAsync`) when promises are involved; they flush microtasks between timers.
- `doNotFake: ['nextTick']` keeps selected APIs real. In the Node environment `process.nextTick` and `process.hrtime` are faked too; in jsdom `requestAnimationFrame` is.
- When testing a rejection that happens after timers run, create the `expect(promise).rejects` first, then advance timers, then await it.

## Async, snapshots, matchers

- `await expect(p).resolves.toBe(...)`, `await expect(p).rejects.toThrow(...)`. Jest does not fail on an unawaited assertion; lint for `jest/valid-expect`.
- `expect.assertions(n)` and `expect.hasAssertions()` exist in Jest (they are Jest APIs, also available in Vitest).
- Snapshots: `toMatchSnapshot`, `toMatchInlineSnapshot` (use `-u` to write/update), property matchers for volatile fields (`{ id: expect.any(String) }`), `snapshotSerializers`. Jest 30 prints `Error.cause` in snapshots and omits empty-string React children.
- Custom matchers via `expect.extend` in a `setupFilesAfterEnv` file; declare them for TypeScript by augmenting `jest.Matchers<R>`.
- Removed aliases in 30: `toBeCalled`, `toBeCalledWith`, `toBeCalledTimes`, `lastCalledWith`, `nthCalledWith`, `toReturn`, `toReturnWith`, `toReturnTimes`, `lastReturnedWith`, `nthReturnedWith`, `toThrowError`; use the `toHaveBeen...` and `toThrow` forms. Non-enumerable properties are excluded from object matchers.

## React Testing Library

```tsx
/** @jest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Counter } from './Counter';

test('increments on click', async () => {
  const user = userEvent.setup();
  render(<Counter initial={2} />);
  await user.click(screen.getByRole('button', { name: /clicked 2 times/i }));
  expect(screen.getByRole('button')).toHaveTextContent('Clicked 3 times');
});
```

`@testing-library/jest-dom` (imported in `jest.setup.ts`) provides `toHaveTextContent`, `toBeVisible` and the like. Testing Library registers automatic cleanup when `afterEach` is a global (Jest default). Query by role first; `findBy*` for async appearance, `waitFor` for assertions that need retrying.

## Coverage

- `--coverage` (or `collectCoverage: true`) with `coverageProvider: 'babel'` (default, instruments the code, works with babel-jest) or `'v8'` (native, no instrumentation).
- Always set `collectCoverageFrom` so files no test imports show up as 0 percent; exclude tests, mocks and generated code with `!` patterns or `coveragePathIgnorePatterns`.
- Thresholds fail the run with a non-zero exit code; per-path thresholds protect critical directories.
- Ignore hints: `/* istanbul ignore next */` (babel provider) and `/* c8 ignore next */` (v8 provider); use sparingly.

## CLI

```bash
jest                              # all tests
jest path/to/file.test.ts -t "applies a"   # file and name filter
jest --watch                      # changed files since last commit
jest --onlyChanged | --changedSince=main   # related tests only
jest --ci --coverage --shard=1/4  # CI run, one of four shards
jest --randomize                  # shuffle tests in each file; prints the seed
jest --testPathPatterns "unit/.*" # Jest 30 name (was --testPathPattern)
jest --maxWorkers=50% | --runInBand
```

Use `--ci` so snapshots are never written implicitly. For JUnit output use the `jest-junit` reporter package (`reporters: ['default', 'jest-junit']`).

## Upgrading 29 to 30 checklist

1. Node 18+, TypeScript 5.4+ (types), jsdom 26 behavior changes in `jest-environment-jsdom`.
2. Replace removed matcher aliases, `genMockFromModule`, `jest.SpyInstance`; fix case-sensitive `jest.mock` paths.
3. Rename `--testPathPattern` to `--testPathPatterns`; stop using `jest --init`; give `--maxWorkers` and `--selectProjects` explicit values.
4. Update snapshots that changed (error causes, empty React strings, `ArrayBuffer`/`DataView` printing).
5. Default `testMatch` and `moduleFileExtensions` now include `.mts` and `.cts`; check for files that should not be treated as tests or modules.
6. Custom `TestSequencer` classes and programmatic `Runtime` use need updates; deep imports into Jest internals no longer work (packages ship bundled with ESM wrappers).
