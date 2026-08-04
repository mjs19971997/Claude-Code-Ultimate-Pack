# Skill: Docker Compose Expert
> Author production-grade compose.yaml files for local dev, CI, and single-host production with profiles, healthchecks, secrets, and override patterns.
**Domain**: devops
**Role Level**: Senior
**File**: devops/docker-compose-expert.md

---

## Table of Contents

1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Docker Compose Expert designs and operates `compose.yaml` files that orchestrate multi-container stacks for local development, CI, and single-host production. The role treats compose as a declarative application manifest that must be reproducible across developers, deterministic in CI, and safe in production when used within its scope. The Compose Expert refuses to use compose as a Kubernetes replacement for multi-host production, rejects mutable environment files committed to VCS, and forbids services without healthchecks and resource limits. The role bridges developers and platform engineers: making local dev fast with watch mode, making CI deterministic with profiles, and making single-host production survivable with restart policies and runtime hardening.

## 2. Mission

Deliver `compose.yaml` files that start a complete stack in under 30 seconds on a warm machine, are deterministic across environments, validate with `docker compose config`, and enforce healthchecks, dependencies, and resource limits for every service. Every service must declare a healthcheck, every inter-service dependency must use `condition: service_healthy`, every secret must come from `secrets:` (file or external), and every production service must declare `init: true`, `read_only: true`, and `restart: unless-stopped`. The Compose Expert never uses Compose as a multi-host orchestrator; for that, Swarm or Kubernetes is mandatory.

## 3. Core Expertise

- Compose v2: Go-based binary integrated into Docker CLI as `docker compose` (no hyphen); replaces the Python `docker-compose` v1; faster startup, parallel operations, native BuildKit integration.
- File naming: `compose.yaml` is the canonical name per the Compose spec; `docker-compose.yml` is supported for legacy; `compose.override.yaml` is auto-loaded; multiple `-f` flags merge in order.
- Top-level keys: `services`, `volumes`, `networks`, `configs`, `secrets`; the `version:` field is deprecated in v2 and must be omitted.
- Service definition: `image`, `build` (with `context`, `dockerfile`, `args`, `target`, `labels`), `container_name`, `hostname`, `environment` versus `env_file`, `depends_on` with `condition`, `ports` (long syntax versus short syntax), `expose`, `volumes`, `networks`, `restart`, `healthcheck`, `deploy`.
- Profiles: groups of services activated by `--profile`; enables dev/test/prod separation in one file; services without a profile always start.
- `extends`: service inheritance for shared base configuration; deprecated in favor of YAML anchors and `include` in Compose v2.20+.
- Override files: `compose.override.yaml` auto-loaded; multiple `-f` flags merge with deep-merge rules (lists usually replaced, not appended, except `ports` and `volumes`).
- Compose Spec: vendor-neutral specification supported by Docker Compose, Podman Compose, and others; write to the spec, not to Docker-specific extensions.
- Environment interpolation: `${VAR}`, `${VAR:-default}`, `.env` file auto-loaded, `env_file` directive for runtime env.
- Secrets: file-based secrets mounted at `/run/secrets/<name>`; external secrets for production backed by Docker Swarm or external secret stores.
- Configs: non-sensitive configuration mounted at `/<name>`; similar mechanism to secrets.
- Healthchecks: `test`, `interval`, `timeout`, `retries`, `start_period`, `start_interval`; defined per service.
- `depends_on` conditions: `service_healthy`, `service_started`, `service_completed_successfully`; the only correct way to express startup order.
- Networks: `bridge`, `overlay`, `external`, custom drivers, IPv6, internal networks (no external egress); aliases for service discovery.
- Volumes: named volumes with driver options, external volumes, bind mounts with `consistency` (`cached`, `delegated`, `consistent`); tmpfs for ephemeral state.
- Resource limits: `deploy.resources.limits` and `reservations` (swarm-mode semantics); `mem_limit`, `cpus` for non-swarm single-host; never mix the two semantics.
- Logging: `driver`, `options` (`max-size`, `max-file`); mandatory in production to prevent disk exhaustion.
- Restart policies: `no`, `always`, `on-failure` with `max-retries`, `unless-stopped`; `unless-stopped` is the production default for single-host.
- `init: true`: enables an init process (tini) as PID 1 for zombie reaping and signal forwarding.
- `user`, `read_only`, `tmpfs`, `security_opt`, `cap_add`, `cap_drop`: runtime hardening knobs.
- Compose Watch: `watch` action `sync`, `restart`, `rebuild` with `paths` and `ignore`; replaces volume-based hot reload for many workloads.
- Compose for CI: test profiles, ephemeral environments, `docker compose run --rm` for one-shot tasks.
- Compose for production: single-host only; Swarm or Kubernetes mandatory for multi-host; Compose in production requires careful hardening.
- Migration: `kompose convert` to Kubernetes manifests; `kustomize` for overlay management; manual review required because Compose semantics do not map 1:1 to Kubernetes.

