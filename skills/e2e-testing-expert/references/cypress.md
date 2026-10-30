# Cypress

Reference for writing and running Cypress end-to-end and component tests; absorbed from the former cypress-expert skill. Verified against Cypress 16.2.x (npm `cypress` 16.2.1; the changelog lists 16.2.2 as the newest entry), Node.js `^22.0.0 || ^24.0.0 || >=26.0.0`, `cypress-io/github-action` v7 (7.4.x), `cypress-split` 1.25.x, `@percy/cypress` 3.1.x and the Cypress documentation and changelog (2026-10). The TypeScript examples below were type-checked against the Cypress 16.2.1 type definitions; they were not executed against a running application.

## 1. What changed in Cypress 15 and 16

| Version | Change that affects test code or CI |
|---|---|
| 15.0.0 | Node 18 and 23 dropped; `Cypress.SelectorPlayground` renamed `Cypress.ElementSelector`; `cy.url()`, `cy.hash()`, `cy.go()`, `cy.reload()`, `cy.title()`, `cy.location()` read through the browser automation client; the 3-argument `cy.stub` signature removed; Cypress config is loaded with `tsx`; direct binary download install dropped (use a package manager) |
| 15.x | `cy.env()` and `Cypress.expose()` introduced; `cy.press()` added for native key events such as Tab; `cy.prompt` (AI-assisted steps) entered beta |
| 16.0.0 | Node 20 and 25 dropped (requires `^22 || ^24 || >=26`); bundled Node 24; `Cypress.env()` removed (use `cy.env()` for secrets, `Cypress.expose()` for public values); `env` in per-test config overrides replaced by `expose`; `cy.exec()` and `execTimeout` removed (use `cy.task()`); `cy.end()` removed; `keystrokeDelay` default 10 to 0; modern visibility algorithm is the default (`visibilityStrategy: 'legacy'` only as a temporary escape); `cy.getCookie()`, `cy.getCookies()`, `cy.getAllCookies()`, `cy.getAllLocalStorage()`, `cy.getAllSessionStorage()` became retrying queries; `viewportWidth`, `viewportHeight`, `blockHosts` cannot be changed through `Cypress.config()` during a test; CoffeeScript support removed; Electron deprecated as a test browser |
| 16.0.0 networking | Chrome, Chromium and Edge use native browser networking, so HTTP/2 and HTTP/3 work as in production; `req.httpVersion` is not reported in `cy.intercept()` there and compression headers are absent from intercepted responses; Firefox, WebKit and Electron keep the legacy path; `forceHttp1` exists but is deprecated |
| 16.0.0 component testing | Vite dev server requires Vite 8 or later; Next.js 15.0.4 or later (14 dropped); Angular 21 or later (22 supported); `cypress/angular-zoneless` merged into `cypress/angular` |
| 16.2.0 | `cy.getByRole(role, { name })` query added (matches native elements by default; `native: false` also matches `role` attributes; `hidden: true` includes elements hidden from the accessibility tree) |
| 16.2.1 | `cy.fixture()` and `cy.intercept()` fixture paths that resolve outside `fixturesFolder` fail; `cy.contains()` works inside `cy.document().within()`; Node-side code (`cy.task()` handlers, `setupNodeEvents`) verifies TLS certificates the way Node does |

