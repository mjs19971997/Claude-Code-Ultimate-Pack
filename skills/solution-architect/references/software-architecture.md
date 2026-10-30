# Software Architecture

Architecture of a single system: choosing a style, expressing quality attributes, recording decisions and keeping the structure intact as the code evolves. Code-level layering rules are in clean-architecture-expert; domain modeling is in ddd-expert.

## Choosing an architectural style

| Style | Fits when | Costs |
|-------|-----------|-------|
| Modular monolith | One team or a few teams, one deployable, clear module boundaries | Needs enforced module boundaries or it drifts into a big ball of mud |
| Layered | Simple business logic, CRUD-heavy | Logic leaks across layers; database-centric design |
| Hexagonal / clean / onion | Rich domain, many delivery mechanisms or adapters, long life | More files and mapping; overkill for CRUD |
| Microservices | Independent deployability and scaling per capability; several autonomous teams | Distributed failure modes, data consistency, platform and observability cost |
| Event-driven | Many consumers react to business facts; temporal decoupling | Harder debugging, eventual consistency, schema evolution |
| Serverless functions | Spiky or low-volume workloads, glue between managed services | Cold starts, vendor coupling, local testing friction |
| CQRS | Reads and writes differ strongly in shape or scale | Projection maintenance, eventual consistency on reads |
| Event sourcing | Full history has business value (audit, temporal queries, replay) | Event versioning, projection rebuilds, steeper learning curve |

Default: start with a modular monolith and extract a service only when a module needs independent deployment, scaling or ownership. Conway's law applies: the structure that survives is the one that matches team communication.

## Quality attributes

Use the ISO/IEC 25010:2023 product quality model as a checklist: functional suitability, performance efficiency, compatibility, interaction capability (formerly usability), reliability, security, maintainability, flexibility (formerly portability, now including scalability) and safety (new in 2023).

Write each requirement as a quality attribute scenario:

```text
Scenario:         Peak checkout
Source:           Customer browser
Stimulus:         Submits checkout
Environment:      Seasonal peak, 10x normal traffic
Artifact:         Checkout service and payment adapter
Response:         Order confirmed or a clear retry message
Response measure: 99% within 2 s, 99.9% within 5 s; no accepted order lost
```

## ATAM in brief

The Architecture Tradeoff Analysis Method (SEI) evaluates an architecture against prioritized scenarios:

1. Present business drivers and the architecture.
2. Build a utility tree: quality attributes, refined into scenarios, each rated for business importance and technical difficulty.
3. Analyze the architectural approaches against the highest-rated scenarios.
4. Record **sensitivity points** (a property depends heavily on one decision), **trade-off points** (one decision affects several attributes in opposite directions), **risks** and **non-risks**.

A lightweight version (a half-day workshop with the top 5-10 scenarios) is usually enough outside regulated or very large programs.

## Architecture decision records

Keep ADRs short, numbered and immutable; supersede rather than edit accepted decisions. A common template (after Michael Nygard):

```markdown
# ADR-0007: Use event sourcing for the invoice aggregate

## Status
Accepted (2026-03-02). Supersedes: none.

## Context
Auditors need the full state history of any invoice. The current CRUD model
overwrites state; the separate audit table has drifted from the source of truth.

## Decision
Persist invoice changes as an append-only event stream. Build the current-state
read model as a projection. Take a snapshot every 100 events.

## Alternatives considered
1. Audit table written by the application: rejected, it has drifted before.
2. Change data capture from the database log: rejected, it records state, not intent.

## Consequences
Positive: complete history by construction; replay for debugging.
Negative: event schema versioning discipline; projection rebuild tooling to build and run.

## Compliance
Fitness function in CI: every invoice command produces exactly one event, and
replaying the stream reproduces the stored projection.
```

## Documentation

- **C4 model** (Simon Brown): system context, container, component and code diagrams, plus supplementary system landscape, dynamic and deployment diagrams. Keep context and container diagrams current; component diagrams only where they help.
- **arc42**: a section template (goals, constraints, context, solution strategy, building blocks, runtime, deployment, cross-cutting concepts, decisions, quality, risks, glossary) that works well as the home for C4 diagrams and ADR links.
- **ISO/IEC/IEEE 42010:2022**: the conceptual model behind both: stakeholders have concerns, viewpoints frame concerns, views address them. Useful when someone asks "which diagrams do we need?": answer per stakeholder concern.

## Coupling and debt

- **Connascence** (static: name, type, meaning, position, algorithm; dynamic: execution, timing, value, identity) gives a vocabulary for how strongly two pieces of code are coupled. Prefer weaker forms across module boundaries and keep strong forms local.
- **Technical debt quadrant** (Fowler): deliberate or inadvertent, prudent or reckless. Track deliberate prudent debt as backlog items with an owner and a trigger for repayment.

## Fitness functions

Automate structural rules so drift fails the build instead of waiting for a review.

TypeScript or JavaScript with dependency-cruiser (`.dependency-cruiser.js`):

```javascript
/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'domain-must-not-depend-on-outer-layers',
      severity: 'error',
      from: { path: '^src/[^/]+/domain/' },
      to: { path: '^src/[^/]+/(infrastructure|api)/' },
    },
    {
      name: 'no-cross-module-internals',
      comment: 'Modules talk through their public contracts folder or shared kernel only',
      severity: 'error',
      from: { path: '^src/([^/]+)/' },
      to: {
        path: '^src/[^/]+/',
        pathNot: ['^src/$1/', '^src/shared/', '^src/[^/]+/contracts/'],
      },
    },
  ],
};
```

Run it in CI with `npx depcruise src --config .dependency-cruiser.js`.

Java with ArchUnit and JUnit 5:

```java
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

@AnalyzeClasses(packages = "com.example.billing")
class ArchitectureTest {

    @ArchTest
    static final ArchRule domainIsIndependent =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat()
            .resideInAnyPackage("..infrastructure..", "..api..");
}
```

Other useful fitness functions: build time and test time budgets, dependency freshness, bundle size, p99 latency of a benchmark endpoint, and "every public API change updates the OpenAPI file".

## Common anti-patterns

- **Big ball of mud:** no discernible boundaries. Introduce module boundaries and enforce them with a fitness function before refactoring internals.
- **Lasagna architecture:** layers that always change together. Merge them.
- **Inner-platform effect:** re-implementing the platform (a rules engine, a query language) inside the application. Use the platform directly unless you add real domain value.
- **Distributed monolith:** services that must deploy together or share a database. Merge them or give each its own data and contract.
- **Speculative generality:** plugin systems and abstractions with one implementation. Wait for the second or third real case.
