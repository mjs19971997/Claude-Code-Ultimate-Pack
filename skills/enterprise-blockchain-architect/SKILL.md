---
name: enterprise-blockchain-architect
description: >-
  Designs permissioned and consortium blockchain systems with Hyperledger Fabric (channels, MSPs, private data collections, endorsement policies, Raft and SmartBFT ordering, chaincode in Go, Fabric Gateway clients) and Hyperledger Besu (QBFT, permissioning, Paladin privacy), including the choice between a database, a permissioned ledger and a public chain, consortium governance, PKI and HSM key management, tokenization of real-world assets (ERC-3643), oracles, interoperability and GDPR-compliant data handling. Absorbs the former hyperledger-fabric-expert skill. Use when deciding whether a blockchain is warranted, designing a multi-party network, writing Fabric chaincode or gateway clients, or planning governance and privacy. Not for Solidity contract coding (use solidity-expert), public-chain DeFi (use defi-expert), or general system architecture (use solution-architect).
license: MIT
metadata:
  version: "3.0.0"
---

# Enterprise Blockchain Architect

This skill covers architecture for multi-party, permissioned ledgers: first deciding whether a blockchain is the right tool, then designing membership, identity, consensus, privacy, smart contracts, integration and operations for a consortium. It absorbs the former hyperledger-fabric-expert skill, whose detail lives in a dedicated Fabric reference, and adds Hyperledger Besu for EVM-compatible permissioned networks.

> Verified against Hyperledger Fabric v3.1.5 (latest) and v2.5.16 (LTS), fabric-contract-api-go v2.2.4, fabric-gateway v1.13.0, Hyperledger Besu 26.10.2 (QBFT, Java 25+), Paladin privacy domains (Pente, Noto, Zeto) and ERC-3643 (Final) (2026-10).

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

- Covered: blockchain suitability, permissioned versus public chains, consortium governance and membership, X.509 PKI and MSPs, HSM key management, privacy (channels, private data, off-chain storage, zero-knowledge), Hyperledger Fabric networks and chaincode, Hyperledger Besu networks, tokenization and real-world assets, oracles, cross-ledger interoperability, data protection (GDPR), and operations.
- Not covered: Solidity language details (solidity-expert), EVM contract vulnerabilities and audits (smart-contract-security-expert), public Ethereum tooling (ethereum-expert, hardhat-expert, foundry-expert, ethersjs-expert), DeFi, DAO and NFT design (defi-expert, dao-expert, nft-expert), and Kubernetes manifests (kubernetes-expert).
- This is engineering guidance. Legal structure, regulatory classification of tokens and data protection conclusions need counsel and, for personal data, the data protection officer.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Fit test | A ledger is justified by several organizations writing shared state, no neutral operator all accept, and a need for independently verifiable history and shared rules. Otherwise a database with audit logs is simpler |
| Fabric | Execute-order-validate architecture: peers endorse and execute chaincode, an ordering service sequences transactions, peers validate and commit. Channels partition ledgers; policies decide who endorses |
| Fabric versions | v2.5.x is the LTS release (latest v2.5.16); v3.0 added SmartBFT Byzantine fault tolerant ordering and Ed25519 (channel capability `V3_0`); v3.1.x (latest v3.1.5) added chaincode read and write batching |
| Fabric ordering | Raft (crash fault tolerant, 3 or 5 nodes) or SmartBFT (tolerates malicious nodes, at least 3f+1 = 4 nodes). BFT consenters are identified by enrollment certificate |
| Fabric identity | MSP per organization, NodeOUs (`client`, `peer`, `admin`, `orderer`), Fabric CA with attributes, mutual TLS, PKCS#11 HSM support |
| Fabric privacy | Channels for whole-ledger isolation; private data collections keep values on authorized peers and hashes on the channel; implicit per-organization collections; transient data for inputs |
| Fabric clients | Fabric Gateway client APIs (Go, Node.js/TypeScript, Java). `fabric-sdk-node` is deprecated since Fabric v2.5 |
| Besu | EVM-compatible client; QBFT proof of authority with immediate finality (minimum 4 validators, tolerate fewer than 1/3 faulty); Java 25+ for Besu 26.x |
| Besu permissioning | Local node and account allowlists (not enforced network-wide); validator set via header votes or a validator contract; HSM-backed node keys through a security module plugin |
| Besu privacy | Paladin (LF Decentralized Trust): Pente (private EVM groups), Noto (notary-backed tokens), Zeto (zero-knowledge tokens) |
| Tokenization | ERC-3643 (T-REX, Final): permissioned security tokens with identity registry, compliance modules and agent controls such as freeze, forced transfer and recovery |
| Data protection | No personal data on-chain; store salted commitments and pointers; keep records in deletable off-chain stores in the right jurisdiction |
| Interoperability | Anchoring hashes, HTLCs, bridges with relay or light-client verification, SATP (IETF specification in progress, implemented by Hyperledger Cacti) |

