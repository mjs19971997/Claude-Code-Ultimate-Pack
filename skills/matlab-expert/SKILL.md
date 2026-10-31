---
name: matlab-expert
description: >-
  Writes, reviews and tests MATLAB code for the R2026b release: vectorisation and preallocation, arguments blocks, classdef, packages, tables and timetables, string arrays, matlab.unittest and buildtool, Code Analyzer, parfor, exportgraphics for papers, Python interop and 5G/Communications Toolbox basics. Use when editing .m, .mlx, buildfile.m or .mat files, running runtests, buildtool, codeIssues or matlab -batch, or fixing slow loops, test failures and figure export. Not for Python numerical code (use scientific-python-expert), 3GPP spec semantics (use 5g-nr-3gpp-expert), ns-3 simulations (use ns3-expert) or statistical method choice (use statistics-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# MATLAB Expert

This skill covers everyday and production MATLAB code on the R2026b line: language idioms that keep code fast and readable, input validation, object-oriented design, tabular data, the unit test framework, the build tool, static analysis, parallel loops, publication figures, Python interop and the entry points of the 5G and Communications toolboxes. It also records where GNU Octave diverges. Python numerics, protocol-specification semantics, network simulators and statistical method selection belong to other skills.

> Verified against MATLAB R2026b (release notes and release-highlights snippets, matlabengine 26.2.5 on PyPI), build tool namespace documentation, 5G Toolbox nrCarrierConfig and nrDLCarrierConfig reference pages, and GNU Octave 11.3.0 (2026-10). Items not confirmed on an official page are marked "check the current docs".

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

- Covered: the MATLAB language and the current release line, scripts versus functions, local functions, packages, `classdef`, `arguments` blocks, tables, timetables, string arrays, `dictionary`, vectorisation, preallocation, the Profiler, `parfor` and basic Parallel Computing Toolbox use, `rng`, `matlab.unittest`, `runtests`, `buildtool`, `codeIssues`, `exportgraphics`, `pyenv` and `py.*`, the MATLAB Engine for Python, the plain-text live script format, and a short orientation to 5G Toolbox and Communications Toolbox. GNU Octave limits are listed briefly.
- Not covered: NumPy, SciPy and Matplotlib code (scientific-python-expert); what a 3GPP clause requires (5g-nr-3gpp-expert); ns-3 C++ and Python scripts (ns3-expert); choosing tests, models or confidence intervals (statistics-expert); Simulink models and Embedded Coder; App Designer layout design; MATLAB Compiler deployment.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Release cadence | Two releases a year, "a" in spring and "b" in autumn. R2026b was announced in September 2026 and is the current release at the time of writing. Check the release notes page of your installed release before relying on a new function |
| R2026b highlights | MATLAB no longer bundles Java (install an OpenJDK; OpenJDK 25 is named as compatible), live scripts and live functions are created as plain text `.m` files by default (`.mlx` stays available as an option), TOML-based project files, package management through File Exchange, `markdowndisp`. A new object management system for faster `classdef` objects is described as not enabled by default. Details of the last two: check the current docs |
| Language basics | Arrays are column-major and 1-based. `end` indexing, logical indexing, implicit expansion (R2016b), local functions in scripts (R2016b), `string` arrays with double quotes, `dictionary` (R2022b), `arguments` blocks (R2019b), `rowfilter` for tables (R2022a) |
| Functions and scripts | A function file has one main function named after the file plus local functions. A script shares the caller workspace and cannot declare arguments. Prefer functions for anything reused or tested; scripts are for drivers and live notebooks |
| Packages | A folder `+pkg` on the path (its parent on the path, not the package folder) exposes `pkg.fn` and `pkg.Class`. `import pkg.*` is function-scope. Private helpers go in `+pkg/+internal` or a `private` folder |
| `classdef` | `handle` classes have reference semantics, value classes copy on assignment. Property validation syntax `x (1,1) double {mustBePositive} = 1`. `enumeration` blocks, `methods (Static)`, `events`, `matlab.mixin.*` helpers. Details: [references/language-and-performance.md](references/language-and-performance.md) |
| Tabular data | `table` for heterogeneous columns, `timetable` for time-indexed rows (`retime`, `synchronize`, `timerange`), `groupsummary`, `innerjoin`, `readtable` with `detectImportOptions`, `parquetread` and `parquetwrite` |
| Test framework | `matlab.unittest.TestCase` class tests, `functiontests(localfunctions)` function tests, `runtests`, `matlab.unittest.TestRunner`, plugins (`XMLPlugin`, `CodeCoveragePlugin`, `TestReportPlugin`), fixtures, parameterised tests, tags |
| Build tool | `buildtool` runs tasks from `buildfile.m` built with `buildplan(localfunctions)`. Built-in tasks in the `matlab.buildtool.tasks` namespace (since R2023b): `CleanTask`, `CodeIssuesTask`, `MexTask`, `PcodeTask`, `TestTask`. Tasks can be run from the Toolstrip since R2025a |
| Code Analyzer | `codeIssues` (R2022b) returns a queryable object and is recommended over `checkcode`; `codeAnalyzer` opens the report app. `CodeIssuesTask` fails the build on error-level issues |
| Parallel | `parfor`, `parfeval`, `parpool("Processes")` and `parpool("Threads")`, `backgroundPool`, `parallel.pool.Constant`, `spmd`, `gpuArray`. `parfor` runs serially without Parallel Computing Toolbox |
| Reproducibility | `rng(seed, "twister")` seeds the default generator. Inside `parfor` use independent streams (`RandStream("Threefry")` with `Substream`); see [references/toolboxes-and-interop.md](references/toolboxes-and-interop.md) |
| Figures | `exportgraphics(fig_or_axes, file, ContentType="vector")` for PDF and EPS, `Resolution=300` for raster, `tiledlayout` for multi-panel figures. Details: [references/figures-and-export.md](references/figures-and-export.md) |
| Python interop | `pyenv`, `py.module.fn(...)`, `pyrun`, `pyrunfile`, `pyargs`; Python side `import matlab.engine`. Install the engine with `python -m pip install matlabengine`; the newest engine targets only the newest MATLAB release, pin an older one by version. Details: [references/toolboxes-and-interop.md](references/toolboxes-and-interop.md) |
| Toolboxes | 5G Toolbox: `nrCarrierConfig` (carrier numerology and grid size), `nrDLCarrierConfig` and `nrWaveformGenerator` (full downlink waveform). Communications Toolbox: modulation, channel and error-rate objects. Both are separately licensed |
| Octave | Octave 11.3.0 (June 2026) is the latest release found. It lacks `arguments` blocks, the `string` class, `table` and `timetable` natively, live scripts and the `matlab.unittest` framework; classdef support is partial |

## 3. Workflow

1. Identify the MATLAB release the code must run on (`ver`, `version`, project README, CI image) and the toolboxes required (`license("test", "Statistics_Toolbox")`, `matlab.addons.toolbox.installedToolboxes`). Do not use functions newer than the oldest supported release.
2. Read the repository layout first: `buildfile.m`, `.prj` or project file, `tests/`, `+pkg` folders, `startup.m`. Keep the existing conventions.
3. Reproduce the problem from the command line the same way CI does: `matlab -batch "buildtool test"` or `matlab -batch "runtests('tests')"`. A GUI-only reproduction hides path and state issues.
4. For slowness, profile before editing (`profile on`, run, `profile viewer`, or `timeit` on one function). Change the top hot spot only, then measure again.
5. Make the smallest change. Add `arguments` validation to functions you touch and a test that fails without the change.
6. Run `codeIssues` on the changed folder and fix new warnings, then run the full test suite.
7. Report the commands run, the release used and any function that needs a toolbox the reader may not have.

## 4. Decision Rules

- If code will be reused or tested, write a function file; use a script only for a top-level driver, and give it `clear` and `close all` only when it truly owns the session.
- If an operation has a built-in vector form (`sum`, `cumsum`, `max`, `vecnorm`, `pagemtimes`, implicit expansion), use it; if the loop body is heavy and iterations are independent, use `parfor` instead of rewriting the maths.
- If an array grows in a loop, preallocate with `zeros`, `nan`, `strings(n,1)`, `cell(n,1)` or `repmat`; if the final size is unknown, collect in a cell array and concatenate once.
- If columns have different types or names matter, use `table`; if rows are time stamped and need resampling, use `timetable`; if everything is one numeric type and indexed by position, use a matrix.
- If a function takes more than two inputs, or optional name-value pairs, use an `arguments` block rather than `varargin` parsing or `inputParser` (keep `inputParser` for code that must run before R2019b).
- If state is shared and mutable (a cache, a connection, a simulation clock), use a `handle` class; if it is a value (a configuration, a result), use a value class or a `struct`.
- If text is processed, use `string` arrays and functions such as `contains`, `split`, `strip`; keep `char` only at API boundaries that require it.
- If a test depends on random numbers, set `rng` in `TestMethodSetup` or use fixed expected values with tolerances; never compare floats with exact equality.
- If a figure goes into a paper, export vector PDF from `exportgraphics`; if it contains tens of thousands of points or an image, export raster at 300 dpi or more, or rasterise only that layer.
- If the code must also run on Octave, avoid `arguments`, `string`, `table`, `dictionary` and `classdef` features outside Octave's support; otherwise do not constrain MATLAB code for Octave.
- If a statistical decision (test choice, correction, power) is being made, hand off to statistics-expert; this skill only covers how to call the functions.

## 5. Coding Standards

- One main function per file, file name equals function name. Local functions go after the main function. Name functions and variables `lowerCamelCase` or `snake_case` consistently within a repo; classes and packages follow the repo (`PascalCase` classes, lowercase packages are common).
- Start every function with a help comment (first block of `%` lines after the signature) that has a one-line summary, then inputs and outputs. The first line feeds `help` and `lookfor`.
- Declare inputs with an `arguments` block: size, class, validators and defaults, for example `x (:,1) double {mustBeFinite}` and `opts.Tol (1,1) double {mustBePositive} = 1e-6`. Name-value arguments live in a `struct` in the block (`opts`).
- Use double-quoted strings for new code (`"text"`), `string` functions for manipulation, and `char` only when an API demands it. Concatenate strings with `+`.
- Use `numel`, `size(x, dim)` and `height`/`width` instead of `length`, which is ambiguous for matrices.
- Use `&&` and `||` in `if` and `while` conditions; use `&` and `|` for element-wise logic. Use `isempty`, `isscalar`, `isrow` for shape tests.
- Do not shadow built-ins (`sum`, `max`, `length`, `table`, `i` as a loop index when complex numbers are used). Check with `which name -all` or the Code Analyzer.
- Terminate statements with a semicolon unless output is wanted. Use `fprintf` or `disp` for output, `warning("pkg:id", "text %s", x)` and `error("pkg:id", ...)` with an identifier so callers and tests can match it.
- Keep lines under 120 characters. Use `...` for continuation. Close every `function` with `end` in files that use local functions.
- Do not use `eval`, `evalin`, `assignin`, `global` or `clear all` in library code. Use `feval` or function handles instead of building function names in strings.
- Test struct fields with `isfield`, variables with `exist("name", "var")` only when unavoidable, and never grow variables inside `parfor`.

## 6. Project Structure

```text
channel-sim/
|-- buildfile.m              # buildtool tasks: check, test
|-- startup.m                # optional; keep it free of side effects beyond path
|-- src/
|   |-- +chan/               # package: chan.fadingLoss, chan.Link
|   |   |-- fadingLoss.m
|   |   `-- Link.m           # classdef
|   `-- private/             # helpers visible only to files in src/
|-- tests/
|   |-- FadingLossTest.m     # class-based test
|   `-- fixtures/            # small .mat or .csv test data
|-- scripts/
|   `-- runSweep.m           # drivers, not reused elsewhere
|-- data/                    # inputs; large files are not committed
|-- results/                 # generated output; ignored by version control
`-- README.md
```

- Add `src` to the path from `startup.m`, a MATLAB project, or `addpath` in `buildfile.m`; never rely on the current folder to find code.
- Keep generated files (`.asv`, `slprj`, `*.mex*`, `results/`) out of version control. Plain-text live scripts (`.m`) diff cleanly; the `.mlx` format is a zip container, so review changes through the editor's comparison tool.
- A MATLAB project (`openProject`) records path entries, startup and shutdown tasks and file classification. R2026b adds a TOML-based project file format; check the current docs before converting existing projects.
- Separate pure computation (functions in `src`) from I/O and plotting so computation can be tested without a display.

## 7. Design Patterns

- **Validated function boundary**: an `arguments` block at the top of each public function, with local validation functions for repeated rules. Cost: slightly slower call overhead in very hot inner functions; validate once at the public boundary and call unvalidated local helpers inside.
- **Configuration struct or value class**: pass one options object, not ten positional arguments. A value class with property validation gives defaults, types and sizes in one place.
- **Handle class for resources**: files, serial ports, database connections, and parallel constants. Implement a `delete` method for cleanup and prefer `onCleanup` objects inside functions.
- **`onCleanup`**: `c = onCleanup(@() fclose(fid));` releases a resource when the function exits, including on error.
- **Function handles and closures**: `f = @(x) x.^2 + k` captures `k` by value at creation. Pass handles to `fzero`, `integral`, `arrayfun` and `cellfun` rather than strings.
- **Table-driven tests and sweeps**: build a `table` of parameter combinations (`combinations(a, b)`, check the release that introduced it) and loop or `parfor` over rows.
- **Package namespaces**: group related functions under `+pkg` and call with `pkg.fn`, avoiding name collisions across projects.
- **Separation of simulation and analysis**: run Monte Carlo into a `results` struct saved with `save(..., "-v7.3")` if above 2 GB, and make plotting a separate function that loads results.

## 8. Best Practices

- Keep functions short and side-effect free; return values rather than writing to the base workspace.
- Prefer `readtable`, `readmatrix`, `writetable`, `jsonencode`, `jsondecode` and `parquetread` to hand-written parsing; set `detectImportOptions` explicitly and pin the types for columns that matter.
- Use `datetime` and `duration` instead of date numbers and strings; give timetables a named row-time variable and explicit time zones where data cross regions.
- Use categorical arrays for repeated labels and `string` for free text; convert with `categorical`, `string`, `cellstr` at boundaries.
- Seed random generators once per experiment (`rng(42, "twister")`), record the seed and release in the results, and never reseed inside inner loops.
- Use `tiledlayout` and `nexttile` for subplots, `exportgraphics` for files, and set fonts and sizes once in a plotting function instead of per figure.
- Store text data as UTF-8; pass `Encoding="UTF-8"` to `readtable`, `fopen` and `writelines` when the source is not guaranteed to match the system locale.
- Use relative paths built with `fullfile` and `mfilename("fullpath")` or `fileparts`; never hard-code drive letters or user directories.
- Use `validateattributes` or `arguments` blocks, not ad-hoc `if ~isnumeric` chains, and `assert` only for internal invariants.
- Check toolbox availability explicitly and fail with a clear identifier (`error("sim:needsToolbox", ...)`).

## 9. Performance

- Measure first: `tic`/`toc` for coarse timing, `timeit(@() f(x))` for a single call (it warms up and takes a median), the Profiler for call trees, and `profile("info")` to read results programmatically. Optimise the top line only.
- Preallocate every array that is filled in a loop. A loop that grows `y(end+1) = v` is quadratic; use `y = zeros(n, 1)` or a cell array and one `vertcat`.
- Vectorise operations over whole arrays; use implicit expansion in place of `repmat` and `bsxfun`; use `pagemtimes` for batched matrix products; use logical indexing in place of `find` plus indexing.
- Do not append rows to a `table` in a loop; collect into arrays or cell arrays and build the table once. Table indexing is slower than matrix indexing in tight loops; extract columns to arrays first.
- `arrayfun` and `cellfun` are not always faster than a loop; the JIT compiles simple loops well. Use them for clarity, benchmark when it matters.
- Use column vectors consistently (column-major memory), avoid unnecessary copies of large arrays (modify in a function with the same variable on both sides to allow in-place update), and clear large temporary variables.
- `parfor` pays off when each iteration takes much longer than its data transfer; broadcast large read-only data once with `parallel.pool.Constant`. Thread-based pools avoid copying data but support only a subset of functions; check the docs for the function in question.
- `gpuArray` helps with large dense arrays and element-wise maths; transfers dominate for small arrays. Time with `gputimeit`.
- `fprintf` in a hot loop and graphics updates (`drawnow`, `plot` inside loops) are common bottlenecks; update `XData`/`YData` of an existing line, and call `drawnow limitrate`.
- Memory: `whos`, `memory` (Windows only), `tall` arrays and `datastore` for data larger than RAM, `matfile` for partial loading of v7.3 files.
- R2026b notes a faster object implementation that is off by default; benchmark on your workload and check the docs before enabling it in shared code.

## 10. Security

- Do not pass untrusted text to `eval`, `evalin`, `feval` with a string name, `str2func`, `str2num` (it calls `eval`; use `str2double`), `run`, `load` of a code-bearing file, or `pyrun` code strings. Parse data with `jsondecode`, `readtable` or `str2double`.
- `load` of an untrusted `.mat` file may instantiate objects and run class load callbacks. Load only trusted files, or restrict with `load(file, "name")` and `whos("-file", file)` first.
- Build shell commands with care: `system(cmd)` runs through a shell. Do not interpolate user input; prefer a MATLAB function, `pyrun`, or validate the argument against an allow-list.
- Do not store credentials in `.m` files, `.mat` files, live scripts (outputs are saved with the file) or project files. Read them from `getenv` or an external secret manager; check the current docs for any built-in secret storage.
- Clear outputs from live scripts and notebooks before sharing: embedded output can include paths, tokens and personal data.
- `webread`, `webwrite` and `websave` use TLS by default; keep certificate checks on, set `weboptions("Timeout", 30)`, and do not disable verification to silence an error.
- Path hijacking: a file named like a built-in earlier on the path shadows it. Keep the path explicit, avoid `addpath(genpath(pwd))` on untrusted folders, and check `which -all name`.
- Validate file names from users with `fullfile` and compare against a base folder before opening; check `fileparts` output for `..` components.
- A shared MEX or compiled `.p` file executes native code with your privileges; obtain it from a trusted build and verify checksums in CI.
- Use fixed seeds only for reproducibility; for tokens or keys use an operating-system or Java/Python secure random source, not `rand`.

## 11. Testing

- Class-based tests (`classdef MyTest < matlab.unittest.TestCase`, tests in `methods (Test)`) support setup and teardown, parameters, fixtures and tags. Function-based tests (`functiontests(localfunctions)`) suit small utilities.
- Run with `runtests("tests")` or `runtests("tests", IncludeSubfolders=true)`; add `Tag="fast"` to filter. Use `results = runtests(...); assertSuccess(results)` in scripts so failures stop the process with an error.
- Choose the narrowest qualification: `verify*` records a failure and continues, `assert*` stops the test, `assume*` filters the test as incomplete, `fatalAssert*` aborts the whole run.
- Floating point: `testCase.verifyEqual(actual, expected, AbsTol=1e-12)` or `RelTol`; never exact equality on computed doubles. Errors: `testCase.verifyError(@() f(-1), "pkg:badInput")`.
- Use `matlab.unittest.fixtures.TemporaryFolderFixture` for files and `PathFixture` for path changes; apply with `testCase.applyFixture(...)` so teardown is automatic.
- Parameterised tests: a `properties (TestParameter)` block plus test method arguments creates one test per value, with names in the report.
- CI: `matlab -batch "buildtool test"` exits non-zero on failure. Produce JUnit XML with `XMLPlugin.producingJUnitFormat` and Cobertura coverage with `CodeCoveragePlugin.forFolder(..., Producing=CoberturaFormat(...))`.
- Keep graphics out of tests: create figures with `Visible="off"`, close them in teardown (`testCase.addTeardown(@close, fig)`), and test computation separately from plotting.
- Test the failure path (invalid input identifiers) and boundary values (empty input, scalar, NaN, single row), not only the happy path. Full recipes: [references/testing-and-build.md](references/testing-and-build.md).

## 12. Review Checklist

- [ ] Every public function has a help comment and an `arguments` block; no new `varargin` parsing where an `arguments` block fits.
- [ ] No growing arrays in loops; large loops are vectorised or preallocated; any performance claim has a Profiler or `timeit` result.
- [ ] No `eval`, `evalin`, `assignin`, `global`, `clear all` or `str2num` in library code.
- [ ] `error` and `warning` calls carry identifiers; tests match identifiers, not message text.
- [ ] `codeIssues` reports no new warnings on changed files; `buildtool` passes.
- [ ] Random code seeds with `rng` at the experiment level and records the seed; parallel code uses independent streams.
- [ ] Floating-point comparisons use tolerances.
- [ ] Figures export with `exportgraphics` at a defined size, vector for line art, with fonts at publication size.
- [ ] Paths are built with `fullfile`; no absolute or user-specific paths.
- [ ] Required toolboxes and the minimum release are documented; functions newer than the minimum release are not used.
- [ ] Credentials, personal data and large outputs are not stored in code, live scripts or `.mat` files in the repository.
- [ ] Python or Java interop calls state the required interpreter or runtime version.

## 13. Production Notes

- Run unattended jobs with `matlab -batch "statement"`; it starts without the desktop, exits when the statement completes, and returns a non-zero code on error. Put long statements in a function and call that.
- Pin the release in CI and in the README; MATLAB code is not forward or backward compatible across every function. Read the compatibility considerations in each release notes page when upgrading.
- R2026b no longer bundles Java. Code using `java.*` classes, `javaaddpath`, or toolboxes that rely on Java needs an installed OpenJDK; check the documentation for how MATLAB locates the runtime and test early.
- Licence use: `batch` and `parfor` consume Parallel Computing Toolbox licences and workers. Check `license("checkout", ...)` behaviour on shared servers and release pools with `delete(gcp("nocreate"))`.
- Log with `fprintf` to a file or `diary`, and write results with `save(file, "-v7.3")` when variables exceed 2 GB. Write temporary output to `tempname` folders and clean up with `onCleanup`.
- Deployment: MATLAB Compiler and the Engine are separate topics; for a Python caller prefer the Engine for interactive use and compiled packages for servers without MATLAB. Check the current docs for the supported Python versions per release (R2026a listed Python 3.9 to 3.13; confirm the R2026b row).
- Live scripts: the default is plain text `.m` in R2026b; if teammates use older releases, agree on one format and set it in the preferences. The text markers and trailing appendix are written by MATLAB and are not meant for hand edits.
- Octave fallback: for batch use without a licence, Octave 11.x can run plain numeric scripts; run the test suite on it only if the project promises compatibility.

## 14. Examples

A validated function with a name-value options block (R2019b or later):

```matlab
function y = movingRms(x, win, opts)
%MOVINGRMS Root mean square over a sliding window.
%   y = movingRms(x, win) returns a column vector the size of x.
%   y = movingRms(x, win, Endpoints="discard") drops partial windows.
    arguments
        x (:,1) double {mustBeFinite}
        win (1,1) double {mustBeInteger, mustBePositive}
        opts.Endpoints (1,1) string {mustBeMember(opts.Endpoints, ["shrink", "discard"])} = "shrink"
    end
    y = sqrt(movmean(x.^2, win, Endpoints=opts.Endpoints));
end
```

Preallocation and a vectorised alternative:

```matlab
n = 1e6;
a = zeros(n, 1);               % preallocated
for k = 1:n
    a(k) = sin(k) / k;         % simple loop body
end

k = (1:n).';                   % vectorised: same result, one expression
b = sin(k) ./ k;
assert(isequal(a, b) || max(abs(a - b)) < 1e-12)

[r, c] = ndgrid(1:3, 1:4);     % implicit expansion replaces repmat/bsxfun
M = r .* 10 + c;
```

A class-based test with a parameter and an error check:

```matlab
classdef MovingRmsTest < matlab.unittest.TestCase
    properties (TestParameter)
        win = {1, 3, 5}
    end
    methods (Test)
        function constantSignal(testCase, win)
            y = movingRms(ones(10, 1) * 2, win);
            testCase.verifyEqual(y, ones(10, 1) * 2, AbsTol=1e-12);
        end
        function rejectsNonInteger(testCase)
            testCase.verifyError(@() movingRms((1:10).', 2.5), ?MException);
        end
    end
end
```

A `buildfile.m` with analysis and tests (tasks from the `matlab.buildtool.tasks` namespace):

```matlab
function plan = buildfile
    plan = buildplan(localfunctions);
    plan("check") = matlab.buildtool.tasks.CodeIssuesTask;
    plan("test") = matlab.buildtool.tasks.TestTask("tests");
    plan("test").Dependencies = "check";
    plan.DefaultTasks = "test";
end

function cleanTask(~)
    % Local function ending in "Task" becomes a task named "clean".
    if isfolder("results")
        rmdir("results", "s");
    end
end
```

Parallel Monte Carlo with reproducible, independent streams:

```matlab
nTrials = 200;
ber = zeros(nTrials, 1);
parfor t = 1:nTrials
    s = RandStream("Threefry", Seed=7);
    s.Substream = t;                 % independent substream per trial
    bits = rand(s, 1e4, 1) > 0.5;
    ber(t) = mean(xor(bits, rand(s, 1e4, 1) > 0.99));
end
```

Exporting a paper figure:

```matlab
fig = figure(Units="centimeters", Position=[2 2 8.5 6]);
plot(0:0.1:10, sin(0:0.1:10), LineWidth=1.2);
xlabel("Time (s)"); ylabel("Amplitude");
exportgraphics(fig, "sine.pdf", ContentType="vector");
exportgraphics(fig, "sine.png", Resolution=300);
```

## 15. Common Mistakes

- **Growing arrays in a loop** (`y(end+1) = v`, `T = [T; row]`): quadratic copies. Preallocate or collect in a cell array.
- **Using `length` on a matrix**: returns the largest dimension. Use `numel`, `size(x, 1)` or `height`.
- **Comparing doubles with `==` or `isequal`** after arithmetic: use `abs(a - b) < tol` or `verifyEqual` with `AbsTol`/`RelTol`.
- **Shadowing a built-in** (`sum = 0;`, `max = ...`, a file named `table.m`): later calls fail with confusing errors. Rename and run `which -all`.
- **`&&` or `||` on arrays** in an `if`: errors or hides cases. Use `all(...)`/`any(...)` or element-wise `&`.
- **Treating `parfor` like `for`**: iterations must be independent and loop variables must be sliced or reduction variables. Dependencies between iterations give an analysis error or wrong results.
- **Calling `rng(seed)` inside a `parfor` body expecting global reproducibility**: workers have their own generators. Use per-iteration `RandStream` substreams.
- **`str2num` on external text**: it evaluates code. Use `str2double`.
- **`saveas` for publication figures**: depends on the renderer and screen size. Use `exportgraphics` and fix the figure size.
- **`jet` colormap or default red-green pairs in figures**: misleading in print and for colour-blind readers. Use `parula`, `turbo` with care, or a sequential map, and vary line style.
- **Forgetting that scripts share the caller workspace**: variables leak between scripts. Convert to a function.
- **Calling `pyenv` after Python was loaded**: the setting is ignored or errors. Call it first in a fresh session, or restart MATLAB.
- **Assuming the `matlabengine` in `pip` matches the installed MATLAB**: the newest wheel targets the newest release. Pin the version that matches the MATLAB you run.
- **Putting the `+pkg` folder itself on the path**: put its parent on the path.
- **Using `checkcode` output only in the editor**: CI sees nothing. Use `codeIssues` or `CodeIssuesTask` in the build.
- **Assuming Octave runs the same code**: `arguments` blocks, `string`, `table` and many toolbox functions are missing or differ.

## 16. References

- [references/language-and-performance.md](references/language-and-performance.md): vectorisation, preallocation, implicit expansion, arguments blocks, classdef, packages, tables and timetables, string arrays, dictionary, Profiler, parfor.
- [references/testing-and-build.md](references/testing-and-build.md): matlab.unittest classes and fixtures, runtests and TestRunner plugins, buildtool and buildfile.m, codeIssues, matlab -batch in CI.
- [references/figures-and-export.md](references/figures-and-export.md): exportgraphics options, figure sizing, tiledlayout, fonts, colour maps, vector versus raster, reproducible plots.
- [references/toolboxes-and-interop.md](references/toolboxes-and-interop.md): 5G Toolbox carrier and waveform objects, Communications Toolbox basics, rng and Monte Carlo, parallel streams, pyenv, py.* calls, pyrun, data conversion, MATLAB Engine for Python, live script text format, Octave compatibility limits.
- MATLAB documentation: https://www.mathworks.com/help/matlab/ and release notes https://www.mathworks.com/help/matlab/release-notes.html
- Build tool: https://www.mathworks.com/help/matlab/matlab_prog/overview-of-matlab-build-tool.html ; Code Analyzer `codeIssues`: https://www.mathworks.com/help/matlab/ref/codeissues.html
- 5G Toolbox: https://www.mathworks.com/help/5g/ ; MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab-engine-for-python.html
- GNU Octave: https://octave.org/ and its news page https://octave.org/news.html
