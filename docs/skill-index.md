# Skill Index

A complete, flat index of every skill in the Claude Code Ultimate Pack. All 93 skills live at `skills/<skill-name>/SKILL.md` per the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).

**Total skills: 93** across 11 domains.

---

## Table of Contents

- [Frontend (10 skills)](#frontend)
- [Backend (10 skills)](#backend)
- [Database (5 skills)](#database)
- [Blockchain (13 skills)](#blockchain)
- [Mobile (6 skills)](#mobile)
- [DevOps (12 skills)](#devops)
- [Architecture (8 skills)](#architecture)
- [Security (5 skills)](#security)
- [Testing (7 skills)](#testing)
- [AI (13 skills)](#ai)
- [SEO (4 skills)](#seo)

---

## Frontend (10 skills)

**Coverage**: React 19, Next.js 15, TypeScript, TailwindCSS, shadcn/ui, UI/UX, accessibility, performance, Framer Motion.

| Skill Name | Folder | Description |
|---|---|---|
| `accessibility-expert` | `skills/accessibility-expert/` | Enforces WCAG 2.2 AA across the entire stack with semantic HTML, disciplined ARIA, keyboard navigation, screen reader testing, and automated axe-core gates in CI. |
| `framer-motion-expert` | `skills/framer-motion-expert/` | Production-grade animation engineering for React with Motion 11+ — declarative variants, imperative controls, scroll-linked motion, layout animations, gestures, and 60fps perfor... |
| `nextjs-15-architect` | `skills/nextjs-15-architect/` | Architects Next.js 15 applications on the App Router with RSC, Server Actions, granular caching, and edge runtimes that scale to millions of users. |
| `performance-expert` | `skills/performance-expert/` | Hits Core Web Vitals targets (LCP < 2.5s, INP < 200ms, CLS < 0.1) through bundle discipline, image and font optimization, cache strategy, third-party taming, and 60fps rendering... |
| `senior-react-19-engineer` | `skills/senior-react-19-engineer/` | Ships production React 19 applications leveraging Actions, the React Compiler, Server Components, and concurrent primitives without compromising accessibility or performance. |
| `shadcn-ui-expert` | `skills/shadcn-ui-expert/` | Ships accessible, themeable, owned component libraries built on Radix UI, Tailwind, cva, and the shadcn/ui copy-paste philosophy — never locked into a package. |
| `tailwindcss-master` | `skills/tailwindcss-master/` | Designs scalable Tailwind 3.4+ design systems with semantic tokens, variant composition, dark mode, container queries, and zero dead CSS in production. |
| `typescript-master` | `skills/typescript-master/` | Designs and ships type-safe TypeScript 5.5+ codebases using advanced generics, conditional types, branded types, and strict `tsconfig` discipline that scale across teams and years. |
| `ui-designer` | `skills/ui-designer/` | Translates product intent into pixel-accurate, accessible, themeable design systems with tokens, fluid typography, dark mode, and motion that scale across teams and devices. |
| `ux-designer` | `skills/ux-designer/` | Designs evidence-based user experiences grounded in research, information architecture, interaction principles, and behavioral science — validated through usability testing and ... |

---

## Backend (10 skills)

**Coverage**: Node.js, Express, NestJS, REST, GraphQL, authn, authz, DDD, microservices, Clean Architecture.

| Skill Name | Folder | Description |
|---|---|---|
| `authentication-expert` | `skills/authentication-expert/` | Design and operate passwordless, multi-factor, and federated authentication systems that resist credential theft, replay, and phishing. |
| `authorization-expert` | `skills/authorization-expert/` | Design and operate authorization systems that enforce least privilege at every layer, from API route to database row, with sub-10 millisecond decisions and audit-grade evidence. |
| `clean-architecture-expert` | `skills/clean-architecture-expert/` | Architect backends where dependencies point inward, the domain stays pure, and infrastructure is a detail that can be swapped without touching the business rules. |
| `ddd-expert` | `skills/ddd-expert/` | Model complex domains with bounded contexts, aggregates, and ubiquitous language so the software reflects the business and survives years of change. |
| `expressjs-expert` | `skills/expressjs-expert/` | Production-grade Express 5 architecture: middleware chains, async error handling, route design, security middleware, sessions, file uploads, and graceful production deployment b... |
| `graphql-expert` | `skills/graphql-expert/` | Production-grade GraphQL architecture: schema design, resolvers, DataLoader batching, Relay pagination, Apollo Federation, persisted queries, complexity analysis, security, and ... |
| `microservices-expert` | `skills/microservices-expert/` | Decompose, integrate, and operate distributed backends that survive partial failure, scale independently, and remain observable across every hop. |
| `nestjs-expert` | `skills/nestjs-expert/` | Production-grade NestJS 10+ architecture: modules, DI scopes, pipes/guards/interceptors/filters, microservices, WebSockets, queues, OpenAPI, and CQRS at enterprise scale. |
| `nodejs-architect` | `skills/nodejs-architect/` | Production-grade Node.js 22+ LTS architecture: event loop mastery, async patterns, streams, worker threads, clustering, ESM, observability, and graceful shutdown. |
| `rest-api-expert` | `skills/rest-api-expert/` | Production-grade REST API design: resource modeling, HTTP semantics, status codes, idempotency, pagination, HATEOAS, content negotiation, RFC 9457 errors, caching, OpenAPI 3.1, ... |

---

## Database (5 skills)

**Coverage**: PostgreSQL, Prisma, MongoDB, Redis, ElasticSearch.

| Skill Name | Folder | Description |
|---|---|---|
| `elasticsearch-expert` | `skills/elasticsearch-expert/` | Design, shard, and operate Elasticsearch 8 clusters with optimal mappings, analyzers, query DSL, aggregations, ILM, and kNN search at any scale. |
| `mongodb-expert` | `skills/mongodb-expert/` | Design, shard, and operate MongoDB 7 clusters with optimal document models, aggregation pipelines, and replica-set high availability at any scale. |
| `postgresql-expert` | `skills/postgresql-expert/` | Design, optimize, and operate PostgreSQL 16 clusters for OLTP, OLAP, and HTAP workloads with sub-millisecond p99 latency at any scale. |
| `prisma-expert` | `skills/prisma-expert/` | Design, migrate, and operate Prisma ORM 5+ applications with type-safe queries, zero-downtime migrations, and production-grade connection pooling. |
| `redis-expert` | `skills/redis-expert/` | Design, shard, and operate Redis 7 clusters with optimal data structures, caching patterns, persistence, and high availability at any scale. |

---

## Blockchain (13 skills)

**Coverage**: Ethereum, Solidity, Hardhat, Foundry, Web3.js, ethers.js, OpenZeppelin, enterprise blockchain, smart-contract security, DeFi, DAO, NFT, Hyperledger Fabric.

| Skill Name | Folder | Description |
|---|---|---|
| `dao-expert` | `skills/dao-expert/` | Ships on-chain DAOs with OpenZeppelin Governor + TimelockController, Snapshot off-chain voting, Tally dashboards, legal wrappers (Wyoming DAO LLC, Swiss Verein), treasury multi-... |
| `defi-expert` | `skills/defi-expert/` | Designs audited DeFi primitives — constant-product and concentrated-liquidity AMMs, lending pools with kinked interest rate models, flash loans, multi-source oracles, MEV-resist... |
| `enterprise-blockchain-architect` | `skills/enterprise-blockchain-architect/` | Designs permissioned consortium ledgers — Hyperledger Fabric, R3 Corda, Besu, Quorum, Avalanche Subnets — with PBFT/QBFT consensus, channel privacy, PKI identity, GDPR-compliant... |
| `ethereum-expert` | `skills/ethereum-expert/` | Engineers production Ethereum integrations on mainnet and L2s — owning execution/consensus client selection, JSON-RPC patterns, EVM gas semantics, EIP-1559 fee logic, and finali... |
| `ethersjs-expert` | `skills/ethersjs-expert/` | Engineers production Ethereum clients with ethers.js v6 — owning providers, signers, contracts, interfaces, EIP-712 signing, ENS resolution, and BigInt-native numeric handling f... |
| `foundry-expert` | `skills/foundry-expert/` | Ships EVM smart contracts with the Foundry toolchain — owning forge build/test/script, fuzz and invariant testing, cast CLI interactions, anvil local node, and chisel REPL for p... |
| `hardhat-expert` | `skills/hardhat-expert/` | Builds and tests EVM smart contract projects with Hardhat 3 — owning HRE configuration, plugin composition, fixture-based tests, mainnet-forked integration suites, and determini... |
| `hyperledger-fabric-expert` | `skills/hyperledger-fabric-expert/` | Designs and operates permissioned blockchain networks on Hyperledger Fabric 2.x/3.x — owning channel topology, MSP hierarchy, chaincode lifecycle (Go/Node/Java), Raft ordering, ... |
| `nft-expert` | `skills/nft-expert/` | Ships NFT systems on ERC-721/1155/721A/721C/6551/404 with IPFS/Arweave metadata, Seaport marketplaces, ERC-4337 gasless minting, Chainlink VRF fair drops, EIP-2981 royalties, an... |
| `openzeppelin-expert` | `skills/openzeppelin-expert/` | Ships upgradeable, audited smart contracts on top of OpenZeppelin Contracts 5.x — modular tokens, AccessControl, Governor, UUPS/transparent proxies, and the hardhat-upgrades val... |
| `smart-contract-security-expert` | `skills/smart-contract-security-expert/` | Hunts vulnerabilities in Solidity 0.8.x contracts — reentrancy, oracle manipulation, signature malleability, MEV, delegatecall — using Slither, Mythril, Echidna, Foundry invaria... |
| `solidity-expert` | `skills/solidity-expert/` | Authors production-grade Solidity 0.8.x smart contracts with built-in overflow checks, custom errors, gas-optimized storage layouts, Foundry-based testing, and reentrancy-proof ... |
| `web3js-expert` | `skills/web3js-expert/` | Engineers production Ethereum clients with Web3.js 4.x — owning providers, contract bindings, subscriptions, ABI encoding, ENS resolution, batch requests, and TypeScript-native ... |

---

## Mobile (6 skills)

**Coverage**: Android Kotlin, Jetpack Compose, Android architecture, Swift, SwiftUI, UIKit.

| Skill Name | Folder | Description |
|---|---|---|
| `android-architecture-expert` | `skills/android-architecture-expert/` | Architect production Android apps with Clean Architecture, MVVM/MVI, modularization, Hilt DI, Room, Retrofit, Paging 3, WorkManager, DataStore, offline-first sync, and comprehen... |
| `android-kotlin-expert` | `skills/android-kotlin-expert/` | Author production-grade Kotlin 2.0+ Android code: coroutines with structured concurrency, Flow for reactive streams, type-safe serialization, null safety, DSL builders, and Kotl... |
| `jetpack-compose-expert` | `skills/jetpack-compose-expert/` | Build production-grade Jetpack Compose UIs with state hoisting, side-effect discipline, Material 3 theming, custom layouts, gesture handling, animations, accessibility, and adap... |
| `swift-expert` | `skills/swift-expert/` | Author production-grade Swift 6 code with strict concurrency (Sendable, actor isolation, structured concurrency), generics with primary associated types, protocols with PATs, pr... |
| `swiftui-expert` | `skills/swiftui-expert/` | Build production SwiftUI apps with `@Observable`, state management, custom layouts, NavigationStack, animations, gestures, accessibility, Swift Charts, widgets, app intents, and... |
| `uikit-expert` | `skills/uikit-expert/` | Build production UIKit apps with modern patterns: diffable data sources, compositional layouts, custom view controller transitions, Auto Layout, modern UIKit APIs (UISheetPresen... |

---

## DevOps (12 skills)

**Coverage**: Docker, Docker Compose, Linux, Ubuntu Server, Nginx, Git, GitHub, GitHub Actions, CI/CD, Kubernetes, Terraform, AWS.

| Skill Name | Folder | Description |
|---|---|---|
| `aws-expert` | `skills/aws-expert/` | Architect, build, and operate AWS at enterprise scale: compute, storage, networking, IAM, databases, security, serverless, CI/CD, IaC, cost, multi-account, well-architected, and... |
| `cicd-expert` | `skills/cicd-expert/` | Design end-to-end CI/CD pipelines: build, test, scan, package, deploy with progressive delivery, GitOps, environment promotion, observability, and DORA metrics. |
| `docker-compose-expert` | `skills/docker-compose-expert/` | Author production-grade compose.yaml files for local dev, CI, and single-host production with profiles, healthchecks, secrets, and override patterns. |
| `docker-expert` | `skills/docker-expert/` | Design hardened, multi-stage, multi-arch container images and operate them in production with proven runtime, networking, and security practices. |
| `git-expert` | `skills/git-expert/` | Operate Git as a senior engineer: internals, branching models, rebase, reflog recovery, signing, bisect, submodules, LFS, and CI integration. |
| `github-actions-expert` | `skills/github-actions-expert/` | Design, secure, and operate GitHub Actions workflows: triggers, jobs, matrix, caching, OIDC, reusable workflows, environments, runners, and supply-chain hardening. |
| `github-expert` | `skills/github-expert/` | Master GitHub platform features, repository governance, branch protection, organizations, security, Actions integration, packages, and developer workflows at enterprise scale. |
| `kubernetes-expert` | `skills/kubernetes-expert/` | Operate Kubernetes 1.30 clusters: workloads, networking, storage, RBAC, autoscaling, Operators, Helm, Kustomize, observability, security, and multi-cluster at production scale. |
| `linux-expert` | `skills/linux-expert/` | Operate, troubleshoot, and harden Linux servers with systemd, networking, performance tuning, and forensic debugging at senior SRE level. |
| `nginx-expert` | `skills/nginx-expert/` | Design high-throughput, secure Nginx reverse proxies and load balancers with correct location matching, TLS hardening, caching, and observability. |
| `terraform-expert` | `skills/terraform-expert/` | Design, write, and operate Terraform at scale: HCL, modules, state backends, workspaces, OIDC, drift detection, policy as code, testing, and production workflows. |
| `ubuntu-server-expert` | `skills/ubuntu-server-expert/` | Provision, harden, and operate Ubuntu LTS servers with apt, snap, netplan, systemd, AppArmor, Ubuntu Pro, and unattended-upgrades at SRE grade. |

---

## Architecture (8 skills)

**Coverage**: Software architecture, solution architecture, enterprise architecture, system design, performance optimization, scalability, refactoring, code review.

| Skill Name | Folder | Description |
|---|---|---|
| `code-review-expert` | `skills/code-review-expert/` | Conducts code reviews that detect defects, share knowledge, mentor engineers, and enforce collective ownership without bikeshedding or drive-by architecture. |
| `enterprise-architect` | `skills/enterprise-architect/` | Governs the multi-year, multi-team alignment of business capability and technology through EA frameworks, capability mapping, governance, and operating-model design. |
| `performance-optimization-expert` | `skills/performance-optimization-expert/` | Diagnoses and eliminates performance bottlenecks through measurement, profiling, and systematic optimization grounded in queueing theory and the universal scalability law. |
| `refactoring-expert` | `skills/refactoring-expert/` | Transforms the structure of existing code without changing behavior, using Fowler's catalog, code smell taxonomy, and safe workflows that make every step reversible. |
| `scalability-expert` | `skills/scalability-expert/` | Designs systems that scale predictably across the scale cube (cloning, decomposition, partitioning) while preserving consistency, observability, and cost efficiency at 1000x gro... |
| `software-architect` | `skills/software-architect/` | Designs the structural backbone of software systems by selecting architectural styles, governing quality attributes, and codifying decisions through durable documentation. |
| `solution-architect` | `skills/solution-architect/` | Designs end-to-end solutions that bridge business capability and technical execution, owning integration topology, migration strategy, NFR elicitation, and the cost/risk model. |
| `system-design-expert` | `skills/system-design-expert/` | Designs distributed systems that satisfy CAP/PACELC trade-offs, partitioning, replication, consensus, and consistency models under internet-scale workloads. |

---

## Security (5 skills)

**Coverage**: OWASP Top 10, secure coding, JWT, OAuth2, API security.

| Skill Name | Folder | Description |
|---|---|---|
| `api-security-expert` | `skills/api-security-expert/` | Architect, audit, and operate APIs against the OWASP API Top 10 with rate limiting, mTLS, HMAC signing, GraphQL security, and replay prevention. |
| `jwt-expert` | `skills/jwt-expert/` | Design, implement, and operate JSON Web Token authentication with correct algorithm selection, claim validation, rotation, revocation, and storage strategies. |
| `oauth2-expert` | `skills/oauth2-expert/` | Design, implement, and operate OAuth 2.0 and OpenID Connect flows with PKCE, secure token handling, refresh rotation, DPoP, and full compliance with RFC 9700 best practices. |
| `owasp-top-10-expert` | `skills/owasp-top-10-expert/` | Architect, audit, and remediate web applications against the OWASP Top 10 (2021) using threat modeling, SAST/DAST/IAST, and a secure SDLC. |
| `secure-coding-expert` | `skills/secure-coding-expert/` | Write, audit, and refactor code in TypeScript, Python, Go, and Java that withstands real-world attacks via input validation, output encoding, secrets management, and defense in ... |

---

## Testing (7 skills)

**Coverage**: Vitest, Jest, Playwright, Cypress, unit, integration, end-to-end.

| Skill Name | Folder | Description |
|---|---|---|
| `cypress-expert` | `skills/cypress-expert/` | Configures and writes Cypress 13+ end-to-end and component test suites with retryability, cy.intercept, custom commands, Cypress Cloud, and time-travel debugging. |
| `e2e-testing-expert` | `skills/e2e-testing-expert/` | Designs end-to-end tests that verify the entire system through the user-facing interface, with flakiness mitigation, parallelization, browser matrices, and CI deployment integra... |
| `integration-testing-expert` | `skills/integration-testing-expert/` | Designs and writes integration tests that verify multiple units together using Testcontainers, contract testing, and per-test database isolation. |
| `jest-expert` | `skills/jest-expert/` | Configures and writes Jest 29+ test suites with TypeScript support, projects for monorepos, comprehensive mocks and timers, coverage thresholds, and CI parallelization. |
| `playwright-expert` | `skills/playwright-expert/` | Designs and writes Playwright 1.40+ browser automation suites with accessibility-first locators, auto-waiting, fixtures, network interception, authentication, tracing, and CI sh... |
| `unit-testing-expert` | `skills/unit-testing-expert/` | Designs and writes unit tests that verify isolated behavior through test doubles, FIRST principles, the test pyramid, and property-based testing with shrinking. |
| `vitest-expert` | `skills/vitest-expert/` | Configures and writes Vitest 2+ test suites with Vite-native speed, ESM-first module mocking, fake timers, snapshots, coverage, and UI mode for modern TypeScript projects. |

---

## AI (13 skills)

**Coverage**: Agent architecture, MCP, LangGraph, LangChain, CrewAI, OpenAI SDK, Anthropic SDK, Gemini SDK, prompt engineering, RAG, vector databases, memory systems, multi-agent.

| Skill Name | Folder | Description |
|---|---|---|
| `ai-agent-architect` | `skills/ai-agent-architect/` | Design and operate autonomous LLM agents that reason, plan, call tools, remember, and act under production constraints. |
| `anthropic-sdk-expert` | `skills/anthropic-sdk-expert/` | Build production applications with the Anthropic SDK: Messages API, streaming, tool use, prompt caching, extended thinking, vision, documents, batch, Bedrock, and Vertex. |
| `crewai-expert` | `skills/crewai-expert/` | Build and operate role-playing, collaborative CrewAI agents that complete multi-step tasks via sequential or hierarchical crews. |
| `gemini-sdk-expert` | `skills/gemini-sdk-expert/` | Build production applications with the Google Gemini SDK: text, multimodal, long context, function calling, code execution, structured output, grounded search, embeddings, files... |
| `langchain-expert` | `skills/langchain-expert/` | Build LLM applications with LangChain: LCEL chains, agents, retrieval, memory, callbacks, streaming, and production hardening. |
| `langgraph-expert` | `skills/langgraph-expert/` | Build stateful, multi-actor LLM agents in LangGraph with cycles, persistence, human-in-the-loop gates, and streaming. |
| `mcp-expert` | `skills/mcp-expert/` | Build, ship, and operate Model Context Protocol servers and clients that connect AI assistants to external data and tools. |
| `memory-systems-expert` | `skills/memory-systems-expert/` | Design, build, and operate production memory systems for AI agents: short-term, long-term, episodic, semantic, procedural memory; storage, retrieval, forgetting, consolidation, ... |
| `multi-agent-expert` | `skills/multi-agent-expert/` | Design, build, and operate production multi-agent systems: topologies, communication, orchestration, roles, task allocation, coordination, failure handling, concurrency, state, ... |
| `openai-sdk-expert` | `skills/openai-sdk-expert/` | Build production applications with the OpenAI SDK: chat completions, streaming, tool calling, structured outputs, vision, audio, embeddings, files, fine-tuning, batch, assistant... |
| `prompt-engineering-expert` | `skills/prompt-engineering-expert/` | Design, version, evaluate, and productionize prompts that behave reliably across model upgrades: patterns, structured output, security, eval, and CI/CD. |
| `rag-expert` | `skills/rag-expert/` | Design, build, evaluate, and operate production retrieval-augmented generation systems: chunking, embeddings, vector stores, retrieval, reranking, generation, evaluation, and ad... |
| `vector-database-expert` | `skills/vector-database-expert/` | Design, build, and operate production vector databases: embeddings, ANN algorithms, distance metrics, indexing, hybrid search, filtering, multi-tenancy, scaling, and observability. |

---

## SEO (4 skills)

**Coverage**: Technical SEO, Core Web Vitals, Schema.org, structured data.

| Skill Name | Folder | Description |
|---|---|---|
| `core-web-vitals-expert` | `skills/core-web-vitals-expert/` | Optimize Core Web Vitals (LCP, INP, CLS, FCP, TTFB, TBT) to Google thresholds, prevent regressions, and ship measurable performance improvements across lab and field data. |
| `schema-org-expert` | `skills/schema-org-expert/` | Author, validate, and operate Schema.org structured data using JSON-LD for Google rich results, entity disambiguation, and E-E-A-T signals. |
| `structured-data-expert` | `skills/structured-data-expert/` | Architect structured data at scale across headless CMS, server-side generation, and multi-platform commerce; validate in CI; monitor in Search Console; build entity-based SEO wi... |
| `technical-seo-expert` | `skills/technical-seo-expert/` | Architect, audit, and operate technical SEO with optimal crawling, indexing, site architecture, redirects, JavaScript rendering, and log file analysis. |

---

## How to Use This Index

1. **Find by domain**: scan the tables above to find skills relevant to your work.
2. **Find by name**: use your editor's find-in-page (`Cmd/Ctrl + F`) to search for a specific skill name.
3. **Activate**: skills auto-activate based on the `description` field in their YAML frontmatter. You can also force-activate with `/skill <skill-name>`.
4. **Compose**: multiple skills can be active simultaneously. For example, building an authenticated REST API with PostgreSQL naturally composes `nestjs-expert`, `authentication-expert`, `postgresql-expert`, and `jest-expert`.

## See Also

- [`docs/usage-guide.md`](./usage-guide.md) — detailed usage patterns
- [`examples/example-usage.md`](../examples/example-usage.md) — real-world scenarios
- [`docs/skill-structure.md`](./skill-structure.md) — the 30-section skill anatomy specification
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — how to add a new skill
