# Go Testing, Profiling and Vulnerability Scanning

Reference for the `testing` package workflows, fuzzing, the race detector, deterministic concurrency tests, benchmarks, pprof and trace, and `govulncheck`. Verified against Go 1.27.3 and 1.26.10, govulncheck v1.9.0 (2026-10).

## Contents

1. [Test layout and helpers](#1-test-layout-and-helpers)
2. [Fuzzing](#2-fuzzing)
3. [Race detector](#3-race-detector)
4. [Deterministic concurrency tests](#4-deterministic-concurrency-tests)
5. [Benchmarks](#5-benchmarks)
6. [Profiling with pprof](#6-profiling-with-pprof)
7. [Execution traces](#7-execution-traces)
8. [govulncheck](#8-govulncheck)
9. [CI command set](#9-ci-command-set)

## 1. Test layout and helpers

- Test files end in `_test.go`; test functions are `func TestXxx(t *testing.T)`. Use package `foo_test` for black-box tests and package `foo` when internals need coverage.
- Fixtures live in `testdata/`, which the go tool ignores when building. Golden files can be compared with an `-update` flag declared in the test package.
- Helpers call `t.Helper()` so failures point at the caller. Use `t.Cleanup` for teardown, `t.TempDir()` for scratch directories, `t.Setenv` for environment (it forbids `t.Parallel` in that test).
- `t.Context()` (Go 1.24+) returns a context canceled just before cleanup functions run; pass it to code under test instead of `context.Background()`.
- `t.ArtifactDir()` (Go 1.26+) returns a directory for output files; they are kept under the `-outputdir` directory when `go test -artifacts` is passed, and removed otherwise.
- Assert errors with `errors.Is`, `errors.AsType[T]` (1.26+) or `errors.As`, never on message strings.
- `t.Parallel()` pauses a test until its serial siblings finish, then runs it with other parallel tests, bounded by `-parallel` (default `GOMAXPROCS`). Parallel subtests resume only after the parent test function body returns, which matters for shared setup and `defer`.
- Use small fakes written against the consumer's interface. For HTTP clients, `httptest.NewServer`; for handlers, `httptest.NewRecorder` with `httptest.NewRequestWithContext`; to build a request with path wildcards set `req.SetPathValue("id", "42")` when calling a handler directly (routing through the real mux is better).
- Flags: `-run 'TestName/subcase'`, `-v`, `-count=1` (disable cache), `-shuffle=on`, `-failfast`, `-timeout 60s`, `-short` with `testing.Short()` to skip slow tests, `-cover`, `-coverprofile`.
- `go test -json` emits machine-readable events; from Go 1.27 output events carry an optional `OutputType` field.
- `go test` runs a vet subset first; Go 1.27 adds the `stdversion` check, which flags standard library symbols newer than the `go` line in `go.mod`. If it fires, either raise the `go` line deliberately or avoid the symbol.

## 2. Fuzzing

Fuzzing generates inputs to find panics, hangs and broken invariants. Good targets are parsers, decoders and round-trip functions.

```go
func FuzzRoundTrip(f *testing.F) {
	f.Add("hello")                  // seed corpus
	f.Add("")
	f.Fuzz(func(t *testing.T, s string) { // parameters: supported basic types and []byte
		enc := Encode(s)
		dec, err := Decode(enc)
		if err != nil || dec != s {
			t.Fatalf("round trip of %q gave %q, %v", s, dec, err)
		}
	})
}
```

- Run: `go test -fuzz=FuzzRoundTrip -fuzztime=30s ./pkg` (one fuzz target per run; `-fuzz` takes a regular expression that must match exactly one). Without `-fuzz`, `go test` runs only the seed corpus and saved failures.
- A failing input is written to `testdata/fuzz/FuzzRoundTrip/<hash>`. Commit that file with the fix; it then runs as a regression test on every `go test`.
- The generated cache of interesting inputs lives under the user cache directory (`go env GOCACHE`), not in the repository.
- Check properties, not exact outputs: no panic, decode(encode(x)) equals x, output stays within limits, two implementations agree.
- Keep the target fast and deterministic: no network, no global mutable state, no unbounded loops on input size.
- In CI run a short time-boxed fuzz job (for example 30 to 60 seconds per target) and run longer sessions on a schedule.

## 3. Race detector

- `go test -race ./...` and `go run -race`, `go build -race` enable it. It reports data races that occur during the execution, with the stacks of both accesses, and exits with a failure.
- It slows execution and uses more memory, so use it in tests, load tests and canary builds. See the Go race detector article for current overhead figures.
- Races that need rare interleavings appear with more work: `-count=20`, `-cpu 1,2,4`, `t.Parallel()` and stress loops in the test.
- Typical fixes: guard with `sync.Mutex`, use `atomic` types, confine data to one goroutine, or hand off ownership through a channel. Copying data to avoid sharing is also valid.

## 4. Deterministic concurrency tests

`testing/synctest` (generally available since Go 1.25) runs a test in a bubble with a fake clock. Time advances instantly when every goroutine in the bubble is durably blocked, so retries, timeouts and tickers need no real sleeping.

```go
package fetch

import (
	"testing"
	"testing/synctest"
	"time"
)

func TestDelayedClose(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		done := make(chan struct{})
		go func() {
			time.Sleep(time.Hour) // fake time: returns immediately in real time
			close(done)
		}()

		synctest.Wait() // all goroutines in the bubble are blocked
		select {
		case <-done:
			t.Fatal("closed too early")
		default:
		}

		time.Sleep(time.Hour)
		synctest.Wait()
		select {
		case <-done:
		default:
			t.Fatal("not closed after an hour")
		}
	})
}
```

- Durably blocking operations are: send, receive or `select` on channels created inside the bubble, `sync.Cond.Wait`, `sync.WaitGroup.Wait` (when `Add` ran inside the bubble) and `time.Sleep`. Locking a mutex, network or file I/O and system calls are not, because something outside the bubble can unblock them. The fake clock starts at midnight UTC 2000-01-01, and `Test` panics if every goroutine is blocked with nothing to wake it (a deadlock).
- Go 1.27 adds `synctest.Sleep` (sleep plus `Wait`) and `httptest.NewTestServer`, an in-memory server suited to bubbles.
- Keep each test self-contained: avoid the real network (use `net.Pipe` or an in-memory server), external processes and goroutines started outside the bubble.

## 5. Benchmarks

```go
func BenchmarkParse(b *testing.B) {
	data := loadFixture(b)   // setup runs once, outside the timed loop
	for b.Loop() {           // Go 1.24+
		if _, err := Parse(data); err != nil {
			b.Fatal(err)
		}
	}
}
```

- `b.Loop()` runs the setup before the loop once, times only the loop, and keeps the values of calls inside the loop alive so the compiler cannot delete the work. Since Go 1.26 it also no longer blocks inlining of the loop body. The older `for range b.N` form still works.
- Run: `go test -run '^$' -bench . -benchmem -count=10 ./pkg > new.txt`. Compare two runs with `benchstat old.txt new.txt` (`go install golang.org/x/perf/cmd/benchstat@latest`).
- `-cpuprofile`, `-memprofile`, `-blockprofile` and `-mutexprofile` write profiles for the benchmark; analyze with `go tool pprof`.
- Keep the machine quiet, pin the Go version, and treat differences inside the reported variance as noise.
- Add `b.ReportAllocs()` or `-benchmem` to see allocations per operation, which is often the first lever in Go performance work.

## 6. Profiling with pprof

Collect:

```text
go test -run '^$' -bench BenchmarkParse -cpuprofile cpu.out -memprofile mem.out ./pkg
go tool pprof -http=localhost:8081 cpu.out
```

- From a running service with the private debug server of [http-servers.md](http-servers.md): `go tool pprof 'http://127.0.0.1:6060/debug/pprof/profile?seconds=30'` for CPU, `.../heap` for live memory, `.../allocs` for cumulative allocations, `.../goroutine` for stacks, `.../block` and `.../mutex` after enabling `runtime.SetBlockProfileRate` and `runtime.SetMutexProfileFraction`, and `.../goroutineleak` on Go 1.27.
- In the web UI (flame graph by default since Go 1.26) look for wide frames; switch to Graph via View. Text views: `top`, `top -cum`, `list FuncName`, `peek`.
- Heap sample types: `-sample_index=inuse_space` (live bytes), `alloc_space` (total bytes), `alloc_objects` (allocation count). High `alloc_space` with low `inuse_space` means churn rather than a leak.
- Compare profiles from before and after a change with `go tool pprof -diff_base before.out after.out`.
- Profile-guided optimization: a `default.pgo` CPU profile placed in the main package directory is picked up automatically by `go build` (`-pgo=auto` is the default). Collect it from production traffic, refresh it periodically, and measure the gain.
- Leaks: a steadily growing goroutine count suggests blocked goroutines; compare two `goroutine?debug=1` snapshots, or use the leak profile on 1.27.
- GC and memory: `GODEBUG=gctrace=1` prints one line per cycle; `runtime/metrics` and `runtime.ReadMemStats` expose counters. The Green Tea collector is the default since Go 1.26; the 1.26 notes list `GOEXPERIMENT=nogreenteagc` as a temporary opt-out expected to go away in 1.27, so check the current release notes before relying on it.

## 7. Execution traces

- Capture: `go test -trace trace.out ./pkg`, or `curl -o trace.out 'http://127.0.0.1:6060/debug/pprof/trace?seconds=5'`, or `runtime/trace.Start` in code. View with `go tool trace trace.out`.
- A trace shows goroutine scheduling, blocking on channels and locks, GC phases and syscalls. Use it when a profile shows low CPU but high latency.
- `go tool trace -http=:6060` now binds to localhost when only a port is given (Go 1.27); pass `-http=0.0.0.0:6060` only when you mean to expose it.
- `runtime/trace.FlightRecorder` (Go 1.25+) keeps a rolling in-memory window of recent trace data and writes it out on demand, for example when a request exceeds its latency budget. See the package documentation for the configuration type.
- User annotations (`trace.NewTask`, `trace.WithRegion`, `trace.Log`) label application phases so they show up in the viewer.

## 8. govulncheck

- Install: `go install golang.org/x/vuln/cmd/govulncheck@latest`. Run from the module root: `govulncheck ./...`.
- It analyzes source or a binary and reports only vulnerabilities in code your program can reach, using the Go vulnerability database at `vuln.go.dev`. Requests send module paths already known to the database, not your source code.
- Binaries: `govulncheck -mode binary ./bin/api`. Output omits call stacks. For source scans, `-show traces` prints full call stacks and `-show verbose` adds progress detail. `-test` includes test files and `-tags` selects build tags.
- Exit status is non-zero when vulnerabilities are found, except for `-json`, `-format sarif` and `-format openvex`, which exit zero so CI can upload the report and decide separately. SARIF output feeds code-scanning dashboards.
- Results depend on the Go version of the `go` command on PATH, since standard library vulnerabilities are fixed in patch releases. Update the toolchain together with module requirements.
- Fixing: `go get example.com/dep@fixedVersion && go mod tidy`, then rerun. If no fixed version exists, check whether the vulnerable symbol is really reachable, mitigate at the call site, or replace the dependency.
- Limits: calls through `reflect` are invisible to the source analysis, interface calls are handled conservatively (possible false positives), and there is currently no built-in way to silence a finding. Keep a written justification in the review instead.

## 9. CI command set

```text
go mod tidy && git diff --exit-code go.mod go.sum
gofmt -l . | (! grep .)
go vet ./...
go test -race -shuffle=on -count=1 ./...
go test -run '^$' -fuzz=FuzzRoundTrip -fuzztime=30s ./pkg
govulncheck ./...
go build -trimpath ./...
```

- Cache the Go build and module caches (`go env GOCACHE GOMODCACHE`) between CI runs.
- Run the fuzz line per fuzz target; each `-fuzz` invocation accepts exactly one match.
- Pin the toolchain with the `go` and `toolchain` lines in `go.mod` so CI and developers agree; set `GOTOOLCHAIN=local` in locked-down CI when downloads are not permitted.
