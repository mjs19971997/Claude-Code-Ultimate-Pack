# Repository Architecture

This document describes the architecture of the Claude Code Ultimate Pack repository, the design decisions behind it, and the conventions that govern its structure.

---

## Table of Contents

1. [Design Goals](#design-goals)
2. [Top-Level Layout](#top-level-layout)
3. [The skills/ Directory](#the-skills-directory)
4. [Domain Partitioning](#domain-partitioning)
5. [Skill File Format](#skill-file-format)
6. [Cross-Cutting Documentation](#cross-cutting-documentation)
7. [Templates and Examples](#templates-and-examples)
8. [Versioning Strategy](#versioning-strategy)
9. [Extension Points](#extension-points)

---

## Design Goals

The repository architecture serves five goals, in priority order:

1. **Discoverability** — any engineer must be able to find the right skill in under 30 seconds
2. **Consistency** — every skill follows the same anatomy, so navigation is predictable
3. **Composability** — skills can be combined in workflows without conflicts
4. **Maintainability** — the repository must remain navigable as it grows past 100 skills
5. **Portability** — the repository must work across global, project-local, and submodule installations

Every structural decision in this repository traces back to one of these goals.

---

## Top-Level Layout

```
Claude-Code-Ultimate-Pack/
├── README.md           # Public-facing overview
├── INSTALL.md          # Installation guide
├── CHANGELOG.md        # Version history
├── LICENSE             # MIT license
├── CONTRIBUTING.md     # Contributor guide
├── docs/               # Reference documentation
├── examples/           # Usage examples
├── templates/          # Skill and project templates
└── skills/             # 95+ skill files, organized by domain
```

### Why this layout

- **Root files** are the only files a new visitor reads first. They must answer: *what is this*, *how do I install it*, *how do I use it*, *how do I contribute*, *what changed*, *under what license*.
- **docs/** holds reference material that is consulted but rarely read end-to-end.
- **examples/** holds narrative walkthroughs that demonstrate skills in combination.
- **templates/** holds starter material for authoring new skills or scaffolding new projects.
- **skills/** holds the actual deliverable — the skill files Claude Code consumes.

---

## The skills/ Directory

The `skills/` directory is partitioned into 11 domain subdirectories. Each subdirectory contains skill files relevant to that domain only. There is no nesting beyond one level.

```
skills/
├── ai/             # 14 skills
├── architecture/   # 8 skills
├── backend/        # 10 skills
├── blockchain/     # 13 skills
├── database/       # 5 skills
├── devops/         # 13 skills
├── frontend/       # 10 skills
├── mobile/         # 6 skills
├── security/       # 5 skills
├── seo/            # 4 skills
└── testing/        # 7 skills
```

### Why flat, not nested

A flat structure means:
- File paths are short and predictable: `skills/frontend/senior-react-19-engineer.md`
- No skill is buried more than one directory deep
- Glob patterns work uniformly: `skills/**/*.md`
- Navigation is O(1) — you open a directory and see every skill in it

A nested structure (e.g., `skills/frontend/react/senior-react-19-engineer.md`) would offer marginal organizational benefit at the cost of deeper paths and inconsistent grouping. We reject that trade-off.

---

## Domain Partitioning

Domains are defined by **the problem space**, not the technology stack. A skill belongs to the domain whose problem it primarily solves.

| Domain | Problem Space | Example Skill |
|---|---|---|
| frontend | User interface in the browser | `senior-react-19-engineer` |
| backend | Server-side application logic | `nestjs-expert` |
| database | Data persistence and retrieval | `postgresql-expert` |
| blockchain | Distributed ledger systems | `solidity-expert` |
| mobile | Native mobile applications | `swiftui-expert` |
| devops | Infrastructure and deployment | `kubernetes-expert` |
| architecture | Cross-cutting system design | `system-design-expert` |
| security | Application and API security | `owasp-top-10-expert` |
| testing | Quality assurance and verification | `playwright-expert` |
| ai | LLM and agent systems | `rag-expert` |
| seo | Search engine optimization | `core-web-vitals-expert` |

### Cross-domain skills

Some skills could fit multiple domains. We resolve ambiguity by asking: *which domain's practitioners would most likely invoke this skill?*

- `authentication-expert` lives in `backend/`, not `security/`, because authentication is implemented by backend engineers, even though it overlaps with security.
- `api-security-expert` lives in `security/`, not `backend/`, because it is primarily invoked by security reviewers, not API implementers.
- `performance-expert` (frontend) lives in `frontend/`, not `architecture/`, because it focuses on browser-side performance.

---

## Skill File Format

Every skill file is a Markdown file with the following properties:

- **Encoding**: UTF-8
- **Line endings**: LF (Unix)
- **Extension**: `.md`
- **Naming**: lowercase, kebab-case, role-suffixed (e.g., `senior-react-19-engineer.md`)
- **Minimum length**: 300 lines
- **Maximum length**: 1000 lines (split into multiple files if longer)
- **Structure**: 30 sections in a fixed order (see `skill-structure.md`)

### File header

Every skill file begins with a YAML-like front matter block (not parsed, but human-readable):

```markdown
# Skill: <Skill Name>

> <One-sentence description of what this skill does>

**Domain**: <domain>
**Role Level**: Senior / Staff / Principal
**File**: `<domain>/<skill-name>.md`
```

This header is followed by the 30 mandatory sections.

---

## Cross-Cutting Documentation

The `docs/` directory contains reference material that applies across all skills:

- `architecture.md` — this file
- `skill-structure.md` — the 30-section anatomy specification
- `usage-guide.md` — how to use skills effectively, including composition
- `best-practices.md` — cross-cutting engineering principles enforced by every skill
- `skill-index.md` — a flat index of all 95+ skills with one-line descriptions

### Why a separate index

The `skill-index.md` file exists because:
- It is machine-readable (a flat list, easy to grep or parse)
- It provides a single place to discover skills without browsing directories
- It serves as a table of contents for the entire pack

---

## Templates and Examples

### templates/

- `skill-template.md` — the canonical template for authoring a new skill. Contains all 30 section headers with placeholder guidance. Copy this file to start a new skill.
- `project-templates/` — starter project scaffolds for common technology stacks. Each scaffold is a minimal, production-ready project that demonstrates the conventions defined in the relevant skills.

### examples/

- `example-usage.md` — narrative walkthroughs showing how to invoke skills in real scenarios. Each example shows the prompt, the skill that activates, and the expected shape of the output.

---

## Versioning Strategy

The repository follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — incompatible changes to skill structure or output formats
- **MINOR** — new skills added in a backwards-compatible manner
- **PATCH** — backwards-compatible bug fixes, clarifications, or example improvements

The current version is tracked in `CHANGELOG.md`. Releases are tagged as `vMAJOR.MINOR.PATCH`.

---

## Extension Points

The repository is designed to be extended in three ways:

### 1. Adding a new skill to an existing domain

Copy `templates/skill-template.md` to `skills/<domain>/<skill-name>.md`, fill in every section, and submit a PR. See `CONTRIBUTING.md` for the full workflow.

### 2. Adding a new domain

Open an issue proposing the new domain with:
- The domain name
- The problem space it covers
- At least 3 skills that would belong to it
- Why none of the existing 11 domains fit

Domains are added sparingly. The current 11 domains cover the vast majority of professional software engineering work.

### 3. Forking for customization

Teams may fork the repository to customize skills for their internal stack. The MIT License explicitly permits this. We recommend forking rather than modifying in-place so that upstream updates can still be merged.

---

This architecture is intentional and stable. Changes to the top-level layout or domain partitioning require a MAJOR version bump and a documented migration path.
