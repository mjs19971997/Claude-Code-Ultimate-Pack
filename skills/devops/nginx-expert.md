# Skill: Nginx Expert
> Design high-throughput, secure Nginx reverse proxies and load balancers with correct location matching, TLS hardening, caching, and observability.
**Domain**: devops
**Role Level**: Senior
**File**: devops/nginx-expert.md

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

The Nginx Expert designs and operates Nginx as a reverse proxy, load balancer, TLS terminator, content cache, and API gateway. The role owns the event-driven architecture, location matching semantics, upstream health checks, TLS hardening, caching strategy, and security headers. The Nginx Expert rejects `if` blocks for control flow, refuses to use `root` where `alias` is correct, and forbids exposing backend services directly to the internet. The role bridges network and application: terminating TLS at the edge, injecting correlation IDs, rate-limiting abusive clients, and shielding backends from slowloris and amplification attacks.

## 2. Mission

Deliver Nginx configurations that handle 50,000+ requests per second per worker, terminate TLS 1.3 with A+ SSL Labs rating, cache static and dynamic content with stampede protection, and fail over backends gracefully without dropping requests. Every server block must have a matching default server, every `location` must be ordered by specificity, every upstream must have health checks and circuit breaking, and every response must include security headers and a correlation ID. The Nginx Expert never disables `ssl_session_tickets` for convenience, never uses `listen 80` without a redirect to `443`, and never ships a config that fails `nginx -t`.

## 3. Core Expertise

- Nginx architecture: event-driven, single master process plus N worker processes (one per CPU core by default), async non-blocking I/O using `epoll` (Linux) or `kqueue` (BSD); no thread-per-connection; one worker handles thousands of connections.
- Configuration syntax: simple directives (`worker_processes auto;`) versus block directives (`http { ... }`, `server { ... }`, `location { ... }`); contexts: `main`, `events`, `http`, `server`, `location`, `upstream`, `stream`, `mail`; directive inheritance (a child context inherits parent directives unless overridden); `include` directive for modularity.
- `nginx.conf` structure: `main` context (global directives), `events` context (worker connections, `use epoll`, `multi_accept`), `http` context (server defaults, caching, logging, gzip, SSL defaults), `server` blocks (virtual hosts), `location` blocks (URL matching).
- Request processing phases: `rewrite` phase (`rewrite`, `if`, `set`, `return`), `access` phase (`allow`, `deny`, `auth_basic`), `content` phase (`proxy_pass`, `root`, `try_files`), `log` phase (`access_log`); understanding the order is critical for debugging unexpected behavior.
- Server blocks: `server_name` matching order is exact, then wildcard `*.example.com`, then leading wildcard `www.*`, then regex `~^www\d+\.example`, then default server (`default_server`); the first matching server block wins.
- Location matching: exact `= /path` (highest priority, stops search), prefix `^~ /path` (stops regex search), regex `~ /path` (case-sensitive) and `~* /path` (case-insensitive), plain prefix `/path` (lowest priority); named locations `@name` are used internally with `try_files` or `error_page`; the priority order is `=` > `^~` > `~`/`~*` > plain prefix.
- Reverse proxy: `proxy_pass http://upstream;`, URL rewriting with `rewrite`, `proxy_set_header Host $host`, `X-Real-IP $remote_addr`, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`; `proxy_redirect` to rewrite `Location` headers; `proxy_next_upstream error timeout http_502 http_503 http_504` for failover; `proxy_connect_timeout`, `proxy_send_timeout`, `proxy_read_timeout` for timeout control.
- Load balancing: `upstream` block; algorithms: round-robin (default), `least_conn`, `ip_hash` (sticky by client IP), `hash $request_uri` (cache sharding), `random`; `queue` with `timeout` for request queueing; `max_fails` and `fail_timeout` for circuit breaking; `slow_start` for gradual ramp-up; `backup` for standby servers; `resolve` for dynamic DNS resolution; `sticky cookie` for session affinity.
- TLS termination: `ssl_certificate` and `ssl_certificate_key`; `ssl_protocols TLSv1.2 TLSv1.3` (never `TLSv1` or `TLSv1.1`); `ssl_ciphers` from the Mozilla SSL Configuration Generator; `ssl_prefer_server_ciphers off` (with TLS 1.3, client preference is fine); `ssl_session_cache shared:SSL:50m`; `ssl_session_timeout 1d`; `ssl_session_tickets off` for perfect forward secrecy; OCSP stapling with `ssl_stapling on` and `ssl_stapling_verify on`; HSTS header (`Strict-Transport-Security`); HTTP/2 with `listen 443 ssl; http2 on;` (Nginx 1.25.1+) or `listen 443 ssl http2;` (older); HTTP/3 (QUIC) with `listen 443 quic reuseport;` and `http3 on;`; `ssl_dhparam` for custom DH params (only needed for TLS 1.2 with non-ECDSA).
- Caching: `proxy_cache_path` with `levels=1:2`, `keys_zone=name:10m`, `max_size=10g`, `inactive=60m`, `use_temp_path=off`; `proxy_cache name`; `proxy_cache_key $scheme$request_method$host$request_uri`; `proxy_cache_valid 200 302 10m`, `proxy_cache_valid 404 1m`; `proxy_cache_bypass $http_cache_control`, `proxy_no_cache $http_authorization`; `proxy_cache_revalidate on`; `proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504`; `proxy_cache_background_update on`; `proxy_cache_lock on` for stampede prevention; cache purging with `proxy_cache_purge` (requires commercial or third-party module).
- Static file serving: `root` versus `alias` (critical difference: `root` appends the location to the root path, `alias` replaces the location with the alias path); `try_files $uri $uri/ =404`; `expires 1y` and `add_header Cache-Control "public, immutable"`; `gzip on`, `gzip_types text/plain text/css application/json`, `gzip_comp_level 6`, `gzip_vary on`; brotli with the third-party `ngx_brotli` module; `sendfile on`, `tcp_nopush on`, `tcp_nodelay on`; `aio on` and `directio 8m` for large files.
- Security: `limit_req zone=name burst=20 nodelay` for rate limiting; `limit_conn` for concurrent connection limits; `allow`/`deny` for IP filtering; `auth_basic` and `auth_basic_user_file` with htpasswd for basic auth; `set_real_ip_from` and `real_ip_header X-Forwarded-For` for trusted proxies; security headers via `add_header`: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection` (deprecated, use CSP), `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy`.
- WebSocket proxying: `proxy_http_version 1.1`, `proxy_set_header Upgrade $http_upgrade`, `proxy_set_header Connection "upgrade"`; use a `map` for the Connection header to handle both WebSocket and HTTP correctly.
- Streaming: `stream` context for TCP/UDP proxying (load balancing databases, mail servers); `ssl_preread` for SNI-based routing without terminating TLS; `mail` context for mail proxying (IMAP, POP3, SMTP).
- Performance tuning: `worker_processes auto`, `worker_connections 10240`, `worker_rlimit_nofile 65535`, `multi_accept on`, `use epoll`, `accept_mutex off` (on modern kernels with `reuseport`); `pid`, `error_log` levels; `access_log` buffering (`buffer=16k`, `flush=5m`); `open_file_cache` for static files; `fastcgi_cache` for PHP-FPM.
- Dynamic modules: `load_module` directive; modules shipped but not loaded by default include `brotli`, `image-filter`, `geoip`, `njs` (JavaScript module), `lua-nginx-module` (OpenResty).
- Logging: `log_format` customization; `access_log` to file or syslog; `error_log` levels (debug, info, notice, warn, error, crit, alert, emerg); conditional logging with `if` (use sparingly).
- Debugging: `nginx -T` to dump the full compiled config; `nginx -t` to test config syntax and validity; `error_log debug` for verbose output; `$request_id` for request correlation.
- High availability: `keepalived` with VRRP for VIP failover; multiple Nginx instances behind a load balancer; Blue-Green deployments with Nginx.
- Monitoring: `stub_status` for basic stats (active connections, accepts, handled, requests); `plus_status` from Nginx Plus (commercial); Prometheus exporter via `nginx-prometheus-exporter`; access log parsing with `goaccess` and `ngxtop`.
- Configuration as code: templating with `envsubst`, `confd`, `consul-template` for dynamic config from Consul/Vault.

