# Migration from web3.js to ethers v6 and viem

Side-by-side mapping and a phased plan for replacing web3.js v1 and v4. Verified against web3 4.16.0, web3 1.10.4, ethers 6.17.0 and viem 2.57.13 by running pure-function comparisons and a fake JSON-RPC server (2026-10). Items marked "pattern" follow the libraries' documented usage but were not executed against a live node.

## 1. Plan

1. **Freeze**: pin versions, add characterization tests, set explicit providers.
2. **Pure functions first**: units, hashing, ABI encoding, address helpers, message hashing. They need no network and are easy to compare (section 4).
3. **Reads**: balances, `eth_call`, blocks, receipts, logs. Compare outputs on the same block number.
4. **Events and subscriptions**: replace `getPastEvents` and `contract.events` with log queries and watchers, and make the follower reorg-aware (see ethereum-expert).
5. **Signing**: message and typed-data signatures, then transaction signing with a throwaway key on a testnet.
6. **Sending**: transactions, nonce handling, receipt waits, error handling.
7. **Cleanup**: remove web3.js, `web3-*` and `@types/web3` packages, polyfills and overrides. Re-run `npm audit`.

Choosing the target:

| Criterion | ethers v6 | viem |
|---|---|---|
| Style | Classes: `Provider`, `Signer`, `Contract` | Functions and clients: `publicClient.readContract(...)` |
| Types from ABI | Generated types (TypeChain) or manual | Inferred from `as const` ABIs |
| Closest to web3.js | `new Contract(addr, abi, signerOrProvider)` mirrors `new web3.eth.Contract(abi, addr)` | Different shape; contract calls take `{ address, abi, functionName, args }` |
| Browser wallets | `BrowserProvider(window.ethereum)` | `createWalletClient({ transport: custom(window.ethereum) })`, wagmi for React |
| Quantities | `bigint` for amounts, `number` for block numbers | `bigint` for both |
| Receipt status | `1` or `0` | `'success'` or `'reverted'` |

## 2. Providers, clients and accounts

| web3.js | ethers v6 | viem |
|---|---|---|
| `new Web3(url)` (HTTP or WebSocket URL) | `new JsonRpcProvider(url)`; `new WebSocketProvider(url)` | `createPublicClient({ chain, transport: http(url) })`; `webSocket(url)` transport |
| `new Web3(window.ethereum)` | `new BrowserProvider(window.ethereum)`, then `await provider.getSigner()` | `createWalletClient({ chain, transport: custom(window.ethereum) })` |
| Multiple endpoints with failover | `new FallbackProvider([...])` | `fallback([http(a), http(b)])` transport |
| `web3.eth.getChainId()` | `(await provider.getNetwork()).chainId` | `publicClient.getChainId()` |
| `web3.eth.getBlockNumber()` | `provider.getBlockNumber()` (number) | `publicClient.getBlockNumber()` (bigint) |
| `web3.eth.getBalance(addr)` | `provider.getBalance(addr)` | `publicClient.getBalance({ address })` |
| `web3.eth.getBlock(n)` | `provider.getBlock(n)` | `publicClient.getBlock({ blockNumber })` or `{ blockTag }` |
| `web3.eth.getTransactionReceipt(h)` | `provider.getTransactionReceipt(h)` | `publicClient.getTransactionReceipt({ hash })` |
| `web3.eth.getTransactionCount(a, 'pending')` | `provider.getTransactionCount(a, 'pending')` | `publicClient.getTransactionCount({ address, blockTag: 'pending' })` |
| `web3.eth.getCode(a)` / `getStorageAt(a, slot)` | `provider.getCode(a)` / `provider.getStorage(a, slot)` | `publicClient.getCode({ address })` / `getStorageAt({ address, slot })` |
| `web3.eth.getGasPrice()` | `(await provider.getFeeData()).gasPrice` | `publicClient.getGasPrice()` |
| EIP-1559 fees: `getMaxPriorityFeePerGas`, `calculateFeeData` | `provider.getFeeData()` returns `maxFeePerGas`, `maxPriorityFeePerGas` | `publicClient.estimateFeesPerGas()` |
| `web3.eth.estimateGas(tx)` | `provider.estimateGas(tx)` | `publicClient.estimateGas({ account, to, data, value })` |
| `web3.eth.call(tx)` | `provider.call(tx)` | `publicClient.call({ to, data })` |
| `web3.eth.sendSignedTransaction(raw)` | `provider.broadcastTransaction(raw)` | `publicClient.sendRawTransaction({ serializedTransaction })` |
| `web3.eth.ens.getAddress(name)` | `provider.resolveName(name)` | `publicClient.getEnsAddress({ name })` |
| `web3.eth.accounts.create()` | `Wallet.createRandom()` | `generatePrivateKey()` then `privateKeyToAccount` (from `viem/accounts`) |
| `web3.eth.accounts.privateKeyToAccount(pk)` | `new Wallet(pk, provider)` | `privateKeyToAccount(pk)` |
| `web3.eth.accounts.wallet.add(pk)` (v4 returns the wallet; v1 returns the account) | pass the `Wallet` as the contract runner | pass `account` to the wallet client or per call |
| `web3.eth.accounts.encrypt(pk, pass)` / `decrypt` | `wallet.encrypt(pass)` / `Wallet.fromEncryptedJson(json, pass)` | no keystore helper; use ethers for keystores or a dedicated signer |
| `web3.eth.personal.*`, `defaultAccount`, `defaultBlock` | none; pass `from`, signer and block tags explicitly | none; pass explicitly |
| `new web3.BatchRequest()` | `JsonRpcProvider` batches concurrent calls by default (`batchMaxCount`) | `http(url, { batch: true })` |

