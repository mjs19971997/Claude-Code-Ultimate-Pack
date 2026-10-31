# Testing and Benchmarking C++

Unit tests with GoogleTest and Catch2 v3, CTest integration, test design for value types and error results, coverage, and micro-benchmarks with Google Benchmark. Examples were built and run with CMake 4.4.4, g++ 13.3, GoogleTest 1.18.0, Catch2 3.16.1 and Google Benchmark 1.10.0, the latest releases seen on their GitHub release pages (2026-10).

## Contents

1. [Choosing a framework](#1-choosing-a-framework)
2. [GoogleTest](#2-googletest)
3. [Catch2 v3](#3-catch2-v3)
4. [CTest](#4-ctest)
5. [Test design](#5-test-design)
6. [Coverage](#6-coverage)
7. [Google Benchmark](#7-google-benchmark)
8. [Benchmark hygiene](#8-benchmark-hygiene)

## 1. Choosing a framework

| Need | GoogleTest | Catch2 v3 |
|---|---|---|
| Mocking | GoogleMock ships in the same repo | none built in; use a mocking library or hand-written fakes |
| Style | fixtures and macros (`TEST`, `TEST_F`, `TEST_P`) | `TEST_CASE` with `SECTION`s, generators, matchers |
| Minimum C++ | C++17 (stated in the 1.18.0 release notes) | C++14 for v3 (check the README) |
| CMake | `GTest::gtest_main`, `gtest_discover_tests` | `Catch2::Catch2WithMain`, `catch_discover_tests` |

- Keep the existing framework in a project. For a new project pick GoogleTest if mocks are needed, Catch2 for sections and generators.
- Catch2 v3 is a compiled library (not the single header of v2): link `Catch2::Catch2` or `Catch2::Catch2WithMain` and include specific headers such as `<catch2/catch_test_macros.hpp>`.

## 2. GoogleTest

Test file used with the CMake project in [cmake.md](cmake.md) (3 tests passed under ASan and UBSan):

```cpp
#include <gtest/gtest.h>

#include "acme/parse.hpp"

TEST(ParseInt, AcceptsDigits) {
    auto r = acme::parse_int("42");
    ASSERT_TRUE(r.has_value());
    EXPECT_EQ(*r, 42);
}

TEST(ParseInt, RejectsEmpty) {
    auto r = acme::parse_int("");
    ASSERT_FALSE(r.has_value());
    EXPECT_EQ(r.error(), acme::ParseError::Empty);
}

TEST(ParseInt, RejectsTrailingGarbage) {
    EXPECT_EQ(acme::parse_int("4x").error(), acme::ParseError::NotANumber);
}
```

- `ASSERT_*` aborts the current test (use before dereferencing a result); `EXPECT_*` records the failure and continues. Use `ASSERT_TRUE(r.has_value())` before `*r` so a failure does not become undefined behaviour.
- Fixtures: `class MyTest : public ::testing::Test { void SetUp() override; };` with `TEST_F(MyTest, Name)`. Prefer a fresh object per test over shared state.
- Parameterised tests: `TEST_P` with `INSTANTIATE_TEST_SUITE_P(Name, Suite, ::testing::Values(...))`; typed tests with `TYPED_TEST_SUITE`. Death tests (`EXPECT_DEATH`) check contract violations and fork, so run them separately from threaded tests.
- GoogleMock: `MOCK_METHOD(ReturnType, Name, (Args...), (const, override));` on a class derived from an interface, then `EXPECT_CALL(mock, Name(_)).WillOnce(Return(x));`. Mock at boundaries you own (interfaces), not standard types.
- Floating point: `EXPECT_NEAR(a, b, tolerance)`, `EXPECT_FLOAT_EQ`.
- Command line: `--gtest_filter='ParseInt.*'`, `--gtest_repeat=100 --gtest_shuffle` to find order dependence and flakiness, `--gtest_brief=1`.
- Pin the dependency by tag or commit with FetchContent, or take it from vcpkg / Conan (see cmake.md). If the sandbox blocks archive downloads, a Git URL can still work.

## 3. Catch2 v3

```cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <string>

TEST_CASE("string size", "[string]") {
    std::string s = "abc";
    REQUIRE(s.size() == 3);
    SECTION("append") {
        s += "d";
        CHECK(s.size() == 4);
    }
    auto n = GENERATE(1, 2, 3);
    CHECK(std::string(static_cast<std::size_t>(n), 'x').size() == static_cast<std::size_t>(n));
    CHECK_THAT(s, Catch::Matchers::StartsWith("a"));
}
```

```cmake
FetchContent_Declare(Catch2 GIT_REPOSITORY https://github.com/catchorg/Catch2.git GIT_TAG v3.16.1 GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(Catch2)
add_executable(ct ct.cpp)
target_link_libraries(ct PRIVATE Catch2::Catch2WithMain)
```

(This built and passed: "All tests passed (10 assertions in 1 test case)".)

- Each `SECTION` runs the enclosing `TEST_CASE` from the start, so setup code above the sections runs fresh each time. `GENERATE` multiplies runs over its values.
- `REQUIRE` aborts the test case on failure; `CHECK` continues. Matchers (`CHECK_THAT`) produce readable messages. Tags select tests: `./ct "[string]"`.
- For CTest discovery add `include(Catch)` (from `Catch2` extras) and `catch_discover_tests(ct)`; check the Catch2 CMake integration documentation for the module path when using FetchContent.
- Benchmarking with `BENCHMARK` macros exists in Catch2 but Google Benchmark is more established for micro-benchmarks.

## 4. CTest

- `enable_testing()` in the top-level CMakeLists.txt, then run `ctest --test-dir build --output-on-failure -j $(nproc)` or `ctest --preset <name>`.
- Useful options: `-R regex` (run matching), `-E regex` (exclude), `--repeat until-fail:50` (find flakiness), `--timeout 60`, `--schedule-random`. Set per-test timeouts with `set_tests_properties(... PROPERTIES TIMEOUT 30)`.
- Run sanitizer builds through the `asan` presets from cmake.md in CI. Do not build with `-fsanitize=thread` and `-fsanitize=address` in one binary.

## 5. Test design

- Test behaviour through the public interface; one reason to fail per test; names that read as sentences (`RejectsEmpty`).
- For `std::expected` and `std::optional` results, assert `has_value()` first, then the value or the error code. Test each error enumerator.
- Boundary values: empty input, one element, maximum size, `INT_MAX`/`INT_MIN`, embedded NUL characters, invalid UTF-8, and non-ASCII text.
- Make time, randomness and filesystem access injectable (a clock parameter, a seeded `std::mt19937`, a `std::filesystem::path` to a temporary directory). Do not sleep for synchronisation in tests; use latches, futures or condition variables.
- Concurrency tests: run many iterations (`--gtest_repeat`, `--repeat until-fail:N`) and always under TSan in CI.
- Test move-only and exception-safety properties of containers with a small instrumented type that counts copies and throws on demand.
- Compile-time behaviour is tested with `static_assert` in the test file; negative compile tests (code that must not compile) can use concepts and `requires` expressions: `static_assert(!std::is_invocable_v<decltype(f), std::string>)`.
- Do not mock what you do not own (STL, OS APIs): wrap them in a thin interface, mock that.

## 6. Coverage

- GCC: compile and link with `--coverage` (`-O0 -g` for accurate lines), run the tests, then `gcov` or `gcovr` (`gcovr -r . --html-details out.html`, a Python tool installed with `pip`). Clang: `-fprofile-instr-generate -fcoverage-mapping`, then `llvm-profdata merge` and `llvm-cov show`.
- Use coverage to find untested branches, not as a goal in itself; an enforced threshold on new code is more useful than a global number. Exclude generated code and third-party sources.
- Coverage builds are Debug builds; do not mix with sanitizers unless the toolchain documents it.

## 7. Google Benchmark

```cpp
#include <benchmark/benchmark.h>
#include <numeric>
#include <vector>

static void BM_Accumulate(benchmark::State& state) {
    std::vector<int> v(static_cast<std::size_t>(state.range(0)), 1);
    for (auto _ : state) {
        int s = std::accumulate(v.begin(), v.end(), 0);
        benchmark::DoNotOptimize(s);
    }
    state.SetItemsProcessed(state.iterations() * state.range(0));
}
BENCHMARK(BM_Accumulate)->Range(1 << 10, 1 << 16);
```

```cmake
set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_Declare(benchmark GIT_REPOSITORY https://github.com/google/benchmark.git GIT_TAG v1.10.0 GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(benchmark)
add_executable(bm bm.cpp)
target_link_libraries(bm PRIVATE benchmark::benchmark_main)
```

- Build and run a Release build: `cmake -S . -B b -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build b && ./b/bm`. The library prints a warning when it was built in Debug mode. On the dev container used for testing, each run reported tens of nanoseconds per iteration for a 1024-element sum; absolute numbers depend entirely on the machine, so compare runs on the same host only.
- `benchmark::DoNotOptimize(x)` forces a value to be materialised; `benchmark::ClobberMemory()` forces pending writes. Without them the compiler may remove the measured work.
- Run options: `--benchmark_filter=regex`, `--benchmark_repetitions=10 --benchmark_report_aggregates_only=true`, `--benchmark_format=json` or `--benchmark_out=file.json`, `--benchmark_min_time=0.1s` (the suffix form is accepted in recent releases; check `--help`).
- Compare two builds with `tools/compare.py` in the Benchmark repository (needs SciPy); it reports a statistical test between JSON outputs.
- Complexity: `->Complexity(benchmark::oN)` fits a curve over the `Range` or `RangeMultiplier` sizes; `state.SetComplexityN(state.range(0))`.

## 8. Benchmark hygiene

- Use Release or RelWithDebInfo with the flags used in production; never benchmark a Debug or sanitizer build.
- Pin CPU frequency governor and affinity where possible (`taskset -c 2 ./bm`, `cpupower frequency-set -g performance`), close other load, and repeat runs; report median and spread.
- Benchmark realistic input sizes and data patterns, including cache-resident and cache-missing sizes. A micro-benchmark that fits in L1 cache can mislead.
- Confirm that the benchmarked function is not optimised away: inspect the assembly (`objdump -d`, or a compiler explorer) or add `DoNotOptimize` on results.
- A speed-up is real when it persists across repetitions, on the target hardware, and in an end-to-end measurement as well (see perf in [sanitizers-and-tooling.md](sanitizers-and-tooling.md)).
- Do not set pass/fail thresholds on absolute times in shared CI; compare relative results from the same job, or track trends offline.
