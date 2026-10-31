# Errors, Deadlines, Retries and Flow Control

Status codes, rich error details, deadlines and cancellation, retry and hedging configuration, keepalive, message limits and streaming behaviour. Go, Python and Connect code was compiled and run against grpc-go 1.85.0, grpcio 1.85.1 and connect-node 2.3.0 (2026-10); service config field names follow the gRPC retry design (gRFC A6) and should be rechecked in the current docs when a library is upgraded.

## Contents

1. [Status codes](#1-status-codes)
2. [Rich error details in Go](#2-rich-error-details-in-go)
3. [Rich error details in Python and Node](#3-rich-error-details-in-python-and-node)
4. [Deadlines and cancellation](#4-deadlines-and-cancellation)
5. [Retries and hedging](#5-retries-and-hedging)
6. [Keepalive and connection lifetime](#6-keepalive-and-connection-lifetime)
7. [Message size and flow control](#7-message-size-and-flow-control)
8. [Streaming patterns](#8-streaming-patterns)

## 1. Status codes

| Code | Number | Use when | Retry |
|---|---|---|---|
| `OK` | 0 | Success | - |
| `CANCELLED` | 1 | Caller cancelled | No |
| `UNKNOWN` | 2 | Unmapped error from another system | Rarely |
| `INVALID_ARGUMENT` | 3 | Bad input regardless of state | No |
| `DEADLINE_EXCEEDED` | 4 | Deadline passed (may have succeeded server side) | Only if idempotent |
| `NOT_FOUND` | 5 | Entity missing | No |
| `ALREADY_EXISTS` | 6 | Create conflicts | No |
| `PERMISSION_DENIED` | 7 | Authenticated but not allowed | No |
| `RESOURCE_EXHAUSTED` | 8 | Quota, rate limit, message too large | With backoff, honour `RetryInfo` |
| `FAILED_PRECONDITION` | 9 | System not in required state (non-empty dir, stale version) | After the state is fixed |
| `ABORTED` | 10 | Concurrency conflict (transaction abort) | At a higher level |
| `OUT_OF_RANGE` | 11 | Past the end (page, offset) | No |
| `UNIMPLEMENTED` | 12 | Method not implemented or not enabled | No |
| `INTERNAL` | 13 | Invariant broken, server bug | No |
| `UNAVAILABLE` | 14 | Transient, server down or connection lost | Yes, with backoff |
| `DATA_LOSS` | 15 | Unrecoverable data loss or corruption | No |
| `UNAUTHENTICATED` | 16 | Missing or invalid credentials | After re-auth |

- gRPC errors are not HTTP statuses: the HTTP status is 200 with `grpc-status` and `grpc-message` in the trailers. Proxy errors before the application can look different (a 502 maps to `UNAVAILABLE`).
- Choose `FAILED_PRECONDITION` versus `ABORTED` versus `UNAVAILABLE` by who can retry: `UNAVAILABLE` retry the same call; `ABORTED` retry the higher-level transaction; `FAILED_PRECONDITION` fix state first.
- Messages are for developers: short, no stack traces, no secrets, no PII. Put machine-readable data in details.
- Map domain errors once, at the edge, e.g. `ErrNotFound -> codes.NotFound`, with `errors.Is`. Unmapped errors become `INTERNAL`, logged with the real cause.
- A client library may generate `CANCELLED`, `DEADLINE_EXCEEDED` or `UNAVAILABLE` on its own. A handler should not return `DEADLINE_EXCEEDED` for its own downstream timeout unless it means exactly that; `UNAVAILABLE` or `INTERNAL` is clearer for the caller.

## 2. Rich error details in Go

```go
import (
	"time"

	"google.golang.org/genproto/googleapis/rpc/errdetails"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/durationpb"
)

func quotaError() error {
	st := status.New(codes.ResourceExhausted, "rate limit exceeded")
	st, err := st.WithDetails(
		&errdetails.ErrorInfo{
			Reason: "RATE_LIMIT_EXCEEDED",
			Domain: "orders.acme.example",
			Metadata: map[string]string{"limit": "100/min"},
		},
		&errdetails.RetryInfo{RetryDelay: durationpb.New(2 * time.Second)},
	)
	if err != nil {
		return status.Error(codes.Internal, "build error details")
	}
	return st.Err()
}
```

Client side:

```go
st := status.Convert(err)          // never nil; non-status errors become UNKNOWN
for _, d := range st.Details() {   // returns []any, with error values for undecodable details
	switch v := d.(type) {
	case *errdetails.BadRequest:
		for _, fv := range v.GetFieldViolations() {
			log.Printf("field %s: %s", fv.GetField(), fv.GetDescription())
		}
	case *errdetails.RetryInfo:
		delay := v.GetRetryDelay().AsDuration()
		_ = delay
	}
}
```

- Standard detail types in `google.rpc.errdetails` (package `google.golang.org/genproto/googleapis/rpc/errdetails`): `ErrorInfo` (stable reason code, domain, metadata; the preferred machine-readable field), `BadRequest` (field violations), `RetryInfo`, `QuotaFailure`, `PreconditionFailure`, `ResourceInfo`, `RequestInfo`, `DebugInfo` (internal only, never send to untrusted clients), `Help`, `LocalizedMessage`.
- Details travel in the `grpc-status-details-bin` trailer. Proxies and clients must preserve trailers; the size counts against the header limit (often 8 KiB to 16 KiB), so keep details small.
- Clients must tolerate details they cannot decode (type not linked in): the `Details()` slice contains an error value for those.
- Use one `ErrorInfo.Reason` per business error in `UPPER_SNAKE_CASE`; clients branch on it, not on message text.

## 3. Rich error details in Python and Node

Python (`grpcio-status`, `googleapis-common-protos`), verified with `grpc.aio`:

```python
from google.protobuf import any_pb2
from google.rpc import code_pb2, error_details_pb2, status_pb2
from grpc_status import rpc_status

# server handler (async)
detail = any_pb2.Any()
detail.Pack(error_details_pb2.BadRequest(field_violations=[
    error_details_pb2.BadRequest.FieldViolation(field="id", description="required"),
]))
await context.abort_with_status(rpc_status.to_status(
    status_pb2.Status(code=code_pb2.INVALID_ARGUMENT, message="bad request", details=[detail])
))

# client
try:
    await stub.GetOrder(request, timeout=2)
except grpc.aio.AioRpcError as e:
    st = rpc_status.from_call(e)           # google.rpc.Status or None
    if st and st.details[0].Is(error_details_pb2.BadRequest.DESCRIPTOR):
        ...
```

- Plain errors: `await context.abort(grpc.StatusCode.NOT_FOUND, "order not found")`. `abort` raises, so code after it does not run.
- Node with Connect: `throw new ConnectError("id required", Code.InvalidArgument, undefined, [ { desc: BadRequestSchema, value: {...} } ])` attaches details; clients read `ConnectError.from(e).findDetails(BadRequestSchema)`. Details need the message schemas from `@bufbuild/protobuf`'s generated googleapis types; check the current Connect docs for the exact import. The `ConnectError.code` check (`Code.InvalidArgument`) was verified.
- Node with grpc-js: callbacks take `{ code: grpc.status.NOT_FOUND, message: "..." }`, optionally with a `metadata` object for trailers; rich details require encoding `google.rpc.Status` into `grpc-status-details-bin` yourself, so prefer Connect or a helper library for this.

## 4. Deadlines and cancellation

- A deadline is an absolute point in time; clients express it as a timeout, and the library sends the remaining time as `grpc-timeout`. Every layer should shrink it, never extend it.
- Go client: `ctx, cancel := context.WithTimeout(ctx, 2*time.Second); defer cancel()`. Server handler: `ctx` has the deadline; `ctx.Done()` fires on cancel or expiry. Passing `ctx` to a downstream call propagates cancellation and the remaining time (Go does not forward `grpc-timeout` metadata by itself, it derives a new timeout from the context).
- Python: `stub.Method(req, timeout=2.0)` (seconds); in handlers `context.time_remaining()` and `context.cancelled()` (sync) or task cancellation (aio: the handler coroutine receives `asyncio.CancelledError`).
- Node grpc-js: `client.getOrder(req, { deadline: Date.now() + 2000 }, cb)` or `{ deadline: new Date(...) }`; Connect: `{ timeoutMs: 2000 }` per call, or `defaultTimeoutMs` on the transport.
- A default deadline per method can be set in service config `timeout`; per-call values replace it (the smaller of the two applies in the retry design).
- Cancelling the context of a client stream resets the stream; the server's `Recv` or `Send` returns an error with `CANCELLED`. Always `cancel()` streams you stop reading, or the stream stays open.
- On the server, loops over large data should check `ctx.Err()` every iteration or batch. Database and HTTP clients must receive the same `ctx`.
- Work that must outlive the request (audit log, async job) gets a detached context with its own timeout: `context.WithoutCancel(ctx)` (Go 1.21+) keeps values but drops cancellation.
- Budget deadlines across hops: if the edge allows 2 seconds and the service calls two backends sequentially, give each less than 1 second or run them in parallel. Do not set the same timeout at every hop.

## 5. Retries and hedging

Service config (JSON) is supplied by the resolver (DNS TXT or xDS) or locally; the Go option is `grpc.WithDefaultServiceConfig(json)`, Python passes `("grpc.service_config", json)` as a channel option, grpc-js uses `"grpc.service_config"` in channel options.

```json
{
  "loadBalancingConfig": [{ "round_robin": {} }],
  "methodConfig": [
    {
      "name": [{ "service": "acme.orders.v1.OrderService", "method": "GetOrder" }],
      "timeout": "3s",
      "waitForReady": false,
      "retryPolicy": {
        "maxAttempts": 4,
        "initialBackoff": "0.1s",
        "maxBackoff": "2s",
        "backoffMultiplier": 2,
        "retryableStatusCodes": ["UNAVAILABLE"]
      }
    }
  ],
  "retryThrottling": { "maxTokens": 10, "tokenRatio": 0.1 }
}
```

- `name` entries without `method` apply to a whole service; an empty object `{}` is the default for all methods.
- `maxAttempts` counts the original call and is capped by the client (5 in the design); `initialBackoff` and `maxBackoff` are strings with an `s` suffix; delay is randomised between 0 and the current backoff. `retryableStatusCodes` uses names such as `UNAVAILABLE`.
- `retryThrottling` is a client-wide token bucket: failures drain tokens, successes refill by `tokenRatio`, and retries stop when tokens drop to half of `maxTokens`. It protects a struggling backend.
- An RPC is committed, and no longer retried, once response headers arrive, when a non-retryable status is returned, or when the retry buffer limit is exceeded. A server can slow or stop retries with the `grpc-retry-pushback-ms` trailer metadata.
- Separate from policy retries, libraries do transparent retry for RPCs that never left the client or were refused by the server.
- Hedging uses `hedgingPolicy` (`maxAttempts`, `hedgingDelay`, `nonFatalStatusCodes`) and sends parallel copies of an idempotent call. Not every language implements it; check the implementation status in the library docs before relying on it. A method has either `retryPolicy` or `hedgingPolicy`.
- Retries multiply load: set `maxAttempts` to 2-4, add throttling, make methods idempotent and use a `request_id` in create calls. Application-level retries (a loop around the stub) must respect the same deadline as the parent call.
- Do not retry `DEADLINE_EXCEEDED` through service config; the budget is already spent.
- Connect: no built-in retry policy in service config terms; add retry in an interceptor or at the HTTP client layer.

## 6. Keepalive and connection lifetime

```go
// Client (Go)
grpc.WithKeepaliveParams(keepalive.ClientParameters{
	Time:                30 * time.Second, // ping after this much inactivity
	Timeout:             10 * time.Second, // wait for the ack
	PermitWithoutStream: false,            // only ping when RPCs are active
})

// Server (Go)
grpc.KeepaliveParams(keepalive.ServerParameters{
	MaxConnectionIdle:     5 * time.Minute,
	MaxConnectionAge:      30 * time.Minute,
	MaxConnectionAgeGrace: 30 * time.Second,
	Time:                  2 * time.Minute,
	Timeout:               20 * time.Second,
})
grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
	MinTime:             20 * time.Second, // reject client pings faster than this
	PermitWithoutStream: false,
})
```

- If a client pings more often than the server's `MinTime` (default 5 minutes in grpc-go), the server sends `GOAWAY` with `too_many_pings` and the connection resets; keep the client `Time` at or above the server's `MinTime`.
- Keepalive detects dead connections behind NAT and load balancers that drop idle flows; set the client `Time` below the shortest idle timeout on the path (cloud LBs often use 60 to 350 seconds).
- `MaxConnectionAge` makes servers close connections after a time, which rebalances clients after scale-out; clients reconnect and the `GracefulStop` semantics let in-flight RPCs finish within the grace period.
- C-core libraries (Python) use channel args: `grpc.keepalive_time_ms`, `grpc.keepalive_timeout_ms`, `grpc.keepalive_permit_without_calls`, `grpc.http2.max_pings_without_data`; grpc-js uses the same `grpc.*` keys. Confirm names for your version.
- Client-side reconnect backoff and `waitForReady` control behaviour while a server is down: without `waitForReady`, calls fail fast with `UNAVAILABLE` in TRANSIENT_FAILURE; with it they wait until the deadline.

## 7. Message size and flow control

- Default max receive size is 4 MiB in grpc-go, grpc-java and the C-core libraries; grpc-go's default max send is effectively unlimited. Exceeding it yields `RESOURCE_EXHAUSTED` on the receiving side.
- Go: `grpc.MaxRecvMsgSize(n)` and `grpc.MaxSendMsgSize(n)` on servers, `grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(n))` on clients. Python: `("grpc.max_receive_message_length", n)` and `("grpc.max_send_message_length", n)`. grpc-js: the same `grpc.*` option names.
- Proxies have their own limits (Envoy buffer limits, ingress body size); raising the gRPC limit alone is not enough.
- HTTP/2 flow control windows throttle senders: a slow reader blocks `Send` after the window is full. Never ignore a slow consumer by buffering unboundedly; let `Send` block or drop with an explicit policy.
- Large payloads: chunk into messages of 16 KiB to 1 MiB with a header message first, or use object storage with signed URLs. Compression (`grpc.UseCompressor(gzip.Name)`, client `grpc.UseCompressor` call option) trades CPU for bytes.
- `MAX_CONCURRENT_STREAMS` bounds simultaneous RPCs per connection (servers advertise it, default 100 in many stacks, effectively unlimited in grpc-go unless `grpc.MaxConcurrentStreams` is set). When reached, new RPCs queue on the client, which looks like latency, not errors.

## 8. Streaming patterns

- Server streaming: the handler loops with `stream.Send`; return `nil` to finish OK, or a status error. Check `stream.Context().Done()` between sends.
- Client streaming: the handler calls `stream.Recv()` until `io.EOF`, then `stream.SendAndClose(resp)`. Enforce a maximum count or bytes so a client cannot stream forever.
- Bidirectional: use one goroutine to read and one to write; the handler returns when both are done. In Go, never call `Send` concurrently from two goroutines on the same stream (it is not safe); `Recv` and `Send` may run in different goroutines. Return from the handler to end the stream.
- Client: after the last `Send`, call `CloseSend()`; keep reading until `io.EOF`; then check the error. Cancel the context to abandon.
- Heartbeats: for long idle watches send a periodic message or rely on keepalive pings so proxies do not drop the stream.
- Resumption: include a resume token (offset, version) in the stream request so a reconnect after `UNAVAILABLE` continues without gaps.
- Ordering: messages on one stream are ordered; there is no ordering across streams.
- Backpressure: `Send` returns when the message is queued for transport, not when the peer processed it; use application acks when delivery confirmation matters.
- Streams are not durable queues. If messages must survive restarts, use a broker (kafka-messaging-expert).
