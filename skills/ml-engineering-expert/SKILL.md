---
name: ml-engineering-expert
description: >-
  Builds, validates and ships classical machine learning on tabular data: scikit-learn Pipelines and ColumnTransformer, cross-validation, data leakage prevention, class imbalance, XGBoost and LightGBM, MLflow tracking and registry aliases, model persistence with skops, serving and drift monitoring. Use when editing scikit-learn, mlflow, xgboost or lightgbm code, MLproject or dvc.yaml files, or debugging suspiciously high CV scores and train-serve mismatch. Not for neural network training loops (use pytorch-expert), LLM fine-tuning (use llm-finetuning-expert), hypothesis tests (use statistics-expert), data cleaning (use data-analysis-expert), or API framework details (use fastapi-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# ML Engineering Expert

This skill covers applied, classical machine learning engineering: scikit-learn pipelines, honest validation, leakage prevention, imbalance handling, gradient boosting, experiment tracking with MLflow, reproducibility, safe model persistence, serving and monitoring. It favours a single `Pipeline` object that carries all learned preprocessing, a locked test set, and a registry alias that deployment resolves. Deep learning loops, LLM fine-tuning, statistical inference, data wrangling and web framework internals belong to other skills.

> Verified against scikit-learn 1.9.1, MLflow 3.17.2, skops 0.16.0, XGBoost 3.4.1, LightGBM 4.7.0, pandas 3.1.0, FastAPI 0.162.0, skl2onnx 1.20.0 and onnxruntime 1.31.1 on Python 3.13 (2026-10). Versions of BentoML (1.4.40), DVC (3.67.1), Weights & Biases (0.31.0) and Evidently (0.7.23) were read from PyPI only; their APIs were not run.

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

- Covered: scikit-learn (`Pipeline`, `ColumnTransformer`, `cross_validate`, splitters, searches, metrics, calibration, threshold tuning, pandas output, metadata routing), data leakage and the train/validation/test protocol, nested cross-validation, class imbalance, XGBoost and LightGBM usage, MLflow tracking, autolog, logged models and registry aliases, Weights & Biases and DVC in brief, seeds and environment pinning, model persistence (skops, joblib, pickle risk), serving (MLflow, FastAPI wrapper, BentoML, ONNX), drift monitoring, feature stores in brief.
- Not covered: neural network training loops and GPU tuning (pytorch-expert); LLM fine-tuning (llm-finetuning-expert); hypothesis tests, confidence-interval theory, Bayesian models (statistics-expert); cleaning and reshaping raw data (data-analysis-expert); numerical computing and plotting (scientific-python-expert); FastAPI routing, dependencies and middleware (fastapi-expert); container builds (docker-expert); metrics, traces and alerting platforms (observability-expert); CI pipelines (cicd-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| scikit-learn 1.9 | Latest is 1.9.1 (September 2026, bug-fix release). 1.9 adds experimental callbacks (`ProgressBar`, `ScoringMonitor` via `set_callbacks`); 1.8 added temperature scaling in `CalibratedClassifierCV` and deprecated `LogisticRegression(penalty=...)` in favour of `l1_ratio` (removal planned for 1.10). Python 3.11 or newer is required |
| Pipelines | `Pipeline` and `ColumnTransformer` refit every learned step per fold. `set_output(transform="pandas")` keeps column names but raises on sparse output, so use `OneHotEncoder(sparse_output=False)` with it. `get_feature_names_out()` maps outputs to inputs |
| Splitters | `StratifiedKFold`, `GroupKFold`, `StratifiedGroupKFold`, `TimeSeriesSplit(gap=...)`, `RepeatedStratifiedKFold`. `GroupKFold` and `StratifiedGroupKFold` accept `shuffle` and `random_state` in 1.9.1 |
| Search | `GridSearchCV`, `RandomizedSearchCV`, `HalvingGridSearchCV`/`HalvingRandomSearchCV` (need `from sklearn.experimental import enable_halving_search_cv`). `TunedThresholdClassifierCV` tunes the decision threshold; `FrozenEstimator` replaces `cv="prefit"` |
| Metadata routing | Off by default; enable with `sklearn.set_config(enable_metadata_routing=True)` or `config_context`. Consumers declare `set_fit_request(sample_weight=True/False)`; `cross_validate` takes `params=` |
| Leakage | Preprocessing, selection, encoding, resampling, calibration and tuning must see training folds only. Group, temporal and duplicate leakage need matching splitters or deduplication. A leaky selection step gave 0.88 AUC on random labels against 0.54 inside a pipeline |
| Gradient boosting | `HistGradientBoosting*` first; XGBoost 3.x takes `early_stopping_rounds` in the constructor; LightGBM uses `lgb.early_stopping` callback. Both are scikit-learn compatible |
| MLflow 3.17 | `mlflow.sklearn.log_model(model, name="model")`; registry aliases via `MlflowClient.set_registered_model_alias` and `models:/<name>@<alias>`; model stages deprecated. Use a SQL backend: file stores are in maintenance mode and error in 3.17.2. `log_model` defaults to the `skops` format; `autolog` still defaults to `cloudpickle`, so pass `serialization_format="skops"` |
| Persistence | `pickle` and `joblib` execute code on load. `skops.io.dump/load` with `get_untrusted_types` is the safer scikit-learn format. ONNX and native booster formats are data formats |
| Serving | `mlflow models serve` exposes `/invocations`, `/health`, `/version` with no auth; wrap with FastAPI for contracts and auth; BentoML for packaging and batching; skl2onnx plus onnxruntime for pickle-free inference |
| Monitoring | Track data quality, input and prediction drift (PSI, KS statistic, category shares) and outcome metrics when labels mature. Drift alone does not prove degradation |

## 3. Workflow

1. Write down the prediction moment, the label definition and its delay, the cost of each error, and the unit new data will arrive in (new customer, new day). These decide the splitter and the metric.
2. Inspect the data's structure: duplicates, repeated entities, time column, class balance, missingness. Choose the splitter before modelling (see section 4).
3. Carve out and store the test set (ids or hash) before exploration that uses the label. Do not look at it again until the final check.
4. Build a baseline: `DummyClassifier`/`DummyRegressor`, then a regularised linear model in a `Pipeline`, then a gradient boosting model. Score all of them with the same CV.
5. Tune with a search inside the development split; use nested CV when data is small or when comparing tuning strategies.
6. Choose the operating point (threshold, calibration) on validation data; evaluate once on the test set; report spread, baseline and subgroup results.
7. Log the run: parameters, seeds, data snapshot id, commit hash, metrics, model with signature and pinned requirements.
8. Register the model, set an alias, test the artifact in a clean environment, then deploy by alias.
9. Monitor inputs, predictions and outcomes; define the retraining trigger and the rollback alias before launch.

## 4. Decision Rules

- If rows share an entity (customer, patient, device, image source), use a group-aware splitter; if rows are time ordered, use `TimeSeriesSplit` with a `gap` at least as long as the label delay. Never use a random split on drifting temporal data.
- If any step learns from data (scaler, imputer, encoder, selector, resampler), put it inside the `Pipeline`. Never call `fit_transform` on the full table before splitting.
- If the positive rate is below roughly 10 percent, report average precision and a calibration metric, stratify splits, and tune the threshold; do not report accuracy.
- If class imbalance matters, try `class_weight` or `sample_weight` before resampling; if you resample, do it inside the training fold only. Recalibrate if probabilities are consumed.
- If data is tabular and large, start with `HistGradientBoosting*`, LightGBM or XGBoost; if it is small or needs interpretability, start with regularised linear models. Compare against the dummy baseline every time.
- If you tune more than a handful of settings, use `RandomizedSearchCV` or halving; if you need an unbiased estimate of the whole procedure and have no spare test set, use nested CV.
- If the reported score will be used for a decision, quote the test-set result obtained once; never quote `best_score_` of a search as the generalisation estimate.
- If a model file comes from outside the process or team, never unpickle it; use skops with an explicit trusted list, or ONNX.
- If one model with simple inputs is served, use `mlflow models serve` behind a gateway or a small FastAPI app; if many models need batching and a build pipeline, evaluate BentoML; if Python must be absent at inference, export to ONNX and test parity.
- If promoting a model, move a registry alias after a gate against the current champion; do not use registry stages in new code.
- If results differ between runs, fix seeds and thread counts first, then check library versions, data snapshot and split definition.

## 5. Coding Standards

- Express preprocessing and model as one estimator (`Pipeline` or `make_pipeline`); name steps explicitly when tuning or logging, so parameters read `clf__C`, `pre__num__impute__strategy`.
- Pass `random_state` to every estimator, splitter and search; derive per-component seeds from one config value. Use `numpy.random.default_rng(seed)` for your own sampling.
- Keep `__init__` of custom estimators limited to storing arguments; learned attributes end with an underscore and are set in `fit`; use `validate_data` and `check_is_fitted`; run `check_estimator` in tests.
- Select columns by explicit lists or `make_column_selector`, set `remainder` deliberately, and use `handle_unknown="ignore"` for one-hot encoding of categories that can appear in production.
- Keep a typed config (dataclass or pydantic settings) for paths, seeds, split definition and hyperparameters; do not scatter literals through notebooks.
- Use `scoring=` strings or `make_scorer` consistently across cross-validation, search and reporting; never compare numbers computed with different metrics.
- Do not mutate input DataFrames inside transformers; return new objects.
- Keep notebooks for exploration; move training, evaluation and scoring into importable modules with a command line entry point.
- Log with `logging`; no prints of data samples that can contain personal data.

## 6. Project Structure

```text
churn-model/
|-- pyproject.toml            # dependencies, ruff, pytest config
|-- uv.lock                   # pinned environment (or requirements.lock)
|-- dvc.yaml                  # optional: data and pipeline stages
|-- configs/
|   `-- baseline.yaml         # seeds, split definition, hyperparameters
|-- src/churn/
|   |-- data.py               # loading, schema checks, split ids
|   |-- features.py           # ColumnTransformer builder, custom transformers
|   |-- train.py              # fit, tune, evaluate, log to MLflow
|   |-- evaluate.py           # metrics, thresholds, subgroup reports
|   |-- score.py              # batch scoring using the registry alias
|   `-- serve.py              # FastAPI wrapper (optional)
|-- tests/
|   |-- test_features.py      # transformer contracts, no-leak tests
|   `-- test_pipeline.py      # smoke fit and predict on a tiny frame
`-- notebooks/                # exploration only
```

- One entry point per job (`python -m churn.train --config configs/baseline.yaml`) that writes everything to the tracking server.
- Training and scoring import the same feature code. Never copy feature logic into the service.
- Store raw data outside git (object storage, DVC); store split ids or a split hash in git.

## 7. Design Patterns

- **Single estimator object**: preprocessing plus model in one `Pipeline`, logged and served as one artifact. Cost: debugging a step requires `named_steps` access.
- **Locked split artifact**: a table of `row_id, fold` written once and versioned. Cost: must be regenerated when rows are added; document the rule.
- **Search then refit then test**: `RandomizedSearchCV(refit=True)` on development data, `search.score(X_test, y_test)` once.
- **Nested CV for comparison**: `cross_validate(search, ..., cv=outer)` to compare model families fairly. Cost: outer x inner x candidates fits.
- **Frozen base plus calibrator**: `CalibratedClassifierCV(FrozenEstimator(base))` on a separate calibration set; threshold chosen on validation data with `TunedThresholdClassifierCV`.
- **Challenger/champion aliases**: candidates get `challenger`; the gate compares to `champion` on the same data; promotion moves the alias, rollback moves it back.
- **Shadow then canary rollout**: score in parallel without acting, then a small traffic share, then full.
- **Reference window monitoring**: a frozen, versioned reference sample compared against rolling production windows per feature and for the score.
- **Feature module shared by training and serving**: one function builds features as of a timestamp, used offline and online.

## 8. Best Practices

- Beat a trivial baseline before tuning; if a model barely beats `DummyClassifier(strategy="prior")`, improve data and features, not hyperparameters.
- Spend effort on the label definition, the feature availability audit and the split, in that order; algorithm choice usually matters less.
- Report the mean and spread over folds, the number of positives per evaluation set, and slices (new versus returning, region, segment).
- Prefer a few interpretable checks over a long list of metrics: ranking (AP or AUC), calibration (Brier), and the cost at the chosen threshold.
- Use `permutation_importance` on held-out data or SHAP-style attributions for sanity checks; impurity importances favour high-cardinality features.
- Treat a suspiciously high score as a leakage hypothesis first: run the drop-top-feature, shuffled-label and duplicate audits (see [references/data-leakage-validation.md](references/data-leakage-validation.md)).
- Keep seeds, versions, data snapshot id and commit hash with every logged run.
- Delete or archive stale runs and model versions on a policy; the registry is a production surface.
- Write the retraining trigger and the rollback procedure down before the first release.

## 9. Performance

- Profile first: time `fit` and `predict` separately, and check memory. Sparse matrices from `OneHotEncoder` are efficient for linear models; `HistGradientBoosting*` and LightGBM take dense or pandas input.
- Reduce cost in this order: fewer rows for tuning (halving, subsampled searches), fewer candidates (`RandomizedSearchCV`), simpler CV (3 to 5 folds), then parallelism.
- Parallelism multiplies: `n_jobs` in a search times threads in the estimator can oversubscribe cores. Set one level, and limit BLAS threads (`OMP_NUM_THREADS`) for process pools.
- Use `Pipeline(memory=...)` to cache expensive preprocessing during a search over model parameters only.
- Boosting: raise `learning_rate` during exploration, use early stopping on a separate set, and bound tree depth or leaves. Histogram-based learners scale to millions of rows.
- High-cardinality categoricals: `min_frequency`/`max_categories` in `OneHotEncoder`, `TargetEncoder` inside the pipeline, or native categorical support in LightGBM and XGBoost.
- Online latency: load once, batch requests, keep feature computation light, and consider ONNX Runtime. Measure p50 and p99 with realistic payloads.
- Do not tune hyperparameters on the full dataset when a representative sample ranks candidates the same; verify the ranking holds on the final fit.

## 10. Security

- Never load pickle, joblib or cloudpickle files from untrusted sources; they run code on load. Use `skops.io.load` with a reviewed `trusted` list, or ONNX and native booster formats.
- Restrict write access to the model store and registry; verify a SHA-256 of the artifact at load time in services; keep the tracking server behind TLS and authentication, bound to localhost or a private network.
- Keep tracking tokens, cloud credentials and database URLs in environment variables or a secret manager, not in code, configs or logged parameters. Do not log raw personal data as params, tags or artifacts.
- Validate inference input at the boundary: types, ranges, batch size, allowed categories. Reject rather than coerce; cap payload size.
- Remove direct identifiers and, where required, apply minimisation before training; check that the model or explanations cannot output raw training records.
- Pin dependencies from a lockfile and scan them; ML stacks have large dependency trees. Build images from pinned bases.
- Model files can leak training data (memorising classifiers, nearest-neighbour models store rows). Treat artifacts with the data's sensitivity.
- Check subgroup performance and document intended use; a model is a decision system with fairness and legal obligations beyond accuracy.

## 11. Testing

- Smoke test: fit the pipeline on a tiny synthetic frame, predict, and assert output shape and probability range.
- Leakage test: fit the pipeline on a frame where labels are random and assert the cross-validated AUC stays near 0.5; assert no split shares a group id (`set(g[train]) & set(g[test]) == set()`); assert `train.time.max() + gap < test.time.min()` for temporal splits.
- Transformer contract: `sklearn.utils.estimator_checks.check_estimator` for custom estimators; unit tests for edge cases (all-NaN column, unseen category, single-class fold).
- Invariance and regression tests: predictions on a frozen small dataset stay within a tolerance across code changes (`numpy.testing.assert_allclose`); keep the tolerance wider than platform noise.
- Serialisation round trip: dump with skops, load, compare predictions; load the registered model in a clean environment (`mlflow.models.predict`).
- Serving contract: test the service with valid, invalid and empty batches; check 422 on schema violations and latency under a realistic batch.
- Drift code: unit test PSI or KS helpers with identical and shifted samples.
- Run pytest in CI with the locked environment; run a short training job on sampled data as a pipeline test.

## 12. Review Checklist

- [ ] Prediction moment, label delay and feature availability are documented.
- [ ] Every learned step is inside a `Pipeline`; no `fit_transform` on the full table before splitting.
- [ ] Splitter matches the data (groups, time with `gap`, stratification); duplicates removed before splitting.
- [ ] Test set fixed before exploration and used once; nested CV or test score reported, not `best_score_`.
- [ ] A dummy baseline is reported with the same CV.
- [ ] Metrics fit the problem (AP and calibration for rare positives); spread and subgroup results shown.
- [ ] Threshold and calibration were chosen on validation data.
- [ ] Seeds set; versions, data snapshot id and commit hash logged.
- [ ] Model saved in skops, ONNX or a native format; no pickle from outside the trust boundary.
- [ ] Registry alias used (no stages); promotion gate defined; rollback path known.
- [ ] Input validation, auth and size limits exist at the serving boundary.
- [ ] Monitoring covers data quality, drift, predictions and outcomes, with a retraining trigger.

## 13. Production Notes

- Deploy by alias (`models:/<name>@champion`) and record the resolved version in logs and predictions so outcomes can be joined to model versions.
- Use a database-backed MLflow server with an object store for artifacts; back up both together. Upgrade the schema with `mlflow db upgrade` only with writers stopped; read the release notes (MLflow 3.x moves quickly, with recent releases focused on GenAI tracing).
- Test the model in a clean environment built from its recorded requirements before promotion; mismatched scikit-learn versions between training and serving are a common cause of load failures and subtle differences.
- Keep training and serving on identical feature code and library versions; store the feature schema with the model.
- Give batch jobs idempotent outputs keyed by entity, as-of date and model version.
- Set resource limits and timeouts on inference services; use readiness checks that confirm the model loaded.
- Plan label collection: without delayed labels there is no outcome monitoring. Retain a small random holdout of decisions when the business allows.
- Version the reference data used for drift detection and the thresholds; review alerts for noise after launch.
- Retire models explicitly: remove aliases, archive artifacts, and update dependent jobs.

## 14. Examples

A grouped development/test split, a pipeline, a cross-validated search and a once-only test score, plus nested CV (run on scikit-learn 1.9.1):

```python
import numpy as np
import pandas as pd
from scipy.stats import loguniform
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    RandomizedSearchCV, StratifiedGroupKFold, cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

rng = np.random.default_rng(0)
n = 800
df = pd.DataFrame({
    "age": rng.normal(40, 10, n),
    "income": rng.lognormal(10, 1, n),
    "city": rng.choice(["a", "b", "c"], n),
    "customer_id": rng.integers(0, 80, n),
})
df.loc[rng.random(n) < 0.1, "age"] = np.nan
y = ((df["age"].fillna(40) - 40) / 10 + rng.normal(0, 1, n) > 0.8).astype(int)
X, groups = df.drop(columns="customer_id"), df["customer_id"]

pre = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                      ("scale", StandardScaler())]),
     make_column_selector(dtype_include="number")),
    ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5),
     make_column_selector(dtype_exclude="number")),
])
pipe = Pipeline([("pre", pre),
                 ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])

# 1. Lock the test set first, grouped so no customer is on both sides.
outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)
dev_idx, test_idx = next(outer.split(X, y, groups))
X_dev, y_dev, g_dev = X.iloc[dev_idx], y.iloc[dev_idx], groups.iloc[dev_idx]
X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

# 2. Tune on the development part only.
search = RandomizedSearchCV(
    pipe, {"clf__C": loguniform(1e-3, 1e2)}, n_iter=10, scoring="average_precision",
    cv=StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=1),
    random_state=0, refit=True,
)
search.fit(X_dev, y_dev, groups=g_dev)

# 3. Touch the test set once.
print("best C:", search.best_params_["clf__C"])
print("test AP:", search.score(X_test, y_test))

# 4. Honest estimate of the whole tuning procedure.
nested = cross_validate(
    search, X_dev, y_dev, groups=g_dev, scoring="average_precision",
    cv=StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=2),
    params={"groups": g_dev},
)
print("nested AP:", nested["test_score"].mean())
```

Logging a run, registering the model and promoting it by alias (MLflow 3.17):

```python
import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("churn-baseline")

with mlflow.start_run(run_name="logreg"):
    mlflow.set_tags({"git_sha": "REPLACE_WITH_COMMIT", "data_version": "2026-10-01"})
    mlflow.log_params({"seed": 0, "C": search.best_params_["clf__C"]})
    mlflow.log_metric("test_ap", search.score(X_test, y_test))
    mlflow.sklearn.log_model(
        search.best_estimator_, name="model", input_example=X_dev.head(5),
        registered_model_name="churn-clf",
    )

client = MlflowClient()
client.set_registered_model_alias("churn-clf", "champion", "1")
model = mlflow.pyfunc.load_model("models:/churn-clf@champion")
```

Safe model file handling with skops:

```python
import skops.io as sio

sio.dump(search.best_estimator_, "model.skops")
untrusted = sio.get_untrusted_types(file="model.skops")
assert not untrusted, f"review before trusting: {untrusted}"
model = sio.load("model.skops", trusted=[])
```

Longer recipes: [references/sklearn-pipelines.md](references/sklearn-pipelines.md), [references/data-leakage-validation.md](references/data-leakage-validation.md), [references/model-serving-monitoring.md](references/model-serving-monitoring.md).

## 15. Common Mistakes

- **Fitting a scaler, imputer, PCA or feature selector on all data, then cross-validating**: the validation fold influenced preprocessing. Put the step in the `Pipeline`. On random labels this turned 0.54 AUC into 0.88.
- **Random split with repeated entities or time order**: near-copies or the future land in training. Use `StratifiedGroupKFold` or `TimeSeriesSplit(gap=...)`.
- **Reporting `search.best_score_` as the expected performance**: it is the maximum over candidates. Use a held-out test set once or nested CV.
- **Tuning thresholds, features or models on the test set**: the test set becomes a validation set. Keep it sealed, or collect a new one.
- **Resampling (SMOTE, oversampling) before the split**: duplicates and synthetic neighbours appear in validation. Resample inside the training fold.
- **Accuracy on imbalanced data**: a constant prediction scores high. Use average precision, recall at a precision target and calibration.
- **Using the validation fold for both early stopping and the reported score in boosting**: mildly optimistic. Use a separate early-stopping split or fixed rounds.
- **Target encoding computed manually on the full table**: leaks the label. Use `TargetEncoder` inside a `Pipeline`.
- **`OneHotEncoder` with default sparse output under `set_output(transform="pandas")`**: raises `ValueError`. Pass `sparse_output=False`.
- **`LogisticRegression(penalty="l1")` in new code**: deprecated since scikit-learn 1.8; use `l1_ratio`.
- **Enabling metadata routing and passing `sample_weight` without `set_*_request`**: `UnsetMetadataPassedError`, including for the default scorer. Declare requests on every consumer or pass a scorer with `set_score_request`.
- **`joblib.load` or `pickle.load` on a downloaded model**: arbitrary code execution. Use skops with a trusted list or ONNX.
- **MLflow `file:./mlruns` tracking store**: in maintenance mode and erroring in 3.17.2. Use SQLite or a server database.
- **`autolog` with its default `cloudpickle` format**: pass `serialization_format="skops"`.
- **Registry stages (`Staging`, `Production`) in new tooling**: deprecated. Use aliases.
- **Comparing runs with different splits or data snapshots**: differences reflect the data. Log and match the split and snapshot id.
- **Drift alarm on a p-value at large sample size**: tiny effects become significant. Threshold an effect size such as PSI or the KS statistic, and confirm with outcome metrics.
- **Training-serving skew from reimplemented features**: share one feature module and test parity on the same rows.
- **No baseline**: a complex model that does not beat `DummyClassifier` has learned nothing; check the label and features.

## 16. References

- [references/sklearn-pipelines.md](references/sklearn-pipelines.md): Pipeline and ColumnTransformer patterns, pandas output, custom transformers, hyperparameter search, metrics, imbalance and thresholds, calibration, metadata routing, XGBoost and LightGBM, version notes.
- [references/data-leakage-validation.md](references/data-leakage-validation.md): train/validation/test protocol, splitter choice, leakage catalogue, runnable leakage demo, nested CV, temporal validation, detection techniques, reporting, checklist.
- [references/experiment-tracking-mlflow.md](references/experiment-tracking-mlflow.md): MLflow backend and setup, logging runs, autolog, logged models and registry aliases, search, tracking server, MLflow 3 version notes, Weights & Biases, seeds and environment pinning, DVC.
- [references/model-serving-monitoring.md](references/model-serving-monitoring.md): persistence formats and skops loading, MLflow serving, FastAPI wrapper, BentoML, ONNX export, batch scoring, drift and outcome monitoring, retraining and rollout, feature stores.
- scikit-learn: https://scikit-learn.org/stable/ (user guide, model persistence, cross-validation, metadata routing) and release notes https://scikit-learn.org/stable/whats_new.html
- MLflow: https://mlflow.org/docs/latest/ and changelog https://github.com/mlflow/mlflow/blob/master/CHANGELOG.md
- skops: https://skops.readthedocs.io/
- XGBoost: https://xgboost.readthedocs.io/ ; LightGBM: https://lightgbm.readthedocs.io/
- DVC: https://dvc.org/doc ; Weights & Biases: https://docs.wandb.ai/ ; BentoML: https://docs.bentoml.com/
- ONNX Runtime: https://onnxruntime.ai/ ; sklearn-onnx: https://onnx.ai/sklearn-onnx/
