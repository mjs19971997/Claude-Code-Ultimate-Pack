# Hardhat 3 Testing

## 1. Test layers

| Layer | Files | Command |
|---|---|---|
| Solidity tests | `*.t.sol` in `contracts/`, or any `.sol` file in `test/`; contracts with `test*` functions | `npx hardhat test solidity` |
| TypeScript, Node test runner (viem toolbox) | `test/*.ts` | `npx hardhat test nodejs` |
| TypeScript, Mocha and chai (ethers toolbox) | `test/*.ts` | `npx hardhat test mocha` |
| Everything | | `npx hardhat test` |

Useful flags: `--grep <pattern>`, `--grep-exclude <pattern>`, `--no-compile`, `--coverage`, `--gas-stats`, `--gas-stats-json <path>`, and for Solidity tests `--snapshot`, `--snapshot-check`, `--tolerance <percent>`.

## 2. Solidity tests

Tests use `forge-std` (install as a dev dependency; the official templates use `foundry-rs/forge-std#v1.17.0`). Any public function starting with `test` runs; functions with parameters are fuzz tests; `invariant*` functions are invariant tests.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.38;

import {Test} from "forge-std/Test.sol";
import {Counter} from "./Counter.sol";

contract CounterInvariantTest is Test {
    Counter counter;

    function setUp() public {
        counter = new Counter();
        targetContract(address(counter));
    }

    function invariant_OwnerNeverChanges() public view {
        assertEq(counter.owner(), address(this));
    }
}
```

Cheatcodes available through `vm` include `prank`, `startPrank`, `stopPrank`, `deal`, `warp`, `roll`, `expectRevert`, `expectEmit`, `store`, `load`, `assume` and `bound` (same semantics as in Foundry; see the foundry-expert skill for the catalogue).

Configuration lives under `test.solidity`, either directly or per profile:

```ts
test: {
  solidity: {
    fuzz: { runs: 1000, maxTestRejects: 65536, showLogs: false },
    invariant: { runs: 256, depth: 100, failOnRevert: false },
    forking: { url: configVariable("MAINNET_RPC_URL"), blockNumber: 21_000_000 },
  },
}
```

Available keys (from the Hardhat 3.21 type definitions):
- `fuzz`: `runs`, `maxTestRejects`, `seed`, `dictionaryWeight`, `includeStorage`, `includePushBytes`, `showLogs`, `timeout`, `failurePersistDir`, `failurePersistFile`.
- `invariant`: `runs`, `depth`, `failOnRevert`, `callOverride`, `dictionaryWeight`, `includeStorage`, `includePushBytes`, `shrinkRunLimit`, `timeout`, `failurePersistDir`.
- `forking`: `url`, `blockNumber`, `rpcEndpoints`.
- Environment: `from`, `txOrigin`, `initialBalance`, `blockBaseFeePerGas`, `coinbase`, `blockTimestamp`, `prevRandao`, `gasLimit`, `blockGasLimit`, `transactionGasCap`, `memoryLimit`, `isolate`.
- Permissions: `ffi` (boolean) and `fsPermissions` (`readFile`, `writeFile`, `readWriteFile`, `readDirectory`, `dangerouslyReadWriteDirectory`, `dangerouslyWriteDirectory`); grant the narrowest access a test needs.
- Per-profile form: `solidity: { profiles: { default: { fuzz: { runs: 256 } }, ci: { fuzz: { runs: 5000 } } } }`.

Leave `ffi` and `fsPermissions` unset unless a test needs them.

## 3. TypeScript tests with viem

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { network } from "hardhat";

describe("Counter", async function () {
  const { viem, networkHelpers } = await network.create();
  const publicClient = await viem.getPublicClient();

  it("counts increments", async function () {
    const counter = await viem.deployContract("Counter");
    await counter.write.incBy([4n]);
    assert.equal(await counter.read.x(), 4n);
    assert.ok((await publicClient.getBlockNumber()) > 0n);
  });
});
```

