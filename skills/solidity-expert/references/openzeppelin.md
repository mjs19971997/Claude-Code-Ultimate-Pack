# OpenZeppelin Contracts 5.x Reference

Applies to OpenZeppelin Contracts and Contracts Upgradeable 5.x (5.7.0 verified 2026-10; 5.6.1 is the previous patch line). Only v5 APIs are listed. Release notes: https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/CHANGELOG.md. Docs: https://docs.openzeppelin.com/contracts.

## Contents
- [Install and pin](#install-and-pin)
- [Import paths](#import-paths)
- [Changes from v4](#changes-from-v4)
- [Tokens](#tokens)
- [Access control](#access-control)
- [AccessManager](#accessmanager)
- [Governance](#governance)
- [Proxies and upgradeable contracts](#proxies-and-upgradeable-contracts)
- [Utilities and cryptography](#utilities-and-cryptography)
- [Pitfalls](#pitfalls)

## Install and pin

```text
npm install @openzeppelin/contracts@5.7.0
npm install @openzeppelin/contracts-upgradeable@5.7.0      # only for proxy-based contracts
forge install OpenZeppelin/openzeppelin-contracts@v5.7.0   # Foundry
forge install OpenZeppelin/openzeppelin-contracts-upgradeable@v5.7.0
```

Keep both packages on the same version. Foundry remappings: `@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/` and `@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/`.

Minimum pragma per file differs: most files are `^0.8.20`, `UUPSUpgradeable` is `^0.8.22`, and `ERC20Votes`, `ERC4626`, the ERC721 and ERC1155 families, `Governor` and `ReentrancyGuardTransient` are `^0.8.24`. Transient-storage contracts need an EVM version with Cancun or later. An exact application pragma such as `pragma solidity 0.8.38;` satisfies all of them.

## Import paths

| Contract | Path under `@openzeppelin/contracts/` |
|---|---|
| `Ownable`, `Ownable2Step` | `access/Ownable.sol`, `access/Ownable2Step.sol` |
| `AccessControl`, `AccessControlEnumerable`, `AccessControlDefaultAdminRules` | `access/AccessControl.sol`, `access/extensions/AccessControlEnumerable.sol`, `access/extensions/AccessControlDefaultAdminRules.sol` |
| `AccessManager`, `AccessManaged` | `access/manager/AccessManager.sol`, `access/manager/AccessManaged.sol` |
| `ReentrancyGuard`, `ReentrancyGuardTransient` | `utils/ReentrancyGuard.sol`, `utils/ReentrancyGuardTransient.sol` |
| `Pausable` | `utils/Pausable.sol` |
| `ERC20`, `IERC20`, `SafeERC20` | `token/ERC20/ERC20.sol`, `token/ERC20/IERC20.sol`, `token/ERC20/utils/SafeERC20.sol` |
| ERC20 extensions (`ERC20Permit`, `ERC20Votes`, `ERC20Burnable`, `ERC20Capped`, `ERC20Pausable`, `ERC20FlashMint`, `ERC20Wrapper`, `ERC4626`) | `token/ERC20/extensions/<Name>.sol` |
| `ERC721` and extensions (`ERC721URIStorage`, `ERC721Enumerable`, `ERC721Burnable`, `ERC721Royalty`, `ERC721Consecutive`, `ERC721Votes`) | `token/ERC721/ERC721.sol`, `token/ERC721/extensions/<Name>.sol` |
| `ERC1155`, `ERC1155Supply`, `ERC1155Burnable` | `token/ERC1155/ERC1155.sol`, `token/ERC1155/extensions/<Name>.sol` |
| `ERC2981` | `token/common/ERC2981.sol` |
| `Governor` and extensions, `TimelockController`, `IVotes` | `governance/Governor.sol`, `governance/extensions/<Name>.sol`, `governance/TimelockController.sol`, `governance/utils/IVotes.sol` |
| `ERC1967Proxy`, `ERC1967Utils` | `proxy/ERC1967/ERC1967Proxy.sol`, `proxy/ERC1967/ERC1967Utils.sol` |
| `TransparentUpgradeableProxy`, `ProxyAdmin` | `proxy/transparent/<Name>.sol` |
| `UpgradeableBeacon`, `BeaconProxy` | `proxy/beacon/<Name>.sol` |
| `Initializable`, `UUPSUpgradeable` | `proxy/utils/Initializable.sol`, `proxy/utils/UUPSUpgradeable.sol` |
| `Clones` | `proxy/Clones.sol` |
| `ECDSA`, `EIP712`, `MerkleProof`, `SignatureChecker`, `MessageHashUtils` | `utils/cryptography/<Name>.sol` |
| `Math`, `SafeCast` | `utils/math/<Name>.sol` |
| `Address`, `Create2`, `Multicall`, `Nonces`, `Strings`, `Base64`, `StorageSlot`, `SlotDerivation`, `TransientSlot` | `utils/<Name>.sol` |
| `EnumerableSet`, `EnumerableMap`, `BitMaps`, `Checkpoints`, `DoubleEndedQueue` | `utils/structs/<Name>.sol` |
| `ERC165`, `ERC165Checker` | `utils/introspection/<Name>.sol` |
| `ERC2771Context`, `ERC2771Forwarder` | `metatx/<Name>.sol` |
| `VestingWallet` | `finance/VestingWallet.sol` |

Upgradeable variants live in `@openzeppelin/contracts-upgradeable/` with the same layout and an `Upgradeable` suffix (`token/ERC20/ERC20Upgradeable.sol`, `access/OwnableUpgradeable.sol`). Import `Initializable` and `UUPSUpgradeable` from the main package: since 5.5 they are no longer transpiled and the aliases in the upgradeable package are deprecated.

## Changes from v4

| v4 | v5 |
|---|---|
| `Ownable()` sets `msg.sender` | `Ownable(initialOwner)` is required; `__Ownable_init(initialOwner)` in the upgradeable version |
| `security/ReentrancyGuard.sol`, `security/Pausable.sol` | `utils/ReentrancyGuard.sol`, `utils/Pausable.sol`; the `security/` folder is gone |
| `_beforeTokenTransfer`, `_afterTokenTransfer` hooks | Single `_update(from, to, value)` for ERC20 and ERC1155; `_update(to, tokenId, auth)` for ERC721 |
| `require` strings in tokens | Custom errors from ERC-6093 (`ERC20InsufficientBalance`, `ERC721NonexistentToken`) |
| `Counters`, `SafeMath` | Removed; use a `uint256` counter and built-in checked arithmetic |
| `safeApprove` | Removed; use `forceApprove`, `safeIncreaseAllowance`, `safeDecreaseAllowance` |
| `ERC20Snapshot`, `ERC165Storage`, `PaymentSplitter`, `PullPayment`, `Escrow` | Removed; use `ERC20Votes` checkpoints, `supportsInterface` overrides, `VestingWallet` or custom pull logic |
| Constructor-less initializers with `__gap` | Initializable and OZ upgradeable contracts store state in ERC-7201 namespaced structs; no `__gap` in OZ parents |
| `TransparentUpgradeableProxy(logic, admin, data)` with shared admin | The proxy deploys its own `ProxyAdmin(initialOwner)`; `upgradeAndCall` is called on that admin |
| `Governor` `execute` only | `propose`, `queue` (when `proposalNeedsQueuing`), `execute`; `votingDelay` and `votingPeriod` use the token clock (block number by default, timestamp if the votes token overrides `clock()`) |
| `AccessControl` only | Adds `AccessManager` and `AccessManaged` with scheduled execution |

Since 5.6 `ERC1967Proxy` and `TransparentUpgradeableProxy` revert with `ERC1967ProxyUninitialized` when the initialization data is empty (a subclass can override `_unsafeAllowUninitialized()` to opt out), and `ERC721`/`ERC1155` reject `address(0)` as an operator. Since 5.7 `EIP712` requires `name` and `version` to fit in 31 bytes.

## Tokens

- **ERC20**: override `_update` to add transfer-time logic (fees, pausing, vote checkpoints). Mint with `_mint`, burn with `_burn`.
- **ERC20Permit** (EIP-2612) adds `permit`; it inherits `Nonces`, so combining it with `ERC20Votes` requires overriding `nonces` (shown below).
- **ERC20Votes** tracks checkpoints for governance; holders must `delegate` (even to themselves) before votes count. Default clock is `block.number`; override `clock()` and `CLOCK_MODE()` to use timestamps.
- **ERC4626** tokenized vault. Override `_decimalsOffset()` to raise virtual shares and make inflation attacks expensive; the default is 0.
- **ERC721**: use `_safeMint` knowing it calls `onERC721Received` on contracts (reentrancy); update counters before minting. `ERC721Enumerable` adds heavy storage; prefer events and off-chain indexing.
- **ERC1155** with `ERC1155Supply` for supply tracking; receivers are called on transfers and mints.
- **ERC2981** royalties are a signal, not enforcement.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

contract GovToken is ERC20, ERC20Permit, ERC20Votes, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    constructor(address admin) ERC20("Gov Token", "GOV") ERC20Permit("Gov Token") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    // Required overrides: ERC20 and ERC20Votes both define _update; ERC20Permit and Nonces both define nonces.
    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {
        super._update(from, to, value);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}
```

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {ERC721, ERC721URIStorage} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract SavingsVault is ERC4626 {
    constructor(IERC20 asset_) ERC4626(asset_) ERC20("Savings Vault Share", "svSHARE") {}

    // Six extra decimals of virtual shares make donation-based inflation attacks costly.
    function _decimalsOffset() internal pure override returns (uint8) {
        return 6;
    }
}

contract Badge is ERC721URIStorage, Ownable {
    uint256 private _nextId;

    constructor(address initialOwner) ERC721("Badge", "BDG") Ownable(initialOwner) {}

    function mint(address to, string calldata uri) external onlyOwner returns (uint256 id) {
        id = _nextId++; // update before the receiver callback in _safeMint
        _safeMint(to, id);
        _setTokenURI(id, uri);
    }
}
```

## Access control

- **Ownable2Step**: one admin, transfer needs `transferOwnership` then `acceptOwnership` by the new owner. `renounceOwnership` makes admin functions permanently unreachable.
- **AccessControl**: roles are `bytes32` ids (`keccak256("MINTER_ROLE")`); `DEFAULT_ADMIN_ROLE` is `0x00` and administers every role unless `_setRoleAdmin` says otherwise. Use `_grantRole` in constructors and `onlyRole(...)` on functions.
- **AccessControlDefaultAdminRules**: constructor `(uint48 initialDelay, address initialDefaultAdmin)`; changing the default admin is two-step with a delay and there is exactly one default admin.
- **AccessControlEnumerable** adds on-chain member enumeration at storage cost; prefer events for listings.
- Hand the admin role to a multisig or timelock and revoke it from the deployer.

## AccessManager

`AccessManager` centralizes permissions for many contracts: it is the `authority`, and target contracts inherit `AccessManaged` and mark functions `restricted`. Roles are `uint64` ids (`ADMIN_ROLE = 0`, `PUBLIC_ROLE = type(uint64).max`). Constructor: `AccessManager(address initialAdmin)`.

Main calls: `labelRole(roleId, label)`, `grantRole(roleId, account, executionDelay)`, `revokeRole(roleId, account)`, `setTargetFunctionRole(target, selectors, roleId)`, `setGrantDelay(roleId, delay)`, `setTargetAdminDelay(target, delay)`, `setTargetClosed(target, closed)`, `schedule(target, data, when)` returning `(operationId, nonce)`, `execute(target, data)`, `cancel(caller, target, data)`, `updateAuthority(target, newAuthority)`.

Callers with an execution delay must `schedule` and later `execute` through the manager. The `restricted` check uses the selector of the function that entered the contract, so internal calls into a restricted function from another external function are checked against that entry selector; avoid calling restricted functions from `receive` and `fallback`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {AccessManaged} from "@openzeppelin/contracts/access/manager/AccessManaged.sol";
import {AccessManager} from "@openzeppelin/contracts/access/manager/AccessManager.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract Treasury is AccessManaged {
    using SafeERC20 for IERC20;

    constructor(address initialAuthority) AccessManaged(initialAuthority) {}

    function sweep(IERC20 token, address to, uint256 amount) external restricted {
        token.safeTransfer(to, amount);
    }
}

/// @dev Wiring, normally done from a deploy script by the manager's admin.
contract TreasurySetup {
    uint64 public constant TREASURER_ROLE = 1;

    function wire(AccessManager manager, Treasury treasury, address treasurer) external {
        manager.labelRole(TREASURER_ROLE, "TREASURER");
        manager.grantRole(TREASURER_ROLE, treasurer, 1 days); // must schedule, then execute after 1 day
        bytes4[] memory selectors = new bytes4[](1);
        selectors[0] = Treasury.sweep.selector;
        manager.setTargetFunctionRole(address(treasury), selectors, TREASURER_ROLE);
    }
}
```

`wire` only succeeds when the calling contract holds `ADMIN_ROLE` in the manager; in practice call these functions from the admin account in a script.

## Governance

Stack: a votes token (`ERC20Votes` or `ERC721Votes`), a `Governor` composed from extensions, and a `TimelockController` that owns the governed contracts. Extensions: `GovernorSettings` (delay, period, threshold), `GovernorCountingSimple`, `GovernorVotes`, `GovernorVotesQuorumFraction`, `GovernorTimelockControl`, `GovernorPreventLateQuorum`, `GovernorStorage`. Delay and period are expressed in the votes token's clock unit (blocks by default). Lifecycle: `propose`, vote, `queue` (when the timelock is used), `execute`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Governor} from "@openzeppelin/contracts/governance/Governor.sol";
import {GovernorSettings} from "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import {GovernorCountingSimple} from "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {GovernorVotes} from "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorVotesQuorumFraction} from "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import {GovernorTimelockControl} from "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {IVotes} from "@openzeppelin/contracts/governance/utils/IVotes.sol";

contract DaoGovernor is
    Governor,
    GovernorSettings,
    GovernorCountingSimple,
    GovernorVotes,
    GovernorVotesQuorumFraction,
    GovernorTimelockControl
{
    constructor(IVotes token, TimelockController timelock)
        Governor("DaoGovernor")
        GovernorSettings(7200 /* blocks */, 50400 /* blocks */, 0)
        GovernorVotes(token)
        GovernorVotesQuorumFraction(4)
        GovernorTimelockControl(timelock)
    {}

    function votingDelay() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingDelay();
    }

    function votingPeriod() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.votingPeriod();
    }

    function proposalThreshold() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.proposalThreshold();
    }

    function state(uint256 proposalId) public view override(Governor, GovernorTimelockControl) returns (ProposalState) {
        return super.state(proposalId);
    }

    function proposalNeedsQueuing(uint256 proposalId)
        public
        view
        override(Governor, GovernorTimelockControl)
        returns (bool)
    {
        return super.proposalNeedsQueuing(proposalId);
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint48) {
        return super._queueOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) {
        super._executeOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint256) {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    function _executor() internal view override(Governor, GovernorTimelockControl) returns (address) {
        return super._executor();
    }
}
```

Deployment order: token, `TimelockController(minDelay, proposers, executors, admin)`, governor; grant the governor `PROPOSER_ROLE` and `CANCELLER_ROLE` on the timelock, grant `EXECUTOR_ROLE` to `address(0)` or a chosen set, and renounce the timelock admin role. Check the timelock constructor against the version you use.

## Proxies and upgradeable contracts

- `ERC1967Proxy(implementation, data)` for UUPS; the implementation inherits `UUPSUpgradeable` and implements `_authorizeUpgrade`.
- `TransparentUpgradeableProxy(logic, initialOwner, data)` deploys its own `ProxyAdmin`; upgrades go through `ProxyAdmin.upgradeAndCall(proxy, newImplementation, data)`.
- `UpgradeableBeacon` plus `BeaconProxy` upgrade many proxies at once.
- `Clones` deploys minimal proxies (EIP-1167) for factory patterns; initialize immediately.
- Upgradeable contracts: no constructor logic except `_disableInitializers()`, an `initialize` function with the `initializer` modifier, parent initializers called with `onlyInitializing` (`__Ownable_init(owner)`, `__ERC20_init(name, symbol)`), and `reinitializer(n)` for later versions.
- Storage of OZ upgradeable contracts is namespaced (ERC-7201), so adding parents does not shift your variables. Your own contract state still needs append-only discipline or its own namespace. See [storage-and-upgrades.md](storage-and-upgrades.md).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Initializable} from "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts/proxy/utils/UUPSUpgradeable.sol";
import {ERC20Upgradeable} from "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import {ERC20PermitUpgradeable} from "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20PermitUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

contract TokenV1 is Initializable, ERC20Upgradeable, ERC20PermitUpgradeable, OwnableUpgradeable, UUPSUpgradeable {
    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address initialOwner) external initializer {
        __ERC20_init("Token", "TKN");
        __ERC20Permit_init("Token");
        __Ownable_init(initialOwner);
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}
```

Tooling: `@openzeppelin/hardhat-upgrades` (`upgrades.deployProxy`, `upgrades.upgradeProxy`, `upgrades.validateUpgrade`) and the OpenZeppelin Foundry Upgrades library validate layouts and flag unsafe operations such as `selfdestruct`, `delegatecall` and constructors; check their current docs for exact APIs and the `@custom:oz-upgrades-from` annotation for V2 contracts.

## Utilities and cryptography

- `SafeERC20`: `safeTransfer`, `safeTransferFrom`, `forceApprove`, `safeIncreaseAllowance`, `safeDecreaseAllowance`.
- `Address.sendValue` and `functionCall` revert on failure.
- `Math` (`mulDiv`, `ceilDiv`, `sqrt`, `tryAdd`), `SafeCast` (`toUint128` and friends revert on overflow).
- `ECDSA.recover` plus `MessageHashUtils.toTypedDataHash` or `EIP712._hashTypedDataV4`; use `SignatureChecker.isValidSignatureNow` to also accept ERC-1271 contract wallets.
- `MerkleProof.verify`: leaves should be double-hashed or otherwise distinct from internal nodes to avoid second-preimage issues.
- `Multicall`, `Nonces`, `Create2`, `Clones`, `StorageSlot`, `SlotDerivation`, `TransientSlot` (typed slot access, ERC-7201 helpers).
- `ERC2771Context` and `ERC2771Forwarder` for trusted-forwarder meta-transactions; use `_msgSender()` consistently, and keep the trusted forwarder set minimal.
- `ReentrancyGuardTransient` is cheaper than `ReentrancyGuard` but needs Cancun or later and is not supported on chains without EIP-1153.

## Pitfalls

- Copying v4 snippets: `Ownable()` with no argument, `security/` imports, hooks, `Counters` and `SafeMath` all fail to compile in v5.
- Forgetting overrides when combining `ERC20Votes`, `ERC20Permit`, `ERC721Enumerable` or `ERC721Votes`: the compiler lists the required `override(A, B)` set.
- Using `Ownable` where several operators need different powers; use roles or `AccessManager`.
- Passing an EOA as `TimelockController` proposer, executor or admin and keeping it.
- Not delegating votes: `ERC20Votes` balances do not count until `delegate` is called.
- Upgradeable implementation without `_disableInitializers()`.
- Installing `contracts` and `contracts-upgradeable` at different versions.
