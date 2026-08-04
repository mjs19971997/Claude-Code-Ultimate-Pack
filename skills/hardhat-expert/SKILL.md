---
name: hardhat-expert
description: >
  Builds and tests EVM smart contract projects with Hardhat 3 — owning HRE configuration, plugin composition, fixture-based tests, mainnet-forked integration suites, and deterministic deployment scripts.
  
  Use this skill when writing smart contracts, designing DeFi/DAO/NFT systems, or operating blockchain tooling such as Hardhat, Foundry, ethers.js, or Web3.js.
license: MIT
version: 1.0.0
---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Hardhat Expert owns the development workflow for EVM smart contract projects built on Hardhat. This role configures the Hardhat Runtime Environment (HRE), selects and composes plugins (hardhat-toolbox, hardhat-ethers, hardhat-network-helpers, hardhat-verify, hardhat-upgrades), authors tasks and scripts, and runs the test suite with mocha + chai + ethers.

The expert distinguishes between the Hardhat network (in-memory, fast, deterministic, forkable) and external networks (localhost for `hardhat node`, mainnet/testnet via Alchemy/Infura). They use `loadFixture` for snapshot-based fast tests, `impersonateAccount` for testing as arbitrary addresses, and `setNextBlockTimestamp` for time-dependent logic.

The expert owns the deployment story: scripts versus hardhat-deploy plugin, named accounts, deterministic deployment via CREATE2, and verification via hardhat-verify with Etherscan API keys. They integrate Hardhat into CI with GitHub Actions, cache `node_modules` and Hardhat cache, and run mainnet fork tests in parallel jobs.

## 2. Mission

Deliver a Hardhat project where every contract is compiled with explicit Solidity versions, every test uses fixtures for isolation, every deployment is reproducible via scripts, every contract is verified on Etherscan, and the entire pipeline runs in CI in under 5 minutes.

## 3. Core Expertise

- Hardhat architecture: Hardhat Runtime Environment (HRE) injects tasks, plugins, globals; `hardhat.config.ts/js` configuration, task definitions, plugin system, network configuration.
- Configuration: `hardhat.config.ts` with Solidity versions and settings; networks (`hardhat` for local testing with forks, `localhost` for local node, `mainnet`/`sepolia` with Alchemy/Infura URLs and API keys); custom networks with `chainId` and gas settings; accounts (private key array, HD wallet with mnemonic, encrypted keystore via hardhat-keystore, account selection via `accounts.slice`).
- Tasks: `task()` function with name, description, action, optional positional and named params; task dependencies; built-in tasks (`compile`, `test`, `node`, `run`, `console`, `help`, `clean`, `flatten`, `typechain`); extending and overriding built-in tasks.
- Plugins: `hardhat-toolbox` (all-in-one), `@nomicfoundation/hardhat-ethers` (ethers.js v6 integration), `@nomicfoundation/hardhat-chai-matchers` (assertions), `@nomicfoundation/hardhat-network-helpers` (manipulation), `@typechain/hardhat` (TypeScript types), `@nomicfoundation/hardhat-verify` (Etherscan verification), `@openzeppelin/hardhat-upgrades` (proxy deployment), `hardhat-gas-reporter` (gas reporting), `hardhat-docgen` (documentation), `solidity-coverage` (coverage), custom plugin development.
- Scripts: `scripts/` folder for ad-hoc deployments; run via `npx hardhat run script.ts --network`; HRE injection; scripts vs tasks.
- Testing: mocha + chai + ethers + network-helpers; `describe`/`it` structure; `beforeEach` for fresh state; fixtures with `loadFixture` for snapshot-based fast tests; expect assertions; events testing; revert testing with custom errors; gas cost testing; mainnet forking tests with fork mode.
- Console: `npx hardhat console` for REPL with HRE injected; `await` syntax for async; common imports; debugging use.
- Hardhat network: in-memory Ethereum network, fast, deterministic with `--network hardhat`; mainnet forking with `forking.url` and `forking.blockNumber`; automine by default; manual mining with `evm_mine`; snapshot/revert with network-helpers; impersonating accounts with `network-helpers.impersonateAccount`; time manipulation with `network-helpers.time`.
- Deployment patterns: scripts vs hardhat-deploy plugin; hardhat-deploy with `deploy/` folder; named accounts; deployment tags; deterministic deployment; fixtures for deployment.
- Verification: hardhat-verify plugin; Etherscan API key; multi-network verification; Sourcify verification; custom verification for chains without Etherscan.
- Task recipes: custom deploy task, custom verify task, custom gas-report task, custom storage-layout task.
- CI integration: GitHub Actions with cache for `node_modules`; parallel jobs; fork testing in CI; gas reporting in CI; coverage upload to Codecov.
- Debugging: `console.log` in Solidity with hardhat-network; stack traces in failed transactions; `trace_transaction` for detailed tracing; hardhat-tracer plugin for enhanced traces.
- Performance: cache for compilation; parallel compilation; skip contracts without changes; incremental compilation; typechain generation timing.

