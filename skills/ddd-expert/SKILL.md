---
name: ddd-expert
description: >-
  Models complex business domains with Domain-Driven Design: strategic design (subdomains, bounded contexts, context maps, ubiquitous language, Event Storming) and tactical patterns (entities, value objects, aggregates and invariants, domain events, repositories, domain services, factories, specifications, application services), with guidance on when CQRS and event sourcing pay off and how to build an anti-corruption layer. Examples are in TypeScript. Use when drawing context boundaries, designing or reviewing aggregates, naming domain concepts, running an Event Storming workshop, or untangling an anemic or god-object model. Not for layering and dependency rules (use clean-architecture-expert) or service decomposition, deployment and inter-service infrastructure (use microservices-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# DDD Expert

This skill covers Domain-Driven Design as a modeling discipline: finding where the business complexity lives, drawing explicit boundaries around models, and expressing the rules of the core domain in code that uses the business's own language. It spans strategic design (subdomains, bounded contexts, context mapping) and tactical design (aggregates, value objects, domain events, repositories), and states honestly when a simpler design is the better one.

> Verified against Eric Evans, Domain-Driven Design (2003) and Domain-Driven Design Reference (2015); Vaughn Vernon, Implementing Domain-Driven Design (2013) and Effective Aggregate Design; Alberto Brandolini, Introducing EventStorming; TypeScript 7.0 with `strict` (examples type-checked, target ES2022) (2026-10).

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

- Covered: subdomain classification, bounded contexts, context mapping patterns, ubiquitous language and glossaries, Event Storming, entities, value objects, aggregates and invariants, aggregate sizing, domain events, repositories, domain services, factories, specifications, application services, anti-corruption layers, and the decision whether to use CQRS or event sourcing.
- Not covered: layering and dependency direction between modules (clean-architecture-expert), splitting a system into deployable services, messaging infrastructure, sagas as infrastructure (microservices-expert), table design and ORM mapping details (postgresql-expert, prisma-expert).
- DDD pays off where the domain is complex and changing. For CRUD-shaped subdomains, a transaction script or an active-record style is the right tool, and the model should say so explicitly.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Subdomains | Core (competitive advantage, build and invest), supporting (needed but not differentiating, build simply), generic (commodity such as identity, billing, email, buy or adopt) |
| Bounded context | Boundary inside which one model and one ubiquitous language hold; the same word may mean different things in two contexts and that is fine |
| Context map | Partnership, shared kernel, customer/supplier, conformist, anti-corruption layer, open host service, published language, separate ways; big ball of mud marks a legacy area |
| Entity | Identity and lifecycle; equality by id, state changes through intention-revealing methods |
| Value object | Immutable, equality by value, self-validating, side-effect-free operations (`Money`, `DateRange`, `Email`) |
| Aggregate | Cluster of entities and value objects with one root; the unit of transactional consistency and of loading and saving |
| Domain event | Immutable fact in past tense (`OrderPlaced`) with id and timestamp; used inside a context and, after translation, across contexts |
| Repository | Collection-like port for one aggregate root; loads and saves whole aggregates; implementation lives in infrastructure |
| Domain service | Stateless operation that does not belong to one entity or value object (a transfer between two accounts, a pricing policy) |
| Application service | Use-case orchestration: load, call the domain, save, publish; holds no business rules |
| Event Storming | Workshop on a wall of sticky notes: domain events first, then commands, actors, policies, aggregates, external systems, hot spots; formats are big picture, process level and design level |
| CQRS / event sourcing | Separate write and read models; store events as the source of truth. Independent options, each with real cost |

## 3. Workflow

1. Gather vocabulary from domain experts in their words (documents, support tickets, interviews). Start a glossary per context.
2. Run a big-picture Event Storming: orange domain events on a timeline, resolve duplicates and conflicting names, mark hot spots. Where one word carries two meanings or two teams disagree, a context boundary is likely.
3. Classify subdomains as core, supporting or generic. Spend modeling effort on the core; buy or keep generic parts simple.
4. Draw bounded contexts and a context map with the relationship type for each pair (who is upstream, who conforms, where a translation layer is needed).
5. For each core context, run a process-level or design-level session: commands, policies, read models, and the invariants that must always hold. Invariants define aggregates.
6. Implement aggregates with behavior, not setters; raise events from the root; define repository ports; write the application service for each use case.
7. Test the domain model with plain unit tests (no database, no framework), then adapter tests for repositories and anti-corruption layers.
8. Revisit the model when language drifts or a rule is awkward to express; refactor toward the better concept and update the glossary.

## 4. Decision Rules

- Use the full tactical toolkit only in core subdomains. Supporting subdomains usually need a simple model; generic subdomains should be bought or reused.
- Choose value object over entity unless the concept needs identity over time. Most concepts that look like entities (addresses, prices, periods) are value objects.
- Draw an aggregate boundary around a true invariant that must be consistent in one transaction ("order total never exceeds the credit limit"). If no invariant spans two objects, they are separate aggregates.
- Keep aggregates small: often a root plus a few value objects. Reference other aggregates by id, never by object reference.
- One transaction normally changes one aggregate. Cross-aggregate rules are eventually consistent through domain events. This is a strong default, not a law: modify two aggregates in one transaction only for a deliberate reason (for example a single-database migration step), and document it.
- Put logic in the aggregate first; use a domain service only when the operation spans several aggregates or needs a policy object; use an application service only for orchestration.
- Do not share a database schema between contexts. Integrate through events, APIs or a published language, and translate at the boundary.
- Use an anti-corruption layer when the upstream model is legacy, external, or unstable; conform (take their model as is) only when it is good enough and cheap.
- Event sourcing is warranted when the history itself is business data (audit trail, temporal queries, undo, accounting-style ledgers). CQRS is warranted when read and write shapes or load differ strongly. Use neither as a default.
- Names beat patterns: if the code uses a word the domain experts do not, fix the code or fix the glossary.

## 5. Coding Standards

- Name types and methods in the ubiquitous language of their context: `order.place()`, not `order.setStatus("PLACED")`.
- Value objects are immutable (`readonly` fields, no setters) and validate in the factory or constructor; invalid values cannot exist.
- Entities and aggregates expose behavior methods that check invariants and then change state. Public fields and setters are limited to the identity and read access.
- Make illegal states unrepresentable: discriminated unions or state objects rather than a status string plus nullable fields.
- Domain code imports no framework, ORM, HTTP or messaging types. Time and ids come in through parameters or small interfaces (`Clock`, `IdGenerator`) so tests are deterministic.
- Use branded id types (`OrderId`, `CustomerId`), and throw `DomainError` subclasses that the application layer maps to responses.
- Money uses integer minor units (`bigint` or integer) or a decimal library, never floating point.
- Events are plain immutable data with a past-tense name and the data a consumer needs; version them when they leave the context.
- Domain events are collected by the aggregate and published by the application layer after the aggregate is saved (or via an outbox), not fired from inside the aggregate to external systems.

## 6. Project Structure

One module (or package) per bounded context; layer folders inside it. Dependency direction rules are covered by clean-architecture-expert.

```
src/
├── ordering/                      # bounded context
│   ├── domain/
│   │   ├── order.ts               # aggregate root
│   │   ├── order-line.ts          # entity or value object inside the aggregate
│   │   ├── money.ts               # value object
│   │   ├── order-events.ts        # OrderPlaced, OrderCancelled
│   │   ├── order-repository.ts    # port (interface)
│   │   └── pricing-policy.ts      # domain service
│   ├── application/
│   │   ├── place-order.ts         # command + handler (application service)
│   │   └── order-summary-query.ts # read side
│   ├── infrastructure/
│   │   ├── pg-order-repository.ts
│   │   └── outbox-publisher.ts
│   └── index.ts                   # public API of the context: commands, queries, published events
├── shipping/                      # another context with its own model
│   └── acl/billing-translator.ts  # anti-corruption layer for a foreign model
└── docs/
    ├── context-map.md
    └── glossary-ordering.md
```

## 7. Design Patterns

- **Aggregate root with intention-revealing methods**: all changes go through the root, which enforces invariants and records events.
- **Factory**: a static method or class that builds a valid aggregate when construction is complex or needs policy (`Order.create(...)`, `Shipment.fromOrder(...)`).
- **Specification**: a named, composable predicate for selection or validation (`OverdueInvoice`, `EligibleForDiscount`), usable in memory and, when needed, translated to a query.
- **Domain service**: stateless policy or operation across aggregates (`TransferService`, `PricingPolicy`).
- **Repository per aggregate root** with `findById`, `save` (optimistic concurrency via a version number), and query methods named in domain terms.
- **Domain event + outbox**: store events in the same transaction as the aggregate, a relay publishes them, consumers are idempotent.
- **Anti-corruption layer**: a translator and adapter that turns a foreign model into your domain types; nothing foreign leaks past it.
- **Open host service / published language**: expose a stable, documented, versioned contract to many consumers instead of negotiating per consumer.
- **Process manager / saga**: coordinates a long-running, multi-aggregate or multi-context process by reacting to events and issuing commands.
- **Read model (CQRS)**: a projection built from events or from the write store for a specific screen or report.
- Full catalogs: [references/strategic-design.md](references/strategic-design.md), [references/tactical-patterns.md](references/tactical-patterns.md), [references/cqrs-event-sourcing.md](references/cqrs-event-sourcing.md).

## 8. Best Practices

- Keep the glossary in the repository next to the code and review it with domain experts; treat a naming disagreement as a modeling bug.
- Model behavior first (what can happen, what must never happen), data second. Start from commands and events, not tables.
- Size aggregates by contention and invariants: if two users often edit different parts at once, the aggregate is too large.
- Prefer eventual consistency between aggregates and make the delay explicit in the UX and in the language ("order is being confirmed").
- Draw the context map early, keep it current, and mark team ownership next to each context.

## 9. Performance

- Loading one aggregate by id should be one or two queries. If it needs many, the aggregate is too big or the access path is wrong.
- Do not load aggregates to answer queries that span many of them; use a read model, a projection, or a direct query returning DTOs.
- Large child collections in an aggregate (thousands of lines, comments, transactions) signal a wrong boundary. Make the children their own aggregates keyed by the parent id.
- Optimistic concurrency (version column, compare-and-set) scales better than long locks; retry on conflict at the application service.
- Event-sourced aggregates with long streams need snapshots; projections need rebuild tooling and a way to catch up.

## 10. Security

- Authorization is not a domain rule unless the business defines it that way. Check permissions in the application service (who may call this use case), and keep domain rules such as "only the account holder can close it" in the model when they are business policy.
- Keep personal and secret data out of domain events that leave the context. Publish the minimum, reference by id, and consider encrypting or omitting sensitive fields.
- Validate and normalize input at the boundary into value objects (email, IBAN, identifiers); never trust a raw string inside the domain.
- Anti-corruption layers are also trust boundaries: validate foreign payloads, cap sizes, and do not pass them through untranslated.
- Tenant identity belongs in aggregate identity and in every repository read and write, not only in queries.
- Event stores are append-only histories: plan for erasure obligations (store personal data outside the stream, or encrypt per subject and delete the key).

## 11. Testing

- Unit-test aggregates through behavior: given prior events or state, when a command method is called, then expect the new state, events or a domain error. No mocks are needed.
- Test each invariant with a case that violates it and a boundary case that just satisfies it.
- Test application services with in-memory repositories and a fake clock; assert on saved aggregates and published events.
- Contract tests for the anti-corruption layer with recorded foreign payloads, including malformed ones.
- Integration tests for the repository against the real database check mapping, optimistic concurrency and the outbox transaction.

## 12. Review Checklist

- [ ] Names in code match the glossary; no `Manager`, `Helper`, `Data` classes hiding concepts.
- [ ] Each aggregate protects a stated invariant; the root is the only entry point.
- [ ] Aggregates reference each other by id; collections inside are bounded.
- [ ] Value objects are immutable and validate themselves; ids are typed.
- [ ] No setters or public mutable state on aggregates; methods express business operations.
- [ ] One use case changes one aggregate, or the exception is documented.
- [ ] Domain code has no framework, database or HTTP imports.
- [ ] Events are past-tense facts, immutable, published after commit or via an outbox, and consumers are idempotent.
- [ ] Foreign models are translated at an anti-corruption layer.
- [ ] Context map and glossary exist and match the code layout.
- [ ] CQRS or event sourcing is used only with a written reason.

## 13. Production Notes

- Event schema evolution: add optional fields, never change meaning; use explicit versions and upcasters for events that are stored or shared.
- Outbox relays deliver at least once. Consumers deduplicate on event id; handlers tolerate reordering where the broker gives no order guarantee.
- Migrating a legacy system: wrap it with an anti-corruption layer, route one capability at a time to the new context (strangler approach), and retire the old model gradually.

## 14. Examples

Aggregate with invariants, a value object and a domain event. Money is stored in integer minor units, the aggregate checks its own rules, and events are collected for the application layer to publish:

```ts
import { randomUUID } from "node:crypto";

export class DomainError extends Error {}

export class Money {
  private constructor(
    readonly minor: bigint,
    readonly currency: string,
  ) {}

  static of(minor: bigint, currency: string): Money {
    if (!/^[A-Z]{3}$/.test(currency)) throw new DomainError(`Invalid currency: ${currency}`);
    if (minor < 0n) throw new DomainError("Money cannot be negative");
    return new Money(minor, currency);
  }

  add(other: Money): Money {
    this.assertSameCurrency(other);
    return new Money(this.minor + other.minor, this.currency);
  }

  times(quantity: number): Money {
    if (!Number.isSafeInteger(quantity) || quantity < 0) throw new DomainError("Quantity must be a non-negative integer");
    return new Money(this.minor * BigInt(quantity), this.currency);
  }

  private assertSameCurrency(other: Money): void {
    if (other.currency !== this.currency) throw new DomainError("Currency mismatch");
  }
}

export interface OrderPlaced {
  readonly type: "OrderPlaced";
  readonly eventId: string;
  readonly occurredAt: Date;
  readonly orderId: string;
  readonly customerId: string;
  readonly totalMinor: string; // bigint serialized as string for JSON
  readonly currency: string;
}

interface Line {
  readonly sku: string;
  readonly unitPrice: Money;
  readonly quantity: number;
}

type State = "draft" | "placed" | "cancelled";

export class Order {
  static readonly MAX_LINES = 50;
  private readonly lines: Line[] = [];
  private state: State = "draft";
  private readonly events: OrderPlaced[] = [];

  private constructor(
    readonly id: string,
    readonly customerId: string,
    readonly currency: string,
    private version: number,
  ) {}

  static start(customerId: string, currency: string): Order {
    return new Order(randomUUID(), customerId, currency, 0);
  }

  addLine(sku: string, unitPrice: Money, quantity: number): void {
    if (this.state !== "draft") throw new DomainError("Only a draft order can be changed");
    if (unitPrice.currency !== this.currency) throw new DomainError("Line currency differs from order currency");
    if (quantity < 1) throw new DomainError("Quantity must be at least 1");
    const existing = this.lines.findIndex((l) => l.sku === sku);
    if (existing >= 0) {
      const line = this.lines[existing]!;
      this.lines[existing] = { ...line, quantity: line.quantity + quantity };
    } else {
      if (this.lines.length >= Order.MAX_LINES) throw new DomainError("Too many lines");
      this.lines.push({ sku, unitPrice, quantity });
    }
  }

  total(): Money {
    return this.lines.reduce((sum, l) => sum.add(l.unitPrice.times(l.quantity)), Money.of(0n, this.currency));
  }

  place(now: Date): void {
    if (this.state !== "draft") throw new DomainError("Order was already placed or cancelled");
    if (this.lines.length === 0) throw new DomainError("An order needs at least one line");
    this.state = "placed";
    const total = this.total();
    this.events.push({
      type: "OrderPlaced",
      eventId: randomUUID(),
      occurredAt: now,
      orderId: this.id,
      customerId: this.customerId,
      totalMinor: total.minor.toString(),
      currency: total.currency,
    });
  }

  /** Called by the repository after a successful save. */
  pullEvents(): OrderPlaced[] {
    return this.events.splice(0, this.events.length);
  }

  get currentVersion(): number {
    return this.version;
  }
}
```

Repository port with optimistic concurrency and an application service that orchestrates one use case. A command handler loads, calls the domain, saves; the repository stores events in the same transaction (outbox):

```ts
export interface OrderRepository {
  /** Returns null when the order does not exist. */
  findById(id: string): Promise<LoadedOrder | null>;
  /** Throws ConcurrencyError when expectedVersion is stale. Saves pending events atomically (outbox). */
  save(order: LoadedOrder, expectedVersion: number): Promise<void>;
}

export class ConcurrencyError extends Error {}
export class NotFoundError extends Error {}

// Minimal shape used by the handler; the real type is the Order aggregate.
export interface LoadedOrder {
  readonly id: string;
  readonly currentVersion: number;
  place(now: Date): void;
}

export interface Clock {
  now(): Date;
}

export interface PlaceOrderCommand {
  readonly orderId: string;
  readonly commandId: string; // idempotency key
}

export class PlaceOrderHandler {
  constructor(
    private readonly orders: OrderRepository,
    private readonly clock: Clock,
  ) {}

  async execute(cmd: PlaceOrderCommand): Promise<void> {
    const order = await this.orders.findById(cmd.orderId);
    if (!order) throw new NotFoundError(`Order ${cmd.orderId} not found`);
    const version = order.currentVersion;
    order.place(this.clock.now());
    // On ConcurrencyError the caller (or a retry decorator) reloads and re-runs the command.
    await this.orders.save(order, version);
  }
}
```

Anti-corruption layer that translates a legacy payment provider response into the ordering context's own type. Unknown values fail loudly instead of leaking through:

```ts
interface LegacyPaymentDto {
  txn_status: string; // "00" | "05" | "51" | ...
  amt: string;        // decimal string in major units, e.g. "12.50"
  ccy: string;
  ref: string;
}

export type PaymentOutcome =
  | { kind: "authorized"; reference: string; amountMinor: bigint; currency: string }
  | { kind: "declined"; reference: string; reason: "insufficient-funds" | "refused" };

export class PaymentTranslationError extends Error {}

export function toPaymentOutcome(dto: LegacyPaymentDto): PaymentOutcome {
  if (!/^[A-Z]{3}$/.test(dto.ccy)) throw new PaymentTranslationError("Unknown currency");
  if (dto.ref.length === 0 || dto.ref.length > 64) throw new PaymentTranslationError("Bad reference");
  switch (dto.txn_status) {
    case "00":
      return { kind: "authorized", reference: dto.ref, amountMinor: parseMinor(dto.amt), currency: dto.ccy };
    case "51":
      return { kind: "declined", reference: dto.ref, reason: "insufficient-funds" };
    case "05":
      return { kind: "declined", reference: dto.ref, reason: "refused" };
    default:
      throw new PaymentTranslationError(`Unmapped status ${dto.txn_status}`);
  }
}

function parseMinor(major: string): bigint {
  const m = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(major);
  if (!m) throw new PaymentTranslationError("Bad amount");
  return BigInt(m[1]! + (m[2] ?? "").padEnd(2, "0"));
}
```

## 15. Common Mistakes

- **Anemic model**: entities as data bags with getters and setters and all rules in services. Move behavior into aggregates; services orchestrate.
- **God aggregate**: `Customer` containing orders, addresses, payments and tickets. Split by invariant and reference by id.
- **Aggregate chosen from the database schema or the object graph** rather than from invariants.
- **Object references across aggregates** that pull in half the database on load and blur transaction boundaries.
- **One shared model for the whole company**: a single `Customer` that serves sales, billing and support. Give each context its own model and translate.
- **Repository per table or per entity**, or a repository that returns partial aggregates. Repositories are per aggregate root and return whole aggregates.
- **Domain events used as RPC or as change-data-capture of columns**: events state business facts, not row updates.
- **Event sourcing everywhere** because it is fashionable, with no need for history: costs in versioning, projections and operations without matching benefit.
- **Domain layer importing ORM decorators or HTTP types**, which makes unit tests need a database.
- **Setters named for the business** (`setStatus("PLACED")`) that skip the checks. Expose `place()` and keep the transition rules inside.
- **DDD ceremony in a CRUD subdomain**: factories, specifications and events for a settings screen. Reserve the toolkit for the core.

## 16. References

- [references/strategic-design.md](references/strategic-design.md): subdomain classification, finding bounded contexts, all context-map relationships with when to use each, ubiquitous language and glossary practice, Event Storming formats and notation, evolving a legacy system.
- [references/tactical-patterns.md](references/tactical-patterns.md): entities, value objects, aggregate design rules and sizing, factories, repositories, domain services, specifications, domain events, application services, concurrency, TypeScript code.
- [references/cqrs-event-sourcing.md](references/cqrs-event-sourcing.md): when CQRS and event sourcing are justified, event-sourced aggregate in TypeScript, projections, snapshots, upcasting, outbox and idempotency, process managers, erasure.
- Official docs: https://www.domainlanguage.com/ddd/reference/ , https://www.eventstorming.com/ , https://www.dddcommunity.org/library/vernon_2011/ , https://martinfowler.com/bliki/BoundedContext.html
