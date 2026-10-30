# RPC, Nodes and Finality

Reference for JSON-RPC conventions and methods, block tags, subscriptions, the Engine and Beacon APIs, clients and node types, RPC providers, proof-of-stake timing, finality and reorg handling. Verified against ethereum/execution-apis (main), consensus-specs mainnet config and presets, the ethereum.org nodes-and-clients documentation and Geth defaults, and by running the follower below against a scripted fork (2026-10).

## 1. Three interfaces, three jobs

| Interface | Between | Transport | Notes |
|---|---|---|---|
| JSON-RPC (`eth_`, `net_`, `web3_`) | Applications and the execution client | HTTP, WebSocket, IPC | Specified in ethereum/execution-apis. Geth defaults: HTTP 8545, WebSocket 8546 |
| Engine API (`engine_`) | Consensus client and execution client | HTTP with JWT, WebSocket handshake with JWT | Default authenticated port 8551; HS256 JWT required; `alg: none` must be rejected; keep it off public networks |
| Beacon API | Applications or validators and the consensus client | REST | Specified in ethereum/beacon-APIs; exposes beacon blocks, validators, finality checkpoints and blob sidecars |

Application code normally talks to the first only. The Engine API is internal plumbing between the two clients of one node.

## 2. JSON-RPC conventions

- Request: `{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}`. A JSON array of requests is a batch; responses may arrive in any order and must be matched by `id`.
- `QUANTITY` values are hex integers without leading zeros (`0x0`, `0x1b4`). `DATA` values are even-length hex byte strings (`0x`, `0x00ff`). Block numbers, gas and wei amounts are quantities.
- Errors carry `code`, `message` and optional `data`; revert data of a failed `eth_call` is returned in `data` by most clients (the shape differs between clients and providers).
- Method families in the specification (a subset that applications use most):

| Group | Methods |
|---|---|
| Client | `eth_chainId`, `eth_blockNumber`, `eth_syncing`, `eth_config`, `net_version` |
| State | `eth_getBalance`, `eth_getStorageAt`, `eth_getTransactionCount`, `eth_getCode`, `eth_getProof` |
| Execution | `eth_call`, `eth_estimateGas`, `eth_createAccessList`, `eth_simulateV1` |
| Fees | `eth_gasPrice`, `eth_maxPriorityFeePerGas`, `eth_feeHistory`, `eth_blobBaseFee` |
| Blocks | `eth_getBlockByHash`, `eth_getBlockByNumber`, `eth_getBlockReceipts`, `eth_getBlockTransactionCountBy*` |
| Transactions | `eth_getTransactionByHash`, `eth_getTransactionReceipt`, `eth_sendRawTransaction`, `eth_sendTransaction` (needs an unlocked node account; do not use on public nodes) |
| Logs and filters | `eth_getLogs`, `eth_newFilter`, `eth_newBlockFilter`, `eth_getFilterChanges`, `eth_getFilterLogs`, `eth_uninstallFilter` |
| Subscriptions | `eth_subscribe`, `eth_unsubscribe` (WebSocket and IPC only) |

- `eth_subscribe` kinds in the specification: `newHeads`, `logs` (removed logs after a reorg are pushed with `removed: true`), `newPendingTransactions`, and `transactionReceipts`. Subscriptions are lost on disconnect, so reconnect and backfill the gap by block range.
- Filters (`eth_newFilter` and relatives) are stateful on one node and expire after inactivity; they do not work across a load balancer without sticky routing. Prefer `eth_getLogs` ranges or subscriptions.
- Debug and trace namespaces (`debug_traceTransaction`, `trace_*`) are client-specific and not part of the specification; availability and output differ between Geth, Erigon, Reth and Nethermind.
- Method availability differs across clients and providers. `eth_simulateV1`, `eth_config` and `eth_getBlockReceipts` are newer; feature-detect and fall back.

## 3. Block tags

From the execution-apis specification:

| Tag | Meaning |
|---|---|
| `earliest` | Lowest block the client has available |
| `finalized` | Most recent crypto-economically secure block; cannot be reorged outside of manual community-driven intervention |
| `safe` | Most recent block safe from reorgs under honest-majority and certain synchronicity assumptions |
| `latest` | Most recent block in the canonical chain seen by the node; can be reorged even under healthy conditions |
| `pending` | A sample next block built by the client on top of `latest` from its local mempool |