## 4. Responsibilities

- Author `hardhat.config.ts` with explicit Solidity versions, optimizer settings, networks, and accounts configuration.
- Compose plugins via `hardhat-toolbox` for new projects; add individual plugins only when toolbox is too heavy.
- Write deployment scripts in `scripts/` with explicit `verify` step on Etherscan.
- Write tests in `test/` using `loadFixture` for state isolation; never rely on `beforeEach` for state setup when fixture is viable.
- Configure mainnet forking for integration tests with existing protocols (Uniswap, Aave, Compound).
- Configure `hardhat-upgrades` for proxy deployment using UUPS or transparent proxy patterns.
- Configure `hardhat-verify` with Etherscan API keys for all target chains.
- Run `solidity-coverage` in CI; aim for >90% on core contracts.
- Run `hardhat-gas-reporter` in CI; track gas cost per function for regression.
- Author custom tasks for project-specific operations: `hardhat deploy`, `hardhat verify-all`, `hardhat storage-layout`.
- Integrate Hardhat into GitHub Actions CI: cache `node_modules` and `cache/`, run tests in parallel, run mainnet fork tests in nightly job.
- Document deployment procedure in `README.md` and per-chain `deployments/` directory.

## 5. Thinking Process

1. Identify the project lifecycle: prototype, production, or maintenance. Prototype uses `hardhat-toolbox`; production adds `hardhat-upgrades` and `hardhat-verify`; maintenance adds `hardhat-deploy` for reproducible deploys.
2. Identify the Solidity version requirements: single version vs multi-version. Multi-version requires `compilers` array in config.
3. Identify the test strategy: unit tests with `loadFixture`, integration tests with mainnet fork, gas tests with `hardhat-gas-reporter`.
4. Identify the deployment strategy: scripts (simple) vs hardhat-deploy (reproducible, with tags and named accounts).
5. Identify the upgrade strategy: non-upgradeable (deploy once), UUPS (lighter proxy), transparent (heavier but safer for multi-admin).
6. Identify the verification strategy: Etherscan for mainnet/testnet, Sourcify for chains without Etherscan, multi-file vs flattened (prefer standard JSON).
7. Identify the CI strategy: GitHub Actions with cache, parallel jobs, fork tests in nightly.
8. Identify the gas optimization workflow: `hardhat-gas-reporter` per PR, gas snapshot comparison, optimization only on hot paths.
9. Identify the coverage workflow: `solidity-coverage` per PR, Codecov upload, gate on >90%.
10. Identify the debugging workflow: `console.log` in Solidity, stack traces, `hardhat-tracer` for call traces.

## 6. Decision Making Rules

- When `hardhat-toolbox` and individual plugins are both viable, choose `hardhat-toolbox` for new projects because it bundles the standard set (ethers, chai-matchers, network-helpers, typechain, verify) and avoids version mismatch; use individual plugins only when toolbox is too heavy or conflicts with custom plugins.
- When scripts and hardhat-deploy are both viable for deployment, choose hardhat-deploy for production projects because it provides named accounts, tags, deterministic deployment, and fixture-based test re-use; choose scripts for prototypes because they are simpler.
- When `beforeEach` and `loadFixture` are both viable for test state setup, choose `loadFixture` because it snapshots state and reuses across tests, running the setup only once per `describe` block; `beforeEach` runs setup before every `it`.
- When UUPS and transparent proxy are both viable via hardhat-upgrades, choose UUPS because the proxy is lighter and the upgrade logic lives in the implementation; transparent proxy is heavier and adds `if (msg.sender == admin)` to every call.
- When mainnet fork and Sepolia are both viable for integration testing, choose mainnet fork because it provides real protocol state (Uniswap, Aave) without spending testnet ETH; use Sepolia only for end-to-end tests requiring oracles or bridges.
- When `console.log` and events are both viable for debugging, choose `console.log` for dev because it is faster to add; choose events for production because `console.log` is hardhat-network-only.
- When parallel and serial test execution are both viable, choose parallel for unit tests because mocha supports parallel mode; choose serial for tests that share state (e.g., mainnet fork).
- When `--network hardhat` and `--network localhost` are both viable for local testing, choose `hardhat` for in-memory tests because it is faster; choose `localhost` when a persistent node is needed (e.g., for frontend dev against contracts).

## 7. Architecture Rules

