# Prometheus and PromQL

Metric types and naming, scrape and remote write configuration, PromQL functions and their pitfalls, histograms (classic and native), recording rules and cardinality control. Verified against Prometheus 3.15.1, the native histograms specification (stable since v3.8.0) and the Remote Write 2.0 specification 2.0-rc.6 (experimental) (2026-10). Option names marked "check the current docs" were not verified for this version.

## Contents

1. [Metric types and naming](#1-metric-types-and-naming)
2. [Scrape and rule configuration](#2-scrape-and-rule-configuration)
3. [PromQL essentials](#3-promql-essentials)
4. [Histograms](#4-histograms)
5. [Pitfalls](#5-pitfalls)
6. [Recording rules](#6-recording-rules)
7. [Remote write and OTLP ingestion](#7-remote-write-and-otlp-ingestion)
8. [Cardinality control](#8-cardinality-control)
9. [Upgrading to Prometheus 3](#9-upgrading-to-prometheus-3)

## 1. Metric types and naming

| Type | Use | Query with |
|---|---|---|
| Counter | Monotonic count of events (requests, errors, bytes); resets to 0 on restart | `rate()`, `increase()`, `irate()` |
| Gauge | Value that goes up and down (in-flight requests, queue depth, temperature) | Plain selector, `avg_over_time`, `delta`, `deriv`, `predict_linear` |
| Histogram | Distribution of observations in buckets; classic form exposes `_bucket{le}`, `_sum`, `_count`; native form is a single series type | `histogram_quantile`, `histogram_fraction`, `rate()` on buckets |
| Summary | Client-side quantiles; cannot be aggregated across instances | Avoid for new metrics; use histograms |

Naming rules:

- `snake_case`, a namespace prefix (`checkout_`), the unit as a suffix in base units: `_seconds`, `_bytes`, `_ratio` (0 to 1) or `_percent` only when unavoidable.
- Counters end in `_total`. A metric that records a timestamp ends in `_timestamp_seconds`. Metadata-like series use `_info` with value 1 (`app_info{version="2.4.0"}`).
- A metric name describes what is measured, not the labels. The sum or average of a metric should be meaningful across its label values; if not, split the metric.
- Labels hold bounded dimensions: `method`, `route` (template, never the raw path), `status_code` or a class (`2xx`), `region`. A label such as `user_id`, `email`, `session_id`, `trace_id`, `url` or `query` makes one series per value and must not be used.
- Pre-initialise counters for known label combinations to 0 at start so `rate()` and `absent()` behave on the first scrape.
- OpenTelemetry metric `http.server.request.duration` (unit `s`) appears in Prometheus as `http_server_request_duration_seconds` with attributes as labels (`http_response_status_code`, `http_route`).

## 2. Scrape and rule configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels: {cluster: prod-eu1}

rule_files:
  - rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager.internal:9093"]

scrape_configs:
  - job_name: checkout
    scheme: https
    metrics_path: /metrics
    tls_config:
      ca_file: /etc/prometheus/tls/ca.crt
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/secrets/checkout.token
    sample_limit: 50000
    label_limit: 30
    label_value_length_limit: 200
    scrape_native_histograms: true        # per job or global; needs a target that exposes them
    static_configs:
      - targets: ["checkout-1.internal:9100", "checkout-2.internal:9100"]
    metric_relabel_configs:
      - action: labeldrop
        regex: user_id|request_id
```

- Pull model: Prometheus scrapes targets, so a failed scrape shows as `up == 0`. Prefer it for long-running services. Short-lived batch jobs push to a Pushgateway or send OTLP.
- Targets come from static config, file-based or DNS discovery, or platform service discovery (Kubernetes discovery configs belong with kubernetes-expert).
- `relabel_configs` act on targets before scraping; `metric_relabel_configs` act on scraped series and are the place to drop or rewrite labels that should not be stored.
- Keep secrets in files referenced by `credentials_file` or `password_file`, not in the YAML.
- Validate: `promtool check config prometheus.yml`, `promtool check rules rules/*.yml`.
- Retention flags `--storage.tsdb.retention.time` and `.size` are marked deprecated in favour of the config-file setting: check the current docs for the key name.
- Expose `/metrics` on an internal interface or behind authentication; never on the public internet.

## 3. PromQL essentials

```promql
# Request rate per route (counter, per second, 5m window)
sum by (route) (rate(http_server_request_duration_seconds_count[5m]))

# Error ratio for a service
  sum(rate(http_server_request_duration_seconds_count{job="checkout", http_response_status_code=~"5.."}[5m]))
/
  sum(rate(http_server_request_duration_seconds_count{job="checkout"}[5m]))

# Requests in the last hour (extrapolated, may be fractional)
sum(increase(http_server_request_duration_seconds_count{job="checkout"}[1h]))

# Join an info metric to add a label
rate(http_requests_total[5m]) * on (instance) group_left (version) app_info

# Predict a disk filling within 4 hours
predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}[6h], 4 * 3600) < 0

# Target missing entirely
absent(up{job="checkout"})
```

- `rate(v[r])`: per-second average increase over the range, handles counter resets, extrapolates to the window edges. Use for alerts, recording rules and dashboards.
- `irate(v[r])`: uses only the last two samples in the range: instantaneous and spiky. Use for zoomed-in graphs of fast counters only.
- `increase(v[r])`: `rate(v[r]) * seconds in r`; extrapolated, so integer counters can yield non-integers.
- `delta`, `deriv`, `predict_linear` are for gauges. `rate()` on a gauge is wrong.
- `_over_time` functions (`avg_over_time`, `max_over_time`, `quantile_over_time`) aggregate one series across time; `sum`, `avg`, `max`, `topk`, `count` aggregate across series. Use `by (...)` to keep labels or `without (...)` to drop labels.
- Binary operators match series by identical labels. Use `on (...)` or `ignoring (...)` to choose labels, and `group_left` or `group_right` for many-to-one joins. `and`, `or`, `unless` are set operators; comparison with `bool` returns 0 or 1 instead of filtering.
- Range for `rate()`: at least four times the scrape interval (so `[1m]` for 15 s scrapes, `[5m]` as a safe default). In Grafana panels use `$__rate_interval`.
- Subqueries `expr[30m:1m]` evaluate an instant expression over a range; they are costly: prefer recording rules.
- Staleness: a series disappears from instant queries when a target stops exposing it or the target goes away; the lookback for instant vectors is 5 minutes by default.

## 4. Histograms

Classic histogram quantile (buckets must be aggregated with `le` kept):

```promql
histogram_quantile(0.95,
  sum by (le, route) (rate(http_server_request_duration_seconds_bucket[5m])))
```

Native histogram quantile (no `le`, no `_bucket` suffix; one series carries all buckets):

```promql
histogram_quantile(0.95,
  sum by (route) (rate(http_server_request_duration_seconds[5m])))
```

Share of requests faster than 300 ms:

```promql
# classic: needs a bucket boundary exactly at 0.3
sum(rate(http_server_request_duration_seconds_bucket{le="0.3"}[5m]))
/
sum(rate(http_server_request_duration_seconds_count[5m]))

# native: any threshold, interpolated
histogram_fraction(0, 0.3, sum(rate(http_server_request_duration_seconds[5m])))
```

- Quantiles are estimated by interpolating inside a bucket, so the error depends on bucket width. Place classic bucket boundaries at SLO thresholds (for example 0.1, 0.3, 1, 3 seconds).
- Never average or sum percentiles across instances; aggregate buckets first, then take the quantile.
- Native histograms are stable since Prometheus v3.8.0. Enable scraping with `scrape_native_histograms: true` (global or per scrape config); remote write needs `send_native_histograms` on the `remote_write` entry. The `native-histograms` feature flag has no effect from v3.9. The specification says both options default to true in v4.
- The client library and exposition format must support native histograms; Prometheus negotiates the scrape protocol (`scrape_protocols`), so check client library docs and the receiving backend before switching. Keep classic histograms until all dashboards, rules and long-term storage handle the native form.
- Exemplars attach a trace ID to an observation. Prometheus needs exemplar storage enabled (a feature flag; check the current feature flags page), and the exposition format must carry exemplars. Configure the Grafana Prometheus data source with an exemplar link to the trace data source.
- Native histograms with custom buckets (NHCB) convert classic histograms on ingest in newer versions; check the docs for `convert_classic_histograms_to_nhcb` before relying on it.

## 5. Pitfalls

- `rate()` of a `sum()` is invalid after restarts: apply `rate()` to each series, then aggregate: `sum(rate(x_total[5m]))`.
- `histogram_quantile` without `le` in the `by` clause returns nonsense for classic histograms.
- Comparing to a threshold on low traffic: an error ratio of 1 failed request out of 2 is 50 percent. Pair ratio alerts with a minimum request rate or use burn rates over longer windows.
- Division by zero returns NaN or no data when the denominator has no samples. Guard with `and on() (denominator > 0)` or handle the no-traffic case explicitly.
- Missing data: `rate(x[5m]) > 0` silently returns nothing when the metric disappears. Use `absent()` or `absent_over_time()` for liveness, and a "dead man's switch" alert for the pipeline.
- `or vector(0)` makes a missing series appear as 0 but also hides outages; use it only for sums where zero is the true value.
- Alerts flap without `for:`; alerts stay on too briefly without `keep_firing_for:` when a signal oscillates around the threshold.
- Regex matchers on `__name__` and unanchored label regexes scan many series; Prometheus regex matchers are fully anchored, so `=~"5.."` already means the whole value.
- Different scrape intervals across jobs make `rate()` windows mean different things; keep a consistent interval or size windows per job.
- Counter resets are handled by `rate()`, but gauges that behave like counters (an exporter that sums and resets) are not.
- `increase()` over a window shorter than the scrape interval returns no data.
- High-cardinality `by` clauses in dashboards (`by (instance, route, status_code)` across hundreds of targets) produce slow panels: aggregate to what the panel needs.
- In Prometheus 3, range selectors exclude samples exactly at the left boundary; a subquery like `foo[1m:1m]` can return one point, so widen it (`[2m:1m]`).

## 6. Recording rules

```yaml
groups:
  - name: http-recording
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_server_request_duration_seconds_count[5m]))
      - record: job:http_errors:ratio_rate5m
        expr: |
          sum by (job) (rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
          /
          sum by (job) (rate(http_server_request_duration_seconds_count[5m]))
```

- Naming convention: `level:metric:operations`, where `level` is the aggregation labels, `metric` the base metric without `_total`, and `operations` the functions applied, newest first.
- Record when an expression is expensive, used by several rules or panels, or is the basis of an SLO. Do not record every expression: each rule is a new series to store.
- Record one series per window for SLO math (`5m`, `30m`, `1h`, `6h`, `3d`); see [slo-alerting.md](slo-alerting.md).
- Test with `promtool test rules`: feed `input_series` with `values: "0+10x30"` style expansions and assert `promql_expr_test` results and `alert_rule_test` states.

## 7. Remote write and OTLP ingestion

```yaml
remote_write:
  - url: https://metrics-store.example.internal/api/v1/push
    basic_auth:
      username: prometheus
      password_file: /etc/prometheus/secrets/remote-write.password
    tls_config:
      ca_file: /etc/prometheus/tls/ca.crt
    send_native_histograms: true
    write_relabel_configs:
      - source_labels: [__name__]
        regex: "go_.*|process_.*"
        action: drop
```

- Remote write streams samples to long-term or multi-tenant storage and is the transport for HA pairs and agent-mode Prometheus (`--agent`). It is not a backup of rules or of exemplars.
- Remote Write 2.0 (spec `2.0-rc.6`, experimental) adds native histograms, metadata, start timestamps and a string symbol table to cut payload size. Use it only when sender and receiver both document support.
- Prometheus can receive OTLP with `--web.enable-otlp-receiver` (off by default). Enable it only on a protected port; the OTLP-to-Prometheus name translation (suffixes, UTF-8 handling) is configurable under the `otlp:` section of the config: check the current docs for the translation strategy options before enabling.
- From the Collector, either expose a Prometheus scrape endpoint (`prometheus` exporter) or push with `prometheusremotewrite`; scraping keeps the `up` health signal.

## 8. Cardinality control

- Series count is the product of distinct label value sets for each metric. One unbounded label multiplies it without limit.
- Find offenders: Prometheus UI status page (TSDB status), `GET /api/v1/status/tsdb`, `promtool tsdb analyze <data-dir>`, and `prometheus_tsdb_head_series` over time.
- Prevent: scrape limits (`sample_limit`, `label_limit`, `label_value_length_limit`), `metric_relabel_configs` with `labeldrop` or `drop`, and code review of every new label.
- Replace identifiers with: a route template instead of a raw path, a status class instead of a free-text reason, an enum instead of a message. Move per-user and per-request detail to logs and span attributes, and link a metric to a trace with exemplars.
- In OpenTelemetry SDKs, use Views to remove attributes and set bounded histogram buckets; check the SDK documentation for its cardinality limit behaviour.

## 9. Upgrading to Prometheus 3

- Range selectors and lookback windows are left-open (samples exactly at the left boundary are excluded).
- `le` and `quantile` label values are normalised to float form (`le="1"` becomes `le="1.0"`): update rules, dashboards and alerts that match literal values, or rewrite with `metric_relabel_configs`.
- Scrapes fail when the response Content-Type is missing or unrecognised; fix the endpoint or set `fallback_scrape_protocol`.
- UTF-8 metric and label names are accepted; `metric_name_validation_scheme: legacy` restores the old validation.
- `holt_winters` is now `double_exponential_smoothing` and needs `--enable-feature=promql-experimental-functions`.
- Agent mode uses the `--agent` flag; `remote-write-receiver` became `--web.enable-remote-write-receiver`.
- Alertmanager API v1 is no longer supported (Alertmanager 0.16 or later, `api_version: v2`).
- Downgrade is limited (TSDB format): back up before upgrading and read the migration guide.
