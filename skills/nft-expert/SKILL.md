---
name: nft-expert
description: >-
  Designs and reviews NFT contracts and minting flows on OpenZeppelin Contracts 5.x: ERC-721 and ERC-1155, ERC-2981 royalties, ERC-4906 metadata updates, ERC-5192 soulbound tokens, ERC-721A batch minting, ERC-6551 token-bound accounts, Merkle allowlists, EIP-712 signature mints, metadata JSON, IPFS and Arweave storage, on-chain SVG and marketplace interoperability. Use when writing or auditing an NFT collection, tokenURI, safeMint, allowlist, royalty, reveal or freeze logic, or when metadata does not show on marketplaces. Not for generic Solidity or upgradeable proxies (use solidity-expert), exploit methodology (use smart-contract-security-expert), or NFT-backed lending and DeFi (use defi-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# NFT Expert

This skill covers the contract and off-chain pieces of an NFT project: choosing the token standard, writing the collection contract with OpenZeppelin Contracts 5.x, selling it safely (allowlists, signatures, public mint), pointing tokens at durable metadata, and making royalties and marketplaces behave. It uses only verified standards and the v5 OpenZeppelin API; v4 patterns such as `_beforeTokenTransfer` and `Counters` do not apply.

> Verified against OpenZeppelin Contracts 5.7.0 (changelog dated 2026-07-29; the npm `latest` tag still pointed to 5.6.1 and the `dev` tag to 5.7.0, so pin the version explicitly), Solidity 0.8.38, ERC721A 4.3.0, @openzeppelin/merkle-tree 1.0.8, viem 2.57.13. The example contracts were compiled with solc 0.8.38 and executed in an EVM harness, including the reentrancy demonstration (2026-10).

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

- Covered: ERC-721 and ERC-1155 collections, royalty signalling, metadata update events, soulbound tokens, token-bound accounts, minting mechanics (public, allowlist, signature, batch), reveal and freeze, metadata JSON and storage on IPFS or Arweave, on-chain SVG, marketplace behavior, and tests for these.
- Not covered: Solidity language, proxies and upgrade safety (solidity-expert), exploit catalogues and audit process (smart-contract-security-expert), AMMs, lending and NFT financialization (defi-expert), governance with NFT voting (dao-expert), Foundry or Hardhat setup (foundry-expert, hardhat-expert), client code (ethersjs-expert).

## 2. Core Expertise

| Topic | Key facts |
|---|---|
| ERC-721 | Final. One owner per `tokenId`; `safeTransferFrom` calls `onERC721Received` (selector `0x150b7a02`) on contract recipients; interface id `0x80ac58cd`; metadata extension `0x5b5e139f` |
| ERC-1155 | Final. Many ids in one contract, balances per `(account, id)`, batch transfers, receiver callbacks (`0xf23a6e61` single, `0xbc197c81` batch), interface id `0xd9b67a26`; URI with `{id}` substitution |
| ERC-2981 | Final. `royaltyInfo(tokenId, salePrice)` returns receiver and amount; interface id `0x2a55205a`; payment is voluntary and not enforced by transfers |
| ERC-4906 | Final. `MetadataUpdate(tokenId)` and `BatchMetadataUpdate(from, to)` events; interface id `0x49064906`; implemented by OpenZeppelin `ERC721URIStorage` |
| ERC-5192 | Final. Minimal soulbound: `locked(tokenId)`, `Locked` and `Unlocked` events, interface id `0xb45a3c0e`; transfers of locked tokens must revert |
| ERC-2309 | Final. Consecutive transfer event for minting many tokens at construction; OpenZeppelin `ERC721Consecutive` |
| ERC-6551 | Status Review (not Final). Token-bound accounts created through a singleton registry at `0x000000006551c19487814612e58FE06813775758` |
| ERC-721A | An implementation by Chiru Labs created for Azuki, not an EIP. Cheaper batch minting, costlier first transfer after a batch; version 4.3.0 |
| OpenZeppelin 5.x | Hook is `_update(to, tokenId, auth)` for ERC-721 and `_update(from, to, ids, values)` for ERC-1155; `Ownable(initialOwner)`; custom errors; `Counters` removed; solidity `^0.8.24` for tokens |
| Metadata | ERC-721 JSON schema has `name`, `description`, `image`; other fields such as `attributes` are marketplace conventions |
| Operator filter | The OpenSea operator filter registry is deprecated (its repository README says so); royalties are not enforceable through it |

## 3. Workflow

1. Pick the standard and supply model: unique 1/1 or large PFP set (ERC-721), editions or game items (ERC-1155), non-transferable credentials (ERC-721 plus ERC-5192). See [references/standards.md](references/standards.md).
2. Decide metadata strategy: off-chain JSON on IPFS or Arweave, on-chain SVG, or a mix, and whether it is revealed later or frozen. See [references/metadata-and-storage.md](references/metadata-and-storage.md).
3. Decide the sale design: Merkle allowlist, signature voucher, public sale, price, per-wallet limits, phases. See [references/minting-patterns.md](references/minting-patterns.md).
4. Write the contract from OpenZeppelin 5.x building blocks. Override `_update` for transfer logic, keep `supportsInterface` correct, and put effects before `_safeMint`.
5. Test happy paths, limits, access control, interface ids, signature replay and reentrancy; add fuzz and invariant tests for supply.
6. Deploy to a testnet, mint with a contract wallet and an EOA, view on a testnet marketplace, then deploy to mainnet or an L2, verify source, and move ownership to a multisig.
7. After the sale: reveal or freeze metadata, emit ERC-4906 events if URIs changed, withdraw funds, and document the contract addresses and metadata hashes.

## 4. Decision Rules

- ERC-721 for unique assets with individual ownership and approvals; ERC-1155 when many tokens share an id (editions, consumables) or when mixed fungible and non-fungible ids are needed; 1155 has no per-id approvals and no `ownerOf`.
- ERC-721A only when large batch minting by the same wallet dominates and the added complexity is acceptable (storage layout differs, transfers of the first token in a batch pay extra, it does not follow OpenZeppelin's `_update` hook). For OpenZeppelin-only code bases, mint in a loop or use `ERC721Consecutive` for a fixed pre-mint.
- Allowlist by Merkle proof when the list is fixed and public-in-advance; by EIP-712 signature when eligibility is dynamic, needs per-user limits that change, or must be revoked without redeploying.
- Royalties: expose ERC-2981 for marketplaces that honor it, and treat income as voluntary. Enforcement through transfer restrictions breaks composability (wallets, escrow, marketplaces) and is a product decision with trade-offs.
- Soulbound: ERC-5192 plus a revert in `_update` for non-mint non-burn moves; decide who can burn or recover a token if a wallet is lost.
- Metadata: IPFS with a CID (immutable content) or Arweave for permanent storage; on-chain data for small SVG art or traits; avoid HTTP URLs and centralized mutable servers for anything promised as permanent.
- Upgradeable NFT contracts only with a clear reason and governance; most collections are immutable with an admin that can be renounced or frozen.
- Chain choice: L2s lower mint cost; check that the target chain supports the opcodes of the chosen compiler EVM version and that marketplaces index it.

## 5. Coding Standards

- Pragma `^0.8.24` (OpenZeppelin 5.7.0 token contracts require it) and a pinned compiler in the build. Import named symbols: `import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";`.
- `Ownable(initialOwner)` or `Ownable2Step` with the owner passed to the constructor. `Ownable` v5 requires the initial owner argument and rejects `address(0)`.
- Use custom errors, not revert strings. OpenZeppelin 5 reverts with `ERC721InvalidReceiver`, `ERC721NonexistentToken`, `ERC721IncorrectOwner`, `ERC721InsufficientApproval` and similar from IERC6093; tests should match these selectors.
- Customize transfers in `_update(address to, uint256 tokenId, address auth) returns (address from)`. Call `super._update` unless you intentionally block the move. Do not override `_transfer`, which no longer carries hooks.
- Replace `_exists(id)` with `_ownerOf(id) != address(0)` or `_requireOwned(id)` (reverts for nonexistent tokens); `tokenURI` must call `_requireOwned`.
- Do not use `Counters` (removed in v5); a plain `uint256 private _nextTokenId` is enough.
- Override `supportsInterface` when inheriting several bases that declare it (for example `ERC721` and `ERC2981`), and return `true` for each standard actually implemented.
- Emit ERC-4906 events whenever a token URI changes; emit `BatchMetadataUpdate(1, type(uint256).max)` when a base URI changes.
- Keep external calls last: update counters and allowance mappings before `_safeMint`, `_safeTransfer` and any ETH transfer.
- NatSpec on public functions; `@author Example Labs` or omit the author tag.

## 6. Project Structure

```
nft-project/
├── src/
│   ├── Collection.sol           # ERC-721 + ERC-2981 + Ownable2Step + sale logic
│   ├── SignedMint.sol           # EIP-712 voucher redemption (optional)
│   └── interfaces/
├── test/
│   ├── Collection.t.sol         # unit, fuzz and invariant tests
│   └── Reentrancy.t.sol         # malicious receiver contracts
├── script/Deploy.s.sol          # deployment with constructor args from env
├── metadata/
│   ├── images/                  # source art (hash them, pin them)
│   ├── json/                    # per-token JSON generated by a script
│   └── provenance.json          # per-token content hashes and the final provenance hash
├── allowlist/
│   ├── list.csv                 # address, allowance
│   └── tree.json                # StandardMerkleTree dump (root published in the contract)
├── foundry.toml                 # solc_version pinned, evm_version set for the target chain
└── package.json                 # @openzeppelin/contracts pinned, @openzeppelin/merkle-tree for scripts
```

## 7. Design Patterns

- **Base URI plus token id**: `tokenURI` returns `string.concat(baseURI, id.toString(), ".json")` for uniform collections. Use `ERC721URIStorage` when each token needs its own URI.
- **Reveal**: sell with a placeholder URI, then set the final base URI once; publish a provenance hash (hash over the ordered per-token metadata hashes) before the sale so the order cannot be changed; call `freezeMetadata()` after reveal.
- **Merkle allowlist with allowance**: leaf `(address, allowance)`, double-hashed; the contract tracks per-address minted counts.
- **Signature voucher**: owner-held signer signs `(to, tokenId, nonce, deadline)` under an EIP-712 domain; anyone can relay the voucher; nonce is consumed on use.
- **Pull payments**: owner withdraws proceeds; royalty receivers can be a splitter contract; never push ETH inside the mint loop.
- **Pre-mint with `ERC721Consecutive`**: mint a large range in the constructor with one event (ERC-2309); remember that `_update` hooks do not run for the batch.
- **Soulbound by `_update`**: block moves where both `from` and `to` are non-zero.
- **On-chain metadata**: build JSON and SVG in `tokenURI`, return `data:application/json;base64,...`; derive the traits from stored seeds, not from user text.
- **Token-bound accounts**: keep the NFT contract standard; create accounts through the ERC-6551 registry by `(implementation, salt, chainId, tokenContract, tokenId)`.

## 8. Best Practices

- Keep the minting function small: check phase, check proof or signature, check payment, update state, then mint.
- Reject `quantity == 0` and cap per-transaction batch size; enforce `MAX_SUPPLY` at the counter, not by reading `totalSupply` repeatedly.
- Use `immutable` for `MAX_SUPPLY` and price when they never change; use events for admin changes.
- Make sale phases explicit state, not implicit timestamps scattered in functions; timestamps are fine for scheduled opens but add an owner override.
- Use two-step ownership transfer (`Ownable2Step`) and put the final owner behind a multisig.
- Make metadata deterministic: generate JSON from a script, hash every file, and store the hashes in the repository.
- Support `contractURI()` for collection-level metadata only as a marketplace convention (ERC-7572 is Draft).
- Document the operator and approval model for users: `setApprovalForAll` grants control over all tokens of the collection to the operator.

## 9. Performance

- Minting cost is dominated by storage writes per token (owner slot, balance slot). A loop of `_safeMint` costs more per token than ERC-721A batch minting, but is simpler and compatible with OpenZeppelin extensions.
- ERC-721A shifts cost to later transfers of the first token of a batch because ownership is resolved lazily; the collection owner decides who bears the gas.
- `ERC721Enumerable` adds several storage writes per transfer and mint; avoid it and use an off-chain index or events to list a holder's tokens.
- Use `calldata` for proofs (`MerkleProof.verifyCalldata`) and `immutable` for constants.
- Use `ReentrancyGuardTransient` (OpenZeppelin 5.x; needs transient storage, available since Cancun) where the target chain supports it; otherwise `ReentrancyGuard`.
- Mint on an L2 for small tickets; check how the L2 charges for data (see ethereum-expert).
- Avoid on-chain string building in views that marketplaces call often; large SVG generation can exceed RPC gas limits for `eth_call`.

## 10. Security

- **Reentrancy through receiver callbacks**: `_safeMint`, `safeTransferFrom` and ERC-1155 transfers call the recipient contract. State that limits minting must be updated before the call; add `nonReentrant` as defense in depth. In an executed demonstration, a contract recipient re-entered a mint function that checked its limit before `_safeMint` but recorded it after, and minted 5 tokens against a limit of 2; moving the update first made the same attack revert.
- **Signature replay**: bind vouchers to `chainId` and the contract (EIP-712 domain), the recipient, the token id or quantity, a nonce and a deadline; reject expired vouchers; consume the nonce; use `SignatureChecker` if the signer can be a contract.
- **Merkle proofs**: double-hash leaves (OpenZeppelin tree format) so a 64-byte internal node cannot pass as a leaf; include the allowance in the leaf, and the caller in the leaf, never a client-supplied address.
- **Access control**: protect `setBaseURI`, `setSale`, `setAllowlistRoot`, `withdraw`; use `Ownable2Step`; avoid `tx.origin`.
- **Payment checks**: require exact `msg.value == price * quantity`; refund or reject extra; withdraw with `call` and check the result.
- **Randomness**: `block.prevrandao` and block hashes are manipulable by proposers and visible to contracts; do not use them to decide valuable traits. Use a commit-reveal scheme or a verifiable randomness service, and a provenance hash.
- **Metadata mutability**: an owner who can change `baseURI` can swap art after sale. Freeze it, or state clearly that it is mutable.
- **Approvals and phishing**: `setApprovalForAll` and `approve` signatures requested by fake sites drain wallets; this is a wallet and UX problem, but contracts should not add unneeded approval requirements.
- **Soulbound tokens** can still be burned or approved unless blocked; decide intentionally.
- **ERC-6551 accounts**: a token transferred into its own account becomes inaccessible (ownership cycle); a seller can empty an account right before a sale, so marketplaces and buyers need account-state checks, as the ERC's security section describes.
- **Supply integrity**: `MAX_SUPPLY` must be enforced in every mint path, including admin and voucher mints.
- **ERC-721A pitfalls**: `_startTokenId()` defaults to 0 (override to 1 if desired); the library does not call `_update`; check its migration notes about `supportsInterface` when combining with OpenZeppelin ERC-2981.

## 11. Testing

- Unit tests per phase: closed, allowlist, public, sold out, wrong payment, over limit, double claim, wrong proof, forged allowance, wrong caller.
- Interface tests: `supportsInterface` for `0x80ac58cd`, `0x5b5e139f`, `0x2a55205a`, `0x49064906` and, if used, `0xb45a3c0e`, and `false` for `0xffffffff`.
- Revert tests with custom errors: `vm.expectRevert(abi.encodeWithSelector(IERC721Errors.ERC721NonexistentToken.selector, id))` (error definitions live in `IERC721Errors` and `IERC1155Errors`).
- Reentrancy tests with a malicious receiver contract that mints or transfers inside `onERC721Received`; include a receiver that returns the wrong selector and one that reverts.
- Signature tests: valid voucher, replay, expired, wrong chain id in the domain, tampered fields, skipped nonce, signer rotation.
- Fuzz the quantity and payment arguments; add an invariant that `totalMinted <= MAX_SUPPLY` and that the contract balance equals proceeds minus withdrawals.
- Metadata tests: `tokenURI` for existing and nonexistent tokens, base URI change events, freeze behavior, and JSON validity of on-chain output (decode the base64 and parse).
- Run on a fork or testnet with a real marketplace listing and a contract-wallet mint before mainnet.

## 12. Review Checklist

- [ ] OpenZeppelin Contracts version is pinned (5.x) and only v5 APIs are used (`_update`, `Ownable(initialOwner)`, custom errors).
- [ ] Every external call (`_safeMint`, transfers, ETH sends) comes after state updates; `nonReentrant` is applied to mint functions.
- [ ] Supply cap is enforced in every mint path; quantity zero is rejected.
- [ ] Allowlist leaves are double-hashed and include the allowance; per-address usage is tracked.
- [ ] Vouchers bind chain, contract, recipient, nonce and deadline.
- [ ] `supportsInterface` covers ERC-721, metadata, ERC-2981, ERC-4906 (and ERC-5192 if used).
- [ ] `tokenURI` reverts for nonexistent tokens; metadata is frozen or its mutability is disclosed.
- [ ] Royalty is set through ERC-2981 with a valid receiver and basis points denominator of 10000.
- [ ] Admin functions use two-step ownership; the owner is a multisig after launch.
- [ ] Metadata files are pinned in more than one place and hashes are recorded.
- [ ] Contract is verified on the block explorer and tested with a contract-wallet recipient.

## 13. Production Notes

- Pin `@openzeppelin/contracts` to the exact version in `package.json` or as a git tag; do not rely on the npm `latest` tag, which can lag behind a release.
- Deploy sequence: deploy, verify source, set royalty, set allowlist root, test mint on the live chain with a small allowance, open the phases, then monitor events.
- After the sale: reveal, then `freezeMetadata()`, then transfer ownership to the multisig or renounce deliberately; keep a record of the final provenance.
- Marketplaces cache metadata. After changing URIs, emit ERC-4906 events; some marketplaces also offer manual refresh. Test with the marketplaces you target; their indexing rules are outside the standards.
- Royalties are paid only by marketplaces that choose to honor ERC-2981. The OpenSea operator filter registry is deprecated, so do not build new collections around it.
- Keep metadata available: pin on at least two independent services or your own IPFS node; NFT.Storage Classic stopped accepting new uploads on 2024-06-30.
- Gas spikes during popular mints; use a fixed price with allowlist phases rather than gas-war public mints, and cap per-wallet mints.
- Document all addresses (contract, royalty receiver, multisig, allowlist signer) and the signer key custody.

## 14. Examples

Merkle allowlist generated off-chain with `@openzeppelin/merkle-tree` (values as strings so the dump is JSON-serializable; the contract recomputes `keccak256(bytes.concat(keccak256(abi.encode(account, allowance))))`):

```js
import { StandardMerkleTree } from '@openzeppelin/merkle-tree';
import fs from 'node:fs';

const rows = [
  ['0x70997970C51812dc3A010C7d01b50e0d17dc79C8', '2'],
  ['0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', '1'],
];
const tree = StandardMerkleTree.of(rows, ['address', 'uint256']);
console.log('root', tree.root);                                   // pass to setAllowlistRoot(bytes32)
fs.writeFileSync('allowlist/tree.json', JSON.stringify(tree.dump()));

// Later, in an API that serves proofs:
const loaded = StandardMerkleTree.load(JSON.parse(fs.readFileSync('allowlist/tree.json', 'utf8')));
const proof = loaded.getProof(rows[0]);                           // bytes32[] for allowlistMint(quantity, allowance, proof)
```

EIP-712 voucher signed by the backend (viem); the domain must match the contract's `EIP712(name, version)` constructor arguments, the chain and the deployed address:

```js
import { privateKeyToAccount } from 'viem/accounts';

const signer = privateKeyToAccount(process.env.VOUCHER_SIGNER_KEY);  // load from a KMS in production
const domain = { name: 'Signed Mint', version: '1', chainId: 1, verifyingContract: CONTRACT_ADDRESS };
const types = {
  MintVoucher: [
    { name: 'to', type: 'address' },
    { name: 'tokenId', type: 'uint256' },
    { name: 'nonce', type: 'uint256' },
    { name: 'deadline', type: 'uint256' },
  ],
};
const message = { to, tokenId: 7n, nonce: 0n, deadline: BigInt(Math.floor(Date.now() / 1000) + 600) };
const signature = await signer.signTypedData({ domain, types, primaryType: 'MintVoucher', message });
```

Soulbound ERC-721 using the OpenZeppelin 5 `_update` hook (mint and burn allowed, moves between holders revert); `IERC5192` is declared next to it:

```solidity
function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
    address from = _ownerOf(tokenId);
    if (from != address(0) && to != address(0)) revert SoulboundToken(tokenId);
    return super._update(to, tokenId, auth);
}

function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
    return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
}
```

Full contracts for a collection with allowlist and public sale, a signature mint, a soulbound token, an on-chain SVG token and an ERC-1155 edition, with the reentrancy demonstration, are in [references/minting-patterns.md](references/minting-patterns.md).

## 15. Common Mistakes

- **Using v4 APIs with v5**: `_beforeTokenTransfer`, `_afterTokenTransfer`, `_exists`, `Counters`, and `Ownable()` without an argument no longer exist; migrate to `_update`, `_ownerOf`/`_requireOwned`, a plain counter and `Ownable(initialOwner)`.
- **Inventing standards**: only ERC-721, ERC-1155, ERC-2981, ERC-4906, ERC-5192 and ERC-6551 (Review) are standards here; "ERC-721A" is an implementation, not an EIP.
- **Counting on enforced royalties**: ERC-2981 only reports an amount. Marketplaces decide whether to pay it.
- **Updating mint counters after `_safeMint`**: the receiver callback re-enters before the counter changes.
- **Trusting `balanceOf(msg.sender)` as a mint limit**: tokens can be transferred out and minted again, and contract wallets can batch. Track minted counts separately.
- **Single-hashed Merkle leaves** or leaves without the allowance: allow second-preimage attacks or let users claim more than granted.
- **Signature vouchers without nonce, deadline or domain**: replay on other chains, other contracts and again after use.
- **Weak randomness for reveals**: `block.prevrandao` and `blockhash` can be influenced or predicted by proposers and contracts.
- **HTTP gateway URLs inside tokens**: gateways come and go; store `ipfs://CID/...` and let clients choose a gateway.
- **Unpinned IPFS content**: a CID only names data; if no node pins it, it disappears.
- **Mutable base URI after sale without disclosure**: owners can change art; freeze or document.
- **Forgetting `supportsInterface`** for ERC-2981 and ERC-4906 when combining bases: marketplaces will not detect them.
- **Pushing ETH in the mint path**: failures or reentrancy; accumulate and withdraw.
- **Assuming `eth_call` of `tokenURI` is cheap**: heavy on-chain rendering can run out of gas on public RPCs.

## 16. References

- [references/standards.md](references/standards.md): ERC-721, ERC-1155, ERC-2981, ERC-4906, ERC-5192, ERC-2309, ERC-6551 and ERC-721A details, statuses, interface ids, and the OpenZeppelin 5.x API for each, plus the v4 to v5 differences.
- [references/minting-patterns.md](references/minting-patterns.md): complete tested contracts for allowlist and public sale, EIP-712 signature mint, soulbound token, on-chain SVG and ERC-1155 edition; the reentrancy demonstration; Merkle and voucher details; tests to write.
- [references/metadata-and-storage.md](references/metadata-and-storage.md): metadata JSON for ERC-721 and ERC-1155, IPFS and Arweave practices, pinning, provenance and reveal, on-chain SVG, marketplace refresh and royalty behavior.
- Official docs: https://docs.openzeppelin.com/contracts/5.x/ , https://eips.ethereum.org/ , https://github.com/ethereum/ERCs , https://github.com/chiru-labs/ERC721A , https://docs.ipfs.tech/how-to/best-practices-for-nft-data/
