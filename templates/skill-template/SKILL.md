---
name: skill-template
description: >-
  Starting point for a new skill in this pack; copy the folder, rename it and replace every placeholder. Use when creating a skill, updating a skill to the v3.0.0 layout, or checking what a SKILL.md section should contain. Not for the format rules themselves (see docs/skill-structure.md) or the contribution workflow (see CONTRIBUTING.md).
license: MIT
metadata:
  version: "3.0.0"
---

# Skill Template

Replace this paragraph with two to four sentences: what the skill covers, which technologies and task types it handles, and what it leaves to other skills. Claude reads the frontmatter description first and this body only after the skill has been chosen, so the scope paragraph should orient, not repeat the description.

> Verified against <technology and exact versions, for example "Tool 4.2.x, Library 9.1.x"> (YYYY-MM).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: list the concrete tasks and technologies, for example "configuring X, writing Y, debugging Z".
- Not covered: name each neighbouring area and the skill that owns it, for example "container images (docker-expert)". Every name must be an existing folder under `skills/`.

## 2. Core Expertise

A table of facts that are easy to get wrong or that changed recently. Keep each row verifiable against the official documentation.

| Area | Key facts |
|---|---|
| Placeholder area | Placeholder fact with the exact option name, default value or version where it applies |
| Another area | Another fact; mention deprecated or removed features and what replaced them |

## 3. Workflow

Numbered steps that Claude follows for a typical task in this area. Fold any "thinking process" material in here.

1. Clarify the runtime, versions and constraints that change the answer.
2. Inspect the existing code or configuration before proposing changes.
3. Make the smallest change that solves the problem and follows the project's conventions.
4. Verify with the project's own commands (build, test, lint) and state what was run.
5. Summarise what changed and any follow-up the user must do.

## 4. Decision Rules

Use "if X, then Y because Z" statements for choices that come up repeatedly.

- If the project already uses option A, keep it; switch to option B only when a stated requirement needs it.
- Prefer the built-in feature over a third-party package unless the package solves a documented gap.
- When two approaches trade speed for safety, choose safety by default and say what the faster option costs.

## 5. Coding Standards

Rules a reviewer could check in a diff: naming, formatting, error handling, typing, imports.

- Follow the formatter and linter configured in the repository; do not add a second one.
- Name things after the domain, not the technology.
- Handle errors at the layer that can act on them; do not swallow them.

## 6. Project Structure

A short tree of the layout this skill recommends. Use a language-tagged fence (`text` for trees).

```text
project/
├── src/            # application code
├── tests/          # mirrors src/
└── config/         # environment-specific settings, no secrets
```

## 7. Design Patterns

- **Pattern name**: when to use it, the problem it solves, and one line on its cost.
- **Another pattern**: same format. Link a reference file for long examples.

## 8. Best Practices

- Practice stated as an action, with the reason in the same bullet.
- Keep bullets self-contained; a reader should not need the previous bullet.

## 9. Performance

- Name the metric to measure first, then the techniques, for example "measure p95 latency, then add an index".
- State when an optimisation is not worth its complexity.

## 10. Security

- Name the threat and the control, for example "untrusted input reaches the query, so use parameterised statements".
- Never include real secrets in examples; use placeholders such as `YOUR_API_KEY` and read values from the environment.
- Flag insecure defaults in the technology and how to change them.

## 11. Testing

- Which test types matter for this area and what each one should cover.
- The commands to run them.
- How to test failure paths, not only the happy path.

## 12. Review Checklist

- [ ] Versions and options match the "Verified against" line.
- [ ] No secrets, tokens or personal data in code or examples.
- [ ] Error paths are handled and tested.
- [ ] The change follows the project's existing conventions.
- [ ] Documentation or changelog updated when behaviour changed.

## 13. Production Notes

- Deployment, rollout and rollback considerations.
- Observability: which logs, metrics and alerts to add.
- Known limits, deprecations and upgrade paths worth planning for.

## 14. Examples

Include two or three short, runnable examples that follow the rules above. Each needs a one-line introduction saying what it demonstrates.

A minimal example, with the language tag matching the content:

```python
def greet(name: str) -> str:
    """Return a greeting; replace this with an example from your domain."""
    return f"Hello, {name}"
```

If an example must itself contain a code fence, open the outer fence with four backticks so the inner three-backtick fence stays balanced. Prefer linking a reference file instead.

## 15. Common Mistakes

- **Mistake as a short title**: what goes wrong, why, and the fix. Anti-patterns belong here.
- **Another mistake**: same format; name the symptom a user would see.

## 16. References

- [references/topic.md](references/topic.md): sample reference file; describe in one line what it holds and when to open it.
- Official docs: add the canonical documentation URLs used to verify this skill.

<!-- Authoring notes (delete before publishing):
- name must equal the folder name; description is "<what>. Use when <triggers>. Not for <area> (use <skill>)." aim 300-700 characters, 1024 maximum.
- Keep SKILL.md at 200-400 lines (validator warns outside 80-450). Move depth into 1-5 files under references/ and link each from section 16.
- Drop sections that have nothing specific to say, renumber the rest and update the Contents anchors.
- Do not add persona lines, reply-format sections, attribution trailers or guessed versions.
- Run: python scripts/validate_skills.py and python scripts/generate_skill_index.py
-->
