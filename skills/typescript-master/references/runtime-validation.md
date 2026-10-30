# Runtime Validation at Boundaries

Reference for validating untrusted data in TypeScript with zod 4 and valibot 1, and for writing code that accepts either through the Standard Schema interface. Verified against zod 4.6.7, valibot 1.5.0, @standard-schema/spec 1.1.0, @valibot/to-json-schema 1.8.0, TypeScript 7.0.2 and Node.js 22.22 (2026-10). The snippets were compiled and executed.

## 1. Where to validate

Types are erased at runtime, so any value that crosses a trust boundary must be parsed before it is treated as a typed value:

- HTTP request bodies, query strings, path parameters and headers
- Environment variables and configuration files
- Responses from third-party APIs and databases without generated types
- Message queue payloads, webhooks, WebSocket frames
- `JSON.parse`, `localStorage`, `postMessage`, URL hash and cookies

Parse once at the edge, return the parsed value, and let internal code accept only parsed types (often branded or schema-derived).

## 2. zod 4

```ts
import { z } from "zod";

export const Event = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("created"), id: z.uuid(), name: z.string().trim().min(1).max(200) }),
  z.strictObject({ type: z.literal("deleted"), id: z.uuid() }),
]);
export type Event = z.infer<typeof Event>;

export const Page = z.object({
  page: z.coerce.number().int().min(1).default(1),
  size: z.coerce.number().int().min(1).max(100).default(20),
});
export type PageInput = z.input<typeof Page>;    // what callers may send
export type PageOutput = z.output<typeof Page>;  // what the code receives

export function handle(raw: unknown) {
  const r = Event.safeParse(raw);
  if (!r.success) return { status: 400 as const, errors: z.flattenError(r.error) };
  return { status: 200 as const, event: r.data };
}
```

- `z.infer` is the output type; use `z.input` and `z.output` when transforms, defaults or coercion make them differ.
- Top-level format helpers: `z.email()`, `z.url()`, `z.uuid()`, `z.int()`, plus `z.iso.datetime()` and others (check the API docs for the current list).
- `parse` throws `ZodError`; `safeParse` returns `{ success, data | error }`. `z.flattenError`, `z.treeifyError` and `z.prettifyError` format issues for APIs, forms and logs.
- `z.object` strips unknown keys by default; `z.strictObject` rejects them (use it for security-sensitive inputs and webhooks); `z.looseObject` keeps them.
- `z.discriminatedUnion("type", [...])` gives fast, precise errors for tagged unions.
- `z.coerce.*` converts strings (query strings, env). Coercion is permissive (`z.coerce.boolean()` treats any non-empty string as true), so use `z.enum(["true", "false"])` or a custom transform for booleans.
- `.refine` and `.superRefine` add custom checks; `.transform` and `.pipe` change values.
- `z.toJSONSchema(schema)` emits JSON Schema (draft 2020-12 by default) for OpenAPI documents and LLM tool definitions.
- Always bound sizes: `.max(n)` on strings, arrays and records.

Environment parsing, once at startup:

```ts
const Env = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DATABASE_URL: z.url(),
});
export const env = Env.parse(process.env);
```

- Fail fast with all problems reported. Keep secrets on the server: do not expose the parsed object to client bundles, and never prefix secret variables with bundler-public prefixes (`NEXT_PUBLIC_`, `VITE_`).
- Do not log the whole `env` object.

## 3. valibot 1

```ts
import * as v from "valibot";

export const Signup = v.pipe(
  v.strictObject({
    email: v.pipe(v.string(), v.trim(), v.email(), v.maxLength(254)),
    password: v.pipe(v.string(), v.minLength(12), v.maxLength(128)),
    confirm: v.string(),
  }),
  v.forward(
    v.partialCheck([["password"], ["confirm"]], (i) => i.password === i.confirm, "Passwords differ"),
    ["confirm"],
  ),
);
export type Signup = v.InferOutput<typeof Signup>;

export const Msg = v.variant("type", [
  v.object({ type: v.literal("ping") }),
  v.object({ type: v.literal("data"), payload: v.array(v.number()) }),
]);

const result = v.safeParse(Signup, input);
if (!result.success) throw new TypeError(v.summarize(result.issues));
```

