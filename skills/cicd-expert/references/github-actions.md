# GitHub Actions

Reference for writing, securing and debugging GitHub Actions workflows, absorbed from the former github-actions-expert skill. Verified against GitHub Actions on github.com with actions/checkout v7.0.1, setup-node v7.1.0, cache v6.1.0, upload-artifact v7.0.2, download-artifact v8.0.2, attest v4.2.2, docker/build-push-action v7.4.0, docker/login-action v4.7.0, docker/setup-buildx-action v4.4.1, aws-actions/configure-aws-credentials v6.3.0 and the hosted runner images list (2026-10). Third-party action SHAs in examples were resolved from the release tags on that date; refresh them with Dependabot.

## 1. Workflow anatomy

```yaml
name: CI                          # shown in the UI
run-name: CI for ${{ github.ref_name }}   # optional run title (trusted context values only)
on:                               # triggers
  pull_request:
  push:
    branches: [main]
permissions:                      # token scopes for every job unless overridden
  contents: read
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
defaults:
  run:
    shell: bash
env:
  CI: "true"
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - run: make test
```

- Workflow files live in `.github/workflows/*.yml` and run from the commit that triggered them (for `pull_request` that is the merge commit; for `pull_request_target`, `schedule` and `workflow_run` it is the default branch).
- A workflow file larger than 500 KB does not run; move logic into reusable workflows, composite actions or scripts.
- Job-level `if:` accepts an expression without `${{ }}`; status functions are `success()`, `failure()`, `always()`, `cancelled()`.

## 2. Triggers

| Trigger | Notes |
|---|---|
| `push`, `pull_request` | Use `branches`, `tags`, `paths`, `paths-ignore` filters; `pull_request` from forks gets a read-only token and no secrets |
| `merge_group` | Required for merge queue: required checks must run on `merge_group` events too |
| `workflow_dispatch` | Manual run with typed `inputs` (`string`, `boolean`, `choice`, `environment`); treat inputs as untrusted text |
| `workflow_call` | Makes the workflow reusable; typed `inputs`, `secrets`, `outputs` |
| `schedule` | Cron in UTC on the default branch; delayed under load; disabled after 60 days of repository inactivity on public repositories |
| `release`, `create`, `delete` | Release automation; prefer tags with `push.tags` for release builds |
| `workflow_run` | Runs after another workflow; privileged context; treat artifacts from fork runs as untrusted data |
| `pull_request_target` | Base-repository context with secrets and write token; only for metadata tasks (labels, comments), never to build or test PR code |
| `issue_comment`, `issues`, `discussion` | Text from users is attacker-controlled; same injection rules apply |
| `repository_dispatch` | External systems trigger workflows through the API |

Path filters and required checks: a workflow skipped by `paths` does not report its checks, so a required check never completes. Use an always-running aggregate job (see the example in SKILL.md) or `dorny/paths-filter`-style change detection inside the workflow.

## 3. Expressions and contexts

- Contexts: `github`, `env`, `vars`, `secrets`, `inputs`, `needs`, `steps`, `job`, `runner`, `matrix`, `strategy`.
- Functions: `contains`, `startsWith`, `endsWith`, `format`, `join`, `toJSON`, `fromJSON`, `hashFiles('**/package-lock.json')`.
- Dynamic matrix: a job outputs `matrix: ${{ steps.plan.outputs.matrix }}` (JSON from a script), and the next job uses `matrix: ${{ fromJSON(needs.plan.outputs.matrix) }}`.
- Step outputs: write `echo "name=value" >> "$GITHUB_OUTPUT"`; job outputs map step outputs for downstream `needs.<job>.outputs.<name>`.
- Never write untrusted text to `$GITHUB_ENV` or `$GITHUB_PATH` or `$GITHUB_OUTPUT` without sanitizing: a newline in a value can set extra variables, and a controlled `PATH` entry can hijack later commands.
- Use `$GITHUB_STEP_SUMMARY` for Markdown summaries; keep secrets out.

## 4. Permissions

Scopes (read, write or none) include: `actions`, `artifact-metadata`, `attestations`, `checks`, `contents`, `deployments`, `discussions`, `id-token` (write only), `issues`, `models`, `packages`, `pages`, `pull-requests`, `security-events`, `statuses`. When any scope is listed, unlisted scopes become `none`. `permissions: {}` disables all.

Typical grants:

| Job | Permissions |
|---|---|
| Build and test | `contents: read` |
| Comment on a PR | `pull-requests: write` |
| Push a container image to GHCR | `contents: read`, `packages: write` |
| Attest build output | `contents: read`, `id-token: write`, `attestations: write`, `artifact-metadata: write` |
| Deploy with OIDC | `contents: read`, `id-token: write` |
| Upload SARIF (CodeQL) | `contents: read`, `security-events: write` |
| Dependency review | `contents: read`, `pull-requests: write` (for comments) |

Set the repository and organization default for the workflow token to read-only so a missing `permissions:` block is not a privilege grant. Fork pull requests cannot receive write scopes through `permissions:` unless an admin enables sending write tokens to fork workflows (leave it off).

