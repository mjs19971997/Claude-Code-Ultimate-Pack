# Form Actions and Remote Functions

Native form actions with progressive enhancement, and the experimental remote functions (`query`, `query.batch`, `query.live`, `form`, `command`, `prerender`). Written for SvelteKit 3.1.x. Remote functions are still marked experimental in the docs and can change without notice.

## Contents

1. [Form actions](#1-form-actions)
2. [Validation and error display](#2-validation-and-error-display)
3. [use:enhance](#3-useenhance)
4. [Choosing between actions and remote functions](#4-choosing-between-actions-and-remote-functions)
5. [Enabling remote functions](#5-enabling-remote-functions)
6. [query, batch and live](#6-query-batch-and-live)
7. [form](#7-form)
8. [command](#8-command)
9. [prerender](#9-prerender)
10. [Single-flight mutations](#10-single-flight-mutations)
11. [Security rules](#11-security-rules)

## 1. Form actions

```ts
// src/routes/login/+page.server.ts
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import * as auth from '#lib/server/auth.js';

export const actions: Actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const email = String(data.get('email') ?? '').trim();
    const password = String(data.get('password') ?? '');

    if (!email || !password) return fail(400, { email, missing: true });

    const session = await auth.login(email, password);
    if (!session) return fail(400, { email, incorrect: true }); // never echo the password

    cookies.set('session', session.id, {
      path: '/', httpOnly: true, secure: true, sameSite: 'lax', maxAge: 60 * 60 * 24 * 7
    });
    redirect(303, '/');
  }
};
```

```svelte
<!-- src/routes/login/+page.svelte -->
<script lang="ts">
  import { enhance } from '$app/forms';
  import type { PageProps } from './$types';
  let { form }: PageProps = $props();
</script>

<form method="POST" use:enhance>
  {#if form?.incorrect}<p role="alert">Wrong email or password.</p>{/if}
  <label>Email <input name="email" type="email" value={form?.email ?? ''} required /></label>
  <label>Password <input name="password" type="password" required /></label>
  <button>Log in</button>
</form>
```

- A page has either one `default` action or several named actions invoked with `action="?/name"` (or `formaction="?/name"` on a button). A page cannot have both `default` and named actions.
- Actions live in `+page.server.ts` only. They receive the same event as server `load` (`request`, `cookies`, `locals`, `params`, `url`, `fetch`, `platform`).
- Return plain serialisable data for success; the value arrives as the `form` prop and as `page.form`. Return `fail(status, data)` for validation errors; the status is the HTTP status of the response (also for enhanced submissions in SvelteKit 3).
- `redirect(303, url)` after success avoids resubmission on reload. `error(status, message)` renders `+error.svelte`.
- Submitting to an action of another page: `action="/other?/save"`. With `use:enhance` in SvelteKit 3 this navigates to that page afterwards, as a native form would.

## 2. Validation and error display

- Validate with a schema library on the server (Valibot, Zod or another Standard Schema implementation). Convert `FormData` with `Object.fromEntries(data)` only for flat forms; use `data.getAll('tag')` for repeated names and parse numbers and booleans explicitly (`FormData` values are strings or `File`).
- Return field errors and the submitted values (except secrets): `fail(400, { values, errors: { email: ['Not a valid address'] } })`.
- Render errors next to fields and link them with `aria-describedby`; set `aria-invalid` on invalid inputs; move focus to the first error or to a summary with `role="alert"`.

## 3. use:enhance

```svelte
<form
  method="POST"
  action="?/save"
  use:enhance={({ formData, cancel }) => {
    if (!formData.get('title')) { cancel(); return; }  // client-side guard
    saving = true;
    return async ({ result, update }) => {
      saving = false;
      if (result.type === 'success') await invalidate('app:items');
      await update({ reset: false });                   // default behaviour, tuned
    };
  }}
>
  <!-- fields; import { enhance } from '$app/forms' and { invalidate } from '$app/navigation' -->
</form>
```

- Without options, `use:enhance` submits with `fetch`, updates `form` and `page.status`, resets the form after success, re-runs `load` functions, and redirects on `redirect` results. Focus is reset to the nearest `autofocus` element or the body.
- The callback may return a function that receives `{ result, update, formData, formElement, action }`. `result.type` is `success`, `failure`, `redirect` or `error`.
- `update({ reset: false })` keeps field values; `update({ refreshAll: false })` skips refreshing data; `update({ navigate: false })` applies non-redirect results to the current page (see the `$app/forms` types for the full list).
- Always render a working `<form method="POST">`; `use:enhance` is an enhancement, and the page must work with JavaScript disabled or not yet loaded.

## 4. Choosing between actions and remote functions

| Need | Prefer |
|---|---|
| Plain form, works without JavaScript, minimal API surface | form action |
| Typed data fetched inside a component, colocated with its UI | `query` |
| Many components requesting rows by id (n+1) | `query.batch` |
| Server push of changing values | `query.live` |
| Mutation from a button handler or timer, no form | `command` |
| Form with typed fields, per-field issues and schema validation shared with client | remote `form` |

## 5. Enabling remote functions

```ts
// vite.config.ts: inside defineConfig({ plugins: [ ... ] })
sveltekit({
  adapter: adapter(),
  experimental: { remoteFunctions: true },
  compilerOptions: { experimental: { async: true } }
})
```

- Remote functions live in files whose name includes a `remote` segment: `data.remote.ts`, `todos.remote.ts`, `remote.ts`. Without `experimental.remoteFunctions`, SvelteKit 3 disallows these files. In SvelteKit 2 the flag is `kit.experimental.remoteFunctions` in `svelte.config.js`.
- `await` in components needs `compilerOptions.experimental.async`. Without it you can still use the returned promise-like objects with `.current`, `.loading`, `.error` instead of `await`.
- Remote modules cannot live in a `server/` directory and cannot export schemas or non-function values; share schemas from a plain module.
- Every exported remote function becomes an HTTP endpoint. Treat each as public input.
- Queries cannot be used on pages that are fully prerendered (including with adapter-static); use `prerender` functions there.

## 6. query, batch and live

```ts
// src/routes/posts/data.remote.ts
import * as v from 'valibot';
import { error } from '@sveltejs/kit';
import { query } from '$app/server';
import * as db from '#lib/server/db.js';

export const getPosts = query(async () => db.listPosts());

export const getPost = query(v.string(), async (slug) => {
  const post = await db.getPost(slug);
  if (!post) error(404, 'Not found');
  return post;
});

export const getAuthors = query.batch(v.number(), async (ids) => {
  const rows = await db.authorsByIds(ids);             // one query for all ids in this tick
  return (id) => rows.find((r) => r.id === id);
});
```

- A query takes one argument validated by a Standard Schema; pass `'unchecked'` as the first argument only for internal tools where you validate yourself. Arguments and results are serialised with devalue, so `Date`, `Map` and custom `transport` types work.
- Queries are cached per argument while in use: `getPosts() === getPosts()`. `.refresh()` refetches; `.set(value)` overwrites the client cache; both can also be called on the server inside a mutation (section 10).
- Without `await`, a query object exposes `loading`, `error`, `ready` and `current` for template use with `{#if}`.
- `query.batch(schema, async (inputs) => (input) => result)` groups calls made in the same macrotask. Separate non-exported `query.batch` functions do not share a batch (fixed in 3.1.1).
- `query.live(schema?, async function* () { ... })` returns an `AsyncIterable`; the client keeps a streaming connection and exposes the latest value as `current`. Multiple consumers share one connection. Do not cache live query responses in a service worker. There is no `refresh()`; mutations can call `.reconnect()`.

## 7. form

```ts
// src/routes/blog/data.remote.ts
import * as v from 'valibot';
import { error, invalid, redirect } from '@sveltejs/kit';
import { form } from '$app/server';
import * as db from '#lib/server/db.js';
import { requireUser } from '#lib/server/auth.js';

export const createPost = form(
  v.object({
    title: v.pipe(v.string(), v.nonEmpty(), v.maxLength(120)),
    content: v.pipe(v.string(), v.nonEmpty()),
    draft: v.optional(v.boolean(), false)           // booleans must be optional or defaulted
  }),
  async ({ title, content, draft }, issue) => {
    const user = requireUser();                     // uses getRequestEvent() inside
    if (await db.titleTaken(user.id, title)) invalid(issue.title('You already used this title'));
    const slug = await db.insertPost(user.id, { title, content, draft });
    redirect(303, `/blog/${slug}`);
  }
);
```

```svelte
<script lang="ts">
  import { createPost } from './data.remote';
</script>

<form {...createPost}>
  <label>Title
    {#each createPost.fields.title.issues() ?? [] as issue}<p role="alert">{issue.message}</p>{/each}
    <input {...createPost.fields.title.as('text')} />
  </label>
  <label>Content <textarea {...createPost.fields.content.as('text')}></textarea></label>
  <label><input {...createPost.fields.draft.as('checkbox')} /> Draft</label>
  <button disabled={!!createPost.pending}>Publish</button>
</form>
```

- Spread the form object on `<form>`: it supplies `method`, `action` and a progressive-enhancement attachment, so it works without JavaScript.
- Every field must be created with `form.fields.name.as(type, value?)`; SvelteKit uses the generated `name` (with type prefixes for numbers and booleans) to coerce the submission. `radio`, `submit` and `hidden` inputs need the value argument; checkboxes in arrays need it too.
- Validation: failing the schema skips the handler and fills `fields.x.issues()` (undefined until validated). Use `invalid(issue.field('message'))` in the handler for server-only checks. `createPost.validate()` validates on demand (`{ includeUntouched: true }` for all fields) and `createPost.preflight(schema)` validates on the client before sending.
- `createPost.enhance(async (form) => { ... })` customises submission: `await form.submit()` resolves to `true` when the data was valid, and `form.element.reset()` clears inputs, because enhanced forms are not reset automatically. `form.submit().updates(...)` accepts query updates such as `todos.withOverride(...)`.
- Sensitive fields: names beginning with an underscore are not repopulated after a failed submission (for example `_password`); check the docs section "Handling sensitive data".
- Several instances of one form in a list: `createPost.for(id)` gives an isolated instance per key; `createPost.result` and `createPost.pending` expose the outcome and in-flight count.

## 8. command

```ts
// src/routes/items/likes.remote.ts
import * as v from 'valibot';
import { command, query } from '$app/server';
import * as db from '#lib/server/db.js';

export const getLikes = query(v.string(), (id) => db.likes(id));

export const addLike = command(v.string(), async (id) => {
  await db.addLike(id);
  await getLikes(id).refresh();                      // single-flight: result travels with the response
});
```

- A command is a mutation callable from event handlers and timers, not during render. It needs JavaScript, so prefer `form` for user-submitted data.
- Without a refresh, `set` or `reconnect` in the handler, the client falls back to refreshing all active queries; with them, only the listed queries update.
- Optimistic updates: `addLike(id).updates(getLikes(id).withOverride((n) => n + 1))` applies a client-side override until the command resolves. `addLike.pending` counts running calls.

## 9. prerender

```ts
export const getPost = prerender(v.string(), async (slug) => db.getPost(slug), {
  inputs: () => ['first-post', 'second-post'], // arguments rendered at build time
  dynamic: false
});
```

- Results are produced at build time and served as static data; `inputs` lists the arguments to render. See the `$app/server` types for the `dynamic` option. Use for data that changes per deploy, not per user.

## 10. Single-flight mutations

By default a successful `form` or `command` refreshes all queries on the page, costing a second round trip.

- Calling `getPosts().refresh()`, `getPost(id).set(value)` or `getLive().reconnect()` inside the handler replaces that default: only the named queries are updated, and their new values travel in the mutation response.
- Every requested client update must be refreshed, set, reconnected or explicitly ignored, otherwise that query goes into an error state in SvelteKit 3 (`errors when a client-requested single-flight mutation isn't respected`).
- A client can request specific refreshes with `.updates(query)` when calling a command or submitting a form. On the server, `requested(getPost, limit)` from `$app/server` lists the query instances the client asked to update, and `.refreshAll()` on its result refreshes them; the same exists for live queries with `reconnectAll()`.

## 11. Security rules

- Validate every argument with a schema; for forms, validate on the server even when a `preflight` schema exists.
- Authorize per resource (does this user own `id`?), authenticate inside every action, and use parameterised queries.
- Authenticate inside the function with `getRequestEvent()`; do not rely on the calling page or layout. `event.url`, `route` and `params` in remote function requests describe the calling page and can be forged.
- Remote function validation failures reach `handleError` with `kind: 'validation'`; return a generic message and log the issues server side.
- CSRF protection applies to remote functions; set `paths.origin` behind a reverse proxy and use `csrf.trustedOrigins` for cross-origin callers.
