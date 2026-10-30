---
name: nestjs-expert
description: >-
  Builds and reviews NestJS 12 applications: modules, providers and dependency injection scopes, controllers, the request lifecycle (middleware, guards, interceptors, pipes, exception filters), validation with ValidationPipe or Standard Schema, configuration, auth guards, testing with Test.createTestingModule and supertest, microservice transports, CQRS, and the Express, Fastify and Node HTTP adapters. Use when writing or reviewing NestJS modules, guards, pipes, interceptors or filters, debugging execution order or DI errors, setting up validation and config, writing unit or e2e tests, or upgrading from NestJS 11. Not for plain Node.js runtime topics (use nodejs-architect), Express without Nest (use expressjs-expert), or GraphQL schema design (use graphql-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# NestJS Expert

This skill covers application structure and behavior in NestJS: modules and dependency injection, the order in which request components run, validation and configuration, authentication and authorization guards, testing, microservice transports and the 11 to 12 upgrade. HTTP framework details of Express and Fastify, and Node.js runtime behavior, are handled by their own skills.

> Verified against NestJS 12.3.2 (`@nestjs/core`, `common`, `testing`, `platform-express`, `platform-fastify`, `platform-node`, `microservices`), `@nestjs/config` 12.0, `@nestjs/jwt` 12.0, `@nestjs/cqrs` 12.1, `@nestjs/graphql` 14.1, class-validator 0.15, class-transformer 0.5, TypeScript 6, Vitest 5, Jest 30, supertest 7.3, Node.js 20.19+/22.12+/24/26 (2026-10).

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

- Covered: modules, providers and scopes, controllers, the request lifecycle, pipes and validation, exception filters, interceptors, guards, `@nestjs/config`, `@nestjs/jwt`, security headers, CORS and CSRF, throttling, lifecycle hooks and shutdown, testing, microservice transports, CQRS, HTTP adapters, and the v11 to v12 upgrade.
- Not covered: Node.js internals, streams and workers (nodejs-architect), Express middleware ecosystem (expressjs-expert), GraphQL schema and resolver design (graphql-expert; Nest only hosts it through `@nestjs/graphql`), ORM modeling (prisma-expert, postgresql-expert), deep authentication design (authentication-expert, authorization-expert), DDD and clean architecture theory (ddd-expert, clean-architecture-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Version 12 | All core packages are ESM-only. CommonJS apps still work through `require(esm)` (Node 20.19+, 22.12+); `nest new` offers CommonJS or ESM layouts. Peer TypeScript is 6 for `@nestjs/schematics`; `nest upgrade` migrates packages |
| Node requirement | Running an app: 20.19+ or 22.12+ (also 24, 26). The CLI generators (`nest new`, `generate`, `upgrade`) need 22.22.3+, 24.15+ or 26+ |
| Request pipeline | Middleware, guards, interceptors (before), pipes, handler, service, interceptors (after, reversed), exception filters. Details in the lifecycle reference |
| Providers | `@Injectable()`; custom providers `useClass`, `useValue`, `useFactory`, `useExisting`; scopes `DEFAULT` (singleton), `REQUEST`, `TRANSIENT`; durable providers group request scopes by tenant |
| Modules | Feature modules encapsulate providers; `exports` shares them; `@Global()` sparingly; dynamic modules via `forRoot`/`forRootAsync` or `ConfigurableModuleBuilder` |
| Validation | `ValidationPipe` with class-validator (`whitelist`, `forbidNonWhitelisted`, `transform`, `errorFormat: 'list' \| 'grouped'`), or `StandardSchemaValidationPipe` with Zod, Valibot or ArkType via `@Body({ schema })` |
| Config | `@nestjs/config` `ConfigModule.forRoot({ isGlobal, validationSchema })`; `validationSchema` accepts any Standard Schema (Joi 18+ still works); `registerAs()` namespaces; `ConfigService.getOrThrow()` |
| Security built-ins | `app.useSecurityHeaders()` and `app.enableCsrfProtection()` (12.1+), `app.enableCors()`, `@nestjs/throttler`; first-party `@nestjs/authentication` and `@nestjs/authorization` exist as early 0.x packages |
| Adapters | Express (default, v5), Fastify (v5), and `NodeAdapter` from `@nestjs/platform-node` (recommended by the docs since 12.3, fastest in their benchmarks) |
| Testing | `Test.createTestingModule`, `overrideProvider`, `useMocker`, supertest or `app.inject()` on Fastify; Vitest is the default for generated ESM projects, Jest 30 for CommonJS |
| Microservices | Transports: TCP (default), Redis, NATS (v3 client), MQTT, gRPC, RabbitMQ, Kafka, plus custom strategies; `@MessagePattern` (request-response) and `@EventPattern` (events); hybrid apps with `connectMicroservice` |
| Observability | `@nestjs/observe` SDK plugged into the Nest lifecycle through the `instrument` option; `ConsoleLogger` has a JSON mode and structured params |

## 3. Workflow

1. Identify the Nest major, adapter, test runner and module format (CommonJS or ESM) from `package.json` and `nest-cli.json`.
2. Model feature modules around business capabilities; decide what each module exports.
3. Write DTOs and validation first; bind the global pipe in `main.ts` and in the e2e setup helper.
4. Put business logic in providers; keep controllers to routing, parameter binding and response mapping.
5. Decide the cross-cutting layer by purpose: middleware for raw request concerns, guards for access, interceptors for mapping and timing, pipes for input, filters for error shape.
6. Load configuration through `ConfigModule` with a schema; inject `ConfigService` or typed `registerAs` namespaces.
7. Enable shutdown hooks and health checks; choose the adapter.
8. Write unit tests for providers, e2e tests for routes with real guards and pipes, and run both in CI.

## 4. Decision Rules

- Middleware versus guard: middleware runs before the handler is known and has no `ExecutionContext`; use a guard for authentication and authorization decisions.
- Guard versus interceptor versus pipe: guards decide whether to run, interceptors wrap execution and the result, pipes transform or validate arguments.
- Exception filters handle errors thrown from guards, interceptors, pipes, handlers and services. Errors thrown in middleware reach only global filters.
- `class-validator` DTO classes for decorator-based codebases; Standard Schema (Zod and similar) when schemas are shared with clients or already exist. Do not mix both on the same parameter.
- Singleton scope by default. Use `REQUEST` scope only when per-request state must live in a provider, knowing it bubbles up to every consumer and creates instances per request; prefer `AsyncLocalStorage`-based context, passing values as arguments, or durable providers for multi-tenant keys.
- Feature module versus shared: share through an explicit `exports`; avoid a catch-all `SharedModule` that imports everything; use `@Global()` for config, logging and similar only.
- Adapter: Express for maximum middleware compatibility; Fastify for plugins and its schema/route features; `NodeAdapter` for lowest overhead when the app does not need Express-only APIs (`res.render()`, `res.download()`, `req.accepts()` are missing there).
- Transport: Redis, NATS or RabbitMQ for simple messaging; Kafka for log-based streaming and replay; gRPC for typed RPC between services; TCP for internal prototypes only.
- CQRS only when read and write models diverge or commands need sagas and events; a plain service layer is simpler for CRUD.
- Authentication: verify tokens in a guard (`@nestjs/jwt` with a fixed algorithm list); for sign-in flows, sessions, MFA and API keys evaluate the first-party `@nestjs/authentication` package after checking its current maturity.

## 5. Coding Standards

- One feature folder per module with `*.module.ts`, `*.controller.ts`, `*.service.ts`, `dto/`, `entities/` or schema files.
- Constructor injection with `private readonly` parameters; inject abstractions through tokens (`@Inject(TOKEN)`) when swapping implementations.
- Use concrete classes for DTOs: interfaces and generics leave no runtime metadata, and a type-only import (`import type { CreateUserDto }`) erases the class, so the pipe cannot validate it.
- DTOs for input, separate response DTOs or serialization rules for output; never return ORM entities that contain secrets.
- Throw built-in `HttpException` subclasses (`NotFoundException`, `ConflictException`) from services for HTTP-visible failures, or domain errors mapped by a filter; use `errorCode` on `HttpExceptionOptions` for machine-readable codes.
- `ParseUUIDPipe`, `ParseIntPipe` and validated param DTOs for path parameters.
- ESM projects: relative imports end in `.js`, use `import.meta.dirname`, and `await bootstrap()` at top level; CommonJS projects omit extensions.
- Decorators: use `Reflector.createDecorator<T>()` for custom metadata rather than raw `SetMetadata` strings.
- Read configuration only through `ConfigService`; do not touch `process.env` in providers.

## 6. Project Structure

```
.
├── nest-cli.json
├── package.json                  # "type": "module" for ESM projects
├── tsconfig.json                 # nodenext, experimentalDecorators, emitDecoratorMetadata
├── src/
│   ├── main.ts                   # bootstrap: adapter, global pipe, shutdown hooks
│   ├── app.module.ts             # imports, APP_GUARD / APP_PIPE / APP_FILTER providers
│   ├── configure-app.ts          # shared setup used by main.ts and e2e tests
│   ├── config/                   # registerAs() namespaces and the env schema
│   ├── common/                   # guards, filters, interceptors, decorators
│   ├── auth/                     # auth.guard.ts, roles.decorator.ts, auth.module.ts
│   └── users/
│       ├── dto/create-user.dto.ts
│       ├── users.controller.ts
│       ├── users.service.ts
│       ├── users.module.ts
│       └── users.service.spec.ts
└── test/
    └── users.e2e-spec.ts
```

## 7. Design Patterns

- **Module per feature** with a narrow public surface (`exports`).
- **Global enhancers through tokens**: register guards, pipes, filters and interceptors with `APP_GUARD`, `APP_PIPE`, `APP_FILTER`, `APP_INTERCEPTOR` in a module so they receive dependency injection; `app.useGlobal*()` instances do not.
- **Decorator plus guard**: `@Roles([...])` or `@Public()` created with `Reflector.createDecorator`, read with `reflector.getAllAndOverride()` in a guard.
- **Dynamic module**: `forRoot`/`forRootAsync` for configurable infrastructure modules; `ConfigurableModuleBuilder` to generate them.
- **Interceptor chain**: logging/timing, response mapping, caching, timeout (RxJS `timeout`), error translation with `catchError`.
- **Exception filter**: one global filter that maps domain errors to responses and logs unexpected errors; extend `BaseExceptionFilter` to keep default behavior.
- **CQRS**: `CqrsModule.forRoot()`, commands extending `Command<TResult>`, `@CommandHandler`, `@QueryHandler`, `@EventsHandler`, sagas. See [references/microservices-and-cqrs.md](references/microservices-and-cqrs.md).
- **Hybrid application**: `app.connectMicroservice()` plus `app.startAllMicroservices()` to serve HTTP and a message transport from one codebase.

## 8. Best Practices

- Bind the validation pipe globally with `whitelist: true`, `forbidNonWhitelisted: true`, `transform: true`.
- Share bootstrap configuration in one function (`configureApp(app)`) so tests exercise the same pipes, filters and prefix as production.
- Call `app.enableShutdownHooks()` so `SIGTERM` runs `onModuleDestroy`, `beforeApplicationShutdown` and `onApplicationShutdown`; close pools in those hooks.
- Give each module a single responsibility and avoid circular imports; if unavoidable, use `forwardRef()` and treat it as a design smell.
- Lifecycle hooks run per component hierarchy level in v12 and do not run for request-scoped providers; do not depend on hook order across unrelated providers.
- Use `routeConflictPolicy` and `routeResolutionStrategy: 'specificity'` options in `NestFactory.create` to catch `@Get(':id')` shadowing `@Get('me')` on order-sensitive adapters.
- Use `Logger` with a context, JSON logging in production (`new ConsoleLogger({ json: true })`), and `bufferLogs: true` when attaching a custom logger.
- Keep microservice handlers thin and idempotent; validate `@Payload()` with the same pipes.

## 9. Performance

- Avoid `Scope.REQUEST`: it re-instantiates the provider and every dependent controller and provider per request. Prefer singletons plus `AsyncLocalStorage`, or durable providers.
- Adapter choice matters only for lightweight routes; the docs' benchmark shows `NodeAdapter` about 50% above Express and about 5% above Fastify on trivial routes. Database and network time usually dominate.
- Make `ClassSerializerInterceptor` and deep `class-transformer` conversions opt-in on hot routes; plain objects are cheaper than class instances.
- Cache with the caching module and explicit TTLs, or at the edge; never cache per-user responses under a shared key.
- Use `ConfigModule.forRoot({ cache: true })` to avoid repeated `process.env` reads on hot paths.
- Build with the SWC builder (`nest start -b swc` or `"builder": "swc"` in `nest-cli.json`) for faster rebuilds; enable type-check separately.
- Offload CPU-heavy work to workers or queues (queue module with BullMQ) rather than the request thread.
- Paginate every list endpoint with a maximum page size enforced by validation.

## 10. Security

- Validation: `ValidationPipe({ whitelist: true, forbidNonWhitelisted: true })` strips or rejects unknown properties, preventing mass assignment. With Zod use `z.strictObject()` to reject unknown keys.
- Authentication: verify JWT signature, expiry and an explicit `algorithms` list in a guard; store secrets in configuration validated at startup (minimum length); set short access-token lifetimes.
- Authorization: a role guard is route-level only. Check ownership and tenant inside the service for each resource, on reads and on writes (update and delete queries must include the tenant or owner condition).
- Headers and CSRF: `app.useSecurityHeaders()` and `app.enableCsrfProtection()` (12.1+) cover Helmet-equivalent headers and Fetch-Metadata based CSRF without extra packages; call them right after `NestFactory.create()`. Keep the content security policy strict: avoid inline scripts and styles, or allow them with nonces or hashes. Cookie-based sessions still need `SameSite` and `Secure`.
- CORS: `app.enableCors({ origin: [...explicit origins], methods: [...], credentials: true })`; never reflect arbitrary origins with credentials. On Fastify list non-simple methods explicitly.
- Rate limiting: `@nestjs/throttler` with `ThrottlerGuard` as `APP_GUARD`; stricter limits on login and password reset; use a shared store when running several instances.
- Errors: Nest returns a generic 500 body for non-HTTP exceptions; do not echo internal messages from custom filters. Set `disableErrorMessages: true` on the validation pipe only if clients must not see validation details.
- Proxy trust: configure trust for `X-Forwarded-*` explicitly (`trustProxy`/`NodeAdapter({ trustProxy })`) and only for known proxies.
- File uploads: limit size and type, store outside the web root, generate server-side names.
- Dependencies: `npm audit`, lockfile, pinned majors across all `@nestjs/*` packages (they must share a major).

## 11. Testing

- Unit tests: `Test.createTestingModule({ providers: [Service, { provide: Dep, useValue: fake }] }).compile()`, then `moduleRef.get(Service)`; or `useMocker()` for auto-mocks. Use `moduleRef.resolve()` for request-scoped or transient providers.
- E2E tests: import the real `AppModule` (or a feature module), `moduleRef.createNestApplication()`, apply the same global setup (`configureApp(app)`), `await app.init()`, call `request(app.getHttpServer())`, and `await app.close()` in `afterAll`.
- Fastify: create with `new FastifyAdapter()`, `await app.getHttpAdapter().getInstance().ready()`, and call `app.inject({ method, url })`.
- Override providers with `.overrideProvider(X).useValue(...)`; override global guards registered via `APP_GUARD` by registering `{ provide: APP_GUARD, useExisting: MyGuard }` plus `MyGuard` as a provider.
- Environment variables must be present before `AppModule` is imported because `ConfigModule.forRoot()` runs at import time: set them in the runner config (`test.env` in Vitest) or a setup file.
- Vitest with decorators needs an SWC plugin (for example `unplugin-swc`) so `emitDecoratorMetadata` works; Jest on ESM Nest 12 needs Node 24.9+ to load the ESM-only packages.
- Test the failure paths: 400 for unknown properties, 401 without token, 403 for wrong role, 404 for missing resources.
- Full recipes: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] All `@nestjs/*` packages share the same major (12.x) and Node meets the requirement.
- [ ] Global `ValidationPipe` (or Standard Schema pipe) is set with whitelist rules, also in e2e setup.
- [ ] Controllers contain no business logic; services do not read `process.env`.
- [ ] No `Scope.REQUEST` without a reason; no `new Service()` for providers.
- [ ] Guards cover every non-public route (global `APP_GUARD` with `@Public()` opt-out is safest).
- [ ] Resource ownership and tenant filters apply to reads and writes.
- [ ] Exception filters registered through `APP_FILTER` where they need DI; no swallowed errors in interceptors.
- [ ] Config validated at startup; secrets not hard-coded or logged.
- [ ] `enableShutdownHooks()` is called; connections close in lifecycle hooks.
- [ ] CORS origins explicit; security headers and CSRF protection enabled when serving browsers.
- [ ] Tests cover happy and failure paths and close the app.
- [ ] No circular dependencies hidden behind `forwardRef` without justification.

## 13. Production Notes

- Health: use `@nestjs/terminus` (12.1); custom indicators use `HealthIndicatorService` (`check(key).up()/down()/attempt()`), the old `HealthIndicator` base class and `HealthCheckError` were removed in 12. Expose separate liveness and readiness endpoints.
- Shutdown: `enableShutdownHooks()` plus a platform grace period longer than your drain time; the Express adapter drains in-flight requests on shutdown in v12. Shutdown hooks on Windows support `SIGINT` and `SIGBREAK` but not `SIGTERM`.
- Serverless: CommonJS Nest 12 on AWS Lambda needs `NODE_OPTIONS=--experimental-require-module` because Lambda disables `require(esm)` by default.
- Observability: `@nestjs/observe` or OpenTelemetry preloaded with `--import`; in a CommonJS app that depends on ESM-only packages, OpenTelemetry's loader hook may be needed for HTTP spans.
- Versioning and prefixes: `app.setGlobalPrefix('api')` and `app.enableVersioning()` before listen; CSRF exclusions resolve after init.
- Reverse proxy: terminate TLS at the proxy and set trust; see nginx-expert.
- Upgrades: run `nest upgrade --dry-run` first; read the lifecycle-ordering, `@Optional()` inheritance and NATS v3 notes. See [references/v12-upgrade-and-platform.md](references/v12-upgrade-and-platform.md).

## 14. Examples

Bootstrap and shared setup (ESM):

```ts
// src/configure-app.ts
import { type INestApplication, ValidationPipe } from '@nestjs/common';

export function configureApp(app: INestApplication): void {
  app.useGlobalPipes(
    new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }),
  );
}
```

```ts
// src/main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { configureApp } from './configure-app.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useSecurityHeaders();           // 12.1+; call right after create()
  app.enableCsrfProtection();         // 12.1+; only relevant for cookie-authenticated browsers
  app.enableCors({ origin: ['https://app.example.com'], credentials: true });
  configureApp(app);
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

DTO, controller and service with role-restricted creation:

```ts
// src/users/dto/create-user.dto.ts
import { IsEmail, IsString, MinLength } from 'class-validator';

export class CreateUserDto {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(12)
  password: string;
}
```

```ts
// src/users/users.controller.ts
import { Body, Controller, Get, Param, ParseUUIDPipe, Post } from '@nestjs/common';
import { Roles } from '../auth/roles.decorator.js';
import { CreateUserDto } from './dto/create-user.dto.js';
import { UsersService } from './users.service.js';

@Controller('users')
export class UsersController {
  constructor(private readonly users: UsersService) {}

  @Post()
  @Roles(['admin'])
  create(@Body() dto: CreateUserDto) {
    return this.users.create(dto);
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.users.findOne(id);
  }
}
```

Global authentication guard with `@Public()` and `@Roles()` metadata, registered once through `APP_GUARD`:

```ts
// src/auth/roles.decorator.ts
import { Reflector } from '@nestjs/core';
export const Roles = Reflector.createDecorator<string[]>();
export const Public = Reflector.createDecorator<boolean>();
```

```ts
// src/auth/auth.guard.ts
import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { JwtService } from '@nestjs/jwt';
import { Public, Roles } from './roles.decorator.js';

interface AccessTokenPayload { sub: string; roles?: string[] }
interface AuthenticatedRequest {
  headers: Record<string, string | string[] | undefined>;
  user?: AccessTokenPayload;
}

@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private readonly jwt: JwtService, private readonly reflector: Reflector) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const targets = [context.getHandler(), context.getClass()];
    if (this.reflector.getAllAndOverride(Public, targets)) return true;

    const request = context.switchToHttp().getRequest<AuthenticatedRequest>();
    const [type, token] = String(request.headers.authorization ?? '').split(' ');
    if (type !== 'Bearer' || !token) throw new UnauthorizedException();

    let payload: AccessTokenPayload;
    try {
      payload = await this.jwt.verifyAsync<AccessTokenPayload>(token, { algorithms: ['HS256'] });
    } catch {
      throw new UnauthorizedException();
    }
    request.user = payload;

    const required = this.reflector.getAllAndOverride(Roles, targets);
    return !required || required.some((role) => payload.roles?.includes(role)); // false -> 403
  }
}
```

```ts
// src/app.module.ts (excerpt)
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      validationSchema: z.object({
        PORT: z.coerce.number().default(3000),
        JWT_SECRET: z.string().min(32),
      }),
    }),
    JwtModule.registerAsync({
      global: true,
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.getOrThrow<string>('JWT_SECRET'),
        signOptions: { expiresIn: '15m' },
      }),
    }),
    UsersModule,
  ],
  providers: [{ provide: APP_GUARD, useClass: AuthGuard }],
})
export class AppModule {}
```

E2E test (Vitest, supertest) covering 401, 400 for unknown properties, 403 and success:

```ts
import { type INestApplication } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterAll, beforeAll, describe, it } from 'vitest';
import { AppModule } from '../src/app.module.js';
import { configureApp } from '../src/configure-app.js';

