---
name: playwright-expert
description: >-
  Designs and writes Playwright Test suites in TypeScript: role-based locators, web-first assertions and auto-waiting, setup projects with storageState authentication, test.extend fixtures, network mocking, API testing with the request fixture, aria and visual snapshots, traces, retries, sharding and merge-reports in CI. Use when working with playwright.config.ts, @playwright/test, *.spec.ts browser tests, page.route, expect.poll, toPass, toHaveScreenshot, toMatchAriaSnapshot, trace viewer, flaky E2E tests, or Playwright test agents and MCP. Not for choosing what to cover across the whole pyramid (use e2e-testing-expert), Jest or Vitest unit tests (use unit-testing-expert), or API and database integration tests without a browser (use integration-testing-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Playwright Expert

This skill covers writing and operating browser tests with Playwright Test: locator and assertion habits that avoid flakiness, authentication done once per run, fixtures for setup and cleanup, mocking and API-assisted setup, snapshot assertions, and CI configuration with sharding and merged reports. Examples are TypeScript against `@playwright/test`. The browser automation library on its own (scraping, scripts without the test runner) is outside this skill's focus.

> Verified against @playwright/test 1.64.1 (Node 20 or newer), release notes through 1.64, and the Playwright docs sources for auth, projects, sharding, webServer, assertions, clock and aria snapshots (2026-10).

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

- Covered: `playwright.config.ts`, projects and dependencies, locators, web-first assertions, `expect.poll` and `toPass`, fixtures, `storageState` auth, `page.route` mocking, the `request` fixture, `page.clock`, `toHaveScreenshot`, `toMatchAriaSnapshot`, traces and the HTML report, retries, sharding, blob reports, `webServer`, Playwright test agents and the bundled MCP server.
- Not covered: deciding which journeys deserve E2E coverage and test-pyramid strategy (e2e-testing-expert); unit tests of functions and components (unit-testing-expert); service and database integration tests (integration-testing-expert); building the CI platform itself (cicd-expert); accessibility rules beyond automated checks (accessibility-expert).

## 2. Core Expertise

- **Auto-waiting**: actions wait for the element to be attached, visible, stable, enabled and able to receive events. Web-first assertions (`expect(locator).toBeVisible()`, `toHaveText`, `toHaveURL`) retry until the expect timeout.
- **Locators**: `getByRole`, `getByLabel`, `getByText`, `getByPlaceholder`, `getByAltText`, `getByTitle`, `getByTestId`; compose with `filter`, `and`, `or`, `first`, `nth`. Locators are lazy and re-resolve on every use.
- **Isolation**: each test gets a fresh browser context (cookies, storage, cache). `fullyParallel: true` runs tests in one file in parallel; workers are separate processes that never share state.
- **Projects**: named configurations (browser, device, `storageState`, `testMatch`). `dependencies: ['setup']` runs the listed projects first and skips dependents if they fail; `teardown` runs after dependents.
- **Fixtures**: `test.extend<T, W>()` provides per-test or per-worker (`scope: 'worker'`) setup with automatic teardown after `await use(...)`; options (`option: true`) let projects override values; `auto: true` runs a fixture for every test.
- **Retry helpers**: `expect.poll(fn)` retries a value, `expect(async () => {...}).toPass()` retries a block (default timeout 0, so pass `timeout`), `expect.soft` records a failure without stopping the test.
- **Network**: `page.route` / `context.route` to fulfill, modify or abort; `routeFromHAR`; `page.waitForResponse`; the `request` fixture for direct HTTP calls that share `baseURL`, headers and `storageState` with the project.
- **Time**: `page.clock.setFixedTime`, `install`, `pauseAt`, `fastForward`, `runFor` control `Date` and timers in the page.
- **Snapshots**: `toHaveScreenshot` (pixel compare, per platform), `toMatchAriaSnapshot` (accessibility tree as YAML, stable across styling changes), `toMatchSnapshot` for text and binary data.
- **Diagnostics**: `trace: 'on-first-retry'`, Trace Viewer (`npx playwright show-trace`), HTML report, UI Mode (`--ui`), `--debug`, `npx playwright codegen`.
- **Agents**: `npx playwright init-agents --loop=claude` (also `vscode`, `codex`, `opencode`) writes planner, generator and healer agent definitions; the Playwright MCP server (`@playwright/mcp`, also bundled as `npx playwright mcp`) lets an agent drive a browser.

## 3. Workflow

1. Pick a user journey and its pass/fail condition in one sentence; decide what must be real (the app, the login) and what can be mocked (third-party APIs, payment, email).
2. Set up the config once: `baseURL`, `webServer`, a `setup` project for login, `trace: 'on-first-retry'`, retries only in CI.
3. Explore with `npx playwright codegen` or UI Mode, then rewrite generated selectors to role and label locators.
4. Seed data through the API or a fixture (unique per test), not by clicking through the UI.
5. Write the test as steps with web-first assertions on user-visible outcomes; no fixed sleeps.
6. Run it repeatedly: `npx playwright test path --repeat-each=20` plus `--workers=1` and a normal parallel run. Add `--shuffle` to find order dependence.
7. Open the trace of any failure before changing code; fix the cause (missing assertion, shared data, race) rather than adding a retry.
8. In CI: install browsers, run (sharded if needed), upload the report and traces, optionally fail the run on flaky tests (`--fail-on-flaky-tests`).

## 4. Decision Rules

- Prefer `getByRole` with an accessible name; fall back to `getByLabel`/`getByText`, then `getByTestId`; avoid CSS and XPath tied to layout. A role locator that is hard to write often signals an accessibility defect.
- Assert with web-first matchers on locators. Use `expect.poll` for values that are not locators (API state), `toPass` for multi-step retried blocks. Never `expect(await locator.isVisible()).toBe(true)`; it does not retry.
- Share login across tests with a setup project and `storageState` when tests do not mutate per-account server state; use one account per worker (worker-scoped `storageState` fixture) when they do.
- Mock only what is outside the system under test or too slow and flaky to call; keep at least one test per critical flow against the real backend.
- Use `page.clock` for time-dependent UI instead of waiting real time or editing system clocks.
- Choose `toMatchAriaSnapshot` for structure and content, `toHaveScreenshot` for layout and styling regressions. Screenshots need a pinned environment (same OS image, same browser build).
- `fullyParallel: true` plus sharding balances at test level; without it sharding balances at file level.
- Retries: 0 locally, 1-2 in CI. A test that passes only on retry is flaky; `failOnFlakyTests` makes that visible.
- Use `test.describe.configure({ mode: 'serial' })` only for steps that truly depend on each other; prefer independent tests. Use `lock` (test locks, 1.63+) for a shared external resource, check the current docs for its exact semantics.

## 5. Coding Standards

- Import `test` and `expect` from `@playwright/test`, or from one project fixtures module that re-exports `expect`.
- One behavior per test; test titles describe the outcome ("shows an error when the card is declined").
- No `page.waitForTimeout`, no `networkidle` waits, no `force: true` to silence actionability failures; wait on an observable condition instead.
- Locators live in variables or page objects, assertions in the test body.
- Use `baseURL` and relative `page.goto('/path')`.
- `test.step('title', async () => {...})` groups long tests so traces and reports read as a story; `{ box: true }` hides helper internals from error locations.
- Tag tests (`test('x', { tag: '@smoke' }, ...)`) and select with `--grep @smoke`.
- `expect.soft` for independent checks in one page state; hard assertions when later steps depend on the result.
- Names for stored state and test data include the worker or test id so parallel runs never collide.
- Playwright's `expect` is not Jest's: there is no `expect.assertions()` or `expect.hasAssertions()`. Use `expect.configure({ timeout, soft })`, `expect.poll`, `expect.extend` for custom matchers.

## 6. Project Structure

```
playwright.config.ts
playwright/.auth/              # generated storageState, git-ignored
fixtures/
  index.ts                     # test.extend: page objects, API-seeded data
tests/
  auth.setup.ts                # setup project: log in, save storageState
  orders.spec.ts
  checkout.anon.spec.ts        # logged-out journeys, no stored state
  a11y.spec.ts
  orders.spec.ts-snapshots/    # written by toHaveScreenshot, one file per project and platform
```

Add `playwright/.auth`, `test-results`, `playwright-report` and `blob-report` to `.gitignore`.

## 7. Design Patterns

- **Setup project**: a `*.setup.ts` test logs in once and writes `storageState`; test projects list it in `dependencies` and load the file via `use.storageState`.
- **Fixture over page object inheritance**: expose page objects and seeded data as fixtures (`test.extend`); cleanup after `await use(...)` runs even when the test fails.
- **API-seeded UI tests**: create preconditions with the `request` fixture, drive only the behavior under test in the browser, verify side effects through the API.
- **Worker-scoped resources**: expensive setup (an account, a database schema per worker) as a `scope: 'worker'` fixture keyed by `testInfo.parallelIndex`.
- **Mock at the edge**: `page.route('**/api/third-party/**', ...)` with typed fixtures for payloads; keep mocks next to the tests that use them.
- **Option fixtures**: `base.extend<{ tenant: string }>({ tenant: ['acme', { option: true }] })` lets a project change the value through `use`. Do not reuse built-in option names such as `locale`.

## 8. Best Practices

- Keep tests independent: no reliance on order, on data from another test, or on leftover server state.
- Create unique data per test (`crypto.randomUUID()` in names, emails on a test domain) and delete it in fixture teardown.
- Configure `testIdAttribute` if the app uses `data-qa` instead of `data-testid`.
- Use `locator.filter({ hasText })`, `filter({ has })` and chained parent-then-child locators to disambiguate instead of `nth`.
- Wait for the outcome of an action (`await expect(page).toHaveURL(...)`) rather than for the action's side channel.
- Run the suite headed or in UI Mode while authoring; run headless in CI against the same browser versions as the lockfile (`npx playwright install` after upgrading).
- Upgrade `@playwright/test` and regenerate browsers together; regenerate agent definitions (`init-agents`) after upgrades.
- Use `--only-changed` (optionally `--only-changed=main`) on pull requests for a fast first signal, and still run the full suite on the main branch.

## 9. Performance

- Parallelize: `fullyParallel: true`, CI `workers` sized to the runner (the docs suggest 1 worker for stability; raise it on larger runners and measure), then shard across jobs with `--shard=i/n`.
- Authenticate once (setup project) rather than per test; seed with API calls, not UI clicks.
- Block heavy third-party resources (analytics, video) with `page.route` and `route.abort()` where they are irrelevant.
- `trace: 'on-first-retry'` keeps passing runs cheap; `'retain-on-failure'` records every test and keeps failures only.
- Keep screenshots small: use element screenshots and `mask` for dynamic areas.
- Reuse the dev server locally (`reuseExistingServer: !process.env.CI`), build once and run `start` rather than `dev` in CI.
- `retryStrategy: 'isolated'` (1.62+) runs retries at the end in one worker, so retries do not slow healthy tests; check the current docs before relying on it.

## 10. Security

- Credentials come from environment variables or the CI secret store (`E2E_USER_EMAIL`, `E2E_USER_PASSWORD`); never hard-code them or commit `.env` files. Use dedicated test accounts with least privilege.
- Authenticate through the real login flow or the real API in a setup project. Do not add a test-only login route, header or token that mints sessions; if the app needs one, build it only into non-production artifacts and verify the production build lacks it.
- `playwright/.auth/*.json`, traces, HAR files and videos contain cookies, tokens and request bodies. Git-ignore them, set short artifact retention, and restrict who can download CI artifacts.
- Run against local, preview or staging environments, never against production data; destructive tests need an environment guard (`if (baseURL.includes('prod')) throw ...`).
- `ignoreHTTPSErrors: true` only for local self-signed certificates, never in shared configs.
- In GitHub Actions, give the workflow `permissions: contents: read`, pass untrusted values (PR titles, inputs) through `env:` and never interpolate `${{ inputs.* }}` or `github.event.*` text into `run:`. Do not run workflows with secrets on `pull_request_target` against untrusted PR code.
- Treat pages under test as untrusted input to the test: do not `eval` page content or write page text to paths.

## 11. Testing

- Stabilize a suspect test: `--repeat-each=30 --workers=4`, then `--shuffle`, then `--retries=0 --trace=on`.
- Detect flakiness in CI: retries >= 1 with `--fail-on-flaky-tests` (or `failOnFlakyTests: true`), then track tests flagged as flaky in the report.
- Verify the setup project actually authenticates: a spec that opens a signed-in page and asserts an account element, run in the authenticated project.
- For mocked flows, add an assertion on the request payload the UI sent (`page.waitForRequest` or inspecting `route.request().postDataJSON()`).
- Accessibility smoke checks with `@axe-core/playwright` complement, but do not replace, role-based locators and manual review.

## 12. Review Checklist

- [ ] Locators are role/label/text based; no brittle CSS chains or `nth` without justification.
- [ ] Every assertion is web-first, `expect.poll` or `toPass`; no sleeps, no `waitForTimeout`.
- [ ] Tests are independent and use unique data; fixtures clean up after `use()`.
- [ ] Authentication happens in a setup project, writes git-ignored `storageState`, and reads credentials from the environment.
- [ ] No test-only bypass reachable in production; no secrets in the repo, traces or logs.
- [ ] Mocks cover only external dependencies; at least one real end-to-end path per critical flow.
- [ ] Snapshot tests run in a pinned environment and mask dynamic content; snapshot updates are reviewed.
- [ ] CI uploads reports and traces, uses `env:` for expressions in `run:`, and fails on `forbidOnly`.
- [ ] No Jest-only APIs (`expect.assertions`, `jest.fn`) in Playwright files.

## 13. Production Notes

- Treat E2E failures like production incidents for flakiness: keep a flaky-test list, fix or quarantine with a tracked reason (`test.fixme` with a link) rather than raising retries.
- Pin the Playwright version in the lockfile and use the matching Docker image (`mcr.microsoft.com/playwright:v1.64.1-noble`, run with `--ipc=host`) for consistent browsers and fonts.
- Store blob reports per shard and publish one merged HTML report; keep traces for failures only.
- Set `globalTimeout` in the config to bound CI cost.
- Run a small `@smoke` subset after each deploy against the deployed environment, read-only or on disposable data.
- Visual baselines belong to one platform; generate them in the same container image used by CI.

## 14. Examples

### Example 1: Config with setup project and authenticated state

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'http://localhost:3000';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  failOnFlakyTests: !!process.env.CI,
  reporter: process.env.CI ? [['github'], ['blob']] : [['list'], ['html', { open: 'never' }]],
  use: { baseURL, trace: 'on-first-retry', screenshot: 'only-on-failure' },
  // Start the app only for local runs; CI points BASE_URL at a deployed preview.
  webServer: process.env.BASE_URL
    ? undefined
    : { command: 'npm run start', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI, timeout: 120_000 },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
      testIgnore: /.*\.anon\.spec\.ts/,
    },
    { name: 'chromium-anon', use: { ...devices['Desktop Chrome'] }, testMatch: /.*\.anon\.spec\.ts/ },
  ],
});
```

```typescript
// tests/auth.setup.ts: the setup project really logs in and saves the state
import fs from 'node:fs';
import path from 'node:path';
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json'; // git-ignored

setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;
  if (!email || !password) throw new Error('Set E2E_USER_EMAIL and E2E_USER_PASSWORD (a dedicated test account).');

  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  // Wait for a signed-in element so redirects finish and cookies are set before saving.
  await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible();

  fs.mkdirSync(path.dirname(authFile), { recursive: true });
  await page.context().storageState({ path: authFile });
});
```

The label and button names must match your login form. See [references/auth-and-fixtures.md](references/auth-and-fixtures.md) for per-worker accounts, role-based states and sessionStorage.

### Example 2: Fixtures with API seeding and cleanup

```typescript
// fixtures/index.ts
import { test as base, expect } from '@playwright/test';

type Order = { id: string };

export const test = base.extend<{ order: Order }>({
  // Seed through the API using the authenticated request context; delete after the test, even on failure.
  order: async ({ request }, use) => {
    const res = await request.post('/api/orders', { data: { sku: 'sku-1', qty: 1 } });
    expect(res.ok()).toBeTruthy();
    const order = (await res.json()) as Order;
    await use(order);
    await request.delete(`/api/orders/${order.id}`);
  },
});

export { expect };
```

### Example 3: Retrying values, mocks, time and snapshots

```typescript
import { test, expect } from '../fixtures';

test('export completes', async ({ page, request }) => {
  await page.goto('/orders');
  await page.getByRole('button', { name: 'Export' }).click();
  await expect
    .poll(async () => (await request.get('/api/exports/latest')).json(), { timeout: 30_000 })
    .toMatchObject({ status: 'done' });
});

