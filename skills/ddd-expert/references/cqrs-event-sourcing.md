# CQRS and Event Sourcing

Reference for deciding on and implementing CQRS, event sourcing, projections, the outbox and process managers in a DDD model, with TypeScript code. Verified against Greg Young's CQRS documents, Martin Fowler's CQRS and Event Sourcing articles, Vernon, Implementing Domain-Driven Design (2013) and TypeScript 7.0 with `strict`; every code block in this file was type-checked (2026-10). Blocks marked `// file:` form one small project.

## 1. When to use what

CQRS (Command Query Responsibility Segregation) and event sourcing are independent. You can have CQRS with a plain relational write model, and event sourcing without separate read stores (rare).

| Situation | Choice |
|---|---|
| CRUD with simple screens | Plain model, no CQRS |
| Read shapes differ strongly from the write model, or reads and writes scale very differently | CQRS with read models (projections or query views) |
| History is business data: audit trail, temporal queries, "what did we know on date X", ledger-like rules | Event sourcing for that aggregate |
| Need to rebuild new views from history | Event sourcing (or an event log kept for this purpose) |
| Team has no experience with eventual consistency and projections | Start without; add CQRS where the pain is |

Costs to accept: eventual consistency between write and read sides, event versioning for the life of the system, projection rebuilds, more moving parts, harder ad hoc queries on the write side, and erasure complexity. Apply it per aggregate or per context, not system-wide.

## 2. Command side and query side

- Commands express intent (`PlaceOrder`), are validated, handled by one aggregate, and may be rejected. They return an acknowledgment or an id, not data for display.
- Queries read from a model shaped for the consumer and never change state.
- The read side can be a view in the same database, a table maintained by event handlers, a search index, or a cache. Choose the lightest thing that works.
- The UI must tolerate staleness: show "processing", read-your-writes by returning the new version in the command response and waiting for the projection to reach it, or route the first read after a write to the write side.

## 3. Event-sourced aggregate

State is derived by folding events. Commands produce new events after checking invariants against the current state. The aggregate keeps uncommitted events until the store appends them with an expected version.

```ts
// file: event-sourcing.ts
export class DomainError extends Error {}
export class WrongExpectedVersion extends Error {}

export interface StoredEvent {
  readonly streamId: string;
  readonly version: number; // 1-based position within the stream
  readonly type: string;
  readonly schemaVersion: number;
  readonly data: Readonly<Record<string, unknown>>;
  readonly occurredAt: string; // ISO-8601
}

export interface EventStore {
  load(streamId: string): Promise<StoredEvent[]>;
  /** Appends atomically; throws WrongExpectedVersion when the stream length differs from expectedVersion. */
  append(streamId: string, expectedVersion: number, events: Omit<StoredEvent, "streamId" | "version">[]): Promise<void>;
}

type CartEvent =
  | { type: "CartOpened"; customerId: string }
  | { type: "ItemAdded"; sku: string; quantity: number }
  | { type: "CartCheckedOut" };

export class Cart {
  private opened = false;
  private checkedOut = false;
  private items = new Map<string, number>();
  private version = 0;
  private uncommitted: CartEvent[] = [];

  constructor(readonly id: string) {}

  static open(id: string, customerId: string): Cart {
    const cart = new Cart(id);
    cart.raise({ type: "CartOpened", customerId });
    return cart;
  }

  static rehydrate(id: string, history: readonly CartEvent[]): Cart {
    const cart = new Cart(id);
    for (const e of history) {
      cart.apply(e);
      cart.version++;
    }
    return cart;
  }

  addItem(sku: string, quantity: number): void {
    if (!this.opened) throw new DomainError("Cart is not open");
    if (this.checkedOut) throw new DomainError("Cart already checked out");
    if (!Number.isInteger(quantity) || quantity < 1) throw new DomainError("Invalid quantity");
    this.raise({ type: "ItemAdded", sku, quantity });
  }

  checkOut(): void {
    if (this.checkedOut) return; // idempotent
    if (this.items.size === 0) throw new DomainError("Cannot check out an empty cart");
    this.raise({ type: "CartCheckedOut" });
  }

  get expectedVersion(): number {
    return this.version;
  }

  takeUncommitted(): CartEvent[] {
    const events = this.uncommitted;
    this.uncommitted = [];
    return events;
  }

  private raise(event: CartEvent): void {
    this.apply(event);
    this.uncommitted.push(event);
  }

  /** Pure state transition: never throws and never checks rules; rules live in the command methods. */
  private apply(event: CartEvent): void {
    switch (event.type) {
      case "CartOpened":
        this.opened = true;
        break;
      case "ItemAdded":
        this.items.set(event.sku, (this.items.get(event.sku) ?? 0) + event.quantity);
        break;
      case "CartCheckedOut":
        this.checkedOut = true;
        break;
    }
  }
}

export async function saveCart(store: EventStore, cart: Cart, now: Date): Promise<void> {
  const pending = cart.takeUncommitted();
  if (pending.length === 0) return;
  await store.append(
    `cart-${cart.id}`,
    cart.expectedVersion,
    pending.map(({ type, ...data }) => ({ type, schemaVersion: 1, data, occurredAt: now.toISOString() })),
  );
}
```

