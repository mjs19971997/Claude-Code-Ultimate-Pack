# Terraform in CI: Plan, Apply and Drift

This file covers the Terraform-specific steps of a pipeline. Runner setup, reusable workflows, branch protection and general GitHub Actions hardening belong to the cicd-expert skill.

## Principles

- Cloud credentials come from OIDC federation, never from stored access keys.
- Two roles per environment: a plan role (read-only plus state read and lock) usable from pull requests, and an apply role trusted only for the protected branch and the deployment environment.
- One run at a time per state: backend locking plus a CI concurrency group.
- The apply step applies a saved plan file produced in the same pipeline, never a fresh `terraform apply -auto-approve` without a plan.
- Untrusted values (branch names, PR titles, workflow inputs) never go straight into `run:` scripts; pass them through `env:` and quote them.
- Pin actions; prefer full commit SHAs for third-party actions.

## IAM trust policy for the apply role (AWS)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:acme/infra:environment:production"
        }
      }
    }
  ]
}
```

The `sub` claim for a job that uses `environment: production` is `repo:<owner>/<repo>:environment:production`, so only jobs gated by that environment can assume the role. The plan role can trust `repo:acme/infra:pull_request`.

## Pull request plan

```yaml
# .github/workflows/terraform-plan.yml
name: terraform-plan
on:
  pull_request:
    paths: ["live/production/payments/**", "modules/**"]
permissions:
  contents: read
  id-token: write
concurrency:
  group: tf-plan-production-payments-${{ github.event.pull_request.number }}
  cancel-in-progress: true
jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: live/production/payments
    steps:
      - uses: actions/checkout@v7
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: arn:aws:iam::123456789012:role/tf-plan-production
          aws-region: us-east-1
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.17.0
          terraform_wrapper: false
      - run: terraform fmt -check -recursive
      - run: terraform init -input=false -lockfile=readonly
      - run: terraform validate
      - run: terraform plan -input=false -lock-timeout=5m -out=tfplan
      - name: Publish plan to job summary
        run: |
          {
            echo '### Plan: production/payments'
            echo
            terraform show -no-color tfplan | sed 's/^/    /'   # indented = code block
          } >> "$GITHUB_STEP_SUMMARY"
```

Plans can contain sensitive values that are not marked sensitive. If the repository is public or many people can read job logs, publish only `terraform show -json tfplan | jq '.resource_changes[] | {address, actions: .change.actions}'` instead of the full plan.

## Apply on merge

```yaml
# .github/workflows/terraform-apply.yml
name: terraform-apply
on:
  push:
    branches: [main]
    paths: ["live/production/payments/**", "modules/**"]
permissions:
  contents: read
  id-token: write
concurrency:
  group: tf-apply-production-payments
  cancel-in-progress: false
jobs:
  apply:
    runs-on: ubuntu-latest
    environment: production        # required reviewers gate this job
    timeout-minutes: 60
    defaults:
      run:
        working-directory: live/production/payments
    steps:
      - uses: actions/checkout@v7
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: arn:aws:iam::123456789012:role/tf-apply-production
          aws-region: us-east-1
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.17.0
          terraform_wrapper: false
      - run: terraform init -input=false -lockfile=readonly
      - run: terraform plan -input=false -lock-timeout=5m -out=tfplan
      - run: terraform show -no-color tfplan >> "$GITHUB_STEP_SUMMARY"
      - run: terraform apply -input=false tfplan
```

This applies a plan made seconds earlier from the merged commit. If reviewers must approve the exact plan file, split plan and apply into two jobs, pass the plan file between them as an artifact, and put the environment gate on the apply job; or use HCP Terraform / a dedicated runner (Atlantis, Spacelift, env0) that stores and gates plans natively.

## Scheduled drift detection

```yaml
# .github/workflows/terraform-drift.yml
name: terraform-drift
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
jobs:
  drift:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        stack: [staging/payments, production/payments]
    steps:
      - uses: actions/checkout@v7
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: arn:aws:iam::123456789012:role/tf-plan-readonly
          aws-region: us-east-1
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: 1.17.0
          terraform_wrapper: false
      - name: Refresh-only plan
        id: drift
        working-directory: live/${{ matrix.stack }}
        run: |
          terraform init -input=false -lockfile=readonly
          set +e
          terraform plan -refresh-only -detailed-exitcode -input=false -lock=false
          code=$?
          set -e
          echo "exitcode=$code" >> "$GITHUB_OUTPUT"
          if [ "$code" -eq 1 ]; then exit 1; fi
      - name: Notify on drift
        if: steps.drift.outputs.exitcode == '2'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          STACK: ${{ matrix.stack }}
        run: |
          payload=$(jq -n --arg s "$STACK" '{text: ("Terraform drift detected in " + $s)}')
          curl -fsS -X POST -H 'Content-Type: application/json' -d "$payload" "$SLACK_WEBHOOK_URL"
```

Exit codes of `-detailed-exitcode`: 0 no changes, 1 error, 2 changes present. The drift job reads only (`-lock=false` avoids blocking a running apply; drop it if you need a consistent snapshot).

## OpenTofu

- Binary `tofu`, same subcommands (`tofu init/plan/apply/test`). Setup action: `opentofu/setup-opentofu`.
- Registry: `registry.opentofu.org` mirrors most providers under the same addresses.
- State is compatible when migrating from the Terraform version the OpenTofu release documents as its compatibility baseline; check the migration guide for your exact versions before switching, and switch one state at a time.
- Do not run both binaries against the same state.
