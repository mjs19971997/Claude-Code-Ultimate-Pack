# Cross-Cutting Best Practices

This document defines the engineering principles that every skill in the Claude Code Ultimate Pack enforces. These principles are not optional — they are the foundation on which every skill is built.

---

## Table of Contents

1. [SOLID Principles](#solid-principles)
2. [DRY — Don't Repeat Yourself](#dry--dont-repeat-yourself)
3. [KISS — Keep It Simple, Stupid](#kiss--keep-it-simple-stupid)
4. [YAGNI — You Aren't Gonna Need It](#yagni--you-arent-gonna-need-it)
5. [Clean Architecture](#clean-architecture)
6. [Feature-Based Architecture](#feature-based-architecture)
7. [Enterprise Architecture](#enterprise-architecture)
8. [Production-Ready Code](#production-ready-code)
9. [Security First](#security-first)
10. [Performance First](#performance-first)
11. [Scalability](#scalability)
12. [Maintainability](#maintainability)
13. [Readable Code](#readable-code)
14. [Reusable Components](#reusable-components)
15. [Comprehensive Documentation](#comprehensive-documentation)

---

## SOLID Principles

### Single Responsibility Principle (SRP)

Every class, module, function, and component must have one and only one reason to change. If a class handles authentication, logging, and email sending, it has three reasons to change — split it into three classes.

**Enforcement**: When designing a module, ask: "If I had to change this module, how many unrelated reasons might cause that change?" If the answer is more than one, split the module.

### Open/Closed Principle (OCP)

Software entities must be open for extension but closed for modification. Add new behavior by adding new code, not by editing existing code.

**Enforcement**: When you need to add a new behavior, prefer composition, strategy patterns, or plugin architectures over editing existing functions. If you must edit existing code, the design is wrong.

### Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types without altering the correctness of the program. A subclass that throws `NotImplementedError` for inherited methods violates LSP.

**Enforcement**: If a subclass cannot fulfill the contract of its parent, the inheritance hierarchy is wrong. Prefer composition over inheritance.

### Interface Segregation Principle (ISP)

Clients must not be forced to depend on interfaces they do not use. A 20-method interface that some implementers only partially implement violates ISP.

**Enforcement**: Split fat interfaces into smaller, role-specific interfaces. An implementer should implement only the methods it actually uses.

### Dependency Inversion Principle (DIP)

High-level modules must not depend on low-level modules. Both must depend on abstractions. Abstractions must not depend on details. Details must depend on abstractions.

**Enforcement**: Define interfaces at the boundary of every layer. Inject dependencies through constructors or parameters. Never instantiate concrete dependencies inside business logic.

---

## DRY — Don't Repeat Yourself

Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.

**What DRY is**: If the same business rule appears in three places, and the rule changes, you must update three places. DRY says: extract the rule into one place and reference it.

**What DRY is not**: DRY is not "extract every similar-looking code into a shared function". Two functions that happen to look similar but serve different purposes are not duplication — they are coincidence. Premature abstraction is worse than duplication.

**Enforcement**:
- Duplicate business rules: always extract
- Duplicate code patterns: extract only when the pattern is used 3+ times AND serves the same purpose
- Duplicate string literals: extract into constants
- Duplicate configuration: extract into shared config files

---

## KISS — Keep It Simple, Stupid

Simplicity is a prerequisite for reliability. The simplest solution that satisfies the requirements is the best solution.

**Enforcement**:
- Prefer a plain function over a class with one method
- Prefer a conditional over a strategy pattern, until you have 3+ strategies
- Prefer a synchronous call over a message queue, until you actually need async decoupling
- Prefer a single SQL query over an ORM with 5 joins, until the query becomes unreadable
- Never add a layer of abstraction unless it removes more complexity than it adds

---

## YAGNI — You Aren't Gonna Need It

Never build for speculative future requirements. Build for today's requirements, in a way that does not prevent tomorrow's changes.

**Enforcement**:
- Never add a configuration option that no caller uses
- Never add a database column that no query reads
- Never add an API parameter that no client sends
- Never add a feature flag that is always on or always off
- Never add an interface with one implementation, unless required for testing
- When tempted to add "future-proofing", ask: "Do I have a concrete, scheduled requirement for this?" If no, do not build it.

---

## Clean Architecture

Dependencies point inward. The domain layer depends on nothing. The application layer depends on the domain. The infrastructure layer depends on the application. The presentation layer depends on the application.

```
Presentation (Controllers, UI)
       ↓
Application (Use Cases, Services)
       ↓
Domain (Entities, Business Rules)
       ↑
Infrastructure (Database, External APIs)
```

**Enforcement**:
- The domain layer imports nothing from outside the domain layer
- The application layer imports from the domain layer only
- The infrastructure layer implements interfaces defined in the application layer
- The presentation layer calls application layer use cases
- Database models, API clients, and frameworks are infrastructure concerns — they live in the outermost layer

---

## Feature-Based Architecture

Organize code by feature, not by technical layer. A feature is a cohesive unit of business functionality.

**Bad (layer-based)**:
```
src/
├── controllers/
│   ├── user-controller.ts
│   ├── order-controller.ts
│   └── product-controller.ts
├── services/
│   ├── user-service.ts
│   ├── order-service.ts
│   └── product-service.ts
└── repositories/
    ├── user-repository.ts
    ├── order-repository.ts
    └── product-repository.ts
```

**Good (feature-based)**:
```
src/
├── features/
│   ├── user/
│   │   ├── user-controller.ts
│   │   ├── user-service.ts
│   │   ├── user-repository.ts
│   │   ├── user-schema.ts
│   │   └── user-tests.ts
│   ├── order/
│   │   └── ...
│   └── product/
│       └── ...
└── shared/
    └── ...
```

**Enforcement**: A feature folder contains everything needed to understand and modify that feature. To change how orders work, you should never need to open more than the `order/` folder.

---

## Enterprise Architecture

Design for multi-team, multi-year sustainability. Enterprise architecture is not about complexity — it is about the discipline required to keep a large system changeable over many years.

**Enforcement**:
- Every module has a documented owner (team or individual)
- Every module has a public interface and a private implementation
- Breaking changes to public interfaces require a deprecation cycle
- Cross-module communication happens through documented contracts, not direct imports
- Every deployment is reproducible from version control
- Every system has a runbook for common operations and incidents

---

## Production-Ready Code

Code is not done when it works. Code is done when it works, is tested, is documented, is observable, is deployable, and is maintainable by someone other than the original author.

**Enforcement — code is not production-ready until**:
- It has tests (unit, integration, and E2E as appropriate)
- It has documentation (inline comments for non-obvious logic, doc comments for public APIs, README for modules)
- It has logging (structured, with correlation IDs, at appropriate levels)
- It has monitoring (metrics for rate, errors, duration; alerts for anomalies)
- It has error handling (every external call has a defined failure behavior)
- It has a deployment plan (how it rolls out, how it rolls back)
- It has a capacity plan (what load it handles, when it will need to scale)
- It has a security review (input validation, output encoding, authentication, authorization)
- It has a performance review (latency under load, resource usage, bottlenecks)

---

## Security First

Every decision is evaluated through a security lens before it is accepted. Security is not a phase at the end of development — it is a property of every decision made during development.

**Enforcement**:
- Never trust user input — validate, sanitize, and encode at every boundary
- Never store secrets in code, configuration files, or environment variables in version control
- Never log secrets, tokens, passwords, or personally identifiable information
- Always authenticate before authorizing
- Always authorize before executing
- Always use parameterized queries — never string concatenation
- Always use HTTPS — never HTTP
- Always use modern hashing algorithms (bcrypt, argon2) for passwords — never MD5, SHA1
- Always use established libraries for cryptography — never roll your own
- Always follow the principle of least privilege — grant the minimum permissions required

---

## Performance First

Every decision is evaluated through a performance lens. Performance is not an optimization phase at the end of development — it is a property of every design decision.

**Enforcement**:
- Know the latency budget for every operation and stay within it
- Know the throughput requirement for every system and design for it
- Measure before optimizing — never optimize based on intuition
- Optimize the common path first — the 80/20 rule applies
- Prefer O(1) and O(log n) algorithms over O(n) and O(n²)
- Prefer streaming over loading entire datasets into memory
- Prefer caching over recomputation, with explicit invalidation
- Prefer async I/O over sync I/O in high-concurrency systems
- Prefer batching over individual operations for network and database calls
- Prefer connection pooling over per-request connections

---

## Scalability

Designs that grow 1000x without rewrites. Scalability is not about handling today's load — it is about not requiring a rewrite when load grows 10x, 100x, or 1000x.

**Enforcement**:
- Statelessness: application servers hold no session state; state lives in databases or caches
- Horizontal scaling: every component scales by adding more instances, not bigger instances
- Partitioning: data is partitionable by some key (tenant_id, user_id, region) so it can be sharded
- Asynchronous boundaries: long-running work is offloaded to queues, not done synchronously
- Caching layers: read-heavy data is cached at multiple layers (CDN, application, database)
- Database scaling: designed for read replicas and sharding from day one, even if not used initially
- Idempotency: every operation is safe to retry, so failed requests can be re-sent

---

## Maintainability

Code that the next developer can understand in 5 minutes. Maintainability is measured by the time it takes a new developer to make a confident change.

**Enforcement**:
- Names reveal intent — `processOrder` is good, `doStuff` is forbidden
- Functions do one thing — if you cannot describe a function in one sentence without "and", split it
- Files are organized — related code lives together, unrelated code lives apart
- Complexity is bounded — cyclomatic complexity per function stays under 10
- Dependencies are explicit — no hidden global state, no magic
- Tests document behavior — a failing test explains what broke and why
- Comments explain why, not what — the code already shows what

---

## Readable Code

Code is read 10x more than it is written. Optimize for the reader, not the writer.

**Enforcement**:
- Prefer clarity over cleverness — a 5-line obvious solution beats a 1-line clever solution
- Prefer named constants over magic numbers — `MAX_RETRIES = 3` beats `3`
- Prefer early returns over nested conditionals — guard clauses over arrow code
- Prefer positive conditions over negated ones — `if (isValid)` over `if (!isInvalid)`
- Prefer small functions over large ones — under 30 lines, ideally under 15
- Prefer pure functions over side effects — testability and predictability follow
- Prefer composition over inheritance — flexible, testable, understandable

---

## Reusable Components

Build once, use everywhere. Reusability is not about generic abstractions — it is about identifying the true seams in the system and extracting at those seams.

**Enforcement**:
- Extract a component only when it is used 3+ times with the same shape
- Never extract a component for "future reuse" — extract when reuse exists
- Components have a single, clear responsibility
- Components have a stable, well-documented public interface
- Components are tested in isolation, with their dependencies mocked
- Components never reach across feature boundaries — cross-feature communication happens through contracts

---

## Comprehensive Documentation

Code without documentation is unfinished. Documentation is not a separate phase — it is part of writing code.

**Enforcement**:
- Every public API has a doc comment explaining what it does, what its parameters mean, what it returns, and what errors it throws
- Every non-obvious decision has an inline comment explaining why
- Every module has a README explaining its purpose, boundaries, and usage
- Every project has a top-level README explaining how to install, configure, run, and test
- Every architectural decision is recorded in an ADR (Architecture Decision Record)
- Every breaking change is documented in the CHANGELOG
- Documentation is version-controlled alongside code — never in a separate wiki

---

These 15 principles are the constitution of the Claude Code Ultimate Pack. Every skill enforces them. Every line of code produced by every skill respects them. Violations are bugs, not stylistic preferences.