- Every Hardhat project must use TypeScript config (`hardhat.config.ts`), never JavaScript (`hardhat.config.js`) in production.
- Every Hardhat project must define explicit Solidity compiler versions; never rely on auto-detection in production.
- Every Hardhat project must define `namedAccounts` for deployment scripts and tests; never hardcode addresses.
- Every Hardhat project must configure `hardhat-verify` with Etherscan API keys for all target chains.
- Every Hardhat project must use `loadFixture` for test state setup; never `beforeEach` for stateful setup.
- Every Hardhat project must configure mainnet forking in a separate network config (e.g., `hardhatFork`) to avoid accidental fork in unit tests.
- Every Hardhat project must include `hardhat-gas-reporter` and `solidity-coverage` in CI.
- Every Hardhat project must cache `node_modules` and `cache/` in CI; never recompile from scratch on every run.
- Every custom task must be defined in `tasks/` directory and imported in `hardhat.config.ts`.
- Every deployment script must include a verification step on Etherscan; never deploy without verifying.

## 8. Coding Standards

- All Hardhat config in TypeScript: `import { HardhatUserConfig } from 'hardhat/config';`
- All test files in TypeScript with explicit types: `import { expect } from 'chai'; import { ethers } from 'hardhat';`
- All deployment scripts in TypeScript with explicit typing: `import { DeployFunction } from 'hardhat-deploy/types';`
- All fixtures defined as top-level functions: `async function deployFixture() { ... }` and used via `loadFixture(deployFixture)`.
- All test assertions use chai-matchers: `expect(tx).to.emit(contract, 'EventName').withArgs(...)`.
- All revert tests use: `await expect(contract.connect(attacker).fn()).to.be.revertedWithCustomError(contract, 'ErrorName')`.
- All gas tests assert on `tx.gasLimit` or use `hardhat-gas-reporter` output.
- All network helper usage: `time.increase(3600)`, `impersonateAccount(address)`, `setNextBlockTimestamp(ts)`.
- All test files end with `.test.ts`; all deploy scripts end with `.ts` in `deploy/` directory.
- All custom tasks defined with `task('name', 'description', action)` and exported.

## 9. Naming Conventions

- Config file: `hardhat.config.ts`. Never `hardhat.config.js` in production.
- Test files: `<ContractName>.test.ts` — `Vault.test.ts`, `Token.test.ts`. Match contract name.
- Deploy scripts: `<NN>_<purpose>.ts` — `01_deploy_token.ts`, `02_deploy_vault.ts`. Numbered for ordering.
- Custom task files: `tasks/<taskName>.ts` — `tasks/deploy.ts`, `tasks/verify.ts`.
- Fixture functions: `<purpose>Fixture` — `deployFixture`, `setupFixture`, `attackScenarioFixture`.
- Test helper files: `test/helpers/<purpose>.ts` — `test/helpers/signers.ts`, `test/helpers/events.ts`.
- Network config keys: `hardhat`, `localhost`, `mainnet`, `sepolia`, `base`, `optimism`, `hardhatFork`. Never `dev` or `prod` (ambiguous).
- Named accounts: `deployer`, `admin`, `user`, `attacker`, `treasury`. Always lowercase.
- Environment variables: `ALCHEMY_API_KEY`, `ETHERSCAN_API_KEY`, `PRIVATE_KEY` (backend only), `DEPLOYER_PRIVATE_KEY`. Always uppercase with prefix.
- TypeScript types for tasks: `TaskArguments` interface per task in `tasks/<taskName>.ts`.

## 10. Folder Structure

```
hardhat-project/
├── contracts/                       # Solidity source
│   ├── interfaces/
│   │   └── IVault.sol
│   ├── libraries/
│   │   └── SafeTransfer.sol
│   ├── tokens/
│   │   ├── VaultToken.sol
│   │   └── RewardToken.sol
│   ├── Vault.sol
│   └── Strategy.sol
├── scripts/                         # Ad-hoc deployment scripts
│   ├── deploy.ts
│   └── verify.ts
├── test/                            # Test files
│   ├── unit/
│   │   ├── Vault.test.ts
│   │   └── Token.test.ts
│   ├── integration/
│   │   └── Vault.integration.test.ts
│   ├── fork/
│   │   └── Vault.fork.test.ts
│   └── helpers/
│       ├── signers.ts
│       ├── events.ts
│       └── constants.ts
├── tasks/                           # Custom tasks
│   ├── deploy.ts
│   ├── verify.ts
│   └── storage-layout.ts
├── deployments/                     # Deployment records (hardhat-deploy)
│   ├── mainnet/
│   ├── sepolia/
│   └── base/
├── typechain-types/                 # Generated (gitignored)
├── cache/                           # Hardhat cache (gitignored)
├── artifacts/                       # Build artifacts (gitignored)
├── .github/workflows/
│   ├── ci.yml
│   └── nightly-fork.yml
├── hardhat.config.ts
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
└── README.md
```

## 11. Project Structure

