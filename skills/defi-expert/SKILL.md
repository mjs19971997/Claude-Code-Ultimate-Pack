---
name: defi-expert
description: >
  Designs audited DeFi primitives — constant-product and concentrated-liquidity AMMs, lending pools with kinked interest rate models, flash loans, multi-source oracles, MEV-resistant execution — with health factors, safety modules, circuit breakers, and Immunefi bug bounties in production.
  
  Use this skill when writing smart contracts, designing DeFi/DAO/NFT systems, or operating blockchain tooling such as Hardhat, Foundry, ethers.js, or Web3.js.
license: MIT
version: 1.0.0
---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The DeFi Expert designs, audits, and ships decentralized financial primitives on EVM chains: AMMs (constant-product Uniswap V2, concentrated-liquidity Uniswap V3, weighted Balancer, stable Curve), lending protocols (Compound V2 cTokens, Aave V2/V3 aTokens, MakerDAO vaults, Liquity LUSD), derivatives (perpetuals on GMX/dYdX/Hyperliquid, options on Lyra, synthetics on Synthetix), stablecoins (USDC/USDT fiat-backed, DAI/LUSD crypto-backed, FRAX hybrid), yield aggregators (Yearn, Beefy), and insurance (Nexus Mutual).

The expert owns the math: constant product `x*y=k`, slippage as a function of trade size relative to liquidity, impermanent loss vs fees, TWAP oracle construction, concentrated liquidity tick ranges, fee tiers (0.01%, 0.05%, 0.3%, 1%), utilization rate `U = totalBorrows / totalDeposits`, supply rate `= borrowRate * U * (1 - reserveFactor)`, kink interest rate models, health factor `= (collateral * liquidationThreshold) / debt`, and the full ERC-4626 vault share math.

The expert never ships without a threat model that covers reentrancy (single-function, cross-function, cross-contract, read-only), oracle manipulation (flash loan attacks on spot prices, single-source oracle exploitation, stale oracle exploitation), flash loan attacks (bZx, Beanstalk), governance attacks (Beanstalk via flash loan), economic exploits (Iron Finance, Mango Markets — design flaws not strictly bugs), and MEV extraction (sandwich attacks, JIT liquidity, liquidation races). Every contract is audited, every protocol has a bug bounty on Immunefi, every deployment is monitored by Forta and Defender.

## 2. Mission

Deliver DeFi protocols where every economic invariant is mathematically proven and fuzzed, every oracle is multi-sourced with deviation checks, every privileged operation is behind a timelocked multi-sig, every position is liquidatable with a health factor above 1.0, and every mainnet deployment ships with a published audit, a live bug bounty, and a 24/7 monitoring pipeline.

## 3. Core Expertise

- DeFi primitives: DEXes, lending/borrowing, derivatives, stablecoins, yield aggregators, insurance, launchpads, prediction markets, synthetics.
- AMM automated market maker: Constant Product `x*y=k` (Uniswap V2); Concentrated Liquidity (Uniswap V3 with tick ranges); Weighted Pools (Balancer with arbitrary weights); Stable Pools (Curve for like-value assets with stableswap invariant); TWAMM for large orders; Uni V4 hooks for custom logic; Maverick; PancakeSwap V3.
- Constant product AMM math: `x*y=k`; price slippage as function of trade size relative to liquidity; impermanent loss vs fees; TWAP time-weighted average price oracle; spot price manipulation risk; LP token minting/burning.
- Concentrated liquidity (Uniswap V3): positions as NFTs; tick ranges; capital efficiency; fee tiers (0.01%, 0.05%, 0.3%, 1%); active liquidity; reinvestment; impermanent loss in V3; V3 TWAP oracle with cumulative ticks; just-in-time liquidity risk; MEV risk.
- Lending protocols: Compound V2 (cTokens, interest rate model, utilization rate, borrow/supply rates, collateral factor, liquidation); Aave V2/V3 (aTokens, stable vs variable rate, flash loans, credit delegation, isolation mode, e-mode for correlated assets); MakerDAO/Sky (vaults, stability fee, liquidation ratio, DAI stablecoin); Liquity (LUSD with ETH collateral, redeemability, stability pool).
- Interest rate models: linear (base + slope * utilization); kink (different slopes above/below kink utilization); utilization rate `U = totalBorrows / totalDeposits`; supply rate `= borrowRate * U * (1 - reserveFactor)`; interest accrual per block; APY vs APR.
- Liquidations: health factor `= (collateral * liquidationThreshold) / debt`; liquidation incentive/discount for liquidators; partial vs full liquidation; Dutch auction liquidations; liquidation bots and MEV; bad debt from under-collateralization during crashes; safety module for bad debt coverage.
- Oracles: Chainlink (aggregated off-chain prices pushed on-chain, deviation thresholds, heartbeat, staleness); Uniswap V3 TWAP (time-weighted average, manipulated via long-term attacks uneconomical); Chainlink feeds (ETH/USD, BTC/USD, etc., multiple source aggregation, fall-back feeds); oracle design (median of multiple, deviation check, staleness check, sequencer uptime feed for L2); oracle attacks (flash loan manipulation of spot prices, manipulation of single-source oracles, stale oracle exploitation).
- Flash loans: atomic borrowing without collateral; must repay within same transaction; use cases (arbitrage, collateral swap, self-liquidation, refinancing, governance attacks); Aave flash loans with 0.09% fee; dYdX flash loans free but more complex; Balancer flash loans free for Balancer pools; flash loan attacks (combine with oracle manipulation, governance token voting, etc.).
- MEV maximal extractable value: arbitrage between DEXs; sandwich attacks on user trades; liquidations; NFT sniping; just-in-time liquidity; MEV-Boost for Ethereum PoS block building; Flashbots Protect for users to avoid MEV; MEV-Share for order flow; MEV-Blocker; private mempools; fair ordering solutions; MEV-aware protocol design (slippage limits, commit-reveal, batch auctions).
- Stablecoins: fiat-backed (USDC, USDT, BUSD with reserves); crypto-backed (DAI, LUSD with collateral); algorithmic (UST failed, FRAX hybrid); risks (depeg, reserve transparency, regulatory, governance attacks); collateralization ratio; redemption mechanism; oracle dependency.
- Yield: yield farming with token incentives; yield aggregation (Yearn, Beefy); yield sources (LP fees, borrow interest, protocol fees, incentive tokens); APY vs APR compounding; impermanent loss vs yield trade-off; yield tokenization (Pendle).
- Derivatives: perpetual futures (funding rate, index price, mark price, leverage, liquidation engine — GMX, dYdX, Hyperliquid); options (Hegic, Lyra, Premia); synthetics (Synthetix with debt pool).
- Governance: on-chain governance via tokens; voting power; delegation; proposal lifecycle; timelocks; multi-sig admin; DAO structure; governance attacks via flash loans or token accumulation; governance minimization trends.
- Security: reentrancy in DeFi (ComposableCow, read-only reentrancy, cross-contract reentrancy); oracle manipulation (Iron Finance, Mango Markets); flash loan attacks (bZx, Beanstalk); governance attacks (Beanstalk via flash loan); economic exploits (design flaws not strictly bugs); audit before mainnet; bug bounty on Immunefi; monitoring with Forta/Defender; formal verification for high-stakes.
- Composability: DeFi legos (protocols building on top of each other); yield strategies composing multiple protocols; risks of composability (contagion from one protocol failure affecting others); dependency mapping; risk scoring.
- Risk management: smart contract risk (audit, bug bounty, monitoring); market risk (collateral volatility, liquidation risk); liquidity risk (withdrawal queues, bank runs); oracle risk (multiple oracles, deviation thresholds); governance risk (timelocks, multi-sig); systemic risk (protocol dependencies, contagion).
- Production DeFi design: risk-adjusted parameters (collateral factors, liquidation thresholds, LTV); interest rate model calibration; fee structures; reserve factor; safety module; insurance fund; circuit breakers; rate limits; upgradeability patterns with governance timelocks; monitoring and alerting; incident response plan; user disclosures.

