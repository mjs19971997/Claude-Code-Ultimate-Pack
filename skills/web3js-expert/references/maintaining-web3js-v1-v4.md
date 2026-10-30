# Maintaining web3.js v1 and v4 Code

Reference for reading, debugging and safely keeping existing web3.js code until it is migrated. Verified by running web3 1.10.4 and web3 4.16.0 against a fake JSON-RPC server and by inspecting the installed packages (2026-10). web3.js is sunset and archived (see the main skill); nothing here is a reason to start new code on it.

## 1. Identify the version

| Signal | v1 (1.x) | v4 (4.x) |
|---|---|---|
| Import | `const Web3 = require('web3')` or `import Web3 from 'web3'` | `import { Web3 } from 'web3'` |
| Numbers from RPC | strings or JS numbers | `bigint` |
| Big numbers in code | `web3.utils.toBN`, `BN` methods | native `bigint` operators |
| Packages | `web3-eth`, `web3-utils`, `web3-core-*` (for example `web3-core-method`) | `web3-eth`, `web3-core`, `web3-types`, `web3-validator`, `web3-errors` |
| Types | `@types/web3` or loose typings | built-in TypeScript types |
| Node engines | older Node supported | package declares `node >= 14` (the library is old; run on a supported Node LTS) |
| Callbacks | callback style supported | promise and PromiEvent only |

Check the lockfile for the exact version rather than guessing from the code; monorepos may contain both.

## 2. Observed behavior differences (same RPC responses)

Results from the same fake node:

| Call | v1 1.10.4 | v4 4.16.0 |
|---|---|---|
| `getBalance(addr)` | `'1000000000000000000'` (string) | `1000000000000000000n` |
| `getBlockNumber()` | `32` (number) | `32n` |
| Contract `balanceOf(...).call()` for `uint256` | `'42'` (string) | `42n` |
| `getTransactionReceipt(...).status` | `true` | `1n` |
| `receipt.gasUsed` | `21000` (number) | `21000n` |
| `getPastEvents(...)[0].returnValues` | object with `0,1,2` plus names | object with `0,1,2,__length__` plus names; `value` is `bigint` |
| `utils.toWei('1.5','ether')` | `'1500000000000000000'` | `'1500000000000000000'` (string) |
| `utils.toBN` / `BN` | present | absent |
| `eth.accounts.wallet.add(pk)` | returns the account | returns the wallet; use `[0]` |

v4 return formats: every method accepts an optional return-format argument and `web3.defaultReturnFormat` sets a global default. Values: `FMT_NUMBER.NUMBER`, `HEX`, `STR`, `BIGINT` and `FMT_BYTES` values for bytes. Code that sets `NUMBER` will return JS numbers (precision loss for large values).

```js
import { Web3, FMT_NUMBER, FMT_BYTES } from 'web3';
const asString = await web3.eth.getBalance(addr, 'latest', { number: FMT_NUMBER.STR, bytes: FMT_BYTES.HEX });
```

## 3. Providers and connections

- v4 exports `HttpProvider` and `WebSocketProvider`; `Web3.providers` exposes `HttpProvider` and `WebsocketProvider`. A URL string passed to `new Web3(url)` selects HTTP or WebSocket by scheme.
- `Web3.givenProvider` is `undefined` outside a browser; in a browser, `new Web3(window.ethereum)` wraps an EIP-1193 provider.
- Always pass a provider. In one test a v4 `new Web3()` instance, asked to sign an EIP-1559 transaction, tried to reach a default hosted RPC endpoint (the `web3-rpc-providers` package is a dependency).
- WebSocket connections drop; v4 `WebSocketProvider` accepts reconnect options in its constructor. Subscriptions do not resume automatically after a drop, so handle `close` and resubscribe, backfilling the missed range with `getPastLogs`.
- To call an RPC method with no helper (for example `eth_getBlockReceipts`, `eth_blobBaseFee`, `eth_simulateV1`, `eth_config`), v4 offers `web3.requestManager.send({ method, params })` and `web3.provider.request({ method, params })`. `requestManager.send` returns the `result` value and `provider.request` returns the whole JSON-RPC response object; neither converts hex strings to numbers.

## 4. Contracts and PromiEvent

