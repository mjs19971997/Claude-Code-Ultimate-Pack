# Testing Reference

xUnit v3, `WebApplicationFactory`, Testcontainers for .NET, a test authentication handler, cross-tenant tests and query counting. Verified against xunit.v3 4.0.2, Microsoft.AspNetCore.Mvc.Testing 10.0.14, Testcontainers.PostgreSql 4.16.0, Microsoft.NET.Test.Sdk 18.11.0 and xunit.runner.visualstudio 4.0.1 (NuGet, 2026-10).

## Contents

1. [Project setup](#1-project-setup)
2. [xUnit v3 notes](#2-xunit-v3-notes)
3. [Fixture with Testcontainers and WebApplicationFactory](#3-fixture-with-testcontainers-and-webapplicationfactory)
4. [Test authentication handler](#4-test-authentication-handler)
5. [Tests worth writing](#5-tests-worth-writing)
6. [Counting queries](#6-counting-queries)
7. [Unit tests and time](#7-unit-tests-and-time)
8. [CI notes](#8-ci-notes)

## 1. Project setup

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <OutputType>Exe</OutputType>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="18.11.0" />
    <PackageReference Include="xunit.v3" Version="4.0.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="4.0.1" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="10.0.14" />
    <PackageReference Include="Testcontainers.PostgreSql" Version="4.16.0" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\Shop.Api\Shop.Api.csproj" />
  </ItemGroup>
</Project>
```

- With central package management, keep `Version` only in `Directory.Packages.props`.
- xUnit v3 test projects are executables (`OutputType` `Exe`) that host their own runner. xunit.net documents running them through VSTest (`dotnet test` with `xunit.runner.visualstudio`) and through Microsoft.Testing.Platform; check the current xunit.net and .NET SDK documentation for the `dotnet test` mode that matches your SDK before changing the runner setup.
- Package version numbers above were current in 2026-10; update them rather than copying them blindly.
- `WebApplicationFactory<Program>` needs an accessible entry point: add `public partial class Program;` to the API project when it uses top-level statements.

## 2. xUnit v3 notes

- Package family: `xunit.v3` replaces the v2 `xunit` package. v3 supports .NET 8 or later and .NET Framework 4.7.2 or later. Remove `xunit.abstractions` and `using Xunit.Abstractions;`.
- `IAsyncLifetime.InitializeAsync()` and `DisposeAsync()` return `ValueTask` (they returned `Task` in v2).
- Pass `TestContext.Current.CancellationToken` to async calls inside tests; xUnit analyzers flag calls that omit it, and it cancels work when a test times out or the run is cancelled.
- Fixtures: `IClassFixture<T>` shares one instance per test class; `ICollectionFixture<T>` with `[CollectionDefinition]` and `[Collection("name")]` shares one across classes; use a collection fixture for expensive containers.
- Constructor injection receives fixtures; use the primary constructor of the test class for brevity.
- Classes in different collections may run in parallel; tests in one collection run sequentially. Isolate data per test (new tenant id) instead of disabling parallelism.
- `[Theory]` with `[InlineData]`, `[MemberData]` or `TheoryData<T>` covers input tables, including the validation rules.

## 3. Fixture with Testcontainers and WebApplicationFactory

The fixture owns the container and composes the factory, so it does not depend on whether the factory's own `DisposeAsync` can be overridden. The application reads its connection string lazily from `IConfiguration` (inside the `AddDbContext` callback), which lets the test host supply it.

```csharp
using System.Net.Http.Headers;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Testcontainers.PostgreSql;

public sealed class ApiFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _db = new PostgreSqlBuilder("postgres:17-alpine").Build();
    private WebApplicationFactory<Program>? _factory;

    public async ValueTask InitializeAsync()
    {
        await _db.StartAsync();

        _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(host =>
        {
            host.UseSetting("ConnectionStrings:Db", _db.GetConnectionString());
            host.ConfigureTestServices(services =>
                services.AddAuthentication(TestAuthHandler.Scheme)
                    .AddScheme<AuthenticationSchemeOptions, TestAuthHandler>(TestAuthHandler.Scheme, _ => { }));
        });

        using var scope = _factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDb>();
        await db.Database.MigrateAsync();   // use EnsureCreatedAsync() only when the project has no migrations
    }

    public HttpClient ClientFor(string tenant)
    {
        var client = _factory!.CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.TenantHeader, tenant);
        return client;
    }

    public async ValueTask DisposeAsync()
    {
        if (_factory is not null) await _factory.DisposeAsync();
        await _db.DisposeAsync();
    }
}
```

- `new PostgreSqlBuilder("postgres:17-alpine")` takes the image as a string; pin a tag that matches production. `GetConnectionString()` returns a connection string for the mapped host port.
- Testcontainers starts a resource reaper container that removes containers when the test process exits, including after a crash. Docker (or a compatible runtime) must be available to the test process.
- `UseSetting` and `ConfigureTestServices` run after the application's own registrations, so test overrides win. When replacing a `DbContext` registration instead, remove every descriptor for the context and its options before registering the new provider; supplying the connection string through configuration avoids that.
- Prefer applying real migrations in the fixture so tests exercise the same schema as production.

## 4. Test authentication handler

A handler that trusts a test-only header replaces the real JWT scheme inside the test host. It exists only in the test project and is never registered by the application.

```csharp
using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

public sealed class TestAuthHandler(
    IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder)
    : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    public const string Scheme = "Test";
    public const string TenantHeader = "X-Test-Tenant";

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue(TenantHeader, out var tenant))
        {
            return Task.FromResult(AuthenticateResult.NoResult());   // anonymous request -> 401 on protected routes
        }

        var claims = new[]
        {
            new Claim("tenant_id", tenant.ToString()),
            new Claim(ClaimTypes.NameIdentifier, "user-1"),
        };
        var principal = new ClaimsPrincipal(new ClaimsIdentity(claims, Scheme));
        return Task.FromResult(AuthenticateResult.Success(new AuthenticationTicket(principal, Scheme)));
    }
}
```

- Keep one test per authorization policy with and without the required claim, so a policy edit that opens an endpoint fails a test.

## 5. Tests worth writing

```csharp
public sealed class OrderTenantTests(ApiFixture fx) : IClassFixture<ApiFixture>
{
    private static readonly object NewOrder = new { number = "A-1", total = 10.5m };

    [Fact]
    public async Task Anonymous_request_gets_401()
    {
        var ct = TestContext.Current.CancellationToken;
        using var anon = fx.ClientFor("ignored");
        anon.DefaultRequestHeaders.Remove(TestAuthHandler.TenantHeader);

        var res = await anon.GetAsync($"/orders/{Guid.NewGuid()}", ct);

        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task Invalid_body_gets_400_problem_details()
    {
        var ct = TestContext.Current.CancellationToken;
        using var client = fx.ClientFor($"t-{Guid.NewGuid():N}");

        var res = await client.PostAsJsonAsync("/orders", new { number = "", total = -1 }, ct);

        Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
    }

    [Fact]
    public async Task Another_tenant_cannot_cancel_or_read_the_order()
    {
        var ct = TestContext.Current.CancellationToken;
        using var owner = fx.ClientFor($"t-{Guid.NewGuid():N}");
        using var other = fx.ClientFor($"t-{Guid.NewGuid():N}");

        var created = await owner.PostAsJsonAsync("/orders", NewOrder, ct);
        created.EnsureSuccessStatusCode();
        var dto = await created.Content.ReadFromJsonAsync<OrderDto>(ct);

        var cancel = await other.PostAsync($"/orders/{dto!.Id}/cancel", null, ct);
        var read = await other.GetAsync($"/orders/{dto.Id}", ct);
        var still = await owner.GetFromJsonAsync<OrderDto>($"/orders/{dto.Id}", ct);

        Assert.Equal(HttpStatusCode.NotFound, cancel.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, read.StatusCode);
        Assert.Equal("New", still!.Status);
    }
}
```

The file also needs `using System.Net;` and `using System.Net.Http.Json;`.

- Cover each failure path once: validation (400), unauthenticated (401), wrong policy (403), foreign tenant (404 on read and write), duplicate (409), and a cancelled request where the handler is long-running.
- Generate a fresh tenant id per test so tests do not depend on execution order or on cleaning tables.
- Assert on status code and the response contract, not on database internals; add a direct database assertion (through a scope from `Services`) only to prove that a rejected write changed nothing.

## 6. Counting queries

Attach an interceptor in the test host to count SQL commands and fail when an endpoint issues one query per row.

```csharp
using System.Data.Common;
using Microsoft.EntityFrameworkCore.Diagnostics;

public sealed class CommandCounter : DbCommandInterceptor
{
    private int _count;
    public int Count => Volatile.Read(ref _count);
    public void Reset() => Interlocked.Exchange(ref _count, 0);

    public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
        DbCommand command, CommandEventData eventData,
        InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
    {
        Interlocked.Increment(ref _count);
        return base.ReaderExecutingAsync(command, eventData, result, cancellationToken);
    }
}

// In the factory configuration:
//   var counter = new CommandCounter();
//   host.ConfigureTestServices(s => { s.AddSingleton(counter); s.ConfigureDbContext<AppDb>(o => o.AddInterceptors(counter)); });
// In the test: counter.Reset(); call the endpoint; Assert.True(counter.Count <= 2);
```

- Seed enough rows (for example 20) that an N+1 pattern produces a count well above the expected number.
- Scalar and non-query commands use `ScalarExecutingAsync` and `NonQueryExecutingAsync`; override them too when the endpoint uses `ExecuteUpdate` or aggregates.

## 7. Unit tests and time

- Test domain rules and services without the host. Inject `TimeProvider` and use `FakeTimeProvider` (package Microsoft.Extensions.TimeProvider.Testing) to move time forward deterministically: `fake.Advance(TimeSpan.FromMinutes(5))`.
- Test typed endpoint handlers as plain methods when they are static: call them with a stub and assert on `Results<Ok<T>, NotFound>` content via the `.Result` property.
- Avoid mocking `DbContext`. Use the real provider in Testcontainers for query behavior; use a fake of your own repository or query interface for pure logic.
- The EF in-memory provider does not enforce constraints, transactions or SQL translation; do not use it as evidence that a query works. The SQLite provider is closer but differs from most production engines.

## 8. CI notes

- Build once, test without rebuilding: `dotnet build -c Release` then `dotnet test -c Release --no-build`.
- Run `dotnet format --verify-no-changes` and `dotnet list package --vulnerable --include-transitive` as separate gates.
- The CI runner needs Docker access for Testcontainers; pull and pin image tags, and use a registry mirror if rate limits apply.
- Keep integration tests in their own project so unit tests stay fast and can run without Docker (`dotnet test tests/Shop.UnitTests`).
- Do not put real credentials in test configuration; containers use generated or throwaway passwords that Testcontainers manages.
