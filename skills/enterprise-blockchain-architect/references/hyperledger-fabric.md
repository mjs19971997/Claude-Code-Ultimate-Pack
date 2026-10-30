# Hyperledger Fabric

Reference for designing, building and operating Hyperledger Fabric networks: versions, network and channel design, identity, chaincode in Go with `fabric-contract-api-go`, the chaincode lifecycle, private data, endorsement policies, the Fabric Gateway client API (Go and TypeScript) and operations. This file absorbs the former hyperledger-fabric-expert skill. Verified against Fabric v3.1.5 (latest release) and v2.5.16 (current LTS), fabric-contract-api-go v2.2.4, fabric-chaincode-go v2.3.x, fabric-gateway v1.13.0 (Go module and `@hyperledger/fabric-gateway` npm package, Node 22.12+), fabric-samples `main` and Go 1.26 (the Go chaincode and TypeScript client below were compiled; the Go module requires Go 1.26.7) (2026-10).

## 1. Versions and what to choose

- Fabric v2.5.x is the designated Long-Term Support release for production users and still receives fixes (latest v2.5.16). The project README lists v2.5.x as the current LTS.
- Fabric v3.0 introduced a Byzantine Fault Tolerant ordering service based on SmartBFT and Ed25519 support for MSP functions, both gated by the channel capability `V3_0`. Fabric v3.1.x (latest v3.1.5) added chaincode read and write batching (`StartWriteBatch`, `GetMultipleStates`, `GetMultiplePrivateData`) and `GetAllStatesCompositeKeyWithPagination`. These need peer `core.yaml` settings under `chaincode.runtimeParams` and `fabric-chaincode-go` v2.1.0, v2.2.0 and v2.3.0 respectively.
- Choice: use v3.x when you want BFT ordering (mutually distrusting ordering organizations) or the new performance features; use v2.5.x when LTS-grade stability and a long maintenance horizon matter more. Raft (CFT) ordering remains supported in both. Check the release notes and the upgrade guide before moving a production channel; capability updates are one-way.
- Application SDKs: use the Fabric Gateway client APIs (Go, Node.js/TypeScript, Java). The older `fabric-sdk-node` (`fabric-network`) is deprecated as of Fabric v2.5 per its README; new applications should not use it.
- Chaincode languages: Go (`fabric-contract-api-go` v2 for contracts), Node.js/TypeScript (`fabric-contract-api` and `fabric-shim`), Java. Go is the usual choice for performance and the largest sample base.

## 2. Network and channel design

- Organizations: each organization has its own MSP (membership service provider), CA(s), peers, and optionally orderer nodes. Keep organization and legal entity aligned so governance maps to cryptographic identity.
- Channels partition ledgers: each channel has its own ledger, membership, chaincode definitions and policies. Use a channel per set of parties that must share the same data. Many channels increase operational cost; consider private data collections when only a subset of channel members should see some data.
- Ordering service: Raft (`etcdraft`) is crash fault tolerant; run 3 or 5 nodes (odd) and spread across organizations or failure domains. SmartBFT (`OrdererType: BFT`) tolerates up to f malicious or faulty nodes with at least 3f+1 nodes, so the smallest useful cluster is 4. BFT nodes identify each other by enrollment certificate and need the `V3_0` capability. The consenter list is defined in channel configuration; see `bft_configuration` in the Fabric docs for `SmartBFT` parameters (batching, timeouts, heartbeats).
- Peers: at least two peers per organization per channel for availability. Anchor peers and gossip let peers of different organizations discover each other, and gossip distributes private data to authorized peers.
- State database: LevelDB (key and range queries) or CouchDB (rich JSON queries, index files required). Choose one per peer and keep it consistent across the channel's peers.
- Chaincode-level endorsement policy decides who must sign each transaction (for example `AND('BankA.peer','BankB.peer')` or `OutOf(2, ...)`). The channel-level lifecycle endorsement policy (default: a majority of channel organizations) governs chaincode definitions. Collection-level and key-level policies refine it.
- Governance in channel config: administrators, readers, writers and the policies to change them; define who can add an organization, update orderer consenters and approve chaincode.

