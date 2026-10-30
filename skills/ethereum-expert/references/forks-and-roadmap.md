# Forks and Roadmap

Reference for Ethereum network upgrades that changed application-visible behavior, with mainnet dates and contents. Verified against the Hardfork Meta EIPs (EIP-7568, 7569, 7600, 7607, 7773), the execution-specs upgrade pages and the consensus-specs mainnet configuration (2026-10).

## 1. Naming and activation

- Upgrades have an execution-layer (EL) name and a consensus-layer (CL) name, joined into one combined name: Dencun = Cancun + Deneb, Pectra = Prague + Electra, Fusaka = Osaka + Fulu, Glamsterdam = Amsterdam + Gloas.
- Since Shanghai, EL forks activate at a block timestamp; CL forks activate at an epoch. The two are chosen to coincide.
- Blob-Parameter-Only (BPO) forks (EIP-7892) change only blob target, max and update fraction, and are scheduled by timestamp and epoch like other forks.
- Each upgrade has a Hardfork Meta EIP that lists what shipped: EIP-7568 (Berlin to Shapella backfill), EIP-7569 (Dencun), EIP-7600 (Pectra), EIP-7607 (Fusaka), EIP-7773 (Glamsterdam).

## 2. Mainnet history

| Upgrade | Activation (UTC) | Key changes for application developers |
|---|---|---|
| London | 2021-08-05, block 12,965,000 | EIP-1559 fee market, `BASEFEE` opcode (EIP-3198), refund cap reduced (EIP-3529), contracts starting with `0xEF` rejected (EIP-3541) |
| The Merge (Paris, with Bellatrix) | 2022-09-15, terminal total difficulty 58,750,000,000,000,000,000,000 | Proof of stake (EIP-3675); `DIFFICULTY` opcode becomes `PREVRANDAO` (EIP-4399) |
| Shapella (Shanghai + Capella) | 2023-04-12 22:27:35, timestamp 1681338455, epoch 194048 | Validator withdrawals (EIP-4895), `PUSH0` (EIP-3855), initcode metering (EIP-3860), warm `COINBASE` (EIP-3651), `SELFDESTRUCT` deprecation notice (EIP-6049) |
| Dencun (Cancun + Deneb) | 2024-03-13 13:55:35, timestamp 1710338135, epoch 269568 | Blob transactions (EIP-4844), transient storage (EIP-1153), `MCOPY` (EIP-5656), `SELFDESTRUCT` only deletes in the creating transaction (EIP-6780), beacon block root in the EVM (EIP-4788), `BLOBBASEFEE` (EIP-7516) |
| Pectra (Prague + Electra) | 2025-05-07 10:05:11, timestamp 1746612311, epoch 364032 | Set-code transactions for EOAs (EIP-7702), higher max effective validator balance (EIP-7251), calldata floor cost (EIP-7623), blob target 6 and max 9 (EIP-7691), BLS12-381 precompiles (EIP-2537), block hash history in state (EIP-2935), execution-layer requests for deposits and exits (EIP-6110, 7002, 7685), committee index moved out of attestation (EIP-7549) |
| Fusaka (Osaka + Fulu) | 2025-12-03 21:49:11, timestamp 1764798551, epoch 411392, fork id `0x5167e2a6` | PeerDAS data availability sampling (EIP-7594), transaction gas cap 2^24 (EIP-7825), ModExp bounds and repricing (EIP-7823, 7883), `CLZ` opcode (EIP-7939), secp256r1 precompile (EIP-7951), blob base fee reserve price (EIP-7918), block size cap (EIP-7934), BPO forks (EIP-7892) |
| BPO1 | 2025-12-09 14:21:11, timestamp 1765290071, epoch 412672 | Blob target 10, max 15 |
| BPO2 | 2026-01-07 01:01:11, timestamp 1767747671, epoch 419072 | Blob target 14, max 21 |

Dates and timestamps come from the Hardfork Meta EIPs and the consensus-specs configuration, converted to UTC.

## 3. What changed for applications, by upgrade

### Dencun

- **EIP-4844 blobs**: rollups moved data from calldata to blobs, which lowered L2 fees. Contracts can read only blob hashes (`BLOBHASH`), not contents.
- **EIP-6780**: `SELFDESTRUCT` no longer removes code or storage unless the contract is created and destroyed in the same transaction; it still transfers the balance. Patterns that relied on destroy-and-redeploy metamorphic contracts no longer work.
- **EIP-1153**: `TLOAD` and `TSTORE` give cheap per-transaction storage; reentrancy guards can use it (OpenZeppelin ships `ReentrancyGuardTransient`).
- **EIP-5656**: `MCOPY` replaces loop-based memory copies in compiler output.
- **EIP-4788**: the beacon block root is readable from a system contract, enabling trust-minimized consensus-state proofs on the EVM.

### Pectra

- **EIP-7702**: an EOA can sign authorizations that point its code at a contract, for batching, sponsorship and scoped permissions. See [l2-and-account-abstraction.md](l2-and-account-abstraction.md).
- **EIP-7251**: validators with `0x02` withdrawal credentials can have an effective balance up to 2048 ETH while the minimum activation balance remains 32 ETH. Consolidation lowers validator counts.
- **EIP-6110, EIP-7002, EIP-7685**: validator deposits and execution-layer-triggered exits and withdrawals are carried by the execution layer through a general "requests" mechanism. Staking contracts and services use these paths.
- **EIP-7623**: calldata-heavy transactions pay a floor of 10 gas per token; wallets must estimate gas accordingly.
- **EIP-7691**: more blob capacity (target 6, max 9), with a different update fraction.
- **EIP-2935**: the last 8191 block hashes are stored in a system contract's storage, which supports stateless clients and some proofs; `BLOCKHASH` behavior is unchanged.
- **EIP-2537**: BLS12-381 precompiles enable on-chain BLS signature and pairing checks.

