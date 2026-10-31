---
name: account-abstraction-expert
description: >-
  Designs, builds and reviews Ethereum account abstraction: ERC-4337 (EntryPoint v0.6 to v0.9, UserOperation and PackedUserOperation, bundlers and the eth_*UserOperation RPC, paymasters, ERC-7562 validation rules and reputation), EIP-7702 delegation of EOAs, smart accounts (Safe, Kernel, OpenZeppelin Account, modular ERC-7579 accounts), session keys, passkey (P-256, WebAuthn) signers and their security pitfalls. Use when writing validateUserOp or validatePaymasterUserOp, an EIP-7702 delegate contract, signing authorizations, packing gas fields, choosing an EntryPoint version, integrating a bundler or paymaster with viem or permissionless, installing ERC-7579 modules, or auditing smart-account code. Not for general Solidity language and patterns (use solidity-expert), ethers.js client code (use ethersjs-expert), audits of non-account contracts (use smart-contract-security-expert) or Ethereum protocol and node topics (use ethereum-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Account Abstraction Expert

This skill covers programmable accounts on Ethereum and EVM chains: ERC-4337 accounts that are validated and paid for through an EntryPoint contract and relayed by bundlers, EIP-7702 delegations that give an existing EOA contract code, and the account implementations and modules built on both. It treats validation code as the most security-critical code in a wallet, because it decides who can spend, and as code that runs under extra restrictions (ERC-7562) so that bundlers can accept it without being attacked. Version numbers, addresses and limits change; the ones below were checked against the sources listed and should be re-read from the chain or the current docs before deployment.

> Verified against ERC-4337 (Final), ERC-7562 (Review), EIP-7702 (Final; Pectra mainnet 2025-05-07), EIP-7951 (Final; Fusaka mainnet 2025-12-03), ERC-7579 (Draft), eth-infinitism `account-abstraction` v0.9.0 (git tag; npm `@account-abstraction/contracts` 0.8.0 latest, 0.9.0-rc.1), OpenZeppelin Contracts 5.6.1, viem 2.57.13, permissionless 0.5.2, Safe 1.5.0 with Safe4337Module 0.3.0, and Kernel v3.3 and v4.0 (2026-10). Solidity examples compile with solc 0.8.38; TypeScript type-checks against viem 2.57.13.

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

- Covered: the ERC-4337 flow (account, EntryPoint, bundler, paymaster, factory, aggregator), UserOperation fields and packing, gas fields and estimation, nonces with keys, validation data and time ranges, deposits and stakes, ERC-7562 rules and reputation, the bundler and paymaster JSON-RPC methods (ERC-7769, ERC-7677), EIP-7702 authorizations and delegate contracts, ERC-1271 and ERC-7739 signatures, ERC-6492 for undeployed accounts, Safe, Kernel and OpenZeppelin accounts, ERC-7579 modules, session keys, passkeys and P-256 verification, wallet batching (ERC-5792).
- Not covered: Solidity language features and generic contract patterns (solidity-expert), ethers.js usage (ethersjs-expert), audits of DeFi or token contracts that are not accounts (smart-contract-security-expert, defi-expert), consensus, clients and network upgrades in general (ethereum-expert), Solana (solana-expert).

## 2. Core Expertise

| Component | Role |
|---|---|
| Account | Contract with `validateUserOp(PackedUserOperation, bytes32 userOpHash, uint256 missingAccountFunds)`; checks the signature, pays the EntryPoint what it owes, then executes `callData` |
| EntryPoint | Singleton that runs `handleOps`: a validation loop over all operations, then an execution loop; charges deposits, pays the bundler's `beneficiary` |
| Bundler | Node that accepts operations through `eth_sendUserOperation`, simulates them under ERC-7562 rules, and submits `handleOps` transactions |
| Paymaster | Contract with `validatePaymasterUserOp` and optional `postOp`; pays gas from its EntryPoint deposit for operations it approves |
| Factory | Deploys the account at a counterfactual address (CREATE2) on the first operation via `initCode` |
| Aggregator | Validates a batch of signatures at once; must be staked |

EntryPoint versions (canonical addresses are identical on every chain where deployed; confirm deployment on the target chain):

| Version | Address | Notes |
|---|---|---|
| v0.6 | `0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789` | Unpacked `UserOperation`; legacy, avoid for new accounts |
| v0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | `PackedUserOperation`, separate paymaster gas limits, 10 percent penalty on unused execution gas, `IAccountExecute` |
| v0.8 | `0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108` | EIP-712 `userOpHash` (domain `ERC4337`, version `1`), native EIP-7702 support (`0x7702` initCode flag), unused-gas penalty only above 40,000 gas, needs EIP-1153 |
| v0.9 | `0x433709009B8330FDa32311DF1C2AFA402eD8D009` | ABI-compatible with v0.7 and v0.8; `paymasterSignature` for parallel signing, block-number validity ranges, `initCode` ignored when the account exists, `getCurrentUserOpHash()`; a separate bundler mempool |

Related standards: ERC-7562 (validation scope rules, Review), ERC-7769 (bundler JSON-RPC, Draft), ERC-7677 (paymaster web service, Review), ERC-7579 (modular accounts, Draft), ERC-6900 (modular accounts, Draft), ERC-7821 (minimal batch executor, Draft), ERC-7739 (readable typed signatures for accounts, Draft), ERC-6492 (signatures from undeployed accounts, Final), ERC-5792 (`wallet_sendCalls`, Final), EIP-7702 (set code for EOAs, Final), EIP-7951 (`P256VERIFY` precompile at `0x100`, Final) and RIP-7212 (the same interface on rollups).

## 3. Workflow

1. Pick the account model: a new smart account (ERC-4337 with a factory), an EOA upgraded with EIP-7702, or both (a 7702 delegate that also implements `validateUserOp`).
2. Pick the EntryPoint version supported by the bundlers, paymasters and account implementations on every target chain; record it in config, not in code comments.
3. Choose an audited implementation (Safe with Safe4337Module, Kernel, OpenZeppelin `Account`, eth-infinitism `SimpleAccount` or `Simple7702Account`) and add only the modules or signers you need.
4. Define signers and permissions: owner key, passkeys, multisig thresholds, session keys with explicit scopes and expiry, recovery path.
5. Write tests: validation success and failure (`SIG_VALIDATION_FAILED` returned, not reverted), nonce keys, prefund, paymaster approval and rejection, time ranges, ERC-1271 signing, upgrade and module install paths.
6. Simulate operations with a bundler on a testnet or local fork; check ERC-7562 compliance with the bundler's debug tracing (`debug_traceCall` based checks or the bundler's validation mode).
7. Integrate the client (viem `createBundlerClient` or permissionless), estimate gas through the bundler, add paymaster data, sign, send, and wait for the UserOperation receipt.
8. Before mainnet: audit or review, stake factories and paymasters that need storage access, fund paymaster deposits, monitor deposits and failed operations.

