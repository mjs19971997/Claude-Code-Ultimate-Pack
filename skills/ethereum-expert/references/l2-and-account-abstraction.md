# L2 Rollups and Account Abstraction

Reference for how rollups differ from L1 for application developers, and for the two account abstraction paths live on Ethereum: ERC-4337 and EIP-7702. Verified against ERC-4337 (Final), EIP-7702 (Final), EIP-5792 (Final), the L2BEAT stages framework, OpenZeppelin Contracts 5.7.0 changelog, and viem 2.57.13 (a sponsored EIP-7702 transaction was built against a mock RPC and decoded to type `0x04`) (2026-10).

## 1. Rollups in one page

- A rollup executes transactions off L1, posts the transaction data to L1 (calldata, and since EIP-4844 mostly blobs) and posts state commitments. Anyone can reconstruct the L2 state from L1 data, which is what lets users exit even if the operator misbehaves (subject to each chain's design).
- **Optimistic rollups** accept state commitments as valid unless challenged. A fraud-proof system lets a challenger prove an invalid state transition during a challenge window; withdrawals to L1 wait for that window, which is commonly about a week (check the chain's documentation).
- **ZK rollups** post a validity proof with each batch (or group of batches). Once the proof is verified on L1, the state is final without a challenge window; the delay is proof generation and posting time.
- Both rely on a **sequencer** that orders transactions and gives fast pre-confirmations. A sequencer is often a single operator; the designs differ in how users can force inclusion through L1 when the sequencer censors or goes down.
- Blob capacity and price (see [transactions-and-gas.md](transactions-and-gas.md)) drive L2 data costs. Fusaka's BPO forks raised the blob target to 14 and the max to 21 per block (since 2026-01-07).

## 2. Maturity stages (L2BEAT)

The L2BEAT Stages framework measures decentralization, not security:

| Stage | Meaning (summarized from the framework) |
|---|---|
| 0 | Operated with significant trusted components; upgrades by parties outside the security council need at least a 7-day exit window; the external challenger requirement was moved here in the June 2025 update |
| 1 | Governed by smart contracts; a security council can remain as a bug backstop |
| 2 | Permissionless proof system; the security council may act only on errors detected on chain |

Check l2beat.com/stages for the current framework version and each project's classification before relying on a rollup for custody.

## 3. What differs for applications

- **Fees**: an L2 transaction pays L2 execution gas plus a component for posting data to L1. Estimate with the chain's own RPC (`eth_estimateGas` may not include the L1 data fee on some chains; the chain documentation lists the extra call or precompile).
- **Finality levels**: L2 nodes distinguish at least sequencer-confirmed (can be reorged by the sequencer), posted to L1, and finalized after L1 finality or proof. OP Stack nodes call these unsafe, safe and finalized heads. Use the strongest level the use case needs.
- **Opcode and precompile support**: L2s adopt L1 upgrades on their own schedule. Verify `PUSH0`, transient storage, `MCOPY`, `BLOBHASH`, `CLZ` and precompile addresses before deploying (see [evm-and-storage.md](evm-and-storage.md)). `P256VERIFY` at `0x100` exists on L1 since Fusaka and on several L2s; costs differ.
- **Block and time semantics**: `block.number`, `block.timestamp` and block time differ from L1 on many chains; read the chain's documentation before using them for timing logic.
- **Cross-domain messages**: L1-to-L2 calls from contracts may appear to come from an aliased address on some rollups. Withdrawals back to L1 need a prove-and-finalize flow on optimistic rollups.
- **Sequencer outages**: oracle consumers on L2 should check sequencer uptime feeds and enforce a grace period after recovery.
- **Gas token and chain id**: some chains use a non-ETH gas token; always read `eth_chainId` and the chain's registry entry.
- **Reorg behavior**: an L2 can reorg when the sequencer reorders unsafe blocks, and its L1 posting can reorg with L1 (rare once L1 finalizes).

## 4. ERC-4337 (account abstraction without protocol changes)

ERC-4337 has status Final. It moves account validation and fee payment into contracts and a separate mempool.

Flow:

1. A user (or wallet) builds a **UserOperation** and sends it to a **bundler** with `eth_sendUserOperation`; `eth_getUserOperationReceipt` returns the result. The ERC specifies these RPC methods.
2. The bundler simulates validation, keeps the operation in an alternative mempool, and packs several operations into one ordinary transaction calling `EntryPoint.handleOps`.
3. The **EntryPoint** singleton runs a verification loop (account `validateUserOp`, optional factory deployment, optional paymaster validation) and then an execution loop. Fees are charged against a deposit held in the EntryPoint.
4. A **paymaster** can sponsor gas or accept ERC-20 payment. Operations are signed over a hash that includes `chainId` and the EntryPoint address, so they do not replay across chains or EntryPoint versions.

Packed on-chain struct fields: `sender`, `nonce`, `initCode`, `callData`, `accountGasLimits` (verification and call gas limits, 16 bytes each), `preVerificationGas`, `gasFees` (priority and max fee, 16 bytes each), `paymasterAndData`, `signature`. The nonce is a 256-bit value with a key and a sequence, so independent operation streams can run in parallel.

EntryPoint deployments (from viem 2.57.13 constants; the contracts come from the eth-infinitism repository):

| Version | Address |
|---|---|
| 0.6 | `0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789` |
| 0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` |
| 0.8 | `0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108` |
| 0.9 | `0x433709009B8330FDa32311DF1C2AFA402eD8D009` |

Choose the EntryPoint version supported by your bundler, paymaster and account implementation, and verify the address on the target chain before using it. The ERC text includes EIP-7702 support: when the `factory` field is the `0x7702` flag, the sender must be an EOA with an EIP-7702 delegation, and the bundler adds the authorization to the bundle.

Related standards: ERC-1271 (signature validation for contract accounts, Final), ERC-6492 (signature validation for accounts not deployed yet, Final), EIP-5792 (`wallet_sendCalls` and `wallet_getCallsStatus` for batched calls from a dapp, Final). ERC-7579 and ERC-6900 (modular smart accounts) are Draft. OpenZeppelin Contracts 5.7.0 ships account building blocks, including `AccountERC7579` and a `Paymaster` family, and removed the `draft-` prefix from its ERC-4337 files.

Costs and trade-offs: UserOperations add overhead (EntryPoint accounting, bundler fees, `preVerificationGas`) compared with a plain transaction, validation code is restricted by the mempool rules so bundlers can simulate it safely, and a bundler or paymaster service is infrastructure you depend on.

## 5. EIP-7702 (EOA delegation)

EIP-7702 is Final and live on mainnet since Pectra (2025-05-07). Processing rules are in [transactions-and-gas.md](transactions-and-gas.md).

Typical uses: batching an approval and a swap in one transaction, a sponsor paying gas for the user, and session or sub-keys with limited permissions, all at the user's existing address.

Sponsored delegation with viem 2.57.13 (the relayer sends the transaction; the EOA signs only the authorization). Keys come from the environment in real code; the nonce in the authorization is the EOA's current nonce when someone else sends the transaction:

```js
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { sepolia } from 'viem/chains';

const eoa = privateKeyToAccount(process.env.EOA_KEY);          // the account being upgraded
const relayer = privateKeyToAccount(process.env.RELAYER_KEY);  // pays gas
const DELEGATE = process.env.DELEGATE_ADDRESS;                 // audited implementation contract

const client = createWalletClient({ account: relayer, chain: sepolia, transport: http(process.env.RPC_URL) });

const authorization = await eoa.signAuthorization({
  chainId: sepolia.id,      // never 0 unless replay on every chain is intended
  address: DELEGATE,
  nonce: await client.getTransactionCount({ address: eoa.address }),
});

const hash = await client.sendTransaction({
  authorizationList: [authorization],
  to: eoa.address,          // executes the delegate's code in the EOA's context
  data: '0x',               // replace with encoded calldata for the delegate, e.g. an initializer signed by the EOA
});
```

If the EOA sends the transaction itself, the authorization nonce must be the account nonce plus 1, because the sender nonce is incremented before authorizations are processed. To remove a delegation, authorize the zero address.

Hazards:

- The delegate controls the account entirely. A malicious or buggy delegate drains it, so wallets should show the delegate address and allow only reviewed implementations.
- Initialization of the delegate's storage must require a signature from the EOA, or an attacker can initialize it first.
- Storage persists across re-delegation; use ERC-7201 namespaced storage in delegate contracts.
- Delegation remains if the surrounding transaction reverts, and authorizations with `chain_id` 0 are replayable on every supporting chain.
- Contracts that assume callers with code are contracts, or that `tx.origin == msg.sender` excludes smart accounts, behave differently with delegated EOAs.
- The EOA's private key still has ultimate control: it can sign a new authorization at any time, and compromise of the key remains compromise of the account.

## 6. Choosing between them

| Need | Choice |
|---|---|
| Keep an existing address and add batching or sponsorship | EIP-7702 delegating to a reviewed implementation |
| New accounts with recovery, modules, social login, per-chain deployment | ERC-4337 smart account (can be an EIP-7702 delegate via a compatible account contract) |
| Gas sponsorship across many dapps with ERC-20 payment | ERC-4337 paymaster, or a relayer with an EIP-7702 delegate that charges in tokens |
| Passkey (secp256r1) signers | A smart account verifying with `P256VERIFY` at `0x100` where available, or a fallback verifier library |
| Broad wallet compatibility for batched calls | EIP-5792 `wallet_sendCalls`, with feature detection through wallet capabilities |
