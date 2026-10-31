# Forms and HTTP

Signal forms, typed reactive forms, `HttpClient` configuration, functional interceptors, error handling, XSRF, `httpResource` and HTTP testing for Angular 22. Signal forms API names were read from the public API report for `@angular/forms/signals` and the adev validation guide (2026-10).

## Contents

1. [Choosing a forms approach](#1-choosing-a-forms-approach)
2. [Signal forms](#2-signal-forms)
3. [Signal form validation](#3-signal-form-validation)
4. [Typed reactive forms](#4-typed-reactive-forms)
5. [HttpClient setup](#5-httpclient-setup)
6. [Interceptors](#6-interceptors)
7. [Errors, retries and cancellation](#7-errors-retries-and-cancellation)
8. [XSRF and credentials](#8-xsrf-and-credentials)
9. [Testing HTTP](#9-testing-http)

## 1. Choosing a forms approach

- Signal forms (`@angular/forms/signals`) moved into the public API in v22 (the adev overview still says they require v21 or later). They suit new code where the model is already a signal.
- Typed reactive forms (`FormGroup`, `FormControl`, `FormArray`) are mature, work with every third-party control, and remain the safer pick for large existing forms.
- Interop exists: v22 shims legacy `NG_VALIDATORS` and `ControlValueAccessor` into signal forms, and `ngNoCva` opts a control out of CVA handling. Test third-party controls before migrating a form.
- v22 removed string values from the `min` and `max` rules; pass numbers or `null`.

## 2. Signal forms

```ts
import {Component, inject, signal} from '@angular/core';
import {FormField, FormRoot, email, form, minLength, required} from '@angular/forms/signals';

interface Registration { name: string; email: string; password: string }

@Component({
  selector: 'app-register',
  imports: [FormField, FormRoot],
  template: `
    <form [formRoot]="f">
      <label for="name">Name</label>
      <input id="name" [formField]="f.name" />

      <label for="email">Email</label>
      <input id="email" type="email" [formField]="f.email" autocomplete="email" />
      @if (f.email().touched() && f.email().invalid()) {
        @for (e of f.email().errors(); track e.kind) {
          <p role="alert">{{ e.message }}</p>
        }
      }

      <label for="pw">Password</label>
      <input id="pw" type="password" [formField]="f.password" autocomplete="new-password" />

      <button type="submit" [disabled]="f().submitting()">Create account</button>
    </form>
  `,
})
export class Register {
  private readonly api = inject(AccountApi);
  protected readonly model = signal<Registration>({ name: '', email: '', password: '' });

  protected readonly f = form(
    this.model,
    (p) => {
      required(p.name, { message: 'Name is required' });
      required(p.email, { message: 'Email is required' });
      email(p.email, { message: 'Enter a valid email address' });
      minLength(p.password, 12, { message: 'Use at least 12 characters' });
    },
    {
      submission: {
        action: async (field) => {
          await this.api.register(field().value());   // send to the server
          return undefined;                            // no server-side errors
        },
      },
    },
  );
}
```

- `form(modelSignal, schemaFn?, options?)` returns a `FieldTree`. Each node is callable: `f.email()` returns the `FieldState` (signals `value`, `errors`, `invalid`, `touched`, `dirty`, `pending`, `disabled`, `hidden`, and more); `f()` is the root state.
- `[formField]="f.email"` binds a native control or a custom control; the model signal is the source of truth and updates as the user types.
- `<form [formRoot]="f">` wires submission to the `submission.action` option and handles `preventDefault`. Alternatively call `submit(f, async (field) => {...})` from a handler; it returns a `Promise<boolean>`.
- A submit action may return server-side validation errors (a `TreeValidationResult`) to display them on fields.
- Dynamic lists: `applyEach(p.items, itemSchema)`; `@for (item of f.items; track item)` binds each child field.
- Conditional state: `disabled(path, logic)`, `hidden(path, logic)`, `readonly(path, logic)`, `applyWhen(path, predicate, schema)`.

## 3. Signal form validation

```ts
import {applyEach, debounce, min, max, pattern, validate, validateHttp} from '@angular/forms/signals';

form(model, (p) => {
  min(p.age, 18, { message: 'Must be at least 18' });
  max(p.age, 120);
  pattern(p.zip, /^\d{5}$/, { message: 'Five digits' });

  // Custom synchronous rule
  validate(p.confirm, (ctx) =>
    ctx.value() === ctx.valueOf(p.password)
      ? undefined
      : { kind: 'mismatch', message: 'Passwords differ' },
  );

  // Async rule backed by HttpClient, debounced
  debounce(p.username, 300);
  validateHttp(p.username, {
    request: (ctx) => (ctx.value() ? `/api/usernames/${encodeURIComponent(ctx.value())}` : undefined),
    onSuccess: (res: { taken: boolean }) => (res.taken ? { kind: 'taken', message: 'Username is taken' } : undefined),
    onError: () => ({ kind: 'lookup-failed', message: 'Could not check the username' }),
  });
});
```

- Built-in rules: `required`, `email`, `min`, `max`, `minLength`, `maxLength`, `pattern`, `minDate`, `maxDate` (see the golden for the full list); each accepts `{message, when}` style options.
- A validator returns `undefined`, `null` or nothing for success, one error or an array of errors; errors have a `kind` and an optional `message`.
- `validateTree` reports errors on child fields from a parent rule; `validateAsync` takes `params` and a `factory` that returns a `Resource`; `validateStandardSchema` accepts a Standard Schema object (for example from a schema library that implements it) to reuse server-shared schemas.
- v22 adds a `debounce` option to `validateAsync` and `validateHttp`, and `FieldState.reloadValidation()` to re-run async validation.

## 4. Typed reactive forms

```ts
import {Component, inject} from '@angular/core';
import {FormArray, NonNullableFormBuilder, ReactiveFormsModule, Validators} from '@angular/forms';

@Component({
  selector: 'app-profile',
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="save()">
      <label for="email">Email</label>
      <input id="email" formControlName="email" type="email" />
      @if (form.controls.email.touched && form.controls.email.errors?.['email']) {
        <p role="alert">Enter a valid email address</p>
      }
      <div formArrayName="phones">
        @for (c of form.controls.phones.controls; track $index) {
          <input [formControlName]="$index" aria-label="Phone {{ $index + 1 }}" />
        }
      </div>
      <button type="submit" [disabled]="form.invalid">Save</button>
    </form>
  `,
})
export class Profile {
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    phones: this.fb.array([this.fb.control('')]),
  });

  protected save() {
    if (this.form.invalid) return;
    const value = this.form.getRawValue();   // { email: string; phones: string[] }
    // send value to the API
  }
}
```

- `NonNullableFormBuilder` gives `FormControl<string>` rather than `FormControl<string | null>`; `reset()` returns to the initial value.
- Cross-field validation goes on the group: `this.fb.group({...}, { validators: [matchValidator] })` with `ValidatorFn`.
- Accessibility for both approaches: label every control with `<label for>` or `aria-label`, associate errors with `aria-describedby`, announce them with `role="alert"` (or a live region), and move focus to the first invalid field on a failed submit.

## 5. HttpClient setup

```ts
import {provideHttpClient, withInterceptors, withXsrfConfiguration} from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([authInterceptor, errorInterceptor]),
      withXsrfConfiguration({ cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN' }),
    ),
  ],
};
```

- v22 makes the fetch backend the default. `withFetch()` is deprecated and can be removed. If you need upload progress events, add `withXhr()`; a v22 migration does this for existing projects that use it.
- `reportProgress` is deprecated in favour of `reportUploadProgress` and `reportDownloadProgress` on requests.
- SSR: `provideClientHydration()` includes an HTTP transfer cache so a request made on the server is not repeated in the browser; see the SSR reference.

## 6. Interceptors

```ts
import {HttpErrorResponse, HttpInterceptorFn} from '@angular/common/http';
import {inject} from '@angular/core';
import {Router} from '@angular/router';
import {catchError, throwError} from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith('/api/')) return next(req);        // never attach to third parties
  const token = inject(AuthService).accessToken();
  return next(token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req);
};

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401) router.navigateByUrl('/login');
      return throwError(() => err);
    }),
  );
};
```

- Interceptors run in array order for requests and in reverse for responses. `req` is immutable; use `clone`.
- Interceptors execute in an injection context, so `inject()` works. Do not call `inject()` after an `await`.
- Restrict credentials to your own API origin, as above. Leaking a bearer token to other hosts is a common bug.

## 7. Errors, retries and cancellation


## 8. XSRF and credentials

- XSRF protection applies to mutating requests (not GET or HEAD) to relative URLs or the same origin, when the server sets a readable cookie (`XSRF-TOKEN` by default) and validates the matching header (`X-XSRF-TOKEN`). Configure names with `withXsrfConfiguration`, disable with `withNoXsrfProtection()` only when the API uses a different mechanism.
- Cookie-based sessions: set `withCredentials: true` on requests to the API origin and configure CORS on the server (specific origin, `Access-Control-Allow-Credentials`).
- Bearer tokens: prefer short-lived access tokens held in memory plus a refresh token in an `HttpOnly`, `Secure`, `SameSite` cookie managed by the server. See authentication-expert for the flow design.

## 9. Testing HTTP

```ts
import {TestBed} from '@angular/core/testing';
import {provideHttpClient} from '@angular/common/http';
import {HttpTestingController, provideHttpClientTesting} from '@angular/common/http/testing';

describe('OrdersApi', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('requests open orders', async () => {
    const result = TestBed.inject(OrdersApi).list();
    const req = http.expectOne('/api/orders');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: '1' }]);
    expect(await result).toEqual([{ id: '1' }]);   // when list() returns a Promise
  });
});
```

- `provideHttpClientTesting()` replaces the backend; `expectOne`, `match` and `expectNone` find requests; `flush(body, {status, statusText})` answers them; `error(new ProgressEvent('error'))` simulates a network failure.
- With `httpResource`, flush the pending request, then `await TestBed.inject(ApplicationRef).whenStable()` before asserting on the resource signals.
