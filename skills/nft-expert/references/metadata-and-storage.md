# Metadata and Storage

Reference for NFT metadata JSON, where to store it, how to reveal and freeze it, on-chain metadata, and how marketplaces consume it. Verified against the ERC-721 and ERC-1155 texts, the IPFS best-practices guide for NFT data, the ar.io and Irys documentation summaries, the NFT.Storage Classic notice, and a generator script that was run with Node 22 and viem 2.57.13 (2026-10). Marketplace-specific field conventions are noted as conventions: the marketplace documentation could not be fetched during verification, so check each marketplace's current metadata guide.

## 1. Metadata JSON

ERC-721 metadata schema (from the ERC) has three fields:

```json
{
  "name": "Identifies the asset",
  "description": "Describes the asset",
  "image": "URI of a resource with MIME type image/*"
}
```

The ERC suggests images between 320 and 1080 pixels wide with an aspect ratio between 1.91:1 and 4:5.

Conventions that marketplaces and wallets commonly read in addition (not part of the ERC; confirm in each marketplace's docs): `attributes` as a list of `{ "trait_type": "...", "value": ... }` with optional `display_type` for numeric traits, `animation_url` for video, audio or HTML media, `external_url` for a project page, and `background_color`. Keep values simple and consistent across tokens so trait filters work.

Example token JSON for an IPFS-hosted collection:

```json
{
  "name": "Example #1",
  "description": "Example collection token.",
  "image": "ipfs://bafy.../1.png",
  "attributes": [{ "trait_type": "Edition", "value": 1 }]
}
```

ERC-1155 metadata (from the ERC): the `uri(id)` return value may contain `{id}`, which clients replace with the token id in lowercase hexadecimal, zero-padded to 64 characters, in the URI and in any JSON string value. The JSON uses the same `name`, `description` and `image` fields plus `decimals` and `properties`, and an optional `localization` object with `uri`, `default` and `locales`.

Collection-level metadata through `contractURI()` is an unofficial marketplace convention (ERC-7572 is Draft); return a small JSON with `name`, `description`, `image`, `external_link` and, for royalties on marketplaces that read it, `seller_fee_basis_points` and `fee_recipient` (check the marketplace documentation).

## 2. URIs inside the contract

- Store `ipfs://<CID>/<path>` or `ar://<id>`, not HTTP gateway links. Gateways change hostnames and policies; clients choose a gateway at display time. The IPFS best-practices guide recommends the `ipfs://` scheme with the CID, with the file name in the path when the CID is a directory.
- For uniform collections set a base URI that ends with `/` and let `tokenURI` append `<id>.json`. For ERC-1155 use `ipfs://<CID>/{id}.json` with files named by the zero-padded hexadecimal id.
- Avoid mutable names: IPNS, DNS-based gateways and centralized APIs can change contents silently. If mutability is needed (dynamic NFTs), say so in the project documentation, emit ERC-4906 events on changes, and limit who can change what.
- `tokenURI` must revert for nonexistent tokens (`_requireOwned`).

## 3. IPFS

- A CID is derived from the content: changing a byte changes the CID. Prefer CIDv1 (`bafy...`, base32) for new data; CIDv0 are 46 characters starting with `Qm` and convert to v1 without re-adding the data.
- Add a directory and keep its root CID: `ipfs add -r --cid-version 1 ./json` prints the CID of the directory; token files are then `ipfs://<dirCID>/<id>.json`.
- Pinning keeps content from being garbage-collected. Content addressing means you can change pinning providers without changing the URI. Pin the same CID on at least two independent providers or your own node, and monitor that pins stay active.
- NFT.Storage Classic stopped accepting new uploads and pins on 2024-06-30 and its notice points new work to partners such as Pinata and Lighthouse. Other services exist; check availability, pricing and retention terms before relying on one. Service SDKs change; read their current docs.
- The data must be reachable by clients: IPFS is a network, not storage by itself, so keep at least one well-connected node pinning the content.
- Keep source images and JSON in version control or backup, with their hashes, in case a provider loses data.

## 4. Arweave

- Arweave offers pay-once permanent storage. The ar.io documentation describes uploading NFT assets and metadata through the Turbo SDK (`@ardrive/turbo-sdk`) with an Arweave wallet: upload the image first, embed its transaction id in the metadata JSON, upload the metadata, then mint with the metadata URL. Irys documents a similar workflow; its tutorial code uses an older `@irys/sdk`, so verify SDK names and versions before copying.
- Use `ar://<transactionId>` or a gateway URL resolved at display time; verify with a gateway that the content matches before minting.
- Permanent storage covers availability, not correctness: upload the final files once and record their transaction ids and hashes.

## 5. Generating metadata and a provenance hash

The script below writes `1.json` to `N.json` and a `provenance.json` containing the keccak256 hash of every file and a combined provenance hash (hash over the ordered per-token hashes). Publish the provenance hash before the sale (for example as a public contract variable); after reveal anyone can recompute it from the pinned files. It validates its arguments and writes only numerically named files into the output directory.

```js
// Generates per-token metadata JSON and a provenance hash.
// Usage: node build-metadata.mjs <imagesCid> <supply> <outDir>
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { keccak256, concat, toHex } from 'viem';

const [imagesCid, supplyArg, outDir] = process.argv.slice(2);
const supply = Number(supplyArg);
if (!/^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{50,})$/.test(imagesCid ?? '') || !Number.isInteger(supply) || supply < 1 || !outDir) {
  console.error('usage: node build-metadata.mjs <imagesCid> <supply> <outDir>');
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const hashes = [];
for (let id = 1; id <= supply; id++) {
  const json = {
    name: `Example #${id}`,
    description: 'Example collection token.',
    image: `ipfs://${imagesCid}/${id}.png`,
    attributes: [{ trait_type: 'Edition', value: id }],
  };
  const body = JSON.stringify(json); // exact bytes that get pinned
  writeFileSync(path.join(outDir, `${id}.json`), body);
  hashes.push(keccak256(toHex(body)));
}
// Provenance: hash of the ordered per-token hashes. Publish it before the sale, store it in the contract.
const provenance = keccak256(concat(hashes));
writeFileSync(path.join(outDir, 'provenance.json'), JSON.stringify({ supply, imagesCid, hashes, provenance }, null, 2));
console.log('provenance', provenance);
```

Run: `node build-metadata.mjs <imagesCid> 10000 ./metadata/json`. Pin `./metadata/json` and use its directory CID in `setBaseURI("ipfs://<CID>/")`.

Reveal flow:

1. Sale with a placeholder base URI (a single image and JSON for every token, or a metadata server that returns the placeholder).
2. Publish the provenance hash before the sale and keep the files private until reveal.
3. After sell-out (or at a fixed time) set the real base URI; the contract emits `BatchMetadataUpdate(1, max)`.
4. If the order is shuffled, derive the shuffle offset from randomness the team cannot predict or influence (a verifiable randomness service or a commit-reveal), and publish how the offset maps ids to files. Do not use `block.prevrandao` or `blockhash` alone for anything valuable.
5. Call `freezeMetadata()` so the base URI cannot change again.

## 6. On-chain metadata

- Return `data:application/json;base64,<base64 of JSON>` where the JSON's `image` is `data:image/svg+xml;base64,<base64 of SVG>`. OpenZeppelin provides `Base64.encode` and `Strings.toString`.
- Keep SVG small: storage writes cost gas, and view functions that build large strings can hit RPC gas caps (`eth_call` limits are provider-defined).
- Escape user-provided text before it goes into SVG or JSON; better, restrict inputs to numbers and fixed sets of traits.
- Keep art data in contract code or SSTORE2-style code storage for large assets (check the library's docs and its audits), not in dynamic storage slots.
- Marketplaces render SVGs differently: avoid scripts, external references and unusual features; test on the target marketplaces.
- On-chain data is permanent only as long as the contract exists and the chain is available; that is usually the strongest guarantee available.

## 7. Marketplace behavior

- Marketplaces cache metadata. After changing a URI, emit `MetadataUpdate` or `BatchMetadataUpdate` (ERC-4906); indexers may honor it, and most marketplaces provide a manual refresh. Plan for delays.
- Royalties: marketplaces decide whether to pay the amount from `royaltyInfo`; the ERC says payment must be voluntary. The OpenSea operator filter registry is deprecated (its repository README says so), so do not design around blocked operators.
- Approvals: listing normally requires `setApprovalForAll(operator, true)` to a marketplace conduit or contract. Document this for users and consider reminding them to revoke unused approvals.
- Contract wallets (smart accounts, multisigs) must implement `onERC721Received` and `onERC1155Received` to receive safe mints and transfers; test minting to one.
- Test on the marketplace's testnet environment where available, with the exact `tokenURI`, `contractURI` and royalty setup you will launch.
- Delisting and lazy-minting flows differ by marketplace; if you use signature-based lazy minting, follow the marketplace's current guide for the order format and keep your own contract's checks authoritative.
