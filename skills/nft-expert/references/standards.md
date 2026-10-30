# NFT Standards and OpenZeppelin 5.x API

Reference for the standards used in NFT contracts, with statuses taken from the ethereum/ERCs repository and the OpenZeppelin Contracts 5.7.0 source (2026-10). Verified against ERC texts (721, 1155, 2981, 4906, 5192, 2309, 6551, 7572), OpenZeppelin Contracts 5.7.0 sources and changelog, and ERC721A 4.3.0 sources.

## 1. Status of each standard

| Standard | Status in ethereum/ERCs | Notes |
|---|---|---|
| ERC-165 interface detection | Final | `supportsInterface(bytes4)`; the basis for detecting every extension below |
| ERC-721 | Final | Non-fungible token standard |
| ERC-1155 | Final | Multi token standard |
| ERC-2981 | Final | Royalty information; payment is voluntary |
| ERC-4906 | Final | Metadata update events for ERC-721 (and by convention ERC-1155) |
| ERC-5192 | Final | Minimal soulbound NFTs |
| ERC-2309 | Final | Consecutive transfer extension for ERC-721 |
| ERC-6093 | Final | Custom errors for tokens; OpenZeppelin 5 uses them |
| ERC-6551 | Review | Token-bound accounts; not Final, so integration carries standard risk |
| ERC-7572 | Draft | `contractURI()` collection metadata; a marketplace convention in practice |
| ERC-7496 | Draft | Dynamic traits; do not depend on it |
| ERC-721A | Not an EIP | Chiru Labs implementation, created for Azuki's sale |
| Operator filter registry | Deprecated | OpenSea's on-chain royalty-enforcement tool; its repository marks it deprecated |

If a standard number is not in this table, check the ERC repository before using it; do not cite unverified numbers.

## 2. ERC-721

Interface (ERC-165 id `0x80ac58cd`): `balanceOf`, `ownerOf`, `safeTransferFrom` (with and without `data`), `transferFrom`, `approve`, `setApprovalForAll`, `getApproved`, `isApprovedForAll`; events `Transfer`, `Approval`, `ApprovalForAll`. Metadata extension (`0x5b5e139f`): `name`, `symbol`, `tokenURI`. The receiver interface `onERC721Received(address operator, address from, uint256 tokenId, bytes data)` returns `0x150b7a02`.

Behavior to remember:

- `safeTransferFrom` and `_safeMint` call `onERC721Received` on contract recipients and revert if the return value is not the selector. `transferFrom` and `_mint` do not check the recipient, so tokens can be locked in contracts that cannot move them.
- Approvals: `approve` gives one address control over one token; `setApprovalForAll` gives an operator control over all of the owner's tokens in this contract. Approvals for one token are cleared on transfer.
- Metadata JSON schema in the ERC has only `name`, `description` and `image`.

OpenZeppelin 5.7.0 building blocks (`@openzeppelin/contracts/token/ERC721/`):

| Contract | Purpose |
|---|---|
| `ERC721` | Base implementation. Constructor `(string name_, string symbol_)`. Internal: `_mint`, `_safeMint`, `_burn`, `_update`, `_ownerOf`, `_requireOwned`, `_isAuthorized`, `_checkAuthorized`, `_approve`, `_setApprovalForAll`, `_baseURI` |
| `extensions/ERC721URIStorage` | Per-token URIs through `_setTokenURI`; implements `IERC4906` and emits `MetadataUpdate`; `tokenURI` concatenates base and suffix when both exist |
| `extensions/ERC721Enumerable` | `totalSupply`, `tokenByIndex`, `tokenOfOwnerByIndex`; heavy on gas |
| `extensions/ERC721Burnable` | Public `burn` for owner or approved |
| `extensions/ERC721Pausable` | Blocks `_update` while paused |
| `extensions/ERC721Royalty` | ERC-2981 wired into ERC-721 |
| `extensions/ERC721Votes` | Voting power from NFT ownership (see dao-expert) |
| `extensions/ERC721Consecutive` | ERC-2309 batch pre-mint during construction |
| `extensions/ERC721Wrapper` | Wrap another ERC-721 |
| `utils/ERC721Holder` | Receiver that accepts safe transfers |
| `../common/ERC2981` | Royalty storage and `royaltyInfo` |

The ERC721 internal `_update(address to, uint256 tokenId, address auth)` returns the previous owner. Behavior:

- If `auth` is non-zero it checks that `auth` is authorized for the token owner (`_checkAuthorized`).
- It clears the single-token approval, updates balances and ownership, and emits `Transfer`.
- Mint: `from` is the zero address (the token has no previous owner). Burn: `to` is the zero address.
- `_mint(to, id)` reverts with `ERC721InvalidReceiver(address(0))` for the zero address and `ERC721InvalidSender(address(0))` if the token already exists. `_safeMint(to, id[, data])` additionally runs the receiver check.

