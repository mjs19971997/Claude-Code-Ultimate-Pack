---
name: aws-expert
description: >-
  Designs and reviews AWS architectures against the Well-Architected pillars: IAM least privilege (roles, IAM Identity Center, permission boundaries, SCPs and RCPs), multi-account setup with Organizations and Control Tower, VPC layout and endpoints, choosing between Lambda, ECS/Fargate, EKS and EC2, S3 and database choices (RDS, Aurora, DynamoDB), secrets handling, IMDSv2, CloudTrail, GuardDuty and Config, cost control, plus AWS SDK for JavaScript v3, boto3 and AWS CDK v2 usage. Use when making AWS service choices, writing IAM policies, hardening an account or reviewing AWS code. Not for Terraform or OpenTofu modules (use terraform-expert), Kubernetes manifests (use kubernetes-expert), or GitHub Actions pipelines (use cicd-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# AWS Expert

This skill covers choosing, securing and operating AWS services: identity and access, account structure, networking, compute, storage and data stores, secrets, detection, cost, and application code that talks to AWS through the SDKs. Infrastructure as code with Terraform is a separate skill; CDK appears here only as far as it expresses AWS-specific defaults.

> Verified against AWS SDK for JavaScript v3 3.1161.0 (Node.js 20 or later), boto3 1.43.x (Python 3.10 or later), AWS CLI 2.39.x, AWS CDK library aws-cdk-lib 2.275.0 with CLI aws-cdk 2.1146.x, Lambda runtimes nodejs24.x and python3.14 (2026-10).

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

- Covered: Well-Architected review, IAM and Organizations guardrails, account and network design, service selection for compute, storage, databases and messaging, secrets and key management, detection and audit services, cost management, AWS SDK for JavaScript v3, boto3, AWS CLI v2 and CDK v2 usage patterns.
- Not covered: Terraform and OpenTofu modules and state (terraform-expert), Kubernetes workloads on EKS (kubernetes-expert), CI/CD pipeline design and GitHub OIDC workflow syntax (cicd-expert), generic distributed-systems design (system-design-expert, solution-architect), Postgres tuning (postgresql-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Well-Architected pillars | Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability; use the Well-Architected Tool to record decisions and risks per workload |
| Identity | Humans sign in through IAM Identity Center (permission sets become roles in each account); workloads use IAM roles with temporary credentials; avoid IAM users and long-lived access keys |
| Policy evaluation | Default deny; an explicit deny anywhere wins; SCPs, RCPs, permission boundaries and session policies only limit, they never grant |
| Guardrails | SCPs restrict principals in member accounts (not the management account); resource control policies (RCPs) restrict resources such as S3, KMS, STS, SQS and Secrets Manager; declarative policies enforce service baselines (for example EC2 IMDS and block public access) |
| Multi-account | Organizations with OUs, Control Tower landing zone (Log Archive and Audit accounts), organization CloudTrail, centralized root access management for member accounts |
| Networking | VPC per environment or per account, private subnets by default, gateway endpoints for S3 and DynamoDB, interface endpoints (PrivateLink) for other services, regional or per-AZ NAT gateways |
| Compute | Lambda (up to 15 min, 10,240 MB memory), ECS on Fargate or EC2, ECS Express Mode (Nov 2025) for single-image web services, EKS, EC2 with Auto Scaling |
| Storage | S3 Block Public Access and ACLs disabled are default for new buckets since April 2023; SSE-S3 is the base encryption for all new objects since January 2023 |
| Data stores | RDS and Aurora (relational), Aurora Serverless v2 (can scale to 0 ACU with auto-pause), DynamoDB (key-value and document), ElastiCache, OpenSearch |
| Secrets | Secrets Manager (rotation, replication) and SSM Parameter Store SecureString (KMS); fetched at runtime by role, never baked into user-data, AMIs or code |
| Instance metadata | IMDSv2 is session-token based; require it with `HttpTokens=required` |
| Detection | CloudTrail, GuardDuty, AWS Config, Security Hub, IAM Access Analyzer, Inspector, Macie |
| SDKs | JavaScript SDK v2 (`aws-sdk`) reached end-of-support on 2025-09-08; use v3 modular clients (`@aws-sdk/client-*`); boto3 clients over the feature-frozen resource interface |
| IaC | CDK v2 (`aws-cdk-lib`, CLI versioned separately from the library), CloudFormation underneath; CDK v1 is end-of-life |

## 3. Workflow

1. Clarify the workload: traffic shape, data sensitivity and residency, availability target (RTO and RPO), team skills, budget, compliance needs.
2. Fix the account boundary first: which account and OU, which guardrails apply, who can deploy (roles, not users).
3. Choose services by the decision rules below, preferring managed, serverless-first options when the workload fits.
4. Design identity: one role per workload component, scoped actions and resources, conditions for org, VPC endpoint or source ARN.
5. Design the network: AZ count, subnet tiers, egress path, endpoints, which services are private.
6. Define data protection: encryption keys, backups, versioning, retention, cross-region copies for the RPO.
7. Add detection and cost controls: org trail, GuardDuty, Config rules, Budgets and anomaly detection, tags.
8. Express it as code (CDK or Terraform), review the diff (`cdk diff`), deploy through a pipeline using short-lived credentials.
9. Validate: Access Analyzer policy checks, Config conformance, load and failure tests, restore tests.
10. Review against the checklist below and record trade-offs.

## 4. Decision Rules

- **Compute**: event-driven or spiky short tasks go to Lambda; long-running HTTP or worker containers go to ECS on Fargate; choose ECS Express Mode for a quick, opinionated web service on Fargate with an ALB; choose EKS only when the team needs the Kubernetes API or portability (kubernetes-expert); use EC2 for special hardware, licensed software, kernel access or steady-state cost optimization with Savings Plans.
- **Lambda runtime**: use a current managed runtime (`nodejs24.x`, `python3.14`; check the runtime support policy for deprecation dates) or `provided.al2023` for Go, Rust and custom builds; prefer arm64 (Graviton) unless a dependency blocks it.
- **Relational data**: RDS for standard engines and simple needs; Aurora for higher throughput, fast failover and read scaling; Aurora Serverless v2 for variable load (minimum 0 ACU enables auto-pause, but a proxy holding connections prevents pausing).
- **Key-value access**: DynamoDB when access patterns are known and keyed; on-demand capacity for unpredictable traffic, provisioned with auto scaling for steady load.
- **Object storage**: S3; use CloudFront with origin access control for public content so buckets stay private.
- **Messaging**: SQS for work queues (add a dead-letter queue), SNS for fan-out, EventBridge for event routing and schedules, Kinesis for ordered high-volume streams, Step Functions for orchestration.
- **Secrets**: Secrets Manager when rotation, cross-region replication or resource policies are needed; Parameter Store SecureString for configuration with lighter needs. Both are read at runtime through the workload's role.
- **Human access**: IAM Identity Center with MFA and short sessions. IAM users only where nothing else works, and then without console passwords for automation.
- **Cross-account access**: assume a role (with `ExternalId` for third parties) rather than sharing keys; use resource policies with `aws:PrincipalOrgID` for org-wide sharing.
- **Region strategy**: pick regions for latency, data residency and service availability; deny unused regions with an SCP; replicate data deliberately.
- **Disaster recovery**: backup and restore, pilot light, warm standby or multi-site active/active, chosen from RTO and RPO and priced honestly.

## 5. Coding Standards

- Never hardcode credentials or region-specific account IDs; let the SDK default credential provider chain resolve credentials (instance, task or function role; SSO profile locally).
- JavaScript/TypeScript: AWS SDK v3 with one client instance per service per process, created outside the handler; import only the clients and commands used; use paginators (`paginateListObjectsV2`) and `@aws-sdk/lib-dynamodb` for DynamoDB documents.
- Python: boto3 clients created once at module load; `botocore.config.Config(retries={"mode": "standard", "max_attempts": 5})`; paginators and waiters instead of manual loops; avoid the resource interface for new code.
- Name resources consistently with environment and purpose; tag with `Owner`, `Environment`, `CostCenter`, `Service` and activate cost allocation tags.
- Make operations idempotent (client tokens, conditional writes, idempotency keys) because retries and at-least-once delivery are normal.
- Set explicit timeouts and bounded retries with jitter on every AWS call and downstream HTTP call.
- IAM policies: specific actions, specific resource ARNs, conditions where available; no `Action: "*"` with `Resource: "*"`.
- Prefer CDK L2 constructs with their secure defaults; run `cdk-nag` or equivalent checks in CI.

## 6. Project Structure

```
.
├── infra/                       # CDK app (or Terraform modules; see terraform-expert)
│   ├── bin/app.ts               # stages per environment and account
│   ├── lib/network-stack.ts
│   ├── lib/data-stack.ts
│   ├── lib/service-stack.ts
│   └── cdk.json
├── services/
│   └── api/                     # application code; one deployable per directory
│       ├── src/
│       └── test/
├── policies/                    # SCPs, RCPs, permission boundaries as reviewed JSON
└── docs/
    └── adr/                     # decisions, Well-Architected review notes
```

Keep per-environment configuration in code (typed props or context), not in console edits.

## 7. Design Patterns

- **Landing zone**: Control Tower with `Security` OU (Log Archive, Audit), `Infrastructure` OU (network, shared services), `Workloads` OUs (prod and non-prod), `Sandbox` OU with budget limits. Details in [references/iam-and-security.md](references/iam-and-security.md).
- **Three-tier VPC**: public subnets hold only load balancers and NAT, private subnets hold compute, isolated subnets hold data stores; gateway endpoints keep S3 and DynamoDB traffic off NAT. Details in [references/networking.md](references/networking.md).
- **Event-driven serverless**: API Gateway or Lambda function URL, SQS or EventBridge buffer, Lambda consumer with partial batch responses and a DLQ.
- **Queue-based load leveling**: front slow or rate-limited dependencies with SQS and a bounded worker pool.
- **Cell-based isolation**: replicate a stack per customer group or region slice to limit blast radius.
- **Presigned URL upload and download**: the API authorizes, signs a short-lived URL for one object key, and clients talk to S3 directly (see the example).
- **Secrets by reference**: pass the secret ARN or parameter name to the workload, fetch the value at startup or on demand with caching, never pass the value through infrastructure parameters.
- **Choosing and sizing compute, storage and data stores**: [references/compute-and-data-choices.md](references/compute-and-data-choices.md).

## 8. Best Practices

- Use many accounts: separate production, non-production, security tooling, logging and shared network; account boundaries are the strongest isolation AWS offers.
- Enable organization-wide services once, centrally: CloudTrail organization trail, GuardDuty, Config, Security Hub, Access Analyzer with delegated administrators.
- Turn on EBS encryption by default and S3 Block Public Access at the account level.
- Use KMS customer managed keys where you need key policies, grants, auditing or cross-account access; otherwise AWS managed or service-owned keys are acceptable.
- Treat quotas as design inputs: check Service Quotas before launch and request increases early.
- Build in multiple AZs (at least two, preferably three) for anything with an availability target.
- Automate everything repeatable with IaC and keep drift detection on.
- Use AWS Backup with vault lock and cross-account copies for data that must survive account compromise.
- Prefer Graviton instances, current-generation families and managed services to reduce operational and compute cost.
- Keep logs with explicit retention (`RetentionInDays`); unbounded CloudWatch Logs and untagged resources are common cost leaks.

## 9. Performance

- Lambda: size memory to the CPU you need (CPU scales with memory), measure with real traffic, move initialization outside the handler, keep packages small, use SnapStart where the runtime supports it and cold starts matter, and provisioned concurrency only for latency-critical paths.
- DynamoDB: design for even key distribution; avoid scans; use GSIs for secondary access patterns; use `BatchGetItem`/`TransactWriteItems` where appropriate; DAX or ElastiCache for read-heavy hot keys.
- S3: parallelize multipart uploads and ranged GETs; use prefixes naturally; CloudFront for read-heavy public content; Transfer Acceleration only when measured to help.
- Databases: connection pooling through RDS Proxy for Lambda-heavy workloads (note that a proxy blocks Aurora Serverless v2 auto-pause), read replicas for read scaling, right-sized instances via Compute Optimizer.
- Networking: keep chatty services in one AZ per request path when possible to limit cross-AZ transfer cost, use VPC endpoints to avoid NAT bandwidth charges, and use placement and enhanced networking for HPC.
- Observe before tuning: CloudWatch metrics and traces (X-Ray or OpenTelemetry via ADOT) identify the real bottleneck.

## 10. Security

- Root user: MFA, no access keys, used only for the few root-only tasks; in Organizations, use centralized root access management for member accounts.
- No long-lived keys: roles for workloads, Identity Center for people, OIDC federation for CI (see cicd-expert). If a key exists, rotate it, scope it, and plan its removal.
- Secrets live in Secrets Manager or Parameter Store and are fetched at runtime by role. Never put secrets in EC2 user-data (it is readable through instance metadata and `DescribeInstanceAttribute`), in AMIs, in environment variables baked into images or task definitions, in code, or in plaintext CloudFormation parameters (use dynamic references such as `{{resolve:secretsmanager:...}}`).
- Require IMDSv2 on every instance, launch template and account default (`aws ec2 modify-instance-metadata-defaults --http-tokens required`), and enforce with an SCP or declarative policy. Set the hop limit to 2 only where containers need it.
- S3: Block Public Access on at account and bucket level, bucket policy denying non-TLS (`aws:SecureTransport`), object ownership `BucketOwnerEnforced`, versioning for important data, presigned URLs short-lived and per object.
- Encrypt at rest (KMS) and in transit (TLS 1.2 or later); enable EBS and RDS encryption at creation because it cannot be switched on in place for existing resources.
- Enforce guardrails with SCPs and RCPs: deny leaving the organization, disabling CloudTrail, GuardDuty or Config, unused regions, and unencrypted or public data exposure.
- Protect against confused deputy: use `aws:SourceArn` and `aws:SourceAccount` in resource policies for service principals, `ExternalId` for third-party roles.
- Detection: organization trail with log file validation to a locked log archive bucket, GuardDuty in all regions, Config rules or conformance packs, Security Hub standards, Access Analyzer external and unused access findings.
- Tenant isolation: scope every read and every write by tenant (IAM condition on `aws:PrincipalTag`, key prefixes, DynamoDB leading keys), not reads alone.
- Details and policy examples: [references/iam-and-security.md](references/iam-and-security.md).

## 11. Testing

- Unit-test application code with SDK mocks (`aws-sdk-client-mock` for v3, `botocore.stub.Stubber` or `moto` for boto3).
- Integration-test against real accounts in a sandbox OU; local emulators (LocalStack and similar) are approximations and miss IAM, VPC and quota behavior.
- CDK: assertions tests (`Template.fromStack(...).hasResourceProperties`), snapshot tests used sparingly, `cdk synth` and `cdk diff` in pull requests.
- Policy checks: IAM Access Analyzer `validate-policy` and custom policy checks in CI; simulate with `aws iam simulate-principal-policy`.
- Resilience: game days for AZ failure, throttling and dependency timeouts; restore a backup into a scratch account on a schedule and time it against the RTO.
- Cost tests: estimate before launch with the Pricing Calculator and verify with Cost Explorer a week after.

## 12. Review Checklist

- [ ] Workload sits in the right account and OU; SCPs and RCPs apply.
- [ ] No IAM users with access keys; humans via Identity Center; workloads via roles.
- [ ] Policies are least privilege with specific resources and conditions; no wildcard admin.
- [ ] Root has MFA and no keys; centralized root access is enabled in the organization.
- [ ] Secrets only in Secrets Manager or Parameter Store; nothing in user-data, AMIs, code or plaintext parameters.
- [ ] IMDSv2 required; Block Public Access on; encryption at rest and TLS in transit.
- [ ] Multi-AZ for stateful and load-balanced components; backups tested; RTO and RPO met.
- [ ] CloudTrail, GuardDuty, Config and Security Hub enabled and routed to security accounts.
- [ ] Budgets, anomaly detection, tags and log retention set.
- [ ] SDK usage: v3 or current boto3, reused clients, timeouts and retries configured.
- [ ] Infrastructure is code, reviewed with a diff, deployed with short-lived credentials.

## 13. Production Notes

- Amazon Linux 2 reached end of support on 2026-06-30; build on Amazon Linux 2023 or another supported OS. Plan for Lambda runtime deprecations using the published dates in the runtime support policy and AWS Health notifications.
- Use Service Quotas and AWS Health events for capacity and deprecation planning; subscribe the operations mailbox or chat channel.
- Pin infrastructure tool versions; the CDK CLI (`aws-cdk`) and the construct library (`aws-cdk-lib`) are versioned separately, so pin both and read the CDK release notes before upgrading either.
- Deploy with change sets or `cdk diff` approval, use stack termination protection and `RemovalPolicy.RETAIN` for stateful resources, and enable deletion protection on databases.
- Keep break-glass access documented: a tightly controlled role and root recovery path, tested yearly.
- Public IPv4 addresses are charged hourly; prefer private addressing, IPv6 and load balancers over per-instance public IPs.
- Use AWS Health and CloudTrail Lake or Athena for audit questions after incidents; keep logs for the retention your compliance regime requires.

## 14. Examples

Service control policy that denies IMDSv1 launches, leaving the organization, and tampering with CloudTrail (attach to workload OUs after testing in a sandbox):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireImdsV2",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": { "StringNotEquals": { "ec2:MetadataHttpTokens": "required" } }
    },
    {
      "Sid": "DenyLeaveOrganization",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    },
    {
      "Sid": "ProtectCloudTrail",
      "Effect": "Deny",
      "Action": ["cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "cloudtrail:UpdateTrail", "cloudtrail:PutEventSelectors"],
      "Resource": "*",
      "Condition": { "ArnNotLike": { "aws:PrincipalArn": "arn:aws:iam::*:role/SecurityAdminRole" } }
    }
  ]
}
```

CDK v2 (TypeScript) stack with a private encrypted bucket and a function that receives only the secret ARN:

```ts
import { Stack, StackProps, RemovalPolicy, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";

export class DataStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, "Uploads", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const apiKey = secretsmanager.Secret.fromSecretNameV2(this, "ApiKey", "prod/payments/api-key");

    const fn = new lambda.Function(this, "Api", {
      runtime: lambda.Runtime.NODEJS_24_X,
      architecture: lambda.Architecture.ARM_64,
      handler: "index.handler",
      code: lambda.Code.fromAsset("services/api/dist"),
      timeout: Duration.seconds(10),
      environment: { BUCKET: bucket.bucketName, API_KEY_SECRET: apiKey.secretName }, // names only, no values
    });
    bucket.grantReadWrite(fn);   // scoped grant on this bucket
    apiKey.grantRead(fn);        // scoped to this secret
  }
}
```

Presigned upload and download with AWS SDK v3, with server-generated keys and per-user prefixes on both reads and writes:

```ts
import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { randomUUID } from "node:crypto";

