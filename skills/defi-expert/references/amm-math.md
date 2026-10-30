# AMM Math and Swap Integration

Constant-product and concentrated-liquidity math, impermanent loss, Uniswap V3 and V4 notes, and a guarded swap contract. Solidity below compiles with solc 0.8.38 and OpenZeppelin Contracts 5.6.1. Pool sizes in the worked examples are hypothetical, not protocol data.

## Constant product (x * y = k)

- Reserves `x` (token in) and `y` (token out) keep `x * y = k` before fees. Spot price is `y / x`.
- Uniswap V2 takes the fee from the input: `amountInWithFee = amountIn * (10000 - feeBps)`, then `amountOut = amountInWithFee * y / (x * 10000 + amountInWithFee)`. V2 uses a 0.30% fee (30 bps).
- Round the output down and a required input up so the pool is never short.
- Price impact is the gap between the spot price and the execution price; it grows with `amountIn / x`.

Worked example (hypothetical pool: 2,000,000 USDC and 1,000 WETH, 30 bps fee). Swapping 1,000 USDC returns about 0.49825 WETH against 0.5 at spot, so execution is about 0.35% worse than spot (0.30% fee plus roughly 0.05% price impact).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice Constant-product (x * y = k) swap math with a proportional input fee.
library AmmMath {
    error InsufficientLiquidity();
    error InsufficientInput();

    /// @param feeBps swap fee in basis points (for example 30 = 0.30%)
    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut, uint256 feeBps)
        internal
        pure
        returns (uint256)
    {
        if (amountIn == 0) revert InsufficientInput();
        if (reserveIn == 0 || reserveOut == 0) revert InsufficientLiquidity();
        uint256 inWithFee = amountIn * (10_000 - feeBps);
        // rounds down: the pool never pays out more than the invariant allows
        return Math.mulDiv(inWithFee, reserveOut, reserveIn * 10_000 + inWithFee);
    }

    /// @notice Input needed for an exact output, rounded up in the pool's favor.
    function getAmountIn(uint256 amountOut, uint256 reserveIn, uint256 reserveOut, uint256 feeBps)
        internal
        pure
        returns (uint256)
    {
        if (reserveIn == 0 || reserveOut <= amountOut) revert InsufficientLiquidity();
        uint256 num = reserveIn * amountOut * 10_000;
        uint256 den = (reserveOut - amountOut) * (10_000 - feeBps);
        return Math.ceilDiv(num, den);
    }

    /// @notice Minimum acceptable output for a given quote and slippage budget.
    function minOut(uint256 quote, uint256 slippageBps) internal pure returns (uint256) {
        return Math.mulDiv(quote, 10_000 - slippageBps, 10_000);
    }
}
```

## Impermanent loss

For a constant-product position whose price ratio changes by factor `r` relative to entry, the value of the LP position relative to simply holding is `2 * sqrt(r) / (1 + r) - 1` (fees excluded). At `r = 2` (or 0.5) this is about -5.7%. Fees and incentives must exceed this over the holding period for the position to beat holding.

## Uniswap V3 (concentrated liquidity)

- A position provides liquidity between two ticks; it earns fees and is exposed to price only while the pool price is inside the range. Outside the range it is entirely one token.
- Capital efficiency is higher for narrow ranges and so is impermanent loss and rebalancing cost.
- Fee tiers are fixed at pool creation (commonly 0.01%, 0.05%, 0.30%, 1.00%); read the factory's enabled tiers on the target chain.
- Price is stored as `sqrtPriceX96`. `slot0` is the instantaneous price and must not be used as an oracle.
- TWAP: `observe(secondsAgo[])` returns cumulative ticks; the arithmetic mean tick over a window is `(tickCumulative1 - tickCumulative0) / window`. The pool needs sufficient observation cardinality (`increaseObservationCardinalityNext`). Manipulation cost rises with window length and pool liquidity.
- Swap routers: the original `SwapRouter` takes `deadline` in its params struct; `SwapRouter02` does not. Check the ABI of the router you call.

## Uniswap v4

- Live on Ethereum mainnet since January 2025 (`@uniswap/v4-core` 1.0.2, `@uniswap/v4-periphery` 1.0.3 on npm).
- One singleton `PoolManager` holds all pools; creating a pool is a state write, not a contract deployment. Pools are keyed by currencies, fee, tick spacing and hook address.
- Flash accounting: callers `unlock` the manager and settle net deltas at the end of the callback; intermediate token transfers are avoided.
- Native ETH can be a pool currency.
- Hooks: a hook contract gets callbacks around initialize, add and remove liquidity, swap and donate. Which callbacks run is determined by flag bits in the low bits of the hook's address, so the hook address is mined (`HookMiner` in v4-periphery) to match its declared permissions, and permissions cannot be changed after deployment.
- Hook security: only the `PoolManager` may call hook callbacks; a pool with your hook can be created by anyone unless `beforeInitialize` restricts it; hooks that take custody, adjust fees or return deltas hold user-fund-critical logic and need the same review as a vault.
- Fees can be static or dynamic (hook-controlled); read the pool key and hook before assuming a fee.

## Guarded swap contract

The router interface below is the original Uniswap V3 `SwapRouter` (deadline in the struct). The caller supplies `minOut` computed from an independent price and a slippage budget.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @dev Minimal view of the original Uniswap V3 SwapRouter (deadline lives in the params struct).
/// SwapRouter02 has a different struct; check the router you integrate with.
interface ISwapRouterV3 {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

/// @notice Swaps a caller's tokens with mandatory slippage and deadline bounds.
contract SwapExecutor is ReentrancyGuard {
    using SafeERC20 for IERC20;

    ISwapRouterV3 public immutable router;

    error Expired();
    error MinOutRequired();

    constructor(ISwapRouterV3 router_) {
        router = router_;
    }

    /// @param minOut Minimum output, computed off-chain from an independent price and a slippage budget.
    function swapExactIn(
        address tokenIn,
        address tokenOut,
        uint24 fee,
        uint256 amountIn,
        uint256 minOut,
        uint256 deadline
    ) external nonReentrant returns (uint256 amountOut) {
        if (block.timestamp > deadline) revert Expired();
        if (minOut == 0) revert MinOutRequired();

        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(router), amountIn);

        amountOut = router.exactInputSingle(
            ISwapRouterV3.ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: fee,
                recipient: msg.sender,
                deadline: deadline,
                amountIn: amountIn,
                amountOutMinimum: minOut,
                sqrtPriceLimitX96: 0
            })
        );

        IERC20(tokenIn).forceApprove(address(router), 0); // leave no standing allowance
    }
}
```

Off-chain, derive `minOut` with `AmmMath.minOut(quote, slippageBps)` semantics: `quote * (10000 - slippageBps) / 10000`, where `quote` comes from a quoter call or an oracle price, and refresh it if the transaction waits long.

## Further checks

- Multi-hop routes multiply impact and fees; compare against direct pools and aggregator quotes.
- Reject tokens whose received amount differs from the sent amount unless the code measures balance deltas.
- Sandwich exposure scales with trade size over liquidity and with the allowed slippage; see [oracles-mev.md](oracles-mev.md).
