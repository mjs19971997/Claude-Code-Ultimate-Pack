# Governance, Identity and Privacy

Reference for the non-code decisions that decide whether a consortium blockchain works: whether to use a ledger at all, consortium governance, identity and PKI, key management, privacy techniques (channels, private data, off-chain storage, zero-knowledge proofs), and data protection obligations such as GDPR. Verified against the Fabric v3.1 and Besu documentation (membership, MSP, private data, Paladin), the EDPB Guidelines 02/2025 on processing personal data through blockchain technologies (published for public consultation in 2025; check the EDPB site for the adopted text) and NIST SP 800-57 key management concepts (2026-10). This is engineering guidance and not legal advice; involve counsel and the data protection officer early.

## 1. Do you need a blockchain? Decision aid

Ask in order; stop at the first "no" that applies:

| Question | If the answer is no |
|---|---|
| Do several organizations that do not fully trust each other write to shared state? | A database owned by one party, with audit logging, is simpler and cheaper |
| Is there no neutral party all would accept as operator, or is operating one too costly, slow or politically hard? | A shared service run by a trusted operator or utility is enough |
| Do the parties need independently verifiable history (tamper evidence) and rule enforcement they cannot unilaterally change? | Use a database with signed audit logs or a transparency log |
| Are the data and rules shared enough that consensus on them is valuable (not just point-to-point messages)? | Use APIs, messaging with signatures, or EDI |
| Can the participants agree on governance, costs and exit? | Resolve governance first; technology will not fix it |

A database (possibly with append-only tables, hash chaining and external timestamping) is the right answer when one party controls the data, when performance and query flexibility dominate, when personal data must be erasable, or when there is no multi-party trust gap. A permissioned ledger is justified by multi-party writes, no neutral operator, shared business logic (smart contracts) and verifiable history.

Public versus permissioned:

| Criterion | Public chain | Permissioned (Fabric, Besu) |
|---|---|---|
| Participants | Anyone | Known, vetted organizations |
| Confidentiality | Everything public unless cryptographically protected | Channels, private data, or restricted membership |
| Throughput and latency | Bounded by network design and fees | Often higher and predictable; depends on consensus and hardware |
| Finality | Probabilistic or economic (varies) | Immediate with BFT/Raft ordering |
| Cost model | Per-transaction fees | Infrastructure shared by members |
| Regulatory fit | Harder for regulated data | Easier to assign responsibility; data protection still applies |
| Trust model | Trust in protocol and open validator set | Trust in consortium rules and member behavior |
| Interoperability | Large existing ecosystem | Needs bridges or anchoring |

Hybrid options: run a permissioned network and anchor state hashes on a public chain for timestamping; or use a public chain with a privacy layer when open participation is the point.

## 2. Consortium governance

Technology decisions must be backed by an operating model, agreed before production:

- Legal structure: a consortium entity or a multi-party agreement covering purpose, membership, liability, IP, data ownership, confidentiality, regulatory responsibilities, dispute resolution and the law that applies.
- Membership lifecycle: admission criteria (KYC/KYB, technical readiness, security baseline), onboarding steps (CA enrollment, node deployment, channel join), periodic recertification, suspension and exit (key and certificate revocation, data return or deletion, continued access to historical records).
- Decision rights: who can approve new members, new channels, chaincode or smart contract upgrades, policy changes, consensus node changes; map these to on-chain policies (Fabric channel config policies, lifecycle endorsement; Besu validator votes or validator contract) so the technical control matches the legal one.
- Operating roles: who runs ordering or validator nodes (spread across organizations so no single member controls the fault-tolerance threshold), who runs CAs, who monitors, who responds to incidents. Document service levels and escalation.
- Cost sharing: infrastructure, support and upgrades; avoid designs where one member bears all cost without influence.
- Change management: versioned contracts with a published upgrade calendar, test networks mirroring production, compatibility windows, and rollback criteria.
- Dispute and error handling: ledger entries are hard to reverse. Define compensating transactions, who can authorize them, and how errors and fraud are resolved off-chain.
- Compliance: data protection, financial regulation, sanctions, record retention, audit access for regulators. Record the data controller and processor roles of each member.
- Exit and wind-down: how the network is decommissioned, how records are preserved and who holds the keys to archives.

