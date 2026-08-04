# Repository Architecture

This document describes the architecture of the Claude Code Ultimate Pack v2.0 repository, the design decisions behind it, and the conventions that govern its structure. v2.0 fully complies with the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).

---

## Table of Contents

1. [Design Goals](#design-goals)
2. [Top-Level Layout](#top-level-layout)
3. [The skills/ Directory](#the-skills-directory)
4. [Skill Folder Anatomy](#skill-folder-anatomy)
5. [YAML Frontmatter Contract](#yaml-frontmatter-contract)
6. [Cross-Cutting Documentation](#cross-cutting-documentation)
7. [Templates and Examples](#templates-and-examples)
8. [Scripts](#scripts)
9. [Versioning Strategy](#versioning-strategy)
10. [Extension Points](#extension-points)
11. [v1.x → v2.0 Architectural Changes](#v1x--v20-architectural-changes)

---

## Design Goals

The repository architecture serves five goals, in priority order:

1. **Spec compliance** — every skill must conform to the official Claude Code Agent Skills specification, with no exceptions.
2. **Discoverability** — any engineer must be able to find the right skill in under 30 seconds, either by browsing the [skill index](./skill-index.md) or by letting Claude Code auto-activate based on the `description` field.
3. **Consistency** — every skill follows the same anatomy, so navigation is predictable.
4. **Composability** — skills can be combined in workflows without conflicts.
5. **Portability** — the repository must work across global, project-local, and submodule installations on Windows, Linux, and macOS.

---

## Top-Level Layout

```
Claude-Code-Ultimate-Pack/
├── README.md
├── INSTALL.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── skills/                # 93 skill folders (flat layout per spec)
│   └── <skill-name>/
│       └── SKILL.md
├── templates/
│   └── skill-template/    # Template skill following the official spec
│       └── SKILL.md
├── docs/
│   ├── architecture.md    # This file
│   ├── skill-structure.md
│   ├── usage-guide.md
│   ├── best-practices.md
│   └── skill-index.md
├── examples/
│   └── example-usage.md
└── scripts/
    ├── migrate_skills.py  # Migration tool (v1.x → v2.0)
    └── validate_skills.py # Spec compliance validator
```

---

## The skills/ Directory

### Flat layout (per official spec)

```
skills/
├── accessibility-expert/
│   └── SKILL.md
├── ai-agent-architect/
│   └── SKILL.md
├── android-kotlin-expert/
│   └── SKILL.md
├── ... (90 more skill folders)
└── ux-designer/
    └── SKILL.md
```

The repository does **not** use domain subdirectories (`skills/frontend/`, `skills/backend/`, etc.). This matches Anthropic's reference [`anthropics/skills`](https://github.com/anthropics/skills) repository and the official specification, which states that each skill is a folder whose name is the skill's identity.

### Why flat?

1. **Spec compliance** — the official spec describes a flat `skills/<skill-name>/SKILL.md` layout.
2. **Cross-tool compatibility** — Claude Code, Claude.ai, VS Code with Claude, and GitHub Copilot CLI all expect the flat layout.
3. **Simpler tooling** — a flat layout means `ls skills/` enumerates all skills; no recursion needed.
4. **No information loss** — domain categorization is preserved in the `description` field and in the [skill index](./skill-index.md).

### Domain categorization without subdirectories

Domain is encoded in two places:

1. **YAML frontmatter `description` field** — the second paragraph of every description mentions the domain ("Use this skill when building web frontends with React...").
2. **`docs/skill-index.md`** — a curated table grouping skills by domain.

This gives engineers a domain-grouped view for browsing while keeping the filesystem layout spec-compliant.

---

## Skill Folder Anatomy

```
skills/<skill-name>/                  # folder name MUST match `name` field
├── SKILL.md                          # required entry point with YAML frontmatter
├── scripts/                          # optional — helper scripts Claude can execute
│   └── helper.py
├── resources/                        # optional — reference materials Claude reads on demand
│   └── patterns.md
└── templates/                        # optional — file templates Claude can copy
    └── starter.ts
```

### Required

- `SKILL.md` — the entry point Claude Code reads. Contains YAML frontmatter + 30-section body.

### Optional

- `scripts/` — executable helpers (Python, Node, Bash) Claude can invoke.
- `resources/` — reference markdown files Claude reads on demand (keeps `SKILL.md` focused).
- `templates/` — file templates Claude can copy into the user's project.

The current repository uses only `SKILL.md` for each of the 93 skills. The optional subdirectories are documented here for future contributors who want to add per-skill helpers.

---

## YAML Frontmatter Contract

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

## Table of Contents
...
```

### Field rules

| Field | Required | Constraints |
|---|---|---|
| `name` | yes | `^[a-z0-9][a-z0-9-]{0,63}$` (lowercase letters, digits, hyphens; max 64 chars; cannot start with a hyphen). MUST match the folder name. |
| `description` | yes | Substantive — describes **what** the skill does **and when** to use it. Claude uses this as the trigger condition. Min 40 characters. Folded scalar (`>`) recommended. |
| `license` | yes (in this repo) | SPDX identifier (e.g., `MIT`). |
| `version` | yes (in this repo) | SemVer (`MAJOR.MINOR.PATCH`). |

### Description best practices

The `description` is the most important field. Claude Code reads it at startup and decides whether to auto-activate the skill based on the user's prompt. A weak description means the skill never activates.

A good description has two paragraphs:

1. **What** — one or two sentences describing the skill's expertise and quality bar.
2. **When** — one sentence starting with "Use this skill when..." listing the trigger conditions.

The two paragraphs are separated by a blank line inside the folded scalar, which YAML parses as a paragraph break.

### What is NOT in the frontmatter

The legacy v1.x metadata block (`**Domain**:`, `**Role Level**:`, `**File**:`) is gone. Domain is encoded in the description's "when" paragraph. Role level is encoded in the `## 1. Role` body section.

---

## Cross-Cutting Documentation

The `docs/` directory contains documentation that applies across all skills:

- **`architecture.md`** (this file) — repository architecture and design decisions.
- **`skill-structure.md`** — the 30-section skill anatomy specification, normative.
- **`usage-guide.md`** — how to use skills effectively, including auto-activation, explicit invocation, and composition.
- **`best-practices.md`** — cross-cutting engineering principles (SOLID, DRY, KISS, YAGNI, Clean Architecture, etc.).
- **`skill-index.md`** — a flat, domain-grouped table of all 93 skills.

These docs are NOT skills — they are not loaded by Claude Code as skills. They are human-facing documentation only.

---

## Templates and Examples

### `templates/skill-template/`

The official-spec template for new skills. Contributors copy this folder to `skills/<new-skill-name>/` and fill in the placeholders.

The template itself is a valid skill (it has YAML frontmatter and the 30-section body), so it can be validated with the same script:

```bash
python3 scripts/validate_skills.py
```

### `examples/example-usage.md`

Real-world scenarios showing how skills compose in professional workflows. Includes five scenarios: greenfield e-commerce backend, legacy monolith modernization, smart contract audit, production incident response, and AI agent system build.

---

## Scripts

### `scripts/migrate_skills.py`

The migration tool that produced v2.0 from v1.x. Reads the legacy `skills/<domain>/<skill-name>.md` layout and writes the spec-compliant `skills/<skill-name>/SKILL.md` layout with YAML frontmatter. Preserves 100% of body content.

Run it again only if you need to re-run the migration from a fresh v1.x source:

```bash
python3 scripts/migrate_skills.py
```

### `scripts/validate_skills.py`

The spec compliance validator. Enforces all hard requirements:

- Folder name matches `name` field
- `name` matches `^[a-z0-9][a-z0-9-]{0,63}$`
- YAML frontmatter parses
- `description` is substantive (≥ 40 chars)
- `license` and `version` present
- UTF-8, LF, no BOM
- 30-section body anatomy present
- No `TODO:`/`FIXME:`/`PLACEHOLDER:` markers in prose
- Content preservation (≥ 95% of legacy body)

Run it locally before opening a PR:

```bash
python3 scripts/validate_skills.py
```

The script exits with code 0 on success and non-zero on any failure. CI runs this on every pull request.

---

## Versioning Strategy

This repository follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — Incompatible changes to skill structure, filesystem layout, or metadata format. Example: v1.x → v2.0 migration to the official spec.
- **MINOR** — New skills added in a backwards-compatible manner. Example: adding a `rust-expert` skill.
- **PATCH** — Backwards-compatible bug fixes, clarifications, or example improvements. Example: correcting a code example in an existing skill.

The `version` field in each skill's YAML frontmatter is independent of the repository version. Individual skills start at `1.0.0` and follow SemVer.

---

## Extension Points

### Adding a new skill

1. Copy `templates/skill-template/` to `skills/<your-skill-name>/`.
2. Edit `SKILL.md` — fill in YAML frontmatter and all 30 body sections.
3. Validate: `python3 scripts/validate_skills.py`.
4. Update `docs/skill-index.md` (run `python3 scripts/generate_skill_index.py` to regenerate).
5. Open a PR per the [contribution workflow](../CONTRIBUTING.md).

### Adding a new domain

Domains are not formal — they are organizational groupings in `docs/skill-index.md`. To add a new domain:

1. Add an entry to `DOMAIN_TITLES` and `DOMAIN_COVERAGE` in `scripts/generate_skill_index.py`.
2. Add the domain to `DOMAIN_ORDER` (controls display order in the index).
3. Re-run `python3 scripts/generate_skill_index.py`.
4. Update `README.md`'s Skill Domains table.

### Adding supporting files to an existing skill

If a skill needs helper scripts or reference materials:

1. Create `skills/<skill-name>/scripts/` or `resources/` or `templates/` as needed.
2. Reference the files from `SKILL.md` using relative paths (e.g., "See `resources/patterns.md` for the full list").
3. Claude Code reads these on demand — only when the skill is active and the reference is needed.

---

## v1.x → v2.0 Architectural Changes

| Aspect | v1.x | v2.0 |
|---|---|---|
| Skill location | `skills/<domain>/<skill-name>.md` | `skills/<skill-name>/SKILL.md` |
| Skill entry point | `<skill-name>.md` | `SKILL.md` |
| Domain folders | 11 subdirectories under `skills/` | None — flat layout |
| Skill metadata | H1 header + blockquote + metadata block | YAML frontmatter |
| Skill name format | Implicit (from filename) | Explicit (`name` field, must match folder) |
| Skill description | Blockquote under H1 | YAML `description` field (folded scalar) |
| Domain | `**Domain**: <domain>` metadata line | Encoded in `description` "when" paragraph |
| Role level | `**Role Level**: <Senior\|Staff\|Principal>` line | Encoded in `## 1. Role` body section |
| License | Not recorded per-skill | YAML `license: MIT` |
| Version | Not recorded per-skill | YAML `version: 1.0.0` |
| Template | `templates/skill-template.md` (file) | `templates/skill-template/SKILL.md` (folder) |
| Skill discovery | Manual `@skill-name` invocation | Auto-activation via `description` field |
| Validator | None | `scripts/validate_skills.py` enforces spec |
| Migration tool | N/A | `scripts/migrate_skills.py` |

### What was preserved

- All 93 skill bodies — 100% verbatim.
- The 30-section anatomy specification in `docs/skill-structure.md`.
- The cross-cutting best practices in `docs/best-practices.md`.
- The five example scenarios in `examples/example-usage.md`.
- The MIT license.

### What was removed

- 11 legacy domain subdirectories under `skills/`.
- 93 legacy `<skill-name>.md` files (replaced by `<skill-name>/SKILL.md`).
- Legacy `# Skill: <Name>` H1 header pattern.
- Legacy `**Domain**:`, `**Role Level**:`, `**File**:` metadata block.
- Legacy `templates/skill-template.md` (replaced by `templates/skill-template/SKILL.md`).
