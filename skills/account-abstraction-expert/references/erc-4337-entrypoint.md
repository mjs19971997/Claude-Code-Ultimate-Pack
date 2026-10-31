# ERC-4337 and the EntryPoint

UserOperation fields and packing, `userOpHash`, nonces, validation data, deposits and stakes, gas fields, the bundler and paymaster JSON-RPC methods, and a verifying paymaster with its signing service. Contract code compiles with solc 0.8.38 against `@account-abstraction/contracts` 0.8.0 and OpenZeppelin Contracts 5.6.1; TypeScript type-checks against viem 2.57.13.

## UserOperation fields

| Field | Type | Meaning |
|---|---|---|
| `sender` | `address` | The account |
| `nonce` | `uint256` | 192-bit key and 64-bit sequence |
| `factory`, `factoryData` | `address`, `bytes` | Deploy the account on first use; `factory = 0x7702` marks an EIP-7702 account and `factoryData` is its optional init call |
| `callData` | `bytes` | Passed to the account in the execution phase |
| `callGasLimit` | `uint256` | Gas for the execution call |
| `verificationGasLimit` | `uint256` | Gas for account (and factory) validation |
| `preVerificationGas` | `uint256` | Gas paid to the bundler for calldata and overhead the EntryPoint cannot meter |
| `maxFeePerGas`, `maxPriorityFeePerGas` | `uint256` | EIP-1559 style fee caps |
| `paymaster` | `address` | Sponsor, or empty |
| `paymasterVerificationGasLimit`, `paymasterPostOpGasLimit` | `uint256` | Gas for the paymaster's validation and `postOp` |
| `paymasterData` | `bytes` | Paymaster-specific data |
| `signature` | `bytes` | Checked by the account; not part of the hash |

The RPC and SDKs use these unpacked fields. On-chain (v0.7 and later) the EntryPoint receives `PackedUserOperation`:

| Packed field | Content |
|---|---|
| `initCode` | `factory` (20 bytes) followed by `factoryData`, or empty |
| `accountGasLimits` | `bytes32`: `verificationGasLimit` (high 16 bytes) then `callGasLimit` (low 16 bytes) |
| `gasFees` | `bytes32`: `maxPriorityFeePerGas` (high 16 bytes) then `maxFeePerGas` (low 16 bytes) |
| `paymasterAndData` | `paymaster` (20) then `paymasterVerificationGasLimit` (16) then `paymasterPostOpGasLimit` (16) then `paymasterData` |

In v0.9, `paymasterAndData` may also end with `paymasterSignature`, its 2-byte length and the magic `0x22e325a297439656`; that suffix is excluded from `userOpHash`, so the user and the paymaster can sign in parallel. Use `UserOperationLib` (eth-infinitism) or `ERC4337Utils` (OpenZeppelin) to read these fields instead of slicing by hand, and viem's `toPackedUserOperation` off-chain.

v0.6 used an unpacked on-chain struct (`initCode`, `callGasLimit`, `verificationGasLimit`, `preVerificationGas`, `maxFeePerGas`, `maxPriorityFeePerGas`, `paymasterAndData` without separate paymaster gas limits); it is not ABI-compatible with v0.7 and later.

## userOpHash

- It covers every field except `signature`, plus the EntryPoint address and chain ID, so a signature cannot be replayed on another chain or EntryPoint.
- From v0.8 it is an EIP-712 typed-data hash with domain name `ERC4337`, version `1`, the chain ID and the EntryPoint as verifying contract, over `PackedUserOperation(address sender,uint256 nonce,bytes initCode,bytes callData,bytes32 accountGasLimits,uint256 preVerificationGas,bytes32 gasFees,bytes paymasterAndData)`. Wallets can display it as typed data.
- For EIP-7702 accounts the first 20 bytes of `initCode` are replaced by the account's current delegate address when hashing, so the signature commits to the delegate.
- Get it from `entryPoint.getUserOpHash(packed)` or viem's `getUserOperationHash`; do not reimplement it unless you test against both.

## Nonces

- `nonce = (key << 64) | sequence`. The EntryPoint tracks a sequence per `(sender, key)` and requires exact increments: `getNonce(sender, key)` returns the next valid nonce.
- Key 0 behaves like an EOA nonce. Other keys give parallel queues, used by modular accounts to select a validator (Kernel encodes the validator in the key) or to separate admin and session-key operations.
- An operation with a used nonce is invalid and dropped by bundlers.

## validationData

`validateUserOp` and `validatePaymasterUserOp` return a `uint256`:

| Bits | Field |
|---|---|
| 0 to 159 | `aggregator`: 0 = valid signature, 1 = `SIG_VALIDATION_FAILED`, otherwise an aggregator address |
| 160 to 207 | `validUntil` (6 bytes); 0 means no expiry |
| 208 to 255 | `validAfter` (6 bytes) |

