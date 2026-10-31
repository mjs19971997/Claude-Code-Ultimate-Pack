# Experiment Tracking, Registry and Reproducibility

MLflow tracking, autolog, logged models, the model registry with aliases, the tracking server, plus Weights & Biases, DVC and environment pinning in brief. Calls below were run against MLflow 3.17.2 with a SQLite backend on Python 3.13; the MLflow changelog was read through 3.17.2 (2026-10). W&B and DVC details were not run, so check their docs.

## Contents

1. [Backend and setup](#1-backend-and-setup)
2. [Logging a run](#2-logging-a-run)
3. [Autolog](#3-autolog)
4. [Logged models and the registry](#4-logged-models-and-the-registry)
5. [Searching and comparing](#5-searching-and-comparing)
6. [Tracking server](#6-tracking-server)
7. [Version notes for MLflow 3](#7-version-notes-for-mlflow-3)
8. [Weights and Biases](#8-weights-and-biases)
9. [Reproducibility](#9-reproducibility)
10. [Data versioning with DVC](#10-data-versioning-with-dvc)

## 1. Backend and setup

```python
import mlflow

mlflow.set_tracking_uri("sqlite:///mlflow.db")   # or http://tracking-host:5000
mlflow.set_experiment("churn-baseline")
```

- Use a database backend (SQLite for a laptop, PostgreSQL or MySQL for a team). In 3.17.2 `file:./mlruns` as the tracking store raised `MlflowException` stating that the filesystem backend is in maintenance mode; the changelog for 3.13 says file stores error unless `MLFLOW_ALLOW_FILE_STORE=true` is set. Prefer migrating over setting the variable.
- With SQLite, run metadata goes to the database file and artifacts still go to a local `mlruns/` directory by default. Keep both out of version control (`.gitignore`).
- Set the URI through the `MLFLOW_TRACKING_URI` environment variable in jobs and containers so code does not hard-code it.
- A remote server needs credentials and TLS configured at the server or proxy; put tokens in the environment, never in the script.

## 2. Logging a run

```python
import mlflow
from sklearn.metrics import average_precision_score

with mlflow.start_run(run_name="logreg-C0.1") as run:
    mlflow.set_tags({"git_sha": git_sha, "data_version": "2026-10-01", "stage": "dev"})
    mlflow.log_params({"C": 0.1, "class_weight": "balanced", "seed": 0})

    ds = mlflow.data.from_pandas(train_df, name="train", targets="y")
    mlflow.log_input(ds, context="training")

    model = pipe.set_params(clf__C=0.1).fit(X_train, y_train)
    mlflow.log_metric("val_ap", average_precision_score(y_val, model.predict_proba(X_val)[:, 1]))

    info = mlflow.sklearn.log_model(
        model, name="model", input_example=X_train.head(5),
        registered_model_name="churn-clf",       # optional: registers a new version
    )
    print(info.model_uri)
```

- Log parameters that define the run (hyperparameters, seed, feature set, split definition), metrics per evaluation set, tags for provenance (commit hash, data snapshot, pipeline version), and artifacts (plots, the confusion matrix, `requirements.txt` or the lockfile).
- `mlflow.log_metric(name, value, step=epoch)` gives curves; use `step` for iterations of boosting or training.
- `input_example` lets MLflow infer a signature and is used by `mlflow models predict` and serving checks. Check that the inferred signature matches the schema you intend to serve.
- Nested runs (`mlflow.start_run(nested=True)`) group a hyperparameter search under one parent.
- A failed run should be marked as such: leaving the `with` block through an exception sets the status to FAILED.
- In 3.x `log_model` takes `name=`; the older `artifact_path=` argument is still in the signature in 3.17.2. The returned object carries `model_uri` and `model_id`, and the model appears under the experiment's logged models.

## 3. Autolog

```python
import mlflow

mlflow.sklearn.autolog(log_datasets=False, serialization_format="skops")
# similar entry points exist: mlflow.xgboost.autolog(), mlflow.lightgbm.autolog()
```

- Autolog records estimator parameters, training metrics, cross-validation and grid-search child runs (it logged the best runs of a `GridSearchCV` as child runs in a check on 3.17.2) and optionally the model.
- In 3.17.2 `mlflow.sklearn.log_model` defaults to the `skops` format, but the `autolog` signature still defaults to `serialization_format="cloudpickle"` and logs a warning that pickle formats can execute code on load. Pass `serialization_format="skops"` explicitly.
- Autolog logs training-set metrics, which are optimistic. Always log held-out metrics yourself.
- Turn off what you do not need (`log_models=False`, `log_datasets=False`) in large searches to keep the store small; call `mlflow.autolog(disable=True)` to switch off.
- Autolog patches library calls; with several libraries in one script check which run received which parameters.

## 4. Logged models and the registry

The registry assigns versions to registered models. Use aliases, not stages.

```python
from mlflow import MlflowClient

client = MlflowClient()
client.set_registered_model_alias("churn-clf", "champion", "3")      # version 3
mv = client.get_model_version_by_alias("churn-clf", "champion")

model = mlflow.pyfunc.load_model("models:/churn-clf@champion")
preds = model.predict(X_new)
```

- Model URIs: `models:/<name>/<version>`, `models:/<name>@<alias>`, `runs:/<run_id>/<path>`, and in MLflow 3 `models:/<model_id>` for a logged model.
- An alias is a movable pointer ("champion", "challenger", "shadow"). Promotion is `set_registered_model_alias` to the new version; rollback is pointing it back. Serving and batch jobs resolve the alias at load time.
- Model version stages (`Staging`, `Production`) are deprecated; `get_latest_versions` emits a `FutureWarning` that stages will be removed in a future major release. Do not build new tooling on them.
- Tag versions with the validation metrics, data snapshot and approver (`client.set_model_version_tag`) so the promotion decision is traceable.
- Automate promotion with a gate: compare the candidate against the current champion on the same held-out data, then move the alias in CI. The `@latest` behaviour was fixed in 3.17 to resolve to the highest version number; check the release notes before relying on it.
- `mlflow.models.predict(model_uri, input_data=..., env_manager="virtualenv")` runs a prediction in a fresh environment built from the model's recorded requirements, which tests that the model is self-contained.
- Registry stores in files are in maintenance mode like the tracking store; use a database.

## 5. Searching and comparing

```python
runs = mlflow.search_runs(
    experiment_names=["churn-baseline"],
    filter_string="metrics.val_ap > 0.5 and params.class_weight = 'balanced'",
    order_by=["metrics.val_ap DESC"], max_results=10,
)
models = mlflow.search_logged_models(
    experiment_ids=[mlflow.get_experiment_by_name("churn-baseline").experiment_id],
    output_format="list",
)
```

- `search_runs` returns a pandas DataFrame with `metrics.*`, `params.*` and `tags.*` columns.
- Compare runs only when they share the split definition and data snapshot; log both as tags.
- Pick a candidate by validation score, then confirm on the locked test set once. Do not rank runs by test score.

## 6. Tracking server

```bash
mlflow server \
  --backend-store-uri postgresql://mlflow@db-host/mlflow \
  --default-artifact-root s3://my-bucket/mlflow-artifacts \
  --host 127.0.0.1 --port 5000 \
  --allowed-hosts "mlflow.example.com" \
  --cors-allowed-origins "https://mlflow.example.com"
```

- Run `mlflow server --help` for the flags of your version; `--backend-store-uri`, `--default-artifact-root`, `--serve-artifacts`, `--allowed-hosts` and `--cors-allowed-origins` exist in 3.17.2.
- Bind to localhost and expose through a reverse proxy with TLS and authentication. The tracking API can read and write models and artifacts; treat access to it as access to the production model store.
- Keep the database password and cloud credentials in environment variables or the platform secret store. Grant the server only the bucket prefix it needs.
- Upgrades that change the schema need `mlflow db upgrade <database-url>` with all writers stopped and a backup taken; the 3.17.0 notes state that mixed-version rolling upgrades are not supported.
- Back up the database and the artifact store together; a registry row without its artifact (or the reverse) is a broken model.

## 7. Version notes for MLflow 3

- MLflow 3 introduced logged models (`m-...` ids) as first-class objects linked to runs; `log_model(name=...)` returns them.
- 3.13 (May 2026): role-based access control replaced the earlier permission tables; MLServer was removed as a pyfunc serving backend; filesystem stores require an opt-in variable.
- 3.14 (June 2026): `serialization_format` default moved to `skops` for the sklearn and LightGBM flavors; `validate_serving_input` was deprecated in favour of `mlflow.models.predict`.
- 3.16 (September 2026): basic-auth fails closed by default.
- 3.17.2 is the current release on PyPI (requires Python 3.10 or newer). Much of recent MLflow development targets GenAI tracing and evaluation; the classical tracking and registry APIs above are the stable part.
- Read the release notes before an upgrade: `https://github.com/mlflow/mlflow/blob/master/CHANGELOG.md`.

## 8. Weights and Biases

- Hosted alternative or complement: `wandb.init(project=..., config={...})`, `wandb.log({...})`, `wandb.finish()`, with sweeps for hyperparameter search and artifacts for datasets and models. Version 0.31.0 is the latest on PyPI at the time of writing.
- Authentication is by API key (`WANDB_API_KEY` environment variable); never commit it. Offline mode (`WANDB_MODE=offline`) records locally for later sync.
- Choose one system of record per project. If both are used, log the same run id as a tag in each so results can be joined. For API details check the current W&B docs.

## 9. Reproducibility

- Seeds: set `random_state` on every estimator, splitter and search; set `numpy.random.default_rng(seed)` for your own sampling. Record the seeds as params. Seeds make a run repeatable on one machine; they do not make results identical across library versions, CPUs or thread counts.
- Determinism with threads: parallel boosting and BLAS reductions can change floating-point sums. For a strict comparison use fixed `n_jobs`, or accept differences below the fold-to-fold noise.
- Environment: pin direct and transitive dependencies in a lockfile (`uv lock` and `uv sync --locked`, `pip-compile`, or a conda lock) and record the Python version. MLflow saves `requirements.txt` and `conda.yaml` with each model; check they pin the scikit-learn version, because a pickle or skops file loaded under a different minor version is not guaranteed to behave the same.
- Container image digest and base image tag belong in the run tags for deployed models (see docker-expert).
- Data: record an immutable snapshot id (DVC revision, table snapshot, file hash) for every run; rerunning on "latest" data is not reproducing.
- Code: log the commit hash and whether the tree was dirty. MLflow records the source commit when run from a git checkout; make it explicit with a tag.
- Make training one command (`python -m project.train --config configs/exp1.yaml`) that writes everything it needs to MLflow; a notebook cell sequence is not reproducible.

## 10. Data versioning with DVC

- DVC stores data and model files outside git and commits small pointer files: `dvc add data/train.parquet` writes `data/train.parquet.dvc`; `dvc push` and `dvc pull` sync with a remote (S3, GCS, Azure, SSH, local path).
- Pipelines: `dvc.yaml` declares stages with `cmd`, `deps`, `params`, `outs` and `metrics`; `dvc repro` reruns only stages whose inputs changed; `dvc.lock` records the exact hashes.
- `dvc params diff` and `dvc metrics diff` compare experiments across git revisions. Latest PyPI version at the time of writing is 3.67.1; confirm the commands against the installed version with `dvc --help`.
- Never put credentials in `.dvc/config`; use `.dvc/config.local` (ignored by git) or environment variables.
- Alternatives that give the same effect: a versioned object-store prefix, Delta or Iceberg table snapshots, or a dataset registry in the tracking server. The requirement is an immutable id per training set.
