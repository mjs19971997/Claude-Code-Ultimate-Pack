# Testcontainers and Test Databases

Reference for running real dependencies in integration tests with Testcontainers, isolating database state per test, testing message brokers, and running the same suites in CI. Verified against `testcontainers` and `@testcontainers/*` 12.2.x for Node (Node 22.22 or later), Testcontainers for Java 2.0.x (`org.testcontainers:testcontainers`, `testcontainers-junit-jupiter`, `testcontainers-postgresql`), `testcontainers` for Python 4.15.x, testcontainers-go 0.44.x, Vitest 5.0.x, supertest 7.3.x, MSW 3.0.x, `node-postgres` 8.x and PostgreSQL 18 (2026-10).

## 1. What belongs in an integration test

- The unit under test is a service (HTTP API, worker, consumer) wired to real instances of the dependencies it owns: its database, cache, broker, object store. Real dependencies catch SQL mistakes, migrations, serialization, transaction and constraint behavior that mocks hide.
- Dependencies owned by other teams or vendors (payment provider, email, identity provider) are replaced at the HTTP boundary by a stub server (MSW, WireMock) or verified by contract tests; see [contract-testing.md](contract-testing.md).
- Keep business-rule permutations in unit tests; use integration tests for the paths where wiring matters: persistence round trips, constraints, auth middleware, error mapping, retries, message handling.

## 2. Modules and versions

| Language | Package | Notes |
|---|---|---|
| Node | `testcontainers` 12.2.x plus modules such as `@testcontainers/postgresql`, `redis`, `kafka`, `rabbitmq`, `mongodb`, `mysql`, `localstack`, `nats`, `redpanda` | Requires Node 22.22 or later; all packages share the version |
| Java | `org.testcontainers:testcontainers` 2.0.x, modules named `testcontainers-<module>` (for example `testcontainers-postgresql`), JUnit 5 support in `testcontainers-junit-jupiter` | In 2.x the Postgres class is `org.testcontainers.postgresql.PostgreSQLContainer` (not generic) |
| Python | `testcontainers` 4.15.x | Modules live under `testcontainers.community.*` (for example `testcontainers.community.postgres`); the old `testcontainers.postgres` import path is deprecated |
| Go | `github.com/testcontainers/testcontainers-go` 0.44.x | Modules under `modules/` |

All of them need a Docker-compatible runtime. Podman works with `DOCKER_HOST` and `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE` set as described in the Node docs.

## 3. Node harness with template database and per file clone

One container per run, one template database with migrations applied, one cloned database per test file. Files run in parallel without sharing rows. `CREATE DATABASE ... TEMPLATE` copies files and takes tens of milliseconds for small schemas, which is much faster than re-running migrations. The template must have no open connections when cloned.

`test/global-setup.ts` (CI can pass `TEST_DATABASE_URL` for a service container; locally Testcontainers starts one):

```ts
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { PostgreSqlContainer } from "@testcontainers/postgresql";
import { Client } from "pg";
import type { TestProject } from "vitest/node";

declare module "vitest" {
  export interface ProvidedContext {
    pgAdminUri: string;
  }
}

function withDatabase(uri: string, name: string): string {
  const url = new URL(uri);
  url.pathname = `/${name}`;
  return url.toString();
}

export default async function setup(project: TestProject) {
  // CI can supply a service container through TEST_DATABASE_URL; locally Testcontainers starts one.
  const external = process.env.TEST_DATABASE_URL;
  const container = external ? null : await new PostgreSqlContainer("postgres:18").start();
  const adminUri = external ?? container!.getConnectionUri();

  // Build the template database once: create it, run migrations, disconnect.
  const admin = new Client({ connectionString: adminUri });
  await admin.connect();
  await admin.query("DROP DATABASE IF EXISTS app_template WITH (FORCE)");
  await admin.query("CREATE DATABASE app_template");
  await admin.end();

  const tpl = new Client({ connectionString: withDatabase(adminUri, "app_template") });
  await tpl.connect();
  const dir = join(import.meta.dirname, "..", "migrations");
  for (const file of readdirSync(dir).filter((f) => f.endsWith(".sql")).sort()) {
    await tpl.query(readFileSync(join(dir, file), "utf8"));
  }
  await tpl.end(); // CREATE DATABASE ... TEMPLATE needs the template to have no open connections

  project.provide("pgAdminUri", adminUri);
  return async () => {
    await container?.stop();
  };
}
```

