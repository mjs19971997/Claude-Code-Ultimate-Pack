# Go HTTP Servers and Logging

Reference for building services on `net/http`, routing with `ServeMux`, middleware, limits, shutdown, a private pprof listener, outbound clients and `log/slog`. Verified against Go 1.27.3 and 1.26.10 (2026-10).

## Contents

1. [ServeMux patterns](#1-servemux-patterns)
2. [Server configuration and shutdown](#2-server-configuration-and-shutdown)
3. [Middleware and handlers](#3-middleware-and-handlers)
4. [Private debug server](#4-private-debug-server)
5. [HTTP clients](#5-http-clients)
6. [slog setup](#6-slog-setup)
7. [Version notes](#7-version-notes)

## 1. ServeMux patterns

Since Go 1.22 `http.ServeMux` matches method, host and path wildcards.

| Pattern | Matches |
|---|---|
| `/index.html` | that path, any method and host |
| `GET /static/` | GET and HEAD requests under `/static/` (a trailing slash is an anonymous `...` wildcard) |
| `POST /items` | POST to exactly `/items` |
| `GET /items/{id}` | one segment captured as `id`, read with `r.PathValue("id")` |
| `GET /files/{path...}` | the rest of the path, slashes included |
| `/{$}` | only `/`, whereas `/` matches every path |
| `example.com/` | any request to host `example.com` |

Rules worth knowing:

- Wildcards are whole path segments: `/b_{id}` is invalid. Names must be valid Go identifiers.
- The most specific pattern wins (`/images/thumbnails/` beats `/images/`). When neither is more specific the registration panics at startup, which is a feature: conflicts surface when the server starts, so cover route registration in a test.
- A method-less pattern matches all methods; a request whose path matches only patterns with other methods gets 405 Method Not Allowed.
- `r.Pattern` holds the matched pattern string, which is a low-cardinality label for logs and metrics, unlike `r.URL.Path`.
- Literal parts match case-sensitively; path segments are unescaped before matching, so `%2F` does not split a segment.
- Trailing-slash redirects (a request for `/dir` when `/dir/` is registered) use status 307 since Go 1.26.
- Wildcard values are strings from the client. Parse and validate them (`strconv.ParseInt`, UUID parsing) and return 400 on failure.

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /users/{id}", getUser)
mux.HandleFunc("POST /users", createUser)
mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNoContent)
})
mux.Handle("GET /static/", http.StripPrefix("/static/", http.FileServer(http.Dir("./public"))))
```

## 2. Server configuration and shutdown

`http.ListenAndServe` and a bare `http.Server{}` have no timeouts. Configure explicitly:

| Field | Purpose |
|---|---|
| `ReadHeaderTimeout` | Time to read request headers; set it on every public server (for example 5 s) |
| `ReadTimeout` | Whole request including body; if `ReadHeaderTimeout` is zero it applies there too |
| `WriteTimeout` | Response write deadline, reset per request header; must exceed the slowest legitimate handler |
| `IdleTimeout` | Keep-alive wait; falls back to `ReadTimeout` when zero |
| `MaxHeaderBytes` | Header size cap, default `DefaultMaxHeaderBytes` |
| `MaxHeaderValueCount` | Cap on header values (Go 1.27; defaults to `DefaultMaxHeaderValueCount`) |
| `BaseContext` | Root context for every request; do not wire the signal context here if in-flight requests should finish during shutdown |
| `ErrorLog` | `*log.Logger` for server-internal errors; bridge with `slog.NewLogLogger(handler, level)` |

Long-running streams (server-sent events, large downloads) conflict with a short `WriteTimeout`. Use `http.NewResponseController(w).SetWriteDeadline(...)` per handler to extend or clear the deadline for specific routes.

Graceful shutdown sequence:

1. Receive `SIGTERM` or `SIGINT` through `signal.NotifyContext`.
2. Mark readiness as failing so the load balancer stops sending traffic (details are orchestrator-specific; see kubernetes-expert for probes).
3. Call `srv.Shutdown(ctx)` with a timeout shorter than the platform's termination grace period. It closes listeners, closes idle connections and waits for active ones to finish. `ListenAndServe` returns `http.ErrServerClosed` immediately, so `main` must wait for `Shutdown` to return before exiting.
4. `Shutdown` ignores hijacked connections (WebSockets). Use `srv.RegisterOnShutdown(func() { ... })` to tell them to close, and wait for them separately.
5. If `Shutdown` returns a context error, call `srv.Close()` to drop what remains, then exit non-zero or log the incident.
6. Close databases and flush logs after the server has stopped.

The complete `run` function with this structure is in section 14 of [SKILL.md](../SKILL.md#14-examples).

## 3. Middleware and handlers

Middleware is `func(http.Handler) http.Handler`. Compose once, outermost first.

```go
package web

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"time"
)

type Middleware func(http.Handler) http.Handler

// Chain applies mws so that the first one is outermost.
func Chain(h http.Handler, mws ...Middleware) http.Handler {
	for i := len(mws) - 1; i >= 0; i-- {
		h = mws[i](h)
	}
	return h
}

// Recover turns a handler panic into a 500 and a log line.
func Recover(log *slog.Logger) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if v := recover(); v != nil {
					if v == http.ErrAbortHandler {
						panic(v) // deliberate abort: let the server handle it
					}
					log.ErrorContext(r.Context(), "panic in handler", "panic", v)
					http.Error(w, "internal error", http.StatusInternalServerError)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// RequestLog logs method, matched pattern and duration after the handler returns.
func RequestLog(log *slog.Logger) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			next.ServeHTTP(w, r)
			log.LogAttrs(r.Context(), slog.LevelInfo, "request",
				slog.String("method", r.Method),
				slog.String("pattern", r.Pattern),
				slog.Duration("dur", time.Since(start)),
			)
		})
	}
}

