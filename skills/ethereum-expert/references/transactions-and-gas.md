# Transactions and Gas

Reference for transaction formats, the gas model, the EIP-1559 and blob fee markets, nonces, and EIP-7702 processing. Verified against ethereum/EIPs (EIP-155, 2718, 2930, 1559, 4844, 7594, 7623, 7691, 7702, 7825, 7918), the Osaka execution-specs gas constants and the Fusaka BPO blob schedule (2026-10).

## 1. Transaction envelope and types

EIP-2718 defines a typed envelope: `TransactionType || TransactionPayload`, where the type byte is below `0x7f`. A legacy transaction is a bare RLP list.

| Type | EIP | Adds | Fee fields |
|---|---|---|---|
| `0x00` legacy | 155 | Replay protection: `v = 35 + 2 * chainId + parity` (or 27/28 without chain id, avoid) | `gasPrice` |
| `0x01` | 2930 | `accessList` of `[address, [storageKeys]]` | `gasPrice` |
| `0x02` | 1559 | Base fee market | `maxPriorityFeePerGas`, `maxFeePerGas` |
| `0x03` | 4844 | Blobs: `max_fee_per_blob_gas`, `blob_versioned_hashes` | as `0x02` plus blob fee |
| `0x04` | 7702 | `authorization_list`, sets EOA code | as `0x02` |

Payload field order (from the EIPs):

```
0x02: rlp([chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list, signature_y_parity, signature_r, signature_s])
0x03: rlp([chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, to, value, data, access_list, max_fee_per_blob_gas, blob_versioned_hashes, y_parity, r, s])
0x04: rlp([chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, value, data, access_list, authorization_list, signature_y_parity, signature_r, signature_s])
authorization_list = [[chain_id, address, nonce, y_parity, r, s], ...]
```

- The signature covers `keccak256(type || rlp(payload fields without signature))`.
- Types `0x03` and `0x04` cannot create contracts: `to` must be a 20-byte address.
- The receipt carries `type`, `status` (1 success, 0 failure, EIP-658), `cumulativeGasUsed`, `logs`, `logsBloom`, `effectiveGasPrice`, `contractAddress` (for creations) and, for blob transactions, `blobGasUsed`.
- `effectiveGasPrice = baseFeePerGas + min(maxFeePerGas - baseFeePerGas, maxPriorityFeePerGas)`.

## 2. Intrinsic gas and calldata

Constants taken from the Osaka execution-specs and the EIPs:

| Item | Gas |
|---|---|
| Transaction base | 21000 |
| Contract creation (transaction with no `to`, or `CREATE`/`CREATE2`) | +32000 |
| Initcode | 2 per 32-byte word (EIP-3860); initcode limit 49152 bytes |
| Code deposit | 200 per byte of deployed code; limit 24576 bytes (EIP-170) |
| Calldata, standard | 4 per zero byte, 16 per non-zero byte |
| Calldata floor (EIP-7623) | 10 per token, where a zero byte is 1 token and a non-zero byte is 4 tokens (so 10 and 40 per byte) |
| Access list | 2400 per address, 1900 per storage key |
| EIP-7702 authorization | 25000 per tuple (`PER_EMPTY_ACCOUNT_COST`), 12500 refunded if the authority account already exists |

EIP-7623: gas used is at least `21000 + 10 * tokens` (the floor), even when execution is cheap; otherwise the standard calldata cost plus execution applies. A transaction whose gas limit is below `21000 + 10 * tokens` is invalid, so wallets and `eth_estimateGas` must account for the floor.

Transaction gas cap (EIP-7825, Fusaka): a single transaction may use at most 16,777,216 (2^24) gas, independent of the block gas limit. Large batch operations and big deployments must be split.

Gas limit per block: validators signal changes; a block may change the limit by at most 1/1024 of the parent's. EIP-7935 (informational) records the 60M default for clients after Fusaka. Read the live value from the latest block header.

## 3. Execution gas that matters in practice