## 3. Identity and PKI

- Use X.509 PKI for permissioned networks. Define a CA hierarchy: an offline root CA (HSM-protected), intermediate CAs per organization, and online issuing CAs for enrollment. Keep root keys offline; issue short-lived leaf certificates where the platform allows.
- Separate identities by purpose: node identities (peer, orderer, validator), TLS identities, administrators, application service identities and end-user identities. Do not reuse certificates across purposes.
- Fabric: each organization defines an MSP (root and intermediate certificates, NodeOU configuration, CRLs). Use NodeOUs to distinguish client, peer, admin and orderer roles. Register identities with attributes needed for access control and enroll with a CA (Fabric CA or an enterprise CA). Use mutual TLS between all nodes. Details: [hyperledger-fabric.md](hyperledger-fabric.md).
- Besu: network identity is the node key (enode public key) and account key. Control membership with node and account allowlists, the validator set and network-level mutual TLS, plus contract-level role registries. Details: [besu-and-evm-permissioned.md](besu-and-evm-permissioned.md).
- Link to enterprise identity: authenticate end users with the organization's identity provider (OIDC/SAML); an application backend maps the authenticated user to a ledger identity (per-user certificate held in an HSM or a signing service, or a service identity with the user ID recorded in the transaction). Choose based on accountability needs: per-user keys give non-repudiation but add key custody burden.
- Decentralized identifiers and verifiable credentials (W3C DID Core and VC Data Model) can express eligibility claims (for example "accredited investor", "licensed carrier") without putting personal data on-chain; the ledger stores the issuer's public key or a revocation status entry. Evaluate maturity and tooling before depending on them.
- Revocation: plan certificate revocation (CRLs in the Fabric MSP, removal from allowlists or validator sets in Besu, contract-level role removal), response time targets and what a revoked identity can still do until the update is committed.
- Lifecycle automation: track expiry for every certificate (identity, TLS, CA), renew ahead of time with alerts at 60/30/7 days, and rehearse CA key rollover.

## 4. Key management

