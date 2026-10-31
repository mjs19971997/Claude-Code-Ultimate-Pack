---
name: angular-expert
description: >-
  Builds, reviews and upgrades Angular 22 applications: standalone components, signals (signal, computed, linkedSignal, resource, httpResource), signal inputs and model, zoneless change detection, built-in control flow and @defer, inject() DI, the router, HttpClient interceptors, signal forms and reactive forms, SSR with hydration, the CLI and Vitest tests. Use when editing Angular components, templates, app.config.ts, angular.json or *.spec.ts, or running ng new, ng generate, ng update, ng build, ng test. Not for React (use senior-react-19-engineer), Vue (use vue-expert), Svelte (use svelte-expert), type-level TypeScript (use typescript-master) or browser e2e design (use playwright-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Angular Expert

This skill covers application development on the current Angular line (22.x): standalone components, the signals-based reactivity model, zoneless change detection, template control flow, dependency injection, routing, HTTP, forms, server rendering, the Angular CLI and unit testing with Vitest. It favours the APIs that the official documentation presents as the default today and flags where older code (NgModules, Zone.js, `*ngIf`, Karma) still appears in existing projects.

> Verified against Angular 22.2.4 (`@angular/core`, npm latest), Angular CLI 22.2.5, Angular Material 22.2.5, `@ngrx/signals` 22.0.1, the angular/angular and angular/angular-cli CHANGELOGs, the public API reports in the angular/angular repository and the adev guides (2026-10).

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

- Covered: Angular 22 components and templates, signals and the resource APIs, signal-based component APIs, zoneless change detection, control flow and deferrable views, DI with `inject()`, `@Service` and `@Injectable`, `provideRouter`, `provideHttpClient`, signal forms and typed reactive forms, RxJS interop, SSR, prerendering and hydration, the CLI (application builder), Vitest-based unit tests, NgOptimizedImage, security features and a short orientation on Angular Material, the CDK and NgRx Signal Store.
- Upgrade work from older majors (NgModules, `*ngIf`, constructor injection, Zone.js, Karma) is covered through the CLI migrations in [references/ssr-testing-tooling.md](references/ssr-testing-tooling.md).
- Not covered: React (senior-react-19-engineer), Vue (vue-expert), Svelte (svelte-expert), TypeScript type-level design (typescript-master), browser end-to-end test design (playwright-expert), Tailwind design systems (tailwindcss-master), generic accessibility audits (accessibility-expert), Core Web Vitals diagnosis (core-web-vitals-expert), REST API design (rest-api-expert), container images (docker-expert) and CI pipeline structure (cicd-expert).

## 2. Core Expertise

| Area | Key facts (Angular 22) |
|---|---|
| Components | Standalone is the default; NgModules are legacy. Components without an explicit `changeDetection` are `OnPush` since v22; `ChangeDetectionStrategy.Eager` keeps the old behaviour (the `Default` name is deprecated). |
| Signals | `signal`, `computed`, `effect`, `linkedSignal`, `resource`, `httpResource`, `rxResource`, `debounced` are all in the public (stable) API reports. `resourceFromSnapshots` is documented as experimental. |
| Component API | `input()`, `input.required()`, `output()`, `model()`, `viewChild()`, `viewChildren()`, `contentChild()`; decorators `@Input`, `@Output`, `@ViewChild` still work but are legacy style. |
| Change detection | Zoneless is the default for new applications since v21. `provideZonelessChangeDetection()` is the v20 opt-in name; `provideZoneChangeDetection()` opts back into Zone.js. |
| Templates | `@if`, `@else`, `@for (x of xs; track x.id)`, `@empty`, `@switch`, `@defer` with `on` and `prefetch on` triggers, `@let`. `*ngIf`, `*ngFor`, `*ngSwitch` are legacy. |
| DI | `inject()` in a field initialiser or factory. `@Service()` (v22) is shorthand for a root-provided singleton; `@Injectable({providedIn: 'root'})` remains for constructor DI, `useClass` style providers and non-root scopes. |
| Router | `provideRouter(routes, ...features)`, `loadComponent`, `loadChildren`, functional guards and resolvers, `withComponentInputBinding()`. v22 defaults `paramsInheritanceStrategy` to `'always'`. |
| HTTP | `provideHttpClient(withInterceptors([...]))`. Since v22 the fetch backend is the default; `withFetch()` is deprecated and `withXhr()` restores XHR (needed for upload progress events). |
| Forms | Signal forms (`@angular/forms/signals`: `form`, `FormField`, `FormRoot`, `submit`, validators) graduated to the public API in v22. Typed reactive forms remain fully supported and are the safer choice for existing apps. |
| SSR | `@angular/ssr` with `provideServerRendering(withRoutes(serverRoutes))`, `RenderMode.Prerender`, `Server`, `Client`. `provideClientHydration()` enables incremental hydration by default in v22. |
| CLI and builder | `@angular/build` (esbuild and Vite) is the builder; webpack builders are deprecated. Node 22.22.3+, 24.15+ or 26+ is required by CLI 22.2.5. TypeScript must be 6.0.x for compiler-cli 22.2.4. |
| Testing | New projects use Vitest with jsdom through `ng test`. Karma is still supported; `ng update` ships a Karma-to-Vitest migration. |

## 3. Workflow

1. Read `package.json`, `angular.json`, `tsconfig.json` and `src/main.ts` to learn the Angular major, the builder, the test runner, and whether the app is zoneless, SSR-enabled and standalone.
2. Run `npx ng version` (or `npm ls @angular/core @angular/cli typescript`) and compare with `npm view @angular/core version`. Do not assume the project is on the latest major.
3. Pick the idioms for the project's major. Code for v22 can use `@Service`, signal forms and default `OnPush`; for v20 or v21 use `@Injectable({providedIn: 'root'})` and explicit `changeDetection: ChangeDetectionStrategy.OnPush`.
4. Generate with the CLI (`npx ng generate component|service|guard|pipe|directive`) so files, selectors and spec files follow workspace conventions; then edit.
5. Model state with signals first: writable `signal` for local state, `computed` for derivation, `resource` or `httpResource` for async reads, `linkedSignal` for state that resets from another signal. Reach for RxJS where streams, cancellation operators or the HTTP interceptor chain require it.
6. Run `npx ng build` (type-checks templates) and `npx ng test --no-watch` after each change set; use `npx ng lint` if the workspace has a linter configured.
7. For upgrades, step one major at a time: `npx ng update @angular/core@<n> @angular/cli@<n>`, review the migrations it applied, then fix remaining compile errors. Read the `update.angular.dev` guide for the exact steps (check the current docs).
8. Before finishing, run the Review Checklist (section 12).

## 4. Decision Rules

| Situation | Choose | Why |
|---|---|---|
| Component-local mutable state | `signal()` | Synchronous, read in templates, triggers zoneless change detection. |
| Value derived from other signals | `computed()` | Lazy, memoised, no manual updates. |
| State that must reset when a source signal changes but is also user-editable | `linkedSignal()` | Writable derived state. |
| Read data by URL, reactive to signals | `httpResource()` | Cancels stale requests, exposes `value`, `isLoading`, `error`. |
| Async read with custom loader (not HTTP, or needs transformation) | `resource()` | `params` plus `loader`, `abortSignal`. |
| Observable-based API already in place | `rxResource()` or `toSignal()` | Keeps RxJS sources, exposes signals. |
| Mutation (POST, PUT, DELETE) | `HttpClient` method, subscribe or `firstValueFrom` | `httpResource` is for reads; the docs advise against it for mutations. |
| Side effect that must follow a signal (logging, localStorage, DOM API) | `effect()` | Never use it to derive state; use `computed` or `linkedSignal`. |
| Parent-to-child value | `input()` / `input.required()` | Signal-based, type safe. |
| Two-way binding | `model()` and `[(value)]="sig"` | Replaces `@Input` plus `@Output` pairs. |
| New form in a new app on v22 | Signal forms | Model is a signal; schema-based validation. |
| Existing large form, `FormArray`-heavy, Material form-field integration you cannot test | Typed reactive forms | Mature, widely supported by libraries. |
| Shared app-wide service | `@Service()` (v22) or `@Injectable({providedIn: 'root'})` | Tree-shakable singleton. |
| Feature-scoped service | `providers: [...]` on the route or component | Own instance per route or component. |
| Route-level data needed before render | Resolver (`ResolveFn`) or load inside the component with a resource | Resolvers block navigation; a resource shows a loading state. |
| Heavy below-the-fold component | `@defer (on viewport)` | Separate chunk, loaded on demand. |
| Global client state with many consumers | NgRx Signal Store, or a plain service with signals | A signal-based service is enough for most apps. |
| Unit tests | Vitest via `ng test` | Default runner; Karma only for projects not migrated. |

## 5. Coding Standards

- Use standalone components with an explicit `imports` array; do not add NgModules to new code.
- Keep one component, directive, pipe or service per file. Recent CLI versions generate files without `.component` or `.service` suffixes by default (for example `app.ts`); follow the existing workspace convention (`--file-name-style-guide` on `ng new` selects it, check the current docs).
- Use `inject()` for dependencies and declare them as `private readonly` fields. Constructor parameters are accepted but `inject()` composes better with functional guards, base classes and `@Service`.
- Inputs, outputs and queries use the signal functions. Name outputs without an `on` prefix (`saved`, not `onSaved`). Never mutate an input value.
- Prefer `class` and `style` bindings (`[class.active]="isActive()"`) over `ngClass` and `ngStyle`. Use `host: {...}` metadata instead of `@HostBinding` and `@HostListener`.
- Always give `@for` a `track` expression (a stable id, not `$index`, when items have ids). `@empty` handles the zero-item case.
- Call signals in templates (`user()`), never store the signal function value in a template variable by mistake.
- Keep templates declarative: no function calls that do work, no mutation. Move logic into `computed()`.
- Use `ChangeDetectionStrategy.OnPush` explicitly on v20 and v21 projects; on v22 it is the default.
- Prefer `readonly` and `protected` for members used only by the template; `private` for everything else.
- Enable `strict`, `strictTemplates` and `noImplicitOverride`; v22 generated workspaces rely on strict templates by default.
- Use typed reactive forms (`FormBuilder` via `inject(NonNullableFormBuilder)`) when not using signal forms; avoid `any` form values.
- Type route data, query params and HTTP responses with interfaces; validate untrusted payloads at the boundary.

## 6. Project Structure

```text
my-app/
|-- angular.json                  # workspace and builder config
|-- package.json
|-- tsconfig.json
|-- public/                       # static assets copied as-is
|-- src/
|   |-- index.html
|   |-- main.ts                   # bootstrapApplication(App, appConfig)
|   |-- main.server.ts            # only with SSR
|   |-- server.ts                 # only with SSR (Express or other server)
|   |-- styles.css
|   `-- app/
|       |-- app.ts                # root component (name depends on style guide)
|       |-- app.config.ts         # providers: router, http, hydration
|       |-- app.config.server.ts  # only with SSR
|       |-- app.routes.ts
|       |-- app.routes.server.ts  # only with SSR: RenderMode per route
|       |-- core/                 # singletons: interceptors, guards, auth
|       |-- shared/               # dumb components, pipes, directives
|       `-- features/
|           `-- orders/
|               |-- orders.routes.ts
|               |-- order-list.ts
|               |-- order-detail.ts
|               `-- orders-api.ts
```

- Organise by feature, not by file type. Each feature exposes a routes file loaded lazily with `loadChildren`.
- `app.config.ts` holds environment-wide providers; feature providers live on the route (`providers: [...]`).
- Libraries and large monorepos: use `ng generate library` and path mapping in `tsconfig.json`; consider an Nx workspace only when you need its caching and boundaries (check the current docs).

## 7. Design Patterns

- **Smart and presentational split**: a routed container component injects services and holds signals; child components take `input()` values and emit `output()` events. Cost: more files, but children are trivial to test.
- **Signal-based service store**: a root service owns `private readonly _items = signal<Item[]>([])`, exposes `asReadonly()` and `computed` selectors, and exposes methods for updates. This replaces most hand-written NgRx usage.
- **Resource per read**: a component declares `order = httpResource<Order>(() => this.id() ? ...: undefined)`; returning `undefined` from the request function keeps the resource idle.
- **Functional interceptors**: auth header, error mapping, retry and logging as plain functions in `withInterceptors([...])`; order in the array is the order of execution.
- **Functional guards**: `canActivate: [() => inject(AuthService).isLoggedIn() || inject(Router).parseUrl('/login')]`; returning a `UrlTree` redirects.
- **Injection tokens for configuration**: `new InjectionToken<Config>('CONFIG', {factory: () => ...})` rather than importing `environment` files in services.
- **Directive composition**: `hostDirectives` reuses behaviour (focus, tooltip) without inheritance.
- **Container with `ng-content` and `ng-template`**: content projection for layout components; `NgTemplateOutlet` for caller-provided row templates.
- **NgRx Signal Store** (`signalStore`, `withState`, `withComputed`, `withMethods`, `patchState` from `@ngrx/signals`) when a feature needs structured state with plugins and DevTools; otherwise use a service.

## 8. Best Practices

- Treat `effect()` as an escape hatch. If an effect only sets another signal, replace it with `computed` or `linkedSignal`.
- Use `afterNextRender` and `afterEveryRender` for DOM measurements and third-party widget setup; they do not run on the server.
- Convert at the edges: `toSignal(obs$, {initialValue})` for template consumption, `toObservable(sig)` when an RxJS pipeline needs a signal; `takeUntilDestroyed()` for manual subscriptions in an injection context.
- Keep subscriptions out of components when possible. When you must subscribe, pass `inject(DestroyRef)` to `takeUntilDestroyed` outside the constructor.
- Use `async` pipe or `toSignal` instead of manual `subscribe` for view data.
- Make inputs `required` when the component cannot work without them.
- Use `provideBrowserGlobalErrorListeners()` in `app.config.ts` and a custom `ErrorHandler` to report errors to your monitoring service.
- Use `@let` for template-local aliases of computed expressions you read several times.
- Lazy-load routes and heavy components; keep the initial bundle small and enforce it with budgets in `angular.json`.
- Use `ng generate` schematics and `ng update` migrations rather than hand-porting syntax (`ng generate @angular/core:control-flow`, `:inject`, `:signal-input-migration` and similar exist; run `npx ng generate @angular/core:` to list the current set, check the current docs).
- Prefer `DatePipe`, `CurrencyPipe`, `AsyncPipe` and pure custom pipes over methods in templates.
- Use `NgOptimizedImage` for every above-the-fold and static image.

## 9. Performance

- Measure first: Angular DevTools profiler, Chrome Performance panel, `npx ng build --stats-json` plus a bundle analyser, Lighthouse.
- Zoneless plus signals plus OnPush gives targeted updates; do not reintroduce `ChangeDetectorRef.detectChanges()` calls except for known gaps.
- Split by route (`loadComponent`, `loadChildren`) and by view (`@defer`). `@defer (on viewport; prefetch on idle)` is a common pair. Defer blocks only split components, directives and pipes that are standalone and not referenced eagerly elsewhere in the same file.
- Always provide `track` in `@for`; with ids, DOM nodes are reused when the list changes. Virtual scrolling (`@angular/cdk/scrolling`) for lists in the thousands.
- Use `NgOptimizedImage` (`ngSrc`, explicit `width` and `height` or `fill`, `priority` on the LCP image) to avoid layout shifts and lazy-load the rest.
- Prerender static routes and use SSR with hydration for content pages; incremental hydration (`@defer` with `hydrate on ...`) postpones JavaScript for below-the-fold regions.
- Set bundle budgets (`budgets` in the production configuration of `angular.json`) so growth fails the build.
- Avoid heavy computations in `computed` that run on every dependency change; split signals so unrelated changes do not invalidate them.
- Import only the Material components you use; do not import whole libraries (lodash, moment) into the initial chunk.
- Debounce expensive reactive inputs: `debounced()` (public API in `@angular/core`) or an RxJS `debounceTime`.
- Details for builds, SSR and budgets: [references/ssr-testing-tooling.md](references/ssr-testing-tooling.md).

## 10. Security

- Angular treats template values as untrusted and sanitises HTML, style, URL and resource URL contexts. Interpolation and property bindings are escaped; do not defeat this.
- Avoid `DomSanitizer.bypassSecurityTrust*`. If unavoidable, call it only on content you control or have sanitised with a vetted library, in one small function that is easy to audit.
- Never build templates or HTML strings from user input; never use `innerHTML` through `ElementRef.nativeElement`. Use `[innerHTML]` (sanitised) if rendering HTML is required.
- Do not use `Renderer2.setProperty` or `document.write` to bypass sanitisation. Validate URLs (scheme allow-list) before binding to `href`, `src` or `[routerLink]` when they originate from users.
- Use a Content Security Policy. With SSR, provide a per-response nonce through the `CSP_NONCE` token or the `ngCspNonce` attribute; for static hosting the CLI `security.autoCsp` option hashes inline scripts (see the security guide for its limitations).
- `HttpClient` includes XSRF protection for cookie-based sessions on mutating requests to the same origin; configure with `withXsrfConfiguration`. Use bearer tokens only in memory or secure cookies set by the server; never store long-lived tokens in `localStorage` if XSS is a concern.
- Do not put secrets in `environment` files or any client code: they ship to every browser. Call a backend that holds secrets.
- Route guards are a UX feature, not authorisation. Enforce access on the server.
- Keep Angular and dependencies current: apply patch releases (the CHANGELOG lists security hardening for `@angular/platform-server` and `@angular/common`), run `npm audit` and review lockfile changes.
- In SSR, v22 returns 400 for requests with unrecognised `Host` headers; configure the allowed hosts for your deployment (check the SSR security docs) and do not forward untrusted `X-Forwarded-*` headers.
- Use `{{ }}` for text; reserve `[attr.href]` bindings for validated URLs; SVG `a` href bindings are sanitised from v22.

## 11. Testing

- `ng test` runs Vitest with jsdom for new projects; run once with `npx ng test --no-watch`. Browser mode needs an extra provider package; follow the current Vitest guide.
- Use `TestBed.configureTestingModule({imports: [MyComponent], providers: [...]})` for standalone components. Create with `TestBed.createComponent`, set inputs with `fixture.componentRef.setInput('name', value)`, then `await fixture.whenStable()`.
- In zoneless apps, drive change detection with `await fixture.whenStable()`, not `fixture.detectChanges()` loops; do not rely on Zone.js `fakeAsync` (the Karma-to-Vitest migration rewrites `fakeAsync` to Vitest fake timers).
- Mock HTTP with `provideHttpClient()` plus `provideHttpClientTesting()` and `HttpTestingController`; call `httpMock.verify()` in `afterEach`.
- Query the DOM with `fixture.nativeElement.querySelector` or Angular's `DebugElement`; prefer role and text assertions over CSS classes. For richer queries, use Testing Library for Angular if the team already uses it.
- Component harnesses (`@angular/cdk/testing`, `MatButtonHarness` etc.) hide DOM structure of Material components.
- Provide fakes via `{provide: Token, useValue: fake}` or `useClass`; use `TestBed.runInInjectionContext` to test functional guards and interceptors.
- Test signals directly: set with `.set()`, read after `TestBed.tick()` or `await fixture.whenStable()` (check the current testing guide for the exact flush API for effects).
- Coverage: add `--coverage`; the Vitest coverage provider needs `@vitest/coverage-v8` or an Istanbul provider (v22 generators add `istanbul-lib-instrument`).
- End-to-end tests belong to playwright-expert; cross-cutting unit-test strategy belongs to unit-testing-expert.

## 12. Review Checklist

- [ ] Angular, CLI and TypeScript versions are consistent (`ng version`), and idioms match the major.
- [ ] No new NgModules, `*ngIf`/`*ngFor`, `@Input`/`@Output` decorators or constructor injection in code that is otherwise modern.
- [ ] Every `@for` has a meaningful `track`; every `input.required` is bound by callers.
- [ ] No `effect()` that only writes signals; no subscriptions without `takeUntilDestroyed`, `async` pipe or `toSignal`.
- [ ] Components are `OnPush` (explicit on v20 and v21) and state changes go through signals, `markForCheck` or events.
- [ ] No `bypassSecurityTrust*`, `innerHTML` via `nativeElement`, secrets or tokens in client code.
- [ ] HTTP errors handled (interceptor or `error()` branch in the template); no unhandled resource errors reading `value()` without `hasValue()`.
- [ ] Routes lazy-loaded; guards return `UrlTree` for redirects; resolvers or resources handle loading and error states.
- [ ] Forms validate on both client and server; submit buttons disabled or guarded while submitting.
- [ ] Accessibility: semantic elements, labels bound to inputs, focus management after navigation, keyboard operation, `alt` text.
- [ ] Tests cover new behaviour, run with `ng test --no-watch`, and clean up `HttpTestingController`.
- [ ] `ng build` passes with production budgets; no new console errors or hydration mismatch warnings with SSR.

## 13. Production Notes

- Build with `npx ng build` (production configuration is the default); the output is under `dist/<project>/` with `browser/` and, for SSR, `server/`.
- SSR apps run the generated Node server (`node dist/<project>/server/server.mjs`); prerender-only apps (`outputMode: "static"`) deploy `dist/<project>/browser` to any static host with an SPA fallback only when routes are client-rendered.
- Cache fingerprinted assets for a long time and `index.html` briefly or not at all.
- Configure the allowed hosts and trusted proxy headers for SSR deployments (v22 migrations add trusted-proxy handling; check the SSR docs).
- Source maps: keep them out of public hosting or upload them to your error tracker.
- Pin the Node version to the supported range of the CLI (`npm view @angular/cli engines`). Odd-numbered Node releases trigger CLI warnings.
- Use `npx ng update` regularly; Angular ships a major roughly every six months with LTS windows listed on the releases page (check the current docs for support dates).
- Monitor Core Web Vitals in production; compare lab and field data before and after a release.
- Service worker and PWA: `ng add @angular/pwa`; version updates need a user-visible refresh prompt (`SwUpdate`).
- Internationalisation: use `@angular/localize` and `i18n` attributes with the build-time translation workflow, or a runtime library such as Transloco when runtime switching is needed.

## 14. Examples

A standalone, zoneless-ready component with signal inputs, `httpResource` and control flow:

```ts
import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';
import {httpResource} from '@angular/common/http';

interface Order {
  id: string;
  status: 'open' | 'shipped';
  lines: { sku: string; qty: number; unitCents: number }[];
}

@Component({
  selector: 'app-order-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (order.hasValue()) {
      <h2>Order {{ order.value().id }} ({{ order.value().status }})</h2>
      <ul>
        @for (line of order.value().lines; track line.sku) {
          <li>{{ line.sku }} x {{ line.qty }}</li>
        } @empty {
          <li>No lines</li>
        }
      </ul>
      <p>Total: {{ totalCents() / 100 | currency }}</p>
    } @else if (order.error()) {
      <p role="alert">Could not load the order.</p>
    } @else if (order.isLoading()) {
      <p>Loading...</p>
    }
  `,
})
export class OrderDetail {
  readonly orderId = input.required<string>();

