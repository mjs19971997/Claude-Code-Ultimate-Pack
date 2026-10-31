# DuckDB, Arrow and Parquet

DuckDB for SQL over Parquet, CSV and in-memory DataFrames, PyArrow as the interchange layer, and Parquet file layout and partitioning. The code blocks run in order in one session (checked with DuckDB 2.0.0, PyArrow 26.0.0, pandas 3.1.0 and Polars 2.1.0 on Python 3.13, 2026-10).

## Contents

1. [DuckDB in Python](#1-duckdb-in-python)
2. [Parameters and safety](#2-parameters-and-safety)
3. [SQL features worth using](#3-sql-features-worth-using)
4. [Reading and writing files](#4-reading-and-writing-files)
5. [Memory, threads and spilling](#5-memory-threads-and-spilling)
6. [PyArrow as interchange](#6-pyarrow-as-interchange)
7. [Parquet layout and partitioning](#7-parquet-layout-and-partitioning)
8. [Pitfalls](#8-pitfalls)

## 1. DuckDB in Python

```python
import pathlib
import tempfile

import duckdb
import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

workdir = pathlib.Path(tempfile.mkdtemp())
df = pd.DataFrame(
    {
        "region": list("aabbb"),
        "amt": [1.0, 2.0, None, 4.0, 5.0],
        "day": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03"]),
    }
)

# duckdb.sql uses the default in-memory connection and finds local DataFrames by variable name
print(duckdb.sql("SELECT region, sum(amt) AS total FROM df GROUP BY ALL ORDER BY region").df())

con = duckdb.connect()                 # explicit connection; pass a file path for a persistent database
con.register("t", df)                  # make a DataFrame visible under a stable name
rel = con.table("t").filter("amt IS NOT NULL").aggregate("region, sum(amt) AS total").order("region")
print(rel.df())                        # relational API: each step returns a new relation
```

- `duckdb.sql(query)` returns a lazy relation on the default connection. Nothing runs until you ask for a result: `.df()`, `.pl()`, `.arrow()`, `.fetchall()`, `.write_parquet(path)`.
- DuckDB reads pandas, Polars and Arrow objects by variable name (replacement scans). Use `con.register(name, obj)` when the name must be explicit or the object is not a plain local variable.
- Use a connection per workload: `duckdb.connect()` for in-memory, `duckdb.connect("analysis.duckdb")` for a database file. A connection is not thread-safe; give each thread its own `con.cursor()`.
- In DuckDB 2.0.0 a relation keeps no result between calls (`rel.fetchone()` is gone; use `rel.limit(1).fetchall()`), and a result from `con.execute(...)` must be fully read before other work on the same connection. Convert with `con.sql(query).to_arrow_reader()` or `.to_arrow_table()` instead of Arrow output on a DB-API result (it warns about an extra copy). Re-check these against the current Python API docs when upgrading.
- Return types: `.df()` gives pandas, `.pl()` Polars, `.arrow()` or `.to_arrow_table()` PyArrow; the relation also exports through the Arrow C stream interface.

## 2. Parameters and safety

```python
print(con.execute("SELECT * FROM t WHERE region = ? AND amt > ?", ["b", 3]).df())
print(con.execute("SELECT count(*) FROM t WHERE region = $r", {"r": "a"}).fetchall())
```

- Bind values with `?` or `$name` placeholders; never format user input into SQL text.
- Identifiers (table and column names) and file paths cannot be bound. Validate them against an allow-list, or build paths from a trusted base directory, before placing them in an f-string.
- File and network access: `read_csv`, `read_parquet`, `COPY` and extensions can touch the filesystem and URLs. For untrusted queries, check the DuckDB security documentation (`enable_external_access`, `lock_configuration`) before exposing a connection.

## 3. SQL features worth using

```python
q = """
SELECT region, day, amt,
       sum(amt) OVER (PARTITION BY region ORDER BY day, amt ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running,
       row_number() OVER (PARTITION BY region ORDER BY amt DESC NULLS LAST) AS rn
FROM t
ORDER BY region, day, amt DESC NULLS LAST
"""
print(con.sql(q).df())
print(con.sql("SELECT * FROM t QUALIFY row_number() OVER (PARTITION BY region ORDER BY amt DESC NULLS LAST) = 1 ORDER BY region").df())
print(con.sql("SELECT region, sum(amt) FILTER (WHERE day >= '2026-01-02') AS late FROM t GROUP BY ALL ORDER BY region").df())
print(con.sql("PIVOT t ON region USING sum(amt) GROUP BY day ORDER BY day").df())
wide = pd.DataFrame({"id": [1, 2], "q1": [5, 6], "q2": [7, 8]})
print(con.sql("UNPIVOT wide ON q1, q2 INTO NAME quarter VALUE sales").df())
```

- `GROUP BY ALL` groups by every non-aggregated column in the select list; `QUALIFY` filters on window results without a subquery.
- A window with `ORDER BY` and no frame uses `RANGE ... CURRENT ROW`, so rows with equal order keys share one running value. Write `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` when you want a strict row-by-row running total.
- `FILTER (WHERE ...)` on an aggregate gives conditional sums and counts in one pass.
- `PIVOT` and `UNPIVOT` are SQL statements here, covering the reshaping done by `pivot`/`melt` in pandas.
- `ASOF JOIN ... ON a.t >= q.t` matches the latest earlier row. `SUMMARIZE t` returns column statistics; `DESCRIBE SELECT ...` returns inferred types.
- `EXPLAIN SELECT ...` shows the plan; for Parquet scans look for projected columns and filters on the scan node. `EXPLAIN ANALYZE` adds timings.

## 4. Reading and writing files

```python
con.execute(
    f"COPY t TO '{(workdir / 'ds').as_posix()}' (FORMAT parquet, PARTITION_BY (region), COMPRESSION zstd)"
)
glob = (workdir / "ds").as_posix() + "/**/*.parquet"
print(con.sql(f"SELECT region, count(*) AS n FROM read_parquet('{glob}', hive_partitioning = true) WHERE region = 'b' GROUP BY region").fetchall())

con.sql("SELECT region, sum(amt) AS total FROM t GROUP BY region").write_parquet(str(workdir / "summary.parquet"))

(workdir / "c.csv").write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
csv_path = (workdir / "c.csv").as_posix()
print(con.sql(f"SELECT * FROM read_csv('{csv_path}', types = {{'a': 'BIGINT'}})").df().dtypes.to_dict())
print(con.sql(f"DESCRIBE SELECT * FROM read_csv('{csv_path}', all_varchar = true)").fetchall()[0][:2])
```

- Parquet readers push projections and filters into the scan, and use row-group statistics to skip data. Select only the columns you need and filter on partition or sorted columns.
- `read_csv` sniffs delimiter, header and types from a sample. Fix wrong guesses with `types = {...}`, `all_varchar = true`, `dateformat`, `sample_size`, `ignore_errors`; check the current docs for option names.
- `COPY (SELECT ...) TO 'file.parquet' (FORMAT parquet, ROW_GROUP_SIZE 100000, COMPRESSION zstd)` writes a single file; `PARTITION_BY (cols)` writes Hive-style folders.
- Reading from S3, GCS or HTTP uses extensions (`httpfs`) and secrets configured through DuckDB's secrets manager. Keep credentials out of code and SQL history.
- Inspect a Parquet file with `SELECT * FROM parquet_metadata('f.parquet')` (row groups, min/max statistics) and `parquet_schema`.

## 5. Memory, threads and spilling

```python
con.execute("SET memory_limit = '2GB'")
con.execute("SET threads = 4")
con.execute(f"SET temp_directory = '{(workdir / 'spill').as_posix()}'")
print(con.sql("SELECT current_setting('memory_limit')").fetchall())
```

- DuckDB runs larger-than-memory aggregations, joins and sorts by spilling to `temp_directory`. Point it at a fast disk with free space and set `memory_limit` below the machine or container limit.
- `SET preserve_insertion_order = false` can lower memory use for big exports when row order is irrelevant.
- Stream results instead of materialising them: `con.sql(q).to_arrow_reader()` returns a `pyarrow.RecordBatchReader`; iterate its batches.
- A persistent database file suits repeated queries over the same data; for one-off analysis, query Parquet in place.

## 6. PyArrow as interchange

```python
tbl = pa.Table.from_pandas(df, preserve_index=False)
print(tbl.schema.names)
print(type(pl.from_arrow(tbl)).__name__, type(tbl.to_pandas()).__name__)
print(tbl.to_pandas(types_mapper=pd.ArrowDtype).dtypes.tolist())    # keep Arrow dtypes in pandas
print(con.sql("SELECT count(*) FROM tbl").fetchall())             # DuckDB queries the Arrow table in place
```

- Arrow is a columnar in-memory format shared by pandas (optional backend), Polars and DuckDB. Moving between them through Arrow avoids Python objects and, for compatible types, copies.
- pandas 3 builds a `str` column from an Arrow string on conversion; pass `types_mapper=pd.ArrowDtype` to keep Arrow dtypes, or use `dtype_backend="pyarrow"` on readers.
- `pyarrow.dataset` scans many files lazily with projection and predicate pushdown:

```python
dset = ds.dataset(workdir / "ds", format="parquet", partitioning="hive")
print(dset.to_table(filter=ds.field("region") == "b").num_rows)
ds.write_dataset(tbl, workdir / "w", format="parquet", partitioning=["region"],
                 partitioning_flavor="hive", existing_data_behavior="error")
```

- `pq.write_table(tbl, path, compression="zstd", row_group_size=...)`, `pq.read_table(path, columns=[...], filters=[("amt", ">", 1)])` and `pq.ParquetFile(path).metadata` cover single files. Set `existing_data_behavior` deliberately in `write_dataset` so a rerun does not overwrite or duplicate files.
- Parquet types: use timestamps with an explicit unit and time zone, decimals for money, and dictionary encoding (`pa.dictionary` or categorical) for repeated strings. Check that nanosecond timestamps survive the reader you use.

## 7. Parquet layout and partitioning

- Aim for files of roughly 100 MB to 1 GB (a common rule of thumb; measure on your reader) and row groups large enough for efficient compression and statistics. Thousands of tiny files and a single multi-gigabyte file are both poor layouts.
- Partition by columns that queries filter on and that have low cardinality (date at day or month level, region, tenant). Do not partition by an id or timestamp: the result is millions of folders.
- Hive-style folders (`region=b/part-0.parquet`) are understood by DuckDB (`hive_partitioning`), Polars (`hive_partitioning=True`) and PyArrow (`partitioning="hive"`). Partition values live in the path, not in the file; the reader adds them as columns.
- Sort data within files by a commonly filtered column before writing so row-group statistics prune well.
- Keep a stable schema across files; add columns rather than changing types. Readers differ on schema evolution, so test with the reader that will be used (Polars has `missing_columns` and `extra_columns` options on `scan_parquet`).
- Write once, append by adding files, and never edit Parquet files in place. For updates and transactions use a table format (Iceberg, Delta Lake) or a database; check the current docs of the tool you choose.
- Compression: `zstd` is a good default for size and speed; `snappy` is faster to write with larger files. Benchmark both on your data.

## 8. Pitfalls

- Formatting user text into SQL strings instead of binding parameters.
- Relying on the default window frame for running totals when ties are possible.
- Reading all columns with `SELECT *` from a wide Parquet dataset.
- Leaving `memory_limit` unset inside a small container; set it explicitly below the container limit so DuckDB spills instead of the process being killed.
- Using one connection from several threads; use `cursor()` per thread.
- Partitioning on a high-cardinality column, producing many small files.
- Writing a partitioned dataset into a non-empty directory without deciding how existing files are treated.
