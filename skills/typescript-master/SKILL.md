---
name: typescript-master
description: >-
  Designs and reviews type-safe TypeScript 5.x to 7.x code and configuration: strict tsconfig, module and moduleResolution choices (nodenext, bundler), verbatimModuleSyntax, isolatedDeclarations, erasableSyntaxOnly, generics, conditional, mapped and template literal types, branded types, satisfies, using declarations, type-level tests (expectTypeOf, tsd), and runtime validation at boundaries with zod or valibot. Covers the TypeScript 6 deprecations and the native TypeScript 7 compiler. Use when writing or tightening tsconfig.json, modeling domain types, fixing complex type errors, migrating to TypeScript 7, publishing typed packages, or validating untrusted input. Not for React component typing patterns (use senior-react-19-engineer), Node.js runtime architecture (use nodejs-architect), or Tailwind class typing (use tailwindcss-master).
license: MIT
metadata:
  version: "3.0.0"
---

# TypeScript Master

This skill covers writing TypeScript that stays correct as it grows: compiler configuration, module settings for Node and bundlers, domain modeling with unions and branded types, type-level programming that remains readable, tests for types, and runtime validation where data enters the program. It also covers the 6.x to 7.x transition, where TypeScript 7 is the native (Go) compiler and several long-deprecated options were removed.

> Verified against TypeScript 7.0.2 (native compiler, npm `typescript` latest; 7.1 is in beta) and 6.0.3 (last JavaScript-based line), zod 4.6.7, valibot 1.5.0, vitest 5.0.5, expect-type 1.4.0, tsd 0.33.0, typescript-eslint 8.72.1, Node.js 22.22 (2026-10).

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

- Covered: `tsconfig.json` design and presets, module systems and resolution, strictness flags, project references, type modeling (unions, generics, conditional, mapped and template literal types), `satisfies`, `using`, type tests, runtime schema validation, typed package publishing, TypeScript 6 to 7 migration.
- Not covered: React component and hook typing (senior-react-19-engineer), Next.js specifics (nextjs-15-architect), Node.js process and stream architecture (nodejs-architect), lint pipeline and CI design (cicd-expert), Tailwind (tailwindcss-master).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | TypeScript 7.0 is the native compiler: `npm install -D typescript` installs it and `tsc` is the command. 6.0 was the last JavaScript-based release and deprecated the options 7.0 removed. Tools built on the old compiler API need 6.x (or `@typescript/typescript6`) until they support 7 |
| Strictness | `strict` defaults to `true` in 6.x and 7.x. Add `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch` |
| Modules | `module: nodenext` (or `node20`) for Node; `module: preserve` or `esnext` with `moduleResolution: bundler` for Vite, esbuild, webpack, Next.js. `node10` and `classic` resolution are removed in 7.0 |
| Per-file safety | `verbatimModuleSyntax` (imports and exports are emitted as written, `import type` required for types), `isolatedModules`, `isolatedDeclarations` (explicit types on exports so tools can emit `.d.ts` per file), `erasableSyntaxOnly` (no enums, namespaces with values, parameter properties; required for Node type stripping) |
| Defaults to know | `types` defaults to `[]` (add `"node"` or others explicitly; `"*"` restores auto-inclusion), `target` defaults to ES2025, `esModuleInterop` and `allowSyntheticDefaultImports` are always on, `noUncheckedSideEffectImports` is on |
| Type system | Generics with `extends` and defaults, `const` type parameters, `NoInfer`, conditional types with `infer X extends Y`, mapped types with `as` key remapping, template literal types, variadic tuples, `satisfies`, inferred type predicates |
| Resource management | `using` and `await using` with `Symbol.dispose` / `Symbol.asyncDispose` |
| Validation | zod 4 (`z.object`, `z.infer`, `safeParse`, `z.toJSONSchema`) and valibot 1 (`v.object`, `v.pipe`, `v.safeParse`, `v.InferOutput`) both implement the Standard Schema interface (`~standard`) |
| Type tests | `expectTypeOf` from vitest (expect-type), `vitest --typecheck` with `*.test-d.ts` files, `tsd` (checks with its own bundled TypeScript 5.9), `@ts-expect-error` |

## 3. Workflow

