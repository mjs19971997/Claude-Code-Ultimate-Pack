# Simulation Output Analysis

Statistical treatment of discrete-event and Monte Carlo simulation output: independent replications, seeds, warm-up removal, batch means, autocorrelation and the number of replications for a target confidence interval. Common random numbers, factorial designs and regression are in [experiment-design.md](experiment-design.md). The examples use a small M/M/1 queue (Lindley recursion, plain NumPy) so they run without a simulator; the same analysis applies to output of ns-3, OMNeT++, SimPy or a custom model. Code blocks are self-contained and were run on SciPy 1.18.1, statsmodels 0.15.0, NumPy 2.5.4 and pandas 3.1.0 (2026-10).

## Contents

1. [Why simulation output needs special treatment](#1-why-simulation-output-needs-special-treatment)
2. [Independent replications](#2-independent-replications)
3. [Seeds and random streams](#3-seeds-and-random-streams)
4. [Warm-up removal](#4-warm-up-removal)
5. [Batch means for a single long run](#5-batch-means-for-a-single-long-run)
6. [Autocorrelation](#6-autocorrelation)
7. [How many replications](#7-how-many-replications)

## 1. Why simulation output needs special treatment

- Successive outputs of one run (delays of consecutive packets, queue lengths over time) are positively autocorrelated. The textbook standard error `s / sqrt(n)` computed on them is far too small, and the confidence interval is falsely tight.
- A run starts in an artificial state (empty queue, no traffic), so early observations are biased. Steady-state estimates need the transient removed; terminating simulations (a fixed scenario with a natural end) do not.
- The statistically valid unit is one independent observation: a replication mean, or a batch mean. n counts those, not packets.
- Decide first whether the question is about a terminating or a steady-state behaviour; that fixes the method.

The model used below:

```python
import numpy as np

def mm1_waits(n_customers, lam, mu, rng):
    """Waiting time in queue of successive customers (Lindley recursion), M/M/1, starts empty."""
    inter = rng.exponential(1 / lam, n_customers)
    serv = rng.exponential(1 / mu, n_customers)
    w = np.empty(n_customers)
    w[0] = 0.0
    for i in range(1, n_customers):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w

rng = np.random.default_rng(0)
w = mm1_waits(20_000, lam=0.8, mu=1.0, rng=rng)
print("theory Wq = rho / (mu - lam) =", round(0.8 / (1.0 - 0.8), 3))   # 4.0
print("one-run mean:", round(w.mean(), 2))
```

## 2. Independent replications

```python
import numpy as np
from scipy import stats

def mm1_mean_wait(rng, n=20_000, warmup=2_000, lam=0.8, mu=1.0):
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w[warmup:].mean()              # one number per replication

ss = np.random.SeedSequence(2026)
seeds = ss.spawn(20)                      # independent child seeds
means = np.array([mm1_mean_wait(np.random.default_rng(s)) for s in seeds])

n = means.size
half = stats.t.ppf(0.975, n - 1) * stats.sem(means)
print(f"mean wait {means.mean():.2f} +- {half:.2f} (95% CI half-width, n={n} replications)")
print("theory 4.00")
```

- Each replication is the same model with an independent random stream and the same warm-up. The replication summary (mean, a quantile, a count) is one observation; the set of summaries is an i.i.d. sample for the t interval.
- Use at least 10 replications for a t interval; fewer makes the interval very wide and the normality assumption of the replication means matters more.
- Report the number of replications, the run length per replication, the warm-up length and the seed policy.
- Percentiles and rare-event probabilities are also estimated per replication and then averaged, or pooled with a bootstrap over replications.

## 3. Seeds and random streams

```python
import numpy as np

root = np.random.SeedSequence(12345)          # record this number with the results
children = root.spawn(3)                      # independent, non-overlapping streams
streams = [np.random.default_rng(c) for c in children]
print([round(float(g.random()), 4) for g in streams])

# Reproducible: the same root gives the same streams
again = [np.random.default_rng(c) for c in np.random.SeedSequence(12345).spawn(3)]
print([round(float(g.random()), 4) for g in again])
```

- `SeedSequence.spawn` is the documented way to create independent streams for replications and parallel workers; it removes the need to hand-pick seeds and avoids accidental reuse of one seed in two places.
- Use separate streams for separate sources of randomness (arrivals, service, failures) so that changing one part of the model does not shift the others. This is a prerequisite for common random numbers.
- Simulators have their own seed and run-number mechanism (ns-3 has `RngSeedManager` with a seed and a run number; see ns3-expert). Follow the tool's documented practice for independent replications and record the values used.
- Store seeds in the result file for every run.

## 4. Warm-up removal

```python
import numpy as np

def mm1_waits(n, lam, mu, rng):
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w

# Welch's graphical method: average several replications point-wise, then smooth.
reps = np.array([mm1_waits(6000, 0.8, 1.0, np.random.default_rng(s)) for s in range(30)])
avg = reps.mean(axis=0)
window = 100
smooth = np.convolve(avg, np.ones(window) / window, mode="valid")
print("smoothed waits at i = 0, 250, 500, 1000, 4000:", np.round(smooth[[0, 250, 500, 1000, 4000]], 2))

# MSER-5 truncation rule on the averaged series: pick the cut that minimises the
# standard error of the remaining batch means.
def mser5(x, batch=5):
    m = len(x) // batch
    b = x[: m * batch].reshape(m, batch).mean(axis=1)
    best, best_d = None, np.inf
    for d in range(0, m // 2):
        tail = b[d:]
        stat = tail.var() / len(tail)
        if stat < best_d:
            best, best_d = d, stat
    return best * batch

print("MSER-5 truncation point (observations):", mser5(avg))
```

- Warm-up is needed for steady-state metrics. Pick the cut point from pilot runs: plot the point-wise average over at least 5 to 10 replications against time (Welch), smooth it, and choose the point where it levels off. Err on the long side; deleting too much costs a little precision, deleting too little biases the result.
- MSER-5 is an automatic rule applied per run; it can truncate too little when the series is still drifting, so check the result against the plot.
- Apply the same warm-up to all configurations compared, and choose it for the slowest-converging configuration (highest utilisation).
- Use time-based warm-up for time-weighted metrics (queue length over time), and observation-count warm-up for per-customer metrics; do not mix.
- Initial conditions that start near steady state (pre-loaded queue, loaded cache) shorten the transient but must be justified.

## 5. Batch means for a single long run

```python
import numpy as np
from scipy import stats

def mm1_waits(n, lam, mu, rng):
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w

w = mm1_waits(220_000, 0.8, 1.0, np.random.default_rng(5))[20_000:]   # drop warm-up

def batch_means_ci(x, n_batches=20, level=0.95):
    m = len(x) // n_batches
    b = x[: m * n_batches].reshape(n_batches, m).mean(axis=1)
    half = stats.t.ppf(0.5 + level / 2, n_batches - 1) * stats.sem(b)
    r1 = np.corrcoef(b[:-1], b[1:])[0, 1]                 # lag-1 autocorrelation of the batch means
    return b.mean(), half, r1

mean, half, r1 = batch_means_ci(w)
naive = stats.t.ppf(0.975, len(w) - 1) * stats.sem(w)
print(f"batch means: {mean:.2f} +- {half:.2f} (lag-1 r of batches {r1:.2f})")
print(f"naive iid half-width: {naive:.3f}  <- too small")
```

- Split the post-warm-up series into 10 to 30 contiguous batches of equal size, take each batch mean, and treat the batch means as approximately independent. The batch size must be large enough that the lag-1 autocorrelation of batch means is small (below about 0.1 to 0.2); if not, double the batch size.
- Fewer, larger batches reduce correlation but widen the t quantile; 20 to 30 is a common compromise.
- Batch means need a long run; replication-deletion is simpler when runs are cheap. Batch means pay the warm-up cost once.
- The naive interval, ignoring autocorrelation, can be several times too narrow at high utilisation.

## 6. Autocorrelation

```python
import numpy as np
from statsmodels.tsa.stattools import acf
from statsmodels.stats.diagnostic import acorr_ljungbox

def mm1_waits(n, lam, mu, rng):
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w

w = mm1_waits(50_000, 0.8, 1.0, np.random.default_rng(3))[5_000:]
r = acf(w, nlags=50)
print("acf lags 1, 5, 20, 50:", np.round(r[[1, 5, 20, 50]], 3))

# Effective sample size from the integrated autocorrelation time (initial positive sequence)
tau = 1.0
for k in range(1, len(r)):
    if r[k] <= 0:
        break
    tau += 2 * r[k]
print(f"integrated autocorr. time ~ {tau:.1f}, effective n ~ {len(w) / tau:.0f} of {len(w)}")
print(acorr_ljungbox(w[:5000], lags=[10], return_df=True).round(4))
```

- `statsmodels.tsa.stattools.acf(x, nlags=...)` returns the sample autocorrelations, lag 0 first. A slowly decaying acf means strong dependence; the effective sample size is roughly `n / tau`, with `tau = 1 + 2 * sum(rho_k)`.
- The truncated sum above is a rough estimate (the acf of heavy-tailed queueing output decays slowly and the estimate is noisy at long lags); use it as a diagnostic, not as the basis for a CI. Use replications or batch means for the interval.
- Autocorrelation grows with utilisation: M/M/1 at rho = 0.95 needs far longer runs than at 0.5.
- `acorr_ljungbox` tests for any autocorrelation up to the given lags; with simulation output it nearly always rejects, so it confirms the need for batching rather than guiding it.

## 7. How many replications

```python
import numpy as np
from scipy import stats

def mm1_mean_wait(seed, n=10_000, warmup=1_000, lam=0.7, mu=1.0):
    rng = np.random.default_rng(seed)
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w[warmup:].mean()

def replications_for_halfwidth(pilot, target, level=0.95):
    """Smallest n with t_{n-1} * s / sqrt(n) <= target, using the pilot standard deviation."""
    s = np.std(pilot, ddof=1)
    n = max(len(pilot), 2)
    while stats.t.ppf(0.5 + level / 2, n - 1) * s / np.sqrt(n) > target:
        n += 1
    return n

pilot = [mm1_mean_wait(s) for s in range(100, 110)]
print("pilot sd:", round(float(np.std(pilot, ddof=1)), 3))
print("replications for half-width 0.05:", replications_for_halfwidth(pilot, 0.05))

# Sequential procedure: add replications until the relative half-width is below 2%
vals, seed = list(pilot), 200
while True:
    n = len(vals)
    half = stats.t.ppf(0.975, n - 1) * stats.sem(vals)
    if n >= 10 and half / abs(np.mean(vals)) < 0.02:
        break
    vals.append(mm1_mean_wait(seed)); seed += 1
print(f"stopped at n={n}: mean {np.mean(vals):.3f} +- {half:.3f}")
```

- The half-width is `t_{n-1,1-alpha/2} * s / sqrt(n)`. Halving it needs four times as many replications. Compute `n` from a pilot's `s`, then confirm with the final run.
- The sequential rule (add replications until a relative or absolute precision target is met) is valid when the minimum n is at least 10 and the stopping rule is fixed in advance. Intervals from very small stopping n are slightly optimistic.
- Choose the target in terms of the decision: the half-width must be smaller than the differences that matter.
- Multiple output metrics need replications for the worst one. Rare-event probabilities need many more (see [confidence-intervals-bootstrap.md](confidence-intervals-bootstrap.md) for the zero-event bound).
