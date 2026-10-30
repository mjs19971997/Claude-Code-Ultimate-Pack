# Server and Client SDKs

Reference for the official MCP SDKs: Python `mcp` 2.x and TypeScript `@modelcontextprotocol/server` / `@modelcontextprotocol/client` 2.x, plus notes on the 1.x lines. Verified against Python SDK `mcp` 2.3.x (docs at py.sdk.modelcontextprotocol.io), TypeScript SDK 2.4.x (docs at ts.sdk.modelcontextprotocol.io/v2), legacy `@modelcontextprotocol/sdk` 1.32.x, MCP specification 2026-07-28 (2026-10).

## 1. Package map

| Language | Package | Notes |
|---|---|---|
| Python | `mcp` (extra `mcp[cli]` for `mcp dev`, `mcp run`, `mcp install`) | v2 is the stable line; Python 3.11+ per the v2 docs; wire types live in `mcp-types` (re-exported as `mcp.types`) |
| Python 1.x | `mcp` `<2` (`from mcp.server.fastmcp import FastMCP`) | Security and critical fixes only; pin `mcp>=1.28,<2` to stay on it |
| TypeScript | `@modelcontextprotocol/server` | `McpServer`, `createMcpHandler`, auth helpers; stdio via `@modelcontextprotocol/server/stdio` |
| TypeScript | `@modelcontextprotocol/client` | `Client`, `StreamableHTTPClientTransport`; stdio via `@modelcontextprotocol/client/stdio` |
| TypeScript | `@modelcontextprotocol/node`, `express`, `hono`, `fastify` | Thin adapters: `toNodeHandler`, `createMcpExpressApp`, `requireBearerAuth`, and so on |
| TypeScript 1.x | `@modelcontextprotocol/sdk` | Maintained on the `v1.x` branch (bug and security fixes for at least six months after the v2 release on 2026-07-27); codemod available for migration |

Runtimes: TypeScript v2 runs on Node.js 20+, Bun and Deno. Schema libraries: Zod v4 (`import * as z from "zod/v4"`) or any Standard Schema library (Valibot, ArkType). Python uses Pydantic.

## 2. Python server (MCPServer)

Minimal server:

```python
from mcp.server import MCPServer

mcp = MCPServer("Demo")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@mcp.prompt()
def summarize(text: str) -> str:
    """Summarize a piece of text in one sentence."""
    return f"Summarize the following text in one sentence:\n\n{text}"


if __name__ == "__main__":
    mcp.run()  # stdio (default); mcp.run(transport="streamable-http", port=3001)
```

Facts:

- Tool name = function name, description = docstring, input schema = type hints (JSON Schema 2020-12). `Annotated[T, Field(description=..., ge=1, le=50)]`, `Literal[...]` and nested Pydantic models constrain inputs; violations return a tool error before your function runs.
- Return type = output schema: a Pydantic model, `TypedDict`, dataclass or typed class produces an object schema and `structured_content`; scalars and lists are wrapped as `{"result": ...}`. The SDK also renders text `content` for models.
- `@mcp.tool(title=..., annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))` sets hints (`mcp.types.ToolAnnotations`).
- Sync functions run on a worker thread; use `async def` for I/O. Check cancellation for long sync tools via the context.
- Constructor arguments describe the server (`name`, `instructions`, `lifespan`, `token_verifier` plus `auth`, `request_state_security`, `resource_security`, `log_level`, `debug`); transport options (`host`, `port`, `streamable_http_path`, `json_response`, `stateless_http`, `max_request_body_size`, `transport_security`, `event_store`, `session_idle_timeout`, `max_sessions`) go to `run()` or the app builder. `MCPServer("x", port=9000)` is a `TypeError`.
- `mcp.streamable_http_app(...)` returns a Starlette ASGI app to mount in an existing app or serve with uvicorn (`uvicorn server:app --workers 4`).
- Lifespan: `MCPServer("name", lifespan=app_lifespan)` with an `asynccontextmanager` yielding shared state (database pool); handlers read it through `ctx.request_context.lifespan_context`. In v2 the HTTP lifespan runs once per process.
- Context: declare `ctx: Context` as a parameter (no ambient `get_context()`); `ctx.request_id`, `await ctx.report_progress(done, total=n, message=...)`.
- `mcp dev server.py` starts the Inspector (needs `npx`); `mcp run server.py` imports the module-level `mcp`, `server` or `app`; `mcp install` registers with Claude Desktop.

### Errors

```python
from mcp import MCPError
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import INVALID_PARAMS

@mcp.tool()
def get_author(title: str) -> str:
    """Look up the author of a book in the catalog."""
    if title not in CATALOG:
        raise ToolError(f"No book titled {title!r}.")      # model sees it, result has is_error=True
    return CATALOG[title]
```

`ToolError` messages reach the model. `MCPError(code=INVALID_PARAMS, message=...)` fails the whole request with a JSON-RPC error that the model never sees. Any other exception reads as `Error executing tool <name>` for the model with the traceback in your log. Never return an error string as a normal result.

### Resources and URI templates