## 3. Identity, MSP and keys

- Each organization runs a Fabric CA (or another X.509 CA). Use separate CAs or roles for identity certificates and for TLS certificates.
- MSP structure: root and intermediate CA certificates, admin certificates (or NodeOUs), revocation lists, TLS CAs. Enable NodeOUs so identities are classified as `client`, `peer`, `admin` and `orderer` by OU in the certificate, and policies like `Org1MSP.peer` and `Org1MSP.admin` work as intended.
- Attributes for attribute-based access control: register identities with attributes (for example `role=issuer:ecert`) so they appear in the enrollment certificate, then check them in chaincode with `ClientIdentity.AssertAttributeValue`.
- Private keys of peers, orderers and admin/client identities should live in an HSM (PKCS#11) for production; Fabric nodes and the Gateway clients both support HSM-backed signing. Never keep organization admin keys on application servers.
- Rotate certificates before expiry; monitor expiry of identity and TLS certificates (an expired orderer TLS certificate can stop the cluster). Fabric v3 supports Ed25519 certificates when the `V3_0` capability is enabled.
- Revocation: update the MSP with a CRL or remove the identity from the relevant policy; endorsement checks use the MSP state in the channel configuration.

## 4. Chaincode in Go

Module setup: `go get github.com/hyperledger/fabric-contract-api-go/v2@v2.2.4` and `go mod tidy`; the chaincode-go dependency is resolved by the module. Go version in `go.mod` must be supported by the build environment: when the peer builds chaincode in its own build image, that image's Go version must satisfy `go.mod`; with chaincode as a service (section 7) you control the toolchain.

Determinism rules (every endorsing peer must produce the same read-write set):

- No `time.Now()`; use `stub.GetTxTimestamp()`. No random numbers, no unordered map iteration affecting writes, no floating-point where results may differ, no network, file or environment access, no goroutine-dependent ordering.
- Marshal JSON from structs (stable field order) or sorted maps; mind locale-independent number formatting.
- `GetState` returns the committed value, not a value written earlier in the same transaction (there is no read-your-writes inside a transaction); design functions as read once, then write once per key.
- Only authorize using the caller identity from `GetClientIdentity()`, not from function arguments.
- Keep personal data out of world state and events: store hashes and pointers to an off-chain store (see the data residency guidance in SKILL.md).

Example contract: an asset registry that stores a document hash and pointer, restricts issuance to certificates carrying `role=issuer`, restricts transfers to the owner, sets a key-level endorsement policy for the owner's organization, and paginates listings:

```go
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"regexp"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/v2/pkg/statebased"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

const (
	roleAttr    = "role"
	roleIssuer  = "issuer"
	maxPageSize = 100
)

var (
	assetIDPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,64}$`)
	hashPattern    = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

// Asset is the world-state record. It holds a hash and pointer to an off-chain
// document, never personal data. Struct field order fixes the JSON byte order,
// so every endorsing peer produces an identical write set.
type Asset struct {
	ID          string `json:"id"`
	ContentHash string `json:"contentHash"` // SHA-256 of the off-chain document, lowercase hex
	DocumentURI string `json:"documentUri"` // pointer to the off-chain store
	Owner       string `json:"owner"`       // cid.GetID() of the owning client
	OwnerMSP    string `json:"ownerMsp"`
	UpdatedAt   string `json:"updatedAt"` // from the transaction timestamp, RFC 3339 UTC
}

type PagedAssets struct {
	Assets   []*Asset `json:"assets"`
	Bookmark string   `json:"bookmark"`
}

type AssetContract struct {
	contractapi.Contract
}