Wrong-chain protection: web3.js does not require a chain; ethers detects the network on first use (pass `{ staticNetwork }` to skip the detection call), and viem clients take a `chain` object that is checked for wallet actions. Always assert `chainId` at startup.

## 3. Contracts

| Task | web3.js | ethers v6 | viem |
|---|---|---|---|
| Construct | `new web3.eth.Contract(abi, addr)` | `new Contract(addr, abi, runner)` | pass `{ address, abi }` per call, or `getContract({ address, abi, client })` |
| Read | `await c.methods.balanceOf(a).call()` | `await c.balanceOf(a)` | `publicClient.readContract({ address, abi, functionName: 'balanceOf', args: [a] })` |
| Write | `await c.methods.transfer(to, v).send({ from })` (PromiEvent) | `const tx = await c.connect(signer).transfer(to, v); await tx.wait()` | `const { request } = await publicClient.simulateContract({...}); const hash = await walletClient.writeContract(request); await publicClient.waitForTransactionReceipt({ hash })` |
| Estimate gas | `c.methods.f(...).estimateGas({ from })` | `await c.f.estimateGas(...)` | `publicClient.estimateContractGas({...})` |
| Static call of a state-changing function | `.call({ from })` | `await c.f.staticCall(...)` | `publicClient.simulateContract({...})` |
| Encode calldata | `c.methods.f(...).encodeABI()` or `web3.eth.abi.encodeFunctionCall(abiItem, args)` | `iface.encodeFunctionData('f', args)` | `encodeFunctionData({ abi, functionName, args })` |
| Decode returned data | `web3.eth.abi.decodeParameters(types, data)` | `iface.decodeFunctionResult('f', data)` | `decodeFunctionResult({ abi, functionName, data })` |
| Deploy | `new web3.eth.Contract(abi).deploy({ data, arguments }).send({ from })` | `new ContractFactory(abi, bytecode, signer).deploy(...args)`, then `await c.waitForDeployment()` | `walletClient.deployContract({ abi, bytecode, args })` |
| Batch many reads | custom or `BatchRequest` | Multicall contract, or provider batching | `publicClient.multicall({ contracts })` |
| ABI format | JSON ABI | JSON ABI or human-readable fragments | JSON ABI as `const`, or `parseAbi([...])` |

Notes:

- web3.js v4 returns `bigint` for uint values; v1 returns strings. ethers returns `bigint`. viem returns `bigint`. Multi-output functions return arrays or objects: web3 v1 gives an object with numeric and named keys; ethers gives a `Result` array with named access; viem gives an array (or the single value for one output).
- web3.js `call` and `send` accept `{ from, gas, gasPrice, value }`. In ethers pass overrides as the last argument: `c.f(arg, { value, gasLimit, maxFeePerGas })`. In viem put `value`, `gas`, `maxFeePerGas` in the action parameters.
- ethers rejects addresses with a wrong mixed-case checksum when it resolves them. viem's `isAddress` is strict by default and returns false for a wrong checksum, but actions may pass such an address through to the node, so validate inputs explicitly. Normalize test data.
- `contract.options.address`, `contract.defaultAccount` and `defaultBlock` have no equivalent. Create a contract object per address, and pass runner and block tag explicitly.

## 4. Pure functions

All rows below produced identical results in a run against web3 4.16.0, ethers 6.17.0 and viem 2.57.13.

