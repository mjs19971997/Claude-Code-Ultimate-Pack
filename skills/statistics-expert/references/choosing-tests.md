# Choosing and Checking Hypothesis Tests

How to pick a test from the data layout, check its assumptions, run it with SciPy and read the result. Code blocks are self-contained and were run on SciPy 1.18.1, statsmodels 0.15.0 and NumPy 2.5.4 (2026-10). R equivalents are given as short snippets; they were not run in this environment, so check them against the R documentation.

## Contents

1. [Selection table](#1-selection-table)
2. [Two independent groups](#2-two-independent-groups)
3. [Paired or repeated measurements](#3-paired-or-repeated-measurements)
4. [Three or more groups](#4-three-or-more-groups)
5. [Counts and proportions](#5-counts-and-proportions)
6. [Checking assumptions](#6-checking-assumptions)
7. [Permutation tests](#7-permutation-tests)
8. [Reading a p-value](#8-reading-a-p-value)
9. [Bayesian alternative in brief](#9-bayesian-alternative-in-brief)
10. [R equivalents](#10-r-equivalents)

## 1. Selection table

| Question | Layout | Default test | Fallback when assumptions fail |
|---|---|---|---|
| Is the mean different from a constant? | one sample | `ttest_1samp` | `wilcoxon(x - c)`, or bootstrap CI of the mean |
| Do two systems differ in mean? | two independent samples | Welch `ttest_ind(equal_var=False)` | `mannwhitneyu`, `permutation_test` |
| Does a change help the same units? | paired (same seed, same scenario, same subject) | `ttest_rel` on the differences | `wilcoxon` on the differences |
| Do 3+ systems differ? | k independent samples | `f_oneway(equal_var=False)` (Welch ANOVA) | `kruskal` |
| Same units under 3+ conditions | repeated measures, blocked | repeated-measures ANOVA (statsmodels `AnovaRM`) | `friedmanchisquare` |
| Do two categorical variables relate? | contingency table of counts | `chi2_contingency` | `fisher_exact` for 2x2 with small counts |
| Is a proportion different? | counts | `binomtest` | exact intervals, not the normal approximation |
| Do two distributions differ in shape? | two samples | `ks_2samp` | `epps_singleton_2samp`, `anderson_ksamp` |

- Decide the test before looking at the results. The unit of analysis is the independent unit (a replication, a run, a subject), not each observation inside it.
- Two measurements on the same random seed or scenario are paired. Use the paired test, because it removes between-scenario variance.
- Equal-variance Student t is rarely needed: Welch loses almost no power when variances are equal and protects the error rate when they are not.

## 2. Two independent groups

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(42)
a = rng.lognormal(mean=1.0, sigma=0.5, size=30)   # e.g. latency, system A
b = rng.lognormal(mean=1.3, sigma=0.5, size=35)   # system B

# Welch t-test: equal_var=False. The SciPy default is equal_var=True (Student).
res = stats.ttest_ind(a, b, equal_var=False)
ci = res.confidence_interval(confidence_level=0.95)   # CI of mean(a) - mean(b)
print(f"Welch t={res.statistic:.2f} df={res.df:.1f} p={res.pvalue:.4f}")
print(f"mean(a)-mean(b) 95% CI [{ci.low:.2f}, {ci.high:.2f}]")

# Mann-Whitney U: tests whether P(X > Y) differs from 0.5 (stochastic dominance),
# not a difference in medians unless the two shapes are the same.
u = stats.mannwhitneyu(a, b, alternative="two-sided")
print(f"U={u.statistic:.1f} p={u.pvalue:.4f}")
```

- `ttest_ind` returns `statistic`, `pvalue`, `df` and a `confidence_interval()` method. The interval is for `mean(a) - mean(b)`.
- `alternative="less"` or `"greater"` gives a one-sided test; fix the direction in the protocol before the data are seen.
- `mannwhitneyu` returns the U statistic of the first sample. With ties or n above the exact-method limit it uses the normal approximation; `method="exact"` and `"asymptotic"` can be forced, and `method="auto"` picks. Check the docs for the size limit of the exact method.
- Mann-Whitney is not a test of medians. With different spreads or skews it can reject while the medians are equal. State the hypothesis as stochastic dominance and report the probability of superiority (see [multiple-comparisons-effect-sizes.md](multiple-comparisons-effect-sizes.md)).
- Heavy-tailed outputs (response time, queue length) often make the mean unstable. Consider the log scale, a trimmed mean (`ttest_ind(..., trim=0.1)`), or a bootstrap CI of the quantity that matters.

## 3. Paired or repeated measurements

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(7)
seed_effect = rng.normal(0, 3, size=25)              # shared per-seed noise
base = 10 + seed_effect + rng.normal(0, 0.5, 25)     # baseline on seed i
new = 9.4 + seed_effect + rng.normal(0, 0.5, 25)     # variant on the same seed i

paired = stats.ttest_rel(base, new)
d = base - new
print(f"paired t={paired.statistic:.2f} p={paired.pvalue:.2e}, mean diff={d.mean():.2f}")
print(paired.confidence_interval())

# Wrong here: treating the paired data as independent hides the effect.
print("unpaired p =", round(stats.ttest_ind(base, new, equal_var=False).pvalue, 3))

w = stats.wilcoxon(base, new)          # signed-rank on the differences
print(f"Wilcoxon W={w.statistic:.1f} p={w.pvalue:.2e}")
```

- `wilcoxon(x, y)` tests whether the differences are symmetric around zero. Zero differences are dropped by default (`zero_method="wilcox"`).
- The paired t-test assumes the differences, not the raw values, are roughly normal. Plot the differences.
- Pairing only helps when the shared factor is real: same random numbers, same input trace, same subject. Pairing unrelated rows adds noise.
- In simulations, pairing is created on purpose with common random numbers (see [experiment-design.md](simulation-output-analysis.md)).

## 4. Three or more groups

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(1)
g1 = rng.normal(10.0, 1.0, 20)
g2 = rng.normal(10.8, 2.0, 20)
g3 = rng.normal(11.5, 3.0, 20)

print(stats.f_oneway(g1, g2, g3, equal_var=False))    # Welch ANOVA
print(stats.kruskal(g1, g2, g3))
tk = stats.tukey_hsd(g1, g2, g3)                      # all pairs, familywise error controlled
print(tk)
dn = stats.dunnett(g2, g3, control=g1)                # each treatment against one control
print(dn.pvalue)
```

- The omnibus F or H test only says that some difference exists. Follow with a post hoc procedure that controls the familywise error: Tukey HSD (all pairs), Dunnett (against a control), or pairwise tests with Holm.
- `tukey_hsd(..., equal_var=False)` gives the Games-Howell variant in current SciPy; check the signature of your installed version.
- Kruskal-Wallis follows with Dunn's test (package `scikit-posthocs`, a third-party library; check that it is maintained) or pairwise Mann-Whitney with Holm adjustment.
- Factorial designs with several factors need a linear model, not many t-tests: see the ANOVA example in [experiment-design.md](simulation-output-analysis.md).

## 5. Counts and proportions

```python
import numpy as np
from scipy import stats

table = np.array([[30, 70],     # system A: pass, fail
                  [45, 55]])    # system B: pass, fail
chi2, p, dof, expected = stats.chi2_contingency(table)
print(f"chi2={chi2:.2f} dof={dof} p={p:.4f}")
print("min expected count:", expected.min())          # rule of thumb: >= 5 in every cell

print(stats.fisher_exact([[3, 9], [8, 2]]))           # small counts, exact

bt = stats.binomtest(k=18, n=200, p=0.05)             # observed 9% vs a 5% target
print(bt.pvalue, bt.proportion_ci(confidence_level=0.95, method="wilson"))
```

- `chi2_contingency` applies Yates correction by default for 2x2 tables (`correction=True`). Expected counts under independence must be large enough; otherwise use `fisher_exact`.
- A chi-square test compares counts of independent units. Do not feed it percentages, or repeated observations of the same unit.
- For a proportion, report an interval (Wilson or exact Clopper-Pearson), not `p +- sqrt(p(1-p)/n)`, which fails near 0 and 1.

## 6. Checking assumptions

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(3)
x = rng.exponential(2.0, 40)
y = rng.exponential(2.5, 40)

print("Shapiro x:", stats.shapiro(x))                  # small p: not normal
print("Levene (median-centred, Brown-Forsythe):", stats.levene(x, y, center="median"))
print("skew, excess kurtosis:", stats.skew(x), stats.kurtosis(x))

# QQ data without plotting: sorted sample vs theoretical normal quantiles
(osm, osr), (slope, intercept, r) = stats.probplot(x, dist="norm")
print("QQ correlation r =", round(r, 3))
```

- Test assumptions on the residuals or the differences, not on pooled raw data. Normality of the response within each group (or of paired differences) is what matters.
- A formal normality test is a weak guide: with n = 10 it has no power, with n = 5000 it rejects trivial departures. Use a QQ plot and the sample size. With n above about 30 per group the t-test on means is robust to moderate skew, but not to heavy tails or extreme outliers.
- Independence is a design property and cannot be tested after the fact. Consecutive outputs of one simulation run are autocorrelated; use replications or batch means.
- Do not use a preliminary Levene test to pick between Student and Welch. Use Welch always.
- If assumptions fail, options in order: transform (log), use a rank test with an honest hypothesis, use a permutation or bootstrap method, or model the data properly (for example a generalised linear model).

## 7. Permutation tests

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(11)
a = rng.gamma(2.0, 2.0, 25)
b = rng.gamma(2.0, 3.0, 25)

def diff_median(x, y, axis=-1):
    return np.median(x, axis=axis) - np.median(y, axis=axis)

res = stats.permutation_test(
    (a, b), diff_median, permutation_type="independent",
    n_resamples=9999, alternative="two-sided", rng=np.random.default_rng(0),
)
print(res.statistic, res.pvalue)

# Paired layout: permutation_type="samples" flips signs within pairs
x = rng.normal(0.0, 1.0, 20)
y = x + rng.normal(0.3, 0.5, 20)
res2 = stats.permutation_test(
    (x, y), lambda u, v, axis=-1: np.mean(u - v, axis=axis),
    permutation_type="samples", vectorized=True, rng=np.random.default_rng(0),
)
print(res2.pvalue)
```

- `permutation_test(data, statistic, *, permutation_type="independent", vectorized=None, n_resamples=9999, batch=None, alternative, axis, rng)` exists in SciPy 1.18. The seed argument is `rng`; `random_state` is the older spelling.
- A permutation test needs exchangeability under the null: it assumes the group labels carry no information, which includes equal spread when the statistic is a location difference.
- When the number of distinct permutations is below `n_resamples` SciPy enumerates all of them and the p-value is exact.
- Minimum possible p-value with a Monte Carlo test is about `1 / (n_resamples + 1)`; do not report `p = 0`.

## 8. Reading a p-value

- The p-value is the probability of data at least as extreme as observed if the null hypothesis and all modelling assumptions were true. It is not the probability that the null is true, not the probability of a replication, and not the size of an effect.
- A small p-value with a huge n can be a trivial effect; a large p-value with a small n means the study could not tell. Report the effect size and its interval first, the p-value second.
- "Not significant" is not "no difference". For equivalence claims use a TOST procedure (`statsmodels.stats.weightstats.ttost_ind`, `ttost_paired`) with a margin chosen before the data are seen.
- Choosing the test, the direction, the exclusions or the outcome after looking at the data inflates the false-positive rate. Record the analysis plan, and report the number of comparisons made (see [multiple-comparisons-effect-sizes.md](multiple-comparisons-effect-sizes.md)).
- Report exact p-values to two or three significant digits (`p = 0.032`), and `p < 0.001` for tiny values. Do not write `p = 0.000`.

## 9. Bayesian alternative in brief

- A Bayesian analysis gives a posterior distribution for the quantity of interest; a 95% credible interval is a statement about the parameter given the prior and the model. It needs a prior and a likelihood to be stated and checked.
- Practical routes: PyMC or Stan (through `cmdstanpy`) for full models, `bambi` for formula-style models, ArviZ for diagnostics. These are third-party packages; check the current versions and that sampling diagnostics (R-hat, effective sample size, divergences) are clean before using results.
- For two proportions a Beta-Binomial model needs only SciPy: the posterior of a proportion with a `Beta(1, 1)` prior after `k` successes in `n` trials is `Beta(1 + k, 1 + n - k)`.

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(5)
post_a = stats.beta(1 + 30, 1 + 70)       # 30/100 successes
post_b = stats.beta(1 + 45, 1 + 55)       # 45/100 successes
draws = post_b.rvs(100_000, random_state=rng) - post_a.rvs(100_000, random_state=rng)
print("P(B > A) =", round(float((draws > 0).mean()), 3))
print("95% credible interval of B - A:", np.percentile(draws, [2.5, 97.5]).round(3))
```

## 10. R equivalents

Not executed here; verify argument names in the R documentation of your installed version.

```r
t.test(a, b)                              # Welch by default (var.equal = FALSE)
t.test(base, new, paired = TRUE)
wilcox.test(a, b, conf.int = TRUE)        # Mann-Whitney; Wilcoxon signed-rank with paired = TRUE
oneway.test(y ~ g, data = d)              # Welch ANOVA
kruskal.test(y ~ g, data = d)
TukeyHSD(aov(y ~ g, data = d))
chisq.test(table)                         # fisher.test(table) for small counts
shapiro.test(x)                           # car::leveneTest(y ~ g) for equal-variance checks
```

R's `t.test` defaults to Welch, the reverse of SciPy's `ttest_ind` default.