## 3. Workflow

1. Qualify the use case: who writes, who reads, who is trusted, what must be provable later. Apply the fit test (section 4). Decide among a database, a shared service, a permissioned ledger and a public chain.
2. Define the consortium: members, roles (validators or orderers, peers, observers, regulators), legal structure, decision rights and exit rules. See [references/governance-identity-privacy.md](references/governance-identity-privacy.md).
3. Classify data: public, consortium-wide, bilateral, single-member confidential, personal. Choose the privacy mechanism per class.
4. Choose the platform: Fabric when channel-level partitioning and organization-level endorsement policies matter; Besu when EVM compatibility and Ethereum tooling matter. Pick consensus and node topology with failure domains and trust assumptions in mind.
5. Design identity and keys: CA hierarchy, MSPs or allowlists, HSM placement, certificate lifecycle, user-to-ledger identity mapping.
6. Design the on-chain model: minimal state, ownership and access rules, endorsement policies, events, upgrade path. Keep business data off-chain where possible.
7. Design integration: API layer, event stream to an off-chain read replica, oracle inputs, bridges. See [references/interoperability-oracles.md](references/interoperability-oracles.md).
8. Build on a local network, test with multiple organizations and failure injection, then run a pilot with real participants before production.
9. Operate: monitoring, backup and recovery, upgrades, certificate rotation, membership changes, incident runbooks, regular governance reviews.

## 4. Decision Rules

- Use a database when one party controls the data, when a trusted operator is acceptable, or when records must be erasable or heavily queried. Use a permissioned ledger when several mutually distrusting organizations share writes and rules, and no neutral operator is feasible.
- Use a public chain when open participation, censorship resistance or an existing asset ecosystem is the point; add a privacy layer or off-chain data for confidential parts.
- Choose Fabric for data partitioning by channel, private data collections, per-organization endorsement and a modular architecture. Choose Besu for Solidity/EVM tooling, token standards, and the option to share contracts with public chains.
- Fabric version: v3.1.x for BFT ordering or new performance features, v2.5.x for long-term-support stability. Raft ordering is enough when ordering organizations are mutually trusted not to be malicious.
- Ordering and validators: put them in different organizations so no single member can halt the network or collude alone (Raft: majority of nodes; BFT and QBFT: fewer than one third faulty).
- Privacy ladder: separate channel or network, then private data collection, then off-chain data with a hash on-chain, then cryptographic privacy (Paladin, zero-knowledge) only where the simpler options fail.
- Never put personal data on-chain. Put a random identifier and a salted or keyed commitment on-chain; keep the record off-chain.
- Prefer a few well-governed channels over many ad hoc ones; prefer private data collections when only some channel members need some values.
- Endorsement policies reflect the business trust model (for example both counterparties must endorse a bilateral trade), not convenience.
- Use HSM-backed keys for CAs, orderers or validators, and administrative signing; use multi-party approval for upgrades and token administration.
- Keep contracts small and boring: validation, ownership and state transitions on-chain; computation, search and reporting off-chain.

## 5. Coding Standards

