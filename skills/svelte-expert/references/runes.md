# Svelte 5 Runes and Component Patterns

Reactive state, derived values, effects, props, snippets, attachments, context, reactive classes and modules, store interop, async expressions and the Svelte 4 to 5 migration table. Written for Svelte 5.57.x; items added in a specific minor are marked with the version.

## Contents

1. [State](#1-state)
2. [Derived](#2-derived)
3. [Effects](#3-effects)
4. [Props and bindables](#4-props-and-bindables)
5. [Snippets and children](#5-snippets-and-children)
6. [Attachments and actions](#6-attachments-and-actions)
7. [Context](#7-context)
8. [Reactive modules and classes](#8-reactive-modules-and-classes)
9. [Stores and legacy interop](#9-stores-and-legacy-interop)
10. [Async expressions and boundaries](#10-async-expressions-and-boundaries)
11. [Svelte 4 to 5 migration table](#11-svelte-4-to-5-migration-table)

## 1. State

```svelte
<script lang="ts">
  let count = $state(0);
  let todos = $state<{ text: string; done: boolean }[]>([]);
  let big = $state.raw({ rows: [] as number[] });

  const add = (text: string) => todos.push({ text, done: false }); // deep proxy: tracked
  const replace = () => (big = { rows: [1, 2, 3] });               // raw: reassign only
</script>
```

- `$state(value)`: plain objects and arrays become deeply reactive proxies. Class instances, `Map`, `Set` and `Date` are not proxied; use a reactive class field or the `svelte/reactivity` equivalents.
- `$state.raw(value)`: no proxy; only reassignment triggers updates. Cheaper for large read-mostly data.
- `$state.snapshot(proxy)`: returns a plain, non-reactive copy. Use it before `structuredClone`, `JSON`-style serialisation to workers, or logging.
- A module-level `export let n = $state(0)` that is reassigned cannot be exported (importers cannot track reassignment). Export an object, class or getter functions.
- State passed to a function is passed by value for primitives. To keep reactivity across the call, pass a getter (`() => count`) or an object.

## 2. Derived

```svelte
<script lang="ts">
  let items = $state<{ price: number; qty: number }[]>([]);
  const total = $derived(items.reduce((s, i) => s + i.price * i.qty, 0));
  const summary = $derived.by(() => {
    const n = items.length;
    return n === 0 ? 'empty' : `${n} lines, total ${total.toFixed(2)}`;
  });
</script>
```

- `$derived(expr)` takes an expression; `$derived.by(fn)` takes a function for multi-statement logic.
- Derived values are lazy and cached; they recompute only when a dependency changes. Since Svelte 5.25 a derived can be temporarily overridden by assignment (useful for optimistic UI); it re-syncs when its dependencies change. Deriveds must be pure: writing state inside one throws `state_unsafe_mutation`.
- `await` inside `$derived(...)` needs the experimental async flag (section 10).

## 3. Effects

```svelte
<script lang="ts">
  let { interval = 1000 }: { interval?: number } = $props();
  let ticks = $state(0);

  $effect(() => {
    const id = setInterval(() => ticks++, interval); // interval is a dependency
    return () => clearInterval(id);                   // teardown before re-run and on destroy
  });
</script>
```

- `$effect` runs after the DOM updates, in the browser only (never during SSR). It re-runs when any state read synchronously during the last run changes.
- `$effect.pre` runs before DOM updates; use it for measuring or restoring scroll positions.
- `$effect.root(fn)` creates an effect scope that is not tied to a component; it returns a dispose function. Needed in tests and in module code.
- `untrack(() => x)` from `svelte` reads state without making it a dependency.
- Do not use effects to derive state, to sync two states, or to fire events that an event handler could fire. Prefer `$derived`, handlers, `bind:`, snippets and attachments.
- Objects are not deeply tracked by effects: `$effect(() => { console.log(obj) })` re-runs only if `obj` itself is reassigned. Read the properties you care about, or `$state.snapshot(obj)`.

## 4. Props and bindables

```svelte
<script lang="ts">
  interface Props {
    value: string;
    label?: string;
    onchange?: (v: string) => void;
    [key: string]: unknown;
  }
  let { value = $bindable(''), label = 'Name', onchange, ...rest }: Props = $props();
  const uid = $props.id(); // unique per component instance, stable across SSR and hydration
</script>

<label for={uid}>{label}</label>
<input id={uid} bind:value oninput={() => onchange?.(value)} {...rest} />
```

- `$bindable(fallback)` marks a prop that the parent may bind with `bind:value={x}`. Without `bind:` the child may still reassign it locally.
- In SvelteKit, `let { data, form }: PageProps = $props();` types route components with the generated `PageProps` and `LayoutProps` from `./$types`.

## 5. Snippets and children

```svelte
<!-- Table.svelte -->
<script lang="ts" generics="T">
  import type { Snippet } from 'svelte';
  let { rows, header, row, empty }: {
    rows: T[];
    header: Snippet;
    row: Snippet<[T, number]>;
    empty?: Snippet;
  } = $props();
</script>

<table>
  <thead><tr>{@render header()}</tr></thead>
  <tbody>
    {#each rows as r, i}
      <tr>{@render row(r, i)}</tr>
    {:else}
      {@render empty?.()}
    {/each}
  </tbody>
</table>
```

- Content between component tags that is not a snippet becomes the implicit `children` snippet: `{@render children?.()}`.
- Declaration tags (`{const total = a + b}` and `{let x = $state(0)}`, available since 5.56) define template-local values; `{@const}` is the older form.

## 6. Attachments and actions

```svelte
<script lang="ts">
  import type { Attachment } from 'svelte/attachments';

  const autofocus: Attachment<HTMLInputElement> = (node) => {
    node.focus();
    return () => {}; // optional cleanup
  };
</script>

<input {@attach autofocus} />
```

- `{@attach fn}` runs `fn(element)` when the element mounts and re-runs if reactive values read inside it change. It can return a cleanup function. Create parameterised attachments by returning a function from a factory: `{@attach tooltip(text)}`.
- `use:action` (from `svelte/action`) remains supported and is not deprecated. Use it for existing libraries; use attachments for new code that needs reactivity.

## 7. Context

```ts
// src/lib/state/theme.svelte.ts
import { createContext } from 'svelte';

export class Theme {
  mode = $state<'light' | 'dark'>('light');
  toggle() { this.mode = this.mode === 'light' ? 'dark' : 'light'; }
}

export const [getTheme, setTheme] = createContext<Theme>();
```

```svelte
<!-- +layout.svelte -->
<script lang="ts">
  import { setTheme, Theme } from '#lib/state/theme.svelte.js';
  let { children } = $props();
  setTheme(new Theme());
</script>

{@render children()}
```

- `createContext` (since 5.40) returns a typed getter and setter; the getter throws if no context was set. Svelte 5.57 added a `has` function to the returned tuple for optional lookups.
- Context lives in the component tree, so each server request gets its own value. Module singletons are shared by all requests.
- `setContext(key, value)`, `getContext(key)`, `hasContext(key)` and `getAllContexts()` remain available. Use a `Symbol` key to avoid collisions.
- Calling the getter or setter must happen during component initialisation (top level of `<script>`), not in handlers, effects or after `await`. On the server, `setContext` after an `await` throws `set_context_after_init`.

## 8. Reactive modules and classes

```ts
// src/lib/state/counter.svelte.ts
export function createCounter(initial = 0) {
  let count = $state(initial);
  return {
    get count() { return count; },
    increment: () => count++,
    reset: () => (count = initial)
  };
}

export class Selection<T> {
  selected = $state<T | null>(null);
  items = $state.raw<T[]>([]);
  count = $derived(this.items.length);
}
```

- Runes in `.svelte.ts`/`.svelte.js` files are compiled; in plain `.ts` they are errors.
- Returning getters keeps reactivity when the object is destructured at the call site only if the destructuring is avoided; use `counter.count`, not `const { count } = counter`.
- `svelte/reactivity` provides `SvelteSet`, `SvelteMap`, `SvelteDate`, `SvelteURL`, `SvelteURLSearchParams`, `MediaQuery` and `createSubscriber` (bridge an external event source into reactivity). `SvelteMap` gained `getOrInsert` and `getOrInsertComputed` in 5.57.

## 9. Stores and legacy interop

- `writable`, `readable`, `derived`, `get` and `fromStore`/`toStore` live in `svelte/store`. In components `$store` auto-subscribes, which works in runes mode for store variables.
- Prefer runes for new app state. Keep stores when a library API exposes them, or when the stream semantics (subscribe, set, update) are the point.
- `fromStore(store)` returns an object with a reactive `.current`; `toStore(get, set)` returns a store from rune-based state.
- `createEventDispatcher` is deprecated; use callback props. Component instantiation with `new Component()` is gone: use `mount(Component, { target, props })`, `hydrate`, and `unmount` from `svelte`.

## 10. Async expressions and boundaries

```svelte
<script lang="ts">
  let id = $state(1);
  const user = $derived(await fetchUser(id));
</script>

<svelte:boundary>
  <h1>{user.name}</h1>
  <p>{await fetchBio(id)}</p>

  {#snippet pending()}<p>Loading</p>{/snippet}
  {#snippet failed(error, reset)}
    <p>Something went wrong.</p>
    <button onclick={reset}>Retry</button>
  {/snippet}
</svelte:boundary>
```

- Needs `compilerOptions: { experimental: { async: true } }`: in `svelte.config.js` for SvelteKit 2, in `sveltekit({ compilerOptions: ... })` for SvelteKit 3. The docs state the flag is removed in Svelte 6. Treat the feature as experimental.
- Updates that depend on pending async work are held back so the UI never shows mixed old and new values; independent updates are not blocked.
- `$effect.pending()` returns the number of pending promises in the current boundary; use it for inline "updating" hints.
- `<svelte:boundary onerror={(e, reset) => ...}>` also catches errors in effects and rendering. It does not catch errors thrown in event handlers.

## 11. Svelte 4 to 5 migration table

| Svelte 4 | Svelte 5 |
|---|---|
| `let count = 0` (reactive at top level) | `let count = $state(0)` |
| `$: double = count * 2` | `const double = $derived(count * 2)` |
| `$: { sideEffect(count) }` | `$effect(() => { sideEffect(count) })` |
| `export let name = 'x'` | `let { name = 'x' } = $props()` |
| `<slot />`, `<slot name="a" />` | `{@render children?.()}`, `{@render a?.()}` |
| `<div slot="a">` | `{#snippet a()}...{/snippet}` |
| `let:item` on a component | snippet parameters: `{#snippet row(item)}` |
| `on:click={fn}` | `onclick={fn}` |
| `on:click\|preventDefault={fn}` | call `e.preventDefault()` in the handler |
| `createEventDispatcher()` | callback props |
| `new Component({ target })` | `mount(Component, { target })` |
| `<svelte:component this={C} />` | `<C />` with `C` a variable (dynamic) |
| `$app/stores` `$page` | `page` from `$app/state` |
| Stores for shared state | `.svelte.ts` modules, classes, context |

Migration tooling: `npx sv migrate svelte-5` rewrites a Svelte 4 project (it runs through `svelte-migrate@1`, which no longer receives fixes for new patterns). Commit first, run it, then review each component: the tool inserts `run()` from `svelte/legacy` for `$:` blocks it cannot convert and `createBubbler` helpers for forwarded events. Replace those by hand. Components can be migrated one at a time; Svelte 4 syntax keeps working in components that use no runes.
