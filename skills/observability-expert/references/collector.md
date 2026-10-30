# OpenTelemetry Collector Configuration

Gateway and agent configurations, processor order, sampling tiers, redaction, and securing OTLP with TLS and authentication. Verified against Collector v0.164.0 and the component READMEs for `memory_limiter`, `batch`, `tail_sampling`, `probabilisticsampler`, `redaction`, `loadbalancing` and exporterhelper (2026-10). Component names, options and internal metric names change between 0.x releases: check the README of the exact version deployed.

## Contents

1. [Anatomy of the configuration](#1-anatomy-of-the-configuration)
2. [Agent configuration](#2-agent-configuration)
3. [Gateway with redaction and tail sampling](#3-gateway-with-redaction-and-tail-sampling)
4. [Sampling tiers](#4-sampling-tiers)
5. [Redaction and attribute hygiene](#5-redaction-and-attribute-hygiene)
6. [TLS and authentication](#6-tls-and-authentication)
7. [Operating the Collector](#7-operating-the-collector)

## 1. Anatomy of the configuration

- Top-level keys: `receivers`, `processors`, `exporters`, `connectors`, `extensions`, `service`. Defining a component does nothing until it is listed in `service.pipelines.<signal>` (or `service.extensions`).
- A component can have several instances named `type/name` (for example `otlp/internal`). Each pipeline has a signal type (`traces`, `metrics`, `logs`) and its own receivers, processors and exporters.
- Processors run in the order listed in the pipeline. Receivers and exporters shared by pipelines are one instance.
- Environment variables are expanded with `${env:NAME}`; use this for tokens and never write secrets into the file.
- Several config files can be merged: `--config=base.yaml --config=prod.yaml`.
- Validate before deploying: `otelcol validate --config=file.yaml` (use the subcommand of the distribution in use, for example `otelcol-contrib validate`).
- Recommended processor order: `memory_limiter`, then enrichment and redaction (`k8sattributes`, `resource`, `redaction`, `transform`, `filter`), then samplers (`tail_sampling`, `probabilistic_sampler`), then `batch`. Batching comes after anything that drops data, and `memory_limiter` is first so back-pressure reaches the receivers.
- `memory_limiter` options: `check_interval` (recommended 1s), `limit_mib` or `limit_percentage` (one is required), `spike_limit_mib` or `spike_limit_percentage` (default 20 percent of the limit). With `limit_mib: 4000` and `spike_limit_mib: 800` the soft limit is 3200 MiB.
- `batch` options: `send_batch_size` (8192, a trigger, not a cap), `send_batch_max_size` (0 = no cap), `timeout` (200ms). Beta for all signals.

## 2. Agent configuration

An agent runs next to the workload (host service or sidecar), accepts local OTLP and forwards to the gateway over TLS. It keeps the SDK endpoint local and adds resource detection.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25
  resourcedetection:
    detectors: [env, system]
  batch: {}

exporters:
  otlp/gateway:
    endpoint: otel-gateway.example.internal:4317
    tls:
      ca_file: /etc/otelcol/tls/ca.crt
      cert_file: /etc/otelcol/tls/client.crt
      key_file: /etc/otelcol/tls/client.key
    sending_queue:
      queue_size: 2000
    retry_on_failure:
      enabled: true

extensions:
  health_check:
    endpoint: 127.0.0.1:13133

service:
  extensions: [health_check]
  pipelines:
    traces:  {receivers: [otlp], processors: [memory_limiter, resourcedetection, batch], exporters: [otlp/gateway]}
    metrics: {receivers: [otlp], processors: [memory_limiter, resourcedetection, batch], exporters: [otlp/gateway]}
    logs:    {receivers: [otlp], processors: [memory_limiter, resourcedetection, batch], exporters: [otlp/gateway]}
```

The exporter verifies the gateway certificate against `ca_file`; client certificate and key give mTLS. Do not set `insecure_skip_verify`.

## 3. Gateway with redaction and tail sampling

A gateway receives from agents over TLS, removes sensitive data, derives RED metrics from all traffic, then samples. This single-replica form is valid; for several replicas add the first tier from section 4.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otelcol/tls/server.crt
          key_file: /etc/otelcol/tls/server.key
          client_ca_file: /etc/otelcol/tls/clients-ca.crt   # require client certificates

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25
  redaction:
    allow_all_keys: true
    blocked_key_patterns: [".*token.*", ".*password.*", ".*secret.*", ".*authorization.*"]
    blocked_values: ["4[0-9]{12}(?:[0-9]{3})?"]      # card-number shaped values
    summary: info
  transform/scrub:
    trace_statements:
      - context: span
        statements:
          - delete_key(attributes, "http.request.header.cookie")
          - replace_pattern(attributes["url.full"], "([?&](?:token|key|sig)=)[^&]+", "$$1REDACTED")
  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    expected_new_traces_per_sec: 200
    policies:
      - name: keep-errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: keep-slow
        type: latency
        latency: {threshold_ms: 2000}
      - name: baseline
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
  batch: {}

connectors:
  spanmetrics: {}
  forward/sampling: {}

exporters:
  otlp/traces:
    endpoint: tempo.example.internal:4317
    headers:
      authorization: "Bearer ${env:TRACES_BACKEND_TOKEN}"
  prometheusremotewrite:
    endpoint: https://prometheus.example.internal/api/v1/write
    tls:
      ca_file: /etc/otelcol/tls/ca.crt
    auth:
      authenticator: basicauth/metrics

extensions:
  basicauth/metrics:
    client_auth:
      username: ${env:METRICS_USER}
      password: ${env:METRICS_PASSWORD}
  health_check:
    endpoint: 127.0.0.1:13133

service:
  extensions: [basicauth/metrics, health_check]
  pipelines:
    traces/in:
      receivers: [otlp]
      processors: [memory_limiter, redaction, transform/scrub]
      exporters: [spanmetrics, forward/sampling]
    traces/sampled:
      receivers: [forward/sampling]
      processors: [tail_sampling, batch]
      exporters: [otlp/traces]
    metrics:
      receivers: [otlp, spanmetrics]
      processors: [memory_limiter, redaction, batch]
      exporters: [prometheusremotewrite]
```

Notes on this file:

- `forward/sampling` is an instance of the `forward` connector, declared under `connectors:`. It splits the traces path so `spanmetrics` sees every span and `tail_sampling` sees the same stream.
- `replace_pattern` replacement strings use `$$1` in Collector YAML because a single `$` starts variable expansion.
- The Prometheus remote write endpoint must have remote-write receiving enabled (`--web.enable-remote-write-receiver`) and be protected, or use a long-term store designed for it.
- `tail_sampling` policy `status_code` takes `status_codes: [ERROR]`; `latency` takes `threshold_ms`; policy results are OR-ed, so a trace matching any policy is kept.
- Check the `basicauth` extension README of the deployed version for the exact client and server option names.

## 4. Sampling tiers

Head sampling decides at the root span in the SDK. Tail sampling decides after the whole trace is buffered, so it can keep every error and slow trace. Choose by need:

| Method | Where | Strength | Cost |
|---|---|---|---|
| Head, parent-based | SDK (`OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.1`) | Cheap, stateless, drops data before it leaves the process | Cannot know the outcome; may drop errors |
| Consistent probability | Collector `probabilistic_sampler` (modes `hash_seed` default, `proportional`, `equalizing`) | Same decision across tiers when the hash seed matches; threshold stored in `tracestate` as `ot=th:...` | Still blind to outcome |
| Tail | Collector `tail_sampling` | Keeps errors, slow traces, specific tenants or routes | Memory for `num_traces`, `decision_wait` delay, needs all spans in one instance |

Scaling tail sampling needs two tiers. Tier 1 load-balances spans by trace ID; tier 2 runs `tail_sampling`:

```yaml
exporters:
  loadbalancing:
    routing_key: traceID
    protocol:
      otlp:
        timeout: 5s
        tls:
          ca_file: /etc/otelcol/tls/ca.crt
    resolver:
      dns:
        hostname: otel-sampler-headless.observability.svc.cluster.local
        port: 4317
```

- Default routing for traces is already `traceID`; set it explicitly for clarity.
- The `dns` resolver suits a headless service; `static` suits a fixed list; `k8s` needs RBAC to read EndpointSlices. Creating the headless Service itself is a kubernetes-expert task.
- Set `decision_wait` above the longest expected trace duration; spans arriving after the decision are handled separately and can produce partial traces.
- Raise `num_traces` with the product of new traces per second and `decision_wait`, and size `memory_limiter` to match.
- Do not tail-sample metrics derived from spans: compute `spanmetrics` before the sampler (section 3).

## 5. Redaction and attribute hygiene

- `redaction` processor: `allowed_keys` removes every attribute not listed (fail-closed); `allow_all_keys: true` disables that and relies on `blocked_key_patterns` (regex on keys) and `blocked_values` (regex on values). `allowed_values` exempts matching values; `ignored_keys` skips exact keys. `hash_function` (`hmac-sha256`, `hmac-sha512`, `sha3`) replaces masking with a hash and needs `hmac_key` for the HMAC variants, read from `${env:...}`. `summary` (`debug`, `info`, `silent`) controls the audit attributes added to the data.
- Use `transform` (OTTL) for structured edits: `delete_key`, `replace_pattern`, `set`, `truncate_all`. Test statements with sample data in a staging pipeline and the `debug` exporter.
- Use `filter` to drop low-value telemetry (health checks, static assets) before it costs money.
- Use `attributes` or `resource` processors to add `deployment.environment.name` and remove noisy resource keys.
- Redaction is a safety net, not the primary control: application code should not put secrets or PII in telemetry. Regex on values has false negatives, and every extra processor costs CPU.

## 6. TLS and authentication

- Receivers and exporters should use encrypted connections; never use `insecure: true` or `insecure_skip_verify` outside a throwaway local test.
- Server TLS: `tls.cert_file` and `tls.key_file` on the receiver. Mutual TLS: add `tls.client_ca_file`. Exporter side: `tls.ca_file` to verify the server, `cert_file` and `key_file` for the client identity.
- Token or password authentication: declare an authenticator extension (`basicauth`, `bearertokenauth`, `oidc`) and attach it with `auth: {authenticator: <extension name>}` on the receiver (server side) or exporter (client side). Option names differ per extension and version: read its README.
- Network exposure: the OTLP receiver defaults to `localhost`; open `0.0.0.0` only with TLS plus authentication or a network policy. Keep `health_check`, `pprof` and `zpages` on localhost.
- SDK side of the same settings: `OTEL_EXPORTER_OTLP_CERTIFICATE` (trusted CA), `OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE` and `OTEL_EXPORTER_OTLP_CLIENT_KEY` (mTLS), `OTEL_EXPORTER_OTLP_HEADERS` for a token (`authorization=Bearer ...`, supplied from a secret, never committed). `OTEL_EXPORTER_OTLP_INSECURE` is `false` by default and should stay so.
- Browser clients cannot hold secrets: do not ship a backend token in a front-end bundle. Receive browser telemetry through a proxy that adds credentials, restrict CORS with `allowed_origins`, and rate-limit.
- Run the Collector as a non-root user, read-only filesystem, with certificates mounted from a secret store.

## 7. Operating the Collector

- Health: `health_check` extension (conventionally port 13133) for liveness and readiness.
- Internal telemetry: scrape the Collector's own metrics endpoint. Watch queue size versus capacity, enqueue failures (`otelcol_exporter_enqueue_failed_*`), send failures, and refused data from `memory_limiter` (`otelcol_processor_refused_*`). Confirm metric names on the deployed version.
- Back-pressure: when `memory_limiter` refuses data, receivers return errors to senders, and SDK exporters retry or drop. A sustained refusal means scale out or reduce volume.
- Persistent queue: set `sending_queue.storage` to a `file_storage` extension to survive restarts; it replaces the in-memory queue and needs a writable volume.
- Retries: `retry_on_failure` defaults are 5s initial, 30s max interval, 300s max elapsed time; `max_elapsed_time: 0` retries forever and can fill the queue.
- Debugging: add the `debug` exporter (`verbosity: detailed`) to a test pipeline only; it prints telemetry, including attribute values, to the Collector log.
- Distributions: the core distribution has a small component set; most processors and exporters named here (`tail_sampling`, `redaction`, `loadbalancing`, `transform`) ship in the contrib distribution, or in a custom build made with the OpenTelemetry Collector Builder.
