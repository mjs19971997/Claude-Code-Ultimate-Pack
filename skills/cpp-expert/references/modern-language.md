# Modern C++ Language and Library Patterns

C++20 and C++23 idioms for ownership, value semantics, error handling, ranges, concepts, compile-time code, formatting and concurrency, with the compiler and standard library versions that gate each feature. Full programs below compile with `g++ 13.3 -std=c++23 -Wall -Wextra -Wpedantic` (checked 2026-10); features that need a newer library are shown as fragments and marked.

## Contents

1. [Ownership and the rule of zero](#1-ownership-and-the-rule-of-zero)
2. [Move semantics](#2-move-semantics)
3. [Non-owning views and lifetime pitfalls](#3-non-owning-views-and-lifetime-pitfalls)
4. [Error handling with expected and optional](#4-error-handling-with-expected-and-optional)
5. [Ranges and views](#5-ranges-and-views)
6. [Concepts and requires clauses](#6-concepts-and-requires-clauses)
7. [constexpr and consteval](#7-constexpr-and-consteval)
8. [Formatting and printing](#8-formatting-and-printing)
9. [Concurrency](#9-concurrency)
10. [Modules and coroutines](#10-modules-and-coroutines)
11. [Undefined behaviour classes](#11-undefined-behaviour-classes)
12. [Library feature availability](#12-library-feature-availability)

## 1. Ownership and the rule of zero

A class that owns resources only through members that already manage themselves (`std::string`, `std::vector`, `std::unique_ptr`, `std::lock_guard`) needs no destructor, copy or move declarations. The compiler-generated special members are correct and `noexcept` where the members allow it.

```cpp
#include <cstdio>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Buffer {              // rule of zero: the unique_ptr member owns the memory
    std::unique_ptr<char[]> data_;
    std::size_t size_ = 0;
public:
    explicit Buffer(std::size_t n) : data_(std::make_unique<char[]>(n)), size_(n) {}
    std::size_t size() const noexcept { return size_; }
};

struct Widget {
    std::string name;
    std::vector<int> values;
    Buffer buf{16};
};

int main() {
    Widget a{"w", {1, 2, 3}};
    Widget b = std::move(a);   // Buffer is move-only, so Widget is move-only too
    std::printf("%zu %zu\n", b.values.size(), b.buf.size());
}
```

- Rule of five: if a class declares any of destructor, copy or move constructor, copy or move assignment, declare or `= default` / `= delete` all five. Only classes that wrap a raw handle (file descriptor, C library object) need this; wrap the handle once, then use the wrapper.
- Pass `T*` / `T&` for "use but do not own" and `std::unique_ptr` by value for "take ownership".
- Smart pointers: `std::unique_ptr` is the default owner (no overhead with the default deleter). `std::shared_ptr` costs an atomic count and hides ownership; use it only for shared lifetime. `std::weak_ptr` breaks cycles. Create with `std::make_unique` / `std::make_shared`.
- Custom cleanup: `std::unique_ptr<FILE, decltype(&std::fclose)> f(std::fopen(path, "rb"), &std::fclose);`. For arbitrary scope exit work use a small RAII guard class; `std::scope_exit` is a library fundamentals TS type and not in the C++23 standard.
- A destructor must not throw (it is `noexcept` by default). Never call virtual functions from constructors or destructors expecting derived behaviour. A polymorphic base needs a virtual destructor, or a protected non-virtual one.

## 2. Move semantics

- `std::move` is a cast to rvalue reference; it moves nothing by itself. After a move the source is valid but unspecified: only destroy it or assign to it.
- Mark move constructors and move assignment `noexcept`. `std::vector` reallocation uses `std::move_if_noexcept`, so a throwing move makes it copy instead.
- Do not `return std::move(local);`: it disables copy elision and triggers `-Wpessimizing-move` / `-Wredundant-move`. Return the local by name.
- Take sink parameters by value and move them into place: `void set_name(std::string s) { name_ = std::move(s); }`.
- `std::forward<T>(x)` only inside a forwarding reference (`T&&` with `T` deduced). `auto&&` in a lambda parameter list needs `decltype(x)` with `std::forward`.
- `std::move_only_function` (C++23, GCC 12.1) stores move-only callables; `std::function` needs copyable ones.

## 3. Non-owning views and lifetime pitfalls

`std::string_view`, `std::span`, iterators, references and ranges views do not own their data. Most real defects come from a view outliving its source.

```cpp
std::string_view bad1 = std::string("temporary, long enough to avoid SSO");  // dangling
std::vector<int> v{1, 2, 3};
int* p = &v[0];
v.push_back(4);                                                                // p may dangle (reallocation)
```

- A function that returns a `string_view` or `span` into a parameter must document that the argument outlives the result. Prefer returning `std::string` / `std::vector` when the caller cannot easily keep the source alive.
- Do not store a `string_view` as a class member unless the class is itself a view. `data()` is not NUL-terminated; build a `std::string` for C APIs.
- Range-for over `make().items()` can dangle when `make()` returns a temporary; bind the temporary to a named variable first.
- `std::span<T>` replaces `(T*, size_t)` pairs; use `std::span<const T>` for read-only parameters and check sizes before `.subspan`, `.first(n)`, `.last(n)`.
- Algorithms return `std::ranges::dangling` when given an rvalue range; do not work around it.
- Find these defects with AddressSanitizer (heap-use-after-free, stack-use-after-scope) and `-Wdangling-gsl` (Clang) and GCC's `-Wdangling-pointer`; see [sanitizers-and-tooling.md](sanitizers-and-tooling.md).

## 4. Error handling with expected and optional

- `std::optional<T>` models "value or nothing" when the reason for absence is obvious (lookups). `std::expected<T, E>` (C++23) carries the error when the caller needs to know why. Exceptions remain right for rare, non-local failures and constructors.
- `std::expected` has monadic operations: `and_then`, `or_else`, `transform`, `transform_error`. `value()` throws `std::bad_expected_access`; `*e` on an error is undefined behaviour, so test `has_value()` or `if (auto r = ...)` first.
- Use an enum or small struct as `E`; mark result-returning functions `[[nodiscard]]`.

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

std::expected<int, ParseError> doubled(std::string_view s) {
    return parse_int(s).transform([](int v) { return v * 2; });
}

int main() {
    for (std::string_view in : {"21", "", "4x", "99999999999"}) {
        if (auto r = doubled(in)) std::puts(std::format("{} -> {}", in, *r).c_str());
        else std::puts(std::format("{} -> error: {}", in, to_string(r.error())).c_str());
    }
}
```

## 5. Ranges and views

- Views are lazy, composable with `|`, and cheap to copy. Algorithms in `std::ranges::` take whole ranges plus projections: `std::ranges::sort(people, {}, &Person::age);`.
- `std::views::filter`, `transform`, `take`, `drop`, `take_while`, `reverse`, `keys`, `values`, `iota`, `split`, `join` are C++20. `zip`, `enumerate`, `chunk`, `slide`, `adjacent`, `join_with`, `stride` and `std::ranges::to` are C++23; each needs a recent library, so check section 12 and the `__cpp_lib_ranges_*` feature macros before using them. `ranges::to` needs GCC 14 or newer (per the libstdc++ status table); on GCC 13 build the container with a loop.
- `filter_view` is not `const`-iterable; take `auto&&` in generic code.
- Do not store a view that refers to a local container beyond that container's life (section 3).

```cpp
#include <algorithm>
#include <concepts>
#include <cstdio>
#include <ranges>
#include <span>
#include <string>
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
    std::printf("%ld\n", sum_of_even_squares(v));          // 4 + 16 + 36 = 56
    std::vector<double> d{1, 2, 3};
    scale(d, 2.0);
    std::vector<std::string> names{"b", "a"};
    std::ranges::sort(names);
    std::printf("%g %s\n", d[2], names.front().c_str());   // 6 a
}
```

## 6. Concepts and requires clauses

- Constrain templates with concepts instead of SFINAE or `enable_if`: `template <std::integral T>`, `void f(std::ranges::range auto&& r)`, or a trailing `requires`. Errors then name the unmet constraint.
- Define small named concepts for the operations the template needs, not for the whole type: `template <typename T> concept Serializable = requires(const T& t, std::ostream& os) { { os << t } -> std::same_as<std::ostream&>; };`.
- Subsumption: a more constrained overload wins when its constraint conjunction contains the other's. Atomic constraints are compared by source expression, so reuse the named concept rather than retyping the expression.
- Standard concepts: `std::integral`, `std::regular`, `std::movable`, `std::invocable`, `std::predicate`, `std::same_as`, `std::convertible_to`, `std::ranges::range`, `std::totally_ordered`.
- Deducing this (C++23, Clang 18 per the Clang status page; check GCC and MSVC) removes duplicated `const` and non-`const` overloads: `auto&& get(this auto&& self) { return self.value_; }`. Confirm the compiler version before use.

## 7. constexpr and consteval

- `constexpr` functions may run at compile time or at run time. `consteval` functions must run at compile time (an immediate function). `constinit` guarantees constant initialisation of a static without making it `const`, which avoids the static initialisation order problem.
- `static_assert` checks at compile time; since C++26 the message may be a constant expression (Clang 17 implements it per the Clang status page).
- C++20 allows `constexpr` `std::vector`, `std::string` and virtual functions within one constant evaluation. Check compiler status for newer relaxations.
- `if consteval { ... } else { ... }` (C++23, Clang 14) selects a compile-time-only path.

```cpp
consteval int fib(int n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
static_assert(fib(10) == 55);
constexpr std::array<int, 4> kPrimes{2, 3, 5, 7};
```

## 8. Formatting and printing

- `std::format` (C++20 `<format>`) is type safe and checks the format string at compile time: a bad specifier is a compile error. `std::format_to`, `std::formatted_size` avoid allocations. Write a `std::formatter<T>` specialisation to format your own type.
- `std::print` and `std::println` (C++23, `<print>`) write directly to `stdout` or a `FILE*` and handle Unicode on a UTF-8 terminal correctly. Library availability: GCC 14.1 and newer for `<print>` (libstdc++ status table); on older toolchains use `std::puts(std::format(...).c_str())` as in section 4. Check libc++ and MSVC STL status pages for your version before relying on `<print>`.
- A format string must be a constant expression; for runtime strings use `std::vformat` with `std::make_format_args`, and never pass untrusted text as the format string itself.
- `std::format("{:>8.3f}", x)` follows a specification close to Python's; `{:?}` debug escape and range formatting are C++23 and arrived in later library versions than basic `<format>` (GCC 15.2 is listed as complete for range formatting).

## 9. Concurrency

- `std::jthread` joins in its destructor and accepts a `std::stop_token` first parameter; `request_stop()` is called on destruction. Use it instead of `std::thread` so a thrown exception cannot hit `std::terminate` from an unjoined thread.
- Cooperative cancellation: poll `st.stop_requested()` or register `std::stop_callback`. For waits use `std::condition_variable_any::wait(lock, st, pred)`.
- Protect shared state with `std::mutex` and `std::scoped_lock` (locks several mutexes deadlock-free). A mutex plus the data it guards in one class is easier to review than free-standing locks.
- `std::atomic<T>` for single words. The default `memory_order_seq_cst` is correct and often fast enough. `relaxed` is only for counters whose value orders nothing; `release` store paired with `acquire` load publishes data. Do not use `volatile` for synchronisation. C++20 adds `atomic::wait` / `notify_one`, `std::latch`, `std::barrier`, `std::counting_semaphore`.
- Data race on a non-atomic is undefined behaviour even if it "looks benign". Detect with ThreadSanitizer.

A complete `std::jthread` plus `std::stop_token` example is in SKILL.md section 14.

## 10. Modules and coroutines

- Modules: `import std;` and `import std.compat;` arrive with C++23 (P2465). libstdc++ lists support from GCC 15.1. In CMake the support is gated: the CMake 4.4 documentation for `CXX_MODULE_STD` still says it is meaningful only when the `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` gate is enabled, and it applies to targets with `cxx_std_23` or newer. Check the current CMake documentation for the gate value and the generator support (Ninja and Visual Studio generators) before adopting. Treat named modules as workable for greenfield code on a single toolchain and risky for libraries consumed with several compilers.
- Keep `#include` headers as the portable interface while downstream users are on older compilers.
- Coroutines (C++20): `co_await`, `co_yield`, `co_return` need a promise type; write them with a library (a task or generator type) rather than by hand. `std::generator` (C++23, `<generator>`) is a range of yielded values; the libstdc++ status table has no row for it in the version checked, so verify availability on your standard library. Coroutine frames are heap allocated by default and reference parameters dangle across suspension: pass by value.
- Do not rely on captures in coroutine lambdas; the frame can outlive the lambda object. Pass state as parameters.

## 11. Undefined behaviour classes

| Class | Typical cause | Detect |
|---|---|---|
| Memory | out of bounds, use after free, double free, uninitialised read, dangling view | ASan, MSan (Clang), `_GLIBCXX_ASSERTIONS`, Valgrind |
| Integer | signed overflow, shift by too many bits, division by zero, narrowing in `float`-to-`int` | UBSan (`-fsanitize=undefined`), `-Wconversion` |
| Lifetime | access after destructor, return reference to local, `string_view` of a temporary, iterator invalidation | ASan (use-after-scope), clang-tidy `bugprone-*` |
| Aliasing and type | strict aliasing violation, wrong `reinterpret_cast`, union type punning | UBSan, `-Wstrict-aliasing`; use `std::bit_cast` and `std::memcpy` |
| Concurrency | data race, unsynchronised access to non-atomic | TSan |
| Contract | `std::expected::operator*` on error, `optional::operator*` on empty, `front()` on empty | `_GLIBCXX_ASSERTIONS`, libc++ hardening, asserts |
| Order | unsequenced modification, static initialisation order across translation units | `-Wsequence-point`, `constinit` |

- Signed overflow is undefined; unsigned wraps. Do the arithmetic in a wide enough type, check before the operation, or use `std::add_sat` (C++26, check availability) or compiler builtins such as `__builtin_add_overflow`.
- Reading an uninitialised object is undefined for most types. Use `T x{};` or `= {}`; C++26 changes this to "erroneous behaviour" (check compiler status).

## 12. Library feature availability

GCC libstdc++ first-implemented versions (libstdc++ C++23 status table, 2026-10); check the macro in your toolchain:

| Feature | GCC | Macro |
|---|---|---|
| `std::expected` | 12.1 | `__cpp_lib_expected` |
| `std::move_only_function`, `std::stacktrace` | 12.1 | `__cpp_lib_move_only_function`, `__cpp_lib_stacktrace` |
| `std::print`, `std::println` | 14.1 | `__cpp_lib_print` |
| `std::ranges::to` | 14.1 | `__cpp_lib_ranges_to_container` |
| `std::flat_map` | 15.1 | `__cpp_lib_flat_map` |
| `import std;` | 15.1 | `__cpp_lib_modules` |

- GCC 16.1 (30 April 2026) defaults the C++ front end to GNU C++20 and lists C++26 reflection (`-freflection`), contracts and `std::simd` as experimental. Do not ship them in production code; pass `-std=c++23` or `-std=c++20` explicitly in your build.
- Clang status (vendor page): C++23 is "partial"; deducing this from Clang 18, static `operator()` from 16, multidimensional subscript from 15, `if consteval` from 14. Reflection (P2996) and contracts (P2900) are marked not implemented on that page.
- MSVC: check the Microsoft C++ conformance page for per-feature versions; `/std:c++latest` enables the newest draft.
- Test macros in code: `#if defined(__cpp_lib_print)`, `#if __has_include(<print>)`, and `__cpp_lib_expected >= 202202L`. A portable fallback beats a hard version assumption.
