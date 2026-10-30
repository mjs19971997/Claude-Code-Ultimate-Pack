# Request Lifecycle

Reference for the order in which NestJS runs middleware, guards, interceptors, pipes, handlers and exception filters, plus provider scopes and application lifecycle hooks. Verified against the "Request lifecycle" chapter of the NestJS documentation source (`content/faq/request-lifecycle.md`) and by running the proof in section 3 on NestJS 12.3.2 with Vitest 5 (2026-10).

## 1. The order

1. Incoming request
2. Middleware
   - 2.1 Globally bound middleware (`app.use()`)
   - 2.2 Module-bound middleware (`configure(consumer)` with `apply().forRoutes()`)
3. Guards
   - 3.1 Global guards
   - 3.2 Controller guards
   - 3.3 Route guards
4. Interceptors, before the handler
   - 4.1 Global, 4.2 controller, 4.3 route
5. Pipes
   - 5.1 Global, 5.2 controller, 5.3 route, 5.4 route parameter pipes
6. Controller (method handler)
7. Service (if the handler calls one)
8. Interceptors, after the handler, in reverse order
   - 8.1 Route, 8.2 controller, 8.3 global
9. Exception filters (only when an exception was thrown and not caught)
   - 9.1 Route, 9.2 controller, 9.3 global
10. Server response

A shorthand that holds: middleware, then guards, then interceptors, then pipes, then the handler, then interceptors again on the way out. Filters are outside this flow and take over when something throws.

## 2. Rules per component

### Middleware

- Global middleware (for example `app.use(...)`) runs first, then module-bound middleware that matches the path. Middleware runs in the order it is bound.
- For module-bound middleware across modules: middleware from `@Global()` modules first, then the root module, then other modules ordered by their distance from the root module in the import graph.
- Middleware runs before a route handler is selected, so it has no `ExecutionContext`, cannot read handler metadata, and cannot be a guard replacement.
- With `app.useSecurityHeaders()` and `app.enableCsrfProtection()` (12.1+) the checks are registered as framework-level middleware or hooks at the call site, so calling them right after `NestFactory.create()` makes them run before middleware added later with `app.use()`.

### Guards

- Order is global, then controller, then route, and in binding order within a level: `@UseGuards(Guard1, Guard2)` on a controller and `@UseGuards(Guard3)` on a route run as Guard1, Guard2, Guard3.
- "Global" means registered with `app.useGlobalGuards()` or provided through `APP_GUARD`; the decorator on a class makes it controller level, on a method route level.
- A guard that returns `false` produces 403; throw `UnauthorizedException` for 401.

### Interceptors

- The inbound side follows global, controller, route. Because interceptors wrap an RxJS `Observable`, the outbound side (after the handler returns) is resolved route, then controller, then global: first in, last out.
- Errors thrown by pipes, controllers or services can be observed in an interceptor's `catchError`.
- Interceptors run before pipes, so they see unvalidated arguments through the execution context.

### Pipes

- Order is global, then controller, then route; pipes passed to `@UsePipes()` run first in, first out.
- At the parameter level, when several parameters have pipes, pipes process the last parameter first and the first parameter last. This also applies to the controller-level and route-level pipes: a general pipe sees `query`, then `params`, then `body` for a handler declared as `(body, params, query)`.
- Parameter-specific pipes (`@Param('id', ParseIntPipe)`) run after the controller-level and route-level pipes, again from the last parameter to the first.

### Exception filters

- Filters are the only component that does not resolve global first. Nest checks route-bound filters, then controller-bound filters, then global filters.
- Exceptions are not passed from filter to filter: if a route-level filter catches an exception, a controller-level or global filter does not see it. Use inheritance between filters to compose behavior.
- Filters run only for uncaught exceptions. An exception you catch yourself with `try/catch` never reaches them. After an uncaught exception the rest of the lifecycle is skipped.
- Exceptions thrown from middleware are handled by the exceptions layer, but only global filters apply because no handler has been selected yet.
- Exceptions thrown from guards, interceptors, pipes, handlers and services are all eligible for route, controller and global filters.