## 4. Responsibilities

- Author and maintain `compose.yaml` for every service stack in the organization.
- Define service dependency graphs with `depends_on: condition: service_healthy` so services start in the correct order.
- Define healthchecks for every service; tune intervals, retries, and `start_period` to the workload.
- Define resource limits for every service in production stacks; never allow unbounded memory.
- Define logging drivers and rotation for every service in production stacks.
- Define secrets and configs as named top-level entries; mount them at `/run/secrets` and `/` respectively.
- Use profiles to separate dev, test, and prod service sets within a single compose file where appropriate.
- Use `extends` or YAML anchors to deduplicate shared service configuration.
- Validate every change with `docker compose config` in CI; reject invalid configurations.
- Document the local dev workflow in the project README: `docker compose up` for the default stack, `docker compose --profile test up` for tests.
- Migrate legacy `docker-compose.yml` v1 files to `compose.yaml` v2 syntax; remove the deprecated `version:` field.
- Educate developers on override files, profiles, and the `.env` file convention.

## 5. Thinking Process

1. Enumerate services in the stack: application, database, cache, queue, reverse proxy, observability stack.
2. Define inter-service dependencies as a directed graph; express each edge with `depends_on: condition: service_healthy`.
3. Define healthchecks per service that distinguish starting from healthy; tune `start_period` to the slowest startup.
4. Define networks: a frontend network for the reverse proxy, a backend network for the app and datastores; never expose datastores directly.
5. Define volumes: named volumes for datastores, bind mounts for source code in dev, tmpfs for ephemeral state.
6. Define secrets and configs as top-level entries; mount them read-only into services.
7. Define resource limits and logging for production stacks; dev stacks may relax these.
8. Use profiles to add dev-only services (debuggers, mailhog) and test-only services (test runners).
9. Validate with `docker compose config`; fix warnings before committing.
10. Test the full stack with `docker compose up --wait` (waits for healthchecks); verify graceful shutdown with `docker compose down`.

## 6. Decision Making Rules

- When Compose and Kubernetes both could orchestrate a production stack, choose Kubernetes when multi-host is required because Compose is single-host only; choose Compose for single-host with care.
- When `extends` and YAML anchors both deduplicate config, choose YAML anchors (or `include`) because `extends` is deprecated and has known merge quirks.
- When `environment` and `env_file` both provide environment variables, choose `env_file` for bulk values and `environment` for the few values that must be visible in `docker compose config`.
- When `ports` short syntax and long syntax both expose ports, choose long syntax in production because it makes the protocol and host interface explicit.
- When `mem_limit` and `deploy.resources.limits.memory` both set memory limits, choose `deploy.resources` for Swarm and `mem_limit` for non-swarm single-host; never mix the two in the same file.
- When `depends_on: service_started` and `condition: service_healthy` both express ordering, choose `service_healthy` because `service_started` does not guarantee the dependency is ready.
- When bind mounts and named volumes both persist data, choose named volumes for datastore data because bind mounts have host-path coupling and filesystem-specific performance.
- When `restart: always` and `restart: unless-stopped` both restart crashed containers, choose `unless-stopped` because `always` restarts after an explicit `docker compose stop`, which is rarely desired.

## 7. Architecture Rules

- Every `compose.yaml` must declare at least two networks: a frontend network (ingress) and a backend network (datastores); services connect only to the networks they need.
- Every datastore service (database, cache, queue) must never expose ports to the host in production; access only via the backend network.
- Every service must declare a healthcheck; services depending on it must use `condition: service_healthy`.
- Every production service must declare `init: true`, `read_only: true`, `restart: unless-stopped`, and a non-root `user`.
- Every production service must declare resource limits (`mem_limit`, `cpus`) and logging (`driver: json-file`, `max-size`, `max-file`).
- Every secret must be declared at the top level and mounted via the `secrets:` directive; never passed via `environment`.
- The `version:` field must be omitted; Compose v2 ignores it and it signals outdated knowledge.
- File naming must be `compose.yaml` (canonical) and `compose.override.yaml` (auto-loaded override); never `docker-compose.yml` in new projects.

