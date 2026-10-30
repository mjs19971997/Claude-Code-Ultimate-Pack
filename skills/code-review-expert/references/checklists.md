# Review Checklists

Checklists to apply by area when reviewing a change, plus a section for AI-generated and very large diffs. Verified against Google Engineering Practices (Code Review), OWASP Top 10:2025 and OWASP Cheat Sheet Series categories, GitHub Actions security hardening guidance, CodeQL CLI 2.27.x and Semgrep 1.183.0 (2026-10). Use the lists as prompts, not as a form to fill in: pick the sections that match what the change touches.

## 1. Design

- Does the change belong in this codebase and this layer? Is there an existing mechanism it duplicates?
- Does it follow the existing architecture and module boundaries, or does it introduce a dependency in the wrong direction?
- Is the abstraction level right: no speculative generality, no copy-paste that should be shared, no premature framework?
- Are responsibilities clear: each function or class has one reason to change; names say what they do?
- Is the public surface minimal: only what callers need is exported; internal details can change later?
- Will it be easy to change or remove? Flags, seams and boundaries where the future is uncertain.
- Does it interact well with the rest of the system: callers, other implementations of the interface, configuration, docs, dashboards?
- Is the complexity justified? Could the same behavior be achieved with fewer moving parts?

## 2. Correctness

- Does the code do what the description says for the main path, and for empty, null, minimum, maximum, duplicate and malformed inputs?
- Off-by-one errors in loops, pagination, ranges and time windows; inclusive versus exclusive bounds.
- Time: time zones, daylight saving, clock skew, monotonic versus wall-clock time, expiry comparisons.
- Numbers: integer overflow, floating-point money, rounding mode, division by zero, unit mix-ups.
- Text: encoding, normalization, case sensitivity, locale-dependent comparisons, truncation of multi-byte characters.
- State machines: every transition is valid; illegal states are unrepresentable or rejected.
- Resource handling: files, sockets, transactions and locks are released on all paths.
- Idempotence: can the operation be retried safely after a partial failure?
- Backward and forward compatibility with stored data, old clients and in-flight messages.

## 3. Concurrency

- Shared mutable state: who else can touch it? Is access synchronized or confined to one thread, task or actor?
- Check-then-act races (TOCTOU): existence checks followed by writes need a transaction, a unique constraint or an atomic operation.
- Read-modify-write on a database row: use an atomic update, `SELECT ... FOR UPDATE`, or optimistic version checks.
- Lock ordering and holding locks across I/O or callbacks; deadlock and starvation potential.
- Async code: awaited everywhere it must be; unhandled rejections; fire-and-forget tasks with no error path; cancellation and timeout propagation.
- Parallelism limits: unbounded `Promise.all` or goroutine spawning over user-controlled sizes.
- Retries and duplicates: at-least-once delivery means consumers must deduplicate.
- Memory visibility and ordering when using lock-free structures or atomics; prefer higher-level primitives unless measured.
- Tests for concurrency: stress or deterministic scheduling where possible; flaky tests are findings, not noise.

## 4. Error handling

- Errors are handled at a level that can act on them; no empty `catch`, no `catch` that logs and continues into an invalid state.
- Error types are specific; callers can distinguish retryable, user-fixable and bug conditions.
- Messages help the operator without leaking secrets, personal data or internals to end users.
- Timeouts on every network call and queue wait; limits on retries with backoff and jitter; circuit breaking where cascades are possible.
- Partial failure in batches: report per item; do not drop the rest or report success wholesale.
- Cleanup and rollback on failure paths (transactions, temp files, reserved resources).
- Panics, assertions and `process.exit` only for programmer errors and startup failures.
- Fallbacks do not hide failures from monitoring.

## 5. Security

Injection and unsafe interpretation:

- SQL: parameterized queries or a query builder; no string concatenation of untrusted values; identifiers from allowlists only.
- OS commands: avoid shells; pass an argument array to the process API; validate against allowlists.
- Templates, HTML, headers, logs: output encoding for the right context; no raw HTML sinks (`innerHTML`, `dangerouslySetInnerHTML`) with untrusted data without a sanitizer.
- Regular expressions on untrusted input: avoid catastrophic backtracking; cap input length.
- Deserialization of untrusted data: use data-only formats with schema validation; avoid formats that instantiate arbitrary types.
- Server-side requests to user-supplied URLs (SSRF): allowlist schemes and hosts, block private and link-local ranges after DNS resolution, disable redirects or revalidate them.

Authentication and authorization:

- Every new endpoint, job and message handler has an explicit authorization check on the server; the default is deny.
- Object-level checks: the caller may access this specific record (guard against insecure direct object references).
- Tenant isolation on reads and on writes and deletes (`UPDATE` and `DELETE` need the tenant predicate as much as `SELECT`); also on caches, files and search indexes.
- Privileged fields are not bindable from request bodies (mass assignment); role changes are checked.
- Sessions and tokens: expiry, rotation, revocation, secure cookie flags, CSRF protection where cookies authenticate requests.

Files and paths:

- User-supplied file names or paths are never joined to a base directory unchecked: normalize and resolve (including symlinks), then verify the result is inside the base directory; reject NUL bytes and absolute paths; prefer generated storage names over user-supplied names.
- Archive extraction (zip slip): check every entry's resolved destination; cap size and count.
- Upload handling: size limits, content-type verification by content, storage outside the web root, no execution permissions.

Secrets and data:

