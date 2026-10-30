# Minting Patterns

Complete contracts for the common NFT sale and token designs, each compiled with solc 0.8.38 against OpenZeppelin Contracts 5.7.0 and exercised in an EVM harness (Cancun rules) with the cases listed in section 8. Verified against `@openzeppelin/contracts` 5.7.0, `@openzeppelin/merkle-tree` 1.0.8 and viem 2.57.13 (2026-10). The code is example code: add the project's own access policy, limits and audit before mainnet use.

## 1. Collection with Merkle allowlist, public sale and royalties

Design notes:

- Token ids start at 1 and `_nextTokenId` is advanced before the loop of `_safeMint` calls.
- `allowlistMinted[msg.sender]` is increased before the first external call.
- The allowlist leaf is `keccak256(bytes.concat(keccak256(abi.encode(msg.sender, allowance))))`, the same double hash that `StandardMerkleTree` uses; the caller is part of the leaf, so a proof cannot be used by another address.
- `ReentrancyGuardTransient` protects both mint functions (it uses transient storage, so the target chain must support Cancun).
- ERC-4906: changing the base URI emits `BatchMetadataUpdate(1, type(uint256).max)`; the contract advertises `0x49064906` in `supportsInterface`.
- `Ownable2Step` with `Ownable(initialOwner)`; proceeds are withdrawn by the owner with a checked `call`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable, Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {MerkleProof} from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import {ReentrancyGuardTransient} from "@openzeppelin/contracts/utils/ReentrancyGuardTransient.sol";
import {IERC4906} from "@openzeppelin/contracts/interfaces/IERC4906.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @title Collection
/// @notice ERC-721 collection with a Merkle allowlist, a public sale, ERC-2981 royalties and freezable metadata.
/// @author Example Labs
contract Collection is ERC721, ERC2981, Ownable2Step, ReentrancyGuardTransient, IERC4906 {
    using Strings for uint256;

    error SaleClosed();
    error SoldOut();
    error WrongPayment(uint256 expected, uint256 sent);
    error NotOnAllowlist();
    error AllowanceExceeded();
    error MetadataFrozen();
    error WithdrawFailed();

    uint256 public immutable MAX_SUPPLY;
    uint256 public immutable PRICE;

    bytes32 public allowlistRoot;
    bool public allowlistOpen;
    bool public publicOpen;
    bool public metadataFrozen;

    uint256 private _nextTokenId = 1; // token ids start at 1
    string private _baseTokenURI;
    mapping(address account => uint256 minted) public allowlistMinted;

    constructor(address initialOwner, uint256 maxSupply, uint256 price, address royaltyReceiver, uint96 royaltyBps)
        ERC721("Example Collection", "EXC")
        Ownable(initialOwner)
    {
        MAX_SUPPLY = maxSupply;
        PRICE = price;
        _setDefaultRoyalty(royaltyReceiver, royaltyBps); // bps out of 10_000; informational only
    }

    // ---- minting ----

    /// @param allowance Maximum quantity the allowlist leaf grants to msg.sender.
    function allowlistMint(uint256 quantity, uint256 allowance, bytes32[] calldata proof) external payable nonReentrant {
        if (!allowlistOpen) revert SaleClosed();
        // Leaf: double keccak256 of the abi.encode'd tuple, matching @openzeppelin/merkle-tree.
        bytes32 leaf = keccak256(bytes.concat(keccak256(abi.encode(msg.sender, allowance))));
        if (!MerkleProof.verifyCalldata(proof, allowlistRoot, leaf)) revert NotOnAllowlist();
        if (allowlistMinted[msg.sender] + quantity > allowance) revert AllowanceExceeded();
        allowlistMinted[msg.sender] += quantity; // effects before the safeMint callback
        _mintBatchTo(msg.sender, quantity);
    }

    function publicMint(uint256 quantity) external payable nonReentrant {
        if (!publicOpen) revert SaleClosed();
        _mintBatchTo(msg.sender, quantity);
    }

    function _mintBatchTo(address to, uint256 quantity) private {
        if (msg.value != PRICE * quantity) revert WrongPayment(PRICE * quantity, msg.value);
        uint256 first = _nextTokenId;
        if (first + quantity - 1 > MAX_SUPPLY) revert SoldOut();
        _nextTokenId = first + quantity; // update the counter before any external call
        for (uint256 i = 0; i < quantity; ++i) {
            _safeMint(to, first + i); // calls onERC721Received on contract recipients
        }
    }

    function totalMinted() external view returns (uint256) {
        return _nextTokenId - 1;
    }

    // ---- admin ----

    function setSale(bool allowlist_, bool public_) external onlyOwner {
        allowlistOpen = allowlist_;
        publicOpen = public_;
    }

    function setAllowlistRoot(bytes32 root) external onlyOwner {
        allowlistRoot = root;
    }

    function setBaseURI(string calldata newBaseURI) external onlyOwner {
        if (metadataFrozen) revert MetadataFrozen();
        _baseTokenURI = newBaseURI;
        emit BatchMetadataUpdate(1, type(uint256).max); // ERC-4906: refresh every token
    }

    function freezeMetadata() external onlyOwner {
        metadataFrozen = true;
    }

    function setDefaultRoyalty(address receiver, uint96 bps) external onlyOwner {
        _setDefaultRoyalty(receiver, bps);
    }

    function withdraw(address payable to) external onlyOwner {
        (bool ok,) = to.call{value: address(this).balance}("");
        if (!ok) revert WithdrawFailed();
    }

    // ---- views ----

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        string memory base = _baseURI();
        return bytes(base).length == 0 ? "" : string.concat(base, tokenId.toString(), ".json");
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC2981, IERC165) returns (bool) {
        return interfaceId == bytes4(0x49064906) || super.supportsInterface(interfaceId);
    }
}
```

## 2. EIP-712 signature mint

Design notes:

- `EIP712("Signed Mint", "1")` builds the domain separator from the name, version, `block.chainid` and the contract address, so a voucher is invalid on other chains and other contracts.
- The voucher binds `to`, `tokenId`, `nonce` and `deadline`. `_useCheckedNonce(to, nonce)` reverts unless `nonce` equals the current nonce of `to`, then increments it; vouchers for one recipient must be redeemed in order, and a used voucher cannot be replayed.
- Anyone can submit the voucher (relayers), but tokens always go to `to`.
- `SignatureChecker.isValidSignatureNow` accepts both EOA signatures and ERC-1271 contract signatures. Rotate the signer with `setVoucherSigner` if the key leaks.
- In OpenZeppelin 5.7.0 the `EIP712` name and version must fit in 31 bytes (`ShortString`).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable, Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

/// @title SignedMint
/// @notice Mints against EIP-712 vouchers issued by an off-chain signer.
/// @author Example Labs
contract SignedMint is ERC721, EIP712, Nonces, Ownable2Step {
    error VoucherExpired(uint256 deadline);
    error InvalidSignature();
    error TokenIdTaken(uint256 tokenId);

    // The domain (name, version, chainId, verifyingContract) is added by EIP712.
    bytes32 private constant VOUCHER_TYPEHASH =
        keccak256("MintVoucher(address to,uint256 tokenId,uint256 nonce,uint256 deadline)");

    address public voucherSigner;

    constructor(address initialOwner, address signer_)
        ERC721("Signed Mint", "SGM")
        EIP712("Signed Mint", "1")
        Ownable(initialOwner)
    {
        voucherSigner = signer_;
    }

    function setVoucherSigner(address signer_) external onlyOwner {
        voucherSigner = signer_;
    }

    /// @notice Redeem a voucher. The voucher binds recipient, token id, a per-recipient nonce and a deadline.
    function mintWithVoucher(address to, uint256 tokenId, uint256 nonce, uint256 deadline, bytes calldata signature)
        external
    {
        if (block.timestamp > deadline) revert VoucherExpired(deadline);

        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(VOUCHER_TYPEHASH, to, tokenId, nonce, deadline)));
        if (!SignatureChecker.isValidSignatureNow(voucherSigner, digest, signature)) revert InvalidSignature();

        _useCheckedNonce(to, nonce); // reverts if nonce is not the current one, then increments it
        _safeMint(to, tokenId);
    }
}
```

