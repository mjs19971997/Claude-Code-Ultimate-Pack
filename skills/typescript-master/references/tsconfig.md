# tsconfig and Compiler Setup

Reference for `tsconfig.json` design, module settings, strictness flags, the TypeScript 6 to 7 transition and running TypeScript in Node. Verified against TypeScript 7.0.2 (native compiler) and 6.0.3, source of the 6.0.3 compiler and the TypeScript 7 port, and Node.js 22.22 (2026-10). The presets below were compiled with both 6.0.3 and 7.0.2. Option names and defaults come from the compiler source; check the TSConfig reference for prose descriptions.

## 1. Presets

Node service or CLI (ESM, compiled with `tsc`):

```json
{
  "compilerOptions": {
    "rootDir": "./src",
    "outDir": "./dist",
    "module": "nodenext",
    "target": "es2025",
    "lib": ["es2025"],
    "types": ["node"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "erasableSyntaxOnly": true,
    "noUncheckedSideEffectImports": true,
    "moduleDetection": "force",
    "skipLibCheck": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src"]
}
```

- Requires `"type": "module"` in `package.json` (otherwise `.ts` files are CommonJS and `import`/`export` fail under `verbatimModuleSyntax`).
- `@types/node` must be installed for `"types": ["node"]`.
- Drop `erasableSyntaxOnly` if you use enums or parameter properties and run only compiled output.

Bundled application (Vite, esbuild, webpack, Next.js):

