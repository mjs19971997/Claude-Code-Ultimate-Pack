# Anchor Programs

Account types, constraints, space, PDAs, CPIs, a Token-2022-compatible token vault, resizing and closing, zero-copy, upgrades, and notes for Anchor 1.0 and 2.0. Code passes `cargo check` with `anchor-lang` and `anchor-spl` 1.2.2 (`init-if-needed` feature enabled for the token example, `bytemuck` added for zero-copy).

## Account types

| Type | Checks Anchor performs | Use for |
|---|---|---|
| `Account<'info, T>` | Owner is the program that defines `T`, 8-byte discriminator matches, data deserializes | Program state |
| `Box<Account<'info, T>>` | Same, data on the heap | Large structs that would overflow the 4 KB stack frame |
| `AccountLoader<'info, T>` | Owner and discriminator; data accessed in place with `load`, `load_mut`, `load_init` | Zero-copy accounts up to 10 MiB |
| `InterfaceAccount<'info, T>` | Owner is one of the interface programs (SPL Token or Token-2022), data deserializes | `Mint`, `TokenAccount` from `anchor_spl::token_interface` |
| `Signer<'info>` | `is_signer` | Authorities and payers |
| `SystemAccount<'info>` | Owner is the System Program | Lamport-only PDAs and wallets |
| `Program<'info, T>` | Address equals `T`'s ID and the account is executable | CPI targets (`System`, `Token`, `AssociatedToken`) |
| `Interface<'info, T>` | Address is one of the interface's program IDs | `TokenInterface` (SPL Token or Token-2022) |
| `Sysvar<'info, T>` | Address is the sysvar | Only when a sysvar must be passed; prefer `T::get()` |
| `UncheckedAccount<'info>` | Nothing | Accounts validated by explicit constraints; requires a `/// CHECK:` comment |
| `Option<Account<'info, T>>` | Checks when present | Optional accounts (client passes the program ID for "none") |
| `Migration<'info, From, To>` | Deserializes `From`, writes `To` on exit | Schema migrations (Anchor 1.0 and later) |

`AccountInfo<'info>` in an `Accounts` struct still compiles in 1.x but emits a deprecation warning; switch to `UncheckedAccount`.

## Constraints

| Constraint | Effect |
|---|---|
| `mut` | Account is writable and is serialized back on exit |
| `mut, dup` | Allows the same account to appear twice (rejected by default since 1.0 for `Account`, `LazyAccount`, `InterfaceAccount`, `Migration`) |
| `init, payer = p, space = n` | Creates the account through the System Program, assigns it to the program, writes the discriminator |
| `init_if_needed` | Creates if missing, otherwise validates; needs the `init-if-needed` feature and a re-initialization review |
| `seeds = [...], bump` | Verifies the address is the PDA for these seeds with the canonical bump; `ctx.bumps.<field>` exposes it |
| `seeds = [...], bump = x` | Verifies with a stored bump (cheaper, no search) |
| `seeds::program = id` | PDA of another program |
| `has_one = field` | `account.field == field.key()` |
| `address = expr` | Exact key |
| `owner = expr` | Account owner |
| `constraint = expr @ Err` | Arbitrary boolean check with a custom error |
| `close = target` | On exit, sends lamports to `target`, clears data and reassigns to the System Program |
| `realloc = n, realloc::payer = p, realloc::zero = bool` | Resizes and tops up or refunds rent |
| `token::mint`, `token::authority`, `token::token_program` | Token account fields |
| `mint::authority`, `mint::decimals`, `mint::token_program` | Mint fields |
| `associated_token::mint`, `associated_token::authority`, `associated_token::token_program` | Associated token account derivation |

Instruction arguments used in constraints must be declared with `#[instruction(arg: Type, ...)]` in the same order and types as the handler; Anchor 1.0 enforces the match.

## Space

- Every `#[account]` needs `8` bytes of discriminator plus the data. Use `#[derive(InitSpace)]` and `space = 8 + T::INIT_SPACE`.
- `String` and `Vec` fields need `#[max_len(n)]` (for `Vec<String>`, `#[max_len(items, chars)]`).
- `Option<T>` costs one extra byte; enums cost one byte plus the largest variant.
- Rent-exempt minimum grows linearly with size; read it with `Rent::get()?.minimum_balance(space)`.
- A single instruction can grow an account by at most 10 KiB (`MAX_PERMITTED_DATA_INCREASE`); larger accounts need several reallocs or creation at full size.

