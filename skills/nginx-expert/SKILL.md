---
name: nginx-expert
description: >-
  Configures and hardens nginx as a web server, TLS terminator, reverse proxy, load balancer and cache: server and location matching, proxy_pass and upstream blocks, TLS 1.2/1.3, HTTP/2 and HTTP/3 (QUIC), security headers, limit_req and limit_conn rate limiting, proxy_cache, real_ip behind CDNs and static file serving. Use when writing or reviewing nginx.conf, conf.d or sites-enabled files, server_name, location, alias, try_files, upstream, ssl_*, add_header or proxy_* directives, 502 and 504 errors, or nginx inside Docker. Not for Kubernetes ingress-nginx resources and manifests (use kubernetes-expert), general Linux hardening (use linux-expert), or application-level auth and CORS design (use api-security-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Nginx Expert

This skill covers writing correct, secure and fast nginx configuration: how requests are matched to servers and locations, how to proxy and balance to upstreams, how to terminate TLS with HTTP/2 and HTTP/3, and how to add rate limits, caching and security headers without opening new holes. It targets open source nginx. Features that exist only in NGINX Plus are called out.

> Verified against nginx 1.31.x mainline (1.31.8) and 1.30.x stable (1.30.6) as of 2026-10, including the `http2` and `http3` directives and the nginx.org module documentation (2026-10).

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

- Covered: `nginx.conf` structure and inheritance, server and location selection, `root` versus `alias`, `try_files`, reverse proxy and upstream behavior, WebSocket and streaming proxying, TLS, HTTP/2, HTTP/3, security headers, rate and connection limits, `proxy_cache`, `real_ip`, gzip, logging formats, container and package layout.
- Not covered: Kubernetes ingress-nginx annotations (kubernetes-expert), kernel and OS hardening (linux-expert), designing authentication, CORS policy and API authorization (api-security-expert, authentication-expert), CDN configuration, NGINX Plus only features (active health checks, `sticky`, `queue`, `proxy_cache_purge`, dynamic reconfiguration API).

## 2. Core Expertise

| Topic | Key facts |
|---|---|
| Versions | Mainline (odd minor, currently 1.31.x) receives features and fixes first; stable (even minor, currently 1.30.x) receives only critical fixes. Both get security patches; run a patched release of either line |
| Request flow | Pick `server` by listen address and `server_name`; pick `location` by `=`, then longest `^~` prefix, then first matching regex, then longest plain prefix |
| Inheritance | Directives inherit downward only when the child context sets none of the same kind. `add_header`, `proxy_set_header` and `error_page` are replaced entirely, not merged, by a lower-level declaration |
| HTTP/2 | `http2 on;` (1.25.1+) at `http` or `server` level. The `http2` parameter of `listen` is deprecated and logs a warning |
| HTTP/3 | `listen 443 quic reuseport;` plus `listen 443 ssl;`, `http3 on;` (default on once a `quic` listener exists), and an `Alt-Svc` header. Needs `--with-http_v3_module`; the module is documented as experimental |
| TLS defaults | `ssl_protocols` defaults to `TLSv1.2 TLSv1.3`; `ssl_ciphers` defaults to `HIGH:!aNULL:!MD5`; `ssl_stapling` defaults to off |
| Upstream defaults | Since 1.29.7 proxying uses HTTP/1.1 and upstream keepalive is on (32 idle connections per worker). Older versions need `proxy_http_version 1.1;` and `proxy_set_header Connection "";` |
| Rate limiting | `limit_req_zone` + `limit_req` (leaky bucket, `burst`, `nodelay`); `limit_conn_zone` + `limit_conn`; rejected requests return 503 unless `limit_req_status` or `limit_conn_status` is set (use 429) |
| Client IP | `ngx_http_realip_module` (`set_real_ip_from`, `real_ip_header`, `real_ip_recursive`) replaces `$remote_addr` only for trusted sources |
| Cache | `proxy_cache_path` + `proxy_cache`, `proxy_cache_key`, `proxy_cache_valid`, `proxy_cache_use_stale`, `proxy_cache_lock`, `proxy_cache_background_update`; `$upstream_cache_status` shows HIT, MISS, STALE and so on |

## 3. Workflow

1. Decide the role of each `server`: redirect-only HTTP, TLS site, internal API proxy, static host.
2. Define upstreams and the trust boundary: what the real client IP is, which proxies may set forwarded headers.
3. Write locations from most specific to least, using exact or `^~` prefixes where possible and regex only when needed.
4. Add TLS, then HTTP/2 and HTTP/3, then security headers, then limits and caching.
5. Check syntax and the effective config: `nginx -t`, then `nginx -T` to see every included file.
6. Reload without dropping connections: `nginx -s reload` (or `systemctl reload nginx`); a failed test keeps the old config running.
7. Verify with `curl -vk --resolve example.com:443:127.0.0.1 https://example.com/`, `curl --http3` where available, and `openssl s_client -connect host:443 -servername host`.
8. Review error log levels and the upstream response codes for the new routes before rolling out broadly.

## 4. Decision Rules

- Terminate TLS at nginx and use HTTP/1.1 keepalive to upstreams; re-encrypt with `proxy_pass https://...` plus `proxy_ssl_verify on` when the network between nginx and the app is untrusted.
- `return 301 https://$host$request_uri;` for HTTP-to-HTTPS redirects; do not use `rewrite` or `if` for that.
- Prefer `root` over `alias`. Use `alias` only when the URL path and filesystem path differ, and keep the trailing slash identical on the location and the alias.
- Avoid `if` inside `location` except for `return` and `rewrite ... last`; use `map` for conditional values.
- Choose the balancing method by workload: round-robin by default, `least_conn` for uneven request durations, `ip_hash` or `hash $cookie_x consistent` only when affinity is required, `random two least_conn` for large pools.
- Retry only idempotent requests: by default `proxy_next_upstream` does not pass POST, PATCH or LOCK requests to the next server once a request has been sent upstream; adding `non_idempotent` allows it and can duplicate side effects.
- Cache only responses that are the same for all users; key and bypass on `Authorization` and cookies deliberately (see the caching reference).
- Use `limit_req` for request rate and `limit_conn` for concurrent connections; apply tight limits to login, password reset and search endpoints, looser ones site-wide.
- Enable OCSP stapling only for certificates whose CA still runs an OCSP responder. Let's Encrypt shut its OCSP service down in 2025 and its certificates no longer carry an OCSP URL, so `ssl_stapling on` only logs a warning for them.
- Run the mainline build when you need a feature such as HTTP/3 fixes sooner; run stable where change control is strict.

## 5. Coding Standards

- One concern per file under `conf.d/` or `sites-enabled/`: `00-defaults.conf`, `example.com.conf`, `snippets/ssl.conf`, `snippets/security-headers.conf`.
- Declare `default_server` explicitly for ports 80 and 443 and make it reject unknown hosts (`return 444;` and `ssl_reject_handshake on;`).
- Always quote header values containing spaces or semicolons, and put `always` on `add_header` so error responses carry the headers too.
- Set `server_name` precisely; avoid `server_name _;` on real sites. Use `$host` (normalized) rather than `$http_host` when building redirects.
- Prefer `return` over `rewrite`; anchor and escape regex locations (`location ~ \.php$`), never leave an unanchored `~ php`.
- Always end `proxy_pass` decisions deliberately: with a URI part (`proxy_pass http://app/;`) nginx replaces the matched prefix, without it the original URI is sent unchanged. With variables in `proxy_pass`, no prefix replacement happens and a `resolver` is required for hostnames.
- Keep timeouts explicit on proxied locations: `proxy_connect_timeout`, `proxy_send_timeout`, `proxy_read_timeout`.
- Comment non-obvious values (burst sizes, cache TTLs) and the reason; `include` shared snippets instead of copy-pasting.

## 6. Project Structure

```
/etc/nginx/
├── nginx.conf                    # main: worker settings, http {} with includes only
├── mime.types
├── conf.d/
│   ├── 00-defaults.conf          # default_server catch-alls, log_format, limit zones, maps
│   ├── example.com.conf          # one file per site
│   └── upstreams.conf            # upstream blocks shared by sites
├── snippets/
│   ├── ssl.conf                  # protocols, session cache, ciphers if customized
│   ├── security-headers.conf     # add_header lines, included per server or location
│   ├── proxy-common.conf         # proxy_set_header Host/X-Forwarded-*, timeouts
│   └── real-ip-cdn.conf          # set_real_ip_from ranges for a known CDN
└── certs/                        # or /etc/letsencrypt/live/<name>/ managed by the ACME client
```

nginx.org packages and the official Docker image use `conf.d/`; Debian and Ubuntu packages use `sites-available/` and `sites-enabled/`.

## 7. Design Patterns

- **Catch-all default servers** that drop traffic with unknown `Host` headers, preventing host header abuse and scanner noise.
- **Snippet composition**: `include snippets/security-headers.conf;` in each server and again in any location that defines its own `add_header`.
- **Upstream with passive failover**: `server ... max_fails=3 fail_timeout=10s;` plus `proxy_next_upstream error timeout http_502 http_503 http_504;` and `keepalive`. Active health checks require NGINX Plus or an external checker.
- **Static assets with cache headers**: fingerprinted files get `expires 1y` and `Cache-Control: public, immutable`; HTML gets `no-cache`.
- **WebSocket upgrade via `map`**: `map $http_upgrade $connection_upgrade { default upgrade; '' close; }`.
- **Micro-cache** for hot anonymous GET endpoints (1 to 10 seconds with `proxy_cache_lock` and `use_stale updating`).
- **Edge limits per route** via named zones declared once in `http {}` and applied in specific locations.
- Detail: [references/reverse-proxy-load-balancing.md](references/reverse-proxy-load-balancing.md), [references/tls-http2-http3.md](references/tls-http2-http3.md), [references/caching-rate-limiting.md](references/caching-rate-limiting.md).

## 8. Best Practices

- Test every change with `nginx -t` in CI against the real included files, using a container with the same nginx version as production.
- Set `server_tokens off;` to drop the version from headers and error pages.
- Use `$request_id` in a `log_format` and pass it upstream (`proxy_set_header X-Request-ID $request_id;`) so a request can be traced across layers.
- Set `client_max_body_size` per location (default 1m) rather than globally to a large value; set it high only on upload routes.
- Return JSON or static error pages with `error_page` and `internal` locations; never expose upstream error bodies or stack traces.
- Use `map` and `geo` for data-driven decisions (allowlists, bot flags) instead of chained `if` blocks.
- Reload, do not restart, for config changes; restart only when upgrading the binary or changing modules.

## 9. Performance

- `worker_processes auto;` and a `worker_connections` large enough for peak (`events { worker_connections 4096; }`); raise `worker_rlimit_nofile` to at least twice that when proxying, since each proxied request uses two sockets.
- Keep upstream keepalive enabled so nginx reuses connections to the app (default on since 1.29.7; set `keepalive N;` explicitly on older versions).
- `sendfile on; tcp_nopush on; tcp_nodelay on;` for static content; `open_file_cache` for hot static sets.
- `gzip on; gzip_vary on; gzip_comp_level 5; gzip_types text/plain text/css application/json application/javascript image/svg+xml;` (HTML is always compressed once `gzip` is on). Do not gzip already-compressed formats. Brotli needs a separate module.
- `ssl_session_cache shared:SSL:10m;` so returning clients resume sessions without a full handshake.
- Leave `proxy_buffering on` for normal responses so slow clients do not hold app workers; turn it off only for streaming (SSE, long polling) locations, or let the app send `X-Accel-Buffering: no`.
- Cache what you can: static assets with long TTLs, and anonymous API or HTML responses with short TTLs and `proxy_cache_lock`.
- Use `reuseport` on the UDP `quic` listener (once per address and port) and keep a TCP listener for HTTP/1.1 and HTTP/2.

## 10. Security

- **Path traversal through `alias`**: with `location /static { alias /srv/app/assets/; }` (no trailing slash on the location) a request for `/static../secret.txt` matches the prefix, the remainder `../secret.txt` is appended to the alias, and nginx opens `/srv/app/assets/../secret.txt`. Fix: make the slashes match on both sides, `location /static/ { alias /srv/app/assets/; }`, or use `root`. Also never combine `alias` with user-controlled variables, and keep nginx patched; some security releases touch `alias` handling.
- **TLS**: leave `ssl_protocols` at the default `TLSv1.2 TLSv1.3` or restrict to `TLSv1.3` if all clients allow it; never enable TLS 1.0, 1.1 or SSL; no self-managed DH parameters needed with ECDHE.
- **Security headers** (set with `always`): `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, and a Content-Security-Policy without `unsafe-inline` or `unsafe-eval`. A static policy such as `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` works only if the page has no inline scripts or styles; for pages that need inline code use per-response nonces generated by the application. `X-XSS-Protection` is obsolete; omit it.
- **No internal endpoints on public listeners**: do not proxy `/admin`, `/debug`, `/metrics`, `/actuator`, `/swagger` or test and seed routes to the internet. Expose `stub_status` only on a loopback or private listener with `allow`/`deny`. Deny hidden files and VCS metadata: `location ~ /\.(?!well-known/) { deny all; }`.
- **Client IP trust**: configure `set_real_ip_from` with only the CIDRs of your own proxies or CDN; trusting `0.0.0.0/0` lets any client spoof `X-Forwarded-For` and bypass `limit_req` and `allow`/`deny`.
- **Header hygiene**: set `Host`, `X-Forwarded-For` (overwrite with `$remote_addr` when nginx is the edge) and `X-Forwarded-Proto` yourself; never forward client-supplied values you did not validate. Clear unneeded request headers with `proxy_set_header Name "";`.
- **Resource caps**: `client_max_body_size`, `client_body_timeout`, `client_header_timeout`, `keepalive_timeout`, `large_client_header_buffers`, `limit_req`, `limit_conn`.
- **HTTP/3 and 0-RTT**: keep `ssl_early_data off` unless the application handles replayed requests; consider `quic_retry on` for address validation.
- Keep nginx and its OpenSSL library patched; follow the nginx security advisories, and rebuild container images regularly.
- Run workers unprivileged (`user nginx;` is the default in packages); in containers use an unprivileged image variant listening on a high port.

## 11. Testing

- `nginx -t` (syntax and file access) and `nginx -T` (dump effective config) in CI.
- Config smoke tests with `curl` against a containerized nginx: status codes, redirects, headers (`curl -sI`), HTTP/2 (`curl --http2 -I`), HTTP/3 where curl supports it (`curl --http3`).
- Path traversal test for every `alias`: `curl --path-as-is 'https://host/static../etc/passwd'` must not return file content.
- TLS verification: `openssl s_client -connect host:443 -servername host -tls1_2` succeeds, `-tls1_1` fails; scan with a TLS testing tool in staging.
- Load and limit tests: confirm `limit_req` returns 429 after the burst and that legitimate bursts pass; confirm the real client IP appears in logs behind the CDN.
- Cache tests: send the same request twice and check `X-Cache-Status` (from `add_header X-Cache-Status $upstream_cache_status;`) for MISS then HIT, and check that authenticated requests are never HIT for another user.

## 12. Review Checklist

- [ ] `nginx -t` passes; `nginx -T` reviewed for unintended includes.
- [ ] Default servers reject unknown hosts on 80 and 443.
- [ ] HTTP redirects to HTTPS with `return 301`; HSTS set only after HTTPS works everywhere.
- [ ] `http2 on;` used instead of `listen ... http2`; HTTP/3 has an `Alt-Svc` header and UDP 443 open.
- [ ] Every `alias` has matching slashes (or is replaced with `root`); dotfiles denied.
- [ ] `add_header` repeated in locations that define their own; CSP has no `unsafe-inline`.
- [ ] `set_real_ip_from` lists only trusted proxies; forwarded headers set explicitly.
- [ ] No admin, debug, metrics or test endpoints reachable from the public side.
- [ ] Rate limits on authentication and expensive routes; body size and timeouts bounded.
- [ ] Caches key on everything that varies the response and never store personalized content.
- [ ] `server_tokens off;`, log format includes `$request_id`, upstream timeouts are explicit.

## 13. Production Notes

- Package repositories: nginx.org publishes mainline and stable builds; distro packages lag. The official Docker image tags follow the same lines (for example `nginx:1.30` for stable). Check `nginx -V` to confirm modules such as `http_v3_module` are compiled in.
- In Docker, run nginx unprivileged where possible (the `nginxinc/nginx-unprivileged` image listens on 8080), mount configuration read-only, send logs to stdout and stderr, and use `nginx -t` as a build step. For Compose stacks see docker-expert.
- Zero-downtime changes: `nginx -t && nginx -s reload`. Old workers finish in-flight requests; with long-lived WebSocket connections set `worker_shutdown_timeout`.
- Certificate renewal: reload nginx after the ACME client renews (`--deploy-hook "systemctl reload nginx"` or equivalent). Since certificates from Let's Encrypt no longer carry OCSP URLs, remove `ssl_stapling` lines copied from older templates (certbot's older `options-ssl-nginx.conf` included them).
- Behind a CDN or load balancer, restrict direct access to the origin by firewall to the CDN ranges so the `real_ip` configuration cannot be bypassed.
- Hot-reload does not apply `listen` socket option changes in every case, and new `reuseport` listeners may need a restart; test in staging.
- Upgrading across mainline releases: read the CHANGES file for directive defaults and removals (for example proxy HTTP version and keepalive defaults changed in 1.29.7).

## 14. Examples

TLS site with HTTP/2 and HTTP/3, reverse proxy to an app, security headers and a rate-limited login route:

```nginx
# conf.d/00-defaults.conf (http context)
map $http_upgrade $connection_upgrade { default upgrade; '' close; }
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_status 429;

server {                                   # reject unknown hosts
    listen 80 default_server;
    listen [::]:80 default_server;
    return 444;
}
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    ssl_reject_handshake on;               # no certificate for unknown SNI names
}

