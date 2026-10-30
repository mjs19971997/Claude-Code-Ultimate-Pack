---
name: observability-expert
description: >-
  Instruments services and builds telemetry pipelines with OpenTelemetry (SDKs, zero-code agents, OTLP, Collector, sampling), Prometheus and PromQL, Grafana dashboards and alerting as code, structured logs correlated by trace_id, and SLO burn-rate alerts with runbooks. Use when editing otel-collector config, prometheus.yml, rule files, alertmanager.yml, Grafana provisioning or OTEL_* variables, or debugging missing traces, high cardinality or noisy alerts. Not for capacity planning or load testing (use scalability-expert), Kubernetes manifests (use kubernetes-expert), cloud-native monitoring (use aws-expert, gcp-expert or azure-expert), or Web Vitals RUM (use core-web-vitals-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Observability Expert

This skill covers making a system observable: emitting traces, metrics and logs with OpenTelemetry, routing them through the Collector, storing and querying metrics in Prometheus, visualising and alerting in Grafana, and defining SLOs with alerts that page on user-visible symptoms. It also covers the safety side: sampling, cardinality control, redaction of sensitive data and protected endpoints. Sizing, load tests and tuning belong to other skills.

> Verified against OpenTelemetry Collector v0.164.0 (core and contrib), OpenTelemetry specification v1.62.0, semantic conventions v1.44.0, Prometheus 3.15.1 (3.16.0-rc.2 is a pre-release), Prometheus Remote Write 2.0 spec 2.0-rc.6 (experimental) and Grafana 13.3.0 (2026-10).

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

- Covered: OpenTelemetry SDK setup and `OTEL_*` environment variables, zero-code instrumentation, OTLP, W3C Trace Context and baggage, Collector pipelines (receivers, processors, connectors, exporters), head and tail sampling, Prometheus scraping, metric types, naming, recording and alerting rules, remote write, PromQL, Grafana provisioning and dashboards as code, Alertmanager routing, structured logging with trace correlation, SLIs, SLOs, error budgets, burn-rate alerts, runbooks, cardinality control.
- Not covered: capacity planning, load testing and performance tuning (scalability-expert); Kubernetes manifests, operators and Helm charts (kubernetes-expert); CloudWatch, Cloud Monitoring or Azure Monitor setup details (aws-expert, gcp-expert, azure-expert); browser Web Vitals and RUM (core-web-vitals-expert); container image builds (docker-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Signal stability | Tracing specification is stable. Metrics API is "Stable, except where otherwise specified" (advisory parameters `Attributes` and `OptIn` are in development; `ExplicitBucketBoundaries` is stable). Logs API and SDK are "Stable, except where otherwise specified" (the ergonomic logs API is in development). Baggage SDK is stable. Per-language SDK status can differ: check the language's own status page |
| Collector versioning | Core and contrib are released together as v0.x (current v0.164.0). Each component declares stability per signal (development, alpha, beta, stable); a component can be 1.x only if stable for at least one signal. Pin the version and read the changelog before upgrading |
| OTLP | gRPC on port 4317, HTTP on port 4318. HTTP signal paths are `/v1/traces`, `/v1/metrics`, `/v1/logs`, appended automatically when only `OTEL_EXPORTER_OTLP_ENDPOINT` is set and used verbatim when a per-signal endpoint variable is set. `OTEL_EXPORTER_OTLP_PROTOCOL` takes `grpc`, `http/protobuf` or `http/json`; `http/protobuf` is the spec's recommended default |
| SDK env vars | `OTEL_SERVICE_NAME` (wins over `service.name` in `OTEL_RESOURCE_ATTRIBUTES`), `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_EXPORTER_OTLP_CERTIFICATE`, `OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE` / `_CLIENT_KEY` (mTLS), `OTEL_EXPORTER_OTLP_TIMEOUT` (10 s), `OTEL_TRACES_SAMPLER` (default `parentbased_always_on`), `OTEL_TRACES_SAMPLER_ARG`, `OTEL_PROPAGATORS` (default `tracecontext,baggage`), `OTEL_SDK_DISABLED`, `OTEL_METRIC_EXPORT_INTERVAL` (60000 ms), `OTEL_BSP_*` batch span processor (queue 2048, batch 512, delay 5000 ms) |
| Context propagation | W3C `traceparent` is `version-traceid(32 hex)-spanid(16 hex)-flags(2 hex)`; flag `01` means sampled. `tracestate` carries vendor data and the OTel sampling threshold (`ot=th:...`). `baggage` carries key-value pairs to downstream services and third parties, and is not added to telemetry automatically |
| Collector pipelines | A pipeline is receivers, then processors in listed order, then exporters, declared under `service.pipelines`. Connectors (for example `spanmetrics`) are an exporter in one pipeline and a receiver in another. Components must be defined and also listed in a pipeline to run |
| Processor order | `memory_limiter` first (so back-pressure reaches receivers), data-shaping processors next (redaction, transform, filter, attributes), samplers after them, `batch` last (after any step that drops data). Defaults: `batch` timeout 200 ms, `send_batch_size` 8192; `memory_limiter` needs `limit_mib` or `limit_percentage` and a `check_interval` (1 s recommended) |
| Exporter queue | Exporters have a `sending_queue` (default queue_size 1000 requests, 10 consumers) and `retry_on_failure` (5 s initial, 30 s max, 300 s max elapsed). Data rejected before entering the queue is dropped and counted in `otelcol_exporter_enqueue_failed_*`. Exporter-level batching exists under `sending_queue.batch` (min_size 8192, flush_timeout 200 ms) |
| Tail sampling | `tail_sampling` processor (traces beta): `decision_wait` default 30 s, `num_traces` default 50000; policies `status_code`, `latency`, `probabilistic`, `string_attribute`, `and`, `composite`, `always_sample`. All spans of a trace must reach the same Collector instance, so scale with a first tier using `loadbalancing` exporter (routing key `traceID`) |
| Prometheus 3.x | Range selectors are left-open; `le` and `quantile` label values are stored as floats (`le="1.0"`); scrapes fail on missing or unknown Content-Type unless `fallback_scrape_protocol` is set; UTF-8 metric and label names are allowed; `holt_winters` became `double_exponential_smoothing` (experimental function); `--agent` flag replaced the agent feature flag |
| Native histograms | Stable since Prometheus v3.8.0. Enable scraping with `scrape_native_histograms: true` (global or per scrape config) and remote write with `send_native_histograms`; the `native-histograms` feature flag no longer does anything from v3.9. Classic histograms (`_bucket`, `_sum`, `_count`) remain valid. The spec says v4 will default both options to true |
| Remote write | Remote Write 1.0 is the stable protocol. Remote Write 2.0 (spec `2.0-rc.6`, experimental) adds native histograms, metadata, start timestamps and a string symbol table; check the receiving backend before enabling |
| Prometheus HTTP flags | Off by default and should stay off unless protected: `--web.enable-otlp-receiver`, `--web.enable-remote-write-receiver`, `--web.enable-lifecycle`, `--web.enable-admin-api`. `--web.config.file` (marked experimental) enables TLS and basic auth |
| Grafana 13.x | Git Sync (bidirectional Git and Grafana resource sync) is generally available per the 13.x release notes; dynamic dashboards and the v2 dashboard schema are the current model; alert rule resources are served as `v1beta1` in 13.3. Read the breaking-changes list before upgrading (13.3 renamed the `marketplace` ini section to `plugins_marketplace`) |
| Alert rule fields | Prometheus alerting rules support `for` (pending time), `keep_firing_for`, `labels` and `annotations`; Alertmanager handles grouping (`group_by`, `group_wait`, `group_interval`), routing, inhibition and silences |

## 3. Workflow

1. Identify what is being asked: instrument a service, route data, add a metric or alert, define an SLO, or debug missing or noisy telemetry. Note language, framework, backends in use and the Collector or Prometheus versions.
2. Inspect existing configuration first: SDK init code, `OTEL_*` variables in deployment config, Collector YAML, `prometheus.yml`, rule files, Grafana provisioning directory. Follow the conventions already in place (naming, labels, directories).
3. Start from user journeys and the four golden signals (latency, traffic, errors, saturation); pick SLIs before adding dashboards.
4. Instrument: prefer zero-code agents for the framework layer, then add manual spans and metrics for business operations. Configure through `OTEL_*` variables so the same build runs in every environment.
5. Route through a Collector (agent or gateway) rather than exporting straight to a vendor from every service, so sampling, redaction, retries and credentials live in one place.
6. Validate the Collector config (`otelcol validate --config=...`, or the distribution's `validate` subcommand), run with the `debug` exporter in a test pipeline, and check Prometheus targets and rule files with `promtool`.
7. Check cardinality before shipping: list labels per metric and confirm none carries user IDs, URLs with IDs, emails or free text.
8. Add alerts on symptoms with runbook links, test them with `promtool test rules`, and keep rules and dashboards in version control.
9. Report what was run and which behaviours could not be verified locally (for example backend-specific limits).

## 4. Decision Rules

- If traces must survive restarts and bursts, use the Collector as an agent or gateway with `memory_limiter` plus `batch` and a persistent or sized `sending_queue`; do not rely on SDK-only export.
- If cost control is needed and every error and slow trace must be kept, use tail sampling in the Collector; if cost control is all that is needed, use `parentbased_traceidratio` in the SDK because it is cheaper and stateless.
- If services call each other, keep the parent-based sampler everywhere so the decision made at the root is honoured; a service that samples independently breaks traces.
- If tail sampling is used with more than one Collector replica, put a `loadbalancing` exporter tier (routing key `traceID`) in front; otherwise decisions are made on partial traces.
- If request counts and latency percentiles are needed on sampled traces, derive RED metrics with the `spanmetrics` connector before the sampler, or instrument metrics directly; counting after sampling undercounts.
- If a value has unbounded distinct values (user ID, session ID, email, full URL, request ID, trace ID), it is a log field or span attribute, never a metric label. Link metrics to traces with exemplars.
- If a latency SLI needs aggregation across instances, use histograms; summaries cannot be aggregated. Use native histograms when the backend supports them and keep classic histograms until all consumers are migrated.
- If a counter must be graphed per second, use `rate()`; use `irate()` only for fast-moving graphs with short ranges, and never in alerts or recording rules because it is noisy and misses short spikes between samples.
- If an alert is about a cause (CPU high, pod restarted), make it a dashboard or ticket; page only when users are or soon will be affected (symptom-based), using SLO burn rates.
- If an exporter or Prometheus endpoint is reachable beyond the host or cluster network, require TLS and authentication; otherwise bind to localhost or an internal interface.

## 5. Coding Standards

- Name the service with `OTEL_SERVICE_NAME` (or the `service.name` resource attribute) and set `service.version` and `deployment.environment.name` consistently across signals; a missing name yields `unknown_service`.
- Span names are low-cardinality operation names (`GET /orders/{id}`, `charge_card`); put identifiers in attributes, not names.
- Set span status to `ERROR` only for failures; leave `OK` unset unless the application explicitly confirms success. Record exceptions on the span with `record_exception`.
- Use semantic convention attribute names (`http.request.method`, `http.response.status_code`, `http.route`, `server.address`, `url.path`) instead of inventing synonyms. Stable HTTP conventions replaced older names such as `http.method`; during migration `OTEL_SEMCONV_STABILITY_OPT_IN` (`http` or `http/dup`) controls which names are emitted in instrumentations that support it.
- Prometheus metric names: `snake_case`, a namespace prefix, base units in the name (`_seconds`, `_bytes`, `_ratio`), counters end in `_total`, no label name inside the metric name, one unit per metric. A gauge that is a single labelled info record is named `<thing>_info` with value 1.
- Label names are lowercase `snake_case`; a given label means the same thing in every metric (`job`, `instance`, `service`, `route`, `status_code`).
- Alert names are CamelCase and describe the symptom (`CheckoutErrorBudgetBurn`); every alert has `severity` and `runbook_url` plus a human `summary`.
- Log in JSON with stable keys: `timestamp`, `level`, `message`, `service.name`, `trace_id`, `span_id`, plus `error.type` and `error.message` for failures. One event per line, to stdout.
- Keep YAML for Collector and Prometheus free of secrets; reference them as `${env:NAME}` (Collector) or files (Prometheus `password_file`, `authorization.credentials_file`).

## 6. Project Structure

```text
observability/
├── otel/
│   ├── collector-agent.yaml        # per-node or sidecar: receive, limit, batch, forward
│   ├── collector-gateway.yaml      # central: redact, sample, route to backends
│   └── tls/                        # certificate paths only; keys come from a secret store
├── prometheus/
│   ├── prometheus.yml              # scrape_configs, rule_files, remote_write
│   ├── rules/
│   │   ├── recording.yml           # job:metric:rate5m style recording rules
│   │   └── slo-checkout.yml        # burn-rate alerts per SLO
│   └── tests/
│       └── slo-checkout.test.yml   # promtool test rules
├── alertmanager/alertmanager.yml   # routes, receivers, inhibition
├── grafana/
│   └── provisioning/
│       ├── datasources/            # Prometheus, Tempo/Jaeger, Loki with trace links
│       ├── dashboards/             # provider file plus dashboard JSON
│       └── alerting/               # only if alerts live in Grafana
└── runbooks/                       # one page per alert, linked from runbook_url
```

## 7. Design Patterns

- **Agent plus gateway Collectors**: agents next to workloads do cheap work (resource detection, memory limit, batching); a gateway tier does expensive or stateful work (redaction, tail sampling, fan-out). Cost: two layers to operate; benefit: SDKs only know one local endpoint.
- **Two-tier tail sampling**: tier 1 receives from agents and uses `loadbalancing` with `routing_key: traceID`; tier 2 runs `tail_sampling`. Cost: added latency of `decision_wait` and memory proportional to `num_traces`.
- **Spanmetrics before sampling**: fan the traces pipeline out to the `spanmetrics` connector and the sampler so RED metrics reflect all traffic. Cost: extra processing on unsampled data.
- **Recording rules for dashboards and SLOs**: precompute `sum by (job) (rate(...[5m]))` once; alerts and panels read the cheap series. Name them `level:metric:operations`.
- **Multi-window multi-burn-rate alerts**: a long window shows sustained burn and a short window shows it is still happening. Details and numbers in [references/slo-alerting.md](references/slo-alerting.md).
- **Exemplars**: attach a trace ID to a histogram observation so a latency spike on a panel links to a representative trace without adding a label.
- **Dashboards as code**: provision data sources and dashboards from files or Git Sync, `allowUiUpdates: false`, review changes through pull requests. Cost: edits in the UI must be exported back to the repository.
- **Logs correlated to traces**: inject `trace_id` and `span_id` into every log line produced inside a span, and configure the log data source to turn that field into a trace link.
- **Collector config layering**: pass several `--config` files (base plus environment overlay) instead of copying the whole file per environment.

## 8. Best Practices

- Export from SDKs to a local Collector endpoint and let the Collector hold backend credentials; rotating a token then touches one place.
- Use the batch span processor in SDKs (the default in most SDKs) and call the provider's shutdown or force-flush on exit, otherwise the last spans of short-lived jobs are lost.
- Cover the entry points first (HTTP, gRPC, queue consumers), then outbound calls (database, cache, HTTP), then business operations; avoid spans around tiny in-memory functions.
- Propagate context across async boundaries: inject `traceparent` into message headers, and use span links when a consumer processes a batch from many producers.
- Make dashboards answer a question: one row per golden signal, a variable for `environment` and `service`, units set on every panel, and a link to the runbook and the logs view.
- Alert on ratios and burn rates, not raw counts, so thresholds survive traffic changes. Use `for:` to absorb blips and `absent()` or a heartbeat alert to detect a silent pipeline.
- Give every metric a `# HELP` text and a unit; reviewers can then judge it without reading the code.
- Set scrape limits (`sample_limit`, `label_limit`, `label_value_length_limit`) per job so one misbehaving target cannot flood the server.
- Prefer pull for service metrics (Prometheus scrapes `/metrics`, and an `up` series shows target health); use push (OTLP, Pushgateway) only for short-lived batch jobs or networks where scraping is impossible.
- Write the runbook when writing the alert: what the symptom means, how to confirm, immediate mitigation, who to escalate to, and how to verify recovery.

## 9. Performance

- Measure telemetry overhead before tuning: Collector CPU and memory, `otelcol_exporter_enqueue_failed_*` and `otelcol_exporter_send_failed_*` counters, queue size versus capacity, Prometheus `prometheus_tsdb_head_series` and scrape duration.
- Reduce volume at the cheapest point: drop health-check and static-asset spans in the SDK or Collector `filter` processor, set `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` for large payload attributes, and sample traces.
- Keep PromQL cheap: select with specific label matchers, aggregate with `sum by (...)` early, avoid regex on `__name__`, and use recording rules for expressions used by many panels or alerts.
- Range selectors need at least two samples inside the window: use at least four scrape intervals for `rate()` (for a 15 s interval, `[1m]` is the practical minimum). In Grafana use `$__rate_interval`.
- Histogram cost scales with bucket count times label combinations; choose bucket boundaries around SLO thresholds, or use native histograms to get high resolution with one series per label set.
- Size `memory_limiter` below the container memory limit (for example `limit_percentage: 80`) so it triggers before the OOM killer; do not put it behind other processors.
- Capacity planning, load tests and tuning of the monitored application itself are covered by scalability-expert.

## 10. Security

- Secure OTLP endpoints: TLS on receivers and exporters (Collector components default to encrypted connections; do not set `insecure: true` outside local development), mTLS with `client_ca_file` for service-to-Collector traffic, or an authenticator extension (basic auth, bearer token, OIDC) attached to the receiver through `auth.authenticator`. Check each extension's README for option names.
- Bind receivers and extensions deliberately. The OTLP receiver defaults to `localhost:4317` and `localhost:4318`; use `0.0.0.0` only behind TLS plus authentication or a network policy. Keep `health_check`, `pprof` and `zpages` extensions on localhost or an admin network.
- Redact in the Collector as a safety net: the `redaction` processor (`blocked_key_patterns`, `blocked_values`, optional `hash_function`; stability beta for traces and alpha for logs and metrics) and the `transform` processor with OTTL `delete_key` and `replace_pattern` for query strings, tokens and payload fields. `allowed_keys` is fail-closed: any key not listed is removed.
- Do not capture sensitive data in the first place: no passwords, tokens, API keys, session cookies, card numbers, health data or full request bodies in span attributes, log fields, baggage or metric labels. HTTP header capture is opt-in per instrumentation; never include `authorization`, `cookie` or `set-cookie`.
- Treat SQL statements carefully: use the instrumentation's sanitised statement text, not the statement with bound parameter values.
- Baggage is sent in HTTP headers to every downstream service, including third parties. Put only non-sensitive routing hints in it and drop it at trust boundaries.
- Do not expose `/metrics` publicly. Bind to an internal interface, restrict by network policy or firewall, or serve it with TLS and authentication (`--web.config.file`, or a reverse proxy). Metrics reveal route names, versions and internal topology.
- Leave `--web.enable-admin-api`, `--web.enable-lifecycle`, `--web.enable-remote-write-receiver` and `--web.enable-otlp-receiver` off unless the port is protected; each lets a caller write or control the server.
- Keep credentials out of config files: Collector `${env:NAME}` expansion, Prometheus `*_file` options, Grafana `secureJsonData` with environment expansion, and a secret manager for the values.
- Grafana: no anonymous admin, use service accounts for automation, give datasources least-privilege read-only credentials, and keep dashboards from embedding secrets in queries or links.
- Never disable TLS verification on exporters (`insecure_skip_verify`); fix the CA bundle instead.

## 11. Testing

- Collector: validate the file (`otelcol validate --config=file.yaml`), then run it with the `debug` exporter and send a test span with an OTLP client to prove the pipeline end to end. Assert that redaction removed a seeded fake secret.
- Prometheus: `promtool check config prometheus.yml`, `promtool check rules rules/*.yml`, and `promtool test rules tests/*.yml` with synthetic series for each alert (fires when it should, stays quiet when it should not, `for:` honoured).
- Alertmanager: `amtool check-config alertmanager.yml`, and `amtool config routes test` to confirm a label set reaches the intended receiver.
- Instrumentation: in unit tests use the SDK's in-memory span exporter or test harness to assert span names, attributes, status and parent-child links; assert that logs inside a span carry its `trace_id`.
- Cardinality test: scrape the service after a load of varied requests and assert the series count per metric stays within a stated bound.
- Failure paths: stop the Collector and confirm the application stays healthy and logs a bounded number of export errors; saturate the queue and confirm the drop counters increment.
- Dashboards: provision into a throwaway Grafana in CI and confirm they load without errors; check variables resolve against a seeded Prometheus.

## 12. Review Checklist

- [ ] Versions and options match the "Verified against" line; unstable components (alpha, development) are noted.
- [ ] No secrets, tokens, PII or full payloads in telemetry, config files, dashboards or examples.
- [ ] OTLP, Prometheus and Grafana endpoints use TLS and authentication where reachable beyond localhost; `/metrics` is not public.
- [ ] No unbounded label values (IDs, URLs, emails) in metrics; exemplars or logs carry the detail.
- [ ] Metric names have base units and `_total` on counters; histogram buckets cover SLO thresholds.
- [ ] Collector pipeline order is `memory_limiter` first, `batch` last; sampler placed after redaction.
- [ ] Sampling is parent-based in SDKs; tail sampling has a trace-ID load-balancing tier when replicated.
- [ ] Logs are JSON with `trace_id` and `span_id`, no secrets, levels used consistently.
- [ ] Alerts are symptom-based, use burn rates with two windows, have `severity`, `summary` and `runbook_url`, and have `promtool` tests.
- [ ] Dashboards and rules are in version control and provisioned, not hand-edited in production.

## 13. Production Notes

- Roll out in order: Collector first, then SDK or agent config with a low sampling rate, then raise it; keep a kill switch (`OTEL_SDK_DISABLED=true` or `OTEL_TRACES_SAMPLER=always_off`).
- Monitor the pipeline itself: Collector internal metrics (prefix `otelcol_`, check the exact names on your version's metrics endpoint), `up` for every Prometheus target, rule evaluation failures, Alertmanager notification failures, and a dead-man's-switch alert that always fires and pages when it stops arriving.
- Upgrading the Collector: component configs and metric names change between 0.x releases; read the changelog, test in staging, and keep the contrib and core versions aligned.
- Upgrading Prometheus 2.x to 3.x: left-open ranges, `le="1.0"` label normalisation, stricter scrape Content-Type and UTF-8 names can break queries, alerts and scrapes; review the migration guide first.
- Retention: Prometheus retention flags (`--storage.tsdb.retention.*`) are marked deprecated in favour of the configuration-file setting; check the current docs for the exact key. Use remote write to long-term storage for history and for HA pairs.
- Dashboards and alert rule APIs in Grafana 13 are versioned (`v1beta1` for alert resources); expect schema changes and pin provisioning formats to what the deployed version accepts.
- Run blameless reviews on every page: if an alert did not need action, delete or downgrade it; if an incident was found by users first, add the missing symptom alert.

## 14. Examples

Zero-code instrumentation of a Python service, configured only through environment variables, with the Collector on the same host:

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install          # installs instrumentations for detected libraries

export OTEL_SERVICE_NAME=checkout
export OTEL_RESOURCE_ATTRIBUTES=service.version=1.8.2,deployment.environment.name=staging
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
opentelemetry-instrument python app.py
```

Manual span plus JSON log line carrying `trace_id` and `span_id` (Python, standard library logging):

```python
import json, logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("checkout")
log = logging.getLogger("checkout")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        doc = {"level": record.levelname, "message": record.getMessage(), "service.name": "checkout"}
        if ctx.is_valid:
            doc["trace_id"] = format(ctx.trace_id, "032x")
            doc["span_id"] = format(ctx.span_id, "016x")
        return json.dumps(doc)

def charge(order_id: str, amount_cents: int) -> None:
    with tracer.start_as_current_span("charge_card") as span:
        span.set_attribute("order.amount_cents", amount_cents)   # no card data, no user email
        try:
            ...  # call the payment provider
            log.info("charge accepted")
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            log.error("charge failed")   # log line shares the span's trace_id
            raise
```

Multi-window multi-burn-rate alerts for a 99.9% availability SLO over 30 days (error ratio recorded per window; the budget is 0.001, so burn rate 14.4 means an error ratio above 0.0144):

```yaml
groups:
  - name: slo-checkout
    rules:
      - alert: CheckoutErrorBudgetFastBurn
        expr: |
          job:http_errors:ratio_rate1h{job="checkout"} > (14.4 * 0.001)
          and
          job:http_errors:ratio_rate5m{job="checkout"} > (14.4 * 0.001)
        labels: {severity: page}
        annotations:
          summary: "Checkout burns 2% of its 30-day error budget per hour"
          runbook_url: https://runbooks.example.com/checkout/error-budget-burn
      - alert: CheckoutErrorBudgetSlowBurn
        expr: |
          job:http_errors:ratio_rate6h{job="checkout"} > (6 * 0.001)
          and
          job:http_errors:ratio_rate30m{job="checkout"} > (6 * 0.001)
        labels: {severity: page}
        annotations:
          summary: "Checkout burns 5% of its 30-day error budget per 6 hours"
          runbook_url: https://runbooks.example.com/checkout/error-budget-burn
```

The full Collector gateway configuration, recording rules and a `promtool` test are in [references/collector.md](references/collector.md) and [references/slo-alerting.md](references/slo-alerting.md).

## 15. Common Mistakes

- **User ID or URL as a metric label**: the series count grows with traffic, Prometheus memory and query time explode. Use a route template as the label, put identifiers in logs or span attributes, and add exemplars for trace links.
- **`batch` before `memory_limiter`, or no `memory_limiter`**: the Collector is OOM-killed under a burst and loses data. Put `memory_limiter` first and `batch` last.
- **Tail sampling on several replicas without trace-ID routing**: each replica sees part of a trace and samples inconsistently. Add the `loadbalancing` exporter tier.
- **Independent sampling in every service**: traces arrive with missing spans. Use parent-based samplers (`parentbased_traceidratio`).
- **`rate()` on a gauge or `rate()` of a sum**: wrong values after resets. Apply `rate()` to each counter series first, then `sum by (...)`.
- **`histogram_quantile` without `by (le)`**: the buckets are mixed across labels and the result is meaningless. Use `histogram_quantile(0.95, sum by (le) (rate(x_bucket[5m])))` for classic histograms, and drop the `le` for native ones. Never average percentiles across instances.
- **`irate()` in alerts**: a single noisy pair of samples decides the alert. Use `rate()` over at least four scrape intervals.
- **Cause-based paging (CPU above 80 percent)**: noisy alerts with no user impact. Page on SLO burn rate; keep resource alerts as tickets.
- **Single-window burn-rate alert**: pages long after recovery or misses slow burns. Pair a long and a short window.
- **Alert without a runbook or an owner**: responders lose minutes finding context. Require `runbook_url` and routing by team label.
- **Secrets or PII in span attributes, logs or baggage**: leaks to the observability vendor and downstream services. Redact at source and again in the Collector.
- **Public `/metrics`, open OTLP port on `0.0.0.0` without TLS or auth**: anyone can read topology or inject telemetry. Bind internally and authenticate.
- **Forgetting shutdown in short-lived jobs**: the final batch of spans is never sent. Call the provider's `shutdown` or `force_flush`.
- **Missing `service.name`**: telemetry appears as `unknown_service`, breaking dashboards and sampling policies. Set `OTEL_SERVICE_NAME` everywhere.
- **Trusting stale versions**: Collector component names, metric names and options change between 0.x releases. Check the changelog and the component README for the deployed version.

## 16. References

- [references/opentelemetry.md](references/opentelemetry.md): SDK setup per language, environment variables, zero-code instrumentation, propagation, semantic conventions and span design.
- [references/collector.md](references/collector.md): Collector gateway and agent configs, processor order, sampling tiers, redaction and TLS or auth for OTLP.
- [references/promql.md](references/promql.md): metric types and naming, PromQL functions and pitfalls, native histograms, recording rules, remote write, cardinality control.
- [references/slo-alerting.md](references/slo-alerting.md): SLIs, error budgets, multi-window burn-rate rules, Alertmanager routing, runbook template, Grafana provisioning and alerting as code.
- OpenTelemetry docs: https://opentelemetry.io/docs/ (Collector: https://opentelemetry.io/docs/collector/; specification: https://github.com/open-telemetry/opentelemetry-specification)
- Collector releases and component READMEs: https://github.com/open-telemetry/opentelemetry-collector-releases and https://github.com/open-telemetry/opentelemetry-collector-contrib
- Semantic conventions: https://github.com/open-telemetry/semantic-conventions
- Prometheus docs: https://prometheus.io/docs/ (Prometheus 3.0 migration guide: https://prometheus.io/docs/prometheus/latest/migration/)
- Grafana docs: https://grafana.com/docs/grafana/latest/ (provisioning, Git Sync, alerting)
- Google SRE Workbook, alerting on SLOs: https://sre.google/workbook/alerting-on-slos/
