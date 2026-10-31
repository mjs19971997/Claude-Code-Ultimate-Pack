---
name: statistics-expert
description: >-
  Applies statistics to engineering and simulation experiments: choosing tests (Welch t, paired, Mann-Whitney, Wilcoxon, chi-square, ANOVA, Kruskal-Wallis), confidence intervals and bootstrap, effect sizes, multiple-comparison corrections, power, factorial designs and simulation output analysis with SciPy and statsmodels. Use when writing scipy.stats or statsmodels code, deciding which test fits, sizing replications, removing warm-up or reporting mean with CI. Not for data cleaning (use data-analysis-expert), ML evaluation (use ml-engineering-expert), plot styling (use scientific-python-expert) or paper prose (use scientific-writing-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Statistics Expert

This skill covers applied statistics for engineering and simulation research: selecting a hypothesis test from the data layout, checking assumptions, interpreting p-values, building confidence intervals (t-based and bootstrap), reporting effect sizes, controlling error rates across many comparisons, planning power and sample size, designing experiments, and analysing simulation output. Implementation is in Python with SciPy and statsmodels, with short R equivalents. Data wrangling, machine-learning evaluation, plot styling and manuscript writing belong to other skills.

> Verified against SciPy 1.18.1 (PyPI, 2026-08-21; requires Python 3.12 or later and NumPy 2.0 or later), statsmodels 0.15.0 (PyPI, 2026-08-27) and NumPy 2.5.4; all Python examples were run against those versions (2026-10). R snippets were not executed.

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

- Covered: one-, two- and k-sample tests for means, ranks, counts and proportions; assumption checks; permutation tests; t, bootstrap percentile and BCa intervals; Cohen's d, Hedges' g, rank-biserial correlation and Cliff's delta; Bonferroni, Holm, Benjamini-Hochberg and Tukey/Dunnett procedures; power and sample size; factorial designs, blocking, randomisation and common random numbers; independent replications, warm-up removal, batch means and autocorrelation of simulation output; regression basics and pitfalls; a brief Bayesian alternative; reporting conventions.
- Not covered: loading, cleaning, joining and reshaping data (data-analysis-expert); train and test splits, cross-validation and model metrics for machine learning (ml-engineering-expert); figure design and matplotlib styling (scientific-python-expert); writing the results section or captions (scientific-writing-expert); how a given simulator seeds its generators (ns3-expert); LaTeX tables (latex-academic-expert).
- Time-series forecasting, survival analysis, mixed-effects and Bayesian hierarchical models are outside the depth of this skill; name the right method and check its documentation instead of improvising.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| SciPy 1.18 tests | `ttest_ind(a, b, equal_var=False, ...)` is Welch; the default `equal_var=True` is Student. `ttest_rel`, `ttest_1samp`, `mannwhitneyu`, `wilcoxon`, `kruskal`, `f_oneway(..., equal_var=False)`, `friedmanchisquare`, `chi2_contingency`, `fisher_exact`, `binomtest`, `shapiro`, `levene`, `ks_2samp`. Result objects expose `statistic` and `pvalue`; `ttest_*` results add `df` and `confidence_interval()` |
| Resampling | `stats.bootstrap(data, statistic, *, n_resamples=9999, paired=False, method='BCa', confidence_level=0.95, rng=...)` with `data` a tuple of samples and the statistic accepting `axis`. `stats.permutation_test(data, statistic, *, permutation_type='independent', n_resamples=9999, rng=...)`. The seed keyword is `rng`; `random_state` is the older spelling |
| Multiple comparisons | `statsmodels.stats.multitest.multipletests(pvals, alpha, method=...)` with `'bonferroni'`, `'holm'`, `'fdr_bh'`, `'fdr_by'` (default `'hs'` is Holm-Sidak, so name the method). `stats.false_discovery_control(ps, method='bh' or 'by')` gives FDR only. Post hoc: `stats.tukey_hsd` (`equal_var=False` gives Games-Howell), `stats.dunnett` |
| Power | `statsmodels.stats.power`: `TTestIndPower`, `TTestPower`, `NormalIndPower`, `FTestAnovaPower`, `GofChisquarePower`; `solve_power` returns whichever of `effect_size`, `nobs1`, `alpha`, `power` is `None` |
| Effect sizes | SciPy has no Cohen's d. Compute it, or use a maintained third-party package. Rank-biserial and Cliff's delta follow from the Mann-Whitney U: `2 * U1 / (n1 * n2) - 1` |
| Design tools | `scipy.stats.qmc` (`LatinHypercube`, `Sobol`, `scale`); `np.random.SeedSequence.spawn` for independent streams; `statsmodels.formula.api.ols` with `anova_lm` for factorial analysis |
| Simulation output | Replication means form the i.i.d. sample; steady state needs warm-up deletion; one long run needs batch means; `statsmodels.tsa.stattools.acf` diagnoses dependence |
| Intervals for proportions | `statsmodels.stats.proportion.proportion_confint(count, nobs, method='wilson' or 'beta')`; the default method is the Wald `'normal'`. `stats.binomtest(...).proportion_ci(method='wilson')` |
| R equivalents | `t.test` (Welch by default), `wilcox.test`, `oneway.test`, `kruskal.test`, `TukeyHSD`, `p.adjust`, `power.t.test`, the `boot` package for `boot.ci(type = c("perc", "bca"))` |

## 3. Workflow

1. State the question, the outcome variable, the unit of analysis and the comparison (two systems, k systems, a factor effect, a target bound). Decide whether the output is steady-state or terminating if it comes from a simulation.
2. Fix the plan before looking at results: the primary metric, the test or interval, the direction (one- or two-sided), the smallest effect of interest, alpha, and the family of comparisons.
3. Size the study: sample size from power for a test, or from a target CI half-width for an estimate (section 14, and [references/multiple-comparisons-effect-sizes.md](references/multiple-comparisons-effect-sizes.md)).
4. Collect independent observations: replications with independent random streams, paired where the design shares seeds or blocks. Record seeds.
5. Look at the data first: a plot of the distribution (histogram or ECDF), the paired differences, outliers, and for simulations the time series and its autocorrelation.
6. Pick the test from the layout ([references/choosing-tests.md](references/choosing-tests.md)), check assumptions on residuals or differences, and compute an effect size with an interval, then the p-value.
7. Adjust for multiplicity across the whole family, and report all comparisons made.
8. Report n, the estimate, the interval with its level and method, the effect size, the test and the exact p-value, and any deviations from the plan.

## 4. Decision Rules

- If two independent groups of continuous data: use Welch `ttest_ind(equal_var=False)`; if the outcome is clearly heavy-tailed or ordinal, use Mann-Whitney and state the hypothesis as stochastic dominance, or a permutation or bootstrap test of the statistic that matters.
- If the two measurements share a seed, scenario or subject: use the paired test (`ttest_rel`, `wilcoxon`) on the differences. Treating paired data as independent loses power.
- If three or more groups: Welch ANOVA (`f_oneway(equal_var=False)`) or Kruskal-Wallis, then Tukey, Games-Howell or Dunnett for pairs; or a linear model when there are several factors.
- If counts of independent units in categories: `chi2_contingency` when all expected counts are at least about 5, else `fisher_exact` for 2x2.
- If a proportion or rate: report a Wilson or exact interval, not Wald.
- If the statistic is a median, quantile, ratio, correlation or custom metric: `stats.bootstrap` with `method="BCa"`; for the mean of near-normal data the t interval is enough.
- If outputs come from one simulation run: do not use `s / sqrt(n)` on raw samples. Use independent replications or batch means ([references/simulation-output-analysis.md](references/simulation-output-analysis.md)).
- If systems are compared in a simulator: use common random numbers and the paired analysis ([references/experiment-design.md](references/experiment-design.md)).
- If more than one hypothesis supports a claim: control the family. Holm for confirmatory FWER, Benjamini-Hochberg for screening, Tukey or Dunnett for planned multi-group comparisons.
- If the result is "not significant": report the interval and, for a claim of equivalence, run TOST with a margin fixed in advance. Do not write "no difference".
- If assumptions fail: transform (often log), choose the rank or resampling alternative, or model properly; do not drop to a weaker test only because it is convenient.
- If n is below about 10 per group: say that the power is low, prefer exact or permutation methods, and avoid the bootstrap for the mean.
- If a prior and a quantity of direct interest exist, a Bayesian analysis is a legitimate alternative (section 9 of [references/choosing-tests.md](references/choosing-tests.md)); check sampler diagnostics before reporting.

## 5. Coding Standards

- Pass NumPy arrays (or pandas columns converted with `.to_numpy()`) to SciPy, and drop or handle `NaN` explicitly. The `nan_policy` argument defaults to `'propagate'`, which returns `nan` silently.
- Seed every random process with `np.random.default_rng(seed)` or a `SeedSequence`, pass the generator to SciPy through `rng=` (current spelling), and store the seed beside the results. Never use the global `np.random.seed`.
- Name the method in code and in output: `equal_var=False`, `method="holm"`, `method="BCa"`. Do not rely on defaults that differ between tools (SciPy `ttest_ind` is Student by default, R `t.test` is Welch).
- Use `ddof=1` for sample standard deviation and variance (`np.std` defaults to `ddof=0`).
- Keep a function per analysis step (summarise, test, effect size, report) that returns plain values or a small dataclass; do not print inside them.
- Format numbers once, in one reporting function: mean and interval to the precision the interval supports, p-values to two or three significant digits, `p < 0.001` for tiny values.
- Type-hint arrays as `numpy.typing.NDArray[np.float64]` and validate sizes (equal lengths for paired data, at least 2 observations per group) at the function boundary.
- Use `from scipy import stats` and `import statsmodels.api as sm`, `import statsmodels.formula.api as smf`; avoid `from scipy.stats import *`.
- Treat warnings from SciPy as findings (ties in Wilcoxon, constant input, degenerate bootstrap), not noise.

## 6. Project Structure

```text
experiment/
|-- pyproject.toml
|-- plan.md                  # hypotheses, metric, test, alpha, n, family, seed policy (written before the run)
|-- src/exp/
|   |-- design.py            # factor levels, replication count, seed streams
|   |-- run.py               # runs the simulator or model, writes one row per run
|   |-- analysis.py          # summaries, tests, intervals, effect sizes
|   `-- report.py            # formatting of results
|-- data/raw/                # immutable run outputs with seeds and parameters
|-- data/derived/            # per-replication summaries
|-- results/                 # tables and figures generated by code
`-- tests/                   # known-answer and coverage tests
```

- Keep raw per-run output immutable; derive summaries by code so the analysis can be rerun.
- One row per independent run, with columns for every factor, the seed or run number, and each metric.
- The plan file is committed before the data are generated; later changes are listed as deviations.

## 7. Design Patterns

- **Replication table**: a long table `(config, replication, seed, metric...)`; all analysis is a group-by over `config` of the per-replication summary. Cost: the summarisation per run must be done before analysis.
- **Pre-registered family**: a list of planned comparisons held in code (`COMPARISONS = [("A", "B"), ...]`), looped over once, adjusted once with `multipletests`. Cost: new comparisons require a new, labelled exploratory family.
- **Estimate with interval object**: return `(estimate, low, high, n, method)` from every estimator so reports cannot drop the interval or the method.
- **Paired-by-seed layout**: store the seed column and merge systems on it before taking differences; the merge failing is a useful check that pairing is real.
- **Sequential replications**: run in batches until the half-width target is met, with a minimum of 10 and a maximum cap, and record the stopping rule.
- **Simulation-based check**: when a method's behaviour is in doubt (coverage, power, Type I error), simulate the data-generating process and measure; the pattern is in [references/confidence-intervals-bootstrap.md](references/confidence-intervals-bootstrap.md).

## 8. Best Practices

- Plot before testing: an ECDF or histogram per group, the paired differences, and a QQ plot of residuals.
- Prefer estimation to dichotomy: interval of the difference in original units, then the effect size, then the p-value.
- Choose the smallest effect of practical interest from the application (a latency budget, a throughput margin), and relate intervals to it.
- Report the number of independent units, the number of replications, run length and warm-up, and the random-number policy. `mean +- std` without a label is ambiguous; write `mean (95% CI)` or state what the +- value is.
- Use paired designs and blocking to remove known nuisance variance before collecting more data.
- Keep raw outputs and analysis code under version control; regenerate tables from code.
- Distinguish confirmatory analyses (planned, adjusted) from exploratory ones (labelled, effect sizes only).
- Report negative and null results with their intervals.
- Check the whole pipeline on simulated data with a known effect (and with no effect) before using it on real output.

## 9. Performance

- Vectorise across replications: SciPy tests accept `axis` for batched inputs, and `bootstrap` and `permutation_test` evaluate a vectorised statistic in batches; pass a statistic that accepts `axis` and works on stacked arrays.
- The cost of a bootstrap is `n_resamples x cost(statistic)`. If the statistic is expensive, lower `n_resamples` (about 2000 is adequate for exploration, 9999 or more for reported intervals) or use the `batch` argument to limit memory.
- Python loops dominate hand-written simulations; vectorise draws up front (`rng.exponential(size=n)`), keep only the sequential recursion in the loop, and move it to Numba or a compiled simulator if replications run into the thousands (see scientific-python-expert).
- Parallelise replications across processes with one spawned `SeedSequence` child per replication; do not share a generator between processes.
- Simulation-based power with 2000 trials of a bootstrap is expensive; use the permutation or t-test version for sizing and the full version for confirmation.

## 10. Security

- Do not `pickle.load`, `eval` or `numpy.load(..., allow_pickle=True)` result files from untrusted sources; store run outputs as CSV, Parquet or `.npy` without pickled objects.
- Treat parameters read from configuration or command lines as input: validate ranges (alpha in (0, 1), n positive, confidence level in (0, 1)) before computing.
- Do not commit data that contains personal or confidential information; aggregate or anonymise before sharing, and remember that small groups in a published table can identify individuals.
- Record software versions (Python, NumPy, SciPy, statsmodels) with the results; pin them in the lockfile so the analysis can be reproduced.
- When running simulators or analysis as a service, never build shell commands from user-supplied parameters (use argument lists, no `shell=True`).

## 11. Testing

- Known-answer tests: compare against textbook or reference values with `pytest.approx` (a t-interval for a fixed sample, `multipletests` on a published p-value vector, M/M/1 mean wait `rho / (mu - lam)` against a long simulation).
- Property tests: the paired test on identical samples gives p = 1; shuffling group labels leaves the Type I error near alpha; scaling data by a constant leaves the p-value and Cohen's d unchanged.
- Type I error check: simulate under the null 2000 times, run the whole analysis, and confirm the rejection rate is about alpha (for example 0.04 to 0.06). Repeat with the skew and sample size of the real data.
- Coverage check: simulate data with a known parameter and count how often the interval contains it; compare with the nominal level.
- Fix the seed in tests so failures are reproducible, and use tolerances wide enough for Monte Carlo error (a standard error of about 0.005 for 2000 trials at alpha 0.05).
- Test edge cases: constant input, ties, a group with one observation, `NaN`, unequal lengths for paired input.

## 12. Review Checklist

- [ ] The unit of analysis is an independent unit (replication, run, subject), and n counts those.
- [ ] Paired data use paired methods; independent data do not.
- [ ] The test, alternative and alpha were fixed before the results; the family of comparisons is stated.
- [ ] Welch or a justified alternative is used; `equal_var=False` appears where intended.
- [ ] Assumptions were checked on residuals or differences, with a plot.
- [ ] Multiple comparisons are adjusted with a named method, and raw and adjusted p-values are given.
- [ ] Every estimate has an interval with its level and method; effect sizes accompany p-values.
- [ ] `mean +- X` is labelled, or replaced by `mean (95% CI)` with n.
- [ ] Simulation output: warm-up handled, no autocorrelated samples treated as independent, seeds recorded.
- [ ] Sample size or replication count is justified by power or a target half-width.
- [ ] "Not significant" is not read as "no effect"; equivalence claims use a pre-set margin.
- [ ] Random seeds, software versions and the analysis script are stored with the results.

## 13. Production Notes

- Reproducibility: store the root seed, the spawned child seed per run, parameters and package versions in the result file; rerunning with the same inputs should give the same numbers.
- SciPy 1.18 requires Python 3.12 or later and NumPy 2.0 or later; statsmodels 0.15.0 lists Python 3.10 or later. Check the compatibility of both on the target interpreter before pinning.
- Seed keyword: current SciPy functions accept `rng`; `random_state` remains accepted as an older spelling. Prefer `rng` and run tests with `-W error::DeprecationWarning` to catch removals early.
- Result objects and defaults change between releases (new `method` arguments, new return fields). Read the release notes when upgrading and re-run the known-answer tests.
- For regulated or high-stakes decisions, have the analysis plan reviewed, keep the code and data archived, and report deviations.
- A dashboard of simulation metrics should show intervals and n, not only means.
- Long-running campaigns: write each run's row on completion, make the runner restartable by skipping existing seeds, and analyse only complete cells.

## 14. Examples

Compare two simulated systems with paired seeds, a Welch alternative, CI and effect size:

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(2026)
shared = rng.normal(0, 2.0, 30)                          # per-seed difficulty shared by both systems
base = 20 + shared + rng.normal(0, 1.0, 30)              # metric per replication, system A
new = 19 + shared + rng.normal(0, 1.0, 30)               # same seeds, system B

d = base - new
res = stats.ttest_rel(base, new)
ci = res.confidence_interval(0.95)
d_z = d.mean() / d.std(ddof=1)
print(f"A-B mean difference {d.mean():.2f}, 95% CI [{ci.low:.2f}, {ci.high:.2f}], n={d.size} paired replications")
print(f"paired t({res.df}) = {res.statistic:.2f}, p = {res.pvalue:.2g}, d_z = {d_z:.2f}")
print(f"wilcoxon p = {stats.wilcoxon(base, new).pvalue:.2g}")
```

Replications needed for a target half-width, and BCa interval for a median:

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(1)
pilot = rng.normal(50, 6, 12)                            # pilot replication means
s, target = pilot.std(ddof=1), 1.0                       # want a 95% CI half-width of 1.0
n = 2
while stats.t.ppf(0.975, n - 1) * s / np.sqrt(n) > target:
    n += 1
print("replications needed:", n)

latency = rng.lognormal(3.0, 0.6, 60)
ci = stats.bootstrap((latency,), np.median, method="BCa", rng=np.random.default_rng(0)).confidence_interval
print(f"median {np.median(latency):.1f}, 95% BCa CI [{ci.low:.1f}, {ci.high:.1f}], n={latency.size}")
```

Adjusting a family of p-values and reporting both columns:

```python
import numpy as np
from statsmodels.stats.multitest import multipletests

names = ["throughput", "latency", "jitter", "loss", "energy"]
p = np.array([0.004, 0.018, 0.031, 0.20, 0.64])
reject, p_adj, _, _ = multipletests(p, alpha=0.05, method="holm")
for n_, a, b, r in zip(names, p, p_adj, reject):
    print(f"{n_:11s} raw {a:.3f}  Holm {b:.3f}  {'reject' if r else 'keep'}")
```

Sample size for a planned two-group comparison:

```python
from statsmodels.stats.power import TTestIndPower
import math

n = TTestIndPower().solve_power(effect_size=0.8, alpha=0.05, power=0.9)
print("n per group:", math.ceil(n))
```

## 15. Common Mistakes

- **Treating raw samples from one run as independent**: the interval is far too narrow. Use replication means or batch means.
- **Unpaired test on paired data, or the reverse**: pairing is a property of the design (shared seed, subject, block), not a choice made after seeing p.
- **Using Student's t by default**: SciPy `ttest_ind` defaults to `equal_var=True`. Pass `equal_var=False`.
- **Reading Mann-Whitney as a test of medians**: it tests stochastic dominance; with different shapes the medians can be equal while the test rejects.
- **Choosing the test by a preliminary normality or variance test**: it distorts error rates. Decide from the design, use Welch, and look at plots.
- **p-value as probability the hypothesis is true**, as effect size, or as the chance of replication.
- **"Not significant" read as "no effect"**: report the interval; use TOST for equivalence.
- **No adjustment across many metrics, scenarios or pairs**: the false-positive rate climbs quickly. Define the family and adjust.
- **`multipletests` with the default method**: it is Holm-Sidak (`'hs'`). Name the method.
- **Overlapping CIs read as no difference**: compute the CI of the difference.
- **`mean +- std` with n missing**: state n, and say whether the +- value is the SD, SE or CI half-width.
- **Wald interval for proportions near 0 or 1**: use Wilson or Clopper-Pearson. `proportion_confint` defaults to the Wald `'normal'`.
- **Ignoring warm-up**: the transient biases steady-state means. Delete it using pilot runs.
- **Bootstrap for tiny samples, maxima or dependent data**: it underestimates spread or is inconsistent. See [references/confidence-intervals-bootstrap.md](references/confidence-intervals-bootstrap.md).
- **Post hoc power from the observed effect**: it restates the p-value. Plan power in advance.
- **Optional stopping**: stopping data collection when p dips below 0.05 inflates false positives. Fix n or use a sequential design.
- **Cohen's 0.2/0.5/0.8 as engineering thresholds**: they are conventions from other fields; compare the raw effect with what matters to the application.
- **Passing a pandas Series with missing values to SciPy**: `nan_policy='propagate'` returns `nan`. Handle missing data explicitly.
- **Using `np.std` for a sample SD**: pass `ddof=1`.

## 16. References

- [references/choosing-tests.md](references/choosing-tests.md): selection table, Welch, paired, rank tests, ANOVA and post hoc, chi-square and Fisher, assumption checks, permutation tests, reading p-values, Bayesian alternative, R equivalents.
- [references/confidence-intervals-bootstrap.md](references/confidence-intervals-bootstrap.md): t intervals, `scipy.stats.bootstrap` with percentile, basic and BCa methods, paired and ratio statistics, proportion intervals, failure cases, coverage check, reporting.
- [references/multiple-comparisons-effect-sizes.md](references/multiple-comparisons-effect-sizes.md): Bonferroni, Holm, Benjamini-Hochberg, choosing a correction, Cohen's d, Hedges' g, Cliff's delta, power and sample size, simulation-based power, pitfalls.
- [references/simulation-output-analysis.md](references/simulation-output-analysis.md): independent replications, seed streams, warm-up (Welch, MSER-5), batch means, autocorrelation, replications for a target half-width.
- [references/experiment-design.md](references/experiment-design.md): common random numbers, factorial designs and ANOVA, Latin hypercube and Sobol designs, blocking and randomisation, regression pitfalls.
- SciPy statistics reference: https://docs.scipy.org/doc/scipy/reference/stats.html and release notes https://docs.scipy.org/doc/scipy/release.html
- statsmodels documentation: https://www.statsmodels.org/stable/ (stats.multitest, stats.power, stats.proportion, stats.anova, tsa.stattools)
- R help pages for `t.test`, `wilcox.test`, `p.adjust` and `power.t.test`, and the `boot` package (`boot.ci`) for bootstrap intervals