// CreateAsset registers an asset. Only clients whose certificate carries role=issuer may call it.
func (c *AssetContract) CreateAsset(ctx contractapi.TransactionContextInterface, id, contentHash, documentURI string) error {
	if err := ctx.GetClientIdentity().AssertAttributeValue(roleAttr, roleIssuer); err != nil {
		return fmt.Errorf("caller is not an issuer: %w", err)
	}
	if !assetIDPattern.MatchString(id) {
		return errors.New("invalid asset id")
	}
	if !hashPattern.MatchString(contentHash) {
		return errors.New("contentHash must be 64 lowercase hex characters")
	}
	if len(documentURI) == 0 || len(documentURI) > 512 {
		return errors.New("invalid documentUri")
	}
	existing, err := ctx.GetStub().GetState(id)
	if err != nil {
		return fmt.Errorf("read state: %w", err)
	}
	if existing != nil {
		return fmt.Errorf("asset %s already exists", id)
	}
	mspID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return err
	}
	clientID, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return err
	}
	asset := &Asset{ID: id, ContentHash: contentHash, DocumentURI: documentURI, Owner: clientID, OwnerMSP: mspID}
	if err := c.save(ctx, asset); err != nil {
		return err
	}
	return requireOrgEndorsement(ctx, id, mspID)
}

// TransferAsset moves ownership. Only the current owner may call it.
func (c *AssetContract) TransferAsset(ctx contractapi.TransactionContextInterface, id, newOwner, newOwnerMSP string) error {
	asset, err := c.get(ctx, id)
	if err != nil {
		return err
	}
	clientID, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return err
	}
	if clientID != asset.Owner {
		return errors.New("only the current owner can transfer the asset")
	}
	if newOwner == "" || newOwnerMSP == "" {
		return errors.New("new owner and MSP are required")
	}
	asset.Owner, asset.OwnerMSP = newOwner, newOwnerMSP
	if err := c.save(ctx, asset); err != nil {
		return err
	}
	if err := requireOrgEndorsement(ctx, id, newOwnerMSP); err != nil {
		return err
	}
	payload, err := json.Marshal(map[string]string{"id": id, "newOwnerMsp": newOwnerMSP})
	if err != nil {
		return err
	}
	return ctx.GetStub().SetEvent("AssetTransferred", payload)
}

// ReadAsset returns one asset.
func (c *AssetContract) ReadAsset(ctx contractapi.TransactionContextInterface, id string) (*Asset, error) {
	return c.get(ctx, id)
}

// ListAssets returns one page of assets. Use the returned bookmark to fetch the next page.
func (c *AssetContract) ListAssets(ctx contractapi.TransactionContextInterface, pageSize int32, bookmark string) (*PagedAssets, error) {
	if pageSize < 1 || pageSize > maxPageSize {
		return nil, fmt.Errorf("pageSize must be between 1 and %d", maxPageSize)
	}
	iter, meta, err := ctx.GetStub().GetStateByRangeWithPagination("", "", pageSize, bookmark)
	if err != nil {
		return nil, err
	}
	defer iter.Close()
	out := &PagedAssets{Assets: []*Asset{}}
	for iter.HasNext() {
		kv, err := iter.Next()
		if err != nil {
			return nil, err
		}
		var a Asset
		if err := json.Unmarshal(kv.Value, &a); err != nil {
			return nil, err
		}
		out.Assets = append(out.Assets, &a)
	}
	out.Bookmark = meta.GetBookmark()
	return out, nil
}

func (c *AssetContract) get(ctx contractapi.TransactionContextInterface, id string) (*Asset, error) {
	raw, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("read state: %w", err)
	}
	if raw == nil {
		return nil, fmt.Errorf("asset %s does not exist", id)
	}
	var a Asset
	if err := json.Unmarshal(raw, &a); err != nil {
		return nil, err
	}
	return &a, nil
}

