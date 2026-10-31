# Settings, Security, Deployment, Tasks and Caching

Environment-driven settings, the production security settings and `check --deploy`, built-in CSP, WhiteNoise, gunicorn and uvicorn, the `django.tasks` framework and caching. The settings example passed `manage.py check --deploy` on Django 6.1.2 with one remaining optional warning (`security.W021`, HSTS preload) and gunicorn 26.2.0 with `uvicorn_worker.UvicornWorker` served a request (2026-10).

## Contents

1. [Settings split and environment config](#1-settings-split-and-environment-config)
2. [Production security settings](#2-production-security-settings)
3. [Content Security Policy](#3-content-security-policy)
4. [Static files with WhiteNoise](#4-static-files-with-whitenoise)
5. [Servers: gunicorn and uvicorn](#5-servers-gunicorn-and-uvicorn)
6. [Background tasks](#6-background-tasks)
7. [Caching](#7-caching)
8. [Email, logging and health checks](#8-email-logging-and-health-checks)
9. [Release checklist](#9-release-checklist)

## 1. Settings split and environment config

```python
# config/settings/base.py
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Set the {name} environment variable")
    return value


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": env("POSTGRES_DB", "app"),
    "USER": env("POSTGRES_USER", "app"),
    "PASSWORD": env("POSTGRES_PASSWORD", ""),
    "HOST": env("POSTGRES_HOST", "localhost"),
    "CONN_MAX_AGE": 60,
    "CONN_HEALTH_CHECKS": True,
}}
```

```python
# config/settings/prod.py
from .base import *  # noqa: F403

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

- `base.py` holds the defaults safe for every environment: `DEBUG = False`, no default secret, hosts from the environment. `local.py` sets `DEBUG = True`, a throwaway key and console mail; `prod.py` adds the transport flags above; `test.py` can use `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]` for speed (tests only) and a `locmem` cache.
- Select the module through `DJANGO_SETTINGS_MODULE`. Set it in `manage.py`, `asgi.py` and `wsgi.py` as a default for development, and override in the process environment in production.
- Keep secrets in the platform secret store, not in the image or repository; rotate `SECRET_KEY` with `SECRET_KEY_FALLBACKS` (list of old keys) to keep sessions valid during rotation.
- Production `DATABASES` should use `psycopg` 3 (`pip install "psycopg[binary]"` or the source build) with `CONN_MAX_AGE` and health checks, or a pooler.

## 2. Production security settings

Run `python manage.py check --deploy` against the production module. Each warning names a setting:

| Check | Setting |
|---|---|
| `security.W004` | `SECURE_HSTS_SECONDS` (start with a small value, raise after verifying HTTPS everywhere) |
| `security.W008` | `SECURE_SSL_REDIRECT = True` |
| `security.W009` | `SECRET_KEY` long, random and not `django-insecure-...` |
| `security.W012` / `W016` | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| `security.W018` | `DEBUG = False` |
| `security.W020` | non-empty `ALLOWED_HOSTS` |
| `security.W021` | `SECURE_HSTS_PRELOAD = True` (only after reading the preload list requirements) |
| `security.W027` | related to CSP configuration (6.1) |
| `mail.E001` | `MAILERS["default"]` must not be a development backend (6.1) |

- Generate a key with `python -c "import secrets; print(secrets.token_urlsafe(60))"`.
- `SECURE_PROXY_SSL_HEADER` tells Django that the original request was HTTPS. Set it only when the proxy always overwrites the header; otherwise a client can spoof it.
- `SESSION_COOKIE_HTTPONLY` is on by default; `SESSION_COOKIE_SAMESITE` and `CSRF_COOKIE_SAMESITE` default to `"Lax"`. Keep Lax or Strict unless a cross-site flow requires otherwise.
- Defaults already on: `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY = "same-origin"`, `SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"`, `X_FRAME_OPTIONS = "DENY"` through `XFrameOptionsMiddleware`. Verify with `check --deploy` and response headers.
- CSRF: keep `CsrfViewMiddleware`; use `{% csrf_token %}` in forms; for fetch calls read the token from the cookie or a meta tag and send `X-CSRFToken`. Cross-origin form posts from other hosts need `CSRF_TRUSTED_ORIGINS` entries with a scheme (`https://app.example.com`).
- `ALLOWED_HOSTS` entries are hostnames (no scheme, no port); a leading dot matches subdomains. Avoid `"*"`.
- 6.1: signed cookies use an unambiguous salt; set `SIGNED_COOKIE_LEGACY_SALT_FALLBACK = True` temporarily only if existing signed cookies must keep working (the setting is deprecated).
- Sessions: the default database backend is fine; use `cached_db` or a cache backend for scale. Rotate session keys on login (the default) and call `logout()` on privilege change.

## 3. Content Security Policy

CSP support is built in since Django 6.0.

```python
# settings
from django.utils.csp import CSP

MIDDLEWARE += ["django.middleware.csp.ContentSecurityPolicyMiddleware"]
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "django.template.context_processors.csp",
]
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "object-src": [CSP.NONE],
}
# Start with SECURE_CSP_REPORT_ONLY = {...same shape...} and collect reports first.
```

```html
<script nonce="{{ csp_nonce }}">/* inline code allowed by nonce */</script>
```

- A request with the default admin login page returned `Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-...'; object-src 'none'` in a local test.
- Use `SECURE_CSP_REPORT_ONLY` first, add `report-uri` or `report-to` directives, then switch to enforcement.
- The `csp` context processor exposes `csp_nonce`; the nonce changes on every request, so cached pages that embed it break. 6.1 adds the `csp_nonce_attr` template tag and adds nonces to the admin and built-in templates when the context processor is configured.
- Avoid `'unsafe-inline'` and `'unsafe-eval'`; move inline handlers to scripts with nonces or external files.
- Per-view overrides: `csp_override` and `csp_report_only_override` in `django.views.decorators.csp`.

## 4. Static files with WhiteNoise

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # directly after SecurityMiddleware
    # ...
]
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
```

- Run `python manage.py collectstatic --noinput` in the image build. WhiteNoise 6.12 serves the collected files with compression and far-future cache headers for hashed names.
- The `STORAGES` setting replaced `STATICFILES_STORAGE` and `DEFAULT_FILE_STORAGE`; do not use the old names.
- Manifest storage raises on a missing static reference in templates (`ValueError: Missing staticfiles manifest entry`); run `collectstatic` before tests that render those templates, or use plain `StaticFilesStorage` in `test.py`.
- User uploads (`MEDIA`) do not belong in WhiteNoise; use object storage with a storage backend package and signed URLs, or an authenticated view.

## 5. Servers: gunicorn and uvicorn

```bash
# WSGI, sync views
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 30 --access-logfile -

# ASGI under gunicorn (pip install gunicorn uvicorn uvicorn-worker)
gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker --bind 0.0.0.0:8000 --workers 4

# ASGI directly
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

- Use ASGI when you have async views, WebSockets (through Channels) or streaming responses; plain sync apps run well on WSGI. An async view under WSGI runs in a one-off event loop and gains little.
- `uvicorn.workers` is deprecated in uvicorn 0.54; use the `uvicorn-worker` package (`uvicorn_worker.UvicornWorker`, `UvicornH11Worker`) with gunicorn for process management.
- Start with `2 x cores + 1` sync workers or one worker per core for ASGI, then load-test. Add `--max-requests` with jitter to bound memory growth. Total database connections are roughly workers times threads.
- Terminate TLS and buffer slow clients at a reverse proxy (nginx-expert); pass `X-Forwarded-Proto` and keep `SECURE_PROXY_SSL_HEADER` consistent.

## 6. Background tasks

Django 6.0 added `django.tasks`. It defines the API and backends contract; it does not include a worker or a durable queue.

```python
# settings
TASKS = {"default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}}
```

```python
# shop/tasks.py
from django.tasks import task


@task(priority=0, queue_name="default")
def send_receipt(order_id: int) -> str:
    ...
    return f"sent {order_id}"
```

```python
# in a service function
from django.db import transaction

transaction.on_commit(lambda: send_receipt.enqueue(order_id=order.pk))
result = send_receipt.using(queue_name="mail").enqueue(order_id=order.pk)
print(result.status, result.id)
```

- Built-in backends: `django.tasks.backends.immediate.ImmediateBackend` (default; runs the task synchronously inside `enqueue()`; development and tests) and `django.tasks.backends.dummy.DummyBackend` (records `TaskResult` objects in `default_task_backend.results` and runs nothing).
- The `TaskResult` carries `id`, `status` (`TaskResultStatus`: READY, RUNNING, FAILED, SUCCESSFUL), `args`, `kwargs`, `return_value`, `errors` and timestamps. `task.aenqueue()` and `aget_result()` are the async forms. Signals `task_enqueued`, `task_started`, `task_finished` exist in `django.tasks.signals`.
- Arguments and return values must be JSON-serializable. Pass ids, not model instances.
- `@task(takes_context=True)` passes a `TaskContext` first. `.using(run_after=...)` schedules a delayed run when the backend supports it; `run_after` cannot be set in the decorator.
- Production needs a backend that persists tasks and a process that runs them: a third-party backend package (check its Django 6.x support and maintenance), or Celery 5.x with its own broker, retries, schedules and canvas workflows. Do not ship `ImmediateBackend` to production for slow work.
- Tasks are at-least-once in practice: make them idempotent, key on an id, and tolerate the row having changed.
- Enqueue after commit (above); enqueueing inside `atomic` can run the task before the data is visible.
- In tests use `DummyBackend` through `override_settings(TASKS=...)` and assert on `default_task_backend.results`, or the default immediate backend to run tasks inline.

## 7. Caching

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "KEY_PREFIX": "shop",
        "TIMEOUT": 300,
    }
}
```

- Built-in backends: `locmem` (per process, tests and single-process dev), `redis` (needs `redis-py`), `memcached` (`PyMemcacheCache`), `db`, `filebased`, `dummy`. Use a shared backend with several workers. Redis operations: redis-expert.
- Low level: `cache.get_or_set(key, callable, timeout)`, `cache.set_many`, `cache.delete`, `cache.incr`. View level: `@cache_page(60)` with `@vary_on_headers`. Templates: `{% load cache %}{% cache 300 sidebar request.user.pk %}...{% endcache %}`.
- Include everything that changes the value in the key (user id, language, tenant); never cache per-user content under a shared key.
- Upgrading to 6.1 changes cache keys for varied pages and template fragments, so the first requests after deploy miss.

## 8. Email, logging and health checks

- Django 6.1 introduces `MAILERS` (aliases with `BACKEND` and `OPTIONS`); the `EMAIL_*` settings are deprecated and scheduled for removal in 2028.

```python
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {"host": env("SMTP_HOST", "localhost")},
    }
}
```

- Send mail from a task or `on_commit` hook, not inline in the request. Log delivery failures; do not use `fail_silently` (deprecated in 6.1).
- Logging: configure `LOGGING` (version 1) with a stream handler to stdout, `django.request` and `django.security` at WARNING, and application loggers at INFO. Use `sensitive_variables` and `sensitive_post_parameters` so error reports exclude secrets.
- Health: a view returning 200 after `connection.ensure_connection()` for readiness, and a trivial view for liveness. Do not call external services in liveness.

## 9. Release checklist

- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy` is clean or each warning is documented.
- [ ] `makemigrations --check --dry-run` clean; `migrate` runs once in the release step.
- [ ] `collectstatic` ran at build; WhiteNoise or the CDN serves hashed assets.
- [ ] Secrets come from the environment; `SECRET_KEY` unique per environment.
- [ ] CSP in report-only or enforcing mode; no `'unsafe-inline'`.
- [ ] A durable task backend and worker are deployed if tasks are used.
- [ ] Shared cache configured; throttle and session stores survive worker restarts.
- [ ] Health checks, structured logs and error reporting wired up.
- [ ] Rollback plan covers code and the last migration.