- Signature mismatch: return 1 and complete the function normally so estimation still measures gas. Revert only for malformed input or wrong caller.
- Time ranges replace `block.timestamp` checks, which ERC-7562 bans. From v0.9, setting the high bit of both values makes them block numbers; one timestamp and one block number cannot be mixed.
- When account and paymaster both return ranges, the EntryPoint uses the intersection.

## Deposits, prefund and stakes

- The EntryPoint holds a deposit per account and per paymaster (`balanceOf`, `depositTo`, `withdrawTo`). Before execution it reserves the maximum cost from limits times `maxFeePerGas`.
- An account without a paymaster pays `missingAccountFunds` to the EntryPoint (its caller) inside `validateUserOp`; do it after the signature check.
- After execution the unused prefund is refunded. v0.7 charges 10 percent of unused execution gas as a penalty; v0.8 and later apply the 10 percent only when the unused amount is at least 40,000 gas, to `callGasLimit` and `paymasterPostOpGasLimit`.
- Stakes (`addStake(unstakeDelaySec)`, `unlockStake`, `withdrawStake`) are separate from deposits and are locked; ERC-7562 uses them to grant storage access and reputation.

## Gas fields in practice

- Ask the bundler: `eth_estimateUserOperationGas` returns `preVerificationGas`, `verificationGasLimit`, `callGasLimit` and the paymaster limits. Add margins; validation limits need at least the ERC-7562 `VALIDATION_GAS_SLACK`.
- `preVerificationGas` must cover calldata cost and the per-operation overhead; on L2s it also covers the L1 data fee, which changes with L1 prices. Bundlers quote it; do not compute it statically.
- Each EIP-7702 authorization costs 25,000 gas that the EntryPoint cannot see; it must be included in `preVerificationGas`.
- Fees: use the bundler's or chain's fee suggestions (some bundlers expose their own fee method; check its docs).

## Bundler and paymaster RPC

| Method | Purpose |
|---|---|
| `eth_sendUserOperation(op, entryPoint)` | Submit; returns `userOpHash`. With EIP-7702, an `eip7702Auth` field carries the authorization tuple |
| `eth_estimateUserOperationGas(op, entryPoint)` | Gas limits for a draft operation with a dummy signature |
| `eth_getUserOperationByHash(hash)` | The operation and where it was included |
| `eth_getUserOperationReceipt(hash)` | Success flag, actual gas cost, logs, transaction receipt |
| `eth_supportedEntryPoints()` | EntryPoint addresses the bundler accepts |
| `eth_chainId()` | Chain ID |
| `pm_getPaymasterStubData` (ERC-7677) | Paymaster fields with a dummy signature, for estimation |
| `pm_getPaymasterData` (ERC-7677) | Final paymaster fields after gas is known |

The methods are specified in ERC-7769 (Draft) and ERC-7677 (Review); bundler vendors add their own extensions.