- Chaincode and contracts are deterministic: no wall-clock time (use the transaction timestamp), no randomness, no external calls, no unordered iteration affecting writes.
- Validate every argument (format, length, range); reject unknown values; use typed errors with stable, non-sensitive messages.
- Authorize by caller identity from the platform (`GetClientIdentity` in Fabric, `msg.sender` in EVM contracts), never from a value passed in as an argument.
- Store minimal data in a stable JSON schema (explicit field names, version field when evolution is expected); use composite keys for secondary access in Fabric.
- Use pagination for list operations and cap page size; avoid unbounded iteration in a transaction.
- Do not keep running totals or counters on one key if many transactions update it; shard them or compute off-chain (MVCC conflicts in Fabric).
- Emit events for business facts and consume them off-chain; never include private or personal data in events.
- Version chaincode and contracts explicitly; document the upgrade procedure and compatibility with stored state.
- Client code shares one gRPC connection per peer endpoint, sets deadlines for every phase, and makes submissions idempotent.

## 6. Project Structure

```
.
├── network/
│   ├── fabric/
│   │   ├── configtx.yaml            # channel profiles, capabilities, policies, consenters
│   │   ├── crypto-config/           # generated per environment; never committed
│   │   ├── collections_config.json  # private data collections
│   │   └── compose-or-k8s/          # peer, orderer, CA, CouchDB deployment
│   └── besu/
│       ├── genesis.json             # QBFT genesis (generated extraData)
│       ├── permissions_config.toml  # node and account allowlists
│       └── config.toml              # node options
├── chaincode/
│   └── asset/                       # go.mod, contract, tests, META-INF/statedb/couchdb/indexes/
├── contracts/                       # EVM contracts for Besu (Solidity project)
├── gateway/                         # API service using Fabric Gateway or ethers
├── indexer/                         # event consumer building the off-chain read model
├── governance/
│   ├── consortium-agreement.md      # roles, decision rights, exit, cost sharing (reviewed by counsel)
│   ├── runbooks/                    # key rotation, member onboarding, incident response
│   └── data-map.md                  # what is on-chain, off-chain, where, and why
└── docs/architecture.md
```

## 7. Design Patterns

- **Hash-and-pointer**: personal or bulky data stored off-chain; the ledger holds a salted commitment, a location pointer, status and non-personal facts. See the example in section 14.
- **Channel per relationship group, collection per sensitive value**: coarse isolation with channels, fine-grained with private data collections.
- **Key-level (state-based) endorsement**: the owner's organization must endorse changes to its assets, in addition to chaincode-level policy.
- **Attribute-based access control**: certificate attributes (for example `role=issuer`) checked in chaincode.
- **Event-sourced read model**: block or chaincode events feed an off-chain database with checkpoints and idempotent writes.
- **Outbox for submissions**: business change and ledger intent are written in one database transaction; a worker submits to the ledger idempotently.
- **Signed oracle report**: external data enters as a signed message verified against a governed key, with freshness and replay checks.
- **Governed upgrades**: chaincode lifecycle approvals (Fabric) or multisig plus timelock on proxies (EVM).
- **Notary or auditor role** for regulated tokens: designed in from the start (Noto in Paladin, auditor in token frameworks, agent roles in ERC-3643).
- **Chaincode as a service** on Kubernetes for control over runtime and scaling.
- Platform specifics: [references/hyperledger-fabric.md](references/hyperledger-fabric.md), [references/besu-and-evm-permissioned.md](references/besu-and-evm-permissioned.md).

## 8. Best Practices

- Start from the business transaction and trust model, then derive the network; do not start from the technology.
- Agree governance and the data map before writing code. Technical policy should implement the legal agreement.
- Run a pilot with at least three organizations and a failure scenario (node down, member offboarded, key rotated) before scaling.
- Keep the on-chain footprint small; every byte is replicated to every member and kept for the life of the network.
- Provide each member a test environment that mirrors production topology and policies.
- Automate onboarding: CA enrollment, node deployment, channel join or validator vote, with checklists and audit logs.
- Keep infrastructure as code, version genesis and channel configuration, and review configuration changes like code.
- Plan for exit and archival: how a member leaves, how records are exported, how the network is wound down.
- Treat the ledger as one component: API gateway, identity provider, document store, monitoring and backup are part of the system.

## 9. Performance

