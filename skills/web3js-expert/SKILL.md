---
name: web3js-expert
description: >-
  Maintains, secures and migrates existing web3.js code. web3.js was sunset by ChainSafe on 2025-03-04 and its repository archived on 2025-03-05, so v1 and v4 get no security fixes, and this skill does not recommend it for new work. Covers reading web3.js v1 and v4 code (contract.methods, PromiEvent, BN versus bigint, providers, accounts and wallet), containing its risks, and a step-by-step migration to ethers v6 or viem with a side-by-side API mapping. Use when a repository imports "web3" or web3-* packages, when triaging npm audit findings in them, or when planning a move off web3.js. Not for new dApp code (use ethersjs-expert), protocol questions (use ethereum-expert) or Solidity (use solidity-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Web3.js Legacy Maintenance and Migration

This skill is for code that already uses web3.js. The library was sunset and its repository archived in March 2025, so the goal is to keep existing code running safely for as long as it must and to move it onto ethers v6 or viem in small, verifiable steps. It does not recommend web3.js for new projects. The API mapping and the v1 versus v4 differences were checked by running the three libraries side by side.

> Verified against web3 4.16.0 (npm `latest`, published 2024-12-03), web3 1.10.4 (npm `legacy`, 2024-02-05), ethers 6.17.0, viem 2.57.13 (a `3.0.0-next` prerelease exists on the `next` tag), Node 22 (2026-10). The sunset and archive dates are from the web3/web3.js repository banner.

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

- Covered: recognizing web3.js v1 and v4 code, understanding its type conventions, keeping it stable while it remains in production, assessing the supply-chain and security impact of an unmaintained dependency, and migrating to ethers v6 or viem.
- Not covered: writing new application code (use ethersjs-expert, or the viem documentation), Ethereum protocol behavior such as gas, finality and reorgs (ethereum-expert), contract development and tests (solidity-expert, hardhat-expert, foundry-expert), and exploit review (smart-contract-security-expert).
- Note that `@solana/web3.js` is a different, unrelated library.

## 2. Core Expertise

| Topic | Key facts |
|---|---|
| Status | The web3/web3.js repository banner states the libraries were sunset on 2025-03-04 and the repository was archived (read-only) on 2025-03-05. The last npm releases are 4.16.0 (2024-12-03) and 1.10.4 (2024-02-05); later 4.16.1 builds exist only as `dev` prereleases. Nothing is maintained or patched |
| Packages | Umbrella `web3` plus `web3-eth`, `web3-eth-contract`, `web3-eth-accounts`, `web3-eth-abi`, `web3-utils`, `web3-core`, `web3-validator`, `web3-providers-http`, `web3-providers-ws` and others at the same major |
| v1 conventions | Numbers return as strings or JS numbers, `web3.utils.toBN` and BN.js, callbacks and PromiEvent, `new Web3(url)` as default export, `contract.methods.fn().call()/send()` |
| v4 conventions | Named export `import { Web3 } from 'web3'`, `bigint` for quantities by default, `web3.eth.getBlockNumber()` returns `bigint`, `FMT_NUMBER` and `FMT_BYTES` return formats, plugins, TypeScript-first types |
| v4 local signing | `web3-eth-accounts` 4.3.1 implements legacy, EIP-2930 and EIP-1559 transactions only; there are no classes for blob (`0x03`) or set-code (`0x04`) transactions |
| Missing helpers | v4 has no `eth_getBlockReceipts`, `eth_blobBaseFee` or `eth_simulateV1` helper methods; call them through `web3.requestManager.send` or migrate |
| Targets | ethers 6.17.0 (class-based, `bigint`) and viem 2.57.13 (functional, strongly typed from ABIs). Both are maintained and support current transaction types |
| Why migrate | No security updates, a growing `npm audit` backlog in transitive dependencies, no support for new protocol features, and shrinking ecosystem tooling |

## 3. Workflow

1. Inventory: list every `web3`, `web3-*` and `@types/web3` dependency and import (`rg "from 'web3'|require\('web3'\)|web3-"`), the major version in the lockfile, and which modules use it (backend, scripts, front end).
2. Identify the major version from the code shape: `new Web3(url)` with `toBN`/string numbers is v1; `import { Web3 } from 'web3'` with `bigint` is v4. Read [references/maintaining-web3js-v1-v4.md](references/maintaining-web3js-v1-v4.md) for the differences.
3. Stabilize first: pin exact versions, add `overrides` (npm) or `resolutions` (yarn) only for vulnerable transitive packages after testing, set an explicit provider everywhere, and add characterization tests around the web3.js-dependent functions.
4. Wrap: put all chain access behind a small interface (read balance, call contract, send transaction, get logs, sign) so call sites stop importing web3.js directly.
5. Migrate module by module, using the mapping in [references/migration-to-ethers-and-viem.md](references/migration-to-ethers-and-viem.md). Run old and new implementations on the same inputs and compare results (parity tests).
6. Remove web3.js dependencies, lockfile entries and polyfills (`Buffer`, `process`) that existed only for it, and re-run `npm audit` and the full test suite.
7. Record decisions and remaining legacy islands (for example a v1 script scheduled for deletion) with owners and removal dates in the repository.

## 4. Decision Rules

- New code does not use web3.js. Start new modules on ethers v6 or viem even while old modules stay.
- Choose ethers v6 when the codebase is class and provider oriented, uses `Wallet`, `Contract` and event listeners heavily, and the team wants the smallest conceptual jump from web3.js. Choose viem when the codebase is TypeScript-heavy and wants ABI-derived types, tree-shaking, wagmi for React, or a functional client model.
- One target per repository. Mixing ethers and viem in the same module doubles the review surface.
- Migrate v1 to ethers or viem directly; going v1 to v4 first only moves you from one unmaintained version to another, unless a very large v1 code base must first be made type-safe.
- Keep web3.js temporarily when: the module is scheduled for deletion, it is a one-off script with no secrets or network exposure, or a vendor SDK pins it. Isolate those in a separate package without production keys.
- Prefer migrating read paths first (balances, calls, logs), then write paths (signing and sending), because reads are easy to parity-test and writes need testnet rehearsal.
- Do not rewrite business logic during the migration. Change only the chain access layer, and keep numeric types explicit at each boundary.

## 5. Coding Standards

- When touching existing web3.js code, keep its style and fix only what the task requires; add types and tests before refactoring.
- Treat numbers as untrusted until normalized: v1 returns strings or numbers, v4 returns `bigint` unless a return format says otherwise. Convert at the boundary: `BigInt(x)` for v1 values, and avoid `Number()` on wei amounts.
- Always pass `from` explicitly to `send` and `estimateGas`; do not rely on `defaultAccount`.
- Always construct `Web3` with an explicit provider. A v4 `Web3` created without a provider tried to contact a default hosted RPC endpoint in a signing test, which can leak activity or fail in restricted networks.
- Never call `web3.eth.accounts.wallet.add` with a private key from a string literal or a file in the repository; read it from the environment or a signer service, and prefer remote signing.
- In v4, `wallet.add(privateKey)` returns the wallet (use `wallet[0]` or `wallet.get(0)` for the account); in v1 it returns the account. Do not port the line verbatim.
- For new helper code written during the migration, follow ethersjs-expert or the viem documentation, and write TypeScript.

## 6. Project Structure

```
src/
├── chain/
│   ├── types.ts              # ChainClient interface used by the rest of the app
│   ├── web3js.adapter.ts     # legacy implementation (to be deleted)
│   ├── ethers.adapter.ts     # target implementation (or viem.adapter.ts)
│   └── index.ts              # exports one implementation chosen by config during rollout
├── features/                 # business code: imports only ../chain, never web3 or ethers directly
└── abi/                      # JSON ABIs as const, shared by both adapters
test/
├── parity/                   # same inputs through both adapters, compare outputs
└── fixtures/                 # recorded JSON-RPC responses for deterministic tests
```

## 7. Design Patterns

- **Adapter plus strangler**: define a narrow `ChainClient` interface, implement it twice, route traffic by configuration, and delete the legacy adapter after the new one has run in production.
- **Parity tests**: for encoding, units, hashing, signing and decoding, feed identical inputs to both implementations. These are pure functions, so they need no network. The reference contains a runnable example.
- **Recorded RPC fixtures**: run both clients against a local fake JSON-RPC server to verify request shapes and result conversion (bigint versus number versus string).
- **Boundary normalization**: convert every quantity to `bigint` and every address to a checksummed string at the adapter boundary; the rest of the code never sees web3.js types.
- **Canary rollout**: send a small share of read traffic through the new adapter first, compare outputs in logs, then move writes on a testnet or low-value account.

## 8. Best Practices

- Migrate one concern at a time: units and hashing, then ABI encoding, then reads, then event handling, then signing, then sending.
- Keep a mapping document in the repository listing each replaced web3.js call and its new equivalent.
- Check ABI formats: web3.js v1 accepts loose JSON ABI; ethers and viem accept human-readable ABI fragments too, and viem derives types from `as const` ABIs.
- Normalize addresses: ethers rejects mixed-case addresses with a wrong checksum, so test fixtures with invalid case will fail after migration; fix the data, not the check.
- Replace callbacks and event-emitter style (`.on('transactionHash')`, `.once('receipt')`) with promises and explicit receipt waits.
- Remove browser polyfills and Node-only workarounds that existed for web3.js, one at a time, with a build check.

## 9. Performance

- web3.js v4 batches through `web3.BatchRequest`; ethers v6 `JsonRpcProvider` batches concurrent calls into one HTTP request by default, and viem batches with `http(url, { batch: true })`. In a mock test, two parallel reads produced one HTTP request in both ethers (default) and viem (batch enabled).
- viem and ethers are tree-shakable enough that front-end bundles typically shrink after removing web3.js; measure with your bundler.
- Avoid polling loops of `eth_getBalance`; use subscriptions or block-driven updates, and cache by block number.
- Do not create a new provider or client per request; construct once and reuse.

## 10. Security

- No security updates: a vulnerability found in web3.js or its internals will not be fixed. A fresh `npm install web3@4.16.0` followed by `npm audit` (2026-10) reported 19 high-severity findings from transitive dependencies (for example `zod` through `web3-validator`), and `web3@1.10.4` reported 49 findings including 3 critical ones in `request`, `form-data` and `tar`. Newer releases of web3.js that would fix them will not be published.
- Do not paper over findings with `npm audit fix --force`. Use `overrides` for specific packages only after tests pass, and treat the override as technical debt that ends with the migration.
- Treat web3.js as a risk for any process that holds private keys or signs value-bearing transactions. Migrate signing paths before read-only paths if you must prioritize by risk.
- Private keys: never place keys in source, front-end bundles or `.env` files committed to git; use a KMS, HSM or hardware signer, and keep wallets in memory only as long as needed.
- Supply chain: pin versions and lockfiles, verify package integrity, and watch for look-alike packages (`web3-*` names are abundant). Prefer packages published under the official scopes and review install scripts.
- A default provider in a v4 `Web3` instance can send RPC traffic to a third-party endpoint; always set the provider.
- Validate user-provided addresses and amounts before building transactions, and keep `chainId` pinned in configuration.

## 11. Testing

- Characterization tests: before changing anything, record the current outputs of web3.js-dependent functions for representative inputs and keep them as golden files.
- Parity tests for pure functions: `toWei`/`parseUnits`, `keccak256`, `soliditySha3` versus `solidityPackedKeccak256`, `encodeFunctionCall` versus `encodeFunctionData`, `encodeParameters`, `sign` versus `signMessage`, `signTypedData`, `recover` versus `verifyMessage`. All of these produced identical outputs across web3 4.16.0, ethers 6.17.0 and viem 2.57.13 in a verification run.
- Fake JSON-RPC server tests for reads and event decoding; compare value types after conversion.
- Testnet rehearsal for writes: Sepolia or Hoodi, with the new client sending real transactions from a throwaway key and the old client verifying them.
- Property to test explicitly: same raw signed transaction bytes for the same fields (EIP-1559 transactions signed with the same key produced the same raw transaction in ethers and viem; web3.js signs through the same fields but needs a provider for missing ones).
- Run `npm audit` in CI and fail the build on new high findings outside an allowlist with expiry dates.

## 12. Review Checklist

- [ ] No new `web3` imports are introduced; new code uses the migration target.
- [ ] Every `Web3` instance has an explicit provider, and `chainId` is validated at startup.
- [ ] Numeric conversions at the boundary are explicit, with no `Number()` on wei values.
- [ ] Private keys come from a secure source and never from code, config in git, or the front end.
- [ ] `overrides` or `resolutions` entries have a comment with the advisory and a removal condition.
- [ ] Parity or characterization tests exist for each migrated function.
- [ ] Legacy islands are listed with owners and a removal date.
- [ ] `npm audit` output is reviewed and the remaining web3.js findings are acknowledged in writing.
- [ ] Callbacks and `PromiEvent` handlers have equivalents (receipt waits, error handling) in the new code.

## 13. Production Notes

- Plan the migration as a project with milestones; an unmaintained dependency in a signing path is a standing risk, not a backlog item.
- Keep rollback simple: the adapter switch is configuration, and the legacy adapter stays until the new one has handled real traffic for a full release cycle.
- Watch for behavior differences after switching: nonce management (web3.js can fill nonces from the provider, ethers `Wallet` with a provider does too, but concurrent sends need an explicit nonce manager), gas estimation and fee defaults, polling intervals and receipt confirmation semantics.
- ethers returns block numbers as `number` and amounts as `bigint`; viem returns both as `bigint`; web3 v4 returns `bigint` for both by default, while v1 returns numbers and strings. Update every comparison and every JSON serialization (`bigint` is not JSON serializable without a replacer).
- Front-end wallets: EIP-1193 providers (`window.ethereum`) and EIP-6963 discovery work with all three libraries; wagmi (viem-based) or ethers `BrowserProvider` replace `new Web3(window.ethereum)`.
- Document which environments still run web3.js so incident response knows where an unpatched library lives.

## 14. Examples

Reading a token balance and sending a transfer, in web3.js v4 and its replacements (ABI abbreviated; keys come from the environment):

```js
// web3.js v4 (legacy)
import { Web3 } from 'web3';
const web3 = new Web3(process.env.RPC_URL);
const sender = web3.eth.accounts.wallet.add(process.env.PRIVATE_KEY)[0];
const token = new web3.eth.Contract(erc20Abi, TOKEN);
const balance = await token.methods.balanceOf(sender.address).call();      // bigint
const receipt = await token.methods.transfer(to, 1_000_000n).send({ from: sender.address });
```

```js
// ethers v6
import { JsonRpcProvider, Wallet, Contract } from 'ethers';
const provider = new JsonRpcProvider(process.env.RPC_URL);
const signer = new Wallet(process.env.PRIVATE_KEY, provider);
const token = new Contract(TOKEN, erc20Abi, signer);
const balance = await token.balanceOf(signer.address);                      // bigint
const tx = await token.transfer(to, 1_000_000n);
const receipt = await tx.wait();                                            // throws CALL_EXCEPTION on revert, TRANSACTION_REPLACED if replaced
```

```js
// viem
import { createPublicClient, createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { mainnet } from 'viem/chains';
const account = privateKeyToAccount(process.env.PRIVATE_KEY);
const publicClient = createPublicClient({ chain: mainnet, transport: http(process.env.RPC_URL) });
const walletClient = createWalletClient({ account, chain: mainnet, transport: http(process.env.RPC_URL) });
const balance = await publicClient.readContract({ address: TOKEN, abi: erc20Abi, functionName: 'balanceOf', args: [account.address] });
const { request } = await publicClient.simulateContract({ account, address: TOKEN, abi: erc20Abi, functionName: 'transfer', args: [to, 1_000_000n] });
const hash = await walletClient.writeContract(request);
const receipt = await publicClient.waitForTransactionReceipt({ hash });      // receipt.status is 'success' or 'reverted'
```

A narrow adapter interface that lets the rest of the code stay unaware of the library during migration:

```ts
export interface ChainClient {
  getBalance(address: string): Promise<bigint>;
  readErc20Balance(token: string, holder: string): Promise<bigint>;
  getTransferLogs(token: string, fromBlock: bigint, toBlock: bigint): Promise<{ from: string; to: string; value: bigint; blockNumber: bigint }[]>;
}
```

A pure-function parity test (no network) that guards the migration of units, hashing, ABI encoding and signing:

```js
import { Web3 } from 'web3';
import * as ethers from 'ethers';
import * as viem from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import assert from 'node:assert/strict';

const web3 = new Web3('http://127.0.0.1:1'); // never contacted by these calls
const to = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
assert.equal(BigInt(web3.utils.toWei('1.5', 'ether')), ethers.parseEther('1.5'));
assert.equal(ethers.parseEther('1.5'), viem.parseEther('1.5'));
const data = [
  web3.eth.abi.encodeParameters(['address', 'uint256'], [to, 5]),
  ethers.AbiCoder.defaultAbiCoder().encode(['address', 'uint256'], [to, 5n]),
  viem.encodeAbiParameters(viem.parseAbiParameters('address, uint256'), [to, 5n]),
];
assert.ok(data.every((d) => d === data[0]));
// Test-only key derived from a label; never reuse a real key in tests.
const pk = viem.keccak256(viem.toHex('parity-test'));
const sigs = [web3.eth.accounts.sign('hello', pk).signature, await new ethers.Wallet(pk).signMessage('hello'), await privateKeyToAccount(pk).signMessage({ message: 'hello' })];
assert.ok(sigs.every((s) => s === sigs[0]));
```

The full mapping tables are in [references/migration-to-ethers-and-viem.md](references/migration-to-ethers-and-viem.md).

## 15. Common Mistakes

- **Starting new work on web3.js** because the old code uses it: new modules should use the migration target.
- **Upgrading v1 to v4 as the "fix"**: v4 is also archived and unpatched; the change adds migration work without removing the risk.
- **`npm audit fix --force`**: can install incompatible majors or remove packages silently. Use targeted overrides with tests.
- **`Number(balance)` on wei values**: loses precision above 2^53. Keep `bigint`.
- **Assuming v1 and v4 return the same types**: v1 returns strings and numbers, v4 returns `bigint`; code that does `a + b` on strings concatenates.
- **Copying `wallet.add(pk)` between versions**: v4 returns the wallet, v1 returns the account.
- **Leaving `new Web3()` without a provider**: v4 can fall back to a hosted default endpoint.
- **Porting `.on('transactionHash')` handlers verbatim**: ethers and viem expose the hash and receipt as separate awaited steps.
- **Mixed-case address fixtures**: ethers throws "bad address checksum" for wrongly cased addresses; correct the fixture or lowercase it.
- **Expecting a receipt object for failed transactions**: ethers v6 `tx.wait()` throws `CALL_EXCEPTION` on a revert and `TRANSACTION_REPLACED` on replacement, and resolves `null` only for `wait(0)` before mining; viem's `waitForTransactionReceipt` returns the receipt with `status: 'reverted'`. Adjust error handling for each.
- **Migrating signing and sending in the same commit as the business refactor**: keep changes separable so a regression has one suspect.
- **Forgetting JSON serialization**: `JSON.stringify` throws on `bigint`; add a replacer or convert at the API boundary.
- **Confusing `@solana/web3.js` with web3.js**: they are unrelated; a Solana advisory does not apply to this library and vice versa.

## 16. References

- [references/migration-to-ethers-and-viem.md](references/migration-to-ethers-and-viem.md): side-by-side mapping for providers, accounts, contracts, events, units, hashing, ABI encoding, signing, transactions, subscriptions, batching, errors and types, with a phased migration plan.
- [references/maintaining-web3js-v1-v4.md](references/maintaining-web3js-v1-v4.md): reading v1 and v4 code, type conventions, return formats, PromiEvent, subscriptions, plugins, known gaps, and safe maintenance practices.
- Official docs: https://github.com/web3/web3.js , https://docs.ethers.org/v6/ , https://viem.sh/ , https://eips.ethereum.org/EIPS/eip-1193 , https://eips.ethereum.org/EIPS/eip-6963
