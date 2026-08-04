# Skill Structure Specification

This document defines the mandatory structure of every skill in the Claude Code Ultimate Pack v2.0. It is normative — deviations require maintainer approval.

v2.0 skills follow the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills). This document adds the repository-specific 30-section body anatomy on top of the spec.

---

## Table of Contents

1. [Why a Fixed Anatomy](#why-a-fixed-anatomy)
2. [Filesystem Layout](#filesystem-layout)
3. [YAML Frontmatter](#yaml-frontmatter)
4. [Body Structure](#body-structure)
5. [The 30 Sections](#the-30-sections)
6. [Section Specifications](#section-specifications)
7. [Formatting Rules](#formatting-rules)
8. [Validation Checklist](#validation-checklist)

---

## Why a Fixed Anatomy

A fixed anatomy serves three purposes:

1. **Predictability** — any engineer can open any skill and immediately know where to find what they need.
2. **Completeness** — the 30 sections are derived from real-world engineering dimensions; omitting any one creates a blind spot.
3. **Machine-readability** — tooling can parse skills uniformly, extract sections, and compose workflows.

The anatomy was designed by surveying what dimensions a senior engineer considers when making a production decision: who they are, what they are accountable for, how they think, how they decide, what rules they follow, what mistakes they avoid, how they verify their work, and how they communicate. The 30 sections capture every one of these dimensions.

---

## Filesystem Layout

Per the official spec, each skill is a folder:

```
skills/<skill-name>/
└── SKILL.md                  # required entry point
```

The folder name MUST match the `name` field in YAML frontmatter exactly. The folder name is the skill's canonical identity — it's what users type in `/skill <name>` invocations and what appears in skill indexes.

Optional supporting files:

```
skills/<skill-name>/
├── SKILL.md                  # required
├── scripts/                  # optional — helper scripts Claude can execute
│   └── helper.py
├── resources/                # optional — reference materials Claude reads on demand
│   └── patterns.md
└── templates/                # optional — file templates Claude can copy
    └── starter.ts
```

---

## YAML Frontmatter

Every `SKILL.md` begins with YAML frontmatter delimited by `---` lines:

```yaml
---
name: senior-react-19-engineer
description: >
  Ships production React 19 applications leveraging Actions, the React
  Compiler, Server Components, and concurrent primitives without
  compromising accessibility or performance.

  Use this skill when building web frontends with React, Next.js,
  TypeScript, TailwindCSS, shadcn/ui, Framer Motion, or when addressing
  UI/UX, accessibility, or performance.
license: MIT
version: 1.0.0
---
```

### Field specifications

| Field | Required | Type | Constraints |
|---|---|---|---|
| `name` | yes | string | `^[a-z0-9][a-z0-9-]{0,63}$`. Lowercase letters, digits, hyphens. Max 64 chars. Cannot start with a hyphen. MUST match the folder name. |
| `description` | yes | string (folded scalar `>` recommended) | Substantive — describes **what** the skill does AND **when** to use it. Claude Code reads this at startup and uses it as the auto-activation trigger. Min 40 chars. |
| `license` | yes (in this repo) | string (SPDX identifier) | e.g., `MIT`, `Apache-2.0`. |
| `version` | yes (in this repo) | string (SemVer) | `MAJOR.MINOR.PATCH`. |

### Description best practices

The `description` field is the most important field in the frontmatter. Claude Code reads it at startup to decide whether to auto-activate the skill based on the user's prompt. A weak description means the skill will never activate.

A good description has two paragraphs:

1. **What** — one or two sentences describing the skill's expertise and quality bar. Example: "Ships production React 19 applications leveraging Actions, the React Compiler, Server Components, and concurrent primitives without compromising accessibility or performance."

2. **When** — one sentence starting with "Use this skill when..." listing the trigger conditions. Example: "Use this skill when building web frontends with React, Next.js, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, or when addressing UI/UX, accessibility, or performance."

The two paragraphs are separated by a blank line inside the folded scalar, which YAML parses as a paragraph break.

### What is NOT in the frontmatter

The legacy v1.x metadata block (`**Domain**:`, `**Role Level**:`, `**File**:`) is gone. Domain is encoded in the description's "when" paragraph. Role level is encoded in the `## 1. Role` body section.

---

## Body Structure

After the frontmatter, the body is a markdown document. It must contain:

1. A `## Table of Contents` section listing all 30 sections.
2. The 30 mandatory sections in the exact order specified below.

The body may also contain:

- Additional subsections (`###`) under any of the 30 sections.
- A `## Standard Response Template` section at the end (optional but recommended).

---

## The 30 Sections

In order:

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

Each section uses a `## N. <Title>` header (e.g., `## 1. Role`, `## 14. Anti Patterns`).

---

## Section Specifications

### 1. Role

[MINIMUM: 5 lines]

Defines the persona Claude Code adopts. Includes years of experience, scale of systems shipped, thinking style, and accountability stance. This replaces the v1.x `**Role Level**:` metadata line — the role level (Senior/Staff/Principal) is now embedded in this section's prose.

### 2. Mission

[MINIMUM: 3 lines]

Single-sentence purpose, how it's achieved, and the quality bar.

### 3. Core Expertise

[MINIMUM: 10 bullets]

Specific expertise areas. Each bullet is a dense one-liner (not a one-word tag).

### 4. Responsibilities

[MINIMUM: 8 bullets]

What the skill is accountable for delivering. Written as "I am responsible for ..." statements.

### 5. Thinking Process

[MINIMUM: 8 steps]

Step-by-step reasoning framework. Always: understand → gather context → identify constraints → evaluate options → decide → implement → verify → document.

### 6. Decision Making Rules

[MINIMUM: 8 rules]

Trade-off resolution rules. Format: "When X and Y conflict, choose Z because <reason>".

### 7. Architecture Rules

[MINIMUM: 8 rules]

Structural constraints the skill enforces.

### 8. Coding Standards

[MINIMUM: 10 rules]

Code-level conventions.

### 9. Naming Conventions

[MINIMUM: 10 rules]

Naming rules for every construct: variables, functions, classes, interfaces, types, constants, enums, files, directories, tests.

### 10. Folder Structure

[MINIMUM: 20 lines including comments]

Canonical project layout for the technology, with comments explaining each directory.

### 11. Project Structure

[MINIMUM: 25 lines]

End-to-end project organization including configuration, environment, and build outputs.

### 12. Design Patterns

[MINIMUM: 6 patterns]

For each pattern: name, when to use, when not to use, one-line code sketch.

### 13. Best Practices

[MINIMUM: 10 practices]

Proven approaches to adopt.

### 14. Anti Patterns

[MINIMUM: 5 anti-patterns]

For each anti-pattern: name, why it's wrong, correct alternative.

### 15. Performance Rules

[MINIMUM: 8 rules]

Performance constraints and optimizations.

### 16. Security Rules

[MINIMUM: 8 rules]

Security constraints and hardening.

### 17. Testing Strategy

[MINIMUM: 10 rules]

Testing pyramid and coverage rules.

### 18. Documentation Standards

[MINIMUM: 8 rules]

Documentation requirements.

### 19. Code Review Checklist

[MINIMUM: 15 items]

Pre-merge verification. Markdown checkbox list (`- [ ]`).

### 20. Refactoring Checklist

[MINIMUM: 10 items]

Safe refactoring steps. Markdown checkbox list.

### 21. Deployment Checklist

[MINIMUM: 15 items]

Pre-deployment verification. Markdown checkbox list.

### 22. Production Checklist

[MINIMUM: 15 items]

Production-readiness verification. Markdown checkbox list.

### 23. Logging Strategy

[MINIMUM: 10 rules]

What, when, and how to log.

### 24. Monitoring Strategy

[MINIMUM: 10 rules]

Metrics, alerts, and dashboards.

### 25. Error Handling

[MINIMUM: 10 rules]

Error handling patterns and rules.

### 26. Examples

[MINIMUM: 3 examples, each 20+ lines]

Concrete code examples. Each example has a title, description, and code block with language identifier.

### 27. Common Mistakes

[MINIMUM: 5 mistakes]

For each mistake: title, what it is, why it happens, how to avoid.

### 28. Professional Workflow

[MINIMUM: 10 steps]

End-to-end delivery workflow.

### 29. Response Style

[MINIMUM: 8 rules]

How the skill communicates.

### 30. Output Format

[MINIMUM: 10 rules]

The exact structure of every response.

---

## Formatting Rules

### File encoding

- UTF-8 only.
- LF line endings (no CRLF).
- No byte-order mark (BOM).

### YAML

- Frontmatter delimited by `---` lines.
- Use folded scalar (`>`) for multi-line descriptions.
- Indent continuation lines with two spaces.
- Never include a literal `---` line inside a description (it would terminate the frontmatter).

### Markdown

- Use `##` for section headers (level 2) — matches the 30-section anatomy.
- Use `###` for subsections (level 3).
- Use code blocks with language identifiers: ` ```typescript `.
- Use tables for structured comparisons.
- Use bullet lists for enumerations.
- Use numbered lists for sequential processes.
- Wrap lines at 100 characters where reasonable.

### Code blocks

- All code examples must be syntactically valid.
- All code examples must include error handling where the language expects it.
- All code examples must follow the naming conventions defined in section 9.
- All code examples must be production-ready — no `console.log` debugging, no `// TODO` comments.

### Voice and tone

- Authoritative — write as a principal engineer with 20+ years of experience.
- Imperial — use "always", "never", "must", "must not", "forbidden".
- Concise — every sentence carries weight; no filler.
- Professional — no slang, no humor, no casual language.

### Forbidden phrases

- "you might consider" → use "always" or "must"
- "perhaps" → use "must" or "never"
- "it depends" → specify the exact conditions
- "TODO" → never use; implement the content
- "placeholder" → never use; provide real content
- "in the future" → never use; if it is not needed now, do not write it (YAGNI)

---

## Validation Checklist

Before a skill can be merged, it must pass:

- [ ] Folder name matches the `name` field exactly
- [ ] `name` matches `^[a-z0-9][a-z0-9-]{0,63}$`
- [ ] `description` is non-empty and at least 40 characters
- [ ] `description` describes both **what** and **when**
- [ ] `license` is a valid SPDX identifier
- [ ] `version` is SemVer
- [ ] UTF-8 encoded, LF line endings, no BOM
- [ ] YAML frontmatter parses without error
- [ ] Body has minimum 300 lines, up to 1500 lines where warranted
- [ ] All 30 body sections present, in order, with the exact section headers
- [ ] No `TODO:`, `FIXME:`, or `PLACEHOLDER:` markers in prose
- [ ] No section shorter than 5 lines (unless inherently list-based)
- [ ] At least 3 concrete code examples in the Examples section
- [ ] At least 5 items in every checklist (Code Review, Refactoring, Deployment, Production)
- [ ] At least 5 anti-patterns documented in the Anti Patterns section
- [ ] At least 5 common mistakes documented in the Common Mistakes section
- [ ] Production-ready language throughout — no "you might", no "consider", no "perhaps"
- [ ] Imperial directives — "always", "never", "must", "must not", "forbidden"
- [ ] `python3 scripts/validate_skills.py` reports `Overall pass: True`

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full contribution workflow.
