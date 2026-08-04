# Claude Code Ultimate Pack

> The most comprehensive, production-ready collection of **Agent Skills** for Claude Code — 93 specialized expert personas across 11 engineering domains, fully migrated to the official [Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Spec: Claude Code Agent Skills](https://img.shields.io/badge/Spec-Claude%20Code%20Agent%20Skills-7c3aed.svg)](https://code.claude.com/docs/en/skills)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()
[![Skills: 93](https://img.shields.io/badge/Skills-93-orange.svg)]()
[![Domains: 11](https://img.shields.io/badge/Domains-11-purple.svg)]()

---

## Table of Contents

1. [Overview](#overview)
2. [What's New in v2.0](#whats-new-in-v20)
3. [Repository Structure](#repository-structure)
4. [Skill Anatomy](#skill-anatomy)
5. [Skill Domains](#skill-domains)
6. [Installation](#installation)
7. [Updating](#updating)
8. [Usage](#usage)
9. [Skill Structure (Official Spec)](#skill-structure-official-spec)
10. [Example Use Cases](#example-use-cases)
11. [Migration Guide (v1 → v2)](#migration-guide-v1--v2)
12. [Troubleshooting](#troubleshooting)
13. [Contributing](#contributing)
14. [Changelog](#changelog)
15. [License](#license)

---

## Overview

**Claude Code Ultimate Pack** is a meticulously engineered collection of [Agent Skills](https://code.claude.com/docs/en/skills) for Claude Code. Each skill is a self-contained folder containing a `SKILL.md` file with YAML frontmatter and a deeply-structured instruction set that constrains Claude Code to behave like a world-class specialist (staff/principal level, 20+ years of experience) in a specific technology, framework, or discipline.

This is not a collection of short prompts. Each `SKILL.md` is a 300–1000 line, production-grade specification covering role definition, thinking processes, decision-making rules, architecture rules, coding standards, naming conventions, folder structures, design patterns, best practices, anti-patterns, performance rules, security rules, testing strategies, documentation standards, code review checklists, refactoring checklists, deployment checklists, production checklists, logging strategies, monitoring strategies, error handling, examples, common mistakes, professional workflows, response styles, and output formats.

Every skill is engineered to produce code and decisions that are:

- **Production-ready** — no prototypes, no placeholders, no shortcuts
- **Secure by design** — following OWASP, CIS, and vendor-specific hardening guides
- **Performant** — optimized for latency, throughput, and resource efficiency
- **Maintainable** — readable, documented, tested, and refactoring-friendly
- **Scalable** — designed to grow from 1 user to 1,000,000 users without rewrites

---

## What's New in v2.0

Version 2.0 is a **full migration** to the official [Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills). The repository is now 100% spec-compliant and works out-of-the-box with the latest Claude Code GUI.

### Breaking Changes from v1.x

| Aspect | v1.x (Legacy) | v2.0 (Official Spec) |
|---|---|---|
| Skill location | `skills/<domain>/<skill-name>.md` | `skills/<skill-name>/SKILL.md` |
| Skill entry point | `<skill-name>.md` | `SKILL.md` (folder name = skill name) |
| Metadata | `# Skill: <Name>` H1 + blockquote + `**Domain**: ...` block | YAML frontmatter (`name`, `description`, `license`, `version`) |
| Domain folders | 11 domain subdirectories under `skills/` | None — flat structure, matching Anthropic's reference repo |
| Skill discovery | Folder-based, manual invocation | Auto-discovered by Claude Code based on `description` field |
| Template location | `templates/skill-template.md` | `templates/skill-template/SKILL.md` |
| Installation paths | `cp skills/* ~/.claude/skills/` | `cp -r skills/* ~/.claude/skills/` (each skill is a folder) |

### Why We Migrated

The official Claude Code Agent Skills specification (published October 2025, stabilized through 2026) defines a strict skill format that enables:

1. **Automatic discovery** — Claude Code reads YAML frontmatter from every `SKILL.md` and decides which skill to invoke based on the `description` field, with no manual `@skill-name` invocation required.
2. **Cross-tool compatibility** — the same skill works in Claude Code, Claude.ai, VS Code with Claude, GitHub Copilot CLI, and any other agent that implements the spec.
3. **Composability** — skills can include supporting files (`scripts/`, `resources/`, `templates/`) inside their folder, loaded on demand.
4. **Validation** — the spec defines a precise `name` format (lowercase letters, digits, hyphens; max 64 chars) that tooling can validate.

See the [Migration Guide](#migration-guide-v1--v2) below for step-by-step upgrade instructions.

---

## Repository Structure

```
Claude-Code-Ultimate-Pack/
├── README.md                          # This file
├── INSTALL.md                         # Cross-platform installation guide
├── CHANGELOG.md                       # Version history (includes v2.0 migration)
├── CONTRIBUTING.md                    # Contribution rules (official spec only)
├── LICENSE                            # MIT License
├── skills/                            # 93 skill folders, flat structure
│   ├── accessibility-expert/
│   │   └── SKILL.md
│   ├── ai-agent-architect/
│   │   └── SKILL.md
│   ├── android-kotlin-expert/
│   │   └── SKILL.md
│   ├── ... (90 more skill folders)
│   └── ux-designer/
│       └── SKILL.md
├── templates/
│   └── skill-template/                # Official-spec template for new skills
│       └── SKILL.md
├── docs/                              # Documentation
│   ├── architecture.md
│   ├── skill-structure.md             # 30-section anatomy spec
│   ├── usage-guide.md
│   ├── best-practices.md
│   └── skill-index.md                 # Complete index of all 93 skills
└── examples/
    └── example-usage.md               # Real-world usage scenarios
```

Each skill folder follows the official spec:

```
skills/<skill-name>/
├── SKILL.md          # Required entry point with YAML frontmatter
└── (optional)        # scripts/, resources/, templates/ — loaded on demand
```

---

## Skill Anatomy

Every `SKILL.md` in this repository combines:

1. **YAML frontmatter** — the official Claude Code Agent Skills metadata block:
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

2. **30-section body** — the deeply-structured instruction set:
   1. Role · 2. Mission · 3. Core Expertise · 4. Responsibilities · 5. Thinking Process · 6. Decision Making Rules · 7. Architecture Rules · 8. Coding Standards · 9. Naming Conventions · 10. Folder Structure · 11. Project Structure · 12. Design Patterns · 13. Best Practices · 14. Anti Patterns · 15. Performance Rules · 16. Security Rules · 17. Testing Strategy · 18. Documentation Standards · 19. Code Review Checklist · 20. Refactoring Checklist · 21. Deployment Checklist · 22. Production Checklist · 23. Logging Strategy · 24. Monitoring Strategy · 25. Error Handling · 26. Examples · 27. Common Mistakes · 28. Professional Workflow · 29. Response Style · 30. Output Format

See [`docs/skill-structure.md`](./docs/skill-structure.md) for the complete specification.

---

## Skill Domains

The 93 skills span 11 engineering domains. Domain is recorded as a tag in each skill's `description` and indexed in [`docs/skill-index.md`](./docs/skill-index.md) — but the filesystem layout is flat (per the official spec).

| Domain | Count | Coverage |
|---|---:|---|
| Frontend | 10 | React 19, Next.js 15, TypeScript, TailwindCSS, shadcn/ui, UI/UX, accessibility, performance, Framer Motion |
| Backend | 10 | Node.js, Express, NestJS, REST, GraphQL, authn, authz, DDD, microservices, Clean Architecture |
| Database | 5 | PostgreSQL, Prisma, MongoDB, Redis, ElasticSearch |
| Blockchain | 13 | Ethereum, Solidity, Hardhat, Foundry, Web3.js, ethers.js, OpenZeppelin, enterprise blockchain, smart-contract security, DeFi, DAO, NFT, Hyperledger Fabric |
| Mobile | 6 | Android Kotlin, Jetpack Compose, Android architecture, Swift, SwiftUI, UIKit |
| DevOps | 12 | Docker, Docker Compose, Linux, Ubuntu Server, Nginx, Git, GitHub, GitHub Actions, CI/CD, Kubernetes, Terraform, AWS |
| Architecture | 8 | Software architecture, solution architecture, enterprise architecture, system design, performance optimization, scalability, refactoring, code review |
| Security | 5 | OWASP Top 10, secure coding, JWT, OAuth2, API security |
| Testing | 7 | Vitest, Jest, Playwright, Cypress, unit, integration, end-to-end |
| AI | 13 | Agent architecture, MCP, LangGraph, LangChain, CrewAI, OpenAI SDK, Anthropic SDK, Gemini SDK, prompt engineering, RAG, vector databases, memory systems, multi-agent |
| SEO | 4 | Technical SEO, Core Web Vitals, Schema.org, structured data |
| **Total** | **93** | |

---

## Installation

Full instructions for Windows, Linux, and macOS — global, project-local, and manual — are in [`INSTALL.md`](./INSTALL.md). Quick start:

### Global installation (Linux / macOS)

```bash
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
```

### Global installation (Windows PowerShell)

```powershell
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
Copy-Item -Path Claude-Code-Ultimate-Pack\skills\* -Destination $HOME\.claude\skills\ -Recurse
```

### Project-local installation

```bash
cd /path/to/your/project
mkdir -p .claude/skills
cp -r /path/to/Claude-Code-Ultimate-Pack/skills/* .claude/skills/
```

After installation, restart Claude Code. Skills activate automatically based on the `description` field — no manual `@skill-name` invocation required (though explicit invocation still works).

---

## Updating

```bash
# Pull the latest from your clone
cd /path/to/Claude-Code-Ultimate-Pack
git pull origin main

# Re-copy to your global skills directory (Linux / macOS)
rm -rf ~/.claude/skills/accessibility-expert ~/.claude/skills/ai-agent-architect # ... etc.
cp -r skills/* ~/.claude/skills/

# Or on Windows PowerShell
Remove-Item $HOME\.claude\skills\* -Recurse -Force
Copy-Item -Path skills\* -Destination $HOME\.claude\skills\ -Recurse
```

For project-local installs, re-copy into `.claude/skills/` and commit the change.

---

## Usage

Skills activate automatically when Claude Code detects relevant context. The `description` field in each skill's YAML frontmatter is the trigger condition — Claude reads it at startup and decides whether to invoke the skill based on the user's prompt.

### Automatic activation

Just ask Claude a question in the skill's domain:

```
Build a Next.js 15 page that fetches user data with Suspense streaming
```

Claude Code reads the `description` of `senior-react-19-engineer` and `nextjs-15-architect`, matches them against the prompt, and activates them automatically.

### Explicit invocation

You can also force-activate a skill by name:

```
/skill senior-react-19-engineer

Build a useDebounce hook that's safe for SSR
```

Or, in the Claude Code GUI, select the skill from the Skills panel.

### Composing skills

Multiple skills can be active simultaneously. For example, building an authenticated REST API with PostgreSQL would naturally compose `nestjs-expert`, `authentication-expert`, `postgresql-expert`, and `jest-expert`.

See [`docs/usage-guide.md`](./docs/usage-guide.md) for detailed patterns and [`examples/example-usage.md`](./examples/example-usage.md) for real-world scenarios.

---

## Skill Structure (Official Spec)

Per the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills):

### Required

- **A folder** named after the skill. The folder name must match the `name` field in YAML frontmatter.
- **A `SKILL.md` file** inside that folder — the entry point Claude reads.
- **YAML frontmatter** at the top of `SKILL.md`, delimited by `---` lines, with:
  - `name` (required) — lowercase letters, digits, hyphens only. Max 64 characters. Cannot start with a hyphen.
  - `description` (required) — a substantive description of what the skill does **and** when to use it. Claude uses this as the trigger condition.

### Recommended

- `license` — SPDX identifier (e.g., `MIT`).
- `version` — SemVer (e.g., `1.0.0`).

### Optional supporting files

Each skill folder may also contain:

- `scripts/` — helper scripts Claude can execute
- `resources/` — reference materials Claude can read on demand
- `templates/` — file templates Claude can copy

### Where skills live

Claude Code auto-discovers skills in:

- **Personal/global**: `~/.claude/skills/<skill-name>/SKILL.md`
- **Project-local**: `.claude/skills/<skill-name>/SKILL.md`
- **Plugin-bundled**: inside a plugin's `skills/` directory

### Validation rules (enforced in this repo)

Every `SKILL.md` in this repository passes the validation script at `scripts/validate_skills.py`:

- UTF-8 encoded, no BOM, LF line endings only
- Frontmatter parses as valid YAML
- `name` matches the folder name and conforms to `^[a-z0-9][a-z0-9-]{0,63}$`
- `description` is non-empty and at least 40 characters
- `license` and `version` are present
- Body contains the 30 mandatory section headers
- No `TODO:`, `FIXME:`, or `PLACEHOLDER:` markers in prose (outside code blocks)

---

## Example Use Cases

1. **Greenfield e-commerce backend** — compose `nestjs-expert`, `postgresql-expert`, `jest-expert`, `docker-expert`, and `aws-expert` to ship a checkout service.
2. **Smart contract audit** — invoke `solidity-expert` + `smart-contract-security-expert` to audit an ERC-20 for reentrancy and access control issues.
3. **Production incident response** — invoke `code-review-expert` + `performance-optimization-expert` + `kubernetes-expert` to diagnose and patch a latency regression.
4. **AI agent system build** — compose `ai-agent-architect`, `langgraph-expert`, `rag-expert`, and `prompt-engineering-expert` to design a multi-step tool-using agent.

See [`examples/example-usage.md`](./examples/example-usage.md) for full scenarios.

---

## Migration Guide (v1 → v2)

If you have a v1.x installation or fork, follow these steps to migrate.

### Step 1: Remove the legacy skills

The legacy layout used domain subdirectories. Remove them:

```bash
# Linux / macOS — remove the 11 legacy domain folders
rm -rf ~/.claude/skills/{ai,architecture,backend,blockchain,database,devops,frontend,mobile,security,seo,testing}

# Windows PowerShell
$domains = 'ai','architecture','backend','blockchain','database','devops','frontend','mobile','security','seo','testing'
foreach ($d in $domains) { Remove-Item -Recurse -Force "$HOME\.claude\skills\$d" }
```

### Step 2: Install the v2.0 pack

```bash
# Linux / macOS
cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/

# Windows PowerShell
Copy-Item -Path Claude-Code-Ultimate-Pack\skills\* -Destination $HOME\.claude\skills\ -Recurse
```

### Step 3: Restart Claude Code

```bash
claude restart
```

### Step 4: Verify

You should now see 93 skill folders (not 11 domain folders) under `~/.claude/skills/`:

```bash
ls ~/.claude/skills/ | wc -l   # should print 93
```

### What changed for end users

- **No more `@skill-name` invocation required** — skills auto-activate based on `description`.
- **Skill names are unchanged** — `senior-react-19-engineer` is still `senior-react-19-engineer`; it's now a folder instead of a `.md` file.
- **Content is unchanged** — every section, every checklist, every example from v1.x is preserved verbatim in v2.0.

### What changed for contributors

- New skills must follow the official spec — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the [`templates/skill-template/`](./templates/skill-template/) folder.
- The legacy `# Skill: <Name>` H1 header is replaced by YAML frontmatter.
- Domain categorization is done via the `description` field and the skill index, not via filesystem subdirectories.

---

## Troubleshooting

### Skills not appearing after installation

1. Verify each skill is a folder containing `SKILL.md`:
   ```bash
   ls ~/.claude/skills/senior-react-19-engineer/
   # Should show: SKILL.md
   ```
2. Verify the YAML frontmatter is valid:
   ```bash
   head -10 ~/.claude/skills/senior-react-19-engineer/SKILL.md
   # Should start with: ---
   ```
3. Restart Claude Code:
   ```bash
   claude restart
   ```

### Skill not auto-activating

The `description` field is the trigger. If a skill doesn't activate, either:
- The prompt doesn't match the description's "when to use" clause — try rephrasing or invoke explicitly with `/skill <name>`.
- Another skill with a more specific description is winning — check for conflicts in `~/.claude/skills/`.

### YAML parse errors

If Claude Code reports a YAML parse error in a `SKILL.md`:
1. Ensure the file starts with `---\n` (no leading blank lines, no BOM).
2. Ensure the frontmatter is closed with a second `---` line.
3. Validate locally:
   ```bash
   python3 -c "import yaml; print(yaml.safe_load(open('SKILL.md').read().split('---')[1]))"
   ```

### CRLF line endings on Windows

If you cloned with `core.autocrlf=true`, files may have CRLF endings. Force LF:

```bash
git config --global core.autocrlf false
git rm --cached -r .
git reset --hard
```

### Line-ending mismatch in WSL2

```bash
find ~/.claude/skills -name "SKILL.md" -exec dos2unix {} \;
```

See [`INSTALL.md`](./INSTALL.md) for full troubleshooting across Windows, Linux, and macOS.

---

## Contributing

Contributions are welcome. All new skills **must** follow the official Claude Code Agent Skills specification — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full workflow and the [`templates/skill-template/`](./templates/skill-template/) folder for the canonical template.

---

## Changelog

See [`CHANGELOG.md`](./CHANGELOG.md) for version history. The v2.0.0 entry documents the full migration to the official spec, including all breaking changes.

---

## License

MIT License — see [`LICENSE`](./LICENSE) for full text.

---

<p align="center">
  Built for engineers who refuse to ship anything less than production-ready.<br>
  Fully compliant with the <a href="https://code.claude.com/docs/en/skills">official Claude Code Agent Skills specification</a>.
</p>
