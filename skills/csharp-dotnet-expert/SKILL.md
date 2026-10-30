---
name: csharp-dotnet-expert
description: >-
  Writes and reviews modern C# and .NET services: ASP.NET Core minimal APIs (route groups, TypedResults, endpoint filters, built-in validation, OpenAPI), EF Core data access, dependency injection and the options pattern, async code, nullable reference types, and xUnit tests with WebApplicationFactory and Testcontainers. Use when working with .csproj, Program.cs, DbContext, dotnet ef, dotnet test, dotnet format, appsettings.json, user-secrets, captive dependencies or N+1 queries. Not for Azure resources or Key Vault setup (use azure-expert), container images (use docker-expert), OAuth/OIDC design (use authentication-expert), or tracing backends (use observability-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# C# and .NET Expert

This skill covers application code on current .NET: C# language features, ASP.NET Core minimal APIs, EF Core, dependency injection, configuration, async programming, analyzers and formatting, and automated tests. It treats security as part of ordinary coding (tenant-scoped writes, authorization policies, no secrets in configuration files). Cloud provisioning, container builds, identity protocols and telemetry backends belong to other skills.

> Verified against .NET 10 (LTS) with C# 14, ASP.NET Core 10.0.14, EF Core 10.0.14, Microsoft.AspNetCore.OpenApi 10.0.14, xunit.v3 4.0.2, Testcontainers 4.16.0 (NuGet and official docs, 2026-10). .NET 11 is at release-candidate stage (11.0.0-rc.3 packages) and is not covered as stable.

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

