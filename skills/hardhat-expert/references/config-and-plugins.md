# Hardhat 3 Configuration and Plugins

## 1. Config structure

```ts
import hardhatToolboxViemPlugin from "@nomicfoundation/hardhat-toolbox-viem";
import { configVariable, defineConfig } from "hardhat/config";

export default defineConfig({
  plugins: [hardhatToolboxViemPlugin],
  paths: { sources: "contracts", tests: "test", artifacts: "artifacts", cache: "cache" },
  solidity: { /* see section 2 */ },
  networks: { /* see section 3 */ },
  verify: { etherscan: { apiKey: configVariable("ETHERSCAN_API_KEY") } },
  test: { solidity: { /* see testing.md */ } },
  ignition: { /* see ignition-deployments.md */ },
});
```

- The config file is an ES module (`hardhat.config.ts` or `.js`/`.mts`/`.mjs`); `package.json` has `"type": "module"`.
- Feature plugins are listed in `plugins`; a plugin that is imported but not listed triggers a warning.
- `paths` accepts `sources` (string, array or object), `tests` (string or object with per-runner paths such as `solidity`), `cache` and `artifacts`; Ignition adds `paths.ignition`.
- `defaultChainType` sets the chain type when a network does not specify one.

## 2. Solidity and build profiles

`solidity` can be a version string, an array of versions, one compiler object, a multi-version object, or an object with `profiles`:

```ts
solidity: {
  profiles: {
    default: { version: "0.8.38" },
    production: {
      version: "0.8.38",
      settings: { optimizer: { enabled: true, runs: 200 }, viaIR: false },
    },
  },
  npmFilesToBuild: ["@openzeppelin/contracts/token/ERC20/ERC20.sol"],
}
```

- Build profiles named `default` and `production` exist by convention; `hardhat build --build-profile production` (global option `--build-profile`) selects one. `hardhat ignition deploy` builds with `production` unless told otherwise.
- `settings` is the solc standard-JSON settings object (optimizer, `evmVersion`, `viaIR`, `outputSelection`, ...).
- Compiler entries accept `version`, `settings`, an optional `path` to a local solc and `preferWasm`.
- `npmFilesToBuild` compiles specific files from npm dependencies so their artifacts are available (for example to deploy a library contract from `node_modules`).
- The `solidity` config also accepts `isolated` and `splitTestsCompilation`; check the current docs before relying on them.
- Import npm packages with their package path (`@openzeppelin/contracts/...`); Foundry-style `remappings.txt` files are honored.

## 3. Networks

Two network types:

```ts
networks: {
  hardhatMainnet: { type: "edr-simulated", chainType: "l1" },
  hardhatOp: { type: "edr-simulated", chainType: "op" },
  mainnetFork: {
    type: "edr-simulated",
    chainType: "l1",
    forking: { url: configVariable("MAINNET_RPC_URL"), blockNumber: 21_000_000 },
  },
  sepolia: {
    type: "http",
    chainType: "l1",
    url: configVariable("SEPOLIA_RPC_URL"),
    accounts: [configVariable("SEPOLIA_PRIVATE_KEY")],
  },
}
```

`edr-simulated` options: `accounts`, `chainId`, `hardfork`, `blockGasLimit`, `initialBaseFeePerGas`, `initialDate`, `allowUnlimitedContractSize`, `allowBlocksWithSameTimestamp`, `coinbase`, `forking` (`url`, `blockNumber`, `enabled`, `httpHeaders`), `mining` (`auto`, `interval`, `mempool.order`), `loggingEnabled`, `throwOnCallFailures`, `throwOnTransactionFailures`, `gas`, `gasPrice`, `gasMultiplier`.

`http` options: `url` (required), `accounts` (`"remote"`, an array of values, or an HD object with `mnemonic`, `count`, `initialIndex`, `passphrase`, `path`), `chainId`, `chainType`, `from`, `gas`, `gasPrice`, `gasMultiplier`, `httpHeaders`, `timeout`.

- Use `accounts: [configVariable("NAME")]` for a single deployer key and `accounts: "remote"` when the node holds the accounts.
- A mnemonic is also a secret: reference it with `configVariable`, not a literal.
- Choose the network per run with the global option: `npx hardhat test --network hardhatMainnet`, `npx hardhat run scripts/x.ts --network sepolia`, `npx hardhat ignition deploy ... --network sepolia`.
- Connect in code: `await network.create()` (default network), `network.create("sepolia")`, or `network.create({ network: "hardhatOp", chainType: "op" })`.
- `chainDescriptors` can describe custom chains (hardfork history, block explorers) for verification and chain-type behavior.

## 4. Secrets: configVariable and the keystore

```ts
url: configVariable("SEPOLIA_RPC_URL"),
accounts: [configVariable("SEPOLIA_PRIVATE_KEY")],
```

```bash
npx hardhat keystore set SEPOLIA_PRIVATE_KEY      # prompts for the value, encrypts it with a password
npx hardhat keystore list
npx hardhat keystore get SEPOLIA_PRIVATE_KEY
npx hardhat keystore delete SEPOLIA_PRIVATE_KEY
npx hardhat keystore rename OLD_NAME NEW_NAME
npx hardhat keystore path
npx hardhat keystore change-password
```

- Resolution order: environment variable, then the development keystore (`--dev` flag on keystore commands), then the production keystore. In CI the keystore is skipped, so define an environment variable for each variable the job needs.
- During `hardhat test` only the development keystore is consulted, so tests do not prompt for the production password.
- A `configVariable("NAME", "default")` form supplies a default for non-sensitive values; do not use it for secrets.
- Values are resolved lazily, when a connection or task needs them.
- Keep `.env` files out of version control; if a team uses one locally, load it into the shell outside the repository's tracked files.