## Verifying paymaster

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {BasePaymaster} from "@account-abstraction/contracts/core/BasePaymaster.sol";
import {_packValidationData} from "@account-abstraction/contracts/core/Helpers.sol";
import {IEntryPoint} from "@account-abstraction/contracts/interfaces/IEntryPoint.sol";
import {PackedUserOperation} from "@account-abstraction/contracts/interfaces/PackedUserOperation.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/// @notice Sponsors UserOperations approved off-chain by `verifyingSigner` (EntryPoint v0.8).
/// paymasterAndData = paymaster (20) | verificationGas (16) | postOpGas (16)
///                    | abi.encode(uint48 validUntil, uint48 validAfter) (64) | signature (65)
/// No storage reads beyond immutables and no TIMESTAMP opcode: the validity window is returned
/// in validationData and enforced by the EntryPoint, as ERC-7562 requires.
contract SponsorPaymaster is BasePaymaster {
    uint256 private constant TIME_OFFSET = PAYMASTER_DATA_OFFSET;
    uint256 private constant SIG_OFFSET = TIME_OFFSET + 64;

    address public immutable verifyingSigner;

    error InvalidPaymasterDataLength(uint256 length);
    error MissingExpiry();

    constructor(IEntryPoint entryPoint_, address verifyingSigner_) BasePaymaster(entryPoint_) {
        verifyingSigner = verifyingSigner_;
    }

    /// @notice Hash the off-chain signer approves. Binds every gas field, the chain and this paymaster.
    function getHash(PackedUserOperation calldata userOp, uint48 validUntil, uint48 validAfter)
        public
        view
        returns (bytes32)
    {
        return keccak256(
            abi.encode(
                userOp.sender,
                userOp.nonce,
                keccak256(userOp.initCode),
                keccak256(userOp.callData),
                userOp.accountGasLimits,
                bytes32(userOp.paymasterAndData[PAYMASTER_VALIDATION_GAS_OFFSET:PAYMASTER_DATA_OFFSET]),
                userOp.preVerificationGas,
                userOp.gasFees,
                block.chainid,
                address(this),
                validUntil,
                validAfter
            )
        );
    }

    function _validatePaymasterUserOp(PackedUserOperation calldata userOp, bytes32, uint256)
        internal
        view
        override
        returns (bytes memory context, uint256 validationData)
    {
        bytes calldata data = userOp.paymasterAndData;
        if (data.length != SIG_OFFSET + 65) revert InvalidPaymasterDataLength(data.length);
        (uint48 validUntil, uint48 validAfter) = abi.decode(data[TIME_OFFSET:SIG_OFFSET], (uint48, uint48));
        if (validUntil == 0) revert MissingExpiry(); // 0 would mean "valid forever"

        bytes32 digest = MessageHashUtils.toEthSignedMessageHash(getHash(userOp, validUntil, validAfter));
        (address recovered, ECDSA.RecoverError err,) = ECDSA.tryRecoverCalldata(digest, data[SIG_OFFSET:]);
        bool sigFailed = err != ECDSA.RecoverError.NoError || recovered != verifyingSigner;

        // Empty context: no postOp call, which unstaked paymasters cannot use anyway (EREP-050).
        return ("", _packValidationData(sigFailed, validUntil, validAfter));
    }
}
```

Notes:
- `BasePaymaster` 0.8.0 sets `msg.sender` as owner (v0.9 takes an explicit owner); the owner funds the deposit (`deposit()`), withdraws it, and manages the stake.
- The signer must rate-limit and authorize per user or app; anyone holding an approval can spend up to the gas limits it covers until `validUntil`.
- Under v0.8 the user signs `userOpHash`, which includes `paymasterAndData`, so the paymaster must sign first. Under v0.9 the `paymasterSignature` suffix removes that ordering; the contract would read its signature with the v0.9 library helpers instead of a fixed offset.

Sponsor service that produces `paymasterData` for this contract. The operation must already carry its final gas limits, including `paymasterVerificationGasLimit` and `paymasterPostOpGasLimit`:

```ts
import { concat, encodeAbiParameters, pad, parseAbi, type Address, type Hex, type PublicClient } from "viem";
import { toPackedUserOperation, type UserOperation } from "viem/account-abstraction";
import { privateKeyToAccount } from "viem/accounts";

const paymasterAbi = parseAbi([
  "struct PackedUserOperation { address sender; uint256 nonce; bytes initCode; bytes callData; bytes32 accountGasLimits; uint256 preVerificationGas; bytes32 gasFees; bytes paymasterAndData; bytes signature; }",
  "function getHash(PackedUserOperation userOp, uint48 validUntil, uint48 validAfter) view returns (bytes32)",
]);

// The approval key lives in the sponsor service's secret store, never in the client.
const approver = privateKeyToAccount(process.env.PAYMASTER_SIGNER_KEY as Hex);

/** Returns paymasterData for SponsorPaymaster: abi.encode(validUntil, validAfter) || signature. */
export async function sponsor(
  client: PublicClient,
  paymaster: Address,
  userOp: UserOperation<"0.8">,
  ttlSeconds = 300,
): Promise<Hex> {
  const now = Math.floor(Date.now() / 1000);
  const validUntil = now + ttlSeconds;
  const validAfter = now - 30; // tolerate small clock skew
  const window = encodeAbiParameters([{ type: "uint48" }, { type: "uint48" }], [validUntil, validAfter]);

  // getHash reads the paymaster gas limits from paymasterAndData, so pack them with a dummy signature.
  const packed = toPackedUserOperation({ ...userOp, paymaster, paymasterData: concat([window, pad("0x", { size: 65 })]) });
  const hash = await client.readContract({
    address: paymaster,
    abi: paymasterAbi,
    functionName: "getHash",
    args: [packed, validUntil, validAfter],
  });
  const signature = await approver.signMessage({ message: { raw: hash } });
  return concat([window, signature]);
}
```

In production, expose this behind the ERC-7677 methods so wallets and SDKs can use it as a standard paymaster service.

## Accounts: minimum contract surface

- `validateUserOp(PackedUserOperation calldata, bytes32 userOpHash, uint256 missingAccountFunds) returns (uint256)`, callable only by the trusted EntryPoint.
- An execution function (`execute`, `executeBatch`, ERC-7579 `execute(bytes32 mode, bytes)`, ERC-7821 `execute`) callable by the EntryPoint or the account itself.
- Optionally `IAccountExecute.executeUserOp(userOp, userOpHash)`, which the EntryPoint calls when `callData` starts with its selector, giving execution access to the full operation.
- ERC-1271 `isValidSignature` for off-chain signatures, and `receive()` for ETH.
- Use an audited base (OpenZeppelin `Account`, eth-infinitism `BaseAccount`, Safe, Kernel) rather than writing these from scratch.
