# Transports and Authorization

Reference for MCP transports, HTTP security, the authorization flow and the SDK authorization APIs. Verified against MCP specification revision 2026-07-28, Python SDK `mcp` 2.3.x and TypeScript SDK `@modelcontextprotocol/server` 2.4.x with `@modelcontextprotocol/express` 2.0.x and `@modelcontextprotocol/node` 2.1.x (2026-10). MUST, SHOULD and MAY below follow the specification's usage.

## 1. Transport overview

Two standard transports exist; custom transports are allowed if they keep the JSON-RPC format, message patterns and per-request metadata model. Over a reliable byte stream (Unix socket, TCP) reuse the stdio framing.

| Transport | Use | Status |
|---|---|---|
| stdio | Host launches the server as a subprocess | Standard |
| Streamable HTTP | Remote or shared servers | Standard (since 2025-03-26) |
| HTTP+SSE (2024-11-05: `/sse` + `/messages`) | Old clients only | Deprecated; eligible for removal |

Protocol semantics are identical on every transport. Servers never send JSON-RPC requests (see MRTR); clients never send JSON-RPC responses. Websocket transports are not part of the specification.

## 2. stdio

- The client launches the server; the server reads JSON-RPC from stdin and writes to stdout, one message per line with no embedded newlines, UTF-8.
- Nothing except valid MCP messages may be written to stdout. Logging goes to stderr; clients may capture, forward or ignore it and must not treat stderr as an error signal.
- Request metadata lives in the message body (`_meta`); there is no header layer.
- Cancellation: client sends `notifications/cancelled` with the request id.
- Shutdown: the client closes the server's stdin and waits; servers should exit promptly on stdin EOF; forced termination (SIGTERM then SIGKILL on POSIX) only as a fallback.
- If the server dies, the client may restart it; because the protocol is stateless, in-flight requests are retried and `subscriptions/listen` streams re-established.
- Authorization: stdio servers should not use the HTTP authorization flow; take credentials from the environment, scoped per server.
- Python SDK: stdout is the wire; the SDK diverts flushed writes to stderr while serving, but output flushed before serving starts (or buffered prints drained at exit) can still corrupt the stream. Use `logging`.
- TypeScript: `serveStdio(() => server)` from `@modelcontextprotocol/server/stdio`; client side `StdioClientTransport` from `@modelcontextprotocol/client/stdio`.

## 3. Streamable HTTP (2026-07-28)

Shape:

- One MCP endpoint path (for example `https://example.com/mcp`) that accepts POST. The client sends every request or notification as its own POST with `Accept` listing both `application/json` and `text/event-stream`.
- The server answers a request with either `application/json` (single object) or `text/event-stream` (an SSE stream scoped to that request carrying related notifications then the final response). A notification POST returns `202 Accepted`.
- Servers MUST NOT send independent JSON-RPC requests on the stream. Asking the client for input uses `InputRequiredResult` and a client retry.
- Closing the response stream cancels the request; `notifications/cancelled` is not used over HTTP.
- Long-lived change notifications arrive on the response stream of a `subscriptions/listen` request. Keep it alive with SSE comment lines. SSE resumability (`Last-Event-ID`) is not supported: a broken stream loses the in-flight request and the client re-issues it with a new id.
- Servers SHOULD send `X-Accel-Buffering: no` on SSE responses so proxies do not buffer.
- Removed relative to 2025-11-25: `Mcp-Session-Id`, DELETE to end sessions, the GET stream endpoint, server requests on streams, resumability. A modern-only server should answer GET or DELETE with `405`, ignore `Mcp-Session-Id` and `Last-Event-ID`.

Required request headers on every POST:

| Header | Value | Failure |
|---|---|---|
| `MCP-Protocol-Version` | must equal `_meta["io.modelcontextprotocol/protocolVersion"]` | `400` `HeaderMismatch` (-32020); unsupported version returns `400` `UnsupportedProtocolVersionError` (-32022) with `data.supported` |
| `Mcp-Method` | the JSON-RPC `method` | `400` `HeaderMismatch` |
| `Mcp-Name` | `params.name` (tools, prompts) or `params.uri` (resources/read) on `tools/call`, `resources/read`, `prompts/get` | `400` `HeaderMismatch`; non-ASCII values use the Base64 sentinel encoding |

Servers MUST reject requests whose headers disagree with the body (so a gateway routing on headers and a server executing on the body cannot be played against each other). An unknown method returns `404` with JSON-RPC `-32601`.

