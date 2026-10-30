# Cloud SQL, Pub/Sub and Cloud Storage

Connectivity, authentication and safe defaults for the managed data services most workloads use. Commands were checked against Google Cloud CLI 570.0.0 and Cloud SQL Auth Proxy v2 (2.27.0) (2026-10).

## Contents

1. [Cloud SQL connectivity options](#1-cloud-sql-connectivity-options)
2. [Cloud SQL private IP and creation](#2-cloud-sql-private-ip-and-creation)
3. [Cloud SQL Auth Proxy and connectors](#3-cloud-sql-auth-proxy-and-connectors)
4. [IAM database authentication](#4-iam-database-authentication)
5. [Pub/Sub delivery semantics](#5-pubsub-delivery-semantics)
6. [Pub/Sub subscriptions in practice](#6-pubsub-subscriptions-in-practice)
7. [Cloud Storage security defaults](#7-cloud-storage-security-defaults)
8. [Lifecycle rules and storage classes](#8-lifecycle-rules-and-storage-classes)
9. [Signed URLs](#9-signed-urls)

## 1. Cloud SQL connectivity options

| Option | When to use | Notes |
|---|---|---|
| Language connector (Go, Java, Python, Node.js libraries) | Application code connecting directly | In-process, IAM-checked, encrypted, no sidecar |
| Cloud SQL Auth Proxy v2 (`cloud-sql-proxy`) | Any language, local development, sidecars, VMs | Listens on localhost; uses the caller's IAM identity; encrypts traffic |
| Private IP (private services access) | Workloads inside the VPC | No public exposure; the proxy or connector is still recommended for IAM and certificates |
| Private Service Connect | Consumers in other VPCs or projects | Set at creation with `--enable-private-service-connect` and `--allowed-psc-projects` |
| Public IP with authorized networks | Last resort | Never authorize `0.0.0.0/0`; prefer proxy with IAM |

- The caller needs `roles/cloudsql.client` to connect through the proxy or a connector, and `roles/cloudsql.instanceUser` to log in with IAM database authentication.
- Cloud Run can mount a socket with `--add-cloudsql-instances PROJECT:REGION:INSTANCE`, which exposes `/cloudsql/PROJECT:REGION:INSTANCE`. With private IP instances, combine Direct VPC egress with a connector or the proxy configured for private IP.
- `--ssl-mode` on the instance accepts `ALLOW_UNENCRYPTED_AND_ENCRYPTED`, `ENCRYPTED_ONLY` and `TRUSTED_CLIENT_CERTIFICATE_REQUIRED`. Use at least `ENCRYPTED_ONLY`.

## 2. Cloud SQL private IP and creation

Private services access needs an allocated range and a peering with the service network:

```bash
gcloud compute addresses create google-managed-services-prod \
  --project=orders-prod --global --purpose=VPC_PEERING --prefix-length=20 \
  --network=prod-vpc

gcloud services vpc-peerings connect \
  --project=orders-prod --network=prod-vpc \
  --ranges=google-managed-services-prod
```

Create a PostgreSQL instance with private IP only, TLS required, IAM authentication on, backups and deletion protection:

```bash
gcloud sql instances create orders-pg \
  --project=orders-prod --region=us-central1 \
  --database-version=POSTGRES_17 --edition=enterprise --tier=db-custom-2-8192 \
  --network=projects/orders-prod/global/networks/prod-vpc --no-assign-ip \
  --ssl-mode=ENCRYPTED_ONLY \
  --database-flags=cloudsql.iam_authentication=on \
  --availability-type=REGIONAL \
  --backup-start-time=03:00 --enable-point-in-time-recovery \
  --deletion-protection
```

- Pick the database version and tier from `gcloud sql tiers list` and `gcloud sql flags list --database-version=...`; the values above are examples and the supported set changes.
- `--edition` takes `enterprise` or `enterprise-plus`.
- `gcloud sql instances patch --database-flags=...` replaces the full set of flags, so include every flag you want to keep.
- Enforce no public IPs across a folder with `constraints/sql.restrictPublicIp`.
- Maintenance, failover and restarts drop connections. Clients need retry with backoff and short pool lifetimes.

## 3. Cloud SQL Auth Proxy and connectors

```bash
# Local development or a sidecar; the proxy uses Application Default Credentials
cloud-sql-proxy --private-ip --auto-iam-authn \
  orders-prod:us-central1:orders-pg

# Print all flags available in the installed version
cloud-sql-proxy --help
```

- Instance connection name format: `PROJECT:REGION:INSTANCE`.
- In v2 the proxy connects to the public IP by default; pass `--private-ip` for private IP (see `cloud-sql-proxy --help` for the Private Service Connect option). The machine running the proxy must have a network path to the instance.
- `--auto-iam-authn` makes the proxy supply the IAM token as the database password for PostgreSQL and MySQL; the application connects to `127.0.0.1` without a password and with the IAM database username.
- Run the proxy as a sidecar or a local process; do not expose its listener beyond localhost (`--address` defaults to loopback).
- Pin the proxy version in production images and check releases for security fixes. Some Go toolchain versions are known to be incompatible with specific proxy releases, so read the release notes when upgrading either.
- Connectors in application code (for example the Go, Java, Python and Node.js connector libraries) avoid the extra process. Follow each library's current documentation for API details.

## 4. IAM database authentication

```bash
# 1. Enable on the instance (PostgreSQL flag)
gcloud sql instances patch orders-pg --project=orders-prod \
  --database-flags=cloudsql.iam_authentication=on

# 2. Create a database user for the workload's service account
gcloud sql users create "orders-api@orders-prod.iam" \
  --instance=orders-pg --project=orders-prod --type=CLOUD_IAM_SERVICE_ACCOUNT

# 3. Allow the service account to connect
gcloud projects add-iam-policy-binding orders-prod \
  --member="serviceAccount:orders-api@orders-prod.iam.gserviceaccount.com" \
  --role=roles/cloudsql.instanceUser
gcloud projects add-iam-policy-binding orders-prod \
  --member="serviceAccount:orders-api@orders-prod.iam.gserviceaccount.com" \
  --role=roles/cloudsql.client
```

- For PostgreSQL, the IAM service account user name is the service account email without the `.gserviceaccount.com` suffix; users and groups use their email. Check the current Cloud SQL IAM authentication page for the exact format for your engine and for MySQL.
- A newly created IAM database user has login rights only. Grant database privileges inside the database with SQL, for example `GRANT CONNECT ON DATABASE orders TO "orders-api@orders-prod.iam";` and table grants as needed. Grant the minimum privileges, and never make the application role a superuser.
- The role bindings above are project-wide for brevity; prefer a condition or a dedicated project when the project hosts several instances.
- Built-in database users with passwords remain for administration; keep their passwords in Secret Manager and rotate them.

## 5. Pub/Sub delivery semantics

- **At-least-once** is the default: a message can be delivered more than once, and handlers must be idempotent (use the message ID or a business key to deduplicate).
- **Acknowledgement deadline**: the subscriber has `--ack-deadline` seconds (maximum 600) to ack before redelivery. Client libraries extend the deadline while a message is being processed; set an upper bound for stuck handlers.
- **Retention**: unacknowledged messages stay for `--message-retention-duration` (default 7 days, between 10 minutes and 31 days). `--retain-acked-messages` keeps acked messages for replay within the same window.
- **Dead-letter topics**: after `--max-delivery-attempts` (5 to 100, default 5) failed deliveries a message is forwarded to `--dead-letter-topic`. The Pub/Sub service agent needs publisher rights on that topic and subscriber rights on the source subscription.
- **Retry policy**: `--min-retry-delay` and `--max-retry-delay` apply exponential backoff to redelivery instead of immediate retry.
- **Exactly-once delivery** (`--enable-exactly-once-delivery`): pull subscriptions only (including StreamingPull); push and export subscriptions are not supported. The guarantee holds when subscribers connect in one region, so use a regional endpoint for multi-region deployments. Acks and deadline modifications can fail with an error if the ack ID expired, which clients must handle. It prevents redelivery after a successful ack; it does not make your side effects idempotent.
- **Ordering**: publish with an ordering key and create the subscription with `--enable-message-ordering`. Messages with the same key are delivered in publish order; different keys have no relative order. A publish failure for a key pauses that key until the publisher resumes it. Publishers should publish to the same region for ordering to hold.
- **Filtering**: `--message-filter` drops non-matching messages at the subscription, which costs less than receiving and discarding them.

## 6. Pub/Sub subscriptions in practice

Pull subscription with dead-lettering and backoff:

```bash
gcloud pubsub subscriptions create orders-worker --project=orders-prod \
  --topic=orders --ack-deadline=60 \
  --message-retention-duration=3d \
  --min-retry-delay=10s --max-retry-delay=300s \
  --dead-letter-topic=orders-dead-letter --max-delivery-attempts=5
```

Push subscription with an authenticated endpoint (the receiver verifies the token):

```bash
gcloud pubsub subscriptions create orders-push --project=orders-prod \
  --topic=orders --ack-deadline=30 \
  --push-endpoint=https://orders-api-abc123-uc.a.run.app/pubsub \
  --push-auth-service-account=pubsub-invoker@orders-prod.iam.gserviceaccount.com
```

The push service account needs `roles/run.invoker` on the target Cloud Run service. Verify the audience and issuer of the token in the receiver if the endpoint is not behind Cloud Run's own authentication.

Ordered publishing from the CLI (client libraries provide the same option):

```bash
gcloud pubsub topics publish orders --project=orders-prod \
  --message='{"order_id":"o-1001","status":"paid"}' --ordering-key=o-1001
```

Subscriber pattern with the Python client (acknowledge after the work is durable; exactly-once subscriptions have a response-returning ack variant). Check the current client library docs for exact signatures:

```python
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
path = subscriber.subscription_path("orders-prod", "orders-worker")

def handle(message: pubsub_v1.subscriber.message.Message) -> None:
    try:
        process_idempotently(message.message_id, message.data)  # your function
    except Exception:
        message.nack()          # redelivery counts toward max delivery attempts
        return
    message.ack()

flow = pubsub_v1.types.FlowControl(max_messages=50)
future = subscriber.subscribe(path, callback=handle, flow_control=flow)
with subscriber:
    try:
        future.result()
    except (TimeoutError, KeyboardInterrupt):
        future.cancel()
        future.result()
```

Alert on oldest unacked message age and on dead-letter subscription backlog (alert design: observability-expert).

## 7. Cloud Storage security defaults

```bash
gcloud storage buckets create gs://orders-prod-uploads \
  --project=orders-prod --location=us-central1 \
  --uniform-bucket-level-access --public-access-prevention \
  --default-storage-class=standard \
  --soft-delete-duration=14d

gcloud storage buckets update gs://orders-prod-uploads --versioning
```

- **Uniform bucket-level access** disables object ACLs so IAM is the only access control; enforce with `constraints/storage.uniformBucketLevelAccess`.
- **Public access prevention** blocks `allUsers` and `allAuthenticatedUsers` grants; enforce with `constraints/storage.publicAccessPrevention`. Serve public content from a dedicated bucket or a load balancer with a backend bucket, and exempt only that bucket.
- Grant roles per bucket to service accounts (`roles/storage.objectViewer`, `roles/storage.objectCreator`); avoid `roles/storage.admin` for applications. Scope with IAM conditions to an object prefix for multi-tenant buckets.
- **Soft delete** (default 7 days; `0` disables it) and **object versioning** protect against accidental deletion and overwrite; versioning needs lifecycle rules to limit cost.
- **Retention policies** (`--retention-period`) and holds make objects immutable for a period; locking a policy cannot be undone, so confirm the period first.
- Use customer-managed keys (`--default-encryption-key`) when policy requires control of key rotation or revocation.
- Choose bucket location by latency, residency and availability needs; dual-region and multi-region cost more.

## 8. Lifecycle rules and storage classes

Storage classes trade storage price against retrieval cost and minimum storage duration: Standard, Nearline, Coldline and Archive (Archive is the coldest). Check the current pricing page for exact prices and minimum durations before moving data. `--enable-autoclass` lets Cloud Storage move objects between classes by access pattern.

```json
{
  "rule": [
    {
      "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
      "condition": {"age": 30, "matchesStorageClass": ["STANDARD"]}
    },
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    },
    {
      "action": {"type": "Delete"},
      "condition": {"daysSinceNoncurrentTime": 14, "isLive": false}
    }
  ]
}
```

```bash
gcloud storage buckets update gs://orders-prod-uploads --lifecycle-file=lifecycle.json
gcloud storage buckets describe gs://orders-prod-uploads --format="json(lifecycle_config)"
```

- `--clear-lifecycle` removes all rules. Test rules on a non-production bucket first, since a Delete action is irreversible once soft delete expires.
- Conditions in a rule combine with AND; separate rules combine with OR.
- Do not combine Autoclass with manual class-transition rules on the same bucket without reading the Autoclass documentation.

## 9. Signed URLs

```bash
gcloud storage sign-url gs://orders-prod-uploads/tenant-a/report.pdf \
  --duration=10m \
  --impersonate-service-account=url-signer@orders-prod.iam.gserviceaccount.com

gcloud storage sign-url gs://orders-prod-uploads/tenant-a/incoming/o-1001.csv \
  --http-verb=PUT --headers=content-type=text/csv --duration=5m \
  --impersonate-service-account=url-signer@orders-prod.iam.gserviceaccount.com
```

- Signing by impersonation avoids key files. The CLI documents a 12 hour maximum for this path (the system-managed key may not stay valid longer); 7 days is possible only with a private key file or an account authorized with a key, which this guidance avoids. Keep lifetimes at minutes for downloads and uploads.
- The caller needs `roles/iam.serviceAccountTokenCreator` on the signing account, and the signing account needs access to the object (a signed URL grants the signer's permissions).
- Server-side code should generate object names itself (a tenant prefix plus a random ID) and never take a client-supplied path. Reject `..` segments and absolute paths before signing, and validate content type and size limits in the signed headers or with a separate scanner.
- A signed URL is a bearer credential: anyone with the URL can use it until expiry. Do not log full URLs.
