# Changelog

All notable changes to the Claude Code Ultimate Pack are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Additional skills for Rust, Go, Python, Java, C# ecosystems
- Skill composition patterns for cross-domain workflows
- Automated skill validation CI pipeline (GitHub Actions)
- Interactive skill discovery CLI tool
- Per-skill `scripts/` and `resources/` supporting files for select high-value skills

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

In v1.x, skills were typically invoked manually with `@skill-name`. In v2.0, Claude Code auto-discovers skills by reading the `description` field of every `SKILL.md` and decides whether to activate based on the user's prompt. Manual `/skill <name>` invocation still works but is no longer required for most use cases.

**Migration action**: none — auto-activation is a strict superset of manual invocation. Existing `@skill-name` and `/skill <name>` usage continues to work.

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

- **MAJOR** — Incompatible changes to skill structure, filesystem layout, or metadata format (e.g., v1.x → v2.0 migration to the official spec)
- **MINOR** — New skills added in a backwards-compatible manner
- **PATCH** — Backwards-compatible bug fixes, clarifications, or example improvements

---

## Release Process

1. Update `CHANGELOG.md` under `[Unreleased]` and add a new version header
2. Bump version in any version-tracking files
3. Create a git tag: `git tag -a v2.0.0 -m "Release 2.0.0"`
4. Push the tag: `git push origin v2.0.0`
5. Create a GitHub Release with the changelog excerpt
6. Attach a zip of the repository to the release (named `Claude-Code-Ultimate-Pack.zip`)

---

[Unreleased]: https://github.com/your-org/Claude-Code-Ultimate-Pack/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/your-org/Claude-Code-Ultimate-Pack/releases/tag/v2.0.0
[1.0.0]: https://github.com/your-org/Claude-Code-Ultimate-Pack/releases/tag/v1.0.0
