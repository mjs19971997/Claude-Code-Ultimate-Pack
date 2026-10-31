# Migrations and the Custom User Model

How Django migrations work, commands for inspecting and applying them, data migrations, squashing, rules for changing a live schema without downtime, PostgreSQL-specific operations and the custom user model setup that must happen before the first migration. Commands and operation names checked against Django 6.1.2 (2026-10).

## Contents

1. [Workflow and commands](#1-workflow-and-commands)
2. [Reading a migration](#2-reading-a-migration)
3. [Data migrations](#3-data-migrations)
4. [Squashing and cleanup](#4-squashing-and-cleanup)
5. [Zero-downtime rules](#5-zero-downtime-rules)
6. [PostgreSQL operations](#6-postgresql-operations)
7. [Branches, merges and conflicts](#7-branches-merges-and-conflicts)
8. [Custom user model](#8-custom-user-model)
9. [CI and deploy gates](#9-ci-and-deploy-gates)

## 1. Workflow and commands

```bash
python manage.py makemigrations shop              # create from model changes
python manage.py makemigrations shop --name add_product_sku
python manage.py makemigrations shop --empty --name backfill_sku   # for a data migration
python manage.py sqlmigrate shop 0004             # print the SQL, review locks
python manage.py migrate --plan                   # what would run
python manage.py migrate                          # apply all
python manage.py migrate shop 0003                # move to (and roll back to) a state
python manage.py showmigrations shop              # applied/unapplied
python manage.py makemigrations --check --dry-run # exit 1 when models and migrations differ
python manage.py migrate --check                  # exit 1 when unapplied migrations exist
python manage.py optimizemigration shop 0004      # collapse redundant operations
python manage.py squashmigrations shop 0001 0010  # squash a range
```

- Commit the model change and its migration together. Never edit a migration that another environment has applied; add a new one.
- Generated names are fine for small changes; pass `--name` for anything that needs explanation.
- Rename detection asks interactively. In scripts, write `RenameField` / `RenameModel` by hand so the data is kept; a drop plus add loses data.
- `migrate app zero` unapplies everything for an app; a `RunPython` without a reverse function makes a migration irreversible.
- `--fake` and `--fake-initial` mark migrations applied without running SQL; use them only to align state with a schema that already matches, and record why.
- Third-party apps ship migrations; do not edit them in site-packages. Override with `MIGRATION_MODULES` only as a last resort.

## 2. Reading a migration

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = True                       # default; set False for CONCURRENTLY operations
    dependencies = [("shop", "0003_product_stock")]
    operations = [
        migrations.AddField(
            model_name="product",
            name="sku",
            field=models.CharField(max_length=40, null=True),
        ),
    ]
```

- `dependencies` form a graph; order within an app is the dependency chain, not the file number.
- Operations run in order inside one transaction on PostgreSQL and SQLite (unless `atomic = False`). On MySQL and MariaDB DDL is not transactional, so a failed migration can leave a half-applied state.
- Cross-app FKs add a dependency on the other app, for example `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`.
- `SeparateDatabaseAndState(database_operations=[...], state_operations=[...])` changes Django's state and the database independently; use it to rename a table, move a model between apps, or adopt an existing column without data copies.
- `migrations.RunSQL(sql, reverse_sql)` for DDL that has no operation; provide a reverse and keep statements parameter-free.

## 3. Data migrations

```python
from django.db import migrations


def backfill_sku(apps, schema_editor):
    Product = apps.get_model("shop", "Product")      # historical model, not the import
    db = schema_editor.connection.alias
    batch = []
    for p in Product.objects.using(db).filter(sku__isnull=True).iterator(chunk_size=2000):
        p.sku = f"P-{p.pk}"
        batch.append(p)
        if len(batch) >= 1000:
            Product.objects.using(db).bulk_update(batch, ["sku"])
            batch.clear()
    if batch:
        Product.objects.using(db).bulk_update(batch, ["sku"])


class Migration(migrations.Migration):
    dependencies = [("shop", "0004_add_product_sku")]
    operations = [
        migrations.RunPython(backfill_sku, migrations.RunPython.noop, elidable=True),
    ]
```

- Always load models with `apps.get_model()`; the real model class may have changed since the migration was written. Custom methods and managers are not available on historical models unless `use_in_migrations = True`.
- Provide `reverse_code` (use `RunPython.noop` when undoing needs no work) so the migration can be unapplied.
- `elidable=True` lets `squashmigrations` drop the operation when the data is no longer needed.
- Keep data and schema changes in separate migrations: a data migration that runs inside the same transaction as a schema change on the same table can hit "pending trigger events" errors on PostgreSQL.
- For large tables, loop in batches and consider `atomic = False` on the migration so each batch commits, or run the backfill as a management command or task and make the code tolerate both states.
- Do not import application services, call APIs or enqueue tasks from a migration.
- Put a data migration after the schema migration that creates the column, and make constraints (`NOT NULL`, unique) a later migration.

## 4. Squashing and cleanup

- `squashmigrations shop 0001 0010` writes `0001_squashed_0010_...` with a `replaces` list. Both the old and squashed files can coexist; Django uses the squashed one on fresh databases and the old ones where they were already applied.
- Squash only when every environment has applied the range. Then run `optimizemigration` on the result, remove the replaced files, and change later migrations' dependencies to the squashed name (see the Django migrations docs, "Squashing migrations").
- `RunPython` and `RunSQL` operations are copied into the squash unless marked `elidable`.
- Circular dependencies in a squash must be fixed by hand.
- Test the squash on an empty database (`migrate` from scratch) and on a copy of production schema.
- Deleting migrations without a squash breaks `migrate` for environments that are not at the latest state.

## 5. Zero-downtime rules

During a rolling deploy, old and new code run against the same schema. Each migration must be compatible with the code on both sides. The usual pattern is expand, migrate data, contract across separate releases.

| Change | Safe approach |
|---|---|
| Add nullable column | One step; old code ignores it |
| Add `NOT NULL` column | Add as nullable or with `db_default=...` (Django 5.0+); backfill; later add the constraint |
| Add column with default | Use `db_default` so the database supplies the value and old code can still insert; a Python-only `default` leaves old code inserting NULL |
| Drop column | Release 1: stop reading and writing it (remove from model code, keep column nullable). Release 2: drop the column |
| Rename column or model | Add the new name, write both, backfill, switch reads, drop the old name later. A plain `RenameField` breaks old code mid-deploy |
| Change column type | Add a new column, dual-write, backfill in batches, switch reads, drop the old one |
| Add index on a big table | PostgreSQL: `AddIndexConcurrently` (see section 6); plain `AddIndex` locks writes |
| Add unique constraint | Build a unique index concurrently first, then add the constraint using it, or validate in stages |
| Add FK | Add as nullable, optionally `db_constraint=False` first on huge tables, validate later |
| Add `CHECK` constraint | PostgreSQL: `AddConstraintNotValid` then `ValidateConstraint` |
| Delete a model | Remove usage first; drop the table in a later release |

- A migration that rewrites a large table (type change, default on old PostgreSQL) holds an `ACCESS EXCLUSIVE` lock; review `sqlmigrate` output and set a `lock_timeout` for DDL in the database role or the migration.
- Run `migrate` before the new code starts serving, and make the previous code version compatible with the new schema (expand step) so a rollback of the code is safe.
- Adding or removing choices on a field creates a migration that changes no SQL; harmless, but still commit it.
- For `on_delete=DB_CASCADE`, `DB_SET_NULL` or `DB_SET_DEFAULT` (6.1) the constraint is created in the database; adding it alters the FK constraint, which locks both tables briefly. A database-level `on_delete` on a FK whose model also takes part in an auto-created many-to-many table fails system check `fields.E323` (tested on 6.1.2); use a Python-level `on_delete` or an explicit `through` model.

## 6. PostgreSQL operations

Import from `django.contrib.postgres.operations` (requires `django.contrib.postgres` and psycopg). Operations that cannot run in a transaction need `atomic = False`.

```python
from django.contrib.postgres.operations import AddIndexConcurrently, ValidateConstraint
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("shop", "0005_backfill_sku")]
    operations = [
        AddIndexConcurrently(
            "product",
            models.Index(fields=["sku"], name="product_sku_idx"),
        ),
    ]
```

- Available: `AddIndexConcurrently`, `RemoveIndexConcurrently`, `AddConstraintNotValid`, `ValidateConstraint`, `CreateExtension` and the extension shortcuts (`TrigramExtension`, `BtreeGinExtension`, `UnaccentExtension`, `HStoreExtension`, ...), `CreateCollation`.
- `AddConstraintNotValid` adds a `CHECK` or FK constraint without scanning the table; `ValidateConstraint` validates later with a weaker lock.
- A concurrent index build can fail and leave an invalid index; check `\d table` and drop and retry.
- With `atomic = False` a failure part-way leaves the earlier operations applied. Keep such a migration to one operation.
- Index design and lock behaviour of specific PostgreSQL versions: postgresql-expert.

## 7. Branches, merges and conflicts

- Two branches that each add a migration to the same app produce two leaf nodes; `migrate` reports "Conflicting migrations". Run `makemigrations --merge` to create a merge migration, then review it.
- Prefer to rebase and renumber your migration on the latest main when the other migration has not shipped.
- CI should run `makemigrations --check --dry-run` so missing migrations fail the build before merge.
- After a merge, run `migrate` on a fresh database and on a dump of the shared environment.

## 8. Custom user model

Create it before the first `migrate` of any project, even if it adds nothing.

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

```python
# settings
AUTH_USER_MODEL = "accounts.User"
```

```python
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

admin.site.register(User, UserAdmin)
```

- Run `makemigrations accounts` and `migrate` first; every app that references users uses `settings.AUTH_USER_MODEL` in FKs, and `get_user_model()` at runtime.
- For email login: subclass `AbstractUser`, set `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`, make `email` unique, set `username = None`, and add a `UserManager` subclass whose `create_user` / `create_superuser` use email. Use `AbstractBaseUser` plus `PermissionsMixin` only when you need to drop the `AbstractUser` fields.
- Add profile data as fields on the user, or a one-to-one `Profile` model for optional or app-specific data.
- If a project already runs on `auth.User`, switching requires creating the new table, copying rows with the same ids, repointing FKs and rewriting migration state (often `SeparateDatabaseAndState`). Rehearse on a copy and plan downtime.
- Third-party packages that reference users must be configured through `AUTH_USER_MODEL`; check before adding one to an old project.
- Password hashing: PBKDF2 with 1,500,000 default iterations on 6.1 (1,200,000 on 6.0); hashes upgrade on next login. For Argon2 install the extra and put `django.contrib.auth.hashers.Argon2PasswordHasher` first in `PASSWORD_HASHERS`.

## 9. CI and deploy gates

```bash
python manage.py makemigrations --check --dry-run   # fail if a migration is missing
python manage.py migrate --noinput                  # on an empty test database
python manage.py migrate --check                    # in the release image before start
python manage.py check --deploy                     # 6.1 also runs database checks on all aliases
```

- Run the full migration chain on an empty database in CI; this catches broken historical `RunPython` and ordering mistakes.
- Make the release job run `migrate` once, before rolling the new application image.
- Add a lint rule or review checklist item for risky operations: `AddField` with `null=False` and no `db_default`, `RemoveField`, `RenameField`, `AlterField` on large tables, plain `AddIndex` on a big PostgreSQL table.
- Keep a rollback plan: unapplying a migration needs its reverse code, and rolling back data migrations rarely restores dropped data. Prefer forward fixes.
- Measure on a production-sized copy: lock duration, table rewrite and index build time.
