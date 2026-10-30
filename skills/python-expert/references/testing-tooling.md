# pytest and ruff

Configuring and using pytest, pytest-asyncio and pytest-cov, and configuring ruff for lint and format. Verified against pytest 9.2.0, pytest-asyncio 1.4.1, pytest-cov 7.1.0 and ruff 0.17.3 on Python 3.13 and 3.14 (2026-10); the configuration and tests below were run together in a sample project.

## Contents

1. [pytest configuration](#1-pytest-configuration)
2. [Fixtures](#2-fixtures)
3. [Parametrize, markers and expected failures](#3-parametrize-markers-and-expected-failures)
4. [Built-in fixtures](#4-built-in-fixtures)
5. [Async tests](#5-async-tests)
6. [Coverage](#6-coverage)
7. [ruff configuration](#7-ruff-configuration)
8. [ruff commands and suppressions](#8-ruff-commands-and-suppressions)
9. [Command order for local work and CI](#9-command-order-for-local-work-and-ci)

## 1. pytest configuration

```toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
strict = true
addopts = ["-ra"]
filterwarnings = ["error"]
markers = ["slow: slow tests"]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

- pytest 9 reads a native `[tool.pytest]` table in `pyproject.toml`. The older `[tool.pytest.ini_options]` table (string-valued ini keys) keeps working and is what most existing projects use; pytest refuses to start when both are present in one file.
- `strict = true` turns unregistered markers and unknown config keys into errors (checked on 9.2.0); `--strict-markers` and `--strict-config` enable those two individually, and `pytest --help` lists what else `--strict` covers.
- `filterwarnings = ["error"]` makes any warning a failure; add narrow ignores such as `"ignore:message text:DeprecationWarning:some_module"` for noise you cannot fix.
- `testpaths` keeps collection fast; `pythonpath = ["src"]` is only needed when the package is not installed (with `uv run` it is installed).
- Useful flags: `-x` stop at first failure, `--lf` rerun last failures, `--ff` failures first, `--sw` stepwise, `--maxfail=N`, `-k "expr"` select by name, `-m "not slow"` select by marker, `--durations=10` slowest tests, `--setup-show` fixture lifecycle, `-p no:cacheprovider` disable the cache.
- Layout: `tests/` mirrors the package, with `conftest.py` files holding fixtures for the directory below them. With the `src/` layout and an installed project, tests import the package like any user.

## 2. Fixtures

```python
import sqlite3
from collections.abc import Callable, Iterator

import pytest

from acme_tools.models import Item


@pytest.fixture
def db() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    yield con  # teardown runs after the test, even when it failed
    con.close()


@pytest.fixture
def make_item() -> Callable[..., Item]:
    def _make(*, sku: str = "A-1", price_cents: int = 100) -> Item:
        return Item(sku=sku, price_cents=price_cents)

    return _make


def test_sql_param(db: sqlite3.Connection) -> None:
    db.execute("INSERT INTO users (name) VALUES (?)", ("o'brien",))
    row = db.execute("SELECT name FROM users WHERE name = ?", ("o'brien",)).fetchone()
    assert row == ("o'brien",)
```

- A fixture is requested by naming it as a test parameter. Scope: `function` (default), `class`, `module`, `package`, `session`. Wider scopes save setup time but share state; return immutable objects or reset them.
- `yield` fixtures run teardown after the yield. For several resources, use `contextlib.ExitStack` or separate fixtures.
- Factory fixtures (return a function) build objects with per-test overrides while keeping the default valid.
- `autouse=True` applies a fixture to every test in its scope; reserve it for environment isolation (clearing env vars, setting a timezone).
- Put shared fixtures in `conftest.py`; do not import fixtures from other test modules.
- Parametrize a fixture with `@pytest.fixture(params=[...])`; each test using it runs once per parameter.
- Fixtures can request other fixtures; `request.param` and `request.addfinalizer` cover the advanced cases.

## 3. Parametrize, markers and expected failures

```python
import pytest

from acme_tools.models import Item, discounted


@pytest.mark.parametrize(
    ("percent", "expected"),
    [(0, 1000), (10, 900), (100, 0)],
    ids=["none", "ten", "free"],
)
def test_discount(percent: int, expected: int) -> None:
    item = Item(sku="A-1", price_cents=1000)
    assert discounted(item, percent).price_cents == expected


def test_negative_price_rejected() -> None:
    with pytest.raises(ValueError, match="must be >= 0"):
        Item(sku="x", price_cents=-1)


def test_float_total() -> None:
    total = 0.1 + 0.2
    assert total == pytest.approx(0.3)
```

- Give parameter sets readable `ids`, or use `pytest.param(value, id="name", marks=...)` to attach a marker to one case.
- Stack several `parametrize` decorators to get the cross product.
- `pytest.raises(Type, match=regex)` checks the type and message; `excinfo.value` exposes the exception. Use `pytest.warns` for warnings and `pytest.RaisesGroup` for exception groups.
- Register custom markers (`markers = [...]`) so strict mode accepts them. Built-ins: `skip`, `skipif(condition, reason=...)`, `xfail(raises=..., strict=True)`, `usefixtures`, `filterwarnings`.
- pytest 9 has a built-in `subtests` fixture: `with subtests.test(i=i): assert ...` reports each iteration separately without parametrizing.

## 4. Built-in fixtures

```python
import json
from pathlib import Path

import pytest

from acme_tools.config import api_base, load_settings


def test_load_settings(tmp_path: Path) -> None:
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"debug": True}), encoding="utf-8")
    assert load_settings(f) == {"debug": True}


def test_api_base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACME_API_BASE", "http://localhost:9999")
    assert api_base() == "http://localhost:9999"
```

- `tmp_path` is a fresh `pathlib.Path` per test (`tmp_path_factory` for wider scopes); never write test files to fixed paths.
- `monkeypatch` sets and removes env vars (`setenv`, `delenv`), attributes (`setattr`), dictionary items (`setitem`) and the working directory (`chdir`); everything is undone after the test. Patch where the name is looked up, not where it is defined.
- `capsys` and `capfd` capture output (`capsys.readouterr().out`); `caplog` captures logging (`caplog.at_level(logging.WARNING, logger="acme")`, then `caplog.text` or `caplog.records`).
- `request`, `pytestconfig`, `cache` and `recwarn` cover plugin and introspection needs.
- Prefer passing fakes through parameters (protocols, factories) over patching; use `monkeypatch` for environment variables, the clock and third-party globals. General mocking strategy is covered in unit-testing-expert.

## 5. Async tests

```python
import pytest
import pytest_asyncio

from acme_tools.aio import fetch_all


@pytest_asyncio.fixture
async def started() -> str:
    return "ready"


@pytest.mark.asyncio
async def test_fetch_all(started: str) -> None:
    assert started == "ready"
    assert await fetch_all([1, 2, 3]) == ["id-1", "id-2", "id-3"]
```

- pytest does not run coroutine tests by itself; install pytest-asyncio (`uv add --dev pytest-asyncio`).
- With `asyncio_mode = "strict"` each async test needs `@pytest.mark.asyncio` and async fixtures use `@pytest_asyncio.fixture`. `auto` mode treats every async test and fixture as asyncio, which is convenient but conflicts with other async plugins.
- Set `asyncio_default_fixture_loop_scope` explicitly; the plugin warns when it is unset. Use `function` unless a fixture is expensive and safely shared.
- Keep tests deterministic: use `asyncio.timeout(...)` around waits instead of sleeping, and inject fake clients instead of real network calls.
- Test cancellation and timeout paths: start the coroutine in a `TaskGroup`, cancel it, and assert cleanup.

## 6. Coverage

```toml
[tool.coverage.run]
branch = true
source = ["acme_tools"]

[tool.coverage.report]
show_missing = true
fail_under = 90
```

- Run `uv run pytest --cov` (pytest-cov reads the config above) or `--cov=acme_tools --cov-report=term-missing --cov-fail-under=90`.
- Branch coverage (`branch = true`) reports untested `if`/`else` arms, not only unexecuted lines.
- Coverage shows what ran, not what was asserted. Treat a percentage as a floor and review the missing lines, especially error handling.
- `# pragma: no cover` excludes a line or block; use it only for code that cannot run in tests, such as `if __name__ == "__main__":`.

## 7. ruff configuration

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
extend-select = ["I", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.ruff.lint.isort]
known-first-party = ["acme_tools"]
```

- Without any `[tool.ruff]` table, ruff 0.17.3 enables a broad default rule set (several hundred rules across families such as `F`, `E`, `B`, `I`, `UP`, `S`, `ASYNC`, `PT`, `SIM`, `RUF`). Run `ruff check --show-settings` to see exactly what is active, and `ruff rule <CODE>` (for example `ruff rule B006`) to read a rule's explanation.
- `extend-select` adds families to the defaults; `select` replaces the default set, so a project that sets `select = ["E", "F"]` silently drops the rest. `ignore` removes specific codes; `per-file-ignores` scopes ignores by glob. `ruff config lint.extend-select` prints the option's documentation.
- Useful families: `I` (import sorting, replaces isort), `UP` (pyupgrade, rewrites to newer syntax per `requires-python`), `B` (bugbear), `S` (bandit security), `ASYNC` (blocking calls in coroutines), `PT` (pytest style), `PTH` (use `pathlib`), `PERF`, `SIM`, `RUF`, `D` (docstrings, enable deliberately and set a convention).
- `target-version` is inferred from `requires-python`; set `[tool.ruff] target-version` only to override it.
- The formatter is Black-compatible; options live under `[tool.ruff.format]` (`quote-style`, `indent-style`, `line-ending`, `docstring-code-format`). Do not run Black as well.
- Rules marked with `[*]` in the output have an automatic fix. Fixes are "safe" or "unsafe"; `--fix` applies safe ones, and unsafe ones need `--unsafe-fixes` and review because they can change behaviour.

## 8. ruff commands and suppressions

```bash
uv run ruff check .                # lint
uv run ruff check . --fix          # apply safe fixes
uv run ruff check . --statistics   # count violations per rule
uv run ruff check . --diff         # show fixes without writing
uv run ruff format .               # format
uv run ruff format --check .       # fail when formatting would change files
uv run ruff rule B006              # explain a rule
```

- Suppress one line with `# noqa: B006` followed by a reason, never a bare `# noqa`. `ruff check --add-noqa` inserts suppressions for every current violation, which is useful once when adopting a rule set but should be reviewed.
- Prefer fixing the code or narrowing `per-file-ignores` over broad `ignore` entries.
- Enable `RUF100` to report unused `noqa` comments.
- Editor integration uses `ruff server` (language server); pre-commit can run ruff through a hook whose version is pinned to match `uv.lock`.
- `uv format` runs ruff's formatter through uv; the version it uses may differ from the one in your dev group, so use `uv run ruff format` when the pinned version matters.

## 9. Command order for local work and CI

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests          # or: uv run pyright
uv run pytest --cov
uv build                       # libraries: verify the package builds
```

- Run the cheap checks first (format, lint) so failures return fast; run tests last.
- Test every Python version in `requires-python`, for example a matrix that adds `--python 3.13` and `--python 3.14` to `uv sync` and `uv run`.
- Run the same commands locally before pushing; a `Makefile` or a task runner entry can wrap them.
- Cache the uv cache directory between CI runs; do not cache `.venv` across Python versions.
- A scheduled job that runs with `uv lock --upgrade` and the full test suite surfaces breakage from new releases before it hits a feature branch.
