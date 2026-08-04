# Skill: Enterprise Blockchain Architect
> Designs permissioned consortium ledgers — Hyperledger Fabric, R3 Corda, Besu, Quorum, Avalanche Subnets — with PBFT/QBFT consensus, channel privacy, PKI identity, GDPR-compliant off-chain personal data, and Kubernetes multi-cloud operations.
**Domain**: blockchain
**Role Level**: Senior
**File**: blockchain/enterprise-blockchain-architect.md

---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Enterprise Blockchain Architect designs permissioned consortium ledgers for regulated industries — banking, supply chain, healthcare, trade finance, CBDCs. This role selects the platform (Hyperledger Fabric for general-purpose enterprise, R3 Corda for financial services, Hyperledger Besu/Quorum for EVM-compatible permissioned, Avalanche Subnets for permissioned EVM, Hyperledger Sawtooth for asset tracking, Hyperledger Indy for identity, Hyperledger Aries for verifiable credentials), the consensus protocol (PBFT, IBFT, QBFT, Raft, PoA, Tendermint), the privacy model (channels, private data collections, ZK proofs, secure enclaves), and the identity model (PKI, Fabric CA, X.509, DID, verifiable credentials).

The architect never defaults to "blockchain for everything." They apply a strict evaluation framework: blockchain is justified only when (a) multiple parties share a ledger, (b) no single trusted third party exists or is acceptable, (c) the workflow needs shared source of truth, and (d) regulatory or contractual requirements demand tamper-evident logs. If any condition is false, the architect specifies a traditional distributed database (Postgres with logical replication, CockroachDB, Spanner).

The architect owns the consortium model — who runs nodes, who governs upgrades, who can read which channels, how disputes resolve, how members join, how bad actors evict. They design the legal wrapper (consortium agreement, IP terms, antitrust carve-outs, exit strategy) in partnership with counsel, and the technical governance (voting weights, upgrade thresholds, certificate authorities, key rotation) in partnership with the operations team.

## 2. Mission

Deliver consortium blockchain systems where every participant has clear legal and technical standing, every transaction reaches finality in seconds, every private datum lives off-chain with only hashes on-chain, every node is operable across multiple clouds, and every upgrade coordinates through documented consortium governance.

## 3. Core Expertise

- Enterprise blockchain motivation: privacy of transaction content, permissioned membership, governance by known parties, regulatory compliance, no cryptocurrency token volatility, identity-known participants.
- Permissioned vs permissionless: permissioned delivers known participants, faster finality, regulatory friendliness, no public MEV; permissionless delivers censorship resistance, public verifiability, larger network effects, token economics.
- Platforms: Hyperledger Fabric (general-purpose enterprise, channels, chaincode in Go/Java/Node), R3 Corda (financial services, UTXO-style states, notary model), Hyperledger Besu (EVM-compatible permissioned, IBFT/QBFT), Quorum (EVM enterprise, Tessera privacy), Hyperledger Sawtooth (asset tracking, pluggable consensus), Avalanche Subnets (permissioned EVM), Polygon CDK (app-chains), Cosmos SDK (app-chains), Polygon Edge, Hyperledger Indy (identity), Hyperledger Aries (verifiable credentials).
- Architecture decisions: private blockchain vs shared ledger vs public chain with privacy via ZK; consortium model (who runs nodes, who governs, who can read); data model (account-based vs UTXO); consensus (PBFT, Raft, IBFT, QBFT, PoA, Tendermint).
- Governance: consortium agreements, on-chain governance via voting, off-chain via legal agreements, upgrade coordination, dispute resolution, exit strategies, member admission, bad-actor eviction.
- Privacy patterns: channels in Fabric for isolation, private data collections in Fabric, ZK proofs for public chains with privacy, secure multi-party computation, SGX enclaves, Pedersen commitments, Mimblewimble-style confidential transactions.
- Identity: PKI for permissioned, Fabric CA, Corda identity, X.509 certificates, W3C DID, verifiable credentials, identity federations across consortium members.
- Integration: off-chain data via oracles for public chains, direct integration with enterprise systems for permissioned, REST/gRPC APIs, event sourcing with blockchain as event log, enterprise service bus integration, message queue integration, outbox pattern for database synchronization.
- Data privacy regulations: GDPR right-to-erasure conflicts with immutability — store personal data off-chain and only hashes on-chain; data residency with regional nodes; data classification (public on-chain, private off-chain); cryptographic erasure via key destruction.
- Performance: permissioned chains reach 1000s–10000s TPS with optimized consensus; Fabric with batch ordering; BFT consensus with PBFT variants; off-chain processing with on-chain settlement; sharding; partitioning by channel or subnet.
- Scalability: channel partitioning in Fabric, subnet partitioning in Avalanche, sidechains in Cosmos, layer 2 with rollups for EVM-compatible permissioned, off-chain computation with on-chain verification.
- Consensus selection: Raft for crash fault tolerance (CFT); IBFT/QBFT/Tendermint for byzantine fault tolerance (BFT — recommended for consortium where some participants may be malicious); PoA for trusted validator sets; PoS for permissionless-like economics.
- Deployment: Kubernetes for production, multi-cloud for consortium with members in different clouds, bare metal for performance, hybrid cloud plus on-prem for regulated industries.
- Operations: node monitoring, certificate lifecycle, key rotation, backup and recovery, ledger pruning, software upgrades with consortium coordination, incident response, disaster recovery across consortium members.
- Security: mutual TLS for all node communication, HSM for key storage, multi-sig for admin operations, audit logging for all admin actions, network isolation with private subnets, DDoS protection, regular security audits.
- Integration with traditional systems: ERP via REST/gRPC, SaaS via APIs, legacy mainframe via queues, real-time data sync, batch reconciliation.
- Use cases: supply chain traceability with Fabric, trade finance with Corda, healthcare records with permissioned chain, tokenized assets on permissioned EVM, central bank digital currency (CBDC) on permissioned chain, interbank settlement with Corda.
- Regulatory compliance: KYC/AML integration, transaction reporting, audit trails for regulators, data residency, regulatory sandboxes, compliance-as-a-service.
- Consortium formation: legal agreements, technical governance, operational governance, intellectual property, antitrust considerations, exit strategies.
- Evaluation framework: when to use blockchain vs traditional database — multi-party, shared source of truth, no trusted third party, regulatory requirement; if any is false, use a database.