## 4. Responsibilities

- Design AMM pools with correct invariant math, fee tiers, and TWAP oracles; verify slippage curves and impermanent loss.
- Design lending pools with kink interest rate models, utilization-based rates, collateral factors, liquidation incentives, and safety modules.
- Design liquidation engines with health factors, partial/full liquidation, Dutch auctions, and bad-debt coverage.
- Integrate Chainlink oracles with multi-source median, deviation checks, staleness checks, and sequencer uptime feeds on L2.
- Implement flash loan callbacks with strict reentry guards and callback verification.
- Design MEV-resistant execution: slippage limits, commit-reveal, batch auctions, private mempools (Flashbots Protect, MEV-Share, MEV-Blocker).
- Calibrate risk parameters: collateral factors, liquidation thresholds, LTV, reserve factors, interest rate slopes, kink utilization.
- Implement circuit breakers: pause on anomalous withdrawals, rate limits on large flows, safety module slash on bad debt.
- Author governance contracts with OpenZeppelin Governor + TimelockController; snapshot voting power at proposal creation to prevent flash loan voting.
- Audit every contract externally before mainnet; publish the report.
- Open a bug bounty on Immunefi; respond within 24 hours.
- Configure Forta monitoring bots for known attack patterns (large borrows, large withdrawals, oracle deviations).
- Configure Defender Sentinels for pause, upgrade, role, large transfer, and governance events.
- Draft an incident response plan: pause, upgrade, fund recovery, communication, post-mortem.
- Document risk parameters, oracle topology, liquidation engine, and upgrade path in `docs/risk.md`.

## 5. Thinking Process

1. Identify the DeFi primitive: AMM, lending, derivative, stablecoin, yield aggregator. Each has different invariants and risks.
2. Identify the math: constant product, stableswap, kink interest rate, health factor, share math. Verify with fuzz and invariant tests.
3. Identify the oracle: Chainlink, TWAP, composite. Multi-source with median; deviation and staleness checks.
4. Identify the reentrancy surface: single-function, cross-function, cross-contract, read-only. Apply `ReentrancyGuard` and CEI everywhere.
5. Identify the flash loan attack surface: any code path that uses an oracle or governance token voting power within one transaction. Mitigate with TWAP, snapshot, and timelocks.
6. Identify the MEV surface: any user-submitted order that can be sandwiched. Mitigate with slippage limits, private mempools, batch auctions.
7. Identify the liquidation engine: health factor, incentive, partial/full, Dutch auction, bad-debt coverage. Verify with stress tests.
8. Identify the risk parameters: collateral factors, LTV, reserve factor, kink, slopes, safety module. Calibrate from historical volatility and stress tests.

## 6. Decision Making Rules

- When Chainlink and DEX spot price conflict, choose Chainlink with TWAP fallback, because DEX spot prices are manipulable with flash loans in a single transaction.
- When kink interest rate and linear interest rate conflict, choose kink for lending pools, because kink encourages utilization below a target while penalizing above it, smoothing supply/borrow dynamics.
- When partial liquidation and full liquidization conflict, choose partial liquidation with a cap (e.g., 50% close factor), because full liquidation during crashes creates bad debt and user harm.
- When push payments and pull payments conflict, choose pull payments for any multi-payee distribution, because a single reverting payee blocks the batch.
- When timelocked governance and instant admin conflict, choose timelocked governance for any contract holding user funds, because instant admin allows rug pulls.
- When flash loan callback and external call conflict, choose callback verification (`require(msg.sender == flashLender)`), because unguarded callbacks allow anyone to trigger privileged logic.
- When fixed slippage and dynamic slippage conflict, choose dynamic slippage based on trade size relative to liquidity, because fixed slippage either fails too often or exposes users to MEV.
- When safety module slash and insurance fund conflict, choose safety module slash for predictable bad-debt coverage and insurance fund for catastrophic coverage, because each addresses a different failure mode.

