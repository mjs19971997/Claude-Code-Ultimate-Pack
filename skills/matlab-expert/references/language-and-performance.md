# MATLAB Language and Performance

Idioms for fast and maintainable MATLAB on R2026b: vectorisation, preallocation, arguments blocks, classdef, packages, tables and timetables, string arrays, dictionary, the Profiler and parfor. Functions used here have existed since the release noted beside them; check the release notes if you must support older versions.

## Contents

1. [Vectorisation and implicit expansion](#1-vectorisation-and-implicit-expansion)
2. [Preallocation and growth](#2-preallocation-and-growth)
3. [Functions, scripts and local functions](#3-functions-scripts-and-local-functions)
4. [Arguments blocks](#4-arguments-blocks)
5. [Packages and namespaces](#5-packages-and-namespaces)
6. [classdef](#6-classdef)
7. [Strings, tables and timetables](#7-strings-tables-and-timetables)
8. [Dictionary and containers](#8-dictionary-and-containers)
9. [Profiling and timing](#9-profiling-and-timing)
10. [parfor and parallel basics](#10-parfor-and-parallel-basics)

## 1. Vectorisation and implicit expansion

```matlab
x = linspace(0, 1, 1000).';     % column vector
w = [1 2 3];                    % row vector
M = x .* w;                     % implicit expansion: 1000x3, no repmat (R2016b+)
d = vecnorm(M, 2, 2);           % row-wise 2-norm
mask = M > 0.5 & x < 0.9;       % logical array, same size as M
M(mask) = 0;                    % logical indexing
```

- Operators `+ - .* ./ .^` and comparison/logical operators expand singleton dimensions. `bsxfun` is no longer needed.
- `pagemtimes(A, B)` multiplies stacks of matrices along the third dimension; `pagetranspose` and `pagectranspose` exist for the same layout.
- `cumsum`, `cumprod`, `diff`, `movmean`, `movsum`, `histcounts`, `accumarray` and `groupsummary` replace many loops that carry state.
- Prefer `any`, `all`, `nnz`, `min`/`max` with a dimension argument over loops with conditionals.
- Not every loop should be vectorised: if the vector form allocates a very large intermediate (for example a pairwise distance matrix of 1e5 by 1e5), loop over blocks instead.
- `arrayfun` and `cellfun` are convenience wrappers and are not guaranteed to be faster than a `for` loop. Use `UniformOutput=false` when results differ in size.

## 2. Preallocation and growth

```matlab
n = 1e5;
out  = zeros(n, 1);             % double
flag = false(n, 1);             % logical
name = strings(n, 1);           % string array of empty strings
buf  = cell(n, 1);              % cell array
vals = nan(n, 3, "single");     % single precision

for k = 1:n
    out(k) = k^2;
end
```

- Growth by `y(end+1) = v` or `y = [y; v]` copies the array each time. Preallocate to the known size, or fill a cell array and call `vertcat(buf{:})` once.
- When the final size is unknown, allocate in chunks (double the capacity when full) and trim at the end.
- For tables, collect columns in arrays or cells inside the loop and call `table(...)` once afterwards.
- `zeros(n, 1, "like", x)` creates an array with the same class and complexity as `x` (and the same GPU residency for `gpuArray`).
- Use the smallest sufficient type for large data (`single`, `uint8`, `logical`), but convert to `double` before accumulating sums that may lose precision.

## 3. Functions, scripts and local functions

- A function file `fadingLoss.m` has one main function `fadingLoss`, optional local functions after it, and nested functions only when sharing variables is intentional.
- Scripts run in the caller workspace and may define local functions at the end of the file (R2016b). A script cannot take arguments.
- Function handles: `f = @fadingLoss;` or anonymous `g = @(x) f(x, 2.4)`. An anonymous function captures variables by value when it is created.
- `nargin`, `nargout`, `varargin` and `varargout` remain valid but an `arguments` block is the first choice for validation.
- `mfilename("fullpath")` gives the folder-relative anchor for locating data next to a file; use `fullfile` to build paths.
- `exist("name", "file")` and `which name -all` diagnose shadowing. The Code Analyzer flags many shadowing cases.
- `inputParser` still works for code that must run before R2019b; otherwise use arguments blocks.
- `onCleanup(@() fclose(fid))` ties cleanup to variable lifetime and runs on error.

## 4. Arguments blocks

```matlab
function [p, info] = detectPeaks(x, opts)
    arguments
        x (:,1) double {mustBeReal}
        opts.MinHeight (1,1) double = 0
        opts.MinDistance (1,1) double {mustBeInteger, mustBePositive} = 1
        opts.Method (1,1) string {mustBeMember(opts.Method, ["simple", "robust"])} = "simple"
    end
    arguments (Output)
        p (:,1) double
        info struct
    end
    [p, loc] = findpeaks(x, MinPeakHeight=opts.MinHeight, MinPeakDistance=opts.MinDistance);
    info = struct("Locations", loc, "Method", opts.Method);
end
```

- Syntax per argument: `name (size) class {validators} = default`. Size and class are coerced where possible (a row vector is reshaped to `(:,1)`; a `char` can become a `string` when the class is `string`).
- Name-value arguments are declared as fields of a struct name (`opts.MinHeight`) and called as `detectPeaks(x, MinHeight=3)` or `detectPeaks(x, "MinHeight", 3)`.
- Repeating arguments use `(1,:) cell` forms with the `Repeating` attribute; check the docs for exact syntax before use.
- Validation functions begin with `must`: `mustBePositive`, `mustBeInteger`, `mustBeFinite`, `mustBeNonempty`, `mustBeMember`, `mustBeNumeric`, `mustBeFile`, `mustBeInRange`. Custom validators are functions that throw an error and return nothing.
- Output validation goes in `arguments (Output)`. It adds cost, so use it on public API functions rather than inner helpers.
- Arguments blocks also work in `classdef` methods; property validation uses the same size/class/validator syntax.
- Autocompletion of name-value names in the Editor and Command Window comes from the block.

## 5. Packages and namespaces

```text
src/
  +chan/
    fadingLoss.m            % call: chan.fadingLoss(...)
    Link.m                  % classdef: obj = chan.Link(...)
    +internal/
      gammaCdf.m            % chan.internal.gammaCdf(...)
```

- Add `src` (the folder that contains `+chan`) to the path, not `+chan` itself.
- Call functions with the full name, or `import chan.*` inside a function to use short names. Imports are scoped to the function or script that declares them.
- Packages do not support `private` folders; use `+internal` sub-packages by convention and document that they are not public API.
- A function and a package of the same name conflict; keep names distinct.
- Class methods defined in a `@ClassName` folder and in a package are separate mechanisms; mixing both in one class is not advisable.
- `meta.package.fromName("chan")` returns package metadata for tooling.

## 6. classdef

```matlab
classdef Link < handle
    properties (SetAccess = private)
        Distance (1,1) double {mustBePositive} = 1
    end
    properties
        FrequencyHz (1,1) double {mustBePositive} = 3.5e9
    end
    properties (Dependent)
        WavelengthM (1,1) double
    end
    methods
        function obj = Link(distance, nvp)
            arguments
                distance (1,1) double {mustBePositive}
                nvp.FrequencyHz (1,1) double {mustBePositive} = 3.5e9
            end
            obj.Distance = distance;
            obj.FrequencyHz = nvp.FrequencyHz;
        end
        function w = get.WavelengthM(obj)
            w = 299792458 / obj.FrequencyHz;
        end
        function pl = freeSpaceLossDb(obj)
            pl = 20 * log10(4 * pi * obj.Distance / obj.WavelengthM);
        end
    end
end
```

- Inherit from `handle` for reference semantics, omit it for value semantics. Value classes are safer for data; handle classes suit resources and shared state.
- Property attributes: `SetAccess`, `GetAccess`, `Dependent`, `Constant`, `Hidden`, `Transient`. Property validation runs on every assignment, which costs time in hot loops.
- Method attributes: `Static`, `Access = private`, `Abstract`, `Sealed`. Overload `disp`, `plus`, `size` or `subsref` only when needed.
- `enumeration` blocks define fixed value sets; `events` and `notify` provide observer behaviour.
- Mix-ins in `matlab.mixin`: `SetGet` (property access by `set`/`get`), `Copyable` (shallow `copy` for handle objects), `CustomDisplay`, `Heterogeneous`. Use `Copyable` rather than writing manual copy code.
- Release notes for R2026b describe a new object management system intended to make objects faster; it is not on by default. Check the current docs before enabling or depending on it.
- Test classes by constructing them with valid and invalid arguments; avoid inspecting private properties.
- Class files must be on the path; changing a class definition requires `clear classes` (or `clear all`) in an interactive session, which is a reason to keep experiments in functions.

## 7. Strings, tables and timetables

```matlab
s = "Throughput: " + 42.5 + " Mbit/s";          % string concatenation with +
parts = split("a,b,c", ",");                     % string array [3x1]
ok = contains(["alpha" "beta"], "et");           % logical [1x2]
keys = lower(strip(["  Foo "; "BAR  "]));        % element-wise string functions

T = readtable("runs.csv", TextType="string");    % strings, not char cells
T.snrDb = round(T.snr_db, 1);                    % add a derived variable
sub = T(T.snrDb >= 10 & T.ber < 1e-3, :);        % row filtering
G = groupsummary(T, "scenario", ["mean" "std"], "ber");
wide = unstack(T(:, ["snrDb" "scenario" "ber"]), "ber", "scenario");

tt = table2timetable(T, RowTimes="time");        % row times become the index
tt5 = retime(tt, "regular", "mean", TimeStep=minutes(5));
win = tt(timerange("2026-10-01", "2026-10-08"), :);
sync = synchronize(tt, tt2, "union", "linear");
```

- Double quotes create `string`, single quotes create `char`. A `string` array element is addressed with `()`, characters of one string with `{}`-free `extractBefore`, `extractAfter`, `extractBetween` and `char(s)`.
- `strcmp`, `strcmpi`, `startsWith`, `endsWith`, `contains`, `replace`, `regexp`, `join`, `compose` and `sprintf` all accept string arrays. Use `strlength` rather than `length`, and `isStringScalar` to validate.
- A `table` stores named columns of any type with the same number of rows. `T.name` returns the column, `T{rows, cols}` returns contents (concatenated), `T(rows, cols)` returns a sub-table.
- `rowfilter` (R2022a) builds reusable filters: `rf = rowfilter(T); T2 = T(rf.snrDb > 10 & rf.ber < 1e-3, :);`.
- `varfun`, `rowfun`, `splitapply`, `findgroups`, `innerjoin`, `outerjoin`, `sortrows`, `unique`, `stack`, `unstack`, `renamevars`, `removevars`, `movevars` are the main table verbs.
- Set `T.Properties.VariableUnits` and `VariableDescriptions` to keep metadata with the data. `summary(T)` gives a quick overview.
- A `timetable` requires a sorted or sortable `datetime` or `duration` row time. `retime`, `synchronize`, `timerange`, `withtol`, `lag`, `rmmissing`, `fillmissing` and `isregular` cover regularisation and alignment.
- For files: `readtable`, `writetable`, `parquetread`, `parquetwrite` (columnar, compressed), `readmatrix`, `readlines`, `writelines`, `jsondecode`, `jsonencode`. Use `detectImportOptions(file)` then edit `opts.VariableTypes` before reading when types matter.
- Tables with very many rows in a hot loop are slow to index; pull needed columns into arrays first.

## 8. Dictionary and containers

```matlab
d = dictionary(["lte" "nr"], [4 5]);     % string keys, double values (R2022b+)
d("nr") = 5.5;
d("wifi") = 6;
if isKey(d, "nr")
    v = d("nr");
end
k = keys(d);  v = values(d);
```

- `dictionary` is a value-semantics key/value type with typed keys and values; it supersedes `containers.Map` for new code. `containers.Map` is a handle class and still works for older releases.
- Use `struct` for fixed named fields known at design time, `dictionary` for lookup by runtime keys, `table` for homogeneous records.
- Dynamic struct fields (`s.(name) = v`) work, but `name` must be a valid identifier; validate with `isvarname`.
- `cell` arrays suit heterogeneous results of unknown shape; avoid them for large numeric data.

## 9. Profiling and timing

```matlab
profile on
result = runSweep(params);
profile off
p = profile("info");                       % structure with FunctionTable
profile viewer                             % interactive view
t = timeit(@() movingRms(randn(1e5, 1), 11));   % median of several runs
```

- Start with the Profiler to find the function and line that dominates; look at "Self time", not only "Total time". Calls that run millions of times with tiny bodies are candidates for vectorising or inlining.
- `timeit` handles warm-up and returns a median; `tic`/`toc` is fine for coarse timing but counts first-run compilation and file loading. Use `gputimeit` for GPU code and call `wait(gpuDevice)` before `toc`.
- The Code Analyzer reports likely performance problems such as arrays that grow in loops. Run `codeIssues` before profiling (see [testing-and-build.md](testing-and-build.md)).
- Save a profile with `profsave(p, "profile_html")` for review.
- Measure end-to-end time from the command line (`matlab -batch`) at least once, because startup, path scanning and licence checkout are not visible in an interactive profile.

## 10. parfor and parallel basics

```matlab
if isempty(gcp("nocreate"))
    parpool("Processes", 4);                 % process workers; "Threads" also exists
end
nTrials = 64;
res = zeros(nTrials, 1);
const = parallel.pool.Constant(@() loadLookupTable("lut.mat"));   % broadcast once
parfor t = 1:nTrials
    tbl = const.Value;
    res(t) = runTrial(t, tbl);               % sliced output variable
end
total = 0;
parfor t = 1:nTrials
    total = total + res(t);                  % reduction variable
end
f = parfeval(backgroundPool, @() sum(1:100), 1);   % run work without blocking
out = fetchOutputs(f);
```

- Iterations must be independent. Variables are classified as loop, sliced, broadcast, reduction or temporary; analysis errors usually come from using a variable in two roles.
- A sliced variable is indexed only by the loop variable (`res(t)`); it is the main way to return data. Preallocate it.
- Broadcast variables are copied to every worker; for large data use `parallel.pool.Constant` or a `datastore`.
- Printing and plotting from workers is unreliable; send progress with `parallel.pool.DataQueue` and `afterEach`.
- `parfor` cannot be nested in effective terms; the inner loop runs serially. `parfor (k = 1:n, 4)` limits workers.
- Without Parallel Computing Toolbox a `parfor` runs as an ordinary `for`, so code stays portable.
- Random numbers: workers have independent streams that are not reproducible by `rng` in the client. Use a counter-based generator with per-iteration substreams (see [toolboxes-and-interop.md](toolboxes-and-interop.md)).
- `parfeval` and `parfevalOnAll` run asynchronous jobs; `backgroundPool` uses threads on the client machine. Check the docs for functions that are supported on thread workers.
- Error handling: errors from workers are wrapped in `MException` objects that carry the original cause in `ME.cause`. Wrap the loop body in `try/catch` and store the error if one failed trial should not stop the sweep.
- Timing: compare against a serial run with the same seed; startup time of the pool is excluded from `timeit` but counted by `tic`/`toc`.
