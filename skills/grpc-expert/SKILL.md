---
name: grpc-expert
description: >-
  Designs, builds and reviews gRPC services and Protocol Buffers schemas: proto3 and Editions, schema evolution, Buf CLI, code generation for Go, Python, Node and Java, streaming, deadlines, retries, status codes, TLS, load balancing, ConnectRPC and gRPC-Web. Use when editing .proto, buf.yaml or buf.gen.yaml files, running buf, protoc, protoc-gen-go or grpcurl, or debugging DEADLINE_EXCEEDED, UNAVAILABLE and message size errors. Not for REST design (use rest-api-expert), GraphQL (use graphql-expert), service boundaries (use microservices-expert), Kafka or queues (use kafka-messaging-expert) or Go language details (use go-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# gRPC Expert

This skill covers gRPC services and the Protocol Buffers schemas behind them: schema design and evolution, the Buf toolchain, code generation, the four RPC kinds, deadlines, errors, retries, security, load balancing, browser access and testing. Examples use Go as the main server language with Python, Node and Connect alongside. REST design, GraphQL, service decomposition, message brokers and general Go language questions belong to other skills.

> Verified against Protocol Buffers editions 2023, 2024 and 2026 (descriptor.proto on main; protoc tags up to v36.2; PyPI protobuf 7.36.2), buf 1.75.0, grpc-go 1.85.0 (requires Go 1.26 in a local build), google.golang.org/protobuf 1.36.12, protoc-gen-go-grpc 1.6.2, grpcio, grpcio-tools, grpcio-status, grpcio-health-checking and grpcio-reflection 1.85.1, @grpc/grpc-js 1.14.7, @grpc/proto-loader 0.8.1, @bufbuild/protobuf and protoc-gen-es 2.16.0, @connectrpc/connect and connect-node 2.3.0, connect-go 1.21.1, grpc-gateway v2.33.0 (2026-10). Go, Python, Node and Connect examples were compiled and run against these versions.

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

- Covered: `.proto` design with proto3 and Editions, field numbers, `reserved`, enums, field presence, `oneof`, well-known types, wire and source compatibility; Buf CLI (`buf lint`, `buf breaking`, `buf generate`, `buf format`, `buf.yaml` and `buf.gen.yaml` v2, BSR briefly); generated code for Go, Python, Node and Java; unary, server streaming, client streaming and bidirectional RPCs; deadlines, cancellation, status codes, `google.rpc.Status` details, retries and hedging through service config, keepalive; TLS, mTLS, per-RPC credentials; interceptors; health checking and reflection; client-side load balancing, xDS, Envoy; gRPC-Web, ConnectRPC, grpc-gateway; OpenTelemetry; in-process tests, `bufconn`, `grpcurl`.
- Not covered: REST resource and URL design (rest-api-expert); GraphQL schemas (graphql-expert); where to split services and data ownership (microservices-expert); brokers, topics and consumer groups (kafka-messaging-expert); Go language, goroutines and modules beyond what gRPC needs (go-expert); Kubernetes manifests and service meshes (kubernetes-expert); nginx configuration (nginx-expert); tracing backends and dashboards (observability-expert); user login flows and token issuance (authentication-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Syntax | `syntax = "proto3";` is still fully supported. Editions replace the syntax line with `edition = "2023";` (or 2024, 2026) and per-file, per-message or per-field `features`. descriptor.proto on main lists released editions 2023, 2024 and 2026. In a local test, buf 1.75.0, protoc-gen-go 1.36.12, protoc-gen-go-grpc 1.6.2, protoc-gen-es 2.16.0 and grpcio-tools 1.85.1 compiled edition 2023 and 2024; Go and grpcio-tools rejected edition 2026 (buf accepted it). Check each generator before choosing an edition |
| Edition 2023 defaults | `features.field_presence` defaults to `EXPLICIT` (proto3 was `IMPLICIT`), so a plain `string id = 1;` becomes `*string` in Go. Set `option features.field_presence = IMPLICIT;` at file level to get proto3 behaviour. Enums default to `OPEN`, repeated scalars to `PACKED`, UTF-8 to `VERIFY`. There is no `optional` or `required` label; `reserved` names are identifiers, not strings |
| Edition 2024 | Adds symbol visibility (`export` and `local` keywords, `default_symbol_visibility`, default `EXPORT_TOP_LEVEL`), `import option`, and a naming style feature. protoc-gen-go switches the default API to Opaque (struct fields hidden, setters and builders); pick `API_HYBRID` with `import "google/protobuf/go_features.proto";` and `option features.(pb.go).api_level = API_HYBRID;` to keep field access |
| Evolution | Never reuse a field number or name: `reserved` removed ones. Renaming a field is wire compatible but breaks JSON and source. Changing a field type is breaking except within compatible groups (int32, uint32, int64, uint64, bool; sint32 and sint64; fixed32 and sfixed32; fixed64 and sfixed64). Adding fields and enum values is safe if receivers tolerate unknowns |
| Buf | `buf.yaml` and `buf.gen.yaml` use `version: v2`. `buf config init` writes `lint.use: [STANDARD]` and `breaking.use: [FILE]`. Lint categories include MINIMAL, BASIC, STANDARD, COMMENTS, UNARY_RPC; breaking categories FILE, PACKAGE, WIRE_JSON, WIRE. `buf breaking --against '.git#branch=main'` compares with a Git ref |
| RPC kinds | Unary, server streaming (`returns (stream R)`), client streaming (`rpc F(stream Q)`), bidirectional streaming. All run over HTTP/2; each RPC is one stream with headers, length-prefixed messages and trailers carrying `grpc-status` |
| Deadlines | The client sets a deadline; it is sent as the `grpc-timeout` header and the server sees a context that expires. The deadline does not propagate to downstream calls unless the handler passes its own context (Go) or equivalent. `DEADLINE_EXCEEDED` is raised on the client when the deadline passes |
| Errors | 17 canonical codes (OK through UNAUTHENTICATED). Rich details travel in the `grpc-status-details-bin` trailer as `google.rpc.Status` with `Any` details such as `BadRequest`, `ErrorInfo`, `RetryInfo`. Go: `status.New(...).WithDetails(...)`; Python: `grpc_status.rpc_status` |
| Retries | Configured with service config JSON: `methodConfig[].retryPolicy` (`maxAttempts` up to 5, `initialBackoff`, `maxBackoff`, `backoffMultiplier`, `retryableStatusCodes`) and top-level `retryThrottling`. Hedging is a separate `hedgingPolicy`; support differs by language, check the implementation docs |
| Transports | gRPC over HTTP/2 needs a client or proxy that supports trailers. Browsers cannot speak it: use gRPC-Web with a proxy (Envoy), or ConnectRPC (Connect, gRPC and gRPC-Web protocols from one handler). grpc-gateway generates a REST reverse proxy from `google.api.http` annotations |
| Language libraries | Go `google.golang.org/grpc` (use `grpc.NewClient`), Python `grpcio` with `grpc.aio`, Node `@grpc/grpc-js`, Java `grpc-java`. Connect: `connectrpc.com/connect` (Go), `@connectrpc/connect` (TypeScript), `connect-python` (check its maturity before adopting) |
| Versions | Go: grpc-go 1.85.0 raised the `go` directive of a test module to 1.26.0, so check the Go toolchain before upgrading. Python: protobuf 7.x pairs with protoc 36.x; regenerate `_pb2.py` files with a `grpcio-tools` release close to the installed `protobuf` runtime, because generated code checks the runtime version |

## 3. Workflow

1. Read the repository first: `buf.yaml`, `buf.gen.yaml`, existing `.proto` files, generated-code locations, CI config, and which languages consume the schema. Find out whether generated code is committed or built in CI.
2. Decide syntax: keep what the repo uses (proto3 or an edition). For a new schema, check that every generator, linter and validator in the pipeline accepts the edition; otherwise use proto3.
3. Change the schema with evolution rules in mind (section 4). Run `buf format -w`, `buf lint`, then `buf breaking --against '.git#branch=main'` before generating.
4. Regenerate with `buf generate` (or the project's script) and never hand-edit generated files. Commit generated code only if the repo already does.
5. Implement handlers and clients. Every client call gets a deadline; every handler checks `ctx.Err()` in loops and passes its context downstream.
6. Test with an in-process server (`bufconn` in Go, `grpc.aio` on `127.0.0.1:0` in Python), then by hand with `grpcurl` or `buf curl` against reflection.
7. Report which commands ran (`buf lint`, `buf breaking`, `buf generate`, tests) and any breaking change that was deliberate.

## 4. Decision Rules

- If a published field is no longer needed, stop using it and `reserved` its number and name; never reuse them, and never change the type of an existing field.
- If a message can grow, wrap request and response in their own messages (`GetOrderRequest`, `GetOrderResponse`) even for one field; never pass a bare scalar or a shared message across RPCs.
- If you need to tell "unset" from "zero", use field presence (`optional` in proto3, default `EXPLICIT` in editions) rather than wrapper messages; use `google.protobuf.*Value` wrappers only for existing schemas or for proto3 generators that need null in JSON.
- If an enum is used, make value 0 `<ENUM>_UNSPECIFIED` and prefix every value with the enum name; the zero value must mean "not set", never a real state.
- If a client needs only one answer, use unary. Use server streaming for large or live result sets, client streaming for uploads and batching, bidirectional only when both sides send independently (chat, watch with acknowledgements). A long stream is not a queue: use kafka-messaging-expert for durable messaging.
- If a result set is unbounded, paginate with `page_size` and `page_token` instead of a stream, unless the consumer needs live updates.
- If the caller is a browser, use ConnectRPC or gRPC-Web through Envoy. If external clients need JSON over REST, add grpc-gateway or Connect's JSON support; do not hand-write a second API.
- If a status code is unclear: `INVALID_ARGUMENT` for bad input independent of state, `FAILED_PRECONDITION` for state conflicts, `NOT_FOUND`, `ALREADY_EXISTS`, `PERMISSION_DENIED` (authenticated, not allowed), `UNAUTHENTICATED` (no or bad credentials), `RESOURCE_EXHAUSTED` (quota, rate limit), `UNAVAILABLE` (retry safe), `INTERNAL` (bug). Do not return `UNKNOWN` or `INTERNAL` for client mistakes.
- If an RPC is retried automatically, it must be idempotent or protected by an idempotency key in the request.
- If clients connect through a layer 4 load balancer, long-lived HTTP/2 connections pin to one backend: use client-side balancing (`round_robin` with a DNS or xDS resolver), a layer 7 proxy, or `MaxConnectionAge` on the server.
- If a project already uses another RPC stack (Connect-only, Twirp), keep it unless asked to migrate.

## 5. Coding Standards

- Follow the Buf STANDARD lint rules: package ends in a version (`acme.orders.v1`), directory matches package (`acme/orders/v1/orders.proto`), `lower_snake_case` fields, `PascalCase` messages, `UPPER_SNAKE_CASE` enum values with the enum name prefix, services end in `Service`, RPC request and response types named `<Rpc>Request` and `<Rpc>Response`.
- One service per file when it grows; keep shared types in a `common` package of the same version line.
- Use `google.protobuf.Timestamp` and `Duration` for time, not strings or epoch integers without units. Use `int64` for IDs only when they are numeric; use `string` for opaque IDs.
- Put comments on every service, RPC and field that is public API; document units, ranges and the status codes an RPC returns.
- Set `go_package` through Buf managed mode (`go_package_prefix`) instead of editing every file, unless the repo already hard-codes it.
- Call `grpc.NewClient` in Go (not the deprecated `Dial`); it connects lazily and defaults to the `dns` resolver, so use the `passthrough:///` scheme for `bufconn` and custom dialers.
- Embed `Unimplemented<Service>Server` in Go servers (the default `require_unimplemented_servers` behaviour of protoc-gen-go-grpc) so new RPCs do not break builds.
- Return errors as `status.Error(codes.X, msg)` or `status.New(...).WithDetails(...).Err()`; never return a plain `error` for an expected failure, and never put internal details (stack traces, SQL) in the message.
- Close connections and cancel contexts: `defer cancel()` after `context.WithTimeout`, `defer conn.Close()`, and drain or cancel streams.

## 6. Project Structure

```text
acme-api/
  buf.yaml               # v2 workspace: modules, lint, breaking, deps
  buf.gen.yaml           # v2 generation template
  buf.lock               # pinned BSR dependencies (buf dep update)
  proto/
    acme/orders/v1/
      orders.proto
      orders_service.proto
  gen/                   # generated code (gitignored or committed, one policy)
    go/
    ts/
  cmd/orders-server/     # main package: wiring, flags, TLS, graceful stop
  internal/orders/       # handler implementations, no generated code edits
  Makefile               # buf format, lint, breaking, generate, test
```

- Keep `.proto` files in a module path (`modules: - path: proto` in `buf.yaml`) so import paths start at the package root. Buf refuses an input directory that is contained in a module unless the module itself is the input.
- Version the package (`v1`, `v2`) and make a new version only for breaking changes; run both versions side by side during migration.
- Publish schemas as one module consumed by all languages, via a monorepo or the Buf Schema Registry (BSR), instead of copying `.proto` files between repos.
- Details of config files and generation: [references/buf-codegen.md](references/buf-codegen.md).

## 7. Design Patterns

- **Request and response wrappers**: every RPC has dedicated messages. Cost: more types; benefit: fields can be added without touching other RPCs.
- **Field masks for partial update**: `google.protobuf.FieldMask update_mask` in update requests; treat an empty mask as "reject" or "replace all" explicitly and document which.
- **Pagination**: `page_size`, `page_token` in the request, `next_page_token` in the response; tokens are opaque and signed or encrypted.
- **Long-running operations**: return an operation resource (`google.longrunning.Operation` or a custom one) and poll or watch; avoid holding a unary RPC open for minutes.
- **Server-side streaming for watch**: send an initial snapshot, then deltas with a resume token; the client reconnects with the last token after `UNAVAILABLE`.
- **Interceptors for cross-cutting concerns**: logging, metrics, auth, panic recovery, validation, per-RPC timeouts. Order matters: recovery outermost, then tracing, logging, auth, validation. Go: `grpc.ChainUnaryInterceptor` and `ChainStreamInterceptor`; Python: `grpc.aio.ServerInterceptor`; Connect: `connect.WithInterceptors`.
- **Validation at the edge**: declare constraints in the schema with protovalidate rules and enforce them in an interceptor, rather than repeating checks in every handler.
- **Graceful degradation**: health `NOT_SERVING` during drain, `GracefulStop` with a timeout fallback to `Stop`.
- **Outbox for events**: do not publish to a broker inside a handler without a transactional outbox; see kafka-messaging-expert.

## 8. Best Practices

- Always set a deadline on the client, either per call (`context.WithTimeout`) or as `timeout` in the service config; a call with no deadline can hang forever.
- Propagate the incoming context to downstream calls so cancellation and the remaining deadline flow through the chain. Do not start a fresh `context.Background()` inside a handler unless work must outlive the request, and then say so in a comment.
- Check `ctx.Err()` (or `context.Cause`) in long loops and before expensive work; on streams, stop sending when `Send` returns an error.
- Make retried methods idempotent; combine retries with backoff and `retryThrottling` so an outage does not multiply load.
- Send identifiers and auth in metadata (headers), not in message bodies; metadata keys are lowercase, binary values end in `-bin`.
- Name and version for compatibility: add fields, add RPCs, deprecate with `[deprecated = true]` and a comment, remove only after clients are gone and the number is `reserved`.
- Keep messages well under 4 MiB (the common default receive limit). Stream large payloads in chunks of tens to hundreds of KiB, or hand out a signed object-store URL.
- Reuse one `ClientConn` (Go) or one channel per target; they multiplex many RPCs and handle reconnection. Do not create one per request.
- Expose the standard health service (`grpc.health.v1.Health`) and use it for Kubernetes probes and load balancer checks.
- Version servers and clients independently; test an old client against a new server and vice versa in CI using `buf breaking` plus compatibility tests.
- Error mapping belongs at the service boundary: translate domain and database errors to status codes in one place.

## 9. Performance

- Reuse connections; HTTP/2 multiplexes streams on one TCP connection, bounded by `MAX_CONCURRENT_STREAMS` (often 100). For high fan-out, use several connections (a pool) or a balancer that opens subchannels per backend.
- Prefer unary for small request and response pairs; streaming helps when sending many messages (per-message overhead is lower than per-call overhead) or when latency to first result matters. A stream pins to one backend for its life.
- Default receive limit is 4 MiB in most libraries and the Go send limit is effectively unlimited; raise limits explicitly (`grpc.MaxRecvMsgSize`, `grpc.max_receive_message_length`) only with a reason, and prefer chunked streaming.
- Use `bytes` for binary data and avoid base64 strings; use packed repeated scalars (the default for proto3 and editions) and `sint32` or `sint64` for values that are often negative.
- Compression: `grpc-encoding: gzip` helps large compressible text; it costs CPU on small messages. Enable per call or per connection after measuring.
- Keepalive: configure client pings (`Time` not below the server's `MinTime`, default 5 minutes in grpc-go) or the server answers with `GOAWAY` and `too_many_pings`. See [references/errors-deadlines-retries.md](references/errors-deadlines-retries.md).
- Avoid copying large messages in interceptors; log sizes, not bodies. In Go, reuse buffers through the proto library and avoid `proto.Clone` on hot paths.
- Measure with `ghz` or the project's load tool, and read server metrics (in-flight RPCs, latency histogram by method and code) before tuning; see load-testing-expert for method.

## 10. Security

- Use TLS for every non-loopback connection. Go: `credentials.NewTLS(&tls.Config{MinVersion: tls.VersionTLS13, ...})`; Python: `grpc.ssl_channel_credentials` and `grpc.ssl_server_credentials`; Node: `grpc.credentials.createSsl` and `grpc.ServerCredentials.createSsl`. Never ship `insecure.NewCredentials()` outside tests or loopback.
- Use mTLS between services: server sets `ClientAuth: tls.RequireAndVerifyClientCert` with a CA pool; derive caller identity from the verified peer certificate (SPIFFE ID or SAN), not from a header.
- Authenticate users and services with tokens in the `authorization` metadata, sent through per-RPC credentials (`credentials.PerRPCCredentials`, `grpc.metadata_call_credentials`). Per-RPC credentials that carry bearer tokens must `RequireTransportSecurity() == true`.
- Verify tokens in a server interceptor and put the principal in the context. Enforce authorization per method (`info.FullMethod`), default deny. Token issuance and scopes: authentication-expert and authorization-expert.
- Disable server reflection in production, or restrict it to authenticated operators; it reveals the full API surface.
- Set limits: `MaxRecvMsgSize`, `MaxConcurrentStreams`, connection idle and age limits, keepalive enforcement, and per-method rate limits, to resist slow and oversized requests.
- Do not log message bodies or metadata containing credentials; redact `authorization` and `cookie`.
- Validate every field at the boundary (lengths, ranges, enum membership, UTF-8). Parameterise SQL; never concatenate request fields into queries or shell commands.
- Keep private keys out of source and images: load certificates from mounted secrets and reload on rotation (`tls.Config.GetCertificate` or `GetConfigForClient` in Go).
- For browsers, enable CORS only for known origins and keep cookies and bearer tokens separate; see [references/security-and-deployment.md](references/security-and-deployment.md) for mTLS code, per-RPC credentials and the Connect and gateway options. General API threats: api-security-expert.

## 11. Testing

- **In-process, Go**: `bufconn.Listen(1 << 20)` with `grpc.NewServer()` and `grpc.NewClient("passthrough:///bufnet", grpc.WithContextDialer(...), grpc.WithTransportCredentials(insecure.NewCredentials()))`; test code stays free of ports. Register `t.Cleanup(s.Stop)` and `t.Cleanup(conn.Close)`.
- **In-process, Python**: start `grpc.aio.server()`, bind `127.0.0.1:0`, read the returned port, connect with `grpc.aio.insecure_channel`; `grpcio-testing` offers fakes for sync servicers.
- **Node and Connect**: `connectNodeAdapter` on `http2.createServer` bound to port 0, with `createGrpcTransport` or `createConnectTransport`; or `createRouterTransport` from `@connectrpc/connect` for no network at all.
- **Behaviour to test**: status codes and details, deadline expiry (server sleeps past a short deadline), cancellation (client cancels, handler sees `ctx.Done()`), streaming end of stream and early client close, interceptor order, auth failure paths, retry with a server that fails with `UNAVAILABLE` twice then succeeds.
- **Schema checks in CI**: `buf format --diff --exit-code`, `buf lint`, `buf breaking --against '.git#branch=main'`, and `buf generate` followed by `git diff --exit-code` when generated code is committed.
- **By hand**: `grpcurl -plaintext localhost:50051 list`, `grpcurl -d '{"id":"o-1"}' -plaintext localhost:50051 acme.orders.v1.OrderService/GetOrder`; `buf curl --protocol grpc ...` works with reflection or a local schema. Use `-cacert` and `-cert`/`-key` for TLS and mTLS.
- Test with the real serialization path; do not call handler methods directly if the behaviour depends on interceptors, metadata or status conversion.
- Test strategy beyond gRPC: unit-testing-expert and integration-testing-expert.

## 12. Review Checklist

- [ ] No field number or name reused; removed fields are `reserved`; no type changes on existing fields.
- [ ] `buf lint` and `buf breaking` pass (or the breaking change is deliberate and versioned).
- [ ] Enums have a `_UNSPECIFIED = 0` value and prefixed names.
- [ ] Each RPC has its own request and response messages; no bare scalars.
- [ ] Field presence is chosen deliberately (edition default is explicit presence).
- [ ] Every client call has a deadline; handlers pass context downstream and respect cancellation.
- [ ] Status codes match the table in section 4; details use `google.rpc` types; no internal error text leaks.
- [ ] Retried RPCs are idempotent; retry policy has backoff and throttling.
- [ ] TLS (or mTLS) configured; per-RPC credentials require transport security; reflection off or protected.
- [ ] Message size, keepalive, concurrency and idle limits are set intentionally.
- [ ] Health service registered and used by probes; graceful shutdown implemented.
- [ ] Streams: end of stream handled, goroutines or tasks exit on cancel, no unbounded buffers.
- [ ] Generated code is not hand-edited; tool versions are pinned (Buf, plugins).
- [ ] Tests cover success, error status, deadline, and one streaming case.

## 13. Production Notes

- Graceful shutdown: set health to `NOT_SERVING`, wait for the load balancer to drain, call `GracefulStop`, and fall back to `Stop` after a timeout. `MaxConnectionAge` plus `MaxConnectionAgeGrace` makes clients reconnect and rebalance.
- Kubernetes: ClusterIP services balance per connection, so gRPC clients stick to one pod; use a headless service with `dns:///` and `round_robin`, a mesh or Envoy, or an xDS resolver. Native gRPC probes (`grpc:` in a probe spec) call the health service.
- Proxies must support HTTP/2 end to end: Envoy (`http2_protocol_options`, route timeouts, `grpc_web` filter), nginx (`grpc_pass`, `grpcs://`; see nginx-expert), cloud load balancers with gRPC support enabled. Proxy idle timeouts shorter than client keepalive cause `UNAVAILABLE` resets.
- Observability: per-method RED metrics (rate, errors by code, duration), traces via OpenTelemetry (Go: `otelgrpc` stats handlers from opentelemetry-go-contrib; Python: `opentelemetry-instrumentation-grpc`; Connect: `connectrpc.com/otelconnect`), and structured logs with method, code, duration and peer. Verify package names against the current OpenTelemetry docs. General guidance: observability-expert.
- Alert on `UNAVAILABLE`, `DEADLINE_EXCEEDED` and `RESOURCE_EXHAUSTED` rates per method, not only on HTTP-level errors, because gRPC errors arrive with HTTP 200.
- Schema rollout: deploy servers that accept the new fields first, then clients that send them; remove old fields only after all clients have stopped using them.
- Debug: set `GRPC_GO_LOG_SEVERITY_LEVEL=info` and `GRPC_GO_LOG_VERBOSITY_LEVEL=2` for grpc-go, `GRPC_VERBOSITY=debug` and `GRPC_TRACE=...` for the C-core libraries (Python), and `GRPC_TRACE` with `GRPC_VERBOSITY` for grpc-js. Use `grpcurl -v` for headers and trailers. Check the library docs for current variable names.
- Deployment and security detail: [references/security-and-deployment.md](references/security-and-deployment.md).

## 14. Examples

Schema (edition 2023 with proto3-style presence, the form used in the checks above):

```proto
edition = "2023";

package acme.orders.v1;

option features.field_presence = IMPLICIT;
option go_package = "example.com/acme/gen/acme/orders/v1;ordersv1";

enum OrderStatus {
  ORDER_STATUS_UNSPECIFIED = 0;
  ORDER_STATUS_PENDING = 1;
  ORDER_STATUS_SHIPPED = 2;
}

message Order {
  string id = 1;
  OrderStatus status = 2;
  // Explicit presence: unset differs from empty.
  string note = 3 [features.field_presence = EXPLICIT];
  reserved 4;
  reserved legacy_total;
}

message GetOrderRequest { string id = 1; }
message GetOrderResponse { Order order = 1; }
message WatchOrdersRequest {}
message WatchOrdersResponse { Order order = 1; }

service OrderService {
  // Returns NOT_FOUND when the order does not exist.
  rpc GetOrder(GetOrderRequest) returns (GetOrderResponse);
  rpc WatchOrders(WatchOrdersRequest) returns (stream WatchOrdersResponse);
}
```

Buf configuration (v2) and generation for Go:

```yaml
# buf.yaml
version: v2
modules:
  - path: proto
lint:
  use:
    - STANDARD
breaking:
  use:
    - FILE
```

```yaml
# buf.gen.yaml
version: v2
managed:
  enabled: true
  override:
    - file_option: go_package_prefix
      value: example.com/acme/gen
plugins:
  - local: protoc-gen-go
    out: gen/go
    opt: paths=source_relative
  - local: protoc-gen-go-grpc
    out: gen/go
    opt: paths=source_relative
inputs:
  - directory: proto
```

Client call with a deadline and error inspection (Go):

```go
ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
defer cancel()

resp, err := client.GetOrder(ctx, &ordersv1.GetOrderRequest{Id: id})
if err != nil {
	switch status.Code(err) {
	case codes.NotFound:
		return nil, ErrOrderNotFound
	case codes.DeadlineExceeded, codes.Unavailable:
		return nil, fmt.Errorf("orders backend: %w", err)
	default:
		return nil, err
	}
}
return resp.GetOrder(), nil
```

Server-side error with details (Go; needs `google.golang.org/genproto/googleapis/rpc/errdetails`):

```go
st := status.New(codes.InvalidArgument, "invalid request")
st, err := st.WithDetails(&errdetails.BadRequest{
	FieldViolations: []*errdetails.BadRequest_FieldViolation{
		{Field: "id", Description: "must not be empty"},
	},
})
if err != nil {
	return nil, status.Error(codes.Internal, "build error details")
}
return nil, st.Err()
```

More complete server, client, Python, Node and Connect programs: [references/language-guides.md](references/language-guides.md).

## 15. Common Mistakes

- Reusing a field number after deleting a field, or changing `int32` to `string`: old data decodes as garbage or fails. Use `reserved` and add a new field.
- Enum without a zero `UNSPECIFIED` value, or with a meaningful zero (`ORDER_STATUS_PENDING = 0`): unset fields look like real states.
- Assuming edition 2023 keeps proto3 presence: a plain scalar becomes a pointer in Go and has `has_` semantics elsewhere. Set `features.field_presence = IMPLICIT` if that is not wanted.
- Using edition 2024 with Go and then writing struct literals: the default Opaque API hides fields. Use builders and setters, or set `API_HYBRID`.
- No deadline on the client: stuck backends hold goroutines and connections indefinitely.
- Starting a fresh `context.Background()` in a handler for downstream calls: the caller's cancellation and remaining deadline are lost.
- Retrying non-idempotent RPCs, or retrying on `DEADLINE_EXCEEDED` without a budget: duplicates and retry storms.
- Returning `UNKNOWN` or `INTERNAL` for validation errors, and leaking exception text in messages.
- One `ClientConn` per request, or a `ClusterIP` service with no client-side balancing: connection churn or all traffic on one pod.
- Keepalive pings more frequent than the server allows: `GOAWAY` with `too_many_pings`.
- Raising max message size instead of streaming large payloads; large unary messages use memory on both sides and hit proxy limits.
- Enabling reflection and plaintext on a public port.
- Calling `Dial` with `WithBlock` in new Go code: use `grpc.NewClient`, which connects lazily, and rely on deadlines and `waitForReady` where needed.
- Editing generated files, or generating with a mix of plugin versions across machines; pin plugins in `buf.gen.yaml` or tooling files.
- Using `buf breaking` with the wrong `--against` target, or categories weaker than the contract (use `WIRE_JSON` or `FILE` when JSON or generated code is part of the contract).

## 16. References

- [references/proto-design-evolution.md](references/proto-design-evolution.md): proto3 versus Editions, features, field presence and wrappers, enums, oneof, maps, field numbers and reserved, wire compatibility table, naming and API shape, protovalidate.
- [references/buf-codegen.md](references/buf-codegen.md): `buf.yaml` and `buf.gen.yaml` v2, managed mode, lint and breaking categories, CI commands, BSR, protoc plugins for Go, Python, Node, Java, grpc-gateway and OpenAPI.
- [references/errors-deadlines-retries.md](references/errors-deadlines-retries.md): status code table, rich error details in Go and Python, deadlines and cancellation, service config retries and hedging, keepalive, message limits, stream flow control.
- [references/security-and-deployment.md](references/security-and-deployment.md): TLS and mTLS code, per-RPC credentials, interceptors, health and reflection, load balancing and xDS, Envoy, gRPC-Web, Connect, grpc-gateway, OpenTelemetry.
- [references/language-guides.md](references/language-guides.md): runnable Go server and client, bufconn test, Python grpc.aio, Node grpc-js and Connect, grpcurl and buf curl.
- gRPC documentation: https://grpc.io/docs/ ; core concepts, status codes and guides at https://grpc.io/docs/guides/
- gRPC repositories and release notes: https://github.com/grpc/grpc , https://github.com/grpc/grpc-go , https://github.com/grpc/grpc-java , https://github.com/grpc/grpc-node
- gRPC proposals (retries, service config, xDS): https://github.com/grpc/proposal
- Protocol Buffers: https://protobuf.dev/ (editions overview, language guide, style guide, best practices); releases at https://github.com/protocolbuffers/protobuf/releases
- Buf: https://buf.build/docs/ ; Buf CLI releases https://github.com/bufbuild/buf/releases
- ConnectRPC: https://connectrpc.com/docs/ ; grpc-gateway: https://grpc-ecosystem.github.io/grpc-gateway/
- Error model: https://cloud.google.com/apis/design/errors ; API design guide https://google.aip.dev/
