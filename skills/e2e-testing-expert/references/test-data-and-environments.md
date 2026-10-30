# Test Data and Environments for End-to-End Tests

Reference for creating deterministic data, reusing authentication, and running journeys in local, CI and shared environments without ever shipping test-only control surfaces to production. Verified against Cypress 16.2.x, Playwright 1.64.x, esbuild 0.x bundling behavior, `node-postgres` 8.x and GitHub Actions `checkout` v7 (2026-10). The Node-side guard and the build-time exclusion example were executed; browser tests were type-checked only.

## 1. Data strategies

| Strategy | How | Speed | Use for |
|---|---|---|---|
| Public API setup | Test calls the same HTTP API a client would (register user, create project) through `cy.request` or Playwright `request` | Fast, realistic | Most per-test data; exercises validation and auth |
| Direct database fixtures from test tooling | A Node task (`cy.task`, Playwright fixture or global setup) connects to the test database and inserts rows | Fastest | States the API cannot produce (old timestamps, deleted flags), reference data, bulk data |
| Snapshot restore | Restore a prepared database or template before the run | Fast for large datasets | Large reference datasets; one restore per machine |
| UI setup | Click through screens to create state | Slow, brittle | Only the journey under test |

Rules:
- The journey under test goes through the UI; everything before it is set up by API or fixtures.
- Each test owns its data: unique emails, names and ids (`randomUUID()`), so tests do not collide when running in parallel or being retried.
- Prefer idempotent setup (upsert, `ON CONFLICT`, get-or-create) so a rerun after a crash does not fail on leftovers.
- Reset or create state before a test, not in `afterEach`/`after` hooks; hooks may not run when a run is interrupted.
- Seed minimal data. A catalog of three products tests a checkout as well as thirty thousand.
- Dates and time zones: seed relative to a fixed clock when possible; stub the browser clock (`cy.clock`, `page.clock`) for countdowns and expiries.
- Keep data creation helpers typed and shared (custom commands, Playwright fixtures), not copy-pasted across specs.
- Never copy production data into end-to-end environments. Generate synthetic data. Masked extracts need the same protection as production.

## 2. No seed or reset endpoint in production

Test-only control surfaces such as `/__test__/reset`, `/api/seed`, "log in as any user" or "set feature flag" are remote data-destruction and account-takeover endpoints if they reach production. A runtime flag (`if (process.env.NODE_ENV !== 'production')`) is not enough: configuration mistakes, copied environment files and misrouted deployments can ship such endpoints. Control it by what is built and deployed.

Order of preference:

1. **No endpoint at all.** Seed from test tooling that connects to the test database directly. The application ships nothing. This is the default recommendation (see the guard below and the `cy.task` seeding in [cypress.md](cypress.md)).
2. **A separate e2e entrypoint** that adds test routes, compiled and packaged only for the e2e environment. The production entrypoint never imports the test module, so the production bundle does not contain it.
3. **Never** a single binary that contains test routes behind a flag.

Node-side guard used by seeding tools (refuses anything that is not a local `*_e2e` database):

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

```

Separate entrypoints with build-time exclusion. The test routes module:

```ts
import { Router } from "express";

// Imported ONLY by server.e2e.ts. Never import this module from production code.
export function testRoutes(reset: () => Promise<void>): Router {
  const router = Router();
  router.post("/__test__/reset", async (_req, res) => {
    await reset();
    res.status(204).end();
  });
  return router;
}
```

The e2e entrypoint, which also refuses to start unless explicitly in the e2e environment:

```ts
import { createApp } from "./app.ts";
import { testRoutes } from "./testing/routes.ts";

if (process.env.APP_ENV !== "e2e") throw new Error("server.e2e.ts must only run with APP_ENV=e2e");

const app = createApp();
app.use(testRoutes(async () => { /* truncate test tables */ }));
app.listen(Number(process.env.PORT ?? 3000));
```

The production entrypoint imports only the application factory:

```ts
import { createApp } from "./app.ts";

createApp().listen(Number(process.env.PORT ?? 3000));
```

Build both targets separately and verify the production artifact does not contain the test surface (this was run with esbuild: the marker string appears in the e2e bundle only):

```bash
npx esbuild src/server.ts --bundle --platform=node --format=esm --packages=external --outfile=dist/server.js
npx esbuild src/server.e2e.ts --bundle --platform=node --format=esm --packages=external --outfile=dist-e2e/server.js

# CI gate on the artifact that will be deployed
if grep -rq "__test__" dist/; then
  echo "test routes found in the production build" >&2
  exit 1
