# GitHub Platform

Reference for protecting repositories and organizing collaboration on GitHub, absorbed from the former github-expert skill. Verified against GitHub rulesets and repository security documentation, the GitHub REST API description for rulesets, and GitHub CLI 2.103.x (2026-10). Features marked github.com-only are unavailable on GitHub Enterprise Server; check the docs for your plan and version.

## 1. Branch protection and rulesets

Rulesets are the current mechanism; classic branch protection rules still exist. Rulesets can target branches, tags or pushes, stack (the most restrictive result wins), run in `evaluate` mode before enforcement, and exist at repository or organization level.

Common rules for the default branch:

| Rule | Purpose |
|---|---|
| Restrict deletions, block force pushes (`non_fast_forward`) | History cannot be erased |
| Require a pull request | At least one approval, dismiss stale approvals on new commits, require review from code owners, require approval of the most recent push by someone other than the pusher, require conversation resolution, optionally limit merge methods |
| Require status checks | Named checks (stable job names) that must pass; optionally require branches to be up to date (`strict`) |
| Require signed commits | Verified signatures on all commits |
| Require linear history | Squash or rebase merges only |
| Require merge queue | Serialized, tested merges (`merge_group` event) |
| Require deployments to succeed | A named environment must have a successful deployment before merge |
| Require workflows to pass | Organization-enforced workflows from a central repository |
| Require code scanning results | CodeQL (or other tool) results with alert thresholds |
| Restrict file paths, extensions, size | Keep generated files, large binaries or secrets-prone files out |

Bypass actors (`actor_type`: `RepositoryRole`, `Team`, `User`, `Integration`, `OrganizationAdmin`, `DeployKey`; `bypass_mode`: `always`, `pull_request`, `exempt`) should be few, auditable, and prefer `pull_request` mode so bypass still leaves a record. Avoid admin bypass for routine merges.

Create a ruleset from JSON with the gh CLI (`gh api --method POST repos/OWNER/REPO/rulesets --input ruleset.json`):

```json
{
  "name": "protect-default-branch",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [ { "context": "ci-ok" } ]
      }
    }
  ]
}
```

Notes:
- `required_status_checks.context` is the check name as shown on the pull request (the job `name`, or `name / job` for reusable workflows); pin the source app with `integration_id` so another app cannot report the same name.
- Start in `"enforcement": "evaluate"` to see what would be blocked, then switch to `active`.
- Inspect: `gh ruleset list`, `gh ruleset view <id>`, `gh ruleset check <branch>`.
- Tag rulesets protect release tags from deletion or movement; combine with immutable releases.
- Review the audit log and ruleset insights for bypasses.

## 2. CODEOWNERS

- File location: `.github/CODEOWNERS`, `CODEOWNERS` or `docs/CODEOWNERS`; patterns follow gitignore syntax; the last matching pattern wins.
- Owners are users or teams with write access: `/infra/ @example-org/platform`, `*.sol @example-org/security`.
- Always cover `/.github/workflows/`, deployment configuration, IAM and infrastructure code, and the CODEOWNERS file itself.
- Enforcement needs the ruleset or branch protection setting "require review from code owners"; without it CODEOWNERS only requests reviews.
- Keep teams small and real; an owner team of everyone provides no review signal. Validate with the CODEOWNERS errors view in the repository.

```
# .github/CODEOWNERS
*                       @example-org/maintainers
/.github/               @example-org/platform
/infra/                 @example-org/platform @example-org/security
/services/payments/     @example-org/payments
```

## 3. Pull request workflow and merge settings

- Repository settings: allow only the merge methods the team uses; default squash message from the PR title and description; delete head branches on merge; enable auto-merge; use a merge queue for busy branches.
- Pull request templates (`.github/pull_request_template.md`) and issue forms (`.github/ISSUE_TEMPLATE/*.yml`) standardize input.
- Keep pull requests small, linked to an issue, with a test plan; use draft pull requests for early feedback.
- Review expectations: reviewers check design, correctness, tests, security and operability; automation handles style (code-review-expert covers technique).
- gh CLI: `gh pr create --fill`, `gh pr checks --watch`, `gh pr merge --auto --squash --delete-branch`, `gh pr view --web`, `gh pr review --approve`.
- `gh repo edit --enable-auto-merge --delete-branch-on-merge --enable-squash-merge --enable-rebase-merge=false` sets merge options from scripts (the `--enable-*` flags take a value to turn a setting off).
- Auto-merge merges when requirements are met; it does not bypass them.
- Merge queue: enable `merge_group` in CI workflows, keep checks fast, and set the grouping and build limits that match your CI capacity.

## 4. Repository security features