Check the changelog (https://docs.cypress.io/app/references/changelog) before upgrading across majors.

## 2. Configuration

```ts
import { defineConfig } from "cypress";
import cypressSplit from "cypress-split";
import { dbTasks } from "./cypress/support/db-tasks";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    specPattern: "cypress/e2e/**/*.cy.ts",
    retries: { runMode: 2, openMode: 0 }, // retries show up as flaky in reports; fix the cause
    screenshotOnRunFailure: true,
    expose: { apiPath: "/api" }, // public values only; secrets are read with cy.env()
    setupNodeEvents(on, config) {
      on("task", dbTasks); // Node-side seeding against the test database only
      cypressSplit(on, config); // SPLIT and SPLIT_INDEX select this machine's share of specs
      return config; // returning the config is required, or every spec runs
    },
  },
  component: {
    devServer: { framework: "react", bundler: "vite" },
    specPattern: "src/**/*.cy.tsx",
  },
});
```

Notes:
- Default test isolation is on (`testIsolation: true`): before each test Cypress clears cookies, local storage and session storage for all origins and visits `about:blank`. Keep it on; use `cy.session()` to carry authentication across tests.
- `retries` can be a number or `{ runMode, openMode }`. Retried tests are reported as flaky in Cypress Cloud and reporters; track them. Experimental flake-detection retry strategies exist; read the current docs before relying on them.
- `expose` values are readable in the browser (`Cypress.expose('apiPath')`) and can be overridden per suite or test with `{ expose: { key: value } }`. Never put secrets there.
- `setupNodeEvents` runs on the Node.js version that runs the Cypress CLI, with `process.env` of that process. Return the config object.
- Do not start the application server from `cy.task()`; start it before Cypress (the GitHub Action's `start` option or a `start-server-and-test` style script).
- Commit `cypress.config.ts` and `cypress/`; gitignore `cypress.env.json`, `cypress/screenshots/`, `cypress/videos/`, `cypress/downloads/`.

## 3. Commands queries and retry ability

- Queries (`cy.get`, `cy.find`, `cy.contains`, `cy.getByRole`, `.eq`, `.first`, `.filter`, and in 16 the cookie and storage getters) re-run until their assertions pass or the timeout (`defaultCommandTimeout`, 4000 ms) expires. Actions (`.click()`, `.type()`) run once, after actionability checks (visible, not covered, not disabled, not animating).
- Chain assertions to queries: `cy.get('[data-testid=count]').should('have.text', '3')` retries the query and the assertion together. Do not store elements in variables and reuse them later; re-query instead.
- Never use `cy.wait(1000)` to wait for the app. Wait for something observable: an assertion, a route alias (`cy.wait('@orders')`), a URL change (`cy.location('pathname').should('eq', '/done')`). `cy.wait('@alias')` on an intercepted request is not an arbitrary wait.
- Calling a query that needs a subject directly off `cy` (for example `cy.first()`) fails immediately in 16.2.
- `.then()` callbacks are not retried; do not put assertions that need retrying in them. Prefer `.should(callback)` for custom retrying checks.
- Use `cy.clock()` and `cy.tick()` for timer-driven UI instead of real delays.
- Avoid `cy.get(...).then(($el) => { if ($el.length) ... })` conditional testing; make the app state deterministic instead.

## 4. Selectors

Preferred order: `cy.getByRole(role, { name })` for user-facing, accessible elements (Cypress 16.2+); `data-*` attributes (`data-cy`, `data-test`, `data-testid`) where roles are ambiguous; `cy.contains(selector, text)` for text that is part of the requirement. Avoid tag, class and id selectors, positional selectors (`:nth-child`) and long CSS chains. Enforce with `eslint-plugin-cypress` (`cypress/require-data-selectors`). Page objects are discouraged by the Cypress docs; use small custom commands and data setup helpers instead.

## 5. Authentication with cy session

`cy.session(id, setup, options)` caches cookies, `localStorage` and `sessionStorage` after `setup` runs and restores them in later tests with the same id. It yields `'created'`, `'restored'` or `'recreated'`. `validate` runs after creating or restoring; if it throws or a command in it fails, the session is recreated. `cacheAcrossSpecs: true` shares it across spec files in one run.

```ts
declare global {
  namespace Cypress {
    interface Chainable {
      loginAs(email: string): Chainable<void>;
    }
  }
}

// Logs in through the API once per user, then restores cookies and storage from the cached session.
Cypress.Commands.add("loginAs", (email: string) => {
  cy.session(
    ["user", email],
    () => {
      cy.env(["E2E_PASSWORD"]).then(({ E2E_PASSWORD }) => {
        cy.request({ method: "POST", url: "/api/auth/login", body: { email, password: E2E_PASSWORD } });
      });
    },
    {
      validate() {
        cy.request("/api/me").its("status").should("eq", 200); // recreate the session if it expired
      },
      cacheAcrossSpecs: true,
    },
  );
});

export {};
```

Rules:
- Log in through the API (`cy.request`) inside `setup`; exercise the real login UI in a few dedicated tests.
- Call `cy.visit()` after `cy.session()`, not before; the page is blank after restore.
- Choose the id so it changes whenever the session would differ (user, role, tenant).
- Read credentials with `cy.env([...])` from `CYPRESS_*` environment variables or the CI secret store. `Cypress.env()` no longer exists in Cypress 16.
- Do not commit `cypress.env.json`.

## 6. Network control with cy intercept

```ts
// Stub a third-party call with a static response
cy.intercept('POST', '/api/payments', { statusCode: 201, body: { status: 'paid' } }).as('pay');

// Spy without changing the response, then assert on the request
cy.intercept('GET', '/api/orders*').as('orders');
cy.visit('/orders');
cy.wait('@orders').its('response.statusCode').should('eq', 200);

// Modify a real response (fault injection)
cy.intercept('GET', '/api/products', (req) => {
  req.continue((res) => { res.setDelay(2000); });
});

// Simulate a network failure
cy.intercept('GET', '/api/profile', { forceNetworkError: true });
```

- Register intercepts before the action that triggers the request. Alias with `.as()` and wait on the alias.
- Stub third-party services (payments, maps, analytics) and flaky edges; keep the first-party API real in end-to-end tests so they still verify integration.
- Match precisely (method, URL, query) so unrelated requests are not swallowed. Header matchers that name the same header twice with different casing are an error in the newest 16.2.x changelog entry; list each header once.
- In Chrome, Chromium and Edge with Cypress 16, intercepts work on the native browser network; `req.httpVersion` is unavailable and compression headers are not present on intercepted responses.
- `cy.get('@alias.0')` for the first call fails at once in 16.2; use `cy.get('@alias.all')` or `cy.wait` with assertions.
- Fixture files referenced by `cy.fixture()` or `{ fixture: 'x.json' }` must live inside `fixturesFolder`.

## 7. Test data with cy task and cy request

Seeding that needs the database runs in Node through `cy.task()`, registered in `setupNodeEvents`. This code exists only in the test tooling; the application ships no seed or reset endpoint.

```ts
import { Client } from "pg";

// Runs in the Cypress config process (Node), never in the browser and never in the application.
async function withTestDb<T>(fn: (db: Client) => Promise<T>): Promise<T> {
  const raw = process.env.E2E_DATABASE_URL;
  if (!raw) throw new Error("E2E_DATABASE_URL is not set");
  const url = new URL(raw);
  const localHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
  // Guard: only a local database whose name ends in _e2e may be modified.
  if (!localHosts.has(url.hostname) || !url.pathname.endsWith("_e2e")) {
    throw new Error(`refusing to modify ${url.hostname}${url.pathname}: not a local *_e2e database`);
  }
  const db = new Client({ connectionString: raw });
  await db.connect();
  try {
    return await fn(db);
  } finally {
    await db.end();
  }
}

interface ProductFixture {
  sku: string;
  name: string;
  priceCents: number;
}

export const dbTasks = {
  // Idempotent: safe to run at the start of every spec.
  "db:upsertProducts": (products: ProductFixture[]) =>
    withTestDb(async (db) => {
      for (const p of products) {
        await db.query(
          `INSERT INTO products (sku, name, price_cents) VALUES ($1, $2, $3)
           ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name, price_cents = EXCLUDED.price_cents`,
          [p.sku, p.name, p.priceCents],
        );
      }
      return null; // cy.task requires a non-undefined return value
    }),

  "db:reset": () =>
    withTestDb(async (db) => {
      await db.query("TRUNCATE orders, order_items, products RESTART IDENTITY CASCADE");
      return null;
    }),
};
```

Using the tasks and the API in a spec (`before` seeds idempotently; each test relies on its own user and cached session):

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
    // Stub only the third-party payment call; everything else hits the real app and database.
    cy.intercept("POST", "/api/payments", { statusCode: 201, body: { status: "paid" } }).as("pay");

    cy.visit("/products/TEE-1");
    cy.getByRole("button", { name: "Add to cart" }).click();
    cy.get("[data-testid=cart-link]").click();
    cy.getByRole("button", { name: "Pay now" }).click();

    cy.wait("@pay").its("request.body").should("deep.include", { sku: "TEE-1" });
    cy.getByRole("heading", { name: "Thank you for your order" }).should("be.visible");
  });

  it("shows an error and keeps the cart when the payment is declined", () => {
    cy.intercept("POST", "/api/payments", { statusCode: 402, body: { error: "declined" } }).as("pay");

    cy.visit("/cart");
    cy.getByRole("button", { name: "Pay now" }).click();

    cy.wait("@pay");
    cy.getByRole("alert").should("contain.text", "declined");
    cy.get("[data-testid=cart-count]").should("have.text", "1");
  });
});
```

Rules:
- A task handler must return a value or a promise that does not resolve to `undefined`, or the command fails; return `null`. Arguments and results are serialized like JSON.
- `cy.exec()` is gone in 16; move shell work into a task (`child_process` inside Node if truly needed) and keep the commands fixed, never built from test input.
- Seed or reset before each test (or spec), not in `after` hooks, which may not run when a run is interrupted. Prefer data that is unique per test over wholesale truncation when specs run in parallel on one database.
- A database used by parallel Cypress machines must be per machine, or tests must create unique data and avoid `TRUNCATE`.
- Environment details and the rule that production must not expose any seed endpoint: [test-data-and-environments.md](test-data-and-environments.md).

## 8. Secrets and configuration cy env and Cypress expose

| API | Where values live | Use for |
|---|---|---|
| `cy.env(['KEY'])` | Read from the Node process on request; only named keys are returned; only key names appear in the command log; works inside `cy.origin()` | Passwords, API keys, tokens |
| `Cypress.expose('key')` | Synchronously readable in the browser, visible to the application and extensions | Feature flags, API versions, environment labels |

Set values with `CYPRESS_<NAME>` environment variables (CI secrets), the `--env` CLI flag, `cypress.env.json` (gitignored) or `setupNodeEvents`. Request only the keys a test needs. `Cypress.env()` and the `allowCypressEnv` option were removed in 16.0.0; migrate calls to `cy.env()` (asynchronous, so values are used inside `.then()`) or `Cypress.expose()`.

## 9. Component testing

```ts
import { mount } from "cypress/react";

