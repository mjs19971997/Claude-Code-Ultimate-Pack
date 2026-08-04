# Contributing to Claude Code Ultimate Pack

Thank you for your interest in contributing to the Claude Code Ultimate Pack. This document defines the standards, workflow, and review process for all contributions.

**As of v2.0.0, all contributions must follow the official [Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).** Legacy v1.x layouts (`skills/<domain>/<skill-name>.md`) are no longer accepted.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Spec Compliance (Mandatory)](#spec-compliance-mandatory)
3. [Contribution Workflow](#contribution-workflow)
4. [Skill Folder Structure](#skill-folder-structure)
5. [SKILL.md Format](#skill-md-format)
6. [Quality Standards](#quality-standards)
7. [Skill Anatomy Requirements](#skill-anatomy-requirements)
8. [Authoring a New Skill](#authoring-a-new-skill)
9. [Submitting a Pull Request](#submitting-a-pull-request)
10. [Review Process](#review-process)
11. [Style Guide](#style-guide)
12. [Commit Message Convention](#commit-message-convention)
13. [Branch Naming Convention](#branch-naming-convention)
14. [Issue Reporting](#issue-reporting)
15. [Recognition](#recognition)

---

## Code of Conduct

Be professional, respectful, and constructive. We are building production-grade tooling for engineers; contributions must reflect that standard. Personal attacks, dismissive language, and unprofessional conduct will not be tolerated.

---

## Spec Compliance (Mandatory)

Every skill in this repository must comply with the **official Claude Code Agent Skills specification** as published at <https://code.claude.com/docs/en/skills>.

### Hard requirements (enforced by CI)

1. **Skill = folder**. Each skill lives at `skills/<skill-name>/`.
2. **Entry point = `SKILL.md`**. The file `skills/<skill-name>/SKILL.md` must exist.
3. **Folder name = `name` field**. The folder name must exactly match the `name` field in the YAML frontmatter.
4. **YAML frontmatter is valid**. The file must begin with `---\n`, contain valid YAML, and end with a second `---\n`.
5. **`name` conforms to spec**. The `name` field must match `^[a-z0-9][a-z0-9-]{0,63}$` (lowercase letters, digits, hyphens; max 64 chars; cannot start with a hyphen).
6. **`description` is substantive**. Must be non-empty and at least 40 characters. It must describe **what the skill does AND when to use it** — Claude Code uses this as the trigger condition for auto-activation.
7. **`license` is present**. Use an SPDX identifier (e.g., `MIT`).
8. **`version` is SemVer**. e.g., `1.0.0`.
9. **UTF-8, LF, no BOM**. Files must be UTF-8 encoded with LF line endings and no byte-order mark.
10. **No `TODO:`, `FIXME:`, or `PLACEHOLDER:` in prose**. Code blocks are exempt (a Swift `placeholder:` closure label is fine).

### Recommended (not enforced)

- **Supporting files**. Place scripts in `skills/<skill-name>/scripts/`, reference materials in `skills/<skill-name>/resources/`, templates in `skills/<skill-name>/templates/`. Claude Code reads these on demand.
- **Keep `SKILL.md` focused**. If the skill grows past ~1500 lines, split dense reference material into `resources/` files and reference them by relative path from `SKILL.md`.

### What is no longer accepted

| v1.x pattern | v2.0 replacement |
|---|---|
| `skills/<domain>/<skill-name>.md` | `skills/<skill-name>/SKILL.md` |
| `# Skill: <Name>` H1 header | YAML frontmatter `name:` field |
| `> <description>` blockquote | YAML frontmatter `description:` field |
| `**Domain**: <domain>` metadata line | Mentioned in `description:` (Claude uses description for discovery, not domain) |
| `**Role Level**: <Senior\|Staff\|Principal>` | Mentioned in the `## 1. Role` body section |
| `**File**: <path>` metadata line | Removed — the folder name is the canonical identifier |

---

## Contribution Workflow

1. **Open an issue** describing the skill you want to add or modify (skip for trivial typo fixes).
2. **Fork the repository** and create a feature branch following the [Branch Naming Convention](#branch-naming-convention).
3. **Author the skill** using the official spec and the [`templates/skill-template/`](./templates/skill-template/) template.
4. **Validate locally**:
   ```bash
   python3 scripts/validate_skills.py
   ```
   The validator must report `Overall pass: True`.
5. **Open a pull request** with a clear description linking back to the issue.
6. **Address review feedback** within 7 days.
7. **Merge** once approved by a maintainer.

---

## Skill Folder Structure

```
skills/
└── <skill-name>/                  # folder name MUST match `name` field
    ├── SKILL.md                   # required entry point
    ├── scripts/                   # optional — helper scripts Claude can execute
    │   └── helper.py
    ├── resources/                 # optional — reference materials Claude reads on demand
    │   └── patterns.md
    └── templates/                 # optional — file templates Claude can copy
        └── starter.ts
```

### Naming the folder

- Use lowercase letters, digits, and hyphens only.
- Max 64 characters.
- Cannot start with a hyphen.
- Conventional suffixes: `-expert`, `-master`, `-architect`, `-engineer`. Pick one and be consistent.
- The folder name is the skill's identity. It appears in:
  - The `name` field of YAML frontmatter (must match exactly)
  - The `/skill <name>` invocation
  - The skill's URL in any index

---

## SKILL.md Format

### YAML frontmatter (required)

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

#### Field rules

- **`name`** (required): Must match the folder name. Pattern: `^[a-z0-9][a-z0-9-]{0,63}$`.
- **`description`** (required): Substantive — describe **what** the skill does **and when** to use it. Claude reads this at startup to decide whether to auto-activate the skill. A vague description means the skill will never activate.
- **`license`** (required in this repo): Use an SPDX identifier (`MIT`, `Apache-2.0`, etc.).
- **`version`** (required in this repo): SemVer (`MAJOR.MINOR.PATCH`).

### Body (required)

The body is a markdown document. It must follow the [30-section anatomy](#skill-anatomy-requirements) defined below.

---

## Quality Standards

Every `SKILL.md` must satisfy ALL of the following before merge:

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

---

## Skill Anatomy Requirements

Every skill body must contain these 30 sections in this exact order. See [`docs/skill-structure.md`](./docs/skill-structure.md) for the full specification.

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

## Authoring a New Skill

### Step 1: Choose the skill name

Skill names must be lowercase, kebab-case, and end with a role suffix:

- `senior-react-19-engineer` — role + technology
- `nestjs-expert` — technology + role
- `software-architect` — discipline + role
- `owasp-top-10-expert` — framework + role

Check [`docs/skill-index.md`](./docs/skill-index.md) to ensure the name is not already taken.

### Step 2: Copy the template

```bash
cp -r templates/skill-template skills/<your-skill-name>
```

Then edit `skills/<your-skill-name>/SKILL.md` and fill in every section.

### Step 3: Fill in the YAML frontmatter

```yaml
---
name: <your-skill-name>      # MUST match the folder name
description: >
  <One-sentence description of what the skill does>.

  Use this skill when <list of trigger conditions>.
license: MIT
version: 1.0.0
---
```

### Step 4: Fill in every body section

Author each of the 30 sections with substantive content. Use existing skills as reference. Every section must contain real, production-grade content — no placeholders.

### Step 5: Validate locally

```bash
python3 scripts/validate_skills.py
```

The validator must report `Overall pass: True`. Fix any errors before opening a PR.

### Step 6: Test the skill

Install the skill locally and invoke it with a real-world prompt. Verify Claude Code activates it correctly and the output meets the standards defined in the skill.

---

## Submitting a Pull Request

1. Push your branch to your fork.
2. Open a pull request against the `main` branch of the upstream repository.
3. Use the PR template below.
4. Link the issue your PR addresses using `Closes #123` syntax.
5. Ensure the validator passes (CI will run it automatically).

### PR Template

```markdown
## Description

<What does this PR add or change?>

## Type of Change

- [ ] New skill
- [ ] Skill enhancement
- [ ] Documentation change
- [ ] Bug fix
- [ ] Other

## Spec Compliance Checklist

- [ ] Skill lives at `skills/<skill-name>/SKILL.md`
- [ ] Folder name matches the `name` field in YAML frontmatter
- [ ] `name` matches `^[a-z0-9][a-z0-9-]{0,63}$`
- [ ] `description` describes what the skill does AND when to use it
- [ ] `license` is a valid SPDX identifier
- [ ] `version` is SemVer
- [ ] UTF-8, LF, no BOM
- [ ] All 30 body sections present, in order
- [ ] `python3 scripts/validate_skills.py` reports `Overall pass: True`

## Quality Checklist

- [ ] Minimum 300 lines
- [ ] No placeholders or TODOs in prose
- [ ] At least 3 code examples
- [ ] At least 5 items per checklist
- [ ] At least 5 anti-patterns
- [ ] At least 5 common mistakes
- [ ] Production-ready language throughout

## Related Issue

Closes #<issue-number>
```

---

## Review Process

Every PR is reviewed by at least one maintainer. Reviewers verify:

1. **Spec compliance** — folder layout, YAML frontmatter, `name` format, `description` quality.
2. **Structural compliance** — all 30 sections present, in order.
3. **Content depth** — every section substantive, no placeholders.
4. **Technical accuracy** — code examples are syntactically valid and follow best practices.
5. **Consistency** — voice, tone, and structure match existing skills.
6. **Production-readiness** — content reflects real-world, senior-level engineering.
7. **Validator passes** — `python3 scripts/validate_skills.py` reports `Overall pass: True`.

Reviewers may request changes. Address all feedback within 7 days or the PR may be closed as stale. If you need more time, leave a comment.

---

## Style Guide

### Voice and Tone

- **Authoritative** — write as a principal engineer with 20+ years of experience.
- **Imperial** — use "always", "never", "must", "must not", "forbidden".
- **Concise** — every sentence carries weight; no filler.
- **Professional** — no slang, no humor, no casual language.
- **Technical** — use precise technical terminology.

### Forbidden Phrases

- "you might consider" → use "always" or "must"
- "perhaps" → use "must" or "never"
- "it depends" → specify the exact conditions
- "TODO" → never use; implement the content
- "placeholder" → never use; provide real content
- "in the future" → never use; if it is not needed now, do not write it (YAGNI)

### YAML Frontmatter Conventions

- Use the folded scalar style (`>`) for multi-line descriptions.
- Indent continuation lines with two spaces.
- Separate the "what" sentence from the "when" sentence with a blank line in the folded scalar — this creates a paragraph break in the parsed value.
- Never include a literal `---` line inside the description (it would terminate the frontmatter).

### Markdown Conventions

- Use `##` for section headers (level 2) — matches the 30-section anatomy.
- Use `###` for subsections (level 3).
- Use code blocks with language identifiers: ` ```typescript `.
- Use tables for structured comparisons.
- Use bullet lists for enumerations.
- Use numbered lists for sequential processes.
- Wrap lines at 100 characters where reasonable.

### Code Conventions

- All code examples must be syntactically valid.
- All code examples must include error handling where the language expects it.
- All code examples must follow the naming conventions defined in the skill.
- All code examples must be production-ready — no `console.log` debugging, no `// TODO` comments.

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat` — a new skill or feature
- `fix` — a bug fix in an existing skill
- `docs` — documentation changes
- `refactor` — a code change that neither fixes a bug nor adds a feature
- `test` — adding missing tests or correcting existing tests
- `chore` — maintenance tasks, dependency updates, etc.

### Scopes

Use the skill name (without role suffix) as the scope:

- `feat(react-19): add senior-react-19-engineer skill`
- `fix(nestjs): correct module example`
- `docs: update installation guide`

### Examples

```
feat(multi-agent): add multi-agent-expert skill

Adds a new skill covering multi-agent system architecture, including
orchestration patterns, communication protocols, and failure handling.

Closes #42
```

```
fix(k8s-yaml): correct Kubernetes deployment YAML indentation

The previous example used 4-space indentation in the container spec,
which is invalid YAML for kubectl apply. Corrected to 2-space.
```

---

## Branch Naming Convention

```
<type>/<skill-name>-<short-description>
```

Examples:

- `feat/senior-react-19-engineer-add-suspense-streaming`
- `fix/nestjs-module-example`
- `docs/installation-update`

---

## Issue Reporting

When opening an issue, include:

1. **Summary** — one-sentence description of the problem or proposal.
2. **Context** — what were you trying to do?
3. **Expected behavior** — what did you expect to happen?
4. **Actual behavior** — what actually happened?
5. **Reproduction steps** — numbered steps to reproduce.
6. **Environment** — OS, Claude Code version, skill version.
7. **Proposed solution** — optional, but welcome.

Use the issue templates provided in `.github/ISSUE_TEMPLATE/` if present.

---

## Recognition

Contributors who merge 3 or more high-quality skills are added to the `AUTHORS.md` file. Contributors who consistently maintain high standards may be invited to become maintainers.

---

Thank you for helping build the most comprehensive Claude Code skill pack in the world — fully compliant with the official Agent Skills specification. Every contribution matters.
