# Layering and the Dependency Rule in TypeScript

A worked "place an order" slice that shows what each layer contains, what may cross a boundary and how the pieces are wired. The code targets TypeScript 5.x or later in strict mode, Node.js 22, `pg` 8, Express 5 and Zod 4. Each block starts with a `// file:` marker naming its path under `src/`. Tenant isolation applies to writes as well as reads, so every repository method carries the tenant.

## Contents
1. [The rule in one paragraph](#1-the-rule-in-one-paragraph)
2. [Domain layer](#2-domain-layer)
3. [Application layer](#3-application-layer)
4. [Infrastructure adapters](#4-infrastructure-adapters)
5. [HTTP adapter and composition root](#5-http-adapter-and-composition-root)
6. [Transactions across repositories](#6-transactions-across-repositories)
7. [What may cross a boundary](#7-what-may-cross-a-boundary)

## 1. The rule in one paragraph

Source-code dependencies point inward: infrastructure and delivery code import application and domain code; the application imports the domain; the domain imports only itself (and the language's standard library). When an inner layer needs something an outer layer provides (a database, a clock, an email gateway) it declares an interface in its own terms (a port) and the outer layer implements it (an adapter). Control flow still goes in and out; only the import direction is constrained. This is the dependency rule from Robert C. Martin, *Clean Architecture* (2017), and the same direction constraint appears in Cockburn's hexagonal architecture and Palermo's onion architecture.

## 2. Domain layer

Entities hold state and enforce invariants; they do not know about persistence, HTTP or frameworks.

```typescript
// file: domain/errors.ts
export class DomainError extends Error {
  constructor(readonly code: string, message: string) {
    super(message);
    this.name = 'DomainError';
  }
}
```

```typescript
// file: domain/order.ts
import { DomainError } from './errors';

export type OrderStatus = 'draft' | 'placed' | 'cancelled';

export interface OrderLine {
  readonly sku: string;
  readonly quantity: number;
  readonly unitPriceCents: number;
}

export interface OrderSnapshot {
  readonly id: string;
  readonly tenantId: string;
  readonly status: OrderStatus;
  readonly lines: readonly OrderLine[];
  readonly version: number;
}

export class Order {
  private constructor(
    readonly id: string,
    readonly tenantId: string,
    private _status: OrderStatus,
    private _lines: readonly OrderLine[],
    readonly version: number,
  ) {}

  static draft(id: string, tenantId: string): Order {
    return new Order(id, tenantId, 'draft', [], 0);
  }

  /** Rebuilds an order from stored state; the adapter calls this, business code does not. */
  static rehydrate(s: OrderSnapshot): Order {
    return new Order(s.id, s.tenantId, s.status, s.lines, s.version);
  }

  get status(): OrderStatus {
    return this._status;
  }

  get lines(): readonly OrderLine[] {
    return this._lines;
  }

  get totalCents(): number {
    return this._lines.reduce((sum, l) => sum + l.quantity * l.unitPriceCents, 0);
  }

  addLine(line: OrderLine): void {
    if (this._status !== 'draft') throw new DomainError('order_not_editable', 'Only draft orders can change');
    if (!Number.isInteger(line.quantity) || line.quantity <= 0) throw new DomainError('invalid_quantity', 'Quantity must be a positive integer');
    if (!Number.isInteger(line.unitPriceCents) || line.unitPriceCents < 0) throw new DomainError('invalid_price', 'Price must be a non-negative integer');
    const existing = this._lines.find((l) => l.sku === line.sku);
    this._lines = existing
      ? this._lines.map((l) => (l.sku === line.sku ? { ...l, quantity: l.quantity + line.quantity } : l))
      : [...this._lines, line];
  }

  place(): void {
    if (this._status !== 'draft') throw new DomainError('order_not_editable', 'Only draft orders can be placed');
    if (this._lines.length === 0) throw new DomainError('empty_order', 'An order needs at least one line');
    this._status = 'placed';
  }
}
```

## 3. Application layer

The application layer owns the use cases and the ports they need. Ports are expressed in domain vocabulary, not in SQL or HTTP terms.

```typescript
// file: application/errors.ts
export class NotFoundError extends Error {
  constructor(readonly resource: string, readonly id: string) {
    super(`${resource} ${id} not found`);
    this.name = 'NotFoundError';
  }
}

export class ConcurrencyError extends Error {
  constructor(readonly resource: string, readonly id: string) {
    super(`${resource} ${id} was changed by someone else`);
    this.name = 'ConcurrencyError';
  }
}
```

```typescript
// file: application/ports.ts
import type { Order } from '../domain/order';

export interface OrderRepository {
  /** Reads are scoped by tenant. */
  findById(tenantId: string, id: string): Promise<Order | undefined>;
  /** Inserts a new order; the tenant comes from the aggregate. */
  add(order: Order): Promise<void>;
  /** Updates an existing order only if tenant and version still match; throws ConcurrencyError otherwise. */
  save(order: Order): Promise<void>;
}

export interface IdGenerator {
  next(): string;
}
```

```typescript
// file: application/place-order.ts
import { Order } from '../domain/order';
import { NotFoundError } from './errors';
import type { IdGenerator, OrderRepository } from './ports';

export interface CreateDraftOrderCommand {
  readonly tenantId: string;
  readonly lines: readonly { sku: string; quantity: number; unitPriceCents: number }[];
}

export interface PlaceOrderCommand {
  readonly tenantId: string;
  readonly orderId: string;
}

export interface OrderView {
  readonly id: string;
  readonly status: string;
  readonly totalCents: number;
}

export class CreateDraftOrder {
  constructor(private readonly orders: OrderRepository, private readonly ids: IdGenerator) {}

  async execute(cmd: CreateDraftOrderCommand): Promise<OrderView> {
    const order = Order.draft(this.ids.next(), cmd.tenantId);
    for (const line of cmd.lines) order.addLine(line);
    await this.orders.add(order);
    return { id: order.id, status: order.status, totalCents: order.totalCents };
  }
}

export class PlaceOrder {
  constructor(private readonly orders: OrderRepository) {}

  async execute(cmd: PlaceOrderCommand): Promise<OrderView> {
    const order = await this.orders.findById(cmd.tenantId, cmd.orderId);
    if (!order) throw new NotFoundError('order', cmd.orderId);
    order.place();
    await this.orders.save(order);
    return { id: order.id, status: order.status, totalCents: order.totalCents };
  }
}
```

The use cases return a plain `OrderView` (a data structure), never the entity, so callers cannot depend on entity internals.

## 4. Infrastructure adapters

The adapter implements the port with `pg`. The `WHERE` clause of the update carries the tenant and the expected version, so the write is scoped and race-safe in one statement.

```typescript
// file: infrastructure/pg-order-repository.ts
import type { Pool } from 'pg';
import { Order, type OrderLine, type OrderStatus } from '../domain/order';
import { ConcurrencyError } from '../application/errors';
import type { OrderRepository } from '../application/ports';

interface OrderRow {
  id: string;
  tenant_id: string;
  status: OrderStatus;
  lines: OrderLine[]; // jsonb column; pg parses it
  version: number;
}

const toDomain = (row: OrderRow): Order =>
  Order.rehydrate({ id: row.id, tenantId: row.tenant_id, status: row.status, lines: row.lines, version: row.version });

export class PgOrderRepository implements OrderRepository {
  constructor(private readonly db: Pick<Pool, 'query'>) {}

  async findById(tenantId: string, id: string): Promise<Order | undefined> {
    const { rows } = await this.db.query<OrderRow>(
      'SELECT id, tenant_id, status, lines, version FROM orders WHERE tenant_id = $1 AND id = $2',
      [tenantId, id],
    );
    const row = rows[0];
    return row ? toDomain(row) : undefined;
  }

  async add(order: Order): Promise<void> {
    await this.db.query(
      'INSERT INTO orders (id, tenant_id, status, lines, version) VALUES ($1, $2, $3, $4::jsonb, 0)',
      [order.id, order.tenantId, order.status, JSON.stringify(order.lines)],
    );
  }

  async save(order: Order): Promise<void> {
    const result = await this.db.query(
      `UPDATE orders
          SET status = $1, lines = $2::jsonb, version = version + 1
        WHERE tenant_id = $3 AND id = $4 AND version = $5`,
      [order.status, JSON.stringify(order.lines), order.tenantId, order.id, order.version],
    );
    if (result.rowCount === 0) throw new ConcurrencyError('order', order.id);
  }
}
```

Other adapters follow the same shape: `SystemClock implements Clock`, `UuidGenerator implements IdGenerator` (using `randomUUID` from `node:crypto`), an SMTP or HTTP gateway implementing a `Notifier` port. A fake or in-memory adapter for tests implements the same interface.

```typescript
// file: infrastructure/uuid-generator.ts
import { randomUUID } from 'node:crypto';
import type { IdGenerator } from '../application/ports';

export class UuidGenerator implements IdGenerator {
  next(): string {
    return randomUUID();
  }
}
```

## 5. HTTP adapter and composition root

The controller translates HTTP into a command and the result into HTTP. It takes the tenant from the verified principal that the authentication middleware attached, never from the body or a client header.

```typescript
// file: delivery/http/orders-router.ts
import { Router, type ErrorRequestHandler, type Request } from 'express';
import { z } from 'zod';
import { DomainError } from '../../domain/errors';
import { ConcurrencyError, NotFoundError } from '../../application/errors';
import type { CreateDraftOrder, PlaceOrder } from '../../application/place-order';

interface Principal {
  userId: string;
  tenantId: string;
}

declare module 'express-serve-static-core' {
  interface Request {
    auth?: Principal; // set by the authentication middleware after token verification
  }
}

const createBody = z.strictObject({
  lines: z
    .array(
      z.strictObject({
        sku: z.string().min(1).max(64),
        quantity: z.number().int().positive().max(1000),
        unitPriceCents: z.number().int().nonnegative(),
      }),
    )
    .min(1)
    .max(100),
});

function principal(req: Request): Principal {
  if (!req.auth) throw Object.assign(new Error('unauthenticated'), { status: 401 });
  return req.auth;
}

export function ordersRouter(uc: { create: CreateDraftOrder; place: PlaceOrder }): Router {
  const router = Router();

  router.post('/orders', async (req, res) => {
    const p = principal(req);
    const body = createBody.parse(req.body);
    const view = await uc.create.execute({ tenantId: p.tenantId, lines: body.lines });
    res.status(201).json(view);
  });

  router.post('/orders/:id/place', async (req, res) => {
    const p = principal(req);
    const orderId = z.uuid().parse(req.params.id);
    res.json(await uc.place.execute({ tenantId: p.tenantId, orderId }));
  });

  return router;
}

/** Maps errors to responses at the edge so inner layers never see HTTP. */
export const errorMapper: ErrorRequestHandler = (err: unknown, _req, res, _next) => {
  if (err instanceof z.ZodError) return void res.status(400).json({ error: 'invalid_request' });
  if (err instanceof NotFoundError) return void res.status(404).json({ error: 'not_found' });
  if (err instanceof ConcurrencyError) return void res.status(409).json({ error: 'conflict' });
  if (err instanceof DomainError) return void res.status(422).json({ error: err.code });
  if (typeof err === 'object' && err !== null && (err as { status?: unknown }).status === 401) {
    return void res.status(401).json({ error: 'unauthenticated' });
  }
  res.status(500).json({ error: 'internal_error' });
};
```

The composition root is the only place that knows every concrete class. Keep it at the edge of the process (`main.ts`) and use constructor injection; a DI container is optional.

```typescript
// file: main.ts
import express from 'express';
import { Pool } from 'pg';
import { CreateDraftOrder, PlaceOrder } from './application/place-order';
import { PgOrderRepository } from './infrastructure/pg-order-repository';
import { UuidGenerator } from './infrastructure/uuid-generator';
import { errorMapper, ordersRouter } from './delivery/http/orders-router';

const pool = new Pool({ connectionString: process.env['DATABASE_URL'] });
const orders = new PgOrderRepository(pool);

const app = express();
app.use(express.json({ limit: '100kb' }));
// app.use(authenticate) goes here and sets req.auth from a verified token.
app.use(ordersRouter({ create: new CreateDraftOrder(orders, new UuidGenerator()), place: new PlaceOrder(orders) }));
app.use(errorMapper);
app.listen(3000);
```

## 6. Transactions across repositories

When one use case must change several aggregates atomically, keep the transaction boundary in the application layer without importing the database driver. Two common shapes:

- A `UnitOfWork` port whose `run` method receives a callback and hands it repositories bound to one transaction.
- A single aggregate per transaction, with other aggregates updated through domain events and an outbox table written in the same transaction (eventual consistency).

```typescript
// file: application/unit-of-work.ts
import type { OrderRepository } from './ports';

export interface Repositories {
  readonly orders: OrderRepository;
}

export interface UnitOfWork {
  run<T>(work: (repos: Repositories) => Promise<T>): Promise<T>;
}
```

```typescript
// file: infrastructure/pg-unit-of-work.ts
import type { Pool } from 'pg';
import type { Repositories, UnitOfWork } from '../application/unit-of-work';
import { PgOrderRepository } from './pg-order-repository';

export class PgUnitOfWork implements UnitOfWork {
  constructor(private readonly pool: Pool) {}

  async run<T>(work: (repos: Repositories) => Promise<T>): Promise<T> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await work({ orders: new PgOrderRepository(client) });
      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }
}
```

A use case then calls `this.uow.run(async ({ orders }) => { ... })`. Keep callbacks short and free of network calls to other services while the transaction is open.

## 7. What may cross a boundary

| Direction | Allowed payload | Not allowed |
|---|---|---|
| Delivery to application | Command or query object (plain data) | Express `Request`, validated-but-framework-typed objects, ORM entities |
| Application to delivery | View or result object (plain data), thrown application or domain errors | Domain entities, repository handles, `Promise<Response>` |
| Application to infrastructure | Domain objects and primitives through a port | SQL fragments, ORM query builders, driver types |
| Infrastructure to application | Domain objects built through `rehydrate` or factories, domain-level errors | Rows, driver errors, ORM models |

Convert at each boundary with a small mapper function; do not let one shape serve as row, entity and response at once.
