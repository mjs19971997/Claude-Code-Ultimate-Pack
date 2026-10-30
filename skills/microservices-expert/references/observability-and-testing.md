# Observability, Contract Testing and Migration

Reference for tracing and metrics across services with OpenTelemetry, consumer-driven contract testing with Pact, and migrating from a monolith with the strangler fig pattern. Verified against OpenTelemetry specification status (traces, metrics and logs stable; OTLP profiles in development), `@opentelemetry/api` 1.10.0, `@opentelemetry/sdk-node` 0.300.0 (Node.js SDK; the package is versioned with the experimental 0.x line even though the tracing, metrics and logs APIs and SDKs are stable), `@pact-foundation/pact` 17.1.x and `pact-broker-cli` (2026-10).

## 1. OpenTelemetry status and vocabulary

| Signal | Specification status | Notes |
|---|---|---|
| Traces | Stable (API, SDK, OTLP) | W3C Trace Context is the default propagation format |
| Metrics | Stable core (API, SDK, OTLP) with some parts still marked mixed or in development; check each language SDK | Use for RED metrics (rate, errors, duration) per service and per route |
| Logs | Stable log SDK and OTLP; the Logs Bridge API is for log-library appenders, not for direct application calls | Correlate by writing `trace_id` and `span_id` into structured logs |
| Profiles | Development (OTLP profiles) | Do not depend on it in production pipelines yet |

- Semantic conventions (attribute names) are versioned separately and parts of them (for example messaging) can still change; check the current semantic conventions before standardizing attribute names. Use the `@opentelemetry/semantic-conventions` constants for stable attributes such as `service.name`.
- The OpenTelemetry Collector receives OTLP, processes (batching, attribute redaction, tail sampling) and exports to the backend of your choice. Run one near each workload and keep exporters out of application code where possible.
- Propagation: the default propagators in the Node.js SDK are W3C Trace Context (`traceparent`, `tracestate`) and W3C Baggage. Baggage travels to every downstream service and may leave your boundary; never put secrets or personal data in it.

## 2. Node.js bootstrap

Install `@opentelemetry/api`, `@opentelemetry/sdk-node`, an OTLP exporter, and `@opentelemetry/auto-instrumentations-node`. Load the bootstrap before any application import (for example `node --import ./telemetry.js server.js` for ESM, or `--require` for CommonJS), otherwise HTTP and database modules are not patched.

```ts
// telemetry.ts - compiled to telemetry.js and loaded first
import { NodeSDK } from "@opentelemetry/sdk-node";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";

const sdk = new NodeSDK({
  instrumentations: [getNodeAutoInstrumentations()],
  // With no traceExporter configured, the SDK sets up the OTLP exporter (http/protobuf)
  // and reads its endpoint and headers from the OTEL_EXPORTER_OTLP_* environment variables.
});

sdk.start();

process.on("SIGTERM", () => {
  sdk.shutdown().finally(() => process.exit(0)); // flush buffered spans before exit
});
```

```bash
export OTEL_SERVICE_NAME=orders
export OTEL_RESOURCE_ATTRIBUTES="service.version=1.8.2,deployment.environment.name=production"
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
```

- The default sampler records all traces; in high-volume production use a parent-based ratio sampler at the SDK and, if you need to keep all errors and slow traces, tail sampling in the Collector.
- Auto-instrumentation covers HTTP servers and clients, common database drivers and some messaging clients. Add manual spans around business operations (a saga step, a payment capture), with low-cardinality names and attributes such as `tenant.id` only when the backend can handle the cardinality.
- Keep OTLP endpoints on a private network or behind authentication; the exporter header values belong in a secret store, not in the image.

## 3. Trace context through messages

HTTP instrumentation propagates context automatically. For messages, inject on the producer side and extract on the consumer side. With the outbox, capture the `traceparent` when the row is written (the request context is available then) and copy it into the message headers in the relay.

```ts
import { context, propagation, trace, SpanKind, SpanStatusCode } from "@opentelemetry/api";

const tracer = trace.getTracer("orders");

// When writing the outbox row: capture the active context into a carrier.
export function currentTraceparent(): string | undefined {
  const carrier: Record<string, string> = {};
  propagation.inject(context.active(), carrier);
  return carrier["traceparent"];
}

// In the consumer: rebuild the context from message headers and run the handler inside a CONSUMER span.
export function handleMessage<T>(headers: Record<string, string>, topic: string, fn: () => Promise<T>): Promise<T> {
  const parent = propagation.extract(context.active(), headers);
  return tracer.startActiveSpan(
    `process ${topic}`,
    { kind: SpanKind.CONSUMER, attributes: { "messaging.system": "kafka", "messaging.destination.name": topic } },
    parent,
    async (span) => {
      try {
        return await fn();
      } catch (err) {
        span.recordException(err as Error);
        span.setStatus({ code: SpanStatusCode.ERROR });
        throw err;
      } finally {
        span.end();
      }
    },
  );
}
```

- Use the extracted context as the parent for a single-message handler. When one span processes a batch, or the producer-to-consumer gap is long (hours, delayed retries), start a new trace and add span links to the producer spans instead of a parent.
- Include the saga id as a span attribute so one saga can be found across traces.
- Sensitive data: do not record request bodies or message payloads as span attributes; scrub query parameters and authorization headers.

## 4. Metrics, logs and alerts

- RED per service and route: request rate, error rate, duration histogram. For consumers: lag, processing duration, retry count, DLQ rate, oldest unpublished outbox row age.
- Dependency view: a metric per downstream (calls, errors, latency, breaker state, bulkhead rejections) from the client side.
- Logs: structured JSON with `trace_id`, `span_id`, service, version and tenant id; sampling for noisy logs, never for errors.
- Alert on symptoms tied to user journeys and SLO burn rates, with dependency metrics as diagnosis aids.

