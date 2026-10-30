# Contract Testing and HTTP Stubs

Reference for consumer-driven contract tests with Pact, publishing and gating on a Pact Broker, and for stubbing external HTTP APIs with MSW or WireMock. Verified against `@pact-foundation/pact` 17.1.x (Node 22 or later, Pact specification V4 through `Pact`), pact-broker-cli 0.9.x, MSW 3.0.x, WireMock 3.13.x (stable; 4.0 is still beta), nock 15.0.x and Vitest 5.0.x (2026-10).

## 1. When to use which technique

| Technique | Verifies | Needs the other side running | Use for |
|---|---|---|---|
| Stub server (MSW, WireMock, nock) | Your client or service behaves correctly for the responses you scripted | No | Third-party APIs you do not control; error, timeout and retry paths |
| Contract test (Pact) | Consumer expectations are met by the real provider, and the provider cannot break them unnoticed | Provider verification runs against the real provider build | Service-to-service APIs inside one organization or with a cooperating partner |
| Full integration environment | Real wiring across services | Yes | Few smoke checks only; slow and flaky at scale |

A stub proves only that your code matches your assumptions. If the assumption is wrong, the test still passes. Contract tests close that gap by turning the consumer's assumptions into a file the provider must satisfy.

## 2. Pact flow

1. The consumer writes tests against a Pact mock server. Each test declares an interaction (provider state, request, expected response). The run writes a pact file (JSON).
2. The consumer CI publishes the pact file to a Pact Broker, tagged with the commit and branch.
3. The provider CI verifies the pacts for its consumers against the real provider, setting up provider states through state handlers, and publishes verification results.
4. `can-i-deploy` asks the broker whether a version is compatible with what runs in the target environment; deployments are recorded with `record-deployment`.

Rules that keep contracts healthy:
- Specify only what the consumer actually uses. Use matchers (type, regex, integer, UUID) instead of exact values wherever the value is not part of the contract.
- Do not turn Pact into a functional test of the provider's business logic. One interaction per distinct request shape and response class (success, not found, validation error) is usually enough.
- Provider states describe data preconditions ("an order exists"), not implementation. Pass parameters (`.given("an order exists", { id })`) so handlers stay generic.
- Treat the pact file as a build artifact; do not edit by hand. Delete the `pacts/` directory before a fresh consumer run so stale interactions do not linger.

## 3. Consumer test with Pact JS 17

In `@pact-foundation/pact` 17.x the root export `Pact` is the V4 API and `MatchersV3` provides matchers. The consumer code under test:

```ts
export interface Order {
  id: string;
  status: "pending" | "paid" | "failed";
  totalCents: number;
}

export async function getOrder(baseUrl: string, id: string): Promise<Order> {
  const res = await fetch(`${baseUrl}/orders/${encodeURIComponent(id)}`, {
    headers: { accept: "application/json" },
  });
  if (!res.ok) throw new Error(`orders service responded ${res.status}`);
  return (await res.json()) as Order;
}
```

The contract test (the suite was run with Vitest and passes; it writes `pacts/checkout-web-orders-api.json`):