## 4. Decision Rules

- New accounts target EntryPoint v0.8 or v0.9 if the chosen bundler and paymaster support it; v0.7 when the account implementation is only audited for v0.7 (for example Safe4337Module 0.3.0). Never mix versions in one account without explicit support.
- Signature mismatches return `SIG_VALIDATION_FAILED` (1) and complete the normal flow; reverts are for malformed input. This keeps gas estimation working.
- Validation code reads only the account's own storage and associated storage; anything else needs a staked entity and still must follow ERC-7562.
- Return validity windows in `validationData` (`validUntil`, `validAfter`) instead of reading `block.timestamp`, which is banned during validation.
- Paymasters that need `postOp` (to charge ERC-20 fees) must be staked: unstaked paymasters may not return a context.
- EIP-7702 delegate contracts keep no initialization that an observer could front-run: either stateless, or initialization signed by the EOA key.
- Use namespaced storage (ERC-7201) in any 7702 delegate so a later delegation to another contract cannot read stale or colliding slots.
- Sign 7702 authorizations for one chain ID; `chain_id = 0` makes the delegation valid on every chain.
- For off-chain message signatures from smart accounts, implement ERC-1271 with ERC-7739-style rehashing so a signature for one account cannot be replayed on another account with the same owner.

## 5. Coding Standards

