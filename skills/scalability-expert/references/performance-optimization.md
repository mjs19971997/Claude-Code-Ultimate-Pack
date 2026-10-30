# Performance Optimization

Reference absorbed from the former performance-optimization-expert skill: methodology, resource and service analysis, profiling by runtime, flame graphs, common bottlenecks and benchmarking pitfalls. Verified against Brendan Gregg's USE method and flame graph documentation, Tom Wilkie's RED method, the Go 1.24 `net/http/pprof` and `testing` packages, Node.js 22 `--cpu-prof`, py-spy, async-profiler 3.x, JDK Flight Recorder, Linux `perf` and PostgreSQL `EXPLAIN` (2026-10). Command output formats differ between versions, so check `--help` on the installed tool.

## 1. Method

Work as an experiment loop and stop when the goal is met:

1. Define the goal: percentile latency, throughput, error rate, cost, at a stated load.
2. Reproduce with a repeatable workload (see [load-testing.md](load-testing.md)). Record a baseline: histograms, throughput, resource use.
3. Find the limiting resource (section 2), then the code or query using it (sections 3-5).
4. Form one hypothesis, predict the effect size, change one thing.
5. Re-measure under identical conditions. Keep the change only if it moves the target metric beyond noise.
6. Repeat until the next improvement is not worth its complexity. Write down the result and the remaining ceiling.

Amdahl's reminder: improving a component that takes 10% of the time can gain at most 10%. Spend effort on the largest share first, and note that removing a bottleneck exposes the next one.

## 2. Finding the bottleneck: USE and RED

USE (for resources): for each of CPU, memory, storage devices, network interfaces, and software resources such as thread pools, connection pools and locks, check Utilization (time busy), Saturation (queued or waiting work), and Errors.

RED (for services): per service and endpoint, Rate (requests per second), Errors (failed per second or ratio), Duration (latency distribution). Combine with the four golden signals by adding saturation.

Typical Linux first-minute checks (read-only):

```bash
uptime                 # load averages: runnable + uninterruptible tasks
vmstat 1               # r (runnable), si/so (swap), cs, us/sy/id/wa
mpstat -P ALL 1        # per-CPU balance; one hot CPU suggests a serial bottleneck
pidstat 1              # per-process CPU, per-thread with -t
iostat -xz 1           # r_await/w_await, aqu-sz (saturation), %util
free -m                # memory, cache, swap
ss -s                  # socket summary; many TIME-WAIT or SYN backlog issues
sar -n DEV 1           # network throughput per interface
dmesg -T | tail        # OOM kills, disk errors, throttling
```

Reading the signals:

| Observation | Likely cause |
|---|---|
| High user CPU, low iowait | CPU-bound code; profile CPU |
| High system CPU | Syscalls, context switching, network stack, many small I/Os |
| Low CPU, high latency | Waiting on locks, I/O, downstream calls, or pool exhaustion; look at traces and wait stacks |
| High iowait, high disk await | Storage saturation or too little page cache; check queries, indexes, IOPS limits |
| Rising memory, GC time up | Allocation pressure or a leak; take heap profiles |
| Latency spikes at regular intervals | GC pauses, cron jobs, checkpoints, log rotation, TLS session or DNS expiry |
| Throughput flat while load grows | Saturated resource, lock contention, or a limit (pool size, rate limit) |
| Throughput falls as load grows | Contention or coherency cost (USL beta term), thrashing, retry storms |

Also check container limits: CPU throttling (`cpu.stat` `nr_throttled`), memory limits near the working set, file descriptor and ephemeral port limits.

## 3. Profiling by runtime

Use a sampling profiler on a representative workload; start with CPU, then allocation, then wait (off-CPU) profiles. Profile with production build flags and realistic data.

Go (standard library `net/http/pprof`; keep the profiling server off public interfaces):

```go
package main

import (
	"log"
	"net/http"
	"net/http/pprof"
)

func startPprof() {
	mux := http.NewServeMux()
	mux.HandleFunc("/debug/pprof/", pprof.Index)
	mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
	mux.HandleFunc("/debug/pprof/trace", pprof.Trace)
	mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
	go func() {
		// Loopback only: reach it with kubectl port-forward or an SSH tunnel.
		srv := &http.Server{Addr: "127.0.0.1:6060", Handler: mux}
		log.Println(srv.ListenAndServe())
	}()
}

func main() {
	startPprof()
	select {}
}
```

Then run `go tool pprof -http=:8081 'http://127.0.0.1:6060/debug/pprof/profile?seconds=30'` for CPU, and `/debug/pprof/heap`, `/debug/pprof/allocs`, `/debug/pprof/goroutine?debug=2`, `/debug/pprof/mutex` and `/debug/pprof/block` (enable with `runtime.SetMutexProfileFraction` and `runtime.SetBlockProfileRate`) for the rest. For benchmarks: `go test -bench . -benchmem -count 10 -cpuprofile cpu.out`, compare runs with `benchstat`.

Node.js:

- `node --cpu-prof --cpu-prof-dir=./prof app.js` writes `.cpuprofile` files that open in Chrome DevTools (Performance, Load profile) or other viewers; `--heap-prof` writes allocation profiles.
- Event loop health: `perf_hooks.monitorEventLoopDelay()` reports delay histograms; sustained p99 delay above tens of milliseconds means synchronous work is blocking the loop.
- Common causes: large `JSON.parse`/`stringify`, synchronous crypto, regex backtracking, big loops in handlers, per-request template compilation. Move CPU work to `worker_threads` or a job queue.

Python:

- `py-spy top --pid <pid>` and `py-spy record -o flame.svg --pid <pid> --duration 30` sample a running process without code changes (may need ptrace permission).
- `cProfile` plus a viewer for development; `tracemalloc` for allocation sources.
- The GIL limits CPU-bound threads; use processes, native extensions, or async I/O for I/O-bound concurrency.

