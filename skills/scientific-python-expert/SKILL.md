---
name: scientific-python-expert
description: >-
  Writes fast, reproducible numerical Python with NumPy, SciPy and numba, and produces publication-quality Matplotlib figures. Use when vectorizing loops, fixing broadcasting or dtype surprises, reasoning about strides and views, seeding numpy.random.Generator for parallel Monte Carlo, profiling with cProfile, timeit or line_profiler (kernprof), limiting BLAS threads, using numba njit or prange, integrating ODEs with scipy.integrate.solve_ivp, or sizing vector PDF figures to a journal column. Not for general Python language, packaging or typing (use python-expert), statistical tests and confidence intervals (use statistics-expert), DataFrame wrangling (use data-analysis-expert) or LaTeX documents that include the figures (use latex-academic-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Scientific Python Expert

This skill covers numerical and simulation code in Python: NumPy arrays and memory layout, vectorization and broadcasting, random number generation and reproducibility, SciPy integration and optimization entry points, numba compilation, profiling, process and thread parallelism, and Matplotlib figures prepared for papers. It treats correctness and reproducibility as equal to speed. General Python language topics, packaging and typing belong to python-expert, and the LaTeX side of including a figure belongs to latex-academic-expert.

> Verified against NumPy 2.5.4, SciPy 1.18.1, numba 0.68.1, Matplotlib 3.11.2, line_profiler 5.1.0 (2026-10). Release numbers come from the PyPI release metadata; the code examples were executed against exactly these versions on Python 3.13.

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

- Covered: NumPy 2.x arrays, dtypes, promotion, strides, views and copies, C and Fortran order, vectorization, broadcasting, `einsum`, `numpy.random.Generator`, `SeedSequence`, SciPy (`integrate`, `optimize`, `stats`, `fft`, `sparse`, `linalg` entry points), numba `njit` and `prange`, `cProfile`, `timeit`, `line_profiler`, `multiprocessing` and `concurrent.futures` for numeric work, BLAS thread control, Monte Carlo and ODE simulation code, and Matplotlib figures for journals.
- Not covered: Python language features, packaging, typing and async code (python-expert); the LaTeX source that includes the figures, captions and bibliography (latex-academic-expert); dataframes and ML frameworks; GPU libraries.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| NumPy 2.x API | Aliases removed in the 2.x line are absent in 2.5.4: `np.trapz` (use `np.trapezoid`), `np.in1d` (use `np.isin`), `np.row_stack` (use `np.vstack`), `np.float_`, `np.Inf`, `np.NaN`, `np.cumproduct`, `np.product`, `np.round_`, `np.asfarray`. Newer functions: `np.unique_values`, `np.vecdot`, `np.matvec`, `np.vecmat`, `np.bitwise_count`, `np.concat` |
| Type promotion | Python scalars are weak: `np.float32(3) + 3.0` stays `float32`. NumPy scalar and array dtypes still promote normally. Fixed-width integers wrap on overflow with a `RuntimeWarning` for scalars and silently for arrays |
| `copy=` argument | `np.array(x, copy=False)` raises `ValueError` if a copy would be needed; use `np.asarray(x)` or `copy=None` for "copy only if needed" |
| Default dtypes | Default integer is `int64` (platform pointer size, `np.intp` for indexing); default float is `float64`. Pass `dtype` explicitly when interfacing with C, files or GPUs |
| Views vs copies | Basic slicing and `reshape` of contiguous data give views; fancy (integer or boolean array) indexing always copies. Check with `np.shares_memory(a, b)`, not `.base is` |
| Memory order | C order is row-major (last axis fastest), Fortran order column-major. `a.T` is a view with swapped strides, so `a.T` of a C array is F-contiguous. `a.flags` and `a.strides` expose the layout |
| `Generator` | `np.random.default_rng(seed)` returns `Generator` over `PCG64`. Legacy `np.random.seed` and `RandomState` still exist for compatibility but share one hidden global state. `Generator.spawn(n)` returns `n` independent child generators |
| `SeedSequence` | `SeedSequence(entropy).spawn(n)` yields independent child seed sequences; pass each to `default_rng` or a bit generator. The same entropy always gives the same stream |
| `solve_ivp` | Methods `RK45` (default), `RK23`, `DOP853`, `Radau`, `BDF`, `LSODA`. Stiff problems need `Radau`, `BDF` or `LSODA`. Tolerances `rtol` (default 1e-3) and `atol` (default 1e-6) are loose for publication results. Events are callables with `terminal` and `direction` attributes |
| SciPy removed names | `scipy.integrate.trapz`, `simps` and `cumtrapz` are absent in 1.18.1; use `trapezoid`, `simpson`, `cumulative_trapezoid`. `workers=` is accepted by `scipy.fft` functions and `scipy.optimize.differential_evolution` |
| numba | `@njit` (nopython mode), `parallel=True` with `prange`, `cache=True`, `fastmath=` flags. Threading layers are `tbb`, `omp`, `workqueue`; `NUMBA_NUM_THREADS`, `NUMBA_THREADING_LAYER`, `numba.set_num_threads` control them |
| BLAS threads | The NumPy wheel links OpenBLAS. Control with `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` or `MKL_NUM_THREADS` before import, or `threadpoolctl.threadpool_limits` at run time |
| Matplotlib 3.11 | `plt.figure(layout="constrained")` replaces `constrained_layout=True`. `figsize` accepts a unit as third element, for example `(8.5, 6, "cm")`. Default colormap `viridis`; `cividis` is available; built-in styles include `petroff10` and `tableau-colorblind10`. Default `pdf.fonttype` is 3, journals often want 42 |
| Profilers | `python -m cProfile -o out.prof script.py`, `timeit.repeat`, `kernprof -l -v script.py` with `@profile` (line_profiler 5.1.0) |

## 3. Workflow

1. Establish the goal: result accuracy, run time, memory, or reproducibility for a paper. Ask for array sizes, dtypes, the Python and NumPy versions, and the number of cores.
2. Write the plain, readable version first and a small known-answer test (analytic case, conservation law or reference output).
3. Fix the random seed strategy before measuring: one root `SeedSequence`, children per task or worker.
4. Profile with `cProfile` to find the hot function, then `line_profiler` or `timeit` for the hot lines. Never optimize unmeasured code.
5. Apply changes in this order: algorithm and data layout, vectorization with NumPy and SciPy primitives, `numba` for loops that cannot be vectorized, process parallelism last.
6. After each change, re-run the known-answer test with `np.testing.assert_allclose` and the benchmark; keep the change only if both pass.
7. For figures, build them from saved data in a script that regenerates every file, with sizes in physical units.
8. Record versions (`numpy.show_config()`, `pip freeze`), the root seed and the command that regenerates results.

## 4. Decision Rules

- If a loop body is a few array operations, then vectorize; if it carries a dependency from one iteration to the next (recurrences, state machines, adaptive stepping), then use `numba.njit` rather than contorting the code into array tricks.
- If the problem is a linear-algebra or FFT call, then call `numpy.linalg`, `scipy.linalg` or `scipy.fft` directly; the BLAS and LAPACK kernels beat hand-written numba.
- If broadcasting would create a huge intermediate (for example `(n, n, d)` pairwise differences), then use `scipy.spatial.distance.cdist`, `einsum` with `optimize=True`, or process in blocks.
- If arrays are large and operations chain (`a * b + c`), then use `out=` arguments or in-place operators to avoid temporaries; if memory is not the limit, readability wins.
- If a function is called with Python objects or strings, then numba will not help; keep it in Python.
- If the ODE is smooth and non-stiff, then use `RK45` or `DOP853` with tight tolerances; if step sizes collapse or run time explodes, treat it as stiff and switch to `Radau`, `BDF` or `LSODA`, supplying a Jacobian (`jac=`) or `jac_sparsity=` for large systems.
- If tasks are independent simulations, then use process-level parallelism with spawned seeds; if one NumPy call is slow, then let BLAS threads handle it. Do not stack both without limiting BLAS threads (see section 9).
- If a stochastic result must be reproducible, then derive every stream from one `SeedSequence`; never seed with the clock, the process id or `seed + rank`.
- If a figure goes into a paper, then save vector PDF (or SVG) for line art, raster PNG at 300 dpi or more only for images and dense scatter plots, and size it to the journal column width.
- If the colormap encodes ordered values, then use a perceptually uniform one (`viridis`, `cividis`); never use `jet` or `rainbow`. Distinguish categories by marker or line style as well as color.

## 5. Coding Standards

- Import as `import numpy as np`, `import scipy.integrate as si` or explicit `from scipy.integrate import solve_ivp`; never `from numpy import *`.
- Create a generator once at the entry point (`rng = np.random.default_rng(seed)`) and pass it as a parameter named `rng`. Library code does not call `np.random.seed` or module-level `np.random.*` draw functions.
- State dtypes at array creation (`np.zeros(n, dtype=np.float64)`) in code that crosses a file, C or numba boundary.
- Use `np.asarray(x)` at function entry for array-likes; use `np.ascontiguousarray` only where a kernel needs contiguity.
- Do not rely on array equality for floats: use `np.isclose`, `np.allclose` or `np.testing.assert_allclose(actual, desired, rtol=..., atol=...)` with stated tolerances.
- Write explicit axes (`a.sum(axis=0, keepdims=True)`) so the broadcasting is visible; add shape comments for non-trivial expressions.
- Keep numba kernels small, typed by their inputs, in their own module, and free of Python objects, with a plain NumPy fallback or test reference.
- Name physical quantities with units in docstrings, and keep unit conversion at the boundary of the code.
- Figure scripts set rcParams in one function or `.mplstyle` file, not scattered `plt.xlabel` fontsize arguments.

## 6. Project Structure

```text
project/
├── pyproject.toml
├── src/simlib/
│   ├── model.py            # pure functions: rhs(t, y, params), kernels
│   ├── kernels.py          # numba-compiled hot loops
│   ├── rng.py              # SeedSequence handling, spawn helpers
│   └── runner.py           # parallel driver, writes results
├── scripts/
│   ├── run_experiments.py  # CLI: --seed, --workers, --out
│   └── make_figures.py     # reads results, writes figures/*.pdf
├── styles/paper.mplstyle   # shared rcParams
├── results/                # data files (npz, csv, parquet), gitignored if large
├── figures/                # generated PDFs, regenerated by make_figures.py
└── tests/                  # known-answer and seed-reproducibility tests
```

## 7. Design Patterns

- **Pure right-hand side**: `rhs(t, y, *params)` has no globals or I/O, so it can be passed to `solve_ivp(args=...)`, jitted, or tested on its own. Cost: parameters travel as arguments.
- **Spawned-stream worker**: the parent spawns child `SeedSequence` objects; each worker builds its own `Generator`. Results are identical for any worker count when work is split by task index, not by worker.
- **Chunked broadcasting**: loop over blocks of rows, broadcast within a block. Bounds memory at the cost of a short Python loop.
- **Structure of arrays**: store fields as separate contiguous arrays for vectorized and numba code, instead of arrays of Python objects or heterogeneous structured rows.
- **Preallocate and fill**: `out = np.empty(shape)` followed by slice assignment in a loop avoids repeated concatenation, which is quadratic.
- **Run script plus figure script**: simulations write `.npz` files; figures read them. Re-plotting never reruns a simulation.
- Long variants of the RNG, memory and figure patterns are in [references/rng-reproducibility.md](references/rng-reproducibility.md), [references/numpy-performance.md](references/numpy-performance.md) and [references/matplotlib-papers.md](references/matplotlib-papers.md).

## 8. Best Practices

- Prefer views for read-only access and copy deliberately with `.copy()` before mutating a slice you do not own; a write through a view changes the parent.
- Use `float64` for accumulations. If data are `float32`, pass `dtype=np.float64` to reductions such as `np.sum` and `np.mean` when precision matters.
- Use `np.errstate(divide="raise", invalid="raise")` around code that must not produce silent `inf` or `nan`.
- Compare an optimized version with the slow reference on random inputs before trusting it.
- Save results with enough metadata to rerun them: seed entropy, parameters, package versions, git commit.
- Vectorize over the largest axis, but check that the intermediate arrays fit in memory: `n * itemsize` per array.
- Use `scipy.stats.qmc` (Sobol, Halton) for low-dimensional integrals where plain Monte Carlo converges too slowly; seed it with a `Generator`.
- Report Monte Carlo results with a standard error or confidence interval, not only the mean.

## 9. Performance

- Measure first: `python -m cProfile -o out.prof script.py`, inspect with `python -m pstats out.prof` or `snakeviz`; then `kernprof -l -v script.py` on functions decorated with `@profile`. For micro-benchmarks use `timeit.repeat` and take the minimum, not the mean.
- Memory traffic usually dominates: avoid temporaries, use the contiguous axis in the innermost loop, and keep dtypes as small as accuracy allows.
- Row-wise operations on C-ordered arrays and column-wise operations on F-ordered arrays are fastest; `np.ascontiguousarray` or `np.asfortranarray` once is cheaper than strided access in a hot loop.
- Fancy indexing copies; `a[idx] += 1` ignores repeated indices, `np.add.at` handles them but is slow, and `np.bincount` is the fast path for counting and weighted sums.
- Avoid growing arrays with `np.append` or `np.concatenate` in a loop; collect pieces in a list and concatenate once, or preallocate.
- numba: the first call compiles; use `cache=True` to persist the result, keep types stable across calls, avoid reflected lists, and time after a warm-up call. `fastmath=True` can change results and NaN handling; enable it only after comparing against the exact version.
- Threads: NumPy BLAS calls use all cores by default. With N worker processes each calling BLAS on M cores you oversubscribe; set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 in the worker environment before importing NumPy, or wrap with `threadpoolctl.threadpool_limits(limits=1, user_api="blas")`. Likewise cap numba with `NUMBA_NUM_THREADS`.
- Multiprocessing: pass small arguments (seeds, parameters, indices) and return small results. Large arrays pickled through pipes can cost more than the compute; use shared memory (`multiprocessing.shared_memory`) or memory-mapped files (`np.load(..., mmap_mode="r")`).
- Python threads help only when the called code releases the GIL (NumPy kernels on large arrays, I/O); for pure-Python loops use processes or numba. Behavior on free-threaded Python builds: check the current NumPy and numba documentation.
- Deeper material and a benchmarking checklist: [references/numpy-performance.md](references/numpy-performance.md).

## 10. Security

- Do not load untrusted `.npy` or `.npz` files with `allow_pickle=True`; pickle executes code on load. Keep the default `allow_pickle=False`, and prefer plain arrays, CSV or Parquet for data you receive.
- Do not `pickle.load` or `joblib.load` simulation checkpoints from other people; share arrays in `.npz` instead.
- Build file paths for outputs from fixed directories and validated names (`pathlib.Path`, reject `..` and absolute parts), especially in scripts that take a run name from the command line.
- `numexpr.evaluate` and `eval` on user-supplied expression strings execute attacker-controlled code or consume unbounded resources; parse a restricted grammar instead.
- Never hard-code credentials for data downloads; read tokens from environment variables.
- Random numbers from `numpy.random` are not cryptographically secure. Use `secrets` for tokens, keys or anything an attacker must not predict.

## 11. Testing

- Known-answer tests: integrate `y' = -y` and compare with `exp(-t)` using `assert_allclose(rtol=1e-6)`; compare Monte Carlo estimates with the analytic value inside several standard errors, using a fixed seed so the test is deterministic.
- Reproducibility test: run the pipeline twice with the same root seed and with different worker counts; assert identical arrays (`np.testing.assert_array_equal`).
- Property tests: conservation laws (mass, energy within tolerance), symmetries, shape and dtype of outputs, behavior at size 0 and size 1 arrays.
- Equivalence tests: numba and vectorized versions agree with a plain-Python reference on random inputs, including edge values (`nan`, `inf`, empty).
- Failure paths: assert the code raises on wrong shapes, negative sizes and non-finite input; run suites with `-W error` so a `RuntimeWarning` from overflow or divide-by-zero fails the test.
- Commands: `python -m pytest -q -W error`, and `python -m pytest --durations=10` to spot slow tests. Keep simulation tests small (short horizons, few samples).
- Figures: test that the figure script runs headless with `MPLBACKEND=Agg` and writes the expected files; do not compare pixels.

## 12. Review Checklist

- [ ] No loop over array elements in Python where a NumPy or SciPy primitive exists; any remaining loop is justified by a profile.
- [ ] Every random draw comes from an explicit `Generator`; seeds derive from one `SeedSequence`; workers get spawned children.
- [ ] No removed NumPy or SciPy names (`np.trapz`, `np.in1d`, `scipy.integrate.simps`, `np.float_`).
- [ ] dtypes explicit at file, C and numba boundaries; float accumulations in `float64`.
- [ ] Views versus copies understood for every in-place write on a slice.
- [ ] ODE solver, tolerances and events chosen and stated; stiffness considered.
- [ ] Parallel code limits BLAS and numba threads; no oversubscription.
- [ ] A known-answer test and a reproducibility test exist and pass.
- [ ] No `allow_pickle=True` on external data; no `eval` on user input; output paths validated.
- [ ] Figures are vector PDF or SVG where possible, fonts embedded as Type 42, sized in inches or cm to the column width, colorblind-safe, and regenerable from a script.

## 13. Production Notes

- Pin versions of NumPy, SciPy, numba and Matplotlib in the lock file; numba supports only a range of NumPy versions per release, so upgrade them together and check the numba release notes.
- NumPy and SciPy 2.x-era releases require a recent Python (the PyPI metadata for NumPy 2.5.4 and SciPy 1.18.1 states `>=3.12`, Matplotlib 3.11.2 `>=3.11`, numba 0.68.1 `>=3.10`); check the metadata before choosing an interpreter.
- Code written for NumPy 1.x needs migration for removed aliases and the weak-scalar promotion rules; run the tests with `-W error::DeprecationWarning` on a staging branch to find deprecations before the next release removes them.
- On clusters, set thread variables from the scheduler allocation (for example the number of cores granted), not the node's core count.
- Log the root seed, `numpy.__version__`, the BLAS in use (`numpy.show_config()`) and the number of workers with each result file. Bitwise-identical results across machines are not guaranteed for BLAS-based operations, only for the random stream.
- Cache compiled numba functions with `cache=True`; on read-only or containerized file systems point `NUMBA_CACHE_DIR` at a writable directory.

## 14. Examples

Parallel Monte Carlo with independent, reproducible streams. The result is the same for repeated runs because each task owns a spawned `SeedSequence`:

```python
from concurrent.futures import ProcessPoolExecutor

import numpy as np


def count_hits(seed_seq: np.random.SeedSequence, n: int) -> int:
    rng = np.random.default_rng(seed_seq)
    xy = rng.random((n, 2))
    return int(np.count_nonzero(np.einsum("ij,ij->i", xy, xy) < 1.0))


def estimate_pi(root_seed: int = 20261030, tasks: int = 4, n: int = 1_000_000) -> float:
    children = np.random.SeedSequence(root_seed).spawn(tasks)
    with ProcessPoolExecutor(max_workers=tasks) as pool:
        hits = sum(pool.map(count_hits, children, [n] * tasks))
    return 4.0 * hits / (tasks * n)


if __name__ == "__main__":
    print(estimate_pi())
```

A stiff-capable ODE solve with tight tolerances, dense output times and a terminal event (prey population falls below 0.5):

```python
import numpy as np
from scipy.integrate import solve_ivp


def lotka_volterra(t, y, a, b, c, d):
    prey, pred = y
    return [a * prey - b * prey * pred, -c * pred + d * prey * pred]


def prey_floor(t, y, *args):
    return y[0] - 0.5


prey_floor.terminal = True
prey_floor.direction = -1

sol = solve_ivp(
    lotka_volterra, (0.0, 50.0), [10.0, 5.0], args=(1.1, 0.4, 0.4, 0.1),
    method="LSODA", rtol=1e-8, atol=1e-10,
    t_eval=np.linspace(0.0, 50.0, 501), events=prey_floor,
)
print(sol.status, sol.message, sol.y.shape)
```

A single-column journal figure (3.4 in wide), vector PDF with embedded TrueType fonts:

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6,
})
fig, ax = plt.subplots(figsize=(3.4, 2.4), layout="constrained")
x = np.linspace(0.0, 2.0 * np.pi, 200)
for k, style in enumerate(["-", "--", ":"]):
    ax.plot(x, np.sin(x + k), ls=style, label=f"shift {k}")
