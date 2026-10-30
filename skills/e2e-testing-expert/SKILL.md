---
name: e2e-testing-expert
description: >-
  Plans and writes browser end-to-end tests for critical user journeys: strategy and test pyramid, choosing Playwright or Cypress, test data seeded through the API or test-environment fixtures (never a seed or reset endpoint in production), authentication state reuse, role and test-id selectors, network stubbing, visual regression, flake control, sharded CI runs and environments. Covers Cypress 16 in depth (cy.session, cy.intercept, cy.task, cy.env, component testing, retries). Use when designing an E2E suite, writing or reviewing Cypress specs, migrating Cypress versions, or fixing slow or flaky browser tests. Not for Playwright API detail (use playwright-expert), service-level tests (use integration-testing-expert) or unit tests (use unit-testing-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# E2E Testing Expert

This skill covers end-to-end testing through a real browser: which journeys to automate, how to choose and structure the tooling, how to create data and sign in without slowing tests down, and how to keep the suite fast and stable in CI. It absorbs the former cypress-expert skill; Cypress specifics are in a dedicated reference. Playwright-specific mechanics are covered by playwright-expert.

> Verified against Cypress 16.2.x (Node 22, 24 or 26+), Playwright 1.64.x, `cypress-io/github-action` v7, `cypress-split` 1.25.x, PostgreSQL 18 service containers and GitHub Actions `checkout`/`setup-node`/`upload-artifact` v7 (2026-10).

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

- Covered: E2E strategy and the test pyramid, journey selection, Playwright versus Cypress, test data and seeding, authentication reuse, selectors, network stubbing, visual regression, flake control, CI sharding, environments, Cypress (config, `cy.session`, `cy.intercept`, `cy.task`, `cy.env`, component testing, version migration).
- Not covered: Playwright APIs, fixtures, trace viewer and configuration depth (playwright-expert); HTTP-level service tests and contract tests (integration-testing-expert); isolated unit tests (unit-testing-expert); accessibility audits beyond basic checks (accessibility-expert); load testing (performance-optimization-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Pyramid | Many unit tests, a moderate number of integration tests, few E2E tests for critical journeys |
| Playwright | Multi-browser (Chromium, Firefox, WebKit), `storageState` auth reuse, `getByRole`, trace viewer, `--shard`, blob report merge; see playwright-expert |
| Cypress 16.2 | Runs in the browser with retrying queries; `cy.session`, `cy.intercept`, `cy.task` (Node), `cy.env` for secrets, `Cypress.expose` for public values, `cy.getByRole`, component testing; requires Node `^22 \|\| ^24 \|\| >=26` |
| Test data | API setup and Node-side fixtures against the test database; unique data per test; no seed or reset endpoint in any production artifact |
| Auth reuse | `cy.session` (Cypress) or `storageState` from a setup project (Playwright); log in through the API |
| Selectors | Accessible role and name first, `data-testid`/`data-cy` where roles are ambiguous, never CSS structure |
| Network control | Stub third-party calls (`cy.intercept`, `page.route`); keep first-party calls real |
| Flake control | Auto-waiting and retrying assertions, unique data, no fixed sleeps, fake clocks, retries only as a measured safety net |
| CI | Smoke on every push, full suite on pull requests and nightly, sharding by machine, artifacts on failure |

## 3. Workflow

1. List critical user journeys with the product owner: revenue paths, sign-up and sign-in, core create-edit-share flows, anything whose failure is an incident. Rank by business risk and usage.
2. For each journey, record the preconditions (user role, existing data), the steps, and the observable outcomes. Push validation rules and edge cases to lower test levels.
3. Choose the tool (see Decision Rules) and set up the project: configuration, base URL, environment variables, folder layout.
4. Build the data layer: factories that call public APIs, Node-side fixtures for the test database, an idempotent seeding step, and the guard that prevents destructive helpers from running against anything but test databases.
5. Build the authentication layer: one login per role through the API, reused via `cy.session` or `storageState`.
6. Write each journey as one test with user-visible assertions. Stub third-party services at the network layer.
7. Run each test alone, repeated, in parallel and in CI-like conditions before merging. Fix flakes at the cause.
8. Wire CI: smoke on push, full on pull request, sharded, artifacts on failure, flake report.
9. Review the suite regularly: remove duplicated coverage, quarantine and fix flaky tests, keep the duration within budget.

## 4. Decision Rules

- E2E only for critical journeys that need the real browser and the whole stack. If an integration or component test can prove it, use that.
- Playwright for new projects needing multiple browsers (including WebKit), multiple tabs or origins, fast parallel runs, and traces; Cypress when the team already uses it, values its interactive runner and component testing in the same tool, or targets Chromium-family browsers and Firefox. Do not run both on the same journeys. Playwright detail: playwright-expert.
- API or fixture setup over UI setup, always. Only the journey under test goes through the UI.
- Log in once per role through the API and reuse the session. Keep a few UI login tests.
- Stub third-party services (payments, maps, analytics, email delivery); keep first-party backend calls real so the test verifies the integration.
- Seed data from test tooling that connects to the test environment. If a test-only HTTP endpoint cannot be avoided, it exists only in a separate e2e build that production never contains; a runtime flag alone is not acceptable ([references/test-data-and-environments.md](references/test-data-and-environments.md)).
- Selectors: role and accessible name first; `data-testid` or `data-cy` next; visible text when the text is the requirement; never class names, tag chains or `nth-child`.
- Retries: zero locally, at most two in CI, always reported. A retry is not a fix.
- Visual regression: use for stable, high-value pages and components, in a dedicated job with reviewed baselines; do not use it as a substitute for functional assertions.
- Shared staging versus ephemeral environments: prefer an ephemeral environment per job or pull request; use shared staging only for checks that need real sandboxes, with synthetic tenants.

## 5. Coding Standards

- One journey per test, named by user outcome: `buys a product and sees the confirmation`. No test depends on another test's side effects.
- Assert what the user sees or can verify (headings, messages, URL, persisted state through a UI or API read), not implementation details such as internal state or CSS classes.
- Use retrying assertions on locators or queries; do not read a value and assert on it later.
- No fixed delays (`cy.wait(2000)`, `page.waitForTimeout`). Wait on an assertion, a response alias or a URL.
- Keep selectors in the test or in small helper commands/fixtures; avoid deep page-object hierarchies that hide what a test does.
- Put environment specifics (base URL, accounts) in configuration and environment variables; never hardcode secrets.
- Type custom commands and fixtures (TypeScript), including Cypress `Chainable` declarations.
- Keep test files short: one feature area per spec; extract data creation to helpers.
- Lint the suite: `eslint-plugin-cypress` or the Playwright ESLint rules to catch `.only`, unhandled promises and unsafe waits.

## 6. Project Structure

```
.
├── cypress.config.ts            # or playwright.config.ts
├── cypress/
│   ├── e2e/                     # journeys: checkout.cy.ts, onboarding.cy.ts
│   ├── component/               # optional component specs
│   ├── fixtures/                # static JSON used by stubs (inside fixturesFolder)
│   └── support/
│       ├── e2e.ts               # imports commands
│       ├── commands.ts          # loginAs() with cy.session, small helpers
│       └── db-tasks.ts          # Node-only seeding tasks with a test-database guard
├── tests/                       # Playwright layout: *.spec.ts, auth.setup.ts
├── playwright/.auth/            # gitignored storage state files
├── src/
│   ├── server.ts                # production entrypoint, no test routes
│   └── server.e2e.ts            # optional e2e-only entrypoint (separate build)
└── .github/workflows/e2e.yml    # smoke, full, sharding, artifacts
```

## 7. Design Patterns

- **Journey test**: arrange through API or fixtures, act through the UI, assert user-visible outcomes and one persisted effect.
- **Session reuse**: `cy.session(["user", email], setup, { validate })` or a Playwright setup project that writes `storageState`; details in [references/cypress.md](references/cypress.md) and [references/test-data-and-environments.md](references/test-data-and-environments.md).
- **Node-side seeding**: `cy.task("db:upsertProducts", ...)` or Playwright global setup/fixtures write to the test database; a guard throws unless the target is a local `*_e2e` database.
- **Boundary stubbing**: intercept only third-party hosts; alias the call and assert on the request the app sent.
- **Fault injection**: delay or fail one first-party response (`req.continue`, `forceNetworkError`, `route.abort()`) to test loading and error states.
- **Smoke tag**: a small, stable subset runs after every deployment against the deployed environment.
- **Data-per-test**: unique emails/ids so parallel workers and retries never collide.
- **Component tests for widgets**: Cypress component testing or Playwright component testing for interaction-heavy components; E2E keeps the integrated journeys.
- **Visual baselines**: pinned viewport, frozen time, stubbed data, masked dynamic regions, baselines reviewed in pull requests.

## 8. Best Practices

- Use accessible names in tests; it keeps the suite aligned with accessibility work (`cy.getByRole` in Cypress 16.2+, `getByRole` in Playwright).
- Start the application before the test runner; never start servers from inside a test task.
- Keep the test environment close to production configuration: same build, same database engine, same feature flags except documented test settings.
- Disable or shorten animations in the test environment through application configuration rather than test hacks.
- Make failure output useful: screenshots, traces, console and network logs, server logs correlated by request id.
- Version and review test accounts and fixtures like code; document how to run a single spec locally.
- Keep the suite deterministic: fixed viewport, locale and timezone; fake time for time-based UI.
- Prefer feature-focused specs over page mirrors; split a spec when it grows slow or needs different setup.
- Treat the suite as a product: owners, a flake budget, and a monthly review of the slowest and most failing tests.

## 9. Performance

- Authenticate once per role; reuse sessions across specs (`cacheAcrossSpecs`, Playwright `storageState`).
- Create data through APIs (milliseconds) rather than UI (seconds).
- Parallelize: files across workers and machines; shard in CI (`--shard=1/4`, `cypress-split`, or Cypress Cloud parallelization); give each machine its own database and server.
- Run the smoke subset first and fail fast; run slower cross-browser and visual jobs separately.
- Trim waiting: rely on auto-waiting and aliases; avoid long timeouts that hide slowness.
- Run headless in CI; cache dependencies and browser binaries.
- Keep traces and videos to failures or first retries to save time and storage.
- Track the median and p95 spec duration; split specs above a threshold.

## 10. Security

- No seed, reset, impersonation or feature-flag endpoint in any production build. Prefer tooling that talks to the test database directly; if an HTTP surface is unavoidable, build it into a separate e2e artifact and fail the production pipeline if its marker appears in the production build ([references/test-data-and-environments.md](references/test-data-and-environments.md)).
- Guard destructive helpers: allowlist hosts, require a database-name suffix, throw on mismatch.
- Secrets (test passwords, API keys, record keys) come from the CI secret store. In Cypress read them with `cy.env([...])`; `Cypress.expose()` is for public values only; `Cypress.env()` no longer exists in Cypress 16.
- Do not commit `cypress.env.json`, `.env`, or `playwright/.auth/*` (session cookies). Do not upload them as artifacts.
- Use dedicated test accounts with least privilege, marked as test accounts, in test environments only. Never reuse real user credentials or production data.
- Do not weaken the application for testing: no authentication bypass header, magic OTP code, disabled CSRF or permissive CORS in builds that can reach users.
- CI workflows: pass inputs and event fields through `env:` instead of interpolating `${{ inputs.* }}` or `${{ github.event.* }}` in `run:`; limit `permissions:`; do not give fork pull requests access to secrets.
- Third-party sandboxes only; no live payment instruments in tests.

## 11. Testing

- Prove each test can fail: break the feature, or remove the stub, and confirm red.
- Run new tests alone, in the full suite, repeatedly (`--repeat-each=20` in Playwright or a loop around `cypress run --spec`), and in parallel.
- Run with reduced CPU or a throttled network on a schedule to expose timing assumptions.
- Test the guards: a unit test that the seeding guard rejects a production-looking URL; a CI check that the production build lacks the e2e route marker.
- Verify stub strictness: unstubbed third-party calls should fail or be visible in logs.
- Measure flake rate and retry counts; fail the build when retries exceed a threshold.
- Cross-browser: run the smoke suite on each supported engine; run the full suite on the primary engine.
- Accessibility smoke checks (axe) can run inside journeys; deeper audits belong to accessibility-expert.

## 12. Review Checklist

- [ ] Each test covers a critical journey that lower test levels cannot cover.
- [ ] Data is created by API or Node-side fixtures, unique per test, and set up before the test (not in `after` hooks).
- [ ] No seed/reset/test endpoint can reach production; guard and build checks exist.
- [ ] Authentication is reused; credentials come from secrets.
- [ ] Selectors use roles, accessible names or test ids; no CSS structure.
- [ ] No fixed sleeps; waits are on assertions, aliases or responses.
- [ ] Third-party calls are stubbed or use sandboxes; first-party calls are real.
- [ ] Retries are limited and reported; flaky tests are tracked with owners.
- [ ] CI shards the suite, uploads failure artifacts without secrets, and has timeouts.
- [ ] Workflow files contain no `${{ inputs.* }}` or `${{ github.event.* }}` inside `run:`.

## 13. Production Notes

- Gate deployments on the smoke suite run against the deployed candidate; run it again after the production deployment using synthetic, read-only or self-cleaning journeys.
- Never run seeding, reset or destructive tests against production. Production monitoring uses a dedicated synthetic account and safe actions only.
- Keep the e2e environment's configuration and secrets separate from production; rotate test credentials.
- Publish test reports and trends; a red suite blocks merges, a flaky suite is fixed within the sprint.
- When a journey breaks in production, add or fix the E2E test and also the lower-level test that should have caught it.
- Budget infrastructure: CI minutes, parallel machines, Cypress Cloud or reporting costs, and artifact retention.
- Upgrade test tooling on a schedule (Cypress majors, Playwright releases, browsers) in a separate pull request with a green full run; read the changelog first ([references/cypress.md](references/cypress.md) has the Cypress 15 and 16 notes).

## 14. Examples

Cypress journey with API login, Node-side seeding and a stubbed third-party call (type-checked against Cypress 16.2.1; `loginAs` and `db:upsertProducts` are defined in [references/cypress.md](references/cypress.md)):

```ts
describe("checkout", () => {
  const email = "shopper@example.test";

  before(() => {
    cy.task("db:upsertProducts", [{ sku: "TEE-1", name: "T-shirt", priceCents: 2500 }]);
  });

  beforeEach(() => {
    cy.loginAs(email);
  });

  it("buys a product and shows the confirmation", () => {
    cy.intercept("POST", "/api/payments", { statusCode: 201, body: { status: "paid" } }).as("pay");

    cy.visit("/products/TEE-1");
    cy.getByRole("button", { name: "Add to cart" }).click();
    cy.get("[data-testid=cart-link]").click();
    cy.getByRole("button", { name: "Pay now" }).click();

    cy.wait("@pay").its("request.body").should("deep.include", { sku: "TEE-1" });
    cy.getByRole("heading", { name: "Thank you for your order" }).should("be.visible");
  });
});
```

The same journey in Playwright, using the `storageState` produced by a setup project (type-checked against Playwright 1.64.1):

```ts
import { test, expect } from "@playwright/test";

test("buys a product and shows the confirmation", async ({ page }) => {
  await page.route("**/api/payments", (route) =>
    route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ status: "paid" }) }),
  );

  await page.goto("/products/TEE-1");
  await page.getByRole("button", { name: "Add to cart" }).click();
  await page.getByTestId("cart-link").click();
  await page.getByRole("button", { name: "Pay now" }).click();

  await expect(page.getByRole("heading", { name: "Thank you for your order" })).toBeVisible();
});
```

Production build gate for the "no test surface" rule (the production bundle is built from `src/server.ts`, which never imports the e2e routes):

```bash
npx esbuild src/server.ts --bundle --platform=node --format=esm --packages=external --outfile=dist/server.js

if grep -rq "__test__" dist/; then
  echo "test routes found in the production build" >&2
  exit 1
fi
```

Sharded Playwright and Cypress CI workflows, auth setup projects and the data guard: [references/ci-and-flake-control.md](references/ci-and-flake-control.md), [references/cypress.md](references/cypress.md), [references/test-data-and-environments.md](references/test-data-and-environments.md).

## 15. Common Mistakes

- **E2E for everything**: slow, flaky and expensive. Keep E2E for critical journeys and test rules lower down.
- **UI login in every test**: seconds per test. Log in through the API and reuse the session.
- **UI-driven data setup**: slow and brittle. Create data by API or fixtures.
- **A seed or reset endpoint guarded only by an environment flag**: one misconfiguration exposes data destruction in production. Exclude it from the production build.
- **`cy.wait(5000)` or `waitForTimeout`**: flaky and slow. Wait on assertions, aliases or responses.
- **CSS and positional selectors**: break on every redesign. Use roles, accessible names and test ids.
- **Shared accounts and global truncation with parallel workers**: collisions. Unique data per test or per worker.
- **Retrying as the flake strategy**: hides races. Fix the cause; track retried tests.
- **Using real third-party services**: rate limits, costs and outages. Stub or use sandboxes.
- **`Cypress.env()` for secrets (pre-16 code)**: removed in 16, and exposes values to the browser. Use `cy.env()`; keep `Cypress.expose()` for public values.
- **`cy.exec()` for seeding (pre-16 code)**: removed in 16. Use `cy.task()`.
- **Starting the server from a test task**: processes leak and ports collide. Start it before the runner.
- **Committing storage state, `cypress.env.json` or uploading them as artifacts**: leaks live sessions and credentials.
- **Visual regression on unstable pages**: noise trains people to ignore failures. Stabilize time, data and fonts first.
- **`${{ github.event.* }}` inside `run:`**: script injection risk. Use `env:`.

## 16. References

- [references/cypress.md](references/cypress.md): Cypress 15 and 16 changes, configuration, retry-ability, selectors, `cy.session`, `cy.intercept`, `cy.task` seeding, `cy.env` versus `Cypress.expose`, component testing, CI with the GitHub Action and sharding, visual regression, migration checklist.
- [references/test-data-and-environments.md](references/test-data-and-environments.md): data strategies, keeping seed and reset out of production (guard, separate entrypoints, build checks), auth state reuse, environments, parallel safety.
- [references/ci-and-flake-control.md](references/ci-and-flake-control.md): pipeline placement, Playwright sharding with merged reports, Cypress parallelization, CI hygiene, flake taxonomy, retry and quarantine policy.
- Official docs: https://docs.cypress.io/ , https://docs.cypress.io/app/references/changelog , https://playwright.dev/docs/intro , https://playwright.dev/docs/test-sharding , https://github.com/cypress-io/github-action , https://github.com/bahmutov/cypress-split