Optional custom headers: a tool parameter schema may carry `"x-mcp-header": "Region"`, and the client then mirrors the value into `Mcp-Param-Region`. Only integer, string and boolean parameters qualify, names must be valid HTTP tokens and unique case-insensitively, and sensitive values must not be annotated.

Example modern request:

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: get_weather
Authorization: Bearer <access-token>

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_weather","arguments":{"location":"Seattle, WA"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"ExampleClient","version":"1.0.0"},"io.modelcontextprotocol/clientCapabilities":{}}}}
```

Era detection for clients that speak both eras: send a modern request or `server/discover` first. A `400` with a recognized modern JSON-RPC error means the server is modern (retry with a supported version, do not fall back). Any other error or no response means legacy: fall back to `initialize`. Do not key the fallback on one specific error code.

## 4. HTTP security rules

- Validate the `Origin` header on all connections; if present and invalid respond `403 Forbidden` (DNS rebinding defense).
- Local servers should bind `127.0.0.1`, not `0.0.0.0`, and should still authenticate.
- Terminate TLS in front of non-local servers; all authorization server endpoints must be HTTPS and redirect URIs must be `localhost` or HTTPS.
- Python: with no `transport_security=`, the app only accepts Host `127.0.0.1:<port>`, `localhost:<port>`, `[::1]:<port>` and a matching Origin; a deployment under another hostname gets `421 Invalid Host header` until allowlisted. `host="mcp.example.com"` does not allowlist the name; it only stops the localhost default from arming protection.

```python
from mcp.server.transport_security import TransportSecuritySettings

app = mcp.streamable_http_app(
    transport_security=TransportSecuritySettings(
        allowed_hosts=["mcp.example.com", "mcp.example.com:*"],
        allowed_origins=["https://app.example.com"],  # only matters for browser clients
    )
)
```

- TypeScript: `createMcpExpressApp()` / `createMcpHonoApp()` / `createMcpFastifyApp()` arm Host and Origin checks for localhost binds; when binding all interfaces pass `allowedHosts` (and `allowedOrigins`, starting from `localhostAllowedOrigins()` if you want to keep the defaults). `createMcpHandler` itself validates no Host, Origin or token: mount checks in front of it. On plain `node:http`, compose `localhostHostValidation()` and `localhostOriginValidation()` and listen on `127.0.0.1`.
- Behind a TLS-terminating proxy, make the ASGI server trust forwarded headers (`uvicorn server:app --proxy-headers --forwarded-allow-ips='<proxy address>'`) or redirects point at `http://` and clients refuse them.

## 5. Authorization overview

Authorization is optional and applies to HTTP transports. The model:

- The MCP server is an OAuth 2.1 resource server (based on OAuth 2.1 draft-13, RFC 6750 bearer tokens, RFC 8414 AS metadata, RFC 8707 resource indicators, RFC 9728 protected resource metadata, RFC 9207 issuer identification, OAuth Client ID Metadata Documents, OpenID Connect Discovery).
- The MCP client is an OAuth 2.1 client. The authorization server issues tokens and may be hosted separately; its implementation is out of scope.

Flow:

1. Client sends an MCP request without a token; server returns `401` with `WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource", scope="files:read"`.
2. Client fetches Protected Resource Metadata (RFC 9728). The document MUST contain `authorization_servers` (at least one). If the header has no `resource_metadata`, the client probes `/.well-known/oauth-protected-resource/<mcp-path>` then `/.well-known/oauth-protected-resource`.
3. Client discovers AS metadata, trying in order (for an issuer with a path): OAuth path insertion, OIDC path insertion, OIDC path appending; for an issuer without a path: `oauth-authorization-server` then `openid-configuration`. The metadata `issuer` MUST equal the issuer used to build the URL. Clients MUST refuse to proceed if `code_challenge_methods_supported` is absent (no PKCE support).
4. Client obtains a client id (section 6), records the issuer, generates PKCE (`S256`), and sends the user to the authorization endpoint with `resource=<canonical MCP server URI>` (RFC 8707) and scopes chosen by the strategy below.
5. Authorization response includes `iss` (RFC 9207). The client compares it with the recorded issuer by exact string comparison before redeeming the code, rejecting mismatches; if the AS advertises `authorization_response_iss_parameter_supported: true` and `iss` is absent, reject. On mismatch do not display `error` fields.
6. Token request includes `code_verifier` and `resource`. The client then sends `Authorization: Bearer <token>` on every MCP request; tokens MUST NOT go in the query string.

