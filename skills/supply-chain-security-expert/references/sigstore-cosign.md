# Sigstore and cosign

Keyless signing and verification with cosign 3.x (3.1.4; the 2.x line is at 2.6.5), Fulcio, Rekor and the Sigstore bundle format; attestations; admission policy with Sigstore policy-controller (0.15.1) and Kyverno (1.19.2). Flag details were checked against the cosign documentation in the repository (2026-10); run `cosign <command> --help` on the installed version before scripting.

## Contents

1. [How keyless signing works](#1-how-keyless-signing-works)
2. [cosign 3 defaults](#2-cosign-3-defaults)
3. [Signing and verifying container images](#3-signing-and-verifying-container-images)
4. [Signing and verifying blobs](#4-signing-and-verifying-blobs)
5. [Attestations with cosign](#5-attestations-with-cosign)
6. [Identities for common signers](#6-identities-for-common-signers)
7. [Trusted root and offline use](#7-trusted-root-and-offline-use)
8. [Policy enforcement](#8-policy-enforcement)
9. [Troubleshooting](#9-troubleshooting)

## 1. How keyless signing works

1. The signer obtains an OIDC identity token from its provider (GitHub Actions, GitLab CI, Google, and others).
2. cosign generates an ephemeral key pair and sends the public key plus the token to Fulcio, the certificate authority. Fulcio issues a short-lived X.509 certificate that embeds the identity (the subject, such as a workflow URL) and the issuer.
3. cosign signs the artifact and records the signature, certificate and a timestamp in Rekor, the transparency log (and/or a signed timestamp authority response, depending on the signing config).
4. The ephemeral private key is discarded. The certificate expires in minutes, so verification relies on proof that the signature was made while the certificate was valid.
5. The verifier checks: the certificate chains to the Fulcio root in the trusted root, the identity and issuer match what the verifier expects, and the log or timestamp proof is valid.

The security property is "this artifact was signed by identity X as asserted by issuer Y". It says nothing about whether X is trustworthy, so the expected identity must be a specific workflow or person.

## 2. cosign 3 defaults

From the cosign changelog (v3.0.0 and later):

- The protobuf Sigstore bundle format is the default; a bundle holds the signature, certificate and log proof in one file.
- Service URLs (Fulcio, Rekor, TSA, OIDC) are taken from a signing config distributed through TUF by default; `--signing-config` and `--trusted-root` supply them from files.
- Container signatures are stored as OCI 1.1 referring artifacts.
- `--bundle` was made required in some v3.0.x signing flows (notes for 3.0.1 and 3.0.2); for `sign-blob` pass `--bundle` explicitly and keep the `*.sigstore.json` file with the artifact.
- Deprecated, not removed, in the notes: `--offline`, `--tlog-upload`, `--rekor-entry-type`, `cosign triangulate`, `cosign copy`. `cosign initialize` lost `--out`.
- Rekor v2 entries require a signed timestamp; TSA use is required for Rekor v2 with Fulcio signing in the notes. If your private deployment differs, read the signing-config docs.
- Keyless signing and transparency log upload have been the default since cosign 2.0; `COSIGN_EXPERIMENTAL` is not needed.
- Verifying with an on-disk key offline no longer requires a trusted root.

When upgrading from 2.x, test both signing and verifying with the new version, and check that consumers on 2.x can still verify what you publish (the cosign 2.x line continues to be released; check the support policy).

## 3. Signing and verifying container images

```bash
# Sign (in CI with an OIDC token available; locally this opens a browser flow)
cosign sign --yes ghcr.io/acme/app@sha256:<digest>

# Verify keyless: identity AND issuer are required
cosign verify ghcr.io/acme/app@sha256:<digest> \
  --certificate-identity "https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# Pattern for any tag of the release workflow
cosign verify ghcr.io/acme/app@sha256:<digest> \
  --certificate-identity-regexp '^https://github\.com/acme/app/\.github/workflows/release\.yml@refs/tags/v[0-9]+\.[0-9]+\.[0-9]+$' \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

- Sign the digest, not a tag. Resolve a tag to a digest with `crane digest IMAGE:TAG` or `docker buildx imagetools inspect`, then deploy by digest.
- For multi-architecture images sign the index digest; `--recursive` also signs each manifest (see `cosign sign --help`).
- `--certificate-identity` and `--certificate-oidc-issuer` have `-regexp` variants; the help text states that one of each pair must be set for keyless flows.
- Anchor regular expressions with `^` and `$` and escape dots; an unanchored pattern can match a longer attacker-controlled string.
- Add `-a key=value` annotations at signing time if you want to verify extra claims; they appear in the signature payload.
- `cosign tree IMAGE` lists signatures, attestations and SBOMs attached to an image.

## 4. Signing and verifying blobs

```bash
# Sign a release archive; the bundle holds signature + certificate + log proof
cosign sign-blob --yes --bundle app-1.4.0.tar.gz.sigstore.json app-1.4.0.tar.gz

# Verify
cosign verify-blob app-1.4.0.tar.gz \
  --bundle app-1.4.0.tar.gz.sigstore.json \
  --certificate-identity "https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

- The verify-blob help says the preferred way to supply verification material is a Sigstore bundle via `--bundle`.
- Verification with a public key uses `--key cosign.pub` together with `--bundle`; with keyed signing the trust anchor is the key, so protect it in a KMS (`awskms://`, `gcpkms://`, `azurekms://`, `hashivault://` references are supported).
- Publish the `.sigstore.json` next to each artifact in the release assets, and list the verification command in the release notes.
- With signed timestamps in the bundle, `verify-blob --use-signed-timestamps` is documented from 2.6.0 for new-format bundles; check help for your version.

## 5. Attestations with cosign

An attestation is a signed in-toto statement about a subject. `cosign attest` signs and attaches one to an image; `verify-attestation` checks it.

```bash
# Attach a CycloneDX SBOM as an attestation (predicate type names are built in)
cosign attest --yes --predicate app.cdx.json --type cyclonedx \
  ghcr.io/acme/app@sha256:<digest>

# Verify and print the statement for a given type
cosign verify-attestation ghcr.io/acme/app@sha256:<digest> --type cyclonedx \
  --certificate-identity "https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# Attestation as a standalone blob bundle, verified against a subject digest
cosign verify-blob-attestation --bundle provenance.sigstore.json \
  --type slsaprovenance1 --digest sha256:<hex> --digestAlg sha256 \
  --certificate-identity "<workflow-url>" --certificate-oidc-issuer "<issuer>"
```

- Built-in `--type` values listed in the help: `slsaprovenance`, `slsaprovenance02`, `slsaprovenance1`, `link`, `spdx`, `spdxjson`, `cyclonedx`, `vuln`, `openvex`, `custom`; a predicate type URI is also accepted.
- `verify-attestation` accepts a `--policy` (Rego or CUE) to evaluate the predicate; for example, require that a vulnerability report has no critical findings. Check the help text for the exact options.
- GitHub's `actions/attest` produces attestations stored with GitHub and verified with `gh attestation verify`; cosign and `gh` verify the same Sigstore bundle format but look in different places. Choose one verification path per consumer and document it.

## 6. Identities for common signers

| Signer | Issuer | Certificate identity (subject) |
|---|---|---|
| GitHub Actions workflow | `https://token.actions.githubusercontent.com` | `https://github.com/<owner>/<repo>/.github/workflows/<file>@<ref>` where ref is `refs/tags/<tag>` or `refs/heads/<branch>` |
| GitHub reusable workflow | same issuer | the subject names the calling workflow; the called workflow is carried in other certificate extensions, so for reusable workflows prefer `gh attestation verify --signer-workflow` or the `--certificate-github-workflow-*` flags in `cosign verify --help` |
| Google account | `https://accounts.google.com` | the email address |
| GitLab CI | the GitLab instance URL | project path and ref as the identity string; confirm in the GitLab Sigstore docs |
| Sigstore public OIDC | `https://oauth2.sigstore.dev/auth` | the email of the authenticated user |

- Inspect what was signed rather than guessing: `cosign verify` prints the certificate subject and issuer in its JSON output when verification passes with a broad regex during investigation. Then tighten the flags.
- A signature by a branch ref (`refs/heads/main`) is weaker than by a tag ref in a protected tag ruleset; pick refs that only trusted maintainers can create.

## 7. Trusted root and offline use

- The client trusts a Sigstore trusted root (Fulcio and Rekor keys and certificates) delivered through TUF. `cosign initialize` fetches and caches it; later runs update it. `--staging` targets the staging instance.
- Air-gapped verification: copy a `trusted_root.json` into the environment and run `cosign verify --trusted-root trusted_root.json ...` (flag shown in the verify help).
- Private Sigstore deployments: use a `--signing-config` for signing and a custom trusted root for verification; the instances publish their own TUF repository.
- Keep the trusted-root refresh working in long-running verifiers; an out-of-date root eventually fails on rotated keys.
- The Go library `sigstore-go` (1.4.0) and the Python `sigstore` package (4.5.1) verify bundles programmatically when shelling out to cosign is not appropriate.

## 8. Policy enforcement

Sigstore policy-controller (admission webhook; `ClusterImagePolicy`):

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: require-release-workflow
spec:
  images:
    - glob: "ghcr.io/acme/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subject: https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0
```

- Namespaces opt in through a label (`policy.sigstore.dev/include: "true"`) per the policy-controller docs; confirm the label and API version for the installed release (0.15.1 at check time).
- Policies can also require attestations of a type and evaluate CUE or Rego over the predicate.
- Subjects can use `subjectRegExp` when several tags must pass; anchor the expression.

Kyverno image verification:

- Kyverno's `ClusterPolicy` has a `verifyImages` rule type that checks cosign signatures and attestations, with keyless (issuer and subject) or key-based attestors. Kyverno 1.19.2 is current; its newer CEL-based `ImageValidatingPolicy` (group `policies.kyverno.io`) is the direction for new policies. Check the Kyverno documentation for the apiVersion and field names for your installed version before writing a policy.
- Run in audit mode first (`validationFailureAction: Audit` on `ClusterPolicy`, or the equivalent action on the newer policy kinds), review violations, then enforce.
- Both engines verify at admission time. Pods already running are not re-verified unless the policy engine background-scans them.
- Require digests: a mutating step (Kyverno `mutateDigest`) can rewrite tags to digests so the signed digest is what runs.
- Admission design (webhook failure policy, exemptions for system namespaces, high availability) belongs to kubernetes-expert.

## 9. Troubleshooting

- "no matching signatures": wrong digest, wrong identity or issuer, or the signature lives in another registry; list with `cosign tree`.
- "none of the expected identities matched": print the certificate subject with a permissive regex in a throwaway shell, then correct the exact value (ref format and `refs/tags/` prefix are the usual mismatches).
- Certificate expired error: the signature lacks a valid log entry or timestamp proof; check that signing used the default transparency log or TSA and that the verifier is not set to ignore it.
- Registry denies referrer artifacts: cosign 3 stores OCI 1.1 referrers; older registries may need a fallback tag scheme. Check the cosign docs for the registry compatibility options.
- TUF errors in air-gapped hosts: provide `--trusted-root` or mirror the TUF repository.
- A `COSIGN_PASSWORD`-style prompt in keyless CI means a key flag or environment variable is set; remove `--key` for keyless.