  protected readonly order = httpResource<Order>(() => `/api/orders/${encodeURIComponent(this.orderId())}`);

  protected readonly totalCents = computed(() =>
    (this.order.value()?.lines ?? []).reduce((sum, l) => sum + l.qty * l.unitCents, 0),
  );
}
```

Application config with router, HTTP interceptor and hydration (no Zone.js provider needed on v21 and later):

```ts
import {ApplicationConfig, provideBrowserGlobalErrorListeners} from '@angular/core';
import {provideRouter, withComponentInputBinding} from '@angular/router';
import {provideHttpClient, withInterceptors, HttpInterceptorFn} from '@angular/common/http';
import {provideClientHydration} from '@angular/platform-browser';
import {routes} from './app.routes';

const apiBase: HttpInterceptorFn = (req, next) =>
  req.url.startsWith('/api/') ? next(req.clone({ withCredentials: true })) : next(req);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([apiBase])),
    provideClientHydration(), // only for SSR projects
  ],
};
```

Lazy routes with a functional guard:

```ts
import {inject} from '@angular/core';
import {CanActivateFn, Router, Routes} from '@angular/router';
import {AuthService} from './core/auth-service';

const requireLogin: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isLoggedIn() ? true : inject(Router).parseUrl('/login');
};

export const routes: Routes = [
  { path: 'orders/:orderId', loadComponent: () => import('./features/orders/order-detail').then(m => m.OrderDetail), canActivate: [requireLogin] },
  { path: 'admin', loadChildren: () => import('./features/admin/admin.routes').then(m => m.adminRoutes), canMatch: [requireLogin] },
  { path: '**', redirectTo: '' },
];
```

With `withComponentInputBinding()`, the `:orderId` route parameter binds to the component's `orderId` input. More examples (signal forms, models, interop, SSR, testing) are in the reference files.

## 15. Common Mistakes

- **Using `effect()` to copy one signal into another**: causes extra renders and ordering bugs. Use `computed` or `linkedSignal`.
- **Reading `resource.value()` while in the error state**: it throws. Guard with `hasValue()` or check `error()` first.
- **Missing `track` or tracking by `$index` on mutable lists**: loses DOM state on reorder. Track by a stable id.
- **Mutating an array or object inside a signal** (`items().push(x)`): the signal does not notify. Use `items.update(list => [...list, x])`.
- **Forgetting to call signals in templates** (`{{ count }}` instead of `{{ count() }}`): renders the function.
- **Leaving Zone.js assumptions in a zoneless app**: `setTimeout` or third-party callbacks that mutate plain fields do not refresh the view. Move state to signals or call `markForCheck`.
- **Importing `HttpClientModule`** or other modules in new code: use `provideHttpClient()`.
- **Subscribing in the constructor without teardown**: leaks. Use `takeUntilDestroyed()`.
- **Calling `inject()` outside an injection context** (inside a callback or async function): capture the dependency in a field first or use `runInInjectionContext`.
- **Using `*ngIf` and `@if` for the same case in one template, or forgetting to import `NgIf` after migrating**: pick control flow only.
- **Putting authorisation only in route guards**: the API must enforce it.
- **Using `bypassSecurityTrustHtml` to "fix" stripped content**: addresses a symptom and opens XSS. Sanitise at source or render with safe bindings.
- **Treating `Default` change detection assumptions as safe on v22**: components are `OnPush` unless they declare `Eager`; mutating objects in place may stop updating the view.
- **Running `ng update` across several majors at once**: update one major at a time and commit between steps.
- **Binding a route param without `withComponentInputBinding()`**: the input stays unset. Add the feature or read `ActivatedRoute`.
- **Relying on `provideZoneChangeDetection` and removing Zone.js polyfills**: inconsistent; choose either zoneless (default) or Zone.js with polyfills.

## 16. References

- [references/signals-and-components.md](references/signals-and-components.md): signal, computed, effect, linkedSignal, resource and httpResource, input/output/model/queries, control flow, @defer, host bindings, zoneless rules, RxJS interop.
- [references/routing-and-di.md](references/routing-and-di.md): provideRouter and features, lazy routes, guards, resolvers, input binding, inject(), @Service versus @Injectable, tokens, provider scopes, environment injectors.
- [references/forms-and-http.md](references/forms-and-http.md): signal forms (form, FormField, validators, submit), typed reactive forms, HttpClient setup, interceptors, errors, XSRF, httpResource, testing HTTP.
- [references/ssr-testing-tooling.md](references/ssr-testing-tooling.md): CLI commands and builder, ng new options, SSR render modes and hydration, Vitest testing, ng update and migrations, budgets, Material, CDK and NgRx Signal Store orientation.
- Angular documentation: https://angular.dev/ (guides, API reference) and the release notes at https://github.com/angular/angular/blob/main/CHANGELOG.md
- Angular CLI changelog: https://github.com/angular/angular-cli/blob/main/CHANGELOG.md ; update guide: https://angular.dev/update-guide
- Angular Material and CDK: https://material.angular.dev/ ; NgRx Signals: https://ngrx.io/guide/signals
- Vitest: https://vitest.dev/ ; RxJS: https://rxjs.dev/
