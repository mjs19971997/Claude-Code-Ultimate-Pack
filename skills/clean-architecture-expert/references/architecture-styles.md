# Hexagonal, Onion, Clean and Vertical Slices

These styles share one constraint (business rules do not depend on delivery or infrastructure details) and differ in vocabulary, how much structure they prescribe inside the core, and how code is grouped. This file maps the vocabularies onto each other and gives rules for choosing. Examples use TypeScript 5.x and `pg` 8.

## Contents
1. [Origins and what each prescribes](#1-origins-and-what-each-prescribes)
2. [Vocabulary map](#2-vocabulary-map)
3. [Layered, and why the arrow direction matters](#3-layered-and-why-the-arrow-direction-matters)
4. [Vertical slices](#4-vertical-slices)
5. [Modular monolith as the outer shape](#5-modular-monolith-as-the-outer-shape)
6. [Choosing](#6-choosing)

## 1. Origins and what each prescribes

| Style | Source | Core idea | Prescribes inside the core? |
|---|---|---|---|
| Hexagonal (Ports and Adapters) | Alistair Cockburn, "Hexagonal architecture" (2005 article); Cockburn and Juan Manuel Garrido de Paz, *Hexagonal Architecture Explained* (2024) | The application is driven through ports by anything (UI, tests, batch) and drives its dependencies through ports; adapters translate between a port and a technology | No. It says nothing about layers inside the hexagon |
| Onion | Jeffrey Palermo, "The Onion Architecture" (2008 article series) | Concentric layers: domain model at the center, then domain services, application services, and infrastructure, UI and tests outermost; all coupling points inward | Yes: domain model, domain services, application services |
| Clean Architecture | Robert C. Martin, "The Clean Architecture" (2012 post) and *Clean Architecture* (2017) | Entities, use cases, interface adapters, frameworks and drivers; the dependency rule; the boundary between layers is crossed with simple data structures | Yes: entities and use cases; plus presenters, controllers and gateways in the adapter ring |
| Vertical Slice | Jimmy Bogard, "Vertical Slice Architecture" (2018 talks and posts) | Group code by feature or request instead of by technical layer; each slice chooses the approach that fits it | No. Each slice is free to be a transaction script or to use a rich domain model |

All four are compatible. A common production shape is a clean or hexagonal core for the part of the system with complex rules, and vertical slices for the rest.

## 2. Vocabulary map

| Concept | Hexagonal | Onion | Clean Architecture | This skill's folder |
|---|---|---|---|---|
| Business rules that exist without the application | Application core (inside the hexagon) | Domain model, domain services | Entities | `domain/` |
| One thing a user or system can do | Application service behind a driving port | Application services | Use case (interactor) with input and output boundaries | `application/` |
| Interface the core needs from the outside | Driven (secondary) port | Interface in an inner ring | Gateway interface or output boundary | `application/ports.ts` |
| Interface the outside uses to call the core | Driving (primary) port | Application service interface | Input boundary | The use case's `execute` method |
| Translates between an external technology and a port | Adapter | Outer ring implementation | Controller, presenter, gateway implementation | `delivery/`, `infrastructure/` |
| Where concrete classes are chosen and wired | Not specified | Not specified | The "Main" component | `main.ts` (composition root) |

## 3. Layered, and why the arrow direction matters

In classic three-tier layering (UI, business logic, data access) the business layer imports the data-access layer, so the domain depends on persistence and cannot be tested or reused without it. The styles above invert exactly that edge: the business layer declares what it needs and persistence implements it. The number of folders is not the point; the direction of the `import` statements is. A folder named `domain` that imports `typeorm` is layered code with an architecture label.

## 4. Vertical slices

A slice contains everything for one use case: request parsing, the operation, data access and response mapping. Cross-slice sharing is limited to small, stable utilities and, where a rich domain exists, a shared domain model.

```typescript
// file: features/orders/cancel-order/handler.ts
import type { Pool } from 'pg';

export type CancelResult = 'cancelled' | 'not_found' | 'not_cancellable';

export async function cancelOrder(
  db: Pick<Pool, 'query'>,
  cmd: { tenantId: string; orderId: string },
): Promise<CancelResult> {
  // The tenant predicate is part of the write itself.
  const update = await db.query(
    `UPDATE orders SET status = 'cancelled', version = version + 1
      WHERE tenant_id = $1 AND id = $2 AND status IN ('draft', 'placed')`,
    [cmd.tenantId, cmd.orderId],
  );
  if ((update.rowCount ?? 0) === 1) return 'cancelled';
  const exists = await db.query('SELECT 1 FROM orders WHERE tenant_id = $1 AND id = $2', [cmd.tenantId, cmd.orderId]);
  return (exists.rowCount ?? 0) > 0 ? 'not_cancellable' : 'not_found';
}
```

Suggested layout:

```
src/features/orders/
├── create-order/        # route, schema, handler, tests for one use case
├── cancel-order/
├── list-orders/
└── shared/              # only what two or more slices truly share
```

When a slice grows invariants that several slices must respect (for example order totals and state transitions), promote that logic into a domain module that the slices import, which is the same move that creates the clean core. Slices importing a pure domain module do not violate the dependency rule; the domain still imports nothing outward.

## 5. Modular monolith as the outer shape

Split the system into modules by business capability (`ordering`, `billing`, `catalog`). Each module exposes a small public API (an `index.ts`, or a package entry point) and hides the rest. Modules may talk through calls to that public API or through events. Inside a module, pick the style that fits: clean core, slices, or plain CRUD. This keeps the option of extracting a module to a service later without paying distributed-system costs up front (see microservices-expert for that decision, and ddd-expert for finding module boundaries).

Enforce the public-API rule with tooling: see [enforcing-boundaries.md](enforcing-boundaries.md).

## 6. Choosing

| Situation | Prefer |
|---|---|
| Mostly forms over tables, little behavior | Vertical slices with thin handlers; skip entities and ports |
| Complex rules, many invariants, long-lived product | Clean or hexagonal core for those rules |
| Several drivers for the same behavior (HTTP, queue consumer, CLI, scheduled job) | Ports and adapters; use cases called from each driver |
| Infrastructure expected to change (provider swap, database migration, on-premise and cloud variants) | Ports for those dependencies only |
| One team, one deployable, growing codebase | Modular monolith with enforced module boundaries |
| Prototype or short-lived tool | Keep it simple; add structure when the second driver or the first painful change appears |

Add an interface when there is a second implementation, a test seam that a fake serves better than mocking the module, or a boundary that must be kept swappable. A one-implementation interface that mirrors a concrete class adds indirection without a benefit.