Errors (from `IERC721Errors`, ERC-6093): `ERC721InvalidOwner`, `ERC721NonexistentToken`, `ERC721IncorrectOwner`, `ERC721InvalidSender`, `ERC721InvalidReceiver`, `ERC721InsufficientApproval`, `ERC721InvalidApprover`, `ERC721InvalidOperator`.

## 3. v4 to v5 differences that break NFT code

Taken from the OpenZeppelin 5.0 changelog and the 5.7.0 source:

| v4 | v5 |
|---|---|
| `_beforeTokenTransfer` and `_afterTokenTransfer` hooks (ERC20, ERC721, ERC1155) | Removed; override `_update` |
| `Ownable()` with `msg.sender` as owner | `Ownable(initialOwner)`; the zero address is rejected |
| `Counters` library | Removed; use a `uint256` counter |
| Revert strings | Custom errors |
| `_exists(tokenId)` | `_ownerOf(tokenId) != address(0)` or `_requireOwned(tokenId)` |
| `Address.isContract` | Removed |
| `SafeMath` | Removed (Solidity 0.8 checked arithmetic) |
| `ERC165Storage` | Removed; use inheritance and `supportsInterface` overrides |
| Pragma `^0.8.0` and similar | Token contracts require `^0.8.24` in 5.7.0 |
| `ERC721._transfer` overridable hook point | Use `_update` |

Other v5.x additions relevant to NFTs: `ERC721Crosschain` and `ERC1155Crosschain` (ERC-7786 based bridges) in 5.7.0, `Paymaster` family for ERC-4337, `Create3`, and `RateLimiter` utilities. Check the changelog for the exact version you pin; 5.7.0 also dropped the storage fallback of `EIP712` (name and version must fit in 31 bytes).

## 4. ERC-1155

Interface (`0xd9b67a26`): `balanceOf(account, id)`, `balanceOfBatch`, `setApprovalForAll`, `isApprovedForAll`, `safeTransferFrom(from, to, id, value, data)`, `safeBatchTransferFrom`; events `TransferSingle`, `TransferBatch`, `ApprovalForAll`, `URI(value, id)`. Receivers implement `onERC1155Received` (`0xf23a6e61`) and `onERC1155BatchReceived` (`0xbc197c81`). All transfers are "safe": a contract recipient must accept or the call reverts.

- `uri(id)` returns a URI template; clients replace `{id}` with the lowercase hexadecimal token id, zero-padded to 64 characters (the ERC example: id 314592 becomes `000000000000000000000000000000000000000000000000000000000004cce0`).
- No `ownerOf`, no per-id approvals. Approval is per operator for the whole contract.
- The ERC-1155 metadata JSON adds `decimals`, `properties` and localization fields to the ERC-721 fields.

OpenZeppelin 5.7.0 (`token/ERC1155/`): `ERC1155` (constructor `(string uri_)`; internal `_mint`, `_mintBatch`, `_burn`, `_burnBatch`, `_update(from, to, ids, values)`, `_setURI`, `_checkAuthorized`), `extensions/ERC1155Supply` (tracks `totalSupply(id)`; override `_update` in the derived contract when combining with `ERC1155`), `ERC1155URIStorage`, `ERC1155Burnable`, `ERC1155Pausable`, `ERC1155Crosschain`. There is no ERC-1155 royalty extension: inherit `ERC2981` and override `supportsInterface`.

Changelog notes: the 5.6.0 changelog changed batch behavior so that a batch transfer with exactly one id/value calls `onERC1155BatchReceived` (not the single callback) for contract recipients; handle both callbacks in receivers.

Errors (from `IERC1155Errors`): `ERC1155InsufficientBalance`, `ERC1155InvalidSender`, `ERC1155InvalidReceiver`, `ERC1155MissingApprovalForAll`, `ERC1155InvalidApprover`, `ERC1155InvalidOperator`, `ERC1155InvalidArrayLength`.

## 5. ERC-2981 royalties

