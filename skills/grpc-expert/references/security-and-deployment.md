# Security, Interceptors and Deployment

TLS and mTLS, per-RPC credentials, interceptors, health checking, reflection, load balancing, Envoy, browser access (gRPC-Web and Connect), REST gateways and OpenTelemetry. Go code was compiled against grpc-go 1.85.0; library names for Python, Node and OpenTelemetry follow the registries checked in 2026-10 (otelgrpc v0.72.0, connectrpc.com/otelconnect v0.12.0, connectrpc.com/grpchealth v1.5.0, connectrpc.com/grpcreflect v1.3.1, connectrpc.com/cors v0.1.0). Verify APIs of those packages in their docs before copying.

## Contents

1. [TLS and mTLS](#1-tls-and-mtls)
2. [Per-RPC credentials and auth](#2-per-rpc-credentials-and-auth)
3. [Interceptors](#3-interceptors)
4. [Health checking and reflection](#4-health-checking-and-reflection)
5. [Load balancing](#5-load-balancing)
6. [Envoy and other proxies](#6-envoy-and-other-proxies)
7. [Browsers: gRPC-Web and Connect](#7-browsers-grpc-web-and-connect)
8. [REST transcoding](#8-rest-transcoding)
9. [OpenTelemetry](#9-opentelemetry)
10. [Kubernetes notes](#10-kubernetes-notes)

## 1. TLS and mTLS

```go
package app

import (
	"crypto/tls"
	"crypto/x509"
	"errors"
	"os"

	"google.golang.org/grpc/credentials"
)

func serverCreds(certFile, keyFile, clientCAFile string) (credentials.TransportCredentials, error) {
	cert, err := tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return nil, err
	}
	caPEM, err := os.ReadFile(clientCAFile)
	if err != nil {
		return nil, err
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caPEM) {
		return nil, errors.New("no CA certificates found")
	}
	return credentials.NewTLS(&tls.Config{
		Certificates: []tls.Certificate{cert},
		ClientCAs:    pool,
		ClientAuth:   tls.RequireAndVerifyClientCert,
		MinVersion:   tls.VersionTLS13,
	}), nil
}

func clientCreds(certFile, keyFile, serverCAFile, serverName string) (credentials.TransportCredentials, error) {
	cert, err := tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return nil, err
	}
	caPEM, err := os.ReadFile(serverCAFile)
	if err != nil {
		return nil, err
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caPEM) {
		return nil, errors.New("no CA certificates found")
	}
	return credentials.NewTLS(&tls.Config{
		Certificates: []tls.Certificate{cert},
		RootCAs:      pool,
		ServerName:   serverName,
		MinVersion:   tls.VersionTLS13,
	}), nil
}
```

- gRPC requires HTTP/2 with ALPN `h2`; Go's credentials set it. Terminating TLS in a proxy that does not negotiate `h2` fails with protocol errors.
- Server-only TLS: omit `ClientCAs`/`ClientAuth`; clients use `credentials.NewClientTLSFromFile(caFile, serverName)` or the system pool with `credentials.NewTLS(&tls.Config{})`.
- Read the caller from the verified chain: `peer.FromContext(ctx)` then `p.AuthInfo.(credentials.TLSInfo).State.VerifiedChains[0][0]`; use SAN URIs (SPIFFE IDs) or DNS names as identity and authorise on them in an interceptor.
- Rotation: use `tls.Config.GetCertificate` (server) and `GetClientCertificate` (client) backed by a reloading file watcher so restarts are not needed; keep leaf lifetimes short.
- Python: `grpc.ssl_server_credentials([(key_pem, cert_pem)], root_certificates=ca_pem, require_client_auth=True)` and `server.add_secure_port("[::]:8443", creds)`; client `grpc.ssl_channel_credentials(root_certificates=ca_pem, private_key=key_pem, certificate_chain=cert_pem)` with `grpc.secure_channel(target, creds)`. Override the expected name with `("grpc.ssl_target_name_override", name)` only in tests.
- Node grpc-js: `grpc.credentials.createSsl(rootCerts, privateKey, certChain)` for clients; `grpc.ServerCredentials.createSsl(rootCerts, [{ private_key, cert_chain }], true)` for servers (the last argument requires client certificates). Node Connect servers use `http2.createSecureServer({ key, cert, ca, requestCert: true })`.
- Never disable verification (`InsecureSkipVerify`, `check_hostname = False`) outside throwaway tests. Generate test certificates with a script into a temp directory, never commit private keys.
- A service mesh or SPIFFE/SPIRE can issue workload certificates.

## 2. Per-RPC credentials and auth

```go
type tokenAuth struct{ token func(ctx context.Context) (string, error) }

func (a tokenAuth) GetRequestMetadata(ctx context.Context, uri ...string) (map[string]string, error) {
	t, err := a.token(ctx)
	if err != nil {
		return nil, err
	}
	return map[string]string{"authorization": "Bearer " + t}, nil
}

// Refuses to send the token over a connection without transport security.
func (a tokenAuth) RequireTransportSecurity() bool { return true }

conn, err := grpc.NewClient(target,
	grpc.WithTransportCredentials(creds),
	grpc.WithPerRPCCredentials(tokenAuth{token: tokenSource}),
)
```

Server-side check in a unary interceptor:

```go
func authInterceptor(verify func(ctx context.Context, token string) (string, error)) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req any, info *grpc.UnaryServerInfo, h grpc.UnaryHandler) (any, error) {
		md, _ := metadata.FromIncomingContext(ctx)
		vals := md.Get("authorization")
		if len(vals) == 0 || !strings.HasPrefix(vals[0], "Bearer ") {
			return nil, status.Error(codes.Unauthenticated, "missing credentials")
		}
		principal, err := verify(ctx, strings.TrimPrefix(vals[0], "Bearer "))
		if err != nil {
			return nil, status.Error(codes.Unauthenticated, "invalid credentials")
		}
		return h(context.WithValue(ctx, principalKey{}, principal), req)
	}
}
```

- Metadata keys are lowercase ASCII; keys ending in `-bin` carry binary values (base64 on the wire). Reserved prefix `grpc-` belongs to the library.
- Python: `grpc.access_token_call_credentials(token)` composed with channel credentials via `grpc.composite_channel_credentials`, or `grpc.metadata_call_credentials(plugin)`; Python refuses call credentials on insecure channels. Server auth through a `grpc.aio.ServerInterceptor` or `ServicerContext.invocation_metadata()`.
- Google-style ADC and OAuth credentials are in `google.golang.org/grpc/credentials/oauth` and `google-auth` for Python; use them for Google APIs only.
- Authorise per method with a table `FullMethod -> required scope or role`, default deny, and keep authorisation separate from authentication. Token format, rotation and scopes: authentication-expert and authorization-expert.
- Do not trust identity headers set by clients (`x-user-id`); only trust headers added by a proxy you control, and strip them at the edge.

## 3. Interceptors

```go
s := grpc.NewServer(
	grpc.ChainUnaryInterceptor(recoveryUnary, loggingUnary, authInterceptor(verify)),
	grpc.ChainStreamInterceptor(recoveryStream, loggingStream),
)

conn, _ := grpc.NewClient(target,
	grpc.WithTransportCredentials(creds),
	grpc.WithChainUnaryInterceptor(clientTimeout(3*time.Second)),
)

func clientTimeout(d time.Duration) grpc.UnaryClientInterceptor {
	return func(ctx context.Context, method string, req, reply any, cc *grpc.ClientConn, inv grpc.UnaryInvoker, opts ...grpc.CallOption) error {
		if _, ok := ctx.Deadline(); !ok {
			var cancel context.CancelFunc
			ctx, cancel = context.WithTimeout(ctx, d)
			defer cancel()
		}
		return inv(ctx, method, req, reply, cc, opts...)
	}
}
```

- Unary and stream interceptors are separate types. Stream interceptors that need the context or per-message hooks wrap `grpc.ServerStream`.
- Order: recovery (convert panics to `INTERNAL`), tracing/metrics, logging, auth, rate limiting, validation. Chained interceptors run first to last on the way in.
- `github.com/grpc-ecosystem/go-grpc-middleware/v2` (v2.3.4 checked) packages recovery, logging, auth, retry, validator and rate-limit interceptors; confirm sub-package names in its README.
- Python: implement `grpc.aio.ServerInterceptor.intercept_service(continuation, handler_call_details)` and pass `interceptors=[...]` to `grpc.aio.server`; client side `grpc.aio.UnaryUnaryClientInterceptor`. The `grpc-interceptor` package (0.15.4) simplifies this.
- Connect: `connect.WithInterceptors(connect.UnaryInterceptorFunc(...))` in Go; `interceptors: [...]` for `createClient` and `ConnectRouter` options in TypeScript.

## 4. Health checking and reflection

```go
import (
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
)

hs := health.NewServer()
healthpb.RegisterHealthServer(s, hs)
hs.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)                 // whole server
hs.SetServingStatus("acme.orders.v1.OrderService", healthpb.HealthCheckResponse_SERVING)
// On shutdown: hs.Shutdown() marks every service NOT_SERVING.

if devMode { reflection.Register(s) } // see security notes
```

- The protocol is `grpc.health.v1.Health` with `Check` (unary) and `Watch` (server streaming). Service name `""` means the process. Python: `grpcio-health-checking` (`health.HealthServicer`, `health.aio.HealthServicer`; verified `Check` returns `SERVING` = 1), Node/Java have equivalents (`grpc-health-check` npm package, `grpc-services` for Java).
- Reflection lets tools discover services without `.proto` files. Python: `grpcio-reflection` and `reflection.enable_server_reflection(service_names, server)` (verified with the `v1alpha` module). Node: `@grpc/reflection` 1.0.4. Connect: `connectrpc.com/grpcreflect`, health via `connectrpc.com/grpchealth`.
- `grpcurl -plaintext host:50051 list` and `describe`; add `-cacert ca.pem`, `-cert client.pem -key client.key` for TLS or mTLS. `buf curl` uses reflection with `--reflect` semantics by default when no schema is given; check `buf curl --help`.
- Reflection exposes the full API: enable only in non-production or behind auth.
- Kubernetes probes: native `grpc:` probes (port and optional service) are supported in current Kubernetes versions; otherwise the `grpc_health_probe` binary. Use readiness for traffic gating and a cheap liveness check that does not depend on downstream services.

## 5. Load balancing

- Policies in grpc-go: `pick_first` (default for most resolvers; one connection) and `round_robin`; select per channel with service config `"loadBalancingConfig": [{"round_robin": {}}]`. Other policies (weighted round robin, ring hash, least request) exist, mostly through xDS; check the library docs.
- Name resolution: `dns:///host:port` returns all A/AAAA records; a Kubernetes headless Service returns pod IPs. DNS results are cached by TTL and re-resolved on connection failure; scale-out is not seen until re-resolution, so combine with server-side `MaxConnectionAge`.
- `passthrough:///` uses the target string as-is (tests, bufconn). `unix:` and `unix-abstract:` targets exist for local sockets.
- xDS: gRPC clients can talk to a control plane directly (target `xds:///service`) and receive endpoints, routes and policies without a sidecar. It needs the xDS bootstrap (`GRPC_XDS_BOOTSTRAP`) and an import of the xds package in Go (`_ "google.golang.org/grpc/xds"`); features vary by language. Check the gRPC xDS docs for supported features.
- Layer 7 proxies (Envoy, Linkerd, Istio) see each RPC and balance per request, which solves the connection pinning of layer 4 balancers. Layer 4 balancers (cloud NLB, kube-proxy) balance connections only.
- For long streams, balancing happens only at stream start; rebalance by closing streams gracefully from the server (`MaxConnectionAge` or a `GOAWAY` on deploy).

## 6. Envoy and other proxies

```yaml
# Envoy route to a gRPC cluster (fragment)
routes:
  - match: { prefix: "/acme.orders.v1.OrderService/" }
    route:
      cluster: orders
      timeout: 5s             # total per-RPC timeout; set 0s for long streams
clusters:
  - name: orders
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options: {}
```

- Cluster must speak HTTP/2 upstream (`http2_protocol_options`). Route `timeout: 0s` disables the route timeout for streaming, with `max_stream_duration` as a cap. Use `grpc_web` and `cors` HTTP filters for browsers, and the gRPC-JSON transcoder filter for REST. Field names change between Envoy versions; verify against the Envoy docs of your version.
- nginx: `grpc_pass grpc://backend;` or `grpcs://`, with `grpc_read_timeout`, `grpc_send_timeout` and `client_max_body_size` tuned for message size (see nginx-expert). HAProxy, Traefik and cloud load balancers need gRPC/HTTP2 end-to-end enabled explicitly.
- Idle timeouts at proxies must exceed client keepalive intervals; otherwise streams die with `UNAVAILABLE` after quiet periods.
- Retries in a proxy and in the client multiply: set the policy in one place.

## 7. Browsers: gRPC-Web and Connect

- Browsers cannot access HTTP/2 framing or trailers, so native gRPC is not available from `fetch`. Options:
  - **Connect protocol** (`createConnectTransport` from `@connectrpc/connect-web`): HTTP POST with JSON or binary bodies; server streaming works over `fetch` streaming; no proxy needed if the server uses Connect (connect-go or connect-es handlers) or an Envoy with the Connect support check.
  - **gRPC-Web** (`createGrpcWebTransport`): needs a server or proxy that speaks gRPC-Web (Envoy `grpc_web` filter, connect-go handlers, grpc-js with a gRPC-Web proxy). Client streaming and bidirectional streaming are not available from browsers in either protocol.
  - Server side with Connect in Node: `connectNodeAdapter({ routes })` on `http2.createServer` (verified: the same handler served the native gRPC client; `createGrpcTransport` from `@connectrpc/connect-node`), or `connect-express` / `connect-fastify` adapters.
- Go servers: mount Connect handlers (`path, handler := ordersv1connect.NewOrderServiceHandler(svc)`) on an `http.ServeMux`; use `golang.org/x/net/http2/h2c` for plaintext HTTP/2 in tests. These handlers accept gRPC clients, gRPC-Web and Connect on the same port.
- CORS: allow only the app origins; expose the headers the protocol uses (`connectrpc.com/cors` helpers list them: Connect, gRPC-Web and trailer headers). Send credentials deliberately.
- Auth for browsers: prefer cookies with `SameSite` and CSRF care, or bearer tokens from the auth flow in `authorization`; do not embed long-lived secrets in client code.
- Generated browser clients: protoc-gen-es (messages and service descriptors) plus Connect; TanStack Query hooks via `@connectrpc/connect-query` (2.3.1 checked).

## 8. REST transcoding

- grpc-gateway (v2.33.0 checked) generates a Go HTTP/JSON reverse proxy from `google.api.http` annotations; run it in the same process or as a sidecar; see buf-codegen.md section 10. It forwards the `authorization` header as gRPC metadata by default and maps gRPC codes to HTTP statuses (`NOT_FOUND` to 404, `INVALID_ARGUMENT` to 400, `UNAVAILABLE` to 503).
- Envoy transcoder and cloud API gateways transcode with a descriptor set. Connect handlers accept JSON POST on `/pkg.Service/Method` with `Content-Type: application/json`, which many "REST-ish" clients can use without gateway code.
- Streaming over REST maps to chunked JSON lines (server streaming only). REST design and versioning: rest-api-expert.

## 9. OpenTelemetry

- Go: `go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc` provides stats handlers (`otelgrpc.NewServerHandler()` for `grpc.StatsHandler(...)` on servers, `NewClientHandler()` with `grpc.WithStatsHandler(...)` on clients); the older interceptors in that package are deprecated in favour of handlers, so prefer handlers and check the package docs. grpc-go also ships a built-in `stats/opentelemetry` package; verify its status in the current grpc-go docs.
- Python: `opentelemetry-instrumentation-grpc` (0.66b2 on PyPI, still a beta version): `GrpcInstrumentorServer().instrument()` and `GrpcInstrumentorClient().instrument()`; async support depends on the version, check its README.
- Node: `@opentelemetry/instrumentation-grpc` targets the legacy `grpc` package and may not cover `@grpc/grpc-js`; check its README and use a Connect interceptor otherwise. Connect: `connectrpc.com/otelconnect` (Go) and `@connectrpc/connect` interceptors for TypeScript.
- Trace context travels as the W3C `traceparent` metadata header; the instrumentation injects and extracts it. Name spans `package.Service/Method` and set `rpc.system=grpc`, `rpc.service`, `rpc.method` and `rpc.grpc.status_code` attributes per the semantic conventions (check the current semconv names).
- Metrics: request rate, duration histogram by method and status code, in-flight streams, message sizes. Cardinality: label by method and code, never by user or request ID.
- Backends, sampling and dashboards: observability-expert.

## 10. Kubernetes notes

- A ClusterIP Service balances TCP connections; a single long-lived HTTP/2 connection sends all RPCs to one pod. Fix with a headless Service plus `dns:///svc.ns.svc.cluster.local:50051` and `round_robin`, a mesh/Envoy, or xDS.
- Set `terminationGracePeriodSeconds` above the server's drain time, flip health to `NOT_SERVING` on SIGTERM, wait a few seconds for endpoints to update, then `GracefulStop`.
- Ingress controllers need explicit gRPC support (backend protocol annotation or Gateway API `GRPCRoute`); check the controller docs. Manifest details: kubernetes-expert.