- Solidity `^0.8.28` for EntryPoint 0.8 and 0.9 integrations; pin the EntryPoint address per version in a constant or immutable and expose it through `entryPoint()`.
- Inherit from audited bases (`Account`, `SignerECDSA`, `SignerP256`, `SignerWebAuthn`, `SignerEIP7702`, `ERC7821`, `BasePaymaster`); override the narrow hooks they provide instead of re-implementing `validateUserOp`.
- Use `ERC4337Utils.packValidationData` (OpenZeppelin) or `_packValidationData` (eth-infinitism `Helpers.sol`) to build validation data; never hand-roll the bit layout.
- Restrict execution entry points to the EntryPoint or the account itself (`onlyEntryPointOrSelf`); restrict `validateUserOp` and paymaster hooks to the EntryPoint.
- Custom errors; events for owner, signer, module and delegation changes.
- Client code keeps private keys out of source: environment variables, a secret manager, a hardware wallet or a passkey.

## 6. Project Structure

```text
contracts/
  accounts/        MyAccount.sol (ERC-4337), Delegate7702.sol (EIP-7702 delegate)
  modules/         validators, executors, hooks (ERC-7579)
  paymasters/      SponsorPaymaster.sol, TokenPaymaster.sol
  factories/       AccountFactory.sol (CREATE2, deterministic salt)
test/
  unit/            signature, nonce, validationData, prefund
  integration/     EntryPoint handleOps with bundler-like simulation
  invariant/       only owner-approved calls execute; deposits never go negative
client/
  bundler.ts       createBundlerClient, account, paymaster wiring
  authorize.ts     EIP-7702 authorization checks and signing
config/
  chains.json      chain id, EntryPoint version and address, bundler and paymaster URLs
```

## 7. Design Patterns

- **Counterfactual account**: address computed from factory, owner and salt before deployment; the first operation carries `initCode` (`factory` and `factoryData`).
- **EIP-7702 upgrade**: the EOA signs an authorization to a delegate; the first operation carries it (`eip7702Auth` in the bundler RPC, `factory = 0x7702` in the operation), later operations do not.
- **Nonce keys**: the 192-bit key in the nonce gives independent sequences, for example key 0 for normal calls and another key for admin or session-key calls, so they do not block each other.
- **Verifying paymaster**: an off-chain service signs approval over the operation fields, chain ID, paymaster address and a validity window; the contract verifies the signature and returns no context.
- **Token paymaster**: charges an ERC-20 in `postOp`, needs a stake, a price source and a pre-charge or allowance check in validation.
- **Modular account (ERC-7579)**: validators (type 1), executors (type 2), fallback handlers (type 3) and hooks (type 4) installed with `installModule`; the account routes `validateUserOp` to the validator selected by the nonce key or signature prefix.
- **Session key**: a scoped signer with expiry, target and selector allowlists, value and spending limits, enforced on-chain by a validator or permission module.
- **Passkey signer**: P-256 public key in the account; WebAuthn assertions verified with `P256VERIFY` where available, with a Solidity fallback where not.

## 8. Best Practices