If `safe` or `finalized` cannot be resolved (for example a node that is still syncing), the method responds as it does for an unknown block. Handle that error.

Block identifiers can also be a block hash (EIP-1898) in the state-reading methods that accept a block parameter, with `requireCanonical` available to reject non-canonical hashes. Logs can be fetched by `blockHash` in `eth_getLogs`, which is mutually exclusive with `fromBlock` and `toBlock`.

## 4. Clients and node types

- Execution clients: Geth (Go), Nethermind (C#), Besu (Java), Erigon (Go), Reth (Rust). Consensus clients: Lighthouse (Rust), Lodestar (TypeScript), Nimbus (Nim), Prysm (Go), Teku (Java), Grandine (Rust). Each pair of one execution and one consensus client forms a node.
- Public testnets listed by ethereum.org: Sepolia and Hoodi. Sepolia chain id is 11155111 and Hoodi chain id is 560048.
- Node types: a full node validates every block and keeps recent state (pruned); an archive node keeps all historical state and is needed for state queries at old blocks; light client support is limited, and Helios, Nimbus and Lodestar are named by ethereum.org as light-client work.
- Sync: execution clients support snap sync (Geth, Nethermind, Besu) or full sync; consensus clients should start from a trusted checkpoint (checkpoint sync) to avoid syncing from genesis.
- An execution client does not follow the chain head on its own after the merge; it needs a consensus client connected through the Engine API. A node showing the execution client "syncing" at an old block usually has a consensus client that is not connected or not synced.
- Client diversity matters: a bug in a client with a supermajority share can finalize an invalid chain. Pick a minority client when you run your own node.

## 5. Proof-of-stake timing and finality

Constants from consensus-specs (mainnet):

| Item | Value |
|---|---|
| Slot duration | 12 s (`SLOT_DURATION_MS` 12000) |
| Slots per epoch | 32 (6.4 min) |
| Minimum activation balance | 32 ETH; max effective balance 2048 ETH with `0x02` credentials (Electra) |
| Ejection balance | 16 ETH |
| Sync committee | 512 validators, rotating every 256 epochs |
| Fork choice | LMD-GHOST, with Casper FFG finality |

- One proposer per slot builds or accepts a block; committees of validators attest. Attestations vote for the head (LMD-GHOST) and for a source-target checkpoint pair (Casper FFG).
- A checkpoint is the first block of an epoch. It becomes justified when two thirds of the stake attests to it, and finalized when the next epoch's checkpoint is justified as well. A transaction included at the start of an epoch typically finalizes about two epochs later (about 13 minutes); one included late in an epoch finalizes a bit later.
- If more than a third of stake goes offline, finality stalls and the inactivity leak gradually reduces inactive validators' balances until finality resumes. During that period `finalized` stops advancing while `latest` and `safe` may keep moving.
- Missed slots are normal; a block can be skipped and the next proposer builds on the previous one. Short reorgs of one or two blocks happen when a late block is orphaned; the proposer score boost makes timely blocks win. Deep reorgs are rare and indicate an incident.
- Block production in practice often goes through external builders and relays (MEV-Boost); enshrined proposer-builder separation (EIP-7732) is scheduled in the Glamsterdam meta EIP.

## 6. Finality policy for applications

| Use case | Read at | Rationale |
|---|---|---|
| UI refresh, price display | `latest` | Freshness matters, wrong answers are cheap |
| Show "confirmed" in a wallet | `safe` | Resistant to ordinary reorgs |
| Credit deposits, release goods or fiat | `finalized` | Reversal requires a protocol failure |
| Cross-chain or bridge relays | `finalized` of the source chain | A reorg would double-spend the destination |
| Signing off-chain outcomes (oracles, keepers) | `safe` or `finalized` depending on value at risk | Match the cost of being wrong |
| Indexer database | Follow `latest` with rollback; mark rows final when below `finalized` | Both speed and correctness |

For L2s, the chain's own notion of unsafe, safe and finalized heads applies; see [l2-and-account-abstraction.md](l2-and-account-abstraction.md).

## 7. RPC providers

- Compare providers on: supported methods (archive state, `debug_`/`trace_`, `eth_simulateV1`), `eth_getLogs` range and result caps, WebSocket reliability, rate limits and compute-unit pricing, regions, and chain coverage including testnets and L2s.
- Public endpoints are rate-limited and may serve stale data; do not use them for production traffic.
- Keep the API key out of client-side code and out of repositories; route browser traffic through a backend proxy that enforces origin and rate limits.
- Run two or more providers with failover, health checks on head lag (compare `eth_blockNumber` to the others) and a timeout per call. For high-value reads compare block hashes across providers.
- Providers can differ on which block `latest` is by a block or two. Pin multi-call reads to one block number or hash.
- Self-hosting gives predictable limits and privacy but needs both clients, monitoring and upgrades before each fork.

## 8. Reorg-aware log follower

The follower keeps a window of recent `{number, hash}` pairs. Each `step()` walks back until the stored tip is on the node's chain, tells the store to delete rows above the common ancestor, then replays forward, fetching logs by block hash. `store` must implement `apply({number, hash, logs})` and `rollbackTo(height)` atomically. It was run against a scripted chain where blocks 6 and 7 were replaced by a competing fork and extended: rows 6 to 8 were rebuilt from the new fork and rows up to 5 stayed.

```js
// Reorg-aware log follower over plain JSON-RPC (Node 22+, no dependencies).
const RPC_URL = process.env.RPC_URL ?? 'http://127.0.0.1:8545';
let nextId = 1;

export async function rpc(method, params, url = RPC_URL) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: nextId++, method, params }),
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  if (body.error) throw new Error(`${method}: ${body.error.code} ${body.error.message}`);
  return body.result;
}

/**
 * Follows the chain head and hands each block's logs to `store`, undoing blocks that get reorged out.
 * `window` keeps the most recent block hashes (oldest first); a reorg deeper than the window is fatal.
 */
export function createFollower({ call = rpc, address, topics, store, window = [], maxDepth = 128 }) {
  let started = false; // false until the first block has been stored
  async function step() {
    const head = await call('eth_getBlockByNumber', ['latest', false]);
    const headNumber = Number(head.number);
    // 1. Roll back while the stored tip is no longer an ancestor of the node's chain.
    while (window.length > 0) {
      const tip = window[window.length - 1];
      const onChain = tip.number <= headNumber ? await call('eth_getBlockByNumber', ['0x' + tip.number.toString(16), false]) : null;
      if (onChain && onChain.hash === tip.hash) break;
      window.pop();
      await store.rollbackTo(window.length ? window[window.length - 1].number : -1); // delete rows above this height
    }
    if (window.length === 0 && started) throw new Error(`reorg deeper than ${maxDepth} blocks, resync required`);
    // 2. Apply new blocks in order, pinning logs to the block hash so a concurrent reorg cannot mix chains.
    let from = window.length ? window[window.length - 1].number + 1 : headNumber;
    for (let n = from; n <= headNumber; n++) {
      const block = await call('eth_getBlockByNumber', ['0x' + n.toString(16), false]);
      const parent = window[window.length - 1];
      if (parent && block.parentHash !== parent.hash) return; // head moved under us; next step() repairs it
      const logs = await call('eth_getLogs', [{ blockHash: block.hash, address, topics }]);
      await store.apply({ number: n, hash: block.hash, logs });
      started = true;
      window.push({ number: n, hash: block.hash });
      if (window.length > maxDepth) window.shift();
    }
  }
  return { step, window };
}
```

Usage notes:

- The first `step()` starts at the current head; to index history, start from a stored height and fetch older ranges with `eth_getLogs` in bounded chunks before switching to the follower.
- Poll every second or two, or call `step()` on each `newHeads` notification.
- To mark rows final, compare `row.number` with the number of the `finalized` block and drop window entries below it; a reorg deeper than `maxDepth` (128 here) means a resync from the last finalized block.
- Keep `apply` and `rollbackTo` in database transactions and make them idempotent, so a crash between steps is safe.
- Fetch receipts per block with `eth_getBlockReceipts` when you need all transactions, not just logs.
