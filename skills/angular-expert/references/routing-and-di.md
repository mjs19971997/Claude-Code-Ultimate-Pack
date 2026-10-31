# Routing and Dependency Injection

Router configuration, lazy loading, functional guards and resolvers, route input binding, `inject()`, `@Service` versus `@Injectable`, tokens, provider scopes and environment injectors for Angular 22. Function names were checked against the public API reports of `@angular/core` and `@angular/router` (2026-10).

## Contents

1. [Router setup](#1-router-setup)
2. [Route configuration and lazy loading](#2-route-configuration-and-lazy-loading)
3. [Functional guards](#3-functional-guards)
4. [Resolvers and route data](#4-resolvers-and-route-data)
5. [Component input binding](#5-component-input-binding)
6. [Navigation and links](#6-navigation-and-links)
7. [inject and injection contexts](#7-inject-and-injection-contexts)
8. [Service decorators and scopes](#8-service-decorators-and-scopes)
9. [Tokens and providers](#9-tokens-and-providers)
10. [Environment injectors and initialisers](#10-environment-injectors-and-initialisers)

## 1. Router setup

```ts
// app.config.ts
import {ApplicationConfig} from '@angular/core';
import {
  provideRouter, withComponentInputBinding, withInMemoryScrolling,
  withPreloading, withViewTransitions, PreloadAllModules,
} from '@angular/router';
import {routes} from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(
      routes,
      withComponentInputBinding(),
      withViewTransitions(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled', anchorScrolling: 'enabled' }),
      withPreloading(PreloadAllModules),
    ),
  ],
};
```

- Other features available in the API report: `withRouterConfig`, `withNavigationErrorHandler`, `withDebugTracing`, `withDisabledInitialNavigation`, `withEnabledBlockingInitialNavigation`.
- `provideRoutes()` was removed in v22; use `provideRouter()` (or the `ROUTES` multi token in libraries).

## 2. Route configuration and lazy loading

```ts
import {Routes} from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'home' },
  { path: 'home', title: 'Home', loadComponent: () => import('./home/home').then(m => m.Home) },
  {
    path: 'orders',
    loadChildren: () => import('./features/orders/orders.routes').then(m => m.ordersRoutes),
  },
  { path: 'legacy/:id', redirectTo: ({ params }) => `/orders/${params['id']}` },
  { path: '**', loadComponent: () => import('./not-found/not-found').then(m => m.NotFound) },
];
```

```ts
// features/orders/orders.routes.ts
import {Routes} from '@angular/router';
import {OrdersApi} from './orders-api';

export const ordersRoutes: Routes = [
  {
    path: '',
    providers: [OrdersApi],               // instance scoped to this route subtree
    children: [
      { path: '', loadComponent: () => import('./order-list').then(m => m.OrderList) },
      { path: ':orderId', loadComponent: () => import('./order-detail').then(m => m.OrderDetail) },
    ],
  },
];
```

- Use `loadComponent` for a single standalone component and `loadChildren` for a routes file. Both create separate chunks.
- `redirectTo` accepts a function receiving the matched snapshot data (typed as `RedirectFunction`); it may return a string or a `UrlTree`.
- `providers` on a route create a route-level environment injector; services there are destroyed with the route subtree.

## 3. Functional guards

```ts
import {inject} from '@angular/core';
import {CanActivateFn, CanDeactivateFn, CanMatchFn, Router} from '@angular/router';
import {AuthService} from './core/auth-service';

export const requireRole = (role: string): CanActivateFn => () => {
  const auth = inject(AuthService);
  return auth.hasRole(role) ? true : inject(Router).createUrlTree(['/forbidden']);
};

export const featureEnabled: CanMatchFn = (route, segments, currentSnapshot) =>
  inject(FeatureFlags).isOn('beta');

export const confirmLeave: CanDeactivateFn<{ dirty(): boolean }> = (component) =>
  !component.dirty() || confirm('Discard changes?');
```

```ts
{ path: 'admin', canActivate: [requireRole('admin')], canMatch: [featureEnabled], loadChildren: () => import('./admin/admin.routes').then(m => m.adminRoutes) }
```

- Guards run in an injection context, so `inject()` works directly. Class-based guards are legacy.
- Return `true`, `false`, a `UrlTree` (redirect) or a `RedirectCommand`, synchronously or as a Promise or Observable.
- `canMatch` decides whether a route is considered at all and prevents the chunk from loading; `canActivate` runs after matching. From v22 the third parameter `currentSnapshot` of `CanMatchFn` is required; an `ng update` migration adds it to class implementations.

## 4. Resolvers and route data

```ts
import {ResolveFn} from '@angular/router';

export const orderResolver: ResolveFn<Order> = (route) =>
  inject(OrdersApi).get(route.paramMap.get('orderId')!);

// route
{ path: ':orderId', component: OrderDetail, resolve: { order: orderResolver }, data: { section: 'orders' } }
```

- A resolver blocks navigation until it completes. For a snappier UI, load in the component with `httpResource` and show a loading state instead.
- Resolved values arrive through `ActivatedRoute.data`, or through inputs with `withComponentInputBinding()` (the `order` and `section` keys become inputs).
- A resolver may return a `RedirectCommand` to redirect on failure instead of throwing.

## 5. Component input binding

```ts
@Component({ selector: 'app-order-detail', template: `...` })
export class OrderDetail {
  readonly orderId = input.required<string>();      // path param :orderId
  readonly tab = input<string>('summary');           // query param ?tab=
  readonly order = input<Order>();                   // resolve key 'order'
}
```

- With `withComponentInputBinding()`, route params, query params, `data` and resolved values bind to inputs of the routed component by name.
- v22 adds `withComponentInputBinding({ queryParams: ..., unmatchedInputBehavior: 'alwaysUndefined' | 'undefinedIfStale' })` to control query param binding and what unmatched inputs do on navigation (check the current docs for exact semantics).
- Combine with `paramsInheritanceStrategy`: the v22 default is `'always'`, so child routes see parent params. Set `withRouterConfig({paramsInheritanceStrategy: 'emptyOnly'})` to restore the old default.
- Inputs bound by the router are strings; use a `transform` (`numberAttribute`, `booleanAttribute`) for other types.

## 6. Navigation and links

```html
<a routerLink="/orders" routerLinkActive="active" ariaCurrentWhenActive="page">Orders</a>
<a [routerLink]="['/orders', order.id]" [queryParams]="{ tab: 'items' }">Open</a>
```

```ts
private readonly router = inject(Router);

openOrder(id: string) {
  return this.router.navigate(['/orders', id], { queryParams: { tab: 'items' } });
}
```

- Prefer `routerLink` on `<a>` elements over click handlers so links are keyboard and crawler friendly.
- v22 router changes: `TitleStrategy.getResolvedTitleForRoute` returns `string | undefined`, `provideRoutes()` is removed, and `lastSuccessfulNavigation` is a signal (since v21).
- Use `Router.parseUrl` or `createUrlTree` to build a `UrlTree`; never concatenate user input into a URL string.
- Validate redirect targets (for example a `returnUrl` query param) against an allow-list or require them to be same-origin paths before navigating.

## 7. inject and injection contexts

```ts
import {DestroyRef, Injectable, inject} from '@angular/core';
import {HttpClient} from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class OrdersApi {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  list() {
    return this.http.get<Order[]>('/api/orders');
  }
}
```

- `inject()` works in field initialisers, constructors, factory functions, `provide*Initializer` callbacks, functional guards, resolvers and interceptors, and inside `runInInjectionContext(injector, fn)`.
- It throws outside such a context (inside `setTimeout`, an RxJS callback or an async function after an `await`). Capture dependencies at construction time.
- Options: `inject(Token, {optional: true})`, `{self: true}`, `{skipSelf: true}`, `{host: true}`.
- `inject(DestroyRef).onDestroy(() => ...)` registers cleanup; `inject(ElementRef)`, `inject(ChangeDetectorRef)` and `inject(Injector)` work the same way.

## 8. Service decorators and scopes

```ts
import {Service, signal} from '@angular/core';

@Service()
export class CartStore {
  private readonly _lines = signal<CartLine[]>([]);
  readonly lines = this._lines.asReadonly();

  add(line: CartLine) { this._lines.update(l => [...l, line]); }
}
```

| Need | Use |
|---|---|
| Root singleton, field-based `inject()` | `@Service()` (v22+) |
| Root singleton on v20 or v21 | `@Injectable({providedIn: 'root'})` |
| Factory for the singleton | `@Service({factory: () => ...})` |
| Provide only where listed (route, component) | `@Service({autoProvided: false})` or `@Injectable()` plus `providers` |
| Constructor parameter injection, `useClass`, `useExisting`, `platform` scope | `@Injectable` |

- `@Service` does not support constructor-based DI; use `inject()` fields. `ng generate service` emits `@Service` in v22 workspaces, and `ng update` offers a migration from `@Injectable` (v22.1).
- Component `providers: [Service]` creates one instance per component instance; `viewProviders` limits visibility to the component's own view.
- Hierarchy: element injector tree (components and directives) first, then route environment injectors, then the root environment injector, then the platform injector. Resolution walks up and throws `NullInjectorError` when nothing provides the token.

## 9. Tokens and providers

```ts
import {InjectionToken, inject} from '@angular/core';

export interface ApiConfig { baseUrl: string; timeoutMs: number }

export const API_CONFIG = new InjectionToken<ApiConfig>('API_CONFIG', {
  providedIn: 'root',
  factory: () => ({ baseUrl: '/api', timeoutMs: 10_000 }),
});

// Override per environment or test
{ provide: API_CONFIG, useValue: { baseUrl: 'https://staging.example.test/api', timeoutMs: 5_000 } }
```

- Provider shapes: `useClass`, `useValue`, `useFactory` (with `inject()` inside), `useExisting` (alias), `multi: true` for collecting values under one token.
- Use `makeEnvironmentProviders([...])` to bundle providers behind a `provideFoo()` function so consumers need not know the internals.
- Root-provided services are tree-shakable: a service nothing injects is dropped from the bundle.

## 10. Environment injectors and initialisers

```ts
import {provideAppInitializer, inject} from '@angular/core';

export const appConfig = {
  providers: [
    provideAppInitializer(async () => {
      await inject(ConfigService).load();   // blocks bootstrap until resolved
    }),
  ],
};
```

- `provideAppInitializer` replaces `APP_INITIALIZER`; `provideEnvironmentInitializer` runs sync setup when an environment injector is created.
- `createEnvironmentInjector(providers, parent)` builds a child injector for dynamically created components; `createComponent(Cmp, {environmentInjector})` creates a component outside a template. `ComponentFactoryResolver` and `ComponentFactory` were removed in v22; pass the component class directly to `ViewContainerRef.createComponent`.
- For SSR, `main.server.ts` passes the `BootstrapContext` it receives to `bootstrapApplication(App, config, context)` (the v21 migration adds it).