Backend signing (viem), with the key from a KMS or secret store in production:

```js
const signature = await signer.signTypedData({
  domain: { name: 'Signed Mint', version: '1', chainId, verifyingContract: contractAddress },
  types: { MintVoucher: [
    { name: 'to', type: 'address' }, { name: 'tokenId', type: 'uint256' },
    { name: 'nonce', type: 'uint256' }, { name: 'deadline', type: 'uint256' },
  ] },
  primaryType: 'MintVoucher',
  message: { to, tokenId, nonce, deadline },
});
```

Read the current nonce with `nonces(to)` before issuing a voucher. For payable mints add `price` and `quantity` to the typed data and check `msg.value` against them.

## 3. Soulbound token (ERC-5192)

`_update` is the single place where mints, transfers and burns pass; reverting for moves between two non-zero addresses blocks transfers (and `transferFrom`, `safeTransferFrom`) while keeping mint and burn. Approvals remain callable but cannot be used to move the token. `locked` reverts for nonexistent ids through `_requireOwned`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @dev ERC-5192 interface (interface id 0xb45a3c0e).
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);

    function locked(uint256 tokenId) external view returns (bool);
}

/// @title Soulbound
/// @notice Non-transferable ERC-721: mint and burn are allowed, transfers revert.
/// @author Example Labs
contract Soulbound is ERC721, Ownable, IERC5192 {
    error SoulboundToken(uint256 tokenId);

    uint256 private _nextTokenId = 1;

    constructor(address initialOwner) ERC721("Soulbound", "SBT") Ownable(initialOwner) {}

    function issue(address to) external onlyOwner returns (uint256 tokenId) {
        tokenId = _nextTokenId++;
        _mint(to, tokenId); // plain _mint: a contract recipient cannot reenter and the token is locked anyway
        emit Locked(tokenId);
    }

    function burn(uint256 tokenId) external {
        _update(address(0), tokenId, _msgSender()); // auth check: owner or approved
    }

    function locked(uint256 tokenId) external view returns (bool) {
        _requireOwned(tokenId);
        return true;
    }

    /// @dev _update is the single hook for mint, transfer and burn in OpenZeppelin Contracts 5.x.
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert SoulboundToken(tokenId);
        return super._update(to, tokenId, auth);
    }

    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }
}
```

## 4. Fully on-chain SVG token

`tokenURI` builds the SVG and the JSON on chain and returns a base64 data URI. Only numbers derived on chain are interpolated, so no user-controlled text reaches the markup. The seed uses `block.prevrandao` and is cosmetic only; do not use it for value-bearing traits. If user-provided text (names, messages) is ever rendered, escape XML special characters (`&`, `<`, `>`, `"`, `'`) in Solidity before concatenation.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @title OnChainSvg
/// @notice Token metadata and image generated entirely on chain.
/// @author Example Labs
contract OnChainSvg is ERC721, Ownable {
    using Strings for uint256;

    uint256 private _nextTokenId = 1;
    mapping(uint256 tokenId => bytes32 seed) private _seed;

    constructor(address initialOwner) ERC721("On-chain SVG", "OCS") Ownable(initialOwner) {}

    function mint(address to) external onlyOwner returns (uint256 tokenId) {
        tokenId = _nextTokenId++;
        _seed[tokenId] = keccak256(abi.encode(tokenId, block.prevrandao)); // not secure randomness; cosmetic only
        _mint(to, tokenId);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        uint256 hue = uint256(_seed[tokenId]) % 360;
        // Only numbers derived on chain are interpolated, so no user text can break out of the markup.
        string memory svg = string.concat(
            '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">',
            '<rect width="256" height="256" fill="hsl(', hue.toString(), ',70%,50%)"/>',
            '<text x="128" y="140" font-size="48" text-anchor="middle" fill="#fff">#', tokenId.toString(), "</text></svg>"
        );
        string memory json = string.concat(
            '{"name":"On-chain #', tokenId.toString(),
            '","description":"Fully on-chain SVG.","image":"data:image/svg+xml;base64,',
            Base64.encode(bytes(svg)),
            '","attributes":[{"trait_type":"Hue","display_type":"number","value":', hue.toString(), "}]}"
        );
        return string.concat("data:application/json;base64,", Base64.encode(bytes(json)));
    }
}
```

## 5. ERC-1155 edition with supply cap and royalties

In OpenZeppelin 5.x the override that replaced the v4 hooks is `_update(from, to, ids, values)`; `ERC1155Supply` needs it overridden together with `ERC1155`. ERC-2981 is inherited directly because there is no 1155 royalty extension.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC1155} from "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import {ERC1155Supply} from "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Edition1155
/// @notice Semi-fungible editions with a per-id supply cap.
/// @author Example Labs
contract Edition1155 is ERC1155, ERC1155Supply, ERC2981, Ownable {
    error CapExceeded(uint256 id);

    mapping(uint256 id => uint256 cap) public maxSupply;

    // "{id}" is replaced by clients with the lowercase, 64-character, zero-padded hex token id (ERC-1155).
    constructor(address initialOwner) ERC1155("ipfs://CID/{id}.json") Ownable(initialOwner) {}

    function setMaxSupply(uint256 id, uint256 cap) external onlyOwner {
        maxSupply[id] = cap;
    }

    function mint(address to, uint256 id, uint256 amount) external onlyOwner {
        if (totalSupply(id) + amount > maxSupply[id]) revert CapExceeded(id);
        _mint(to, id, amount, "");
    }

    // OpenZeppelin Contracts 5.x: _update replaces _beforeTokenTransfer / _afterTokenTransfer.
    function _update(address from, address to, uint256[] memory ids, uint256[] memory values)
        internal
        override(ERC1155, ERC1155Supply)
    {
        super._update(from, to, ids, values);
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC1155, ERC2981) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
```

