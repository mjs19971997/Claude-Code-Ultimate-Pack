---
name: mcp-expert
description: >-
  Builds, secures and debugs Model Context Protocol servers and clients: tools, resources, prompts, structured tool output, elicitation and multi round-trip requests, the stdio and Streamable HTTP transports, OAuth 2.1 based authorization, extensions, and the official SDKs (Python `mcp` 2.x with `MCPServer`, TypeScript `@modelcontextprotocol/server` and `client` 2.x, legacy 1.x). Use when writing or reviewing an MCP server or client, choosing a transport, adding authorization, migrating from HTTP+SSE or from protocol revisions before 2026-07-28, or hardening against tool poisoning, token passthrough and DNS rebinding. Not for calling the Claude API itself (use anthropic-sdk-expert), agent system design (use ai-agent-architect), or generic login and token design (use authentication-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# MCP Expert

This skill covers the Model Context Protocol (MCP): the wire protocol and its revisions, server features (tools, resources, prompts), client features (elicitation), transports, authorization, security, and the official Python and TypeScript SDKs. The current revision is stateless: there is no `initialize` handshake and no protocol-level session, so tutorials written for 2025 revisions (HTTP+SSE, `Mcp-Session-Id`, `FastMCP`, `StreamableHTTPServerTransport`) are out of date.

> Verified against MCP specification revision 2026-07-28 (newest; previous 2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05), Python SDK `mcp` 2.3.x, TypeScript SDK `@modelcontextprotocol/server` and `@modelcontextprotocol/client` 2.4.x, legacy `@modelcontextprotocol/sdk` 1.32.x (2026-10).

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

- Covered: protocol revisions and compatibility, JSON-RPC message shape and `_meta`, `server/discover`, tools (schemas, annotations, structured content, errors), resources and URI templates, prompts, completion, pagination and caching hints, progress and cancellation, `subscriptions/listen`, elicitation and multi round-trip requests (MRTR), stdio and Streamable HTTP, OAuth-based authorization, extensions (tasks, MCP Apps, authorization extensions), SDK usage, MCP security, testing with the in-memory client and the Inspector.
- Not covered: calling Claude with the MCP connector parameter (anthropic-sdk-expert), agent framework design (ai-agent-architect), general OAuth provider operation (authentication-expert, authorization-expert), HTTP API design unrelated to MCP (rest-api-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Revisions | Dated: `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`, `2026-07-28` (newest). "Legacy era" = `initialize` handshake (through 2025-11-25); "modern era" = per-request metadata (2026-07-28 on). SDKs serve both |
| Stateless core | No `initialize`/`initialized`, no `Mcp-Session-Id`, no GET stream. Every request carries `_meta` keys `io.modelcontextprotocol/protocolVersion` and `.../clientCapabilities` (and SHOULD carry `.../clientInfo`). Unsupported version returns `UnsupportedProtocolVersionError` listing `supported` versions |
| Discovery | Servers MUST implement `server/discover` (supported versions, capabilities, identity, `ttlMs`, `cacheScope`). Clients MAY call it first or invoke any method inline |
| Transports | `stdio` (newline-delimited JSON-RPC, subprocess) and Streamable HTTP (single endpoint, every message a POST, response is JSON or an SSE stream scoped to that request). HTTP+SSE (2024-11-05) is Deprecated; do not build on it |
| HTTP headers | POSTs MUST carry `MCP-Protocol-Version`, `Mcp-Method`, and `Mcp-Name` (for `tools/call`, `resources/read`, `prompts/get`); a mismatch with the body returns 400 `HeaderMismatch`. Tool params can opt into `Mcp-Param-*` headers via `x-mcp-header` |
| Server features | Tools (model-controlled), resources (application-controlled, URI-addressed), prompts (user-controlled), completion, logging (deprecated), pagination, caching fields `ttlMs`/`cacheScope` on list and read results |
| Client features | Elicitation (form and URL modes), sampling and roots (both Deprecated). Server-to-client asks happen via MRTR: return `InputRequiredResult` (`resultType: "input_required"` with `inputRequests`), client retries with `inputResponses` |
| Change notifications | `subscriptions/listen` opens one long-lived POST response stream for `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`, `resourceSubscriptions`; `ping` and `logging/setLevel` are removed |
| Tool results | `content` blocks (text, image, audio, resource_link, embedded resource), optional `structuredContent` matching `outputSchema` (JSON Schema 2020-12 by default), `isError: true` for execution errors the model can fix; JSON-RPC errors for protocol problems |
| Authorization | Optional, HTTP only. MCP server = OAuth 2.1 resource server; RFC 9728 Protected Resource Metadata is mandatory; clients use RFC 8707 `resource`, PKCE `S256`, RFC 9207 `iss` check; Client ID Metadata Documents preferred over Dynamic Client Registration (deprecated). stdio servers take credentials from the environment instead |
| Extensions | `{vendor}/{name}` ids negotiated in capabilities `extensions`: tasks (`io.modelcontextprotocol/tasks`), MCP Apps, OAuth client credentials, enterprise-managed authorization |
| SDKs | Python `mcp` 2.x: `from mcp.server import MCPServer`, `from mcp import Client`. TypeScript v2: `McpServer`, `createMcpHandler`, `serveStdio` from `@modelcontextprotocol/server`; `Client` from `@modelcontextprotocol/client`; adapters `@modelcontextprotocol/express`, `node`, `hono`, `fastify` |

## 3. Workflow

1. Decide whether the server must run locally (needs the user's files, devices or tools) or can be remote. Prefer remote Streamable HTTP when it needs no local access.
2. List the capabilities as MCP primitives: actions the model calls become tools; data the application loads becomes resources; reusable user-triggered templates become prompts.
3. Design each tool: unique name (1 to 128 chars, letters, digits, `_`, `-`, `.`), a description written for a model, an input schema, an output schema when results are structured, annotations, and a clear error plan (`isError` for fixable problems).
4. Pick the SDK (section 4), build with the high-level API, and keep handlers stateless: any state is an explicit server-minted handle passed as a tool argument.
5. Choose the transport: stdio for local subprocess servers, Streamable HTTP for anything deployed. Add authorization for any HTTP server that exposes non-public data.
6. If a tool needs user input mid-call, use elicitation through the SDK's resolver or `input_required` helper, never a blocking server-to-client request.
7. Test in memory with the SDK client, then with the MCP Inspector against the real transport, then with a real host.
8. Review with section 12; pin versions and deploy behind Host/Origin validation and TLS.

## 4. Decision Rules

- SDK: new Python code uses `mcp` 2.x (`MCPServer`). New TypeScript code uses `@modelcontextprotocol/server` and `@modelcontextprotocol/client` 2.x. The `@modelcontextprotocol/sdk` 1.x line and Python 1.x `FastMCP` keep receiving fixes but speak the legacy era; use them only to match an existing codebase.
- Transport: stdio for a server a host launches as a child process; Streamable HTTP for shared, remote or multi-client servers. Never add HTTP+SSE except to serve old clients.
- Era: servers built with the 2.x SDKs answer both eras from one definition; clients use auto negotiation (`mode="auto"` in Python, `versionNegotiation: { mode: "auto" }` in TypeScript). Pin to `2026-07-28` only when you control both ends.
- Tool vs resource vs prompt: tool when the model decides to act or compute; resource when the host decides what context to load; prompt when the user picks a templated workflow.
- Errors: failures the model can correct (bad argument value, not found, business rule) are tool errors (`isError: true`, Python `ToolError`); malformed requests, unknown tools and server faults are protocol errors.
- User input in a tool: ask with elicitation (form mode for non-sensitive values, URL mode for passwords, API keys, payments and OAuth consent); the form mode MUST NOT collect secrets.
- Auth on HTTP: verify bearer tokens on every request, check audience, publish Protected Resource Metadata. Use a separate identity provider; do not embed an authorization server in a new MCP server.
- State: no sessions. Return a handle from a creation tool, accept it as an argument, bind it server-side to the authenticated principal.
- Local vs hosted bridge: avoid proxies that run arbitrary commands for remote URLs; if a bridge is unavoidable, pin its version and sandbox it.

## 5. Coding Standards

- Tool names: stable, namespaced when aggregated (`orders_get_status`), unique per server; keep descriptions specific about when to use the tool and what it returns.
- Input schemas come from type hints (Python) or Zod / Standard Schema (TypeScript); constrain arguments (enums, bounds, patterns) so the SDK rejects bad input before your handler runs.
- Declare `outputSchema` / a typed return so clients get `structuredContent`; also return a text rendering for clients that ignore structured data.
- Set `ToolAnnotations` hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) honestly. Clients must treat them as untrusted unless the server is trusted, so never rely on them for access control.
- Return tools from `tools/list` in a deterministic order (helps client caching and model prompt caching). Paginate large lists.
- stdio servers write only protocol messages to stdout; log to stderr (Python `logging`, TypeScript `console.error`). A stray `print`/`console.log` corrupts the stream.
- Use `async` handlers for I/O. In Python, plain `def` tools run on a worker thread in 2.x.
- Do not put secrets in tool arguments, resource URIs or tool results unless the user must see them.
- Validate all inputs in the handler beyond the schema (authorization, ownership, path containment, SSRF filtering).

## 6. Project Structure

```
mcp-orders/
├── pyproject.toml            # mcp>=2,<3 (Python 3.11+); or package.json with @modelcontextprotocol/server ^2
├── src/orders_mcp/
│   ├── server.py             # MCPServer instance, registration, run()
│   ├── tools/                # one module per tool group; pure functions + thin MCP wrappers
│   ├── resources.py          # URI templates, path containment helpers
│   ├── prompts.py
│   ├── auth.py               # TokenVerifier (audience + scope checks), AuthSettings
│   ├── domain/               # business logic with no MCP imports
│   └── config.py             # env-driven settings, allowed hosts/origins
├── tests/
│   ├── test_tools.py         # in-memory Client against the server object
│   ├── test_auth.py          # 401/403 behavior through the ASGI app
│   └── fixtures/
├── Dockerfile                # non-root, pinned base digest
└── README.md                 # transports, env vars, required scopes, client config snippet
```

## 7. Design Patterns

- **Thin wrapper over domain code**: tools call domain services; MCP concerns (schemas, errors, annotations) stay in the wrapper layer.
- **Explicit state handles**: `create_basket` returns an opaque, high-entropy id; later tools take `basket_id`; the server stores state under `<principal>:<handle>` and rejects other principals.
- **Resolver or `input_required` for confirmation**: destructive tools ask the user to confirm through elicitation rather than relying on the host to prompt.
- **Resource templates for read-only data**: `orders://{order_id}` with strict parameter validation; expose list tools when resources are numerous.
- **Per-request factory (TypeScript)**: `createMcpHandler(() => buildServer())` builds a fresh server per request, so nothing leaks between callers and horizontal scaling is free.
- **Scope-gated tools**: `tools/list` may vary by the caller's authorization (per request, not per connection); per-operation `insufficient_scope` challenges drive step-up consent.
- **Gateway aggregation**: if a client merges several servers, prefix tool names with a server identifier and surface which server owns each tool.

## 8. Best Practices

- Write tool descriptions as instructions to a model, but treat them as an attack surface when consuming other people's servers (section 10).
- Return actionable error text ("No order A-1. Ids look like A-10293."), never stack traces.
- Cap result sizes and use pagination or resource links instead of embedding huge blobs.
- Support cancellation: on Streamable HTTP, a closed response stream cancels the request; stop work promptly. Report progress with `notifications/progress` for long tools.
- Use `ttlMs` and `cacheScope` honestly on list and read results; keep `listChanged` notifications for real changes.
- Version your server (`serverInfo`) and document required scopes, env vars and egress needs.
- Keep the surface small: fewer, well-described tools beat dozens of overlapping ones.
- Prefer URL-mode elicitation or out-of-band flows for credentials; never ask for passwords or API keys in a form.
- For long operations consider the tasks extension (`io.modelcontextprotocol/tasks`), which replaces the old core tasks API; check SDK support before relying on it (the Python 2.x SDK did not implement it at the time of verification).

## 9. Performance

- Streamable HTTP in the modern era is stateless: any instance can serve any request, so scale horizontally behind a plain load balancer; legacy-era sessions need sticky routing or stateless mode.
- MRTR retries carry `requestState`; with several workers, seal it with a shared key and a shared audience (Python `RequestStateSecurity(keys=[...])`) or retries fail on a different worker.
- Create connection pools and caches once at module scope or in a lifespan, not per request (the TypeScript factory runs per request; Python lifespan runs once per process in 2.x).
- Return `ttlMs`/`cacheScope` so clients can cache `tools/list`, `resources/list` and similar results instead of polling.
- Keep SSE responses unbuffered behind proxies: send `X-Accel-Buffering: no` (SDKs do) and configure the proxy not to buffer.
- Use JSON-only responses (`json_response=True` in Python, `responseMode: "json"` in TypeScript) when no tool streams progress; note this drops mid-call notifications.
- Avoid chatty tools: combine lookups into one call to save round trips and model turns.

## 10. Security

- **Origin and Host validation**: Streamable HTTP servers MUST validate `Origin` (respond 403 when present and invalid) to block DNS rebinding. Bind local servers to `127.0.0.1`, not `0.0.0.0`. The SDKs arm Host/Origin checks for localhost by default; when deploying under a real hostname set the allowlist explicitly (Python `TransportSecuritySettings(allowed_hosts=[...], allowed_origins=[...])`, TypeScript `createMcpExpressApp({ host, allowedHosts })`).
- **Authorization**: validate every bearer token on every request; verify signature, expiry, issuer and that the audience is this server (RFC 8707 `resource` binding). Return 401 for missing or invalid tokens with `WWW-Authenticate` pointing at the Protected Resource Metadata, 403 `insufficient_scope` with the needed scopes. Never accept tokens in the query string.
- **Token passthrough is forbidden**: a server must not accept tokens issued for another resource and must not forward the client's token to a downstream API. For upstream calls obtain a separate token as an OAuth client of that API.
- **Confused deputy**: MCP proxy servers with a static upstream client id must obtain per-client user consent before forwarding to the third-party authorization server; validate redirect URIs exactly.
- **Scope minimization**: advertise a small `scopes_supported`, challenge for more via `insufficient_scope`, and include all scopes needed for one operation in a single challenge.
- **Tool poisoning and rug pulls (client side)**: tool names and descriptions are instructions the model reads, and a server can change them after approval or target other servers' tools. Review descriptions, prefer clients that pin and re-prompt on changes, keep the server roster small, and treat annotations from untrusted servers as untrusted.
- **Tool results are untrusted input** to the model (indirect prompt injection): sanitize outputs, keep a human in the loop for sensitive actions, show tool inputs before calls.
- **Local servers**: a stdio server runs with the user's privileges. Pin versions (container images by digest), identify the publisher, run in a container with only the needed mounts, pass secrets per server via environment, and limit network egress. Clients must show the exact command before one-click installs.
- **Input handling**: validate and bound all arguments; contain file paths (Python `safe_join`, reject `..` and absolute paths); never build shell or SQL strings from arguments; filter outbound URLs against SSRF (HTTPS only, block private and link-local ranges, no redirects to them).
- **Secrets**: form-mode elicitation MUST NOT request passwords, API keys, tokens or payment data; use URL mode. Do not mark sensitive parameters with `x-mcp-header` (header values are visible to intermediaries).
- **State handles**: use unguessable ids, expiry, and bind them to the authenticated principal; possession of a handle is not authentication.
- **Multi-tenant servers**: scope reads and writes by the tenant derived from the verified token, not from arguments.
- **Rate limit and audit**: limit tool invocations per principal and log tool name, caller and outcome without logging secrets or full payloads.

## 11. Testing

- Python: use the in-memory client, `async with Client(mcp, raise_exceptions=True) as client:` then `await client.call_tool("name", {...})`; assert on `result.structured_content` and `result.is_error`. Note that in-memory tests skip the HTTP layer, so authorization is not exercised; test it through the ASGI app (`mcp.streamable_http_app()`) with an HTTP test client.
- TypeScript: drive `createMcpHandler(factory).fetch` in process through a `Client` over `StreamableHTTPClientTransport` with a custom `fetch`, or an in-memory transport; assert on `structuredContent` and `isError`.
- Test both eras: connect once with auto negotiation and once pinned to legacy (`mode="legacy"` / `versionNegotiation: { mode: "legacy" }`) if you support 2025 clients.
- Negative tests: invalid arguments, unknown tool, expired token (401), wrong audience (401), missing scope (403), bad `Origin`/`Host` (403/421), path traversal in resource URIs, oversized bodies.
- Inspect interactively with `npx @modelcontextprotocol/inspector <command>` (stdio) or `uv run mcp dev server.py`; read the tool list as a model would and look for instructions unrelated to the tool.
- Check stdout cleanliness for stdio servers: run the process, send a request, and assert every stdout line parses as JSON-RPC.

## 12. Review Checklist

- [ ] Targets revision 2026-07-28 with the 2.x SDKs; legacy support is deliberate and tested.
- [ ] No HTTP+SSE-only server; no reliance on `Mcp-Session-Id`, GET streams or resumable SSE.
- [ ] Tool names unique and valid; descriptions specific; schemas constrained; output schema present where results are structured.
- [ ] Fixable failures use `isError` / `ToolError`; protocol errors are reserved for malformed requests and server faults.
- [ ] stdio: nothing but protocol messages on stdout; logs on stderr.
- [ ] HTTP: TLS, Origin/Host validation, allowlist for the real hostname, bound to loopback when local.
- [ ] Auth: audience-checked tokens, Protected Resource Metadata, 401/403 behavior, minimal scopes, no passthrough, tokens never in URLs.
- [ ] No secrets requested via form elicitation; URL mode used for credentials.
- [ ] Inputs validated; paths contained; no shell/SQL string building; SSRF filtering on fetches.
- [ ] State handles unguessable and principal-bound; multi-tenant filters on reads and writes.
- [ ] Annotations honest; destructive tools confirm via elicitation.
- [ ] Tests cover in-memory calls, auth failures and both protocol eras.
- [ ] Dependencies and container images pinned; SDK version recorded.

## 13. Production Notes

- Behind a TLS-terminating proxy, configure the ASGI server to trust forwarded headers (uvicorn `--proxy-headers --forwarded-allow-ips`), or redirects downgrade to `http://` and clients refuse them.
- A deployed Python server with default transport security rejects every non-localhost request (421 Invalid Host header); allowlist hostnames with `transport_security=`.
- Legacy-era clients need sticky sessions unless you run stateless mode; modern-era clients need nothing. In Python 2.x legacy sessions live in one worker's memory (idle timeout and max-session limits apply).
- Request body size defaults to 4 MiB in the Python HTTP transport; raise only for legitimate large messages.
- Dynamic Client Registration is deprecated; prefer Client ID Metadata Documents on the authorization server and pre-registration for known clients.
- Deprecated features (Roots, Sampling, Logging, HTTP+SSE, DCR) stay functional during a minimum twelve-month window; do not adopt them in new code and plan removals.
- Error codes: `-32602` for unknown resource and invalid params; MCP-reserved range `-32020` to `-32099` (`HeaderMismatch` -32020, `MissingRequiredClientCapability` -32021, `UnsupportedProtocolVersion` -32022).
- Python HTTP client in 2.x is `httpx2`; minimal containers need CA certificates because TLS verifies against the system trust store.
- Record the exact SDK and protocol versions in your README; SDK majors move with spec revisions.

## 14. Examples

Python server with typed output, honest annotations, a model-fixable error and a contained resource path (stdio by default, Streamable HTTP on request):

```python
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.shared.path_security import safe_join
from mcp.types import ToolAnnotations

mcp = MCPServer("Orders", instructions="Look up orders before answering questions about shipping.")


class OrderStatus(BaseModel):
    order_id: str
    status: Literal["pending", "shipped", "delivered"]
    eta_days: int | None = None


ORDERS = {"A-10293": OrderStatus(order_id="A-10293", status="shipped", eta_days=2)}
DOCS_ROOT = Path("./manuals")


@mcp.tool(title="Order status", annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def get_order_status(
    order_id: Annotated[str, Field(pattern=r"^A-\d{5}$", description="Order id, for example A-10293")],
) -> OrderStatus:
    """Look up the shipping status of one order. Read-only. Returns status and days to delivery."""
    order = ORDERS.get(order_id)
    if order is None:
        raise ToolError(f"No order {order_id!r}. Ids look like A-10293.")  # model can fix and retry
    return order


@mcp.resource("manuals://{+name}")
def read_manual(name: str) -> str:
    """Support manual page by relative name, for example returns/policy.md."""
    file = safe_join(DOCS_ROOT, name)  # raises if the path would leave DOCS_ROOT
    if not file.is_file():
        raise ResourceNotFoundError(f"No manual at {name!r}.")
    return file.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()  # stdio; for HTTP: mcp.run(transport="streamable-http", port=3001)
```

Python Streamable HTTP app with bearer-token verification and an explicit Host/Origin allowlist (run with uvicorn):

```python
from pydantic import AnyHttpUrl

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings

RESOURCE = "https://mcp.example.com/mcp"


class JwtVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        claims = await verify_jwt_signature_and_expiry(token)  # your code: JWKS, issuer, exp
        if claims is None or RESOURCE not in claims.audiences:
            return None  # wrong audience means 401, never "close enough"
        return AccessToken(token=token, client_id=claims.client_id, scopes=claims.scopes,
                           expires_at=claims.exp, resource=RESOURCE)


mcp = MCPServer(
    "Orders",
    token_verifier=JwtVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl(RESOURCE),
        required_scopes=["orders:read"],
        validate_token_resource=True,
    ),
)

app = mcp.streamable_http_app(
    transport_security=TransportSecuritySettings(
        allowed_hosts=["mcp.example.com", "mcp.example.com:*"],
        allowed_origins=["https://app.example.com"],
    )
)
# uvicorn server:app --proxy-headers --forwarded-allow-ips='<proxy address>'
```

TypeScript server on Express with a per-request factory, structured output and a bearer-token gate:

```typescript
import { createMcpExpressApp, requireBearerAuth } from "@modelcontextprotocol/express";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createMcpHandler, McpServer } from "@modelcontextprotocol/server";
import * as z from "zod/v4";

const handler = createMcpHandler(() => {
  const server = new McpServer({ name: "orders", version: "1.0.0" });
  server.registerTool(
    "get-order-status",
    {
      description: "Look up the shipping status of one order. Read-only.",
      inputSchema: z.object({ orderId: z.string().regex(/^A-\d{5}$/) }),
      outputSchema: z.object({ status: z.enum(["pending", "shipped", "delivered"]) }),
      annotations: { readOnlyHint: true, openWorldHint: false }
    },
    async ({ orderId }, ctx) => {
      const caller = ctx.http?.authInfo; // set by the gate; re-check that the caller may read this order
      if (!caller || !(await mayRead(caller.clientId, orderId))) {
        return { content: [{ type: "text", text: "Order not found." }], isError: true };
      }
      const output = { status: "shipped" as const };
      return { content: [{ type: "text", text: JSON.stringify(output) }], structuredContent: output };
    }
  );
  return server;
});

const app = createMcpExpressApp({ host: "0.0.0.0", allowedHosts: ["mcp.example.com"] });
const auth = requireBearerAuth({ verifier, requiredScopes: ["orders:read"], expectedResource: new URL("https://mcp.example.com/mcp") });
const node = toNodeHandler(handler);
app.all("/mcp", auth, (req, res) => void node(req, res, req.body));
app.listen(3000);
```

`verifier` (an `OAuthTokenVerifier` that returns `AuthInfo` with `expiresAt` and `resource`) and `mayRead` are your own code; see [references/transports-and-auth.md](references/transports-and-auth.md) for the verifier contract and metadata routes.

## 15. Common Mistakes

- **Building on HTTP+SSE** (`/sse` plus `/messages`): deprecated since 2025-03-26. Use Streamable HTTP.
- **Expecting sessions**: `Mcp-Session-Id`, `initialize` and the GET stream are gone in 2026-07-28. Use explicit handles and per-request `_meta`.
- **`print()` or `console.log()` in a stdio server**: corrupts the protocol stream; log to stderr.
- **Importing `FastMCP` / `StreamableHTTPServerTransport` from 2.x docs**: v2 renamed `FastMCP` to `MCPServer` (`mcp.server`) and replaced transport wiring with `run()` / `createMcpHandler`.
- **Passing `port=` to `MCPServer(...)`**: transport options belong on `run()` or the app builder.
- **Sending the client's access token to an upstream API**: token passthrough is forbidden; get a separate upstream token.
- **Skipping audience validation**: accepting any valid JWT from the authorization server lets tokens for other services in.
- **Binding to `0.0.0.0` without Host/Origin checks**: reachable by DNS-rebinding pages and other hosts.
- **Collecting an API key with form elicitation**: not allowed; use URL mode or out-of-band configuration.
- **Trusting tool annotations or descriptions from third-party servers**: both can mislead; review and pin.
- **Returning errors as normal text**: use `isError` / `ToolError` so clients and models see failure.
- **Raising plain exceptions for model-fixable errors (Python 2.x)**: only `ToolError` text reaches the model; other exceptions become a generic message.
- **Using `ctx.elicit()` or sampling from a tool on 2026-07-28 connections**: server-initiated requests are gone; use `Resolve`/`Elicit` (Python) or `inputRequired` (TypeScript).
- **Multiple workers with default `requestState` keys**: MRTR retries fail intermittently; share keys and the server name.
- **Relying on `x-mcp-header` for sensitive values**: header values are visible to intermediaries.
- **Unbounded path parameters in resource templates**: reject traversal; contain paths under a root.

## 16. References

- [references/transports-and-auth.md](references/transports-and-auth.md): modern and legacy transports, request metadata and headers, stdio rules, HTTP security, the authorization flow, registration, scopes and step-up, token validation, SDK auth APIs, security best-practice summary.
- [references/server-sdks.md](references/server-sdks.md): Python `mcp` 2.x and TypeScript v2 server and client APIs, tools, structured output, errors, resources, elicitation and MRTR, lifespan, progress, testing, and v1 compatibility.
- [references/protocol-revisions.md](references/protocol-revisions.md): what changed between 2025-11-25 and 2026-07-28, deprecations, extensions, error codes, and interoperability between eras.
- Official docs: https://modelcontextprotocol.io/specification/2026-07-28 , https://modelcontextprotocol.io/specification/2026-07-28/basic/transports , https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization , https://py.sdk.modelcontextprotocol.io/ , https://ts.sdk.modelcontextprotocol.io/v2/ , https://github.com/modelcontextprotocol/python-sdk , https://github.com/modelcontextprotocol/typescript-sdk
