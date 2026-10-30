# Type-Level Patterns

Reference for modeling domains and building reusable type utilities in TypeScript, plus how to test them and keep them fast. Verified against TypeScript 7.0.2 and 6.0.3, vitest 5.0.5 and expect-type 1.4.0 (2026-10). Every snippet compiled under `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` and `erasableSyntaxOnly` with both compilers (except where marked as a fragment).

## 1. Domain modeling

```ts
// Branded (nominal) identifiers
declare const brand: unique symbol;
export type Brand<T, B extends string> = T & { readonly [brand]: B };
export type UserId = Brand<string, "UserId">;

export function parseUserId(raw: string): UserId {
  if (!/^usr_[a-z0-9]{8,}$/.test(raw)) throw new RangeError("invalid user id");
  return raw as UserId;
}

// Discriminated unions model states; optional fields do not
export type Payment =
  | { status: "pending" }
  | { status: "paid"; paidAt: Date; receiptId: string }
  | { status: "failed"; reason: string };

export function describe(p: Payment): string {
  switch (p.status) {
    case "pending": return "waiting";
    case "paid": return `paid ${p.paidAt.toISOString()}`;
    case "failed": return p.reason;
  }
}
```

- A branded type is erased at runtime; the only cast is inside the validating constructor. Parse once at the boundary and pass the brand inward.
- With a `switch` over every `status` and a declared return type, TypeScript reports missing cases; add `default: return assertNever(p)` when you want a runtime guard as well.
- `Result<T, E>` as `{ ok: true; value: T } | { ok: false; error: E }` keeps expected failures in the type.
- Use `readonly` fields and `ReadonlyArray` for data that should not be mutated; `as const` preserves literal types of tables.

## 2. satisfies, const type parameters, NoInfer

```ts
type Route = { path: `/${string}`; auth: boolean };

export const routes = {
  home: { path: "/", auth: false },
  account: { path: "/account", auth: true },
} as const satisfies Record<string, Route>;

export type RouteName = keyof typeof routes; // "home" | "account"

export function tuple<const T extends readonly unknown[]>(...items: T): T {
  return items;
}
// tuple(1, "a") has type readonly [1, "a"]

export function pick<T extends string>(options: readonly T[], fallback: NoInfer<T>): T {
  return options[0] ?? fallback;
}
// pick(["a", "b"], "c") is an error: "c" does not widen T
```

- `satisfies` validates the shape and keeps the narrow inferred type; a plain annotation would widen `path` to the template literal type.
- `const` type parameters infer literal tuples and readonly objects without `as const` at call sites.
- `NoInfer<T>` stops a position from contributing to inference, so one argument defines `T` and others are checked against it.

## 3. Conditional types and infer

```ts
export type First<T extends readonly unknown[]> = T extends readonly [infer H, ...unknown[]] ? H : never;
export type ParseInt<S extends string> = S extends `${infer N extends number}` ? N : never; // "42" -> 42

export type UnionToIntersection<U> =
  (U extends unknown ? (k: U) => void : never) extends (k: infer I) => void ? I : never;

export function parse<T extends "json" | "text">(
  kind: T,
  raw: string,
): T extends "json" ? unknown : string {
  return (kind === "json" ? JSON.parse(raw) : raw) as T extends "json" ? unknown : string;
}
```

- Conditional types distribute over naked type parameters in unions; wrap in a tuple (`[T] extends [U]`) to prevent distribution.
- `infer X extends C` constrains an inferred type (`ParseInt` above).
- A conditional return type needs a cast inside the implementation, because TypeScript cannot correlate the runtime branch with the type; keep such casts in small, tested functions, or use overloads.
- Prefer overloads when there are only two or three call shapes; use conditional return types when the mapping is systematic.

## 4. Mapped types and key remapping

