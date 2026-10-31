---
name: fastapi-expert
description: >-
  Builds, reviews and ships FastAPI services with Pydantic v2: path operations, APIRouter, Annotated dependencies (yield, scope), response models, pydantic-settings, lifespan, OAuth2 with JWT, async SQLAlchemy 2.x, pytest with TestClient and httpx, and deployment with the fastapi CLI. Use when editing FastAPI apps, main.py or routers, running fastapi dev or fastapi run, uvicorn or gunicorn, or fixing 422 errors, blocked event loops and dependency cleanup bugs. Not for general Python tooling (use python-expert), REST resource design (use rest-api-expert), Django (use django-expert), ML model serving (use ml-engineering-expert) or auth protocol theory (use authentication-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# FastAPI Expert

This skill covers production FastAPI applications on the 0.16x line with Pydantic v2 and Starlette 1.x: routing, dependency injection, request and response models, settings, lifespan, security with OAuth2 and JWT, database access with async SQLAlchemy, testing, the `fastapi` CLI and deployment. It favours typed `Annotated` signatures, small routers and dependencies that own their resources. REST design principles, Python packaging, Django and authentication theory belong to other skills.

> Verified against FastAPI 0.162.0 (release notes and tutorial pages read, example app and tests run locally), Pydantic 2.14.2, pydantic-settings 2.16.2, Starlette 1.10.0, Uvicorn 0.54.0, fastapi-cli 0.0.32, SQLAlchemy 2.1.6 (latest 2.0.x is 2.0.55), Alembic 1.20.1, PyJWT 2.15.1, pwdlib 0.3.1, pytest 9.2.0, httpx 0.28.1 and httpx2 2.16.0, gunicorn 26.2.0, uvicorn-worker 0.4.0, Python 3.13 (2026-10).

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

- Covered: `FastAPI` and `APIRouter`, path, query, header, cookie, body and form parameters (including Pydantic parameter models), `Depends` with `Annotated`, yield dependencies and their exit timing, `response_model`, exception handlers, `BackgroundTasks`, lifespan and app state, pydantic-settings, OAuth2 password flow with JWT, CORS and middleware, SQLAlchemy 2.x async sessions, SQLModel and Alembic in outline, OpenAPI customisation, Server-Sent Events, the `fastapi` CLI, uvicorn and gunicorn deployment, TestClient and httpx `AsyncClient` tests.
- Not covered: Python tooling, typing and packaging (python-expert); resource naming, pagination contracts and versioning policy (rest-api-expert); Django and DRF (django-expert); model loading, batching and GPU serving (ml-engineering-expert); OAuth and OIDC protocol design (authentication-expert); authorization models (authorization-expert); API threat modelling (api-security-expert); Dockerfile and image hardening (docker-expert); reverse proxy tuning (nginx-expert); PostgreSQL schema and query tuning (postgresql-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | FastAPI 0.162.0 needs Python >=3.10, Pydantic >=2.9 and Starlette >=0.46 (Starlette 1.x is supported). Pydantic v1 models are not the path forward; write v2 (`model_config`, `model_validate`, `model_dump`). `fastapi-slim` is no longer published; use `fastapi` |
| Install | `pip install "fastapi[standard]"` adds the `fastapi` CLI, uvicorn, httpx2, httpx, jinja2, python-multipart, email-validator and pydantic-settings. Plain `fastapi` has none of these |
| Dependencies | `Annotated[T, Depends(fn)]` aliases (`SessionDep = Annotated[AsyncSession, Depends(get_session)]`). Results are cached per request (`use_cache=True`). `Depends(fn, scope="function")` ends a yield dependency right after the endpoint function returns; the default `scope="request"` ends it after the response and background tasks. See [references/dependencies-and-lifespan.md](references/dependencies-and-lifespan.md) |
| Yield history | Exit code ran after the response before 0.106.0, before the response from 0.106.0 to 0.117.x, and after the response again since 0.118.0; `scope` was added in 0.121.0. Exceptions caught in a yield dependency are not re-raised automatically since 0.110.0 |
| Lifespan | `FastAPI(lifespan=...)` with an async context manager; `@app.on_event` is deprecated and emits `DeprecationWarning`. Yield a dict (or TypedDict) to expose state as `request.state.<key>` |
| Models | Pydantic v2. Return annotations or `response_model=` filter output. Since 0.151.0 an explicit JSON `null` is validated as `None` and defaults apply only when a key is omitted. Use `model_dump(exclude_unset=True)` for PATCH |
| Parameters | `Annotated[Page, Query()]` binds a Pydantic model to query parameters (also Header, Cookie, Form); `extra="forbid"` rejects unknown parameters with 422. The `**extra` keywords on `Query`, `Path` and similar were removed in 0.155.0; use `json_schema_extra` |
| Requests | Strict `Content-Type` checking for JSON bodies since 0.132.0 (`strict_content_type` argument on `FastAPI` and `APIRouter`); a body sent as `text/plain` fails with 422. Unselected file inputs count as missing since 0.150.0. Omitted `bool` form fields use their default since 0.162.0 |
| Responses | Pydantic serialises the return value directly; `ORJSONResponse` and `UJSONResponse` are deprecated since 0.131.0. Streaming JSON Lines and binary via `yield` since 0.134.0; Server-Sent Events via `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`) since 0.135.0 |
| Async model | `async def` runs on the event loop; `def` runs in AnyIO's worker threadpool (default limiter: 40 threads). Blocking calls in `async def` stall every request |
| Security | `fastapi.security`: `OAuth2PasswordBearer`, `OAuth2PasswordRequestForm`, `HTTPBearer`, `APIKeyHeader`, `SecurityScopes`. The tutorial uses PyJWT (`jwt.encode`, `jwt.decode`, `InvalidTokenError`) and pwdlib with Argon2 (`PasswordHash.recommended()`) |
| CLI | `fastapi dev` (reload, 127.0.0.1) and `fastapi run` (production mode); options include `--host`, `--port`, `--workers`, `--proxy-headers`, `--forwarded-allow-ips`, `--root-path`, `--app`, `--entrypoint`. `fastapi login` and `fastapi deploy` target FastAPI Cloud |
| Database | SQLAlchemy 2.x: `create_async_engine`, `async_sessionmaker(expire_on_commit=False)`, `AsyncSession`, `select()`, `session.scalars()`. With 2.1.6 the asyncio extension raised ImportError until greenlet was installed: use `sqlalchemy[asyncio]`. SQLModel is at 0.0.48 (pre-1.0). See [references/database-sqlalchemy.md](references/database-sqlalchemy.md) |
| Testing | `TestClient` (Starlette; uses httpx2, falls back to httpx with a deprecation warning); `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` for async tests; `app.dependency_overrides`. See [references/testing-and-deployment.md](references/testing-and-deployment.md) |
| Python support | Free-threaded Python 3.14t support was added in 0.136.0; check the release notes before relying on it with your dependency set |

## 3. Workflow

1. Read `pyproject.toml` (or requirements), the app entry point, the router layout, the settings class and the existing tests. Identify the installed FastAPI and Pydantic versions with `pip show fastapi pydantic` and read the release notes between that version and the current one before upgrading.
2. Reproduce the problem with a test or `curl` against `fastapi dev`; inspect `/docs` and `/openapi.json` to confirm what the API contract actually is.
3. Keep to the project's database layer (SQLAlchemy, SQLModel, or another driver) and package manager; do not introduce a second one.
4. Make the smallest change: a typed signature, one dependency, one model. Put shared parameters in `Annotated` aliases rather than repeating `Depends(...)`.
5. Add a test with `TestClient` or `AsyncClient` that fails without the change, including the 401, 403, 404 and 422 paths.
6. Run the project's linter, type checker and `pytest`; for dependency or version changes also run the suite with `-W error::DeprecationWarning`.
7. Check the generated OpenAPI after changing models or routes (`app.openapi()`), and report which commands ran.

## 4. Decision Rules

- If a path operation awaits an async client or driver, use `async def`; if it calls a blocking library (sync SQLAlchemy engine, `requests`, file or CPU work), use plain `def` so FastAPI runs it in the threadpool; if unsure, use `def`. Never put blocking calls in `async def`.
- If a resource must live for the whole process (engine, HTTP client, ML object), create it in `lifespan`; if it is per request (session, transaction), create it in a yield dependency.
- If the exit code of a yield dependency must finish before the response is sent (commit, then report failure to the client), use `Depends(dep, scope="function")`; if the response streams data that uses the resource, keep the default `scope="request"`.
- If work must run after the response and is short and in-process, use `BackgroundTasks`; if it must survive a restart, retry or run elsewhere, use a task queue (a separate worker process). Background tasks must open their own session and take IDs, not ORM objects.
- If the response must hide fields (password hashes, internal notes), declare a separate output model and set `response_model` or the return annotation; do not return ORM or input models directly.
- If an endpoint takes PATCH input, define all fields optional and apply `model_dump(exclude_unset=True)`; an explicit `null` and an omitted key are distinct since 0.151.0.
- If you need several query or header parameters that travel together, use a Pydantic parameter model with `extra="forbid"` instead of a long argument list.
- If the app is behind a TLS-terminating proxy, run with `--proxy-headers` and restrict `--forwarded-allow-ips` to the proxy address; do not trust forwarded headers from the open internet.
- If replicas are managed by Kubernetes or a similar orchestrator, run one process per container; if one host runs several processes, use `fastapi run --workers N` or gunicorn with `uvicorn-worker`.
- If tests need the app's lifespan, use `with TestClient(app)`; `httpx.ASGITransport` does not run lifespan.
- If the team has no preference, use PyJWT with pwdlib (Argon2) as the tutorial does, and `Annotated` dependencies everywhere.

## 5. Coding Standards

- Annotate every path operation parameter and return type. Prefer the return annotation (`-> ItemPublic`) or `response_model=` for output filtering; use `response_model=None` only for responses that return a `Response` directly.
- Use `Annotated` for metadata: `Annotated[int, Query(ge=1, le=100)]`, `Annotated[str, Path(min_length=3)]`, `Annotated[Session, Depends(get_session)]`. Defaults go after `=`, not inside `Query(...)`.
- Name models by role: `ItemCreate`, `ItemUpdate`, `ItemPublic`, `ItemInDB`. Input models never carry server-set fields (`id`, `owner`, `is_admin`).
- Use Pydantic v2 APIs: `model_config = ConfigDict(...)`, `field_validator`, `model_validator`, `from_attributes=True` for ORM objects, `SecretStr` for secrets.
- Use `status.HTTP_201_CREATED` style constants or integer literals consistently; set `status_code` on the decorator for non-200 success.
- Raise `HTTPException(status_code, detail, headers=...)` for expected client errors; register `@app.exception_handler` for domain exceptions. Do not return error dicts with status 200.
- Keep path operation functions thin: parse, call a service function, return. Business logic lives in plain functions or classes that do not import FastAPI.
- Give routers `prefix` and `tags`, and set explicit `operation_id` or `generate_unique_id_function` when clients are generated from the OpenAPI document.
- Use `lifespan`, never `@app.on_event`. Do not read `os.environ` in handlers; inject a settings object.
- Do not use mutable defaults in models (`list[int] = []` is copied by Pydantic, but use `Field(default_factory=list)` for clarity).

## 6. Project Structure

```text
acme-api/
|-- pyproject.toml
|-- alembic.ini
|-- migrations/               # Alembic env.py and versions/
|-- app/
|   |-- __init__.py
|   |-- main.py               # FastAPI(), lifespan, include_router, middleware
|   |-- config.py             # pydantic-settings Settings, get_settings
|   |-- deps.py               # Annotated aliases: SessionDep, CurrentUser, SettingsDep
|   |-- db.py                 # engine factory, session dependency, Base
|   |-- security.py           # hashing, JWT helpers, OAuth2 scheme
|   |-- models/               # SQLAlchemy models
|   |-- schemas/              # Pydantic request and response models
|   |-- routers/              # items.py, users.py, auth.py (one APIRouter each)
|   `-- services/             # business logic without FastAPI imports
`-- tests/
    |-- conftest.py           # client fixtures, dependency_overrides, test database
    `-- test_items.py
```

- `fastapi dev` and `fastapi run` find `main.py`, `app.py` or `api.py` (also under `app/`) and an object named `app` or `api`; pass a path or `--entrypoint` for anything else. A package layout needs `__init__.py` files.
- Keep one `include_router` list in `main.py`; routers import dependencies from `deps.py`, never from `main.py` (avoids circular imports).
- Keep SQLAlchemy models and Pydantic schemas in separate modules even when SQLModel could merge them; the API contract should not change when a column does.

## 7. Design Patterns

- **Annotated dependency aliases**: define `SessionDep`, `CurrentUser`, `SettingsDep` once and reuse them in signatures. Cost: aliases hide the dependency graph from a casual reader, so keep them in one `deps.py`.
- **Session per request**: a yield dependency opens `async with sessionmaker() as session: yield session`; the endpoint or a service commits. Keep the commit in one place (endpoint or service), not in the dependency, unless the project deliberately wraps every request in a transaction.
- **Router-level dependencies**: `APIRouter(dependencies=[Depends(require_admin)])` applies a check to every route without adding an unused parameter. Cost: the dependency result is not available in the handler unless it is also declared there (cached, so it runs once).
- **Settings as a cached dependency**: `@lru_cache def get_settings()` plus `Depends(get_settings)`; tests override it with `app.dependency_overrides`.
- **Lifespan state**: create the engine, HTTP client and caches once, yield them as state, dispose after the `yield`. Access with `request.state.client`.
- **Domain exceptions and handlers**: services raise `DomainError` subclasses; one handler per class maps them to JSON responses. This keeps HTTP out of the service layer.
- **Output model per audience**: `UserPublic` for other users, `UserPrivate` for the owner, `UserAdmin` for staff. Cost: more classes, but the leak surface is explicit.
- **Sub-applications**: `app.mount("/v2", v2_app)` for a separately versioned app with its own docs; routers with a prefix suit most cases.
- **Streaming**: `yield` from an async generator with `EventSourceResponse` for Server-Sent Events, or return `StreamingResponse` for files; keep the generator free of blocking calls.

## 8. Best Practices

- Declare `response_model` (or a return type) on every route that returns data; it validates, filters and documents the output.
- Use `HTTPException` with a stable `detail` string or object that clients can rely on; add `responses={404: {"model": ErrorOut}}` so errors appear in OpenAPI.
- Validate at the edge: constraints in `Field`, `Query`, `Path`; cross-field rules in `model_validator`. Return 422 for shape errors and 409 or 400 for business conflicts.
- Page every list endpoint with bounded `limit` (`le=100`) and a deterministic `order_by`.
- Use `Literal` or `StrEnum` for closed sets of values so OpenAPI lists them.
- Pass the clock, ID generator and external clients through dependencies so tests can replace them.
- Set explicit timeouts on every outbound call (`httpx.AsyncClient(timeout=5.0)`); reuse one client created in lifespan.
- Log with structured fields and a request ID set in middleware; never log tokens, passwords or full bodies.
- Mark deprecated routes with `deprecated=True` and keep them in OpenAPI until clients move.
- Pin dependency versions through a lockfile and read the FastAPI release notes before each minor upgrade; this project line has shipped behavioural changes in 0.x minors (see section 2).

## 9. Performance

- The biggest FastAPI performance bug is a blocking call inside `async def`: `time.sleep`, `requests.get`, a sync database driver, `open().read()` of large files, password hashing, image processing. Move the work to a `def` endpoint, `anyio.to_thread.run_sync` or `asyncio.to_thread`, or a worker process.
- Argon2 hashing is deliberately slow and CPU bound. Call `password_hash.hash(...)` and `verify(...)` from a `def` endpoint or via `await anyio.to_thread.run_sync(...)` so a login burst does not freeze the loop.
- The threadpool for `def` endpoints defaults to 40 threads. Raise it only with a measurement: `anyio.to_thread.current_default_thread_limiter().total_tokens = N` inside lifespan.
- Size connection pools to the work: `create_async_engine(url, pool_size=10, max_overflow=10, pool_pre_ping=True)`, and keep total connections across all workers below the database limit. See [references/database-sqlalchemy.md](references/database-sqlalchemy.md).
- Avoid N+1 queries: use `selectinload` or `joinedload`; with `AsyncSession`, lazy loading raises `MissingGreenlet`, so load relations eagerly.
- Return Pydantic models or let `response_model` serialise; do not build large dicts and then validate them twice. Skip `response_model` validation cost only with measured evidence.
- Add `GZipMiddleware(minimum_size=1000)` for large JSON if no proxy compresses; cache expensive read endpoints with an explicit cache (Redis, `Cache-Control` headers) rather than module globals.
- Scale with processes: `fastapi run --workers N`, or one process per container with more replicas. Measure with a load tool before choosing N; see [references/testing-and-deployment.md](references/testing-and-deployment.md).
- Use `uvloop` and `httptools` (installed by `uvicorn[standard]`) on Linux; profile with `py-spy` or `cProfile` before tuning.

## 10. Security

- Hash passwords with Argon2 through pwdlib (`PasswordHash.recommended()`); verify against a dummy hash when the user does not exist to even out timing. Never store or log plain passwords.
- Sign JWTs with PyJWT. Always pass `algorithms=[...]` to `jwt.decode`, require `exp` and `sub` (`options={"require": [...]}`), keep lifetimes short, and load the key from settings (`SecretStr`), never from source. Generate a key with `openssl rand -hex 32`. Use asymmetric keys (`pyjwt[crypto]`) when other services verify tokens. Details: [references/security-auth.md](references/security-auth.md).
- Authenticate through dependencies (`OAuth2PasswordBearer`, `HTTPBearer`), and check authorization per object: compare `item.owner` with the current user, as in the example in section 14. Return 404 rather than 403 when existence must not leak.
- Configure CORS explicitly: `allow_origins` as a list of exact origins, never `["*"]` together with `allow_credentials=True`; list the methods and headers you need. CORS is a browser rule and does not protect the API from other clients.
- Add `TrustedHostMiddleware` with real hostnames, and HTTPS redirect or HSTS at the proxy. Set `--proxy-headers` and a narrow `--forwarded-allow-ips` only behind a proxy you control.
- Use SQLAlchemy `select()` with bound parameters; if raw SQL is unavoidable use `text("... WHERE id = :id")` with a parameter dict, never f-strings.
- Bound request sizes: limit upload size at the proxy and read `UploadFile` in chunks; validate file type by content, not by the client-supplied filename or content type; never use a client filename as a path.
- Disable interactive docs in production if the API is private (`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`), or protect them.
- Do not expose exception details: the default 500 handler returns a generic body; keep `debug=False`. Do not echo `RequestValidationError` bodies that contain secrets (log them selectively).
- Apply rate limiting at the proxy or with a maintained library, especially on `/token`.
- Keep secrets out of the repository; read them from environment variables or a secret manager through pydantic-settings, and keep `.env` out of version control.

## 11. Testing

- Use pytest with `TestClient(app)` for synchronous tests; wrap it in `with` to run lifespan. Use `httpx.AsyncClient` with `httpx.ASGITransport(app=app)` and an async test marker (`@pytest.mark.anyio` or pytest-asyncio) when the test itself must await.
- Replace infrastructure with `app.dependency_overrides[get_session] = fake` and clear it after each test in a fixture. Override `get_settings` for secrets and URLs. Overrides apply to sub-dependencies too.
- Use a real database in tests when you can: in-memory SQLite with `StaticPool` for unit speed, or the production engine in a container for fidelity. Create and drop tables per test or wrap each test in a rolled-back transaction.
- Test each route for success, validation failure (422), missing or bad credentials (401), forbidden (403) and not found (404). Assert on the response body model, and check that hidden fields are absent.
- Test exception handlers and lifespan side effects directly. Test background tasks by calling the task function, or by asserting after the `TestClient` request returns (tasks have run by then).
- Run with `-W error::DeprecationWarning` so `on_event`, removed parameters and httpx deprecations show up early.
- Details and a complete conftest: [references/testing-and-deployment.md](references/testing-and-deployment.md).

## 12. Review Checklist

- [ ] Every blocking call is in a `def` endpoint, thread, or worker; no `requests`, sync DB driver or `time.sleep` in `async def`.
- [ ] Every returned model is an output model; no password hashes, tokens or internal fields in `response_model`.
- [ ] Dependencies use `Annotated`; yield dependencies close resources in `finally`; `scope` is chosen deliberately.
- [ ] Startup and shutdown use `lifespan`; no `@app.on_event`.
- [ ] Settings come from pydantic-settings; secrets are `SecretStr` and not committed.
- [ ] JWT decode pins `algorithms`, requires `exp`; passwords use Argon2; login handles unknown users.
- [ ] Ownership or role checks exist on every object-level route.
- [ ] CORS origins are explicit; docs are disabled or protected where required.
- [ ] Lists are paginated with a bounded limit and stable order; no N+1 queries.
- [ ] Sessions are closed; background tasks open their own session.
- [ ] Tests cover success, 401, 403, 404, 422; `dependency_overrides` are cleared.
- [ ] The release notes were read for the version change; the suite passes with deprecation warnings as errors.
- [ ] Container runs `CMD` in exec form with `fastapi run`, not `--reload`, and handles SIGTERM.

## 13. Production Notes

- Run `fastapi run app/main.py --port 8000` (production mode, no reload). `fastapi dev` binds 127.0.0.1 with reload and is for development only.
- One process per container is the recommended shape under Kubernetes; use `--workers N` only for a single host or Docker Compose. Each worker has its own pool, caches and lifespan, so multiply pool sizes accordingly.
- Use the exec form of `CMD` (`CMD ["fastapi", "run", "app/main.py", "--port", "8000"]`) so signals reach the process and lifespan shutdown runs. Behind a proxy add `--proxy-headers`.
- Gunicorn is optional: `gunicorn app.main:app -k uvicorn_worker.UvicornWorker -w 4` works with the `uvicorn-worker` package (the old `uvicorn.workers` module is deprecated; check the uvicorn docs). Use it for worker recycling and a process manager, not for speed.
- Expose `/healthz` (liveness, no dependencies) and `/readyz` (checks the database). Set uvicorn's `--timeout-graceful-shutdown` (gunicorn: `--graceful-timeout`) so in-flight requests finish.
- Run Alembic migrations as a separate release step (job or init container), not at import time of every worker.
- Emit logs to stdout as JSON, add a request ID middleware, and export metrics and traces (OpenTelemetry is an optional extra of FastAPI; its exporter setup is opt-in since 0.143.0). See [references/testing-and-deployment.md](references/testing-and-deployment.md).
- Before upgrading across minors, read the release notes: recent minors changed JSON `null` handling (0.151.0), parameter keyword arguments (0.155.0), strict JSON content type (0.132.0) and form defaults (0.162.0).
- `root_path` as a `FastAPI()` argument is deprecated since 0.146.0; for a path-stripping proxy pass `--root-path` to the CLI or uvicorn (check the current docs).

## 14. Examples

Typed dependencies, a protected router and output filtering (the full tested app is built from these pieces):

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Item, get_session
from app.security import get_current_user

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[str, Depends(get_current_user)]


class ItemCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    internal_note: str = ""


class ItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner: str


router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemPublic, status_code=status.HTTP_201_CREATED)
async def create_item(body: ItemCreate, user: CurrentUser, session: SessionDep) -> Item:
    item = Item(name=body.name, owner=user, internal_note=body.internal_note)
    session.add(item)
    await session.commit()
    return item  # internal_note is filtered out by ItemPublic


@router.get("/{item_id}", response_model=ItemPublic)
async def read_item(item_id: int, user: CurrentUser, session: SessionDep) -> Item:
    item = await session.get(Item, item_id)
    if item is None or item.owner != user:  # per-object authorization
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item
```

Lifespan with shared state and an exception handler:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class State(TypedDict):
    http: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        yield {"http": client}  # available as request.state.http


class DomainError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


app = FastAPI(lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": exc.code})
```

Yield dependency timing (output verified on 0.162.0: `req:enter, fn:enter, endpoint, fn:exit, bg:done, req:exit`):

```python
@app.get("/x")
def x(
    tasks: BackgroundTasks,
    a: Annotated[str, Depends(req_dep)],  # exit runs after response and background tasks
    b: Annotated[str, Depends(fn_dep, scope="function")],  # exit runs after the endpoint returns
): ...
```

Pydantic parameter model and PATCH semantics:

```python
class Page(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


@app.get("/things")
def things(page: Annotated[Page, Query()]) -> Page:
    return page  # ?bogus=1 gives 422


class ThingPatch(BaseModel):
    name: str | None = None


@app.patch("/things/{thing_id}")
def patch_thing(thing_id: int, body: ThingPatch) -> dict:
    return body.model_dump(exclude_unset=True)  # {} when omitted, {"name": None} when null
```

## 15. Common Mistakes

- **Blocking call in `async def`** (`requests`, sync SQLAlchemy, `time.sleep`): every other request waits. Use an async client or a `def` endpoint.
- **Returning the database model or input model**: leaks `password_hash` and server fields. Declare a separate output model.
- **`@app.on_event("startup")`**: deprecated. Use `lifespan`.
- **Sharing one `AsyncSession` across requests or tasks**: sessions are not concurrency safe. Open one per request; open a new one in background tasks.
- **Passing ORM objects to `BackgroundTasks`** after the session closed: detached or expired instances. Pass IDs and reload.
- **Expecting a yield dependency to clean up before the response**: the default `scope="request"` exits after the response and background tasks. Use `scope="function"` when the commit result must reach the client.
- **Catching an exception in a yield dependency and not re-raising**: the client gets a 500 with no log. Re-raise or raise `HTTPException` from the handler.
- **`jwt.decode(token, key)` without `algorithms=`**: PyJWT requires it; never allow `none` or accept an algorithm from the token header.
- **`allow_origins=["*"]` with `allow_credentials=True`**: invalid for browsers and unsafe; list origins.
- **Lazy loading with `AsyncSession`**: raises `MissingGreenlet`. Use `selectinload`, `joinedload` or `await session.refresh(obj, ["rel"])`; set `expire_on_commit=False`.
- **Creating the engine at import time inside a library module for tests**: leaks connections and ties to the wrong event loop. Create it in lifespan and override the session dependency in tests.
- **`TestClient(app)` without `with`**: lifespan does not run, so `request.state` is empty. Use the context manager.
- **Using `httpx.AsyncClient(app=app)`**: the shortcut was removed from httpx; pass `transport=httpx.ASGITransport(app=app)`.
- **Setting `Content-Type: text/plain` on JSON requests**: fails with 422 since 0.132.0 unless `strict_content_type=False` is set deliberately.
- **PATCH that uses `model_dump()` without `exclude_unset=True`**: overwrites fields with defaults.
- **Running `fastapi dev` or `--reload` in production images**: reload watches files and binds to localhost. Use `fastapi run`.
- **Multiplying pool size by workers unchecked**: 4 workers with `pool_size=20` need 80 connections. Size against the database limit.
- **Pulling in `pydantic.v1` models**: unsupported path; port to v2 models.

## 16. References

- [references/dependencies-and-lifespan.md](references/dependencies-and-lifespan.md): Depends with Annotated, caching and scope, yield dependency timing, lifespan and state, settings, background tasks, exception handlers, middleware and CORS.
- [references/database-sqlalchemy.md](references/database-sqlalchemy.md): async engine and session setup, session dependency, queries and eager loading, transactions, pools, SQLModel notes, Alembic migrations.
- [references/security-auth.md](references/security-auth.md): OAuth2 password flow, Argon2 hashing with pwdlib, JWT with PyJWT, scopes, API keys, CORS and hardening, login timing.
- [references/testing-and-deployment.md](references/testing-and-deployment.md): pytest layout, TestClient and AsyncClient, dependency overrides, test databases, lifespan in tests, WebSocket and SSE tests; fastapi CLI, uvicorn and gunicorn workers, containers, proxy headers, health checks, graceful shutdown, logging, OpenAPI customisation.
- FastAPI documentation and release notes: https://fastapi.tiangolo.com/ and https://fastapi.tiangolo.com/release-notes/
- Pydantic: https://docs.pydantic.dev/ ; pydantic-settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Starlette: https://www.starlette.io/ ; Uvicorn: https://www.uvicorn.org/
- SQLAlchemy asyncio: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html ; Alembic: https://alembic.sqlalchemy.org/
- PyJWT: https://pyjwt.readthedocs.io/ ; pwdlib: https://frankie567.github.io/pwdlib/
