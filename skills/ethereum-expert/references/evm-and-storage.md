# EVM and Storage

Reference for the EVM execution model, opcodes added by upgrades, precompiles, storage slot layout, namespaced and proxy storage, contract creation, revert data and event logs. Verified against the Osaka execution-specs, EIP-1967 and ERC-7201 texts, and a solc 0.8.38 storage layout run plus viem 2.57.13 hash computations (2026-10).

## 1. Execution model

- The EVM is a stack machine with 256-bit words and a stack depth limit of 1024. Memory is byte-addressed, zeroed and paid for by expansion. Persistent storage is a key-value map from 256-bit slots to 256-bit values per account. Transient storage (EIP-1153) has the same shape but is cleared at the end of every transaction.
- Each call frame has its own memory, stack and program counter. Calldata and return data are read-only buffers.
- Call types:
  - `CALL`: runs the target's code in the target's context (its storage, `msg.sender` is the caller).
  - `STATICCALL`: like `CALL` but any state change reverts.
  - `DELEGATECALL`: runs the target's code in the caller's context, preserving `msg.sender` and `msg.value`. This is the mechanism behind proxies and libraries.
  - `CALLCODE`: legacy variant of `DELEGATECALL` that changes `msg.sender`; avoid it.
- Call depth is limited to 1024 frames, and a call forwards at most 63/64 of the remaining gas (EIP-150).
- A `REVERT` returns data to the caller and refunds remaining gas of that frame; an invalid opcode or running out of gas consumes all gas of the frame. State changes of a failed frame are discarded, but logs and storage changes of earlier successful frames in the same transaction persist unless the outer frame also fails.
- `selfdestruct` after EIP-6780 deletes an account only when called in the same transaction that created it; otherwise it only moves the balance.

## 2. Opcodes added by upgrades

| Opcode | Upgrade | EIP | Notes |
|---|---|---|---|
| `BASEFEE` | London | 3198 | Current block base fee |
| `PREVRANDAO` (was `DIFFICULTY`) | Merge | 4399 | Beacon chain randomness mix; not safe as a sole randomness source for value-bearing outcomes because proposers can influence it |
| `PUSH0` | Shanghai | 3855 | Pushes zero cheaply; requires the target chain to support Shanghai |
| `TLOAD`, `TSTORE` | Cancun | 1153 | Transient storage, 100 gas each |
| `MCOPY` | Cancun | 5656 | Memory copy |
| `BLOBHASH`, `BLOBBASEFEE` | Cancun | 4844, 7516 | Blob versioned hash by index; current blob base fee |
| `CLZ` | Osaka | 7939 | Count leading zero bits |

Compilers target an EVM version. Deploying bytecode built for a newer EVM version to a chain that lacks an opcode fails with invalid opcode errors. Check each target chain (especially L2s and sidechains) before choosing the compiler's `evm_version`.

## 3. Precompiles

| Address | Function | Since |
|---|---|---|
| `0x01` | `ecrecover` | genesis |
| `0x02` | `sha256` | genesis |
| `0x03` | `ripemd160` | genesis |
| `0x04` | identity (data copy) | genesis |
| `0x05` | `modexp` | Byzantium; repriced by EIP-7883 and bounded by EIP-7823 in Fusaka |
| `0x06`, `0x07`, `0x08` | BN254 add, multiply, pairing | Byzantium |
| `0x09` | `blake2f` | Istanbul |
| `0x0a` | KZG point evaluation | Cancun (EIP-4844) |
| `0x0b` to `0x11` | BLS12-381: G1 add, G1 MSM, G2 add, G2 MSM, pairing check, map to G1, map to G2 | Prague (EIP-2537) |
| `0x100` | `P256VERIFY` (secp256r1) | Osaka (EIP-7951) |

