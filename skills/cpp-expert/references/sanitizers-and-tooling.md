# Sanitizers, Warnings, Static Analysis and Hardening

Runtime and compile-time defect detection for C++: AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, MemorySanitizer, compiler warnings, clang-tidy, clang-format, hardening flags, libFuzzer and perf. Sanitizer outputs below were produced with g++ 13.3 on Linux x86-64; clang-tidy and clang-format come from LLVM 18 locally, while the latest LLVM release seen on GitHub is 23.1.4 (October 2026) (2026-10).

## Contents

1. [Sanitizer matrix](#1-sanitizer-matrix)
2. [AddressSanitizer and UBSan in practice](#2-addresssanitizer-and-ubsan-in-practice)
3. [ThreadSanitizer](#3-threadsanitizer)
4. [MemorySanitizer and Valgrind](#4-memorysanitizer-and-valgrind)
5. [Warnings](#5-warnings)
6. [clang-tidy](#6-clang-tidy)
7. [clang-format](#7-clang-format)
8. [Hardening flags](#8-hardening-flags)
9. [Fuzzing with libFuzzer](#9-fuzzing-with-libfuzzer)
10. [Profiling with perf](#10-profiling-with-perf)

## 1. Sanitizer matrix

| Sanitizer | Flag | Finds | Compilers | Notes |
|---|---|---|---|---|
| AddressSanitizer | `-fsanitize=address` | heap, stack and global overflow, use after free, use after scope, double free, leaks (LeakSanitizer on Linux) | GCC, Clang, MSVC (`/fsanitize=address`) | about 2x slowdown, 2-3x memory |
| UndefinedBehaviorSanitizer | `-fsanitize=undefined` | signed overflow, bad shifts, null deref, misaligned access, bad enum/bool, bounds of arrays with known size | GCC, Clang | combine with ASan |
| ThreadSanitizer | `-fsanitize=thread` | data races, lock order inversions | GCC, Clang | cannot be combined with ASan or MSan |
| MemorySanitizer | `-fsanitize=memory` | reads of uninitialised memory | Clang only, Linux | needs the whole program and libc++ instrumented |

- ASan + UBSan: `-fsanitize=address,undefined`. TSan alone. Confirmed locally: `g++ -fsanitize=address,thread` fails with "'-fsanitize=thread' is incompatible with '-fsanitize=address'".
- Compile with `-g -O1 -fno-omit-frame-pointer` for readable stacks and low overhead; `-O0` also works. Link with the same `-fsanitize=` flags.
- Make UBSan fatal in CI with `-fno-sanitize-recover=undefined` (otherwise it prints and continues). Select extra checks (Clang) with `-fsanitize=integer`, `-fsanitize=nullability`; check the Clang docs for the list.
- Run options come from environment variables: `ASAN_OPTIONS=detect_stack_use_after_return=1:strict_string_checks=1:detect_leaks=1`, `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`, `TSAN_OPTIONS=halt_on_error=1`. Provide a symbolizer (`llvm-symbolizer` on `PATH`) for readable traces.
- Do not ship sanitizer builds to production; run the full test suite and fuzzers under them in CI (a separate job per sanitizer family).
- Third-party code not built with the sanitizer can produce false negatives; false positives in TSan appear with unsupported primitives (for example hand-written fences), so use `std::atomic` and mutexes.

## 2. AddressSanitizer and UBSan in practice

```cpp
// uaf.cpp
#include <cstdio>
#include <vector>
int main() {
    std::vector<int> v{1, 2, 3};
    int* p = &v[0];
    v.push_back(4);          // may reallocate: p dangles
    std::printf("%d\n", *p); // heap-use-after-free
}
```

```bash
g++ -std=c++23 -g -fsanitize=address,undefined -fno-omit-frame-pointer uaf.cpp -o uaf && ./uaf
# ==NNN==ERROR: AddressSanitizer: heap-use-after-free on address 0x... 
# SUMMARY: AddressSanitizer: heap-use-after-free uaf.cpp:9 in main
```

```cpp
// ub.cpp
#include <climits>
#include <cstdio>
int main(int argc, char**) {
    int x = INT_MAX - 1 + argc;   // argc == 1 -> INT_MAX
    x += argc;                    // signed overflow
    std::printf("%d\n", x);
}
```

```bash
g++ -std=c++23 -g -fsanitize=undefined ub.cpp -o ub && ./ub
# ub.cpp:5:7: runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
```

- Read the report from the top: the access stack, then "freed by" and "previously allocated by" stacks.
- `detect_stack_use_after_return` catches a returned pointer to a local; it costs memory, so enable it for test runs.
- Container annotations (`_GLIBCXX_SANITIZE_VECTOR`, Clang's libc++ annotations) detect reads in the unused capacity of a `std::vector`; check the library docs for the macro in your version.
- LeakSanitizer is enabled by default with ASan on Linux; it can fail in restricted sandboxes (ptrace limits). If it errors out, try `ASAN_OPTIONS=detect_leaks=0` and test leaks elsewhere.

## 3. ThreadSanitizer

```cpp
// race.cpp
#include <thread>
int counter = 0;
int main() {
    std::jthread a([] { for (int i = 0; i < 100000; ++i) ++counter; });
    std::jthread b([] { for (int i = 0; i < 100000; ++i) ++counter; });
}
```

```bash
g++ -std=c++23 -g -fsanitize=thread race.cpp -o race -pthread && ./race
# WARNING: ThreadSanitizer: data race (pid=NNN)
# SUMMARY: ThreadSanitizer: data race race.cpp:6 in operator()
```

- Fix with `std::atomic<int>` or a mutex, then re-run. TSan sees only races that actually execute, so exercise concurrent paths in tests.
- TSan needs a high-entropy ASLR mapping on some kernels; if it aborts at startup with a memory-mapping message, check the sanitizer documentation for the `vm.mmap_rnd_bits` note.
- Annotate custom synchronisation only as a last resort (`__tsan_acquire`, `__tsan_release`).

## 4. MemorySanitizer and Valgrind

- MSan (`clang++ -fsanitize=memory -fsanitize-memory-track-origins`) flags use of uninitialised values. It requires every linked library, including the standard library, to be instrumented; build libc++ with MSan or accept false positives. The LLVM docs describe building an instrumented libc++.
- Valgrind (`valgrind --leak-check=full ./app`) needs no recompile and finds uninitialised reads, but runs 10-50x slower and does not see stack overflows the way ASan does.
- Use a Debug build with `_GLIBCXX_ASSERTIONS` as the first, cheapest check (section 8).

## 5. Warnings

- GCC and Clang baseline: `-Wall -Wextra -Wpedantic`. Useful additions: `-Wshadow -Wconversion -Wsign-conversion -Wnon-virtual-dtor -Woverloaded-virtual -Wold-style-cast -Wcast-align -Wnull-dereference -Wdouble-promotion -Wformat=2 -Wimplicit-fallthrough -Wuseless-cast` (GCC) and `-Wunused`. Test each addition on your code; `-Wconversion` is noisy on existing code.
- MSVC: `/W4` (use `/Wall` only for research, it is very noisy) and `/permissive-`; `/sdl` for extra security checks.
- CI: add `-Werror` (or `/WX`) in CI only, through an option, so a new compiler version's new warning does not break users who build releases. Warnings from third-party headers: include them with `SYSTEM` (`target_include_directories(... SYSTEM ...)`) to silence them.
- `-fanalyzer` (GCC) is a static path analyser; GCC 13 supports C well and C++ only partially, so treat its C++ output as advisory and check current GCC docs.
- `[[nodiscard]]` on error-returning functions, `explicit` on single-argument constructors, `override` on every virtual override (`-Wsuggest-override`).

## 6. clang-tidy

- Run through the compilation database: `clang-tidy -p build src/parse.cpp` (needs `CMAKE_EXPORT_COMPILE_COMMANDS=ON`), or `run-clang-tidy -p build`. CMake can run it during the build with `CMAKE_CXX_CLANG_TIDY` (slow; prefer a separate CI job).
- Start from a small, curated `.clang-tidy`, then expand:

```yaml
Checks: 'bugprone-*,performance-*,modernize-*,cppcoreguidelines-*,-modernize-use-trailing-return-type'
WarningsAsErrors: ''
HeaderFilterRegex: '^(include|src)/'
```

- Valuable groups: `bugprone-*` (use after move, dangling handle, suspicious string-compare), `performance-*` (unnecessary copy, move-const-arg), `modernize-*` (`use-nullptr`, `use-override`, `use-emplace`), `readability-*` (naming, braces), `cppcoreguidelines-*` (avoid-c-arrays, owning-memory), `clang-analyzer-*` (path analysis), `misc-*`.
- Suppress a single line with `// NOLINT(check-name)` and a reason; never a bare `NOLINT`. `--fix` applies safe fixes; review them as a normal diff.
- Match the clang-tidy major version to the compiler that produced `compile_commands.json`, or the parser may reject GCC-only flags (use `--extra-arg=-Wno-unknown-warning-option` or drop the flag). Checks are added in each LLVM release; check the docs for the version in use.

## 7. clang-format

- `.clang-format` at the repo root. Start with `BasedOnStyle: Google` (or LLVM, Chromium, Mozilla, WebKit, Microsoft, GNU) and override only a few keys, for example `IndentWidth: 4`, `ColumnLimit: 100`. Generate a starter file with `clang-format -style=Google -dump-config > .clang-format`.
- Check in CI without modifying files: `clang-format --dry-run --Werror $(git ls-files '*.cpp' '*.hpp')`. Format locally with `-i`.
- Pin one clang-format version in CI and in the pre-commit hook; output changes between major versions.

## 8. Hardening flags

Tested to compile and run with g++ 13.3 on x86-64 Linux:

```bash
g++ -std=c++23 -O2 -D_FORTIFY_SOURCE=3 -D_GLIBCXX_ASSERTIONS \
    -fstack-protector-strong -fstack-clash-protection -fcf-protection=full \
    -fPIE -pie -Wl,-z,relro,-z,now app.cpp -o app
```

| Flag | Effect |
|---|---|
| `-D_FORTIFY_SOURCE=3` | Checks sizes in `memcpy`, `strcpy`, `read` and others at run time; needs optimisation (`-O1` or higher) and a glibc that supports level 3 (check the glibc version; 2 is the older level) |
| `-D_GLIBCXX_ASSERTIONS` | libstdc++ precondition checks: `vector::operator[]`, `front()` on empty, `optional::operator*`, `span` access |
| `-fstack-protector-strong` | Stack canaries on functions with arrays or address-taken locals |
| `-fstack-clash-protection` | Probes large stack allocations |
| `-fcf-protection=full` | Intel CET branch and shadow-stack markers (x86 only); on ARM use `-mbranch-protection=standard` |
| `-fPIE -pie`, `-Wl,-z,relro,-z,now` | Position independent executable, read-only relocations, immediate binding |

- libc++ has its own hardening modes selected at build time (`_LIBCPP_HARDENING_MODE` with fast, extensive and debug levels in recent releases); check the libc++ hardening documentation for your version.
- MSVC counterparts: `/GS` (default), `/guard:cf` (control-flow guard), `/sdl`, `/DYNAMICBASE`, `/NXCOMPAT`.
- Measure the performance cost of assertions on hot paths before enabling them in release builds. Hardening reduces exploit impact; it does not remove undefined behaviour.
- Pair with `-Wformat -Wformat-security` and avoid `printf` with non-literal format strings.

## 9. Fuzzing with libFuzzer

A fuzz target is a function receiving bytes. Build with Clang and the `fuzzer` sanitizer plus ASan and UBSan:

```cpp
// fz.cpp
#include <cstddef>
#include <cstdint>
#include <string_view>

bool starts_with_magic(std::string_view s) { return s.size() >= 4 && s.substr(0, 4) == "MAGI"; }

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    std::string_view s(reinterpret_cast<const char*>(data), size);
    (void)starts_with_magic(s);
    return 0;
}
```

```bash
clang++ -std=c++23 -g -O1 -fsanitize=fuzzer,address,undefined fz.cpp -o fz
mkdir -p corpus && ./fz -max_total_time=60 corpus
```

- Not run here: the local Clang 18 package lacks the sanitizer runtime libraries, so the commands are the documented shape and not locally verified. Check the LLVM libFuzzer documentation for current options and its maintenance status.
- Keep the corpus and crash inputs in the repository (`crash-*` files) as regression tests; replay them by passing the file name to the binary.
- Make the target deterministic, fast and free of global state; avoid network, clock and random sources. A seed corpus of valid inputs and a dictionary (`-dict=`) speed up structured formats.
- Alternatives: AFL++ (check docs), and GCC has no libFuzzer; use Clang for fuzz builds.

## 10. Profiling with perf

```bash
g++ -std=c++23 -O2 -g -fno-omit-frame-pointer app.cpp -o app
perf record -g ./app          # sample call stacks
perf report --stdio | head -40
perf stat -e cycles,instructions,cache-misses,branch-misses ./app
```

- Keep `-O2` or `-O3` and add `-g` plus frame pointers (or `perf record --call-graph dwarf`) so the profile reflects optimised code.
- `perf` may need `kernel.perf_event_paranoid` adjusted or CAP_PERFMON; containers often block it. Alternatives: Valgrind `callgrind`, Google `pprof` with gperftools, and `-pg` with `gprof`.
- Check for obvious causes before micro-tuning: allocations in loops (`reserve`, `string_view`, small-buffer types), unnecessary copies (`performance-*` tidy checks), cache-unfriendly data layout (structure of arrays), virtual calls in hot loops, and `std::endl` flushes.
- Verify a change with a benchmark (see [testing-and-benchmarking.md](testing-and-benchmarking.md)); do not accept a speed-up that is within the noise.