`test/helpers/test-db.ts`:

```ts
import { randomUUID } from "node:crypto";
import { Client, Pool } from "pg";
import { inject } from "vitest";

export interface TestDb {
  pool: Pool;
  drop(): Promise<void>;
}

// One cloned database per test file: files run in parallel without sharing rows.
export async function createTestDb(): Promise<TestDb> {
  const adminUri = inject("pgAdminUri");
  const name = `t_${randomUUID().replaceAll("-", "")}`; // hex only, safe as an identifier

  const admin = new Client({ connectionString: adminUri });
  await admin.connect();
  await admin.query(`CREATE DATABASE "${name}" TEMPLATE app_template`);
  await admin.end();

  const url = new URL(adminUri);
  url.pathname = `/${name}`;
  const pool = new Pool({ connectionString: url.toString(), max: 4 });

  return {
    pool,
    async drop() {
      await pool.end();
      const cleanup = new Client({ connectionString: adminUri });
      await cleanup.connect();
      await cleanup.query(`DROP DATABASE IF EXISTS "${name}" WITH (FORCE)`);
      await cleanup.end();
    },
  };
}
```

`vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    globalSetup: ["./test/global-setup.ts"],
    testTimeout: 15_000,
    hookTimeout: 120_000, // first run may pull the database image
  },
});
```

An API test using supertest and MSW against that setup (the whole suite was run against PostgreSQL):

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
  db = await createTestDb();
  app = createApp({ pool: db.pool, paymentsUrl: PAYMENTS });
  payments.listen({
    // Fail on any outbound call without a handler, but let supertest reach the app under test.
    onUnhandledFrame({ frame, defaults }) {
      const data = frame.data as { request?: Request };
      const host = data.request ? new URL(data.request.url).hostname : "";
      if (host === "127.0.0.1" || host === "localhost" || host === "::1") return;
      defaults.error();
    },
  });
});

afterEach(() => payments.resetHandlers());
afterAll(async () => {
  payments.close();
  await db.drop();
});
beforeEach(async () => {
  await db.pool.query("TRUNCATE orders");
});

describe("POST /orders", () => {
  it("stores the order and marks it paid when the payment service accepts", async () => {
    payments.use(http.post(`${PAYMENTS}/charges`, () => HttpResponse.json({ ok: true }, { status: 201 })));
    const customerId = randomUUID();

    const created = await request(app).post("/orders").send({ customerId, totalCents: 1250 }).expect(201);
    expect(created.body.status).toBe("paid");

    const fetched = await request(app).get(`/orders/${created.body.id}`).expect(200);
    expect(fetched.body).toMatchObject({ customerId, totalCents: 1250, status: "paid" });
  });

  it("returns 402 and persists a failed order when the payment is declined", async () => {
    payments.use(http.post(`${PAYMENTS}/charges`, () => HttpResponse.json({ error: "declined" }, { status: 402 })));
    const res = await request(app).post("/orders").send({ customerId: randomUUID(), totalCents: 500 }).expect(402);
    const { rows } = await db.pool.query("SELECT status FROM orders WHERE id = $1", [res.body.id]);
    expect(rows[0].status).toBe("failed");
  });

  it("rejects invalid input without calling the payment service", async () => {
    await request(app).post("/orders").send({ customerId: randomUUID(), totalCents: -5 }).expect(400);
    const { rows } = await db.pool.query("SELECT count(*)::int AS n FROM orders");
    expect(rows[0].n).toBe(0);
  });
});
```

Notes on MSW 3: `onUnhandledRequest` from MSW 2 is replaced by `onUnhandledFrame`, which accepts `'bypass'`, `'warn'`, `'error'` or a callback receiving `{ frame, defaults }`. A plain `'error'` also flags supertest's own request to `127.0.0.1`, which is why the callback above lets loopback traffic through and rejects every other host. Database traffic uses raw TCP and is not intercepted. If your test code makes no loopback HTTP calls (for example it uses `fetch` against a stubbed host only), `onUnhandledFrame: "error"` is enough.

## 4. Database isolation strategies

| Strategy | How | Speed | Use when | Watch out |
|---|---|---|---|---|
| Transaction rollback | `BEGIN` in `beforeEach`, `ROLLBACK` in `afterEach`, code under test uses that connection | Fastest | Repository and query tests | Code that opens its own connections, commits, uses `NOTIFY`, deferred constraints or advisory locks sees different behavior; HTTP tests rarely share the connection |
| Truncate | `TRUNCATE a, b RESTART IDENTITY CASCADE` in `beforeEach` | Fast | One database per worker or file | Must list all tables; truncation takes locks, so never share the database across parallel workers |
| Delete by tenant | Each test creates its own tenant or unique keys and cleans up nothing | Fast, parallel-safe | Multi-tenant schemas, idempotent tests | Requires disciplined unique data |
| Template database clone | `CREATE DATABASE x TEMPLATE app_template` per file or per test | Fast (copy) | Parallel workers, expensive migrations or seed data | Needs superuser or `CREATEDB`; drop clones afterward (`DROP DATABASE ... WITH (FORCE)`) |
| Container snapshot | `await container.snapshot()` then `await container.restoreSnapshot()` (`@testcontainers/postgresql`) | Fast | Sequential suites sharing one database | Restoring drops and recreates the database, so reopen connections; do not use the `postgres` system database as the container database |
| Container per file or per test | New container each time | Slowest | Destructive tests, version matrix | Use sparingly; seconds per container |

Transaction rollback pattern:

```ts
import type { PoolClient } from "pg";

