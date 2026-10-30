---
name: unit-testing-expert
description: >-
  Designs and configures unit tests in TypeScript and JavaScript with Jest and Vitest: test structure, test doubles, module mocking (jest.mock, vi.mock, vi.hoisted), fake timers, snapshots, React Testing Library, coverage thresholds, projects for monorepos, property-based testing with fast-check, and CI sharding. Use when writing or fixing *.test.ts files, jest.config or vitest.config, mocks that leak between tests, flaky async or timer tests, coverage gaps, or migrating Jest to Vitest. Not for browser end-to-end tests (use playwright-expert or e2e-testing-expert) or tests against real databases and services (use integration-testing-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Unit Testing Expert

This skill covers unit testing with Jest and Vitest: what a good unit test looks like, where to place test doubles, how each runner is configured and mocks modules, how to test time and async code, and how to read coverage and mutation results. It replaces the former separate Jest and Vitest skills; runner-specific depth is in the reference files. Examples are TypeScript and run on the versions below.

> Verified against Vitest 5.0.5 (Node 22.12+, Vite 6.4+), Jest 30.5.2 (Node 18+), @swc/jest 0.2.39, ts-jest 29.4.15, @testing-library/react 16.3.3, @testing-library/jest-dom 7.0.1, fast-check 4.10.2 (2026-10). Both example suites were executed on these versions.

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

- Covered: unit and component tests with Jest 30 and Vitest 5, test doubles, module and function mocking, fake timers, snapshots, custom matchers, Testing Library, coverage (v8, istanbul, Jest babel), projects, sharding, property-based and mutation testing, Jest to Vitest migration.
- Not covered: Playwright and Cypress browser tests (playwright-expert, e2e-testing-expert); tests that need a real database, queue or HTTP service (integration-testing-expert); refactoring code for testability beyond seams and injection (refactoring-expert); Vitest browser mode internals beyond a config sketch (check the current docs).

## 2. Core Expertise

- **Unit**: a function, class or module tested through its public API with slow or non-deterministic collaborators (network, clock, randomness, filesystem) replaced. Pure code needs no doubles.
- **Test doubles (Meszaros)**: dummy (unused argument), stub (canned answers), spy (records calls), fake (working simplified implementation, for example an in-memory repository), mock (pre-programmed expectations). `jest.fn`/`vi.fn` create stubs and spies; which role they play depends on how the test uses them.
- **Schools**: classical (Chicago) tests state with real collaborators and mocks only at process boundaries; mockist (London) isolates every collaborator and verifies calls. Prefer classical by default; use interaction checks for outgoing side effects (email sent, event published).
- **Structure**: arrange, act, assert in one visible flow; one behavior per test; descriptive names ("rejects a discount above 100").
- **FIRST**: fast, independent, repeatable, self-validating, timely.
- **Coverage**: line, branch, function, statement. It shows what was not executed, not whether assertions are good. Mutation testing (Stryker, `@stryker-mutator/core` with the `jest-runner` or `vitest-runner` plugin) checks whether tests fail when the code is changed.
- **Property-based testing**: `fast-check` generates inputs and shrinks failures; assert invariants (a discount never raises a total), not examples.
- **Runner map** (details in references):

| Concern | Jest 30 | Vitest 5 |
|---|---|---|
| Config file | `jest.config.js/ts` with `defineConfig` from `jest` | `vitest.config.ts` (or `test` block in `vite.config.ts`) with `defineConfig` from `vitest/config` |
| Setup per test file | `setupFiles` (before framework), `setupFilesAfterEnv` (after framework, for matchers and hooks) | `setupFiles` (before each test file, test APIs available) |
| Global setup once | `globalSetup`, `globalTeardown` | `globalSetup` |
| Test API globals | on (`injectGlobals: true`) | off; set `globals: true` or import from `vitest` |
| Module mocks | `jest.mock` (hoisted by the transformer), `jest.doMock`, `jest.requireActual`, `jest.unstable_mockModule` for native ESM | `vi.mock` (hoisted, top level only in v5), `vi.doMock`, `vi.hoisted`, `vi.importActual` |
| Timers | `jest.useFakeTimers`, `advanceTimersByTime(Async)`, `runAllTimers(Async)` | `vi.useFakeTimers`, `advanceTimersByTime(Async)`, `runAllTimers(Async)`, `setSystemTime` |
| Mock cleanup options | `clearMocks`, `resetMocks`, `restoreMocks` (all default false) | `clearMocks` (default true in v5), `mockReset`, `restoreMocks`, `unstubEnvs`, `unstubGlobals` |
| Coverage | `collectCoverage`, `coverageProvider: 'babel' \| 'v8'`, `collectCoverageFrom`, `coverageThreshold` | `coverage.provider: 'v8' \| 'istanbul'`, `coverage.include`, `coverage.thresholds` |
| Multiple configs | `projects` | `test.projects` (the old `workspace` is removed) |
| DOM | `testEnvironment: 'jsdom'` plus the `jest-environment-jsdom` package | `environment: 'jsdom' \| 'happy-dom'` (install the package), docblock `@vitest-environment` |
| Ordering | `--randomize`, `test.concurrent` | `sequence.shuffle`, `describe.shuffle`, `describe.concurrent`, `{ concurrent: false }` |
| CI split | `--shard=i/n`, `--ci` | `--shard=i/n`, `--reporter=blob` with `--merge-reports` |

## 3. Workflow

1. Identify the behavior and its observable outcome (return value, thrown error, state change, outgoing call).
2. Pick the seam: a parameter, constructor dependency or module boundary. Prefer injection over module mocking for code you own; mock modules for third-party or process-boundary code.
3. List cases: normal, boundaries, invalid input, error propagation, empty input, and one case per branch worth protecting.
4. Write the test first for new behavior or a bug (red), make it pass, then refactor.
5. Run the single file in watch mode; run it in random order and repeated (`vitest --sequence.shuffle`, `jest --randomize`) before committing.
6. Check the coverage report for untested branches, not for a number; use mutation testing on critical modules.
7. In CI run with `--ci` (Jest) or `vitest run`, produce a coverage report and JUnit or blob output, and fail on thresholds.

## 4. Decision Rules

- New project on Vite, ESM and TypeScript: Vitest. Existing Jest suite, React Native, or tooling that integrates only with Jest: stay on Jest 30. Do not run both runners on the same files.
- Component and hook tests: Testing Library with `jsdom` (or `happy-dom`); real browser behavior or layout: browser tests (playwright-expert) or Vitest browser mode with the Playwright provider.
- Mock at the boundary of the unit: the HTTP client, mailer, clock, random source, filesystem. Do not mock the unit's own helpers or value objects.
- Inject time and randomness (`now: () => Date`, `random: () => number`) in code you own; otherwise fake timers and `setSystemTime`.
- `vi.fn()`/`jest.fn()` for a callback you pass in; `spyOn` for an existing method you want to observe or briefly replace; module mock for an import you cannot inject.
- Snapshots: small inline snapshots for stable serialized output; avoid large component snapshots that nobody reviews.
- Coverage thresholds (`lines`, `branches`) as a floor in CI; do not chase 100 percent or reward lines without assertions.
- Jest transformers: `@swc/jest` or `babel-jest` for speed and no type-check (run `tsc --noEmit` separately); `ts-jest` for type-checked tests but it needs the TypeScript JS compiler API (it rejected TypeScript 7.0.2 at verification time, so pin a supported TypeScript version).
- Use `test.each`/`it.each` for tables, `test.for` (Vitest) when the case should also carry the test context.

## 5. Coding Standards

- File names `*.test.ts` or `*.spec.ts` next to the source or under `tests/`; one convention per repo.
- Test titles describe behavior and condition; nested `describe` by unit and method.
- Assertions are specific (`toEqual`, `toThrow(RangeError)`, `toHaveBeenCalledWith`) rather than `toBeTruthy`. Await every promise assertion: `await expect(p).rejects.toThrow()` (Vitest 5 fails the test when an async assertion is not awaited).
- No logic in tests (loops, branches) except to build table data; no shared mutable state between tests.
- Do not use `done` callbacks; use async functions. Keep `test.only` and `fit` out of commits: Vitest rejects `.only` when `CI` is set (`allowOnly` defaults to `!process.env.CI`); add a lint rule for Jest.
- Imports: Vitest tests import `describe, test, expect, vi` from `vitest` unless `globals: true`; Jest tests use globals or `@jest/globals`.
- Types: Jest TypeScript projects add `@types/jest` or import from `@jest/globals`; Vitest ships its own types, and `vitest/globals` goes into `tsconfig` `types` when `globals: true`.
- `expect.assertions(n)` and `expect.hasAssertions()` exist in both Jest and Vitest and are useful to prove that a catch block ran; they are not a substitute for awaiting.

## 6. Project Structure

```
src/
  pricing.ts
  pricing.test.ts            # colocated unit tests
  notifier.ts
  notifier.test.ts
  mailer.ts                  # boundary module, mocked in notifier tests
  Counter.tsx
  Counter.test.tsx
test/
  setup.ts                   # matchers, global cleanup (jest-dom)
  builders.ts                # test data builders
jest.config.js | vitest.config.ts
```

Keep one config per runner at the package root; in a monorepo use `projects` with one entry per package.

## 7. Design Patterns

- **Test data builders**: functions returning valid defaults with overrides (`anOrder({ qty: 0 })`), so each test states only the fields it cares about.
- **Fakes over mocks for stateful boundaries**: an in-memory repository implementing the same interface lets tests assert state instead of call sequences.
- **Ports and adapters**: depend on an interface (`Mailer`, `Clock`); tests pass a stub, production passes the adapter.
- **Table-driven tests**: `test.each([...])('...', ...)` with named fields; add `$field` placeholders to titles.
- **Fixtures** (Vitest `test.extend`): per-test setup with automatic teardown after `await use(value)`.
- **Custom matchers**: `expect.extend` for domain assertions, with typed declarations (`jest.Matchers` or Vitest's `Assertion` interface augmentation).
- **Contract tests for fakes**: run the same test table against the fake and the real adapter (the latter in integration tests).

## 8. Best Practices

- Reset state in `beforeEach`, not by relying on test order. In Jest set `restoreMocks`/`resetMocks` in config; in Vitest note that `clearMocks` is already on and add `mockReset` or `restoreMocks` when implementations must not leak.
- Always restore timers (`useRealTimers`), environment (`vi.stubEnv` with `unstubEnvs: true`, or save and restore `process.env`) and globals (`vi.stubGlobal` with `unstubGlobals: true`).
- Prefer Testing Library queries by role and accessible name (`getByRole`) and `userEvent` over `fireEvent`.
- Assert on outputs and effects visible to callers, not on private fields or call counts of internals.
- Keep a test failing for one reason; split tests whose names contain "and".
- Fix a flaky test by removing the nondeterminism (inject time, await the right promise), not by retrying or adding sleeps.
- Seed and print the seed for random or shuffled runs so failures reproduce (`--randomize` prints the seed in Jest; Vitest `--sequence.seed`).

## 9. Performance

- Unit tests should run in milliseconds each; keep real I/O out.
- Jest: `@swc/jest` or `babel-jest` over `ts-jest` for speed; set `maxWorkers` (for example `50%` in CI containers), use `workerIdleMemoryLimit` if workers grow, avoid `--runInBand` except for debugging.
- Vitest: `pool` defaults to `forks`; `threads` communicates faster but cannot use process APIs such as `process.chdir()`; `maxWorkers` limits parallelism; `isolate: false` reuses workers across files and is faster when tests are side-effect free (Vitest 5 prints a hint with the estimated gain); `--changed` runs tests affected by changes.
- Use `node` environment unless a test needs DOM; per-file `@vitest-environment jsdom` or `@jest-environment jsdom` docblocks keep the default cheap.
- Do not import large barrels in tests; import the module under test directly and mock heavy dependencies.
- Shard large suites (`--shard=1/4`) and merge reports.

## 10. Security

- No real secrets, tokens or production URLs in tests, snapshots or fixtures; use obviously fake values and stub `process.env` per test.
- Block accidental network calls: stub `fetch`/HTTP clients at the boundary, and fail tests that reach the network (a Jest `setupFilesAfterEnv` or Vitest `setupFiles` that replaces `globalThis.fetch` with a throwing stub is enough).
- Snapshots are committed artifacts: review them for tokens, emails and personal data, and use property matchers or redaction for volatile fields.
- Security-relevant units (authorization checks, input validation, signature verification) get negative tests: denied access, malformed input, wrong signature, expired token.
- CI: pass untrusted values through `env:` rather than interpolating `${{ inputs.* }}` or event text into `run:`; do not expose repository secrets to tests run for fork pull requests.
- Vitest UI and API server expose test files and results; in Vitest 5 the UI requires an authenticated URL. Do not bind them to public interfaces in shared environments.

## 11. Testing

- Test the tests: break the code on purpose (or run Stryker on critical modules) and confirm a test fails.
- Run shuffled and repeated runs to find order dependence: `vitest run --sequence.shuffle`, `jest --randomize`.
- Type-check tests in CI (`tsc --noEmit`), because swc and esbuild transforms do not check types.
- Use Vitest `--typecheck` for libraries whose types are part of the contract (type tests live in `*.test-d.ts` files by default); check the current docs for setup.
- Compare coverage deltas on pull requests; investigate uncovered branches in changed files.

## 12. Review Checklist

- [ ] Each test has one behavior, a clear name and an assertion that can fail.
- [ ] Mocks sit at boundaries and are reset or restored between tests.
- [ ] Timers, env vars and globals changed by a test are restored.
- [ ] No sleeps, no real network, no dependence on test order or wall-clock time.
- [ ] Promises are awaited; rejected paths are tested.
- [ ] Snapshots are small, reviewed and free of secrets.
- [ ] Coverage thresholds configured; `coverage.include` (Vitest) or `collectCoverageFrom` (Jest) lists source files so untested files appear.
- [ ] Config uses real keys: `setupFilesAfterEnv` (Jest), `test.projects` (Vitest), `describe.concurrent`/`describe.shuffle`.
- [ ] Tests are type-checked separately when the transformer does not do it.

## 13. Production Notes

- Pin runner, transformer and Node versions in the lockfile and CI image. Vitest 5 needs Node 22.12 or newer and Vite 6.4 or newer; Jest 30 needs Node 18 or newer and TypeScript 5.4 or newer for its types.
- Emit JUnit or JSON and coverage artifacts from CI; Vitest 5 writes reports under `.vitest/` (add it to `.gitignore`).
- Track flaky tests and slow tests (Jest `slowTestThreshold`, Vitest reporter durations) and fix them on a schedule.
- Upgrade runners deliberately: Jest 30 removed matcher aliases such as `toBeCalled` and `toThrowError`, renamed `--testPathPattern` to `--testPathPatterns` and dropped `jest.genMockFromModule`; Vitest 5 turned `clearMocks` on, hoists mock calls only at top level and removed `describe.sequential`. See the references for migration notes.

## 14. Examples

### Example 1: Pure function with table and error cases (Vitest)

```typescript
// src/pricing.ts
export type LineItem = { sku: string; unitCents: number; qty: number };

export function totalCents(items: LineItem[], discountPercent = 0): number {
  if (discountPercent < 0 || discountPercent > 100) {
    throw new RangeError('discountPercent must be between 0 and 100');
  }
  const subtotal = items.reduce((sum, item) => sum + item.unitCents * item.qty, 0);
  return Math.round((subtotal * (100 - discountPercent)) / 100);
}
```

```typescript
// src/pricing.test.ts
import { describe, expect, test } from 'vitest';
import { totalCents } from './pricing';

describe('totalCents', () => {
  test('sums quantity times unit price', () => {
    expect(totalCents([{ sku: 'a', unitCents: 250, qty: 2 }, { sku: 'b', unitCents: 100, qty: 1 }])).toBe(600);
  });

  test.each([
    { percent: 0, expected: 1000 },
    { percent: 25, expected: 750 },
    { percent: 100, expected: 0 },
  ])('applies a $percent% discount', ({ percent, expected }) => {
    expect(totalCents([{ sku: 'a', unitCents: 1000, qty: 1 }], percent)).toBe(expected);
  });

  test('rejects out-of-range discounts', () => {
    expect(() => totalCents([], 101)).toThrow(RangeError);
    expect(() => totalCents([], -1)).toThrow('between 0 and 100');
  });
});
```

The same file runs under Jest 30 by deleting the `vitest` import (globals) or importing from `@jest/globals`.

### Example 2: Module mock and fake timers (Vitest 5)

```typescript
// src/notifier.ts
import { sendMail } from './mailer';

export async function notifyWithRetry(to: string, body: string, attempts = 3, delayMs = 1000) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await sendMail(to, body);
    } catch (err) {
      if (attempt >= attempts) throw err;
      await new Promise((resolve) => setTimeout(resolve, delayMs * attempt));
    }
  }
}
```

```typescript
// src/notifier.test.ts
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

const { sendMail } = vi.hoisted(() => ({ sendMail: vi.fn() })); // available inside the hoisted factory
vi.mock('./mailer', () => ({ sendMail }));                         // top level only in Vitest 5

import { notifyWithRetry } from './notifier';

describe('notifyWithRetry', () => {
  beforeEach(() => {
    sendMail.mockReset();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  test('retries with growing delays and then succeeds', async () => {
    sendMail.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce({ id: 'm1' });

    const result = notifyWithRetry('a@example.com', 'hi');
    await vi.advanceTimersByTimeAsync(1000); // first backoff

    await expect(result).resolves.toEqual({ id: 'm1' });
    expect(sendMail).toHaveBeenCalledTimes(2);
  });

  test('gives up after the last attempt', async () => {
    sendMail.mockRejectedValue(new Error('down'));

    const outcome = expect(notifyWithRetry('a@example.com', 'hi', 2)).rejects.toThrow('down');
    await vi.runAllTimersAsync(); // attach the rejection handler first, then run the timers

    await outcome;
    expect(sendMail).toHaveBeenCalledTimes(2);
  });
});
```

### Example 3: The same test and config in Jest 30

```javascript
// jest.config.js
const { defineConfig } = require('jest');

module.exports = defineConfig({
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.test.{ts,tsx}'],
  transform: { '^.+\\.tsx?$': '@swc/jest' }, // no type-check: run `tsc --noEmit` separately
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'], // NOT setupFilesAfterEach: that key does not exist
  restoreMocks: true,
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.test.ts'],
  coverageProvider: 'v8',
  coverageThreshold: { global: { lines: 80, branches: 80 } },
});
```

```typescript
// src/notifier.test.ts
import { sendMail } from './mailer';
import { notifyWithRetry } from './notifier';

jest.mock('./mailer'); // hoisted above the imports; every export becomes a jest.fn()
const sendMailMock = jest.mocked(sendMail);

describe('notifyWithRetry', () => {
  beforeEach(() => {
    sendMailMock.mockReset();
    jest.useFakeTimers();
  });

  test('retries with growing delays and then succeeds', async () => {
    sendMailMock.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce({ id: 'm1' });

    const result = notifyWithRetry('a@example.com', 'hi');
    await jest.advanceTimersByTimeAsync(1000);

    await expect(result).resolves.toEqual({ id: 'm1' });
    expect(sendMailMock).toHaveBeenCalledTimes(2);
  });
});
```

`jest.setup.ts` holds `afterEach(() => jest.useRealTimers())` and, for DOM tests, `import '@testing-library/jest-dom'`. With `@swc/jest` 0.2.39, `jest.mock` was not hoisted when `jest` was imported from `@jest/globals`; use the global `jest` there, or use `babel-jest`/`ts-jest`.

## 15. Common Mistakes

| Mistake | Fix |
|---|---|
| `setupFilesAfterEach` in Jest config | No such key. Use `setupFilesAfterEnv` (after the framework is installed) or `setupFiles` (before) |
| `describe.serial` or `describe.sequential` in Vitest | `describe.serial` never existed. `describe.sequential` was removed in Vitest 5: use `describe('x', { concurrent: false }, ...)`. Available: `describe.concurrent`, `describe.shuffle` |
| Vitest `workspace` file or `poolOptions`, `minWorkers` | Use `test.projects`, top-level pool options and `maxWorkers` |
| Using a variable inside a hoisted `vi.mock` factory | Create it with `vi.hoisted`, or use `vi.doMock` plus a dynamic import |
| `vi.mock` inside `describe` or a function (Vitest 5 error) | Move to the top level; use `vi.doMock` for per-test mocks |
| Jest `jest.mock` factory referencing a variable not prefixed `mock` | Prefix with `mock`, use automock plus `jest.mocked`, or build the mock inside the factory |
| Unawaited `expect(p).rejects` / `.resolves` | Always `await`; Vitest 5 fails the test, Jest silently passes |
| Mock implementations leaking between tests | `mockReset()` in `beforeEach`, or `restoreMocks`/`mockReset` in config |
| Real timers and `setTimeout` waits | Fake timers with `advanceTimersByTimeAsync`, or inject a clock |
| Awaiting an unresolved rejection after running timers | Create the `expect(...).rejects` promise first, then advance timers (Example 2) |
| Snapshot of a whole component tree | Assert roles and text with Testing Library; keep snapshots small |
| Coverage that ignores untested files | Set `coverage.include` (Vitest) or `collectCoverageFrom` (Jest) |
| Expecting `coverageProvider` default to be v8 in Jest | Jest default is `babel`; Vitest default is `v8` |
| `ts-jest` with an unsupported TypeScript version | Pin a supported TypeScript or switch to `@swc/jest` and run `tsc --noEmit` |
| Old matcher aliases (`toBeCalled`, `toThrowError`) on Jest 30 | Use `toHaveBeenCalled`, `toThrow` |
| `jest --testPathPattern` on Jest 30 | Use `--testPathPatterns` |

## 16. References

- [references/jest.md](references/jest.md): Jest 30 configuration keys, transformers, projects, ESM mocking, timers, snapshots, React Testing Library, coverage, CLI, v29 to v30 upgrade notes.
- [references/vitest.md](references/vitest.md): Vitest 5 configuration, projects, mocking and `vi.hoisted`, fixtures, concurrency and shuffle, coverage providers, browser mode, in-source tests, Jest migration, v4 to v5 changes.
- [references/test-design.md](references/test-design.md): test doubles, builders, fakes, fast-check properties, mutation testing, time and randomness seams.
- Official docs: https://jestjs.io/docs/getting-started, https://vitest.dev/guide/, https://vitest.dev/guide/migration, https://fast-check.dev
