# Usage Guide

This guide explains how to use the Claude Code Ultimate Pack v2.0 effectively, including how skills activate, how to invoke them explicitly, how to compose them in workflows, and how to get the best output.

v2.0 skills follow the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills) — they auto-activate based on the `description` field in YAML frontmatter.

---

## Table of Contents

1. [How Skills Activate](#how-skills-activate)
2. [Explicit Invocation](#explicit-invocation)
3. [Composing Skills in Workflows](#composing-skills-in-workflows)
4. [Getting the Best Output](#getting-the-best-output)
5. [Common Patterns](#common-patterns)
6. [Troubleshooting](#troubleshooting)

---

## How Skills Activate

When you send a prompt to Claude Code, the following happens:

1. **Startup scan** — Claude Code reads the YAML frontmatter (`name` + `description`) of every `SKILL.md` in `~/.claude/skills/` and `.claude/skills/`. This happens once per session.
2. **Prompt analysis** — Claude analyzes your prompt to identify technologies, frameworks, intent, and context.
3. **Skill matching** — Claude compares your prompt against every skill's `description` field. Skills whose "Use this skill when..." clause matches your prompt are candidates for activation.
4. **Activation** — Claude activates the best-matching skill(s). The skill's full `SKILL.md` body is loaded into context, and Claude follows its instructions.

### What this means for you

- **No manual `@skill-name` invocation required** — just ask your question naturally.
- **Multiple skills can be active simultaneously** — Claude composes them based on your prompt.
- **The `description` field is critical** — a vague description means the skill won't activate. Every skill in this pack has a carefully crafted two-paragraph description (what + when).

### Example: automatic activation

If you type:

```
Build a Next.js 15 page that fetches user data with Suspense streaming
```

Claude Code reads the descriptions of:
- `senior-react-19-engineer` — "Use this skill when building web frontends with React, Next.js, TypeScript..."
- `nextjs-15-architect` — "Use this skill when building Next.js 15 applications with App Router, RSC, streaming..."
- `performance-expert` — "Use this skill when addressing web performance..."

It activates the most relevant ones (likely `nextjs-15-architect` and `senior-react-19-engineer`) and follows their guidance for Server Components, Suspense streaming, and React 19 patterns.

---

## Explicit Invocation

Sometimes you want to force-activate a specific skill — for example, to override Claude's auto-selection, or to ensure a particular skill's checklist is applied.

### `/skill` command

```
/skill senior-react-19-engineer

Build a useDebounce hook that's safe for SSR
```

This forces `senior-react-19-engineer` to be active for the next response. The skill's full body is loaded into context.

### Skill chaining

You can chain multiple `/skill` invocations:

```
/skill nestjs-expert
/skill postgresql-expert
/skill jest-expert

Design a NestJS module for user registration that stores users in PostgreSQL and includes Jest unit tests
```

All three skills are active, and Claude composes their guidance.

### Claude Code GUI

In the Claude Code GUI, you can also select skills from the Skills panel. The panel shows every skill Claude has discovered (i.e., every `SKILL.md` in `~/.claude/skills/` and `.claude/skills/`).

---

## Composing Skills in Workflows

Skills compose naturally — Claude reads multiple skill bodies and applies all of their constraints simultaneously. Here are common composition patterns:

### Pattern 1: Greenfield full-stack feature

**Goal**: Add a new feature end-to-end.

**Skills activated**: `senior-react-19-engineer` + `nextjs-15-architect` + `nestjs-expert` + `postgresql-expert` + `jest-expert` + `playwright-expert`

**Prompt**:

```
Add a "team invitations" feature: a React 19 form (with the React Compiler)
that posts to a NestJS endpoint, which stores the invitation in PostgreSQL
and sends an email. Include Jest unit tests for the service and Playwright
E2E tests for the form submission.
```

Claude composes the constraints from all five skills:
- React 19 patterns (Server Actions, useActionState, useOptimistic)
- Next.js 15 App Router patterns
- NestJS module structure (controller, service, DTO, module)
- PostgreSQL schema design and Prisma migration
- Jest test structure (describe/it/expect, mocking)
- Playwright test structure (page fixture, assertions)

### Pattern 2: Production incident response

**Goal**: Diagnose and patch a production latency regression.

**Skills activated**: `code-review-expert` + `performance-optimization-expert` + `kubernetes-expert` + `nginx-expert`

**Prompt**:

```
We're seeing p99 latency spike from 200ms to 2.5s on the /checkout endpoint
in production. The cluster is on Kubernetes with an Nginx ingress. Diagnose
the likely causes and propose a fix.
```

Claude composes:
- Code review checklist (recent deploys, schema changes)
- Performance optimization (profiling, bottlenecks)
- Kubernetes (pod CPU/memory, HPA, cluster autoscaler)
- Nginx (upstream timeouts, connection limits, rate limiting)

### Pattern 3: Smart contract audit

**Goal**: Audit an ERC-20 token contract for security issues.

**Skills activated**: `solidity-expert` + `smart-contract-security-expert` + `openzeppelin-expert`

**Prompt**:

```
Audit this ERC-20 contract for reentrancy, access control, and integer
overflow issues. Suggest OpenZeppelin-based mitigations.
```

Claude composes:
- Solidity 0.8+ patterns and gas optimization
- Smart contract security (reentrancy, access control, common vulnerabilities)
- OpenZeppelin (AccessControl, SafeERC20, ReentrancyGuard)

### Pattern 4: AI agent system build

**Goal**: Design a multi-step tool-using agent.

**Skills activated**: `ai-agent-architect` + `langgraph-expert` + `rag-expert` + `prompt-engineering-expert`

**Prompt**:

```
Design a LangGraph-based agent that answers questions about our internal
docs. It should: (1) retrieve relevant chunks from a vector store, (2)
decide whether the retrieved context is sufficient, (3) call a search
tool if not, (4) synthesize an answer with citations.
```

Claude composes:
- AI agent architecture (anatomy, reasoning patterns, production hardening)
- LangGraph (stateful graphs, conditional edges, tool nodes)
- RAG (chunking, embedding, retrieval, reranking)
- Prompt engineering (system prompts, few-shot, chain-of-thought)

---

## Getting the Best Output

### 1. Be specific about constraints

Skills apply their decision-making rules based on constraints you state. Mention:

- **Scale** — "10M users", "1B rows", "$1B TVL"
- **Performance** — "p99 < 100ms", "60fps", "TTFB < 200ms"
- **Security** — "SOC 2 compliant", "audited by OpenZeppelin", "PCI-DSS"
- **Team** — "5 engineers", "mixed seniority", "remote-first"
- **Timeline** — "ship in 2 weeks", "long-term maintainable"

Example:

> ❌ "Build a checkout API."
> ✅ "Build a NestJS checkout API that handles 1000 RPS, persists to PostgreSQL with serializable isolation, and includes idempotency keys for retry safety. Ship in 3 weeks with a 5-engineer team."

The second prompt activates more skills (`nestjs-expert`, `postgresql-expert`, `performance-optimization-expert`, `scalability-expert`) and applies their performance and scalability rules.

### 2. Ask for the production checklist

Every skill has a `## 22. Production Checklist` section. Ask Claude to apply it:

```
Build this feature, then verify it against the production checklist from
the nestjs-expert skill.
```

### 3. Ask for trade-offs

Skills have `## 6. Decision Making Rules` sections that document trade-offs. Ask Claude to surface them:

```
What are the trade-offs between using a transactional outbox and a
two-phase commit for this checkout flow? Apply the decision-making rules
from the microservices-expert and postgresql-expert skills.
```

### 4. Ask for anti-patterns

Every skill has a `## 14. Anti Patterns` section. Ask Claude to check its work:

```
Review your proposed implementation against the anti-patterns section of
the senior-react-19-engineer skill. Did you introduce any?
```

### 5. Iterate

Skills are most powerful when used iteratively. After Claude's first response, ask:

- "Apply the code review checklist from `<skill>` to your response."
- "Refactor this using the refactoring checklist from `<skill>`."
- "What would the production checklist say is missing?"

---

## Common Patterns

### "Design X using skill Y"

```
Design a rate limiter using the redis-expert skill. Include the Redis
data structure, the algorithm (token bucket vs sliding window), and
the fail-closed vs fail-open trade-off.
```

### "Audit X using skill Y"

```
Audit this Dockerfile using the docker-expert skill. Apply the
production checklist and list every failing item with a fix.
```

### "Refactor X using skill Y"

```
Refactor this Express route using the clean-architecture-expert skill.
Move the business logic into a use case, the HTTP concerns into a
controller, and the data access into a repository.
```

### "Compare X and Y using skill Z"

```
Compare PostgreSQL and MongoDB for a product catalog with 10M SKUs and
5 attribute facets per product. Apply the decision-making rules from
the postgresql-expert and mongodb-expert skills.
```

### "Write tests for X using skills Y and Z"

```
Write Jest unit tests and Playwright E2E tests for the user
registration flow. Apply the testing strategy from the jest-expert and
playwright-expert skills.
```

---

## Troubleshooting

### Skill not auto-activating

1. Verify the skill is installed:
   ```bash
   ls ~/.claude/skills/<skill-name>/SKILL.md
   ```
2. Verify the YAML frontmatter parses:
   ```bash
   python3 -c "import yaml; print(yaml.safe_load(open('$HOME/.claude/skills/<skill-name>/SKILL.md').read().split('---')[1]))"
   ```
3. Re-read the skill's `description` field — does your prompt match the "Use this skill when..." clause?
4. Force-activate with `/skill <skill-name>` to verify the skill itself works.
5. Restart Claude Code: `claude restart`.

### Wrong skill activating

If a less-specific skill wins over a more-specific one:

1. Check the descriptions — the less-specific skill may have a broader "when" clause that matches your prompt.
2. Force-activate the more-specific skill with `/skill <skill-name>`.
3. Consider opening a PR to tighten the more-specific skill's `description`.

### Too many skills activating

If too many skills activate and Claude's response is unfocused:

1. Force-activate only the skills you want with `/skill`.
2. Be more specific in your prompt — vague prompts match more skills.
3. Uninstall skills you don't use from `~/.claude/skills/`.

### Skill body not applied

If Claude activates a skill but doesn't follow its rules:

1. Verify the skill body is well-formed — run the validator:
   ```bash
   python3 scripts/validate_skills.py
   ```
2. Check that the skill body has all 30 sections in order.
3. Re-invoke with an explicit instruction: "Apply the production checklist from `<skill>` to your response."

### Conflict between skills

If two skills give conflicting guidance:

1. Skills have `## 6. Decision Making Rules` sections — Claude should resolve conflicts using these.
2. If Claude doesn't, explicitly invoke the higher-priority skill with `/skill`.
3. Open a PR to clarify the conflict in one of the skills' decision-making rules.

---

## See Also

- [`docs/skill-index.md`](./skill-index.md) — complete index of all 93 skills
- [`docs/skill-structure.md`](./skill-structure.md) — the 30-section skill anatomy specification
- [`examples/example-usage.md`](../examples/example-usage.md) — real-world usage scenarios
- [`INSTALL.md`](../INSTALL.md) — installation guide for Windows, Linux, and macOS
