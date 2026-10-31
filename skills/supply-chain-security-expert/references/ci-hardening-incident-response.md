# CI Hardening and Incident Response

Hardening GitHub Actions workflows (permissions, injection, dangerous triggers, secrets, caching, runner egress), linting with zizmor 1.31.1, and a runbook for a compromised dependency. Audit names were checked against the zizmor audit documentation (2026-10). General pipeline design belongs to cicd-expert.

## Contents

1. [Permissions](#1-permissions)
2. [Script injection](#2-script-injection)
3. [Dangerous triggers](#3-dangerous-triggers)
4. [Checkout, credentials and caches](#4-checkout-credentials-and-caches)
5. [Secrets and environments](#5-secrets-and-environments)
6. [zizmor](#6-zizmor)
7. [Runner egress control](#7-runner-egress-control)
8. [Compromised dependency runbook](#8-compromised-dependency-runbook)
9. [After the incident](#9-after-the-incident)

## 1. Permissions

```yaml
name: ci
on:
  pull_request:

permissions: {}          # workflow default: nothing

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read     # only what this job needs
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - run: make test
```

- Set `permissions: {}` (or `contents: read`) at workflow level and widen per job. zizmor's `excessive-permissions` reports broad grants and `undocumented-permissions` reports permission blocks that give no reason.
- Typical per-job grants: `id-token: write` (OIDC for signing and trusted publishing), `attestations: write`, `packages: write`, `contents: write` (creating a release), `pull-requests: write` (comments), `security-events: write` (SARIF upload).
- Also set the repository or organisation default for `GITHUB_TOKEN` to read-only in settings so a workflow without a `permissions:` block is safe.
- Scopes of `GITHUB_TOKEN` are limited to the repository; a personal access token or app token is broader. Prefer the built-in token, then a GitHub App token with narrow permissions, then a fine-grained token. Avoid classic PATs.

## 2. Script injection

`${{ ... }}` is expanded before the shell runs, so attacker-controlled text becomes shell source. Attacker-controlled contexts include `github.event.issue.title`, `github.event.pull_request.title`, `github.event.pull_request.body`, `github.head_ref`, `github.event.comment.body`, commit messages and author names, and workflow inputs.

```yaml
# Vulnerable
- run: echo "Title: ${{ github.event.pull_request.title }}"

# Safe: expand into an environment variable, use it as a shell variable
- name: Print title
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: printf 'Title: %s\n' "$PR_TITLE"
```

- Use `"$VAR"`, not `${{ env.VAR }}`, in the script: the latter is still template expansion (stated in the zizmor `template-injection` docs).
- The same rule applies to `actions/github-script` `script:` bodies and to any input that ends up in code. Pass data through `env:` and read `process.env.X`.
- Branch names are attacker-controlled too: `github.head_ref` can contain shell metacharacters.
- Do not write untrusted data to `GITHUB_ENV` or `GITHUB_PATH` (zizmor `github-env`); a value with newlines can inject variables, and a path entry can hijack commands.
- In composite actions and reusable workflows, treat `inputs.*` as untrusted unless every caller is trusted.
- Compare untrusted strings in `if:` conditions with care; zizmor audits `unsound-contains`, `unsound-condition` and `bot-conditions` for patterns that can be spoofed (for example checking `github.actor` against a bot name).

## 3. Dangerous triggers

- `pull_request_target` runs in the base repository context with a write-capable token and access to secrets, even for fork pull requests. It is safe only when the job never checks out, builds or executes the pull request's code or any file it controls. A job that does `actions/checkout` with `ref: ${{ github.event.pull_request.head.sha }}` and then runs a build hands the attacker a privileged shell.
- `workflow_run` runs with base-repo privileges after another workflow; artifacts it downloads from a pull-request workflow are untrusted input. Validate them, do not execute them, and do not trust names or contents of files inside.
- `issue_comment` and `issues` triggers run with base-repo context and take attacker text; keep them to labelling and commenting with minimal permissions.
- zizmor `dangerous-triggers` reports these triggers; fix by switching to `pull_request`, or splitting into an unprivileged workflow that builds and a privileged one that only handles artifacts as data.
- Label-based gating (`if: contains(github.event.pull_request.labels.*.name, 'safe to test')`) is acceptable when only maintainers can add the label, and the code is checked out at the exact commit that was reviewed (use the SHA recorded at labelling time, not a branch name).

## 4. Checkout, credentials and caches

- `actions/checkout` stores the token in the git config by default; set `persist-credentials: false` unless a later step must push. zizmor `artipacked` reports the case where credentials can leak into uploaded artifacts.
- Do not upload the whole workspace (`path: .`) as an artifact; it may contain `.git` with credentials and local files.
- Caches: a cache written by a pull-request workflow can be restored by a privileged workflow if keys collide. Use separate cache keys per trust level, and do not restore caches in release or publish jobs unless it is required (zizmor `cache-poisoning`).
- Self-hosted runners persist state between jobs; use ephemeral runners for untrusted code and never for public-fork pull requests (zizmor `self-hosted-runner`).
- Third-party actions run with the job's permissions and can read its secrets and tokens. Keep the number small, pin them, and read the source of any action in a release job. zizmor `known-vulnerable-actions` checks pinned actions against known advisories in online mode.
- Impostor commits: a SHA that exists only in a fork network can still resolve under the upstream name. Take SHAs from upstream tags and let zizmor `impostor-commit` check in online mode.

## 5. Secrets and environments

- Prefer OIDC to cloud providers and registries over stored secrets. Configure the trust policy on the identity (repository, workflow file, ref or environment), not just the organisation.
- Use GitHub environments for release jobs: required reviewers, branch or tag restrictions, and environment-scoped secrets. A secret that exists only in the `release` environment is not available to jobs on other refs.
- Do not pass `secrets: inherit` to reusable workflows you do not control (zizmor `secrets-inherit`); pass the specific secrets needed. zizmor `overprovisioned-secrets` flags jobs that expose the whole secrets context.
- Never echo a secret or place it in a command line (visible in process lists); pass it through `env:` for the single step that needs it. Masking in logs is a safety net, not a control.
- Review who can edit workflows (CODEOWNERS on `.github/`) and who can create tags that trigger release jobs (tag protection or rulesets).
- Use `use-trusted-publishing`: zizmor reports workflows that publish with a long-lived token where a registry supports trusted publishing.

## 6. zizmor

```bash
uvx zizmor .github/workflows                  # offline audits
pip install zizmor && zizmor --version
export GH_TOKEN=<read-only token from the environment>
zizmor .github/workflows                      # online mode when a token is set
zizmor --offline .github/workflows            # force offline
zizmor --persona pedantic .github/workflows   # more findings (also: auditor)
zizmor --format sarif .github/workflows > zizmor.sarif   # check --help for formats
```

- zizmor 1.31.1 audits workflows, composite actions and Dependabot configuration. Online mode (a `GH_TOKEN`, `GITHUB_TOKEN` or `ZIZMOR_GITHUB_TOKEN` is set) enables audits that call the GitHub API, such as `impostor-commit`, `known-vulnerable-actions`, `ref-confusion` and `stale-action-refs`; `--offline` or `ZIZMOR_OFFLINE` disables them.
- The default persona reports confident findings; `pedantic` and `auditor` add noisier ones. For `template-injection` the pedantic and auditor personas flag every template expansion in code contexts.
- Audits worth knowing: `template-injection`, `unpinned-uses`, `excessive-permissions`, `dangerous-triggers`, `artipacked`, `cache-poisoning`, `github-env`, `secrets-inherit`, `use-trusted-publishing`, `unpinned-images`, `dependabot-cooldown`, `anonymous-definition`, `concurrency-limits`, `obfuscation`, `forbidden-uses`.
- Suppress a finding in the workflow with a comment that carries a reason, or in a `zizmor.yml` config; do not suppress by deleting the audit. Keep suppressions reviewable.
- Run zizmor in CI on pull requests that touch `.github/`, with a pinned version, and make the job fail on findings of the severity you decided to enforce. Where a maintained zizmor action is used, pin it to a SHA like any other.

## 7. Runner egress control

- A compromised dependency or action usually needs the network to exfiltrate secrets or fetch a payload. Restricting runner egress to an allow-list limits the damage.
- StepSecurity `harden-runner` is a commonly used GitHub Action for this: run it first in the job in audit mode to record outbound connections, then switch to block mode with an allow-list of endpoints. Check its documentation for the current inputs, supported runners and licensing of the hosted features.
- Self-hosted or private runners can enforce egress at the network layer (firewall, proxy) with the same allow-list approach.
- Egress rules cannot stop exfiltration through an allowed endpoint (for example a registry you publish to); combine with least privilege.

## 8. Compromised dependency runbook

Use when an advisory, maintainer notice or detection says a package or action you use shipped malicious code. Work in this order; timestamp each step in an incident log.

1. Establish facts: package name, affected versions and time window, the malicious behaviour (credential theft, install script, backdoor), and the indicators (domains, file paths, hashes). Use the registry advisory, GHSA or OSV entry, and vendor write-ups; treat chat rumours as unconfirmed.
2. Find exposure. Search lockfiles in all repositories and branches for the affected versions: `grep` or code search for the package name in `package-lock.json`, `uv.lock`, `go.sum` and similar; `osv-scanner scan -r .` once the advisory is in OSV; query SBOMs you stored (`grype sbom:...`). Check CI logs for the install time window, Dependabot or Renovate PRs that merged, and developer machines that ran an unlocked install.
3. Contain. Block the version: pin to the last good version or remove the package; for npm you can add an `overrides` entry, for pip a constraint, for Go a `replace` or exclusion. Stop auto-merge of dependency PRs. Disable affected workflows or cancel runs. If it is a GitHub Action, pin to a known-good SHA or remove it.
4. Assume secrets exposed to any job or machine that ran the bad version are compromised: repository and organisation secrets, cloud credentials, registry tokens, SSH keys, and the `GITHUB_TOKEN` of those runs. Rotate them, starting with those that can publish or deploy. Prefer revoking over waiting for proof of use.
5. Review what the exposed credentials could do: audit logs for cloud accounts, registry publish events, repository settings changes, new deploy keys or workflow files, new tags or releases, and package versions published by your accounts. If you publish packages, check that no unexpected version appeared.
6. Rebuild and redeploy: build from a clean state using the fixed lockfile on clean runners; do not reuse caches from the affected window (clear them). Redeploy artifacts that included the bad version, found through SBOMs by component and version. Revoke or yank your own artifacts built during the window.
7. Verify: confirm the bad version is absent (`npm ls <pkg>`, `uv tree`, `syft` on the new image), indicators of compromise are absent, and new artifacts carry provenance from the expected workflow.
8. Communicate: notify internal owners and, if your published artifacts were affected, downstream users with specific versions, a verification method and remediation steps. Report to the registry or package maintainers if not already known.

Useful queries:

```bash
git grep -n -E '"?<package>"?.*<bad-version>' -- '*lock*' '*.sum'
npm ls <package> --all
uv tree --package <package>
syft scan registry:ghcr.io/acme/app@sha256:<digest> -o syft-table | grep -i <package>
```

## 9. After the incident

- Write a short timeline: introduction, detection, containment, rotation, recovery, with gaps and decisions noted.
- Find the control that would have limited impact and add it: release-age delay, hash or lockfile enforcement, egress allow-list, narrower secrets (environment-scoped), OIDC instead of tokens, `--ignore-scripts`, SBOM retention for quick queries.
- Keep a current inventory so step 2 takes minutes: SBOMs per release in a searchable store, plus a list of repositories and their ecosystems.
- Add a detection: alert on new install scripts in dependency updates, unexpected outbound connections from CI, and publishes outside the release workflow.
- Rehearse the runbook periodically with a fake advisory and measure time to scope and time to rotate.