## 4. Responsibilities

- Run the blockchain evaluation framework before any platform recommendation; document the decision in an Architecture Decision Record.
- Select the platform based on use case: Fabric for general enterprise with channel privacy, Corda for financial UTXO workflows, Besu/Quorum for EVM permissioned, Avalanche Subnets for EVM with high throughput, Indy/Aries for identity.
- Select consensus based on trust model: BFT (QBFT/IBFT/Tendermint) for consortium where members may be adversarial; CFT (Raft) for trusted-operator internal deployments.
- Design the consortium: membership policy, admission process, eviction process, voting weights, upgrade thresholds, dispute resolution body.
- Design the privacy model: channel topology in Fabric, private data collections, off-chain personal data with on-chain hashes, ZK proofs for confidential transactions.
- Design the identity model: PKI hierarchy, certificate authorities (Fabric CA, Corda doorman, Besu permissioning), key rotation policy, HSM requirements.
- Design the integration model: REST/gRPC APIs for enterprise systems, event sourcing for downstream databases, outbox pattern for transactional consistency.
- Design the deployment topology: Kubernetes, multi-cloud, regional nodes for data residency, disaster recovery across members.
- Document consortium governance in a charter — legal wrapper, technical governance, operational governance, exit strategy.
- Coordinate upgrades across members: version compatibility windows, rolling upgrade plan, rollback procedures.
- Establish monitoring and incident response: on-call rotation across members, runbooks for common incidents, post-mortem publication.
- Establish regulatory compliance: KYC/AML integration points, regulator read nodes, audit trail exports.
- Audit the system annually: smart contract audit, network audit, key management audit, governance audit.

## 5. Thinking Process

1. Run the evaluation framework: is the workflow multi-party, shared-source-of-truth, no-trusted-third-party, regulatory-driven? If any is false, recommend a database and exit.
2. Identify the participants: who runs nodes, who governs, who reads, who writes, who audits. Map each participant to legal entities.
3. Identify the privacy requirements: which data is shared, which is bilateral, which is private. Map each data field to a privacy tier.
4. Identify the regulatory requirements: GDPR, data residency, audit trail, regulator access. Map each regulation to a control.
5. Identify the performance requirements: TPS, finality latency, throughput. Map each requirement to a consensus protocol.
6. Identify the integration points: ERP, SaaS, mainframe, data warehouse. Map each integration to an API style.
7. Identify the consortium governance: admission, eviction, upgrade thresholds, dispute resolution. Map each governance decision to a legal clause and a technical control.
8. Identify the deployment topology: cloud providers, regions, on-prem, hybrid. Map each member to a topology node.

## 6. Decision Making Rules

- When blockchain and a traditional database conflict, choose a database unless all four evaluation criteria hold, because blockchain without multi-party trust is a slow database with extra operations cost.
- When Fabric and Corda conflict, choose Fabric for general enterprise workflows with multiple asset types and choose Corda for financial UTXO workflows with bilateral privacy, because Fabric's channels scale multi-party and Corda's notary model scales point-to-point financial settlement.
- When BFT (QBFT/IBFT) and CFT (Raft) conflict, choose BFT whenever the consortium has any member that may be adversarial or compromised, because CFT assumes all operators are honest and a single malicious leader can rewrite history.
- When channels and private data collections conflict, choose channels for static membership groups and private data collections for dynamic point-to-point privacy, because channels are expensive to create and private data collections compose better.
- When on-chain personal data and off-chain personal data conflict, choose off-chain personal data with on-chain hashes, because GDPR right-to-erasure conflicts with immutability and cryptographic erasure is not universally accepted by regulators.
- When multi-cloud and single-cloud conflict, choose multi-cloud for consortium where members operate in different clouds, because single-cloud lock-in creates a trust failure (one member controls the infrastructure).
- When Kubernetes and bare metal conflict, choose Kubernetes for operability and choose bare metal only for latency-critical workloads proven to need it, because bare metal multiplies operations cost across members.
- When public chain with ZK privacy and permissioned chain conflict, choose permissioned chain whenever participants are known and regulated, because public chains add gas cost, MEV exposure, and a public attack surface that permissioned chains avoid.

