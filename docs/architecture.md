# Architecture

How the Claude Code Ultimate Pack v3.0.0 is organized and why. For the format of a single skill see [skill-structure.md](./skill-structure.md); for the contribution workflow see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Contents

1. [Design goals](#design-goals)
2. [Repository layout](#repository-layout)
3. [Skills directory](#skills-directory)
4. [How Claude Code loads a skill](#how-claude-code-loads-a-skill)
5. [Boundaries between skills](#boundaries-between-skills)
6. [Scripts](#scripts)
7. [Versioning](#versioning)
8. [Extension points](#extension-points)
9. [Changes since v2](#changes-since-v2)

## Design goals

1. **Format compliance.** Every skill follows the [Agent Skills format](https://code.claude.com/docs/en/skills); a validator enforces the rules that can be checked by script.
2. **Accurate triggering.** The `description` says what the skill does, when to use it and when to use a sibling instead, so the right skill loads and the wrong ones do not.
3. **Small context cost.** `SKILL.md` stays at 200-400 lines; detail lives in `references/` files that are read only when needed.
4. **Verifiable content.** Each skill names the technology versions it was checked against and the month of the check.
5. **Portability.** Skills are plain folders that work as personal skills (`~/.claude/skills/`) or project skills (`.claude/skills/`) on Linux, macOS and Windows.

## Repository layout

```text
Claude-Code-Ultimate-Pack/
├── README.md
├── INSTALL.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── skills/                       # 80 skill folders
│   └── <skill-name>/
│       ├── SKILL.md
│       └── references/<topic>.md
├── templates/skill-template/     # starting point for a new skill
│   ├── SKILL.md
│   └── references/topic.md
├── docs/
│   ├── architecture.md           # this file
│   ├── skill-structure.md
│   ├── usage-guide.md
│   ├── best-practices.md
│   └── skill-index.md            # generated
├── examples/example-usage.md
└── scripts/
    ├── validate_skills.py
    └── generate_skill_index.py
```

The files in `docs/` and `examples/` are for people; Claude Code does not load them as skills.

## Skills directory

`skills/` is flat: one folder per skill, named by the skill. There are no domain subfolders, because the format identifies a skill by its folder name. Categories are kept in one place, the `CATEGORIES` list in `scripts/generate_skill_index.py`, which produces the grouped [skill index](./skill-index.md).

| Category | Skills |
|---|---|
| Architecture | 8 |
| Frontend | 12 |
| Backend | 5 |
| Languages | 5 |
| Data | 5 |
| Infrastructure and DevOps | 11 |
| Security | 4 |
| Testing | 4 |
| Mobile | 4 |
| Blockchain | 11 |
| AI and LLM | 9 |
| Scientific and Academic | 2 |

Total: 80 skills in 12 categories.

## How Claude Code loads a skill

1. At session start Claude Code reads the `name` and `description` of each installed skill.
2. When a request matches a description, Claude loads that skill's `SKILL.md`. You can also call a skill directly with `/<skill-name>`.
3. While working, Claude opens a file under `references/` only if the task needs that detail.

Because only descriptions are always in context, the description carries the triggering job, and the body and references carry the substance. Details for users are in the [usage guide](./usage-guide.md).

## Boundaries between skills

Overlapping skills were merged in v3 so that one topic has one owner. Where two skills border each other, each description names the other in its "Not for" clause. Examples:

| Topic | Owner |
|---|---|
| Container images and Docker Compose | `docker-expert` |
| Kubernetes manifests and Helm | `kubernetes-expert` |
| CI pipelines and GitHub Actions | `cicd-expert` |
| Login, sessions, JWT, OAuth 2.0 | `authentication-expert` |
| Permissions and policy | `authorization-expert` |
| OWASP Top 10 and secure coding | `secure-coding-expert` |
| Unit tests (Jest, Vitest) | `unit-testing-expert` |
| End-to-end tests (Cypress) | `e2e-testing-expert` |
| Playwright Test | `playwright-expert` |
| Front-end performance (LCP, INP, CLS) | `core-web-vitals-expert` |
| Back-end scaling and performance | `scalability-expert` |
| Solidity and OpenZeppelin | `solidity-expert` |
| LLM agents, multi-agent, memory | `ai-agent-architect` |
| Retrieval and vector databases | `rag-expert` |

The full list of merges is in the [README](../README.md#merged-skills).

## Scripts

Both scripts need only Python 3 and PyYAML (`python3 -m pip install pyyaml`) and run from any directory.

- `scripts/validate_skills.py` reads every skill and the template. It checks encoding and line endings, the frontmatter keys and `name`, the description length, `license`, `metadata.version`, forbidden sections and phrases, anchor and relative links, balanced code fences and the line-count range. It never writes files and exits 1 on errors. `--json` prints a machine-readable report.
- `scripts/generate_skill_index.py` writes `docs/skill-index.md` from the frontmatter of each skill and the `CATEGORIES` list. `--check` exits 1 when the committed index is out of date. It reports a skill folder that is missing from the list and a listed skill that has no folder.

## Versioning

The repository follows [Semantic Versioning](https://semver.org/). v3.0.0 changed the skill layout, names and frontmatter, so it is a major release; see the [changelog](../CHANGELOG.md). Each skill records its own version in `metadata.version`, which is `"3.0.0"` for every skill in this release and changes when that skill changes.

## Extension points

- **New skill:** copy `templates/skill-template/` to `skills/<name>/`, fill it in, add it to `CATEGORIES`, then validate and regenerate the index. Steps in [CONTRIBUTING.md](../CONTRIBUTING.md#add-a-skill).
- **New category:** add a `(title, [skill names])` entry to `CATEGORIES` and update the README tables.
- **Supporting files:** add `references/<topic>.md` (and link it from the References section). A skill may also ship scripts or templates if its `SKILL.md` explains when to use them.

## Changes since v2

| Aspect | v2.x | v3.0.0 |
|---|---|---|
| Skills | 93 | 67 (overlapping skills merged) |
| Body | One long file with a fixed anatomy of 30 numbered sections | At most 16 numbered sections plus `references/` files |
| Description | What plus "Use this skill when ..." | What, "Use when", and "Not for ... (use ...)" |
| Version field | Top-level `version` | `metadata.version` |
| Reply style | Sections and persona lines | Removed; user settings decide |
| Facts | Not dated | "Verified against" line per skill |
| Tooling | Migration script and validator | Validator and index generator |
