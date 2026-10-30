# Random Numbers and Reproducibility

Reference for `numpy.random.Generator`, `SeedSequence` and parallel Monte Carlo, verified on NumPy 2.5.4 and SciPy 1.18.1 (2026-10). The goal: results that are statistically sound, identical on rerun, and independent of the number of workers.

## Contents

1. [Generator basics](#1-generator-basics)
2. [SeedSequence and spawning](#2-seedsequence-and-spawning)
3. [Parallel patterns](#3-parallel-patterns)
4. [Making results independent of worker count](#4-making-results-independent-of-worker-count)
5. [Legacy API](#5-legacy-api)
6. [Variance reduction and quasi-random sequences](#6-variance-reduction-and-quasi-random-sequences)
7. [Recording seeds with results](#7-recording-seeds-with-results)
8. [Reproducibility limits](#8-reproducibility-limits)

## 1. Generator basics

- `rng = np.random.default_rng(seed)` returns a `Generator` backed by `PCG64`. `seed` may be an int, a sequence of ints, a `SeedSequence`, a `BitGenerator` or an existing `Generator`; `None` pulls fresh OS entropy.
- Draw with methods: `rng.random(size)`, `rng.standard_normal(size)`, `rng.normal(loc, scale, size)`, `rng.integers(low, high, size)`, `rng.choice(a, size, replace=False)`, `rng.permutation(x)`, `rng.shuffle(x)`, `rng.exponential`, `rng.poisson`, `rng.multivariate_normal`.
- `rng.integers(low, high)` excludes `high` unless `endpoint=True`.
- Fill an existing buffer with `rng.standard_normal(n, out=buf)` (also `random`, `standard_exponential`) to avoid allocation in time-stepping loops; the dtype must be `float64` or `float32`.
- Other bit generators in `numpy.random`: `PCG64DXSM`, `Philox` (counter based), `SFC64`, `MT19937`. `PCG64` is the default and a good general choice; use `Philox` when you want counter-based streams that can be jumped to arbitrary positions.
- Create the generator at the program entry point and pass it down as `rng`. Functions that accept `rng` are deterministic under test.
- The stream of a given seed is not guaranteed to be identical across NumPy releases for every method (algorithm improvements are allowed to change the values). Pin the NumPy version for bit-for-bit reproducibility, and treat tests as statistical or tolerance-based where that is enough.

## 2. SeedSequence and spawning

```python
import numpy as np

root = np.random.SeedSequence(20261030)
children = root.spawn(4)                       # 4 independent SeedSequence objects
rngs = [np.random.default_rng(c) for c in children]
```

- A `SeedSequence` hashes entropy into high-quality state and can spawn children whose streams are designed not to overlap in practice, regardless of how similar the parent entropy is.
- Spawning is deterministic and stateful: each `root.spawn(k)` call continues numbering after the previous one (`n_children_spawned`). Spawn all children for a stage in one call, or spawn in a fixed order.
- `rng.spawn(n)` on a `Generator` (and `bit_generator.spawn(n)`) returns `n` independent `Generator` objects derived from the generator's seed sequence. Use it when you receive a `rng` argument and need sub-streams.
- `rng.bit_generator.seed_seq.entropy` returns the entropy of a generator built from an int seed; with `default_rng(None)` it holds the random entropy chosen at start, which you should log.
- Never derive streams by `default_rng(seed + i)`, `default_rng(hash(...))`, the clock, `os.getpid()` or by sharing one `Generator` across forked processes. These patterns risk correlated or duplicated streams.
- Jumping (`PCG64.jumped`, `Philox.jumped`, `advance`) exists, but spawning is the simpler and recommended way to get independent streams.
- A hierarchical layout is fine: `SeedSequence(root_entropy, spawn_key=(experiment_id, replicate_id))` constructs a reproducible child directly, so replicate 17 of experiment 3 can be rerun alone without running replicates 0 to 16.

## 3. Parallel patterns

Process pool, one spawned seed per task:

```python
from concurrent.futures import ProcessPoolExecutor

import numpy as np


def one_replicate(seed_seq: np.random.SeedSequence, n: int) -> float:
    rng = np.random.default_rng(seed_seq)
    return float(rng.standard_normal(n).mean())


def run(root_seed: int, n_replicates: int, n: int) -> np.ndarray:
    seeds = np.random.SeedSequence(root_seed).spawn(n_replicates)
    with ProcessPoolExecutor() as pool:
        return np.array(list(pool.map(one_replicate, seeds, [n] * n_replicates)))


if __name__ == "__main__":
    print(run(7, 8, 100_000))
```

- `SeedSequence` objects are small and picklable; send them to workers instead of generators or large arrays.
- Threads: each thread needs its own `Generator`. A `Generator` is not safe to use from several threads at once without external locking. The sampling methods release the GIL for large draws, so thread-parallel generation with per-thread generators is valid.
- numba: the `np.random` functions inside jitted code use numba's own per-thread state. It is not the same stream as a NumPy `Generator` created outside; draw arrays outside and pass them in when exact reproducibility against NumPy matters.
- When using `multiprocessing` with `fork`, never create the generator before forking and reuse it in children. Create it in the worker from its seed.
- Job arrays on a scheduler: use the array index as the `spawn_key` component, with one shared root entropy for the whole study.

## 4. Making results independent of worker count

Reproducibility should not change when you move from 4 to 64 workers.

- Assign a seed per task (replicate, path batch, chain), not per worker. Tasks are the units with identity; workers are interchangeable.
- Fix the task partition in the input (for example 1000 batches of 10,000 paths) and let the pool schedule them freely. Combine results in task order, not in completion order (`pool.map` preserves order; `as_completed` does not).
- Floating-point sums depend on order. Reduce task results in a fixed order (for example `np.sum` over an array indexed by task id) to get bit-identical totals.
- Test it: run with `workers=1` and `workers=4` and assert the arrays are equal with `np.testing.assert_array_equal`.

## 5. Legacy API

- `np.random.seed(s)`, `np.random.rand`, `np.random.randn` and `np.random.RandomState` still exist and use a single hidden global stream (`MT19937`). They exist for compatibility; new code uses `Generator`.
- Third-party code that calls the global state makes your runs depend on import order and call counts. Seed it too (`np.random.seed`) only as a stopgap in scripts, and say so.
- `RandomState` values are frozen for backward compatibility; `Generator` values may change when algorithms improve.
- Python's `random` module is a separate generator; seed it separately if used.
- Libraries often accept `random_state=` or `seed=` and treat a `Generator` as valid input; SciPy functions accept `seed=` (int, `Generator` or `RandomState`). Pass a spawned generator rather than an int when you call several in a row.

## 6. Variance reduction and quasi-random sequences

- Antithetic variates: use `z` and `-z` in pairs; halves the number of draws for symmetric payoffs and often cuts variance.
- Control variates: subtract a correlated quantity with known expectation; fit the coefficient from a pilot run.
- Common random numbers: compare two configurations using the same spawned seed so differences are not buried in noise.
- Quasi-Monte Carlo with `scipy.stats.qmc`: `qmc.Sobol(d=2, scramble=True, seed=rng)` and `.random_base2(m)` give `2**m` points in `[0, 1)^d`; Sobol sequences keep their balance properties at powers of two. `qmc.Halton` and `qmc.LatinHypercube` are also available. Use scrambling with several independent replicates to estimate error.
- Report the standard error: `sem = samples.std(ddof=1) / np.sqrt(len(samples))`, and a confidence interval. Do not report more digits than the error supports.
- Check convergence by doubling `n` and observing the error shrink roughly as `1/sqrt(n)` for plain Monte Carlo.

## 7. Recording seeds with results

- Store the entropy and spawn information next to the data: root entropy, number of tasks, task index, `numpy.__version__`, parameters, git commit.
- Example metadata save:

```python
import json
import platform

import numpy as np

meta = {
    "root_entropy": 20261030,
    "task": 3,
    "numpy": np.__version__,
    "python": platform.python_version(),
}
np.savez("run_0003.npz", samples=np.zeros(10), meta=json.dumps(meta))
```

- When a seed was drawn from OS entropy (`default_rng()`), read it back from `rng.bit_generator.seed_seq.entropy` and write it down before the run starts, so a surprising result can be replayed.
- Save generator state mid-run for checkpointing with `rng.bit_generator.state` (a plain dict of ints). Restore it by assigning it to `rng.bit_generator.state`.
- Prefer `.npz`, CSV or Parquet over pickle for checkpoints that others will load.

## 8. Reproducibility limits

- The random stream is deterministic. Floating-point results from BLAS-backed operations (`@`, `np.linalg`, `np.dot`) can differ between machines, thread counts and library builds in the last bits. Compare with tolerances; do not assert exact equality on them.
- Parallel reductions with changing thread counts reorder additions. Fix the order or accept a tolerance.
- Different NumPy versions may change generator output for some methods; pin versions in the lock file when exact reproduction is required.
- Hash-based ordering in Python sets and dicts of strings varies per process unless `PYTHONHASHSEED` is fixed; do not iterate over sets to assign seeds or tasks.
- Record the full environment: `pip freeze`, `numpy.show_config()`, CPU type, thread settings.
