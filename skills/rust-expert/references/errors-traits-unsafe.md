# Errors, Traits and Unsafe

Designing error types with `thiserror` and `anyhow`, choosing between generics and trait objects, writing trait APIs, and rules for writing and reviewing `unsafe` code. Verified against Rust 1.99.1, thiserror 2.0.21 and anyhow 1.0.104 (2026-10).

## Contents

1. [Error design](#1-error-design)
2. [thiserror in libraries](#2-thiserror-in-libraries)
3. [anyhow in applications](#3-anyhow-in-applications)
4. [Generics, impl Trait and dyn Trait](#4-generics-impl-trait-and-dyn-trait)
5. [Trait design](#5-trait-design)
6. [Writing unsafe code](#6-writing-unsafe-code)
7. [Reviewing unsafe code](#7-reviewing-unsafe-code)

## 1. Error design

- A fallible function returns `Result<T, E>`. `?` returns early on `Err`, converting the error with `From::from`; in an `Option`-returning function `?` returns `None` early.
- A library error should say what failed and keep the cause: implement `std::error::Error` with `source()`, so callers and reporters can walk the chain.
- Variants are API. Group by what a caller can do (retry, fix input, give up), not by the line that failed. Mark public error enums `#[non_exhaustive]` so adding a variant is not a breaking change.
- Do not put secrets or entire request bodies in error messages; include identifiers and paths that help diagnosis.
- Display messages are lowercase fragments without a trailing period, because reporters chain them with `: `.
- `panic!`, `unwrap()` and `expect()` are for bugs and proven invariants. Input from users, files, networks and environment is never an invariant.
- Convert at layer boundaries: a storage error becomes a service error with `#[from]` or an explicit `map_err` that adds context.

## 2. thiserror in libraries

- `#[derive(thiserror::Error)]` generates `Display` from `#[error("...")]` and `Error::source` from `#[source]` or `#[from]` fields. thiserror 2.x is the current major version; check the docs when upgrading from 1.x.
- `#[from]` implements `From<Source>` and marks the field as the source; a variant with `#[from]` can hold only that field (plus an optional backtrace), so use `#[source]` plus `map_err` when context fields are needed.
- `#[error(transparent)]` forwards `Display` and `source` to the inner error, for wrapping an error without adding a message.
- Format arguments can refer to fields: `#[error("invalid port {value:?}")]`, or tuple fields as `{0}`.

```rust
use std::path::PathBuf;

#[derive(Debug, thiserror::Error)]
#[non_exhaustive]
pub enum StoreError {
    #[error("cannot read {path}")]
    Read {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("record {0} not found")]
    NotFound(String),
    #[error(transparent)]
    Parse(#[from] std::num::ParseIntError),
}

pub fn read_record(path: impl Into<PathBuf>) -> Result<String, StoreError> {
    let path = path.into();
    std::fs::read_to_string(&path).map_err(|source| StoreError::Read { path, source })
}
```

- Test the contract: `matches!(err, StoreError::NotFound(_))` and `std::error::Error::source(&err).is_some()`.

## 3. anyhow in applications

- `anyhow::Result<T>` is `Result<T, anyhow::Error>`, a boxed, `Send + Sync + 'static` dynamic error that any `std::error::Error` converts into via `?`. Use it in `main`, command handlers, test helpers and glue code.
- `.context("msg")` and `.with_context(|| format!(...))` (trait `anyhow::Context`) wrap an error with a message while keeping the cause. Use `with_context` when the message allocates.
- `bail!("msg")` returns an error; `ensure!(cond, "msg")` returns an error when the condition is false.
- Display modes: `{e}` prints only the outermost message; `{e:#}` prints the chain on one line separated by `: `; `{e:?}` prints the chain with a "Caused by" list (and a backtrace when enabled by `RUST_BACKTRACE`).
- `main` can return `anyhow::Result<()>`; a returned error is printed with `{:?}` and the process exits with status 1.
- Recover a concrete type with `err.downcast_ref::<StoreError>()` when a handler must branch; if that happens often in one place, the layer wants a typed error instead.
- `anyhow::Error` itself does not implement `std::error::Error`, so it cannot be a library's `#[source]`; wrap library errors with `thiserror`.

```rust
use anyhow::{Context, Result, bail, ensure};

fn load(id: u32) -> Result<String, StoreError> {
    if id == 0 {
        return Err(StoreError::NotFound(id.to_string()));
    }
    Ok(format!("record-{id}"))
}

fn run(id: u32) -> Result<()> {
    ensure!(id < 100, "id {id} out of range");
    let record = load(id).with_context(|| format!("loading record {id}"))?;
    if record.is_empty() {
        bail!("record {id} is empty");
    }
    println!("{record}");
    Ok(())
}
```

(`StoreError` is the enum from section 2.)

## 4. Generics, impl Trait and dyn Trait

| Choice | Dispatch | Use when | Cost |
|---|---|---|---|
| Generic `fn f<T: Tr>(x: T)` | Static, monomorphized | One concrete type per call site, hot paths, you need associated types or `Sized` | Code size and compile time grow per type |
| `impl Tr` in argument position | Static | Same as generic, shorter syntax; callers cannot name the type with turbofish | Same |
| `impl Tr` in return position | Static | Return one hidden concrete type (closures, iterators) | Cannot return two different types |
| `Box<dyn Tr>` / `&dyn Tr` | Dynamic (vtable) | Heterogeneous collections, plugin-like extension, reducing monomorphization | Indirection, allocation for `Box`, trait must be dyn compatible |
| `enum` of variants | Static match | Closed set of implementations | Adding a variant touches all matches |

- Dyn compatible traits have no generic methods (without `where Self: Sized`), do not use `Self` in arguments or return types other than the receiver, and have no native `async fn` methods. A trait that is not dyn compatible fails at `dyn Trait` with "the trait is not dyn compatible".
- Add `Send + Sync` to trait objects that cross threads: `Box<dyn Notifier + Send + Sync>`.
- Prefer generics in library APIs where the caller supplies the type and callers care about speed; use `dyn` at architecture boundaries (plugins, handlers stored in a map).
- Bounds belong in `where` clauses once they exceed one short bound. Use `impl Trait` arguments for simple one-off bounds.

```rust
trait Notifier {
    fn notify(&self, msg: &str);
}

struct Log;

impl Notifier for Log {
    fn notify(&self, msg: &str) {
        println!("{msg}");
    }
}

fn send_static(n: &impl Notifier, msg: &str) {
    n.notify(msg);
}

fn send_all(targets: &[Box<dyn Notifier + Send + Sync>], msg: &str) {
    for t in targets {
        t.notify(msg);
    }
}

fn main() {
    send_static(&Log, "static");
    send_all(&[Box::new(Log)], "dynamic");
}
```

## 5. Trait design

- Keep traits small and focused; combine with supertraits (`trait Repo: Send + Sync`). Provide default methods for convenience built on required ones.
- Associated types for "one output per implementor" (`Iterator::Item`); generic parameters when one type can implement the trait several ways (`From<T>`).
- Orphan rule: implement a foreign trait only for a local type, or a local trait for any type. Wrap foreign types in a newtype to get around it.
- Implement the std conversion traits (`From`, `TryFrom`, `FromStr`, `AsRef`, `Display`) instead of ad hoc `to_x` methods when they fit.
- A sealed trait (public trait with a supertrait from a private module) keeps the implementor set closed so methods can be added later.
- Async methods in traits: native `async fn` is stable (1.75); for spawning on a multi-thread runtime declare `-> impl Future<Output = T> + Send` in the trait; for `dyn` use boxed futures or the `async-trait` crate.
- Do not over-abstract: introduce a trait when there are two real implementations (for example production and a test double), not for a single type.

## 6. Writing unsafe code

- Unsafe Rust adds five abilities: dereference a raw pointer, call an `unsafe fn`, access or modify a `static mut`, implement an `unsafe trait`, and access union fields. Everything else the compiler still checks.
- Keep the unsafe core small and behind a safe API. The safe wrapper must make it impossible to violate the invariants from safe code.
- Every `unsafe` block gets a `// SAFETY:` comment that states why each precondition holds at that site, not what the code does. Every `unsafe fn` and `unsafe trait` gets a `# Safety` doc section listing what the caller or implementor must guarantee.
- In edition 2024 `unsafe_op_in_unsafe_fn` warns by default; deny it in the workspace lints and wrap each operation in an inner `unsafe {}` block.
- `extern` blocks are `unsafe extern`; mark an item `safe` only when any call from safe code is sound. Exported symbols use `#[unsafe(no_mangle)]`.
- Prefer safe alternatives first: `slice::get`, `split_at_mut`, `chunks`, `MaybeUninit` helpers, `bytemuck` or `zerocopy` for plain-data casts, `OnceLock` instead of `static mut`.
- Raw references to a `static mut`: use `&raw const` / `&raw mut` and read or write through the pointer, or avoid `static mut` entirely.
- Pointers: keep provenance and alignment; `ptr.read()` / `write()` require valid, aligned pointers, `read_unaligned` does not require alignment. Never create a `&T` or `&mut T` to uninitialized memory or to a location that is concurrently written.
- Do not let a panic cross an FFI boundary: unwinding out of an `extern "C"` function aborts the process. Catch it with `std::panic::catch_unwind` at the boundary, or use `extern "C-unwind"` only when the other side supports unwinding.
- `Send` / `Sync` impls (`unsafe impl Send for T {}`) need a SAFETY comment explaining why sharing or moving across threads is sound.

```rust
/// Returns the first byte, or `None` for an empty slice.
pub fn first_byte(data: &[u8]) -> Option<u8> {
    if data.is_empty() {
        return None;
    }
    // SAFETY: `data` is non-empty, so index 0 is in bounds.
    Some(unsafe { *data.get_unchecked(0) })
}
```

(In real code `data.first().copied()` is the right answer; the example shows the comment style.)

```rust
unsafe extern "C" {
    pub safe fn abs(x: i32) -> i32;
    pub unsafe fn strlen(p: *const std::ffi::c_char) -> usize;
}

pub fn c_len(s: &std::ffi::CStr) -> usize {
    // SAFETY: `CStr` guarantees a valid, NUL-terminated string.
    unsafe { strlen(s.as_ptr()) }
}
```

## 7. Reviewing unsafe code

- [ ] Can the unsafe block be removed with a safe API or a vetted crate?
- [ ] The block is as small as possible, with a SAFETY comment that argues each precondition (non-null, aligned, initialized, in bounds, lifetime, aliasing, thread safety).
- [ ] The safe wrapper cannot be misused from safe code to reach undefined behavior (check public fields, `Clone`, `Drop` and panics in the middle of the invariant).
- [ ] `unsafe fn` and `unsafe trait` have `# Safety` docs; `unsafe impl Send/Sync` is justified.
- [ ] Integer overflow, casts and length arithmetic that feed the unsafe operation use checked operations.
- [ ] Tests exercise the unsafe path, including edge sizes (empty, one element, maximum); the suite runs under Miri (`cargo +nightly miri test`).
- [ ] FFI: signatures match the C declarations, ownership of every pointer is documented, strings are NUL-terminated, panics do not unwind across the boundary.
- [ ] `#![forbid(unsafe_code)]` is present in every crate that does not need unsafe.