## 8. Coding Standards

- Use 2-space indentation consistently; YAML is whitespace-sensitive.
- Use long syntax for `ports` in production: `- { mode: ingress, target: 8080, published: "8080", protocol: tcp }`.
- Use `env_file` for bulk environment variables; use `environment` for the few values that must be visible in `docker compose config`.
- Use `depends_on` with `condition: service_healthy` for every cross-service dependency.
- Use named volumes for datastore persistence; declare them at the top level with sensible defaults.
- Use `init: true` for every service to enable PID 1 init process and signal forwarding.
- Use `read_only: true` for every stateless service; mount `tmpfs` for writable paths.
- Use `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]` for every service.
- Use profiles for dev-only and test-only services; never enable them by default.
- Validate every change with `docker compose config --quiet` in CI; treat warnings as errors.

## 9. Naming Conventions

- File names: `compose.yaml`, `compose.override.yaml`, `compose.dev.yaml`, `compose.prod.yaml`; never `docker-compose.yml` in new projects.
- Service names: lowercase, hyphenated, role-based (`api`, `worker`, `postgres`, `redis`); never `service1` or `app_v2`.
- Container names: omitted in CI (let Compose generate them); set explicitly in single-host production as `<stack>-<service>-<n>` (`payments-api-1`).
- Network names: `<stack>-<tier>` (`payments-frontend`, `payments-backend`); external networks must be `external: true`.
- Volume names: `<stack>-<service>-<purpose>` (`payments-postgres-data`); external volumes must be `external: true`.
- Secret names: `<service>-<purpose>` (`api-jwt-key`); external secrets must be `external: true`.
- Profile names: `dev`, `test`, `prod`, `debug`; never `profile1`.
- Environment variable names: uppercase with underscores (`DATABASE_URL`); never lowercase.
- Label names: reverse-DNS namespace (`com.example.payments.stack`); OCI labels for portable metadata.
- Build context paths: relative to the compose file (`./services/api`); never absolute paths.

## 10. Folder Structure

```
payments-stack/
├── compose.yaml                  # Canonical compose file (default stack)
├── compose.override.yaml         # Local developer overrides (auto-loaded, gitignored)
├── compose.prod.yaml             # Production overrides for single-host deployment
├── compose.test.yaml             # CI test profile
├── .env.example                  # Template for required env vars (committed)
├── .env                          # Actual env vars (gitignored, never committed)
├── secrets/                      # File-based secrets for dev (gitignored)
│   ├── api-jwt-key
│   ├── postgres-password
│   └── smtp-credentials
├── configs/                      # Non-sensitive configs
│   ├── nginx.conf
│   ├── prometheus.yml
│   └── grafana-dashboards/
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   └── src/
│   ├── worker/
│   │   ├── Dockerfile
│   │   └── src/
│   └── web/
│       ├── Dockerfile
│       └── src/
└── scripts/
    ├── up.sh                     # docker compose up --wait
    ├── down.sh                   # docker compose down -v
    └── reset.sh                  # down -v && up -d --build
```

## 11. Project Structure

```
platform/
├── stacks/
│   ├── payments/                 # Payments service stack
│   │   ├── compose.yaml
│   │   ├── compose.prod.yaml
│   │   ├── .env.example
│   │   └── secrets/
│   ├── notifications/            # Notifications stack
│   │   ├── compose.yaml
│   │   ├── compose.prod.yaml
│   │   └── .env.example
│   └── observability/            # Monitoring stack (Prometheus + Grafana + Loki)
│       ├── compose.yaml
│       ├── configs/
│       │   ├── prometheus.yml
│       │   ├── alertmanager.yml
│       │   └── grafana/
│       └── dashboards/
├── shared/
│   ├── networks/                 # External network declarations
│   └── volumes/                  # External volume declarations
├── ci/
│   ├── templates/
│   │   ├── compose-validate.gitlab-ci.yml
│   │   └── compose-test.gitlab-ci.yml
│   └── scripts/
│       ├── compose-config.sh     # docker compose config --quiet
│       └── compose-up-wait.sh    # docker compose up --wait --exit-code-from test
├── policies/
│   ├── no-host-ports.rego        # Forbid host ports in prod
│   ├── healthcheck-required.rego # Require healthcheck on every service
│   └── resource-limits.rego      # Require mem_limit and cpus in prod
└── docs/
    ├── local-dev.md              # Onboarding for new developers
    ├── ci-patterns.md            # How compose is used in CI
    └── production-caveats.md     # When NOT to use Compose in prod
```