- Use the bundler's `eth_estimateUserOperationGas` and add margins; keep `verificationGasLimit` above the measured usage by at least the ERC-7562 slack.
- Read `eth_supportedEntryPoints` from the bundler before building operations; refuse to sign for an unknown EntryPoint.
- Keep validation cheap and deterministic: one signature check, nonce, prefund. Move policy checks that need external state into execution or a staked module.
- Simulate every operation before asking the user to sign, and show decoded calls, value and token movements.
- Keep paymaster deposits funded with alerts; a drained deposit fails every sponsored operation.
- For 7702, check the account's current code (`0xef0100 || delegate`) before signing a new authorization, and verify the delegate address against the implementation's published deployment.
- Prefer ERC-5792 `wallet_sendCalls` in dApps so the wallet chooses between 4337, 7702 or plain transactions.

## 9. Performance

- `preVerificationGas` covers calldata and bundler overhead that the EntryPoint cannot measure, plus the 25,000 gas per EIP-7702 authorization; underpricing it gets operations dropped.
- Batch calls in one operation (`executeBatch`, ERC-7821 `execute`) instead of several operations.
- Compress calldata and signatures on rollups where calldata dominates cost; use the chain's gas oracle for L1 data fees.
- P-256 verification through `P256VERIFY` (6,900 gas on L1 per EIP-7951) is far cheaper than Solidity verification; check precompile availability per chain.
- ERC-7579 hooks run on every execution; keep them minimal or scope them to the selectors that need them.

## 10. Security

- **Validation bypass**: missing `onlyEntryPoint` on `validateUserOp`, or execution functions callable by anyone, lets attackers skip signature checks.
- **Signature replay**: the signature must cover `userOpHash`, which already binds chain ID, EntryPoint and every field except the signature. Custom signature schemes must not drop any of these.
- **Prefund theft**: an account that pays `missingAccountFunds` before checking the signature leaks ETH to any caller impersonating the EntryPoint.
- **Paymaster drain**: signatures that do not bind gas limits and fees let a user inflate gas and burn the deposit; signatures without expiry are valid forever.
- **ERC-1271 replay across accounts**: a raw `isValidSignature` that accepts an owner signature for any account with the same owner; use ERC-7739 rehashing or bind the account address.
- **EIP-7702 delegate risks**: front-run initialization, storage collisions between successive delegates, delegations with `chain_id = 0`, phishing for authorizations to malicious delegates, and `tx.origin == msg.sender` checks that no longer prove an EOA.
- **Module risks**: a malicious or buggy validator can authorize anything; an executor can move funds without a signature; uninstall paths must not brick the account or leave dangling permissions.
- **Session keys**: missing expiry, unbounded value, wildcard targets or selectors, and no revocation path turn a convenience key into a full key.
- **Passkeys**: verify the WebAuthn challenge equals the hash being signed, check user presence and verification flags as required, reject high-`s` signatures where the verifier requires it, and plan recovery for lost devices.
- **Upgrades**: UUPS accounts must protect `upgradeToAndCall` with the account's own authorization; a broken upgrade can lock funds.

## 11. Testing

- Unit-test `validateUserOp` directly: correct signature returns 0, wrong signature returns 1 without reverting, malformed signature reverts, wrong caller reverts.
- Run full `handleOps` flows against a deployed EntryPoint on a fork or local chain, including `initCode` deployment and EIP-7702 authorization paths.
- Test nonce keys: two keys progress independently, a reused nonce fails.
- Test paymasters: valid approval, expired approval, tampered gas fields, insufficient deposit, and `postOp` with reverted execution.
- Test 7702 delegates: calls from the EOA itself, from the EntryPoint, from a third party (must fail), re-delegation to another implementation and storage layout across it.
- Run the operations through a bundler in validation mode (or its tracer) to catch ERC-7562 violations before users do.

## 12. Review Checklist

