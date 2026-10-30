# Docker Compose

Reference for the Compose Specification and the `docker compose` CLI, absorbed from the former docker-compose-expert skill. Verified against Docker Compose 5.6.x (successor to Compose v2; 5.0.0 skipped 3.x and 4.x on purpose to avoid confusion with the obsolete file format versions) and the Compose Specification (2026-10). Features below note the minimum Compose version where the docs state one.

## 1. File anatomy

```yaml
name: shop                 # optional project name; exposed as COMPOSE_PROJECT_NAME
include: []                # other Compose applications loaded as units
services: {}
networks: {}
volumes: {}
secrets: {}
configs: {}
```

- The top-level `version:` key is obsolete. It is accepted only for backward compatibility, prints a warning, and Compose validates against the latest schema regardless. Remove it.
- Preferred file names: `compose.yaml` (also `compose.yml`, `docker-compose.yaml`, `docker-compose.yml`). `compose.override.yaml` is merged automatically when present.
- Project name precedence: `-p` flag, `COMPOSE_PROJECT_NAME`, top-level `name:`, then the directory name.
- Use `docker compose config` to print the fully merged and interpolated model, and `docker compose config --quiet` to validate only.

## 2. Startup order and health

`depends_on` short syntax only orders container creation. Long syntax:

```yaml
services:
  api:
    depends_on:
      db:
        condition: service_healthy      # wait for the healthcheck to pass
        restart: true                   # restart api when Compose restarts db (2.17.0+)
      migrate:
        condition: service_completed_successfully
      cache:
        condition: service_started
        required: false                 # only warn if cache is unavailable (2.20.0+)
```

Conditions: `service_started` (default), `service_healthy`, `service_completed_successfully` (one-shot jobs such as migrations). A `service_healthy` dependency needs a `healthcheck` on the dependency (or inherited from its image).

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]   # or ["CMD", ...]; ["NONE"] disables
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s        # failures here do not count against retries
      start_interval: 2s       # probe frequency during start_period (2.20.2+; Engine 25.0+)
```

Use `docker compose up -d --wait` so the command blocks until services are running (healthy, where a healthcheck exists). Applications should still retry their own connections: a database can become unhealthy after startup.

## 3. Profiles

Services without `profiles` always start; services with profiles start only when a profile is activated. A service started explicitly by name (`docker compose run tools`) is activated automatically along with its dependencies.

```yaml
services:
  api:
    build: .
  db:
    image: postgres:18
  mailpit:
    image: axllent/mailpit
    profiles: [dev]
  tests:
    build:
      context: .
      target: test
    profiles: [test]
    depends_on:
      db:
        condition: service_healthy
```

```bash
docker compose up -d                                  # api + db
docker compose --profile dev up -d                    # + mailpit
COMPOSE_PROFILES=dev,test docker compose up          # several profiles
docker compose --profile "*" up                       # all profiles
```

## 4. Secrets and configs

```yaml
services:
  api:
    build:
      context: .
      secrets: [npm_token]             # build-time secret (BuildKit secret mount)
    secrets:
      - db_password                    # mounted at /run/secrets/db_password
      - source: api_key
        target: api_key
        uid: "10001"
        mode: 0400
    configs:
      - source: app_config
        target: /etc/app/config.toml

secrets:
  db_password:
    file: ./secrets/db_password.txt    # gitignored
  api_key:
    environment: API_KEY               # taken from the shell environment of the Compose CLI
  npm_token:
    environment: NPM_TOKEN

configs:
  app_config:
    file: ./config/app.toml
```

- Secrets are mounted as files under `/run/secrets/` (tmpfs); read them in the app, or use the `*_FILE` convention supported by official images such as `postgres` and `mysql` (`POSTGRES_PASSWORD_FILE`).
- Build secrets in `build.secrets` reach the Dockerfile through `RUN --mount=type=secret,id=npm_token`; they are not part of the image.
- `configs` are for non-sensitive configuration; both can be `external: true` or have a `name:`.
- Avoid `environment:` for passwords: values show up in `docker inspect`, `docker compose config`, and process environments. Never commit real `.env` files; commit `.env.example`.
- `env_file` accepts a list with `required: false` for optional files and `format: raw` to disable interpolation inside the file.

## 5. Networks and exposure

```yaml
services:
  proxy:
    image: nginx:1.30
    ports:
      - "80:80"
      - "443:443"
    networks: [edge, app]
  api:
    expose: ["8080"]          # reachable by other services, not published to the host
    networks: [app, data]
  db:
    networks: [data]

networks:
  edge: {}
  app: {}
  data:
    internal: true            # no external connectivity
```

- Services on the same user-defined network reach each other by service name; the default network is created per project.
- `ports` publishes to the host and bypasses host firewall tools such as UFW; use `127.0.0.1:` prefixes for host-only access, and publish only the edge proxy.
- `expose` documents and opens a port only between containers; it does not publish.

## 6. Includes, overlays and extends

Merge multiple files (later files override earlier ones; mappings merge, sequences append):

```bash
docker compose -f compose.yaml -f compose.prod.yaml config
docker compose -f compose.yaml -f compose.prod.yaml up -d --wait
```

Remove or replace inherited values with the custom tags:

```yaml
# compose.prod.yaml
services:
  api:
    ports: !override
      - "127.0.0.1:8080:8080"
    environment:
      LOG_LEVEL: !reset null
