---
name: ethersjs-expert
description: >-
  Builds dApp front ends, backend services, bots and scripts on ethers.js v6: JsonRpcProvider, BrowserProvider (EIP-1193 and EIP-6963 wallets), FallbackProvider, Wallet, Contract, Interface and ABI coding, native bigint and parseUnits, EIP-191 and EIP-712 signing with TypedDataEncoder, event filters and queryFilter, tx.wait confirmations and v5 to v6 migration. Use when writing or reviewing code that imports from "ethers", handling wallets, gas, receipts, logs, custom-error decoding or typed data. Not for the Solidity contracts themselves (use solidity-expert), the web3.js library (use web3js-expert), Hardhat or Foundry project tooling (use hardhat-expert or foundry-expert), or protocol economics (use defi-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Ethers.js Expert

This skill covers application code that talks to EVM chains through ethers.js v6: choosing providers and signers, calling and sending to contracts, decoding events and errors, signing messages and typed data, and migrating v5 code. It keeps private keys on the server, wallet prompts in the browser, and all token math in `bigint`.

> Verified against ethers 6.17.0 (npm `latest`; v5 is the `legacy-v5` tag at 5.8.0), TypeScript 5, Node 22 (2026-10). Examples were type-checked against these versions.

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

- Covered: provider and signer selection, wallet connection, `Contract` calls and transactions, human-readable and JSON ABIs, `Interface` encoding and decoding, event backfill and live subscriptions, EIP-191 and EIP-712 signing, units and `bigint`, fee data, receipts and confirmations, error handling, v5 to v6 migration.
- Not covered: writing the contracts (solidity-expert, smart-contract-security-expert), web3.js (web3js-expert), compile and deploy pipelines and test runners (hardhat-expert, foundry-expert), protocol math and risk (defi-expert), chain and client internals (ethereum-expert).

## 2. Core Expertise

| Need | v6 API |
|---|---|
| Server read/write RPC | `JsonRpcProvider(url, network?, { staticNetwork })`; batching is on by default (`batchMaxCount` 100, `batchStallTime` 10 ms) |
| Redundancy | `FallbackProvider([{ provider, priority, stallTimeout, weight }], network, { quorum })` |
| Browser wallet | `new BrowserProvider(window.ethereum)`, `provider.getSigner()` (async), `BrowserProvider.discover()` for EIP-6963 (resolves `null` if none) |
| Live events | `WebSocketProvider`, `contract.on(filter, listener)`, `provider.destroy()` to free resources |
| Server signer | `new Wallet(privateKey, provider)`, `Wallet.fromEncryptedJson`, `Wallet.createRandom()`, `NonceManager` wrapper for parallel sends |
| Contracts | `new Contract(address, abi, runner)`, `contract.fn.staticCall`, `.estimateGas`, `.populateTransaction`, `.send`, `contract.connect`, `getAddress()`, `waitForDeployment()` |
| ABI coding | `Interface`, `AbiCoder.defaultAbiCoder()`, `iface.getFunction(n).selector`, `parseLog`, `parseError`, `Result` (immutable, `toObject()`) |
| Units | `parseUnits`, `formatUnits`, `parseEther`, `formatEther`, native `bigint`, `FixedNumber` |
| Hash and sign | `id`, `keccak256`, `solidityPackedKeccak256`, `hashMessage`, `verifyMessage`, `TypedDataEncoder`, `signTypedData`, `verifyTypedData`, `Signature.from` |
| Errors | `isError(err, "CALL_EXCEPTION")` (`err.revert.name/args`), `"TRANSACTION_REPLACED"`, `"INSUFFICIENT_FUNDS"`, `"NONCE_EXPIRED"`, `"REPLACEMENT_UNDERPRICED"`, `"TIMEOUT"`, `"ACTION_REJECTED"` |

- **Transactions**: `signer.sendTransaction` returns a `TransactionResponse`; `tx.wait(confirms, timeout)` resolves a `TransactionReceipt`, throws `CALL_EXCEPTION` when the receipt status is 0 and `TRANSACTION_REPLACED` when replaced or cancelled; `wait(0)` can resolve `null` for an unmined tx. A `timeout` (ms) makes it reject with `TIMEOUT`. `provider.waitForTransaction(hash, confirms, timeout)` waits by hash the same way.
- **Fees**: `provider.getFeeData()` returns `gasPrice`, `maxFeePerGas`, `maxPriorityFeePerGas` (each can be `null` on chains without EIP-1559).
- **Name resolution**: `provider.resolveName`, `provider.lookupAddress`; ENS names are accepted where an address is expected, but resolve and validate them before authorizing anything.

## 3. Workflow

1. Decide the runtime: server (keys from env or a KMS), browser (wallet signs), or both. Never share one provider config between them.
2. Pin the expected chain id. On servers pass it with `staticNetwork`; in browsers compare `getNetwork().chainId` to the expected `bigint`.
3. Define ABIs as typed constants (`as const` human-readable ABI or generated types), not loose JSON strings.
4. For writes: validate inputs, `parseUnits` with the token's real decimals, simulate with `staticCall`, send, then `wait(confirms)` with a timeout.
5. For reads at scale: batch via the provider, or use a Multicall3 contract; avoid per-item awaits in loops.
6. For events: backfill in bounded block ranges with `queryFilter`, then subscribe; store the last processed block and de-duplicate by `(blockHash, logIndex)` to survive reorgs.
7. Map every failure to a typed error (`isError`, `parseError`) before it reaches the UI or logs.
8. Test against a local node or mainnet fork before touching a live chain.

## 4. Decision Rules

- `JsonRpcProvider` for HTTP backends; `WebSocketProvider` only when push events matter and reconnect logic exists; `BrowserProvider` is for wallets only, never for server reads.
- Use `staticNetwork` only when the chain cannot change (fixed URL). Never with a wallet: the user can switch networks at any time.
- `FallbackProvider` with `quorum` above 1 when read correctness matters more than latency; `quorum: 1` is a failover, not a consensus check.
- `Contract` with a `Provider` is read-only; with a `Signer` it can send. Use `contract.connect(signer)` per request rather than sharing one signer-bound instance across users.
- `tx.wait(1)` for UX feedback, a higher `confirms` before crediting value off-chain. Confirmation count is a policy decision per chain.
- `signTypedData` (EIP-712) for anything an on-chain contract or backend will verify; `signMessage` (EIP-191) only for human-readable login or proofs. Never sign raw hashes a user cannot read.
- `getDefaultProvider` is for demos: it uses shared community keys and is rate limited.
- Smart-contract wallets cannot be verified with `verifyMessage`; use ERC-1271 `isValidSignature` on-chain for them.

## 5. Coding Standards

- TypeScript strict mode. Amounts are `bigint` end to end; convert to display strings only in the UI layer.
- No JS `number` for wei, token amounts or block-scale values above 2^53; literals use the `n` suffix (`1_000n`).
- Division on `bigint` truncates; do share and fee math as `a * bps / 10_000n` with the multiplication first.
- Addresses: normalize with `getAddress` at system boundaries; compare checksummed or lower-cased strings, never mix.
- Import named exports from `"ethers"`; v6 removed the `ethers.utils` and `ethers.providers` namespaces.
- One `Interface`/ABI constant per contract, shared between encoding and log parsing.
- Handle `Result` values by name (`result.amount`) or `toObject()`; do not mutate them.
- Treat everything from a wallet, RPC and logs as untrusted input; validate shape before use.

## 6. Project Structure

```text
src/
  config/chains.ts          chain ids, explorers, public RPC list (no keys)
  abi/                      typed ABI constants (erc20.ts, router.ts)
  clients/
    provider.server.ts      JsonRpcProvider / FallbackProvider from env
    signer.server.ts        Wallet or KMS signer, server only
    wallet.browser.ts       BrowserProvider and chain switching
  services/                 token.ts, swap.ts, indexer.ts (business logic)
  lib/errors.ts             maps ethers errors to app errors
test/                       unit tests (offline) and fork tests
```

Keep `*.server.ts` out of any client bundle (framework "server-only" boundaries or separate packages).

## 7. Design Patterns

- **Provider factory**: one function builds providers from env, so every service shares caching and batching.
- **Simulate-then-send**: `staticCall` (or `estimateGas`) first; send only on success. Catches reverts without spending gas.
- **Typed service wrapper**: expose `transferToken(to, human)` instead of leaking `Contract` objects to callers.
- **Outbox for transactions**: persist intent, nonce and hash; resume with `waitForTransaction` after a restart; replace stuck txs by reusing the nonce with higher fees.
- **Checkpointed indexer**: `queryFilter` in chunks, persist `lastBlock`, re-read a few blocks back on start to absorb reorgs.
- **Nonce lane**: one `NonceManager`-wrapped signer per process lane, or a queue, so concurrent sends do not collide.

## 8. Best Practices

- Read `decimals()` per token instead of assuming 18 (USDC and USDT use 6).
- Use exact approvals or `permit` (EIP-2612) rather than unlimited allowances where the UX permits.
- Show the user the chain, spender and amount before every approval and signature.
- Prefer `populateTransaction` when a relayer, Safe or batch needs the unsigned request.
- Subscribe to wallet `accountsChanged` and `chainChanged` and rebuild provider state.
- Cache immutable data (decimals, symbols, ABI) and block-scoped reads within one block number.
- Pin a block tag (`{ blockTag: n }`) on multi-call reads that must be consistent.

## 9. Performance

- v6 JSON-RPC providers batch concurrent requests automatically; fire reads with `Promise.all` instead of sequential awaits. Tune `batchMaxCount` if the provider rejects large batches.
- Many contract reads: Multicall3 (`aggregate3`) through `Interface.encodeFunctionData` and `decodeFunctionResult`.
- Narrow `getLogs` with address, topics and block range; respect the provider's range and result limits (check the current provider docs).
- WebSocket subscriptions avoid polling; the default polling interval for HTTP providers is 4000 ms (`pollingInterval`).
- Reuse one provider per chain per process; call `destroy()` on short-lived ones to stop timers.

## 10. Security

- Private keys and RPC URLs with embedded keys live in server env or a secret manager. Anything in a front-end bundle is public: use a server proxy or a domain-restricted key for read-only front-end RPC.
- Never log keys, mnemonics or keystore passwords; redact `Wallet` objects before serialization.
- Prefer `Wallet.fromEncryptedJson` or a KMS/HSM signer over raw keys in env for hot wallets with real funds.
- Validate chain id before signing; include `chainId` and `verifyingContract` in every EIP-712 domain, plus a nonce and a deadline in the message.
- Do not trust `window.ethereum` identity; multiple injected wallets exist (use EIP-6963 discovery).
- Simulate before sending, set slippage and deadline on swaps (see defi-expert), and cap gas via `maxFeePerGas`.
- Treat `eth_call` results and logs from a single untrusted RPC as unverified when value depends on them; use a `FallbackProvider` quorum or your own node.
- Verify signatures server-side with `verifyTypedData`/`verifyMessage` and compare the recovered address to the expected signer (exact match after `getAddress`).

## 11. Testing

- Unit-test pure code offline: `Interface` encode/decode, units, typed-data signing and verification with `Wallet.createRandom()`.
- Integration tests against a local node (Anvil or Hardhat network) and a mainnet fork for realistic token behavior.
- Assert reverts through `isError(err, "CALL_EXCEPTION")` and `err.revert?.name`, not message strings.
- Test reorg and restart handling of the indexer with a mock provider that returns overlapping ranges.
- Use fixed-seed or throwaway keys in tests; never reuse a funded key.

## 12. Review Checklist

- [ ] No key, mnemonic or keyed RPC URL reachable from client code.
- [ ] Every amount is `bigint`; decimals come from the token.
- [ ] Chain id checked before signing or sending.
- [ ] Writes simulated, then confirmed with a bounded `wait(confirms, timeout)`.
- [ ] Reverts and replacements handled via `isError` codes.
- [ ] Event consumers de-duplicate and handle reorgs.
- [ ] EIP-712 domain has chain id, verifying contract, nonce and deadline.
- [ ] Providers are reused and destroyed when short-lived.
- [ ] No v5 namespaces (`ethers.utils`, `ethers.providers`, `BigNumber`) remain.

## 13. Production Notes

- Use at least two RPC providers; alert on divergence of block height and on error rate.
- Persist pending transaction hashes and nonces; after a crash reconcile with `getTransactionCount("pending")` and `waitForTransaction`.
- Expect rate limits (`429`); back off with jitter. `FallbackProvider` `stallTimeout` starts the next provider if one is slow.
- Gas: take `getFeeData()` and apply your own cap; chains without EIP-1559 return `maxFeePerGas: null`.
- Record chain id, tx hash, block number and log index with every business event for audit.

## 14. Examples

Server: simulate, send, confirm and decode a custom error (type-checked against ethers 6.17.0):

```typescript
import {
  Contract, FallbackProvider, JsonRpcProvider, Wallet,
  formatUnits, getAddress, isAddress, isError, parseUnits,
} from "ethers";

const erc20Abi = [
  "function decimals() view returns (uint8)",
  "function transfer(address to, uint256 amount) returns (bool)",
  "error ERC20InsufficientBalance(address sender, uint256 balance, uint256 needed)",
] as const;

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing env var ${name}`);
  return v;
}

