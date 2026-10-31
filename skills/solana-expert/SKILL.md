---
name: solana-expert
description: >-
  Builds, tests and reviews Solana programs in Rust with Anchor 1.x (accounts, PDAs, CPIs, constraints, Token-2022 via token_interface) and TypeScript clients with @solana/kit: the account model, rent, compute budget, priority fees, versioned transactions and address lookup tables, testing with LiteSVM or Mollusk, and Sealevel security (missing signer and owner checks, account confusion, arithmetic, PDA seeds). Use when editing Anchor.toml, programs/*/src/*.rs with #[program] or #[derive(Accounts)], declare_id!, seeds and bump constraints, CpiContext, @solana/kit transaction messages, LiteSVM tests, or when migrating from @coral-xyz/anchor or @solana/web3.js 1.x. Not for EVM contracts (use solidity-expert), EVM security audits (use smart-contract-security-expert), DeFi protocol economics (use defi-expert) or general Rust outside on-chain programs (use rust-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Solana Expert

This skill covers on-chain programs for Solana written in Rust with Anchor, the TypeScript clients that call them, and the tests that prove they are safe. It explains the account model that every design decision follows from (programs are stateless, state lives in accounts passed by the caller, and the program must check every account it is given), then the transaction mechanics a client controls: compute units, priority fees, blockhash lifetime, versioned messages and lookup tables. Examples target the current stable lines: Anchor 1.x and `@solana/kit` 8.x; Anchor 2.0 is a release candidate and is noted where it changes things.

> Verified against Anchor 1.2.2 (`anchor-lang`, `anchor-spl`, `@anchor-lang/core`), `@solana/kit` 8.6.0, `@solana-program/system` 0.16.0, `@solana-program/compute-budget` 0.20.0, LiteSVM 0.18.1 (crate) and 1.6.1 (npm), `mollusk-svm` 0.16.4, Agave 4.4.0 crates, and `@solana/web3.js` 1.99.0 and 3.1.1 (2026-10). Rust examples pass `cargo check` against anchor-lang 1.2.2; TypeScript examples type-check against Kit 8.6.0 and litesvm 1.6.1.

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

- Covered: the account model, rent, PDAs and bumps, CPIs with and without PDA signers, Anchor account types and constraints, SPL Token and Token-2022 through `token_interface`, events, errors, account resizing and closing, upgrades and program authority, compute budget and priority fees, legacy, v0 and v1 transaction messages, address lookup tables, `@solana/kit` clients, LiteSVM and Mollusk tests, Sealevel attack classes, migration from `@coral-xyz/anchor` and `@solana/web3.js` 1.x.
- Not covered: Solidity and EVM contracts (solidity-expert), EVM audits (smart-contract-security-expert), protocol economics such as AMM curves, lending and oracle design (defi-expert), Rust language questions unrelated to on-chain constraints (rust-expert), Ethereum JavaScript libraries (ethersjs-expert, web3js-expert), and dApp UI frameworks beyond the transaction layer (senior-react-19-engineer, nextjs-15-architect).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Account model | Every account has an address, lamports, data, an owner program and an executable flag. Only the owner program may change data or debit lamports; anyone may credit lamports |
| Programs | Stateless executables; all state is in accounts listed by the transaction. A program must validate every account it reads or writes |
| Rent | Accounts must hold at least the rent-exempt minimum for their size, or exactly 0 lamports. Read it with `Rent::get()?.minimum_balance(len)` or the `getMinimumBalanceForRentExemption` RPC; do not hard-code it |
| PDAs | Addresses derived from seeds and a program ID that are off the ed25519 curve, so no private key exists. Up to 16 seeds, each at most 32 bytes. `find_program_address` returns the canonical bump |
| CPIs | A program calls another with `invoke` or, for PDA signing, `invoke_signed`; Anchor wraps both in `CpiContext::new(program_id, accounts)` plus `.with_signer(seeds)` |
| Anchor | `#[program]` handlers, `#[derive(Accounts)]` validation structs, `#[account]` data with an 8-byte discriminator, `InitSpace` for sizing, `#[error_code]`, `#[event]` and `emit!` |
| Compute | Default 200,000 compute units per instruction if no limit is set; 1,400,000 per transaction maximum. Priority fee for legacy and v0 is CU price (micro-lamports) times CU limit |
| Transactions | Legacy and v0 messages share a 1,232-byte packet limit; v0 adds address lookup tables. Kit 8 also models a v1 message whose priority fee is a lamport total; check the current docs for cluster support |
| Tokens | SPL Token and Token-2022 are separate programs with compatible core instructions. Use `InterfaceAccount<Mint>`, `InterfaceAccount<TokenAccount>`, `Interface<TokenInterface>` and `transfer_checked` to support both |
| Clients | `@solana/kit` (functional, tree-shakable, `bigint`, `Address`) is the maintained SDK. `@solana/web3.js` 3.x keeps the class API on top of Kit; 1.x receives critical fixes only |

Anchor 1.0 (April 2026) changes that matter when reading older code:
- The TypeScript package is `@anchor-lang/core`; `@coral-xyz/anchor` stops at 0.32.x.
- `AccountInfo` fields in `#[derive(Accounts)]` emit a deprecation warning; use `UncheckedAccount` with a `/// CHECK:` comment.
- Duplicate mutable accounts of serializing types are rejected unless the field has `#[account(mut, dup)]`.
- `CpiContext::new` takes the callee program ID (`Pubkey`), not its `AccountInfo`.
- `anchor init` creates a multi-file program with LiteSVM Rust tests; `anchor test` and `anchor localnet` start Surfpool instead of `solana-test-validator` when a local network is needed.
- IDLs are stored through Program Metadata; the Anchor CLI no longer shells out to the `solana` CLI.

## 3. Workflow

1. Install the toolchain with `avm install 1.2.2 && avm use 1.2.2` (Rust 1.89 or newer for `anchor-lang`); `anchor init <name>` and commit `Anchor.toml`, `Cargo.lock` and the program keypair path policy.
2. Model state first: list every account type, its owner program, its seeds, who pays for it, who may mutate it, and when it is closed. Write the size of each with `#[derive(InitSpace)]`.
3. For each instruction, write the `Accounts` struct before the handler. Every account gets an explicit type and constraint; any `UncheckedAccount` gets a `/// CHECK:` comment that names the check performed.
4. Implement handlers with checked arithmetic and `require!`; keep CPIs at the end of the handler where possible and reload accounts a CPI may have changed.
5. Run `anchor build`, then the LiteSVM tests (`cargo test` for Rust tests, or the TS runner configured in `Anchor.toml`). Add a negative test for every constraint.
6. Generate or write the client: Codama-generated Kit clients from the IDL, or hand-built instructions for small programs. Set compute unit limit from simulation and a priority fee from recent fees.
7. Deploy to devnet with `anchor deploy --provider.cluster devnet`, run the client end to end, then plan mainnet: upgrade authority on a multisig, verifiable build, `security.json` metadata.
8. After deploy, confirm the on-chain program hash matches the verifiable build and monitor failed transactions by error code.

## 4. Decision Rules

- Use `Account<'info, T>` for program-owned data, `Signer` for authorities, `Program<'info, X>` for program accounts, `SystemAccount` for lamport-only PDAs, `InterfaceAccount` for token accounts and mints. Use `UncheckedAccount` only with a documented check.
- Store the canonical bump in the account at creation and pass `bump = state.bump` later; never accept a bump from instruction data.
- Bind PDAs to their owner with seeds (`[b"vault", owner.key().as_ref()]`) and `has_one = owner`, so one user cannot pass another user's account.
- Choose `init` over `init_if_needed` unless the instruction is idempotent by design; `init_if_needed` needs the feature flag and a re-initialization review.
- Use `transfer_checked` (mint and decimals verified) for tokens, and `token_interface` types unless the program must reject Token-2022 mints.
- Zero-copy (`AccountLoader`, `#[account(zero_copy)]`) only for accounts too large to deserialize within the compute or heap budget.
- Set an explicit compute unit limit on every client transaction, sized from simulation plus a margin; set the CU price from `getRecentPrioritizationFees` for the writable accounts.
- Use v0 messages and lookup tables when a transaction exceeds the account limit or packet size; legacy messages otherwise remain fine.
- New TypeScript code uses `@solana/kit`; existing 1.x code migrates to Kit or to `@solana/web3.js` 3.x, which keeps the class API.

## 5. Coding Standards

- Rust 2021 edition, `anchor-lang` and `anchor-spl` on the same exact version, `overflow-checks = true` in the release profile (the Anchor template sets it).
- One module per instruction under `instructions/`, state structs under `state/`, seeds and limits under `constants.rs`, one `#[error_code]` enum per program.
- Use `checked_add`, `checked_sub`, `checked_mul` with a mapped error; no `as` casts that truncate; no `unwrap` in handlers.
- Name seeds with constants (`pub const VAULT_SEED: &[u8] = b"vault";`) and reuse the same constant in the client.
- Every `/// CHECK:` explains the invariant enforced elsewhere; reviewers treat a missing explanation as a defect.
- Emit an event for each state change a client or indexer must observe; keep event payloads small.
- TypeScript: `bigint` for lamports and token amounts, `Address` from `address()` for keys, no floating-point money.

## 6. Project Structure

```text
Anchor.toml                  cluster, wallet path, program IDs, test script, hooks
Cargo.toml                   workspace; [profile.release] overflow-checks = true
programs/vault/
  Cargo.toml                 anchor-lang, anchor-spl (same version), features
  src/
    lib.rs                   declare_id!, #[program] module dispatching to handlers
    constants.rs             seeds, limits
    error.rs                 #[error_code]
    state/                   #[account] structs with InitSpace
    instructions/            one file per instruction: Accounts struct + handler
  tests/                     LiteSVM Rust tests (include_bytes! of target/deploy/*.so)
clients/js/                  generated or hand-written Kit client
target/idl/vault.json        IDL produced by anchor build
target/deploy/vault.so       program binary
```

## 7. Design Patterns

- **State PDA per user**: `seeds = [STATE_SEED, owner.key().as_ref()]`, bump stored in the account, `has_one = owner` on every mutation.
- **Lamport vault**: a separate system-owned PDA with no data holds SOL; the program moves lamports out with a System Program transfer signed by the PDA seeds.
- **Token vault**: an associated token account whose authority is a program PDA; deposits use the user as authority, releases sign with the PDA seeds.
- **Config singleton**: `seeds = [b"config"]`, created once by the upgrade authority or a stored admin, holding admin keys and parameters.
- **Two-step authority transfer**: store `pending_admin`, require the new admin to sign `accept_admin`.
- **Close to reclaim rent**: `#[account(mut, close = receiver)]` zeroes the discriminator, transfers lamports and assigns the account back to the System Program.
- **Event CPI** (`#[event_cpi]`, `emit_cpi!`) when logs may be truncated and indexers need reliable events.

## 8. Best Practices

- Read the clock with `Clock::get()?`, rent with `Rent::get()?`; do not pass sysvars as accounts unless an instruction requires it.
- Validate every account that influences control flow or value: owner, signer, type (discriminator), relationship (`has_one`, seeds), and mint for token accounts.
- Prefer one writable account per user over a global writable account: global writable state serializes all transactions that touch it and raises fees.
- Keep handlers short and push validation into constraints, where it is visible and tested.
- For upgradeable programs, put the upgrade authority on a multisig and plan when to make the program immutable.
- Log sparingly; logs cost compute and are truncated at a byte limit.
- Pin the client dependency versions (Kit packages move together) and regenerate clients after every IDL change.

## 9. Performance

- Size compute unit limits from simulation: `estimateComputeUnitLimitFactory({ rpc })` from `@solana-program/compute-budget`, then `setTransactionMessageComputeUnitLimit` with a 10 to 20 percent margin. A lower limit lowers the priority fee paid at a given price.
- Use `Box<Account<...>>` for large account structs to move them off the 4 KB stack frame; use zero-copy for very large accounts.
- Avoid re-deriving PDAs on-chain with `find_program_address` in loops; pass the stored bump and use `create_program_address` semantics through `bump = state.bump`.
- Writable account contention, not CU count, is usually the bottleneck; split hot state by user or by shard.
- Use lookup tables for transactions that reference many fixed accounts (markets, oracles, programs).
- `msg!` with formatting is expensive; log fixed strings or emit events.

## 10. Security

- **Missing signer check**: an authority that is `UncheckedAccount` or `AccountInfo` lets anyone act as it. Use `Signer<'info>` and bind it with `has_one` or seeds.
- **Missing owner check**: deserializing data from an account the program does not own lets an attacker forge state. `Account<T>` checks owner and discriminator; raw accounts need `owner = ...`.
- **Account confusion**: two account types with the same layout can be swapped. Anchor discriminators prevent this for `#[account]` types; do not use all-zero or shared discriminators, and note that generic `#[account]` instantiations share one discriminator.
- **PDA seed and bump issues**: seeds that omit the user allow cross-user access; non-canonical bumps from input allow alternate addresses. Store the canonical bump.
- **Arbitrary CPI**: a CPI target taken from an unchecked account lets the caller substitute a malicious program. Use `Program<'info, X>` or `Interface<'info, TokenInterface>`.
- **Arithmetic**: overflow wraps in release builds unless `overflow-checks = true`; use checked operations anyway and round in the protocol's favor.
- **Duplicate mutable accounts**: passing the same account twice can double-count; Anchor 1.x rejects it by default, so review every `dup`.
- **Reinitialization and revival**: `init_if_needed` and manual init must not reset an existing account; closed accounts must not be reusable within the same transaction.
- **Stale data after CPI**: call `.reload()` on accounts a CPI may have modified before reading them again.
- **Token-2022 extensions**: transfer fees, hooks, permanent delegates and confidential transfers change transfer semantics; restrict accepted mints or handle each extension.

## 11. Testing

- LiteSVM is the default for `anchor init` and runs the compiled `.so` in-process; it is fast enough to test every constraint and failure path. `solana-bankrun` is deprecated in favor of LiteSVM.
- Mollusk tests a single instruction against explicit account inputs and reports compute units; use it for unit-level and CU-regression tests.
- Surfpool (the `anchor test` default) runs a local network and can fork mainnet accounts for integration tests.
- For every instruction, test: success, wrong signer, wrong owner, wrong PDA (another user's seeds), overflow inputs, duplicate accounts, and closed-account reuse.
- Assert on the custom error code, not only on failure.
- Record compute units per instruction in CI and fail when they rise past a threshold.

Details and runnable test layouts are in [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Every account in every `Accounts` struct has a type and constraints that pin owner, signer, seeds or relationship.
- [ ] Each `UncheckedAccount` has a `/// CHECK:` that names the check and the check exists.
- [ ] Canonical bumps are stored and reused; no bump is read from instruction data.
- [ ] Seeds include the user or entity they belong to; seed constants are shared with clients.
- [ ] All arithmetic is checked; `overflow-checks = true` in release.
- [ ] CPI targets are typed (`Program`, `Interface`); PDA signer seeds match the derivation.
- [ ] Token transfers use `transfer_checked` and verify the mint; Token-2022 extensions are handled or rejected.
- [ ] Accounts modified by CPI are reloaded before reuse; closes use `close = ...`.
- [ ] Clients set a compute unit limit and price and handle blockhash expiry.
- [ ] Negative tests exist for every constraint; CU budget tracked.
- [ ] Upgrade authority, verifiable build and `security.json` planned before mainnet.

## 13. Production Notes

- Deploy from a verifiable build (`anchor build --verifiable`) and publish the build hash; since Anchor 1.1 the TypeScript `verifiedBuild` helper reads the OtterSec registry (`verify.osec.io`).
- Hold the upgrade authority in a multisig (for example Squads); document who can upgrade and how fast.
- Use `anchor deploy --security-metadata` to publish `security.json` with a contact; Anchor warns on mainnet deploys without it.
- Send transactions through an RPC provider that supports priority fees and, where needed, staked connections; retry with a fresh blockhash after `BLOCK_HEIGHT_EXCEEDED`.
- Monitor program logs for custom error codes, CU usage and failed-transaction rates; alert on spikes.
- Read current fee markets, rent, feature activation and cluster versions from the RPC or the current docs rather than hard-coding them.

## 14. Examples

Lamport vault: per-user state PDA, system-owned vault PDA, checked arithmetic, PDA-signed CPI (passes `cargo check` with anchor-lang 1.2.2):

```rust
use anchor_lang::prelude::*;
use anchor_lang::system_program::{self, Transfer};

declare_id!("6J3hLLkJAia6JAE5aQeHiGGbLS6HViBbJ1CxffB4uh25");

pub const STATE_SEED: &[u8] = b"state";
pub const VAULT_SEED: &[u8] = b"vault";

#[program]
pub mod vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.owner = ctx.accounts.owner.key();
        state.total = 0;
        state.state_bump = ctx.bumps.state;
        state.vault_bump = ctx.bumps.vault;
        Ok(())
    }

    /// The first deposit must be at least the rent-exempt minimum for a 0-byte account.
    pub fn deposit(ctx: Context<Move>, amount: u64) -> Result<()> {
        require!(amount > 0, VaultError::ZeroAmount);
        let cpi = CpiContext::new(
            system_program::ID,
            Transfer {
                from: ctx.accounts.owner.to_account_info(),
                to: ctx.accounts.vault.to_account_info(),
            },
        );
        system_program::transfer(cpi, amount)?;

        let state = &mut ctx.accounts.state;
        state.total = state.total.checked_add(amount).ok_or(VaultError::Overflow)?;
        emit!(Deposited { owner: state.owner, amount });
        Ok(())
    }

    /// A withdrawal must leave the vault at 0 lamports or at least rent-exempt.
    pub fn withdraw(ctx: Context<Move>, amount: u64) -> Result<()> {
        require!(amount > 0, VaultError::ZeroAmount);
        let owner_key = ctx.accounts.owner.key();
        let seeds: &[&[u8]] = &[VAULT_SEED, owner_key.as_ref(), &[ctx.accounts.state.vault_bump]];
        let signer_seeds = &[seeds];
        let cpi = CpiContext::new(
            system_program::ID,
            Transfer {
                from: ctx.accounts.vault.to_account_info(),
                to: ctx.accounts.owner.to_account_info(),
            },
        )
        .with_signer(signer_seeds);
        system_program::transfer(cpi, amount)?;

        let state = &mut ctx.accounts.state;
        state.total = state.total.checked_sub(amount).ok_or(VaultError::Insufficient)?;
        Ok(())
    }
}

#[account]
#[derive(InitSpace)]
pub struct VaultState {
    pub owner: Pubkey,
    pub total: u64,
    pub state_bump: u8,
    pub vault_bump: u8,
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(
        init,
        payer = owner,
        space = 8 + VaultState::INIT_SPACE,
        seeds = [STATE_SEED, owner.key().as_ref()],
        bump
    )]
    pub state: Account<'info, VaultState>,
    /// System-owned PDA with no data; it only holds lamports.
    #[account(seeds = [VAULT_SEED, owner.key().as_ref()], bump)]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Move<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(
        mut,
        seeds = [STATE_SEED, owner.key().as_ref()],
        bump = state.state_bump,
        has_one = owner @ VaultError::Unauthorized
    )]
    pub state: Account<'info, VaultState>,
    #[account(mut, seeds = [VAULT_SEED, owner.key().as_ref()], bump = state.vault_bump)]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[event]
pub struct Deposited {
    pub owner: Pubkey,
    pub amount: u64,
}

#[error_code]
pub enum VaultError {
    #[msg("Amount must be greater than zero")]
    ZeroAmount,
    #[msg("Arithmetic overflow")]
    Overflow,
    #[msg("Withdrawal exceeds the recorded balance")]
    Insufficient,
    #[msg("Signer is not the vault owner")]
    Unauthorized,
}
```

The program ID above is a placeholder; `anchor keys sync` writes the real one. A `@solana/kit` client for `deposit` with compute budget and priority fee is in [references/clients-and-transactions.md](references/clients-and-transactions.md); LiteSVM tests for this program are in [references/testing.md](references/testing.md); a Token-2022-compatible token vault is in [references/anchor-programs.md](references/anchor-programs.md).

## 15. Common Mistakes

- Using `AccountInfo` or `UncheckedAccount` for an authority, then comparing keys without checking `is_signer`.
- Seeds such as `[b"vault"]` shared by all users when the vault belongs to one user.
- Accepting a bump in instruction data, or recomputing a PDA with a bump other than the canonical one.
- Moving lamports out of a program-owned data account with a System Program transfer (it fails: the System Program can only debit accounts it owns). Debit the lamports directly in the owner program or use a system-owned PDA.
- Leaving an account below the rent-exempt minimum but above zero, which makes the transaction fail.
- Using `transfer` instead of `transfer_checked`, or `Program<Token>` where Token-2022 mints must be supported.
- Reading an account after a CPI without `.reload()`.
- Copying `@coral-xyz/anchor`, `PublicKey` and `BN` code into a Kit project, or mixing web3.js 1.x and Kit types in one transaction.
- Sending without a compute unit limit, or with a CU price set but the default 200,000-per-instruction limit, which overpays.
- Treating a confirmed signature as finalized for irreversible off-chain actions.

## 16. References

- [references/anchor-programs.md](references/anchor-programs.md): account types and constraints, space, PDAs, CPIs, Token-2022 token vault, realloc and close, zero-copy, upgrades, Anchor 1.0 and 2.0 migration notes.
- [references/clients-and-transactions.md](references/clients-and-transactions.md): `@solana/kit` client, compute budget, priority fees, blockhash and durable nonces, v0 and v1 messages, lookup tables, web3.js 1.x migration.
- [references/testing.md](references/testing.md): LiteSVM in Rust and TypeScript, Mollusk, Surfpool, negative and CU tests, Bankrun deprecation.
- [references/security.md](references/security.md): Sealevel attack classes with insecure and fixed Anchor code, review procedure.
- Official docs: Solana https://solana.com/docs, Anchor https://www.anchor-lang.com/docs, Anchor source https://github.com/otter-sec/anchor, Kit https://github.com/anza-xyz/kit, LiteSVM https://github.com/LiteSVM/litesvm, Mollusk https://github.com/anza-xyz/mollusk
