---
name: django-expert
description: >-
  Builds, reviews and deploys Django 6.x projects: models and migrations, QuerySet tuning and N+1 fixes, transactions, async views, forms, admin, custom user and permissions, Django REST Framework, the built-in Tasks framework, CSP and security settings, WhiteNoise, ASGI deployment and testing. Use when editing models.py, views.py, urls.py, admin.py, settings.py, migrations, serializers.py or conftest.py, or running manage.py, makemigrations, migrate, check --deploy, gunicorn, uvicorn or pytest-django. Not for FastAPI services (use fastapi-expert), general Python tooling (use python-expert), PostgreSQL server tuning (use postgresql-expert), or REST resource design (use rest-api-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Django Expert

This skill covers application work on Django 6.0 and 6.1 (and the 5.2 LTS line): project layout, settings per environment, models, migrations, the ORM and its query cost, transactions, sync and async views, forms, admin, authentication, Django REST Framework, background tasks, caching, security settings, static files, deployment and tests. FastAPI, general Python packaging, database server tuning and HTTP API design belong to sibling skills.

> Verified against Django 6.1.2 (installed and run locally on Python 3.13; 6.1 release notes, 6.0 release notes and 6.2 development notes read on GitHub), Django REST Framework 3.18.3, django-ninja 1.7.3, pytest-django 4.14.0, pytest-asyncio 1.4.1, factory_boy 3.3.3, WhiteNoise 6.12.0, gunicorn 26.2.0, uvicorn 0.54.0, Celery 5.6.3 (2026-10).

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

- Covered: `django-admin` and `manage.py`, settings and environment config, apps, models, constraints and indexes, migrations (schema, data, squashing, zero-downtime rules), QuerySet API, transactions, async views and the async ORM, class-based and function views, forms and ModelForms, admin, auth and permissions, DRF and django-ninja, signals, caching, the `django.tasks` framework, security settings and `check --deploy`, WhiteNoise, gunicorn and uvicorn, TestCase, pytest-django, factory_boy.
- Not covered: FastAPI and Pydantic-first services (fastapi-expert); Python packaging, typing and uv (python-expert); PostgreSQL indexes, vacuum and query plans beyond what the ORM emits (postgresql-expert); resource modelling, status codes and versioning policy (rest-api-expert); cache server operation (redis-expert); container images (docker-expert); generic authentication design (authentication-expert, authorization-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Releases | Django 6.1 shipped 2026-08-05 (6.1.3 listed in the release index); Python 3.12 to 3.14 (3.15 from 6.1.3). 6.0 is the previous feature release (6.0.10 listed). 5.2 is the current LTS with support to April 2028. 6.2 is the next LTS, in development, expected April 2027. Check djangoproject.com/download for the live support table before choosing a target |
| 6.1 ORM | `QuerySet.fetch_mode()` with `FETCH_ONE` (default), `FETCH_PEERS` (one extra query for all instances of the same queryset) and `FETCH_RAISE` (raises `FieldFetchBlocked`); `on_delete=DB_CASCADE`, `DB_SET_NULL`, `DB_SET_DEFAULT` (SQL `ON DELETE`, no Python signals); `UUID4` and `UUID7` DB functions; `JSONNull`; `QuerySet.totally_ordered`. Deprecated: `select_related()` with no arguments, `values_list(flat=True)` without a field, `transaction.savepoint()` (use `savepoint_create()`) |
| 6.0 changes | `DEFAULT_AUTO_FIELD` defaults to `BigAutoField`; built-in Tasks framework (`django.tasks`); Content Security Policy support; template partials (`{% partialdef %}`, `{% partial %}`); `CheckConstraint(condition=...)` only (the `check` keyword was removed); `StringAgg` and `AnyValue`; `Model.NotUpdated`; `AsyncPaginator`; modern `email.message.EmailMessage` API |
| Tasks | `from django.tasks import task`; `@task` function, `.enqueue(*args, **kwargs)` returns a `TaskResult`; options `priority`, `queue_name`, `backend`, `takes_context`; `.using(run_after=...)`. Configured by `TASKS`. Built-in backends are `ImmediateBackend` (the default, runs inline) and `DummyBackend` (stores results, runs nothing). Django ships no worker and no durable backend; production needs a third-party backend or Celery. Arguments and return values must be JSON-serializable |
| CSP | Built in since 6.0: `django.middleware.csp.ContentSecurityPolicyMiddleware`, settings `SECURE_CSP` and `SECURE_CSP_REPORT_ONLY` (dicts of directive to list), constants in `django.utils.csp.CSP` (`SELF`, `NONE`, `NONCE`), context processor `django.template.context_processors.csp`. 6.1 adds the `csp_nonce_attr` template tag and system check `security.W027` |
| Mailers (6.1) | `MAILERS = {"default": {"BACKEND": ..., "OPTIONS": {...}}}` replaces `EMAIL_BACKEND` and the other `EMAIL_*` settings, which are deprecated (removal in 2028). `check --deploy` raises `mail.E001` when the `default` mailer is a development-only backend such as the console backend |
| Async | Views, middleware and signals may be `async`; ORM methods have `a`-prefixed variants (`aget`, `acreate`, `acount`, `aiterator`, ...) and `async for` works on querysets. Transactions do not work in async mode: wrap transactional code in a sync function and call it through `sync_to_async`. Under WSGI an async view runs in a one-off event loop |
| DRF 3.18 | Supports Django 5.2, 6.0 and 6.1 on Python 3.10+ (package metadata); 3.18.0 dropped Django 4.2, 5.0 and 5.1. Serializers, `ModelViewSet`, routers, permissions, throttling, pagination (`PageNumberPagination`, `LimitOffsetPagination`, `CursorPagination`), filtering via `django-filter` |
| Auth | Define a custom user model before the first migration (`AUTH_USER_MODEL`); it is very costly to change later. PBKDF2 default iterations are 1,500,000 in 6.1. Permissions are `app_label.codename`; `has_perm`, `@permission_required`, `PermissionRequiredMixin` |
| Testing | `TestCase` wraps each test in a transaction; `setUpTestData`, `assertNumQueries`, `captureOnCommitCallbacks(execute=True)`, `override_settings`, `Client` and `AsyncClient`. pytest-django adds `@pytest.mark.django_db`, `django_assert_num_queries`, `--reuse-db`. Async pytest tests need pytest-asyncio or anyio |

## 3. Workflow

1. Read `pyproject.toml` or `requirements*.txt`, `manage.py`, the settings module(s), `INSTALLED_APPS`, `AUTH_USER_MODEL`, the database engine and the CI config. Record the Django version in use; do not apply 6.1 features to a 5.2 project.
2. Run `python manage.py check` and `python manage.py makemigrations --check --dry-run` to see the baseline state before editing.
3. For a slow page, measure first: Django Debug Toolbar or `assertNumQueries` for query counts, `QuerySet.explain()` for plans, `connection.queries` in a shell with `DEBUG=True`.
4. Change models and write the migration in the same change; read the generated file and `sqlmigrate app 000N` output for anything that locks a large table.
5. Add a test that fails without the change: a `TestCase` or pytest-django test, using `assertNumQueries` for query-count fixes.
6. Run `manage.py check`, `makemigrations --check`, the tests, and for deploy changes `manage.py check --deploy` with production settings.
7. Report which commands ran, the Django version targeted, and any migration that needs a staged rollout.

## 4. Decision Rules

- If the project has no custom user model yet, create one (`AbstractUser` subclass, even if empty) before the first `migrate`; if it already has migrations on the default `auth.User`, changing is a data migration project and needs an explicit plan.
- If a template loop touches a related object, add `select_related` (forward FK or one-to-one) or `prefetch_related` (reverse FK, many-to-many); on 6.1 `fetch_mode(FETCH_PEERS)` is a low-effort mitigation, and `FETCH_RAISE` is a guard in tests.
- If two writers can update the same row, use `F()` expressions for counters and `select_for_update()` inside `transaction.atomic()` for read-modify-write; do not rely on `save()` after a plain read.
- If a side effect (email, task enqueue, webhook) depends on a committed row, schedule it with `transaction.on_commit(...)`, not directly in the atomic block or a `post_save` handler.
- If work takes more than a request budget (seconds), run it as a task. With `django.tasks` choose a durable third-party backend; with Celery, keep the existing setup. `ImmediateBackend` is for development and tests only.
- If the API is a thin CRUD layer over models, use DRF `ModelViewSet` with a router; if you want type-hint-driven schemas and OpenAPI with less code, django-ninja is an option; for a mixed HTML site use plain Django views.
- If a view is mostly I/O to other services, use `async def` under ASGI; if it uses the ORM transactionally or relies on sync-only libraries, keep it sync.
- If a signal would implement core business logic, call a service function from the view or model method instead; keep signals for decoupled reactions in other apps.
- If the schema change drops, renames or retypes a column used by running code, split it into deploy steps (see [references/migrations.md](references/migrations.md)).
- If you serve static files without a CDN or nginx, use WhiteNoise; if you need user uploads in production, use object storage via `STORAGES`.

## 5. Coding Standards

- Follow the Django coding style (PEP 8, ruff or black formatting as configured in the repository). Models are singular `PascalCase`; `related_name` is plural and explicit on every FK and M2M.
- Order model contents: fields, custom managers, `Meta`, `__str__`, `save`/`clean`, `get_absolute_url`, other methods.
- Declare `Meta.constraints` (`CheckConstraint(condition=...)`, `UniqueConstraint`) and `Meta.indexes` for rules the database must enforce; do not rely on `clean()` alone.
- Use `settings.AUTH_USER_MODEL` in ForeignKeys and `get_user_model()` in code; never import `django.contrib.auth.models.User` directly.
- Keep views thin: parse input, call a service or model method, return a response. Put multi-model business logic in `services.py` functions or model methods, not in views, forms or signals.
- URLs: `path()` with named routes, `app_name` namespaces, and `reverse()` or `{% url %}`; no hardcoded paths.
- Use `TextChoices` and `IntegerChoices` for enumerated fields. Use `timezone.now()` with `USE_TZ = True`.
- Import settings through `from django.conf import settings`; never `import config.settings`.
- Never edit an applied migration; add a new one. Commit migrations with the model change.
- Do not use `null=True` on string fields (use `blank=True`, empty string); do use `null=True` on non-string optional fields.

## 6. Project Structure

```text
shop-project/
|-- manage.py
|-- pyproject.toml
|-- config/                  # project package: settings, urls, asgi, wsgi
|   |-- settings/
|   |   |-- __init__.py
|   |   |-- base.py          # shared, reads env vars
|   |   |-- local.py         # DEBUG, console mail, debug toolbar
|   |   |-- prod.py          # SECURE_* and cookie flags
|   |   `-- test.py          # fast hasher, in-memory cache
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- accounts/                # custom user model lives here from day one
|   |-- models.py
|   `-- migrations/
|-- shop/                    # one app per bounded feature
|   |-- models.py
|   |-- services.py          # business operations
|   |-- selectors.py         # read queries (optional)
|   |-- views.py
|   |-- forms.py
|   |-- admin.py
|   |-- api.py               # DRF serializers and viewsets
|   |-- tasks.py             # django.tasks or Celery tasks
|   |-- signals.py
|   |-- migrations/
|   `-- tests/
|       |-- factories.py
|       `-- test_models.py
`-- templates/
```

- Select the settings module with `DJANGO_SETTINGS_MODULE` (for example `config.settings.prod`), set in `manage.py`, `asgi.py` and the process environment, not by editing files per host.
- Register signals in `AppConfig.ready()` by importing `signals`, and use the full `AppConfig` path in `INSTALLED_APPS` only when a custom config exists.
- Keep apps small and acyclic; if two apps import each other, extract the shared piece or reference models by string (`"shop.Product"`).

## 7. Design Patterns

- **Service functions**: `def place_order(*, user, items) -> Order` in `services.py`, decorated with `@transaction.atomic`, called by views, DRF actions and tasks alike. Cost: one more layer; benefit: one place to test and to schedule `on_commit` work.
- **Custom QuerySet methods**: `class ProductQuerySet(models.QuerySet): def in_stock(self): ...` with `objects = ProductQuerySet.as_manager()`. Chainable and reusable; prefer over manager-only methods.
- **Custom user from day one**: `class User(AbstractUser): pass` in `accounts`, `AUTH_USER_MODEL = "accounts.User"`, before any migration runs. Log in with email by overriding `USERNAME_FIELD` and a manager when required.
- **ModelForm plus form-level validation**: `clean_<field>()` for one field, `clean()` for cross-field rules; model constraints stay the final guard.
- **Admin as an internal tool**: `list_display`, `list_select_related`, `search_fields`, `readonly_fields`, `autocomplete_fields` and `raw_id_fields` for large FKs, `@admin.action` for bulk actions; override `get_queryset` to avoid per-row queries. Limit admin access by permission and network.
- **Signals sparingly**: `post_save` and `m2m_changed` receivers hide control flow, are skipped by `bulk_create`, `update()` and `DB_CASCADE`, and run inside the caller's transaction. Use them for cross-app notification, not core logic.
- **Tasks via on_commit**: `transaction.on_commit(lambda: send_receipt.enqueue(order_id=order.pk))`. The task receives an id, not a model instance, and reloads it.
- **Caching layers**: per-view `cache_page`, template fragment `{% cache %}`, low-level `cache.get_or_set(key, callable, timeout)`; version or prefix keys, and invalidate on write. Use a shared backend (Redis, Memcached) in multi-process deployments; `LocMemCache` is per process.
- **Template partials (6.0+)**: `{% partialdef card %}...{% endpartialdef %}` and `render(request, "page.html#card", ctx)` for HTMX-style fragment responses.
- **Thin DRF layer**: serializers validate and shape data; the viewset calls a service. See [references/drf-apis.md](references/drf-apis.md).

## 8. Best Practices

- Configure through environment variables read in `base.py`; fail at startup (`ImproperlyConfigured`) when `DJANGO_SECRET_KEY` is missing. See [references/security-deployment.md](references/security-deployment.md).
- Set `DEFAULT_AUTO_FIELD` explicitly in `AppConfig` or settings if the project supports Django older than 6.0.
- Prefer `Model.objects.filter(...).exists()` to `len(qs)` or `if qs:` for presence, `.count()` for a number, and `values_list("id", flat=True)` for id lists.
- Use `get_object_or_404`, `update_fields=[...]` on partial `save()`, `bulk_create`/`bulk_update` for batches, and `iterator(chunk_size=...)` for large scans.
- Keep `DEBUG = False` outside local; log through `LOGGING` to stdout with `django.request` and `django.security` loggers at WARNING or above.
- Run `python manage.py check --deploy` in CI against the production settings module.
- Pin Django to a minor series (`>=6.1,<6.2`) and upgrade by running tests with `python -W error::DeprecationWarning` (Django emits `RemovedInDjangoXXWarning`) one release ahead.
- Use `AppConfig.ready()` only for registration, not for queries.
- Use `django-environ` or plain `os.environ`; do not commit `.env` files with real values.

## 9. Performance

- Count queries before tuning: one list page should issue a small constant number of queries independent of row count. Lock this in with `assertNumQueries`.
- N+1 fixes: `select_related("fk")` joins forward FK and one-to-one; `prefetch_related("reverse_set")` issues one extra query per relation and supports `Prefetch(..., queryset=..., to_attr=...)`; `fetch_mode(FETCH_PEERS)` (6.1) batches lazy loads for all peers of an instance.
- Reduce columns with `only()`/`defer()` or `values()`/`values_list()` when full instances are not needed; do not defer a column that the template later reads.
- Push work into the database: `annotate(Count(...), Sum(...))`, `Exists()`, `Subquery(OuterRef())`, `F()` arithmetic, `Case/When`, window functions; avoid Python loops that call the ORM per row.
- Batch writes: `bulk_create(batch_size=...)`, `bulk_update(objs, fields, batch_size=...)`, `QuerySet.update()`; none of these call `save()` or send per-object signals.
- Paginate always; for large tables use `CursorPagination` (DRF) or keyset filters, since `OFFSET` cost grows with the page number.
- Index what you filter and order by (`Meta.indexes`, `db_index=True`, composite indexes matching the `WHERE` then `ORDER BY`); check with `explain()`. Server-side index design: postgresql-expert.
- Reuse connections: `CONN_MAX_AGE` (for example 60) with `CONN_HEALTH_CHECKS = True`, or a pooler. With ASGI and threads, count total connections as processes x threads.
- Cache expensive, read-heavy fragments; measure hit rate; cache invalidation is part of the design.
- Do not enable Django Debug Toolbar or `DEBUG = True` when benchmarking; `DEBUG` retains every SQL string in memory.

## 10. Security

- Run `python manage.py check --deploy` with production settings and resolve every warning (`security.W004` HSTS, `W008` SSL redirect, `W009` secret key, `W012` and `W016` secure cookies, `W018` DEBUG, `W020` ALLOWED_HOSTS).
- Production flags: `DEBUG = False`, strong `SECRET_KEY` from the environment, explicit `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_PROXY_SSL_HEADER` only when a trusted proxy sets and strips that header.
- `CSRF_TRUSTED_ORIGINS` must list full origins with scheme (`https://app.example.com`). Keep `CsrfViewMiddleware` on; never `@csrf_exempt` a cookie-authenticated view.
- Enable CSP (6.0+) with `ContentSecurityPolicyMiddleware`, start in `SECURE_CSP_REPORT_ONLY`, use nonces (`CSP.NONCE` plus the `csp` context processor) instead of `'unsafe-inline'`.
- The ORM parameterises queries. When using `raw()`, `extra()`, `RawSQL` or `cursor.execute()`, pass values as parameters (`cursor.execute("... WHERE id = %s", [pk])`) and never format strings into SQL. Column aliases passed to `annotate`/`values` must not come from user input.
- Templates auto-escape; mark strings safe (`mark_safe`, `|safe`) only for content built with `format_html`. Use `json_script` to pass data to JavaScript.
- Validate uploads: restrict extensions and size (`DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE`), store outside the static root, serve through object storage or an authenticated view, never trust `content_type`.
- Passwords: keep the default PBKDF2 hasher or add `argon2` (`pip install django[argon2]`) first in `PASSWORD_HASHERS`; keep `AUTH_PASSWORD_VALIDATORS` enabled. Add rate limiting on login (DRF throttling, a proxy, or a package such as django-axes).
- Restrict the admin: strong auth, MFA via a package or SSO, unguessable or network-restricted URL, staff accounts with minimal permissions.
- Keep dependencies patched: Django publishes security fixes for supported series only; subscribe to the django-announce list and upgrade patch releases promptly.
- Redirects: validate `next` parameters with `url_has_allowed_host_and_scheme`. Deserialization: never `pickle` session or cache data from untrusted sources; the default JSON session serializer is safe.

## 11. Testing

- `django.test.TestCase` for most tests (per-test transaction, fast); `TransactionTestCase` only when testing `on_commit` behaviour against real commits or transaction semantics; `SimpleTestCase` when no database is used.
- Use `setUpTestData` for class-level fixtures and `factory_boy` factories (`DjangoModelFactory`) rather than JSON fixtures.
- Assert behaviour and cost: `self.assertNumQueries(n)`, `self.assertContains(response, ...)`, `self.assertRedirects(...)`, `self.assertTemplateUsed(...)`, `with self.captureOnCommitCallbacks(execute=True) as callbacks:` for `on_commit` hooks.
- pytest-django: set `DJANGO_SETTINGS_MODULE` in `pytest.ini` or `pyproject.toml`, mark DB tests with `@pytest.mark.django_db`, use `client`, `admin_client`, `django_assert_num_queries`, `settings` fixtures; add `--reuse-db` locally and `--create-db` after migration changes.
- Test the API with `rest_framework.test.APIClient` and `force_authenticate`; test permissions for anonymous, wrong-user and right-user cases.
- Test migrations: `makemigrations --check --dry-run` in CI; for data migrations, a test that applies `MigrationExecutor` to the earlier state, loads rows, then migrates forward.
- Use the 6.0+ in-memory `ImmediateBackend` default for tasks in tests, or `DummyBackend` and assert on enqueued results.
- Details and runnable setups: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Model changes include a migration, committed together; `makemigrations --check` is clean.
- [ ] The migration is safe for a running deployment (no long lock, no destructive step before code stops using the column).
- [ ] Custom user model is in place; FKs use `settings.AUTH_USER_MODEL`.
- [ ] No N+1: list views and serializers use `select_related`/`prefetch_related`, covered by `assertNumQueries`.
- [ ] Read-modify-write paths use `F()`, `select_for_update()` or constraints, inside `transaction.atomic()`.
- [ ] Side effects that depend on commit use `transaction.on_commit`.
- [ ] No raw SQL built from user input; no `mark_safe` on user data; no `@csrf_exempt` on session-authenticated views.
- [ ] DRF views set explicit `permission_classes`, pagination and throttles; serializers list fields explicitly (no `__all__` on writable models).
- [ ] Production settings pass `manage.py check --deploy`; secrets come from the environment.
- [ ] Async code does not call sync ORM or blocking I/O directly; transactions run in sync code.
- [ ] Tests cover success, validation failure and permission failure.

## 13. Production Notes

- Serve with gunicorn (WSGI) for sync apps, or gunicorn with `uvicorn_worker.UvicornWorker` (package `uvicorn-worker`) or uvicorn directly (ASGI) for async. The `uvicorn.workers` module is deprecated in uvicorn 0.54 in favour of the `uvicorn-worker` package. Run `collectstatic` at build time.
- Worker sizing starts around `2 x cores + 1` for sync gunicorn workers; measure. Each process holds its own DB connections, so size `max_connections` or add a pooler (PgBouncer) accordingly.
- Run migrations as a separate release step before starting new code (`manage.py migrate --noinput`); gate the deploy with `manage.py migrate --check` in the new image. Do not run migrations from every replica at start-up.
- Health checks: a lightweight view that checks the database (`connection.ensure_connection()`), not one that renders templates.
- Behind a proxy or load balancer set `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST` only if needed, and make the proxy overwrite client-supplied forwarded headers.
- Logging: JSON or key-value logs to stdout; send errors to a tracker; scrub `SENSITIVE_VARIABLES` with `sensitive_variables` and `sensitive_post_parameters` decorators.
- Background work: with `django.tasks`, install and configure a third-party backend that persists and runs a worker, because the built-in backends do not. Celery 5.x remains a mature choice for retries, schedules and workflows. Keep tasks idempotent and pass ids.
- Email: on 6.1 configure `MAILERS` (the `EMAIL_*` settings still work but are deprecated); `mail.E001` blocks deploy checks with a console backend as `default`.
- Upgrades: step through feature releases (5.2 to 6.0 to 6.1), read each release's "Backwards incompatible changes", run tests with deprecation warnings as errors, and update third-party packages first. 6.1 changes cache keys for varied pages and template fragments, so expect a cold cache after upgrading.
- Backups, point-in-time recovery and connection tuning are database-side concerns (postgresql-expert).

## 14. Examples

Models with constraints, an explicit `related_name`, and a chainable QuerySet (Django 6.0+, verified on 6.1.2):

```python
from django.conf import settings
from django.db import models
from django.db.models import Q


class ProductQuerySet(models.QuerySet):
    def in_stock(self):
        return self.filter(stock__gt=0)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)
    price_cents = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.CheckConstraint(condition=Q(price_cents__gt=0), name="product_price_positive"),
        ]
        indexes = [models.Index(fields=["category", "-created"])]
```

A service function that locks the row, updates stock atomically and enqueues a task after commit:

```python
from django.db import transaction
from django.tasks import task


@task
def send_receipt(order_id: int) -> None:
    ...  # reload the order by id and send the message


@transaction.atomic
def reserve(product_id: int, qty: int, order_id: int) -> None:
    product = Product.objects.select_for_update().get(pk=product_id)
    if product.stock < qty:
        raise ValueError("insufficient stock")
    Product.objects.filter(pk=product.pk).update(stock=models.F("stock") - qty)
    transaction.on_commit(lambda: send_receipt.enqueue(order_id=order_id))
```

Query-count test (a plain lazy loop costs 1 + N queries; `select_related` costs 1; `fetch_mode(FETCH_PEERS)` costs 2):

```python
from django.db.models import FETCH_PEERS
from django.test import TestCase


class ProductQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name="a")
        Product.objects.bulk_create(
            [Product(category=cat, name=f"p{i}", price_cents=100) for i in range(5)]
        )

    def test_list_uses_join(self):
        with self.assertNumQueries(1):
            [p.category.name for p in Product.objects.select_related("category")]

    def test_peers_batches(self):
        with self.assertNumQueries(2):
            [p.category.name for p in Product.objects.fetch_mode(FETCH_PEERS)]
```

An async view using the async ORM (works under ASGI; under WSGI it runs in a one-off loop):

```python
from django.http import JsonResponse


async def product_summary(request):
    names = [p.name async for p in Product.objects.in_stock().select_related("category")[:5]]
    total = await Product.objects.acount()
    return JsonResponse({"names": names, "total": total})
```

More worked snippets: [references/orm-and-queries.md](references/orm-and-queries.md), [references/migrations.md](references/migrations.md), [references/drf-apis.md](references/drf-apis.md).

## 15. Common Mistakes

- **Using the default `User` and switching later**: changing `AUTH_USER_MODEL` after migrations exist breaks FKs and the migration graph. Create a custom user first.
- **N+1 in serializers and templates**: a nested serializer or `{{ order.customer.name }}` in a loop issues one query per row. Add `select_related`/`prefetch_related` in `get_queryset()`.
- **`select_related()` with no arguments**: deprecated in 6.1 and follows every non-null FK. Name the relations.
- **Doing side effects in `post_save` or inside `atomic`**: the task or email may run before commit, or for a rolled-back row. Use `transaction.on_commit`.
- **Relying on `save()` signals with bulk operations**: `bulk_create`, `bulk_update`, `update()`, `delete()` on querysets with `DB_CASCADE` skip `save()` and sometimes signals.
- **Read-modify-write without a lock**: `obj.count += 1; obj.save()` loses updates. Use `F("count") + 1` or `select_for_update()`.
- **Editing or deleting an applied migration**: other environments diverge. Add a corrective migration; squash only after every environment has migrated.
- **Adding a NOT NULL column without a default, or renaming a column, in one step on a live table**: old code breaks or the table locks. Use the staged approach in the migrations reference.
- **`ModelSerializer` with `fields = "__all__"`**: new model fields become API fields automatically, including sensitive ones. List fields.
- **Treating `ImmediateBackend` as production**: it runs the task inline in the request. Configure a durable backend or Celery.
- **Calling the sync ORM from `async def`**: raises `SynchronousOnlyOperation`. Use `a`-methods, `async for`, or `sync_to_async`; do not set `DJANGO_ALLOW_ASYNC_UNSAFE` in production.
- **`transaction.atomic()` in async code**: transactions do not work in async mode. Put the transaction in a sync function and call it with `sync_to_async`.
- **`ALLOWED_HOSTS = ["*"]` or `DEBUG = True` in production**: host-header attacks and information leaks. Set explicit hosts; `check --deploy` flags both.
- **Storing secrets in `settings.py`**: read from the environment; rotate if committed.
- **`LocMemCache` with several processes**: each worker has its own copy, so invalidation does not propagate. Use Redis or Memcached.
- **`@csrf_exempt` to "fix" a 403**: set `CSRF_TRUSTED_ORIGINS` with scheme and send the token instead.
- **Forgetting `-W error` upgrades**: deprecated APIs (`transaction.savepoint()`, `values_list(flat=True)` with no field, `EMAIL_*` settings) are removed on schedule.

## 16. References

- [references/orm-and-queries.md](references/orm-and-queries.md): QuerySet API, N+1 patterns, annotate and subqueries, F and Q, bulk operations, iterator, transactions and locking, on_commit, async ORM, 6.1 fetch modes.
- [references/migrations.md](references/migrations.md): makemigrations and migrate flow, data migrations, squashing, zero-downtime rules per operation, PostgreSQL concurrent index operations, custom user model setup.
- [references/drf-apis.md](references/drf-apis.md): serializers, viewsets and routers, permissions, throttling, pagination, filtering, error handling, versions, django-ninja comparison.
- [references/security-deployment.md](references/security-deployment.md): settings split, environment config, SECURE_* settings, CSRF, CSP, check --deploy, WhiteNoise, gunicorn and uvicorn, tasks framework, caching.
- [references/testing.md](references/testing.md): TestCase patterns, assertNumQueries, pytest-django configuration, factory_boy, async tests, API tests, migration tests.
- Django documentation: https://docs.djangoproject.com/en/stable/ and release notes https://docs.djangoproject.com/en/stable/releases/
- Django source and release notes: https://github.com/django/django/tree/main/docs/releases
- Django REST Framework: https://www.django-rest-framework.org/ ; django-ninja: https://django-ninja.dev/
- pytest-django: https://pytest-django.readthedocs.io/ ; factory_boy: https://factoryboy.readthedocs.io/
- WhiteNoise: https://whitenoise.readthedocs.io/ ; Celery: https://docs.celeryq.dev/
