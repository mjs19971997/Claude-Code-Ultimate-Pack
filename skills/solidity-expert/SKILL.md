---
name: solidity-expert
description: >-
  Writes and reviews production Solidity 0.8.x smart contracts, including OpenZeppelin Contracts 5.x (ERC20, ERC721, ERC1155, ERC4626, AccessControl, AccessManager, Governor, upgradeable proxies): custom errors, pragma and EVM version choice, storage layout and ERC-7201 namespaced storage, UUPS upgrades, gas optimization, and Foundry tests. Use when working with .sol files, pragma solidity, solc settings, Ownable, ReentrancyGuard, SafeERC20, Initializable, UUPSUpgradeable, TimelockController, storage collisions, or contract size and gas problems. Not for exploit and audit methodology (use smart-contract-security-expert), Foundry or Hardhat project tooling (use foundry-expert, hardhat-expert), off-chain clients (use ethersjs-expert), or ERC-4337 and EIP-7702 account code (use account-abstraction-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Solidity Expert

This skill covers writing Solidity contracts that are small, explicit and safe to upgrade or keep immutable: language features of 0.8.x, compiler and EVM settings, storage layout, access control, token and governance building blocks from OpenZeppelin Contracts 5.x, gas costs, and tests. It absorbs the former openzeppelin-expert skill; OpenZeppelin details live in a dedicated reference file. Audit techniques, DeFi protocol design and tooling configuration are left to neighbouring skills.

> Verified against Solidity 0.8.38 (released 2026-10-22, default EVM version osaka), OpenZeppelin Contracts and Contracts Upgradeable 5.7.0, forge-std master (2026-10).

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

- Covered: Solidity language and compiler settings, custom errors, events, inheritance, libraries, inline assembly basics, storage layout, proxies and upgrade safety, OpenZeppelin Contracts 5.x usage, gas costs, unit, fuzz and invariant tests with Foundry, verification and deployment hygiene.
- Not covered: attack catalogues and audit process (smart-contract-security-expert); Foundry or Hardhat configuration and scripting (foundry-expert, hardhat-expert); client libraries (ethersjs-expert, web3js-expert); protocol design for DeFi, DAOs and NFTs (defi-expert, dao-expert, nft-expert).

## 2. Core Expertise

- **Compiler**: 0.8.x has checked arithmetic by default (`unchecked { }` opts out), custom errors (0.8.4), `abi.encodeCall` (0.8.11), `using ... for ... global` (0.8.13), named mapping parameters (0.8.18), `transient` state variables of value types (0.8.28), `layout at <slot>` custom storage layout (0.8.29), `erc7201("id")` builtin (0.8.35). The default EVM version is `osaka` since 0.8.31; set `evm_version` to what the target chain supports.
- **Deprecations in 0.8.31**: `address.send` and `address.transfer`, virtual modifiers, ABI coder v1, the `memory-safe-assembly` comment (use `assembly ("memory-safe") { }`). Avoid all of them in new code.
- **Types and locations**: value types, `bytesN`, `string` and `bytes`, structs, mappings, enums, user-defined value types; `storage`, `memory`, `calldata`, `transient`. Prefer `calldata` for read-only external arguments.
- **Errors**: `revert CustomError(args)` ABI-encodes a 4-byte selector plus arguments. `require(cond, "text")` reverts with `Error(string)` (selector 0x08c379a0); failed `assert` and arithmetic checks revert with `Panic(uint256)` (selector 0x4e487b71). `require(cond, CustomError(args))` works from 0.8.27 in the legacy pipeline and 0.8.26 with via-IR.
- **Calls**: `call`, `staticcall`, `delegatecall` return `(bool, bytes)` and must be checked; `try/catch` handles external calls only. Use `Address.sendValue` or a checked `call{value:}` for ETH, never `transfer`.
- **Storage**: sequential slots by declaration order, packing of adjacent small types, mappings and dynamic arrays located by `keccak256`, ERC-1967 proxy slots, ERC-7201 namespaced layouts. See [storage and upgrades](references/storage-and-upgrades.md).
- **Opcodes that changed**: `selfdestruct` only deletes the account when called in the creating transaction (EIP-6780); `block.prevrandao` replaced `difficulty`; transient storage `TLOAD`/`TSTORE` (EIP-1153) costs 100 gas each; code size limit 24,576 bytes (EIP-170), initcode limit 49,152 bytes (EIP-3860).
- **OpenZeppelin Contracts 5.x**: tokens, access control, `AccessManager`, governance, proxies, cryptography and utilities. See [OpenZeppelin](references/openzeppelin.md).

## 3. Workflow

1. Pin the toolchain: exact compiler, `evm_version`, optimizer runs, OpenZeppelin version. Record them in `foundry.toml` or `hardhat.config`.
2. Model the system before coding: actors, privileged roles, funds flows, what must never happen (invariants). Decide upgradeable or immutable now; it changes the storage and constructor rules.
3. Reuse OpenZeppelin for tokens, access control, pausing, signatures, math and proxies instead of rewriting them.
4. Write the interface and events first, then storage, then external functions with checks, effects and interactions in that order.
5. Write unit tests, fuzz tests for arithmetic and accounting, and invariant tests for protocol properties. Run `forge fmt` and a static analyzer (Slither).
6. Measure gas with `forge test --gas-report` and `forge snapshot`; optimize only measured hot paths.
7. For upgradeable contracts, diff the storage layout (`forge inspect <Contract> storage-layout`) against the deployed version.
8. Deploy from a script, verify source on a block explorer or Sourcify, hand roles to a multisig or timelock, and keep deployment addresses and constructor arguments in the repo.

## 4. Decision Rules

| Question | Choose | Why |
|---|---|---|
| Pragma for a deployable contract | Exact: `pragma solidity 0.8.38;` | A caret range is floating: the compiler used can differ from the one tested |
| Pragma for a library or shared package | Caret or range, such as `^0.8.24` or `>=0.8.24 <0.9.0` | Consumers pick the compiler; test on the lowest and highest supported |
| Error reporting | Custom errors with parameters | Cheaper deployment and runtime than strings, structured data for clients |
| Constructor-set value that never changes | `immutable`; literal values `constant` | Stored in code, no SLOAD |
| Sending ETH | `call` with a checked result, or `Address.sendValue` | `transfer`/`send` forward 2300 gas and are deprecated |
| Admin model | `Ownable2Step` for one admin; `AccessControl` for several roles; `AccessManager` for many contracts and delays | Match governance needs; see the OpenZeppelin reference |
| Upgradeability | Immutable unless there is a concrete reason; then UUPS or Transparent | Upgrades add trust and storage risk |
| Reentrancy defense | Checks-effects-interactions first, `ReentrancyGuard` as backup | The guard does not fix cross-contract or read-only reentrancy |
| Token transfers | `SafeERC20` | Handles tokens that return no value |
| Gas vs readability | Readability, unless a profile shows the cost | Unmeasured tricks hide bugs |
| Compiler pipeline | Legacy by default; `via_ir` when stack-too-deep or optimizer gains justify slower builds | Test with the exact settings you deploy |

## 5. Coding Standards

- Layout order: SPDX line, pragma, imports, errors, events, types, state variables, modifiers, constructor, external, public, internal, private functions. Functions inside a group go state-changing first, then `view`, then `pure`.
- Naming: `PascalCase` contracts and structs, `camelCase` functions and variables, `UPPER_SNAKE_CASE` constants and immutables, `_leadingUnderscore` for internal and private functions and variables, trailing underscore for constructor params that shadow state (`asset_`).
- Use named imports (`import {Ownable} from "..."`), never bare `import "file.sol"`.
- Use named mapping parameters: `mapping(address account => uint256 amount)`.
- Explicit visibility and mutability everywhere; `external` for functions not called internally.
- NatSpec (`@notice`, `@dev`, `@param`, `@return`) on every external function; leave out author tags.
- Add a SPDX identifier to every file; format with `forge fmt`.
- Keep inline assembly small, mark it `("memory-safe")` only when it is, and comment the invariant it relies on.
- Check zero addresses and zero amounts at trust boundaries, not on every internal helper.

## 6. Project Structure

```text
src/
  interfaces/        IVault.sol
  libraries/         Math helpers, pure logic
  Vault.sol
  VaultV2.sol        # next upgrade, with @custom:oz-upgrades-from
test/
  Vault.t.sol        # unit and fuzz tests
  invariant/         # handlers and invariants
  mocks/             # test-only tokens and callers
script/
  Deploy.s.sol
foundry.toml
remappings.txt       # or rely on lib/ and soldeer; keep one dependency source
```

## 7. Design Patterns

- **Checks-effects-interactions**: validate, update storage, then call out. Emit events after state changes.
- **Pull over push**: record what each account may claim and let it withdraw, instead of looping over recipients.
- **Pausable with open exits**: pause deposits and risky actions; keep withdrawals available so a pause cannot trap funds.
- **Two-step ownership**: `Ownable2Step` prevents transferring ownership to a wrong address.
- **Role separation**: distinct roles for minting, pausing and upgrading, each held by a different account behind a timelock.
- **Factory with deterministic addresses**: `Create2` or minimal proxies (`Clones`) for many identical instances; initialize in the same transaction.
- **Namespaced storage (ERC-7201)**: each module keeps its state in a struct at a hashed slot, so inheritance changes do not shift layouts.
- **Commit-reveal and signatures**: EIP-712 typed data with `EIP712` and `ECDSA`, with a per-signer nonce and a deadline.

## 8. Best Practices

- Keep contracts small and composable; extract logic into internal functions or libraries and keep external functions thin.
- Emit an event for every state change that off-chain code needs; index at most three fields.
- Use interfaces and `IERC20` types in signatures rather than raw `address` where the type is known.
- Prefer `uint256` for storage and arithmetic unless packing is a measured win; use `SafeCast` when narrowing.
- Avoid unbounded loops over user-controlled arrays; paginate or use pull payments.
- Do not rely on `block.timestamp` for sub-minute precision or on `address(this).balance` for accounting (ETH can be forced in).
- Do not depend on code size or `extcodesize` to detect EOAs; delegated EOAs (EIP-7702) have code.
- Document trust assumptions: who can pause, upgrade, mint, and with what delay.
- Prefer battle-tested OpenZeppelin code over copy-pasted snippets; import by package path and pin the version.

## 9. Performance

- Storage is the dominant cost. Cold `SLOAD` is 2100 gas, warm `SLOAD` 100 (EIP-2929); a cold account access (`CALL`, `BALANCE`, `EXTCODESIZE`) is 2600; writing a zero slot to nonzero costs 20,000 plus the cold surcharge.
- Cache storage reads in locals when used more than once; write back once.
- Pack related small fields into one slot only when they are read and written together.
- Use `immutable`, `constant`, `calldata`, custom errors, and `unchecked` only where bounds are proven in the same function.
- Use transient storage (`transient` state variables, or `ReentrancyGuardTransient`) for per-transaction flags; it requires an EVM version with Cancun or later.
- Avoid on-chain enumeration (`ERC721Enumerable`) unless needed; index with events.
- Optimizer runs trade deployment size against runtime cost; tune by measuring. See [gas optimization](references/gas-optimization.md).

## 10. Security

- Apply checks-effects-interactions and `nonReentrant` to every function that moves value or calls untrusted code.
- Authenticate with `msg.sender`, never `tx.origin`.
- Treat any external call, token callback (ERC-777, ERC-721 `onERC721Received`, ERC-1155 receivers) and `delegatecall` target as hostile.
- Validate signatures with `ECDSA` or `SignatureChecker`; include chain id, contract address, nonce and deadline in the signed data (`EIP712` does this).
- Guard share-based vaults against inflation attacks (virtual offset via `_decimalsOffset()` in `ERC4626`) and read prices from sources that cannot be moved in one transaction.
- Never put secrets or private data in storage; everything on chain is readable.
- Initialize every proxy in the deploy transaction; call `_disableInitializers()` in implementation constructors.
- Use a multisig plus `TimelockController` or `AccessManager` delays for upgrades and parameter changes.
- Run Slither and fuzz/invariant tests before review; get an external audit before holding user funds. Use smart-contract-security-expert for attack patterns.

## 11. Testing

- Foundry layout: `test/*.t.sol` inheriting `forge-std/Test.sol`; names `test_Thing`, `testFuzz_Thing`, `invariant_Thing`.
- Expect custom errors with `vm.expectRevert(abi.encodeWithSelector(Err.selector, args))` or `vm.expectRevert(Err.selector)`.
- Use `bound` for fuzz inputs, `vm.prank`/`vm.startPrank` for callers, `makeAddr` for labelled addresses, `vm.warp`/`vm.roll` for time.
- Invariant tests: a handler contract exposes bounded actions; assert conservation properties (sum of balances equals total assets).
- Fork tests (`vm.createSelectFork`) for integrations with real tokens; pin the block number.
- Upgrade tests: deploy V1 behind a proxy, write state, upgrade to V2, assert state is intact and new logic works.
- Commands: `forge test -vvv`, `forge test --match-test`, `forge coverage`, `forge test --gas-report`, `forge inspect <Contract> storage-layout`.

## 12. Review Checklist

- [ ] Exact pragma and pinned `evm_version` for deployables; dependencies pinned.
- [ ] No `tx.origin`, `transfer`/`send`, unchecked low-level call results, or unbounded loops.
- [ ] External calls follow checks-effects-interactions; reentrancy guard where value moves.
- [ ] Every privileged function has an explicit role and an event.
- [ ] Custom errors and events cover all state changes and failures.
- [ ] `SafeERC20` for token transfers; balance-delta accounting if fee-on-transfer tokens are possible.
- [ ] Upgradeable: `_disableInitializers()`, initializer called at deploy, namespaced storage or preserved layout, `_authorizeUpgrade` restricted.
- [ ] Unit, fuzz and invariant tests pass; storage layout diff clean; gas report reviewed.
- [ ] Contract size under 24,576 bytes; constructor arguments and roles verified.

## 13. Production Notes

- Verify source on the explorer or Sourcify using the exact compiler version, settings and metadata; keep the standard JSON input.
- Deploy from a script, not by hand; prefer a hardware-wallet or multisig deployer and transfer admin roles in the same script.
- Confirm `evm_version` against each target chain before deploying; L2s and sidechains can lag mainnet opcodes.
- Check the Solidity security advisories and bug list for your compiler version (soliditylang.org). Release 0.8.34 fixed an IR-pipeline bug that could clear a regular storage variable instead of a transient one at the same layout position, and 0.8.32 fixed array clearing and copying for arrays that straddle the end of storage; prefer 0.8.34 or later.
- Keep an emergency plan: pausing, role revocation, and who signs.
- Use CREATE2 only when the address must be predictable; remember `selfdestruct` no longer enables redeploy patterns.

## 14. Examples

### Example 1: ERC-20 vault with SafeERC20, custom errors and open exits

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable, Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @notice Single-asset vault. Deposits are credited by the amount actually received,
///         so fee-on-transfer tokens cannot inflate balances.
contract TokenVault is Ownable2Step, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    error ZeroAmount();
    error InsufficientBalance(uint256 available, uint256 requested);

    event Deposited(address indexed account, uint256 amount);
    event Withdrawn(address indexed account, uint256 amount);

    IERC20 public immutable ASSET;
    mapping(address account => uint256 amount) public balanceOf;

    constructor(IERC20 asset_, address initialOwner) Ownable(initialOwner) {
        ASSET = asset_;
    }

    function deposit(uint256 amount) external whenNotPaused nonReentrant {
        if (amount == 0) revert ZeroAmount();
        uint256 before = ASSET.balanceOf(address(this));
        ASSET.safeTransferFrom(msg.sender, address(this), amount);
        uint256 received = ASSET.balanceOf(address(this)) - before;
        balanceOf[msg.sender] += received;
        emit Deposited(msg.sender, received);
    }

    /// @dev Withdrawals stay open while paused so a pause never traps funds.
    function withdraw(uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        uint256 available = balanceOf[msg.sender];
        if (amount > available) revert InsufficientBalance(available, amount);
        balanceOf[msg.sender] = available - amount; // effect before interaction
        ASSET.safeTransfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
```

### Example 2: Foundry fuzz and revert tests for the vault

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {TokenVault} from "../src/TokenVault.sol";

contract MockToken is ERC20 {
    constructor() ERC20("Mock", "MCK") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract TokenVaultTest is Test {
    TokenVault vault;
    MockToken token;
    address owner = makeAddr("owner");
    address alice = makeAddr("alice");

    function setUp() public {
        token = new MockToken();
        vault = new TokenVault(IERC20(address(token)), owner);
    }

    function testFuzz_depositThenWithdraw(uint96 amount) public {
        amount = uint96(bound(amount, 1, type(uint96).max));
        token.mint(alice, amount);

        vm.startPrank(alice);
        token.approve(address(vault), amount);
        vault.deposit(amount);
        assertEq(vault.balanceOf(alice), amount);
        vault.withdraw(amount);
        vm.stopPrank();

        assertEq(token.balanceOf(alice), amount);
    }

    function test_withdrawMoreThanBalanceReverts() public {
        vm.expectRevert(abi.encodeWithSelector(TokenVault.InsufficientBalance.selector, 0, 1));
        vm.prank(alice);
        vault.withdraw(1);
    }

    function test_onlyOwnerCanPause() public {
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, alice));
        vm.prank(alice);
        vault.pause();
    }
}
```

### Example 3: UUPS upgradeable contract with ERC-7201 namespaced storage

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Initializable} from "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts/proxy/utils/UUPSUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

contract Registry is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    /// @custom:storage-location erc7201:example.storage.Registry
    struct RegistryStorage {
        mapping(bytes32 key => bytes32 value) entries;
        uint256 count;
    }

    // keccak256(abi.encode(uint256(keccak256("example.storage.Registry")) - 1)) & ~bytes32(uint256(0xff))
    bytes32 private constant REGISTRY_STORAGE_LOCATION =
        0x9059e8fd9c5070bf26463002743d587936571e76c7911ed0ac60ce4e404c5200;

    event EntrySet(bytes32 indexed key, bytes32 value);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address initialOwner) external initializer {
        __Ownable_init(initialOwner);
    }

    function set(bytes32 key, bytes32 value) external onlyOwner {
        RegistryStorage storage $ = _getRegistryStorage();
        if ($.entries[key] == bytes32(0)) ++$.count;
        $.entries[key] = value;
        emit EntrySet(key, value);
    }

    function get(bytes32 key) external view returns (bytes32) {
        return _getRegistryStorage().entries[key];
    }

    function _getRegistryStorage() private pure returns (RegistryStorage storage $) {
        assembly {
            $.slot := REGISTRY_STORAGE_LOCATION
        }
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}
```

Deploy behind `ERC1967Proxy(implementation, abi.encodeCall(Registry.initialize, (owner)))` so initialization happens in the same transaction. `Initializable` and `UUPSUpgradeable` are imported from the main package because the aliases in `contracts-upgradeable` are scheduled for removal.

## 15. Common Mistakes

- **Caret pragma treated as pinned**: `^0.8.20` accepts any 0.8.x at or above 0.8.20, so it floats. Pin deployables to one version; reserve ranges for libraries.
- **Calling `transfer` or `send` for ETH**: a recipient contract that needs more than 2300 gas reverts. Use a checked `call` or `Address.sendValue`, and keep state updates before it.
- **Ignoring a low-level call result**: `(bool ok, ) = to.call(...)` without `if (!ok) revert`.
- **Reordering or inserting state variables in an upgrade**: slots shift and data is read as the wrong variable. Append only, or use ERC-7201 namespaces; check `forge inspect` diffs.
- **Leaving an implementation uninitialized**: anyone can initialize it and, for UUPS, call `upgradeToAndCall` on it. Call `_disableInitializers()` in the constructor.
- **Mixing OpenZeppelin v4 and v5 APIs**: `Ownable()` without arguments, `security/ReentrancyGuard.sol`, `Counters`, `SafeMath`, `_beforeTokenTransfer` and `_afterTokenTransfer` do not exist in v5. See the reference for the v5 equivalents.
- **Fee-on-transfer and rebasing tokens**: crediting the requested amount instead of the received amount.
- **Using `tx.origin`, `block.timestamp` randomness, or spot DEX prices** as security inputs.
- **Gas micro-optimizing before measuring**: removing checks or packing slots that are never hot.
- **Granting `DEFAULT_ADMIN_ROLE` to the deployer EOA permanently**: transfer it to a multisig or timelock and renounce the deployer's role.
- **Unbounded loops over user-supplied arrays**: a large input makes the function uncallable. Cap the length or paginate.

## 16. References

- [references/openzeppelin.md](references/openzeppelin.md): OpenZeppelin Contracts 5.x import paths, v4 to v5 changes, tokens, access control, AccessManager, Governor, proxies, utilities.
- [references/storage-and-upgrades.md](references/storage-and-upgrades.md): slot layout rules, ERC-7201, ERC-1967, UUPS vs Transparent vs Beacon, initializers, upgrade safety checks and tooling.
- [references/gas-optimization.md](references/gas-optimization.md): gas cost table, storage and calldata techniques, transient storage, optimizer settings and measurement.
- Solidity documentation: https://docs.soliditylang.org
- Solidity releases and changelog: https://github.com/ethereum/solidity/releases
- OpenZeppelin Contracts documentation: https://docs.openzeppelin.com/contracts
- ERC-7201: https://eips.ethereum.org/EIPS/eip-7201
- Foundry book: https://book.getfoundry.sh