## 3. Runnable proof

This Vitest file registers one component at every level and records the order. It was run on NestJS 12.3.2 and produced the output below. Use it when a team disagrees about execution order.

```ts
import {
  ArgumentMetadata, ArgumentsHost, CallHandler, CanActivate, Catch, Controller, ExceptionFilter, ExecutionContext,
  Get, HttpException, Injectable, MiddlewareConsumer, Module, NestInterceptor, NestMiddleware, NestModule,
  PipeTransform, Query, UseFilters, UseGuards, UseInterceptors, UsePipes,
} from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR, APP_PIPE } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { tap } from 'rxjs';
import { describe, it } from 'vitest';

const log: string[] = [];
const mark = (s: string) => log.push(s);

const guard = (name: string) => {
  @Injectable() class G implements CanActivate { canActivate() { mark(name); return true; } }
  return G;
};
const interceptor = (name: string) => {
  @Injectable() class I implements NestInterceptor {
    intercept(_c: ExecutionContext, next: CallHandler) {
      mark(`${name}:before`);
      return next.handle().pipe(tap(() => mark(`${name}:after`)));
    }
  }
  return I;
};
const pipe = (name: string) => {
  @Injectable() class P implements PipeTransform {
    transform(v: unknown, m: ArgumentMetadata) { mark(`${name}:${m.type}`); return v; }
  }
  return P;
};
const filter = (name: string) => {
  @Catch() class F implements ExceptionFilter {
    catch(_e: HttpException, host: ArgumentsHost) { mark(name); host.switchToHttp().getResponse().status(500).json({ filter: name }); }
  }
  return F;
};
class ModuleMiddleware implements NestMiddleware {
  use(_req: unknown, _res: unknown, next: () => void) { mark('middleware:module'); next(); }
}

const [GlobalGuard, ControllerGuard, RouteGuard] = [guard('guard:global'), guard('guard:controller'), guard('guard:route')];
const [GlobalI, ControllerI, RouteI] = [interceptor('interceptor:global'), interceptor('interceptor:controller'), interceptor('interceptor:route')];
const [GlobalP, ControllerP, RouteP, ParamP] = [pipe('pipe:global'), pipe('pipe:controller'), pipe('pipe:route'), pipe('pipe:param')];
const [GlobalF, ControllerF, RouteF] = [filter('filter:global'), filter('filter:controller'), filter('filter:route')];

@Injectable() class Svc { run() { mark('service'); return 'ok'; } }

@Controller('t')
@UseGuards(ControllerGuard) @UseInterceptors(ControllerI) @UsePipes(ControllerP) @UseFilters(ControllerF)
class TController {
  constructor(private svc: Svc) {}

  @Get() @UseGuards(RouteGuard) @UseInterceptors(RouteI) @UsePipes(RouteP) @UseFilters(RouteF)
  get(@Query('q', ParamP) _q: string) { mark('controller'); return this.svc.run(); }

  @Get('boom') @UseFilters(RouteF)
  boom() { mark('controller'); throw new HttpException('x', 400); }
}

@Module({
  controllers: [TController],
  providers: [
    Svc,
    { provide: APP_GUARD, useClass: GlobalGuard },
    { provide: APP_INTERCEPTOR, useClass: GlobalI },
    { provide: APP_PIPE, useClass: GlobalP },
    { provide: APP_FILTER, useClass: GlobalF },
  ],
})
class TModule implements NestModule {
  configure(consumer: MiddlewareConsumer) { consumer.apply(ModuleMiddleware).forRoutes('t'); }
}

describe('request lifecycle', () => {
  it('prints the order', async () => {
    const ref = await Test.createTestingModule({ imports: [TModule] }).compile();
    const app = ref.createNestApplication();
    app.use((_req: unknown, _res: unknown, next: () => void) => { mark('middleware:global'); next(); });
    await app.init();
    await request(app.getHttpServer()).get('/t?q=1').expect(200);
    console.log(log.join('\n'));
    log.length = 0;
    await request(app.getHttpServer()).get('/t/boom').expect(500);
    console.log(log.join('\n'));
    await app.close();
  });
});
```

