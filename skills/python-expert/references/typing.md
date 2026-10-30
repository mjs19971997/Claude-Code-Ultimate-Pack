# Typing and Type Checkers

Static typing patterns for Python 3.13 and 3.14, and configuring mypy and pyright. Verified against mypy 2.4.1, pyright 1.1.x and CPython 3.13 and 3.14 (2026-10); the code blocks were checked with both checkers in strict mode.

## Contents

1. [Choosing and configuring a checker](#1-choosing-and-configuring-a-checker)
2. [Modern syntax](#2-modern-syntax)
3. [Protocols and structural typing](#3-protocols-and-structural-typing)
4. [TypedDict and dataclasses](#4-typeddict-and-dataclasses)
5. [Overloads, decorators and ParamSpec](#5-overloads-decorators-and-paramspec)
6. [Narrowing](#6-narrowing)
7. [Annotations at runtime on 3.14](#7-annotations-at-runtime-on-314)
8. [Adopting types in an untyped codebase](#8-adopting-types-in-an-untyped-codebase)

## 1. Choosing and configuring a checker

- Use the checker the repository already runs in CI. For a new project either mypy or pyright is fine; running both doubles maintenance and the two disagree on edge cases.
- ty (marked Beta on PyPI) and pyrefly are newer checkers. `uv check` wraps ty and is itself marked experimental. Treat them as optional extras and check their current status before making them a gate.

```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_unreachable = true
enable_error_code = ["deprecated", "redundant-expr"]

[[tool.mypy.overrides]]
module = ["legacy.*"]
ignore_errors = true

[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "strict"
include = ["src", "tests"]
reportMissingTypeStubs = false
```

- `strict = true` in mypy turns on a bundle of flags (`disallow_untyped_defs`, `disallow_any_generics`, `warn_return_any`, `warn_unused_ignores`, `no_implicit_reexport`, `extra_checks` and more; `mypy --help` lists them). Adopt it per package with `[[tool.mypy.overrides]]` when migrating.
- pyright's modes are `off`, `basic`, `standard`, `strict`; per-file `# pyright: strict` comments raise the level for one file.
- Set `python_version` / `pythonVersion` to the lowest version you support so the checker flags syntax and stdlib APIs that do not exist there.
- Run: `uv run mypy src tests` and `uv run pyright` (the PyPI `pyright` package downloads the Node-based checker on first use). Cache directories (`.mypy_cache`, `.ruff_cache`) go in `.gitignore`.
- Third-party packages without inline types need stub packages (for example `types-requests`); add them to the dev group. Packages that ship a `py.typed` marker are typed.
- A typed library ships an empty `py.typed` file inside the package so users' checkers read its annotations.

## 2. Modern syntax

```python
from collections.abc import Callable, Sequence
from typing import Self


def first[T](items: Sequence[T]) -> T:
    return items[0]


class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> Self:
        self._items.append(item)
        return self

    def pop(self) -> T:
        return self._items.pop()


type Json = dict[str, Json] | list[Json] | str | int | float | bool | None
type Handler[**P, R] = Callable[P, R]


class Box[T = int]:  # TypeVar default, 3.13+
    def __init__(self, v: T) -> None:
        self.v = v
```

- PEP 695 syntax (3.12+) declares type parameters on the function or class; no `TypeVar` import is needed. Bounds and constraints: `def f[T: Hashable](x: T)`, `def g[T: (int, str)](x: T)`.
- `type Alias = ...` creates a lazily evaluated alias that can be recursive, as `Json` above.
- Use built-in generics (`list[int]`, `dict[str, int]`), `X | None` and `collections.abc` types. `typing.List`, `Dict`, `Optional` and `Union` still work but add noise.
- `Self` types fluent methods and alternative constructors; `@override` (from `typing`, 3.12+) makes the checker verify a method really overrides something.
- `Final` marks constants (`MAX: Final = 10`); `Literal["r", "w"]` types closed sets of values; `typing.NewType` creates distinct types for identifiers (`UserId = NewType("UserId", int)`).
- `Any` disables checking silently; prefer `object` for "anything, but I must narrow it" and `Protocol` for "anything with these methods".

## 3. Protocols and structural typing

```python
from collections.abc import Iterable
from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...


def shutdown(items: Iterable[Closeable]) -> None:
    for i in items:
        i.close()
```

- A class satisfies a `Protocol` by having the right members; it does not inherit. This keeps interfaces on the consumer side and lets tests pass plain fakes.
- `@runtime_checkable` allows `isinstance` checks, which only test that attributes exist, not their signatures.
- Prefer protocols for callbacks with several arguments or keyword-only parameters (`def __call__(self, x: int, *, flag: bool) -> str: ...`) over long `Callable[...]` types.
- Use `abc.ABC` when you need shared implementation or registration; use `Protocol` when you only need a shape.

## 4. TypedDict and dataclasses

```python
from dataclasses import dataclass
from typing import NotRequired, ReadOnly, TypedDict


class Movie(TypedDict):
    title: str
    year: NotRequired[int]
    id: ReadOnly[int]


@dataclass(frozen=True, slots=True, kw_only=True)
class Item:
    sku: str
    price_cents: int
```

- `TypedDict` types dictionaries that come from JSON or other APIs; the checker verifies keys and value types but nothing is validated at runtime. Validate untrusted input with a validation library, then rely on the types.
- `NotRequired[...]` marks optional keys (or use `total=False` for the whole class); `ReadOnly[...]` (3.13+) makes the checker reject assignment to a key.
- Use a dataclass (or `NamedTuple`) for internal records. `frozen=True` gives immutability and hashing; `slots=True` saves memory and blocks stray attributes; `kw_only=True` prevents positional mix-ups; `field(default_factory=list)` creates per-instance mutable defaults.
- Update frozen instances with `dataclasses.replace(obj, x=1)`; on 3.13+ `copy.replace(obj, x=1)` works too.
- `__post_init__` validates invariants. `InitVar` passes construction-only values.

## 5. Overloads, decorators and ParamSpec

```python
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import overload


@overload
def parse(x: str) -> int: ...
@overload
def parse(x: bytes) -> bytes: ...
def parse(x: str | bytes) -> int | bytes:
    return int(x) if isinstance(x, str) else x


def logged[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)

    return inner


def logged_async[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(fn)
    async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        return await fn(*args, **kwargs)

    return inner
```

- `@overload` signatures describe the public contract; the final unannotated-by-overload implementation must accept every case and is not visible to callers.
- Decorators that keep the wrapped signature use `ParamSpec` (`[**P]`) and `functools.wraps`; without them the decorated function loses its parameter types.
- A function that never returns normally has return type `Never` (or `NoReturn`); `assert_never(x)` at the end of a `match` or `if/elif` chain makes the checker prove all cases are handled.

## 6. Narrowing

```python
from typing import Literal, TypeIs, assert_never

Mode = Literal["r", "w"]


def is_str(val: object) -> TypeIs[str]:
    return isinstance(val, str)


def handle(m: Mode) -> int:
    match m:
        case "r":
            return 1
        case "w":
            return 2
        case _:
            assert_never(m)
```

- `isinstance`, `is None`, `in`, `len` checks on tuples, `match` patterns and truthiness narrow types inside the branch.
- `TypeIs[T]` (3.13+) narrows both branches: the `else` branch excludes `T`. The narrowed type must be a subtype of the parameter type, so `TypeIs[list[str]]` for a `list[object]` parameter is rejected by both checkers (lists are invariant); use `TypeGuard[list[str]]` there, which narrows only the positive branch.
- Avoid `cast` and `# type: ignore` as a first resort. When needed, use `cast("Type", value)` with a comment, and `# type: ignore[error-code]` (mypy) or `# pyright: ignore[ruleName]` so unrelated errors stay visible. Enable `warn_unused_ignores` (part of mypy `strict`) so stale ignores fail.

## 7. Annotations at runtime on 3.14

- Python 3.14 evaluates annotations lazily (PEP 649, PEP 749). A function or class can reference a name defined later without quotes:

```python
def make() -> Later:
    return Later()


class Later: ...
```

- Reading annotations goes through `annotationlib`:

```python
import annotationlib

annotationlib.get_annotations(make, format=annotationlib.Format.VALUE)       # real objects; NameError if undefined
annotationlib.get_annotations(make, format=annotationlib.Format.FORWARDREF)  # unresolved names become placeholders
annotationlib.get_annotations(make, format=annotationlib.Format.STRING)      # {'return': 'Later'}
```

- `typing.get_type_hints()` keeps working. Libraries that read annotations at runtime (dataclass-like frameworks, validators, dependency injectors) should use `FORWARDREF` or `STRING` when they must tolerate names that are not defined yet.
- On 3.13 and earlier, forward references still need quotes, a later definition, or `from __future__ import annotations`. Code that must run on both versions keeps one of those. Check the docs for the long-term status of the `__future__` import.

## 8. Adopting types in an untyped codebase

1. Start with `strict = false`, `check_untyped_defs = true`, and fix real errors the checker finds.
2. Annotate leaf modules first (utilities, models), then callers; add `[[tool.mypy.overrides]]` with `disallow_untyped_defs = true` for each module as it is finished.
3. Replace `Any` at module boundaries with `Protocol`, `TypedDict` or a dataclass.
4. Keep a counter or baseline of remaining ignores; require a reason or error code on each new one.
5. Turn on `strict` for the whole package once overrides cover everything, then remove the overrides.
6. Type tests lightly: annotate fixtures and parameters (`tmp_path: Path`, `monkeypatch: pytest.MonkeyPatch`) so the checker sees them.
