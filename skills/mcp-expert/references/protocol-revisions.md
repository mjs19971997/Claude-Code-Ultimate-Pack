# Protocol Revisions and Compatibility

Reference for MCP specification revisions, what changed in 2026-07-28, deprecations, extensions, error codes and era interoperability. Verified against the MCP specification repository (revisions 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28; a `draft` directory also exists and is not a release), Python SDK `mcp` 2.3.x and TypeScript SDK 2.4.x (2026-10).

## 1. Revision timeline

Revisions are identified by date strings. The newest released revision is `2026-07-28`; `draft` accumulates unreleased changes and must not be targeted.

| Revision | Highlights |
|---|---|
| 2024-11-05 | First public revision; stdio and HTTP+SSE transports |
| 2025-03-26 | Streamable HTTP replaces HTTP+SSE; OAuth 2.1 based authorization framework; tool annotations; JSON-RPC batching (removed again in 2025-06-18); audio content; `completions` capability |
| 2025-06-18 | JSON-RPC batching removed; structured tool output; MCP servers classified as OAuth resource servers (RFC 9728); RFC 8707 resource indicators required of clients; elicitation; resource links; `MCP-Protocol-Version` header; `title` fields |
| 2025-11-25 | OpenID Connect discovery for authorization servers; icons; incremental scope consent via `WWW-Authenticate`; tool name guidance; URL-mode elicitation; tool calling in sampling; Client ID Metadata Documents; experimental tasks; JSON Schema 2020-12 as default dialect; input validation errors as tool execution errors |
| 2026-07-28 | Stateless protocol; see section 2 |

## 2. What 2026-07-28 changed

Major changes from 2025-11-25:

1. No protocol-level sessions and no `Mcp-Session-Id`. List endpoints no longer vary per connection. State needed across calls is an explicit server-minted handle passed as an ordinary tool argument.
2. No `initialize` / `notifications/initialized`. Each request carries `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities` in `_meta`; clients SHOULD add `.../clientInfo`; servers SHOULD return `.../serverInfo` in result `_meta`. Version mismatch returns `UnsupportedProtocolVersionError`.
3. `server/discover` (servers MUST implement): supported versions, capabilities, identity, instructions, `ttlMs`, `cacheScope`.
4. `subscriptions/listen` replaces the HTTP GET endpoint and `resources/subscribe` / `resources/unsubscribe`: one long-lived POST response stream; clients opt in to `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`, `resourceSubscriptions`; notifications carry `io.modelcontextprotocol/subscriptionId`. Request-scoped `notifications/progress` and `notifications/message` stay on the originating request's stream.
5. Removed: `ping`, `logging/setLevel`, `notifications/roots/list_changed`. Log level is per request via `io.modelcontextprotocol/logLevel` in `_meta`; servers MUST NOT emit `notifications/message` for requests without it.
6. Tasks moved out of core into the official extension `io.modelcontextprotocol/tasks`: polling with `tasks/get`, `tasks/update` for client-to-server input, no `tasks/result` blocking call, no `tasks/list`.
7. Multi Round-Trip Requests (MRTR) replace server-initiated requests (`roots/list`, `sampling/createMessage`, `elicitation/create`): the server returns an `InputRequiredResult` (`resultType: "input_required"`, `inputRequests`, optional `requestState`), and the client retries the original request with `inputResponses`.
8. Every result carries `resultType`: `"complete"` or `"input_required"`; clients treat a missing field from older servers as `"complete"`.
9. Streamable HTTP: no SSE resumability (`Last-Event-ID`) and no redelivery; a broken stream loses the in-flight request and the client re-issues it with a new id.

Minor changes: `extensions` in client and server capabilities; OpenTelemetry trace context keys (`traceparent`, `tracestate`, `baggage`) in `_meta`; deterministic `tools/list` order recommended; required `Mcp-Method` and `Mcp-Name` headers and optional `x-mcp-header` parameter mirroring; required `ttlMs` and `cacheScope` on list and read results (`CacheableResult`); resource not found is `-32602`; authorization servers SHOULD return `iss` (RFC 9207) and clients MUST validate a present `iss`; clients set `application_type` in Dynamic Client Registration; client credentials are bound to the issuing authorization server; `inputSchema` / `outputSchema` accept any JSON Schema 2020-12 keywords and `structuredContent` may be any JSON value; the URL-mode `notifications/elicitation/complete` and `elicitationId` are removed (the client learns the outcome by retrying; servers needing correlation put an id in `requestState`); error code allocation policy.

## 3. Deprecations (minimum twelve-month window)

| Feature | Since | Migration |
|---|---|---|
| Roots | 2026-07-28 | Pass directories or files via tool parameters, resource URIs or server configuration |
| Sampling (and `includeContext` values `thisServer`/`allServers`, deprecated since 2025-11-25) | 2026-07-28 | Call LLM provider APIs directly; omit `includeContext` or use `none` |
| Logging | 2026-07-28 | stderr (stdio) or OpenTelemetry |
| Dynamic Client Registration (RFC 7591) | 2026-07-28 | Client ID Metadata Documents; DCR stays for compatibility |
| HTTP+SSE transport | 2025-03-26 (reclassified 2026-07-28) | Streamable HTTP |

Deprecated features remain functional during the window but new implementations should not adopt them. No feature has been removed under the policy yet.

