# Hardhat Ignition Deployments

Hardhat Ignition (`@nomicfoundation/hardhat-ignition` 3.1.9, core `@nomicfoundation/ignition-core` 3.1.8) describes a deployment as futures in a module. It executes them in dependency order, journals each step, and resumes after a failure.

## 1. Module API

```ts
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("VaultModule", (m) => {
  const deployer = m.getAccount(0);
  const treasury = m.getParameter("treasury");              // required parameter, no default
  const paused = m.getParameter("paused", false);           // parameter with a default

  const vault = m.contract("Vault", [treasury], { from: deployer });
  m.call(vault, "setPaused", [paused], { id: "SetPaused", after: [vault] });

  return { vault };
});
```

| Method | Purpose |
|---|---|
| `m.contract(name, args?, options?)` | Deploy a contract; options: `id`, `after`, `libraries`, `value`, `from` |
| `m.library(name, options?)` | Deploy a library |
| `m.contractAt(name, address, options?)` | Attach to an existing contract |
| `m.call(future, fn, args?, options?)` | Send a transaction to a contract function; options: `id`, `after`, `value`, `from` |
| `m.staticCall(future, fn, args?, nameOrIndex?, options?)` | Read a value during the deployment |
| `m.readEventArgument(future, eventName, argName, options?)` | Read an event argument from a deployment or call |
| `m.send(id, to, value?, data?, options?)` | Send ether or raw data |
| `m.encodeFunctionCall(future, fn, args?, options?)` | Encode calldata (for proxies and initializers) |
| `m.getAccount(index)` | The configured account at an index |
| `m.getParameter(name, default?)` | A module parameter |
| `m.useModule(otherModule)` | Compose modules and use their returned futures |

- Futures have ids derived from the module id and contract name; set `id` explicitly when the same contract is deployed twice or the same function called more than once.
- Return the futures you want to use afterwards (`return { vault }`); `ignition.deploy` hands them back as typed contract instances.
- Module ids and future ids are persisted in the journal; renaming them after a live deployment makes Ignition treat the module as changed, so keep them stable.

## 2. Running a deployment

```bash
npx hardhat ignition deploy ignition/modules/Vault.ts                        # in-process network
npx hardhat ignition deploy ignition/modules/Vault.ts --network sepolia
npx hardhat ignition deploy ignition/modules/Vault.ts --network sepolia \
  --parameters ignition/parameters/sepolia.json --deployment-id sepolia-v1 --verify
```

`ignition/parameters/sepolia.json` is keyed by module id and holds non-secret values:

```json
{
  "VaultModule": {
    "treasury": "0x0000000000000000000000000000000000000001",
    "paused": false
  }
}
```

Options of `ignition deploy`: `--parameters <json file>`, `--deployment-id <id>`, `--default-sender <address>`, `--strategy <basic|create2>`, `--reset` (wipe existing state first), `--verify`, `--write-localhost-deployment`.

- Pass `--deployment-id` to name a deployment; repeated runs with the same id resume or extend it. Check `ignition deployments` for the ids in use.
- Deployments use the `production` build profile by default.
- Parameters are public: do not put keys or credentials in them. Account keys come from `configVariable` on the network.

## 3. State, journal and recovery

State lives in `ignition/deployments/<deploymentId>/`: a journal of every step, a map from future ids to deployed addresses, and the artifacts needed for verification. Inspect it with the commands below rather than editing it by hand.

Commands:

| Command | Purpose |
|---|---|
| `ignition status <deploymentId>` | Which futures succeeded, failed or are pending |
| `ignition deployments` | List deployment ids |
| `ignition transactions <deploymentId>` | Transactions of a deployment |
| `ignition wipe <deploymentId> <futureId>` | Reset one future so it can be rerun |
| `ignition track-tx <txHash> <deploymentId>` | Add a transaction missing from the journal (only when an error message asks for it) |
| `ignition verify <deploymentId>` | Verify the deployment's contracts on configured explorers (`--force`) |
| `ignition visualize <modulePath>` | HTML diagram of a module (`--no-open`) |
| `ignition migrate <deploymentId>` | Convert Hardhat 2 deployment artifacts to the Hardhat 3 format |

- Rerun the same command after a failure (timeout, underpriced transaction); Ignition continues from the journal.
- If module code changes in ways that conflict with the journal (reconciliation error), either revert the change, deploy a new module under a new deployment id, or wipe the affected future.
- Commit `ignition/deployments/` for live networks; the journal is the source of truth for addresses.

## 4. Configuration

```ts
export default defineConfig({
  plugins: [hardhatToolboxViemPlugin],
  ignition: {
    requiredConfirmations: 2,
    blockPollingInterval: 1_000,
    strategyConfig: { create2: { salt: "vault-v1" } },
  },
  networks: {
    sepolia: {
      type: "http",
      url: configVariable("SEPOLIA_RPC_URL"),
      accounts: [configVariable("SEPOLIA_PRIVATE_KEY")],
      ignition: { maxFeePerGasLimit: 50_000_000_000n, disableFeeBumping: false },
    },
  },
});
```

- Top-level `ignition` keys (from the deploy config): `blockPollingInterval`, `timeBeforeBumpingFees`, `maxFeeBumps`, `requiredConfirmations`, `disableFeeBumping`, `maxRetries`, `retryInterval`, plus `strategyConfig`.
- Per-network `ignition` keys: `maxFeePerGasLimit`, `maxFeePerGas`, `maxPriorityFeePerGas`, `gasPrice`, `disableFeeBumping`, `explorerUrl`, `maxRetries`, `retryInterval`.
- The `create2` strategy deploys through a CREATE2 factory for deterministic addresses; it needs `strategyConfig.create2.salt`. The default is `basic`.

## 5. Using Ignition in tests and scripts

```ts
import { network } from "hardhat";
import VaultModule from "../ignition/modules/Vault.js";

const { ignition } = await network.create();
const { vault } = await ignition.deploy(VaultModule, {
  parameters: { VaultModule: { treasury: "0x0000000000000000000000000000000000000001" } },
});
```

- With the viem toolbox `vault` is a typed viem contract (`vault.read...`, `vault.write...`); with the ethers toolbox it is a TypeChain-typed ethers contract.
- `deploy` options include `parameters`, `defaultSender`, `strategy`, `strategyConfig`, `deploymentId` and `displayUi`.
- Testing the module itself keeps production deployment and test setup identical.

## 6. Deployment safety

- Use a fresh deployer account per environment; transfer ownership to a multisig as a module step (`m.call(vault, "transferOwnership", [multisig])`) and read it back with `m.staticCall`.
- Simulate against a fork first: define an `edr-simulated` network with `forking` and run the same module there.
- Review the deployment folder (journal and address map) in the pull request that records the deployment.
- Verify with `--verify` or `ignition verify`; Etherscan keys come from `verify.etherscan.apiKey` with `configVariable`.

## 7. CI workflow (build and test only)

Deploying to a live network from CI is a separate, protected workflow; the job below only builds and tests.

```yaml
name: CI

permissions: {}

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - uses: actions/setup-node@v6
        with:
          node-version: 22
          cache: npm

      - run: npm ci
      - run: npx hardhat build
      - run: npx tsc --noEmit
      - run: npx hardhat test
```

For a protected deployment job, expose secrets with `env:` on the step (for example `SEPOLIA_RPC_URL`, `SEPOLIA_PRIVATE_KEY`), restrict it to a GitHub environment with required reviewers, and never interpolate `${{ ... }}` expressions directly into the `run:` script.
