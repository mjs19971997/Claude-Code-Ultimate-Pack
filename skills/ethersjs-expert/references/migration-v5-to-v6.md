# Migrating from ethers v5 to v6

Mapping of the common v5 APIs to v6. v5 remains available as `ethers@5` (npm tag `legacy-v5`); v6 is `latest`. Names below were checked against ethers 6.17.0 exports.

## Imports and namespaces

| v5 | v6 |
|---|---|
| `ethers.utils.parseUnits`, `formatUnits`, `parseEther`, `formatEther` | `parseUnits`, `formatUnits`, `parseEther`, `formatEther` (top-level) |
| `ethers.providers.JsonRpcProvider` | `JsonRpcProvider` |
| `ethers.providers.Web3Provider` | `BrowserProvider` |
| `ethers.providers.WebSocketProvider` | `WebSocketProvider` |
| `ethers.providers.FallbackProvider` | `FallbackProvider` (config adds `weight`, `priority`, `stallTimeout`) |
| `ethers.constants.AddressZero`, `HashZero` | `ZeroAddress`, `ZeroHash` |
| `ethers.constants.MaxUint256` | `MaxUint256` (a `bigint`) |
| `ethers.utils.Interface` | `Interface` |
| `ethers.utils.defaultAbiCoder` | `AbiCoder.defaultAbiCoder()` |
| `ethers.utils.id`, `keccak256` | `id`, `keccak256` |
| `ethers.utils.solidityKeccak256` | `solidityPackedKeccak256` |
| `ethers.utils.arrayify` | `getBytes` |
| `ethers.utils.hexlify` | `hexlify` |
| `ethers.utils.hexValue` | `toQuantity` |
| `ethers.utils.formatBytes32String` | `encodeBytes32String` (and `decodeBytes32String`) |
| `ethers.utils.splitSignature` | `Signature.from(sig)` |
| `ethers.utils.verifyMessage` | `verifyMessage` |
| `ethers.utils._TypedDataEncoder` | `TypedDataEncoder` |
| `ethers.utils.verifyTypedData` | `verifyTypedData` |
| `Wallet.fromMnemonic` | `Wallet.fromPhrase` |
| `signer._signTypedData` | `signer.signTypedData` |

## Numbers

- `BigNumber` is gone; use native `bigint`. `BigNumber.from(x)` becomes `BigInt(x)` or `getBigInt(x)`; `a.add(b)`, `a.mul(b)`, `a.div(b)` become `a + b`, `a * b`, `a / b` (integer division truncates).
- Comparison: `a.gt(b)` becomes `a > b`; `a.eq(b)` becomes `a === b`.
- Everything that returned `BigNumber` (balances, gas used, block numbers for chain ids in `getNetwork()`, `value`) now returns `bigint`. `getNetwork().chainId` is a `bigint`: compare with `1n`, not `1`.
- JSON serialization: `JSON.stringify` throws on `bigint`; convert with `.toString()` or a replacer.

## Contracts

| v5 | v6 |
|---|---|
| `contract.address` | `await contract.getAddress()` (or `contract.target`) |
| `await contract.deployed()` | `await contract.waitForDeployment()` |
| `contract.callStatic.fn(...)` | `contract.fn.staticCall(...)` |
| `contract.estimateGas.fn(...)` | `contract.fn.estimateGas(...)` |
| `contract.populateTransaction.fn(...)` | `contract.fn.populateTransaction(...)` |
| `contract.functions.fn(...)` (array result) | `contract.fn(...)` |
| `receipt.events` | `receipt.logs` (parse with `contract.interface.parseLog`) |
| `contract.on("Transfer", ...)` | still supported; filters via `contract.filters.Transfer(...)`; `on` is async |
| `contract.interface.getSighash(...)` | `contract.interface.getFunction(name)!.selector` |
| `Result` mutable arrays | `Result` is immutable; use `toArray()` / `toObject()` |

## Providers and signers

- `getSigner()` on a browser provider is async: `await provider.getSigner()`.
- `provider.getGasPrice()` is replaced by `provider.getFeeData()` (`gasPrice`, `maxFeePerGas`, `maxPriorityFeePerGas`).
- `new Web3Provider(window.ethereum)` becomes `new BrowserProvider(window.ethereum)`; request accounts with `provider.send("eth_requestAccounts", [])`.
- Transaction `type` and fee fields use `bigint`; `gasLimit` is `bigint`. Override objects accept `bigint`.
- `tx.wait()` now throws `CALL_EXCEPTION` when the receipt status is 0 and `TRANSACTION_REPLACED` on replacement.
- Network detection is stricter: JSON-RPC providers verify the chain id; use `staticNetwork` only for fixed URLs.
- JSON-RPC requests are batched by default; disable with `batchMaxCount: 1` if your endpoint rejects batches.

## Errors

- Error codes were reorganized; branch with `isError(err, "CALL_EXCEPTION")` and read `err.revert` for custom errors. Message strings are not stable.
- Insufficient funds, nonce and replacement conditions have their own codes (`INSUFFICIENT_FUNDS`, `NONCE_EXPIRED`, `REPLACEMENT_UNDERPRICED`).

## Migration procedure

1. Pin `ethers@6` in a branch; run the TypeScript compiler. Most breakage surfaces as type errors on `BigNumber` and removed namespaces.
2. Replace namespaces and constants using the tables above.
3. Convert arithmetic to `bigint`; review every division and every place a number is compared with a chain id.
4. Replace `callStatic`, `estimateGas`, `populateTransaction` and `deployed()` usages.
5. Update event parsing: `receipt.events` to `receipt.logs` plus `parseLog`.
6. Re-run tests against a fork; check gas and fee code paths and error handling.
7. Libraries that wrap ethers (hardhat plugins, wagmi adapters, typechain targets) must also be v6-compatible; check each package's current docs.
