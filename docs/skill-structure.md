# Skill Structure

This is the v3.0.0 anatomy of a skill in this pack. It follows the [Agent Skills format](https://code.claude.com/docs/en/skills) and adds a few repository rules that `scripts/validate_skills.py` checks. Start new skills from [templates/skill-template/](../templates/skill-template/SKILL.md); the workflow is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Contents

1. [Layout](#layout)
2. [Frontmatter](#frontmatter)
3. [Body](#body)
4. [Sections](#sections)
5. [Reference files](#reference-files)
6. [Not allowed](#not-allowed)
7. [What the validator checks](#what-the-validator-checks)

## Layout

```text
skills/<skill-name>/
├── SKILL.md            # frontmatter + body, 200-400 lines
└── references/         # 1-5 focused documents, read on demand
    └── <topic>.md
```

- The folder name is the skill name: lowercase letters, digits and hyphens, at most 64 characters, matching `^[a-z0-9][a-z0-9-]{0,63}$`.
- Skills sit directly under `skills/`; there are no domain subfolders. Categories exist only in the generated [skill index](./skill-index.md).
- Claude loads the frontmatter at startup, the body when the skill is chosen, and a reference file only when the task needs it. Keep `SKILL.md` for what is needed every time.

## Frontmatter

```yaml
---
name: example-expert
description: >-
  <What it does.> Use when <triggers>. Not for <area> (use <other-skill>).
license: MIT
metadata:
  version: "3.0.0"
---
```

| Key | Rule |
|---|---|
| `name` | Required. Equal to the folder name. |
| `description` | Required. 1024 characters at most (the validator also requires 40 or more); aim for 300-700. Format: what the skill does, then "Use when" with concrete triggers (tools, file names, commands, symptoms), then "Not for" with each confusable area and the skill to use instead. |
| `license` | Required. `MIT`. |
| `metadata.version` | Required. SemVer string, `"3.0.0"` for this release. |
| `allowed-tools`, `compatibility` | Optional. Allowed by the format; leave them out unless the skill needs them. |

Only `name`, `description`, `license`, `allowed-tools`, `metadata` and `compatibility` may appear at the top level. A top-level `version` key is an error.

The description is what Claude matches against the user's request, so write it in plain third person and name real triggers. Do not repeat one sentence across a category of skills.

## Body

In order:

1. `# Title`
2. A scope paragraph of two to four sentences: what the skill covers and what it leaves to others.
3. A verification line: `> Verified against <technology and exact versions> (YYYY-MM).` Use versions you confirmed in the official documentation or release notes; leave a version out rather than guess it.
4. `## Contents`: a numbered list linking to every section.
5. The numbered sections below.

Length: 200-400 lines for `SKILL.md`; a skill that absorbed several older ones may reach about 450. The validator warns outside 80-450.

## Sections

Sections are numbered `## N. Title` in this order. Leave out a section that has nothing specific to say, renumber the rest and keep the Contents anchors in step.

| # | Section | Content |
|---|---|---|
| 1 | Scope | What is covered, and what is not, naming the skill that owns each neighbouring area |
| 2 | Core Expertise | Table of precise, version-sensitive facts |
| 3 | Workflow | Numbered steps for a typical task, including how to investigate before changing things |
| 4 | Decision Rules | "If X, then Y because Z" choices |
| 5 | Coding Standards | Rules a reviewer can check in a diff |
| 6 | Project Structure | Recommended layout |
| 7 | Design Patterns | Patterns with when to use them and their cost |
| 8 | Best Practices | Action plus reason |
| 9 | Performance | What to measure and what to change |
| 10 | Security | Threats and controls; safe defaults only |
| 11 | Testing | Test types, commands, failure-path coverage |
| 12 | Review Checklist | Checkbox list for reviewing a change |
| 13 | Production Notes | Rollout, observability, limits, deprecations |
| 14 | Examples | Two or three short, correct, runnable examples |
| 15 | Common Mistakes | Mistake, consequence, fix (anti-patterns go here) |
| 16 | References | Links to every `references/` file and the official documentation |

## Reference files

- Put deep material in `references/<topic>.md`: long examples, option tables, migration notes, framework-specific guidance.
- Use one to five files. Link every file from section 16 with a one-line description; the validator checks that relative links resolve.
- Each file starts with a title and stands on its own. Add a Contents list when it has more than three sections.
- Reference files are plain Markdown. Do not put frontmatter in them.

## Not allowed

- Sections that tell Claude how to format or phrase its replies (response-style or output-format sections). The user's own settings decide tone and reply format.
- Persona lines such as "You are a Principal ...", and claims of final or sole authority.
- A trigger sentence shared by a whole category of skills.
- Separate Anti Patterns or Thinking Process sections. Put anti-patterns in Common Mistakes and the investigation steps in Workflow.
- Nested code fences of the same length. Open the outer fence with four backticks when an example contains a fence.
- Guessed versions, fictional packages or APIs, and insecure examples (hard-coded secrets, disabled TLS verification, string-built SQL).
- Attribution trailers in the files or in commit messages.

## What the validator checks

`python scripts/validate_skills.py` is read-only and exits with status 1 on errors. It checks, for every skill and for the template:

- `SKILL.md` exists, is UTF-8 without BOM and uses LF line endings.
- Frontmatter parses and uses only the allowed keys; `name` matches the folder; `description` length; `license` present; `metadata.version` is SemVer.
- No reply-format sections, persona lines or attribution trailers.
- In-file anchor links point at real headings, relative links point at existing files, and code fences are balanced.
- A warning when `SKILL.md` is shorter than 80 or longer than 450 lines.

Quality rules that a script cannot check, such as accurate versions and a well-aimed description, are covered in the [review section of CONTRIBUTING.md](../CONTRIBUTING.md#review).
