---
name: docker-expert
description: >-
  Builds small, reproducible and hardened container images with Dockerfile and BuildKit (multi-stage, cache and secret mounts, buildx multi-platform, SBOM and provenance attestations) and runs multi-container stacks with Docker Compose (healthcheck-gated depends_on, profiles, secrets, include, develop.watch). Use when writing or reviewing a Dockerfile, .dockerignore, compose.yaml or docker-compose.yml, docker buildx or docker compose commands, container healthchecks, rootless Docker, Docker Scout scans, or image signing and pinning. Not for Kubernetes manifests, Helm or operators (use kubernetes-expert), CI pipeline design (use cicd-expert), or reverse proxy configuration (use nginx-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Docker Expert

This skill covers building container images and running them with Docker Engine and Docker Compose: Dockerfile structure, BuildKit features, image size and cache behavior, supply-chain controls, runtime hardening, and Compose files for development, testing and single-host deployment. It absorbs the former docker-compose-expert skill; Compose details live in a dedicated reference.

> Verified against Docker Engine 29.9.x, Docker Compose 5.6.x (the successor to Compose v2; the version jumped from 2.x to 5.0), Buildx 0.38.x, Dockerfile frontend `docker/dockerfile:1` and the Compose Specification (2026-10).

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

- Covered: Dockerfile, `.dockerignore`, BuildKit and `docker buildx`, multi-stage and multi-platform builds, build cache, secret handling at build and run time, SBOM and provenance attestations, Docker Scout, image signing and digest pinning, `docker run` hardening, rootless mode, HEALTHCHECK, and Docker Compose files and CLI.
- Not covered: Kubernetes workloads (kubernetes-expert), CI pipeline structure and caching in a specific CI system (cicd-expert), nginx configuration inside a container (nginx-expert), cloud registries and ECS/Fargate specifics (aws-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Dockerfile frontend | First line `# syntax=docker/dockerfile:1` selects the latest stable 1.x frontend, so new features (heredocs, `--link`, `--exclude`) work without upgrading the daemon |
| `RUN --mount` | Types `bind`, `cache`, `tmpfs`, `secret`, `ssh`; cache and secret mounts never end up in image layers |
| `COPY` flags | `--from`, `--chown`, `--chmod` (octal or symbolic such as `+x`), `--link` (layer independent of earlier layers, better cache reuse), `--exclude` |
| Heredocs | `RUN <<EOF ... EOF` and `COPY <<EOF /path` write multi-line scripts and files without `&&` chains |
| HEALTHCHECK | Options `--interval` (30s), `--timeout` (30s), `--start-period` (0s), `--start-interval` (5s, Engine 25.0+), `--retries` (3); exit 0 healthy, 1 unhealthy, 2 reserved |
| Attestations | `--sbom=true` and `--provenance=mode=max` (default `min`); `mode=max` includes build-arg values, so never pass secrets as build args |
| Multi-platform | `docker buildx build --platform linux/amd64,linux/arm64 --push`; compile natively per platform or cross-compile with `$BUILDPLATFORM`, `$TARGETARCH` |
| Docker Scout | `docker scout quickview`, `docker scout cves <image>`, `docker scout recommendations <image>` for CVEs and base image advice |
| Rootless mode | Daemon and containers run in a user namespace as a non-root user; set up with `dockerd-rootless-setuptool.sh install` |
| Compose Specification | No top-level `version:` (obsolete, only warns); `name:`, `include:`, `profiles`, `secrets`, `configs`, `develop.watch`, `depends_on.condition` |

## 3. Workflow

1. Identify the runtime: language, build tool, whether a shell or libc is needed at run time, target platforms, and who pulls the image.
2. Write `.dockerignore` first (`.git`, `node_modules`, build output, `.env*`, local secrets), then the Dockerfile.
3. Split into stages: dependency fetch, build, and a minimal runtime stage. Order instructions from least to most frequently changing.
4. Put package-manager caches in `RUN --mount=type=cache` and credentials in `RUN --mount=type=secret`.
5. Set a non-root `USER`, an exec-form `ENTRYPOINT`/`CMD`, a `HEALTHCHECK` where the image has a probe binary, and `STOPSIGNAL` if the app needs a non-default one.
6. Build locally with `docker buildx build`, then inspect: `docker history`, `docker image inspect`, `docker scout quickview`.
7. For stacks, model services in `compose.yaml`, gate startup on `service_healthy`, keep secrets in `secrets:`, validate with `docker compose config`.
8. In CI, build with `--sbom=true --provenance=mode=max`, scan, push, sign by digest, and deploy by digest or immutable tag.

## 4. Decision Rules

- Runtime base: static binaries (Go, Rust) go on `scratch` or a distroless `static` image; JVM, Node and Python use a slim or distroless variant of the language image; use Alpine only after confirming musl compatibility (native wheels, DNS and locale behavior differ from glibc).
- Distroless and `scratch` images have no shell, so `HEALTHCHECK CMD curl ...` fails there; build a `healthcheck` subcommand into the binary or define the probe in Compose using a tool that exists in the image.
- Use `COPY` for local files and `ADD` only for local tar auto-extraction or a Git/URL source that is pinned and verified (`ADD --checksum=sha256:... <url>`); prefer a download in a `RUN` step with checksum verification when the tool is not available.
- Pass configuration through `ENV`/`ARG` only when it is non-sensitive. Build-time credentials use `--mount=type=secret`; runtime credentials use Compose or orchestrator secrets mounted as files.
- Tag strategy: immutable version tags (`1.4.2`) plus a digest for deployment; `latest` only as a convenience alias, never as a deploy reference.
- One process per container is the default. Use `init: true` (Compose) or `docker run --init` when the app spawns children and does not reap zombies.
- Prefer `docker compose` (the Compose plugin) over the end-of-life standalone `docker-compose` v1 binary; commands are otherwise similar.
- Single-host Compose is fine for development, CI and small deployments; choose an orchestrator when scheduling across hosts, rolling updates or autoscaling are required (kubernetes-expert).

## 5. Coding Standards

- Start with `# syntax=docker/dockerfile:1`. Use uppercase instruction names and `AS build` style stage names.
- Use exec form (`["/app", "--port", "8080"]`) for `ENTRYPOINT` and `CMD` so signals reach the process; shell form wraps it in `/bin/sh -c`.
- Combine related `apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*` in one `RUN`, or use cache mounts with `sharing=locked`.
- Pin base images by tag and, for production, by digest (`FROM node:22-slim@sha256:...`); automate bumps with Renovate or Dependabot.
- Declare `ARG`s after the `FROM` they belong to; an `ARG` before `FROM` is only visible to `FROM` lines.
- Set `WORKDIR` explicitly; never `RUN cd`. Use `COPY --chown=app:app` or `--chmod` instead of a later `chown -R`, which duplicates layers.
- Add `LABEL org.opencontainers.image.source`, `.revision`, `.version` for traceability.
- In Compose, use `compose.yaml`, omit `version:`, use long syntax when it carries intent (ports, volumes, depends_on), and quote ports (`"127.0.0.1:8080:8080"`).
- The Dockerfile build checks (`# check=error=true`) turn lint warnings such as `JSONArgsRecommended` and `StageNameCasing` into build failures; enable them in CI.

## 6. Project Structure

```
.
├── Dockerfile                 # multi-stage; targets: build, test, runtime
├── .dockerignore
├── compose.yaml               # base stack: services, networks, volumes
├── compose.override.yaml      # local dev overrides, loaded automatically (optional)
├── compose.prod.yaml          # explicit prod overlay: -f compose.yaml -f compose.prod.yaml
├── .env.example               # variable names with dummy values; real .env is gitignored
├── secrets/                   # gitignored; files referenced by Compose secrets
└── docker/
    ├── healthcheck.sh         # probe for images that have a shell
    └── entrypoint.sh          # only when init logic is unavoidable; ends with exec "$@"
```

## 7. Design Patterns

- **Multi-stage build**: a `build` stage with the full toolchain, an optional `test` stage (`docker build --target test`), and a final stage that copies only artifacts via `COPY --link --from=build`.
- **Cache-friendly layering**: copy the dependency manifest, install with a cache mount, then copy sources; a source edit no longer reinstalls dependencies.
- **Bind-mount manifests**: `RUN --mount=type=bind,source=package.json,target=package.json` avoids a layer for files only needed during install.
- **Build-time secret**: `RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci`, built with `--secret id=npmrc,src=$HOME/.npmrc`; the file never enters a layer.
- **Healthcheck-gated startup** (Compose): `depends_on: db: {condition: service_healthy}` so the app starts after the database accepts connections.
- **Overlay files and `include`**: a base `compose.yaml` plus overlays for environments; `include:` to compose another team's stack as a unit.
- **Network tiering**: a public `edge` network for the proxy, an `internal: true` backend network for databases.
- Details and full Compose examples: [references/compose.md](references/compose.md).

## 8. Best Practices

- Keep the build context small; `docker buildx build` sends the whole context unless `.dockerignore` excludes it.
- Make builds reproducible: pinned base digests, lockfile installs (`npm ci`, `pip install --require-hashes`, `go mod download`), no `apt-get upgrade`.
- Use `docker buildx bake` (a `docker-bake.hcl` file) for several targets or platforms with shared settings.
- Write logs to stdout and stderr and let the runtime collect them; do not log to files inside the container.
- Handle `SIGTERM` in the application and set `stop_grace_period` (Compose) or `--stop-timeout` to match shutdown time.
- Use named volumes for state and tmpfs for scratch data; keep the container filesystem disposable.
- Give each Compose project a `name:` so volume and network names are stable.

## 9. Performance

- Layer order and cache mounts dominate rebuild time: dependencies first, sources last, caches under `/root/.cache`, `/go/pkg/mod`, `/root/.npm`, `/var/cache/apt`.
- `COPY --link` keeps a copied layer independent of the layers below it, so changing a base image or earlier layer does not force re-copying.
- Select a small runtime base and strip build tools; measure with `docker image ls` and `docker history --no-trunc`, or `dive`.
- In CI, use a remote cache backend (`--cache-from type=registry,ref=... --cache-to type=registry,ref=...,mode=max` or the GitHub Actions cache) so ephemeral runners reuse layers.
- Prefer native builders per architecture over QEMU emulation for multi-platform builds; cross-compile in the build stage where the toolchain supports it.
- Set resource limits (`mem_limit`, `cpus`, `pids_limit` in Compose; `--memory`, `--cpus`, `--pids-limit` in `docker run`) and tune the runtime to honor them (for example JVM container awareness).

## 10. Security

- No secrets in images: not in `ENV`, `ARG`, `COPY`d `.env` files or layers. `docker history` and `mode=max` provenance expose build args and environment values. Use secret mounts at build time and Compose `secrets:` (or an orchestrator secret store) at run time.
- Run as non-root: create a user with a fixed UID (`RUN groupadd -r app && useradd -r -g app -u 10001 app`, then `USER 10001:10001`), or use a `:nonroot` distroless tag.
- Harden at run time: `read_only: true` with `tmpfs` for writable paths, `cap_drop: [ALL]` (add back only what is needed), `security_opt: ["no-new-privileges:true"]`, resource limits, and no `privileged: true`.
- Do not mount `/var/run/docker.sock` into a container. Access to the socket is root-equivalent on the host: the container can start a privileged container and mount the host filesystem. If a tool truly needs it (CI agents, some proxies), put a socket proxy with an API allowlist in front or use a rootless daemon.
- Published ports bypass host firewall rules such as UFW because Docker writes its own iptables/nftables rules. Bind to loopback (`127.0.0.1:5432:5432`) or do not publish at all; databases and admin tools stay on internal networks.
- Pin and verify: base images by digest, downloads by checksum, images signed (cosign) and verified at deploy.
- Scan in CI with Docker Scout (`docker scout cves`) or another scanner; fail on fixable critical and high findings and rebuild regularly for base image patches.
- Attach SBOM and provenance attestations (`--sbom=true --provenance=mode=max`) so consumers can audit what is inside.
- Consider rootless mode (or user namespace remapping) for hosts that run untrusted workloads; it limits the impact of daemon and runtime vulnerabilities.
- Details: [references/image-security.md](references/image-security.md).

## 11. Testing

- Lint Dockerfiles with the built-in checks (`docker build --check .`) and optionally `hadolint`.
- Test the image, not only the code: a `test` stage run with `docker build --target test`, or container-structure-test, or a smoke test that starts the container and probes the health endpoint.
- Validate Compose files with `docker compose config --quiet` in CI; render the final model with `docker compose config` to review merges and interpolation.
- Integration tests: `docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests`, then `docker compose down -v`.
- Check non-root and read-only behavior explicitly: `docker run --rm --read-only --user 10001 image` should start.
- Verify multi-platform manifests with `docker buildx imagetools inspect <ref>` and attestations with `docker buildx imagetools inspect <ref> --format '{{ json .Provenance }}'` (or `.SBOM`).

## 12. Review Checklist

- [ ] First line `# syntax=docker/dockerfile:1`; base images pinned (digest for production).
- [ ] Multi-stage; runtime stage has no compilers, package managers' caches or source.
- [ ] `.dockerignore` excludes `.git`, dependencies, build output and env or key files.
- [ ] `USER` is non-root; `ENTRYPOINT`/`CMD` in exec form.
- [ ] No secrets in `ENV`, `ARG`, `COPY` or layers; secret mounts used for build credentials.
- [ ] `HEALTHCHECK` (or Compose `healthcheck`) matches what exists in the image; dependents use `service_healthy`.
- [ ] No `privileged`, no docker socket mount, no `network_mode: host` without a reason, ports bound to loopback unless public.
- [ ] Compose file has no `version:`; secrets use `secrets:`; real `.env` is not committed.
- [ ] Resource limits, restart policy and `stop_grace_period` set for long-running services.
- [ ] CI builds with attestations, scans, signs by digest and deploys by digest or immutable tag.

## 13. Production Notes

- Deploy by digest (`image: registry.example.com/app@sha256:...`) or an immutable tag; roll back by redeploying the previous digest.
- Restart policy: `restart: unless-stopped` for single-host Compose; use `docker compose up -d --wait` in deploy scripts so the command returns after services are running (and healthy, when a healthcheck exists).
- Keep `docker system prune` out of production hosts without filters; use `docker image prune --filter until=168h` and `docker builder prune --filter until=168h` on build hosts.
- Docker Engine releases quickly; track security advisories and update the daemon, not only images. Check the current Engine release notes before upgrading across major versions.
- Docker Compose is not a multi-host scheduler: it does not reschedule containers if the host dies. Document that single point of failure or move to an orchestrator.
- Healthcheck results do not restart containers by themselves in plain Docker Engine; the `restart` policy reacts to process exit only. Use an external supervisor or orchestrator if unhealthy must trigger a restart.
- Rootless Docker has limits (privileged ports below 1024 need a sysctl, some storage and networking features differ); read the rootless prerequisites before choosing it.

## 14. Examples

Go service on a distroless static image with cache mounts, a private-module secret and a non-root user:

```dockerfile
# syntax=docker/dockerfile:1
ARG GO_VERSION=1.25
FROM golang:${GO_VERSION} AS build
WORKDIR /src
# Dependencies first: cached until go.mod or go.sum changes.
# The optional netrc secret is mounted only for this step and never stored in a layer.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=bind,source=go.mod,target=go.mod \
    --mount=type=bind,source=go.sum,target=go.sum \
    --mount=type=secret,id=netrc,target=/root/.netrc \
    go mod download
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=bind,target=. \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/app

FROM gcr.io/distroless/static:nonroot AS runtime
LABEL org.opencontainers.image.source="https://github.com/example/app"
COPY --link --from=build /out/app /app
USER nonroot:nonroot
EXPOSE 8080
# No shell here, so the probe is a subcommand of the binary itself.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["/app", "healthcheck"]
ENTRYPOINT ["/app"]
```

Build, attest and scan (the secret comes from a file or environment variable, not a build arg):

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --secret id=netrc,src=$HOME/.netrc \
  --sbom=true --provenance=mode=max \
  -t registry.example.com/shop/api:1.4.2 --push .

docker scout cves registry.example.com/shop/api:1.4.2
docker buildx imagetools inspect registry.example.com/shop/api:1.4.2
```

Compose stack with a healthcheck-gated database, file-based secret, hardened app container and no published database port:

```yaml
name: shop
services:
  api:
    image: registry.example.com/shop/api:1.4.2
    ports:
      - "127.0.0.1:8080:8080"        # front it with a reverse proxy; do not expose directly
    depends_on:
      db:
        condition: service_healthy
        restart: true
    environment:
      DB_HOST: db
      DB_USER: app
      DB_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    init: true
    restart: unless-stopped
    networks: [frontend, backend]

  db:
    image: postgres:18
    environment:
      POSTGRES_USER: app
      POSTGRES_DB: app
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
    volumes:
      - db-data:/var/lib/postgresql   # Postgres 18+ image; older images use /var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    networks: [backend]

networks:
  frontend: {}
  backend:
    internal: true                   # no outbound or inbound access from outside the project

volumes:
  db-data: {}

secrets:
  db_password:
    file: ./secrets/db_password.txt  # gitignored; created out of band
```

## 15. Common Mistakes

- **`ENV DB_PASSWORD=...` or `ARG TOKEN`**: visible in `docker history`, `docker inspect` and provenance. Use secret mounts and file-based secrets.
- **`COPY . .` without `.dockerignore`**: copies `.git`, `.env` and `node_modules` into the image and busts the cache on every commit.
- **Shell-form `CMD npm start`**: the shell is PID 1 and swallows `SIGTERM`; the container is killed after the grace period. Use exec form and handle signals, or `init: true`.
- **`FROM image:latest` and unpinned `apt-get install`**: builds change silently. Pin tags or digests.
- **Running as root "because it works"**: file ownership and port 80 are usually the cause; fix ownership with `COPY --chown`, use a high port, and add `USER`.
- **`depends_on: [db]` as readiness**: it waits only for the container to start. Use `condition: service_healthy` with a real healthcheck.
- **`version: "3.8"` in compose.yaml**: obsolete and ignored with a warning; delete it. The file is validated against the latest Compose Specification.
- **`ports: ["5432:5432"]` for a database**: published on all interfaces and not filtered by the host firewall. Drop it, or bind `127.0.0.1`.
- **Mounting `/var/run/docker.sock`** for convenience: grants root on the host to anything in the container.
- **Healthcheck uses `curl` in an image without curl**: the container reports unhealthy forever; probe with a tool present in the image.
- **Large `chown -R` or `chmod -R` layers**: duplicate file data; use `COPY --chown` and `--chmod`.
- **`mode=max` provenance with secrets in build args**: the values are recorded in the attestation.

## 16. References

- [references/dockerfile-buildkit.md](references/dockerfile-buildkit.md): Dockerfile instructions, cache and secret mounts, heredocs, multi-stage targets, buildx, bake, multi-platform and cache backends.
- [references/compose.md](references/compose.md): Compose Specification file anatomy, healthcheck dependencies, profiles, include, extends, secrets and configs, develop.watch, overlays, CLI workflows, dev/prod/CI examples.
- [references/image-security.md](references/image-security.md): hardening runtime flags, rootless mode, SBOM and provenance, Docker Scout, signing and verification with cosign, base image selection.
- Official docs: https://docs.docker.com/reference/dockerfile/ , https://docs.docker.com/reference/compose-file/ , https://docs.docker.com/build/ , https://docs.docker.com/engine/security/rootless/