const chainId = 1;
const providers = ["RPC_URL_PRIMARY", "RPC_URL_SECONDARY"].map(
  (n) => new JsonRpcProvider(requireEnv(n), chainId, { staticNetwork: true }),
);
const provider = new FallbackProvider(
  providers.map((p, i) => ({ provider: p, priority: i + 1, stallTimeout: 1500, weight: 1 })),
  chainId,
  { quorum: 1 },
);
const signer = new Wallet(requireEnv("SIGNER_PRIVATE_KEY"), provider); // server only

export async function sendToken(token: string, to: string, human: string): Promise<string> {
  if (!isAddress(to)) throw new Error("invalid recipient");
  const erc20 = new Contract(getAddress(token), erc20Abi, signer);
  const decimals: bigint = await erc20.decimals();
  const amount = parseUnits(human, decimals);
  try {
    await erc20.transfer.staticCall(to, amount);        // simulate first
    const tx = await erc20.transfer(to, amount);
    const receipt = await tx.wait(2, 120_000);          // confirmations, timeout in ms
    return receipt!.hash;
  } catch (err) {
    if (isError(err, "CALL_EXCEPTION") && err.revert?.name === "ERC20InsufficientBalance") {
      const [, balance, needed] = err.revert.args;
      throw new Error(`balance ${formatUnits(balance, decimals)} < ${formatUnits(needed, decimals)}`);
    }
    if (isError(err, "TRANSACTION_REPLACED")) return err.replacement.hash;
    throw err;
  }
}
```

Browser: connect, check chain, approve. The wallet signs; the page holds no key:

```typescript
import { BrowserProvider, Contract, parseUnits, type Eip1193Provider } from "ethers";

