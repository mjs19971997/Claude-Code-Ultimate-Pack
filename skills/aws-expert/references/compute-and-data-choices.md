# Compute and Data Choices

Reference for picking compute, storage, database, messaging and disaster-recovery options, reducing cost, and using the SDKs and CDK. Verified against AWS SDK for JavaScript v3 3.1161.0, boto3 1.43.x, AWS CLI 2.39.x, aws-cdk-lib 2.275.0, and the Lambda runtimes page (nodejs24.x, python3.14) as of 2026-10. Quotas change; confirm limits in Service Quotas before design sign-off.

## 1. Compute selection

| Option | Best for | Watch for |
|---|---|---|
| Lambda | Event handlers, APIs with spiky load, glue code, short batch (max 15 minutes per invocation) | Cold starts, 15-minute cap, payload size limits, connection management to databases |
| ECS on Fargate | Containers without managing servers: web services, workers, scheduled tasks | Per-vCPU/GB pricing at steady high load, no host access, ephemeral storage limits |
| ECS Express Mode | One container image to a load-balanced HTTPS service with autoscaling and a URL, resources created in your account | Opinionated; changing generated resources outside Express Mode can interfere with it |
| ECS on EC2 | Steady containers where Savings Plans and bin-packing beat Fargate, GPUs, special instance types | You patch and scale the hosts |
| EKS | Teams that need the Kubernetes API, ecosystem tooling or portability (see kubernetes-expert) | Control plane cost, upgrade cadence, cluster operations |
| EC2 | Licensed or legacy software, kernel or hardware access, steady-state with commitments | Patching, scaling and AMI lifecycle |
| Batch | Queue-based batch and HPC on Spot | Job design and retry semantics |

General rules: start serverless-first; move to containers when you hit runtime limits; move to EC2 for cost or control only when measured. Use Graviton (arm64) where dependencies allow.

## 2. Lambda specifics

- Runtimes: use current managed runtimes (`nodejs24.x`, `python3.14` at the time of writing) and `provided.al2023` for compiled languages; runtime deprecation dates are published and enforced in phases (block create, then block update), so track them.
- Memory 128 MB to 10,240 MB; CPU scales with memory; timeout up to 900 seconds; package as zip or container image.
- Initialize SDK clients, connections and config outside the handler; keep the handler thin.
- Concurrency: reserved concurrency caps and guarantees; provisioned concurrency keeps warm environments; SnapStart reduces start time for supported runtimes.
- Failure handling: asynchronous invocations use on-failure destinations or a DLQ; SQS event sources use partial batch responses (`ReportBatchItemFailures`) and a DLQ on the queue with a visibility timeout longer than the function timeout.
- VPC access: attach only when needed (private databases); egress then needs NAT or endpoints.
- Packaging: bundle with esbuild for Node.js (CDK `NodejsFunction`), use layers sparingly, AWS Lambda Powertools for logging, tracing and idempotency.
- Function URLs: `AWS_IAM` auth or a fronting API Gateway/CloudFront; do not leave a `NONE` auth URL on a sensitive function.

## 3. Containers on ECS and Fargate

- One task definition per deployable; `awsvpc` networking gives each task its own ENI and security group.
- Task role for application permissions, execution role for pulling images and fetching injected secrets.
- Secrets: `secrets: [{ name, valueFrom }]` with a Secrets Manager or Parameter Store ARN; non-secret config in `environment`.
- Deployments: rolling with deployment circuit breaker and rollback, or blue/green through CodeDeploy; health check grace period for slow starts.
- Capacity: Fargate Spot for interruptible workers; scale on ALB request count or queue depth; set CPU and memory per task from measurement.
- Images: ECR with scan on push, immutable tags, lifecycle policies; deploy by digest.
- Logging: `awslogs` or FireLens to CloudWatch Logs with retention set.

## 4. EC2 and Auto Scaling

