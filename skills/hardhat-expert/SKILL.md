---
name: hardhat-expert
description: >-
  Builds, tests and deploys Ethereum smart contracts with Hardhat 3: hardhat.config.ts with defineConfig, build profiles, EDR simulated and HTTP networks, Solidity (.t.sol) and TypeScript tests, hardhat-toolbox-viem or hardhat-toolbox-mocha-ethers, Hardhat Ignition modules, hardhat-verify and secrets via configVariable and the encrypted keystore. Use when editing hardhat.config.ts, writing network.create() tests, networkHelpers.loadFixture, Ignition modules, hardhat ignition deploy, hardhat verify or migrating a Hardhat 2 project. Not for Foundry projects (use foundry-expert), Solidity language and contract design (use solidity-expert), or ethers.js or viem application code (use ethersjs-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Hardhat Expert

This skill covers Hardhat 3: project setup and configuration, compiling with build profiles, writing Solidity and TypeScript tests, deploying with Hardhat Ignition, verifying contracts and handling secrets. Hardhat 3 is ESM-only and plugin-based, so configuration, imports and test setup differ from Hardhat 2; a short migration note is included for existing projects.

> Verified against Hardhat 3.21.2, @nomicfoundation/hardhat-toolbox-viem 5.0.7, hardhat-toolbox-mocha-ethers 4.0.0, hardhat-ignition 3.1.9, hardhat-keystore 3.1.2, hardhat-verify 3.1.4, Node.js 22.13+ and Solidity 0.8.38 (2026-10).

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

- Covered: `hardhat --init`, `hardhat.config.ts` (`defineConfig`, `plugins`, `solidity` profiles, `networks`, `paths`, `verify`, `test`), the tasks `build`, `test`, `run`, `node`, `clean`, `ignition`, `verify`, `keystore`, network connections (`network.create()`), `networkHelpers`, the viem and ethers+Mocha toolboxes, Ignition, verification, migration from Hardhat 2.
- Not covered: Foundry (foundry-expert), Solidity language patterns (solidity-expert), vulnerability analysis (smart-contract-security-expert), general ethers.js or viem application code (ethersjs-expert).

## 2. Core Expertise

Hardhat 3 core:
- **Config**: `defineConfig` from `hardhat/config`; features come from the `plugins` array, not side-effect imports; the config file is ESM TypeScript or JavaScript.
- **Compilation**: `hardhat build` (alias `compile`); build profiles (`default` for tests and scripts, `production` for Ignition deployments by default); `--build-profile <name>` selects one; compiler config accepts a version string, a list of versions, a single compiler object or `profiles`.
- **Networks**: `type: "edr-simulated"` (in-process EVM with forking, mining and hardfork options) and `type: "http"` (remote JSON-RPC); `chainType` `"l1"` or `"op"`; a global `--network <name>` option on tasks.
- **Network connections**: `const { viem, networkHelpers } = await network.create()` creates an isolated chain state and a connection extended by plugins (`network.connect()` still exists but is deprecated in favor of `create()`).
- **Tests**: Solidity tests (`*.t.sol` in `contracts/` or `.sol` in `test/`, forge-std cheatcodes, fuzz and invariant testing) and TypeScript tests with Node's test runner (viem toolbox, `hardhat test nodejs`) or Mocha and chai (ethers toolbox, `hardhat test mocha`).
- **Ignition**: declarative deployments with `buildModule`, journaled state, resumable runs, `--verify`.
- **Secrets**: `configVariable("NAME")` resolved from environment variables, then the encrypted keystore (`hardhat keystore set NAME`).

Toolbox choice:

| Toolbox | Runner and libraries |
|---|---|
| `@nomicfoundation/hardhat-toolbox-viem` | Node test runner, viem, `viem.assertions`, Ignition (viem), verify, keystore, network helpers |
| `@nomicfoundation/hardhat-toolbox-mocha-ethers` | Mocha, chai, ethers v6, TypeChain, chai matchers, Ignition (ethers), verify, keystore, network helpers |

Plugin details and versions are in [references/config-and-plugins.md](references/config-and-plugins.md).

## 3. Workflow

1. `npx hardhat --init` in an empty directory; pick the viem or the Mocha and ethers template. Node.js 22.13 or later is required.
2. Pin the Solidity version in `solidity.profiles` and add a `production` profile with the optimizer settings used on-chain.
3. Write contracts in `contracts/`; write unit and fuzz tests as `.t.sol` files next to them; write integration scenarios as TypeScript tests in `test/`.
4. Run `npx hardhat test` (everything), `npx hardhat test solidity`, `npx hardhat test nodejs` or `npx hardhat test mocha`; add `--coverage` and `--gas-stats` when needed.
5. Typecheck against generated types: `npx hardhat build && npx tsc --noEmit`.
6. Store secrets with `npx hardhat keystore set SEPOLIA_PRIVATE_KEY` and reference them with `configVariable` in config.
7. Write an Ignition module, run it against the in-process network, then against a testnet: `npx hardhat ignition deploy ignition/modules/Counter.ts --network sepolia`.
8. Verify with `--verify` on the deploy command, or `npx hardhat ignition verify <deploymentId>`, or `npx hardhat verify --network sepolia <address> <constructor args>`.
9. In CI, supply secrets as environment variables and run `build`, `test` and a typecheck.

## 4. Decision Rules

- Solidity tests for contract logic and fuzz or invariant checks; TypeScript tests for multi-contract flows, scripts, off-chain interaction and deployment-module tests.
- viem toolbox for new projects that want typed clients and the Node test runner; ethers and Mocha toolbox when the team or codebase already uses ethers and chai.
- One `network.create()` per test file when state can be shared; use `networkHelpers.loadFixture` for per-test isolation; create a new connection for stronger isolation.
- `configVariable` for every value that differs per environment or is sensitive (RPC URLs, API keys, private keys); plain values for public constants.
- Ignition for any deployment that is more than a throwaway script (it journals progress and resumes); `hardhat run` scripts for one-off tasks.
- Use build profiles instead of editing the compiler settings: `default` for fast local iteration, `production` for deployed bytecode.
- On a new project use Hardhat 3; keep Hardhat 2 only when a required plugin has no Hardhat 3 version.

## 5. Coding Standards

- `package.json` has `"type": "module"`; use ESM `import` and top-level `await`; relative imports of TypeScript files follow the template's `tsconfig.json` (`module: "node20"`, `verbatimModuleSyntax`).
- Import `network` (and `artifacts` if needed) from `"hardhat"`; import `defineConfig` and `configVariable` from `"hardhat/config"`.
- Test files are named after the contract (`test/Counter.ts`, `contracts/Counter.t.sol`).
- Use `bigint` literals (`1n`, `10n ** 18n`) for on-chain values; never `number` for wei.
- Pass the unawaited transaction promise to assertion helpers (`viem.assertions.revert(counter.write.inc())`, `expect(counter.inc()).to.emit(...)`).
- Prefer `node:assert/strict` for plain equality in the viem stack; use chai `expect` in the Mocha stack.
- `loadFixture` needs a named function; an anonymous or arrow function defeats the snapshot cache.

## 6. Project Structure

```
hardhat.config.ts
package.json                 # "type": "module"
tsconfig.json
contracts/
├── Counter.sol
└── Counter.t.sol            # Solidity unit and fuzz tests (forge-std)
test/
└── Counter.ts               # TypeScript integration tests
ignition/
├── modules/Counter.ts       # Ignition modules
└── parameters/              # per-network parameter files (non-secret)
scripts/                     # run with `hardhat run`
```

## 7. Design Patterns

- **Fixture per suite**: a named `deployX` function returning the contracts and signers; each test calls `networkHelpers.loadFixture(deployX)`.
- **Module per system**: one Ignition module per deployable unit, composed with `m.useModule(...)`; parameters through `m.getParameter(name, default)`.
- **Profiles per purpose**: `default` and `production` build profiles; network entries per environment (`hardhatMainnet`, `hardhatOp`, a forking network, `sepolia`).
- **Forked network entry**: an `edr-simulated` network with `forking: { url: configVariable("MAINNET_RPC_URL"), blockNumber }` for mainnet-fork tests.
- **Solidity-first tests**: `.t.sol` contract tests using `forge-std/Test.sol` for logic and fuzzing; TypeScript only for flows that need off-chain orchestration.
- **Config-driven secrets**: all credentials flow through `configVariable`, so tests and CI need no code change.

## 8. Best Practices

- Keep `hardhat.config.ts` declarative; compute nothing at import time that reads secrets.
- Label networks by purpose and keep a local `edr-simulated` network for tests.
- Install `forge-std` as a dev dependency (`foundry-rs/forge-std#v1.17.0` in the official template) when using Solidity tests.
- Run `npx hardhat build` before typechecking; generated types come from compiled artifacts.
- Use `networkHelpers.time.increase`, `mine`, `setBalance`, `impersonateAccount` instead of raw JSON-RPC calls.
- Commit the `ignition/deployments/` journal for networks you deploy to, so redeploys resume instead of repeating.
- Ignore `artifacts/`, `cache/` and `node_modules/` in git; do not ignore the Ignition deployments of live networks.

## 9. Performance

- Prefer Solidity tests for heavy loops and fuzzing: they run directly in the EVM.
- `loadFixture` snapshots state once and reverts to it; use it instead of redeploying in every test.
- Use `hardhat test --grep <pattern>` or a file argument to run a subset; `--no-compile` skips compilation when nothing changed.
- Fuzz and invariant settings are configured under `test.solidity` (`fuzz.runs`, `invariant.runs`, `invariant.depth`); keep defaults for local runs and raise them in a CI profile.
- Pin a `blockNumber` for forked networks so RPC responses are cached and results are stable.
- `hardhat test --gas-stats` reports gas per function; `--snapshot` and `--snapshot-check` (Solidity tests) track gas against stored values.

## 10. Security

- Never put a private key, mnemonic or API key in `hardhat.config.ts`, `.env` files that are committed, or Ignition parameter files. Use `configVariable("SEPOLIA_PRIVATE_KEY")` and store the value with `npx hardhat keystore set SEPOLIA_PRIVATE_KEY` (encrypted, password-protected).
- Resolution order for a `configVariable` is: environment variable, development keystore (`--dev`), production keystore; in CI the keystore is not used, so provide variables through the CI secret store. Keep real keys in the production keystore, not the `--dev` one.
- Variables are resolved lazily, only when a network that uses them is connected, so local tests do not need testnet secrets.
- Use a dedicated deployer account with limited funds per environment; for mainnet prefer a hardware wallet or a multisig flow over a hot key.
- `edr-simulated` networks with `allowUnlimitedContractSize` or relaxed gas settings hide production limits; keep those off in test setups that stand in for mainnet.
- Solidity test `ffi` and `fsPermissions` (under `test.solidity`) are opt-in settings; enable only what a test needs and never for untrusted pull requests.
- In GitHub Actions, never interpolate workflow inputs or other untrusted context expressions into `run:` scripts; pass them through `env:`.
- Verify deployed contracts and review the Ignition journal before announcing addresses.

## 11. Testing

- Test layers: Solidity (`hardhat test solidity`), TypeScript (`hardhat test nodejs` or `mocha`), or all together (`hardhat test`).
- Assertions in the viem stack: `viem.assertions.revert`, `revertWith`, `revertWithCustomError`, `revertWithCustomErrorWithArgs`, `emit`, `emitWithArgs`, `balancesHaveChanged`.
- Assertions in the ethers stack: chai matchers `.to.emit`, `.to.be.revertedWith`, `.to.be.revertedWithCustomError(...).withArgs(...)`, `.to.changeEtherBalance(ethers, ...)`.
- State control through `networkHelpers`: `time.increase`, `time.increaseTo`, `time.latest`, `mine`, `setBalance`, `impersonateAccount`, `takeSnapshot`, `loadFixture`.
- Test an Ignition module by deploying it in a test: `const { ignition } = await network.create(); const { counter } = await ignition.deploy(CounterModule);`.
- Coverage: `npx hardhat test --coverage`. Run the typecheck (`tsc --noEmit`) in CI.
- More in [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Config uses `defineConfig`, a `plugins` array and no hard-coded secrets.
- [ ] Every sensitive value goes through `configVariable`; CI provides them as environment variables.
- [ ] Solidity version and optimizer settings are pinned in a `production` profile used for deployment.
- [ ] Tests cover reverts (with custom error and args), events, access control and edge values.
- [ ] Fixtures use named functions with `loadFixture`.
- [ ] Forked networks pin a block number.
- [ ] Ignition modules return the contracts they deploy; parameters have defaults or a parameters file.
- [ ] Deployed contracts are verified; verification config uses `configVariable`.
- [ ] `npx hardhat build && npx tsc --noEmit` passes.
- [ ] `ignition/deployments/` for live networks is committed and reviewed.

## 13. Production Notes

- Deploy with the `production` build profile (Ignition uses it by default); do not mix bytecode built with different settings for deployment and verification.
- Ignition keeps a journal in `ignition/deployments/<deploymentId>`; rerunning the same deploy command resumes. Use `ignition status`, `ignition transactions`, `ignition wipe` (to rerun a failed future) and `ignition track-tx` (when advised by an error) for recovery.
- Verification options: `--verify` on `ignition deploy`, `ignition verify <deploymentId>`, or `hardhat verify` for Etherscan, `hardhat verify blockscout` for Blockscout; Sourcify is supported by the plugin.
- Fee settings for Ignition per network live under a network's `ignition` key (`maxFeePerGas`, `maxPriorityFeePerGas`, `gasPrice`, `disableFeeBumping`, `maxRetries`, `retryInterval`); global behavior (`requiredConfirmations`, `blockPollingInterval`) under the top-level `ignition` key.
- Local node: `npx hardhat node` starts a JSON-RPC server (default port 8545; `--fork <url>`, `--fork-block-number <n>`).
- Details are in [references/ignition-deployments.md](references/ignition-deployments.md).

## 14. Examples

Configuration with profiles, a forked network, secrets and verification (`hardhat.config.ts`):

```ts
import hardhatToolboxViemPlugin from "@nomicfoundation/hardhat-toolbox-viem";
import { configVariable, defineConfig } from "hardhat/config";

export default defineConfig({
  plugins: [hardhatToolboxViemPlugin],
  solidity: {
    profiles: {
      default: { version: "0.8.38" },
      production: {
        version: "0.8.38",
        settings: { optimizer: { enabled: true, runs: 200 } },
      },
    },
  },
  networks: {
    hardhatMainnet: { type: "edr-simulated", chainType: "l1" },
    mainnetFork: {
      type: "edr-simulated",
      chainType: "l1",
      forking: {
        url: configVariable("MAINNET_RPC_URL"),
        blockNumber: 21_000_000,
      },
    },
    sepolia: {
      type: "http",
      chainType: "l1",
      url: configVariable("SEPOLIA_RPC_URL"),
      accounts: [configVariable("SEPOLIA_PRIVATE_KEY")],
    },
  },
  verify: {
    etherscan: { apiKey: configVariable("ETHERSCAN_API_KEY") },
  },
  test: {
    solidity: { fuzz: { runs: 1000 } },
  },
});
```

```bash
npx hardhat keystore set SEPOLIA_RPC_URL
npx hardhat keystore set SEPOLIA_PRIVATE_KEY
npx hardhat keystore set ETHERSCAN_API_KEY
```

Contract (`contracts/Counter.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.38;

contract Counter {
    error Unauthorized(address caller);

    event Increment(uint256 by);

    address public immutable owner = msg.sender;
    uint256 public x;

    function inc() external {
        x++;
        emit Increment(1);
    }

    function incBy(uint256 by) external {
        require(by > 0, "incBy: increment should be positive");
        x += by;
        emit Increment(by);
    }

    function reset() external {
        if (msg.sender != owner) revert Unauthorized(msg.sender);
        x = 0;
    }
}
```

Solidity test with fuzzing (`contracts/Counter.t.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.38;

import {Test} from "forge-std/Test.sol";
import {Counter} from "./Counter.sol";

contract CounterTest is Test {
    Counter counter;
    address alice = makeAddr("alice");

    function setUp() public {
        counter = new Counter();
    }

    function testFuzz_IncBy(uint128 by) public {
        uint256 amount = bound(by, 1, type(uint128).max);
        counter.incBy(amount);
        assertEq(counter.x(), amount);
    }

    function test_RevertWhen_NonOwnerResets() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(Counter.Unauthorized.selector, alice));
        counter.reset();
    }
}
```

TypeScript test with the viem toolbox (`test/Counter.ts`):

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { network } from "hardhat";

describe("Counter", async function () {
  const { viem, networkHelpers } = await network.create();

  async function deployCounter() {
    const counter = await viem.deployContract("Counter");
    const [owner, alice] = await viem.getWalletClients();
    return { counter, owner, alice };
  }

  it("emits Increment and updates x", async function () {
    const { counter } = await networkHelpers.loadFixture(deployCounter);

    await viem.assertions.emitWithArgs(counter.write.incBy([3n]), counter, "Increment", [3n]);
    assert.equal(await counter.read.x(), 3n);
  });

  it("rejects reset from a non-owner", async function () {
    const { counter, alice } = await networkHelpers.loadFixture(deployCounter);

    await viem.assertions.revertWithCustomErrorWithArgs(
      counter.write.reset({ account: alice.account }),
      counter,
      "Unauthorized",
      [alice.account.address],
    );
  });
});
```

Ignition module (`ignition/modules/Counter.ts`) and deployment:

```ts
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("CounterModule", (m) => {
  const counter = m.contract("Counter");
  m.call(counter, "incBy", [5n]);
  return { counter };
});
```

```bash
npx hardhat ignition deploy ignition/modules/Counter.ts --network sepolia --verify
```

## 15. Common Mistakes

- **Hardhat 2 habits in a Hardhat 3 project**: `require`, `hre.ethers` globals and `import "@nomicfoundation/hardhat-toolbox"` do not apply. Use ESM, the `plugins` array and `network.create()`.
- **Forgetting to add a plugin to `plugins`**: importing a plugin without registering it prints a warning and the feature is missing.
- **Private keys in the config or `.env`**: use `configVariable` and the keystore; in CI use the secret store.
- **Anonymous fixture functions**: `loadFixture(async () => ...)` does not cache; pass a named function.
- **Awaiting the transaction before the assertion**: assertions need the promise (`viem.assertions.revert(counter.write.inc())`), not the result.
- **Sharing one connection when tests need isolation**: state persists across tests in a connection; use `loadFixture` or create a new connection.
- **Deploying with the `default` profile**: build deployed bytecode with the `production` profile (Ignition does by default) and verify with the same settings.
- **Unpinned fork blocks**: forked tests become slow and flaky; set `blockNumber`.
- **Treating the `--dev` keystore as a vault**: it exists for development values; keep real keys in the production keystore or a hardware wallet.
- **Typechecking before building**: generated types come from artifacts; run `hardhat build` first.
- **Expecting the keystore in CI**: it is skipped in CI; define environment variables for every `configVariable` the job uses.

## 16. References

- [references/config-and-plugins.md](references/config-and-plugins.md): config structure, build profiles, network options, plugins and versions, secrets and keystore, verification, migration from Hardhat 2.
- [references/ignition-deployments.md](references/ignition-deployments.md): module API, parameters, deployment state and recovery, strategies, fee settings, verification, CI workflow.
- [references/testing.md](references/testing.md): Solidity test configuration, TypeScript tests with viem and ethers, `networkHelpers`, forking, coverage, gas statistics.
- Hardhat docs: https://hardhat.org/docs
- Hardhat repository: https://github.com/NomicFoundation/hardhat