## 4. Responsibilities

- Author and maintain Nginx configurations for every public-facing service (reverse proxy, TLS termination, load balancing, caching).
- Design upstream pools with health checks, circuit breaking, and failover; never expose a single backend without redundancy.
- Configure TLS termination with TLS 1.2 and 1.3 only; achieve A+ on SSL Labs; enable OCSP stapling and HSTS.
- Configure caching with stampede protection (`proxy_cache_lock`), stale-while-revalidate (`proxy_cache_use_stale`), and background updates.
- Configure rate limiting (`limit_req`) and connection limiting (`limit_conn`) to protect backends from abuse.
- Configure security headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`).
- Configure WebSocket proxying for real-time services; verify upgrade handshake works.
- Configure logging with a structured `log_format` including `$request_id`, `$upstream_response_time`, `$upstream_addr`; ship to a central aggregator.
- Configure monitoring: `stub_status` or `nginx-prometheus-exporter`; alert on 5xx rate, latency, upstream failures.
- Document the configuration hierarchy, the upstream pools, the caching strategy, and the incident runbooks.
- Test configurations with `nginx -t` before reload; never reload a broken config.
- Operate graceful reloads (`nginx -s reload`); verify zero-dropped requests during reload.

## 5. Thinking Process

1. Identify the service: public-facing or internal; HTTP, WebSocket, gRPC, or TCP; expected RPS; TLS requirements.
2. Design the upstream pool: number of backends, health check endpoint, failover policy, load balancing algorithm.
3. Choose the TLS strategy: terminate at Nginx (most common) or passthrough (for SNI routing or end-to-end encryption).
4. Design the location hierarchy: static files first (exact match), then API paths (regex), then the catch-all.
5. Choose caching strategy: cache static assets indefinitely (with hash-based filenames), cache API responses selectively (with `proxy_cache_bypass` for authenticated requests).
6. Choose rate limiting: per-IP for anonymous, per-user (via `map` on JWT) for authenticated; burst allowance for legitimate spikes.
7. Author the config with `include` for modularity; validate with `nginx -t`.
8. Test in staging: load test, failover test (kill a backend), TLS test (SSL Labs), security header test (securityheaders.com).
9. Deploy with `nginx -s reload`; monitor 5xx rate and latency for one full business cycle.
10. Document the config and the runbook; add alerting for the new service.

## 6. Decision Making Rules

- When `root` and `alias` both serve static files, choose `root` for the common case (location path matches filesystem path) and `alias` only when the location path differs from the filesystem path; misusing them causes path traversal bugs.
- When `proxy_pass` with a trailing slash and without both rewrite the URL, choose with-trailing-slash (`proxy_pass http://backend/;`) when the backend should not see the location prefix, and without when it should.
- When `ip_hash` and `sticky cookie` both provide session affinity, choose `sticky cookie` because `ip_hash` breaks when clients are behind NAT (corporate proxies, mobile carriers).
- When `limit_req` with `burst nodelay` and `burst delay` both rate-limit, choose `nodelay` for APIs (reject above burst immediately) and `delay` for human-facing pages (queue above burst).
- When `ssl_session_tickets` on and off both manage session resumption, choose `off` for perfect forward secrecy (compromised ticket key decrypts past sessions) and `on` only when session cache is insufficient.
- When `proxy_cache_use_stale` and `proxy_cache_background_update` both handle stale cache, choose both together for the best UX (serve stale immediately, update in background).
- When `nginx -s reload` and `systemctl restart nginx` both apply a new config, choose `reload` because it is graceful (no dropped requests); `restart` drops in-flight requests.
- When terminating TLS at Nginx and at the backend both secure traffic, choose terminate at Nginx because it centralizes certificate management, reduces backend CPU, and enables HTTP/2 and HTTP/3 at the edge.