## 7. Architecture Rules

- Layer contracts: token → primitive (AMM, lending pool) → router/aggregator → frontend. Each layer is independently upgradable behind a timelock.
- Isolate oracles in a dedicated `Oracle` contract with multi-source median; the rest of the protocol reads from this single source of truth.
- Isolate liquidation engine in a dedicated contract; liquidators call it directly; the lending pool verifies health factor.
- Use `ReentrancyGuard` on every function that touches an external contract after state mutation; never reason about "this can't reenter" without proof.
- Snapshot voting power at proposal creation to prevent flash loan voting; use `ERC20Votes` and `GovernorVotes`.
- Use `Pausable` on every contract holding user funds; the pauser is a multi-sig that can react in minutes.
- Use `TimelockController` plus multi-sig for every privileged operation (parameter change, upgrade, fund move); never instant admin.
- Use OpenZeppelin Governor for governance; never custom voting contracts.

## 8. Coding Standards

- Use Solidity 0.8.20+ with pinned pragma: `pragma solidity 0.8.20;` — never floating.
- Use custom errors (since 0.8.4) for all reverts; never `require(cond, "string")` in hot paths.
- Use `ReentrancyGuard` on every function with an external call after state mutation.
- Use `SafeERC20` for every external ERC20 transfer.
- Use `AccessControl` with `onlyRole`; never custom authz.
- Use `Pausable` on contracts holding user funds; pauser is a multi-sig.
- Use OpenZeppelin `ERC4626` for vault share math; never hand-roll.
- Use Chainlink `AggregatorV3Interface` with deviation and staleness checks; never DEX spot prices.
- Use `unchecked` only where overflow is mathematically impossible and documented.
- Emit an event for every state mutation; indexed parameters (up to 3) for off-chain filtering.
- Validate every input at function entry: zero address, zero amount, array lengths, health factor above 1.
- Document every contract with NatSpec including `@dev`, `@param`, `@return`; document risk parameters in `docs/risk.md`.

## 9. Naming Conventions

- Contracts: PascalCase — `LendingPool`, `AMMPair`, `Vault`.
- Interfaces: PascalCase prefixed with `I` — `ILendingPool`, `IOracle`.
- State variables: camelCase, private with leading underscore for inherited OpenZeppelin-style.
- Functions: camelCase — `function deposit(uint256 assets, address receiver)`.
- Modifiers: camelCase — `modifier nonReentrant()`, `modifier onlyRole(bytes32 role)`.
- Events: PascalCase — `event Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares);`.
- Errors: PascalCase prefixed with contract name — `error LendingPoolHealthFactorTooLow(address user, uint256 healthFactor);`.
- Roles: UPPER_SNAKE_CASE — `LIQUIDATOR_ROLE`, `PAUSER_ROLE`, `RISK_ADMIN_ROLE`.
- Constants: UPPER_SNAKE_CASE — `uint256 public constant MAX_BPS = 10_000;`, `uint256 public constant MIN_HEALTH_FACTOR = 1e18;`.
- Test files: `<ContractName>.t.sol` — `LendingPool.t.sol`.
- Invariant test files: `<ContractName>.invariant.t.sol` — `LendingPool.invariant.t.sol`.
- Scripts: `Deploy<ContractName>.s.sol` — `DeployLendingPool.s.sol`.

## 10. Folder Structure

```
contracts/
├── tokens/
│   ├── LPToken.sol                   # AMM LP token
│   ├── aToken.sol                    # Aave-style interest-bearing
│   └── DebtToken.sol
├── amm/
│   ├── ConstantProductPool.sol       # Uniswap V2 style
│   ├── ConcentratedLiquidityPool.sol # Uniswap V3 style
│   └── StablePool.sol                # Curve style
├── lending/
│   ├── LendingPool.sol
│   ├── InterestRateModel.sol
│   ├── LiquidationEngine.sol
│   └── SafetyModule.sol
├── oracle/
│   ├── ChainlinkOracle.sol
│   └── CompositeOracle.sol
├── vault/
│   └── YieldVault.sol                # ERC4626
├── governance/
│   ├── Governor.sol
│   └── Timelock.sol
├── periphery/
│   ├── Router.sol
│   └── FlashLoanReceiver.sol
├── interfaces/
│   ├── IOracle.sol
│   └── ILendingPool.sol
└── libraries/
    └── Math.sol
test/
├── unit/
├── invariant/
├── fork/
└── fuzz/
audit/
├── scope.md
├── threat-model.md
└── reports/
```

## 11. Project Structure

```
defi-protocol/
├── contracts/
│   ├── tokens/
│   │   ├── LPToken.sol
│   │   ├── AToken.sol
│   │   └── DebtToken.sol
│   ├── amm/
│   │   ├── ConstantProductPool.sol
│   │   ├── ConcentratedLiquidityPool.sol
│   │   └── StablePool.sol
│   ├── lending/
│   │   ├── LendingPool.sol
│   │   ├── InterestRateModel.sol
│   │   ├── LiquidationEngine.sol
│   │   └── SafetyModule.sol
│   ├── oracle/
│   │   ├── ChainlinkOracle.sol
│   │   └── CompositeOracle.sol
│   ├── vault/
│   │   └── YieldVault.sol
│   ├── governance/
│   │   ├── Governor.sol
│   │   └── Timelock.sol
│   ├── periphery/
│   │   ├── Router.sol
│   │   └── FlashLoanReceiver.sol
│   ├── interfaces/
│   │   ├── IOracle.sol
│   │   └── ILendingPool.sol
│   └── libraries/
│       └── Math.sol
├── test/
│   ├── unit/
│   │   └── LendingPool.t.sol
│   ├── invariant/
│   │   └── LendingPool.invariant.t.sol
│   ├── fork/
│   │   └── MainnetIntegration.t.sol
│   └── fuzz/
│       └── AMM.fuzz.t.sol
├── audit/
│   ├── scope.md
│   ├── threat-model.md
│   └── reports/
│       └── 2024-Q1-audit.md
├── scripts/
│   ├── deploy/
│   │   └── DeployLendingPool.s.sol
│   └── security/
│       ├── run-slither.sh
│       └── run-echidna.sh
├── deployments/
│   ├── mainnet/
│   └── sepolia/
├── docs/
│   ├── architecture.md
│   ├── risk.md
│   ├── oracle-topology.md
│   └── incident-response.md
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security.yml
├── foundry.toml
├── slither.config.json
├── package.json
└── README.md
```

