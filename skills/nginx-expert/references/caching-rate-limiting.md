# Caching, Rate Limiting and Client IP

Designing `proxy_cache`, `limit_req`, `limit_conn` and `real_ip` safely. Verified against the nginx.org module documentation for 1.31.x mainline and 1.30.x stable (2026-10).

## 1. proxy_cache

```nginx
# http context
proxy_cache_path /var/cache/nginx/app levels=1:2 keys_zone=app:20m
                 max_size=2g inactive=30m use_temp_path=off;

map $http_authorization$cookie_session $skip_cache {
    default 1;               # any credential present: do not cache
    ""      0;
}

server {
    ...
    location /api/public/ {
        proxy_pass http://app;

        proxy_cache            app;
        proxy_cache_key        "$scheme$host$request_uri";
        proxy_cache_valid      200 301 302 5m;
        proxy_cache_valid      404 30s;
        proxy_cache_methods    GET HEAD;                # default
        proxy_cache_min_uses   2;                       # only cache repeatedly requested URLs
        proxy_cache_lock       on;                      # one request fills a missing entry
        proxy_cache_lock_timeout 5s;
        proxy_cache_background_update on;               # refresh stale entries in the background
        proxy_cache_use_stale  error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_bypass     $skip_cache;             # do not serve from cache
        proxy_no_cache         $skip_cache;             # do not store

        add_header X-Cache-Status $upstream_cache_status always;
    }
}
```

Key facts:

- `proxy_cache_path` parameters: `levels`, `keys_zone=name:size`, `max_size`, `inactive` (remove entries not accessed for this time, default 10m), `min_free`, `use_temp_path`, plus loader, manager and purger tuning. Zone memory holds keys and metadata (about 8000 keys per MB); the cache directory holds bodies.
- Default `proxy_cache_key` is `$scheme$proxy_host$request_uri`. Include everything that changes the response: `$host` for multi-tenant servers, a language or device variable if used, and never omit the query string unless the app ignores it.
- Responses with `Set-Cookie` are not cached by default, nor are those with `Cache-Control: private`, `no-cache`, `no-store` or `Vary: *`; origin `Cache-Control`, `Expires` and `X-Accel-Expires` headers set the TTL before `proxy_cache_valid` applies. `proxy_cache_valid` with only a time caches 200, 301 and 302.
- `proxy_ignore_headers Set-Cookie Cache-Control;` overrides those protections and is how personalized pages end up shared between users; use it only for endpoints verified to be identical for everyone.
- `proxy_cache_lock on` collapses a stampede on a cold entry into one upstream request; `proxy_cache_use_stale ... updating` plus `proxy_cache_background_update on` serves stale content while one request refreshes it.
- `proxy_cache_revalidate on` uses conditional requests (`If-Modified-Since`, `If-None-Match`) to refresh expired entries cheaply.
- `proxy_cache_purge` is a commercial feature. In open source, delete files (the file name is the MD5 of the key) or shorten TTLs and use versioned URLs.
- `$upstream_cache_status` values: `MISS`, `BYPASS`, `EXPIRED`, `STALE`, `UPDATING`, `REVALIDATED`, `HIT`. Expose it in a header only in non-production environments if you do not want to reveal cache behavior.
- Mount the cache path on a volume with enough space and inodes; in containers use a named volume or tmpfs sized to `max_size`.

Micro-cache for a hot anonymous endpoint:

```nginx
location = /api/public/news {
    proxy_pass http://app;
    proxy_cache app;
    proxy_cache_valid 200 5s;
    proxy_cache_lock on;
    proxy_cache_use_stale updating error timeout;
    proxy_cache_background_update on;
}
```

Static assets and browser caching:

```nginx
location /assets/ {                                  # fingerprinted file names (app.3f2a1c.js)
    alias /srv/app/assets/;
    expires 1y;
    add_header Cache-Control "public, immutable" always;
}
location = /index.html {
    root /srv/app;
    add_header Cache-Control "no-cache" always;      # always revalidate the entry document
}
```

Remember `add_header` inheritance: headers declared at server level are dropped by these locations, so include the security-headers snippet again.

## 2. Request rate limiting (limit_req)

`limit_req` implements a leaky bucket per key.

```nginx
# http context
limit_req_zone $binary_remote_addr zone=perip:10m   rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m   rate=5r/m;
limit_req_zone $server_name        zone=perhost:1m  rate=200r/s;
limit_req_status 429;
limit_req_log_level warn;

server {
    limit_req zone=perip burst=20 nodelay;         # site-wide: 10 r/s with bursts up to 20
    limit_req zone=perhost burst=100;

    location = /login {
        limit_req zone=login burst=5 nodelay;      # 5 per minute plus 5 burst, then 429
        proxy_pass http://app;
    }
}
```