type createReq struct {
	Name string `json:"name"`
}

// Create decodes a size-limited JSON body strictly.
func Create(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var in createReq
	if err := dec.Decode(&in); err != nil {
		var mbe *http.MaxBytesError
		if errors.As(err, &mbe) {
			http.Error(w, "body too large", http.StatusRequestEntityTooLarge)
			return
		}
		http.Error(w, "invalid JSON", http.StatusBadRequest)
		return
	}
	w.WriteHeader(http.StatusCreated)
}

func Routes(log *slog.Logger) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /items", Create)
	cop := http.NewCrossOriginProtection() // Go 1.25+: rejects unsafe cross-origin browser requests
	return Chain(cop.Handler(mux), Recover(log), RequestLog(log))
}
```

Handler guidance:

- Validate input at the edge, return a client error for bad input and a generic message for server errors; log the detail with the request context.
- Wrap response writers carefully: a wrapper that hides `http.Flusher`, `http.Hijacker` or `io.ReaderFrom` breaks streaming. Use `http.NewResponseController(w)` and implement `Unwrap() http.ResponseWriter` on wrappers.
- Set `Content-Type` before the first `Write`; call `WriteHeader` once. After the first write, status and headers are fixed.
- Do not start goroutines that outlive the request using `r.Context()`; use `context.WithoutCancel` and your own timeout, and track them for shutdown.
- `http.CrossOriginProtection` guards browsers using cookie-based sessions; it complements, and does not replace, authentication and authorization checks in handlers.
- Reverse proxies: use `httputil.ReverseProxy` with `Rewrite`; `Director` is deprecated as of Go 1.26.

## 4. Private debug server

Importing `net/http/pprof` for side effects registers `/debug/pprof/` on `http.DefaultServeMux`. If the public server uses `DefaultServeMux` (or a nil `Handler`) the profiles become public. Register handlers on a separate mux instead and bind to loopback:

```go
package web

import (
	"net/http"
	"net/http/pprof"
	"time"
)

