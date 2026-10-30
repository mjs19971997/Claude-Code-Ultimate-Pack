# Refactoring, Import and State Migration

Config-driven blocks make state changes reviewable: they appear in `terraform plan`, run in every environment that applies the configuration, and leave a record in version control. Use the `terraform state` subcommands only for inspection or for recovery when no block fits.

## `moved` blocks (Terraform 1.1+)

Use when a resource or module changes address but the real object stays the same.

```hcl
# Rename
moved {
  from = aws_iam_role.lambda_role
  to   = aws_iam_role.lambda
}

# count -> for_each migration, one block per instance
moved {
  from = aws_subnet.private[0]
  to   = aws_subnet.private["us-east-1a"]
}
moved {
  from = aws_subnet.private[1]
  to   = aws_subnet.private["us-east-1b"]
}

# Extract into a module
moved {
  from = aws_s3_bucket.logs
  to   = module.logging.aws_s3_bucket.this
}

# Rename a module call
moved {
  from = module.db
  to   = module.payments_db
}
```

Rules:
- The plan must show "has moved to" and no create/destroy for the moved object.
- Keep `moved` blocks until every state that uses the configuration has applied them. In a published module, keep them for at least one major version.
- Chains are allowed (`a -> b`, later `b -> c`); keep the history in order.

## `import` blocks (Terraform 1.5+)

Use to bring existing infrastructure under management through a reviewed plan.

```hcl
import {
  to = aws_route53_zone.main
  id = "Z0123456789ABCDEFGHIJ"
}

# Many objects at once (for_each in import blocks: 1.7+)
locals {
  queues = {
    orders   = "https://sqs.us-east-1.amazonaws.com/123456789012/orders"
    payments = "https://sqs.us-east-1.amazonaws.com/123456789012/payments"
  }
}

import {
  for_each = local.queues
  to       = aws_sqs_queue.this[each.key]
  id       = each.value
}
```

Workflow:
1. Write the `import` blocks only.
2. `terraform plan -generate-config-out=generated.tf` drafts resource blocks for targets that have no configuration yet.
3. Clean the generated code: remove computed and default attributes, replace literals with references and variables, move it into the right file or module.
4. Plan again until it shows only imports and no changes. Apply.
5. Delete the `import` blocks in a later change (they are no-ops once imported, but clutter the code).

Import IDs differ per resource type; the provider documentation lists the format at the bottom of each resource page. Current Terraform versions also support `import` blocks inside child modules; check the docs for your version before relying on it.

## `removed` blocks (Terraform 1.7+)

Use to stop managing an object.

```hcl
# Forget it; the real object stays (handed to another state or tool)
removed {
  from = aws_cloudwatch_log_group.legacy
  lifecycle {
    destroy = false
  }
}

# Remove it and destroy the real object (the default), with a cleanup step
removed {
  from = aws_instance.bastion
  provisioner "local-exec" {
    when    = destroy
    command = "echo 'bastion removed' >> decommission.log"
  }
}
```

Without `destroy = false`, a `removed` block behaves like deleting the resource block: the object is destroyed. Review the plan carefully.

## Splitting a state

Moving resources from one root module to another without destroy:

1. In the target root, add the resource blocks and matching `import` blocks.
2. In the source root, replace the resource blocks with `removed { lifecycle { destroy = false } }`.
3. Apply the source first (forgets the objects), then the target (imports them). Both plans must show no create or destroy.
4. Replace any cross-references with outputs or data sources.

## Backend migration

From DynamoDB locking to S3 native locking:

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "production/payments/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    use_lockfile   = true
    dynamodb_table = "terraform-locks" # keep only while old clients still run
  }
}
```

With both configured, Terraform must acquire both locks. Once every pipeline and engineer uses a version that supports `use_lockfile`, remove `dynamodb_table` and run `terraform init -reconfigure`. The role needs `s3:GetObject`, `s3:PutObject` and `s3:DeleteObject` on the `<key>.tflock` object.

Moving to a different backend: change the `backend` block and run `terraform init -migrate-state`; verify with `terraform plan` (expect no changes) before deleting the old state.

## Recovery commands

- `terraform state list` / `state show ADDRESS`: inspection, safe.
- `terraform state pull > backup.tfstate`: take a copy before any manual change.
- `terraform state rm`, `state mv`, `state push`: emergency only, by one person with the lock held, with a backup, and recorded in the change log.
- Backend object versioning (S3 versioning) is the restore path for a corrupted state.