- [ ] EntryPoint version and address fixed per chain and matched by bundler, paymaster and account.
- [ ] `validateUserOp` is EntryPoint-only, checks the signature over `userOpHash`, returns 1 on mismatch, pays prefund after validation.
- [ ] Execution functions are callable only by the EntryPoint or the account itself (or by authorized modules).
- [ ] Validation follows ERC-7562: no banned opcodes, only allowed storage, no `block.timestamp`; time limits returned in `validationData`.
- [ ] Paymaster signatures bind sender, nonce, callData, all gas fields, chain ID, paymaster address and a non-zero expiry.
- [ ] ERC-1271 implementation resists cross-account replay (ERC-7739 or equivalent).
- [ ] 7702 delegate has no front-runnable initialization and uses namespaced storage; authorizations are chain-specific.
- [ ] Modules and session keys have scopes, expiry, limits and revocation; uninstall tested.
- [ ] Upgrade and recovery paths require the account's authorization and are tested.
- [ ] Factories and paymasters that need it are staked; deposits are monitored.

## 13. Production Notes

- Run or contract at least two bundlers per chain and fail over; verify they support your EntryPoint version and mempool.
- Monitor paymaster deposit, stake and unstake delay, sponsored volume per user, and rejection reasons.
- Rate-limit paymaster approval services per user and per app; log every approval with the operation hash.
- Publish account implementation and module addresses, versions and audits; users and wallets need them to verify 7702 delegates.
- Track EntryPoint releases and ERC-7562 revisions; bundler behavior follows them, and older versions lose bundler support over time.
- Read addresses, limits and precompile availability from the chain and the current docs rather than from memory.

## 14. Examples

EIP-7702 delegate built from OpenZeppelin Contracts 5.6.1: the EOA key signs UserOperations and ERC-1271 messages, batches run through ERC-7821, no storage to initialize (compiles with solc 0.8.38):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Account} from "@openzeppelin/contracts/account/Account.sol";
import {ERC7821} from "@openzeppelin/contracts/account/extensions/draft-ERC7821.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignerEIP7702} from "@openzeppelin/contracts/utils/cryptography/signers/SignerEIP7702.sol";
import {ERC7739} from "@openzeppelin/contracts/utils/cryptography/signers/draft-ERC7739.sol";
import {ERC721Holder} from "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import {ERC1155Holder} from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";

/// @notice Delegate for EIP-7702. The EOA's own key signs UserOperations (validated through
/// the EntryPoint) and ERC-1271 messages (ERC-7739 defensive rehashing). The contract keeps no
/// storage, so there is nothing to initialize and nothing for an observer to front-run.
/// Batches run through ERC-7821 `execute`, callable by the EntryPoint or by the EOA itself.
contract Delegate7702Account is Account, EIP712, ERC7739, SignerEIP7702, ERC7821, ERC721Holder, ERC1155Holder {
    constructor() EIP712("Delegate7702Account", "1") {}

    function _erc7821AuthorizedExecutor(address caller, bytes32 mode, bytes calldata executionData)
        internal
        view
        virtual
        override
        returns (bool)
    {
        return caller == address(entryPoint()) || super._erc7821AuthorizedExecutor(caller, mode, executionData);
    }
}
```

OpenZeppelin 5.6's `Account.entryPoint()` returns EntryPoint v0.9; override it to pin another version. Sending a batched UserOperation from an EOA with viem, including the first-time authorization (type-checks with viem 2.57.13):

```ts
import { concat, createPublicClient, encodeFunctionData, erc20Abi, http, type Address, type Hex } from "viem";
import { createBundlerClient, toSimple7702SmartAccount } from "viem/account-abstraction";
import { privateKeyToAccount } from "viem/accounts";
import { sepolia } from "viem/chains";

// Keys and endpoints come from the environment or a secret manager, never from source.
const owner = privateKeyToAccount(process.env.OWNER_PRIVATE_KEY as Hex);
const client = createPublicClient({ chain: sepolia, transport: http(process.env.RPC_URL) });

// The EOA keeps its address; its code becomes 0xef0100 || implementation.
const account = await toSimple7702SmartAccount({ client, owner, entryPoint: "0.8" });
const bundler = createBundlerClient({ account, client, transport: http(process.env.BUNDLER_URL) });

