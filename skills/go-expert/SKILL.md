---
name: go-expert
description: >-
  Writes, reviews and debugs idiomatic Go 1.26 and 1.27 services and libraries: modules (go.mod, go and toolchain directives, tool directive, workspaces, GOPRIVATE), error wrapping, context, goroutines and channels, generics, table-driven tests and fuzzing, net/http servers with ServeMux patterns, slog, pprof and govulncheck. Use when working with .go files, go.mod, go.work, go test, go vet, errgroup, goroutine leaks, data races, http.Server timeouts or graceful shutdown. Not for container images (use docker-expert), Kubernetes manifests (use kubernetes-expert), OpenTelemetry or metrics pipelines (use observability-expert), or API design (use rest-api-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Go Expert

This skill covers everyday Go engineering: module and toolchain management, error handling, context propagation, concurrency, generics, testing, HTTP servers built on the standard library, structured logging, profiling and vulnerability scanning. It targets the two supported Go releases and flags which release introduced each feature so older modules can be handled correctly. Container packaging, cluster deployment, metrics and tracing pipelines, and HTTP API contracts belong to other skills.

> Verified against Go 1.27.3 (latest patch of the August 2026 release) and Go 1.26.10, golang.org/x/sync v0.24.0 and govulncheck v1.9.0 (2026-10).

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

- Covered: `go.mod` and `go.work`, toolchain selection, private modules, error design, `context`, goroutines, channels, `sync`, `errgroup`, generics, `testing` (tables, subtests, fuzzing, benchmarks, race detector, `testing/synctest`), `net/http` servers and middleware, `log/slog`, `net/http/pprof`, `go tool trace`, `govulncheck`.
- Not covered: Dockerfiles and image hardening (docker-expert), Kubernetes manifests and probes (kubernetes-expert), OpenTelemetry, Prometheus and tracing pipelines (observability-expert), resource modeling, versioning and error formats of HTTP APIs (rest-api-expert), SQL schema and query tuning (postgresql-expert), general application security review (secure-coding-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Releases | Each major release is supported until two newer major releases exist, so 1.26 and 1.27 are supported and 1.25 is not. Go 1.27 shipped in August 2026, Go 1.26 in February 2026 |
| Go 1.27 | Generic methods (a method may declare its own type parameters; interface methods may not). `encoding/json` is now backed by the v2 implementation, with new packages `encoding/json/v2` and `encoding/json/jsontext`; `GOEXPERIMENT=nojsonv2` restores the old one. `goroutineleak` pprof profile is generally available (`/debug/pprof/goroutineleak`). `go test` runs the `stdversion` vet check. vet `printf` flags `%w` of a `*E` where `E` implements `error`. `go tool trace -http=:6060` binds to localhost only. `testing/synctest.Sleep`. `asynctimerchan` GODEBUG removed |
| Go 1.26 | `new(expr)` sets an initial value, for example `new(yearsSince(born))`. Generic types may reference themselves in constraints. `errors.AsType[T]` is the generic `errors.As`. `slog.NewMultiHandler`. `T.ArtifactDir`. `go fix` was rewritten around analyzers (modernizers, `//go:fix inline`). Green Tea GC is the default. pprof web UI opens on the flame graph. `ServeMux` trailing-slash redirects use 307. `ReverseProxy.Director` is deprecated for `Rewrite` |
| Go 1.25 | `sync.WaitGroup.Go`. `testing/synctest` is generally available (`synctest.Test`, `synctest.Wait`; fake clock inside a bubble). `GOMAXPROCS` follows the cgroup CPU limit on Linux and updates at run time. `runtime/trace.FlightRecorder`. `http.CrossOriginProtection`. `go.mod` `ignore` directive. vet analyzers `waitgroup` and `hostport`. The go command stops adding a `toolchain` line when it updates `go` |
| Go 1.24 | `tool` directive in `go.mod`, `go get -tool`, `go tool <name>`. `testing.B.Loop`. `T.Context` and `B.Context`. `os.Root` for traversal-resistant file access. `GOAUTH` for private module authentication. `omitzero` JSON tag option. `weak` package |
| Language since 1.22 | Loop variables are per-iteration when `go.mod` says `go 1.22` or newer. `for i := range 10` ranges over an integer. Range over functions (iterators) since 1.23 with `iter.Seq`. `min`, `max`, `clear` since 1.21 |
| `go` vs `toolchain` | The `go` line is the minimum Go version needed to build the module and sets the language version. The optional `toolchain` line suggests a toolchain at least that new. A module's `go` line must be at least as new as every dependency's. `GOTOOLCHAIN=auto` (default) downloads a newer toolchain when `go` or `toolchain` demands it; `GOTOOLCHAIN=local` refuses instead. Change both with `go get go@1.27.3` rather than by hand |
| `tool` directive | `go get -tool golang.org/x/tools/cmd/stringer` records the tool in `go.mod` with a `require`; run it with `go tool stringer`. The `tool` meta-pattern lists all tools. This replaces the `tools.go` blank-import trick |
| Workspaces | `go work init ./a ./b` creates `go.work` with `use` directives; `GOWORK=off` disables it; `go env GOWORK` shows the file in use. `go mod tidy`, `go mod vendor` and `go get` always act on a single main module |
| Private modules | `GOPRIVATE` is a comma-separated list of glob prefixes and is the default for `GONOPROXY` and `GONOSUMDB`, so private paths skip the public proxy and checksum database. `GOINSECURE` allows plain HTTP for matching paths. Set with `go env -w GOPRIVATE=example.com/corp/*` |
| Errors | `fmt.Errorf("...: %w", err)` wraps; several `%w` verbs and `errors.Join` are allowed. `errors.Is` walks the chain for a value, `errors.As` or `errors.AsType` for a type. Wrapping is part of the API: wrap only what callers may inspect |
| Context | `WithCancel`, `WithTimeout`, `WithDeadline`; `WithCancelCause` and `context.Cause`; `WithoutCancel` keeps values but drops cancellation; `AfterFunc` runs a callback on cancel. First parameter, named `ctx`, never stored in a struct field |
| Concurrency | `errgroup.WithContext` plus `SetLimit` bounds fan-out; `TryGo` does not block. `sync.OnceFunc`, `OnceValue`, `OnceValues`. `atomic.Int64` and other typed atomics. A timer channel is unbuffered since 1.23 and unreferenced timers are collected |
| Generics | Constraints are interfaces with type sets (`~int \| ~string`), `comparable`, `cmp.Ordered`, `any`. Packages `slices`, `maps`, `cmp` and `iter` cover most needs |
| Testing | `go test -race`, `-shuffle=on`, `-count=N`, `-run`, `-bench`, `-benchmem`, `-cover`, `-fuzz=FuzzX -fuzztime=30s`. Failing fuzz inputs land in `testdata/fuzz/FuzzX/` and replay as regular tests. `t.Cleanup`, `t.TempDir`, `t.Setenv`, `t.Helper` |
| `ServeMux` | Pattern is `[METHOD ][HOST]/[PATH]` with `{name}`, `{name...}` and `{$}` wildcards. `GET` also matches `HEAD`. The most specific pattern wins; ambiguous registrations panic at startup. A path with no method match gets 405. Read wildcards with `r.PathValue("id")` and the matched pattern from `r.Pattern` |
| `http.Server` | Zero timeouts mean no timeouts. `ReadHeaderTimeout` is the one most deployments need first; it falls back to `ReadTimeout` when zero. `IdleTimeout` also falls back to `ReadTimeout`. `Shutdown(ctx)` stops listeners, closes idle connections, waits for active ones, and does not track hijacked connections such as WebSockets |
| `slog` | `slog.New(slog.NewJSONHandler(w, opts))`, `slog.SetDefault`, `Logger.With`, `slog.Group`, `LogAttrs`, `slog.LogValuer` for redaction, `HandlerOptions.ReplaceAttr`, `slog.DiscardHandler` for tests. Use the `*Context` methods so handlers can read the request context |
| Profiling | `go test -cpuprofile cpu.out -memprofile mem.out`, `go tool pprof -http=localhost:8081 cpu.out`. Importing `net/http/pprof` registers handlers on `http.DefaultServeMux` as a side effect |
| `govulncheck` | `go install golang.org/x/vuln/cmd/govulncheck@latest`, then `govulncheck ./...` for source or `govulncheck -mode binary ./bin/app` for a built binary. It reports only vulnerabilities whose affected symbols are reachable. Exit code is non-zero when findings exist, except with `-format sarif`, `-format openvex` or `-json` |

## 3. Workflow

1. Read `go.mod`: the `go` line, `toolchain` line, `tool` entries and `replace` directives. Run `go version` and `go env GOFLAGS GOPRIVATE GOWORK` to see what the build really uses.
2. Run `go build ./...`, `go vet ./...` and `go test ./...` before changing anything so existing failures are known.
3. Reproduce a bug with a failing test first. For concurrency bugs run `go test -race -count=20 ./pkg`.
4. Make the smallest change that follows the repository's style. Prefer the standard library; add a dependency only for a documented gap.
5. Format and analyze: `gofmt -l .` (or `go fmt ./...`), `go vet ./...`, and the linter the repository already uses.
6. For performance claims, write a benchmark, capture a profile, change one thing, and compare with `benchstat` when available.
7. Before release: `go mod tidy`, `govulncheck ./...`, and a build with `-trimpath` for reproducible paths.
8. Report which commands were run and their results.

## 4. Decision Rules

- If the module sets `go 1.22` or newer, do not add `v := v` loop-variable copies; if it sets an older version, keep them or raise the version deliberately.
- If a caller must branch on an error, export a sentinel (`var ErrNotFound = errors.New(...)`) for a condition or a pointer-receiver type for a condition that carries data. Otherwise return a wrapped, unexported error.
- If several goroutines each return an error and one failure should stop the rest, use `errgroup.WithContext`. If only waiting is needed and nothing can fail, `sync.WaitGroup` (with `Go` on 1.25+) is enough.
- If work is CPU-bound, size parallelism near `GOMAXPROCS`. If it is I/O-bound, bound it by the downstream limit with `errgroup.SetLimit`, not by CPU count.
- If state is shared, prefer confining it to one goroutine and passing messages. Use a mutex for small critical sections and caches, `atomic` types for single counters and flags, `sync.Map` only for the cases its documentation describes (stable keys, write once read many).
- If a function would take `any` and type-switch, consider an interface. If the same algorithm repeats for several concrete types with no behavior difference (containers, `Map`, `Filter`, `Max`), use generics. Do not make a type parameter just to avoid writing an interface.
- If an HTTP service needs routing by method and path variables only, use `net/http.ServeMux` rather than a router package; add a router when route groups, regex constraints or middleware chaining at that scale are required.
- If logging is new code, use `log/slog`. If the project uses another logger, keep it and bridge with an `slog.Handler` instead of mixing both styles.
- If a test touches the clock or sleeps to wait for goroutines, use `testing/synctest` (1.25+) instead of `time.Sleep`.
- If `go.mod` must reference private code, set `GOPRIVATE` for those prefixes and authenticate through the VCS credential helper, `.netrc`, or `GOAUTH`, never by embedding tokens in the module path or `go.mod`.

## 5. Coding Standards

- Format with `gofmt`; exported names have doc comments starting with the name; package names are short, lower case, singular, with no underscores and no stutter (`store.Store` is acceptable only when nothing shorter exists).
- Accept interfaces, return concrete types. Define an interface in the package that uses it, with the methods it needs and no more.
- Pass `context.Context` as the first parameter named `ctx`. Do not store it in a struct, except in a type whose job is to represent one request or operation.
- Return `error` as the last result. Check it immediately; do not log and return the same error at the same layer.
- Error strings are lower case with no trailing punctuation; wrap with context in the form `"verb noun: %w"`.
- No `panic` for expected failures. Use it for programmer errors and impossible states; recover only at a boundary such as an HTTP middleware or a goroutine root.
- Every goroutine has an owner, a way to stop (context or closed channel) and a way to be waited for.
- Only the sender closes a channel. Never close from the receiver or from several senders.
- Name receivers with one or two letters, consistent across a type. Use pointer receivers when the type has a mutex, is large, or mutates state; do not mix receiver kinds on one type.
- Do not use `init()` for work that can fail or has side effects other than registering; build dependencies in `main` and pass them in.
- Prefer `time.Duration` typed fields over integers with unit suffixes; prefer `errors.Is(err, io.EOF)` over `err == io.EOF` once errors can be wrapped.

## 6. Project Structure

```text
service/
├── go.mod                 # module path, go line, tool directives
├── go.sum
├── cmd/
│   └── api/main.go        # wiring only: config, logger, server, signals
├── internal/              # packages that must not be imported by other modules
│   ├── httpapi/           # handlers, middleware, routes
│   ├── store/             # persistence behind small interfaces
│   └── config/            # env parsing and validation
├── pkg/                   # only if other modules are meant to import it
└── testdata/              # fixtures; ignored by the go tool
```

- Keep `main` thin; business logic lives in packages that tests can call without starting a process.
- Start with a flat layout and split packages when a clear boundary appears. Avoid `utils`, `common` and `helpers` packages.
- A library module keeps the public API at the module root and hides the rest in `internal/`.

## 7. Design Patterns

- **Functional options** (`func WithTimeout(d time.Duration) Option`): constructors with many optional settings. Cost: more code than a config struct; use a plain struct when options are few.
- **Small interfaces at the consumer**: tests substitute a fake without a mocking framework. Cost: the same method set may be declared in more than one package.
- **Worker pool with `errgroup.SetLimit`**: bounded concurrency with first-error cancellation. Cost: results need an index or channel to be collected in order. See [references/concurrency.md](references/concurrency.md).
- **Pipeline stages joined by channels**: each stage owns its output channel and closes it. Cost: every stage needs `select` on `ctx.Done()` to avoid leaks.
- **Middleware as `func(http.Handler) http.Handler`**: logging, recovery, auth, limits. Cost: order matters; compose in one place.
- **Typed errors with `Unwrap`**: carry fields (operation, key) while keeping the cause reachable by `errors.Is`.
- **Table-driven tests with subtests**: one loop, many named cases. Cost: huge tables hide logic; split by behavior.
- **Iterators (`iter.Seq`)**: stream results without building a slice. Cost: harder to debug than a loop; keep for APIs that benefit.

## 8. Best Practices

- Wrap errors at package boundaries with what the function was doing, and keep the original error reachable with `%w`.
- Make zero values useful (`sync.Mutex`, `bytes.Buffer`); when a type needs a constructor, document it.
- Bound everything that comes from outside: request bodies (`http.MaxBytesReader`), response reads (`io.LimitReader`), header size, concurrency, and queue length.
- Set a timeout on every outbound call: `http.Client{Timeout: ...}` or a context deadline. The zero `http.Client` has none.
- Close what you open and check the interesting errors: `defer resp.Body.Close()` for clients; check `Close` on files you wrote.
- Prefer `t.Context()` (1.24+) in tests and `signal.NotifyContext` in `main` as roots of cancellation.
- Keep dependencies few and run `go mod tidy` in the same commit as the import change. Commit `go.sum`.
- Use build tags and `_test.go` files rather than runtime flags to separate integration tests (`//go:build integration`).
- Run `go fix ./...` (1.26+) on a clean tree to apply modernizers, review the diff, and run tests.
- Use `os.Root` (1.24+) when opening files named by untrusted input under a base directory.

## 9. Performance

- Measure first: `go test -bench . -benchmem -count=10`, then compare runs with `benchstat`. Use `for b.Loop() { ... }` (1.24+); since 1.26 it no longer blocks inlining in the loop body.
- Profile CPU with `go test -cpuprofile` or `/debug/pprof/profile?seconds=30`, allocations with `-memprofile` or `/debug/pprof/allocs`, contention with block and mutex profiles after setting `runtime.SetBlockProfileRate` and `runtime.SetMutexProfileFraction`.
- Reduce allocations in hot paths: preallocate (`make([]T, 0, n)`), reuse buffers, avoid converting between `string` and `[]byte` in loops, use `strings.Builder`. Reach for `sync.Pool` only when a profile shows allocation pressure from short-lived equal-sized objects.
- Keep a dependency-free struct layout in mind only after profiling shows cache effects; do not reorder fields by habit.
- Use `GOMEMLIMIT` as a soft memory cap in containers and leave `GOGC` at the default unless measurements say otherwise. With 1.25+, `GOMAXPROCS` already follows the container CPU limit; do not add a third-party library for it on those versions.
- Use `go tool trace` for scheduler latency, GC pauses and goroutine blocking; use `runtime/trace.FlightRecorder` (1.25+) to capture the moments before a rare slow event.
- Stop optimizing when the profile is flat or the gain is below noise. Prefer algorithm and I/O changes over micro-optimizations.

## 10. Security

- Never expose `net/http/pprof` on the public listener. Importing it for side effects registers handlers on `http.DefaultServeMux`; serve profiling from a separate server bound to `127.0.0.1` or an internal network, behind authentication, or register handlers explicitly on a private mux (see the example in [references/http-servers.md](references/http-servers.md)).
- Run `govulncheck ./...` in CI and on a schedule, because new advisories appear after a release. Update the Go toolchain too: standard library fixes ship in patch releases (1.27.x, 1.26.x).
- Use parameterized queries (`db.QueryContext(ctx, "SELECT ... WHERE id = $1", id)`); never build SQL with `fmt.Sprintf` or string concatenation.
- Do not disable TLS verification (`InsecureSkipVerify`). To trust a private CA, load it into `tls.Config.RootCAs`. Set `MinVersion: tls.VersionTLS12` or higher on servers you configure.
- Generate tokens and keys with `crypto/rand`, not `math/rand`. Compare secrets with `subtle.ConstantTimeCompare`.
- Treat file paths from users as hostile: use `os.Root` or `filepath.IsLocal` plus a fixed base directory; do not join user input into paths and open them directly.
- Read secrets from the environment or a secret store at start-up, never from source or `go.mod`. Do not log tokens, passwords or full request bodies; implement `slog.LogValuer` on types holding secrets.
- Cross-site request forgery for cookie-authenticated browsers: wrap handlers with `http.NewCrossOriginProtection().Handler(mux)` (1.25+) or use a CSRF token scheme.
- Set `http.Server` timeouts and body limits to resist slow-client and large-body attacks.
- Pin CI tools and use `go mod verify` to confirm cached modules match `go.sum`. Keep `GOFLAGS=-mod=mod` out of CI so a build cannot silently change `go.mod`.

## 11. Testing

- Unit tests sit next to the code in `_test.go` files; use the `pkg_test` package for black-box tests of exported behavior.
- Table-driven tests with `t.Run(tt.name, ...)`. Call `t.Parallel()` in the test and in each subtest only when cases share no mutable state. Since 1.22 the loop variable needs no copy.
- Cover failure paths: errors returned by fakes, canceled contexts, timeouts, empty and oversize input. Assert with `errors.Is` or `errors.AsType`, not on message text.
- Race detector: `go test -race ./...` in CI. It only finds races that actually execute, so combine it with `-count` and parallel tests.
- Fuzzing: write `func FuzzX(f *testing.F)`, seed with `f.Add`, run `go test -fuzz=FuzzX -fuzztime=30s ./pkg`. Commit minimized failures under `testdata/fuzz`. Fuzz parsers, decoders and anything taking untrusted bytes.
- Benchmarks: `func BenchmarkX(b *testing.B) { for b.Loop() { ... } }`; call `b.ReportAllocs()` or run with `-benchmem`.
- HTTP: `httptest.NewRecorder` with `httptest.NewRequestWithContext` for handlers, `httptest.NewServer` for clients. Test the whole `http.Handler` including middleware, not only inner functions.
- Concurrency and time: `testing/synctest` (1.25+) runs a function in a bubble with a fake clock; `synctest.Test(t, func(t *testing.T) {...})` and `synctest.Wait()` make timeout and retry tests instant and deterministic.
- Goroutine leaks: run tests with `-race`, check `runtime.NumGoroutine()` only in focused tests, and use the `goroutineleak` profile (generally available in 1.27) in staging to find blocked goroutines.
- `go test` also runs a small `go vet` subset by default; run full `go vet ./...` separately. Coverage: `go test -coverprofile=c.out ./... && go tool cover -func=c.out`.
- Commands: `go test ./...`, `go test -race -shuffle=on ./...`, `go test -run TestName -v ./pkg`, `go test -bench . -benchmem ./pkg`.

## 12. Review Checklist

- [ ] `go.mod` has a deliberate `go` line (and `toolchain` only when needed); `go mod tidy` leaves no diff.
- [ ] Every error is checked, wrapped with `%w` when callers may inspect it, and compared with `errors.Is` or `errors.As`.
- [ ] `ctx` is the first parameter, is passed down to I/O, and is not stored in a struct.
- [ ] Every goroutine has a stop condition and an owner that waits for it; no sends on unbuffered channels without a receiver or `ctx.Done()` case.
- [ ] Shared data is protected by a mutex, atomic or confinement; `go test -race` passes.
- [ ] `http.Server` sets `ReadHeaderTimeout` (and the other timeouts), request bodies are size-limited, and shutdown is graceful.
- [ ] `net/http/pprof` is not reachable from the public listener.
- [ ] No string-built SQL, no `InsecureSkipVerify`, no secrets in code or logs.
- [ ] New code has tests for success and failure paths; fuzz tests exist for untrusted-input parsers.
- [ ] `govulncheck ./...` is clean or each finding is justified; the Go patch version is current.
- [ ] Generics are used only where several concrete types share one algorithm.
- [ ] Logging uses `slog` with key-value attributes and the `*Context` methods.

## 13. Production Notes

- Build reproducibly: `CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o bin/api ./cmd/api` for a static binary. Packaging it into an image is covered by docker-expert.
- Handle `SIGTERM` with `signal.NotifyContext`, stop accepting work, call `Server.Shutdown` with a deadline shorter than the orchestrator's termination grace period, then close databases and flush logs. Since 1.26 `NotifyContext` cancels with a cause that names the signal (`context.Cause(ctx)`).
- Expose liveness and readiness endpoints that are cheap and do not depend on slow downstream calls (probe configuration belongs to kubernetes-expert).
- Log JSON to stdout with `slog.NewJSONHandler`; add request IDs as attributes. Metric and trace export is covered by observability-expert.
- Stay on a supported release: patch versions carry security fixes, and a release leaves support when the second newer major release ships. Plan upgrades by reading the release notes for runtime changes (GC, `GOMAXPROCS`, timers) and running `go fix`.
- Upgrades: run `go get go@1.27.3 && go mod tidy`, then the full test suite with `-race`. A GODEBUG setting removed in a new release is still accepted in `go.mod` or `//go:debug` from 1.27 only if set to its final default.
- Versioned libraries: tag semantic versions, keep `v2+` modules in a `/v2` path, and use `retract` in `go.mod` for broken releases.
- Enable profiling endpoints only on an internal port; capture a profile during an incident with `go tool pprof http://127.0.0.1:6060/debug/pprof/profile?seconds=30` through a port-forward or tunnel.

## 14. Examples

Sentinel and typed errors, extracted with `errors.Is` and `errors.AsType` (1.26+; use `errors.As` with a pointer variable on older versions):

```go
package store

import (
	"context"
	"errors"
	"fmt"
)

var ErrNotFound = errors.New("not found")

type ValidationError struct{ Field, Reason string }

func (e *ValidationError) Error() string { return e.Field + ": " + e.Reason }

type User struct{ ID, Name string }
type Store struct{ users map[string]User }

func (s *Store) Get(ctx context.Context, id string) (User, error) {
	if err := ctx.Err(); err != nil {
		return User{}, fmt.Errorf("get user %q: %w", id, err)
	}
	if id == "" {
		return User{}, &ValidationError{Field: "id", Reason: "must not be empty"}
	}
	u, ok := s.users[id]
	if !ok {
		return User{}, fmt.Errorf("get user %q: %w", id, ErrNotFound)
	}
	return u, nil
}

func status(err error) int {
	if _, ok := errors.AsType[*ValidationError](err); ok {
		return 400
	}
	if errors.Is(err, ErrNotFound) {
		return 404
	}
	return 500
}
```

A server with method-and-wildcard routing, explicit timeouts and graceful shutdown on `SIGTERM`:

```go
package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	if err := run(logger); err != nil {
		logger.Error("server stopped", "err", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("GET /users/{id}", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "user %s\n", r.PathValue("id"))
	})

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           http.MaxBytesHandler(mux, 1<<20),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	errc := make(chan error, 1)
	go func() { errc <- srv.ListenAndServe() }()
	logger.Info("listening", "addr", srv.Addr)

	select {
	case err := <-errc:
		return err
	case <-ctx.Done():
		stop() // a second signal now terminates the process
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("graceful shutdown: %w", err)
	}
	return nil
}
```

A table-driven parallel test, a fuzz target and a benchmark for one function:

```go
package parse

import "testing"

func TestPort(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		in      string
		want    int
		wantErr bool
	}{
		{name: "ok", in: "localhost:8080", want: 8080},
		{name: "no port", in: "localhost", wantErr: true},
		{name: "out of range", in: "h:70000", wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := Port(tt.in)
			if (err != nil) != tt.wantErr || got != tt.want {
				t.Fatalf("Port(%q) = %d, %v; want %d, wantErr=%v", tt.in, got, err, tt.want, tt.wantErr)
			}
		})
	}
}

func FuzzPort(f *testing.F) {
	f.Add("localhost:8080")
	f.Fuzz(func(t *testing.T, s string) {
		if n, err := Port(s); err == nil && (n < 1 || n > 65535) {
			t.Fatalf("Port(%q) = %d without error", s, n)
		}
	})
}

func BenchmarkPort(b *testing.B) {
	for b.Loop() {
		Port("localhost:8080")
	}
}
```

## 15. Common Mistakes

- **Unbounded `http.Server{}`**: no timeouts lets slow clients hold connections open forever. Set `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout` and `IdleTimeout`.
- **`http.ListenAndServe` and `http.Get` in production code**: both use defaults with no timeouts. Build an explicit `http.Server` and `http.Client`.
- **Pprof on the public mux**: `import _ "net/http/pprof"` plus serving `DefaultServeMux` publicly exposes heap and goroutine dumps. Use a private listener.
- **Goroutine leak on early return**: workers send on an unbuffered channel nobody reads after an error. Use `errgroup` with a derived context, buffer the channel to the worker count, or select on `ctx.Done()`.
- **Closing a channel from the receiver or twice**: panics. The single sender closes; use `sync.Once` or restructure when several producers exist.
- **`sync.WaitGroup.Add` inside the goroutine**: races with `Wait`. Call `Add` before `go`, or use `wg.Go` (1.25+); vet's `waitgroup` analyzer reports the misplaced call.
- **Copying a mutex or struct containing one**: the copy has independent state. Pass pointers; `go vet` copylocks reports it.
- **Storing `context.Context` in a struct**: lifetimes become unclear and cancellation is lost. Pass `ctx` per call.
- **Using `context.Background()` inside a handler**: drops client cancellation and deadlines. Use `r.Context()`; use `context.WithoutCancel(r.Context())` for work that must outlive the request.
- **Comparing errors with `==` or by string**: breaks as soon as a layer wraps. Use `errors.Is` and `errors.As`.
- **Wrapping with `%v` instead of `%w`**: the cause is lost to `errors.Is`. Use `%w` where callers may inspect it.
- **Returning a typed nil pointer as `error`**: `var e *MyErr; return e` is a non-nil interface. Return a literal `nil`.
- **Wrapping `*E` with `%w` where `E` implements `error`**: type assertions and `errors.Is` fail on it, and vet reports it from Go 1.27.
- **`defer` in a long loop**: deferred calls run at function exit and pile up. Wrap the body in a function or close explicitly.
- **Ignoring the `go` line when upgrading dependencies**: `go get` may raise it and force a newer toolchain. Review `git diff go.mod` and pin with `go get go@1.26.10` if needed.
- **`tools.go` blank imports on Go 1.24+**: use `tool` directives and `go tool` instead.
- **Over-generic code**: a type parameter on every function hides intent. Start concrete and generalize when a second type appears.
- **`time.After` in a hot `select` loop on old modules**: before 1.23 unreferenced timers were not collected until they fired. Use `time.NewTimer` with `Reset` and `Stop` when targeting older `go` lines.
- **Reading an unbounded body**: `io.ReadAll(r.Body)` on untrusted input exhausts memory. Wrap with `http.MaxBytesReader` or `io.LimitReader`.

## 16. References

- [references/concurrency.md](references/concurrency.md): goroutine ownership, errgroup fan-out, pipelines, worker pools, mutex and atomic use, leak patterns and the leak profile, context cancellation causes.
- [references/http-servers.md](references/http-servers.md): ServeMux pattern rules and precedence, middleware, request limits, timeouts, graceful shutdown details, private pprof server, client configuration, slog setup for services.
- [references/testing-profiling.md](references/testing-profiling.md): test layout, fuzzing workflow, race detector, benchmarks with `b.Loop`, `testing/synctest`, pprof and trace workflows, govulncheck in CI.
- Official: [Go release notes](https://go.dev/doc/devel/release), [Go 1.27 notes](https://go.dev/doc/go1.27), [Go 1.26 notes](https://go.dev/doc/go1.26), [Go modules reference](https://go.dev/ref/mod), [toolchains](https://go.dev/doc/toolchain), [net/http](https://pkg.go.dev/net/http), [log/slog](https://pkg.go.dev/log/slog), [testing](https://pkg.go.dev/testing), [errgroup](https://pkg.go.dev/golang.org/x/sync/errgroup), [govulncheck](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck), [Effective Go](https://go.dev/doc/effective_go).
