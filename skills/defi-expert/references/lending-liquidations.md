# Lending, Liquidations, Flash Loans and Vaults

Rate models, health factor math, liquidation design, Aave V3 and V4 notes, a flash-loan receiver and ERC-4626 details. Parameters in examples are illustrative; read real values from the protocol. Solidity compiles with solc 0.8.38, OpenZeppelin Contracts 5.6.1 and `@aave/core-v3` 1.19.3.

## Utilization and rate models

- Utilization `U = totalBorrows / (cash + totalBorrows)`.
- Kink model: below the kink, `borrowRate = base + slope1 * U / kink`; above it, the rate rises with `slope2` over the remaining utilization range. The steep second slope pushes borrowers to repay and suppliers to deposit when liquidity is scarce.
- `supplyRate = borrowRate * U * (1 - reserveFactor)`.
- Accrue interest with an index that grows with time and rate; compute balances from index ratios so accrual is O(1).
- Rate models are governance parameters: change them behind a timelock and simulate the effect on utilization first.

Illustrative parameters (not a protocol's): base 2%, slope1 4%, slope2 60%, kink 80%. This gives 6.0% at 80% utilization, 36% at 90% and 66% at 100%.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice Kink interest-rate model and health factor helpers. All rates and ratios use 1e18 (WAD).
library LendingMath {
    uint256 internal constant WAD = 1e18;

    struct RateParams {
        uint256 baseRate;      // borrow rate at 0% utilization (per year, WAD)
        uint256 slope1;        // added linearly up to the kink
        uint256 slope2;        // added linearly above the kink
        uint256 kink;          // optimal utilization (WAD), must be < WAD
    }

    function utilization(uint256 totalBorrows, uint256 cash) internal pure returns (uint256) {
        uint256 total = cash + totalBorrows;
        return total == 0 ? 0 : Math.mulDiv(totalBorrows, WAD, total);
    }

    function borrowRate(RateParams memory p, uint256 u) internal pure returns (uint256) {
        if (u <= p.kink) {
            return p.baseRate + Math.mulDiv(u, p.slope1, p.kink);
        }
        uint256 excess = Math.mulDiv(u - p.kink, WAD, WAD - p.kink);
        return p.baseRate + p.slope1 + Math.mulDiv(excess, p.slope2, WAD);
    }

    function supplyRate(uint256 borrowRate_, uint256 u, uint256 reserveFactor) internal pure returns (uint256) {
        return Math.mulDiv(Math.mulDiv(borrowRate_, u, WAD), WAD - reserveFactor, WAD);
    }

    /// @notice Position is liquidatable when the result is below WAD (1.0).
    function healthFactor(uint256 collateralValue, uint256 liquidationThreshold, uint256 debtValue)
        internal
        pure
        returns (uint256)
    {
        if (debtValue == 0) return type(uint256).max;
        return Math.mulDiv(Math.mulDiv(collateralValue, liquidationThreshold, WAD), WAD, debtValue);
    }
}
```

## Health factor and liquidation

- `healthFactor = collateralValue * liquidationThreshold / debtValue`. Below 1.0 the position can be liquidated.
- Example (hypothetical): collateral worth 10,000, threshold 0.80, debt 7,000 gives 1.143. A 12.5% collateral price drop gives exactly 1.0.
- The liquidation bonus pays the liquidator in collateral for repaying debt; it must exceed gas plus price risk during volatility, and stay small enough not to over-penalize users.
- Close factor: partial liquidation limits how much debt is repaid per call. Bound it, and document the exact rule the protocol uses.
- Bad debt occurs when collateral value falls below debt value before liquidation. Mitigations: conservative liquidation thresholds, supply and borrow caps, isolation of volatile or illiquid collateral, a reserve or safety module, and fast oracles.
- Liquidation must work during network congestion and oracle updates; keep the path cheap and permissionless.
- Self-liquidation, liquidation of dust positions and bonus rounding are common edge cases; fuzz them.

## Aave

- V3 (`@aave/core-v3` 1.19.3): `Pool` with aTokens and debt tokens, `supply`, `borrow`, `repay`, `withdraw`, `liquidationCall`, `flashLoan` and `flashLoanSimple`, supply and borrow caps, isolation mode, efficiency mode. Read `FLASHLOAN_PREMIUM_TOTAL()` from the pool for the current flash-loan fee instead of hard-coding it.
- V4: hub-and-spoke architecture (liquidity held in hubs, lending markets as spokes with their own collateral and risk settings); check the current Aave docs for its deployment status and interfaces. Integration interfaces differ from V3; confirm contracts and addresses in the current Aave documentation before integrating.
- Always fetch pool and reserve data from the protocol's data provider contracts rather than caching parameters.

## Flash loans

A flash loan lends any amount without collateral if it is repaid within the same transaction.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IPool} from "@aave/core-v3/contracts/interfaces/IPool.sol";

/// @notice Aave V3 simple flash-loan receiver. Verifies the caller and the initiator,
/// repays principal plus premium, and leaves no allowance behind.
contract FlashReceiver is Ownable {
    using SafeERC20 for IERC20;

    IPool public immutable pool;

    error NotPool();
    error NotInitiator();

    constructor(IPool pool_, address initialOwner) Ownable(initialOwner) {
        pool = pool_;
    }

    function borrow(address asset, uint256 amount, bytes calldata params) external onlyOwner {
        pool.flashLoanSimple(address(this), asset, amount, params, 0);
    }

    // Matches IFlashLoanSimpleReceiver.executeOperation.
    function executeOperation(address asset, uint256 amount, uint256 premium, address initiator, bytes calldata)
        external
        returns (bool)
    {
        if (msg.sender != address(pool)) revert NotPool();
        if (initiator != address(this)) revert NotInitiator();

        // ... use `amount` of `asset` here; revert if the strategy is not profitable ...

        IERC20(asset).forceApprove(address(pool), amount + premium);
        return true;
    }
}
```

- Verify `msg.sender` is the pool and `initiator` is this contract, otherwise anyone can trigger the callback.
- Repay `amount + premium` by approving the pool; revert the whole transaction if the strategy is unprofitable.
- Flash loans are also how attackers fund oracle pushes, vault donations and governance-vote attacks; design every invariant to hold against unlimited one-transaction capital.
- Other lenders (Uniswap v4 `unlock`, Balancer vault, others) have different callback shapes and fee rules; read their docs.

## ERC-4626 vaults

- Interface: `asset`, `totalAssets`, `convertToShares`, `convertToAssets`, `maxDeposit`, `maxMint`, `maxWithdraw`, `maxRedeem`, `previewDeposit`, `previewMint`, `previewWithdraw`, `previewRedeem`, `deposit`, `mint`, `withdraw`, `redeem` (EIP-4626).
- Rounding: conversions favor the vault. `deposit` and `redeem` round down what the user receives; `mint` and `withdraw` round up what the user pays.
- Inflation (donation) attack: the first depositor mints a tiny number of shares, then donates assets directly to the vault to inflate the share price so later deposits round to zero shares. OpenZeppelin 5.x mitigates this with virtual shares and assets in its conversions: shares are computed against `totalSupply() + 10 ** _decimalsOffset()` and `totalAssets() + 1`. Override `_decimalsOffset()` to a positive value; it also adds that many decimals to the share token. This makes the attack unprofitable but is not a substitute for seeding or minimum-deposit policies when the asset can be donated cheaply.
- `maxDeposit` and `maxMint` should reflect caps and pauses; withdrawals and redemptions should remain available whenever the underlying funds are.
- Underlying token constraints: plain ERC-20 behavior. Fee-on-transfer and rebasing assets break the accounting assumptions.
- Strategies that deploy assets elsewhere must value `totalAssets()` from trusted sources and handle illiquid withdrawals explicitly (queues or partial fills).
- Reentrancy: use a guard on deposit and withdraw paths; `ReentrancyGuardTransient` needs EIP-1153 support on the chain.