| Operation | Gas |
|---|---|
| Cold account access (`CALL`, `BALANCE`, `EXTCODE*`) | 2600 (warm: 100) |
| Cold `SLOAD` | 2100 (warm: 100) |
| `SSTORE` zero to non-zero | 20000 (plus 2100 if cold) |
| `SSTORE` non-zero to non-zero (cold slot) | 5000 total; 2900 if the slot was already warm |
| Refund for clearing a slot | 4800; total refunds are capped at one fifth of gas used (EIP-3529) |
| `CALL` with value | +9000, +25000 if the target account is new, 2300 stipend to the callee |
| `LOG0` to `LOG4` | 375 + 375 per topic + 8 per data byte |
| `KECCAK256` | 30 + 6 per word |
| `TLOAD`, `TSTORE` | 100 each (EIP-1153) |
| Memory | 3 per word plus a quadratic expansion term |
| `ecrecover` precompile | 3000 |
| `P256VERIFY` precompile at `0x100` (EIP-7951) | 6900 |
| KZG point evaluation precompile at `0x0a` | 50000 |

Gas forwarding on calls follows the 63/64 rule (EIP-150): a call can forward at most 63/64 of the remaining gas. A callee that needs more fails even when the caller specified a larger gas value.

## 4. EIP-1559 fee market

```
gas_target       = gas_limit // 2                 (ELASTICITY_MULTIPLIER = 2)
next_base_fee    = base_fee + base_fee * (gas_used - gas_target) // gas_target // 8
                   (denominator BASE_FEE_MAX_CHANGE_DENOMINATOR = 8; an increase is at least 1 wei)
priority_fee     = min(maxPriorityFeePerGas, maxFeePerGas - base_fee)
paid_per_gas     = base_fee + priority_fee         (burn: base_fee; proposer: priority_fee)
```

