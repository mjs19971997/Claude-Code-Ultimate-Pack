# Packaging and uv

Project metadata in `pyproject.toml`, build backends, and the uv workflow for interpreters, dependencies, lockfiles, scripts, workspaces, building and publishing. Verified against uv 0.13.6, hatchling 1.33.x and Python 3.13 and 3.14 (2026-10).

## Contents

1. [pyproject.toml anatomy](#1-pyprojecttoml-anatomy)
2. [Build backends](#2-build-backends)
3. [uv project commands](#3-uv-project-commands)
4. [Lockfile and reproducible installs](#4-lockfile-and-reproducible-installs)
5. [Interpreters](#5-interpreters)
6. [Scripts and tools](#6-scripts-and-tools)
7. [Workspaces and sources](#7-workspaces-and-sources)
8. [Build and publish](#8-build-and-publish)
9. [Migrating from pip and requirements.txt](#9-migrating-from-pip-and-requirementstxt)

## 1. pyproject.toml anatomy

```toml
[project]
name = "acme-tools"
version = "0.1.0"
description = "Small example package"
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"
dependencies = [
    "httpx>=0.28",
]

[project.optional-dependencies]
cli = ["rich>=14"]

[project.scripts]
acme = "acme_tools.cli:main"

[dependency-groups]
dev = ["pytest>=9", "pytest-cov>=7", "mypy>=2", "ruff>=0.17"]

[build-system]
requires = ["uv_build>=0.13.6,<0.14.0"]
build-backend = "uv_build"
```

- `[project]` is the standard metadata table (PEP 621). `name`, and either `version` or `dynamic = ["version"]`, are required.
- `license = "MIT"` is an SPDX expression; older metadata used a table form (`license = { text = "MIT" }`), so check the backend's docs when upgrading old projects.
- `[project.optional-dependencies]` are extras that end users install (`pip install "acme-tools[cli]"`). They are published.
- `[dependency-groups]` (PEP 735) are development sets such as `dev`, `docs`, `lint`. They are not published and are not extras. uv installs the `dev` group by default on `uv sync`; add more with `--group docs` or `--all-groups`.
- `[project.scripts]` creates console commands from `module:function`; `[project.gui-scripts]` and `[project.entry-points."group"]` cover other cases.
- `requires-python` is a contract with installers: pip refuses to install on older interpreters, and uv resolves for the whole range, so tools such as ruff also infer their target version from it.
- Dependency specifiers follow PEP 508: `"httpx>=0.28,<1"`, `"tomli; python_version < '3.11'"`, `"pkg[extra]>=1"`.

## 2. Build backends

| Backend | Use when | Notes |
|---|---|---|
| `uv_build` | New pure-Python projects using uv | Default for `uv init`; pin a range that matches your uv minor version (`>=0.13.6,<0.14.0`); expects `src/<import_name>/__init__.py` by default |
| `hatchling` | You need build hooks, dynamic versions from VCS, or extra file inclusion | `requires = ["hatchling>=1.27"]`, `build-backend = "hatchling.build"`; detects `src/<name>` automatically; configured under `[tool.hatch.*]` |
| `setuptools` | Legacy projects or C extensions already built with it | `requires = ["setuptools"]` with a recent lower bound, `build-backend = "setuptools.build_meta"`; keep config in `pyproject.toml` rather than `setup.py` |
| `maturin`, `scikit-build-core` | Rust or CMake extensions | Pick via `uv init --build-backend maturin` or `scikit` |
| `flit-core`, `pdm-backend`, `poetry-core` | Existing projects that use them | Keep the existing backend unless migration is the task |

- `uv init --build-backend <name>` accepts `uv`, `hatch`, `flit`, `pdm`, `poetry`, `setuptools`, `maturin` and `scikit`.
- In uv 0.13.6 `uv init` (an application by default) and `uv init --lib` both write a `[build-system]` table with `uv_build` and a `src/` layout; `--no-package` opts out. `uv init --bare` writes only a minimal `[project]` table.
- A project without `[build-system]` is not installed into its own environment; only its dependencies are. Applications that are only run with `uv run` can work that way.
- The backend is installed in an isolated environment at build time. Pin it with an upper bound when you depend on its behaviour.
- `uv init` fills `authors` from git by default; use `--author-from none` to leave it out.

## 3. uv project commands

```bash
uv init my-app --package --python 3.13   # create project, src layout, .python-version
uv add httpx "pydantic>=2"               # add runtime dependencies, update uv.lock, sync .venv
uv add --dev pytest ruff mypy            # add to the dev dependency group
uv add --group docs mkdocs               # add to a named dependency group
uv add --optional cli rich               # add to an extra
uv remove httpx                          # remove a dependency
uv sync                                  # make .venv match uv.lock (includes dev group)
uv run pytest -x                         # run in the project environment (locks and syncs first)
uv run python -m acme_tools              # run a module
uv tree                                  # dependency tree
uv version --bump minor --dry-run        # preview a version bump (omit --dry-run to write it)
```

- `uv run` checks that `uv.lock` matches `pyproject.toml` and the environment matches the lock, then runs the command; `--no-sync` skips the sync, `--locked` fails if the lock is stale, `--frozen` uses the lock without checking it.
- `uv run --with rich python -c "import rich"` adds a temporary dependency without changing the project.
- `uv add` edits `pyproject.toml` and the lockfile together; `--bounds` chooses the written specifier style (`lower`, `major`, `minor`, `exact`).
- `uv sync --no-dev` leaves the dev group out; `--extra cli` or `--all-extras` include extras; `--no-install-project` installs only dependencies, which helps layer caching in image builds (the Dockerfile itself belongs to docker-expert).
- `uv format` runs ruff's formatter on the project (`--check` and `--diff` available). `uv check` is marked experimental and `uv audit` contacts a vulnerability database; check the docs before relying on them in CI.
- `uv pip install -r requirements.txt` and `uv pip compile` give a pip-compatible interface for projects not yet on the uv project model.

## 4. Lockfile and reproducible installs

- `uv.lock` is a universal, cross-platform lockfile that records exact versions and hashes. Commit it for applications and for libraries' development environments.
- `uv lock` creates or updates it; `uv lock --check` verifies it is current without writing (use in CI); `uv lock --upgrade` or `-P httpx` upgrades everything or one package.
- Installs in CI and production: `uv sync --locked` (error if the lock is out of date) or `uv sync --frozen` (no freshness check).
- `--exclude-newer <date>` restricts resolution to packages uploaded before a date; useful for reproducing an older environment or delaying adoption of brand-new releases.
- `uv export --format requirements.txt --no-hashes --no-dev` writes a requirements file for tools that cannot read `uv.lock`; `--format pylock.toml` and `--format cyclonedx1.5` export other formats.
- Libraries should keep dependency ranges wide in `pyproject.toml`; the lockfile pins only the development environment.
- Resolution notes: uv resolves for every platform and every Python in `requires-python`. A dependency that supports fewer interpreters than your range makes the lock fail or fork; narrow `requires-python` or use environment markers.

## 5. Interpreters

```bash
uv python list                  # installed and downloadable interpreters
uv python install 3.14          # download a managed CPython
uv python install 3.14t         # the free-threaded build
uv python pin 3.13              # write .python-version
uv run --python 3.14 python -V  # run with a specific interpreter
uv venv --python 3.13           # create .venv without a project
```

- uv honours `.python-version` and `requires-python` when choosing an interpreter, and downloads a managed build when none fits (disable with `--no-python-downloads` or `UV_PYTHON_DOWNLOADS=never`).
- Managed interpreters come from the python-build-standalone project; `uv python upgrade` moves installed managed versions to the latest supported patch release.
- On a free-threaded interpreter, `sys._is_gil_enabled()` returns `False`; `PYTHON_GIL=1` turns the GIL back on for a run. Check each extension's docs for free-threading support before relying on it.
- Test the lowest and highest supported versions in CI: `uv run --python 3.13 pytest` and `uv run --python 3.14 pytest`, or a matrix of `uv sync --python`.

## 6. Scripts and tools

Inline script metadata (PEP 723) lets a single file declare its interpreter and dependencies:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich>=14"]
# ///
from rich import print

print("[bold]hello[/bold]")
```

- `uv run script.py` creates a cached environment from the block. `uv init --script script.py` writes the header and `uv add --script script.py 'rich>=14'` edits it; `uv lock --script` locks it.
- `uv tool run ruff check .` (alias `uvx ruff check .`) runs a command-line tool in a temporary isolated environment; `uvx ruff@0.17.3 check .` pins a version.
- `uv tool install ruff` installs a tool permanently on `PATH`; `uv tool upgrade --all`, `uv tool list`, `uv tool uninstall` manage them.
- Keep project-specific tools (ruff, mypy, pytest) in the `dev` dependency group so every contributor and CI uses the locked version; use `uvx` for one-off utilities.

## 7. Workspaces and sources

```toml
# root pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
core-lib = { workspace = true }
```

- A workspace shares one `uv.lock` and one virtual environment across several packages; `uv add ./packages/core` from the root registers the member and writes the `workspace = true` source.
- `uv sync --all-packages` installs every member; `uv run --package core-lib pytest` runs inside one member.
- `[tool.uv.sources]` redirects a dependency name to a local path, a git URL or a specific index (`httpx = { git = "https://github.com/encode/httpx", rev = "..." }`). Sources are uv-specific and are ignored by other tools and by published metadata, so a published package must still name a real index version in `dependencies`.
- Private indexes: declare under `[[tool.uv.index]]` with a `name` and `url`, and keep credentials out of `pyproject.toml`; check the uv docs for the supported mechanisms (environment variables, keyring, `uv auth`). Set `explicit = true` on an index so only packages that name it in `tool.uv.sources` are fetched from it.

## 8. Build and publish

```bash
uv build                  # writes dist/*.tar.gz and dist/*.whl
uv build --wheel          # wheel only
python -m zipfile -l dist/*.whl   # list wheel contents before upload
uv publish --dry-run      # check the upload without sending
uv publish                # upload dist/* ; token from UV_PUBLISH_TOKEN or trusted publishing
```

- Check the wheel includes your package, `py.typed` for typed libraries, and no tests, secrets or `.env` files. Hatchling honours `[tool.hatch.build.targets.wheel]` `packages`/`include`/`exclude`; `uv_build` has `[tool.uv.build-backend]` options (check the docs for the current keys).
- Prefer trusted publishing from CI (OIDC to the index) so no long-lived token exists: `uv publish --trusted-publishing always` in a workflow with the permissions the index documents. Otherwise provide a scoped token via `UV_PUBLISH_TOKEN` from a secret store.
- Use a unique, increasing version per upload; indexes reject re-uploads of the same file. `uv version --bump patch|minor|major` edits `pyproject.toml`.
- Upload to a test index first when changing packaging metadata (`uv publish --index <name>` with an index declared in `pyproject.toml`).

## 9. Migrating from pip and requirements.txt

1. `uv init --bare` (or add a `[project]` table by hand) in the repository root; set `requires-python` to the real supported range.
2. `uv add -r requirements.txt` imports runtime dependencies; `uv add --dev -r requirements-dev.txt` imports development ones.
3. Replace loose pins that were only there to reproduce a build with ranges; the lock now records exact versions.
4. Update CI: `uv sync --locked`, then `uv run pytest`. Remove `pip install -r` steps and virtualenv caching, and cache the uv cache directory instead.
5. Remove or regenerate `requirements*.txt` only if some consumer still needs them (`uv export --no-hashes`).
6. From poetry or pdm: move `[tool.poetry.dependencies]` entries into `[project.dependencies]` using PEP 508 specifiers (poetry's `^1.2` means `>=1.2,<2`), move group tables to `[dependency-groups]`, then `uv lock`. Run the test suite before deleting the old lockfile.
