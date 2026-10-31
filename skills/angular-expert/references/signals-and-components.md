# Signals and Components

Reactive primitives, the signal-based component API, template control flow, deferrable views, zoneless rules and RxJS interop for Angular 22. Public API status was checked in the angular/angular API reports and the adev guides (2026-10).

## Contents

1. [Signal primitives](#1-signal-primitives)
2. [effect and untracked](#2-effect-and-untracked)
3. [resource and httpResource](#3-resource-and-httpresource)
4. [Component inputs, outputs and models](#4-component-inputs-outputs-and-models)
5. [Queries and host bindings](#5-queries-and-host-bindings)
6. [Control flow](#6-control-flow)
7. [Deferrable views](#7-deferrable-views)
8. [Zoneless and change detection](#8-zoneless-and-change-detection)
9. [RxJS interop](#9-rxjs-interop)
10. [Render hooks](#10-render-hooks)

## 1. Signal primitives

```ts
import {computed, linkedSignal, signal} from '@angular/core';

const count = signal(0);                      // WritableSignal<number>
const doubled = computed(() => count() * 2);  // read-only, lazy, memoised

count.set(3);
count.update(n => n + 1);

// Writable state derived from another signal; resets when the source changes.
const options = signal(['a', 'b', 'c']);
const selected = linkedSignal(() => options()[0]);
selected.set('b');            // user choice
options.set(['x', 'y']);      // selected becomes 'x'
```

- `signal`, `computed`, `effect`, `linkedSignal`, `resource`, `httpResource`, `rxResource` and `debounced` appear in the public API reports for v22. `resourceFromSnapshots` is documented as experimental.
- Expose state as read-only from a service: `readonly items = this._items.asReadonly();`.

## 2. effect and untracked

```ts
import {Component, effect, signal, untracked} from '@angular/core';

@Component({ selector: 'app-theme', template: `...` })
export class Theme {
  readonly theme = signal<'light' | 'dark'>('light');

  constructor() {
    effect((onCleanup) => {
      const value = this.theme();                 // tracked
      document.documentElement.dataset['theme'] = value;
      untracked(() => this.logChange(value));     // read without tracking
      onCleanup(() => { /* release resources from the previous run */ });
    });
  }

  private logChange(v: string) { console.debug('theme', v); }
}
```

- Effects run asynchronously during change detection, at least once, and again when a tracked signal changes. They need an injection context (constructor, field initialiser) or an explicit `injector` option.
- Use effects for non-reactive outputs: `localStorage`, analytics, canvas drawing, calling a non-signal library. Do not use them to derive state or to trigger HTTP calls (use `computed`, `linkedSignal`, `resource`).

## 3. resource and httpResource

```ts
import {Component, input, resource} from '@angular/core';
import {httpResource} from '@angular/common/http';

@Component({ selector: 'app-user', template: `...` })
export class User {
  readonly id = input.required<string>();

  // Custom async loader; params returning undefined keeps the resource idle.
  protected readonly profile = resource({
    params: () => ({ id: this.id() }),
    loader: async ({ params, abortSignal }) => {
      const res = await fetch(`/api/users/${encodeURIComponent(params.id)}`, { signal: abortSignal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as { name: string };
    },
  });

  // URL-based read through HttpClient (interceptors apply).
  protected readonly posts = httpResource<{ id: number; title: string }[]>(
    () => `/api/users/${encodeURIComponent(this.id())}/posts`,
    { defaultValue: [] },
  );
}
```

- Resource members: `value()`, `status()`, `error()`, `isLoading()`, `hasValue()`, `reload()`, plus `set()` and `update()` on the writable `ResourceRef`.
- The loader receives `{params, previous, abortSignal}`. Pass `abortSignal` to `fetch` so a stale request is cancelled when `params` changes.
- Reading `value()` in the error state throws. In templates use `@if (r.hasValue()) {...} @else if (r.error()) {...} @else if (r.isLoading()) {...}`.
- `httpResource` accepts a URL string, or a request object (`url`, `method`, `headers`, `params`, `body`, `withCredentials`, `transferCache` and more). It starts eagerly and cancels the pending request when its inputs change.
- `httpResource` is for reads. For writes call `HttpClient` directly and then `resource.reload()` or update the local signal.
- `rxResource` (`@angular/core/rxjs-interop`) builds a resource from an Observable-returning `stream` or `loader`.

## 4. Component inputs, outputs and models

```ts
import {ChangeDetectionStrategy, Component, input, model, numberAttribute, output} from '@angular/core';

@Component({
  selector: 'app-rating',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @for (n of stars; track n) {
      <button type="button" [attr.aria-pressed]="n <= value()" (click)="pick(n)">{{ n }}</button>
    }
  `,
})
export class Rating {
  readonly label = input.required<string>();
  readonly max = input(5, { transform: numberAttribute });
  readonly value = model(0);            // supports [(value)]
  readonly rated = output<number>();    // (rated)="..."

  protected readonly stars = [1, 2, 3, 4, 5];

  protected pick(n: number) {
    this.value.set(n);
    this.rated.emit(n);
  }
}
```

Parent usage: `<app-rating label="Quality" [(value)]="score" (rated)="log($event)" />`.

- `input()` is a read-only signal; `input.required<T>()` fails compilation when a parent omits it; `input(default, {alias, transform})` customises binding.
- `model()` is both an input and an output named `<name>Change`. Use it only for genuine two-way state.
- v22 throws at compile time when inputs, outputs or models bind the same name, and when two selectors match one element.

## 5. Queries and host bindings

```ts
import {Component, ElementRef, afterNextRender, signal, viewChild, viewChildren} from '@angular/core';

@Component({
  selector: 'app-search',
  host: {
    'class': 'search',
    '[class.busy]': 'busy()',
    '(keydown.escape)': 'clear()',
  },
  template: `<input #box /> @for (r of results; track r) { <li #row>{{ r }}</li> }`,
})
export class Search {
  protected readonly box = viewChild.required<ElementRef<HTMLInputElement>>('box');
  protected readonly rows = viewChildren<ElementRef<HTMLLIElement>>('row');
  protected readonly busy = signal(false);
  protected results: string[] = [];

  constructor() {
    afterNextRender(() => this.box().nativeElement.focus());
  }

  protected clear() { this.box().nativeElement.value = ''; }
}
```

## 6. Control flow

```html
@if (user(); as u) {
  <p>{{ u.name }}</p>
} @else {
  <p>Anonymous</p>
}

@for (item of items(); track item.id; let i = $index, last = $last) {
  <li [class.last]="last">{{ i + 1 }}. {{ item.name }}</li>
} @empty {
  <li>Nothing here</li>
}

@switch (status()) {
  @case ('open') { <app-open /> }
  @case ('closed') { <app-closed /> }
  @default { <app-unknown /> }
}

@let total = price() * qty();
<p>{{ total | currency }}</p>
```

- v22 compiler changes: optional chaining in templates returns `undefined`, `nullishCoalescingNotNullable` and `optionalChainNotNullable` diagnostics are active (the update migration may disable them temporarily), `data-` prefixed attributes no longer bind inputs or outputs, and `in` variables in expressions throw.

## 7. Deferrable views

```html
@defer (on viewport; prefetch on idle) {
  <app-comments [postId]="postId()" />
} @placeholder (minimum 300ms) {
  <div class="skeleton" aria-hidden="true"></div>
} @loading (after 150ms; minimum 500ms) {
  <app-spinner />
} @error {
  <p role="alert">Comments failed to load.</p>
}
```

- Triggers: `on idle` (default), `on viewport`, `on interaction`, `on hover`, `on immediate`, `on timer(5s)`, and `when <expression>`. `prefetch on ...` or `prefetch when ...` downloads the chunk earlier.
- `on idle` accepts an optional timeout in v22, for example `on idle(500)`; the idle behaviour can be customised through an `IdleService` provider (check the current docs).
- Incremental hydration (SSR): `@defer (hydrate on interaction) {...}`, plus `hydrate on idle`, `hydrate on viewport`, `hydrate when cond`, `hydrate never`. In v22 `provideClientHydration()` enables it by default and it enables event replay.

## 8. Zoneless and change detection

- New applications from CLI 21 are zoneless. On v20 add `provideZonelessChangeDetection()`; on v21 or later, do not use `provideZoneChangeDetection()` unless you deliberately keep Zone.js.
- Change detection is scheduled when a signal read by a template changes, a template or host listener fires, `markForCheck` is called (the `async` pipe does it), `ComponentRef.setInput` is used, or a dirty view is attached.
- Remove `zone.js` and `zone.js/testing` from the `polyfills` array of both the build and test targets, then `npm uninstall zone.js`.
- Replace `NgZone.onMicrotaskEmpty`, `onStable` and `isStable` with `afterNextRender` or `afterEveryRender`; those observables never emit without Zone.js. `NgZone.run` and `runOutsideAngular` still work.
- `ChangeDetectionStrategy.OnPush` is the default in v22; use `ChangeDetectionStrategy.Eager` only for a component that relies on the old always-check behaviour (an `ng update` migration adds it where needed).

## 9. RxJS interop

```ts
import {Component, DestroyRef, inject, signal} from '@angular/core';
import {takeUntilDestroyed, toObservable, toSignal} from '@angular/core/rxjs-interop';
import {debounceTime, distinctUntilChanged, switchMap} from 'rxjs';
import {HttpClient} from '@angular/common/http';

@Component({ selector: 'app-typeahead', template: `...` })
export class Typeahead {
  private readonly http = inject(HttpClient);
  readonly query = signal('');

  readonly results = toSignal(
    toObservable(this.query).pipe(
      debounceTime(250),
      distinctUntilChanged(),
      switchMap(q => this.http.get<string[]>('/api/search', { params: { q } })),
    ),
    { initialValue: [] as string[] },
  );

  constructor() {
    inject(SomeStream).events$.pipe(takeUntilDestroyed()).subscribe(e => console.debug(e));
  }
}
```

- `toSignal(obs)` subscribes immediately and unsubscribes on destroy; the value is `undefined` until the first emission unless `initialValue` or `requireSync: true` is given. Errors thrown by the source surface when the signal is read.
- `toSignal` and `toObservable` need an injection context or an explicit `injector`. `takeUntilDestroyed()` also needs one, or a `DestroyRef` argument.
- `toObservable` emits asynchronously (effect-based), so it can skip intermediate values; it suits debouncing pipelines, not synchronous mirroring.

## 10. Render hooks

- `afterNextRender(() => ...)` runs once after the next render, browser only; use it for focus, measuring and third-party widgets. `afterEveryRender` runs after every render.
