# Foundry Testing and Cheatcodes

Cheatcodes are called on the `vm` object that `Test` and `Script` from forge-std provide. Signatures below were checked against the Foundry cheatcode specification (`crates/cheatcodes/assets/cheatcodes.json`); the authoritative list for the installed version is `lib/forge-std/src/Vm.sol`.

## 1. Caller, balance and chain state

| Cheatcode | Effect |
|---|---|
| `vm.prank(address)` | Sets `msg.sender` for the next call. `vm.prank(sender, origin)` also sets `tx.origin`. |
| `vm.startPrank(address)` / `vm.stopPrank()` | Same, for every call until stopped. |
| `vm.deal(address, uint256)` | Sets an account's ETH balance (overwrites, does not add). |
| `hoax(address, uint256)` / `startHoax(...)` | forge-std helpers: prank plus deal in one call. |
| `deal(address token, address to, uint256 amount)` | forge-std helper for ERC-20 balances; works for most tokens by locating the balance slot. |
| `vm.warp(uint256)` / `vm.roll(uint256)` | Set `block.timestamp` / `block.number`. `skip(uint256)` (forge-std) advances time. |
| `vm.fee(uint256)`, `vm.txGasPrice(uint256)`, `vm.chainId(uint256)`, `vm.coinbase(address)`, `vm.prevrandao(bytes32)` | Set block and transaction environment. |
| `vm.store(address, bytes32 slot, bytes32 value)` / `vm.load(address, bytes32 slot)` | Raw storage write and read. |
| `vm.etch(address, bytes code)` | Replace runtime code at an address. |
| `vm.setNonce(address, uint64)` / `vm.getNonce(address)` | Account nonce control. |
| `vm.label(address, string)` | Names an address in traces. `makeAddr("name")` creates and labels one. |
| `vm.snapshotState()` / `vm.revertToState(uint256)` | Save and restore EVM state within a test. |

## 2. Expecting reverts, events and calls

```solidity
vm.expectRevert();                                              // any revert
vm.expectRevert(bytes4 selector);                               // custom error without arguments
vm.expectRevert(abi.encodeWithSelector(Err.selector, a, b));    // error with arguments
vm.expectRevert("message");                                     // revert string
vm.expectPartialRevert(Err.selector);                           // selector only, arguments ignored

vm.expectEmit(true, true, false, true);                         // topic1, topic2, topic3, data
emit Transfer(from, to, amount);                                // the expected event, then the call
token.transfer(to, amount);

vm.expectEmit(true, false, false, true, address(vault));        // also check the emitter
vm.expectCall(address(oracle), abi.encodeCall(Oracle.price, (asset)));
vm.mockCall(address(oracle), abi.encodeCall(Oracle.price, (asset)), abi.encode(2000e8));
```

- `vm.expectRevert` applies to the next call. Cheatcode calls in between (such as `vm.prank`) do not consume it, but any other external call does, including a view call evaluated as an argument.
- `expectRevert` overloads also exist with an `address` (revert must originate from that contract) and a `uint64` count; check `Vm.sol` before relying on them.
- `vm.expectEmit()` with no arguments checks all topics and data. The four booleans select which of topics 1 to 3 and the data are compared (topic 0, the event signature, is always compared).
- `vm.mockCallRevert`, `vm.clearMockedCalls` and `vm.mockFunction` complete the mocking set.

## 3. Fuzz tests

A test function with parameters is a fuzz test. Foundry generates values and shrinks failures.

```solidity
function testFuzz_Transfer(address to, uint256 amount) public {
    vm.assume(to != address(0) && to != address(token));
    amount = bound(amount, 0, token.balanceOf(alice));
    vm.prank(alice);
    token.transfer(to, amount);
    assertEq(token.balanceOf(to), amount);
}
```

- `bound(x, min, max)` maps any value into a range without rejecting inputs; prefer it for ranges.
- `vm.assume(cond)` rejects inputs; many rejections abort the test (`max_test_rejects`, default 65536). forge-std adds `assumeNotZeroAddress`, `assumeNotPrecompile`, `assumeNotForgeAddress`, `assumePayable` and `assumeAddressIsNot` for address inputs.
- `vm.assumeNoRevert()` discards a fuzz run if the next call reverts, instead of failing it.
- Configuration in `[fuzz]`: `runs` (256 by default), `max_test_rejects`, `seed`, `dictionary_weight`, `include_storage`, `include_push_bytes`, `show_logs`, `timeout`, `failure_persist_dir`. CLI: `--fuzz-runs`, `--fuzz-seed`.
- Failing inputs are persisted under `cache/fuzz` and replayed first on the next run; `forge test --rerun` re-runs only the tests that failed last time.

## 4. Invariant tests

Functions whose name starts with `invariant` are checked after each call in a random sequence of calls to the target contracts.

