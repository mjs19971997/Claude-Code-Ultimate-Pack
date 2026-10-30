# Identity and RBAC on Azure

Reference for Microsoft Entra ID identities, federation from GitHub Actions and AKS, Azure RBAC and Key Vault access. Commands were checked against Azure CLI 2.91.0 help output; the `azure/login` guidance reflects the action's v3 README (2026-10).

## Contents

1. [Identity objects](#1-identity-objects)
2. [Managed identities](#2-managed-identities)
3. [GitHub Actions with OIDC](#3-github-actions-with-oidc)
4. [AKS workload identity](#4-aks-workload-identity)
5. [Azure RBAC](#5-azure-rbac)
6. [Key Vault access](#6-key-vault-access)
7. [Troubleshooting](#7-troubleshooting)

## 1. Identity objects

| Object | What it is | Typical use |
|---|---|---|
| Application (app registration) | Global definition: client ID, redirect URIs, API permissions, federated credentials | Sign-in for your own app, deployment identity with federation |
| Service principal | Local instance of an application in one tenant; this is what receives role assignments | Target of `az role assignment create` |
| System-assigned managed identity | Service principal created and deleted with one Azure resource | Single app reading one vault or database |
| User-assigned managed identity | Standalone Azure resource with its own lifecycle, attachable to many resources | Shared identity, pre-granted access, GitHub or AKS federation |
| User, group | Human principals | Assign roles to groups, not people |

- Role assignments target a principal's object ID. The client ID (application ID) is what an application presents; do not confuse the two when scripting `--assignee-object-id`.
- `az ad sp create-for-rbac` creates an app, a service principal and a role assignment at once. Its `--sdk-auth` output is deprecated. Prefer a federated credential and keep client secrets for the rare case where federation is impossible.

## 2. Managed identities

```bash
# System-assigned on an existing web app, with a role and scope in one step
az webapp identity assign -g rg-shop -n app-shop --identities '[system]' \
  --role "Storage Blob Data Reader" \
  --scope "$(az storage account show -g rg-shop -n stshopdata --query id -o tsv)"

# User-assigned identity attached to a web app
az identity create -g rg-shop -n id-shop-app
ID=$(az identity show -g rg-shop -n id-shop-app --query id -o tsv)
az webapp identity assign -g rg-shop -n app-shop --identities "$ID"
```

- A system-assigned identity cannot receive roles before its host exists. Infrastructure that must grant access in the same deployment should use a user-assigned identity so the role assignment can be created first.
- Delete a resource and its system-assigned identity goes with it, leaving orphaned role assignments that show as "Identity not found". Clean them with `az role assignment list --all` and delete stale entries.
- On a VM or other host with an identity, `az login --identity` (add `--client-id` or `--resource-id` for user-assigned) signs the CLI in with the host identity.
- Managed identity tokens come from the platform endpoint; application code should use an SDK credential (for example `DefaultAzureCredential` in the SDKs) instead of calling it by hand. SDK usage details belong to the language skill.

## 3. GitHub Actions with OIDC

Steps to set up keyless deployment:

1. Create a user-assigned identity (or an app registration) per environment.
2. Add a federated credential with issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange` and a subject that matches how the workflow runs.
3. Assign a role to the identity at the narrowest scope.
4. Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` as repository or environment variables or secrets. They are identifiers, not credentials, but `azure/login` masks the client ID by default (`mask-client-id: false` opts out).

Subject formats GitHub emits:

| Trigger | Subject |
|---|---|
| Job using a GitHub environment | `repo:<org>/<repo>:environment:<name>` |
| Branch push | `repo:<org>/<repo>:ref:refs/heads/<branch>` |
| Tag push | `repo:<org>/<repo>:ref:refs/tags/<tag>` |
| Pull request | `repo:<org>/<repo>:pull_request` |

Prefer the environment subject for production: environment protection rules (required reviewers, branch restrictions) then gate who can obtain a token. Each exact subject needs its own federated credential; an identity supports a limited number of them, so check the current limit in the docs. The CLI also exposes a preview flexible form through `--claims-matching-expression-value`; check the docs before depending on it.

```bash
az identity federated-credential create -g rg-shop-prod --identity-name id-deploy-prod \
  --name github-production \
  --issuer https://token.actions.githubusercontent.com \
  --subject "repo:my-org/shop:environment:production" \
  --audiences api://AzureADTokenExchange
```

For an app registration use `az ad app federated-credential create --id <app-id> --parameters @credential.json`, where the JSON holds `name`, `issuer`, `subject` and `audiences`.

Workflow rules for `azure/login`:

- Pin the major tag (`azure/login@v3`), an exact tag, or a full commit SHA with a version comment. v3 is supported, v2 gets security fixes only, v1 is end of life, and branch references are not supported.
- Grant `permissions: id-token: write` (workflow or job) and `contents: read`. Without `id-token: write` the OIDC token request fails.
- Pass only `secrets.*` or `vars.*` into `client-id`, `tenant-id`, `subscription-id` and `creds`. Values from `github.event.*`, `workflow_dispatch` inputs or branch names can steer which identity is used.
- Do not interpolate inputs or event fields into `run:`; hand them over as `env:` entries and reference the shell variable in quotes.
- After login, plain `az` commands in later steps reuse the session. Add `enable-AzPSSession: true` only if the job runs Azure PowerShell.
- Avoid managed identity login on self-hosted runners in public repositories, since any pull request can reach the runner.

## 4. AKS workload identity

Workload identity lets a pod exchange its Kubernetes service account token for a Microsoft Entra token without a secret.

```bash
# Enable on a new cluster (use az aks update to enable on an existing one)
az aks create -g rg-aks -n aks-shop --enable-oidc-issuer --enable-workload-identity \
  --network-plugin azure --network-plugin-mode overlay

ISSUER=$(az aks show -g rg-aks -n aks-shop --query "oidcIssuerProfile.issuerUrl" -o tsv)

az identity create -g rg-aks -n id-shop-pod
az identity federated-credential create -g rg-aks --identity-name id-shop-pod \
  --name shop-api \
  --issuer "$ISSUER" \
  --subject system:serviceaccount:shop:shop-api \
  --audiences api://AzureADTokenExchange
```

The Kubernetes side (kubernetes-expert owns manifest design): a `ServiceAccount` named `shop-api` in namespace `shop` annotated with `azure.workload.identity/client-id: <client id of id-shop-pod>`, and pods labelled `azure.workload.identity/use: "true"`.

- The subject must match `system:serviceaccount:<namespace>:<service-account>` exactly.
- A federated credential takes seconds to propagate; the first token request after creating it can fail.
- Identity bindings (`az aks identity-binding create`) are a newer way to have AKS create the credential for you. Check the current docs for status and limits before using them.
- For Key Vault secrets in pods, the Secrets Store CSI driver can use workload identity; grant the identity Key Vault Secrets User on the vault.

## 5. Azure RBAC

```bash
# Find a role definition (name, ID, actions) by display name
az role definition list --name "Key Vault Secrets User" --query "[0].{id:name,actions:permissions[0].dataActions}" -o json

# Assign to a managed identity at resource scope
KV_ID=$(az keyvault show -n kv-shop-prod --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$KV_ID"

# Audit
az role assignment list --scope "$KV_ID" -o table
az role assignment list --assignee "$PRINCIPAL_ID" --all -o table
```

- Scopes: `/providers/Microsoft.Management/managementGroups/<id>`, `/subscriptions/<id>`, `/subscriptions/<id>/resourceGroups/<rg>`, or a resource ID. Assignments inherit downward.
- Control plane vs data plane: Owner, Contributor and Reader act on management operations (`actions`). Reading secrets, blobs or messages needs `dataActions` roles. A subscription Owner has no automatic data access to a Key Vault using RBAC (they can grant it to themselves).
- Common built-in roles worth knowing: Reader, Contributor, Owner, User Access Administrator, Role Based Access Control Administrator (can assign roles with optional conditions), Key Vault Secrets User/Officer, Key Vault Crypto User, Key Vault Certificates Officer, Storage Blob Data Reader/Contributor/Owner, Storage Queue Data Contributor, AcrPull, AcrPush, Azure Service Bus Data Sender/Receiver, Monitoring Reader.
- Roles that can assign roles (Owner, User Access Administrator, Role Based Access Control Administrator) are the highest-risk grants. Use `--condition` (preview in the CLI) to limit which roles a deployment identity may assign.
- Custom roles are JSON with `Actions`, `NotActions`, `DataActions`, `NotDataActions` and `AssignableScopes`; create with `az role definition create --role-definition @role.json`. Prefer built-ins unless a documented gap exists.
- Deny assignments (created, for example, by deployment stack deny settings) override role assignments.
- Propagation can take several minutes; scripts that assign and immediately use a role should retry.

## 6. Key Vault access

```bash
az keyvault create -g rg-shop-prod -n kv-shop-prod -l westeurope \
  --enable-rbac-authorization true \
  --enable-purge-protection true \
  --retention-days 90 \
  --public-network-access Disabled

az keyvault secret set --vault-name kv-shop-prod -n db-connection --file ./secret.txt
```

- Vaults created with API version 2026-02-01 or later default to Azure RBAC when `enableRbacAuthorization` is omitted; older vaults keep the access policy model until you switch. Set the property explicitly in templates so behaviour does not depend on the API version.
- With RBAC enabled, access policies on the vault are ignored. Migrate by mapping each policy to the narrowest data-plane role (Secrets User for get/list, Secrets Officer for set/delete, Crypto User for key operations) and test before switching the model.
- Soft delete cannot be disabled; retention is 7 to 90 days. Purge protection is opt-in and irreversible; use it for production vaults.
- Setting `--public-network-access Disabled` blocks portal and CLI access from outside the VNet; plan operator access through private endpoints, a jump host or Bastion. Alternatively keep it enabled with `--default-action Deny` and an allowlist of IP ranges.
- Set secrets from a file or stdin, not on the command line, so values stay out of shell history and process lists.
- App Service references: `@Microsoft.KeyVault(SecretUri=https://kv-shop-prod.vault.azure.net/secrets/db-connection)`. Omit the version to follow the latest. The app's identity needs Key Vault Secrets User; a user-assigned identity must also be selected with `keyVaultReferenceIdentity`. An unresolved reference shows up as the literal reference string in the app's environment.
- Container Apps secrets can point to Key Vault with a managed identity; see the compute reference.

## 7. Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| `AADSTS700213` or `AADSTS7002138` on OIDC login | No federated credential matches the token's subject | Compare the credential's subject with the job's trigger (environment, branch, pull request) |
| `Not all values are present. Ensure 'client-id' and 'tenant-id' ...` | Missing inputs or missing `id-token: write` | Workflow `permissions`, variable names |
| 403 reading a Key Vault secret | Control-plane role only, or role not yet propagated | `az role assignment list --scope <vault>`, wait and retry |
| `ForbiddenByRbac` or `ForbiddenByFirewall` | RBAC missing, or network rule blocking the caller | Role at vault scope; vault network settings and private DNS |
| Key Vault reference shows as literal text | Identity lacks role, wrong identity selected, vault unreachable from app | `keyVaultReferenceIdentity`, VNet integration and DNS |
| "Principal does not exist in the directory" during role assignment | Newly created identity not replicated | Use `--assignee-object-id` with `--assignee-principal-type`, retry |
| Pod gets no token on AKS | Wrong subject, missing label or annotation, issuer mismatch | Subject string, `azure.workload.identity/use`, `oidcIssuerProfile.issuerUrl` |
