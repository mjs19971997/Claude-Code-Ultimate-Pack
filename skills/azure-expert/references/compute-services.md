# Compute and Data Services

Reference for App Service, Azure Container Apps, AKS and Azure SQL Database. CLI flags were checked against Azure CLI 2.91.0 help (Container Apps commands come from the `containerapp` extension, installed with `az extension add -n containerapp`).

## Contents

1. [App Service](#1-app-service)
2. [Container Apps](#2-container-apps)
3. [AKS](#3-aks)
4. [Azure SQL Database](#4-azure-sql-database)
5. [Choosing a compute service](#5-choosing-a-compute-service)

## 1. App Service

```bash
az appservice plan create -g rg-shop -n plan-shop --sku P1V3 --is-linux
az webapp create -g rg-shop -p plan-shop -n app-shop-prod --runtime "NODE:22-lts"
az webapp identity assign -g rg-shop -n app-shop-prod --identities '[system]'

# Staging slot cloned from production settings
az webapp deployment slot create -g rg-shop -n app-shop-prod --slot staging \
  --configuration-source app-shop-prod

# Slot-sticky setting (stays with the slot during a swap)
az webapp config appsettings set -g rg-shop -n app-shop-prod --slot staging \
  --slot-settings APP_ENV=staging

# Swap staging into production
az webapp deployment slot swap -g rg-shop -n app-shop-prod --slot staging --target-slot production
```

- Runtime strings differ by stack and change over time; list them with `az webapp list-runtimes --os-type linux`.
- Slots require the Standard tier or higher. Slots share the plan's compute, so load tests on a slot affect production.
- Slot-sticky (`--slot-settings`) values do not move on a swap; use them for environment names, connection targets and feature flags that belong to a slot. Other settings swap with the code.
- `az webapp deployment slot swap --action preview` applies the target slot's settings to the source first so you can test before completing; `--preserve-vnet` defaults to true.
- Key Vault references in app settings: `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<name>)`. Grant the app identity Key Vault Secrets User; for a user-assigned identity set the `keyVaultReferenceIdentity` property (Bicep: on the site resource, see the `Microsoft.Web/sites` template reference).
- VNet integration for outbound traffic: `az webapp vnet-integration add -g rg-shop -n app-shop-prod --vnet vnet-spoke --subnet snet-appsvc-integration`. The subnet is delegated to App Service and used only for outbound calls; inbound private access uses a private endpoint with group ID `sites`.
- Access restrictions control inbound traffic by rule priority, evaluated lowest number first, with an implicit deny once any rule exists:

```bash
az webapp config access-restriction add -g rg-shop -n app-shop-prod \
  --rule-name allow-frontdoor --priority 100 --action Allow \
  --service-tag AzureFrontDoor.Backend \
  --http-header x-azure-fdid=00000000-0000-0000-0000-000000000000
```

Replace the header value with your Front Door profile's ID so another tenant's Front Door cannot reach the app. Add a separate rule set for the `scm` (Kudu) site with `--scm-site true`.

- Turn on HTTPS only (`az webapp update -g rg-shop -n app-shop-prod --https-only true`), set a minimum TLS version, disable FTP basic publishing credentials unless needed, and turn on diagnostics logging to Log Analytics.

## 2. Container Apps

Concepts: an environment hosts apps and jobs; an app has revisions (immutable snapshots of the template); scale rules decide replica counts; ingress exposes a target port.

```bash
az extension add -n containerapp -y

az containerapp env create -g rg-shop -n cae-shop -l westeurope

az containerapp create -g rg-shop -n api --environment cae-shop \
  --image myregistry.azurecr.io/shop/api:1.4.0 \
  --registry-server myregistry.azurecr.io --registry-identity system \
  --system-assigned \
  --ingress external --target-port 8080 \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 1 --max-replicas 10 \
  --scale-rule-name http-load --scale-rule-type http --scale-rule-http-concurrency 50 \
  --revisions-mode multiple
```

- `--registry-identity system` (or a user-assigned identity resource ID) pulls from Azure Container Registry with AcrPull instead of admin credentials; grant AcrPull to the identity on the registry.
- Revisions mode: `single` (default) replaces the active revision on each update; `multiple` keeps several active and lets you split traffic. Change with `az containerapp revision set-mode`. Event-driven (non-HTTP) scale rules need single revision mode per the scaling documentation.
- Traffic splitting in multiple mode:

```bash
az containerapp ingress traffic set -g rg-shop -n api \
  --revision-weight api--v2=10 api--v1=90
az containerapp revision list -g rg-shop -n api -o table
az containerapp revision deactivate -g rg-shop -n api --revision api--v1
```

- Scale rules: `http` (concurrent requests per replica, default 10), `tcp`, and KEDA-based custom rules via `--scale-rule-type` (for example `azure-queue`) with `--scale-rule-metadata` and `--scale-rule-auth`. Prefer identity-based scaler authentication where the scaler supports it, instead of connection-string secrets; check the scaler's page in the docs.
- `--min-replicas 0` scales to zero and saves cost but adds a cold start; keep at least one replica for latency-sensitive APIs.
- Secrets: `--secrets name=value` stores values in the app; reference them from env vars with `secretref:name`. Better, use Key Vault-backed secrets with a managed identity so values are not typed into commands (check the secrets page for the current syntax).
- Dapr is available through the `--dapr-*` options (for example `--dapr-enable-api-logging` appears in the CLI help). Enable it only when the design uses its building blocks; the sidecar adds resource use.
- Jobs run to completion rather than serve traffic. Trigger types: Schedule, Event, Manual.

```bash
az containerapp job create -g rg-shop -n nightly-report --environment cae-shop \
  --trigger-type Schedule --cron-expression "0 2 * * *" \
  --image myregistry.azurecr.io/shop/report:1.4.0 \
  --registry-server myregistry.azurecr.io --registry-identity system \
  --replica-timeout 900 --replica-retry-limit 1 --parallelism 1
```

Cron expressions are evaluated in UTC. HTTP scale rules do not apply to jobs; event jobs use `--polling-interval`, `--min-executions`, `--max-executions` and a scale rule.

- Networking: bring the environment into your VNet with a dedicated infrastructure subnet at creation time; this cannot be retrofitted on all environment types, so decide early. Internal ingress keeps apps off the public internet.

## 3. AKS

Create a production-oriented cluster:

```bash
az aks create -g rg-aks -n aks-shop -l westeurope \
  --tier standard \
  --enable-managed-identity \
  --enable-aad --enable-azure-rbac --disable-local-accounts \
  --network-plugin azure --network-plugin-mode overlay --network-dataplane cilium \
  --pod-cidr 192.168.0.0/16 \
  --vnet-subnet-id "$SUBNET_ID" \
  --nodepool-name system --node-count 3 --zones 1 2 3 \
  --auto-upgrade-channel patch --node-os-upgrade-channel NodeImage \
  --enable-oidc-issuer --enable-workload-identity \
  --generate-ssh-keys

az aks nodepool add -g rg-aks --cluster-name aks-shop -n workers --mode User \
  --node-vm-size Standard_D4ds_v5 --zones 1 2 3 \
  --enable-cluster-autoscaler --min-count 2 --max-count 10 --max-surge 33%
```

- Network options (flags verified in CLI help): `--network-plugin azure` with `--network-plugin-mode overlay` gives Azure CNI Overlay (pods use an overlay CIDR, saving VNet addresses); `--network-plugin azure` alone gives pods VNet IPs from the subnet; `--network-dataplane cilium` selects the Cilium dataplane; `--network-policy` accepts `azure`, `cilium`, `calico` or `none`. `kubenet` is still listed by the CLI, but treat it as legacy and check the AKS docs for its retirement date before using it.
- Upgrade channels: `none`, `patch`, `stable` (latest patch of N-1 minor), `rapid` (latest patch of latest minor), and the legacy `node-image` value. Prefer `--node-os-upgrade-channel` for node OS patching. Out-of-support clusters can be upgraded by the platform even on `none`. AKS Automatic clusters fix the channel to `stable`.
- Pools: keep a `System` mode pool (use `--node-taints CriticalAddonsOnly=true:NoSchedule` to keep app pods off it) and separate `User` pools per workload class. Spot pools use `--priority Spot` with `--spot-max-price`, for interruptible work only.
- `--tier standard` buys the uptime SLA; `free` is for dev and test.
- Identity and access: Entra integration with Azure RBAC for Kubernetes (`--enable-azure-rbac`) and `--disable-local-accounts` removes static admin kubeconfigs. Fetch credentials with `az aks get-credentials` and, for Entra tokens, convert with `kubelogin convert-kubeconfig -l azurecli`.
- Outbound: `--outbound-type` accepts `loadBalancer` (default), `managedNATGateway`, `userAssignedNATGateway`, `userDefinedRouting` (through Azure Firewall or an NVA) and `none`. Use a NAT gateway for predictable outbound IPs and to avoid SNAT port exhaustion.
- Private clusters: `--enable-private-cluster` puts the API server behind a private endpoint; plan DNS and operator access. Otherwise restrict with `--api-server-authorized-ip-ranges`.
- Kubernetes objects, Helm charts and policies are covered by kubernetes-expert; this skill stops at the cluster, pools and Azure integrations.

## 4. Azure SQL Database

Create a server with Entra-only authentication and a serverless database:

```bash
az sql server create -g rg-data -n sql-shop-prod -l westeurope \
  --enable-ad-only-auth \
  --external-admin-principal-type Group \
  --external-admin-name sql-admins \
  --external-admin-sid "$ADMIN_GROUP_OBJECT_ID" \
  --minimal-tls-version 1.2

az sql db create -g rg-data -s sql-shop-prod -n shop \
  --edition GeneralPurpose --compute-model Serverless --family Gen5 \
  --capacity 2 --min-capacity 0.5 --auto-pause-delay 60 \
  --zone-redundant false --backup-storage-redundancy Zone
```

- With `--enable-ad-only-auth` no SQL logins or passwords exist, so there is no `--admin-password` to leak. For an existing server: `az sql server ad-only-auth enable -g rg-data -n sql-shop-prod` (set an Entra admin first). Enabling or disabling needs a high-privilege role such as Owner, Contributor or SQL Security Manager; SQL Server Contributor is not enough.
- Serverless scales compute between `--min-capacity` and `--capacity` vCores and can auto-pause after `--auto-pause-delay` minutes (the first connection after a pause resumes the database and takes time). Provisioned compute avoids this and suits steady production load. The free offer for a database is controlled with `--use-free-limit`; check the current offer terms.
- Give an application access by creating a contained user for its managed identity, run as an Entra admin connected to the target database (not `master`):

```sql
CREATE USER [app-shop-prod] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [app-shop-prod];
ALTER ROLE db_datawriter ADD MEMBER [app-shop-prod];
```

The user name is the managed identity's display name (the resource name for system-assigned identities). Grant narrower rights than `db_owner`.
- Connection strings carry no password. With Microsoft.Data.SqlClient use `Authentication=Active Directory Default` (or `Active Directory Managed Identity`), for example `Server=tcp:sql-shop-prod.database.windows.net,1433;Database=shop;Authentication=Active Directory Default;Encrypt=True`. Never turn off `Encrypt` or trust the server certificate to silence a failure.
- Network: `az network private-endpoint create ... --group-id sqlServer`, zone `privatelink.database.windows.net`, then disable public access with `az sql server update -g rg-data -n sql-shop-prod --enable-public-network false` (the flag is marked preview in the CLI). `--restrict-outbound-network-access` (preview) limits server egress.
- Geo-replication, failover groups, long-term retention and elastic pools are separate decisions; check the current docs for tier limits.

## 5. Choosing a compute service

| Need | Pick | Because |
|---|---|---|
| Web app or API in a supported runtime, minimal ops | App Service | Slots, built-in auth, simple scaling |
| Containerised HTTP services, event workers, scale to zero | Container Apps | KEDA scaling, revisions, no cluster to operate |
| Run-to-completion batch or scheduled work | Container Apps jobs | Schedule, Event and Manual triggers |
| Kubernetes APIs, operators, custom networking, many services | AKS | Full Kubernetes control, node pool flexibility |
| Short event handlers | Azure Functions | Per-execution billing (not detailed in this skill; check the Functions docs) |
