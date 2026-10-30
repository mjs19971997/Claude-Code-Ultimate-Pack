---
name: solution-architect
description: >-
  Designs end-to-end solutions across systems, vendors, clouds and teams: NFR elicitation, build-vs-buy, integration topology, migration strategy, cost (TCO) and risk, documented with C4 diagrams and ADRs. Also covers software architecture (architectural styles, ISO 25010 quality attributes, fitness functions) and enterprise architecture (TOGAF ADM, capability maps, TIME portfolio rationalization, ARB governance, technology radar). Use when choosing an architectural style, writing an ADR or solution design document, quantifying NFRs, comparing build/buy/SaaS options, planning a strangler-fig migration, modeling TCO, or setting architecture principles and governance. Not for distributed-systems internals such as replication or consensus (use system-design-expert), layering inside one codebase (use clean-architecture-expert), domain modeling (use ddd-expert), service decomposition (use microservices-expert), or capacity and load (use scalability-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Solution Architect

This skill covers the design of a solution that spans several systems, vendors or organizational boundaries: turning business capabilities and non-functional requirements into a feasible, costed, operable design and a safe migration path. It also covers the two neighbouring levels that used to be separate skills: software architecture (the structure and quality attributes of one system) and enterprise architecture (portfolio, principles and governance across many systems). It does not cover the internals of distributed data systems, code-level layering, domain modeling, microservice boundaries or load engineering; those have their own skills.

> Verified against ISO/IEC 25010:2023, ISO/IEC/IEEE 42010:2022, the TOGAF Standard 10th Edition, the C4 model (c4model.com) and the AWS Well-Architected Framework (six pillars) (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Architecture Standards](#5-architecture-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security and Compliance](#10-security-and-compliance)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

Three levels of architecture work, with different questions:

| Level | Question | Typical artifacts |
|-------|----------|-------------------|
| Enterprise | Which capabilities, systems and standards should the organization have over 3-5 years? | Capability map, principles, technology radar, portfolio (TIME) classification, roadmap |
| Solution | How do we deliver this business capability across systems, vendors and teams? | Solution design document, NFR register, integration topology, migration plan, TCO, risk register |
| Software | How is one system structured so it meets its quality attributes? | C4 container and component views, ADRs, quality attribute scenarios, fitness functions |

This file focuses on the solution level. Details for the other two levels are in [references/software-architecture.md](references/software-architecture.md) and [references/enterprise-architecture.md](references/enterprise-architecture.md).

## 2. Core Expertise

- **Discovery:** stakeholder map, capability analysis, current state, target state, gap analysis.
- **NFRs as quality attribute scenarios:** source, stimulus, environment, artifact, response, response measure. Use the ISO/IEC 25010:2023 product quality model as a checklist: functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility, safety.
- **Availability and recovery targets:** SLO, RTO, RPO, error budget; how each maps to a mechanism (multi-AZ, replication, backups, failover).
- **Build vs buy vs SaaS:** differentiation, total cost of ownership, switching cost, exit plan, vendor risk.
- **Integration styles** (Hohpe and Woolf): file transfer, shared database, remote procedure invocation, messaging; plus APIs across organizational boundaries (versioning, auth, rate limits, idempotency, deprecation).
- **Migration strategies:** strangler fig, parallel run, phased cutover, big bang, each with its risk profile and rollback options.
- **Cloud service selection:** compute, storage, data, messaging and networking options across AWS, Azure and GCP; managed vs self-hosted trade-offs; Well-Architected reviews (operational excellence, security, reliability, performance efficiency, cost optimization, sustainability).
- **Identity across boundaries:** OIDC, SAML, SCIM provisioning, workload identity, propagation of the end-user identity to downstream services.
- **Compliance and data residency:** data classification, GDPR Chapter V (Articles 44-50) for cross-border transfers, HIPAA, PCI DSS scope reduction, SOC 2 and ISO/IEC 27001 control mapping.
- **Cost:** TCO over a fixed horizon (build, run, change, exit), unit economics (cost per order, per tenant), FinOps tagging.
- **Risk register:** probability, impact, mitigation, owner, residual risk, acceptance by the business.

## 3. Workflow

1. **Name the capability and the sponsor.** If neither can be named, the solution is premature.
2. **Map stakeholders and concerns:** sponsor, users, operations, security, finance, legal, data protection.
3. **Document the current state honestly,** including legacy constraints, contracts, skills gaps and existing lock-in.
4. **Elicit NFRs as measurable scenarios** and get the business to ratify them. "Fast" and "highly available" are not requirements; "99% of checkouts complete in under 2 s at 3x normal load" is.
5. **Generate options:** at least one buy or SaaS option, one build option and one hybrid, where they exist.
6. **Score options** against NFRs, cost, risk, time to value and strategic fit. Record sensitivity points (decisions that one NFR depends on) and trade-off points (decisions that affect several NFRs in opposite directions).
7. **Design the selected option:** C4 context and container views, integration contracts, identity flow, data flow with classification, deployment and DR topology.
8. **Plan the migration** in reversible steps, each with acceptance criteria and a rollback trigger.
9. **Build the TCO and the risk register;** review them with finance and with the risk owners.
10. **Record decisions as ADRs** and assemble the solution design document; take it through architecture review.
11. **Stay with delivery:** calibrate estimates with the engineering leads, keep ADRs current, and check after go-live that each NFR is met in production.

## 4. Decision Rules

- **Buy** a capability that does not differentiate the business when a product meets the NFRs; **build** what differentiates. Always price the exit (data export, contract terms, re-platforming).
- **Prefer managed services** when the team lacks the operational depth to run the self-hosted equivalent; operational burden is a recurring cost that TCO models often omit.
- **Single region, multiple availability zones** is the default when it meets RTO and RPO. Go multi-region when the business RTO or a regulation requires surviving a regional outage, and quantify the added cost and consistency trade-offs.
- **Synchronous integration** when the caller needs the answer to proceed; **asynchronous messaging** when the producer should not depend on the consumer's availability or pace.
- **Never trade below a ratified SLO to save cost** without written business acceptance; record the decision as an ADR.
- **Time to market vs structural quality:** take the shortcut only with an explicit, tracked debt item and an owner.
- **Safe migration over fast migration** for regulated data and load-bearing systems; failed cutovers cost more trust than late launches.
- **Open standards at boundaries** (OpenAPI, AsyncAPI, CloudEvents, OIDC, SQL, OpenTelemetry) reduce lock-in where portability matters; do not wrap every vendor API by reflex when portability has no business value.

## 5. Architecture Standards

- Define SLO, RTO and RPO before selecting services; each service choice must trace to the NFR it satisfies.
- Every API that crosses a team or organization boundary has a machine-readable contract (OpenAPI or AsyncAPI), a versioning policy and a deprecation window.
- Every remote dependency has a timeout, bounded retries with backoff and jitter, and a defined behaviour when it is down (fallback, queue, or fail fast).
- Limit blast radius: a failing component must not take down unrelated capabilities (separate accounts or projects, cells, bulkheads, quotas).
- Infrastructure is defined as code; configuration is externalized; secrets come from a secrets manager at runtime.
- Personal data is classified, stored only in permitted regions, encrypted at rest with managed keys, and its flows are drawn on the data-flow diagram.
- Name systems after the capability they serve (`order-fulfillment`), not the technology (`kafka-pipeline`).
- Diagrams follow C4 notation with a legend; every arrow is labelled with intent and protocol.

## 6. Project Structure

One repository layout for solution-level artifacts (code lives in the delivery repositories):

```
checkout-solution/
  README.md                       # One-page summary: capability, sponsor, status
  sdd.md                          # Solution design document
  nfr-register.md                 # Quantified NFR scenarios with owners
  diagrams/
    c4-context.dsl                # Structurizr DSL or another C4 tool
    c4-container.dsl
    data-flow.md                  # PII flows and classification
  adr/
    0001-record-architecture-decisions.md
    0002-use-managed-message-broker.md
  integration/
    openapi/checkout.yaml
    asyncapi/order-events.yaml
  migration/
    plan.md                       # Phases, acceptance criteria, rollback triggers
    cutover-runbook.md
  risk/
    risk-register.md
    dr-plan.md
  cost/
    tco-model.md                  # Assumptions, horizon, unit economics
```

## 7. Design Patterns

| Pattern | Use when | Avoid when |
|---------|----------|-----------|
| API gateway | Several backends share edge concerns (TLS, auth, quotas, routing) | One backend with no shared concerns |
| Backend for frontend | Web, mobile and partner clients need different shapes | One client, or a generic API already fits |
| Strangler fig | Replacing a legacy system incrementally behind a routing layer | The legacy system is small enough to replace in one step |
| Anti-corruption layer | A legacy or vendor model would leak into your model | The external model already matches yours |
| Transactional outbox | A database change and an event must be published together | Eventual consistency is unacceptable for the flow |
| Saga | A business transaction spans services without a shared transaction | It fits inside one service's database |
| Claim check | Message payloads are large; pass a reference to object storage | Payloads are small |
| Parallel run | Correctness of a replacement must be proven on real traffic before cutover | Side effects cannot be duplicated safely |

Pattern internals (outbox relays, saga coordination, idempotent consumers) are covered in system-design-expert and microservices-expert.

## 8. Best Practices

- Quantify every NFR and give it an owner and a verification method before choosing technology.
- Model TCO over the same horizon for every option: build, run, change, support, exit. The build cost is usually the smallest share.
- Keep a living risk register; a risk without an owner is unmanaged.
- Run a DR exercise before go-live and on a schedule; an untested DR plan is an assumption.
- Run a Well-Architected style review against the chosen cloud's framework and record exceptions as ADRs.
- Keep the solution design document short and link to ADRs for rationale; update ADR status rather than rewriting history.
- Decouple deploy from release with feature flags for risky cutovers.

## 9. Performance

- Set end-to-end latency budgets from the user-facing SLO and allocate them per hop; external calls usually dominate.
- Keep synchronous external calls off the hot path where possible: cache, precompute, or move to asynchronous processing.
- Size for peak with headroom and verify with load tests before go-live; detailed capacity work belongs to scalability-expert.
- Place data close to its heaviest consumers; cross-region calls add tens to hundreds of milliseconds per round trip.

## 10. Security and Compliance

- Authenticate every entry point; authorize at the resource level, not only at the route.
- Propagate the end-user identity (or a token exchanged for it) to downstream services; use workload identity for service-to-service calls instead of shared static keys.
- Encrypt in transit everywhere, including internal traffic in regulated environments (mTLS or equivalent).
- Reduce compliance scope by design: tokenize card data at the payment provider so it never enters your systems; minimize the personal data you collect.
- Map regulatory controls to architectural mechanisms in a traceable table; review it with the compliance owner.
- Audit-log privileged actions in a tamper-evident store with retention set by policy.

## 11. Testing

- Every NFR scenario has at least one automated or scheduled verification (load test, failover test, restore test, security scan).
- Use consumer-driven contract tests for APIs and events that cross team boundaries.
- Rehearse migrations on production-sized, anonymized data in a staging environment; time the cutover and the rollback.
- Test DR by actually failing over and restoring, and record achieved RTO and RPO against targets.
- Use synthetic or anonymized data outside production.

## 12. Review Checklist

- [ ] Capability, sponsor and stakeholders are named; concerns are recorded.
- [ ] NFRs are measurable scenarios with owners and verification methods.
- [ ] At least two real options were compared; the rejected ones are in the ADR.
- [ ] Each major service choice traces to an NFR, a cost line and a risk entry.
- [ ] Integration contracts are versioned; timeouts, retries and failure behaviour are defined.
- [ ] Identity flow and data flow (with classification and residency) are drawn.
- [ ] Migration steps are reversible, with acceptance criteria and rollback triggers.
- [ ] TCO covers build, run, change and exit over a stated horizon, with assumptions.
- [ ] DR design states RTO and RPO and how they are tested.
- [ ] Residual risks are accepted in writing by the business owner.
- [ ] Refactoring or re-platforming steps are motivated by a measured pain point (cost, incidents, lead time), not by fashion.

## 13. Production Notes

- Track the NFRs as SLOs after launch and compare achieved RTO, RPO, latency and cost per unit with the design targets; feed gaps back into the risk register and ADRs.
- Tag every cloud resource with capability, environment and owner so cost can be attributed per capability.
- Hold a post-implementation review 30-90 days after go-live: what met the targets, what did not, which assumptions in the TCO were wrong.

## 14. Examples

### NFR register entries

```markdown
| ID      | Scenario                                      | Response measure                                   | Owner         | Verification                     |
|---------|-----------------------------------------------|----------------------------------------------------|---------------|----------------------------------|
| NFR-014 | Customer submits checkout at 3x normal load   | 99% complete in < 2 s; 99.9% in < 5 s              | Checkout team | Load test in staging before each release |
| NFR-015 | Payment provider unavailable in one region    | Orders accepted and queued; charged within 15 min of recovery | Checkout team | Failure-injection test each quarter |
| NFR-016 | Loss of one availability zone                 | RPO 0 for orders, RTO 5 min                        | Platform team | Failover exercise each quarter   |
| NFR-017 | Card data handling                            | No card numbers stored or logged; tokenized at the provider | Security team | Annual PCI DSS assessment |
```

### TCO comparison (illustrative figures)

```text
Horizon: 3 years. All figures are assumptions to be replaced with quotes and estimates.

Option A - build on managed cloud services
  Build:   6 engineers x 24 weeks x 4,000/week        = 576,000
  Run:     infrastructure 150,000/yr + on-call 60,000/yr = 210,000/yr -> 630,000
  Change:  1.5 engineers ongoing x 200,000/yr         = 300,000/yr -> 900,000
  Total 3-year TCO                                    = 2,106,000

Option B - SaaS checkout product
  Integration build: 2 engineers x 10 weeks x 4,000   = 80,000
  Subscription: 0.02 per order x 40M orders/yr        = 800,000/yr -> 2,400,000
  Change: 0.5 engineer x 200,000/yr                   = 100,000/yr -> 300,000
  Exit cost (data export, re-platform), estimated     = 250,000
  Total 3-year TCO including exit                     = 3,030,000

Sensitivity: Option B becomes cheaper below ~25M orders/yr.
Decision recorded in ADR-0004 together with the non-cost factors
(differentiation, vendor lock-in, time to market).
```

### Strangler-fig migration step

```yaml
phase: 3
capability: order-cancellation
routing:
  mechanism: feature-flag            # evaluated in the routing layer
  flag: checkout.use_new_cancel_service
  rollout:
    - cohort: internal-users
      percent: 100
      min_duration: 24h
    - cohort: all-customers
      percent: 5
      min_duration: 72h
    - cohort: all-customers
      percent: 100
acceptance:
  - cancel p99 latency <= legacy p99 + 10%
  - cancel error rate < 0.1%
  - nightly reconciliation finds no orders missing between old and new stores
rollback:
  trigger: error rate > 1% for 5 min OR reconciliation mismatch
  action: switch flag off; legacy path serves 100% of traffic
owner: checkout-team
```

## 15. Common Mistakes

- **Qualitative NFRs.** "Fast and reliable" cannot be tested, so technology choices become arbitrary. Write scenarios with numbers and owners.
- **Designing without operations, security or finance.** Their constraints surface after launch at much higher cost. Include them from discovery.
- **One option only.** Without alternatives the ADR has no rationale. Compare at least two real options, including buy where it exists.
- **Big-bang migration.** Failure modes are unbounded and rollback is often impossible. Use strangler fig or parallel run with reversible steps.
- **Over-engineered integration.** A broker, a stream and an ESB where one HTTP call would do; operations cost dominates. Match the integration style to the coupling.
- **Single region without acknowledgment.** Fine for many systems, but the business must accept the regional-outage risk explicitly.
- **Missing cost model.** Managed services that look cheap at design time scale with usage; model unit economics and watch them in production.
- **Ignoring data residency.** Storing personal data outside permitted regions without a valid transfer mechanism makes the design non-compliant from the start.
- **Speculative scale.** Designing for 100x current load costs money now and rarely matches the future. Design for the next 12-18 months and record the trigger for the next step.
- **Ivory-tower architecture.** Decisions handed down without engineering input get worked around. Co-author ADRs with the teams that build and run the system.

## 16. References

- [references/software-architecture.md](references/software-architecture.md): architectural styles, quality attribute scenarios, ATAM, ADR template, C4 and arc42, fitness functions with dependency-cruiser and ArchUnit.
- [references/enterprise-architecture.md](references/enterprise-architecture.md): TOGAF ADM, capability maps, TIME portfolio classification, principles and standards catalog, ARB and exceptions, technology radar, operating models.