- A precompile that is the target of an EIP-7702 delegation executes as empty code.
- L2s and sidechains implement their own sets. For example, `P256VERIFY` uses the same address `0x100` as the L2 precompile (EIP-7951 states this), but gas costs may differ.

## 4. Storage layout rules (Solidity)

State variables are assigned to 32-byte slots in declaration order, with inheritance linearized base-first.

- Values smaller than 32 bytes are packed into one slot from the low-order end while they fit, and a struct or array always starts a new slot.
- Fixed-size types: `uint128 a; uint64 b; uint64 c;` share slot 0 (offsets 0, 16, 24 bytes). `address owner; bool flag;` share the next slot (offsets 0 and 20).
- Mapping `mapping(K => V)` at slot `p`: the value for key `k` lives at `keccak256(h(k) . p)`, where `h(k)` is the key padded to 32 bytes (value types) or the raw bytes (strings and bytes), and `.` is concatenation. The slot `p` itself stays empty.
- Dynamic array at slot `p`: slot `p` holds the length; element `i` of a `uint256[]` lives at `keccak256(p) + i`. Elements smaller than 32 bytes are packed.
- `bytes` and `string`: up to 31 bytes are stored in the slot itself with the length in the lowest byte (`len * 2`); longer values store `len * 2 + 1` in slot `p` and the data starting at `keccak256(p)`.
- Struct members follow the same packing rules, starting at a fresh slot.
- `immutable` and `constant` variables are not in storage.

A solc 0.8.38 run on this declaration order printed:

```
a    slot 0 offset 0   uint128
b    slot 0 offset 16  uint64
c    slot 0 offset 24  uint64
owner slot 1 offset 0  address
flag slot 1 offset 20  bool
big  slot 2            uint256
bal  slot 3            mapping(address => uint256)
arr  slot 4            uint256[]
name slot 5            string
s    slot 6            struct S { uint8 x; uint256 y; }
```

Produce the same table for any contract with `solc --storage-layout` or `forge inspect <Contract> storageLayout`. Read a slot with `eth_getStorageAt(address, slot, blockTag)`, where `slot` is hex of up to 32 bytes (`0x0` and a full 32-byte value both work).

Mapping and array slot computations (viem 2.57.13, verified by execution):

```js
import { keccak256, encodeAbiParameters } from 'viem';
// bal[key] for `mapping(address => uint256) bal` at slot 3:
const slot = keccak256(encodeAbiParameters([{ type: 'address' }, { type: 'uint256' }], [key, 3n]));
// element 2 of a dynamic array at slot 4: BigInt(keccak256(encodeAbiParameters([{ type: 'uint256' }], [4n]))) + 2n
```

Upgradeable contracts must keep the layout append-only; see solidity-expert and its storage reference for upgrade safety rules.

## 5. Namespaced storage and proxy slots

- **ERC-7201 (Final)** places a contract's variables in a struct stored at a derived root slot instead of slot 0 onward, to avoid collisions in proxies and diamond-like designs:

```
erc7201(id) = keccak256(abi.encode(uint256(keccak256(bytes(id))) - 1)) & ~bytes32(uint256(0xff))
```

  The Solidity annotation is `/// @custom:storage-location erc7201:<id>`. Computed for OpenZeppelin's id `openzeppelin.storage.Initializable`, the formula gives `0xf0c57e16840df040f15088dc2f81fe391c3923bec73e23a9662efc9c229c6a00`, matching the constant in OpenZeppelin's `Initializable`. The `- 1` keeps the root from overlapping the standard layout tree, and `& ~0xff` aligns the root to 256 slots (anticipating gas schedule changes for state-tree migrations, per the ERC's rationale).
- **ERC-1967 (Final)** fixes proxy bookkeeping slots as `bytes32(uint256(keccak256('eip1967.proxy.<name>')) - 1)`:

| Slot | Value |
|---|---|
| implementation | `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` |
| admin | `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` |
| beacon | `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` |

  Explorers and tooling read these with `eth_getStorageAt` to find a proxy's implementation.
- EIP-7702 delegated accounts keep their own storage, written by whatever code they delegated to. Re-delegating to code with a different layout can corrupt or expose old data, so use ERC-7201 namespaces in delegate contracts.

## 6. Contract creation

- A creation transaction (or `CREATE`/`CREATE2`) runs initcode; the bytes it returns become the runtime code. Constructor arguments are appended to initcode and ABI-decoded by the constructor.
- During construction the new account has no code yet, so `extcodesize(address(this))` is 0 and a caller that is mid-construction passes "is this an EOA" size checks. This is another reason `extcodesize` does not prove EOA status.
- Runtime code is limited to 24576 bytes (EIP-170) and initcode to 49152 bytes (EIP-3860). Glamsterdam's EIP-7954 proposes a larger limit; it is not active on mainnet.
- Code starting with `0xEF` is rejected at creation (EIP-3541), except for the EIP-7702 delegation indicator which is written by the protocol, not by creation.
- `CREATE2` addresses are predictable from deployer, salt and initcode hash, which allows counterfactual addresses for smart accounts and deterministic deployments. With EIP-6780, destroying and re-creating at the same address is no longer possible across transactions.

## 7. Revert data and errors

- `require(false, "msg")` and `revert("msg")` return `Error(string)`: selector `0x08c379a0` followed by the ABI-encoded string.
- Failed `assert`, arithmetic overflow, division by zero, bad array index and similar return `Panic(uint256)`: selector `0x4e487b71` followed by a code.
- Custom errors return their 4-byte selector followed by encoded arguments and are cheaper than strings. Clients decode them with the contract ABI (`decodeErrorResult` in viem, `Interface.parseError` in ethers).
- `eth_call` and `eth_estimateGas` surface revert data in the JSON-RPC error `data` field; the field's presence and shape varies by client and provider, so handle both a missing field and a plain message.
- Low-level calls (`call`, `delegatecall`, `staticcall`) return `(false, returndata)` instead of reverting; unchecked results are a common bug source.

## 8. Logs

- A log has an emitting `address`, up to 4 `topics` (32 bytes each) and a `data` byte string. Contracts can write logs but cannot read them. Opcodes `LOG0` to `LOG4` select the topic count and cost 375 + 375 per topic + 8 per data byte.
- For a non-anonymous Solidity event, `topics[0]` is `keccak256("Name(type1,type2)")` (canonical types, no spaces, no parameter names). `indexed` parameters follow as `topics[1..3]`; non-indexed parameters are ABI-encoded in `data`. The ERC-20 `Transfer(address,address,uint256)` topic0 is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.
- Indexed dynamic types (`string`, `bytes`, arrays, structs) are stored as their `keccak256` hash, so the original value cannot be recovered from the topic.
- Anonymous events omit `topics[0]` and can index up to 4 parameters.
- Each block header and receipt carries a 2048-bit bloom filter of log addresses and topics; nodes use it to skip blocks quickly in `eth_getLogs`. Blooms have false positives, so always filter results.
- `eth_getLogs` filter: `fromBlock`/`toBlock` or `blockHash` (not both), `address` (one or a list), and `topics` as a positional array where `null` is a wildcard and a nested array means OR for that position.
- Logs from a block that is reorged out are marked `removed: true` in subscriptions and filter polling; range queries simply stop returning them.
- Use events for data that off-chain consumers need and contracts do not; storage writes cost more than logs by orders of magnitude.

```bash
# Transfer logs of one token for a short range (replace the address; keep ranges small)
curl -s -X POST "$RPC_URL" -H 'content-type: application/json' --data '{
  "jsonrpc":"2.0","id":1,"method":"eth_getLogs",
  "params":[{"fromBlock":"0x1312d00","toBlock":"0x1312d0a",
    "address":"0x0000000000000000000000000000000000000001",
    "topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]}]}'
```
