# Gas Optimization Reference

Gas costs and techniques for Solidity 0.8.38 on EVM versions Cancun and later (default `osaka`), verified 2026-10. Measure first: `forge test --gas-report`, `forge snapshot`, `forge snapshot --diff`.

## Contents
- [Cost table](#cost-table)
- [Storage](#storage)
- [Transient storage](#transient-storage)
- [Calldata and memory](#calldata-and-memory)
- [Control flow and arithmetic](#control-flow-and-arithmetic)
- [Errors and events](#errors-and-events)
- [Compiler settings](#compiler-settings)
- [Contract size](#contract-size)
- [Assembly](#assembly)
- [Measuring](#measuring)

## Cost table

| Operation | Gas | Source |
|---|---|---|
| Cold `SLOAD` | 2100 | EIP-2929 |
| Warm `SLOAD` | 100 | EIP-2929 |
| Cold account access (`CALL`, `BALANCE`, `EXTCODESIZE`, `EXTCODEHASH` to an untouched address) | 2600 | EIP-2929 |
| Warm account access | 100 | EIP-2929 |
| `SSTORE` zero to nonzero | 20,000 (plus 2100 if the slot is cold) | Yellow Paper, EIP-2929 |
| `TLOAD` / `TSTORE` | 100 each | EIP-1153 |
| Contract runtime size limit | 24,576 bytes | EIP-170 |
| Initcode size limit | 49,152 bytes | EIP-3860 |

Other storage write costs depend on the original and current value (EIP-2200, EIP-3529 refunds); use `forge snapshot` rather than assuming them.

## Storage

- Cache a storage variable read more than once in a local, then write once.
- Pack fields written together into one slot (`uint128 + uint128`, `address + uint96`); packing fields written independently adds masking cost for no gain.
- `constant` for compile-time values, `immutable` for constructor-set values: both avoid `SLOAD`.
- Prefer `mapping` to arrays for lookups; keep arrays only for ordered iteration, and never iterate unbounded user data on-chain.
- Skip on-chain enumeration (`ERC721Enumerable`, `EnumerableSet` for listings) and emit events for indexers.
- Do not store what can be derived or supplied in calldata and verified (Merkle proofs for allowlists via `MerkleProof`).
- Avoid redundant writes: skip the `SSTORE` when the new value equals the current one if that case is common.
- Deleting storage earns a refund only within the limits of EIP-3529; do not design around refunds.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

contract Accounting {
    error LengthMismatch();
    error Unauthorized();

    address public immutable OPERATOR;
    uint256 public total;
    mapping(address account => uint256 amount) public credits;

    constructor(address operator) {
        OPERATOR = operator;
    }

    // One read of `total`, one write; calldata arrays; loop counter in unchecked because i < len.
    function credit(address[] calldata accounts, uint256[] calldata amounts) external {
        if (msg.sender != OPERATOR) revert Unauthorized();
        uint256 len = accounts.length;
        if (len != amounts.length) revert LengthMismatch();
        uint256 sum;
        for (uint256 i; i < len;) {
            credits[accounts[i]] += amounts[i]; // checked: amounts are caller-controlled
            sum += amounts[i];
            unchecked {
                ++i;
            }
        }
        total += sum;
    }
}
```

## Transient storage

`transient` state variables (value types, 0.8.28+) live for one transaction and cost 100 gas per read or write. Use them for reentrancy locks, per-transaction flags and flash-loan style accounting. `ReentrancyGuardTransient` from OpenZeppelin packages the lock. Requires an EVM version with Cancun or later on the target chain. 0.8.34 fixed an IR code generation bug that could confuse regular and transient variables at the same layout position, so use 0.8.34 or later.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

contract Guarded {
    error Locked();

    bool transient _entered;

    modifier lock() {
        if (_entered) revert Locked();
        _entered = true;
        _;
        _entered = false;
    }

    function act() external lock {}
}
```

## Calldata and memory

- `calldata` for external array, struct, `bytes` and `string` arguments you only read; `memory` copies them.
- Memory expansion costs grow with size; avoid building large arrays in memory when a loop can process items one at a time.
- Use `bytes32` instead of `string` for short fixed identifiers.
- Prefer `abi.encodePacked` only where ambiguity cannot arise (never for hashing several dynamic values); `abi.encode` is the safe default.

## Control flow and arithmetic

- Checked arithmetic is the default; wrap in `unchecked` only where the bound is proved in the same function (loop counters bounded by `len`, subtraction after a comparison).
- Order `&&` and `||` operands so the cheaper or more likely deciding check is first (short-circuit evaluation).
- Use `++i` in loops; the saving is small, do not trade clarity for it.
- Replace division and modulo by powers of two with shifts and masks only when profiled.
- Use `Math.mulDiv` for full-precision multiply-divide instead of hand-written overflow workarounds.

## Errors and events

- Custom errors are cheaper than revert strings in deployment size and in runtime when they revert.
- Keep error parameters few and small.
- Events cost less than storage for data consumed only off-chain; indexed parameters add topics (up to three on non-anonymous events).

## Compiler settings

- Optimizer: `optimizer_runs` is the expected number of executions of each function. Low values (such as 1 to 200) favor smaller deployments; high values favor cheaper runtime at larger code size. Choose per contract and measure.
- `via_ir` enables the Yul-based pipeline, which can optimize across functions and avoid stack-too-deep; compile times are longer and output differs, so test with the exact deploy settings.
- `evm_version` must match the chain; newer versions unlock `PUSH0`, `MCOPY`, transient storage and other cheaper operations.
- Pin the compiler exactly so measured gas matches deployed bytecode.

## Contract size

- Limit is 24,576 bytes runtime and 49,152 bytes initcode. Check with `forge build --sizes`.
- Reduce: lower `optimizer_runs`, remove unused features, move logic into libraries with `internal` functions or external linked libraries, shorten revert data, split into several contracts, use custom errors.
- Do not disable size checks for production deployments.

## Assembly

- Use inline assembly only for a measured hot path or an operation Solidity cannot express (storage slot access for ERC-7201, `mcopy`, `tload`).
- Mark blocks `assembly ("memory-safe") { }` only when they respect the Solidity memory model; the older `/// @solidity memory-safe-assembly` comment is deprecated since 0.8.31.
- Prefer OpenZeppelin helpers (`StorageSlot`, `SlotDerivation`, `TransientSlot`, `Math`, `Packing`) over hand-written assembly.
- Keep assembly out of access-control and accounting logic unless covered by fuzz tests.

## Measuring

- `forge test --gas-report` for per-function averages; `forge snapshot` writes `.gas-snapshot`, and `forge snapshot --check` fails CI when numbers drift.
- Compare before and after on the same compiler settings and the same inputs; fuzz-heavy tests give noisy averages, so also write fixed-input benchmark tests.
- Track deployment size with `forge build --sizes`.
- On L2s, calldata and data-availability costs dominate: shrink calldata (packed arguments, fewer arguments) rather than micro-optimizing opcodes.