func (c *AssetContract) save(ctx contractapi.TransactionContextInterface, a *Asset) error {
	ts, err := ctx.GetStub().GetTxTimestamp() // deterministic across peers; never use time.Now()
	if err != nil {
		return err
	}
	a.UpdatedAt = ts.AsTime().UTC().Format(time.RFC3339)
	raw, err := json.Marshal(a)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(a.ID, raw)
}

// requireOrgEndorsement sets a key-level endorsement policy so future changes to this asset
// must be endorsed by the owner's organization (in addition to the chaincode-level policy).
func requireOrgEndorsement(ctx contractapi.TransactionContextInterface, key, mspID string) error {
	ep, err := statebased.NewStateEP(nil)
	if err != nil {
		return err
	}
	if err := ep.AddOrgs(statebased.RoleTypePeer, mspID); err != nil {
		return err
	}
	policy, err := ep.Policy()
	if err != nil {
		return err
	}
	return ctx.GetStub().SetStateValidationParameter(key, policy)
}

func main() {
	cc, err := contractapi.NewChaincode(&AssetContract{})
	if err != nil {
		log.Panicf("create chaincode: %v", err)
	}
	if err := cc.Start(); err != nil {
		log.Panicf("start chaincode: %v", err)
	}
}
```

Notes on the code:

- `AssertAttributeValue("role", "issuer")` works only if the enrollment certificate contains that attribute (registered with the `:ecert` option in Fabric CA); otherwise the call fails.
- `SetStateValidationParameter` stores a key-level endorsement policy; changing the key later requires endorsement by the owner's organization in addition to the chaincode-level policy. When ownership moves, the policy must be updated by the transaction that moves it, as shown.
- `GetStateByRangeWithPagination` returns a bookmark; page sizes are capped in code. Range and key queries are re-checked at commit time; rich (CouchDB) queries are not re-executed at validation, so do not use rich query results as the basis for writes where phantom reads would be a problem.
- Use composite keys (`CreateCompositeKey`) for secondary lookups on LevelDB-compatible access paths; use CouchDB indexes for rich queries.
- Return typed errors with stable messages. Peers log the chaincode error message; avoid putting secrets in it.
- `GetHistoryForKey` is not for in-transaction logic (history is not part of the read set); use it in queries for audit views.
- Events set with `SetEvent` are visible to all channel members with access to blocks; do not include private data.

CouchDB index files live in the chaincode package under `META-INF/statedb/couchdb/indexes/` and deploy with the chaincode:

```json
{
  "index": { "fields": ["ownerMsp", "updatedAt"] },
  "ddoc": "indexOwnerDoc",
  "name": "indexOwner",
  "type": "json"
}
```

Unit testing: functions take `contractapi.TransactionContextInterface`, so tests can pass a mock stub and client identity (generate mocks with counterfeiter as the Fabric samples do). Integration-test on a local network (`fabric-samples/test-network`) before any channel deployment.

## 5. Chaincode lifecycle

Fabric's lifecycle requires organizations to agree on a chaincode definition. The sequence per upgrade:

```bash
# 1. Package (language-based). The label identifies the package version for humans.
peer lifecycle chaincode package asset_1.0.tar.gz --path ./chaincode --lang golang --label asset_1.0

# 2. Each organization installs on its peers and notes the package ID.
peer lifecycle chaincode install asset_1.0.tar.gz
peer lifecycle chaincode queryinstalled

# 3. Each organization approves the definition (same name, version, sequence, policy, collections).
peer lifecycle chaincode approveformyorg -o orderer.example.com:7050 --tls --cafile "$ORDERER_CA" \
  --channelID mychannel --name asset --version 1.0 --package-id "$PACKAGE_ID" --sequence 1 \
  --signature-policy "AND('Org1MSP.peer','Org2MSP.peer')" --collections-config ./collections_config.json

# 4. Check readiness, then one organization commits once enough organizations approved.
peer lifecycle chaincode checkcommitreadiness --channelID mychannel --name asset --version 1.0 --sequence 1 \
  --signature-policy "AND('Org1MSP.peer','Org2MSP.peer')" --collections-config ./collections_config.json --output json
