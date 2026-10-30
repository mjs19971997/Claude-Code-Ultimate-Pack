# Hooks and Actions in React 19

Verified against React 19.3.1 and @types/react 19.3.0 (2026-10).

## Actions and Transitions

An Action is an async function run inside a Transition. React tracks the pending state, keeps the UI responsive, handles errors through the nearest error boundary, and can show optimistic state while it runs.

- `startTransition(async () => { ... })` or the `[isPending, startTransition] = useTransition()` pair runs an Action imperatively.
- `<form action={fn}>` runs `fn(formData)` as an Action on submit; uncontrolled fields reset after success. `requestFormReset` from `react-dom` resets a form manually.
- A component can expose an Action prop (`action`, `onSubmitAction`) and call it inside `startTransition`, so callers get pending behavior without extra code.
- State updates after an `await` inside an Action are not automatically part of the Transition; wrap them in another `startTransition`.
- Multiple `dispatchAction` calls from `useActionState` are queued and run sequentially, each receiving the previous result.

## useActionState

```tsx
const [state, dispatchAction, isPending] = useActionState(reducerAction, initialState, permalink?)
```

- `reducerAction(previousState, payload)` can be sync or async and can perform side effects; it is not double-invoked in StrictMode.
- The returned state type must match `initialState`; annotate it explicitly when inference narrows (`{ status: 'idle' } as State`).
- Pass `dispatchAction` to `<form action>` or call it inside `startTransition`; calling it outside a Transition logs an error in development.
- If `dispatchAction` throws, queued actions are cancelled and the nearest error boundary renders. Return error state for expected failures.
- `permalink` is for server-rendered forms with a Server Function: before the bundle loads, the browser navigates to that URL.
- With Server Functions, `initialState` and the payload must be serializable.

## useOptimistic

```tsx
const [optimistic, setOptimistic] = useOptimistic(value, reducer?)
```

