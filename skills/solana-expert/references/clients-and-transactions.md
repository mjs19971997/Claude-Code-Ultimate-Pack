# Clients and Transactions

Building, sizing, pricing and sending transactions with `@solana/kit`, lookup tables, durable nonces, and migrating from `@solana/web3.js` 1.x. TypeScript type-checks with `@solana/kit` 8.6.0, `@solana-program/system` 0.16.0 and `@solana-program/compute-budget` 0.20.0 (TypeScript 5.9, `strict`).

## Packages

| Package | Role |
|---|---|
| `@solana/kit` | RPC and subscriptions clients, addresses, codecs, signers, transaction messages, send-and-confirm factories |
| `@solana-program/system` | System Program instructions (`getTransferSolInstruction`, `getCreateAccountInstruction`), `SYSTEM_PROGRAM_ADDRESS` |
| `@solana-program/compute-budget` | `estimateComputeUnitLimitFactory`, compute budget instructions |
| `@solana-program/token`, `@solana-program/token-2022` | Token instructions and account decoders |
| `@solana-program/address-lookup-table` | Create, extend, deactivate and close lookup tables |
| `@solana/compat` | `fromLegacyPublicKey`, `fromLegacyKeypair`, `fromLegacyTransactionInstruction`, `fromVersionedTransaction` for gradual migration |
| `@solana/web3.js` 3.x | The 1.x class API rebuilt on Kit, for codebases that keep classes |
| Codama | Generates typed Kit clients from an Anchor or Codama IDL |

Kit packages are released together; keep every `@solana/*` package on the same version.

## Transaction anatomy

- A message holds a fee payer, a lifetime (recent blockhash or durable nonce), and instructions; each instruction lists a program address, account metas (address plus role: readonly, writable, signer, writable signer) and data bytes.
- Legacy and v0 messages must fit a 1,232-byte packet including signatures; v0 can reference accounts through lookup tables to save 31 bytes per account.
- Kit 8 also models v1 messages (`createTransactionMessage({ version: 1 })`), where the priority fee is a total in lamports (`setTransactionMessagePriorityFeeLamports`). Check the current docs for which clusters accept v1 and how it interacts with lookup tables before adopting it.
- Each signature costs a base fee; the priority fee is extra and goes to the leader.

## Compute budget and priority fees

- Without an explicit limit, validators assume 200,000 CU per instruction; the maximum per transaction is 1,400,000.
- For legacy and v0: priority fee = CU price (micro-lamports per CU) times the CU limit. Requesting a tight limit lowers the fee at a given price and makes the transaction easier to schedule.
- Kit helpers: `setTransactionMessageComputeUnitLimit(units, m)` and `setTransactionMessageComputeUnitPrice(microLamports, m)` add, replace or remove the compute budget instructions idempotently.
- Estimate with `estimateComputeUnitLimitFactory({ rpc })` (simulation), then add a margin, because state can change between simulation and execution.
- Pick the price from `getRecentPrioritizationFees` for the transaction's writable accounts; a median or percentile of recent non-zero values is a reasonable start, and some RPC providers offer their own fee estimates.

## Client for the vault program

