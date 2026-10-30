# Tools and Structured Outputs

Reference for function calling, built-in tools, remote MCP, tool choice and Structured Outputs in the Responses API. Verified against openai-python 3.41.0 and openai-node 7.45.1 type definitions and helper declarations (2026-10). Tool availability varies by model, so confirm in the current tools guide before depending on one.

## 1. Function calling protocol

1. Send `tools=[{"type": "function", "name": ..., "description": ..., "parameters": <JSON Schema>, "strict": True}]`. In the Python types `name`, `parameters`, `strict` and `type` are required keys, so always pass `strict` explicitly.
2. The response `output` contains items with `type == "function_call"`, each with `name`, `arguments` (a JSON string) and `call_id`.
3. Run your code, then send the results as new input items:

```python
{"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)}
```

   `output` is a string, or a list of text, image or file content items.
4. Call `responses.create` again with those items, either with `previous_response_id` or by replaying the earlier output items yourself. Repeat until a response has no `function_call` items.

Rules that prevent most failures:

- Every `function_call` needs a matching `function_call_output` with the same `call_id` before the next request.
- Parallel calls: one response can hold several `function_call` items. Return one output per call; set `parallel_tool_calls=False` if your handlers cannot run together.
- Parse `arguments` with `json.loads` inside a try block and validate with a schema; with `strict` the shape is guaranteed but the values are still untrusted.
- Return errors as data (`{"error": "..."}`) so the model can recover, and never put stack traces or secrets in tool output.
- `max_tool_calls` limits built-in tool calls; your own loop needs its own turn cap.

Streaming function calls: accumulate `response.function_call_arguments.delta` by `item_id`, then parse on `response.function_call_arguments.done` or `response.output_item.done`.

Schema helpers: in Python, `openai.pydantic_responses_function_tool(Model, name=..., description=...)` builds a strict Responses function tool from a Pydantic model; pass it to `client.responses.parse(...)` (or `responses.stream`) to get `parsed_arguments` on function-call items. Parsing does not run your function or send results back; you still own the execution loop. Node: `zodResponsesFunction({ name, parameters, description })` from `openai/helpers/zod` behaves the same way.

## 2. Tool choice

| `tool_choice` | Effect |
|---|---|
| `"auto"` (default) | Model decides |
| `"none"` | No tool calls |
| `"required"` | Must call at least one tool |
| `{"type": "function", "name": "get_order_status"}` | Force one function |
| `{"type": "allowed_tools", "mode": "auto" \| "required", "tools": [...]}` | Restrict the callable set without changing the `tools` list (helps prompt caching) |

Custom and MCP tools have their own forced-choice shapes in the SDK types.

## 3. Built-in tools

| Tool | Request shape | Notes |
|---|---|---|
| Web search | `{"type": "web_search", "filters": {"allowed_domains": [...]}, "search_context_size": "low\|medium\|high", "user_location": {"type": "approximate", ...}, "external_web_access": true}` | Add `include=["web_search_call.action.sources"]` for source lists; citations arrive as `annotations` on `output_text`. Omitting `user_location` falls back to the United States |
| File search | `{"type": "file_search", "vector_store_ids": [...], "max_num_results": N, "filters": ..., "ranking_options": ...}` | Vector stores are managed with `client.vector_stores`; add `include=["file_search_call.results"]` to see hits |
| Code interpreter | `{"type": "code_interpreter", "container": {"type": "auto", "file_ids": [...], "memory_limit": "1g"}}` | Container can also be an existing container ID; a `network_policy` controls outbound access. Add `include=["code_interpreter_call.outputs"]` for outputs |
| Remote MCP | `{"type": "mcp", "server_label": ..., "server_url": ..., "allowed_tools": [...], "require_approval": "always"\|"never"\|{...}, "headers": {...}, "authorization": "..."}` | See section 4 |
| Image generation | `{"type": "image_generation"}` | Partial images stream as `response.image_generation_call.partial_image` |
| Computer use, shell, apply_patch | `computer`, `shell`, `apply_patch` | Your code executes the actions the model requests; run them in a sandbox and review the current guides |
| Custom tool | `{"type": "custom", "name": ..., "description": ..., "format": ...}` | Free-form (non-JSON) input; returns `custom_tool_call` items |
| Tool search | `defer_loading=True` on tools plus a `tool_search` tool | Lets the model discover tools lazily in large catalogs; check the current guide |

