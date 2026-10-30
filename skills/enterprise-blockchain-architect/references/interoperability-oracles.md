# Interoperability, Oracles and Off-chain Integration

Reference for connecting a permissioned ledger to the outside world: off-chain data stores and event-driven integration, oracles, cross-ledger interoperability and tokenization patterns on Fabric. Verified against Fabric v3.1.5, fabric-gateway v1.13.0 (`checkpointers`, chaincode events; TypeScript compiled), fabric-contract-api-go v2.2.4 and Go 1.26 (the oracle chaincode compiled), fabric-samples (`off_chain_data`, `token-sdk`, `token-erc-20`, `token-utxo`), Hyperledger Cacti project updates (SATP implementation tracking the IETF draft, 0.0.3-beta in Q4 2025) and ERC-3643 (2026-10).

## 1. Integration principles

- The ledger is the system of record for shared facts and rules, not an application database. Query, reporting and search workloads run on off-chain replicas built from ledger events.
- Treat every crossing of the ledger boundary as an integration with failure modes: duplicates, reordering, partial failure and replay. Make consumers idempotent and checkpoint progress.
- Never let chaincode or contracts call external systems; every validating node must reach the same result from the same inputs. Bring external data in as signed inputs (section 3) and push internal events out through the event stream.
- Prefer thin, versioned interfaces: commands in (submit transaction), events out (committed facts), snapshots by query. Keep message schemas (JSON Schema, protobuf) in the repository and version them.
- Align identifiers: use business identifiers across systems and store the transaction ID with every off-chain record for traceability.

## 2. Off-chain replica from ledger events

Pattern: a service listens to committed events, writes them idempotently to a database or search index, and checkpoints its position, so a restart resumes without loss. The Fabric Gateway client supports a checkpointer that persists the block number and transaction position; checkpoint after the sink has stored the event, so delivery is at-least-once and the sink must deduplicate on `(txId, eventName)`.

```ts
import { checkpointers, type Network } from "@hyperledger/fabric-gateway";

export interface LedgerEvent {
  readonly txId: string;
  readonly blockNumber: bigint;
  readonly name: string;
  readonly payload: Uint8Array;
}

export interface EventSink {
  /** Must be idempotent on (txId, name): after a crash the last event can be delivered again. */
  apply(event: LedgerEvent): Promise<void>;
}

export async function runIndexer(
  network: Network,
  chaincode: string,
  checkpointFile: string,
  sink: EventSink,
  signal: AbortSignal,
): Promise<void> {
  const checkpointer = await checkpointers.file(checkpointFile);
  while (!signal.aborted) {
    // startBlock applies only when the checkpointer holds no state yet.
    const events = await network.getChaincodeEvents(chaincode, { checkpoint: checkpointer, startBlock: 0n });
    const stop = (): void => events.close();
    signal.addEventListener("abort", stop, { once: true });
    try {
      for await (const event of events) {
        await sink.apply({
          txId: event.transactionId,
          blockNumber: event.blockNumber,
          name: event.eventName,
          payload: event.payload,
        });
        await checkpointer.checkpointChaincodeEvent(event); // only after the sink has stored the event
      }
    } catch (error) {
      if (signal.aborted) return;
      console.error("Event stream failed, retrying in 2 s", error);
      await new Promise<void>((resolve) => setTimeout(resolve, 2_000));
    } finally {
      signal.removeEventListener("abort", stop);
      events.close();
    }
  }
}
```

Notes:

- The `off_chain_data` sample in fabric-samples shows the full pattern with block events, a checkpointer and a store.
- Chaincode events carry only what the chaincode puts in them; use block events when the replica needs the full read-write set. Do not emit private data in events.
- Build the replica schema for the queries you need (denormalized, indexed) and rebuild it from the stream when the schema changes; keep a reconciliation job that compares counts and hashes with the ledger.
- Lag, dead-letter handling and idempotency belong in the monitoring plan; alert when the replica falls behind the ledger height.
- For Besu, index logs through JSON-RPC (`eth_getLogs`, subscriptions) with a stored block cursor, handle restarts, and treat QBFT blocks as final (no reorg handling is needed, unlike public proof-of-work or proof-of-stake chains).

Outbound commands to the ledger should go through a queue or an outbox in the application database so that business transactions and ledger submissions stay consistent: write the intent in the same database transaction as the business change, then a worker submits to the ledger with an idempotency key and records the outcome. Retry on transient failures; on MVCC conflicts retry with backoff; on endorsement errors surface the chaincode message.

## 3. Oracles

An oracle supplies external data (prices, FX rates, shipment events, sensor readings, KYC status) to the ledger. Ledger validators cannot fetch it themselves, and a single feed is a single point of failure and a manipulation target.