```ts
import { createHash } from "node:crypto";
import {
  AccountRole,
  address,
  appendTransactionMessageInstructions,
  assertIsSendableTransaction,
  assertIsTransactionWithBlockhashLifetime,
  createSolanaRpc,
  createSolanaRpcSubscriptions,
  createTransactionMessage,
  getAddressEncoder,
  getProgramDerivedAddress,
  getSignatureFromTransaction,
  getU64Encoder,
  pipe,
  sendAndConfirmTransactionFactory,
  setTransactionMessageComputeUnitLimit,
  setTransactionMessageComputeUnitPrice,
  setTransactionMessageFeePayerSigner,
  setTransactionMessageLifetimeUsingBlockhash,
  signTransactionMessageWithSigners,
  type Address,
  type Instruction,
  type TransactionSigner,
} from "@solana/kit";
import { estimateComputeUnitLimitFactory } from "@solana-program/compute-budget";
import { SYSTEM_PROGRAM_ADDRESS } from "@solana-program/system";

const PROGRAM_ID = address("6J3hLLkJAia6JAE5aQeHiGGbLS6HViBbJ1CxffB4uh25");

// Anchor instruction discriminator: first 8 bytes of sha256("global:<name>").
function discriminator(name: string): Uint8Array {
  return createHash("sha256").update(`global:${name}`).digest().subarray(0, 8);
}

async function findPda(seed: string, owner: Address): Promise<Address> {
  const [pda] = await getProgramDerivedAddress({
    programAddress: PROGRAM_ID,
    seeds: [seed, getAddressEncoder().encode(owner)],
  });
  return pda;
}

export async function deposit(
  rpcUrl: string,
  wsUrl: string,
  owner: TransactionSigner,
  amount: bigint,
  microLamportsPerCu: bigint,
): Promise<string> {
  const rpc = createSolanaRpc(rpcUrl);
  const rpcSubscriptions = createSolanaRpcSubscriptions(wsUrl);

  const ix: Instruction = {
    programAddress: PROGRAM_ID,
    accounts: [
      { address: owner.address, role: AccountRole.WRITABLE_SIGNER },
      { address: await findPda("state", owner.address), role: AccountRole.WRITABLE },
      { address: await findPda("vault", owner.address), role: AccountRole.WRITABLE },
      { address: SYSTEM_PROGRAM_ADDRESS, role: AccountRole.READONLY },
    ],
    data: new Uint8Array([...discriminator("deposit"), ...getU64Encoder().encode(amount)]),
  };

  const { value: latestBlockhash } = await rpc.getLatestBlockhash().send();
  const message = pipe(
    createTransactionMessage({ version: 0 }),
    (m) => setTransactionMessageFeePayerSigner(owner, m),
    (m) => setTransactionMessageLifetimeUsingBlockhash(latestBlockhash, m),
    (m) => appendTransactionMessageInstructions([ix], m),
    (m) => setTransactionMessageComputeUnitPrice(microLamportsPerCu, m),
  );

  // Simulate to size the compute unit limit, then add a 10% margin.
  const units = await estimateComputeUnitLimitFactory({ rpc })(message);
  const sized = setTransactionMessageComputeUnitLimit(Math.ceil(units * 1.1), message);

  const signed = await signTransactionMessageWithSigners(sized);
  assertIsSendableTransaction(signed);
  assertIsTransactionWithBlockhashLifetime(signed);
  await sendAndConfirmTransactionFactory({ rpc, rpcSubscriptions })(signed, { commitment: "confirmed" });
  return getSignatureFromTransaction(signed);
}

// Median of recent prioritization fees for the accounts the transaction writes.
export async function suggestPriceMicroLamports(rpcUrl: string, writable: Address[]): Promise<bigint> {
  const fees = await createSolanaRpc(rpcUrl).getRecentPrioritizationFees(writable).send();
  const sorted = fees.map((f) => f.prioritizationFee).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0n;
}
```

Hand-encoding instruction data is fine for a small program; for anything larger, generate a client from the IDL with Codama so account order, roles and argument encoding come from one source.

## Signers and keys

- `generateKeyPairSigner()` for ephemeral keys in tests; `createKeyPairSignerFromBytes(bytes)` to load a 64-byte keypair, for example a CLI keypair file read at runtime.
- Browser apps receive a `TransactionSigner` from the wallet adapter (Wallet Standard); never handle the user's secret key.
- Server keys come from a KMS, HSM or secret manager; never commit keypair JSON or paste secret bytes into source.

