# IAM and Security

Reference for identity, guardrails, secrets, encryption and detection on AWS. Verified against IAM, Organizations (SCPs, RCPs, declarative policies), EC2 instance metadata and the AWS CLI 2.39.x documentation as of 2026-10. Account IDs below (111122223333) and the organization ID are documentation placeholders.

## 1. Policy anatomy and evaluation

- A policy statement has `Effect`, `Action` (or `NotAction`), `Resource` (or `NotResource`), optional `Principal` (resource and trust policies only) and `Condition`.
- Evaluation: everything is denied by default; an explicit `Deny` in any applicable policy overrides any `Allow`; an `Allow` is needed in an identity-based or resource-based policy. SCPs, RCPs, permission boundaries, session policies and VPC endpoint policies each narrow the maximum; none of them grants access by itself.
- Same-account access is granted by either an identity policy or a resource policy (when the principal is named). Cross-account access needs the grant on both sides.
- Prefer `Resource` ARNs over `"*"`, and prefer conditions over broad actions: `aws:PrincipalOrgID`, `aws:SourceVpce`, `aws:SourceArn`, `aws:SecureTransport`, `aws:MultiFactorAuthPresent`, `aws:RequestedRegion`, `aws:ResourceTag/<key>`, `aws:PrincipalTag/<key>`.
- Attribute-based access control (ABAC): tag principals and resources with the same keys and allow when `aws:PrincipalTag/Project` equals `aws:ResourceTag/Project`; it scales better than listing ARNs.

## 2. Reaching least privilege

1. Start from a narrow template for the job (for example a Lambda role with logs access only), then add actions the code needs.
2. Generate a policy from CloudTrail activity with IAM Access Analyzer policy generation after a test run, then review and tighten resources.
3. Validate in CI: `aws accessanalyzer validate-policy --policy-document file://policy.json --policy-type IDENTITY_POLICY`, and custom policy checks (for example check that a new policy does not grant new access compared with a reference).
4. Enable unused access analysis to find unused roles, keys, passwords and permissions, then remove them.
5. Simulate: `aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names s3:GetObject --resource-arns <arn>`.
6. Review last-accessed information for services and actions before removing permissions.
7. Remove inline admin shortcuts: `AdministratorAccess` and `PowerUserAccess` are for break-glass or sandbox roles only.

Example identity policy for a function that reads one secret, writes one table and nothing else:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOneSecret",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:eu-west-1:111122223333:secret:prod/orders/api-key-*"
    },
    {
      "Sid": "WriteOrders",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:eu-west-1:111122223333:table/orders",
        "arn:aws:dynamodb:eu-west-1:111122223333:table/orders/index/*"
      ]
    }
  ]
}
```

The trailing `-*` on a secret ARN matches the random suffix Secrets Manager appends; the wildcard stays narrow because the name prefix is fixed.

## 3. Roles and trust policies

- Service roles: trust `lambda.amazonaws.com`, `ecs-tasks.amazonaws.com`, `ec2.amazonaws.com` and so on; the permissions policy is separate.
- ECS: the task execution role pulls images and reads secrets for injection; the task role is what the application code uses. Do not merge them.
- EKS: use EKS Pod Identity or IAM roles for service accounts (IRSA) so pods get their own role instead of the node role (kubernetes-expert covers the cluster side).
- Cross-account: the target role trusts the source account (or better, a specific role ARN as principal); third-party access adds `sts:ExternalId`.
- Confused deputy: when an AWS service acts on your resource (for example SNS, CloudTrail, S3 log delivery), add `aws:SourceArn` and `aws:SourceAccount` conditions to the resource policy.
- Session duration: roles default to one hour (`MaxSessionDuration` up to 12 hours); keep it short for automation.

Trust policy for GitHub Actions OIDC (workflow side is in cicd-expert). Always constrain `sub`; an `aud` check alone allows any repository:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:example-org/example-repo:environment:production"
        }
      }
    }
  ]
}
```

