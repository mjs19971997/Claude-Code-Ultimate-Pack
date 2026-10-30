# Minimal APIs Reference

Longer examples for ASP.NET Core 10 minimal APIs: route groups, typed results, endpoint filters, built-in validation, ProblemDetails, OpenAPI and authorization wiring. Verified against ASP.NET Core 10.0.14 and Microsoft.AspNetCore.OpenApi 10.0.14 (2026-10).

## Contents

1. [Route groups and feature layout](#1-route-groups-and-feature-layout)
2. [Typed results](#2-typed-results)
3. [Endpoint filters](#3-endpoint-filters)
4. [Validation](#4-validation)
5. [Errors and ProblemDetails](#5-errors-and-problemdetails)
6. [OpenAPI](#6-openapi)
7. [Authorization wiring](#7-authorization-wiring)
8. [Rate limiting and CORS](#8-rate-limiting-and-cors)

## 1. Route groups and feature layout

One extension method per feature keeps `Program.cs` declarative. Group-level calls (`RequireAuthorization`, `WithTags`, `AddEndpointFilter`, `RequireRateLimiting`) apply to every endpoint in the group, including nested groups.

```csharp
public static class OrderEndpoints
{
    public static IEndpointRouteBuilder MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/orders")
            .RequireAuthorization("TenantMember")
            .WithTags("Orders");

        group.MapGet("/", ListAsync);
        group.MapGet("/{id:guid}", GetAsync).WithName("GetOrder");
        group.MapPost("/", CreateAsync);
        return app;
    }

    private static async Task<Ok<List<OrderDto>>> ListAsync(
        ClaimsPrincipal user, AppDb db, CancellationToken ct, int page = 1)
    {
        var tenant = user.FindFirstValue("tenant_id") ?? throw new InvalidOperationException("tenant_id claim is required.");
        var items = await db.Orders.AsNoTracking()
            .Where(o => o.TenantId == tenant)
            .OrderBy(o => o.Id)
            .Skip((Math.Max(page, 1) - 1) * 50).Take(50)
            .Select(o => new OrderDto(o.Id, o.Number, o.Total, o.Status))
            .ToListAsync(ct);
        return TypedResults.Ok(items);
    }

    // GetAsync and CreateAsync follow the same shape as the examples in SKILL.md.
}
```

- Route constraints (`{id:guid}`, `{page:int:min(1)}`) reject malformed input with 404 before the handler runs.
- Parameters bind from route, query, headers (`[FromHeader]`), the body (a complex type on POST/PUT/PATCH), or DI services (any registered service type, no attribute needed). Add `[FromBody]`, `[FromServices]` or `[AsParameters]` when the source is ambiguous.
- `[AsParameters]` on a record groups many parameters into one type; keep it for handlers with more than four inputs.
- `WithName` is required for link generation (`TypedResults.CreatedAtRoute`) and gives the OpenAPI operation an id.

## 2. Typed results

```csharp
app.MapGet("/orders/{id:guid}", async Task<Results<Ok<OrderDto>, NotFound, ProblemHttpResult>> (
    Guid id, AppDb db, CancellationToken ct) =>
{
    var dto = await db.Orders.AsNoTracking()
        .Where(o => o.Id == id)               // add the tenant condition in real code
        .Select(o => new OrderDto(o.Id, o.Number, o.Total, o.Status))
        .SingleOrDefaultAsync(ct);
    return dto is null ? TypedResults.NotFound() : TypedResults.Ok(dto);
});
```

- `Results<T1, ..., Tn>` lists every possible response. OpenAPI generation reads it, and a handler that returns a type outside the list does not compile.
- Common types: `Ok<T>`, `Created<T>`, `CreatedAtRoute<T>`, `NoContent`, `NotFound`, `BadRequest`, `Conflict`, `UnprocessableEntity`, `ProblemHttpResult` (`TypedResults.Problem(...)`), `ValidationProblem`.
- Unit tests can assert on the returned type directly (`Assert.IsType<Ok<OrderDto>>(result.Result)`) without starting a host.
- Prefer `TypedResults` over `Results` (the factory that returns `IResult`) in new code; `Results.*` hides the concrete type.

## 3. Endpoint filters

An endpoint filter wraps the handler and can read or replace arguments and the result. Use filters for cross-cutting request checks, not business rules.

```csharp
public sealed class RequireIdempotencyKey : IEndpointFilter
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next)
    {
        var key = ctx.HttpContext.Request.Headers["Idempotency-Key"].ToString();
        if (string.IsNullOrWhiteSpace(key) || key.Length > 100)
        {
            return TypedResults.Problem(
                title: "Idempotency-Key header is required.",
                statusCode: StatusCodes.Status400BadRequest);
        }
        return await next(ctx);
    }
}

// Attach to one endpoint or to a whole group.
orders.MapPost("/", CreateAsync).AddEndpointFilter<RequireIdempotencyKey>();
```

- A lambda form exists: `.AddEndpointFilter(async (ctx, next) => { ...; return await next(ctx); })`. Use `ctx.GetArgument<T>(index)` to read a bound argument.
- Filters registered on a group run before filters registered on the endpoint; order of registration is the order of execution.
- Filters do not run for requests rejected earlier by authentication, authorization, routing or rate limiting middleware.

## 4. Validation

```csharp
builder.Services.AddValidation();   // Microsoft.Extensions.Validation, new in .NET 10

public sealed record CreateOrder
{
    [Required, StringLength(40)] public required string Number { get; init; }
    [Range(0.01, 1_000_000)] public decimal Total { get; init; }
}
```

- `AddValidation()` registers a source-generated resolver and an endpoint filter that validates DataAnnotations on handler parameters, including nested properties and collections. A failure returns 400 with a ProblemDetails body listing the errors.
- The generator discovers types only in the assembly that calls `AddValidation`. Handlers and DTOs in another project need that project to register validation as well; otherwise invalid requests reach the handler.
- `ValidatableTypeAttribute` and `SkipValidationAttribute` are marked experimental in .NET 10; suppress the diagnostic deliberately or avoid them.
- Implement `IValidatableObject` for cross-field rules. For rules that need a database lookup, validate in the handler or a filter and return `TypedResults.ValidationProblem(errors)`.
- Validation checks shape, not authorization: never accept `TenantId`, `OwnerId` or `Status` from the body to "validate" them; leave those fields out of the DTO.
- Before .NET 10 there was no built-in minimal API validation; projects on older targets use FluentValidation or a custom filter. Keep the existing library when migrating is not a goal.

## 5. Errors and ProblemDetails

```csharp
builder.Services.AddProblemDetails(o =>
    o.CustomizeProblemDetails = ctx => ctx.ProblemDetails.Extensions["traceId"] = ctx.HttpContext.TraceIdentifier);

var app = builder.Build();
app.UseExceptionHandler();      // unhandled exceptions become ProblemDetails (500)
app.UseStatusCodePages();       // bare 401/403/404 responses get a ProblemDetails body
```

- Do not return exception messages or stack traces to clients outside Development. `UseDeveloperExceptionPage` is on by default only in Development.
- Map expected conflicts explicitly: catch `DbUpdateConcurrencyException` or a unique-violation in the handler and return `TypedResults.Conflict()` or `TypedResults.Problem(statusCode: 409)`.
- Add `ProducesProblem(StatusCodes.Status409Conflict)` to the endpoint when the response type is not already visible in `Results<...>`.

## 6. OpenAPI

```csharp
builder.Services.AddOpenApi(options =>
{
    options.OpenApiVersion = Microsoft.OpenApi.OpenApiSpecVersion.OpenApi3_1;   // pin the document version
    options.AddDocumentTransformer((document, context, ct) =>
    {
        document.Info.Title = "Shop API";
        return Task.CompletedTask;
    });
});

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();   // serves /openapi/v1.json
}
```

- Package: Microsoft.AspNetCore.OpenApi. It generates the document only; a viewer UI (Swagger UI, Scalar and others) is a separate package, so check the current docs for the one you choose.
- .NET 10 defaults to OpenAPI 3.1 and uses Microsoft.OpenApi 2.x. Document, operation and schema transformers written for the 1.x object model need updates. ASP.NET Core 11 previews change the default to 3.2 and move to Microsoft.OpenApi 3.x; pin `OpenApiVersion` and test generated clients before upgrading.
- Expose the document in production only when the API is meant to be public; otherwise generate it at build time or in CI and publish it as an artifact.
- Metadata that improves the document: `WithName`, `WithSummary`, `WithDescription`, `WithTags`, `Produces<T>`, `ProducesProblem`, `Accepts<T>`, and XML or attribute descriptions where supported (check the current docs for XML comment support in your SDK version).

## 7. Authorization wiring

```csharp
builder.Services.AddAuthorizationBuilder()
    .SetFallbackPolicy(new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build())
    .AddPolicy("TenantMember", p => p.RequireAuthenticatedUser().RequireClaim("tenant_id"))
    .AddPolicy("OrdersWrite", p => p.RequireClaim("scope", "orders.write"));

app.MapHealthChecks("/healthz").AllowAnonymous();
orders.MapPost("/", CreateAsync).RequireAuthorization("OrdersWrite");
```

- The fallback policy protects every endpoint that has no explicit authorization metadata, so a new endpoint is closed by default. Mark public endpoints with `AllowAnonymous()`.
- Call `UseAuthentication()` before `UseAuthorization()`. With `WebApplication`, they are added automatically when you register authentication and authorization services, but calling them explicitly keeps the order visible when other middleware sits between them.
- Resource-based checks use `IAuthorizationService.AuthorizeAsync(user, resource, requirementOrPolicy)` after loading the resource (still loaded with the tenant condition); a failed check returns 404 or 403 consistently with the tenant rule.
- Token validation settings (authority, audience, clock skew) and scopes design belong to authentication-expert and authorization-expert.

## 8. Rate limiting and CORS

```csharp
builder.Services.AddRateLimiter(o =>
{
    o.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    o.AddFixedWindowLimiter("api", l =>
    {
        l.PermitLimit = 100;
        l.Window = TimeSpan.FromMinutes(1);
    });
});
builder.Services.AddCors(o => o.AddPolicy("web", p =>
    p.WithOrigins("https://app.example.com").WithMethods("GET", "POST").WithHeaders("Authorization", "Content-Type")));

app.UseRateLimiter();
app.UseCors("web");
orders.RequireRateLimiting("api");
```

- List explicit origins; `AllowAnyOrigin` together with credentials is rejected by the framework, and a wildcard on an authenticated API defeats the browser's protection.
- A fixed window limiter is per process. Behind several instances, partition by user or tenant and use a shared limiter (gateway or distributed store) when limits must be global.