| Feature | Notes |
|---|---|
| Secret scanning | Detects known credential formats in code, issues, pull requests and more; alerts notify the committer or admins; custom patterns available |
| Push protection | Blocks pushes that contain detected secrets; contributors can bypass with a reason unless delegated bypass controls require approval; enable at repository or organization level (`gh repo edit --enable-secret-scanning --enable-secret-scanning-push-protection`) |
| Dependabot alerts | Vulnerable dependency notifications from the advisory database; triage with auto-triage rules |
| Dependabot security updates | Automatic pull requests that fix alerted dependencies |
| Dependabot version updates | `.github/dependabot.yml`; ecosystems include `github-actions`, `npm`, `pip`, `docker`, `gomod`, `cargo`, `terraform`; `groups` merge related updates; `cooldown` delays version updates after release (default cooldown is 3 days for version updates, not security updates) |
| Dependency review | `actions/dependency-review-action` fails pull requests that add vulnerable or disallowed-license dependencies |
| Code scanning with CodeQL | Default setup (no workflow file) or advanced setup (`github/codeql-action/init`, `autobuild` if needed, `analyze`) with `security-events: write`; run on pull requests and a schedule |
| Private vulnerability reporting and security advisories | Researchers report privately; maintainers publish advisories and request CVEs |
| Code security configurations | Organization-level bundles that enable these features across many repositories consistently |
| Immutable releases | Published release assets and tag cannot be changed or deleted; a release attestation is created automatically; publish as draft, attach assets, then publish |

Minimal advanced CodeQL workflow:

```yaml
name: CodeQL
on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: "17 3 * * 1"
permissions:
  contents: read
jobs:
  analyze:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    permissions:
      contents: read
      security-events: write
    strategy:
      matrix:
        language: [javascript-typescript]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: github/codeql-action/init@9b3254085494b55a0f7c4c2b3d2d52cc712ce370 # v4.39.1
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/analyze@9b3254085494b55a0f7c4c2b3d2d52cc712ce370 # v4.39.1
        with:
          category: "/language:${{ matrix.language }}"
```

## 5. Actions policies at repository and organization level

- Restrict allowed actions: GitHub-owned, verified creators, or an explicit allow list.
- Turn on the policy that requires actions to be pinned to a full-length commit SHA where available; GitHub also documents a workflow dependency lockfile with a "Require lockfile" protection on github.com plans.
- Set workflow token default permissions to read-only and disable "Allow GitHub Actions to create and approve pull requests" unless a release bot needs it.
- Require approval to run workflows from outside collaborators and first-time contributors.
- Use event policies (for example the default policy for `pull_request_target` on public repositories) and review policy insights before enforcement dates.
- Runner groups bind self-hosted runners to specific repositories.

## 6. Environments and deployments

- Define `staging` and `production` environments with required reviewers (prevent self-review), branch or tag restrictions (for example only `main` or `v*` tags), optional wait timers, and environment secrets and variables.
- Show deployments in the repository by using `environment:` on the job; the deployment record links to the run and commit.
- Pair environments with OIDC role trust on `repo:<owner>/<repo>:environment:<name>` (see [supply-chain.md](supply-chain.md)).
- Custom deployment protection rules (apps) can gate on external checks such as change management or observability.
- Admin bypass of protection rules is configurable per environment; disable it for production.

## 7. Releases and versioning

- Tag with semantic versions on the default branch; create releases from tags (draft, then publish) so notes and assets are reviewed first.
- Automatic notes: `gh release create v1.4.0 --generate-notes --verify-tag` and `.github/release.yml` for categories.
- Attach built artifacts with checksums and attestations (`gh release upload`, `gh attestation verify`).
- Enable immutable releases in repository settings for published software, and use signed tags where policy requires.
- Keep a changelog or generated release notes that map merged pull requests to versions.

## 8. gh CLI and REST recipes

```bash
gh auth status                                   # token scopes and host
gh repo view --json defaultBranchRef,visibility
gh api repos/{owner}/{repo}/rulesets --jq '.[].name'
gh api --method POST repos/{owner}/{repo}/rulesets --input ruleset.json
gh secret set DEPLOY_CONFIG --env production < config.txt   # value from file, not argv
gh variable set AWS_REGION --env production --body "eu-west-1"
gh run list --workflow ci.yml --limit 5
gh run view 1234567890 --log-failed
gh pr checks --watch
gh attestation verify app.tgz --repo example-org/app
```

- `{owner}` and `{repo}` placeholders in `gh api` paths are filled from the current repository.
- Use `GH_TOKEN` in automation (the workflow's `github.token` or an app installation token); prefer GitHub App tokens over personal access tokens for bots (fine-grained, short-lived, not tied to a person).
- For personal access tokens use fine-grained tokens with an expiry and the minimum repository scope.
- GitHub Apps: grant only the permissions needed, install on selected repositories, generate short-lived installation tokens in workflows (an app-token action pinned by SHA) when `GITHUB_TOKEN` cannot cross repositories.
- Paginate with `gh api --paginate`; avoid scraping the web UI.

## 9. Organization governance

- Base permissions: members default to `read`; grant write through teams; limit repository creation and visibility changes; require two-factor authentication.
- Use teams mapped to your identity provider; review outside collaborators and deploy keys regularly (prefer GitHub Apps over deploy keys).
- Enable audit log streaming for security events; alert on ruleset bypasses, disabled protections and new deploy keys.
- Standardize with repository templates, organization rulesets, required workflows, and code security configurations; use `.github` community health repositories for shared templates and policies (`SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`).
- Archive stale repositories; set a naming and topic convention; document ownership in `CODEOWNERS` and repository descriptions.
- Plan for emergency access: a documented, monitored break-glass procedure for ruleset bypass.
