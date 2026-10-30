# Audit Tooling

Tools for finding smart contract bugs, with the versions checked in 2026-10 and minimal working usage. Examples use the `EthVault` contract from Example 1 in `SKILL.md` (file `src/EthVault.sol`). The Foundry, Echidna and Halmos sources below compile with solc 0.8.38 and OpenZeppelin Contracts 5.x; they were compiled, not executed, so run them in your project.

## Contents
1. [Tool matrix](#1-tool-matrix)
2. [Slither](#2-slither)
3. [Aderyn](#3-aderyn)
4. [Foundry invariant testing](#4-foundry-invariant-testing)
5. [Echidna](#5-echidna)
6. [Medusa](#6-medusa)
7. [Halmos](#7-halmos)
8. [Certora Prover](#8-certora-prover)
9. [Discontinued tools](#9-discontinued-tools)
10. [CI wiring](#10-ci-wiring)

## 1. Tool matrix

| Tool | Kind | Version checked | Use it for |
|---|---|---|---|
| Slither | Static analysis (Python, Trail of Bits) | 0.11.6 (PyPI) | Known bug patterns, inheritance and call graphs, upgradeability checks |
| Aderyn | Static analysis (Rust, Cyfrin) | 0.6.8 (npm) | Fast Markdown, JSON and SARIF reports for Foundry and Hardhat projects |
| Foundry invariants | Stateful fuzzing in `forge test` | Foundry 1.8.7 | Protocol invariants with handlers; first choice for most teams |
| Echidna | Property-based fuzzer (Haskell, Trail of Bits) | 2.3.3 | Long campaigns, corpus reuse, assertion and property modes |
| Medusa | Parallel fuzzer (Go, Trail of Bits) | 1.5.1 | Echidna-style properties with parallel workers and coverage |
| Halmos | Symbolic testing (a16z) | 0.3.3 (latest PyPI release, 2025-07-31) | Proving `check_` tests for all inputs on arithmetic and small state machines |
| Certora Prover | Formal verification | certora-cli 8.20.3 (PyPI) | CVL rules and invariants over whole protocols; the Prover source is public on GitHub |

Static analyzers find patterns, fuzzers find stateful bugs, symbolic and formal tools prove properties on bounded or full state spaces. Use more than one kind.

## 2. Slither

```bash
pip install slither-analyzer          # or pipx install slither-analyzer
slither .                             # analyze a Foundry/Hardhat project
slither . --exclude-informational --exclude-optimization
slither . --print human-summary       # contract overview
slither . --checklist > slither.md    # Markdown report grouped by severity
slither-check-erc src/Token.sol Token --erc erc20
slither-check-upgradeability src/RegistryV1.sol RegistryV1
```

Triage rather than suppress. When a finding is a verified false positive, annotate the line with `// slither-disable-next-line <detector>` and a reason. Custom detectors can be written in Python against Slither's IR; see the Slither wiki for the API of the installed version.

## 3. Aderyn

```bash
npm install @cyfrin/aderyn -g   # or cyfrinup, Homebrew or the curl installer
aderyn                          # run from the project root; writes a Markdown report
aderyn --help                   # flags (output path, scope, format) for the installed version
```

Aderyn needs no configuration for standard Foundry and Hardhat layouts. Treat its output like Slither's: a list of candidates to confirm by reading the code.

## 4. Foundry invariant testing

Foundry runs `invariant_*` functions after random sequences of calls to the targeted contracts. Constrain the fuzzer with a handler so it only performs meaningful actions; unconstrained targeting wastes runs on reverts.

```toml
# foundry.toml
[profile.default]
solc = "0.8.38"
evm_version = "cancun"

[invariant]
runs = 256
depth = 128
fail_on_revert = false   # handlers bound their inputs; set true to treat any revert as failure
show_metrics = true      # shows calls and reverts per handler function

[profile.ci.invariant]
runs = 2048
depth = 256
```

The test below checks solvency (the vault holds exactly what it owes) and conservation of deposited value.

```solidity
// SPDX-License-Identifier: MIT
// test/invariant/EthVault.invariants.t.sol
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {StdInvariant} from "forge-std/StdInvariant.sol";
import {EthVault} from "../../src/EthVault.sol";

/// Handler: bounded, valid actions on a fixed set of actors, with ghost accounting.
contract VaultHandler is Test {
    EthVault public immutable vault;
    address[] public actors;
    uint256 public ghostDeposited;
    uint256 public ghostWithdrawn;

    constructor(EthVault v) {
        vault = v;
        for (uint160 i = 1; i <= 3; i++) {
            address a = address(uint160(0xA000) + i);
            actors.push(a);
            vm.deal(a, 1_000 ether);
        }
    }

    function deposit(uint256 actorSeed, uint256 amount) external {
        address a = actors[actorSeed % actors.length];
        amount = bound(amount, 1, 100 ether);
        vm.prank(a);
        vault.deposit{value: amount}();
        ghostDeposited += amount;
    }

    function withdraw(uint256 actorSeed, uint256 amount) external {
        address a = actors[actorSeed % actors.length];
        uint256 bal = vault.balanceOf(a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(a);
        vault.withdraw(payable(a), amount);
        ghostWithdrawn += amount;
    }

    function sumBalances() external view returns (uint256 sum) {
        for (uint256 i; i < actors.length; i++) sum += vault.balanceOf(actors[i]);
    }
}

contract EthVaultInvariants is StdInvariant, Test {
    EthVault internal vault;
    VaultHandler internal handler;

    function setUp() public {
        vault = new EthVault(address(this));
        handler = new VaultHandler(vault);

        targetContract(address(handler)); // fuzz only the handler
        bytes4[] memory selectors = new bytes4[](2);
        selectors[0] = VaultHandler.deposit.selector;
        selectors[1] = VaultHandler.withdraw.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    /// Solvency: the vault holds exactly what it owes.
    function invariant_balanceEqualsLiabilities() public view {
        assertEq(address(vault).balance, vault.totalDeposits());
        assertEq(vault.totalDeposits(), handler.sumBalances());
    }

    function invariant_conservation() public view {
        assertEq(handler.ghostDeposited() - handler.ghostWithdrawn(), vault.totalDeposits());
    }
}
```

Guidance:
- `targetContract(address)` and `targetSelector(FuzzSelector)` come from forge-std `StdInvariant`; `excludeContract`, `excludeSender` and `targetSender` narrow the campaign further.
- Use ghost variables in the handler for accounting the contract does not keep itself.
- Add an `afterInvariant` hook for end-of-run checks, and `show_metrics` to find handler functions that always revert.
- Failing sequences are shrunk and printed; copy them into an exploit regression test.
- Run `forge test --profile ci` for deeper runs in CI. Check `forge test --help` and the Foundry book for the flags in the installed version.

## 5. Echidna

Echidna runs property functions named `echidna_*` (return `bool`, no arguments) in the default `property` mode, or checks `assert` statements in `assertion` mode. The harness below wraps the vault and drives it with random calls.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EthVault} from "../src/EthVault.sol";

/// Echidna drives the public functions below with random arguments and senders.
contract EchidnaEthVault {
    EthVault internal vault;
    uint256 internal deposited;
    uint256 internal withdrawn;

    constructor() {
        vault = new EthVault(address(this));
    }

    receive() external payable {}

    function deposit() public payable {
        if (msg.value == 0) return;
        vault.deposit{value: msg.value}();
        deposited += msg.value;
    }

    function withdraw(uint256 amount) public {
        uint256 bal = vault.balanceOf(address(this));
        if (bal == 0) return;
        amount = (amount % bal) + 1;
        vault.withdraw(payable(address(this)), amount);
        withdrawn += amount;
    }

    function echidna_vault_is_solvent() public view returns (bool) {
        return address(vault).balance == vault.totalDeposits()
            && deposited - withdrawn == vault.totalDeposits();
    }
}
```

```yaml
# echidna.yaml
testMode: property
testLimit: 100000
corpusDir: echidna-corpus
```

```bash
echidna echidna/EchidnaEthVault.sol --contract EchidnaEthVault --config echidna.yaml
```

Echidna 2.3.3 also generates Foundry reproducers for some failures; check `echidna --help` for the options of the installed version. Keep the corpus directory in CI cache so campaigns resume with coverage.

## 6. Medusa

Medusa reads `medusa.json` and runs `property_*` functions (default prefix) and assertion tests, using parallel workers.

```bash
medusa init                 # writes medusa.json
medusa fuzz                 # run the campaign with the project's config
```

Relevant `fuzzing` keys in `medusa.json` include `workers`, `testLimit`, `callSequenceLength` and `corpusDirectory`; testing modes are under `fuzzing.testing` (`propertyTesting`, `assertionTesting`, each with `enabled` and `testPrefixes`). Medusa 1.5.1 supports `assert*` cheatcodes. Rename Echidna's `echidna_` properties to `property_` (or change the prefix) to reuse a harness.

## 7. Halmos

Halmos symbolically executes Foundry-style tests whose names start with `check_`, so an `assert` is proven for all inputs satisfying the assumptions (within loop and array bounds), or a counterexample is printed.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// Halmos runs `check_` functions symbolically: the assertion must hold for all inputs.
contract FeeBoundsSymbolicTest is Test {
    function check_feeNeverExceedsAmount(uint128 amount, uint16 bps) public pure {
        vm.assume(bps <= 10_000);
        uint256 fee = Math.mulDiv(amount, bps, 10_000, Math.Rounding.Ceil);
        assert(fee <= amount);
    }
}
```

```bash
uv tool install --python 3.12 halmos   # or: pip install halmos
halmos                                  # run from the Foundry project root
halmos --help                           # solver, loop and timeout options
```

Best for pure arithmetic, rounding, encoding/decoding and small state machines. Large storage-heavy code or unbounded loops can time out; split the property or switch to fuzzing. Halmos 0.3.3 is the newest PyPI release as of 2026-10; check the repository activity before depending on newer features.

## 8. Certora Prover

Certora verifies rules written in CVL (`.spec`) against compiled contracts for all inputs and all call sequences, using invariants, parametric rules and summaries for external calls.

```bash
pip install certora-cli                 # provides certoraRun
certoraRun certora/confs/vault.conf     # conf references contracts, spec and solc
```

Typical properties: balances sum to total supply, only a role can change a parameter, no function decreases another user's balance, withdraw followed by deposit never creates value. Cloud runs need an access key (`CERTORAKEY`); the Prover is also published as source on GitHub for local builds. Check the current Certora documentation for installation and the `.conf` schema.

## 9. Discontinued tools

- MythX (the Consensys Diligence analysis service) has been sunset; do not add it to new pipelines. Mythril remains open source.
- OpenZeppelin Defender: the hosted service was announced to shut down on 1 July 2026. OpenZeppelin points to its open source Relayer and Monitor (AGPL-3.0) as replacements. The Defender SDK is deprecated after the shutdown.

## 10. CI wiring

- Pull request: `forge build`, `forge test`, Slither (fail on high and medium after triage), Aderyn report as an artifact.
- Nightly or on tag: `forge test --profile ci` (deep invariants), Echidna or Medusa campaign with a cached corpus, Halmos for `check_` tests.
- Pre-audit: Certora rules for the core accounting contracts, with the rules kept in the repo.
- Pin tool versions in CI (for example `slither-analyzer==0.11.6`) and upgrade deliberately; new detectors change results.
