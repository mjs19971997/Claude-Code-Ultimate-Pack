# Dependencies, Lifespan and Settings

Dependency injection, yield dependency timing, lifespan and app state, pydantic-settings, background tasks, exception handlers, middleware and CORS in FastAPI 0.162.0 with Pydantic 2.14 and Starlette 1.10. The code blocks were run on Python 3.13 (2026-10).

## Contents

1. [Depends with Annotated](#1-depends-with-annotated)
2. [Caching and sub-dependencies](#2-caching-and-sub-dependencies)
3. [Yield dependencies and exit timing](#3-yield-dependencies-and-exit-timing)
4. [Lifespan and app state](#4-lifespan-and-app-state)
5. [Settings with pydantic-settings](#5-settings-with-pydantic-settings)
6. [Background tasks](#6-background-tasks)
7. [Exception handlers](#7-exception-handlers)
8. [Middleware and CORS](#8-middleware-and-cors)
9. [Async or sync endpoints](#9-async-or-sync-endpoints)

## 1. Depends with Annotated

```python
from typing import Annotated

from fastapi import Depends, FastAPI, Query


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PageDep = Annotated[Pagination, Depends()]  # class as dependency: Depends() infers it

app = FastAPI()


@app.get("/things")
def things(page: PageDep) -> dict[str, int]:
    return {"limit": page.limit, "offset": page.offset}
```

- A dependency is any callable: function, class, or an object with `__call__`. Its parameters follow the same rules as endpoint parameters (path, query, header, body, other dependencies).
- `Annotated[T, Depends(fn)]` keeps the default slot free and lets the alias be reused; do not mix it with `= Depends(fn)` in one codebase.
- `APIRouter(dependencies=[Depends(check)])` and `FastAPI(dependencies=[...])` run for every route; return values are discarded.
- Decorator level: `@router.get("/x", dependencies=[Depends(check)])` runs a check without a handler parameter.
- A group of query parameters can also be a Pydantic model: `Annotated[Page, Query()]` with `model_config = ConfigDict(extra="forbid")`. The same works for headers, cookies and forms. Check the release notes for the combination and optional-model features added in 0.157 to 0.161.

## 2. Caching and sub-dependencies

- Within one request, a dependency declared several times (directly or via other dependencies) is called once and its result reused (`use_cache=True`, the default). Use `Depends(fn, use_cache=False)` when each use needs a fresh value.
- Keep the dependency graph shallow: settings, session, current user, then permission checks.
- Override in tests with `app.dependency_overrides[original] = replacement`; the key is the original callable object, so import it from one place. See [testing-and-deployment.md](testing-and-deployment.md).

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.security import get_current_user


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


AdminDep = Annotated[dict, Depends(require_admin)]
```

## 3. Yield dependencies and exit timing

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session  # closed by the context manager when the dependency exits


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

Verified behaviour on 0.162.0 with one `scope="request"` (default) and one `scope="function"` dependency plus a background task, in execution order:

```text
req:enter, fn:enter, endpoint, fn:exit, bg:done, req:exit
```

- Code before `yield` runs before the endpoint. Code after `yield` is the exit code.
- `scope="function"`: exit right after the endpoint function returns, before the response is sent. Use when a commit or flush failure must become an error response, or when the resource must not be held while the response streams to a slow client.
- `scope="request"` (default for yield dependencies): exit after the response is sent, and after background tasks (observed above). Use when a `StreamingResponse` or generator reads from the resource.
- A `scope="request"` dependency needs its sub-dependencies to be `scope="request"` too; a `scope="function"` dependency can use either.
- History worth knowing when reading older answers: before 0.106.0 exit code ran after the response; 0.106.0 moved it before the response; 0.118.0 reverted to after the response; 0.121.0 added `scope`. Since 0.110.0 an exception caught with `except` inside a yield dependency is not automatically re-raised to handlers.
- Wrap the `yield` in `try/finally` so cleanup runs on errors. If you catch the exception, re-raise it (or raise `HTTPException`), otherwise the client gets a 500 and the server logs nothing.
- Background tasks that need a database must open their own session; they must not reuse the one yielded to the request, and should receive IDs instead of ORM instances.

## 4. Lifespan and app state

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI, Request


class State(TypedDict):
    http: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    # startup
    async with httpx.AsyncClient(timeout=5.0) as client:
        yield {"http": client}
    # shutdown: the async with block closes the client


app = FastAPI(lifespan=lifespan)


@app.get("/ping")
async def ping(request: Request) -> dict[str, str]:
    client: httpx.AsyncClient = request.state.http
    return {"client": type(client).__name__}
```

- `@app.on_event("startup")` and `"shutdown"` are deprecated and emit a `DeprecationWarning`; use the `lifespan` argument and do not mix the two styles.
- Yielded state is copied per request onto `request.state`. Objects stored in `app.state` (for example the engine in the tested example) are reachable through `request.app.state`.
- Lifespan runs once per worker process; do not run migrations there.
- Lifespan runs when the server starts (`fastapi run`, uvicorn) and in tests only under `with TestClient(app)`. `httpx.ASGITransport` does not run it.

## 5. Settings with pydantic-settings

```python
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = "sqlite+aiosqlite:///./app.db"
    jwt_secret: SecretStr  # required: APP_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()  # reads APP_* variables, then .env
```

- Install: `pydantic-settings` (included in `fastapi[standard]`). Priority: init arguments, environment variables, dotenv file, secrets directory, defaults.
- A missing required field fails at first `get_settings()` call with a clear validation error; call it in lifespan to fail fast at startup.
- Use `SecretStr` for keys and passwords so they do not appear in `repr` or logs; read with `.get_secret_value()`.
- Inject with `Annotated[Settings, Depends(get_settings)]`; override in tests with `app.dependency_overrides[get_settings] = lambda: Settings(jwt_secret="x" * 32, ...)` (or set environment variables before the first call, as the tested conftest does).
- Keep `.env` out of version control and out of images.

## 6. Background tasks

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()


def write_audit(user_id: int, action: str) -> None:
    ...  # open its own session or connection here


@app.post("/actions", status_code=202)
async def action(tasks: BackgroundTasks) -> dict[str, str]:
    tasks.add_task(write_audit, 42, "export")
    return {"status": "accepted"}
```

- Tasks run after the response is sent, in the same process (`def` in the threadpool, `async def` on the loop), and finished before a `scope="request"` dependency exited in the tested run.
- Use them for short work (audit row, email enqueue). A crash or restart loses them and there is no retry; use a queue and a separate worker for anything that must complete.
- Pass plain values, not the request, the session or ORM instances.

## 7. Exception handlers

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()


class DomainError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


@app.exception_handler(DomainError)
async def domain_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": exc.code})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # exc.errors() can contain submitted input; do not echo secrets back
    return JSONResponse(status_code=422, content={"detail": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]})
```

- Validation failures raise `RequestValidationError` (422); response validation failures become 500 and indicate a server bug.
- Unhandled exceptions become a 500 and are logged. Services raise domain exceptions; handlers translate them to HTTP.

## 8. Middleware and CORS

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)
```

- Verified: a preflight `OPTIONS` with `Origin: https://app.example.com` returned the matching `access-control-allow-origin` header.
- Middleware order: the last one added is the outermost. Add CORS so that it wraps authentication failures and error responses, otherwise browsers see a CORS error instead of the 401.
- `@app.middleware("http")` (a function taking `request, call_next`) is simple; for streaming responses or heavy use prefer a pure ASGI middleware class.
- Other built-ins: `GZipMiddleware`, `TrustedHostMiddleware`, `HTTPSRedirectMiddleware`.

## 9. Async or sync endpoints

- `async def` endpoint: runs on the event loop; await only async-capable libraries.
- `def` endpoint: runs in AnyIO's threadpool (40 threads by default), so blocking code is safe but each concurrent request holds a thread.
- To call blocking code from `async def`, use `await anyio.to_thread.run_sync(fn, arg)` or `await asyncio.to_thread(fn, arg)`.
- CPU-bound work does not speed up with threads on a GIL build; use a process pool or another service.
