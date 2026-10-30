---
name: rust-expert
description: >-
  Writes, reviews and debugs Rust 2024 edition code: ownership, borrowing and lifetimes, error handling with Result, thiserror and anyhow, traits and generics, async Rust on tokio, Cargo workspaces, clippy and rustfmt, unsafe code, and tests. Use when working with Cargo.toml, Cargo.lock, rust-toolchain.toml, .rs files, borrow checker errors (E0382, E0499, E0502, E0597, E0106), cargo build, test, clippy, fmt, miri, nextest, audit or deny, or migrating to edition 2024. Not for container images (use docker-expert), smart contracts (use solidity-expert), or OpenTelemetry pipelines (use observability-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Rust Expert

This skill covers everyday and production Rust: the 2024 edition and its migration, ownership and lifetimes, error types, trait design, async code on tokio, Cargo workspaces, lints and formatting, unsafe code, testing and dependency auditing. Deep material sits in the reference files; this file holds the rules needed on every task. Container packaging, on-chain code and telemetry pipelines belong to other skills.

> Verified against Rust 1.99.1 stable (edition 2024, stable since 1.85.0), Cargo 0.100, tokio 1.54.1, thiserror 2.0.21, anyhow 1.0.104, proptest 1.12.0, cargo-nextest 0.9.150, cargo-deny 0.20.2, cargo-audit 0.22.2 (2026-10).

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

- Covered: Rust 2024 edition features and `cargo fix --edition` migration, ownership, borrowing, lifetimes and smart pointers, `Result` and `?`, `thiserror` for library errors, `anyhow` for application errors, traits, generics, `dyn` versus `impl`, `async fn` in traits, tokio runtime, tasks, channels, `select!`, cancellation and `spawn_blocking`, Cargo workspaces and features, clippy, rustfmt, `unsafe` and Miri, unit, integration and doc tests, proptest, nextest, `cargo audit` and `cargo deny`.
- Not covered: container images and Dockerfiles for Rust services (docker-expert), smart contracts and Solidity tooling (solidity-expert), OpenTelemetry collectors and trace pipelines (observability-expert), Kubernetes manifests (kubernetes-expert), CI pipeline design (cicd-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Edition 2024 | Stable since Rust 1.85.0. New projects from `cargo new` get `edition = "2024"`. Migrate with `cargo fix --edition`, then change the edition key. The minimum `rust-version` for an edition 2024 crate is 1.85 |
| `unsafe extern` | `extern` blocks must be written `unsafe extern "C" { ... }`. Items inside may be marked `safe fn` / `safe static` when any argument is sound; unmarked items default to unsafe |
| Unsafe attributes | `no_mangle`, `export_name` and `link_section` must be written `#[unsafe(no_mangle)]` and so on, with a SAFETY comment |
| `unsafe_op_in_unsafe_fn` | Warns by default in 2024: the body of an `unsafe fn` is not an implicit unsafe block. Wrap each unsafe operation in `unsafe { }` |
| `static mut` | `static_mut_refs` is `deny` in 2024: no `&X` or `&mut X` to a `static mut`. Use `AtomicXxx`, `Mutex`, `OnceLock` or `&raw const` / `&raw mut` |
| `env::set_var` | `std::env::set_var` and `remove_var` are `unsafe` in 2024 (unsound with other threads). Set variables before spawning threads, or pass values explicitly |
| RPIT capture | Return-position `impl Trait` captures all in-scope generic and lifetime parameters by default. Opt out with `+ use<..>` (for example `impl Iterator<Item = u32> + use<>`) |
| Tail expressions | Temporaries in a block's tail expression are dropped before the block's locals, so `c.borrow().len()` as the last expression no longer fails with E0597 |
| `if let` scope | Temporaries in the scrutinee of `if let` are dropped before the `else` branch, which removes a class of lock-held-in-else deadlocks |
| `let` chains | `if let Some(a) = x && let Some(b) = y && cond { }` is allowed in edition 2024 (`if` and `while`) |
| `gen` keyword | Reserved in 2024. An identifier called `gen` must become `r#gen`; `cargo fix --edition` does it |
| Prelude | `Future` and `IntoFuture` are in the 2024 prelude; an ambiguous method call may need a fully qualified path |
| Cargo 2024 | `edition = "2024"` implies `resolver = "3"` (Rust-version-aware resolution). Virtual workspaces must set `resolver = "3"` explicitly. Underscore key spellings such as `dev_dependencies` and `default_features` are rejected |
| Inherited features | Since Rust 1.99, `default-features` set on an inherited dependency in a 2024 package overrides the `[workspace.dependencies]` entry; on 1.85 to 1.98 that combination is an error |
| Doctests | Edition 2024 combines doctests into one binary for speed; tests still run in separate processes. An example that cannot be combined (for example one using `global_allocator`) takes the `standalone_crate` tag |
| async fn in traits | Stable since 1.75. A trait with `async fn` is not dyn compatible. For work moved across threads, write `fn f(&self) -> impl Future<Output = T> + Send` in the trait |
| tokio | 1.54.x, MSRV 1.85. Features are opt-in; `full` enables everything. `net`, `time`, `macros`, `rt-multi-thread`, `signal`, `sync`, `fs`, `io-util` are the common ones |
| Error crates | thiserror 2.x (derive `Error` for libraries), anyhow 1.x (`anyhow::Result`, `.context()` for applications) |
| Tooling | `cargo clippy`, `cargo fmt`, `cargo miri` (nightly component), `cargo nextest run` (does not run doctests, so also run `cargo test --doc`), `cargo audit`, `cargo deny check` |

## 3. Workflow

1. Read `Cargo.toml`, `rust-toolchain.toml`, `rustfmt.toml`, `clippy.toml` and `[lints]` first: edition, `rust-version`, workspace layout, enabled features. Do not assume 2021 or a recent compiler.
2. Reproduce with the smallest command: `cargo check -p <crate>`, then `cargo test -p <crate> <name>`. Read the full compiler message; Rust errors usually contain the fix.
3. For borrow errors, state who owns the value, who borrows it and for how long before editing. Prefer restructuring (split borrows, shorter scopes, owned data) over `clone()` or `Rc<RefCell<_>>`.
4. For async code, identify where each future can be dropped (every `.await` inside `select!`, timeout or abort) and what is lost when it is.
5. Keep the change minimal and follow the repository's error-handling and module style.
6. Run `cargo fmt --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace` and `cargo test --doc`. Report what was run.
7. For `unsafe` changes, add or update the `// SAFETY:` comment and run the affected tests under Miri when the toolchain allows it.
8. For dependency changes, run `cargo deny check` or `cargo audit` and `cargo tree -d` to see duplicate versions.

## 4. Decision Rules

- If code is a library or a reusable crate, then define a typed error enum with `thiserror` so callers can match on variants; use `anyhow` in binaries, tests and glue code where the only action is to report.
- If a function never needs ownership, then take `&str`, `&[T]`, `&Path` rather than `&String`, `&Vec<T>`, `&PathBuf`.
- If a value is returned and may or may not be modified, then return `Cow<'_, str>` instead of cloning in the common case.
- If the set of implementations is closed or heterogeneous collections are needed, then use an `enum` or `Box<dyn Trait>`; if the type is known at compile time and speed matters, then use generics or `impl Trait` (static dispatch, monomorphized).
- If a trait must be used as `dyn Trait` and has async methods, then use a boxed future return (`Pin<Box<dyn Future<Output = T> + Send + '_>>`) or the `async-trait` crate; native `async fn` in traits is not dyn compatible.
- If work is CPU-bound or calls a blocking API for more than a few tens of microseconds, then use `tokio::task::spawn_blocking` (or a dedicated thread or rayon pool) rather than running it on a worker thread.
- If shared state is held only briefly and never across `.await`, then use `std::sync::Mutex`; use `tokio::sync::Mutex` only when the lock must be held across an await point, and prefer message passing (`mpsc`) to a shared lock.
- If a loop in `select!` reads partial data (for example `read_exact` into a local buffer), then move the state outside the loop or use a cancellation-safe method, because a losing branch is dropped.
- If a type does not need to be shared across threads, then use `Rc` and `RefCell`; for threads use `Arc` with `Mutex` or `RwLock`, or atomics for counters and flags.
- If several crates share dependencies, versions, lints or metadata, then use a workspace with `[workspace.dependencies]`, `[workspace.package]` and `[workspace.lints]`.
- If the project needs to compile on an older compiler, then set `rust-version` and test it in CI; do not rely on the latest stable only.
- If unsafe code is needed, then isolate it in a small module with a safe API, document invariants, and prefer an established crate over a hand-written FFI or pointer structure.

## 5. Coding Standards

- Format with `cargo fmt`; set `style_edition = "2024"` in `rustfmt.toml` if `rustfmt` is invoked directly, because plain `rustfmt` defaults to the 2015 style while `cargo fmt` infers it from the manifest.
- Run clippy with `-D warnings` in CI; configure lints centrally under `[workspace.lints]` and opt in with `[lints] workspace = true` in each member.
- Use `#[expect(lint, reason = "...")]` instead of `#[allow(lint)]` for deliberate exceptions, so a stale suppression is reported.
- Public items get doc comments with a runnable example when practical; add `# Errors`, `# Panics` and `# Safety` sections where they apply.
- No `unwrap()` or `expect()` on fallible runtime input in library or service code. `expect("invariant: ...")` is fine for proven invariants and in tests.
- Return `Result<T, E>`; avoid `panic!` for recoverable failures. Do not use `Box<dyn Error>` in public library APIs.
- Derive `Debug` on public types; add `Clone`, `PartialEq`, `Eq`, `Hash`, `Default` only when they are meaningful.
- Prefer iterators and combinators to index loops; prefer `match` or `let ... else` to nested `if let`.
- Make invalid states unrepresentable: newtypes for IDs and units, enums for state, builder or typestate for multi-step construction.
- Every `unsafe` block has a `// SAFETY:` comment stating why the preconditions hold; every `unsafe fn` and `unsafe trait` has a `# Safety` doc section.
- Name crates and modules in `snake_case`, types in `UpperCamelCase`, constants in `SCREAMING_SNAKE_CASE`; keep `pub` surface minimal and use `pub(crate)`.

## 6. Project Structure

```text
workspace/
├── Cargo.toml              # [workspace], resolver, shared deps, lints, profiles
├── Cargo.lock              # committed for binaries and workspaces with binaries
├── rust-toolchain.toml     # pinned channel and components (clippy, rustfmt)
├── rustfmt.toml            # style_edition = "2024"
├── deny.toml               # cargo-deny policy: advisories, licenses, bans, sources
├── crates/
│   ├── app/                # binary: main.rs, wiring, anyhow, tokio runtime
│   │   └── src/main.rs
│   └── core/               # library: domain types, thiserror errors
│       ├── src/lib.rs
│       ├── tests/          # integration tests, one file per scenario
│       └── benches/        # optional benchmarks
└── .github/workflows/      # fmt, clippy, test, deny (see cicd-expert)
```

- Keep `main.rs` thin: parse config, build dependencies, call a library `run()`; this makes the logic testable.
- Split a crate when compile time, public API boundaries or dependency weight justify it, not by default.
- Unit tests live next to code in `#[cfg(test)] mod tests`; integration tests in `tests/` can only use the public API.

## 7. Design Patterns

- **Newtype**: `struct UserId(u64);` prevents argument mix-ups at zero runtime cost; add `From`/`TryFrom` at the boundary.
- **Builder**: for types with many optional fields; the cost is extra code, so use it once there are about four or more options.
- **Typestate**: encode protocol state in a generic parameter (`Conn<Open>`) so illegal sequences fail to compile; the cost is more types and harder trait objects.
- **RAII guard**: release resources in `Drop` (locks, temp files, spans); never rely on `Drop` for something that must be awaited or can fail, use an explicit `close().await`.
- **Extension trait**: add methods to foreign types without wrapping them; keep it `pub(crate)` unless it is part of the API.
- **Sealed trait**: a public trait with a private supertrait lets the crate add methods without a breaking change.
- **Message passing**: own state in one task and talk to it over `mpsc` plus a `oneshot` reply channel; avoids lock ordering and holding locks across awaits.
- **Cow**: borrow when no change is needed, own when it is; adds a branch and a lifetime parameter.
- **Interior mutability**: `Cell`, `RefCell`, `Mutex`, `RwLock`, `OnceLock` move borrow checks to runtime; use sparingly and keep the guarded section short.

## 8. Best Practices

- Pass borrowed data in and return owned data out at API boundaries; add lifetime parameters to structs only when a borrowed view is the point (parsers, iterators).
- Let lifetime elision work; name lifetimes only when elision fails or the signature needs relations (`fn pick<'a>(a: &'a str, b: &'a str) -> &'a str`).
- Add context where errors cross a layer: `.context("reading config")` in applications, a `source` field in `thiserror` variants in libraries. Keep the original error as the source instead of formatting it into a string.
- Use `#[non_exhaustive]` on public error enums and config structs that may grow.
- Keep futures `Send` when they run on the multi-thread runtime: do not hold `Rc`, `RefCell` borrows or a `std::sync::MutexGuard` across `.await`.
- Bound everything that can grow: use `mpsc::channel(n)` (bounded) rather than unbounded channels, and a `Semaphore` to limit concurrent work.
- Give every network and external call a timeout (`tokio::time::timeout`) and a shutdown path (`CancellationToken` from tokio-util).
- Track spawned tasks in a `JoinSet` so errors and panics are observed and tasks are cancelled on drop.
- Gate heavy dependencies behind Cargo features; features must be additive, so enabling one never removes functionality.
- Commit `Cargo.lock` for applications; pin the toolchain with `rust-toolchain.toml`.
- Read the docs of the exact version in `Cargo.lock` (`cargo doc --open`, docs.rs); APIs and defaults change between majors such as thiserror 1 to 2.

## 9. Performance

- Measure first: `cargo build --release`, then a benchmark (criterion or the project's choice) or a profiler (`perf`, flamegraph). Debug builds are often 10 to 100 times slower and say nothing about release speed.
- Avoid needless allocation: reserve capacity (`Vec::with_capacity`), reuse buffers, take `&str` and return `Cow`, use `collect` into a typed container once.
- Avoid `clone()` as a borrow checker workaround in hot paths; restructure or use `Arc`/`Rc` deliberately for shared immutable data.
- Static dispatch (generics) is faster but grows binary size and compile time; use `dyn` at cold boundaries and where heterogeneity is needed.
- Release profile knobs: `lto = "thin"` or `"fat"`, `codegen-units = 1`, `panic = "abort"` (only when unwinding is not needed), `opt-level`; each trades compile time or behavior, so measure.
- In async code, do not block the executor: a blocking call stalls other tasks on that worker. Detect with `tokio-console` or by checking for long polls.
- Use `tokio::sync::mpsc` batch receive (`recv_many`) and buffered I/O (`BufReader`, `BufWriter`) before reaching for lock-free structures.
- Compile time: `cargo check` for the inner loop, `cargo tree -d` to cut duplicate dependencies, trim tokio features, and consider a shared `target` cache in CI.

## 10. Security

- Memory safety holds only in safe code: every `unsafe` block is an audit point. Keep the block as small as possible, state the invariant in `// SAFETY:`, and deny `unsafe_op_in_unsafe_fn` plus `clippy::undocumented_unsafe_blocks` in `[workspace.lints]`.
- Add `#![forbid(unsafe_code)]` to crates that need no unsafe.
- Run unsafe-heavy tests under Miri (`cargo +nightly miri test`) to catch out-of-bounds access, use after free, invalid alignment and data races in tested paths. Miri covers only executed paths.
- Supply chain: run `cargo audit` (RustSec advisories) and `cargo deny check` (advisories, licenses, bans, sources) in CI; review new dependencies, their maintainers and build scripts; commit `Cargo.lock`.
- Do not run `cargo` commands (build scripts and proc macros execute code) on untrusted projects; `cargo audit --file Cargo.lock` audits a lockfile without building.
- Read secrets from the environment or a secrets manager, never from source; wrap them in a type whose `Debug` does not print the value (for example a `Secret` newtype) so logs stay clean.
- Parse untrusted input into typed values at the boundary; check sizes before allocating; use `checked_*` or `saturating_*` arithmetic where overflow matters, since release builds wrap by default.
- Path handling: canonicalize and verify that a joined path stays under the base directory before opening it; reject `..` components from user input.
- Build SQL with bound parameters (sqlx, diesel, tokio-postgres parameters), never `format!`.
- Use rustls-based TLS with certificate verification on; never disable verification to silence an error.
- `unwrap()` on user-controlled data is a denial-of-service bug; return an error.

## 11. Testing

- Unit tests: `#[cfg(test)] mod tests` beside the code; they can reach private items. Run `cargo test -p <crate>`.
- Integration tests: files in `tests/` compile as separate crates against the public API; share helpers in `tests/common/mod.rs`.
- Doc tests: code blocks in `///` comments are compiled and run by `cargo test --doc`; use them to keep examples correct. Use `no_run` for code that must compile but not execute.
- Async tests: `#[tokio::test]` (needs tokio features `macros` and `rt`); `#[tokio::test(start_paused = true)]` with the `test-util` feature makes `sleep` and `timeout` deterministic and instant.
- Property tests: proptest (`proptest! { #[test] fn f(x in 0u32..1000) { prop_assert!(...) } }`) for parsers, round trips and invariants; commit regression files it writes.
- cargo-nextest (`cargo nextest run`) runs each test in its own process, with better output and retries; it does not run doctests, so keep `cargo test --doc` as a separate step.
- Failure paths: assert on error variants with `matches!` or `assert!(matches!(...))`, check `source()` chains, and test cancellation and timeouts for async code.
- Miri for unsafe code, `cargo test --release` occasionally for overflow behavior differences, and a build with `--no-default-features` and `--all-features` for feature combinations.
- Coverage: `cargo llvm-cov` (cargo-llvm-cov 0.9.x) if the project tracks it.

## 12. Review Checklist

- [ ] Edition, `rust-version` and resolver in `Cargo.toml` match the code (2024 rules applied, no `gen` identifiers, `unsafe extern`, `#[unsafe(no_mangle)]`).
- [ ] `cargo fmt --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace` and `cargo test --doc` pass.
- [ ] No `unwrap()` or `expect()` on runtime input; errors carry context and keep their source.
- [ ] Library errors are typed (`thiserror`); application code uses `anyhow`; no `Box<dyn Error>` in public library signatures.
- [ ] Every `unsafe` block has `// SAFETY:`; every `unsafe fn` has `# Safety`; unsafe code is covered by tests or Miri.
- [ ] No lock or `RefCell` borrow held across `.await`; no blocking calls on async worker threads.
- [ ] Spawned tasks are tracked and cancellable; channels and concurrency are bounded; external calls have timeouts.
- [ ] `select!` branches are cancellation safe or their state lives outside the loop.
- [ ] New dependencies reviewed, features trimmed, `cargo deny check` or `cargo audit` clean, `Cargo.lock` updated.
- [ ] No secrets in source, logs or `Debug` output; SQL uses parameters; TLS verification stays on.
- [ ] Public API documented; `#[non_exhaustive]` considered for growing enums; semver impact understood.

## 13. Production Notes

- Release builds: `cargo build --release --locked` so the lockfile is honored; keep `debug = "line-tables-only"` or separate debuginfo for usable backtraces.
- Pin the toolchain in `rust-toolchain.toml` and update it deliberately; stable releases arrive about every six weeks, and a new edition needs a migration PR (`cargo fix --edition`, then review the diff).
- Graceful shutdown: listen for `tokio::signal::ctrl_c()` (and SIGTERM through `tokio::signal::unix` on Unix), cancel a `CancellationToken`, drain the `JoinSet`, and bound the whole shutdown with a timeout.
- Panics: decide per binary between `panic = "abort"` (smaller, crash-only) and unwinding (needed by `catch_unwind` and for the runtime to report a panicked task as a `JoinError`). A panic in a spawned tokio task is contained in that task.
- Logging and metrics: use the `tracing` ecosystem for structured events; shipping traces to a collector is covered by observability-expert.
- Dependencies: schedule `cargo update` and `cargo audit` in CI, watch yanked crates, and prefer native async fn in traits over the `async-trait` crate where dyn dispatch is not needed.
- MSRV policy: state it in `rust-version`, test it in CI, and bump it in a minor release with a changelog entry. The Rust-version-aware resolver (`resolver = "3"`) then avoids dependency versions that need a newer compiler.
- Publishing: `cargo publish --dry-run`, check `cargo package --list`, and set `package.include` or `exclude` so test fixtures and secrets do not ship.
- Container images for the built binary are covered by docker-expert.

## 14. Examples

A workspace manifest with a Rust-version-aware resolver, inherited metadata, shared dependencies and shared lints.

```toml
[workspace]
resolver = "3"
members = ["crates/*"]
default-members = ["crates/app"]

[workspace.package]
edition = "2024"
rust-version = "1.85"
license = "MIT"
publish = false

[workspace.dependencies]
core-lib = { path = "crates/core" }
anyhow = "1"
thiserror = "2"
tokio = { version = "1", default-features = false }
tokio-util = "0.7"
proptest = "1"

[workspace.lints.rust]
unsafe_op_in_unsafe_fn = "deny"
missing_debug_implementations = "warn"

[workspace.lints.clippy]
undocumented_unsafe_blocks = "deny"
dbg_macro = "warn"
```

A member opts in with `edition.workspace = true`, `rust-version.workspace = true`, `thiserror.workspace = true` and a `[lints]` table containing `workspace = true`.

A typed library error, a fallible parser and its tests (unit test plus property test):

```rust
use std::num::ParseIntError;

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("invalid port {value:?}")]
    Port {
        value: String,
        #[source]
        source: ParseIntError,
    },
    #[error("port {0} is reserved")]
    Reserved(u16),
}

pub fn parse_port(value: &str) -> Result<u16, ConfigError> {
    let port: u16 = value.trim().parse().map_err(|source| ConfigError::Port {
        value: value.to_owned(),
        source,
    })?;
    if port < 1024 {
        return Err(ConfigError::Reserved(port));
    }
    Ok(port)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn reserved_port_is_rejected() {
        assert!(matches!(parse_port("80"), Err(ConfigError::Reserved(80))));
    }

    proptest! {
        #[test]
        fn roundtrip(port in 1024u16..=u16::MAX) {
            prop_assert_eq!(parse_port(&port.to_string()).unwrap(), port);
        }
    }
}
```

An async worker that stops on cancellation, keeps CPU work off the runtime threads and propagates a panic from the blocking task as an error (needs tokio features `rt-multi-thread`, `macros`, `sync`, `time` and the `tokio-util` and `anyhow` crates):

```rust
use anyhow::{Context, Result};
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;

fn checksum(data: &[u8]) -> u64 {
    data.iter().fold(0u64, |acc, b| {
        acc.wrapping_mul(31).wrapping_add(u64::from(*b))
    })
}

async fn worker(mut rx: mpsc::Receiver<Vec<u8>>, token: CancellationToken) -> Result<()> {
    loop {
        tokio::select! {
            () = token.cancelled() => return Ok(()),
            msg = rx.recv() => {            // mpsc recv is cancellation safe
                let Some(buf) = msg else { return Ok(()) };
                let sum = tokio::task::spawn_blocking(move || checksum(&buf))
                    .await
                    .context("checksum task failed")?;
                println!("checksum {sum}");
            }
        }
    }
}
```

An `unsafe` function written for edition 2024: the unsafe operation sits in its own block with a SAFETY comment, and the contract is documented.

```rust
/// Reads one `u32` through a raw pointer.
///
/// # Safety
/// `ptr` must be non-null, aligned and valid for reads of a `u32`.
pub unsafe fn read_u32(ptr: *const u32) -> u32 {
    // SAFETY: the caller upholds the contract documented above.
    unsafe { ptr.read() }
}
```

## 15. Common Mistakes

- **Cloning to silence the borrow checker**: hides a design problem and costs allocations. Restructure ownership, split the struct borrow, or shorten the borrow scope.
- **`&String` / `&Vec<T>` parameters**: forces callers to own that exact type. Take `&str` / `&[T]`.
- **`Rc<RefCell<T>>` everywhere**: turns compile errors into runtime panics (`already borrowed`). Prefer ownership trees, indices or message passing.
- **Holding a `MutexGuard` or `RefCell` borrow across `.await`**: the future is not `Send` or deadlocks. Scope the guard in a block, or use a message-passing task.
- **Blocking in async code** (`std::thread::sleep`, `std::fs`, heavy loops, sync HTTP clients): stalls the worker and other tasks. Use `tokio::time::sleep`, `tokio::fs`, or `spawn_blocking`.
- **`spawn_blocking` expecting abort**: a started blocking task cannot be aborted and delays runtime shutdown. Give long jobs their own cancellation flag or a dedicated thread.
- **Non-cancellation-safe futures in `select!`**: a dropped `read_exact`, `write_all` or similar future may lose data already consumed. Use cancellation-safe calls (`read`, `mpsc::recv`) or keep the future alive outside the loop; check the `select!` docs for the list.
- **Detached `tokio::spawn` with ignored `JoinHandle`**: panics and errors vanish. Keep a `JoinSet`, log results, and cancel on shutdown.
- **Unbounded channels and unlimited spawns**: memory grows under load. Use bounded channels and a `Semaphore`.
- **`anyhow` in a library's public API**: callers cannot match on errors. Use a `thiserror` enum, and keep `anyhow` in binaries.
- **Formatting the source into the message** (`format!("{e}")` in a new error): loses the chain. Use `#[source]` or `#[from]`.
- **`async fn` in a trait used as `dyn Trait`**: not dyn compatible; the error mentions the trait not being dyn compatible. Return a boxed future or use generics.
- **Edition 2021 habits under 2024**: `unsafe` operations inside `unsafe fn` without a block, `extern "C" {}` without `unsafe`, `#[no_mangle]` without `unsafe(...)`, `&STATIC_MUT`. Run `cargo fix --edition` and read the warnings.
- **`std::env::set_var` after threads started**: unsound, and `unsafe` in 2024. Set it at the start of `main` before spawning, or avoid it.
- **Forgetting tokio features**: `unresolved import tokio::net` or `no function named main` usually means `net` or `macros`/`rt-multi-thread` is not enabled.
- **Workspace members that do not inherit lints**: `[workspace.lints]` applies only to members that have `[lints] workspace = true`.
- **Relying on `cargo nextest` for everything**: doctests are skipped. Add `cargo test --doc`.
- **Unpinned or unaudited dependencies**: a yanked or vulnerable crate ships. Commit `Cargo.lock`, run `cargo deny check` and `cargo audit`.

## 16. References

- [references/ownership-lifetimes.md](references/ownership-lifetimes.md): moves, borrows, lifetime elision and annotations, borrowed structs, `Cow`, smart pointers, 2024 temporary and capture rules, how to read borrow errors.
- [references/async-tokio.md](references/async-tokio.md): runtime setup, tasks and `JoinSet`, channels, `select!` and cancellation safety, `CancellationToken`, graceful shutdown, `spawn_blocking`, async traits, async tests.
- [references/cargo-workspaces.md](references/cargo-workspaces.md): workspace manifests, inheritance, resolver 3 and MSRV, features, lints, clippy and rustfmt config, edition migration, `cargo audit`, `cargo deny`, nextest and Miri commands.
- [references/errors-traits-unsafe.md](references/errors-traits-unsafe.md): `thiserror` and `anyhow` patterns, error design, dyn versus impl, trait design, and rules for writing and reviewing `unsafe`.
- Official docs: https://doc.rust-lang.org/edition-guide/rust-2024/ , https://doc.rust-lang.org/cargo/ , https://doc.rust-lang.org/reference/ , https://doc.rust-lang.org/nomicon/ , https://rust-lang.github.io/rust-clippy/ , https://tokio.rs/tokio/tutorial , https://docs.rs/tokio , https://docs.rs/thiserror , https://docs.rs/anyhow , https://docs.rs/proptest , https://nexte.st , https://embarkstudios.github.io/cargo-deny/ , https://github.com/rust-lang/miri