```ts
export type Getters<T> = {
  [K in keyof T & string as `get${Capitalize<K>}`]: () => T[K];
};
// Getters<{ name: string }> is { getName: () => string }

export type DeepReadonly<T> = T extends (...args: never[]) => unknown
  ? T
  : T extends readonly (infer U)[]
    ? readonly DeepReadonly<U>[]
    : T extends object
      ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
      : T;
```

- `as` clauses rename or filter keys (map to `never` to drop a key).
- Homomorphic mapped types (`[K in keyof T]`) preserve optionality and `readonly`; add or remove with `+?`, `-?`, `+readonly`, `-readonly`.
- Use `keyof T & string` when building template literal keys, since `keyof` can include `number` and `symbol`.

## 5. Template literal types

```ts
export type RouteParams<Path extends string> =
  Path extends `${string}:${infer Param}/${infer Rest}`
    ? { [K in Param | keyof RouteParams<`/${Rest}`>]: string }
    : Path extends `${string}:${infer Param}`
      ? { [K in Param]: string }
      : {};
// RouteParams<"/users/:id/posts/:postId"> is { id: string; postId: string }

export type Split<S extends string, D extends string> =
  S extends `${infer H}${D}${infer T}` ? [H, ...Split<T, D>] : S extends "" ? [] : [S];

export type Join<T extends readonly string[], Sep extends string, Acc extends string = ""> =
  T extends readonly [infer H extends string, ...infer R extends readonly string[]]
    ? Join<R, Sep, Acc extends "" ? H : `${Acc}${Sep}${H}`>
    : Acc;
```

- `Join` carries an accumulator, which makes the recursion tail-recursive and allows deeper inputs than a non-tail version.
- Use template literal types for typed routes, event names (`${Entity}:${"created" | "deleted"}`), CSS custom property names and header names; keep string-parsing types to small inputs.
- Inferring from an empty placeholder consumes a full Unicode code point in TypeScript 7 (the 6.x behavior split surrogate pairs).

## 6. Typed event map and builder

```ts
export type Events = { login: { userId: string }; logout: undefined };

export class Emitter<E extends Record<string, unknown>> {
  readonly #handlers = new Map<keyof E, Set<(payload: never) => void>>();

  on<K extends keyof E>(event: K, handler: (payload: E[K]) => void): () => void {
    const set = this.#handlers.get(event) ?? new Set();
    set.add(handler as (payload: never) => void);
    this.#handlers.set(event, set);
    return () => set.delete(handler as (payload: never) => void);
  }

  emit<K extends keyof E>(event: K, ...args: E[K] extends undefined ? [] : [payload: E[K]]): void {
    for (const h of this.#handlers.get(event) ?? []) (h as (p: unknown) => void)(args[0]);
  }
}
// emit("logout") needs no payload; emit("login") without a payload is a compile error

export class Query<Set extends string = never> {
  declare readonly _done: (steps: Set) => void; // phantom member so Set affects assignability
  readonly #parts: Readonly<Record<string, string>>;
  private constructor(parts: Readonly<Record<string, string>>) { this.#parts = parts; }
  static create(): Query { return new Query({}); }
  from(table: string): Query<Set | "from"> { return new Query({ ...this.#parts, from: table }); }
  where(clause: string): Query<Set | "where"> { return new Query({ ...this.#parts, where: clause }); }
  build(this: Query<"from" | "where">): string {
    return `SELECT * FROM ${this.#parts["from"]} WHERE ${this.#parts["where"]}`;
  }
}
// Query.create().from("users").build() is a compile error: where() was never called
```

- The builder tracks completed steps in a type parameter; a contravariant phantom member makes `Query<"from">` not assignable to `Query<"from" | "where">`. Interpolating user input into SQL as shown is only for illustrating types; use parameterized queries in real code.
- Generic constraints (`E extends Record<string, unknown>`) tie the handler signature to the map without overloads.

## 7. Resource management with using

```ts
export class TempFile implements Disposable {
  readonly path: string;
  constructor(path: string) { this.path = path; }
  [Symbol.dispose](): void { /* release the resource */ }
}

