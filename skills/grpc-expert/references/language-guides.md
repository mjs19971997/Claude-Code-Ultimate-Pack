# Language Guides and Tooling

Runnable gRPC server, client and test code for Go, Python and Node (grpc-js and Connect), and command-line tools (Java notes are in buf-codegen.md). The Go, Python, grpc-js and Connect programs were built from the `acme.orders.v1` schema in SKILL.md and run against grpc-go 1.85.0, protoc-gen-go 1.36.12, protoc-gen-go-grpc 1.6.2, grpcio 1.85.1, @grpc/grpc-js 1.14.7 and @connectrpc/connect 2.3.0 (2026-10).

## Contents

1. [Go server](#1-go-server)
2. [Go client](#2-go-client)
3. [Go tests with bufconn](#3-go-tests-with-bufconn)
4. [Python grpc.aio](#4-python-grpcaio)
5. [Node with grpc-js](#5-node-with-grpc-js)
6. [Node and Go with Connect](#6-node-and-go-with-connect)
7. [grpcurl and buf curl](#7-grpcurl-and-buf-curl)

## 1. Go server

```go
package main

import (
	"context"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/status"

	ordersv1 "example.com/app/gen/acme/orders/v1"
)

type orders struct{ ordersv1.UnimplementedOrderServiceServer }

func (*orders) GetOrder(ctx context.Context, req *ordersv1.GetOrderRequest) (*ordersv1.GetOrderResponse, error) {
	if req.GetId() == "" {
		return nil, status.Error(codes.InvalidArgument, "id is required")
	}
	return &ordersv1.GetOrderResponse{Order: &ordersv1.Order{Id: req.GetId()}}, nil
}

func main() {
	lis, err := net.Listen("tcp", "127.0.0.1:50051")
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer(
		grpc.KeepaliveParams(keepalive.ServerParameters{MaxConnectionIdle: 5 * time.Minute, Time: 2 * time.Minute, Timeout: 20 * time.Second}),
		grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{MinTime: 30 * time.Second}),
	)
	ordersv1.RegisterOrderServiceServer(s, &orders{})
	hs := health.NewServer()
	healthpb.RegisterHealthServer(s, hs)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		hs.Shutdown() // NOT_SERVING for all services
		t := time.AfterFunc(20*time.Second, s.Stop)
		s.GracefulStop()
		t.Stop()
	}()
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
```

- Server streaming handler (protoc-gen-go-grpc 1.6.x signature): `func (*orders) WatchOrders(_ *ordersv1.WatchOrdersRequest, stream grpc.ServerStreamingServer[ordersv1.WatchOrdersResponse]) error`, which loops on `stream.Send` and checks `stream.Context().Err()`; older generated code names the type `OrderService_WatchOrdersServer`.
- Loopback without TLS is for development; add `grpc.Creds(...)` and an interceptor chain (see security-and-deployment.md) for production.

## 2. Go client

```go
const serviceConfig = `{
  "loadBalancingConfig": [{"round_robin": {}}],
  "methodConfig": [{
    "name": [{"service": "acme.orders.v1.OrderService", "method": "GetOrder"}],
    "timeout": "3s",
    "retryPolicy": {
      "maxAttempts": 4, "initialBackoff": "0.1s", "maxBackoff": "2s",
      "backoffMultiplier": 2, "retryableStatusCodes": ["UNAVAILABLE"]
    }
  }]
}`

conn, err := grpc.NewClient("dns:///127.0.0.1:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()), // TLS credentials outside local tests
	grpc.WithDefaultServiceConfig(serviceConfig),
	grpc.WithKeepaliveParams(keepalive.ClientParameters{Time: 30 * time.Second, Timeout: 10 * time.Second}),
)
if err != nil {
	log.Fatal(err)
}
defer conn.Close()
c := ordersv1.NewOrderServiceClient(conn)

ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

resp, err := c.GetOrder(ctx, &ordersv1.GetOrderRequest{Id: "o-1"})
if err != nil {
	log.Fatal(err)
}
log.Println(resp.GetOrder().GetId())
```

- This body goes inside `main`. `grpc.NewClient` does not connect until the first RPC; connection errors surface as `UNAVAILABLE` on the call. Streams: `stream, err := c.WatchOrders(ctx, req)`, then `stream.Recv()` until `io.EOF`.
- With edition 2024 and the Opaque API, use `ordersv1.GetOrderRequest_builder{Id: "o-1"}.Build()` or set `API_HYBRID`.

## 3. Go tests with bufconn

```go
func newTestClient(t *testing.T, impl ordersv1.OrderServiceServer, opts ...grpc.DialOption) ordersv1.OrderServiceClient {
	t.Helper()
	lis := bufconn.Listen(1 << 20)
	s := grpc.NewServer()
	ordersv1.RegisterOrderServiceServer(s, impl)
	go func() { _ = s.Serve(lis) }()
	t.Cleanup(s.Stop)

	opts = append([]grpc.DialOption{
		grpc.WithContextDialer(func(ctx context.Context, _ string) (net.Conn, error) { return lis.DialContext(ctx) }),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	}, opts...)
	conn, err := grpc.NewClient("passthrough:///bufnet", opts...)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = conn.Close() })
	return ordersv1.NewOrderServiceClient(conn)
}
```

- Retry test: a `flaky` server embedding `UnimplementedOrderServiceServer` whose `GetOrder` returns `codes.Unavailable` while an `atomic.Int32` counter is at most 2. Pass the service config from section 2 with `grpc.WithDefaultServiceConfig(cfg)` (use short backoffs in tests) and assert `f.calls.Load() == 3` after one client call. Also test deadline expiry: a handler waiting on `ctx.Done()` and a 50 ms client timeout give `codes.DeadlineExceeded`.

## 4. Python grpc.aio

```python
import asyncio
import grpc
from acme.orders.v1 import orders_pb2, orders_pb2_grpc


class Orders(orders_pb2_grpc.OrderServiceServicer):
    async def GetOrder(self, request, context):
        if not request.id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "id is required")
        return orders_pb2.GetOrderResponse(order=orders_pb2.Order(id=request.id))

    async def WatchOrders(self, request, context):
        for i in range(3):
            yield orders_pb2.WatchOrdersResponse(order=orders_pb2.Order(id=str(i)))


async def serve() -> None:
    server = grpc.aio.server(options=[("grpc.max_receive_message_length", 4 * 1024 * 1024)])
    orders_pb2_grpc.add_OrderServiceServicer_to_server(Orders(), server)
    server.add_insecure_port("127.0.0.1:50051")  # add_secure_port in production
    await server.start()
    await server.wait_for_termination()
```

- Run with `asyncio.run(serve())`; blocking calls in `async def` handlers stall the loop (use `asyncio.to_thread`). Stop gracefully with `await server.stop(grace=5)`. Sync servicers use `grpc.server(ThreadPoolExecutor(max_workers=N))`, where `max_workers` bounds concurrent RPCs.
- Plain exceptions become `UNKNOWN`; call `context.abort(...)`. Run with `PYTHONPATH=gen` so generated package imports resolve.

## 5. Node with grpc-js

```js
import grpc from "@grpc/grpc-js";
import protoLoader from "@grpc/proto-loader";

const def = protoLoader.loadSync("proto/acme/orders/v1/orders.proto", { keepCase: true, defaults: true });
const pkg = grpc.loadPackageDefinition(def).acme.orders.v1;

const server = new grpc.Server();
server.addService(pkg.OrderService.service, {
  getOrder(call, callback) {
    if (!call.request.id) {
      return callback({ code: grpc.status.INVALID_ARGUMENT, message: "id is required" });
    }
    callback(null, { order: { id: call.request.id } });
  },
});
server.bindAsync("127.0.0.1:50051", grpc.ServerCredentials.createInsecure(), (err) => { if (err) throw err; });

const client = new pkg.OrderService("127.0.0.1:50051", grpc.credentials.createInsecure());
client.getOrder({ id: "o-1" }, { deadline: Date.now() + 2000 }, (err, res) => {
  console.log(err ? `${err.code} ${err.details}` : res.order.id);
});
```

- This ran against a proto3 copy of the schema. `@grpc/proto-loader` 0.8.1 parses with protobufjs: check whether it accepts `edition = "2023"` files before relying on them, and use the Buf stack (section 6) for edition schemas.
- The server starts once `bindAsync` succeeds (the old `server.start()` is deprecated; check release notes). Share clients per target and call `client.close()` at shutdown; `call.cancel()` abandons a stream.

## 6. Node and Go with Connect

Node, with code from `protoc-gen-es` v2 for the same schema:

```ts
import http2 from "node:http2";
import { Code, ConnectError, createClient } from "@connectrpc/connect";
import { connectNodeAdapter, createGrpcTransport } from "@connectrpc/connect-node";
import { OrderService } from "./gen/acme/orders/v1/orders_pb.js";

const server = http2.createServer(
  connectNodeAdapter({
    routes: (router) =>
      router.service(OrderService, {
        async getOrder(req) {
          if (!req.id) throw new ConnectError("id required", Code.InvalidArgument);
          return { order: { id: req.id } };
        },
        async *watchOrders() {
          for (let i = 0; i < 3; i++) yield { order: { id: String(i) } };
        },
      }),
  }),
);
server.listen(8080, "127.0.0.1");

const client = createClient(OrderService, createGrpcTransport({ baseUrl: "http://127.0.0.1:8080" }));
const res = await client.getOrder({ id: "o-1" }, { timeoutMs: 2000 });
for await (const msg of client.watchOrders({})) console.log(msg.order?.id);
```

- Swap in `createConnectTransport` (`connect-node` or `connect-web`) or `createGrpcWebTransport` (`connect-web`) to use the other protocols against the same handler. `createRouterTransport(routes)` from `@connectrpc/connect` gives in-memory tests with no sockets. A handler error arrived at the client as `ConnectError` with `Code.InvalidArgument`.
- Go: `connectrpc.com/connect` (v1.21.1) with `protoc-gen-connect-go` generates `NewOrderServiceHandler(svc, opts...)` returning `(path, http.Handler)` for an `http.ServeMux`; serve with TLS (HTTP/2 via ALPN) or `h2c`. Errors are `connect.NewError(connect.CodeNotFound, err)`; check the docs for generated names under the Opaque API.

## 7. grpcurl and buf curl

```bash
grpcurl -plaintext 127.0.0.1:50051 list        # needs reflection, -proto or -protoset
grpcurl -plaintext -d '{"id":"o-1"}' 127.0.0.1:50051 acme.orders.v1.OrderService/GetOrder
grpcurl -cacert ca.pem -cert client.pem -key client.key -H "authorization: Bearer $TOKEN" \
  orders.internal:8443 acme.orders.v1.OrderService/GetOrder
buf curl --protocol grpc --data '{"id":"o-1"}' \
  http://127.0.0.1:50051/acme.orders.v1.OrderService/GetOrder
```

- Take `TOKEN` from a secret store; keep real tokens out of shell history.
- `buf curl` (1.74.0 and later) enables HTTP/2 prior knowledge for `http` URLs when reflection, the gRPC protocol or a bidirectional streaming method is used.
- Without reflection, `grpcurl` needs `-import-path proto -proto acme/orders/v1/orders.proto` or `-protoset descriptor.binpb` from `buf build -o descriptor.binpb`.
