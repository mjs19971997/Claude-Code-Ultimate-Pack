---
name: cpp-expert
description: >-
  Writes, reviews and builds modern C++20 and C++23: RAII and the rule of zero, move semantics, std::expected, ranges, concepts, std::format, jthread, CMake presets, sanitizers, clang-tidy and GoogleTest or Catch2. Use when editing .cpp, .hpp, CMakeLists.txt, CMakePresets.json, .clang-tidy or vcpkg.json, running g++, clang++, cmake, ctest, clang-tidy or perf, or fixing dangling references, data races, undefined behaviour and link errors. Not for Rust (use rust-expert), ns-3 simulations (use ns3-expert), OS administration (use linux-expert), CI pipelines (use cicd-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# C++ Expert

This skill covers everyday and production C++ on the C++20 and C++23 standards: ownership and value semantics, error handling, the ranges and concepts libraries, formatting, concurrency, the CMake build with presets, package managers, warnings, sanitizers, static analysis, hardening, testing and benchmarking. It favours the standard library and a target-based build. Rust, network simulators, operating system administration and CI pipeline design belong to other skills.

> Verified against GCC 16.1 (released 30 April 2026) and the local g++ 13.3 and clang++ 18.1, LLVM 23.1.4 (latest on GitHub), CMake 4.4.4 (4.4.5 latest), vcpkg 2026.10.16, Conan 2.x, GoogleTest 1.18.0, Catch2 3.16.1 and Google Benchmark 1.10.0 (2026-10).

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

- Covered: C++20 and C++23 language and library, RAII, smart pointers, `std::span`, `std::string_view`, ranges, concepts, `constexpr` and `consteval`, `std::expected` and `std::optional`, `std::format` and `std::print`, modules (status only), coroutines (briefly), `std::jthread`, atomics, undefined behaviour classes, CMake and presets, `FetchContent`, vcpkg and Conan 2 (briefly), sanitizers, warnings, clang-tidy, clang-format, hardening flags, GoogleTest, Catch2, libFuzzer (briefly), Google Benchmark and perf.
- Not covered: Rust (rust-expert); ns-3 simulator code (ns3-expert); Linux system administration (linux-expert); CI pipeline structure (cicd-expert); container images (docker-expert); cross-language test strategy (unit-testing-expert); secure coding across languages (secure-coding-expert); GPU and numerical libraries.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Compilers | GCC 16.1 (30 April 2026) defaults to GNU C++20 and lists C++26 reflection (`-freflection`), contracts and `std::simd` as experimental. LLVM 23.1.4 is the latest release on GitHub. The Clang status page rates C++23 as partial and C++26 reflection and contracts as not implemented. MSVC ships with Visual Studio 2026 (check the Microsoft conformance page) |
| Standard flags | Pass `-std=c++23` (or `/std:c++latest` on MSVC) explicitly; do not rely on the compiler default. In CMake use `target_compile_features(t PUBLIC cxx_std_23)` |
| Library support | libstdc++ first versions: `std::expected` 12.1, `std::print` and `ranges::to` 14.1, `flat_map` and `import std` 15.1. Check feature-test macros (`__cpp_lib_print`) in the target toolchain. Table in [references/modern-language.md](references/modern-language.md) |
| Ownership | Rule of zero by default; `std::unique_ptr` for single owner, `std::shared_ptr` for shared lifetime, `std::weak_ptr` for back references; no owning raw pointers |
| Views | `std::string_view`, `std::span` and ranges views do not own data; most dangling defects are a view outliving its source |
| Errors | `std::expected<T, E>` (C++23) for recoverable failures with a reason, `std::optional<T>` for absence, exceptions for rare failures and constructors |
| Generic code | Concepts and `requires` clauses replace SFINAE; `consteval` forces compile-time evaluation; `constinit` fixes static initialisation order |
| Concurrency | `std::jthread` joins on destruction and carries a `std::stop_token`; `std::scoped_lock`; `std::atomic` defaults to sequential consistency; a data race is undefined behaviour |
| Modules | `import std;` is a C++23 feature; libstdc++ lists it from GCC 15.1. CMake 4.4 documentation still gates `import std` behind an experimental setting. Treat as optional and verify per toolchain |
| CMake | 4.4.5 latest stable seen, 4.5 at release candidate. Preset schema 6 needs CMake 3.25, schema 12 needs 4.4, schema 13 needs 4.5 |
| Dependencies | `find_package` for system, vcpkg or Conan packages; `FetchContent` for small pinned source dependencies; vcpkg manifest mode uses `vcpkg.json` with a `builtin-baseline` |
| Sanitizers | ASan + UBSan together; TSan alone; MSan is Clang-only and needs an instrumented standard library. `-fsanitize=address,thread` is rejected by GCC |
| Tests | GoogleTest 1.18.0 requires C++17; Catch2 3.16.1 is a compiled library; Google Benchmark 1.10.0 for micro-benchmarks |

## 3. Workflow

1. Read `CMakeLists.txt`, `CMakePresets.json`, `.clang-tidy`, `.clang-format`, the package manifest (`vcpkg.json`, `conanfile.*`) and CI configuration. Identify the compilers, standard library and C++ standard in use before suggesting anything.
2. Reproduce with the project's own preset: `cmake --preset dev && cmake --build --preset dev && ctest --preset dev`. For a crash or wrong output, reproduce under `-fsanitize=address,undefined` first.
3. Keep to the project's toolchain, standard level and style. Do not raise the standard, add a dependency or change the build system without a reason.
4. Make the smallest change that fixes the cause. Prefer ownership types and standard algorithms over manual loops and raw `new`/`delete`.
5. Add a test that fails without the change. Run the sanitizer preset and, for concurrent code, a TSan build.
6. Run, in order: `clang-format`, build with warnings as errors, `clang-tidy`, tests, sanitizers. Report which commands ran and their results.
7. When a feature depends on library version (`std::print`, `ranges::to`, `import std`), check the feature-test macro or the compiler matrix before using it, and give a fallback.
8. For performance work, measure first (benchmark in Release, `perf`), change one thing, measure again.

## 4. Decision Rules

- If a type owns a resource, build it from owning members and declare no special members (rule of zero); if it wraps a raw handle, write a small RAII class with all five special members defined or deleted.
- If ownership is unique, use `std::unique_ptr`; if there is genuinely shared lifetime, use `std::shared_ptr` with `make_shared`; if a function only uses an object, take `T&`, `const T&` or `T*`.
- If a function reads a string and keeps nothing, take `std::string_view`; if it stores the string, take `std::string` by value and move it in. Never return a view into a local or a temporary.
- If a function needs a contiguous sequence, take `std::span<T>` / `std::span<const T>`.
- If a failure is expected and the caller must react to its cause, return `std::expected<T, E>`; if absence is the only failure, return `std::optional<T>`; if failure is exceptional or arises in a constructor, throw.
- If the project forbids exceptions (`-fno-exceptions`), use `std::expected` and `[[nodiscard]]` throughout and avoid standard facilities that throw.
- If a template parameter must satisfy an interface, constrain it with a concept; if a standard concept exists, use it.
- If a computation can run at build time and is on the critical path of start-up or table generation, use `constexpr` or `consteval`; otherwise keep it plain.
- If a feature needs a newer library than the oldest supported toolchain (`std::print`, `ranges::to`, `std::flat_map`), either raise the toolchain floor or guard with `__has_include` / feature-test macros and use `std::format` or a loop as fallback.
- If a thread must be cancellable, use `std::jthread` with `std::stop_token`; if two threads touch the same object, guard it with a mutex or make it `std::atomic`.
- If a dependency is small, header-only or CMake-native and pinned to a release, `FetchContent` is acceptable; for large or system libraries use vcpkg, Conan or `find_package`.
- If you need to choose a package manager, use what the project already uses; vcpkg manifest mode and Conan 2 should not be mixed in one build.
- If a sanitizer is needed: ASan + UBSan for memory and UB, TSan for races (separate binary), MSan only with an instrumented Clang toolchain.
- If `import std;` is considered, check compiler, standard library, CMake version and generator support first; keep `#include` as the default.

## 5. Coding Standards

- Format with `clang-format` using the checked-in `.clang-format`; do not hand-align. Naming follows the project; if none, `snake_case` for functions and variables, `PascalCase` for types, `kConstant` or `UPPER_CASE` for constants, `member_` for private data.
- Headers use `#pragma once` or include guards, include what they use, and avoid `using namespace` at any scope in headers. Order includes: own header, project, third party, standard library.
- Mark single-argument constructors `explicit`, overrides `override`, non-throwing moves `noexcept`, and return values that must be checked `[[nodiscard]]`.
- Use `const` and `constexpr` wherever possible; initialise at declaration with braces; prefer `auto` when the type is obvious from the right side, spell the type when it documents intent.
- Use `enum class`, `std::array`, `std::string`, `std::vector`; avoid C arrays, `malloc` and `free`, C-style casts, `NULL`, and macros for constants or functions.
- Pass cheap types (arithmetic, `string_view`, `span`) by value, other read-only parameters by `const T&`, sinks by value then `std::move`. Return by value; do not `return std::move(local)`.
- Prefer algorithms and ranges over index loops; use `at()` or checked access at trust boundaries, not unchecked `operator[]` on untrusted indices.
- Exceptions: throw by value, catch by `const&`, never throw from destructors, and use RAII instead of `try`/`catch` cleanup.
- Do not use `reinterpret_cast`, `const_cast` or `volatile` for synchronisation without a documented reason; use `std::bit_cast` for type punning.
- Comments state intent or invariants; do not restate the code.

## 6. Project Structure

```text
acme/
  CMakeLists.txt          # targets, options, install rules
  CMakePresets.json       # dev, asan, tsan, release presets
  vcpkg.json              # or conanfile.txt
  .clang-format
  .clang-tidy
  include/acme/           # public headers (installed)
  src/                    # implementation and private headers
  tests/                  # GoogleTest or Catch2 files
  bench/                  # Google Benchmark files
  fuzz/                   # libFuzzer targets
  cmake/                  # package config template, helper modules
```

- One target per library or executable; public headers under `include/<project>/`, so includes read `#include "acme/parse.hpp"`.
- Keep warnings and sanitizer options in an INTERFACE target, not in global `CMAKE_CXX_FLAGS`. Details and a complete tested CMakeLists.txt: [references/cmake.md](references/cmake.md).
- Commit `CMakePresets.json`; ignore `CMakeUserPresets.json` and `build/`.

## 7. Design Patterns

- **RAII wrappers**: every acquire has an owning object whose destructor releases (files, locks, handles, transactions). Cost: none at run time; the wrapper must be move-only if the resource is unique.
- **Value semantics**: pass and return objects by value, make types regular (copyable, comparable) and avoid hidden sharing. Cost: copies of large objects; use move or views where measured.
- **Pimpl**: hide implementation behind a `std::unique_ptr<Impl>` declared in the header and defined in the `.cpp` (define the destructor there). Cost: one allocation and indirection; benefit: stable ABI and faster builds.
- **Type erasure with `std::function` / `std::move_only_function`** or a small virtual interface for runtime polymorphism; templates and concepts for compile-time polymorphism. Cost: indirect calls versus larger binaries and slower builds.
- **Strong types**: wrap integers in small structs or enum classes (`UserId`, `Meters`) so arguments cannot be swapped. Cost: boilerplate; zero run-time cost.
- **Error pipelines**: chain `std::expected` with `and_then` / `transform`, and convert at module boundaries. Cost: error types must be designed; benefit: explicit control flow.
- **Dependency injection by constructor**: pass clocks, filesystems and clients as interfaces or callables so tests substitute them.
- **Visitor with `std::variant`**: `std::visit` with an overloaded lambda set for closed type sets; compile-time exhaustiveness replaces `dynamic_cast` chains.
- **Cancellation with stop tokens**: long-running loops poll `stop_token`; owners are `std::jthread`.

## 8. Best Practices

- Enable the strictest warning set the code base can pass and keep it at zero warnings; treat third-party headers as `SYSTEM`.
- Run sanitizer and clang-tidy jobs in CI, not only locally. Fix the report; do not suppress it without a comment.
- Prefer composition and free functions over deep inheritance; make destructors of polymorphic bases virtual or protected.
- Keep headers light: forward-declare where possible, move implementations into `.cpp` files, avoid heavy includes in public headers.
- Use `std::string_view` and `std::span` only at function boundaries, not as stored members.
- Use `std::chrono` types (`std::chrono::milliseconds`) in interfaces rather than naked integers.
- Use `std::filesystem::path` for paths, `std::from_chars` for number parsing, `<random>` instead of `rand()`.
- Avoid global mutable state and static initialisation that depends on other translation units; use function-local statics or `constinit`.
- Keep each feature guarded by the macro that reports it, so a toolchain upgrade enables it without edits.
- Pin dependency versions (tags, commits, `builtin-baseline`, lockfiles) so a build is reproducible.

## 9. Performance

- Measure before changing: `perf record -g`, `perf stat`, and Google Benchmark in a Release build with the production flags. Details: [references/testing-and-benchmarking.md](references/testing-and-benchmarking.md).
- Choose data structures first: contiguous `std::vector` beats node-based containers for most workloads; `reserve` when the size is known; `std::flat_map` (where available) or sorted vectors for small read-mostly maps; `std::unordered_map` for large hash lookups.
- Avoid allocation in hot loops: reuse buffers, use `std::string_view`, small-buffer types, and `std::pmr` allocators for arena-like patterns.
- Avoid copies: pass by reference, move sinks, `emplace_back`, return by value (elision), `std::span` for slices. Check `performance-*` clang-tidy checks.
- Mind cache behaviour: struct-of-arrays for scans over one field, predictable access order, no pointer chasing in inner loops.
- Use `-O2` for general release builds; `-O3`, `-march=native` (not portable), LTO (`INTERPROCEDURAL_OPTIMIZATION`) and profile-guided optimisation only after measuring on the target hardware.
- `std::shared_ptr` copies and `std::function` calls have a cost; do not use them for plain ownership or for hot callbacks where a template parameter works.
- Use `std::atomic` with the default ordering until a profile shows contention; weaker memory orders need a written justification and TSan plus stress tests.
- Compile time is a cost too: prefer forward declarations, precompiled headers (`target_precompile_headers`) and fewer template instantiations; measure with `-ftime-report`.

## 10. Security

- Memory safety defects are the main risk. Use containers, spans and smart pointers; keep bounds checks on at trust boundaries (`at()`, `std::span` size checks); fuzz parsers with libFuzzer under ASan and UBSan.
- Treat all external input (files, network, command line, environment) as untrusted: validate lengths before indexing, check integer overflow before arithmetic (`__builtin_add_overflow` or a checked wrapper), and use `std::from_chars` with error checks.
- Never pass untrusted text as a format string (`printf(user)`, `std::vformat(user, ...)`). Use `std::format("{}", user)`.
- Do not build shell commands from input (`system()`, `popen`); use `execve`-style APIs with an argument vector and drop privileges.
- Build hardened: `-D_FORTIFY_SOURCE=3` (with optimisation), `-D_GLIBCXX_ASSERTIONS`, `-fstack-protector-strong`, `-fstack-clash-protection`, `-fcf-protection=full` (x86), `-fPIE -pie`, `-Wl,-z,relro,-z,now`. This set compiled and ran with g++ 13.3; see [references/sanitizers-and-tooling.md](references/sanitizers-and-tooling.md).
- Use `memcpy`/`std::bit_cast` for type punning; use `std::span` and `std::array` rather than `memcpy` on arbitrary sizes; clear secrets with a function the compiler cannot remove (`explicit_bzero` or `memset_s` where available).
- Keep secrets out of source and out of `compile_commands.json`; read them from the environment or a secret store. Do not log them.
- Pin and review dependencies; verify downloads with `URL_HASH` or a Git commit; do not run `curl | sh` for toolchain setup; run `vcpkg` or Conan from reviewed sources.
- Random numbers for security come from the operating system (`getrandom`, `BCryptGenRandom`) or a vetted crypto library, not `std::mt19937` or `rand()`.
- Use sanitizers and fuzzers in CI on every parser, decoder and deserialiser.

## 11. Testing

- Use the framework already in the project; for a new one see [references/testing-and-benchmarking.md](references/testing-and-benchmarking.md). Register tests with CTest and run through presets.
- GoogleTest: `ASSERT_*` before dereferencing, `EXPECT_*` for further checks, `TEST_P` for tables, `--gtest_repeat` and `--gtest_shuffle` to find flakiness. Catch2 v3: `TEST_CASE` with `SECTION`, `GENERATE`, matchers.
- Test the failure path of every `std::expected` function, boundary sizes, empty inputs and embedded NUL characters.
- Run the full suite under ASan + UBSan on every change, and concurrent tests under TSan; keep these as separate CI jobs.
- Fuzz parsers: a `LLVMFuzzerTestOneInput` target built with `-fsanitize=fuzzer,address,undefined` and a saved corpus as regression input.
- Inject time, randomness and I/O; do not sleep to synchronise.
- Measure coverage with `--coverage` and `gcovr` or with `llvm-cov`; use it to find gaps.
- Benchmarks live in `bench/`, run only on demand or in a dedicated job, and compare relative results on the same machine.

## 12. Review Checklist

- [ ] The code builds with the project's presets and `-Wall -Wextra -Wpedantic` is clean (and `-Werror` in CI).
- [ ] No owning raw pointers, `new`/`delete`, `malloc`/`free` or C arrays where a standard type fits.
- [ ] Special member functions follow the rule of zero (or all five are defined or deleted); moves are `noexcept`.
- [ ] No `string_view`, `span`, iterator or reference outlives its source; no view stored as a member without justification.
- [ ] Failures are reported through `std::expected`, `std::optional` or exceptions consistently; results are `[[nodiscard]]`.
- [ ] No data race: shared state is guarded or atomic; threads are `std::jthread`; TSan run is clean.
- [ ] No signed overflow, out-of-range shift, unchecked index or division by an unchecked value; UBSan run is clean.
- [ ] Features tied to library versions (`std::print`, `ranges::to`, `import std`) are guarded or the toolchain floor is documented.
- [ ] CMake uses targets (`target_*` commands with PUBLIC / PRIVATE / INTERFACE); no `include_directories`, `file(GLOB)` for sources or global flags.
- [ ] Dependencies are pinned (tag/commit/baseline/lockfile) and verified; no secrets in source.
- [ ] New behaviour has tests including error paths; sanitizer and clang-tidy jobs pass.
- [ ] Performance claims are backed by a Release-build measurement.

## 13. Production Notes

- Release builds: `-O2 -DNDEBUG` plus the hardening flags in section 10, separate debug symbols (`-g`, then `objcopy --only-keep-debug` or `strip`), and a reproducible compiler and library version recorded in the build.
- Provide `RelWithDebInfo` builds for profiling and crash analysis; keep symbol files for core dumps (`coredumpctl` or `gdb` with the matching binary).
- Install and export CMake targets (`install(EXPORT ...)`, `write_basic_package_version_file`) so consumers use `find_package`; see [references/cmake.md](references/cmake.md).
- ABI: libstdc++ dual ABI (`_GLIBCXX_USE_CXX11_ABI`), mixing libstdc++ and libc++ and mixing debug and release runtimes on MSVC produce link or run-time failures; build all components with one toolchain configuration.
- Shared libraries: hide symbols by default (`CXX_VISIBILITY_PRESET hidden`), export a small API, avoid exposing standard library types across a DLL boundary if the consumer toolchain can differ.
- Plan toolchain upgrades: build with the next compiler in a CI job early (GCC 16 changed the default dialect to C++20 for code that omitted `-std`), and read each release's incompatibility list.
- C++26 items (reflection, contracts) are experimental in GCC 16.1 and not implemented in Clang per its status page; do not use them in production code.
- Check the compiler vendor documentation for support dates; free compilers are updated yearly, so choose a floor that your distributions package.
- Graceful shutdown: signal handlers set a `std::atomic<bool>` or call `request_stop()` on a stop source (only async-signal-safe operations in the handler), and the main thread joins workers.

## 14. Examples

Error handling with `std::expected`, `std::from_chars` and `std::format` (compiled with g++ 13.3, `-std=c++23 -Wall -Wextra -Wpedantic`):

```cpp
#include <charconv>
#include <cstdio>
#include <expected>
#include <format>
#include <string_view>
#include <system_error>

enum class ParseError { Empty, NotANumber, OutOfRange };

constexpr std::string_view to_string(ParseError e) noexcept {
    switch (e) {
        case ParseError::Empty: return "empty";
        case ParseError::NotANumber: return "not a number";
        case ParseError::OutOfRange: return "out of range";
    }
    return "unknown";
}

std::expected<int, ParseError> parse_int(std::string_view s) {
    if (s.empty()) return std::unexpected(ParseError::Empty);
    int value{};
    auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), value);
    if (ec == std::errc::result_out_of_range) return std::unexpected(ParseError::OutOfRange);
    if (ec != std::errc{} || ptr != s.data() + s.size()) return std::unexpected(ParseError::NotANumber);
    return value;
}

int main() {
    for (std::string_view in : {"21", "", "4x", "99999999999"}) {
        if (auto r = parse_int(in).transform([](int v) { return v * 2; }))
            std::puts(std::format("{} -> {}", in, *r).c_str());
        else
            std::puts(std::format("{} -> error: {}", in, to_string(r.error())).c_str());
    }
}
```

Cooperative cancellation with `std::jthread` (compiled and run with g++ 13.3):

```cpp
#include <atomic>
#include <chrono>
#include <cstdio>
#include <stop_token>
#include <thread>

int main() {
    std::atomic<long> ticks{0};
    {
        std::jthread worker([&](std::stop_token st) {
            while (!st.stop_requested()) {
                ticks.fetch_add(1, std::memory_order_relaxed);
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
        });
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }  // the jthread requests stop and joins here
    std::printf("ticks>0: %d\n", ticks.load() > 0);
}
```

Concepts, ranges and `std::span` (compiled with g++ 13.3):

```cpp
#include <concepts>
#include <cstdio>
#include <ranges>
#include <span>
#include <vector>

template <std::integral T>
constexpr T square(T x) { return x * x; }

template <typename R>
concept IntRange = std::ranges::input_range<R> && std::integral<std::ranges::range_value_t<R>>;

long sum_of_even_squares(IntRange auto&& r) {
    long total = 0;
    for (auto v : r | std::views::filter([](auto x) { return x % 2 == 0; })
                    | std::views::transform([](auto x) { return square(static_cast<long>(x)); }))
        total += v;
    return total;
}

void scale(std::span<double> xs, double k) { for (double& x : xs) x *= k; }

int main() {
    std::vector v{1, 2, 3, 4, 5, 6};
    std::vector<double> d{1, 2, 3};
    scale(d, 2.0);
    std::printf("%ld %g\n", sum_of_even_squares(v), d[2]);   // 56 6
}
```

Sanitizer and hardened builds (commands tested with g++ 13.3 on Linux):

```bash
g++ -std=c++23 -g -fsanitize=address,undefined -fno-omit-frame-pointer app.cpp -o app_asan
g++ -std=c++23 -g -fsanitize=thread app.cpp -o app_tsan -pthread
g++ -std=c++23 -O2 -D_FORTIFY_SOURCE=3 -D_GLIBCXX_ASSERTIONS -fstack-protector-strong \
    -fstack-clash-protection -fcf-protection=full -fPIE -pie -Wl,-z,relro,-z,now app.cpp -o app
```

Preset workflow (CMake 4.4.4; the full CMakeLists.txt and CMakePresets.json are in [references/cmake.md](references/cmake.md)):

```bash
cmake --preset asan && cmake --build --preset asan && ctest --preset asan
```

## 15. Common Mistakes

- **Dangling `string_view`**: `std::string_view sv = make_string();` points into a destroyed temporary. Keep the `std::string` alive or store a `std::string`.
- **Iterator or pointer invalidation**: `push_back` can reallocate a `vector`; a pointer taken before is dangling (ASan reports heap-use-after-free). Re-fetch after mutation or use indices.
- **`return std::move(local)`**: blocks copy elision and triggers a warning. Return the local by name.
- **Throwing move operations**: `vector` then copies on growth. Mark moves `noexcept`.
- **Raw `new`/`delete` or owning raw pointers**: leaks on exception paths. Use `make_unique` and containers.
- **`shared_ptr` everywhere**: hidden ownership, atomic cost and cycles. Default to `unique_ptr`.
- **Calling `std::move` and then using the object**: valid but unspecified. Reassign before use.
- **Signed overflow assumed to wrap**: undefined; the optimiser may delete checks. Check before the operation or use wider/unsigned types.
- **Unsynchronised shared writes** ("benign" counters): data race. Use `std::atomic` or a mutex and verify with TSan.
- **Detached or unjoined `std::thread`**: `std::terminate` on destruction. Use `std::jthread`.
- **`expected::operator*` on an error or `optional::operator*` on empty**: undefined. Test first, or use `value()` where throwing is acceptable.
- **Using `std::print` or `ranges::to` on an old toolchain**: compile error on GCC 13. Guard with `__has_include(<print>)` or raise the compiler.
- **Relying on the default dialect**: GCC 16 changed it to GNU C++20 and older compilers default to C++17. Set the standard in CMake.
- **Global `include_directories` / `CMAKE_CXX_FLAGS` / `file(GLOB)`**: invisible dependencies and stale source lists. Use target commands and explicit file lists.
- **Combining `-fsanitize=address` with `-fsanitize=thread`**: rejected by the compiler. Use separate builds.
- **Benchmarking Debug builds or letting the compiler delete the loop**: use Release with `benchmark::DoNotOptimize`.
- **Passing runtime strings as `std::format` format strings**: compile error (or a vulnerability with `vformat`). Use `"{}"` with the value.
- **Shipping a sanitizer or assertion-heavy build to production without measuring**: large slowdown. Keep separate presets.

## 16. References

- [references/modern-language.md](references/modern-language.md): ownership and rule of zero, move semantics, view lifetime pitfalls, expected and optional, ranges, concepts, constexpr, format and print, jthread and atomics, modules and coroutines status, UB classes, library version table.
- [references/cmake.md](references/cmake.md): complete tested CMakeLists.txt, target rules, CMakePresets.json, FetchContent versus find_package, vcpkg manifest mode, Conan 2, install and export, `import std` in CMake.
- [references/sanitizers-and-tooling.md](references/sanitizers-and-tooling.md): sanitizer matrix and sample reports, warnings, clang-tidy, clang-format, hardening flags, libFuzzer, perf.
- [references/testing-and-benchmarking.md](references/testing-and-benchmarking.md): GoogleTest, Catch2 v3, CTest, test design, coverage, Google Benchmark and benchmark hygiene.
- C++ reference: https://en.cppreference.com/ ; Core Guidelines: https://isocpp.github.io/CppCoreGuidelines/
- CMake documentation: https://cmake.org/cmake/help/latest/ ; presets manual: https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html
- GCC: https://gcc.gnu.org/ ; libstdc++ status: https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html ; Clang C++ status: https://clang.llvm.org/cxx_status.html ; LLVM sanitizers: https://clang.llvm.org/docs/
- vcpkg: https://learn.microsoft.com/en-us/vcpkg/ ; Conan: https://docs.conan.io/2/
- GoogleTest: https://github.com/google/googletest ; Catch2: https://github.com/catchorg/Catch2 ; Google Benchmark: https://github.com/google/benchmark
