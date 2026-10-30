# Tactical Patterns

Reference for tactical Domain-Driven Design: entities, value objects, aggregates, factories, repositories, domain services, specifications, domain events and application services, with TypeScript code. Verified against Evans, Domain-Driven Design (2003), Vernon, Effective Aggregate Design (2011) and TypeScript 7.0 with `strict`, `exactOptionalPropertyTypes` and `noUncheckedIndexedAccess`; every code block in this file was type-checked (2026-10). Blocks marked `// file:` form one small project; imports use the `.js` extension required by `module: NodeNext`.

## 1. Identity and branded ids

Entities are compared by identity. Give ids their own types so an `OrderId` cannot be passed where a `CustomerId` is expected, and validate at the boundary.

```ts
// file: ids.ts
declare const brand: unique symbol;
export type Brand<T, B extends string> = T & { readonly [brand]: B };

export type OrderId = Brand<string, "OrderId">;
export type CustomerId = Brand<string, "CustomerId">;
export type AccountId = Brand<string, "AccountId">;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function parseUuid<B extends string>(kind: B, raw: string): Brand<string, B> {
  if (!UUID.test(raw)) throw new Error(`Invalid ${kind}`);
  return raw as Brand<string, B>;
}

export const orderId = (raw: string): OrderId => parseUuid("OrderId", raw);
export const customerId = (raw: string): CustomerId => parseUuid("CustomerId", raw);
export const accountId = (raw: string): AccountId => parseUuid("AccountId", raw);
```

Generate ids in the application layer or a factory through an `IdGenerator` port (UUID v4/v7, ULID) so the aggregate has an identity before it is saved and tests are deterministic.

## 2. Value objects

Immutable, validated on creation, compared by value, and rich in behavior. Return new instances from operations.

```ts
// file: value-objects.ts
export class DomainError extends Error {}

export class Email {
  private constructor(readonly value: string) {}

  static parse(raw: string): Email {
    const v = raw.trim().toLowerCase();
    if (v.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) throw new DomainError("Invalid email");
    return new Email(v);
  }

  equals(other: Email): boolean {
    return this.value === other.value;
  }
}

export class DateRange {
  private constructor(
    readonly start: Date,
    readonly end: Date,
  ) {}

  /** Half-open interval [start, end). */
  static of(start: Date, end: Date): DateRange {
    if (!(start.getTime() < end.getTime())) throw new DomainError("start must be before end");
    return new DateRange(new Date(start), new Date(end));
  }

  overlaps(other: DateRange): boolean {
    return this.start < other.end && other.start < this.end;
  }

  contains(instant: Date): boolean {
    return this.start <= instant && instant < this.end;
  }
}
```

Rules of thumb: wrap a primitive when it has rules (email, percentage, quantity), when two primitives always travel together (amount and currency, latitude and longitude), or when it carries operations. Copy mutable inputs (`Date`) on the way in and out.

## 3. Aggregates and invariants

Design rules (Vernon):

1. Model true invariants in consistency boundaries. An invariant is a business rule that must be true after every transaction.
2. Design small aggregates: the root, a few value objects, and only the entities the invariant needs.
3. Reference other aggregates by identity.
4. Use eventual consistency outside the boundary: react to domain events in a later transaction.

Sizing questions: Does this rule need both objects consistent at the same instant? How often do different users change the parts concurrently? How many children are there at the 95th percentile and at the maximum? If a rule can tolerate seconds or minutes of delay, it belongs across aggregates.

Example: a credit account protects "balance never below the negative credit limit". Only the account's own data is needed, so one aggregate is enough. Transfers between accounts are coordinated outside it.

```ts
// file: credit-account.ts
import { randomUUID } from "node:crypto";
import type { AccountId } from "./ids.js";
import { DomainError } from "./value-objects.js";

export type AccountEvent =
  | { type: "AccountDebited"; eventId: string; occurredAt: Date; accountId: AccountId; amountMinor: bigint; reference: string }
  | { type: "AccountCredited"; eventId: string; occurredAt: Date; accountId: AccountId; amountMinor: bigint; reference: string };

export class CreditAccount {
  private readonly pending: AccountEvent[] = [];
  private readonly seenReferences: Set<string>;

  constructor(
    readonly id: AccountId,
    private balanceMinor: bigint,
    private readonly creditLimitMinor: bigint,
    private version: number,
    processedReferences: Iterable<string> = [],
  ) {
    if (creditLimitMinor < 0n) throw new DomainError("Credit limit cannot be negative");
    if (balanceMinor < -creditLimitMinor) throw new DomainError("Balance below credit limit");
    this.seenReferences = new Set(processedReferences);
  }

  debit(amountMinor: bigint, reference: string, now: Date): void {
    this.assertPositive(amountMinor);
    if (this.seenReferences.has(reference)) return; // idempotent: same reference applied once
    if (this.balanceMinor - amountMinor < -this.creditLimitMinor) throw new DomainError("Credit limit exceeded");
    this.balanceMinor -= amountMinor;
    this.seenReferences.add(reference);
    this.pending.push({ type: "AccountDebited", eventId: randomUUID(), occurredAt: now, accountId: this.id, amountMinor, reference });
  }

  credit(amountMinor: bigint, reference: string, now: Date): void {
    this.assertPositive(amountMinor);
    if (this.seenReferences.has(reference)) return;
    this.balanceMinor += amountMinor;
    this.seenReferences.add(reference);
    this.pending.push({ type: "AccountCredited", eventId: randomUUID(), occurredAt: now, accountId: this.id, amountMinor, reference });
  }

  get balance(): bigint {
    return this.balanceMinor;
  }

  get loadedVersion(): number {
    return this.version;
  }

  pullEvents(): AccountEvent[] {
    return this.pending.splice(0, this.pending.length);
  }

  private assertPositive(amountMinor: bigint): void {
    if (amountMinor <= 0n) throw new DomainError("Amount must be positive");
  }
}
```

