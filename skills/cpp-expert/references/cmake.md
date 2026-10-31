# CMake, Presets and Dependency Management

Target-based CMake for C++20 and C++23 projects: library and executable targets, compile features, `CMakePresets.json`, dependency acquisition with `find_package`, `FetchContent`, vcpkg manifest mode and Conan 2, plus install and export. The project below was configured, built, tested and installed with CMake 4.4.4, Ninja, g++ 13.3 and GoogleTest 1.18.0 (2026-10).

## Contents

1. [Versions and policy](#1-versions-and-policy)
2. [Project layout and a complete CMakeLists.txt](#2-project-layout-and-a-complete-cmakeliststxt)
3. [Target rules](#3-target-rules)
4. [Presets](#4-presets)
5. [FetchContent versus find_package](#5-fetchcontent-versus-find_package)
6. [vcpkg manifest mode](#6-vcpkg-manifest-mode)
7. [Conan 2](#7-conan-2)
8. [Install and export](#8-install-and-export)
9. [import std and modules in CMake](#9-import-std-and-modules-in-cmake)
10. [Troubleshooting](#10-troubleshooting)

## 1. Versions and policy

- Latest stable CMake seen on the Kitware GitHub releases page is 4.4.5 (27 October 2026); 4.5.0 is at release candidate stage. Check `cmake --version` on the build machine; distribution packages often lag (Ubuntu 24.04 ships 3.28).
- `cmake_minimum_required(VERSION 3.28)` sets the policy baseline. Pick the oldest version your CI and users actually have; CMake 4 removed compatibility with projects that ask for a minimum below 3.5 (check the release notes if an old dependency fails to configure).
- Preset schema versions map to CMake versions: 6 needs 3.25, 7 needs 3.27, 8 needs 3.28, 9 needs 3.30, 10 needs 3.31, 11 needs 4.3, 12 needs 4.4, 13 needs 4.5 (from the CMake presets manual). Use the lowest schema version that has the fields you use.
- Use the Ninja generator for single-config builds (`-G Ninja`); Visual Studio generators are multi-config (`--config Release`).

## 2. Project layout and a complete CMakeLists.txt

```text
acme/
  CMakeLists.txt
  CMakePresets.json
  cmake/acmeConfig.cmake      # one line: include(".../acmeTargets.cmake")
  include/acme/parse.hpp      # public headers
  src/parse.cpp
  tests/parse_test.cpp
```

```cmake
cmake_minimum_required(VERSION 3.28)
project(acme VERSION 1.0.0 LANGUAGES CXX)

option(ACME_BUILD_TESTS "Build tests" ON)
option(ACME_SANITIZE "Enable ASan and UBSan" OFF)

add_library(acme src/parse.cpp)
add_library(acme::acme ALIAS acme)
target_include_directories(acme PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_compile_features(acme PUBLIC cxx_std_23)
set_target_properties(acme PROPERTIES CXX_EXTENSIONS OFF)

add_library(acme_options INTERFACE)
target_compile_options(acme_options INTERFACE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wshadow>
  $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->)
if(ACME_SANITIZE AND NOT MSVC)
  target_compile_options(acme_options INTERFACE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(acme_options INTERFACE -fsanitize=address,undefined)
endif()
target_link_libraries(acme PRIVATE $<BUILD_LOCAL_INTERFACE:acme_options>)

if(ACME_BUILD_TESTS)
  enable_testing()
  include(FetchContent)
  FetchContent_Declare(googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.18.0
    GIT_SHALLOW TRUE)
  FetchContent_MakeAvailable(googletest)
  include(GoogleTest)
  add_executable(acme_tests tests/parse_test.cpp)
  target_link_libraries(acme_tests PRIVATE acme::acme $<BUILD_LOCAL_INTERFACE:acme_options> GTest::gtest_main)
  gtest_discover_tests(acme_tests)
endif()
```

- Warnings live in an INTERFACE target (`acme_options`) so they apply to your code and not to FetchContent dependencies. Do not set `CMAKE_CXX_FLAGS` globally for warnings.
- `target_compile_features(... cxx_std_23)` requests "at least C++23" and propagates to consumers (PUBLIC). `CXX_EXTENSIONS OFF` gives `-std=c++23` instead of `-std=gnu++23`. Avoid `set(CMAKE_CXX_STANDARD ...)` in libraries.
- The sanitizer flags are not exported because the target is linked through `BUILD_LOCAL_INTERFACE`; otherwise `install(EXPORT)` would complain about a missing export for `acme_options`.

## 3. Target rules

- Everything is a target with properties: `PRIVATE` for the target's own build, `INTERFACE` for consumers only, `PUBLIC` for both. Use the narrowest keyword; headers included from public headers need `PUBLIC` include directories.
- Link with `target_link_libraries(app PRIVATE acme::acme)`; transitive include paths, definitions and features follow. Use namespaced alias names (`acme::acme`) so a typo is a configure error, not a linker flag.
- Do not use `include_directories`, `link_directories`, `add_definitions`, `file(GLOB)` for source lists (new files are not detected without a reconfigure) or `CMAKE_CXX_FLAGS` edits in project code.
- Generator expressions select per-config and per-compiler values: `$<CONFIG:Debug>`, `$<CXX_COMPILER_ID:GNU>`, `$<BUILD_INTERFACE:...>`, `$<INSTALL_INTERFACE:...>`.
- Set `CMAKE_EXPORT_COMPILE_COMMANDS=ON` so clang-tidy and editors find `compile_commands.json`.
- Set `CMAKE_BUILD_TYPE` for single-config generators (Debug, Release, RelWithDebInfo, MinSizeRel); an empty value means no optimisation flags. Link-time optimisation: set `INTERPROCEDURAL_OPTIMIZATION` per target after `include(CheckIPOSupported)`.
- Run tests with `ctest --preset <name> --output-on-failure`; `gtest_discover_tests` registers each test case.

## 4. Presets

`CMakePresets.json` (committed) holds shared configure, build, test and workflow presets; `CMakeUserPresets.json` (git-ignored) holds personal ones and may inherit from the shared file. Tested with CMake 4.4.4 using schema version 6:

```json
{
  "version": 6,
  "cmakeMinimumRequired": { "major": 3, "minor": 28, "patch": 0 },
  "configurePresets": [
    {
      "name": "base",
      "hidden": true,
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/${presetName}",
      "cacheVariables": { "CMAKE_EXPORT_COMPILE_COMMANDS": "ON" }
    },
    { "name": "debug", "inherits": "base", "cacheVariables": { "CMAKE_BUILD_TYPE": "Debug" } },
    {
      "name": "asan",
      "inherits": "base",
      "cacheVariables": { "CMAKE_BUILD_TYPE": "Debug", "ACME_SANITIZE": "ON" }
    },
    { "name": "release", "inherits": "base", "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" } }
  ],
  "buildPresets": [
    { "name": "asan", "configurePreset": "asan" },
    { "name": "release", "configurePreset": "release" }
  ],
  "testPresets": [
    { "name": "asan", "configurePreset": "asan", "output": { "outputOnFailure": true } }
  ]
}
```

```bash
cmake --preset asan && cmake --build --preset asan && ctest --preset asan
cmake --list-presets          # shows configure presets; add 'build' or 'test' to list those
```

- `inherits` merges fields; `hidden: true` presets are templates. `condition` can restrict a preset to a host OS.
- Use `$env{VCPKG_ROOT}` in `toolchainFile` for vcpkg; do not commit absolute personal paths.
- Workflow presets (`workflowPresets`, schema 6+) chain configure, build and test as one name for CI.
- Presets are an interface for developers, IDEs and CI alike; CI should call the same preset names.

## 5. FetchContent versus find_package

| Use | When |
|---|---|
| `find_package(fmt CONFIG REQUIRED)` | The dependency comes from the OS, vcpkg or Conan; builds are fast and versions are managed outside the repo |
| `FetchContent` | Small, pure CMake dependencies (test frameworks, benchmark) pinned to a tag or commit; the source builds with your flags |
| Git submodule / vendoring | Offline builds or patched sources; accept the maintenance cost |

- Pin a tag or, better, a full commit hash with `GIT_TAG`; use `GIT_SHALLOW TRUE` only with tags or branches. For archives use `URL` plus `URL_HASH SHA256=...` so the download is verified.
- `FIND_PACKAGE_ARGS` on `FetchContent_Declare` makes it try `find_package` first and fall back to download; `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON` favours config files.
- Dependencies built with FetchContent inherit your global flags and run their own install rules; set their options before `FetchContent_MakeAvailable` (for example `set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)`), and mark test-only dependencies so they are not installed.
- Offline or restricted networks: a `URL` download may be blocked while `git clone` works (seen in a sandbox during testing); provide `FETCHCONTENT_SOURCE_DIR_<NAME>` or `FETCHCONTENT_FULLY_DISCONNECTED` for reproducible offline builds.
- Libraries should not call FetchContent on behalf of consumers; offer `find_package` support instead.

## 6. vcpkg manifest mode

Latest vcpkg release seen: tag `2026.10.16` (published 20 October 2026). In manifest mode a `vcpkg.json` next to the root `CMakeLists.txt` lists the dependencies, and the toolchain file installs them during configure.

```json
{
  "name": "acme",
  "version-string": "1.0.0",
  "dependencies": ["fmt", "gtest"],
  "builtin-baseline": "<40-hex vcpkg commit>"
}
```

```bash
git clone https://github.com/microsoft/vcpkg.git && ./vcpkg/bootstrap-vcpkg.sh   # review the script first
export VCPKG_ROOT="$PWD/vcpkg"
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake"
```

- `builtin-baseline` pins the versions of every port to a vcpkg commit; run `vcpkg x-update-baseline --add-initial-baseline` (check the docs for the current command) and commit the result for reproducible builds. Without it, versions float with your vcpkg checkout.
- Triplets (`x64-linux`, `x64-windows`, `x64-windows-static`) choose architecture and linkage; set `VCPKG_TARGET_TRIPLET` and keep it the same across the team.
- Binary caching avoids rebuilding ports on CI; configure it in the CI system and do not put credentials into the repository.

## 7. Conan 2

Conan 2.x is on PyPI (2.34.0 listed at the time of writing). A minimal consumer recipe:

```ini
# conanfile.txt
[requires]
fmt/<version from conan center>

[generators]
CMakeDeps
CMakeToolchain

[layout]
cmake_layout
```

```bash
pip install conan            # or pipx install conan
conan profile detect --force
conan install . --build=missing -s build_type=Release
cmake --preset conan-release         # CMakeToolchain writes CMakeUserPresets.json
cmake --build --preset conan-release
```

- Use `find_package(fmt CONFIG REQUIRED)` and link `fmt::fmt`; CMakeDeps generates the config files.
- Lockfiles (`conan lock create`) and a `-s compiler.cppstd=23` setting make builds reproducible; profiles under version control describe compilers.
- Choose between vcpkg and Conan once per project; mixing them in one build leads to duplicate or conflicting libraries.

## 8. Install and export

Appended to the CMakeLists.txt above and tested with `cmake --install build/release --prefix <dir>`:

```cmake
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
install(TARGETS acme EXPORT acmeTargets)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT acmeTargets NAMESPACE acme:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/acme)
write_basic_package_version_file(acmeConfigVersion.cmake COMPATIBILITY SameMajorVersion)
install(FILES cmake/acmeConfig.cmake ${CMAKE_CURRENT_BINARY_DIR}/acmeConfigVersion.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/acme)
```

- Consumers then write `find_package(acme 1 CONFIG REQUIRED)` and `target_link_libraries(app PRIVATE acme::acme)`.
- If the library has dependencies, the config file must call `include(CMakeFindDependencyMacro)` and `find_dependency(fmt)` before including the targets file.
- Shared libraries: set `CXX_VISIBILITY_PRESET hidden`, `VISIBILITY_INLINES_HIDDEN ON` and use `GenerateExportHeader`; keep ABI-sensitive types out of the public interface.

## 9. import std and modules in CMake

- CMake scans C++20 sources for module dependencies (policy CMP0155, since 3.28) with Ninja and Visual Studio generators. Module interface units are declared with `target_sources(tgt PUBLIC FILE_SET CXX_MODULES FILES ...)`.
- `import std;` support is controlled by the `CXX_MODULE_STD` target property and `CMAKE_CXX_MODULE_STD` variable (3.30+). The CMake 4.4 documentation states they are only meaningful when the `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` gate is set, and that a future policy may change the default. Read the "cmake-cxxmodules" manual of the version you use for the gate value; it changes between releases.
- It needs a standard library that ships the std module (libstdc++ from GCC 15.1 per the libstdc++ status table; libc++ and MSVC STL: check their docs) and a compiler new enough to build it. This was not tested here: the local toolchain (g++ 13.3, clang 18) cannot build it.

## 10. Troubleshooting

- "Target ... requires the language dialect CXX23": the compiler is too old for the requested feature; raise the compiler or lower `cxx_std_N`.
- Stale cache: remove the build directory or run `cmake --fresh --preset <name>` (CMake 3.24+) instead of editing `CMakeCache.txt`.
- Debug configure: `cmake --trace-expand` is noisy; prefer `message(STATUS ...)` plus `cmake --debug-find` (3.17+) for `find_package` problems.
- Print what a build actually runs: `cmake --build build -- -v` (Ninja) or `cmake -DCMAKE_VERBOSE_MAKEFILE=ON`.
- Mixed standard libraries (libstdc++ and libc++) or mismatched `_GLIBCXX_USE_CXX11_ABI` across prebuilt packages give undefined-reference errors at link time; build everything with one toolchain and one profile.