peer lifecycle chaincode commit -o orderer.example.com:7050 --tls --cafile "$ORDERER_CA" \
  --channelID mychannel --name asset --version 1.0 --sequence 1 \
  --signature-policy "AND('Org1MSP.peer','Org2MSP.peer')" --collections-config ./collections_config.json \
  --peerAddresses peer0.org1.example.com:7051 --tlsRootCertFiles "$ORG1_TLS_CA" \
  --peerAddresses peer0.org2.example.com:9051 --tlsRootCertFiles "$ORG2_TLS_CA"
```

Rules: `--sequence` increments by one with every change (code, policy, collections); definition parameters must match across the approvals; the peer CLI requires the environment for the acting identity (MSP ID, MSP config path, TLS settings), which you set per organization; define upgrade windows because peers must install the new package before commit takes effect. `--init-required` forces an `Init` call; most new contracts avoid `Init` and use ordinary initialization transactions.

## 6. Private data and privacy design

Private data collections keep data on the peers of authorized organizations only; the ordering service and other channel members see only a hash on-chain (add a random salt for low-entropy values). Define collections in JSON and pass them with `--collections-config`:

```json
[
  {
    "name": "assetPrivate",
    "policy": "OR('Org1MSP.member', 'Org2MSP.member')",
    "requiredPeerCount": 1,
    "maxPeerCount": 2,
    "blockToLive": 0,
    "memberOnlyRead": true,
    "memberOnlyWrite": true,
    "endorsementPolicy": { "signaturePolicy": "AND('Org1MSP.member','Org2MSP.member')" }
  }
]
```

- `requiredPeerCount` and `maxPeerCount` control gossip dissemination at endorsement time; set `requiredPeerCount` above 0 for data that must not be lost with a single peer. `blockToLive` 0 keeps data indefinitely; a positive number purges it after that many blocks. `memberOnlyRead`/`memberOnlyWrite` restrict clients to members.
- Implicit per-organization collections (named `_implicit_org_<MSPID>`) exist without configuration and suit data private to one organization.
- Send private values in the transient map (`stub.GetTransient()` in chaincode; transient data in the Gateway proposal), never as function arguments, so they are not recorded in the transaction. Do not return private data in the response or events of a transaction submitted by non-members.
- Prove agreement without revealing data by comparing hashes (`GetPrivateDataHash`) across collections, as in the `asset-transfer-private-data` sample.
- Fabric v2.5 added purging of private data for compliance (`PurgePrivateData`); use it together with `blockToLive` where erasure is a requirement. Hashes remain on-chain; they must not be reversible (use high-entropy values or salts for low-entropy inputs).
- A private data collection is not a replacement for channels when parties must not even know a transaction exists: the hash and the transaction metadata (channel, chaincode, collection name, endorsers) are visible to all channel members.

## 7. Chaincode as a service

By default a peer builds and runs chaincode in containers it manages. Chaincode as a service (CCaaS) runs the chaincode as its own long-lived server, which suits Kubernetes and gives you control over the image, runtime and scaling. The peer image ships the `ccaas_builder` external builder configured in `core.yaml`.

Package: `metadata.json` with `{"type": "ccaas", "label": "asset_1.0"}` and `code.tar.gz` containing `connection.json`:

```json
{
  "address": "asset-cc.org1.svc:9999",
  "dial_timeout": "10s",
  "tls_required": true,
  "client_auth_required": true,
  "client_key": "-----BEGIN EC PRIVATE KEY----- ... -----END EC PRIVATE KEY-----",
  "client_cert": "-----BEGIN CERTIFICATE----- ... -----END CERTIFICATE-----",
  "root_cert": "-----BEGIN CERTIFICATE----- ... -----END CERTIFICATE-----"
}
```

The chaincode process starts a `shim.ChaincodeServer{CCID, Address, CC, TLSProps}` with the package ID in `CHAINCODE_ID` and the listen address in `CHAINCODE_SERVER_ADDRESS`, as in the `asset-transfer-basic/chaincode-external` sample. Use TLS with mutual authentication in production (`tls_required` and `client_auth_required` true), and treat the chaincode server like any other service that holds no more privilege than needed.

## 8. Client applications with Fabric Gateway

The Gateway runs inside the peer. A client sends a proposal to its gateway peer; the gateway collects endorsements (using discovery and the endorsement policy), submits to ordering and reports commit status. Clients hold an identity (certificate), a signer (private key or HSM) and a gRPC connection; they do not need a connection profile or wallet abstractions.

Flow per call: `evaluate` (query on one peer, no ledger change), or `endorse` then `submit` then `commit status`. `submitTransaction` performs all steps and throws if the transaction is not committed successfully.

Go client (from the `application-gateway-go` sample pattern): create one shared gRPC connection and build the gateway.

```go
gw, err := client.Connect(
	id,                                     // identity.NewX509Identity(mspID, certificate)
	client.WithSign(sign),                  // identity.NewPrivateKeySign(privateKey)
	client.WithHash(hash.SHA256),
	client.WithClientConnection(conn),      // grpc.NewClient(endpoint, grpc.WithTransportCredentials(creds))
	client.WithEvaluateTimeout(5*time.Second),
	client.WithEndorseTimeout(15*time.Second),
	client.WithSubmitTimeout(5*time.Second),
	client.WithCommitStatusTimeout(time.Minute),
)
```

TypeScript client (`@hyperledger/fabric-gateway` 1.13, Node 22.12+). Paths and identity come from environment variables; the connection uses TLS to the peer:

```ts
import * as grpc from "@grpc/grpc-js";
import {
  connect,
  hash,
  signers,
  GatewayError,
  type Contract,
  type Gateway,
  type Identity,
  type Signer,
} from "@hyperledger/fabric-gateway";
import { createPrivateKey } from "node:crypto";
import { readFile } from "node:fs/promises";