Notes:

- `apply` only mutates state. A rule check inside `apply` would break replays of old events after the rule changes.
- The stream id includes the aggregate type (`cart-<id>`) so ids from different aggregates never collide.
- Optimistic concurrency comes from `expectedVersion`; on `WrongExpectedVersion`, reload, re-run the command and retry (or fail if the command is no longer valid).
- Real stores add global ordering (a position) for projections and subscriptions. Existing options include EventStoreDB (KurrentDB), PostgreSQL tables with a sequence, or a cloud log; check the current docs for the product you choose.

## 4. Projections (read models)

A projection subscribes to events and updates a read model. Make it idempotent and resumable.

```ts
// file: projection.ts
export interface Checkpointed {
  readonly position: number;
}

export interface ItemAddedData {
  readonly sku: string;
  readonly quantity: number;
}

export interface ReadStore {
  /** Runs fn in one transaction together with the checkpoint update. */
  transaction<T>(fn: (tx: TxStore) => Promise<T>): Promise<T>;
  checkpoint(name: string): Promise<number>;
}

export interface TxStore {
  upsertCartItem(cartId: string, sku: string, deltaQuantity: number): Promise<void>;
  setCheckpoint(name: string, position: number): Promise<void>;
}

export interface GlobalEvent {
  readonly position: number; // global, strictly increasing
  readonly streamId: string;
  readonly type: string;
  readonly data: Readonly<Record<string, unknown>>;
}

export class CartItemsProjection {
  static readonly NAME = "cart-items";

  constructor(private readonly store: ReadStore) {}

  async handle(event: GlobalEvent): Promise<void> {
    await this.store.transaction(async (tx) => {
      const last = await this.store.checkpoint(CartItemsProjection.NAME);
      if (event.position <= last) return; // already applied: safe on redelivery
      if (event.type === "ItemAdded") {
        const data = event.data as unknown as ItemAddedData;
        await tx.upsertCartItem(event.streamId.replace(/^cart-/, ""), data.sku, data.quantity);
      }
      await tx.setCheckpoint(CartItemsProjection.NAME, event.position);
    });
  }
}
```

Projection practices:

- Store the checkpoint in the same transaction as the read-model change, so a crash cannot apply an event twice or skip it.
- A projection must be rebuildable: keep the handler pure with respect to the event stream, version it, and rebuild into a new table, then switch over.
- Replays must not trigger side effects (emails, payments). Side effects belong to separate reactors that track their own deduplication.
- Monitor lag (latest event position minus checkpoint) per projection.

## 5. Schema evolution and upcasting

Stored events are immutable. Evolve by adding optional fields and, when meaning changes, by introducing a new schema version and converting on read.

```ts
// file: upcast.ts
import type { StoredEvent } from "./event-sourcing.js";

type Upcaster = (event: StoredEvent) => StoredEvent;

// v1 stored { sku, qty }; v2 stores { sku, quantity }
const itemAddedV1toV2: Upcaster = (e) => {
  const { qty, ...rest } = e.data as { qty?: number } & Record<string, unknown>;
  return { ...e, schemaVersion: 2, data: { ...rest, quantity: qty ?? 1 } };
};

const upcasters: Record<string, Record<number, Upcaster>> = {
  ItemAdded: { 1: itemAddedV1toV2 },
};

export function upcast(event: StoredEvent): StoredEvent {
  let current = event;
  for (;;) {
    const next = upcasters[current.type]?.[current.schemaVersion];
    if (!next) return current;
    current = next(current);
  }
}
```

Rules: never rewrite history in place unless doing a controlled migration; keep old versions readable; test upcasters against stored samples of every old version.