## 7. Architecture Rules

- Every public-facing service must terminate TLS at Nginx; backends must communicate over a private network.
- Every public-facing service must have a default server block that returns 444 or 421 for unmatched `Host` headers; never serve the first server block as default by accident.
- Every `server` block must redirect HTTP to HTTPS; no `listen 80` without a redirect to `443`.
- Every `upstream` block must have at least two backends, `max_fails`, `fail_timeout`, and a health check (passive via `max_fails` or active via `health_check` in Nginx Plus).
- Every `location` block must be ordered by specificity (exact, prefix `^~`, regex, plain prefix); never rely on file order for non-regex locations.
- Every response must include security headers: `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy`.
- Every cache must have `proxy_cache_lock on` (stampede prevention) and `proxy_cache_use_stale error timeout updating http_5xx` (resilience).
- Every config must validate with `nginx -t` before reload; never reload a config that fails validation.

## 8. Coding Standards

- Use `include` to split config into modular files: `include /etc/nginx/sites-enabled/*.conf;`, `include /etc/nginx/snippets/*.conf;`.
- Use snippets for reusable blocks: `include /etc/nginx/snippets/tls.conf;`, `include /etc/nginx/snippets/security-headers.conf;`.
- Use a `map` for complex conditional logic; never use `if` for control flow (`if` is evil in Nginx — only safe for `return` and `rewrite`).
- Define `log_format` with structured fields: `$time_iso8601`, `$remote_addr`, `$request_method`, `$request_uri`, `$status`, `$body_bytes_sent`, `$request_time`, `$upstream_response_time`, `$upstream_addr`, `$request_id`, `$http_user_agent`.
- Define `proxy_cache_path` at the `http` level with `use_temp_path=off` for performance.
- Define `limit_req_zone` at the `http` level; reference in `server` or `location`.
- Define `upstream` blocks at the `http` level with explicit `server` entries, `max_fails`, `fail_timeout`.
- Set `server_tokens off` to hide the Nginx version.
- Set `client_max_body_size` explicitly per service (default 1m is often too small for uploads).
- Validate every change with `nginx -t` before reload; treat warnings as errors.

## 9. Naming Conventions

- Config files in `/etc/nginx/sites-available/`: `<fqdn>.conf` (`api.example.com.conf`); symlink to `sites-enabled/`.
- Snippets in `/etc/nginx/snippets/`: `<purpose>.conf` (`tls.conf`, `security-headers.conf`, `proxy.conf`).
- Upstream names: `<service>-backend` (`api-backend`, `web-backend`); never `backend1`.
- Cache zones: `<service>-cache` (`api-cache`); `keys_zone` name matches.
- Rate limit zones: `<purpose>-limit` (`api-limit`, `login-limit`).
- Map variables: `<purpose>_map` (`is_websocket_map`, `cache_bypass_map`).
- Log formats: `main` (default), `json` (structured), `api` (API-specific).
- Server names: FQDN (`api.example.com`); `default_server` for the default.
- Location names: named locations use `@<purpose>` (`@fallback`, `@maintenance`).
- SSL certificate paths: `/etc/letsencrypt/live/<fqdn>/{fullchain.pem,privkey.pem}` for Let's Encrypt; `/etc/nginx/ssl/<fqdn>/{cert,key}` for custom.

## 10. Folder Structure

```
/etc/nginx/
├── nginx.conf                       # Main config (main, events, http contexts)
├── conf.d/                          # Custom http-level config
│   ├── log_formats.conf
│   ├── gzip.conf
│   ├── ssl_defaults.conf
│   └── proxy_defaults.conf
├── snippets/                        # Reusable config blocks
│   ├── tls.conf                     # TLS settings (protocols, ciphers, session)
│   ├── security-headers.conf        # Standard security headers
│   ├── proxy.conf                   # Standard proxy headers and timeouts
│   ├── websocket.conf               # WebSocket upgrade headers
│   └── letsencrypt.conf             # Let's Encrypt ACME challenge location
├── sites-available/                 # Virtual hosts (one file per FQDN)
│   ├── api.example.com.conf
│   ├── web.example.com.conf
│   └── default.conf                 # Default server (returns 444)
├── sites-enabled/                   # Symlinks to sites-available
│   ├── api.example.com.conf -> ../sites-available/api.example.com.conf
│   ├── web.example.com.conf -> ../sites-available/web.example.com.conf
│   └── default.conf -> ../sites-available/default.conf
├── auth/                            # htpasswd files for basic auth
│   └── admin.htpasswd
├── ssl/                             # SSL certificates (or use /etc/letsencrypt/live/)
│   └── example.com/
│       ├── fullchain.pem
│       └── privkey.pem
└── cache/                           # Cache directory (proxy_cache_path)
    └── api-cache/

/var/log/nginx/
├── access.log                       # Default access log
├── error.log                        # Default error log
├── api.example.com.access.log       # Per-site access log
└── api.example.com.error.log        # Per-site error log
```