export function useTemp(): string {
  using file = new TempFile("/tmp/example");
  return file.path; // dispose runs when the scope exits, including on throw
}
```

- `await using` pairs with `Symbol.asyncDispose` for async cleanup. `DisposableStack` and `AsyncDisposableStack` collect several resources.
- The runtime must support the feature or the compiler must downlevel it; check `target` and `lib` (`esnext.disposable`) for your environment.

## 8. Type guards and narrowing

```ts
export function isDefined<T>(v: T | null | undefined): v is T { return v != null; }
export function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}
const present = [1, null, 2, undefined].filter(isDefined); // number[]
```

- Recent compilers infer type predicates for simple arrow functions (`(x) => x !== null`), so explicit predicates are needed mainly for exported APIs.
- Narrow `unknown` with `typeof`, `in`, `Array.isArray` and schema parsers; avoid casts.
- Use `Object.hasOwn(obj, key)` (not `in`) when checking own properties of untrusted objects.

## 9. Testing types

Compile-time assertions without dependencies:

```ts
export type Equal<X, Y> =
  (<T>() => T extends X ? 1 : 2) extends (<T>() => T extends Y ? 1 : 2) ? true : false;
type Expect<T extends true> = T;

type _t1 = Expect<Equal<RouteParams<"/users/:id/posts/:postId">, { id: string; postId: string }>>;
```

With vitest (`vitest run --typecheck`, config `test.typecheck.enabled` and `include: ["src/**/*.test-d.ts"]`):

```ts
import { expectTypeOf, test } from "vitest";
import type { UserId, RouteParams } from "./types.js";
import { parseUserId, tuple } from "./types.js";

test("branded ids are not plain strings", () => {
  expectTypeOf(parseUserId("usr_abcdefgh")).toEqualTypeOf<UserId>();
  expectTypeOf<string>().not.toExtend<UserId>();
});

test("const type parameters keep tuples", () => {
  expectTypeOf(tuple(1, "a")).toEqualTypeOf<readonly [1, "a"]>();
  expectTypeOf<RouteParams<"/health">>().toEqualTypeOf<{}>();
});
```

- `expectTypeOf` (expect-type) offers `toEqualTypeOf`, `toExtend`, `toMatchObjectType`, `toBeCallableWith`, `toHaveProperty`, `toBeNever`, `toBeAny`, `toBeUnknown`, plus `.not` and helpers such as `.parameters` and `.returns`. `toMatchTypeOf` still exists but `toExtend` is the current name.
- `// @ts-expect-error` marks code that must fail to compile; an unused directive is itself an error.
- `tsd` (`expectType<T>(value)`, `expectError(...)`, files named `*.test-d.ts`) bundles its own TypeScript (5.9 for tsd 0.33), so it validates against that version, not your installed compiler.
- Run type tests in CI against the TypeScript versions your consumers use (for libraries, a matrix across supported versions).

## 10. Keeping types fast and readable

- Keep recursion shallow. Non-tail-recursive conditional types hit the instantiation depth limit quickly, while tail-recursive ones (accumulator parameter, as in `Join`) are allowed far more iterations (TypeScript 4.5 raised that limit to 1000). Break large computations into named aliases.
- Be careful with unions of hundreds of members combined with mapped or conditional types; the cost multiplies.
- Prefer `interface extends` over repeated intersections of object types; interfaces are cached by name, and intersections are re-computed.
- Annotate exported function return types: it speeds the compiler, makes `.d.ts` stable, and is required by `isolatedDeclarations`.
- A type that needs a paragraph of explanation is a candidate for a schema, a codegen step or a simpler API.
- Use `tsc --extendedDiagnostics` and `tsc --generateTrace dir` to find expensive types; TS2589 means an instantiation hit the depth limit.
- Do not hide `any` inside utility types; `unknown` plus constraints keeps callers honest.
