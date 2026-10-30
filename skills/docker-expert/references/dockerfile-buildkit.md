# Dockerfile and BuildKit

Reference for writing Dockerfiles against the `docker/dockerfile:1` frontend and building with `docker buildx` (BuildKit). Verified against Buildx 0.38.x and Docker Engine 29.9.x (2026-10).

## 1. Frontend and parser directives

```dockerfile
# syntax=docker/dockerfile:1
# check=error=true
```

- `# syntax=docker/dockerfile:1` pulls the latest stable 1.x frontend from the registry, so syntax features do not depend on the installed Engine version. Each feature has a minimum frontend version (`--chmod` 1.2, `--link` 1.4, `--exclude` 1.19, `RUN --mount=type=secret,env=` 1.10).
- `# check=skip=<name,...>` disables named build checks; `# check=error=true` makes warnings fail the build. Run checks without building: `docker build --check .`.
- Parser directives must be first, before any blank line, comment or instruction.

## 2. Instruction notes

| Instruction | Notes |
|---|---|
| `FROM` | `FROM base AS name`; `--platform=$BUILDPLATFORM` runs a stage on the builder's native architecture for cross-compilation |
| `ARG` | Before `FROM`: usable only in `FROM` lines. Inside a stage: re-declare to use. Not secret: visible in `docker history` and `mode=max` provenance |
| `ENV` | Persists in the image and the running container; not for secrets |
| `COPY` | `--from=stage|image`, `--chown=user:group`, `--chmod=755` or `--chmod=+x`, `--link`, `--exclude=pattern` (repeatable) |
| `ADD` | Local tar auto-extract, Git and URL sources; `ADD --checksum=sha256:... https://...` verifies a download |
| `RUN` | `--mount`, `--network` (`default`, `none`, `host`), `--security`; shell form or exec form; heredocs |
| `WORKDIR` | Creates the directory; use instead of `RUN cd` |
| `USER` | Numeric UID:GID is unambiguous and works with Kubernetes `runAsNonRoot` checks |
| `ENTRYPOINT` / `CMD` | Exec form `["bin", "arg"]`; `ENTRYPOINT` is the program, `CMD` the default arguments |
| `HEALTHCHECK` | `--interval`, `--timeout`, `--start-period`, `--start-interval`, `--retries`; `HEALTHCHECK NONE` disables an inherited check; only the last one counts |
| `STOPSIGNAL` | Signal sent on `docker stop`; default `SIGTERM` |
| `EXPOSE` | Documentation only; does not publish ports |
| `VOLUME` | Declares an anonymous volume at run time; avoid for paths you want to modify in later `RUN` steps |
| `SHELL` | Changes the shell for shell-form instructions, for example `SHELL ["/bin/bash", "-euo", "pipefail", "-c"]` |

`MAINTAINER` is deprecated; use `LABEL org.opencontainers.image.authors=...`.

## 3. RUN --mount

```dockerfile
# Cache: persists between builds, never in the image. Good for package manager caches.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# apt needs exclusive access, so lock the caches
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends gcc

# Secret as a file (default /run/secrets/<id>) or as an environment variable
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
RUN --mount=type=secret,id=API_KEY,env=API_KEY ./fetch-assets.sh

# Bind: read-only view of the build context or another stage, no layer created
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci

# SSH agent forwarding for private Git remotes: docker buildx build --ssh default .
RUN --mount=type=ssh git clone git@github.com:example/private.git
```

- Cache mount options: `id`, `target`, `sharing` (`shared`, `private`, `locked`), `from`, `source`, `ro`, `mode`, `uid`, `gid`. The build must still work with an empty cache.
- Cache mounts live in the builder's local storage and are not exported by `--cache-to`. On ephemeral CI runners they start empty unless the CI system restores them (the Docker docs describe a GitHub Actions approach).
- Secret options: `id`, `target`, `env`, `required`, `mode` (default `0400`), `uid`, `gid`. Supply secrets with `--secret id=npmrc,src=$HOME/.npmrc` or `--secret id=API_KEY` (read from the environment variable `API_KEY`).
- Secrets are not written to layers or provenance. They can still leak if the command echoes them, writes them into the output (for example a `.npmrc` copied into `node_modules`), or the step sets them in `ENV`.

## 4. Heredocs

