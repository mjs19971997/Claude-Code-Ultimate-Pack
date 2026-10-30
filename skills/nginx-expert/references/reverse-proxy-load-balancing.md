# Reverse Proxy and Load Balancing

Location matching, `proxy_pass` URI rules, forwarded headers, upstream blocks, failover, WebSockets, streaming, gRPC and the `stream` context. Verified against nginx 1.31.x mainline and 1.30.x stable module documentation (2026-10).

## 1. Server and location selection

Server selection: nginx matches the listen address and port first, then `server_name` in this order: exact name, longest wildcard starting with `*`, longest wildcard ending with `*`, first matching regular expression (in file order), then the `default_server` for that address and port.

Location selection:

1. `location = /path` exact match ends the search.
2. Longest matching prefix is remembered; if it carries `^~`, regex locations are skipped.
3. Regex locations (`~` case-sensitive, `~*` case-insensitive) are tried in file order; the first match wins.
4. Otherwise the remembered longest prefix is used.

```nginx
location = /healthz        { return 200 "ok\n"; }          # exact, cheap, internal use only
location ^~ /static/       { alias /srv/app/assets/; }     # prefix, skips regex locations
location ~* \.(?:png|jpg|svg)$ { expires 30d; }            # regex
location /                 { proxy_pass http://app; }      # catch-all prefix
```

- Nginx normalizes the URI (decoding, `..` and `.` segments, merged slashes) before matching, so `location` rules match the normalized path. Keep `merge_slashes on` (default) unless an application requires otherwise.
- Named locations `@fallback` are for `try_files` and `error_page` only.
- Expose a `/healthz` style endpoint only if it reveals nothing and is restricted (`allow` internal networks, `deny all`) when it is not meant for the public.

## 2. proxy_pass URI rules

| Config | Request `/api/users` goes to |
|---|---|
| `location /api/ { proxy_pass http://app; }` | `http://app/api/users` (URI unchanged) |
| `location /api/ { proxy_pass http://app/; }` | `http://app/users` (matched prefix replaced) |
| `location /api/ { proxy_pass http://app/v2/; }` | `http://app/v2/users` |
| `location ~ ^/api/ { proxy_pass http://app; }` | URI unchanged (a URI part is not allowed with regex locations) |
| `proxy_pass http://$backend;` | variables disable prefix replacement; hostnames need `resolver` |

