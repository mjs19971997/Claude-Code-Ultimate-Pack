# Tool Use

Reference for defining tools, running the tool loop by hand or with the SDK tool runner, forced tool use, strict tools, thinking with tools, and the MCP connector. Verified against the Claude API docs, Python SDK `anthropic` 2.3.x and TypeScript SDK `@anthropic-ai/sdk` 1.3.x, models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` (2026-10).

## 1. Client tools and server tools

- Client tools (your own tools and Anthropic-schema tools such as bash and text editor) run in your application. The response has `stop_reason: "tool_use"` and one or more `tool_use` blocks with `id`, `name` and `input`.
- Server tools (web search, web fetch, code execution, tool search) run on Anthropic infrastructure; results arrive in the same response. A long server-tool loop can end with `stop_reason: "pause_turn"` (default limit 10 iterations per request): send the assistant content back as it is to continue.
- A response can contain a client `tool_use` and a server tool call that has no result block yet. Reply with a user message containing only `tool_result` blocks for the client tools and keep the same `tools` array.
- `count_tokens` rejects server tools, the MCP connector and `image`/`document` blocks with `url` or `file` sources; the Messages API accepts them.

## 2. Defining a client tool

A user-defined tool has `name` (regex `^[a-zA-Z0-9_-]{1,128}$`), `description`, `input_schema` (JSON Schema object) and optional `input_examples`, `strict`, `cache_control`.

```python
tool = {
    "name": "github_search_issues",
    "description": (
        "Search issues in one GitHub repository. Use when the user asks about existing bugs or "
        "feature requests; do not use it to create or edit issues. Returns up to `limit` issues "
        "as JSON with number, title, state and url. Does not return comments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/name, e.g. anthropics/anthropic-sdk-python"},
            "query": {"type": "string", "description": "Free-text search terms"},
            "limit": {"type": "integer", "description": "Maximum results, 1 to 20"},
        },
        "required": ["repo", "query"],
        "additionalProperties": False,
    },
    "strict": True,
}
```

Guidelines from the docs:

- Descriptions are the most important factor: what the tool does, when to use it and when not to, what each parameter means, caveats, what it returns. Several sentences per tool.
- Prefer fewer, consolidated tools (one tool with an `action` parameter) over many near-duplicates; namespace names by service when tools span services (`github_list_prs`, `slack_send_message`).
- Return high-signal data: stable identifiers and only the fields needed for the next step.
- `input_examples` helps for nested or format-sensitive inputs; each example must validate against `input_schema` (otherwise 400) and costs prompt tokens. Not supported on server tools or client toolsets.
- Ask for a short explanation in a parameter, not "your reasoning": a parameter that asks for step-by-step thinking can trigger a `reasoning_extraction` refusal.
- With the default `tool_choice: auto`, steer how readily Claude calls tools in the system prompt ("use the tools to investigate before answering" versus "use your judgment").

## 3. The manual loop and its formatting rules

Rules that cause 400 errors when broken:

1. The user message with results must come immediately after the assistant message that contains the `tool_use` blocks.
2. In that user message, all `tool_result` blocks come first; any text comes after.
3. Every `tool_use` id needs a `tool_result` with the same `tool_use_id`, including calls you chose not to run (return `is_error: true` with a short explanation).
4. When the assistant turn also contains a server tool call without a result, the user message must contain only `tool_result` blocks.
5. Thinking blocks in the assistant turn are passed back complete and unmodified.

`tool_result.content` is a string, or a list of `text`, `image`, `document` or `search_result` blocks. Set `is_error: true` when execution failed.

Parallel calls: by default Claude may emit several `tool_use` blocks in one turn. Run read-only calls concurrently, side-effecting calls sequentially, and return all results together in one user message. To disable parallelism, set `tool_choice={"type": "auto", "disable_parallel_tool_use": True}`.

```python
import asyncio
import anthropic

client = anthropic.AsyncAnthropic()