## 6. Reentrancy through the receiver callback

`_safeMint` calls `onERC721Received` on contract recipients before the function returns. The first contract checks the limit before minting and records it afterward, so a malicious recipient re-enters `mint()` while the counter is stale. In the executed test an attacker contract that re-entered up to five times ended with 5 tokens against a limit of 2 on `VulnerableMint`, and `FixedMint` (state update first) reverted the whole attack.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

/// @dev INSECURE on purpose: the per-wallet limit is checked before _safeMint but recorded after it.
contract VulnerableMint is ERC721 {
    uint256 public constant LIMIT = 2;
    uint256 private _next = 1;
    mapping(address => uint256) public minted;

    constructor() ERC721("Vulnerable", "VUL") {}

    function mint() external {
        require(minted[msg.sender] < LIMIT, "limit");
        _safeMint(msg.sender, _next++); // external call to onERC721Received happens here
        minted[msg.sender] += 1; // too late: the receiver already re-entered
    }
}

/// @dev Same function with effects before the external call.
contract FixedMint is ERC721 {
    uint256 public constant LIMIT = 2;
    uint256 private _next = 1;
    mapping(address => uint256) public minted;

    constructor() ERC721("Fixed", "FIX") {}

    function mint() external {
        require(minted[msg.sender] < LIMIT, "limit");
        minted[msg.sender] += 1;
        _safeMint(msg.sender, _next++);
    }
}