fi
```

Packaging rules:
- The production image or archive is built from `dist/` only; the e2e image is a different target with a different tag and repository, and is never promoted.
- Frameworks that discover routes from the file system (Next.js, Nuxt and similar) include every route file in the build. Keep test routes outside the source tree and copy them in only in an e2e build step, then assert their absence from the production build output.
- Add a post-deploy production smoke check that requests the test paths and expects 404.
- Review process: a lint rule or CODEOWNERS entry on the test-only directory, and a rule that production code must not import from it.
- The same applies to test-only feature flags, "magic" OTP codes, bypass headers and permissive CORS: they must be impossible to enable in a production build, not merely switched off.

## 3. Authentication state reuse

- Log in once per user or role through the API, store the session, and start each test already authenticated.
- Cypress: `cy.session(id, setup, { validate, cacheAcrossSpecs })`; the page is blank after restore, so visit afterwards. See [cypress.md](cypress.md).
- Playwright: a `setup` project logs in and writes `storageState`; test projects depend on it:

```ts
// playwright.config.ts (excerpt)
projects: [
  { name: "setup", testMatch: /auth\.setup\.ts/ },
  {
    name: "chromium",
    use: { ...devices["Desktop Chrome"], storageState: "playwright/.auth/shopper.json" },
    dependencies: ["setup"],
  },
],
```

```ts
// tests/auth.setup.ts
import { test as setup, expect } from "@playwright/test";

setup("authenticate shopper", async ({ request }) => {
  const res = await request.post("/api/auth/login", {
    data: { email: "shopper@example.test", password: process.env.E2E_PASSWORD },
  });
  expect(res.ok()).toBeTruthy();
  await request.storageState({ path: "playwright/.auth/shopper.json" });
});
```

- The storage state file holds live session cookies: add `playwright/.auth/` to `.gitignore`, never upload it as a CI artifact, and delete it after the run on shared runners.
- One account per role (viewer, editor, admin) for permission journeys; one account per parallel worker when tests mutate user state.
- Test accounts use the test environment's own identity data, least privilege, and a marker (domain `example.test`, a `is_test` flag) so email, analytics and billing systems skip them.
- Passwords and tokens come from CI secrets (`CYPRESS_E2E_PASSWORD`, `E2E_PASSWORD`), never from the repository.
- MFA and SSO: prefer a test tenant configured for password login, or a test identity provider container; if TOTP is required, generate codes from a secret held in the CI secret store. Do not add an authentication bypass to the application.
- For the login flow itself keep a few UI tests; they also catch regressions in the login page.

## 4. Environments

| Environment | Purpose | Data | Notes |
|---|---|---|---|
| Local | Authoring and debugging | Local database seeded by tooling | Same commands as CI; one command to start app, database and dependencies |
| Ephemeral CI | Gate for every pull request | Fresh database per job (service container or Testcontainers), seeded by tooling | Deterministic; parallel machines each get their own stack |
| Shared staging | Pre-release checks, integration with real third-party sandboxes | Synthetic tenant(s) created for tests | Read-mostly; tests must tolerate other users' data; schedule heavy suites off-hours |
| Production | Synthetic monitoring only | Dedicated synthetic account | Read-only journeys or safe actions with cleanup; never seed, reset or truncate |

- Base URL and credentials come from environment variables (`BASE_URL`, `CYPRESS_*`), not constants in specs.
- Third-party systems use sandboxes or stubs: payment test mode, email capture (a local SMTP sink such as Mailpit with its HTTP API for asserting messages), stubbed maps or analytics via network interception.
- Feature flags in tests come from the test environment's flag configuration, not from a bypass in the app.
- Keep test and production credentials in separate secret stores with different access.
- Pin application and dependency versions in the e2e environment to the build under test (image digest or commit SHA) so failures are attributable.
- Health gate: wait for a health endpoint (`/healthz`) and for migrations before starting tests; fail fast with a clear message if the environment is not ready.
- Ephemeral preview environments per pull request give realistic checks; destroy them on close and cap their lifetime.

## 5. Parallel safety

- Parallel workers or machines share nothing mutable: separate databases per machine, or unique tenants/users per worker with no global truncation.
- Avoid asserting on global counts ("exactly 3 products") unless the test owns the entire dataset; assert on the records the test created.
- Rate limits and CAPTCHAs in the test environment are disabled or raised through configuration of the environment, not through bypass headers in production code.
- Idempotent cleanup jobs (nightly) remove leftover test tenants older than a retention period in shared environments.

## 6. Safeguards for destructive helpers

- Every helper that truncates, deletes or restores data checks the target first (host allowlist, database name suffix, environment variable) and throws otherwise, as in the guard above.
- Credentials for seeding tools have access to test databases only.
- Logs of seeding tasks print what ran and where, never connection strings with passwords.
- Run the destructive-helper guard in a unit test: given a production-looking URL it must refuse.
