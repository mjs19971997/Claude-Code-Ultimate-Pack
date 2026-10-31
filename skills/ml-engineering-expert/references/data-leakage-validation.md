# Data Leakage and Validation Protocol

How to split data, which leakage patterns occur in practice, how to detect them, and how to estimate performance honestly with cross-validation, nested CV and a locked test set. Splitters and demos were run on scikit-learn 1.9.1 (2026-10).

## Contents

1. [Protocol: train, validation, test](#1-protocol-train-validation-test)
2. [Choosing the splitter](#2-choosing-the-splitter)
3. [Leakage catalogue](#3-leakage-catalogue)
4. [Demonstration: selection outside the pipeline](#4-demonstration-selection-outside-the-pipeline)
5. [Nested cross-validation](#5-nested-cross-validation)
6. [Temporal validation](#6-temporal-validation)
7. [Detecting leakage](#7-detecting-leakage)
8. [Reporting results](#8-reporting-results)
9. [Leakage review checklist](#9-leakage-review-checklist)

## 1. Protocol: train, validation, test

1. Define the prediction moment first: what is known when the model is called in production, and what the label is. Every feature must exist at that moment with the same delay it will have in production.
2. Split before any exploration that uses the label. The test set is carved out once, with a fixed seed, and stored (row ids or a hash) so it cannot drift.
3. Everything that learns (imputation values, scaling, encodings, feature selection, resampling, calibration, thresholds, hyperparameters, early-stopping round, model choice) is fit on training data only, inside a `Pipeline` or inside the training fold.
4. Use cross-validation on the development part (train plus validation) to compare models and tune. The validation score is used up by tuning.
5. Evaluate the single chosen model on the test set once. If the result prompts another round of changes, the test set has become a validation set; collect a new one or report that it is no longer clean.
6. Refit on all development data (or development plus test, when the protocol allows it) for the final artifact, with the hyperparameters chosen earlier.

Typical fractions: a test set large enough to give a useful confidence interval for the metric (the number of positives matters more than total rows). For small data prefer repeated or nested CV over a single tiny test set.

## 2. Choosing the splitter

| Data structure | Splitter | Notes |
|---|---|---|
| Independent rows, classification | `StratifiedKFold(shuffle=True, random_state=...)` | Keeps class ratio per fold |
| Independent rows, regression | `KFold(shuffle=True, random_state=...)` | Stratify on binned target if skewed |
| Repeated entities (customer, patient, device, session, image source) | `GroupKFold`, `StratifiedGroupKFold` | Pass `groups=`; no group in two folds |
| Time ordered | `TimeSeriesSplit(n_splits, gap=..., test_size=...)` | Train always precedes validation; `gap` skips rows between them |
| Small data | `RepeatedStratifiedKFold` | Averages split noise |
| Spatial autocorrelation | Group by region or block | Standard CV is optimistic for neighbours |

- Use `shuffle=True` with `random_state` for `KFold` variants on data that is sorted by label or time, but not for time series.
- `GroupKFold` and `StratifiedGroupKFold` take `shuffle` and `random_state` in 1.9.1 (default `shuffle=False`); older releases had no `shuffle` on `GroupKFold`. Use `StratifiedGroupKFold` when you need both stratification and group separation.
- The group definition is a modelling decision: split by the unit the model will meet as new (a new customer, a new hospital), not by the row.
- Splits and `groups` go to `cross_validate(..., groups=g, cv=cv)`; for searches, `search.fit(X, y, groups=g)`.

## 3. Leakage catalogue

| Type | What happens | Fix |
|---|---|---|
| Preprocessing leakage | Scaler, imputer, PCA, encoder or feature selector fitted on all rows, then split | Put every learned step in the `Pipeline`; never call `fit_transform` before the split |
| Target leakage | A feature encodes the label or its consequence (refund flag for a fraud label, discharge code for a diagnosis, "days to churn") | Audit features against the prediction moment; drop or time-shift them |
| Target encoding leakage | Category mean of the target computed on the same rows | `TargetEncoder` inside a pipeline (cross-fits in `fit_transform`), or compute on training fold only |
| Group leakage | Same customer, patient or image source in train and validation | Group-aware splitter |
| Temporal leakage | Future rows in training, or features aggregated over a window that crosses the split date | Time-ordered split with `gap`; build features as of each row's timestamp |
| Duplicate leakage | Identical or near-identical rows on both sides (scraped copies, augmented images, oversampled rows) | Deduplicate before splitting; resample only inside the training fold |
| Tuning on the test set | Choosing model, threshold or features by looking at test results | Keep the test set untouched until the end |
| Selection bias in tuning | Reporting `best_score_` of a search as the generalisation estimate | Nested CV or a separate test set |
| Early-stopping leakage | The validation set that stops boosting is also the reported score | Separate early-stopping set per fold, or fixed rounds |
| Label-derived imputation | Missing values filled using the target | Fill from features only, inside the pipeline |
| ID and ordering artefacts | Row id, file name, timestamp or export order correlates with the label | Drop identifiers; test with shuffled ids |
| Look-ahead in aggregates | Rolling means, lags, "customer lifetime" values computed over the whole table | Compute features per as-of date; lag by at least the label delay |
| Monitoring leakage | Drift thresholds or scoring windows tuned on the evaluation period | Freeze reference data and thresholds before the evaluation period |

## 4. Demonstration: selection outside the pipeline

Random labels have no signal, so the honest score is about 0.5 AUC. Selecting 20 of 2000 features on all rows before cross-validation produces a high score on noise (run on scikit-learn 1.9.1: 0.881 leaky, 0.54 clean).

```python
import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline

rng = np.random.default_rng(0)
X = rng.normal(size=(100, 2000))
y = rng.integers(0, 2, 100)
cv = StratifiedKFold(5, shuffle=True, random_state=0)

X_sel = SelectKBest(f_classif, k=20).fit_transform(X, y)        # leaks the labels
leaky = cross_val_score(LogisticRegression(), X_sel, y, cv=cv, scoring="roc_auc")

pipe = make_pipeline(SelectKBest(f_classif, k=20), LogisticRegression())
clean = cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc")
print(leaky.mean(), clean.mean())
```

The same shape of bug appears with any step that sees `y` (target encoding, supervised binning, SMOTE, feature selection) or whole-table statistics (scaling, PCA, imputation) applied before the split.

## 5. Nested cross-validation

An inner loop tunes; an outer loop scores the whole tuning procedure on data the inner loop never saw. Use it to compare models or tuning strategies on small data, or to report an unbiased estimate when no separate test set exists.

```python
from scipy.stats import loguniform
from sklearn.model_selection import (
    RandomizedSearchCV, StratifiedGroupKFold, cross_validate,
)

inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=1)
outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=2)

search = RandomizedSearchCV(
    pipe, {"clf__C": loguniform(1e-3, 1e2)}, n_iter=10,
    scoring="average_precision", cv=inner, random_state=0,
)
res = cross_validate(
    search, X_dev, y_dev, groups=g_dev, cv=outer,
    scoring="average_precision", params={"groups": g_dev},
)
print(res["test_score"].mean(), res["test_score"].std())
```

- `groups=` feeds the outer splitter; `params={"groups": ...}` forwards the groups to `search.fit` for the inner splitter (run on 1.9.1 with metadata routing off).
- Cost is outer folds times inner folds times candidates. Reduce `n_iter` or use halving search, and set `n_jobs` at one level.
- Nested CV estimates the performance of the procedure, not of one model. The final model is the search refit on all development data.
- Do not use nested CV to select hyperparameters; its inner loop already does that in each outer fold, and each outer fold may pick different values.

## 6. Temporal validation

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=4, gap=5)       # gap rows skipped between train and test
for train_idx, test_idx in tscv.split(X):
    assert train_idx.max() + 5 < test_idx.min()
```

- Sort the data by time first; `TimeSeriesSplit` assumes row order is time order.
- Set `gap` to at least the label delay (the time between an event and the moment its label is known) and the longest lookback overlap of features.
- Hold out the most recent period as the test set. A random split of temporal data overestimates performance whenever the distribution drifts.
- For several entities over time, combine: split by time, and make sure entity-level features use only past data.
- Rolling-origin evaluation (train on a window, score the next period, advance) shows how the score changes over time, which is also a drift signal.

## 7. Detecting leakage

- **Too good**: a score far above the best known baseline, or a single feature with near-perfect importance, is a prompt to look for leakage before celebrating.
- **Drop-column test**: remove the top feature; a collapse in performance points to a proxy for the label.
- **Shuffled-label control**: run the full pipeline on permuted labels (`sklearn.model_selection.permutation_test_score`); a score clearly above chance means the pipeline leaks.
- **Adversarial validation**: train a classifier to tell train rows from test rows. AUC well above 0.5 means the split is not representative (drift, ordering, ids), and the top features say why.
- **Duplicate audit**: hash rows (or key columns) and count overlaps between train and test; for text or images use near-duplicate search.
- **Production gap**: offline score much higher than online score is the commonest symptom; compare feature values computed offline and online for the same entity and time.
- **Pipeline audit**: grep for `fit_transform(` or `.fit(` on the full frame before `train_test_split` or `cross_val_*`.

## 8. Reporting results

- Report the mean and spread across folds (standard deviation or an interval) and the number of positives in each evaluation set; a single number hides variance.
- Report the baseline (`DummyClassifier`, last value, simple rule) and the metric at the operating point, not only a ranking metric.
- For a held-out set, a bootstrap interval of the metric (resampling rows, or groups when they exist) is a reasonable uncertainty estimate; for model comparison use paired differences on the same folds. Formal tests belong to statistics-expert.
- Record seeds, split definitions, library versions and the data snapshot id with the result (see [experiment-tracking-mlflow.md](experiment-tracking-mlflow.md)).
- Slice results by relevant subgroups (region, new versus returning users); an aggregate can hide a failing slice.

## 9. Leakage review checklist

- [ ] The prediction moment and label delay are written down.
- [ ] Every feature is available at that moment with the production delay.
- [ ] Test rows were separated before exploration and fixed by id or hash.
- [ ] All learned steps sit in a `Pipeline`; none is fit on the full table.
- [ ] Splitter matches the structure (groups, time); `gap` covers the label delay.
- [ ] Duplicates and near-duplicates were removed before the split.
- [ ] Resampling, target encoding and feature selection happen only inside training folds.
- [ ] Hyperparameters, thresholds and calibration were chosen without the test set.
- [ ] A shuffled-label or dummy-baseline control was run.
- [ ] The reported number comes from nested CV or a test set used once.
