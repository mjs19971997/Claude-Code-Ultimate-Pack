# pandas 3 Patterns

pandas 3.0 and 3.1 behaviour that changes how code is written: Copy-on-Write, the `str` dtype, datetime resolution, `pd.col`, joins with `validate=`, groupby, window and time series work, missing data and reshaping. The code blocks run in order in one session (checked with pandas 3.1.0 on Python 3.13, 2026-10).

## Contents

1. [What changed in pandas 3](#1-what-changed-in-pandas-3)
2. [Copy-on-Write and chained assignment](#2-copy-on-write-and-chained-assignment)
3. [Dtypes and missing data](#3-dtypes-and-missing-data)
4. [Column expressions with pd.col](#4-column-expressions-with-pdcol)
5. [Joins and merges](#5-joins-and-merges)
6. [Reshaping](#6-reshaping)
7. [GroupBy and window calculations](#7-groupby-and-window-calculations)
8. [Time series](#8-time-series)
9. [Upgrading from pandas 2](#9-upgrading-from-pandas-2)

## 1. What changed in pandas 3

The 3.0 release notes list these main changes; 3.1 adds `DataFrame.select`, a `cond=` mask on `filter`, and a faster, parallel `read_csv` for large local files (see the 3.1 notes).

| Area | pandas 3 behaviour |
|---|---|
| Python and NumPy | Python 3.11 or newer; NumPy 1.26 or newer for 3.0, NumPy 2.0.2 or newer for 3.1 |
| Copy-on-Write | Always on. Any result of indexing or a method behaves as a copy; pandas still uses views internally to avoid copies. The `mode.copy_on_write` option has no effect and is deprecated for removal in pandas 4.0 |
| Strings | String columns are inferred as the dedicated `str` dtype instead of `object`. It uses PyArrow when installed and a NumPy object fallback otherwise. It holds only strings or missing values, and the missing marker is `NaN` |
| Datetimes | The resolution is inferred, not fixed at nanoseconds. Strings give microseconds unless they carry nanoseconds, so many columns are `datetime64[us]`. `astype("int64")` on such a column returns integers 1000 times smaller than before; use `as_unit` to choose a unit explicitly |
| pytz | No longer a required dependency; install it or `pandas[timezone]` if the code needs it |
| Expressions | `pd.col()` builds column expressions without `lambda` |
| Arrow interchange | `DataFrame` and `Series` export and import through the Arrow PyCapsule interface; `from_arrow` constructors exist |

## 2. Copy-on-Write and chained assignment

```python
import io
import numpy as np
import pandas as pd

df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

col = df["a"]
col.iloc[0] = 100          # modifies only `col`; df is unchanged
assert df["a"].tolist() == [1, 2, 3]

df.loc[df["a"] > 1, "b"] = 0           # one-step assignment: this is the supported form
assert df["b"].tolist() == [4, 0, 0]
```

- Chained assignment such as `df["a"][0] = 99` or `df[df.a > 1]["b"] = 0` never updates `df`. In 3.1.0 it emits a `ChainedAssignmentError` warning; do not rely on it being caught. Use `df.loc[rows, col] = value`.
- `SettingWithCopyWarning` is gone, and so is the need for defensive `.copy()` calls. Keep `.copy()` only when you want an independent object that outlives its parent for clarity.
- A function that receives a DataFrame and assigns into it no longer mutates the caller's frame through a view. If a caller depends on in-place mutation, return the new frame instead.
- `inplace=True` rarely saves memory under Copy-on-Write; prefer assigning the result.
- Do not set `pd.options.mode.copy_on_write` in new code; it has no effect.

## 3. Dtypes and missing data

```python
s = pd.Series(["x", None, "z"])
print(s.dtype)                   # str
print(s.isna().tolist())         # [False, True, False]; the marker is NaN

raw = "a,b\n1,x\n,y\n"
nullable = pd.read_csv(io.StringIO(raw), dtype_backend="numpy_nullable")
print(nullable.dtypes.to_dict())   # a: Int64, b: string
arrow = pd.read_csv(io.StringIO(raw), dtype_backend="pyarrow")
print(arrow.dtypes.to_dict())      # a: int64[pyarrow], b: string[pyarrow]
```

- Default NumPy-backed `int64` and `float64` columns turn into `float64` with `NaN` when a missing value appears. Use nullable dtypes (`Int64`, `Float64`, `boolean`, `string`) or `dtype_backend="pyarrow"` when integer columns must stay integers with true missing values.
- The `str` dtype means `.str` methods return `NaN` for missing entries, and comparisons with `NaN` are False. To keep `pd.NA` semantics use `dtype="string"` explicitly.
- Replace `dtype=object` string checks (`df.dtypes == object`) with `pd.api.types.is_string_dtype` or `select_dtypes(include="str")`. In 3.1 `select_dtypes` is stricter and raises for several loose specifications, so test selections after upgrading.
- `df.convert_dtypes()` upgrades a frame to nullable dtypes in one call; check the result column by column on messy input.
- Parse numbers explicitly: `pd.to_numeric(s, errors="coerce")` turns bad values into missing; count them afterwards (`s.isna().sum()`) rather than discarding silently.
- Decide per column whether missing means "unknown", "not applicable" or "zero". `fillna` encodes an assumption; keep a mask column when the distinction matters.
- Report with `df.isna().sum()` and `df.isna().mean()` before choosing `dropna(subset=...)`, `fillna`, `ffill()` for ordered data, or leaving the gaps.

## 4. Column expressions with pd.col

```python
out = df.assign(total=pd.col("a") + pd.col("b"))
rows = df.loc[pd.col("a") > 1]
print(out.shape, rows.shape)

picked = df.select("a", doubled=pd.col("a") * 2)    # DataFrame.select: pandas 3.1
masked = df.filter(cond=pd.col("a") > 1)            # cond= mask: pandas 3.1
print(picked.columns.tolist(), masked.shape)
```

- `pd.col("a")` is evaluated against the frame at the point it is used, so it replaces `lambda d: d["a"]` in `assign`, `loc` and getitem.
- `DataFrame.select` and `filter(cond=...)` need pandas 3.1 or newer. If the project supports 3.0, use `assign` plus `loc`.
- `DataFrame.query("a > 1 and b >= 0")` still works and reads well for simple filters; avoid interpolating untrusted text into the query string.
- Chain with `.pipe(func, ...)` and `.assign(...)` rather than reassigning one name many times; the pipeline reads top to bottom and each step can be tested.

## 5. Joins and merges

```python
users = pd.DataFrame({"id": [1, 2, 2], "name": ["a", "b", "c"]})
orders = pd.DataFrame({"id": [1, 2], "amt": [10, 20]})

try:
    users.merge(orders, on="id", validate="1:1")
except pd.errors.MergeError as err:
    print("rejected:", str(err).splitlines()[0])

joined = users.merge(orders, on="id", how="left", validate="m:1", indicator=True)
print(joined["_merge"].value_counts().to_dict())
```

- Always pass `validate=` (`"1:1"`, `"1:m"`, `"m:1"`, `"m:m"`) when you know the key cardinality. A duplicated key on the "one" side silently multiplies rows otherwise.
- `indicator=True` adds a `_merge` column (`both`, `left_only`, `right_only`) to test coverage; assert on it in pipelines that must not lose rows.
- Compare row counts and the sum of an additive measure before and after a join; both should match the expected cardinality.
- Keys with different dtypes (`int64` against `str`, or `Int64` against `float64`) can fail or silently not match. Cast first and check `df["id"].dtype`.
- Missing keys: pandas matches `NaN` to `NaN` in merge keys, which SQL and Polars do not by default. Drop or fill null keys before joining.
- Use `merge_asof` for nearest-time matches on sorted keys:

```python
trades = pd.DataFrame({"t": pd.to_datetime(["2026-01-01 10:00:01", "2026-01-01 10:00:05"]), "px": [1, 2]})
quotes = pd.DataFrame({"t": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-01 10:00:04"]), "bid": [9, 8]})
print(pd.merge_asof(trades, quotes, on="t", tolerance=pd.Timedelta("3s")))
```

- `pd.concat([...], ignore_index=True)` stacks frames; pass `verify_integrity=True` only when the index must stay unique. Never concatenate in a loop; collect the pieces in a list and call `concat` once.

## 6. Reshaping

```python
wide = pd.DataFrame({"id": [1, 2], "q1": [5, 6], "q2": [7, 8]})
long = wide.melt(id_vars="id", var_name="quarter", value_name="sales")
back = long.pivot(index="id", columns="quarter", values="sales")
agg = long.pivot_table(index="id", columns="quarter", values="sales", aggfunc="sum")
print(long.shape, back.shape, agg.shape)
```

- Tidy data: one variable per column, one observation per row, one table per observational unit. `melt` goes wide to long; `pivot` goes back and fails on duplicate index and column pairs; `pivot_table` aggregates instead.
- `pd.wide_to_long(df, stubnames, i=..., j=...)` handles `x1`, `x2` style column families.
- `explode` turns a list column into rows; `str.split(",")` followed by `explode` splits delimited text.
- `stack` and `unstack` move column levels to the index and back; prefer `melt` and `pivot` for readability.
- Keep the long form for grouping and plotting libraries; use wide only for presentation or matrix operations.

## 7. GroupBy and window calculations

```python
sales = pd.DataFrame({"region": list("aabb"), "item": list("xyxy"), "amt": [1, 2, 3, 4]})

summary = sales.groupby("region", as_index=False).agg(total=("amt", "sum"), n=("amt", "size"))
sales["share"] = sales["amt"] / sales.groupby("region")["amt"].transform("sum")
sales["rank"] = sales.groupby("region")["amt"].rank(method="dense", ascending=False)
print(summary.shape, sales["share"].round(2).tolist())
```

- Named aggregation (`agg(total=("amt", "sum"))`) gives flat, readable column names and avoids a MultiIndex.
- `transform` returns a result aligned to the original rows (shares, z-scores within group); `agg` returns one row per group; `apply` is the slow general fallback.
- Grouping by a `category` column includes unobserved categories unless `observed=True` is passed; set it explicitly.
- `groupby(..., dropna=False)` keeps missing keys as a group; the default drops them.
- `size()` counts rows, `count()` counts non-missing values. Mixing them up changes results when columns contain missing data.
- Group-wise rolling: `df.groupby("k")["v"].rolling(3, min_periods=1).mean()` returns a MultiIndex result; `transform(lambda s: s.rolling(3, min_periods=1).mean())` keeps the original index.
- Sort before positional operations (`shift`, `diff`, `cumsum`, `rolling`): they follow row order, not time.

## 8. Time series

```python
ts = pd.DataFrame(
    {"ts": pd.date_range("2026-01-01", periods=6, freq="12h", tz="UTC"), "v": range(6)}
).set_index("ts")

daily = ts.resample("1D").agg({"v": ["sum", "mean"]})
rolling = ts["v"].rolling("1D").mean()      # time-based window needs a sorted DatetimeIndex
print(daily.shape, rolling.round(1).tolist())
```

- Store timestamps in UTC with a timezone (`tz="UTC"`), convert for display with `tz_convert`. Naive timestamps hide daylight-saving errors.
- `resample` needs a datetime-like index (or `on="col"`); choose `closed` and `label` explicitly when bin edges matter, and fill empty bins on purpose (`asfreq`, `ffill`, `interpolate`).
- Use the current frequency aliases: in 3.1.0 `"H"` and `"M"` raise `ValueError`; write `"h"` for hours and `"ME"` for month end.
- Because resolution is inferred in pandas 3, do not assume nanoseconds: use `ts.dt.as_unit("ns")` when mixing with data that requires it, and avoid `astype("int64")` for epoch maths.
- Use `pd.Timestamp`/`pd.Timedelta` arithmetic and `dt` accessors, not Python loops over rows.

## 9. Upgrading from pandas 2

1. Upgrade to pandas 2.3 first and fix every deprecation warning; the 3.0 notes recommend this step.
2. Run the test suite with warnings as errors on pandas 3 and look for: chained assignment, `object` dtype assumptions for strings, nanosecond-based integer maths, `select_dtypes` specifications, and code that relied on `inplace` or views.
3. Remove `pd.options.mode.copy_on_write = True` and `future.infer_string` settings; they are deprecated and have no effect.
4. If a dependency (a plotting or ML library) fails on the `str` dtype, convert at the boundary with `df.astype({"col": object})` or `df.to_numpy(dtype=object)` rather than disabling the new dtype globally.
5. Validate shapes and dtypes after the upgrade with a schema (see the SKILL.md validation section).
