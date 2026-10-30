# Cloud Run and GKE

Deploying and configuring Cloud Run services and jobs, and creating GKE Autopilot and Standard clusters, with flags checked against Google Cloud CLI 570.0.0 (2026-10). Kubernetes manifests, Helm and operators are covered by kubernetes-expert.

## Contents

1. [Cloud Run services](#1-cloud-run-services)
2. [Scaling, concurrency and CPU](#2-scaling-concurrency-and-cpu)
3. [Ingress, authentication and invokers](#3-ingress-authentication-and-invokers)
4. [Secrets and service identity](#4-secrets-and-service-identity)
5. [Private networking from Cloud Run](#5-private-networking-from-cloud-run)
6. [Revisions and traffic](#6-revisions-and-traffic)
7. [Cloud Run jobs](#7-cloud-run-jobs)
8. [GKE Autopilot](#8-gke-autopilot)
9. [GKE Standard](#9-gke-standard)
10. [Release channels and maintenance](#10-release-channels-and-maintenance)
11. [Choosing between Cloud Run and GKE](#11-choosing-between-cloud-run-and-gke)

## 1. Cloud Run services

A service runs a container that listens for HTTP requests (or gRPC) on the port in `$PORT` (default 8080). Each deploy creates an immutable revision.

```bash
gcloud run deploy orders-api \
  --project=orders-prod --region=us-central1 \
  --image=us-central1-docker.pkg.dev/orders-prod/apps/orders-api:1.4.2 \
  --service-account=orders-api@orders-prod.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --labels=env=prod,team=orders
```

- Deploy by image digest or an immutable tag so a revision always maps to one build. `--source` builds from source with a buildpack; image builds themselves are covered by docker-expert.
- `--timeout` sets the request timeout; `--cpu` and `--memory` set resources per instance; `--execution-environment` selects the sandbox generation (check the current docs for differences before choosing).
- `--revision-suffix` gives a revision a readable name; `--description` and `--labels` aid audit and billing.
- Containers must be stateless: local disk is in-memory and per instance, and instances can be stopped at any time. Persist to Cloud SQL, Cloud Storage or another managed service.
- Handle `SIGTERM` and finish in-flight work within the shutdown grace period; log to stdout and stderr.

## 2. Scaling, concurrency and CPU

| Flag | Meaning |
|---|---|
| `--min-instances=N` | Keeps N instances warm; removes cold starts for that capacity but you pay for idle instances |
| `--max-instances=N` | Upper bound on instances; protects databases and caps spend. Modifying it creates a new revision |
| `--concurrency=N` | Maximum simultaneous requests per instance. Default 80, maximum 1000. Use 1 for code that is not safe under concurrency |
| `--[no-]cpu-throttling` | Throttled CPU outside request handling (default behaviour) versus CPU always allocated; use the latter for background work between requests |
| `--[no-]cpu-boost` | Extra CPU during instance startup to shorten cold starts |
| `--timeout` | Per-request time limit |

- Instances scale on concurrent requests and CPU use. A lower concurrency means more instances; a higher value uses fewer instances but needs thread-safe code and enough memory.
- `--min` (a service-level minimum across revisions) exists next to `--min-instances` (per revision); read `gcloud run deploy --help` for the current distinction before using either in automation.
- Size `--max-instances` against downstream limits: with `--max-instances=20` and a pool of 10 connections per instance, Cloud SQL sees up to 200 connections.
- Cold start levers in order of cost: smaller image and lazy initialisation, `--cpu-boost`, then `--min-instances`.

## 3. Ingress, authentication and invokers

Two separate controls decide who can call a service:

| Control | Flag | Values |
|---|---|---|
| Network path | `--ingress` | `all` (default), `internal`, `internal-and-cloud-load-balancing` |
| Caller identity | `--[no-]allow-unauthenticated` | Public calls allowed or `roles/run.invoker` required |

- `internal` accepts requests from VPC networks in the same project or VPC Service Controls perimeter, plus Pub/Sub and Eventarc in the same project or perimeter. `internal-and-cloud-load-balancing` additionally allows Google Cloud load balancers.
- Authenticated calls carry an ID token whose audience is the service URL. Grant `roles/run.invoker` on the single service:

```bash
gcloud run services add-iam-policy-binding orders-api --region=us-central1 \
  --member="serviceAccount:frontend@orders-prod.iam.gserviceaccount.com" \
  --role=roles/run.invoker --project=orders-prod
```

- A caller with the right role can test with `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$SERVICE_URL"`.
- `--[no-]invoker-iam-check` can turn off the invoker check. Leave it on unless another layer (for example a load balancer with Identity-Aware Proxy) authenticates callers, and document why.
- A public service should sit behind a global external Application Load Balancer when you need Cloud Armor, custom domains with managed certificates, or a CDN; set ingress to `internal-and-cloud-load-balancing` so the default URL is not a bypass.

## 4. Secrets and service identity

```bash
printf '%s' "$DB_PASSWORD_VALUE" | gcloud secrets create orders-db-password \
  --project=orders-prod --replication-policy=automatic --data-file=-

gcloud secrets add-iam-policy-binding orders-db-password --project=orders-prod \
  --member="serviceAccount:orders-api@orders-prod.iam.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor

gcloud run deploy orders-api --project=orders-prod --region=us-central1 \
  --image=us-central1-docker.pkg.dev/orders-prod/apps/orders-api:1.4.2 \
  --set-secrets="DB_PASSWORD=orders-db-password:3,/secrets/api/key=orders-api-key:latest"
```

- `--set-secrets` replaces all secret references; `--update-secrets` and `--remove-secrets` change some of them. Form: `ENV_NAME=SECRET:VERSION` for an environment variable, or `/mount/path/file=SECRET:VERSION` for a mounted file.
- Pin a numbered version for stability and roll secrets deliberately; `latest` is read when an instance starts, so running instances keep old values until they restart.
- The secret value in the first command comes from a variable your pipeline supplies at run time; never type it into a command history or commit it.
- The service identity (`--service-account`) is the only credential the container has. Application Default Credentials in client libraries use it automatically through the metadata server. Create one account per service and grant only what the service uses.
- The deploying principal needs `roles/iam.serviceAccountUser` on the runtime service account.

## 5. Private networking from Cloud Run

Direct VPC egress sends outbound traffic into your VPC without a connector:

```bash
gcloud run deploy orders-api --project=orders-prod --region=us-central1 \
  --image=us-central1-docker.pkg.dev/orders-prod/apps/orders-api:1.4.2 \
  --network=prod-vpc --subnet=run-us-central1 \
  --vpc-egress=private-ranges-only \
  --network-tags=orders-api
```

- `--vpc-egress` values: `private-ranges-only` (only RFC 1918 and similar ranges go through the VPC), `all-traffic` (everything, requiring Cloud NAT for internet access). `all` is accepted but deprecated in favour of `all-traffic`.
- The subnet must be /26 or larger, and plan address space for the maximum instance count.
- Network tags on the service let VPC firewall rules target it.
- A Serverless VPC Access connector (`--vpc-connector`) is the older option; use it only where Direct VPC egress is not suitable.
- For Cloud SQL on private IP, combine Direct VPC egress with a connector library or the Auth Proxy; for public-IP instances, `--add-cloudsql-instances` mounts the proxy socket (see data-services.md).

## 6. Revisions and traffic

```bash
# Deploy without sending traffic, with a tag for testing
gcloud run deploy orders-api --project=orders-prod --region=us-central1 \
  --image=us-central1-docker.pkg.dev/orders-prod/apps/orders-api:1.5.0 \
  --no-traffic --tag=candidate

# Gradual rollout, then roll back by moving traffic
gcloud run services update-traffic orders-api --region=us-central1 --project=orders-prod \
  --to-revisions=orders-api-00041-abc=90,orders-api-00042-def=10
gcloud run services update-traffic orders-api --region=us-central1 --project=orders-prod --to-latest
```

- Tagged revisions get their own URL for smoke tests without affecting production traffic.
- Keep the previous revision until the new one has served real traffic without errors; rollback is a traffic change, not a rebuild.

## 7. Cloud Run jobs

Jobs run containers to completion (batch work, migrations, scheduled tasks) and exit; they are not for serving requests.

```bash
gcloud run jobs create orders-migrate --project=orders-prod --region=us-central1 \
  --image=us-central1-docker.pkg.dev/orders-prod/apps/orders-api:1.5.0 \
  --command=/app/migrate --args=up \
  --service-account=orders-migrator@orders-prod.iam.gserviceaccount.com \
  --set-secrets="DB_PASSWORD=orders-db-password:3" \
  --tasks=1 --max-retries=1 --task-timeout=15m

gcloud run jobs execute orders-migrate --project=orders-prod --region=us-central1 --wait
```

- `--tasks` sets the number of tasks per execution (default 1) and `--parallelism` how many run at once. Each task gets `CLOUD_RUN_TASK_INDEX` and `CLOUD_RUN_TASK_COUNT` environment variables to partition work.
- `--max-retries` retries a failed task; `--task-timeout` bounds each task. Make tasks idempotent because retries re-run them.
- `gcloud run jobs execute --wait` blocks until the execution finishes and returns a non-zero status on failure, which suits CI migration steps. Use `--args` or `--update-env-vars` on execute to override per run.
- Scheduling runs with Cloud Scheduler needs a service account with permission to run the job; check the current Cloud Scheduler and Cloud Run jobs documentation for the exact trigger setup.
- Use a separate, more privileged service account for migrations than for the serving container.

## 8. GKE Autopilot

```bash
gcloud container clusters create-auto orders-auto \
  --project=orders-prod --location=us-central1 \
  --release-channel=regular \
  --network=prod-vpc --subnetwork=gke-us-central1 \
  --enable-private-nodes \
  --enable-master-authorized-networks \
  --master-authorized-networks=203.0.113.0/24 \
  --labels=env=prod,team=orders

gcloud container clusters get-credentials orders-auto --location=us-central1 --project=orders-prod
```

- Autopilot manages nodes, scaling and many hardening settings; you pay for the resources Pods request, so right-size requests. Workload Identity Federation for GKE is always on.
- Control plane access: `--enable-master-authorized-networks` limits public endpoint sources; `--enable-private-endpoint` removes the public endpoint; `--enable-dns-access` enables the DNS-based endpoint and `--enable-ip-access` controls the IP-based endpoint. Choose one access model per environment and test from the real client network.
- `--security-posture` and `--workload-vulnerability-scanning` accept `standard`, `enterprise` (posture only) or `disabled`; check the current editions page for what each tier includes.
- Autopilot restricts some privileged workloads (privileged containers, host access); workloads that need them belong on Standard.
- `kubectl` access requires the `gke-gcloud-auth-plugin` component; follow the current install docs.

## 9. GKE Standard

```bash
gcloud container clusters create orders-std \
  --project=orders-prod --location=us-central1 \
  --release-channel=regular \
  --workload-pool=orders-prod.svc.id.goog \
  --enable-ip-alias --enable-shielded-nodes \
  --enable-private-nodes \
  --service-account=gke-nodes@orders-prod.iam.gserviceaccount.com \
  --num-nodes=1 --enable-autoupgrade --enable-autorepair

gcloud container node-pools create batch \
  --project=orders-prod --cluster=orders-std --location=us-central1 \
  --spot --enable-autoscaling --min-nodes=0 --max-nodes=10 \
  --workload-metadata=GKE_METADATA \
  --node-taints=workload=batch:NoSchedule
```

- `--num-nodes` is per zone for regional clusters. A regional cluster spreads nodes across zones (`--node-locations` selects them).
- Give nodes a dedicated service account with logging, monitoring and image-pull roles only; do not use the default Compute Engine account.
- `--workload-pool` enables Workload Identity Federation for GKE; node pools using `GKE_METADATA` expose the GKE metadata server to Pods.
- `--spot` node pools suit fault-tolerant batch work because nodes can be reclaimed at short notice.
- Upgrade tuning per pool: `--max-surge-upgrade` (default 1) and `--max-unavailable-upgrade`.

## 10. Release channels and maintenance

- `--release-channel` accepts `rapid`, `regular`, `stable`, `extended`, or `None` to opt out. A cluster created without a channel and without a version is enrolled in Regular; specifying a version without a channel enrolls it in the most mature channel that offers the version.
- In a channel, Google maintains control plane and node versions and node auto-upgrade is on by default. `extended` keeps a minor version available for longer than the other channels (the CLI help states up to 24 months from the minor version's Regular availability).
- Use maintenance windows and exclusions to control timing:

```bash
gcloud container clusters update orders-std --location=us-central1 --project=orders-prod \
  --maintenance-window-start=2026-01-01T02:00:00Z \
  --maintenance-window-end=2026-01-01T08:00:00Z \
  --maintenance-window-recurrence='FREQ=WEEKLY;BYDAY=SA,SU'
```

- Check the GKE release notes for the current default version per channel and for deprecated Kubernetes APIs before each minor upgrade.

## 11. Choosing between Cloud Run and GKE

| Need | Choose |
|---|---|
| Stateless HTTP or event-driven container, scale to zero | Cloud Run service |
| Batch, migration or scheduled task that exits | Cloud Run job |
| Kubernetes API, operators, service mesh, StatefulSets | GKE Autopilot |
| Custom nodes, GPUs with specific drivers, privileged DaemonSets | GKE Standard |
| Minimal operations team, no cluster expertise | Cloud Run |
