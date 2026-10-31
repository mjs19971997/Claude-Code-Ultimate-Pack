# Experiment Design for Simulation Studies

Designing comparisons of simulated systems: common random numbers for paired comparison, factorial designs and blocking analysed with a linear model, and the main regression pitfalls. The examples use a small M/M/1 queue (Lindley recursion, plain NumPy) so they run without a simulator. Output analysis of single runs (replications, warm-up, batch means) is in [simulation-output-analysis.md](simulation-output-analysis.md). Code blocks are self-contained and were run on SciPy 1.18.1, statsmodels 0.15.0, NumPy 2.5.4 and pandas 3.1.0 (2026-10).

## Contents

1. [Common random numbers](#1-common-random-numbers)
2. [Factorial designs and blocking](#2-factorial-designs-and-blocking)
3. [Screening many factors](#3-screening-many-factors)
4. [Blocks and randomisation in practice](#4-blocks-and-randomisation-in-practice)
5. [Regression basics and pitfalls](#5-regression-basics-and-pitfalls)

## 1. Common random numbers

```python
import numpy as np
from scipy import stats

def run(seed, mu, n=5_000, lam=0.8):
    ss = np.random.SeedSequence(seed).spawn(2)                  # separate arrival and service streams
    inter = np.random.default_rng(ss[0]).exponential(1 / lam, n)
    serv = np.random.default_rng(ss[1]).exponential(1.0, n) / mu    # same draws, scaled by the service rate
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w[500:].mean()

seeds = range(30)
a = np.array([run(s, mu=1.0) for s in seeds])         # baseline server
b = np.array([run(s, mu=1.1) for s in seeds])         # faster server, same seeds -> same random numbers
c = np.array([run(1000 + s, mu=1.1) for s in seeds])  # faster server, independent seeds

crn = stats.ttest_rel(a, b)
ind = stats.ttest_ind(a, c, equal_var=False)
d_crn = (a - b)
print(f"CRN paired : mean diff {d_crn.mean():.3f}, SE {stats.sem(d_crn):.3f}, p={crn.pvalue:.2e}")
print(f"independent: mean diff {a.mean() - c.mean():.3f}, SE {np.sqrt(a.var(ddof=1)/30 + c.var(ddof=1)/30):.3f}, p={ind.pvalue:.2e}")
```

- With common random numbers (CRN) the compared configurations see the same arrival times and the same underlying draws, so most of the run-to-run noise cancels in the difference. The variance of the difference falls when the outputs are positively correlated; the paired t-test or the CI of the paired differences uses that.
- Requirements: one independent stream per source of randomness, the same seeds across configurations, and a model structure where the draws are used in the same order. If the configurations consume random numbers in different orders, synchronisation breaks and CRN gives little.
- CRN reduces the variance of the difference, not of each configuration; the paired analysis is mandatory (an unpaired test wastes the correlation and is not wrong, only weak).
- For more than two systems, compare each with a baseline using CRN and a multiplicity correction (Dunnett or Holm; see [multiple-comparisons-effect-sizes.md](multiple-comparisons-effect-sizes.md)).
- Antithetic variates and control variates are further variance-reduction methods; check the simulation literature before using them, as they can backfire without care.

## 2. Factorial designs and blocking

```python
import itertools
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

def run(rng, lam, mu, n=4_000):
    inter = rng.exponential(1 / lam, n)
    serv = rng.exponential(1 / mu, n)
    w = np.zeros(n)
    for i in range(1, n):
        w[i] = max(0.0, w[i - 1] + serv[i - 1] - inter[i])
    return w[400:].mean()

rows = []
cells = list(itertools.product([0.6, 0.8], [1.0, 1.3]))                       # 2x2 design
for cell, (lam, mu) in enumerate(cells):
    for rep in range(8):                                                       # 8 replications per cell
        rng = np.random.default_rng(np.random.SeedSequence([2026, cell, rep]))
        rows.append({"lam": lam, "mu": mu, "rep": rep, "y": run(rng, lam, mu)})
df = pd.DataFrame(rows)
df["lam"] = df["lam"].astype("category")
df["mu"] = df["mu"].astype("category")

model = smf.ols("y ~ C(lam) * C(mu)", data=df).fit()
print(anova_lm(model, typ=2).round(4))
print(model.params.round(3))
print(model.conf_int().round(3))
```

- A factorial design varies all factors together (here 2 x 2). It estimates each main effect with the full sample and also the interaction, which one-factor-at-a-time experiments cannot see.
- Use a linear model (`ols` plus `anova_lm`) rather than many t-tests. Check residuals (QQ plot, residuals against fitted); a log transform of strictly positive outputs often fixes unequal variance.
- Replicate every cell, so that the error variance can be estimated. Without replication, the highest-order interaction is the only error estimate.
- Full factorials grow as `levels^factors`. For 6 or more factors use a fractional factorial or a space-filling design (Latin hypercube, `scipy.stats.qmc.LatinHypercube`, Sobol, `scipy.stats.qmc.Sobol`), and keep a few replications at the centre to estimate noise.
- Randomise the run order and the seed assignment so that no factor level is tied to a time trend, machine, or seed block. Where an unavoidable nuisance exists (machine, day, scenario input trace), treat it as a block: include it in the model as a factor and use the same blocks for every treatment.
- With stochastic inputs shared across configurations (the same traffic trace), the trace is a block, and the analysis is paired or blocked ANOVA.
- Report factor levels, the number of replications per cell, the model formula and the effect estimates with intervals.

## 3. Screening many factors

```python
import numpy as np
from scipy.stats import qmc

sampler = qmc.LatinHypercube(d=3, rng=np.random.default_rng(0))
unit = sampler.random(n=16)                                  # 16 points in [0, 1)^3
lower, upper = [0.3, 0.8, 1.0], [0.9, 2.0, 4.0]              # e.g. load, service rate, buffer size
design = qmc.scale(unit, lower, upper)
print(design.shape, design.min(axis=0).round(2), design.max(axis=0).round(2))
print("discrepancy:", round(qmc.discrepancy(unit), 4))

sobol = qmc.Sobol(d=3, scramble=True, rng=np.random.default_rng(0))
print(sobol.random_base2(m=4).shape)                         # 2**4 = 16 points, balanced
```

- A Latin hypercube covers each factor's range evenly with few runs; Sobol sequences (use powers of two for `n`) are better balanced. Both come with `scipy.stats.qmc`, whose samplers take `rng` for the seed.
- Fit a regression or a Gaussian-process metamodel on the design points, replicate some points to estimate noise, and treat the screening result as a ranking of factors to follow up, not as final inference.
- Integer or categorical factors need rounding or a mixed design; check that the rounded points still cover the space.

## 4. Blocks and randomisation in practice

- Randomise the order in which configurations are run and the assignment of seeds to cells (`rng.permutation`), then record the order. A time trend, a machine difference or a seed block cannot then masquerade as a factor effect.
- A block is a nuisance variable that groups runs: the same input trace, the same topology draw, the same machine. Apply every treatment inside each block and analyse with the block as a factor (`y ~ C(treatment) + C(block)`) or with a paired test for two treatments.
- Blocking with CRN is the standard way to compare several systems: each block shares seeds, each system is run once per block, and the block effect is removed from the error.
- Check that the design is balanced (same number of replications per cell). With unbalanced data use Type II or III sums of squares deliberately and state which.
- Write the design, the factor levels, the replication count, the seed policy and the analysis model before running the experiment.

```python
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

rng = np.random.default_rng(10)
blocks, systems = range(12), ["base", "tuned", "alt"]
block_effect = rng.normal(0, 2.0, len(blocks))                # shared trace difficulty
gain = {"base": 0.0, "tuned": -0.8, "alt": -0.3}
rows = [{"block": b, "system": s, "y": 10 + block_effect[b] + gain[s] + rng.normal(0, 0.4)}
        for b in blocks for s in systems]
df = pd.DataFrame(rows)

blocked = smf.ols("y ~ C(system) + C(block)", data=df).fit()
ignoring = smf.ols("y ~ C(system)", data=df).fit()
print(anova_lm(blocked, typ=2).round(4).loc[["C(system)"]])
print("system p, blocked:", round(float(anova_lm(blocked, typ=2).loc["C(system)", "PR(>F)"]), 5))
print("system p, ignoring blocks:", round(float(anova_lm(ignoring, typ=2).loc["C(system)", "PR(>F)"]), 3))
```

## 5. Regression basics and pitfalls

- `y ~ x` with `smf.ols` estimates the slope and its interval under the assumptions of linearity, independent errors, constant variance and roughly normal errors. Look at residual plots first, p-values second. Use `model.get_robustcov_results(cov_type="HC3")` or `fit(cov_type="HC3")` when the variance is not constant.
- Association is not causation. Regression on observational data shows conditional association; only randomised assignment (as in a designed simulation experiment) supports a causal reading.
- Extrapolating beyond the range of the fitted inputs is unreliable, especially near a saturation point such as utilisation approaching 1, where response is nonlinear. Fit on a transformed scale or choose a model from the physics (queueing: delay grows like `1 / (1 - rho)`).
- Collinear predictors give unstable coefficients with wide intervals; check variance inflation factors (`statsmodels.stats.outliers_influence.variance_inflation_factor`) and centre predictors before including interaction terms.
- A high R-squared does not mean a good model; compare against a holdout or cross-validation. For prediction tasks beyond inference, see ml-engineering-expert.
- Do not fit regression to autocorrelated time series of one run and trust the standard errors. Use replication means as the response.
- Include only the terms planned in the design; searching many models and reporting the best inflates significance.
