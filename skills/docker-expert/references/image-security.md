# Image Security and Supply Chain

Hardening container images and the Docker runtime: base image choice, run-time restrictions, rootless mode, SBOM and provenance attestations, Docker Scout, and signing. Verified against Docker Engine 29.9.x, Buildx 0.38.x and the Docker Scout CLI plugin (2026-10).

## 1. Base images

- Prefer minimal bases: `scratch` (static binaries), distroless (`gcr.io/distroless/static:nonroot`, `base`, language variants), or `-slim` language images. Fewer packages means fewer CVEs and fewer tools for an attacker.
- Distroless has no shell or package manager: debugging uses an ephemeral debug container (`docker debug` where available, or a `:debug` tag variant that includes busybox) rather than shipping a shell in production.
- Pin by digest for production and let Renovate or Dependabot propose updates:

```dockerfile
FROM node:22-slim@sha256:<digest> AS runtime
```

- Resolve a digest with `docker buildx imagetools inspect node:22-slim` and record both tag and digest so humans can read the version.
- Official images and Docker Hardened Images, Verified Publisher or internally mirrored bases are better sources than random community images; mirror into your registry so builds do not depend on public availability.
- Rebuild on a schedule even without code changes; base image CVEs are fixed upstream and reach you only when you rebuild.

## 2. Non-root and filesystem

```dockerfile
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --chown=10001:10001 --from=build /out/app /app/app
USER 10001:10001
```

- Use numeric IDs so `USER` works in images without `/etc/passwd` entries and satisfies orchestrator `runAsNonRoot` checks.
- Application code should be owned by root and not writable by the runtime user; give the user write access only to specific data or temp directories.
- Ports below 1024 need extra privileges; listen on 8080 and map at the proxy.
- Avoid setuid binaries: `RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} +` in Debian-based images that do not need them.

## 3. Run-time restrictions

```bash
docker run -d --name api \
  --user 10001:10001 \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 256 --memory 512m --cpus 1 \
  --init \
  -p 127.0.0.1:8080:8080 \
  registry.example.com/shop/api@sha256:<digest>
```

- `--cap-drop ALL` then add only what is required (`--cap-add NET_BIND_SERVICE`).
- The default seccomp profile and AppArmor or SELinux confinement stay on; do not use `--security-opt seccomp=unconfined` or `apparmor=unconfined` as a debugging shortcut left in place.
- Avoid `--privileged`, `--pid=host`, `--network=host`, `--ipc=host`, `--device` of raw hardware without need, and host path mounts of `/`, `/etc`, `/proc`, `/sys` or `/var/run/docker.sock`.
- The Docker socket grants root-equivalent control of the host: a container with it can start a privileged container with the host filesystem mounted. Anything that needs Docker API access (CI runners, dashboards, auto-discovery proxies) should use a restricted socket proxy exposing only the required API calls read-only, or a rootless daemon, and should not be reachable from the internet.
- `--read-only` plus `--tmpfs` for writable paths prevents persistence of dropped files; named volumes only for real state.
- Set `--log-opt max-size` (or a Compose `logging` block) so container logs cannot fill the disk.

## 3a. Network exposure

- `-p 5432:5432` publishes on all host interfaces and Docker adds firewall rules ahead of host tools such as UFW. Bind explicitly (`-p 127.0.0.1:5432:5432`) or keep the service on an internal network without publishing.
- Put services that must not reach the internet on networks created with `internal: true` (Compose) or `docker network create --internal`.

## 4. Rootless mode

Rootless mode runs the daemon and containers inside a user namespace, so a daemon or runtime escape yields an unprivileged host user.

```bash
# as a non-root user, with newuidmap/newgidmap (uidmap package) and /etc/subuid, /etc/subgid entries
dockerd-rootless-setuptool.sh install
systemctl --user enable --now docker
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
```