- A full block raises the next base fee by 12.5%; an empty block lowers it by 12.5%.
- A transaction is includable only when `maxFeePerGas >= base_fee` of the block that includes it. Set `maxFeePerGas` to roughly `2 * nextBaseFee + tip` to survive several full blocks (the code is in the main skill).
- The sender's balance must cover `gas_limit * maxFeePerGas + value` (plus the blob fee cap for type `0x03`) at inclusion time, even though less is charged.
- Unused gas is refunded at the effective price; the burn applies to gas actually used.
- Use `eth_feeHistory(blockCount, newestBlock, rewardPercentiles)`: `baseFeePerGas` has `blockCount + 1` entries (the last is the next block's), `gasUsedRatio` and `reward` have `blockCount` entries, and `baseFeePerBlobGas` and `blobGasUsedRatio` cover blobs.

## 5. Blob transactions and the blob fee market

- One blob is 4096 field elements of 32 bytes: 131,072 bytes (128 KiB), priced as `GAS_PER_BLOB = 2^17` blob gas.
- Blob gas is a separate resource: `blob_fee = blob_gas_used * blob_base_fee`, paid from the sender's balance and burned. The sender sets `max_fee_per_blob_gas`. Execution gas and blob gas are independent in the transaction.
- Blob base fee: `fake_exponential(MIN_BASE_FEE_PER_BLOB_GAS = 1, excess_blob_gas, BLOB_BASE_FEE_UPDATE_FRACTION)`. Excess blob gas accumulates when blocks use more blob gas than the target and decays when they use less.
- EIP-7918 (Fusaka) adds a reserve price: when `BLOB_BASE_COST (2^13) * base_fee_per_gas` exceeds `GAS_PER_BLOB * blob_base_fee`, the excess grows by a fraction of used blob gas instead of subtracting the target. In effect the blob base fee cannot stay at 1 wei while execution gas is expensive.
- Parameters by fork (target and max blobs per block; update fraction), from the consensus config and the Geth defaults:

| Fork | Mainnet activation (UTC) | Target | Max | Update fraction |
|---|---|---|---|---|
| Cancun (EIP-4844) | 2024-03-13 | 3 | 6 | 3338477 |
| Prague/Electra (EIP-7691) | 2025-05-07 | 6 | 9 | 5007716 |
| BPO1 (Fusaka schedule, EIP-7892) | 2025-12-09 | 10 | 15 | 8346193 |
| BPO2 | 2026-01-07 | 14 | 21 | 11684671 |

Read the live schedule with `eth_config`; clients also expose `blobSchedule` in their chain configuration (EIP-7840).

- Versioned hash: `0x01 || sha256(kzg_commitment)[1:]`. The EVM sees only hashes via the `BLOBHASH` opcode (`0x49`); blob contents are not readable by contracts. `BLOBBASEFEE` (EIP-7516) returns the current blob base fee. The point evaluation precompile at `0x0a` verifies a KZG proof against a versioned hash.
- Network wrapper: blob data is carried beside the transaction in the transaction pool. Since Fusaka (EIP-7594) the wrapper is `rlp([tx_payload_body, wrapper_version, blobs, commitments, cell_proofs])` with `wrapper_version = 1`, and the sender computes the cell proofs. A transaction may carry at most 6 blobs.
- Blob data is pruned by consensus nodes after about 18 days (`MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS = 4096` epochs). Applications that need the data later must store it.
- Replacement: Geth's blob pool requires a 100% fee bump to replace a blob transaction; its regular pool requires 10%.

## 6. Nonces, ordering and replacement

- A sender's transactions execute in strict nonce order. A gap holds all later nonces in the queued (non-executable) pool.
- Nonce is capped at 2^64 - 1 (EIP-2681).
- Replace a stuck transaction by sending the same nonce with higher fees (at least the client's bump; Geth's default is 10% on both fee fields). To cancel, send a zero-value self-transfer with the same nonce and higher fees. The original can still win if it is included first.
- Query `eth_getTransactionCount(address, "pending")` for the next nonce including mempool transactions of that node, and `"latest"` for the confirmed count. In a multi-process sender, keep nonce allocation in one component.
- Geth's default pool limits per account are small (16 executable slots by default), so do not queue deep chains of nonces on one node.
- Dropped transactions (evicted from the pool, node restart, fee below the base fee for too long) produce no receipt; `eth_getTransactionByHash` returns `null` on nodes that no longer hold them.

## 7. EIP-7702 set-code transactions

Rules from the EIP text (live since Pectra, Final):

1. `SET_CODE_TX_TYPE = 0x04`, `MAGIC = 0x05`. The authorization message is `keccak256(0x05 || rlp([chain_id, address, nonce]))`, signed by the authorizing account (the "authority").
2. The transaction is invalid if `authorization_list` is empty. Each tuple is processed before execution but after the sender's nonce is incremented.
3. Per tuple: skip it (without failing the transaction) unless `chain_id` is 0 or the current chain, `nonce < 2^64 - 1`, `s <= secp256k1n / 2`, the authority's code is empty or already a delegation, and the authority's current nonce equals the tuple's `nonce`. Valid tuples add the authority to the accessed addresses, set its code to `0xef0100 || address` (the delegation indicator) and increment its nonce.
4. If the tuple's `address` is the zero address, the account's code is cleared instead, which removes the delegation.
5. When several tuples have the same authority, the last valid one wins.
6. Delegation is not rolled back if the rest of the transaction reverts.
7. If the sender authorizes itself in the same transaction, its tuple nonce must equal the transaction nonce plus 1, because the sender nonce is incremented first.
8. Code-executing operations (`CALL`, `CALLCODE`, `DELEGATECALL`, `STATICCALL`, and a transaction whose destination is the account) follow the pointer and run the target's code in the authority's context. `EXTCODESIZE` of a delegated account returns 23; `CODESIZE` and `CODECOPY` act on the executing code.
9. A pointer to another delegation is not followed: clients read only the first hop. A delegation to a precompile executes empty code.
10. Accounts with a delegation indicator may originate transactions (EIP-3607 is relaxed for exactly that code pattern).
11. Cost: the transaction pays `25000` per tuple whether valid or not; a refund of 12500 applies for authorities that already existed. A cold delegated target adds 2600 gas (warm: 100).

## 8. Practical formulas

```
maxCost (type 0x02)       = gas_limit * maxFeePerGas + value
maxCost (type 0x03)       = gas_limit * maxFeePerGas + blob_gas * max_fee_per_blob_gas + value
actual cost (type 0x02)   = gas_used * effectiveGasPrice + value
priority fee per gas      = effectiveGasPrice - baseFee
burned ETH                = gas_used * baseFee  (+ blob_gas_used * blob_base_fee)
```

- Plan a minimum balance per sending key as `N * maxCost` for the number of transactions in flight, plus a margin for fee spikes.
- When a transaction fails with "intrinsic gas too low", the cause is usually calldata floor (EIP-7623) or access list or authorization costs not included in the limit; recompute with the tables above.
- When `eth_estimateGas` succeeds but the transaction runs out of gas, the usual causes are state that changed between estimation and inclusion, 63/64 forwarding to a callee that needs a fixed amount, or refunds counted in the estimate; add headroom and simulate again at the intended block.
