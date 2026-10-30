# Enterprise Architecture

Architecture across the whole portfolio: which capabilities the organization needs, which systems deliver them, which standards they follow, and how decisions are governed. Use it when the question is about many systems at once (modernization programs, mergers, rationalization, standards), not about one solution.

## TOGAF ADM

The TOGAF Standard, 10th Edition (The Open Group, 2022) splits a stable core (fundamental content) from series guides. Its Architecture Development Method is a cycle:

| Phase | Purpose |
|-------|---------|
| Preliminary | Set up the architecture capability: principles, governance, tools |
| A. Architecture Vision | Scope, stakeholders, business goals, statement of architecture work |
| B. Business Architecture | Capabilities, value streams, organization, processes |
| C. Information Systems Architectures | Data and application architecture |
| D. Technology Architecture | Platforms, infrastructure, technology standards |
| E. Opportunities and Solutions | Work packages, transition architectures, build/buy |
| F. Migration Planning | Sequenced, costed roadmap |
| G. Implementation Governance | Architecture contracts and compliance reviews during delivery |
| H. Architecture Change Management | Monitor change drivers; decide when to start a new cycle |
| Requirements Management | Central, runs throughout all phases |

Tailor it: most organizations run a light version per initiative rather than the full method. The Zachman Framework (six interrogatives: what, how, where, who, when, why; by six audience perspectives) is an ontology for classifying artifacts, not a process; it complements the ADM.

## Business capability map

- A capability is what the business does (`Order Management`, `Pricing`), independent of who does it or how. Keep it stable across reorganizations.
- Use 2-3 levels; map every application to the capabilities it supports.
- Heat-map capabilities by strategic importance and current maturity or pain to prioritize investment.
- Give capabilities stable IDs (`sales.lead-management`) so roadmaps, systems and budgets can reference them.

## Application portfolio: TIME

Gartner's TIME model classifies each application by business value and technical fit:

| Class | Business value | Technical fit | Action |
|-------|----------------|---------------|--------|
| Tolerate | Low | High | Keep running at minimal cost |
| Invest | High | High | Extend and improve |
| Migrate | High | Low | Move to a better platform or replacement |
| Eliminate | Low | Low | Retire; plan data archival and decommissioning |

Every Migrate or Eliminate entry needs a funded owner, a target date and a decommissioning plan; otherwise the review changes nothing.

## Principles and standards catalog

Number, date and own every principle. Each one has a statement, rationale, implications and a compliance check.

```markdown
# P-014: Events are versioned contracts

Statement: Events that cross system boundaries are registered in the event
catalog with a versioned schema before any producer ships.

Rationale: Unregistered events create hidden coupling; schema changes break
consumers silently.

Implications:
- Producers publish only registered event types.
- Schema changes follow backward-compatible evolution rules in the schema registry.
- Consumers are idempotent because delivery is at least once.

Compliance check: the CI step rejects a publish call whose event type is not
registered; the architecture review samples new events each quarter.
```

Standards (`S-007: New OLTP workloads use PostgreSQL`) are narrower than principles and name concrete technologies, formats or protocols, with an exception process.

## Governance: architecture review board

- Charter: membership (architecture, security, operations, a business representative), scope (what must come to the board), decision rights, turnaround target.
- Review proposals against principles, standards and the radar; outcomes are approve, approve with conditions, reject, or grant a time-boxed exception (waiver) with an owner and expiry.
- Track the exception rate; frequent exceptions to the same principle mean the principle needs revision.
- Govern irreversible decisions (identity, data model, core platforms) more tightly than reversible ones (internal tools, UI libraries).
- Keep decisions in a searchable log; an undocumented decision is not a decision.

## Technology radar

Rings (as popularized by Thoughtworks): **Adopt** (default choice), **Trial** (use on real projects with care), **Assess** (explore), **Hold** (do not start new work with it). Each entry has a date, owner and rationale; review on a fixed cadence and move or remove entries that have sat in Assess too long.

```markdown
# Radar 2026-Q3: PostgreSQL 18

Ring: Adopt (new OLTP workloads)
Owner: Database platform team
Rationale: Matches our workload profile; the platform team operates it with
automated backups, upgrades and monitoring.
Action: New services use PostgreSQL 18. Existing clusters upgrade during
scheduled maintenance; check the PostgreSQL versioning policy for end-of-life
dates of older majors before planning.
```

## Operating model

Ross, Weill and Robertson (Enterprise Architecture as Strategy) describe four operating models by the degree of business-process integration and standardization:

| Model | Integration | Standardization | Architecture emphasis |
|-------|-------------|-----------------|------------------------|
| Diversification | Low | Low | Shared infrastructure services only |
| Coordination | High | Low | Shared data and integration |
| Replication | Low | High | Standard processes and applications per unit |
| Unification | High | High | Enterprise-wide processes and data |

Choose the model with business leadership; it decides what to centralize.

## Centralize vs federate

- Centralize platform capabilities that need consistency: identity, observability, CI/CD, secrets, network and landing zones.
- Federate domain decisions: business logic, user experience, team-internal tooling.
- Standardize protocols at boundaries (OIDC, OpenAPI, AsyncAPI, CloudEvents, OpenTelemetry) rather than mandating one framework everywhere.

## FinOps

- Allocate cost to capabilities and owners through mandatory resource tags; unattributed spend is a finding.
- Report showback (or chargeback) monthly; watch unit economics such as cost per order or per active customer.
- Manage commitments (reserved capacity, savings plans) centrally against measured baselines.

## Common mistakes

- **Capability map mirrors the org chart:** the next reorganization invalidates it. Model business functions instead.
- **Standards without enforcement:** a catalog nobody checks becomes shelfware. Every standard needs a compliance check.
- **Governance theater:** a board that approves everything, or one so slow that teams route around it. Publish a turnaround target and real rejection criteria.
- **Over-standardization:** one mandated framework for every context blocks good local choices. Standardize cross-cutting concerns and interfaces.
- **Portfolio reviews without decommissioning:** Migrate and Eliminate labels with no funded plan keep consuming budget.
