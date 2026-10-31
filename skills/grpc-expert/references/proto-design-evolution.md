# Protocol Buffers Design and Evolution

Schema design for gRPC APIs: proto3 versus Editions, features, field presence, enums, oneof, field numbers and reserved ranges, wire compatibility, naming, API shape and validation. Edition behaviour below was checked against descriptor.proto on main and by compiling with buf 1.75.0, protoc-gen-go 1.36.12, protoc-gen-es 2.16.0 and grpcio-tools 1.85.1 (2026-10).

## Contents

1. [proto3 versus Editions](#1-proto3-versus-editions)
2. [Features in edition 2023](#2-features-in-edition-2023)
3. [Editions 2024 and 2026](#3-editions-2024-and-2026)
4. [Field presence and wrappers](#4-field-presence-and-wrappers)
5. [Enums](#5-enums)
6. [Field numbers and reserved](#6-field-numbers-and-reserved)
7. [Compatibility rules](#7-compatibility-rules)
8. [oneof, map, repeated, Any](#8-oneof-map-repeated-any)
9. [Well-known types](#9-well-known-types)
10. [API shape](#10-api-shape)
11. [Validation](#11-validation)

## 1. proto3 versus Editions

```proto
// proto3
syntax = "proto3";
package acme.orders.v1;

// Edition 2023
edition = "2023";
package acme.orders.v1;
```

- A file has exactly one of `syntax = "proto2"`, `syntax = "proto3"` or `edition = "..."`, and it comes before `package`.
- Editions replace the language-level proto2/proto3 split with named behaviours called features. An edition sets defaults for all features; a file, message, field, enum or service overrides them with `option features.<name> = VALUE;` or inline `[features.<name> = VALUE]`.
- Released editions per descriptor.proto on main: 2023, 2024, 2026. Older syntax remains supported; proto3 is still the lowest-risk choice for a pipeline with many consumers.
- Choose an edition only after a compile test with every generator and tool in the pipeline (protoc or buf, language plugins, gateway, validator, documentation generators). In the 2026-10 check: edition 2023 and 2024 worked with buf 1.75.0, protoc-gen-go 1.36.12, protoc-gen-go-grpc 1.6.2, protoc-gen-es 2.16.0 and grpcio-tools 1.85.1; edition 2026 compiled in buf 1.75.0 but was rejected by the Go protobuf runtime ("not yet supported") and by grpcio-tools ("later than the maximum supported edition 2024").
- Migration: No converter was verified here; check the protobuf.dev editions pages for the current migration tool. Manual migration: replace the syntax line, add `option features.field_presence = IMPLICIT;` to keep proto3 presence, delete `optional` labels (explicit presence is the default), and turn string `reserved` names into identifiers.

## 2. Features in edition 2023

Defaults, read from the `edition_defaults` in descriptor.proto:

| Feature | proto3 value | edition 2023 value | Notes |
|---|---|---|---|
| `field_presence` | `IMPLICIT` | `EXPLICIT` | Others: `LEGACY_REQUIRED` (avoid). Scalars become pointers in Go under explicit presence |
| `enum_type` | `OPEN` | `OPEN` | `CLOSED` makes unknown values go to unknown fields (proto2 behaviour); avoid for evolving enums |
| `repeated_field_encoding` | `PACKED` | `PACKED` | `EXPANDED` for compatibility with old readers |
| `utf8_validation` | `VERIFY` | `VERIFY` | `NONE` skips validation on strings |
| `message_encoding` | `LENGTH_PREFIXED` | `LENGTH_PREFIXED` | `DELIMITED` replaces proto2 groups |
| `json_format` | `ALLOW` | `ALLOW` | `LEGACY_BEST_EFFORT` is the proto2 behaviour |

```proto
edition = "2023";

package acme.catalog.v1;

// Keep proto3 presence for the whole file.
option features.field_presence = IMPLICIT;

message Product {
  string id = 1;
  // This one tracks presence even though the file default is IMPLICIT.
  int32 stock = 2 [features.field_presence = EXPLICIT];
}
```

- There is no `optional` or `required` label in editions; presence is a feature.
- `reserved` names in editions are bare identifiers: `reserved legacy_total;`. A string literal fails with "cannot use string literals in reserved range in editions mode" (seen in buf 1.75.0).
- Language-specific features are separate extensions. Go: `import "google/protobuf/go_features.proto";` then `option features.(pb.go).api_level = API_HYBRID;`. Check the current docs of each plugin before depending on other language features.

## 3. Editions 2024 and 2026

From descriptor.proto and a local compile:

- Edition 2024 adds symbol visibility for imports: feature `default_symbol_visibility` (`EXPORT_ALL`, `EXPORT_TOP_LEVEL`, `LOCAL_ALL`, `STRICT`), default `EXPORT_TOP_LEVEL` in 2024 and `STRICT` in 2026. The `export` and `local` modifiers override per symbol. Visibility affects what other files may import, not generated code.
- Edition 2024 adds a naming style feature (`STYLE2024`, `STYLE2026` defaults) and `import option` for option-only dependencies (buf 1.75.0 added image support for it).
- Edition 2026 adds protoc-level limit enforcement (`PROTO_LIMITS2026`) and removes the `cc_enable_arenas` option.
- Go effect: protoc-gen-go uses the Opaque API by default for edition 2024. Generated structs have a hidden state field and `xxx_hidden_` members, so `&pb.Order{Id: "x"}` fails to compile; use `pb.Order_builder{Id: "x"}.Build()` or setters (`SetId`). Add `option features.(pb.go).api_level = API_HYBRID;` to get both field access and accessors (verified: compiles with literal construction and `GetId()`).
- Treat 2026 as not usable for gRPC services until Go, Python, Java and TypeScript generators advertise support; recheck release notes of each.

## 4. Field presence and wrappers

- Implicit presence (proto3 default): a scalar equal to its zero value is not serialized and cannot be told from unset. Fine for most fields.
- Explicit presence: proto3 `optional string note = 3;` or edition `EXPLICIT`. Generated code exposes has-methods (`HasNote()` in Go under hybrid or opaque, `HasField("note")` in Python, `note !== undefined` in protobuf-es) or pointer fields in Go's open struct API.
- Message-typed fields always have presence. Use a message when "unset" has to be distinct from "empty".
- Wrappers (`google.protobuf.StringValue`, `Int32Value`, `BoolValue`) predate proto3 `optional`. They add a message allocation and JSON `null` mapping. Prefer explicit presence for new fields; keep wrappers when an existing schema uses them.
- Partial updates: use `google.protobuf.FieldMask` plus the resource, not a pile of optional fields. Document the mask paths and whether an empty mask is an error.
- `oneof` members have presence by definition and are the right tool for "exactly one of".

## 5. Enums

```proto
enum OrderStatus {
  ORDER_STATUS_UNSPECIFIED = 0;
  ORDER_STATUS_PENDING = 1;
  ORDER_STATUS_SHIPPED = 2;
  reserved 3;
  reserved ORDER_STATUS_LOST;
}
```

- Value 0 is `<ENUM_NAME>_UNSPECIFIED` (Buf lint `ENUM_ZERO_VALUE_SUFFIX`, suffix configurable with `enum_zero_value_suffix`). It is the default of an unset field; handlers should reject it where a value is required.
- Prefix values with the enum name (`ENUM_VALUE_PREFIX`) because enum values are scoped to the enclosing package, not the enum, in C++-style scoping.
- Keep enums open (default in proto3 and edition 2023): a new server value reaches an old client as an integer, not a parse failure. Handle unknown values with a default branch.
- Never reuse removed value numbers or names; `reserved` them. `allow_alias` makes two names share a number and complicates JSON; avoid.
- Do not turn booleans into enums later: a field type change is breaking. Use an enum when more than two states are plausible.

## 6. Field numbers and reserved

- Numbers 1-15 take one byte of tag; put frequently set fields there. 16-2047 take two. Valid range 1 to 536,870,911, excluding 19000-19999 (reserved by the implementation).
- Never reuse a number, even years later: stored data and old clients still carry it.
- When deleting a field: `reserved 4;` and `reserved legacy_total;` (the name matters for JSON and text formats and for Buf's `FIELD_NO_DELETE_UNLESS_*_RESERVED` breaking rules).
- Do not renumber to "tidy" a message. Gaps are normal.
- Extensions (`extend`) are discouraged outside of options; use `oneof`, `Any` or a new message.

## 7. Compatibility rules

Wire compatible type groups (a change within a group decodes, with truncation or sign pitfalls):

| Group | Types |
|---|---|
| Varint | `int32`, `uint32`, `int64`, `uint64`, `bool` (values are truncated or widened) |
| Zigzag varint | `sint32`, `sint64` |
| Fixed 32 | `fixed32`, `sfixed32` |
| Fixed 64 | `fixed64`, `sfixed64` |
| Length-delimited | `string` and `bytes` (only if the bytes are valid UTF-8), a message and `bytes` containing it |

| Change | Wire | JSON | Generated source |
|---|---|---|---|
| Add a field | safe | safe | safe |
| Add an enum value | safe (open enums) | safe | switch statements may need a default |
| Add an RPC | safe | safe | clients unaffected; servers with `Unimplemented` embedding compile |
| Remove a field (reserve it) | safe | safe | breaks code that reads it |
| Rename a field | safe | breaks | breaks |
| Rename a message or enum | safe (unless in `Any`) | safe | breaks; also changes `Any` type URLs |
| Change a field number | breaks | breaks | breaks |
| Change a field type outside its group | breaks | breaks | breaks |
| Move a field into or out of a `oneof` | breaks for out of a multi-member oneof | check | breaks |
| Change `repeated` to singular or back | breaks (packed encoding aside) | breaks | breaks |
| Change package | breaks wire (method path changes) | breaks | breaks |
| Rename a service or RPC | breaks (the path `/pkg.Service/Method` changes) | breaks | breaks |

- Buf categories map to the contract: `FILE` (generated source stability, the default), `PACKAGE`, `WIRE_JSON` (binary and JSON), `WIRE` (binary only). Pick the strictest that matches who depends on you.
- Unknown fields are preserved by proto3 parsers in current libraries, which keeps middle services from dropping data; do not rely on it when a proxy re-encodes through a different schema version.
- Default values: do not change a default in a new version of a proto2-style default; implicit defaults are fixed by the type.

## 8. oneof, map, repeated, Any

- `oneof payload { A a = 1; B b = 2; }`: at most one is set; setting one clears the others. Adding a field to an existing oneof is safe; moving an existing field into a oneof is wire-breaking in some cases.
- `map<string, Item> items = 5;`: keys can be integral or string types (not floats, bytes, enums or messages); iteration order is undefined; maps cannot be `repeated`; map entries are encoded as a repeated message, so a large map is not compact.
- `repeated` scalars are packed by default in proto3 and edition 2023; parsers accept both forms. Order is preserved.
- `google.protobuf.Any` carries a typed message by URL (`type.googleapis.com/acme.orders.v1.Order`); the receiver needs the type linked in. Use it for error details and plugin payloads, not as a general escape hatch.
- Avoid deep nesting and very large repeated fields in one message: the default receive limit is 4 MiB in most libraries and parse depth limits exist (100 in many implementations).

## 9. Well-known types

| Type | Use |
|---|---|
| `google.protobuf.Timestamp` | Instants (UTC seconds and nanos); JSON is RFC 3339 |
| `google.protobuf.Duration` | Spans of time; JSON is `"3.5s"` |
| `google.protobuf.FieldMask` | Partial updates and field selection |
| `google.protobuf.Struct` / `Value` | Schemaless JSON-like data; use sparingly |
| `google.protobuf.Empty` | Avoid for RPC signatures; define `FooRequest {}` and `FooResponse {}` so they can grow |
| `google.type.Date`, `Money`, `LatLng` | In googleapis (`buf.build/googleapis/googleapis`); decimal and money types avoid float rounding |
| `google.rpc.Status` and `errdetails` | Error model; see errors-deadlines-retries.md |

- Represent money as integer minor units plus currency code, or `google.type.Money`; never `double`.
- IDs: opaque `string` unless arithmetic is meaningful. 64-bit integers appear as JSON strings in the canonical proto3 JSON mapping, which surprises JavaScript consumers using plain `JSON.parse`.

## 10. API shape

- Name services after a noun with the `Service` suffix and package version: `acme.orders.v1.OrderService`. Method names are verbs: `GetOrder`, `ListOrders`, `CreateOrder`, `UpdateOrder`, `DeleteOrder`; custom verbs after a colon in REST terms become `CancelOrder`.
- Request messages are `<Method>Request`, responses `<Method>Response`, in the same file or package (Buf `RPC_REQUEST_STANDARD_NAME`, `RPC_RESPONSE_STANDARD_NAME`, `RPC_REQUEST_RESPONSE_UNIQUE`). Buf lint option `rpc_allow_same_request_response` and similar exist but weaken this rule.
- List methods: `page_size`, `page_token`, optional `filter` and `order_by` as strings with documented grammar; responses return `next_page_token`. Cap `page_size` on the server.
- Create methods take the resource plus a client-chosen `request_id` (UUID) when retries are possible, and the server stores it to make the call idempotent.
- Use resource names (`orders/123`) as strings in `name` fields if following Google AIP; otherwise a plain `id`. Pick one style per API.
- Keep read and write models separate when they diverge; do not expose database rows as messages.
- Stream messages should be small and self-describing; define an end condition (server closes the stream with OK).
- Document the status codes each method returns in the comment above it.

## 11. Validation

- Declare constraints in the schema with protovalidate (`buf.validate` options, CEL-based) so every language enforces the same rules. Packages seen on registries in 2026-10: Go `buf.build/go/protovalidate` v1.4.0, Python `protovalidate` 2.1.0, npm `@bufbuild/protovalidate` 1.3.0; check the docs of each for the current API.
- Add the dependency in `buf.yaml` (`deps: - buf.build/bufbuild/protovalidate`) and run `buf dep update`; import `buf/validate/validate.proto` in the schema.
- Enforce in an interceptor (Go: community interceptor modules, for Connect `connectrpc.com/validate`) and map violations to `INVALID_ARGUMENT` with a `BadRequest` detail.
- Buf lint has a `PROTOVALIDATE` rule that checks protovalidate constraints compile; run `buf lint` in CI.
- Validation in the schema is documentation too; do not duplicate the same limits as free-form comments that drift.
