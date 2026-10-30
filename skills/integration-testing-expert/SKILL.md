---
name: integration-testing-expert
description: >-
  Designs integration tests that run a service against real dependencies: Testcontainers (Node, Java, Python, Go), per-test database isolation (rollback, truncate, template databases), seeding and idempotent test data, HTTP API tests with supertest, consumer-driven contract tests with Pact, stubbing external HTTP with MSW or WireMock, message-broker tests, parallelism, flaky-test control and CI service containers. Use when testing repositories, migrations, API endpoints, queue consumers or service-to-service contracts, or when integration tests are slow, flaky or order-dependent. Not for isolated unit tests with mocks (use unit-testing-expert) or browser end-to-end tests (use e2e-testing-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Integration Testing Expert

This skill covers tests that exercise a service together with the dependencies it owns: database, cache, broker, HTTP boundaries and other services' contracts. It rewrites the former integration-testing-expert skill from scratch, with working examples for Node and notes for Java, Python and Go. Unit tests and browser journeys are separate skills.

> Verified against Testcontainers for Node 12.2.x (Node 22.22 or later), Testcontainers for Java 2.0.x, testcontainers-python 4.15.x, Vitest 5.0.x, supertest 7.3.x, MSW 3.0.x, `@pact-foundation/pact` 17.1.x, WireMock 3.13.x, PostgreSQL 18 and GitHub Actions `checkout`/`setup-node` v7 (2026-10).

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

- Covered: the scope and boundaries of integration tests, real dependencies via Testcontainers or CI service containers, database setup and isolation, migrations and seeding, HTTP API tests, contract tests with Pact, stubbing third-party HTTP, message broker tests, parallel execution, flaky-test control.
- Not covered: isolated unit tests and test doubles for internal collaborators (unit-testing-expert), browser journeys and UI automation (e2e-testing-expert, playwright-expert), load testing (performance-optimization-expert), designing the service boundaries themselves (microservices-expert), Dockerfile and Compose authoring (docker-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Scope | One service plus the dependencies it owns, running for real; other teams' services and vendors replaced by stubs or contract tests |
| Testcontainers | Starts throwaway Docker containers from test code; modules for Postgres, Redis, Kafka, RabbitMQ, MongoDB, LocalStack and more; dynamic ports; Ryuk reaper cleans up |
| Node packages | `testcontainers` and `@testcontainers/<module>` 12.2.x; Java `testcontainers-<module>` 2.0.x; Python `testcontainers.community.<module>` 4.15.x |
| DB isolation | Transaction rollback, truncate, unique-data-per-test, template database clone (`CREATE DATABASE ... TEMPLATE`), Postgres container snapshots |
| HTTP API tests | supertest drives an Express/Koa/Fastify app in process; real database; stubbed outbound HTTP |
| Contract testing | Pact consumer tests produce a pact file; provider verification replays it with state handlers; Pact Broker `can-i-deploy` gates releases |
| HTTP stubs | MSW 3 in-process (`onUnhandledFrame` controls unhandled calls), WireMock 3 as a standalone server, nock for small Node stubs |
| Flake control | Unique data, polling with timeouts instead of sleeps, fixed clocks, no shared mutable state, isolated databases |
| CI | `services:` containers with health checks, or Testcontainers on runners that have Docker; separate job from unit tests |

## 3. Workflow

1. List the boundaries of the service: what it owns (database, cache, queue) and what it calls (internal services, vendors).
2. For each owned dependency pick a real instance (Testcontainers locally, service container or Testcontainers in CI). For each external dependency pick a stub or a contract.
3. Build the test harness once: global container start, migrations into a template database, helpers that create an isolated database or tenant per file.
4. Expose the app as a factory (`createApp({ pool, paymentsUrl })`) so tests inject real connections and stub URLs without environment tricks.
5. Write tests per behavior at the seam: request in, persisted state and outbound calls out. Include failure paths (constraint violations, upstream 5xx, timeouts, duplicates).
6. Add contract tests for service-to-service APIs and publish pacts from CI.
7. Run in parallel by file with isolated state; measure; fix any test that fails when run alone, in a different order, or twice.
8. Put the suite in CI as its own job with timeouts, artifacts and a flake report.

## 4. Decision Rules

- Real over mock for what you own. A mocked repository cannot catch a wrong column, a missing index, a unique constraint or a migration error; a real PostgreSQL can.
- Stub what you do not own. Vendors and slow or paid APIs are replaced at the HTTP boundary (MSW or WireMock), not inside your client code.
- The same database engine and major version as production. SQLite or an in-memory fake hides dialect, locking and JSON/array behavior.
- Isolation choice: transaction rollback for repository-level tests where code shares one connection; truncate for a database owned by one worker; template clone per file when files run in parallel; container snapshot restore for sequential suites. Details in [references/testcontainers.md](references/testcontainers.md).
- Contract test versus stub: if you control or can talk to the provider team, use Pact so changes fail the provider build; if not, use a stub and optionally record real responses periodically.
- WireMock over MSW when the service under test is not Node, when several services share the stubs, or when the stub must be a separate process; MSW otherwise.
- Testcontainers over a shared dev database always; shared databases make tests depend on other people's data. Use CI service containers when the CI platform already provides them cheaply and a health check is configured.
- Keep tests in the pyramid's middle: dozens to a few hundred integration tests, each seconds or less; business-rule permutations belong in unit tests.
- A retry is not a fix. Retries can be a temporary quarantine while the root cause is tracked, never a default.

## 5. Coding Standards

- Name tests by behavior: `returns 409 when the email already exists`. One behavior per test; Arrange, Act, Assert visible.
- Application code exposes a factory or accepts injected dependencies (database pool, clock, base URLs); do not read configuration at import time.
- Each file creates its own database, tenant or key space; each test creates the rows it needs with factories and unique values.
- No `sleep`. Wait on conditions (`vi.waitFor`, `expect.poll`, wait strategies on containers) with an explicit timeout.
- Assert on observable outcomes: response status and body, rows in the database, messages published, requests received by the stub. Do not assert on internal calls.
- Set explicit timeouts for container start (`hookTimeout`) and tests (`testTimeout`); keep them generous for startup and tight for tests.
- Type test helpers; share them from `test/helpers/`, not by importing other test files.
- Tests must not depend on file or test order; run with random ordering (`sequence.shuffle`) periodically to catch it.

## 6. Project Structure

```
.
├── src/
│   ├── app.ts                    # createApp({ pool, paymentsUrl }) factory
│   └── orders-client.ts          # client of another service (contract consumer)
├── migrations/                   # SQL applied to the template database
├── test/
│   ├── global-setup.ts           # start Postgres (or use TEST_DATABASE_URL), build template DB
│   ├── helpers/
│   │   ├── test-db.ts            # clone template database per file, drop afterwards
│   │   └── factories.ts          # data builders with unique values
│   ├── orders.api.test.ts        # supertest + MSW
│   ├── orders-client.pact.test.ts    # consumer contract
│   └── orders-api.provider.test.ts   # provider verification
├── pacts/                        # generated pact files (gitignored)
└── vitest.config.ts              # globalSetup, timeouts, include patterns
```

## 7. Design Patterns

- **Global container, template database, per-file clone**: one container start per run, migrations once, a copy per test file. Code in [references/testcontainers.md](references/testcontainers.md).
- **App factory with injected dependencies**: tests pass real pool plus stub URLs; production passes configuration.
- **Test data factories**: `makeOrder({ totalCents: 500 })` fills defaults with unique ids; tests override only what matters.
- **Boundary stubs with strict unhandled-request policy**: MSW `onUnhandledFrame` rejects unexpected outbound calls; handlers capture requests for assertions.
- **Consumer-driven contract**: consumer tests write a pact; provider verifies it with state handlers that insert the needed rows; broker gates deployment ([references/contract-testing.md](references/contract-testing.md)).
- **Polling assertions for async work**: `await vi.waitFor(() => expect(...))` with a timeout for queue consumers and background jobs.
- **Idempotent consumers tested by duplicate delivery**: send the same message twice, assert one effect.
- **Tenant-per-test for shared databases**: when cloning is not possible, each test creates a tenant and works only inside it.

## 8. Best Practices

- Pin image versions (`postgres:18`) to match production; update deliberately.
- Run migrations the same way production does (the migration tool, not hand-written DDL) so migration bugs surface in tests.
- Test the migration path too: apply the previous release's schema plus data, then the new migration, in a dedicated test or job.
- Keep seed data to reference tables; tests create everything else.
- Make error paths first-class tests: unique violations, foreign key failures, upstream timeouts, partial failures, retries with idempotency keys.
- Capture container logs on failure (`container.logs()`), and keep request/response dumps of stubs when an assertion fails.
- Use the real HTTP stack (supertest over the actual Express/Fastify app) so middleware, auth, parsing and error handlers are covered.
- Keep secrets out of tests: throwaway credentials generated per run or fixed CI-only values for local containers; never real API keys.
- Document how to run the suite locally in one command (`npm run test:integration`) and how to debug a single file.

## 9. Performance

- Start containers once per run, not per test; clone databases from a template instead of re-running migrations (milliseconds against seconds).
- Parallelize by test file (Vitest and Jest workers); each worker needs its own database.
- Use small databases and indexes that match production, but avoid large seed data in the template.
- Prefer `TRUNCATE ... RESTART IDENTITY CASCADE` over row-by-row deletes; prefer transaction rollback where the code shares the connection.
- Pre-pull images in CI and use a registry mirror; cache dependencies.
- Shard across CI machines by file when the suite exceeds a few minutes; report timings to rebalance.
- Track suite duration and the slowest tests; set a budget (for example under five minutes) and treat regressions like bugs.
- Containers with `.withReuse()` speed local loops but must not be used in CI.

## 10. Security

- Test credentials are throwaway: random passwords per run or CI-only values scoped to a local container; never reuse production secrets, tokens or connection strings.
- Do not use production databases, queues or accounts for tests. Guard destructive helpers (`TRUNCATE`, `DROP DATABASE`) with a check that the connection string points to a local or test host.
- Do not copy production data into fixtures. Generate synthetic data; if masked extracts are unavoidable, keep them out of version control.
- Pass workflow inputs and event data to test scripts through `env:` in CI, never by interpolating `${{ inputs.* }}` or `${{ github.event.* }}` into `run:` lines.
- Pin third-party GitHub Actions to a version tag (or commit SHA) and grant the job the minimum `permissions:`.
- Exposed container ports bind to localhost by default; do not publish test databases on public interfaces on shared runners.
- Pact files and broker credentials: publish pacts only from CI, keep tokens in the secret store, and review pacts for personal data in examples.

## 11. Testing

- Test the tests: break the code deliberately (remove a constraint, flip a status code) and confirm a test fails.
- Run each new test alone, then in the full suite, then repeated 20 to 50 times in a loop and in random order before merging.
- Detect shared state: run files with `--sequence.shuffle` and with different worker counts.
- Check cleanup: after the suite, no containers remain (`docker ps`), no leftover databases.
- Verify the strict stub policy works: remove a handler and confirm the test fails on the unhandled request.
- Verify contract wiring: change a response field on the provider and confirm provider verification fails.
- Track flakiness: record failures per test in CI; quarantine with an issue and an owner, fix within a deadline.
- Coverage from integration tests is a by-product; do not gate on it.

## 12. Review Checklist

- [ ] The test exercises a real dependency owned by the service; only unowned systems are stubbed.
- [ ] Database engine and version match production; migrations are applied by the real tool.
- [ ] Each file/test has isolated state; no reliance on order or leftover rows.
- [ ] No `sleep`, no wall-clock assumptions; async waits use polling with a timeout.
- [ ] Unhandled outbound HTTP fails the test.
- [ ] Failure paths covered: constraint violation, upstream error and timeout, duplicate request.
- [ ] Container start has a generous timeout; image tags are pinned.
- [ ] CI job has a timeout, health-checked services or Testcontainers, logs on failure, and no secrets in `run:` interpolation.
- [ ] Contract tests exist for service-to-service calls; pacts are published and verified in CI.
- [ ] Suite runs under its time budget, in random order, and when repeated.

## 13. Production Notes

- Gate merges on the integration job; gate deployments on `can-i-deploy` when contracts are in use, and record deployments in the broker.
- Provider verification should run on every provider build and when consumers publish new pacts (broker webhooks), so breaking changes are found before release.
- Keep a quarantine list with owners and dates; fix or delete within a sprint. Do not let the suite accumulate skipped tests.
- Budget CI cost: containers per job, parallel shards, and Docker pull limits; use a mirror for base images.
- Periodically re-record or refresh third-party stubs from the vendor's sandbox, and diff against current stubs.
- Treat migration tests as release gates for databases with large tables: test the migration against realistic data volumes in a separate job.
- When a production incident escapes the suite, add the integration test that would have caught it before closing the incident.

## 14. Examples

API test with supertest, a cloned database per file and strict MSW stubs (excerpt; the full harness is in [references/testcontainers.md](references/testcontainers.md)):

```ts
import { randomUUID } from "node:crypto";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import request from "supertest";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { createApp } from "../src/app.ts";
import { createTestDb, type TestDb } from "./helpers/test-db.ts";

const PAYMENTS = "https://payments.example.test";
const payments = setupServer();
let db: TestDb;
let app: ReturnType<typeof createApp>;

beforeAll(async () => {
  db = await createTestDb();                       // clone of the migrated template database
  app = createApp({ pool: db.pool, paymentsUrl: PAYMENTS });
  payments.listen({
    onUnhandledFrame({ frame, defaults }) {        // fail on unexpected outbound calls, allow supertest's loopback
      const data = frame.data as { request?: Request };
      const host = data.request ? new URL(data.request.url).hostname : "";
      if (host === "127.0.0.1" || host === "localhost" || host === "::1") return;
      defaults.error();
    },
  });
});
afterEach(() => payments.resetHandlers());
afterAll(async () => { payments.close(); await db.drop(); });
beforeEach(async () => { await db.pool.query("TRUNCATE orders"); });

describe("POST /orders", () => {
  it("returns 402 and persists a failed order when the payment is declined", async () => {
    payments.use(http.post(`${PAYMENTS}/charges`, () => HttpResponse.json({ error: "declined" }, { status: 402 })));

    const res = await request(app).post("/orders").send({ customerId: randomUUID(), totalCents: 500 }).expect(402);

    const { rows } = await db.pool.query("SELECT status FROM orders WHERE id = $1", [res.body.id]);
    expect(rows[0].status).toBe("failed");
  });
});
```

Consumer contract with Pact JS 17 (the generated pact is verified by the provider's own test, see [references/contract-testing.md](references/contract-testing.md)):

```ts
import { MatchersV3, Pact } from "@pact-foundation/pact";

const { integer, regex, uuid } = MatchersV3;
const pact = new Pact({ consumer: "checkout-web", provider: "orders-api", dir: "pacts" });

it("returns an order by id", async () => {
  await pact
    .addInteraction()
    .given("an order exists", { id: "7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111" })
    .uponReceiving("a request for an order")
    .withRequest("GET", "/orders/7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111")
    .willRespondWith(200, (b) =>
      b.headers({ "content-type": "application/json" }).jsonBody({
        id: uuid("7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111"),
        status: regex(/^(pending|paid|failed)$/, "paid"),
        totalCents: integer(1250),
      }),
    )
    .executeTest(async (mockServer) => {
      const order = await getOrder(mockServer.url, "7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111");
      expect(order.status).toBe("paid");
    });
});
```

CI job with a health-checked PostgreSQL service container (inputs and event data stay out of `run:`):

```yaml
jobs:
  integration:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: ci-only-password
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npm run test:integration
        env:
          TEST_DATABASE_URL: postgres://postgres:ci-only-password@localhost:5432/postgres
```

## 15. Common Mistakes

- **Mocking the database or ORM in an "integration" test**: it then checks only your mock. Use a real engine of the production version.
- **SQLite or H2 standing in for PostgreSQL or MySQL**: different SQL, types, locking and JSON behavior; bugs reach production.
- **One shared database for all tests and developers**: tests depend on leftover rows and run order. Use per-run containers and per-file databases.
- **Running migrations before every test**: seconds per test. Migrate once into a template and clone.
- **Truncating a database shared by parallel workers**: workers wipe each other's rows. One database per worker or file.
- **`sleep(2000)` waits**: slow when the system is fast, flaky when it is slow. Poll for a condition with a timeout.
- **Hardcoded ports and hosts**: collide on shared runners. Use mapped ports from the container object.
- **Real third-party calls in tests**: slow, flaky, costly and a data leak risk. Stub at the HTTP boundary and verify with contracts.
- **Pact contracts that copy the full response or assert exact values**: any provider change fails consumers. Use matchers and only the fields the consumer reads.
- **Retrying failures by default**: hides real race conditions. Fix the cause; use retries only as labeled, temporary quarantine.
- **Order-dependent tests**: pass in sequence, fail in parallel or in isolation. Create data per test and shuffle order.
- **Using `${{ inputs.* }}` or event fields inside `run:` lines**: shell injection risk. Pass them via `env:`.
- **Leaving containers running (reuse enabled, reaper disabled) on CI**: leaks resources and state. Keep reuse for local development only.
- **Treating coverage as the goal**: integration tests are for wiring risk, not line counts.

## 16. References

- [references/testcontainers.md](references/testcontainers.md): module and version matrix, Node harness (global setup, template database, per-file clone, supertest and MSW test), isolation strategies, wait strategies, brokers, Java and Python notes, CI service containers, troubleshooting.
- [references/contract-testing.md](references/contract-testing.md): Pact consumer and provider tests that were run, Pact Broker CLI flow, MSW versus WireMock versus nock, WireMock admin API, keeping stubs honest.
- Official docs: https://node.testcontainers.org/ , https://java.testcontainers.org/ , https://testcontainers-python.readthedocs.io/ , https://docs.pact.io/ , https://mswjs.io/docs/ , https://wiremock.org/docs/ , https://vitest.dev/guide/ , https://docs.github.com/en/actions/using-containerized-services/about-service-containers
