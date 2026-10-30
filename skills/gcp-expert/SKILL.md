---
name: gcp-expert
description: >-
  Designs and operates workloads on Google Cloud: resource hierarchy, IAM and least privilege, keyless auth with Workload Identity Federation, Cloud Run, GKE, Cloud SQL, Pub/Sub, Cloud Storage, VPC networking and cost controls, using current gcloud commands. Use when writing gcloud commands, IAM bindings or conditions, org policies, google-github-actions/auth workflows, Cloud Run deploys, Pub/Sub subscriptions, or budgets. Not for AWS (use aws-expert), Kubernetes manifests (use kubernetes-expert), Terraform design (use terraform-expert), images (use docker-expert), or metrics and tracing (use observability-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# GCP Expert

This skill covers building and running workloads on Google Cloud with the `gcloud` CLI: organization, folder and project structure, IAM design, keyless authentication, serverless and Kubernetes compute, managed data services, networking and cost governance. It focuses on the choices that are easy to get wrong (identity, network exposure, delivery semantics, spend limits) and leaves infrastructure-as-code structure, Kubernetes objects and observability design to the neighbouring skills.

> Verified against Google Cloud CLI 570.0.0 (command and flag names checked with `gcloud help`), google-github-actions/auth v3 (3.0.0), google-github-actions/setup-gcloud v3 (3.0.1) and Cloud SQL Auth Proxy v2 (2.27.0) (2026-10).

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

- Covered: resource hierarchy and org policies, IAM roles, conditions and deny policies, service accounts, Workload Identity Federation for external CI and for GKE, Cloud Run services and jobs, GKE Autopilot and Standard cluster choices, Cloud SQL connectivity and IAM database authentication, Pub/Sub delivery semantics, Cloud Storage security and lifecycle, VPC design, Private Google Access, Private Service Connect, Cloud NAT, firewall policies, VPC Service Controls, budgets, billing export, committed use discounts, labels and quotas.
- Not covered: AWS services (aws-expert), Kubernetes manifests, Helm and operators (kubernetes-expert), Terraform module and state design (terraform-expert), container image builds (docker-expert), CI pipeline structure (cicd-expert), the Gemini API (gemini-sdk-expert), metrics, logs and tracing design (observability-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Hierarchy | Organization > folders > projects > resources. IAM policies and org policies inherit downward and the effective policy is the union of allows (minus denies). The project ID is immutable and globally unique; the project number is what IAM principal identifiers use |
| Roles | Basic roles (`roles/owner`, `editor`, `viewer`) are broad; prefer predefined roles, then custom roles (`gcloud iam roles create --file=...`) when no predefined role is narrow enough. Some commands, such as `gcloud run services add-iam-policy-binding`, reject basic roles, but do not rely on that |
| IAM conditions | `--condition=title=...,expression=...` on `add-iam-policy-binding`, or `--condition-from-file`. Use `^:^` as a delimiter prefix when the expression contains commas. Conditions use CEL over resource, request time and (for some products) tags |
| Deny policies | `gcloud iam policies create ID --attachment-point=... --kind=denypolicies --policy-file=...`. Deny is evaluated before allow, so it overrides grants; use for guardrails such as blocking a permission for everyone but an admin group |
| Service account keys | Constraints `constraints/iam.disableServiceAccountKeyCreation` and `constraints/iam.disableServiceAccountKeyUpload` block persistent keys; `constraints/iam.serviceAccountKeyExpiryHours` limits lifetime where keys must exist. New organizations get a security baseline that enforces the key constraints; older organizations must set them. A managed variant `constraints/iam.managed.disableServiceAccountKeyCreation` also exists, so check which name your tooling reports |
| Workload Identity Federation | Pool plus provider (`gcloud iam workload-identity-pools providers create-oidc`). `--attribute-condition` is the entry gate and `--attribute-mapping` exposes claims such as `attribute.repository`. Grant `roles/iam.workloadIdentityUser` on a service account to a `principalSet://` member, or skip the service account and grant roles directly to the principal |
| google-github-actions/auth | Needs `permissions: id-token: write`. Inputs: `workload_identity_provider`, `service_account` (omit for direct federation), `project_id`, `token_format`, `create_credentials_file`. v3 runs on Node 24 and removed deprecated inputs |
| Workload Identity Federation for GKE | Autopilot has it always on. On Standard add `--workload-pool=PROJECT_ID.svc.id.goog` to the cluster and `GKE_METADATA` on node pools. Grant roles directly to `principal://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/PROJECT_ID.svc.id.goog/subject/ns/NAMESPACE/sa/KSA_NAME` |
| Cloud Run | `gcloud run deploy` for services, `gcloud run jobs` for run-to-completion work. Flags: `--min-instances`, `--max-instances`, `--concurrency` (default 80, up to 1000), `--ingress` (`all`, `internal`, `internal-and-cloud-load-balancing`), `--service-account`, `--set-secrets`, `--network`/`--subnet`/`--vpc-egress` for Direct VPC egress, `--[no-]cpu-throttling` |
| GKE | Autopilot (Google manages nodes, pay per Pod resource requests) or Standard (you manage node pools). `--release-channel` takes `rapid`, `regular`, `stable`, `extended` (or `None` to opt out). A cluster created without a channel or version is enrolled in Regular |
| Cloud SQL | Cloud SQL Auth Proxy v2 (`cloud-sql-proxy`) or language connectors give IAM-checked, TLS-encrypted connections. v2 uses public IP unless `--private-ip` is passed. IAM database authentication: PostgreSQL flag `cloudsql.iam_authentication=on`; users via `gcloud sql users create --type=...`. `--ssl-mode` values: `ALLOW_UNENCRYPTED_AND_ENCRYPTED`, `ENCRYPTED_ONLY`, `TRUSTED_CLIENT_CERTIFICATE_REQUIRED` |
| Pub/Sub | At-least-once delivery by default. `--ack-deadline` (seconds, max 600), `--dead-letter-topic` with `--max-delivery-attempts` (5 to 100, default 5), `--enable-message-ordering`, `--enable-exactly-once-delivery` (pull subscriptions only, guarantee holds within one region), `--message-retention-duration` (10 minutes to 31 days, default 7 days) |
| Cloud Storage | `gcloud storage buckets create --uniform-bucket-level-access --public-access-prevention`; lifecycle through `--lifecycle-file`; `gcloud storage sign-url --duration=... --impersonate-service-account=...` signs without a key file; soft delete via `--soft-delete-duration` |
| VPC | `gcloud compute networks create NAME --subnet-mode=custom`; per-subnet `--enable-private-ip-google-access`; Private Service Connect endpoints for Google APIs use a global address with `--purpose=PRIVATE_SERVICE_CONNECT` and a forwarding rule with `--target-google-apis-bundle=all-apis` or `vpc-sc`; network firewall policies via `gcloud compute network-firewall-policies` |
| VPC Service Controls | Perimeters via `gcloud access-context-manager perimeters create` (`--resources`, `--restricted-services`, `--policy`, ingress and egress YAML); dry-run mode with `perimeters dry-run` before enforcing |
| Cost | `gcloud billing budgets create` (`--threshold-rule=percent=0.5,basis=forecasted-spend`, `--filter-projects`, `--filter-labels`, `--notifications-rule-pubsub-topic`). Budgets alert; they do not stop spend. Billing export to BigQuery is enabled in the Billing console |

## 3. Workflow

1. Establish the context: organization or standalone project, billing account, environments, regions, data residency and compliance needs, and which identities (people, CI, workloads) need access.
2. Inspect before changing: `gcloud config list`, `gcloud projects describe PROJECT_ID`, `gcloud projects get-iam-policy PROJECT_ID`, `gcloud org-policies list --project=PROJECT_ID`, `gcloud services list --enabled`.
3. Place the work in the hierarchy: one project per environment and workload boundary, folders to attach policy, labels for cost allocation.
4. Design identity first: one user-managed service account per workload, narrowest predefined role on the narrowest resource, keyless authentication for CI and for workloads outside Google Cloud.
5. Choose compute (Cloud Run, GKE Autopilot, GKE Standard) using the decision rules below, then network exposure (ingress, private connectivity, egress path).
6. Create resources with explicit `--project` and `--region` flags so commands do not depend on ambient configuration. Prefer a dry run or `describe` after each create.
7. Add guardrails: org policies, budgets with alerts, quotas awareness, and VPC Service Controls in dry-run mode when exfiltration risk matters.
8. Verify with `gcloud ... describe`, test connectivity from the real caller identity, and record the commands in the project's IaC or runbook (see terraform-expert for module design).

## 4. Decision Rules

- If a workload is a stateless HTTP container or a run-to-completion task, use Cloud Run (service or job) because it scales to zero and has no cluster to patch. Choose GKE when you need Kubernetes APIs, custom controllers, DaemonSets, or tight node control.
- If you choose GKE and do not need node-level control, use Autopilot because Google manages nodes and hardening defaults. Use Standard for specific machine, GPU or kernel requirements.
- Subscribe production GKE clusters to the Regular or Stable release channel because Google then manages upgrades; use Rapid only for pre-production, and `extended` when you need longer minor-version support.
- If CI runs on GitHub Actions (or any OIDC issuer), use Workload Identity Federation, never a downloaded service account key.
- If a workload runs on GKE, use Workload Identity Federation for GKE with direct principal grants; do not mount key files into Pods.
- If a service must be reachable only from your VPC, set `--ingress=internal`; to publish it behind a load balancer set `--ingress=internal-and-cloud-load-balancing`. Ingress and `--[no-]allow-unauthenticated` are independent controls.
- If a Cloud Run service needs a private resource, use Direct VPC egress (`--network`, `--subnet`, `--vpc-egress`) and keep `private-ranges-only` unless all egress must traverse the VPC.
- If a Cloud Run cold start hurts latency, set `--min-instances` and consider `--no-cpu-throttling` only if background work after the response is needed; both cost money while idle.
- If consumers must not see duplicates, enable exactly-once delivery on a pull subscription and still make handlers idempotent, because the guarantee is regional and does not cover side effects.
- If message order matters, publish with an ordering key and create the subscription with `--enable-message-ordering`; ordering only holds per key and limits parallelism.
- If an application connects to Cloud SQL, use a connector or the Auth Proxy with IAM database authentication where the engine supports it; avoid authorized networks with `0.0.0.0/0`.
- If a bucket stores user uploads, enable uniform bucket-level access and public access prevention, and hand out signed URLs with short lifetimes.
- If an API must not leave a trust boundary, add VPC Service Controls (dry run first). IAM alone does not prevent a credentialed insider from copying data to an outside project.
- If usage is steady for 1 or 3 years, buy commitments (resource-based or spend-based) only after reviewing the CUD analysis report; keep burst and experimental workloads outside commitments.

## 5. Coding Standards

- Pass `--project`, `--region` (or `--location`) and `--quiet` only where intended; do not rely on `gcloud config set` inside scripts.
- Reference service accounts by full email and projects by ID in scripts; use the project number only for principal identifiers and read it with `gcloud projects describe PROJECT_ID --format='value(projectNumber)'`.
- Use `--format=json` or `--format='value(...)'` for scripting and `--filter` for server-side selection; never parse the default table output.
- Quote shell variables and keep IAM conditions in a file (`--condition-from-file`) when they contain commas or quotes.
- Give resources a naming scheme with environment and workload (`orders-api-prod`) and apply labels (`env`, `team`, `cost-center`) at creation.
- Grant roles with `add-iam-policy-binding` (additive), not `set-iam-policy` (replaces the whole policy), unless the task is a full policy rewrite from reviewed source.
- Pin GitHub Actions to a major version tag at minimum (`google-github-actions/auth@v3`) and consider a full commit SHA for supply-chain-sensitive repositories.
- Never place `${{ inputs.* }}`, `${{ github.event.* }}` or other untrusted expressions directly in `run:`; pass them through `env:` and reference the shell variable.
- Secrets live in Secret Manager and are referenced by name and version; never in source, build args or plain environment values.

## 6. Project Structure

```text
org/
├── folder: platform/            # shared networking, logging, security projects
│   ├── net-host-prod            # Shared VPC host project
│   └── sec-logging              # log sinks, audit exports
├── folder: workloads-prod/
│   └── orders-prod              # one project per workload and environment
├── folder: workloads-nonprod/
│   ├── orders-staging
│   └── orders-dev
└── folder: sandbox/             # budget-capped experiments, short TTL
```

- Attach org policies and deny policies at folder level so environments inherit them.
- Keep the billing account separate from project ownership; link projects with `gcloud billing projects link PROJECT_ID --billing-account=ACCOUNT_ID`.
- Keep deployment identities in the project they deploy to, and let a central project own only what is truly shared.

## 7. Design Patterns

- **Environment per project**: isolates IAM, quotas and billing; cost is more projects to manage, mitigated by folders and automation.
- **Shared VPC**: a host project owns the network, service projects attach to subnets; central network control with delegated workload ownership, at the cost of cross-project IAM (`roles/compute.networkUser` on subnets).
- **Keyless CI deploy**: GitHub OIDC token exchanged through a Workload Identity pool, impersonating a deploy-only service account scoped to one repository and branch.
- **Runtime identity per service**: each Cloud Run service or GKE Kubernetes service account gets its own identity with only the roles it uses; avoids the default Compute Engine service account.
- **Private-by-default data plane**: Cloud SQL on private IP, Cloud Run with Direct VPC egress, Google API access through Private Google Access or a Private Service Connect endpoint, no external IPs, Cloud NAT only where internet egress is needed.
- **Fan-out with dead-lettering**: one topic, many subscriptions, each with its own dead-letter topic and alert on dead-letter backlog.
- **Signed URL upload**: the API issues a short-lived V4 signed URL scoped to one object; clients upload directly to Cloud Storage and the API never proxies the bytes.
- **Guardrails then delegation**: org policies and VPC Service Controls set the outer limits, IAM conditions narrow what each team can do inside them.

## 8. Best Practices

- Use groups for human access and bind roles to groups, not individuals, so offboarding is a directory change.
- Use IAM Recommender and policy insights to remove unused permissions, and review `roles/owner` holders regularly.
- Enable only the APIs a project needs (`gcloud services enable ...`) and disable unused ones to shrink attack surface.
- Turn on Admin Activity audit logs (always on) and Data Access audit logs for sensitive services, routed to a locked-down logging project.
- Use `--impersonate-service-account` for administrative scripts so humans act through audited, scoped identities instead of broad personal roles.
- Set Cloud Run `--max-instances` to protect downstream databases and to cap runaway cost.
- Make Pub/Sub handlers idempotent and ack after the work is durable; extend the ack deadline for slow work rather than acking early.
- Use object versioning or soft delete plus lifecycle rules for buckets that matter, and retention policies when regulation requires immutability.
- Set deletion protection on Cloud SQL (`--deletion-protection`) and enable backups and point-in-time recovery for production.
- Tag cost with labels and enable billing export on day one; export cannot be backfilled for the period before it was enabled.

## 9. Performance

- Measure first: Cloud Run request latency, instance count and container startup time; GKE Pod scheduling and node utilisation; Cloud SQL connections and CPU; Pub/Sub oldest unacked message age.
- Cloud Run: raise `--concurrency` only for code that is safe under concurrent requests; set `--cpu-boost` (`--[no-]cpu-boost`) for faster startup of heavy runtimes; use `--min-instances` for latency-critical paths.
- Cloud SQL: pool connections in the app (or use managed connection pooling where offered) because each Cloud Run instance holds its own pool; size pools against `max_connections` multiplied by `--max-instances`.
- Pub/Sub: scale subscriber instances by backlog age, tune flow control (outstanding messages and bytes) in the client library, and keep processing time inside the ack deadline.
- Cloud Storage: spread heavy write rates across object name prefixes only if you see throttling; choose bucket location close to compute and use dual-region or multi-region only when availability needs justify the price.
- Networking: keep chatty services in the same region and zone group, use Private Google Access to avoid NAT bandwidth charges for Google APIs, and size Cloud NAT ports (`--min-ports-per-vm`) when you see allocation errors.

## 10. Security

- No service account key files. Enforce `constraints/iam.disableServiceAccountKeyCreation` and `constraints/iam.disableServiceAccountKeyUpload` at the organization or a top folder; exceptions go to a tagged folder or project with an expiry.
- Add an attribute condition to every Workload Identity provider, for example `assertion.repository == 'OWNER/REPO'` or an `assertion.repository_owner` check. Without it, any repository on GitHub that can mint a token for the issuer can reach the pool.
- Bind `roles/iam.workloadIdentityUser` to a `principalSet` scoped by `attribute.repository`, not to the whole pool. Add a branch or environment check (`assertion.ref` or `assertion.environment`) for production deploy identities.
- Least privilege: use predefined roles on the specific resource (for example `roles/run.invoker` on one Cloud Run service) rather than project-wide roles. Never grant `roles/owner` or `roles/editor` to workloads.
- Grant `roles/iam.serviceAccountUser` and `roles/iam.serviceAccountTokenCreator` sparingly; they allow acting as the service account and are common privilege-escalation paths.
- Do not use the default Compute Engine service account for workloads. Enforce `constraints/iam.automaticIamGrantsForDefaultServiceAccounts` so default accounts do not receive Editor.
- Cloud Run: require authentication (`--no-allow-unauthenticated`) unless the service is intentionally public; mount secrets with `--set-secrets` from Secret Manager and grant `roles/secretmanager.secretAccessor` on those secrets only.
- GKE: use private nodes, restrict control plane access with authorized networks or DNS-based access, enable Workload Identity Federation for GKE, and keep Shielded nodes on.
- Cloud SQL: disable public IP where possible (`--no-assign-ip`), require TLS (`--ssl-mode=ENCRYPTED_ONLY` or stricter), prefer IAM database authentication, and enable deletion protection.
- Cloud Storage: enforce `constraints/storage.uniformBucketLevelAccess` and `constraints/storage.publicAccessPrevention`; sign URLs by impersonation and keep lifetimes short.
- Pub/Sub push subscriptions should authenticate with an OIDC token (`--push-auth-service-account`) and the receiver must verify audience and issuer.
- Use VPC Service Controls for data exfiltration risk and test in dry-run first; perimeter changes can break legitimate cross-project flows.
- Details: [references/iam-workload-identity.md](references/iam-workload-identity.md).

## 11. Testing

- Validate commands without side effects: `gcloud ... describe`, `--dry-run` where a command offers it, and `gcloud help <command>` to confirm flags in the installed version.
- IAM: `gcloud iam service-accounts get-iam-policy`, `gcloud projects get-iam-policy`, and the Policy Troubleshooter (`gcloud policy-troubleshoot iam`) to explain why a call is allowed or denied. Test with the real identity via `--impersonate-service-account`.
- Federation: run the workflow on a branch and on a disallowed repository or branch to confirm the attribute condition rejects the latter.
- Cloud Run: deploy a no-traffic revision (`--no-traffic --tag=candidate`), smoke test its tagged URL, then shift traffic with `gcloud run services update-traffic`.
- Pub/Sub: test redelivery by letting an ack deadline expire, test dead-lettering by forcing failures past `--max-delivery-attempts`, and use the Pub/Sub emulator (see the current emulator documentation) for local unit tests.
- Networking: test reachability from the actual workload (a Cloud Run job or a debug Pod), and run VPC Service Controls in dry-run, reading violations in audit logs before enforcing.
- Cost guardrails: confirm a budget notification reaches the intended Pub/Sub topic or channel with a low test threshold.

## 12. Review Checklist

- [ ] Command names and flags match the installed gcloud version (`gcloud version`, `gcloud help`).
- [ ] No service account key files; key creation and upload constraints are enforced or the exception is documented.
- [ ] Every Workload Identity provider has an attribute condition, and bindings use `principalSet` scoped to a repository.
- [ ] Each workload has its own service account with narrow predefined roles bound on the narrowest resource.
- [ ] No basic roles (`owner`, `editor`) granted to workloads or broad groups.
- [ ] Workflows give `id-token: write` only where needed, and no `${{ inputs.* }}` or event data inside `run:`.
- [ ] Cloud Run ingress, authentication, `--max-instances` and secret references are explicit.
- [ ] GKE uses a release channel, private nodes and Workload Identity Federation for GKE.
- [ ] Cloud SQL uses private connectivity or the Auth Proxy, TLS enforced, deletion protection and backups on.
- [ ] Pub/Sub subscriptions set ack deadline, dead-letter topic, retry policy and idempotent handlers.
- [ ] Buckets use uniform access and public access prevention; lifecycle rules match retention needs.
- [ ] VPC is custom mode, no default network, no external IPs without a reason, firewall rules are least-open.
- [ ] Budgets with alerts, labels, and billing export are in place for each project.

## 13. Production Notes

- Roll out Cloud Run changes as tagged no-traffic revisions, shift traffic gradually, and roll back by routing traffic to the previous revision.
- Plan for GKE upgrades: define maintenance windows and exclusions, watch deprecated API usage before minor upgrades, and keep a surge or disruption budget for stateful workloads.
- Budgets notify but do not cap. For hard limits, drive automation from the budget Pub/Sub topic (for example disabling billing on a sandbox project) and test it carefully, since disabling billing stops resources.
- Quotas are per project and region; request increases before launches. Check the Quotas page and the current quota CLI documentation, since quota tooling lives in separate components.
- Organization policy changes propagate with delay and can block running pipelines; roll them out with dry-run policies where available and communicate exceptions.
- Cloud SQL maintenance windows and failover cause connection drops; make clients retry with backoff and keep pool lifetimes short.
- Pub/Sub dead-letter forwarding needs the Pub/Sub service agent to hold publisher rights on the dead-letter topic and subscriber rights on the source subscription; without them messages are not forwarded.
- Billing export tables only contain data from the day export was enabled; enable at account creation. Spend-based commitment models are changing from a credit model to a discount model, so check which applies to the billing account before writing cost queries.
- Keep a break-glass admin path documented and tested, separate from daily automation identities.

## 14. Examples

Keyless GitHub Actions access: pool, provider locked to one repository, and a deploy service account that only that repository can impersonate. Values come from shell variables.

```bash
PROJECT_ID="orders-prod"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
REPO="my-org/orders-api"
SA="orders-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create orders-deployer --project="$PROJECT_ID" \
  --display-name="Orders API deployer"

gcloud iam workload-identity-pools create github --project="$PROJECT_ID" \
  --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc orders-repo \
  --project="$PROJECT_ID" --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == '${REPO}'"

gcloud iam service-accounts add-iam-policy-binding "$SA" --project="$PROJECT_ID" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}"

# Deploy permissions on the narrowest scope that works (add roles/run.admin only if the job must manage the service).
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA}" --role=roles/run.developer
```

The workflow that uses it. Values are repository variables, and nothing from `inputs` or the event reaches a `run:` line.

```yaml
name: deploy
on:
  push:
    branches: [main]
permissions:
  contents: read
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}
      REGION: ${{ vars.GCP_REGION }}
      IMAGE: ${{ vars.ORDERS_IMAGE }}
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
          service_account: ${{ vars.GCP_DEPLOY_SA }}
      - uses: google-github-actions/setup-gcloud@v3
      - name: Deploy
        run: |
          gcloud run deploy orders-api \
            --project="$PROJECT_ID" --region="$REGION" --image="$IMAGE" \
            --service-account="orders-api@${PROJECT_ID}.iam.gserviceaccount.com" \
            --no-allow-unauthenticated --ingress=internal-and-cloud-load-balancing \
            --min-instances=1 --max-instances=20 --concurrency=80 \
            --set-secrets="DB_PASSWORD=orders-db-password:latest"
```

Pub/Sub subscription with ack deadline, dead-lettering, exactly-once delivery and the permissions dead-lettering needs:

```bash
PROJECT_ID="orders-prod"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
PUBSUB_AGENT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

gcloud pubsub topics create orders --project="$PROJECT_ID"
gcloud pubsub topics create orders-dead-letter --project="$PROJECT_ID"
gcloud pubsub subscriptions create orders-worker --project="$PROJECT_ID" \
  --topic=orders --ack-deadline=60 \
  --enable-exactly-once-delivery \
  --dead-letter-topic=orders-dead-letter --max-delivery-attempts=5

gcloud pubsub topics add-iam-policy-binding orders-dead-letter --project="$PROJECT_ID" \
  --member="serviceAccount:${PUBSUB_AGENT}" --role=roles/pubsub.publisher
gcloud pubsub subscriptions add-iam-policy-binding orders-worker --project="$PROJECT_ID" \
  --member="serviceAccount:${PUBSUB_AGENT}" --role=roles/pubsub.subscriber
```

More examples (Cloud Run jobs, GKE federation, Cloud SQL, buckets, budgets, VPC) are in the reference files.

## 15. Common Mistakes

- **Downloading a service account key for CI**: the key is a long-lived bearer secret that leaks through logs and laptops. Use Workload Identity Federation and enforce the key-creation constraint.
- **Workload Identity provider without an attribute condition**: any identity the issuer vouches for may enter the pool. Always set `--attribute-condition`, and scope bindings by repository.
- **Binding `workloadIdentityUser` to the whole pool**: every repository in the pool can impersonate the account. Use `principalSet` with `attribute.repository/OWNER/REPO`.
- **`${{ inputs.name }}` or `${{ github.head_ref }}` inside `run:`**: shell injection through attacker-controlled values. Pass through `env:` and quote the variable.
- **Using `roles/editor` for convenience**: grants hundreds of permissions and lets workloads change IAM-adjacent resources. Choose a predefined role on the specific resource.
- **Running workloads as the default Compute Engine service account**: broad, shared identity. Create a dedicated account per workload.
- **`gcloud ... set-iam-policy` for a small change**: replaces the entire policy and can lock people out. Use `add-iam-policy-binding` and `remove-iam-policy-binding`.
- **Cloud Run `--allow-unauthenticated` plus `--ingress=all` by default**: the service is public to the internet. Decide both settings deliberately.
- **Relying on a budget to stop spend**: budgets only notify. Add quotas, `--max-instances`, and automation if a hard limit is required.
- **Assuming Pub/Sub is exactly-once**: default delivery is at least once, so handlers see duplicates. Make handlers idempotent; enable exactly-once only on pull subscriptions and keep consumers in one region.
- **No dead-letter permissions**: the dead-letter topic is configured but the Pub/Sub service agent lacks publisher rights, so failing messages loop forever. Grant the roles shown above.
- **Ack deadline shorter than processing time**: messages are redelivered while still being processed. Raise `--ack-deadline` or extend it from the client.
- **Cloud SQL authorized network `0.0.0.0/0`**: database exposed to the internet. Use private IP, the Auth Proxy or a connector.
- **Auto-mode default network left in place**: wide firewall rules and overlapping ranges. Use custom mode VPCs and skip default network creation with an org policy.
- **Enabling billing export late**: past usage cannot be backfilled. Enable it when the billing account is created.

## 16. References

- [references/iam-workload-identity.md](references/iam-workload-identity.md): hierarchy and org policy commands, custom roles, conditions, deny policies, Workload Identity Federation for CI and GKE, service account impersonation, key-free patterns.
- [references/cloud-run-gke.md](references/cloud-run-gke.md): Cloud Run services and jobs flags, scaling, secrets, VPC egress, traffic splitting, GKE Autopilot and Standard creation, release channels, Workload Identity Federation for GKE.
- [references/data-services.md](references/data-services.md): Cloud SQL connectivity and IAM authentication, Pub/Sub delivery semantics and commands, Cloud Storage security, lifecycle and signed URLs.
- [references/networking-cost.md](references/networking-cost.md): custom VPC, Private Google Access, Private Service Connect, Cloud NAT, firewall policies, VPC Service Controls, budgets, billing export, commitments, labels, quotas.
- Official docs: https://cloud.google.com/docs , https://cloud.google.com/sdk/gcloud/reference , https://cloud.google.com/iam/docs , https://cloud.google.com/run/docs , https://cloud.google.com/kubernetes-engine/docs , https://cloud.google.com/pubsub/docs , https://cloud.google.com/sql/docs , https://cloud.google.com/storage/docs , https://cloud.google.com/vpc/docs , https://cloud.google.com/billing/docs , https://github.com/google-github-actions/auth