# conf.d/example.com.conf
upstream app {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    listen 443 quic reuseport;
    listen [::]:443 quic reuseport;
    http2 on;
    http3 on;
    server_name example.com;
    server_tokens off;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_session_cache   shared:SSL:10m;

    include snippets/security-headers.conf;
    add_header Alt-Svc 'h3=":443"; ma=86400' always;

    client_max_body_size 2m;

    location = /login {
        include snippets/security-headers.conf;   # add_header in a location replaces inherited ones
        limit_req zone=login burst=5 nodelay;
        include snippets/proxy-common.conf;
        proxy_pass http://app;
    }

    location / {
        include snippets/proxy-common.conf;
        proxy_pass http://app;
    }
}
```

```nginx
# snippets/security-headers.conf
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'" always;

# snippets/proxy-common.conf
proxy_http_version 1.1;                    # explicit for versions before 1.29.7
proxy_set_header Connection "";            # keep upstream connections reusable
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $request_id;
proxy_connect_timeout 5s;
proxy_read_timeout 30s;
```

Static files: the safe `alias` form, hidden files denied, no directory listing, fingerprinted assets cached:

```nginx
location /static/ {                         # slash on the location ...
    alias /srv/app/assets/;                 # ... and on the alias
    expires 1y;
    add_header Cache-Control "public, immutable" always;
    add_header X-Content-Type-Options "nosniff" always;
    autoindex off;
}

