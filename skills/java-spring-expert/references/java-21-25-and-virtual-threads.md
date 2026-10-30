# Java 21 to 25 Features and Virtual Threads

Language and runtime features that matter in Spring services, which release finalized each one, and how virtual threads behave with Spring Boot. Java 21 and Java 25 are the LTS releases covered. Release facts come from the OpenJDK JEP pages; Spring facts from Spring Boot 4.1 (2026-10).

## Contents

1. [Feature timeline](#1-feature-timeline)
2. [Records](#2-records)
3. [Sealed types and pattern matching](#3-sealed-types-and-pattern-matching)
4. [Java 25 additions](#4-java-25-additions)
5. [Virtual threads in Spring](#5-virtual-threads-in-spring)
6. [Pinning](#6-pinning)
7. [Scoped values and structured concurrency](#7-scoped-values-and-structured-concurrency)
8. [Build setup](#8-build-setup)

## 1. Feature timeline

| Feature | JEP | Final in | Notes |
|---|---|---|---|
| Records | 395 | 16 | Immutable data carriers; cannot be JPA entities |
| Sealed classes and interfaces | 409 | 17 | `sealed ... permits`, subclasses `final`, `sealed` or `non-sealed` |
| Pattern matching for `switch` | 441 | 21 | Type patterns, guards with `when`, exhaustiveness for sealed types |
| Record patterns | 440 | 21 | Deconstruct records in `switch` and `instanceof` |
| Virtual threads | 444 | 21 | Lightweight threads scheduled by the JVM |
| Sequenced collections | 431 | 21 | `getFirst()`, `getLast()`, `reversed()` on lists, deques, `LinkedHashSet`, `LinkedHashMap` |
| Unnamed variables and patterns (`_`) | 456 | 22 | For unused variables and pattern components |
| Stream gatherers | 485 | 24 | `Stream.gather(Gatherer)` for custom intermediate operations |
| Virtual threads without `synchronized` pinning | 491 | 24 | Blocking in `synchronized` no longer pins the carrier thread |
| Module import declarations | 511 | 25 | `import module java.base;` |
| Scoped values | 506 | 25 | Immutable per-scope data shared with callees and child threads |
| Compact source files and instance main methods | 512 | 25 | Small programs and scripts without class boilerplate |
| Flexible constructor bodies | 513 | 25 | Statements before `super(...)` or `this(...)` that do not touch `this` |
| Structured concurrency | 505 | preview in 25 | Fifth preview; needs `--enable-preview`; check the current JDK status before use in production |

Language level is set by the build (`maven.compiler.release` or Gradle toolchain), so a feature final in 25 is unavailable when the project compiles for 21.

## 2. Records

```java
public record CreateNoteRequest(
        @NotBlank @Size(max = 200) String title,
        @Size(max = 10_000) String body) {

    public CreateNoteRequest {            // compact constructor: normalize and validate
        title = title == null ? null : title.strip();
    }
}
```

- Use records for request and response bodies, projections, events and `@ConfigurationProperties`. Jackson (3.x under Boot 4) and Bean Validation both support them.
- Record components are final and the class is final: lazy proxies and Hibernate entity requirements rule out `@Entity` records. Hibernate `@Embeddable` records are possible; check the Hibernate 7 docs for the supported mappings before relying on them.
- Mutable components (lists, arrays) stay mutable; copy with `List.copyOf` in the compact constructor when the record must be immutable.

## 3. Sealed types and pattern matching

```java
public sealed interface Shipment permits Pickup, Courier, Locker {}
public record Pickup(String storeId) implements Shipment {}
public record Courier(String address, boolean express) implements Shipment {}
public record Locker(String lockerId) implements Shipment {}

static Money fee(Shipment s) {
    return switch (s) {
        case Pickup p -> Money.ZERO;
        case Courier(var address, var express) when express -> Money.of(15);
        case Courier c -> Money.of(7);
        case Locker l -> Money.of(3);
    };   // no default: adding a permitted type breaks compilation here
}
```

- Leave out `default` when switching over a sealed type so the compiler reports missing cases.
- Order matters: a guarded case must come before the unguarded case of the same type.
- `switch` on `null` throws `NullPointerException` unless a `case null` is present.
- Use pattern matching for `instanceof` (`if (o instanceof Courier c && c.express())`) instead of cast chains.
- Use `_` (Java 22+) for components you do not need: `case Courier(_, var express)`.
- Sealed hierarchies suit domain results and event types; avoid them for plugin-style extension points.

## 4. Java 25 additions

- **Scoped values** (final): see section 7.
- **Flexible constructor bodies**: validate or compute arguments before calling `super(...)`:

```java
public class Positive extends Value {
    public Positive(long n) {
        if (n <= 0) throw new IllegalArgumentException("must be positive");
        super(n);
    }
}
```

  Code before `super(...)` may not read `this` or call instance methods; it is useful in class hierarchies, rarely in Spring beans (which use constructor injection and few hierarchies).
- **Compact source files and instance main**: a single file with `void main() { ... }` runs with `java Hello.java`; suitable for scripts and learning, not for Spring applications.
- **Module import declarations**: `import module java.base;` imports the exported packages of a module; style choice, not required.
- Runtime changes in 25 (garbage collector, compact object headers, startup) are tuning topics; read the JDK 25 release notes before changing JVM flags.

## 5. Virtual threads in Spring

- Enable with `spring.threads.virtual.enabled=true` on Java 21+. Boot then uses virtual threads for the embedded web server's request handling, and the auto-configured `applicationTaskExecutor` (`SimpleAsyncTaskExecutor`) and task scheduler (`SimpleAsyncTaskScheduler`) run on virtual threads; the scheduler ignores pool-related properties.
- Virtual threads help blocking, I/O-bound code (JDBC, HTTP calls). They do not speed up CPU-bound work.
- A virtual thread per request removes the thread-count limit but not the limits of downstream systems:
  - Hikari pool size caps concurrent database work; extra requests wait for a connection (`spring.datasource.hikari.connection-timeout` bounds the wait).
  - For rate-limited APIs or expensive operations cap concurrency with a `Semaphore` or Spring's `@ConcurrencyLimit` (Framework 7, enable with `@EnableResilientMethods`).
- Do not pool virtual threads. Create one per task with `Executors.newVirtualThreadPerTaskExecutor()` or `Thread.ofVirtual().start(...)`.
- Thread-local data (security context, MDC, transaction state) does not cross into new threads automatically; tasks started with `@Async` need their own transaction and security propagation (Spring Security offers delegating executors for the context).
- Avoid large `ThreadLocal` caches (for example per-thread buffers): millions of short-lived threads multiply the memory.

```java
@Bean(destroyMethod = "close")
ExecutorService reportExecutor() {
    return Executors.newVirtualThreadPerTaskExecutor();
}
```

## 6. Pinning

A virtual thread is pinned when it cannot unmount from its carrier (platform) thread while blocked, which can starve other virtual threads.

- Java 21 to 23: blocking while holding a monitor (`synchronized` block or method) pins the carrier. Mitigation: use `java.util.concurrent.locks.ReentrantLock` in your own code, and upgrade libraries that synchronize around I/O.
- Java 24 and later (JEP 491): the `synchronized` case no longer pins; virtual threads waiting for or blocking in `Object.wait()` or monitors unmount. Pinning remains possible while a native method or foreign function is on the stack; read JEP 491 for the exact remaining cases.
- Diagnostics: the `-Djdk.tracePinnedThreads` option was dropped in JDK 24; use the JFR event `jdk.VirtualThreadPinned` (it also covers the additional pinning cases). On Java 21, `-Djdk.tracePinnedThreads=full` prints stack traces for pinned parking.
- Signs of pinning in production: request latency rises while CPU is idle and the carrier thread count is saturated; check JFR before changing code.
- Target Java 25 for new services that use virtual threads so the monitor pinning problem does not apply.

## 7. Scoped values and structured concurrency

```java
private static final ScopedValue<String> TENANT = ScopedValue.newInstance();

void handle(String tenantId, Runnable work) {
    ScopedValue.where(TENANT, tenantId).run(work);   // value visible to callees, gone after run()
}

String current() { return TENANT.get(); }
```

- `ScopedValue` data is immutable and bound for the dynamic scope of `run` or `call`; it replaces `ThreadLocal` for passing request-scoped data down a call tree, with cheaper inheritance in child threads when used with structured concurrency.
- In Java 25, `ScopedValue.orElse` no longer accepts `null`.
- Spring's own request context (`RequestContextHolder`, `SecurityContextHolder`) is `ThreadLocal`-based; scoped values complement it for your own data and do not replace the framework's holders.
- Structured concurrency (JEP 505) is a preview in 25: its API can change and needs `--enable-preview` at compile and run time. Use `ExecutorService` with `Future` or `CompletableFuture` in production code until it is final.

## 8. Build setup

```xml
<properties>
  <java.version>25</java.version>
  <maven.compiler.release>${java.version}</maven.compiler.release>
</properties>
```

```kotlin
// build.gradle.kts
java {
    toolchain { languageVersion = JavaLanguageVersion.of(25) }
}
```

- Boot 4 requires at least Java 17; the 4.1.x system requirements list the newest supported JDK, so check them when moving past 25.
- Match the JDK in CI, the container base image and production (image choices: docker-expert).
- JVM flags: prefer container-aware defaults and `-XX:MaxRAMPercentage`; avoid copying flag lists from old blog posts, since several options were removed across releases.
- Preview features need `--enable-preview` for the compiler and runtime; avoid them in shared libraries.
