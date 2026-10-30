# Refactoring Catalog with Before and After (TypeScript)

Common refactorings from Martin Fowler, *Refactoring: Improving the Design of Existing Code* (2nd ed., 2018), shown on small TypeScript examples. Every block below compiles under `strict`, and the before and after versions in sections 2, 3, 4 and 6 returned identical results over the sample inputs used to check them; the pairs in sections 5, 7 and 8 change an API shape on purpose and need caller migration. A refactoring is only a refactoring if observable behavior stays the same: run the tests after every step and commit after each green step. Names in bold are the catalog names from the book.

## Contents
1. [Smell to refactoring map](#1-smell-to-refactoring-map)
2. [Extract Function, Split Phase, Replace Loop with Pipeline](#2-extract-function-split-phase-replace-loop-with-pipeline)
3. [Decompose Conditional and guard clauses](#3-decompose-conditional-and-guard-clauses)
4. [Replace Conditional with Polymorphism](#4-replace-conditional-with-polymorphism)
5. [Introduce Parameter Object and Replace Primitive with Object](#5-introduce-parameter-object-and-replace-primitive-with-object)
6. [Introduce Special Case](#6-introduce-special-case)
7. [Remove Flag Argument and Separate Query from Modifier](#7-remove-flag-argument-and-separate-query-from-modifier)
8. [Extract Class and Encapsulate Collection](#8-extract-class-and-encapsulate-collection)
9. [Change Function Declaration by parallel change](#9-change-function-declaration-by-parallel-change)
10. [Steps that are not refactorings](#10-steps-that-are-not-refactorings)

## 1. Smell to refactoring map

Smells are Fowler's 2nd edition list. A smell is a prompt to look, not a defect by itself.

| Smell | Typical refactorings |
|---|---|
| Mysterious Name | Change Function Declaration, Rename Variable, Rename Field |
| Duplicated Code | Extract Function, Slide Statements, Pull Up Method |
| Long Function | Extract Function, Replace Temp with Query, Introduce Parameter Object, Preserve Whole Object, Replace Function with Command, Decompose Conditional, Split Loop |
| Long Parameter List | Replace Parameter with Query, Preserve Whole Object, Introduce Parameter Object, Remove Flag Argument, Combine Functions into Class |
| Global Data | Encapsulate Variable |
| Mutable Data | Encapsulate Variable, Split Variable, Separate Query from Modifier, Remove Setting Method, Replace Derived Variable with Query, Change Reference to Value |
| Divergent Change | Split Phase, Move Function, Extract Function, Extract Class |
| Shotgun Surgery | Move Function, Move Field, Combine Functions into Class, Inline Function, Inline Class |
| Feature Envy | Move Function, Extract Function |
| Data Clumps | Extract Class, Introduce Parameter Object, Preserve Whole Object |
| Primitive Obsession | Replace Primitive with Object, Replace Type Code with Subclasses, Extract Class |
| Repeated Switches | Replace Conditional with Polymorphism |
| Loops | Replace Loop with Pipeline |
| Lazy Element, Speculative Generality | Inline Function, Inline Class, Collapse Hierarchy, Remove Dead Code |
| Temporary Field | Extract Class, Introduce Special Case |
| Message Chains | Hide Delegate, Extract Function, Move Function |
| Middle Man | Remove Middle Man, Inline Function |
| Large Class | Extract Class, Extract Superclass |
| Data Class | Encapsulate Record, Remove Setting Method, Move Function |
| Refused Bequest | Push Down Method, Replace Subclass with Delegate, Replace Superclass with Delegate |
| Comments (explaining unclear code) | Extract Function, Change Function Declaration, Introduce Assertion |

## 2. Extract Function, Split Phase, Replace Loop with Pipeline

Before: computation and formatting are interleaved, and `let` accumulators hide what each loop computes.

```typescript
// file: catalog/receipt.before.ts
export interface Line {
  readonly sku: string;
  readonly qty: number;
  readonly unitCents: number;
}

export function summary(lines: readonly Line[], taxRateBp: number): string {
  let subtotal = 0;
  for (const l of lines) {
    subtotal += l.qty * l.unitCents;
  }
  const tax = Math.round((subtotal * taxRateBp) / 10_000);
  let out = '';
  for (const l of lines) {
    out += `${l.sku} x${l.qty} ${((l.qty * l.unitCents) / 100).toFixed(2)}\n`;
  }
  out += `Subtotal ${(subtotal / 100).toFixed(2)}\nTax ${(tax / 100).toFixed(2)}\nTotal ${((subtotal + tax) / 100).toFixed(2)}\n`;
  return out;
}
```

After: **Extract Function** names each step, **Replace Loop with Pipeline** removes the accumulator, and **Split Phase** separates computing the numbers from rendering them.

```typescript
// file: catalog/receipt.after.ts
export interface Line {
  readonly sku: string;
  readonly qty: number;
  readonly unitCents: number;
}

const lineCents = (l: Line): number => l.qty * l.unitCents;
const money = (cents: number): string => (cents / 100).toFixed(2);

interface Totals {
  readonly subtotal: number;
  readonly tax: number;
  readonly total: number;
}

function computeTotals(lines: readonly Line[], taxRateBp: number): Totals {
  const subtotal = lines.reduce((sum, l) => sum + lineCents(l), 0);
  const tax = Math.round((subtotal * taxRateBp) / 10_000);
  return { subtotal, tax, total: subtotal + tax };
}

function renderReceipt(lines: readonly Line[], t: Totals): string {
  const body = lines.map((l) => `${l.sku} x${l.qty} ${money(lineCents(l))}\n`).join('');
  return `${body}Subtotal ${money(t.subtotal)}\nTax ${money(t.tax)}\nTotal ${money(t.total)}\n`;
}

export function summary(lines: readonly Line[], taxRateBp: number): string {
  return renderReceipt(lines, computeTotals(lines, taxRateBp));
}
```

## 3. Decompose Conditional and guard clauses

Before: nested conditions hide the rule.

```typescript
// file: catalog/shipping.before.ts
export interface ShippingInput {
  readonly totalCents: number;
  readonly country: string;
  readonly express: boolean;
  readonly isMember: boolean;
}

export function shippingCents(o: ShippingInput): number {
  let result: number;
  if (o.country === 'DE') {
    if (o.isMember) {
      result = 0;
    } else {
      if (o.totalCents >= 5000) {
        result = 0;
      } else {
        result = o.express ? 1299 : 499;
      }
    }
  } else {
    result = o.express ? 2999 : 1499;
  }
  return result;
}
```

After: **Replace Nested Conditional with Guard Clauses** plus **Decompose Conditional** (named predicates).

```typescript
// file: catalog/shipping.after.ts
export interface ShippingInput {
  readonly totalCents: number;
  readonly country: string;
  readonly express: boolean;
  readonly isMember: boolean;
}

const FREE_SHIPPING_THRESHOLD_CENTS = 5000;

const isDomestic = (o: ShippingInput): boolean => o.country === 'DE';
const qualifiesForFreeShipping = (o: ShippingInput): boolean =>
  o.isMember || o.totalCents >= FREE_SHIPPING_THRESHOLD_CENTS;

export function shippingCents(o: ShippingInput): number {
  if (!isDomestic(o)) return o.express ? 2999 : 1499;
  if (qualifiesForFreeShipping(o)) return 0;
  return o.express ? 1299 : 499;
}
```

The threshold is business data; keep it in configuration or a named constant, not as a rule of the refactoring.

## 4. Replace Conditional with Polymorphism

Use it when the same switch on a type code appears in several places (the **Repeated Switches** smell). In TypeScript a discriminated union with one exhaustive `switch` is often enough for a single decision; polymorphism pays off when each variant needs several behaviors.

Before: two functions switch on the same type code, so every new plan needs two edits.

```typescript
// file: catalog/plans.before.ts
export type PlanType = 'free' | 'team' | 'enterprise';

export function monthlyCents(plan: PlanType, seats: number): number {
  switch (plan) {
    case 'free':
      return 0;
    case 'team':
      return 800 * seats;
    case 'enterprise':
      return 2000 * seats;
  }
}

export function seatLimit(plan: PlanType): number {
  switch (plan) {
    case 'free':
      return 3;
    case 'team':
      return 50;
    case 'enterprise':
      return Number.POSITIVE_INFINITY;
  }
}
```

After: a record of behaviors keyed by the type code. `satisfies Record<PlanType, PlanBehavior>` makes the compiler reject a missing plan.

```typescript
// file: catalog/plans.after.ts
export type PlanType = 'free' | 'team' | 'enterprise';

interface PlanBehavior {
  monthlyCents(seats: number): number;
  readonly seatLimit: number;
}

const plans = {
  free: { monthlyCents: () => 0, seatLimit: 3 },
  team: { monthlyCents: (seats) => 800 * seats, seatLimit: 50 },
  enterprise: { monthlyCents: (seats) => 2000 * seats, seatLimit: Number.POSITIVE_INFINITY },
} satisfies Record<PlanType, PlanBehavior>;

export const monthlyCents = (plan: PlanType, seats: number): number => plans[plan].monthlyCents(seats);
export const seatLimit = (plan: PlanType): number => plans[plan].seatLimit;
```

## 5. Introduce Parameter Object and Replace Primitive with Object

Before: four parameters that always travel together (**Data Clumps**), with no place for the validation rule.

```typescript
// file: catalog/range.before.ts
export function overlaps(aStart: Date, aEnd: Date, bStart: Date, bEnd: Date): boolean {
  return aStart.getTime() < bEnd.getTime() && bStart.getTime() < aEnd.getTime();
}
```

After: the clump becomes a small immutable class that owns its invariant and its behavior.

```typescript
// file: catalog/range.after.ts
export class DateRange {
  constructor(readonly start: Date, readonly end: Date) {
    if (end.getTime() < start.getTime()) throw new RangeError('end must not be before start');
  }

  overlaps(other: DateRange): boolean {
    return this.start.getTime() < other.end.getTime() && other.start.getTime() < this.end.getTime();
  }
}
```

Migrate callers in steps: add the class, add an overload or a new function that takes `DateRange`, switch callers one by one, then remove the old signature (see section 9). The same move applies to **Replace Primitive with Object** for `Money`, `EmailAddress` or `Quantity`, where a private constructor and a `parse` factory keep invalid values out of the system.

## 6. Introduce Special Case

Before: every caller checks for a missing customer.

```typescript
// file: catalog/customer.before.ts
export interface Customer {
  readonly name: string;
  readonly plan: 'free' | 'team';
}

export function greeting(customer: Customer | undefined): string {
  return `Hello ${customer === undefined ? 'guest' : customer.name}`;
}

export function canExport(customer: Customer | undefined): boolean {
  return customer !== undefined && customer.plan === 'team';
}
```

After: one special-case value carries the default behavior, so the checks disappear from the callers.

```typescript
// file: catalog/customer.after.ts
export interface Customer {
  readonly name: string;
  readonly plan: 'free' | 'team';
}

const GUEST: Customer = { name: 'guest', plan: 'free' };
const orGuest = (c: Customer | undefined): Customer => c ?? GUEST;

export function greeting(customer: Customer | undefined): string {
  return `Hello ${orGuest(customer).name}`;
}

export function canExport(customer: Customer | undefined): boolean {
  return orGuest(customer).plan === 'team';
}
```

Apply the conversion once, at the edge where the value is loaded, so inner code never sees `undefined`.

## 7. Remove Flag Argument and Separate Query from Modifier

Before: a boolean that selects behavior, and a function that both answers a question and changes state.

```typescript
// file: catalog/flags.before.ts
export interface Seat {
  readonly row: number;
  readonly premium: boolean;
}

export function bookSeat(row: number, premium: boolean): Seat {
  return { row, premium };
}

export class Inbox {
  private readonly messages: string[] = [];

  /** Returns the oldest message and also removes it. */
  next(): string | undefined {
    return this.messages.shift();
  }

  push(m: string): void {
    this.messages.push(m);
  }
}
```

After: **Remove Flag Argument** gives each intent its own function, and **Separate Query from Modifier** splits `peek` from `take`.

```typescript
// file: catalog/flags.after.ts
export interface Seat {
  readonly row: number;
  readonly premium: boolean;
}

export const bookStandardSeat = (row: number): Seat => ({ row, premium: false });
export const bookPremiumSeat = (row: number): Seat => ({ row, premium: true });

export class Inbox {
  private readonly messages: string[] = [];

  peek(): string | undefined {
    return this.messages[0];
  }

  take(): void {
    this.messages.shift();
  }

  push(m: string): void {
    this.messages.push(m);
  }
}
```

## 8. Extract Class and Encapsulate Collection

Before: a class mixes two concepts (**Large Class**, **Data Clumps**) and exposes its collection for callers to mutate.

```typescript
// file: catalog/person.before.ts
export class Person {
  readonly phones: string[] = [];

  constructor(
    readonly name: string,
    readonly officeAreaCode: string,
    readonly officeNumber: string,
  ) {}

  officePhone(): string {
    return `(${this.officeAreaCode}) ${this.officeNumber}`;
  }
}
```

After: the telephone concept moves to its own class and the collection is only changed through methods.

```typescript
// file: catalog/person.after.ts
export class TelephoneNumber {
  constructor(readonly areaCode: string, readonly number: string) {}

  toString(): string {
    return `(${this.areaCode}) ${this.number}`;
  }
}

export class Person {
  private readonly _phones: string[] = [];

  constructor(readonly name: string, readonly office: TelephoneNumber) {}

  get phones(): readonly string[] {
    return this._phones;
  }

  addPhone(phone: string): void {
    this._phones.push(phone);
  }

  officePhone(): string {
    return this.office.toString();
  }
}
```

## 9. Change Function Declaration by parallel change

When a function has many callers (or callers you cannot edit in one commit), change its signature in three releasable steps, also called expand, migrate, contract.

```typescript
// file: catalog/parallel-change.ts
export interface Recipient {
  readonly email: string;
  readonly locale: string;
}

// Step 1 (expand): add the new signature next to the old one; the old one delegates.
export function sendWelcome(to: Recipient): string {
  return `welcome:${to.email}:${to.locale}`;
}

/** @deprecated Use sendWelcome({ email, locale }). Remove after all callers migrate. */
export function sendWelcomeLegacy(email: string, locale = 'en'): string {
  return sendWelcome({ email, locale });
}

// Step 2 (migrate): move callers one module or team at a time, each change releasable on its own.
// Step 3 (contract): when no references to sendWelcomeLegacy remain, delete it.
```

Find remaining callers with the compiler (rename to force errors), `grep`, ts-morph's `findReferencesAsNodes` or an ast-grep pattern; see [automated-refactoring.md](automated-refactoring.md). For a published library, keep the deprecated function for at least one release and announce the removal.

## 10. Steps that are not refactorings

These change behavior and belong in separate commits from refactoring steps:
- Fixing a bug found while reading the code.
- Changing a threshold, price or message.
- Adding validation that rejects input the old code accepted (for example the `RangeError` in section 5 changes behavior for reversed ranges).
- Changing error types, log formats or database queries that alter results.

Also separate formatting-only commits (running a formatter over many files) from structural ones, so reviewers and `git blame --ignore-revs-file` can skip the noise.
