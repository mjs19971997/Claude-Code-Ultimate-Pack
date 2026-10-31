# Smart Accounts, Modules, Session Keys and Passkeys

Account implementations (Safe, Kernel, OpenZeppelin, others), the ERC-7579 and ERC-6900 module standards, session keys, passkey signers and P-256 verification, and the signature standards accounts need. The Solidity example compiles with solc 0.8.38 and OpenZeppelin Contracts 5.6.1. Versions are those tagged in each project's repository in 2026-10; check each project's docs for deployments and audit status.

## Implementations

| Implementation | Model | Notes |
|---|---|---|
| Safe (`safe-smart-account` v1.5.0) | Multisig account with modules and guards | ERC-4337 through `Safe4337Module` 0.3.0, audited and deployed for EntryPoint v0.7 (`0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226`, setup helper `SafeModuleSetup` `0x2dd68b007B46fBe91B9A7c3EDa5A7a1063cB5b47`). Passkeys through `safe-modules` WebAuthn signers (passkey v0.2.1) |
| Kernel (ZeroDev) | ERC-7579 modular account | v3.3 targets EntryPoint v0.7; v4.0 (tagged 2026-10) targets v0.9, adds permissions (one signer plus policies), scoped execution hooks and a `Kernel7702` variant. Validator choice is encoded in the nonce key |
| OpenZeppelin Contracts 5.6 | Building blocks | `Account`, signers (`SignerECDSA`, `SignerP256`, `SignerWebAuthn`, `SignerRSA`, `SignerEIP7702`, `SignerERC7913`, `MultiSignerERC7913`, `MultiSignerERC7913Weighted`), `ERC7739`, `ERC7821`, `AccountERC7579`, `AccountERC7579Hooked`, `ERC4337Utils`, `ERC7579Utils`, `EIP7702Utils`. Several files are `draft-` because their ERCs are drafts |
| eth-infinitism | Reference | `SimpleAccount`, `SimpleAccountFactory`, `Simple7702Account`, `BasePaymaster`; minimal and audited with the EntryPoint |
| Alchemy Modular Account v2 | ERC-6900 | Targets ERC-4337 v0.9 and ERC-6900 v0.8 per its README |
| Coinbase Smart Wallet | Multi-owner (address and passkey owners) | viem `toCoinbaseSmartAccount` |

Choosing: Safe for multisig treasuries and organizations; Kernel or another ERC-7579 account for consumer wallets with modules and session keys; OpenZeppelin parts for a custom account with a small audited surface; a 7702 delegate for existing EOAs that should keep their address.

## ERC-7579 (modular accounts)

- Account interface: `execute(bytes32 mode, bytes executionCalldata)`, `executeFromExecutor(bytes32 mode, bytes executionCalldata)`, `installModule(uint256 moduleTypeId, address module, bytes initData)`, `uninstallModule(uint256 moduleTypeId, address module, bytes deInitData)`, `isModuleInstalled(uint256 moduleTypeId, address module, bytes additionalContext)`, `accountId()`, `supportsExecutionMode(bytes32)`, `supportsModule(uint256)`, plus ERC-1271 `isValidSignature`.
- Mode (`bytes32`): call type (1 byte: single, batch, delegatecall), exec type (1 byte: revert or try), 4 unused bytes, 4-byte mode selector, 22-byte payload.
- Module types: 1 validator, 2 executor, 3 fallback handler, 4 hook. Every module implements `onInstall(bytes)`, `onUninstall(bytes)`, `isModuleType(uint256)`.
- Validators implement `validateUserOp(PackedUserOperation, bytes32) returns (uint256)` and `isValidSignatureWithSender(address sender, bytes32 hash, bytes signature) returns (bytes4)`; hooks implement `preCheck` and `postCheck`.
- Module storage must be keyed by the account address so validation stays within ERC-7562 associated storage.
- ERC-7579 is a Draft; module registries and attestations (for example the Rhinestone registry) are a separate trust layer.

ERC-6900 (Draft) is a more prescriptive modular standard (validation, execution and hook functions declared in module manifests); accounts and modules are not interchangeable with ERC-7579 ones.

## Module security

- An installed validator can authorize any operation that routes to it; an executor can call `executeFromExecutor` without a signature. Treat install as granting full or scoped control, and require the root signer.
- Uninstall must succeed even if the module reverts in `onUninstall` (or provide a forced path), and must clear permissions it granted.
- Fallback handlers extend the account's ABI; a handler that forwards with `delegatecall` runs code in the account's storage.
- Hooks run on every execution; a reverting hook bricks execution until removed, so keep a root path that bypasses or removes it.
- Pin module addresses and verify code hashes or registry attestations before install.

## Session keys

A session key is a secondary signer with a narrow scope, typically generated in the browser or app and held there.

Scope it with all of:
- expiry (`validUntil`) and optional start time, returned in `validationData`;
- allowed targets and function selectors;
- value and token spending limits per call and per period;
- optional argument constraints (recipient equals the user, amount below a cap);
- gas or paymaster limits so it cannot burn the deposit;
- a revocation path signed by the root key.

Implementations: Kernel permissions (signer plus policies), Smart Sessions modules for ERC-7579 accounts (Rhinestone; its `@rhinestone/module-sdk` package is deprecated in favor of `@rhinestone/sdk`), Safe modules. ERC-7715 (Draft) defines a wallet RPC for dApps to request permissions. Check the current docs of each project for policy contracts and audits.

