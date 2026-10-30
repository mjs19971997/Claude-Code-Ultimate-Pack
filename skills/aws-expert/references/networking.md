# Networking

Reference for VPC design, egress, endpoints, connectivity and load balancing on AWS. Verified against the Amazon VPC documentation, including regional NAT gateways (announced 2025-11-19), and aws-cdk-lib 2.275.0 (2026-10).

## 1. CIDR planning

- Use RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). VPC CIDR blocks range from /16 to /28.
- Plan ranges across all accounts, regions, on-premises networks and partners before creating VPCs; overlapping ranges cannot be peered or routed through Transit Gateway. Use Amazon VPC IPAM to allocate non-overlapping blocks by OU or environment.
- A /16 per VPC leaves room for tiers and growth; secondary CIDR blocks can be added later.
- AWS reserves five addresses in every subnet (network, router, DNS, future use, broadcast), so a /28 subnet has 11 usable addresses.
- Consider IPv6 (dual stack) to avoid public IPv4 costs and NAT for outbound traffic; public IPv4 addresses are charged hourly, including those on in-use resources.

## 2. Subnet tiers and AZ layout

| Tier | Contents | Route to internet |
|---|---|---|
| Public | Load balancers, NAT gateways, nothing else | Internet gateway |
| Private (app) | ECS tasks, EC2, Lambda in VPC, EKS nodes | NAT gateway or egress proxy |
| Isolated (data) | RDS, Aurora, ElastiCache, internal-only services | None; reach AWS APIs through endpoints |

- Use at least two AZs, three for critical workloads; one subnet per tier per AZ, with route tables per AZ when each AZ has its own NAT gateway.
- Do not give instances public IPs by default; disable auto-assign public IPv4 on subnets.
- Separate VPCs (ideally separate accounts) for production and non-production, and a shared-services or network account for inspection and egress when scale demands it.

## 3. Egress patterns

- **Internet gateway** gives public subnets bidirectional access. **Egress-only internet gateway** gives IPv6 private subnets outbound access without inbound.
- **NAT gateway** gives IPv4 private subnets outbound access. A zonal NAT gateway lives in one AZ's public subnet; per-AZ NATs avoid cross-AZ dependency and cross-AZ data charges. A regional NAT gateway (`--availability-mode regional`, launched November 2025) expands across AZs automatically with no public subnet needed; its automatic mode is the configuration AWS recommends, it does not offer private connectivity (use zonal mode for private NAT), and expansion to a new AZ can take up to about an hour. Check regional availability and pricing before choosing.
- NAT gateways charge per hour and per GB processed: keep S3, DynamoDB and AWS API traffic off NAT with endpoints, and review Flow Logs for large talkers.
- Control outbound destinations with AWS Network Firewall (domain allow lists), a proxy fleet, or Route 53 Resolver DNS Firewall when data exfiltration risk is high.

## 4. VPC endpoints

| Type | Services | Notes |
|---|---|---|
| Gateway endpoint | S3, DynamoDB | No hourly or data charge; added as a route-table target; supports endpoint policies |
| Interface endpoint (PrivateLink) | Most other AWS services (Secrets Manager, SSM, ECR, STS, CloudWatch Logs, KMS, SQS and more) and partner or your own services | ENIs in your subnets; hourly plus per-GB charge; enable private DNS; attach security groups and endpoint policies |

- Required for fully isolated subnets: ECR (`ecr.api`, `ecr.dkr`) plus the S3 gateway endpoint for image layers, `logs`, `secretsmanager` or `ssm`, `sts`, and `kms` when used.
- Endpoint policies restrict which principals and resources can be used through the endpoint; pair with bucket policies on `aws:SourceVpce` for data perimeter control.
- Share interface endpoints from a central VPC through Transit Gateway only when the cost saving outweighs the complexity.

## 5. Security groups and network ACLs

- Security groups are stateful and allow-only, attached to ENIs. Reference other security groups instead of CIDR ranges (`app-sg` allows from `alb-sg`). Keep one group per role.
- Avoid `0.0.0.0/0` on anything except public load balancer listeners (80/443). Never open SSH or RDP to the internet; use SSM Session Manager (no inbound ports, audited) or EC2 Instance Connect Endpoint.
- Network ACLs are stateless and per subnet; leave defaults unless you need explicit subnet-level denies. Remember ephemeral return ports when you do write rules.
- Use prefix lists for shared CIDR sets and managed prefix lists for AWS services.
- Audit with Config rules and Security Hub controls for unrestricted ingress.

## 6. Connectivity

| Need | Option |
|---|---|
| Two VPCs, simple, no transitive routing | VPC peering (no overlapping CIDRs, non-transitive) |
| Many VPCs and on-premises networks | Transit Gateway (route tables per attachment for segmentation); AWS Cloud WAN for global networks |
| Expose one service to many consumers without routing the whole network | PrivateLink (endpoint service behind an NLB or GWLB), or VPC Lattice for service-to-service networking with auth policies |
| On-premises encrypted over internet | Site-to-Site VPN |
| Dedicated private link | Direct Connect (often with a VPN backup) |
| Inspection appliances | Gateway Load Balancer, Network Firewall |

## 7. DNS

- Enable `enableDnsSupport` and `enableDnsHostnames` on the VPC for endpoint private DNS and instance names.
- Route 53 private hosted zones for internal names associated with the VPCs that need them; Route 53 Resolver inbound and outbound endpoints for hybrid DNS.
- Use alias records to AWS resources; keep TTLs low only where failover needs it.
- Enable DNSSEC signing and query logging where compliance asks.

## 8. Load balancing and edge

- ALB for HTTP/HTTPS (host and path routing, OIDC authentication, WAF integration); NLB for TCP/UDP/TLS, static IPs and PrivateLink; GWLB for appliances.
- Terminate TLS with ACM certificates; redirect HTTP to HTTPS; use current TLS security policies (check the policy list for the latest).
- ALB hardening: drop invalid header fields, desync mitigation mode `defensive` or `strictest`, access logs to S3, deletion protection, WAF with managed rule groups and rate limits.
- CloudFront in front of public content and APIs with origin access control to S3 and a custom header or VPC origin for ALBs, so origins are not reachable directly.
- Shield Standard is automatic; consider Shield Advanced for large exposure.

## 9. Visibility

- VPC Flow Logs to S3 or CloudWatch Logs (reject-only for cost, all traffic for forensics on sensitive subnets); Athena queries for analysis.
- Reachability Analyzer and Network Access Analyzer verify intended paths and unintended exposure.
- Traffic Mirroring for packet-level inspection where needed.
- Alarm on NAT gateway `ErrorPortAllocation` and bytes-out anomalies.

## 10. CDK example

```ts
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";

export class NetworkStack extends Stack {
  public readonly vpc: ec2.Vpc;
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    this.vpc = new ec2.Vpc(this, "Vpc", {
      ipAddresses: ec2.IpAddresses.cidr("10.20.0.0/16"),
      maxAzs: 3,
      natGateways: 3,                      // one per AZ for production; fewer in dev
      subnetConfiguration: [
        { name: "public", subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: "app", subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 22 },
        { name: "data", subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
      ],
      gatewayEndpoints: {
        S3: { service: ec2.GatewayVpcEndpointAwsService.S3 },
        DynamoDB: { service: ec2.GatewayVpcEndpointAwsService.DYNAMODB },
      },
      flowLogs: { all: { trafficType: ec2.FlowLogTrafficType.ALL } },
    });
    this.vpc.addInterfaceEndpoint("Secrets", {
      service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
    });
  }
}
```

Terraform equivalents belong to terraform-expert.
