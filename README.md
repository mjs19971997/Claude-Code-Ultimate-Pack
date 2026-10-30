# Claude Code Ultimate Pack

A collection of 80 [Agent Skills](https://code.claude.com/docs/en/skills) for Claude Code covering software architecture, frontend, backend, programming languages, data, infrastructure, security, testing, mobile, blockchain, AI engineering, and scientific and academic work.

Each skill is a folder with a `SKILL.md` file. Claude Code loads a skill when your request matches its `description`, and reads the skill's `references/` files only when it needs the extra detail.

- Install, update and uninstall: [INSTALL.md](./INSTALL.md)
- What changed: [CHANGELOG.md](./CHANGELOG.md)
- Full index with descriptions: [docs/skill-index.md](./docs/skill-index.md)

License: [MIT](./LICENSE)

---

## Contents

1. [What's new in v3.0.0](#whats-new-in-v300)
2. [Quick start](#quick-start)
3. [Skills](#skills)
4. [Merged skills](#merged-skills)
5. [Skill layout](#skill-layout)
6. [Validation](#validation)
7. [Using the skills](#using-the-skills)
8. [Repository structure](#repository-structure)
9. [Contributing](#contributing)

---

## What's new in v3.0.0

Released 2026-10-30. See the [changelog](./CHANGELOG.md#300---2026-10-30) for details.

- 93 → 67 skills: overlapping skills were merged (see [Merged skills](#merged-skills)).
- Every skill was rewritten into a shorter layout of at most 16 sections, with deeper material moved into `references/` files.
- Each description now says specifically what the skill covers, when to use it ("Use when …"), and which sibling skill to use instead ("Not for …").
- The "Response Style" and "Output Format" sections and persona instructions were removed, so your own settings decide tone and reply format.
- Versions, APIs and examples were checked against current documentation in October 2026; each skill names what it was checked against.
- Frontmatter follows the Agent Skills format: the skill version is now `metadata.version`.

If you have v2.x installed, read [INSTALL.md → From v2.x to v3.0.0](./INSTALL.md#from-v2x-to-v300); some old folders have new names.

---

## Quick start

```bash
git clone https://github.com/mjs19971997/Claude-Code-Ultimate-Pack.git
```

Then copy the skill folders you want into `~/.claude/skills/` (personal) or `<project>/.claude/skills/` (project). [INSTALL.md](./INSTALL.md#install) has copy commands for Linux, macOS and Windows that skip any folder that already exists, so your other skills are never overwritten.

---

## Skills

### Architecture (8)

| Skill | Covers |
|---|---|
| `solution-architect` | End-to-end solution design, integration, migration, non-functional requirements; includes software and enterprise architecture |
| `system-design-expert` | Distributed systems: partitioning, replication, consistency, capacity |
| `clean-architecture-expert` | Dependency rule, ports and adapters, framework-independent domain code |
| `ddd-expert` | Domain-Driven Design: bounded contexts, aggregates, domain events |
| `microservices-expert` | Service boundaries, communication, data ownership, sagas |
| `code-review-expert` | Reviewing pull requests and code for correctness and maintainability |
| `refactoring-expert` | Behaviour-preserving refactoring and code smells |
| `scalability-expert` | Scaling and performance optimisation of backend systems |

### Frontend (12)

| Skill | Covers |
|---|---|
| `senior-react-19-engineer` | React 19: Actions, Server Components, the React Compiler |
| `nextjs-15-architect` | Next.js App Router, rendering, caching, Server Actions |
| `typescript-master` | Advanced TypeScript types and strict configuration |
| `tailwindcss-master` | Tailwind CSS and utility-first design systems |
| `shadcn-ui-expert` | shadcn/ui components, theming and the shadcn CLI |
| `framer-motion-expert` | Animation with Motion (Framer Motion) |
| `accessibility-expert` | WCAG, semantic HTML, ARIA, keyboard and screen reader support |
| `ui-designer` | Visual design systems, tokens, typography, colour |
| `ux-designer` | User research, information architecture, interaction design |
| `core-web-vitals-expert` | LCP, INP, CLS and front-end performance |
| `technical-seo-expert` | Crawling, indexing, Schema.org and structured data |
| `vue-expert` | Vue 3 Composition API, Pinia, Vue Router, Nuxt, Vitest |

### Backend (5)

| Skill | Covers |
|---|---|
| `nodejs-architect` | Node.js runtime, event loop, streams, workers |
| `expressjs-expert` | Express middleware, routing, error handling |
| `nestjs-expert` | NestJS modules, providers, pipes, guards |
| `graphql-expert` | GraphQL schemas, resolvers, federation, N+1 |
| `rest-api-expert` | REST resource design, HTTP semantics, OpenAPI |

### Languages (5)

| Skill | Covers |
|---|---|
| `python-expert` | Modern Python, typing, uv, ruff, pytest, asyncio |
| `go-expert` | Go modules, errors, concurrency, net/http, testing, profiling |
| `rust-expert` | Rust 2024 edition, ownership, traits, tokio, Cargo workspaces |
| `java-spring-expert` | Java 21/25 and Spring Boot, Spring Data JPA, Spring Security |
| `csharp-dotnet-expert` | C# and .NET, ASP.NET Core minimal APIs, EF Core, xUnit |

### Data (5)

| Skill | Covers |
|---|---|
| `postgresql-expert` | PostgreSQL schema design, indexing, query tuning, operations |
| `mongodb-expert` | MongoDB data modelling, indexes, aggregation |
| `redis-expert` | Redis data structures, caching patterns, persistence |
| `elasticsearch-expert` | Elasticsearch mappings, analyzers, query DSL |
| `prisma-expert` | Prisma ORM schema, migrations, queries |

### Infrastructure and DevOps (11)

| Skill | Covers |
|---|---|
| `aws-expert` | AWS services, IAM, networking |
| `kubernetes-expert` | Kubernetes workloads, networking, Helm |
| `terraform-expert` | Terraform modules, state, testing |
| `docker-expert` | Container images, runtime hardening, Docker Compose |
| `nginx-expert` | Nginx reverse proxy, TLS, load balancing |
| `linux-expert` | Linux and Ubuntu Server administration and hardening |
| `cicd-expert` | CI/CD pipelines, GitHub Actions, GitHub repository settings |
| `git-expert` | Git branching, history, recovery |
| `gcp-expert` | Google Cloud IAM, Workload Identity Federation, Cloud Run, GKE |
| `azure-expert` | Azure Entra ID, managed identities, Container Apps, AKS, Bicep |
| `observability-expert` | OpenTelemetry, Prometheus and PromQL, Grafana, SLOs and alerting |

### Security (4)

| Skill | Covers |
|---|---|
| `secure-coding-expert` | Secure coding and the OWASP Top 10 |
| `api-security-expert` | API threats, rate limiting, request signing |
| `authentication-expert` | Login, MFA, passkeys, sessions, JWT, OAuth 2.0 and OpenID Connect |
| `authorization-expert` | RBAC, ABAC, ReBAC and policy enforcement |

### Testing (4)

| Skill | Covers |
|---|---|
| `unit-testing-expert` | Unit testing practice with Jest and Vitest |
| `integration-testing-expert` | Integration and contract tests |
| `e2e-testing-expert` | End-to-end test strategy, flakiness, Cypress |
| `playwright-expert` | Playwright Test |

### Mobile (4)

| Skill | Covers |
|---|---|
| `swift-expert` | Swift, SwiftUI and UIKit |
| `android-expert` | Kotlin, Android architecture and Jetpack Compose |
| `react-native-expert` | React Native with Expo, Expo Router, EAS Build and Update |
| `flutter-expert` | Flutter and Dart, Riverpod, Bloc, go_router |

### Blockchain (11)

| Skill | Covers |
|---|---|
| `solidity-expert` | Solidity contracts and OpenZeppelin Contracts |
| `smart-contract-security-expert` | Smart contract auditing and vulnerability classes |
| `ethereum-expert` | EVM, gas, accounts, transactions, JSON-RPC |
| `ethersjs-expert` | ethers.js v6 |
| `web3js-expert` | web3.js (legacy) and migrating away from it |
| `hardhat-expert` | Hardhat projects, tests and deployments |
| `foundry-expert` | Foundry: forge, cast, anvil |
| `defi-expert` | AMMs, lending, oracles, MEV |
| `dao-expert` | On-chain governance and treasuries |
| `nft-expert` | ERC-721, ERC-1155, metadata, royalties |
| `enterprise-blockchain-architect` | Permissioned networks, including Hyperledger Fabric |

### AI and LLM (9)

| Skill | Covers |
|---|---|
| `ai-agent-architect` | LLM agent design, multi-agent systems and agent memory |
| `crewai-expert` | CrewAI agents, tasks and crews |
| `langchain-expert` | LangChain and LangGraph |
| `prompt-engineering-expert` | Prompt design and evaluation |
| `mcp-expert` | Model Context Protocol servers and clients |
| `rag-expert` | Retrieval-augmented generation and vector databases |
| `anthropic-sdk-expert` | Claude API and the Anthropic SDKs |
| `openai-sdk-expert` | OpenAI API and SDKs |
| `gemini-sdk-expert` | Gemini API and the Google Gen AI SDK |

### Scientific and Academic (2)

| Skill | Covers |
|---|---|
| `scientific-python-expert` | NumPy, SciPy, numba, reproducible simulations, Matplotlib figures |
| `latex-academic-expert` | LaTeX papers and theses, BibTeX and biblatex, arXiv submission |

---

## Merged skills

These v2.x skills no longer have their own folder. Their content now lives in the target skill, usually in a `references/` file, and the target's description names the old topic so it still triggers.

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

Installing v3.0.0 does not remove the old folders. [INSTALL.md](./INSTALL.md#from-v2x-to-v300) lists them so you can remove them yourself.

---

## Skill layout

```text
skills/<skill-name>/
├── SKILL.md          # frontmatter + up to 16 sections
└── references/       # 1-5 focused documents, read on demand
    └── <topic>.md
```

Frontmatter:

```yaml
---
name: postgresql-expert
description: >-
  <What the skill does.> Use when <concrete triggers>. Not for <confusable area> (use <other-skill>).
license: MIT
metadata:
  version: "3.0.0"
---
```

Body sections: Scope, Core Expertise, Workflow, Decision Rules, Coding Standards, Project Structure, Design Patterns, Best Practices, Performance, Security, Testing, Review Checklist, Production Notes, Examples, Common Mistakes, References. Sections with nothing specific to say are left out. The full rules are in [docs/skill-structure.md](./docs/skill-structure.md).

---

## Validation

Run these from the repository root. `PyYAML` is required (`python -m pip install pyyaml`).

```bash
python scripts/validate_skills.py              # checks every skill; read-only
python scripts/generate_skill_index.py         # rewrites docs/skill-index.md
python scripts/generate_skill_index.py --check # exits 1 if the index is out of date
```

---

## Using the skills

- **Automatic:** describe your task. Claude Code compares it with each installed skill's `description` and loads the ones that match.
- **Direct:** type `/` and the skill name, for example `/postgresql-expert why is this query slow?`.
- **Several at once:** a task that spans areas can load several skills, for example `nestjs-expert`, `postgresql-expert` and `unit-testing-expert` for a NestJS service with tests.

More in [docs/usage-guide.md](./docs/usage-guide.md) and [examples/example-usage.md](./examples/example-usage.md).

---

## Repository structure

```text
Claude-Code-Ultimate-Pack/
├── README.md
├── INSTALL.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── skills/                       # 80 skill folders
├── templates/skill-template/     # starting point for a new skill
├── docs/
│   ├── architecture.md
│   ├── skill-structure.md
│   ├── usage-guide.md
│   ├── best-practices.md
│   └── skill-index.md            # generated by scripts/generate_skill_index.py
├── examples/example-usage.md
└── scripts/
    ├── validate_skills.py        # checks every skill (read-only)
    └── generate_skill_index.py   # writes docs/skill-index.md
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) and start from [templates/skill-template/](./templates/skill-template/). Run `python3 scripts/validate_skills.py` before opening a pull request.

## License

MIT, see [LICENSE](./LICENSE). Author: Mostafa Jalili Sanjarani.