```ts
import path from "node:path";
import { MatchersV3, Pact } from "@pact-foundation/pact";
import { describe, expect, it } from "vitest";
import { getOrder } from "../src/orders-client.ts";

const { like, regex, integer, uuid } = MatchersV3;

const pact = new Pact({
  consumer: "checkout-web",
  provider: "orders-api",
  dir: path.resolve(process.cwd(), "pacts"),
  logLevel: "warn",
});

describe("orders-api contract", () => {
  it("returns an order by id", async () => {
    await pact
      .addInteraction()
      .given("an order exists", { id: "7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111", status: "paid", totalCents: 1250 })
      .uponReceiving("a request for an order")
      .withRequest("GET", "/orders/7b0f6f0e-2a0e-4b9e-9a39-0c9b2a1a1111", (b) =>
        b.headers({ accept: "application/json" }),
      )
      .willRespondWith(200, (b) =>
        b
          .headers({ "content-type": "application/json" })
          .jsonBody({
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

  it("surfaces a 404 for an unknown order", async () => {
    await pact
      .addInteraction()
      .given("no order exists")
      .uponReceiving("a request for a missing order")
      .withRequest("GET", "/orders/00000000-0000-4000-8000-000000000000", (b) =>
        b.headers({ accept: "application/json" }),
      )
      .willRespondWith(404, (b) => b.headers({ "content-type": "application/json" }).jsonBody({ error: like("not_found") }))
      .executeTest(async (mockServer) => {
        await expect(getOrder(mockServer.url, "00000000-0000-4000-8000-000000000000")).rejects.toThrow("404");
      });
  });
});
```

## 4. Provider verification

Start the real provider with a test database, and replay every consumer interaction against it. State handlers receive the parameters declared by the consumer:

```ts
import type { Server } from "node:http";
import path from "node:path";
import { Verifier } from "@pact-foundation/pact";
import { afterAll, beforeAll, describe, it } from "vitest";
import { createApp } from "../src/app.ts";
import { createTestDb, type TestDb } from "./helpers/test-db.ts";

let db: TestDb;
let server: Server;
let baseUrl: string;

beforeAll(async () => {
  db = await createTestDb();
  const app = createApp({ pool: db.pool, paymentsUrl: "http://127.0.0.1:1" }); // never called in these interactions
  await new Promise<void>((resolve) => {
    server = app.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address();
  baseUrl = `http://127.0.0.1:${typeof address === "object" && address ? address.port : 0}`;
});

afterAll(async () => {
  await new Promise((resolve) => server.close(resolve));
  await db.drop();
});

describe("orders-api provider verification", () => {
  it("honours the checkout-web contract", async () => {
    await new Verifier({
      provider: "orders-api",
      providerBaseUrl: baseUrl,
      pactUrls: [path.resolve(process.cwd(), "pacts", "checkout-web-orders-api.json")],
      stateHandlers: {
        "an order exists": async (params) => {
          const p = params as { id: string; status: string; totalCents: number };
          await db.pool.query(
            "INSERT INTO orders (id, customer_id, total_cents, status) VALUES ($1, gen_random_uuid(), $2, $3)",
            [p.id, p.totalCents, p.status],
          );
        },
        "no order exists": async () => {
          await db.pool.query("TRUNCATE orders");
        },
      },
    }).verifyProvider();
  });
});
```

Notes:
- Run verification after the consumer tests have produced the pact file (or after fetching pacts from the broker), not in parallel with them.
- In production pipelines fetch pacts from the broker instead of a file: pass `pactBrokerUrl`, `provider`, `consumerVersionSelectors` (for example main branch and deployed or released versions), `enablePending`, `includeWipPactsSince`, `providerVersion`, `providerVersionBranch` and `publishVerificationResult: true` only in CI. Broker credentials come from environment variables or the CI secret store.
- If an HTTP proxy variable is set in the environment, the native verifier may route loopback traffic through the proxy; exclude `127.0.0.1` and `localhost` via `NO_PROXY` or unset the proxy variables for the verification step.
- Replace outbound calls of the provider (databases stay real) with stubs only for dependencies that are not part of the interaction.

## 5. Pact Broker CLI

`pact-broker-cli` (the Pact Foundation CLI, 0.9.x) publishes pacts, checks deployability and records deployments. Authentication uses `PACT_BROKER_BASE_URL` plus either basic auth (`PACT_BROKER_USERNAME`, `PACT_BROKER_PASSWORD`) or a bearer token (`PACT_BROKER_TOKEN`, used by PactFlow). Keep credentials in CI secrets.

```bash
# consumer CI, after tests: publish pacts for this commit and branch
pact-broker-cli publish ./pacts \
  --consumer-app-version "$GIT_SHA" \
  --branch "$GIT_BRANCH"

