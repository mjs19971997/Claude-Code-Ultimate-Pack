# Building and Running ns-3

The `ns3` CMake wrapper, build profiles, module selection, adding scratch programs and contrib modules, running with arguments and debuggers, and the usual build failures. Checked against the ns-3.49 sources (`ns3` script, `CMakeLists.txt`, `build-support/macros-and-definitions.cmake`, release notes) in 2026-10.

## Contents

1. [Requirements and obtaining the source](#1-requirements-and-obtaining-the-source)
2. [The ns3 script](#2-the-ns3-script)
3. [Build profiles and feature switches](#3-build-profiles-and-feature-switches)
4. [Choosing modules](#4-choosing-modules)
5. [Adding programs and modules](#5-adding-programs-and-modules)
6. [Running programs](#6-running-programs)
7. [Debugging](#7-debugging)
8. [Python bindings](#8-python-bindings)
9. [Build problems and fixes](#9-build-problems-and-fixes)

## 1. Requirements and obtaining the source

- ns-3.49 release notes list: g++ 11.1 or later or clang++ 17 or later, CMake 3.25 or later, Python 3.10 or later; macOS needs Xcode 16.3 or later; Windows is supported through Msys2, ClangCL/MSVC or WSL2. Linux is the primary platform.
- The default C++ standard is C++23 (default since ns-3.46; `CMAKE_CXX_STANDARD_MINIMUM` is 23 in the 3.49 `CMakeLists.txt`). A project that needs an older standard cannot simply lower it; check `./ns3 configure --help` before overriding `--cxx-standard`.
- Get the source from Git, not from a distribution package, so the version is pinned and reviewable:

```bash
git clone https://gitlab.com/nsnam/ns-3-dev.git
cd ns-3-dev
git checkout -b ns-3.49 ns-3.49        # release tags are named ns-3.NN
./ns3 show version                     # confirms what is checked out
```

- Release tarballs are also published on https://www.nsnam.org/ (the site was not reachable from the verification environment, so release dates in this skill come from GitLab tags).
- `ns-3-dev` master is the development line. Use a tag for experiments and record the tag or commit hash with the results.

## 2. The ns3 script

`./ns3` is a Python wrapper over CMake. It keeps the build tree in `cmake-cache/` and the outputs in `build/`.

| Command (alias) | Purpose |
|---|---|
| `./ns3 configure` (`cfg`) | Run CMake; options below |
| `./ns3 build [targets]` (`bld`) | Build everything or named targets (`./ns3 build scratch/my-sim`) |
| `./ns3 run <target>` (`run`) | Build, then run; arguments for the program follow `--` or sit in one quoted string |
| `./ns3 clean` / `distclean` | Remove build products / also tests and docs artifacts |
| `./ns3 show profile`, `version`, `config`, `targets`, `all`, `typeid <tid>` | Inspect the configuration; `typeid` prints the introspected attributes of a TypeId |
| `./ns3 shell` | Shell with the library and Python paths exported |
| `./ns3 docs <manual\|models\|tutorial\|doxygen\|...>` | Build documentation |

Global options: `-j N` (parallel jobs), `--dry-run` (print commands), `-v` (show executed commands), `--quiet`.

```bash
./ns3 configure -d optimized --enable-examples --enable-tests
./ns3 build -j 4
./ns3 show targets | grep -i flow
./ns3 show typeid ns3::PointToPointNetDevice
```

- `./ns3 configure` remembers its options. A later `./ns3 configure --enable-tests` keeps the earlier switches unless they are overridden; `--force-refresh` rebuilds the CMake cache and keeps settings.
- Re-run `./ns3 configure` after adding a source file to a module or `contrib` directory, and after editing a module `CMakeLists.txt`. The script records the list of `scratch/` sources and reconfigures by itself when that list changes.

## 3. Build profiles and feature switches

`./ns3 configure -d <profile>` (long form `--build-profile`) accepts `debug`, `default`, `release`, `optimized`, `minsizerel`.

| Profile | Use |
|---|---|
| `default` | The profile used when none is given: asserts and logging on, size-optimised code with debug info; fine for development |
| `debug` | No optimisation, full debug info, asserts and logs on; for gdb sessions |
| `release` | Optimised (CMake Release); asserts and logs off unless switched on with `--enable-asserts` / `--enable-logs`; portable binaries |
| `optimized` | `release` plus `-march=native -mtune=native` (`NS3_NATIVE_OPTIMIZATIONS`); fastest, but the binaries may not run on a different CPU model |
| `minsizerel` | Smallest binaries |

- Inspect the active profile with `./ns3 show profile`; the profile and its switches decide what `NS_LOG` can print. Check the installation chapter of the manual for the exact flags of each profile.
- Production sweeps use `release` (or `optimized` when every job runs on the same CPU model). Verify one run from the `default` build and one from the sweep build give the same output for the same seed and run; a difference points to code with side effects inside `NS_ASSERT` or `NS_LOG` expressions.
- Logging and asserts are compile-time options (`NS3_LOG`, `NS3_ASSERT`, both OFF by default in CMake); the `default` and `debug` profiles switch them on.
- Feature switches follow `--enable-X` / `--disable-X`: `asserts`, `logs`, `examples`, `tests`, `mpi`, `python-bindings`, `eigen`, `sanitizers`, `warnings`, `werror`, `static`, `precompiled-headers`, `monolib`, `build-version`, among others. `./ns3 configure --help` lists the current set.
- `--enable-sanitizers` builds with the address and undefined-behaviour sanitizers; use it for a debug build when hunting memory errors, not for timing runs.
- Examples and tests are off by default. Turn them on only when needed; they multiply build time.

## 4. Choosing modules

- Build only what the scenario uses: `./ns3 configure --enable-modules "core;network;internet;point-to-point;applications;flow-monitor;mobility"` (semicolon separated, quote it for the shell). `--disable-modules` removes some. A contrib module such as `nr` is enabled automatically when its directory is present, unless the module lists exclude it.
- A smaller build changes nothing in results; it only saves compile time. Dependencies of the listed modules are pulled in.
- `--filter-module-examples-and-tests "nr"` limits examples and tests to the named modules, which keeps `--enable-examples` affordable.
- `./ns3 show targets` lists every buildable target, including module libraries (`libcore`, `libnr`) and each example. Library targets are built with `./ns3 build <lib>` and cannot be run.
- The `wimax` module was removed in ns-3.46 and lives in the ns-3 App Store. Check the release notes before relying on an older module.
- Optional dependencies (Eigen3 for nr MIMO, SQLite for nr traces and realistic beamforming, GSL, GTK, MPI) are detected at configure time; read the "Optional features" lines in the configure output and fix a missing library before building.

## 5. Adding programs and modules

Single-file programs go in `scratch/`:

```text
ns-3-dev/
  scratch/
    my-sim.cc                 # becomes target scratch/my-sim (or my-sim)
    my-study/                 # a directory: all .cc files are one program
      CMakeLists.txt          # optional; main file must define main()
      my-study.cc
      helper.cc
```

```bash
./ns3 build scratch/my-sim
./ns3 run scratch/my-sim
```

- Names are derived from the file or directory name; two scratch programs with the same base name collide.
- Do not edit ns-3 source tree files for study code. Keep the study in its own Git repository and copy or link it into `scratch/`, or write it as a contrib module.
- A contrib module lives in `contrib/<name>/` with `model/`, `helper/`, `examples/`, `test/` and a `CMakeLists.txt` that calls `build_lib(LIBNAME <name> SOURCE_FILES ... HEADER_FILES ... LIBRARIES_TO_LINK ...)`. Copy the structure of an existing small module (`src/` or `contrib/`) and run `./ns3 configure` again. The helper `utils/create-module.py` generates a skeleton: `python3 utils/create-module.py contrib/my-module`.
- Third-party header-only libraries can go in `third-party/` (supported since 3.49).
- Headers are included as `"ns3/<module>-module.h"` (whole module) or `"ns3/<header>.h"` (single header).

## 6. Running programs

```bash
./ns3 run scratch/my-sim                              # no program arguments
./ns3 run "scratch/my-sim --simTime=10s --rate=5Mbps"  # one quoted string
./ns3 run scratch/my-sim -- --simTime=10s              # after a double dash
./ns3 run scratch/my-sim --no-build -- --RngRun=3      # skip the build step
./ns3 run scratch/my-sim --cwd=/path/to/outdir -- --simTime=10s
./ns3 run scratch/my-sim --command-template="%s --RngRun=3"
```

- `--no-build` is the right choice inside sweep loops: build once, then launch many runs without CMake checks.
- `--cwd` sets the working directory, so relative output files (PCAP, XML, `.db`) land in a chosen run directory and the source tree stays clean.
- The binaries live under `build/`, with names like `build/scratch/ns3.49-my-sim-default` (the suffix is the profile). For batch systems, call the binary directly after `./ns3 shell` or after exporting `LD_LIBRARY_PATH=$PWD/build/lib`; check `./ns3 show config` for the real paths.
- Program arguments: `--PrintHelp`, `--PrintAttributes=ns3::TypeId`, `--PrintGlobals`, `--PrintTypeIds`, `--PrintGroups`, `--PrintGroup=name`, `--PrintVersion` come from `CommandLine`; see [tracing-and-output.md](tracing-and-output.md) and [reproducible-experiments.md](reproducible-experiments.md).
- Environment variables read at run time: `NS_LOG` (logging), `NS_GLOBAL_VALUE` (globals such as `RngRun`, `SimulatorImplementationType`), `NS_ATTRIBUTE_DEFAULT` (attribute defaults). Prefer explicit command-line values in scripts and record them.
- Run inside a container or with a pinned toolchain when results must be repeatable across machines; floating-point results can differ with compiler version and flags.

## 7. Debugging

```bash
./ns3 configure -d debug --enable-sanitizers
./ns3 build
./ns3 run scratch/my-sim --gdb -- --simTime=1s
./ns3 run scratch/my-sim --valgrind -- --simTime=1s
```

- `--gdb`, `--lldb`, `--valgrind`, `--perf`, `--heaptrack` wrap the run; the first three need the debuggers installed.
- Assertions (`NS_ASSERT`, `NS_ABORT_IF`, `NS_FATAL_ERROR`) print the failing expression and the file and line; a failing `NS_ASSERT` exists only in builds with asserts enabled.
- Turn on the component log (`NS_LOG="Component=level_all|prefix_time"`) near the failure and read the sequence of calls before attaching a debugger.
- `Simulator::Now()` and `Simulator::GetContext()` help locate which event and node triggered a problem. A crash after `Simulator::Run()` often means a callback or trace sink outlived an object; call `Simulator::Destroy()` and disconnect or scope sinks properly.
- Memory growth in long runs usually comes from unbounded containers in application code or from per-packet tracing kept in memory; profile with `--heaptrack` before blaming the simulator.

## 8. Python bindings

- ns-3.49 Python bindings use cppyy (release notes: cppyy 3.5.0 or later, Python 3.10 or later, tested on Linux only). Enable with `./ns3 configure --enable-python-bindings`, then `./ns3 run first.py`-style scripts or `./ns3 shell`.
- The bindings suit small scripts and teaching. C++ remains the main route for large scenarios: more modules, every helper, and no wrapper overhead. Many trace callbacks and `Config` paths are easier to get right in C++.
- A Python script is not a substitute for a C++ model: custom models, schedulers and traced values still need C++.
- Check the manual's Python chapter for supported helpers before porting an example; the nr module's examples are C++.

## 9. Build problems and fixes

| Symptom | Likely cause and fix |
|---|---|
| `CMake 3.25 or higher is required` | Old distribution CMake; install a newer one (`pip install cmake`, a distribution backport) |
| Compiler too old or `-std=c++23` unsupported | Install g++ 11.1+ (newer is safer for C++23) or clang 17+, then `./ns3 configure --force-refresh` |
| New file in `scratch/` or a module not built | Run `./ns3 configure` after adding files to a module (scratch changes are detected by the script) |
| `Target "x" not found` | `./ns3 show targets` to see names; scratch targets use the file name without extension |
| Module missing at link time | The module was not in `--enable-modules`, or a needed dependency is disabled; reconfigure with the module |
| Everything rebuilds after `configure` | Profile or feature switches changed; keep them stable between runs |
| `NS_LOG` prints nothing | Release or optimized build without `--enable-logs`, or a wrong component name; check `./ns3 show profile` and `./ns3 show config` |
| Different results on two machines | Different compilers or flags, library versions, seeds, or run numbers; compare `./ns3 show config` output and the recorded versions |
| nr build errors after updating ns-3 | nr release and ns-3 release do not match; see [nr-5g-lena.md](nr-5g-lena.md) |
| Out of memory while linking | Lower `-j`, enable a fast linker (`NS3_FAST_LINKERS` defaults to ON when mold or lld exist), build fewer modules |

- Keep `build/` and `cmake-cache/` out of version control. After a failed or mixed build, `./ns3 clean` and a fresh `./ns3 configure` resolves most stale-state problems.
- Parallel builds use RAM: about 1 to 2 GB per job for heavy modules such as `wifi`, `lte` and `nr`.