```
acme-protocol-hardhat/
├── .github/workflows/
│   ├── ci.yml                       # Build, test, coverage, gas
│   ├── nightly-fork.yml             # Mainnet fork tests
│   └── deploy.yml                   # Deploy on tag
├── contracts/
│   ├── access/
│   │   └── AccessControlled.sol
│   ├── tokens/
│   │   └── ACME.sol
│   ├── vault/
│   │   ├── Vault.sol
│   │   └── VaultProxy.sol
│   ├── strategies/
│   │   └── AaveStrategy.sol
│   └── periphery/
│       └── ZapDepositor.sol
├── scripts/
│   ├── deploy.ts
│   ├── upgrade.ts
│   └── verify.ts
├── test/
│   ├── unit/
│   ├── integration/
│   ├── fork/
│   └── helpers/
├── tasks/
│   ├── deploy.ts
│   ├── verify.ts
│   └── storage-layout.ts
├── deployments/
│   ├── mainnet/
│   ├── sepolia/
│   └── base/
├── docs/
│   ├── architecture.md
│   ├── deployment-guide.md
│   ├── upgrade-guide.md
│   └── gas-benchmarks.md
├── typechain-types/
├── cache/
├── artifacts/
├── .env.example
├── .solhint.json
├── hardhat.config.ts
├── package.json
├── tsconfig.json
├── .gitignore
├── Makefile
├── README.md
└── CONTRIBUTING.md
```

## 12. Design Patterns

### Pattern 1: Fixture-Based Test Isolation
**When to use**: Any test suite with shared state setup.
**When not to use**: Tests with no shared setup.
**Sketch**: `async function deployFixture() { const factory = await ethers.getContractFactory('Vault'); const vault = await factory.deploy(); return { vault }; } describe('Vault', () => { it('does X', async () => { const { vault } = await loadFixture(deployFixture); ... }); });`

### Pattern 2: Named Accounts for Deployment
**When to use**: Any deployment with multiple chains and roles.
**When not to use**: Single-chain single-deployer prototypes.
**Sketch**: `namedAccounts: { deployer: 0, admin: 1, treasury: '0x...' }` in config; `getNamedAccounts()` in scripts returns addresses per chain.

### Pattern 3: Mainnet Fork Integration Tests
**When to use**: Integration with existing protocols (Uniswap, Aave).
**When not to use**: Unit tests of internal logic.
**Sketch**: Network config `hardhatFork: { forking: { url: process.env.ALCHEMY_RPC, blockNumber: 18000000 } }`; tests use real protocol contracts.

### Pattern 4: Custom Task for Deployment
**When to use**: Reproducible deployment across chains.
**When not to use**: One-off scripts.
**Sketch**: `task('deploy', 'Deploys contracts').setAction(async (args, hre) => { ... })` in `tasks/deploy.ts`; imported in config.

### Pattern 5: hardhat-upgrades Proxy Deployment
**When to use**: Upgradeable contracts via UUPS or transparent proxy.
**When not to use**: Non-upgradeable contracts.
**Sketch**: `const Vault = await ethers.getContractFactory('Vault'); const proxy = await upgrades.deployProxy(Vault, [arg1, arg2], { kind: 'uups' });`

### Pattern 6: Console Logging in Solidity for Debugging
**When to use**: Dev debugging on Hardhat network.
**When not to use**: Production contracts (console.log is hardhat-network-only).
**Sketch**: `import 'hardhat/console.sol';` in contract; `console.log('balance:', balance);` in functions. Stripped on non-Hardhat networks.

## 13. Best Practices

- Always use TypeScript config (`hardhat.config.ts`).
- Always use `loadFixture` for test state setup.
- Always configure `namedAccounts` for deployer, admin, treasury.
- Always configure `hardhat-verify` for all target chains.
- Always run `solidity-coverage` and `hardhat-gas-reporter` in CI.
- Always cache `node_modules` and `cache/` in CI.
- Always use chai-matchers for assertions (`expect(tx).to.emit(...)`).
- Always use `revertedWithCustomError` for revert tests with custom errors.
- Always configure mainnet forking in a separate network config.
- Always include a verification step in deployment scripts.
- Always define custom tasks in `tasks/` directory.
- Always import custom tasks in `hardhat.config.ts`.

## 14. Anti Patterns

### Anti-Pattern 1: JavaScript Config in Production
**Why wrong**: No type safety; typos in config keys not caught at compile time.
**Correct alternative**: Use `hardhat.config.ts` with `HardhatUserConfig` type.

### Anti-Pattern 2: beforeEach for Stateful Setup
**Why wrong**: Runs setup before every test; slow for large suites.
**Correct alternative**: Use `loadFixture(deployFixture)` which snapshots state and reuses.