test('shows an error state when the API fails', async ({ page }) => {
  await page.route('**/api/orders', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"boom"}' }),
  );
  await page.goto('/orders');
  await expect(page.getByRole('alert')).toContainText('Something went wrong');
});

test('trial banner on the last day', async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-01-31T10:00:00Z'));
  await page.goto('/billing');
  await expect(page.getByText('Trial ends today')).toBeVisible();
});

test('navigation structure and layout', async ({ page }) => {
  await page.goto('/orders');
  await expect(page.getByRole('navigation')).toMatchAriaSnapshot(`
    - navigation:
      - link "Orders"
      - link "Billing"
  `);
  await expect(page.getByRole('main')).toHaveScreenshot('orders.png', {
    mask: [page.getByTestId('relative-time')],
  });
});
```

## 15. Common Mistakes

| Mistake | Fix |
|---|---|
| Logging in inside every test, or a "login" example that never submits credentials | Setup project that fills the form with env credentials, waits for a signed-in element, then saves `storageState` |
| `expect.assertions(1)` or `jest.fn()` in a Playwright test | Not Playwright APIs; use web-first assertions, `expect.poll`, `page.route` handlers |
| `await page.waitForTimeout(2000)` | Assert the outcome: `await expect(locator).toBeVisible()` |
| `expect(await el.isVisible()).toBe(true)` | `await expect(el).toBeVisible()` (retries) |
| `toPass()` with no timeout | Default timeout is 0 (no limit within the test timeout); pass `{ timeout }` and `intervals` |
| Tests share a user and mutate settings in parallel | One account per worker, or unique data per test |
| Screenshots generated on a laptop, compared in CI | Generate and compare in the same container image |
| Committing `playwright/.auth` or uploading traces publicly | Git-ignore, short retention, restricted artifacts |
| `${{ inputs.x }}` or PR text inside a workflow `run:` | Pass through `env:` and reference the shell variable |
| Raising `retries` to hide flakiness | Open the trace, fix the race; use `--fail-on-flaky-tests` |
| Selecting by generated CSS classes or `nth(3)` | Roles, labels, test ids, or `filter({ has })` |
| Mocking everything | Keep real-backend coverage for critical journeys |

## 16. References

- [references/auth-and-fixtures.md](references/auth-and-fixtures.md): per-worker accounts, multiple roles, API login, sessionStorage, fixture scopes, option and auto fixtures.
- [references/ci-and-sharding.md](references/ci-and-sharding.md): GitHub Actions with sharding and merge-reports, Docker image, `--only-changed`, flaky policy, reporters, timeouts.
- [references/visual-and-api-testing.md](references/visual-and-api-testing.md): `toHaveScreenshot` options, aria snapshots, `request` fixture, route mocking, clock, test agents and MCP.
- Official docs: https://playwright.dev/docs/intro, https://playwright.dev/docs/release-notes, https://playwright.dev/docs/auth, https://playwright.dev/docs/test-sharding, https://playwright.dev/docs/test-agents
