# Oracles and MEV

Reading prices safely, oracle attack patterns, and MEV exposure of swaps, liquidations and vaults. Feed-specific values (heartbeat, deviation, decimals) differ per feed and chain; read them from the feed's page in the Chainlink docs and from `decimals()` on-chain.

## Chainlink Data Feeds

`AggregatorV3Interface` (from `@chainlink/contracts` 1.5.0) exposes `decimals()`, `description()`, `version()`, `getRoundData(roundId)` and `latestRoundData()`:

| Field | Meaning |
|---|---|
| `roundId` | Round identifier |
| `answer` | Price as `int256`, scaled by the feed's `decimals()` |
| `startedAt` | When the round started |
| `updatedAt` | When the answer was last updated |
| `answeredInRound` | Legacy round field; judge freshness by `updatedAt` (check the current docs) |

Required checks on every read:

1. `answer > 0` (the type is signed).
2. `updatedAt != 0` and `block.timestamp - updatedAt <= maxAge`, where `maxAge` is the feed's heartbeat plus a small buffer.
3. Normalize with `decimals()` (many USD feeds use 8, but do not assume; ETH-denominated feeds commonly use 18).
4. On L2 chains, read the sequencer uptime feed: `answer == 0` means the sequencer is up and `1` means down; `startedAt` is when that status began. Revert while down and during a grace period after recovery, so stale or liquidation-triggering prices cannot be used immediately.
5. Optionally compare with a secondary source (second feed, TWAP) and revert or pause on large deviation.

A feed adapter implementing checks 1 to 4 is in the Examples section of [SKILL.md](../SKILL.md#14-examples).

Design notes:

- Feeds update on a heartbeat or when the price deviates by a threshold, so on-chain prices lag the market by design; set liquidation thresholds and caps with that lag in mind.
- Pair feeds when no direct pair exists (for example TOKEN/ETH and ETH/USD) and multiply with correct decimal handling; the errors of both feeds compound.
- Wrapped, staked and bridged assets can depeg from the asset a feed prices; use a feed for the actual asset or add a depeg check.
- A feed can be deprecated or paused; make the oracle address upgradeable only through a timelock, and handle reverts from `latestRoundData` with an explicit fallback or pause path.
- Pull-based oracles (such as Pyth, RedStone or Chainlink low-latency products) require the transaction to submit or trigger a price update and often provide a confidence or timestamp; apply the same staleness and sanity checks and follow each provider's current integration docs.

## Uniswap TWAP

- Uniswap V3 pools record cumulative ticks; `observe` over a window gives a time-weighted mean tick, from which a price is derived. The helper library is `OracleLibrary` in `@uniswap/v3-periphery` (written for Solidity 0.7; call it from an adapter or port it).
- Manipulating a TWAP requires holding the manipulated price across many blocks, which costs more with longer windows and deeper liquidity. Short windows on thin pools are weak.
- Use TWAP as a cross-check or fallback to a decentralized feed, or for long-tail assets that have no feed, with pool-liquidity minimums.
- Never use `slot0` or reserve ratios directly.

## Oracle attack patterns

- **Spot price manipulation**: flash-loan a large swap, move a pool price, call the victim protocol that reads that pool, and unwind in the same transaction. Defense: do not read same-transaction-manipulable prices.
- **Stale oracle**: a feed stops updating, the market moves, and an attacker borrows or liquidates at the old price. Defense: max-age checks and pause on failure.
- **Thin-market manipulation across blocks**: pumping an illiquid asset used as collateral on a venue that feeds the oracle (the Mango Markets exploit in October 2022 is the well-known case). Defense: collateral caps, liquidity-aware risk parameters, no oracle derived from one venue for illiquid assets.
- **Governance and flash-loan combination**: borrow voting power in one transaction to pass a proposal (the Beanstalk exploit in April 2022). Defense: voting snapshots from before the proposal, timelocks and execution delays.
- **Donation attacks**: balances read via `balanceOf` can be changed by direct transfers; ERC-4626 vaults and LP pricing must not trust raw balances. See [lending-liquidations.md](lending-liquidations.md).
- **Read-only reentrancy**: a view function of protocol A read by protocol B during a callback in A returns inconsistent state. Defense: guard views used as oracles or check the reentrancy status.

## MEV

Maximal extractable value is value gained by ordering, inserting or censoring transactions in a block.

| Pattern | Mechanism | Mitigation |
|---|---|---|
| Sandwich | Attacker buys before and sells after a victim's swap, profiting from the victim's slippage allowance | Tight `minOut`, deadlines, private order flow, batch auctions, smaller trades |
| Arbitrage / backrun | Trades after a price-moving transaction to realign pools | Largely benign; protocols can capture it via auctions or hooks |
| Liquidation races | Bots compete to liquidate unhealthy positions | Fair incentive sizing; do not rely on one keeper |
| Just-in-time liquidity | Liquidity added before a large swap and removed right after, capturing fees | Accept as market behavior; hooks or fee design can respond (v4) |
| Oracle-update frontrunning | Trading ahead of a visible oracle update | Deviation-based updates, trade limits, pause windows |

Mitigations at the integration level:

- Compute `minOut` from an independent price and a stated slippage budget; set a short `deadline`.
- Route user swaps through private transaction channels or MEV-protected RPC endpoints where available (Flashbots Protect and MEV Blocker are examples; check each service's current docs and guarantees).
- Prefer venues with batch auctions or intent-based settlement (CoW Protocol is one) for large or sensitive trades.
- Avoid designs where a pending transaction reveals a profitable ordering; commit-reveal or batching can help.
- On the builder and proposer side, Ethereum block building runs through MEV-Boost relays; protocol designers should assume ordering is adversarial rather than depend on it.
