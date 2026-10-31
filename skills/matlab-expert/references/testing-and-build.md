# Testing, Build Tool and Code Analysis

The MATLAB unit test framework, `runtests`, `matlab.unittest.TestRunner` plugins, `buildtool` with `buildfile.m`, `codeIssues`, and running all of it in CI with `matlab -batch`. API names below belong to long-standing `matlab.unittest` and to the `matlab.buildtool` namespace (introduced R2023b); the task classes were confirmed in the namespace reference, and option names that were not should be checked in the current docs.

## Contents

1. [Class-based tests](#1-class-based-tests)
2. [Function-based and script-based tests](#2-function-based-and-script-based-tests)
3. [Qualifications and constraints](#3-qualifications-and-constraints)
4. [Fixtures, parameters and tags](#4-fixtures-parameters-and-tags)
5. [runtests and TestRunner](#5-runtests-and-testrunner)
6. [Build tool and buildfile.m](#6-build-tool-and-buildfilem)
7. [Code Analyzer](#7-code-analyzer)
8. [CI with matlab -batch](#8-ci-with-matlab--batch)
9. [Projects and path control](#9-projects-and-path-control)

## 1. Class-based tests

```matlab
classdef ChannelTest < matlab.unittest.TestCase
    properties
        Link
    end
    methods (TestClassSetup)
        function addSource(testCase)
            root = fileparts(fileparts(mfilename("fullpath")));
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture(fullfile(root, "src")));
        end
    end
    methods (TestMethodSetup)
        function makeLink(testCase)
            testCase.Link = chan.Link(100);
        end
    end
    methods (Test)
        function lossGrowsWithDistance(testCase)
            near = chan.Link(10).freeSpaceLossDb();
            far  = testCase.Link.freeSpaceLossDb();
            testCase.verifyGreaterThan(far, near);
        end
        function rejectsZeroDistance(testCase)
            testCase.verifyError(@() chan.Link(0), ?MException);
        end
    end
end
```

- The file name equals the class name; test methods live in a `methods (Test)` block and take `testCase` as the first argument.
- Setup blocks: `TestClassSetup` (once per class), `TestMethodSetup` (before each test), and the matching `TestMethodTeardown` and `TestClassTeardown`. Prefer `testCase.addTeardown(@fn, args)` next to the code that needs cleanup.
- Test classes can inherit from a shared base class that holds common helpers.
- Keep each test short with a single reason to fail. Name tests for the behaviour (`lossGrowsWithDistance`).
- `testCase.log("message")` and `testCase.onFailure(...)` add diagnostics to the report.

## 2. Function-based and script-based tests

```matlab
function tests = movingRmsTest
    tests = functiontests(localfunctions);
end

function setupOnce(testCase)
    testCase.TestData.x = ones(10, 1) * 2;
end

function testConstant(testCase)
    y = movingRms(testCase.TestData.x, 3);
    verifyEqual(testCase, y, testCase.TestData.x, AbsTol=1e-12);
end
```

- Function-based tests need a main function that returns `functiontests(localfunctions)`. Test functions are local functions named `test...`; fixture functions are `setupOnce`, `teardownOnce`, `setup`, `teardown`.
- Script-based tests use `%%` sections as separate tests and plain `assert`-style checks; they are least flexible. Prefer class-based tests for new work.
- Test file names conventionally end in `Test` or start with `test`; the suite finder accepts files that define tests, and `runtests` searches the folder.

## 3. Qualifications and constraints

- Four qualification types: `verify*` (record and continue), `assert*` (fail and stop this test), `fatalAssert*` (stop the whole run), `assume*` (mark the test filtered if the precondition is not met).
- Common methods: `verifyEqual`, `verifyTrue`, `verifyFalse`, `verifyEmpty`, `verifyNotEmpty`, `verifySize`, `verifyClass`, `verifyError`, `verifyWarning`, `verifyWarningFree`, `verifyLessThan`, `verifyGreaterThan`, `verifyThat`.
- Tolerances in `verifyEqual`: `AbsTol=1e-12` and `RelTol=1e-9`. If both are given the test passes when either is met.
- Constraint objects give full control: `testCase.verifyThat(x, IsEqualTo(y, "Within", AbsoluteTolerance(1e-9)))` with `matlab.unittest.constraints.IsEqualTo` and `matlab.unittest.constraints.AbsoluteTolerance` imported.
- Match errors by identifier (`verifyError(@() f(), "pkg:badInput")`) or by class (`?MException`). Do not match message text, which changes with the release and the locale.
- `assumeTrue(license("test", "Communication_Toolbox"), "Needs Communications Toolbox")` skips tests cleanly when a toolbox is missing.
- For non-deterministic code, seed in setup (`rng(1, "twister")`) and restore the generator state in teardown; see [toolboxes-and-interop.md](toolboxes-and-interop.md).

## 4. Fixtures, parameters and tags

```matlab
classdef IoTest < matlab.unittest.TestCase
    properties (TestParameter)
        fmt = {"csv", "parquet"}
        n   = {1, 100}
    end
    methods (Test, TestTags = {"io"})
        function roundTrip(testCase, fmt, n)
            tmp = testCase.applyFixture(matlab.unittest.fixtures.TemporaryFolderFixture);
            T = table((1:n).', rand(n, 1), VariableNames=["id" "v"]);
            f = fullfile(tmp.Folder, "data." + fmt);
            if fmt == "csv", writetable(T, f); T2 = readtable(f);
            else, parquetwrite(f, T); T2 = parquetread(f);
            end
            testCase.verifyEqual(T2.id, T.id);
            testCase.verifyEqual(T2.v, T.v, AbsTol=1e-12);
        end
    end
end
```

- `TemporaryFolderFixture` creates a folder that is removed on teardown. `WorkingFolderFixture` changes the current folder temporarily. `PathFixture` adds a folder to the path temporarily. `SuppressedWarningsFixture` silences named warnings for one test.
- `properties (TestParameter)` creates a test for each value and for the Cartesian product of several parameters by default. Use `ParameterCombination="sequential"` on the method attribute for matched pairs.
- Tags: `methods (Test, TestTags = {"slow"})`. Run with `runtests("tests", Tag="slow")`; exclude by building a suite and filtering with `selectIf`.
- Mocking: `[mock, behavior] = testCase.createMock(?pkg.Interface)` from the `matlab.mock` namespace lets tests replace collaborators; check the docs for the exact calling form.
- Share setup by writing a base class that subclasses `matlab.unittest.TestCase` and applies fixtures in `TestClassSetup`.

## 5. runtests and TestRunner

```matlab
results = runtests("tests", IncludeSubfolders=true);   % quick run
assertSuccess(results);                                % error if any test failed
disp(table(results))                                   % name, passed, failed, duration
```

```matlab
import matlab.unittest.TestRunner
import matlab.unittest.TestSuite
import matlab.unittest.plugins.XMLPlugin
import matlab.unittest.plugins.CodeCoveragePlugin
import matlab.unittest.plugins.codecoverage.CoberturaFormat

if ~isfolder("results"), mkdir("results"); end
suite  = TestSuite.fromFolder("tests", IncludingSubfolders=true);
runner = TestRunner.withTextOutput;
runner.addPlugin(XMLPlugin.producingJUnitFormat("results/junit.xml"));
runner.addPlugin(CodeCoveragePlugin.forFolder("src", Producing=CoberturaFormat("results/cobertura.xml")));
results = runner.run(suite);
assertSuccess(results);
```

- `runtests` takes a folder, file, class name or package; options include `Tag`, `Name`, `UseParallel`, `Strict`, `OutputDetail` and `IncludeSubfolders`. Run `doc runtests` for the list in your release.
- `TestRunner` with plugins gives control over output, XML reports, coverage and test reports (`TestReportPlugin.producingHTML` or `producingPDF`).
- Parallel test runs (`UseParallel=true` or `runner.runInParallel(suite)`) need Parallel Computing Toolbox and tests that do not share files or global state.
- Coverage formats include Cobertura XML and HTML; the coverage plugin reports on the files under the folder you pass.
- `TestSuite.fromClass`, `fromFile`, `fromFolder`, `fromPackage` and `fromProject` build suites explicitly. `selectIf("Name", "*Loss*")` filters.
- `results` is a `TestResult` array; `results.Failed`, `results.Incomplete` and `table(results)` give summaries.

## 6. Build tool and buildfile.m

```matlab
function plan = buildfile
    import matlab.buildtool.tasks.*
    plan = buildplan(localfunctions);

    plan("clean")   = CleanTask;
    plan("check")   = CodeIssuesTask;
    plan("test")    = TestTask("tests");

    plan("test").Dependencies = "check";
    plan.DefaultTasks = "test";
end

function docsTask(context)
    % A local function ending in "Task" becomes a task named "docs".
    root = context.Plan.RootFolder;
    disp("Building docs in " + root);
end
```

- A build file is a function file named `buildfile.m` in the project root that returns a `matlab.buildtool.Plan` created by `buildplan(localfunctions)`. Local functions whose names end in `Task` become tasks, and their first argument is a `TaskContext`.
- Built-in task classes in the `matlab.buildtool.tasks` namespace: `CleanTask`, `CodeIssuesTask`, `MexTask`, `PcodeTask`, `TestTask`. They have constructor options for inputs and outputs (for example result files for `TestTask` and `CodeIssuesTask`); look them up in the class reference of your release.
- Run from the command line: `buildtool` (default tasks), `buildtool test`, `buildtool check test`. `buildtool -tasks` lists tasks; `buildtool -init` generates a starter build file (check `doc buildtool` for the flags in your release).
- Tasks declare `Inputs` and `Outputs`; a task whose inputs and outputs are unchanged since the last successful run is skipped, which makes incremental builds fast.
- `CodeIssuesTask` fails the build on error-level issues by default; configure the severity threshold through its properties to fail on warnings as well.
- Since R2025a tasks can also be run from the Toolstrip in the Editor. In R2026b, TOML-based project files are available; check the docs before relying on them in build logic.
- Put rules for packaging toolboxes (`.mltbx`) in a separate task using the toolbox packaging functions; keep release steps out of `test`.

## 7. Code Analyzer

```matlab
issues = codeIssues("src");                       % codeIssues object (R2022b+)
errs   = issues.Issues(issues.Issues.Severity == "error", :);
disp(issues.Issues(:, ["Location" "Severity" "Description"]))
codeAnalyzer(issues)                              % open the report app
```

- `codeIssues` is the recommended programmatic interface; `checkcode` remains for single-file legacy use. `codeIssues` with no argument analyses the current folder and its subfolders.
- The `Issues` property is a table with columns that include `Location`, `Severity`, `Description`, `CheckID` and `LineStart`; confirm column names with `issues.Issues.Properties.VariableNames` in your release.
- Suppress a message on one line with a trailing `%#ok<CHECKID>` comment and a reason elsewhere in the code review; avoid file-wide suppression.
- Typical findings: arrays that change size in loops, unused variables, `&` where `&&` is intended, functions with unreachable code, missing semicolons, and shadowed built-ins.
- Configure the checks in the Editor preferences; check the docs for sharing a configuration file across a team.
- Run the analysis in CI through `CodeIssuesTask` so warnings do not reach the main branch unnoticed.

## 8. CI with matlab -batch

```bash
matlab -batch "buildtool test"
matlab -batch "results = runtests('tests', IncludeSubfolders=true); assertSuccess(results);"
```

- `-batch` runs a statement without the desktop, then exits with status 0 on success and non-zero when an error occurred. This is the supported way to drive CI.
- MathWorks publishes GitHub Actions for MATLAB (`matlab-actions/setup-matlab`, `run-tests`, `run-build`) and plugins for other CI systems. Pin the action to a released tag and check the repository README for current inputs.
- Choose the MATLAB release in `setup-matlab` explicitly (for example the release input) so a new release does not change results; add required products in the setup step.
- Cache the MATLAB installation where the CI system allows. Licensing for hosted runners depends on the project (public repositories use a free path; private ones need a batch licensing token). Read the current licensing page rather than assuming.
- Keep the licensing token in the CI secret store, not in the repository or workflow file.
- Upload `results/junit.xml` and coverage files as artifacts so failures can be inspected.

## 9. Projects and path control

- Use a MATLAB project (`.prj`) or a `startup.m` that only adds folders to the path. Avoid `genpath` on the whole repository because it adds `private`-like folders you did not intend to expose.
- `openProject("path/to/project")`, `currentProject` and `addPath(proj, folder)` manage path entries programmatically.
- Use `which -all function_name` to detect duplicate names and `matlab.lang.makeValidName` when generating names from data.
- Keep tests independent of the current folder: build absolute paths from `mfilename("fullpath")` and apply `PathFixture`.
- `clear classes` or `clear all` is often needed when a class definition changes in an interactive session; scripts that depend on it should be rewritten as functions.
- Treat generated artefacts (coverage reports, `*.asv`, `slprj`) as build output and ignore them in version control.