## 5. Consumer-driven contract testing with Pact

The consumer defines the interactions it needs; the generated pact is verified against the real provider. A Pact Broker (or a hosted service) stores pacts and verification results and answers `can-i-deploy`.

### Consumer test (HTTP)

```ts
import path from "node:path";
import { Pact, Matchers, SpecificationVersion } from "@pact-foundation/pact";
import { getOrder } from "../src/orders-client"; // the real client code under test

const { like, integer, string } = Matchers;

const pact = new Pact({
  consumer: "checkout-web-bff",
  provider: "orders-service",
  dir: path.resolve(process.cwd(), "pacts"),
  spec: SpecificationVersion.SPECIFICATION_VERSION_V4,
});

it("fetches an order for a tenant", async () => {
  await pact
    .addInteraction()
    .given("order 9d2b exists for tenant acme")
    .uponReceiving("a request for order 9d2b")
    .withRequest("GET", "/orders/9d2b", (b) => {
      b.headers({ Accept: "application/json", Authorization: like("Bearer test-token") });
    })
    .willRespondWith(200, (b) => {
      b.headers({ "Content-Type": "application/json" });
      b.jsonBody({ id: string("9d2b"), status: string("PENDING"), totalCents: integer(4200) });
    })
    .executeTest(async (mockServer) => {
      const order = await getOrder(mockServer.url, "9d2b", "test-token");
      expect(order.status).toBe("PENDING");
    });
});
```

Contract only the fields the consumer reads, with type matchers rather than exact values, so the provider keeps freedom to add fields.

### Provider verification

```ts
import { Verifier } from "@pact-foundation/pact";

await new Verifier({
  provider: "orders-service",
  providerBaseUrl: "http://127.0.0.1:3000", // the service started with a test database
  pactBrokerUrl: process.env.PACT_BROKER_BASE_URL,
  pactBrokerToken: process.env.PACT_BROKER_TOKEN,
  consumerVersionSelectors: [{ mainBranch: true }, { deployedOrReleased: true }],
  enablePending: true,                 // new pacts do not break the provider build until verified once
  publishVerificationResult: process.env.CI === "true",
  providerVersion: process.env.GIT_SHA,
  providerVersionBranch: process.env.GIT_BRANCH,
  stateHandlers: {
    "order 9d2b exists for tenant acme": async () => {
      await seedOrder({ id: "9d2b", tenant: "acme", status: "PENDING", totalCents: 4200 });
    },
  },
}).verifyProvider();
```

- State handlers set up data in a test database; they do not mock the code under test.
- Verify authorization paths too: add interactions where tenant B requests tenant A's order and expect `404` or `403`, so the contract documents isolation.
- Consumer version selectors define which consumer pacts a provider verifies (main branch, deployed or released versions); check the Pact documentation for the selector syntax of your broker version.

### Message contracts (events)

Use the asynchronous interaction API for events: the consumer states the message shape it can handle and runs its handler against it; the provider verifies that its producing code generates a matching message.

```ts
import { Pact, Matchers, v4SynchronousBodyHandler } from "@pact-foundation/pact";
const { like, regex } = Matchers;

const messagePact = new Pact({ consumer: "billing", provider: "orders-service" });

it("handles order.placed.v1", () =>
  messagePact
    .addAsynchronousInteraction()
    .given("an order was placed")
    .expectsToReceive("an order.placed.v1 event", (b: any) => {
      b.withJSONContent({ orderId: like("9d2b"), totalCents: like(4200), currency: regex("^[A-Z]{3}$", "EUR") })
       .withMetadata({ topic: "orders.events" });
    })
    .executeTest(v4SynchronousBodyHandler(billingHandler)));
```

### Release gate with can-i-deploy

```bash
pact-broker-cli can-i-deploy \
  --pacticipant orders-service --version "$GIT_SHA" \
  --to-environment production \
  --broker-base-url "$PACT_BROKER_BASE_URL"
```

The command succeeds only when all contracts involving this version are verified against what is deployed in the target environment. Record deployments in the broker after each release so it knows what is in each environment. Check `pact-broker-cli can-i-deploy --help` for the options of your installed version and credentials via environment variables rather than flags in CI logs.

### What contract tests do not cover

They do not test business behavior, performance or end-to-end journeys. Pair them with provider integration tests, a few end-to-end journeys, and schema checks on event contracts.

## 6. Strangler fig migration

1. Put a routing facade (gateway, reverse proxy, or a thin proxy module) in front of the monolith. All traffic passes through it unchanged.
2. Choose a slice with a clear boundary and low coupling (a capability with few inbound dependencies). Define its API and events first.
3. Build the new service behind the facade. Add an anti-corruption layer where it must read monolith data, so the old model does not leak.
4. Move data ownership explicitly. Prefer: new service owns writes for the slice; the monolith reads through the service API or a replicated read model. For the transition, replicate with CDC or an outbox, not with application-level dual writes, which diverge on partial failure.
5. Shift traffic gradually (by tenant, by percentage, or by route), comparing results with shadow traffic or a read-only comparison where possible. Keep a fast rollback at the router.
6. When the new path serves everything, delete the old code and tables for the slice. A strangler that never finishes leaves two systems to maintain.
7. Repeat for the next slice; each step must leave the system releasable.

Signs to stop and merge back: services always deployed together, chatty synchronous calls between the new service and the monolith, or no team that can own the new service.

Official docs: https://opentelemetry.io/docs/specs/status/ , https://opentelemetry.io/docs/languages/js/ , https://docs.pact.io/ , https://github.com/pact-foundation/pact-js , https://github.com/pact-foundation/pact-broker-cli
