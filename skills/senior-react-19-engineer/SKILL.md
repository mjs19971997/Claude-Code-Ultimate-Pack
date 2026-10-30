---
name: senior-react-19-engineer
description: >-
  Builds and reviews React 19 components, hooks and forms: Actions (useActionState, useOptimistic, useFormStatus, use), ref as a prop, Context as provider, document metadata hoisting, Suspense and error boundaries, Server and Client Component boundaries, the React Compiler, Activity, useEffectEvent and ViewTransition. Use when writing .tsx components and custom hooks, handling forms and mutations, upgrading from React 18, configuring babel-plugin-react-compiler or eslint-plugin-react-hooks, deciding what manual memoization to keep, or testing with React Testing Library. Not for Next.js routing, caching, proxy.ts and Server Action deployment details (use nextjs-15-architect), type-level TypeScript design (use typescript-master), or WCAG and ARIA work (use accessibility-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Senior React 19 Engineer

This skill covers writing React 19 the way the current release expects: components that stay pure, state changes expressed as Actions and Transitions, effects only for synchronizing with external systems, and memoization left to the React Compiler. It spans React 19.0 to the current 19.3, noting which feature arrived in which minor, and it treats Server Components and Server Functions as a framework-provided boundary whose security rules apply regardless of framework.

> Verified against React and React DOM 19.3.1, babel-plugin-react-compiler 1.0.0, eslint-plugin-react-hooks 7.1.1, @types/react 19.3.0, Vite 8 with @vitejs/plugin-react 6, Testing Library (react 16.3) and Vitest 5 (2026-10).

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

- Covered: React 19.x APIs and idioms, Actions and forms, concurrent features, Suspense, Effects and Effect Events, refs, Context, resource and metadata rendering, the React Compiler and its lint rules, Server and Client Component rules, testing components.
- Not covered: Next.js routes, caching, `proxy.ts` and deployment (nextjs-15-architect); advanced TypeScript typing (typescript-master); styling systems (tailwindcss-master, shadcn-ui-expert); animation libraries (framer-motion-expert); ARIA patterns and audits (accessibility-expert); Core Web Vitals diagnosis (core-web-vitals-expert).

What arrived when (all stable in 19.3.1):

| Release | Additions |
|---|---|
| 19.0 | Actions in Transitions, `useActionState`, `useOptimistic`, `useFormStatus`, `use`, `ref` as a prop and ref cleanup functions, `<Context>` as a provider, native `<title>`/`<meta>`/`<link>` hoisting, stylesheet `precedence`, `preload`/`preinit` APIs, `onCaughtError`/`onUncaughtError`, Server Components and Server Functions |
| 19.2 | `<Activity>`, `useEffectEvent`, `cacheSignal` (Server Components), partial pre-rendering APIs (`prerender` with `resume`/`resumeAndPrerender`), Chrome Performance Tracks, batched Suspense reveals during SSR |
| 19.3 | `<ViewTransition>` and Fragment refs stable, `use(browser())` from `react-dom` to skip server rendering, Trusted Types integration, Server Components can render a Context imported from a `'use client'` module |

`forwardRef` still works but is no longer necessary; `Context.Provider` still works and will be deprecated. React 19 removed `propTypes`, `defaultProps` on function components, string refs, legacy context, `ReactDOM.render`/`hydrate`, `findDOMNode` and `react-test-renderer/shallow`.

## 2. Core Expertise

- **Actions**: async functions passed to `<form action>` or called inside `startTransition`; React tracks pending state, errors, optimistic updates and form reset. See [references/hooks-and-actions.md](references/hooks-and-actions.md).
- **`useActionState(action, initial, permalink?)`** returns `[state, dispatch, isPending]`; the action receives `(previousState, payload)`.
- **`useOptimistic(value, reducer?)`** shows temporary state while an Action runs; the setter must be called inside an Action or Transition.
- **`useFormStatus()`** from `react-dom` reads the parent `<form>` status (`pending`, `data`, `method`, `action`) and must be rendered inside the form.
- **`use(resource)`** reads a Promise (suspends) or a Context (works in conditions and loops, not in `try/catch`); the Promise must be stable across renders.
- **Effects**: synchronization with external systems only; `useEffectEvent` separates event-like logic fired from an Effect from the Effect's dependencies.
- **React Compiler 1.0**: automatic memoization at build time; compiler-powered lint rules ship in `eslint-plugin-react-hooks`. See [references/react-compiler.md](references/react-compiler.md).
- **Server Components boundary**: `'use client'` starts the client graph, `'use server'` marks Server Functions (public endpoints). See [references/server-components-and-boundaries.md](references/server-components-and-boundaries.md).
- **UI state APIs**: `<Activity mode="visible" | "hidden">` keeps state of hidden UI and cleans up its Effects; `<ViewTransition>` animates updates inside Transitions; Fragment refs observe a group of siblings.

## 3. Workflow

1. Check versions (`react`, `react-dom`, `@types/react`, `eslint-plugin-react-hooks`) and keep `react` and `react-dom` on the same patched 19.x.
2. Model state: derive what can be derived during render; keep one source of truth; lift state only as far as needed.
3. Classify each interaction: pure render, event handler, Action (async mutation with pending/error/optimistic state), or Effect (external synchronization).
4. Write components as pure functions of props and state; do not mutate props, state or module-level values during render.
5. Put async data behind Suspense (`use(promise)` with a promise created outside render, or a data library) and errors behind error boundaries.
6. Enable `eslint-plugin-react-hooks` (`recommended`) and fix findings; they mark code the compiler cannot optimize.
7. Turn on the React Compiler after lint is clean; verify with React DevTools ("Memo" badge). Do not write new `useMemo`/`useCallback` by default; leave existing memoization in place or test carefully before removing it.
8. Test behavior through the DOM with Testing Library, including pending, error and success paths of Actions.
9. Review boundaries: what runs on the server, what is serialized to the client, and what each public Server Function checks.

## 4. Decision Rules

- State that can be computed from props or other state is not state; compute it in render (the compiler memoizes it if needed).
- Mutation with pending/error UI: an Action (`<form action>` or `startTransition(async () => ...)`) with `useActionState`; use `useOptimistic` only when the result is predictable and a rollback is acceptable.
- Reading async data during render: `use(promise)` inside Suspense. Create the promise in a Server Component, a loader, a cache or a `useMemo`-stable owner, never inline in the consuming render (a new promise every render suspends forever).
- Subscribing to an external store: `useSyncExternalStore`, not state plus Effect.
- Effect needed only to reset state when a prop changes: use a `key` on the component instead.
- Effect reads values that should not retrigger it (theme, callbacks, logging data): `useEffectEvent`. Do not use it to silence the dependency lint rule for values that are truly reactive.
- Keep UI state while hiding a panel or tab: `<Activity mode="hidden">`; unmount when state should reset or cost matters.
- Expose a DOM node: accept `ref` as a regular prop; wrap in `forwardRef` only for code that still targets React 18.
- Shared value for a subtree: `<ThemeContext value={theme}>` (no `.Provider`); for server-originated values in 19.3, a Server Component can render a Context imported from a `'use client'` module.
- Manual `useMemo`/`useCallback`: in new code rely on the compiler and add them only for precise control (for example a value used as an Effect dependency that must not change identity needlessly, or third-party code relying on stable identity). In existing code, leave them in place; removing them can change compiled output.
- Class components stay only for error boundaries (or use a library boundary); there is no hook equivalent.
- Server Component by default in RSC frameworks; `'use client'` for interactivity, state, Effects and browser APIs.

## 5. Coding Standards

- Function components with named exports; props typed with an interface or type; `ref` typed as `React.Ref<HTMLInputElement>` in props.
- Use `React.JSX` rather than the removed global `JSX` namespace; `useRef` requires an argument (`useRef<HTMLDivElement>(null)`); ref callbacks must not implicitly return a value (use a block body or return a cleanup function).
- Keys: stable ids, never array indexes for reorderable lists.
- Default values with parameter defaults, not `defaultProps`.
- Never call Hooks conditionally; `use` may be conditional. Effect Events are called only inside Effects or other Effect Events, and are not listed in dependency arrays.
- Event handlers named `handleX` internally, `onX` as props.
- Form controls: uncontrolled with `name` and `FormData` by default; controlled only when the UI reacts to every keystroke.
- Do not read or write `ref.current` during render (lint rule `react-hooks/refs`).
- Do not call `setState` synchronously inside an Effect to derive state (`react-hooks/set-state-in-effect`); compute it during render.
- Do not define components inside components (`react-hooks/static-components`).
- Render at most one `<title>` at a time; stylesheets need `precedence` for hoisting and ordering.
- Use `react-dom` resource APIs (`preload`, `preinit`, `preconnect`, `prefetchDNS`) instead of hand-managed `<link>` injection in Effects.

## 6. Project Structure

```
src/
├── main.tsx                      # createRoot / hydrateRoot with onCaughtError, onUncaughtError
├── app/
│   ├── App.tsx
│   └── providers.tsx             # 'use client' context providers (RSC apps)
├── features/
│   └── orders/
│       ├── OrderList.tsx
│       ├── OrderForm.tsx         # Action-based form
│       ├── useOrderFilters.ts    # custom hook, one concern
│       ├── orders.api.ts         # fetchers; server modules marked server-only in RSC apps
│       └── OrderList.test.tsx
├── components/                   # presentational, reusable
├── lib/                          # pure helpers
└── test/setup.ts                 # Testing Library setup
```

## 7. Design Patterns

- **Container-free data flow**: a parent creates or receives a promise, passes it to a child that calls `use(promise)` within `<Suspense>`.
- **Action props**: components expose `action` or `onSubmitAction` props that may be async; they call them in `startTransition` so parents get pending state for free.
- **Form action state machine**: `{ status: 'idle' | 'error' | 'success', errors?, values? }` returned from the Action and rendered by the form.
- **Optimistic reducer**: `useOptimistic(items, (current, added) => [...current, { ...added, pending: true }])`; the real data replaces it when the Action settles.
- **Compound components** with Context for tab, menu and dialog families; `<Context value>` for the provider.
- **Controlled-by-key resets**: `<Profile key={userId} />` resets internal state without Effects.
- **Activity for navigation**: render likely-next panels in `hidden` mode to prefetch and keep state of previous panels.
- **Error boundaries per feature** with a reset path; report through `onCaughtError`/`onUncaughtError` (React 19 no longer re-throws render errors).
- **Custom hooks** wrap one concern (`useDebouncedValue`, `useMediaQuery` via `useSyncExternalStore`) and return stable, minimal APIs.

## 8. Best Practices

- Prefer composition (`children`, slots) to prop drilling and to Context for everything.
- Split Contexts by update rate; the compiler memoizes values but a single hot context still rerenders all consumers.
- Colocate state with the component that uses it; lift only when two siblings need it.
- Use `useDeferredValue(value, initialValue?)` for expensive derived UI from fast input; `useTransition` for state updates that may suspend.
- Wrap route or panel-level Suspense boundaries deliberately; too many boundaries cause popcorn loading, too few block the page.
- Document metadata can be rendered by any component (`<title>`, `<meta>`, `<link>`); React hoists it into `<head>`. A framework metadata API may be preferable for per-route SEO.
- Use `<ViewTransition>` for enter/exit/update/share animations triggered by Transitions; updates not wrapped in a Transition do not animate.
- Report errors through root options and boundaries, not by relying on re-thrown errors.
- Keep components under one screen of JSX; extract hooks for logic and components for markup.
- Use Fragment refs (19.3) to attach observers or focus management across siblings without wrapper divs.

## 9. Performance

- Measure first: React DevTools Profiler and the Chrome Performance Tracks added in 19.2 (Scheduler and Components tracks).
- Let the compiler memoize: with it enabled, components and hooks that follow the Rules of React get fine-grained memoization, including after early returns.
- Fix what the compiler cannot fix: large lists (virtualize), expensive work in render (move to a worker or memoized module-level cache), unstable context values from non-compiled code.
- Keep state local; high-frequency state (pointer, scroll) lives in refs, `useSyncExternalStore` or CSS, not top-level state.
- Split code with `lazy` and Suspense at route or feature level; preload with `preload`/`preinit` or framework prefetch.
- Server Components keep large dependencies off the client bundle; do not mark broad parents `'use client'`.
- StrictMode double-invokes render and Effects in development to expose impure code; do not remove it to silence a warning. In 19.3 hydration also double-invokes Effects in Strict Mode.

## 10. Security

- Do not render untrusted HTML with `dangerouslySetInnerHTML`. When HTML must be rendered, sanitize it with a maintained sanitizer (for example DOMPurify) with an allowlist, ideally on the server, and keep a CSP without `unsafe-inline`. Prefer rendering Markdown or structured content to React elements.
- URLs from users (`href`, `src`, `action`): parse with `new URL()` and allow only `http:` and `https:` (and `mailto:` if needed); `javascript:` URLs execute on click.
- No secrets in client code: everything bundled for the browser (including `VITE_*` and `NEXT_PUBLIC_*` variables) is public. Call a server endpoint that holds the key.
- Store session tokens in `HttpOnly`, `Secure`, `SameSite` cookies, not `localStorage`; cookie-authenticated mutations need CSRF protection (SameSite, Origin checks or tokens) on the server.
- Server Functions are public HTTP endpoints: validate input with a schema (for example Zod), re-authenticate and authorize inside the function, and scope writes by tenant and owner. Do not trust arguments, closure values or hidden form fields.
- Never pass raw database rows or secrets from a Server Component to a Client Component; props are serialized to the browser. Mark server modules with `import 'server-only'`.
- Keep React server packages patched: unauthenticated RCE (CVE-2025-55182) and follow-up denial of service and source exposure issues (CVE-2025-55183, CVE-2025-55184, CVE-2025-67779, CVE-2026-23864) affected `react-server-dom-webpack`, `react-server-dom-parcel` and `react-server-dom-turbopack` in 19.0.0 to 19.2.3; fixes were released as 19.0.4, 19.1.5, 19.2.4 and later. Apps without server rendering of React Server Components are not affected.
- Trusted Types: React 19.3 passes `TrustedHTML` and related values through unchanged, so a policy created with `require-trusted-types-for 'script'` works with sanitized HTML.
- Third-party components can render untrusted content; vet libraries and lock versions.

## 11. Testing

- Test behavior through the DOM with `@testing-library/react` and `@testing-library/user-event`; query by role and label. `react-test-renderer` is deprecated and shallow rendering is removed.
- Await asynchronous Actions: after `await user.click(...)`, use `findBy*` or `waitFor` for the pending, error and success states.
- `act` is exported from `react`; Testing Library wraps it, so call it directly only for custom timers or manual updates.
- Test hooks through a small test component or `renderHook`; avoid testing internals such as the number of renders.
- Mock the network boundary (fetch handlers, Mock Service Worker), not React.
- For Suspense and `use`, render inside `<Suspense>` and assert the fallback then the content; create promises in the test so they are stable.
- Async Server Components do not render in jsdom; test their logic as functions and cover them with end-to-end tests in the framework.
- Run `eslint-plugin-react-hooks` in CI; compiler diagnostics catch impure code before tests do.

## 12. Review Checklist

- [ ] Render is pure: no mutation of props, state, module variables or `ref.current` during render.
- [ ] No Effect for derived state, event handling or resetting by prop; `key` or render-time computation used instead.
- [ ] Effects clean up subscriptions and timers; Effect Events are used only for event-like logic.
- [ ] Mutations use Actions with pending, error and (if needed) optimistic state; forms work with `FormData`.
- [ ] `use(promise)` receives a stable promise inside Suspense; an error boundary exists above.
- [ ] `ref` passed as a prop; no new `forwardRef` unless React 18 support is required.
- [ ] `eslint-plugin-react-hooks` `recommended` passes; `"use no memo"` is used only as a temporary, commented escape hatch.
- [ ] No `dangerouslySetInnerHTML` with unsanitized input; user-supplied URLs are protocol-checked.
- [ ] No secrets in client bundles; Server Functions validate, authenticate, authorize and scope writes.
- [ ] Props crossing the server-client boundary are serializable DTOs.
- [ ] Tests cover pending, error and success paths and use accessible queries.
- [ ] `react`, `react-dom` and any RSC bundler packages are on a patched 19.x release.

## 13. Production Notes

- Error reporting: React 19 reports uncaught render errors to `window.reportError` and caught ones to `console.error`; hook your reporter into `createRoot`/`hydrateRoot` options `onUncaughtError`, `onCaughtError` and `onRecoverableError`.
- React Compiler adds build time (Babel) and requires keeping `babel-plugin-react-compiler` pinned; use `panicThreshold: 'none'` (default) so uncompilable components are skipped instead of failing the build.
- Roll the compiler out gradually with `compilationMode: 'annotation'` and `"use memo"`, or per directory, then switch to the default `infer` mode.
- To support React 17 or 18 with the compiler, set `target` and install `react-compiler-runtime`.
- Upgrade path from 18: install `react@19 react-dom@19 @types/react@19 @types/react-dom@19`, run the official React 19 codemods, fix removed APIs, then adopt Actions and the compiler incrementally.
- Server Functions in React 19 are stable for app developers, but the bundler-level APIs used to implement them are not semver-stable across 19.x minors; frameworks should pin or use the version they ship against.
- Hidden `<Activity>` trees still render at low priority; budget for the work of what you keep hidden.

## 14. Examples

### Example 1: Form Action with pending and error state (client Action)

```tsx
import { useActionState } from 'react'
import { useFormStatus } from 'react-dom'
import { z } from 'zod'

type State = { status: 'idle' | 'success' | 'error'; message?: string; errors?: Record<string, string[]> }

const schema = z.object({
  name: z.string().trim().min(1).max(80),
  email: z.email().max(254),
})

// Client validation is for UX only; the server endpoint validates, authenticates and authorizes again.
async function saveProfile(_prev: State, formData: FormData): Promise<State> {
  const parsed = schema.safeParse({ name: formData.get('name'), email: formData.get('email') })
  if (!parsed.success) return { status: 'error', errors: z.flattenError(parsed.error).fieldErrors }

  const res = await fetch('/api/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(parsed.data),
  })
  if (!res.ok) return { status: 'error', message: 'Could not save your profile.' }
  return { status: 'success', message: 'Saved.' }
}

function SubmitButton() {
  const { pending } = useFormStatus() // must be rendered inside the <form>
  return <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>
}

export function ProfileForm() {
  const [state, formAction] = useActionState(saveProfile, { status: 'idle' } as State)
  return (
    <form action={formAction}>
      <label htmlFor="name">Name</label>
      <input id="name" name="name" required maxLength={80} />
      {state.errors?.name && <p role="alert">{state.errors.name[0]}</p>}
      <label htmlFor="email">Email</label>
      <input id="email" name="email" type="email" required />
      {state.errors?.email && <p role="alert">{state.errors.email[0]}</p>}
      <SubmitButton />
      {state.message && <p role={state.status === 'error' ? 'alert' : 'status'}>{state.message}</p>}
    </form>
  )
}
```

React resets uncontrolled fields after a successful form Action; return the submitted values in state if they must remain after an error.

### Example 2: Optimistic list with a reducer

```tsx
import { useOptimistic, useTransition } from 'react'

type Todo = { id: string; title: string; pending?: boolean }

export function TodoList({ todos, addTodo }: { todos: Todo[]; addTodo: (title: string) => Promise<void> }) {
  const [optimisticTodos, addOptimistic] = useOptimistic(
    todos,
    (current: Todo[], title: string): Todo[] => [...current, { id: `tmp-${current.length}`, title, pending: true }],
  )
  const [isPending, startTransition] = useTransition()

  function onSubmit(formData: FormData) {
    const title = String(formData.get('title') ?? '').trim().slice(0, 200)
    if (!title) return
    startTransition(async () => {
      addOptimistic(title)       // shown immediately, reverts to `todos` when the Action settles
      await addTodo(title)       // the parent updates `todos` (and the server re-validates the input)
    })
  }

  return (
    <>
      <ul>
        {optimisticTodos.map((t) => (
          <li key={t.id} style={{ opacity: t.pending ? 0.5 : 1 }}>{t.title}</li>
        ))}
      </ul>
      <form action={onSubmit}>
        <input name="title" maxLength={200} aria-label="New todo" />
        <button disabled={isPending}>Add</button>
      </form>
    </>
  )
}
```

### Example 3: ref as a prop with cleanup, and an Effect Event

```tsx
import { useEffect, useEffectEvent, type ComponentProps, type Ref } from 'react'

export function TextField({ ref, label, ...rest }: { ref?: Ref<HTMLInputElement>; label: string } & ComponentProps<'input'>) {
  // `ref` is an ordinary prop in React 19; no forwardRef needed.
  return (
    <label>
      {label}
      <input ref={ref} {...rest} />
    </label>
  )
}

export function ChatRoom({ roomId, theme, connect }: {
  roomId: string
  theme: 'light' | 'dark'
  connect: (roomId: string, onConnected: () => void) => () => void
}) {
  // Reads the latest theme without making the connection depend on it.
  const onConnected = useEffectEvent(() => {
    console.debug(`connected to ${roomId} with the ${theme} theme`)
  })

  useEffect(() => {
    const disconnect = connect(roomId, () => onConnected())
    return disconnect
  }, [roomId, connect])               // onConnected is intentionally not a dependency

  return <h2>{roomId}</h2>
}
```

## 15. Common Mistakes

- Creating a Promise inside the component that calls `use(promise)`: it is new on every render and suspends repeatedly.
- Calling the `useOptimistic` setter outside an Action or Transition.
- Rendering `useFormStatus` in the same component that renders the `<form>`; it reads the parent form, so it must be in a child.
- Putting an Effect Event in a dependency array, passing it as a prop, or calling it during render.
- Using `useEffectEvent` to avoid honest dependencies, which hides stale-value bugs.
- Adding `useMemo`/`useCallback` to new code by habit; the compiler handles it. Conversely, deleting existing memoization in bulk without testing, which can change compiled output.
- Mutating state, props or refs during render; the compiler skips the component and the lint rules flag it.
- Using `useEffect` to fetch on mount without cleanup or race handling when Suspense or a data library would do.
- Relying on `Context.Provider` and `forwardRef` in new code; use `<Context value>` and `ref` as a prop.
- Passing `ref` through `element.ref` (deprecated); read `element.props.ref`.
- Trusting client-side validation: Actions and Server Functions need the same validation, authentication and authorization on the server.
- Marking a layout `'use client'` and pulling the whole tree, and server-only dependencies, into the bundle.
- Testing with shallow rendering or `react-test-renderer`.
- Using array index keys for lists that reorder or insert.
- Leaving `"use no memo"` in code as a permanent fix.

## 16. References

- [references/hooks-and-actions.md](references/hooks-and-actions.md): Actions, `useActionState`, `useOptimistic`, `useFormStatus`, `use`, Transitions, Effects and `useEffectEvent`, error handling options.
- [references/react-compiler.md](references/react-compiler.md): installation per build tool, options, directives, lint rules, adoption plan, what the compiler skips.
- [references/server-components-and-boundaries.md](references/server-components-and-boundaries.md): `'use client'` and `'use server'`, serialization, composition, Context across the boundary, `cache`, resource and metadata rendering, Activity and ViewTransition, security rules.
- Official docs: https://react.dev, React 19.3 release post https://react.dev/blog/2026/09/09/react-19-3, React Compiler 1.0 https://react.dev/blog/2025/10/07/react-compiler-1.