let client: PoolClient;
beforeEach(async () => {
  client = await pool.connect();
  await client.query("BEGIN");
});
afterEach(async () => {
  await client.query("ROLLBACK");
  client.release();
});
```

Truncate pattern for a per-file database:

```ts
beforeEach(async () => {
  await pool.query("TRUNCATE orders, order_items, customers RESTART IDENTITY CASCADE");
});
```

## 5. Test data

- Create data through factories with unique values (`randomUUID()`, counters) so tests do not collide and can run in any order.
- Seed only reference data (countries, plans, permission tables) in the template database; every test creates the rest.
- Prefer inserting rows through the same repository or API code the app uses when it carries invariants, and raw SQL when you need states the app cannot produce.
- Keep factories next to tests; each test states the data it depends on. Avoid giant shared fixtures.
- Never copy production data into tests; generate synthetic data. If a masked dump is unavoidable, treat it as sensitive and keep it out of the repository.
- Time: inject a clock into the code under test or use `vi.useFakeTimers({ toFake: ["Date"] })` when only the date matters; fake timers that also fake `setTimeout` can stall real I/O.

## 6. Wait strategies and networking

- Modules ship sensible wait strategies. For `GenericContainer`, choose one explicitly: `Wait.forListeningPorts()`, `Wait.forLogMessage("ready")`, `Wait.forHttp("/health", 8080)`, `Wait.forHealthCheck()`, `Wait.forSuccessfulCommand("...")`, composed with `Wait.forAll([...])`.
- Never `sleep` to wait for readiness.
- Map ports dynamically: use `container.getHost()` and `container.getMappedPort(5432)` (or module helpers such as `getConnectionUri()`); never hardcode host ports.
- Containers that must talk to each other share a network: `const network = await new Network().start()`, then `.withNetwork(network).withNetworkAliases("db")` and connect through the alias.
- Reuse (`.withReuse()`) keeps containers between runs for local speed; leave it off in CI so every run starts clean.
- The reaper container (Ryuk) removes containers if the test process dies. Disable it (`TESTCONTAINERS_RYUK_DISABLED=true`) only on ephemeral CI machines or where the runtime forbids it, and then make sure containers are stopped in teardown.

## 7. Message brokers

Patterns that keep broker tests deterministic:
- Use a unique queue, topic or consumer group per test (or per file) so leftovers from earlier tests do not leak in.
- Assert on outcomes with polling and a timeout (`vi.waitFor`, `expect.poll`), not fixed sleeps.
- Test the consumer's idempotency by delivering the same message twice and asserting a single effect.
- Test failure paths: poison message goes to the dead-letter queue, retry count is bounded, the consumer commits offsets only after success.

RabbitMQ with `@testcontainers/rabbitmq` and `amqplib`:

```ts
import amqp from "amqplib";
import { RabbitMQContainer, type StartedRabbitMQContainer } from "@testcontainers/rabbitmq";
import { afterAll, beforeAll, expect, it, vi } from "vitest";

