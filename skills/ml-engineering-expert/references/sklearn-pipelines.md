# scikit-learn Pipelines and Model Selection

Pipelines, ColumnTransformer, pandas output, hyperparameter search, imbalance handling, threshold tuning, calibration, metadata routing and gradient boosting libraries. Code blocks were run against scikit-learn 1.9.1, pandas 3.1.0, XGBoost 3.4.1 and LightGBM 4.7.0 on Python 3.13 (2026-10).

## Contents

1. [Pipeline and ColumnTransformer](#1-pipeline-and-columntransformer)
2. [Pandas output and feature names](#2-pandas-output-and-feature-names)
3. [Custom transformers](#3-custom-transformers)
4. [Hyperparameter search](#4-hyperparameter-search)
5. [Metrics and scoring](#5-metrics-and-scoring)
6. [Class imbalance and thresholds](#6-class-imbalance-and-thresholds)
7. [Calibration](#7-calibration)
8. [Metadata routing](#8-metadata-routing)
9. [Gradient boosting libraries](#9-gradient-boosting-libraries)
10. [Version notes](#10-version-notes)

## 1. Pipeline and ColumnTransformer

Every step that learns from data (imputer, scaler, encoder, feature selector, resampler, target encoder) belongs inside the `Pipeline`, so cross-validation refits it on each training fold.

```python
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

pre = ColumnTransformer(
    [
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]),
         make_column_selector(dtype_include="number")),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5),
         make_column_selector(dtype_exclude="number")),
    ],
    remainder="drop",
)
pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])
```

- `remainder="drop"` is the default: a column not named in any transformer disappears silently. Use `remainder="passthrough"` deliberately, or list every column.
- Select columns by explicit name lists where possible. `make_column_selector` by dtype also catches bool and `category` columns under `dtype_exclude="number"`; print the selected names (`selector(X)`) before trusting it. On pandas 3 text columns have the `str` dtype, and `dtype_include=object` still matched them in the check run for this skill.
- `handle_unknown="ignore"` on `OneHotEncoder` keeps inference from failing on a category unseen in training. `min_frequency` or `max_categories` bounds the width for high-cardinality columns.
- Trees do not need scaling. `HistGradientBoostingClassifier` and `HistGradientBoostingRegressor` accept NaN and take `categorical_features="from_dtype"` for pandas `category` columns.
- Reach a nested parameter with a double underscore: `pipe.set_params(clf__C=0.5)`, `pre__num__impute__strategy`.
- `make_pipeline` and `make_column_transformer` auto-name steps; use the explicit form when you tune or log by name.
- `Pipeline(..., memory="cache_dir")` caches fitted transformers during a search; clear the directory when the data changes.
- `sklearn.frozen.FrozenEstimator(est)` wraps an already fitted estimator so that `fit` does nothing. It replaces the old `cv="prefit"` pattern.

## 2. Pandas output and feature names

```python
pre.set_output(transform="pandas")      # or sklearn.set_config(transform_output="pandas")
names = pre.fit(X_train).get_feature_names_out()
```

- Pandas output keeps column names and the index through the pipeline; it is useful for debugging and for models that read column names (LightGBM, XGBoost with `enable_categorical`).
- Pandas output does not support sparse data. `OneHotEncoder` with the default sparse output raises `ValueError: Pandas output does not support sparse data`; pass `sparse_output=False` or leave the output as default numpy.
- `get_feature_names_out()` works after fitting and is how you map coefficients or importances back to inputs.
- Fit on a DataFrame and predict on a DataFrame with the same column names; reordered or missing columns raise an error in modern versions. Validate the schema at the serving boundary rather than rely on this.

## 3. Custom transformers

```python
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted, validate_data


class Clipper(TransformerMixin, BaseEstimator):
    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        X = validate_data(self, X)
        self.lo_, self.hi_ = np.quantile(X, [self.lower, self.upper], axis=0)
        return self

    def transform(self, X):
        check_is_fitted(self)
        X = validate_data(self, X, reset=False)
        return np.clip(X, self.lo_, self.hi_)
```

- `__init__` only stores arguments, unchanged, so `clone` and `get_params` work. Learned values end in an underscore and are set in `fit`.
- `validate_data` (from `sklearn.utils.validation`) records `n_features_in_` and `feature_names_in_`; call it with `reset=False` in `transform`.
- Use `FunctionTransformer` for stateless functions (log, ratio). A stateless function can still leak if it uses statistics of the whole frame; compute those inside `fit`.
- `sklearn.utils.estimator_checks.check_estimator(Clipper())` runs the library's own contract tests; use it in unit tests for shared transformers.

## 4. Hyperparameter search

| Tool | Use when |
|---|---|
| `GridSearchCV` | Few discrete parameters, small grid |
| `RandomizedSearchCV` | Many parameters or continuous ranges; fixed budget via `n_iter`; draw from `scipy.stats` distributions such as `loguniform` |
| `HalvingGridSearchCV`, `HalvingRandomSearchCV` | Large candidate sets, resource that can be subsampled (samples or `n_estimators`); needs `from sklearn.experimental import enable_halving_search_cv` |
| Optuna or similar | Adaptive search, pruning, conditional spaces; keep the CV protocol identical |

```python
from scipy.stats import loguniform
from sklearn.model_selection import RandomizedSearchCV, StratifiedGroupKFold

search = RandomizedSearchCV(
    pipe, {"clf__C": loguniform(1e-3, 1e2)}, n_iter=20,
    scoring="average_precision", refit=True, random_state=0, n_jobs=-1,
    cv=StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=1),
)
search.fit(X_dev, y_dev, groups=g_dev)
```

- Search on the development split only; evaluate the refit estimator on the held-out test set once. `search.best_score_` is optimistically biased because it is the maximum over candidates; nested CV removes that bias (see [data-leakage-validation.md](data-leakage-validation.md)).
- Pass `groups=` to `fit` when the splitter needs it. With metadata routing off, `groups` reaches the splitter through `fit`.
- Multi-metric search: `scoring={"ap": "average_precision", "auc": "roc_auc"}` with `refit="ap"`.
- Halving starts each candidate on a small sample. With imbalanced targets a small sample can contain one class, giving `nan` scores and a warning that only one class is present; raise `min_resources`.
- Inspect `search.cv_results_` (as a DataFrame) for the spread of scores; a flat plateau means the choice does not matter and a simpler model may do.
- `n_jobs=-1` multiplies with the estimator's own threads (`HistGradientBoosting`, XGBoost); cap one level to avoid oversubscription.

## 5. Metrics and scoring

- Classification with a positive rate below about 10 percent: report `average_precision` (PR AUC), recall at a chosen precision, and a calibration measure (`neg_brier_score` or `neg_log_loss`). Accuracy is not informative.
- `roc_auc` ranks only; it says nothing about calibrated probabilities or the cost of an operating point.
- Multiclass: pick `f1_macro` (classes equal) or `f1_weighted` (frequency weighted) deliberately; `roc_auc_ovr` needs `predict_proba`.
- Regression: `neg_root_mean_squared_error` or `neg_mean_absolute_error`; compare against a `DummyRegressor` baseline. `r2` can be negative on held-out data.
- Always compare to `DummyClassifier(strategy="prior")` or `DummyRegressor` in the same CV; a model that does not beat it has learned nothing.
- `cross_validate(..., scoring=[...], return_train_score=True)` gives the train/validation gap; a large gap indicates overfitting, equal low scores indicate underfitting.
- Custom scorer: `make_scorer(fn, greater_is_better=False, response_method="predict_proba")`. Metrics for decision cost belong in business units (cost matrix), computed at the chosen threshold.

## 6. Class imbalance and thresholds

1. Keep the natural class ratio in validation and test splits; stratify (`StratifiedKFold`, `StratifiedGroupKFold`).
2. Prefer `class_weight="balanced"` or `sample_weight` to resampling. Resampling must happen inside the training fold only (`imblearn.pipeline.Pipeline` from the separate imbalanced-learn package); resampling before the split puts duplicates or synthetic neighbours in the validation fold.
3. Weighting and resampling distort probabilities. Recalibrate if the output is used as a probability (section 7).
4. Choose the threshold on validation data, not at 0.5:

```python
from sklearn.model_selection import TunedThresholdClassifierCV

tuned = TunedThresholdClassifierCV(pipe, scoring="f1", cv=5, refit=True, random_state=0)
tuned.fit(X_train, y_train)
print(tuned.best_threshold_)
```

`TunedThresholdClassifierCV` refits the base model and stores `best_threshold_`; the scoring metric can be any scorer, including a custom cost-based one. The threshold itself needs a stable estimate: with few positives, report its variability across folds.

- XGBoost has `scale_pos_weight`; LightGBM has `is_unbalance` and `scale_pos_weight`. Use one mechanism, not several.

## 7. Calibration

```python
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.model_selection import train_test_split

X_fit, X_cal, y_fit, y_cal = train_test_split(X_train, y_train, stratify=y_train, random_state=0)
base = pipe.fit(X_fit, y_fit)
cal = CalibratedClassifierCV(FrozenEstimator(base), method="isotonic").fit(X_cal, y_cal)
```

- Methods: `"sigmoid"` (Platt, few parameters, good for small calibration sets), `"isotonic"` (flexible, needs a few thousand samples or it overfits), and `"temperature"` (added in scikit-learn 1.8, suited to multiclass).
- Calibrate on data not used to fit the base model, or pass an unfitted estimator and `cv=5` so the wrapper does the cross-fitting.
- Check with `sklearn.calibration.CalibrationDisplay.from_predictions` and `brier_score_loss`; calibration is judged on held-out data, never on the calibration set.
- Calibrate after any threshold-independent training choice such as class weights.

## 8. Metadata routing

Routing sends `sample_weight`, `groups` and similar arguments to the steps that declare they want them. It is off by default.

```python
import sklearn
from sklearn.metrics import get_scorer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

with sklearn.config_context(enable_metadata_routing=True):
    pp = make_pipeline(
        StandardScaler().set_fit_request(sample_weight=False),
        LogisticRegression().set_fit_request(sample_weight=True),
    )
    scorer = get_scorer("roc_auc").set_score_request(sample_weight=True)
    cross_validate(pp, X, y, cv=StratifiedKFold(5), scoring=scorer,
                   params={"sample_weight": w})
```

- With routing on, every consumer that receives the metadata must state `True` or `False`; otherwise `UnsetMetadataPassedError` is raised, including for the default scorer (`score`) and for each step.
- `cross_validate` and `cross_val_score` take `params=` (the older `fit_params=` was replaced).
- Metadata routing support is still being extended across meta-estimators; the 1.9.x patch releases fix several routing bugs. Test the exact combination you rely on.

## 9. Gradient boosting libraries

For tabular data the order of try is: `HistGradientBoosting*` (no extra dependency), then LightGBM or XGBoost when you need their features (GPU, categorical handling, monotone constraints, ranking objectives, distributed training).

```python
import xgboost as xgb
import lightgbm as lgb

xgb_clf = xgb.XGBClassifier(
    n_estimators=2000, learning_rate=0.05, early_stopping_rounds=50,
    eval_metric="aucpr", n_jobs=4, random_state=0,
)
xgb_clf.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

lgb_clf = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.05, random_state=0, verbose=-1)
lgb_clf.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], eval_metric="average_precision",
            callbacks=[lgb.early_stopping(50, verbose=False)])
```

- In XGBoost 3.x `early_stopping_rounds` is a constructor argument, not a `fit` argument. LightGBM uses the `lgb.early_stopping` callback.
- Early stopping needs a validation set that is separate from the test set; with cross-validation, early-stop inside each training fold (`eval_set` from that fold) or fix `n_estimators` from a prior run. Using the fold's own validation part for stopping and scoring is mild leakage.
- Tune `learning_rate`, `max_depth` or `num_leaves`, `min_child_samples` or `min_child_weight`, `subsample`, `colsample_bytree`, `reg_lambda`. Lower learning rate with more trees is the usual trade of time for score.
- Both estimators are scikit-learn compatible, so they sit inside a `Pipeline` and work with `GridSearchCV`; set `n_jobs` on one level only.
- Determinism: set `random_state`; multi-threaded histogram building can still give small floating-point differences between machines.
- Native categorical support (`enable_categorical=True` in XGBoost, `category` dtype in LightGBM) avoids one-hot width; handle unseen categories explicitly at serving time.

## 10. Version notes

- scikit-learn 1.9 adds experimental callbacks (`sklearn.callback.ProgressBar`, `ScoringMonitor`, set with `set_callbacks`); the API may change without deprecation. 1.9.1 is a bug-fix release (September 2026).
- scikit-learn 1.8 deprecates the `penalty` parameter of `LogisticRegression` (removal in 1.10); use `l1_ratio` (0 is L2, 1 is L1) and `C`. `TargetEncoder` parameters `shuffle` and `random_state` also show as deprecated in 1.9.1.
- `TargetEncoder.fit_transform` cross-fits internally, while `fit(X, y).transform(X)` on the same data does not and leaks the target; inside a `Pipeline` this is handled correctly.
- Array API support (GPU arrays through PyTorch or CuPy) is experimental and must be enabled in configuration; check the current docs for the estimators supported.
- Check the changelog before upgrading: run the test suite with `-W error::FutureWarning` to catch deprecations early.
