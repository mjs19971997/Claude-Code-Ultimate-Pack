# Solana Program Security

Sealevel attack classes with insecure and fixed Anchor code, and a review procedure. The snippets come from one scratch program that passes `cargo check` with anchor-lang 1.2.2; insecure versions are marked and must not be deployed. The Anchor repository keeps longer examples of each class in its Sealevel attacks reference.

## Threat model

- The caller chooses every account in the transaction, every instruction argument, and the order of instructions in the transaction.
- Any program can be invoked by any other program through CPI, and any account can be passed in any slot.
- A program is safe only if, for every account it touches, it proves: who owns it, what type it is, which entity it belongs to, and whether the required party signed.

## Missing signer check

```rust
// INSECURE: admin is compared but never required to sign.
#[derive(Accounts)]
pub struct SetFeeInsecure<'info> {
    #[account(mut)]
    pub config: Account<'info, Config>,
    /// CHECK: insecure example, missing Signer.
    pub admin: UncheckedAccount<'info>,
}
// handler: require_keys_eq!(ctx.accounts.config.admin, ctx.accounts.admin.key(), ...)
```

Anyone can pass the admin's public key without its signature. Fix: make it a `Signer` and bind it with `has_one`.

```rust
#[derive(Accounts)]
pub struct SetFee<'info> {
    #[account(mut, seeds = [b"config"], bump = config.bump, has_one = admin @ SecError::Unauthorized)]
    pub config: Account<'info, Config>,
    pub admin: Signer<'info>,
}
```

## Missing owner and type check

```rust
// INSECURE: no owner or discriminator check; anyone can craft these bytes.
#[derive(Accounts)]
pub struct ReadPriceInsecure<'info> {
    /// CHECK: insecure example, no owner check.
    pub oracle: UncheckedAccount<'info>,
}
// handler: u64::from_le_bytes(data[8..16].try_into().unwrap())
```

An attacker creates an account they own with the same byte layout and any price. Fix: `Account<'info, Oracle>` checks the owner is this program and the discriminator is `Oracle`'s; pin the expected address when there is exactly one.

```rust
#[derive(Accounts)]
pub struct ReadPrice<'info> {
    #[account(address = config_oracle::ID)]
    pub oracle: Account<'info, Oracle>,
}
```

For accounts owned by another program (an oracle, a token account), check `owner = that_program::ID` and deserialize with that program's types, or use the `InterfaceAccount` and `Program` wrappers.

## Account type confusion

- Anchor's 8-byte discriminator (`sha256("account:<Name>")[..8]`) distinguishes `#[account]` types. Custom discriminators must be unique and must not be all zeros (Anchor 1.2 rejects all-zero account discriminators).
- Generic `#[account]` structs share one discriminator across instantiations (`State<u64>` and `State<u128>`); use distinct structs.
- Raw `borsh` structs without a discriminator are confusable; add a type tag or move to `#[account]`.

## PDA seeds and bumps

- Seeds must bind the PDA to its owner or entity. `seeds = [b"position"]` gives every user the same position; use `seeds = [b"position", owner.key().as_ref()]`.
- Store the canonical bump at init and constrain with `bump = account.bump`; never accept a bump argument, since `create_program_address` with another bump can produce a different valid address.
- Variable-length seeds can collide (`["ab", "c"]` versus `["a", "bc"]`); use fixed-length seeds or a length-prefixed or hashed value.
- When a PDA signs a CPI, make sure the signer seeds belong to the account that should authorize, not to a shared authority that controls every user's funds unless that is intended.

## Arithmetic

```rust
pub fn accrue(ctx: Context<Accrue>, amount: u64, rate_bps: u64) -> Result<()> {
    let pos = &mut ctx.accounts.position;
    let interest = amount
        .checked_mul(rate_bps)
        .and_then(|v| v.checked_div(10_000))
        .ok_or(SecError::Overflow)?;
    pos.debt = pos.debt.checked_add(interest).ok_or(SecError::Overflow)?;
    Ok(())
}
```

- Release builds wrap on overflow unless `overflow-checks = true`; keep it on and still use checked operations so the error is explicit.
- Avoid `as` casts between integer widths; use `u64::try_from(x)?`.
- Multiply before dividing, and round in the protocol's favor (debt up, payouts down). Use `u128` intermediates for products of two `u64` values.
- Avoid floating point in programs; results can differ from client calculations.

## Duplicate mutable accounts

```rust
#[derive(Accounts)]
pub struct SwapBalances<'info> {
    pub owner: Signer<'info>,
    #[account(mut, has_one = owner)]
    pub from: Account<'info, Balance>,
    #[account(mut, constraint = to.key() != from.key() @ SecError::SameAccount)]
    pub to: Account<'info, Balance>,
}
```

Anchor 1.x already rejects the same `Account` in two mutable slots unless one is marked `dup`; the explicit constraint documents the intent and also covers `UncheckedAccount` slots, which Anchor does not check.

## Arbitrary CPI

- A CPI target taken from `UncheckedAccount` lets the caller substitute a program that pretends to transfer. Use `Program<'info, Token>`, `Interface<'info, TokenInterface>` or `address = known::ID`.
- Before a CPI that passes a signer or a PDA signature, check every account forwarded: the callee receives the signer privilege for the duration of the call.
- After a CPI, reload any account the callee could modify.

## Initialization, closing and revival

- `init` fails if the account exists, which prevents re-initialization. `init_if_needed` does not; when used on program state, check a stored `initialized` flag or a non-default field before overwriting.
- Close with `close = receiver`. A manual close that only drains lamports leaves data readable and the account revivable within the same transaction if someone refunds it.
- Do not reuse a closed account's address for a different type without a new discriminator check.

## Token-specific checks

- Verify the mint of every token account (`token::mint = mint`) and the token program (`token::token_program = token_program`).
- Verify the authority of every source account; for vaults, the authority is a PDA and only the program can sign.
- Use `transfer_checked`; it also verifies decimals.
- Token-2022: transfer fees (received amount differs), transfer hooks (extra accounts, reentrancy into your program), permanent delegate (tokens can be moved out of your vault by the delegate), non-transferable and pausable mints, confidential transfers. Decide per extension: support, or reject the mint at init.

## Other classes

- **Sysvar spoofing**: read sysvars with `Clock::get()?` and `Rent::get()?`; if an account must be passed, use `Sysvar<'info, T>`, which checks the address.
- **Instruction introspection**: when a program checks other instructions in the transaction (for example an ed25519 signature verification), load the Instructions sysvar through its checked address and verify program ID, index and data exactly.
- **Front-running and ordering**: anyone can place instructions before or after yours in the same transaction; do not rely on a balance or price being unchanged across instructions.
- **Upgrade authority**: a single-key upgrade authority is a full compromise path; put it in a multisig and document the policy.
- **Unbounded loops over `remaining_accounts`**: validate each account and cap the count; compute exhaustion is an availability bug.

## Review procedure

1. List every instruction and its `Accounts` struct. For each account, write down: owner, type, entity binding (seeds or `has_one`), signer requirement, writability.
2. Mark every `UncheckedAccount` and `remaining_accounts` use and confirm the `/// CHECK:` describes a real check.
3. Trace value flows: lamports and tokens in, lamports and tokens out, and who authorizes each.
4. Check arithmetic and rounding on every value computation.
5. Check every CPI: target typed, accounts forwarded validated, signer seeds correct, accounts reloaded after.
6. Check init, realloc and close paths for reinitialization, rent and revival.
7. Confirm negative tests exist for each finding class (see [testing.md](testing.md)).
8. Confirm upgrade authority, admin keys and emergency controls are documented.