# before deploying either side: is this version compatible with what runs in production?
pact-broker-cli can-i-deploy \
  --pacticipant checkout-web --version "$GIT_SHA" \
  --to-environment production

# after a successful deployment
pact-broker-cli record-deployment \
  --pacticipant checkout-web --version "$GIT_SHA" \
  --environment production
```

`$GIT_SHA` and `$GIT_BRANCH` should be set from the CI provider's trusted variables. Environments must be created in the broker before `can-i-deploy --to-environment` works. For other languages, use the Pact implementation for that language: Pact JVM (`au.com.dius.pact`, 4.7.x on Maven Central at the time of writing), pact-python 4.x, pact-go. Their APIs differ from Pact JS; check their docs.

## 6. Stubbing external HTTP

| Tool | How it works | Choose when |
|---|---|---|
| MSW 3 | Intercepts requests inside the Node process (`msw/node`) | Same language as the test; also usable in browser tests; handlers shared between unit, integration and dev |
| nock 15 | Patches Node's HTTP layer | Node-only, small stubs |
| WireMock 3 | Standalone HTTP server (Docker image `wiremock/wiremock`, or the Java library) | Service under test is not in Node, or several services share stubs, or you need fault injection and request journal over HTTP |

MSW rules:
- Create the server once per file, `listen()` in `beforeAll`, `resetHandlers()` in `afterEach`, `close()` in `afterAll`; add per-test handlers with `server.use(...)`.
- Make unhandled external requests fail (`onUnhandledFrame`), so a new outbound call cannot reach a real service silently. See [testcontainers.md](testcontainers.md) for the loopback allowance when using supertest.
- Script failures as well as success: 5xx, 429 with `retry-after`, slow responses (`delay()`), malformed bodies, connection resets via `HttpResponse.error()`.
- Assert what was sent, not only what was received: capture the request inside the handler and assert on headers, body and idempotency keys.

WireMock in a Testcontainers-managed container, stubs registered through the admin API:

```ts
import { GenericContainer, Wait, type StartedTestContainer } from "testcontainers";

let wiremock: StartedTestContainer;
let baseUrl: string;

beforeAll(async () => {
  wiremock = await new GenericContainer("wiremock/wiremock:3.13.2")
    .withExposedPorts(8080)
    .withWaitStrategy(Wait.forHttp("/__admin/mappings", 8080))
    .start();
  baseUrl = `http://${wiremock.getHost()}:${wiremock.getMappedPort(8080)}`;
}, 120_000);

afterAll(async () => { await wiremock.stop(); });

beforeEach(async () => {
  await fetch(`${baseUrl}/__admin/mappings`, { method: "DELETE" });   // remove all stubs
});

it("handles a declined charge", async () => {
  await fetch(`${baseUrl}/__admin/mappings`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      request: { method: "POST", urlPath: "/charges" },
      response: { status: 402, jsonBody: { error: "declined" }, headers: { "Content-Type": "application/json" } },
    }),
  });
  // point the service under test at `baseUrl` and assert its behavior
});
```

WireMock also supports response delays and faults (`fixedDelayMilliseconds`, `fault`), request matching on headers and bodies, scenarios for stateful sequences, and a request journal (`POST /__admin/requests/count`). The Java library offers a JUnit 5 extension; there is also a Testcontainers module for WireMock, which was still an alpha release when this was written, so prefer the plain container above unless you have verified it.

## 7. Keeping stubs honest

- Generate stubs from the provider's OpenAPI document or from recorded real responses where possible, and re-record on a schedule.
- Pair every important stub with a contract (consumer-driven) or a provider-side schema test so drift fails a build.
- Keep stub data minimal and realistic; do not invent fields the real API never returns.
- Tag tests that use stubs only for third-party systems you cannot verify; revisit when a sandbox is available.
