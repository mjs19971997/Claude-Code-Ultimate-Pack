---
name: ethereum-expert
description: >-
  Explains Ethereum protocol behavior for application developers: accounts and transaction types (legacy, EIP-2930, EIP-1559, EIP-4844 blob, EIP-7702 set-code), gas and the fee market, proof-of-stake slots, epochs and finality, execution and consensus clients, hard forks from Dencun through Fusaka, the EVM, storage layout, logs, JSON-RPC, L2 rollups and account abstraction (ERC-4337, EIP-7702). Use when reasoning about gas, nonces, reorgs and confirmations, block tags, blobs, node or RPC provider choices, fork readiness, or how a transaction is processed. Not for writing Solidity contracts (use solidity-expert), JavaScript client code (use ethersjs-expert), or exploit review (use smart-contract-security-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Ethereum Expert

This skill covers how Ethereum works below the contract language and above the cryptography: accounts, the transaction types and their fee rules, the gas model, proof-of-stake timing and finality, the split between execution and consensus clients, the network upgrades that changed application behavior, the EVM and storage layout, the JSON-RPC surface, rollups, and account abstraction. It is meant for developers who build or operate applications that read from and write to the chain. Contract code, client library usage and audits belong to neighbouring skills.

> Verified against the ethereum/EIPs and ethereum/ERCs repositories, execution-specs, consensus-specs and execution-apis (main branches), Fusaka and its BPO forks on mainnet, Glamsterdam as listed in EIP-7773, and viem 2.57.13 for the code that was executed (2026-10).

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

- Covered: accounts and nonces, transaction envelope and types, gas, base fee, tips and blob fees, slots, epochs, finality and reorgs, execution and consensus clients and the Engine API, hard fork contents and dates, EVM execution model and storage layout, logs and bloom filters, JSON-RPC methods and block tags, node types and RPC providers, optimistic and ZK rollups from an application view, ERC-4337 and EIP-7702 account abstraction.
- Not covered: Solidity language and OpenZeppelin usage (solidity-expert), ethers or viem API usage (ethersjs-expert), legacy web3.js (web3js-expert), exploit catalogues and audits (smart-contract-security-expert), Foundry or Hardhat tooling (foundry-expert, hardhat-expert), DeFi, DAO and NFT protocol design (defi-expert, dao-expert, nft-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Accounts | Two kinds: externally owned (EOA, controlled by a secp256k1 key) and contract (code plus storage). Each has `nonce`, `balance`, `storageRoot`, `codeHash`. An EOA nonce counts sent transactions; a contract nonce counts contracts it created |
| Address derivation | `CREATE`: `keccak256(rlp([sender, nonce]))[12:]`. `CREATE2` (EIP-1014): `keccak256(0xff ++ deployer ++ salt ++ keccak256(initcode))[12:]` |
| Transaction types | Envelope from EIP-2718 (`type ++ payload`). `0x00` legacy (EIP-155 replay protection), `0x01` EIP-2930 access list, `0x02` EIP-1559, `0x03` EIP-4844 blob, `0x04` EIP-7702 set-code |
| Fee market | EIP-1559: base fee is burned and adjusts by at most 1/8 (12.5%) per block toward a gas target of half the gas limit; the tip goes to the block proposer. Blob gas has a separate base fee |
| Consensus timing | 12 s slots, 32 slots per epoch (6.4 min). Finality needs two epochs (about 12.8 min). Validators stake 32 ETH minimum; since Pectra (EIP-7251) an effective balance can reach 2048 ETH |
| Clients | A node runs one execution client (Geth, Nethermind, Besu, Erigon, Reth) and one consensus client (Lighthouse, Lodestar, Nimbus, Prysm, Teku, Grandine), joined by the authenticated Engine API (default port 8551, JWT) |
| Forks | Dencun 2024-03-13, Pectra 2025-05-07, Fusaka 2025-12-03 (BPO1 2025-12-09, BPO2 2026-01-07). Glamsterdam is not scheduled on mainnet as of this check |
| EVM | 256-bit word stack machine (depth 1024), byte-addressed memory, persistent storage, transient storage (EIP-1153), call depth 1024, 63/64 gas forwarding on calls (EIP-150), contract size limit 24576 bytes (EIP-170), initcode limit 49152 bytes (EIP-3860) |
| JSON-RPC | Standard `eth_` methods specified in ethereum/execution-apis. Block tags: `earliest`, `finalized`, `safe`, `latest`, `pending`. Quantities are hex without leading zeros |
| Rollups | Post transaction data to L1 (blobs since EIP-4844) and inherit L1 security to different degrees. Optimistic rollups rely on fraud proofs and a challenge window; ZK rollups post validity proofs |
| Account abstraction | ERC-4337 (UserOperations, bundlers, EntryPoint, paymasters; status Final) and EIP-7702 (EOA delegates to contract code; Final, live since Pectra) |

## 3. Workflow

1. Name the layer in question: transaction and gas (execution), validators and finality (consensus), or API behavior (JSON-RPC, Engine API, Beacon API). Many bugs come from mixing these.
2. Pin the time or block. Behavior depends on the active fork, so look up the fork at that timestamp before answering (execution-layer forks activate by timestamp since Shanghai, consensus-layer forks by epoch). Use [references/forks-and-roadmap.md](references/forks-and-roadmap.md).
3. Find the governing EIP or ERC in the ethereum/EIPs or ethereum/ERCs repository and read its status. `Final` means specified and shipped or accepted; `Draft`, `Review` and `Last Call` do not guarantee activation. The Hardfork Meta EIP for each upgrade lists what actually shipped.
4. For fees and sending, compute with the rules in [references/transactions-and-gas.md](references/transactions-and-gas.md) and check against the node: `eth_estimateGas`, `eth_feeHistory`, `eth_call`.
5. For reading data, choose the block tag deliberately (`latest` for freshness, `safe` or `finalized` for correctness) and pin multi-call reads to one block number or hash.
6. For anything that must survive reorgs (indexers, balances, order books), use the hash-chained follower pattern in [references/rpc-nodes-finality.md](references/rpc-nodes-finality.md).
7. For L2 or smart-account questions, read [references/l2-and-account-abstraction.md](references/l2-and-account-abstraction.md) and the chain's own documentation, because rollups differ in fees, finality and precompiles.
8. State what was verified and what depends on a client version or provider, and say "check the current docs" for items that change between releases.

## 4. Decision Rules

- Transaction type: use type `0x02` by default; type `0x03` only for data posted as blobs (rollups, data availability); type `0x04` only when an EOA needs batching, sponsorship or scoped permissions; legacy `0x00` only for chains or tooling that lack EIP-1559.
- Confirmations: show a result at `latest` for UX, treat `safe` as reorg-resistant under honest-majority assumptions, and require `finalized` before irreversible actions such as releasing goods, crediting fiat or signing off-chain on the outcome. A fixed number of confirmations is a heuristic; the tags are the protocol's own answer.
- Node or provider: use a provider for prototypes and burst traffic; run your own execution plus consensus client when you need guaranteed rate limits, `debug_` or `trace_` methods, custom filters, privacy of queries, or independence. Use at least two providers behind failover for production reads.
- Archive vs full: only historical state queries (`eth_call` or `eth_getBalance` at old blocks, `eth_getProof` for old blocks) need archive data. Logs and transactions do not.
- L1 vs L2: use L1 for highest security and composability with deep liquidity; use an L2 for cost-sensitive volume. Treat L2 `latest` as sequencer-ordered, not L1-final, and read the chain's withdrawal and finality rules.
- Smart accounts: ERC-4337 when you need a paymaster, bundler infrastructure, account factories or modular accounts on many chains; EIP-7702 when existing EOA addresses must gain batching or sponsorship without migrating assets. They can be combined.
- Gas estimation: take `eth_estimateGas`, add headroom (for example 10 to 20 percent) for state that can change before inclusion, and never exceed the per-transaction cap of 2^24 gas (EIP-7825, live since Fusaka).

## 5. Coding Standards

- Use `BigInt` (or a decimal library) for every wei, gas and fee value. JavaScript `number` loses precision above 2^53, which is far below one ether in wei.
- JSON-RPC quantities (`QUANTITY`) are hex with no leading zeros (`0x0`, `0x400`); byte strings (`DATA`) are even-length hex. Parse and build them with a library, not string slicing.
- Store raw chain facts (block number, block hash, transaction hash, log index) and derive everything else. Identify a block by hash when correctness matters, because a number can map to different blocks after a reorg.
- Set `chainId` explicitly and make signing code take it from configuration, not from the provider response alone.
- Give every request a timeout, bounded retries with backoff, and a cap on `eth_getLogs` block range (providers enforce their own caps).
- Set the fee fields (`maxFeePerGas`, `maxPriorityFeePerGas`) and `gas` explicitly on every transaction you build, and handle replacement by reusing the nonce with fees raised by at least the client's bump (Geth's default is 10 percent for regular transactions and 100 percent for blob transactions).
- Never log private keys, mnemonics, JWT secrets or full RPC URLs that embed API keys.

## 6. Project Structure

```
chain-service/
├── src/
│   ├── config.ts            # chainId, RPC URLs from env, confirmation policy, fork timestamps
│   ├── rpc/
│   │   ├── client.ts        # JSON-RPC wrapper: timeout, retry, failover, request ids
│   │   └── fees.ts          # eth_feeHistory based fee suggestion
│   ├── follower/
│   │   ├── follower.ts      # hash-chained head follower with rollback
│   │   └── store.ts         # apply(block) and rollbackTo(height) against the database
│   ├── tx/
│   │   ├── nonce.ts         # nonce allocation and replacement
│   │   └── confirm.ts       # inclusion state: included, safe, finalized, reorged-out
│   └── abi/                 # ABIs of the contracts being read
├── test/                    # unit tests with a fake JSON-RPC, integration tests against a dev node
└── .env.example             # variable names only
```

## 7. Design Patterns

- **Hash-chained follower**: remember the last N block hashes; on each head, walk back until your stored hash equals the node's hash at that height, roll back derived rows above it, then replay forward. Fetch logs by `blockHash` so one query cannot mix two forks.
- **Finality-tiered state**: serve `latest` data labeled provisional, promote rows to final once their block number is at or below the `finalized` block, and prune the rollback window to that point.
- **Nonce manager**: one process owns the nonce sequence per sending address, reads `pending` count at startup, increments locally, and has an explicit replace or cancel path (same nonce, higher fees) for stuck transactions.
- **Fee oracle from history**: derive `maxFeePerGas` from the next block's base fee and recent tips, not from the legacy `eth_gasPrice` alone.
- **Block-pinned reads**: pass one block hash or number to every read that must be consistent (for example reserves of two pools), using `blockHash` where supported (EIP-1898).
- **Read via multicall**: aggregate many `eth_call`s into one call to a multicall contract to get a consistent snapshot with one round trip.
- **Provider failover with quorum for critical reads**: compare block hash or state across two providers before trusting a single response.
- **Blob posting pipeline** (rollups): batch data, compute commitments and cell proofs, send a type `0x03` transaction, and track the blob fee market separately from execution gas. See [references/transactions-and-gas.md](references/transactions-and-gas.md).

## 8. Best Practices

- Treat the chain as an eventually final database: writes are proposals until included, and inclusion is provisional until finalized.
- Prefer `eth_getBlockReceipts` (one call per block) over one `eth_getTransactionReceipt` per transaction when a provider supports it.
- Use `eth_simulateV1` or `eth_call` with state overrides to preview outcomes of bundles and to estimate against hypothetical state, where the client supports it.
- Subscribe over WebSocket (`eth_subscribe` with `newHeads` or `logs`) for low-latency events, but keep a polling reconciliation loop. Removed logs after a reorg arrive with `removed: true`.
- Read `eth_chainId` at startup and refuse to run if it does not match configuration. Wrong-chain transactions are the most expensive class of operator mistake.
- Keep upgrade dates in configuration. Before a fork, check that the client versions you run support it and that your gas, signing and RPC assumptions still hold.
- Use `eth_config` (EIP-7910, required of clients since Fusaka) to read the active and next fork configuration from a node.

## 9. Performance

- State access dominates cost. Cold account access is 2600 gas and a cold storage slot read is 2100 gas; warm reads cost 100 (EIP-2929). Access lists (type `0x01` and later) pre-declare addresses at 2400 gas each and slots at 1900 gas each, which only pays off when the declared items would otherwise be cold.
- Calldata costs 4 gas per zero byte and 16 per non-zero byte, with a floor of 10 and 40 for data-heavy transactions (EIP-7623, since Pectra). Large payloads belong in blobs, not calldata.
- Transient storage (`TLOAD`, `TSTORE`, EIP-1153) is cleared at transaction end and is much cheaper than persistent storage for per-transaction flags such as reentrancy locks.
- Reduce RPC load: batch JSON-RPC requests (arrays), cache immutable data by block hash, paginate `eth_getLogs` by block range with address and topic filters, and avoid `pending` queries in loops.
- Keep indexers close to the node (same region or same host) and read from the node's WebSocket for heads.
- Blob capacity is a separate resource: target and max blobs per block are 14 and 21 since BPO2 (2026-01-07). See [references/forks-and-roadmap.md](references/forks-and-roadmap.md).

## 10. Security

- RPC exposure: never expose `admin`, `debug`, `personal` or `txpool` namespaces, or unauthenticated `eth_sendTransaction` with unlocked accounts, to untrusted networks. The Engine API port must stay private and requires the shared JWT secret.
- Provider keys are credentials. Keep them server-side and rotate them; do not embed them in browser bundles or public repositories.
- Signature replay: include `chainId` and contract address in signed messages (EIP-712 domain). A type `0x04` authorization with `chain_id = 0` is valid on every chain that supports EIP-7702, so only sign chain-specific authorizations.
- EIP-7702 delegation gives the delegate code full control of the EOA. Delegate only to audited, minimal implementations; initialization must be authorized by the account's key to prevent front-running; delegations are not rolled back if the surrounding transaction reverts.
- EOA assumptions break under EIP-7702: `extcodesize == 0` no longer means "EOA" (an EOA can hold the 23-byte delegation indicator `0xef0100 ++ address`), and `tx.origin == msg.sender` checks no longer prove "not a contract" for delegated accounts.
- Mempool visibility: public transactions can be front-run or sandwiched. Use private order-flow endpoints, tight slippage and deadlines for value-sensitive transactions.
- Reorg handling is a security property for payments: crediting at `latest` can be reversed.
- Key management: signing keys live in HSMs, KMS or hardware wallets; hot keys hold only operating balances. For general secret handling see secure-coding-expert.

## 11. Testing

- Unit-test fee math, nonce logic and hash-chain rollback against a fake `call(method, params)` function that returns scripted blocks, including a fork that replaces the last blocks.
- Integration-test against a local development node (Anvil, Hardhat Network or `geth --dev`). Dev nodes add non-standard methods such as `evm_snapshot` and `evm_revert` that are useful to simulate reorgs; they are not part of the execution-apis specification.
- Use a mainnet fork for realistic state, and pin the fork block number so tests are repeatable.
- Run end-to-end checks on Sepolia or Hoodi, the public testnets listed in the ethereum.org client documentation; faucets and fork schedules differ from mainnet.
- Test fork transitions by configuring the node's fork timestamps, and test EIP-7702 and blob transactions only on nodes whose active fork supports them.
- Test the failure paths: timeouts, provider returning stale blocks, `null` receipts, dropped transactions, and `finalized` tag unresolvable on a syncing node.

## 12. Review Checklist

- [ ] Every wei, gas and fee value is a `BigInt` or decimal, never a JavaScript `number`.
- [ ] Block tag choice is justified for each read; irreversible actions wait for `finalized`.
- [ ] Reorg handling exists for anything derived from logs or receipts; logs are fetched by block hash.
- [ ] Fee fields come from `eth_feeHistory` or equivalent, with headroom, and a replacement path exists.
- [ ] `chainId` is validated at startup and included in signed payloads.
- [ ] Gas limit is below 2^24 per transaction and estimated with headroom.
- [ ] Provider failover, timeouts and `eth_getLogs` range caps are configured.
- [ ] No privileged RPC namespaces or Engine API ports are reachable from untrusted networks.
- [ ] EIP-7702 delegations point to reviewed code and are initialized by the account owner.
- [ ] Fork dates and client versions are tracked; behavior that depends on an unscheduled fork is not assumed.

## 13. Production Notes

- Upgrade execution and consensus clients before each fork's activation timestamp; running an old client past activation forks it off the network. Read the client release notes and the Hardfork Meta EIP.
- Run at least two client combinations if you operate several nodes, to avoid a single-implementation bug taking all of them down. Client diversity also protects the network.
- Beacon nodes should start from checkpoint sync and, since PeerDAS (EIP-7594, Fusaka), enough bandwidth and disk for their share of blob data columns. Blobs are retained for about 18 days (4096 epochs); archive them yourself if you need them longer.
- Monitor head lag, peer count, sync state (`eth_syncing`), finalized-epoch lag, and mempool backlog. A stalled `finalized` tag signals a network or client problem.
- Gas limit and blob parameters change by fork and by validator coordination. Read live values (`gasLimit` in the latest block header, `eth_config`, `eth_blobBaseFee`) instead of hardcoding them.
- Glamsterdam (EL name Amsterdam, CL name Gloas) is specified in EIP-7773 with activation rows for Sepolia and Hoodi and none for mainnet; plan for its changes (enshrined PBS, block-level access lists, gas repricing) but do not assume a mainnet date.
- RPC providers differ on `eth_getLogs` limits, archive access, tracing, WebSocket stability and rate limits. Test each provider with your real query shapes.

## 14. Examples

Fee suggestion from `eth_feeHistory` with plain BigInt math (any JSON-RPC `call(method, params)` function works). `baseFeePerGas` has one more entry than `blockCount`; the last entry is the next block's base fee.

```js
export async function suggestFees(call) {
  const hist = await call('eth_feeHistory', ['0xa', 'latest', [25, 50]]);
  const nextBaseFee = BigInt(hist.baseFeePerGas.at(-1));
  const tips = hist.reward
    .map((r) => BigInt(r[1]))
    .filter((t) => t > 0n)
    .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const tip = tips.length ? tips[Math.floor(tips.length / 2)] : 1_000_000_000n; // fall back to 1 gwei
  // Base fee rises at most 12.5% per full block; 2x covers about six full blocks in a row.
  return { maxPriorityFeePerGas: tip, maxFeePerGas: nextBaseFee * 2n + tip };
}
// Paid per gas: min(maxFeePerGas, baseFee + maxPriorityFeePerGas). The base fee part is burned.
```

Classify how reorg-proof a transaction's inclusion is, using the node's own `safe` and `finalized` tags:

```js
export async function inclusionState(call, txHash) {
  const receipt = await call('eth_getTransactionReceipt', [txHash]);
  if (!receipt) return { state: 'not-included' };
  if (receipt.status !== '0x1') return { state: 'reverted', receipt };
  const at = await call('eth_getBlockByNumber', [receipt.blockNumber, false]);
  if (!at || at.hash !== receipt.blockHash) return { state: 'reorged-out' };
  const tagged = async (tag) => (await call('eth_getBlockByNumber', [tag, false]))?.number;
  const [safe, finalized] = await Promise.all([tagged('safe'), tagged('finalized')]);
  const n = BigInt(receipt.blockNumber);
  if (finalized && n <= BigInt(finalized)) return { state: 'finalized', receipt };
  if (safe && n <= BigInt(safe)) return { state: 'safe', receipt };
  return { state: 'included', receipt };
}
```

Raw JSON-RPC calls for the same facts (HTTP POST with `Content-Type: application/json`; replace the URL with a node you control or a provider URL kept in an environment variable):

```bash
curl -s -X POST "$RPC_URL" -H 'content-type: application/json' --data \
  '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["finalized",false]}'
curl -s -X POST "$RPC_URL" -H 'content-type: application/json' --data \
  '{"jsonrpc":"2.0","id":2,"method":"eth_feeHistory","params":["0xa","latest",[25,50]]}'
curl -s -X POST "$RPC_URL" -H 'content-type: application/json' --data \
  '{"jsonrpc":"2.0","id":3,"method":"eth_config","params":[]}'
```

A reorg-aware log follower, an EIP-7702 delegation example, and storage slot calculations are in the reference files.

## 15. Common Mistakes

- **Treating `latest` as final**: it can be reorged under normal conditions. Use `safe` or `finalized` for decisions that cannot be reversed.
- **Counting a fixed number of confirmations as finality**: finality is a protocol event (two epochs of attestations), not a block count.
- **Using `number` for wei**: precision is lost above 2^53. Use `BigInt`.
- **Hardcoding gas price or the gas limit**: fees move every block and the block gas limit is a validator-signaled value. Read them from the node.
- **Assuming `eth_gasPrice` equals the base fee plus a safe tip**: it is a node heuristic. Use `eth_feeHistory` for EIP-1559 fields.
- **Filtering logs by block range across a reorg**: one range query can span two forks. Query by `blockHash` and track parent hashes.
- **Unbounded `eth_getLogs`**: providers reject or truncate large ranges. Paginate and add address and topic filters.
- **Reading `balanceOf` and other state from different blocks**: pin to one block for consistency.
- **Believing `extcodesize` or `tx.origin` identify EOAs after EIP-7702**: delegated EOAs carry code and may call through contracts.
- **Signing an EIP-7702 authorization with `chain_id` 0 unintentionally**: it is replayable on every supporting chain.
- **Sending blob transactions with calldata expectations**: type `0x03` requires a non-null `to`, at least one versioned hash, and blob data travels in the network sidecar, not in the transaction body or EVM-visible calldata.
- **Assuming royalties, fees or finality on an L2 match L1**: L2 fees include an L1 data component and L2 finality has extra stages. Check the chain's documentation.
- **Relying on an EIP that is not final or not scheduled**: for example Glamsterdam content has no mainnet activation yet. Cite the Hardfork Meta EIP and its status.
- **Running the Engine API or `admin` RPC on a public interface**: it exposes control of the node.

## 16. References

- [references/transactions-and-gas.md](references/transactions-and-gas.md): transaction field layouts for each type, intrinsic gas, EIP-1559 and blob fee formulas, calldata floor, nonces, replacement, EIP-7702 processing rules, and gas cost tables.
- [references/forks-and-roadmap.md](references/forks-and-roadmap.md): upgrade history with dates and contents (London to Fusaka and the BPO forks), blob parameter schedule, Glamsterdam as listed in EIP-7773, and how to verify fork status.
- [references/evm-and-storage.md](references/evm-and-storage.md): execution model, opcodes added over time, precompiles, storage slot layout, namespaced storage (ERC-7201), proxy slots (ERC-1967), logs and bloom filters.
- [references/rpc-nodes-finality.md](references/rpc-nodes-finality.md): JSON-RPC conventions and methods, block tags, WebSocket subscriptions, clients and the Engine API, node types, RPC providers, finality, reorgs, and the follower implementation.
- [references/l2-and-account-abstraction.md](references/l2-and-account-abstraction.md): optimistic and ZK rollups, rollup stages, L1 data costs, ERC-4337 flow and EntryPoint versions, EIP-7702 usage with viem, and risks.
- Official docs: https://ethereum.org/en/developers/docs/ , https://github.com/ethereum/EIPs , https://github.com/ethereum/ERCs , https://github.com/ethereum/execution-apis , https://github.com/ethereum/execution-specs , https://github.com/ethereum/consensus-specs , https://eips.ethereum.org/