- Keys that sign blocks, endorse transactions, issue certificates or move assets belong in HSMs or cloud KMS with non-exportable keys (PKCS#11 for Fabric nodes and Gateway clients; the security module plugin for Besu validators; a signing service for application accounts).
- Separate duties: no single person can export, use and approve use of a high-value key. Use multi-party approval (multisig contracts, quorum-based signing, HSM m-of-n activation) for admin operations such as contract upgrades, validator changes and token minting.
- Define key ceremonies for roots: documented script, witnesses, offline machine, tamper-evident storage of backups, tested recovery.
- Rotation: crypto-period per key class; rotate on schedule and on suspected compromise; ensure old keys can still verify historical signatures.
- Do not keep private keys in source control, container images, CI logs, environment dumps or application databases. Inject at runtime from a secret manager or sign through a remote service; limit network access to the signer.
- Back up wrapped keys and recovery material separately from the HSM; test restoration.
- Monitor key usage: alert on signing volume anomalies, signing outside business hours or from unexpected hosts.
- Post-quantum readiness: record where long-lived signatures and encrypted archives exist, since ledgers keep data for decades; follow standards bodies on algorithm migration and design for algorithm agility (certificate rotation, versioned signature schemes).

## 5. Privacy techniques

Choose the least complex technique that satisfies the confidentiality requirement:

| Technique | What it hides | From whom | Costs and limits |
|---|---|---|---|
| Separate network | Everything | Non-members | Operations per network; weak interoperability |
| Fabric channel | Entire ledger partition, chaincode and transaction data | Non-channel members, including other consortium members | Channel proliferation; members of a channel see all data on it |
| Fabric private data collection | Values (hashes remain on the channel ledger) | Channel members outside the collection | Hash and metadata are visible; gossip dissemination; purge rules |
| Off-chain storage with on-chain hash and pointer | Document or record content | Everyone without access to the store | Availability and integrity depend on the store; access control outside the ledger |
| Encryption (envelope or per-recipient) | Content | Anyone without the key | Key distribution and revocation; ciphertext is permanent on-chain; avoid for personal data |
| Paladin domains (Besu) | State (Pente), balances and amounts (Noto, Zeto) | Non-participants (and, for Zeto, even the notary) | New component to operate; see the Besu reference |
| Zero-knowledge proofs | The witness (private inputs) while proving a statement | Verifiers | Circuit development, proving cost, trusted setup in some schemes, specialist audit |
| Trusted execution environments | Computation inputs | Operators | Hardware trust and side-channel risk; attestation needed |

Guidance:

- Metadata leaks: who transacts with whom, when, how often, and sizes are visible even when contents are hidden. Consider batching, padding and pseudonymous identifiers where this matters.
- Low-entropy data (names, small numbers, dates) hashed without a secret salt can be recovered by guessing. Use random salts or keyed hashes (HMAC) held by the data owner.
- Zero-knowledge proofs suit statements such as "balance is sufficient and amounts are conserved", "holder is over 18", or "I am a member of the allowed set" without revealing the underlying data. Prefer audited libraries and circuits, use established proving systems (for example Groth16 as used in Zeto, or others), and treat circuit changes as security changes.
- Selective disclosure for auditors: design an auditor role from the start (notary or auditor key, viewing keys, disclosure by the data owner) instead of retrofitting.

## 6. Data protection and residency (GDPR and similar)

- Do not store personal data on-chain. Ledger data is replicated to many parties, is designed to be immutable and cannot be reliably erased. Hashes of personal data can still be personal data when the data is guessable or linkable; encryption does not remove this status, and deleting a key may not be accepted as erasure by every regulator. The EDPB's blockchain guidelines (Guidelines 02/2025, version published for consultation in April 2025) are reported to advise against storing personal data on-chain and to refer to off-chain data instead, with encryption, salted or keyed hashes and commitments as fallbacks that have limits over long retention; confirm the wording and status in the current EDPB text.
- Pattern: store personal data in an off-chain, access-controlled, deletable store (database, object storage) in the appropriate jurisdiction. Put on-chain only a random identifier, a salted hash or commitment of the record, a content pointer, a status, and the non-personal business facts. Verification: recompute the hash of the off-chain record and compare. Erasure: delete the off-chain record and the salt, leaving an unlinkable commitment.
- Prefer commitments with a random salt held off-chain (so the hash cannot be guessed). Do not use deterministic hashes of emails, phone numbers or national IDs.
- Public keys and pseudonymous identifiers linked to a natural person can be personal data. Avoid putting user names in certificate subject fields on a shared ledger; use opaque identifiers in certificates and map them off-chain.
- Data residency: node placement determines where ledger data is stored. If the ledger may contain regulated data, place nodes of the relevant members in the required jurisdiction, restrict channel or collection membership, and check cross-border transfer rules. For ordering services, remember they see transaction content on channels unless payloads are encrypted or private data is used.
- Controllers and processors: decide who is the controller for off-chain records, whether the consortium is a joint controller of on-chain data, and document it in the consortium agreement. Run a data protection impact assessment before launch.
- Data subject rights: access, rectification, erasure and restriction must be served from the off-chain store; design so that correction creates a new version and invalidates old commitments.
- Retention: define how long off-chain records and ledger archives are kept, and what happens when a member leaves.
- Logs and events: chaincode events, application logs and monitoring traces can leak personal data; apply the same rules.

## 7. Security baseline for consortium networks

- Network: private connectivity (VPN, private links), no public exposure of peers, orderers, validators or databases; restrict ingress to known member ranges; mutual TLS everywhere.
- Hosts and containers: hardened images, non-root users, read-only filesystems where possible, patch cadence for node software and dependencies, secrets from a vault.
- Smart contract security: independent audit, static analysis, tests with property and fuzz techniques, staged rollout, bug disclosure process (see smart-contract-security-expert for EVM, and the Fabric chaincode rules in the Fabric reference).
- Monitoring and incident response: shared dashboards for network health, agreed alert thresholds, a joint incident runbook (who can pause a contract, rotate keys, remove a member).
- Backups and disaster recovery: ledger snapshots, CA databases, configuration blocks, channel and genesis artifacts, tested restores; recovery objectives agreed across the consortium.
- Independent assurance: periodic penetration tests of the network and applications, and audits of governance controls.