- With `rewrite ... break;` inside the location, nginx uses the rewritten URI and ignores any URI in `proxy_pass`.
- When `proxy_pass` uses variables, nginx resolves names at request time through `resolver` (for example `resolver 127.0.0.11 valid=10s;` for Docker's embedded DNS). Name resolution through `upstream` blocks happens at start-up or reload unless the `resolve` parameter and a shared `zone` are used (the `resolve` server parameter is available in open source since 1.27.3).

## 3. Forwarded headers

```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $remote_addr;            # nginx is the first proxy: overwrite
# proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # behind another trusted proxy: append
proxy_set_header X-Forwarded-Proto $scheme;
```

- By default nginx does not pass the client's `Host` and `Connection` headers; it sends `Host: $proxy_host` and `Connection: close`, unless proxying uses HTTP/1.1 with the keepalive defaults described below.
- `$proxy_add_x_forwarded_for` appends `$remote_addr` to whatever the client sent. Use it only when `$remote_addr` is already the trusted client or when the application takes the rightmost trusted entry. Use overwriting (`$remote_addr`) at the edge so clients cannot inject values.
- The standard header is `Forwarded` (RFC 7239); most applications still read `X-Forwarded-*`. Configure the application framework's trusted proxy setting to match, otherwise it will honor forged headers.
- `proxy_set_header` directives at a lower level replace all inherited ones; repeat the full set (or use an include snippet).
- Strip headers the backend should not see from clients (for example internal auth headers): `proxy_set_header X-Internal-User "";`.

## 4. Upstream blocks

```nginx
upstream app {
    zone app 64k;                         # shared state across workers; needed for resolve
    least_conn;
    server 10.0.1.10:8080 weight=3 max_fails=3 fail_timeout=10s;
    server 10.0.1.11:8080 max_fails=3 fail_timeout=10s;
    server 10.0.1.12:8080 backup;         # used when all primary servers are unavailable
    keepalive 64;
    keepalive_time 1h;
    keepalive_timeout 60s;
}
```

Methods:

| Directive | Behavior |
|---|---|
| (default) | Weighted round-robin |
| `least_conn;` | Fewest active connections; good for uneven request durations |
| `ip_hash;` | Same client IPv4 /24 or IPv6 address maps to the same server; breaks behind NAT and CDNs unless `real_ip` is configured |
| `hash $key [consistent];` | Hash of any key such as `$request_uri` or `$cookie_session`; `consistent` limits remapping when servers change |
| `random [two [method]];` | Random choice; `two` picks two and uses `least_conn` (default) between them |

Server parameters: `weight`, `max_conns`, `max_fails` (default 1), `fail_timeout` (default 10s, also the unavailability window), `backup`, `down`, `resolve`. NGINX Plus only: `sticky`, `queue`, `slow_start`, `least_time`, `drain`, `route`, active health checks and the runtime API.

- Passive health: a server is marked unavailable after `max_fails` failed attempts within `fail_timeout`; what counts as a failure is controlled by `proxy_next_upstream` (default `error timeout`).
- Keepalive: since 1.29.7 upstream keepalive is on by default (32 idle connections per worker) and proxying defaults to HTTP/1.1, so the old `proxy_http_version 1.1;` and `proxy_set_header Connection "";` lines are no longer required. On older releases both are required together with `keepalive N;` or connections are closed after every request. Keep `keepalive` small enough that the backend can serve new connections too; it limits idle connections per worker, not total connections.
- A server defined in `upstream` can use `proxy_pass https://app;` with `proxy_ssl_*` directives to talk TLS to the backends.

## 5. Failover and retries

```nginx
location /api/ {
    proxy_pass http://app;
    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 10s;
    proxy_connect_timeout 3s;
    proxy_read_timeout 30s;
    proxy_send_timeout 30s;
}
```

- Default retry conditions are `error timeout`. `http_500` and others are opt-in. POST, PATCH and LOCK are not retried after the request reached an upstream unless `non_idempotent` is added.
- Bound retries with `proxy_next_upstream_tries` and `proxy_next_upstream_timeout` so one slow request cannot hit every server in turn.
- `proxy_read_timeout` is the time between two reads, not the total response time.
- Status mapping for debugging: 502 means the upstream connection failed or returned an invalid response; 504 means connect or read timeout; 503 is also what rate limits return unless changed; `no live upstreams` in the error log means every server is marked unavailable.

Log the upstream view:

```nginx
log_format upstream '$remote_addr "$request" $status $body_bytes_sent '
                    'rt=$request_time uct=$upstream_connect_time urt=$upstream_response_time '
                    'us=$upstream_status ua=$upstream_addr rid=$request_id';
access_log /var/log/nginx/access.log upstream;
```

## 6. WebSocket and streaming

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

location /ws/ {
    proxy_pass http://app;
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host       $host;
    proxy_read_timeout 1h;           # idle WebSocket connections are closed after this
}

location /events/ {                  # Server-Sent Events
    proxy_pass http://app;
    proxy_buffering off;             # stream responses as they arrive
    proxy_cache off;
    proxy_read_timeout 1h;
    add_header X-Accel-Buffering "no" always;
}
```

- Hop-by-hop headers (`Upgrade`, `Connection`) are not passed by default; the `map` keeps normal requests on `close`/keepalive behavior and upgrades only when asked.
- Validate the `Origin` header in the application, since nginx does not enforce WebSocket origin rules.
- Limit connections per client for long-lived routes with `limit_conn`.

## 7. Request and response buffering

- `proxy_buffering on` (default) lets nginx read the whole upstream response quickly and serve slow clients itself. Turn off per location for streaming.
- `proxy_request_buffering on` (default) reads the whole request body before contacting the upstream, which protects the app from slow uploads; turn off only for streaming uploads and large bodies you want to pass through.
- Raise `proxy_buffer_size` only when upstream response headers are large (for example big cookies), and `large_client_header_buffers` for large request headers.
- Buffers spill to disk in `proxy_temp_path` when responses exceed memory buffers; `proxy_max_temp_file_size 0;` disables spilling at the cost of back-pressure on upstreams.

## 8. gRPC

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name grpc.example.com;
    ssl_certificate     /etc/nginx/certs/grpc.crt;
    ssl_certificate_key /etc/nginx/certs/grpc.key;

    location /example.v1.Greeter/ {
        grpc_pass grpc://127.0.0.1:50051;      # grpcs:// for TLS to the backend
        grpc_read_timeout 60s;
    }
}
```

`grpc_pass` needs `http2` on the listener, and the backend scheme is `grpc://` or `grpcs://`. Authentication metadata is passed as normal headers; restrict who may reach internal gRPC services at the network level.

## 9. The stream context (TCP and UDP)

```nginx
stream {
    map $ssl_preread_server_name $backend {
        db.example.com    10.0.2.10:5432;
        default           127.0.0.1:8443;
    }
    server {
        listen 443;
        ssl_preread on;                 # read SNI without terminating TLS
        proxy_pass $backend;
    }
}
```

- `stream` needs the stream modules (`--with-stream`, `--with-stream_ssl_preread_module`); check `nginx -V`.
- Do not expose databases or admin protocols through a stream proxy to the internet; restrict with `allow`/`deny` in the stream server or firewall rules.
- Real client IP across a TCP hop requires the PROXY protocol (`proxy_protocol on;` on the outbound side and `listen ... proxy_protocol;` plus `set_real_ip_from`/`real_ip_header proxy_protocol;` on the receiving nginx).
