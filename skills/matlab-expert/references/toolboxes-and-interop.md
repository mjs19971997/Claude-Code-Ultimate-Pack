# 5G and Communications Toolboxes, Monte Carlo, Python Interop and Octave

A short orientation for wireless-link simulation in MATLAB: the 5G Toolbox carrier and waveform objects, Communications Toolbox modulation and error-rate basics, reproducible random numbers for Monte Carlo runs, calling Python from MATLAB and MATLAB from Python, the plain-text live script format and GNU Octave limits. The objects `nrCarrierConfig`, `nrDLCarrierConfig` and `nrWaveformGenerator` were confirmed on the current reference pages; other function names are long-standing toolbox functions, so confirm signatures with `doc name` in your release before copying. What a 3GPP clause requires is covered by 5g-nr-3gpp-expert, not here.

## Contents

1. [Licensing and availability](#1-licensing-and-availability)
2. [5G Toolbox carrier objects](#2-5g-toolbox-carrier-objects)
3. [Full downlink waveform](#3-full-downlink-waveform)
4. [Link-level building blocks](#4-link-level-building-blocks)
5. [Communications Toolbox basics](#5-communications-toolbox-basics)
6. [Reproducible Monte Carlo](#6-reproducible-monte-carlo)
7. [Parallel Monte Carlo](#7-parallel-monte-carlo)
8. [Validation and pitfalls](#8-validation-and-pitfalls)
9. [Configure Python with pyenv](#9-configure-python-with-pyenv)
10. [Calling Python from MATLAB](#10-calling-python-from-matlab)
11. [Data conversion](#11-data-conversion)
12. [MATLAB Engine for Python](#12-matlab-engine-for-python)
13. [Errors and debugging](#13-errors-and-debugging)
14. [Plain-text live scripts](#14-plain-text-live-scripts)
15. [GNU Octave compatibility](#15-gnu-octave-compatibility)

## 1. Licensing and availability

- 5G Toolbox and Communications Toolbox are separately licensed products. Check at run time: `license("test", "5G_Toolbox")` and `license("test", "Communication_Toolbox")`, or list installed products with `ver`.
- Some features need support packages or add-ons; for example the `pre6GCarrierConfig` object, which allows values beyond the standard (spacing above 960 kHz, grid sizes above 275 resource blocks), needs an add-on. Check the toolbox documentation for the add-on name.
- GNU Octave has a `communications` package but no equivalent of 5G Toolbox; see [section 15](#15-gnu-octave-compatibility).
- Release notes of each toolbox list new objects and renamed properties. Pin the release in CI and read the compatibility notes when upgrading, since property names on configuration objects have changed between releases.

## 2. 5G Toolbox carrier objects

```matlab
carrier = nrCarrierConfig;                  % defaults: 15 kHz spacing, 52 RB (10 MHz)
carrier.SubcarrierSpacing = 30;             % kHz
carrier.NSizeGrid = 273;                    % resource blocks (100 MHz at 30 kHz)
carrier.NSlot = 0;
carrier.CyclicPrefix = "normal";
disp(carrier)
```

- `nrCarrierConfig` defines the numerology and grid for one carrier: subcarrier spacing, grid size in resource blocks, grid start, cell identity, slot number and cyclic prefix, with reference to the OFDM numerology clauses of TS 38.211 (the object page cites Sections 4.2, 4.3 and 4.4).
- `SubcarrierSpacing` accepts 15, 30, 60, 120, 240, 480 or 960 kHz. `NSizeGrid` is an integer from 1 to 275. The extended cyclic prefix applies only to 60 kHz spacing.
- A normal cyclic prefix gives 14 OFDM symbols per slot, an extended one gives 12.
- The same object is passed to resource-grid, OFDM and channel-estimation helpers so numerology is defined once.
- Treat property names as checked data: set properties by name, read back with `disp`, and let the object throw on invalid values rather than validating by hand.
- `nrDLCarrierConfig` and `nrULCarrierConfig` describe a complete single-carrier downlink or uplink waveform (channels, bandwidth parts, SS burst, CORESETs) and are the usual entry point for waveform generation.

## 3. Full downlink waveform

```matlab
cfgDL = nrDLCarrierConfig;                  % default single-carrier downlink configuration
[waveform, info] = nrWaveformGenerator(cfgDL);
size(waveform)                              % [samples, antennas]
disp(info)                                  % inspect the information structure
```

- `nrWaveformGenerator(cfg)` returns the time-domain waveform and an information structure. The per-channel configuration objects (PDSCH, PDCCH, CSI-RS, SS burst) are stored as properties of the carrier configuration; the PDSCH property is a cell array of `nrWavegenPDSCHConfig` objects.
- Release R2026a added a constructor form that takes frequency range, channel bandwidth and subcarrier spacing and adjusts the dependent properties to a valid configuration; check `doc nrDLCarrierConfig` for the syntax in your release.
- Inspect `info` for sampling rate and grid dimensions before computing spectra or applying channels; do not assume the rate from the bandwidth alone.
- Use the toolbox examples in the documentation as a starting point and change one parameter at a time, keeping each variant under test.

## 4. Link-level building blocks

Names below are long-standing 5G Toolbox functions and objects. Confirm exact signatures in `doc` for your release.

| Task | Typical function or object |
|---|---|
| Empty resource grid for a carrier | `nrResourceGrid(carrier, nTxAnts)` |
| OFDM modulation and demodulation | `nrOFDMModulate`, `nrOFDMDemodulate`, `nrOFDMInfo` |
| Data channel configuration | `nrPDSCHConfig`, `nrPDSCH`, `nrPDSCHIndices` |
| Transport channel coding | `nrDLSCH`, `nrDLSCHDecoder` and `nrDLSCHInfo`, or the lower-level `nrLDPCEncode` and `nrLDPCDecode` |
| Channel models | `nrTDLChannel`, `nrCDLChannel` (System objects) |
| Channel estimation | `nrPerfectChannelEstimate`, `nrChannelEstimate` |

- Link-level loops use System objects (`nrTDLChannel`, `nrDLSCH`): construct once, call with `step`-style syntax in the loop, and call `reset` between independent trials where required.
- Keep the carrier object, the PDSCH configuration and the channel configuration as the single source of truth for numerology; derive sampling rate and FFT size with `nrOFDMInfo(carrier)`.
- Verify a chain stage by stage: modulate and demodulate with no channel and no noise and expect zero errors, then add the channel, then add noise.
- A BLER or throughput simulation needs many slots per SNR point; budget runtime early with a small run and extrapolate.
- Follow the standard text for what a procedure means; this skill only covers how MATLAB exposes it.

## 5. Communications Toolbox basics

```matlab
M = 16;  k = log2(M);
nBits = 4e5;
EbNoDb = 0:2:14;
ber = zeros(size(EbNoDb));
s = RandStream("Threefry", Seed=2026);

for i = 1:numel(EbNoDb)
    bits = randi(s, [0 1], nBits, 1);
    tx = qammod(bits, M, "gray", InputType="bit", UnitAveragePower=true);
    snrDb = EbNoDb(i) + 10*log10(k);                 % one sample per symbol
    n0 = 10^(-snrDb/10);                             % noise power for unit signal power
    noise = sqrt(n0/2) * (randn(s, size(tx)) + 1j*randn(s, size(tx)));
    rx = tx + noise;
    est = qamdemod(rx, M, "gray", OutputType="bit", UnitAveragePower=true);
    ber(i) = mean(est ~= bits);
end
theory = berawgn(EbNoDb, "qam", M);                  % Communications Toolbox
semilogy(EbNoDb, ber, "o-", EbNoDb, theory, "--");
```

- `qammod`/`qamdemod`, `pskmod`/`pskdemod`, `awgn`, `biterr`, `berawgn`, `comm.AWGNChannel`, `comm.ErrorRate`, `comm.RayleighChannel` and `comm.PSKModulator` are the common entry points. Use `UnitAveragePower=true` so SNR definitions match theory.
- The example draws noise from an explicit `RandStream` so the result is reproducible and independent of the global generator; `awgn` uses the global stream, so seed it with `rng` if you call it.
- Check the relation between Eb/N0, Es/N0 and SNR for your sampling convention (samples per symbol, code rate, bits per symbol). Errors here shift curves by a constant number of dB and are easy to miss.
- Compare simulated BER with theory (`berawgn`) for a simple case before trusting a new chain.
- Confidence: a BER estimate with few errors is noisy. Run until a minimum number of errors (for example 100) is counted per point, or until a maximum number of bits; see statistics-expert for interval choice.
- `comm.ErrorRate` accumulates errors across calls and suits streaming simulations; `biterr` suits block simulations and returns a count and a ratio.

## 6. Reproducible Monte Carlo

```matlab
rng(42, "twister");           % seed the default generator
s0 = rng;                     % capture state (struct with Type, Seed, State)
a = rand(1, 3);
rng(s0);                      % restore: next draws repeat
b = rand(1, 3);               % equals a
```

- `rng(seed)` seeds the default global generator; `rng("default")` returns to the start-up state; `rng("shuffle")` seeds from the clock (not reproducible; record the seed if you use it).
- Capture and restore state with `s = rng; ...; rng(s)`. In tests, restore in teardown with `testCase.addTeardown(@rng, rng)` after setting the seed.
- Generator choice: `"twister"` (Mersenne Twister) is the default; `"threefry"` and `"philox"` are counter-based generators designed for parallel streams; `"combRecursive"` also supports substreams.
- Prefer explicit `RandStream` objects in library code and pass them in as arguments, so functions do not touch global state: `x = randn(s, n, 1)`.
- Record the MATLAB release (`version("-release")`), the generator type and the seed with the results. Different releases may change generators or function internals; a fixed seed guarantees repeatability only within a release and platform for the same code.
- Deterministic runs also require the same number of draws in the same order. Adding a draw in the middle of a function changes all later numbers.
- `randperm`, `randi`, `randsample` (Statistics and Machine Learning Toolbox) and `datasample` consume the global stream unless you pass a stream where supported.

## 7. Parallel Monte Carlo

```matlab
nTrials = 128;
nBits = 1e5;
errs = zeros(nTrials, 1);
parfor t = 1:nTrials
    s = RandStream("Threefry", Seed=2026);
    s.Substream = t;                          % independent, reproducible stream per trial
    bits = randi(s, [0 1], nBits, 1);
    flip = rand(s, nBits, 1) < 0.01;          % 1 percent bit-flip channel
    errs(t) = sum(xor(bits, flip) ~= bits);
end
berEstimate = sum(errs) / (nTrials * nBits);
```

- Each iteration builds its own stream from the same seed and a distinct substream index, so the result does not depend on how iterations are scheduled across workers or on the number of workers.
- Calling `rng(seed)` on the client does not control the workers. Workers have their own generators.
- Return per-trial counts, not rates, and combine after the loop; sum errors and bits separately to weight trials correctly.
- Use `parallel.pool.DataQueue` to report progress from workers to the client, and write partial results to disk with `save` in chunks for long runs.
- For an SNR sweep, parallelise over the flattened (SNR, trial) pairs when the number of SNR points is smaller than the number of workers.
- Compare `parpool("Processes")` with `parpool("Threads")` on your workload; some toolbox objects (System objects, channel models) may run only on process workers. Check the documentation for the objects in use.
- On GPU: `gpuArray` data and `gpuArray.randn` give faster large-array simulation; verify that results match the CPU path statistically, not bit-for-bit.

## 8. Validation and pitfalls

- Pin and print the MATLAB and toolbox versions (`ver` lists installed products with versions) in the run log.
- Mismatched sampling rate or FFT size between transmitter, channel and receiver is the most common reason for a chain with no errors at high SNR but unexplained loss: derive both from `nrOFDMInfo` of the same carrier object.
- Delay and filter group delay must be compensated before demodulation; the channel objects can report their delay (`info` structures), so use it rather than correlating blindly.
- Normalise power before adding noise and state whether SNR is per sample, per symbol or per bit.
- Avoid comparing to published curves without matching every parameter (channel profile, Doppler, antenna setup, receiver type, number of iterations).
- Keep simulation scripts deterministic and parameterised: pass a configuration struct, save results with the configuration, and plot from saved results (see [figures-and-export.md](figures-and-export.md)).
- Long simulations: checkpoint results every N points and make the script restartable, since licence outages and session timeouts occur.
- Unit-test link components with fixed seeds and tolerances, for example "noiseless chain recovers input exactly" and "measured BER lies within a stated interval of theory".

## 9. Configure Python with pyenv

```matlab
pe = pyenv;                                   % show current configuration
disp(pe.Version + " at " + pe.Home)
pyenv(Version="3.12");                        % choose before any Python call (name or path to executable)
pyenv(ExecutionMode="OutOfProcess");          % isolate Python in a separate process
terminate(pyenv);                             % stop an out-of-process interpreter
```

- Call `pyenv` before the first `py.` call in a session. After Python has loaded in-process, changing the version requires restarting MATLAB; switching `ExecutionMode` needs the interpreter to be unloaded.
- `Version` accepts a version string or the full path of a Python executable, for example one inside a virtual environment. Use a virtual environment per project and install packages with `python -m pip`, not into the system Python.
- Use a Python version listed as supported for your MATLAB release in the Python compatibility table. Unsupported combinations can fail at load or crash.
- In-process execution is fastest (shared memory, no copies) but a crash in a native Python library takes MATLAB down and library conflicts (OpenMP, C++ runtime) occur. `OutOfProcess` isolates both at the cost of data copying.
- Put the `pyenv` call in `startup.m` or the project startup task so that scripts and tests behave the same. Print `pyenv` output into the CI log.

## 10. Calling Python from MATLAB

```matlab
r = py.math.sqrt(2);                                  % py.<module>.<function>
v = double(py.numpy.linspace(0, 1, 5));              % numpy array -> MATLAB double
s = string(py.str("hello"));                          % Python str -> MATLAB string
d = py.dict(pyargs("a", 1, "b", 2));                  % keyword arguments via pyargs
lst = py.list({1, 2, 3});
n = double(py.len(lst));

out = pyrun("y = sum(x)", "y", x=[1 2 3]);            % run code, return variable y (R2021b+)
res = pyrunfile("score.py", "score", threshold=0.5);  % run a script file, return a variable

mod = py.importlib.import_module("statistics");
m = mod.mean(py.list({1, 2, 3, 4}));
```

- `py.module.name` accesses any importable module. Use `py.importlib.reload(mod)` after editing a module in the same session.
- `pyargs("name", value, ...)` passes keyword arguments. Positional arguments are passed normally.
- Add a folder to Python's path with `P = py.sys.path; if count(P, string(folder)) == 0, insert(P, int32(0), string(folder)); end`.
- Long scripts belong in `.py` files run with `pyrunfile`; keep inline `pyrun` to short statements. Never build code strings from untrusted text.
- Python objects keep their identity: `x = py.list(); x.append(1)` mutates a Python list in place. Use `methods(x)` to discover the calls of a Python object, and the Python package documentation for semantics.
- Python callables can be called with MATLAB arguments in simple cases; to pass MATLAB function handles into Python, check the current docs for the supported forms.
- Calls from `parfor` workers need the same Python environment on every worker; prefer `OutOfProcess` and explicit paths, and test on a small pool first.

## 11. Data conversion

| MATLAB to Python | Python result |
|---|---|
| scalar `double` | `float` |
| `int32`, `int64` scalar | `int` |
| `logical` scalar | `bool` |
| `string` or `char` row | `str` |
| `cell` array | `list` |
| `struct` scalar | `dict` |
| numeric vector or matrix | `matlab.double` and similar types, or a NumPy array after `py.numpy.array(...)` |

| Python to MATLAB | Conversion |
|---|---|
| `float`, `int`, `bool` | automatic to `double`, `int64`, `logical` |
| `str` | `string(x)` or `char(x)` |
| `list`, `tuple` | `cell(x)` (elements stay Python objects until converted) |
| `dict` | `struct(x)` (keys become fields) |
| NumPy array | `double(x)`; check shape and dtype first |
| pandas DataFrame | convert columns individually (`double(df.col.values)`), or write and read Parquet |

- Check dtype and memory order of NumPy arrays: MATLAB is column-major and NumPy is row-major by default. Converting through `double()` handles the layout, but transposes and reshape logic should be tested with a non-symmetric array.
- Large arrays: avoid element-by-element conversion; convert whole arrays, or exchange data through files (`.mat` via `scipy.io`, Parquet, HDF5) when sizes reach hundreds of megabytes.
- Cell arrays of strings convert element-wise; build with `py.list(cellstr(x))` when Python expects `str` items.
- Integers: MATLAB defaults to `double`, so a count passed to Python may arrive as `float`. Cast explicitly with `int32(n)` or `int64(n)`.
- `NaN` and `missing` map differently between languages; test round trips for missing data.

## 12. MATLAB Engine for Python

```bash
python -m pip install matlabengine              # newest wheel, targets the newest MATLAB release
python -m pip install matlabengine==26.2.5      # PyPI listing for R2026b; pin the version for your release
```

```python
import matlab.engine

eng = matlab.engine.start_matlab()
try:
    x = matlab.double([1.0, 4.0, 9.0])
    root = eng.sqrt(x)                       # returns matlab.double
    eng.eval("disp(version)", nargout=0)     # statements that return nothing need nargout=0
    eng.workspace["gain"] = 2.5
    out = eng.eval("gain * 2")
finally:
    eng.quit()
print(root, out)
```

- The engine package version follows the MATLAB release (26.2.x for R2026b on PyPI; the major.minor part encodes the release). The newest engine works only with the newest MATLAB release; for older releases pin `matlabengine==<version>` after checking the PyPI release history, or install from the `extern/engines/python` folder of the MATLAB installation.
- Requirements: a MATLAB installation (and licence) on the machine, and a Python version supported by that MATLAB release. Use a virtual environment.
- `matlab.engine.start_matlab()` starts a new session; `matlab.engine.find_matlab()` lists shared sessions and `matlab.engine.connect_matlab(name)` attaches to one started in MATLAB with `matlab.engine.shareEngine`.
- `start_matlab("-nodesktop")` style option strings can be passed; check `help(matlab.engine.start_matlab)` for the options of your release. Start-up costs seconds, so reuse one engine for many calls.
- `matlab.engine.start_matlab(background=True)` returns a future so Python can work while MATLAB starts; check the docs for this and for `async_` calls (`eng.fn(..., background=True)`).
- Pass data as `matlab.double`, `matlab.int32`, `matlab.logical` and so on; NumPy arrays can be converted with `matlab.double(arr.tolist())` or, in recent releases, directly by supported types (check the docs). Multiple outputs: call with `nargout=2` and unpack the tuple.
- Do not share one engine between threads without locking, and always call `quit()` (use `try/finally`) so MATLAB processes and licences are released.
- An engine session on a server consumes a licence seat. For servers without MATLAB, compile the function with MATLAB Compiler SDK instead; that topic is outside this skill.

## 13. Errors and debugging

- A Python exception surfaces in MATLAB as a `MException` whose message contains the Python error text. Catch it and inspect `ME.identifier` and `ME.message`.
- In Python, MATLAB errors raise `matlab.engine.MatlabExecutionError`; the message carries the MATLAB error text.
- If `py.` calls report a missing module, the interpreter in use is not the one where you installed packages: check `pyenv().Executable` and install with that interpreter's `-m pip`.
- A library crash with in-process mode (for example conflicting OpenMP runtimes) is cured by `OutOfProcess` mode.
- Use `pyenv` output, `py.sys.version`, `py.sys.executable` and `py.sys.path` to print the environment in test logs.
- Tests that call Python should skip with `assumeTrue` when the interpreter or package is missing, not fail.

## 14. Plain-text live scripts

- R2026b creates and saves live scripts and live functions as plain text `.m` files by default, with the binary `.mlx` format kept as an option in Settings (Home tab, Environment, Settings). Plain text is chosen for source control and external editors. Earlier releases default to `.mlx`; check the release notes for the first release that supported plain-text live code.
- A plain-text live script is an ordinary `.m` file with special comment markers for formatted text and a data block at the end that stores output and layout metadata. Typical markers look like `%[text]` for text lines. Treat the marker syntax and the trailing appendix as owned by MATLAB: edit prose and code, but let the Live Editor write the appendix, and review the file format page of your release before writing tooling that parses it.
- Because it is plain text, diff and merge work line by line, but the stored outputs (figures, tables) can still produce large, noisy diffs. Clear outputs before committing, or commit results separately.
- Convert between formats in the Live Editor (Save As); check the current docs for a documented programmatic route rather than relying on internal functions.
- Do not run `.mlx` or live scripts in CI directly; extract logic into functions and call them from a build task.
- A live script is still a script: it shares the base workspace, so avoid hidden state between sections.

## 15. GNU Octave compatibility

Octave 11.3.0 (June 2026) is the newest release found on the Octave news page; 11.1.0 appeared in February 2026. Compatibility is feature by feature, so read the Octave manual for the construct in question.

| MATLAB feature | In Octave |
|---|---|
| `arguments` blocks | not supported; use `inputParser` or manual checks |
| `string` class and double-quoted `string` arrays | double-quoted literals are `char` arrays with escape processing; no `string` array type |
| `table`, `timetable`, `categorical`, `datetime` | not built in; some functionality in packages |
| `dictionary` | not available; use `containers.Map` or `struct` |
| `classdef` | partial support; advanced features (some property validation, `enumeration`, mix-ins) may be missing |
| `matlab.unittest`, `buildtool` | not available; Octave has `test` and `%!test` blocks, and `runtests` for a folder of test functions |
| Live scripts and plain-text live code | not supported; markers are comments only |
| `parfor` | accepted as `for` (runs serially) unless a package provides parallel execution |
| `exportgraphics`, `tiledlayout` | not available; use `print` and `subplot` |
| `pyenv` / `py.*` | not available; use `system` calls or package-specific bridges |
| Toolboxes | Octave Forge packages (`pkg load statistics`) cover part of the functionality; no 5G Toolbox equivalent |
| Syntax extras | Octave accepts `#` comments, `!` as not, `endif`/`endwhile`, `printf`; avoid these if code must stay MATLAB compatible |

- If both must be supported, write a small compatibility layer, keep new language features out of shared code, and run a numerical subset of the tests on Octave in CI.
- Numerical results, random streams and default plotting differ between the two; do not expect bit-identical output.
- Names, defaults and error messages differ even for functions with the same name: check each one used in shared code.
- For a licence-free workflow that needs modern MATLAB features, consider Python with scientific-python-expert guidance instead of constraining MATLAB code to Octave's subset.
