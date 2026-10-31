# Multiple Comparisons, Effect Sizes, Power and Sample Size

Controlling error rates when many tests are run, quantifying how large an effect is, and planning how much data to collect. Code blocks are self-contained and were run on SciPy 1.18.1, statsmodels 0.15.0 and NumPy 2.5.4 (2026-10).

## Contents

1. [Why adjust](#1-why-adjust)
2. [Bonferroni, Holm and Benjamini-Hochberg](#2-bonferroni-holm-and-benjamini-hochberg)
3. [Choosing a correction](#3-choosing-a-correction)
4. [Effect sizes for means](#4-effect-sizes-for-means)
5. [Effect sizes for ranks](#5-effect-sizes-for-ranks)
6. [Power and sample size](#6-power-and-sample-size)
7. [Precision-based planning](#7-precision-based-planning)
8. [Pitfalls](#8-pitfalls)
9. [R equivalents](#9-r-equivalents)

## 1. Why adjust

- With `m` independent tests at level 0.05 and all nulls true, the chance of at least one false positive is `1 - 0.95^m`: 40% for m = 10, 92% for m = 50.
- The family is every test whose result could support the same claim: all metrics, all scenarios, all pairwise system comparisons in the study. Count the comparisons that were examined, including ones that were not reported.
- Two error rates: the familywise error rate (FWER, probability of any false positive) and the false discovery rate (FDR, expected share of false positives among the rejections).

## 2. Bonferroni, Holm and Benjamini-Hochberg

```python
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

p = np.array([0.001, 0.008, 0.012, 0.030, 0.041, 0.20, 0.45, 0.80])

for method in ("bonferroni", "holm", "fdr_bh"):
    reject, p_adj, _, _ = multipletests(p, alpha=0.05, method=method)
    print(f"{method:10s} adj={np.round(p_adj, 3)} reject={reject.sum()}")

# SciPy has FDR adjustment only (Benjamini-Hochberg 'bh' and Benjamini-Yekutieli 'by')
print(np.round(stats.false_discovery_control(p, method="bh"), 3))
print(np.round(stats.false_discovery_control(p, method="by"), 3))
```

- `statsmodels.stats.multitest.multipletests(pvals, alpha=0.05, method='hs', maxiter=1, is_sorted=False, returnsorted=False)` returns `(reject, pvals_corrected, alphacSidak, alphacBonf)`. The default `method='hs'` is Holm-Sidak; always pass the method explicitly. Other names include `'bonferroni'`, `'sidak'`, `'holm'`, `'holm-sidak'`, `'simes-hochberg'`, `'hommel'`, `'fdr_bh'`, `'fdr_by'` and `'fdr_tsbh'`; check the docstring of the installed version.
- `scipy.stats.false_discovery_control(ps, *, axis=0, method='bh')` returns BH-adjusted p-values (q-values) for `method='bh'`, and Benjamini-Yekutieli for `'by'`. It has no FWER methods.
- Adjusted p-values are compared directly with alpha. Report both raw and adjusted p-values, and name the method.
- Bonferroni: multiply each p by `m` (cap at 1). Controls FWER, any dependence, conservative.
- Holm: step-down version of Bonferroni, uniformly at least as powerful, same guarantee. Use it instead of Bonferroni.
- Benjamini-Hochberg: controls FDR under independence or positive dependence. Benjamini-Yekutieli controls it under any dependence but is more conservative.

## 3. Choosing a correction

| Situation | Procedure |
|---|---|
| A few confirmatory hypotheses, any false positive is costly | Holm (FWER) |
| All pairwise comparisons of k means | Tukey HSD (`stats.tukey_hsd`), or Games-Howell for unequal variances |
| Several treatments against one control | Dunnett (`stats.dunnett`) |
| Screening many metrics or parameters, a few false leads are tolerable | Benjamini-Hochberg (FDR) |
| Hypotheses with a fixed order of importance | Fixed-sequence (hierarchical) testing: test in order, stop at the first failure, no adjustment needed |
| One primary metric and several secondary ones | Pre-register the primary; adjust or label the rest as exploratory |

- Adjust across the whole family, not within each figure or table.
- If a full multiple-testing correction is impossible, say that results are exploratory and report effect sizes with intervals.
- A pairwise matrix of k systems has `k(k-1)/2` comparisons: 45 for k = 10.

## 4. Effect sizes for means

```python
import numpy as np
from scipy import stats

def cohens_d(x, y):
    """Standardised mean difference with the pooled standard deviation."""
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    return (np.mean(x) - np.mean(y)) / sp

def hedges_g(x, y):
    """Small-sample corrected d."""
    df = len(x) + len(y) - 2
    j = 1 - 3 / (4 * df - 1)
    return j * cohens_d(x, y)

def d_paired(before, after):
    """Standardised difference of paired data (d_z): mean(diff) / sd(diff)."""
    d = np.asarray(before) - np.asarray(after)
    return d.mean() / d.std(ddof=1)

rng = np.random.default_rng(8)
a = rng.normal(100, 15, 25)
b = rng.normal(108, 15, 25)

print(f"d={cohens_d(a, b):.2f} g={hedges_g(a, b):.2f}")

res = stats.bootstrap((a, b), lambda x, y, axis=-1: (np.mean(x, axis=axis) - np.mean(y, axis=axis)),
                      rng=np.random.default_rng(0))
print("raw difference CI:", res.confidence_interval)

# CI for g by bootstrap (statistic over two samples, 1-D inputs, vectorized=False)
rg = stats.bootstrap((a, b), hedges_g, vectorized=False, rng=np.random.default_rng(0),
                     n_resamples=2000, method="percentile")
print("g CI:", rg.confidence_interval)
```

- SciPy has no Cohen's d function; write it (3 lines) or use a maintained package such as `pingouin` (third-party; verify its current version).
- Prefer the raw difference in the original units with its interval, and add a standardised effect only when units are arbitrary or studies must be compared. A standardised value depends on the spread of the sample.
- Benchmarks of 0.2, 0.5 and 0.8 for small, medium and large are conventions from the behavioural sciences, not engineering thresholds. Judge the effect against what matters in the application.
- With unequal variances or unequal group sizes, the pooled `d` can mislead; use the control group's standard deviation (Glass's delta) and say so.
- Paired designs: `d_z` uses the SD of differences and is not comparable with the pooled `d` of independent groups.

## 5. Effect sizes for ranks

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(9)
x = rng.gamma(2.0, 2.0, 40)
y = rng.gamma(2.0, 2.6, 45)

u1 = stats.mannwhitneyu(x, y, alternative="two-sided").statistic   # U for the first sample
n1, n2 = len(x), len(y)
prob_superiority = u1 / (n1 * n2)          # P(X > Y) + 0.5 P(X = Y)
cliffs_delta = 2 * prob_superiority - 1    # equals the rank-biserial correlation for two groups
print(f"P(X>Y)={prob_superiority:.3f}, Cliff's delta={cliffs_delta:.3f}")

# Check against the direct definition
direct = (np.sum(x[:, None] > y[None, :]) - np.sum(x[:, None] < y[None, :])) / (n1 * n2)
print(np.isclose(cliffs_delta, direct))

# Paired data: matched-pairs rank-biserial from Wilcoxon signed-rank sums
a = rng.normal(10, 2, 30)
b = a + rng.normal(0.5, 1, 30)
d = b - a
d = d[d != 0]
ranks = stats.rankdata(np.abs(d))
r_pairs = (ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum()
print("matched-pairs rank-biserial:", round(float(r_pairs), 3))
```

- Probability of superiority is the most readable effect size for ordinal or skewed outcomes: "a random run of system A beats a random run of system B in 63% of pairings".
- `U1 / (n1 n2)` needs the U statistic of the first sample, which `mannwhitneyu(x, y)` returns for `x`. The direct-definition check above confirms the direction; keep it in tests when the sign matters.
- Cliff's delta ranges from -1 to 1; 0 means stochastic equality. It is the same number as the rank-biserial correlation for two independent groups.
- Bootstrap an interval for any of these with `stats.bootstrap` as in [confidence-intervals-bootstrap.md](confidence-intervals-bootstrap.md).

## 6. Power and sample size

```python
from statsmodels.stats.power import TTestIndPower, TTestPower, NormalIndPower, FTestAnovaPower

# Sample size per group to detect d = 0.5 with 80% power, two-sided alpha 0.05
n = TTestIndPower().solve_power(effect_size=0.5, alpha=0.05, power=0.80, alternative="two-sided")
print(f"independent t-test: n per group = {n:.1f}")

# Power achieved with n = 30 per group
print("power:", round(TTestIndPower().solve_power(effect_size=0.5, nobs1=30, alpha=0.05), 3))

# Smallest detectable effect at n = 30, power 0.8
print("MDE:", round(TTestIndPower().solve_power(nobs1=30, alpha=0.05, power=0.8), 3))

# Paired design: effect_size is d_z
print("paired n:", round(TTestPower().solve_power(effect_size=0.5, alpha=0.05, power=0.80), 1))

# Two proportions via Cohen's h
from statsmodels.stats.proportion import proportion_effectsize
h = proportion_effectsize(0.30, 0.45)
print("two proportions n per group:", round(NormalIndPower().solve_power(abs(h), alpha=0.05, power=0.8), 1))

# One-way ANOVA with 4 groups: effect_size is Cohen's f, nobs is the TOTAL sample size
print("ANOVA total n:", round(FTestAnovaPower().solve_power(effect_size=0.25, alpha=0.05, power=0.8, k_groups=4), 1))
```

- Exactly one of `effect_size`, `nobs1`, `alpha`, `power` is left out (set to `None`) and `solve_power` returns it. Round sample sizes up.
- `TTestIndPower.solve_power(effect_size=None, nobs1=None, alpha=None, power=None, ratio=1.0, alternative='two-sided')`: `ratio` is `nobs2 / nobs1`.
- Power classes in `statsmodels.stats.power`: `TTestPower` (one-sample or paired), `TTestIndPower`, `NormalIndPower`, `FTestAnovaPower`, `FTestPower`, `GofChisquarePower`.
- Choose the effect size from the smallest difference that matters in the application or from a pilot, not from a published large effect. Using an estimate from a small pilot is optimistic; use the lower end of its interval.
- Power classes assume the t-test. For roughly normal data the Mann-Whitney test needs about 5 percent more observations than the t-test (asymptotic relative efficiency 3/pi, about 0.955); with heavy tails it can need fewer. Simulate when the data are far from normal.
- Simulation-based power: generate data from the assumed model, run the planned test 2000 times, count rejections. It works for any test, adjustment or design.

```python
import numpy as np
from scipy import stats

def simulated_power(n, shift, sd=1.0, trials=2000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    rej = 0
    for _ in range(trials):
        a = rng.lognormal(0.0, sd, n)
        b = rng.lognormal(shift, sd, n)
        rej += stats.mannwhitneyu(a, b).pvalue < alpha
    return rej / trials

print("Mann-Whitney power, lognormal, n=30:", simulated_power(30, shift=0.6))
```

## 7. Precision-based planning

- When there is no hypothesis to test, plan for the CI half-width. For a mean: `n = (t * s / h)^2`, solved iteratively because `t` depends on `n`. For a proportion: `n = z^2 p(1-p) / h^2`, with `p = 0.5` as the worst case.
- A pilot of 10 to 20 replications gives `s`. Add a safety margin because `s` is itself noisy.
- The same logic drives the number of simulation replications; the sequential procedure is in [simulation-output-analysis.md](simulation-output-analysis.md).

## 8. Pitfalls

- Post hoc ("observed") power computed from the observed effect is a transformation of the p-value and adds nothing. Plan power before the study.
- Running a study until p < 0.05, then stopping (optional stopping) inflates the false-positive rate. Fix n in advance, or use a proper sequential design.
- Dropping non-significant arms, metrics or scenarios from the report makes the reported p-values meaningless. Report all comparisons made.
- Adjusting only the "interesting" subset of tests does not control the error rate.
- Significance in a subgroup and non-significance in another is not evidence that the subgroups differ; test the interaction.
- Adjusted p-values with FDR methods do not support the claim that each individual discovery is real; they bound the proportion of false ones.

## 9. R equivalents

Not executed here; verify in the R documentation.

```r
p.adjust(p, method = "holm")             # also "bonferroni", "BH", "BY", "hommel"
pairwise.t.test(y, g, p.adjust.method = "holm", pool.sd = FALSE)
power.t.test(delta = 5, sd = 10, power = 0.8)          # n per group
power.prop.test(p1 = 0.30, p2 = 0.45, power = 0.8)
```
