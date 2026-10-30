# IAM, Org Policy and Workload Identity Federation

Commands and patterns for structuring access on Google Cloud: hierarchy, org policies, roles, conditions, deny policies, service accounts, and keyless authentication for GitHub Actions and GKE. Command names and flags were checked against Google Cloud CLI 570.0.0 and google-github-actions/auth v3 (2026-10).

## Contents

1. [Hierarchy and project setup](#1-hierarchy-and-project-setup)
2. [Organization policies](#2-organization-policies)
3. [Roles and bindings](#3-roles-and-bindings)
4. [IAM conditions](#4-iam-conditions)
5. [Deny policies](#5-deny-policies)
6. [Service accounts and impersonation](#6-service-accounts-and-impersonation)
7. [Workload Identity Federation for GitHub Actions](#7-workload-identity-federation-for-github-actions)
8. [Workload Identity Federation for GKE](#8-workload-identity-federation-for-gke)
9. [Auditing access](#9-auditing-access)

## 1. Hierarchy and project setup

```bash
# Folders and projects (IDs are examples)
gcloud resource-manager folders create --display-name="workloads-prod" --organization=ORG_ID
gcloud projects create orders-prod --folder=FOLDER_ID --name="Orders prod" \
  --labels=env=prod,team=orders,cost-center=cc-1234
gcloud billing projects link orders-prod --billing-account=BILLING_ACCOUNT_ID
gcloud services enable run.googleapis.com secretmanager.googleapis.com --project=orders-prod
```

- Policies inherit downward, so grant at the lowest level that covers the need.
- One project per environment and workload boundary gives separate quotas, IAM and billing views. Labels (`env`, `team`, `cost-center`) on projects feed billing reports.
- The project number (not the ID) appears in principal identifiers and service agent addresses: `gcloud projects describe PROJECT_ID --format='value(projectNumber)'`.

## 2. Organization policies

Org policies constrain what can be configured. Set a boolean constraint from a file:

```yaml
# no-sa-keys.yaml
name: organizations/ORG_ID/policies/iam.disableServiceAccountKeyCreation
spec:
  rules:
    - enforce: true
```

```bash
gcloud org-policies set-policy no-sa-keys.yaml
gcloud org-policies list --organization=ORG_ID
gcloud org-policies describe iam.disableServiceAccountKeyCreation --organization=ORG_ID --effective
```

Constraint names confirmed in the installed gcloud tooling:

| Constraint | Effect |
|---|---|
| `constraints/iam.disableServiceAccountKeyCreation` | Blocks creation of persistent service account keys |
| `constraints/iam.disableServiceAccountKeyUpload` | Blocks uploading externally generated public keys |
| `constraints/iam.serviceAccountKeyExpiryHours` | Caps lifetime of keys where they must exist |
| `constraints/iam.automaticIamGrantsForDefaultServiceAccounts` | Stops default service accounts from getting Editor at creation |
| `constraints/iam.disableServiceAccountCreation` | Blocks creating service accounts (use for locked-down projects) |
| `constraints/iam.allowedPolicyMemberDomains` | Restricts which identity domains may appear in IAM policies |
| `constraints/storage.uniformBucketLevelAccess` | Requires uniform bucket-level access |
| `constraints/storage.publicAccessPrevention` | Blocks public buckets and objects |
| `constraints/sql.restrictPublicIp` | Blocks public IPs on Cloud SQL |
| `constraints/compute.skipDefaultNetworkCreation` | New projects get no default network |
| `constraints/compute.vmExternalIpAccess` | Controls which VMs may have external IPs |
| `constraints/gcp.resourceLocations` | Restricts where resources can be created |

- New organizations created from May 2024 onward receive a security baseline that already enforces the key constraints; older organizations should set them explicitly. A managed form named `constraints/iam.managed.disableServiceAccountKeyCreation` is also listed in Google documentation, so confirm which name `gcloud org-policies list` shows for your organization before scripting.
- Grant exceptions by setting a policy on a specific project or by using tags with conditional rules, with a documented owner and review date.

## 3. Roles and bindings

```bash
# Additive grant on one Cloud Run service (not the project)
gcloud run services add-iam-policy-binding orders-api --region=us-central1 \
  --member="serviceAccount:web-frontend@orders-prod.iam.gserviceaccount.com" \
  --role=roles/run.invoker --project=orders-prod

# Remove a grant
gcloud projects remove-iam-policy-binding orders-prod \
  --member="user:former@example.com" --role=roles/viewer

# Find the smallest predefined role that holds a permission
gcloud iam list-testable-permissions //cloudresourcemanager.googleapis.com/projects/orders-prod \
  --filter="name:run.services.create" --format="value(name)"
gcloud iam roles describe roles/run.developer --format="value(includedPermissions)"
```

Custom role from a file:

```yaml
# deploy-role.yaml
title: Orders Deployer
description: Deploy Cloud Run revisions and read secrets metadata
stage: GA
includedPermissions:
  - run.services.get
  - run.services.update
  - run.revisions.get
  - run.revisions.list
```

```bash
gcloud iam roles create ordersDeployer --project=orders-prod --file=deploy-role.yaml
```

- Predefined roles are maintained by Google; custom roles must be updated by you, so use them only when no predefined role fits.
- Prefer `add-iam-policy-binding`; `set-iam-policy` replaces the whole policy and can remove access for everyone not in the file.
- Bind to groups for people and service accounts for workloads; avoid `allUsers` and `allAuthenticatedUsers`.

## 4. IAM conditions

```bash
gcloud projects add-iam-policy-binding orders-prod \
  --member="group:oncall@example.com" --role=roles/run.admin \
  --condition='title=expires-2026-12,description=Temporary on-call access,expression=request.time < timestamp("2026-12-31T00:00:00Z")'
```

- Expressions with commas need an alternate delimiter (`--condition=^:^title=...:expression=...`) or `--condition-from-file=condition.yaml`.
- Typical uses: time-boxed access, limiting a Storage role to an object prefix (`resource.name.startsWith("projects/_/buckets/uploads/objects/tenant-a/")` together with `resource.type == "storage.googleapis.com/Object"`), or limiting by resource tag.
- Not every role and resource type supports conditions. If a binding is rejected, check the product's IAM conditions documentation.

## 5. Deny policies

Deny rules override allow grants. Attach them at organization, folder or project level.

```json
{
  "displayName": "Block SA key creation except platform admins",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": ["principalSet://goog/public:all"],
        "exceptionPrincipals": ["principalSet://goog/group/platform-admins@example.com"],
        "deniedPermissions": ["iam.googleapis.com/serviceAccountKeys.create"]
      }
    }
  ]
}
```

```bash
gcloud iam policies create block-sa-keys \
  --attachment-point=cloudresourcemanager.googleapis.com/projects/PROJECT_ID \
  --kind=denypolicies --policy-file=deny.json
gcloud iam policies list --attachment-point=cloudresourcemanager.googleapis.com/projects/PROJECT_ID --kind=denypolicies
```

- The `--kind=denypolicies` form is confirmed in the CLI. The principal syntax and the list of permissions that support deny come from the IAM deny documentation; check it before relying on a specific permission or principal format, because not all permissions can be denied.

## 6. Service accounts and impersonation

```bash
gcloud iam service-accounts create orders-api --project=orders-prod \
  --display-name="Orders API runtime"

# Let an operator impersonate it for administration (short-lived tokens, audited)
gcloud iam service-accounts add-iam-policy-binding \
  orders-api@orders-prod.iam.gserviceaccount.com \
  --member="group:orders-admins@example.com" \
  --role=roles/iam.serviceAccountTokenCreator

gcloud run services list --project=orders-prod \
  --impersonate-service-account=orders-api@orders-prod.iam.gserviceaccount.com
```

- `roles/iam.serviceAccountUser` lets a principal attach the account to resources (for example deploy a Cloud Run service that runs as it); `roles/iam.serviceAccountTokenCreator` lets a principal mint tokens as it. Both are privilege-escalation paths; grant on the single service account, never on the project.
- List and audit keys with `gcloud iam service-accounts keys list --iam-account=EMAIL`; delete user-managed keys with `keys delete`. Disable unused accounts with `gcloud iam service-accounts disable`.

## 7. Workload Identity Federation for GitHub Actions

Setup commands are in SKILL.md section 14. Details that matter:

- `--attribute-condition` is the gate for who may exchange a token at all. Google's guidance for the auth action is to always set one. Examples: `assertion.repository_owner == 'my-org'` (all repositories of an organization) or `assertion.repository == 'my-org/orders-api'` (one repository).
- `--attribute-mapping` must map a claim before a condition or `principalSet` can use it. Useful mappings: `attribute.repository=assertion.repository`, `attribute.repository_owner=assertion.repository_owner`, `attribute.ref=assertion.ref`, `attribute.environment=assertion.environment`.
- To restrict production deploys to the main branch, combine conditions: `assertion.repository == 'my-org/orders-api' && assertion.ref == 'refs/heads/main'`.
- Two access models with the auth action:
  - Through a service account: pass `service_account`; grant `roles/iam.workloadIdentityUser` on that service account to the `principalSet`.
  - Direct: omit `service_account`; grant resource roles straight to the `principalSet://.../attribute.repository/OWNER/REPO` member. Check that each product you call supports federated principals before choosing this.
- Workflow requirements: `permissions: id-token: write` (plus `contents: read` for checkout). Pin `google-github-actions/auth@v3`. Pass values from `vars`/`secrets` into `with:` or `env:`; do not interpolate `${{ inputs.* }}` or event fields into `run:` scripts.
- Gate deploy jobs on protected branches or environments and bind the `ref` or `environment` claim in the provider condition.

Minimal read-only job (no service account, identity chosen by the pool):

```yaml
permissions:
  contents: read
  id-token: write
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
          project_id: ${{ vars.GCP_PROJECT_ID }}
      - uses: google-github-actions/setup-gcloud@v3
      - run: gcloud run services list --region="$REGION"
        env:
          REGION: ${{ vars.GCP_REGION }}
```

Other issuers (AWS, any OIDC or SAML provider) use the same pool and provider model; always add an attribute condition.

## 8. Workload Identity Federation for GKE

```bash
# Standard cluster: enable on create, or on an existing cluster
gcloud container clusters update orders-gke --location=us-central1 \
  --workload-pool=orders-prod.svc.id.goog
# Autopilot: always enabled, nothing to turn on.
```

Grant a Kubernetes service account access to Google Cloud resources directly:

```bash
PROJECT_ID="orders-prod"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud storage buckets add-iam-policy-binding gs://orders-prod-exports \
  --role=roles/storage.objectViewer \
  --member="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/orders/sa/orders-api"
```

- The Kubernetes service account `orders-api` in namespace `orders` needs no annotation for direct grants. The Pod must run on a node pool using the GKE metadata server (`--workload-metadata=GKE_METADATA`, the default when the workload pool is enabled).
- To impersonate a Google service account instead (for products that do not accept federated principals), bind `roles/iam.workloadIdentityUser` on the service account to the same `principal://` member and annotate the Kubernetes service account with `iam.gke.io/gcp-service-account`. Kubernetes manifests are covered by kubernetes-expert.
- The workload pool `PROJECT_ID.svc.id.goog` is shared by all clusters in a project, so a grant to `ns/orders/sa/orders-api` applies to every cluster in that project with that namespace and name. Use separate projects for hard isolation.
- Never mount a service account key into a Pod. Application client libraries pick up credentials through Application Default Credentials from the metadata server.

## 9. Auditing access

```bash
# Who has a role on this project
gcloud projects get-iam-policy orders-prod \
  --flatten="bindings[].members" --filter="bindings.role:roles/owner" \
  --format="value(bindings.members)"

# Why was a call allowed or denied
gcloud policy-troubleshoot iam //cloudresourcemanager.googleapis.com/projects/orders-prod \
  --principal-email=orders-api@orders-prod.iam.gserviceaccount.com \
  --permission=run.services.get

# Search IAM policies across the organization (Cloud Asset Inventory)
gcloud asset search-all-iam-policies --scope=organizations/ORG_ID \
  --query="policy:roles/owner" --format="table(resource,policy.bindings.members)"
```

- Use IAM Recommender (`gcloud recommender recommendations list`) to find unused permissions.
- Export audit logs to a dedicated logging project with restricted access, and alert on key creation, policy changes and impersonation (alert design: observability-expert).