const decoder = new TextDecoder();

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}

export async function openGateway(): Promise<{ gateway: Gateway; client: grpc.Client }> {
  const tlsRootCert = await readFile(requireEnv("PEER_TLS_CA_FILE"));
  const hostAlias = process.env["PEER_HOST_ALIAS"];
  const client = new grpc.Client(
    requireEnv("PEER_ENDPOINT"),
    grpc.credentials.createSsl(tlsRootCert),
    // Only set the override when the endpoint name differs from the name in the peer TLS certificate.
    hostAlias ? { "grpc.ssl_target_name_override": hostAlias } : {},
  );
  const identity: Identity = {
    mspId: requireEnv("MSP_ID"),
    credentials: await readFile(requireEnv("CLIENT_CERT_FILE")),
  };
  // For HSM-backed keys, supply a signer that calls PKCS#11 instead of newPrivateKeySigner.
  const signer: Signer = signers.newPrivateKeySigner(createPrivateKey(await readFile(requireEnv("CLIENT_KEY_FILE"))));

  const gateway = connect({
    client,
    identity,
    signer,
    hash: hash.sha256,
    evaluateOptions: () => ({ deadline: Date.now() + 5_000 }),
    endorseOptions: () => ({ deadline: Date.now() + 15_000 }),
    submitOptions: () => ({ deadline: Date.now() + 5_000 }),
    commitStatusOptions: () => ({ deadline: Date.now() + 60_000 }),
  });
  return { gateway, client };
}

export class AssetClient {
  constructor(private readonly contract: Contract) {}

  async create(id: string, contentHash: string, documentUri: string): Promise<void> {
    try {
      // Waits for the transaction to be committed in a block and throws if it was invalidated.
      await this.contract.submitTransaction("CreateAsset", id, contentHash, documentUri);
    } catch (error) {
      throw explain(error);
    }
  }