location ~ /\.(?!well-known/) { deny all; }
```

Behind a CDN: restore the real client address only from trusted ranges (replace with the CDN's published ranges):

```nginx
set_real_ip_from 203.0.113.0/24;           # example range; list your CDN or load balancer CIDRs
set_real_ip_from 2001:db8::/32;
real_ip_header   X-Forwarded-For;
real_ip_recursive on;                      # skip trusted hops from the right
```

## 15. Common Mistakes

- **`location /static { alias /srv/assets/; }`**: allows `/static../` traversal. Match the slashes or use `root`.
- **Forgetting `add_header` inheritance**: one `add_header` in a `location` silently drops all headers set at `server` level, including HSTS and CSP. Include the snippet again.
- **`listen 443 ssl http2;`** on new versions: deprecated; use `http2 on;`.
- **`ssl_stapling on;` with Let's Encrypt certificates**: no OCSP URL, so nginx logs "ssl_stapling ignored"; remove it.
- **`proxy_pass http://app/` versus `http://app`**: the trailing slash changes the upstream URI. Test with the access log.
- **`if ($request_uri ~ ...) { proxy_pass ... }`** and other `if` in `location` for logic: use `map` and `try_files`.
- **Trusting `X-Forwarded-For` from anyone**: spoofs the IP and defeats limits; use `set_real_ip_from` with real proxy CIDRs.
- **Caching authenticated responses** with a key of just `$uri`: serves one user's page to another. Include a discriminator or bypass the cache when `Authorization` or session cookies are present.
- **`limit_req` without `burst`**: any two requests in the same short window get rejected; use `burst` and decide on `nodelay`.
- **Large global `client_max_body_size`** to fix one upload route; scope it to that location.
- **Exposing `stub_status`, `/metrics` or a debug route** on the public listener.
- **Self-signed or mismatched `proxy_ssl_*` settings**: `proxy_pass https://` does not verify upstream certificates unless `proxy_ssl_verify on` and a trusted CA file are set.
- **Using `rewrite` for redirects** and `server_name` regexes where `return` and exact names work.
- **502/504 debugging without the error log**: check `error_log` for `connect() failed`, `upstream timed out` and `no live upstreams`, and compare `$upstream_status` and `$upstream_response_time` in the access log.

## 16. References

- [references/reverse-proxy-load-balancing.md](references/reverse-proxy-load-balancing.md): location matching, proxy_pass URI rules, headers, upstream blocks and balancing methods, failover, WebSockets, streaming, gRPC, the `stream` context.
- [references/tls-http2-http3.md](references/tls-http2-http3.md): certificates, protocol and cipher settings, session cache and tickets, OCSP status, HSTS, HTTP/2, HTTP/3 and QUIC, mTLS to clients and upstreams.
- [references/caching-rate-limiting.md](references/caching-rate-limiting.md): `proxy_cache` design, keys, bypass, stale serving, `limit_req`, `limit_conn`, `real_ip`, allow/deny and bot controls.
- Official docs: https://nginx.org/en/docs/ , https://nginx.org/en/docs/http/ngx_http_core_module.html , https://nginx.org/en/docs/http/ngx_http_v3_module.html , https://nginx.org/en/CHANGES