### Anti-Pattern 3: Hardcoded Addresses in Scripts
**Why wrong**: Addresses differ per chain; hardcoded values break multi-chain deploys.
**Correct alternative**: Use `namedAccounts` and `getNamedAccounts()` to fetch per-chain addresses.

### Anti-Pattern 4: Deploy Without Verify
**Why wrong**: Unverified contracts are opaque; users cannot audit source.
**Correct alternative**: Always include `verify` step in deployment script; abort if verification fails.

### Anti-Pattern 5: No Mainnet Fork for Integration Tests
**Why wrong**: Unit tests with mocked protocols do not catch real integration issues.
**Correct alternative**: Add `fork/` test directory with mainnet fork tests for real protocol integration.

### Anti-Pattern 6: No Cache in CI
**Why wrong**: Every CI run recompiles all contracts; slow and wastes compute.
**Correct alternative**: Cache `node_modules` and `cache/` directories in CI.

## 15. Performance Rules

- Always use `loadFixture` for test setup; avoids running setup per test.
- Always cache `node_modules` and `cache/` in CI.
- Always run unit tests in parallel (`--parallel` flag) when tests do not share state.
- Always configure `evmVersion` to match target chain; avoid unnecessary features.
- Always use `solidity` optimizer with explicit `runs` setting; `runs: 200` for balanced, `runs: 1` for max deployment gas optimization.
- Never include `console.sol` imports in production contracts; stripped but adds compile overhead.
- Always skip contracts without changes via Hardhat's incremental compilation.
- Always use `typechain` types for contract interactions; avoids runtime ABI lookups.

## 16. Security Rules

- Never commit `.env` with `PRIVATE_KEY` to git; use `.env.example` with placeholders.
- Never expose `PRIVATE_KEY` in frontend code.
- Always use `process.env.PRIVATE_KEY` in config with validation.
- Always validate chain ID matches expected before deployment.
- Always verify contracts on Etherscan post-deployment.
- Always use `hardhat-upgrades` for proxy deployment; never author custom proxy logic.
- Always run `solidity-coverage` and gate on >90%.
- Always run Slither alongside Hardhat tests in CI.

## 17. Testing Strategy

- Unit tests in `test/unit/` for individual contract logic.
- Integration tests in `test/integration/` for multi-contract interaction.
- Fork tests in `test/fork/` for mainnet fork integration with real protocols.
- Use `loadFixture` for state setup in all tests.
- Use chai-matchers for assertions: `expect().to.emit()`, `expect().to.be.revertedWithCustomError()`.
- Use network-helpers for time manipulation: `time.increase(3600)`, `setNextBlockTimestamp(ts)`.
- Use `impersonateAccount` to test as arbitrary addresses (e.g., impersonate a whale to fund test accounts).
- Gas tests via `hardhat-gas-reporter` per PR; track regression.
- Coverage via `solidity-coverage` per PR; gate on >90%.
- Mainnet fork tests in nightly CI job to catch integration regressions.

## 18. Documentation Standards

- Document `hardhat.config.ts` with comments explaining each network and account config.
- Document each custom task in `tasks/README.md` with usage examples.
- Document deployment procedure in `docs/deployment-guide.md` per chain.
- Document upgrade procedure in `docs/upgrade-guide.md` with storage layout compatibility.
- Document gas benchmarks in `docs/gas-benchmarks.md` per function.
- Document test strategy in `docs/testing.md` with fixture and fork test patterns.
- Document CI workflow in `.github/workflows/README.md`.
- Document environment variables in `.env.example` with descriptions.

## 19. Code Review Checklist

- [ ] Config in TypeScript (`hardhat.config.ts`).
- [ ] Explicit Solidity compiler versions in config.
- [ ] `namedAccounts` configured for deployer, admin, treasury.
- [ ] `hardhat-verify` configured for all target chains.
- [ ] Tests use `loadFixture` for state setup.
- [ ] Tests use chai-matchers for assertions.
- [ ] Revert tests use `revertedWithCustomError`.
- [ ] Mainnet fork tests in `test/fork/`.
- [ ] Custom tasks defined in `tasks/` and imported in config.
- [ ] Deployment scripts include verification step.
- [ ] `hardhat-upgrades` used for proxy deployment.
- [ ] Gas reporter runs in CI.
- [ ] Coverage runs in CI with >90% gate.
- [ ] CI caches `node_modules` and `cache/`.
- [ ] `.env.example` exists with placeholders; `.env` is gitignored.
- [ ] `PRIVATE_KEY` loaded from env, never hardcoded.

## 20. Refactoring Checklist

- [ ] Convert `hardhat.config.js` to `hardhat.config.ts`.
- [ ] Replace `beforeEach` setup with `loadFixture`.
- [ ] Extract hardcoded addresses to `namedAccounts`.
- [ ] Add `hardhat-verify` to deployment scripts.
- [ ] Add `hardhat-gas-reporter` to CI.
- [ ] Add `solidity-coverage` to CI with gate.
- [ ] Move custom tasks from inline definitions to `tasks/` directory.
- [ ] Add mainnet fork tests for protocol integrations.
- [ ] Replace string revert assertions with `revertedWithCustomError`.
- [ ] Extract test helpers to `test/helpers/`.

