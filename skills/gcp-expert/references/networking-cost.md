# VPC Networking and Cost Controls

Designing a private network on Google Cloud and keeping spend visible and bounded. Commands were checked against Google Cloud CLI 570.0.0 (2026-10); product behaviour that the CLI help does not state is marked "check the current docs".

## Contents

1. [Custom mode VPC and subnets](#1-custom-mode-vpc-and-subnets)
2. [Private Google Access](#2-private-google-access)
3. [Private Service Connect for Google APIs](#3-private-service-connect-for-google-apis)
4. [Cloud NAT](#4-cloud-nat)
5. [Firewall policies](#5-firewall-policies)
6. [VPC Service Controls](#6-vpc-service-controls)
7. [Budgets and alerts](#7-budgets-and-alerts)
8. [Billing export to BigQuery](#8-billing-export-to-bigquery)
9. [Commitments](#9-commitments)
10. [Labels and quotas](#10-labels-and-quotas)

## 1. Custom mode VPC and subnets

```bash
gcloud compute networks create prod-vpc --project=orders-prod \
  --subnet-mode=custom --bgp-routing-mode=regional

gcloud compute networks subnets create app-us-central1 --project=orders-prod \
  --network=prod-vpc --region=us-central1 --range=10.10.0.0/20 \
  --enable-private-ip-google-access --enable-flow-logs
```

- Custom mode lets you choose ranges. Auto mode creates a subnet in every region from a fixed block and can collide with on-premises or peered ranges. The `default` network is auto mode; stop it being created with `constraints/compute.skipDefaultNetworkCreation`.
- Plan CIDR ranges across environments, on-premises networks and GKE (Pod and Service secondary ranges via `--secondary-range` on the subnet) before creating subnets; ranges can be expanded but not shrunk.
- `--bgp-routing-mode` is `regional` by default; use `global` when Cloud Router must advertise routes across regions.
- Flow logs help investigations; they add logging cost, so sample (`--logging-flow-sampling`) and filter where volume is high.
- Use Shared VPC when a central team owns the network: a host project owns the VPC, service projects get `roles/compute.networkUser` on specific subnets.
- Avoid external IPs on VMs; enforce with `constraints/compute.vmExternalIpAccess` and reach instances with IAP TCP forwarding or OS Login. Check the current IAP documentation for setup.

## 2. Private Google Access

Private Google Access lets resources with only internal IPs reach Google APIs and services through the subnet.

```bash
gcloud compute networks subnets update app-us-central1 --project=orders-prod \
  --region=us-central1 --enable-private-ip-google-access
gcloud compute networks subnets describe app-us-central1 --region=us-central1 \
  --project=orders-prod --format="value(privateIpGoogleAccess)"
```

- It is a per-subnet setting. It also needs routing to Google's API ranges and DNS that resolves Google API names appropriately; the default internet gateway route covers the routing for public endpoints (`*.googleapis.com`).
- For restricted access, DNS can point to the `restricted.googleapis.com` or `private.googleapis.com` virtual IP ranges (check the current docs for the ranges). `restricted.googleapis.com` fits VPC Service Controls.
- Private Google Access traffic to Google APIs does not use Cloud NAT, so it avoids NAT data processing charges for that traffic.

## 3. Private Service Connect for Google APIs

PSC endpoints give Google APIs an internal IP address of your choosing.

```bash
gcloud compute addresses create psc-google-apis --project=orders-prod \
  --global --purpose=PRIVATE_SERVICE_CONNECT --addresses=10.255.0.5 \
  --network=prod-vpc

gcloud compute forwarding-rules create pscgoogleapis --project=orders-prod \
  --global --network=prod-vpc --address=psc-google-apis \
  --target-google-apis-bundle=all-apis
```

- Bundles: `all-apis` (all Google APIs) or `vpc-sc` (APIs that support VPC Service Controls). Use `vpc-sc` when a perimeter protects the project.
- The address must be outside the subnet ranges used by the VPC; reserve a dedicated block for endpoints. Naming rules for these forwarding rules are strict; check the current docs if creation fails.
- Create DNS records (for example a private zone) so API hostnames resolve to the endpoint address; check the current PSC documentation for the exact DNS names.
- PSC is also how consumers reach published services (including Cloud SQL with `--enable-private-service-connect`) across VPCs without peering and without overlapping-range problems.

## 4. Cloud NAT

Cloud NAT provides outbound internet access for resources without external IPs.

```bash
gcloud compute routers create nat-router --project=orders-prod \
  --network=prod-vpc --region=us-central1

gcloud compute routers nats create nat-us-central1 --project=orders-prod \
  --router=nat-router --region=us-central1 \
  --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges \
  --enable-logging --log-filter=ERRORS_ONLY
```

- Use `--nat-external-ip-pool` with reserved addresses when partners need a fixed allowlist of source IPs, and `--nat-custom-subnet-ip-ranges` to limit which subnets use NAT.
- Watch for port exhaustion (many connections to the same destination): raise `--min-ports-per-vm` or enable dynamic port allocation (`--enable-dynamic-port-allocation` where supported; check the current docs).
- Cloud NAT is regional and does not handle inbound connections. GKE private nodes and Cloud Run with `--vpc-egress=all-traffic` rely on it for internet egress.
- NAT is billed on gateway hours and data processed, so route Google API traffic through Private Google Access or PSC instead.

## 5. Firewall policies

Network firewall policies are the current way to manage rules at scale; they attach to VPC networks and replace per-VPC firewall rule sprawl. Legacy VPC firewall rules (`gcloud compute firewall-rules`) still work, and an implied deny-ingress and allow-egress rule applies at the bottom.

```bash
gcloud compute network-firewall-policies create orders-prod-policy \
  --project=orders-prod --global --description="Prod VPC policy"

# Allow health checks and load balancer probes to the app tag, nothing else inbound
gcloud compute network-firewall-policies rules create 1000 \
  --project=orders-prod --firewall-policy=orders-prod-policy --global-firewall-policy \
  --action=allow --direction=INGRESS \
  --src-ip-ranges=35.191.0.0/16,130.211.0.0/22 \
  --layer4-configs=tcp:8080 --enable-logging \
  --description="Google health check ranges"

gcloud compute network-firewall-policies associations create \
  --project=orders-prod --firewall-policy=orders-prod-policy --global-firewall-policy \
  --network=prod-vpc --name=prod-vpc-association
```

- Rule priority is the positional number: lower numbers are evaluated first. Leave gaps (100, 200, ...) to insert rules later.
- Target rules with secure tags (`--target-secure-tags`, `--src-secure-tags`) or service accounts rather than IP lists where possible; they follow identities instead of addresses.
- Rules can match FQDNs (`--dest-fqdns`) and threat intelligence lists in supported tiers; check the current docs for edition requirements.
- Hierarchical firewall policies attach to organizations or folders to set guardrails (for example deny SSH from the internet everywhere) that projects cannot override; they evaluate before network policies.
- Inspect the result with `gcloud compute network-firewall-policies get-effective-firewalls --network=prod-vpc` and keep rules narrow: specific ports, specific sources, logging on allow rules for sensitive paths.

## 6. VPC Service Controls

VPC Service Controls draw a perimeter around Google APIs for chosen projects, so credentials alone cannot move data across the boundary.

```bash
# Dry-run perimeter first: violations are logged, nothing is blocked
gcloud access-context-manager perimeters dry-run create orders-perimeter \
  --policy=ACCESS_POLICY_ID \
  --perimeter-title="Orders data perimeter" --perimeter-type=regular \
  --resources=projects/PROJECT_NUMBER \
  --restricted-services=storage.googleapis.com,bigquery.googleapis.com

# After reviewing audit logs for violations and adding ingress/egress rules
gcloud access-context-manager perimeters dry-run enforce orders-perimeter \
  --policy=ACCESS_POLICY_ID
```

- Resources in `--resources` are projects by number (`projects/123456789`) or VPC networks. `--restricted-services` lists the APIs the perimeter protects.
- Access from outside is allowed only through access levels (`--access-levels`) and ingress or egress policy YAML files (`--ingress-policies`, `--egress-policies`). Design these from the violations seen in dry run.
- Use the `restricted.googleapis.com` virtual IP or a PSC endpoint with the `vpc-sc` bundle for in-perimeter clients.
- Perimeters block legitimate flows that cross the boundary (CI deploys, partner access, BigQuery cross-project queries). Run in dry run for long enough to cover monthly and quarterly jobs.
- Pair a perimeter with `constraints/iam.allowedPolicyMemberDomains` and uniform bucket-level access; none of these replaces least-privilege IAM.

## 7. Budgets and alerts

```bash
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="orders-prod monthly" \
  --budget-amount=2000USD \
  --calendar-period=month \
  --filter-projects=projects/orders-prod \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0,basis=forecasted-spend \
  --notifications-rule-pubsub-topic=projects/billing-admin/topics/budget-alerts
```

- A budget notifies; it does not stop resources. By default, billing account administrators and users receive threshold emails (`--disable-default-iam-recipients` turns that off), and a Pub/Sub topic or Cloud Monitoring channel can receive programmatic notifications.
- `--threshold-rule=percent=...,basis=forecasted-spend` alerts on forecasted overruns before they happen; the default basis is current spend.
- Filter by project, service (`--filter-services`), label (`--filter-labels`, one pair) or resource ancestor (`--filter-resource-ancestors`, for a folder). `--credit-types-treatment` controls whether credits reduce counted spend.
- Automation that reacts to a budget message (for example detaching billing from a sandbox project) must be tested; detaching billing stops resources and can lose data. Give such automation its own narrow service account.
- Hard limits come from quotas, `--max-instances`, and org policies, not from budgets.

## 8. Billing export to BigQuery

- Enable export in the Cloud Billing console (Billing export) for the billing account: standard usage cost, detailed usage cost (resource level), and pricing data go to a BigQuery dataset you choose. Use a dataset in a dedicated billing-admin project with restricted access.
- Standard and detailed usage tables are named with the billing account ID, for example `gcp_billing_export_v1_<ACCOUNT_ID>` and `gcp_billing_export_resource_v1_<ACCOUNT_ID>`; confirm the names in your dataset.
- Export starts from the day it is enabled; earlier usage is not backfilled. Enable it when the billing account is created.
- Spend-based commitment metadata can be exported to a `cud_subscriptions_export` table, which joins to usage data by subscription ID.
- Group costs with labels, project, service and SKU. Example query shape (run in BigQuery with a parameterised date range; table names come from your dataset):

```sql
SELECT
  project.id AS project_id,
  (SELECT value FROM UNNEST(labels) WHERE key = 'team') AS team,
  service.description AS service,
  SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) AS net_cost
FROM `billing-admin.billing_export.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`
WHERE usage_start_time >= TIMESTAMP(@start_date) AND usage_start_time < TIMESTAMP(@end_date)
GROUP BY project_id, team, service
ORDER BY net_cost DESC;
```

## 9. Commitments

- Resource-based committed use discounts commit to a minimum amount of Compute Engine resources (vCPU, memory and so on) in a region for one or three years. They suit stable machine families and regions.
- Spend-based commitments commit to a minimum hourly spend on a product or service and apply to eligible usage each hour; they cover more services and tolerate changes in machine shape.
- Google is moving spend-based commitments from a credit model to a discount model, with the switch date shown in the Billing Overview page; check which model applies to the account before writing cost queries.
- Review the CUD analysis report before buying, size commitments to the steady baseline (not peaks), and track utilisation after purchase. Keep experimental and bursty workloads outside commitments.
- Cloud Run, GKE Autopilot and other serverless products have their own commitment eligibility; check the current commitments documentation per product. Discount percentages vary by product, term and region, so use the pricing pages rather than remembered figures.

## 10. Labels and quotas

- Apply labels at creation (`--labels=env=prod,team=orders,cost-center=cc-1234` on `gcloud projects create`, `gcloud run deploy`, `gcloud container clusters create`, `gcloud run jobs create`, `gcloud container clusters create-auto`). `gcloud projects update` in the GA CLI changes only the name, so add labels to existing projects through the console, API or a release-track command (check the current docs).
- Define a small mandatory label set, enforce it in IaC review (terraform-expert), and use it in billing export queries and budgets. Labels are not secret and must not hold personal data.
- Not every resource supports labels or appears in billing export with the label; verify on a sample before relying on it for chargeback.
- Quotas are per project (and often per region). View and request changes in the Quotas page of the console, or with the quota CLI; the quota commands are not part of the base `gcloud` command set used here, so check the current quotas documentation for the command group and its component requirements.
- Treat a quota as a safety limit too: lowering a quota or capping instances in a sandbox project limits the blast radius of leaked credentials or runaway loops.
- API rate limits and per-minute quotas show up as `RESOURCE_EXHAUSTED` or HTTP 429; retry with exponential backoff and request increases ahead of launches.
