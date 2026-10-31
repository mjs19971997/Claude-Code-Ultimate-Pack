# SLSA, Provenance and Attestations

SLSA v1.2 tracks and levels, in-toto statements, GitHub artifact attestations with `actions/attest` v4 and `gh attestation verify`, slsa-github-generator, npm provenance and trusted publishing, PyPI Trusted Publishing and PEP 740 attestations, and reproducible builds. Versions checked 2026-10: SLSA 1.2, in-toto attestation 1.2.0, actions/attest v4, slsa-github-generator 2.1.0, slsa-verifier 2.7.1, GitHub CLI 2.103.3, pypi-attestations 0.0.30.

## Contents

1. [SLSA at a glance](#1-slsa-at-a-glance)
2. [In-toto statements and predicates](#2-in-toto-statements-and-predicates)
3. [GitHub artifact attestations](#3-github-artifact-attestations)
4. [Verifying with gh](#4-verifying-with-gh)
5. [slsa-github-generator](#5-slsa-github-generator)
6. [npm provenance and trusted publishing](#6-npm-provenance-and-trusted-publishing)
7. [PyPI Trusted Publishing and PEP 740](#7-pypi-trusted-publishing-and-pep-740)
8. [Reproducible builds](#8-reproducible-builds)

## 1. SLSA at a glance

- SLSA (Supply-chain Levels for Software Artifacts) is a specification of incremental guarantees. Version 1.2 was published in November 2025; it is described as backwards compatible with 1.1 and introduces the Source track next to the Build track. Check https://slsa.dev/spec/ for later revisions and for the current status of each track.
- Build track levels: L1 provenance exists (may be unsigned, produced by the build); L2 builds run on a hosted platform that signs the provenance, so forging it requires compromising that platform; L3 the build platform hardens against tenant interference: builds are isolated, and the signing material is not accessible to the build steps.
- Source track (new in 1.2): levels describe source control practices, with provenance for the source revision; the release candidate notes describe Level 2 as history and provenance and Level 3 as continuous enforcement of technical controls. Read the spec text before claiming a source level.
- Provenance is a claim "this artifact was built by this builder from this source with these inputs". It is useful only when a verifier checks it against expectations: expected builder identity, source repository and ref, and subject digest.
- SLSA levels apply to a build process and platform, not to a product as a whole. State the level together with the track and the spec version.

## 2. In-toto statements and predicates

An attestation is a signed envelope (DSSE) around an in-toto Statement:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    { "name": "ghcr.io/acme/app", "digest": { "sha256": "<hex>" } }
  ],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": { }
}
```

- `subject` names the artifacts by digest; `predicateType` selects the schema of `predicate`.
- Common predicate types: SLSA provenance (`https://slsa.dev/provenance/v1`), SPDX and CycloneDX SBOMs, OpenVEX, vulnerability scan results, and custom types. Keep custom types under a URI you control.
- SLSA provenance v1 has `buildDefinition` (build type, external parameters, resolved dependencies) and `runDetails` (builder id, metadata). Verifiers compare `externalParameters` and the builder id to policy.
- The in-toto attestation framework is at 1.2.0 on GitHub. Tools hide the envelope, but you see it in `cosign verify-attestation` output and in `gh attestation verify --format json`.

## 3. GitHub artifact attestations

The `actions/attest` action (v4 at check time) signs attestations with the workflow's OIDC identity through Sigstore and stores them with GitHub; `actions/attest-build-provenance` v4 is documented as a wrapper around it and new workflows should use `actions/attest`.

Permissions documented for the action: `id-token: write`, `attestations: write`, and `artifact-metadata: write`; examples add `contents: read`, and `packages: write` for images.

Key inputs from the README: `subject-path` (artifact paths or globs, up to 1024 subjects), `subject-digest` plus `subject-name` (for an image already pushed; `sha256:<hex>`), `subject-checksums`, `sbom-path` (SPDX or CycloneDX JSON, up to 16 MB), `predicate-type` with `predicate` or `predicate-path`, `push-to-registry` (default false; the subject must be an OCI image reference with a SHA-256 digest), `show-summary` (default true). Outputs: `attestation-id`, `attestation-url`, `bundle-path` (a Sigstore bundle file), `storage-record-ids`.

- With none of `sbom-path`, `predicate-type`, `predicate`, `predicate-path` the action generates a SLSA build provenance attestation.
- `sbom-path` cannot be combined with the predicate inputs.

Release artifacts:

```yaml
permissions: {}
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - run: make dist
      - uses: actions/upload-artifact@<full-commit-sha>  # v<x.y.z>
        with:
          name: dist
          path: dist/
          if-no-files-found: error
  attest:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      attestations: write
      artifact-metadata: write
    steps:
      - uses: actions/download-artifact@<full-commit-sha>  # v<x.y.z>
        with:
          name: dist
          path: dist/
      - uses: actions/attest@<full-commit-sha>  # v4
        with:
          subject-path: dist/*
```

- Splitting build and attest means only the attest job has `id-token: write`. The attestation then says "this workflow attested these bytes"; it vouches for the build only to the degree the build job is trusted. Higher assurance uses a reusable workflow that builds and attests inside one isolated run (see GitHub's documentation on SLSA Build L3 with reusable workflows).
- Attestations for private repositories and for GitHub Enterprise Server need the right plan and settings; check the GitHub docs for availability.
- SBOM attestation: `with: { subject-digest: ..., subject-name: ..., sbom-path: app.cdx.json }`.

## 4. Verifying with gh

```bash
# Local file; scope by repository or by organization
gh attestation verify dist/app-1.4.0.tar.gz --repo acme/app

# Require the exact workflow that signed
gh attestation verify dist/app-1.4.0.tar.gz --repo acme/app \
  --signer-workflow acme/app/.github/workflows/release.yml

# Container image
gh attestation verify oci://ghcr.io/acme/app@sha256:<digest> --repo acme/app

# Other predicate types (default is SLSA provenance v1) and JSON output
gh attestation verify oci://ghcr.io/acme/app@sha256:<digest> --repo acme/app \
  --predicate-type https://cyclonedx.org/bom --format json
```

Flags confirmed in the gh source (2.103.x): `--repo`/`-R` or `--owner`/`-o` (one required), `--signer-workflow`, `--signer-repo`, `--cert-identity` / `--cert-identity-regex`, `--cert-oidc-issuer` (defaults to the GitHub issuer), `--predicate-type`, `--source-ref`, `--source-digest`, `--signer-digest`, `--deny-self-hosted-runners`, `--bundle` (verify against a bundle file offline), `--bundle-from-oci`, `--custom-trusted-root`, `--format`, `--limit`.

- `--repo` alone proves "some workflow in this repository"; add `--signer-workflow` and `--source-ref` to pin the release path.
- Use `--deny-self-hosted-runners` when the policy requires GitHub-hosted runners.
- `--bundle` and `--custom-trusted-root` allow offline verification of a downloaded bundle.
- Kubernetes can enforce GitHub attestations through admission controllers that understand the Sigstore bundle; see the policy-controller and Kyverno notes in [sigstore-cosign.md](sigstore-cosign.md).

## 5. slsa-github-generator

- `slsa-framework/slsa-github-generator` provides reusable workflows (generic, container, Go, Node.js builders) that produce SLSA provenance with Build L3 properties on GitHub-hosted runners. Latest release noted in its README: v2.1.0 (February 2025).
- Reusable workflows must be referenced by a tag (`@v2.1.0`), not by SHA, because the verifier extracts the builder version from the ref; this is a documented exception to SHA pinning. Review the README for the current rule before changing it, and do not assume it applies to other actions.
- Output is an `*.intoto.jsonl` file attached to the release. Verify it with `slsa-verifier` (2.7.1):

```bash
slsa-verifier verify-artifact app-1.4.0.tar.gz \
  --provenance-path app-1.4.0.intoto.jsonl \
  --source-uri github.com/acme/app \
  --source-tag v1.4.0

slsa-verifier verify-image ghcr.io/acme/app@sha256:<digest> \
  --source-uri github.com/acme/app --source-tag v1.4.0
```

- Choose between the two systems: `actions/attest` is simpler and verified with `gh`; slsa-github-generator has a long track record of L3 provenance and a verifier built for it. Do not attest the same artifact twice by default; pick one and document it.

## 6. npm provenance and trusted publishing

- Provenance: `npm publish --provenance --access public` run from a supported CI provider with an OIDC token (`permissions: id-token: write` on GitHub Actions) attaches a signed provenance statement that links the package version to its source repository and build. The registry page shows it, and `npm audit signatures` verifies registry signatures and provenance attestations of installed packages.
- Trusted publishing: instead of a publish token, configure the package on npmjs.com to trust a specific GitHub repository and workflow file; the workflow then publishes using OIDC. The npm docs state a minimum npm CLI version, and that provenance is generated automatically for trusted publishing from public repositories. Check https://docs.npmjs.com/trusted-publishers for the current CLI floor, supported providers and the setting that disallows token publishing, because this feature set has changed during 2025 and 2026.
- After enabling it, remove the `NPM_TOKEN` secret and set the package publishing access to forbid tokens where the registry offers that option.
- Provenance proves where a package was built, not that the source is benign. Pair it with review and install-script control.

```yaml
permissions: {}
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: npm-release
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - uses: actions/setup-node@<full-commit-sha>  # v<x.y.z>
        with:
          node-version: "lts/*"
          registry-url: "https://registry.npmjs.org"
      - run: npm ci
      - run: npm publish --provenance --access public
```

## 7. PyPI Trusted Publishing and PEP 740

- Trusted Publishing: register the GitHub repository, workflow filename and optional environment as a trusted publisher in the project's PyPI settings; the workflow exchanges an OIDC token for a short-lived upload token. No API token secret is stored.
- `pypa/gh-action-pypi-publish` README: needs `id-token: write` ("mandatory for trusted publishing"), recommends granting it only in the publishing job, and states that signed digital attestations for all distribution files are generated and uploaded by default for projects using Trusted Publishing; set `attestations: false` to disable. Attestations use Sigstore and the workflow's OIDC identity (PEP 740).
- The README shows `pypa/gh-action-pypi-publish@release/v1`. That is a branch ref; pin the SHA of a release tag instead and let Dependabot or Renovate update it.
- Build in one job, upload the `dist/` artifact, and publish in a second job with `id-token: write` and a deployment environment with required reviewers.
- Consumers: `pypi-attestations` (0.0.30) provides a CLI to verify attestations; pip does not yet verify them at install time as of this check, so verification is an explicit step (`pypi-attestations verify pypi ...`; check `--help`). The index also shows provenance on the project page.

```yaml
permissions: {}
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@<full-commit-sha>  # v<x.y.z>
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@<full-commit-sha>  # v<x.y.z>
```

## 8. Reproducible builds

- A build is reproducible when the same source and inputs produce bit-for-bit identical output. It lets independent parties confirm an artifact matches its source, which provenance alone cannot.
- Typical sources of difference: embedded timestamps, file ordering, absolute paths, locale and time zone, random IDs, and unpinned toolchains. Mitigate with `SOURCE_DATE_EPOCH`, sorted archive entries and normalised mtimes, `-trimpath` for Go, fixed compiler versions, and a hermetic build environment.
- Containers: pin the base image by digest, pin package versions or snapshot repositories, and set deterministic timestamps in the image build (check docker-expert and your builder's documentation for rewrite-timestamp options).
- Verify by building twice (in different directories or hosts) and comparing digests, or with `diffoscope` for a readable diff of differences.
- Reproducibility is a goal per project, not a switch. Document the known non-reproducible parts rather than claiming the property.