- Fabric throughput is limited by endorsement (chaincode execution and signatures), ordering batch settings, validation and the state database. Tune batch size and timeout, keep endorsement policies as small as the trust model allows, and add endorsing peers per organization.
- Avoid hot keys: concurrent updates to one key cause MVCC read conflicts and retries. Use UTXO-like models, key sharding or off-chain aggregation.
- Fabric v3.1 chaincode batching (`StartWriteBatch`, `GetMultipleStates`) reduces peer-chaincode round trips for many-key transactions; it needs peer configuration and a recent `fabric-chaincode-go`.
- CouchDB rich queries need indexes and pagination; keep range queries bounded.
- Besu block time (`blockperiodseconds`) and request timeout set latency and stability; validators need low-latency links. Raise the block gas limit rather than raising the per-block time when many small transactions arrive.
- Use an off-chain read replica for queries and dashboards instead of reading the chain for every request.
- Measure with realistic endorsement policies and multiple organizations; single-organization benchmarks overstate throughput.
- Use the scalability-expert skill for load-test method and capacity planning.

## 10. Security

- Protect the root of trust: offline root CAs in HSMs, intermediate CAs per organization, short-lived leaf certificates where supported, and tested CA key rollover.
- Keep orderer, validator and admin private keys in HSMs or KMS; applications sign through a signing service or an HSM-backed signer. No private keys in repositories, images, logs or CI output.
- Mutual TLS between all network components; private connectivity between members; no public peer, orderer, validator, database or admin endpoints.
- Least privilege: separate admin, deployer and application identities; multi-party approval for upgrades, validator changes and token administration.
- Chaincode and contract authorization on every state-changing function, with owner checks, role attributes and tenant boundaries on both reads and writes.
- Data protection by design: no personal data in state, events, transaction arguments, certificates or logs; transient data for private inputs.
- Monitor for certificate expiry, unexpected membership or policy changes, endorsement failures and unusual signing volume.
- Audit smart contracts independently, test upgrades on a copy of production state, and rehearse emergency procedures (pause, key rotation, member removal).
- Do not rely on Besu local permissioning for network-wide enforcement; combine validator set control, network controls and contract-level authorization.

## 11. Testing

- Unit-test chaincode against a mocked stub and client identity (counterfeiter mocks as in the Fabric samples), including authorization failures and invalid arguments.
- Integration-test on a local multi-organization network (`fabric-samples/test-network`, or a local Besu QBFT network with four validators), including endorsement policy failures and private data access.
- Determinism test: run the same transaction on several endorsers and verify identical results.
- Upgrade test: install a new chaincode version, run the lifecycle approvals, and verify existing state is readable.
- Failure injection: stop an orderer or validator, partition a network segment, expire a certificate, replay a transaction, submit conflicting updates.
- Performance test with the real endorsement policy, realistic keys and data volume; measure MVCC conflict rate.
- Data protection test: confirm that logs, events and state contain no personal data fields.
- Contract tests (EVM): unit, fuzz and invariant tests, fork tests where relevant, and an external audit before production (foundry-expert, smart-contract-security-expert).

## 12. Review Checklist

- [ ] The decision record explains why a ledger is needed and why not a database or public chain.
- [ ] Consortium agreement covers membership, decision rights, liability, data protection roles, exit and costs.
- [ ] Orderers or validators are spread across organizations and meet the fault-tolerance threshold.
- [ ] Endorsement policies match the trust model; key-level policies exist where ownership matters.
- [ ] No personal data on-chain; commitments are salted; erasure path exists off-chain.
- [ ] CA hierarchy, HSM usage, certificate expiry monitoring and revocation procedures are documented and tested.
- [ ] Chaincode or contracts are deterministic, validated, authorized and tested, with an upgrade procedure.
- [ ] Clients use deadlines, idempotent submissions and checkpointed event consumption.
- [ ] Oracle inputs are signed, fresh, replay-protected and governed.
- [ ] Backup, disaster recovery, upgrade and incident runbooks exist and have been rehearsed.
- [ ] Network exposure is private; mutual TLS is on; admin interfaces are restricted.

## 13. Production Notes