## PDAs

```rust
// Derive (client or tests)
let (pda, bump) = Pubkey::find_program_address(&[b"state", owner.as_ref()], &program_id);

// Validate in Accounts (canonical bump, searched once at init)
#[account(init, payer = owner, space = 8 + State::INIT_SPACE, seeds = [b"state", owner.key().as_ref()], bump)]
pub state: Account<'info, State>,

// Later instructions: reuse the stored bump
#[account(mut, seeds = [b"state", owner.key().as_ref()], bump = state.bump, has_one = owner)]
pub state: Account<'info, State>,
```

- Seeds must make the address unique per logical entity: include the owner, the mint, an index, or all three.
- Seeds are bytes: use `key().as_ref()`, `id.to_le_bytes()`, fixed-length tags. Variable-length user strings as seeds can collide across different splits (`"ab"+"c"` and `"a"+"bc"`); prefer fixed-length or hashed seeds.
- A PDA signs a CPI only inside its own program, with `invoke_signed` and the exact seeds plus bump.

## CPIs

```rust
// Plain CPI: the user signs
let cpi = CpiContext::new(
    system_program::ID,
    Transfer { from: ctx.accounts.user.to_account_info(), to: ctx.accounts.vault.to_account_info() },
);
system_program::transfer(cpi, amount)?;

// PDA-signed CPI
let seeds: &[&[u8]] = &[b"vault", owner_key.as_ref(), &[bump]];
let cpi = CpiContext::new(system_program::ID, Transfer { from: vault_info, to: owner_info })
    .with_signer(&[seeds]);
system_program::transfer(cpi, amount)?;
```

- Since 1.0, `CpiContext::new` takes the program ID; keep the `Program` or `Interface` account in the `Accounts` struct so the program is validated and passed to the runtime.
- For programs without an Anchor CPI crate, `declare_program!(name)` generates CPI helpers and types from an IDL in `idls/name.json`.
- After a CPI that may change an account you already deserialized, call `ctx.accounts.x.reload()?` before reading it.
- CPI depth and the number of accounts per instruction are limited; check the current docs for the active limits.

## Token vault (SPL Token and Token-2022)

```rust
use anchor_lang::prelude::*;
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token_interface::{self, Mint, TokenAccount, TokenInterface, TransferChecked};

declare_id!("6J3hLLkJAia6JAE5aQeHiGGbLS6HViBbJ1CxffB4uh25");

pub const AUTH_SEED: &[u8] = b"authority";

#[program]
pub mod tokvault {
    use super::*;

    /// Moves tokens from the user's account into the vault owned by the program PDA.
    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        require!(amount > 0, ErrorCode::ZeroAmount);
        let cpi = CpiContext::new(
            ctx.accounts.token_program.key(),
            TransferChecked {
                from: ctx.accounts.user_ata.to_account_info(),
                mint: ctx.accounts.mint.to_account_info(),
                to: ctx.accounts.vault_ata.to_account_info(),
                authority: ctx.accounts.user.to_account_info(),
            },
        );
        token_interface::transfer_checked(cpi, amount, ctx.accounts.mint.decimals)
    }

    /// Pays tokens out of the vault; the PDA signs with its seeds.
    pub fn release(ctx: Context<Release>, amount: u64) -> Result<()> {
        let bump = ctx.bumps.vault_authority;
        let seeds: &[&[u8]] = &[AUTH_SEED, &[bump]];
        let signer_seeds = &[seeds];
        let cpi = CpiContext::new(
            ctx.accounts.token_program.key(),
            TransferChecked {
                from: ctx.accounts.vault_ata.to_account_info(),
                mint: ctx.accounts.mint.to_account_info(),
                to: ctx.accounts.recipient_ata.to_account_info(),
                authority: ctx.accounts.vault_authority.to_account_info(),
            },
        )
        .with_signer(signer_seeds);
        token_interface::transfer_checked(cpi, amount, ctx.accounts.mint.decimals)
    }
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mint::token_program = token_program)]
    pub mint: InterfaceAccount<'info, Mint>,
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = user,
        associated_token::token_program = token_program
    )]
    pub user_ata: InterfaceAccount<'info, TokenAccount>,
    /// CHECK: PDA used only as the vault's token authority; seeds are verified.
    #[account(seeds = [AUTH_SEED], bump)]
    pub vault_authority: UncheckedAccount<'info>,
    #[account(
        init_if_needed,
        payer = user,
        associated_token::mint = mint,
        associated_token::authority = vault_authority,
        associated_token::token_program = token_program
    )]
    pub vault_ata: InterfaceAccount<'info, TokenAccount>,
    pub token_program: Interface<'info, TokenInterface>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Release<'info> {
    pub admin: Signer<'info>,
    #[account(seeds = [b"config"], bump, has_one = admin)]
    pub config: Account<'info, Config>,
    #[account(mint::token_program = token_program)]
    pub mint: InterfaceAccount<'info, Mint>,
    /// CHECK: PDA used only as the vault's token authority; seeds are verified.
    #[account(seeds = [AUTH_SEED], bump)]
    pub vault_authority: UncheckedAccount<'info>,
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = vault_authority,
        associated_token::token_program = token_program
    )]
    pub vault_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, token::mint = mint, token::token_program = token_program)]
    pub recipient_ata: InterfaceAccount<'info, TokenAccount>,
    pub token_program: Interface<'info, TokenInterface>,
}

#[account]
#[derive(InitSpace)]
pub struct Config {
    pub admin: Pubkey,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Amount must be greater than zero")]
    ZeroAmount,
}
```

