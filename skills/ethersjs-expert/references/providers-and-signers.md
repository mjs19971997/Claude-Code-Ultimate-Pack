# Providers, Signers and Transactions (ethers v6)

Reference for choosing providers and signers, tuning them, and managing the transaction lifecycle. Checked against ethers 6.17.0 type definitions.

## Provider options

`JsonRpcProvider(url | FetchRequest, network?, options?)` accepts `JsonRpcApiProviderOptions`:

| Option | Meaning |
|---|---|
| `staticNetwork` | Skip chain-id validation on each request. Only for fixed URLs; never with a wallet |
| `batchMaxCount` | Max requests per batch (default 100); `1` disables batching |
| `batchStallTime` | Milliseconds to aggregate requests (default 10) |
| `batchMaxSize` | Target max batch size in bytes (default 1 MB) |
| `polling` | Use polling for events immediately instead of filters |
| `pollingInterval` | Polling interval (default 4000 ms) |
| `cacheTimeout` | Provider-side cache lifetime |

Pass the network (chain id or name) as the second argument so the provider does not need to detect it; combine with `staticNetwork: true` only when the URL pins the chain.

## FallbackProvider

```typescript
import { FallbackProvider, JsonRpcProvider } from "ethers";

const urls = [process.env.RPC_A, process.env.RPC_B, process.env.RPC_C];
if (urls.some((u) => !u)) throw new Error("RPC env vars missing");
const provider = new FallbackProvider(
  urls.map((u, i) => ({
    provider: new JsonRpcProvider(u as string, 1, { staticNetwork: true }),
    priority: i + 1,   // lower priority value is dispatched first
    stallTimeout: 1500, // ms before the next provider is started
    weight: 1,          // weight counted toward the quorum
  })),
  1,
  { quorum: 2 },
);
```

- `quorum` is the total weight that must agree on a result; `eventQuorum` applies to event subscriptions.
- With `quorum: 1` the provider is only a failover. With a higher quorum, a single lying or lagging node cannot decide a read.
- Mixed vendors reduce correlated outages. Destroy the fallback with `provider.destroy()` when done.

## Browser wallets

- `new BrowserProvider(window.ethereum)` wraps any EIP-1193 object (`request({ method, params })`).
- `BrowserProvider.discover()` uses EIP-6963 and resolves `null` when no wallet announces itself. Prefer it to `window.ethereum` when several wallets may be installed.
- `provider.send("eth_requestAccounts", [])` prompts for connection; `await provider.getSigner()` returns a `JsonRpcSigner` (async in v6).
- A `BrowserProvider` is tied to the network at creation. On `chainChanged` build a new provider (or reload).
- User rejection surfaces as an `ACTION_REJECTED` error; show a retry path, not a crash.
- Never request or store a seed phrase or private key in a page.

## Server signers

| Signer | Use |
|---|---|
| `new Wallet(privateKey, provider)` | Hot wallet; key from env or secret manager |
| `Wallet.fromEncryptedJson(json, password)` | Keystore file; password from a separate secret |
| `Wallet.createRandom()` | Tests and throwaway keys; returns an `HDNodeWallet` |
| `HDNodeWallet.fromPhrase` / `Wallet.fromPhrase` | Mnemonic derivation (BIP-39 and BIP-44 paths) for tooling, not production hot paths |
| `NonceManager(signer)` | Tracks nonces locally for concurrent sends from one signer |
| `VoidSigner` | Read-only "from" address for `eth_call` and gas estimates |

For production value, prefer a KMS/HSM-backed signer implemented as an `AbstractSigner` subclass, or a multisig/Safe flow, over raw private keys. Never commit `.env` files; load them in the server process only.

## Transaction lifecycle

1. Build: `contract.fn.populateTransaction(...)` or a `TransactionRequest` (`to`, `data`, `value`, `nonce`, `gasLimit`, `maxFeePerGas`, `maxPriorityFeePerGas`, `chainId`, `type`).
2. Fees: `await provider.getFeeData()` gives `gasPrice`, `maxFeePerGas`, `maxPriorityFeePerGas`; each may be `null` on chains without EIP-1559. Apply your own cap before sending.
3. Simulate: `contract.fn.staticCall(...)` and `estimateGas`.
4. Send: `signer.sendTransaction(req)` returns a `TransactionResponse`. Persist `hash` and `nonce` at once.
5. Confirm: `tx.wait(confirms, timeoutMs)` or `provider.waitForTransaction(hash, confirms, timeoutMs)`. Failure modes: `CALL_EXCEPTION` (status 0), `TRANSACTION_REPLACED` (`err.replacement`, `err.reason` is `repriced`, `cancelled` or `replaced`), `TIMEOUT`.
6. Stuck transactions: resend with the same nonce and fees raised by at least the node's replacement bump (10% is the common minimum; 25% is a safe margin).

```typescript
import { getAddress, type TransactionRequest, type Wallet } from "ethers";

export async function speedUp(wallet: Wallet, stuckNonce: number, to: string) {
  const fee = await wallet.provider!.getFeeData();
  const bump = (v: bigint | null) => (v ? (v * 125n) / 100n : undefined);
  const req: TransactionRequest = {
    to: getAddress(to), value: 0n, nonce: stuckNonce,
    maxFeePerGas: bump(fee.maxFeePerGas),
    maxPriorityFeePerGas: bump(fee.maxPriorityFeePerGas),
  };
  return wallet.sendTransaction(req);
}
```

(Replace `to`/`value`/`data` with the original transaction's fields; a cancel is a zero-value self-send with the same nonce.)

## Subscriptions

- `provider.on("block", cb)`, `provider.on(filter, cb)`, `contract.on(filter, cb)`. HTTP providers poll; `WebSocketProvider` pushes.
- WebSocket connections drop. Detect close, recreate the provider and resume from the last stored block with `queryFilter`.
- Remove listeners with `off`/`removeAllListeners`; call `destroy()` when finished.

## ENS

- `provider.resolveName("name.eth")` returns an address or `null`; `provider.lookupAddress(address)` returns the primary name or `null`.
- Forward-resolve a reverse-resolved name before trusting it, and never authorize by ENS name alone.