Pitfalls: policies checked only off-chain, limits stored where validation cannot read them (ERC-7562), session keys that can install modules or change owners, missing expiry, and keys stored in plain `localStorage`.

## Passkeys and P-256

- Passkeys (WebAuthn credentials) sign with P-256 (secp256r1). The account stores the public key `(qx, qy)` and verifies a WebAuthn assertion: `authenticatorData`, `clientDataJSON` (which contains the challenge), and the signature `(r, s)`.
- The challenge must be the hash being authorized (the `userOpHash` or ERC-1271 hash, possibly wrapped); check the `type` is `webauthn.get` and the user-presence flag, and user-verification if your policy needs it.
- `P256VERIFY` is a precompile at `0x100`: on Ethereum mainnet since Fusaka (EIP-7951, 6,900 gas), and on many rollups through RIP-7212. Where it is absent, a Solidity verifier costs far more gas. OpenZeppelin's `P256.verify` uses the precompile and falls back to Solidity.
- OpenZeppelin's `P256.verify` rejects `s` above `n/2`; normalize `s` to the lower half off-chain before submitting.
- Passkeys can be synced across devices by the platform or bound to one device; plan recovery (a second passkey, a guardian, or a recovery module) before users depend on one credential.
- viem provides `toWebAuthnAccount` for client-side signing with passkeys.

Single-passkey account with a CREATE2 factory, usable as the `factory` of the first UserOperation (compiles with solc 0.8.38 and OpenZeppelin Contracts 5.6.1):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Account} from "@openzeppelin/contracts/account/Account.sol";
import {ERC7821} from "@openzeppelin/contracts/account/extensions/draft-ERC7821.sol";
import {Create2} from "@openzeppelin/contracts/utils/Create2.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignerP256} from "@openzeppelin/contracts/utils/cryptography/signers/SignerP256.sol";
import {SignerWebAuthn} from "@openzeppelin/contracts/utils/cryptography/signers/SignerWebAuthn.sol";
import {ERC7739} from "@openzeppelin/contracts/utils/cryptography/signers/draft-ERC7739.sol";

/// @notice ERC-4337 account controlled by one passkey (P-256 key, WebAuthn assertions).
/// The key is set in the constructor, so there is no initializer to front-run.
contract PasskeyAccount is Account, EIP712, ERC7739, SignerWebAuthn, ERC7821 {
    constructor(bytes32 qx, bytes32 qy) EIP712("PasskeyAccount", "1") SignerP256(qx, qy) {}

    function _erc7821AuthorizedExecutor(address caller, bytes32 mode, bytes calldata executionData)
        internal
        view
        override
        returns (bool)
    {
        return caller == address(entryPoint()) || super._erc7821AuthorizedExecutor(caller, mode, executionData);
    }
}

/// @notice CREATE2 factory used as the UserOperation `factory`. The init code contains the key,
/// so the counterfactual address commits to it and nobody can deploy another key there.
contract PasskeyAccountFactory {
    function createAccount(bytes32 qx, bytes32 qy, bytes32 salt) external returns (address account) {
        account = getAddress(qx, qy, salt);
        if (account.code.length == 0) {
            new PasskeyAccount{salt: salt}(qx, qy);
        }
    }

    function getAddress(bytes32 qx, bytes32 qy, bytes32 salt) public view returns (address) {
        bytes memory initCode = abi.encodePacked(type(PasskeyAccount).creationCode, abi.encode(qx, qy));
        return Create2.computeAddress(salt, keccak256(initCode));
    }
}
```

Full-contract deployment per user costs more gas than a clone; a clone-based factory must initialize the signer in the same call and bind the key into the salt, otherwise the counterfactual address can be taken over. The factory's single `CREATE2` of the sender satisfies ERC-7562 OP-031; stake the factory if initialization touches storage outside the new account.

## Signatures from accounts

- **ERC-1271**: `isValidSignature(bytes32 hash, bytes signature)` returns `0x1626ba7e` when valid. dApps must call it for contract accounts instead of `ecrecover`.
- **ERC-7739** (Draft): wraps the app's EIP-712 hash with the account's own domain so a signature made for account A cannot be replayed on account B with the same owner, while keeping the typed data readable in wallets. OpenZeppelin's `ERC7739` implements it.
- **ERC-6492** (Final): signatures from accounts not yet deployed are wrapped with the factory call and a magic suffix; verifiers simulate deployment, then call ERC-1271. viem's `verifyMessage` and `verifyTypedData` on a public client handle 6492 and 1271.
- **Replay across chains**: signatures over raw hashes without chain ID can be replayed on every chain where the account exists at the same address; include the chain in the signed data.

## Upgrades and recovery

- UUPS accounts (Kernel, many custom accounts) upgrade through the account itself; protect `upgradeToAndCall` with the root validator and test upgrades between versions with stored state.
- Safe upgrades by changing its singleton through a signed transaction; use Safe's migration contracts and supported versions.
- Recovery options: guardian modules with delays, social recovery with thresholds, a backup passkey, or an off-chain recovery service with an on-chain delay. Every recovery path is also an attack path; add a delay and a cancel option controlled by the current owner.