Notes:
- `init_if_needed` on an associated token account is safe because the address is deterministic and the constraints re-check mint, authority and token program. The `Config` account is created by a separate admin-only instruction (not shown).
- One vault authority for all mints is a deliberate simplification; per-mint or per-user authorities (`seeds = [AUTH_SEED, mint.key().as_ref()]`) limit the blast radius.
- Token-2022 mints with a transfer fee deliver less than `amount`; mints with a transfer hook need the hook's extra accounts in the CPI. Either support them explicitly or reject mints whose extensions the program does not handle.

## Resizing and closing

- `realloc` adds or removes space and moves rent between the account and `realloc::payer`. A subtractive realloc refunds every lamport above the new rent-exempt minimum, so do not shrink accounts that intentionally hold extra lamports.
- Set `realloc::zero = true` when an account can shrink and grow again in one transaction, so stale bytes do not reappear.
- `close = receiver` is the safe way to close; manual closes must zero the data, move all lamports and reassign the owner. Anchor rejects closing an account into itself.

## Zero-copy

Add `bytemuck = { version = "1.20.0", features = ["min_const_generics"] }` to the program's dependencies, then:

```rust
#[account(zero_copy)]
pub struct OrderBook {
    pub orders: [Order; 1024],
}

#[zero_copy]
pub struct Order {
    pub owner: Pubkey,
    pub price: u64,
    pub size: u64,
}

#[derive(Accounts)]
pub struct InitBook<'info> {
    #[account(zero)]
    pub book: AccountLoader<'info, OrderBook>,
}

// handler: let mut book = ctx.accounts.book.load_init()?;
```

- Types inside a zero-copy account must be `Pod` (fixed size, no `String` or `Vec`); Anchor derives `bytemuck` traits.
- Accounts larger than the 10 KiB per-instruction growth are created by the client with the System Program (full size, owned by the program) and passed with `#[account(zero)]`.

## Upgrades and authority

- Programs deployed with the upgradeable loader have an upgrade authority; anyone holding it can replace the code. Keep it in a multisig, or set it to none to make the program immutable.
- An admin check can bind to the upgrade authority by reading the program data account: `#[account(constraint = program_data.upgrade_authority_address == Some(admin.key()))]` with `program_data: Account<'info, ProgramData>` (check the current docs for the field names in your Anchor version).
- Account layouts are permanent: append fields, never reorder; use `Migration<'info, From, To>` or a versioned struct to change shape.

## Anchor 1.0 and 2.0 notes

- 1.0 renamed the TypeScript package to `@anchor-lang/core`, deprecated `AccountInfo` in `Accounts`, rejected duplicate mutable accounts by default, removed the program `AccountInfo` from `CpiContext`, moved IDL storage to Program Metadata, and defaulted tests to LiteSVM and local networks to Surfpool.
- 1.2.1 added a `solana-v4` feature for Agave 4 crates; the default remains the 3.x crates.
- 1.2.2 creates accounts that already hold lamports with `CreateAccountAllowPrefund` instead of separate Transfer, Allocate and Assign CPIs.
- 2.0 is in release candidates. Its TypeScript client is built on Kit (`Address` instead of `PublicKey`, `bigint` instead of `BN`, `provider.rpc` instead of `provider.connection`) and handlers take `&mut Context<...>`. Test migrations before adopting; check the v2 migration guide in the current docs.