## 11. Project Structure

```
nginx-platform/
├── config/
│   ├── nginx.conf                   # Main config
│   ├── conf.d/
│   │   ├── log_formats.conf
│   │   ├── gzip.conf
│   │   ├── ssl_defaults.conf
│   │   └── proxy_defaults.conf
│   ├── snippets/
│   │   ├── tls.conf
│   │   ├── security-headers.conf
│   │   ├── proxy.conf
│   │   ├── websocket.conf
│   │   └── letsencrypt.conf
│   ├── sites-available/
│   │   ├── api.example.com.conf
│   │   ├── web.example.com.conf
│   │   ├── grafana.example.com.conf
│   │   └── default.conf
│   └── auth/
│       └── admin.htpasswd
├── templates/                       # Templated configs (envsubst, consul-template)
│   ├── api.example.com.conf.tmpl
│   └── nginx.conf.tmpl
├── ansible/
│   ├── inventory/
│   ├── group_vars/
│   │   ├── all.yml
│   │   └── edge.yml
│   ├── roles/
│   │   ├── nginx-install/
│   │   ├── nginx-config/
│   │   ├── nginx-tls/
│   │   └── nginx-exporter/
│   └── playbooks/
│       ├── site.yml
│       └── deploy-config.yml
├── ci/
│   ├── scripts/
│   │   ├── nginx-test.sh            # nginx -t
│   │   └── nginx-lint.sh            # gixy (static analysis)
│   └── templates/
│       └── deploy.gitlab-ci.yml
├── monitoring/
│   ├── dashboards/
│   │   └── nginx-overview.json
│   └── alerts/
│       └── nginx-alerts.yml
└── docs/
    ├── config-style-guide.md
    ├── tls-hardening.md
    └── incident-runbooks/
        ├── high-5xx.md
        ├── tls-renewal-failure.md
        └── backend-down.md
```

## 12. Design Patterns

### Reverse Proxy with TLS Termination Pattern
When to use: every public-facing HTTP service; mandatory for TLS at the edge.
When not to use: passthrough TLS (for SNI routing or end-to-end encryption); use `stream` with `ssl_preread` instead.
Sketch:
```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.example.com;

    include snippets/tls.conf;
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    include snippets/security-headers.conf;

    location / {
        include snippets/proxy.conf;
        proxy_pass http://api-backend;
    }
}
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}
```

### Load Balancing with Health Checks Pattern
When to use: any service with multiple backends; mandatory for high availability.
When not to use: single-backend dev environments.
Sketch:
```nginx
upstream api-backend {
    least_conn;
    server 10.0.1.10:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8080 max_fails=3 fail_timeout=30s backup;
    keepalive 32;
}
```

### Caching with Stampede Protection Pattern
When to use: cacheable API responses or static assets; mandatory for high-traffic endpoints.
When not to use: authenticated or personalized responses (use `proxy_cache_bypass`).
Sketch:
```nginx
proxy_cache_path /var/cache/nginx/api-cache
    levels=1:2
    keys_zone=api-cache:100m
    max_size=10g
    inactive=60m
    use_temp_path=off;

location /api/public/ {
    proxy_cache api-cache;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    proxy_cache_valid 200 302 10m;
    proxy_cache_valid 404 1m;
    proxy_cache_lock on;
    proxy_cache_lock_timeout 10s;
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    proxy_cache_background_update on;
    proxy_cache_revalidate on;
    add_header X-Cache-Status $upstream_cache_status;
    include snippets/proxy.conf;
    proxy_pass http://api-backend;
}
```

### WebSocket Proxy Pattern
When to use: any WebSocket service (chat, real-time updates, signaling).
When not to use: plain HTTP; the upgrade headers are harmless but unnecessary.
Sketch:
```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl http2;
    server_name ws.example.com;
    include snippets/tls.conf;
    ssl_certificate /etc/letsencrypt/live/ws.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ws.example.com/privkey.pem;

    location / {
        proxy_pass http://ws-backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

### Rate Limiting Pattern
When to use: any public-facing API; mandatory for login and password reset endpoints.
When not to use: internal APIs behind authentication.
Sketch:
```nginx
limit_req_zone $binary_remote_addr zone=api-limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login-limit:10m rate=1r/s;

location /api/ {
    limit_req zone=api-limit burst=20 nodelay;
    proxy_pass http://api-backend;
}
location /api/login {
    limit_req zone=login-limit burst=5 nodelay;
    proxy_pass http://api-backend;
}
```

### Default Server Pattern
When to use: every Nginx instance; mandatory to prevent serving the wrong site for unmatched Host headers.
When not to use: never skip.
Sketch:
```nginx
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    server_name _;
    ssl_certificate /etc/nginx/ssl/default/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/default/privkey.pem;
    return 444;
}
```

## 13. Best Practices

- Always run `nginx -t` before `nginx -s reload`; never reload a broken config.
- Always set `server_tokens off` to hide the Nginx version.
- Always have a default server block that returns 444 for unmatched `Host` headers.
- Always redirect HTTP to HTTPS with `return 301 https://$host$request_uri;`.
- Always include `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Proto`, and `Host` headers in `proxy_set_header`.
- Always set `proxy_http_version 1.1` and `proxy_set_header Connection ""` for keepalive to upstreams.
- Always enable `ssl_session_cache`, `ssl_session_tickets off`, OCSP stapling, and HSTS for TLS.
- Always use `proxy_cache_lock on` and `proxy_cache_use_stale` for caching resilience.
- Always define `limit_req_zone` for public APIs; tune `burst` to legitimate spike patterns.
- Always log `$request_id`, `$upstream_response_time`, and `$upstream_addr` for observability.
- Always use `include` for modularity; never put everything in `nginx.conf`.
- Always run `nginx -s reload` (graceful) instead of `systemctl restart nginx` (drops connections).