```ts
import { readFile } from "node:fs/promises";
import { createKeyPairSignerFromBytes } from "@solana/kit";

// Load a CLI keypair file (JSON array of 64 bytes) from a path given at runtime.
export async function loadSigner(path: string) {
  const bytes = new Uint8Array(JSON.parse(await readFile(path, "utf8")));
  return createKeyPairSignerFromBytes(bytes);
}
```

## Lifetime, confirmation and retries

- A blockhash lifetime expires after a bounded number of blocks; `sendAndConfirmTransactionFactory` throws `SOLANA_ERROR__BLOCK_HEIGHT_EXCEEDED` when it does. Rebuild with a new blockhash and re-sign; do not resend the expired bytes.
- Durable nonces (`setTransactionMessageLifetimeUsingDurableNonce`, `sendAndConfirmDurableNonceTransactionFactory`) remove the expiry for offline or multi-party signing; the nonce advances when the transaction lands.
- Commitments: `processed` (seen by the node), `confirmed` (supermajority vote), `finalized` (rooted). Use `finalized` before irreversible off-chain actions such as releasing goods or bridging.
- Simulate before sending for user-facing flows and show the decoded error; map Anchor custom errors (6000 and up) back to the IDL.

## Address lookup tables

- A table stores up to 256 addresses; create it with `getCreateLookupTableInstruction`, append with `getExtendLookupTableInstruction`, and wait at least one slot after extending before using new entries.
- Only v0 (and later) messages can use tables. Signers and the fee payer cannot be loaded from a table.
- Deactivate, wait for the cool-down, then close to recover rent.

```ts
import {
  compressTransactionMessageUsingAddressLookupTables,
  fetchAddressesForLookupTables,
  type Address,
  type Rpc,
  type SolanaRpcApi,
  type TransactionMessage,
  type TransactionMessageWithFeePayer,
} from "@solana/kit";

// Replace static account keys with lookup-table indexes where the tables contain them.
export async function compressWithTables<M extends TransactionMessage & TransactionMessageWithFeePayer & { version: 0 }>(
  rpc: Rpc<SolanaRpcApi>,
  message: M,
  tables: Address[],
) {
  const addressesByTable = await fetchAddressesForLookupTables(tables, rpc);
  return compressTransactionMessageUsingAddressLookupTables(message, addressesByTable);
}
```

## Migrating from @solana/web3.js 1.x

| web3.js 1.x | Kit |
|---|---|
| `new Connection(url)` | `createSolanaRpc(url)` and `createSolanaRpcSubscriptions(wsUrl)`; calls end with `.send()` |
| `PublicKey` | `Address` (branded string) from `address("...")` |
| `Keypair` | `KeyPairSigner` (`generateKeyPairSigner`, `createKeyPairSignerFromBytes`) |
| `number` or `BN` lamports | `bigint` with `lamports(...)` |
| `Transaction`, `VersionedTransaction` | Immutable transaction messages built with `pipe` and `createTransactionMessage` |
| `SystemProgram.transfer` | `getTransferSolInstruction` from `@solana-program/system` |
| `ComputeBudgetProgram.setComputeUnitPrice` | `setTransactionMessageComputeUnitPrice` |
| `sendAndConfirmTransaction` | `sendAndConfirmTransactionFactory({ rpc, rpcSubscriptions })` |
| `PublicKey.findProgramAddressSync` | `await getProgramDerivedAddress({ programAddress, seeds })` |
| `@coral-xyz/anchor` | `@anchor-lang/core` 1.x (still web3.js 1.x types) or 2.0 (Kit types, release candidate) |

Steps:
1. Inventory where `PublicKey`, `Keypair`, `Connection` and `Transaction` cross module boundaries.
2. Convert at the edges with `@solana/compat` while modules move to Kit.
3. Replace program helpers with `@solana-program/*` packages or Codama clients.
4. If a full rewrite is not possible, move to `@solana/web3.js` 3.x, which keeps the class API on Kit internals; 1.x gets critical fixes only.