- v1/v4: `new web3.eth.Contract(abi, address)`; read with `contract.methods.fn(args).call()`; write with `.send({ from, gas, ... })`; estimate with `.estimateGas({ from })`; encode with `.encodeABI()`.
- `send` returns a PromiEvent: a promise that is also an event emitter with `transactionHash`, `receipt`, `confirmation` and `error` events. Code that listens with `.on(...)` or `.once(...)` must be rewritten for promise-based targets.
- Events: `contract.getPastEvents(name, { fromBlock, toBlock, filter })` for history; `contract.events.Name({ fromBlock })` for live events (a subscription object in v4, an emitter in v1).
- Contract objects remember `options.from` and `options.gas` if set; hidden defaults are a common source of "works on my account" bugs. Search for `defaultAccount`, `defaultBlock`, `defaultGas`, `handleRevert` and `transactionBlockTimeout` settings.
- ABI JSON must be well formed. In v1, an output with a missing `name` field caused a decode failure in a test; use `name: ''` for unnamed outputs.

## 5. Accounts and wallets

- `web3.eth.accounts.create()`, `privateKeyToAccount(pk)`, `sign(message, pk)`, `recover(message, signature)`, `hashMessage`, `signTransaction(tx, pk)`, `encrypt(pk, password)` and `decrypt(keystore, password)` exist in both versions. In v4 `accounts.sign` returns `message`, `messageHash`, `v`, `r`, `s` and `signature`.
- `web3.eth.accounts.wallet` is an in-memory collection; in v4, adding the same address twice logs "Account ... already exists." and keeps a single entry.
- Signing hex strings: `sign('0x...')` treats the input as bytes, which differs from the default of the replacement libraries (see the migration reference).
- v4 local signing supports transaction types 0 (legacy), 1 (EIP-2930) and 2 (EIP-1559). It cannot sign blob (`0x03`) or set-code (`0x04`) transactions.
- The wallet keeps private keys in process memory. Do not log wallet objects; they contain keys.

## 6. Plugins and extensions

v4 has a plugin system (`Web3PluginBase`, `web3.registerPlugin(plugin)`) used for custom RPC methods and contract wrappers. Inventory any plugins; each needs a replacement (a small wrapper function in the adapter, or viem's client `extend`).

## 7. Maintenance practices while migrating

- Pin exact versions; do not widen ranges for an unmaintained package. Commit the lockfile.
- Run `npm audit` at least weekly and record which findings come through web3.js. In 2026-10 a clean install of web3 4.16.0 reported 19 high findings (root cause `zod` via `web3-validator`), and web3 1.10.4 reported 49, including critical ones in `request`, `form-data` and `tar`. Findings in packages that your own runtime path never calls (for example `tar` used only by tooling) can be documented as accepted risk with an expiry date.
- Use `overrides` (npm) or `resolutions` (Yarn) to force patched versions of individual transitive packages, then run the full test suite. If a forced version breaks behavior, isolate web3.js in a sandboxed service instead.
- Do not fork the library to apply fixes; the migration cost is similar and a fork inherits the whole unmaintained surface.
- Never run web3.js in a process that holds production signing keys if it can be avoided. Move signing to a KMS/HSM or a small service already migrated to ethers or viem.
- Keep Node at a supported LTS; test web3.js code on the Node version you deploy.
- Block new web3.js imports with a lint rule (`no-restricted-imports` for `web3` and `web3-*`) and allow existing files with a `// legacy-web3` marker so the count only goes down.
- Track remaining usage with a script (`rg -l "from 'web3'|require\('web3'\)"`) in CI and print the number on each build.

## 8. Debugging common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `TypeError: Cannot mix BigInt and other types` | v4 returned `bigint`, code mixes with number | Convert operands to `bigint` explicitly |
| String concatenation instead of addition | v1 returned strings | `BigInt(a) + BigInt(b)` |
| `TypeError: wallet.add(...).address` undefined on v4 | v4 returns the wallet | `web3.eth.accounts.wallet.add(pk)[0].address` |
| Network request to an unexpected host | `new Web3()` without a provider | Pass a provider explicitly |
| `Returned values aren't valid, did it run Out of Gas?` (v1 message) | Contract call to an address without code or wrong ABI/chain | Check `eth_chainId`, `eth_getCode`, ABI |
| Event listener silent after some hours | WebSocket dropped without resubscribe | Reconnect and backfill with `getPastLogs` |
| Different gas fee behavior than before | Node default fee fields and v1/v4 defaults differ | Set `maxFeePerGas`/`maxPriorityFeePerGas` explicitly (derive from `eth_feeHistory`) |
| Hex string signature differs between libraries | hex string treated as bytes in web3.js | Pass bytes explicitly in the new library |