interface IMint {
    function mint() external;
}

contract Attacker is IERC721Receiver {
    IMint public immutable target;
    uint256 public received;

    constructor(IMint target_) {
        target = target_;
    }

    function attack() external {
        target.mint();
    }

    function onERC721Received(address, address, uint256, bytes calldata) external returns (bytes4) {
        received++;
        if (received < 5) target.mint(); // re-enter while minted[] is still stale
        return IERC721Receiver.onERC721Received.selector;
    }
}
```

Defense in depth: update state first, add `nonReentrant` to every function that mints or transfers, and do not rely on `balanceOf(msg.sender)` for limits.

## 7. Allowlist and voucher operations

- Build the tree off-chain with `StandardMerkleTree.of(rows, ['address', 'uint256'])`; use string values when dumping to JSON because `bigint` is not JSON-serializable. `tree.root` goes into `setAllowlistRoot`; `tree.getProof(rowOrIndex)` returns the proof array.
- Publish the list or an API that returns proofs; keep the dumped tree (`tree.dump()`) under version control so the root can be reproduced.
- Changing the root during a sale invalidates outstanding proofs; plan phases so the root changes only between phases.
- A Merkle root cannot revoke one address; use a signature mint if revocation matters, or a mapping of banned addresses.
- With vouchers, keep the signer key off the web server, rate-limit issuance, store issued nonces, and set short deadlines (minutes).
- Per-wallet limits are only per address. Sybil resistance needs off-chain checks (KYC, social, payment history) that the voucher signer enforces.

## 8. Tests that were run against these contracts

- Collection: allowlist mint blocked while closed; allowlist mint succeeds with a proof built by `@openzeppelin/merkle-tree` (confirms the double-hash leaf matches); allowance exceeded reverts; a forged allowance reverts; a proof for another address reverts; wrong payment reverts; owner of token 1 is the minter; sold out when quantity exceeds remaining supply; public mint works; `totalMinted`; `tokenURI` equals `ipfs://CID/1.json`; `setBaseURI` reverts after `freezeMetadata`; `royaltyInfo` returns 5 percent of the sale price; `supportsInterface` is true for `0x49064906`, `0x2a55205a`, `0x80ac58cd`, `0x5b5e139f` and false for `0xffffffff`; non-owner calls are rejected; withdraw works.
- SignedMint: valid voucher relayed by a third party mints to `to`; replay reverts; expired voucher reverts; a voucher signed for another chain id reverts; a tampered token id reverts; the next nonce works; a skipped nonce reverts.
- Soulbound: issue works; transfer reverts; `locked` is true; `supportsInterface(0xb45a3c0e)` is true; burn by a stranger reverts and by the owner succeeds.
- OnChainSvg: `tokenURI` decodes to JSON with a valid SVG image.
- Edition1155: mint within cap works; exceeding the cap reverts; `totalSupply` is tracked; `supportsInterface(0xd9b67a26)` is true.
- Reentrancy: vulnerable mint exceeds its limit; fixed mint reverts.