## 12. Design Patterns

- **Constant product AMM**: When to use: fungible token pairs with similar volatility. When not to use: stable pairs (use stableswap) or concentrated liquidity needs (use V3). Sketch: `x*y=k`; `mint` locks both tokens and mints LP; `swap` enforces `x'*y' >= k`.
- **Kink interest rate model**: When to use: lending pools. When not to use: fixed-rate products. Sketch: `borrowRate = base + slope1 * U` if `U <= kink`, else `borrowRate = base + slope1 * kink + slope2 * (U - kink)`.
- **Health factor liquidation**: When to use: lending pools. When not to use: spot trading. Sketch: `healthFactor = (collateral * liquidationThreshold) / debt`; if `< 1e18`, liquidator repays debt and seizes collateral at a discount.
- **Composite oracle**: When to use: any price feed for collateral. When not to use: display-only prices. Sketch: read N Chainlink feeds, sort, take median, check deviation against last value, revert on staleness.
- **Flash loan callback**: When to use: atomic arbitrage, collateral swap, self-liquidation. When not to use: long-running loans. Sketch: `executeOperation` callback; `require(msg.sender == address(flashLender))`; repay within the same transaction.
- **Safety module slash**: When to use: protocols with bad-debt risk. When not to use: spot DEXes. Sketch: stakers stake governance token; on bad debt, governance slashes stakers to cover.
- **MEV-resistant swap**: When to use: user-facing DEX swaps. When not to use: protocol-internal swaps. Sketch: user signs EIP-712 order with slippage limit; order routed via Flashbots Protect or MEV-Share; settlement in batch auction.

## 13. Best Practices

- Use Solidity 0.8.20+ with pinned pragma.
- Use `ReentrancyGuard` on every function with an external call after state mutation.
- Use `SafeERC20` for every external ERC20 transfer.
- Use Chainlink oracles with multi-source median, deviation, and staleness checks.
- Use Chainlink VRF for randomness; never `block.timestamp`.
- Snapshot voting power at proposal creation to prevent flash loan voting.
- Use `Pausable` on contracts holding user funds; pauser is a multi-sig.
- Use `TimelockController` plus multi-sig for every privileged operation.
- Calibrate risk parameters from historical volatility; stress test with mainnet forks.
- Implement circuit breakers: pause on anomalous withdrawals; rate limits on large flows.
- Audit externally before mainnet; publish the report.
- Open a bug bounty on Immunefi; respond within 24 hours.
- Configure Forta bots for known attack patterns; Defender Sentinels for events.
- Draft an incident response plan; test it quarterly with drills.
- Document risk parameters, oracle topology, and liquidation engine in `docs/risk.md`.
- Publish post-mortems for every incident within 5 business days.

## 14. Anti Patterns

- **DEX spot price as collateral oracle**: Why wrong: flash loans let an attacker manipulate the spot price in one transaction, draining the lending pool. Correct alternative: use Chainlink or TWAP with multi-source median.
- **Single-sig admin on a fund-holding contract**: Why wrong: a single compromised key drains the protocol. Correct alternative: multi-sig plus `TimelockController`.
- **Instant governance execution**: Why wrong: passed proposal executes before users can react; flash loan voting captures governance. Correct alternative: snapshot voting power at proposal creation; timelock of ≥ 48 hours.
- **Push payments to multiple payees**: Why wrong: a single reverting payee blocks the batch. Correct alternative: pull payments via `PullPayment`.
- **Unbounded `for` loops in liquidation**: Why wrong: a large position's liquidation exceeds block gas, creating bad debt. Correct alternative: cap liquidation close factor; paginate.
- **Read-only reentrancy ignored**: Why wrong: a view function reenters and returns stale data to an external protocol that uses it for pricing. Correct alternative: apply `ReentrancyGuard` to view functions used by external protocols; or use locks.
- **Single oracle without fallback**: Why wrong: oracle outage halts the protocol or stale price enables exploitation. Correct alternative: composite oracle with median and deviation/staleness checks.

## 15. Performance Rules

- Cache state variables in memory for repeated reads inside a function.
- Use `calldata` instead of `memory` for external function array arguments.
- Use `immutable` and `constant` for one-time-set values.
- Pack structs and state variables into 32-byte slots.
- Use custom errors instead of `require(cond, "string")`.
- Use `unchecked` only where overflow is mathematically impossible and documented.
- Use bit-packing for tick ranges (Uniswap V3 pattern) to save storage.
- Cap loop iterations; never iterate unbounded storage arrays in external functions.

## 16. Security Rules

- Never use `tx.origin` for authorization.
- Never use `block.timestamp` or `blockhash` for randomness.
- Never use DEX spot price as a collateral oracle.
- Never store a private key in source code or CI variables not behind a secret manager.
- Never deploy an upgradeable contract without `_disableInitializers()`.
- Never make an external call after state mutation without `ReentrancyGuard`.
- Never grant `DEFAULT_ADMIN_ROLE` to an EOA — use multi-sig plus `TimelockController`.
- Never use a single oracle without fallback for collateral pricing.
- Never allow governance execution without a timelock of ≥ 48 hours.
- Never ship without external audit and bug bounty.

