# Changing Legacy Code Safely

Techniques for code without tests, from Michael C. Feathers, *Working Effectively with Legacy Code* (2004), plus the incremental replacement patterns used at system level. Feathers defines legacy code as code without tests: without tests you cannot know whether a change preserved behavior. Examples are TypeScript 5.x with Vitest 5; Node.js 22.

## Contents
1. [The legacy change algorithm](#1-the-legacy-change-algorithm)
2. [Characterization tests](#2-characterization-tests)
3. [Seams and breaking dependencies](#3-seams-and-breaking-dependencies)
4. [Sprout and wrap](#4-sprout-and-wrap)
5. [Strangler fig, branch by abstraction, parallel run](#5-strangler-fig-branch-by-abstraction-parallel-run)
6. [Planning big changes: the Mikado Method](#6-planning-big-changes-the-mikado-method)
7. [Removing dead code](#7-removing-dead-code)

## 1. The legacy change algorithm

Feathers' sequence for any change in untested code:
1. Identify change points: where must the code change?
2. Find test points: where can behavior be observed (return values, writes, calls to collaborators)?
3. Break dependencies so the code can run in a test (time, network, database, globals, constructors that do work).
4. Write tests that pin current behavior.
5. Make the change, then refactor, with the tests running.

Steps 3 and 4 are the expensive ones; the minimum dependency-breaking edit that lets a test run is preferable to a clean redesign. Make those edits mechanical and small (add a parameter with a default, extract a method), because they are made without a safety net.

## 2. Characterization tests

A characterization test documents what the code actually does today, not what it should do. Procedure from Feathers: call the code in a test, assert something you know is wrong, run it, and copy the real result into the assertion. Bugs found this way are recorded, not fixed, until a decision is made to change the behavior.

```typescript
// file: legacy/pricing.ts
// Legacy function whose rules are unknown; do not "fix" it while characterizing.
export function legacyPrice(qty: number, tier: string, month: number): number {
  let p = qty * 1000;
  if (tier === 'gold') p = p * 0.9;
  if (qty > 10) p = p - 500;
  if (month === 12) p = p * 1.1;
  return Math.round(p);
}
```

```typescript
// file: legacy/pricing.characterization.test.ts
import { describe, expect, it } from 'vitest';
import { legacyPrice } from './pricing';

describe('legacyPrice (characterization)', () => {
  // Inputs span the boundaries the code branches on; expected values were recorded from the current implementation.
  it.each([
    { qty: 1, tier: 'basic', month: 3, expected: 1000 },
    { qty: 1, tier: 'gold', month: 3, expected: 900 },
    { qty: 10, tier: 'basic', month: 3, expected: 10000 },
    { qty: 11, tier: 'basic', month: 3, expected: 10500 },
    { qty: 11, tier: 'gold', month: 12, expected: 10340 },
    { qty: 0, tier: 'basic', month: 12, expected: 0 },
  ])('qty=$qty tier=$tier month=$month', ({ qty, tier, month, expected }) => {
    expect(legacyPrice(qty, tier, month)).toBe(expected);
  });
});
```

Practical guidance:
- Choose inputs from the branches in the code (boundaries and each condition), then add a few real production inputs.
- For large outputs (reports, HTML, generated files) use a golden master: store the output once and compare later outputs with Vitest snapshots (`toMatchSnapshot`, `toMatchFileSnapshot`) or an approval-testing tool. Scrub nondeterministic parts (timestamps, ids) before comparing.
- Pin down nondeterminism first: inject a clock and random source (section 3), or use Vitest fake timers (`vi.useFakeTimers`, `vi.setSystemTime`).
- A characterization test is not a specification. Mark tests that pin suspicious behavior with a comment, and keep a list of "behavior to confirm with the owner".
- Coverage and mutation testing (Stryker for JavaScript and TypeScript) show whether the pinned tests would notice a change; use them as a signal, not a target.

## 3. Seams and breaking dependencies

A seam is a place where behavior can be changed without editing the code at that place; the enabling point is where the choice is made. Feathers distinguishes object seams (substitute an object), link seams (substitute at link or module-resolution time) and preprocessing seams (macros, relevant in C and C++). In TypeScript the common ones are object seams (parameters, constructors) and module seams (a test runner's module mocking).

Before: time and network are baked in, so the function cannot be tested deterministically.

```typescript
// file: legacy/token.before.ts
export async function refreshIfExpired(token: { value: string; expiresAt: number }): Promise<string> {
  if (Date.now() < token.expiresAt) return token.value;
  const res = await fetch('https://auth.example.com/refresh', { method: 'POST', body: token.value });
  return await res.text();
}
```

After: **Parameterize** the dependencies with defaults that keep every existing caller unchanged. The default arguments are the enabling point.

```typescript
// file: legacy/token.after.ts
export interface TokenDeps {
  now(): number;
  post(url: string, body: string): Promise<string>;
}

const realDeps: TokenDeps = {
  now: () => Date.now(),
  post: async (url, body) => (await fetch(url, { method: 'POST', body })).text(),
};

export async function refreshIfExpired(
  token: { value: string; expiresAt: number },
  deps: TokenDeps = realDeps,
): Promise<string> {
  if (deps.now() < token.expiresAt) return token.value;
  return deps.post('https://auth.example.com/refresh', token.value);
}
```

```typescript
// file: legacy/token.test.ts
import { expect, it } from 'vitest';
import { refreshIfExpired } from './token.after';

it('returns the same token before expiry without calling the network', async () => {
  const deps = { now: () => 1000, post: async () => { throw new Error('unexpected network call'); } };
  expect(await refreshIfExpired({ value: 'abc', expiresAt: 2000 }, deps)).toBe('abc');
});

it('refreshes after expiry', async () => {
  const deps = { now: () => 3000, post: async (_url: string, body: string) => `new-${body}` };
  expect(await refreshIfExpired({ value: 'abc', expiresAt: 2000 }, deps)).toBe('new-abc');
});
```

Other dependency-breaking techniques from the book that map directly to TypeScript:
- **Parameterize Constructor** and **Parameterize Method**: pass the collaborator in, defaulting to the real one.
- **Extract Interface**: declare the minimal interface the code needs and let the real class satisfy it structurally.
- **Extract and Override Call**: move one awkward call into a protected method and override it in a test subclass.
- **Subclass and Override Method**: use a test subclass to neutralize behavior that cannot run in a test.
- **Extract Method** to isolate a pure core from a shell of I/O.
- Module mocking (`vi.mock`) is a link-style seam; prefer parameter seams for new code because they survive bundler and ESM changes.

Avoid **Introduce Static Setter**-style global hooks in production code; they make tests order-dependent.

## 4. Sprout and wrap

When the surrounding code cannot be tested yet, add new behavior in a testable unit and call it from the legacy code.

- **Sprout Method / Sprout Class**: write the new logic as a new function or class with tests (ideally test-first), then insert one call to it in the legacy function.
- **Wrap Method / Wrap Class**: keep the old behavior untouched and wrap it, so the new behavior runs before or after it.

```typescript
// file: legacy/sprout-wrap.ts
export interface Order {
  readonly id: string;
  readonly totalCents: number;
}

// Sprout: new rule, fully testable on its own.
export function loyaltyPoints(totalCents: number): number {
  return Math.floor(totalCents / 100);
}

declare function legacySaveOrder(order: Order): Promise<void>; // untested legacy code

// Wrap: new behavior around the unchanged legacy function (the Decorator pattern).
export async function saveOrderWithAudit(
  order: Order,
  audit: (entry: { orderId: string; points: number }) => Promise<void>,
): Promise<void> {
  await legacySaveOrder(order);
  await audit({ orderId: order.id, points: loyaltyPoints(order.totalCents) });
}
```

Both leave the legacy body unmodified. The cost is some duplication and a dependency edge from legacy to new code, which is the right direction.

## 5. Strangler fig, branch by abstraction, parallel run

System-level replacement without a big-bang rewrite. The strangler fig pattern (Martin Fowler's bliki article "StranglerFigApplication"; also discussed in Sam Newman, *Monolith to Microservices*, 2019) grows the new system around the old one and moves functionality across slice by slice.

1. Put a facade or router in front of the old system (reverse proxy, API gateway or an in-process router).
2. Pick one capability and build it in the new system. Route a small share of traffic or one tenant to it.
3. Compare behavior (see parallel run below), then route all traffic for that capability.
4. Delete the old implementation of that capability. Repeat.

**Branch by abstraction** does the same inside one codebase: introduce an abstraction over the old component, move callers onto it, build the new implementation behind it, switch with a flag, delete the old one. The trunk stays releasable throughout.

**Parallel change** (expand, migrate, contract) applies the same idea to a single interface; see the catalog, section 9.

**Parallel run (shadow comparison)**: run old and new implementations on the same input, return the old result, and record differences. GitHub's Scientist library popularized the technique in Ruby; the core is small enough to write directly.

```typescript
// file: legacy/shadow.ts
export interface Mismatch<I, O> {
  readonly input: I;
  readonly oldResult: O;
  readonly newResult: O | { readonly error: unknown };
}

export function withShadow<I, O>(
  oldImpl: (input: I) => Promise<O>,
  newImpl: (input: I) => Promise<O>,
  report: (m: Mismatch<I, O>) => void,
  equals: (a: O, b: O) => boolean = (a, b) => JSON.stringify(a) === JSON.stringify(b),
): (input: I) => Promise<O> {
  return async (input) => {
    const oldResult = await oldImpl(input);
    // The candidate never affects the caller: its result and its failures are only recorded.
    void newImpl(input).then(
      (newResult) => {
        if (!equals(oldResult, newResult)) report({ input, oldResult, newResult });
      },
      (error: unknown) => report({ input, oldResult, newResult: { error } }),
    );
    return oldResult;
  };
}
```

Rules for shadowing: the candidate must be free of side effects (writes go to a sandbox or are skipped), its latency must not reach the caller, sample if it doubles load, and mask personal data in the recorded mismatches. Move traffic across only when mismatches are explained or accepted.

Choosing: use strangler fig when the boundary is a network edge (HTTP, queue), branch by abstraction when the replaced part is a library or module deep inside, and parallel change for an interface with many callers. See microservices-expert when the target of the strangling is a set of services.

## 6. Planning big changes: the Mikado Method

For a change whose prerequisites are unknown (Ola Ellnestam and Daniel Brolund, *The Mikado Method*, 2014): try the goal change; when it breaks the build or tests, write down what blocked it as a prerequisite node and revert; repeat on each prerequisite until you find leaves that can be done safely; do the leaves first and commit each. The result is a graph of small, independently mergeable changes and never a long-lived broken branch.

## 7. Removing dead code

Deleting unused code is a refactoring (**Remove Dead Code**) and reduces what must be understood. Tools: the TypeScript compiler options `noUnusedLocals` and `noUnusedParameters`, ESLint's unused-variable rules, and knip (verified at 6.44) to find unused files, exports and dependencies across a project. Verify before deleting: dynamic imports, reflection, framework conventions (file-based routing), and public package exports can all hide real usage. Version control keeps the history, so delete rather than comment out.