Target selection (forge-std `StdInvariant`, inherited by `Test`):
- `targetContract(address)`, `targetSelector(FuzzSelector)`, `targetSender(address)`, `targetInterface(FuzzInterface)`, `targetArtifact(string)`, `targetArtifactSelector(FuzzArtifactSelector)`.
- `excludeContract(address)`, `excludeSelector(FuzzSelector)`, `excludeSender(address)`, `excludeArtifact(string)`.
- With no explicit targets Foundry targets every contract deployed in `setUp`, which usually includes contracts you do not want called directly.

Configuration in `[invariant]`:

| Key | Meaning |
|---|---|
| `runs` | Number of call sequences (256 by default) |
| `depth` | Calls per sequence (500 by default) |
| `fail_on_revert` | Fail when a call reverts (false by default) |
| `call_override` | Override unsafe external calls to test for reentrancy (false by default) |
| `dictionary_weight` | Percent of inputs drawn from the dictionary of values seen in state and code |
| `include_storage`, `include_push_bytes` | Feed storage values and PUSH constants into the dictionary |
| `shrink_run_limit` | Maximum attempts to shrink a failing sequence |
| `max_assume_rejects` | Cap on `vm.assume` rejections |
| `timeout`, `failure_persist_dir`, `show_metrics` | Time limit, where failures are saved, call-metrics table |

Patterns:
- **Handler**: a contract exposing bounded actions, with actors created via `makeAddr`, ghost variables for expected state, and `vm.prank` inside the action. Register it with `targetContract` or `targetSelector`.
- **Ghost accounting**: track expected totals in the handler and assert equality with the system under test.
- **Bounded actions**: shape every input with `bound`; use a `try/catch` or a guard to skip impossible states rather than reverting.
- **Strict mode**: once handlers never revert unintentionally, set `fail_on_revert = true` in a dedicated profile so accidental reverts surface.
- **Fixed senders**: `targetSender(address)` restricts msg.sender to chosen addresses to model roles.

## 5. Fork tests

```solidity
function setUp() public {
    vm.createSelectFork(vm.rpcUrl("mainnet"), 21_000_000);   // alias from [rpc_endpoints], pinned block
}
```

- Alias form: `vm.createSelectFork("mainnet", blockNumber)`; both `createSelectFork(string)` and `createSelectFork(string,uint256)` exist.
- `vm.createFork`, `vm.selectFork(uint256)`, `vm.rollFork(uint256)` and `vm.makePersistent(address)` allow several forks in one test and keep a contract alive across `selectFork` calls.
- Command-line alternative: `forge test --fork-url <alias-or-url> --fork-block-number <n>`.
- Pin a block, read RPC URLs from `[rpc_endpoints]` (`${MAINNET_RPC_URL}`), and keep the default RPC cache for speed and rate limits.
- `vm.envOr("NAME", default)` gives a fallback when a variable is unset, so fork tests can skip: `if (!vm.envExists("MAINNET_RPC_URL")) vm.skip(true);`.

## 6. Environment, files and parsing

- `vm.envUint("NAME")`, `envAddress`, `envBool`, `envString`, `envBytes32` read environment variables; `vm.envOr("NAME", default)` supplies defaults. Use them for non-secret configuration such as chain parameters; do not read private keys this way.
- `vm.readFile`, `vm.writeFile`, `vm.projectRoot()` plus `stdJson`/`stdToml` helpers read config files; all file access is limited by `fs_permissions`.
- `vm.parseJsonUint`, `parseJsonAddress` and the `parseToml*` family decode typed values.
- `vm.ffi(string[])` runs an external command; it requires `ffi = true` and should stay off unless essential.

## 7. Gas, state diffs and logs

- `forge test --gas-report` prints per-function gas; `forge snapshot` writes `.gas-snapshot`, and `forge snapshot --check` fails when numbers change.
- `vm.startSnapshotGas("name")` / `vm.stopSnapshotGas()` record gas for a code section into a snapshot file.
- `vm.recordLogs()` and `vm.getRecordedLogs()` capture emitted logs for assertions on several events.
- `vm.startStateDiffRecording()` and `vm.stopAndReturnStateDiff()` return storage and balance changes of a call tree.
- `vm.record()` and `vm.accesses(address)` list storage slots read and written.

## 8. Tracing and debugging

- `-vv` shows logs, `-vvv` traces for failing tests, `-vvvv` traces for all tests (and setup traces for failures), `-vvvvv` setup traces for all tests.
- `console.log` from `forge-std/console.sol` prints inside tests and scripts.
- `forge test --match-test <name> --debug` opens the interactive debugger; `-vvvv` is usually enough.
- `forge inspect <Contract> storageLayout` prints slots for use with `vm.store`.
