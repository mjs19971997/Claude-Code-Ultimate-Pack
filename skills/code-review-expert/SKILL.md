---
name: code-review-expert
description: >-
  Reviews code changes (pull requests, patches, large or AI-generated diffs) for design, correctness, tests, security and readability, and writes actionable comments with severity labels in the Conventional Comments style. Covers author preparation and PR size, review order, per-area checklists (security, concurrency, error handling, performance), reviewing tests, automated gates (linters, CodeQL, Semgrep, secret scanning), and team norms such as turnaround time. Use when reviewing or preparing a pull request, writing review guidelines, auditing a diff before merge, or deciding what to automate. Not for restructuring existing code (use refactoring-expert) or full secure-coding rules and vulnerability audits (use secure-coding-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Code Review Expert

This skill covers how to review a change well and how to make it easy to review: what the author prepares, what the reviewer looks at and in which order, how to word comments so they are acted on, what to automate so humans spend time on design and logic, and how to handle large and AI-generated diffs. The goal is the one stated in Google's Engineering Practices: the codebase's health improves with every merged change, without blocking progress.

> Verified against Google Engineering Practices (Code Review), Conventional Comments, CodeQL CLI 2.27.x with github/codeql-action v4, Semgrep 1.183.0, Gitleaks 8.30.x (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: preparing a change for review, reviewing it, writing and receiving comments, review checklists, reviewing tests, automated review gates, reviewing AI-generated and very large diffs, and team conventions for turnaround and disagreement.
- Not covered: refactoring technique (refactoring-expert), the full secure-coding rule set and penetration-style audits (secure-coding-expert, api-security-expert), CI pipeline design (cicd-expert), git branching and history hygiene (git-expert).
- Reviews are for humans to judge what tools cannot: whether the design fits, whether the logic is right, whether the change is understandable and testable.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Standard | Approve a change once it improves overall code health, even if it is not perfect; do not approve changes that worsen it. Perfect is not the bar |
| Order of attention | Intent and description, then design, correctness and edge cases, tests, security, readability and naming, then style (mostly automated) |
| Speed | Google's guidance: one business day is the maximum time to respond to a review request; quick individual responses matter more than total completion time |
| Size | Small, self-contained changes are reviewed faster and more thoroughly and are easier to roll back; split large work into reviewable steps |
| Comment format | Conventional Comments: `label [decorations]: subject`, followed by optional discussion. Labels include praise, nitpick, suggestion, issue, todo, question, thought, chore, note; decorations include `(blocking)`, `(non-blocking)`, `(if-minor)` |
| Automated gates | Formatter and linter, type checker, tests, SAST (CodeQL, Semgrep), secret scanning (Gitleaks, GitHub secret scanning), dependency audit; they block merges on defined severities |
| AI-assisted changes | Same standard, more scrutiny on invented APIs and packages, plausible but wrong logic, tests that mirror the implementation, and overreach beyond the request |
| Ownership | CODEOWNERS route reviews to the right people; the author owns the change until merged and in production |

## 3. Workflow

Author:
1. Self-review the full diff in the review tool before requesting review; remove debug code and unrelated edits.
2. Keep the change to one purpose. Separate refactors and formatting from behavior changes (different commits or PRs).
3. Write the description: what and why, how it was tested, risk and rollback, links to the issue or design, and screenshots for UI.
4. Run the automated gates locally or wait for green CI before pinging reviewers.
5. Respond to every comment: fix, or explain; mark resolved only after the change is pushed.

Reviewer:
1. Read the description and linked issue first; decide whether the change should exist and whether the approach is right before reading lines.
2. Skim the whole diff for shape (files touched, size, surprises), then review in order: design, correctness, tests, security, readability.
3. Review every line you are asked to approve; read surrounding code for context; for generated files, review the generator input.
4. Write comments with labels (section 7); separate must-fix from preferences.
5. Finish with a clear verdict: approve, approve with non-blocking comments, or request changes with the blocking items listed.
6. Re-review quickly after updates; check only what changed and the blocking items.

## 4. Decision Rules

- Approve when the change improves code health and has no blocking issues. Leave non-blocking suggestions as such so the author can merge.
- Request changes for defects, security problems, missing tests for new behavior, broken contracts, and designs that will be costly to undo.
- Technical facts and data outrank opinion; for style not covered by the guide, defer to the author or the existing code; for design disputes, discuss synchronously after two rounds and escalate to an owner or tech lead if needed.
- Ask for a split when the change mixes concerns or exceeds what you can review with attention. A rough ceiling is a few hundred changed lines of hand-written code; generated code, moves and mechanical renames are exceptions.
- Do not ask for unrelated cleanup in the same PR; record it as a follow-up.
- Prefer a question over an assertion when you may be missing context.
- Block on process only where the team agreed to (tests, review of migrations, security review for auth changes).
- Urgent fixes may be reviewed after merge under a stated emergency rule, with a follow-up review within the day.

## 5. Coding Standards

For the review itself:

- One comment, one point, one location. Say what is wrong, why it matters, and a way forward.
- Label severity every time; unlabeled comments are read as blocking by anxious authors and ignored by others.
- Comment on the code, not the person: "this function reads the file twice" instead of "you read the file twice".
- Include evidence: a failing input, a reference to the rule or doc, a link to the similar code elsewhere.
- Offer a snippet when the fix is small; ask a question when it is design.
- Praise specific good decisions; it keeps the signal honest and teaches.
- Keep style discussion out of review by encoding it in the formatter and linter.

## 6. Project Structure

Review support files in the repository:

```
.
├── .github/
│   ├── CODEOWNERS                    # routes reviews by path
│   ├── pull_request_template.md      # description prompts: what, why, tests, risk, rollback
│   └── workflows/
│       ├── ci.yml                    # format, lint, typecheck, tests
│       ├── codeql.yml                # SAST (or default setup in repo settings)
│       └── semgrep.yml               # custom rules and registry rules
├── .gitleaks.toml                    # secret-scanning allowlist for known fixtures
├── .semgrep/                         # team rules, each with a test file
└── docs/review-guidelines.md         # labels, turnaround, size limits, escalation
```

## 7. Design Patterns

Conventional Comments labels and when to use them:

| Label | Use for | Blocking by default |
|---|---|---|
| `praise:` | Something done well | No |
| `nitpick:` | Trivial preference | No |
| `suggestion:` | A concrete improvement; say why | Depends: add a decoration |
| `issue:` | A defect or problem; pair with a suggestion | Yes unless marked otherwise |
| `todo:` | A small necessary change | Yes |
| `question:` | A request for clarification | Depends |
| `thought:` | An idea that may not apply to this PR | No |
| `chore:` | A process step to complete (changelog, ticket link) | Yes |
| `note:` | Something the reader should know | No |

Decorations go in parentheses after the label: `issue (blocking):`, `suggestion (non-blocking):`, `nitpick (if-minor):`. Check the current Conventional Comments page for the full list before adopting it as a team rule.

Other patterns:

- **Review in layers**: first pass for design questions and a "shape" comment, second pass for line-level issues, so authors do not polish code that will be rewritten.
- **Checklists by change type**: API change, database migration, concurrency, auth, UI. See [references/checklists.md](references/checklists.md).
- **Two-key rule** for risky areas (auth, payments, migrations): two approvals, one from a domain owner.
- **Review rota** with a visible queue so response time is shared and measurable.
- **Pairing or walkthrough** call for large or contentious changes, followed by a written summary on the PR.
- Comment wording guide with before and after examples: [references/comment-guide.md](references/comment-guide.md).

## 8. Best Practices

- Review early and in small pieces; stack or sequence changes so each is reviewable alone.
- Read tests first when the code is unclear; the tests state the intended behavior.
- Verify the claim in the description: run the branch when behavior or UI changes are subtle.
- Check what is missing: error paths, tests for edge cases, docs, migration, feature flag, metrics, rollback.
- Check how the change behaves in production: timeouts, retries, large inputs, concurrent calls, partial failure, and old clients.
- Leave the code better: if the surrounding code has a smell, mention it as a follow-up, not a blocker.
- Authors: explain non-obvious choices in the PR description or in a code comment; if the reviewer was confused, the next reader will be too.
- Track review metrics (time to first response, time to merge, PR size) to find bottlenecks, not to rank people.

## 9. Performance

Review for performance proportionate to the path's importance:

- Accidental N+1 queries, queries in loops, missing indexes for new filters, unbounded result sets, missing pagination.
- Work in hot paths: repeated parsing or serialization, regex compilation in a loop, synchronous I/O on an event loop, large allocations.
- Algorithmic complexity on inputs that can grow: nested loops over collections, `includes` in loops where a set fits.
- Unbounded caches, queues or buffers; missing timeouts; retries without backoff and jitter.
- Evidence beats guesses: ask for a benchmark or profile when the claim is performance, and do not accept micro-optimizations that hurt clarity without it.
- Review speed itself: slow CI and slow reviews both cost; keep gates fast enough to run on every push.

## 10. Security

Look at every change for these, and apply extra scrutiny to auth, input handling and data access (details in [references/checklists.md](references/checklists.md)):

- Untrusted input reaching interpreters: SQL, shell, template, regex, deserializers, URL fetchers (SSRF), file paths (path traversal).
- Authorization on every new endpoint and object access: checked on the server, per object and per tenant, on writes as well as reads.
- Secrets: none in code, config samples, logs, test fixtures or CI output; use a secrets manager or CI secrets.
- Output encoding for HTML, headers and logs; no sensitive data in error messages.
- Cryptography: use library defaults and vetted algorithms; no home-grown schemes; compare secrets in constant time.
- New dependencies: necessity, maintenance, license, and that the package name is the real one (typosquats and invented package names are a risk, especially in AI-suggested code).
- CI workflow changes: no untrusted event data interpolated into shell steps (pass through `env:` instead), least-privilege `permissions:`, pinned action versions.

## 11. Testing

Reviewing tests is part of reviewing the change:

- Does a test fail without the change? For a bug fix, there should be a regression test that fails before and passes after.
- Do tests assert behavior and outcomes rather than implementation details and call counts?
- Are edge cases covered: empty, null, boundary, large, duplicate, concurrent, error from a dependency?
- Are tests deterministic: fixed clocks and seeds, no sleeps, no dependence on order or network?
- Is the test readable: arrange, act, assert; names that state the rule; minimal fixtures?
- Snapshot tests: is the snapshot reviewed and small enough to be meaningful?
- Coverage numbers are a hint, not a verdict; look for untested branches that matter (error handling, authorization denials).
- Mocks: are they replacing the thing under test or hiding integration problems? Prefer fakes or real dependencies at the boundary that matters.

## 12. Review Checklist

- [ ] Description explains what, why, testing, risk and rollback; scope matches the title.
- [ ] Change is small and single-purpose, or the split plan is stated.
- [ ] Design fits the existing architecture; no new pattern without reason.
- [ ] Logic is correct for edge cases, error paths and concurrency.
- [ ] New behavior has tests; bug fixes have regression tests.
- [ ] Inputs are validated; authorization and tenant checks are present on reads and writes.
- [ ] No secrets, no debug leftovers, no commented-out code.
- [ ] Public interfaces and migrations are backward compatible, or the break is planned.
- [ ] Logs, metrics and errors are useful and free of sensitive data.
- [ ] Names, comments and docs make the intent clear.
- [ ] Automated gates are green; no suppressed warnings without a reason.
- [ ] Verdict is explicit and blocking items are listed.

## 13. Production Notes

- Set team targets and review them: first response within one business day, and a shared definition of "ready for review".
- Use branch protection: required approvals, required status checks, CODEOWNERS review for sensitive paths, dismiss stale approvals on new pushes for risky areas, and no force pushes to protected branches.
- Run SAST on pull requests and on the default branch; triage findings with owners and track false positives as suppressed rules with comments.
- Keep tool rules versioned and tested (Semgrep rule tests, CodeQL query packs), and update pinned tool and action versions on a schedule.
- Feature flags and staged rollouts reduce review pressure: a reviewed change can still ship dark.
- After incidents, add the missed check to the checklist or automate it; a review miss is a process finding.
- AI-generated changes: treat the author as accountable for the diff. Ask for the spec or prompt used, require the author to explain the change, and run the code. See [references/checklists.md](references/checklists.md) section 8.

## 14. Examples

Rewriting a vague comment into an actionable one:

```text
Before: "This is wrong, fix it."

After:  issue (blocking): `refund()` updates the invoice by id only.
        Another tenant's invoice id would be updated. Add the tenant to the WHERE
        clause (and to the tests): `... WHERE id = $2 AND tenant_id = $3`.
        This is the same rule as in `getInvoice()`; reads and writes both need it.
```

A path-handling fix requested in review. The reviewer asks for the resolved path to be verified against the base directory, including symlinks, before a user-supplied name is used:

```ts
import { realpath } from "node:fs/promises";
import { resolve, sep } from "node:path";

export async function resolveUpload(baseDir: string, name: string): Promise<string> {
  if (name.length === 0 || name.includes("\0")) throw new Error("Invalid file name");
  const base = await realpath(baseDir);
  const real = await realpath(resolve(base, name)); // follows symlinks; rejects if missing
  if (real !== base && !real.startsWith(base + sep)) throw new Error("Path escapes upload directory");
  return real;
}
```

Automated review gates for pull requests: CodeQL and Semgrep with least-privilege permissions. Untrusted values are never interpolated into `run:` steps:

```yaml
name: security-scan
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  codeql:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: [javascript-typescript, python]
    steps:
      - uses: actions/checkout@v7
      - uses: github/codeql-action/init@v4
        with:
          languages: ${{ matrix.language }}
          build-mode: none
      - uses: github/codeql-action/analyze@v4
        with:
          category: "/language:${{ matrix.language }}"

  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
      - run: pip install semgrep==1.183.0
      - run: semgrep scan --config p/default --error --metrics=off .
```

Pin third-party actions to a full commit SHA when the policy requires it, and keep the tag in a comment for readability.

Summary comment on a pull request using labels:

```text
Verdict: request changes (2 blocking, 3 non-blocking)

praise: Splitting the parser from the loader made the diff easy to follow.
issue (blocking): retry loop in `fetchRates()` has no backoff and no cap; a provider outage
  will multiply load. Suggest exponential backoff with jitter and a max of 3 attempts.
issue (blocking): no test for the empty-response branch added in `parseRates()`.
suggestion (non-blocking): extract the currency whitelist into a constant shared with `validate()`.
question (non-blocking): is the 30 s timeout agreed with the provider SLA?
nitpick (if-minor): `tmp` -> `parsedRates`.
```

## 15. Common Mistakes

- **Reviewing style by hand**: it burns time and goodwill. Automate formatting and lint rules.
- **"LGTM" after scanning headlines** on a large diff: either split it, or review it properly and say what you did not review.
- **Unlabeled severity**: authors cannot tell must-fix from preference. Use labels.
- **Blocking on taste**: if the code works, is consistent and improves health, approve and leave a non-blocking note.
- **Review that never ends**: raising new issues in each round. Collect everything in the first pass; later rounds check fixes.
- **Reviewing only the diff**: missing callers, other implementations, config, migrations and docs the change should have touched.
- **Tenant or permission checks verified on reads only**, while updates and deletes go unchecked.
- **Trusting tests because they exist**: tests that mock the code under test or assert nothing meaningful.
- **Accepting AI-generated code on plausibility**: invented functions, packages or flags look fine until run. Run it and verify the dependencies exist.
- **Mixed-purpose PRs** (refactor plus feature plus dependency bump) that hide risk. Ask for separate changes.
- **Slow turnaround without notice**: authors batch work and context goes stale. Respond within the agreed time even if only to say when you will review.
- **Public shaming or sarcasm**: review is collaboration; critique code, thank authors, and take sensitive feedback to a call.
- **Security scanners enabled but alerts ignored**: assign owners and a triage time, or the signal decays.

## 16. References

- [references/checklists.md](references/checklists.md): review checklists by area (design, correctness, concurrency, error handling, security, performance, API and database changes, tests, dependencies, CI workflows) and a section on reviewing AI-generated and very large diffs.
- [references/comment-guide.md](references/comment-guide.md): Conventional Comments in detail, tone and wording, before and after examples, receiving feedback, resolving disagreements, review turnaround norms.
- Official docs: https://google.github.io/eng-practices/review/ , https://conventionalcomments.org/ , https://docs.github.com/en/code-security/code-scanning , https://semgrep.dev/docs/ , https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
