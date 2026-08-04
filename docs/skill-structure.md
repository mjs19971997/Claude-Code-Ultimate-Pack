# Skill Structure Specification

This document defines the mandatory 30-section anatomy that every skill file in the Claude Code Ultimate Pack must follow. This specification is normative — deviations require maintainer approval.

---

## Table of Contents

1. [Why a Fixed Anatomy](#why-a-fixed-anatomy)
2. [File Header](#file-header)
3. [The 30 Sections](#the-30-sections)
4. [Section Specifications](#section-specifications)
5. [Formatting Rules](#formatting-rules)
6. [Validation Checklist](#validation-checklist)

---

## Why a Fixed Anatomy

A fixed anatomy serves three purposes:

1. **Predictability** — any engineer can open any skill and immediately know where to find what they need
2. **Completeness** — the 30 sections are derived from real-world engineering dimensions; omitting any one creates a blind spot
3. **Machine-readability** — tooling can parse skills uniformly, extract sections, and compose workflows

The anatomy was designed by surveying what dimensions a senior engineer considers when making a production decision: who they are, what they are accountable for, how they think, how they decide, what rules they follow, what mistakes they avoid, how they verify their work, and how they communicate. The 30 sections capture every one of these dimensions.

---

## File Header

Every skill file begins with this header:

```markdown
# Skill: <Skill Name>

> <One-sentence description>

**Domain**: <domain>
**Role Level**: <Senior | Staff | Principal>
**File**: `<domain>/<skill-name>.md`
```

The header is followed by a horizontal rule and the table of contents, then the 30 sections in order.

---

## The 30 Sections

In strict order:

1. Role
2. Mission
3. Core Expertise
4. Responsibilities
5. Thinking Process
6. Decision Making Rules
7. Architecture Rules
8. Coding Standards
9. Naming Conventions
10. Folder Structure
11. Project Structure
12. Design Patterns
13. Best Practices
14. Anti Patterns
15. Performance Rules
16. Security Rules
17. Testing Strategy
18. Documentation Standards
19. Code Review Checklist
20. Refactoring Checklist
21. Deployment Checklist
22. Production Checklist
23. Logging Strategy
24. Monitoring Strategy
25. Error Handling
26. Examples
27. Common Mistakes
28. Professional Workflow
29. Response Style
30. Output Format

---

## Section Specifications

### 1. Role

The exact persona Claude Code adopts. Must specify:
- The technology or discipline
- The seniority level (Senior, Staff, Principal)
- The years of experience (always 20+)
- The operating context (production systems, enterprise scale, etc.)

**Minimum length**: 5 lines.

### 2. Mission

A single-paragraph statement of the skill's purpose. Must answer: *what does this skill produce, for whom, and to what standard?*

**Minimum length**: 3 lines.

### 3. Core Expertise

A bullet list of the knowledge domains the skill masters. Each item must be specific (not "JavaScript" but "JavaScript event loop, closures, prototypes, async/await, generators, iterators").

**Minimum length**: 10 bullets.

### 4. Responsibilities

A bullet list of what the skill is accountable for delivering. phrased as "I am responsible for..." statements.

**Minimum length**: 8 bullets.

### 5. Thinking Process

A numbered, step-by-step reasoning framework the skill follows for every request. Must cover: understanding the request, gathering context, evaluating options, making decisions, implementing, verifying.

**Minimum length**: 8 steps.

### 6. Decision Making Rules

Trade-off resolution rules. Each rule must be of the form "When X and Y conflict, choose Z because <reason>." Must cover at least: performance vs. readability, security vs. convenience, simplicity vs. flexibility, speed vs. correctness.

**Minimum length**: 8 rules.

### 7. Architecture Rules

Structural constraints on the systems the skill designs. Must cover: layering, dependency direction, module boundaries, separation of concerns.

**Minimum length**: 8 rules.

### 8. Coding Standards

Code-level conventions. Must cover: error handling, async patterns, immutability, null/undefined handling, function length, file length, parameter count.

**Minimum length**: 10 rules.

### 9. Naming Conventions

Naming rules for every construct in the technology: variables, functions, classes, files, directories, types, interfaces, constants, enums.

**Minimum length**: 10 rules.

### 10. Folder Structure

The canonical directory layout for a project in this technology. Must be presented as a tree with comments explaining each directory.

**Minimum length**: 20 lines including comments.

### 11. Project Structure

End-to-end project organization, including configuration files, environment files, test directories, build output, and documentation. Must include a tree and a paragraph explaining the organization.

**Minimum length**: 25 lines.

### 12. Design Patterns

Patterns to apply and when. Each pattern must include: name, when to use, when not to use, and a one-line code sketch.

**Minimum length**: 6 patterns.

### 13. Best Practices

Proven approaches to adopt. Must be specific and actionable, not generic platitudes.

**Minimum length**: 10 practices.

### 14. Anti Patterns

Mistakes to refuse and explain why. Each anti-pattern must include: name, why it is wrong, and the correct alternative.

**Minimum length**: 5 anti-patterns.

### 15. Performance Rules

Performance constraints and optimizations specific to the technology. Must cover: latency, throughput, memory, network, rendering (where applicable).

**Minimum length**: 8 rules.

### 16. Security Rules

Security constraints and hardening specific to the technology. Must reference relevant standards (OWASP, CIS, NIST) where applicable.

**Minimum length**: 8 rules.

### 17. Testing Strategy

The testing pyramid for this technology: what to test at each level, what coverage to target, what tools to use, what to mock, what not to mock.

**Minimum length**: 10 rules.

### 18. Documentation Standards

Documentation requirements: what must be documented, in what format, with what level of detail. Must cover: code comments, function docs, architecture docs, README, API docs.

**Minimum length**: 8 rules.

### 19. Code Review Checklist

A checklist of items to verify before approving a pull request. Each item must be a yes/no question.

**Minimum length**: 15 items.

### 20. Refactoring Checklist

A checklist for safe refactoring. Must cover: test coverage verification, behavior preservation, incremental steps, rollback plan.

**Minimum length**: 10 items.

### 21. Deployment Checklist

A checklist for pre-deployment verification. Must cover: environment variables, secrets, database migrations, feature flags, health checks, rollback plan.

**Minimum length**: 15 items.

### 22. Production Checklist

A checklist for production-readiness. Must cover: monitoring, alerting, logging, dashboards, runbooks, capacity planning, disaster recovery.

**Minimum length**: 15 items.

### 23. Logging Strategy

What to log, when, at what level, in what format. Must cover: structured logging, correlation IDs, sensitive data redaction, log levels, log retention.

**Minimum length**: 10 rules.

### 24. Monitoring Strategy

Metrics, alerts, and dashboards. Must cover: RED metrics (Rate, Errors, Duration), USE metrics (Utilization, Saturation, Errors), alerting thresholds, dashboard layout.

**Minimum length**: 10 rules.

### 25. Error Handling

Error handling patterns and rules. Must cover: error propagation, error classification, retry logic, circuit breakers, fallbacks, user-facing error messages.

**Minimum length**: 10 rules.

### 26. Examples

Concrete code examples demonstrating the skill in action. Must include at least 3 examples, each syntactically valid and production-ready.

**Minimum length**: 3 examples, each 20+ lines.

### 27. Common Mistakes

Frequently observed errors in the technology. Each mistake must include: the mistake, why it happens, and how to avoid it.

**Minimum length**: 5 mistakes.

### 28. Professional Workflow

End-to-end delivery workflow: from receiving a request to delivering production-ready output. Must cover: requirement analysis, design, implementation, testing, documentation, deployment.

**Minimum length**: 10 steps.

### 29. Response Style

How the skill communicates. Must cover: tone, structure, level of detail, use of code, use of diagrams, when to ask clarifying questions.

**Minimum length**: 8 rules.

### 30. Output Format

The exact structure of every response. Must specify: header, sections, code block format, closing.

**Minimum length**: 10 rules.

---

## Formatting Rules

- **Section headers**: `## <number>. <Section Name>` (level 2, numbered)
- **Subsection headers**: `### <number>.<number> <Subsection Name>` (level 3, numbered)
- **Code blocks**: must specify language: ` ```typescript `, ` ```python `, ` ```bash `, etc.
- **Tables**: used for structured comparisons
- **Bullet lists**: used for enumerations
- **Numbered lists**: used for sequential processes
- **Bold**: used for emphasis on critical rules ("**never**", "**always**")
- **Inline code**: used for code identifiers, file paths, and commands
- **Horizontal rules**: used to separate major sections where appropriate

---

## Validation Checklist

Before a skill can be merged, validate against this checklist:

- [ ] File header present and complete
- [ ] All 30 sections present, in order, with correct numbering
- [ ] Every section meets its minimum length requirement
- [ ] At least 3 code examples in the Examples section
- [ ] All code examples specify a language
- [ ] All code examples are syntactically valid
- [ ] No placeholders, no TODOs, no "TBD"
- [ ] No section shorter than 5 lines (unless inherently list-based)
- [ ] File is between 300 and 1000 lines
- [ ] File uses LF line endings
- [ ] File is UTF-8 encoded
- [ ] File name is lowercase, kebab-case, ends in `.md`

A skill that fails any item on this checklist must not be merged.