- Launch templates with the AMI (Amazon Linux 2023 or a hardened custom image), instance profile, IMDSv2 required, encrypted EBS, no SSH key (use SSM Session Manager).
- Auto Scaling groups across at least two AZs with ELB health checks; instance refresh for rolling AMI updates; mixed instances policy to blend Spot and On-Demand.
- Bootstrap through the AMI plus minimal user-data that contains no secrets; fetch configuration and secrets by role at start.
- Patch with SSM Patch Manager or by replacing instances from a new AMI built in a pipeline (EC2 Image Builder or Packer).

## 5. S3 choices

| Topic | Guidance |
|---|---|
| Access | Block Public Access at account and bucket level; bucket policy with TLS-only deny; object ownership `BucketOwnerEnforced` (ACLs disabled); access points for many consumers |
| Encryption | SSE-S3 applies by default to new objects; use SSE-KMS with bucket keys for audit and key control; SSE-C is disabled by default on new buckets since April 2026 |
| Durability and recovery | Versioning, lifecycle rules for noncurrent versions, replication (same or cross region), Object Lock for write-once retention |
| Classes | Standard; Intelligent-Tiering when access is unknown; Standard-IA / One Zone-IA for infrequent access; Glacier Instant, Flexible and Deep Archive for archives (check minimum storage durations and retrieval fees) |
| Public content | CloudFront with origin access control; never public-read buckets |
| Uploads and downloads | Presigned URLs (short expiry, one key, server-generated key, signed content type) or presigned POST with conditions for size limits; multipart uploads for large objects with a lifecycle rule to abort incomplete uploads |

Presigned URL facts: they use the signer's credentials, so they stop working when those credentials expire (role sessions shorten the effective lifetime); anyone with the URL can use it until expiry; scope the signing role narrowly and keep expiry in minutes.

## 6. Databases

| Need | Pick |
|---|---|
| Standard SQL engine, simple operations | RDS (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server) with Multi-AZ |
| Higher throughput, fast failover, up to 15 read replicas, storage autoscaling | Aurora (PostgreSQL or MySQL compatible) |
| Intermittent or unpredictable relational load | Aurora Serverless v2; minimum 0 ACU supports auto-pause (not with RDS Proxy or other proxies holding connections) |
| Single-digit-millisecond key-value or document access at any scale | DynamoDB |
| Caching, sessions, leaderboards | ElastiCache (Valkey, Redis OSS, Memcached) or MemoryDB for durable in-memory |
| Search and log analytics | OpenSearch Service (see elasticsearch-expert for query design) |
| Graph, wide-column, other specialized stores | Neptune (graph), Keyspaces (Cassandra-compatible); for time-series and ledger needs check current service availability first, because some AWS services stop accepting new customers |
| Analytics | Redshift, Athena over S3, Glue; Lake Formation for governance |

Relational operations checklist: encryption at creation, Multi-AZ, automated backups with point-in-time recovery and a tested restore, deletion protection, parameter groups under IaC, managed master password in Secrets Manager, IAM database authentication for applications where supported, RDS Proxy for Lambda or many short connections, minor-version auto upgrade windows, read replicas for read scaling and cross-region DR.

DynamoDB checklist: design from access patterns; choose partition keys with high cardinality; use GSIs for alternate queries; on-demand capacity by default for unknown load, provisioned with auto scaling for steady load; point-in-time recovery on; TTL for expiry; conditional writes for idempotency and optimistic locking; transactions for multi-item atomicity; streams for change data capture; global tables for multi-region active/active; item size limit 400 KB.

## 7. Messaging and integration

- SQS standard (at-least-once, unordered) or FIFO (ordering per message group, deduplication); always configure a DLQ and alarm on its depth; make consumers idempotent.
- SNS topics for fan-out to SQS, Lambda, HTTP; filter policies to reduce consumers' work.
- EventBridge buses for routing between services and SaaS, rules with patterns, Scheduler for cron and one-off schedules, Pipes for point-to-point integrations.
- Step Functions for orchestration with retries, catches and human approval; Express workflows for high-volume short runs.
- Kinesis Data Streams or MSK for ordered streaming with replay.
- API Gateway (REST or HTTP APIs) for managed APIs with authorizers (JWT, IAM, Lambda), throttling, usage plans; AppSync for GraphQL.

## 8. Disaster recovery strategies