// DebugServer serves pprof on its own mux and a loopback address.
func DebugServer() *http.Server {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /debug/pprof/", pprof.Index)
	mux.HandleFunc("GET /debug/pprof/profile", pprof.Profile)
	mux.HandleFunc("GET /debug/pprof/trace", pprof.Trace)
	return &http.Server{
		Addr:              "127.0.0.1:6060",
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
}
```

- `pprof.Index` serves the named profiles (`heap`, `goroutine`, `allocs`, `block`, `mutex`, and `goroutineleak` from Go 1.27). `Profile` and `Trace` are separate handlers, so register them explicitly. A CPU profile request holds the connection for the sampling duration, so the debug server needs a `WriteTimeout` of zero or longer than the largest `seconds` you request.
- Reach it through `kubectl port-forward`, an SSH tunnel or an internal-only network, and add authentication if more than operators can reach that network.
- Profiles reveal code paths and sometimes data (goroutine stacks, goroutine labels); treat them as sensitive. From Go 1.27, goroutine labels also appear in tracebacks for modules with a `go` line of 1.27 or newer; keep secrets out of labels.

## 5. HTTP clients

- Reuse one `http.Client` (it is safe for concurrent use and pools connections). Set `Timeout` for the whole exchange, or pass a context with a deadline per request.
- Build requests with `http.NewRequestWithContext(ctx, method, url, body)`.
- Always close the response body. Reading it to the end allows connection reuse; since Go 1.27 HTTP/1 bodies are drained on `Close` up to a conservative limit. Limit what you read with `io.LimitReader`.
- Do not set `InsecureSkipVerify`. For an internal CA, build a `x509.CertPool` and set `tls.Config{RootCAs: pool, MinVersion: tls.VersionTLS12}` on the transport.
- Tune `http.Transport` (`MaxIdleConnsPerHost`, `IdleConnTimeout`, `TLSHandshakeTimeout`, `ResponseHeaderTimeout`) when talking to a single backend at high rate; clone `http.DefaultTransport` and change fields rather than building one from scratch.

## 6. slog setup

```go
package logging

import (
	"log/slog"
	"os"
)

func New(level slog.Level) *slog.Logger {
	opts := &slog.HandlerOptions{
		Level: level,
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			if a.Key == "password" || a.Key == "token" {
				return slog.String(a.Key, "[redacted]")
			}
			return a
		},
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, opts))
}
```

- Use key-value pairs or `slog.Attr`: `logger.InfoContext(ctx, "order created", "order_id", id, slog.Group("user", "id", uid))`. `LogAttrs` avoids allocations on hot paths.
- Build per-request loggers with `logger.With("request_id", id)` in middleware and store them in the context, or pass them explicitly.
- `slog.SetDefault` also redirects the `log` package output to the new handler; use `slog.NewLogLogger` to feed libraries that need a `*log.Logger`.
- Implement `slog.LogValuer` on types with sensitive fields so the logged form is safe by construction rather than by `ReplaceAttr` string matching.
- Levels: `Debug` (-4), `Info` (0), `Warn` (4), `Error` (8). Use `slog.LevelVar` to change the level at run time.
- Fan out to several destinations with `slog.NewMultiHandler` (Go 1.26+). On older versions write a small handler wrapper.
- In tests use `slog.New(slog.DiscardHandler)` or a handler writing to a buffer and assert on the output.

## 7. Version notes

- Go 1.22: method and wildcard patterns in `ServeMux`, `Request.PathValue`; pprof endpoints require GET. `GODEBUG=httpmuxgo121=1` restores the old matching for legacy programs only.
- Go 1.25: `http.CrossOriginProtection`.
- Go 1.26: trailing-slash redirects use 307; `ReverseProxy.Director` deprecated; `Client` cookie scoping uses `Request.Host`; `slog.NewMultiHandler`.
- Go 1.27: `Server.MaxHeaderValueCount`; HTTP/2 server honors client priority signals (RFC 9218) unless `Server.DisableClientPriority` is true; HTTP/1 response bodies drain on close; `httptest.NewTestServer` for use with `testing/synctest`; `go tool trace -http=:PORT` listens on localhost only.