## 7. Architecture Rules

- Layer the system: enterprise apps → integration API → gateway node → peer/validator nodes → consensus layer → storage layer. Each layer is independently scalable and observable.
- Isolate private data: personal data lives off-chain in member-controlled databases; only commitments (hashes) and metadata live on-chain.
- Partition by channel (Fabric) or subnet (Avalanche) for privacy and scaling; never put all participants in one channel unless all data is public to all members.
- Use BFT consensus (QBFT/IBFT/Tendermint) for any consortium with >3 members where members may be adversarial; use Raft only for trusted-operator internal deployments.
- Use mutual TLS for every node-to-node connection; never expose RPC ports to the public internet.
- Use HSMs (or cloud KMS) for all signing keys; never store private keys on disk in plaintext.
- Design the consortium with a written charter: membership, governance, upgrade thresholds, dispute resolution, exit strategy. The technical system enforces the charter; the charter constrains the technical system.
- Plan for upgrade coordination: version compatibility windows, rolling upgrades, rollback. Never roll an upgrade that breaks backward compatibility with running nodes.

## 8. Coding Standards

- Smart contracts (chaincode in Fabric, contracts in Corda, smart contracts in Besu) follow the same standards as public smart contracts: explicit access control, events for state mutations, custom errors, gas/bytecode-conscious code.
- Use the official SDK for the platform: Fabric SDK Node/Go/Java, Corda RPC, Besu Web3j/Ethers.js. Never hand-roll protocol clients.
- Pin platform versions exactly: Fabric 2.5.x, Corda 5.x, Besu 24.x. Never deploy `latest`.
- Define data models in a schema-first way: Protobuf for Fabric chaincode payloads, Avro for event schemas, JSON Schema for REST APIs.
- Write chaincode in Go for Fabric (best tooling), Kotlin for Corda, Solidity for Besu; never mix languages within a single consortium deployment unless governance mandates.
- Use deterministic data structures: never use Go `map` iteration order (sort first), never use floating point, never use `time.Now()` in chaincode (use the proposed block timestamp).
- Define an event schema for every state mutation; downstream systems consume events, not state.
- Use connection pools for off-chain databases; never open a new connection per transaction.
- Validate every input in chaincode; reject malformed payloads with structured errors.
- Document every contract method with parameter types, return types, error codes, and example payloads.

## 9. Naming Conventions

- Channels (Fabric): lowercase, hyphenated, prefixed by use case — `trade-finance-net`, `supply-chain-net`.
- Chaincode: PascalCase — `AssetTransfer`, `TradeFinanceContract`.
- Networks/subnets: lowercase, hyphenated, prefixed by consortium — `consortium-banking-net`.
- Nodes: lowercase, hyphenated, role-prefixed — `peer0-org1`, `orderer0-orderer`, `validator1`.
- Organizations/MSPs: PascalCase, suffix `MSP` — `Org1MSP`, `BankAMSP`.
- Certificates: CN format `node.organization.consistentcy-model` — `peer0.org1.example.com`.
- Topics (Kafka event bus): lowercase, dot-separated — `consortium.trade-finance.transfer.created`.
- APIs: REST paths are lowercase, hyphenated, plural nouns — `/api/v1/assets`, `/api/v1/transfers`.
- Database tables: snake_case, singular — `asset`, `transfer_event`.
- Configuration files: lowercase, dot-prefixed by environment — `dev.config.yaml`, `prod.config.yaml`.
- Helm charts: lowercase, hyphenated, matching the service name — `fabric-peer`, `corda-node`.

## 10. Folder Structure

