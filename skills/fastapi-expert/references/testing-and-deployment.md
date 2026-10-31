# Testing, Deployment and Operations

pytest layout, `TestClient`, `httpx.AsyncClient` with `ASGITransport`, `dependency_overrides`, test databases, lifespan in tests, and tests for auth, background tasks, WebSockets and SSE. The conftest below was run with FastAPI 0.162.0, Starlette 1.10.0, httpx 0.28.1, pytest 9.2.0, anyio 4.15.1, SQLAlchemy 2.1.6 and aiosqlite 0.22.1 (2026-10). The `fastapi` CLI, uvicorn and gunicorn workers, containers, proxy headers, health checks, shutdown, logging and OpenAPI customisation for FastAPI 0.162.0 with fastapi-cli 0.0.32, Uvicorn 0.54.0, gunicorn 26.2.0 and uvicorn-worker 0.4.0. CLI options were read from `--help` output, worker setups were started locally, and the deployment guidance follows the FastAPI deployment pages (2026-10). Container image hardening belongs to docker-expert; reverse proxy tuning to nginx-expert.

## Contents

1. [Which client to use](#1-which-client-to-use)
2. [Configuration](#2-configuration)
3. [Conftest with a test database](#3-conftest-with-a-test-database)
4. [Writing tests](#4-writing-tests)
5. [Dependency overrides](#5-dependency-overrides)
6. [Lifespan, background tasks and SSE](#6-lifespan-background-tasks-and-sse)
7. [pytest-asyncio instead of anyio](#7-pytest-asyncio-instead-of-anyio)
8. [CI order](#8-ci-order)
9. [The fastapi CLI](#9-the-fastapi-cli)
10. [Workers and process managers](#10-workers-and-process-managers)
11. [Containers](#11-containers)
12. [Behind a proxy](#12-behind-a-proxy)
13. [Health checks and shutdown](#13-health-checks-and-shutdown)
14. [Logging and observability](#14-logging-and-observability)
15. [OpenAPI customisation](#15-openapi-customisation)
16. [Release checklist](#16-release-checklist)

## 1. Which client to use

| Need | Client |
|---|---|
| Plain request and response checks, simplest | `TestClient(app)` in sync tests |
| Lifespan, `request.state`, WebSockets | `with TestClient(app) as client:` |
| The test itself must `await` (async fixtures, direct DB checks) | `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")` in async tests |

- `TestClient` is Starlette's. In Starlette 1.10.0 it imports `httpx2` and falls back to `httpx` with a `StarletteDeprecationWarning`; `fastapi[standard]` installs both. If you install plain `fastapi` for tests, add `httpx2` (or `httpx`) yourself.
- `httpx.AsyncClient(app=app)` no longer exists in httpx 0.28; use `ASGITransport` (verified: `TypeError ... unexpected keyword argument 'app'`). `httpx2` also exposes `ASGITransport` and `AsyncClient`; match the package to what your project depends on.
- `ASGITransport` does not run lifespan. For lifespan with an async client, use the `asgi-lifespan` package's `LifespanManager` (suggested by the FastAPI docs) or override the dependencies lifespan would have created.
- A sync test function cannot depend on an async fixture (pytest raises an error); keep sync tests on sync fixtures.

## 2. Configuration

```toml
[tool.pytest]
pythonpath = ["."]          # lets tests import the `app` package
filterwarnings = ["error::DeprecationWarning"]
```

- The native `[tool.pytest]` table is available in pytest 9; `[tool.pytest.ini_options]` still works.
- Async tests with AnyIO's bundled plugin need `@pytest.mark.anyio` (or `pytestmark = pytest.mark.anyio`) and a session-scoped `anyio_backend` fixture returning `"asyncio"`.
- Set environment variables for settings in `conftest.py` before importing the app, or override `get_settings` (see [dependencies-and-lifespan.md](dependencies-and-lifespan.md)).

## 3. Conftest with a test database

```python
import os

os.environ.setdefault("APP_JWT_SECRET", "test-secret-not-for-production-0123456789")
os.environ.setdefault("APP_DATABASE_URL", "sqlite+aiosqlite://")

from collections.abc import AsyncIterator, Iterator  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def maker() -> AsyncIterator[async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,  # one shared in-memory connection
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def override(maker: async_sessionmaker) -> Iterator[None]:
    async def _get_session() -> AsyncIterator:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sync_client() -> Iterator[TestClient]:
    with TestClient(app) as c:  # "with" runs lifespan
        yield c
```

- Every test gets a fresh empty database because `maker` is function scoped. For a production-like database (PostgreSQL in a container), create the schema once per session and wrap each test in a transaction that is rolled back.
- Environment variables are set before `from app.main import app` because `get_settings()` is cached.

## 4. Writing tests

```python
import httpx
import pytest

pytestmark = pytest.mark.anyio


async def login(client: httpx.AsyncClient) -> dict[str, str]:
    r = await client.post(
        "/token", data={"username": "alice", "password": "correct horse battery staple"}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_requires_auth(client: httpx.AsyncClient) -> None:
    assert (await client.get("/items")).status_code == 401


async def test_create_hides_internal_fields(client: httpx.AsyncClient) -> None:
    headers = await login(client)
    r = await client.post("/items", json={"name": "a", "internal_note": "x"}, headers=headers)
    assert r.status_code == 201
    assert r.json() == {"id": 1, "name": "a", "owner": "alice"}
    assert (await client.get("/items/99", headers=headers)).status_code == 404


async def test_validation_error(client: httpx.AsyncClient) -> None:
    headers = await login(client)
    r = await client.post("/items", json={"name": ""}, headers=headers)
    assert r.status_code == 422
```

- Login through `/token` with form `data=`, not `json=`.
- Assert the full response body for output models, so a leaked field fails the test.
- Parametrize validation cases: `@pytest.mark.parametrize("payload", [{}, {"name": ""}, {"name": "x" * 101}])`.
- Cover each guard: no token (401), wrong owner (404 or 403), invalid body (422), duplicate (409).
- Sync version: `def test_x(sync_client): r = sync_client.get("/items"); assert r.status_code == 401`.

## 5. Dependency overrides

```python
from app.config import Settings, get_settings
from app.security import get_current_user


def test_with_fake_user(sync_client):
    app.dependency_overrides[get_current_user] = lambda: "bob"
    try:
        ...  # requests now run as "bob" without a token
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

- Keys are the original callables; the replacement may be a function with its own parameters and sub-dependencies.
- Always clear overrides (fixture teardown or `finally`), because `app` is a module-level object shared by all tests.
- Override outbound clients (payment, email) with fakes; do not let tests call real services.
- Prefer overriding `get_session` with a test database to mocking SQLAlchemy calls.

## 6. Lifespan, background tasks and SSE

```python
def test_lifespan_state(sync_client):
    r = sync_client.get("/ping")          # uses request.state set by lifespan
    assert r.status_code == 200


def test_sse(sync_client):
    r = sync_client.get("/events")        # route declared with EventSourceResponse
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: tick" in r.text
```

- Background tasks have already run when the `TestClient` call returns (verified: the task logged before the next statement). Assert on their side effects directly.
- WebSockets: `with client.websocket_connect("/ws") as ws: ws.send_text("hi"); assert ws.receive_text() == "..."`.
- For SSE, `ServerSentEvent(data=..., event=...)` yields `event:` and `data:` lines, and the content type is `text/event-stream`; the check above matched on 0.162.0.
- Test shutdown logic by leaving the `with TestClient(app)` block and asserting that resources are closed.

## 7. pytest-asyncio instead of anyio

- pytest-asyncio 1.4.1 works too: `@pytest.mark.asyncio` on tests, `@pytest_asyncio.fixture` on async fixtures in strict mode, and set `asyncio_mode` and `asyncio_default_fixture_loop_scope` explicitly (the plugin raises a deprecation warning when the latter is unset, and `-W error` turns it into an error).
- Do not enable both plugins' markers on the same tests. Pick one per project.
- Create loop-bound objects (engines, clients) inside fixtures, not at import time, to avoid "attached to a different loop" errors.

## 8. CI order

```bash
ruff format --check . && ruff check .
mypy app            # or pyright
pytest -q -W error::DeprecationWarning --cov=app
```

- Run tests against the dependency versions in the lockfile, and once per release train against the newest FastAPI to catch deprecations early.
- Regenerate and diff the OpenAPI document (`python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))"`) in CI when clients are generated from it.

## 9. The fastapi CLI

```bash
pip install "fastapi[standard]"
fastapi dev app/main.py            # development: reload on, host 127.0.0.1
fastapi run app/main.py --port 8000   # production mode: reload off
fastapi run app/main.py --workers 4   # several worker processes
```

- Commands in 0.0.32: `dev`, `run`, `login`, `deploy`, `cloud` (the last three belong to FastAPI Cloud).
- Options on `run`: `--host`, `--port`, `--reload/--no-reload`, `--workers`, `--root-path`, `--app`, `--entrypoint` / `-e`, `--proxy-headers/--no-proxy-headers`, `--forwarded-allow-ips`, `--verbose`. Run `fastapi run --help` for the installed version.
- Discovery: with no path it tries `main.py`, `app.py`, `api.py`, then the same names under `app/`; the app object is `app` or `api`, otherwise the first `FastAPI` instance found. The `--entrypoint` option takes an import string such as `app.main:app` (check the help text for the exact format in your version).
- `fastapi dev` binds 127.0.0.1; use `--host 0.0.0.0` only in a container or trusted network, and never use reload in production.
- Plain `uvicorn app.main:app --host 0.0.0.0 --port 8000` is equivalent and works without the CLI package.

## 10. Workers and process managers

```bash
# built-in multi-process
fastapi run app/main.py --workers 4
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# gunicorn as process manager, with the maintained worker class
pip install gunicorn uvicorn-worker
gunicorn app.main:app -k uvicorn_worker.UvicornWorker -w 4 -b 0.0.0.0:8000
```

- Verified: `fastapi run --workers 2` and `gunicorn ... -k uvicorn_worker.UvicornWorker -w 2` both started and served requests.
- The FastAPI docs recommend `--workers` for a single host and one process per container under Kubernetes or another orchestrator, where replication is the orchestrator's job.
- `uvicorn-worker` provides `UvicornWorker` (and `UvicornH11Worker`) for gunicorn; the older `uvicorn.workers` module is deprecated, so check the uvicorn documentation before using it.
- Uvicorn's own recycling flags: `--limit-max-requests` and `--limit-max-requests-jitter` restart workers periodically; gunicorn has `--max-requests` and `--max-requests-jitter`. Use them as a leak mitigation, not a design.
- Choose the worker count from CPU cores and measured throughput. Each worker has its own lifespan, connection pool and caches, so total database connections scale with workers.
- Free-threaded Python 3.14t has been supported by FastAPI since 0.136.0; test every native dependency before using it in production.

## 11. Containers

```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /code

COPY requirements.txt .
RUN pip install --upgrade -r requirements.txt

COPY ./app ./app

RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8000
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
```

- Use the exec (JSON array) form of `CMD`, as the FastAPI docs require, so signals reach the process and lifespan shutdown runs; the shell form wraps the server in `/bin/sh`.
- Copy the requirements file first for layer caching. Generate it from a lockfile: `uv export --format requirements-txt --no-dev --no-emit-project --output-file requirements.txt` (command from the FastAPI docs; regenerate when `uv.lock` changes).
- The old FastAPI-specific base images are deprecated; build from the official Python image and pick a current tag.
- Behind a TLS-terminating proxy add `--proxy-headers`. In Kubernetes run one process per container and scale replicas; use `--workers` for a single-host Compose setup.
- Do not bake `.env` files or secrets into the image; pass settings as environment variables or mounted secrets.
- Run as a non-root user, keep the filesystem read-only where possible, and add a health check (below).

## 12. Behind a proxy

- A TLS-terminating proxy (Nginx, Traefik, a cloud load balancer) forwards the original scheme and client IP in `X-Forwarded-*` headers. Run with `--proxy-headers` so redirects and `request.url` use `https`, and restrict `--forwarded-allow-ips` to the proxy address instead of trusting everyone.
- If the proxy strips a path prefix (`/api`), the app needs to know the prefix for docs and generated URLs: use the CLI or uvicorn `--root-path`. The `root_path` argument of `FastAPI()` is deprecated since 0.146.0; check the current "Behind a Proxy" docs.
- Let the proxy enforce request size limits, timeouts and TLS; the app should still bound uploads and set outbound timeouts.
- WebSockets and SSE need proxy settings that disable response buffering and allow long reads.

## 13. Health checks and shutdown

```python
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import text

app = FastAPI()


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}  # liveness: no dependencies


@app.get("/readyz", include_in_schema=False)
async def readyz(request: Request) -> dict[str, str]:
    try:
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ready"}
```

- Liveness answers "is the process responsive"; readiness answers "can it serve traffic now". Do not make liveness depend on the database or a restart loop follows an outage.
- On SIGTERM uvicorn stops accepting connections, finishes in-flight requests, then runs lifespan shutdown. Set `--timeout-graceful-shutdown` (uvicorn) or `--graceful-timeout` (gunicorn) lower than the orchestrator's kill timeout (for example Kubernetes `terminationGracePeriodSeconds`).
- Long-lived streams (SSE, WebSockets) keep connections open and delay shutdown; close them from the lifespan exit code or a shutdown event.
- Migrations: run Alembic as a separate step before rolling out new replicas; see [database-sqlalchemy.md](database-sqlalchemy.md).

## 14. Logging and observability

- Configure logging once at start-up (JSON to stdout) and attach a request ID in middleware; keep tokens, passwords and full bodies out of logs.
- Uvicorn's access log can be disabled (`--no-access-log`) when the proxy already logs requests.
- FastAPI declares an optional `opentelemetry` extra; exporter setup is opt-in since 0.143.0. Check the release notes before enabling it.
- Export metrics at the proxy or with a maintained Prometheus middleware; track request rate, latency percentiles, error rate, event-loop lag and pool saturation.
- Profile slow endpoints with `py-spy` or `cProfile`; the usual culprit is a blocking call in `async def` (see the SKILL performance section).

## 15. OpenAPI customisation

```python
from fastapi import FastAPI

tags_metadata = [{"name": "items", "description": "Operations on items"}]


def custom_route_id(route) -> str:
    prefix = route.tags[0] if route.tags else "default"  # untagged routes have no tags
    return f"{prefix}-{route.name}"


app = FastAPI(
    title="Items API",
    version="1.2.0",
    summary="Manage items",
    description="Longer **markdown** description.",
    openapi_tags=tags_metadata,
    generate_unique_id_function=custom_route_id,
    docs_url="/docs",             # None disables Swagger UI
    redoc_url=None,
    openapi_url="/openapi.json",  # None disables the schema and both UIs
)
```

- Prefer constructor arguments: `title`, `version`, `summary`, `description`, `openapi_tags`, `servers`, `contact`, `license_info`, `terms_of_service`, `swagger_ui_parameters`, `generate_unique_id_function`.
- Per route: `summary`, `description`, `response_description`, `responses={404: {"model": ErrorOut}}`, `deprecated=True`, `operation_id`, `include_in_schema=False`, `openapi_extra={...}`.
- Set stable `operation_id` values (via `generate_unique_id_function`) when generating client SDKs; default IDs include the function name and path.
- Pydantic extras: `Field(examples=[...])`, `model_config = ConfigDict(json_schema_extra={"examples": [...]})`. Parameter metadata uses `json_schema_extra`; the old `**extra` keywords on `Query` and friends were removed in 0.155.0.
- To patch the whole schema, override `app.openapi` with a function that builds it once with `fastapi.openapi.utils.get_openapi(...)`, edits the dict, caches it in `app.openapi_schema` and returns it.
- Mount a second `FastAPI` app (`app.mount("/v2", v2)`) to serve an independently versioned schema.

## 16. Release checklist

- [ ] `fastapi run` (no reload) with exec-form `CMD`; non-root user; secrets from the environment.
- [ ] One process per container under an orchestrator, or `--workers N` sized against CPU and database connections.
- [ ] `--proxy-headers` with a narrow `--forwarded-allow-ips` behind a proxy.
- [ ] Liveness and readiness endpoints; graceful timeout below the orchestrator kill timeout.
- [ ] Migrations run before rollout; they are backward compatible with the previous version.
- [ ] Docs and OpenAPI disabled or protected on private APIs.
- [ ] Release notes read for each FastAPI, Pydantic and Starlette upgrade; tests pass with deprecation warnings as errors.
