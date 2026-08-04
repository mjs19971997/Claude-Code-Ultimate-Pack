# Usage Guide

This guide explains how to use the Claude Code Ultimate Pack effectively, including how skills activate, how to invoke them explicitly, how to compose them in workflows, and how to get the best output.

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

When you send a prompt to Claude Code, it analyzes the prompt and activates the most relevant skill based on:

1. **Keywords** — technologies, frameworks, and concepts mentioned in the prompt
2. **Intent** — what you are asking for (design, implement, review, debug, deploy)
3. **Context** — the surrounding project files, if any

For example, if you type "build a Next.js 15 page that fetches data with server components", Claude Code activates `nextjs-15-architect` because the prompt mentions Next.js 15, server components, and data fetching.

Skills activate automatically; you do not need to do anything special. However, if Claude Code does not activate the skill you expect, you can invoke it explicitly.

---

## Explicit Invocation

To guarantee a specific skill activates, prefix your prompt with `@<skill-name>` (without the `.md` extension):

```
@senior-react-19-engineer Build a useDebounce hook with TypeScript
@nestjs-expert Design a module structure for an e-commerce checkout
@kubernetes-expert Convert this docker-compose into Helm charts
@solidity-expert Audit this ERC-20 contract for reentrancy
@postgresql-expert Design a schema for a multi-tenant SaaS application
@playwright-expert Write an E2E test for the user signup flow
```

The skill name is the file name without the `.md` extension. For example, `senior-react-19-engineer.md` becomes `@senior-react-19-engineer`.

---

## Composing Skills in Workflows

Real engineering work spans multiple domains. Compose skills by invoking them in sequence within a single conversation. Claude Code maintains context across invocations.

### Pattern 1: Design then implement

```
@system-design-expert Design the architecture for a real-time chat application
```
*(Review the design, then:)*
```
@nestjs-expert Implement the WebSocket gateway based on this design
```
*(Review the implementation, then:)*
```
@postgresql-expert Design the schema for messages and conversations
```

### Pattern 2: Implement then secure

```
@rest-api-expert Implement the user registration endpoint
```
```
@owasp-top-10-expert Review this endpoint for security vulnerabilities
```
```
@api-security-expert Add rate limiting and input validation
```

### Pattern 3: Implement then test then deploy

```
@expressjs-expert Implement the order processing service
```
```
@jest-expert Write unit tests for the order processing logic
```
```
@playwright-expert Write E2E tests for the checkout flow
```
```
@docker-expert Create a production Dockerfile for this service
```
```
@github-actions-expert Create a CI/CD pipeline to build, test, and deploy
```

### Pattern 4: Audit then refactor

```
@code-review-expert Review this codebase for issues
```
```
@refactoring-expert Refactor the authentication module based on the review
```
```
@performance-optimization-expert Optimize the database queries identified in the review
```

---

## Getting the Best Output

### 1. Be specific

Vague prompts produce vague output. Specify:
- The exact technology and version
- The exact problem
- The constraints (performance, security, scale)
- The expected output format

**Bad**: "Build a React component"

**Good**: "Build a React 19 server component using TypeScript that fetches user data from `/api/users/[id]` with Suspense streaming, handles loading and error states, and is accessible per WCAG 2.2 AA"

### 2. Provide context

If you have existing code, architecture, or constraints, share them. Claude Code cannot read your mind.

**Bad**: "Design the database schema"

**Good**: "Design the database schema for a multi-tenant SaaS application using PostgreSQL 16. Each tenant must have isolated data. We expect 10,000 tenants, 1,000,000 users total, and 100,000,000 records total. The primary query pattern is filtering records by tenant_id and created_at."

### 3. Ask for one thing at a time

Complex requests produce shallow output. Break them down.

**Bad**: "Build the entire authentication system with JWT, OAuth2, refresh tokens, rate limiting, and audit logging"

**Good**:
1. "Design the authentication architecture"
2. "Implement the JWT issuance endpoint"
3. "Implement the refresh token rotation logic"
4. "Add rate limiting to the login endpoint"
5. "Add audit logging for all authentication events"

### 4. Review and iterate

Treat Claude Code's first response as a draft. Review it, identify weaknesses, and ask for improvements:

- "This design does not handle the case where the database is unavailable. Add a fallback."
- "The error handling is too generic. Specify exact error codes and messages."
- "The test coverage is incomplete. Add tests for the edge cases."

### 5. Use the checklists

Every skill includes four checklists (Code Review, Refactoring, Deployment, Production). Use them:

```
@nestjs-expert Review this module against your Code Review Checklist and report any failures
```

```
@docker-expert Verify this Dockerfile against your Production Checklist before we deploy
```

---

## Common Patterns

### Pattern: Greenfield project

1. `@system-design-expert` — design the overall architecture
2. `@software-architect` — define the module structure and boundaries
3. Domain-specific skills — implement each module
4. `@testing-expert` (various) — write tests
5. `@cicd-expert` — set up the pipeline
6. `@docker-expert` and `@kubernetes-expert` — containerize and orchestrate
7. `@owasp-top-10-expert` — security review
8. `@performance-optimization-expert` — performance review

### Pattern: Legacy modernization

1. `@code-review-expert` — audit the existing codebase
2. `@refactoring-expert` — plan the refactoring in incremental steps
3. `@testing-expert` (various) — add characterization tests before refactoring
4. Domain-specific skills — implement the modernized version
5. `@security-expert` (various) — security review of the modernized version

### Pattern: Incident response

1. `@linux-expert` — investigate on the server
2. `@performance-optimization-expert` — identify the bottleneck
3. Domain-specific skill — implement the fix
4. `@testing-expert` — verify the fix
5. `@cicd-expert` — deploy the fix
6. `@code-review-expert` — post-mortem review

### Pattern: Security audit

1. `@owasp-top-10-expert` — top-level audit
2. `@api-security-expert` — API-specific audit
3. `@jwt-expert` or `@oauth2-expert` — authentication-specific audit
4. `@secure-coding-expert` — code-level audit
5. Domain-specific skills — implement the fixes

---

## Troubleshooting

### The wrong skill activated

If Claude Code activates the wrong skill, explicitly invoke the correct one:

```
@nestjs-expert <your prompt>
```

### The output is too generic

Your prompt is too vague. Add specificity: exact technology, exact version, exact constraints, exact expected output.

### The output does not follow the skill's standards

Remind Claude Code of the skill:

```
@nestjs-expert Re-implement this following your Coding Standards and Architecture Rules exactly
```

### The skill is not installed

If `@<skill-name>` produces an error, the skill is not installed. See `INSTALL.md` for installation instructions. Verify with:

```bash
ls ~/.claude/skills/<domain>/<skill-name>.md
```

### Skills conflict

If two skills give contradictory guidance, prioritize by domain relevance. For example, if `@expressjs-expert` and `@clean-architecture-expert` disagree on file organization, `@clean-architecture-expert` wins on architecture decisions, `@expressjs-expert` wins on Express-specific implementation details.

---

The Claude Code Ultimate Pack is most powerful when you treat it as a team of specialists. Each skill is a world-class engineer in their domain. Compose them, direct them, review their work, and iterate. That is how senior engineers use tools — not as oracles, but as collaborators.