1. Check the toolchain: `tsc --version`, Node version, bundler, and whether linters (typescript-eslint) or codegen tools import the TypeScript API.
2. Pick the runtime target (Node service, bundled app, published library, monorepo) and start from the matching tsconfig preset in [references/tsconfig.md](references/tsconfig.md).
3. Turn on strictness at the start. For an existing loose codebase, enable flags one at a time and fix in slices; do not add `any` to silence errors.
4. Model the domain first: unions with a `kind` discriminant, branded identifiers, `readonly` data, `Result` types for expected failures.
5. Validate every boundary (HTTP bodies, env, files, queue messages, `JSON.parse`) with a schema, and derive the static type from the schema.
6. Add type-level utilities only when they remove repetition or encode an invariant; test them with `expectTypeOf`.
7. Run `tsc --noEmit` in CI next to the linter and tests; for libraries also run `publint` and `attw`.
8. When upgrading to 7.x: clear 6.x deprecation errors first (`ignoreDeprecations` only as a temporary bridge), then switch the compiler and check tool compatibility.

## 4. Decision Rules

- `unknown` over `any` at every boundary; narrow with a schema or a type guard. `any` only in generic internals with a comment, never in public signatures.
- Union of string literals (or an `as const` object plus `typeof X[keyof typeof X]`) instead of `enum`. Regular enums and `const enum` are incompatible with `erasableSyntaxOnly` and cause trouble with per-file transpilers.
- `interface` for object contracts that are extended or implemented; `type` for unions, tuples, mapped and conditional types. Choose one convention per codebase.
- Discriminated union (`{ kind: "a" } | { kind: "b" }`) instead of optional fields that are only valid together.
- `satisfies` to check a value against a type while keeping its literal type; annotation (`: T`) when you want the wider type; `as` only inside a validating constructor or after a runtime check.
- `module: nodenext` for code run by Node (including published packages), `bundler` when a bundler resolves imports. Do not use `bundler` for code Node will execute directly.
- Parameter properties and enums are fine in bundled applications; avoid them when the code must run through Node's type stripping or other erase-only tools.
- Result type or typed error classes for expected failures; `throw` for programmer errors. Catch variables are `unknown`.
- zod when you want the widest ecosystem and built-in JSON Schema output; valibot when bundle size matters (modular functions); either through Standard Schema so libraries accept both.
- Declaration files for dependencies without types go in a local `types/` folder with `declare module`; do not widen to `any` globally.
- Keep TypeScript 7 for `tsc`, builds and editors when your tooling supports it; pin `typescript@~6.0` (or add `@typescript/typescript6`) for tools that still need the JavaScript API.

## 5. Coding Standards

- Use `import type { X }` or inline `import { type X }` for type-only imports (required by `verbatimModuleSyntax`). Relative imports under `nodenext` include the file extension (`./util.js`, or `./util.ts` with `rewriteRelativeImportExtensions`).
- Annotate exported functions with explicit parameter and return types; let inference work inside bodies. This is mandatory under `isolatedDeclarations` and keeps public APIs stable.
- Prefer `readonly` properties and `readonly T[]` or `ReadonlyArray<T>` for inputs. Use `as const` for literal tables.
- Name types in PascalCase, type parameters `T`, `K`, `V` or descriptive (`TItem`). Do not prefix interfaces with `I`.
- No non-null assertions (`!`) outside tests; no `@ts-ignore` (use `@ts-expect-error` with a reason so it fails when the error disappears).
- Use `#private` fields for runtime privacy; `private` only affects the type system.
- Exhaustive `switch` with an `assertNever(x: never)` default.
- Keep generics shallow: at most two or three type parameters per function; name the intent in a type alias instead of nesting conditionals.
- Use `Array.prototype.at`, `Object.groupBy`, `structuredClone` and other ES2025 features only when the `lib` and runtime support them.

## 6. Project Structure

```
.
├── package.json                  # "type": "module"; exports map for libraries
├── tsconfig.base.json            # shared strict options (extended by packages)
├── tsconfig.json                 # solution file with "references" in monorepos
├── eslint.config.js
├── src/
│   ├── domain/                   # pure types, unions, branded ids, no IO
│   ├── boundary/                 # zod/valibot schemas for HTTP, env, queues
│   ├── services/
│   ├── env.ts                    # parses process.env once at startup
│   └── index.ts                  # public API (explicit exports)
├── test/
│   ├── unit/
│   └── types/                    # *.test-d.ts type tests
└── dist/                         # build output, gitignored
```

## 7. Design Patterns