- `value` is returned whenever no Action is pending. During an Action it is the optimistic value (the argument passed to `setOptimistic`, or the reducer's result).
- The reducer `(current, action) => next` must be pure.
- Call `setOptimistic` inside an Action or Transition; outside, React warns and the value flashes briefly.
- The optimistic and real state converge in one render when the Transition ends; there is no separate "clear" step. If the Action fails, the UI returns to `value`.

## useFormStatus

```tsx
import { useFormStatus } from 'react-dom'
const { pending, data, method, action } = useFormStatus()
```

Reads the status of the nearest parent `<form>`. It must be called from a component rendered inside that form, not from the component that renders the `<form>`. Useful for design-system submit buttons.

## use

- `use(promise)`: suspends until the promise resolves; a rejected promise goes to the nearest error boundary. It cannot be called in `try/catch`.
- The promise must be stable across renders: create it in a Server Component and pass it down, in a cache, in a loader, or in memoized state owned above the Suspense boundary. A promise created during the consuming component's render is new on every render.
- Promises passed from Server to Client Components must resolve to serializable values.
- `use(Context)` reads Context like `useContext` but may be called conditionally or in loops; it is not supported in Server Components for reading context.
- 19.3 warns when `use` is misused in a conditional position.
- `use(browser())` (from `react-dom`, 19.3) opts a component out of server rendering: during SSR the nearest Suspense fallback is rendered, and on the client the component renders without suspending.

```tsx
import { Suspense, use } from 'react'

function Comments({ commentsPromise }: { commentsPromise: Promise<{ id: string; text: string }[]> }) {
  const comments = use(commentsPromise)
  return <ul>{comments.map((c) => <li key={c.id}>{c.text}</li>)}</ul>
}

export function Post({ commentsPromise }: { commentsPromise: Promise<{ id: string; text: string }[]> }) {
  return (
    <Suspense fallback={<p>Loading comments...</p>}>
      <Comments commentsPromise={commentsPromise} />
    </Suspense>
  )
}
```

## useDeferredValue and useTransition

- `useDeferredValue(value, initialValue?)`: React renders with the old value first and re-renders with the new one in the background; `initialValue` is used for the first render so the first paint can skip the expensive part.
- `useTransition` marks updates as non-urgent; updates that suspend keep showing the previous UI.
- 19.3 renders independent Transitions separately instead of entangling them, so a slow Transition no longer holds up unrelated ones.

## Effects

Effects synchronize a component with something outside React (network connection, DOM API, third-party widget, subscription). Avoid them for:

- Derived data: compute in render.
- Resetting state when a prop changes: use a `key`.
- Responding to user events: use event handlers.
- Subscribing to stores: use `useSyncExternalStore`.
- Initializing app-wide singletons: do it at module level or in the entry file.

Rules: return a cleanup that fully reverses the setup (StrictMode runs setup, cleanup, setup in development to prove it); list every reactive value used inside; handle races in fetch Effects with an abort signal or an ignore flag.

### useEffectEvent

```tsx
const onEvent = useEffectEvent(callback)
```

- Stable in React 19.2 and later (exported from `react`).
- The returned function always sees the latest committed props and state, is not a dependency, and has intentionally unstable identity.
- Call it only from inside Effects (`useEffect`, `useLayoutEffect`, `useInsertionEffect`) or other Effect Events of the same component; do not pass it down or call it during render. The lint plugin enforces this.
- Use it for logic that is conceptually an event fired from an Effect (analytics, notifications) and not to hide dependencies that should retrigger the Effect.
- 19.3 fixes `useEffectEvent` reading stale values in `forwardRef` and `memo` components.

## Refs

- `ref` is a regular prop on function components: `function Input({ ref, ...props }) { return <input ref={ref} {...props} /> }`.
- Ref callbacks may return a cleanup function; React then skips calling the callback with `null` on unmount. Do not return anything else from a ref callback (use a block body for assignments).
- Read `element.props.ref`, not `element.ref` (deprecated).
- Fragment refs (19.3): `<Fragment ref={fragmentRef}>` yields a `FragmentInstance` with `addEventListener`, `removeEventListener`, `dispatchEvent`, `focus`, `focusLast`, `blur`, `observeUsing`, `unobserveUsing`, `getClientRects`, `getRootNode`, `compareDocumentPosition` and `scrollIntoView` over the first-level children.

## Context

```tsx
const ThemeContext = createContext<'light' | 'dark'>('light')

function Page({ children }: { children: React.ReactNode }) {
  return <ThemeContext value="dark">{children}</ThemeContext>
}
```

`<Context>` replaces `<Context.Provider>`; the old form works and will be deprecated.

## Document metadata, stylesheets and resources

- `<title>`, `<meta>` and `<link>` rendered anywhere are placed in `<head>`. Render a single `<title>` at a time; React does not dedupe titles. A `<title>` inside `<svg>` or with `itemProp` is left in place.
- `<link rel="stylesheet" href="..." precedence="default">` is hoisted, deduplicated, ordered by `precedence`, and suspends the component until the sheet loads. A stylesheet without `precedence` gets no special handling.
- `<script async src="...">` rendered in components is deduplicated.
- `preload`, `preloadModule`, `preinit`, `preinitModule`, `preconnect` and `prefetchDNS` from `react-dom` hint the browser early; call them in render or event handlers.
- Frameworks usually provide a route-level metadata API; use native tags for component-local needs.

## Error handling

```tsx
import { createRoot } from 'react-dom/client'

createRoot(document.getElementById('root')!, {
  onCaughtError: (error, info) => reportError(error, { componentStack: info.componentStack }),
  onUncaughtError: (error, info) => reportError(error, { componentStack: info.componentStack }),
  onRecoverableError: (error) => reportError(error),
}).render(<App />)

declare function reportError(error: unknown, context?: Record<string, unknown>): void
```

- Errors thrown during render are no longer re-thrown: uncaught errors go to `window.reportError`, caught ones to `console.error`. The root options above give a single place to forward them.
- Error boundaries are still class components (`getDerivedStateFromError`, `componentDidCatch`) or come from a library.
- Hydration mismatches produce a single diff-style message; fix them by making server and client output equal, or use `use(browser())` for browser-only UI.

## React 18 to 19 migration notes

- Removed: `propTypes` and `defaultProps` on function components, `contextTypes`/`getChildContext`, string refs, module-pattern factory components, `React.createFactory`, `ReactDOM.render`, `ReactDOM.hydrate`, `unmountComponentAtNode`, `findDOMNode`, `react-dom/test-utils` (import `act` from `react`), `react-test-renderer/shallow`. UMD builds are gone.
- TypeScript: the global `JSX` namespace is removed (use `React.JSX`), `useRef` needs an initial argument, `ReactElement['props']` defaults to `unknown`, ref callbacks cannot implicitly return values, `useReducer` infers from the reducer.
- Run the official codemods from the React 19 upgrade guide, then upgrade `@types/react` and `@types/react-dom`.