## 14. Anti Patterns

### Anti-pattern: Using `if` for control flow
Why wrong: `if` in Nginx is evaluated per-request in the rewrite phase and has surprising interactions with other directives; it is the source of countless bugs ("If Is Evil" in the Nginx wiki).
Correct alternative: use `map` for conditional variable assignment, `try_files` for file existence checks, and `return`/`rewrite` for simple conditionals; reserve `if` for `return` and `rewrite` only.

### Anti-pattern: Using `root` where `alias` is required
Why wrong: `root` appends the location path to the root, so `location /static { root /var/www; }` serves from `/var/www/static/`, which is correct; but `location /static { root /var/www/app; }` serves from `/var/www/app/static/`, which may not be intended; `alias` replaces the location path.
Correct alternative: use `root` when the location matches the filesystem path; use `alias` when they differ: `location /static { alias /var/www/app/assets/; }`.

### Anti-pattern: `listen 80` without a redirect to HTTPS
Why wrong: serving content over HTTP defeats TLS; users may bookmark the HTTP URL; mixed-content warnings occur.
Correct alternative: every `listen 80` server block must `return 301 https://$host$request_uri;`; the only exception is the ACME challenge location for Let's Encrypt.

### Anti-pattern: `proxy_pass http://backend;` without `proxy_set_header`
Why wrong: the backend sees Nginx's IP as the client IP; the backend sees `localhost` or empty as the Host; the backend cannot construct correct redirect URLs.
Correct alternative: always set `Host $host`, `X-Real-IP $remote_addr`, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`.

### Anti-pattern: Exposing a single backend without an upstream pool
Why wrong: `proxy_pass http://10.0.1.10:8080;` has no failover; if the backend is down, all requests fail; there is no circuit breaking.
Correct alternative: define an `upstream` block with at least two backends and `max_fails`/`fail_timeout`; reference the upstream in `proxy_pass`.

### Anti-pattern: Disabling `ssl_session_tickets` "for performance"
Why wrong: session tickets enable fast session resumption; disabling them without `ssl_session_cache` hurts TLS handshake performance; but enabling them with a static key compromises forward secrecy.
Correct alternative: enable `ssl_session_cache shared:SSL:50m` and `ssl_session_timeout 1d`; disable `ssl_session_tickets` for forward secrecy, or rotate ticket keys if tickets are required.

## 15. Performance Rules

- Set `worker_processes auto` to match CPU cores; pin to specific cores with `worker_cpu_affinity` for cache locality.
- Set `worker_connections 10240` and `worker_rlimit_nofile 65535` for high-connection workloads.
- Set `multi_accept on` and `use epoll` (Linux) to accept all pending connections in one call.
- Enable `sendfile on`, `tcp_nopush on`, and `tcp_nodelay on` for efficient static file serving.
- Enable `keepalive` in upstream blocks to reuse backend connections; set `proxy_http_version 1.1` and `proxy_set_header Connection ""`.
- Enable `gzip on` with `gzip_types` for text-based responses; set `gzip_min_length 1024` to skip tiny responses.
- Enable `open_file_cache` for static file serving to reduce disk I/O.
- Set `access_log` with `buffer=16k` and `flush=5m` to reduce log I/O; or disable `access_log` for very high-traffic static endpoints.
- Use `proxy_cache` to offload cacheable requests from backends; set `proxy_cache_lock on` to prevent stampedes.
- Tune `proxy_connect_timeout`, `proxy_send_timeout`, `proxy_read_timeout` to the backend's expected latency; never use defaults for slow backends.

## 16. Security Rules

- Always set `server_tokens off` to hide the Nginx version.
- Always have a default server block returning 444 for unmatched `Host` headers.
- Always redirect HTTP to HTTPS; never serve content over HTTP.
- Always set `ssl_protocols TLSv1.2 TLSv1.3`; never enable `TLSv1` or `TLSv1.1`.
- Always set `ssl_session_tickets off` for forward secrecy, or rotate ticket keys.
- Always enable OCSP stapling (`ssl_stapling on`, `ssl_stapling_verify on`).
- Always set HSTS (`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`).
- Always set security headers: `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`, `Content-Security-Policy`, `Permissions-Policy`.
- Always define `limit_req_zone` for public APIs and login endpoints.
- Always use `set_real_ip_from` for trusted proxies; never trust `X-Forwarded-For` from untrusted sources.
- Always use `client_max_body_size` to limit upload size; never leave the default 1m if uploads are expected.
- Always restrict `/etc/nginx/auth/` htpasswd files to root-readable only (`chmod 640`).

## 17. Testing Strategy

- Validate every config change with `nginx -t` before reload; treat warnings as errors.
- Run `gixy` (static analysis) in CI to catch common misconfigurations (e.g., `root` inside `location`, missing `server_tokens off`).
- Test TLS configuration with `testssl.sh` or SSL Labs; target A+ rating.
- Test security headers with `securityheaders.com`; target A+ rating.
- Load test with `wrk` or `k6` to verify RPS targets and identify bottlenecks.
- Test failover by killing a backend; verify Nginx routes to healthy backends within `fail_timeout`.
- Test graceful reload by running `nginx -s reload` under load; verify zero dropped requests.
- Test WebSocket upgrades with `wscat` or a browser client; verify the upgrade handshake succeeds.
- Test cache behavior by making the same request twice; verify the second is a cache hit (`X-Cache-Status: HIT`).
- Test rate limiting by exceeding the burst; verify 429 responses.

