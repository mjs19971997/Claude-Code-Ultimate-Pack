# Large-Scale and Automated Refactoring

When one change touches hundreds of files (an API migration, a rename, a deprecation, a framework upgrade) write a codemod instead of editing by hand. This file compares ts-morph, jscodeshift, ast-grep, Comby and OpenRewrite, and shows runnable examples. Versions verified in 2026-10: ts-morph 28.0.0 (bundles TypeScript 6.0.2), jscodeshift 17.4.0, ast-grep 0.51.0, Comby 1.8.1 (latest GitHub tag), OpenRewrite Maven plugin 6.46.1, OpenRewrite Gradle plugin 7.41.0 and `rewrite-recipe-bom` 3.38.0.

## Contents
1. [Choosing a tool](#1-choosing-a-tool)
2. [ts-morph: type-aware transforms](#2-ts-morph-type-aware-transforms)
3. [jscodeshift: syntax-level transforms](#3-jscodeshift-syntax-level-transforms)
4. [ast-grep: patterns and rules](#4-ast-grep-patterns-and-rules)
5. [Comby: structural search and replace for any language](#5-comby-structural-search-and-replace-for-any-language)
6. [OpenRewrite: JVM recipes](#6-openrewrite-jvm-recipes)
7. [Rollout process](#7-rollout-process)
8. [Codemod pitfalls](#8-codemod-pitfalls)

## 1. Choosing a tool

| Need | Tool | Why |
|---|---|---|
| Rename or move symbols, change signatures, update call sites that must resolve to one specific declaration | ts-morph | Uses the TypeScript type checker, so it can tell two functions with the same name apart |
| Rewrite syntax across thousands of JS, JSX, TS or TSX files, preserving formatting | jscodeshift | Wraps recast, reprints only changed nodes; runs in parallel workers; large ecosystem of existing codemods |
| Quick pattern-based rewrite or a lint-like rule with an automatic fix, many languages | ast-grep | Patterns look like the code (`console.log($$$ARGS)`), YAML rules, fast Rust implementation, `scan` and `run` commands |
| Search and replace with balanced delimiters in any language, including config and templates | Comby | Declarative templates with holes (`:[name]`) and no per-language AST code |
| Java, Kotlin, Gradle, Maven or Spring migrations | OpenRewrite | Recipes operate on a lossless semantic tree with type attribution; many ready-made framework upgrade recipes |
| Single rename or extract inside one editor session | Editor and language-server refactorings | Rename Symbol, Move to File, Extract Function, Organize Imports are safe and need no script |

Start with the least powerful tool that can express the change. A pattern rewrite in ast-grep is cheaper to write and review than a jscodeshift transform, which in turn is cheaper than ts-morph. Reach for ts-morph only when you need types or symbol resolution.

## 2. ts-morph: type-aware transforms

ts-morph wraps the TypeScript compiler API. The script below changes `createUser(name, email, admin)` to `createUser({ name, email, admin })` at every call that resolves to that exact declaration, then rewrites the declaration. It ran against ts-morph 28 on a sample project; run it from the project root so `tsconfig.json` resolves.

```typescript
// file: tools/codemods/positional-to-options.ts
import { Node, Project } from 'ts-morph';

const project = new Project({ tsConfigFilePath: 'tsconfig.json' });
const fn = project.getSourceFileOrThrow('src/users.ts').getFunctionOrThrow('createUser');

const params = fn.getParameters().map((p) => ({ name: p.getName(), type: p.getTypeNode()?.getText() ?? 'unknown' }));

// Resolve call sites through the type checker, so a same-named function elsewhere is not touched.
const edits = fn
  .findReferencesAsNodes()
  .flatMap((ref) => {
    const call = ref.getParent();
    return Node.isCallExpression(call) && call.getExpression() === ref ? [call] : [];
  })
  .filter((call) => call.getArguments().length === params.length) // leave unusual calls for manual review
  .map((call) => ({ call, args: call.getArguments().map((a) => a.getText()) }));

for (const { call, args } of edits) {
  for (const arg of call.getArguments()) call.removeArgument(arg);
  call.addArgument(`{ ${params.map((p, i) => `${p.name}: ${args[i]}`).join(', ')} }`);
}

for (const p of fn.getParameters()) p.remove();
fn.addParameter({ name: 'input', type: `{ ${params.map((p) => `${p.name}: ${p.type}`).join('; ')} }` });
fn.setBodyText(`const { ${params.map((p) => p.name).join(', ')} } = input;\n${fn.getBodyText() ?? ''}`);

project.saveSync();
console.log(`rewrote ${edits.length} call(s)`);
```

Notes:
- Collect nodes first, then edit: after a manipulation, previously obtained nodes can be invalid. The script gathers `edits` before changing anything.
- Calls with an unexpected argument count are skipped and should be listed for manual handling; print them instead of guessing.
- Run `tsc --noEmit` afterwards; the compiler is the first verifier of a signature change.
- ts-morph carries its own TypeScript version (6.0.2 in release 28), which can differ from the project's compiler; check the ts-morph release notes when the project uses newer language features.
- Run the script with a TypeScript runner such as `tsx`, or compile it first.

## 3. jscodeshift: syntax-level transforms

A transform is a module that exports a function `(file, api, options) => string | undefined | null`; returning `undefined` leaves the file unchanged. This transform replaces `console.log(...)` with `logger.debug(...)` and adds the import. It ran with jscodeshift 17.4 and `--parser=ts`.

```typescript
// file: tools/codemods/console-to-logger.ts
import type { API, FileInfo } from 'jscodeshift';

export default function transform(file: FileInfo, api: API): string | undefined {
  const j = api.jscodeshift;
  const root = j(file.source);

  const calls = root.find(j.CallExpression, {
    callee: {
      type: 'MemberExpression',
      object: { type: 'Identifier', name: 'console' },
      property: { type: 'Identifier', name: 'log' },
    },
  });
  if (calls.size() === 0) return undefined; // undefined means "unchanged"

  calls.forEach((path) => {
    path.node.callee = j.memberExpression(j.identifier('logger'), j.identifier('debug'));
  });

  const hasImport = root.find(j.ImportDeclaration, { source: { value: '@/logger' } }).size() > 0;
  if (!hasImport) {
    root.get().node.program.body.unshift(j.importDeclaration([j.importSpecifier(j.identifier('logger'))], j.stringLiteral('@/logger')));
  }
  return root.toSource({ quote: 'single' });
}
```

Run it (flags from `jscodeshift --help`):

```bash
npx jscodeshift -t tools/codemods/console-to-logger.ts --parser=ts --dry --print src
npx jscodeshift -t tools/codemods/console-to-logger.ts --parser=ts src
```

Use `--parser=tsx` for files containing JSX, `--extensions=ts,tsx` to select file types and `--ignore-pattern` to skip generated code. jscodeshift sees syntax only: it does not know whether `console` is shadowed or whether two identifiers refer to the same binding, so use scope checks (`path.scope.lookup`) or ts-morph when that matters. Test transforms with fixtures: the `jscodeshift/src/testUtils` helpers (`defineInlineTest`, `defineTest`) run a transform against input and expected-output files.

## 4. ast-grep: patterns and rules

Patterns are code with metavariables: `$X` matches one node, `$$$ARGS` matches zero or more. The one-off form (verified with ast-grep 0.51):

```bash
npx ast-grep run --pattern 'console.log($$$ARGS)' --rewrite 'logger.debug($$$ARGS)' --lang ts src
```

Without `--update-all` (`-U`) the command prints a diff and changes nothing; `-i` reviews each change interactively. For a rule that lives in the repository and runs in CI, add `sgconfig.yml` at the project root and a rule file:

```yaml
# sgconfig.yml
ruleDirs:
  - rules
```

```yaml
# rules/use-sleep-helper.yml
id: use-sleep-helper
language: ts
severity: warning
message: Use the shared sleep() helper instead of an inline timer promise.
rule:
  pattern: new Promise(($R) => setTimeout($R, $MS))
fix: sleep($MS)
```

`npx ast-grep scan src` reports matches and shows the proposed fix; `npx ast-grep scan --update-all src` applies them. The rule reported and rewrote `await new Promise((resolve) => setTimeout(resolve, 250));` to `await sleep(250);`. `ast-grep test` runs rule test cases. Rules can also combine conditions (`all`, `any`, `not`, `inside`, `has`, `kind`) and constrain metavariables; see the ast-grep rule reference for the current syntax.

Caution when writing `fix` strings: a captured expression is spliced in as text, so a rewrite such as `$X == null` to `$X === null || $X === undefined` changes meaning inside a larger expression (`a && b == null`). Parenthesize the replacement or restrict the match with `inside` and `kind`, and review the diff.

The `@ast-grep/napi` package exposes the same engine to Node.js scripts for rewrites that need logic.

## 5. Comby: structural search and replace for any language

Comby matches templates in which `:[hole]` matches any text up to the next literal in the template, with balanced parentheses, braces and strings respected. Template pair for changing a call shape:

```
match:   oldApi(:[url], :[opts])
rewrite: newApi({ url: :[url], ...:[opts] })
```

Comby does not parse the language, which is its strength for mixed repositories (source, config, docs) and its limit: it has no type information and no scope awareness. Pick the file matcher and the in-place or review mode from `comby -help` for your installed version (1.8.1 at the time of writing).

## 6. OpenRewrite: JVM recipes

OpenRewrite applies recipes to Java, Kotlin, Groovy, Gradle, Maven, YAML and properties files. Declarative recipes compose existing ones in a `rewrite.yml` at the project root:

```yaml
type: specs.openrewrite.org/v1beta/recipe
name: com.example.MigrateLegacyClient
displayName: Migrate LegacyClient to NewClient
recipeList:
  - org.openrewrite.java.ChangeType:
      oldFullyQualifiedTypeName: com.example.legacy.LegacyClient
      newFullyQualifiedTypeName: com.example.platform.NewClient
```

Activate it in Maven (the plugin version below was the latest when verified; update it) and preview with `mvn rewrite:dryRun`, which writes a patch file instead of changing sources, then apply with `mvn rewrite:run`:

```xml
<plugin>
  <groupId>org.openrewrite.maven</groupId>
  <artifactId>rewrite-maven-plugin</artifactId>
  <version>6.46.1</version>
  <configuration>
    <activeRecipes>
      <recipe>com.example.MigrateLegacyClient</recipe>
    </activeRecipes>
  </configuration>
</plugin>
```

Ready-made recipes for Java and Spring upgrades come from `rewrite-recipe-bom` (3.38.0 when verified) and the recipe modules it manages; add the modules you need as `plugin` dependencies. Gradle users apply the `org.openrewrite.rewrite` plugin (7.41.0 when verified) and use the `rewriteRun` and `rewriteDryRun` tasks. For logic that no existing recipe provides, write an imperative recipe in Java; see the OpenRewrite documentation for the current recipe-authoring API.

## 7. Rollout process

1. Write the codemod in the repository (`tools/codemods/`) with fixture tests: input file, expected output file, and at least one "must not change" case.
2. Run it in dry-run mode and read the diff of a sample covering each package or team.
3. Run it on a branch, then run the formatter, the type check, linters and the full test suite.
4. Commit the codemod and the generated changes separately, and list the formatting-only commit in an ignore-revs file for `git blame`.
5. Land in batches for large monorepos (per package or per owner, using CODEOWNERS for review routing) so conflicts stay small; freeze or rebase long-lived branches on request.
6. Add a lint rule (ESLint `no-restricted-imports` or `no-restricted-syntax`, an ast-grep rule, or a dependency-cruiser rule) so the old pattern cannot return.
7. Delete the codemod when the migration is complete, or archive it with a note on what it migrated.

## 8. Codemod pitfalls

- Matching by name alone: a function called `format` in two modules is two different symbols. Use ts-morph or scope checks when names collide.
- Dropping comments or changing formatting: prefer tools that preserve trivia (recast in jscodeshift, ts-morph's printer), then run the project formatter.
- Operator precedence and `await` placement when splicing expression text: parenthesize captured expressions that may contain operators.
- Calls that cannot be migrated mechanically (spread arguments, dynamic callees, calls through `any`): detect and report them rather than guessing.
- Generated code, vendored code and snapshots: exclude them in the codemod's path filter and regenerate instead.
- Running the codemod twice: make it idempotent; the second run should change nothing.