- Valibot is built from small functions (`v.string`, `v.pipe`, `v.minLength`, ...), so bundlers include only what you use; this suits front-end code with a size budget.
- `v.object` strips unknown keys, `v.strictObject` rejects them, `v.looseObject` keeps them.
- `v.pipe(schema, ...actions)` chains validations and transformations; `v.InferInput` and `v.InferOutput` give the types.
- `v.variant` is the discriminated union; `v.safeParse` returns `{ success, output | issues }`; `v.summarize` and `v.flatten` format issues.
- JSON Schema output comes from the separate `@valibot/to-json-schema` package.

## 4. Standard Schema

Both libraries implement the Standard Schema interface (`schema["~standard"]` with `vendor`, `version` and `validate`), so libraries and your own helpers can accept either:

```ts
import type { StandardSchemaV1 } from "@standard-schema/spec";

export async function validate<S extends StandardSchemaV1>(
  schema: S,
  data: unknown,
): Promise<StandardSchemaV1.InferOutput<S>> {
  const result = await schema["~standard"].validate(data);
  if (result.issues) throw new TypeError(result.issues.map((i) => i.message).join("; "));
  return result.value;
}
```

- `validate` may return a promise (async refinements), so `await` the result as shown.
- Use this for framework adapters (routers, form libraries) so application teams choose the schema library.
- `@standard-schema/spec` is types only; add it as a dev or type dependency.

## 5. Choosing between them

| Concern | zod 4 | valibot 1 |
|---|---|---|
| API style | Method chaining on schema objects | Functions composed with `pipe` |
| Bundle impact | Larger; a smaller functional `zod/mini` entry point also exists | Modular; unused actions are tree-shaken |
| JSON Schema | `z.toJSONSchema` built in | `@valibot/to-json-schema` |
| Ecosystem | Widest integration support | Growing; supported by many form and router libraries through Standard Schema |
| Errors | `flattenError`, `treeifyError`, `prettifyError` | `flatten`, `summarize` |

Pick one per codebase unless a library forces otherwise; both are fine for server code.

## 6. Security-oriented schema rules

- Prefer `strictObject` for webhooks, admin APIs and anything that is later spread into a database update, to avoid mass assignment of unexpected fields.
- Bound every collection and string length to keep memory and CPU bounded; reject oversized bodies before parsing at the HTTP layer too.
- Validate identifiers with exact patterns (`z.uuid()`, anchored regexes) rather than accepting arbitrary strings; avoid regexes with nested quantifiers on user input.
- Validate file names and paths by normalizing and checking against an allowed root after parsing, since a `string` schema does not make a path safe.
- Do not echo raw validation issues containing sensitive values to clients; return field names and generic messages, and log details server-side without secrets.
- When merging parsed objects, skip `__proto__`, `constructor` and `prototype` keys or build with `Object.create(null)`/`Map`; schemas with unknown-key rejection prevent most cases.
- Validate outbound data too when it comes from untrusted stores (for example, user-supplied JSON columns).
- Keep schema libraries updated; they sit directly on the attack surface.

## 7. Patterns

- **One schema, many outputs**: derive TypeScript types, runtime validation, JSON Schema/OpenAPI and test fixtures from one schema module.
- **Brand after parse**: give a validated string a branded type (`z.string().brand<"UserId">()` in zod, `v.pipe(v.string(), v.brand("UserId"))` in valibot) so internal functions can demand it.
- **Anti-corruption layer**: parse third-party responses into your own domain types in one adapter module; the rest of the code never sees vendor shapes.
- **Schema tests**: table-driven tests for valid input, each invalid class, boundary lengths, unknown keys, and coercion edge cases.
- **Form libraries and routers**: pass the schema through Standard Schema instead of writing resolvers per library.