| web3.js | ethers v6 | viem |
|---|---|---|
| `web3.utils.toWei('1.5', 'ether')` (string) | `parseEther('1.5')` (bigint) | `parseEther('1.5')` |
| `web3.utils.toWei('2', 'gwei')` | `parseUnits('2', 'gwei')` | `parseGwei('2')` |
| `web3.utils.fromWei(v, 'ether')` (string) | `formatEther(v)` | `formatEther(v)` |
| `web3.utils.keccak256(str)` / `sha3` | `keccak256(toUtf8Bytes(str))` | `keccak256(toHex(str))` |
| `web3.utils.soliditySha3({ type, value }, ...)` | `solidityPackedKeccak256(types, values)` | `keccak256(encodePacked(types, values))` |
| `web3.eth.abi.encodeParameters(types, values)` | `AbiCoder.defaultAbiCoder().encode(types, values)` | `encodeAbiParameters(parseAbiParameters('address, uint256'), values)` |
| `web3.eth.abi.encodeFunctionCall(item, args)` | `new Interface(abi).encodeFunctionData(name, args)` | `encodeFunctionData({ abi, functionName, args })` |
| `web3.eth.abi.encodeEventSignature(item)` | `id('Transfer(address,address,uint256)')` | `toEventSelector(item)` |
| `web3.eth.abi.decodeLog(inputs, data, topics)` | `iface.parseLog({ topics, data })` | `decodeEventLog({ abi, data, topics })` |
| `web3.utils.toChecksumAddress(a)` | `getAddress(a)` | `getAddress(a)` |
| `web3.utils.isAddress(a)` | `isAddress(a)` | `isAddress(a)` |
| `web3.utils.toHex(255)` / `numberToHex` | `toBeHex(255)` | `toHex(255)` |
| `web3.utils.hexToNumber('0xff')` | `toNumber('0xff')` | `hexToNumber('0xff')` |
| `web3.utils.padLeft('0x1', 64)` | `zeroPadValue('0x01', 32)` | `pad('0x01')` |
| `web3.utils.utf8ToHex('hi')` | `hexlify(toUtf8Bytes('hi'))` | `stringToHex('hi')` |

v1 only: `web3.utils.toBN`, `BN` arithmetic and `isBN` have no counterpart. Convert with `BigInt(bn.toString())` and use native `bigint` operators.

## 5. Signing

| web3.js | ethers v6 | viem |
|---|---|---|
| `web3.eth.accounts.sign(msg, pk)` returns `{ message, messageHash, v, r, s, signature }` | `await wallet.signMessage(msg)` returns the signature string | `await account.signMessage({ message })` |
| `web3.eth.accounts.recover(msg, sig)` | `verifyMessage(msg, sig)` | `recoverMessageAddress({ message, signature })` or `verifyMessage({ address, message, signature })` |
| `web3.eth.accounts.hashMessage(msg)` | `hashMessage(msg)` | `hashMessage(msg)` |
| `web3.eth.accounts.signTransaction(tx, pk)` (needs a provider to fill missing fields) | `await wallet.signTransaction(tx)` | `await account.signTransaction(tx)` |
| `web3.eth.signTypedData(addr, typed)` | `wallet.signTypedData(domain, types, value)` | `account.signTypedData({ domain, types, primaryType, message })` |
| `web3.eth.personal.sign` / `web3.eth.sign` through a wallet | `signer.signMessage` from `BrowserProvider` | `walletClient.signMessage({ account, message })` |

Message encoding differs for hex strings:

- web3.js signs a `0x`-prefixed hex string as raw bytes.
- ethers `signMessage('0x1234')` and viem `signMessage({ message: '0x1234' })` sign the text characters "0x1234".
- To match web3.js, pass bytes: ethers `signMessage(getBytes('0x1234'))`, viem `signMessage({ message: { raw: '0x1234' } })`. This was verified by comparing signatures.
- The same applies to `hashMessage`.

Transaction field names also differ: web3.js `gas`, ethers `gasLimit`, viem `gas`. Signed EIP-1559 transactions with identical fields and key produced identical raw bytes in ethers and viem. web3.js v4 local signing covers legacy, EIP-2930 and EIP-1559 types only, so blob and set-code transactions (types `0x03`, `0x04`) require the new libraries (viem has `signAuthorization` for EIP-7702).

EIP-712 signatures from ethers and viem were identical for the same domain, types and message.

## 6. Events and subscriptions (pattern)