Add on top of these in a real project: fuzz tests for quantity and payment, an invariant `totalMinted <= MAX_SUPPLY`, a receiver that returns a wrong selector, a receiver that reverts, and gas snapshots for mint at quantities 1, 5 and 10.

## 9. Variations

- **Pre-mint a fixed range**: `ERC721Consecutive` with `_mintConsecutive(treasury, 1000)` in the constructor; remember that `_update` logic does not run for the batch and that consecutive ids are bounded by `_maxBatchSize()` (5000 by default).
- **Per-token URIs**: inherit `ERC721URIStorage`; `_setTokenURI(id, uri)` emits `MetadataUpdate` (ERC-4906) automatically.
- **Burnable**: add `ERC721Burnable`; check that `totalMinted` and `totalSupply` semantics are what the UI expects.
- **Pausable transfers**: `ERC721Pausable` blocks all `_update` calls while paused, including mints and burns.
- **Enumerable**: only if an on-chain list of a holder's tokens is a hard requirement; otherwise index events.
- **ERC-721A**: replace the loop with `_mint(to, quantity)`; keep the same state-before-mint discipline and override `_startTokenId` to 1 when ids should start at 1.
- **Payment splits**: send proceeds to a splitter contract, or use pull-based withdrawals per beneficiary.
- **Dutch auction or raffle sales**: keep price calculation in a view function and refund in a separate claim step; avoid pushing refunds inside the mint.