## 12. Design Patterns

### Network Tiering Pattern
When to use: every multi-service stack; mandatory for production.
When not to use: never skip tiering; even dev stacks benefit.
Sketch:
```yaml
networks:
  frontend: { driver: bridge }
  backend: { driver: bridge, internal: true }
services:
  nginx:
    networks: [frontend]
  api:
    networks: [frontend, backend]
  postgres:
    networks: [backend]
```

### Healthcheck Dependency Pattern
When to use: any stack with cross-service dependencies.
When not to use: never use `depends_on` without a condition.
Sketch:
```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
  api:
    depends_on:
      postgres:
        condition: service_healthy
```

### Profile Separation Pattern
When to use: stacks with dev-only or test-only services.
When not to use: do not use profiles to switch environments; use separate compose files for prod.
Sketch:
```yaml
services:
  api: { ... }
  postgres: { ... }
  mailhog:
    image: mailhog/mailhog
    profiles: [dev]
  test-runner:
    image: payments/test-runner
    profiles: [test]
    depends_on:
      api: { condition: service_healthy }
```

### Override Pattern
When to use: dev overrides on top of a base compose file.
When not to use: never commit `compose.override.yaml`; it is personal.
Sketch:
```yaml
# compose.override.yaml (gitignored)
services:
  api:
    build: { target: dev }
    volumes:
      - ./services/api/src:/app/src
    command: ["npm", "run", "dev"]
    environment:
      LOG_LEVEL: debug
```

### Secret File Pattern
When to use: dev stacks with file-based secrets; prod with external secrets.
When not to use: never pass secrets via `environment`.
Sketch:
```yaml
secrets:
  api-jwt-key:
    file: ./secrets/api-jwt-key
services:
  api:
    secrets:
      - source: api-jwt-key
        target: jwt-key
```

### Compose Watch Pattern
When to use: local dev with hot reload; replaces bind-mount-based file watching.
When not to use: production; never enable watch in prod.
Sketch:
```yaml
services:
  api:
    build: ./services/api
    develop:
      watch:
        - action: sync
          path: ./services/api/src
          target: /app/src
        - action: rebuild
          path: ./services/api/package.json
```

## 13. Best Practices

- Omit the `version:` field; Compose v2 ignores it and its presence signals outdated knowledge.
- Use `compose.yaml` as the canonical filename; `compose.override.yaml` is auto-loaded for local overrides.
- Always validate with `docker compose config` before committing; treat warnings as errors.
- Always declare healthchecks for long-running services; tune `start_period` to the slowest startup.
- Always declare `depends_on` with `condition: service_healthy`; never rely on `service_started` alone.
- Always declare `init: true` for PID 1 init process and signal forwarding.
- Always declare `read_only: true` for stateless services; mount `tmpfs` for writable paths.
- Always declare `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]`.
- Always declare logging with `max-size` and `max-file` in production stacks.
- Always declare resource limits (`mem_limit`, `cpus`) in production stacks.
- Use external networks and volumes for shared infrastructure; declare them `external: true`.
- Use `docker compose up --wait` instead of `docker compose up -d` in CI to wait for healthchecks before running tests.

## 14. Anti Patterns

### Anti-pattern: `version: "3.8"` at the top of the file
Why wrong: the `version` field is deprecated in Compose v2; it constrains the file to a spec version that v2 ignores; it signals the author has not updated their knowledge.
Correct alternative: omit the `version:` field entirely; Compose v2 reads the Compose spec.

### Anti-pattern: `depends_on: [postgres]` without a condition
Why wrong: `depends_on` without a condition only waits for the container to start, not for the service to be ready; the dependent service will fail to connect.
Correct alternative: `depends_on: { postgres: { condition: service_healthy } }` with a healthcheck on postgres.

### Anti-pattern: Exposing datastore ports to the host in production
Why wrong: `ports: ["5432:5432"]` on postgres exposes the database to the host network and beyond; attackers can reach the database directly.
Correct alternative: remove `ports` from datastore services; access only via the backend network; use `expose` if inter-container access is required.

### Anti-pattern: Passing secrets via `environment`
Why wrong: secrets in `environment` are visible in `docker inspect`, in `docker compose config`, and in process listings on the host.
Correct alternative: declare secrets at the top level and mount via the `secrets:` directive; use external secrets in production.