## 5. Plugins and versions

Versions on npm at the time of verification (2026-10):

| Package | Version | Role |
|---|---|---|
| `hardhat` | 3.21.2 | Core: build, test, run, node, clean, coverage, gas stats, Solidity tests |
| `@nomicfoundation/hardhat-toolbox-viem` | 5.0.7 | Bundle: viem, viem assertions, Node test runner, Ignition (viem), verify, keystore, network helpers |
| `@nomicfoundation/hardhat-toolbox-mocha-ethers` | 4.0.0 | Bundle: ethers, Mocha, chai matchers, TypeChain, Ignition (ethers), verify, keystore, network helpers |
| `@nomicfoundation/hardhat-ignition` | 3.1.9 | Declarative deployments |
| `@nomicfoundation/hardhat-ignition-viem` / `-ethers` | 3.1.6 | Ignition helper on the connection (`ignition.deploy`) |
| `@nomicfoundation/hardhat-keystore` | 3.1.2 | Encrypted secrets store |
| `@nomicfoundation/hardhat-verify` | 3.1.4 | Etherscan, Blockscout and Sourcify verification |
| `@nomicfoundation/hardhat-viem` | 3.1.0 | viem clients and typed contracts |
| `@nomicfoundation/hardhat-viem-assertions` | 3.1.5 | `viem.assertions` |
| `@nomicfoundation/hardhat-node-test-runner` | 3.1.2 | `hardhat test nodejs` |
| `@nomicfoundation/hardhat-ethers` | 4.2.2 | ethers v6 provider and signers |
| `@nomicfoundation/hardhat-mocha` | 4.0.1 | `hardhat test mocha` |
| `@nomicfoundation/hardhat-ethers-chai-matchers` | 3.0.13 | chai matchers for ethers |
| `@nomicfoundation/hardhat-typechain` | 3.1.3 | TypeChain types |
| `@nomicfoundation/hardhat-network-helpers` | 3.0.12 | `networkHelpers` (time, mine, balances, fixtures, snapshots) |

- A toolbox declares the individual plugins as peer dependencies; `hardhat --init` installs them. Register only the toolbox in `plugins`.
- Install a single plugin on its own (for example `hardhat-verify` in a minimal project) with `npm install --save-dev <package>` and add it to `plugins`.
- Plugin authors extend config and the connection through type extensions and hook handlers; see the plugin authoring section of the Hardhat docs.

## 6. Core tasks

| Command | Purpose |
|---|---|
| `npx hardhat --init` | Create a project from a template (viem, Mocha and ethers, minimal) |
| `npx hardhat build` | Compile contracts and Solidity tests (`--force`, `--quiet`, `--no-tests`, `--no-contracts`) |
| `npx hardhat test [files]` | Run all tests; subtasks `solidity`, `nodejs`, `mocha`; `--grep`, `--grep-exclude`, `--no-compile`, `--coverage`, `--gas-stats` |
| `npx hardhat run <script> [--network <name>]` | Run a script after compiling |
| `npx hardhat node` | JSON-RPC server (port 8545; `--fork`, `--fork-block-number`, `--hostname`, `--chain-type`) |
| `npx hardhat clean` | Delete cache and artifacts |
| `npx hardhat ignition ...` | Deployments (see ignition-deployments.md) |
| `npx hardhat verify ...` | Contract verification |
| `npx hardhat keystore ...` | Secrets |

## 7. Verification

```bash
npx hardhat verify --network sepolia 0xDeployedAddress "constructor arg 1"      # Etherscan
npx hardhat verify blockscout --network sepolia 0xDeployedAddress               # Blockscout
```

```ts
import hre from "hardhat";
import { verifyContract } from "@nomicfoundation/hardhat-verify/verify";

await verifyContract(
  { address: "0xDeployedAddress", constructorArgs: ["constructor arg 1"], provider: "etherscan" },
  hre,
);
```

- Etherscan config: `verify: { etherscan: { apiKey: configVariable("ETHERSCAN_API_KEY") } }`; Blockscout keys are optional (`verify.blockscout.apiKey`).
- The compiler settings used for verification are those of the build that produced the artifacts; deploy and verify from the same profile.

## 8. Migrating from Hardhat 2

Hardhat 2 remains available on npm under the `hh2` tag (2.29.1 at the time of verification). Main differences when moving to 3:

| Hardhat 2 | Hardhat 3 |
|---|---|
| CommonJS or TypeScript config, `HardhatUserConfig`, side-effect plugin imports | ESM config with `defineConfig` and a `plugins` array |
| `@nomicfoundation/hardhat-toolbox` | `hardhat-toolbox-viem` or `hardhat-toolbox-mocha-ethers` |
| `import { ethers } from "hardhat"` global environment | `const { ethers } = await network.create()` (or `viem`) |
| `loadFixture` from `hardhat-network-helpers` imports | `networkHelpers.loadFixture` on the connection |
| `mnemonic` or private keys from `process.env` | `configVariable` plus the keystore |
| Single `solidity` version and optimizer block | `solidity.profiles` with `default` and `production` |
| `hardhat` network with `hardhat_*` settings | `edr-simulated` network entries |
| Ignition for Hardhat 2 (state in `ignition/deployments`) | Ignition 3 (`ignition migrate` converts existing deployment artifacts to the Hardhat 3 format) |
| `hardhat verify` Etherscan config under `etherscan` | `verify.etherscan` block |

Migration steps: add `"type": "module"`, convert the config, switch to a toolbox, replace global environment access with `network.create()`, move secrets to `configVariable`, run `npx hardhat build && npx tsc --noEmit`, then run the tests.
