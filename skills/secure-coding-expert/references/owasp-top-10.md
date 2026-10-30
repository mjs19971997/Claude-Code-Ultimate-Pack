# OWASP Top 10:2025 Review Guide

The OWASP Top 10:2025 is the current edition of the OWASP awareness list for web application risks (https://owasp.org/Top10/2025/). Use it as a review checklist and a shared vocabulary, not as a complete standard; for verification depth use OWASP ASVS. API-specific risks are covered by the separate OWASP API Security Top 10 (see api-security-expert).

## 1. Categories and defenses

### A01:2025 Broken Access Control
Includes IDOR, missing function-level checks, CORS misconfiguration, forced browsing, CSRF, and Server-Side Request Forgery (SSRF, CWE-918), which was its own category in 2021.
- Deny by default; check object ownership or tenant on every read and write (authorization-expert, api-security-expert).
- SSRF: destination allowlist, dial-time IP checks, redirect re-validation, no environment proxy, network egress controls (SKILL.md Example 2).
- Path traversal: resolve and check containment (SKILL.md Example 1).

### A02:2025 Security Misconfiguration
Default credentials, debug endpoints, verbose errors, permissive cloud storage, missing security headers, XML external entities.
- Hardened, reproducible configuration (infrastructure as code), with production and staging differing only in secrets and scale.
- Disable XML external entity and DTD processing in every XML parser.
- Shared middleware for security headers and cookie attributes; automated checks in CI and against staging.

### A03:2025 Software Supply Chain Failures
Expands the 2021 "Vulnerable and Outdated Components" to the whole build chain: dependencies, build systems, CI/CD, artifact distribution.
- Lockfiles and pinned versions; SCA on every build (Dependabot, Renovate, Snyk, Trivy, OSV-Scanner).
- SBOM per release (CycloneDX or SPDX); signed artifacts and provenance (Sigstore, SLSA levels).
- CI hardening: least-privilege tokens, pinned third-party actions by commit SHA, no untrusted input interpolated into shell steps, OIDC federation instead of stored cloud keys.
- Guard against typosquatting and dependency confusion: scoped registries, private package namespaces.

### A04:2025 Cryptographic Failures
Weak or missing encryption, weak hashes for passwords, predictable randomness, keys in code.
- TLS 1.2+ (prefer 1.3), HSTS; AES-GCM or ChaCha20-Poly1305 via vetted libraries; keys in a KMS.
- Argon2id for passwords; CSPRNG for tokens; no custom crypto.

### A05:2025 Injection
SQL, NoSQL, OS command, LDAP, template (SSTI), expression language, header and log injection, and cross-site scripting.
- Parameterized queries; argument arrays for processes; auto-escaping templates; sandboxed or logic-less templates for user-authored content; CSP as a second layer for XSS.

### A06:2025 Insecure Design
Missing threat modeling, missing abuse cases, business logic that can be skipped or replayed.
- Threat model new features (Section 3), write abuse cases next to user stories, use server-side state machines for multi-step flows, add limits to business flows.

### A07:2025 Authentication Failures
Credential stuffing, weak passwords, missing MFA, session fixation, unverified tokens.
- See authentication-expert: Argon2id, breached-password screening, phishing-resistant MFA (passkeys), session rotation on login, strict JWT validation.

### A08:2025 Software or Data Integrity Failures
Unsigned updates, insecure deserialization, trusting data or code from untrusted sources without integrity checks.
- JSON or Protobuf with schemas instead of native serialization; signature verification on updates, plugins and webhooks; SRI on third-party scripts.

### A09:2025 Security Logging and Alerting Failures
Security events not logged, logs not monitored, alerts missing or ignored, sensitive data written to logs.
- Log authentication, authorization denials, validation failures and admin actions with actor, action, target, outcome, request id.
- Ship to a central store with retention and access control; alert on patterns, and test that alerts fire.
- Neutralize CR/LF and control characters in logged user input (log injection).

### A10:2025 Mishandling of Exceptional Conditions
New in 2025: improper handling of errors, unexpected states and resource exhaustion that leads to failing open, leaking information or leaving inconsistent state.
- Fail closed on errors in security decisions; release resources and roll back transactions on every error path.
- Generic client errors with correlation ids; full detail only in server logs.
- Bounded retries, timeouts and resource limits; global handlers for unhandled rejections and panics that log and terminate cleanly.

## 2. Mapping from the 2021 edition

| 2021 | 2025 |
|---|---|
| A01 Broken Access Control | A01 Broken Access Control |
| A02 Cryptographic Failures | A04 Cryptographic Failures |
| A03 Injection | A05 Injection |
| A04 Insecure Design | A06 Insecure Design |
| A05 Security Misconfiguration | A02 Security Misconfiguration |
| A06 Vulnerable and Outdated Components | A03 Software Supply Chain Failures (broader scope) |
| A07 Identification and Authentication Failures | A07 Authentication Failures |
| A08 Software and Data Integrity Failures | A08 Software or Data Integrity Failures |
| A09 Security Logging and Monitoring Failures | A09 Security Logging and Alerting Failures |
| A10 Server-Side Request Forgery | merged into A01 Broken Access Control |
| (none) | A10 Mishandling of Exceptional Conditions |

When a report, policy or contract references the 2021 IDs, quote both IDs (for example "A05:2025 Injection (A03:2021)") to avoid confusion.

## 3. Threat modeling

1. Draw the data flow: actors, processes, data stores, trust boundaries.
2. For each element crossing a boundary, walk STRIDE: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.
3. Record each threat with a mitigation, an owner and a test; map it to a Top 10 category and CWE.
4. Revisit when a new entry point, data store, third party or privilege level is added.

Lightweight tools: OWASP Threat Dragon, a Markdown table next to the design doc.

## 4. Testing pipeline

| Stage | Tooling examples | Gate |
|---|---|---|
| Pull request | Semgrep, CodeQL, secret scanning (Gitleaks), SCA | Block new high/critical findings |
| Build | SBOM generation, image scanning (Trivy, Grype), artifact signing | Block known exploitable CVEs in runtime images |
| Staging | DAST (OWASP ZAP baseline/full scan), authenticated scans | Triage before release |
| Periodic | Penetration test, dependency review, threat model refresh | Track findings to closure |

Notes:
- Tune SAST rules to the codebase; a noisy gate gets bypassed. Add custom rules for banned APIs.
- Never run active DAST against production without explicit approval and a rollback plan.
- Record accepted risks with an owner and an expiry date, and re-review them on expiry.

## 5. Review report shape

For each finding: title, location (file:line or endpoint), Top 10:2025 category and CWE, impact, reproduction steps or payload, fix, and the regression test that proves the fix.