## 5. Script injection and safe patterns

Expressions inside `run:` are replaced with their text before the shell parses the script. An issue title, branch name, PR body, commit message, label, or workflow input can therefore contain shell syntax. Safe pattern:

```yaml
- name: Greet
  env:
    NAME: ${{ inputs.name }}            # value never becomes part of the script text
    BRANCH: ${{ github.head_ref }}
  run: |
    printf 'Hello %s on %s\n' "$NAME" "$BRANCH"
```

Rules:
- Pass every user-influenced value through `env:` (or action `with:` inputs) and reference it as a quoted variable.
- In `actions/github-script`, read `process.env.NAME`; do not put `${{ ... }}` inside the `script:` body.
- In composite actions, pass inputs to scripts through `env:` as well; `${{ inputs.x }}` inside a composite `run:` has the same flaw.
- Validate with allow-lists (`case`, regex) before using a value as a path, ref or command argument; reject path separators and `..` when the value names a file or directory.
- Do not rely on `contains()`/`if:` checks for sanitization.
- Trusted values (`github.run_id`, `github.sha`, matrix entries defined in the file) are safe to interpolate, but the habit of using `env:` for everything is simpler to audit.

Never use these patterns: checking out a pull request head in a `pull_request_target` or `workflow_run` workflow and then executing it; `eval` of any input; `curl | sh` of unpinned URLs; the deprecated `set-output` and `save-state` workflow commands (use the `$GITHUB_OUTPUT` and `$GITHUB_STATE` files).

## 6. Concurrency, timeouts and retries

- `concurrency.group` serializes or cancels runs sharing a key; CI: `cancel-in-progress: true`; deploys: `false` so the active deploy finishes and one newer run waits.
- `timeout-minutes` at job and step level; the default job limit is 360 minutes.
- `continue-on-error` on a step or a matrix entry for informational checks only.
- Retry network-flaky commands inside the step (`for i in 1 2 3; do cmd && break; sleep 5; done`); avoid blanket workflow re-runs that mask flaky tests.
- `fail-fast: false` on matrices when you want every combination's result.

## 7. Matrices and sharding

```yaml
strategy:
  fail-fast: false
  max-parallel: 6
  matrix:
    os: [ubuntu-24.04, windows-2025]
    node: [22, 24]
    include:
      - os: ubuntu-24.04
        node: 24
        coverage: true
    exclude:
      - os: windows-2025
        node: 22
```

- A matrix generates at most 256 jobs per run.
- `include` adds combinations or extra properties; `exclude` removes combinations.
- Shard slow suites with an index dimension (`shard: [1, 2, 3, 4]`) and the test runner's shard flag; upload per-shard reports with unique names (`report-${{ matrix.shard }}`), then merge in a final job with `actions/download-artifact` `pattern: report-*` and `merge-multiple: true`.
- Matrix values are defined in the workflow file and safe to interpolate; values computed from outputs of untrusted data are not.

## 8. Caching and artifacts

```yaml
- uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('requirements.lock') }}
    restore-keys: |
      pip-${{ runner.os }}-
```

- Prefer the setup actions' built-in caching (`cache: npm|pip|gradle|maven`) over hand-written keys.
- Keys include the OS and a lockfile hash; `restore-keys` provide partial hits; never include `github.sha`.
- Caches are branch-scoped: runs can restore from the current branch, the base branch and the default branch. Total repository cache defaults to 10 GB and entries unused for 7 days are evicted.
- Splitting `actions/cache/restore` and `actions/cache/save` lets a trusted workflow write the cache while untrusted ones only read. Low-trust triggers (fork pull requests, issue comments) get read-only access to the default-branch cache scope by default; the github.com-only `cache-mode` key (`read`, `write`, `write-only`, `none`) can restrict a workflow or job further.
- Artifacts share files between jobs and with humans: `actions/upload-artifact` (inputs include `name`, `path`, `retention-days`, `if-no-files-found`, `include-hidden-files`, `archive`) and `actions/download-artifact` (`name`, `pattern`, `merge-multiple`, `path`, `run-id` with a token for cross-run downloads). Artifact names must be unique within a run; hidden files (dot-directories such as `.next`) are excluded unless `include-hidden-files: true`.
- Never upload credentials or `.git/config` with a persisted token in an artifact: use `persist-credentials: false` on checkout when the workspace is uploaded.

## 9. Reusable workflows

Callee (`.github/workflows/test-node.yml` in a shared repository):

```yaml
name: Test Node
on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: "24"
      working-directory:
        type: string
        default: "."
    secrets:
      NPM_TOKEN:
        required: false
    outputs:
      coverage:
        description: Coverage percentage
        value: ${{ jobs.test.outputs.coverage }}

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    outputs:
      coverage: ${{ steps.cov.outputs.value }}
    defaults:
      run:
        working-directory: ${{ inputs.working-directory }}
    steps:
      - name: Validate working directory
        working-directory: .
        env:
          WORKDIR: ${{ inputs.working-directory }}
        run: |
          case "$WORKDIR" in /*|*..*) echo "invalid working-directory" >&2; exit 1;; esac
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: ${{ inputs.node-version }}
          cache: npm
          cache-dependency-path: ${{ inputs.working-directory }}/package-lock.json
      - run: npm ci
      - run: npm test -- --coverage
      - id: cov
        run: echo "value=$(node scripts/coverage-pct.js)" >> "$GITHUB_OUTPUT"
```

