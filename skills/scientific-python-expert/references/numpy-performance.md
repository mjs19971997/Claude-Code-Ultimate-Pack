# NumPy Performance and Memory Layout

Deep notes for NumPy 2.5.x, SciPy 1.18.x and numba 0.68.x (2026-10): dtypes, strides, views and copies, broadcasting, in-place work, numba, parallelism and a measurement routine. Behaviors below were run on those versions with Python 3.13.

## Contents

1. [Dtypes and promotion](#1-dtypes-and-promotion)
2. [Strides, views and copies](#2-strides-views-and-copies)
3. [C and Fortran order](#3-c-and-fortran-order)
4. [Broadcasting and vectorization patterns](#4-broadcasting-and-vectorization-patterns)
5. [Temporaries and in-place work](#5-temporaries-and-in-place-work)
6. [numba](#6-numba)
7. [Parallelism and thread control](#7-parallelism-and-thread-control)
8. [Profiling and benchmarking routine](#8-profiling-and-benchmarking-routine)

## 1. Dtypes and promotion

- Default float is `float64`; default integer is `int64` (`np.dtype(int)` printed `int64` on Linux). Pass `dtype` explicitly across file, C and numba boundaries.
- Python scalars are "weak": `np.float32(3) + 3.0` is `float32`. A NumPy `float64` scalar or array operand still promotes to `float64`.
- Fixed-width integers wrap: `np.uint8(200) + np.uint8(100)` gives `44` and emits a `RuntimeWarning` for scalars; arrays wrap silently. Cast to a wider type before summing or multiplying small integers, or request `dtype=` in the reduction (`a.sum(dtype=np.int64)`).
- Reductions on `float32` accumulate in `float32` for many operations (pairwise summation reduces, but does not remove, the error). Use `dtype=np.float64` for `sum` and `mean` when precision matters.
- Use `np.finfo(dtype).eps` and `np.iinfo(dtype)` for limits instead of hard-coded constants.
- `np.array(x, copy=False)` raises `ValueError` when a copy is needed. For "copy only if needed" use `np.asarray(x)` or `np.array(x, copy=None)`.
- Names removed from the main namespace in the 2.x line and absent in 2.5.4: `np.float_`, `np.Inf`, `np.NaN`, `np.in1d`, `np.row_stack`, `np.trapz`, `np.asfarray`, `np.round_`, `np.product`, `np.cumproduct`. Replacements: `np.float64`, `np.inf`, `np.nan`, `np.isin`, `np.vstack`, `np.trapezoid`, `np.asarray(..., dtype=float)`, `np.round`, `np.prod`, `np.cumprod`.
- SciPy 1.18.1 no longer has `scipy.integrate.trapz`, `simps`, `cumtrapz`; use `trapezoid`, `simpson`, `cumulative_trapezoid`.

## 2. Strides, views and copies

An array is a buffer plus `shape`, `strides` (bytes to step per axis) and `dtype`. Many operations only change the metadata.

```python
import numpy as np

a = np.arange(12, dtype=np.float64).reshape(3, 4)
print(a.strides)                     # (32, 8): row-major
print(a.T.strides)                   # (8, 32): transpose is a view
print(np.shares_memory(a, a[:, ::2]))   # True: basic slicing -> view
print(np.shares_memory(a, a[[0, 1]]))   # False: fancy indexing -> copy
```

| Operation | Result |
|---|---|
| Basic slice `a[1:3, ::2]`, `a.T`, `a.swapaxes`, `np.broadcast_to`, `a.view(dtype)` | View |
| Integer-array or boolean-mask indexing `a[idx]`, `a[mask]` | Copy |
| `a.reshape(...)`, `a.ravel()` | View when strides allow, copy otherwise |
| `a.flatten()`, `np.array(a)`, `a.copy()` | Always a copy |
| `np.ascontiguousarray(a)` | No copy if already C-contiguous |

- Decide by `np.shares_memory(a, b)` (exact) or `np.may_share_memory` (fast, bounds only), not by inspecting `.base`, which can point to an intermediate array.
- Assigning through a view modifies the parent. Copy before mutating a slice that belongs to the caller.
- Boolean masks and fancy indices on the left side of an assignment write in place (`a[mask] = 0`), but `a[mask][0] = 1` writes into a temporary copy and is lost.
- `np.lib.stride_tricks.sliding_window_view(x, w)` gives a read-only windowed view, safe for rolling statistics. `as_strided` can read or write outside the buffer when given wrong strides; avoid it unless `sliding_window_view` or `broadcast_to` cannot express the layout.
- `np.broadcast_to` returns a read-only view with zero strides: no memory is allocated, and writing is blocked on purpose.

## 3. C and Fortran order

- C order: last axis varies fastest in memory. Fortran order: first axis fastest. `a.flags["C_CONTIGUOUS"]` and `a.flags["F_CONTIGUOUS"]` report which holds; a transposed C array is F-contiguous.
- Loop so the innermost loop runs along the contiguous axis. Reductions along the contiguous axis are faster; for example `a.sum(axis=1)` on a C array beats `a.sum(axis=0)` for large arrays (measure on your sizes).
- LAPACK routines are column-major internally. SciPy and NumPy handle layout, but passing the wrong order can cost a hidden copy. If a hot loop repeatedly operates column-wise, create the array with `order="F"` or call `np.asfortranarray` once.
- `np.empty_like(a, order="K")` keeps the memory layout of `a`; `order="C"` forces C.
- Use `a.flags.writeable = False` to mark an array read-only; it protects shared inputs.
- Memory-mapped files: `np.load("big.npy", mmap_mode="r")` and `np.memmap` read lazily; sequential access along the contiguous axis keeps the page cache effective.

## 4. Broadcasting and vectorization patterns

Broadcasting aligns shapes from the trailing axis; axes of size 1 stretch. Use `None` or `np.newaxis` to insert axes.

```python
import numpy as np

x = np.random.default_rng(0).standard_normal((1000, 3))   # (n, d)
c = np.random.default_rng(1).standard_normal((5, 3))      # (k, d)
d2 = ((x[:, None, :] - c[None, :, :]) ** 2).sum(axis=-1)  # (n, k) squared distances
```

- The intermediate `(n, k, d)` array above costs `n*k*d*8` bytes. For large `n*k`, use `scipy.spatial.distance.cdist(x, c, "sqeuclidean")` or the expansion `|x|^2 - 2 x.c + |c|^2` with a matrix product, and clip small negative results.
- `np.einsum("ij,ij->i", a, b)` computes row-wise dot products without a temporary; `optimize=True` lets `einsum` pick a contraction order for multi-operand expressions.
- `np.vecdot`, `np.matvec` and `np.vecmat` exist in 2.5.4 for batched products over the last axes.
- Conditional logic: `np.where(cond, a, b)` evaluates both branches; guard operations that can fail inside the untaken branch (`np.log` of negatives) with `where=` in the ufunc or `np.errstate`.
- Many ufuncs take `where=` and `out=`: `np.divide(a, b, out=np.zeros_like(a), where=b != 0)` avoids division warnings.
- Counting and grouping: `np.bincount(idx, weights=w, minlength=m)` is the fast path for grouped sums; `np.add.at(out, idx, vals)` handles repeated indices but is slower; `np.unique(x, return_counts=True)` for distinct values.
- Cumulative and recurrent scans (`np.cumsum`, `np.maximum.accumulate`, `scipy.signal.lfilter`) cover many loops that look sequential.
- Sorting-based tricks (`np.searchsorted`, `np.argpartition`) replace many nested loops with O(n log n) work.

## 5. Temporaries and in-place work

- Each binary operation allocates a result array. `a * b + c` creates two. For large arrays use `np.multiply(a, b, out=tmp); tmp += c`, or in-place operators when the left operand may be overwritten.
- In-place operators keep the left dtype: `int_array += 0.5` raises a casting error under the default `same_kind` rule instead of truncating. Use an explicit float array.
- Fusing many element-wise steps in one pass is what numba or `numexpr` do; for moderately sized arrays that fit in cache, plain NumPy is often as fast.
- Reuse work buffers across iterations in time-stepping loops: allocate once, update with `out=`.
- `rng.standard_normal(size, out=buf)` fills an existing float64 or float32 buffer (see rng-reproducibility.md).
- Large temporaries can be released earlier with `del tmp`; peak memory matters on clusters, so check it with `/usr/bin/time -v` or `resource.getrusage`.

## 6. numba

- `@njit` compiles in nopython mode; Python objects, dicts of mixed types and most third-party libraries are unsupported. `@jit` without `nopython` is not a safe default.
- First call compiles. Use `cache=True` to store machine code (set `NUMBA_CACHE_DIR` where the source directory is read-only). Benchmark after a warm-up call.
- `parallel=True` turns on automatic parallelization; write `for i in prange(n)` for explicit parallel loops. Iterations must be independent; scalar reductions inside `prange` (`s += x[i]`) are recognized, array element races are not.
- Do not draw from a shared global generator inside `prange`: each numba thread keeps its own internal random state for `np.random` calls inside jitted code, seeded independently of the NumPy generator outside. For reproducible parallel draws, generate the random numbers outside with a `Generator`, or draw inside with explicit per-iteration seeding you control.
- Threading layer: numba picks from `tbb`, `omp` and `workqueue`. Set `NUMBA_THREADING_LAYER` to force one; `workqueue` is not safe to call concurrently from several Python threads. Control thread counts with `NUMBA_NUM_THREADS` before import or `numba.set_num_threads(n)` at run time (not above the launched count).
- `fastmath=True` permits reassociation and assumes no NaN or inf; results can differ in the last bits and NaN checks may be optimized away. Compare to the default build before enabling it.
- Keep argument types stable: switching between `float32` and `float64` or between C and F layouts triggers a new compilation per signature.
- `@vectorize` and `@guvectorize` build ufuncs; useful when you want broadcasting plus compiled speed.
- numba releases support a limited range of NumPy and Python versions. Check the release notes before upgrading NumPy.
- Behavior on free-threaded Python builds is not covered here: check the current numba and NumPy documentation.

## 7. Parallelism and thread control

| Layer | How to limit |
|---|---|
| OpenBLAS (default in NumPy wheels) | `OPENBLAS_NUM_THREADS` or `OMP_NUM_THREADS` |
| MKL builds (conda or other distributions) | `MKL_NUM_THREADS` or `OMP_NUM_THREADS` |
| numba | `NUMBA_NUM_THREADS`, `numba.set_num_threads` |
| SciPy functions with `workers=` | pass `workers=n` (accepted by `scipy.fft` functions and `scipy.optimize.differential_evolution`) |
| Run time, any library | `threadpoolctl.threadpool_limits(limits=1, user_api="blas")` as a context manager; `threadpool_info()` lists loaded pools |

- Environment variables must be set before the library is imported (in the launching shell, a job script, or at the top of the entry script before `import numpy`).
- Choose one level of parallelism: many processes with 1 BLAS thread each for independent simulations, or one process with BLAS threads for large matrix work.
- `concurrent.futures.ProcessPoolExecutor` suits independent tasks; submit task descriptions (seed, parameters), not big arrays. Under the `spawn` start method (default on Windows and macOS, and a choice on Linux), worker code must be importable and the entry point guarded by `if __name__ == "__main__":`.
- Chunk many tiny tasks (`pool.map(f, items, chunksize=...)`); per-task overhead is on the order of a pickle round trip.
- Share a read-only array with workers through `multiprocessing.shared_memory.SharedMemory` or a memory-mapped `.npy` file instead of pickling it per task.
- `joblib.Parallel` is a real alternative with memmapping of large arrays; it is a separate package.

## 8. Profiling and benchmarking routine

1. Reproduce with a fixed seed and a representative size.
2. `python -m cProfile -o out.prof script.py`, then `python -m pstats out.prof` (commands `sort cumtime`, `stats 20`) or a viewer such as `snakeviz out.prof`.
3. Decorate the hot function with `@profile` and run `kernprof -l -v script.py` (line_profiler 5.1.0); the decorator is injected by `kernprof`, so remove it before normal runs.
4. Micro-benchmark candidates with `timeit.repeat(stmt_callable, number=N, repeat=5)` and use `min(...) / N`. Run large benchmarks with the same BLAS thread setting as production.
5. Check memory with `tracemalloc` for Python allocations (NumPy registers its data allocations with it) or the OS-level peak from `/usr/bin/time -v`.
6. Change one thing, re-run the correctness test (`np.testing.assert_allclose`), record before and after, and keep the notes with the commit message.
7. Stop when the profile is flat or the target is met; a 10 percent gain that costs readability is rarely worth it.
