# Async Rust with Tokio

Practical rules for async Rust on tokio: runtime setup, tasks, channels, `select!` and cancellation safety, graceful shutdown, blocking work, async traits and async tests. Verified against Rust 1.99.1 and tokio 1.54.1 (MSRV 1.85), tokio-util 0.7 (2026-10).

## Contents

1. [Runtime and features](#1-runtime-and-features)
2. [Tasks and JoinSet](#2-tasks-and-joinset)
3. [Channels and shared state](#3-channels-and-shared-state)
4. [select and cancellation safety](#4-select-and-cancellation-safety)
5. [Graceful shutdown](#5-graceful-shutdown)
6. [Blocking and CPU-bound work](#6-blocking-and-cpu-bound-work)
7. [Async fn in traits](#7-async-fn-in-traits)
8. [Testing async code](#8-testing-async-code)

## 1. Runtime and features

- Tokio features are opt-in. Enable only what the crate uses. Common ones: `rt`, `rt-multi-thread`, `macros` (for `#[tokio::main]`, `#[tokio::test]`, `select!`), `net`, `time`, `sync`, `signal`, `fs`, `io-util`, `process`. `full` turns everything on; use it for applications, not libraries.
- A missing feature shows up as `unresolved import tokio::net`, or as a failure on `#[tokio::main]` or `tokio::select!`. Add the missing feature (`net`, `macros`, `rt-multi-thread`).
- Libraries should depend on tokio with the minimum features and let the application choose the runtime flavor.
- `#[tokio::main]` builds a multi-thread runtime (needs `rt-multi-thread`). Use `#[tokio::main(flavor = "current_thread")]` for a single-threaded runtime, or build one by hand with `tokio::runtime::Builder` to control worker threads and thread names.
- A future does nothing until awaited or spawned. `let f = work();` without `.await` is a no-op (the compiler warns with `unused_must_use`).
- Futures are state machines: a large local held across an `.await` makes the future big. Box very large futures or drop big buffers before awaiting.

## 2. Tasks and JoinSet

- `tokio::spawn(fut)` needs `fut: Send + 'static` on the multi-thread runtime. Move owned data in; share state with `Arc`.
- The returned `JoinHandle` yields `Result<T, JoinError>`; a panic in the task becomes `Err(JoinError)` with `is_panic()`. Dropping the handle detaches the task, it keeps running.
- Use `JoinSet` to run a dynamic group of tasks: results arrive in completion order with `join_next().await`, and dropping the set aborts the remaining tasks.
- Bound concurrency with a `Semaphore` (`acquire_owned` moves the permit into the task) instead of spawning per item without limit.
- Task-local non-`Send` work goes on a `LocalSet` or the current-thread runtime.

```rust
use std::sync::Arc;
use tokio::task::JoinSet;

trait Fetch {
    fn fetch(&self, id: u32) -> impl Future<Output = String> + Send;
}

struct Real;

impl Fetch for Real {
    async fn fetch(&self, id: u32) -> String {
        format!("item-{id}")
    }
}

async fn run_all<F: Fetch + Send + Sync + 'static>(f: Arc<F>) -> Vec<String> {
    let mut set = JoinSet::new();
    for id in 0..3 {
        let f = Arc::clone(&f);
        set.spawn(async move { f.fetch(id).await });
    }
    let mut out = Vec::new();
    while let Some(res) = set.join_next().await {
        out.push(res.expect("task panicked"));
    }
    out
}
```

## 3. Channels and shared state

| Primitive | Use |
|---|---|
| `mpsc::channel(n)` | Many producers, one consumer, bounded. Backpressure: `send().await` waits when full |
| `mpsc::unbounded_channel()` | Only when the sender must never wait and growth is bounded by other means |
| `oneshot` | One value back to a requester (reply channel) |
| `broadcast` | Many consumers each see every message; slow receivers lag and lose messages |
| `watch` | Latest value only (config, shutdown flag); receivers wait for `changed()` |
| `Semaphore` | Limit concurrency or model a pool |
| `Notify` | Wake a task without data |
| `Mutex` / `RwLock` (tokio) | Lock that may be held across `.await`; slower than `std::sync::Mutex` |

- Use `std::sync::Mutex` for short critical sections that never contain an `.await`; it is cheaper and clippy's `await_holding_lock` flags mistakes.
- Prefer an actor: one task owns the state, others send commands carrying a `oneshot::Sender` for the reply.
- Receivers return `None` when all senders are dropped; treat it as shutdown, not as an error.
- `recv_many(&mut buf, limit)` drains several messages per wake-up for throughput.

## 4. select and cancellation safety

- `tokio::select!` polls branches concurrently, runs the handler of the first one that completes and drops the others. Dropping a future at an `.await` cancels it there; its remaining code never runs.
- A future is cancellation safe when dropping it before completion loses no data and leaves no half-done state, so it can be retried. The `select!` documentation lists the methods in each group:
  - Safe in the current docs: `mpsc::Receiver::recv`, `broadcast::Receiver::recv`, `watch::Receiver::changed`, `TcpListener::accept`, `AsyncReadExt::read`, `AsyncWriteExt::write`, `tokio_stream::StreamExt::next`.
  - Not safe (data may be lost): `AsyncReadExt::read_exact`, `read_to_end`, `read_to_string`, `AsyncWriteExt::write_all`.
  - Lose their place in the fairness queue if dropped: `Mutex::lock`, `RwLock::read`/`write`, `Semaphore::acquire`, `Notify::notified`.
- To use a non-safe future in a loop, create it once outside the loop, pin it (`tokio::pin!`) and poll it with `&mut fut` in the branch so it is not dropped when another branch wins.
- Your own async functions are cancellation safe only if every `.await` point is: state mutated before an `.await` and not restored on drop is a bug on cancellation. Prefer designs where the cancel point is at the top of the loop.
- Branch patterns: `Some(x) = rx.recv()` disables the branch when the pattern fails; add `else => break` for when all branches are disabled.
- `select!` picks randomly among ready branches; add `biased;` at the top only when ordering matters (for example checking shutdown first).
- `tokio::time::timeout(dur, fut)` cancels `fut` by dropping it on expiry; apply the same cancellation-safety rules.
- `JoinHandle::abort()` cancels a task at its next `.await`; it cannot stop a task blocked in synchronous code.

```rust
use std::time::Duration;
use tokio::time::{sleep, timeout};

#[tokio::main]
async fn main() {
    let slow = sleep(Duration::from_secs(5));
    let result = timeout(Duration::from_millis(10), slow).await;
    assert!(result.is_err()); // Elapsed: the inner future was dropped
}
```

## 5. Graceful shutdown

- Create one `CancellationToken` (tokio-util, `sync` module) at startup and hand clones to tasks. `token.cancelled()` is a future for `select!`; `token.cancel()` wakes all waiters; `child_token()` gives a scoped token.
- Sequence: receive the signal, cancel the token, stop accepting new work, wait for the `JoinSet` to drain, flush buffers, exit. Bound the wait with a timeout so a stuck task cannot hang the process.
- `tokio::signal::ctrl_c()` handles SIGINT everywhere; use `tokio::signal::unix::signal(SignalKind::terminate())` for SIGTERM on Unix (orchestrators send SIGTERM).
- Dropping the runtime at the end of `main` aborts remaining tasks; work that must finish needs explicit awaiting.

```rust
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::Semaphore;
use tokio::task::JoinSet;
use tokio_util::sync::CancellationToken;

pub async fn serve(token: CancellationToken) -> std::io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:0").await?;
    let limit = Arc::new(Semaphore::new(100));
    let mut conns = JoinSet::new();
    loop {
        tokio::select! {
            () = token.cancelled() => break,
            accepted = listener.accept() => {
                let (_socket, _peer) = accepted?;
                let permit = Arc::clone(&limit)
                    .acquire_owned()
                    .await
                    .expect("semaphore is never closed");
                conns.spawn(async move {
                    let _permit = permit; // released when the connection task ends
                    // handle the connection here
                });
            }
        }
    }
    while conns.join_next().await.is_some() {}
    Ok(())
}
```

## 6. Blocking and CPU-bound work

- A worker thread running synchronous code cannot poll other tasks. Symptoms: high latency with idle CPU, timers firing late, `tokio-console` showing long polls.
- `tokio::task::spawn_blocking(|| ...)` runs a closure on the blocking pool (default cap of 512 threads) and returns a `JoinHandle` to await. Use it for synchronous file or database drivers, compression, hashing and parsing of large inputs.
- A running `spawn_blocking` task cannot be aborted; `abort()` only helps before it starts. At runtime shutdown, tokio waits for blocking tasks unless `shutdown_timeout` or `shutdown_background` is used. Long CPU jobs should poll a flag or run on a dedicated thread or rayon pool and report back over a `oneshot`.
- For an unbounded stream of CPU jobs use a dedicated pool with a bounded queue, so the blocking pool is not exhausted.
- `tokio::fs` itself uses the blocking pool; for many small file operations, one `spawn_blocking` around a batch can be cheaper.
- `std::thread::sleep`, synchronous `reqwest::blocking` or `std::net` calls inside async code are bugs; use the async equivalents.

## 7. Async fn in traits

- `async fn` in traits is stable (Rust 1.75). Static dispatch (generics, `impl Trait`) works; `dyn Trait` does not, because the trait is not dyn compatible.
- Returned futures from a plain `async fn` in a trait are not guaranteed `Send`, so generic code that spawns them needs a bound. Declare the method as `fn f(&self) -> impl Future<Output = T> + Send;` in the trait (implementations may still be written with `async fn`) as in section 2.
- For `dyn` use, return `Pin<Box<dyn Future<Output = T> + Send + '_>>` by hand, or use the `async-trait` crate, which does the boxing for you.
- Async closures (`async || {}`) are stable since Rust 1.85; use them where a closure must borrow from its captures across an await.

## 8. Testing async code

- `#[tokio::test]` runs the test on a current-thread runtime; use `#[tokio::test(flavor = "multi_thread", worker_threads = 2)]` when the code requires parallelism.
- Enable tokio's `test-util` feature in `[dev-dependencies]` and use `#[tokio::test(start_paused = true)]`: the clock auto-advances when the runtime is idle, so `sleep` and `timeout` complete instantly and deterministically.
- Test cancellation explicitly: cancel the token, then assert the task finishes within a timeout and its side effects are consistent.
- Test error paths of the channels (sender dropped, receiver dropped, full queue).
- Avoid real network and wall-clock time in unit tests; bind to `127.0.0.1:0` in integration tests to get a free port.

```rust
#[cfg(test)]
mod tests {
    use std::time::Duration;
    use tokio::time::{sleep, timeout};

    #[tokio::test(start_paused = true)]
    async fn timeout_fires_without_real_waiting() {
        let slow = sleep(Duration::from_secs(60));
        assert!(timeout(Duration::from_secs(1), slow).await.is_err());
    }
}
```