describe('Users (e2e)', () => {
  let app: INestApplication;
  let admin: string;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleRef.createNestApplication();
    configureApp(app);
    await app.init();
    admin = await app.get(JwtService).signAsync({ sub: 'u1', roles: ['admin'] });
  });
  afterAll(() => app.close());

  it('401 without a token', () => request(app.getHttpServer()).post('/users').send({}).expect(401));

  it('400 on unknown properties', () =>
    request(app.getHttpServer())
      .post('/users')
      .set('Authorization', `Bearer ${admin}`)
      .send({ email: 'a@example.com', password: 'a-long-password', isAdmin: true })
      .expect(400));

  it('201 for an admin with a valid body', () =>
    request(app.getHttpServer())
      .post('/users')
      .set('Authorization', `Bearer ${admin}`)
      .send({ email: 'a@example.com', password: 'a-long-password' })
      .expect(201));
});
```

## 15. Common Mistakes

- **Wrong mental model of the pipeline**: guards run before interceptors and pipes; exception filters run last and apply to the whole chain. Pipes never run before guards.
- **Assuming a global filter always wins**: filters resolve route first, then controller, then global, and only one handles the exception. Middleware errors reach only global filters.
- **Pipes order on parameters**: with several decorated parameters, pipes run from the last parameter to the first.
- **Business logic in controllers**: untestable and hard to reuse; move it to providers.
- **`import type` for DTOs or injected classes**: erases the runtime class, breaking validation metadata and DI tokens.
- **`new SomeService()`**: bypasses DI. Register providers and inject them.
- **`Scope.REQUEST` everywhere**: every consumer becomes request-scoped and slower, and lifecycle hooks do not run for it.
- **Reading `process.env` in services**: bypasses validation. Inject `ConfigService`.
- **No global validation pipe**: unvalidated bodies reach services; add `whitelist` and `forbidNonWhitelisted`.
- **`useGlobalGuards(new Guard())` when the guard needs DI**: dependencies are not injected. Use `APP_GUARD`.
- **Setting environment variables inside a test after imports**: `ConfigModule.forRoot()` already ran; configure the runner instead.
- **Role guard as the only authorization**: it cannot know which record is requested; enforce ownership and tenant in the service.
- **Forgetting `enableShutdownHooks()`**: pools stay open and in-flight work is cut on `SIGTERM`.
- **Mixing `@nestjs/*` majors**: packages must move together; run `nest upgrade`.
- **Swallowing errors in an interceptor `catchError`**: rethrow or map to an `HttpException`.
- **Treating `@Get(':id')` before `@Get('me')` as harmless**: on Express it shadows the later route; reorder or enable `routeResolutionStrategy: 'specificity'`.

## 16. References

- [references/request-lifecycle.md](references/request-lifecycle.md): the verified execution order with a runnable proof, per-component rules, exception paths, scopes and lifecycle hooks.
- [references/testing.md](references/testing.md): unit and e2e recipes for Vitest and Jest, Fastify `inject`, overriding global enhancers, request-scoped providers, microservice tests, Vitest configuration.
- [references/microservices-and-cqrs.md](references/microservices-and-cqrs.md): transports, message and event patterns, hybrid apps, client proxies, validation and errors over RPC, CQRS buses and sagas.
- [references/v12-upgrade-and-platform.md](references/v12-upgrade-and-platform.md): NestJS 11 to 12 changes, ESM and CommonJS setups, adapters, Standard Schema, config, security features, Terminus, CLI.
- Official docs: https://docs.nestjs.com/ , https://docs.nestjs.com/faq/request-lifecycle , https://docs.nestjs.com/migration-guide , https://github.com/nestjs/docs.nestjs.com
