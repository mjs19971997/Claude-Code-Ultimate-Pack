# Go Concurrency

Reference for goroutine lifecycle, channels, `sync`, `errgroup` and `context`. Verified against Go 1.27.3 and 1.26.10 and golang.org/x/sync v0.24.0 (2026-10); the Go version that introduced each feature is noted where it matters.

## Contents

1. [Ownership rules](#1-ownership-rules)
2. [errgroup fan-out](#2-errgroup-fan-out)
3. [Pipelines and worker pools](#3-pipelines-and-worker-pools)
4. [Shared state](#4-shared-state)
5. [Context details](#5-context-details)
6. [Finding leaks and races](#6-finding-leaks-and-races)

## 1. Ownership rules

- Start a goroutine only when you know how it ends. Each one needs a stop signal (a canceled `context.Context` or a closed channel) and someone who waits for it (`WaitGroup`, `errgroup`, or a done channel).
- The sender owns a channel and closes it; receivers use `for v := range ch` or `v, ok := <-ch`. Closing signals "no more values", not "stop sending"; to stop senders, cancel a context.
- A send or receive on a nil channel blocks forever. This is useful inside `select` to disable a case, and a bug elsewhere.
- Unbuffered channels synchronize; buffered channels decouple. Pick a buffer size for a reason (number of workers, known batch) and not to hide a deadlock.
- Do not start goroutines in `init()` or package-level variable initializers; start them from `main` or a constructor that returns a `Close` or `Run(ctx)` method.
- Prefer `Run(ctx context.Context) error` for long-lived components: it blocks until the context ends and returns the final error, which composes with `errgroup`.
- Since Go 1.22 each iteration has its own loop variable (for modules whose `go` line is 1.22 or newer), so `go func() { use(v) }()` inside a `for` loop is safe. Older modules still need `v := v`.

## 2. errgroup fan-out

`golang.org/x/sync/errgroup` runs functions in goroutines, returns the first non-nil error from `Wait`, and cancels the derived context on the first error. Its methods: `WithContext`, `Go`, `TryGo`, `SetLimit`, `Wait`. `SetLimit` must be called before any goroutine starts, and `Go` blocks once the limit is reached.

```go
package fetch

import (
	"context"
	"fmt"
	"io"
	"net/http"

	"golang.org/x/sync/errgroup"
)

// All fetches every URL with at most limit requests in flight.
// The first error cancels the remaining work and is returned.
func All(ctx context.Context, client *http.Client, urls []string, limit int) ([][]byte, error) {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(limit)

	bodies := make([][]byte, len(urls)) // each goroutine writes only its own index
	for i, u := range urls {
		g.Go(func() error {
			req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
			if err != nil {
				return fmt.Errorf("build request %q: %w", u, err)
			}
			resp, err := client.Do(req)
			if err != nil {
				return fmt.Errorf("fetch %q: %w", u, err)
			}
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusOK {
				return fmt.Errorf("fetch %q: status %d", u, resp.StatusCode)
			}
			b, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			if err != nil {
				return fmt.Errorf("read %q: %w", u, err)
			}
			bodies[i] = b
			return nil
		})
	}
	if err := g.Wait(); err != nil {
		return nil, err
	}
	return bodies, nil
}
```

Notes:

- Writing to distinct slice indexes from different goroutines is race-free; appending to a shared slice is not. Collect with indexes, a mutex, or a channel.
- Only the first error is returned. When every failure matters, collect them with a mutex-guarded slice and `errors.Join`.
- Do not reuse a `Group` for a second batch of work after `Wait`; make a new one.
- For work that must keep going when a sibling fails, use a plain `errgroup.Group{}` (no derived context) and handle errors inside each function.
- `TryGo` returns false instead of blocking when the limit is reached, which suits load shedding.

For goroutines that cannot fail, `sync.WaitGroup` is enough. On Go 1.25 and newer, `wg.Go(func() { ... })` replaces the `Add(1)` / `go` / `defer Done()` triple, and the vet `waitgroup` analyzer reports `Add` calls placed inside the goroutine.

## 3. Pipelines and worker pools

Every stage selects on `ctx.Done()` when sending, so canceling the context unblocks the whole chain.

```go
package conc

import (
	"context"
	"sync"
)

// Generate sends 0..n-1 until ctx is canceled, then closes the channel.
func Generate(ctx context.Context, n int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for i := range n {
			select {
			case out <- i:
			case <-ctx.Done():
				return
			}
		}
	}()
	return out
}

// Square starts workers goroutines; out is closed after all of them finish.
func Square(ctx context.Context, in <-chan int, workers int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup
	for range workers {
		wg.Go(func() { // Go 1.25+; use wg.Add(1) and go func() { defer wg.Done() ... } before
			for v := range in {
				select {
				case out <- v * v:
				case <-ctx.Done():
					return
				}
			}
		})
	}
	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}
```

- The consumer must either drain the output channel or cancel the context. Returning early without canceling leaves the producers blocked on their sends, which is the classic leak.
- Results arrive in completion order. If order matters, carry an index in the value and sort, or write into a pre-sized slice.
- A bounded worker pool is usually `errgroup` with `SetLimit` over a slice of items; reserve long-lived pools with a jobs channel for cases where workers hold expensive state (a connection, a parser).
- Fan-in of many channels: one goroutine per input forwarding to a shared output, closed after a `WaitGroup` completes.
- Timeouts in `select`: use `context.WithTimeout` for the whole operation; use `time.NewTimer` with `Stop` when a loop needs a per-iteration timeout. Since Go 1.23, unreferenced timers and tickers are garbage collected and timer channels are unbuffered, so `Stop` and `Reset` no longer leave stale values (for modules with `go 1.23` or newer).

## 4. Shared state

- Mutex: guard a map or struct with `sync.Mutex` or `sync.RWMutex` held for the shortest possible time; document which fields it protects and keep them together in the struct. Never copy a value containing a mutex.

```go
package conc

import "sync"

type Cache struct {
	mu sync.RWMutex // guards m
	m  map[string]string
}

func NewCache() *Cache { return &Cache{m: make(map[string]string)} }

func (c *Cache) Get(k string) (string, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok := c.m[k]
	return v, ok
}

func (c *Cache) Set(k, v string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.m[k] = v
}
```

- Atomics: `atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]` are typed and preferred over the function forms. Use them for counters, flags and swapping an immutable config snapshot.
- One-time initialization: `sync.OnceFunc`, `sync.OnceValue` and `sync.OnceValues` return a function that runs once and caches results, including a panic.

```go
var loadConfig = sync.OnceValues(func() (map[string]string, error) {
	return map[string]string{"mode": "prod"}, nil
})
```

- `sync.Map` fits two patterns: keys written once and read many times, and goroutines touching disjoint keys. Otherwise a plain map with a mutex is clearer and type-safe.
- `sync.Pool` is a cache of temporary objects the garbage collector may drop. Reset objects before `Put`, never keep references to a pooled object after returning it, and add it only after a profile shows allocation cost.
- `sync.Cond` is rarely needed; a channel or `context` is simpler. If you use it, wait in a loop that rechecks the condition.
- Lock ordering: acquire multiple locks in one global order and never call unknown code (callbacks, interface methods) while holding a lock.

## 5. Context details

- Create roots in `main` or at the edge: `signal.NotifyContext` for a process, `r.Context()` for a request, `t.Context()` for a test (Go 1.24+). Derive children with `WithCancel`, `WithTimeout` or `WithDeadline` and always `defer cancel()`; `go vet` reports a missing cancel (`lostcancel`).
- `context.WithTimeoutCause`, `WithDeadlineCause` and `WithCancelCause` attach a reason that `context.Cause(ctx)` returns, while `ctx.Err()` stays `Canceled` or `DeadlineExceeded`. Since Go 1.26, `signal.NotifyContext` cancels with a cause naming the received signal.
- Wrap both: `fmt.Errorf("call: %w (cause: %w)", err, context.Cause(ctx))` keeps `errors.Is(err, context.DeadlineExceeded)` and `errors.Is(err, ErrBudget)` true. Multiple `%w` verbs have been allowed since Go 1.20.
- `context.WithoutCancel(parent)` keeps values (trace IDs, logger) but drops cancellation and deadline: use it for cleanup or audit work that must finish after the request ends, with its own timeout.
- `context.AfterFunc(ctx, f)` runs `f` in its own goroutine after the context ends and returns a `stop` function; it is the clean way to unblock a non-context-aware API such as closing a connection.
- Context values are for request-scoped data crossing API boundaries (request ID, auth principal), never for optional parameters. Use unexported key types (`type ctxKey struct{}`) to avoid collisions.
- Respect cancellation in loops: check `ctx.Err()` between units of work, or select on `ctx.Done()` around blocking calls. Library calls that accept a `ctx` (`db.QueryContext`, `http.NewRequestWithContext`) must receive it.
- In handlers, derive from `r.Context()`; it is canceled when the client disconnects or the server shuts the connection down.

## 6. Finding leaks and races

- Race detector: `go test -race ./...` and `go build -race` for staging binaries. It adds memory and CPU overhead (see the Go race detector docs for current figures), so use it in tests and canary environments, not on all production traffic.
- Leak symptoms: growing `runtime.NumGoroutine()`, rising memory, `/debug/pprof/goroutine?debug=2` showing many goroutines parked at the same `chan send`, `chan receive` or `sync.(*Mutex).Lock` line.
- Leak profile: a `goroutineleak` profile reports goroutines blocked on a primitive that can no longer be unblocked. It was experimental in Go 1.26 (`GOEXPERIMENT=goroutineleakprofile`) and is generally available in Go 1.27 through `runtime/pprof` and the `/debug/pprof/goroutineleak` endpoint. Detection relies on reachability, so leaks through globals or live goroutines' locals may go unreported.
- The typical leak: an unbuffered channel, N workers, and an early `return` on the first error. Fix by canceling a context the workers select on, by sizing the channel to N, or by using `errgroup`.
- Deadlock hunting: send `SIGQUIT` to get all goroutine stacks, or set `GOTRACEBACK=all`. The runtime reports "all goroutines are asleep" only when every goroutine is blocked, so partial deadlocks need the stacks.
- Deterministic concurrency tests use `testing/synctest` (generally available in 1.25): inside `synctest.Test`, `time` is a fake clock that advances when all goroutines in the bubble block, and `synctest.Wait()` returns when they are all idle. See [testing-profiling.md](testing-profiling.md).
- Static checks: `go vet` covers copylocks, loopclosure on old modules, lostcancel and, from 1.25, `waitgroup`. Run it in CI.
