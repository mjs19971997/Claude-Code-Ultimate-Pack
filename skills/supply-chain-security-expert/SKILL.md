---
name: supply-chain-security-expert
description: >-
  Secures the software supply chain: SBOMs (SPDX, CycloneDX) with Syft, vulnerability scanning with Grype, Trivy and OSV-Scanner, Sigstore signing with cosign, SLSA provenance and GitHub artifact attestations, npm and PyPI trusted publishing, dependency pinning and review, GitHub Actions hardening with zizmor, and compromised-dependency response. Use when editing workflows, dependabot.yml, renovate.json, lockfiles or requirements.txt hashes, or running syft, grype, trivy, cosign, gh attestation or osv-scanner. Not for application code flaws (use secure-coding-expert), general CI design (use cicd-expert), image builds (use docker-expert), or admission controllers in depth (use kubernetes-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Supply Chain Security Expert

This skill covers securing what goes into and comes out of a build: inventorying dependencies (SBOMs), finding known vulnerabilities, pinning and reviewing dependencies, hardening CI, signing artifacts, proving where they were built (provenance) and verifying them before use. It also covers the first hours of a compromised-dependency incident. Findings are reported with the exact command and its output, and every verification step names the identity it expects.

> Verified against Sigstore cosign 3.1.4 (2.x line at 2.6.5), Rekor 1.5.5, Fulcio 1.9.1, sigstore-go 1.4.0, sigstore policy-controller 0.15.1, Kyverno 1.19.2, Syft 1.55.0, Grype 0.121.0, Trivy 0.76.1, OSV-Scanner 2.7.0, OpenSSF Scorecard 5.6.0, GitHub CLI 2.103.3, zizmor 1.31.1, actions/attest v4, slsa-github-generator 2.1.0, slsa-verifier 2.7.1, in-toto attestation 1.2.0, SLSA spec 1.2, CycloneDX 1.7, SPDX 3.0.1, pip 26.2.2, uv 0.13.6, pypi-attestations 0.0.30 (2026-10).

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

- Covered: SBOM formats and generation (SPDX, CycloneDX, Syft, language-specific CycloneDX tools), vulnerability scanning (Grype, Trivy, OSV-Scanner) and VEX at a glance, Sigstore (cosign, Fulcio, Rekor) signing and verification of images and blobs, signature and attestation policy (Sigstore policy-controller, Kyverno), SLSA levels, in-toto attestations, GitHub artifact attestations and `gh attestation verify`, npm provenance and trusted publishing, PyPI Trusted Publishing and attestations, lockfiles, hash pinning, SHA-pinned Actions, digest-pinned images, dependency review, Dependabot and Renovate settings including release-age delays, vetting new dependencies, OpenSSF Scorecard, GitHub Actions hardening and zizmor, reproducible builds, and incident response.
- Not covered: injection, authentication or crypto bugs in application code (secure-coding-expert); general pipeline structure, caching and deployment strategy (cicd-expert); writing Dockerfiles and image optimisation (docker-expert); Kubernetes admission, RBAC and network policy in depth (kubernetes-expert); IaC scanning rules (terraform-expert); secret handling and API auth design (api-security-expert, authentication-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| SBOM formats | SPDX 3.0.1 is the newest SPDX release found; SPDX 2.3 is still what many tools emit, so check the format version a consumer accepts. CycloneDX 1.7 is current and is standardised as ECMA-424 (2nd edition). Syft can write `spdx-json`, `cyclonedx-json` and others |
| Scanners | Grype scans images, directories and SBOMs (`grype sbom:./sbom.json`). Trivy scans images, filesystems, repos and SBOMs and supports OpenVEX filtering. OSV-Scanner v2 scans lockfiles and directories (`osv-scanner scan -r .`, `scan -L <lockfile>`, `scan image`) and has a `fix` subcommand |
| cosign 3.x | New protobuf Sigstore bundle format is the default; service URLs come from a TUF-distributed signing config; container signatures are stored as OCI 1.1 referring artifacts. Keyless signing needs no `COSIGN_EXPERIMENTAL`. `sign-blob` writes and `verify-blob` reads a `--bundle` file (conventionally `*.sigstore.json`) |
| Keyless identity | Fulcio issues a short-lived certificate bound to an OIDC identity; Rekor records the signature in a transparency log. Verification must state the expected identity and issuer: `--certificate-identity` (or `-regexp`) plus `--certificate-oidc-issuer` (or `-regexp`). For GitHub Actions the issuer is `https://token.actions.githubusercontent.com` |
| GitHub attestations | `actions/attest` v4 creates SLSA build provenance by default, or an SBOM attestation with `sbom-path`, or a custom predicate. Needs `id-token: write` and `attestations: write`; the v4 docs also list `artifact-metadata: write`. `actions/attest-build-provenance` v4 is a thin wrapper and new work should use `actions/attest`. Verify with `gh attestation verify` |
| SLSA | Spec v1.2 (November 2025) added the Source track alongside the Build track and is described as backwards compatible with v1.1. Build levels L1 (provenance exists), L2 (hosted build, signed provenance), L3 (hardened build isolation). `slsa-github-generator` is at 2.1.0 (February 2025); `slsa-verifier` verifies its output |
| in-toto | An attestation is a signed Statement (`https://in-toto.io/Statement/v1`) with `subject` (name and digest) and a typed `predicate` such as `https://slsa.dev/provenance/v1`. in-toto attestation spec 1.2.0 |
| Registry publishing | PyPI Trusted Publishing via `pypa/gh-action-pypi-publish`: PEP 740 attestations are generated and uploaded by default for trusted-publisher flows. npm supports `npm publish --provenance` from supported CI and trusted publishing with OIDC; check the npm docs for the minimum CLI version and the per-package setup |
| Dependency delay | Dependabot `cooldown: default-days: N`; zizmor flags a cooldown below 7 days by default. Renovate `minimumReleaseAge`. uv `--exclude-newer`. Delays do not stop a compromise, they reduce exposure to short-lived malicious releases |
| Workflow linting | zizmor 1.31.1 audits workflows, composite actions and Dependabot config: `template-injection`, `unpinned-uses`, `excessive-permissions`, `dangerous-triggers`, `artipacked`, `cache-poisoning`, `impostor-commit`, `ref-confusion`, `known-vulnerable-actions`, `use-trusted-publishing`, `dependabot-cooldown` and more |
| Admission policy | Sigstore policy-controller uses `ClusterImagePolicy`; Kyverno uses `verifyImages` rules in `ClusterPolicy` and a newer CEL-based `ImageValidatingPolicy`. Check the Kyverno docs for which API your installed version prefers |

## 3. Workflow

1. Identify the ecosystems (npm, PyPI, Go, Maven, containers, GitHub Actions) and the existing controls: lockfiles, Dependabot or Renovate, CI permissions, signing, SBOM generation. Read `.github/workflows/`, `.github/dependabot.yml` and the lockfiles before proposing changes.
2. State the threat being addressed: vulnerable dependency, malicious package, compromised maintainer, compromised build, tampered artifact, or workflow injection. Each has a different control (scan, delay and review, trusted publishing, provenance, verification, linting).
3. Run the read-only tools first: `zizmor .github/workflows`, a scan (`osv-scanner scan -r .`, `trivy fs .`, `grype dir:.`), and `scorecard --repo=...` for third-party projects.
4. Make the smallest hardening change that closes the finding: add `permissions:`, pin a SHA, move an expression into `env:`, add a cooldown, add `--require-hashes`.
5. Verify by running the verification command a consumer would run (`cosign verify ...`, `gh attestation verify ...`), not only the signing command.
6. Record the expected identity (workflow path, repository, ref pattern, OIDC issuer) next to the verification command so consumers can copy it.
7. For an incident, follow the order in [references/ci-hardening-incident-response.md](references/ci-hardening-incident-response.md): contain, scope, rotate, rebuild, then prevent.

## 4. Decision Rules

- If a tool, spec or flag version matters, confirm it on the project's release page or `--help` first; this ecosystem renames flags between major versions (cosign 2 to 3 changed bundle defaults).
- If consumers need to know what is inside an artifact, publish an SBOM; if they need to know who built it and from what, publish provenance; if they need tamper evidence, sign it. These are three separate artifacts.
- If the SBOM consumer is not specified, emit CycloneDX JSON for vulnerability tooling and SPDX JSON where licence or procurement tooling expects SPDX; Syft can write both from one scan.
- If signing in CI, use keyless signing with the CI job's OIDC identity; if the environment has no OIDC provider or is air-gapped, use a KMS-backed key rather than a key file in a secret.
- If signing a container image, sign the digest (`repo/name@sha256:...`), never a mutable tag.
- If verifying, pin the expected identity to a workflow path and ref pattern (`--certificate-identity-regexp` anchored with `^...$`), not to a whole organisation.
- If publishing to PyPI, use Trusted Publishing; if publishing to npm, use trusted publishing or `--provenance` from CI and drop long-lived publish tokens where the registry allows.
- If a workflow runs on `pull_request_target` or `workflow_run`, do not check out or execute code from the pull request in that job.
- If an action is third party, pin it to a full commit SHA with a version comment; first-party `actions/*` and `github/*` are also pinned in security-sensitive repositories, and zizmor's `unpinned-uses` reports both.
- If an application is deployed, install from a lockfile with integrity hashes (`npm ci`, `uv sync --locked`, `pip install --require-hashes`, `go mod verify`).
- If a dependency update arrives, review the diff of the lockfile and the new version's install scripts, and prefer a delay (cooldown) for routine bumps; security fixes may bypass the delay deliberately.
- If a vulnerability is reported but unreachable, record the decision as a VEX statement (OpenVEX or CycloneDX VEX) rather than silently ignoring it.

## 5. Coding Standards

- Every workflow file sets top-level `permissions: {}` or `contents: read`, and each job grants only what it needs (`id-token: write`, `attestations: write`, `packages: write`).
- Pin `uses:` to a 40-character commit SHA followed by a comment with the version tag: `uses: owner/action@<full-commit-sha>  # vX.Y.Z`. The examples here use that placeholder because a real SHA must be resolved at the time of editing.
- Pass untrusted values (`github.event.*`, `github.head_ref`, PR titles, branch names, `inputs.*`) to scripts through `env:` and reference them as shell variables (`"$PR_TITLE"`); never interpolate `${{ ... }}` inside `run:` or `github-script` code.
- Set `persist-credentials: false` on `actions/checkout` unless a later step must push.
- Reference container images by digest (`image@sha256:...`) in Dockerfiles, Compose files, Kubernetes manifests and `container:` / `services:` in workflows, keeping the tag in a comment.
- Name signed artifacts consistently: `<artifact>.sigstore.json` for bundles, `<artifact>.cdx.json` or `<artifact>.spdx.json` for SBOMs, `<artifact>.intoto.jsonl` for provenance from slsa-github-generator.
- Keep verification commands in the repository (README or `SECURITY.md`) with the real identity strings filled in.
- Commit lockfiles; review lockfile diffs as code.

## 6. Project Structure

```text
repo/
+-- .github/
|   +-- dependabot.yml          # grouped updates, cooldown, github-actions ecosystem
|   +-- workflows/
|   |   +-- ci.yml              # tests, permissions: contents: read
|   |   +-- release.yml         # build, SBOM, attest, sign, publish (tag-triggered)
|   |   +-- dependency-review.yml
|   |   `-- zizmor.yml          # workflow lint on pull requests
|   `-- CODEOWNERS              # owners for .github/ and release config
+-- SECURITY.md                 # how to report, how to verify releases (identities)
+-- package-lock.json | uv.lock | go.sum | requirements.txt (with hashes)
`-- renovate.json               # alternative to dependabot.yml
```

- Keep release logic in one workflow with a tag trigger so the signing identity (workflow path plus ref) is stable and easy to pin.
- Put `.github/` under CODEOWNERS and branch protection; whoever edits workflows controls the signing identity.

## 7. Design Patterns

- **Build once, attest the digest**: build the artifact in one job, upload it, and have a later job with `id-token: write` attest and sign that exact digest. Cost: an extra job and artifact hand-off; benefit: the signing job never runs untrusted build steps.
- **Reusable workflow as the trust anchor**: a release workflow called from a protected tag lets consumers verify `--signer-workflow` or a certificate identity that names the reusable workflow. This is how SLSA Build L3 is reached with GitHub attestations (see the GitHub docs for the exact requirements).
- **Separate untrusted and privileged workflows**: a `pull_request` workflow builds and tests with no secrets; a separate `workflow_run` or manual workflow does privileged work on artifacts, treating them as data.
- **Allow-list verification at deploy**: an admission policy accepts only images whose signature matches the expected issuer and subject, and optionally require an attestation of a given predicate type.
- **Cooldown plus review**: a 7 day cooldown (or `minimumReleaseAge`) on routine updates, grouped PRs to cut noise, and an immediate path for security advisories.
- **SBOM at build, scan on schedule**: generate the SBOM once at build time, store it with the release, and re-scan the stored SBOM daily as new advisories appear; this scans what was shipped, not what is on a branch now.
- **Trusted publishing instead of tokens**: the registry trusts a specific repository and workflow file; no publish token exists to steal.

## 8. Best Practices

- Treat each dependency as code you run with your privileges; keep the tree small and remove unused packages.
- Prefer one attested release path over many manual ones. A manual `npm publish` from a laptop bypasses every control above.
- Rotate and minimise tokens; where an OIDC trust relationship exists, delete the old long-lived secret.
- Review new dependencies with the checklist in [references/dependency-pinning-review.md](references/dependency-pinning-review.md): maintainers, age, install scripts, repository match, download history, Scorecard.
- Enable GitHub security features that exist for the repository (Dependabot alerts, secret scanning, push protection, dependency graph); confirm in repository settings what your plan includes.
- Require review for changes to `.github/workflows/`, release configuration and lockfiles.
- Publish the verification instructions with the release, including the exact `--certificate-identity` and issuer.
- Use environments with required reviewers for the job that publishes.
- Keep a list of build-time tools (compilers, scanners, signers) and pin their versions and checksums too.

## 9. Performance

- Scanners download vulnerability databases; cache them between CI runs (Grype and Trivy have DB directories and update controls) and refresh at least daily, or scans become stale.
- Scan an SBOM instead of re-cataloguing the image when both are needed: `syft` once, then `grype sbom:` and `trivy sbom` on the file.
- Scan the lockfile (`osv-scanner scan -L`) for fast pull-request feedback, and the full image on the release path.
- Attesting and signing are small, fast operations; the slow parts are network calls to Fulcio and Rekor. Set job timeouts and retry the sign step once rather than rerunning the build.
- Large monorepos: scan changed lockfiles only on pull requests and everything on a schedule.
- Hash-checking installs (`pip --require-hashes`) can fail on first run if a transitive dependency is missing a hash; generate the full set with `uv pip compile --generate-hashes` or `uv export` rather than editing by hand.

## 10. Security

- Never sign with a private key stored in a repository secret when keyless signing is available; a stolen key signs anything until revoked, a keyless certificate lives minutes.
- A valid signature proves who signed, not that the content is safe. Always verify identity, and then also apply scanning and policy.
- Verification without identity flags (`cosign verify` with no `--certificate-identity*` and no `--certificate-oidc-issuer*`) fails for keyless signatures; do not work around this with wildcards such as `.*`.
- Do not run `pull_request_target` jobs that check out the pull request head, and do not pass secrets to jobs triggered by forks.
- Avoid `curl | sh` installers in CI. Download a release, verify its checksum or signature (or install through a pinned package), then run it.
- Mark the signing job's `id-token: write` permission at job level only; any step in that job can request an OIDC token, so pin every action in it.
- Cache poisoning: do not restore caches written by untrusted workflows in a privileged job (zizmor audit `cache-poisoning`).
- Assume a build agent that runs untrusted code can read its own environment, tokens and checked-out credentials; `persist-credentials: false` and short-lived tokens limit this.
- Typosquatting and dependency confusion: configure scoped registries or index priority so internal package names never resolve to the public registry.
- Disable or review install scripts for packages you do not trust (`npm install --ignore-scripts`, `ignore-scripts=true` in `.npmrc`); allow-list those that need them.

## 11. Testing

- Treat verification as a test: in the release workflow, after signing, run the same verify command a consumer will run, in a fresh job, and fail the release if it fails.
- Run `zizmor .github/workflows` as a CI check (`--persona pedantic` to see more findings) and fix or explicitly ignore each finding with a reason.
- Test policy with a known-bad case: try to deploy an unsigned image or one signed by a different workflow and confirm it is rejected (policy-controller and Kyverno both support dry-run or audit modes).
- Test hash-pinned installs in a clean environment: `pip install --require-hashes -r requirements.txt` or `uv sync --locked`.
- Validate generated SBOMs against the format's JSON schema where the consuming system requires strict validity, and confirm key fields are present (components, versions, purls, hashes).
- Periodically rehearse the incident runbook against a harmless fake advisory: find all usages, rebuild, redeploy.

## 12. Review Checklist

- [ ] Every workflow has least-privilege `permissions:`; no job has write permissions it does not use.
- [ ] No `${{ }}` of untrusted data inside `run:` or script bodies; values go through `env:`.
- [ ] All third-party actions are pinned to full SHAs with a version comment; images are pinned by digest.
- [ ] No `pull_request_target` or `workflow_run` job checks out or executes pull request code with secrets available.
- [ ] Releases are built in CI from a tag; artifacts are attested or signed; the identity is documented.
- [ ] Verification command exists, includes identity and issuer, and is tested.
- [ ] SBOM is generated at build time, stored with the release, and scanned on a schedule.
- [ ] Lockfiles are committed; installs use `ci`, `--locked` or `--require-hashes`.
- [ ] Dependabot or Renovate has grouping and a delay for routine updates; the `github-actions` ecosystem is included.
- [ ] New dependencies were reviewed (maintainers, install scripts, name, age); Scorecard checked for important ones.
- [ ] Publishing uses trusted publishing or OIDC where available; no long-lived publish token remains.
- [ ] zizmor passes or findings are documented.

## 13. Production Notes

- Record the signing and verification contract: issuer, subject pattern, predicate types, the trusted root source. Rotation of the Sigstore trust root is handled by TUF (`cosign initialize`, or the client's built-in update); airgapped clusters need a mirrored root and `--trusted-root`.
- Rekor and Fulcio public-good instances are shared infrastructure with their own availability; plan retries, and for private artifacts consider whether public log entries are acceptable (they expose repository names and workflow paths).
- cosign 3 changed defaults (bundle format, signing config); pin the cosign version in CI and the cosign-installer action to a SHA, and test upgrades on a staging image before changing the release workflow.
- Keep old verification instructions valid: a consumer may hold an older cosign. Check the cosign release notes before changing bundle or attestation layout.
- Retain SBOMs and provenance for as long as the artifact is deployed; scanning a running version needs its SBOM.
- Enforce at admission only after running the policy in audit mode and fixing the exceptions; keep a break-glass procedure that is logged.
- Review third-party action and tool versions monthly; run `zizmor` online mode with a read-only token to catch known-vulnerable and impostor commits.
- For regulated environments map evidence (SBOM, provenance, scan reports) to the framework requested; check the current text of the framework since requirements change.

## 14. Examples

A release workflow that builds, attests provenance and an SBOM, and signs a container digest. Replace each `<full-commit-sha>` with the real commit SHA of the tagged release before use.

```yaml
name: release
on:
  push:
    tags: ["v*"]

permissions: {}

jobs:
  image:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - uses: docker/login-action@<full-commit-sha>  # v<x.y.z>
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: build
        uses: docker/build-push-action@<full-commit-sha>  # v<x.y.z>
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      - uses: actions/attest@<full-commit-sha>  # v4
        with:
          subject-name: ghcr.io/${{ github.repository }}
          subject-digest: ${{ steps.build.outputs.digest }}
          push-to-registry: true
      - uses: sigstore/cosign-installer@<full-commit-sha>  # v<x.y.z>
      - name: Sign image digest
        env:
          IMAGE: ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
        run: cosign sign --yes "$IMAGE"
```

Consumer-side verification of that image, and of the GitHub attestation:

```bash
IMAGE=ghcr.io/acme/app@sha256:<digest>

cosign verify "$IMAGE" \
  --certificate-identity "https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

gh attestation verify "oci://$IMAGE" --repo acme/app \
  --signer-workflow acme/app/.github/workflows/release.yml
```

SBOM generation and scanning from the same scan result:

```bash
syft scan ghcr.io/acme/app:1.4.0 \
  -o cyclonedx-json=app.cdx.json -o spdx-json=app.spdx.json
grype sbom:./app.cdx.json --fail-on high
trivy sbom app.cdx.json --severity HIGH,CRITICAL --exit-code 1
```

Passing untrusted input safely in a workflow step:

```yaml
- name: Label by title
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: |
    printf 'Title: %s\n' "$PR_TITLE"
```

More recipes: [references/sbom-and-scanning.md](references/sbom-and-scanning.md), [references/sigstore-cosign.md](references/sigstore-cosign.md), [references/slsa-provenance-attestations.md](references/slsa-provenance-attestations.md).

## 15. Common Mistakes

- **Signing a tag, not a digest**: the tag can move after signing. Sign and verify `name@sha256:...`.
- **Verifying only that a signature exists**: anyone with a GitHub account can produce a Sigstore signature. The identity and issuer checks are the security property.
- **Broad identity regex** such as `--certificate-identity-regexp '.*'` or the whole organisation: any workflow in scope passes. Pin workflow path and ref.
- **`${{ github.event.pull_request.title }}` inside `run:`**: shell injection. Use `env:`.
- **Pinning to a tag or branch** (`@v4`, `@main`): a moved tag changes the code you run. Pin the commit SHA and let Dependabot or Renovate update it.
- **Trusting a SHA from a fork**: a commit SHA can exist only in a fork network and still resolve (impostor commit). Take SHAs from the upstream repository's tag and check with zizmor `impostor-commit`.
- **`pull_request_target` plus checkout of the PR head**: runs attacker code with a write token and secrets.
- **Granting `id-token: write` workflow-wide**: every job can then mint a signing identity. Scope it to the signing job.
- **Treating "no known CVE" as "safe"**: scanners find known vulnerabilities, not new malicious packages; add delay, review and behaviour checks.
- **Ignoring SBOM staleness**: an SBOM from the build date is correct for that artifact, but the vulnerability data changes daily; re-scan it.
- **Mixing `npm install` and `npm ci`** in CI: `install` can rewrite the lockfile. Use `npm ci`.
- **Auto-merging all updates**: without a cooldown or review, an automated bump delivers a compromised release directly.
- **Hash-pinning only top-level dependencies**: `pip --require-hashes` requires hashes for every requirement, including transitive ones.
- **Keeping the old publish token after enabling trusted publishing**: the token remains an attack path; revoke it.
- **Assuming reproducible builds are implied by provenance**: provenance says how the build ran, not that another party gets identical bytes.

## 16. References

- [references/sbom-and-scanning.md](references/sbom-and-scanning.md): SPDX and CycloneDX versions, Syft and language-specific generators, Grype, Trivy and OSV-Scanner commands, CI gates, VEX basics.
- [references/sigstore-cosign.md](references/sigstore-cosign.md): keyless model, cosign 3 defaults, signing and verifying images and blobs, attestations, trusted root, policy-controller and Kyverno.
- [references/slsa-provenance-attestations.md](references/slsa-provenance-attestations.md): SLSA v1.2 levels, in-toto statements, GitHub artifact attestations, slsa-github-generator, npm provenance, PyPI attestations, reproducible builds.
- [references/dependency-pinning-review.md](references/dependency-pinning-review.md): lockfiles, hash pinning, digest pinning, Dependabot and Renovate settings, dependency review, vetting new packages, Scorecard.
- [references/ci-hardening-incident-response.md](references/ci-hardening-incident-response.md): workflow permissions, injection, pull_request_target, zizmor, harden-runner, secrets, and a compromised-dependency runbook.
- Sigstore: https://docs.sigstore.dev/ and cosign releases https://github.com/sigstore/cosign/releases
- SLSA: https://slsa.dev/spec/ ; in-toto attestation: https://github.com/in-toto/attestation
- SPDX: https://spdx.dev/ ; CycloneDX: https://cyclonedx.org/specification/overview/
- Syft: https://github.com/anchore/syft ; Grype: https://github.com/anchore/grype ; Trivy: https://trivy.dev/ ; OSV-Scanner: https://google.github.io/osv-scanner/
- GitHub artifact attestations: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations ; actions/attest: https://github.com/actions/attest
- zizmor: https://docs.zizmor.sh/ ; OpenSSF Scorecard: https://github.com/ossf/scorecard
- PyPI attestations (PEP 740): https://peps.python.org/pep-0740/
