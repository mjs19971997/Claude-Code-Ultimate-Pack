# Dependency Pinning and Review

Lockfiles, hash pinning, pinning GitHub Actions and base images, dependency review on pull requests, Dependabot and Renovate settings (grouping, release-age delay), and a checklist for vetting new dependencies. Checked 2026-10: pip 26.2.2, uv 0.13.6, zizmor 1.31.1, OpenSSF Scorecard 5.6.0; Dependabot and Renovate option names were checked against the zizmor audit docs and the Renovate configuration reference.

## Contents

1. [Lockfiles and frozen installs](#1-lockfiles-and-frozen-installs)
2. [Hash pinning](#2-hash-pinning)
3. [Pinning GitHub Actions and images](#3-pinning-github-actions-and-images)
4. [Dependabot configuration](#4-dependabot-configuration)
5. [Renovate configuration](#5-renovate-configuration)
6. [Dependency review on pull requests](#6-dependency-review-on-pull-requests)
7. [Vetting a new dependency](#7-vetting-a-new-dependency)
8. [OpenSSF Scorecard](#8-openssf-scorecard)

## 1. Lockfiles and frozen installs

| Ecosystem | Lockfile | Install command that fails on drift |
|---|---|---|
| npm | `package-lock.json` | `npm ci` |
| pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
| Yarn (Berry) | `yarn.lock` | `yarn install --immutable` |
| Python (uv) | `uv.lock` | `uv sync --locked` |
| Python (pip) | `requirements.txt` with hashes | `pip install --require-hashes -r requirements.txt` |
| Go | `go.sum` | `go mod verify`; build with `-mod=readonly` |
| Rust | `Cargo.lock` | `cargo build --locked` |
| Ruby | `Gemfile.lock` | `bundle install --frozen` (or deployment mode) |

- Applications commit lockfiles. Libraries commit them too for their own CI, but publish loose ranges for consumers.
- Install in CI with the "fails if out of date" command, never with the resolver-updating variant.
- Review lockfile diffs: a changed `resolved` URL or registry host, a new transitive package, or a version that moved more than the pull request claims all deserve a look. Lockfile-only changes by a first-time contributor are a known attack pattern.
- Configure the registry explicitly (`.npmrc`, `pip.conf`, `uv` index settings) and use scoped registries or index priority so an internal package name cannot resolve from the public index (dependency confusion).
- `ignore-scripts` (npm: `npm ci --ignore-scripts`) prevents install-time code execution; then run only the lifecycle scripts you need explicitly.

## 2. Hash pinning

pip hash-checking mode (from the pip documentation): hashes are given per requirement with `--hash`, and specifying a hash on any requirement turns the mode on for all of them; `--require-hashes` makes it explicit.

```text
# requirements.txt (generated, do not hand edit)
<package-a>==<version> \
    --hash=sha256:<hex-1> \
    --hash=sha256:<hex-2>
<package-b>==<version> \
    --hash=sha256:<hex-3>
```

```bash
uv pip compile pyproject.toml --generate-hashes -o requirements.txt
pip install --require-hashes --no-deps -r requirements.txt
uv export --format requirements-txt > requirements.txt   # from a uv project; hashes included by default
uv sync --locked                                         # uv.lock records hashes itself
```

- In hash mode every requirement must be pinned with `==` and have a hash, including transitive dependencies; `--no-deps` avoids resolving anything not listed.
- Include hashes for every wheel and sdist you may install across platforms, or the install fails on a platform whose wheel was not hashed. Generate on or for each target platform set.
- `uv.lock` stores hashes for locked packages; `uv sync --locked` fails if the lock does not match `pyproject.toml`. `uv lock --exclude-newer <timestamp>` (and the `exclude-newer` setting) restrict resolution to releases uploaded before a time (uv docs, resolution page); it applies to packages read from a registry.
- npm lockfiles carry `integrity` hashes (SRI) by default; `npm ci` verifies them.
- Go verifies module hashes against `go.sum` and the checksum database (`GONOSUMDB`/`GOFLAGS=-mod=mod` weaken this; avoid in CI).

## 3. Pinning GitHub Actions and images

```yaml
# Weak: moves when the tag moves
- uses: owner/action@v4
# Strong: immutable commit, tag in a comment so updaters can bump it
- uses: owner/action@<full-commit-sha>  # v4.2.1
```

- Resolve a tag to a SHA from the upstream repository (`git ls-remote https://github.com/owner/action refs/tags/v4.2.1`; for annotated tags use the `^{}` dereferenced line). Check that the SHA belongs to the upstream repository, not a fork (zizmor `impostor-commit`).
- Let tooling maintain it: Dependabot's `github-actions` ecosystem updates SHA-pinned actions along with the version comment, and Renovate has a preset that pins action digests (`helpers:pinGitHubActionDigests`; confirm the preset name in the Renovate presets docs).
- zizmor `unpinned-uses` reports unpinned actions, `ref-version-mismatch` reports a comment that does not match the pinned SHA, and `stale-action-refs` reports refs that are stale.
- Pin also: reusable workflow references (`uses: org/repo/.github/workflows/x.yml@<sha>`), `container:` and `services:` images in workflows (`unpinned-images` in zizmor), and tools installed by `pip install`, `npm i -g`, `go install` in `run:` steps (`unpinned-tools` in zizmor, check the audit docs for current scope).
- Exception: some projects require a tag ref for their reusable workflows (for example, slsa-github-generator); follow their README.
- Docker: use `FROM image:1.2.3@sha256:<digest>` so the tag documents intent and the digest guarantees content; update with Dependabot's `docker` ecosystem or Renovate. Image construction itself: docker-expert.
- Kubernetes manifests and Compose files: reference images by digest, then verify signatures at admission (see [sigstore-cosign.md](sigstore-cosign.md)).

## 4. Dependabot configuration

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    groups:
      minor-and-patch:
        update-types: ["minor", "patch"]
    open-pull-requests-limit: 5
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    groups:
      actions:
        patterns: ["*"]
```

- `cooldown.default-days` delays version updates after a release. Dependabot applies a three day cooldown by default according to the zizmor docs; zizmor's `dependabot-cooldown` audit flags values under 7 days (configurable with `rules.dependabot-cooldown.config.days`). Check the Dependabot options reference for the per-semver keys (`semver-major-days`, `semver-minor-days`, `semver-patch-days`) and include/exclude lists.
- Security updates (for known advisories) are a separate mechanism and are not delayed by version-update cooldowns; confirm in the Dependabot docs.
- Grouping with `groups:` reduces PR noise; keep major bumps separate so they get individual review.
- Add the `github-actions` ecosystem so pinned SHAs stay current, and `docker` for base images. zizmor can lint `dependabot.yml` itself (audits `dependabot-cooldown` and `dependabot-execution`).
- Do not auto-merge without a required CI check set and branch protection; auto-merge on patch-only updates for development dependencies is the usual limit.

## 5. Renovate configuration

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", "helpers:pinGitHubActionDigests"],
  "minimumReleaseAge": "7 days",
  "prCreation": "not-pending",
  "internalChecksFilter": "strict",
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "groupName": "minor and patch updates"
    }
  ]
}
```

- `minimumReleaseAge` (from the Renovate docs) makes Renovate wait a duration after a release before proposing it; the branch shows a pending status until the age passes. It needs a datasource that provides release timestamps. The docs give `minimumReleaseAge=3 days` with `prCreation="not-pending"` and `internalChecksFilter="strict"` as the way to create branches only after the delay; `0 days` is treated as unset from Renovate 42.19.5.
- It does not wait for quiet periods; do not use it to slow down fast-releasing projects. It is a guard against short-lived malicious releases.
- Vulnerability alert updates can be configured separately so security fixes are not held back by the delay; check Renovate's `vulnerabilityAlerts` docs.
- Check the config with `renovate-config-validator` before merging config changes.

## 6. Dependency review on pull requests

The `actions/dependency-review-action` compares the dependency graph of a pull request against the base and fails on vulnerable or disallowed additions. It needs the dependency graph enabled and `contents: read`; for PR comments it also needs `pull-requests: write`.

```yaml
name: dependency-review
on:
  pull_request:
permissions: {}
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - uses: actions/dependency-review-action@<full-commit-sha>  # v<x.y.z>
        with:
          fail-on-severity: high
```

- Option names such as `fail-on-severity`, `deny-licenses` / `allow-licenses`, and `comment-summary-in-pr` are in the action README; confirm spelling for the pinned version, since the action changes options occasionally.
- It catches additions in the pull request; it does not scan what is already in the tree (use a scanner, see [sbom-and-scanning.md](sbom-and-scanning.md)).
- Use a pull-request trigger, not `pull_request_target`, so forks cannot influence a privileged run.

## 7. Vetting a new dependency

1. Need: could the standard library or an existing dependency do this? A 20 line function is cheaper than a package.
2. Name: check spelling against the intended package (typosquatting), and the exact registry scope or organisation. Search the project's own docs for the install command rather than copying one from a forum.
3. Source match: the registry page links to a repository; the repository's README links back; the published version corresponds to a tag. A package with no source link or a mismatched one is a flag.
4. Maintainers and history: number of maintainers, age of the package, recent ownership changes, release cadence, and whether the latest release is unusually new, with a big diff from the previous one.
5. Install-time behaviour: `preinstall`, `install`, `postinstall` scripts (npm), `setup.py` with custom commands or build backends (Python), `build.rs` (Rust), `go generate` and cgo. Read them. In npm, `npm view <pkg> scripts` and `npm pack <pkg> --dry-run` show metadata and contents without installing.
6. Provenance: does the registry show provenance or attestations (npm provenance, PyPI attestations)? These tie a release to a repository build; they are positive evidence, not a guarantee.
7. Dependency footprint: how many transitive packages does it pull in? Compare with `npm ls`, `uv tree` or `go mod graph` before and after.
8. Health: open security advisories, archived repository, last commit date, Scorecard results ([section 8](#8-openssf-scorecard)).
9. Licence: compatible with your distribution model; checked by a licence tool or dependency review.
10. Record the decision in the pull request: why this package, version pinned, who reviewed the install scripts.

Red flags: a very recent first release with many downloads from nowhere, install scripts that fetch and execute remote code, obfuscated code, network calls at import time, a maintainer change right before a new release, and minimal README with a name close to a popular package.

## 8. OpenSSF Scorecard

- Scorecard (v5.6.0) runs automated checks on a repository (for example Pinned-Dependencies, Token-Permissions, Dangerous-Workflow, Branch-Protection, Code-Review, Maintained, Signed-Releases, Vulnerabilities) and scores each. Run it on a dependency before adopting it, and on your own repository.

```bash
export GITHUB_AUTH_TOKEN=<read-only token from the environment>
scorecard --repo=github.com/owner/project
scorecard --repo=github.com/owner/project --checks Pinned-Dependencies,Token-Permissions --show-details
```

- A published score is available for many projects at https://scorecard.dev/ (viewer) and through its API; use it as one signal. A low score is not malicious and a high score is not safe.
- Use the Scorecard check names as a to-do list for your own repository: `Dangerous-Workflow`, `Token-Permissions` and `Pinned-Dependencies` overlap with the zizmor audits.
