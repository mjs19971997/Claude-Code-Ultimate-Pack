# SLOs, Alerting and Grafana as Code

Defining SLIs and SLOs, error budgets, multi-window multi-burn-rate alerts in Prometheus, Alertmanager routing, runbooks, and Grafana provisioning and alerting as code. Verified against Prometheus 3.15.1, Grafana 13.3.0 release notes and the Google SRE Workbook chapter on alerting on SLOs (2026-10). Grafana option names outside the examples: check the current docs for the deployed version.

## Contents

1. [SLIs and SLOs](#1-slis-and-slos)
2. [Error budgets and burn rates](#2-error-budgets-and-burn-rates)
3. [Recording rules per window](#3-recording-rules-per-window)
4. [Burn-rate alert rules](#4-burn-rate-alert-rules)
5. [Testing alert rules](#5-testing-alert-rules)
6. [Alertmanager routing](#6-alertmanager-routing)
7. [Runbooks and alert quality](#7-runbooks-and-alert-quality)
8. [Grafana as code](#8-grafana-as-code)

## 1. SLIs and SLOs

- An SLI is a ratio of good events to valid events over a window, measured where users experience the service (load balancer or server edge, not a single host).
- An SLO is a target for the SLI over a rolling window, commonly 28 or 30 days. The remainder is the error budget.
- Typical SLIs by service type:
  - Request-driven: availability (non-5xx responses over all valid requests) and latency (requests faster than a threshold over all requests).
  - Pipelines and queues: freshness (data newer than N minutes) and throughput or correctness.
- Decide and document which events are valid: client errors such as 404 usually count as successes; health checks and probes may be excluded.
- Allowed downtime over 30 days (43,200 minutes): 99 percent is 432 minutes (7.2 hours), 99.9 percent is 43.2 minutes, 99.95 percent is 21.6 minutes, 99.99 percent is 4.32 minutes.
- Availability SLI from OpenTelemetry HTTP server metrics (Prometheus names):

```promql
1 - (
  sum(rate(http_server_request_duration_seconds_count{job="checkout", http_response_status_code=~"5.."}[30d]))
  /
  sum(rate(http_server_request_duration_seconds_count{job="checkout"}[30d]))
)
```

- Latency SLI (classic histogram, bucket at the threshold must exist):

```promql
sum(rate(http_server_request_duration_seconds_bucket{job="checkout", le="0.3"}[5m]))
/
sum(rate(http_server_request_duration_seconds_count{job="checkout"}[5m]))
```

For long windows such as 30 days, query a recording rule instead of a raw 30-day range; raw long ranges are slow and costly.

## 2. Error budgets and burn rates

- Error budget = 1 - SLO (0.001 for 99.9 percent).
- Burn rate = observed error ratio / error budget ratio. Burn rate 1 spends exactly the budget over the SLO window; 14.4 spends it in about two days of a 30-day window.
- Budget consumed by a burn over a window = burn rate x window / SLO window. In a 30-day (720 hour) window, 14.4 x 1 h = 2 percent, 6 x 6 h = 5 percent, 1 x 72 h = 10 percent.
- Recommended starting set for a 30-day SLO (from the Google SRE Workbook):

| Severity | Long window | Short window | Burn rate | Budget consumed | Threshold at 99.9 percent |
|---|---|---|---|---|---|
| Page | 1 h | 5 min | 14.4 | 2 percent | error ratio > 0.0144 |
| Page | 6 h | 30 min | 6 | 5 percent | error ratio > 0.006 |
| Ticket | 3 d | 6 h | 1 | 10 percent | error ratio > 0.001 |

- The short window is about one twelfth of the long window. The alert fires only when both windows exceed the threshold: the long window proves the burn is significant, the short window proves it is still happening, so the alert resets soon after recovery.
- Low-traffic services produce a noisy error ratio; a few failures can exceed 14.4x. Use longer windows, a minimum request rate guard, or synthetic traffic.

## 3. Recording rules per window

One rule per window keeps alert expressions short and cheap. Rule names follow `level:metric:operations`.

```yaml
groups:
  - name: slo-checkout-recording
    rules:
      - record: job:http_errors:ratio_rate5m
        expr: |
          sum by (job) (rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
          /
          sum by (job) (rate(http_server_request_duration_seconds_count[5m]))
      - record: job:http_errors:ratio_rate1h
        expr: |
          sum by (job) (rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[1h]))
          /
          sum by (job) (rate(http_server_request_duration_seconds_count[1h]))
```

Repeat the rule for the `30m`, `6h` and `3d` windows (same expression, different range). SLO generators such as Sloth or Pyrra can produce these rules from a short SLO spec; check their documentation for the current format.

## 4. Burn-rate alert rules

```yaml
groups:
  - name: slo-checkout-alerts
    rules:
      - alert: CheckoutErrorBudgetFastBurn
        expr: |
          job:http_errors:ratio_rate1h{job="checkout"} > (14.4 * 0.001)
          and
          job:http_errors:ratio_rate5m{job="checkout"} > (14.4 * 0.001)
        labels:
          severity: page
          service: checkout
        annotations:
          summary: "Checkout is burning 2% of its monthly error budget per hour"
          description: "5xx ratio {{ $value | humanizePercentage }} over the last hour."
          runbook_url: https://runbooks.example.com/checkout/error-budget-burn
      - alert: CheckoutErrorBudgetSlowBurn
        expr: |
          job:http_errors:ratio_rate6h{job="checkout"} > (6 * 0.001)
          and
          job:http_errors:ratio_rate30m{job="checkout"} > (6 * 0.001)
        labels:
          severity: page
          service: checkout
        annotations:
          summary: "Checkout is burning 5% of its monthly error budget per 6 hours"
          runbook_url: https://runbooks.example.com/checkout/error-budget-burn
      - alert: CheckoutErrorBudgetSteadyBurn
        expr: |
          job:http_errors:ratio_rate3d{job="checkout"} > 0.001
          and
          job:http_errors:ratio_rate6h{job="checkout"} > 0.001
        labels:
          severity: ticket
          service: checkout
        annotations:
          summary: "Checkout will exhaust its error budget before the window ends"
          runbook_url: https://runbooks.example.com/checkout/error-budget-burn
```

- The `and` of two recording rules works because both have the same `job` label; the result keeps the left-hand labels.
- Multi-window alerts need no `for:`; add a short `for:` (for example 2m) only if the short window flaps.
- Alert on a symptom users feel (errors, latency, freshness). Keep cause-level signals (CPU, memory, pod restarts, disk) on dashboards or as ticket-level alerts, except where a cause reliably leads to an outage that burn-rate alerts would detect too late (for example a disk that will be full within hours: `predict_linear`).
- Add a liveness alert for the monitoring path itself: an always-firing rule routed to a dead-man's-switch receiver, plus `absent()` alerts on key metrics.

## 5. Testing alert rules

```yaml
rule_files:
  - ../rules/slo-checkout-alerts.yml
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'job:http_errors:ratio_rate1h{job="checkout"}'
        values: "0.02+0x20"
      - series: 'job:http_errors:ratio_rate5m{job="checkout"}'
        values: "0.02+0x20"
    alert_rule_test:
      - eval_time: 5m
        alertname: CheckoutErrorBudgetFastBurn
        exp_alerts:
          - exp_labels: {severity: page, service: checkout, job: checkout}
            exp_annotations:
              summary: "Checkout is burning 2% of its monthly error budget per hour"
              description: "5xx ratio 2% over the last hour."
              runbook_url: https://runbooks.example.com/checkout/error-budget-burn
```

Run `promtool test rules tests/*.yml`. Also add a case where the long window is high and the short window is low (alert must not fire) and a case where traffic is zero. Keep recorded-series names in tests identical to the recording rule names.

## 6. Alertmanager routing

```yaml
route:
  receiver: team-default
  group_by: [alertname, service]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers: ['severity="page"']
      receiver: oncall-pager
    - matchers: ['severity="ticket"']
      receiver: team-tickets
inhibit_rules:
  - source_matchers: ['severity="page"']
    target_matchers: ['severity="ticket"']
    equal: [service]
receivers:
  - name: team-default
  - name: oncall-pager
    pagerduty_configs:
      - routing_key_file: /etc/alertmanager/secrets/pagerduty.key
  - name: team-tickets
    webhook_configs:
      - url_file: /etc/alertmanager/secrets/ticket-webhook.url
```

- Group related alerts (`group_by`, `group_wait`), use inhibition so a page suppresses lower-severity noise for the same service, and route by `severity` and a team or `service` label.
- Keep receiver credentials in files (`*_file` options) outside version control. Check the receiver's documentation for the exact option names of the Alertmanager version in use.
- Check with `amtool check-config alertmanager.yml` and `amtool config routes test --config.file=alertmanager.yml severity=page service=checkout`.

## 7. Runbooks and alert quality

An alert deserves a page only when it is actionable, urgent and user-visible. Review each paging alert against the three; fix or downgrade any that fail.

Runbook template (one page per alert, linked from `runbook_url`):

```text
Alert: CheckoutErrorBudgetFastBurn
Meaning: more than 1.44% of checkout requests fail over 1h and 5m; budget gone in ~2 days at this rate.
Impact: customers cannot complete payment.
Check first: dashboard link; recent deploys (rollback if within the last hour); dependency status (payments provider, database).
Mitigate: rollback, shed load, disable the feature flag.
Verify recovery: 5m error ratio below 0.1%; alert resolves.
```

- Every alert carries `summary`, `runbook_url`, `severity`, and a routing label; descriptions use templated values (`{{ $value }}`, `{{ $labels.service }}`).

## 8. Grafana as code

Data source provisioning (`provisioning/datasources/prometheus.yaml`), with a secret from the environment and an exemplar link to traces:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: https://prometheus.internal:9090
    basicAuth: true
    basicAuthUser: grafana
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
        - name: trace_id
          datasourceUid: tempo
    secureJsonData:
      basicAuthPassword: $PROM_READER_PASSWORD
```

Dashboard provider (`provisioning/dashboards/services.yaml`):

```yaml
apiVersion: 1
providers:
  - name: services
    orgId: 1
    type: file
    disableDeletion: true
    allowUiUpdates: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

- `$VAR` references in provisioning files are expanded from the process environment; use them for secrets, never literal values.
- Choose one authoring path per dashboard and keep the file in Git: provisioning from files, Git Sync (generally available in Grafana 13.x; connect a repository and review changes through pull requests), Terraform (`grafana` provider), or code generators such as the Grafana Foundation SDK. Grafana 13 uses dynamic dashboards and a v2 dashboard schema; check the docs before hand-editing JSON produced by an older version.
- Dashboard hygiene: variables for environment and service, units on every panel, `$__rate_interval` in `rate()` queries, links to runbooks and trace views.
- Alerting: either keep rules in Prometheus or a Mimir-compatible ruler (versioned as rule files, evaluated server side) or use Grafana-managed alert rules (provisioned from files under `provisioning/alerting`, through the HTTP provisioning API, or Terraform `grafana_rule_group`). In Grafana 13.3 the `AlertRule` and `RecordingRule` resources are served as `v1beta1`; expect API changes between releases.
- Access: service accounts with the minimum role for automation, anonymous access off, read-only data source credentials.
- Error budget policy: write down what happens when the budget is spent (freeze risky releases, prioritise reliability work) and who decides.
- Upgrade checklist: read the release's breaking changes (13.3 renamed the `marketplace` ini section to `plugins_marketplace`), test provisioning in a staging instance, then roll out.