The set of processed references makes `debit` and `credit` safe against redelivered commands. In production, persist references (or a bounded window of them) with the aggregate, or enforce uniqueness in the database.

## 4. Factories

Use a factory when creation involves policy, many parameters, or building a valid aggregate from another aggregate's data. A static method on the aggregate covers most cases; a separate class is justified when creation needs collaborators.

```ts
// file: account-factory.ts
import { randomUUID } from "node:crypto";
import { type AccountId, accountId } from "./ids.js";
import { CreditAccount } from "./credit-account.js";
import { DomainError } from "./value-objects.js";

export type CustomerTier = "standard" | "premium";

export class AccountFactory {
  private static readonly LIMITS: Record<CustomerTier, bigint> = { standard: 0n, premium: 500_00n };

  open(tier: CustomerTier, openingDepositMinor: bigint, now: Date): CreditAccount {
    if (openingDepositMinor < 0n) throw new DomainError("Opening deposit cannot be negative");
    const id: AccountId = accountId(randomUUID());
    const account = new CreditAccount(id, 0n, AccountFactory.LIMITS[tier], 0);
    if (openingDepositMinor > 0n) account.credit(openingDepositMinor, `opening:${id}`, now);
    return account;
  }
}
```

## 5. Repositories

One repository per aggregate root, expressed in domain terms, returning whole aggregates. Persistence details (SQL, ORM, document store) stay in infrastructure. Use a version number for optimistic concurrency.

```ts
// file: account-repository.ts
import type { AccountId } from "./ids.js";
import type { CreditAccount } from "./credit-account.js";

export class ConcurrencyError extends Error {}

export interface AccountRepository {
  findById(id: AccountId): Promise<CreditAccount | null>;
  /**
   * Persists the aggregate and its pending events in one transaction.
   * Rejects with ConcurrencyError when the stored version differs from expectedVersion.
   */
  save(account: CreditAccount, expectedVersion: number): Promise<void>;
}
```

Implementation sketch for SQL: `UPDATE accounts SET balance = $1, version = version + 1 WHERE id = $2 AND version = $3`; zero rows updated means a concurrent change, so throw `ConcurrencyError`. Insert the events into an outbox table in the same transaction.

Query-oriented needs (lists, reports, search) are not repository methods on the write model; use a read model or a query service returning DTOs.

## 6. Domain services

A domain service holds a domain operation that does not naturally belong to one entity or value object. It is stateless and named in the language of the domain. Dependencies are ports passed in or arguments.

```ts
// file: pricing-policy.ts
import { DomainError } from "./value-objects.js";

export type Tier = "standard" | "premium";

export interface PricingInput {
  readonly subtotalMinor: bigint;
  readonly tier: Tier;
  readonly orderCountLast12Months: number;
}

export class PricingPolicy {
  /** Discount in basis points (1 bp = 0.01%). */
  discountBasisPoints(input: PricingInput): number {
    if (input.subtotalMinor < 0n) throw new DomainError("Negative subtotal");
    let bp = 0;
    if (input.tier === "premium") bp += 500;
    if (input.orderCountLast12Months >= 10) bp += 250;
    if (input.subtotalMinor >= 100_000n) bp += 100;
    return Math.min(bp, 1000);
  }

  apply(input: PricingInput): bigint {
    const bp = BigInt(this.discountBasisPoints(input));
    return input.subtotalMinor - (input.subtotalMinor * bp) / 10_000n;
  }
}
```

If the logic needs only one aggregate's data, make it a method on that aggregate instead.

## 7. Specifications

A specification is a named, testable business predicate that can be combined. Use it for validation and selection rules that appear in several places.

