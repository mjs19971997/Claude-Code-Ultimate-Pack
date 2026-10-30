# OpenTelemetry SDKs, Propagation and Instrumentation

Setting up OpenTelemetry in applications: environment-variable configuration, zero-code agents, manual spans and metrics, context propagation, semantic conventions, logs correlation and troubleshooting. Verified against the OpenTelemetry specification v1.62.0 (SDK environment variables and OTLP exporter documents) and semantic conventions v1.44.0 (2026-10). Per-language SDK versions and defaults differ from the specification: check the language's own documentation for the version in use.

## Contents

1. [Signal status](#1-signal-status)
2. [Configuration through environment variables](#2-configuration-through-environment-variables)
3. [Zero-code instrumentation](#3-zero-code-instrumentation)
4. [Manual instrumentation](#4-manual-instrumentation)
5. [Context propagation](#5-context-propagation)
6. [Semantic conventions](#6-semantic-conventions)
7. [Logs and correlation](#7-logs-and-correlation)
8. [Troubleshooting missing telemetry](#8-troubleshooting-missing-telemetry)

## 1. Signal status

| Signal | Specification status | Practical note |
|---|---|---|
| Traces | Stable | API, SDK and OTLP are stable and under long-term support |
| Metrics | API "Stable, except where otherwise specified" | Data model stable. Advisory parameters `Attributes` and `OptIn` are in development; `ExplicitBucketBoundaries` is stable |
| Logs | API and SDK "Stable, except where otherwise specified" | The ergonomic logs API is in development. Most applications keep their logging library and attach a log bridge or write JSON with trace IDs |
| Baggage | SDK stable | Propagates key-value pairs; no OTLP signal |

- Language SDKs mark each signal separately (stable, beta, development). Confirm on the language status page before relying on logs or metrics in a given language.
- Semantic conventions are versioned separately from the specification (v1.44.0 is the latest release listed). HTTP conventions are stable; for other domains check each convention's status before depending on attribute names.

## 2. Configuration through environment variables

Configure through the environment so the same artifact runs in every stage; code stays free of endpoints and credentials.

| Variable | Meaning and default |
|---|---|
| `OTEL_SERVICE_NAME` | Sets `service.name`; takes precedence over `OTEL_RESOURCE_ATTRIBUTES` |
| `OTEL_RESOURCE_ATTRIBUTES` | Comma-separated `key=value` pairs, for example `service.version=1.8.2,deployment.environment.name=prod` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Base URL. Default `http://localhost:4317` for gRPC and `http://localhost:4318` for HTTP. For HTTP, `/v1/traces`, `/v1/metrics`, `/v1/logs` are appended |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (and `_METRICS_`, `_LOGS_`) | Per-signal URL used exactly as given (an empty path becomes `/`) |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc`, `http/protobuf` or `http/json`; `http/protobuf` is the recommended default, SDKs must support `grpc` or `http/protobuf` |
| `OTEL_EXPORTER_OTLP_HEADERS` | `key=value,key2=value2` (W3C baggage format); use for tokens supplied from a secret |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | Trusted CA/server certificate file |
| `OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE`, `OTEL_EXPORTER_OTLP_CLIENT_KEY` | Client certificate and key for mTLS |
| `OTEL_EXPORTER_OTLP_COMPRESSION` | `gzip` or `none` |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | Whole-batch export timeout, default 10 s, including retries |
| `OTEL_TRACES_EXPORTER`, `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER` | Default `otlp`; also `console`, `none`; metrics also `prometheus`; traces also `zipkin` |
| `OTEL_TRACES_SAMPLER` | Default `parentbased_always_on`; also `always_on`, `always_off`, `traceidratio`, `parentbased_always_off`, `parentbased_traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG` | Ratio from 0 to 1 for the ratio samplers (default 1.0) |
| `OTEL_PROPAGATORS` | Default `tracecontext,baggage`; also `b3`, `b3multi`, `none`. Add `b3` only to interoperate with legacy services |
| `OTEL_SDK_DISABLED` | `true` installs a no-op SDK for all signals (does not affect propagators) |
| `OTEL_METRIC_EXPORT_INTERVAL` | Default 60000 ms |
| `OTEL_BSP_SCHEDULE_DELAY`, `_EXPORT_TIMEOUT`, `_MAX_QUEUE_SIZE`, `_MAX_EXPORT_BATCH_SIZE` | Batch span processor: 5000 ms, 30000 ms, 2048, 512 |
| `OTEL_ATTRIBUTE_COUNT_LIMIT`, `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` | 128 and unlimited by default; set a value limit to cap large attributes |

Typical production block (values supplied by the deployment, token from a secret store):

```bash
OTEL_SERVICE_NAME=orders-api
OTEL_RESOURCE_ATTRIBUTES=service.version=2.4.0,deployment.environment.name=prod
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-gateway.example.internal:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_CERTIFICATE=/etc/ssl/otel/ca.crt
OTEL_EXPORTER_OTLP_COMPRESSION=gzip
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.05
# OTEL_EXPORTER_OTLP_HEADERS is injected from the secret store, never committed
```

## 3. Zero-code instrumentation

Zero-code (automatic) instrumentation attaches to a runtime and instruments common libraries without code changes. It covers inbound and outbound HTTP, gRPC, databases, caches and messaging for supported libraries; it knows nothing about business operations, so add manual spans for those.

| Runtime | How it attaches |
|---|---|
| Java | `java -javaagent:/path/to/opentelemetry-javaagent.jar -jar app.jar`; configuration through `OTEL_*` variables or `-Dotel.*` system properties |
| Python | `pip install opentelemetry-distro opentelemetry-exporter-otlp`, `opentelemetry-bootstrap -a install`, then `opentelemetry-instrument python app.py` (works with `OTEL_*` variables) |
| Node.js | Install `@opentelemetry/api` and `@opentelemetry/auto-instrumentations-node`, run `node --require @opentelemetry/auto-instrumentations-node/register app.js` |
| .NET | The OpenTelemetry .NET Automatic Instrumentation project provides install and instrument scripts; follow its documentation for the version |
| Go | No in-process agent; wrap handlers and clients with `otelhttp`, `otelgrpc` and similar libraries, or evaluate the eBPF-based Go auto-instrumentation project (check its current status) |
| Kubernetes | The OpenTelemetry Operator can inject agents with an `Instrumentation` resource and pod annotations; manifests belong to kubernetes-expert |

- Pre-forking servers (gunicorn, uWSGI) need SDK initialisation after the fork, in a post-fork hook; otherwise background export threads die in the worker.
- Disable noisy instrumentations (health checks, static files) through the agent's per-instrumentation switches or exclusion lists rather than sampling them away later.
- Agents add startup time and memory; measure a canary before fleet rollout.

## 4. Manual instrumentation

Manual API calls add business spans and metrics. Libraries depend only on the API package; the application owns SDK setup. Without an installed SDK, API calls are no-ops, which is safe.

Explicit SDK setup in Python (endpoint, headers, certificates, sampler and resource still come from the environment):

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
# on shutdown: provider.shutdown()
```

Node.js SDK setup in `instrumentation.mjs`, loaded with `node --import ./instrumentation.mjs app.mjs`:

```javascript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";

const sdk = new NodeSDK({ instrumentations: [getNodeAutoInstrumentations()] });
sdk.start();
process.on("SIGTERM", () => sdk.shutdown().finally(() => process.exit(0)));
```

Spans:

- Kinds: `SERVER` (inbound request), `CLIENT` (outbound call), `PRODUCER` and `CONSUMER` (messaging), `INTERNAL` (default).
- Name by operation, low cardinality. Attributes carry identifiers. Add events for notable moments, and `record_exception` for errors.
- Status: set `ERROR` on failure; leave unset otherwise.
- Use span links to connect a batch-processing span to the many producer spans it consumed.

Metrics (Python API):

```python
from opentelemetry import metrics

meter = metrics.get_meter("orders")
orders = meter.create_counter("orders.placed", unit="{order}", description="Orders placed")
duration = meter.create_histogram("orders.charge.duration", unit="s", description="Payment latency")

orders.add(1, {"payment.method": "card"})
duration.record(0.182, {"payment.method": "card"})
```

- Instrument types: counter and up-down counter (additive), histogram (distributions), gauge (non-additive current value), and observable (async callback) variants.
- Attribute values must be bounded; never use a user ID or raw URL. Views can drop attributes or change histogram buckets; SDKs apply an aggregation cardinality limit whose default and configuration are SDK-specific.
- When exported to Prometheus, dots become underscores, the unit becomes a suffix (`orders_charge_duration_seconds`) and monotonic counters get `_total`, depending on the translation strategy configured (see [promql.md](promql.md)).

## 5. Context propagation

- Default propagators are W3C Trace Context (`traceparent`, `tracestate`) and W3C Baggage (`baggage`).
- `traceparent` format: `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01` (version, 32-hex trace ID, 16-hex parent span ID, flags; `01` = sampled).
- Instrumented HTTP and gRPC clients and servers propagate automatically. For queues, background jobs and custom transports, inject and extract manually:

```python
from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("jobs")

def publish(queue, payload: bytes) -> None:
    headers: dict[str, str] = {}
    with tracer.start_as_current_span("orders publish", kind=SpanKind.PRODUCER):
        inject(headers)                      # writes traceparent (and baggage)
        queue.send(payload, headers=headers)

def handle(message) -> None:
    ctx = extract(message.headers)
    with tracer.start_as_current_span("orders process", context=ctx, kind=SpanKind.CONSUMER):
        ...
```

- Use the same propagator set across all services. Mixed `b3` and `tracecontext` fleets split traces; if both are required, list both in `OTEL_PROPAGATORS` during migration.
- Baggage is copied to every outgoing request, including calls to third parties. Do not place user identifiers, tokens or other sensitive values in it, and strip it at the edge.
- Reverse proxies and API gateways must forward `traceparent`; some strip unknown headers. If a gateway starts its own traces, configure it to continue the incoming one.

## 6. Semantic conventions

- Use the standard attribute names so backends and dashboards work across languages: `http.request.method`, `http.response.status_code`, `http.route`, `url.path`, `url.full` (may contain secrets in query strings; redact), `server.address`, `server.port`, `error.type`, `exception.type`, `exception.message`.
- Resource attributes: `service.name`, `service.version`, `service.namespace`, `service.instance.id`, `deployment.environment.name`, `host.name`, cloud and Kubernetes attributes added by resource detectors.
- HTTP conventions changed names in the stable release (for example `http.method` became `http.request.method`). Instrumentations that still emit old names honour `OTEL_SEMCONV_STABILITY_OPT_IN` (`http` for new names only, `http/dup` for both during migration). Dashboards and rules built on old names break when it flips: migrate them together.
- Custom attributes use a company or domain namespace (`acme.order.priority`) and never reuse a standard name with a different meaning.
- Prefer one attribute per fact; avoid packing JSON blobs into a single value.

## 7. Logs and correlation

- Keep the existing logging library; make it emit JSON to stdout with `trace_id` and `span_id` taken from the active span context. Many logging instrumentations inject them automatically (Java MDC keys, Python logging record fields); verify the field names the instrumentation produces.
- IDs are lowercase hex: 32 characters for the trace ID, 16 for the span ID.
- OTLP logs: use the logging library's OpenTelemetry bridge or appender when logs should travel over OTLP; the Collector can also tail files with a file log receiver. The log record then carries trace context natively.
- Levels: `DEBUG` for diagnostics (off in production by default), `INFO` for state changes, `WARN` for recoverable anomalies, `ERROR` for failed operations that need attention. One error log per failure at the layer that handles it, not at every layer it passes through.
- Never log request bodies, credentials, tokens, full URLs with query strings, or personal data. Mask or omit; if a user must be correlated, log an internal opaque ID.
- Configure the log data source in Grafana with a derived field on `trace_id` to link to the trace data source, and the trace data source to link back to logs by `trace_id`.

## 8. Troubleshooting missing telemetry

1. Nothing arrives: check `OTEL_SDK_DISABLED`, the exporter name (`OTEL_TRACES_EXPORTER`), the endpoint scheme and port (4317 for gRPC, 4318 for HTTP), and the protocol. A gRPC exporter pointed at port 4318 (or the reverse) fails with connection or protocol errors.
2. Wrong path: setting `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to a base URL without `/v1/traces` returns 404 over HTTP, because per-signal endpoints are used verbatim.
3. TLS errors: the CA is not trusted (`OTEL_EXPORTER_OTLP_CERTIFICATE`), the certificate name does not match, or an `http://` endpoint hits a TLS listener. Fix the certificates; do not disable verification.
4. Authentication errors: wrong header name or value in `OTEL_EXPORTER_OTLP_HEADERS`; the format is `key=value` pairs without quotes or spaces around commas.
5. Traces broken into pieces: a hop does not propagate `traceparent` (proxy stripping, custom client, queue), propagators differ between services, or samplers are not parent-based.
6. Only the first request traced or spans missing at exit: short-lived processes did not call `shutdown` or `force_flush`; pre-forking server initialised the SDK before forking.
7. Everything sampled out: a ratio sampler with a tiny argument, or `always_off` left over from a kill switch.
8. Spans arrive but have `unknown_service`: `OTEL_SERVICE_NAME` is not set in that process.
9. Collector drops data: check `memory_limiter` refusals, exporter queue enqueue failures and the `debug` exporter output on a test pipeline (see [collector.md](collector.md)).
10. Verify locally by setting `OTEL_TRACES_EXPORTER=console` to confirm the application creates spans before debugging the network path.