const EXPECTED_CHAIN_ID = 8453n;

export async function approve(eth: Eip1193Provider, token: string, spender: string, amount: string) {
  const provider = new BrowserProvider(eth);
  await provider.send("eth_requestAccounts", []);
  const { chainId } = await provider.getNetwork();
  if (chainId !== EXPECTED_CHAIN_ID) {
    await provider.send("wallet_switchEthereumChain", [{ chainId: "0x" + EXPECTED_CHAIN_ID.toString(16) }]);
    throw new Error("Chain switched; retry"); // a BrowserProvider is bound to the network it was created on
  }
  const signer = await provider.getSigner();
  const erc20 = new Contract(token, ["function approve(address,uint256) returns (bool)"], signer);
  return (await erc20.approve(spender, parseUnits(amount, 6))).wait(1);
}
```

EIP-712 sign and verify (run offline):

```typescript
import { TypedDataEncoder, Wallet, verifyTypedData } from "ethers";

const domain = { name: "Orders", version: "1", chainId: 1n, verifyingContract: "0x0000000000000000000000000000000000000001" };
const types = { Order: [
  { name: "maker", type: "address" }, { name: "amount", type: "uint256" },
  { name: "nonce", type: "uint256" }, { name: "deadline", type: "uint256" },
] };
const wallet = Wallet.createRandom();
const value = { maker: wallet.address, amount: 5n, nonce: 0n, deadline: 2_000_000_000n };
const sig = await wallet.signTypedData(domain, types, value);
console.log(verifyTypedData(domain, types, value, sig) === wallet.address, TypedDataEncoder.hash(domain, types, value));
```

More examples (event backfill and live listeners, Multicall3) are in [references/contracts-events-abi.md](references/contracts-events-abi.md).

## 15. Common Mistakes

- Keeping v5 habits: `BigNumber.from`, `ethers.utils.parseUnits`, `ethers.providers.Web3Provider`, `contract.callStatic.fn()`. In v6 use `bigint`, `parseUnits`, `BrowserProvider`, `contract.fn.staticCall()`.
- Forgetting `getSigner()` is async in v6 and `contract.address` is replaced by `await contract.getAddress()`.
- Using `Number(amount)` or `parseFloat` for token math, losing precision above 2^53.
- Assuming 18 decimals for every token.
- Treating `tx.wait()` as optional or unbounded; a missing timeout hangs the request, and an unhandled revert throws.
- Using `staticNetwork` with a browser wallet, or not checking chain id before signing.
- Putting `RPC_URL` with a key or a private key in `NEXT_PUBLIC_*`/`VITE_*` variables.
- Calling `getLogs` over an unbounded range or ignoring reorgs.
- Comparing addresses without normalizing case.
- Using `signMessage` for data that a contract will verify (no domain separation, replayable across chains and contracts).
- Leaving `WebSocketProvider` or `contract.on` listeners open and leaking memory; remove listeners or call `destroy()`.
- Parsing logs with the wrong ABI and treating `null` from `parseLog` as success.

## 16. References

- [references/providers-and-signers.md](references/providers-and-signers.md): provider options, fallback quorum, wallets, EIP-6963, fees, nonces, transaction lifecycle.
- [references/contracts-events-abi.md](references/contracts-events-abi.md): Contract calls, Interface coding, error decoding, logs, Multicall3, signing and typed data.
- [references/migration-v5-to-v6.md](references/migration-v5-to-v6.md): v5 to v6 API mapping table and behavior changes.
- Official docs: https://docs.ethers.org/v6/ and the changelog at https://github.com/ethers-io/ethers.js/releases
