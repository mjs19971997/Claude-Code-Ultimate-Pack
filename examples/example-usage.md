# Example Usage

Real-world scenarios demonstrating how to use the Claude Code Ultimate Pack v2.0 in professional engineering workflows.

> **Auto-activation note**: In v2.0, skills auto-activate based on the `description` field in YAML frontmatter — you typically do NOT need to invoke them explicitly. The `/skill <name>` invocations shown below are for cases where you want to force-activate a specific skill. In practice, just describe your task naturally and Claude Code will activate the right skills.

---

## Table of Contents

1. [Scenario 1: Greenfield E-Commerce Backend](#scenario-1-greenfield-e-commerce-backend)
2. [Scenario 2: Legacy Monolith Modernization](#scenario-2-legacy-monolith-modernization)
3. [Scenario 3: Smart Contract Audit](#scenario-3-smart-contract-audit)
4. [Scenario 4: Production Incident Response](#scenario-4-production-incident-response)
5. [Scenario 5: AI Agent System Build](#scenario-5-ai-agent-system-build)

---

## Scenario 1: Greenfield E-Commerce Backend

**Goal**: Build a new e-commerce backend from scratch using NestJS, PostgreSQL, and Docker, deployed to AWS via GitHub Actions.

### Step 1: Architecture Design

**Prompt**:
```
/skill system-design-expert Design the architecture for an e-commerce backend. Requirements:
- 100,000 daily active users
- 1,000,000 products
- 10,000 orders per day
- Payment via Stripe
- Search via ElasticSearch
- Caching via Redis
- Deploy to AWS ECS Fargate
- Multi-AZ, multi-region disaster recovery
```

**Expected output**: A complete architecture document with component diagram, data flow, capacity estimates, and trade-off analysis.

### Step 2: Database Schema Design

**Prompt**:
```
/skill postgresql-expert Design the database schema based on the architecture. Include:
- Users, addresses, carts, orders, order_items, products, categories, reviews
- Multi-currency support
- Soft deletes with audit columns
- Indexes for the primary query patterns
- Partitioning strategy for orders table
```

**Expected output**: SQL schema with indexes, partitioning DDL, and a paragraph explaining each design decision.

### Step 3: NestJS Module Implementation

**Prompt**:
```
/skill nestjs-expert Implement the OrdersModule based on the schema. Use:
- Clean Architecture with use cases, repositories, and controllers
- Prisma ORM
- Zod validation
- Custom decorators for roles
- Unit tests with Vitest
```

**Expected output**: A complete NestJS module with controllers, services, repositories, DTOs, and tests.

### Step 4: Authentication and Authorization

**Prompt**:
```
/skill authentication-expert Implement JWT-based authentication with refresh token rotation.
/skill authorization-expert Add RBAC with roles: customer, support, admin, super_admin.
```

**Expected output**: Auth module with login, refresh, logout, and a role-based guard.

### Step 5: Testing

**Prompt**:
```
/skill integration-testing-expert Write integration tests for the order placement flow.
/skill e2e-testing-expert Write E2E tests for the checkout flow.
```

**Expected output**: Test suites with setup, teardown, and assertions.

### Step 6: Containerization and CI/CD

**Prompt**:
```
/skill docker-expert Create a production Dockerfile for the NestJS service.
/skill github-actions-expert Create a CI/CD pipeline that builds, tests, scans, and deploys to AWS ECS.
```

**Expected output**: Multi-stage Dockerfile and a GitHub Actions workflow.

### Step 7: Security Review

**Prompt**:
```
/skill owasp-top-10-expert Review the entire codebase for OWASP Top 10 vulnerabilities.
/skill api-security-expert Review the API for rate limiting, input validation, and authn/authz gaps.
```

**Expected output**: Security report with findings, severity, and remediation steps.

### Step 8: Performance Optimization

**Prompt**:
```
/skill performance-optimization-expert Profile the order placement flow and optimize bottlenecks.
/skill redis-expert Design a caching layer for product catalog and user sessions.
```

**Expected output**: Performance report with before/after metrics and cache strategy.

---

## Scenario 2: Legacy Monolith Modernization

**Goal**: Modernize a 10-year-old PHP monolith into a NestJS microservices architecture with zero downtime.

### Step 1: Audit

**Prompt**:
```
/skill code-review-expert Audit the existing PHP monolith. Identify:
- Modules that map cleanly to microservices
- Shared database tables that need to be split
- Synchronous calls that need to become async
- Technical debt that blocks modernization
```

### Step 2: Refactoring Plan

**Prompt**:
```
/skill refactoring-expert Create an incremental refactoring plan. Constraints:
- Zero downtime
- 2-week sprint cycles
- 5-engineer team
- Must ship customer value every sprint
```

### Step 3: Strangler Fig Pattern

**Prompt**:
```
/skill microservices-expert Implement the Strangler Fig pattern. Start with the Products module.
Extract it into a NestJS microservice behind an API gateway that routes /products to the new service
and everything else to the legacy monolith.
```

### Step 4: Database Decoupling

**Prompt**:
```
/skill clean-architecture-expert Design the boundary between the new Products service and the legacy database.
Use the Outbox pattern for eventual consistency.
```

### Step 5: Testing

**Prompt**:
```
/skill integration-testing-expert Write contract tests between the API gateway and both backends.
```

---

## Scenario 3: Smart Contract Audit

**Goal**: Audit an ERC-20 token contract before mainnet deployment with $50M TVL.

### Step 1: Static Analysis

**Prompt**:
```
/skill solidity-expert Review this ERC-20 contract for:
- Reentrancy
- Integer overflow/underflow
- Access control
- Front-running
- Logic errors
```

### Step 2: Tool-Based Audit

**Prompt**:
```
/skill foundry-expert Write fuzz tests and invariant tests for this contract.
/skill hardhat-expert Create a test suite that exercises every external function with edge case inputs.
```

### Step 3: Security Review

**Prompt**:
```
/skill smart-contract-security-expert Perform a full security audit. Produce a report with severity levels
(critical, high, medium, low, informational) and remediation steps for each finding.
```

### Step 4: Gas Optimization

**Prompt**:
```
/skill ethereum-expert Optimize gas usage without sacrificing security. Identify storage slots that can be packed,
unnecessary SLOADs, and loops that can be replaced with mappings.
```

### Step 5: Deployment

**Prompt**:
```
/skill openzeppelin-expert Set up an upgradeable proxy pattern using OpenZeppelin Defender.
```

---

## Scenario 4: Production Incident Response

**Goal**: A production API is returning 500 errors at 10x the normal rate. Investigate, fix, and deploy within 4 hours.

### Step 1: Investigation

**Prompt**:
```
/skill linux-expert The production server is an Ubuntu 22.04 EC2 instance. SSH in and gather:
- Top processes by CPU and memory
- Recent log entries from the application
- Disk space and inode usage
- Network connections
- Database connection count
```

### Step 2: Diagnosis

**Prompt**:
```
/skill performance-optimization-expert Based on these logs and metrics, diagnose the root cause.
The error rate spiked at 14:30 UTC. The database CPU is at 95%. The application is throwing connection pool errors.
```

### Step 3: Fix

**Prompt**:
```
/skill postgresql-expert This query is taking 5 seconds. It was 50ms yesterday. Investigate and fix:
<query and EXPLAIN ANALYZE output>
```

### Step 4: Deployment

**Prompt**:
```
/skill cicd-expert Deploy the fix using a blue-green deployment. Verify health checks before cutting over.
```

### Step 5: Post-Mortem

**Prompt**:
```
/skill code-review-expert Help me write a blameless post-mortem. What early warning signals did we miss?
What alerts should we add to catch this earlier next time?
```

---

## Scenario 5: AI Agent System Build

**Goal**: Build a multi-agent research assistant that can answer questions about a company's internal documents.

### Step 1: Architecture

**Prompt**:
```
/skill ai-agent-architect Design a multi-agent system with:
- A planner agent that decomposes questions into sub-tasks
- A retriever agent that searches the document store
- A synthesizer agent that combines results into an answer
- A critic agent that verifies the answer against sources
```

### Step 2: Retrieval

**Prompt**:
```
/skill rag-expert Design the RAG pipeline. Use:
- Chunking strategy: semantic chunking with 512 token windows
- Embedding model: text-embedding-3-large
- Vector database: pgvector
- Reranking: cross-encoder
- Hybrid search: keyword + vector
```

### Step 3: Vector Store

**Prompt**:
```
/skill vector-database-expert Design the pgvector schema. We have 10M chunks. What indexing strategy?
What HNSW parameters? What's the expected query latency?
```

### Step 4: Orchestration

**Prompt**:
```
/skill langgraph-expert Implement the agent graph. Use LangGraph with:
- Conditional edges for the planner
- Human-in-the-loop for low-confidence answers
- State persistence for long-running research
```

### Step 5: Memory

**Prompt**:
```
/skill memory-systems-expert Design the agent memory system. The assistant must remember:
- User preferences across sessions
- Previously answered questions
- Source documents the user has marked as trusted
```

### Step 6: Tooling

**Prompt**:
```
/skill mcp-expert Expose the document store as an MCP server so the agents can use it as a tool.
```

### Step 7: Evaluation

**Prompt**:
```
/skill prompt-engineering-expert Design an evaluation pipeline. Use:
- RAGAS for retrieval quality
- LLM-as-judge for answer quality
- Human eval for the top 100 questions
```

---

## Composing Skills: General Principles

1. **Start with architecture, end with operations** — design first, implement second, deploy third, monitor fourth.
2. **One skill per prompt** — each skill works best when it can focus on its specialty.
3. **Carry context forward** — reference previous outputs explicitly so the next skill can build on them.
4. **Review between phases** — never let a phase's output flow into the next without review.
5. **Use checklists at every gate** — code review, refactoring, deployment, production. Every skill has them; use them.

---

The Claude Code Ultimate Pack is not a magic wand — it is a team of senior engineers. Treat it as such. Direct each skill precisely, review each output critically, and iterate. That is how senior engineers use tools to produce senior-engineer-quality work.
