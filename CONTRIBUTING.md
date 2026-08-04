# Contributing to Claude Code Ultimate Pack

Thank you for your interest in contributing to the Claude Code Ultimate Pack. This document defines the standards, workflow, and review process for all contributions.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Contribution Workflow](#contribution-workflow)
3. [Quality Standards](#quality-standards)
4. [Skill Anatomy Requirements](#skill-anatomy-requirements)
5. [Authoring a New Skill](#authoring-a-new-skill)
6. [Submitting a Pull Request](#submitting-a-pull-request)
7. [Review Process](#review-process)
8. [Style Guide](#style-guide)
9. [Commit Message Convention](#commit-message-convention)
10. [Branch Naming Convention](#branch-naming-convention)
11. [Issue Reporting](#issue-reporting)
12. [Recognition](#recognition)

---

## Code of Conduct

Be professional, respectful, and constructive. We are building production-grade tooling for engineers; contributions must reflect that standard. Personal attacks, dismissive language, and unprofessional conduct will not be tolerated.

---

## Contribution Workflow

1. **Open an issue** describing the skill you want to add or modify (skip for trivial typo fixes)
2. **Fork the repository** and create a feature branch
3. **Author the skill** following the 30-section anatomy and quality standards below
4. **Validate locally** using the checklist in this document
5. **Open a pull request** with a clear description linking back to the issue
6. **Address review feedback** within 7 days
7. **Merge** once approved by a maintainer

---

## Quality Standards

Every skill file must satisfy ALL of the following before it can be merged:

- [ ] Minimum 300 lines, up to 1000 lines where warranted
- [ ] All 30 sections present, in order, with the exact section headers
- [ ] No placeholders, no TODOs, no "implement later", no "TBD"
- [ ] No section shorter than 5 lines (unless inherently list-based, e.g., naming conventions)
- [ ] At least 3 concrete code examples in the Examples section
- [ ] At least 5 items in every checklist (Code Review, Refactoring, Deployment, Production)
- [ ] At least 5 anti-patterns documented in the Anti Patterns section
- [ ] At least 5 common mistakes documented in the Common Mistakes section
- [ ] Production-ready language throughout — no "you might", no "consider", no "perhaps"
- [ ] Imperial directives — "always", "never", "must", "must not", "forbidden"
- [ ] All code examples must be syntactically valid for their language
- [ ] All code examples must include error handling where the language expects it
- [ ] File name must be lowercase, kebab-case, ending in `.md`
- [ ] File name must match the skill's identity (e.g., `senior-react-19-engineer.md`)

---

## Skill Anatomy Requirements

Every skill must contain these 30 sections in this exact order. See `docs/skill-structure.md` for the full specification.

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

### Step 1: Choose the domain and skill name

Determine which domain your skill belongs to. If none fit, open an issue proposing a new domain. Skill names must be lowercase, kebab-case, and end with a role suffix:

- `senior-react-19-engineer` — role + technology
- `nestjs-expert` — technology + role
- `software-architect` — discipline + role
- `owasp-top-10-expert` — framework + role

### Step 2: Copy the template

```bash
cp templates/skill-template.md skills/<domain>/<skill-name>.md
```

### Step 3: Fill in every section

Author each section with substantive content. Use the existing skills in the repository as reference. Every section must contain real, production-grade content — no placeholders.

### Step 4: Validate locally

Run through the Quality Standards checklist above. Every box must be checked.

### Step 5: Test the skill

Install the skill locally and invoke it with a real-world prompt. Verify the output meets the standards defined in the skill.

---

## Submitting a Pull Request

1. Push your branch to your fork
2. Open a pull request against the `main` branch of the upstream repository
3. Use the PR template (provided below) to describe your change
4. Link the issue your PR addresses using `Closes #123` syntax
5. Ensure CI passes (if CI is configured)

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

## Domain

<frontend | backend | database | blockchain | mobile | devops | architecture | security | testing | ai | seo>

## Quality Checklist

- [ ] Minimum 300 lines
- [ ] All 30 sections present
- [ ] No placeholders or TODOs
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

1. **Structural compliance** — all 30 sections present, in order
2. **Content depth** — every section substantive, no placeholders
3. **Technical accuracy** — code examples are syntactically valid and follow best practices
4. **Consistency** — voice, tone, and structure match existing skills
5. **Production-readiness** — content reflects real-world, senior-level engineering

Reviewers may request changes. Address all feedback within 7 days or the PR may be closed as stale. If you need more time, leave a comment.

---

## Style Guide

### Voice and Tone

- **Authoritative** — write as a principal engineer with 20+ years of experience
- **Imperial** — use "always", "never", "must", "must not", "forbidden"
- **Concise** — every sentence carries weight; no filler
- **Professional** — no slang, no humor, no casual language
- **Technical** — use precise technical terminology

### Forbidden Phrases

- "you might consider" → use "always" or "must"
- "perhaps" → use "must" or "never"
- "it depends" → specify the exact conditions
- "TODO" → never use; implement the content
- "placeholder" → never use; provide real content
- "in the future" → never use; if it is not needed now, do not write it (YAGNI)

### Markdown Conventions

- Use `##` for section headers (level 2)
- Use `###` for subsections (level 3)
- Use code blocks with language identifiers: ` ```typescript `
- Use tables for structured comparisons
- Use bullet lists for enumerations
- Use numbered lists for sequential processes
- Wrap lines at 100 characters where reasonable

### Code Conventions

- All code examples must be syntactically valid
- All code examples must include error handling where the language expects it
- All code examples must follow the naming conventions defined in the skill
- All code examples must be production-ready — no `console.log` debugging, no `// TODO` comments

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

Use the domain name as the scope:

- `feat(frontend): add senior-react-19-engineer skill`
- `fix(backend): correct NestJS module example`
- `docs: update installation guide`

### Examples

```
feat(ai): add multi-agent-expert skill

Adds a new skill covering multi-agent system architecture, including
orchestration patterns, communication protocols, and failure handling.

Closes #42
```

```
fix(devops): correct Kubernetes deployment YAML indentation

The previous example used 4-space indentation in the container spec,
which is invalid YAML for kubectl apply. Corrected to 2-space.
```

---

## Branch Naming Convention

```
<type>/<scope>-<short-description>
```

Examples:

- `feat/frontend-react-19-skill`
- `fix/devops-k8s-yaml`
- `docs/installation-update`

---

## Issue Reporting

When opening an issue, include:

1. **Summary** — one-sentence description of the problem or proposal
2. **Context** — what were you trying to do?
3. **Expected behavior** — what did you expect to happen?
4. **Actual behavior** — what actually happened?
5. **Reproduction steps** — numbered steps to reproduce
6. **Environment** — OS, Claude Code version, skill version
7. **Proposed solution** — optional, but welcome

Use the issue templates provided in `.github/ISSUE_TEMPLATE/` if present.

---

## Recognition

Contributors who merge 3 or more high-quality skills are added to the `AUTHORS.md` file. Contributors who consistently maintain high standards may be invited to become maintainers.

---

Thank you for helping build the most comprehensive Claude Code skill pack in the world. Every contribution matters.
