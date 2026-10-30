# Migration from the Legacy SDKs

Mapping from the deprecated `google-generativeai` (Python) and `@google/generative-ai` (JavaScript) packages to the Google Gen AI SDK. Verified against google-genai 2.34.0 and @google/genai 2.32.0 (2026-10). The legacy repository README states that development is limited to critical fixes and that all support ended on 2025-11-30; PyPI still lists `google-generativeai` 0.8.6 (December 2025) as its last release. Legacy call shapes below describe those packages' public API for recognition; Google's migration guide is the authority for edge cases.

## 1. Why migrate

- One SDK covers the Gemini Developer API and Gemini Enterprise Agent Platform (formerly Vertex AI), plus Files, caches, batches, chats, Live and the Interactions API.
- Legacy packages receive no new features, and new model features (thinking controls, newer tools, newer models) arrive only in the new SDK.
- The new SDK uses a client object instead of global configuration, so multiple keys, projects or backends can coexist in one process.

## 2. Python mapping

| Legacy (`google.generativeai`) | Current (`google.genai`) |
|---|---|
| `import google.generativeai as genai` | `from google import genai` and `from google.genai import types` |
| `genai.configure(api_key=KEY)` | `client = genai.Client(api_key=KEY)` or env `GEMINI_API_KEY` |
| `model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=...)` | no model object; pass `model="..."` per call and `system_instruction` in config |
| `model.generate_content(prompt)` | `client.models.generate_content(model=MODEL, contents=prompt)` |
| `generation_config=genai.GenerationConfig(temperature=...)` | fields directly on `types.GenerateContentConfig(temperature=...)` |
| `safety_settings={...}` | `config=types.GenerateContentConfig(safety_settings=[types.SafetySetting(category=..., threshold=...)])` |
| `model.generate_content(prompt, stream=True)` | `client.models.generate_content_stream(model=, contents=)` |
| `await model.generate_content_async(...)` | `await client.aio.models.generate_content(...)` |
| `chat = model.start_chat(history=[...])` | `chat = client.chats.create(model=MODEL, history=[...], config=...)` |
| `chat.send_message(text)` | `chat.send_message(text)` (same name) |
| `genai.upload_file(path)` | `client.files.upload(file=path)` |
| `genai.get_file(name)`, `genai.delete_file(name)` | `client.files.get(name=)`, `client.files.delete(name=)` |
| `genai.caching.CachedContent.create(model=, contents=, ttl=timedelta)` | `client.caches.create(model=, config=types.CreateCachedContentConfig(contents=, ttl="3600s"))` |
| `GenerativeModel.from_cached_content(cache)` | `config=types.GenerateContentConfig(cached_content=cache.name)` |
| `genai.embed_content(model="models/text-embedding-004", content=...)` | `client.models.embed_content(model="gemini-embedding-001", contents=...)` |
| `tools=[python_function]` on the model | `config=types.GenerateContentConfig(tools=[python_function])` |
| `enable_automatic_function_calling=True` on `start_chat` | automatic calling is on by default for callables; disable with `AutomaticFunctionCallingConfig(disable=True)` |
| `response_mime_type` and `response_schema` in `GenerationConfig` | same names in `GenerateContentConfig`; prefer `response_json_schema` for standard JSON Schema |
| `genai.list_models()` | `client.models.list()` |
| `response.text`, `response.candidates`, `response.usage_metadata` | same attributes |

## 3. JavaScript mapping

| Legacy (`@google/generative-ai`) | Current (`@google/genai`) |
|---|---|
| `new GoogleGenerativeAI(key)` | `new GoogleGenAI({ apiKey: key })` |
| `genAI.getGenerativeModel({ model })` | no model object; pass `model` per call |
| `const result = await model.generateContent(prompt)` | `const response = await ai.models.generateContent({ model, contents: prompt })` |
| `result.response.text()` (a method) | `response.text` (a property) |
| `generateContentStream` returns `{ stream }` | `await ai.models.generateContentStream({...})` is itself async-iterable; read `chunk.text` |
| `model.startChat({ history })` | `ai.chats.create({ model, history, config })` |
| `generationConfig`, `systemInstruction`, `tools` on the model | all inside the `config` object of each call |
| `GoogleAIFileManager` (separate import) | `ai.files.upload({ file, config: { mimeType } })` |