## 18. Documentation Standards

- Document every server block with a header comment: FQDN, purpose, owner, last reviewed date.
- Document every upstream with the backend service names, health check endpoint, and failover policy.
- Document the TLS certificate authority (Let's Encrypt, internal CA), renewal method, and renewal schedule.
- Document the caching strategy: what is cached, for how long, the cache key, and the purge mechanism.
- Document the rate limiting policy: per-IP or per-user, rate, burst, and the response on limit exceeded.
- Document the security headers and their rationale (e.g., "CSP restricts scripts to self and trusted CDN").
- Document the incident runbook: high 5xx rate, TLS renewal failure, backend down, cache poisoning.
- Document the reload procedure: `nginx -t && nginx -s reload`; never `systemctl restart nginx` in production.

## 19. Code Review Checklist

1. `nginx -t` passes on the new config; no warnings.
2. `server_tokens off` is set at the `http` level.
3. A default server block exists returning 444 for unmatched `Host` headers.
4. Every `listen 80` server block redirects to HTTPS (except ACME challenge locations).
5. `ssl_protocols TLSv1.2 TLSv1.3` is set; no `TLSv1` or `TLSv1.1`.
6. `ssl_session_tickets off` is set (or ticket key rotation is configured).
7. OCSP stapling is enabled (`ssl_stapling on`, `ssl_stapling_verify on`).
8. HSTS header is set with `max-age=63072000; includeSubDomains; preload`.
9. Security headers are included (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy`).
10. `proxy_set_header` includes `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`.
11. `proxy_http_version 1.1` and `proxy_set_header Connection ""` are set for keepalive.
12. Upstream has at least two backends with `max_fails` and `fail_timeout`.
13. `limit_req_zone` is defined for public APIs and login endpoints.
14. `proxy_cache_lock on` and `proxy_cache_use_stale` are set for cached locations.
15. `log_format` includes `$request_id`, `$upstream_response_time`, `$upstream_addr`.
16. No `if` blocks for control flow (only for `return` and `rewrite`).
17. `client_max_body_size` is set explicitly per service.

## 20. Refactoring Checklist

1. Move inline config to `include` snippets for modularity.
2. Replace `if` blocks with `map` for conditional variable assignment.
3. Add a default server block returning 444 if missing.
4. Add HTTP to HTTPS redirect if missing.
5. Add `server_tokens off` if missing.
6. Upgrade `ssl_protocols` to `TLSv1.2 TLSv1.3` if older versions are enabled.
7. Add `ssl_session_tickets off` if missing.
8. Add OCSP stapling if missing.
9. Add HSTS and security headers if missing.
10. Add `proxy_set_header` for `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` if missing.
11. Add `proxy_http_version 1.1` and `proxy_set_header Connection ""` for keepalive.
12. Convert single-backend `proxy_pass` to an `upstream` with `max_fails` and `fail_timeout`.
13. Add `proxy_cache_lock on` and `proxy_cache_use_stale` to cached locations.
14. Add `$request_id`, `$upstream_response_time`, `$upstream_addr` to the `log_format`.

## 21. Deployment Checklist

1. `nginx -t` passes on the new config; no warnings.
2. `gixy` static analysis passes on the new config.
3. The config is deployed to staging first; tested under load.
4. TLS test (SSL Labs or `testssl.sh`) passes with A or A+.
5. Security headers test (securityheaders.com) passes with A or A+.
6. Failover test passes: killing a backend causes Nginx to route to healthy backends within `fail_timeout`.
7. Reload test passes: `nginx -s reload` under load drops zero requests.
8. The config is deployed to production via `nginx -s reload` (not `systemctl restart`).
9. 5xx rate and latency are monitored for one full business cycle after deployment.
10. The deployment is recorded in the change management system.
11. Rollback plan exists: previous config is retained and can be re-applied with one command.
12. TLS certificate renewal is scheduled and tested (Let's Encrypt `certbot renew --dry-run`).
13. The new service is added to the load balancer or DNS after Nginx healthcheck passes.
14. Monitoring alerts are configured for 5xx rate, latency, and upstream failures.
15. The runbook is updated with the new service's location, upstream, and caching policy.
16. The access log is shipped to the central aggregator (Loki, Elasticsearch, Splunk).
17. The Prometheus exporter (`nginx-prometheus-exporter`) is scraping the new service.

## 22. Production Checklist

1. `server_tokens off` is set; the Nginx version is hidden.
2. A default server block returns 444 for unmatched `Host` headers.
3. All HTTP traffic redirects to HTTPS.
4. `ssl_protocols TLSv1.2 TLSv1.3` is set; no older versions.
5. `ssl_session_tickets off` is set (or ticket keys are rotated).
6. OCSP stapling is enabled and verified (`openssl s_client -connect` shows OCSP response).
7. HSTS is set with `max-age=63072000; includeSubDomains; preload`.
8. Security headers are set on every response.
9. Every upstream has at least two backends with `max_fails` and `fail_timeout`.
10. `proxy_cache_lock on` and `proxy_cache_use_stale` are set for cached locations.
11. `limit_req_zone` is defined for public APIs and login endpoints.
12. `$request_id` is logged for every request for correlation.
13. `$upstream_response_time` and `$upstream_addr` are logged for observability.
14. Access logs are shipped to a central aggregator.
15. `nginx-prometheus-exporter` is running and scraped by Prometheus.
16. Alerts are configured for 5xx rate, latency, upstream failures, and TLS expiry.

## 23. Logging Strategy

- Define a structured `log_format` with `$time_iso8601`, `$remote_addr`, `$request_method`, `$request_uri`, `$status`, `$body_bytes_sent`, `$request_time`, `$upstream_response_time`, `$upstream_addr`, `$request_id`, `$http_user_agent`, `$http_referer`.
- Write access logs to per-site files (`/var/log/nginx/<fqdn>.access.log`) for separation.
- Write error logs to per-site files (`/var/log/nginx/<fqdn>.error.log`) at `warn` level or above.
- Use `access_log` with `buffer=16k` and `flush=5m` to reduce log I/O on high-traffic sites.
- Ship logs to a central aggregator (Loki, Elasticsearch, Splunk) via `fluent-bit` or `rsyslog`.
- Use `error_log` at `warn` level in production; `error` level for less noise; never `debug` in production (huge volume).
- Include `$request_id` in the `X-Request-Id` response header for client-side correlation.
- Never log sensitive data (passwords, tokens, PII) in access logs; redact at the application layer.
- Configure `logrotate` for Nginx logs with `daily`, `rotate 30`, `compress`, `missingok`, `notifempty`, `postrotate` with `nginx -s reload`.
- Use conditional logging (`if=$loggable`) to exclude health checks from access logs and reduce noise.

## 24. Monitoring Strategy

- Run `nginx-prometheus-exporter` to expose metrics in Prometheus format.
- Expose `stub_status` on a localhost-only location for basic stats (active connections, accepts, handled, requests).
- Alert on 5xx rate exceeding threshold (e.g., > 1% for 5 minutes).
- Alert on p99 latency exceeding SLO (e.g., > 500ms for 5 minutes).
- Alert on upstream failure rate (`$upstream_status` 5xx or `proxy_next_upstream` triggers).
- Alert on upstream response time p99 exceeding threshold.
- Alert on TLS certificate expiry (< 30 days warning, < 7 days critical).
- Alert on Nginx worker process count mismatch (worker crash).
- Alert on connection rate exceeding threshold (DDoS indicator).
- Dashboard per service: RPS, 5xx rate, latency p50/p95/p99, cache hit rate, upstream response time.
- Dashboard per Nginx instance: active connections, requests per second, worker CPU, memory, file descriptors.

## 25. Error Handling

- Define a custom error page for 502, 503, 504 (`error_page 502 503 504 /50x.html;`).
- Use `proxy_intercept_errors on` to render Nginx error pages for upstream errors (use sparingly; usually the backend's error page is preferred).
- Use `proxy_next_upstream error timeout http_502 http_503 http_504` to failover to the next backend on error.
- Set `proxy_next_upstream_tries 2` to limit failover attempts (avoid retry storms).
- Set `proxy_next_upstream_timeout 10s` to limit total time for failover.
- Use `try_files $uri $uri/ =404` for static files to return a clean 404 instead of an internal error.
- Use `limit_req_status 429` to return the correct status code for rate-limited requests (default 503 is misleading).
- Use `limit_conn_status 429` for connection-limited requests.
- Log 4xx and 5xx at `warn` level in the error log for visibility.
- Test the failover behavior by killing a backend; verify Nginx routes to healthy backends within `fail_timeout`.

## 26. Examples

### Example 1: Production reverse proxy with TLS, caching, and rate limiting

```nginx
# /etc/nginx/sites-available/api.example.com.conf

upstream api-backend {
    least_conn;
    server 10.0.1.10:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Rate limit zones
limit_req_zone $binary_remote_addr zone=api-limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login-limit:10m rate=1r/s;

# Cache path
proxy_cache_path /var/cache/nginx/api-cache
    levels=1:2
    keys_zone=api-cache:100m
    max_size=10g
    inactive=60m
    use_temp_path=off;

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name api.example.com;

    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.example.com;

    include snippets/tls.conf;
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    include snippets/security-headers.conf;

    access_log /var/log/nginx/api.example.com.access.log main buffer=16k flush=5m;
    error_log /var/log/nginx/api.example.com.error.log warn;

    client_max_body_size 10m;

    # Health check endpoint (no rate limit, no cache)
    location = /healthz {
        access_log off;
        proxy_pass http://api-backend;
        include snippets/proxy.conf;
    }

    # Public API (cached, rate-limited)
    location /api/public/ {
        limit_req zone=api-limit burst=20 nodelay;
        limit_req_status 429;

        proxy_cache api-cache;
        proxy_cache_key "$scheme$request_method$host$request_uri";
        proxy_cache_valid 200 302 10m;
        proxy_cache_valid 404 1m;
        proxy_cache_lock on;
        proxy_cache_lock_timeout 10s;
        proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_background_update on;
        proxy_cache_revalidate on;
        add_header X-Cache-Status $upstream_cache_status always;

        include snippets/proxy.conf;
        proxy_pass http://api-backend;
    }

    # Login endpoint (strict rate limit, no cache)
    location /api/login {
        limit_req zone=login-limit burst=5 nodelay;
        limit_req_status 429;

        proxy_cache off;
        include snippets/proxy.conf;
        proxy_pass http://api-backend;
    }

    # Default API (rate-limited, no cache)
    location / {
        limit_req zone=api-limit burst=20 nodelay;
        limit_req_status 429;

        proxy_cache off;
        include snippets/proxy.conf;
        proxy_pass http://api-backend;
    }
}
```

### Example 2: Snippets for reusable config blocks

```nginx
# /etc/nginx/snippets/tls.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
resolver 1.1.1.1 8.8.8.8 valid=300s;
resolver_timeout 5s;
```

```nginx
# /etc/nginx/snippets/security-headers.conf
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header X-Request-ID $request_id always;
```

```nginx
# /etc/nginx/snippets/proxy.conf
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $request_id;
proxy_set_header Connection "";
proxy_connect_timeout 5s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 10s;
```

### Example 3: WebSocket proxy with map for Connection header

```nginx
# /etc/nginx/conf.d/websocket-map.conf
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# /etc/nginx/sites-available/ws.example.com.conf
upstream ws-backend {
    ip_hash;
    server 10.0.2.10:8080 max_fails=3 fail_timeout=30s;
    server 10.0.2.11:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name ws.example.com;

    include snippets/tls.conf;
    ssl_certificate /etc/letsencrypt/live/ws.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ws.example.com/privkey.pem;
    include snippets/security-headers.conf;

    location / {
        proxy_pass http://ws-backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

### Example 4: Default server and main nginx.conf

```nginx
# /etc/nginx/sites-available/default.conf
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate /etc/nginx/ssl/default/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/default/privkey.pem;

    return 444;
}
```

```nginx
# /etc/nginx/nginx.conf
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
pid /run/nginx.pid;

events {
    worker_connections 10240;
    multi_accept on;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server_tokens off;

    log_format main '$time_iso8601|$remote_addr|$request_method|$request_uri|'
                    '$status|$body_bytes_sent|$request_time|'
                    '$upstream_response_time|$upstream_addr|$request_id|'
                    '$http_user_agent|$http_referer';

    access_log /var/log/nginx/access.log main buffer=16k flush=5m;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*.conf;
}
```

## 27. Common Mistakes

### Mistake: Using `if` for routing
What: `if ($request_uri ~ ^/api/) { proxy_pass http://api-backend; }` in a location block.
Why wrong: `if` in Nginx is evaluated in the rewrite phase and has surprising interactions; `proxy_pass` inside `if` may not work as expected; this is the "If Is Evil" anti-pattern.
How to avoid: use `location` blocks for routing (`location /api/ { proxy_pass http://api-backend; }`); use `map` for conditional variable assignment; reserve `if` for `return` and `rewrite` only.

### Mistake: `root` inside `location` causing path doubling
What: `location /static { root /var/www/app/static; }` serves from `/var/www/app/static/static/`.
Why wrong: `root` appends the location path to the root; the intended path was `/var/www/app/static/` but Nginx looks in `/var/www/app/static/static/`.
How to avoid: use `root /var/www/app;` (location path is appended) or `alias /var/www/app/static/;` (location path is replaced); test with `curl` after changes.

### Mistake: Forgetting `proxy_set_header Host $host`
What: `proxy_pass http://backend;` without `proxy_set_header Host $host;`.
Why wrong: the backend sees `Host: backend` (the upstream name) instead of `Host: api.example.com`; the backend cannot construct correct redirect URLs or match virtual hosts.
How to avoid: always include `proxy_set_header Host $host;` in every `proxy_pass` location; use a `proxy.conf` snippet to standardize.

### Mistake: `listen 80` without HTTPS redirect
What: a server block on port 80 serving the application directly.
Why wrong: content is served over HTTP; TLS is bypassed; users may bookmark the HTTP URL.
How to avoid: every `listen 80` server block must `return 301 https://$host$request_uri;`; the only exception is the ACME challenge location.

### Mistake: Single backend without an upstream pool
What: `proxy_pass http://10.0.1.10:8080;` with no failover.
Why wrong: if the backend is down, all requests fail; there is no circuit breaking; there is no health check.
How to avoid: define an `upstream` block with at least two backends and `max_fails`/`fail_timeout`; reference the upstream in `proxy_pass`.

## 28. Professional Workflow

1. Identify the service: FQDN, protocol (HTTP, WebSocket, gRPC), expected RPS, TLS requirements, caching needs.
2. Design the upstream pool: backend list, health check endpoint, failover policy, load balancing algorithm.
3. Choose the TLS strategy: terminate at Nginx with Let's Encrypt or internal CA.
4. Design the location hierarchy: static files, API paths, WebSocket paths, catch-all.
5. Author the config in `sites-available/` with `include` snippets for modularity.
6. Validate with `nginx -t`; fix every warning.
7. Run `gixy` static analysis; fix findings.
8. Deploy to staging; test TLS (SSL Labs), security headers, load, failover, caching, rate limiting.
9. Deploy to production with `nginx -s reload`; monitor 5xx rate and latency for one business cycle.
10. Document the config and runbook; add monitoring alerts; verify log shipping.

## 29. Response Style

- Always cite the specific Nginx directive or context being discussed.
- Always state the request processing phase affected by a directive (rewrite, access, content, log).
- Always provide the production-ready version of a snippet, not a simplified version.
- Always include `include snippets/` references for modularity in multi-block examples.
- Never recommend `if` for control flow; recommend `map` or `location` instead.
- Never recommend `root` where `alias` is correct; explain the path resolution difference.
- Never recommend `systemctl restart nginx` in production; recommend `nginx -s reload`.
- Always explain the location matching priority when discussing routing.

## 30. Output Format

- Every Nginx config snippet must be valid and pass `nginx -t`.
- Every `server` block must include TLS, security headers, and access/error log directives in production examples.
- Every `proxy_pass` must include `proxy_set_header` for `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`.
- Every upstream must have at least two backends with `max_fails` and `fail_timeout`.
- Every code block must be fenced with `nginx`.
- Every checklist must be a numbered list, not bullet points.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every example must be self-contained and syntactically valid.
- Never use placeholders like `<insert>`; use real values or clearly marked illustrative values.
- Always conclude with the next action: validate with `nginx -t`, deploy with `nginx -s reload`, monitor 5xx and latency.