- No credentials, tokens, private keys or connection strings in code, tests, fixtures, config samples, images or logs; secret scanning in CI and push protection enabled.
- Personal data minimized, encrypted in transit and at rest where required, and absent from logs, URLs and analytics events.
- Cryptography uses vetted libraries and current algorithms (AEAD ciphers, password hashing with Argon2id, scrypt or bcrypt, secure random for tokens); no custom schemes; constant-time comparison for secrets and MACs.
- Error responses and stack traces do not leak internals.

Dependencies and supply chain:

- New packages: needed, maintained, licensed compatibly, and spelled correctly (check the registry page; look-alike and nonexistent names are a known risk).
- Lockfile updated consistently; no install scripts run from unknown packages without review; versions pinned or ranges justified.

## 6. Performance

- Database: queries inside loops, missing indexes for new filters and sorts, `SELECT *` on wide tables, unbounded lists without pagination, transactions held open across network calls.
- Complexity of loops and searches on growing inputs; repeated work that could be hoisted or cached.
- Memory: large objects held longer than needed, unbounded buffers and caches, streaming versus loading whole files.
- I/O: blocking calls on event loops or request threads, sequential calls that could be concurrent, chatty protocols.
- Caching: key includes every input that changes the value (tenant, user, locale); invalidation is defined; TTLs make sense.
- Evidence for claims: benchmark or profile attached when the change is about speed; budgets stated for hot paths.

## 7. API and database changes

API:

- Backward compatible for existing clients: new fields optional, no changed meaning, no removed fields without a deprecation path; versioning rule respected.
- Validation, error format, status codes, pagination, rate limits and idempotency keys follow the API conventions.
- Documentation and examples updated; generated clients regenerated.

Database migrations:

- Safe to run while the old version is serving traffic: additive first (expand), switch code, remove later (contract).
- No long exclusive locks on large tables; indexes created concurrently where the database supports it; backfills in batches.
- Reversible or with a documented forward-fix plan; tested on production-sized data.
- Constraints and defaults match application invariants; nullability changes are staged.

## 8. Reviewing AI-generated and very large diffs

AI-generated changes deserve the same standard as human changes, applied with specific risks in mind. The author is accountable for every line they submit.

- Ask what the change is meant to do and what spec, issue or prompt it came from. A description the author cannot explain in their own words is a sign to slow down.
- Check that every referenced function, method, flag, config key and package exists in the version in use. Invented APIs and nonexistent package names are common failure modes.
- Look for plausible but wrong logic: boundary conditions, ordering assumptions, silently swallowed errors, defaults that differ from the real system.
- Compare against the request: unrequested refactors, removed checks, deleted tests, changed lint configuration, loosened types, added dependencies.
- Search for duplicated utilities and patterns the codebase already has; ask for reuse.
- Read the tests with suspicion: tests that restate the implementation, assert on mocks, or pass for any input. Confirm a test fails when the behavior is broken (mutation by hand).
- Verify security-sensitive code line by line; generated code often omits authorization, input validation, or tenant predicates on writes.
- Run it: build, tests, linters and the changed behavior locally or in a preview environment.
- Prefer smaller, incremental generations; reject a single huge generated change and ask for steps.

Very large diffs (hand-written or generated):

- Ask for a split first; a reviewer cannot hold thousands of changed lines in mind. Propose a sequence: preparatory refactor, interface or schema, behavior, cleanup.
- Review by commit if commits are meaningful; otherwise by directory or layer, starting from interfaces, tests and schemas.
- Separate mechanical changes (renames, moves, formatting, codemods) from logic. Review the tool invocation or script and a sample, and confirm the rest by running the tool again.
- Generated artifacts (lockfiles, clients, protobuf output, snapshots): review the generator input and version, regenerate and diff, and do not hand-edit.
- Say explicitly in the review what you did and did not examine.
- Use risk-based depth: auth, money, data deletion and migrations get line-by-line review; boilerplate gets a sample.

## 9. Tests

- A regression test exists for bug fixes and fails without the fix.
- New behavior is covered for success, failure and edge cases; names state the rule.
- Assertions check outcomes, not implementation details; mocks are limited to true boundaries.
- Tests are deterministic and independent: no real time, network or shared global state; random data seeded.
- Test code is held to review standards: readable, minimal setup, no commented-out cases, no skipped tests without a ticket.

## 10. Dependencies and configuration

- New dependency justified against writing a small function; license and maintenance checked; size and transitive footprint considered.
- Configuration changes are safe by default; new settings have documented defaults and validation at startup.
- Feature flags have an owner and a removal plan.
- Infrastructure-as-code changes: reviewed for blast radius, public exposure, IAM scope and data deletion (plan output attached).

## 11. CI workflow and build changes

- Workflows declare least-privilege `permissions:`; tokens are not granted write access by default.
- Untrusted data (`github.event.*` fields such as titles, branch names and comment bodies, and workflow inputs) is never interpolated into `run:` scripts; pass it through `env:` and quote it in the script.
- Third-party actions are pinned to a full commit SHA or an approved version; `pull_request_target` and `workflow_run` triggers are reviewed with great care because they run with secrets.
- Secrets are not echoed, written to artifacts or passed to forks' workflows.
- Caches and artifacts cannot be poisoned by pull requests from forks.

## 12. User interface changes

- Accessibility: semantic elements, labels, focus order and visible focus, keyboard operation, color contrast, announced state changes.
- States: loading, empty, error, partial and offline are designed and tested.
- Rendering of untrusted content is escaped; links to external sites use safe attributes.
- Internationalization: no concatenated sentences, plural rules and formats from the locale.
- Screenshots or recordings attached for visual changes, including narrow screens.
