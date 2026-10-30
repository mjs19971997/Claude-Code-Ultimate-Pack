# Storage Layout and Upgrades Reference

Covers state variable layout, ERC-7201 namespaced storage, custom storage layout, ERC-1967 proxy slots, and upgrade safety for Solidity 0.8.38 and OpenZeppelin Contracts 5.7.0 (verified 2026-10).

## Contents
- [Slot layout rules](#slot-layout-rules)
- [ERC-7201 namespaced storage](#erc-7201-namespaced-storage)
- [Custom storage layout](#custom-storage-layout)
- [ERC-1967 slots](#erc-1967-slots)
- [Choosing a proxy pattern](#choosing-a-proxy-pattern)
- [Initializers](#initializers)
- [Upgrade safety rules](#upgrade-safety-rules)
- [Upgrade example](#upgrade-example)
- [Tooling](#tooling)

## Slot layout rules

- State variables occupy 32-byte slots in declaration order, starting at slot 0, with base contracts first (in C3 linearization order, most base first).
- Value types smaller than 32 bytes pack into the current slot when they fit; a struct or array always starts a new slot, and items after it start a new slot.
- A mapping or dynamic array occupies one slot (`p`) by itself. Mapping value for key `k` lives at `keccak256(abi.encode(k, p))`; dynamic array elements start at `keccak256(abi.encode(p))`.
- `bytes` and `string` store short values (31 bytes or less) in the slot itself and long values at `keccak256(abi.encode(p))`.
- `constant` and `immutable` values take no storage slot; `transient` variables live in a separate transient layout.
- Inspect with `forge inspect <Contract> storage-layout` or the `storageLayout` compiler output.

```solidity
struct Packed {
    uint128 a; // slot 0, low bytes
    uint128 b; // slot 0, high bytes
    address owner; // slot 1
    bool flag; // slot 1, packs after the address
}
```

## ERC-7201 namespaced storage

ERC-7201 puts each module's state in a struct at a collision-resistant slot derived from a namespace id, so inheritance order and added parents never shift existing data. OpenZeppelin Contracts Upgradeable 5.x uses it for its own state.

Steps:
1. Choose a namespace id, usually `<project>.storage.<Module>` (for example `example.storage.Registry`).
2. Annotate the struct with NatSpec `@custom:storage-location erc7201:<id>`.
3. Compute the slot: `keccak256(abi.encode(uint256(keccak256(bytes(id))) - 1)) & ~bytes32(uint256(0xff))`. Subtracting 1 means the slot is not the output of a keccak256 with a known preimage, and the mask leaves the low byte zero so the struct's first slots can be addressed by small offsets.
4. Keep the slot as a `private constant` and access the struct through a pure getter using assembly.

Computation of the slot for `example.storage.Registry`: `0x9059e8fd9c5070bf26463002743d587936571e76c7911ed0ac60ce4e404c5200`. For the OpenZeppelin ERC20 namespace `openzeppelin.storage.ERC20` the slot is `0x52c63247e1f47db19d5ce0460030c497f067ca4cebf71ba98eeadabe20bace00`.

Since 0.8.35 the compiler can compute the slot at compile time with the `erc7201` builtin (returns `uint256`, usable in constants), which removes the chance of a typo in the hard-coded hash:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

contract Counter {
    /// @custom:storage-location erc7201:example.storage.Counter
    struct CounterStorage {
        uint256 value;
    }

    bytes32 private constant COUNTER_STORAGE_LOCATION = bytes32(erc7201("example.storage.Counter"));

    function increment() external returns (uint256) {
        CounterStorage storage $ = _getCounterStorage();
        return ++$.value;
    }

    function _getCounterStorage() private pure returns (CounterStorage storage $) {
        bytes32 location = COUNTER_STORAGE_LOCATION;
        assembly {
            $.slot := location
        }
    }
}
```

Rules for namespaced structs:
- Add new fields only at the end of the struct; never reorder, retype or remove fields in a deployed namespace.
- Create a new namespace (new id, new struct) for a new module, instead of extending an unrelated one.
- Do not reuse the id of a different struct.
- Tooling that understands the annotation (OpenZeppelin Upgrades plugins) checks the struct for layout compatibility across versions.

Older code instead reserves `uint256[50] private __gap;` at the end of each upgradeable base contract and shrinks it when adding variables. That pattern still works but is easy to get wrong; prefer namespaces for new code.

## Custom storage layout

Since 0.8.29 a contract can relocate its whole storage (including inherited state) to a base slot with the `layout at` specifier; the expression must be compile-time evaluable and may use constants and `erc7201`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

contract Vault layout at erc7201("example.storage.Vault") {
    uint256 public totalAssets; // lives at the namespaced base slot, not slot 0
}
```

Use it when a contract is deployed behind a proxy or as an EIP-7702 delegation target and must not collide with the delegating account's low slots. The compiler errors if the layout would wrap around the end of storage. Verify the result with `forge inspect <Contract> storage-layout`.

## ERC-1967 slots

ERC-1967 reserves fixed slots, computed as `bytes32(uint256(keccak256("eip1967.proxy.<name>")) - 1)`:

| Purpose | Slot |
|---|---|
| Implementation | `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` |
| Admin | `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` |
| Beacon | `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` |

Use `ERC1967Utils` to read and write them; do not hand-roll proxy slots. Explorers read these slots to show the implementation behind a proxy.

## Choosing a proxy pattern

| Pattern | Upgrade logic lives in | Notes |
|---|---|---|
| UUPS (`ERC1967Proxy` + `UUPSUpgradeable`, ERC-1822) | Implementation | Smaller proxy, cheaper calls. If an upgrade ships an implementation without `upgradeToAndCall` or with broken `_authorizeUpgrade`, the proxy is stuck. |
| Transparent (`TransparentUpgradeableProxy`) | Proxy, via its own `ProxyAdmin` | The admin cannot call the implementation through the proxy; each proxy gets its own admin contract in v5. Slightly more expensive calls. |
| Beacon (`UpgradeableBeacon` + `BeaconProxy`) | Beacon | One upgrade changes every proxy pointing at the beacon; suited to many instances of one contract. |
| Minimal proxy (`Clones`, EIP-1167) | Not upgradeable | Cheap factories; implementation is fixed. |
| Diamond (ERC-2535) | Facets | Complex storage and tooling; use only when contract size or modularity really requires it. |

Default to immutable contracts. If upgradeability is needed, UUPS or Transparent behind a multisig and timelock covers most cases.

## Initializers

- Constructors do not run in the proxy context; use an `initializer` function and call it in the deployment transaction through the proxy constructor data.
- Implementation constructor: `_disableInitializers()` so nobody can initialize or take over the implementation.
- Parent initializers (`__Ownable_init`, `__ERC20_init`) are `internal onlyInitializing` and must be called once each.
- `reinitializer(n)` runs a one-time migration for version `n`; `initializer` covers version 1.
- Immutables set in the implementation constructor are baked into the implementation code and are shared by every proxy; use them only for values common to all proxies (a trusted forwarder, a WETH address).

## Upgrade safety rules

- Never reorder, remove, retype or insert state variables in a deployed layout; append only (or add a new namespace).
- Do not change inheritance order of contracts that use sequential storage.
- Avoid `selfdestruct`, and `delegatecall` to arbitrary addresses, in implementations.
- Never add logic that makes `_authorizeUpgrade` permissionless, and test that the upgrade path still works after upgrading (a UUPS implementation must keep `UUPSUpgradeable`).
- Do not change the fields of a struct that is stored inside a mapping or array; append fields only to a namespaced struct held at a fixed slot. Appending enum members at the end is safe.
- Keep constructor arguments and immutables consistent across versions or document the change.
- Test upgrades against a fork or snapshot of real state, not only a fresh deployment.

## Upgrade example

V2 adds a field to the namespaced struct and a reinitializer. `@custom:oz-upgrades-from` tells the OpenZeppelin validators which contract it replaces.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Initializable} from "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts/proxy/utils/UUPSUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// @custom:oz-upgrades-from Registry
contract RegistryV2 is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    /// @custom:storage-location erc7201:example.storage.Registry
    struct RegistryStorage {
        mapping(bytes32 key => bytes32 value) entries;
        uint256 count;
        uint256 maxEntries; // appended in V2
    }

    bytes32 private constant REGISTRY_STORAGE_LOCATION =
        0x9059e8fd9c5070bf26463002743d587936571e76c7911ed0ac60ce4e404c5200;

    error TooManyEntries();

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initializeV2(uint256 maxEntries_) external reinitializer(2) {
        _getRegistryStorage().maxEntries = maxEntries_;
    }

    function set(bytes32 key, bytes32 value) external onlyOwner {
        RegistryStorage storage $ = _getRegistryStorage();
        if ($.entries[key] == bytes32(0)) {
            if ($.count >= $.maxEntries) revert TooManyEntries();
            ++$.count;
        }
        $.entries[key] = value;
    }

    function _getRegistryStorage() private pure returns (RegistryStorage storage $) {
        assembly {
            $.slot := REGISTRY_STORAGE_LOCATION
        }
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}
```

Upgrade call from the owner: `Registry(proxy).upgradeToAndCall(address(newImpl), abi.encodeCall(RegistryV2.initializeV2, (1000)))`, so the migration runs atomically with the upgrade. A contract that is the upgrade target must also keep `UUPSUpgradeable` in its inheritance.

## Tooling

- `forge inspect <Contract> storage-layout` prints slots, offsets and types; diff the output between versions in CI.
- OpenZeppelin Upgrades plugins for Hardhat (`@openzeppelin/hardhat-upgrades`) and Foundry (OpenZeppelin Foundry Upgrades) validate upgrade safety and layout compatibility; their manifests and APIs change, so check the current docs.
- Slither has upgradeability checks (`slither-check-upgradeability`).
- On every upgrade: dry-run on a fork, confirm the implementation is verified, confirm roles after the upgrade, and keep the previous implementation address for rollback.
