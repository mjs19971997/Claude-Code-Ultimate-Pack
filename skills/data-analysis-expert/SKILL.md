---
name: data-analysis-expert
description: >-
  Analyses and reshapes tabular data with pandas 3, Polars 2 and DuckDB, using Arrow and Parquet as storage and interchange: joins, groupby, window functions, time series, missing data, dtypes, memory and performance. Use when editing code that imports pandas, polars, duckdb or pyarrow, reading .parquet, .csv or .arrow files, writing SQL over files, fixing slow or out-of-memory pipelines, or choosing between the three engines. Not for hypothesis tests or inference (use statistics-expert), model training (use ml-engineering-expert), NumPy, SciPy or plotting (use scientific-python-expert), or database servers (use postgresql-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Data Analysis Expert

This skill covers working with tabular data in Python: loading, cleaning, reshaping, joining, aggregating and writing it with pandas, Polars and DuckDB, using Apache Arrow and Parquet as the common format. It focuses on correct results first (join cardinality, missing values, dtypes, time zones) and then on speed and memory. Statistical testing, model pipelines, numerical computing and plotting, and database administration belong to other skills.

> Verified against pandas 3.1.0 (3.0 and 3.1 release notes), Polars 2.1.0 (2.0.0 release notes), DuckDB 2.0.0, PyArrow 26.0.0 and pandera 0.35.0, current on PyPI in 2026-10; all code blocks in this skill and its references were run on Python 3.13 with these versions (2026-10).

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

- Covered: pandas 3 (Copy-on-Write, `str` dtype, `pd.col`), Polars 2 (expressions, lazy API, `scan_*`, streaming engine), DuckDB (SQL on files and DataFrames, Python and relational APIs), PyArrow as interchange, Parquet layout and partitioning, tidy data, reshaping, joins and their cardinality pitfalls, groupby and window functions, time series, missing data, dtypes and memory, performance work, notebooks versus scripts, brief data validation with pandera, and choosing between the engines.
- Not covered: statistical tests, confidence intervals, regression inference (statistics-expert); feature engineering for models, training, experiment tracking (ml-engineering-expert); NumPy and SciPy numerics, Matplotlib and other plotting (scientific-python-expert); running and tuning PostgreSQL (postgresql-expert); Python language, packaging and typing in general (python-expert); Spark and other distributed engines (check their own documentation).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| pandas 3.x | Requires Python 3.11+. Copy-on-Write is always on: indexing results and method results behave as copies, chained assignment never updates the original, `SettingWithCopyWarning` is gone. The `mode.copy_on_write` option has no effect (deprecated for removal in pandas 4.0) |
| pandas strings and times | Text columns infer the `str` dtype (PyArrow-backed when PyArrow is installed; missing marker is `NaN`). Datetime resolution is inferred (often `datetime64[us]`), so integer epoch maths that assumed nanoseconds breaks; use `as_unit`. `pd.col("a")` builds column expressions; 3.1 adds `DataFrame.select`, `filter(cond=...)` and faster parallel `read_csv` |
| Polars 2.x | Expression API in contexts (`select`, `with_columns`, `filter`, `group_by().agg`). `LazyFrame` plus `scan_parquet`, `scan_csv`, `sink_parquet`. `collect(engine=...)` takes `"auto"`, `"in-memory"`, `"streaming"`, `"gpu"`; in 2.1.0 `"auto"` falls back to `"streaming"` unless engine affinity is configured. `unpivot` (wide to long), `pivot`, `over` for windows, `join(..., validate=)` |
| DuckDB 2.x | In-process analytical SQL. `duckdb.sql(...)` returns a lazy relation on the default connection and sees local DataFrames by variable name; results via `.df()`, `.pl()`, `.arrow()`, `.fetchall()`. Reads and writes Parquet, CSV and JSON directly; `COPY ... TO ... (FORMAT parquet, PARTITION_BY (...))`; `QUALIFY`, `GROUP BY ALL`, `PIVOT`, `UNPIVOT`, `ASOF JOIN`; spills to disk beyond `memory_limit` |
| Arrow and Parquet | Arrow is the columnar in-memory format shared by the three libraries; Parquet is the columnar on-disk format with compression, column pruning and row-group statistics. PyArrow adds `pyarrow.dataset` (lazy multi-file scans) and `pyarrow.parquet` |
| Tidy data | One variable per column, one observation per row, one table per observational unit. Long form for grouping and plotting; wide form for display |
| Joins | Check key uniqueness and dtype. pandas: `merge(validate="m:1", indicator=True)`; Polars: `join(validate="m:1")`; SQL: count rows before and after. Null keys: pandas matches `NaN` to `NaN`, Polars and SQL do not by default |
| Validation | pandera (0.35) validates pandas and Polars frames through `pandera.pandas` and `pandera.polars`: schemas, checks, `lazy=True` to collect all failures |
| Tool choice | pandas for small to medium in-memory work and the widest library ecosystem; Polars for fast, memory-aware pipelines in Python; DuckDB for SQL, ad hoc queries over many files and larger-than-memory aggregation |

## 3. Workflow

1. Look at the data before writing code: row and column counts, dtypes, missing values, key uniqueness, value ranges, time zones. Use `df.info()` and `df.describe()` (pandas), `df.glimpse()` and `df.describe()` (Polars) or `SUMMARIZE` and `DESCRIBE` (DuckDB).
2. Identify the grain of each table (what one row represents) and the join keys between tables. Write the expected cardinality of every join (`1:1`, `m:1`, `1:m`).
3. Read the project's existing stack (requirements, `pyproject.toml`, imports) and keep to it. Do not introduce a second dataframe library for one function; convert at a boundary through Arrow if needed.
4. Load only the columns and rows required. Prefer Parquet over CSV for anything reused; set dtypes explicitly when reading CSV.
5. Build the pipeline as a sequence of named steps (functions, or a chained expression or SQL with CTEs). Assert invariants between steps: row counts, key uniqueness, no unexpected nulls.
6. Run on a sample, compare with a manual calculation on a handful of rows, then run on the full data.
7. Profile before optimising; see [references/performance-and-memory.md](references/performance-and-memory.md).
8. Write results in a typed, self-describing format (Parquet) with documented schema, and keep the script or notebook that produced them reproducible.

## 4. Decision Rules

- If the data fits comfortably in memory, the team knows pandas and a library requires pandas objects, use pandas 3; do not rewrite working code for speed alone.
- If a pandas job is slow or runs out of memory, or you are building a new pipeline, use Polars lazy (`scan_*`, expressions, `collect(engine="streaming")`) or DuckDB, and compare on a sample.
- If the work is naturally SQL (joins of many tables, window functions, ad hoc questions over a folder of Parquet files), use DuckDB; if the work is a chain of column transformations in Python, use Polars or pandas.
- If data is larger than RAM but fits on disk, use Polars streaming or DuckDB with `memory_limit` and `temp_directory` before considering a cluster.
- If you hand data between libraries, go through Arrow (`pl.from_pandas`, `df.to_pandas()`, DuckDB `.arrow()` or `.pl()`), once, at a boundary.
- If a join key should be unique on one side, state it with `validate=` (pandas, Polars) or an assertion; if it fails, fix the data, do not deduplicate blindly.
- If text has few distinct values and is grouped or joined often, use `category` (pandas), `pl.Enum` or `pl.Categorical`, or dictionary-encoded Arrow.
- If integers must survive missing values, use nullable dtypes (`Int64`, `dtype_backend="pyarrow"`) in pandas; Polars keeps integer dtypes with nulls by default.
- If you reuse data across runs, store it as partitioned Parquet; partition by low-cardinality columns that queries filter on, never by an id.
- If rows are being processed with `apply(axis=1)`, `iterrows` or `map_elements`, look for a vectorised or expression form first.
- If the task is exploratory, a notebook is fine; once it is repeated or shared, move the logic into a script or package with functions and tests, and keep the notebook as a thin front end.
- If a task needs a statistical test, model or plot, finish the data preparation here and hand over a tidy frame to the relevant skill.

## 5. Coding Standards

- Name frames for what they hold (`orders`, `daily_revenue`), not `df2`. Name columns in `snake_case`, with units where useful (`amount_eur`, `duration_s`).
- Prefer method chaining or a short sequence of named steps over many reassignments of one variable. In pandas use `.assign(...)`, `.pipe(...)`, `.loc[...]` and `pd.col`; in Polars use `with_columns`, `filter`, `group_by`; in SQL use CTEs.
- Never assign through chained indexing (`df["a"][0] = 1`). Use `df.loc[rows, "a"] = 1`.
- Avoid `inplace=True`; assign the result. Avoid `df.apply(axis=1)`, `iterrows()` and Python loops over rows for logic that has a column form.
- Select columns explicitly when reading and before joining; do not carry unused columns.
- Set dtypes deliberately: parse dates, use categories for repeated text, use nullable or Arrow-backed dtypes where missing integers matter.
- Keep timestamps timezone-aware in UTC and convert for display. Do not mix naive and aware values.
- Name join keys and state the cardinality: `validate="m:1"`. Name aggregations (`agg(total=("amt", "sum"))`).
- Keep SQL strings readable: one clause per line, CTEs for steps, `?` or `$name` parameters for values.
- Put reusable steps in functions that take and return frames, with type hints (`pd.DataFrame`, `pl.LazyFrame`). Do not mutate arguments.
- Do not use bare `except` around frame operations to hide failures; validate the data instead.

## 6. Project Structure

```text
analysis-project/
|-- pyproject.toml            # dependencies pinned through a lockfile
|-- data/
|   |-- raw/                  # immutable inputs, never edited by code
|   |-- interim/              # intermediate Parquet
|   `-- processed/            # final tables, partitioned Parquet
|-- notebooks/                # exploration; thin, restart-and-run-all clean
|-- src/analysis/
|   |-- load.py               # readers with explicit schemas
|   |-- transform.py          # pure functions: frame in, frame out
|   |-- schemas.py            # pandera schemas or dtype maps
|   `-- pipeline.py           # entry point: load -> transform -> validate -> write
`-- tests/
    |-- test_transform.py     # small fixture frames, assert_frame_equal
    `-- conftest.py
```

- Keep raw data read-only and out of version control when it is large or sensitive; commit a small sample fixture for tests.
- Make the pipeline runnable end to end with one command, with input and output paths as arguments or configuration.
- Notebooks hold exploration and reporting; code that is reused moves into `src/`. A notebook must run top to bottom after a kernel restart. Strip outputs or use a notebook-to-script tool before committing, according to team practice.

## 7. Design Patterns

- **Pure transform functions**: each step takes a frame and returns a frame, so it can be unit-tested with a ten-row fixture and chained with `.pipe`. Cost: more small functions.
- **Lazy pipeline**: in Polars, build one `LazyFrame` from `scan_*` to the final `collect` or `sink_*`; the optimizer prunes columns and rows. Cost: errors surface at `collect`, so test with a small sample.
- **SQL as the transformation layer**: DuckDB queries over Parquet, with CTEs per step, are easy to review and run without loading the data into Python. Cost: logic splits between SQL and Python.
- **Staged files**: write interim results as Parquet so a failed step can restart from the last good stage. Cost: storage and a schema to maintain.
- **Dimension lookups by join**: replace `map` or `apply` with a join to a small table (`m:1`), which is vectorised and auditable.
- **Window instead of self-join**: group-wise totals, ranks and lags use `transform`/`over`/SQL window functions, not a join back to an aggregate.
- **Schema at the boundary**: validate data on read and before write (pandera, or explicit dtype maps and asserts); trust it inside.
- **Long form storage, wide form presentation**: store tidy data; pivot only for the final report.

## 8. Best Practices

- Define the grain of every table and check it: `df.duplicated(subset=keys).sum() == 0`, or `SELECT keys, count(*) ... HAVING count(*) > 1`.
- Check joins: row count before and after, count of unmatched keys (`indicator=True`, anti join), and the sum of an additive column.
- Treat missing data as information: count it per column, decide per column whether it means unknown, not applicable or zero, and document the choice. Do not `fillna(0)` by default.
- Be explicit about time: time zone, resolution, the bin edges of resamples (`closed`, `label`), and week or fiscal-year definitions.
- Be explicit about floating-point and money: store money as integer minor units or decimals; compare floats with a tolerance.
- Sort before positional operations (`shift`, `diff`, `cumsum`, rolling windows, `first`/`last`); group order and join order are not guaranteed.
- Prefer deterministic outputs: sort final tables by key, fix random seeds for sampling, and stamp outputs with the code version and input snapshot.
- Keep a data dictionary (column, type, unit, meaning, allowed values) next to the processed tables.
- Do exploratory work on a sample, but state when numbers come from a sample.
- Record library versions (lockfile); defaults changed across pandas 3 and Polars 2, and results can differ.

## 9. Performance

- Measure first (`time.perf_counter`, `%timeit`, `lf.explain()`, `EXPLAIN ANALYZE`, `df.memory_usage(deep=True)`), then change the largest cost. Details in [references/performance-and-memory.md](references/performance-and-memory.md).
- Read less: `usecols`/`columns=`, Parquet over CSV, filters pushed to the scan, partitions that match common filters.
- Use the right dtype: categories for repeated text, `float32` and small integers where precision allows, datetimes instead of strings.
- Vectorise: column arithmetic, `np.where`/`np.select`, `pl.when`, joins to lookup tables. Remove `apply(axis=1)`, `iterrows` and `map_elements`.
- Stay lazy in Polars until the final result; check the plan for projection and predicate pushdown.
- For larger-than-memory work, use Polars streaming, DuckDB with `memory_limit` and `temp_directory`, or chunked reading.
- Reduce both sides before a join, sort once at the end, use top-N instead of full sorts, and concatenate once.
- Do not optimise code that runs once in seconds; spend effort where a pipeline runs repeatedly or fails on size.

## 10. Security

- Parameterise SQL values (`con.execute("... WHERE region = ?", [region])`); identifiers and file paths cannot be bound, so check them against an allow-list. Do not build `DataFrame.query`, `eval` or SQL strings from untrusted text.
- Never call `pd.read_pickle` (or unpickle in any form) on data you did not produce; pickle can execute code. Use Parquet, Arrow IPC, CSV or JSON for exchange.
- Be careful with file and URL readers on untrusted input: path traversal in user-supplied file names, DuckDB's file and network access (see its `enable_external_access` and `lock_configuration` settings), and archive bombs. Resolve paths against a base directory.
- Cloud credentials for S3, GCS or Azure come from the environment, a credential provider or DuckDB secrets, never from source code or notebooks. Clear notebook outputs that show tokens or personal data.
- Treat personal data deliberately: drop or hash identifiers you do not need, avoid putting raw rows in logs or error messages, and restrict access to processed files.
- When exporting CSV for spreadsheet users, text cells that start with `=`, `+`, `-` or `@` can be interpreted as formulas; sanitise or prefix them for untrusted data.
- Pin dependencies with a lockfile and audit them in CI; data libraries load native code and parse untrusted binary formats.

## 11. Testing

- Test transforms with small, hand-built frames that cover the edge cases: empty input, duplicate keys, nulls, ties, time-zone boundaries, a single group.
- Compare frames with the library helpers: `pandas.testing.assert_frame_equal` and `polars.testing.assert_frame_equal`, setting `check_dtype`, `check_exact` or tolerances deliberately. Sort both sides when order is not part of the contract.
- Assert invariants in tests and in the pipeline: unique keys, row counts after joins, totals preserved by reshaping (`melt` then `pivot` returns the original), no new nulls.
- Use pandera schemas (or the library's schema) on pipeline inputs and outputs. Use `lazy=True` to report all failures at once.
- Run the same fixture through each engine if a pipeline exists in two forms and assert equal results.
- Fix random seeds; do not depend on the current date or on the default order of group-by results.
- Keep a tiny Parquet fixture in `tests/data/` for reader tests, and test that the pipeline runs end to end on it.
- Test under the dtypes you ship: pandas 3 behaviour (`str`, `datetime64[us]`, Copy-on-Write) differs from pandas 2, so run CI on the pinned version.

## 12. Review Checklist

- [ ] The grain of each table is stated and key uniqueness is checked.
- [ ] Every join has a stated cardinality (`validate=` or an assertion) and row counts are checked.
- [ ] Missing values are counted and handled by an explicit rule per column; no blanket `fillna(0)`.
- [ ] Dtypes are explicit on read; dates parsed; time zones consistent; categories used for repeated text.
- [ ] No chained assignment, `inplace=True`, row-wise `apply`, `iterrows` or `map_elements` where a vectorised form exists.
- [ ] Only needed columns and rows are read; Parquet is used for reused data; partitions match filters.
- [ ] Polars code stays lazy until the end; the plan shows pushdown; streaming used for large inputs.
- [ ] SQL values are parameterised; no untrusted text reaches `query`, `eval` or SQL strings; no pickle from outside.
- [ ] Output is sorted deterministically, typed, and written to Parquet with a documented schema.
- [ ] Tests cover edge cases and compare frames with the testing helpers; the library versions are pinned.
- [ ] Secrets and personal data are absent from code, notebooks and logs.

## 13. Production Notes

- Pin pandas, Polars, DuckDB and PyArrow in a lockfile; the major versions changed defaults (pandas 3 strings, datetimes and Copy-on-Write; Polars 2 engine and SQL behaviour; DuckDB 2 Python API). Read the release notes before upgrading and run the tests on the new versions.
- Run pipelines as scripts or tasks with logged row counts per stage, input snapshot ids and output paths. Fail loudly when validation fails.
- Make runs idempotent: write to a temporary location and rename, or overwrite a partition completely; do not append blindly on retry.
- Set resource limits: DuckDB `memory_limit`, `threads` and `temp_directory`; container memory above the engine limit; Polars streaming for large inputs.
- Keep file layout healthy: moderately sized Parquet files, partitions that match queries, periodic compaction of tiny files.
- Schedule schema checks on inputs; upstream column renames and type changes are the common cause of breakage.
- Notebooks in production are a smell: parameterise and run them with a tool that records the executed copy, or convert them to scripts.

## 14. Examples

The same aggregation in three engines, on a Parquet file written once. This runs on pandas 3.1, Polars 2.1 and DuckDB 2.0.

```python
import pathlib
import tempfile

import duckdb
import pandas as pd
import polars as pl

path = pathlib.Path(tempfile.mkdtemp()) / "orders.parquet"
pd.DataFrame(
    {
        "region": ["north", "north", "south", "south", "south"],
        "amount": [10.0, 20.0, None, 5.0, 15.0],
        "ts": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-01", "2026-01-03", "2026-01-03"], utc=True),
    }
).to_parquet(path)

# pandas: eager, read only needed columns, named aggregation
pdf = pd.read_parquet(path, columns=["region", "amount"])
by_region_pd = (
    pdf.dropna(subset=["amount"])
    .groupby("region", as_index=False)
    .agg(total=("amount", "sum"), orders=("amount", "size"))
    .sort_values("region", ignore_index=True)
)

# Polars: lazy scan, pushdown, expressions
by_region_pl = (
    pl.scan_parquet(path)
    .filter(pl.col("amount").is_not_null())
    .group_by("region")
    .agg(total=pl.col("amount").sum(), orders=pl.len())
    .sort("region")
    .collect()
)

# DuckDB: SQL straight over the file; the path is trusted, values would be parameters
by_region_db = duckdb.sql(
    f"""
    SELECT region, sum(amount) AS total, count(*) AS orders
    FROM read_parquet('{path.as_posix()}')
    WHERE amount IS NOT NULL
    GROUP BY region
    ORDER BY region
    """
).pl()

assert by_region_pd["total"].tolist() == by_region_pl["total"].to_list() == by_region_db["total"].to_list()
print(by_region_pl)
```

A join with a cardinality check and a row-count assertion (pandas):

```python
import pandas as pd

orders = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": [10, 10, 11], "amount": [5.0, 7.0, 3.0]})
customers = pd.DataFrame({"customer_id": [10, 11], "tier": ["gold", "basic"]})

enriched = orders.merge(customers, on="customer_id", how="left", validate="m:1", indicator=True)
assert len(enriched) == len(orders)                   # a m:1 join must not add rows
assert (enriched["_merge"] == "both").all()           # every order found its customer
enriched = enriched.drop(columns="_merge")
print(enriched.groupby("tier")["amount"].sum().to_dict())
```

Schema validation with pandera, collecting all failures:

```python
import pandas as pd
import pandera.pandas as pa

schema = pa.DataFrameSchema(
    {
        "id": pa.Column(int, pa.Check.ge(0), unique=True),
        "region": pa.Column(str, pa.Check.isin(["a", "b"])),
        "amt": pa.Column(float, nullable=True),
    },
    strict=True,
    coerce=True,
)

bad = pd.DataFrame({"id": [1, 1], "region": ["a", "z"], "amt": [1.0, 2.0]})
try:
    schema.validate(bad, lazy=True)
except pa.errors.SchemaErrors as err:
    print(err.failure_cases[["column", "check"]].to_dict("records"))
```

Time-series resampling with explicit time zone handling (pandas):

```python
import pandas as pd

ts = pd.DataFrame(
    {"ts": pd.date_range("2026-01-01", periods=6, freq="12h", tz="UTC"), "v": range(6)}
).set_index("ts")
daily_paris = ts.tz_convert("Europe/Paris").resample("1D").agg({"v": ["sum", "mean"]})
print(daily_paris.shape)
```

More engine-specific examples are in the reference files below.

## 15. Common Mistakes

- **Joining without checking key uniqueness**: duplicates multiply rows and inflate totals. Use `validate=` and compare row counts and sums.
- **Chained assignment** (`df[df.a > 1]["b"] = 0`): does nothing under pandas 3 Copy-on-Write. Use `df.loc[df["a"] > 1, "b"] = 0`.
- **Assuming strings are `object`** in pandas 3: dtype checks against `object` fail. Use `pd.api.types.is_string_dtype` or `select_dtypes(include="str")`.
- **Casting datetimes to `int64` and assuming nanoseconds**: pandas 3 infers the resolution, often microseconds. Convert with `as_unit` before doing integer maths.
- **Using `NaN` equality in joins**: pandas matches `NaN` keys to each other, Polars and SQL do not. Drop or fill null keys on purpose.
- **Row-wise `apply`, `iterrows`, `map_elements`** for logic that has a vectorised form: orders of magnitude slower and not parallel.
- **Calling `.collect()` early in Polars** and filtering afterwards: loses pushdown and memory benefits.
- **Reading a whole CSV when a few columns are needed**, or re-parsing the same CSV every run: convert to Parquet once.
- **Partitioning Parquet by a high-cardinality column**: millions of tiny files. Partition by date or region and keep files reasonably large.
- **Relying on group order or join order**: neither is guaranteed. Sort explicitly before positional operations and before writing.
- **Default window frame in SQL** with ties: `ORDER BY` without a frame uses a `RANGE` frame, so equal keys share a running total. Spell out `ROWS BETWEEN ...` for row-by-row sums.
- **`fillna(0)` as a default**: turns "unknown" into a measured zero and biases means. Decide per column.
- **Mixing naive and time-zone-aware timestamps**, or resampling in UTC when the business day is local: convert before resampling.
- **Unpickling or `read_pickle` on external files**: code execution risk. Use Parquet or Arrow.
- **Formatting values into SQL strings**: injection risk and quoting bugs. Bind parameters.
- **Rewriting a working pandas job in another engine without a benchmark and an equality test**: gains are workload-specific.

## 16. References

- [references/pandas.md](references/pandas.md): pandas 3 changes (Copy-on-Write, `str` dtype, datetime resolution), dtypes and missing data, `pd.col`, merges with `validate=`, reshaping, groupby and windows, time series, upgrade checklist.
- [references/polars.md](references/polars.md): expressions and contexts, lazy scans and engines, joins, window expressions, reshaping, time series, nulls and dtypes, Parquet output and partitions, pitfalls.
- [references/duckdb-arrow-parquet.md](references/duckdb-arrow-parquet.md): DuckDB Python API and SQL features, parameters, reading and writing files, memory and spilling, PyArrow interchange and datasets, Parquet layout and partitioning.
- [references/performance-and-memory.md](references/performance-and-memory.md): measuring, reading less, dtypes and memory, vectorisation, chunked and out-of-core work, lazy evaluation, join and sort costs, switching tools, benchmarking.
- pandas: https://pandas.pydata.org/docs/ and release notes https://pandas.pydata.org/docs/whatsnew/index.html
- Polars: https://docs.pola.rs/ and releases https://github.com/pola-rs/polars/releases
- DuckDB: https://duckdb.org/docs/ and releases https://github.com/duckdb/duckdb/releases
- Apache Arrow / PyArrow: https://arrow.apache.org/docs/python/ ; Parquet: https://parquet.apache.org/docs/
- pandera: https://pandera.readthedocs.io/
- Tidy data (Wickham, Journal of Statistical Software, 2014): https://www.jstatsoft.org/article/view/v059i10