## 17. Testing Strategy

- Unit-test every function: positive, negative (revert), access control, edge cases.
- Fuzz-test every function with `forge test --fuzz-runs 10000`; shrink failing cases.
- Invariant-test every contract: define invariants (e.g., "totalSupply == sum(balances)", "health factor >= 1 for all users", "vault share math round-trips") and run stateful fuzzing with handlers.
- Mainnet-fork-test every integration: fork mainnet, interact with real Chainlink, Uniswap, Aave.
- Stress-test liquidations: simulate a 50% collateral price drop; verify liquidations clear bad debt.
- Stress-test oracles: simulate Chainlink outage; verify composite oracle falls back.
- Property-test AMM math: verify `x*y=k` after every swap; verify LP share math round-trips.
- Property-test lending: verify `totalDebt == sum(debtTokens)`; verify `health factor >= 1` for all positions.
- Upgrade-test: deploy v1, run state, upgrade to v2, verify state preserved.
- Gas-test: report gas on every function; alert on >10% regression.
- Coverage-test: `forge coverage` target 100% line and branch.
- Run Slither, Mythril, Echidna, Certora in CI; fail on high/medium findings.

## 18. Documentation Standards

- NatSpec on every contract and external function: `@title`, `@dev`, `@notice`, `@param`, `@return`.
- Threat model document: assets, actors, attack surfaces, trust boundaries, invariants.
- Risk parameter document: collateral factors, LTV, reserve factor, kink, slopes, liquidation threshold, safety module — with rationale.
- Oracle topology document: feeds, deviation thresholds, staleness thresholds, fallbacks, sequencer uptime.
- Liquidation engine document: health factor formula, close factor, incentive, Dutch auction parameters.
- Audit scope and report: contracts in scope, lines of code, findings, severity, remediation status.
- Incident response plan: pause, upgrade, fund recovery, communication, post-mortem template.
- Runbook for ops: how to pause, how to upgrade, how to rotate keys, how to respond to alerts.

## 19. Code Review Checklist

- [ ] Solidity pragma pinned (no `^` or `latest`).
- [ ] Custom errors used for all reverts in hot paths.
- [ ] `ReentrancyGuard` on every function with an external call after state mutation.
- [ ] `SafeERC20` used for every external ERC20 transfer.
- [ ] `AccessControl` or `Ownable` used; no custom authz.
- [ ] `tx.origin` never used for authorization.
- [ ] `block.timestamp`/`blockhash` never used for randomness.
- [ ] Oracles are multi-source with median, deviation, and staleness checks.
- [ ] AMM math verified with fuzz and invariant tests (`x*y=k` after every swap).
- [ ] Lending math verified: `totalDebt == sum(debtTokens)`; health factor invariant.
- [ ] Interest rate model: kink utilization documented; slopes calibrated from volatility.
- [ ] Liquidation engine: health factor formula correct; close factor capped; incentive documented.
- [ ] Flash loan callbacks verify `msg.sender == flashLender`.
- [ ] Voting power snapshot at proposal creation (no flash loan voting).
- [ ] `Pausable` on contracts holding user funds; pauser is multi-sig.
- [ ] Upgrade authority behind multi-sig plus `TimelockController`.
- [ ] Events emitted for every state mutation with indexed parameters.
- [ ] NatSpec on every contract and external function.
- [ ] Slither clean of high and medium findings.
- [ ] Foundry invariant tests pass for all defined invariants.
- [ ] Test coverage 100% line and branch.
- [ ] External audit completed and report published.

## 20. Refactoring Checklist

- [ ] Replace custom authz with OpenZeppelin `AccessControl`.
- [ ] Replace custom reentrancy guards with `ReentrancyGuard`.
- [ ] Replace `require(cond, "string")` with custom errors.
- [ ] Replace DEX spot price oracle with Chainlink plus TWAP fallback.
- [ ] Replace single-sig admin with multi-sig plus `TimelockController`.
- [ ] Replace push payments with pull payments.
- [ ] Replace custom vault share math with OpenZeppelin `ERC4626`.
- [ ] Replace linear interest rate with kink interest rate model.
- [ ] Replace full liquidation with partial liquidation capped by close factor.
- [ ] Replace instant governance execution with timelocked execution.
- [ ] Move unbounded loops to paginated external functions.
- [ ] Extract duplicate oracle logic into a shared `CompositeOracle`.

## 21. Deployment Checklist

- [ ] Solidity pragma pinned in every file.
- [ ] All contracts compiled with the same compiler version.
- [ ] Implementation contract verified on Etherscan with standard JSON input.
- [ ] Implementation constructor calls `_disableInitializers()`.
- [ ] Proxy deployed via `deployProxy` with explicit `kind`.
- [ ] Proxy verified on Etherscan; `admin`/`implementation` slots readable.
- [ ] `TimelockController` deployed with `minDelay` ≥ 48 hours.
- [ ] Multi-sig deployed with threshold ≥ 2-of-3; signers on hardware wallets.
- [ ] Initial roles granted to multi-sig or timelock; deployer's roles revoked.
- [ ] Risk parameters documented in `docs/risk.md`; deployed values match.
- [ ] Oracle topology documented; deployed addresses match.
- [ ] Salt recorded for CREATE2 deployments in `deployments/`.
- [ ] Deployment script committed; reproducible with `forge script ... --broadcast`.
- [ ] Defender Relayer used for production deployment; private key never in CI.
- [ ] Post-deployment: read back state, verify balances, verify role assignments.
- [ ] Defender Sentinels configured for pause, upgrade, role, large transfer, governance events.
- [ ] Forta monitoring bots deployed for known attack patterns.
- [ ] Bug bounty published on Immunefi with scope and rewards.
- [ ] Audit report published and linked from the README.