- `rate` is the sustained rate (`r/s` or `r/m`); `burst` is how many excess requests are queued; `nodelay` serves burst requests immediately and then rejects once the burst is consumed; `delay=N` (1.15.7) serves the first N excess requests immediately and delays the rest.
- Rejected requests get 503 by default; set `limit_req_status 429;`. `limit_req_dry_run on;` logs would-be rejections without enforcing, for tuning.
- Several `limit_req` directives can apply together (per IP and per host).
- Key choice: `$binary_remote_addr` (compact, 4 or 16 bytes) is right for per-IP limits. A zone of 1 MB holds roughly 16,000 IPv4 states; when the zone is full nginx evicts old entries and, if it cannot, rejects with an error.
- Behind a proxy or CDN the key must be the real client address; configure `real_ip` (below) first, otherwise all users share one bucket (or the attacker spoofs another).
- Do not key on a client-controlled header (`$http_x_forwarded_for`, `$http_user_agent`) for security limits.
- Rate limiting at nginx complements application limits (per user, per API key); it does not replace them. Credential stuffing protection needs per-account counters in the application.
- A `limit_req` set in a location replaces the inherited set from the server level for that location (the same inheritance rule as other directives), so repeat the site-wide limit when adding a stricter one.

## 3. Connection limiting (limit_conn)

```nginx
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn_status 429;

server {
    limit_conn addr 20;                       # at most 20 concurrent connections per IP

    location /downloads/ {
        limit_conn addr 2;
        limit_rate_after 5m;                  # full speed for the first 5 MB
        limit_rate 500k;                      # then 500 KB/s per connection
    }
}
```

- A connection is counted only while it has a request being processed by the server; idle keepalive connections are not counted.
- Slow-request defenses: `client_header_timeout`, `client_body_timeout`, `send_timeout`, and `reset_timedout_connection on;`.
- For long-lived routes such as WebSockets and SSE a low `limit_conn` per IP protects worker resources.

## 4. Client IP: ngx_http_realip_module

The module is built with `--with-http_realip_module` in the common packages. It replaces `$remote_addr` (and the port) with a value taken from a header, but only when the connecting peer is trusted.

```nginx
set_real_ip_from  10.0.0.0/8;           # your own load balancer or proxy
set_real_ip_from  192.0.2.0/24;         # replace with your CDN's published ranges
real_ip_header    X-Forwarded-For;      # or X-Real-IP, or proxy_protocol
real_ip_recursive on;                   # skip trusted addresses from the right
```

- `real_ip_header` defaults to `X-Real-IP`. With `X-Forwarded-For` and `real_ip_recursive on`, nginx walks the list from the right and picks the first address that is not trusted. With `real_ip_recursive off` (default) it takes the last address.
- `set_real_ip_from unix:;` trusts all UNIX-domain sockets; `proxy_protocol` as `real_ip_header` reads the PROXY protocol header from a load balancer that sends it (the listener needs `listen 443 ssl proxy_protocol;`).
- Trust exactly the proxies you operate. A broad `set_real_ip_from 0.0.0.0/0;` makes the header attacker-controlled and defeats `limit_req`, `limit_conn`, `allow`/`deny` and log forensics.
- Keep the original peer address in logs for investigations: `$realip_remote_addr` holds the address before replacement.
- When the origin is reachable only from the CDN, enforce that with a firewall as well; otherwise requests that bypass the CDN can still reach nginx directly.
- Cloud CDNs publish their IP ranges and often send a dedicated header (for example a connecting-IP header); update the ranges automatically and prefer the provider's dedicated header when available.

## 5. Access control

```nginx
location /internal-tools/ {
    allow 10.20.0.0/16;
    allow 127.0.0.1;
    deny  all;                       # first match wins, order matters
    proxy_pass http://tools;
}

location = /nginx_status {
    stub_status;                     # active connections, accepts, handled, requests
    allow 127.0.0.1;
    deny  all;
}
```

- `allow`/`deny` rely on `$remote_addr`; verify `real_ip` is correct first.
- Put `stub_status` on a loopback or management-only `listen`, not the public listener. Metrics exporters scrape it from inside the host or network.
- `auth_basic` with `auth_basic_user_file` suits simple internal protection; use bcrypt or similar hashes from `htpasswd -B`, serve it only over TLS, and combine with `allow`/`deny` using `satisfy all;`.
- Block scanners cheaply by returning 444 on default servers and for obviously invalid paths; avoid long regex blocklists that need constant upkeep.

## 6. Logging fields for tuning

```nginx
log_format main '$remote_addr [$time_local] "$request" $status $body_bytes_sent '
                'rt=$request_time cache=$upstream_cache_status '
                'limit=$limit_req_status rid=$request_id';
```

`$limit_req_status` (available since 1.17.6) records `PASSED`, `DELAYED`, `REJECTED` and their dry-run variants, which makes tuning `burst` values data-driven instead of guesswork.