let rabbit: StartedRabbitMQContainer;
beforeAll(async () => {
  rabbit = await new RabbitMQContainer("rabbitmq:4-management").start();
}, 120_000);
afterAll(async () => { await rabbit.stop(); });

it("consumes an order event once even when it is delivered twice", async () => {
  const conn = await amqp.connect(rabbit.getAmqpUrl());
  const ch = await conn.createChannel();
  const queue = `orders.${crypto.randomUUID()}`;
  await ch.assertQueue(queue, { durable: false });

  const handled: string[] = [];
  const seen = new Set<string>();
  await ch.consume(queue, (msg) => {
    if (!msg) return;
    const { eventId } = JSON.parse(msg.content.toString());
    if (!seen.has(eventId)) { seen.add(eventId); handled.push(eventId); } // idempotent handler under test
    ch.ack(msg);
  });

  const event = Buffer.from(JSON.stringify({ eventId: "evt-1" }));
  ch.sendToQueue(queue, event);
  ch.sendToQueue(queue, event);

  await vi.waitFor(() => expect(handled).toEqual(["evt-1"]), { timeout: 5_000 });
  await ch.close(); await conn.close();
});
```

Kafka (`@testcontainers/kafka`), Redpanda, NATS, LocalStack (SQS, SNS, S3) follow the same shape: start the module container, take its bootstrap or endpoint URL from the started container object, create unique topics or queues per test, poll for results. Check each module's docs page for the exact getter names and recommended images.

## 8. Other languages

Java with JUnit 5 and Testcontainers 2.x:

```java
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
class OrderRepositoryIT {

    @Container
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:18"); // static: shared by all tests in the class

    @Test
    void connects() throws Exception {
        try (var conn = java.sql.DriverManager.getConnection(
                POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())) {
            // run migrations, exercise the repository
        }
    }
}
```

The JUnit 5 extension is tested with sequential execution; parallel test execution with it is unsupported, so use the singleton container pattern (start once in a static initializer) for parallel suites. With Spring Boot, `@ServiceConnection` on a container field wires connection properties automatically; check the Spring Boot docs for the version you use.

Python with pytest:

```python
import pytest
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:18", driver=None) as pg:  # driver=None gives postgresql://...
        yield pg.get_connection_url()
```

## 9. CI

GitHub Actions runners (`ubuntu-latest`) include Docker, so Testcontainers works without extra setup. Service containers are an alternative when you want the database to start before the job, with a health check:

```yaml
name: integration
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  integration:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: ci-only-password   # throwaway credential for a job-local container
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run test:integration
        env:
          TEST_DATABASE_URL: postgres://postgres:ci-only-password@localhost:5432/postgres
```

- Pass values to scripts through `env:`, not by interpolating `${{ github.event.* }}` or `${{ inputs.* }}` into `run:` lines.
- Cache the Docker image layers or use a registry mirror to avoid rate limits when pulling images (`TESTCONTAINERS_HUB_IMAGE_NAME_PREFIX` points Testcontainers at a mirror).
- Set explicit timeouts for the job and for container startup (`hookTimeout`).
- Upload logs on failure; enable container logs with `DEBUG=testcontainers*` when diagnosing.
- Run integration tests in a separate job from unit tests so failures are attributable and unit feedback stays fast.

## 10. Troubleshooting

- "Could not find a working container runtime": the Docker socket is not reachable; check `DOCKER_HOST` and permissions of the user running tests.
- Timeouts on first run: image pulls; raise `hookTimeout`, pre-pull images in CI.
- Port conflicts: caused by hardcoded ports; use mapped ports.
- ARM and x86 mismatch: choose multi-arch images or set the platform explicitly.
- Flaky readiness: the default wait strategy is not enough for the image; use a log or health check strategy that proves the app is ready for queries.
- Leaked containers: Ryuk disabled and teardown skipped on crash; list with `docker ps` and label filters.