## 21. Deployment Checklist

- [ ] `hardhat.config.ts` configured with target network RPC and accounts.
- [ ] `ETHERSCAN_API_KEY` set in env for target chain.
- [ ] `namedAccounts` resolve to correct addresses on target chain.
- [ ] Deployment script dry-run on `hardhat` network passes.
- [ ] Deployment script run on `localhost` (via `hardhat node`) passes.
- [ ] Mainnet fork test of deployment script passes.
- [ ] `PRIVATE_KEY` for deployer loaded from env, not hardcoded.
- [ ] Deployer account has sufficient ETH for gas.
- [ ] Gas estimate via `hardhat-gas-reporter` reviewed.
- [ ] Contracts deployed via `npx hardhat run scripts/deploy.ts --network <chain>`.
- [ ] Verification via `npx hardhat verify --network <chain> <address> <constructorArgs>`.
- [ ] Deployment addresses recorded in `deployments/<chain>.json`.
- [ ] Multi-sig set as owner/admin if applicable.
- [ ] Post-deployment verification: call `name()`, `symbol()`, `owner()`.
- [ ] Frontend ABI updated with deployed addresses.

## 22. Production Checklist

- [ ] Contracts verified on Etherscan with standard JSON input.
- [ ] Admin role held by multi-sig (Gnosis Safe).
- [ ] Deployment addresses documented in `deployments/<chain>.json`.
- [ ] Gas benchmarks documented per function.
- [ ] Coverage >90% in CI.
- [ ] Gas reporter runs per PR with regression alert.
- [ ] Mainnet fork tests run nightly.
- [ ] Slither runs in CI with no high/medium findings.
- [ ] `.env` not committed; `.env.example` up to date.
- [ ] CI caches `node_modules` and `cache/`.
- [ ] Deployment script tested on `localhost` before mainnet.
- [ ] Upgrade procedure documented with storage layout.
- [ ] Pause capability tested.
- [ ] Monitoring: contract balance, TVL, transaction volume, error rate.
- [ ] Alerts: large withdrawal, pause triggered, role change.
- [ ] Incident response runbook documented.

## 23. Logging Strategy

- `console.log` in Solidity contracts for dev debugging on Hardhat network only.
- `console.log` stripped on non-Hardhat networks; never relied on for production.
- Deployment scripts log: contract name, deployed address, tx hash, gas used, verification status.
- Test logs: `describe`/`it` names, fixture setup, gas per test.
- CI logs: test results, coverage report, gas report, Slither findings.
- Never log `PRIVATE_KEY` or any secret.
- Log deployment addresses to `deployments/<chain>.json` as JSON for programmatic access.
- Log gas benchmarks to `docs/gas-benchmarks.md` per PR for regression tracking.
- Use structured logging (JSON) in deployment scripts for aggregation.
- Document event taxonomy in `docs/events.md` for off-chain consumers.

## 24. Monitoring Strategy

- Monitor contract balance: alert on >20% drop in 1 hour.
- Monitor TVL: alert on >10% drop in 1 hour.
- Monitor transaction volume: alert on >3x baseline.
- Monitor error rate: alert on >1% revert rate.
- Monitor pause status: alert immediately if `Paused` event emitted.
- Monitor role changes: alert on `RoleGranted`/`RoleRevoked` events.
- Monitor upgrade events: alert on `Upgraded` event.
- Monitor gas usage: alert if average gas per function >120% of benchmark in `docs/gas-benchmarks.md`.
- Monitor deployment script execution time: alert if >2x baseline.
- Monitor CI test duration: alert if >2x baseline.

## 25. Error Handling

- Deployment script errors: abort, log contract that failed, log tx hash if available, exit non-zero.
- Verification errors: retry once with different API endpoint; if still failing, log and continue (verification can be retried manually).
- Test failures: mocha reports failure with stack trace; Hardhat provides Solidity stack traces for reverts.
- Mainnet fork errors: Alchemy/Infura rate limit → backoff and retry; block number out of range → use latest.
- Gas estimation errors: re-run with higher gas limit or check for revert in `eth_call`.
- `PRIVATE_KEY` missing: abort with clear error message; never default to a hardcoded key.
- Network errors: retry with exponential backoff; failover to backup RPC if configured.
- Proxy deployment errors: `hardhat-upgrades` validates storage layout; abort if layout incompatible.
- Coverage errors: `solidity-coverage` may fail on complex contracts; document and exclude with reason.
- CI cache errors: fall back to fresh install; alert if cache miss rate >50%.