- `royaltyInfo(uint256 tokenId, uint256 salePrice) returns (address receiver, uint256 royaltyAmount)`; interface id `0x2a55205a`. The amount is in the same unit as `salePrice`.
- The ERC states royalty payment must be voluntary: ordinary transfers cannot tell a sale from a gift, and marketplaces decide whether to implement the standard.
- OpenZeppelin `ERC2981`: `_setDefaultRoyalty(receiver, feeNumerator)`, `_setTokenRoyalty(tokenId, receiver, feeNumerator)`, `_deleteDefaultRoyalty`, `_resetTokenRoyalty`. The default denominator is 10000 (basis points), via `_feeDenominator()`. Errors: `ERC2981InvalidDefaultRoyalty`, `ERC2981InvalidDefaultRoyaltyReceiver`, `ERC2981InvalidTokenRoyalty`, `ERC2981InvalidTokenRoyaltyReceiver`.
- Combine with ERC-721: `supportsInterface(bytes4) public view override(ERC721, ERC2981, IERC165)` (or use `ERC721Royalty`). Combine with ERC-1155: `override(ERC1155, ERC2981)`.
- Lock down who can change the royalty (owner, multisig, or immutable) and consider a maximum.
- Enforcement approaches (transfer restrictions, operator filtering) are not part of the standard and carry composability costs. The operator filter registry is deprecated.

## 6. ERC-4906 metadata updates

- Events: `MetadataUpdate(uint256 _tokenId)` and `BatchMetadataUpdate(uint256 _fromTokenId, uint256 _toTokenId)`; the ERC says they MUST be emitted when the JSON metadata of a token or range changes. Interface id `0x49064906`.
- OpenZeppelin `ERC721URIStorage` implements `IERC4906`, advertises the interface and emits `MetadataUpdate` in `_setTokenURI`. For a base URI change, emit `BatchMetadataUpdate(firstId, lastId)` yourself.
- The event helps indexers and marketplaces refresh but is not guaranteed to be honored.

## 7. ERC-5192 soulbound tokens

- Interface id `0xb45a3c0e`: `locked(uint256 tokenId) returns (bool)`, events `Locked(uint256)` and `Unlocked(uint256)`. A locked token's transfer functions must revert. If a token is minted locked, emit `Locked`.
- OpenZeppelin 5 does not ship an ERC-5192 contract; implement with an `_update` override (see the main skill).
- Design questions the standard does not answer: burn rights, recovery for lost wallets (an issuer-controlled reissue/burn), and approval functions (block `approve` or leave it harmless).

## 8. ERC-2309 and ERC721Consecutive

- ERC-2309 defines `ConsecutiveTransfer(fromTokenId, toTokenId, fromAddress, toAddress)` so a contract can create a range of tokens in the constructor with one event.
- OpenZeppelin `ERC721Consecutive`: `_mintConsecutive(to, batchSize)` only in the constructor; `_maxBatchSize()` defaults to 5000; `_update` hooks are not called for consecutive mints, so logic that must run on mint (supply tracking, voting units) needs extra care. Regular `_mint` is rejected during construction (`ERC721ForbiddenMint`) and allowed afterward, so ids minted after the constructor must start above the consecutive range (`_firstConsecutiveId()` and the batch size define where it ends).

## 9. ERC-721A

- `ERC721A` (chiru-labs/ERC721A, 4.3.0): constructor `(name, symbol)`, `_mint(to, quantity)`, `_safeMint(to, quantity)`, `_nextTokenId()`, `_totalMinted()`, `_numberMinted(owner)`, `_setAux/_getAux`, `_burn`. `_startTokenId()` returns 0 by default; override to start at 1.
- Ownership of a batch is stored once at the first token id; `ownerOf` of a later token scans backward to find it, which makes later transfers of the first token in a batch more expensive.
- Extensions: `ERC721AQueryable`, `ERC721ABurnable`, `ERC4907A` (rental). Compiler `^0.8.4`.
- It is not built on OpenZeppelin's `ERC721`, so OpenZeppelin extensions that override `_update` do not apply. Read the project's migration guide before combining with OpenZeppelin ERC-2981: `supportsInterface` needs an explicit override.
- Use `_safeMint` with `nonReentrant` and update counters first, as with any safe mint.

## 10. ERC-6551 token-bound accounts

- Status Review: the specification could still change.
- A singleton registry deployed at `0x000000006551c19487814612e58FE06813775758` creates deterministic accounts: `createAccount(implementation, salt, chainId, tokenContract, tokenId)`; `account(...)` computes the address without deploying. Accounts are proxies (ERC-1167 based) of an implementation, bound to a token by constants appended to the bytecode.
- An account implements `token()` (chain id, contract, id), `state()`, `isValidSigner(signer, context)` and `execute(to, value, data, operation)`; the owner is whoever owns the NFT. Accounts can hold assets and own other NFTs.
- Risks stated by the ERC: sellers can empty an account just before a sale (marketplaces and buyers need state checks or a lock); transferring a token into its own account (or any ownership cycle) makes everything inaccessible.
- Use an audited account implementation; choose chain-specific behavior deliberately since the account address is the same across chains but control may differ.