## 6. Snapshots

When streams grow long (rule of thumb: thousands of events and rehydration latency visible), store a snapshot (state plus the version it covers) every N events. Load the latest snapshot, then fold events after its version. A snapshot is an optimization and must be discardable and regenerable from events. Version the snapshot schema; discard on mismatch.

## 7. Outbox and integration events

To publish events reliably without a distributed transaction, write the event rows to an outbox table in the same transaction as the aggregate change, and run a relay that publishes them and marks them sent. Delivery is at least once.

```ts
// file: outbox.ts
export interface OutboxRow {
  readonly id: string;
  readonly topic: string;
  readonly payload: string;
}

export interface OutboxStore {
  /** Claims up to `limit` unsent rows, e.g. SELECT ... FOR UPDATE SKIP LOCKED in PostgreSQL. */
  claim(limit: number): Promise<OutboxRow[]>;
  markSent(ids: string[]): Promise<void>;
}

export interface Publisher {
  publish(topic: string, key: string, payload: string): Promise<void>;
}

export async function relayOnce(store: OutboxStore, publisher: Publisher): Promise<number> {
  const rows = await store.claim(100);
  const sent: string[] = [];
  for (const row of rows) {
    try {
      await publisher.publish(row.topic, row.id, row.payload); // row id doubles as a dedupe key
      sent.push(row.id);
    } catch {
      break; // keep order; retry the rest next tick
    }
  }
  if (sent.length > 0) await store.markSent(sent);
  return sent.length;
}
```

Consumers deduplicate on the message id (a table of processed ids with a unique constraint, committed in the same transaction as their effect). Translate internal domain events into a stable integration event (published language) before they leave the context.

## 8. Process managers and sagas

A process manager keeps the state of a long-running process that spans aggregates or contexts. It reacts to events, sends commands, and handles timeouts and failures with compensations.

```ts
// file: transfer-process.ts
export type TransferState = "requested" | "debited" | "completed" | "failed";

export type TransferEvent =
  | { type: "TransferRequested"; transferId: string; from: string; to: string; amountMinor: bigint }
  | { type: "AccountDebited"; transferId: string }
  | { type: "AccountCredited"; transferId: string }
  | { type: "DebitRejected"; transferId: string };

export type Command =
  | { type: "DebitAccount"; accountId: string; amountMinor: bigint; reference: string }
  | { type: "CreditAccount"; accountId: string; amountMinor: bigint; reference: string };

export class TransferProcess {
  private state: TransferState = "requested";

  constructor(
    private readonly transferId: string,
    private readonly from: string,
    private readonly to: string,
    private readonly amountMinor: bigint,
  ) {}

  /** Returns the commands to dispatch; the reference makes each command idempotent. */
  on(event: TransferEvent): Command[] {
    switch (event.type) {
      case "TransferRequested":
        return [{ type: "DebitAccount", accountId: this.from, amountMinor: this.amountMinor, reference: `${this.transferId}:debit` }];
      case "AccountDebited":
        if (this.state !== "requested") return [];
        this.state = "debited";
        return [{ type: "CreditAccount", accountId: this.to, amountMinor: this.amountMinor, reference: `${this.transferId}:credit` }];
      case "AccountCredited":
        this.state = "completed";
        return [];
      case "DebitRejected":
        this.state = "failed";
        return [];
    }
  }

  get current(): TransferState {
    return this.state;
  }
}
```

Persist the process state (or event-source it), set timeouts for steps that never answer, and decide compensations explicitly (refund, release reservation). Orchestration versus choreography trade-offs and broker infrastructure belong to microservices-expert.

## 9. Erasure and privacy in event stores

An append-only log conflicts with deletion duties such as GDPR erasure. Options:

- Keep personal data out of events: store a reference id, keep the data in a mutable store that can be deleted.
- Crypto-shredding: encrypt personal fields per data subject, keep the key in a key store, delete the key to render the data unreadable.
- Stream rewrite as a last resort, run as a controlled migration with approval.

Decide this before the first event is stored; it is very hard to retrofit.

## 10. Testing event-sourced code

Use given/when/then on events:

- Given: a history of past events rehydrates the aggregate.
- When: call a command method.
- Then: assert the uncommitted events (or the thrown `DomainError`).

Projections are tested by feeding event sequences, including duplicates and gaps, and asserting on the read model and checkpoint. Contract-test upcasters with recorded real events of each historic version.