- Fabric upgrades: orderers first, then peers, one at a time; enable new channel capabilities only after every node supports them (they cannot be rolled back). Read the release notes and upgrade guide for the exact versions.
- Fabric sizing: at least two peers per organization per channel, 3 or 5 Raft orderers or at least 4 BFT orderers across organizations, CouchDB with indexes and persistent volumes, ledger snapshots for fast peer rebuilds.
- Chaincode as a service with mutual TLS suits Kubernetes; align the chaincode runtime Go version with `go.mod` (current fabric-contract-api-go requires a recent Go toolchain).
- Observability: Prometheus metrics from peers, orderers and Besu nodes; alert on height divergence, commit latency, validator participation, certificate expiry, pending transactions and replica lag.
- Besu: never drop below four healthy validators; keep fewer than one third offline; take regular database backups; treat genesis changes as a coordinated network upgrade via transitions.
- Membership changes are governance events: record approvals, apply the technical change (channel update, validator vote), and verify.
- Key events (rotation, compromise, HSM migration) need rehearsed procedures and consortium-wide communication.
- Keep a data map and a record of processing for regulators; review it when the data model changes.
- Plan multi-year support: contract upgrades, cryptographic algorithm changes, retention of archived blocks and CA records.

## 14. Examples

Fabric `configtx.yaml` excerpt for a four-organization BFT ordering service (the shape follows the `configtx.yaml` in Fabric's `sampleconfig`; the aliases such as `*ChannelDefaults` and `*BankAOrderer` refer to definitions elsewhere in the file, and the certificate paths are generated per environment). `V3_0` must be enabled on the channel and all nodes must run v3.x:

```yaml
Capabilities:
  Channel: &ChannelCapabilities
    V3_0: true
  Orderer: &OrdererCapabilities
    V2_0: true
  Application: &ApplicationCapabilities
    V2_5: true

Profiles:
  ConsortiumChannelBft:
    <<: *ChannelDefaults
    Orderer:
      <<: *OrdererDefaults
      OrdererType: BFT
      BatchSize:
        MaxMessageCount: 500
        AbsoluteMaxBytes: 10 MB
      SmartBFT:
        RequestBatchMaxInterval: 200ms
        LeaderHeartbeatTimeout: 1m0s
        LeaderHeartbeatCount: 10
      ConsenterMapping:
        - ID: 1
          Host: orderer0.bank-a.example.com
          Port: 7050
          MSPID: BankAOrdererMSP
          Identity: crypto/bank-a/orderer0/signcerts/cert.pem
          ClientTLSCert: crypto/bank-a/orderer0/tls/client.crt
          ServerTLSCert: crypto/bank-a/orderer0/tls/server.crt
        # IDs 2, 3 and 4 follow the same shape for orderers run by three other organizations
      Organizations:
        - *BankAOrderer
        - *BankBOrderer
        - *BankCOrderer
        - *BankDOrderer
      Capabilities: *OrdererCapabilities
    Application:
      <<: *ApplicationDefaults
      Organizations:
        - *BankA
        - *BankB
        - *BankC
        - *BankD
      Capabilities: *ApplicationCapabilities
```

The anchors (`*BankAOrderer` and so on) refer to organization definitions with `OrdererEndpoints`; in BFT, every consenter should have a matching delivery endpoint and global `Orderer/Addresses` are not supported. See [references/hyperledger-fabric.md](references/hyperledger-fabric.md) for the full chaincode, lifecycle and client code.

Hash-and-pointer: a salted commitment for an off-chain record. The commitment goes into the ledger; the record and its salt stay in a deletable store. Verification recomputes the commitment, and erasure deletes the record and the salt:

```ts
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

/** Deterministic JSON: object keys sorted, no whitespace. Both writer and verifier must use the same form. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(",")}}`;
}

export interface Commitment {
  /** Goes on-chain: HMAC-SHA-256 of the record under a random per-record salt, hex-encoded. */
  readonly commitment: string;
  /** Stays off-chain next to the record. Deleting the record and salt makes the commitment unlinkable. */
  readonly salt: string;
}

export function commit(record: unknown): Commitment {
  const salt = randomBytes(32);
  const mac = createHmac("sha256", salt).update(canonicalJson(record)).digest("hex");
  return { commitment: mac, salt: salt.toString("hex") };
}

