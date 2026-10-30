# Playwright in CI: Sharding, Reports and Flaky Policy

Verified against @playwright/test 1.64.1 and the Playwright CI, sharding and Docker docs (2026-10). Companion to [../SKILL.md](../SKILL.md).

## Config knobs for CI

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  forbidOnly: !!process.env.CI,          // fail if test.only is committed
  retries: process.env.CI ? 2 : 0,
  failOnFlakyTests: !!process.env.CI,    // same as --fail-on-flaky-tests
  fullyParallel: true,                   // test-level sharding balance
  workers: process.env.CI ? 2 : undefined, // docs suggest 1 for stability; measure on your runner
  globalTimeout: 30 * 60 * 1000,         // bound total CI cost
  reporter: process.env.CI ? [['blob'], ['github']] : [['list'], ['html', { open: 'never' }]],
  use: { trace: 'on-first-retry' },
});
```

- By default a run exits 0 when every failed test passed on retry. `failOnFlakyTests` (or `--fail-on-flaky-tests`) turns those into a failing exit code.
- `retryStrategy: 'isolated'` (1.62+) runs all retries at the end, one by one in a single worker; the default is `'immediate'`.
- Trace modes: `'on'`, `'off'`, `'on-first-retry'`, `'on-all-retries'`, `'retain-on-failure'`, `'retain-on-first-failure'`, `'retain-on-failure-and-retries'`. `'on-first-retry'` is the usual CI choice.
- `--shuffle [seed]` randomizes order (1.64+); the printed seed reproduces a failing order.
- `--last-failed` reruns only failures from the previous run; `--only-changed[=ref]` runs test files changed since the last commit or ref, plus files that import changed files.
- `--update-snapshots [mode]` accepts `all`, `changed`, `missing`, `none`, `default`. Since 1.64 the `missing` mode passes the run when it only creates missing snapshots, so CI can add new baselines and check existing ones in one run.
- A project can be excluded from plain `npx playwright test` with `default: false` (1.64+) and selected with `--project=name` or `--project="*"`.

## GitHub Actions: sharded run with merged report

Every `${{ }}` expression that lands in a shell command is routed through `env:`. Action versions below follow the current Playwright docs.

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
        shardIndex: [1, 2, 3, 4]
        shardTotal: [4]
    env:
      BASE_URL: ${{ vars.E2E_BASE_URL }}
      E2E_USER_EMAIL: ${{ secrets.E2E_USER_EMAIL }}
      E2E_USER_PASSWORD: ${{ secrets.E2E_USER_PASSWORD }}
      SHARD: ${{ matrix.shardIndex }}/${{ matrix.shardTotal }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: lts/*
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --shard="$SHARD"
      - uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: blob-report-${{ matrix.shardIndex }}
          path: blob-report
          retention-days: 1

  merge-reports:
    if: ${{ !cancelled() }}
    needs: [test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: lts/*
      - run: npm ci
      - uses: actions/download-artifact@v5
        with:
          path: all-blob-reports
          pattern: blob-report-*
          merge-multiple: true
      - run: npx playwright merge-reports --reporter html ./all-blob-reports
      - uses: actions/upload-artifact@v5
        with:
          name: html-report-attempt-${{ github.run_attempt }}
          path: playwright-report
          retention-days: 7
```

Notes:
- Secrets are exposed only to the job that needs them. Fork pull requests do not receive repository secrets; run authenticated suites on branches of the same repository, and never combine `pull_request_target` with checking out untrusted PR code.
- Never write `${{ inputs.x }}`, `${{ github.event.pull_request.title }}` or similar directly inside `run:`; assign to `env:` and use `"$VAR"`.
- The blob reporter writes `blob-report/`; names include the shard number so files from different shards do not clash.
- Merge across operating systems needs an explicit merge config (`--config`) so the tests root is unambiguous.
- Same tests in several environments (not shards): set `tag: process.env.CI_ENVIRONMENT_NAME` in the config so the merged report separates them.
- Selecting reporters at merge time: `--reporter=html,github`.

## Pull request fast path

```yaml
      - run: npx playwright test --only-changed="origin/$BASE_REF"
        env:
          BASE_REF: ${{ github.base_ref }}
```

This needs `fetch-depth: 0` (or an explicit fetch of the base branch) on checkout. Keep the full sharded suite on `main` and nightly.

## Docker image

Use the image that matches the installed version so browsers and system libraries line up:

```bash
docker run --rm --ipc=host -v "$PWD":/work -w /work mcr.microsoft.com/playwright:v1.64.1-noble npx playwright test
```

`--ipc=host` avoids Chromium running out of shared memory. For untrusted pages, the Playwright Docker docs describe running as the `pwuser` user with a seccomp profile (check the current docs for the profile). Generate screenshot baselines inside the same image CI uses.

## Flaky test policy

1. CI runs with `retries: 2` and `failOnFlakyTests`, so a pass-on-retry is a visible failure rather than green noise.
2. The first action on a flaky test is the trace of the failed first attempt (`on-first-retry`), then `--repeat-each=30`, then `--shuffle`.
3. Typical causes: missing web-first assertion, shared data between tests, animation or clock dependence, a race with a network call that should be awaited via `waitForResponse`, or an environment difference for snapshots.
4. Quarantine only with `test.fixme(condition, 'link-to-issue')` and an owner in the issue; do not raise retries globally.

## Reporters worth knowing

`list`, `line`, `dot`, `html`, `blob`, `json`, `junit`, `github` (annotations on GitHub), and the `perfetto` reporter added in 1.63 (timeline of workers). `--reporter` replaces the configured reporters; `--add-reporter` (1.63+) appends one.

## Playwright test agents in a pipeline

`npx playwright init-agents --loop=claude` writes planner, generator and healer definitions into the repository (also `--loop=vscode`, `codex`, `opencode`). Regenerate after every Playwright upgrade. Review generated tests like any other code: they must follow the locator, fixture and auth rules in SKILL.md, and healer changes that weaken assertions or skip tests need a human decision. `npx playwright test --debug=cli` lets a coding agent attach and debug over `playwright-cli`, and `npx playwright trace` lets it inspect traces from the command line.
