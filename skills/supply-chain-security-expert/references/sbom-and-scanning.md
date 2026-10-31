# SBOMs and Vulnerability Scanning

SBOM formats, generating SBOMs with Syft and ecosystem tools, scanning with Grype, Trivy and OSV-Scanner, CI gates and a short VEX section. Tool versions checked 2026-10: Syft 1.55.0, Grype 0.121.0, Trivy 0.76.1, OSV-Scanner 2.7.0. Flags change between releases, so confirm with `<tool> --help` before scripting.

## Contents

1. [Formats and versions](#1-formats-and-versions)
2. [Generating SBOMs](#2-generating-sboms)
3. [Scanning with Grype](#3-scanning-with-grype)
4. [Scanning with Trivy](#4-scanning-with-trivy)
5. [Scanning with OSV-Scanner](#5-scanning-with-osv-scanner)
6. [CI gates](#6-ci-gates)
7. [VEX](#7-vex)
8. [SBOM quality](#8-sbom-quality)

## 1. Formats and versions

| Format | Current version found | Notes |
|---|---|---|
| CycloneDX | 1.7 (released October 2025; ECMA-424 2nd edition) | JSON and XML encodings. Component `purl`, `hashes`, `licenses`, `dependencies` graph. Supports VEX in the same format. A future 2.0 is announced direction only |
| SPDX | 3.0.1 (patch to 3.0, December 2024) | SPDX 3 is a model with several serialisations (JSON-LD). SPDX 2.3 JSON and tag-value are still widely emitted and consumed; check which version the receiving system accepts |

- The version a tool writes is a tool setting; do not assume the newest. Look in the output (`bomFormat` and `specVersion` for CycloneDX, `spdxVersion` for SPDX 2.x).
- Pick one format as the primary and convert only when a consumer demands the other. Conversion can lose fields.
- Subject binding matters: an SBOM is only useful if it identifies the artifact it describes (image digest, file hash). Attest it to that digest (see [sigstore-cosign.md](sigstore-cosign.md)).

## 2. Generating SBOMs

Syft catalogs container images, directories, archives and more:

```bash
# Image to CycloneDX and SPDX in one scan
syft scan ghcr.io/acme/app:1.4.0 \
  -o cyclonedx-json=app.cdx.json -o spdx-json=app.spdx.json

# Directory (source tree) and a local archive
syft scan dir:. -o cyclonedx-json=source.cdx.json
syft scan oci-archive:./image.tar -o spdx-json=image.spdx.json

# Convert an existing SBOM to another format
syft convert app.cdx.json -o spdx-json=converted.spdx.json
```

- Run `syft scan --help` and `syft --help` for the list of source schemes (`docker:`, `registry:`, `dir:`, `file:`, `oci-archive:`) and output formats on your version.
- For images, scan the digest you will ship: `registry:ghcr.io/acme/app@sha256:...`.
- A source-tree SBOM sees lockfiles and manifests; an image SBOM also sees OS packages and files copied into the image. Release SBOMs for containers come from the image.

Ecosystem tools produce richer dependency graphs from the build tool's own resolver:

| Ecosystem | Tool | Example |
|---|---|---|
| npm | `@cyclonedx/cyclonedx-npm` (6.0.1) | `npx @cyclonedx/cyclonedx-npm --output-file bom.json` |
| Python | `cyclonedx-bom` (CLI `cyclonedx-py`) | `cyclonedx-py environment -o bom.json` (subcommands for requirements, poetry, pipenv: check `--help`) |
| Go | `cyclonedx-gomod` | `cyclonedx-gomod app -json -output bom.json` (check `--help` for current flags) |
| Any | CycloneDX CLI | validation, merge and conversion of BOM files |

- Generate Python SBOMs from the environment you actually ship (the built virtualenv or image), not from a loose requirements file, or transitive pins will differ.
- Install SBOM tools from a pinned version and verify their checksums; they are build-time code too.

## 3. Scanning with Grype

```bash
grype ghcr.io/acme/app:1.4.0               # image
grype dir:.                                # source tree
grype sbom:./app.cdx.json                  # an existing SBOM
cat app.cdx.json | grype                   # SBOM on stdin

grype sbom:./app.cdx.json --fail-on high   # non-zero exit at or above severity
grype sbom:./app.cdx.json --only-fixed     # hide findings with no fix yet
grype sbom:./app.cdx.json -o json > grype.json
```

- `--fail-on <severity>` gates the build on severity. `--only-fixed` is useful for gates (actionable) but hides unfixed issues from reports; use both views.
- Grype downloads and updates its vulnerability database; in CI cache the database directory and refresh it daily. Behaviour on offline mode and DB age limits is in the Grype configuration docs.
- Grype can consume VEX documents; check `grype --help` for the current option names (`--vex`) before relying on them.
- Install from a verified release (checksums or signature) or a package manager; the README shows a script installer, but in CI download the release and check it instead of piping a script to a shell.

## 4. Scanning with Trivy

```bash
trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 ghcr.io/acme/app:1.4.0
trivy fs --scanners vuln,secret,misconfig .
trivy image --format cyclonedx --output app.trivy.cdx.json ghcr.io/acme/app:1.4.0
trivy sbom app.cdx.json --severity HIGH,CRITICAL --exit-code 1
```

- Trivy covers vulnerabilities, secrets, misconfiguration and licences, selected with `--scanners`. Keep the scanner list explicit so scan time and findings stay predictable.
- `--exit-code 1` turns findings into a failing status; without it Trivy exits 0 even with findings.
- Trivy supports OpenVEX to filter and augment results (see its supply-chain docs). Check the current flag spelling in `trivy image --help`.
- Trivy keeps a vulnerability DB and a checks bundle that it downloads from registries; in restricted networks mirror them and point Trivy at the mirror (see its air-gapped docs).
- Pin the Trivy installation in CI and verify it. If you use the official action, pin it to a commit SHA like any other action.

## 5. Scanning with OSV-Scanner

```bash
osv-scanner scan -r .                              # recursive, finds lockfiles and manifests
osv-scanner scan -L package-lock.json              # one lockfile
osv-scanner scan image my-image:latest             # container image
osv-scanner scan -L package-lock.json --format json --output-file osv.json
osv-scanner scan -L package-lock.json --config ./osv-scanner.toml
osv-scanner fix -M package.json -L package-lock.json   # guided remediation
```

- OSV-Scanner queries the OSV.dev database through the OSV-Scalibr extraction library; output formats are selected with `--format` (check the docs for the list).
- It reads lockfiles directly, so it is a fast pull-request check and does not need a built artifact.
- An ignore list lives in the TOML config (`osv-scanner.toml`) with a reason and optional expiry; check the config docs for field names.
- `--licenses` reports licence violations against an allow-list in current docs; verify the exact form for your version.
- OSV.dev is a network service: in air-gapped environments check the offline database options in the docs.

## 6. CI gates

- Two lanes work well: fast lockfile scan on pull requests (OSV-Scanner or Trivy `fs`), full image scan plus SBOM on the release path (Syft, Grype or Trivy).
- Gate on severity and fixability, not on any finding; a gate that fails on unfixable low-severity issues is disabled within a week.
- A dependency added by a pull request is checked by the dependency review action (see [dependency-pinning-review.md](dependency-pinning-review.md)); scanners cover what is already in the tree.
- Keep scanner results as workflow artifacts and, where supported, upload SARIF to code scanning. Upload requires `security-events: write` on that job only.
- Schedule a nightly scan of the stored release SBOMs so new advisories surface without a new build.
- Different scanners disagree because of different databases and matching rules. Choose one as the gate and use another for cross-checking; do not require all of them to agree.

Scheduled scan of a stored SBOM (job-level permissions, pinned actions, no untrusted input):

```yaml
name: nightly-sbom-scan
on:
  schedule:
    - cron: "17 3 * * *"
permissions: {}
jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<full-commit-sha>  # v<x.y.z>
        with:
          persist-credentials: false
      - name: Install grype from a verified release
        run: echo "download a pinned release, verify its checksum, then install"
      - name: Scan
        run: grype sbom:./release/app.cdx.json --fail-on high
```

## 7. VEX

- VEX (Vulnerability Exploitability eXchange) states whether a product is affected by a given vulnerability: statuses include not affected, affected, fixed and under investigation, with a justification for "not affected".
- Formats: OpenVEX (small JSON documents), CycloneDX VEX (inside a BOM or a standalone BOM), and CSAF VEX profile. Trivy supports OpenVEX; cosign can attach an OpenVEX statement as an attestation (`--type openvex`).
- Use VEX to record decisions such as "vulnerable function not reachable", signed and attached to the release, so scanners and consumers stop re-reporting it. Review VEX statements when the dependency version changes.

## 8. SBOM quality

- Check that components have versions, `purl` identifiers and hashes; findings quality depends on accurate identifiers (CPE and purl matching).
- Check that the dependency graph or relationships are present, not only a flat list.
- Include build tools only if consumers need them; label what is runtime and what is build-time.
- Minimum fields commonly requested for regulated procurement are set by the requesting authority; check the current guidance of the requesting party rather than assuming a list.
- An SBOM generated at build time but never signed or attached can be replaced; attach it with `actions/attest` (`sbom-path`) or `cosign attest --type cyclonedx|spdxjson`.
