---
name: defi-expert
description: >-
  Designs and reviews DeFi protocol logic and integrations: constant-product and concentrated-liquidity AMMs (Uniswap V2, V3, V4 hooks), lending and liquidations (Aave V3 and V4, Compound-style markets), ERC-4626 vaults, flash loans, Chainlink Data Feeds and TWAP oracles, stablecoin and perps risk, and MEV (sandwiches, private order flow). Use when integrating swaps, price feeds or lending markets, writing vaults or rate models, calculating slippage, impermanent loss or health factors, or threat-modelling oracle manipulation and flash-loan attacks. Not for generic Solidity syntax (use solidity-expert), vulnerability audits of contract code (use smart-contract-security-expert), ethers.js client code (use ethersjs-expert), or token-holder governance (use dao-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# DeFi Expert

This skill covers the mechanics and failure modes of on-chain finance: how AMMs price trades, how lending markets set rates and liquidate, how vaults account for shares, how oracles are read safely and how MEV changes what a transaction is worth. It prefers designs whose safety does not depend on a single price source, a single transaction ordering or a trusted caller, and it keeps protocol-specific numbers out unless they are read from the chain or the current docs.

> Verified against Solidity 0.8.38 (npm `solc` latest), OpenZeppelin Contracts 5.6.1, `@chainlink/contracts` 1.5.0, `@aave/core-v3` 1.19.3, `@uniswap/v4-core` 1.0.2 and `@uniswap/v3-periphery` 1.4.4 (2026-10). Solidity examples were compiled with these versions.

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

- Covered: AMM math and LP economics, swap integration with slippage and deadlines, lending rate models and liquidation mechanics, flash loans, ERC-4626 vaults, Chainlink and TWAP oracles, sequencer checks on L2, MEV exposure, stablecoin and derivatives risk models, composability risk.
- Not covered: language features and gas golfing (solidity-expert), line-by-line audits and exploit taxonomy (smart-contract-security-expert), client-side wallet and RPC code (ethersjs-expert), voting and treasury design (dao-expert), NFT markets (nft-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Constant-product AMM | `x * y = k`; Uniswap V2 charges its fee on the input amount; price impact grows with trade size relative to reserves |
| Concentrated liquidity | Uniswap V3 positions are ranges of ticks; liquidity is active only while price is in range; fee tiers are set at pool creation |
| Uniswap v4 | Singleton `PoolManager` holds all pools; flash accounting via `unlock` and deltas; native ETH pools; hooks run custom logic at pool lifecycle points; a hook's permissions are encoded in the low bits of its address and cannot change after deployment |
| Lending | Pooled collateral and debt; interest accrues from a utilization-based rate model; positions with health factor below 1 are liquidatable for a bonus |
| Aave | V3: aTokens, supply and borrow caps, isolation mode, efficiency mode, `flashLoan` and `flashLoanSimple`. V4: hub-and-spoke architecture (liquidity in hubs, risk-segmented spokes); confirm interfaces in the current Aave docs |
| Vaults | ERC-4626 tokenized vaults: `asset`, `totalAssets`, `convertTo*`, `preview*`, `max*`, `deposit/mint/withdraw/redeem`; rounding favors the vault |
| Oracles | Chainlink `latestRoundData()` returns `(roundId, answer, startedAt, updatedAt, answeredInRound)`; `decimals()` per feed; heartbeat and deviation differ per feed; Uniswap TWAP from `observe` |
| MEV | Sandwiches, backruns, liquidation and arbitrage races, JIT liquidity; mitigated by slippage limits, private order flow and batch auctions |
| Stablecoins | Fiat-backed (reserve and issuer risk), crypto-collateralized (liquidation risk), algorithmic (reflexivity risk) |
| Perps and options | Funding rate, mark vs index price, margin and liquidation engines, oracle dependency |

## 3. Workflow

1. Write the invariant first: what must always hold (solvency, share price monotonic except for losses, no free value from a single transaction).
2. List every external price, balance and call the invariant depends on; classify each as trusted, manipulable within one transaction, or manipulable across blocks.
3. Choose the oracle: a decentralized feed for collateral and liquidation decisions; TWAP only with enough liquidity and window; never a pool's spot price.
4. Specify parameters (LTV, liquidation threshold, caps, fees) in a table with the reason and the owner who can change them, and put changes behind a timelock.
5. Implement with checks-effects-interactions, `SafeERC20`, a reentrancy guard on state-changing entry points, and explicit rounding direction.
6. Simulate adversarial sequences: flash-loan price push, donation to a vault, sandwich, oracle staleness, depeg, sequencer outage, liquidation cascade.
7. Add monitoring (oracle age, utilization, bad debt, pause triggers) before launch and test pause and recovery paths.
8. Get an independent review and keep conservative caps at launch; raise them gradually.

## 4. Decision Rules

- Price a collateral asset with a decentralized oracle feed plus staleness and sanity checks; use a TWAP as a cross-check or fallback, never a spot reserve ratio.
- Swap integrations take `minOut` and `deadline` from the caller. `minOut == 0` is a bug, not a default.
- Use partial liquidations with a bounded close factor; full liquidation only where the protocol design explicitly requires it.
- Pull over push for payouts to multiple recipients.
- Round against the user and in favor of the protocol on every conversion: shares down on deposit, shares up on withdraw, debt up, collateral down.
- Any contract that holds user funds and has an admin uses a timelock for parameter and upgrade changes, and exits stay available during a pause.
- ERC-4626 vaults: use OpenZeppelin's implementation with a non-zero `_decimalsOffset()`; do not use `balanceOf(address(this))` for share pricing in a custom vault.
- For flash-loan receivers verify `msg.sender` is the lender and `initiator` is the contract itself.
- Prefer audited protocol primitives (Uniswap, Aave, Chainlink) behind a thin adapter over custom copies.

## 5. Coding Standards

- Solidity `^0.8.24` with OpenZeppelin Contracts 5.x import paths (`@openzeppelin/contracts/...`); `Ownable(initialOwner)` takes the owner explicitly.
- Fixed-point: choose WAD (1e18), RAY (1e27) or basis points per module and state it in the comments; multiply before dividing; use `Math.mulDiv` for 512-bit intermediate safety.
- Custom errors instead of revert strings; events for every parameter change and every user-facing balance movement.
- `SafeERC20` (`safeTransfer`, `safeTransferFrom`, `forceApprove`) for every token call; never assume `transfer` returns `true` or that amounts received equal amounts sent.
- Immutable addresses for routers, pools and feeds where upgrades are not needed; no hard-coded mainnet addresses in library code.
- Omit author tags from NatSpec; document rounding direction and units on every public function.

## 6. Project Structure

```text
contracts/
  core/            Vault.sol, Market.sol, RateModel.sol
  oracle/          PriceOracle.sol (feed adapter, staleness, sequencer)
  adapters/        SwapExecutor.sol, FlashReceiver.sol
  libraries/       AmmMath.sol, LendingMath.sol
  interfaces/
test/
  unit/            math and rounding
  fork/            integration against live pools, feeds and lenders
  invariant/       solvency, share price, supply conservation
  attack/          flash loan, donation, sandwich, stale oracle
```

## 7. Design Patterns

- **Oracle adapter**: one contract per feed pair that normalizes decimals, enforces max age and positivity, and checks the L2 sequencer; the rest of the system sees only `price()`.
- **Guarded swap**: transfer in, approve exact, swap with `minOut` and `deadline`, reset allowance, send out to the user.
- **Virtual shares**: ERC-4626 with a decimals offset so the first depositor cannot inflate the share price by donation.
- **Pull-based accounting**: users claim rewards and refunds; the protocol never loops over user lists.
- **Circuit breakers**: pause deposits and borrows (never withdrawals or repayments), caps on supply, borrow and per-block flows.
- **Adapter plus allowlist** for external calls from vaults and strategies, so a compromised dependency cannot receive arbitrary calls.
- **Keeper-friendly liquidation**: public `liquidate(user, debtToCover)` with a bonus that covers gas and risk but is bounded.

## 8. Best Practices

- Keep every external value (price, balance, rate) in a local variable read once per transaction.
- Compute minimum outputs from an independent source and a slippage budget in basis points, not from the same pool being traded against.
- Cap exposure to any single oracle, collateral and market; start with conservative caps.
- Document trust assumptions: who can pause, who can change parameters, which oracles can fail, what happens on failure.
- Treat tokens as untrusted: fee-on-transfer, rebasing, pausable, blocklisted (some stablecoins), ERC-777-style hooks, non-standard `decimals`, missing return values.
- Prefer exact approvals and revoke after use; avoid standing allowances to routers.
- For v4 hooks, restrict hook callbacks to the `PoolManager`, mine the hook address to match its declared permissions, and review hook-controlled fee and delta logic as user-fund-critical code.

## 9. Performance

- Cache storage reads; pack small values; keep loops bounded by protocol-controlled sizes.
- Batch oracle reads and use one price per asset per transaction.
- Prefer Uniswap v4 flash accounting or Aave `flashLoanSimple` over multiple transfers when composing atomic strategies.
- `ReentrancyGuardTransient` (OpenZeppelin 5.x) uses transient storage and needs an EVM with EIP-1153 (Cancun) on the target chain; otherwise use `ReentrancyGuard`.
- Off-chain: quote with the protocol's quoter or simulation, then verify on-chain with `minOut`.

## 10. Security

- **Oracle manipulation**: do not read prices from pool reserves or `slot0`. Reject non-positive, stale or incomplete oracle answers; check the sequencer feed on L2 with a grace period after recovery.
- **Flash loans**: assume any caller has unlimited temporary capital; no logic may depend on a balance, price or voting weight that one transaction can move.
- **Reentrancy**: checks-effects-interactions plus a guard; include read-only reentrancy (views consumed by other protocols mid-call) and callback tokens.
- **Share inflation**: ERC-4626 donation attacks; use the decimals offset, seed liquidity or minimum deposits.
- **Sandwich and MEV**: mandatory `minOut` and `deadline`; route sensitive user trades through private order flow where available; avoid on-chain commitments that reveal profitable orderings.
- **Approvals**: exact approvals; never leave unlimited allowances on helper contracts.
- **Admin risk**: timelocks and multisigs on upgrades and parameters; emergency actions limited to pausing.
- **Composability**: every integrated protocol is a dependency whose failure can propagate (depeg, oracle outage, paused market); define fallbacks and caps.
- **Unsafe tokens**: whitelist collateral and reserve assets; test with fee-on-transfer and rebasing mocks and reject them where unsupported.

## 11. Testing

- Fuzz math libraries for rounding, overflow and monotonicity (`getAmountOut` never exceeds the invariant, health factor decreases as price falls).
- Invariant tests: total assets covers total share claims, supply conservation, no profit from deposit-then-withdraw in the same block.
- Fork tests against real pools, feeds and lenders at pinned blocks.
- Attack tests: flash-loan oracle push, vault donation, stale feed, sequencer down, token with fee on transfer, reentrant token callback.
- Property: a user can always exit (withdraw or repay) when the protocol is paused.

## 12. Review Checklist

- [ ] Every price is from a decentralized feed or a sufficiently long TWAP; staleness, positivity and decimals handled.
- [ ] Swaps enforce `minOut` and `deadline`; allowances reset after use.
- [ ] CEI order, guard on external-call paths, `SafeERC20` everywhere.
- [ ] Rounding direction documented and tested for every conversion.
- [ ] ERC-4626 offset or equivalent inflation mitigation present.
- [ ] Flash-loan callbacks verify caller and initiator.
- [ ] Liquidation path tested for partial and bad-debt cases.
- [ ] Parameter changes behind a timelock; pause cannot block exits.
- [ ] Unsupported token types rejected or tested.
- [ ] Monitoring and incident response in place before launch.

## 13. Production Notes

- Launch with low caps and an allowlist; raise caps as oracle, liquidation and keeper behavior is observed.
- Monitor oracle updatedAt age, deviation vs a secondary source, utilization, health-factor distribution, bad debt and pause state.
- Rehearse emergency pause, oracle failover and parameter rollback.
- Verify contracts on the block explorer and publish addresses, parameters and the audit scope.
- Read live values (fees, caps, premiums, heartbeats) from contracts or current official docs rather than hard-coding them in code or documentation.

## 14. Examples

Oracle adapter: staleness, positivity, decimals and L2 sequencer checks (compiles with solc 0.8.38 and `@chainlink/contracts` 1.5.0):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// @notice Reads one Chainlink Data Feed and rejects stale, incomplete or non-positive answers.
contract PriceOracle {
    AggregatorV3Interface public immutable feed;
    AggregatorV3Interface public immutable sequencerFeed; // address(0) on L1
    uint256 public immutable maxAge; // heartbeat of the feed plus a small buffer, in seconds
    uint256 public constant SEQUENCER_GRACE_PERIOD = 1 hours;

    error StalePrice(uint256 updatedAt);
    error InvalidPrice(int256 answer);
    error SequencerDown();
    error GracePeriodNotOver();

    constructor(AggregatorV3Interface feed_, AggregatorV3Interface sequencerFeed_, uint256 maxAge_) {
        feed = feed_;
        sequencerFeed = sequencerFeed_;
        maxAge = maxAge_;
    }

    /// @notice Price scaled to 18 decimals.
    function price() public view returns (uint256) {
        if (address(sequencerFeed) != address(0)) {
            (, int256 status, uint256 startedAt,,) = sequencerFeed.latestRoundData();
            if (status != 0) revert SequencerDown(); // 0 = up, 1 = down
            if (block.timestamp - startedAt <= SEQUENCER_GRACE_PERIOD) revert GracePeriodNotOver();
        }

        (, int256 answer,, uint256 updatedAt,) = feed.latestRoundData();
        if (answer <= 0) revert InvalidPrice(answer);
        if (updatedAt == 0 || block.timestamp - updatedAt > maxAge) revert StalePrice(updatedAt);

        uint8 d = feed.decimals();
        uint256 p = uint256(answer);
        return d <= 18 ? p * 10 ** (18 - d) : p / 10 ** (d - 18);
    }
}
```

ERC-4626 vault: OpenZeppelin 5.x, decimals offset against inflation attacks, deposit cap, pause that never blocks exits (compiles with OpenZeppelin Contracts 5.6.1):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @notice ERC-4626 vault with a deposit cap, a pause switch and a virtual-share offset
/// against the first-depositor inflation attack. The asset must be a plain ERC-20
/// (no fee-on-transfer, no rebasing, no hooks that call back into the vault).
contract CappedVault is ERC4626, Ownable, Pausable, ReentrancyGuard {
    uint256 public depositCap;

    event DepositCapUpdated(uint256 newCap);

    constructor(IERC20 asset_, address initialOwner, uint256 cap_)
        ERC20("Capped Vault Share", "cvSHARE")
        ERC4626(asset_)
        Ownable(initialOwner)
    {
        depositCap = cap_;
    }

    function setDepositCap(uint256 newCap) external onlyOwner {
        depositCap = newCap;
        emit DepositCapUpdated(newCap);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /// @dev Shares have `offset` more decimals than the asset; the virtual shares and assets
    /// in the conversion make donation-based share-price inflation uneconomical.
    function _decimalsOffset() internal pure override returns (uint8) {
        return 6;
    }

    function maxDeposit(address) public view override returns (uint256) {
        if (paused()) return 0;
        uint256 total = totalAssets();
        return total >= depositCap ? 0 : depositCap - total;
    }

    function maxMint(address receiver) public view override returns (uint256) {
        return _convertToShares(maxDeposit(receiver), Math.Rounding.Floor);
    }

    // Withdrawals stay open while paused so users can always exit.
    function _deposit(address caller, address receiver, uint256 assets, uint256 shares)
        internal
        override
        nonReentrant
    {
        super._deposit(caller, receiver, assets, shares);
    }

    function _withdraw(address caller, address receiver, address owner_, uint256 assets, uint256 shares)
        internal
        override
        nonReentrant
    {
        super._withdraw(caller, receiver, owner_, assets, shares);
    }
}
```

A guarded swap contract (mandatory `minOut`, deadline, `SafeERC20`, reset allowance) is in [references/amm-math.md](references/amm-math.md); a flash-loan receiver and rate model are in [references/lending-liquidations.md](references/lending-liquidations.md).

## 15. Common Mistakes

- Pricing collateral or LP tokens from pool reserves or `slot0`, which one flash-loaned swap can move.
- Using `latestRoundData()` without checking `answer > 0`, `updatedAt` age and, on L2, the sequencer.
- Treating `amountOutMinimum = 0` or `deadline = block.timestamp` (set inside the call) as acceptable defaults.
- Letting an ERC-4626 vault start empty without virtual shares, a decimals offset or seeded liquidity.
- Assuming 18 decimals, or that `transfer` moves exactly `amount` (fee-on-transfer, rebasing tokens).
- Valuing LP tokens from spot reserve balances. Use fair-reserve pricing, `2 * sqrt(k * p0 * p1) / totalSupply` with oracle prices `p0`, `p1`, so a reserve skew cannot inflate the value.
- Distributing rewards with unbounded loops or push payments that one reverting recipient can block.
- Liquidation incentives that are too small to cover gas in a crash, or so large that they invite self-liquidation games.
- Using unlimited approvals on routers and leaving them set.
- Forgetting that hooks, callbacks and flash-loan receivers are entry points that need caller checks.
- Copying fee, TVL, cap or premium numbers into code or docs from memory instead of reading them from the protocol.

## 16. References

- [references/amm-math.md](references/amm-math.md): constant-product and concentrated-liquidity math, impermanent loss, Uniswap V3 and V4 notes, a guarded swap contract.
- [references/lending-liquidations.md](references/lending-liquidations.md): rate models, health factor and liquidation math, Aave V3 and V4 notes, flash-loan receiver, ERC-4626 details.
- [references/oracles-mev.md](references/oracles-mev.md): Chainlink Data Feeds, sequencer checks, TWAP, oracle attack patterns, MEV and mitigation.
- Official docs: Uniswap https://docs.uniswap.org/, Aave https://aave.com/docs, Chainlink Data Feeds https://docs.chain.link/data-feeds, OpenZeppelin ERC-4626 https://docs.openzeppelin.com/contracts/5.x/erc4626, EIP-4626 https://eips.ethereum.org/EIPS/eip-4626