JVM:

- JDK Flight Recorder: `java -XX:StartFlightRecording=duration=60s,filename=rec.jfr ...` or `jcmd <pid> JFR.start duration=60s filename=rec.jfr`, then inspect in JDK Mission Control.
- async-profiler (`asprof -d 30 -e cpu -f flame.html <pid>`, also `-e alloc` and `-e lock`) yields low-bias flame graphs including native frames.
- GC: read GC logs (`-Xlog:gc*`) before tuning; reduce allocation rate first; pick the collector for the goal (low pause versus throughput).

Native and system-wide (Linux `perf`):

```bash
# CPU flame graph, 99 Hz sampling, call graphs, 30 s, one process
perf record -F 99 -g -p <pid> -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg
```

`stackcollapse-perf.pl` and `flamegraph.pl` come from the FlameGraph repository. Native code needs frame pointers (or `--call-graph dwarf`) for good stacks; interpreted runtimes may need a perf map or their own profiler. eBPF tools (bpftrace, BCC) provide off-CPU and latency histograms with low overhead; they need privileges and a matching kernel.

Databases: see section 5.

## 4. Reading flame graphs

- The x-axis is the share of samples (not time order); width is cost. The y-axis is stack depth; the top edge is where CPU was spent.
- Look for wide plateaus at the top: that function (not its callers) burns the cycles.
- Compare two graphs with a differential flame graph or by saving profiles per release.
- Off-CPU flame graphs show where threads wait (locks, I/O, sleeps), which explains low-CPU latency.
- Beware inlining and missing symbols; unknown frames and `[unknown]` mean the profiler cannot unwind that code.
- Cross-check with metrics: a hot function is only worth fixing if the code path matters for the endpoint that misses the SLO.

## 5. Common bottlenecks and fixes

Database:

- Find the worst queries by total time (`pg_stat_statements` in PostgreSQL), not only the slowest single query.
- `EXPLAIN (ANALYZE, BUFFERS)` on the real query with representative data: look for sequential scans on large tables, row estimate errors, nested loops over large sets, sorts spilling to disk, and high buffer reads.
- Add or fix indexes (composite order matching filters then sort), avoid functions on indexed columns, use keyset pagination instead of large `OFFSET`.
- Remove N+1 by batching (`WHERE id = ANY($1)`), joins, or dataloader patterns. Use bulk inserts or `COPY`.
- Keep transactions short; lock waits show in `pg_stat_activity` and `pg_locks`.
- Details of scaling the data layer: [data-scaling.md](data-scaling.md).

Application:

- Serialization and parsing: avoid repeated conversion; stream large payloads; precompute static responses.
- Hot loops: replace quadratic algorithms, hoist invariant work, use appropriate data structures (set/map instead of list scans).
- Allocation: reuse buffers and objects where profiles show GC pressure; avoid creating closures or regexes per request.
- Locks: shrink critical sections, shard state, use read-write locks or lock-free structures only when profiling shows contention; prefer immutable shared data.
- Concurrency: run independent I/O in parallel with a bounded fan-out; size worker pools using Little's law; do not block the event loop.
- Logging and metrics: synchronous logging and high-cardinality metrics can dominate; sample debug logs, buffer writes.

Network and edge:

- Reuse connections (HTTP keep-alive, HTTP/2 multiplexing, database pools); avoid per-request DNS lookups and TLS handshakes; compress text responses; cache at CDN or reverse proxy.
- Reduce chattiness: batch calls, use GraphQL or composite endpoints only where it cuts round trips, and co-locate dependent services.

Memory and GC:

- Distinguish leak (growth without bound across GCs) from high steady state; take heap snapshots at two points and diff.
- Set container memory limits above the working set plus runtime overhead; configure runtime heap limits to the container (for example the JVM's container awareness, `GOMEMLIMIT` in Go, `--max-old-space-size` in Node).

I/O:

- Batch small writes, use async or vectored I/O, fsync intentionally, separate noisy workloads (logs, temp files) from data volumes, and watch cloud disk burst credits.

## 6. Benchmarking pitfalls

- Microbenchmarks mislead without warm-up (JIT, caches), enough iterations, and protection against dead-code elimination; use the language's harness (Go `testing`, JMH, criterion, benchmark.js-style tools).
- Measure variance: run multiple times, report medians and confidence intervals, and compare with a statistical tool (benchstat). Differences inside noise are not wins.
- Isolate the environment: fixed CPU frequency/governor, no noisy neighbors, same hardware for before and after, fixed dataset.
- Do not benchmark on the same host as the load generator; the generator can be the bottleneck.
- Avoid coordinated omission: use arrival-rate (open model) load or correct the histograms.
- Realistic data and access patterns matter: skew, cache hit rate, payload sizes, cold versus warm start.
- A faster microbenchmark does not guarantee a faster system; confirm with an end-to-end test.

## 7. Concurrency and queuing intuition

- Little's law sizes pools: `in-flight = rate × latency`. A pool smaller than that queues requests; a pool far larger just moves the queue into the database.
- Utilization near 100% makes queues explode; keep headroom or reject early.
- More threads than cores help only when threads block; CPU-bound work wants about one runnable thread per core.
- Fan-out amplifies tail latency: the slowest of N parallel calls sets the response time. Reduce N, add timeouts, or hedge (see [autoscaling-capacity.md](autoscaling-capacity.md)).

## 8. Reporting results

Report before and after on the same workload: load, throughput, p50/p95/p99, error rate, CPU and memory, cost per request, and the profile or query plan that explains the change. Keep the profiles in the repository or a profile store so regressions can be compared later.