- Covered: C# 14 language use, project files and `Directory.Build.props`, minimal APIs, EF Core (DbContext, migrations, queries, raw SQL), DI lifetimes and the options pattern, async and cancellation, nullable reference types, analyzers and `dotnet format`, xUnit v3 tests, `WebApplicationFactory` integration tests, Testcontainers for .NET, user-secrets for local development.
- Not covered: Azure resources, App Service and Key Vault provisioning (azure-expert); Dockerfiles and image hardening (docker-expert); OAuth 2.0 and OpenID Connect flows, token issuing and JWT validation design (authentication-expert); metrics, traces and log backends (observability-expert); general authorization model design (authorization-expert); schema design and tuning inside PostgreSQL (postgresql-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Release train | .NET 10 is LTS and ships C# 14. .NET 8 (LTS) and .NET 9 (STS) both reach end of support on 2026-11-10, so plan the move to 10. .NET 11 is a release candidate in 2026-10; its GA is expected in November 2026, check the support policy page before adopting |
| C# 14 | `field` keyword in property accessors; `extension(...)` blocks for extension properties and static members; null-conditional assignment (`customer?.Order = x`); `nameof(List<>)`; lambda parameter modifiers without types (`(text, out result) => ...`); partial constructors and events; implicit span conversions |
| Nullable | `<Nullable>enable</Nullable>` in the project; annotate APIs honestly, avoid `!` except after a check the compiler cannot see; `required` members and `init` for DTOs |
| Minimal APIs | `app.MapGroup("/x")` shares prefix, filters, auth and metadata; `TypedResults` plus `Results<Ok<T>, NotFound>` give typed responses that feed OpenAPI; `AddEndpointFilter` runs around a handler; `ProducesProblem`, `WithName`, `WithTags` add metadata |
| Validation | .NET 10 adds built-in minimal API validation: `builder.Services.AddValidation()` (package Microsoft.Extensions.Validation) validates DataAnnotations on parameters and DTOs and returns 400 ProblemDetails. A source generator finds types in the assembly that calls `AddValidation`; endpoints in other assemblies need their own registration. `ValidatableTypeAttribute` and `SkipValidationAttribute` are experimental in 10 |
| OpenAPI | Microsoft.AspNetCore.OpenApi: `builder.Services.AddOpenApi()` and `app.MapOpenApi()`. .NET 10 emits OpenAPI 3.1 by default (`OpenApiOptions.OpenApiVersion`) on Microsoft.OpenApi 2.x, which broke some transformers. ASP.NET Core 11 previews move the default to 3.2 and to Microsoft.OpenApi 3.x; pin the version if clients cannot read 3.2 |
| EF Core 10 | LTS, requires .NET 10. Named query filters: `HasQueryFilter("Name", expr)` and `IgnoreQueryFilters(["Name"])`. `ExecuteUpdateAsync` takes a plain lambda (`s => s.SetProperty(...)`) so `if` blocks work. `LeftJoin`/`RightJoin` LINQ operators translate. Complex types map to table splitting or JSON. Collections in `Contains` are sent as individual parameters by default (`UseParameterizedCollectionMode`) |
| Raw SQL | `FromSql($"... {x}")` and `ExecuteSqlAsync($"...")` turn interpolated values into parameters; `FromSqlRaw`/`ExecuteSqlRaw` do not, and EF 10 includes an analyzer that warns on concatenation in `FromSqlRaw` |
| DI | `Singleton`, `Scoped`, `Transient`; keyed services via `AddKeyedSingleton` and `[FromKeyedServices("key")]`; `ValidateScopes` and `ValidateOnBuild` are on by default in the Development environment only |
| Options | `AddOptions<T>().BindConfiguration("Section").ValidateDataAnnotations().ValidateOnStart()` fails startup on bad configuration; `IOptions<T>` (fixed), `IOptionsSnapshot<T>` (per scope), `IOptionsMonitor<T>` (change notifications) |
| Async | ASP.NET Core has no synchronization context, so `ConfigureAwait(false)` is unnecessary in app code but still recommended in reusable libraries; `async void` only for event handlers; `ValueTask` may be awaited once |
| Testing | xunit.v3 (current stable 4.0.2, supports .NET 8+ and .NET Framework 4.7.2+); test projects are executables; `IAsyncLifetime` methods return `ValueTask`; pass `TestContext.Current.CancellationToken` to async calls. `Microsoft.AspNetCore.Mvc.Testing` provides `WebApplicationFactory<TEntryPoint>` |
| Tooling | `dotnet format --verify-no-changes`, `dotnet build -warnaserror`, `dotnet list package --vulnerable`, `dotnet user-secrets`, `dotnet ef migrations add|bundle|script` |

## 3. Workflow

1. Read `global.json`, `Directory.Build.props`, `Directory.Packages.props` and the target framework in the `.csproj` files before changing code; match the existing conventions and do not upgrade the SDK as a side effect.
2. For a bug, reproduce it with a failing test or a `dotnet run` request first. For slow endpoints, log the generated SQL (`LogTo` or `EnableSensitiveDataLogging` in Development only) before changing queries.
3. Make the smallest change: handler, service, query or registration. Keep new public surface minimal.
4. Run `dotnet build -warnaserror`, `dotnet format --verify-no-changes` and `dotnet test` and read the results; do not assume they pass.
5. When a schema changes, add a migration with `dotnet ef migrations add <Name>`, read the generated `Up`/`Down`, and produce an idempotent script or bundle for deployment.
6. Summarize the change and name any follow-up (secret to set, migration to apply, configuration key to add).

## 4. Decision Rules

- New HTTP service with a small surface: minimal APIs with route groups. Many controllers, filters and conventions already in place: stay on controllers rather than rewriting.
- Prefer `TypedResults` and `Results<...>` return types over `IResult` so the response types appear in OpenAPI without `Produces` attributes.
- Use built-in `AddValidation()` for DataAnnotations rules. Use FluentValidation or a custom endpoint filter only when rules need cross-field logic or async lookups that attributes cannot express.
- Read-only queries use `AsNoTracking()` (or `AsNoTrackingWithIdentityResolution()` when the graph repeats entities). Writes load and `SaveChangesAsync`, or use `ExecuteUpdateAsync`/`ExecuteDeleteAsync` for set-based changes without loading.
- Several collection `Include`s on one query cause a cartesian product; use `AsSplitQuery()` for those and a projection (`Select` to a DTO) when only some columns are needed.
- `AddDbContext` (scoped) for request code; `AddDbContextFactory` for background services, Blazor Server and anything that outlives a scope; `AddDbContextPool` only after measuring, and never keep per-request state in a pooled context.
- A singleton that needs a scoped service gets `IServiceScopeFactory` and creates a scope per unit of work; a scoped service is never injected into a singleton constructor.
- `IOptions<T>` for settings fixed at startup, `IOptionsMonitor<T>` for values that change at run time, `IOptionsSnapshot<T>` only inside scoped services.
- `ValueTask<T>` only for hot paths that usually complete synchronously and are measured; default to `Task<T>`.
- Local secrets go in user-secrets; production secrets come from a managed store through configuration (Key Vault setup: azure-expert). Neither goes in `appsettings.json`.
- Tests that need real SQL behavior (constraints, translation, transactions) use Testcontainers with the production provider; the EF in-memory provider does not behave like a relational database and the SQLite provider differs from most production engines.

## 5. Coding Standards

- Enable `<Nullable>enable</Nullable>`, `<ImplicitUsings>enable</ImplicitUsings>`, `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` (at least in CI) and `<AnalysisLevel>latest-recommended</AnalysisLevel>` in `Directory.Build.props`; add `<EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>` so `.editorconfig` style rules fail the build.
- File-scoped namespaces, primary constructors for DI-only classes, `sealed` on classes not designed for inheritance, `record` for immutable DTOs.
- Async methods end in `Async`, return `Task`/`Task<T>`/`ValueTask`, and accept a `CancellationToken ct` as the last parameter; never `async void` outside event handlers; never `.Result` or `.Wait()` on a task.
- Do not catch `Exception` to log and continue; handle specific exceptions where recovery is possible, and let the global exception handler (`UseExceptionHandler` with `AddProblemDetails`) turn the rest into ProblemDetails.
- Do not use `DateTime.Now` in logic; take `TimeProvider` through DI so tests control time.
- Bind configuration to typed options classes; do not read `IConfiguration["Key"]` in business code.
- Use `ILogger<T>` with message templates (`"Order {OrderId} cancelled"`) or `LoggerMessage` source generation, never string interpolation in log calls.
- Use `Guid.CreateVersion7()` (.NET 9+) for new identifiers that benefit from time ordering as index keys.

## 6. Project Structure

```text
repo/
├── global.json                      # pins the SDK version (rollForward policy)
├── Directory.Build.props            # Nullable, analyzers, TreatWarningsAsErrors
├── Directory.Packages.props         # central package versions (ManagePackageVersionsCentrally)
├── .editorconfig                    # style and analyzer severities
├── src/
│   ├── Shop.Api/                    # Program.cs, endpoint groups, DI wiring
│   │   ├── Endpoints/OrderEndpoints.cs
│   │   └── appsettings.json         # non-secret defaults only
│   ├── Shop.Domain/                 # entities, rules, no framework references
│   └── Shop.Infrastructure/         # DbContext, configurations, Migrations/
└── tests/
    ├── Shop.UnitTests/
    └── Shop.IntegrationTests/       # WebApplicationFactory + Testcontainers
```

- One `Map<Feature>Endpoints(this IEndpointRouteBuilder app)` extension per feature keeps `Program.cs` short.
- Keep `public partial class Program;` (or the equivalent accessibility) in the API project so tests can reference the entry point.

## 7. Design Patterns

- **Endpoint group per feature**: `MapGroup` with shared `RequireAuthorization`, tags and filters. Cost: filters on a group apply to every endpoint, so order them deliberately.
- **Endpoint filter for cross-cutting checks**: `AddEndpointFilter` for idempotency keys or request normalization. Cost: filters are invisible in handler signatures; keep them few and documented.
- **Options with startup validation**: typed class, DataAnnotations or `IValidateOptions<T>`, `ValidateOnStart()`. Cost: a bad setting stops the app, which is the intended behavior.
- **Keyed services**: several implementations of one interface chosen by key (for example two payment gateways). Cost: string keys are not compile-time checked; use constants.
- **Unit of work via DbContext**: the scoped `DbContext` is already one; avoid a repository layer that only forwards to `DbSet`. Add a repository or query class when the query is reused or needs a seam for tests.
- **Result types over exceptions for expected failures**: return `Results<Ok<T>, NotFound, Conflict>` from handlers; reserve exceptions for faults.
- **Compiled queries**: `EF.CompileAsyncQuery` for a measured hot query. Cost: less readable; profile first.
- Long examples and templates: [references/minimal-apis.md](references/minimal-apis.md), [references/ef-core.md](references/ef-core.md).

## 8. Best Practices

- Pass `CancellationToken` from the handler parameter (bound to `HttpContext.RequestAborted`) through every awaited call so abandoned requests stop work.
- Return `ProblemDetails` for errors (`AddProblemDetails`, `TypedResults.Problem`, `ProducesProblem`) so clients see one error shape.
- Version public APIs in the route or a header and keep OpenAPI documents in CI as an artifact to diff for breaking changes.
- Keep `Program.cs` declarative: register services, map groups, run. Business logic sits in services that tests can construct without the host.
- Set explicit `HttpClient` timeouts and use `IHttpClientFactory` (typed or named clients) with resilience handlers; never `new HttpClient()` per call.
- Store timestamps in UTC (`DateTimeOffset`) and convert at the edge.
- Use `Directory.Packages.props` for one version per package across projects, and review `dotnet list package --outdated` and `--vulnerable` regularly.
- Run `dotnet format` in CI with `--verify-no-changes` so formatting never produces noisy diffs.

## 9. Performance

- Measure first: BenchmarkDotNet for code paths, `dotnet-counters` and `dotnet-trace` for a running process, the EF generated SQL and the database's own plan for queries.
- N+1: a loop that touches a navigation property or queries per item. Fix with `Include`/`ThenInclude`, a projection, or one `Where(x => ids.Contains(x.Id))` query. Check by counting SQL statements in a test (see the EF reference).
- `AsNoTracking` on read-only queries; project to DTOs instead of loading entities; never `ToList()` before filtering (`IEnumerable` filtering runs in memory).
- Page with keyset conditions for large tables; `Skip/Take` deep offsets scan and discard rows. Always include a deterministic `OrderBy`.
- Add indexes that match the `Where` and `OrderBy` of the endpoints, including the tenant column first in multi-tenant tables.
- Avoid sync-over-async (`.Result`, `.GetAwaiter().GetResult()`) on request threads: it exhausts the thread pool under load.
- Use `HybridCache` (Microsoft.Extensions.Caching.Hybrid) or output caching for hot reads; check the current docs for configuration and stampede protection.
- Consider `System.Text.Json` source generation (`JsonSerializerContext`) for trimming or startup-sensitive deployments.

## 10. Security

- Tenant and owner filters apply to writes too. Every `ExecuteUpdateAsync`, `ExecuteDeleteAsync` and `Remove` path includes the tenant (or owner) in its `Where`, and "not found" and "not yours" return the same 404. A write that targets `Id` alone is an IDOR.
- Read the tenant from the authenticated principal (a validated claim), never from a header, route or body field the client controls. Global query filters (`HasQueryFilter`) are a backstop for reads, not a substitute for explicit conditions on writes; `IgnoreQueryFilters` bypasses them.
- Authorization: require an authenticated user by default (`FallbackPolicy` via `AddAuthorizationBuilder().SetFallbackPolicy(...)`) and attach named policies with `RequireAuthorization("Policy")` on groups. Use resource-based checks (`IAuthorizationService`) when the decision depends on the loaded object. Policy and model design: authorization-expert.
- SQL: use `FromSql`/`ExecuteSql` with interpolation or explicit `SqlParameter`s; never build SQL by concatenation or `string.Format`, and never pass user text to `FromSqlRaw` as the statement. Identifiers cannot be parameters; map them from an allowlist.
- Secrets: none in `appsettings.json`, source control, test fixtures or container environment baked into images. Development uses `dotnet user-secrets` (stored unencrypted in the user profile, development only). Production reads from a managed secret store through configuration providers or environment variables (Key Vault setup: azure-expert).
- Bind request DTOs, not entities, to avoid over-posting (mass assignment); mark server-owned fields (`TenantId`, `Status`, `Id`) as not bindable by leaving them out of the DTO.
- Keep HTTPS redirection and HSTS (`UseHsts`) on outside Development; never set `ServerCertificateCustomValidationCallback` to always return true.
- Add rate limiting (`AddRateLimiter`/`UseRateLimiter`) on login-like and expensive endpoints, and request size limits where uploads exist.
- Log identifiers, not payloads; `EnableSensitiveDataLogging` stays off outside local debugging. EF 10 redacts inlined constants as `?` in logs by default.
- Token validation, scopes and OIDC configuration: authentication-expert.

## 11. Testing

- Unit tests: plain xUnit `[Fact]`/`[Theory]` on services and domain code with fakes; use `TimeProvider` (the `FakeTimeProvider` in Microsoft.Extensions.TimeProvider.Testing) for time.
- Integration tests: `WebApplicationFactory<Program>` with a real database in Testcontainers; apply migrations in the fixture, create a fresh tenant per test instead of truncating tables.
- Cover failure paths: 400 validation, 401/403, 404 for another tenant's id (write and read), 409 conflicts, and cancellation.
- Count queries for N+1 regressions with a `LogTo` or interceptor in the test host and assert on the number of commands.
- Commands: `dotnet test`, `dotnet test --filter "FullyQualifiedName~Orders"`, `dotnet test --no-build` in CI after a separate build. For xunit.v3 and `dotnet test` modes, check the current xunit.net documentation for the runner setup that matches the SDK.
- Docker must be reachable on the CI agent for Testcontainers; pin the image tag (`postgres:17-alpine`) and let the library's resource reaper clean up.
- Details and a test authentication handler: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Target framework, SDK and package versions match `global.json` and `Directory.Packages.props`; no accidental upgrade.
- [ ] Nullable warnings are fixed, not suppressed; no new `!` without a comment-worthy reason.
- [ ] Every async path takes and forwards a `CancellationToken`; no `async void`, `.Result` or `.Wait()`.
- [ ] No captive dependencies; singletons use `IServiceScopeFactory` or `IDbContextFactory<T>` for scoped work.
- [ ] Queries filter and project in SQL, use `AsNoTracking` when read-only, and do not loop over navigation properties.
- [ ] All writes (including `ExecuteUpdate`/`ExecuteDelete`) include the tenant or owner condition; another tenant's id returns 404.
- [ ] Raw SQL uses `FromSql`/`ExecuteSql` interpolation or parameters; no concatenation.
- [ ] Endpoints declare auth (policy or `AllowAnonymous` deliberately), typed results and `ProducesProblem` where relevant.
- [ ] Options are validated at startup; no secrets in `appsettings*.json`, tests or logs.
- [ ] Migration reviewed (data loss, long locks, default values) and the `Down` is sensible.
- [ ] Tests cover success, validation failure, authorization failure and cross-tenant access.
- [ ] `dotnet build -warnaserror`, `dotnet format --verify-no-changes` and `dotnet test` pass.

## 13. Production Notes

- Apply migrations as a deployment step (`dotnet ef migrations bundle` or `migrations script --idempotent`), not in `Program.cs` with several instances starting at once. Make migrations backward compatible (expand, deploy, contract) for rolling deploys.
- Health checks: `AddHealthChecks()` with `MapHealthChecks("/healthz")` for liveness, a separate readiness check that includes the database; keep them anonymous but expose no details.
- Graceful shutdown: honor `IHostApplicationLifetime.ApplicationStopping` and the `CancellationToken` in `BackgroundService.ExecuteAsync`; set the host shutdown timeout to match the platform's grace period.
- Behind a reverse proxy, enable forwarded headers explicitly and restrict `KnownProxies` or `KnownNetworks` rather than trusting every sender.
- Telemetry: emit logs, metrics and traces through OpenTelemetry-compatible APIs; backends and dashboards are the job of observability-expert.
- Support windows: .NET 8 and 9 end on 2026-11-10; upgrade by changing `TargetFramework`, SDK and package versions together, then running the full test suite. EF Core 10 only runs on .NET 10.
- Configuration layering order is `appsettings.json`, `appsettings.{Environment}.json`, user-secrets (Development), environment variables, command line; environment variables use `__` for nesting (`ConnectionStrings__Db`).

## 14. Examples

Minimal API with a route group, built-in validation, a typed result, and tenant-scoped read and write (the tenant comes from a validated claim):

```csharp
using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddProblemDetails();
builder.Services.AddValidation();
builder.Services.AddOpenApi();
builder.Services.AddDbContext<AppDb>((sp, o) =>
    o.UseNpgsql(sp.GetRequiredService<IConfiguration>().GetConnectionString("Db")));
builder.Services.AddAuthentication().AddJwtBearer();   // authority and audience: see authentication-expert
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("TenantMember", p => p.RequireAuthenticatedUser().RequireClaim("tenant_id"));

var app = builder.Build();

app.UseExceptionHandler();
app.UseAuthentication();
app.UseAuthorization();
if (app.Environment.IsDevelopment()) app.MapOpenApi();

var orders = app.MapGroup("/orders").RequireAuthorization("TenantMember").WithTags("Orders");

orders.MapGet("/{id:guid}", async Task<Results<Ok<OrderDto>, NotFound>> (
    Guid id, ClaimsPrincipal user, AppDb db, CancellationToken ct) =>
{
    var tenant = TenantOf(user);
    var dto = await db.Orders.AsNoTracking()
        .Where(o => o.TenantId == tenant && o.Id == id)
        .Select(o => new OrderDto(o.Id, o.Number, o.Total, o.Status))
        .SingleOrDefaultAsync(ct);
    return dto is null ? TypedResults.NotFound() : TypedResults.Ok(dto);
});

orders.MapPost("/", async (CreateOrder body, ClaimsPrincipal user, AppDb db, CancellationToken ct) =>
{
    var order = new Order { Id = Guid.CreateVersion7(), TenantId = TenantOf(user), Number = body.Number, Total = body.Total };
    db.Orders.Add(order);
    await db.SaveChangesAsync(ct);
    return TypedResults.Created($"/orders/{order.Id}", new OrderDto(order.Id, order.Number, order.Total, order.Status));
});

orders.MapPost("/{id:guid}/cancel", async Task<Results<NoContent, NotFound>> (
    Guid id, ClaimsPrincipal user, AppDb db, CancellationToken ct) =>
{
    var tenant = TenantOf(user);
    var rows = await db.Orders
        .Where(o => o.TenantId == tenant && o.Id == id && o.Status == "New")   // tenant filter on the write
        .ExecuteUpdateAsync(s => s.SetProperty(o => o.Status, "Cancelled"), ct);
    return rows == 0 ? TypedResults.NotFound() : TypedResults.NoContent();
});

app.Run();

static string TenantOf(ClaimsPrincipal user) =>
    user.FindFirstValue("tenant_id") ?? throw new InvalidOperationException("tenant_id claim is required.");

public sealed record OrderDto(Guid Id, string Number, decimal Total, string Status);

public sealed record CreateOrder
{
    [Required, StringLength(40)] public required string Number { get; init; }
    [Range(0.01, 1_000_000)] public decimal Total { get; init; }
}

public sealed class Order
{
    public Guid Id { get; set; }
    public required string TenantId { get; set; }
    public required string Number { get; set; }
    public decimal Total { get; set; }
    public string Status { get; set; } = "New";
}

public sealed class AppDb(DbContextOptions<AppDb> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();

    protected override void OnModelCreating(ModelBuilder b) =>
        b.Entity<Order>().HasIndex(o => new { o.TenantId, o.Number }).IsUnique();
}

public partial class Program;
```

Options with startup validation and a keyed service (packages: none beyond the shared framework):

```csharp
using System.ComponentModel.DataAnnotations;

builder.Services.AddOptions<PaymentOptions>()
    .BindConfiguration("Payments")
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddKeyedSingleton<IGateway, PrimaryGateway>("primary");
builder.Services.AddKeyedSingleton<IGateway, BackupGateway>("backup");

public sealed class PaymentOptions
{
    [Required, Url] public string BaseUrl { get; init; } = "";
    [Range(1, 60)] public int TimeoutSeconds { get; init; } = 10;
    // Payments:ApiKey is bound from user-secrets in development and from the managed secret store in
    // production; it never appears in appsettings.json, and startup fails if it is missing.
    [Required] public string ApiKey { get; init; } = "";
}

public interface IGateway { Task ChargeAsync(decimal amount, CancellationToken ct); }

public sealed class CheckoutService([FromKeyedServices("primary")] IGateway gateway)
{
    public Task PayAsync(decimal amount, CancellationToken ct) => gateway.ChargeAsync(amount, ct);
}
```

Local secret for that setting, kept out of the repository:

```bash
dotnet user-secrets init --project src/Shop.Api
dotnet user-secrets set "Payments:ApiKey" "<value-from-your-password-manager>" --project src/Shop.Api
```

## 15. Common Mistakes

- **Scoped service injected into a singleton (captive dependency)**: the scoped object lives for the whole app, a `DbContext` is shared across requests and throws concurrency errors. Fix: inject `IServiceScopeFactory` or `IDbContextFactory<T>`, and keep scope validation on in tests.
- **Write by `Id` only in a multi-tenant system**: any authenticated user can update or delete another tenant's row by guessing an id. Fix: tenant condition in the `Where` of every write; return 404 for both missing and foreign rows.
- **`FromSqlRaw` with interpolation or concatenation**: SQL injection. Fix: `FromSql($"... {value}")`, which parameterizes, or `SqlParameter`s.
- **`async void` handlers and fire-and-forget `Task`s**: exceptions crash the process or vanish. Fix: return `Task`, await it, or run background work in a `BackgroundService` with its own scope and logging.
- **`.Result` / `.Wait()` on request paths**: thread pool starvation and, with a synchronization context, deadlocks. Fix: async all the way.
- **Awaiting a `ValueTask` twice or storing it**: undefined behavior. Fix: await once, or call `.AsTask()` when it must be reused.
- **Ignoring `CancellationToken`**: abandoned requests keep querying. Fix: take the token as a handler parameter and pass it down.
- **`ToList()` before `Where`**: loads the table into memory. Fix: keep the query an `IQueryable` until the terminal call.
- **N+1 queries from lazy navigation access in loops**: one query per row. Fix: `Include`, projection, or batched `Contains`.
- **Secrets in `appsettings.json` or committed `.env` files**: they leak through source control and images. Fix: user-secrets locally, managed store in production, rotate anything already committed.
- **Calling `Database.Migrate()` at startup of every replica**: races and long locks during rolling deploys. Fix: run a migration bundle or idempotent script once per release.
- **Using the EF in-memory provider as proof the SQL works**: no constraints, no translation errors. Fix: Testcontainers with the real provider.
- **Trusting `X-Tenant-Id` from the client**: tenant spoofing. Fix: derive the tenant from a validated token claim.
- **Disabling certificate validation to make a dev call work**: the code ships. Fix: trust the development certificate (`dotnet dev-certs https --trust`) or the internal CA.

## 16. References

- [references/minimal-apis.md](references/minimal-apis.md): route groups, TypedResults, endpoint filters, validation, ProblemDetails, OpenAPI configuration and authorization wiring with longer examples.
- [references/ef-core.md](references/ef-core.md): DbContext lifetime, migrations workflow, query patterns, split queries, compiled queries, raw SQL, named query filters and tenant-safe writes.
- [references/testing.md](references/testing.md): xUnit v3 setup, WebApplicationFactory, Testcontainers fixture, test authentication handler, cross-tenant tests and query counting.
- .NET support policy: https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core
- What's new in C# 14: https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-14
- ASP.NET Core minimal APIs: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis/overview
- Validation in ASP.NET Core: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/validation
- OpenAPI in ASP.NET Core: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/overview
- What's new in EF Core 10: https://learn.microsoft.com/en-us/ef/core/what-is-new/ef-core-10.0/whatsnew
- Global query filters: https://learn.microsoft.com/en-us/ef/core/querying/filters
- Options pattern: https://learn.microsoft.com/en-us/dotnet/core/extensions/options
- Safe storage of app secrets in development: https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets
- xUnit.net v3: https://xunit.net/docs/getting-started/v3/getting-started
- Integration tests in ASP.NET Core: https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests
- Testcontainers for .NET: https://dotnet.testcontainers.org/