Create the OIDC identity provider once per account with URL `https://token.actions.githubusercontent.com` and audience `sts.amazonaws.com`. Use separate roles for deploy and read-only plan jobs, and match `sub` to a GitHub environment (`:environment:<name>`) or branch (`:ref:refs/heads/main`) so only protected contexts can assume the role.

## 4. Permission boundaries and delegation

A permissions boundary is a managed policy that caps what an IAM role or user can do, whatever its identity policies say. Use it to let application teams create their own roles safely:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CreateRolesOnlyWithBoundary",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:PutRolePermissionsBoundary", "iam:AttachRolePolicy", "iam:PutRolePolicy"],
      "Resource": "arn:aws:iam::111122223333:role/app-*",
      "Condition": { "StringEquals": { "iam:PermissionsBoundary": "arn:aws:iam::111122223333:policy/AppBoundary" } }
    },
    {
      "Sid": "NeverRemoveOrEditBoundary",
      "Effect": "Deny",
      "Action": ["iam:DeleteRolePermissionsBoundary", "iam:CreatePolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion", "iam:SetDefaultPolicyVersion"],
      "Resource": "arn:aws:iam::111122223333:policy/AppBoundary"
    }
  ]
}
```

Session policies narrow an assumed role further at `AssumeRole` time. Boundaries apply inside one account; SCPs apply across accounts.

## 5. Organizations guardrails

- **SCPs** apply to IAM principals (including the root user) of member accounts, not the management account, and not to service-linked roles. Start with allow-all (`FullAWSAccess`) plus targeted denies; test each in a sandbox OU.
- **RCPs** (resource control policies) set the maximum permissions on supported resources, such as S3, STS, KMS, SQS and Secrets Manager, regardless of who calls; check the current docs for the list of supported services.
- **Declarative policies** enforce a service baseline in the service control plane across the organization (for example EC2 IMDS defaults, block public access for AMIs and snapshots, VPC block public access).
- Management account: keep it nearly empty (billing, Organizations, Control Tower); run workloads and security tooling in other accounts using delegated administrators.

Deny actions outside approved regions (extend the `NotAction` list with the global services you use):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnapprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*", "organizations:*", "account:*", "sts:*", "route53:*", "route53domains:*",
        "cloudfront:*", "budgets:*", "ce:*", "support:*", "waf:*", "wafv2:*", "trustedadvisor:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": { "aws:RequestedRegion": ["eu-west-1", "us-east-1"] },
        "ArnNotLike": { "aws:PrincipalArn": "arn:aws:iam::*:role/OrganizationAdminRole" }
      }
    }
  ]
}
```