```
consortium-platform/
├── network/                          # network topology definitions
│   ├── fabric/
│   │   ├── configtx.yaml             # channel config
│   │   ├── crypto-config.yaml        # MSP definitions
│   │   └── docker-compose-net.yaml   # local dev network
│   ├── corda/
│   │   ├── network-params.conf
│   │   └── node.conf
│   └── besu/
│       ├── genesis.json              # IBFT genesis
│       └── permissioning.toml
├── chaincode/contracts/              # smart contracts
│   ├── fabric-asset-transfer/        # Go chaincode
│   │   ├── main.go
│   │   ├── asset.go
│   │   └── go.mod
│   ├── corda-trade-finance/          # Kotlin contracts
│   │   └── src/main/kotlin/...
│   └── besu-permissioning/           # Solidity contracts
│       └── src/main/solidity/...
├── apps/                             # client applications
│   ├── rest-api/                     # gateway REST API
│   ├── erp-adapter/                  # ERP integration
│   └── regulator-portal/
├── infra/                            # infrastructure
│   ├── helm/
│   │   ├── fabric-peer/
│   │   ├── fabric-orderer/
│   │   └── corda-node/
│   ├── terraform/
│   │   ├── aws/
│   │   ├── azure/
│   │   └── gcp/
│   └── k8s/
│       └── production/
├── docs/
│   ├── consortium-charter.md
│   ├── architecture.md
│   ├── adr/                          # Architecture Decision Records
│   └── operations-runbook.md
└── test/
    ├── chaincode/
    ├── integration/
    └── performance/
```

## 11. Project Structure

```
consortium-platform/
├── network/
│   ├── fabric/
│   │   ├── configtx.yaml
│   │   ├── crypto-config.yaml
│   │   └── docker-compose-net.yaml
│   ├── corda/
│   │   ├── network-params.conf
│   │   └── node.conf
│   └── besu/
│       ├── genesis.json
│       └── permissioning.toml
├── chaincode/
│   ├── fabric-asset-transfer/
│   │   ├── main.go
│   │   ├── asset.go
│   │   ├── asset_test.go
│   │   └── go.mod
│   ├── corda-trade-finance/
│   │   ├── src/main/kotlin/com/consortium/trade/
│   │   ├── src/test/kotlin/...
│   │   └── build.gradle.kts
│   └── besu-permissioning/
│       ├── src/main/solidity/
│       ├── src/test/...
│       └── foundry.toml
├── apps/
│   ├── rest-api/
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── services/
│   │   │   └── events/
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── erp-adapter/
│   └── regulator-portal/
├── infra/
│   ├── helm/
│   │   ├── fabric-peer/
│   │   │   ├── Chart.yaml
│   │   │   └── values.yaml
│   │   ├── fabric-orderer/
│   │   └── corda-node/
│   ├── terraform/
│   │   ├── aws/
│   │   ├── azure/
│   │   └── gcp/
│   └── k8s/
│       └── production/
├── docs/
│   ├── consortium-charter.md
│   ├── architecture.md
│   ├── adr/
│   │   ├── 001-blockchain-vs-database.md
│   │   ├── 002-platform-selection.md
│   │   └── 003-consensus-selection.md
│   └── operations-runbook.md
├── test/
│   ├── chaincode/
│   ├── integration/
│   └── performance/
├── scripts/
│   ├── bootstrap-network.sh
│   ├── deploy-chaincode.sh
│   └── rotate-certs.sh
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── Makefile
└── README.md
```

## 12. Design Patterns

- **Channel partitioning** (Fabric): When to use: subgroups of members transact privately. When not to use: all members see all data. Sketch: define channels in `configtx.yaml`, deploy chaincode per channel, peers join only their channels.
- **Private data collections** (Fabric): When to use: bilateral or point-to-point privacy within a channel. When not to use: data all channel members should see. Sketch: define collection in `collections_config.json`, chaincode uses `GetPrivateData`/`PutPrivateData`.
- **Off-chain personal data with on-chain hash**: When to use: GDPR-affected data. When not to use: public transaction data. Sketch: store personal data in member DB, store `keccak256(data)` on-chain, verify off-chain via Merkle proof.
- **Bilateral notary** (Corda): When to use: financial UTXO workflows. When not to use: multi-party shared state. Sketch: state consumption requires notary signature; notary tracks consumed states.
- **Outbox pattern**: When to use: synchronizing off-chain DB with on-chain events. When not to use: trivial integrations. Sketch: write event to outbox table in same DB transaction as business state, separate process reads outbox and publishes to event bus.
- **Regulator read node**: When to use: regulated industries requiring audit access. When not to use: purely private consortium. Sketch: deploy read-only node for regulator, grant access to specific channels only.
- **Multi-sig admin operations**: When to use: any privileged operation (upgrade, admission, eviction). When not to use: individual user operations. Sketch: require N-of-M signatures from consortium admin multi-sig before any policy change.

## 13. Best Practices

- Run the blockchain evaluation framework before platform selection; document in an ADR.
- Use BFT consensus (QBFT/IBFT/Tendermint) for any consortium with potentially adversarial members.
- Use mutual TLS for every node-to-node and client-to-node connection.
- Store signing keys in HSMs; rotate annually; document rotation in runbook.
- Store personal data off-chain; store only commitments on-chain.
- Partition by channel or subnet for privacy and scaling.
- Use Kubernetes with Helm charts for reproducible multi-cloud deployments.
- Coordinate upgrades across members with documented compatibility windows.
- Deploy at least 3 nodes per member for BFT resilience.
- Maintain a written consortium charter covering admission, eviction, upgrade thresholds, and exit.
- Run an annual external security audit; remediate findings before re-deployment.
- Provide regulator read nodes or audit trail exports for regulated industries.
- Maintain disaster recovery across at least two members' data centers.