```ts
// file: specification.ts
export interface Specification<T> {
  isSatisfiedBy(candidate: T): boolean;
}

export abstract class BaseSpecification<T> implements Specification<T> {
  abstract isSatisfiedBy(candidate: T): boolean;
  and(other: Specification<T>): Specification<T> {
    return new BaseFn((c) => this.isSatisfiedBy(c) && other.isSatisfiedBy(c));
  }
  or(other: Specification<T>): Specification<T> {
    return new BaseFn((c) => this.isSatisfiedBy(c) || other.isSatisfiedBy(c));
  }
  not(): Specification<T> {
    return new BaseFn((c) => !this.isSatisfiedBy(c));
  }
}

class BaseFn<T> extends BaseSpecification<T> {
  constructor(private readonly fn: (c: T) => boolean) {
    super();
  }
  isSatisfiedBy(candidate: T): boolean {
    return this.fn(candidate);
  }
}

export interface Invoice {
  readonly dueDate: Date;
  readonly paid: boolean;
  readonly amountMinor: bigint;
}

export class Overdue extends BaseSpecification<Invoice> {
  constructor(private readonly now: Date) {
    super();
  }
  isSatisfiedBy(i: Invoice): boolean {
    return !i.paid && i.dueDate < this.now;
  }
}

export class LargeAmount extends BaseSpecification<Invoice> {
  isSatisfiedBy(i: Invoice): boolean {
    return i.amountMinor >= 1_000_000n;
  }
}

// Usage: new Overdue(now).and(new LargeAmount()).isSatisfiedBy(invoice)
```

Specifications evaluated in memory are for domain rules. For large data sets, translate the idea into a query in a read model rather than loading every aggregate to filter in memory.

## 8. Domain events

An event records something that happened. It is immutable, named in past tense, and carries an id, time, aggregate id and the data consumers need.

- Raise events inside the aggregate (collect them), publish after commit. Publishing inside the aggregate method couples the domain to infrastructure and fires events for transactions that later roll back.
- Domain events inside a context may be rich. Integration events that cross contexts are a published language: keep them stable, small, versioned (`type` plus `schemaVersion`), and free of internal ids that leak the model.
- Consumers are idempotent: deduplicate by `eventId` or by a natural key.
- Do not use an event as a remote procedure call: an event announces a fact and does not expect a particular reaction.

## 9. Application services

An application service implements one use case. It authenticates and authorizes the caller, loads aggregates, calls domain methods, saves, and triggers publication. It contains no business rules.

```ts
// file: transfer-service.ts
import type { AccountId } from "./ids.js";
import { ConcurrencyError, type AccountRepository } from "./account-repository.js";

export interface Clock {
  now(): Date;
}

export interface Authorizer {
  canDebit(actorId: string, account: AccountId): Promise<boolean>;
}

export class DebitAccountHandler {
  constructor(
    private readonly accounts: AccountRepository,
    private readonly auth: Authorizer,
    private readonly clock: Clock,
  ) {}

  async execute(cmd: { actorId: string; accountId: AccountId; amountMinor: bigint; reference: string }): Promise<void> {
    if (!(await this.auth.canDebit(cmd.actorId, cmd.accountId))) throw new Error("Forbidden");
    for (let attempt = 1; ; attempt++) {
      const account = await this.accounts.findById(cmd.accountId);
      if (!account) throw new Error("Account not found");
      const version = account.loadedVersion;
      account.debit(cmd.amountMinor, cmd.reference, this.clock.now());
      try {
        await this.accounts.save(account, version);
        return;
      } catch (e) {
        if (!(e instanceof ConcurrencyError) || attempt >= 3) throw e;
      }
    }
  }
}
```

Keep transaction handling in one place (a unit-of-work wrapper or a decorator around handlers) rather than in each service. Return identifiers or small result objects, not aggregates, to the caller.

## 10. Consistency across aggregates

Pattern for "move money between two accounts" without a transaction spanning both:

1. Command `StartTransfer` creates a `Transfer` aggregate (or a process manager) in state `requested`.
2. A handler debits the source account; `AccountDebited` is published.
3. A policy reacts to `AccountDebited` and credits the target account; `AccountCredited` is published.
4. The transfer completes on `AccountCredited`; on failure a compensating credit is issued to the source and the transfer is marked failed.

Each step is idempotent through the `reference` shown above. See [cqrs-event-sourcing.md](cqrs-event-sourcing.md) for process managers and the outbox.

## 11. Entities inside aggregates

Child entities have local identity unique within the aggregate and are reached only through the root. If outside code needs to refer to a child, pass the root id plus the local id. If children need independent lifecycles, concurrent edits or unbounded growth, promote them to their own aggregates referencing the parent id.

## 12. Mapping to persistence

- Map the aggregate to storage in the repository; the domain class does not carry ORM annotations. Use a separate persistence model or a mapper when the ORM forces constraints on the class shape.
- Value objects map to embedded columns or JSON; ids map to native key types.
- Reconstitution (loading) bypasses creation rules that depend on "now" or on external policy: use a dedicated restore constructor or factory, so loading old data never fails on newer rules.
- Never expose the persistence model to the application layer's callers.
