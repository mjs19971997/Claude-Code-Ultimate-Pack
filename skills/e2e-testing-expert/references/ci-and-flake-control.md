# CI, Sharding and Flake Control

Reference for running end-to-end suites in CI at a sustainable speed and keeping them trustworthy. Verified against Playwright 1.64.x (`--shard`, `--repeat-each`, `merge-reports`), Cypress 16.2.x with `cypress-split` 1.25.x, `actions/checkout`, `actions/setup-node` and `actions/upload-artifact` v7, `actions/download-artifact` v8 (2026-10). Playwright details beyond this page belong to playwright-expert.

## 1. Pipeline placement

| Suite | When | Budget |
|---|---|---|
| Smoke (3 to 10 critical journeys: sign in, core purchase or create flow) | Every push and before each deployment, also against the deployed environment | Under 5 minutes |
| Full regression | Pull requests that touch the app, and nightly | Under 20 to 30 minutes wall-clock with sharding |
| Cross-browser / mobile viewport | Nightly or pre-release | As needed |
| Visual regression | Pull requests (changed pages) or nightly | Separate job so baselines are reviewed on their own |

Tag tests (`@smoke` in the title with `--grep`, Playwright projects, or folders) rather than maintaining separate copies.

## 2. Playwright sharding with merged reports

Each shard runs a slice of the tests and emits a blob report; a final job merges them into one HTML report. The `playwright.config.ts` uses `reporter: [["blob"], ["list"]]` when `CI` is set.

```yaml
name: e2e
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4]
    env:
      SHARD: ${{ matrix.shard }}
      TOTAL_SHARDS: ${{ strategy.job-total }}
      E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test --shard="$SHARD/$TOTAL_SHARDS"
      - uses: actions/upload-artifact@v7
        if: ${{ !cancelled() }}
        with:
          name: blob-report-${{ matrix.shard }}
          path: blob-report
          retention-days: 1

  merge-reports:
    needs: [test]
    if: ${{ !cancelled() }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - uses: actions/download-artifact@v8
        with:
          path: all-blob-reports
          pattern: blob-report-*
          merge-multiple: true
      - run: npx playwright merge-reports --reporter html ./all-blob-reports
      - uses: actions/upload-artifact@v7
        with:
          name: playwright-report
          path: playwright-report
          retention-days: 14
```

Keep `fullyParallel: true` in the config so shards balance by test rather than by file. Do not upload the `playwright/.auth/` directory.

## 3. Cypress parallelization

Two approaches (full workflow in [cypress.md](cypress.md)):
- `cypress-split`: free; each matrix job sets `SPLIT` and `SPLIT_INDEX` and the plugin selects that job's spec files. Balance is by spec count unless you provide timings.
- Cypress Cloud: `record` plus `parallel` and a shared `group`/`ci-build-id`; Cloud balances by historical spec duration and can prioritize failed specs first.

Either way, give each parallel job its own database and server, and make specs independent so they can run in any order.

## 4. Environments in CI

- Start the application and its dependencies inside the job (service containers, Docker Compose, Testcontainers) with health checks, or target an ephemeral preview deployment; do not point pull-request jobs at a shared staging database.
- Pin the build under test: the commit SHA or image digest the job just built.
- Pass secrets as environment variables from the secret store. Fork pull requests do not receive secrets: run a reduced suite for forks or require maintainer approval before running the full suite.
- Never interpolate workflow inputs or event fields (`github.event.pull_request.title`, `inputs.*`) into `run:` scripts; pass them via `env:` and quote the variable.
- Upload traces, screenshots and videos on failure only, with short retention, and keep sensitive files (storage state, `cypress.env.json`) out of artifacts.

## 5. Flake taxonomy and fixes

| Symptom | Typical cause | Fix |
|---|---|---|
| Passes alone, fails in suite | Shared state, leftover rows, order dependence | Unique data per test; independent setup; random order in CI |
| Fails only in CI | Slower CPU, cold caches, different viewport or timezone | Wait on conditions, set viewport/timezone explicitly, check resource limits |
| Element not found / detached from DOM | Re-render between query and action | Re-query with auto-retrying locators; assert state before acting |
| Click intercepted or element covered | Animation, overlay, toast | Wait for the overlay to disappear by assertion; disable animations in the test environment |
| Wrong data shown | Race between request and assertion | Wait on the response (`cy.wait('@alias')`, `page.waitForResponse`) or on the visible result |
| Third-party timeouts | Real external service | Stub or use a sandbox; keep the real integration in a separate monitored suite |
| Time-dependent failures | Real clock (midnight, DST, expiry) | Fake the clock; seed relative to a fixed date |
| Parallel collisions | Same user, same email, global truncate | Per-worker accounts and unique values |

## 6. Policy for retries and quarantine

- Retries: 0 locally, 1 or 2 in CI. A test that passes only on retry is reported as flaky and counts against a flake budget.
- Quarantine: move a repeatedly flaky test to a non-blocking job or tag it `@quarantine`, open an issue with an owner and a deadline, and delete tests that are not fixed in time. Do not leave `test.skip` without a ticket.
- Track: flaky rate per test and per suite, retry count, median and p95 duration, time to first failure signal. Review weekly.
- Repro before fixing: Playwright `--repeat-each=30` (optionally `--workers=1` or many workers to stress), or a shell loop around `cypress run --spec`; reproduce with the CI browser and CPU limits.
- Use evidence: Playwright traces (`trace: "retain-on-failure"`), Cypress screenshots and Test Replay, network logs, console errors, server logs correlated by a request id header.
- After a fix, run the loop again and keep the test in the merge gate.

## 7. Keeping the suite small and fast

- E2E tests cover critical user journeys through the real UI and backend; push validation matrices, edge cases and rendering variants down to unit, component and integration tests.
- Prefer API setup over UI setup; log in once per role.
- One journey per test, a handful of meaningful assertions, no tests that depend on earlier tests.
- Delete tests that duplicate lower-level coverage or that nobody trusts.
- Review the slowest 10 tests monthly.