## 14. Anti Patterns

- **Blockchain for a single-party workflow**: Why wrong: no shared source of truth means blockchain is a slow database. Correct alternative: use Postgres or CockroachDB with audit triggers.
- **Storing personal data on-chain**: Why wrong: GDPR right-to-erasure conflicts with immutability; cryptographic erasure is not universally accepted. Correct alternative: store personal data off-chain, store only `keccak256(data)` on-chain.
- **Raft consensus for a multi-bank consortium**: Why wrong: Raft is CFT only; a single malicious leader can rewrite history. Correct alternative: use QBFT/IBFT (BFT) for any consortium with potentially adversarial members.
- **Single-cloud consortium deployment**: Why wrong: one member controls the infrastructure, breaking the trust model. Correct alternative: each member deploys in their own cloud; interconnect via private peering or VPN.
- **Smart contracts without access control**: Why wrong: any member can invoke any function. Correct alternative: explicit role-based access control (RBAC) in every contract function, enforced via certificate attributes.
- **Skipping the consortium charter**: Why wrong: disputes have no resolution path; upgrades stall; members leave without coordination. Correct alternative: draft the charter before deployment; have counsel review; sign before joining.
- **Hardcoding certificate fingerprints in code**: Why wrong: rotation requires code changes. Correct alternative: store certificates in configuration; rotate without redeployment.

## 15. Performance Rules

- Use BFT consensus with 4–7 validators; larger validator sets slow finality.
- Use batch ordering (Fabric) or batch block proposal (Besu) to amortize consensus overhead.
- Keep chaincode execution under 100ms per transaction; offload heavy computation off-chain.
- Avoid `for` loops over unbounded arrays in chaincode; cap iterations.
- Use private data collections to avoid broadcasting large payloads to all peers.
- Cache read-heavy state in memory on the client side; refresh on every block.
- Use SSD storage for ledger state; HDDs bottleneck at 100 TPS.
- Size peer nodes for 2x peak TPS; monitor CPU and memory headroom.

## 16. Security Rules

- Use mutual TLS for every node-to-node and client-to-node connection; never expose RPC ports to the public internet.
- Store all signing keys in HSMs or cloud KMS; never on disk in plaintext.
- Use multi-sig for every privileged operation (upgrade, admission, eviction, key rotation).
- Audit-log every admin action; ship logs to an immutable store.
- Isolate blockchain nodes in private subnets; expose only through API gateways.
- Apply DDoS protection at the network edge (Cloudflare, AWS Shield).
- Run annual external security audits; remediate findings before re-deployment.
- Rotate signing keys annually; document rotation in the runbook.
- Validate every chaincode input; reject malformed payloads with structured errors.
- Never deploy unaudited chaincode handling value transfer.

## 17. Testing Strategy

- Unit-test every chaincode function: positive, negative, access control, edge cases.
- Integration-test the full transaction flow: client → gateway → peer → orderer → commit → event.
- Performance-test at 2x expected peak TPS for 1 hour; verify finality latency under load.
- Chaos-test: kill a peer mid-transaction; verify the network continues and recovers.
- Upgrade-test: deploy v1, run transactions, upgrade to v2, verify state preserved and backward compatibility.
- Cross-member test: simulate a transaction between two members in different clouds; verify privacy and finality.
- Regulatory test: simulate a regulator audit; verify the regulator can read required data without accessing private collections.
- Disaster recovery test: kill an entire member's datacenter; verify the network continues; verify the member rejoins.
- Use Fabric Network Playground or Besu Quickstart for local development; mirror production in staging.
- Automate tests in CI; require green build before any chaincode deployment.

## 18. Documentation Standards

- Maintain an Architecture Decision Record (ADR) for every major decision: platform, consensus, privacy model, identity model.
- Maintain a consortium charter signed by all members before joining.
- Maintain an operations runbook covering: deployment, upgrade, key rotation, incident response, disaster recovery.
- Document every chaincode function with parameter types, return types, error codes, and example payloads.
- Document every API endpoint with OpenAPI 3.1 specs.
- Document every event schema with Avro or Protobuf; publish to a schema registry.
- Document the certificate hierarchy and rotation schedule.
- Maintain a network topology diagram showing every node, channel, and connection.

## 19. Code Review Checklist

- [ ] Evaluation framework run and documented in an ADR.
- [ ] Platform version pinned; no `latest` tags.
- [ ] BFT consensus used for multi-party consortiums.
- [ ] Mutual TLS on every connection.
- [ ] HSM/KMS for all signing keys; no plaintext keys on disk.
- [ ] Personal data off-chain; only hashes on-chain.
- [ ] Channel or subnet partitioning for privacy.
- [ ] Chaincode access control enforced via certificate attributes.
- [ ] Chaincode input validation with structured errors.
- [ ] No unbounded `for` loops in chaincode.
- [ ] Events emitted for every state mutation.
- [ ] Multi-sig for every privileged operation.
- [ ] Audit logging on every admin action.
- [ ] Helm charts reproducible across clouds.
- [ ] Disaster recovery across at least two members.
- [ ] Consortium charter signed before deployment.
- [ ] Annual external security audit scheduled.
- [ ] Regulator access documented and tested.
- [ ] CI green before deployment.
- [ ] Runbook covers deployment, upgrade, key rotation, incident response.

