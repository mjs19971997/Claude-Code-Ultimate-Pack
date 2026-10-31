# Databases with SQLAlchemy 2.x, SQLModel and Alembic

Async SQLAlchemy sessions in FastAPI, queries, eager loading, transactions, connection pools, SQLModel notes and Alembic migrations. Verified with SQLAlchemy 2.1.6 (2.0.55 is the latest 2.0.x), aiosqlite 0.22.1, Alembic 1.20.1 and SQLModel 0.0.48 on Python 3.13 (2026-10).

## Contents

1. [Install and engine](#1-install-and-engine)
2. [Models](#2-models)
3. [Session dependency](#3-session-dependency)
4. [Queries](#4-queries)
5. [Transactions](#5-transactions)
6. [Pools and workers](#6-pools-and-workers)
7. [Sync SQLAlchemy in def endpoints](#7-sync-sqlalchemy-in-def-endpoints)
8. [SQLModel](#8-sqlmodel)
9. [Alembic](#9-alembic)

## 1. Install and engine

```bash
pip install "sqlalchemy[asyncio]" aiosqlite   # SQLite for local work
pip install "sqlalchemy[asyncio]" asyncpg     # PostgreSQL (or psycopg[binary] with postgresql+psycopg://)
```

- With SQLAlchemy 2.1.6, importing `sqlalchemy.ext.asyncio` raised `ImportError` until `greenlet` was installed; the `asyncio` extra installs it.
- Async URLs name an async driver: `sqlite+aiosqlite:///./app.db`, `postgresql+asyncpg://user:pass@host/db`, `postgresql+psycopg://...` (psycopg 3 supports async).
- Create the engine once per process in `lifespan`, store it in `app.state`, and `await engine.dispose()` after the `yield`.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()
```

- `expire_on_commit=False` keeps attributes readable after `commit()`; with the default, accessing them in an async context triggers a lazy refresh and raises `MissingGreenlet`.

## 2. Models

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    author: Mapped["Author"] = relationship(back_populates="books")
```

- Use typed `Mapped[...]` and `mapped_column`. Keep ORM models separate from Pydantic schemas; convert with `model_config = ConfigDict(from_attributes=True)` on the schema.
- Index every foreign key and every column used in `where` or `order_by` of hot queries.
- `Base.metadata.create_all` is for tests and prototypes. Real schemas change through Alembic.

## 3. Session dependency

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

- One session per request; never share a session across tasks (`asyncio.gather` on one session is unsafe) or store it globally.
- The session is closed when the dependency exits, after the response by default; see the `scope` discussion in [dependencies-and-lifespan.md](dependencies-and-lifespan.md). If a commit failure must change the response, call `await session.commit()` in the endpoint (before returning), not in the exit code.
- Background tasks open their own `async with sessionmaker()` block.

## 4. Queries

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def books_by_author(session: AsyncSession, author_id: int, limit: int, offset: int):
    stmt = (
        select(Book)
        .where(Book.author_id == author_id)  # bound parameter, not string formatting
        .options(selectinload(Book.author))
        .order_by(Book.id)
        .limit(limit)
        .offset(offset)
    )
    return (await session.scalars(stmt)).all()


async def get_or_404(session: AsyncSession, book_id: int) -> Book:
    book = await session.get(Book, book_id)
    if book is None:
        raise LookupError(book_id)
    return book
```

- Use `select()` with `session.scalars()` / `session.execute()`; the legacy `session.query()` is not available on `AsyncSession`.
- Lazy loading is not allowed in async code. Load relationships eagerly with `selectinload` (collections) or `joinedload` (many-to-one), or `await session.refresh(obj, ["rel"])`.
- Raw SQL: `await session.execute(text("SELECT * FROM books WHERE id = :id"), {"id": book_id})`. Never build SQL with f-strings.
- For large result sets, `await session.stream_scalars(stmt)` yields rows incrementally; combine with a streaming response.
- Keyset pagination (`where(Book.id > last_id).order_by(Book.id).limit(n)`) scales better than large `offset` values.
- Bulk work: `session.add_all([...])`, or `insert(Book).values([...])` for many rows; flush in chunks.
- `unique` violations raise `sqlalchemy.exc.IntegrityError`; catch it, `await session.rollback()` and raise a 409 domain error.

## 5. Transactions

```python
from sqlalchemy.exc import IntegrityError


async def create_author(session: AsyncSession, name: str) -> Author:
    author = Author(name=name)
    session.add(author)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return author
```

- A session starts a transaction on first use; `commit()` ends it and `rollback()` discards it. `async with session.begin():` commits on success and rolls back on exception, and fits service functions.
- Keep one commit per request in one layer (service or endpoint). Several commits in one request give partial writes on failure.
- A session that raised during flush is in a failed state until `rollback()` is called.
- For read-modify-write races use `select(...).with_for_update()` (PostgreSQL and MySQL) or a unique constraint plus retry.
- Isolation level is set on the engine (`isolation_level="REPEATABLE READ"`) or per connection; check the database documentation for semantics.

## 6. Pools and workers

- Each worker process has its own engine and pool. Total connections = workers x replicas x (`pool_size` + `max_overflow`). Keep that below the database `max_connections`, leaving headroom for migrations and admin tools.
- Typical start: `create_async_engine(url, pool_size=10, max_overflow=10, pool_timeout=30, pool_recycle=1800, pool_pre_ping=True)`. Tune with measurements; for serverless or many replicas put a pooler (PgBouncer) in front and, with transaction-mode pooling, check driver-specific settings for prepared statements.
- `pool_pre_ping=True` tests a connection on checkout and replaces stale ones after a database restart.
- In tests, SQLite in memory needs `poolclass=StaticPool` and `connect_args={"check_same_thread": False}` so all sessions see the same database.
- Dispose the engine on shutdown so connections close cleanly.

## 7. Sync SQLAlchemy in def endpoints

- A sync engine with `def` endpoints is a valid, simpler choice: FastAPI runs each endpoint in the threadpool (40 threads by default), so the pool size should be similar to the number of threads you expect to be active.
- Do not call a sync `Session` from `async def` code; it blocks the event loop.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:  # SessionLocal = sessionmaker(engine)
        yield db


DbDep = Annotated[Session, Depends(get_db)]
```

## 8. SQLModel

- SQLModel (0.0.48 at the time of checking, pre-1.0) combines Pydantic and SQLAlchemy models: `class Hero(SQLModel, table=True)`. It targets sync use mainly; for async use `sqlmodel.ext.asyncio.session.AsyncSession` with an SQLAlchemy async engine. Check its docs for current async details.
- The documented pattern uses separate models: `HeroBase` (shared fields), `Hero(HeroBase, table=True)`, `HeroCreate`, `HeroPublic`, `HeroUpdate`. Use `response_model=HeroPublic` so internal columns never leak.
- For updates: `hero_db.sqlmodel_update(body.model_dump(exclude_unset=True))`.
- Because of the pre-1.0 version, pin it and read its release notes before upgrading; plain SQLAlchemy is the lower-risk choice for large services.

## 9. Alembic

```bash
pip install alembic
alembic init -t async migrations      # async template (check `alembic init --help` for templates)
alembic revision --autogenerate -m "create books"
alembic upgrade head
alembic downgrade -1
```

- Set `sqlalchemy.url` from your settings in `migrations/env.py` (not a literal URL in `alembic.ini`), and set `target_metadata = Base.metadata` so autogenerate sees models.
- Always review generated revisions: autogenerate misses renames (shows drop plus add), some constraints and server defaults.
- Run `alembic upgrade head` as a separate deploy step (init container or release job) before new workers start; make migrations backward compatible with the previous app version (add column, deploy, then drop in a later release).
- Do not call `create_all` in production start-up; it hides drift from the migration history.
- In CI, run `alembic upgrade head` on an empty database and `alembic check` to detect models that have no migration.