```dockerfile
RUN <<EOF
set -eu
apt-get update
apt-get install -y --no-install-recommends ca-certificates
rm -rf /var/lib/apt/lists/*
EOF

COPY --chmod=0644 <<EOF /etc/app/config.toml
listen = "0.0.0.0:8080"
log_format = "json"
EOF
```

- Without `set -e` in a heredoc, only the last command's exit status counts. Add `set -eu` or use `SHELL ["/bin/bash", "-eu", "-c"]`.
- Use `<<-EOF` to strip leading tabs, and quote the delimiter (`<<'EOF'`) to prevent variable expansion at the Dockerfile level.

## 5. Multi-stage targets

```dockerfile
FROM node:22-slim AS base
WORKDIR /app

FROM base AS deps
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

FROM base AS build
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci
COPY . .
RUN npm run build

FROM build AS test
RUN npm test

FROM base AS runtime
ENV NODE_ENV=production
COPY --link --from=deps /app/node_modules ./node_modules
COPY --link --from=build /app/dist ./dist
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

- `docker build --target test .` runs only up to the `test` stage; the default target is the last stage.
- BuildKit builds only the stages the target depends on, and builds independent stages in parallel.
- The official `node` images ship a `node` user (UID 1000); check the base image for its non-root user before relying on one.

## 6. Build context and .dockerignore

```
.git
.gitignore
node_modules
dist
coverage
*.log
.env
.env.*
!.env.example
secrets/
*.pem
*.key
Dockerfile*
compose*.yaml
```

- Patterns are rooted at the context; `**` matches across directories; `!` re-includes.
- Excluding the Dockerfile from the context is fine: BuildKit still reads it.
- A per-Dockerfile ignore file `Dockerfile.dockerignore` next to the Dockerfile takes precedence for that Dockerfile.

## 7. buildx

```bash
# One-time: a builder using the docker-container driver (needed for multi-platform, cache export, attestations)
docker buildx create --name ci --driver docker-container --use

# Multi-platform push with attestations
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --sbom=true --provenance=mode=max \
  --cache-from type=registry,ref=registry.example.com/app:buildcache \
  --cache-to type=registry,ref=registry.example.com/app:buildcache,mode=max \
  -t registry.example.com/app:1.4.2 --push .

# Load a single-platform image into the local daemon for testing
docker buildx build --load -t app:dev .

# Inspect the pushed manifest list, SBOM and provenance
docker buildx imagetools inspect registry.example.com/app:1.4.2
```

- `--attest type=sbom` and `--attest type=provenance,mode=max,version=v1` are the long forms of `--sbom` and `--provenance`. Provenance `mode` is `min` (default) or `max`; `version` is `v0.2` (default) or `v1`.
- Attestations require pushing to a registry or exporting with an OCI layout; the classic local image store cannot hold a multi-platform manifest list with attestations. Check the current docs for how the containerd image store changes this.
- `--cache-to type=registry,mode=max` caches intermediate stages too; `mode=min` caches only the final stage's layers. Other backends include `type=gha` (GitHub Actions), `type=s3`, `type=azblob`, `type=local` and `type=inline`.
- Cross-compilation avoids emulation:

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.25 AS build
ARG TARGETOS TARGETARCH
RUN --mount=type=bind,target=. --mount=type=cache,target=/go/pkg/mod \
    CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -o /out/app ./cmd/app
```

- Build args `BUILDPLATFORM`, `TARGETPLATFORM`, `TARGETOS`, `TARGETARCH`, `TARGETVARIANT` are predefined; declare `ARG` in the stage to use them.

## 8. Bake

```hcl
# docker-bake.hcl
variable "TAG" { default = "dev" }

group "default" { targets = ["app"] }

target "app" {
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = ["linux/amd64", "linux/arm64"]
  tags       = ["registry.example.com/app:${TAG}"]
  attest = [
    "type=sbom",
    "type=provenance,mode=max",
  ]
}
```

`TAG=1.4.2 docker buildx bake --push` builds every target in a group with shared settings. `docker buildx bake --print` shows the resolved configuration, and Bake can read a Compose file's `build` sections.

## 9. Debugging builds

- `docker buildx build --progress=plain --no-cache .` shows full output.
- `docker buildx build --target build -t app:debug .` then `docker run --rm -it app:debug sh` explores an intermediate stage.
- `docker history --no-trunc <image>` shows instructions and layer sizes; secrets passed incorrectly appear here.
- `docker buildx du` and `docker buildx prune --filter until=168h` inspect and trim the build cache.
