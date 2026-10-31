---
name: python-expert
description: >-
  Writes, reviews and ships modern Python 3.13 and 3.14 projects: typing with mypy and pyright, pyproject.toml packaging (PEP 621, dependency groups, build backends), uv, ruff, pytest, asyncio with TaskGroup and timeouts, dataclasses and profiling. Use when editing .py files, pyproject.toml, uv.lock, ruff or mypy config or conftest.py, running uv, ruff, pytest, mypy, pyright or cProfile, or fixing type errors, event-loop errors and slow Python code. Not for NumPy, SciPy or scientific plots (use scientific-python-expert), web APIs with FastAPI or Django (use fastapi-expert or django-expert), container images (use docker-expert), cross-language test strategy (use unit-testing-expert), or LLM SDK calls (use anthropic-sdk-expert or openai-sdk-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Python Expert

This skill covers everyday and production Python on the 3.13 and 3.14 lines: language features worth using, static typing, project metadata and packaging, the uv workflow, ruff, pytest, asyncio, dataclasses and basic performance work. It favours the standard library and the tools configured in `pyproject.toml`. Numerical computing, container builds, language-agnostic test design and LLM SDK usage belong to other skills.

> Verified against CPython 3.13 and 3.14 (3.14.6 run locally, including the free-threaded build), uv 0.13.6, ruff 0.17.3, pytest 9.2.0, pytest-asyncio 1.4.1, mypy 2.4.1 and pyright 1.1.x (2026-10).

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

- Covered: Python syntax and standard library on 3.13 and 3.14, type hints and type checkers (mypy, pyright), `pyproject.toml` metadata, build backends, uv (projects, lock, run, tool, python install, build, publish), ruff (lint and format), pytest, asyncio, dataclasses, `cProfile` and `timeit`, and common security pitfalls in Python code.
- Not covered: array and scientific computing, numba, plotting (scientific-python-expert); Dockerfiles and image builds for Python apps (docker-expert); language-agnostic unit-testing strategy, mocking philosophy and coverage targets (unit-testing-expert); calling LLM APIs (anthropic-sdk-expert, openai-sdk-expert); retrieval pipelines (rag-expert); web API design (rest-api-expert); CI pipeline structure (cicd-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Free-threading | 3.13 introduced the optional free-threaded build as experimental; in 3.14 it is officially supported (PEP 779) but still optional and not the default. `sys._is_gil_enabled()` reports the state; `PYTHON_GIL=1` re-enables the GIL on a free-threaded build. Install with `uv python install 3.14t`. Check that every C extension in use ships free-threaded wheels |
| Deferred annotations | 3.14 evaluates annotations lazily (PEP 649, PEP 749): forward references need no quotes and no `from __future__ import annotations`. Inspect with `annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF)` (also `VALUE`, `STRING`) |
| Template strings | 3.14 adds `t"..."` literals (PEP 750). The result is a `string.templatelib.Template`, not a `str`: it keeps `.strings` and `.interpolations` (each with `value`, `expression`, `conversion`, `format_spec`) so a function can escape or parameterise before building output |
| Other 3.14 changes | `except ValueError, TypeError:` without parentheses when there is no `as`; `return`, `break` or `continue` that leaves a `finally` block emits a `SyntaxWarning`; `compression.zstd` (Zstandard); `concurrent.interpreters` (subinterpreters, PEP 734); `multiprocessing` default start method on Linux is `forkserver`; `tarfile` extraction defaults to the `data` filter |
| 3.13 changes | `copy.replace()`, `warnings.deprecated`, `asyncio.Queue.shutdown()`, TypeVar defaults (`class Box[T = int]`), `typing.ReadOnly`, `typing.TypeIs` |
| asyncio | `asyncio.TaskGroup` and `asyncio.timeout()` (3.11+) replace most `gather` and `wait_for` uses; failures arrive as `ExceptionGroup`, handled with `except*`. 3.14: `asyncio.get_event_loop()` raises `RuntimeError` when no loop is set; the policy API is deprecated (removal planned for 3.16); `python -m asyncio ps PID` and `pstree PID` list running tasks of a live process |
| Typing syntax | 3.12+: `def f[T](x: T)`, `class Stack[T]`, `type Alias = ...` (PEP 695). `@override`, `Self`, `TypedDict` with `Required`, `NotRequired`, `ReadOnly`; `Protocol` for structural types |
| uv 0.13.x | `uv init`, `add`, `remove`, `lock`, `sync`, `run`, `tree`, `export`, `build`, `publish`, `tool`, `python`, `pip`, `format` (runs ruff). Default build backend for new projects is `uv_build`. `uv check` is marked experimental and `uv audit` queries an external vulnerability database; check the docs before relying on either |
| pyproject.toml | `[project]` (PEP 621): `name`, `version`, `requires-python`, `dependencies`, `optional-dependencies`, `scripts`. `license = "MIT"` is an SPDX expression. `[dependency-groups]` (PEP 735) holds dev-only sets that are not published; `[build-system]` names the backend |
| ruff 0.17 | The default rule set is much larger than the older `E4, E7, E9, F`: a fresh run flags unsorted imports (I), mutable defaults (B006), bare `except` (E722), `try/except/pass` (S110) and more. Run `ruff check --show-settings` to see the active rules. `extend-select` adds to the defaults; `select` replaces them |
| pytest 9 | Native `[tool.pytest]` table in `pyproject.toml` (the `[tool.pytest.ini_options]` table still works); `strict = true`; built-in `subtests` fixture; `pytest.RaisesGroup` for exception groups. Plugins are needed for async tests (pytest-asyncio) and coverage (pytest-cov) |
| Type checkers | mypy 2.x: `--strict`, `--python-version`, per-module `[[tool.mypy.overrides]]`. pyright: `typeCheckingMode = "strict"` under `[tool.pyright]`. ty (marked Beta on PyPI) and pyrefly are newer checkers; verify their maturity and rule coverage before adopting |

## 3. Workflow

1. Read `pyproject.toml`, `.python-version`, the lockfile and CI config first. Identify the supported Python range (`requires-python`), the package manager (uv, pip, poetry, pdm) and the configured linters before suggesting anything.
2. Reproduce the problem with the project's own command (`uv run pytest -x`, `uv run mypy src`, `uv run python -m pkg`). For slowness, profile before editing.
3. Keep to the repository's tools. Do not introduce a second formatter, a second type checker or a different package manager.
4. Make the smallest change. Add type hints to what you touch, and a test that fails without the change.
5. Run, in order: `uv run ruff format`, `uv run ruff check`, the type checker, `uv run pytest`. Report which commands ran and their result.
6. When dependencies change, commit `pyproject.toml` and `uv.lock` together, and check `uv lock --check` passes.
7. Note any behaviour that differs between 3.13 and 3.14 when the project supports both.

## 4. Decision Rules

- If the project already uses poetry, pdm, hatch or pip-tools, keep it; for a new project or a migration the user asked for, use uv because it covers interpreters, lockfile, environments and publishing in one tool.
- If a library is published, set a wide `requires-python` lower bound and loose dependency ranges; if it is an application, pin through `uv.lock` and deploy with `uv sync --locked`.
- If the code is I/O bound with many concurrent waits, use asyncio; if it is blocking I/O in few places, use threads (`asyncio.to_thread` or `ThreadPoolExecutor`); if it is CPU bound pure Python, use `ProcessPoolExecutor`, or a free-threaded build only after every dependency supports it.
- If you need structured data with validation at a trust boundary (JSON, config, API input), use a validation library such as pydantic; for internal value objects use `dataclass`.
- If a type checker is not yet configured, add mypy or pyright in non-strict mode and tighten per module; do not enable both unless CI already does.
- If a type cannot be expressed, use `Protocol`, `TypeVar` or `object` before `Any`; if `# type: ignore` is unavoidable, use a specific code (`# type: ignore[arg-type]`) and a reason.
- If you need a mutable default, use `field(default_factory=...)` in dataclasses and `None` plus assignment in functions.
- If both `asyncio.gather` and `TaskGroup` fit, use `TaskGroup` because a failure cancels siblings and no task is left running unobserved.
- If code must be portable to 3.13 and 3.14, avoid 3.14-only syntax (t-strings, parenthesis-free `except`) until `requires-python` is `>=3.14`.

## 5. Coding Standards

- Format with `ruff format` (Black-compatible, 88 columns by default). Lint with `ruff check`; do not hand-format against the tool.
- Annotate every public function, method and module-level constant. Use built-in generics (`list[int]`, `dict[str, int]`, `X | None`), `collections.abc` for abstract types (`Sequence`, `Mapping`, `Iterable`), and never `typing.List` or `Optional`.
- Use PEP 695 syntax (`def f[T]`, `type Alias = ...`) when `requires-python >= 3.12`.
- Import order: standard library, third party, first party (ruff rule `I`). Absolute imports inside a package; no wildcard imports.
- Name modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`. Keep a leading underscore for non-public names.
- Raise specific exceptions, chain with `raise NewError(...) from err`, and never use a bare `except:`. Catch `Exception` only at a boundary that logs or converts it.
- Use `pathlib.Path` for paths, `with` for files, and always pass `encoding="utf-8"` to `open()` and `Path.read_text()`.
- Use f-strings for messages, `%`-style lazy arguments for `logging` calls (`log.info("user %s", user_id)`).
- Prefer `enumerate`, `zip(strict=True)`, `dict.get`, comprehensions and `itertools` over index loops; do not write comprehensions with side effects.
- Write docstrings for public APIs; the first line is a one-sentence summary. Do not repeat the type hints in prose.
- Do not use mutable default arguments, `assert` for input validation (stripped under `-O`), or `eval` and `exec` on external data.

## 6. Project Structure

```text
acme-tools/
├── pyproject.toml          # metadata, dependency groups, ruff, mypy, pytest config
├── uv.lock                 # committed for applications and for reproducible CI
├── .python-version         # interpreter pin read by uv
├── README.md
├── src/
│   └── acme_tools/         # importable package (underscores)
│       ├── __init__.py
│       ├── py.typed        # marker for typed libraries
│       ├── models.py
│       └── cli.py
└── tests/
    ├── conftest.py         # shared fixtures
    └── test_models.py
```

- Use the `src/` layout so tests import the installed package, not the working directory.
- The project name uses hyphens or underscores on PyPI; the import name is the normalized underscore form.
- Keep one `pyproject.toml` per distributable package. For several packages use a uv workspace (`[tool.uv.workspace]`) rather than relative path hacks; see [references/packaging-uv.md](references/packaging-uv.md).

## 7. Design Patterns

- **Frozen dataclass value objects**: `@dataclass(frozen=True, slots=True, kw_only=True)` for immutable records; update with `dataclasses.replace` or `copy.replace`. Cost: not suited to objects that need identity-based mutation.
- **Protocol for dependencies**: define a small `Protocol` where a function needs behaviour (`close()`, `read()`), so tests pass a fake without inheritance. Cost: structural checks happen only in the type checker unless `@runtime_checkable`.
- **Context managers for resources**: `contextlib.contextmanager`, `asynccontextmanager` and `ExitStack` pair acquire and release; prefer them to try/finally scattered across callers.
- **Dependency injection by parameter**: pass clients, clocks and settings into functions or constructors instead of importing globals; this makes `monkeypatch` rarely necessary.
- **Structured concurrency**: one `TaskGroup` per unit of work, a `Semaphore` to bound fan-out, `asyncio.timeout()` around the whole block. Details: [references/async.md](references/async.md).
- **Generators for streams**: yield items instead of building lists when the consumer reads once; cost is single-pass iteration.
- **`functools.cache` or `lru_cache(maxsize=N)`** for pure functions with hashable arguments; an unbounded cache on a long-lived process is a memory leak.
- **Entry-point functions**: expose `main()` and register it under `[project.scripts]`; keep `if __name__ == "__main__":` as a thin wrapper.

## 8. Best Practices

- Keep functions small and side effects at the edges; pure functions are easy to test and type.
- Pin the interpreter with `.python-version` and test in CI on every version in `requires-python`.
- Treat warnings as errors in tests (`filterwarnings = ["error"]`) so deprecations surface early, and allow-list the known noisy ones individually.
- Use `logging` with module-level `log = logging.getLogger(__name__)`; configure handlers once, in the entry point.
- Read configuration from environment variables or files at startup into one typed settings object; do not scatter `os.environ` lookups.
- Use `enum.StrEnum` or `Literal[...]` for closed sets of values instead of bare strings.
- Use `with open(...)`/`Path` and `tempfile` rather than fixed paths in `/tmp`.
- Prefer `datetime.now(UTC)` (timezone-aware) to naive datetimes; store UTC and convert at the edges.
- Remove dead code and unused dependencies; `uv remove` and re-lock keep `uv.lock` honest.

## 9. Performance

- Measure first: `python -m cProfile -o out.prof -m pkg` then `pstats` (sort by `cumulative` or `tottime`), `python -m timeit` for micro-benchmarks, `tracemalloc` for memory. Optimise the top entry only, then measure again.
- Remove quadratic patterns before anything else: membership tests against a `list` in a loop (use a `set` or `dict`), repeated `str +=` in a loop (use `"".join`), `list.insert(0, x)` or `pop(0)` (use `collections.deque`), nested loops that could be a dict lookup, and re-sorting inside a loop.
- Hoist invariant work out of loops; use generators or `itertools` for large streams; use `__slots__` (or `@dataclass(slots=True)`) for millions of small objects.
- In asyncio, do not call blocking code in a coroutine; move it with `asyncio.to_thread()`. Bound concurrency with a `Semaphore` so thousands of tasks do not overwhelm a service.
- CPU-bound work: processes (`ProcessPoolExecutor`) or a native extension; threads help only for I/O unless on a free-threaded build.
- Benchmark your own workload on the default and the free-threaded build before switching; do not assume either is faster.
- Import cost matters for CLIs: check with `python -X importtime -m pkg`, and import heavy modules inside the function that needs them.

## 10. Security

- Never build SQL, shell commands or file paths by concatenating untrusted input. Use parameter placeholders (`cursor.execute("... WHERE name = ?", (name,))`), `subprocess.run([...], check=True, timeout=...)` with a list and without `shell=True`, and resolve paths against a base directory (see the example in section 14).
- Do not unpickle, `yaml.load` or `eval` untrusted data. Use `json`, or `yaml.safe_load`. `pickle` is for data you wrote yourself.
- Extract archives with an explicit filter: `tar.extractall(dest, filter="data")`. On 3.13 the default still extracts `../` paths (with a `DeprecationWarning`); 3.14 rejects them by default. Validate `zipfile` member names yourself.
- Generate tokens with `secrets` (`secrets.token_urlsafe(32)`), never `random`. Compare secrets with `hmac.compare_digest`. Hash passwords with a dedicated KDF library (argon2 or bcrypt), not `hashlib.sha256`.
- Keep TLS verification on: use `ssl.create_default_context()` and library defaults; never pass `verify=False`.
- Keep secrets out of source and out of `pyproject.toml`; read them from the environment or a secret manager. Use `UV_PUBLISH_TOKEN` or trusted publishing, not a token in a file.
- Pin and audit dependencies: commit `uv.lock`, install with `uv sync --locked`, and run a vulnerability audit (for example `uv audit`, or pip-audit) in CI. `uv lock --exclude-newer <date>` limits resolution to packages uploaded before a date.
- Do not log secrets or full request bodies; set `repr=False` on dataclass fields that hold credentials (`field(repr=False)`).
- Run `ruff check` with the `S` (bandit) rules enabled; the 0.17 defaults already include some of them.

## 11. Testing

- Use pytest with `tests/` mirroring the package. Name files `test_*.py`, functions `test_*`; keep tests independent and order-free.
- Fixtures provide setup (`@pytest.fixture`, `yield` for teardown); put shared ones in `conftest.py`. Use the narrowest scope that is fast enough.
- `@pytest.mark.parametrize(("a", "b"), [...], ids=[...])` for table-driven cases; `pytest.raises(Type, match="...")` for failure paths; `pytest.RaisesGroup` for exception groups.
- Built-ins: `tmp_path` for files, `monkeypatch` for env vars, attributes and `chdir` (undone automatically), `capsys` and `caplog` for output and logs.
- Async tests: pytest-asyncio with `asyncio_mode = "strict"`, `@pytest.mark.asyncio`, and `asyncio_default_fixture_loop_scope` set explicitly (the plugin warns when it is unset).
- Run: `uv run pytest -x --lf` while iterating, `uv run pytest --cov=acme_tools --cov-report=term-missing` in CI. Add `--strict-markers` and `--strict-config` (or `strict = true`) so typos fail.
- Test error paths and boundaries, not only the happy path; avoid asserting on log text or private attributes.
- Run the type checker and ruff in the same CI job so a test-only change cannot drift. More recipes: [references/testing-tooling.md](references/testing-tooling.md).

## 12. Review Checklist

- [ ] `requires-python`, `.python-version` and the CI matrix agree, and no syntax newer than the lowest supported version is used.
- [ ] Public functions are annotated; no new bare `Any`, bare `# type: ignore` or `typing.List`/`Optional`.
- [ ] `ruff format --check`, `ruff check`, the type checker and `pytest` pass.
- [ ] `pyproject.toml` and `uv.lock` changed together; `uv lock --check` passes.
- [ ] No mutable default arguments, bare `except`, `assert` used for validation, or `shell=True`.
- [ ] External input is validated; SQL is parameterised; paths are confined; archives use `filter="data"`.
- [ ] No secrets, tokens or personal data in code, tests, config or logs.
- [ ] Async code has no blocking calls, no orphan tasks (use `TaskGroup`) and every wait has a timeout or cancellation path.
- [ ] New behaviour has a test, including the failure path.
- [ ] Performance claims are backed by a measurement.

## 13. Production Notes

- Deploy applications from the lockfile: `uv sync --locked --no-dev` (fails if `uv.lock` is stale). Use `--frozen` only when you deliberately skip the freshness check.
- Libraries: build with `uv build`, inspect the sdist and wheel contents, publish with `uv publish` using trusted publishing from CI where the index supports it, and bump the version in `pyproject.toml`.
- Configure logging as structured output to stdout; handle `SIGTERM` by cancelling the main task so `async with` blocks release resources.
- Set explicit timeouts on every network call (`httpx.Client(timeout=...)`, `asyncio.timeout`); several standard-library defaults (for example `urllib.request.urlopen`) set no timeout.
- Check python.org for the current support status, end-of-life dates and newest release before choosing a `requires-python` floor.
- Plan upgrades: run tests with `-W error::DeprecationWarning` on the next version early. Known 3.14 breakers: code that calls `asyncio.get_event_loop()` without a running loop, `return` inside `finally`, and code that relied on `fork` as the `multiprocessing` default on Linux.
- Free-threaded interpreters: pin the build explicitly (`3.14t`), test the whole dependency set, and keep a rollback to the default build.

## 14. Examples

A frozen dataclass with validation and a PEP 695 generic function (3.12+):

```python
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True, kw_only=True)
class Item:
    sku: str
    price_cents: int

    def __post_init__(self) -> None:
        if self.price_cents < 0:
            raise ValueError("price_cents must be >= 0")


def discounted(item: Item, percent: int) -> Item:
    return replace(item, price_cents=item.price_cents * (100 - percent) // 100)


def first[T](items: list[T]) -> T:
    return items[0]
```

Bounded concurrency with `TaskGroup`, a timeout and `except*` (runs on 3.13 and 3.14):

```python
import asyncio
from collections.abc import Awaitable, Callable, Iterable
from functools import partial


async def bounded_gather[T](
    factories: Iterable[Callable[[], Awaitable[T]]], limit: int = 5
) -> list[T]:
    sem = asyncio.Semaphore(limit)

    async def run(f: Callable[[], Awaitable[T]]) -> T:
        async with sem:
            return await f()

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(run(f)) for f in factories]
    return [t.result() for t in tasks]


async def main() -> None:
    async def fetch(i: int) -> str:
        await asyncio.sleep(0.01)
        return f"item-{i}"

    try:
        async with asyncio.timeout(2):
            jobs = [partial(fetch, i) for i in range(6)]
            print(await bounded_gather(jobs, limit=2))
    except* TimeoutError:
        print("timed out")


asyncio.run(main())
```

Confining a user-supplied path and parameterising SQL:

```python
import sqlite3
from pathlib import Path


def safe_join(base: Path, user_path: str) -> Path:
    base = base.resolve()
    target = (base / user_path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("path escapes base directory")
    return target


def find_user(con: sqlite3.Connection, name: str) -> list[tuple[int, str]]:
    return con.execute("SELECT id, name FROM users WHERE name = ?", (name,)).fetchall()
```

## 15. Common Mistakes

- **Mutable default argument** (`def f(x=[])`): the list is shared between calls. Use `None` and create it inside, or `field(default_factory=list)`.
- **Bare `except:` or `except Exception: pass`**: hides bugs and swallows `KeyboardInterrupt` (bare form). Catch the specific exception and log or re-raise.
- **Blocking call inside `async def`** (`time.sleep`, `requests.get`, large file reads): stalls every task. Use `await asyncio.sleep`, an async client, or `asyncio.to_thread`.
- **Creating tasks and dropping the reference** (`asyncio.create_task(f())` unobserved): the task can be garbage collected and its exception is lost. Use a `TaskGroup` or keep references.
- **`asyncio.get_event_loop()` outside a running loop**: raises `RuntimeError` on 3.14. Use `asyncio.run(main())` or `asyncio.Runner`.
- **`x in some_list` inside a loop**: quadratic. Convert to a `set` once.
- **`str +=` in a loop** building large text: use a list and `"".join`.
- **Running `pip install` into the system interpreter or an unmanaged venv**: drifts from the lockfile. Use `uv sync` and `uv run`.
- **Editing `uv.lock` by hand or committing `pyproject.toml` without it**: CI with `--locked` fails. Re-run `uv lock`.
- **Flat layout with tests importing from the working directory**: tests pass locally, package is broken once installed. Use `src/` and install the project.
- **Mixing `Optional[X]`, `List[X]` and `X | None`, `list[X]`** in one codebase: needless noise. Use the built-in forms.
- **`from __future__ import annotations` copied everywhere by habit**: unnecessary on 3.14, where annotations are already deferred, and it turns annotations into strings for libraries that read them at runtime. Drop it when the floor is 3.14, otherwise use it consistently; check the docs for its long-term status.
- **Using `tarfile.extractall` without a filter**: path traversal on 3.13. Pass `filter="data"`.
- **Asserting on floats with `==`**: use `pytest.approx`.
- **Catching `ExceptionGroup` members with plain `except`**: a `TaskGroup` raises a group; use `except*`.

## 16. References

- [references/packaging-uv.md](references/packaging-uv.md): pyproject.toml fields, build backends, uv project, lock, run, tool and python commands, workspaces, PEP 723 scripts, building and publishing.
- [references/typing.md](references/typing.md): mypy and pyright configuration, PEP 695 generics, Protocol, TypedDict, overloads, narrowing with TypeIs, deferred annotations on 3.14, migration tips.
- [references/async.md](references/async.md): TaskGroup, timeouts, cancellation, queues, exception groups, bridging blocking code, debugging tasks.
- [references/testing-tooling.md](references/testing-tooling.md): pytest configuration and fixtures, pytest-asyncio, parametrize, ruff configuration, CI command order.
- Python documentation: https://docs.python.org/3/ and What's New pages https://docs.python.org/3/whatsnew/3.14.html and https://docs.python.org/3/whatsnew/3.13.html
- PEPs: https://peps.python.org/ (649, 695, 735, 750, 779)
- Python Packaging User Guide: https://packaging.python.org/ and the `pyproject.toml` specification https://packaging.python.org/en/latest/specifications/pyproject-toml/
- uv: https://docs.astral.sh/uv/ ; ruff: https://docs.astral.sh/ruff/
- pytest: https://docs.pytest.org/ ; pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- mypy: https://mypy.readthedocs.io/ ; pyright: https://microsoft.github.io/pyright/
