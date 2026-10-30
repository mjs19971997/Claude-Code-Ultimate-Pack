---
name: foundry-expert
description: >-
  Builds, tests and deploys Solidity projects with Foundry (forge, cast, anvil, chisel): foundry.toml profiles, forge-std cheatcodes, fuzz and invariant tests, fork tests, forge script deployments with keystore accounts, Etherscan verification, gas snapshots and coverage. Use when working with foundry.toml, *.t.sol tests, *.s.sol scripts, forge test or forge script, vm.expectRevert, vm.prank, vm.deal, invariant_ functions, handlers, cast wallet import, anvil forks or chisel. Not for Solidity language design or contract patterns (use solidity-expert), auditing for vulnerabilities (use smart-contract-security-expert), or JavaScript-based projects (use hardhat-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Foundry Expert

This skill covers day-to-day work with the Foundry toolchain: project layout and `foundry.toml`, writing unit, fuzz, invariant and fork tests in Solidity, deploying with `forge script`, and the helper tools `cast`, `anvil` and `chisel`. Foundry is on the 1.x line, so examples target current `forge-std` and the cheatcode names that ship with it.

> Verified against Foundry 1.8.7 (forge, cast, anvil, chisel; released 2026-10-29), forge-std v1.17.0 and Solidity 0.8.38 (2026-10).

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

- Covered: `forge` (build, test, script, create, verify-contract, snapshot, coverage, fmt, lint, inspect, install, soldeer), `cast`, `anvil`, `chisel`, `foundry.toml` and profiles, forge-std (`Test`, `Script`, `StdInvariant`, `StdCheats`), cheatcodes, fuzz and invariant testing, fork testing, scripts, keystores, verification, gas reports, coverage, CI.
- Not covered: Solidity language features and contract design patterns (solidity-expert), vulnerability classes and audit methodology (smart-contract-security-expert), Hardhat or ethers/viem JavaScript tooling (hardhat-expert, ethersjs-expert).

## 2. Core Expertise

| Tool | Purpose |
|---|---|
| `forge` | Compile, test, deploy, verify, format, lint, inspect storage layout and ABI, manage dependencies |
| `cast` | CLI for RPC calls, ABI encoding, transactions, wallet and keystore management |
| `anvil` | Local node, optionally forking a live chain (`--fork-url`) |
| `chisel` | Solidity REPL for quick experiments |
| forge-std | `Test`, `Script`, `console`, `StdInvariant`, `StdCheats`, `StdUtils`, `stdJson`, `stdToml` |

Test kinds, all written in Solidity:
- **Unit**: functions starting with `test` (`test_`, `testFuzz_`, `test_RevertWhen_...` by convention).
- **Fuzz**: a test with parameters; Foundry generates inputs (256 runs by default).
- **Invariant**: functions starting with `invariant`; Foundry calls random sequences of target functions, then checks the property after each call.
- **Fork**: tests run against live chain state via `--fork-url` or `vm.createSelectFork`.

Frequently used cheatcodes (all on the `vm` object): `prank`, `startPrank`, `stopPrank`, `deal`, `warp`, `roll`, `expectRevert`, `expectEmit`, `expectCall`, `mockCall`, `assume`, `bound`, `store`, `load`, `etch`, `label`, `createSelectFork`, `envUint`, `envOr`, `startBroadcast`, `stopBroadcast`. The full catalogue with signatures is in [references/testing-and-cheatcodes.md](references/testing-and-cheatcodes.md).

## 3. Workflow

1. `forge init` (or `forge init --template <repo>`), then `forge install foundry-rs/forge-std` if it is not present. Commit `foundry.toml` and the dependency pins.
2. Pin the compiler (`solc = "0.8.38"`) and set an explicit `evm_version` only when the target chain needs it.
3. Write the contract, then its tests alongside: unit tests for each branch, `vm.expectRevert` for each custom error, `vm.expectEmit` for each event.
4. Add fuzz tests for pure arithmetic and input validation; add invariant tests with a handler for stateful protocols.
5. Run `forge test -vvv`; use `--match-test`, `--match-contract`, `--match-path` to focus; `-vvvv` shows full traces for failures.
6. Run `forge fmt`, `forge lint`, `forge build --sizes`, `forge snapshot` (or `forge test --gas-report`), `forge coverage`.
7. Add a fork test for every external integration (token, oracle, router) before relying on mocks.
8. Write a deployment script, simulate it without `--broadcast`, then broadcast with a keystore account and verify.
9. Re-run the full suite with the `ci` profile (higher fuzz and invariant runs) before merging.

## 4. Decision Rules

- Cheatcode or plain Solidity: use plain Solidity for logic and assertions; use `vm` only to control the environment (caller, time, balances, expected reverts, forks).
- `prank` for a single call, `startPrank`/`stopPrank` for several; `vm.expectRevert` binds to the next external call, so put it immediately before that call.
- `bound(x, min, max)` to reshape a fuzzed input into a valid range; `vm.assume` only for rare exclusions, because rejected inputs count against `max_test_rejects` (default 65536).
- Stateless properties (round trips, math) are fuzz tests; properties over sequences of calls (solvency, supply accounting) are invariant tests with a handler.
- Fork tests when behavior depends on a deployed contract you do not control; mocks (`vm.mockCall`, test doubles) when you only need a response shape.
- Deploy with `forge script`; avoid `forge create` for anything beyond a single throwaway contract (it deploys one contract at a time and has no multi-step script flow or `--resume`).
- Dependencies via `forge install` (git submodules) or `forge soldeer` (Foundry's built-in package manager); pin versions either way.

## 5. Coding Standards

- Test files `Name.t.sol`, scripts `Name.s.sol`, test contracts `NameTest`, handlers `NameHandler`.
- Test function names: `test_Behavior`, `test_RevertWhen_Condition`, `testFuzz_Property`, `invariant_Property`. Revert tests belong in `test_RevertWhen_...`; the old `testFail` prefix is not reliable (it passes on any revert) and should not be used.
- Use named imports (`import {Test} from "forge-std/Test.sol";`) and exact compiler pragmas in `src/`; tests and scripts may use the same pin.
- Create addresses with `makeAddr("alice")` (labels them in traces) rather than hard-coded literals.
- Assert with `assertEq`, `assertGt`, `assertApproxEqAbs`, `assertApproxEqRel`; prefer the overload that takes a message when a test has several assertions.
- Run `forge fmt` in CI with `--check`; configure style under `[fmt]` in `foundry.toml`.

## 6. Project Structure

```
foundry.toml
remappings.txt            # optional; Foundry infers remappings from lib/
src/
├── Vault.sol
└── interfaces/
test/
├── unit/Vault.t.sol
├── fuzz/Vault.fuzz.t.sol
├── invariant/
│   ├── Vault.invariant.t.sol
│   └── handlers/VaultHandler.sol
├── fork/Vault.fork.t.sol
└── utils/                # shared base contracts, mocks
script/
├── DeployVault.s.sol
└── config/               # non-secret per-chain JSON, read with stdJson
lib/                      # forge install / soldeer dependencies
broadcast/                # script run artifacts; commit or ignore per team policy
```

## 7. Design Patterns

- **Base test contract**: a shared `BaseTest is Test` that deploys the system, creates labeled actors and funds them; feature tests inherit it.
- **Handler-based invariant testing**: a handler contract exposes bounded, valid actions (`deposit`, `withdraw`), tracks ghost variables, and is the only target (`targetContract` or `targetSelector`); the invariant test asserts on the system and the ghost state.
- **Fork tests with pinned block**: `vm.createSelectFork("mainnet", 21_000_000)` (or `--fork-block-number`) so results are reproducible and RPC responses are cached.
- **Script split**: `run()` for broadcast, a separate pure function that builds the deployment so the same code is reused by tests (`new DeployVault().run()`).
- **Environment-specific config**: JSON or TOML per chain under `script/config/`, read with `vm.readFile` plus `stdJson`, with `fs_permissions` granting read access to that directory only.
- **Profiles**: `default` for local speed, `ci` for deep fuzzing, `production` or `deploy` for the exact optimizer settings used on-chain (see [references/foundry-toml-and-ci.md](references/foundry-toml-and-ci.md)).

## 8. Best Practices

- Keep each test about one behavior; set up state in `setUp()`, which runs before every test and fuzz run.
- Label every address (`vm.label`, `makeAddr`) so `-vvvv` traces are readable.
- Prefer custom errors and assert them with `abi.encodeWithSelector(Error.selector, args)`; `vm.expectPartialRevert(Error.selector)` when the arguments do not matter.
- Test the access-control matrix: for every privileged function, one test per unauthorized caller type.
- Check event arguments with `vm.expectEmit` and indexed flags that match the event definition; pass the emitter address as the fifth argument when several contracts emit.
- Keep handler functions total: bound inputs and skip invalid states inside the handler instead of letting calls revert (see `fail_on_revert` in section 9).
- Commit `foundry.toml`, `remappings.txt` and dependency pins; keep `cache/` and `out/` out of git.

## 9. Performance

- Fuzz and invariant knobs live in `[fuzz]` and `[invariant]`: `runs` (256 each by default), `depth` (500 by default for invariants), `dictionary_weight`, `shrink_run_limit`, `timeout`. Keep `default` low for fast feedback and raise them in the `ci` profile.
- `fail_on_revert = false` (the invariant default) lets handlers revert without failing the run; reverting calls waste depth, so bound handler inputs. Set `fail_on_revert = true` for a strict profile once handlers are clean.
- Use `forge test --match-path` or `--match-contract` during development instead of the whole suite.
- Fork tests: pin a block number so RPC responses are cached; use `--no-storage-caching` only when debugging stale state.
- `via_ir = true` produces better code for some contracts but compiles much slower; enable it only in the profile that matches production.
- `forge build --sizes` surfaces the EIP-170 contract size limit early; `forge snapshot --check` fails CI on gas regressions.

## 10. Security

- Never place private keys in `foundry.toml`, `.env` files that are committed, shell history or scripts. Create an encrypted keystore with `cast wallet import deployer --interactive` and pass `--account deployer` (plus `--sender <address>` for `forge script`) to `forge script` or `cast send`. Hardware wallets use `--ledger` or `--trezor`.
- Avoid `vm.envUint("PRIVATE_KEY")` plus `vm.startBroadcast(key)` in scripts; call `vm.startBroadcast()` with no argument and let the CLI supply the signer.
- RPC URLs and API keys go in environment variables referenced as `${VAR}` in `foundry.toml` (`[rpc_endpoints]`, `[etherscan]`); in CI they come from the secret store, never from the repository.
- `ffi = true` lets tests execute arbitrary programs; enable it per profile only when required and never in a profile that runs on untrusted pull requests.
- Cheatcodes that touch the filesystem (`readFile`, `writeFile`, `parseJson` on files) are gated by `fs_permissions`; grant `read` to a specific directory rather than `"./"`, and avoid `read-write` outside `out/` and `broadcast/`.
- Treat `vm.etch`, `vm.store` and `vm.mockCall` as test-only shortcuts: a test that depends on them proves nothing about the real dependency, so pair them with a fork test.
- Review `broadcast/` and dry-run output before broadcasting to mainnet: confirm chain id, sender, nonce and the list of transactions.

## 11. Testing

- Unit tests prove each branch and revert; fuzz tests prove properties over input ranges; invariant tests prove properties over call sequences; fork tests prove integration.
- Name the property in the test: `invariant_TotalSupplyEqualsSumOfBalances`, `testFuzz_DepositWithdrawRoundTrip`.
- Reproduce a failure: Foundry prints the seed and persists failing fuzz inputs under `cache/fuzz`; replay with `forge test --rerun` and fix the seed with `--fuzz-seed` when comparing runs.
- `vm.expectRevert` fails the test if the next call does not revert; `vm.expectEmit` fails if the matching event is not emitted by a later call in the same test.
- Measure with `forge coverage` (`--report lcov` for tooling); treat coverage as a floor, not a goal.
- Run the same suite against a pinned fork block in CI with an RPC key supplied through the environment.

## 12. Review Checklist

- [ ] `solc` is pinned, optimizer settings match what will be deployed, `evm_version` matches the target chain.
- [ ] Every revert path has a `vm.expectRevert` test with the exact error and arguments.
- [ ] Every event has a `vm.expectEmit` test.
- [ ] Fuzz inputs are shaped with `bound`; `vm.assume` is used sparingly.
- [ ] Invariant tests use a handler with bounded inputs; `targetContract` or `targetSelector` is explicit.
- [ ] Fork tests pin a block number and read the RPC URL from the environment.
- [ ] No private key, mnemonic or API key appears in the repository, scripts, CI config or logs.
- [ ] Deploy scripts use `vm.startBroadcast()` without a key and are simulated before `--broadcast`.
- [ ] CI runs `forge fmt --check`, `forge build --sizes`, `forge test` with the `ci` profile and a gas snapshot check.
- [ ] Dependencies are pinned (submodule commit or soldeer version).

## 13. Production Notes

- Install a specific release in CI (`foundry-rs/foundry-toolchain` with `version: v1.8.7`) so builds do not move with the default channel; locally use `foundryup --install v1.8.7` and `foundryup --list` to switch.
- Run the deployment with `--verify` and an Etherscan key from the environment; if verification fails the broadcast is not lost, retry with `forge verify-contract` or resume with `--resume`.
- Keep a record of each deployment (`broadcast/<script>/<chainId>/run-latest.json`) and store the addresses in a reviewed file, not in a chat message.
- Re-run the exact script in simulation against a fork of the target chain (`anvil --fork-url`) before the real broadcast.
- `forge script` batches transactions; use `--slow` on chains with unreliable nonces so each transaction confirms before the next is sent.
- Details on scripts, keystores, verification, `cast`, `anvil` and `chisel` are in [references/scripts-and-deployment.md](references/scripts-and-deployment.md).

## 14. Examples

Contract under test (`src/Vault.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

contract Vault {
    error ZeroAmount();
    error InsufficientBalance(uint256 available, uint256 requested);

    event Deposited(address indexed account, uint256 amount);
    event Withdrawn(address indexed account, uint256 amount);

    mapping(address account => uint256) public balanceOf;
    uint256 public totalDeposits;

    function deposit() external payable {
        if (msg.value == 0) revert ZeroAmount();
        balanceOf[msg.sender] += msg.value;
        totalDeposits += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        uint256 bal = balanceOf[msg.sender];
        if (amount > bal) revert InsufficientBalance(bal, amount);
        balanceOf[msg.sender] = bal - amount;
        totalDeposits -= amount;
        emit Withdrawn(msg.sender, amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok, "ETH transfer failed");
    }
}
```

Unit and fuzz tests (`test/unit/Vault.t.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Test} from "forge-std/Test.sol";
import {Vault} from "../../src/Vault.sol";

contract VaultTest is Test {
    Vault vault;
    address alice = makeAddr("alice");

    function setUp() public {
        vault = new Vault();
        vm.deal(alice, 100 ether);
    }

    function test_DepositEmitsEvent() public {
        vm.expectEmit(true, false, false, true, address(vault));
        emit Vault.Deposited(alice, 1 ether);
        vm.prank(alice);
        vault.deposit{value: 1 ether}();
        assertEq(vault.balanceOf(alice), 1 ether);
    }

    function test_RevertWhen_WithdrawExceedsBalance() public {
        vm.prank(alice);
        vault.deposit{value: 1 ether}();

        vm.expectRevert(abi.encodeWithSelector(Vault.InsufficientBalance.selector, 1 ether, 2 ether));
        vm.prank(alice);
        vault.withdraw(2 ether);
    }

    function testFuzz_DepositWithdrawRoundTrip(uint96 amount) public {
        uint256 value = bound(amount, 1, 100 ether);
        vm.startPrank(alice);
        vault.deposit{value: value}();
        vault.withdraw(value);
        vm.stopPrank();

        assertEq(vault.balanceOf(alice), 0);
        assertEq(alice.balance, 100 ether);
    }
}
```

Invariant test with a handler (`test/invariant/Vault.invariant.t.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Test} from "forge-std/Test.sol";
import {Vault} from "../../src/Vault.sol";

contract VaultHandler is Test {
    Vault public immutable vault;
    address[] internal actors;
    uint256 public ghostDeposited;

    constructor(Vault vault_) {
        vault = vault_;
        actors.push(makeAddr("actor1"));
        actors.push(makeAddr("actor2"));
        actors.push(makeAddr("actor3"));
    }

    function deposit(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        amount = bound(amount, 1, 10 ether);
        vm.deal(actor, actor.balance + amount);
        vm.prank(actor);
        vault.deposit{value: amount}();
        ghostDeposited += amount;
    }

    function withdraw(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        amount = bound(amount, 0, vault.balanceOf(actor));
        vm.prank(actor);
        vault.withdraw(amount);
        ghostDeposited -= amount;
    }
}

contract VaultInvariantTest is Test {
    Vault vault;
    VaultHandler handler;

    function setUp() public {
        vault = new Vault();
        handler = new VaultHandler(vault);

        bytes4[] memory selectors = new bytes4[](2);
        selectors[0] = VaultHandler.deposit.selector;
        selectors[1] = VaultHandler.withdraw.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    function invariant_BalanceMatchesAccounting() public view {
        assertEq(address(vault).balance, vault.totalDeposits());
        assertEq(vault.totalDeposits(), handler.ghostDeposited());
    }
}
```

Keystore-based deployment (`script/DeployVault.s.sol`) and commands:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

import {Script} from "forge-std/Script.sol";
import {console} from "forge-std/console.sol";
import {Vault} from "../src/Vault.sol";

contract DeployVault is Script {
    function run() external returns (Vault vault) {
        vm.startBroadcast(); // signer comes from --account, never from the source
        vault = new Vault();
        vm.stopBroadcast();
        console.log("Vault deployed at", address(vault));
    }
}
```

```bash
cast wallet import deployer --interactive          # prompts for the key and a keystore password
forge script script/DeployVault.s.sol --rpc-url sepolia --account deployer --sender 0xYourDeployerAddress
forge script script/DeployVault.s.sol --rpc-url sepolia --account deployer --sender 0xYourDeployerAddress --broadcast --verify
```

The first `forge script` call only simulates; adding `--broadcast` sends the transactions and `--verify` submits sources using the key under `[etherscan]` in `foundry.toml`.

## 15. Common Mistakes

- **`testFail` for revert checks**: it passes on any revert, including setup bugs. Use `vm.expectRevert` with the specific error.
- **`vm.expectRevert` placed before the wrong call**: it applies to the next call, including view calls used as arguments. Compute arguments first, then set the expectation, then call.
- **Unbounded fuzz inputs with `vm.assume`**: most inputs are rejected and the test aborts on `max_test_rejects`. Use `bound`.
- **Invariant tests without a handler**: the fuzzer calls every function with random arguments and mostly reverts. Write a handler and target it.
- **Targeting the handler's inherited functions**: use `targetSelector` to list only the handler actions you want called.
- **Private keys via `vm.envUint` and `--private-key`**: they end up in shell history and CI logs. Use `cast wallet import` and `--account`.
- **Floating `solc_version` or auto-detect in production profiles**: the deployed bytecode then depends on the machine. Pin `solc` and the optimizer.
- **Forking without a block number**: tests become non-deterministic and uncached. Pin the block.
- **Mocking everything**: `mockCall` and `etch` hide integration bugs; add at least one fork test per integration.
- **Forgetting `--broadcast`**: `forge script` only simulates without it; `forge create` also needs `--broadcast` in current releases.
- **Committing `broadcast/` of throwaway deployments or `.env` with real keys**: ignore throwaway runs, and never create `.env` files with secrets that can be committed.

## 16. References

- [references/testing-and-cheatcodes.md](references/testing-and-cheatcodes.md): cheatcode catalogue with signatures, fuzz and invariant configuration and patterns, fork testing, gas snapshots.
- [references/scripts-and-deployment.md](references/scripts-and-deployment.md): forge script flow, keystore accounts, verification, resuming broadcasts, cast, anvil and chisel usage.
- [references/foundry-toml-and-ci.md](references/foundry-toml-and-ci.md): foundry.toml keys and profiles, remappings, rpc and etherscan sections, dependency management, GitHub Actions workflow.
- Foundry book: https://book.getfoundry.sh
- forge-std: https://github.com/foundry-rs/forge-std
- Foundry releases: https://github.com/foundry-rs/foundry/releases
