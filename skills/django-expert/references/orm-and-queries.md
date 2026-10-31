# ORM, Queries and Transactions

QuerySet behaviour, N+1 diagnosis and fixes, annotations, bulk operations, transactions with locking and `on_commit`, and the async ORM on Django 6.0 and 6.1. Snippets use the `Category`, `Product` and `Tag` models from SKILL.md section 14 and were run on Django 6.1.2 (2026-10).

## Contents

1. [QuerySet basics](#1-queryset-basics)
2. [N+1 and relation loading](#2-n1-and-relation-loading)
3. [Fetch modes in 6.1](#3-fetch-modes-in-61)
4. [Filters, F and Q](#4-filters-f-and-q)
5. [Aggregation and subqueries](#5-aggregation-and-subqueries)
6. [Bulk operations and large scans](#6-bulk-operations-and-large-scans)
7. [Transactions and locking](#7-transactions-and-locking)
8. [Async ORM](#8-async-orm)
9. [Diagnosing queries](#9-diagnosing-queries)
10. [Deprecations and changes to watch](#10-deprecations-and-changes-to-watch)

## 1. QuerySet basics

- A QuerySet is lazy: building it runs no SQL. SQL runs on iteration, `len()`, `list()`, `bool()`, slicing with a step, `repr()`, `get()`, `count()`, `exists()`, `first()`, aggregates and writes.
- Results are cached on the QuerySet instance after the first evaluation. A new `.filter()` creates a new QuerySet and a new query.
- Use the cheapest terminal for the question:

| Need | Use | Avoid |
|---|---|---|
| Is there any row | `qs.exists()` | `if qs:` or `len(qs) > 0` (loads every row) |
| How many | `qs.count()` | `len(qs)` unless the rows are already loaded |
| One row, must exist | `qs.get(pk=...)` (raises `DoesNotExist` / `MultipleObjectsReturned`) | `qs.filter(...)[0]` |
| First by order | `qs.order_by("created").first()` | `list(qs)[0]` |
| A column of ids | `qs.values_list("id", flat=True)` | iterating full instances |
| Dicts for output | `qs.values("id", "name")` | instances when only two columns are needed |

- `get_or_create` and `update_or_create` need a unique constraint on the lookup fields to be race-free; they retry through `IntegrityError` only when such a constraint exists.

```python
obj, created = Product.objects.update_or_create(
    category=cat, name="p1", defaults={"price_cents": 99}
)
```

## 2. N+1 and relation loading

An N+1 appears when code iterates a QuerySet and touches a related object for each row. Query count equals 1 plus the number of rows.

```python
# 1 + N queries
for p in Product.objects.all():
    print(p.category.name)

# 1 query: forward FK or one-to-one joined in SQL
for p in Product.objects.select_related("category"):
    print(p.category.name)

# 2 queries: reverse FK or many-to-many loaded with a second IN query
for c in Category.objects.prefetch_related("products"):
    print([p.name for p in c.products.all()])
```

- `select_related("a", "a__b")` follows FK and one-to-one forward (and one-to-one reverse). One JOIN query; wide rows if overused.
- `prefetch_related("rel")` runs one extra query per relation level and joins results in Python. Works for reverse FK, M2M and generic relations.
- `Prefetch` customises the second query and can store the result under another attribute:

```python
from django.db.models import Prefetch

cats = Category.objects.prefetch_related(
    Prefetch(
        "products",
        queryset=Product.objects.filter(stock__gt=0).only("id", "name", "category_id"),
        to_attr="available",
    )
)
```

- Calling `.filter()` or `.order_by()` on a prefetched relation (`c.products.filter(...)`) discards the prefetch cache and issues a new query. Filter inside `Prefetch(queryset=...)` instead.
- `select_related()` with no arguments is deprecated in 6.1; name each relation.
- `only("name", "category__name")` and `defer("body")` limit columns. Accessing a deferred field later issues one query per instance, so do not defer what is read.
- In DRF, put the loading in `get_queryset()`; a nested serializer cannot fix it. In admin, use `list_select_related = ("category",)` (the value `True` is deprecated in 6.1) and override `get_queryset` for prefetches.

## 3. Fetch modes in 6.1

Django 6.1 adds `QuerySet.fetch_mode()` to control what happens when code reads a field or relation that was not loaded (deferred fields and FK/one-to-one descriptors).

```python
from django.db.models import FETCH_ONE, FETCH_PEERS, FETCH_RAISE
from django.db.models.fetch_modes import FieldFetchBlocked  # exception

qs = Product.objects.fetch_mode(FETCH_PEERS)
[p.category.name for p in qs]          # 2 queries instead of 1 + N

guard = Product.objects.fetch_mode(FETCH_RAISE)
p = guard.first()
p.category                              # raises FieldFetchBlocked
```

- `FETCH_ONE` is the default: load the missing value for that instance only.
- `FETCH_PEERS`: load the missing value for every instance that came from the same QuerySet in one query. A safety net, not a replacement for `select_related` where the join is known up front.
- `FETCH_RAISE`: raise `FieldFetchBlocked`. Use in tests and in serializers or templates that must not hit the database.
- Custom `Model.from_db()` overrides need a `fetch_mode=None` parameter; versions without it are deprecated.

## 4. Filters, F and Q

```python
from django.db.models import F, Q

Product.objects.filter(Q(stock=0) | Q(price_cents__gt=10_000), ~Q(name__startswith="x"))
Product.objects.filter(stock__lt=F("reorder_level"))          # column to column
Product.objects.filter(pk=pk).update(stock=F("stock") - 1)    # atomic in SQL
```

- Chained `.filter()` calls across multi-valued relations apply to different related rows; a single `.filter(a=..., b=...)` applies to the same row. Know which one you mean.
- After `F()` update the in-memory instance is stale; call `refresh_from_db(fields=["stock"])` if you read it.
- 6.1: ordering after `union()`, `difference()` and `intersection()` must select the default ordering fields or `DatabaseError` is raised; check `qs.totally_ordered` before paginating.

## 5. Aggregation and subqueries

```python
from django.db.models import Count, Sum, Exists, OuterRef, Subquery
from django.db.models.functions import Coalesce

# one query, grouped in SQL
rows = (
    Category.objects
    .annotate(n=Count("products"), total=Coalesce(Sum("products__price_cents"), 0))
    .values("name", "n", "total")
)

# latest product name per category, plus an existence flag
latest = Product.objects.filter(category=OuterRef("pk")).order_by("-created")
qs = Category.objects.annotate(
    latest_name=Subquery(latest.values("name")[:1]),
    has_stock=Exists(Product.objects.filter(category=OuterRef("pk"), stock__gt=0)),
)
```

- `annotate()` adds a per-row value; `aggregate()` returns one dict for the whole QuerySet. Order matters: `.values("x").annotate(...)` groups by `x`; `.annotate(...).values("x")` does not.
- Conditional aggregation: `Count("products", filter=Q(products__stock__gt=0))`; `Case(When(...), default=...)` for computed columns.
- `Exists()` and `Subquery()` avoid loading rows; prefer them to Python-side joins.
- 6.0 added `StringAgg` and `AnyValue` for all backends and an `order_by` argument on `Aggregate`; the `ordering` keyword on PostgreSQL aggregates was removed in 6.1 (use `order_by`).
- Window functions use `Window(expression=Rank(), partition_by=..., order_by=...)`; check the docs for your Django series before filtering on a window annotation.
- 6.1 adds `UUID4()` and `UUID7()` database functions and `JSONNull()` for JSON scalar null (top-level `None` in JSONField queries is deprecated).

## 6. Bulk operations and large scans

```python
Product.objects.bulk_create(
    [Product(category=cat, name=f"p{i}", price_cents=100) for i in range(1000)],
    batch_size=500,
)

items = list(Product.objects.filter(stock__lt=2))
for p in items:
    p.stock += 10
Product.objects.bulk_update(items, ["stock"], batch_size=500)

Product.objects.filter(stock=0).update(stock=F("stock") + 5)   # one UPDATE
Product.objects.filter(stock=0, created__lt=cutoff).delete()  # one DELETE (plus cascades)
```

- `bulk_create`, `bulk_update`, `QuerySet.update()` and `QuerySet.delete()` do not call `Model.save()` and do not send `pre_save`/`post_save`. Queryset `delete()` still sends `pre_delete`/`post_delete` unless fast-deletion applies; `on_delete=DB_CASCADE` (6.1) sends neither.
- `bulk_create(ignore_conflicts=True)` skips errors silently; `update_conflicts=True` with `unique_fields` and `update_fields` performs an upsert on supported databases.
- `iterator(chunk_size=2000)` streams rows without caching the QuerySet. With PostgreSQL server-side cursors and a transaction pooler (PgBouncer in transaction mode) set `DISABLE_SERVER_SIDE_CURSORS = True` in `DATABASES`.

## 7. Transactions and locking

`ATOMIC_REQUESTS` is off by default; each ORM call autocommits unless you open `transaction.atomic()`.

```python
from django.db import IntegrityError, transaction

@transaction.atomic
def transfer(src_id: int, dst_id: int, amount: int) -> None:
    # lock rows in a stable order to avoid deadlocks
    accounts = {
        a.pk: a
        for a in Account.objects.select_for_update().filter(pk__in=[src_id, dst_id]).order_by("pk")
    }
    src, dst = accounts[src_id], accounts[dst_id]
    if src.balance < amount:
        raise ValueError("insufficient funds")
    Account.objects.filter(pk=src.pk).update(balance=F("balance") - amount)
    Account.objects.filter(pk=dst.pk).update(balance=F("balance") + amount)
```

- `atomic` blocks nest as savepoints. Catch `IntegrityError` outside the block that raised it, or wrap the risky statement in its own inner `atomic`; catching inside a block leaves the transaction broken (`TransactionManagementError`).
- `select_for_update()` only works inside a transaction. Options: `nowait=True`, `skip_locked=True` (job queues), `of=("self",)`, `no_key=True` (PostgreSQL). SQLite ignores row locks.
- `transaction.on_commit(func)` runs `func` after the outermost atomic block commits and drops it on rollback. In `TestCase` use `captureOnCommitCallbacks(execute=True)`. `on_commit(func, robust=True)` logs and continues if a callback raises.
- `transaction.savepoint()` is deprecated in 6.1; use `savepoint_create()` (with `savepoint_commit` / `savepoint_rollback` helpers).

## 8. Async ORM

- Every QuerySet method that runs SQL has an `a`-prefixed counterpart: `aget`, `afirst`, `alast`, `acount`, `aexists`, `acreate`, `aget_or_create`, `aupdate_or_create`, `abulk_create`, `abulk_update`, `aupdate`, `adelete`, `aiterator`, `aaggregate`, `aexplain`, `ain_bulk`, `alatest`, `aearliest`. Model instances have `asave`, `adelete`, `arefresh_from_db`. Related managers expose `aadd`, `aset`, `aremove`, `aclear`.
- `async for obj in qs` works; list comprehension form: `[x async for x in qs]`.
- Lazy foreign-key access in async code raises `SynchronousOnlyOperation`; load with `select_related` / `prefetch_related` or `await qs.aget()` first.
- Transactions do not work in async mode. Put transactional work in a sync function and call it:

```python
from asgiref.sync import sync_to_async


@sync_to_async
def buy(product_id: int) -> None:
    with transaction.atomic():
        p = Product.objects.select_for_update().get(pk=product_id)
        Product.objects.filter(pk=p.pk).update(stock=F("stock") - 1)


async def buy_view(request, pk):
    await buy(pk)
    ...
```

- `sync_to_async` runs in a shared thread by default (`thread_sensitive=True`), so calls from one request serialize; use it for short, DB-bound sync code, not for CPU work.
- Async ORM calls still use a thread pool internally for the database driver; the gain is non-blocking handling of other I/O (HTTP calls, websockets), not faster queries.
- A sync view under ASGI runs in a thread; an async view under WSGI runs in a one-off loop. Match the server to the view style (SKILL.md section 13).
- 6.0 added `AsyncPaginator` and `AsyncPage` for paginating in async views.

## 9. Diagnosing queries

```python
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as ctx:
    list(Product.objects.select_related("category"))
print(len(ctx), ctx.captured_queries[0]["sql"])

print(Product.objects.filter(tags__name="t").distinct().explain())   # plan text
print(Product.objects.filter(stock=0).query)                          # SQL (unexecuted)
```

- `QuerySet.explain(analyze=True)` (PostgreSQL) runs the query; do not use it on destructive or very expensive queries in production.
- Use `assertNumQueries` to freeze an expected count; update the number deliberately when the design changes.

## 10. Deprecations and changes to watch

| Change | Version | Action |
|---|---|---|
| `check` keyword on `CheckConstraint` removed | 6.0 | Use `condition=` |
| Positional args to `Model.save()` / `asave()` removed | 6.0 | Use keywords such as `update_fields=` |
| `DEFAULT_AUTO_FIELD` defaults to `BigAutoField` | 6.0 | Set the old value explicitly only for existing tables |
| `Prefetch.get_current_queryset()` / `get_prefetch_queryset()` removed | 6.0 | Only affects custom prefetch code; check the 6.0 notes |
| `select_related()` without arguments deprecated | 6.1 | Name the relations |
| `values_list(flat=True)` without a field deprecated | 6.1 | Pass the field |
| `transaction.savepoint()` deprecated | 6.1 | `savepoint_create()` |
| Annotation, table and join aliases are quoted | 6.1 | Review raw SQL that references aliases |
| `ArrayAgg`, `JSONBAgg`, `StringAgg` `ordering=` removed | 6.1 | `order_by=` |
| `BitAnd`, `BitOr`, `BitXor` available on all backends | 6.1 | Import from `django.db.models`; the `postgres.aggregates` names are deprecated |

Read the full backwards-incompatible list in the release notes before each upgrade: https://github.com/django/django/tree/main/docs/releases