RCP that requires TLS for supported resources, regardless of the caller:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceSecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": ["s3:*", "sqs:*", "kms:*", "secretsmanager:*", "sts:*"],
      "Resource": "*",
      "Condition": { "BoolIfExists": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

Root user hygiene: enable organization-level centralized root access management (root credentials management and root sessions through `sts:AssumeRoot`) so member accounts have no root passwords, keys or MFA devices to lose; use `AssumeRoot` for the rare root-only task.

## 6. IAM Identity Center and workforce access

- Connect an external identity provider (SCIM provisioning) or use the built-in directory; assign groups to permission sets per account, not individuals.
- Permission sets become IAM roles in each account; sessions default to one hour and can be up to 12 hours.
- CLI: `aws configure sso`, `aws sso login --profile prod-readonly`, `aws sts get-caller-identity --profile prod-readonly`. SDKs read the same SSO profile, so no keys land on disk.
- Provide a read-only permission set for everyone, a deploy role only through the pipeline, and an elevated break-glass set with approval and alarms.

## 7. Secrets and encryption

Where secrets may live: Secrets Manager or Parameter Store SecureString, read at runtime through the workload's role. Where they must not: EC2 user-data, AMIs and images, repository code, `.env` files committed or copied into images, plaintext CloudFormation/CDK parameters, Lambda or task environment values containing the secret itself, client-side bundles.

| Need | Choice |
|---|---|
| Automatic rotation (RDS, Redshift, DocumentDB, custom Lambda rotators), cross-region replication, resource policies | Secrets Manager |
| Plain configuration plus a few secrets, hierarchy by path, lower cost, tight KMS control | Parameter Store (`SecureString`, advanced tier for larger values and policies) |
| RDS or Aurora master password | Let RDS manage it in Secrets Manager (`ManageMasterUserPassword`), so it is rotated and never in IaC state |
| Container needs a secret at start | ECS task definition `secrets` with `valueFrom` (the value is injected at launch; fetch through the SDK instead when you need rotation without restart) |
| Lambda needs a secret often | Parameters and Secrets Lambda Extension (local cache) or SDK call with module-level caching |

CloudFormation dynamic reference (value resolved at deploy time, not stored in the template): `{{resolve:secretsmanager:prod/orders/db:SecretString:password}}`. Prefer passing the secret name or ARN to the application.

KMS basics: customer managed keys have key policies (the root of authorization), grants and aliases; enable automatic rotation (`aws kms enable-key-rotation --key-id <id>`); use separate keys per data classification or account boundary; S3 bucket keys reduce KMS request volume for SSE-KMS; multi-Region keys support cross-region replication of encrypted data.

S3 baseline bucket policy statement (TLS only):

```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::example-bucket", "arn:aws:s3:::example-bucket/*"],
  "Condition": { "Bool": { "aws:SecureTransport": "false" } }
}
```

## 8. IMDSv2 rollout

- IMDSv2 requires a session token (`PUT` for a token, then token header on requests), which defeats most SSRF-based credential theft.
- Account and Region default for new launches: `aws ec2 modify-instance-metadata-defaults --http-tokens required --region eu-west-1` (inspect with `aws ec2 get-instance-metadata-defaults`). Declarative policies set it organization-wide.
- Existing instances: `aws ec2 modify-instance-metadata-options --instance-id i-0123456789abcdef0 --http-tokens required --http-endpoint enabled`.
- Launch templates: `MetadataOptions: { HttpTokens: required, HttpEndpoint: enabled, HttpPutResponseHopLimit: 1 }`; use hop limit 2 only for containers that need to reach metadata through a bridge network.
- Find remaining IMDSv1 callers with the CloudWatch metric `MetadataNoToken` per instance, update SDKs and agents, then enforce.
- Enforce at launch with the SCP shown in SKILL.md (`ec2:MetadataHttpTokens` equals `required`).
- Amazon Linux 2023 images are designed for IMDSv2; confirm other AMIs with `aws ec2 describe-images` (the `ImdsSupport` field).

## 9. Detection and audit

| Service | Setup |
|---|---|
| CloudTrail | One organization trail, all regions, management events plus selected data events (S3, Lambda), log file validation, delivered to the Log Archive account bucket with object lock or restricted deletes; CloudTrail Lake or Athena for queries |
| GuardDuty | Enable organization-wide with a delegated administrator and auto-enable; turn on protection plans that match your services (S3, EKS, runtime, malware, Lambda) |
| AWS Config | Recorder in all accounts and regions you use; conformance packs or managed rules (public S3, unencrypted volumes, IMDS, root MFA); aggregator in the Audit account |
| Security Hub | Aggregate findings, enable the relevant security standards, route high severity to on-call |
| IAM Access Analyzer | External access analyzer per region (organization zone of trust) and unused access analyzer |
| Inspector, Macie | Vulnerability scanning for EC2, ECR and Lambda; sensitive data discovery in S3 |
| Budgets and Cost Anomaly Detection | Alerts to the same channels; spikes often signal compromised credentials |

Response basics: isolate with a deny-all inline policy or security group swap, preserve evidence (snapshots, logs), rotate secrets, and review CloudTrail for the credential's actions.

## 10. Data perimeter summary

- Identity perimeter: only trusted identities access your resources (`aws:PrincipalOrgID` on resource policies and RCPs).
- Resource perimeter: your identities access only trusted resources (SCP conditions on `aws:ResourceOrgID`).
- Network perimeter: access only from expected networks (`aws:SourceVpc` or `aws:SourceVpce`, VPC endpoint policies).
- Apply all three to sensitive data stores and test with Access Analyzer before enforcing.
