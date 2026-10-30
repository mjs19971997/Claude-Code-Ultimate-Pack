# Testing Terraform Modules

The native test framework (`terraform test`, Terraform 1.6+) runs `.tftest.hcl` files against a module. Each file creates its own ephemeral state; resources created by apply-mode runs are destroyed when the file finishes. Mocking (`mock_provider`, `override_resource`, `override_data`) arrived in 1.7. Verified against Terraform 1.17.1 and OpenTofu 1.13.5 (2026-10).

## 1. Layout

```
modules/rds-postgres/
├── main.tf
├── variables.tf
├── outputs.tf
└── tests/
    ├── unit.tftest.hcl          # command = plan, mocked provider
    └── integration.tftest.hcl   # command = apply, real sandbox account
```

`terraform test` discovers files in the module root and in `tests/`. Run one file with `terraform test -filter=tests/unit.tftest.hcl`.

## 2. Building blocks

- `variables { ... }` at file level sets defaults; a `variables` block inside a `run` overrides them.
- `run "name" { ... }` executes in order. `command = plan` checks logic without creating anything; `command = apply` (the default) creates real resources.
- `assert { condition = ...; error_message = "..." }`: any number per run; conditions can reference resources, data sources, outputs and earlier runs (`run.setup.vpc_id`).
- `expect_failures = [var.name, resource.aws_x.y]`: the run passes only if those checkable objects fail (validation, preconditions, postconditions, check blocks).
- `module { source = "./tests/setup" }` inside a run executes a helper module instead of the module under test, for fixtures such as a VPC.
- `providers = { aws = aws.sandbox }` selects provider configurations defined in the test file.

## 3. Unit tests with mocks

```hcl
# tests/unit.tftest.hcl
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }
}

variables {
  name               = "orders"
  environment        = "staging"
  subnet_ids         = ["subnet-aaa", "subnet-bbb"]
  security_group_ids = ["sg-123"]
}

run "staging_is_single_az" {
  command = plan
  assert {
    condition     = aws_db_instance.this.multi_az == false
    error_message = "Staging should not pay for Multi-AZ."
  }
}

run "family_matches_major_version" {
  command = plan
  variables {
    postgres_major_version = "16"
  }
  assert {
    condition     = aws_db_parameter_group.this.family == "postgres16"
    error_message = "Parameter group family must follow the major version."
  }
}

run "name_validation" {
  command = plan
  variables {
    name = "Orders_DB"
  }
  expect_failures = [var.name]
}
```

Notes:
- Mocked computed attributes get generated placeholder values; use `mock_resource` / `mock_data` defaults or `override_resource` when a test depends on a specific value (an ARN format, an ID used in a policy).
- Assertions on values unknown at plan time fail in plan mode; assert on inputs and derived values, or switch that run to apply mode.

## 4. Integration tests

```hcl
# tests/integration.tftest.hcl
provider "aws" {
  region = "us-east-1"
}

run "setup_network" {
  module {
    source = "./tests/setup"
  }
}

run "creates_instance" {
  variables {
    name               = "tftest-orders"
    environment        = "dev"
    subnet_ids         = run.setup_network.subnet_ids
    security_group_ids = [run.setup_network.security_group_id]
  }
  assert {
    condition     = startswith(aws_db_instance.this.endpoint, "tftest-orders.")
    error_message = "Endpoint should start with the identifier."
  }
}
```

Run integration tests in a dedicated sandbox account with OIDC credentials, on a schedule or before tagging a module release. The `prevent_destroy = true` in the module under test blocks the test's own cleanup; integration tests for such modules need a test-only wrapper or `override_resource`, or must accept manual cleanup. Decide this explicitly.

## 5. In CI

1. `terraform fmt -check -recursive`
2. `terraform init -backend=false` then `terraform validate`
3. `tflint --recursive`
4. `terraform test -filter=tests/unit.tftest.hcl` in every PR (no credentials)
5. Integration files on schedule or release, with a timeout and a cleanup job that deletes anything tagged by the test run.

## 6. Other tools

- Terratest (Go): apply, then exercise endpoints (HTTP checks, SQL connections), then destroy.
- Conftest/OPA on `terraform show -json tfplan`: policy over the full plan.
- Checkov, Trivy (config scanning), tflint rulesets: static checks on HCL.