`@mcp.resource("config://app")` for fixed URIs; `@mcp.resource("books://{isbn}")` for RFC 6570 templates (`{+path}` keeps slashes, `{?limit,sort}` query parameters, `{/path*}` segments). The SDK rejects parameters that escape their directory via `..`, absolute paths, Windows drive-relative values and null bytes before your handler runs; configure with `security=ResourceSecurity(exempt_params={...})` or `resource_security=` on the constructor, and use `mcp.shared.path_security.safe_join` for filesystem handlers. Listing does not call your function; reading does.

### Elicitation and multi round-trip

Preferred (works on every protocol era): a resolver parameter.

```python
from typing import Annotated
from pydantic import BaseModel
from mcp.server import MCPServer
from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, Resolve

mcp = MCPServer("Files")


class Confirm(BaseModel):
    ok: bool


async def confirm_delete(path: str) -> Confirm | Elicit[Confirm]:
    count = await count_files(path)  # your code
    if count == 0:
        return Confirm(ok=True)  # nothing to confirm, no round trip
    return Elicit(f"{path} has {count} file(s). Delete anyway?", Confirm)


@mcp.tool()
async def delete_folder(path: str, confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete)]) -> str:
    """Delete a folder, asking for confirmation when it is not empty."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            await remove_folder(path)  # your code; re-validate that this caller may delete it
            return f"deleted {path}"
        case _:
            return "not deleted"
```

The resolver parameter does not appear in the tool's input schema. On a 2026-07-28 connection the SDK returns the question as `input_required` and the client's retry carries the answer; on a legacy connection it sends a live elicitation request. `await ctx.elicit(...)` and sampling calls exist only for legacy connections and fail on 2026-07-28 connections. A handler can also return `InputRequiredResult(input_requests={...}, request_state="...")` and read `ctx.input_responses` on the retry.

`request_state` is sealed with a key generated at construction. With several worker processes, pass `request_state_security=RequestStateSecurity(keys=[shared_secret])` (at least 32 bytes; first key seals, all keys unseal) and give every instance the same server name (the name is the audience claim), or set `RequestStateSecurity(keys=[...], audience="billing")`. Without that, a retry that reaches another worker fails with `-32602` "Invalid or expired requestState". A tool that fails intermittently only with more than one worker has this problem.

Form mode must not collect secrets; use URL mode (`ctx.elicit_url` on legacy connections) for credentials and OAuth consent.

## 3. Python client

```python
import anyio
from mcp import Client


async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:   # URL = Streamable HTTP
        tools = await client.list_tools()
        result = await client.call_tool("add", {"a": 1, "b": 2})
        print(result.structured_content)  # {'result': 3}


anyio.run(main)
```

- `Client` accepts a URL (Streamable HTTP), `StdioServerParameters` (stdio subprocess), another transport context manager, or a server object (in memory).
- `mode="auto"` (default) probes with `server/discover` and falls back to `initialize`; `mode="legacy"` skips the probe and runs the 2025 handshake (needed for push-style features such as `ctx.elicit`). `client.protocol_version` reports the result.
- Callbacks for elicitation and sampling are registered on the client; they answer both eras and run concurrently.
- OAuth: `OAuthClientProvider` (an `httpx2.Auth`) attached to the HTTP client of the transport; give it `server_url`, `client_metadata`, a `TokenStorage` and redirect/callback handlers.
- `client.session` exposes the low-level `ClientSession`.
- The client validates inbound traffic against the negotiated protocol version; a non-conforming server raises `pydantic.ValidationError`.

Low-level server: the decorator-based `Server` API of v1 is gone; handlers are constructor arguments `(ctx, params) -> result`, results are built in full, and schema validation of arguments is advertised but not applied for you. Use `MCPServer` unless you need custom methods.

## 4. TypeScript server

stdio:

```typescript
import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";

serveStdio(() => {
  const server = new McpServer({ name: "greeting-server", version: "1.0.0" });
  server.registerTool(
    "greet",
    { description: "Greet someone by name", inputSchema: z.object({ name: z.string() }) },
    async ({ name }) => ({ content: [{ type: "text", text: `Hello, ${name}!` }] })
  );
  return server;
});
console.error("greeting server listening on stdio"); // stderr only
```

HTTP: `createMcpHandler(factory)` returns `{ fetch, close, notify, bus }`; `fetch` is a web-standard `(Request) => Promise<Response>`. The factory runs once per request, receives `{ era, authInfo, requestInfo }`, and must register tools on the fresh instance (never on a shared one). Keep pools and caches at module scope. `export default handler` mounts it on Workers, Deno and Bun; `toNodeHandler(handler)` adapts it for Node frameworks. Options include `responseMode: "json" | "sse"` and `legacy: "stateless" | "reject"` (default serves 2025 clients statelessly from the same factory). `await handler.close()` on shutdown.

Facts:

- `registerTool(name, config, handler)`: `inputSchema` is a Zod object (arguments are validated before the handler; rejects come back as `isError: true` results), `outputSchema` plus `structuredContent` in the result (validated against the schema before returning), `annotations`, `scopeChallenge`. The handler's second argument `ctx` carries `ctx.mcpReq` (progress token via `_meta`, `notify`, `inputResponses`) and `ctx.http?.authInfo`.
- Returning `{ content: [...], isError: true }` or throwing both produce a tool error; protocol errors use `ProtocolError` / `ProtocolErrorCode`, and `ResourceNotFoundError` for resources.
- `registerResource(name, uri, metadata, readCallback)` returns `{ contents: [{ uri: uri.href, text | blob }] }`; templates use `ResourceTemplate`. `registerPrompt(name, { title, description, argsSchema }, callback)` returns `{ messages }`.
- Server-to-client asks on 2026-07-28: return `inputRequired({ inputRequests: { confirm: inputRequired.elicit({ message, requestedSchema }) } })` and read `acceptedContent(ctx.mcpReq.inputResponses, "confirm", schema)` on the retry; `ctx.mcpReq.elicitInput` and `requestSampling` throw on 2026-07-28 connections.
- Notifications: `handler.notify` / `handler.bus` publish change events to `subscriptions/listen` subscribers.

Express with Host/Origin validation and auth: see [transports-and-auth.md](transports-and-auth.md).

## 5. TypeScript client

```typescript
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";

const client = new Client({ name: "my-client", version: "1.0.0" }, { versionNegotiation: { mode: "auto" } });
await client.connect(new StreamableHTTPClientTransport(new URL("https://mcp.example.com/mcp")));
console.log(client.getProtocolEra()); // "modern" or "legacy"

const { tools } = await client.listTools();
const result = await client.callTool({ name: "get-order-status", arguments: { orderId: "A-10293" } });
if (result.isError) console.error(result.content);
await client.close();
```

- Without `versionNegotiation`, `connect()` runs the 2025 `initialize` handshake (`mode: "legacy"`). `mode: "auto"` probes with `server/discover` and falls back; `mode: { pin: "2026-07-28" }` rejects with `SdkError` (`ERA_NEGOTIATION_FAILED`) against a 2025-only server.
- `StdioClientTransport({ command, args })` from `@modelcontextprotocol/client/stdio` spawns the server; `close()` closes stdin, then SIGTERM, then SIGKILL.
- `InMemoryTransport.createLinkedPair()` links a client and server in one process for tests.
- A tool name the server never registered is a protocol failure that throws from `callTool`; handler failures and schema rejects resolve as `isError: true`.
- Fall back to `SSEClientTransport` on a fresh `Client` only for old HTTP+SSE servers.
- Register handlers for server asks with `client.setRequestHandler("elicitation/create", ...)` and declare the capability in the constructor options.
- The Anthropic TypeScript SDK ships helpers (`@anthropic-ai/sdk/helpers/beta/mcp`) to convert MCP tools, prompts and resources for the Claude API.

## 6. Testing recipes

Python (pytest with anyio):

```python
import pytest
from mcp import Client

from server import mcp


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as c:
        yield c


@pytest.mark.anyio
async def test_add(client: Client):
    result = await client.call_tool("add", {"a": 1, "b": 2})
    assert result.structured_content == {"result": 3}
```

TypeScript (in-process, no port):

```typescript
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import { createMcpHandler } from "@modelcontextprotocol/server";

const handler = createMcpHandler(createServer);
const transport = new StreamableHTTPClientTransport(new URL("http://test.local/mcp"), {
  fetch: (url, init) => handler.fetch(new Request(url, init))
});
const client = new Client({ name: "test", version: "1.0.0" }, { versionNegotiation: { mode: "auto" } });
await client.connect(transport);
const result = await client.callTool({ name: "apply-discount", arguments: { price: 80, percent: 25 } });
```

In-memory tests skip HTTP-level behavior (authorization, Host/Origin validation, body limits); cover those with an HTTP test client against the ASGI app or the Express app.

## 7. Migrating from 1.x

- Python: `FastMCP` becomes `MCPServer` (`from mcp.server import MCPServer`); `mcp.server.fastmcp.*` becomes `mcp.server.mcpserver.*`; `ctx.fastmcp` becomes `ctx.mcp_server`; `get_context()` is replaced by a `ctx: Context` parameter; `McpError` becomes `MCPError`; type attributes are snake_case (`is_error`, `input_schema`); transport options move from the constructor to `run()`; WebSocket transport and experimental tasks are removed; `httpx` becomes `httpx2`; low-level `Server` handlers are rewritten. See the SDK migration guide.
- TypeScript: `@modelcontextprotocol/sdk` becomes `@modelcontextprotocol/server` / `client`; `tool()`, `resource()`, `prompt()` become `registerTool`, `registerResource`, `registerPrompt`; `new StdioServerTransport()` plus `connect()` becomes `serveStdio(factory)`; per-request `StreamableHTTPServerTransport` plumbing becomes `createMcpHandler`; authorization server helpers (`mcpAuthRouter`, `ProxyOAuthServerProvider`) moved to `@modelcontextprotocol/server-legacy/auth`. A codemod (`@modelcontextprotocol/codemod`) handles the mechanical part; run it first, then read the upgrade guide.