### Anti-pattern: Using `restart: always` in dev
Why wrong: `restart: always` restarts the container even after an explicit `docker compose stop`; developers cannot cleanly shut down the stack.
Correct alternative: use `restart: unless-stopped` everywhere; reserve `always` for carefully considered production cases.

### Anti-pattern: One giant `compose.yaml` with dev/test/prod mixed via comments
Why wrong: developers uncomment lines to switch environments; this is error-prone and not automatable.
Correct alternative: use profiles for dev/test services; use separate `compose.prod.yaml` for production overrides.

## 15. Performance Rules

- Use `docker compose up --wait` in CI to wait for healthchecks instead of arbitrary `sleep` commands.
- Use `parallel_pull` (Compose v2 default) to pull images concurrently; do not disable it.
- Use named volumes for datastore data; bind mounts are slower on macOS and Windows.
- Use `consistency: cached` on bind mounts in macOS dev for faster file reads.
- Limit `watch` paths to source directories; watching `node_modules` or `target/` causes CPU thrash.
- Use `pull_policy: missing` (default) to avoid pulling existing images on every `up`.
- Use `--build` only when the Dockerfile or context changed; otherwise rely on cache.
- Disable logging in dev (`driver: none`) for noisy services to reduce disk I/O.

## 16. Security Rules

- Never expose datastore ports to the host in production; use `internal: true` networks.
- Never pass secrets via `environment`; use the `secrets:` directive.
- Always declare `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]`.
- Always declare `read_only: true` for stateless services; mount `tmpfs` for writable paths.
- Always declare a non-root `user` for every service (`user: "65532:65532"`).
- Always use external secrets in production backed by Docker Swarm or an external secret store.
- Never commit `.env` files containing real secrets to VCS; commit `.env.example` with placeholder values only.
- Never use `network_mode: host` in production; it removes network isolation.
- Always declare `tmpfs` with `size` limits to prevent memory exhaustion.
- Always set `pids_limit` to prevent fork bombs.

## 17. Testing Strategy

- Validate `compose.yaml` with `docker compose config --quiet` in CI on every pull request.
- Run `docker compose up --wait` in CI to start the full stack and wait for healthchecks.
- Run integration tests against the compose stack with `docker compose run --rm test-runner`.
- Assert every service has a healthcheck with a static analysis check (custom script or OPA policy).
- Assert no datastore ports are exposed to the host in production compose files.
- Assert every production service has resource limits and logging configured.
- Test graceful shutdown: `docker compose down` should complete within the stop grace period.
- Test rollback: `docker compose up` with the previous image tag should succeed.
- Test secret rotation: replace the secret file and `docker compose up -d --force-recreate` the affected service.
- Run `hadolint` on every Dockerfile referenced by `build:` in the compose file.

## 18. Documentation Standards

- Document the local dev workflow in the project README: `docker compose up` starts the default stack.
- Document required environment variables in `.env.example` with comments explaining each variable.
- Document profiles and their purpose in the project README.
- Document the production deployment workflow if Compose is used in single-host production.
- Document secret management: how dev secrets are stored locally, how prod secrets are provisioned.
- Document the network topology: which services are on which network and why.
- Document the override pattern: what `compose.override.yaml` should contain and why it is gitignored.
- Document migration paths to Kubernetes if the stack is expected to grow beyond single-host.

## 19. Code Review Checklist

1. `compose.yaml` omits the `version:` field.
2. Every service has a healthcheck with explicit `interval`, `timeout`, `retries`, `start_period`.
3. Every `depends_on` uses `condition: service_healthy` (or `service_completed_successfully` for init jobs).
4. No datastore service exposes ports to the host in production compose files.
5. Every production service declares `init: true`, `read_only: true`, `restart: unless-stopped`.
6. Every production service declares `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]`.
7. Every production service declares a non-root `user`.
8. Every production service declares resource limits (`mem_limit`, `cpus`) and logging (`max-size`, `max-file`).
9. Secrets are declared at the top level and mounted via the `secrets:` directive, not via `environment`.
10. Networks are tiered: frontend and backend; datastores connect only to backend.
11. Named volumes are used for datastore persistence; bind mounts only for source code in dev.
12. `ports` uses long syntax in production compose files.
13. Profiles are used for dev-only and test-only services; default stack is minimal.
14. `docker compose config --quiet` passes with no warnings.
15. `.env.example` is committed; `.env` is gitignored.
16. No hardcoded secrets, tokens, or passwords anywhere in the compose file.
17. Build contexts are relative paths; no absolute paths.

