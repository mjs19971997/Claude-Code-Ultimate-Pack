---
name: smart-contract-security-expert
description: >-
  Finds and fixes vulnerabilities in Solidity smart contracts: reentrancy, access control, upgradeable-proxy and initializer bugs, signature replay and malleability, oracle and price manipulation, ERC-20 and ERC-4626 edge cases, denial of service, MEV and front-running. Covers audit workflow, Slither, Aderyn, Foundry invariant tests, Echidna, Medusa, Halmos and Certora. Use when reviewing or hardening contracts, writing invariants, triaging analyzer output, preparing for an audit, or running a post-incident review. Not for writing contracts in general (use solidity-expert), DeFi protocol design (use defi-expert), Foundry or Hardhat project setup (use foundry-expert or hardhat-expert), DAO governance (use dao-expert), smart-account validation code (use account-abstraction-expert), or Solana programs (use solana-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Smart Contract Security Expert

This skill covers finding, exploiting (in tests) and fixing vulnerabilities in EVM smart contracts written in Solidity. It combines a manual review method with automated analysis (static analyzers, fuzzers, symbolic execution, formal verification) and a catalog of vulnerability classes with concrete fixes. Contracts are immutable or expensive to upgrade and hold value directly, so the emphasis is on preventing bugs by design and proving key properties with invariants.

> Verified against Solidity 0.8.38, OpenZeppelin Contracts 5.6.1 (npm `latest`) and 5.7.0 (GitHub latest release), Foundry 1.8.7 with forge-std, Slither 0.11.6, Echidna 2.3.3, Medusa 1.5.1, Aderyn 0.6.8, Halmos 0.3.3 and Certora CLI 8.20.3 (2026-10). All examples compile with solc 0.8.38 against OpenZeppelin 5.6.1 and 5.7.0.

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

- Covered: manual review method, vulnerability classes and fixes, OpenZeppelin 5.x secure building blocks, static analysis, fuzzing and invariant testing, symbolic execution, formal verification, audit preparation, incident response for deployed contracts.
- Not covered: general Solidity authoring, gas tuning and language features (solidity-expert); AMM, lending and oracle protocol design (defi-expert); Foundry and Hardhat project configuration (foundry-expert, hardhat-expert); Governor and timelock design (dao-expert); NFT standards (nft-expert); web2 API and application security (secure-coding-expert).

## 2. Core Expertise

| Class | Typical root cause | Primary fix |
|---|---|---|
| Reentrancy (single, cross-function, cross-contract, read-only) | External call before state update; view functions read mid-update state | Checks-effects-interactions, `ReentrancyGuard`, no trust in callbacks (ERC-777, ERC-721, ERC-1155 hooks, ERC-4626 receivers) |
| Access control | Missing or wrong modifier, unprotected initializer, `tx.origin` auth | `Ownable`/`AccessControl`, `Ownable2Step`, least privilege, timelocked admin |
| Upgradeability | Uninitialized implementation, storage collisions, unchecked `_authorizeUpgrade` | `_disableInitializers()`, ERC-7201 namespaced storage, upgrade-safety checks |
| Signatures | Replay across chain, contract or time; malleable signatures; missing nonce | EIP-712 domain, per-signer nonce, deadline, OZ `ECDSA`/`SignatureChecker` |
| Oracles and prices | Spot price from a pool, stale or zero feed answer, no L2 sequencer check | Validated Chainlink answers, TWAP with long window, circuit breakers |
| Token integration | Fee-on-transfer, rebasing, no-return `transfer`, blocklists, ERC-777 hooks | `SafeERC20`, balance-delta accounting, allowlist of supported tokens |
| ERC-4626 vaults | Donation or inflation attack on the first deposit, rounding in the user's favor | Virtual shares (built into OZ 5 ERC4626) plus a larger `_decimalsOffset()`, round against the caller |
| Math | Unsafe downcasts, rounding direction, `unchecked` blocks, precision loss | `SafeCast`, `Math.mulDiv`, explicit rounding, bounded `unchecked` |
| Denial of service | Unbounded loops, push payments, forced ETH via `selfdestruct` | Pull payments, pagination, never rely on `address(this).balance` for logic |
| MEV and ordering | Missing slippage or deadline, predictable commit data | Min-out and deadline parameters, commit-reveal, private order flow |
| Cross-chain | Message replay, missing sender check, chain-id assumptions | Verify origin and chain, nonce or message id, rate limits |

The SWC registry is no longer maintained, so this skill names issues instead of citing SWC ids. Signature malleability is SWC-117 in the old registry, and SWC-121 (missing protection against signature replay) is a different issue.

Full catalog with vulnerable and fixed snippets: [references/vulnerability-catalog.md](references/vulnerability-catalog.md). Tool usage and CI: [references/audit-tooling.md](references/audit-tooling.md).

## 3. Workflow

1. Scope: commit hash, in-scope files, trust assumptions, privileged roles, external dependencies, intended invariants. Read the docs and tests first.
2. Map the system: entry points, value flows (who can move which asset), external calls, upgrade and admin paths, oracle inputs.
3. Run Slither and Aderyn; read the findings critically and mark false positives with a reason.
4. Manual pass, function by function: who can call it, what state it reads and writes, what external calls it makes, what happens at zero, max, and repeated calls.
5. Write down invariants (solvency, conservation of value, monotonic counters, access rules) and encode them as Foundry invariant tests or Echidna and Medusa properties.
6. Fuzz and run symbolic tools on arithmetic-heavy and accounting code (Halmos); use Certora for properties that must hold for all inputs.
7. For each finding, write a failing test that demonstrates the exploit, apply the fix, and keep the test as a regression.
8. Re-review changed code; fixes introduce bugs. Record severity by impact and likelihood, with the exploit path.

## 4. Decision Rules

- Use `ReentrancyGuard` on every function that makes an external call and touches shared state, and still apply checks-effects-interactions. The guard does not protect read-only reentrancy for other contracts that read this contract's views.
- Prefer pull over push for payouts; a recipient that reverts must not block others.
- Use `Ownable2Step` or `AccessControlDefaultAdminRules` for admin roles; put sensitive actions behind a timelock and a multisig.
- Use a proxy only when upgradeability is a requirement; immutable contracts with migration are simpler to reason about. When upgradeable, use UUPS or transparent proxies from OZ 5 and validate upgrades with the OpenZeppelin upgrades plugins.
- Treat any price derived from an on-chain spot ratio (reserves, `balanceOf`) as attacker-controlled within one transaction.
- Integrate only tokens that are verified to behave; for arbitrary tokens, use `SafeERC20` and measure balance changes.
- Pick the tool by property type: static analyzers for known patterns, fuzzing for stateful invariants, Halmos or Certora for universally quantified properties.

## 5. Coding Standards

- Pin the compiler (`pragma solidity 0.8.38;` for deployed contracts, a `^0.8.24` range for libraries) and set `evm_version` explicitly; `ReentrancyGuardTransient` and the OZ 5 transient-storage helpers need the Cancun EVM.
- Use OpenZeppelin Contracts 5.x only; do not mix v4 import paths. In v5: `utils/ReentrancyGuard.sol`, `utils/Pausable.sol`, `Ownable(initialOwner)` takes the owner in the constructor. `PullPayment` and `Escrow` were removed in v5.
- Use custom errors, named mapping parameters and explicit visibility. Emit events for every state change that off-chain monitors need.
- Keep `unchecked` blocks tiny with a comment proving the bound.
- NatSpec on external functions: `@notice`, `@param`, `@return`; no author tags.

## 6. Project Structure

```text
src/                     contracts (interfaces/, libraries/, core/)
test/
  unit/                  per-function tests, revert reasons, access control
  invariant/             handlers + invariant_ tests (Foundry)
  fork/                  mainnet-fork integration against real tokens and oracles
  exploits/              one test per past finding (regression)
echidna/ or medusa.json  property contracts and fuzzer config
specs/                   Certora .spec/.conf, Halmos check_ tests
audit/                   scope, threat model, findings log
foundry.toml             solc, evm_version, [fuzz], [invariant] profiles
```

## 7. Design Patterns

- **Checks-effects-interactions**: validate, update state, then call out. Emit events before the external call so logs order matches state.
- **Pull payments**: record a credit, let the recipient withdraw. Replaces the removed OZ `PullPayment`.
- **Pausable with exit**: pause blocks inflows (`deposit`, `swap`); withdrawals stay available so a pause cannot trap funds.
- **Role separation**: distinct roles for upgrade, pause, parameter change and treasury; pauser can pause but not unpause or upgrade.
- **Rate limits and caps**: per-tx and per-window caps on mints, withdrawals and oracle moves limit blast radius.
- **Circuit breaker on oracle deviation**: revert or switch to a fallback when two sources disagree beyond a bound.
- **Namespaced storage (ERC-7201)** for upgradeable modules, so inherited layouts cannot collide.

## 8. Best Practices

- Write the invariants before the code under review: total assets >= total liabilities, shares and assets move together, only role X changes parameter Y.
- Model the adversary: arbitrary contract caller, flash loan capital, ordering control within a block, malicious token, malicious receiver.
- Check every external call target: does it return data, can it reenter, can it revert, can it consume all gas.
- Use balance-delta accounting for deposits of arbitrary ERC-20 tokens.
- Initialize every proxy in the same transaction as deployment and call `_disableInitializers()` in implementation constructors.
- Reduce privileged surface: renounce deployer roles, avoid `delegatecall` to user-supplied addresses, avoid `selfdestruct`.
- Document trust assumptions (oracle honest, admin multisig threshold) in the README so auditors test the right model.

## 9. Performance

Security-relevant trade-offs only:
- Gas griefing: unbounded loops over user-growable arrays can make functions uncallable; page or batch them.
- Fixed-gas `transfer` and `send` are not a reentrancy defense and break with contract recipients; use `Address.sendValue` with a guard and CEI.
- Cache storage reads in memory inside loops but keep state updates before external calls.
- Transient storage (`ReentrancyGuardTransient`) is cheaper than the storage guard, and requires an EVM with transient storage on every target chain.

## 10. Security

- Private keys: deployer and admin keys in hardware wallets or multisig (Safe); never in repo or CI secrets for mainnet.
- Admin actions: timelock plus event monitoring; emergency pause held by a faster, narrower role.
- Dependencies: pin OZ and other libraries by exact version and commit; review any copied code. Do not import `draft-` or unaudited contracts into production without review.
- Randomness: `block.prevrandao` and `block.timestamp` are influenceable; use a verifiable randomness oracle for value-bearing outcomes.
- `selfdestruct` after EIP-6780 only transfers ETH (code is removed only when called in the creation transaction), so forced ETH can still arrive.
- Hosted monitoring: MythX was discontinued and OpenZeppelin Defender's hosted service was announced to shut down on 1 July 2026; use the open source OpenZeppelin Relayer and Monitor, or a maintained alternative, for runtime alerts.

## 11. Testing

- Unit tests for every revert path and every role; fuzz tests for arithmetic and boundary inputs.
- Invariant tests with handlers: bounded actions on a fixed actor set, ghost variables for accounting, `targetContract` and `targetSelector` restricted to the handler. See [references/audit-tooling.md](references/audit-tooling.md) for a full handler example.
- Fork tests against real tokens (USDT-style no-return, fee-on-transfer) and real oracles.
- Exploit tests that reproduce each finding before the fix.
- Mutation testing (for example `gambit` or `vertigo-rs`) on critical modules to check the tests actually fail when logic breaks; check each tool's current status first.
- Symbolic: Halmos `check_*` tests for pure math; Certora CVL rules and invariants for protocol-level properties.

## 12. Review Checklist

- [ ] Every external or public function has the right access control and is reachable only as intended.
- [ ] State is updated before every external call; `nonReentrant` where shared state is involved; views used by other protocols are consistent mid-call.
- [ ] Initializers: protected, called once, implementation locked; storage layout checked on upgrade.
- [ ] Signatures bind chain id, contract, signer nonce and deadline (EIP-712); OZ `ECDSA` used, `ecrecover` result never compared to zero by hand.
- [ ] Oracle reads validate sign, freshness, and (on L2) sequencer uptime; no spot prices for valuation.
- [ ] Token transfers use `SafeERC20`; accounting uses balance deltas for arbitrary tokens.
- [ ] Rounding favors the protocol; downcasts use `SafeCast`; `unchecked` blocks justified.
- [ ] No unbounded loops or push payments to untrusted addresses.
- [ ] Slippage, deadline and min-out parameters on every swap-like function.
- [ ] Invariants written and fuzzed; Slither and Aderyn findings triaged.
- [ ] Admin keys behind multisig and timelock; deployer roles renounced.

## 13. Production Notes

- Pre-deploy: freeze the commit, run the full test and invariant suite on a fork, verify bytecode on the block explorer, and confirm constructor arguments and role assignments by script.
- Staged launch: deposit caps and allowlists first; raise limits after a clean period.
- Monitoring: alert on role changes, upgrades, pause events, large transfers and oracle deviations (OpenZeppelin Monitor or an equivalent maintained tool).
- Bug bounty and disclosure policy before launch; a tested incident runbook (who pauses, who communicates, how funds are recovered).
- After an incident: root cause, regression test, and a check of all other deployments of the same code.

## 14. Examples

All three compile with solc 0.8.38 and OpenZeppelin Contracts 5.x. An invariant test for the first one is in [references/audit-tooling.md](references/audit-tooling.md).

### Example 1: ETH vault with CEI and ReentrancyGuard (OZ 5 paths)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Address} from "@openzeppelin/contracts/utils/Address.sol";

/// @title EthVault
/// @notice Per-account ETH balances. Checks-effects-interactions plus a reentrancy guard.
contract EthVault is Ownable, Pausable, ReentrancyGuard {
    mapping(address account => uint256 amount) public balanceOf;
    uint256 public totalDeposits;

    event Deposited(address indexed account, uint256 amount);
    event Withdrawn(address indexed account, address indexed to, uint256 amount);

    error ZeroAmount();
    error InsufficientBalance(uint256 available, uint256 requested);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function deposit() external payable whenNotPaused {
        if (msg.value == 0) revert ZeroAmount();
        balanceOf[msg.sender] += msg.value;
        totalDeposits += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw(address payable to, uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        uint256 available = balanceOf[msg.sender];
        if (amount > available) revert InsufficientBalance(available, amount);

        // Effects before the external call.
        balanceOf[msg.sender] = available - amount;
        totalDeposits -= amount;
        emit Withdrawn(msg.sender, to, amount);

        // Interaction last; reverts bubble up from Address.sendValue.
        Address.sendValue(to, amount);
    }

    /// @dev Pausing blocks deposits only; users can always withdraw.
    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
```

### Example 2: Validated price feed read

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @dev Subset of Chainlink's AggregatorV3Interface (same selectors).
interface IAggregatorV3 {
    function decimals() external view returns (uint8);

    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

/// @title PriceFeedReader
/// @notice Reads one feed and rejects stale, non-positive or incomplete answers.
contract PriceFeedReader {
    IAggregatorV3 public immutable FEED;
    uint256 public immutable MAX_AGE; // seconds; set at or slightly above the feed heartbeat

    error InvalidConfig();
    error InvalidPrice(int256 answer);
    error StalePrice(uint256 updatedAt, uint256 maxAge);

    constructor(IAggregatorV3 feed, uint256 maxAge) {
        if (address(feed) == address(0) || maxAge == 0) revert InvalidConfig();
        FEED = feed;
        MAX_AGE = maxAge;
    }

    /// @return price Answer scaled to 18 decimals.
    function price18() external view returns (uint256 price) {
        (, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        if (answer <= 0) revert InvalidPrice(answer);
        if (updatedAt == 0 || block.timestamp - updatedAt > MAX_AGE) revert StalePrice(updatedAt, MAX_AGE);

        uint8 d = FEED.decimals();
        price = d <= 18 ? uint256(answer) * 10 ** (18 - d) : uint256(answer) / 10 ** (d - 18);
    }
}
```

### Example 3: Signed withdrawals (EIP-712, nonce, deadline, EIP-1271)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title SignedWithdrawals
/// @notice Token custody where a depositor can authorize a withdrawal to any address with an
/// EIP-712 signature (for example, so a relayer pays the gas). The signed data binds token,
/// recipient, amount, nonce and deadline; the domain binds chain id and this contract's address.
contract SignedWithdrawals is EIP712, Nonces {
    using SafeERC20 for IERC20;

    bytes32 private constant WITHDRAW_TYPEHASH =
        keccak256("Withdraw(address token,address to,uint256 amount,uint256 nonce,uint256 deadline)");

    mapping(address account => mapping(IERC20 token => uint256 amount)) public balanceOf;

    error Expired(uint256 deadline);
    error InvalidSignature();
    error InsufficientBalance(uint256 available, uint256 requested);

    constructor() EIP712("SignedWithdrawals", "1") {}

    function deposit(IERC20 token, uint256 amount) external {
        uint256 before = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), amount);
        // Credit what actually arrived (fee-on-transfer tokens deliver less than `amount`).
        balanceOf[msg.sender][token] += token.balanceOf(address(this)) - before;
    }

    function withdrawBySig(
        address signer,
        IERC20 token,
        address to,
        uint256 amount,
        uint256 deadline,
        bytes calldata signature
    ) external {
        if (block.timestamp > deadline) revert Expired(deadline);

        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(WITHDRAW_TYPEHASH, address(token), to, amount, _useNonce(signer), deadline))
        );
        // OZ ECDSA rejects malleable (high-s) signatures; EIP-1271 contract wallets are supported.
        if (!SignatureChecker.isValidSignatureNow(signer, digest, signature)) revert InvalidSignature();

        uint256 available = balanceOf[signer][token];
        if (amount > available) revert InsufficientBalance(available, amount);
        balanceOf[signer][token] = available - amount;

        token.safeTransfer(to, amount);
    }
}
```

## 15. Common Mistakes

- Importing OZ v4 paths (`security/ReentrancyGuard.sol`, `security/Pausable.sol`) into a v5 project, or constructing `Ownable()` without an owner argument.
- Importing `PullPayment` or `Escrow`; they no longer exist in v5.
- Using `transfer` or `send` as reentrancy protection.
- Valuing collateral with `pool.getReserves()` or `token.balanceOf(pool)` spot ratios.
- Reading `latestRoundData()` without checking `answer > 0` and `updatedAt` freshness.
- Verifying a signature without a nonce, deadline or domain separator; hand-rolling `ecrecover` and accepting high-s signatures or the zero address.
- Leaving an upgradeable implementation uninitialized, or reordering inherited storage across upgrades.
- Trusting `msg.sender.code.length == 0` to exclude contracts (true during construction).
- Assuming `address(this).balance == totalDeposits`; anyone can force-send ETH.
- Not handling tokens that return nothing, charge fees or rebase.
- Making a pause block withdrawals, so a compromised pauser can freeze all funds.
- Treating a clean Slither run as proof of safety; static analysis finds patterns, not logic flaws.

## 16. References

- [references/vulnerability-catalog.md](references/vulnerability-catalog.md): vulnerability classes with vulnerable and fixed snippets (reentrancy variants, proxies, signatures, oracles, ERC-4626, tokens, DoS, MEV).
- [references/audit-tooling.md](references/audit-tooling.md): Slither, Aderyn, Foundry invariants with a handler example, Echidna, Medusa, Halmos, Certora, CI wiring, current tool status.
- Solidity security considerations: https://docs.soliditylang.org/en/latest/security-considerations.html
- OpenZeppelin Contracts 5.x docs: https://docs.openzeppelin.com/contracts/5.x/
- Ethereum smart contract security best practices (Consensys Diligence): https://consensysdiligence.github.io/smart-contract-best-practices/