## 4. Model ID replacement

- Gemini 1.5 IDs (`gemini-1.5-flash`, `gemini-1.5-pro` and `-latest` variants) are not in the current SDK model list, and Google's JS codegen guide lists them as prohibited. Replace them with a current ID from the models page; the rolling aliases `gemini-flash-latest`, `gemini-flash-lite-latest` and `gemini-pro-latest` appear in the SDK list.
- Older text embedding IDs such as `text-embedding-004` are not in the current examples; the README uses `gemini-embedding-001`. Re-embed the corpus after changing embedding models, since vectors from different models are not comparable.
- The legacy prefix `models/` was part of many legacy examples; the current README examples pass bare IDs such as `gemini-flash-latest`.
- Response metadata can tell you about retirement: on the Developer API, `response.model_status` carries `model_stage` (`PREVIEW`, `STABLE`, `LEGACY`, `DEPRECATED`, `RETIRED` and others) and `retirement_time`. Log it.

## 5. Migration steps

1. Search the codebase: `google.generativeai`, `generativeai`, `GenerativeModel`, `@google/generative-ai`, `GoogleGenerativeAI`, `gemini-1.5`, `text-embedding-004`.
2. Replace the dependency: remove `google-generativeai` from requirements and add `google-genai` (Python 3.11 or newer for 2.34.0); in JS remove `@google/generative-ai` and add `@google/genai` (Node 20 or newer).
3. Create a single client module and replace global `configure(...)` calls with it.
4. Convert each call site using the tables above; move generation parameters into the config object.
5. Convert chats, file uploads and caches; check file `state` handling (poll until `ACTIVE`).
6. Choose current model IDs from configuration and run your evals against them; behavior and output length differ between model generations.
7. Review thinking: newer models may think by default, which consumes `max_output_tokens`; set `thinking_config` and raise the token limit where needed.
8. Review safety settings: category names and threshold enums are `HARM_CATEGORY_*` and `BLOCK_*` strings or enum members; confirm any previously relaxed settings are still needed.
9. Replace response parsing: `response.text` is a property in JS now; null-check results.
10. Remove the legacy dependency and add a lint rule or CI grep that blocks re-introduction.

## 6. Before and after

```python
# Legacy (do not write new code like this)
import google.generativeai as genai
genai.configure(api_key=KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
reply = model.generate_content("Summarize this.", generation_config={"temperature": 0.2})
print(reply.text)
```

```python
# Current
from google import genai
from google.genai import types

client = genai.Client()  # GEMINI_API_KEY from the environment
reply = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Summarize this.",
    config=types.GenerateContentConfig(temperature=0.2),
)
print(reply.text)
```

```ts
// Legacy (do not write new code like this)
// const genAI = new GoogleGenerativeAI(key);
// const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });
// const result = await model.generateContent('Summarize this.');
// console.log(result.response.text());

// Current
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const response = await ai.models.generateContent({
  model: 'gemini-flash-latest',
  contents: 'Summarize this.',
  config: { temperature: 0.2 },
});
console.log(response.text);
```

## 7. Behavior differences to expect

- Default API surface: the new SDK targets beta endpoints by default; set `api_version="v1"` in `HttpOptions` for stable endpoints.
- Automatic function calling is the default when you pass callables; the README announces a change in the next major version, so prefer explicit loops.
- Errors are `google.genai.errors.APIError` subclasses, not the legacy `google.api_core` exceptions; update `except` clauses and retry decorators.
- Retries are configured through `HttpOptions.retry_options`, not through `request_options` on each call.
- Timeouts are in milliseconds in `HttpOptions`.
- The `Content`, `Part`, `Tool` and config classes are Pydantic models in `google.genai.types`; dictionaries are accepted wherever those types are.
