# Networking and Cost Control

Reference for VNet layout, private endpoints, egress, edge protection, budgets, tagging and Azure Policy. CLI flags were checked against Azure CLI 2.91.0 help; SKU details, pricing and retirement dates change often, so confirm them in the current docs before committing.

## Contents

1. [VNet layout](#1-vnet-layout)
2. [NSGs](#2-nsgs)
3. [Private endpoints and private DNS](#3-private-endpoints-and-private-dns)
4. [Egress control](#4-egress-control)
5. [Front Door and Application Gateway](#5-front-door-and-application-gateway)
6. [Budgets and cost visibility](#6-budgets-and-cost-visibility)
7. [Tags and Azure Policy](#7-tags-and-azure-policy)
8. [Commitment discounts](#8-commitment-discounts)

## 1. VNet layout

```bash
az network vnet create -g rg-net -n vnet-spoke-prod --address-prefixes 10.20.0.0/16
az network vnet subnet create -g rg-net --vnet-name vnet-spoke-prod -n snet-app \
  --address-prefixes 10.20.1.0/24
az network vnet subnet create -g rg-net --vnet-name vnet-spoke-prod -n snet-private-endpoints \
  --address-prefixes 10.20.2.0/24
```

- Plan address space before creating anything: ranges of peered VNets and on-premises networks must not overlap, and some services need a dedicated or delegated subnet with a minimum size (App Service VNet integration, Container Apps environments, AKS node subnets, Application Gateway, Azure Firewall, Bastion). Check each service's subnet requirements page.
- Keep a dedicated subnet for private endpoints so one NSG and route table policy covers them.
- Hub-and-spoke: shared services (Firewall, DNS resolver, Bastion, VPN or ExpressRoute gateway) in the hub, workloads in spokes, peering between them. Peering is not transitive; route through the hub firewall or use gateway transit.
- Zones: spread zone-capable resources across availability zones; subnets are not zonal.

## 2. NSGs

```bash
az network nsg create -g rg-net -n nsg-app
az network nsg rule create -g rg-net --nsg-name nsg-app -n allow-https-from-agw \
  --priority 100 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes 10.20.3.0/24 --destination-port-ranges 443
az network vnet subnet update -g rg-net --vnet-name vnet-spoke-prod -n snet-app \
  --network-security-group nsg-app
```

- Rules are evaluated by priority (lowest number first); default rules allow VNet-to-VNet and outbound internet and deny other inbound traffic. Add explicit deny rules where the defaults are too open.
- Prefer service tags (`AzureFrontDoor.Backend`, `Storage`, `Sql`) and application security groups over hard-coded IP lists.
- Do not open SSH or RDP to `*` or `Internet`. Use Azure Bastion, just-in-time access or a private jump path.
- Enable NSG flow logs or the current equivalent (check the docs; flow-log offerings have changed) for incident investigation.

## 3. Private endpoints and private DNS

Pattern for a Key Vault (the same shape applies to SQL, Storage and others):

```bash
KV_ID=$(az keyvault show -n kv-shop-prod --query id -o tsv)

az network private-endpoint create -g rg-net -n pe-kv-shop \
  --vnet-name vnet-spoke-prod --subnet snet-private-endpoints \
  --private-connection-resource-id "$KV_ID" --group-id vault \
  --connection-name kv-shop-conn

az network private-dns zone create -g rg-net -n privatelink.vaultcore.azure.net
az network private-dns link vnet create -g rg-net -z privatelink.vaultcore.azure.net \
  -n link-spoke-prod --virtual-network vnet-spoke-prod --registration-enabled false

az network private-endpoint dns-zone-group create -g rg-net --endpoint-name pe-kv-shop \
  -n default --private-dns-zone privatelink.vaultcore.azure.net \
  --zone-name privatelink.vaultcore.azure.net
```

| Service | Group ID | Private DNS zone |
|---|---|---|
| Key Vault | `vault` | `privatelink.vaultcore.azure.net` |
| Azure SQL Database | `sqlServer` | `privatelink.database.windows.net` |
| Storage (blob) | `blob` | `privatelink.blob.core.windows.net` |
| App Service / Functions | `sites` | `privatelink.azurewebsites.net` |

Other storage sub-resources (`file`, `queue`, `table`, `dfs`) and other services use their own group IDs and zones; look them up in the private endpoint DNS zone table in the Azure docs.

- The DNS zone group writes the A record automatically and keeps it in step with the endpoint; without it clients resolve the public address and connect to the wrong place or fail.
- Link each private DNS zone to every VNet that must resolve it. In hub-and-spoke designs keep zones in one place and link them to hub and spokes, and make on-premises DNS forward the `privatelink` suffixes to the hub resolver (Azure DNS Private Resolver or a DNS forwarder).
- After creating the endpoint, disable public network access on the service (`--public-network-access Disabled` for Key Vault, `--enable-public-network false` for SQL, `publicNetworkAccess: 'Disabled'` for Storage in Bicep) and test from inside the VNet with `nslookup <name>`, which should return a private address.
- Private endpoints cost per endpoint-hour plus data processed; centralize where several workloads share a service.
- Service endpoints are a simpler subnet-to-service allowlist but keep the service on its public IP; use private endpoints for stricter isolation.

## 4. Egress control

| Option | Use when | Notes |
|---|---|---|
| Default outbound access | Throwaway dev only | Implicit public IP that Microsoft is phasing out for new subnets; check the current docs for its status and do not design around it |
| NAT Gateway | You need stable outbound IPs or more SNAT ports | Attach to the subnet; uses Standard SKU public IPs or a prefix; no filtering |
| Azure Firewall | You need FQDN and network rules, threat intelligence, central logging | Route `0.0.0.0/0` through it with a route table (user-defined route) |
| Load balancer outbound rules | Simple internal setups | Watch SNAT exhaustion |

```bash
az network public-ip create -g rg-net -n pip-nat --sku Standard --allocation-method Static
az network nat gateway create -g rg-net -n natgw-spoke --public-ip-addresses pip-nat --idle-timeout 10
az network vnet subnet update -g rg-net --vnet-name vnet-spoke-prod -n snet-app --nat-gateway natgw-spoke
```

- Use Standard SKU public IPs; check the current docs for the retirement status of Basic SKU public IPs before relying on them anywhere.
- AKS accepts `--outbound-type managedNATGateway`, `userAssignedNATGateway` or `userDefinedRouting`; with the last, a route table to Azure Firewall must exist before cluster creation.
- Allow-list outbound by FQDN at the firewall for update endpoints, container registries and Azure control-plane dependencies; AKS and other platforms publish their required endpoints.

## 5. Front Door and Application Gateway

| | Front Door | Application Gateway |
|---|---|---|
| Scope | Global edge, anycast, many origins | Regional, deployed into your VNet |
| Layer | HTTP(S) | HTTP(S) (WAF v2), also TCP/TLS proxy features in newer SKUs (check the docs) |
| Use for | Public web apps and APIs across regions, caching, global failover | Regional ingress, private frontends, AKS ingress |
| WAF | Azure WAF policy with managed rule sets and bot protection | Azure WAF policy attached to gateway or listener |

- Start the WAF in Detection mode, review logs for false positives, then switch to Prevention. Tune with exclusions and custom rules rather than turning rule groups off wholesale.
- Lock the origin to the edge: for App Service use an access restriction on service tag `AzureFrontDoor.Backend` plus a header check on `X-Azure-FDID`; with Private Link origins the origin has no public path at all.
- Terminate TLS with a managed or Key Vault certificate, enforce HTTPS and a minimum TLS version, and redirect HTTP to HTTPS.
- Front Door and Application Gateway are separate products with their own CLI groups (`az afd` and `az network application-gateway`); `az afd` was not available in the core CLI used for verification, so check the current docs for exact commands and whether an extension is needed. Define them in Bicep or AVM modules for repeatability.

## 6. Budgets and cost visibility

```bash
# The consumption command group is in preview. Print the exact shorthand for the structured
# arguments before building the command.
az consumption budget create-with-rg --notifications "??"
az consumption budget create-with-rg --time-period "??"

# Shape of the final command (structured values come from the help above or from json/yaml files)
az consumption budget create-with-rg --resource-group rg-shop-prod \
  --budget-name shop-prod-monthly --amount 1500 --category Cost --time-grain Monthly \
  --time-period @time-period.json --notifications @notifications.json
```

A budget has a start date on the first of a month, up to five notifications, and a time grain of Monthly, Quarterly or Annually. To keep it in source control, define the budget in Bicep (`Microsoft.Consumption/budgets`; check the template reference for the current API version and schema).

- Budgets alert; they do not stop spend. For hard stops combine alerts with an action group that triggers automation, or Policy to prevent expensive SKUs.
- Set thresholds on actual cost (for example 50, 80, 100 percent) and a forecast threshold for early warning. Send alerts to a group mailbox, not a person.
- Cost Management supports scheduled exports of usage and cost data to a storage account for reporting and FinOps tooling. The CLI command group for exports is an extension in the version checked; use the portal, Bicep or the REST API as described in the current docs.
- Cost analysis groups by tag, resource group, service and location only for resources that carry the tags, so enforce tags first.
- Look for waste regularly: unattached disks and public IPs, idle App Service plans, oversized databases, development clusters running at night (stop AKS clusters or scale node pools to zero where supported), Log Analytics ingestion volume and retention.

## 7. Tags and Azure Policy

- Minimum tags: `env`, `owner`, `cost-center`, `app`. Apply them in templates through one shared `tags` parameter.
- Tags on a resource group are not inherited by resources by default; use a Policy with a modify effect to inherit or enforce them.
- Assign built-in policies where they exist (allowed locations, allowed VM SKUs, require a tag, deny public network access for storage or SQL). Use `az policy definition list --query "[?displayName=='Allowed locations']"` to find the built-in definition, then assign it.

```bash
POLICY_ID=$(az policy definition list --query "[?displayName=='Allowed locations'].id | [0]" -o tsv)
az policy assignment create --name allowed-locations --display-name "Allowed locations" \
  --policy "$POLICY_ID" --scope "/subscriptions/$SUBSCRIPTION_ID" \
  --params '{"listOfAllowedLocations": {"value": ["westeurope", "northeurope"]}}' \
  --enforcement-mode DoNotEnforce
```

- Start with `--enforcement-mode DoNotEnforce`, review compliance results, then switch to `Default` to enforce. Effects to know: `Audit`, `Deny`, `Modify`, `DeployIfNotExists`, `Disabled`. Policies that deploy or modify need a managed identity and role assignment (`--mi-user-assigned`, `--identity-scope`, `--location`).
- Group related policies into an initiative (policy set) and assign at management group or subscription scope. Use exemptions with an expiry for exceptions rather than weakening the policy.
- Policy governs resource properties at create and update time; it does not grant or restrict data access (that is RBAC).
- Deployment stacks with deny settings and resource locks (`CanNotDelete`, `ReadOnly`) protect specific resources; Policy covers whole scopes.

## 8. Commitment discounts

- Reservations commit to a specific resource type, size family and region for one or three years; savings plans commit to an hourly spend across eligible compute and are more flexible. Both apply as billing discounts, not as deployed resources.
- Commit only for baseline load that has run steadily for weeks; keep spiky and experimental workloads on pay-as-you-go. Review utilisation reports monthly and use the scope setting (shared, subscription, resource group) deliberately.
- Reserved capacity exists for services such as Azure SQL and Cosmos DB; check the current docs for which services and terms are offered, and for exchange and cancellation rules, which change over time.
- Dev/test pricing, Azure Hybrid Benefit and spot capacity are other levers; confirm eligibility in the current pricing docs before relying on them in a plan.
