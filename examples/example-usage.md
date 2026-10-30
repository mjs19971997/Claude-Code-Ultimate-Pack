# Example Usage

Five scenarios that show how skills combine across a project. Skills load automatically from your request, so the prompts below name the area instead of the skill; to force a particular skill, start the prompt with `/<skill-name>`, for example `/rag-expert design the chunking strategy`. More background is in the [usage guide](../docs/usage-guide.md).

## Contents

1. [Greenfield e-commerce backend](#1-greenfield-e-commerce-backend)
2. [Legacy monolith modernization](#2-legacy-monolith-modernization)
3. [Smart contract audit](#3-smart-contract-audit)
4. [Production incident response](#4-production-incident-response)
5. [Document question answering agent](#5-document-question-answering-agent)
6. [General principles](#6-general-principles)

## 1. Greenfield e-commerce backend

Goal: a NestJS and PostgreSQL backend, containerized and deployed to AWS from GitHub Actions.

| Step | Prompt | Skills that apply |
|---|---|---|
| Architecture | "Design the architecture for an e-commerce backend: 100,000 daily users, 1,000,000 products, 10,000 orders a day, Stripe payments, Elasticsearch search, Redis cache, AWS, multi-AZ." | `system-design-expert`, `solution-architect` |
| Schema | "Design the PostgreSQL schema for users, carts, orders, products and reviews, with multi-currency prices, audit columns and indexes for the main queries." | `postgresql-expert` |
| Service | "Implement the orders module in NestJS with Prisma, use cases and repositories, validation at the boundary, and role guards." | `nestjs-expert`, `prisma-expert`, `clean-architecture-expert` |
| Auth | "Add login with short-lived JWT access tokens and rotating refresh tokens, then role-based access for customer, support and admin." | `authentication-expert`, `authorization-expert` |
| Tests | "Write unit tests for the order service with Vitest, integration tests for order placement against a real database, and a Playwright test for checkout." | `unit-testing-expert`, `integration-testing-expert`, `playwright-expert` |
| Ship | "Create a multi-stage Dockerfile for the service, then a GitHub Actions workflow that builds, tests, scans and deploys to AWS." | `docker-expert`, `cicd-expert`, `aws-expert` |
| Security | "Review the codebase against the OWASP Top 10 and review the API for rate limiting and input validation gaps." | `secure-coding-expert`, `api-security-expert` |
| Performance | "Profile the order placement flow, then design a Redis cache for the product catalog." | `scalability-expert`, `redis-expert` |

Expected result at each step: a design or code change with the reasoning, plus the commands to verify it.

## 2. Legacy monolith modernization

Goal: move a ten-year-old PHP monolith to services without downtime.

1. **Audit.** "Review this monolith and list the modules that map to separate services, the shared tables that block a split, and the riskiest code." Uses `code-review-expert` and `ddd-expert`.
2. **Plan.** "Propose a refactoring plan that starts with characterization tests and small, reversible steps." Uses `refactoring-expert`.
3. **Strangler fig.** "Route the orders endpoints through an nginx proxy to a new service while everything else stays on the monolith, and describe the cut-over and rollback." Uses `microservices-expert`, `nginx-expert`, `solution-architect`.
4. **Data.** "Decouple the orders tables: dual writes versus change data capture, and how to verify the copies match." Uses `postgresql-expert`, `system-design-expert`.
5. **Tests.** "Add contract tests between the monolith and the new service, and end-to-end tests for the critical paths." Uses `integration-testing-expert`, `e2e-testing-expert`.

## 3. Smart contract audit

Goal: review an ERC-20 token with a vesting contract before deployment.

1. **Read the code.** "Review this contract for reentrancy, access control, unchecked external calls and unsafe upgrade patterns." Uses `solidity-expert` and `smart-contract-security-expert`.
2. **Test.** "Write Foundry fuzz and invariant tests, for example total supply never exceeds the cap, and a Hardhat suite for every external function." Uses `foundry-expert`, `hardhat-expert`.
3. **Report.** "Produce an audit report with severity, impact, proof of concept and a fix for each finding." Uses `smart-contract-security-expert`.
4. **Gas.** "Reduce gas without weakening safety: storage packing, custom errors, calldata use." Uses `ethereum-expert`, `solidity-expert`.
5. **Deploy.** "Plan an upgradeable deployment with OpenZeppelin Upgrades, a multisig owner, a timelock and verification on a block explorer." Uses `solidity-expert`, `dao-expert`.

## 4. Production incident response

Goal: p99 latency on `/checkout` rose from 200 ms to 2.5 s after a release.

1. **Gather facts.** "On the Ubuntu host, show load, memory, disk and network state, and which processes changed since the last deploy." Uses `linux-expert`, `kubernetes-expert`.
2. **Diagnose.** "Here are logs and metrics from the last two hours. Find the most likely root cause and what to check next." Uses `scalability-expert`, `code-review-expert`.
3. **Database.** "This query went from 50 ms to 5 s. Read the plan, find the cause and suggest a fix that does not lock the table." Uses `postgresql-expert`.
4. **Fix and roll out.** "Deploy the fix with a rolling or blue-green release and check health before shifting traffic." Uses `cicd-expert`, `kubernetes-expert`.
5. **Post-mortem.** "Draft a blameless post-mortem with a timeline, root cause, detection gaps and action items." Uses `code-review-expert`.

## 5. Document question answering agent

Goal: an agent that answers questions about internal documents with citations.

1. **Architecture.** "Design an agent that retrieves chunks, judges whether they suffice, calls a search tool if not, and answers with citations." Uses `ai-agent-architect`.
2. **Retrieval.** "Design the RAG pipeline: chunking, embeddings, hybrid search, reranking, and an evaluation set." Uses `rag-expert`.
3. **Vector store.** "Design a pgvector schema for 10 million chunks, including the index type and how filtering interacts with it." Uses `rag-expert`, `postgresql-expert`.
4. **Orchestration.** "Implement the agent as a LangGraph graph with a retrieval node, a grading node and a conditional edge to search." Uses `langchain-expert`.
5. **Memory.** "Keep per-user preferences and conversation summaries across sessions, and say what should be forgotten." Uses `ai-agent-architect`.
6. **Tools.** "Expose the document store as an MCP server so other clients can use it." Uses `mcp-expert`.
7. **Evaluation.** "Build an evaluation pipeline for answer quality and citation accuracy, with a regression set." Uses `prompt-engineering-expert`.

## 6. General principles

1. Work in phases: design, implement, test, ship, operate.
2. Give each request one clear job and state the constraints that matter.
3. Paste the previous result when the next step depends on it.
4. Review each phase before moving on, and run the commands the skill suggests.
5. Ask for the review checklist of the relevant skill at each gate.