function Counter() {
  return <button>Count</button>;
}

describe("Counter", () => {
  it("renders", () => {
    mount(<Counter />);
    cy.getByRole("button", { name: "Count" }).should("be.visible");
  });
});
```

- `devServer: { framework: 'react', bundler: 'vite' }`; other combinations include `next`, `vue`, `svelte`, `angular` with webpack. Cypress 16 requires Vite 8+, Next.js 15.0.4+, Angular 21+.
- Component tests run in a real browser with the component mounted in isolation (`cy.mount`, imported from `cypress/react`, `cypress/vue`, `cypress/svelte` or `cypress/angular`). Use them for interaction-heavy components, focus management and visual states where jsdom is inadequate.
- Put global providers (router, store, theme) in `cypress/support/component.ts` as a custom `mount` wrapper.
- `cy.session()` and `cy.visit()` are E2E commands; component specs stub network with `cy.intercept()`.
- Keep end-to-end tests for journeys and component tests for widget behavior.

## 10. Retries flake and diagnostics

- Fix first: tests that wait on conditions, use unique data and avoid shared state rarely flake. Retries (`retries: { runMode: 2, openMode: 0 }`) are a safety net that must show up on a flake dashboard.
- Typical causes: arbitrary waits, assertions on elements being replaced (detached DOM), races between navigation and the next command, shared database rows, animations (Cypress waits for animations by default; keep `waitForAnimations` on), third-party scripts, test order dependence.
- Failures produce screenshots (`screenshotOnRunFailure`); record videos or use Cypress Cloud Test Replay when you need timelines. Upload screenshots as CI artifacts.
- Reproduce a flake with a loop (`for i in $(seq 1 30); do npx cypress run --spec path; done`) in CI-like conditions (same browser, headless, constrained CPU).
- Test code runs in the browser; `console.log` is available in DevTools; `cy.log` writes to the command log; `cy.task('log', ...)` writes to the terminal.

## 11. CI with GitHub Actions

`cypress-io/github-action@v7` installs dependencies with caching, builds and starts the app, waits for it, and runs Cypress. Pass secrets through `env:`; never interpolate event data or inputs into `run:` commands.

```yaml
name: e2e
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  cypress:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        containers: [1, 2, 3]            # three parallel machines
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: ci-only-password
          POSTGRES_DB: shop_e2e
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v7
      - uses: cypress-io/github-action@v7
        with:
          build: npm run build:e2e
          start: npm run start:e2e
          wait-on: "http://localhost:3000/healthz"
          browser: chrome
        env:
          E2E_DATABASE_URL: postgres://postgres:ci-only-password@localhost:5432/shop_e2e
          CYPRESS_E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
          SPLIT: ${{ strategy.job-total }}          # read by cypress-split
          SPLIT_INDEX: ${{ strategy.job-index }}
      - uses: actions/upload-artifact@v7
        if: failure()
        with:
          name: cypress-screenshots-${{ strategy.job-index }}
          path: cypress/screenshots
          if-no-files-found: ignore
