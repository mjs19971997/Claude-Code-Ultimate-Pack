# TLS, HTTP/2 and HTTP/3

Certificates, protocol settings, session resumption, OCSP status, HSTS, HTTP/2, HTTP/3 over QUIC and mutual TLS. Verified against the nginx.org module documentation for 1.31.x mainline and 1.30.x stable (2026-10).

## 1. Baseline TLS server

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;   # leaf + intermediates
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_session_cache   shared:SSL:10m;      # about 40000 sessions per 10 MB
    ssl_session_timeout 1h;
}
```

Defaults worth knowing (nginx.org docs):

| Directive | Default |
|---|---|
| `ssl_protocols` | `TLSv1.2 TLSv1.3` |
| `ssl_ciphers` | `HIGH:!aNULL:!MD5` |
| `ssl_prefer_server_ciphers` | `off` |
| `ssl_session_tickets` | `on` |
| `ssl_stapling` | `off` |
| `ssl_early_data` | `off` |

- With the defaults, no `ssl_protocols` or `ssl_ciphers` lines are needed for a secure modern configuration. Set `ssl_protocols TLSv1.3;` only when every client supports it. Never add `TLSv1`, `TLSv1.1` or `SSLv3`.
- TLS 1.3 cipher suites are not controlled by `ssl_ciphers`; use `ssl_conf_command Ciphersuites ...` only if policy requires, and check the OpenSSL documentation.
- The key file must be readable by the nginx master (which reads it as root before dropping privileges); keep it `0600` and owned by root. Never copy private keys into container images or repositories; mount them as secrets.
- `ssl_certificate` may be repeated to serve RSA and ECDSA certificates side by side; give each `ssl_certificate_key` in the same order.
- Variables can load certificates per host (`ssl_certificate /certs/$ssl_server_name.pem;`); this reads files on handshake unless certificate caching is configured, so check the current docs for `ssl_certificate_cache` before using it at scale.
- To reject unknown SNI names, add a default TLS server with `ssl_reject_handshake on;` (no certificate needed).

## 2. Session resumption

- `ssl_session_cache shared:SSL:10m;` lets all workers share session state. `builtin` (per-worker) caches are a poor default.
- Session tickets are on by default. Tickets are encrypted with keys held by the nginx process; keys that live for a long time weaken forward secrecy for resumed sessions. Either leave defaults and reload regularly, rotate a shared `ssl_session_ticket_key` file across a fleet with a secret-managed process, or set `ssl_session_tickets off;` if forward secrecy for resumed sessions matters more than handshake cost.
- Keep nginx patched: the project has shipped fixes for session ticket handling in the past; read the security advisories for the version you run.
- TLS 1.3 0-RTT (`ssl_early_data on;`) allows replay of early requests. Leave it off unless the application treats early-data requests as replayable (the `$ssl_early_data` variable can be passed upstream as a header so the app can reject non-idempotent early requests with 425).

## 3. OCSP stapling: current status

- `ssl_stapling on;` makes nginx fetch and staple OCSP responses; it requires the certificate to carry an OCSP responder URL and a `resolver` for the responder's hostname.
- Let's Encrypt retired OCSP: it stopped including OCSP URLs in new certificates and switched its responders off in August 2025. For its certificates nginx logs `"ssl_stapling" ignored, no OCSP responder URL in the certificate` and stapling does nothing. Remove `ssl_stapling` and `ssl_stapling_verify` from templates for these certificates; older certbot-generated `options-ssl-nginx.conf` files may contain them.
- Keep stapling for commercial CAs that still run an OCSP responder:

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/certs/ca-chain.pem;   # root + intermediates for verification
resolver 1.1.1.1 9.9.9.9 valid=300s;
resolver_timeout 5s;
```