Caller:

```yaml
jobs:
  test:
    uses: example-org/shared-workflows/.github/workflows/test-node.yml@<full-commit-sha>  # v2.3.0
    with:
      node-version: "24"
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
    permissions:
      contents: read
```

- Callers set `permissions:`; the callee can only keep or reduce them. Nested reusable workflows are allowed; permissions can only be maintained or reduced down the chain.
- Pass secrets by name; `secrets: inherit` forwards all of them and fits only workflows you own inside the same trust boundary.
- A `uses:` on a job cannot be combined with `steps`, and it supports `with`, `secrets`, `needs`, `if`, `strategy` and `permissions`.
- Pin external reusable workflows by full SHA; the lockfile feature does not pin `jobs.<id>.uses` references.
- Reusable workflow inputs are text: apply the same injection rules inside the callee.
- Use a reusable workflow when you need jobs, `environment`, or runner selection; use a composite action for step bundles.

## 10. Composite actions

`.github/actions/setup-app/action.yml`:

```yaml
name: Setup app
description: Install toolchain and dependencies
inputs:
  node-version:
    description: Node.js version
    default: "24"
runs:
  using: composite
  steps:
    - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
      with:
        node-version: ${{ inputs.node-version }}
        cache: npm
    - shell: bash
      run: npm ci
```

- Every `run` step needs an explicit `shell`.
- Composite actions cannot read the `secrets` context; pass secrets as inputs from the calling workflow.
- A composite action in the same repository is referenced as `uses: ./.github/actions/setup-app` after checkout; a local path runs whatever is in the workspace, so avoid it in workflows that check out untrusted code.
- JavaScript actions run on Node 24 at current action majors; Docker container actions work only on Linux runners.

## 11. Environments, variables and secrets

- Environments hold deployment protection rules: required reviewers (up to 6, any one approves; enable **Prevent self-review**), wait timer, deployment branch and tag restrictions, plus environment secrets and variables available only after the gate passes.
- Variables (`vars.*`) are non-sensitive configuration; secrets are encrypted and masked. Scope order: environment over repository over organization for the same name.
- Organization secrets can be limited to selected repositories. Dependabot has its own secret store; fork pull requests receive none.
- `gh secret set NAME --env production` reads the value from stdin or a prompt; do not pass values as command arguments in shared shells.
- Use OIDC instead of cloud secrets (see [supply-chain.md](supply-chain.md)).

## 12. Runners

- Hosted labels (2026-10): `ubuntu-latest` and `ubuntu-24.04`, `ubuntu-26.04`, `ubuntu-24.04-arm`, `ubuntu-22.04`, `ubuntu-slim` (a lighter-weight image for short jobs; check its documentation for limits), `windows-latest` and `windows-2025`, `windows-2022`, `windows-11-arm`, `macos-latest` and `macos-26` (arm64), `macos-26-intel`, `macos-15`. macOS 14 images are marked deprecated. Installed tool versions are listed per image in the `actions/runner-images` repository.
- Larger runners are an organization feature for heavy jobs.
- Self-hosted: run ephemeral runners (one job, then discard), keep them in private repositories only, isolate network access, and restrict the runner group to specific repositories and workflows.
- `runs-on` can use a group or label set; a job waiting for a self-hosted runner is cancelled after 24 hours.

## 13. Container build and push with attestation

```yaml
jobs:
  image:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
      artifact-metadata: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1
      - uses: docker/login-action@81c6f93d4bc991e510b342a00b419b3bb4efc5c6 # v4.7.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: build
        uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: .
          push: true
          tags: ghcr.io/example-org/app:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: mode=max
          sbom: true
      - uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-name: ghcr.io/example-org/app
          subject-digest: ${{ steps.build.outputs.digest }}
          push-to-registry: true
```

Registry image names must be lowercase. Deploy by the digest in `steps.build.outputs.digest`, not by a mutable tag. Dockerfile guidance lives in docker-expert.

## 14. Debugging and operations

- Re-run with debug logging from the UI, or set `ACTIONS_STEP_DEBUG` and `ACTIONS_RUNNER_DEBUG` as secrets or variables to `true`.
- CLI: `gh run list`, `gh run view <id> --log-failed`, `gh run watch`, `gh run rerun <id> --failed`, `gh workflow run ci.yml -f key=value`, `gh run download <id>`.
- Locally lint with `actionlint` and audit with `zizmor` before pushing; local runners such as `act` approximate hosted runners and miss OIDC, caches and several contexts.
- Use `workflow_dispatch` on a branch to test deploy logic against a non-production environment.
- Look at the job's `GITHUB_STEP_SUMMARY`, the annotations tab, and the run's timing view to find slow steps.
- Workflow commands: `::error file=a.js,line=1::msg`, `::group::title` / `::endgroup::`, `::add-mask::value`.