## 4. Remote MCP and connectors

- One of `server_url`, `connector_id` or `tunnel_id` is required. `connector_id` values (for example `connector_googledrive`, `connector_gmail`) are documented in the SDK as deprecated for models released after 2026-09-01; prefer `server_url` or a tunnel.
- The API lists the server's tools (`mcp_list_tools` item) and then calls them (`mcp_call` items). Restrict exposure with `allowed_tools` (names or a filter).
- `require_approval`: `"always"`, `"never"`, or a filter object keyed by tool name or `read_only`. When approval is required, the response contains an `mcp_approval_request` item; answer with a new input item:

```python
{"type": "mcp_approval_response", "approval_request_id": req.id, "approve": True}
```

- Default to approval for any tool that writes, deletes, pays or sends. Show the human the tool name and arguments, not only a summary.
- Pass bearer tokens through `authorization` or `headers` at request time from a secret store; do not hard-code or log them. The OAuth flow is your application's job.
- A remote server's tool descriptions and results are untrusted input.

## 5. Structured Outputs

Responses API (JSON Schema in `text.format`):

```python
response = client.responses.create(
    model=MODEL,
    input=text,
    text={
        "format": {
            "type": "json_schema",
            "name": "ticket",
            "description": "A triaged support ticket",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["billing", "bug", "feature", "other"]},
                    "summary": {"type": "string"},
                    "assignee": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["category", "summary", "assignee"],
                "additionalProperties": False,
            },
        }
    },
)
data = json.loads(response.output_text)
```

Strict mode requirements (enforced by the SDK's schema helper, which sets both automatically for Pydantic models):

- Every object sets `additionalProperties: false`.
- Every property appears in `required`; represent "optional" as a union with `null`.
- `name` uses letters, digits, underscores or dashes, at most 64 characters.
- Only a subset of JSON Schema is supported; if the API rejects a keyword, simplify the schema (the structured outputs guide lists the supported subset and limits on depth and size).

Parse helpers:

- Python: `client.responses.parse(model=..., input=..., text_format=MyModel)` sets a strict schema from the Pydantic model and fills `response.output_parsed`. Streaming variant: `with client.responses.stream(..., text_format=MyModel) as s:` then `s.get_final_response().output_parsed`.
- Node: `text: { format: zodTextFormat(Schema, 'name') }` with `client.responses.parse(...)`. `responses.create` with the same format does not auto-parse. Zod 3.25+ or 4 is the optional peer dependency.

Handling failures:

- A refusal appears as a `refusal` content part and `output_parsed` is `None`; do not retry blindly.
- `status == "incomplete"` means truncated output; the JSON may be cut off. Raise `max_output_tokens` (reasoning tokens count too) or shrink the schema.
- Schema-valid does not mean correct. Validate business rules (ranges, IDs exist, permissions) after parsing.
- The older `{"type": "json_object"}` mode only guarantees syntactically valid JSON and is not recommended for newer models.

Function calling versus structured output: use `text.format` when the final answer itself must have a shape; use function tools when the model needs to trigger your code or fetch data first.

Chat Completions equivalent for legacy code: `response_format={"type": "json_schema", "json_schema": {"name": ..., "strict": True, "schema": ...}}` and `client.chat.completions.parse(response_format=Model)`.

## 6. Prompt-injection posture for tools

- Instruct the model that retrieved content, web pages and tool results are data, and keep them out of `instructions`.
- Give each request the smallest tool set; use `allowed_tools` to narrow it per step.
- Authorize each action in your handler using the authenticated user, not the model's claim.
- Require human approval for irreversible actions and show the exact arguments.
- Log tool name, arguments hash, caller identity and outcome for audit.
