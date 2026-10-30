# Changelog

All notable changes to the Claude Code Ultimate Pack are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Additional skills for Rust, Go, Python, Java and C# ecosystems
- Running `scripts/validate_skills.py` in CI on every pull request

---

## [3.0.0] — 2026-10-25

### Headline

93 skills became 67. Overlapping skills were merged, every skill was rewritten into a shorter layout with `references/` files, and facts and examples were checked against current documentation (2026-10).

### Breaking changes

- **Merged skills.** 27 skill folders were merged into other skills and one new folder, `android-expert`, was added. Installing v3.0.0 does not remove the old folders; see [INSTALL.md → From v2.x to v3.0.0](./INSTALL.md#from-v2x-to-v300).

  | Old skill (v2.x) | Merged into |
  |---|---|
  | `software-architect`, `enterprise-architect` | `solution-architect` |
  | `schema-org-expert`, `structured-data-expert` | `technical-seo-expert` |
  | `cypress-expert` | `e2e-testing-expert` |
  | `jest-expert`, `vitest-expert` | `unit-testing-expert` |
  | `swiftui-expert`, `uikit-expert` | `swift-expert` |
  | `android-architecture-expert`, `android-kotlin-expert`, `jetpack-compose-expert` | `android-expert` (new) |
  | `performance-expert` | `core-web-vitals-expert` |
  | `performance-optimization-expert` | `scalability-expert` |
  | `owasp-top-10-expert` | `secure-coding-expert` |
  | `jwt-expert`, `oauth2-expert` | `authentication-expert` |
  | `docker-compose-expert` | `docker-expert` |
  | `github-actions-expert`, `github-expert` | `cicd-expert` |
  | `vector-database-expert` | `rag-expert` |
  | `hyperledger-fabric-expert` | `enterprise-blockchain-architect` |
  | `multi-agent-expert`, `memory-systems-expert` | `ai-agent-architect` |
  | `langgraph-expert` | `langchain-expert` |
  | `ubuntu-server-expert` | `linux-expert` |
  | `openzeppelin-expert` | `solidity-expert` |

- **Frontmatter.** `version` moved under `metadata` (`metadata.version: "3.0.0"`). Only the keys `name`, `description`, `license`, `allowed-tools`, `metadata` and `compatibility` are used.
- **Body layout.** The 30-section layout was replaced by at most 16 numbered sections (Scope, Core Expertise, Workflow, Decision Rules, Coding Standards, Project Structure, Design Patterns, Best Practices, Performance, Security, Testing, Review Checklist, Production Notes, Examples, Common Mistakes, References). See [docs/skill-structure.md](./docs/skill-structure.md).

### Changed

- Every `SKILL.md` was rewritten: duplicated sections merged (Anti Patterns into Common Mistakes, Thinking Process into Workflow, the two folder trees into one) and generic deployment, logging and monitoring boilerplate removed. Most skills are now 200-400 lines.
- Deeper material (long examples, extended tables, sub-topics of merged skills, migration guides) moved into `skills/<name>/references/*.md`, which Claude Code reads only when needed.
- Descriptions are specific to each skill, with a "Use when …" sentence and, where a sibling skill could be confused, a "Not for … (use …)" clause. The 11 shared category sentences that made many skills load together were removed.
- Versions, APIs and examples were checked against current official documentation in October 2026. Each skill states what it was verified against. Retired models, discontinued tools and outdated APIs were replaced or removed.
- Insecure example code was fixed (for example secrets in client bundles, untrusted input in CI `run:` steps, missing tenant filters on writes, `NOPASSWD:ALL`, test endpoints reachable in production).
- `git-expert` now treats force-pushes, deleting remote branches and global Git config changes as steps to take only when the user asks.
- `INSTALL.md` rewritten: install copies folders without overwriting existing skills; update replaces only the pack's own folders after a backup; uninstall removes only the pack's folders by name, to a backup folder or the Recycle Bin.
- `README.md`, `CONTRIBUTING.md`, `docs/*` and `examples/example-usage.md` updated for the new layout and names.
- `templates/skill-template/SKILL.md` rewritten for the new layout.
- `scripts/` use paths relative to the repository and only write inside it; the validator only reads files and no longer installs packages.

### Removed

- The "Response Style" and "Output Format" sections and persona lines ("You are a Principal …", "final authority"). Your own instructions decide tone and reply format.
- Documentation of commands that do not exist (`claude restart`, `/skill <name>`). Skills load by description, or directly as `/<skill-name>`.
- Install instructions that deleted the whole skills folder, other packs' skills, or added antivirus exclusions.

---

## [2.0.0] — 2026-08-04

### Headline

**Full migration to the official [Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).** Every skill is now a folder containing a `SKILL.md` file with YAML frontmatter, matching the layout Anthropic uses in their reference [`anthropics/skills`](https://github.com/anthropics/skills) repository.

### Migration Summary

| Metric | Value |
|---|---|
| Skills migrated | 93 / 93 |
| Skills failed | 0 |
| Domains preserved | 11 (ai, architecture, backend, blockchain, database, devops, frontend, mobile, security, seo, testing) |
| Validator result | `Overall pass: True` (93/93 skills, 4/4 repo checks) |
| Body content preservation | ≥ 95% on every skill (most are 100%) |
| Spec reference | <https://code.claude.com/docs/en/skills> |

### Breaking Changes

> ⚠️ **Migration required.** v1.x installations must be removed before installing v2.0. See [`INSTALL.md#upgrade`](./INSTALL.md#upgrade) for step-by-step instructions.

#### BC-1: Skill filesystem layout changed

| Aspect | v1.x | v2.0 |
|---|---|---|
| Skill location | `skills/<domain>/<skill-name>.md` | `skills/<skill-name>/SKILL.md` |
| Skill entry point | `<skill-name>.md` (a file) | `SKILL.md` (inside a folder) |
| Domain subdirectories | 11 folders under `skills/` | Removed — flat layout |
| Folder name | N/A (was a file) | Must match the `name` field in YAML frontmatter |

**Migration action**: delete `~/.claude/skills/{ai,architecture,backend,blockchain,database,devops,frontend,mobile,security,seo,testing}/` then copy `skills/*` from v2.0 into `~/.claude/skills/`.

#### BC-2: Skill metadata format changed

| Field | v1.x | v2.0 |
|---|---|---|
| Skill name | `# Skill: <Human-Readable Name>` H1 header | YAML frontmatter `name:` field (kebab-case, max 64 chars) |
| Description | `> <description>` blockquote | YAML frontmatter `description:` field (folded scalar) |
| Domain | `**Domain**: <domain>` metadata line | Mentioned inside `description:` (no separate field) |
| Role level | `**Role Level**: <Senior\|Staff\|Principal>` metadata line | Mentioned inside `## 1. Role` body section |
| File path | `**File**: <path>` metadata line | Removed — folder name is the canonical identifier |
| License | Not recorded per-skill | YAML frontmatter `license: MIT` |
| Version | Not recorded per-skill | YAML frontmatter `version: 1.0.0` |

**Migration action**: none for end users. Contributors must use the new template at [`templates/skill-template/SKILL.md`](./templates/skill-template/SKILL.md).

#### BC-3: Template location changed

| Aspect | v1.x | v2.0 |
|---|---|---|
| Template path | `templates/skill-template.md` (a file) | `templates/skill-template/SKILL.md` (a folder) |

**Migration action**: update any scripts or documentation that reference the old template path.

#### BC-4: Installation commands changed

| Platform | v1.x command | v2.0 command |
|---|---|---|
| Linux / macOS | `cp -r skills/* ~/.claude/skills/` (works, but creates nested dirs) | `cp -r skills/* ~/.claude/skills/` (now correct: each skill is a folder) |
| Windows | `xcopy /E skills\* %USERPROFILE%\.claude\skills\` | `Copy-Item -Path skills\* -Destination $HOME\.claude\skills\ -Recurse` |

The commands look similar but the **semantics** changed: in v1.x, `cp -r skills/*` copied 11 domain folders; in v2.0, it copies 93 skill folders. End-user workflows that auto-discover skills (e.g., `claude skills list`) will see a different (correct) result.

#### BC-5: Skill discovery mechanism changed

In v1.x, skills were typically invoked manually with `@skill-name`. In v2.0, Claude Code auto-discovers skills by reading the `description` field of every `SKILL.md` and decides whether to activate based on the user's prompt. (Correction in v3.0.0: Claude Code has no `/skill <name>` command; a skill is called directly as `/<skill-name>`.)

**Migration action**: none — auto-activation is a strict superset of manual invocation. 

### Added

#### Repository Foundation
- New `README.md` documenting the v2.0 layout, the official spec, the migration guide, and platform-specific quick start
- New `INSTALL.md` covering Windows (PowerShell + WSL2 + Git Bash), Linux, and macOS — global, project-local, manual, selective, submodule, upgrade, validation, common errors, and troubleshooting
- Updated `CONTRIBUTING.md` enforcing the official spec — v1.x layout contributions are no longer accepted
- Updated `CHANGELOG.md` (this entry)
- `LICENSE` (MIT) — unchanged from v1.x
- `scripts/migrate_skills.py` — the migration script that produced v2.0 from v1.x
- `scripts/validate_skills.py` — the validator that enforces spec compliance

#### Migrated Skills (93 total)

All 93 skills migrated from `skills/<domain>/<skill-name>.md` to `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`, `license: MIT`, `version: 1.0.0`). Body content preserved verbatim from v1.x.

##### Frontend Domain (10 skills)
- `accessibility-expert` — WCAG 2.2 AA/AAA, ARIA, keyboard, screen readers
- `framer-motion-expert` — production animations, gestures, layout animations
- `nextjs-15-architect` — App Router, RSC, streaming, middleware, edge runtime
- `performance-expert` — Web Vitals, rendering, bundle optimization
- `senior-react-19-engineer` — React 19 Actions, Compiler, Server Components
- `shadcn-ui-expert` — Radix-based accessible component architecture
- `tailwindcss-master` — utility-first design systems
- `typescript-master` — advanced types, generics, inference, strict mode
- `ui-designer` — visual design systems, design tokens
- `ux-designer` — user research, IA, interaction design

##### Backend Domain (10 skills)
- `authentication-expert` — authn patterns, sessions, MFA
- `authorization-expert` — RBAC, ABAC, policy enforcement
- `clean-architecture-expert` — dependencies inward, separation of concerns
- `ddd-expert` — Domain-Driven Design, bounded contexts, aggregates
- `expressjs-expert` — Express.js middleware, routing, production hardening
- `graphql-expert` — schemas, resolvers, federation, N+1
- `microservices-expert` — service boundaries, communication, transactions
- `nestjs-expert` — modules, providers, DI, decorators
- `nodejs-architect` — event loop, streams, clustering, performance
- `rest-api-expert` — REST constraints, versioning, HATEOAS

##### Database Domain (5 skills)
- `elasticsearch-expert` — mappings, analyzers, query DSL
- `mongodb-expert` — schemas, indexes, aggregation pipeline
- `postgresql-expert` — PostgreSQL 16, OLTP/OLAP/HTAP
- `prisma-expert` — schema, migrations, queries, performance
- `redis-expert` — data structures, persistence, clustering

##### Blockchain Domain (13 skills)
- `dao-expert` — governance, voting, treasury
- `defi-expert` — AMMs, lending, oracles, MEV
- `enterprise-blockchain-architect` — consortium, permissioned networks
- `ethereum-expert` — EVM, gas, accounts, RPC
- `ethersjs-expert` — ethers.js v6, providers, signers, contracts
- `foundry-expert` — Forge, Cast, Anvil, fuzz testing
- `hardhat-expert` — tasks, plugins, network config
- `hyperledger-fabric-expert` — channels, chaincode, MSPs
- `nft-expert` — ERC-721, ERC-1155, metadata, royalties
- `openzeppelin-expert` — AccessControl, Upgradeable, SafeERC20
- `smart-contract-security-expert` — reentrancy, access control, audits
- `solidity-expert` — Solidity 0.8+, gas optimization, patterns
- `web3js-expert` — web3.js v4, contracts, providers

##### Mobile Domain (6 skills)
- `android-architecture-expert` — Clean Architecture, MVVM, MVI
- `android-kotlin-expert` — Kotlin, coroutines, Flow
- `jetpack-compose-expert` — Compose, Material 3, state
- `swift-expert` — Swift 5.9+, concurrency, generics
- `swiftui-expert` — SwiftUI, layouts, animations
- `uikit-expert` — UIKit, Auto Layout, view controllers

##### DevOps Domain (12 skills)
- `aws-expert` — EC2, S3, RDS, IAM, CloudFormation
- `cicd-expert` — pipeline design, secrets, artifacts
- `docker-compose-expert` — multi-service, networks, volumes
- `docker-expert` — multi-stage, multi-arch, runtime hardening
- `git-expert` — branching, rebasing, history rewriting
- `github-actions-expert` — workflows, runners, actions
- `github-expert` — repos, PRs, releases, security
- `kubernetes-expert` — Deployments, Services, Ingress, Helm
- `linux-expert` — systemd, processes, networking
- `nginx-expert` — reverse proxy, load balancing, TLS
- `terraform-expert` — modules, state, providers
- `ubuntu-server-expert` — server hardening, package management

##### Architecture Domain (8 skills)
- `code-review-expert` — review process, anti-patterns, checklist
- `enterprise-architect` — multi-team, multi-year systems
- `performance-optimization-expert` — profiling, bottlenecks, scaling
- `refactoring-expert` — safe refactoring, patterns, code smells
- `scalability-expert` — horizontal/vertical, sharding, caching
- `software-architect` — patterns, trade-offs, documentation
- `solution-architect` — end-to-end solutions, integration
- `system-design-expert` — capacity, availability, consistency

##### Security Domain (5 skills)
- `api-security-expert` — REST/GraphQL security, rate limiting
- `jwt-expert` — JWT structure, validation, rotation
- `oauth2-expert` — flows, PKCE, refresh tokens
- `owasp-top-10-expert` — OWASP Top 10, mitigation
- `secure-coding-expert` — input validation, output encoding, secrets

##### Testing Domain (7 skills)
- `cypress-expert` — E2E, component testing, CI
- `e2e-testing-expert` — E2E strategy, flakiness, parallelism
- `integration-testing-expert` — service boundaries, contracts
- `jest-expert` — Jest config, snapshots, mocking
- `playwright-expert` — Playwright, fixtures, browser contexts
- `unit-testing-expert` — unit testing principles, mocking, coverage
- `vitest-expert` — Vitest, workspace, snapshots

##### AI Domain (13 skills)
- `ai-agent-architect` — agent anatomy, reasoning patterns, production hardening
- `anthropic-sdk-expert` — Anthropic SDK, messages API, tool use
- `crewai-expert` — CrewAI, roles, tasks, crews
- `gemini-sdk-expert` — Gemini SDK, multimodal, function calling
- `langchain-expert` — LangChain, chains, agents, memory
- `langgraph-expert` — LangGraph, stateful graphs, conditional edges
- `mcp-expert` — Model Context Protocol, servers, resources, tools
- `memory-systems-expert` — working/short/long-term memory, vector stores
- `multi-agent-expert` — orchestration, communication, failure handling
- `openai-sdk-expert` — OpenAI SDK, function calling, streaming
- `prompt-engineering-expert` — prompts, few-shot, chain-of-thought
- `rag-expert` — chunking, embedding, retrieval, reranking
- `vector-database-expert` — pgvector, Pinecone, Weaviate, Qdrant

##### SEO Domain (4 skills)
- `core-web-vitals-expert` — LCP, INP, CLS optimization
- `schema-org-expert` — Schema.org vocabularies, JSON-LD
- `structured-data-expert` — rich results, validation
- `technical-seo-expert` — crawlability, indexing, log file analysis

### Changed

- `README.md` — fully rewritten for v2.0
- `INSTALL.md` — fully rewritten with Windows/Linux/macOS coverage
- `CONTRIBUTING.md` — fully rewritten to enforce the official spec
- `templates/` — moved from `templates/skill-template.md` to `templates/skill-template/SKILL.md`
- All 93 skills — converted from `skills/<domain>/<skill-name>.md` to `skills/<skill-name>/SKILL.md` with YAML frontmatter; body content preserved

### Removed

- 11 legacy domain subdirectories under `skills/` (`ai/`, `architecture/`, `backend/`, `blockchain/`, `database/`, `devops/`, `frontend/`, `mobile/`, `security/`, `seo/`, `testing/`)
- 93 legacy `<skill-name>.md` files (replaced by `<skill-name>/SKILL.md`)
- Legacy `templates/skill-template.md` (replaced by `templates/skill-template/SKILL.md`)
- Legacy `# Skill: <Name>` H1 header pattern
- Legacy `**Domain**:`, `**Role Level**:`, `**File**:` metadata block

### Engineering Standards (unchanged from v1.x)

Every skill in this release continues to enforce:
- SOLID, DRY, KISS, YAGNI principles
- Clean Architecture and Feature-Based Architecture
- Security-first and performance-first thinking
- Production-ready output with no placeholders
- Comprehensive testing strategy
- Complete documentation standards
- Four mandatory checklists (code review, refactoring, deployment, production)
- Concrete code examples
- Anti-patterns and common mistakes documentation

### Documentation

- Complete 30-section skill anatomy specification (preserved)
- Cross-cutting best practices guide covering all 11 domains (preserved)
- Real-world usage examples for frontend, backend, DevOps, AI, and blockchain scenarios (preserved)
- Comprehensive installation guide with platform-specific instructions (rewritten)
- Contribution guide with official-spec compliance rules (rewritten)
- Migration guide for v1.x → v2.0 upgrade (new)

---

## [1.0.0] — 2026-08-04 (historical, pre-migration)

### Added

#### Initial Release

The first stable, production-ready release of the Claude Code Ultimate Pack. Used the legacy v1.x layout (`skills/<domain>/<skill-name>.md`) — see the v2.0.0 entry above for the migration to the official spec.

#### Repository Foundation (v1.x)
- `README.md` with complete project overview, structure, and usage instructions
- `INSTALL.md` covering 5 installation methods (global, project-local, selective, submodule, symlink)
- `CHANGELOG.md` following Keep a Changelog 1.1.0
- `LICENSE` — MIT
- `CONTRIBUTING.md` with contribution workflow and quality standards
- `docs/architecture.md` — repository architecture documentation
- `docs/skill-structure.md` — 30-section skill anatomy specification
- `docs/usage-guide.md` — comprehensive usage guide
- `docs/best-practices.md` — cross-cutting engineering best practices
- `docs/skill-index.md` — complete index of all 93 skills
- `templates/skill-template.md` — template for authoring new skills
- `examples/example-usage.md` — real-world usage scenarios

#### 93 Skills Across 11 Domains (v1.x layout)
All skills listed in the v2.0.0 entry above were originally authored in v1.x with the legacy layout. The body content of each skill is identical between v1.x and v2.0.0 — only the filesystem layout and metadata format changed.

---

## Versioning Policy

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — Incompatible changes to skill structure, filesystem layout, or metadata format (e.g., the v1.x → v2.0 layout migration, or the v3.0.0 skill merges)
- **MINOR** — New skills added in a backwards-compatible manner
- **PATCH** — Backwards-compatible bug fixes, clarifications, or example improvements

---

## Release Process

1. Update `CHANGELOG.md` under `[Unreleased]` and add a new version header
2. Bump version in any version-tracking files
3. Create a git tag: `git tag -a vX.Y.Z -m "Release X.Y.Z"`
4. Push the tag: `git push origin vX.Y.Z`
5. Create a GitHub Release with the changelog excerpt
6. Attach a zip of the repository to the release (named `Claude-Code-Ultimate-Pack.zip`)

---

[Unreleased]: https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/releases/tag/v3.0.0
[2.0.0]: https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/releases/tag/v2.0.0
[1.0.0]: https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/releases/tag/v1.0.0
