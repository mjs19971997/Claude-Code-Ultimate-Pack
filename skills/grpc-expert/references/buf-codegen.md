# Buf CLI and Code Generation

Buf configuration (v2), lint and breaking checks, generation templates for Go, Python, Node and Java, grpc-gateway and OpenAPI, CI wiring and the Buf Schema Registry. Commands and configs were run with buf 1.75.0 installed from npm (`@bufbuild/buf`), protoc-gen-go 1.36.12, protoc-gen-go-grpc 1.6.2, protoc-gen-es 2.16.0 and grpcio-tools 1.85.1 (2026-10). Remote plugin and BSR commands need network access to buf.build and were not run.

## Contents

1. [Installing and pinning](#1-installing-and-pinning)
2. [buf.yaml v2](#2-bufyaml-v2)
3. [Lint](#3-lint)
4. [Breaking change detection](#4-breaking-change-detection)
5. [buf.gen.yaml v2](#5-bufgenyaml-v2)
6. [Go](#6-go)
7. [Python](#7-python)
8. [Node and TypeScript](#8-node-and-typescript)
9. [Java](#9-java)
10. [grpc-gateway and OpenAPI](#10-grpc-gateway-and-openapi)
11. [CI and BSR](#11-ci-and-bsr)

## 1. Installing and pinning

- Install Buf from the GitHub release binary, a package manager, or npm (`npm install --save-dev @bufbuild/buf`, which gives `npx buf`). Pin the version in the repository (package.json, a tool file or CI) so lint results do not change under you. Latest checked: 1.75.0.
- `buf --version`, `buf config init` (writes a starting `buf.yaml`), `buf config ls-lint-rules`, `buf config ls-breaking-rules`, `buf ls-files` help to inspect what is active.
- Local plugins must be on `PATH`: `go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.12` and `go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.6.2` (install into a pinned `GOBIN`). Note that a recent grpc-go may require a recent Go toolchain; Go downloads one automatically when `GOTOOLCHAIN=auto`.
- Buf also offers remote plugins on the BSR (`remote: buf.build/protocolbuffers/go`); they remove local installs but need network access and pin a plugin version in the reference.

## 2. buf.yaml v2

```yaml
version: v2
modules:
  - path: proto
    name: buf.build/acme/orders   # only needed when pushing to the BSR
deps:
  - buf.build/googleapis/googleapis
  - buf.build/bufbuild/protovalidate
lint:
  use:
    - STANDARD
  except:
    - PACKAGE_VERSION_SUFFIX     # example only; prefer fixing the schema
  enum_zero_value_suffix: _UNSPECIFIED
  service_suffix: Service
  disallow_comment_ignores: false
breaking:
  use:
    - FILE
```

- `version: v2` is the current config version (written by `buf config init` in 1.75.0). One `buf.yaml` at the repository root declares every module under `modules:`; v1 had one file per module.
- A module path is the import root: with `path: proto`, the file `proto/acme/orders/v1/orders.proto` is imported as `acme/orders/v1/orders.proto`.
- Run `buf dep update` after changing `deps:` to write `buf.lock`; commit both. Dependencies are fetched from the BSR.
- With no `modules:` entry, Buf treats the repository root as the module; `inputs: - directory: proto` then fails with "contained by module at path .". Declare `modules: - path: proto` (checked with 1.75.0) and the same input works. `--path` on `buf generate` or `buf lint` limits work to a file or directory.
- `buf format -w` rewrites files in place; `buf format --diff --exit-code` fails CI when formatting differs.

## 3. Lint

- Categories (from `buf config ls-lint-rules`): MINIMAL, BASIC, STANDARD (default for new configs), COMMENTS, UNARY_RPC. `STANDARD` includes naming, package layout, enum zero value, service suffix and request/response naming rules.
- Useful rules: `ENUM_VALUE_PREFIX`, `ENUM_ZERO_VALUE_SUFFIX`, `FIELD_LOWER_SNAKE_CASE`, `PACKAGE_VERSION_SUFFIX`, `PACKAGE_DIRECTORY_MATCH`, `RPC_REQUEST_RESPONSE_UNIQUE`, `RPC_REQUEST_STANDARD_NAME`, `SERVICE_SUFFIX`, `PROTOVALIDATE`. Add `COMMENTS` when public docs are required; add `UNARY_RPC` to forbid streaming in a module.
- Suppress one finding with a comment `// buf:lint:ignore RULE_ID` above the element, or `ignore_only:` in `buf.yaml` for path-based exceptions. Every suppression needs a reason in the commit.
- Output formats via `--error-format`: `text`, `json`, `msvs`, `junit`, `github-actions`, `gitlab-code-quality`, `config-ignore-yaml` (prints ignore config for existing violations when adopting lint on a legacy repo).
- `buf lint --path proto/acme/orders/v1` lints a subset; the command exits non-zero on findings.

## 4. Breaking change detection

```bash
# Against the main branch of this repository
buf breaking --against '.git#branch=main'

# Against a subdirectory module in another ref
buf breaking --against '.git#branch=main,subdir=proto'

# Against a published BSR module
buf breaking --against 'buf.build/acme/orders'
```

- Categories (from `buf config ls-breaking-rules`): `FILE` (default; generated source stability), `PACKAGE` (per package), `WIRE_JSON` (binary and JSON), `WIRE` (binary only). A rule belongs to several categories; picking `FILE` includes the others' checks.
- A local run deleting `string id = 1` from `GetOrderRequest` printed: `Previously present field "1" with name "id" on message "GetOrderRequest" was deleted.`
- `buf breaking` needs a baseline: in CI fetch full history (`fetch-depth: 0`) or compare with an image (`buf build -o baseline.binpb` on main, then `--against baseline.binpb`).
- Add `ignore_unstable_packages: true` under `breaking:` to skip packages whose version suffix is unstable (`v1alpha1`, `v1beta1`, `v1test`).
- Breaking checks run on the schema only. They do not catch semantic changes (a field now means seconds instead of milliseconds); review those by hand.

## 5. buf.gen.yaml v2

```yaml
version: v2
clean: true                      # delete plugin output dirs before generating
managed:
  enabled: true
  disable:
    - file_option: go_package
      module: buf.build/googleapis/googleapis
  override:
    - file_option: go_package_prefix
      value: example.com/acme/gen/go
plugins:
  - local: protoc-gen-go
    out: gen/go
    opt: paths=source_relative
  - local: protoc-gen-go-grpc
    out: gen/go
    opt: paths=source_relative
  - local: protoc-gen-es
    out: gen/ts
    opt: target=ts
inputs:
  - directory: proto
```

- `version: v2` replaces v1's `version: v1` templates; plugins are a list with `remote:`, `local:` or `protoc_builtin:` as the source, plus `out`, `opt`, `include_imports`, `include_wkt`, `strategy`.
- Managed mode sets file options (`go_package_prefix`, `java_package_prefix`, `java_multiple_files`, `csharp_namespace`, `objc_class_prefix` and others) at generation time, so `.proto` files stay free of per-language options. `disable:` and `override:` take a `file_option`, `module` or `path`. Buf 1.75.0 skips `cc_enable_arenas` for edition 2026 files.
- `inputs:` may be a `directory`, `git_repo`, `module`, `proto_file` or `tarball`; override at the command line with `buf generate path/or/ref`.
- Run: `buf generate` (reads `buf.gen.yaml`) or `buf generate --template buf.gen.tools.yaml`. Use `--path proto/acme/orders` to regenerate one package.
- Commit generated code or generate in CI/build; pick one policy per repository and document it. If committed, run `buf generate && git diff --exit-code` in CI.

## 6. Go

- Plugins: `protoc-gen-go` (messages, from `google.golang.org/protobuf`) and `protoc-gen-go-grpc` (services, from `google.golang.org/grpc/cmd/protoc-gen-go-grpc`, a separate module). Both options `paths=source_relative` place files next to the schema path.
- `protoc-gen-go-grpc` options include `require_unimplemented_servers` (default true: servers must embed `UnimplementedXServer`). Generated service code is `_grpc.pb.go`; messages `.pb.go`.
- Edition 2024 files generate the Opaque API by default; see proto-design-evolution.md section 3 for `API_HYBRID`.
- Runtime dependencies in `go.mod`: `google.golang.org/grpc`, `google.golang.org/protobuf`, and for rich errors `google.golang.org/genproto/googleapis/rpc`. Run `go mod tidy`.
- Connect for Go uses a different plugin, `protoc-gen-connect-go` from `connectrpc.com/connect`, producing `connectrpc` handlers beside the messages; it serves gRPC, gRPC-Web and the Connect protocol from one handler (connect-go 1.21.1 checked).

## 7. Python

```bash
python -m pip install grpcio grpcio-tools protobuf
python -m grpc_tools.protoc -I proto \
  --python_out=gen --pyi_out=gen --grpc_python_out=gen \
  proto/acme/orders/v1/orders.proto
```

- `grpcio-tools` bundles a protoc, so no system protoc is needed; the versions checked were grpcio and grpcio-tools 1.85.1 with protobuf 7.36.2. It supports editions up to 2024 in that release.
- Output is `orders_pb2.py`, `orders_pb2.pyi` (type stubs) and `orders_pb2_grpc.py`. The generated gRPC file imports `orders_pb2` with a package-relative path derived from the `-I` root; keep `__init__.py` files or add the output to `sys.path`.
- With Buf, either call `python -m grpc_tools.protoc` from a Makefile (simple, verified above) or use BSR remote plugins for Python messages and gRPC stubs; check the BSR plugin pages for current names and versions before pinning.
- Add `grpcio-status`, `grpcio-health-checking` and `grpcio-reflection` for rich errors, health and reflection. Async servers use `grpc.aio`.

## 8. Node and TypeScript

- Two stacks: `@grpc/grpc-js` with `@grpc/proto-loader` (runtime loading, optional `proto-loader-gen-types` for types), and Bufbuild: `@bufbuild/protobuf` with `@bufbuild/protoc-gen-es` for messages and descriptors plus `@connectrpc/connect` for clients and servers (versions checked: 2.16.0 and 2.3.0).
- protoc-gen-es v2 emits one `_pb` file per proto with message types and service descriptors; there is no separate `protoc-gen-connect-es` in v2. Options: `target=ts`, `target=js`, `target=js+dts`, `import_extension=js`.
- Connect clients: `createClient(Service, transport)` with `createConnectTransport` (browser or Node), `createGrpcWebTransport` (browser), or `createGrpcTransport` (Node, native gRPC over HTTP/2).
- Package list checked on npm: `@connectrpc/connect-node`, `@connectrpc/connect-web`, `@connectrpc/connect-express`, `@connectrpc/connect-fastify`, `@connectrpc/connect-query` (TanStack Query hooks), `@grpc/reflection` 1.0.4.
- `@grpc/proto-loader` 0.8.1 parses with protobufjs; check its editions support before feeding it edition files, and use proto3 or the Buf stack otherwise.

## 9. Java

- Use the Maven or Gradle protobuf plugin, or Buf with `buf.build/protocolbuffers/java` and `buf.build/grpc/java` remote plugins (names to confirm on the BSR). Runtime artifacts: `io.grpc:grpc-netty-shaded` (or `grpc-netty`), `grpc-protobuf`, `grpc-stub`, plus `grpc-services` for health and reflection.
- grpc-java releases track the grpc core version (1.85.1 was the latest tag seen); align `grpc-bom` versions and protobuf-java with the protoc used.
- Server: `ServerBuilder.forPort(p).addService(new OrdersImpl()).build().start()`; `OrdersImpl extends OrderServiceGrpc.OrderServiceImplBase`; call `responseObserver.onNext(...)` then `onCompleted()`, or `onError(Status.NOT_FOUND.withDescription("...").asRuntimeException())`.
- Spring Boot gRPC starters exist; see java-spring-expert for Spring specifics.

## 10. grpc-gateway and OpenAPI

```proto
import "google/api/annotations.proto";

service OrderService {
  rpc GetOrder(GetOrderRequest) returns (GetOrderResponse) {
    option (google.api.http) = { get: "/v1/orders/{id}" };
  }
  rpc CreateOrder(CreateOrderRequest) returns (CreateOrderResponse) {
    option (google.api.http) = { post: "/v1/orders" body: "*" };
  }
}
```

```yaml
# buf.gen.gateway.yaml (plugins from github.com/grpc-ecosystem/grpc-gateway/v2)
version: v2
plugins:
  - local: protoc-gen-grpc-gateway
    out: gen/go
    opt: [paths=source_relative, generate_unbound_methods=false]
  - local: protoc-gen-openapiv2
    out: gen/openapi
```

- Add `buf.build/googleapis/googleapis` to `deps:` for `google/api/annotations.proto`.
- Gateway (v2.33.0 checked): a Go reverse proxy generated from the annotations that translates JSON/REST to gRPC calls in process (`RegisterOrderServiceHandlerFromEndpoint`) or through a connection. `body: "*"` maps the whole request body; path variables bind to request fields.
- Alternatives: Envoy's gRPC-JSON transcoder filter (descriptor set built with `buf build -o descriptor.binpb` and `--as-file-descriptor-set`), and Connect, which serves JSON POST natively but not REST URLs. REST API conventions: rest-api-expert.
- Generated OpenAPI covers the REST surface only; do not treat it as a complete description of gRPC.

## 11. CI and BSR

```yaml
# GitHub Actions job body (no untrusted expressions in run steps)
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0
  - uses: bufbuild/buf-action@v1
    with:
      version: "1.75.0"
```

- Or run explicit commands: `buf format --diff --exit-code`, `buf lint --error-format github-actions`, `buf breaking --against '.git#branch=main'`, `buf generate`, then `git diff --exit-code` when output is committed. Check the current docs for the buf-action inputs before relying on them.
- BSR (Buf Schema Registry, buf.build): host modules, `buf push` publishes a module (needs `name:` in `buf.yaml` and a token in `BUF_TOKEN`, stored as a CI secret), `buf dep update` consumes them, generated SDKs let consumers install packages instead of running generators, and remote plugins run server side. Private registries and organisations need an account; check the BSR docs for the current limits.
- `buf curl` calls gRPC, gRPC-Web and Connect endpoints using reflection or a local schema; `buf convert` converts between binary, JSON and text; `buf registry login` stores credentials (prefer `BUF_TOKEN` in CI).
- A language server is available as `buf lsp`; editor integrations use it for diagnostics and formatting.