- Clients: `viem.getPublicClient()`, `viem.getWalletClients()`, `viem.getTestClient()`.
- Contracts: `viem.deployContract(name, args?, options?)`, `viem.getContractAt(name, address)`; calls are typed by ABI (`counter.read.x()`, `counter.write.incBy([3n], { account })`).
- Avoid `walletClient.writeContract` in tests; it has no ABI typing.
- Assertions (`viem.assertions`): `revert`, `revertWith`, `revertWithCustomError`, `revertWithCustomErrorWithArgs`, `emit`, `emitWithArgs`, `balancesHaveChanged`. The `*WithArgs` variants accept predicates `(value) => boolean` and `anyValue` from `@nomicfoundation/hardhat-toolbox-viem/predicates`.
- Pass unawaited promises to the assertion helpers.

## 4. TypeScript tests with ethers and Mocha

```ts
import { expect } from "chai";
import { network } from "hardhat";

const { ethers, networkHelpers } = await network.create();

describe("Counter", function () {
  async function deployCounter() {
    const counter = await ethers.deployContract("Counter");
    const [owner, alice] = await ethers.getSigners();
    return { counter, owner, alice };
  }

  it("reverts reset from a non-owner", async function () {
    const { counter, alice } = await networkHelpers.loadFixture(deployCounter);
    await expect(counter.connect(alice).reset())
      .to.be.revertedWithCustomError(counter, "Unauthorized")
      .withArgs(alice.address);
  });

  it("emits Increment", async function () {
    const { counter } = await networkHelpers.loadFixture(deployCounter);
    await expect(counter.inc()).to.emit(counter, "Increment").withArgs(1n);
  });
});
```

- Mocha does not await `describe` callbacks, so create the connection with top-level `await` at the top of the file.
- Signers: `ethers.getSigners()`, `ethers.getImpersonatedSigner(address)`; provider: `ethers.provider`.
- Matchers: `.to.emit`, `.to.be.revertedWith`, `.to.be.revertedWithCustomError(...).withArgs(...)`, `.to.revert(ethers)`, `.to.changeEtherBalance(ethers, account, amount)`, `.to.changeEtherBalances(ethers, [accounts], [amounts])`.
- Types come from TypeChain; run `npx hardhat build` before `tsc`.

## 5. networkHelpers

Available on every connection (`const { networkHelpers } = await network.create()`):

```ts
await networkHelpers.time.increase(3600);             // mine a block one hour later
await networkHelpers.time.increaseTo(timestamp);
const now = await networkHelpers.time.latest();
await networkHelpers.time.setNextBlockTimestamp(ts);
await networkHelpers.mine(5);
await networkHelpers.setBalance(address, 10n ** 18n);
await networkHelpers.impersonateAccount(address);
await networkHelpers.setPrevRandao(value);
await networkHelpers.setNextBlockBaseFeePerGas(baseFee);

const { counter } = await networkHelpers.loadFixture(deployCounter);   // named function
const snapshot = await networkHelpers.takeSnapshot();
await snapshot.restore();
```

Each `network.create()` is an isolated chain; fixtures snapshot and restore state within one connection.

## 6. Forking in TypeScript tests

Define a forking network in the config (see `config-and-plugins.md`) and connect to it: `await network.create("mainnetFork")`. Pin `blockNumber`, supply the RPC URL through `configVariable`, and use `networkHelpers.impersonateAccount` plus `setBalance` to act as existing holders.

## 7. Coverage and gas

- `npx hardhat test --coverage` collects coverage for Solidity and TypeScript tests; scope it with `npx hardhat test solidity --coverage`.
- `npx hardhat test --gas-stats` prints gas usage per function; `--gas-stats-json <path>` writes it to a file for CI comparison.
- `--snapshot` stores gas snapshots for Solidity tests and `--snapshot-check` fails when values drift beyond `--tolerance`.

## 8. Typechecking and CI

```bash
npx hardhat build && npx tsc --noEmit
npx hardhat test
```

Generated types are derived from artifacts, so build first. In CI define environment variables for every `configVariable` that a test network needs (the keystore is not used there); tests that run on `edr-simulated` networks without forking need none.