- If a certificate was issued with the OCSP Must-Staple extension, disabling stapling breaks clients that enforce it; renew the certificate without Must-Staple first (check your ACME client's options).
- Check with `openssl s_client -connect example.com:443 -status -servername example.com`.

## 4. HSTS

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

- Introduce HSTS with a short `max-age` (for example 300) and raise it after verifying that HTTPS works on every subdomain covered by `includeSubDomains`.
- Add `preload` only if you intend to submit the domain to the browser preload list; removal is slow.
- HSTS is sent only over HTTPS responses; clients ignore it on plain HTTP.
- Remember `add_header` inheritance: repeat HSTS in any location that defines its own `add_header`.

## 5. HTTP/2

```nginx
http {
    http2 on;                        # all TLS servers; or set per server
    http2_max_concurrent_streams 128;      # default 128
    server {
        listen 443 ssl;
        ...
    }
}
```

- `http2 on;` (since 1.25.1) works in `http` or `server`. The older `listen 443 ssl http2;` still works but is deprecated and logs a warning. Do not mix both styles on the same listener.
- HTTP/2 is negotiated through ALPN on TLS listeners; HTTP/2 over cleartext (h2c) is possible with `listen 80; http2 on;` but browsers do not use it.
- `http2_max_concurrent_streams`, `http2_max_field_size` and related limits bound abuse; keep defaults unless measurements show a reason, and keep nginx patched, since HTTP/2 implementations have had denial-of-service issues across all servers.
- HTTP/2 server push (`http2_push`) is not useful with modern browsers; prefer `Link: rel=preload` or 103 Early Hints from the application.
- Proxying to upstreams: `proxy_http_version 2` is accepted since 1.29.4 and needs the HTTP/2 module; `grpc_pass` requires `http2` on the client-facing listener.

## 6. HTTP/3 and QUIC

```nginx
http {
    server {
        listen 443 quic reuseport;            # UDP; reuseport once per address:port across all servers
        listen 443 ssl;                       # TCP for HTTP/1.1 and HTTP/2
        listen [::]:443 quic reuseport;
        listen [::]:443 ssl;

        http2 on;
        http3 on;                             # default on, listed for clarity
        quic_retry on;                        # QUIC address validation (default off)

        server_name example.com;
        ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
        # QUIC always uses TLS 1.3; keep the default ssl_protocols so TCP clients can still use TLS 1.2

        add_header Alt-Svc 'h3=":443"; ma=86400' always;
    }
}
```

- The module is not built by default: it needs `--with-http_v3_module`, and OpenSSL 1.1.1 or newer (0-RTT needs OpenSSL 3.5.1+; BoringSSL, LibreSSL or QuicTLS also work). The nginx.org module documentation still describes HTTP/3 as experimental. Check `nginx -V 2>&1 | grep http_v3`.
- Browsers learn about HTTP/3 from the `Alt-Svc` response header (or HTTPS DNS records); the first request uses TCP. Use the same port number for TCP and UDP for best compatibility.
- Open UDP 443 in host, cloud and container firewalls; Docker needs `-p 443:443/udp` in addition to TCP.
- The `$http3` variable is `h3` for HTTP/3 requests and empty otherwise; log it to measure adoption.
- Other directives: `http3_max_concurrent_streams`, `http3_stream_buffer_size`, `quic_gso` (UDP segmentation offload on Linux), `quic_bpf` (connection migration across workers with `reuseport` on Linux), `quic_host_key` (stateless reset key), `quic_active_connection_id_limit`.
- Rate limiting and `real_ip` work the same for QUIC clients, but QUIC makes IP-based controls easier to evade through connection migration; keep application-level limits as well.
- Recent releases have fixed several HTTP/3 and QUIC security bugs; run a current patched build if you enable it on the public internet.
- ECH (Encrypted ClientHello) is supported in recent releases through `ssl_ech_file` (since 1.29.4, requires OpenSSL 4.0 or newer); treat it as a new feature and read the current docs before relying on it.

## 7. Mutual TLS for clients

```nginx
ssl_client_certificate /etc/nginx/certs/client-ca.pem;   # CAs offered and trusted
ssl_verify_client      on;                               # optional | optional_no_ca | off
ssl_verify_depth       2;

location / {
    proxy_set_header X-Client-Verified $ssl_client_verify;
    proxy_set_header X-Client-DN       $ssl_client_s_dn;
    proxy_pass http://app;
}
```

- Overwrite identity headers with nginx values so a client cannot supply its own `X-Client-DN`.
- For revocation use `ssl_crl`, the `ssl_ocsp` directive (see the ssl module docs), or short-lived client certificates.
- Use `optional` with an explicit check (`if ($ssl_client_verify != SUCCESS) { return 403; }` is one of the safe uses of `if`) for routes that mix public and certificate-protected paths.

## 8. TLS to upstreams

```nginx
location / {
    proxy_pass https://backend.internal:8443;
    proxy_ssl_server_name on;                   # send SNI
    proxy_ssl_name backend.internal;            # name to verify and send
    proxy_ssl_verify on;                        # off by default!
    proxy_ssl_trusted_certificate /etc/nginx/certs/internal-ca.pem;
    proxy_ssl_protocols TLSv1.2 TLSv1.3;
    # mTLS to the backend:
    proxy_ssl_certificate     /etc/nginx/certs/nginx-client.pem;
    proxy_ssl_certificate_key /etc/nginx/certs/nginx-client.key;
}
```

`proxy_ssl_verify` defaults to off, so `proxy_pass https://` encrypts but does not authenticate the backend until it is turned on.

## 9. Testing

```bash
openssl s_client -connect example.com:443 -servername example.com -tls1_3 </dev/null
openssl s_client -connect example.com:443 -servername example.com -tls1_1 </dev/null   # must fail
curl -sI --http2 https://example.com/ | head -1
curl -sI --http3 https://example.com/ | head -1           # needs a curl built with HTTP/3
nginx -t && nginx -T | grep -E 'ssl_protocols|http2|http3|quic'
```