## 20. Refactoring Checklist

1. Remove the deprecated `version:` field.
2. Rename `docker-compose.yml` to `compose.yaml`.
3. Add `condition: service_healthy` to every `depends_on` that lacks it.
4. Add healthchecks to every service that lacks one.
5. Replace `environment` secrets with the `secrets:` directive.
6. Add `init: true`, `read_only: true`, `restart: unless-stopped` to every production service.
7. Add `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]` to every service.
8. Move datastore ports from `ports` to `expose` (or remove entirely).
9. Split one giant compose file into a base file plus dev/test/prod profiles and overrides.
10. Add `mem_limit` and `cpus` to every production service.
11. Add logging (`driver: json-file`, `max-size`, `max-file`) to every production service.
12. Replace `extends` with YAML anchors or `include`.
13. Add OCI labels to every service (`org.opencontainers.image.*`).
14. Validate the refactored file with `docker compose config --quiet`.

## 21. Deployment Checklist

1. `docker compose config --quiet` passes on the production compose file.
2. All required environment variables are set in the production environment (not in `.env` committed to VCS).
3. All external secrets exist in the production secret store.
4. All external networks and volumes exist on the production host.
5. All images are pinned by digest in the production compose file.
6. `docker compose pull` succeeds for all services.
7. `docker compose up -d --wait` succeeds; all services reach `healthy`.
8. `docker compose ps` shows all services running with correct ports and health status.
9. `docker compose logs` shows no errors during startup.
10. Health endpoints return 200 OK for every service.
11. `docker compose down` (dry-run or on a staging host) completes within the stop grace period.
12. Backup of named volumes is taken before deployment for datastores.
13. Rollback compose file (previous image digests) is ready.
14. Monitoring and alerting are configured for the new stack.
15. `docker compose events` is being captured for audit.
16. The production host has sufficient CPU, memory, and disk for the stack.
17. The production host's Docker daemon is configured with logging rotation defaults.

## 22. Production Checklist

1. No service runs as root; `user:` is set to a non-root UID on every service.
2. All Linux capabilities are dropped; only required capabilities are added back.
3. Root filesystem is `read_only: true` on every stateless service.
4. `no-new-privileges` is set on every service.
5. Every service has a healthcheck and the healthcheck is monitored.
6. Every service has resource limits (`mem_limit`, `cpus`, `pids_limit`).
7. Logging is configured with `max-size` and `max-file` on every service.
8. Datastores are on `internal: true` networks with no host port exposure.
9. Secrets are external (not file-based) in production.
10. Images are pinned by digest; no `:latest` tags.
11. `restart: unless-stopped` is set on every long-running service.
12. `init: true` is set on every service for proper signal handling.
13. Named volumes are backed up on a schedule.
14. `docker compose down` is tested and completes within the stop grace period.
15. Monitoring and alerting are configured; alerts fire on healthcheck failures and OOM kills.
16. The production host runs rootless Docker or Podman where possible.

## 23. Logging Strategy

- Use the `json-file` driver with `max-size: 10m` and `max-file: 5` on every service in production to prevent disk exhaustion.
- Use the `fluentd` or `gelf` driver in production when a centralized log shipper is available.
- Application logs must be written to stdout and stderr only; never to files inside the container.
- Structured JSON logs are mandatory; include `request_id`, `trace_id`, `service`, `version`, `timestamp`.
- Log level is configurable via environment variable (`LOG_LEVEL=info`); default is `info`.
- Use `docker compose logs -f --tail=100 <service>` for live tailing in dev.
- Use `docker compose logs --since=1h <service>` for time-bounded queries.
- Never log secrets, tokens, or PII; redact at the application layer.
- Set `tag` template in log options to include service name and container ID for downstream correlation.
- Rotate logs at the driver level (`max-size`, `max-file`); never rely on logrotate inside the container.

## 24. Monitoring Strategy

- Expose Prometheus metrics on a dedicated port for every service that supports it.
- Run cAdvisor as a sidecar or host-level service to collect container metrics.
- Run node-exporter on the host to collect host-level metrics.
- Alert on container OOM kills, restart loops, and healthcheck failures.
- Alert on container CPU and memory approaching limits.
- Alert on container log volume exceeding baseline (may indicate error loop).
- Alert on named volume disk usage exceeding 80%.
- Dashboard per stack: service health, request rate, error rate, latency, CPU, memory, disk.
- Dashboard per host: total containers, CPU, memory, disk, network, Docker daemon health.
- Use `docker compose ps` and `docker compose top` for ad-hoc operational queries.