- Prerequisites: `newuidmap` and `newgidmap` on the host, at least 65,536 subordinate UIDs and GIDs for the user in `/etc/subuid` and `/etc/subgid`.
- Privileged ports (< 1024) need `net.ipv4.ip_unprivileged_port_start` lowered or `CAP_NET_BIND_SERVICE` on `rootlesskit`; prefer publishing high ports.
- Some features differ in rootless mode (network performance, storage drivers, AppArmor, certain `--cap-add` values); read the rootless limitations in the current docs before migrating.
- Rootless is a daemon-level control; it does not replace running containers as non-root inside the image.

## 5. SBOM and provenance

```bash
docker buildx build \
  --sbom=true \
  --provenance=mode=max \
  -t registry.example.com/shop/api:1.4.2 --push .

docker buildx imagetools inspect registry.example.com/shop/api:1.4.2 --format '{{ json .SBOM }}'
docker buildx imagetools inspect registry.example.com/shop/api:1.4.2 --format '{{ json .Provenance }}'
```

- `--sbom=true` is shorthand for `--attest type=sbom`; `--provenance=...` for `--attest type=provenance,...`. Provenance modes: `min` (default) and `max` (more detail: build arguments, Dockerfile source, source maps). Schema `version` is `v0.2` (default) or `v1`.
- `mode=max` records the values of build arguments. If anything credential-like was passed with `--build-arg`, refactor it to `--secret`; secret mounts are never included in provenance.
- Attestations are attached to the image index in the registry; multi-platform images carry one set per platform. Registries and tools that do not understand OCI attestation manifests may display them as extra unknown platforms.
- SBOM scope: by default the scanner reports the final image contents; scanning build stages and application dependencies requires the SBOM generator's scope options, so check the current attestation docs.

## 6. Docker Scout

```bash
docker scout quickview registry.example.com/shop/api:1.4.2           # summary of CVEs by severity
docker scout cves registry.example.com/shop/api:1.4.2                # package-level CVEs
docker scout cves --only-severity critical,high --exit-code IMAGE    # non-zero exit for CI gating
docker scout recommendations IMAGE                                   # base image update suggestions
docker scout compare IMAGE --to IMAGE_PREVIOUS --exit-on vulnerability,policy --only-severity critical,high --ignore-unchanged
```

- Use `--exit-code` in CI so critical and high findings fail the job; handle unfixable findings through documented exceptions (VEX statements or scanner ignore files) rather than disabling the gate.
- Scout reads SBOM attestations when they exist, which gives more accurate results than re-indexing the image.
- Any scanner (Trivy, Grype, Snyk) is acceptable; the important parts are gating on severity, scanning on a schedule for already-published images, and rebuilding after base image fixes.

## 7. Signing and verification

Sign by digest, never by mutable tag. Example with cosign keyless signing from CI (OIDC identity from the CI provider):

```bash
DIGEST=$(docker buildx imagetools inspect registry.example.com/shop/api:1.4.2 --format '{{ .Manifest.Digest }}')
cosign sign --yes registry.example.com/shop/api@${DIGEST}

cosign verify registry.example.com/shop/api@${DIGEST} \
  --certificate-identity "https://github.com/example/shop/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

- Verification must pin the expected signer identity and issuer; verifying without them accepts any valid signature.
- Cosign's flags and bundle format have changed across major versions; check the current cosign documentation for the installed version.
- Enforce verification where images are admitted (admission controller, deploy script) so unsigned images do not run.

## 8. Secrets hygiene

- Build time: `RUN --mount=type=secret,id=...` and `docker buildx build --secret id=...,src=...` (or `env=`). Not `ARG`, `ENV` or `COPY`.
- Run time: Compose `secrets:` or orchestrator secrets mounted as files, read by the app from `/run/secrets/<name>`. Avoid secrets in `docker run -e` because they appear in `docker inspect` and process listings.
- Scan images and repositories for leaked secrets in CI (for example with `gitleaks` or `trufflehog`) and rotate anything that ever reached a layer: deleting a file in a later layer does not remove it from earlier layers.
- Do not commit real `.env` files; commit `.env.example`, add `.env*` to `.gitignore` and `.dockerignore`.