- **Branded identifiers**: `type UserId = string & { readonly [brand]: "UserId" }` created only by a validating function, so a `UserId` cannot be passed where an `OrderId` is expected.
- **Discriminated unions and `assertNever`**: model states explicitly and let the compiler flag unhandled cases when a variant is added.
- **Schema as source of truth**: define a zod or valibot schema, export `type T = z.infer<typeof T>`, and parse at the boundary; internal code receives only parsed values.
- **Result type**: `{ ok: true; value } | { ok: false; error }` for operations whose failure is part of the domain.
- **Builder with accumulating generics**: each call widens a type parameter, and the terminal method requires the complete state through a `this:` parameter type.
- **Typed registries and event maps**: a map type drives `on<K extends keyof E>(event: K, handler: (payload: E[K]) => void)`.
- **Mapped and template literal types** for derived APIs: getters from a record, route params from a path string, prefixed keys.
- **Resource scopes**: `using handle = openHandle()` releases resources at scope exit, including on exceptions.
- More in [references/type-level-patterns.md](references/type-level-patterns.md) and [references/runtime-validation.md](references/runtime-validation.md).

## 8. Best Practices

- Derive types from values (`typeof`, `keyof typeof`, `ReturnType`, `z.infer`) instead of maintaining parallel declarations.
- Keep one source of truth for shared contracts (a schema or a types package) and generate the rest (OpenAPI, JSON Schema) from it.
- Avoid optional fields for state machines; encode states as union members.
- Use `Partial<T>`, `Pick`, `Omit`, `Required` sparingly; prefer named types that state intent (`UpdateUserInput`).
- Treat `tsconfig` as shared code: one strict base, small per-package overrides, and `${configDir}` in the base for paths.
- Use `ReadonlyMap`/`ReadonlySet` and `Object.freeze` plus `as const` for constants that must not change.
- Document non-obvious types with TSDoc and a usage example; link to tests.
- Keep generated code and `.d.ts` out of source folders; do not edit `node_modules/@types` by patching.

## 9. Performance

- Type-checking cost grows with type complexity: deep recursive conditional types, large unions (hundreds of members) crossed with mapped types, and intersections of many object types. If `tsc` reports "Type instantiation is excessively deep" or editor latency grows, simplify the type or use an interface plus `extends`.
- Use tail-recursive conditional types (accumulator parameter) for recursion over long tuples or strings.
- `skipLibCheck` avoids checking `.d.ts` files in dependencies. `incremental` and `composite` with `tsc -b` reuse work across runs in monorepos.
- TypeScript 7 checks projects in parallel: `--checkers` (default 4) sets checkers per project, `--builders` sets concurrent projects in `-b` mode, `--singleThreaded` disables parallelism (useful in constrained CI containers).
- `isolatedDeclarations` lets build tools produce declaration files per file without full type-checking; keep `tsc --noEmit` as the correctness gate.
- Split very large programs into project references so editors load only the relevant project.
- Inspect cost with `tsc --extendedDiagnostics` and `tsc --generateTrace <dir>`.

## 10. Security

- Types are erased at runtime. Data from HTTP, files, env, message queues, `localStorage` and `JSON.parse` is untrusted; validate with a schema before treating it as a typed value.
- `as T` on external data is a lie to the compiler; restrict assertions to validated constructors and review each one.
- Never send secrets to the browser through bundler-exposed environment variables (`NEXT_PUBLIC_*`, `VITE_*`, and similar); parse server env into a typed object on the server only.
- Index signatures (`Record<string, T>`) on user-controlled keys invite prototype pollution; use `Map`, `Object.create(null)` or schemas with `.strict()` and reject `__proto__`, `constructor` and `prototype` keys when merging objects.
- Normalize and validate file paths before use (`path.resolve` then check the prefix); a `string` type does not make a path safe.
- Validate regular expressions on user input for catastrophic backtracking and bound input lengths in schemas (`.max(n)`).
- Do not use `eval`, `new Function` or dynamic `import()` with user-controlled specifiers.
- Lock dependencies (lockfile, `npm ci`), review `@types/*` and postinstall scripts, and keep `typescript` and validation libraries updated.
- Treat `any`, `@ts-ignore` and `@ts-nocheck` as security-relevant when they sit on a boundary; ban them with lint rules (`@typescript-eslint/no-explicit-any`, `ban-ts-comment`).

## 11. Testing