Design choices:

| Choice | Options |
|---|---|
| Who reports | A designated oracle organization or operator (simple, trusted); several independent reporters with aggregation (median or threshold of signatures); a decentralized oracle network for EVM chains |
| What is signed | The full report (feed, value, observation time, sequence number), with a signature scheme and key registered on-chain |
| Freshness | Report timestamp compared with the transaction timestamp, with a maximum age; heartbeat expectations per feed |
| Replay protection | Strictly increasing sequence number or nonce per feed |
| Failure handling | Stale-data behavior defined per use case: pause, fall back to last value with a flag, or reject |
| Governance | Who can add, rotate or remove oracle keys, thresholds and feed parameters (policy, multisig, or consortium vote) |

Chaincode pattern for Fabric: the client application obtains the signed report from the oracle service and passes it to the chaincode as an argument; the chaincode verifies the signature against a registered public key, checks age and sequence using the deterministic transaction timestamp, and stores the value. Every endorsing peer gets the same input, so endorsements match.

```go
package main

import (
	"crypto/ecdsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

const (
	oracleKeyPrefix = "oracle~key~"
	feedPrefix      = "oracle~feed~"
	maxReportAge    = 5 * time.Minute
)

// Report is the payload the oracle operator signs. The signature covers the exact JSON bytes
// passed to SubmitReport, so the signer and the verifier never disagree about serialization.
type Report struct {
	Feed       string `json:"feed"`
	Value      string `json:"value"`      // decimal string; never a float
	ObservedAt int64  `json:"observedAt"` // Unix seconds, set by the oracle
	Sequence   uint64 `json:"sequence"`   // strictly increasing per feed
}

type OracleContract struct {
	contractapi.Contract
}

// RegisterOracleKey stores the PEM-encoded ECDSA public key allowed to sign a feed.
// Restrict who may call this with the channel's governance policy or a key-level endorsement policy.
func (c *OracleContract) RegisterOracleKey(ctx contractapi.TransactionContextInterface, feed, publicKeyPEM string) error {
	if err := ctx.GetClientIdentity().AssertAttributeValue("role", "oracle-admin"); err != nil {
		return fmt.Errorf("caller is not an oracle admin: %w", err)
	}
	if _, err := parsePublicKey(publicKeyPEM); err != nil {
		return err
	}
	return ctx.GetStub().PutState(oracleKeyPrefix+feed, []byte(publicKeyPEM))
}

// SubmitReport verifies a signed report and stores the latest value. The data is passed in as an
// argument: chaincode must never fetch it from the network, because each endorser would see
// different values and the endorsements would not match.
func (c *OracleContract) SubmitReport(ctx contractapi.TransactionContextInterface, reportJSON, signatureB64 string) error {
	var r Report
	if err := json.Unmarshal([]byte(reportJSON), &r); err != nil {
		return fmt.Errorf("invalid report: %w", err)
	}
	pemBytes, err := ctx.GetStub().GetState(oracleKeyPrefix + r.Feed)
	if err != nil {
		return err
	}
	if pemBytes == nil {
		return fmt.Errorf("no oracle key registered for feed %q", r.Feed)
	}
	pub, err := parsePublicKey(string(pemBytes))
	if err != nil {
		return err
	}
	sig, err := base64.StdEncoding.DecodeString(signatureB64)
	if err != nil {
		return errors.New("signature is not valid base64")
	}
	digest := sha256.Sum256([]byte(reportJSON))
	if !ecdsa.VerifyASN1(pub, digest[:], sig) {
		return errors.New("signature verification failed")
	}
	txTime, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return err
	}
	age := txTime.AsTime().Sub(time.Unix(r.ObservedAt, 0))
	if age < -time.Minute || age > maxReportAge {
		return errors.New("report is stale or from the future")
	}
	prevRaw, err := ctx.GetStub().GetState(feedPrefix + r.Feed)
	if err != nil {
		return err
	}
	if prevRaw != nil {
		var prev Report
		if err := json.Unmarshal(prevRaw, &prev); err != nil {
			return err
		}
		if r.Sequence <= prev.Sequence {
			return errors.New("sequence must increase (replay protection)")
		}
	}
	stored, err := json.Marshal(r)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(feedPrefix+r.Feed, stored)
}

func parsePublicKey(pemText string) (*ecdsa.PublicKey, error) {
	block, _ := pem.Decode([]byte(pemText))
	if block == nil {
		return nil, errors.New("public key is not valid PEM")
	}
	parsed, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	pub, ok := parsed.(*ecdsa.PublicKey)
	if !ok {
		return nil, errors.New("public key must be ECDSA")
	}
	return pub, nil
}
```

Practices:

- Use multiple independent sources where the value moves money; aggregate on-chain with a median and outlier rules, or require signatures from a quorum of oracle operators.
- Put the oracle key in an HSM, rotate it, and register keys through a governed transaction (the sample restricts it by identity attribute; use a stronger policy such as a multi-organization endorsement for production).
- Record the source and observation time with the value so downstream consumers and auditors can see how stale it is.
- For EVM networks, either run your own signed-report contract as above, or use an established oracle network and its client contracts; check each provider's documentation for current interfaces and supported chains, and treat the oracle contract address as a governed configuration item.
- For events originating in the physical world (IoT, logistics), the weak point is the data source, not the ledger: attest at the device or at a trusted gateway, and design cross-checks (multiple sensors, third-party confirmation).
- Resist manipulation with circuit breakers: reject values that move beyond a configured bound without a second confirmation, and allow governance to pause a feed.

## 4. Interoperability between ledgers

Choose the simplest mechanism that gives the required guarantee.

| Need | Mechanism |
|---|---|
| Prove on ledger B that something happened on ledger A | Anchoring: publish a hash or Merkle root of A's state or blocks on B (or on a public chain) and verify inclusion proofs; no value moves |
| Atomic exchange of assets between two ledgers | Hash time-locked contracts (HTLC): both legs lock under the same hash and expire if the secret is not revealed in time |
| Transfer an asset from ledger A to ledger B | Lock-and-mint or burn-and-mint with a relay, notary or light-client verification; the bridge is the main security risk |
| Cross-network asset transfer standard | Secure Asset Transfer Protocol (SATP), an IETF specification still in progress; Hyperledger Cacti is implementing it (beta releases at the time of writing); check project status before depending on it |
| Same business process spanning organizations | Shared channel or network, or event-driven integration with a saga and compensations |
| Interaction with traditional systems | APIs and message queues with signatures; ISO 20022 style messages mapped to ledger commands |

Risks and guidance:

- Bridges are high-value targets: a bridge that holds locked assets or has a small signer set concentrates risk. Prefer designs where verification is cryptographic (inclusion proofs, light clients, HTLC) over trusted multisig relays, and cap value per time window.
- Finality differs by ledger. Do not act on a source event before it is final there; with Raft or BFT ordering and QBFT, finality is immediate once committed, but public chains need confirmations or finality checkpoints.
- Atomicity across ledgers does not exist by default. Define the timeout, rollback and reconciliation process and test partial failure paths.
- Use a common asset identity and metadata model across networks (token standards, registries) so representations do not diverge.
- Governance: both consortia need agreements on bridge operation, incident response and liability.
- Hyperledger Cacti is a graduated project that provides connectors and the SATP gateway; the project reported reduced maintainer capacity in its updates, so evaluate its health, test coverage and your ability to maintain it before adopting.

## 5. Tokenization patterns on Fabric

- Fungible and non-fungible tokens: fabric-samples includes `token-erc-20`, `token-erc-721`, `token-erc-1155` (account-based) and `token-utxo` chaincode samples. Use them as starting points; add issuer/minter roles, transfer restrictions, pausing and an audit trail required by your regulator.
- Confidential tokens: the Token SDK (a Hyperledger Labs project used in the `token-sdk` sample) provides UTXO-style tokens with hidden amounts and owners, and an auditor role that approves transactions; the sample is meant for proofs of concept, so assess its maturity and support before production use.
- Account vs UTXO: account-based tokens are simpler and fit KYC-bound registries; UTXO-style tokens parallelize better (fewer MVCC conflicts on hot balances) and suit privacy designs.
- Avoid hot keys: a single total-supply counter or a central account updated by every transaction causes MVCC read conflicts. Shard counters, derive totals off-chain, or use a UTXO model.
- Regulated assets on EVM-based networks: see ERC-3643 in [besu-and-evm-permissioned.md](besu-and-evm-permissioned.md).
- Cash leg: decide whether settlement uses a tokenized deposit, a stablecoin, a wholesale CBDC, or an off-ledger payment with an on-ledger confirmation; DvP requires the cash leg to be on a ledger that can be atomically combined with the asset leg.

## 6. API layer

- Expose business APIs (REST or gRPC) in front of the gateway; do not hand ledger credentials to browsers or mobile apps.
- Authenticate callers with the enterprise identity provider; authorize in the API and again in chaincode (identity attributes, ownership). Never trust a user identifier passed as an argument.
- Return a transaction ID and status for submitted commands; provide a status endpoint that checks the commit status by transaction ID instead of re-submitting.
- Rate-limit and size-limit requests; the endorsement and ordering path is a scarce resource.
- Version the API independently of the chaincode, and use chaincode events and the replica for read APIs.