| Strategy | RTO / RPO | Pattern |
|---|---|---|
| Backup and restore | Hours / hours | AWS Backup with cross-region and cross-account copies; IaC to rebuild |
| Pilot light | Tens of minutes / minutes | Data replicated, minimal core running, scale up on failover |
| Warm standby | Minutes / seconds-minutes | Scaled-down full stack running in the second region |
| Multi-site active/active | Near zero / near zero | Global tables or Aurora Global Database, Route 53 or Global Accelerator routing |

Rules: choose from business RTO and RPO; test failover and restores on a schedule; keep DR runbooks as code; keep backups in a separate account with vault lock so a compromised workload account cannot delete them.

## 9. Cost levers

- Commitments: Compute Savings Plans cover EC2, Fargate and Lambda usage across families and regions; EC2 Instance Savings Plans trade flexibility for a deeper discount; Database Savings Plans (announced December 2025) cover supported database services such as Aurora, RDS and DynamoDB and cannot be combined with reserved instances for the same usage. Check current coverage and terms on the Savings Plans pages before buying. Buy after right-sizing, cover the steady baseline, not the peak.
- Spot for fault-tolerant, stateless or batch work; diversify instance types and AZs.
- Right-size with Compute Optimizer and CloudWatch metrics; stop idle non-production environments on a schedule.
- Storage: lifecycle policies, Intelligent-Tiering, delete unattached EBS volumes and old snapshots, gp3 instead of gp2.
- Network: avoid NAT for AWS service traffic (endpoints), keep traffic in one AZ where architecture allows, watch inter-region and internet egress, use CloudFront for repeated egress.
- Observability cost: log retention, sampling, metric cardinality.
- Governance: AWS Budgets with alerts per account and tag, Cost Anomaly Detection, cost allocation tags activated in billing, monthly review with the owning teams, Cost Explorer and CUR/Data Exports for analysis.

## 10. SDK and CLI notes

- **JavaScript v3**: `npm install @aws-sdk/client-s3`; `const s3 = new S3Client({ region })`; `await s3.send(new GetObjectCommand(...))`. Packages require Node.js 20 or later. Use `@aws-sdk/lib-storage` `Upload` for multipart, `@aws-sdk/lib-dynamodb` for document marshalling, `@aws-sdk/credential-providers` for explicit providers (`fromSSO`, `fromIni`, `fromTemporaryCredentials`), and `maxAttempts` on the client for retries.
- **v2 to v3 migration**: `aws-sdk` v2 has been end-of-support since 2025-09-08. Run `npx aws-sdk-js-codemod -t v2-to-v3 <paths>` to automate the mechanical parts, then review: v3 uses command objects, modular imports and `Uint8Array`/stream helpers (`transformToString`) on response bodies.
- **boto3**: `session = boto3.Session()`; create clients once (`s3 = session.client("s3")`); paginate with `get_paginator`; waiters for async resources; `botocore.exceptions.ClientError` for service errors and `error.response["Error"]["Code"]`; configure retries and timeouts via `botocore.config.Config(connect_timeout=..., read_timeout=..., retries={"mode": "standard", "max_attempts": 5})`. Resource interfaces are feature-frozen; prefer clients.
- **Credentials chain**: environment, shared config/SSO profile, container credentials, instance profile. Do not export long-lived keys; for local work use `aws sso login`.
- **AWS CLI v2**: `aws configure sso`, `--profile`, `--query` (JMESPath), `--output json|table|text`, `aws sts get-caller-identity` to confirm identity, `aws s3 sync --delete` carefully (preview with `--dryrun`).
- **CDK v2**: `npm install aws-cdk-lib constructs`; CLI `npm install -g aws-cdk` or `npx cdk`; `cdk bootstrap aws://<account>/<region>` once per environment (creates roles and assets bucket; use a custom qualifier or modern bootstrap with trust limited to the pipeline account); `cdk synth`, `cdk diff`, `cdk deploy --require-approval broadening`. Prefer L2 constructs, avoid hardcoded physical names, keep stateful resources in separate stacks with `RemovalPolicy.RETAIN` and termination protection, use `Aspects` or `cdk-nag` for policy checks, and keep `cdk.context.json` in version control.
