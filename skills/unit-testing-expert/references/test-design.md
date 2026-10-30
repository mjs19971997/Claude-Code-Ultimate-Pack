# Unit Test Design: Doubles, Builders, Properties, Mutation

Verified against fast-check 4.10.2, Vitest 5.0.5, Jest 30.5.2 and Stryker 10.1.1 (`@stryker-mutator/core`, `jest-runner`, `vitest-runner`) (2026-10). Companion to [../SKILL.md](../SKILL.md). Code is TypeScript; fast-check examples were executed under both runners.

## Test doubles in practice

| Double | Purpose | Typical tool |
|---|---|---|
| Dummy | Fills a required parameter that is never used | `{} as Mailer` |
| Stub | Returns canned data so the unit can proceed | `vi.fn().mockResolvedValue(x)` / `jest.fn().mockResolvedValue(x)` |
| Spy | Records how a real or stub function was called | `vi.spyOn(obj, 'm')`, `jest.spyOn(obj, 'm')` |
| Fake | Working, simplified implementation | In-memory repository, fake clock, local file system |
| Mock | Stub with built-in expectations | Prefer explicit `expect(fn).toHaveBeenCalledWith(...)` after the act step |

Guidelines:
- Verify state (return value, stored data) first; verify calls only for outgoing effects that cannot be observed otherwise (message published, email sent, audit entry written).
- Stub queries (calls that return data); mock commands (calls that cause effects). Asserting on stubbed queries couples tests to implementation.
- Do not mock what you own and can construct cheaply (value objects, pure helpers). Do mock slow, nondeterministic or external boundaries.
- A fake must honor the same contract as the real adapter. Run one shared test table against both (the real one in an integration suite).

```typescript
type User = { id: string; name: string };

interface UserRepo { find(id: string): Promise<User | undefined>; save(user: User): Promise<void> }

class InMemoryUserRepo implements UserRepo {
  private rows = new Map<string, User>();
  async find(id: string) { return this.rows.get(id); }
  async save(user: User) { this.rows.set(user.id, structuredClone(user)); }
}
```

## Seams for time, randomness and I/O

```typescript
type Clock = { now(): Date };
type Rng = () => number;                         // returns [0, 1)

export function issueToken(clock: Clock, rng: Rng, ttlMs: number) {
  return { value: Math.floor(rng() * 1e9).toString(36), expiresAt: new Date(clock.now().getTime() + ttlMs) };
}

// test
const token = issueToken({ now: () => new Date('2026-01-01T00:00:00Z') }, () => 0.5, 60_000);
expect(token.expiresAt.toISOString()).toBe('2026-01-01T00:01:00.000Z');
```

Production code passes `{ now: () => new Date() }` and a cryptographically secure source where tokens matter (`crypto.randomBytes`), not `Math.random()`. When injection is impractical use fake timers (`vi.useFakeTimers` / `jest.useFakeTimers`) and `setSystemTime`.

## Test data builders

```typescript
type Order = { id: string; customerId: string; lines: { sku: string; qty: number; unitCents: number }[]; status: 'open' | 'paid' };

export function anOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 'order-1',
    customerId: 'customer-1',
    lines: [{ sku: 'sku-1', qty: 1, unitCents: 1000 }],
    status: 'open',
    ...overrides,
  };
}

test('paid orders cannot be cancelled', () => {
  expect(() => cancel(anOrder({ status: 'paid' }))).toThrow('already paid');
});
```

Defaults must be valid; each test overrides only what it is about. Generate unique ids with `crypto.randomUUID()` only when uniqueness matters, so failures stay reproducible.

## Property-based testing with fast-check

`fast-check` generates many inputs, then shrinks a failing input to a minimal counterexample. Use `fc.assert(fc.property(...arbitraries, predicate))` inside a normal test; it works in Jest and Vitest alike.

```typescript
import fc from 'fast-check';

test('a discount never raises the total', () => {
  fc.assert(
    fc.property(
      fc.array(fc.record({ sku: fc.string({ minLength: 1 }), unitCents: fc.nat(100_000), qty: fc.nat(100) })),
      fc.integer({ min: 0, max: 100 }),
      (items, percent) => totalCents(items, percent) <= totalCents(items),
    ),
  );
});
```

Good properties:
- Round trip: `decode(encode(x))` equals `x`.
- Invariants: totals are non-negative, sorting keeps length, ids stay unique.
- Idempotence: normalizing twice equals normalizing once.
- Oracle: the optimized implementation equals a simple reference implementation.
- Monotonicity or ordering relations between inputs and outputs.

Tips: constrain generators to valid domain values (`fc.nat`, `fc.integer({ min, max })`, `fc.record`, `fc.constantFrom`), keep predicates fast, commit reproduced counterexamples as ordinary example tests, and use the printed seed (`fc.assert(prop, { seed })`) to reproduce a failure.

## Mutation testing

Line coverage says code ran; mutation testing says whether a test fails when the code changes.

```bash
npm i -D @stryker-mutator/core @stryker-mutator/vitest-runner   # or @stryker-mutator/jest-runner
npx stryker init
npx stryker run
```

```json
{
  "testRunner": "vitest",
  "mutate": ["src/**/*.ts", "!src/**/*.test.ts"],
  "coverageAnalysis": "perTest",
  "reporters": ["clear-text", "html"],
  "thresholds": { "high": 80, "low": 60, "break": 50 }
}
```

(Keys `testRunner`, `mutate`, `coverageAnalysis` with values `off`, `all`, `perTest`, `reporters`, `thresholds`, `incremental` exist in the Stryker 10 schema; `npx stryker init` writes a config that matches your versions.) Run it on critical modules or changed files, not on every commit; surviving mutants point to missing assertions or untested branches. `break` fails the run when the score drops below it.

## Common unit-test smells

- Logic in tests (loops, conditionals) that can itself be wrong.
- Fragile tests that break on refactors because they assert call order or private state.
- Giant tests that check many behaviors; split them.
- Shared mutable fixtures; build fresh data per test.
- Hidden test dependencies: ordering, wall-clock time, locale, time zone (pin `TZ` in the test script if needed), environment variables.
- Over-mocking: every collaborator mocked, so refactors break tests and bugs pass.
- Asserting only that something "did not throw" when a result is available to check.
- Snapshot tests nobody reads; keep them small and review diffs.
