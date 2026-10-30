# Besu and Permissioned EVM Networks

Reference for building a permissioned Ethereum-compatible network with Hyperledger Besu: when it fits, QBFT consensus, genesis and node configuration, validator management, permissioning and its limits, free-gas networks, privacy with Paladin, key management with HSMs, and tokenization patterns including ERC-3643. Verified against Besu 26.10.2 (calendar versioning; the project and docs moved to the besu-eth organization and docs.besu-eth.org; Besu 26.x requires Java 25+), the Besu documentation sources for QBFT, permissioning and privacy, Paladin documentation as referenced there, and ERC-3643 (status Final) (2026-10). Solidity development itself is covered by solidity-expert, smart-contract-security-expert, hardhat-expert and foundry-expert.

## 1. When Besu fits

- Use Besu when the consortium wants EVM compatibility (Solidity contracts, Ethereum tooling such as ethers, Hardhat, Foundry, wallets, block explorers), a shared transparent ledger among known operators, and the option to connect to public Ethereum later or to deploy the same contracts on a public chain.
- Use Fabric when channel-level data partitioning, organization-level endorsement policies and private data collections are central requirements; see [hyperledger-fabric.md](hyperledger-fabric.md).
- Remember the default transparency: in a Besu network every node holds the full state and every permitted node can read all transactions. Confidentiality requires an extra mechanism (section 6) or keeping data off-chain.

## 2. Consensus: QBFT

QBFT is Besu's recommended enterprise proof-of-authority consensus. Validators take turns proposing blocks; a block is final once at least two thirds of validators sign it, so there are no forks and finality is immediate. IBFT 2.0 is also implemented; Clique is no longer supported.

- Minimum 4 validators to be Byzantine fault tolerant. Never lose more than one third of the validators: if more than 1/3 stop participating, block production stalls and recovery can take significant time.
- Spread validators across organizations and failure domains so no single organization controls a third or more of the set.
- Genesis `qbft` properties: `blockperiodseconds` (minimum block time, default 1), `emptyblockperiodseconds`, `epochlength` (default 30000; do not change on a running network), `requesttimeoutseconds` (default 1), `blockreward`, `validatorcontractaddress` (contract validator selection), `pertxgaslimit`, `startblock`, `miningbeneficiary`, plus advanced message limits.
- `blockperiodseconds` and `requesttimeoutseconds` trade latency against stability; keep the request timeout above the block period and test under load with the real network latency between sites. `transitions` allow changing block time, per-transaction gas limit or the validator management method at a future block.

Genesis sketch for a 4-validator network (generate `extraData` with Besu rather than writing it by hand):

```json
{
  "genesis": {
    "config": {
      "chainId": 1337,
      "berlinBlock": 0,
      "qbft": {
        "blockperiodseconds": 2,
        "epochlength": 30000,
        "requesttimeoutseconds": 4
      }
    },
    "nonce": "0x0",
    "timestamp": "0x0",
    "gasLimit": "0x47b760",
    "difficulty": "0x1",
    "mixHash": "0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {}
  },
  "blockchain": {
    "nodes": {
      "generate": true,
      "count": 4
    }
  }
}
```

Generate keys and the final genesis (including the validator list in `extraData`):

```bash
besu operator generate-blockchain-config --config-file=qbftConfigFile.json --to=networkFiles --private-key-file-name=key
```

Notes:

- Use a unique `chainId` (not 1337 and not a public chain's id) for production networks to prevent transaction replay across networks.
- The Besu docs recommend the latest protocol milestone for private networks (it implies earlier ones) so that new opcodes are available; see the genesis items reference for the milestone names your version supports, and align the Solidity `evmVersion` with the milestone. The example above keeps the milestone used in the documentation tutorial.
- Do not fund test accounts with known private keys in `alloc` on a real network.
- Pre-deploy system contracts (for example a validator contract, a registry, or a token factory) through `alloc` with `code` and `storage` when they must exist at genesis.

## 3. Running nodes

Typical validator command line (Besu 26.x, Java 25+). Bind JSON-RPC to a private interface or loopback and restrict the allowlists; the wide-open `--host-allowlist="*"` used in tutorials is not for production:

```bash
besu \
  --data-path=/var/lib/besu \
  --genesis-file=/etc/besu/genesis.json \
  --bootnodes=enode://<bootnode-public-key>@bootnode.consortium.internal:30303 \
  --profile=ENTERPRISE \
  --min-gas-price=0 \
  --p2p-host=0.0.0.0 \
  --rpc-http-enabled \
  --rpc-http-host=127.0.0.1 \
  --rpc-http-api=ETH,NET,QBFT \
  --metrics-enabled --metrics-host=127.0.0.1 \
  --permissions-nodes-config-file-enabled \
  --permissions-nodes-config-file=/etc/besu/permissions_config.toml
```

- `--profile=ENTERPRISE` applies the pre-configured enterprise/private profile; explicit options override profile values.
- The Docker image is `hyperledger/besu` (check the docs for the current registry and tags). Data must be on a persistent volume mounted at the data path.
- Keep the node key (`key` file in the data path) backed up and protected; for validators it defines the validator address (section 5).
- Separate validators (no public RPC, restricted peers) from RPC nodes that serve applications. Put an authenticated, rate-limited gateway or reverse proxy in front of RPC nodes; Besu supports JWT-authenticated RPC (`--rpc-http-authentication-enabled`) and TLS options, so check the option reference for your version.
- Enable only the RPC API groups needed (`ETH`, `NET`, `WEB3`; `QBFT` only on admin paths; avoid `ADMIN`, `DEBUG`, `TRACE` on shared endpoints).
- Monitor with the Prometheus metrics endpoint: peer count, block height and block time, validator participation (`qbft_getSignerMetrics`), pending transactions, and sync state.

## 4. Validator management

Two methods, selected in the genesis file:

- Block header validator selection (default): existing validators vote to add or remove a validator with `qbft_proposeValidatorVote(address, true|false)`; a majority of validators must propose the same change. Enable the `QBFT` JSON-RPC API on validator nodes' admin interface only. Use `qbft_getValidatorsByBlockNumber` to confirm and `qbft_discardValidatorVote` to drop a pending proposal.
- Contract validator selection: set `validatorcontractaddress` and deploy a validator contract at genesis; the contract owner or governance logic controls the set, which allows multi-signature or DAO-style governance and on-chain audit of changes. Transitions can swap methods on a running network.

Operating practices: document who may propose validator changes, keep an N+1 spare validator ready, rotate validator keys through add-then-remove (never drop below 4), and rehearse recovery from a stalled network on a test copy.

## 5. Key management and HSMs

- A validator's node address is its validator address. To keep the node key in a hardware security module, use a security module plugin such as the Besu HSM plugin (`besu-eth/besu-hsm-plugin`) with the `--security-module` option; check the plugin's documentation for supported HSMs and versions.
- Application signing keys (accounts that send transactions) should be held in an HSM, KMS or custody service; sign transactions through the service rather than exposing raw keys to application processes. Libraries such as ethers support external signers.
- Separate roles: validator keys, deployer/admin keys (use a multisig for contract upgrades and administration), and application hot wallets with low balances and strict limits.
- Document key ceremonies, backup and recovery, rotation intervals and revocation (removing a validator or blocking an account).

## 6. Permissioning and its limits

Besu supports local permissioning at node level:

- Node allowlist: `--permissions-nodes-config-file-enabled` restricts which nodes this node connects to.
- Account allowlist: `--permissions-accounts-config-file-enabled` restricts which accounts may submit transactions through this node.
- Configuration lives in a TOML file (`accounts-allowlist` and `nodes-allowlist` arrays), reloadable with `perm_reloadPermissionsFromFile` or updated with the `perm_*` API methods.

```toml
accounts-allowlist=["0xb9b81ee349c3807e46bc71aa2632203c5b462032"]
nodes-allowlist=["enode://<public-key>@10.0.1.10:30303", "enode://<public-key>@10.0.1.11:30303"]
```

Limits to design around: local permissioning protects the resources you control and is not enforced by the network. Each node has its own file, other nodes may have different rules, and a participant that ignores the rules cannot be stopped by your configuration. In a consortium, enforce the membership through (a) the validator set, since only validators produce blocks, (b) network controls (private connectivity, firewalls, mutual TLS between known peers), (c) application-layer authorization in smart contracts (role registries, allowlisted callers), and (d) written governance and legal agreements with technical audit (monitoring that peers conform). More complex rules can be implemented by writing a Besu plugin.

The Docker image does not use the permissions file options as in a binary install (the documentation notes this); mount the file and check the current Docker guidance.

## 7. Free gas and gas policy

Many consortium networks use a gas price of zero because validators are run by the participants.

- Set `--min-gas-price=0` on nodes and increase the genesis `gasLimit` if blocks should hold many transactions; the free-gas guide shows a very large block gas limit as an option, with the trade-off that blocks can take longer.
- EIP-7825 caps single-transaction gas at 16,777,216 (2^24). On QBFT networks that need larger deployment or migration transactions, set `pertxgaslimit` in the `qbft` configuration (0 disables the cap; a positive value must not exceed the genesis `gasLimit`).
- `contractSizeLimit` in genesis `config` can raise the deployed code size limit. Prefer modular contracts and proxies to unbounded code size.
- Free gas removes the economic spam barrier. Replace it with account allowlisting, rate limits at the RPC gateway, and monitoring; consider a nominal gas price with sponsored accounts if you need accounting.
- Some pre-crafted deployment transactions (for example the EIP-1820 registry) need gas available to the deployer; fund such accounts or pre-deploy the contract in `alloc`.

## 8. Privacy: Paladin and off-chain patterns

The Besu documentation now points to Paladin, a privacy layer developed under LF Decentralized Trust and separate from Besu, for private state on a Besu network. It runs alongside each Besu node, keeps private state in each node's encrypted local database, and anchors cryptographic commitments on the chain. Permissioning decides who can join; Paladin decides what permitted participants can see.

| Domain | Mechanism | Trust model | Use for |
|---|---|---|---|
| Pente | Privacy groups sharing an encrypted private EVM; only an encrypted state root lands on-chain | No trusted third party; group members endorse each execution | Confidential contracts and multi-party workflows |
| Noto | Private tokens with a notary that co-signs every transfer (UTXO hashes on-chain) | Notary sees all balances and transfers; participants see their own | Regulated assets needing issuer or regulator oversight |
| Zeto | Private tokens with ZK-SNARK proofs (Groth16) | No trusted third party; the proof replaces the co-signer | Maximum privacy, such as interbank settlement |

Production notes from the docs: the bundled WASM prover is suitable for development and adds minutes of warm-up on first use; production deployments typically use natively compiled circuits and a dedicated prover. Each domain needs its factory contract deployed before Paladin nodes start. Check the Paladin documentation for current releases and operational requirements before committing to it.

Alternative patterns when a privacy layer is not warranted:

- Keep the data off-chain in an access-controlled store and anchor only a hash (and a pointer or identifier) on-chain. Use salted hashes for low-entropy data.
- Use commit-reveal or hash-time-locked schemes for ordering-sensitive data.
- Use separate networks per confidentiality domain when parties and data sets are cleanly separable.
- Encrypt payloads to the intended recipients (envelope encryption) and store the ciphertext on-chain only if the retention and erasure implications are acceptable; see the data residency section of SKILL.md.

## 9. Tokenization and real-world assets

Principles:

- A token represents a claim whose legal effect is defined by contract and law, not by the code. Define the legal wrapper (issuer, SPV, custodian, redemption rights, which ledger is the register of record) before the token design.
- Regulated tokens need transfer restrictions: eligible holders (KYC, accreditation, jurisdiction), holding limits, lock-ups, freezes, forced transfers and recovery for lost keys, pausing, and issuer and agent roles.
- ERC-3643 (T-REX, status Final) is the Ethereum standard for permissioned security tokens: an ERC-20-compatible token whose transfers are checked against an identity registry (holder eligibility via on-chain identity claims) and compliance modules (rules such as country or holder-count limits), with agent roles for freezing, forced transfer and recovery. It fits when transfer eligibility must be enforced on-chain; it is heavier than a plain ERC-20 with an allowlist, which can be enough for closed consortia.
- Keep personal data off-chain: store only the minimum eligibility proof (a claim or status flag, issued by a trusted claim issuer), not names or documents.
- Delivery versus payment (DvP): settle the asset leg and the cash leg atomically. Options are a single contract on one chain holding both tokens (stablecoin, tokenized deposit or wholesale CBDC alongside the asset), an escrow contract with a timeout, or a hash-time-locked exchange across ledgers. Without atomic settlement, define the failure and reconciliation procedure.
- Corporate actions (dividends, coupons, voting, redemption): snapshot balances or use a registry that can compute entitlements at a record date; automate payouts from a funded contract and provide a manual path.
- Upgradeability: use audited proxy patterns with a multisig and a timelock, publish the upgrade policy, and plan emergency pause; changes to a regulated token generally require governance and legal sign-off.
- Oracles for price, NAV and reference data: see the oracle guidance in SKILL.md; for tokenized funds the administrator signs the NAV and a contract verifies the signature and timestamp.
- Audit the token and compliance contracts independently (smart-contract-security-expert), test with invariants and fuzzing (foundry-expert), and rehearse emergency procedures (pause, freeze, forced transfer, key recovery).

## 10. Application integration

- Use standard JSON-RPC clients (ethers, viem, web3 libraries) against RPC nodes; configure the chain ID, confirmations (QBFT has immediate finality, so one confirmation is final) and retry on dropped transactions.
- Nonce management per sending account is the usual source of stuck transactions; serialize sends per account or use a transaction service.
- Index events to an off-chain database for queries instead of polling contract state; handle restarts with a stored block cursor.
- Use the same contracts and tests on a local Besu or a development network in CI; foundry and Hardhat can target a local Besu node by URL and chain ID.
- Plan upgrades of Besu by rolling restarts of non-validators first, then validators one at a time, and read the release notes for consensus, genesis and Java requirements before each major update.
