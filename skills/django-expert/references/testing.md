# Testing Django Projects

Test structure for Django 6.x with the built-in test runner and with pytest-django 4.14.0: database handling, factories, query-count assertions, `on_commit` and task testing, async tests, API tests and migration tests. Snippets were run on Django 6.1.2, pytest 9.2.0, pytest-asyncio 1.4.1 and factory_boy 3.3.3 (2026-10).

## Contents

1. [Choosing a runner](#1-choosing-a-runner)
2. [Built-in TestCase patterns](#2-built-in-testcase-patterns)
3. [pytest-django setup](#3-pytest-django-setup)
4. [Factories with factory_boy](#4-factories-with-factory_boy)
5. [Query-count tests](#5-query-count-tests)
6. [Transactions, on_commit and tasks](#6-transactions-on_commit-and-tasks)
7. [Async tests](#7-async-tests)
8. [API tests](#8-api-tests)
9. [Migration tests](#9-migration-tests)
10. [Speed and CI](#10-speed-and-ci)

## 1. Choosing a runner

- `python manage.py test` (unittest-based) needs no extra packages and understands `--parallel`, `--keepdb`, `--tag`, `--shuffle`, `--debug-sql`.
- pytest with pytest-django gives fixtures, parametrization and plugins; it is the common choice for larger projects. Do not mix runners in one CI job without a reason.
- Use PostgreSQL in CI if production is PostgreSQL; SQLite hides differences in locking, JSON, constraints, `DISTINCT ON`, `select_for_update` and index behaviour.

## 2. Built-in TestCase patterns

| Class | Use |
|---|---|
| `SimpleTestCase` | No database; template, URL and form logic |
| `TestCase` | Default; each test runs in a transaction that is rolled back; `setUpTestData` runs once per class |
| `TransactionTestCase` | Real commits and flushes tables; needed to test `on_commit` against a real commit or database-level concurrency; slower |
| `LiveServerTestCase` | Real HTTP server for Selenium or Playwright (e2e-testing-expert) |

```python
from django.test import TestCase, override_settings
from django.urls import reverse

class ProductListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="a")
        Product.objects.bulk_create(
            [Product(category=cls.cat, name=f"p{i}", price_cents=100) for i in range(5)]
        )

    def test_lists_products(self):
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "p0")

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_with_setting(self):
        ...
```

- `setUpTestData` objects are shared and wrapped so mutations in one test do not leak (since 3.2); reload with `refresh_from_db()` if you rely on fresh state.

## 3. pytest-django setup

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py
addopts = --reuse-db --strict-markers
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

- The same keys can live in `pyproject.toml` under pytest's configuration table; check the pytest and pytest-django docs for the spelling your pytest version expects.
- Mark database access: `@pytest.mark.django_db` (function or class), or request the `db` fixture. Tests without it that touch the database fail, which keeps pure tests fast.
- `--reuse-db` keeps the test database between runs; `--create-db` forces a rebuild (use after migration changes); `--no-migrations` skips migrations and builds tables from models (fast, but hides migration bugs; run the migrations once in CI).
- Fixtures: `client`, `async_client`, `rf` (RequestFactory), `admin_client`, `admin_user`, `django_user_model`, `settings` (temporary setting overrides), `transactional_db`, `django_assert_num_queries`, `django_assert_max_num_queries`, `mailoutbox`, `live_server`.
- Shared fixtures go in `conftest.py`:

```python
import pytest

from shop.factories import ProductFactory

@pytest.fixture
def product(db):
    return ProductFactory()
```

## 4. Factories with factory_boy

```python
import factory
from factory.django import DjangoModelFactory

from .models import Category, Product

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"category-{n}")

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    category = factory.SubFactory(CategoryFactory)
    name = factory.Faker("word")
    price_cents = factory.Faker("random_int", min=1, max=10_000)
    stock = 5
```

- `ProductFactory()` saves; `ProductFactory.build()` does not; `create_batch(n, **overrides)` makes many.
- Prefer a factory per model with sensible defaults, and override only what a test cares about. `SubFactory` builds required relations; `factory.post_generation` handles many-to-many.

## 5. Query-count tests

```python
from django.db.models import FETCH_PEERS
from django.test import TestCase

class QueryCountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ProductFactory.create_batch(5)

    def test_n_plus_one_documented(self):
        with self.assertNumQueries(6):                    # 1 + 5
            [p.category.name for p in Product.objects.all()]

    def test_select_related(self):
        with self.assertNumQueries(1):
            [p.category.name for p in Product.objects.select_related("category")]

    def test_fetch_peers(self):                           # Django 6.1+
        with self.assertNumQueries(2):
            [p.category.name for p in Product.objects.fetch_mode(FETCH_PEERS)]
```

- pytest: `with django_assert_num_queries(1): ...` and `django_assert_max_num_queries(n)`.
- `fetch_mode(FETCH_RAISE)` in a test turns any unexpected lazy load into `FieldFetchBlocked` (6.1).

## 6. Transactions, on_commit and tasks

```python
from django.db import transaction
from django.tasks import TaskResultStatus, default_task_backend
from django.test import TestCase, override_settings

DUMMY = {"default": {"BACKEND": "django.tasks.backends.dummy.DummyBackend"}}

class ReserveTests(TestCase):
    @override_settings(TASKS=DUMMY)
    def test_enqueues_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            reserve(product_id=self.product.pk, qty=1, order_id=7)
        self.assertEqual(len(callbacks), 1)
        [result] = default_task_backend.results
        self.assertEqual(result.status, TaskResultStatus.READY)
        self.assertEqual(result.kwargs, {"order_id": 7})

    def test_runs_inline_with_default_backend(self):
        result = send_receipt.enqueue(order_id=2)         # ImmediateBackend is the default
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
```

- In a plain `TestCase`, `on_commit` callbacks never run because the outer transaction is rolled back; `captureOnCommitCallbacks(execute=True)` collects and runs them.
- `TransactionTestCase` (or `@pytest.mark.django_db(transaction=True)`) exercises real commits; use it for locking and concurrency tests with threads, on PostgreSQL.
- To test `select_for_update` and races, use two connections in threads under `TransactionTestCase`, or assert on the generated SQL; SQLite ignores row locks.
- Keep task functions importable and test their body directly (`send_receipt.call(order_id=1)` runs the function without a backend).

## 7. Async tests

- Django's `TestCase` supports `async def test_...` methods; the client has an async twin (`AsyncClient`, `await client.get(...)`, `await client.aforce_login(user)`).
- pytest-django async tests require an async plugin: install pytest-asyncio (set `asyncio_mode` and `asyncio_default_fixture_loop_scope` explicitly, otherwise the plugin warns) or anyio. Without one, pytest fails with "async def functions are not natively supported".

```python
import pytest
from django.test import AsyncClient, AsyncRequestFactory

@pytest.mark.django_db
async def test_async_orm():
    cat = await Category.objects.acreate(name="z")
    await Product.objects.acreate(category=cat, name="n", price_cents=5)
    response = await product_summary(AsyncRequestFactory().get("/"))
    assert response.status_code == 200

@pytest.mark.django_db(transaction=True)
async def test_async_client(admin_user):
    client = AsyncClient()
    await client.aforce_login(admin_user)
    assert (await client.get("/admin/")).status_code == 200
```

- With an in-memory SQLite database, an `AsyncClient` request that runs ORM calls in worker threads raised "database table is locked" in a plain `django_db` test; `transaction=True` fixed it. Use PostgreSQL in CI to avoid SQLite threading quirks.
- Never wrap `transaction.atomic()` around `await` calls in tests; put transactional code in a sync function.

## 8. API tests

```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_anonymous_cannot_write():
    assert APIClient().post("/api/products/", {}, format="json").status_code in (401, 403)

@pytest.mark.django_db
def test_user_sees_only_own_orders(django_user_model):
    alice = django_user_model.objects.create_user("alice", password="pw-for-tests")
    bob = django_user_model.objects.create_user("bob", password="pw-for-tests")
    OrderFactory(owner=bob)
    client = APIClient()
    client.force_authenticate(alice)
    assert client.get("/api/orders/").json()["results"] == []
```

- Cover anonymous, wrong user, right user, staff, validation errors (400), missing objects (404) and throttled (429, with `override_settings` for a tiny rate and a cleared cache).
- Run one end-to-end authentication test without `force_authenticate`.

## 9. Migration tests

```python
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

class BackfillSkuTests(TransactionTestCase):
    migrate_from = [("shop", "0004_add_product_sku")]
    migrate_to = [("shop", "0005_backfill_sku")]

    def test_backfill(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        Product = old_apps.get_model("shop", "Product")
        cat = old_apps.get_model("shop", "Category").objects.create(name="c")
        p = Product.objects.create(category=cat, name="n", price_cents=5, sku=None)

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        self.assertEqual(new_apps.get_model("shop", "Product").objects.get(pk=p.pk).sku, f"P-{p.pk}")
```

- In CI also run `makemigrations --check --dry-run` and a clean `migrate` on an empty database.

## 10. Speed and CI

- Parallelize: `python manage.py test --parallel` or `pytest -n auto` (pytest-xdist; each worker gets its own database).
- Use a fast password hasher in `settings/test.py` (tests only) and `locmem` cache; avoid disk-bound storage with `InMemoryStorage` or `tmp_path`.
- CI order: `ruff` (or the configured linter), `manage.py check`, `makemigrations --check --dry-run`, tests with coverage, `check --deploy` with the production settings module.