## 4. Error codes

JSON-RPC server-error range policy: `-32000` to `-32019` implementation-defined (existing SDK usage grandfathered); `-32020` to `-32099` reserved for the MCP specification.

| Code | Name | When |
|---|---|---|
| `-32020` | `HeaderMismatch` | HTTP headers missing, malformed or inconsistent with the body (HTTP 400) |
| `-32021` | `MissingRequiredClientCapability` | Server needs a client capability (for example elicitation) that the request did not declare |
| `-32022` | `UnsupportedProtocolVersion` | Requested version not supported; `data.supported` lists versions (HTTP 400) |
| `-32601` | Method not found | Unknown RPC method (HTTP 404 on Streamable HTTP) |
| `-32602` | Invalid params | Unknown tool, malformed request, resource not found, invalid or expired `requestState` |
| `-32603` | Internal error | Unexpected server fault (SDKs sanitize the message) |

Tool execution failures are not JSON-RPC errors: they are results with `isError: true`.

## 5. Extensions

Extensions are optional and negotiated through `extensions` in capabilities. Ids use `{vendor-prefix}/{name}`; third parties use a reversed domain they own (`com.example/my-extension`). Stages: Experimental (any change without notice), Beta (breaking changes rare), Stable (fixed within a core revision). Official extensions live in `ext-` repositories under the modelcontextprotocol GitHub organization:

- Authorization (`ext-auth`): OAuth client credentials (machine-to-machine) and enterprise-managed authorization, both Stable at the time of verification.
- MCP Apps (`ext-apps`): servers display interactive UI (charts, forms, video players) inline in conversations; Stable.
- Tasks (`io.modelcontextprotocol/tasks`; Beta, heading to Core at the time of verification): durable long-running work with polling and mid-flight input. The Python 2.x SDK does not implement it yet; check the TypeScript SDK docs and the `ext-tasks` repository before depending on it.
- Skills over MCP (`ext-skills`, Beta) and Server Cards (`ext-server-card`, Beta): discovery of workflow instructions through resources, and HTTP discovery of server metadata before connecting.

Always read the extension's own spec page for its current stage, since stages change independently of core revisions.

## 6. Interoperability between eras

Terms: legacy era = `initialize` handshake (through 2025-11-25); modern era = per-request metadata (2026-07-28 on); dual-era implementations support both.

Client strategy:

- Probe with `server/discover` (stdio) or a modern request (HTTP) first. A recognized modern JSON-RPC error means the server is modern; read `supported` and retry. Any other error, or no answer, means legacy: use `initialize`. Never key the fallback on a single error code, because legacy servers answer unknown pre-initialize requests inconsistently.
- Probing is recommended even for modern-only clients: some legacy servers do not enforce initialization order and would run `tools/call` under legacy semantics.

Server strategy:

- A modern-only HTTP server answers GET and DELETE with `405`, ignores `Mcp-Session-Id` and `Last-Event-ID`, and never mints session ids.
- To serve 2025 clients too, implement the legacy behavior of the corresponding revision. The 2.x SDKs do this for you: the Python `MCPServer` serves both eras (legacy sessions held in one worker's memory unless `stateless_http=True`; sticky routing required otherwise), and TypeScript `createMcpHandler` defaults to `legacy: "stateless"` (each legacy request from a fresh instance, no sessions, no server-initiated requests) with `legacy: "reject"` to refuse 2025 clients with `UnsupportedProtocolVersionError`.
- Feature differences visible to tool authors: on legacy connections `ctx.elicit()` and sampling work as live server requests; on 2026-07-28 connections they fail and MRTR (`Resolve`/`Elicit` in Python, `inputRequired` in TypeScript) is the path. A resolver or `inputRequired` handler works on both.

Choosing a version in client code:

- Python `Client(url)` defaults to `mode="auto"`; `mode="legacy"` forces the 2025 handshake.
- TypeScript `Client` defaults to the legacy handshake unless `versionNegotiation: { mode: "auto" }` (or a pin) is set; `client.getProtocolEra()` reports `"modern"` or `"legacy"`.
- Intermediaries that enforce policy from `Mcp-*` headers should check that `MCP-Protocol-Version` names a version requiring header and body validation and reject older or absent values rather than trusting unvalidated headers.

## 7. Migration checklist from HTTP+SSE and 2025 revisions

1. Replace `/sse` plus `/messages` endpoints with one Streamable HTTP endpoint; keep the old pair only while old clients remain.
2. Remove dependence on `Mcp-Session-Id`, GET streams, resumable SSE and `initialize`; replace implicit session state with explicit handles bound to the authenticated principal.
3. Replace server-initiated elicitation, sampling and roots requests with MRTR; drop reliance on sampling and roots (deprecated).
4. Add `server/discover` support (the SDKs do), `ttlMs` / `cacheScope` on list and read results, and the `Mcp-Method` / `Mcp-Name` header handling if you run your own HTTP layer.
5. Switch client registration to Client ID Metadata Documents; keep DCR only as a fallback.
6. Validate `iss` in authorization responses; keep credentials keyed by issuer.
7. Move to SDK 2.x (Python `mcp` 2.x with `MCPServer`; TypeScript `@modelcontextprotocol/server` / `client`), run the TypeScript codemod, and re-test both eras.
8. Update docs and client configuration snippets with the new URL and auth requirements.
