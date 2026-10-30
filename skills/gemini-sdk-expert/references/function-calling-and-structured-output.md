# Function Calling, Structured Output, Thinking and Safety

Reference for tool use, JSON schemas, thinking configuration, safety settings and error handling in the Google Gen AI SDK. Verified against google-genai 2.34.0 and @google/genai 2.32.0 type definitions and READMEs (2026-10). Behavior that depends on the model (thinking support, schema subsets, tool availability) is noted as such; confirm it on the current model and feature pages.

## 1. Function declarations

Python:

```python
from google.genai import types

declaration = types.FunctionDeclaration(
    name="get_order_status",
    description="Look up the status of one order by its id.",
    parameters_json_schema={
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "Order id such as A-1042"}},
        "required": ["order_id"],
    },
)
tool = types.Tool(function_declarations=[declaration])
config = types.GenerateContentConfig(tools=[tool])
```

TypeScript:

```ts
const declaration: FunctionDeclaration = {
  name: 'get_order_status',
  description: 'Look up the status of one order by its id.',
  parametersJsonSchema: {
    type: 'object',
    properties: { order_id: { type: 'string' } },
    required: ['order_id'],
  },
};
const config = { tools: [{ functionDeclarations: [declaration] }] };
```

- `parameters_json_schema` takes standard JSON Schema; the older `parameters` field takes the OpenAPI-style `Schema` type.
- Good descriptions matter more than clever names. Use `enum` for closed value sets.
- Other tool types sit in the same `types.Tool`: `google_search`, `url_context`, `code_execution`, `file_search`, `google_maps`, `retrieval`, `computer_use`, `mcp_servers`. Availability differs by model and backend.

## 2. Modes and tool config

`types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode=..., allowed_function_names=[...]))`

| Mode | Behavior |
|---|---|
| `AUTO` | Model chooses between text and function calls (default) |
| `ANY` | Model must call a function; combine with `allowed_function_names` to force one |
| `NONE` | Model must not call functions |
| `VALIDATED` | Present in the SDK enum; check the function calling guide for its semantics |

JS: `toolConfig.functionCallingConfig.mode = FunctionCallingConfigMode.ANY` and `allowedFunctionNames`.

## 3. Manual loop

1. Call `generate_content` with `automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)` when you pass callables, or pass only declarations.
2. `response.function_calls` is a list of `FunctionCall` objects with `id` (when provided), `name` and `args`.
3. Append the model's content exactly as returned: `contents.append(response.candidates[0].content)`. This preserves `thought_signature` values and call IDs that the model needs on the next turn.
4. Append one `Content(role="tool", parts=[...])` whose parts are `FunctionResponse(id=call.id, name=call.name, response={...})`.
5. The `response` object uses the key `output` for results and `error` for failures; if neither key is present the whole object is treated as the output.
6. Repeat until a response has no function calls, with a turn cap.

Parallel calls arrive as several `function_calls` in one response; answer all of them in one `tool` content, matched by `id`.

Some function calls can run without blocking the conversation (`will_continue`, `scheduling`) in Live sessions; those fields are not needed for ordinary request/response loops.

Streaming: `FunctionCallingConfig(stream_function_call_arguments=True)` exists in the SDK for partial arguments (`partial_args`, `will_continue`); check the guide for model support before use.

## 4. Automatic function calling

- Pass Python callables in `tools=[fn]`. The SDK builds the declaration from type hints and the docstring, runs the function, sends the result, and loops up to `maximum_remote_calls` (default 10).
- The README warns that a future major version will no longer run automatic calling from direct `Models.generate_content` calls and will move it to Chats. Pin below 3.0.0 or use manual loops.
- Constrain it: `AutomaticFunctionCallingConfig(maximum_remote_calls=3, ignore_call_history=True)`; the call history is otherwise available in `response.automatic_function_calling_history`.
- Automatic mode runs your function with model-chosen arguments: validate inside the function and take tenant or user identity from closure state, not parameters.
- `google.genai.errors.UnknownFunctionCallArgumentError` is raised when an argument cannot be converted to the annotated type.
- JS: `mcpToTool(mcpClient)` (experimental) turns an MCP client into a tool that is called automatically.

## 5. Structured output

```python
response = client.models.generate_content(
    model=MODEL,
    contents="Extract the invoice.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=Invoice.model_json_schema(),   # Pydantic v2
    ),
)
invoice = Invoice.model_validate_json(response.text)
```