async def execute(block, handlers) -> dict:
    handler = handlers.get(block.name)
    if handler is None:
        return {"type": "tool_result", "tool_use_id": block.id, "content": f"Unknown tool {block.name}", "is_error": True}
    try:
        output = await handler(**block.input)
        return {"type": "tool_result", "tool_use_id": block.id, "content": output}
    except PermissionError:
        return {"type": "tool_result", "tool_use_id": block.id, "content": "Not permitted for this user.", "is_error": True}
    except Exception as exc:  # report a short message, log the traceback elsewhere
        return {"type": "tool_result", "tool_use_id": block.id, "content": f"Tool failed: {type(exc).__name__}", "is_error": True}


async def turn(messages, tools, handlers, system):
    response = await client.messages.create(
        model="claude-sonnet-5-5", max_tokens=4096, system=system, tools=tools, messages=messages
    )
    messages.append({"role": "assistant", "content": response.content})
    if response.stop_reason == "tool_use":
        calls = [b for b in response.content if b.type == "tool_use"]
        results = await asyncio.gather(*(execute(b, handlers) for b in calls))  # only for read-only tools
        messages.append({"role": "user", "content": list(results)})
    return response
```

Stop when `stop_reason` is not `tool_use`, and bound the loop with an iteration cap and a token or time budget.

## 4. tool_choice and forced tool use

| Setting | Behavior |
|---|---|
| `{"type": "auto"}` (default) | Claude decides. Works on every current model |
| `{"type": "none"}` | No tool calls. Works on every current model |
| `{"type": "any"}` / `{"type": "tool", "name": "..."}` | 400 on Opus 5.5, Sonnet 5.5, Fable 5.1 and Mythos 5.1, including on the token counting endpoint. Manual extended thinking (`thinking.type: "enabled"`) also rejects them. Where accepted (for example Haiku 5.5 with adaptive thinking), the response starts with the tool call and has no thinking block |

On models that reject forced tool use, keep `auto` and combine it with `strict: true` tools (schema-valid inputs) or `output_config.format` (schema-valid final answer), and say in the prompt when the tool must be used. Changing `tool_choice` between requests invalidates cached message blocks (tools and system caches stay valid).

## 5. Strict tool use and structured outputs

- `strict: true` on a tool definition constrains sampling so `tool_use.input` matches `input_schema` and the tool name is valid; no more `"2"` for `2` or missing required fields.
- Objects need `additionalProperties: false`. Unsupported schema features return 400: recursive schemas, numeric constraints (`minimum`, `maximum`, `multipleOf`), string length constraints, array constraints beyond `minItems` 0 or 1, external `$ref`, and some regex features (backreferences, lookaround, `\b`). SDK helpers can transform schemas with unsupported constraints.
- Enum and const casing is not guaranteed (a value may differ in capitalization); compare case-insensitively.
- Strict validity is not business validity: still validate IDs, ranges and permissions in the handler.
- The same constraint engine powers `output_config.format` for the final answer. Both can be used in one request. First use of a schema adds compilation latency; compiled grammars are cached for 24 hours since last use. Changing the schema or `output_config.format` invalidates the prompt cache for that conversation.
- Structured outputs are incompatible with citations (400) and with prefill. Grammar scope covers direct output only, not tool calls, tool results or thinking.

## 6. Tool runner (beta)

Use it when you do not need custom approval, logging or conditional execution. The runner calls the API, runs requested tools, appends results and repeats until a response without tool use or `max_iterations`.

Python (sync; use `@beta_async_tool` with the async client):

```python
import json
from anthropic import Anthropic, beta_tool
from anthropic.lib.tools import ToolError

client = Anthropic()


@beta_tool
def get_weather(location: str, unit: str = "celsius") -> str:
    """Get the current weather in a given location.

    Args:
        location: City and country, e.g. Paris, France
        unit: Temperature unit, either 'celsius' or 'fahrenheit'
    """
    if not location.strip():
        raise ToolError("location must not be empty")
    return json.dumps({"location": location, "temperature": 20, "unit": unit, "condition": "sunny"})


