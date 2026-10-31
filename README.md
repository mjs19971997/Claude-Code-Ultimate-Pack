# Claude Code Ultimate Pack

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Spec: Agent Skills](https://img.shields.io/badge/Spec-Agent%20Skills-7c3aed.svg)](https://code.claude.com/docs/en/skills)
[![Skills: 105](https://img.shields.io/badge/Skills-105-orange.svg)](./docs/skill-index.md)
[![Domains: 12](https://img.shields.io/badge/Domains-13-purple.svg)](#skill-domains)
[![Validation: 0 errors](https://img.shields.io/badge/Validation-0%20errors-brightgreen.svg)](#validation)

A collection of 105 [Agent Skills](https://code.claude.com/docs/en/skills) for Claude Code covering software architecture, frontend, backend, programming languages, data, infrastructure, security, testing, mobile, blockchain, AI and machine learning, scientific and academic work, and telecom research.

Each skill is a folder with a `SKILL.md` file. Claude Code loads a skill when your request matches its `description`, and reads the skill's `references/` files only when it needs the extra detail.

- Install, update and uninstall: [INSTALL.md](./INSTALL.md)
- What changed: [CHANGELOG.md](./CHANGELOG.md)
- Full index with descriptions: [docs/skill-index.md](./docs/skill-index.md)

License: [MIT](./LICENSE)

---

## Contents

1. [What's new in v3.1.0](#whats-new-in-v310)
2. [Quick start](#quick-start)
3. [Skill domains](#skill-domains)
4. [Skills](#skills)
5. [Merged skills](#merged-skills)
6. [Skill layout](#skill-layout)
7. [Validation](#validation)
8. [Using the skills](#using-the-skills)
9. [Repository structure](#repository-structure)
10. [Contributing](#contributing)

---

## What's new in v3.1.0

Released 2026-10-30. See the [changelog](./CHANGELOG.md#310---2026-10-30) for details.

- 67 → 80 skills: 13 new skills in the v3 layout.
- New **Languages** domain: `python-expert`, `go-expert`, `rust-expert`, `java-spring-expert`, `csharp-dotnet-expert`.
- New **Scientific and Academic** domain: `scientific-python-expert`, `latex-academic-expert`.
- Also new: `vue-expert`, `react-native-expert`, `flutter-expert`, `gcp-expert`, `azure-expert`, `observability-expert`.
- No skill was renamed or removed, so updating from v3.0.0 needs no clean-up.

### v3.0.0

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

## Skill domains

The 105 skills cover 13 work domains. The folder layout is flat, as the Agent Skills format requires; the domain is only a grouping in this README and in [docs/skill-index.md](./docs/skill-index.md).

| Domain | Count | Coverage |
|---|---:|---|
| Architecture | 8 | Solution and system design, Clean Architecture, DDD, microservices, code review, refactoring, scalability |
| Frontend | 16 | React 19, Next.js, Vue 3, TypeScript, Tailwind CSS, shadcn/ui, Motion, accessibility, UI and UX design, Core Web Vitals, technical SEO, Svelte 5 and SvelteKit, Angular, TanStack Query and Zustand, Electron and Tauri desktop apps |
| Backend | 9 | Node.js, Express, NestJS, GraphQL, REST, FastAPI, Django, Kafka and RabbitMQ, gRPC |
| Languages | 7 | Python, Go, Rust, Java and Spring Boot, C# and .NET, C++20 and C++23, Bash scripting |
| Data | 6 | PostgreSQL, MongoDB, Redis, Elasticsearch, Prisma, pandas, Polars and DuckDB analysis |
| Infrastructure and DevOps | 13 | AWS, Google Cloud, Azure, Kubernetes, Terraform, Docker, Nginx, Linux, CI/CD, Git, observability, Ansible, Cloudflare Workers |
| Security | 5 | Secure coding and OWASP Top 10, API security, authentication, authorization, software supply chain (SBOM, Sigstore, SLSA) |
| Testing | 5 | Unit, integration and end-to-end testing, Playwright, load testing with k6 and Locust |
| Mobile | 4 | Swift and SwiftUI, Android and Jetpack Compose, React Native with Expo, Flutter |
| Blockchain | 13 | Solidity, smart contract security, Ethereum, ethers.js, web3.js, Hardhat, Foundry, DeFi, DAO, NFT, account abstraction (ERC-4337, EIP-7702), Solana and Anchor, enterprise blockchain |
| AI and LLM | 12 | Agent architecture, MCP, RAG, prompt engineering, LangChain, CrewAI, Anthropic, OpenAI and Gemini SDKs, PyTorch, ML engineering with scikit-learn and MLflow, LLM fine-tuning |
| Scientific and Academic | 5 | Scientific Python, LaTeX papers and theses, MATLAB, scientific writing, applied statistics |
| Telecom and Networking | 2 | 5G NR RAN, mobility and handover, ns-3 and 5G-LENA simulation |
| **Total** | **105** | |

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

### Frontend (16)

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
| `svelte-expert` | Svelte 5 runes, SvelteKit routing, load functions, form actions, adapters |
| `angular-expert` | Angular signals, standalone components, zoneless change detection, routing, forms, SSR |
| `tanstack-state-expert` | TanStack Query server state and Zustand client state in React apps |
| `desktop-apps-expert` | Electron and Tauri 2 desktop apps: IPC, security, packaging, signing, updates |

### Backend (9)

| Skill | Covers |
|---|---|
| `nodejs-architect` | Node.js runtime, event loop, streams, workers |
| `expressjs-expert` | Express middleware, routing, error handling |
| `nestjs-expert` | NestJS modules, providers, pipes, guards |
| `graphql-expert` | GraphQL schemas, resolvers, federation, N+1 |
| `rest-api-expert` | REST resource design, HTTP semantics, OpenAPI |
| `fastapi-expert` | FastAPI with Pydantic v2, dependencies, async SQLAlchemy, auth, testing |
| `django-expert` | Django ORM, migrations, Django REST Framework, security settings, testing |
| `kafka-messaging-expert` | Apache Kafka and RabbitMQ: producers, consumers, delivery guarantees, outbox, DLQ |
| `grpc-expert` | gRPC and Protocol Buffers, Buf, deadlines, errors, streaming, Connect |

### Languages (7)

| Skill | Covers |
|---|---|
| `python-expert` | Modern Python, typing, uv, ruff, pytest, asyncio |
| `go-expert` | Go modules, errors, concurrency, net/http, testing, profiling |
| `rust-expert` | Rust 2024 edition, ownership, traits, tokio, Cargo workspaces |
| `java-spring-expert` | Java 21/25 and Spring Boot, Spring Data JPA, Spring Security |
| `csharp-dotnet-expert` | C# and .NET, ASP.NET Core minimal APIs, EF Core, xUnit |
| `cpp-expert` | Modern C++20 and C++23, CMake, sanitizers, testing and benchmarking |
| `bash-scripting-expert` | Robust Bash and POSIX sh scripts, strict mode, quoting, ShellCheck, bats |

### Data (6)

| Skill | Covers |
|---|---|
| `postgresql-expert` | PostgreSQL schema design, indexing, query tuning, operations |
| `mongodb-expert` | MongoDB data modelling, indexes, aggregation |
| `redis-expert` | Redis data structures, caching patterns, persistence |
| `elasticsearch-expert` | Elasticsearch mappings, analyzers, query DSL |
| `prisma-expert` | Prisma ORM schema, migrations, queries |
| `data-analysis-expert` | pandas, Polars, DuckDB, Arrow and Parquet, tidy data and performance |

### Infrastructure and DevOps (13)

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
| `ansible-expert` | Ansible playbooks, roles, collections, Vault, ansible-lint and Molecule |
| `cloudflare-expert` | Cloudflare Workers, Wrangler, R2, D1, KV and Pages |

### Security (5)

| Skill | Covers |
|---|---|
| `secure-coding-expert` | Secure coding and the OWASP Top 10 |
| `api-security-expert` | API threats, rate limiting, request signing |
| `authentication-expert` | Login, MFA, passkeys, sessions, JWT, OAuth 2.0 and OpenID Connect |
| `authorization-expert` | RBAC, ABAC, ReBAC and policy enforcement |
| `supply-chain-security-expert` | SBOMs, Sigstore and cosign, SLSA provenance, dependency pinning and review |

### Testing (5)

| Skill | Covers |
|---|---|
| `unit-testing-expert` | Unit testing practice with Jest and Vitest |
| `integration-testing-expert` | Integration and contract tests |
| `e2e-testing-expert` | End-to-end test strategy, flakiness, Cypress |
| `playwright-expert` | Playwright Test |
| `load-testing-expert` | Load and performance testing with k6, plus Locust |

### Mobile (4)

| Skill | Covers |
|---|---|
| `swift-expert` | Swift, SwiftUI and UIKit |
| `android-expert` | Kotlin, Android architecture and Jetpack Compose |
| `react-native-expert` | React Native with Expo, Expo Router, EAS Build and Update |
| `flutter-expert` | Flutter and Dart, Riverpod, Bloc, go_router |

### Blockchain (13)

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
| `account-abstraction-expert` | ERC-4337, EntryPoint, paymasters, ERC-7562, EIP-7702, smart accounts and modules |
| `solana-expert` | Solana programs with Anchor, @solana/kit clients, LiteSVM tests |
| `enterprise-blockchain-architect` | Permissioned networks, including Hyperledger Fabric |

### AI and LLM (12)

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
| `pytorch-expert` | PyTorch training loops, mixed precision, torch.compile, data loading, DDP and FSDP |
| `ml-engineering-expert` | scikit-learn pipelines, data leakage, MLflow tracking, model serving |
| `llm-finetuning-expert` | Fine-tuning open LLMs with transformers, PEFT/LoRA and TRL, and evaluation |

### Scientific and Academic (5)

| Skill | Covers |
|---|---|
| `scientific-python-expert` | NumPy, SciPy, numba, reproducible simulations, Matplotlib figures |
| `latex-academic-expert` | LaTeX papers and theses, BibTeX and biblatex, arXiv submission |
| `matlab-expert` | MATLAB language, performance, testing, figures, 5G and Communications Toolboxes |
| `scientific-writing-expert` | Paper structure, abstracts, related work, figures, reviewer responses |
| `statistics-expert` | Hypothesis tests, confidence intervals, effect sizes, simulation output analysis |

### Telecom and Networking (2)

| Skill | Covers |
|---|---|
| `5g-nr-3gpp-expert` | 5G NR RAN, RRC, measurement events, handover and CHO, beam management, TR 38.901 channel models |
| `ns3-expert` | ns-3 simulator and the 5G-LENA nr module, tracing, reproducible runs |

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
├── skills/                       # 105 skill folders
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