Canonical server URI examples: `https://mcp.example.com/mcp`, `https://mcp.example.com:8443`; invalid: a bare hostname or a URI with a fragment. Prefer no trailing slash unless significant. Clients MUST send `resource` whether or not the AS supports it.

Scope selection: use the `scope` from the initial `WWW-Authenticate` challenge, else all `scopes_supported` from the metadata, else omit. Keep `scopes_supported` minimal and do not advertise `offline_access`.

## 6. Client registration

Priority for clients that support all options: pre-registered credentials, then Client ID Metadata Documents (if the AS metadata says `client_id_metadata_document_supported`), then Dynamic Client Registration (deprecated, kept for compatibility, only if `registration_endpoint` exists), then prompt the user.

- Client ID Metadata Document: the `client_id` is an HTTPS URL with a path (for example `https://app.example.com/oauth/client-metadata.json`) whose JSON includes at least `client_id` (identical to the URL), `client_name`, `redirect_uris`. The AS fetches and validates it, checks redirect URIs exactly, caches per HTTP headers, and must guard against SSRF. Localhost redirect URIs cannot prove identity: AS should warn and display the redirect host.
- Client credentials are bound to the issuing authorization server: key persisted credentials by issuer, never reuse them with another AS, and re-register when the AS changes.
- Clients must set an appropriate `application_type` during Dynamic Client Registration.

## 7. Server-side token handling

Resource server obligations:

- Validate every token on every request (OAuth 2.1 section 5.2): signature, expiry, issuer and audience. Tokens MUST have been issued for this MCP server as audience (RFC 8707). Reject others with `401`.
- MCP servers MUST NOT accept or pass through tokens issued for other resources. When calling an upstream API, act as an OAuth client of that API and use a separate token.
- Errors: `401` for missing or invalid tokens (always with a `WWW-Authenticate` challenge that points to the metadata), `403` for insufficient permissions, `400` for malformed authorization requests.
- Runtime step-up: respond `403` with `WWW-Authenticate: Bearer error="insufficient_scope", scope="files:write", resource_metadata="...", error_description="..."`. Include all scopes needed for the operation in one challenge. Servers account for scope hierarchies.
- Clients re-authorize with the union of previously granted scopes and the challenged scopes, retry a limited number of times, and treat repeated failure as permanent.
- Refresh tokens: clients keep them confidential and must not assume they will be issued; authorization servers rotate refresh tokens for public clients; servers should issue short-lived access tokens.

## 8. SDK authorization APIs

Python (resource server half; the authorization server is a separate product):

```python
from pydantic import AnyHttpUrl
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

RESOURCE = "https://mcp.example.com/mcp"


class Verifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        info = await introspect(token)  # your code: RFC 7662 introspection or JWT validation
        if info is None or not info.active or RESOURCE not in info.audiences:
            return None
        return AccessToken(token=token, client_id=info.client_id, scopes=info.scopes,
                           expires_at=info.exp, resource=RESOURCE)


mcp = MCPServer(
    "Notes",
    token_verifier=Verifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl(RESOURCE),
        required_scopes=["notes:read"],
        validate_token_resource=True,
    ),
)


@mcp.tool()
def whoami() -> str:
    """Report which client is calling."""
    token = get_access_token()  # None on stdio, in-memory tests, or unauthenticated requests
    return "anonymous" if token is None else f"{token.client_id} ({', '.join(token.scopes)})"
```

- `token_verifier=` and `auth=` must be passed together. The SDK serves `/.well-known/oauth-protected-resource/mcp` (RFC 9728 metadata with `resource`, `authorization_servers`, `scopes_supported`) and answers unauthenticated requests with `401` and `WWW-Authenticate` including `resource_metadata`.
- `validate_token_resource=True` rejects tokens whose `AccessToken.resource` differs from `resource_server_url`; use it when the AS binds tokens to the requested `resource`. If your AS uses its own audience identifiers, check `aud` in the verifier and return `None` otherwise. Leaving it unset while `resource_server_url` is set warns and behaves as `False`.
- Do not use `auth_server_provider=` for new servers (it embeds an authorization server).
- Client side: `OAuthClientProvider` is an `httpx2.Auth` attached to the HTTP client of the Streamable HTTP transport; supply `client_metadata`, a `TokenStorage` (persist tokens, for example in the OS keyring), and redirect and callback handlers. Identity-assertion and client-credentials flows exist for machine callers.
- Per-tool scope rules: read `get_access_token().scopes` and refuse; raise or return an error for insufficient scope.