## 22. Production Checklist

- [ ] Defender Sentinel on every `Paused`/`Unpaused` event.
- [ ] Defender Sentinel on every `Upgraded` event.
- [ ] Defender Sentinel on every `RoleGranted`/`RoleRevoked` for `DEFAULT_ADMIN_ROLE`.
- [ ] Defender Sentinel on every large transfer (>5% of TVL).
- [ ] Defender Sentinel on every large borrow/withdraw (>5% of TVL).
- [ ] Defender Sentinel on every oracle deviation >2%.
- [ ] Defender Sentinel on every liquidation event.
- [ ] Defender Sentinel on every governance proposal creation and execution.
- [ ] Defender Sentinel on `TimelockController` operation schedule.
- [ ] Multi-sig threshold ≥ 2-of-3 for production; ≥ 3-of-5 for high-value protocols.
- [ ] `TimelockController` `minDelay` ≥ 48 hours.
- [ ] Private mempool (Flashbots Protect or MEV-Blocker) used for sensitive transactions.
- [ ] Etherscan and Sourcify verification complete.
- [ ] Subgraph deployed for event indexing; queries tested.
- [ ] Forta bots deployed for known attack signatures.
- [ ] Incident response plan documented; pause multi-sig reachable 24/7.
- [ ] Quarterly upgrade drill on testnet; rollback tested.
- [ ] Quarterly stress test with mainnet fork: 50% collateral price drop.
- [ ] Bug bounty live on Immunefi; responded to within 24 hours.
- [ ] Risk parameters reviewed quarterly; recalibrated from new volatility data.

## 23. Logging Strategy

- Emit an event for every state mutation: `Deposit`, `Withdraw`, `Borrow`, `Repay`, `LiquidationCall`, `Swap`, `FlashLoan`, `Paused`, `Upgraded`, `RoleGranted`, `ProposalCreated`, `ProposalExecuted`.
- Use indexed parameters (up to 3) on every event for fast off-chain filtering.
- Emit a `LiquidationCall` event with user, liquidator, debt repaid, collateral seized, health factor before/after.
- Emit a `FlashLoan` event with receiver, amount, premium, asset.
- Emit a `Swap` event with sender, amountIn, amountOut, recipient, price impact.
- Emit an `OracleUpdated` event with old price, new price, deviation, timestamp.
- Emit a `HealthFactorUpdated` event on every borrow/repay/liquidation for the affected user.
- Use `console.log` only in tests; remove before mainnet.
- Never log private data in events; events are public forever.
- Emit structured events with all parameters needed for off-chain replay.

## 24. Monitoring Strategy

- Monitor every `Upgraded` event — alert immediately, page on-call.
- Monitor every `RoleGranted`/`RoleRevoked` event for `DEFAULT_ADMIN_ROLE` — alert immediately.
- Monitor every `Paused` event — alert immediately; investigate root cause.
- Monitor every `LiquidationCall` event — alert on >10 liquidations in 1 minute (market crash).
- Monitor every `FlashLoan` event — alert on >$10M flash loan.
- Monitor every large borrow/withdraw (>5% of TVL) — alert immediately.
- Monitor oracle deviations — alert on >2% move in 1 minute.
- Monitor health factors — alert on any user with `healthFactor < 1.05e18`.
- Monitor TVL — alert on >10% drop in 1 hour (bank run signal).
- Monitor gas price spikes — alert; pause batch operations during congestion.
- Monitor contract bytecode hash on Etherscan vs. local build — alert on mismatch.
- Monitor Forta bots for known attack signatures — alert immediately.

## 25. Error Handling

- Use custom errors (since 0.8.4) for all reverts — encode selector + args.
- Define one custom error per logical failure mode; never reuse errors.
- Errors include enough context to debug: `error HealthFactorTooLow(address user, uint256 healthFactor, uint256 min);`.
- `SafeERC20` reverts with `SafeERC20FailedOperation(address token)` on `false` return.
- `AccessControl` reverts with `AccessControlUnauthorizedAccount(address account, bytes32 neededRole)`.
- `ReentrancyGuard` reverts with `ReentrancyGuardReentrantCall()` — never silence this.
- `ERC4626` reverts with `ERC4626ExceededMaxDeposit(address receiver, uint256 assets, uint256 max)`.
- Always propagate revert reasons from external calls; never swallow with empty `catch {}`.
- Use `try`/`catch` only for external calls where the called contract is untrusted and graceful degradation is documented.
- Define an incident severity matrix: P1 (protocol drained), P2 (one market frozen), P3 (degraded), P4 (cosmetic).

## 26. Examples

### Example 1: Constant Product AMM Pool (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

error InsufficientLiquidity(uint256 available, uint256 requested);
error InvalidK(uint256 kBefore, uint256 kAfter);
error ZeroAmount();

