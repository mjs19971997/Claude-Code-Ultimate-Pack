# Review Comment Guide

Guide to writing, receiving and resolving review comments, using the Conventional Comments format, with wording examples and team norms for turnaround. Verified against Google Engineering Practices (Code Review: how to write review comments, handling pushback, speed) and Conventional Comments; the Conventional Comments site was not reachable during verification, so confirm the label and decoration list on conventionalcomments.org before making it a team rule (2026-10).

## 1. Comment format

Conventional Comments structure each comment as:

```text
<label> [decorations]: <subject>

[discussion]
```

- The label states the intent: `praise`, `nitpick`, `suggestion`, `issue`, `todo`, `question`, `thought`, `chore`, `note`.
- Decorations in parentheses refine it: `(blocking)`, `(non-blocking)`, `(if-minor)`. Teams may add their own, such as `(security)` or `(test)`; document them.
- The subject is a single sentence a reader can act on; the discussion carries the reasoning, evidence and alternatives.

Examples:

```text
suggestion (non-blocking): extract the retry settings into `RetryPolicy`.

  The same three numbers appear in `fetchRates()` and `fetchHolidays()`.
  A shared type makes it a one-line change when the provider's limits change.

issue (blocking): `deleteProject()` removes rows by `project_id` only.

  A caller from tenant A can delete tenant B's project by guessing the id.
  Add `AND tenant_id = $2` to the delete and to the preceding lookup, plus a test for the cross-tenant case.

question: why `Math.floor` here instead of rounding?

  Prices like 19.99 -> 1998 look off by one minor unit. If that is intended (truncate), a comment would help.
```

## 2. Severity guide

| Level | Meaning | Typical labels |
|---|---|---|
| Blocker | Must change before merge: defect, security hole, data loss, broken contract, missing test for critical behavior | `issue (blocking)`, `todo`, `chore` |
| Should fix | Real improvement the reviewer wants but will accept a reasoned no | `suggestion`, `question` |
| Optional | Preference, polish, follow-up idea | `nitpick`, `thought`, `suggestion (non-blocking)` |
| Positive | Reinforcement and context | `praise`, `note` |

If you cannot decide between blocker and should-fix, ask whether you would stop the release for it. If not, it is not a blocker.

## 3. Tone and wording

Principles from the Google guidance: be courteous, explain the reasoning, balance direction with the author's freedom to solve it, comment on the code and not the person, and encourage simplification through code rather than only through explanatory comments.

| Instead of | Write |
|---|---|
| "Why did you do it this way?" | "question: what does this approach give us over the existing `RateLimiter`?" |
| "This is confusing." | "suggestion: renaming `data` to `pendingInvoices` would make the loop easier to follow." |
| "You forgot to handle null." | "issue (blocking): `lookup()` can return `null` when the id is unknown; line 42 dereferences it." |
| "Just use a map." | "suggestion: a `Map` keyed by id makes this lookup O(1); the nested loop is O(n*m) and the lists can reach thousands." |
| "LGTM" on a complex change | "Reviewed design, tests and the migration. Did not review generated client code. Approving." |
| "Wrong." | "issue: this returns 0 for an empty list, but the spec in the ticket says it should be an error." |

Habits that help:

- Lead with what works when it does; the author reads the whole thread.
- Use "we" for shared code ownership and "I" for personal reactions ("I find this hard to follow").
- Ask before assuming: the author may know something you do not.
- Give the reason and, where cheap, the fix. A one-line snippet beats a paragraph.
- Link to the guideline, doc or example instead of re-explaining it.
- Keep the number of comments proportionate; if there are many of the same kind, comment once and say "same elsewhere in this file".
- Use a video call for emotionally loaded or complicated threads, then post the outcome in writing.

## 4. Making comments actionable

An actionable comment has four parts:

1. Location: the exact line or range.
2. Problem: what is wrong or unclear, with evidence (input that fails, line reference, link).
3. Impact: why it matters (bug, security, maintainability, cost).
4. Direction: a fix, an option list, or a question that leads to one.

Example with all four:

```text
issue (blocking): `parseDuration("1d")` returns 86400000 but the doc in `README` says durations are in seconds.

  Callers in `scheduler.ts` pass the result to `setTimeout` expecting ms, `billing.ts` expects seconds.
  Pick one unit and name it in the function (`parseDurationMs`) and update the other caller; add a test for "1d".
```

## 5. Receiving feedback

- Treat comments as input about the code. Assume good intent; ask for clarification if a comment is unclear.
- Respond to every thread: fixed (say which commit), declined with a reason, or a follow-up ticket link.
- If you disagree, explain the constraint or data behind your choice; if the reviewer is still not convinced, move to a call and bring in a third person if needed.
- If a reviewer was confused by the code, improve the code or add a comment rather than only replying in the thread.
- Do not push large unrelated changes in response to a small comment; it resets the reviewer's context.
- Say thanks for catches; it makes the next review easier.

## 6. Resolving disagreement

Order of precedence suggested by the Google guidance:

1. Technical facts and data override opinions and preferences.
2. On style, the project style guide (and formatter) is the authority; if nothing applies, accept the author's choice or the existing code's.
3. On design, weigh engineering principles, not personal taste; if several options are valid, prefer the author's.
4. If consensus fails after discussion, escalate to the code owner, tech lead or architecture group, and write the decision in the PR.
5. A reviewer should not hold up a change indefinitely over a matter of taste; an author should not merge over an unresolved blocking comment.

## 7. Turnaround norms

- Respond to a review request within one business day at most; shorter for small changes and during active collaboration. Respond to author updates faster than to new requests.
- Reviewing is part of the job, not an interruption; put review time in the schedule. Check queues at natural breaks (after a build, before lunch).
- If you cannot review in time, say so and suggest another reviewer.
- Authors help by sending small changes, a clear description, and green CI.
- When a time-zone gap makes round trips slow, reviewers leave complete feedback including approve-with-comments so the author can merge without another round.
- Approve with comments when remaining issues are minor and the author can be trusted to fix them; request changes when you need to see the result.
- Track time to first response and time to merge as team health indicators; address queues by sharing load, not by lowering the bar.

## 8. Emergency changes

- Define in writing what qualifies as an emergency (production outage, active security incident) and who may approve.
- Review can follow merge for emergencies; schedule a full review within a business day and record follow-ups.
- Keep the fix minimal; refactors wait for the normal process.

## 9. Pull request description template

```text
## What and why
<one paragraph; link to issue or design>

## How it was tested
<tests added, manual steps, screenshots>

## Risk and rollback
<what could break, flags, migration notes, how to roll back>

## Notes for reviewers
<where to start, what to skip (generated files), open questions>
```