runner = client.beta.messages.tool_runner(
    model="claude-opus-5-5",
    max_tokens=1024,
    tools=[get_weather],
    messages=[{"role": "user", "content": "What is the weather in Paris?"}],
)
final_message = runner.until_done()
print(final_message.content)
```

TypeScript with Zod (Zod 3.25 or newer):

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { betaZodTool } from "@anthropic-ai/sdk/helpers/beta/zod";
import { z } from "zod";

const client = new Anthropic();

const getWeather = betaZodTool({
  name: "get_weather",
  description: "Get the current weather in a given location",
  inputSchema: z.object({
    location: z.string().describe("City and country, e.g. Paris, France"),
    unit: z.enum(["celsius", "fahrenheit"]).default("celsius")
  }),
  run: async ({ location, unit }) => JSON.stringify({ location, unit, temperature: 20 })
});

const finalMessage = await client.beta.messages.toolRunner({
  model: "claude-opus-5-5",
  max_tokens: 1024,
  tools: [getWeather],
  messages: [{ role: "user", content: "What is the weather in Paris?" }]
});
```

Runner facts from the docs and SDK guides:

- Iterating yields each assistant message; `break` ends your loop but not the runner; `until_done()` (Python) resumes it and returns the final message. Call `runner.close()` for a runner you will not resume. `max_iterations` caps the loop.
- A tool that raises is reported to Claude as a tool result with `is_error: true` (Python sends the exception `repr()`). Python `ToolError` and TypeScript `ToolError` (from `@anthropic-ai/sdk/lib/tools/BetaRunnableTool`) accept content blocks and are not logged as failures.
- `betaTool()` (JSON Schema) does not validate Claude's input at runtime; validate inside `run`. `betaZodTool` validates with Zod.
- Streaming is available (`stream=True` in Python); `run_tools_eagerly=True` runs each tool as soon as its call is written, and `defer_tool_call` holds calls that are not safe to run twice.
- Client-side compaction in the TypeScript and Ruby runners was removed; use server-side compaction. `runner.compact_before_next_turn()` (Python) works with the `compact-2026-09-04` beta; the threshold form needs at least 50,000 tokens.
- Changing `tools` mid-run misses the prompt cache unless you use the `inline-tools-2026-09-15` beta with `add_tools` / `remove_tools`. Beta names change; check the current docs before using them.

## 7. Thinking with tools

- Thinking works with tools. In a tool loop, pass every `thinking` and `redacted_thinking` block of the assistant turn back unmodified. Modified blocks return 400.
- The whole tool loop is one assistant turn and runs in one thinking mode. Toggling thinking mid-turn silently disables thinking for that request. Change configuration between turns.
- Adaptive thinking interleaves thinking between tool calls automatically; no beta header.
- Thinking or effort configuration changes invalidate cache prefixes; for thinking-heavy loops that pause longer than five minutes consider the one-hour cache TTL.
- On Claude 5.1 and later models the API checks each thinking block's signature against the model that wrote it and everything sent before it. Keep history append-only; replace prefix edits with mid-conversation system messages, `tool_addition` / `tool_removal` blocks or compaction (see the Preserved thinking page).

## 8. MCP connector (beta)

The Messages API can call remote MCP servers directly: pass `mcp_servers` (type `url`, `url`, `name`, optional `authorization_token`) and a matching `{"type": "mcp_toolset", "mcp_server_name": "..."}` entry in `tools`, with the beta header named in the MCP connector docs (`mcp-client-2026-09-15` and `mcp-client-2025-11-20` are listed; the older `mcp-client-2025-04-04` is deprecated).

- Only MCP tool calls are supported (not resources or prompts), and the server must be publicly reachable over HTTP (Streamable HTTP or SSE); local stdio servers cannot be used.
- You can enable all tools, allowlist or denylist tools, and configure tools individually.
- For local servers, prompts or resources, use an MCP client and convert: the TypeScript SDK ships `@anthropic-ai/sdk/helpers/beta/mcp` (`mcpTools`, `mcpMessages`, `mcpResourceToContent`, `mcpResourceToFile`).
- Do not put long-lived tokens in prompts; pass a short-lived OAuth access token as `authorization_token` obtained for that server and audience. See mcp-expert for server-side rules.

## 9. Untrusted content

Tool results often carry webpages, email, uploads and third-party API data. An attacker who controls any of it can try to redirect Claude. Keep such content inside `tool_result` blocks rather than `system` or plain user text, restrict what tools can do (read-only by default, confirmation for writes, per-user authorization in the handler), and cap output size. For deeper hardening see the Anthropic guidance on mitigating jailbreaks and prompt injections.