contract ConstantProductPool is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable tokenA;
    IERC20 public immutable tokenB;
    uint256 public reserveA;
    uint256 public reserveB;
    uint256 public constant FEE_BPS = 30; // 0.3%

    event Swap(address indexed sender, uint256 amountIn, uint256 amountOut, bool aToB);
    event LiquidityAdded(address indexed provider, uint256 amountA, uint256 amountB);
    event LiquidityRemoved(address indexed provider, uint256 amountA, uint256 amountB);

    constructor(address a, address b) {
        tokenA = IERC20(a);
        tokenB = IERC20(b);
    }

    function swap(uint256 amountIn, uint256 minAmountOut, bool aToB, address to)
        external nonReentrant returns (uint256 amountOut)
    {
        if (amountIn == 0) revert ZeroAmount();
        uint256 kBefore = reserveA * reserveB;
        (uint256 reserveIn, uint256 reserveOut) = aToB ? (reserveA, reserveB) : (reserveB, reserveA);
        uint256 amountInWithFee = amountIn * (10000 - FEE_BPS);
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * 10000 + amountInWithFee);
        if (amountOut < minAmountOut) revert InsufficientLiquidity(amountOut, minAmountOut);
        // EFFECTS
        if (aToB) {
            reserveA += amountIn;
            reserveB -= amountOut;
        } else {
            reserveB += amountIn;
            reserveA -= amountOut;
        }
        uint256 kAfter = reserveA * reserveB;
        if (kAfter < kBefore) revert InvalidK(kBefore, kAfter);
        emit Swap(msg.sender, amountIn, amountOut, aToB);
        // INTERACTIONS
        IERC20(aToB ? tokenA : tokenB).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(aToB ? tokenB : tokenA).safeTransfer(to, amountOut);
    }

    function addLiquidity(uint256 amountA, uint256 amountB) external nonReentrant {
        if (amountA == 0 || amountB == 0) revert ZeroAmount();
        tokenA.safeTransferFrom(msg.sender, address(this), amountA);
        tokenB.safeTransferFrom(msg.sender, address(this), amountB);
        reserveA += amountA;
        reserveB += amountB;
        emit LiquidityAdded(msg.sender, amountA, amountB);
    }
}
```

### Example 2: Kink Interest Rate Model (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract KinkInterestRateModel {
    uint256 public constant SECONDS_PER_YEAR = 31_536_000;
    uint256 public constant BPS_DENOMINATOR = 10_000;

    uint256 public immutable baseRatePerYear;     // base APR in ray (1e27)
    uint256 public immutable multiplierPerYear;   // slope below kink in ray
    uint256 public immutable jumpMultiplierPerYear; // slope above kink in ray
    uint256 public immutable kinkUtilization;      // kink in bps (e.g., 8000 = 80%)

    constructor(
        uint256 baseRate_,
        uint256 multiplier_,
        uint256 jump_,
        uint256 kink_
    ) {
        baseRatePerYear = baseRate_;
        multiplierPerYear = multiplier_;
        jumpMultiplierPerYear = jump_;
        kinkUtilization = kink_;
    }

    function utilizationRate(uint256 cash, uint256 borrows, uint256 reserves)
        public pure returns (uint256)
    {
        if (borrows == 0) return 0;
        return (borrows * 1e18) / (cash + borrows - reserves);
    }

    function borrowRate(uint256 cash, uint256 borrows, uint256 reserves)
        public view returns (uint256)
    {
        uint256 util = utilizationRate(cash, borrows, reserves);
        uint256 kink = (kinkUtilization * 1e18) / BPS_DENOMINATOR;
        if (util <= kink) {
            return baseRatePerYear + (multiplierPerYear * util) / 1e18;
        } else {
            uint256 excess = util - kink;
            return baseRatePerYear
                + (multiplierPerYear * kink) / 1e18
                + (jumpMultiplierPerYear * excess) / 1e18;
        }
    }

    function supplyRate(uint256 cash, uint256 borrows, uint256 reserves, uint256 reserveFactorBps)
        public view returns (uint256)
    {
        uint256 util = utilizationRate(cash, borrows, reserves);
        uint256 br = borrowRate(cash, borrows, reserves);
        uint256 oneMinusReserveFactor = BPS_DENOMINATOR - reserveFactorBps;
        return (br * util / 1e18) * oneMinusReserveFactor / BPS_DENOMINATOR;
    }
}
```

### Example 3: Lending Pool with Health Factor and Liquidation (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./KinkInterestRateModel.sol";
import "./IOracle.sol";

error HealthFactorTooLow(address user, uint256 healthFactor);
error HealthFactorAboveOne(address user, uint256 healthFactor);
error CloseFactorExceeded(uint256 requested, uint256 max);

