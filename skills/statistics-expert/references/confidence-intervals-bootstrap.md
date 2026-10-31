# Confidence Intervals and the Bootstrap

How to compute and report confidence intervals for means, differences, proportions and arbitrary statistics: t-based intervals, bootstrap percentile and BCa intervals with `scipy.stats.bootstrap`, paired and clustered resampling, and when the bootstrap fails. Code blocks are self-contained and were run on SciPy 1.18.1 and NumPy 2.5.4 (2026-10).

## Contents

1. [What a confidence interval means](#1-what-a-confidence-interval-means)
2. [t-based intervals](#2-t-based-intervals)
3. [scipy.stats.bootstrap](#3-scipystatsbootstrap)
4. [Percentile versus BCa](#4-percentile-versus-bca)
5. [Differences and paired data](#5-differences-and-paired-data)
6. [Proportions](#6-proportions)
7. [When the bootstrap fails](#7-when-the-bootstrap-fails)
8. [Reporting](#8-reporting)
9. [R equivalents](#9-r-equivalents)

## 1. What a confidence interval means

- A 95% confidence interval is produced by a procedure that covers the true parameter in 95% of repeated experiments under the model's assumptions. A single computed interval either contains the truth or does not; it is not a 95% probability statement about this interval.
- The width shrinks like `1/sqrt(n)`. To halve the half-width, collect four times the data.
- Overlapping intervals of two group means do not imply a non-significant difference; compute the interval of the difference itself.
- The interval describes uncertainty about a parameter (the mean). It is not the range of the data. A prediction interval or the spread (standard deviation, quantiles) answers a different question.

## 2. t-based intervals

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(1)
x = rng.normal(50.0, 8.0, size=20)          # one summary value per independent replication

n = x.size
mean = x.mean()
sem = stats.sem(x)                          # s / sqrt(n), ddof=1
t_crit = stats.t.ppf(0.975, df=n - 1)
low, high = mean - t_crit * sem, mean + t_crit * sem
print(f"mean {mean:.2f}, 95% CI [{low:.2f}, {high:.2f}], half-width {t_crit * sem:.2f}, n={n}")

# Same interval from SciPy directly
low2, high2 = stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem)
print(np.allclose([low, high], [low2, high2]))

# Via the one-sample t-test result object
print(stats.ttest_1samp(x, popmean=0).confidence_interval(0.95))
```

- Use the t quantile with `n - 1` degrees of freedom, not 1.96, unless n is in the hundreds. At n = 10 the factor is 2.26, at n = 5 it is 2.78.
- `stats.sem` uses `ddof=1` by default. `np.std` defaults to `ddof=0`; pass `ddof=1` for a sample standard deviation.
- The input must be independent observations. Applying this formula to consecutive autocorrelated samples from one run gives intervals that are too narrow (see [simulation-output-analysis.md](simulation-output-analysis.md)).
- Skewed or heavy-tailed data need a larger n for the t interval to reach its nominal coverage. Check coverage by simulation if it matters (section 7).

## 3. scipy.stats.bootstrap

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(2)
x = rng.lognormal(mean=0.0, sigma=1.0, size=40)

res = stats.bootstrap(
    (x,),                       # data is a sequence of samples
    np.median,                  # statistic(sample, axis=-1) must accept axis
    confidence_level=0.95,
    n_resamples=9999,
    method="BCa",               # default; also "percentile" and "basic"
    rng=np.random.default_rng(0),
)
print(res.confidence_interval)  # ConfidenceInterval(low=..., high=...)
print("bootstrap SE:", res.standard_error)
print("median:", np.median(x))
```

- Signature in SciPy 1.18: `bootstrap(data, statistic, *, n_resamples=9999, batch=None, vectorized=None, paired=False, axis=0, confidence_level=0.95, alternative='two-sided', method='BCa', bootstrap_result=None, rng=None, random_state=None)`. Seed with `rng`; `random_state` is the older spelling.
- `data` must be a sequence of arrays, even for one sample: `(x,)`.
- The statistic is called with an `axis` keyword. NumPy reductions (`np.mean`, `np.median`, `np.std`) already accept it. A custom function must accept `axis` and reduce along it, or be called through `vectorized=False`, which is slower.
- 9999 resamples gives stable endpoints for a 95% interval; use more (about 50000) for 99% intervals or when the endpoints will be quoted to many digits.
- Always seed with a `Generator` so the interval is reproducible; record the seed.

## 4. Percentile versus BCa

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(4)
x = rng.exponential(scale=3.0, size=25)

for method in ("percentile", "basic", "BCa"):
    r = stats.bootstrap((x,), np.mean, method=method, n_resamples=9999,
                        rng=np.random.default_rng(1))
    ci = r.confidence_interval
    print(f"{method:10s} [{ci.low:.2f}, {ci.high:.2f}]")
t_ci = stats.t.interval(0.95, df=x.size - 1, loc=x.mean(), scale=stats.sem(x))
print(f"{'t':10s} [{t_ci[0]:.2f}, {t_ci[1]:.2f}]")
```

- Percentile: take the 2.5th and 97.5th percentiles of the resampled statistic. Simple, transformation-respecting, but biased for skewed statistics at small n.
- BCa (bias-corrected and accelerated): adjusts the percentiles using a bias term and a jackknife-based acceleration. Second-order accurate and the better default for means of skewed data, medians and ratios. It needs at least a few distinct values and fails or warns on degenerate samples.
- Basic (reverse percentile) is less used; avoid it for skewed statistics.
- Bootstrap intervals for the mean of small samples (n below about 15) tend to be too narrow, because the resampling distribution has less spread than the sampling distribution. Do not assume the bootstrap rescues a tiny sample.
- For means of roughly symmetric data the t interval and the bootstrap agree; the bootstrap earns its place for medians, quantiles, ratios, correlations, trimmed means and any custom metric.

## 5. Differences and paired data

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(6)
a = rng.gamma(3.0, 2.0, 30)
b = a * 0.9 + rng.normal(0, 1.0, 30)       # paired with a (same scenario index)

def mean_diff(x, y, axis=-1):
    return np.mean(x, axis=axis) - np.mean(y, axis=axis)

# Independent samples: resample each group separately
r_ind = stats.bootstrap((a, b), mean_diff, method="BCa", rng=np.random.default_rng(0))
print("independent:", r_ind.confidence_interval)

# Paired: paired=True resamples whole pairs together
r_pair = stats.bootstrap((a, b), mean_diff, paired=True, method="BCa",
                         rng=np.random.default_rng(0))
print("paired:     ", r_pair.confidence_interval)

# Equivalent and simpler for paired data: bootstrap the differences
r_d = stats.bootstrap((a - b,), np.mean, method="BCa", rng=np.random.default_rng(0))
print("differences:", r_d.confidence_interval)

# Ratio of means (relative improvement) - a statistic the t-test cannot give directly
def ratio(x, y, axis=-1):
    return np.mean(y, axis=axis) / np.mean(x, axis=axis)

print("ratio:", stats.bootstrap((a, b), ratio, paired=True, rng=np.random.default_rng(0)).confidence_interval)
```

- For independent groups `bootstrap` resamples within each sample. For paired data pass `paired=True`, or bootstrap the vector of differences.
- Report a relative effect (ratio, percent change) with an interval of the ratio, not the ratio of two separately computed intervals.
- The CI of the difference answers "how large is the effect"; compare it with a pre-chosen smallest effect of practical interest.

## 6. Proportions

```python
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

k, n = 7, 50
wilson = proportion_confint(k, n, alpha=0.05, method="wilson")
exact = proportion_confint(k, n, alpha=0.05, method="beta")       # Clopper-Pearson
print("Wilson:", [round(v, 3) for v in wilson])
print("Clopper-Pearson:", [round(v, 3) for v in exact])
print("scipy binomtest:", stats.binomtest(k, n).proportion_ci(0.95, method="wilson"))

# Zero events: "0 out of 50" still has an upper bound
print("0/50 upper bound (exact):", round(proportion_confint(0, 50, method="beta")[1], 3))
print("rule of three:", 3 / 50)
```

- Avoid the Wald interval `p +- 1.96*sqrt(p(1-p)/n)`: it has poor coverage near 0 and 1 and with small n. Use Wilson or Clopper-Pearson.
- `proportion_confint(count, nobs, alpha=0.05, method="normal")` has the Wald interval as default `method`; pass `method="wilson"` or `"beta"` explicitly.
- For rare-event rates in simulation (packet loss, bit error rate), the number of events, not the number of trials, controls precision; plan for at least tens of events.

## 7. When the bootstrap fails

- Too few observations (n below about 10) or too few distinct values: the resampling distribution is a poor model of the population.
- Extreme-value statistics (maximum, minimum, very high quantiles such as the 99.9th percentile): the bootstrap is inconsistent for them. Use extreme-value theory or many more replications.
- Heavy tails with infinite variance: the mean has no stable interval; consider a trimmed mean or a quantile.
- Dependent data: the ordinary bootstrap assumes independent observations. For a time series use block bootstraps (`arch.bootstrap.StationaryBootstrap`, third-party) or batch means; for clustered data resample whole clusters (runs, subjects), never the individual rows.
- Hierarchical data (replications within configurations): resample at the level of the independent unit.

A coverage check shows whether an interval method works for your data type:

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(123)
true_mean = 1.0                                   # mean of Exponential(scale=1)
hits_t = hits_b = 0
trials, n = 300, 15
for _ in range(trials):
    x = rng.exponential(1.0, n)
    lo, hi = stats.t.interval(0.95, n - 1, loc=x.mean(), scale=stats.sem(x))
    hits_t += lo <= true_mean <= hi
    r = stats.bootstrap((x,), np.mean, n_resamples=999, method="BCa", rng=rng)
    hits_b += r.confidence_interval.low <= true_mean <= r.confidence_interval.high
print(f"t coverage {hits_t / trials:.3f}, BCa coverage {hits_b / trials:.3f} (nominal 0.95)")
```

## 8. Reporting

- Write the point estimate, the interval with its level, the method and n: `mean latency 12.4 ms, 95% CI [11.8, 13.0] (t interval, n = 30 replications)`.
- `mean +- X` is ambiguous. If you use it, say whether X is the standard deviation, the standard error or the confidence half-width. Standard deviation describes the data; the standard error and the CI describe the estimate.
- State what n counts: independent replications, runs, subjects, not the total number of raw samples.
- Round to the precision the interval supports (two or three significant digits).
- When the interval of a difference contains zero, say that the data are compatible with no difference and with effects up to the interval's end; do not say there is no effect.
- In figures, label error bars ("95% CI of the mean over 30 replications").

## 9. R equivalents

Not executed here; verify in the R documentation.

```r
t.test(x)$conf.int                              # t interval for the mean
library(boot)                                   # recommended package shipped with R
b <- boot(x, statistic = function(d, i) median(d[i]), R = 9999)
boot.ci(b, type = c("perc", "bca"))
binom.test(7, 50)$conf.int                      # Clopper-Pearson
```
