# Contracts, Events, ABI Coding and Signing (ethers v6)

Reference for `Contract`, `Interface`, logs, error decoding, Multicall3 and signatures. Code was type-checked against ethers 6.17.0.

## Contract calls

```typescript
const erc20 = new Contract(address, abi, runner); // runner: Provider (read) or Signer (read/write)
await erc20.balanceOf(user);                   // view call, returns decoded value (bigint)
await erc20.transfer.staticCall(to, amount);   // simulate a state-changing call
await erc20.transfer.estimateGas(to, amount);  // gas estimate
await erc20.transfer.populateTransaction(to, amount); // unsigned request
const tx = await erc20.transfer(to, amount, { gasLimit: 100_000n }); // overrides are the last argument
await erc20.getAddress();                      // replaces contract.address
await erc20.connect(otherSigner);              // new instance with another runner
```

- Overloaded functions need the full signature: `contract.getFunction("safeTransferFrom(address,address,uint256)")` returns the callable for that overload.
- Return values: a single output is returned directly; several outputs come back as a `Result` (array-like, named, immutable). Use `.toObject()` or `.toArray()` for plain copies.
- Deploy with `ContractFactory`; `await contract.waitForDeployment()` replaces `deployed()`.

## Interface

```typescript
import { AbiCoder, Interface } from "ethers";

const iface = new Interface(["function transfer(address to, uint256 amount) returns (bool)"]);
const data = iface.encodeFunctionData("transfer", [to, amount]);
iface.getFunction("transfer")!.selector;           // 0xa9059cbb
const out = iface.decodeFunctionResult("transfer", returnData);
AbiCoder.defaultAbiCoder().encode(["uint256", "address"], [1n, to]);
```

Prefer human-readable ABIs declared `as const` for small surfaces and full JSON ABIs (from the compiler output) for large ones.

## Multicall3

```typescript
import { Contract, Interface, type JsonRpcProvider } from "ethers";

const MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"; // same address on most chains; confirm on the target chain
const multicallAbi = [
  "function aggregate3((address target, bool allowFailure, bytes callData)[] calls) payable returns ((bool success, bytes returnData)[] returnData)",
];
const erc20 = new Interface(["function balanceOf(address) view returns (uint256)"]);

export async function balances(provider: JsonRpcProvider, tokens: string[], holder: string): Promise<bigint[]> {
  const mc = new Contract(MULTICALL3, multicallAbi, provider);
  const calls = tokens.map((t) => ({ target: t, allowFailure: true, callData: erc20.encodeFunctionData("balanceOf", [holder]) }));
  const results: { success: boolean; returnData: string }[] = await mc.aggregate3.staticCall(calls);
  return results.map((r) => (r.success ? (erc20.decodeFunctionResult("balanceOf", r.returnData)[0] as bigint) : 0n));
}
```

Verify Multicall3 is deployed on the chain (`getCode`) before relying on it.

## Events

- Filters: `contract.filters.Transfer(from, to)` matches indexed arguments only; `null` is a wildcard.
- Backfill: `contract.queryFilter(filter, fromBlock, toBlock)` in chunks sized to the provider's range limit.
- Live: `contract.on(filter, (from, to, value, payload) => ...)`; the last argument is a `ContractEventPayload` with `payload.log` (`blockNumber`, `blockHash`, `transactionHash`, `index`, `removed`).
- Parsing arbitrary logs: `iface.parseLog({ topics, data })` returns `null` when the log does not match the ABI.
- Reorgs: key stored events by `(blockHash, index)`, wait for confirmations before crediting value, and re-scan the last N blocks on restart.

```typescript
import { Interface, type Log } from "ethers";

const iface = new Interface(["event Transfer(address indexed from, address indexed to, uint256 value)"]);

export function decodeLogs(logs: readonly Log[]) {
  return logs.flatMap((log) => {
    const parsed = iface.parseLog({ topics: [...log.topics], data: log.data });
    return parsed ? [{ name: parsed.name, args: parsed.args.toObject(), block: log.blockNumber, index: log.index }] : [];
  });
}
```

## Errors

- Reverts surface as `CALL_EXCEPTION`. When the ABI includes the custom error, `err.revert` holds `{ name, signature, args }`; for `Error(string)` use `err.reason`.
- For raw revert data use `iface.parseError(data)`, which returns `null` for unknown selectors.
- Other codes: `INSUFFICIENT_FUNDS`, `NONCE_EXPIRED`, `REPLACEMENT_UNDERPRICED`, `TIMEOUT`, `ACTION_REJECTED`, `NETWORK_ERROR`, `SERVER_ERROR`. Test with `isError(err, "CODE")` for narrowing.
- Do not match on `err.message`; wording differs by provider and version.

## Units and bigint

```typescript
import { formatUnits, parseUnits } from "ethers";

const amount = parseUnits("1.5", 6);          // 1500000n
const fee = (amount * 30n) / 10_000n;         // multiply first, then divide
formatUnits(amount - fee, 6);                 // "1.4955" (display only)
```

`parseUnits` throws on more fractional digits than `decimals`; surface that to the user instead of rounding silently. Use `FixedNumber` only when decimal fixed-point semantics are needed.

## Signing

- `signer.signMessage(msg)` signs the EIP-191 personal-message hash. Use it for human-readable login statements (include domain, nonce, expiry); verify with `verifyMessage(msg, sig)` and compare to the expected address.
- `signer.signTypedData(domain, types, value)` signs EIP-712 data. The `types` object must not include `EIP712Domain`; `primaryType` is inferred. Verify with `verifyTypedData` or compute the digest with `TypedDataEncoder.hash`.
- Include `chainId` (`bigint`) and `verifyingContract` in the domain, plus a nonce and a deadline in the message, and have the contract enforce them.
- Contract wallets (ERC-1271) cannot be verified off-chain by recovery; call `isValidSignature(hash, sig)` on the account and expect the magic value `0x1626ba7e`.
- Use `Signature.from(sig)` to split into `r`, `s`, `v` (or `yParityAndS`) for contract calls such as `permit`.
