# Model Persistence, Serving and Monitoring

Saving and loading models safely, serving with MLflow, a FastAPI wrapper, BentoML, ONNX export, batch scoring, drift and performance monitoring, and a short note on feature stores. The skops, FastAPI, ONNX and `mlflow models serve` snippets were run with skops 0.16.0, scikit-learn 1.9.1, MLflow 3.17.2, FastAPI 0.162.0, skl2onnx 1.20.0 and onnxruntime 1.31.1 on Python 3.13 (2026-10).

## Contents

1. [Persistence formats](#1-persistence-formats)
2. [Loading with skops](#2-loading-with-skops)
3. [Serving with MLflow](#3-serving-with-mlflow)
4. [FastAPI wrapper](#4-fastapi-wrapper)
5. [BentoML](#5-bentoml)
6. [ONNX export](#6-onnx-export)
7. [Batch scoring](#7-batch-scoring)
8. [Monitoring and drift](#8-monitoring-and-drift)
9. [Retraining and rollout](#9-retraining-and-rollout)
10. [Feature stores](#10-feature-stores)

## 1. Persistence formats

| Format | Safe to load untrusted file | Notes |
|---|---|---|
| `pickle`, `joblib.dump` | No | Loading runs arbitrary code. Only for files you produced and keep in a trusted location |
| `cloudpickle` | No | Same risk, wider object coverage |
| `skops.io` | Yes, when you check trusted types | Restricted loader for scikit-learn objects and common NumPy/SciPy types; refuses unknown types unless trusted |
| ONNX | Yes (data format, executed by a runtime) | Inference only; converts many but not all scikit-learn estimators |
| XGBoost `save_model` (JSON/UBJ), LightGBM `save_model` (text) | Yes (data formats) | Native formats avoid pickle; the preprocessing pipeline still needs its own format |

- The scikit-learn docs recommend skops for persistence of estimators across environments and warn about pickle security; also pin the same library versions on both sides, because no format guarantees behaviour across scikit-learn versions.
- Store the model file together with the versions of Python, scikit-learn, NumPy and any custom code; MLflow's `requirements.txt`/`conda.yaml` serve this purpose.
- Sign or hash model files in the registry or object store (SHA-256 checked at load) and restrict who can write to the model bucket. A tampered pickle is remote code execution on the serving host.
- Custom classes (your own transformers) must be importable at load time. With skops they appear in the untrusted list and must be trusted explicitly after review.

## 2. Loading with skops

```python
import skops.io as sio

sio.dump(model, "model.skops")

untrusted = sio.get_untrusted_types(file="model.skops")
print(untrusted)                      # [] for a Pipeline of scikit-learn components
model = sio.load("model.skops", trusted=untrusted)    # review the list first
```

- `get_untrusted_types` lists types the loader will not instantiate by default. For a pipeline made of scikit-learn components it returned an empty list in the check run; custom code or unusual types appear by their dotted names.
- In a service, fail closed: refuse to start if the list is non-empty and not in an allow-list file reviewed in code review.
- `sio.dumps(obj)` and `sio.loads(bytes, trusted=...)` work on bytes; `sio.load(path)` without `trusted` raises on any untrusted type.
- skops covers scikit-learn estimators. Models from other libraries need their native format or MLflow flavor.
- MLflow's sklearn flavor stores `model.skops` by default in 3.17.2 and accepts `skops_trusted_types=[...]` in `log_model` for custom types.

## 3. Serving with MLflow

```bash
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
mlflow models serve -m "models:/churn-clf@champion" --env-manager local \
  --host 127.0.0.1 --port 5055 --workers 2

curl -s http://127.0.0.1:5055/invocations -H 'Content-Type: application/json' \
  -d '{"dataframe_split": {"columns": ["f0", "f1"], "data": [[0.1, 0.2]]}}'
```

- Verified endpoints in 3.17.2: `POST /invocations` (returned `{"predictions": [...]}`), `GET /health` (200), `GET /version`.
- Request bodies use one of `dataframe_split`, `dataframe_records`, `instances` or `inputs`; the model signature validates column names and types. Check `mlflow models serve --help` for flags of your version (`-m`, `-p`, `-h`, `-w`, `-t`, `--env-manager`, `--install-mlflow`, `--no-conda`).
- `--env-manager local` uses the current environment (install the model's `requirements.txt` first, and run with the venv's `bin` on `PATH`). The default builds a virtualenv from the model's recorded requirements, which is slower but reproducible. The MLServer backend was removed in MLflow 3.13.
- The built-in server has no authentication, rate limiting or request-size policy. Bind to localhost and put a gateway or service mesh in front, or use a wrapper (section 4).
- `mlflow models build-docker` produces an image for the model; scan and pin the base image (docker-expert). Check the current docs for its flags.
- Test the artifact before promotion: `mlflow.models.predict(model_uri, input_data=...)` in a clean environment.

## 4. FastAPI wrapper

Use your own service when you need authentication, input contracts, custom metrics or pre/post processing. API framework details belong to fastapi-expert.

```python
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
import skops.io as sio
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_PATH = Path("model.skops")
FEATURES = ["f0", "f1", "f2"]
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    untrusted = sio.get_untrusted_types(file=MODEL_PATH)
    if untrusted:
        raise RuntimeError(f"unexpected types in model file: {untrusted}")
    state["model"] = sio.load(MODEL_PATH, trusted=[])
    yield
    state.clear()


app = FastAPI(lifespan=lifespan)


class Row(BaseModel):
    f0: float
    f1: float
    f2: float


class Batch(BaseModel):
    rows: list[Row] = Field(min_length=1, max_length=1000)


@app.post("/predict")
def predict(batch: Batch) -> dict[str, list[float]]:
    X = pd.DataFrame([r.model_dump() for r in batch.rows], columns=FEATURES)
    proba = state["model"].predict_proba(X.to_numpy())[:, 1]
    return {"proba": proba.tolist()}
```

- Load the model once at startup, not per request. A plain `def` endpoint runs in a worker thread, which suits CPU-bound `predict_proba`; do not call blocking inference inside `async def`.
- The Pydantic model is the input contract: types, bounds and batch size are checked before the model sees data; an empty batch returned 422 in the check run. Reject unknown categories or out-of-range values explicitly.
- Keep feature order in one constant shared with training; or pass a DataFrame with the same column names to a pipeline fitted on names.
- Expose `/health` (process up) and `/ready` (model loaded) separately; log model version, request id, latency and a hash or sample of inputs for monitoring, not raw personal data.
- Run with several worker processes for CPU load, each loads its own model copy; size memory accordingly.

## 5. BentoML

- BentoML (1.4.x on PyPI; latest seen 1.4.40) packages a model and service code into a "bento" that builds into a container image, with adaptive batching and a service decorator API. The service API has changed between 1.x minor lines; follow the current docs for `bentoml.Service` and the `@bentoml.service` decorator rather than copying older snippets.
- Choose it over a hand-written FastAPI app when you want batching, a model store and standard build/deploy tooling for many models. Choose a wrapper for one or two simple models.
- The security rules of section 1 apply: do not load untrusted pickles into the model store.

## 6. ONNX export

```python
import numpy as np
import onnxruntime as ort
from skl2onnx import to_onnx

X_sample = X_train[:1].astype(np.float32)
onx = to_onnx(model, X_sample, options={id(model): {"zipmap": False}}, target_opset=17)
sess = ort.InferenceSession(onx.SerializeToString(), providers=["CPUExecutionProvider"])
labels, probas = sess.run(None, {sess.get_inputs()[0].name: X_test.astype(np.float32)})
```

- Check parity: compare `probas[:, 1]` with `model.predict_proba(X_test)[:, 1]` on a few thousand rows (the difference was about 1e-8 in the check run for a scaler plus logistic regression pipeline).
- `zipmap=False` returns probabilities as an array instead of a list of dicts. Inputs are typed (float32 by default); string columns need explicit initial types.
- Not every scikit-learn estimator or custom transformer converts; unsupported ones raise at conversion. XGBoost and LightGBM have their own converters (`onnxmltools`); check the support matrix.
- ONNX Runtime gives smaller images, no Python training dependency and often lower latency; the cost is a conversion step to test in CI. `skl2onnx` 1.20.0 and `onnxruntime` 1.31.1 are the PyPI versions at the time of writing.

## 7. Batch scoring

- For nightly or hourly jobs, load the model by alias at the start of the job, score in chunks (Parquet partitions, `pandas.read_parquet` with filters, or a warehouse job), and write predictions with the model version, input snapshot id and timestamp.
- Make the job idempotent: output keyed by `(entity_id, as_of_date, model_version)` so reruns overwrite rather than duplicate.
- Reuse the training feature code, not a reimplementation; training-serving skew is the largest source of silent accuracy loss.
- Record feature-level null rates and counts per run; a sudden change is the first sign of an upstream break.

## 8. Monitoring and drift

Monitor at four levels: service health (latency, error rate, saturation), data quality (schema, nulls, ranges), input drift and prediction drift, and outcome quality when labels arrive. Metrics export belongs in the platform described by observability-expert.

```python
import numpy as np
from scipy.stats import ks_2samp


def psi(reference, current, bins=10):
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(reference, edges)[0] / len(reference)
    c = np.histogram(current, edges)[0] / len(current)
    r, c = np.clip(r, 1e-6, None), np.clip(c, 1e-6, None)
    return float(np.sum((c - r) * np.log(c / r)))


stat = ks_2samp(reference_col, current_col)     # statistic is the max CDF distance
```

- Reference window: the training data (or a recent stable period), frozen and versioned. Current window: the last day or week of production inputs. Compare each important feature plus the score distribution.
- PSI is a descriptive index; common rules of thumb call below 0.1 small, 0.1 to 0.25 moderate and above 0.25 large, but treat them as starting points and calibrate on your own history. A KS test p-value becomes tiny at large sample sizes even for harmless shifts; prefer the effect size (KS statistic, PSI) with a threshold.
- Categorical features: compare category frequencies (chi-square distance, Jensen-Shannon, or PSI on categories) and track the share of unseen categories.
- Prediction drift often shows up before labels do: watch the mean score, the share above the decision threshold and the score histogram.
- Outcome monitoring: when labels arrive with delay, compute the same metrics as in validation on matured cohorts, by model version, and compare to the validation estimate with its interval. Missing labels for the model's own positive decisions (selection bias) can distort this; keep a small random holdout of decisions if the business can afford it.
- Libraries such as Evidently (0.7.23 on PyPI) generate drift and data-quality reports; their APIs change between 0.x releases, so check the current docs. The core calculations above are small enough to own.
- Alert on sustained breaches over several windows, not single points, and attach a runbook: check upstream pipeline, compare to the reference, decide to retrain, roll back or accept.
- Data drift is not the same as model degradation: inputs can move without hurting accuracy, and concept drift can hurt with stable inputs. Use outcome metrics as the arbiter when available.

## 9. Retraining and rollout

- Retrain on a schedule or on a trigger (drift alarm, metric drop, new labelled volume). Every candidate goes through the same pipeline and the same locked evaluation protocol as the original (see [data-leakage-validation.md](data-leakage-validation.md)).
- Compare the candidate to the champion on the same fresh holdout; promote only if it meets the gate, then move the registry alias (see [experiment-tracking-mlflow.md](experiment-tracking-mlflow.md)).
- Rollout patterns: shadow (score in parallel, do not act), canary (small traffic share), then full. Keep the previous version loadable for rollback by alias.
- Log which model version produced each decision so outcomes can be joined back for evaluation.
- Time-box feedback loops: a model whose decisions shape its future training data (recommendations, approvals) needs exploration traffic or counterfactual logging.

## 10. Feature stores

- A feature store gives one definition of each feature for training (point-in-time correct joins) and serving (low-latency lookup). The value is removing training-serving skew and leakage from as-of joins, and reusing features across teams.
- Open-source Feast and cloud offerings (Vertex AI, SageMaker, Databricks) exist; evaluate them against the cost of operating another system. For one or two models, a shared feature module used by both the training and the scoring job, with snapshot tables, is often enough.
- Requirement either way: features are computed as of the prediction timestamp, with the same code path offline and online, and are versioned with the model.
