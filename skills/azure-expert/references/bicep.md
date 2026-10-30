# Bicep

Reference for writing and deploying Bicep. Verified against Bicep 0.48.x (latest release tag v0.48.1; linter rule names read from the Bicep repository) and Azure CLI 2.91.0 (2026-10). Resource API versions in examples are ones known to exist; the `use-recent-api-versions` linter rule reports when newer ones are available, and the Azure template reference lists current versions.

## Contents

1. [File anatomy](#1-file-anatomy)
2. [Parameters and secrets](#2-parameters-and-secrets)
3. [Modules](#3-modules)
4. [Parameter files](#4-parameter-files)
5. [Validation and deployment](#5-validation-and-deployment)
6. [Deployment stacks](#6-deployment-stacks)
7. [Azure Verified Modules](#7-azure-verified-modules)
8. [Linter configuration](#8-linter-configuration)
9. [Patterns and pitfalls](#9-patterns-and-pitfalls)

## 1. File anatomy

```bicep
targetScope = 'resourceGroup'   // default; also 'subscription', 'managementGroup', 'tenant'

@description('Deployment environment short name.')
@allowed(['dev', 'prod'])
param env string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags applied to every resource.')
param tags object = {}

var suffix = uniqueString(resourceGroup().id)
var storageName = 'st${env}${suffix}'      // 3-24 chars, lowercase letters and digits

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_ZRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
  }
}

output storageId string = storage.id
```

- Use symbolic references (`storage.id`, `storage.name`) instead of `resourceId()` strings so Bicep infers dependencies; add `dependsOn` only when no reference exists.
- `existing` resources read something deployed elsewhere: `resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = { name: vaultName }`. Use `scope:` to point at another resource group (`scope: resourceGroup(subId, rgName)`).
- Loops and conditions: `[for item in items: { ... }]` and `= if (condition) { ... }`. Names inside loops must be unique per item.
- Prefer user-defined types and the `@export()` decorator for shared shapes over untyped `object` parameters.
- Outputs return resource IDs and names, never keys or connection strings.

## 2. Parameters and secrets

```bicep
@secure()
@description('Value stored in Key Vault. Supplied at deploy time, never in the repo.')
param bootstrapSecret string

resource secret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'bootstrap'
  properties: { value: bootstrapSecret }
}
```

- `@secure()` on `string` and `object` parameters keeps values out of deployment history and logs. Do not give secure parameters default values (linter: `secure-parameter-default`).
- Do not put secrets in `.bicepparam` files in source control. Supply them from the environment at deploy time (`readEnvironmentVariable('NAME')` in the parameter file) or avoid them entirely: use managed identity access, Key Vault references, and generated values.
- Passing a secret on the command line (`--parameters bootstrapSecret=...`) exposes it in process lists and shell history. Prefer the environment variable route.
- Never emit secrets from `output` (linter: `outputs-should-not-contain-secrets`). Other resources read secrets at run time through their identity.
- For SQL administrators and VM credentials, avoid passwords: use Entra-only authentication on SQL and SSH keys on Linux VMs.

## 3. Modules

```bicep
module identity 'modules/identity.bicep' = {
  name: 'identity-${env}'
  params: {
    location: location
    tags: tags
    name: 'id-shop-${env}'
  }
}

module app 'modules/app.bicep' = {
  name: 'app-${env}'
  params: {
    location: location
    identityId: identity.outputs.id
  }
}

module vaultAccess 'modules/vault-access.bicep' = {
  name: 'vault-access-${env}'
  scope: resourceGroup(sharedSubscriptionId, sharedRgName)   // different scope
  params: {
    principalId: identity.outputs.principalId
  }
}
```

- One module per concern; modules expose a small parameter surface and outputs for IDs and principal IDs.
- A module deployment `name` should be stable and unique per scope so repeated deployments update it in place.
- A role assignment on a resource in another resource group needs a module whose `scope` is that group.
- Registry modules use `br/public:avm/res/<service>/<resource>:<version>` or `br:<registry>.azurecr.io/<path>:<tag>`. Publish private modules with `az bicep publish --file module.bicep --target br:<registry>.azurecr.io/bicep/<name>:<version>` and restore with `az bicep restore`.
- Template specs (`ts:`) are an alternative when you want Azure-side versioned templates.

## 4. Parameter files

```bicep
// main.prod.bicepparam
using './main.bicep'

param env = 'prod'
param tags = {
  env: 'prod'
  owner: 'platform-team'
  'cost-center': 'cc-1234'
}
param bootstrapSecret = readEnvironmentVariable('BOOTSTRAP_SECRET')
```

- The `using` statement binds the file to a template and gives type checking and completion. Parameters absent from the file fall back to template defaults; required ones must be present.
- `using none` is allowed for parameter files not tied to one template (check the docs for use cases).
- Deploy with `--parameters main.prod.bicepparam`; if you use a `.bicepparam` file you can pass it only once and cannot mix it with other `--parameters` files, though a `KEY=VALUE` override syntax exists for JSON parameter files.
- `az bicep build-params --file main.prod.bicepparam` compiles to JSON for tools that need it.

## 5. Validation and deployment

```bash
az bicep version                      # shows the Bicep CLI that az uses
az bicep upgrade                      # update the az-managed Bicep CLI
az bicep build --file infra/main.bicep
az bicep lint  --file infra/main.bicep

# Preview changes (no changes made)
az deployment group what-if -g rg-shop-dev --parameters infra/main.dev.bicepparam

# Deploy; --what-if previews first, --confirm-with-what-if prompts before applying
az deployment group create -g rg-shop-dev --parameters infra/main.dev.bicepparam \
  --confirm-with-what-if

# Subscription scope (needs --location for deployment metadata)
az deployment sub create --location westeurope --parameters infra/sub.bicepparam
```

- `what-if` shows Create, Modify, Delete, NoChange, Ignore and Deploy; `--result-format` takes `FullResourcePayloads` (default) or `ResourceIdOnly`, and `--exclude-change-types` hides noise. Treat `Delete` and replacement of stateful resources (databases, storage, vaults) as stop signs.
- What-if is a prediction and can miss runtime-only properties; it does not replace a non-production deployment.
- Incremental mode (default) leaves unmentioned resources alone. Complete mode deletes resources in the group that the template omits; use it only on groups that the template fully owns, and prefer a deployment stack for that intent.
- Use `az deployment group validate` for a server-side validation, and `--validation-level` options (see the CLI help) to choose depth.
- `az bicep decompile` converts ARM JSON to Bicep as a starting point; review the output, it is not guaranteed to be complete.
- Experimental features are enabled in `bicepconfig.json` and are for testing only (the Bicep docs say not to use them in production). Examples at this version include `deployCommands`, `localDeploy` and `moduleExtensionConfigs`. Do not rely on them in shared templates.

## 6. Deployment stacks

A deployment stack manages a set of resources as a unit: it tracks what the template deployed, can delete resources removed from the template, and can deny out-of-band changes.

```bash
az stack group create --name stack-shop-prod --resource-group rg-shop-prod \
  --template-file infra/main.bicep --parameters env=prod \
  --action-on-unmanage deleteResources \
  --deny-settings-mode denyWriteAndDelete \
  --deny-settings-excluded-principals "$BREAKGLASS_GROUP_OBJECT_ID" \
  --yes
```

- `--action-on-unmanage` is required: `detachAll` (keep everything, stop managing), `deleteResources` (delete unmanaged resources, keep resource groups) or `deleteAll` (delete unmanaged resources and resource groups). Start with `detachAll` or `deleteResources` and read the stack's output before using `deleteAll`.
- `--deny-settings-mode` is required: `none`, `denyDelete` or `denyWriteAndDelete`. Use `--deny-settings-excluded-principals` and `--deny-settings-excluded-actions` for break-glass accounts and operations.
- The stack help documents template files plus inline or JSON parameters; check the current docs before passing a `.bicepparam` file to `az stack`.
- Stacks exist at resource group (`az stack group`), subscription (`az stack sub`, needs `--location`) and management group scope. `az stack ... delete` applies the unmanage action to everything the stack owns, so confirm what it will remove.
- Deny settings create deny assignments that block even owners; document the excluded principals and the procedure for lifting them.

## 7. Azure Verified Modules

- Azure Verified Modules (AVM) are the Microsoft-maintained module library, published to the public Bicep registry and developed in the `Azure/bicep-registry-modules` repository. Resource modules sit under `avm/res/<provider>/<resource>`, pattern modules under `avm/ptn/...`.
- Reference by pinned version: `module storage 'br/public:avm/res/storage/storage-account:<version>' = { ... }`. Find the current version on the module's page before pinning; do not use a floating reference.
- AVM modules expose parameters such as `roleAssignments`, `privateEndpoints`, `diagnosticSettings`, `lock` and `tags` using a consistent interface, which reduces boilerplate for private networking and RBAC.
- Non-AVM modules have been removed from the public registry per the Bicep modules documentation, so older `br/public:storage/...` references may fail to restore.
- If no AVM module exists for a resource type, write a native resource with the latest stable API version.
- Read a module's inputs before adopting it; defaults may enable or disable features (public access, redundancy) that your policy requires set explicitly.

## 8. Linter configuration

```json
{
  "analyzers": {
    "core": {
      "rules": {
        "use-recent-api-versions": { "level": "warning" },
        "use-recent-module-versions": { "level": "warning" },
        "no-hardcoded-env-urls": { "level": "error" },
        "outputs-should-not-contain-secrets": { "level": "error" },
        "secure-parameter-default": { "level": "error" },
        "secure-secrets-in-params": { "level": "error" },
        "use-secure-value-for-secure-inputs": { "level": "error" },
        "no-unused-params": { "level": "warning" },
        "no-unused-vars": { "level": "warning" },
        "use-stable-resource-identifiers": { "level": "warning" }
      }
    }
  }
}
```

- Rule IDs above correspond to rules shipped in the Bicep repository (UseRecentApiVersion, UseRecentModuleVersions, NoHardcodedEnvironmentUrls, OutputsShouldNotContainSecrets, SecureParameterDefault, SecretsInParamsMustBeSecure, UseSecureValueForSecureInputs, NoUnusedParameters, NoUnusedVariables, UseStableResourceIdentifiers). Run `az bicep lint` to see which IDs your Bicep version reports, and copy IDs from its output.
- Some rules are off by default; the configuration file turns them on or raises their level.
- Put `bicepconfig.json` next to the templates (or higher in the tree); it also defines module registry aliases.

## 9. Patterns and pitfalls

- Deterministic names: `guid(scope.id, principalId, roleId)` for role assignments; `uniqueString(resourceGroup().id)` for global names. A role assignment whose name changes between deployments creates a duplicate and fails with a conflict.
- Role assignments need the target principal to exist; if the identity was just created in the same deployment, reference its `principalId` output so ordering is implied and set `principalType: 'ServicePrincipal'` to avoid replication races.
- Key Vault: set `enableRbacAuthorization: true`, `enableSoftDelete: true`, `enablePurgeProtection: true` and `publicNetworkAccess: 'Disabled'` explicitly; do not depend on API-version defaults.
- Keep environment differences in parameter files (SKU, instance counts, address ranges), not in conditionals scattered through modules.
- Use `@description` on every parameter and output; it is the documentation your colleagues and tools read.
- CI shape: lint and build on pull requests, `what-if` on the target scope, manual approval through a GitHub environment, then deploy. The login step is covered in identity-rbac.md; the pipeline layout belongs to cicd-expert.
