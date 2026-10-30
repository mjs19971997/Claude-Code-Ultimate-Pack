# React Compiler

Verified against babel-plugin-react-compiler 1.0.0 (stable since the 1.0 release in October 2025), eslint-plugin-react-hooks 7.1.1, React 19.3.1, @vitejs/plugin-react 6.1.2 and Next.js 16.4.3 (2026-10).

## What it is

A build-time optimizer, implemented as a Babel plugin, that automatically memoizes React components and hooks so that only the parts of the UI that depend on changed values re-render. It works with React 19 without configuration and supports React 17 and 18 with a `target` setting and the `react-compiler-runtime` package.

Properties that matter:

- It memoizes components and hooks, not arbitrary functions. A heavy pure helper called from many components is not cached across components; give it its own memoization if profiling shows it matters.
- It relies on the Rules of React (pure render, no mutation of props or state, no reading refs during render). Code that breaks them is skipped, not failed, unless `panicThreshold` is changed.
- It handles conditional early returns, optional chains and array indexes as dependencies, and values after `use()` calls.
- Memoization is a performance optimization, not a semantic guarantee. Code that needs a value to stay referentially stable for correctness (for example an Effect that must not re-run) should be made explicit and verified.

## Installation

```bash
npm install -D --save-exact babel-plugin-react-compiler@latest
npm install -D eslint-plugin-react-hooks@latest
```

Pin the exact compiler version (`--save-exact`) because its output can change between releases.

The compiler must run first in the Babel plugin pipeline.

### Babel

```js
// babel.config.js
module.exports = {
  plugins: [
    'babel-plugin-react-compiler', // must be first
    // other plugins
  ],
}
```

### Vite (with @vitejs/plugin-react 6 or later)

```bash
npm install -D @rolldown/plugin-babel
```

```js
// vite.config.js
import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
  ],
})
```

On older `@vitejs/plugin-react` versions use `react({ babel: { plugins: ['babel-plugin-react-compiler'] } })`.

### Next.js 16

```ts
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactCompiler: true, // stable in 16; not enabled by default; increases compile time
}

export default nextConfig
```

Install `babel-plugin-react-compiler` as well. Opt-in mode: `reactCompiler: { compilationMode: 'annotation' }` and add `"use memo"` to chosen functions. Next.js runs the compiler only on files it detects as relevant (JSX or Hooks). An experimental Rust port exists behind `experimental.turbopackRustReactCompiler`.

### Other tools

Rspack, Rsbuild, Expo and React Native (Metro, via Babel) have their own integration docs; webpack uses a community loader. React Router needs `vite-plugin-babel` with the compiler plugin.

## Options

```js
['babel-plugin-react-compiler', {
  compilationMode: 'infer',   // 'infer' (default) | 'syntax' | 'annotation' | 'all'
  panicThreshold: 'none',     // 'none' (default, recommended) | 'critical_errors' | 'all_errors'
  target: '19',               // '17' | '18' | '19'; 17 and 18 also need react-compiler-runtime
}]
```

| Option | Use |
|---|---|
| `compilationMode: 'infer'` | Heuristics find components (PascalCase functions returning JSX) and hooks (`use` prefix). Default. |
| `compilationMode: 'annotation'` | Only functions with the `"use memo"` directive. Good for first rollout. |
| `compilationMode: 'syntax'` | Only Flow component and hook syntax. |
| `compilationMode: 'all'` | Every top-level function; not recommended. |
| `panicThreshold` | `'none'` skips components that cannot be compiled and keeps building. |
| `target` | React version to generate code for. |
| `gating` | Runtime feature flag, `{ source, importSpecifierName }`, for A/B tests and gradual rollouts. |
| `logger` | Receives compilation events such as `CompileSuccess` and skips, useful to measure coverage. |

## Directives

- `"use memo"` at the start of a function opts it in (in `annotation` mode).
- `"use no memo"` (alias `"use no forget"`) at the very start of a function body excludes it and takes precedence over every mode. Use it as a temporary debugging escape hatch with a comment explaining why, not as a permanent fix.

## ESLint

Flat config:

```js
// eslint.config.js
import reactHooks from 'eslint-plugin-react-hooks'
import { defineConfig } from 'eslint/config'

export default defineConfig([
  reactHooks.configs.flat.recommended,
])
```

- `recommended` enables the classic rules and the compiler-powered rules. `recommended-latest` also includes newer rules (for example `react-hooks/void-use-memo`).
- Legacy `.eslintrc`: `"extends": ["plugin:react-hooks/recommended"]`.
- The linter does not need the compiler installed. `eslint-plugin-react-compiler` is superseded by `eslint-plugin-react-hooks`.
- Rules in the 7.1.1 `recommended` preset: `rules-of-hooks`, `exhaustive-deps`, `static-components`, `use-memo`, `preserve-manual-memoization`, `incompatible-library`, `immutability`, `globals`, `refs`, `set-state-in-effect`, `error-boundaries`, `purity`, `set-state-in-render`, `unsupported-syntax`, `config`, `gating`.
- `exhaustive-deps` accepts `additionalHooks` (a regex) to check custom hooks with dependency arrays.
- A reported violation means the compiler skips that component; it is safe and can be fixed gradually.

What the main rules catch:

| Rule | Typical violation |
|---|---|
| `purity` | `Math.random()`, `Date.now()` or other impure calls during render |
| `immutability` | mutating props, state or values captured by hooks |
| `refs` | reading or writing `ref.current` during render |
| `set-state-in-effect` | calling `setState` synchronously in an Effect to derive state |
| `set-state-in-render` | unconditionally setting state during render (render loops) |
| `static-components` | defining a component inside another component |
| `preserve-manual-memoization` | existing manual memoization with incomplete dependencies, which prevents the compiler from understanding the data flow |
| `incompatible-library` | use of libraries that are incompatible with memoization, manual or automatic |
| `globals` | assigning or mutating globals during render |
| `error-boundaries` | `try/catch` used to catch errors from child components; only Error Boundaries can catch render errors |

## Adoption plan

1. Upgrade to React 19 (or choose `target` for 17/18).
2. Install `eslint-plugin-react-hooks` `recommended` and fix findings, starting with `purity`, `immutability`, `refs` and `set-state-in-effect`.
3. Install the compiler with `compilationMode: 'annotation'`, or use Babel `overrides` to enable it for one directory at a time, or use `gating` for a measured rollout.
4. Verify in React DevTools: compiled components show a "Memo" badge. Run the test suite and watch for behavior changes.
5. Widen coverage, then switch to the default `infer` mode for the whole app.
6. For new code rely on the compiler and use `useMemo`/`useCallback` only where precise control is needed, for example a memoized value used as an Effect dependency so the Effect does not fire repeatedly. For existing code, leave manual memoization in place (removing it can change compilation output) or test carefully before removing it. The compiler preserves existing manual memoization and compiles a component only if its inference matches or exceeds it.

## Debugging

- Compiler build errors are rare and usually a compiler bug: report with the error, the code, and React and compiler versions.
- Behavior changes are almost always a Rules of React violation the linter missed, or code that relied on memoization for correctness (Effects relying on referential equality, dependency arrays needing stable references, reference checks used as caches).
- Isolate with `"use no memo"` on the suspect component; if the bug disappears, find the impure or mutating code and fix it.
- Do not mutate objects after they are used in JSX or passed to hooks; copy and update instead.

## What not to expect

- No speedup for the initial render; the focus is update performance (re-renders).
- No effect on server-only rendering cost beyond bundle differences; Server Components do not need memoization.
- It does not fix slow lists, heavy computations or network latency.
