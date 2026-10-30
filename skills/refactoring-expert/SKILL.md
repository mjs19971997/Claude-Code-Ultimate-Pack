---
name: refactoring-expert
description: >-
  Improves the structure of existing code without changing behavior: code smells, Fowler's refactoring catalog, preparatory refactoring, characterization tests and seams for legacy code, sprout and wrap, strangler fig and parallel change, and large-scale codemods with ts-morph, jscodeshift, ast-grep, Comby and OpenRewrite. Use when cleaning up long functions or tangled classes, adding tests to untested code, planning an incremental rewrite or API migration, renaming or changing a signature across many files, or deciding whether to refactor or rewrite. Not for deciding the target layering of a service (use clean-architecture-expert), domain model redesign (use ddd-expert), splitting into services (use microservices-expert), reviewing someone else's diff (use code-review-expert), or writing tests as such (use unit-testing-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Refactoring Expert

This skill covers changing the internal structure of code while keeping its observable behavior, in steps small enough that each one can be verified and reverted. It covers recognizing smells, choosing a refactoring from the catalog, getting untested code under test, replacing components incrementally, and automating changes that span many files. Behavior changes, bug fixes and performance work are separate activities that this skill keeps apart from refactoring.

> Verified against Refactoring 2nd ed. (Fowler, 2018) catalog names, TypeScript 5.x strict with Vitest 5, ts-morph 28.0.0, jscodeshift 17.4.0, ast-grep 0.51.0, Comby 1.8.1, OpenRewrite Maven plugin 6.46.1, ESLint 10.14, eslint-plugin-sonarjs 4.2.2, knip 6.44 (2026-10).

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

- Covered: smell detection, the refactoring catalog with TypeScript before/after pairs, safe workflow, legacy code techniques (characterization tests, seams, sprout and wrap), incremental replacement (strangler fig, branch by abstraction, parallel change, parallel run), the Mikado Method, dead code removal, metrics as signals, and codemods.
- Not covered: choosing a layering or module structure (clean-architecture-expert); domain modelling (ddd-expert); service decomposition (microservices-expert); reviewing a specific diff (code-review-expert); test design in general (unit-testing-expert, integration-testing-expert); performance tuning (scalability-expert for system-level, profiling tools for code-level).

## 2. Core Expertise

- **Definition** (Fowler): a change to internal structure that makes code easier to understand and cheaper to modify without changing observable behavior. If behavior changes, it is not a refactoring.
- **Two hats** (Kent Beck): at any moment you are either adding behavior or refactoring. Switch hats deliberately, and never mix them in one commit.
- **Safety net**: automated tests, the type checker, linters, version control and small steps. The smaller the step, the cheaper a mistake.
- **Smells**: Fowler's 2nd edition list (Mysterious Name, Duplicated Code, Long Function, Long Parameter List, Global Data, Mutable Data, Divergent Change, Shotgun Surgery, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Loops, Lazy Element, Speculative Generality, Temporary Field, Message Chains, Middle Man, Insider Trading, Large Class, Alternative Classes with Different Interfaces, Data Class, Refused Bequest, Comments). A smell indicates where to look; the map to refactorings is in [references/refactoring-catalog.md](references/refactoring-catalog.md).
- **When to refactor** (Fowler): preparatory (make the change easy, then make the easy change), comprehension (encode what you just understood into the code), litter-pickup (leave the code a little better), planned (only when a larger structural debt blocks work). Rule of three: tolerate duplication twice, refactor on the third occurrence.
- **Tidyings** (Beck, *Tidy First?*, 2023): tiny structural edits (guard clauses, extract helper, explaining variable) made before a behavior change when they lower its cost.
- **Legacy code** (Feathers, *Working Effectively with Legacy Code*, 2004): code without tests. Break dependencies minimally, pin behavior with characterization tests, then change. See [references/legacy-code.md](references/legacy-code.md).
- **Incremental replacement**: strangler fig, branch by abstraction, parallel change (expand, migrate, contract), parallel run, and the Mikado Method for planning.
- **Automation**: language-server refactorings for single edits; ts-morph, jscodeshift, ast-grep, Comby and OpenRewrite for many files. See [references/automated-refactoring.md](references/automated-refactoring.md).

## 3. Workflow

1. State the goal in one sentence ("make the discount rules changeable in one place") and whether it is preparatory to a specific change.
2. Check the safety net: do tests cover the code you will touch, and do they pass now? If not, write characterization tests first, using seams to make the code testable (see the legacy reference).
3. Identify the smell and pick the refactoring from the catalog; for large goals, draw a Mikado graph of prerequisites.
4. Take one small step with the tool that does it mechanically (editor rename, extract, move) wherever possible.
5. Run the compiler and tests. Green: commit with a message that starts with `refactor:`. Red: revert the step (do not debug a broken refactoring) and take a smaller step.
6. Repeat until the structure supports the intended change. Stop at "good enough for this change"; do not tidy the whole file.
7. Make the behavior change in separate commits after the structural ones.
8. For changes spanning many files or teams, use parallel change so every commit stays releasable, and a codemod for the migrate step.
9. Remove what became unused (old signature, dead code, temporary adapters) as the last step, or the refactoring is not finished.
10. Record formatting-only or mechanical commits in `.git-blame-ignore-revs` so history stays readable.

## 4. Decision Rules

- Refactor when it lowers the cost or risk of a change you are about to make, or when you needed effort to understand the code. Do not refactor code that is stable, rarely touched and working, unless it blocks work.
- Refactor, do not rewrite, unless the code is small, well understood and fully specified by tests, or the technology is being replaced. A rewrite of a large system has to recover every undocumented behavior; use strangler fig for replacement.
- No tests and no seam: add the smallest dependency-breaking change, write characterization tests, then refactor. If that is impossible, restrict yourself to automated refactorings the tools guarantee (rename, extract) and verify by review and the compiler.
- A step that needs the tests changed is not a pure refactoring unless it only touches tests coupled to the internal structure being changed; make test edits and code edits in separate commits where possible.
- Public APIs (HTTP, library exports, database schema, events) need compatibility handling: expand, migrate, contract over several releases.
- Metrics are signals, not goals. Tool defaults are starting points to tune per codebase: ESLint core defaults are `complexity` 20, `max-lines-per-function` 50, `max-params` 3 and `max-depth` 4 (these rules are off unless enabled), and eslint-plugin-sonarjs `cognitive-complexity` defaults to 15. Raise or lower them after looking at your distribution of values; lint only new and changed code on legacy codebases.
- Prioritize by change frequency times pain: files that change often and are hard to change (churn plus complexity from version-control history) come first.
- Dead code: delete it. Version control remembers it.

## 5. Coding Standards

- Prefer small functions with one level of abstraction and names that say what, not how; extract when a comment explains a block.
- Prefer returning values over mutating arguments; use `readonly` and `as const` for data that should not change.
- Replace boolean parameters with separate functions or option objects, and long parameter lists with a parameter object.
- Model variants as discriminated unions and handle them with an exhaustive `switch` whose default branch assigns to `never`, so adding a variant fails compilation where it is unhandled.
- Replace `any` and unchecked casts with `unknown` plus narrowing at boundaries.
- Keep functions free of hidden dependencies (clock, randomness, globals); pass them in.
- Keep one commit per refactoring step, each leaving tests green; write messages as `refactor: <catalog name> <what>`.
- Do not widen visibility or export symbols just to make a test pass; test through the public behavior or introduce a seam.

## 6. Project Structure

```
src/
├── orders/
│   ├── discount.ts
│   └── discount.test.ts          # pinned behavior, kept after the refactoring
tools/
└── codemods/
    ├── console-to-logger.ts       # codemod, with fixtures and a "must not change" case
    └── __fixtures__/
rules/                              # ast-grep rules that stop old patterns returning
sgconfig.yml
.git-blame-ignore-revs              # mechanical and formatting-only commits
```

Legacy characterization tests live beside the code they pin and are renamed to ordinary tests once the behavior is confirmed.

## 7. Design Patterns

Refactorings often end in a pattern, but the pattern is the result, not the plan. Typical destinations:
- **Strategy or behavior table** from repeated switches on a type code.
- **Null object or special case** from repeated `undefined` checks.
- **Adapter or anti-corruption layer** from direct use of a legacy API (the seam for replacement).
- **Facade or router** in front of an old system for strangler fig.
- **Decorator** from wrap method and wrap class.
- **Parameter object, value object, command object** from long parameter lists, primitive obsession and long functions with many temporaries.
- **Pipeline** from accumulating loops.

Joshua Kerievsky, *Refactoring to Patterns* (2004), describes behavior-preserving routes to patterns. Introduce a pattern when the code shows the duplication or variation it resolves, not in anticipation.

## 8. Best Practices

- Work in the smallest step that keeps tests green; a step that takes more than a few minutes to verify is too big.
- Let the compiler find usages: rename a symbol or change a type and follow the errors.
- Prefer IDE or language-server refactorings (Rename Symbol, Extract Function, Move to File) over manual edits; they update references.
- Run the full test suite before pushing; run the fast subset after every step.
- Keep pull requests reviewable: structural moves in one commit and edits in another, so `git diff --color-moved` and rename detection make the review simple.
- Make flag-guarded or compatibility changes visible in code with a `@deprecated` comment and a removal condition.
- Ask what the next change will be; refactor toward that change only.
- Delete temporary scaffolding (adapters, flags, characterization tests that duplicate new tests) when the migration ends.

## 9. Performance

- Refactoring should not change performance characteristics intentionally; if a refactoring may (extracting functions in a hot loop, replacing a loop with chained array methods that allocate, splitting a loop into two passes), measure that path before and after and keep the optimization decision separate.
- Most of the cost of structure is cognitive, not CPU. Optimize only what a profile shows, and refactor first when code is too tangled to optimize safely.
- A parallel run doubles work for the shadowed call; sample the traffic and keep the shadow off the request's critical path.
- Large codemods run once; their speed matters only for CI-time lint rules (ast-grep scans and ESLint with type information have different costs, so scope them to changed files).

## 10. Security

- Refactors silently weaken security when code moves: an authorization check, tenant filter, input validation or output encoding that lived in the old location must be carried to the new one. List these before moving code and verify with tests.
- Extracting a query function must keep the tenant or owner predicate on writes as well as reads; add a test that a second tenant cannot read, update or delete the record.
- Characterization tests may capture real data; use synthetic or scrubbed inputs and golden masters free of secrets and personal data.
- Do not log new values while debugging a refactoring in a way that reaches production logs.
- A codemod and its dependencies execute with the repository's permissions: pin versions, review third-party codemods before running them, and run them on a branch without access to secrets.
- Deleting "dead" code can remove a rarely used security control (a cleanup job, a revocation path); check scheduled jobs, feature flags and reflection before deleting.

## 11. Testing

- **Characterization tests** pin current behavior before changes in legacy code (record actual outputs, then assert them).
- **Golden master or snapshot tests** cover large outputs; scrub timestamps and ids; review snapshot diffs as carefully as code.
- **Property-based tests** (fast-check 4.10 for TypeScript) compare old and new implementations over generated inputs: assert `newImpl(x)` equals `oldImpl(x)` while both exist.
- **Mutation testing** (Stryker, `@stryker-mutator/core` 10.1) checks whether the tests would notice a change; use it to judge a safety net before a risky refactoring.
- **Contract tests** protect interfaces that stay stable while the implementation changes.
- Tests should assert behavior, not structure. Tests tightly coupled to private methods or mocks of internals break on every refactoring and should be rewritten to the public behavior first.
- After the refactoring, remove duplicate or redundant characterization tests and keep the ones that express rules.

## 12. Review Checklist

- [ ] The change is either a refactoring or a behavior change, not both in one commit.
- [ ] Tests existed (or were added first) for the code touched, and pass after every commit.
- [ ] No test expectation changed in a "refactor" commit, or the change is explained as test-only decoupling.
- [ ] Moved code kept its authorization, tenant scoping, validation and error handling.
- [ ] Public signatures, events, schemas and exports are unchanged or migrated with parallel change.
- [ ] Old code, flags and adapters that the change made obsolete are removed or tracked with an owner.
- [ ] Mechanical or formatting commits are separate and listed in the ignore-revs file.
- [ ] Complexity or size thresholds are used as signals and configured per project, not copied blindly.
- [ ] Codemods are idempotent, have fixtures, and unusual cases are reported rather than guessed.
- [ ] Performance-sensitive paths were measured if the refactoring touched them.

## 13. Production Notes

- Ship risky structural changes behind a flag or as a parallel run first; keep the old path until the new one has matched it on real traffic, then delete it.
- Database changes follow expand and contract: add the new column or table, dual-write or backfill, migrate readers, then drop the old structure in a later release. The application and schema must work together at every deployed version.
- Roll out in small releases; a refactoring that cannot be rolled back by redeploying the previous version needs extra care and a written plan.
- Communicate large moves (renames, directory restructures) to the team and land them quickly to minimize merge conflicts; ask others to rebase.
- Add a lint or architecture rule that prevents the old pattern from returning; otherwise the refactoring decays.
- Track outcomes that the refactoring was meant to improve (time to change, defect rate in the area, build or test time), not only structural metrics.

## 14. Examples

### Example 1: Pin behavior, then extract and name the rules

The discount rules below were extracted from one long function after the table-driven test had been written against the original. The test is unchanged by the refactoring.

```typescript
// file: orders/discount.ts
export interface CartLine {
  readonly qty: number;
  readonly unitCents: number;
}

export interface Cart {
  readonly lines: readonly CartLine[];
  readonly couponPercent?: number;
  readonly isMember: boolean;
}

const MAX_DISCOUNT_PERCENT = 30;
const BULK_MIN_ITEMS = 10;

const subtotalCents = (lines: readonly CartLine[]): number =>
  lines.reduce((sum, l) => sum + l.qty * l.unitCents, 0);

const itemCount = (lines: readonly CartLine[]): number => lines.reduce((n, l) => n + l.qty, 0);

function discountPercent(cart: Cart): number {
  const bulk = itemCount(cart.lines) >= BULK_MIN_ITEMS ? 5 : 0;
  const member = cart.isMember ? 3 : 0;
  const coupon = cart.couponPercent ?? 0;
  return Math.min(bulk + member + coupon, MAX_DISCOUNT_PERCENT);
}

export function totalCents(cart: Cart): number {
  return Math.round((subtotalCents(cart.lines) * (100 - discountPercent(cart))) / 100);
}
```

```typescript
// file: orders/discount.test.ts
import { describe, expect, it } from 'vitest';
import { totalCents, type Cart } from './discount';

const line = (qty: number, unitCents: number) => ({ qty, unitCents });

describe('totalCents (pinned before refactoring)', () => {
  it.each<{ name: string; cart: Cart; expected: number }>([
    { name: 'no discounts', cart: { lines: [line(1, 1000)], isMember: false }, expected: 1000 },
    { name: 'member', cart: { lines: [line(1, 1000)], isMember: true }, expected: 970 },
    { name: 'bulk at threshold', cart: { lines: [line(10, 100)], isMember: false }, expected: 950 },
    { name: 'just below bulk', cart: { lines: [line(9, 100)], isMember: false }, expected: 900 },
    { name: 'coupon plus member plus bulk', cart: { lines: [line(10, 100)], isMember: true, couponPercent: 10 }, expected: 820 },
    { name: 'discount cap', cart: { lines: [line(10, 100)], isMember: true, couponPercent: 50 }, expected: 700 },
    { name: 'empty cart', cart: { lines: [], isMember: true }, expected: 0 },
  ])('$name', ({ cart, expected }) => {
    expect(totalCents(cart)).toBe(expected);
  });
});
```

### Example 2: Lint thresholds as adjustable signals (ESLint 10 flat config)

```javascript
// eslint.config.mjs
import tseslint from 'typescript-eslint';

export default [
  {
    files: ['src/**/*.ts'],
    languageOptions: { parser: tseslint.parser },
    rules: {
      // Starting points taken from the rules' own defaults; tune after looking at your codebase.
      complexity: ['warn', { max: 20 }],
      'max-lines-per-function': ['warn', { max: 50, skipBlankLines: true, skipComments: true }],
      'max-params': ['warn', { max: 3 }],
      'max-depth': ['warn', { max: 4 }],
    },
  },
  {
    // On a legacy codebase, enforce only where new work happens.
    files: ['src/legacy/**/*.ts'],
    rules: { complexity: 'off', 'max-lines-per-function': 'off', 'max-params': 'off', 'max-depth': 'off' },
  },
];
```

### Example 3: Commit sequence for a preparatory refactoring

```text
test: pin totalCents behavior with table-driven characterization tests
refactor: Extract Function subtotalCents and itemCount from totalCents
refactor: Extract Function discountPercent, name BULK_MIN_ITEMS
refactor: Replace magic number 30 with MAX_DISCOUNT_PERCENT
feat: add loyalty tier discount (behavior change, new tests)
chore: remove legacy discount helper (no remaining references)
```

More before/after pairs are in [references/refactoring-catalog.md](references/refactoring-catalog.md), and a runnable ts-morph, jscodeshift and ast-grep codemod set is in [references/automated-refactoring.md](references/automated-refactoring.md).

## 15. Common Mistakes

- **Refactoring without tests.** Behavior changes unnoticed. Write characterization tests or use only tool-guaranteed refactorings.
- **Mixing refactoring and behavior change in one commit or pull request.** Neither can be reviewed or reverted cleanly. Separate them.
- **Big-bang restructuring on a long-lived branch.** Merge conflicts grow and the branch stays broken for weeks. Use small releasable steps, parallel change and the Mikado Method.
- **Debugging a failed step instead of reverting it.** Revert, take a smaller step.
- **Speculative refactoring.** Abstractions for requirements that do not exist add indirection. Refactor toward the next real change.
- **Introducing a pattern up front.** Let duplication or variation justify it.
- **Rewriting instead of refactoring.** Undocumented behavior is lost. Strangle in slices, comparing old and new with a parallel run.
- **Deleting tests that "get in the way".** If a test breaks on a pure refactoring it was coupled to structure; decouple it first, then proceed.
- **Matching codemod targets by name.** Two symbols named `format` are not the same. Use type-aware tools or scope checks and review the diff.
- **Leaving the old path in place.** Compatibility shims, flags and deprecated functions need a removal condition and an owner.
- **Treating metrics as targets.** Splitting a function only to satisfy a line limit can make it harder to follow. Use thresholds to find candidates, then judge.
- **Dropping security checks during a move.** Authorization and tenant predicates on writes are easy to lose when extracting data access; test for them.

## 16. References

- [references/refactoring-catalog.md](references/refactoring-catalog.md): smell-to-refactoring map and before/after TypeScript for the most used refactorings, plus parallel change.
- [references/legacy-code.md](references/legacy-code.md): legacy change algorithm, characterization tests, seams and dependency breaking, sprout and wrap, strangler fig, branch by abstraction, parallel run, Mikado Method, dead code.
- [references/automated-refactoring.md](references/automated-refactoring.md): choosing between ts-morph, jscodeshift, ast-grep, Comby and OpenRewrite, with runnable examples and a rollout process.
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd ed. (2018).
- Michael C. Feathers, *Working Effectively with Legacy Code* (2004).
- Kent Beck, *Tidy First?* (2023); Joshua Kerievsky, *Refactoring to Patterns* (2004).
- Ola Ellnestam and Daniel Brolund, *The Mikado Method* (2014).
- Martin Fowler, bliki article "StranglerFigApplication"; Sam Newman, *Monolith to Microservices* (2019).
