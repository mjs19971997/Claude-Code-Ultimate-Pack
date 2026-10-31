# Performance and Memory

Measuring and reducing time and memory in tabular work: dtypes, reading only what is needed, chunking, vectorisation, categoricals, lazy evaluation, predicate pushdown, joins and sorting, and when to change tools. The code blocks run in order in one session (checked with pandas 3.1.0, Polars 2.1.0, DuckDB 2.0.0 and PyArrow 26.0.0 on Python 3.13, 2026-10). No timing figures are quoted: measure on your own data.

## Contents

1. [Measure first](#1-measure-first)
2. [Reading less data](#2-reading-less-data)
3. [Dtypes and memory](#3-dtypes-and-memory)
4. [Vectorise instead of looping](#4-vectorise-instead-of-looping)
5. [Chunked and out-of-core processing](#5-chunked-and-out-of-core-processing)
6. [Lazy evaluation and pushdown](#6-lazy-evaluation-and-pushdown)
7. [Joins, sorts and groupby cost](#7-joins-sorts-and-groupby-cost)
8. [Switching tools](#8-switching-tools)
9. [Benchmarking hygiene](#9-benchmarking-hygiene)

## 1. Measure first

```python
import pathlib
import tempfile
import time

import duckdb
import numpy as np
import pandas as pd
import polars as pl

workdir = pathlib.Path(tempfile.mkdtemp())
n = 200_000
rng = np.random.default_rng(0)
df = pd.DataFrame(
    {
        "id": np.arange(n),
        "k": rng.choice(["aa", "bb", "cc"], n),
        "v": rng.random(n),
        "ts": pd.date_range("2026-01-01", periods=n, freq="s"),
    }
)
df.to_csv(workdir / "x.csv", index=False)
df.to_parquet(workdir / "x.parquet", compression="zstd")

print(df.memory_usage(deep=True).to_dict())      # bytes per column, including string payloads
print(df.dtypes.to_dict())
print(pl.from_pandas(df).estimated_size("mb") > 0)
```

- Memory: `df.memory_usage(deep=True)` (pandas), `df.estimated_size("mb")` (Polars), `tracemalloc` or process RSS for the whole program. `df.info(memory_usage="deep")` summarises a pandas frame.
- Time: `time.perf_counter()` around a block, `%timeit` in notebooks, `cProfile` for Python-level hot spots. For query engines read the plan: `lf.explain()` (Polars), `EXPLAIN ANALYZE` (DuckDB).
- Find the cost centre before changing code: reading, parsing, joining, grouping, Python-level `apply`, or writing. Optimise the largest one, then measure again.
- Compare results as well as time: an optimisation that changes the output is a bug. Keep a small frame and `assert_frame_equal` (pandas.testing or polars.testing) in a test.

## 2. Reading less data

```python
small = pd.read_csv(
    workdir / "x.csv",
    usecols=["k", "v", "ts"],
    dtype={"k": "category", "v": "float32"},
    parse_dates=["ts"],
)
print(small.dtypes.to_dict())

pq_part = pd.read_parquet(workdir / "x.parquet", columns=["k", "v"], filters=[("k", "==", "aa")])
print(pq_part.shape, (pq_part["k"] == "aa").all())
```

- Choose columns at read time (`usecols`, `columns=`, `SELECT col1, col2`). Parquet is columnar, so skipped columns are not read at all; CSV must still be scanned and tokenized.
- Pass `dtype=` to `read_csv` instead of letting pandas infer and then convert; set `parse_dates` for known date columns. Wrong inference on mixed columns is a common source of `object` or `str` columns that should be numeric.
- Push row filters into the reader: `filters=` in `pd.read_parquet`, `.filter()` after `pl.scan_parquet`, or `WHERE` in DuckDB. Predicate pushdown uses row-group statistics, so it works best on sorted or partitioned columns.
- Convert CSV to Parquet once and query Parquet afterwards. Parquet stores types, compresses well and supports column and row-group pruning.
- pandas 3.1 reads large local uncompressed CSV files in parallel by default (controlled by the `mode.max_threads` option, per the 3.1 notes); `engine="pyarrow"` is another fast path for simple files.
- Sample before scaling: `nrows=`, `n_rows=`, `LIMIT` while developing, but remove them before a full run.

## 3. Dtypes and memory

- Numeric downcasting: `float32` halves float memory; `pd.to_numeric(s, downcast="integer")` picks the smallest integer type. Do not downcast values that feed accumulations where precision matters (money, sums over millions of rows).
- Repeated strings: `category` (pandas), `pl.Categorical` or `pl.Enum` (Polars), dictionary encoding (Arrow, Parquet) store each distinct value once.

```python
s = df["k"]
c = df["k"].astype("category")
print(s.memory_usage(deep=True), c.memory_usage(deep=True))     # the category column is much smaller
print(c.groupby(c, observed=True).size().to_dict())
```

- With a categorical grouping key pass `observed=True`; otherwise pandas builds every category combination.
- Booleans as `bool`, flags as small integers, and dates as datetimes rather than strings. Use nullable or Arrow dtypes only where missing values require them: they cost extra memory or speed in some operations; test.
- pandas 3 stores text as `str` (PyArrow-backed when PyArrow is installed), which is already more compact than Python objects; still use categories for low-cardinality text that is grouped or joined often.
- Drop columns early and drop intermediate frames you no longer need (`del tmp`).
- Avoid wide object-style columns (lists, dicts, Python objects) in large frames; they defeat vectorisation and compression. Normalise them into rows or Arrow lists and structs.

## 4. Vectorise instead of looping

```python
t0 = time.perf_counter()
slow = df["v"].apply(lambda x: x * 2)
t_apply = time.perf_counter() - t0
t0 = time.perf_counter()
fast = df["v"] * 2
t_vec = time.perf_counter() - t0
print(slow.equals(fast), t_apply > t_vec)

bucket = np.select([df["v"] < 0.3, df["v"] < 0.6], ["lo", "mid"], default="hi")
print(pd.Series(bucket).value_counts().to_dict())
```

- `iterrows`, `itertuples`, `apply(axis=1)` and `map_elements` run Python per row. Replace them with column arithmetic, `np.where`/`np.select`, `Series.where`, `str` and `dt` accessors, `merge` against a lookup table, or `cut`/`searchsorted`.
- Use `transform` and `agg` with built-in function names (`"sum"`, `"mean"`, `"first"`), which have fast paths, instead of `apply(lambda g: ...)`.
- In Polars write the logic as expressions (`pl.when`, `over`, `list` and `str` namespaces); a user-defined function breaks parallelism and optimisation.
- If a loop is unavoidable, loop over groups or files, not rows, and keep per-iteration work vectorised. Collect results in a list and combine once with `concat`.
- For numeric hot loops that cannot be expressed in the library, move that part to NumPy or a compiled tool (see scientific-python-expert); keep the frame logic in the dataframe library.

## 5. Chunked and out-of-core processing

```python
total = 0.0
for chunk in pd.read_csv(workdir / "x.csv", usecols=["v"], chunksize=50_000):
    total += chunk["v"].sum()
print(abs(total - df["v"].sum()) < 1e-6)

q = (
    pl.scan_csv(workdir / "x.csv", schema_overrides={"k": pl.Categorical})
    .group_by("k")
    .agg(pl.col("v").mean())
    .sort("k")
)
print(q.collect(engine="streaming").shape)

print(duckdb.sql(f"SELECT k, avg(v) AS mean_v FROM read_csv('{(workdir / 'x.csv').as_posix()}') GROUP BY k ORDER BY k").df().shape)
```

- pandas `chunksize` keeps memory flat for aggregations that combine incrementally (sums, counts, min/max); means need sum and count; medians and distinct counts do not combine by chunk.
- Polars `collect(engine="streaming")` and `sink_parquet` process data in batches, and DuckDB spills to disk when `memory_limit` is reached. These are usually simpler than hand-written chunk loops.
- Partitioned Parquet lets a job process one partition at a time and makes reruns of a single day cheap.
- Writing: stream large outputs with `sink_parquet` (Polars), `COPY ... TO` (DuckDB) or `pq.ParquetWriter` (PyArrow) rather than building one huge frame.
- If the data fits on disk but not in memory, prefer Polars streaming or DuckDB over a cluster; reach for a distributed engine only when one machine is not enough.

## 6. Lazy evaluation and pushdown

- Lazy engines plan the whole query first. Projection pushdown reads only used columns; predicate pushdown filters at the scan; common sub-expression elimination avoids repeated work.
- Keep filters and column selections in the same lazy chain as the scan. Calling `.collect()` and then filtering throws the benefit away.
- Check the plan: Polars `lf.explain()` shows `PROJECT n/m COLUMNS` and `SELECTION` on the scan; DuckDB `EXPLAIN` shows projections and filters on the Parquet scan node.
- pandas is eager: every step materialises a result. Reduce columns and rows first, then compute, and filter with `loc` masks or `pd.col` expressions.
- Cache an expensive lazy intermediate that is reused by calling `collect()` once and building later queries from `.lazy()` on the result.

## 7. Joins, sorts and groupby cost

- Reduce both sides before joining: select needed columns and filter rows. Join keys should be the same dtype; join on integers or categoricals rather than long strings when you can.
- Check key uniqueness with `validate=` so a duplicate key cannot explode the row count and memory.
- Joining a small lookup table to a large one is cheap in all three engines; avoid cross joins and range joins on large inputs unless the engine has a dedicated operator (`merge_asof`, `join_asof`, `ASOF JOIN`).
- Sorting is expensive. Sort once, at the end or on the minimum columns, and use `nlargest`/`top_k`/`ORDER BY ... LIMIT` instead of a full sort for top-N.
- Group by integer or categorical keys when you can. High-cardinality string keys cost more memory and time.
- `drop_duplicates`, `unique` and `nunique` are hash-based; for huge data compute them in DuckDB or Polars streaming rather than pandas.
- Repeated `concat` or `append` in a loop copies the data each time; collect pieces and concatenate once.

## 8. Switching tools

| Symptom | Try |
|---|---|
| pandas job runs out of memory on a CSV or Parquet file | `pl.scan_*` with streaming, or DuckDB over the files |
| Group-bys or joins are slow on tens of millions of rows | Polars or DuckDB (multithreaded, vectorised); compare on your data |
| Many Parquet files, ad hoc SQL, no pipeline code | DuckDB `read_parquet` with a glob |
| A library needs a DataFrame (plotting, scikit-learn) | Do heavy work in Polars or DuckDB, then convert the result to pandas or NumPy |
| Code is already clear and fast enough | Leave it alone; switching costs more than it saves |

- Convert once at a boundary through Arrow (`pl.from_pandas`, `df.to_pandas()`, `.arrow()`), not repeatedly inside loops.
- A rewrite must have an equality test against the old output on a sample.

## 9. Benchmarking hygiene

- Use the same data, the same output and warm caches for each variant; run several repetitions and report the median.
- Include read and write time if production does; a faster engine that reads CSV slowly may lose overall.
- Test with realistic cardinality and skew, not only random uniform keys.
- Record library versions and hardware with the result; behaviour and defaults change between releases (for example the pandas 3 string dtype and the Polars 2 default engine).
- Do not trust blog numbers for your workload; treat them as a hypothesis to test.