- Test types as code: `expectTypeOf<T>().toEqualTypeOf<U>()` in `*.test-d.ts` files, executed with `vitest --typecheck` (config: `test.typecheck.enabled`, `include: ["**/*.test-d.ts"]`).
- Test that invalid usage fails with `// @ts-expect-error`; the build breaks if the line stops being an error.
- `tsd` (`expectType`, `expectError`) works for libraries but checks with its own TypeScript version (5.9 in tsd 0.33), so results can differ from your compiler.
- A small `Equal<X, Y>` helper plus `Expect<...>` aliases gives dependency-free compile-time assertions; see the reference.
- Runtime tests cover schemas: valid input passes, each invalid class (missing, wrong type, out of range, extra keys) is rejected with a useful message.
- Run `tsc --noEmit` for the whole repo including tests, so test files are type-checked too.
- Check packaging with `npx publint` and `npx attw --pack .` before publishing a library.

## 12. Review Checklist

- [ ] `strict` plus `noUncheckedIndexedAccess`; any weakening is justified in the config.
- [ ] `module` and `moduleResolution` match how the code runs (Node vs bundler); no removed options (`baseUrl`, `outFile`, `node10`, `target: es5`, `downlevelIteration`, `esModuleInterop: false`).
- [ ] `types` lists what is needed (for example `"node"`) since it defaults to empty.
- [ ] No `any`, `as unknown as`, `!` or `@ts-ignore` without a comment; external data passes through a schema.
- [ ] Exported functions have explicit types; unions use a discriminant and exhaustive handling.
- [ ] Type-only imports use `import type`; relative imports have correct extensions.
- [ ] Enums, namespaces and parameter properties absent where `erasableSyntaxOnly` is on.
- [ ] Type utilities are tested and named by intent; no deeply nested conditionals.
- [ ] Library: `exports` map has `types` conditions first, `publint` and `attw` pass.
- [ ] CI runs `tsc --noEmit` (or `tsc -b`), lint, tests.

## 13. Production Notes

- TypeScript 7 ships as the `typescript` npm package with per-platform native binaries; Node `>=16.20` is the declared engine for the launcher. The old programmatic API is not the package entry point: the main export exposes version information and the new API lives under `typescript/unstable/*` entry points, which are marked unstable. Tools that `import ts from "typescript"` (typescript-eslint 8.72.1 declares the peer range `typescript >=4.8.4 <6.1.0`; check each build plugin and codegen tool) need TypeScript 6.x until they support 7. `@typescript/typescript6` provides a `tsc6` command and the TypeScript 6 API.
- A pragmatic setup: `tsc` 7 for `tsc --noEmit`, `tsc -b` and editors; TypeScript 6 for tools that require the old API; check each tool's release notes.
- Option removals in 7.0 (deprecated in 6.0): `baseUrl` (use `paths` with relative targets), `outFile`, `target: es5`, `module: amd | umd | system`, `moduleResolution: node10 | classic`, `esModuleInterop: false`, `allowSyntheticDefaultImports: false`, `alwaysStrict: false`, `downlevelIteration`. In 6.x `"ignoreDeprecations": "6.0"` silences the errors temporarily.
- Running TypeScript directly in Node: Recent Node releases (22.22 was tested) strip types by default for `.ts` files (no enums, namespaces with values, parameter properties, or other syntax needing transformation). Combine `erasableSyntaxOnly`, `verbatimModuleSyntax` and `rewriteRelativeImportExtensions` so the same `./file.ts` imports work under Node and in the compiled output.
- Builds: `tsc` can emit directly for Node services; bundle with tsdown, tsup, esbuild or the framework's build when you need a single file; generate declarations with `tsc --emitDeclarationOnly` or the bundler's dts plugin.
- Publishing: `"type": "module"`, an `exports` map with `types` first in each condition block, `files` allowlist, `sideEffects` when tree-shaking matters, provenance on publish.
- Source maps and `declarationMap` help consumers debug; do not ship `.ts` sources unless intended.
- Details: [references/tsconfig.md](references/tsconfig.md).

## 14. Examples

Branded identifiers, a `Result` type and an exhaustive switch (compiled with TypeScript 6.0.3 and 7.0.2 under the strict settings above):

```ts
declare const brand: unique symbol;
export type Brand<T, B extends string> = T & { readonly [brand]: B };
export type UserId = Brand<string, "UserId">;
export type OrderId = Brand<string, "OrderId">;

export function parseUserId(raw: string): UserId {
  if (!/^usr_[a-z0-9]{8,}$/.test(raw)) throw new RangeError("invalid user id");
  return raw as UserId; // the single cast, behind a validating constructor
}

export type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };

export type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rect"; width: number; height: number };

export function assertNever(value: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(value)}`);
}