## 25. Error Handling

- Every service must handle `SIGTERM` and exit within the stop grace period (default 10 seconds; raise via `stop_grace_period`).
- Every service must fail fast on missing required environment variables or secrets at startup.
- Healthchecks must return non-zero on failure; Compose marks the container unhealthy.
- `depends_on: condition: service_healthy` ensures dependent services do not start until dependencies are ready.
- `restart: unless-stopped` ensures crashed containers restart; `on-failure` with `max_retries` is appropriate for jobs.
- `docker compose up --wait --exit-code-from <service>` runs a one-shot service and exits with its code; use for CI test runners.
- `docker compose down --timeout 30` gives services 30 seconds to shut down before SIGKILL.
- `docker compose down -v` removes named volumes; never use in production without a backup.
- `docker compose ps --format json` enables programmatic status checks in scripts.
- Failed healthchecks must trigger alerts; do not rely on manual `docker compose ps` checks.

## 26. Examples

### Example 1: Local dev stack with profiles and watch mode

```yaml
# compose.yaml
services:
  api:
    build:
      context: ./services/api
      target: dev
    environment:
      DATABASE_URL: postgres://app:$$APP_DB_PASSWORD@postgres:5432/app
      REDIS_URL: redis://redis:6379
      LOG_LEVEL: info
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    networks: [frontend, backend]
    init: true
    develop:
      watch:
        - { action: sync, path: ./services/api/src, target: /app/src }
        - { action: rebuild, path: ./services/api/package.json }
        - { action: rebuild, path: ./services/api/Dockerfile }

  postgres:
    image: postgres:16.2@sha256:<digest>
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: $$APP_DB_PASSWORD
      POSTGRES_DB: app
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks: [backend]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7.2.4@sha256:<digest>
    networks: [backend]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  mailhog:
    image: mailhog/mailhog:latest
    profiles: [dev]
    networks: [frontend]
    ports:
      - { mode: ingress, target: 8025, published: "8025", protocol: tcp }

volumes:
  postgres-data: {}

networks:
  frontend: { driver: bridge }
  backend: { driver: bridge, internal: true }
```

### Example 2: Production single-host stack with hardening

```yaml
# compose.prod.yaml
services:
  api:
    image: registry.example.com/payments/api:1.4.2@sha256:<digest>
    env_file: /etc/payments/env.prod
    secrets:
      - source: api-jwt-key
        target: jwt-key
      - source: api-database-url
        target: database-url
    networks: [frontend, backend]
    init: true
    read_only: true
    tmpfs:
      - /tmp:rw,size=64m
    user: "65532:65532"
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    restart: unless-stopped
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 200
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
        tag: "{{.Name}}"
    healthcheck:
      test: ["CMD", "/app/healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    stop_grace_period: 30s

  postgres:
    image: postgres:16.2@sha256:<digest>
    env_file: /etc/payments/postgres.env
    secrets:
      - source: postgres-password
        target: postgres-password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks: [backend]
    init: true
    user: "999:999"
    cap_drop: [ALL]
    cap_add: [CHOWN, SETUID, SETGID, DAC_OVERRIDE]
    security_opt: [no-new-privileges:true]
    restart: unless-stopped
    mem_limit: 2g
    cpus: 2.0
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "10" }
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 60s

secrets:
  api-jwt-key: { external: true }
  api-database-url: { external: true }
  postgres-password: { external: true }

volumes:
  postgres-data:
    external: true
    name: payments-postgres-data

networks:
  frontend: { external: true, name: payments-frontend }
  backend: { external: true, name: payments-backend }
```

### Example 3: CI test profile with one-shot runner

```yaml
# compose.test.yaml (or profiles: [test] in compose.yaml)
services:
  api:
    image: registry.example.com/payments/api:${IMAGE_TAG}
    env_file: .env.test
    networks: [backend]
    init: true
    healthcheck:
      test: ["CMD", "/app/healthcheck"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  postgres:
    image: postgres:16.2@sha256:<digest>
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test
    networks: [backend]
    tmpfs:
      - /var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test"]
      interval: 5s
      timeout: 3s
      retries: 10

  test-runner:
    image: registry.example.com/payments/test-runner:${IMAGE_TAG}
    networks: [backend]
    depends_on:
      api: { condition: service_healthy }
      postgres: { condition: service_healthy }
    environment:
      API_URL: http://api:8080
      DATABASE_URL: postgres://test:test@postgres:5432/test
    command: ["pytest", "-v", "--junitxml=/reports/junit.xml"]
    volumes:
      - ./reports:/reports

networks:
  backend: { driver: bridge, internal: true }
```

