---
name: cicd-expert
description: >-
  Designs secure, fast CI/CD pipelines with GitHub Actions and the GitHub platform: build-once-promote artifacts, caching, test sharding, environments and approvals, blue/green and canary deployments, SLSA provenance and artifact attestations, OIDC federation to cloud providers, least-privilege permissions, script-injection and pull_request_target defenses, action pinning, rulesets and branch protection, CODEOWNERS, Dependabot, secret scanning, CodeQL and the gh CLI. Absorbs the former github-actions-expert and github-expert skills. Use when writing or reviewing workflows, reusable workflows, composite actions, deployment pipelines or GitHub repository security settings. Not for Dockerfile content (use docker-expert), cloud resource design (use aws-expert, terraform-expert), Git history operations (use git-expert) or SBOMs, artifact signing and provenance (use supply-chain-security-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# CI/CD Expert

This skill covers pipeline design and its implementation on GitHub: workflow structure, runners, caching and sharding, artifact promotion across environments, deployment strategies, supply-chain controls, and the repository settings that enforce them. It absorbs the former github-actions-expert skill (workflow syntax and security, in a dedicated reference) and the former github-expert skill (rulesets, CODEOWNERS, repository security features, gh CLI, in a second reference).

> Verified against GitHub Actions with actions/checkout v7.0.1, setup-node v7.1.0, cache v6.1.0, upload-artifact v7.0.2, download-artifact v8.0.2, attest v4.2.2, aws-actions/configure-aws-credentials v6.3.0, github/codeql-action v4.39.1, hosted images ubuntu-24.04 (`ubuntu-latest`) and ubuntu-26.04, GitHub CLI 2.103.x, cosign 3.1.x and SLSA specification v1.2 (2026-10).

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

- Covered: pipeline architecture, GitHub Actions workflows, reusable workflows and composite actions, runners, caching, matrices and sharding, environments and approvals, deployment strategies, release automation, artifact attestations and provenance, OIDC to AWS, Azure and Google Cloud, secrets in CI, branch protection and rulesets, CODEOWNERS, Dependabot, secret scanning and push protection, CodeQL, the gh CLI.
- Not covered: Dockerfile and image build internals (docker-expert), cloud resource design (aws-expert, terraform-expert), Kubernetes rollout manifests (kubernetes-expert), Git history operations (git-expert), test design (unit-testing-expert, e2e-testing-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Pipeline shape | Commit stage (lint, unit tests, build) then artifact stage (build once, version, sign) then promotion through environments with the same artifact |
| Runners | `ubuntu-latest` is Ubuntu 24.04; `ubuntu-26.04`, `ubuntu-24.04-arm`, `ubuntu-slim`, `windows-latest` (Server 2025), `macos-latest` (macOS 26 arm64) are hosted labels; self-hosted runners only for private networks and only on trusted triggers |
| Token | `GITHUB_TOKEN` is per job; set `permissions:` explicitly (scopes include `contents`, `pull-requests`, `packages`, `id-token`, `attestations`, `artifact-metadata`, `security-events`); unlisted scopes become `none` once any scope is listed |
| Triggers | `pull_request` (unprivileged for forks), `push`, `merge_group`, `workflow_dispatch`, `workflow_call`, `schedule`, `release`; `pull_request_target` and `workflow_run` are privileged |
| OIDC | Jobs with `id-token: write` get a short-lived JWT that a cloud role trusts, replacing stored cloud keys |
| Attestations | `actions/attest` creates signed SLSA build provenance, SBOM or custom attestations; verify with `gh attestation verify` |
| Pinning | Full-length commit SHA with a version comment; Dependabot keeps SHAs current; an opt-in workflow dependency lockfile (`.github/workflows/actions.lock`, `gh actions-lock`) exists on github.com plans |
| Rulesets | Repository or organization rules: pull request reviews, status checks, signed commits, linear history, merge queue, required workflows, code scanning results |
| Repository security | Secret scanning with push protection, Dependabot alerts and version updates, CodeQL, dependency review, private vulnerability reporting, immutable releases |
| Limits | Matrix up to 256 jobs per run; repository cache 10 GB default and entries unused for 7 days are evicted; workflow file up to 500 KB; job timeout default 360 minutes |

## 3. Workflow

1. Define the delivery goal: environments, who approves, rollback expectation, target deployment frequency, compliance needs.
2. Draw the pipeline: commit checks, one build that produces versioned artifacts, then promotion steps; list which job needs which secret or cloud role.
3. Write workflows with `permissions: {}` or `contents: read` at top level and grant more per job.
4. Add caching, concurrency and path filters to keep feedback under about ten minutes.
5. Authenticate to clouds with OIDC; scope the cloud role by repository, environment and branch claims.
6. Attest and sign build outputs; verify the attestation (or signature) at deploy time.
7. Protect the repository: ruleset on the default branch, required status checks, CODEOWNERS for workflows and deploy configuration, environment protection rules.
8. Lint workflows (actionlint, zizmor) in CI; run Dependabot for actions and dependencies.
9. Observe: duration, flake rate, queue time and deployment success; fix the slowest or flakiest step first.

## 4. Decision Rules

- Build once, promote the same artifact (image digest, package checksum) through test, staging and production; never rebuild per environment. Configuration differences come from environment-scoped variables and secrets.
- Trunk-based flow with short-lived branches and a merge queue suits frequent delivery; use release branches only when several versions are supported.
- Deployment strategy: rolling for stateless services with backward-compatible changes; blue/green for fast rollback and schema-compatible releases; canary (percentage or header-based) when you can measure error rate and latency automatically; feature flags to decouple deploy from release. Database changes follow expand, migrate, contract so old and new code both work.
- Reusable workflow (`workflow_call`) when sharing whole jobs, secrets handling and environments across repositories; composite action when sharing a sequence of steps inside a job. A reusable workflow runs as its own jobs, so it can set `environment`, `permissions` and `runs-on` and receive secrets; a composite action is a list of steps and receives everything as inputs.
- Hosted runners by default; self-hosted or larger runners for private network access, special hardware or heavy builds. Never attach persistent self-hosted runners to public repositories.
- Use `pull_request` for untrusted code (forks). Use `pull_request_target` or `workflow_run` only for metadata tasks (labeling, commenting) that never check out or execute pull request code.
- OIDC for every cloud deploy; a stored cloud access key is a fallback only when the provider cannot federate, and then lives in an environment secret with reviewers.
- Pin third-party actions to a full commit SHA; GitHub-owned and in-house actions may use a major tag if the organization accepts the risk, but pinning everything is simpler to audit.
- Prefer squash or rebase merge on trunk for linear history; require status checks and at least one review from someone other than the last pusher.
- Choose a monorepo build strategy by size: path filters and per-package jobs first, then a build graph tool (Nx, Turborepo, Bazel) when path filters stop scaling.

## 5. Coding Standards

- Name workflows and jobs clearly (`CI`, `Release`; jobs `lint`, `test`, `build`, `deploy`); required status checks reference job names, so keep them stable.
- Top-level `permissions:` minimal; job-level `permissions:` add only what the job needs.
- Add `timeout-minutes` to every job; add `concurrency` with `cancel-in-progress: true` for CI on pull requests and `false` for deployments.
- Use `actions/checkout` with `persist-credentials: false` unless the job pushes.
- Never interpolate `${{ inputs.* }}`, `${{ github.event.* }}`, branch names, PR titles or any user-controlled value inside `run:`. Pass it through `env:` and reference the quoted shell variable (`"$PR_TITLE"`). For `actions/github-script`, read values from `process.env`, not from template expressions in the script body.
- Set `shell: bash` explicitly for multi-line scripts: it runs with `-e -o pipefail`, while the implicit default shell applies only `-e`. Add `set -u` when unset variables should fail.
- Pin runners to a label you intend (`ubuntu-24.04`) when reproducibility matters; `ubuntu-latest` moves.
- Extract scripts longer than about 15 lines into repository scripts that can be run and tested locally.
- Declare `defaults.run.working-directory` for monorepo packages rather than `cd` in every step.
- Keep secrets out of logs: GitHub masks registered secrets only, so never echo derived values; use `::add-mask::` for generated values.

## 6. Project Structure

```
.github/
├── workflows/
│   ├── ci.yml              # PR and push checks
│   ├── release.yml         # build, attest, promote
│   ├── codeql.yml          # or use default setup
│   └── _reusable-test.yml  # workflow_call; underscore marks internal use
├── actions/
│   └── setup-app/action.yml   # composite action shared by workflows
├── dependabot.yml
├── CODEOWNERS
└── rulesets/               # optional: JSON exported for review, applied via gh api
scripts/
├── ci/                     # scripts called from workflows; runnable locally
└── deploy/
```

## 7. Design Patterns

- **Pipeline as stages**: `lint` and `test` in parallel, `build` after both, `deploy-staging` after build, `deploy-production` after staging with an environment approval.
- **Build once, promote**: the build job uploads an artifact or pushes an image by digest; later jobs consume the identical output and verify its attestation.
- **Matrix and sharding**: `strategy.matrix` for OS and runtime versions, plus shard indexes (`--shard=1/4`) to split slow suites; merge coverage or reports in a final job.
- **Reusable workflow library**: a central repository exposes `ci-node.yml`, `deploy-aws.yml` with typed inputs; callers pass inputs and select secrets explicitly (`secrets: inherit` only within one organization-owned trust boundary).
- **Environment gates**: `environment: production` with required reviewers, wait timer, branch restriction and environment-scoped variables; OIDC `sub` includes the environment name so the cloud role is only assumable from that gate.
- **Progressive delivery**: shift traffic gradually (load balancer weights, Argo Rollouts, Flagger, feature flags) with automated analysis and rollback; see [references/supply-chain.md](references/supply-chain.md) for verification at deploy time.
- **GitOps promotion**: CI opens a pull request that bumps an image digest in a deployment repository; a controller applies it; the pull request is the approval record.
- **Scheduled maintenance**: `schedule` workflows for dependency refresh, stale cleanup and security scans, with `workflow_dispatch` for manual runs.
- Detailed Actions syntax, reusable workflows, composite actions and matrices: [references/github-actions.md](references/github-actions.md). Repository settings, rulesets, CODEOWNERS and gh CLI: [references/github-platform.md](references/github-platform.md).

## 8. Best Practices

- Keep the main branch always releasable; fail fast with cheap checks first.
- Make pipelines deterministic: lockfile installs (`npm ci`, `pip install --require-hashes`), pinned tool versions, pinned base images, no network downloads without checksums.
- Treat flaky tests as defects: quarantine with a tracking issue and a deadline, never blanket retries.
- One source of truth per concern: build logic in scripts or the build tool, pipeline YAML only orchestrates.
- Version everything the pipeline produces (semantic version plus commit SHA) and keep release notes automated from merged pull requests.
- Use environments and variables for configuration; keep secrets minimal and short-lived.
- Document the rollback command next to every deploy job and test it periodically.
- Use `workflow_dispatch` inputs with `type: choice` or `environment` for manual operations instead of free-form strings.
- Publish test and coverage reports as artifacts or job summaries (`$GITHUB_STEP_SUMMARY`) to cut debugging time.

## 9. Performance

- Cache dependencies through the setup actions (`actions/setup-node` with `cache: npm`, `setup-python` with `cache: pip`) or `actions/cache` keyed on lockfile hashes; restore keys fall back to partial hits.
- Docker layers: buildx with `cache-from`/`cache-to` (registry or `type=gha`) and a multi-stage Dockerfile; see docker-expert.
- Run independent jobs in parallel, shard slow test suites, and use `needs` only for real dependencies.
- Use `paths` and `paths-ignore` filters or a change-detection job to skip unaffected packages; remember required checks must still report (use a final aggregate job).
- Cancel superseded runs with `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }` for CI.
- Choose runner size by measurement: larger runners cost more per minute but can be cheaper per build; ARM runners are often cheaper for ARM targets.
- The repository cache limit is 10 GB by default and unused entries are evicted after 7 days; avoid caching large build outputs that change every run, and avoid cache keys that include `github.sha`.
- On github.com, the `cache-mode` workflow key can restrict a job to `read` access to caches; low-trust triggers default to read-only for the default-branch cache scope.
- Download artifacts only where needed and keep them small; upload with a short `retention-days`.

## 10. Security

- **Permissions**: set the repository and organization default for `GITHUB_TOKEN` to read-only and grant per job. Jobs that publish need `packages: write`, attest jobs need `id-token`, `attestations` and `artifact-metadata` write.
- **Script injection**: expressions such as `${{ github.event.pull_request.title }}`, `${{ github.head_ref }}` and `${{ inputs.name }}` are substituted into the script text before the shell runs, so attacker-controlled values become code. Put the value in `env:` and use `"$VAR"` in the script. The same applies to `github-script` bodies and to `run:` in composite actions.
- **`pull_request_target` and `workflow_run`**: run with write access and secrets in the base repository context. Do not check out or run pull request code, and do not trust artifacts produced by fork runs. `actions/checkout` v7 refuses to check out fork pull requests in these events unless you opt out, which reduces risk but does not replace design discipline. For public repositories, GitHub documents a default policy that blocks `pull_request_target` (in evaluate mode with enforcement planned for 2026-12-02); check the current policy status.
- **Pinning**: reference third-party actions by full commit SHA (`uses: owner/action@<40-hex-sha> # v1.2.3`), let Dependabot update them, and consider the repository "Require actions to be pinned to a full-length commit SHA" policy or the workflow dependency lockfile where available. Reusable workflows are pinned the same way.
- **OIDC**: restrict the cloud trust policy on `sub` (repository, environment, branch or tag) and `aud`; use separate roles for plan and apply; keep `id-token: write` only on jobs that need it.
- **Secrets**: scope to environments, never print them, never pass to untrusted steps; fork pull requests do not receive them. Rotate on exposure. Prefer OIDC and short-lived tokens over stored credentials.
- **Self-hosted runners**: ephemeral and just-in-time, isolated per job, no public repositories, no shared persistent state.
- **Caches and artifacts**: a poisoned cache or artifact is code execution in later privileged jobs; scope cache writes to trusted triggers and verify artifact attestations before deploying.
- **Workflow change control**: CODEOWNERS for `.github/workflows/` and deployment scripts, and a ruleset that requires review.
- **Supply chain**: SLSA provenance, SBOMs, signed images, dependency review on pull requests, `npm ci` with lockfiles; see [references/supply-chain.md](references/supply-chain.md).

## 11. Testing

- Lint workflows with actionlint (syntax, expression types, shell via shellcheck) and zizmor (security audits such as injection, excessive permissions, unpinned actions) in CI.
- Test shared logic as scripts with ordinary unit tests; keep YAML thin.
- Exercise workflows safely: a sandbox repository, `workflow_dispatch` with a dry-run input, and non-production environments with separate OIDC roles.
- Test reusable workflows from a caller in the same repository (`uses: ./.github/workflows/...`) on pull requests before tagging a release.
- Verify required checks: open a pull request that fails a check and confirm the ruleset blocks merge; confirm skipped path-filtered jobs still satisfy required checks via an aggregate job.
- Rehearse rollback and the break-glass path (admin bypass, manual dispatch) on a schedule.
- Check provenance end to end: `gh attestation verify <artifact> --repo <owner>/<repo>` must succeed on the artifact the deploy job actually downloads.

## 12. Review Checklist

- [ ] Top-level `permissions:` is minimal; jobs add only what they need; default token permission is read-only.
- [ ] No `${{ inputs.* }}` or `${{ github.event.* }}` inside `run:` or script bodies; values pass through `env:`.
- [ ] Third-party actions pinned to full SHAs with version comments; Dependabot covers `github-actions`.
- [ ] Cloud access via OIDC with `sub` and `aud` restrictions; no static cloud keys.
- [ ] `pull_request_target` and `workflow_run` workflows never execute untrusted code.
- [ ] Build once; deploy jobs consume the built artifact by digest and verify its attestation.
- [ ] Production deploys use an environment with reviewers (prevent self-review) and branch restrictions.
- [ ] `timeout-minutes` and `concurrency` set; deployments do not cancel in progress.
- [ ] Caches keyed on lockfiles; no secrets or credentials in cached paths.
- [ ] Default branch is protected by a ruleset with required checks and reviews; CODEOWNERS covers workflows.
- [ ] Secret scanning, push protection, Dependabot alerts and code scanning are enabled.
- [ ] Rollback steps are documented and tested.

## 13. Production Notes

- Action runtimes move: current first-party actions run on Node 24, so self-hosted runners need a recent runner version; major tags in this skill reflect 2026-10 and Dependabot will propose newer ones.
- Hosted image labels change: `ubuntu-latest` currently maps to Ubuntu 24.04 while `ubuntu-26.04` is available; test on the next image before `latest` moves, and move off images marked deprecated in the runner-images repository before they are removed.
- Artifacts: since `upload-artifact` v4 an artifact is immutable and its name must be unique within a run; upgrade `upload-artifact` and `download-artifact` together and read their release notes for breaking changes.
- Protect against outage dependence: a mirror or cache for critical downloads, retries with backoff, and a manual deploy path that does not depend on a single runner pool.
- Track pipeline cost: minutes per workflow, cache hit rate, artifact storage; set retention and budget alerts.
- Use immutable releases and release attestations for published software where the feature is available.
- Record who deployed what: deployment environments, `deployments` API, release notes with commit range, change tickets if required.
- Organization policy: restrict allowed actions (GitHub-owned, verified creators, selected list), require SHA pinning, restrict who can approve workflow runs from forks, and keep workflow permissions read-only by default.

## 14. Examples

CI workflow with least privilege, concurrency, caching, a matrix, and a safe PR-title check (third-party SHAs pinned):

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
  merge_group:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  pr-title:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - name: Validate title
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: |
          printf '%s\n' "$PR_TITLE" | grep -Eq '^(feat|fix|docs|chore|refactor|test)(\(.+\))?: .+' \
            || { echo "PR title must follow Conventional Commits"; exit 1; }

  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        node: [22, 24]
        shard: [1, 2, 3]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: ${{ matrix.node }}
          cache: npm
      - run: npm ci
      - run: npm test -- --shard=${{ matrix.shard }}/3

  ci-ok:                      # single required status check for the ruleset
    if: always()
    needs: [test]
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - env:
          RESULT: ${{ needs.test.result }}
        run: test "$RESULT" = "success"
```

Release: build once, attest, then deploy with OIDC behind an environment, verifying the attestation first:

```yaml
name: Release
on:
  push:
    tags: ["v*"]

permissions: {}

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
      id-token: write
      attestations: write
      artifact-metadata: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: 24
          cache: npm
      - run: npm ci && npm run build && tar -czf app.tgz -C dist .
      - uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-path: app.tgz
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: app
          path: app.tgz
          retention-days: 14

  deploy-production:
    needs: build
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    environment: production          # required reviewers and branch/tag rules live here
    concurrency:
      group: deploy-production
      cancel-in-progress: false
    permissions:
      contents: read
      id-token: write
      attestations: read
    steps:
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
        with:
          name: app
      - name: Verify provenance
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
        run: gh attestation verify app.tgz --repo "$REPO"
      - uses: aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd # v6.3.0
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}   # trust policy pins sub to this environment
          aws-region: ${{ vars.AWS_REGION }}
      - name: Upload release
        env:
          BUCKET: ${{ vars.RELEASE_BUCKET }}
          TAG: ${{ github.ref_name }}
        run: aws s3 cp app.tgz "s3://${BUCKET}/releases/${TAG}/app.tgz"
```

Dependabot for actions and npm with grouping and a cooldown on version updates:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
    groups:
      actions:
        patterns: ["*"]
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
    open-pull-requests-limit: 10
```

## 15. Common Mistakes

- **`${{ github.event.pull_request.title }}` (or `inputs.*`, `head_ref`) inside `run:`**: attacker-controlled text becomes shell code. Pass it via `env:` and quote `"$VAR"`.
- **No `permissions:` block**: relies on repository defaults that may be broader than needed. Set them explicitly.
- **Static cloud keys in secrets**: long-lived and exfiltratable. Use OIDC with restricted `sub`.
- **OIDC trust policy that checks only `aud`**: any repository can assume the role. Constrain `sub`.
- **`pull_request_target` plus checkout of the PR head**: a "pwn request" that runs attacker code with secrets. Use `pull_request`, or split privileged work into a metadata-only workflow.
- **Actions pinned to tags or branches (`@main`, `@v1`)**: tags move. Pin SHAs and let Dependabot update.
- **Rebuilding per environment**: the tested artifact is not the deployed one. Build once and promote by digest.
- **Required checks that never report on skipped paths**: merges block forever. Use an aggregate job that always runs.
- **`cancel-in-progress: true` on deploy jobs**: leaves releases half-applied. Cancel CI only.
- **Cache keys without lockfile hashes or with `github.sha`**: stale or useless caches.
- **Secrets in `echo`/`set -x` output or in artifacts**: masking covers only registered secrets.
- **Self-hosted runners on public repositories**: any pull request can run code on your network.
- **Skipping `timeout-minutes`**: hung jobs run for up to 6 hours.
- **`secrets: inherit` to external reusable workflows**: shares every secret with code you do not own. Pass only named secrets.
- **Unreviewed workflow edits**: no CODEOWNERS or ruleset on `.github/workflows`, so a pull request can add exfiltration steps.

## 16. References

- [references/github-actions.md](references/github-actions.md): workflow syntax essentials, triggers, expressions, permissions, concurrency, matrices, caching, artifacts, reusable workflows, composite actions, environments, runners, debugging, and injection-safe patterns (former github-actions-expert).
- [references/github-platform.md](references/github-platform.md): rulesets and branch protection, CODEOWNERS, pull request settings, merge queue, repository security (secret scanning, push protection, Dependabot, CodeQL), environments, immutable releases, gh CLI and REST recipes (former github-expert).
- [references/supply-chain.md](references/supply-chain.md): SLSA levels, artifact attestations and verification, SBOMs, image signing with cosign, pinning and lockfiles, OIDC trust policies for AWS, Azure and Google Cloud, progressive delivery and rollback.
- Official docs: https://docs.github.com/en/actions , https://docs.github.com/en/code-security , https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets , https://slsa.dev/spec/v1.2/ , https://cli.github.com/manual/
