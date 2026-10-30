# Usage Guide

How to get good results from the 67 skills in this pack. Installation is covered in [INSTALL.md](../INSTALL.md); the list of skills is in the [skill index](./skill-index.md).

## Contents

1. [How skills load](#how-skills-load)
2. [Calling a skill directly](#calling-a-skill-directly)
3. [Combining skills](#combining-skills)
4. [Writing good requests](#writing-good-requests)
5. [Request patterns](#request-patterns)
6. [Troubleshooting](#troubleshooting)

## How skills load

- Claude Code reads each installed skill's `name` and `description` at the start of a session.
- When your request matches a description, Claude loads that skill's `SKILL.md`. You do not need to name the skill.
- The skill may point to files under its `references/` folder; Claude reads them only when the task needs that detail.
- Several skills can apply to one request. Descriptions end with "Not for ... (use ...)" so that neighboring skills hand work to each other instead of competing.

Example request:

```text
Build a Next.js 15 page that streams user data with Suspense.
```

This usually loads `nextjs-15-architect` and may add `senior-react-19-engineer`.

## Calling a skill directly

Type `/` followed by the skill name, then your request:

```text
/postgresql-expert why is this query slow? EXPLAIN output is below.
```

Use this when you want a particular skill to apply or when automatic matching picked a different one. Type `/` alone to browse what is installed, or open the `/skills` menu. Calling a skill loads it for that request; you can call more than one in a session.

## Combining skills

A request that spans areas can load several skills. Name the areas in the request and Claude will pick up the matching skills.

| Task | Skills that typically apply |
|---|---|
| New feature across the stack | `senior-react-19-engineer`, `nextjs-15-architect`, `nestjs-expert`, `postgresql-expert`, `unit-testing-expert`, `playwright-expert` |
| Latency regression in production | `scalability-expert`, `postgresql-expert`, `redis-expert`, `kubernetes-expert`, `nginx-expert` |
| Smart contract audit | `solidity-expert`, `smart-contract-security-expert`, `foundry-expert` or `hardhat-expert` |
| Document question answering agent | `ai-agent-architect`, `langchain-expert`, `rag-expert`, `prompt-engineering-expert` |
| Containerize and ship a service | `docker-expert`, `cicd-expert`, `kubernetes-expert`, `terraform-expert` |
| Login and permissions | `authentication-expert`, `authorization-expert`, `secure-coding-expert` |

Example for the feature row:

```text
Add a "team invitations" feature: a React 19 form that posts to a NestJS
endpoint, stores the invitation in PostgreSQL and sends an email. Include
unit tests for the service and a Playwright test for the form.
```

For larger jobs, work in phases (design, implement, test, deploy) and carry the previous result into the next request. The [example scenarios](../examples/example-usage.md) show this.

## Writing good requests

State the facts that change the answer:

- **Scale:** requests per second, data volume, user count.
- **Targets:** p95 latency, availability, Core Web Vitals thresholds.
- **Constraints:** versions in use, cloud provider, compliance needs, team size, deadline.
- **Existing code:** paste the relevant file, error message or configuration.

Compare:

- Vague: "Build a checkout API."
- Specific: "Build a NestJS checkout API for about 1,000 requests per second. Persist to PostgreSQL, use idempotency keys so retries are safe, and include unit and integration tests."

You can also ask for the reasoning: "What are the trade-offs between a transactional outbox and two-phase commit here?" or "Check this change against the review checklist in `nestjs-expert`."

## Request patterns

```text
Design a rate limiter for our API with redis-expert. Compare token bucket
and sliding window, and say what happens when Redis is unavailable.
```

```text
Review this Dockerfile with docker-expert and list each problem with a fix.
```

```text
Refactor this Express route with clean-architecture-expert: move business
logic into a use case and data access into a repository.
```

```text
Compare PostgreSQL and MongoDB for a product catalog with 10 million SKUs
and five filter facets, using postgresql-expert and mongodb-expert.
```

```text
Write unit tests with unit-testing-expert and an end-to-end test with
playwright-expert for the registration flow.
```

## Troubleshooting

**A skill does not load.**

1. Check the file exists: `ls ~/.claude/skills/<skill-name>/SKILL.md` (or `.claude/skills/` in the project).
2. Check its frontmatter parses: run `python3 scripts/validate_skills.py` in the pack repository.
3. Compare your wording with the skill's `description`; mention the tool, file name or symptom it lists.
4. Start a new Claude Code session so the skill list is re-read.
5. Call it with `/<skill-name>` to confirm the skill itself works.

**The wrong skill loads.** Call the one you want with `/<skill-name>`, name the technology in your request, and check the "Not for" clause of both descriptions. If a description is too broad, open an issue or a pull request.

**Too many skills load.** Make the request narrower, or install only the skills you use. Fewer installed skills also shortens the list Claude has to match against.

**A skill's advice does not fit your project.** Say which convention or version you use. Check the skill's `Verified against` line for the versions it assumed.

**Two skills disagree.** Ask Claude to explain the difference, and follow your project's conventions. If one skill is wrong, report it as described in [CONTRIBUTING.md](../CONTRIBUTING.md#reporting-issues).

## See also

- [skill-index.md](./skill-index.md): all skills by category
- [skill-structure.md](./skill-structure.md): how a skill is built
- [example-usage.md](../examples/example-usage.md): end-to-end scenarios
- [INSTALL.md](../INSTALL.md): install, upgrade, uninstall