```

`include` loads other Compose files as separate applications, each with its own project directory for relative paths; name conflicts produce a warning and are not merged:

```yaml
include:
  - ../platform/compose.yaml
  - path: ../observability/compose.yaml
    project_directory: ../observability
    env_file: ../observability/.env
services:
  api:
    depends_on: [platform-db]     # a service defined in the included file
```

`extends` shares a service definition (`extends: {file: common.yaml, service: base}`); referenced resources such as networks, volumes and secrets are not imported automatically and must be declared in the extending model.

## 7. Development with `develop.watch`

Available from Compose 2.22.0; `sync+restart` needs 2.23.0 and `restart` and `sync+exec` need 2.32.0.

```yaml
services:
  web:
    build: .
    develop:
      watch:
        - path: ./src
          action: sync                  # copy changes into the running container
          target: /app/src
          ignore: [node_modules/, "**/*.test.ts"]
        - path: ./config
          action: sync+restart          # copy, then restart the container
          target: /app/config
        - path: ./package.json
          action: rebuild               # rebuild the image and recreate the service
        - path: ./scripts
          action: sync+exec
          target: /app/scripts
          exec:
            command: /app/scripts/reload.sh
```

```bash
docker compose up --watch        # start and watch
docker compose watch             # watch only
```

- Actions: `sync`, `rebuild`, `restart`, `sync+restart`, `sync+exec`. `path` is relative to the project directory.
- `ignore` and `include` use `.dockerignore` syntax; quote patterns that start with `*` because YAML treats a bare `*` as an alias. Patterns in the build context's `.dockerignore` apply implicitly.
- `initial_sync: true` checks that container files match the watched path when a watch session starts (for `sync+x` actions).
- Watch needs the service to have a `build` section for `rebuild` and a writable target for sync; with `read_only: true` use a dev override that turns it off.

## 8. Hardened service template

```yaml
services:
  api:
    image: registry.example.com/shop/api@sha256:<digest>
    user: "10001:10001"
    read_only: true
    tmpfs:
      - /tmp
    cap_drop: [ALL]
    security_opt:
      - no-new-privileges:true
    init: true
    pids_limit: 256
    mem_limit: 512m
    cpus: 1.0
    restart: unless-stopped
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "/app", "healthcheck"]
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 10s
    logging:
      driver: local
      options: {max-size: "10m", max-file: "3"}
```

- Never add `privileged: true`, `network_mode: host`, `pid: host` or a `/var/run/docker.sock` bind mount without a documented reason. Socket access equals root on the host.
- `pull_policy: always` (or `missing`, `never`, `build`) controls image pulls; use immutable tags or digests rather than relying on `always`.
- Lifecycle hooks exist: `post_start` and `pre_stop` run commands around the container's life; `privileged: true` inside a hook is as dangerous as on the service.

## 9. Environment variables and interpolation

- Compose reads `.env` from the project directory for interpolation (`${VAR}`), not automatically for the container; pass values with `environment:` or `env_file:`.
- Interpolation forms: `${VAR:-default}`, `${VAR-default}`, `${VAR:?error message}` (fail if unset or empty), `${VAR:+replacement}`. Use `:?` for mandatory settings so a missing value fails at `up` rather than at run time.
- Precedence (highest first): `docker compose run -e`; `environment` or `env_file` values interpolated from the shell or a `.env` file (`--env-file`); plain `environment` entries; `env_file` files; the image's `ENV`. Check `docker compose config` to see what a service receives.
- Literal `$` in values is written `$$`.

## 10. CLI workflows

```bash
docker compose up -d --build --wait            # build, start, wait for health
docker compose ps --format json                # machine-readable status
docker compose logs -f --since 10m api
docker compose exec api sh                     # only if the image has a shell
docker compose run --rm tests                  # one-off container, removed after
docker compose pull && docker compose up -d    # update to newer images
docker compose down                            # remove containers and networks
docker compose down -v                         # also remove named volumes (data loss)
docker compose config --quiet                  # validate in CI
```

CI test run with exit code propagation:

```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests
status=$?
docker compose --profile test down -v
exit $status
```

## 11. Compose in production

Single-host Compose works for small deployments with these constraints:

- Deploy images by digest or immutable tag from a registry; do not build on the server.
- Keep one `compose.yaml` plus an explicit production overlay; do not mix dev bind mounts and `watch` into production files.
- Persist data in named volumes and back them up outside the host; `down -v` deletes them.
- Put a TLS-terminating reverse proxy (nginx, Caddy, Traefik) on the only published ports; keep databases on an `internal` network.
- `deploy.resources.limits` is honored by `docker compose`; `mem_limit`/`cpus` are the shorthand equivalents. Swarm-only `deploy` keys (replicas scheduling, placement, update_config) do not turn Compose into a scheduler.
- There is no automatic rescheduling if the host fails; plan for that or use an orchestrator (kubernetes-expert).