ax.set(xlabel="x", ylabel="sin(x + shift)")
ax.legend(frameon=False)
fig.savefig("figure1.pdf")
```

## 15. Common Mistakes

- **Seeding with `seed + rank` or the clock**: streams may overlap or differ between runs. Spawn children from one `SeedSequence`.
- **Calling `np.random.seed` in library code**: it mutates global state for every caller. Pass a `Generator`.
- **Sharing one `Generator` across processes by fork**: children inherit identical state and draw the same numbers. Create a generator inside each worker from its spawned seed.
- **Writing through a view by accident**: `b = a[:, 0]; b[:] = 0` zeroes the parent. Use `.copy()` when the data must be independent, and test with `np.shares_memory`.
- **Assuming `reshape` copies or views**: it returns a view when strides allow and a copy otherwise. Do not rely on either; use `ravel` or `reshape` and treat the result as read-only, or `.copy()` explicitly.
- **`a[idx] += 1` with repeated indices**: only one increment applies per element. Use `np.add.at` or `np.bincount`.
- **Integer overflow**: `np.uint8(200) + np.uint8(100)` wraps to 44. Cast to a wider dtype before arithmetic.
- **Loose ODE tolerances**: the `solve_ivp` defaults (`rtol=1e-3`, `atol=1e-6`) are not suitable for reported results. Set and justify them, and compare two methods.
- **Using an explicit solver on stiff problems**: run time explodes with tiny steps. Switch to `Radau`, `BDF` or `LSODA`.
- **Timing numba including compilation**: the first call compiles. Warm up, then time.
- **Oversubscribed threads**: N processes times M BLAS threads slows everything. Cap BLAS and numba threads in workers.
- **Mean of timings instead of minimum**: system noise only adds time. Use `min(timeit.repeat(...))`.
- **Raster figures for line art**: blurry in print and large. Save PDF or SVG; raster only for images.
- **Default Type 3 fonts in PDF**: some publishers reject them. Set `pdf.fonttype` to 42.
- **`jet`/`rainbow` colormaps and red-green pairs**: misleading luminance and unreadable for color-vision deficiency. Use `viridis` or `cividis` and add line styles.
- **Resizing figures in LaTeX**: scaling a PDF changes font size. Make the figure at final size in Matplotlib.

## 16. References

- [references/numpy-performance.md](references/numpy-performance.md): dtypes, strides and layout, broadcasting patterns, in-place operations, numba and parallelism notes, and a profiling and benchmarking routine.
- [references/rng-reproducibility.md](references/rng-reproducibility.md): `Generator`, bit generators, `SeedSequence` spawning, worker patterns, quasi-random sequences and storing seeds with results.
- [references/matplotlib-papers.md](references/matplotlib-papers.md): rcParams for papers, sizing to column width, vector output, fonts, colorblind-safe colors and a figure-script template.
- NumPy documentation: https://numpy.org/doc/stable/
- NumPy random Generator: https://numpy.org/doc/stable/reference/random/index.html
- SciPy documentation: https://docs.scipy.org/doc/scipy/
- numba documentation: https://numba.readthedocs.io/
- Matplotlib documentation: https://matplotlib.org/stable/
- line_profiler: https://github.com/pyutils/line_profiler
- threadpoolctl: https://github.com/joblib/threadpoolctl
- Python profilers (cProfile) and timeit: https://docs.python.org/3/library/profile.html and https://docs.python.org/3/library/timeit.html