  async read(id: string): Promise<unknown> {
    // evaluateTransaction runs on one peer and does not change the ledger.
    const result = await this.contract.evaluateTransaction("ReadAsset", id);
    return JSON.parse(decoder.decode(result)) as unknown;
  }

  async transfer(id: string, newOwner: string, newOwnerMsp: string): Promise<void> {
    try {
      await this.contract.submitTransaction("TransferAsset", id, newOwner, newOwnerMsp);
    } catch (error) {
      throw explain(error);
    }
  }
}

function explain(error: unknown): Error {
  if (error instanceof GatewayError) {
    // code is the gRPC status; details list per-peer errors (chaincode error messages for failed endorsements)
    return new Error(`Gateway error ${String(error.code)}: ${error.message}`, { cause: error });
  }
  return error instanceof Error ? error : new Error(String(error));
}

export async function privateAgreement(contract: Contract, assetId: string, price: number): Promise<void> {
  // Sensitive values travel in transient data, not in arguments, so they are not stored in the transaction.
  const proposal = contract.newProposal("SetPrice", {
    arguments: [assetId],
    transientData: { price: JSON.stringify({ assetId, price }) },
  });
  const transaction = await proposal.endorse();
  const submitted = await transaction.submit();
  const status = await submitted.getStatus();
  if (!status.successful) throw new Error(`Transaction ${status.transactionId} failed with code ${String(status.code)}`);
}

export async function watchEvents(gateway: Gateway, channel: string, chaincode: string, signal: AbortSignal): Promise<void> {
  const network = gateway.getNetwork(channel);
  const events = await network.getChaincodeEvents(chaincode, { startBlock: 0n });
  signal.addEventListener("abort", () => events.close(), { once: true });
  try {
    for await (const event of events) {
      console.log(event.eventName, decoder.decode(event.payload), event.blockNumber);
    }
  } finally {
    events.close();
  }
}
```

Practices:

- Share one gRPC connection per peer endpoint across gateway instances; create a `Gateway` per identity.
- Set deadlines for each phase; treat a timeout during `submit` as unknown outcome and check the commit status by transaction ID instead of resubmitting blindly. Make chaincode transactions idempotent (reject a duplicate ID or compare hashes) so a retry cannot double-apply.
- Handle MVCC read conflicts (`MVCC_READ_CONFLICT`) with a bounded retry; reduce conflicts by avoiding hot keys (counters, balances) and splitting state across keys.
- For backend services acting for many users, decide between one service identity (simple, audit trail shows the service) and per-user identities held in an HSM or a signing service (traceability, more key handling). Never put user private keys in browsers or logs.
- Use block or chaincode events with a checkpointer to build off-chain read models, and replay from the last committed block after a restart.

## 9. Operations

- Observability: the peer and orderer operations service exposes Prometheus metrics and `/healthz`; configure `operations.listenAddress` and TLS, and keep it off public networks. Alert on block height divergence between peers, ledger commit duration, endorsement failures, MVCC conflicts, gossip membership, orderer consensus leader changes, and certificate expiry.
- Storage: put ledger and state DB on fast persistent volumes; back up the ledger and take ledger snapshots (supported in v2.5 and v3); rebuild a peer by joining from a snapshot rather than replaying from genesis when the history is large.
- Capacity: endorsement is CPU-bound in chaincode execution and signature verification; commit is bound by validation and state DB. Scale endorsing peers horizontally per organization and keep CouchDB indexes in place.
- Upgrades: upgrade orderers first, then peers, one node at a time, validating health between steps; update channel capabilities only after all nodes support them. Read the upgrade documentation for the exact versions involved.
- Disaster recovery: orderer cluster quorum loss needs a documented recovery plan; keep copies of channel genesis and configuration blocks and of CA databases and keys (encrypted, offline).
- Local development: `fabric-samples/test-network` brings up two organizations and an ordering service, with options for CouchDB, CCaaS and BFT ordering.