### Fusaka

- **EIP-7594 PeerDAS**: nodes download only a subset of blob data columns (custody) and sample the rest, which lets blob capacity grow without every node downloading every blob. Blob sidecar wrappers use cell proofs and each blob transaction is limited to 6 blobs.
- **EIP-7825**: no transaction may use more than 16,777,216 gas. Very large deployments and mega-batches must be split.
- **EIP-7883 and EIP-7823**: `MODEXP` gets higher gas costs and an upper bound of 8192 bits (1024 bytes) per input; RSA-verifying contracts see changed costs.
- **EIP-7939**: `CLZ` counts leading zero bits of a 256-bit word, available to compilers for cheaper math routines.
- **EIP-7951**: `P256VERIFY` precompile at address `0x100`, 6900 gas, enabling WebAuthn or passkey signatures to be verified cheaply on L1.
- **EIP-7918**: ties the blob base fee floor to execution gas costs.
- **EIP-7934**: blocks above 10 MiB of RLP are invalid (this includes a 2 MiB margin for beacon block size).
- **EIP-7910**: `eth_config` JSON-RPC method that reports the current and next fork configuration; clients must support it.
- **EIP-7642**: `eth/69` drops pre-merge fields from the peer protocol. **EIP-7935**: default gas limit 60M (informational).
- **EIP-7917**: the proposer schedule for upcoming slots is computed ahead of time and stored in beacon state, so it is known deterministically.

### BPO forks

- They only raise blob target and max (and update fraction). Applications that post blobs should read the schedule from the node (`eth_config`, EIP-7840) and handle changing limits.

## 4. Glamsterdam (Amsterdam + Gloas)

EIP-7773 is the Hardfork Meta EIP. Its status is `Review`, and it lists these activation rows: Sepolia 2026-10-06 13:53:36 (timestamp 1791294816), Hoodi 2026-10-26 17:42:48 (timestamp 1793036568), and no mainnet row. Do not state a mainnet date for it.

The EIP lists these as "Scheduled for Inclusion" (the list is maintained by the core developers and can change):

| Area | EIPs |
|---|---|
| Consensus and block production | EIP-7732 enshrined proposer-builder separation, EIP-7688 forward-compatible consensus data structures, EIP-8045 exclude slashed validators from proposing, EIP-8061 increase exit and consolidation churn, EIP-8282 builder execution requests |
| Execution parallelism and accounting | EIP-7928 block-level access lists, EIP-7778 block gas accounting without refunds, EIP-7843 `SLOTNUM` opcode |
| Gas repricing | EIP-2780 resource-based intrinsic transaction gas, EIP-8037 state creation gas increase, EIP-8038 state-access gas update, EIP-7976 higher calldata floor, EIP-7981 higher access list cost |
| Limits and opcodes | EIP-7954 larger maximum contract size, EIP-8024 backward compatible `SWAPN`, `DUPN`, `EXCHANGE` |
| Logs and utilities | EIP-7708 ETH transfers emit a log, EIP-7997 deterministic factory contract, EIP-8246 remove the `SELFDESTRUCT` burn |

Networking EIPs listed alongside: eth/70, eth/71, eth/72 (sparse blobpool), snap/2, and cell-level deltas for data column broadcast.

Implications to plan for (verify against the final specification once activated):

- Gas repricing changes costs of state creation and access, so gas constants and estimates should not be hardcoded.
- ETH transfers emitting a log (EIP-7708) changes what indexers can observe for plain transfers.
- A larger contract size limit (EIP-7954) changes deployment assumptions, and the `SLOTNUM` opcode (EIP-7843) exposes the slot number to contracts.
- Enshrined PBS changes the builder and proposer relationship, so MEV relay assumptions need review.

## 5. Beyond Glamsterdam

The consensus-specs mainnet configuration contains placeholder entries for later forks with the fork epoch set to the maximum value (not scheduled) and for experimental EIP-specific forks. Treat anything after Glamsterdam as research, and consult the ethereum.org roadmap and ACD notes before relying on it. Native account abstraction proposals are not live: EIP-3074 is Withdrawn, EIP-7701 is Withdrawn, and EIP-8141 (frame transactions) is Draft. EOF (EIP-3540) has status Stagnant and is not active on mainnet.

## 6. How to verify fork status

1. Open the Hardfork Meta EIP (7600, 7607, 7773) and read its status and the activation table.
2. Check `configs/mainnet.yaml` in ethereum/consensus-specs: `*_FORK_EPOCH` set to a real epoch means scheduled; `18446744073709551615` means not scheduled. `BLOB_SCHEDULE` lists blob parameter changes.
3. Call `eth_config` on your node (EIP-7910) to see `current`, `next` and `last` fork entries.
4. Read client release notes for the supported fork set and the minimum version before an activation timestamp.
5. Use forkcast.org (linked from the execution-specs README) for EIP inclusion and client implementation progress.
6. Test networks activate before mainnet; the testnet activation does not imply a mainnet date.
