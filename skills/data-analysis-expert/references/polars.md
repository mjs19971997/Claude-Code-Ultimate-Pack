# Polars Patterns

Polars 2.x for tabular work: expressions, the lazy API with `scan_*`, the streaming engine, joins with `validate=`, window expressions with `over`, reshaping, time series and Parquet output. The code blocks run in order in one session (checked with Polars 2.1.0 on Python 3.13, 2026-10).

## Contents

1. [Mental model](#1-mental-model)
2. [Expressions and contexts](#2-expressions-and-contexts)
3. [Lazy scans and engines](#3-lazy-scans-and-engines)
4. [Joins](#4-joins)
5. [Window expressions and group by](#5-window-expressions-and-group-by)
6. [Reshaping](#6-reshaping)
7. [Time series](#7-time-series)
8. [Nulls and dtypes](#8-nulls-and-dtypes)
9. [Writing Parquet and partitions](#9-writing-parquet-and-partitions)
10. [Pitfalls](#10-pitfalls)

## 1. Mental model

- A `DataFrame` is eager; a `LazyFrame` records a query plan and runs it on `collect()`. Start with `scan_parquet` or `scan_csv` so the optimizer can push filters and column selections into the reader and skip unused columns.
- There are no row indexes. Position-based tricks from pandas (`iloc`, index alignment) have no counterpart; use `with_row_index`, joins and window expressions.
- Work is expressed with expressions (`pl.col("x") * 2`) inside contexts (`select`, `with_columns`, `filter`, `group_by().agg`). Expressions run in parallel and are optimised as a whole; Python lambdas are not.
- Polars 2.0.0 (October 2026) is the current major line. Its release notes list SQL changes (window functions over grouped rows, exact numeric literals as Decimal), Parquet `ENUM` columns read as `pl.String`, out-of-core streaming enabled by default, and `cut`/`qcut` deprecated. Check the upgrade guide on docs.pola.rs when moving from 1.x.

## 2. Expressions and contexts

```python
import datetime as dt
import pathlib
import tempfile

import polars as pl

workdir = pathlib.Path(tempfile.mkdtemp())
df = pl.DataFrame(
    {
        "region": ["a", "a", "b", "b", "b"],
        "ts": [dt.datetime(2026, 1, 1, h) for h in (0, 6, 12, 18, 23)],
        "amt": [1.0, 2.0, None, 4.0, 5.0],
        "item": ["x", "y", "x", "y", "x"],
    }
)

out = df.with_columns(
    size=pl.when(pl.col("amt") > 3).then(pl.lit("big")).otherwise(pl.lit("small")),
    amt_filled=pl.col("amt").fill_null(0),
).filter(pl.col("amt").is_between(1, 5))
print(out.shape)
```

- `with_columns` adds or replaces columns and keeps the rest; `select` returns only what you list. Keyword arguments name the new column.
- `pl.when(cond).then(a).otherwise(b)` is the vectorised if/else; chain several `.when` for a case table.
- Selectors (`import polars.selectors as cs`, `cs.numeric()`, `cs.starts_with("q")`) choose columns by dtype or name pattern.
- `pl.len()` counts rows; `pl.col("x").count()` counts non-null values. Pick deliberately.
- `map_elements` runs a Python function per value and emits a `PolarsInefficientMapWarning` when a native expression exists. Rewrite with expressions first.
- Strings, dates and lists have namespaces: `.str`, `.dt`, `.list`, `.struct`, `.arr`.

## 3. Lazy scans and engines

```python
df.write_parquet(workdir / "t.parquet")

lf = (
    pl.scan_parquet(workdir / "t.parquet")
    .filter(pl.col("amt").is_not_null())
    .with_columns(share=pl.col("amt") / pl.col("amt").sum().over("region"))
    .group_by("region", maintain_order=True)
    .agg(total=pl.col("amt").sum(), shares=pl.col("share").max(), n=pl.len())
    .sort("region")
)
print(lf.explain())                     # check PROJECT n/m COLUMNS and SELECTION in the scan
result = lf.collect()
streamed = lf.collect(engine="streaming")
in_memory = lf.collect(engine="in-memory")
print(result.shape, streamed.shape, in_memory.shape)
```

- `LazyFrame.explain()` prints the optimised plan. A scan line such as `PROJECT 3/4 COLUMNS` and a `SELECTION` entry show projection and predicate pushdown at work.
- `collect(engine=...)` accepts `"auto"`, `"in-memory"`, `"streaming"` and `"gpu"`. In 2.1.0 the installed docstring says `"auto"` uses the engine set by `pl.Config.set_engine_affinity` or `POLARS_ENGINE_AFFINITY` and falls back to `"streaming"` if unset; if the selected engine cannot run a query, Polars falls back to the in-memory engine. Pass the engine explicitly when you need predictable behaviour.
- The streaming engine processes data in batches and can spill to disk (out-of-core processing is on by default in 2.0, per the release notes). The RAM threshold and disk budget are configurable; check the docs for the current settings.
- `sink_parquet`, `sink_csv` and `sink_ipc` write a lazy query to disk without materialising the whole result:

```python
pl.scan_parquet(workdir / "t.parquet").filter(pl.col("amt") > 1).sink_parquet(workdir / "out.parquet")
print(pl.read_parquet(workdir / "out.parquet").shape)
```

- `scan_csv` infers the schema from the first rows only. Pass `schema_overrides={"col": pl.String}` or `infer_schema_length=None` for columns whose type appears late, and `try_parse_dates=True` for ISO dates.
- Use `lf.collect_schema()` to read names and dtypes; reading `lf.schema` resolves the plan and emits a `PerformanceWarning`.
- Multi-file scans accept globs and directories (`pl.scan_parquet("data/*.parquet")`); `include_file_paths="path"` adds the source file as a column. Hive-style directories need `hive_partitioning=True` to expose `key=value` folders as columns.

## 4. Joins

```python
left = pl.DataFrame({"id": [1, 2, 2], "n": ["a", "b", "c"]})
right = pl.DataFrame({"id": [1, 2], "amt": [10, 20]})

try:
    left.join(right, on="id", validate="1:1")
except Exception as err:               # polars.exceptions.ComputeError
    print(type(err).__name__)

joined = left.join(right, on="id", how="left", validate="m:1")
missing = left.join(right, on="id", how="anti")
print(joined.shape, missing.shape)
```

- `validate` accepts `"m:m"` (default, no check), `"1:1"`, `"1:m"` and `"m:1"`. Set it whenever you know the cardinality.
- `how` covers `inner`, `left`, `right`, `full`, `semi`, `anti` and `cross`. `semi` and `anti` filter the left table without adding columns, which replaces most `isin` tricks.
- Nulls do not match each other unless `nulls_equal=True`. This differs from pandas, which matches `NaN` keys.
- Key columns of the same name are coalesced for `left` and `inner` joins; use `suffix=` for clashing non-key columns (default `_right`), and `coalesce=` to control full joins.
- Join order is not guaranteed unless `maintain_order` is set; sort afterwards when order matters.
- `join_asof(other, on="ts", by="symbol", strategy="backward", tolerance="3s")` matches the nearest earlier row; both sides must be sorted on the key.
- Joining on columns with different dtypes raises; cast both sides to one dtype first.

## 5. Window expressions and group by

```python
ranked = df.with_columns(
    share=pl.col("amt") / pl.col("amt").sum().over("region"),
    rank=pl.col("amt").rank("dense", descending=True).over("region"),
    running=pl.col("amt").cum_sum().over("region", order_by="ts"),
)
top = df.group_by("region", maintain_order=True).agg(
    total=pl.col("amt").sum(), best=pl.col("item").sort_by("amt").last()
)
print(ranked.shape, top.shape)
```

- `expr.over("key")` computes a group-wise value and broadcasts it back to every row (the pandas `transform` pattern). `over("key", order_by="ts")` orders rows inside each window for cumulative or lagging expressions.
- `group_by(...).agg(...)` returns one row per group. Group order is not stable unless `maintain_order=True`.
- `pl.col("x").sort_by("y").last()`, `.first()`, `.top_k(n)`, `.implode()` pick or collect values within a group without `apply`.
- Multiple aggregations run in one pass; list them in a single `agg` call rather than looping over columns.
- `df.sort("ts").rolling("ts", period="12h").agg(...)` and `group_by_dynamic("ts", every="1d")` give time-based windows; the index column must be sorted.
- `unique(subset=[...], keep="first", maintain_order=True)` removes duplicates deterministically; `value_counts(sort=True)` summarises categories.

## 6. Reshaping

```python
wide = pl.DataFrame({"id": [1, 2], "q1": [5, 6], "q2": [7, 8]})
long = wide.unpivot(index="id", variable_name="quarter", value_name="sales")
back = long.pivot(on="quarter", index="id", values="sales", aggregate_function="sum")
print(long.shape, back.shape)
```

- `unpivot` (wide to long) replaced the older `melt` name; `pivot` goes long to wide and needs `aggregate_function` when index and column pairs repeat.
- `explode("col")` turns list entries into rows; `str.split(",")` produces the list first. `struct.unnest()` spreads struct fields into columns.
- `concat([...], how="vertical" | "diagonal" | "horizontal")` combines frames; `diagonal` fills missing columns with nulls.

## 7. Time series

```python
daily = df.sort("ts").group_by_dynamic("ts", every="1d").agg(pl.col("amt").sum())
rolling = df.sort("ts").rolling("ts", period="12h").agg(pl.col("amt").mean())
print(daily.shape, rolling.shape)
```

- Datetime columns carry a unit (`ms`, `us`, `ns`) and an optional time zone. Parse with `pl.col("s").str.to_datetime(...)` and set zones with `dt.replace_time_zone` (label naive data) or `dt.convert_time_zone` (change the zone of aware data).
- `group_by_dynamic` takes `every`, `period`, `offset`, `closed`, `label` and `group_by`; `upsample("ts", every="1h")` inserts missing rows, then fill with `forward_fill`, `interpolate` or constants.
- Sort by the time column before dynamic windows. The `check_sortedness` flag guards `join_asof`; do not disable it without sorting.

## 8. Nulls and dtypes

```python
print(df.null_count())
cleaned = df.with_columns(
    pl.col("region").cast(pl.Categorical),
    pl.col("item").cast(pl.Enum(["x", "y"])),
)
print(cleaned.schema["item"])
```

- Polars uses `null` for every dtype; floating-point `NaN` is a separate value. `fill_null` fills nulls, `fill_nan` fills NaN, `is_nan` and `is_null` test them.
- Prefer `pl.Enum([...])` for a fixed, known set of categories (validated) and `pl.Categorical` for open sets. Both save memory against strings for repeated values.
- Integer columns stay integers with nulls; there is no float promotion. Casting with `strict=True` (default) raises on lossy values, `strict=False` makes them null; count the nulls afterwards.
- Use the smallest sensible numeric dtypes (`pl.Int32`, `pl.Float32`) for large frames when precision allows; `df.estimated_size("mb")` reports the footprint.
- Eager arithmetic mixing strings and numbers is disallowed in 2.1.0 (breaking-change note in the release page). Cast explicitly.

## 9. Writing Parquet and partitions

```python
df.write_parquet(workdir / "part", partition_by="region")      # one folder per region value
parts = sorted(p.relative_to(workdir).as_posix() for p in (workdir / "part").rglob("*.parquet"))
print(parts)
back = pl.scan_parquet(workdir / "part", hive_partitioning=True).collect()
print(back.columns)
```

- `write_parquet` defaults to `zstd` compression; set `compression`, `compression_level`, `row_group_size` and `statistics` as needed.
- `partition_by` on `write_parquet` writes Hive-style folders. `sink_parquet(pl.PartitionBy(base_path, key="region"))` does the same from a lazy query and supports `max_rows_per_file`.
- Partition on low-cardinality columns that queries filter by (date, region). Thousands of tiny files hurt scans; see [duckdb-arrow-parquet.md](duckdb-arrow-parquet.md).
- Pass `storage_options` for object stores; keep credentials out of the code (environment or a credential provider).
- Interop: `df.to_pandas()`, `df.to_arrow()`, `pl.from_pandas(pdf)`, `pl.from_arrow(table)`; the Arrow route avoids Python objects.

## 10. Pitfalls

- Calling `.collect()` early and continuing eagerly throws away pushdown. Keep the pipeline lazy until the final result.
- Using Python `for` loops over rows or `map_elements` for logic that exists as an expression.
- Treating `group_by` order as stable, or relying on join output order.
- Reading `lf.schema` in a loop; it resolves the plan each time.
- Assuming a pandas index exists after `to_pandas()`; add the key as a column and set the index only if needed.
- Expecting `NaN` and `null` to behave the same in filters and aggregations.
- Casting join keys implicitly: align key dtypes yourself and test the result with `validate=` and a row count.