- `response_json_schema` accepts JSON Schema. The SDK docstring lists the supported keywords: `$id`, `$defs`, `$ref`, `$anchor`, `type`, `format`, `title`, `description`, `enum`, `items`, `prefixItems`, `minItems`, `maxItems`, `minimum`, `maximum`, `anyOf`, `oneOf` (treated as `anyOf`), `properties`, `additionalProperties`, `required`, plus the non-standard `propertyOrdering`. Other keywords may be ignored or rejected.
- Cyclic references are unrolled only to a limited depth and are allowed only within non-required properties.
- When `response_json_schema` is set, `response_schema` must be omitted and `response_mime_type` is required.
- `response_schema` takes the OpenAPI-style `Schema`, a Pydantic class or a Python type (and fills `response.parsed`). If it handles your schema badly, switch to `response_json_schema` (SDK docstring advice).
- Do not duplicate the schema or a sample JSON in the prompt; the README says that can reduce quality.
- Truncation (`finish_reason == MAX_TOKENS`) can cut JSON mid-object; raise `max_output_tokens`, remembering thinking tokens count toward usage, and handle parse failures.
- Validation still matters: a schema guarantees shape, not truth.

JS equivalent: `config: { responseMimeType: 'application/json', responseJsonSchema: schema }`; with Zod 4 you can produce the schema with `z.toJSONSchema(Schema)` and validate with `Schema.parse(JSON.parse(response.text))`.

## 6. Thinking

```python
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="LOW", include_thoughts=False),
    max_output_tokens=4000,
)
```

- `thinking_level`: `MINIMAL`, `LOW`, `MEDIUM`, `HIGH` (enum `types.ThinkingLevel`). Google's JS codegen guide ties levels to Gemini 3 models and notes `MINIMAL` and `MEDIUM` are Flash-only there; `HIGH` is the default.
- `thinking_budget`: token count; `0` disables, `-1` lets the model decide. The same guide ties budgets to Gemini 2.5 models, says thinking cannot be turned off for `gemini-2.5-pro`, and gives a minimum of 128 for it. Newer models may differ, so read the thinking page for the model you use.
- `include_thoughts=True` returns thought summaries as parts with `thought=True`; filter them out before showing answers to users unless you intend to display them.
- Usage metadata reports `thoughts_token_count`; the total includes it.
- Thinking tokens count against `max_output_tokens`; a small limit can end the response before an answer appears.
- Set the level per task type, not globally.

## 7. Safety and blocked responses

```python
config = types.GenerateContentConfig(
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        )
    ]
)
```

- Categories in the SDK enum include `HARM_CATEGORY_HARASSMENT`, `HARM_CATEGORY_HATE_SPEECH`, `HARM_CATEGORY_SEXUALLY_EXPLICIT`, `HARM_CATEGORY_DANGEROUS_CONTENT`, `HARM_CATEGORY_CIVIC_INTEGRITY` and others; thresholds are `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, `BLOCK_NONE` and `OFF`. Defaults differ by model; check the safety guide.
- A prompt can be blocked before generation: `response.prompt_feedback.block_reason` (values include `SAFETY`, `OTHER`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `IMAGE_SAFETY`, `JAILBREAK`).
- A candidate can stop early: `candidate.finish_reason` values include `STOP`, `MAX_TOKENS`, `SAFETY`, `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `SPII`, `MALFORMED_FUNCTION_CALL`, `UNEXPECTED_TOOL_CALL`, `TOO_MANY_TOOL_CALLS`, `NO_IMAGE`.
- `MALFORMED_FUNCTION_CALL`: retry once with a simpler declaration or lower thinking; do not execute partial calls.
- Show users a neutral message on blocks and log the reason code, not the content.

## 8. Errors and retries

Python:

```python
from google.genai import errors, types

client = genai.Client(
    http_options=types.HttpOptions(
        timeout=60_000,
        retry_options=types.HttpRetryOptions(attempts=4, initial_delay=1.0, max_delay=30.0),
    )
)
try:
    response = client.models.generate_content(model=MODEL, contents=prompt)
except errors.ClientError as exc:       # 4xx: bad request, auth, quota (429)
    handle_client_error(exc.code, exc.status, exc.message)
except errors.ServerError as exc:       # 5xx
    handle_server_error(exc.code, exc.status)
```

- `HttpRetryOptions` fields: `attempts` (including the first try; default 5 when retry options are given), `initial_delay` (1.0 s), `max_delay` (60 s), `exp_base` (2.0), `jitter` (1.0), `http_status_codes` (default includes 408, 429 and 5xx).
- Do not retry 400, 401, 403 or 404. For 429, reduce concurrency and respect backoff.
- JS: `ApiError` has `status` and `message`; `httpOptions` accepts the same retry fields in camelCase (`attempts`, `initialDelay`, `maxDelay`, `expBase`, `jitter`, `httpStatusCodes`); request configs accept an `abortSignal` for client-side cancellation (the service may still bill for the request).
- Count tokens before large calls with `client.models.count_tokens(model=, contents=)` and read `usage_metadata` after.

## 9. Grounding with Google Search

```python
config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
response = client.models.generate_content(model=MODEL, contents="What changed in the latest release?", config=config)
meta = response.candidates[0].grounding_metadata
queries = meta.web_search_queries if meta else None
sources = meta.grounding_chunks if meta else None
```

- Grounding metadata includes `web_search_queries`, `grounding_chunks`, `grounding_supports` (links text spans to sources) and `search_entry_point`. Check the grounding terms for display requirements.
- Grounded web content is untrusted input; do not let it drive privileged actions.
