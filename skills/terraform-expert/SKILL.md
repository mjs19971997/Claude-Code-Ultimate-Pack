---
name: terraform-expert
description: >-
  Writes and reviews Terraform (and OpenTofu) HCL: modules, providers, remote state with S3 native locking, variables and validation, lifecycle rules, moved/removed/import blocks, terraform test, drift detection and safe plan/apply workflows. Use when editing .tf, .tfvars, .tftest.hcl or .terraform.lock.hcl files, designing module interfaces, splitting or migrating state, importing existing resources, refactoring addresses without destroy, or fixing plan/validate errors. Not for choosing or designing AWS services themselves (use aws-expert), Kubernetes manifests (use kubernetes-expert), or general CI pipeline design (use cicd-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Terraform Expert

This skill covers infrastructure as code with Terraform and its open-source fork OpenTofu: the HCL language, module design, providers and version pinning, remote state, refactoring with config-driven blocks (`moved`, `removed`, `import`), the native `terraform test` framework, and safe plan/apply workflows. It does not cover which cloud services to choose (see aws-expert), Kubernetes object design (see kubernetes-expert), or the CI system itself beyond the Terraform-specific steps (see cicd-expert).

> Verified against Terraform 1.17.0 and 1.16.x, the hashicorp/aws provider 6.x and OpenTofu 1.13 (2026-10).

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

- HCL authoring: resources, data sources, variables, outputs, locals, modules, expressions, `for_each`, `dynamic` blocks, functions.
- Module design: interfaces, versioning, composition, examples, tests.
- State: remote backends, locking, isolation per environment and component, state migration, refactoring without destroy.
- Lifecycle and validation: `lifecycle`, `precondition`/`postcondition`, `check` blocks, variable `validation`.
- Workflows: plan review, apply with short-lived credentials, drift detection, provider and Terraform upgrades.
- OpenTofu: where it differs and how to stay compatible with both.

## 2. Core Expertise

- **Language.** Blocks (`terraform`, `provider`, `resource`, `data`, `module`, `variable`, `output`, `locals`, `check`, `moved`, `removed`, `import`, `ephemeral`), type constraints (`object({...})` with `optional()` defaults), `nullable`, `sensitive`, `ephemeral` variables and outputs.
- **Meta-arguments.** `count`, `for_each`, `depends_on`, `provider`, `lifecycle`. Lifecycle settings accept only literal values: `prevent_destroy = var.x` or any expression fails validation.
- **Lifecycle arguments.** `create_before_destroy`, `prevent_destroy`, `ignore_changes`, `replace_triggered_by`, `precondition`, `postcondition`, and in current versions `action_trigger` and `destroy` (see the lifecycle docs for your version).
- **Providers.** `required_providers` with source and constraint, provider aliases, passing providers into modules with `providers = { aws = aws.us_east_1 }`, the dependency lock file `.terraform.lock.hcl` (commit it; refresh hashes for every platform with `terraform providers lock -platform=...`).
- **State.** The S3 backend with `use_lockfile = true` (S3 native locking, introduced as opt-in in Terraform 1.10; DynamoDB locking is now documented as deprecated), GCS, azurerm, HCP Terraform. `terraform state list/show/mv/rm` for inspection and emergencies; prefer config-driven blocks for planned changes.
- **Refactoring blocks.** `moved` (rename or move into a module without destroy), `removed` (forget a resource, optionally `lifecycle { destroy = false }`), `import` (adopt existing objects; `for_each` supported; `terraform plan -generate-config-out=generated.tf` drafts the config).
- **Secrets.** `sensitive` hides values in output but they still land in state. Ephemeral resources and write-only arguments (Terraform 1.11+, provider support required, for example `password_wo` with `password_wo_version`) keep values out of state and plan.
- **Testing.** `terraform test` with `.tftest.hcl` files (1.6+), `command = plan` for unit-style checks, `mock_provider` and `override_resource` (1.7+) to run without credentials, `expect_failures` for validation tests.
- **Drift.** `terraform plan -refresh-only -detailed-exitcode` (exit 2 means drift or changes). `terraform refresh` is a deprecated alias that writes state without review.
- **OpenTofu.** MPL-licensed fork. Mostly compatible HCL; adds features such as client-side state encryption and early variable evaluation. Its features and Terraform's diverge over time, so test a codebase on the binary it will actually run with.

## 3. Workflow

1. **Locate the change.** Which root module (state) does it touch? What is the blast radius of that state? Prefer small states per environment and component.
2. **Read before writing.** `terraform init`, `terraform plan` on a clean tree to confirm there is no pending drift that would be mixed into your change.
3. **Edit HCL.** Reuse existing modules; pin new providers; add `description` and `type` to new variables; add `validation` where invalid input is possible.
4. **Refactor with blocks, not commands.** Renames get a `moved` block, adoptions an `import` block, removals a `removed` block, so the change is reviewed in the plan.
5. **Static checks.** `terraform fmt -recursive`, `terraform validate`, `tflint`, and a policy scanner (Checkov, Trivy config scanning or similar).
6. **Test.** `terraform test` for modules; plan-only runs with mocks in every PR, apply-mode runs against a sandbox account on a schedule or before release.
7. **Plan review.** Save the plan (`-out=tfplan`), review creates/updates/destroys and every `-/+` replacement. Any unexpected destroy blocks the change.
8. **Apply the saved plan** with short-lived credentials (OIDC), one apply at a time per state.
9. **Verify** with a follow-up plan that shows no changes; schedule drift detection for the state.

## 4. Decision Rules

- **Separate states over workspaces** for environments that need different access, backends or approval gates. CLI workspaces suit identical, short-lived copies (feature environments).
- **`for_each` over `count`** for anything with an identity. Use `count` only for a conditional single instance (`count = var.enabled ? 1 : 0`).
- **`moved`/`import`/`removed` blocks over `terraform state mv/import/rm`.** Blocks are reviewed in the plan and replayed safely in every environment; commands are invisible, one-off state edits.
- **Protecting prod data:** lifecycle settings cannot vary by variable. Combine an argument-level guard that can (`deletion_protection = var.environment == "production"`) with `prevent_destroy = true` in the module or root that only production uses. Do not try to template `prevent_destroy`.
- **Write-only arguments or managed secrets over `sensitive` alone** when the provider supports them (for RDS, `manage_master_user_password = true` or `password_wo`).
- **`ignore_changes` only for attributes another system owns** (autoscaler-managed `desired_count`, tags added by a service). Never to hide drift you do not understand.
- **Terragrunt or a thin wrapper** only when many near-identical roots exist and plain `tfvars` plus modules become repetitive; native Terraform first.
- **Terraform or OpenTofu:** pick one per codebase and pin it. Choose OpenTofu when the license matters or you need its specific features; otherwise follow the organization's standard.
- **`-target` only for recovery.** It produces partial plans that hide dependencies.

## 5. Coding Standards

- Files per module: `versions.tf`, `variables.tf`, `main.tf` (or files per concern), `outputs.tf`, `README.md`, `examples/`, `tests/`.
- Names: `snake_case` for resources, variables, outputs, locals. Use `this` or `main` for the single resource of its type in a module. Do not repeat the type in the name (`aws_s3_bucket.logs`, not `aws_s3_bucket.logs_bucket`).
- Every variable has `type` and `description`; constrain with `validation`. Use `optional()` attributes in object types instead of many loose variables.
- Every output has `description`; mark secrets `sensitive = true` (or `ephemeral = true` where supported).
- Version constraints: reusable modules declare a minimum and major bound (`version = ">= 6.0, < 7.0"`); root modules pin with `~>` and commit `.terraform.lock.hcl`. Set `required_version` in both.
- Module sources: registry modules with a `version`; Git sources with an immutable `?ref=v1.4.2` tag.
- Prefer data sources and remote outputs over hard-coded IDs; keep data sources out of hot loops.
- Keep `locals` for derived values used more than once; do not hide simple attributes behind locals.
- Default tags through the provider (`default_tags` in the AWS provider) rather than repeating a `tags` map on every resource.

## 6. Project Structure

```
infra/
├── modules/
│   └── rds-postgres/
│       ├── versions.tf
│       ├── variables.tf
│       ├── main.tf
│       ├── outputs.tf
│       ├── README.md
│       ├── examples/basic/main.tf
│       └── tests/
│           └── plan.tftest.hcl
├── live/
│   ├── staging/
│   │   └── payments/
│   │       ├── backend.tf        # key = "staging/payments/terraform.tfstate"
│   │       ├── providers.tf
│   │       ├── main.tf           # module calls only
│   │       ├── terraform.tfvars
│   │       └── .terraform.lock.hcl
│   └── production/
│       └── payments/
└── .tflint.hcl
```

## 7. Design Patterns

- **Thin roots, versioned modules.** Roots wire modules together and hold environment values; modules hold the logic. Upgrading an environment means bumping one module version.
- **One state per environment and component.** Network, data stores and applications in separate states so a bad apply cannot touch everything; share values through outputs (`terraform_remote_state` or SSM parameters).
- **Config-driven refactoring.** Rename with `moved`, adopt with `import`, hand off with `removed { lifecycle { destroy = false } }`. Keep the blocks until every environment has applied them, then delete them in a later release.
- **Guardrails in code.** `validation` for inputs, `precondition` for assumptions about data sources, `postcondition` for guarantees about results, `check` blocks for continuous assertions that warn instead of failing.
- **Plan as artifact.** CI produces a saved plan, reviewers approve that plan, the apply job consumes exactly that plan.
- **Drift as an alert.** Scheduled refresh-only plans notify; humans decide whether to codify or revert the drift.

## 8. Best Practices

- Run `fmt`, `validate`, `tflint` and a policy scanner before every plan in CI.
- Review every replacement (`-/+`) in a plan; check which attribute forces it.
- Use `create_before_destroy` for resources that must not have a gap (certificates, launch templates) and make names unique to allow it.
- Keep provider configuration in roots only; modules receive providers, never configure them.
- Prefer `default_tags` plus a small set of per-resource tags.
- Pin module versions per environment so staging can run a new version before production.
- Document each module: purpose, inputs, outputs, an example and upgrade notes (generate the tables with `terraform-docs`).
- Upgrade one thing at a time: Terraform version, then providers, then modules, each with a clean plan.

## 9. Performance

- Large states plan slowly and lock widely; split by component when plans exceed a few minutes.
- `-parallelism=N` (default 10) trades speed for provider API rate limits; lower it when you see throttling.
- `-refresh=false` speeds up a re-plan when you just refreshed; never use it for the plan you apply.
- Avoid data sources that list large collections in modules used many times.
- Cache providers in CI with `TF_PLUGIN_CACHE_DIR` and a committed lock file.

## 10. Security

- No static cloud keys in CI: use OIDC federation to a role scoped to the repository and branch or environment.
- Separate plan and apply roles: the plan role is read-only plus state read/lock; the apply role is used only on the protected branch with an approval gate.
- State contains secrets. Encrypt the backend (SSE-KMS for S3), block public access, enable versioning, restrict who can read it, and log access.
- Keep secrets out of state with write-only arguments, ephemeral resources or service-managed secrets; otherwise treat the state as secret material.
- Never commit `*.tfvars` files with secrets, `.terraform/` or local state; commit `.terraform.lock.hcl`.
- `terraform force-unlock` only after confirming no apply is running.
- Scan plans as well as code (policy as code on `terraform show -json tfplan` with OPA/Conftest or Sentinel on HCP Terraform).

## 11. Testing

- **Unit-style:** `terraform test` with `command = plan` and `mock_provider` for variable validation, naming, conditional resources and outputs. No credentials, runs in every PR.
- **Validation tests:** `expect_failures = [var.environment]` to prove that bad input is rejected.
- **Integration:** `command = apply` runs in a sandbox account; Terraform destroys test resources at the end of the file. Run on schedule or before a module release.
- **Policy:** Checkov, tflint rulesets, Conftest on the JSON plan.
- **Upgrade tests:** plan every environment with the new Terraform or provider version and expect no changes.
- Terratest (Go) remains an option when tests must call real endpoints after apply.

## 12. Review Checklist

- [ ] `fmt`, `validate`, `tflint`, scanner pass; `terraform test` passes for touched modules.
- [ ] Plan reviewed; no unexpected destroy or replacement; plan saved and applied as-is.
- [ ] `required_version` set; providers constrained; lock file committed and updated deliberately.
- [ ] Variables typed, described and validated; outputs described; secrets `sensitive` or write-only.
- [ ] Lifecycle arguments use literals only; production data stores have `prevent_destroy = true` and service-level deletion protection.
- [ ] Renames use `moved`, adoptions `import`, removals `removed`; no unreviewed `state` commands.
- [ ] `for_each` keys are stable and known at plan time.
- [ ] Backend encrypted, versioned, locked with `use_lockfile = true` (DynamoDB only during migration).
- [ ] No hard-coded account IDs, AMIs or secrets; module sources pinned.
- [ ] Refactoring: duplicated resources extracted to modules; `count` with identities migrated to `for_each` with `moved` blocks; deprecated `terraform refresh` replaced by refresh-only plans.

## 13. Production Notes

- One apply at a time per state: backend locking plus CI concurrency groups.
- Production applies require an approval on the saved plan; the apply job must fail if the plan is stale.
- Keep a runbook for lock recovery, state restore from backend versioning, and provider rollback (revert lock file and module version, then plan).
- Track plan duration and drift counts per state; long plans signal a state that should be split.
- After incidents where people changed the console, run a refresh-only plan, then codify or revert.

## 14. Examples

### Example 1: Backend and module with literal lifecycle and validated input

```hcl
# live/production/payments/backend.tf
terraform {
  required_version = "~> 1.17.0"
  backend "s3" {
    bucket       = "acme-tfstate-prod"
    key          = "production/payments/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

# modules/rds-postgres/variables.tf
variable "name" {
  description = "Identifier prefix for the instance and related resources."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,40}$", var.name))
    error_message = "name must be 2-41 chars: lowercase letters, digits, hyphens."
  }
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging or production."
  }
}

variable "postgres_major_version" {
  description = "PostgreSQL major version, e.g. \"17\". Check RDS for supported versions."
  type        = string
  default     = "17"
}

variable "subnet_ids" {
  description = "Private subnet IDs for the DB subnet group."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups attached to the instance."
  type        = list(string)
}

# modules/rds-postgres/main.tf
resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_db_parameter_group" "this" {
  name   = "${var.name}-pg${var.postgres_major_version}"
  family = "postgres${var.postgres_major_version}" # e.g. postgres17; MySQL uses mysql8.0

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "this" {
  identifier                  = var.name
  engine                      = "postgres"
  engine_version              = var.postgres_major_version
  instance_class              = "db.m7g.large"
  allocated_storage           = 100
  storage_encrypted           = true
  username                    = "app_admin"
  manage_master_user_password = true # secret lives in Secrets Manager, not in state
  db_subnet_group_name        = aws_db_subnet_group.this.name
  parameter_group_name        = aws_db_parameter_group.this.name
  vpc_security_group_ids      = var.security_group_ids
  multi_az                    = var.environment == "production"
  backup_retention_period     = var.environment == "production" ? 30 : 7
  deletion_protection         = var.environment == "production" # expressions are fine here
  skip_final_snapshot         = var.environment != "production"
  final_snapshot_identifier   = "${var.name}-final"
  copy_tags_to_snapshot       = true

  lifecycle {
    prevent_destroy = true # literal only (var.* fails validation); this module is for long-lived databases
  }
}
```

### Example 2: Refactoring without destroy

```hcl
# The resource was renamed and moved into a module.
moved {
  from = aws_s3_bucket.logs_bucket
  to   = module.logging.aws_s3_bucket.this
}

# Adopt buckets created by hand; draft config with
# terraform plan -generate-config-out=generated.tf
import {
  for_each = toset(["acme-prod-assets", "acme-prod-exports"])
  to       = aws_s3_bucket.managed[each.key]
  id       = each.key
}

resource "aws_s3_bucket" "managed" {
  for_each = toset(["acme-prod-assets", "acme-prod-exports"])
  bucket   = each.key
}

# Hand the legacy queue to another team's state without deleting it.
removed {
  from = aws_sqs_queue.legacy
  lifecycle {
    destroy = false
  }
}
```

### Example 3: Plan-only test with a mocked provider

```hcl
# modules/rds-postgres/tests/plan.tftest.hcl
mock_provider "aws" {}

variables {
  name               = "payments"
  subnet_ids         = ["subnet-aaa", "subnet-bbb"]
  security_group_ids = ["sg-123"]
}

run "production_is_protected" {
  command = plan
  variables {
    environment = "production"
  }
  assert {
    condition     = aws_db_instance.this.multi_az && aws_db_instance.this.deletion_protection
    error_message = "Production must be Multi-AZ with deletion protection."
  }
}

run "rejects_unknown_environment" {
  command = plan
  variables {
    environment = "prod"
  }
  expect_failures = [var.environment]
}
```

## 15. Common Mistakes

- **Expressions in lifecycle.** `prevent_destroy = var.environment == "production"` fails with "Variables may not be used here". Use a literal plus an argument such as `deletion_protection` that accepts expressions.
- **Wrong parameter group family.** Families are engine plus major version (`postgres17`, `mysql8.0`); string-building `"${var.engine}15"` produces invalid families like `mysql15`.
- **DynamoDB-only locking on new backends.** Use `use_lockfile = true`; keep `dynamodb_table` only while older clients still run, then remove it.
- **`terraform state mv` for renames.** Invisible in review and must be repeated per environment; use `moved`.
- **`count` over a list of named things.** Removing one item shifts every index and recreates resources; use `for_each` and migrate with `moved` blocks.
- **Secrets in variables and state.** `sensitive = true` only masks output. Use write-only arguments, ephemeral resources or service-managed secrets, and protect the state.
- **Local or shared state.** Local state cannot be locked or shared; one state for all environments puts everything in one blast radius.
- **`terraform refresh` for drift.** It updates state without a review; use `plan -refresh-only`.
- **Unpinned providers or no lock file.** A new major version arrives on the next `init`; commit the lock file and use bounded constraints.
- **Configuring providers inside modules.** Blocks `for_each`/`count` on the module and makes removal impossible; pass providers in.
- **Apply without a saved plan.** What was reviewed and what is applied can differ.

## 16. References

- [references/refactoring-and-import.md](references/refactoring-and-import.md): `moved`, `removed`, `import` blocks, config generation, state splitting and backend migration.
- [references/testing.md](references/testing.md): `terraform test` in depth, mocks, overrides, apply-mode integration tests and CI layout.
- [references/ci-workflows.md](references/ci-workflows.md): plan/apply/drift jobs with OIDC, saved plans, concurrency and OpenTofu notes.