const s3 = new S3Client({});                 // region and credentials come from the environment or role
const BUCKET = process.env.BUCKET!;
const ALLOWED = new Set(["image/png", "image/jpeg"]);

export async function createUploadUrl(userId: string, contentType: string) {
  if (!ALLOWED.has(contentType)) throw new Error("unsupported content type");
  const key = `uploads/${userId}/${randomUUID()}`;     // never built from client-supplied names
  const url = await getSignedUrl(
    s3,
    new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType }),
    { expiresIn: 300 },
  );
  return { url, key };
}

export async function createDownloadUrl(userId: string, key: string) {
  const prefix = `uploads/${userId}/`;
  if (!key.startsWith(prefix) || key.includes("..")) throw new Error("forbidden");
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: BUCKET, Key: key }), { expiresIn: 300 });
}
```

## 15. Common Mistakes

- **Long-lived access keys in CI, laptops or code**: leaked keys are the top cause of account compromise. Use roles, Identity Center and OIDC.
- **Secrets in EC2 user-data, AMIs or task environment values**: readable by anyone with describe permissions or instance access. Use Secrets Manager or Parameter Store.
- **IMDSv1 left enabled**: SSRF in the app yields instance credentials. Require IMDSv2 everywhere.
- **`"Action": "*", "Resource": "*"`** or `AdministratorAccess` on workload roles. Scope actions and resources; use Access Analyzer to trim.
- **Public S3 buckets or ACL-based sharing**: keep Block Public Access on and front content with CloudFront.
- **One account for everything**: no blast-radius control and no clean guardrails. Use Organizations.
- **Single AZ or single NAT in production**: an AZ outage takes the system down. Spread across AZs; weigh NAT cost against availability.
- **Using SDK v2 (`aws-sdk`)**: end-of-support since 2025-09-08. Migrate with `aws-sdk-js-codemod` and v3 modular clients.
- **Creating SDK clients inside handlers or per request**: loses connection reuse and slows cold paths.
- **No retention on logs, no budgets**: silent cost growth. Set `RetentionInDays`, Budgets and anomaly detection.
- **Enabling encryption later**: RDS, EBS and EFS encryption is set at creation. Decide up front.
- **NAT for S3 and DynamoDB traffic**: use free gateway endpoints.
- **Trusting tenant ID from the request body for authorization**: derive it from the verified identity and enforce it on every read and write.
- **Console-only changes**: drift and unreviewable history. Change via code.

## 16. References

- [references/iam-and-security.md](references/iam-and-security.md): policy anatomy and evaluation, trust policies (including GitHub OIDC), permission boundaries, SCP and RCP patterns, Identity Center, Access Analyzer, secrets handling, KMS, IMDSv2 rollout, detection services.
- [references/networking.md](references/networking.md): VPC and subnet design, CIDR planning, egress patterns and NAT, endpoints, security groups and NACLs, connectivity (peering, Transit Gateway, PrivateLink), DNS, load balancers.
- [references/compute-and-data-choices.md](references/compute-and-data-choices.md): Lambda, ECS/Fargate, EKS, EC2 selection; S3, RDS/Aurora, DynamoDB, caching and messaging choices; DR strategies; cost levers and Savings Plans; SDK and CDK notes.
- Official docs: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html , https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html , https://docs.aws.amazon.com/organizations/latest/userguide/ , https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/ , https://docs.aws.amazon.com/cdk/v2/guide/