Observed order for `GET /t?q=1`:

```text
middleware:global
middleware:module
guard:global
guard:controller
guard:route
interceptor:global:before
interceptor:controller:before
interceptor:route:before
pipe:global:query
pipe:controller:query
pipe:route:query
pipe:param:query
controller
service
interceptor:route:after
interceptor:controller:after
interceptor:global:after
```

Observed order for `GET /t/boom` (handler throws): middleware, guards, interceptors (before), the controller, then only `filter:route`. The controller-level and global filters never run because the route-level filter handled the exception.

## 4. Where components can be bound

| Component | Global without DI | Global with DI | Controller | Route | Parameter |
|---|---|---|---|---|---|
| Middleware | `app.use()` | n/a | n/a | `consumer.apply().forRoutes()` | n/a |
| Guard | `app.useGlobalGuards()` | `APP_GUARD` | `@UseGuards()` on class | `@UseGuards()` on method | n/a |
| Interceptor | `app.useGlobalInterceptors()` | `APP_INTERCEPTOR` | `@UseInterceptors()` | `@UseInterceptors()` | n/a |
| Pipe | `app.useGlobalPipes()` | `APP_PIPE` | `@UsePipes()` | `@UsePipes()` | `@Param('id', Pipe)` |
| Filter | `app.useGlobalFilters()` | `APP_FILTER` | `@UseFilters()` | `@UseFilters()` | n/a |

Instances registered through `app.useGlobal*()` are created outside the module context and cannot inject providers. Register through the `APP_*` tokens when the component has dependencies, and to make it overridable in tests (`useExisting` pattern in testing.md).

## 5. Provider scopes and the lifecycle

- `Scope.DEFAULT` (singleton): one instance per application; the default and the fastest.
- `Scope.REQUEST`: a new instance per request, garbage-collected afterwards. The scope bubbles up the injection chain: a controller that depends on a request-scoped provider becomes request-scoped.
- `Scope.TRANSIENT`: a new instance for each consumer that injects it; not shared.
- Durable providers (`@Injectable({ scope: Scope.REQUEST, durable: true })`) with a registered `ContextIdStrategy` share an instance per tenant or other grouping key instead of per request. Durability also bubbles up; read the injection-scopes chapter before relying on it.
- Lifecycle hooks are not called for request-scoped classes.

Application lifecycle hooks:

| Hook | When |
|---|---|
| `onModuleInit()` | After the host module's dependencies are resolved |
| `onApplicationBootstrap()` | After all modules initialized, before listening |
| `onModuleDestroy()` | After a termination signal (needs `enableShutdownHooks()`) or `app.close()` |
| `beforeApplicationShutdown(signal)` | After all `onModuleDestroy()` completed; then connections close |
| `onApplicationShutdown(signal)` | After connections are closed, the last step of `app.close()` |

`onModuleInit` and `onApplicationBootstrap` are called module by module, ordered by each module's distance from the root in the import graph (deepest and global modules first). In v12 hooks are called by component hierarchy level, which can change the order between related providers; do not depend on a particular order across providers unless they import each other. Async hooks defer initialization until their promise settles.

## 6. Other execution contexts

Guards, interceptors, pipes and filters also apply to WebSocket gateways, microservice handlers and GraphQL resolvers. `ExecutionContext.getType()` returns `'http'`, `'rpc'`, `'ws'` (or `'graphql'` with the GraphQL module); use `context.switchToHttp()`, `switchToRpc()` or `switchToWs()` to read arguments. Exception filters for RPC and WebSocket contexts work with `RpcException`/`WsException` and have their own base filters; an HTTP filter does not translate those. Middleware is HTTP-only.
