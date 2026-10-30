# Engineering Best Practices

Principles that recur across the skills in this pack. They are guidelines for judgment, not rules to apply mechanically: each skill gives the specific, version-checked details for its technology, and a project's own conventions come first. Where a topic has an owner, the section links to the skill that covers it in depth (see the [skill index](./skill-index.md)).

## Contents

1. [Design principles](#design-principles)
2. [Structure](#structure)
3. [Quality attributes](#quality-attributes)
4. [Delivery](#delivery)
5. [Working with the skills](#working-with-the-skills)

## Design principles

**Single responsibility.** A module should have one reason to change. If a class handles authentication, logging and email, split it. Test: how many unrelated changes could force an edit here?

**Open for extension, closed for modification.** Add behavior through composition, strategies or plugins rather than editing working code on every new case. Do not build extension points before a second case exists.

**Substitutability.** A subtype must honor its parent's contract. A subclass that throws "not implemented" for inherited methods signals the wrong hierarchy; prefer composition.

**Small interfaces.** Clients should not depend on methods they do not use. Split wide interfaces by role.

**Depend on abstractions at boundaries.** Business logic should receive its collaborators (database, clock, HTTP client) through constructors or parameters instead of creating them.

**DRY applies to knowledge, not to text.** A business rule should live in one place. Two code fragments that look alike but change for different reasons are not duplication; extract after the third real use, not before.

**KISS and YAGNI.** Choose the simplest design that meets today's stated requirements. Add flexibility when a concrete, scheduled requirement asks for it. A boring solution that the team understands beats a clever one.

## Structure

**Dependencies point inward.** Domain rules depend on nothing; application use cases depend on the domain; frameworks, databases and UI sit at the edge and implement interfaces the inner layers define. See `clean-architecture-expert`, `ddd-expert` and `solution-architect`.

**Organize by feature.** Keep the controller, service, repository, schema and tests for one feature together so a change to orders touches the `orders/` folder:

```text
src/
├── features/
│   ├── orders/      # controller, service, repository, schema, tests
│   └── users/
└── shared/          # truly cross-cutting code only
```

**Make module boundaries explicit.** Each module has an owner, a public interface and private internals. Cross-module calls go through documented contracts, and breaking changes get a deprecation period. Service boundaries and data ownership are covered by `microservices-expert` and `system-design-expert`.

## Quality attributes

**Production readiness.** Code is finished when it is tested, observable, deployable and understandable to someone other than its author. Check: tests at the right levels, structured logs with correlation IDs, metrics for rate, errors and duration, a defined failure behavior for every external call, a rollout and rollback plan, and a capacity estimate.

**Security by default.** Treat all input as untrusted, validate at the boundary, use parameterized queries and output encoding, enforce authentication and authorization on the server, keep secrets out of code and images, and apply least privilege. See `secure-coding-expert`, `api-security-expert`, `authentication-expert` and `authorization-expert`.

**Measure before optimizing.** Set a target (for example p95 latency or Core Web Vitals thresholds), profile, fix the largest cost, and measure again. Front-end metrics: `core-web-vitals-expert`. Back-end throughput and scaling: `scalability-expert`. Data access: `postgresql-expert`, `redis-expert`.

**Plan for scale where it is cheap.** Keep services stateless, make writes idempotent, put timeouts and retries with backoff on remote calls, and move slow work to queues. Do not shard or split services before measurements show the need.

**Maintainability and readability.** Name things after the domain, keep functions short enough to read at once, comment why rather than what, and keep the formatter and linter in CI. Review with `code-review-expert`; restructure safely with `refactoring-expert`.

**Reusable components.** Build components around a clear contract with sensible defaults and tests. Share code when three call sites need the same behavior, not because two look similar.

**Documentation.** Keep a README that gets a new developer running, document public interfaces and decisions (short architecture decision records), and keep a runbook for common incidents. Update docs in the same change as the code.

## Delivery

- **Version control:** small, reviewed changes; one logical change per commit; see `git-expert`.
- **Automation:** build, lint, test and scan on every pull request; deploy from the same pipeline. See `cicd-expert`.
- **Environments:** reproducible from version control (`terraform-expert`, `docker-expert`, `kubernetes-expert`).
- **Testing:** many fast unit tests, fewer integration tests, a small set of end-to-end tests for critical paths. See `unit-testing-expert`, `integration-testing-expert`, `e2e-testing-expert` and `playwright-expert`.
- **Releases:** roll out gradually when risk is high, watch the metrics, and keep a tested rollback.

## Working with the skills

- State your constraints (scale, latency target, compliance needs, team size, deadline); skills choose differently when they are known.
- Treat a skill's `Verified against` line as the version baseline and check it against what your project runs.
- Ask for trade-offs and for the review checklist of the relevant skill when you want the reasoning, for example "check this against the review checklist in `nestjs-expert`".
- When skills disagree with your project's established conventions, say so; consistency inside a project usually matters more than a general rule.