```

- Sharding options: `cypress-split` (free; plugin splits spec files by `SPLIT` and `SPLIT_INDEX`) or Cypress Cloud parallelization (`record: true`, `parallel: true`, `group`, with `CYPRESS_RECORD_KEY` as a secret) that balances by historical spec duration.
- Each parallel machine needs its own database (service containers are per job, so each matrix job gets one) and its own server.
- Run a small smoke subset on every push and the full suite on pull requests and nightly; tag specs or use folder conventions to select them.
- Use the same browser in CI as the one you debug with. Electron is deprecated as a test browser in 16; prefer Chrome or Firefox.

## 12. Visual regression

Cypress has no built-in screenshot diffing. Options: a service plugin such as Percy (`@percy/cypress`, `cy.percySnapshot('name')`, requires a Percy token as a CI secret), or an image-diff plugin. Whatever the tool, stabilize first: fixed viewport, fixed fonts, frozen time (`cy.clock`), stubbed network, disabled animations and caret blinking, masked dynamic regions (dates, ads, avatars). Review baselines in pull requests like code. For Playwright, `toHaveScreenshot()` is built in (see playwright-expert).

## 13. Migration checklist to Cypress 16

1. Upgrade Node to 22, 24 or 26+; update CI images.
2. Replace `Cypress.env('X')` with `cy.env(['X'])` or `Cypress.expose('X')`; change `env:` per-test overrides to `expose:`.
3. Replace `cy.exec(...)` with `cy.task(...)`; remove `.end()`; delete `execTimeout`, `allowCypressEnv`, `experimentalSourceRewriting`; rename `experimentalMemoryManagement` to `manageBrowserMemory`.
4. Re-check tests that depended on `keystrokeDelay: 10`, on cookies being read once rather than retried, or on the legacy visibility rules.
5. Review `cy.intercept()` tests in Chrome-family browsers for `req.httpVersion` and compression headers.
6. Component testing: upgrade Vite, Next.js or Angular to the new minimums.
7. Move away from Electron as the test browser.
