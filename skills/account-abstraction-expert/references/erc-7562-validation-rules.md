# ERC-7562 Validation Rules

What validation code (account `validateUserOp`, factory deployment, paymaster `validatePaymasterUserOp`, aggregator) may do so that bundlers in the shared mempool accept it, and how to stay compliant. ERC-7562 is in Review; the rule IDs and constants below come from the current text and can change, so check the specification before relying on a specific value.

## Why the rules exist

A bundler simulates each UserOperation before accepting it and again before including it. If validation could depend on state that another transaction can change cheaply (a timestamp, a balance, a shared storage slot), an attacker could make thousands of pending operations invalid at once and make the bundler pay for failed bundles. The rules limit validation to inputs that only the operation's own entities control, and use stake and reputation to bound the damage from entities that need more.

## Phases and entities

- Phases: factory deployment (if `initCode` is set), account validation, paymaster validation. Execution (`callData`, `postOp`) is not restricted by these rules.
- Entities: `sender` (account), `factory`, `paymaster`, `aggregator`. An entity is staked when its EntryPoint stake is at least `MIN_STAKE_VALUE` (per chain) with an unstake delay of at least `MIN_UNSTAKE_DELAY` (86,400 seconds).

## Opcode rules

- **OP-011**: banned during validation: `ORIGIN`, `GASPRICE`, `BLOCKHASH`, `COINBASE`, `TIMESTAMP`, `NUMBER`, `PREVRANDAO`, `GASLIMIT`, `BASEFEE`, `BLOBHASH`, `BLOBBASEFEE`, `INVALID`, `SELFDESTRUCT`, `CREATE` (except as allowed below), and newer environment opcodes listed in the specification.
- **OP-012**: `GAS` only when immediately followed by a `*CALL`.
- **OP-020**: reverting with out-of-gas is forbidden.
- **OP-031**: `CREATE2` exactly once, in the deployment frame, to deploy the sender.
- **OP-041**: no `EXTCODE*` or `*CALL` to addresses without code (except the sender during deployment).
- **OP-051 to OP-055**: the EntryPoint may be called only for `depositTo`, `incrementNonce` from the sender, its fallback from the sender, or checked with `EXTCODESIZE`.
- **OP-061**: `CALL` with value is forbidden except to the EntryPoint.
- **OP-062**: only accepted precompiles: the core set `0x1` to `0x11` and `P256VERIFY` (EIP-7951).
- **OP-070**: transient storage (`TLOAD`, `TSTORE`) follows the same rules as persistent storage.
- **OP-080**: `BALANCE` and `SELFBALANCE` only from a staked entity.
- **COD-010**: code of any address touched must not change between the first and second simulation.

## Storage rules

- **STO-010**: the account's own storage is always accessible.
- **STO-021, STO-022**: storage associated with the account in another contract (for example `balanceOf[sender]` in a token, a mapping keyed by the sender address) is accessible if the account exists, or if the factory is staked.
- **STO-031 to STO-033**: a staked paymaster or factory may access its own storage, storage associated with itself in other contracts, and read any storage in non-entity contracts.
- **STO-040, STO-041** (local rules): an address used as an entity in one operation may not be the sender of another in the mempool, and associated storage may not belong to another pending sender.

"Associated" storage with address `A` is a slot whose value is `A`, or a slot computed as `keccak256(A || x) + n` with a `bytes32` value `x` and `n` from 0 to 128. Solidity mappings keyed by address (and structs stored in them) fall under this definition.

## Reputation and limits

| Constant | Value in the current text |
|---|---|
| `SAME_SENDER_MEMPOOL_COUNT` | 4 operations per unstaked sender |
| `SAME_UNSTAKED_ENTITY_MEMPOOL_COUNT` | 10 operations referencing one unstaked entity (grows with inclusion rate) |
| `MAX_VERIFICATION_GAS` | 500,000 per verification limit |
| `VALIDATION_GAS_SLACK` | 4,000 above measured validation usage |
| `PRE_VERIFICATION_OVERHEAD_GAS` | 50,000 |
| `MAX_USEROP_SIZE` | 8,192 bytes |
| `MAX_CONTEXT_SIZE` | 2,048 bytes per paymaster context |
| `MAX_BUNDLE_SIZE` | 262,144 bytes |

- Entities that fail after passing simulation are throttled and then banned (`GREP-*` rules); a banned paymaster or factory stops all operations that use it.
- **EREP-040**: aggregators must be staked.
- **EREP-050**: an unstaked paymaster may not return a context, so it cannot use `postOp`.
- **EREP-010**: bundlers track the total gas a paymaster's pending operations may cost against its deposit.

## EIP-7702 authorizations

- **AUTH-010**: at most one authorization tuple per operation.
- **AUTH-020, AUTH-030**: a delegated EOA may only be the sender, and may only be called or inspected when it is the sender of the current operation.
- **AUTH-040**: pending operations from one sender with authorizations must all use the same delegate.

## Staying compliant

- Account validation: verify a signature over `userOpHash`, check the nonce policy, pay the prefund. Read only the account's storage. Return validity windows instead of reading time.
- Signers stored in other contracts (validator modules) must store data keyed by the account address so the access counts as associated storage.
- Passkey accounts: use `P256VERIFY` where available (accepted under OP-062) and a pure Solidity fallback otherwise; avoid calls to arbitrary verifier contracts without code-hash stability.
- Paymasters: verify an off-chain signature and return data; if you need `postOp`, token balances or oracle reads, stake the paymaster and keep reads within STO-031 to STO-033.
- Factories: deploy exactly the sender with `CREATE2`; stake the factory if the account's initialization touches associated storage elsewhere.
- Test with a bundler's validation tracer (most bundlers expose a safe mode or debug tracing that applies these rules) and treat any violation as a release blocker.

## Alternative mempools

Operations that break a canonical rule may still be accepted by bundlers that subscribe to an alternative mempool with different rules (ALT-* rules). Using one ties the account or paymaster to the bundlers that serve that mempool; prefer the canonical rules unless the product requires otherwise.