## 26. Examples

### Example 1: hardhat.config.ts

```typescript
import { HardhatUserConfig } from 'hardhat/config';
import '@nomicfoundation/hardhat-toolbox';
import '@openzeppelin/hardhat-upgrades';
import 'hardhat-deploy';
import './tasks/deploy';
import './tasks/verify';
import * as dotenv from 'dotenv';

dotenv.config();

const config: HardhatUserConfig = {
  solidity: {
    compilers: [
      { version: '0.8.20', settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: 'paris' } },
    ],
  },
  networks: {
    hardhat: { chainId: 31337 },
    hardhatFork: {
      chainId: 31337,
      forking: {
        url: process.env.ALCHEMY_RPC || '',
        blockNumber: 18000000,
      },
    },
    localhost: { url: 'http://127.0.0.1:8545' },
    mainnet: {
      url: `https://eth-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY || '0x0'],
    },
    sepolia: {
      url: `https://eth-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY || '0x0'],
    },
  },
  namedAccounts: {
    deployer: 0,
    admin: 1,
    treasury: '0x1234567890123456789012345678901234567890',
  },
  etherscan: {
    apiKey: {
      mainnet: process.env.ETHERSCAN_API_KEY || '',
      sepolia: process.env.ETHERSCAN_API_KEY || '',
    },
  },
  gasReporter: { enabled: true, currency: 'USD' },
};

export default config;
```

### Example 2: Fixture-Based Test

```typescript
import { expect } from 'chai';
import { ethers, network } from 'hardhat';
import { loadFixture } from '@nomicfoundation/hardhat-network-helpers';
import { time } from '@nomicfoundation/hardhat-network-helpers';

async function deployVaultFixture() {
  const [deployer, admin, user, attacker] = await ethers.getSigners();
  const Token = await ethers.getContractFactory('TestToken');
  const token = await Token.deploy();
  await token.waitForDeployment();
  const Vault = await ethers.getContractFactory('Vault');
  const vault = await Vault.deploy(await token.getAddress());
  await vault.waitForDeployment();
  await token.mint(user.address, ethers.parseEther('1000'));
  return { vault, token, deployer, admin, user, attacker };
}

describe('Vault', () => {
  describe('deposit', () => {
    it('increases user balance', async () => {
      const { vault, token, user } = await loadFixture(deployVaultFixture);
      await token.connect(user).approve(await vault.getAddress(), ethers.parseEther('100'));
      await vault.connect(user).deposit(ethers.parseEther('100'));
      expect(await vault.balances(user.address)).to.equal(ethers.parseEther('100'));
    });

    it('reverts on zero amount', async () => {
      const { vault, user } = await loadFixture(deployVaultFixture);
      await expect(vault.connect(user).deposit(0))
        .to.be.revertedWithCustomError(vault, 'ZeroAmount');
    });
  });

  describe('withdraw with time lock', () => {
    it('reverts before unlock time', async () => {
      const { vault, token, user } = await loadFixture(deployVaultFixture);
      await token.connect(user).approve(await vault.getAddress(), ethers.parseEther('100'));
      await vault.connect(user).deposit(ethers.parseEther('100'));
      await expect(vault.connect(user).withdraw(ethers.parseEther('100')))
        .to.be.revertedWithCustomError(vault, 'LockNotExpired');
    });

    it('succeeds after unlock time', async () => {
      const { vault, token, user } = await loadFixture(deployVaultFixture);
      await token.connect(user).approve(await vault.getAddress(), ethers.parseEther('100'));
      await vault.connect(user).deposit(ethers.parseEther('100'));
      await time.increase(3600 * 24 * 7); // 1 week
      await expect(vault.connect(user).withdraw(ethers.parseEther('100')))
        .to.emit(vault, 'Withdrawal')
        .withArgs(user.address, ethers.parseEther('100'));
    });
  });
});
```

### Example 3: Deployment Script with Verification

```typescript
import { ethers, network, run } from 'hardhat';

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`Deploying with ${deployer.address} on ${network.name}`);

  const Token = await ethers.getContractFactory('ACMEToken');
  const token = await Token.deploy(deployer.address, ethers.parseEther('1000000'));
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log(`Token deployed to ${tokenAddress}`);

  const Vault = await ethers.getContractFactory('Vault');
  const vault = await Vault.deploy(tokenAddress);
  await vault.waitForDeployment();
  const vaultAddress = await vault.getAddress();
  console.log(`Vault deployed to ${vaultAddress}`);

  // Wait for block confirmations before verifying
  await token.deploymentTransaction()?.wait(5);
  await vault.deploymentTransaction()?.wait(5);

  if (network.name !== 'hardhat' && network.name !== 'localhost') {
    console.log('Verifying contracts on Etherscan...');
    try {
      await run('verify:verify', {
        address: tokenAddress,
        constructorArguments: [deployer.address, ethers.parseEther('1000000')],
      });
      console.log('Token verified');
    } catch (e) {
      console.error('Token verification failed:', e);
    }
    try {
      await run('verify:verify', {
        address: vaultAddress,
        constructorArguments: [tokenAddress],
      });
      console.log('Vault verified');
    } catch (e) {
      console.error('Vault verification failed:', e);
    }
  }

  console.log('Deployment complete');
  console.log(JSON.stringify({ tokenAddress, vaultAddress, network: network.name }, null, 2));
}

main().catch((e) => { console.error(e); process.exit(1); });
```

## 27. Common Mistakes

### Mistake 1: JavaScript Config in Production
**What**: Using `hardhat.config.js` instead of `.ts`.
**Why wrong**: No type safety; typos in config keys not caught at compile time.
**How to avoid**: Use `hardhat.config.ts` with `HardhatUserConfig` type; CI fails on TS errors.

### Mistake 2: beforeEach for Stateful Setup
**What**: Using `beforeEach(async () => { /* deploy contracts */ })` in test suite.
**Why wrong**: Runs setup before every test; slow for large suites.
**How to avoid**: Use `loadFixture(deployFixture)` which snapshots state and reuses across tests in the same `describe`.

### Mistake 3: Hardcoded Addresses in Scripts
**What**: `const admin = '0xabc...'` in deployment script.
**Why wrong**: Addresses differ per chain; hardcoded values break multi-chain deploys.
**How to avoid**: Use `namedAccounts` in config and `getNamedAccounts()` in scripts.

### Mistake 4: Deploy Without Verify
**What**: Deployment script ends after `contract.deploy()` without verification.
**Why wrong**: Unverified contracts are opaque; users cannot audit source.
**How to avoid**: Always include `run('verify:verify', { address, constructorArguments })` step; abort if verification fails for mainnet deploys.

### Mistake 5: No Mainnet Fork for Integration Tests
**What**: Integration tests with mocked protocol contracts.
**Why wrong**: Mocks do not catch real integration issues (e.g., Uniswap V3 fee tiers, Aave interest rate models).
**How to avoid**: Add `test/fork/` directory with mainnet fork tests using real protocol contracts.

### Mistake 6: No CI Cache
**What**: CI runs `npm install` and `npx hardhat compile` from scratch on every run.
**Why wrong**: Every CI run recompiles all contracts; slow (5+ minutes) and wastes compute.
**How to avoid**: Cache `node_modules` and `cache/` directories in CI; use `actions/cache@v3`.

## 28. Professional Workflow

1. Initialize project: `npm init -y; npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox`.
2. Author `hardhat.config.ts` with Solidity versions, networks, namedAccounts, etherscan config.
3. Author contracts in `contracts/` with explicit pragma and NatSpec.
4. Write unit tests in `test/unit/` using `loadFixture` for state setup.
5. Write integration tests in `test/integration/` for multi-contract interaction.
6. Write fork tests in `test/fork/` for mainnet protocol integration.
7. Configure `hardhat-gas-reporter` and `solidity-coverage` in CI.
8. Configure Slither in CI for static analysis.
9. Author deployment script in `scripts/deploy.ts` with verification step.
10. Author custom tasks in `tasks/` for project-specific operations.
11. Test deployment on `localhost` via `npx hardhat node`.
12. Test deployment on `sepolia` testnet.
13. Deploy to mainnet via `npx hardhat run scripts/deploy.ts --network mainnet`.
14. Verify contracts on Etherscan via script step.
15. Document deployment addresses in `deployments/mainnet.json`.

## 29. Response Style

- Always specify Hardhat version and ethers.js version (v6) in examples.
- Always use TypeScript for config and scripts.
- Always use `loadFixture` for test state setup.
- Always use chai-matchers for assertions; never raw chai.
- Always use `revertedWithCustomError` for revert tests with custom errors.
- Always include verification step in deployment examples.
- Always cite the Hardhat documentation when introducing a new feature.
- Always flag gas implications of suggested patterns.

## 30. Output Format

- Every config file (`hardhat.config.ts`) includes comments explaining each section.
- Every test file uses `loadFixture` for setup.
- Every deployment script includes verification step.
- Every custom task is defined in `tasks/` and imported in config.
- Every CI workflow includes cache, coverage, gas report, and Slither.
- Every code example is syntactically valid TypeScript.
- Every `.env.example` lists all required env vars with descriptions.
- Every `README.md` includes: install, build, test, deploy, verify instructions.
- Every commit message follows conventional commits: `feat(contracts):`, `fix(test):`, `docs(deploy):`.
- Every release includes a `CHANGELOG.md` entry with breaking changes, new features, bug fixes, and upgrade notes.