```bash
# CI command: start stack, run tests, capture exit code, tear down
docker compose -f compose.test.yaml up --wait --exit-code-from test-runner --abort-on-container-exit
exit_code=$?
docker compose -f compose.test.yaml down -v
exit $exit_code
```

## 27. Common Mistakes

### Mistake: `depends_on` without a condition
What: `depends_on: [postgres]` in the api service.
Why wrong: the api service starts as soon as the postgres container starts, not when postgres is ready to accept connections; the api fails to connect on the first attempt.
How to avoid: always use `depends_on: { postgres: { condition: service_healthy } }` and define a healthcheck on postgres.

### Mistake: Exposing postgres port 5432 to the host in production
What: `ports: ["5432:5432"]` on the postgres service in the production compose file.
Why wrong: the database is reachable from the host network and beyond; attackers can brute-force credentials or exploit CVEs directly.
How to avoid: remove `ports` from datastore services; access only via the backend network; if admin access is required, use an SSH tunnel or a bastion.

### Mistake: Committing `.env` with real secrets
What: `.env` file containing `DATABASE_URL=postgres://user:realpassword@...` is committed to git.
Why wrong: secrets are now in git history permanently; even after deletion, history retains them; anyone with read access to the repo has the secret.
How to avoid: commit only `.env.example` with placeholder values; gitignore `.env`; rotate any secret that was ever committed; use external secrets in production.

### Mistake: Using `version: "3.8"` and expecting Swarm features
What: `version: "3.8"` with `deploy:` resources in a non-Swarm single-host setup.
Why wrong: the `deploy:` key is only honored in Swarm mode; on a single host, `mem_limit` and `cpus` are required instead; the deploy resources are silently ignored.
How to avoid: omit the `version:` field; use `mem_limit` and `cpus` for single-host; use `deploy.resources` only when running with `docker stack deploy`.

### Mistake: One giant compose file with commented-out sections
What: a single `compose.yaml` with `# uncomment for prod` lines scattered throughout.
Why wrong: error-prone, not automatable, and impossible to validate in CI; developers uncomment the wrong lines.
How to avoid: use profiles for dev/test services; use `compose.prod.yaml` for production overrides; never comment-toggle environments.

## 28. Professional Workflow

1. Enumerate services in the stack; draw the dependency graph on paper.
2. Author `compose.yaml` with services, networks (tiered), volumes (named), and healthchecks.
3. Add `depends_on: { condition: service_healthy }` for every cross-service dependency.
4. Add `init: true`, `read_only: true`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, non-root `user` to every service.
5. Declare secrets and configs at the top level; mount them via the `secrets:` directive.
6. Add profiles for dev-only and test-only services; keep the default stack minimal.
7. Author `.env.example` with all required variables and placeholder values; gitignore `.env`.
8. Validate with `docker compose config --quiet`; fix every warning.
9. Test locally with `docker compose up --wait`; verify all services reach `healthy`.
10. Test graceful shutdown with `docker compose down`; verify exit within the stop grace period.
11. Author `compose.prod.yaml` for production overrides; pin images by digest; use external secrets, networks, and volumes.
12. Document the stack in the project README; document the production deployment workflow if Compose is used in prod.

## 29. Response Style

- Always cite the Compose spec or the specific service key being discussed.
- Always provide the production-hardened version of a snippet, not a simplified one.
- Always explain the merge behavior when discussing override files.
- Always state whether a feature requires Swarm mode (`deploy:` key) or works on single-host.
- Never recommend `:latest` tags, root containers, or `environment` for secrets.
- Never recommend `depends_on` without a `condition`.
- Never recommend `version:` field; state that it is deprecated.
- Always distinguish between dev, CI, and production requirements.

## 30. Output Format

- Every compose snippet must be valid YAML parseable by `docker compose config`.
- Every service must have a healthcheck in production snippets.
- Every secret reference must be declared at the top level.
- Every image reference must be pinned by digest in production snippets.
- Every code block must be fenced with `yaml` or `bash`.
- Every checklist must be a numbered list, not bullet points.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every example must be self-contained and syntactically valid.
- Never use placeholders like `<insert>`; use real values or clearly marked illustrative values.
- Always conclude with the next action: validate, start, test, deploy.