| Task | web3.js | ethers v6 | viem |
|---|---|---|---|
| Past events of a contract | `await c.getPastEvents('Transfer', { fromBlock, toBlock, filter: { from } })` | `await c.queryFilter(c.filters.Transfer(from, null), fromBlock, toBlock)` | `publicClient.getContractEvents({ address, abi, eventName: 'Transfer', args: { from }, fromBlock, toBlock })` or `getLogs({ event, args })` |
| Raw logs | `web3.eth.getPastLogs({ address, topics, fromBlock, toBlock })` | `provider.getLogs({ address, topics, fromBlock, toBlock })` | `publicClient.getLogs({ address, event, args, fromBlock, toBlock })` |
| Live events | `const sub = await c.events.Transfer({ fromBlock: 'latest' }); sub.on('data', fn)` | `c.on('Transfer', (from, to, value, payload) => ...)` | `publicClient.watchContractEvent({ address, abi, eventName: 'Transfer', onLogs })` returns an unwatch function |
| New blocks | `await web3.eth.subscribe('newBlockHeaders')` then `.on('data', fn)` | `provider.on('block', fn)` | `publicClient.watchBlocks({ onBlock })` or `watchBlockNumber` |
| Unsubscribe | `sub.unsubscribe()` | `c.off(...)` or `provider.removeAllListeners()` | call the function returned by the watcher |

In the executed comparison one mock `Transfer` log decoded to the same sender, recipient and value (42) through `getPastEvents`, `queryFilter`, `getContractEvents` and `getLogs`. Differences to handle:

- Block numbers in event objects: web3 v4 `bigint`, ethers `number`, viem `bigint`.
- Decoded arguments: web3 `returnValues` has numeric keys, a `__length__` field and named keys (in v1 and v4), ethers `args` is a `Result` (array with named access), viem `args` is an object keyed by parameter name.
- Log objects expose `blockHash`, `transactionHash` and `logIndex` in all three; use them for idempotency keys.
- Use block-range chunks for `getLogs`; providers cap ranges.
- Handle reorgs: removed logs arrive with `removed: true` in subscriptions; see the follower in the ethereum-expert references.
- Polling versus WebSocket: viem watchers poll over HTTP and subscribe over WebSocket transports; ethers `JsonRpcProvider` polls, `WebSocketProvider` subscribes.

## 7. Transactions, receipts and errors

| Topic | web3.js | ethers v6 | viem |
|---|---|---|---|
| Send native value | `web3.eth.sendTransaction({ from, to, value })` | `await signer.sendTransaction({ to, value })` | `walletClient.sendTransaction({ account, to, value })` |
| Wait for inclusion | PromiEvent `.once('receipt')` or awaiting `send` | `await tx.wait(confirmations)` | `await publicClient.waitForTransactionReceipt({ hash, confirmations })` |
| Receipt status | v1 `true/false`; v4 `1n/0n` | `1` / `0` | `'success'` / `'reverted'` |
| `gasUsed` | v1 number; v4 `bigint` | `bigint` | `bigint` |
| Revert behavior on wait | rejects (check your version) | `wait()` throws `CALL_EXCEPTION`; throws `TRANSACTION_REPLACED` when replaced | `waitForTransactionReceipt` returns the receipt; check `status` |
| Revert reason decoding | `error.data` and manual ABI decoding | `error.revert` / `Interface.parseError(data)` on `CALL_EXCEPTION` | `ContractFunctionRevertedError` with `data.errorName` and `data.args` |
| Fee fields | `maxFeePerGas`, `maxPriorityFeePerGas`, `gasPrice` | same names | same names |
| Nonce management | node-provided nonce at send time | node-provided; add your own nonce manager for concurrent sends | node-provided; set `nonce` explicitly for concurrent sends |

Use the transaction-level rules in the ethereum-expert references when moving fee and replacement logic.

## 8. Types and serialization

- Wei amounts are `bigint` in the targets. Replace string and BN arithmetic, `parseInt` and `Number()` on wei, and string comparisons.
- `JSON.stringify` throws on `bigint`. Serialize with a replacer (`(k, v) => typeof v === 'bigint' ? v.toString() : v`) and parse explicitly.
- Database columns for wei should be `NUMERIC(78,0)` or text, not `BIGINT` or float.
- ethers block numbers are `number`; viem block numbers are `bigint`. Pick one convention at the adapter boundary.
- Addresses: keep checksummed strings; compare case-insensitively or normalize with `getAddress`.
- web3.js v4 supports a global return format (`web3.defaultReturnFormat`, `FMT_NUMBER` values `NUMBER`, `HEX`, `STR`, `BIGINT`); code that sets `NUMBER` will see JS numbers where the targets return `bigint`.

## 9. Verification checklist per migrated function

1. Same inputs produce equal outputs, or an intentional documented difference (type only).
2. Error cases (revert, timeout, wrong chain, invalid address) produce handled errors with a stable shape.
3. Gas and fee behavior is equal or better on a testnet.
4. Event handling is idempotent and reorg-aware.
5. Dependency removed from `package.json`, lockfile cleaned, bundle size checked.
