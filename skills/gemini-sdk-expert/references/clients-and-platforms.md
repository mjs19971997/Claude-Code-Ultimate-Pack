# Clients, Platforms and HTTP Options

Reference for creating Gemini clients against the Gemini Developer API and Gemini Enterprise Agent Platform (the SDK documents it as the product previously called Vertex AI), plus transport, retry and proxy options. Verified against google-genai 2.34.0 and @google/genai 2.32.0 source and READMEs (2026-10). Product naming is changing; the older names (`vertexai`, Vertex AI) still appear in flags, environment variables and URLs.

## 1. Choosing a backend

| | Gemini Developer API | Gemini Enterprise Agent Platform |
|---|---|---|
| Auth | API key | Google Cloud credentials (Application Default Credentials or explicit `credentials`) |
| Required settings | `api_key` | `enterprise=True`, `project`, `location` |
| Files API | Yes | No (use `gs://` URIs) |
| Quota and billing | Per API key / project in AI Studio | Per Google Cloud project |
| Data and region controls | Per Gemini API terms | Google Cloud project, IAM, location, organization policies |
| Some SDK features | Interactions API, `model_status` metadata | Batch via GCS or BigQuery, some enterprise tools |

Pick by organization policy and required features. Keep model IDs, quotas and feature availability per backend in your configuration, because they are not identical.

## 2. Python clients

```python
from google import genai
from google.genai import types

# Gemini Developer API
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Gemini Enterprise Agent Platform (uses Application Default Credentials)
client = genai.Client(enterprise=True, project="my-project", location="global")
```

- Environment-driven construction: `genai.Client()` with `GEMINI_API_KEY` or `GOOGLE_API_KEY` (the latter wins if both are set), or with `GOOGLE_GENAI_USE_ENTERPRISE=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`.
- `enterprise` replaces the older `vertexai` flag (still accepted). Setting both with conflicting values raises `ValueError`. `GOOGLE_GENAI_USE_VERTEXAI` is still read as a legacy variable.
- Local development for Agent Platform: `gcloud auth application-default login`. In production prefer an attached service account or workload identity; do not store key files in repositories or images.
- Context managers close underlying connections: `with genai.Client() as client:` and `async with genai.Client().aio as aclient:`; otherwise call `client.close()` or `await aclient.aclose()` (the async client is `client.aio`) as the README shows.
- Async uses the same surface under `client.aio` (`client.aio.models.generate_content`, `client.aio.chats.create`, `client.aio.files`).
- Branch on `client.vertexai` (the boolean property defined on the client in 2.34.0; one README example uses `client.enterprise`, which the client source does not define) when code must differ between backends, or keep the choice in your own settings.

## 3. JavaScript clients

```ts
import { GoogleGenAI } from '@google/genai';

const dev = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const platform = new GoogleGenAI({
  enterprise: true,
  project: process.env.GOOGLE_CLOUD_PROJECT,
  location: process.env.GOOGLE_CLOUD_LOCATION,
});
```

- Node reads `GOOGLE_API_KEY`, or `GOOGLE_GENAI_USE_ENTERPRISE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` when constructed without arguments. `vertexai: true` remains as the legacy option.
- Requires Node 20 or newer today; the README announces Node 22 or newer from SDK 3.0.0.
- The README repeats that API keys must not be exposed in client-side code. Browser builds work, but only use a key there if it is a deliberately restricted, disposable key; otherwise call your own backend.
- `GoogleAuthOptions` from google-auth-library are accepted for Agent Platform auth.

## 4. API versions

- The SDK defaults to beta endpoints so preview features work.
- Python: `http_options=types.HttpOptions(api_version="v1")` (stable) or `"v1alpha"` (Developer API alpha features such as some experimental capabilities).
- JS: `apiVersion: 'v1'` in the constructor options.
- Stable endpoints may lack preview features; pick the version per feature and test.

## 5. HttpOptions

```python
http_options = types.HttpOptions(
    api_version="v1",
    timeout=60_000,                              # milliseconds
    headers={"x-request-source": "billing-bot"},
    retry_options=types.HttpRetryOptions(
        attempts=4, initial_delay=1.0, max_delay=30.0, exp_base=2.0, jitter=1.0,
        http_status_codes=[408, 429, 500, 502, 503, 504],
    ),
)
client = genai.Client(http_options=http_options)
```

- Other fields: `base_url`, `base_url_resource_scope`, `extra_body`, `client_args`, `async_client_args`, `httpx_client`, `httpx_async_client`, `aiohttp_client`.
- Per-request override: `config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=120_000))`.
- Custom `base_url` (for a gateway) can bypass project and key checks; with `base_url_resource_scope=types.ResourceScope.COLLECTION` the resource path omits version, project and location. Use only with a gateway you control and that adds the credentials.
- HTTP transports: the default is `httpx`; install `google-genai[aiohttp]` for a faster async client, or `google-genai[httpx2]` and set `GOOGLE_GENAI_HTTP_CLIENT=httpx2` (or inject `httpx2.Client`) to opt into HTTPX2.
- Proxies: set `HTTPS_PROXY` and, for custom CAs, `SSL_CERT_FILE` before creating the client; SOCKS proxies need `httpx[socks]` and `client_args={'proxy': 'socks5://...'}`.
- JS `httpOptions`: `baseUrl`, `apiVersion`, `headers`, `timeout` (ms), `retryOptions`, `fetch`, `extraBody`.

## 6. Observability and limits

- Log `response.response_id`, `model_version`, `usage_metadata` and, on the Developer API, `model_status` (stage and retirement time).
- Rate-limit errors are `ClientError` with code 429; reduce concurrency with a semaphore and rely on `retry_options` for transient cases.
- Keep one client per process. Creating a client per request wastes connections and skips reuse.
- Track SDK versions: the READMEs announce breaking changes for the next major (automatic function calling moves to Chats, some Live and video parameters are removed, `GenerationConfigThinkingConfig` is replaced by `ThinkingConfig`). Pin `google-genai<3.0.0` and `@google/genai<3.0.0` until reviewed.