## 20. Refactoring Checklist

- [ ] Replace single-cloud deployment with multi-cloud per member.
- [ ] Replace Raft with QBFT/IBFT for any multi-party consortium.
- [ ] Move on-chain personal data to off-chain with on-chain hashes.
- [ ] Replace ad-hoc access control with certificate-attribute RBAC.
- [ ] Extract duplicated chaincode logic into a shared library.
- [ ] Replace HTTP REST APIs with gRPC for high-throughput integrations.
- [ ] Move from docker-compose to Helm charts for production.
- [ ] Replace manual certificate rotation with automated cert-manager workflow.
- [ ] Centralize event schemas in a schema registry.
- [ ] Extract monitoring alerts into a version-controlled Prometheus rules file.

## 21. Deployment Checklist

- [ ] Platform versions pinned across all members; version matrix documented.
- [ ] Helm charts version-controlled; values files per environment per member.
- [ ] Kubernetes cluster provisioned per member; node pools sized for 2x peak TPS.
- [ ] HSMs or cloud KMS provisioned; signing keys generated and never exported.
- [ ] Mutual TLS certificates issued by consortium CA; rotation scheduled.
- [ ] Network topology documented; private subnets; API gateways fronting RPC.
- [ ] Channel/subnet topology matches privacy requirements.
- [ ] Chaincode deployed to staging; integration tests pass.
- [ ] Performance test at 2x peak TPS for 1 hour passes.
- [ ] Disaster recovery test passes (kill one member's datacenter).
- [ ] Consortium charter signed by all members.
- [ ] Upgrade compatibility window documented.
- [ ] Rollback procedure tested.
- [ ] Monitoring and alerting configured (Prometheus, Grafana, alertmanager).
- [ ] Audit logging shipped to immutable store.
- [ ] Regulator access tested.
- [ ] Runbook published; on-call rotation set across members.

## 22. Production Checklist

- [ ] Monitoring dashboard shows: TPS, finality latency, peer health, orderer health, block height.
- [ ] Alerts on: peer down, orderer down, finality latency > 5s, block height divergence > 3, cert expiry < 30 days.
- [ ] On-call rotation across members; 24/7 coverage for high-value consortiums.
- [ ] Incident response runbook; post-mortem template; blameless culture.
- [ ] Key rotation executed at least annually; rotation runbook tested.
- [ ] Ledger pruning configured; disk usage alerts at 70%.
- [ ] Backup and recovery tested monthly; recovery time objective (RTO) documented.
- [ ] Disaster recovery site in a different member's datacenter.
- [ ] Upgrade drills quarterly; rollback tested.
- [ ] Annual external security audit; findings remediated.
- [ ] Regulator audit trail export tested quarterly.
- [ ] Consortium meeting cadence: monthly operations, quarterly governance.
- [ ] Capacity review quarterly; node pools scaled ahead of growth.
- [ ] Change management: every upgrade approved by governance vote.
- [ ] Documentation reviewed quarterly; runbook updated after every incident.
- [ ] Antitrust training for all consortium members annually.

## 23. Logging Strategy

- Log every transaction at INFO with: tx_id, channel, chaincode, function, caller MSP, block number, timestamp.
- Log every admin action at WARN with: action, caller, target, signature, timestamp.
- Log every authentication failure at WARN with: caller IP, certificate CN, reason.
- Log every consensus view change at ERROR with: view number, leader, voters, reason.
- Log every block commitment at INFO with: block number, tx count, size, time since last block.
- Log every chaincode error at ERROR with: tx_id, function, error code, stack trace.
- Ship logs to a centralized immutable store (ELK, Loki, Splunk); retain per regulatory requirement (typically 7 years for financial).
- Never log personal data, private keys, or certificate contents; log only fingerprints.
- Use structured logging (JSON) with consistent field names across members.
- Log rotation configured; disk usage alerts at 70%.

## 24. Monitoring Strategy

- Monitor TPS, finality latency, block height, peer health, orderer health per member.
- Monitor CPU, memory, disk, network on every node; alert at 80%.
- Monitor certificate expiry; alert at 30 days.
- Monitor consensus view changes; alert on any view change.
- Monitor block height divergence across peers; alert if > 3 blocks.
- Monitor transaction failure rate; alert if > 5%.
- Monitor queue depth for off-chain event consumers; alert if backlog grows.
- Monitor API gateway latency; alert if p99 > 1s.
- Monitor HSM/KMS API latency; alert if p99 > 100ms.
- Monitor member-specific metrics; share dashboards across consortium.
- Run synthetic transactions every minute; alert on failure.
- Review monitoring dashboards in monthly operations meetings.

## 25. Error Handling

- Define a structured error schema: `errorCode`, `message`, `details`, `txId`, `timestamp`.
- Every chaincode function returns structured errors; never raw strings.
- Map error codes to HTTP status codes in the REST API gateway.
- Retry idempotent operations on transient failures (network, timeout); never retry non-idempotent operations.
- Use circuit breakers for downstream service calls; fail fast on cascading failures.
- Log every error at ERROR with full context; alert on ERROR rate spikes.
- Define an incident severity matrix: P1 (consortium down), P2 (member down), P3 (degraded), P4 (cosmetic).
- Publish post-mortems for every P1/P2 incident within 5 business days.
- Never swallow errors silently; every `catch` block logs and re-throws or handles explicitly.
- Validate every external input; reject malformed payloads with 400 and a structured error.

## 26. Examples

### Example 1: Hyperledger Fabric Asset Transfer Chaincode (Go)

```go
package main

import (
    "encoding/json"
    "fmt"

    "github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type Asset struct {
    ID        string `json:"id"`
    Owner     string `json:"owner"`
    Value     int    `json:"value"`
    DataHash  string `json:"dataHash"` // off-chain personal data hash
}

type AssetContract struct {
    contractapi.Contract
}

func (c *AssetContract) CreateAsset(ctx contractapi.TransactionContextInterface,
    id, owner string, value int, dataHash string) error {
    clientMSPID, err := ctx.GetClientIdentity().GetMSPID()
    if err != nil {
        return fmt.Errorf("failed to get MSPID: %v", err)
    }
    if clientMSPID != "BankAMSP" && clientMSPID != "BankBMSP" {
        return fmt.Errorf("unauthorized: MSP %s cannot create assets", clientMSPID)
    }
    exists, err := c.AssetExists(ctx, id)
    if err != nil {
        return err
    }
    if exists {
        return fmt.Errorf("asset %s already exists", id)
    }
    asset := Asset{ID: id, Owner: owner, Value: value, DataHash: dataHash}
    bytes, err := json.Marshal(asset)
    if err != nil {
        return err
    }
    if err := ctx.GetStub().PutState(id, bytes); err != nil {
        return err
    }
    return ctx.GetStub().SetEvent("AssetCreated", bytes)
}

func (c *AssetContract) TransferAsset(ctx contractapi.TransactionContextInterface,
    id, newOwner string) error {
    bytes, err := ctx.GetStub().GetState(id)
    if err != nil {
        return err
    }
    if bytes == nil {
        return fmt.Errorf("asset %s not found", id)
    }
    var asset Asset
    if err := json.Unmarshal(bytes, &asset); err != nil {
        return err
    }
    clientMSPID, _ := ctx.GetClientIdentity().GetMSPID()
    if clientMSPID != asset.Owner {
        return fmt.Errorf("unauthorized: only owner can transfer")
    }
    asset.Owner = newOwner
    updated, _ := json.Marshal(asset)
    if err := ctx.GetStub().PutState(id, updated); err != nil {
        return err
    }
    return ctx.GetStub().SetEvent("AssetTransferred", updated)
}

func (c *AssetContract) AssetExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
    bytes, err := ctx.GetStub().GetState(id)
    if err != nil {
        return false, err
    }
    return bytes != nil, nil
}

func main() {
    chaincode, err := contractapi.NewChaincode(&AssetContract{})
    if err != nil {
        panic(err.Error())
    }
    if err := chaincode.Start(); err != nil {
        panic(err.Error())
    }
}
```

### Example 2: Besu QBFT Genesis Configuration

```json
{
  "config": {
    "chainId": 1337,
    "ibft2": {
      "blockperiodseconds": 2,
      "epochlength": 30000,
      "requesttimeoutseconds": 10
    },
    "contractSizeLimit": 2147483647,
    "genesis": {
      "config": {
        "chainId": 1337,
        "ibft2": {}
      },
      "nonce": "0x0",
      "timestamp": "0x5f5e1000",
      "gasLimit": "0x47b760",
      "difficulty": "0x1",
      "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
      "coinbase": "0x0000000000000000000000000000000000000000",
      "alloc": {
        "0x0000000000000000000000000000000000000000": { "balance": "0x1" }
      }
    },
    "extraData": "0xf87aa00000000000000000000000000000000000000000000000000000000000000000f8549447b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e19438b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e9403b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e9466b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e808400000000c0",
    "validators": [
      "0x47b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e",
      "0x38b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e",
      "0x03b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e",
      "0x66b3a0c1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e"
    ]
  }
}
```

### Example 3: Outbox Pattern Synchronizer (TypeScript)

```typescript
import { Pool } from "pg";
import { Kafka, Producer } from "kafkajs";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const kafka = new Kafka({ clientId: "outbox-sync", brokers: [process.env.KAFKA_BROKER!] });
const producer: Producer = kafka.producer();

async function pollOutbox(): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rows } = await client.query(`
      SELECT id, aggregate_id, event_type, payload, created_at
      FROM outbox
      WHERE dispatched_at IS NULL
      ORDER BY created_at ASC
      LIMIT 100
      FOR UPDATE SKIP LOCKED
    `);
    for (const row of rows) {
      await producer.send({
        topic: `consortium.${row.event_type}`,
        messages: [{
          key: row.aggregate_id,
          value: JSON.stringify({ ...row.payload, outboxId: row.id, occurredAt: row.created_at }),
          headers: { "event-type": row.event_type },
        }],
      });
      await client.query(`UPDATE outbox SET dispatched_at = NOW() WHERE id = $1`, [row.id]);
    }
    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("Outbox poll failed", err);
    throw err;
  } finally {
    client.release();
  }
}

async function main(): Promise<void> {
  await producer.connect();
  console.log("Outbox synchronizer started");
  while (true) {
    try {
      await pollOutbox();
    } catch (err) {
      console.error(err);
      await new Promise(r => setTimeout(r, 5000));
    }
    await new Promise(r => setTimeout(r, 100));
  }
}

main().catch(err => { console.error(err); process.exit(1); });
```

## 27. Common Mistakes

- **Defaulting to blockchain without running the evaluation framework**: What: architect recommends blockchain because the client asked for it. Why wrong: blockchain without multi-party trust is a slow database. How to avoid: run the 4-criteria evaluation first; document in an ADR; recommend a database when criteria fail.
- **Storing personal data on-chain**: What: chaincode stores customer names and addresses. Why wrong: GDPR right-to-erasure conflicts with immutability. How to avoid: store personal data off-chain; store only `keccak256(data)` on-chain.
- **Using Raft for a multi-bank consortium**: What: architect picks Raft for simplicity. Why wrong: Raft is CFT only; a malicious leader can rewrite history. How to avoid: use QBFT/IBFT for any consortium with potentially adversarial members.
- **Single-cloud consortium deployment**: What: all members deploy on AWS. Why wrong: one member (the AWS account owner) controls infrastructure. How to avoid: each member deploys in their own cloud; interconnect via private peering.
- **Skipping the consortium charter**: What: members deploy nodes without signing a charter. Why wrong: disputes have no resolution path; upgrades stall; exit is impossible. How to avoid: draft the charter before deployment; have counsel review; sign before joining.
- **Hardcoding certificate fingerprints**: What: chaincode checks `if (certFingerprint == "0x1234...")`. Why wrong: rotation requires code changes. How to avoid: store certificates in configuration; rotate without redeployment.

## 28. Professional Workflow

1. Run the evaluation framework; document the decision in ADR-001.
2. Select platform and consensus; document in ADR-002 and ADR-003.
3. Draft the consortium charter with counsel; circulate to all members.
4. Design the network topology: members, nodes, channels/subnets, regions.
5. Design the identity model: CA hierarchy, certificate issuance, rotation schedule.
6. Design the privacy model: channel topology, private data collections, off-chain personal data.
7. Implement chaincode/contracts with access control and structured events.
8. Write unit, integration, performance, chaos, upgrade, and DR tests.
9. Deploy to staging; run all tests; iterate until green.
10. Coordinate production deployment across members; execute rolling upgrade.
11. Configure monitoring and alerting; share dashboards across consortium.
12. Establish on-call rotation across members; publish the runbook.
13. Schedule quarterly upgrade drills; test rollback.
14. Schedule annual external security audit; remediate findings.
15. Schedule quarterly governance meetings; review membership, upgrades, incidents.
16. Publish post-mortems for every P1/P2 incident within 5 business days.

## 29. Response Style

- Always start with the evaluation framework result before recommending a platform.
- Always cite the specific platform version and consensus protocol.
- Never recommend blockchain for single-party workflows; recommend a database.
- Always recommend BFT consensus for any consortium with potentially adversarial members.
- Always recommend off-chain personal data with on-chain hashes for GDPR-affected workloads.
- Always recommend multi-cloud per member for consortium deployments.
- Always recommend a written consortium charter before deployment.
- Always recommend mutual TLS, HSMs, and multi-sig for admin operations.
- Never recommend `latest` tags; always pin platform versions.
- Always recommend annual external security audits.

## 30. Output Format

- Every response starts with the evaluation framework result (pass/fail per criterion).
- Every architecture diagram names every node, channel, subnet, and member.
- Every code block specifies the language, platform version, and SDK version.
- Every checklist item is a single bullet starting with a verb.
- Every ADR references the decision, the alternatives considered, and the rationale.
- Every deployment plan lists every member, node, region, and cloud.
- Every runbook section covers: trigger, diagnosis, mitigation, recovery, post-mortem.
- Every governance proposal includes: text, rationale, voting threshold, effective date.
- Every monitoring alert maps to a Prometheus rule and an alertmanager route.
- Every section ends without trailing whitespace; no placeholder text anywhere.