```json
{
  "compilerOptions": {
    "target": "es2025",
    "lib": ["es2025", "dom", "dom.iterable"],
    "module": "preserve",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "types": [],
    "noEmit": true,
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "allowImportingTsExtensions": true,
    "moduleDetection": "force",
    "skipLibCheck": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- The bundler transpiles; `tsc` only type-checks (`noEmit`). Add environment types you need to `types` (for example the bundler's client types).
- `paths` targets are relative to the tsconfig, so `baseUrl` is not needed (and is removed in 7.0). The bundler must also know the alias.
- Frameworks such as Next.js generate or manage parts of this file; follow the framework's template and keep its required plugins.

Published library (Node and bundler consumers):

```json
{
  "compilerOptions": {
    "rootDir": "./src",
    "outDir": "./dist",
    "module": "nodenext",
    "target": "es2022",
    "types": [],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "isolatedDeclarations": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

```json
{
  "name": "@example/lib",
  "type": "module",
  "exports": {
    ".": { "types": "./dist/index.d.ts", "default": "./dist/index.js" }
  },
  "files": ["dist"]
}
```

- Pick `target` from the oldest runtime you support, not from your own machine.
- `isolatedDeclarations` requires explicit types on every export; it needs `declaration` (or `composite`) and cannot be combined with `allowJs`.
- Verify the package: `npx publint` and `npx attw --pack .`.

Monorepo with project references:

```json
{
  "compilerOptions": {
    "target": "es2025",
    "module": "nodenext",
    "types": [],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "skipLibCheck": true,
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "rootDir": "${configDir}/src",
    "outDir": "${configDir}/dist"
  }
}
```

- Save as `tsconfig.base.json`. Each package has `{ "extends": "../../tsconfig.base.json", "include": ["src"], "references": [{ "path": "../core" }] }`; the root `tsconfig.json` is `{ "files": [], "references": [ ... ] }` and `tsc -b` builds in dependency order.
- `${configDir}` resolves to the directory of the tsconfig that is being built, so paths in a shared base apply per package.
- Workspace packages are resolved through `node_modules` links and their `exports` map, which should point `types` at built `dist` output.

## 2. The `tsc --init` template in TypeScript 7

The generated file is a good baseline. It enables: `module: nodenext`, `target: esnext`, `types: []` (with a commented `["node"]` hint), `sourceMap`, `declaration`, `declarationMap`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `strict`, `jsx: react-jsx`, `verbatimModuleSyntax`, `isolatedModules`, `noUncheckedSideEffectImports`, `moduleDetection: force`, `skipLibCheck`, and comments out optional style flags (`noImplicitReturns`, `noImplicitOverride`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noPropertyAccessFromIndexSignature`) plus `rootDir` and `outDir`.

## 3. Strictness options

| Option | Effect and guidance |
|---|---|
| `strict` | Enables the strict family (`strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `useUnknownInCatchVariables`, `alwaysStrict`). Default `true` in 6.x and 7.x; write it explicitly anyway |
| `noUncheckedIndexedAccess` | `arr[i]` and index-signature reads include `undefined`; forces handling of missing elements. Pair with `for...of` or `.at()` + checks |
| `exactOptionalPropertyTypes` | `{ a?: string }` no longer accepts an explicit `undefined`; write `a?: string | undefined` if you mean that. Can surface errors in third-party types |
| `noImplicitOverride` | Requires the `override` keyword on overriding members |
| `noPropertyAccessFromIndexSignature` | Forces `obj["key"]` for index-signature properties; reduces typos |
| `noFallthroughCasesInSwitch`, `noImplicitReturns` | Catch missing `break`/`return` paths |
| `noUnusedLocals`, `noUnusedParameters` | Useful in CI; many teams enforce through lint instead |
| `useUnknownInCatchVariables` | Part of `strict`; `catch (e)` gives `unknown` |

## 4. Module settings

| Setting | Use for | Notes |
|---|---|---|
| `module: nodenext` | Code executed by Node (apps, tools, published libraries) | Follows Node's ESM/CJS rules, `exports` maps, `.js` extensions on relative imports. File format comes from the nearest `package.json` `"type"` and from `.mts`/`.cts` |
| `module: node20` / `node18` / `node16` | Pin Node's semantics instead of following the latest | `nodenext` floats; the pinned values give stable behavior across compiler upgrades |
| `module: preserve` | Bundler or runtime handles modules; TypeScript leaves import/export syntax as written | Use with `moduleResolution: bundler` |
| `module: esnext` / `es2022` | ESM output for a bundler | `bundler` resolution applies when `moduleResolution` is omitted and module is not a Node mode |
| `moduleResolution: bundler` | Imports resolved by Vite, esbuild, webpack, Next.js | Extensionless relative imports allowed; supports `exports`/`imports` maps; not valid for code Node runs unbundled |
| `moduleResolution: nodenext` / `node16` | Matches Node | Defaulted from `module`: `nodenext` for `module: nodenext`, `node16` for `node16`/`node18`/`node20`, otherwise `bundler` |
| `module: commonjs` | CJS output for legacy consumers | Prefer ESM; if dual-publishing, build both formats with a bundler and verify with `attw` |
| `moduleDetection: force` | Treat every non-declaration file as a module | Avoids accidental global scripts |
| `rewriteRelativeImportExtensions` | Write `./x.ts` in source, emit `./x.js` | Makes the same import work for Node type stripping and compiled output |
| `allowImportingTsExtensions` | Allow `.ts` import specifiers when not emitting | For bundler apps with `noEmit` |
| `verbatimModuleSyntax` | Imports/exports without `type` are emitted unchanged | Replaces `importsNotUsedAsValues` and `preserveValueImports`; use `import type` for types |
| `isolatedModules` | Flags constructs that cannot be transpiled per file | Implied by `verbatimModuleSyntax` for checking purposes |
| `esModuleInterop` | Always on in 6.x/7.x (turning it off is deprecated/removed) | Do not set to `false` |

## 5. Emit and environment options

- `target` defaults to ES2025 in 6.x and 7.x; `module` defaults from `target` when omitted (ESNext for `esnext`, ES2022 for targets from ES2022, and so on). Set both explicitly.
- `lib` defaults to the target's libraries; add `dom` and `dom.iterable` only for browser code. Newer proposals have separate `esnext.*` libs (for example `esnext.temporal`, `esnext.disposable`); include them only when your runtime supports the feature.
- `types` defaults to an empty list; list ambient packages explicitly (`"node"`, test-runner types). `"types": ["*"]` restores automatic inclusion of every `@types` package.
- `skipLibCheck: true` skips checking `.d.ts` files; keep it on for speed and turn it off occasionally in a CI job when you want to validate your own declaration output.
- `declaration`, `declarationMap`, `sourceMap` for libraries; `inlineSources` when publishing maps.
- `noEmit` for type-check-only setups; `noEmitOnError` for compiled services; `noCheck` skips type checking in emit-only steps.
- `erasableSyntaxOnly` rejects enums, namespaces containing values, parameter properties and other syntax that needs a transform.
- `isolatedDeclarations` makes the compiler require annotations that let other tools generate declarations without type inference. Error codes and exact locations can differ between 6.x and 7.x.
- `libReplacement` is off by default; leave it off unless you intentionally replace `lib.*.d.ts` files.

## 6. TypeScript 6 to 7 migration

TypeScript 6.0 was the last JavaScript-based release and marks a set of options as deprecated; TypeScript 7.0 removes them. Diagnostics point at the option in `tsconfig.json`.

| Removed in 7.0 | Replace with |
|---|---|
| `baseUrl` | `paths` with explicit relative targets, for example `"paths": { "*": ["./src/*"] }` |
| `outFile` | A bundler, or per-file output with `outDir` |
| `target: es5` | `es2015` or later; transpile further with a bundler if ES5 output is required |
| `module: amd`, `umd`, `system` | `esnext`, `preserve` or `nodenext` plus a bundler for legacy formats |
| `moduleResolution: node10` (alias `node`), `classic` | `nodenext` or `bundler` |
| `esModuleInterop: false`, `allowSyntheticDefaultImports: false` | Remove (always enabled) |
| `alwaysStrict: false` | Remove |
| `downlevelIteration` | Remove; use a modern `target` |

Steps:

1. Upgrade to 6.0.x first, run `tsc`, and fix every deprecation error. `"ignoreDeprecations": "6.0"` silences them temporarily; remove it before moving to 7.
2. Add `"types": [...]` for ambient packages if globals disappeared (the default is empty).
3. Install `typescript@7` and run `tsc --noEmit`; type-check results match 6.0 in nearly all cases. Error messages can print types differently, and conflicting declarations are now reported at every contributing site, so errors previously hidden by `skipLibCheck` can appear in non-`.d.ts` files.
4. JavaScript checking (`allowJs`/`checkJs`) is stricter and drops several Closure-era JSDoc features and constructor-function expandos; convert to classes and ES modules.
5. Check tools that import the TypeScript API. In 7.0 the package's main entry exposes version information only and the API lives in `typescript/unstable/*` entry points that are explicitly unstable. typescript-eslint 8.72.1 declares a peer range of `typescript >=4.8.4 <6.1.0`. `@typescript/typescript6` provides a `tsc6` command and the TypeScript 6 API for such tools.
6. Tune CI for parallelism: `--checkers <n>` (default 4), `--builders <n>` with `tsc -b` (default 4), `--singleThreaded` to disable.
7. Editors: check your editor's documentation for how it selects the TypeScript 7 language service and which workspace version it uses.

Positions in the 7.x API use UTF-8 offsets rather than UTF-16 offsets, which matters only to tools that consume node positions.

## 7. Running TypeScript directly in Node

- Node releases with type stripping enabled (22.22 was tested) run `node file.ts`. Stripping removes type syntax only; enums, namespaces with values and parameter properties fail. `erasableSyntaxOnly` makes the compiler flag them.
- Imports must name the real file: `import { x } from "./x.ts"`. With `rewriteRelativeImportExtensions: true`, `tsc` emits `./x.js` in compiled output, so the same source runs both ways (tested with 7.0.2).
- Use `verbatimModuleSyntax` so type-only imports are explicit (`import type`), because stripping cannot know whether an import is a type.
- Node does not read `tsconfig.json`: `paths` aliases do not apply at runtime. Use subpath imports (`"imports": { "#lib/*": "./src/lib/*.ts" }` in `package.json`, then `import { x } from "#lib/util"`) for aliases that work in both Node and TypeScript when running sources directly; for compiled output, point the map at `dist` (for example through conditions).
- Type stripping does not type-check; keep `tsc --noEmit` in CI.
- Do not rely on type stripping for files inside `node_modules`.

## 8. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| TS1295 / TS1287 under `verbatimModuleSyntax` | File is CommonJS: add `"type": "module"` or use `.mts`, or change `module` |
| TS1294 with `erasableSyntaxOnly` | Enum, namespace with values or parameter property; rewrite as literal union, plain object, explicit field assignment |
| TS2688 Cannot find type definition file | A name in `types` is not installed |
| `process`, `describe`, `Buffer` not found | `types` is empty by default: add `"node"` or the test runner's types |
| Relative import not found under `nodenext` | Add the extension (`.js`, or `.ts` with `rewriteRelativeImportExtensions`) |
| TS2589 excessively deep instantiation | Simplify the type; use accumulator-style recursion; split into aliases |
| `isolatedDeclarations` errors on exports | Add explicit parameter and return types and annotate exported constants that are not simple literals |
| Slow `tsc` | `skipLibCheck`, project references, `--extendedDiagnostics`, `--generateTrace <dir>`, `--listFilesOnly` to find stray includes |
| Editor and CLI disagree | Different TypeScript versions or tsconfig selected; run `tsc --showConfig` and check the workspace version |