export function verify(record: unknown, saltHex: string, commitmentHex: string): boolean {
  const mac = createHmac("sha256", Buffer.from(saltHex, "hex")).update(canonicalJson(record)).digest();
  const expected = Buffer.from(commitmentHex, "hex");
  return expected.length === mac.length && timingSafeEqual(mac, expected);
}
```

Worked decision, trade finance consortium with four banks, a regulator and a logistics provider:

```text
Question                             Answer                                    Consequence
Who writes shared state?             Banks and the logistics provider          Multi-party writes: ledger is justified
Neutral operator available?          None accepted by all                      Consortium-run network
Confidential per pair of banks?      Yes (prices, limits)                      Private data collections per bank pair
Regulator access?                    Read-only, all channels                   Observer peer; collection membership for audit
Personal data (signatories)?         Yes                                       Off-chain store; ledger holds salted commitments
Ordering trust                       Banks may not trust each other fully      Fabric 3.1.x with SmartBFT, one orderer per bank
Keys                                 Bank-owned HSMs                           PKCS#11 for peers/orderers; gateway signs via HSM
Integration                          Bank core systems, ERP of logistics       Gateway API, checkpointed event consumers, outbox
```

## 15. Common Mistakes

- **Using a blockchain where a database suffices**: the consortium pays the operational cost without a trust gap to close.
- **Starting with technology before governance**: unclear decision rights stall upgrades and membership changes.
- **One organization running all orderers or validators**: it can halt or rewrite the network's behavior; spread them across members.
- **Storing personal data or raw documents on-chain** (even encrypted or hashed without a salt): erasure and data protection duties cannot be met.
- **Treating a private data collection as a replacement for channels**: hashes, transaction metadata and collection names remain visible to all channel members.
- **Passing private values as chaincode arguments** instead of transient data, which records them in the transaction.
- **Using `time.Now()`, random numbers or external calls in chaincode**: endorsements mismatch and transactions fail validation.
- **Endorsement policy `OR` across all organizations by default**: any one organization can unilaterally change state. Match the policy to the trust model.
- **Hot keys and global counters**: every concurrent update conflicts (MVCC) and throughput collapses.
- **Using the deprecated `fabric-sdk-node` or building custom endorsement logic in clients** instead of the Fabric Gateway APIs.
- **Relying on Besu local permissioning as network-wide enforcement**: it only constrains the node that runs it.
- **Free gas without any spam or abuse control** on the RPC layer and account allowlisting.
- **Fewer than four validators on a QBFT or BFT network, or losing a third at once**: the chain stalls.
- **Private keys on application servers or in CI**: use HSM-backed or remote signing.
- **Expired certificates**: unmonitored TLS or identity expiry can stop ordering or client access.
- **Bridges and oracles with a single trusted signer** holding large value, without caps, monitoring and governance.
- **No exit plan**: members leave, keys remain valid, and archives become unreadable.

## 16. References

- [references/hyperledger-fabric.md](references/hyperledger-fabric.md): the former hyperledger-fabric-expert skill: versions, network and channel design, MSP and identity, Go chaincode with fabric-contract-api-go, lifecycle commands, private data, chaincode as a service, Fabric Gateway clients in Go and TypeScript, operations.
- [references/besu-and-evm-permissioned.md](references/besu-and-evm-permissioned.md): QBFT networks, genesis and node options, validator management, permissioning limits, free gas, HSM keys, Paladin privacy, tokenization and ERC-3643.
- [references/governance-identity-privacy.md](references/governance-identity-privacy.md): ledger-versus-database decision aid, consortium governance, PKI and key management, privacy techniques, GDPR and data residency.
- [references/interoperability-oracles.md](references/interoperability-oracles.md): off-chain read models with checkpointed events, signed oracle reports in Go, cross-ledger interoperability, tokenization on Fabric, API layer.
- Official docs: https://hyperledger-fabric.readthedocs.io/ , https://hyperledger.github.io/fabric-gateway/ , https://docs.besu-eth.org/ , https://lfdt-paladin.github.io/paladin/head/architecture/overview/ , https://eips.ethereum.org/EIPS/eip-3643 , https://github.com/hyperledger/fabric-samples