TypeScript:

```typescript
import { createMcpExpressApp, getOAuthProtectedResourceMetadataUrl, mcpAuthMetadataRouter, requireBearerAuth } from "@modelcontextprotocol/express";
import { toNodeHandler } from "@modelcontextprotocol/node";
import type { AuthInfo } from "@modelcontextprotocol/server";
import { createMcpHandler, requireScopes } from "@modelcontextprotocol/server";

const mcpServerUrl = new URL("https://api.example.com/mcp");

async function verifyAccessToken(token: string): Promise<AuthInfo> {
  const payload = await verifyJwt(token); // your code: signature, issuer, exp
  const audience = [payload.aud ?? []].flat().find(a => URL.canParse(a) && new URL(a).origin === mcpServerUrl.origin);
  return { token, clientId: payload.sub, scopes: payload.scopes, expiresAt: payload.exp, resource: audience ? new URL(audience) : undefined };
}

const auth = requireBearerAuth({
  verifier: { verifyAccessToken },
  requiredScopes: ["mcp"],
  resourceMetadataUrl: getOAuthProtectedResourceMetadataUrl(mcpServerUrl),
  expectedResource: mcpServerUrl
});

const app = createMcpExpressApp({ host: "0.0.0.0", allowedHosts: ["api.example.com"] });
app.use(mcpAuthMetadataRouter({ oauthMetadata, resourceServerUrl: mcpServerUrl }));
app.all("/mcp", auth, (req, res) => void toNodeHandler(createMcpHandler(buildServer))(req, res, req.body));
```

- Throw `OAuthError` with `OAuthErrorCode.InvalidToken` to reject a token (becomes `401`); other exceptions return `500`. `requireBearerAuth` answers `401 invalid_token` for a token whose `expiresAt` is unset, so always populate it.
- `expectedResource` makes the gate accept only tokens whose `AuthInfo.resource` matches. `@modelcontextprotocol/express` 2.0.1 did not forward that option (nothing is compared); upgrade it together with `@modelcontextprotocol/server` and confirm the installed version accepts it.
- Handlers read the caller as `ctx.http?.authInfo` (undefined on stdio). Per-operation step-up uses `scopeChallenge: requireScopes("notes:write")` on `registerTool`, `registerResource` and `registerPrompt`, or a callback that computes required scopes from the request.
- On web-standard hosts (Workers, Deno, Bun, Hono) use `requireBearerAuth` from `@modelcontextprotocol/server` as `const result = await gate(request)`; pass the resulting `AuthInfo` to `handler.fetch(request, { authInfo })`; `oauthMetadataResponse` serves the metadata documents.
- Authorization server helpers (`mcpAuthRouter`, `ProxyOAuthServerProvider`) are frozen in `@modelcontextprotocol/server-legacy/auth`; use a dedicated identity provider for new servers.

## 9. Security checklist (from the specification and best-practices guide)

- **Confused deputy**: proxy servers with a static client id at a third-party AS must get user consent for each dynamically registered client before forwarding, and must validate redirect URIs exactly.
- **Token passthrough**: forbidden. It defeats audience-based controls, rate limiting and audit.
- **SSRF in clients**: when fetching metadata URLs from a possibly malicious server, require HTTPS (loopback excepted in development), block private, loopback and link-local ranges (including cloud metadata addresses) with a vetted library rather than hand-written IP parsing, validate each redirect hop, pin DNS results between check and use, and consider an egress proxy.
- **State handle hijacking**: handles must be unguessable, expiring, and bound to the verified principal (for example key state by `<user_id>:<handle>` with the user id from the token).
- **Local server compromise**: show the exact command before one-click installation; sandbox servers; restrict filesystem and network.
- **Authorization URL validation**: clients allow only `http`/`https` authorization URLs (http only for loopback in development), reject `javascript:`, `data:`, `file:` and similar schemes, and open URLs without a shell.
- **Mix-up attacks**: record the issuer and check `iss`.
- **Scope minimization**: minimal initial scopes, progressive step-up, one challenge per operation.
- **Token theft**: short-lived access tokens, secure storage, rotation of refresh tokens for public clients, no tokens in logs.
