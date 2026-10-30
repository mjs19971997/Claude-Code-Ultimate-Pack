# asyncio Patterns

Structured concurrency with `asyncio` on Python 3.13 and 3.14: TaskGroup, timeouts, cancellation, queues, exception groups, bridging blocking code and debugging. The code blocks run on both versions (checked on 3.13 and 3.14.6, 2026-10).

## Contents

1. [Entry points and the event loop](#1-entry-points-and-the-event-loop)
2. [TaskGroup](#2-taskgroup)
3. [Timeouts and cancellation](#3-timeouts-and-cancellation)
4. [Limiting concurrency](#4-limiting-concurrency)
5. [Queues and producer-consumer](#5-queues-and-producer-consumer)
6. [Blocking code and threads](#6-blocking-code-and-threads)
7. [Exception groups](#7-exception-groups)
8. [Debugging](#8-debugging)
9. [Changes in 3.14](#9-changes-in-314)

## 1. Entry points and the event loop

```python
import asyncio


async def main() -> None:
    await asyncio.sleep(0.01)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
```

- `asyncio.run(main())` creates a loop, runs the coroutine, cancels leftover tasks and closes the loop. Call it once per process at the top level, never from inside a running loop.
- `asyncio.Runner` keeps one loop across several calls (`with asyncio.Runner() as r: r.run(main())`); pytest plugins and REPL helpers use it.
- Do not call `asyncio.get_event_loop()` to obtain a loop outside a coroutine. On 3.14 it raises `RuntimeError` when no loop is set. Inside a coroutine use `asyncio.get_running_loop()`.
- A coroutine that is called but not awaited does nothing and produces a "never awaited" warning. `await` it, or wrap it in a task.
- Third-party libraries that expose their own async API (httpx, asyncpg, aiofiles) must be used from the same loop; do not mix loops across threads.

## 2. TaskGroup

```python
import asyncio


async def fetch(i: int) -> str:
    await asyncio.sleep(0.01)
    if i == 3:
        raise ValueError(f"bad item {i}")
    return f"item-{i}"


async def main() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch(i)) for i in range(5)]
        print([t.result() for t in tasks])
    except* ValueError as eg:
        print("failed:", [str(e) for e in eg.exceptions])


asyncio.run(main())
```

- Leaving the `async with` block waits for every task. If one task raises, the group cancels the others and raises an `ExceptionGroup` with all the failures (cancellations of siblings are not included).
- Always call `tg.create_task()` for work inside the group; the group holds the reference, so no task is garbage collected or forgotten.
- Read results after the block with `t.result()`; do not read them inside, they may not be finished.
- `asyncio.gather(*coros)` still exists. Its default leaves the other awaitables running when one fails, and `return_exceptions=True` returns exceptions as values. Use it only when you want exactly that behaviour; otherwise use `TaskGroup`.
- A child task should not swallow `asyncio.CancelledError`. If you catch it for cleanup, re-raise it afterward.
- A task created with `asyncio.create_task()` outside a group needs a stored reference (a set with a done-callback that discards it) so it is not garbage collected before it finishes.

## 3. Timeouts and cancellation

```python
import asyncio


async def slow() -> None:
    await asyncio.sleep(10)


async def main() -> None:
    try:
        async with asyncio.timeout(0.05):
            await slow()
    except TimeoutError:
        print("timed out")

    # a deadline shared by several steps
    async with asyncio.timeout(1) as cm:
        await asyncio.sleep(0.01)
        cm.reschedule(asyncio.get_running_loop().time() + 0.5)


asyncio.run(main())
```

- `asyncio.timeout(seconds)` (3.11+) cancels the enclosed block and raises `TimeoutError` outside it. It composes: nested timeouts and cancellation by the caller both work. `timeout_at(when)` takes a loop-clock deadline; `None` disables the limit.
- `asyncio.wait_for(aw, timeout)` is still available, but wraps a single awaitable; prefer `timeout()` for blocks.
- Cancellation is delivered as `asyncio.CancelledError` raised at the next `await`. Clean up in `finally`; if you must await in cleanup, keep it short.
- `asyncio.shield(aw)` protects an inner task from cancellation of the outer one; the outer still gets cancelled, so use it sparingly and keep a reference to the inner task.
- Every network wait should have a timeout, either on the client (`httpx.AsyncClient(timeout=5.0)`) or with `asyncio.timeout`.
- Handle process signals by cancelling the main task so `async with` blocks unwind; check the `asyncio.Runner` docs for how `Ctrl+C` is handled in your version.

## 4. Limiting concurrency

```python
import asyncio
from collections.abc import Awaitable, Callable, Iterable
from functools import partial


async def bounded_gather[T](
    factories: Iterable[Callable[[], Awaitable[T]]], limit: int = 5
) -> list[T]:
    sem = asyncio.Semaphore(limit)

    async def run(f: Callable[[], Awaitable[T]]) -> T:
        async with sem:
            return await f()

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(run(f)) for f in factories]
    return [t.result() for t in tasks]


async def work(i: int) -> int:
    await asyncio.sleep(0.01)
    return i * i


print(asyncio.run(bounded_gather([partial(work, i) for i in range(10)], limit=3)))
```

- Passing factories (callables) instead of coroutine objects means a coroutine is only created when a slot is free; creating 100,000 coroutine objects up front costs memory.
- For a very large input, do not create one task per item: use a fixed pool of worker tasks reading from a queue (next section).
- `asyncio.Lock`, `Event`, `Condition` and `Barrier` guard shared state; keep critical sections free of `await` where possible.
- `asyncio.eager_task_factory` (install with `loop.set_task_factory(asyncio.eager_task_factory)`) starts each task synchronously until its first suspension, which can cut overhead for short tasks that often finish without waiting; measure before adopting.

## 5. Queues and producer-consumer

```python
import asyncio


async def consumer(q: asyncio.Queue[int]) -> int:
    total = 0
    while True:
        try:
            item = await q.get()
        except asyncio.QueueShutDown:
            return total
        total += item
        q.task_done()


async def main() -> None:
    q: asyncio.Queue[int] = asyncio.Queue(maxsize=100)
    async with asyncio.TaskGroup() as tg:
        workers = [tg.create_task(consumer(q)) for _ in range(3)]
        for i in range(20):
            await q.put(i)  # blocks when the queue is full: backpressure
        await q.join()
        q.shutdown()  # 3.13+: wakes consumers with QueueShutDown
    print(sum(w.result() for w in workers))


asyncio.run(main())
```

- Use a bounded queue (`maxsize`) so a fast producer cannot exhaust memory.
- `Queue.shutdown()` (3.13+) ends consumers cleanly; `shutdown(immediate=True)` also discards queued items. On 3.12 and earlier, use a sentinel value per consumer.
- Call `task_done()` for each processed item, otherwise `join()` never returns.
- `asyncio.PriorityQueue` and `LifoQueue` follow the same API.

## 6. Blocking code and threads

```python
import asyncio
import time


def blocking(n: int) -> int:
    time.sleep(0.01)
    return n * 2


async def main() -> None:
    result = await asyncio.to_thread(blocking, 21)
    print(result)


asyncio.run(main())
```

- `asyncio.to_thread(fn, *args)` runs a blocking function in the default thread pool and copies the current context variables. Use it for blocking libraries and file I/O that has no async version.
- CPU-bound work blocks the loop and holds the GIL on the default build; use `loop.run_in_executor(ProcessPoolExecutor(), fn, arg)` with a process pool, or a native extension.
- The reverse direction: from a worker thread, submit to the loop with `asyncio.run_coroutine_threadsafe(coro, loop)`.
- Do not call `asyncio.run()` inside a coroutine. Await the coroutine instead.
- Synchronous libraries (the `requests` package, plain `sqlite3`) block the loop if called directly in a coroutine; Ruff's `ASYNC` rules flag many such calls.

## 7. Exception groups

```python
import asyncio


async def boom(exc: Exception) -> None:
    raise exc


async def main() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(boom(ValueError("a")))
            tg.create_task(boom(KeyError("b")))
    except* ValueError as eg:
        print("values:", eg.exceptions)
    except* KeyError as eg:
        print("keys:", eg.exceptions)


asyncio.run(main())
```

- `except*` handles the matching subset of an `ExceptionGroup` and lets the rest propagate; each clause may run. Do not mix `except` and `except*` in one `try`.
- A group can nest. `eg.split(Type)` and `eg.subgroup(Type)` filter programmatically.
- In tests, `pytest.RaisesGroup(ValueError, KeyError)` asserts the structure of a group.
- Code that previously caught a single exception from a task may now receive a group when the task ran inside a `TaskGroup`; update the handlers.
- `asyncio.timeout` raises plain `TimeoutError`; it is not wrapped in a group unless raised inside a group's child task.

## 8. Debugging

- `asyncio.run(main(), debug=True)`, `python -X dev` or `PYTHONASYNCIODEBUG=1` enable debug mode: slow-callback warnings, never-awaited coroutine tracebacks and thread-safety checks.
- Set `loop.slow_callback_duration` to tune the slow-callback threshold in debug mode.
- Name tasks (`tg.create_task(coro, name="fetch-user-42")`) so logs and tooling show something useful.
- On 3.14, inspect a live process from the outside with `python -m asyncio ps PID` (a table of pending tasks) and `python -m asyncio pstree PID` (the await tree). Within code, `asyncio.print_call_graph()` and `asyncio.capture_call_graph()` show who is awaiting what.
- Use `logging` with `exc_info=True` inside task wrappers; an exception in a task that nobody awaits is only reported when the task is garbage collected.
- A hang usually means a missing `await`, a blocking call in a coroutine, an unbounded `queue.join()` without `task_done()`, or a missing timeout. Profile the loop with `cProfile` on a representative run to see which synchronous call dominates.

## 9. Changes in 3.14

- `asyncio.get_event_loop()` raises `RuntimeError` when there is no current loop, instead of creating one.
- The event loop policy system (`get_event_loop_policy`, `set_event_loop_policy`, `AbstractEventLoopPolicy`, `DefaultEventLoopPolicy`) is deprecated, with removal scheduled for 3.16. Where a policy was used to choose a loop implementation, pass `loop_factory=` to `asyncio.run()` or `asyncio.Runner()` instead.
- A test suite that turns warnings into errors can fail on policy-related deprecation warnings raised by plugins (reported for pytest-asyncio); upgrade the plugin and read its release notes before suppressing them.
- The default `multiprocessing` start method on Linux is `forkserver`; code that relied on inheriting globals through `fork` must pass data explicitly.
- On a free-threaded build, threads started by `to_thread` can run Python code in parallel, so shared mutable state needs explicit locks.
