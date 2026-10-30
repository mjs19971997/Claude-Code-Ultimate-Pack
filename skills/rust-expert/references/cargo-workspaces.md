# Cargo Workspaces, Lints, Auditing and Tooling

Workspace manifests and inheritance, resolver 3 and MSRV, features, lint configuration, clippy and rustfmt, edition migration, dependency auditing and the test tool commands. Verified against Rust 1.99.1, Cargo 0.100, cargo-nextest 0.9.150, cargo-deny 0.20.2, cargo-audit 0.22.2 (2026-10).

## Contents

1. [Workspace manifest](#1-workspace-manifest)
2. [Member manifests and inheritance](#2-member-manifests-and-inheritance)
3. [Resolver 3 and MSRV](#3-resolver-3-and-msrv)
4. [Features](#4-features)
5. [Lints, clippy and rustfmt](#5-lints-clippy-and-rustfmt)
6. [Migrating to edition 2024](#6-migrating-to-edition-2024)
7. [Auditing dependencies](#7-auditing-dependencies)
8. [Test and verification commands](#8-test-and-verification-commands)
9. [CI sequence](#9-ci-sequence)

## 1. Workspace manifest

- A workspace is a set of packages sharing one `Cargo.lock` and one `target` directory. The root `Cargo.toml` has a `[workspace]` table; it may also be a package (root package) or "virtual" (no `[package]`).
- `members` accepts globs (`crates/*`); `exclude` removes paths; `default-members` limits what plain `cargo build` and `cargo run` act on.
- A virtual workspace has no edition to imply a resolver, so set `resolver = "3"` explicitly.
- Inheritable tables: `[workspace.package]` (version, edition, rust-version, license, repository, authors, publish and similar), `[workspace.dependencies]`, `[workspace.lints]`.
- Select packages on the command line with `-p name`, `--workspace`, `--exclude name`.

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

[profile.release]
lto = "thin"
codegen-units = 1
```

- Profiles (`[profile.*]`) are valid only in the workspace root; a profile in a member is ignored with a warning.

## 2. Member manifests and inheritance

```toml
[package]
name = "app"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
license.workspace = true
publish.workspace = true

[dependencies]
core-lib.workspace = true
anyhow.workspace = true
tokio = { workspace = true, features = ["rt-multi-thread", "macros", "signal", "time", "sync", "net"] }
tokio-util.workspace = true

[dev-dependencies]
proptest.workspace = true

[lints]
workspace = true
```

- `dep.workspace = true` takes version, source and default features from the workspace entry; a member may add `features = [...]` on top and `optional = true`.
- Put `default-features = false` on the workspace entry when members should opt in to features. Since Rust 1.99, a 2024 edition member can also set `default-features` on an inherited dependency and it overrides the workspace value; on 1.85 to 1.98 a member that disagrees with the workspace entry is an error, and in editions before 2024 the member setting is ignored.
- `[lints] workspace = true` is required in each member; it cannot be combined with other keys in the same `[lints]` table (add per-crate exceptions with `#[expect]` or `#![allow]` in code).
- Path dependencies that are published need a `version` as well: `core-lib = { path = "crates/core", version = "0.1.0" }`.
- `cargo tree -d` lists duplicated crate versions; `cargo tree -i <crate>` shows who depends on a crate; `cargo tree -e features` shows feature origins.

## 3. Resolver 3 and MSRV

- Resolver "2" avoids unifying features across platforms, build scripts and proc macros, and dev-dependencies; resolver "3" keeps that and also considers `package.rust-version` when choosing dependency versions (the `fallback` behavior), preferring versions whose declared MSRV is compatible with yours.
- `edition = "2024"` in a package implies `resolver = "3"`; a virtual workspace must say so in `[workspace]`.
- `rust-version = "1.85"` is also a hard check: Cargo refuses to build with an older compiler (override with `--ignore-rust-version`). Edition 2024 itself needs 1.85 or later.
- The resolver preference applies when Cargo picks versions (`cargo update`, `cargo add`, a fresh lockfile); an existing `Cargo.lock` entry is kept. It is a preference, not a guarantee; verify the MSRV in CI.
- MSRV check in CI: install the toolchain named in `rust-version` and run `cargo check --workspace --locked` with it (for example through `rustup toolchain install 1.85` and `cargo +1.85 check`).
- Pin the developer and CI toolchain separately from MSRV with `rust-toolchain.toml`:

```toml
[toolchain]
channel = "stable"
components = ["clippy", "rustfmt"]
```

- Use a specific version (for example `channel = "1.99.1"`) when builds must be reproducible, and update it in a reviewed change.

## 4. Features

- Features are additive: enabling a feature must never remove an item or change behavior incompatibly, because Cargo unifies features across the dependency graph.
- Keep `default` small. Heavy or optional integrations go behind features: `serde = ["dep:serde"]` hides the implicit feature name of an optional dependency.
- Document each feature in the crate docs and test the combinations that matter: `--no-default-features`, `--all-features`, and each feature alone for libraries.
- For tokio and similar crates in a library, depend with `default-features = false` and enable only what the code needs; the binary adds the rest.
- `cargo hack --each-feature` (the cargo-hack tool) checks feature combinations if the project installs it.

## 5. Lints, clippy and rustfmt

- Central lint policy in `[workspace.lints]` (see section 1). Levels are `allow`, `warn`, `deny`, `forbid`. Use `priority` when a group and a single lint conflict:

```toml
[workspace.lints.clippy]
pedantic = { level = "warn", priority = -1 }
module_name_repetitions = "allow"
```

- CI command: `cargo clippy --workspace --all-targets --all-features -- -D warnings`. `--all-targets` includes tests, examples and benches.
- Lint groups: `clippy::all` (default set), `pedantic`, `restriction` (cherry-pick, never enable wholesale), `nursery`, `cargo` (manifest checks).
- Prefer `#[expect(lint, reason = "...")]` over `#[allow]`; `expect` warns when the suppression is no longer needed.
- Useful lints for production code: `clippy::unwrap_used` and `clippy::expect_used` (library code), `clippy::undocumented_unsafe_blocks`, `clippy::await_holding_lock`, `clippy::dbg_macro`, `clippy::todo`.
- `clippy.toml` holds lint settings such as `msrv`; see the clippy configuration book for the options of the installed version.
- rustfmt: `cargo fmt --all --check` in CI. Put options in `rustfmt.toml`. `style_edition` is inferred from `edition` when run via `cargo fmt`, but plain `rustfmt` defaults to 2015, so set it explicitly:

```toml
style_edition = "2024"
```

- `cargo clippy --fix` and `cargo fix` apply suggestions; review the diff, since some fixes are not behavior preserving.

## 6. Migrating to edition 2024

1. Update the toolchain to 1.85 or later and make sure the tree builds and tests pass on the old edition.
2. Run `cargo fix --edition` per package (add `--workspace` for the whole workspace). It applies the `rust-2024-compatibility` lints: `gen` becomes `r#gen`, `unsafe extern`, `#[unsafe(no_mangle)]`, RPIT `use<..>` bounds where captures would change, tail-expression and `if let` temporary changes, and similar.
3. Change `edition = "2021"` to `edition = "2024"` (or `edition.workspace = true` with the workspace value), set `rust-version = "1.85"` or higher, and for a virtual workspace set `resolver = "3"`.
4. Fix what the tool cannot: `unsafe_op_in_unsafe_fn` warnings (add inner `unsafe {}` blocks with SAFETY comments), `static_mut_refs` errors (switch to atomics, `Mutex` or `OnceLock`), calls to `std::env::set_var`/`remove_var` (now `unsafe`), and Cargo key spellings (`dev_dependencies` to `dev-dependencies`, `default_features` to `default-features`, `[project]` to `[package]`).
5. Run `cargo fmt` (style edition changes reformat code; commit that separately), `cargo clippy` and `cargo test --workspace --doc`. Doctests are combined in 2024; tag an example `standalone_crate` if it cannot be combined.
6. Check macros: in 2024 the `expr` fragment specifier also matches `const {}` blocks and `_`; a macro that relied on the old behavior can use `expr_2021`.

## 7. Auditing dependencies

- `cargo audit` checks `Cargo.lock` against the RustSec advisory database. It requires Rust 1.74 or later. Run it at the workspace root; if `Cargo.lock` is missing it generates one, which runs Cargo on the project, so for an untrusted project pass the lockfile: `cargo audit --file path/to/Cargo.lock`.
- `cargo deny` (cargo-deny) runs four checks: `advisories`, `licenses`, `bans` (denied crates, duplicate versions) and `sources` (allowed registries and git repositories). Create a starting config with `cargo deny init`, then `cargo deny check`; run one check with `cargo deny check licenses`.
- Install with `cargo install --locked cargo-deny` and `cargo install cargo-audit --locked`, or use the project's CI action; pin versions in CI.
- A minimal `deny.toml` shape (keys vary by cargo-deny version, so start from `cargo deny init` output and check the cargo-deny book):

```toml
[advisories]
# defaults from `cargo deny init`; add reviewed, dated ignores with a reason

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unicode-3.0"]

[bans]
multiple-versions = "warn"

[sources]
unknown-registry = "deny"
unknown-git = "deny"
```

- Treat an ignored advisory as debt: record the id, reason and a review date next to it.
- `cargo update -p <crate>` moves one dependency; `cargo update --dry-run` previews; `cargo outdated` and `cargo upgrade` (cargo-edit) are optional helpers.
- Review build scripts and proc macros of new dependencies: they run arbitrary code at build time.

## 8. Test and verification commands

| Goal | Command |
|---|---|
| Fast type check | `cargo check --workspace --all-targets` |
| Unit and integration tests | `cargo test --workspace` |
| Doctests only | `cargo test --workspace --doc` |
| One test | `cargo test -p core-lib parse_port -- --nocapture` |
| nextest (parallel, per-test process) | `cargo nextest run --workspace` |
| Miri (nightly component) | `rustup +nightly component add miri` then `cargo +nightly miri test` |
| Coverage | `cargo llvm-cov --workspace` (cargo-llvm-cov) |
| Docs with warnings as errors | `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps` |
| Locked build | `cargo build --release --locked` |
| Dry-run publish | `cargo publish --dry-run -p core-lib` |

- cargo-nextest does not run doctests; keep `cargo test --doc` as its own step.
- Miri interprets the test suite and reports undefined behavior it observes; it is slow, does not support all FFI and I/O, and finds only what the executed tests exercise. Use `#[cfg(miri)]` to shrink test sizes.
- proptest writes failing cases to `proptest-regressions/`; commit those files so the case is replayed.

## 9. CI sequence

1. `cargo fmt --all --check`
2. `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`
3. `cargo test --workspace --locked` (or `cargo nextest run --workspace --locked`) followed by `cargo test --workspace --doc --locked`
4. `cargo deny check` (and `cargo audit` on a schedule, since new advisories appear without code changes)
5. MSRV job: `cargo +<rust-version> check --workspace --locked`
6. Optional nightly job: `cargo +nightly miri test` for crates with unsafe code

CI pipeline structure itself (caching, matrices, permissions) is covered by cicd-expert.