async function authorizationIfNeeded() {
  const expected = concat(["0xef0100", account.authorization.address]).toLowerCase();
  const code = (await client.getCode({ address: owner.address }))?.toLowerCase();
  if (code === expected) return undefined; // already delegated to the expected implementation
  if (code && !code.startsWith("0xef0100")) throw new Error("address holds contract code");
  // Sign for this chain only (never chainId 0) and for the EOA's current nonce.
  return owner.signAuthorization({
    address: account.authorization.address,
    chainId: sepolia.id,
    nonce: await client.getTransactionCount({ address: owner.address }),
  });
}

export async function batchApproveAndCall(token: Address, spender: Address, amount: bigint, target: Address, data: Hex) {
  const hash = await bundler.sendUserOperation({
    authorization: await authorizationIfNeeded(),
    calls: [
      { to: token, data: encodeFunctionData({ abi: erc20Abi, functionName: "approve", args: [spender, amount] }) },
      { to: target, data },
      { to: token, data: encodeFunctionData({ abi: erc20Abi, functionName: "approve", args: [spender, 0n] }) },
    ],
  });
  const receipt = await bundler.waitForUserOperationReceipt({ hash });
  if (!receipt.success) throw new Error(`UserOperation reverted in tx ${receipt.receipt.transactionHash}`);
  return receipt.receipt.transactionHash;
}
```

`toSimple7702SmartAccount` delegates to eth-infinitism's `Simple7702Account` at the implementation address viem ships for the chosen EntryPoint; confirm that address is deployed on your chain. A verifying paymaster for EntryPoint v0.8 is in [references/erc-4337-entrypoint.md](references/erc-4337-entrypoint.md).

## 15. Common Mistakes

- Reverting on a bad signature instead of returning `SIG_VALIDATION_FAILED`, which breaks gas estimation and wallet UX.
- Reading `block.timestamp`, other accounts' storage or `BALANCE` during validation, so bundlers reject the operation.
- Signing paymaster approvals that omit gas fields, chain ID, the paymaster address or an expiry.
- Packing `accountGasLimits` or `gasFees` in the wrong order (verification gas and priority fee are the high 128 bits).
- Assuming the account is deployed: ERC-1271 checks against undeployed accounts need ERC-6492.
- Using one nonce key for everything, so a stuck admin operation blocks normal use.
- Delegating an EOA to an unaudited contract, or signing a 7702 authorization with `chainId = 0`.
- Treating `tx.origin == msg.sender` as proof that the caller has no code; after EIP-7702 it is not.
- Hard-coding an EntryPoint address without checking that the bundler supports that version on that chain.
- Installing ERC-7579 modules from unknown sources, or session keys without expiry and limits.

## 16. References

- [references/erc-4337-entrypoint.md](references/erc-4337-entrypoint.md): UserOperation fields and packing, `userOpHash`, nonces, `validationData`, prefund and deposits, gas fields, bundler and paymaster RPC, a verifying paymaster.
- [references/erc-7562-validation-rules.md](references/erc-7562-validation-rules.md): opcode, storage, staking, reputation and size rules, and how to stay compliant.
- [references/eip-7702.md](references/eip-7702.md): set-code transactions, authorization tuples, delegation indicator, interaction with ERC-4337, delegate contract security.
- [references/smart-accounts-and-modules.md](references/smart-accounts-and-modules.md): Safe, Kernel, OpenZeppelin, ERC-7579 and ERC-6900, session keys, passkeys and P-256, signatures (ERC-1271, ERC-7739, ERC-6492).
- Specifications: https://eips.ethereum.org/EIPS/eip-4337, https://eips.ethereum.org/EIPS/eip-7562, https://eips.ethereum.org/EIPS/eip-7702, https://eips.ethereum.org/EIPS/eip-7579. Code: https://github.com/eth-infinitism/account-abstraction, https://docs.openzeppelin.com/contracts/5.x/accounts, https://viem.sh/account-abstraction