export function area(s: Shape): number {
  switch (s.kind) {
    case "circle":
      return Math.PI * s.radius ** 2;
    case "rect":
      return s.width * s.height;
    default:
      return assertNever(s); // a new variant becomes a compile error here
  }
}
```

Validation at the boundary with zod 4, deriving the type from the schema and parsing environment variables once:

```ts
import { z } from "zod";

export const CreateUser = z.object({
  email: z.email(),
  age: z.int().min(13).max(130),
  role: z.enum(["admin", "member"]).default("member"),
});
export type CreateUser = z.infer<typeof CreateUser>;

export function parseBody(input: unknown): CreateUser {
  const result = CreateUser.safeParse(input);
  if (!result.success) throw new TypeError(z.prettifyError(result.error));
  return result.data;
}

const Env = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DATABASE_URL: z.url(),
});
export const env = Env.parse(process.env); // fails fast at startup with all problems listed
```

Type-level helpers with compile-time tests (`vitest --typecheck` runs the `*.test-d.ts` file):

```ts
// route-params.ts
export type RouteParams<Path extends string> =
  Path extends `${string}:${infer Param}/${infer Rest}`
    ? { [K in Param | keyof RouteParams<`/${Rest}`>]: string }
    : Path extends `${string}:${infer Param}`
      ? { [K in Param]: string }
      : {};

// route-params.test-d.ts
import { expectTypeOf, test } from "vitest";
import type { RouteParams } from "./route-params.js";

test("params are derived from the path", () => {
  expectTypeOf<RouteParams<"/users/:id/posts/:postId">>()
    .toEqualTypeOf<{ id: string; postId: string }>();
  expectTypeOf<RouteParams<"/health">>().toEqualTypeOf<{}>();
});
```

## 15. Common Mistakes

- **Leaving removed options in tsconfig** (`baseUrl`, `moduleResolution: node`, `target: es5`, `esModuleInterop: false`): TypeScript 6 reports them as deprecated and 7 as removed. Replace `baseUrl` with `paths` entries relative to the tsconfig and use `nodenext` or `bundler`.
- **Expecting `@types/*` to load automatically**: `types` defaults to `[]` in 6.x and 7.x, so globals such as `process` or `describe` vanish. Add `"types": ["node"]` (and test runner types) explicitly.
- **`module: nodenext` without `"type": "module"` in package.json** while writing `import`/`export` under `verbatimModuleSyntax`: files are treated as CommonJS and report TS1295 and TS1287. Set `"type": "module"` or use `.mts`.
- **Relative imports without extensions under `nodenext`**: Node ESM needs `./file.js` (or `./file.ts` with `rewriteRelativeImportExtensions`).
- **Parameter properties (`constructor(private x: string)`) or enums with `erasableSyntaxOnly`**: rejected (TS1294). Declare fields explicitly and use literal unions.
- **`as` on parsed JSON or request bodies**: compiles, then fails in production. Parse with a schema.
- **`enum` for string options**: emits runtime code and breaks type stripping; use a literal union.
- **Optional fields for mutually exclusive data**: allows impossible states; use a discriminated union.
- **`interface` merging across packages** and global augmentations scattered in the code: surprising behavior; keep augmentations in one `types/` file.
- **Fighting variance with `any`**: reach for `unknown`, a generic constraint, or `NoInfer` instead.
- **Huge recursive conditional types**: slow builds and TS2589; simplify or use accumulator-style recursion.
- **Assuming the TypeScript API is available in 7**: scripts and plugins that call `ts.createProgram` need TypeScript 6 or the new unstable API.
- **Leaving `@ts-expect-error` without a reason** or using `@ts-ignore`: hides regressions.
- **Publishing with `types` after `default` in `exports`**: consumers get no types. Put `types` first and verify with `attw`.

## 16. References

- [references/tsconfig.md](references/tsconfig.md): option-by-option guidance, presets for Node services, bundled apps, libraries and monorepos, module and resolution matrix, TypeScript 6 to 7 migration, type stripping setup, tooling compatibility.
- [references/type-level-patterns.md](references/type-level-patterns.md): branded types, conditional and mapped types, template literal parsing, variadic tuples, builders, event maps, `satisfies`, `using`, and how to test and keep type-level code fast.
- [references/runtime-validation.md](references/runtime-validation.md): zod 4 and valibot 1 at HTTP, env, JSON and queue boundaries, Standard Schema, error handling, JSON Schema output, and security-oriented schema options.
- Official docs: https://www.typescriptlang.org/docs/ , https://www.typescriptlang.org/tsconfig/ , https://github.com/microsoft/TypeScript , https://zod.dev , https://valibot.dev , https://vitest.dev/guide/testing-types
