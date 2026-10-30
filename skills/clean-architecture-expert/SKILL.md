---
name: clean-architecture-expert
description: >-
  Structures backend code so business rules do not depend on frameworks, databases or delivery mechanisms: the dependency rule, entities, use cases, ports and adapters, composition root, DTO boundaries, transaction handling, and comparisons of hexagonal, onion, clean and vertical-slice styles. Use when laying out a service in layers, deciding where logic and interfaces belong, replacing ORM or framework coupling in use cases, writing repository ports, or enforcing layer boundaries with dependency-cruiser, eslint-plugin-boundaries or ArchUnitTS. Not for strategic domain modelling, aggregates and bounded contexts (use ddd-expert), splitting into services (use microservices-expert), system-level technology choices (use solution-architect or system-design-expert), or reviewing a specific diff (use code-review-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Clean Architecture Expert

This skill covers how to arrange code inside one deployable so that policy (business rules) sits at the center and details (web framework, database driver, message broker, third-party SDKs) sit at the edge and depend on the center, never the reverse. It covers the layers, what may cross a boundary, where interfaces live, how to wire concrete classes, how to test each layer, and how to make the structure fail the build when it is violated. It treats Clean Architecture, hexagonal and onion architecture as variations on one dependency constraint and says when the extra structure is not worth it.

> Verified against TypeScript 5.x strict (also compiled with 7.0), Node.js 22, `pg` 8, Express 5, Zod 4, dependency-cruiser 18.7, eslint-plugin-boundaries 7.4, ArchUnitTS (`archunit`) 2.5, ArchUnit for Java 1.5.1 (2026-10).

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

- Covered: layering inside a service, the dependency rule, ports and adapters, use case design, DTO and entity mapping, composition root and dependency injection, transaction boundaries, error translation at the edge, architecture tests and lint rules, introducing the structure into an existing codebase, choosing between clean/hexagonal/onion and vertical slices.
- Not covered: bounded contexts, aggregates and ubiquitous language (ddd-expert); splitting a system into independently deployed services, sagas and service contracts (microservices-expert); cloud and infrastructure choices (solution-architect, system-design-expert); reviewing a pull request (code-review-expert); framework-specific details such as NestJS modules (nestjs-expert).

## 2. Core Expertise

**The dependency rule** (Martin, *Clean Architecture*): source-code dependencies point only inward. Nothing in an inner circle names anything declared in an outer circle: no class, function, variable or data format.

| Ring (inner to outer) | Contains | May import |
|---|---|---|
| Entities (domain) | Enterprise-wide rules: entities, value objects, domain services, domain errors | Itself only |
| Use cases (application) | Application-specific rules: one class or function per user intention, input and output data structures, ports | Domain |
| Interface adapters | Controllers, presenters, repository and gateway implementations, mappers | Application, domain |
| Frameworks and drivers | Web framework, ORM, database driver, SDKs, `main` | Anything inward |

Related ideas to apply:
- **Ports and adapters** (Cockburn): the core is driven through ports (inbound) and drives its dependencies through ports (outbound); an adapter translates a port to a technology. See [references/architecture-styles.md](references/architecture-styles.md).
- **Onion architecture** (Palermo): the same inward coupling with explicit domain-model, domain-service and application-service rings.
- **Boundary crossing**: data crossing a boundary is a plain structure in the shape the inner side wants. Do not pass framework requests, ORM models or entities outward.
- **Humble object**: keep code that is hard to test (rendering, SQL, HTTP) as thin as possible, and move decisions into testable code.
- **Screaming architecture**: top-level folders name the business capability, not the framework.
- **Component principles** (Martin): depend in the direction of stability (Stable Dependencies Principle); stable components should be abstract enough to extend (Stable Abstractions Principle); no cycles between components (Acyclic Dependencies Principle).

## 3. Workflow

1. Decide whether the structure is warranted (see Decision Rules). For CRUD-shaped parts, use vertical slices or simple handlers.
2. List the use cases in business language ("place order", "cancel subscription") and the actors that trigger each (HTTP, queue consumer, scheduler, CLI).
3. For each use case, sketch input data, output data and failure modes, then the domain rules it enforces, then the outside capabilities it needs (persistence, clock, ids, email, payment).
4. Put invariants on entities and value objects; put orchestration (load, call, save, publish) in the use case; declare each outside capability as a port in the application layer.
5. Write the use case test with fakes before choosing the database or framework.
6. Implement adapters for each port; write contract tests that run the same assertions against the fake and the real adapter.
7. Implement the delivery adapter (controller, consumer) that validates input, builds the command, calls the use case and maps results and errors.
8. Wire everything in the composition root.
9. Add architecture rules (import-graph checks) in the same change that introduces the layers, so the structure is protected from day one.
10. When converting existing code, move one use case at a time inward: extract the logic, introduce the port, keep behavior under tests (see refactoring-expert for the techniques).

## 4. Decision Rules

- Apply the full structure when the domain has rules that change independently of the delivery mechanism, several drivers share behavior, or infrastructure choices are expected to change. Skip it for forms-over-tables CRUD, short-lived tools and prototypes.
- Create a port when there is a real second implementation, when a fake is the right test double, or when a dependency must stay swappable (payment provider, mail provider, clock). Otherwise use the concrete class directly.
- Define the port in the layer that uses it, in that layer's vocabulary (`OrderRepository.findById`), not in the vocabulary of the implementation (`executeQuery`).
- One use case per class or function; name it by intention, not by CRUD verb unless the intention is CRUD.
- Entities enforce invariants that are always true (an order has at least one line when placed). Use cases enforce rules that depend on the application (who may do this, which feature flag is on).
- Validation split: shape and format at the delivery edge (schema parser); invariants in the domain; cross-record checks (uniqueness) in the use case backed by a database constraint.
- Return result data from use cases, not entities. Throw or return domain and application errors; map them to HTTP, gRPC or queue behavior only in the adapter.
- Keep the transaction boundary in the use case (through a unit-of-work port) or in a decorator around it, never in the controller or inside a repository method that hides it from the caller.
- Reads that serve screens or reports may bypass the domain model with a dedicated query port that returns view data directly; do not load aggregates to list things.
- Dependency injection: constructor injection with a hand-written composition root first; adopt a container only when the wiring becomes hard to maintain. Domain and use case classes must not reference the container.

## 5. Coding Standards

- Inner layers (`domain`, `application`) import no framework, ORM, driver or SDK. Enforce this in tooling, not by convention.
- Domain classes expose behavior (`order.place()`), not public mutable fields; state changes go through methods that check invariants.
- Use immutable value objects for money, quantities, identifiers and ranges; avoid raw `number` and `string` for domain concepts that carry rules.
- Money is integer minor units (or a decimal library), never floating point.
- Application ports and use cases use `readonly` inputs and return plain data (`interface` or `type` with primitive fields).
- Use `import type` for interface-only imports so erased imports cannot create runtime coupling; set `verbatimModuleSyntax` in `tsconfig.json`.
- Name by role: `PlaceOrder` (use case), `OrderRepository` (port), `PgOrderRepository` (adapter), `OrdersController` or `ordersRouter` (delivery). Keep technology names out of ports and use cases.
- Errors: a small hierarchy per layer (`DomainError` with a stable `code`, `NotFoundError`, `ConcurrencyError`); adapters catch driver errors and rethrow application-level ones.
- Do not read `process.env` or the clock directly in inner layers; inject configuration values and a `Clock` port.

## 6. Project Structure

```
src/
├── domain/                  # entities, value objects, domain services, domain errors
│   ├── order.ts
│   ├── order.test.ts        # pure unit tests, no doubles
│   └── errors.ts
├── application/             # use cases and the ports they need
│   ├── place-order.ts
│   ├── place-order.test.ts  # use case tests with fakes, next to the code
│   ├── ports.ts             # OrderRepository, IdGenerator, Clock, Notifier
│   ├── unit-of-work.ts
│   └── errors.ts
├── infrastructure/          # implementations of ports
│   ├── pg-order-repository.ts
│   ├── pg-unit-of-work.ts
│   └── uuid-generator.ts
├── delivery/                # inbound adapters
│   └── http/orders-router.ts
└── main.ts                  # composition root
test/
├── architecture.test.ts     # import-graph rules
└── contract/                # same assertions against fake and real adapters
```

For larger products, put this tree inside each business module (`src/ordering/...`, `src/billing/...`) and expose one public entry point per module. See [references/architecture-styles.md](references/architecture-styles.md).

## 7. Design Patterns

- **Use case (interactor)**: a class with one `execute(command)` method, orchestrating domain objects and ports.
- **Repository**: a port that looks like a collection of aggregates (`findById`, `add`, `save`); implemented per technology. Carry the tenant or owner in every method so reads and writes are scoped.
- **Unit of work**: a port whose `run(work)` provides repositories bound to one transaction.
- **Gateway**: a port for an external system, named for the capability (`PaymentGateway.charge`), with an adapter per provider.
- **Presenter or view model**: maps a use case result into the response shape; keep it in the delivery layer.
- **Mapper**: explicit functions between row, entity and view; no automatic mapping that hides field changes.
- **Domain events with an outbox**: the aggregate records events; the adapter writes them to an outbox table in the same transaction; a relay publishes them.
- **Anti-corruption layer**: an adapter that translates a foreign or legacy model into your domain terms so its shape does not leak inward.
- **Decorator for cross-cutting concerns**: wrap a use case or repository to add logging, metrics, caching or transactions without touching the core.
- **Composition root**: one place that instantiates adapters and use cases (`main.ts`).

## 8. Best Practices

- Start with the domain and use case tests; the database schema follows from the repository port, not the other way around.
- Keep adapters thin: translate, call, translate back. Business decisions found in an adapter move inward.
- Treat the framework as a plugin: controllers call `useCase.execute(...)`; there is no `@Injectable` or decorator import in `domain/` or `application/`.
- Prefer functions plus closures over classes where state is not needed; the dependency rule is about imports, not about OOP.
- Version use case inputs and outputs deliberately when they are exposed through a public API; internal commands can change freely.
- Keep the number of layers proportional to the problem; each extra mapping layer needs a reason.
- Record the dependency rules and the decision to use this structure in a short architecture decision record so new contributors understand the constraint.

## 9. Performance

- Mapping between row, entity and view costs little compared with I/O; optimize queries before removing layers.
- Avoid N+1 in repositories: expose batch methods (`findByIds`) or a read-model query port instead of calling `findById` in a loop.
- For list and search screens use a query port that selects only the needed columns and paginates in SQL; do not rehydrate full aggregates.
- Load aggregates by id and keep them small; large aggregates cause contention and slow rehydration.
- Hold a transaction only for the unit of work; do not make remote calls inside it.
- Use optimistic concurrency (a version column checked in the `UPDATE`) rather than long-held locks for most aggregates.

## 10. Security

- Authorization is an application concern: pass the verified principal (user id, tenant id, roles) into the command and check permission in the use case or a decorator. The controller only authenticates and extracts the principal (authentication-expert and authorization-expert cover the mechanisms).
- Derive tenant and owner from the verified principal, never from the request body; scope every repository read and write by tenant, and include the tenant in the `WHERE` clause of updates and deletes.
- Parse and bound input at the edge (strict schemas, size limits) before building the command; the domain still rejects invalid states.
- Domain and application code never see secrets or connection strings; adapters receive them from the composition root.
- Map errors at the edge so stack traces, SQL and internal ids do not leave the process (see secure-coding-expert and api-security-expert for response and object-level controls).

## 11. Testing

| Layer | Test type | Doubles |
|---|---|---|
| Domain | Fast unit tests on entities and value objects | None |
| Use cases | Unit tests with in-memory fakes of the ports | Fakes for repositories, clock, id generator; stubs for gateways |
| Adapters | Contract tests against the real technology (for example a PostgreSQL container) that also run against the fake | Real database; no mocking of the driver |
| Delivery | Request-level tests for status codes, validation and error mapping | Use cases replaced by stubs or real use cases over fakes |
| Architecture | Import-graph rules in CI | None |
| End to end | A few journeys through the real composition root | Real or containerized dependencies |

- Prefer fakes over mocks for repositories; assert on resulting state, not on call sequences.
- Run the same repository contract suite (`save then find`, tenant isolation, optimistic concurrency) against the fake and the real adapter so the fake cannot drift.
- Test tenant isolation explicitly: tenant B cannot read, update or delete tenant A's record through the repository.

## 12. Review Checklist

- [ ] `domain/` and `application/` import nothing from `infrastructure/`, `delivery/` or any framework, driver or SDK.
- [ ] Every outside dependency used by a use case is a port declared in the application layer, in domain vocabulary.
- [ ] Use cases return plain data; entities and ORM models do not cross the delivery boundary.
- [ ] Repository methods take the tenant or owner, and writes include it in the predicate.
- [ ] Invariants live on entities and value objects, not in controllers.
- [ ] Errors are translated to protocol responses only in the delivery layer.
- [ ] Transaction boundaries are explicit and contain no remote calls.
- [ ] There is a composition root and no service locator or global container in inner layers.
- [ ] Architecture tests or lint rules enforce the layers in CI.
- [ ] Every interface has a reason (second implementation, fake, swappable dependency).
- [ ] Adapters are covered by contract tests against the real technology.

## 13. Production Notes

- Keep configuration, secrets and feature flags in the composition root; build a validated config object once at startup and pass values inward.
- Add logging, metrics and tracing as decorators or at adapters and delivery, so the domain stays free of observability libraries.
- Database migrations must stay compatible with the previous release while both versions run (expand and contract); the repository adapter is where the old and new schema meet.
- Publish integration events through an outbox written in the same transaction as the state change; consumers must tolerate duplicates.
- Map infrastructure failures (timeouts, unique violations, serialization failures) to application errors in adapters so use cases can decide on retries.
- Keep the architecture tests in the default CI path; a rule that is not run on every pull request decays.

## 14. Examples

### Example 1: Entity and use case with a port

```typescript
// file: domain/stock-item.ts
export class StockError extends Error {
  constructor(readonly code: 'invalid_quantity' | 'insufficient_stock', message: string) {
    super(message);
    this.name = 'StockError';
  }
}

export class StockItem {
  constructor(
    readonly tenantId: string,
    readonly sku: string,
    private _available: number,
    readonly version: number,
  ) {}

  get available(): number {
    return this._available;
  }

  reserve(quantity: number): void {
    if (!Number.isInteger(quantity) || quantity <= 0) throw new StockError('invalid_quantity', 'Quantity must be a positive integer');
    if (quantity > this._available) throw new StockError('insufficient_stock', `Only ${this._available} available`);
    this._available -= quantity;
  }
}
```

```typescript
// file: application/reserve-stock.ts
import type { StockItem } from '../domain/stock-item';

export interface StockRepository {
  find(tenantId: string, sku: string): Promise<StockItem | undefined>;
  /** Updates only if tenant, sku and version still match; returns false when nothing was updated. */
  save(item: StockItem): Promise<boolean>;
}

export interface ReserveStockCommand {
  readonly tenantId: string;
  readonly sku: string;
  readonly quantity: number;
}

export type ReserveStockResult =
  | { readonly kind: 'reserved'; readonly remaining: number }
  | { readonly kind: 'not_found' }
  | { readonly kind: 'conflict' };

export class ReserveStock {
  constructor(private readonly stock: StockRepository) {}

  async execute(cmd: ReserveStockCommand): Promise<ReserveStockResult> {
    const item = await this.stock.find(cmd.tenantId, cmd.sku);
    if (!item) return { kind: 'not_found' };
    item.reserve(cmd.quantity); // throws StockError for rule violations; the delivery layer maps it
    const saved = await this.stock.save(item);
    return saved ? { kind: 'reserved', remaining: item.available } : { kind: 'conflict' };
  }
}
```

### Example 2: Adapter with a tenant-scoped write

```typescript
// file: infrastructure/pg-stock-repository.ts
import type { Pool } from 'pg';
import { StockItem } from '../domain/stock-item';
import type { StockRepository } from '../application/reserve-stock';

interface StockRow {
  tenant_id: string;
  sku: string;
  available: number;
  version: number;
}

export class PgStockRepository implements StockRepository {
  constructor(private readonly db: Pick<Pool, 'query'>) {}

  async find(tenantId: string, sku: string): Promise<StockItem | undefined> {
    const { rows } = await this.db.query<StockRow>(
      'SELECT tenant_id, sku, available, version FROM stock_items WHERE tenant_id = $1 AND sku = $2',
      [tenantId, sku],
    );
    const r = rows[0];
    return r ? new StockItem(r.tenant_id, r.sku, r.available, r.version) : undefined;
  }

  async save(item: StockItem): Promise<boolean> {
    const result = await this.db.query(
      `UPDATE stock_items SET available = $1, version = version + 1
        WHERE tenant_id = $2 AND sku = $3 AND version = $4`,
      [item.available, item.tenantId, item.sku, item.version],
    );
    return (result.rowCount ?? 0) === 1;
  }
}
```

### Example 3: Use case test with an in-memory fake (Vitest)

```typescript
// file: application/reserve-stock.test.ts
import { describe, expect, it } from 'vitest';
import { StockError, StockItem } from '../domain/stock-item';
import { ReserveStock, type StockRepository } from './reserve-stock';

class InMemoryStock implements StockRepository {
  private readonly rows = new Map<string, StockItem>();

  seed(item: StockItem): void {
    this.rows.set(`${item.tenantId}/${item.sku}`, item);
  }

  async find(tenantId: string, sku: string): Promise<StockItem | undefined> {
    return this.rows.get(`${tenantId}/${sku}`);
  }

  async save(item: StockItem): Promise<boolean> {
    const key = `${item.tenantId}/${item.sku}`;
    const current = this.rows.get(key);
    if (!current || current.version !== item.version) return false;
    this.rows.set(key, new StockItem(item.tenantId, item.sku, item.available, item.version + 1));
    return true;
  }
}

describe('ReserveStock', () => {
  it('reserves and reports the remaining quantity', async () => {
    const repo = new InMemoryStock();
    repo.seed(new StockItem('t1', 'sku-1', 5, 0));
    const result = await new ReserveStock(repo).execute({ tenantId: 't1', sku: 'sku-1', quantity: 2 });
    expect(result).toEqual({ kind: 'reserved', remaining: 3 });
  });

  it('does not see another tenant\'s stock', async () => {
    const repo = new InMemoryStock();
    repo.seed(new StockItem('t1', 'sku-1', 5, 0));
    const result = await new ReserveStock(repo).execute({ tenantId: 't2', sku: 'sku-1', quantity: 1 });
    expect(result).toEqual({ kind: 'not_found' });
  });

  it('rejects over-reservation with a domain error', async () => {
    const repo = new InMemoryStock();
    repo.seed(new StockItem('t1', 'sku-1', 1, 0));
    await expect(new ReserveStock(repo).execute({ tenantId: 't1', sku: 'sku-1', quantity: 2 })).rejects.toBeInstanceOf(StockError);
  });
});
```

A fuller slice (HTTP adapter, error mapper, composition root, unit of work) is in [references/dependency-rule-typescript.md](references/dependency-rule-typescript.md).

## 15. Common Mistakes

- **Anemic domain with logic in use cases or services.** Invariants drift and are duplicated. Put behavior on entities and value objects; keep use cases as orchestration.
- **ORM or driver imported in the application layer.** The use case becomes untestable without a database and the rule is broken. Route persistence through a port.
- **Returning entities or ORM models from controllers.** Clients come to depend on internals and sensitive fields leak. Map to a response shape at the edge.
- **Interfaces for everything.** One-implementation mirrors of concrete classes add noise. Introduce a port at a real seam.
- **Repository methods without the tenant, or updates without the tenant predicate.** Cross-tenant writes become possible. Make the tenant part of every method signature and every `WHERE`.
- **Tenant or user id taken from the request body.** Derive it from the verified principal.
- **Framework exceptions or HTTP status codes thrown from use cases.** The use case then depends on the framework. Throw domain or application errors and map them in the adapter.
- **Transaction opened in the controller, or remote calls inside a transaction.** Move the boundary to the use case and keep it short.
- **Folders without rules.** A `domain/` folder that imports the ORM is layered code with an architecture label. Add import-graph checks.
- **Applying the full structure to simple CRUD.** The indirection cost exceeds the benefit. Use vertical slices or plain handlers there.
- **Shared "common" or "utils" module that every layer imports.** It becomes a hidden dependency hub and cycles appear. Keep shared code small, stable and dependency-free.

## 16. References

- [references/dependency-rule-typescript.md](references/dependency-rule-typescript.md): a complete slice (entity, ports, use cases, Postgres adapter, Express 5 delivery, composition root, unit of work) and the table of what may cross each boundary.
- [references/architecture-styles.md](references/architecture-styles.md): hexagonal, onion, clean and vertical slices compared, vocabulary map, modular monolith, and when to choose which.
- [references/enforcing-boundaries.md](references/enforcing-boundaries.md): tested configurations for dependency-cruiser, eslint-plugin-boundaries and ArchUnitTS, ArchUnit for Java, monorepo boundaries, and adopting rules on legacy code.
- Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design* (2017); "The Clean Architecture" (2012 blog post).
- Alistair Cockburn, "Hexagonal architecture" (2005); Cockburn and Juan Manuel Garrido de Paz, *Hexagonal Architecture Explained* (2024).
- Jeffrey Palermo, "The Onion Architecture" (2008 article series).
- Martin Fowler, *Patterns of Enterprise Application Architecture* (2002), for repository, unit of work and service layer.
- Jimmy Bogard, writing and talks on Vertical Slice Architecture.
- eslint-plugin-boundaries documentation: https://www.jsboundaries.dev/docs/overview/
