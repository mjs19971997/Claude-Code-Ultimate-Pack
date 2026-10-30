# EF Core Reference

DbContext lifetime, migrations workflow, query patterns, raw SQL, query filters and tenant-safe writes for EF Core 10. Verified against EF Core 10.0.14 (LTS, requires .NET 10; package API checked in the 10.0.14 assemblies) and Npgsql.EntityFrameworkCore.PostgreSQL 10.0.x (2026-10). Provider-specific calls below use PostgreSQL; the EF calls themselves are provider-neutral.

## Contents

1. [DbContext lifetime and registration](#1-dbcontext-lifetime-and-registration)
2. [Migrations workflow](#2-migrations-workflow)
3. [Reading data](#3-reading-data)
4. [N+1, Include and split queries](#4-n1-include-and-split-queries)
5. [Compiled queries](#5-compiled-queries)
6. [Raw SQL](#6-raw-sql)
7. [Query filters and multi-tenancy](#7-query-filters-and-multi-tenancy)
8. [Writing data](#8-writing-data)
9. [Concurrency and transactions](#9-concurrency-and-transactions)

## 1. DbContext lifetime and registration

```csharp
builder.Services.AddDbContext<AppDb>((sp, o) =>
{
    var cs = sp.GetRequiredService<IConfiguration>().GetConnectionString("Db");
    o.UseNpgsql(cs, npgsql => npgsql.EnableRetryOnFailure());
    if (sp.GetRequiredService<IHostEnvironment>().IsDevelopment())
    {
        o.EnableSensitiveDataLogging();   // never outside local development
    }
});
```

- `DbContext` is scoped, cheap to create and not thread-safe. One instance per request; never share it across parallel tasks (`Task.WhenAll` on one context throws).
- `AddDbContextFactory<T>` registers `IDbContextFactory<T>` for singletons, `BackgroundService` and Blazor Server: `await using var db = await factory.CreateDbContextAsync(ct);`.
- `AddDbContextPool<T>` reuses instances to cut allocation. State kept in context fields (for example a tenant id injected through the constructor) is not reset the way EF's own state is; avoid pooling for tenant-aware contexts unless the tenant is resolved per use. Measure before adopting.
- `ConfigureDbContext<T>(...)` (services extension) adds options to an existing registration, which tests use to attach interceptors without replacing the provider.
- Retry strategies (`EnableRetryOnFailure`) require user-initiated transactions to run inside `CreateExecutionStrategy().ExecuteAsync(...)`.
- The connection string comes from configuration (user-secrets in development, the managed store in production); it never lives in `appsettings.json` with a password.

## 2. Migrations workflow

Install the tool locally so the version is pinned in the repository, and add `Microsoft.EntityFrameworkCore.Design` to the startup project.

```bash
dotnet new tool-manifest
dotnet tool install dotnet-ef
dotnet ef migrations add AddOrderNumberIndex --project src/Shop.Infrastructure --startup-project src/Shop.Api
dotnet ef migrations script --idempotent --project src/Shop.Infrastructure --startup-project src/Shop.Api -o artifacts/migrate.sql
dotnet ef migrations bundle --project src/Shop.Infrastructure --startup-project src/Shop.Api -o artifacts/efbundle
```

- Read the generated `Up` and `Down` before committing. Look for dropped columns, type changes that rewrite a table, new `NOT NULL` columns without defaults, and index builds that lock large tables.
- Deploy with a script (reviewed by a DBA or pipeline) or a bundle executed with the connection string passed as an argument (`./efbundle --connection "$DB_CONNECTION"` from a secret variable). Avoid `Database.Migrate()` in `Program.cs` when more than one instance can start at the same time.
- For rolling deployments use expand then contract: add the new column nullable, deploy code that writes both, backfill, switch reads, then drop the old column in a later release.
- Data fixes inside migrations use static SQL (`migrationBuilder.Sql("UPDATE ...")`); never interpolate user or environment values into it.
- Do not edit a migration that has been applied anywhere shared; add a new one. Remove the latest local-only migration with `dotnet ef migrations remove`.
- EF 10 note: on SQL Server 2025 and Azure SQL (compatibility level 170 and up) JSON columns default to the native `json` type, and existing `nvarchar` JSON columns convert in the first migration unless you opt out. Review that migration.

## 3. Reading data

```csharp
var rows = await db.Orders
    .AsNoTracking()
    .Where(o => o.TenantId == tenant && o.Status == "New")
    .OrderByDescending(o => o.Id)
    .Take(50)
    .Select(o => new OrderDto(o.Id, o.Number, o.Total, o.Status))
    .ToListAsync(ct);
```

- `AsNoTracking()` skips change tracking for read-only results. Use `AsNoTrackingWithIdentityResolution()` when the result graph contains the same entity several times. Set `UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)` as a default only if most queries are reads and writes opt in with `AsTracking()`.
- Project to DTOs with `Select` so only needed columns are fetched and no entity is tracked.
- Keep the query an `IQueryable` until the terminal operator (`ToListAsync`, `SingleOrDefaultAsync`, `AnyAsync`, `CountAsync`). Filtering after `ToList()` runs in memory.
- Prefer `AnyAsync` over `CountAsync() > 0`, and `SingleOrDefaultAsync` (or `FirstOrDefaultAsync` with an order) over loading a list to take one row.
- Keyset pagination: `Where(o => o.Id < lastId).OrderByDescending(o => o.Id).Take(n)` stays fast on deep pages; `Skip(n)` scans and discards rows. Always order deterministically when paging.
- EF 10 translates the LINQ `LeftJoin` and `RightJoin` operators to SQL `LEFT JOIN` and `RIGHT JOIN` (method syntax only; query syntax does not support them yet).

## 4. N+1, Include and split queries

```csharp
// N+1: one query for orders, then one per order for its lines.
foreach (var o in await db.Orders.ToListAsync(ct))
{
    total += o.Lines.Sum(l => l.Amount);   // lazy loading or a separate query per row
}

// One round trip, only what is needed:
var totals = await db.Orders
    .Where(o => o.TenantId == tenant)
    .Select(o => new { o.Id, Total = o.Lines.Sum(l => l.Amount) })
    .ToListAsync(ct);
```

- Lazy-loading proxies hide N+1; leave them off unless there is a strong reason.
- When the entities themselves are needed, `Include(o => o.Lines)` loads them in the same query. Several collection includes on one query multiply rows (cartesian explosion); add `AsSplitQuery()` to run one SQL statement per collection, or set `UseQuerySplittingBehavior(QuerySplittingBehavior.SplitQuery)` globally and opt out with `AsSingleQuery()`. Split queries can see inconsistent data if rows change between statements; wrap in a transaction when that matters.
- Filtered includes: `Include(o => o.Lines.Where(l => l.Amount > 0))`.
- Batch lookups with `Where(x => ids.Contains(x.Id))`. EF 10 sends each value as its own parameter by default and pads the list to reduce distinct SQL shapes; tune with `UseParameterizedCollectionMode` or `EF.Constant` per query.
- Detect N+1 in tests by counting commands (see [testing.md](testing.md#6-counting-queries)).

## 5. Compiled queries

```csharp
public static class OrderQueries
{
    public static readonly Func<AppDb, string, Guid, CancellationToken, Task<OrderDto?>> ById =
        EF.CompileAsyncQuery((AppDb db, string tenant, Guid id) =>
            db.Orders.AsNoTracking()
                .Where(o => o.TenantId == tenant && o.Id == id)
                .Select(o => new OrderDto(o.Id, o.Number, o.Total, o.Status))
                .SingleOrDefault());
}

var dto = await OrderQueries.ById(db, tenant, id, ct);
```

- EF already caches the translation of normal queries by expression shape. A compiled query removes the remaining lookup overhead and only matters on a measured hot path.
- Parameters, not captured variables, carry the changing values; the tenant is a parameter here so the tenant condition is part of the compiled shape.

## 6. Raw SQL

```csharp
// Interpolation is parameterized: {term} becomes a DbParameter, not text in the statement.
var term = userInput;
var found = await db.Orders
    .FromSql($"SELECT * FROM orders WHERE tenant_id = {tenant} AND number ILIKE {term + "%"}")
    .AsNoTracking()
    .ToListAsync(ct);

// Scalar or DTO results without an entity:
var counts = await db.Database
    .SqlQuery<int>($"SELECT count(*)::int AS \"Value\" FROM orders WHERE tenant_id = {tenant}")
    .ToListAsync(ct);

// Non-query commands:
await db.Database.ExecuteSqlAsync($"DELETE FROM sessions WHERE expires_at < {DateTimeOffset.UtcNow}", ct);
```

- `FromSql` and `ExecuteSql`/`ExecuteSqlAsync` accept a `FormattableString` and parameterize every interpolation hole. `FromSqlInterpolated` is the older equivalent.
- `FromSqlRaw`/`ExecuteSqlRaw` take a plain string and parameters you build yourself. Passing a concatenated or interpolated string there is SQL injection; EF 10 ships an analyzer that warns about concatenation in `FromSqlRaw`.
- Parameters substitute values only. Table, column and sort-direction names cannot be parameters; choose them from a fixed allowlist in code.
- `FromSql` must return all columns of the entity and can be composed with `Where`, `OrderBy` and `Include` when the SQL is a plain `SELECT`.
- Stored procedures and views: map views with `ToView`, use `SqlQuery<T>` for ad hoc shapes, and keep the SQL in version control.

## 7. Query filters and multi-tenancy

```csharp
public sealed class AppDb(DbContextOptions<AppDb> options, ITenantAccessor tenantAccessor) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();

    // Read at query time, per context instance; EF turns it into a parameter.
    private string CurrentTenant => tenantAccessor.TenantId;

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Order>().HasQueryFilter("Tenant", o => o.TenantId == CurrentTenant);
        b.Entity<Order>().HasQueryFilter("SoftDelete", o => !o.IsDeleted);
    }
}

// Bypass only the soft-delete filter, keep the tenant filter:
var withDeleted = await db.Orders.IgnoreQueryFilters(["SoftDelete"]).ToListAsync(ct);
```

- Named query filters (`HasQueryFilter("Name", expr)`) and `IgnoreQueryFilters(["Name"])` are new in EF Core 10. Before EF 10 a type has one unnamed filter and `IgnoreQueryFilters()` disables all of it.
- The filter is a safety net for reads. It does not replace explicit tenant conditions on writes, and `IgnoreQueryFilters()` without names removes the tenant filter along with the rest.
- `ITenantAccessor` reads the tenant from the authenticated principal (a validated claim) through `IHttpContextAccessor`; for jobs and consumers without an HTTP context it is set explicitly from the message being processed.
- Add the tenant column as the first column of the indexes that serve the filtered queries, and as part of unique constraints (`HasIndex(o => new { o.TenantId, o.Number }).IsUnique()`).
- Required navigations to a filtered entity produce warnings about inconsistent filters; give the dependent the same tenant filter.

## 8. Writing data

```csharp
// Tracked write: load with the tenant condition, mutate, save.
var order = await db.Orders.SingleOrDefaultAsync(o => o.TenantId == tenant && o.Id == id, ct);
if (order is null) return TypedResults.NotFound();
order.Total = body.Total;
await db.SaveChangesAsync(ct);

// Set-based update, conditional parts allowed with a plain lambda in EF 10:
var rows = await db.Orders
    .Where(o => o.TenantId == tenant && o.Status == "New" && o.CreatedAt < cutoff)
    .ExecuteUpdateAsync(s =>
    {
        s.SetProperty(o => o.Status, "Expired");
        if (notify) s.SetProperty(o => o.NotifyPending, true);
    }, ct);

// Set-based delete, same rule:
await db.Orders.Where(o => o.TenantId == tenant && o.Id == id).ExecuteDeleteAsync(ct);
```

- Every write path carries the tenant or owner condition: tracked loads, `ExecuteUpdateAsync`, `ExecuteDeleteAsync`, and `Remove` of an entity fetched by id. Treat "no rows affected" as 404.
- `ExecuteUpdate` and `ExecuteDelete` run immediately as one SQL statement. They bypass the change tracker, `SaveChanges` interceptors, concurrency tokens and cascade rules that EF would apply in memory, and they are not part of the `SaveChanges` unit of work. Use a transaction when several must succeed together.
- Bind request DTOs, never entities. Assign only the fields a caller may change; set `TenantId`, `Id` and audit columns on the server.
- Use `AddRange` for bulk inserts of moderate size; for very large loads use the provider's bulk copy API, outside EF.

## 9. Concurrency and transactions

```csharp
// Entity: a concurrency token column (for SQL Server, [Timestamp] public byte[] Version; other providers map this differently, check the provider docs)
try
{
    await db.SaveChangesAsync(ct);
}
catch (DbUpdateConcurrencyException)
{
    return TypedResults.Conflict();
}

await using var tx = await db.Database.BeginTransactionAsync(ct);
var moved = await db.Accounts.Where(a => a.TenantId == tenant && a.Id == from && a.Balance >= amount)
    .ExecuteUpdateAsync(s => s.SetProperty(a => a.Balance, a => a.Balance - amount), ct);
if (moved == 0) return TypedResults.Conflict();
await db.Accounts.Where(a => a.TenantId == tenant && a.Id == to)
    .ExecuteUpdateAsync(s => s.SetProperty(a => a.Balance, a => a.Balance + amount), ct);
await tx.CommitAsync(ct);
```

- Optimistic concurrency with a row-version or concurrency token turns lost updates into a handled 409. The mechanism differs by provider; check the provider documentation for the exact mapping.
- `SaveChanges` wraps its own changes in a transaction. An explicit transaction is for sequences of `ExecuteUpdate`, raw SQL and `SaveChanges` that must commit together; with `EnableRetryOnFailure`, wrap the whole block in `db.Database.CreateExecutionStrategy().ExecuteAsync(...)`.
- Conditional updates (`Balance >= amount` in the `Where`) make check-and-change atomic without a read first.