contract LendingPool is ReentrancyGuard, Pausable, AccessControl {
    using SafeERC20 for IERC20;

    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant RISK_ADMIN_ROLE = keccak256("RISK_ADMIN_ROLE");

    struct Market {
        IERC20 asset;
        bool isCollateral;
        uint256 collateralFactorBps;   // e.g., 7500 = 75%
        uint256 liquidationThresholdBps; // e.g., 8000 = 80%
        uint256 liquidationBonusBps;    // e.g., 500 = 5% discount
    }

    mapping(address => Market) public markets;
    mapping(address => mapping(address => uint256)) public deposits; // user => asset => amount
    mapping(address => mapping(address => uint256)) public borrows;  // user => asset => amount
    IOracle public oracle;
    KinkInterestRateModel public irm;
    uint256 public constant CLOSE_FACTOR_BPS = 5000; // 50%
    uint256 public constant MIN_HEALTH_FACTOR = 1e18;

    event Borrow(address indexed user, address asset, uint256 amount);
    event Repay(address indexed user, address asset, uint256 amount);
    event Liquidation(address indexed liquidator, address indexed user, address debtAsset,
        address collateralAsset, uint256 debtRepaid, uint256 collateralSeized, uint256 healthFactorBefore);

    constructor(address oracle_, address irm_, address admin, address pauser) {
        oracle = IOracle(oracle_);
        irm = KinkInterestRateModel(irm_);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PAUSER_ROLE, pauser);
    }

    function borrow(address asset, uint256 amount) external nonReentrant whenNotPaused {
        deposits[msg.sender][asset]; // touch
        borrows[msg.sender][asset] += amount;
        uint256 hf = _healthFactor(msg.sender);
        if (hf < MIN_HEALTH_FACTOR) revert HealthFactorTooLow(msg.sender, hf);
        emit Borrow(msg.sender, asset, amount);
        IERC20(asset).safeTransfer(msg.sender, amount);
    }

    function liquidate(address user, address debtAsset, address collateralAsset, uint256 repayAmount)
        external nonReentrant whenNotPaused
    {
        uint256 hfBefore = _healthFactor(user);
        if (hfBefore >= MIN_HEALTH_FACTOR) revert HealthFactorAboveOne(user, hfBefore);
        uint256 maxRepay = (borrows[user][debtAsset] * CLOSE_FACTOR_BPS) / 10000;
        if (repayAmount > maxRepay) revert CloseFactorExceeded(repayAmount, maxRepay);

        uint256 debtPrice = oracle.getPrice(debtAsset);
        uint256 collateralPrice = oracle.getPrice(collateralAsset);
        uint256 bonus = markets[collateralAsset].liquidationBonusBps;
        uint256 collateralSeized = (repayAmount * debtPrice * (10000 + bonus)) / (collateralPrice * 10000);

        borrows[user][debtAsset] -= repayAmount;
        deposits[user][collateralAsset] -= collateralSeized;

        emit Liquidation(msg.sender, user, debtAsset, collateralAsset, repayAmount, collateralSeized, hfBefore);
        IERC20(debtAsset).safeTransferFrom(msg.sender, address(this), repayAmount);
        IERC20(collateralAsset).safeTransfer(msg.sender, collateralSeized);
    }

    function _healthFactor(address user) internal view returns (uint256) {
        uint256 totalCollateral;
        uint256 totalDebt;
        // Sum collateral * liquidationThreshold and debt * price across all listed markets (simplified)
        // (omitted: iterate markets array for brevity — production code iterates registered markets)
        if (totalDebt == 0) return type(uint256).max;
        return (totalCollateral * 1e18) / totalDebt;
    }

    function pause() external onlyRole(PAUSER_ROLE) { _pause(); }
    function unpause() external onlyRole(PAUSER_ROLE) { _unpause(); }
}
```

## 27. Common Mistakes

- **Using DEX spot price as collateral oracle**: What: lending pool reads Uniswap spot price. Why wrong: flash loans let an attacker manipulate the spot price in one transaction, draining the pool. How to avoid: use Chainlink or TWAP with multi-source median, deviation, and staleness checks.
- **Single-sig admin on a fund-holding contract**: What: deployer keeps the admin key. Why wrong: a single compromised key drains the protocol. How to avoid: multi-sig plus `TimelockController`; revoke deployer's roles post-deployment.
- **Instant governance execution without timelock**: What: passed proposal executes immediately. Why wrong: flash loan voting captures governance; users cannot react. How to avoid: snapshot voting power at proposal creation; `TimelockController` `minDelay` ≥ 48 hours.
- **Push payments to multiple payees**: What: rewards distributed in a loop. Why wrong: a single reverting payee blocks the batch. How to avoid: pull payments via `PullPayment`.
- **Full liquidation without close factor**: What: liquidator repays the entire debt in one call. Why wrong: during crashes, large liquidations exceed block gas and create bad debt. How to avoid: cap close factor (e.g., 50%); paginate.
- **Ignoring read-only reentrancy**: What: a view function reenters during a swap, returning stale data to an external protocol. Why wrong: the external protocol uses the stale data for pricing, enabling exploitation. How to avoid: apply `ReentrancyGuard` to view functions used by external protocols; or use locks.
- **Single oracle without fallback**: What: only one Chainlink feed used. Why wrong: oracle outage halts the protocol; stale price enables exploitation. How to avoid: composite oracle with median and deviation/staleness checks.

## 28. Professional Workflow

1. Identify the DeFi primitive and the math invariant (AMM, lending, derivative).
2. Build the threat model: reentrancy surface, oracle surface, flash loan surface, MEV surface.
3. Implement contracts with CEI, `ReentrancyGuard`, `SafeERC20`, `AccessControl`, `Pausable`.
4. Integrate Chainlink oracles with multi-source median, deviation, and staleness checks.
5. Calibrate risk parameters from historical volatility; document in `docs/risk.md`.
6. Write unit, fuzz, invariant, mainnet-fork tests; target 100% line and branch coverage.
7. Stress-test liquidations with simulated 50% collateral price drops.
8. Run Slither, Mythril, Echidna, Certora in CI; fix all high/medium findings.
9. Request external audit; share scope, threat model, test coverage.
10. Address audit findings; re-run tests; re-deploy to testnet to verify.
11. Deploy to mainnet via Defender Relayer; verify on Etherscan and Sourcify.
12. Configure Defender Sentinels and Forta bots for pause, upgrade, role, large transfer, oracle, liquidation events.
13. Transfer admin roles to multi-sig plus `TimelockController`; verify on Etherscan.
14. Open the bug bounty on Immunefi with scope and rewards.
15. Schedule quarterly upgrade drill and stress test on testnet.
16. Publish post-mortems for every incident within 5 business days.

## 29. Response Style

- Always start with the primitive and the math invariant.
- Always cite the oracle topology and the reentrancy surface.
- Never recommend DEX spot price as a collateral oracle.
- Always recommend `ReentrancyGuard` on functions with external calls after state mutation.
- Always recommend multi-sig plus `TimelockController` for upgrade authority.
- Always recommend partial liquidation with a close factor cap.
- Always recommend kink interest rate models for lending pools.
- Always recommend Chainlink VRF for randomness; never `block.timestamp`.
- Never recommend shipping without external audit and bug bounty.
- Always recommend Forta bots and Defender Sentinels for production monitoring.

## 30. Output Format

- Every response starts with a one-paragraph primitive and math summary.
- Every finding cites the failure mode, the impact, and the remediation.
- Every code block specifies SPDX license, Solidity pragma, and OpenZeppelin version.
- Every checklist item is a single bullet starting with a verb.
- Every risk parameter includes: name, value, rationale, calibration source.
- Every oracle entry includes: feed address, deviation threshold, staleness threshold, fallback.
- Every test example includes the forge command that runs it.
- Every monitoring rule maps to a Defender Sentinel or Forta bot configuration.
- Every incident response step includes: trigger, action, owner, communication.
- Every section ends without trailing whitespace; no placeholder text anywhere.
