---
name: azure-expert
description: >-
  Designs and operates secure Azure workloads with Microsoft Entra ID identities, Azure RBAC, App Service, Container Apps, AKS, Azure SQL, Key Vault, private networking, Bicep and cost controls. Use when writing az CLI commands, .bicep or .bicepparam files, azure/login OIDC workflows, managed or workload identity setups, role assignments, private endpoints, Key Vault references, deployment slots, budgets or Azure Policy. Not for AWS (use aws-expert), GCP (use gcp-expert), Kubernetes manifests (use kubernetes-expert), Terraform (use terraform-expert), .NET code (use csharp-dotnet-expert), pipeline structure (use cicd-expert), or tracing design (use observability-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Azure Expert

This skill covers building and reviewing Azure infrastructure and its access model: identities and federation, role assignments, the main compute and data services, private networking, infrastructure as code with Bicep, and spend control. It prefers keyless authentication (managed identities, workload identity federation) and Azure RBAC over stored secrets and access keys. Application code, Kubernetes manifests, other clouds and pipeline design belong to the neighbouring skills named in section 1.

> Verified against Azure CLI 2.91.0 (command and flag names checked in the installed CLI help), Bicep 0.48.x (latest release tag v0.48.1), `azure/login` GitHub Action v3 (latest tag v3.1.0, Node 24 runtime) and Azure Key Vault Azure RBAC as the default access model for vaults created with API version 2026-02-01 or later (2026-10).

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

- Covered: Microsoft Entra ID app registrations, service principals and managed identities; federated credentials for GitHub Actions and AKS; Azure RBAC role assignments and scopes; App Service, Azure Container Apps, AKS (cluster, node pool and network choices); Azure SQL Database; Key Vault; VNets, NSGs, private endpoints and private DNS; Front Door and Application Gateway WAF; Bicep modules, parameter files, what-if and deployment stacks; budgets, tags and Azure Policy; `az` CLI usage.
- Not covered: AWS (aws-expert), GCP (gcp-expert), Kubernetes manifests, Helm and cluster workloads (kubernetes-expert), Terraform and the `azurerm` provider (terraform-expert), .NET application code and SDK usage (csharp-dotnet-expert), CI pipeline structure and caching (cicd-expert), metrics, logs and tracing design (observability-expert), container image builds (docker-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Identity objects | An app registration is the global definition of an application; a service principal is its instance in one tenant; a managed identity is a service principal whose credentials Azure manages and never exposes |
| Managed identity types | System-assigned: tied to one resource and deleted with it. User-assigned: separate resource, reusable across resources, survives redeployments, needed for pre-granted access or shared identity |
| Workload identity federation | A federated identity credential trusts tokens from an external issuer by `issuer`, `subject` and `audience` (`api://AzureADTokenExchange`); no secret is stored. GitHub issuer is `https://token.actions.githubusercontent.com` |
| `azure/login` | Pin the major tag `azure/login@v3` (v3 supported, v2 security fixes only, v1 end of life); needs `permissions: id-token: write`; inputs `client-id`, `tenant-id`, `subscription-id` come from `secrets.*` or `vars.*` only |
| Azure RBAC | Assignment = principal + role + scope. Scopes inherit downward: management group, subscription, resource group, resource. Control-plane roles (Contributor) do not grant data-plane access to Key Vault or Storage data |
| Data-plane roles | Key Vault Secrets User (read secrets), Key Vault Secrets Officer, Storage Blob Data Reader / Contributor, Azure Service Bus Data Receiver; look up IDs with `az role definition list --name "<role>"` |
| Key Vault | Azure RBAC is the default for vaults created with API 2026-02-01 or later; older vaults keep access policies until migrated. Soft delete is always on (retention 7-90 days); purge protection is opt-in (`--enable-purge-protection`) and cannot be turned off |
| App Service | Slots need Standard tier or higher; slot-sticky settings via `--slot-settings`; Key Vault reference form `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<name>)`; `keyVaultReferenceIdentity` selects a user-assigned identity |
| Container Apps | Revisions are immutable snapshots; `--revisions-mode single` or `multiple`; scale rules `http`, `tcp`, `azure-queue` and other KEDA scalers via `--scale-rule-type`; jobs have trigger types Schedule, Event, Manual. `az containerapp` comes from a CLI extension |
| AKS networking | `--network-plugin azure` with `--network-plugin-mode overlay` (Azure CNI Overlay); `--network-dataplane cilium` for Cilium; `--network-plugin azure` without a mode gives pods VNet-routable IPs; `kubenet` is still accepted by the CLI but check the current retirement notice before choosing it |
| AKS upgrades | `--auto-upgrade-channel` is one of `none`, `patch`, `stable`, `rapid`, `node-image` (legacy); node OS updates use `--node-os-upgrade-channel` (`NodeImage`, `None`, `SecurityPatch`, `Unmanaged`) |
| Azure SQL | `az sql server create --enable-ad-only-auth` with an external admin; serverless via `--compute-model Serverless --min-capacity --auto-pause-delay`; disable SQL logins entirely when Entra-only is on |
| Private endpoints | One private endpoint per service and sub-resource (`sqlServer`, `vault`, `blob`, `sites`); name resolution needs the matching `privatelink.*` private DNS zone linked to the VNet |
| Bicep | Current 0.48.x; `.bicepparam` files start with `using './main.bicep'`; `@secure()` for secret params and outputs never carry secrets; `what-if` previews changes; deployment stacks via `az stack`; public registry modules are Azure Verified Modules under `br/public:avm/...` |
| Cost controls | Budgets with alerts (`az consumption budget`), tags for cost allocation, Azure Policy to restrict SKUs and regions, reservations and savings plans for steady usage |

## 3. Workflow

1. Establish the tenant, subscription, region, environment tiers and compliance limits (data residency, private-only access). Run `az account show` to confirm which subscription a command will hit.
2. Inspect what exists before changing it: `az resource list -g <rg> -o table`, `az role assignment list --scope <scope> -o table`, or a Bicep `what-if`.
3. Choose the identity first: who or what calls the resource, which managed identity or federated credential it uses, and which data-plane role at which scope it needs.
4. Express the change as Bicep (or a reviewed `az` command for one-off operations). Parameterise environment differences in `.bicepparam` files, never in copies of the template.
5. Validate: `az bicep build`, `az bicep lint`, then `az deployment group what-if` against the target scope; read the diff for deletions and replacements.
6. Deploy with a least-privilege identity, preferably from a pipeline using OIDC federation. For long-lived environments consider a deployment stack so removed resources are cleaned up.
7. Verify behaviour with the identity the workload really uses (for example `az login --identity` on the host, or the app's own health check), not with an owner account.
8. Record the result: resources touched, role assignments added, DNS or firewall follow-ups, and cost impact.

## 4. Decision Rules

- If the workload runs on Azure, use a managed identity; if it runs outside Azure in GitHub Actions or Kubernetes, use a federated credential on a user-assigned identity or app registration. A client secret is the last resort because it expires and leaks.
- If several resources must share one identity or the identity must be granted access before the resource exists (for example Key Vault references during first deployment), use a user-assigned identity; otherwise system-assigned is simpler.
- If a role exists at data-plane level (Key Vault Secrets User, Storage Blob Data Reader), use it instead of Contributor or Owner; Contributor cannot manage role assignments and does not read secrets under RBAC.
- Assign roles at the narrowest scope that works: the resource first, the resource group when a stack of resources shares a lifecycle, the subscription only for platform automation.
- If the app is a stateless HTTP service or worker without Kubernetes needs, prefer Container Apps or App Service over AKS; choose AKS when you need Kubernetes APIs, custom operators or fine-grained node control.
- If new AKS clusters need pod networking without exhausting VNet addresses, use Azure CNI Overlay; choose VNet-routable pod IPs only when pods must be directly addressable from the VNet.
- If a PaaS service holds sensitive data, disable public network access and add a private endpoint plus private DNS zone; use service endpoints only when private endpoints are not available.
- If traffic is HTTP(S) from the internet, put Front Door (global) or Application Gateway (regional, inside a VNet) with WAF in front; use Azure Firewall for egress filtering and NAT Gateway for stable outbound IPs.
- If deployments must remove what the template no longer declares, use a deployment stack with an explicit `--action-on-unmanage`; otherwise incremental deployments leave orphans.
- If a team needs a quick spend guard, create a budget with email alerts at 50, 80 and 100 percent first, then add Policy restrictions.

## 5. Coding Standards

- Bicep: lower camelCase symbolic names, one module per concern, `@description()` on every parameter, `@allowed` or `@minLength` for constrained inputs, `@secure()` on secrets.
- Parameter files use `.bicepparam` with `using './main.bicep'`; do not keep per-environment copies of the template.
- Resource names come from a naming function or a prefix parameter plus `uniqueString(resourceGroup().id)` for globally unique names; never hard-code globally unique names.
- Pin resource API versions explicitly; enable the `use-recent-api-versions` linter rule in `bicepconfig.json` to be told when they age.
- Reference modules by version (`br/public:avm/res/...:<version>`); do not use floating references.
- `az` commands in scripts: always pass `--resource-group` or `--scope` explicitly, use `-o tsv --query` for values, and set `--only-show-errors` in CI logs.
- Tag every resource group and resource with at least `env`, `owner` and `cost-center` via a shared `tags` parameter.
- No secrets in parameters files, shell history or output blocks; Bicep outputs must not contain secrets (linter rule `outputs-should-not-contain-secrets`).

## 6. Project Structure

```text
infra/
├── main.bicep                  # entry point, subscription or resource group scope
├── main.dev.bicepparam         # using './main.bicep'
├── main.prod.bicepparam
├── bicepconfig.json            # linter rules, module aliases
├── modules/
│   ├── network.bicep
│   ├── identity.bicep          # user-assigned identities and role assignments
│   ├── keyvault.bicep
│   ├── app.bicep
│   └── data.bicep
└── scripts/
    └── whatif.sh               # wrapper around az deployment ... what-if
.github/workflows/
└── deploy.yml                  # azure/login@v3 with OIDC, what-if then deploy
```

## 7. Design Patterns

- **Identity module**: one module creates user-assigned identities and the role assignments they need, and exports only principal and client IDs. Cost: a role assignment must wait for the identity, so use `dependsOn` through symbolic references.
- **Hub-and-spoke network**: shared services (Firewall, DNS, Bastion) in a hub VNet, workloads in peered spokes. Cost: Firewall and peering charges, and routing tables to maintain.
- **Private link per service with central private DNS zones**: zones live in one subscription and are linked to every spoke. Cost: DNS link management; benefit: consistent name resolution.
- **Slot swap release**: deploy to a staging slot, warm it, swap, keep the old version in the staging slot for quick rollback. Cost: slots share the plan's compute.
- **Revision-based rollout (Container Apps)**: multiple revision mode with traffic weights for canary, then move 100 percent and deactivate the old revision.
- **Federated credentials per environment**: one identity per environment, subject bound to a GitHub environment, so production deployments require the environment's protection rules.
- **Deployment stack with deny settings**: protects platform resources from manual edits. Cost: operators need explicit exclusions for break-glass changes.

## 8. Best Practices

- Use Azure RBAC for Key Vault, Storage and Service Bus data access; keys and SAS tokens are not auditable per caller.
- Keep one resource group per application lifecycle so deleting or locking it is meaningful and scoped assignments stay small.
- Assign roles to groups or managed identities, not individual users, and give every assignment a `description`.
- Use `--assignee-object-id` with `--assignee-principal-type ServicePrincipal` in automation to avoid Graph lookups and replication delay errors.
- Make a role assignment name deterministic in Bicep with `guid(scope.id, principalId, roleDefinitionId)` so redeploys do not create duplicates.
- Use Key Vault references or SDK calls with a managed identity instead of copying secrets into app settings.
- Choose regions with availability zones for production, and pair that with zone-redundant SKUs only where the service offers them.
- Run `what-if` for every production deployment and review replacements of stateful resources.
- Enable diagnostic settings to a Log Analytics workspace for Key Vault, SQL, Firewall and WAF; design of dashboards and alerts belongs to observability-expert.

## 9. Performance

- Measure first: Azure Monitor metrics for CPU, memory, requests and queue length; Container Apps replica count; SQL DTU or vCore percentages; Front Door origin latency.
- Container Apps: tune `--min-replicas` (0 saves cost but adds cold start), concurrency for the http scale rule (default 10), and KEDA polling and cooldown for event scalers.
- App Service: scale up (plan tier) for per-instance limits and scale out for throughput; keep Always On enabled for non-Free tiers that need it and warm slots before a swap.
- AKS: separate system and user node pools, use the cluster autoscaler with sensible `--min-count` and `--max-count`, and use `--max-surge` on node pools to speed upgrades.
- Azure SQL serverless: pick `--min-capacity` and `--auto-pause-delay` for the idle pattern; resuming from pause adds seconds of latency, so keep production APIs on provisioned compute if that matters.
- Keep calls to dependent services inside the same region and use private endpoints in the same region as clients to avoid cross-region latency and egress charges.

## 10. Security

- Prefer no stored credentials: managed identity on Azure, federated credentials from GitHub Actions and AKS. `az ad sp create-for-rbac --sdk-auth` is deprecated.
- In GitHub workflows set `permissions: id-token: write` and `contents: read` at job level, pin `azure/login@v3`, and pass `client-id`, `tenant-id`, `subscription-id` only from `secrets.*` or `vars.*`. Never pass `github.event.*` or `${{ inputs.* }}` into `azure/login` or into a `run:` script; pass such values through `env:` and quote the shell variable.
- Scope the federated credential subject tightly (`repo:<org>/<repo>:environment:<env>` rather than a wildcard branch pattern) so a pull request from a fork cannot obtain a deploy token.
- Least privilege: separate identities for deploy (Contributor on one resource group, plus User Access Administrator only if the template creates role assignments, ideally with a condition) and for runtime (data-plane roles only).
- Key Vault: Azure RBAC model, purge protection on for production, `--public-network-access Disabled` with a private endpoint, no `Owner` or `Key Vault Administrator` for apps.
- Azure SQL: Entra-only authentication, no SQL logins, minimal TLS 1.2, public access disabled or firewalled, and database users created `FROM EXTERNAL PROVIDER` with only the database roles needed.
- Storage: disable shared key access and anonymous blob access where the workload allows it; use Blob Data roles.
- Network: NSG rules by service tag or application security group, no `*` inbound from the internet to management ports, WAF in prevention mode after a detection-mode baseline.
- Secure Bicep: `@secure()` on secrets, no secret defaults, no secrets in outputs; fetch secrets at deploy time from Key Vault references rather than passing them on the command line.
- Defender for Cloud recommendations and Azure Policy (deny effects for public storage, missing tags, disallowed regions) turn these rules into guardrails.

## 11. Testing

- `az bicep build --file main.bicep` and `az bicep lint --file main.bicep` in every pull request.
- `az deployment group what-if --resource-group <rg> --parameters main.dev.bicepparam` against a non-production scope; check for unexpected `Delete` or `Replace` changes.
- Deploy to a short-lived resource group per pull request when infrastructure is cheap, then delete it.
- Negative tests: confirm a denied path is denied (anonymous blob read returns 401 or 403, SQL login with a password fails on an Entra-only server, a public IP cannot reach a private-endpoint-only vault).
- Verify RBAC with `az role assignment list --assignee <principal-id> --all -o table` and test as the real identity.
- For Policy changes, assign in `DoNotEnforce` mode first (`--enforcement-mode DoNotEnforce`), review compliance, then enforce.

## 12. Review Checklist

- [ ] Versions and CLI flags match the "Verified against" line, or the docs were re-checked.
- [ ] Workloads authenticate with managed identity or federation; no client secrets, connection strings with keys or SAS tokens in code, settings or workflows.
- [ ] Role assignments use the narrowest scope and data-plane roles; no unexplained Owner or User Access Administrator.
- [ ] GitHub workflows pin `azure/login` to a major tag or commit, set `id-token: write` only where needed, and keep untrusted values out of `run:` scripts.
- [ ] Key Vault uses Azure RBAC, soft delete and purge protection, and denies public access in production.
- [ ] Data services have public access disabled or restricted, private endpoints and linked private DNS zones.
- [ ] Bicep has `@secure()` on secrets, no secret outputs, deterministic role assignment names, tags and a `.bicepparam` per environment.
- [ ] What-if output was reviewed and no stateful resource is replaced unintentionally.
- [ ] Budget, tags and Policy for allowed SKUs and regions exist for the subscription or resource group.
- [ ] Diagnostic settings and an owner for alerts exist for each production resource.

## 13. Production Notes

- Rollout: slots for App Service, revisions with traffic weights for Container Apps, node pool surge upgrades for AKS; always write the rollback step before deploying.
- AKS clusters on `none` still get platform-initiated upgrades once the Kubernetes version is out of support; plan upgrades inside the support window, and choose `patch` or `stable` with a maintenance window if you want predictable timing.
- Soft-deleted Key Vaults and purge protection keep names reserved; recreating a deleted vault with the same name needs a recover or purge (purge is blocked when protection is on).
- Private endpoint changes can break name resolution silently; check the private DNS zone has the A record and the VNet link before cutting over.
- Role assignments can take minutes to propagate; deployments that grant a role and immediately use it should retry or sequence the steps.
- Creating a federated credential can take a few seconds to propagate before the first token exchange succeeds.
- Newer features (for example AKS identity bindings, some Bicep experimental flags) change often; confirm status in the current docs before adopting them, and keep experimental Bicep features out of production templates.
- Quotas and SKU availability vary by region; check `az vm list-skus` or the portal quota page before committing to a SKU in a template.

## 14. Examples

A GitHub Actions job that logs in with OIDC federation and previews then deploys a Bicep file; untrusted values never reach `run:`.

```yaml
name: deploy-infra
on:
  push:
    branches: [main]
permissions:
  id-token: write
  contents: read
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v3
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: What-if
        env:
          RG: rg-shop-prod
        run: |
          az deployment group what-if --resource-group "$RG" \
            --parameters infra/main.prod.bicepparam
      - name: Deploy
        env:
          RG: rg-shop-prod
        run: |
          az deployment group create --resource-group "$RG" \
            --parameters infra/main.prod.bicepparam
```

Create the user-assigned identity and its federated credential for that GitHub environment, then grant it a role on one resource group only.

```bash
az identity create -g rg-shop-prod -n id-deploy-prod
az identity federated-credential create -g rg-shop-prod --identity-name id-deploy-prod \
  --name github-prod \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:my-org/shop:environment:production \
  --audiences api://AzureADTokenExchange
PRINCIPAL_ID=$(az identity show -g rg-shop-prod -n id-deploy-prod --query principalId -o tsv)
RG_ID=$(az group show -n rg-shop-prod --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal --role Contributor --scope "$RG_ID"
```

A Bicep module that gives an app identity read access to secrets in one vault, with a deterministic assignment name. The role definition ID is passed in, looked up with `az role definition list --name "Key Vault Secrets User" --query "[0].name" -o tsv`.

```bicep
@description('Name of the existing key vault in this resource group.')
param vaultName string

@description('Object (principal) ID of the identity that reads secrets.')
param principalId string

@description('GUID of the Key Vault Secrets User role definition.')
param secretsUserRoleId string

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName
}

resource secretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, principalId, secretsUserRoleId)
  scope: vault
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
    description: 'Runtime identity reads secrets'
  }
}
```

## 15. Common Mistakes

- **Contributor to read a secret**: under RBAC, Contributor does not grant data-plane access, so the app gets 403; assign Key Vault Secrets User at the vault.
- **Secrets in app settings or pipeline variables**: they leak through logs and exports; use Key Vault references or a managed identity.
- **Wildcard federated subject**: a broad subject lets any branch or fork workflow deploy; bind to a GitHub environment with approvals.
- **`${{ inputs.* }}` or `github.event.*` in `run:`**: script injection; pass through `env:` and quote.
- **Floating or missing action pins**: `azure/login@master` is unsupported; use `@v3`, an exact tag or a full commit SHA.
- **Private endpoint without private DNS**: clients resolve the public address and fail; create the `privatelink.*` zone, the zone group and the VNet link.
- **Assuming a system-assigned identity exists before the resource**: it cannot be granted access in advance; use a user-assigned identity.
- **Deploying Complete mode to a shared resource group**: deletes everything not in the template; use incremental or a deployment stack with reviewed unmanage actions.
- **No purge protection on production vaults**: a deleted vault or key can be purged permanently; enable it, remembering it cannot be disabled.
- **Entra-only SQL without a database user for the app**: login succeeds at the server and fails in the database; create the user `FROM EXTERNAL PROVIDER`.
- **Hard-coded globally unique names**: second deployment fails with a name conflict; derive names with `uniqueString`.
- **Scale-to-zero on latency-sensitive endpoints**: first request pays the cold start; set `--min-replicas 1` for those apps.

## 16. References

- [references/identity-rbac.md](references/identity-rbac.md): Entra objects, managed identities, GitHub OIDC federation, AKS workload identity, RBAC scopes and role lookup, Key Vault access.
- [references/compute-services.md](references/compute-services.md): App Service slots and settings, Container Apps revisions, scale rules and jobs, AKS cluster and node pool commands, Azure SQL setup.
- [references/bicep.md](references/bicep.md): Bicep file anatomy, modules, `.bicepparam`, secure parameters, what-if, deployment stacks, Azure Verified Modules, linter configuration.
- [references/networking-cost.md](references/networking-cost.md): VNet and NSG layout, private endpoints and private DNS, egress options, Front Door and Application Gateway WAF, budgets, tags and Azure Policy.
- Azure CLI reference: https://learn.microsoft.com/cli/azure/
- Bicep documentation: https://learn.microsoft.com/azure/azure-resource-manager/bicep/
- Bicep releases: https://github.com/Azure/bicep/releases
- Azure Login action: https://github.com/Azure/login
- Azure RBAC documentation: https://learn.microsoft.com/azure/role-based-access-control/
- Microsoft Entra workload identity federation: https://learn.microsoft.com/entra/workload-id/workload-identity-federation
- Key Vault Azure RBAC guide: https://learn.microsoft.com/azure/key-vault/general/rbac-guide
- AKS documentation: https://learn.microsoft.com/azure/aks/
- Azure Container Apps documentation: https://learn.microsoft.com/azure/container-apps/
- Azure Verified Modules: https://azure.github.io/Azure-Verified-Modules/
