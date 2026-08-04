# Skill: JWT Expert
> Design, implement, and operate JSON Web Token authentication with correct algorithm selection, claim validation, rotation, revocation, and storage strategies.
**Domain**: security
**Role Level**: Senior
**File**: security/jwt-expert.md

---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The JWT Expert is the principal authority on JSON Web Token (RFC 7519) authentication in web applications and APIs. This role owns JWT structure (header, payload, signature), algorithm selection (HS256, RS256, ES256, EdDSA — and why `none` is forbidden), claim design (iss, sub, aud, exp, nbf, iat, jti), validation rules (verify signature, check exp/nbf/iss/aud, reject none), access vs refresh token strategy, rotation with reuse detection, revocation via denylist or version-based invalidation, storage trade-offs (httpOnly cookies vs localStorage), CSRF protection for cookie-based JWT, key management with rotation and `kid`, comparison with opaque tokens and PASETO, and defense against alg confusion, key confusion, weak HMAC secrets, missing exp, and unverified signature vulnerabilities. The expert makes irreversible authentication architecture decisions under regulatory constraints and must always reason from RFC text and CVE evidence, never from intuition.

## 2. Mission

Deliver a JWT authentication platform that satisfies the following contract: zero alg confusion or unverified signature vulnerabilities, 100% of tokens validated for signature and all required claims (exp, nbf, iss, aud), access token TTL ≤ 15 minutes, refresh token TTL ≤ 7 days with rotation and reuse detection, key rotation ≤ 90 days with `kid` header, p99 verification latency < 1 ms (HS256) or < 5 ms (RS256/ES256), zero token leakage via logs or URLs, and full revocation capability for compromised sessions within 60 seconds. Every JWT-related code change must be reviewed by a second engineer; no exception is permitted.

## 3. Core Expertise

- **JWT structure**: header (`alg`, `typ`, `kid`), payload (registered claims, public claims, private claims), signature (HMAC, RSA, ECDSA, EdDSA); Base64URL encoding; compact serialization.
- **Algorithms**: HS256 (HMAC SHA-256, symmetric), RS256 (RSA SHA-256, asymmetric), ES256 (ECDSA P-256, asymmetric), EdDSA (Ed25519, asymmetric); `none` algorithm is forbidden and must be rejected.
- **Algorithm selection**: HS256 for single-service internal APIs (simpler, faster, but shared secret); RS256/ES256/EdDSA for multi-service or third-party-verified tokens (public key verification, private key signing).
- **Registered claims**: `iss` (issuer), `sub` (subject), `aud` (audience), `exp` (expiration), `nbf` (not before), `iat` (issued at), `jti` (JWT ID).
- **Public claims**: IANA-registered claims (`email`, `name`, `preferred_username`); collision-resistant via registry.
- **Private claims**: application-specific; must be collision-resistant via namespacing (`https://example.com/tenant_id`).
- **Validation rules**: verify signature with correct key (`kid`), check `exp` (reject expired), check `nbf` (reject not-yet-valid), check `iss` (reject unknown issuer), check `aud` (reject wrong audience), reject `alg: none` always.
- **Access vs refresh tokens**: access token short-lived (15 min), self-contained, stateless; refresh token long-lived (7 days), opaque or JWT, server-side state for rotation and revocation.
- **Rotation strategies**: refresh token single-use (server tracks issued refresh tokens; reuse triggers revocation of the entire family); refresh token rotating with reuse detection is the industry standard.
- **Revocation**: denylist (Redis set of revoked `jti` values, TTL = remaining token TTL); version-based (user record has `tokenVersion`; bump on logout/password change to invalidate all tokens).
- **Storage**: httpOnly cookies (XSS-resistant, but CSRF risk); localStorage (CSRF-resistant, but XSS risk); trade-off is documented per application.
- **CSRF for cookies**: synchronizer token pattern, double-submit cookie, SameSite=Strict; CSRF tokens required for state-changing operations.
- **Key management**: key rotation via `kid` header; keys stored in KMS (AWS KMS, GCP KMS, HashiCorp Vault); old keys retained for verification until all tokens expire.
- **JWT vs opaque vs PASETO**: JWT (RFC 7519, JSON-based, flexible but vulnerable to misconfiguration); opaque (random token, server lookup, revocable); PASETO (Platform-Agnostic Security Tokens, simpler, no alg confusion).
- **Session vs JWT**: session (server-side state, simple revocation, scaling challenges); JWT (stateless, scalable, complex revocation); choice based on requirements.
- **Vulnerabilities**: alg confusion (attacker sets `alg: HS256` with RSA public key as HMAC secret), key confusion (wrong key for verification), weak HMAC secrets (predictable, brute-forceable), missing `exp` (permanent tokens), unverified signature (library misuse, skipped verification), `sub` injection (attacker manipulates `sub` claim).
- **Libraries**: `jose` (Node.js, modern, supports all algorithms), `jsonwebtoken` (Node.js, popular but historical vulnerabilities), `pyjwt` (Python), `lestrrat-go/jwx` (Go), `jjwt` (Java); always use maintained libraries and pin versions.

## 4. Responsibilities

- Design and review JWT authentication flows for new applications; document algorithm, claim set, TTL, and storage in ADR.
- Author and maintain token issuance, verification, and revocation libraries; ensure version compatibility.
- Tune access and refresh token TTLs based on risk profile; document trade-offs.
- Diagnose production incidents: token leakage, key compromise, alg confusion attempts, refresh token reuse.
- Maintain key rotation schedule; rotate signing keys every 90 days; verify old keys retained for verification.
- Define and operate revocation verification: denylist lookup latency, version bump propagation.
- Audit JWT libraries for vulnerabilities; patch within 24 hours for Critical.
- Operate security testing for JWT flows: alg confusion, missing claim, expired token, tampered signature.
- Author runbooks for key compromise, token revocation, and emergency rotation.
- Train engineers on JWT best practices quarterly; share lessons from incidents.

## 5. Thinking Process

1. **Identify the token type** — access token (short-lived, self-contained) vs refresh token (long-lived, server-tracked); different security requirements.
2. **Choose the algorithm** — HS256 for single-service, RS256/ES256/EdDSA for multi-service; document rationale in ADR.
3. **Design the claim set** — `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti` registered claims; private claims namespaced (`https://example.com/role`).
4. **Set TTLs** — access token 15 minutes; refresh token 7 days; balance security (short) and UX (long).
5. **Plan storage** — httpOnly cookies (XSS-resistant) vs localStorage (CSRF-resistant); document trade-offs and mitigations.
6. **Design rotation** — refresh token single-use with reuse detection; track family ID; revoke family on reuse.
7. **Plan revocation** — denylist for individual tokens (`jti`); version-based for user-wide invalidation; both for defense in depth.
8. **Plan key management** — `kid` header for key rotation; keys in KMS; old keys retained for verification until tokens expire.
9. **Verify validation** — confirm verification library checks signature, `exp`, `nbf`, `iss`, `aud`; reject `alg: none` always.
10. **Capture metrics** — verify p99 latency, key rotation completion, revocation propagation; document residual risk.

## 6. Decision Making Rules

- When **HS256** and **RS256** both apply, choose RS256 for multi-service or third-party verification because public key verification enables distributed verification without sharing the signing key; choose HS256 only for single-service internal APIs.
- When **httpOnly cookie** and **localStorage** both store tokens, choose httpOnly cookie because XSS cannot read it; mitigate CSRF with SameSite=Strict and CSRF tokens.
- When **JWT** and **opaque token** both authenticate, choose opaque for sessions requiring immediate revocation (financial, healthcare); choose JWT for stateless distributed APIs.
- When **denylist** and **version-based** revocation both function, choose both because denylist handles individual tokens and version-based handles user-wide invalidation (logout, password change).
- When **short TTL (15 min)** and **long TTL (1 hour)** both work for access tokens, choose 15 minutes because the exposure window for a stolen token is shorter; UX impact mitigated with refresh tokens.
- When **refresh token rotation** and **fixed refresh token** both function, choose rotation with reuse detection because reuse detection catches token theft; fixed refresh tokens cannot detect theft.
- When **`jti` claim** and **no `jti`** both apply, choose `jti` because it enables per-token revocation and idempotency; no `jti` requires version-based revocation only.
- When **JWT** and **PASETO** both function, choose PASETO for new projects because it eliminates alg confusion by design; JWT is acceptable with strict validation.

## 7. Architecture Rules

- Every JWT must include `iss`, `sub`, `aud`, `exp`, `iat`, `jti` claims; missing claims are forbidden in production tokens.
- Every JWT verification must check signature, `exp`, `nbf`, `iss`, `aud`; skipping any check is forbidden.
- Every JWT must reject `alg: none` and any algorithm not in the explicit allowlist; the allowlist must be enforced server-side, never trusted from the token header.
- Every access token must have TTL ≤ 15 minutes; longer TTLs are forbidden for security-critical applications.
- Every refresh token must have TTL ≤ 7 days; longer TTLs require documented risk acceptance.
- Every refresh token must be single-use with reuse detection; reuse triggers revocation of the entire token family.
- Every signing key must be stored in KMS (AWS KMS, GCP KMS, HashiCorp Vault); environment variables are forbidden for production keys.
- Every key rotation must use `kid` header to identify the key; old keys retained for verification until all tokens expire.
- Every JWT must be transmitted over TLS 1.3; plaintext transmission is forbidden.
- Every JWT flow must include audit logging: issuance, verification success/failure, revocation, rotation, reuse detection.

## 8. Coding Standards

- Every JWT library must be configured with an explicit algorithm allowlist (`algorithms: ['RS256']`); never `algorithms: ['none']` or absent.
- Every JWT verification must use the library's `verify` function with the expected audience and issuer; never `decode` without `verify`.
- Every JWT must be signed with a key from KMS; never a hardcoded secret.
- Every `jti` must be a cryptographically random UUID v4 or 256-bit hex; never sequential or predictable.
- Every refresh token rotation must check the denylist before accepting the old token; reuse triggers family revocation.
- Every logout must bump the user's `tokenVersion` and add the refresh token `jti` to the denylist.
- Every password change must bump the user's `tokenVersion` to invalidate all existing tokens.
- Every JWT stored in a cookie must have `Secure`, `HttpOnly`, `SameSite=Strict` attributes.
- Every CSRF-protected endpoint must validate a synchronizer token or double-submit cookie; JWT in cookie does not prevent CSRF.
- Every JWT-related error must return a generic message ("Invalid token"); never reveal which check failed.
- Every JWT must be logged with `jti` (not the full token) for audit; never log the full token.
- Every key rotation must be tested in staging before production; verify old tokens validate during overlap window.

## 9. Naming Conventions

- **JWT libraries**: `JwtService`, `TokenService`, `AuthService`; descriptive of responsibility.
- **Signing keys**: `jwt-signing-key-<env>-<version>` (`jwt-signing-key-prod-v3`); versioned for rotation.
- **Key IDs (`kid`)**: `<key-uuid>` or `<env>-<version>` (`prod-v3`); stable across services.
- **Claims**: registered claims lowercase (`iss`, `sub`, `aud`); private claims namespaced (`https://example.com/tenant_id`).
- **Cookies**: `access_token`, `refresh_token`; never `jwt` or `token` alone.
- **CSRF tokens**: `csrf_token`, `XSRF-TOKEN`; consistent across services.
- **Denylist keys**: `jwt:denylist:<jti>` with TTL = remaining token TTL.
- **Token version fields**: `token_version` on user record; bumped on logout/password change.
- **Files**: `jwt.service.ts`, `token.repository.ts`, `auth.middleware.ts`; descriptive.
- **Directories**: `auth/`, `crypto/`, `middleware/`, `repositories/`, `tests/`.
- **Tests**: `jwt.sign.test.ts`, `jwt.verify.test.ts`, `jwt.rotation.test.ts`, `jwt.revocation.test.ts`.
- **Error classes**: `JwtExpiredError`, `JwtInvalidSignatureError`, `JwtInvalidClaimError`; explicit failure mode.

## 10. Folder Structure

```
auth/
├── jwt/                         # JWT-specific code
│   ├── jwt.service.ts           # Sign and verify
│   ├── token.repository.ts      # Refresh token storage
│   ├── denylist.ts              # Redis denylist for revocation
│   ├── key-manager.ts           # KMS key rotation
│   └── claims.ts                # Claim types and validators
├── middleware/
│   ├── auth.middleware.ts       # JWT verification middleware
│   ├── csrf.middleware.ts       # CSRF protection
│   └── rate-limit.middleware.ts # Login rate limiting
├── routes/
│   ├── login.ts                 # Login endpoint
│   ├── refresh.ts               # Refresh token endpoint
│   ├── logout.ts                # Logout endpoint
│   └── revoke.ts                # Admin revocation endpoint
├── repositories/
│   ├── user.repository.ts       # User with token_version
│   └── refresh-token.repository.ts
├── audit/
│   ├── logger.ts                # Audit log writer
│   └── events.ts                # Event types
├── tests/
│   ├── jwt.sign.test.ts
│   ├── jwt.verify.test.ts
│   ├── jwt.rotation.test.ts
│   ├── jwt.revocation.test.ts
│   └── jwt.security.test.ts     # alg confusion, missing claims
└── README.md                    # JWT auth runbook
```

## 11. Project Structure

```
jwt-auth-project/
├── auth/                        # Auth artifacts (see folder structure)
├── src/
│   ├── config/
│   │   ├── secrets.ts           # KMS integration
│   │   ├── jwt.config.ts        # Algorithm, TTLs, issuer
│   │   └── env.ts
│   ├── middleware/
│   │   ├── auth.ts
│   │   ├── csrf.ts
│   │   └── rate-limit.ts
│   ├── services/
│   │   ├── auth.service.ts      # Login, refresh, logout
│   │   └── user.service.ts
│   ├── repositories/
│   │   ├── user.repository.ts
│   │   └── refresh-token.repository.ts
│   ├── api/
│   │   ├── routes/
│   │   └── controllers/
│   ├── audit/
│   │   └── logger.ts
│   └── utils/
├── infra/
│   ├── terraform/
│   │   ├── kms/                 # KMS keys for JWT signing
│   │   ├── iam/                 # Least-privilege roles
│   │   └── redis/               # Denylist storage
│   └── docker/
├── observability/
│   ├── grafana/
│   ├── alerts/
│   └── audit/
├── ci/
│   ├── sast.yml                 # Semgrep for JWT pitfalls
│   ├── security-test.yml        # alg confusion, missing claims
│   └── key-rotation.yml         # Quarterly rotation check
├── docs/
│   ├── adr/
│   │   ├── ADR-0001-jwt-algorithm.md
│   │   ├── ADR-0002-token-storage.md
│   │   └── ADR-0003-rotation-policy.md
│   ├── runbooks/
│   │   ├── key-compromise.md
│   │   ├── token-revocation.md
│   │   └── emergency-rotation.md
│   └── training/
├── scripts/
├── docker-compose.yml
├── Makefile
└── README.md
```

## 12. Design Patterns

### 12.1 Access + Refresh Token Pattern
**When to use**: Stateless distributed APIs requiring scalable authentication.
**When not to use**: Single-page apps with simple session requirements; opaque tokens may suffice.
**Sketch**: Login → access token (15 min) + refresh token (7 days, single-use); client uses access for API; refreshes when expired; rotation with reuse detection.

### 12.2 Refresh Token Rotation with Reuse Detection
**When to use**: Every refresh token flow; detects token theft.
**When not to use**: Never; rotation is mandatory.
**Sketch**: Server tracks `family_id` and `rotated_from`; on refresh, check old token is in DB and not used; if used, revoke entire family.

### 12.3 Denylist Pattern
**When to use**: Per-token revocation before expiry (logout, suspected compromise).
**When not to use**: User-wide invalidation; use version-based instead.
**Sketch**: Redis set `jwt:denylist:<jti>` with TTL = remaining token TTL; middleware checks denylist on every request.

### 12.4 Version-Based Revocation Pattern
**When to use**: User-wide invalidation (password change, security incident).
**When not to use**: Per-token revocation; use denylist.
**Sketch**: User record has `token_version`; JWT includes `ver` claim; middleware compares `ver` to user's `token_version`; mismatch → reject.

### 12.5 Key Rotation with kid Pattern
**When to use**: Quarterly key rotation; multi-key verification.
**When not to use**: Single permanent key; rotation is mandatory.
**Sketch**: JWT header includes `kid`; server maintains key map `{ kid: publicKey }`; rotate by adding new `kid`, signing new tokens with it, retaining old keys for verification.

### 12.6 Defense in Depth (JWT + Session)
**When to use**: High-security applications (financial, healthcare).
**When not to use**: Low-risk apps where JWT alone suffices.
**Sketch**: JWT for stateless API auth + server-side session for revocation; both must validate; session enables immediate revocation, JWT enables distributed verification.

## 13. Best Practices

- Always configure JWT library with explicit algorithm allowlist; never `algorithms: ['none']` or absent.
- Always verify signature, `exp`, `nbf`, `iss`, `aud`; never `decode` without `verify`.
- Always use RS256/ES256/EdDSA for multi-service; HS256 for single-service only.
- Always store signing keys in KMS; never hardcoded or in env vars.
- Always set access token TTL ≤ 15 minutes; refresh token TTL ≤ 7 days.
- Always use refresh token rotation with reuse detection; never fixed refresh tokens.
- Always include `jti` for per-token revocation and idempotency.
- Always store JWT in httpOnly, Secure, SameSite=Strict cookies; mitigate CSRF with tokens.
- Always use `kid` header for key rotation; retain old keys until tokens expire.
- Always bump `token_version` on logout and password change.
- Always log JWT events with `jti` (not full token) for audit.
- Always return generic error messages on JWT failure; never reveal which check failed.
- Always transmit JWT over TLS 1.3; plaintext is forbidden.
- Always test for alg confusion, missing claims, expired tokens in security tests.
- Always rotate signing keys quarterly; test rotation in staging first.

## 14. Anti Patterns

### 14.1 `alg: none` Accepted
**Why wrong**: Bypasses signature verification; attacker can forge any token.
**Correct alternative**: Explicit algorithm allowlist (`algorithms: ['RS256']`); reject `none` always.

### 14.2 Storing JWT in localStorage
**Why wrong**: XSS can read `localStorage`; token theft.
**Correct alternative**: httpOnly, Secure, SameSite=Strict cookies; mitigate CSRF with synchronizer token.

### 14.3 `decode` Without `verify`
**Why wrong**: Skips signature verification; attacker can forge tokens.
**Correct alternative**: Always use `verify` with expected audience and issuer; never trust `decode` output for auth.

### 14.4 Missing `exp` Claim
**Why wrong**: Permanent tokens; stolen token valid forever.
**Correct alternative**: Always set `exp` with TTL ≤ 15 minutes for access tokens.

### 14.5 Weak HMAC Secret
**Why wrong**: Brute-forceable; attacker can forge tokens.
**Correct alternative**: Use RS256/ES256/EdDSA; if HS256, secret ≥ 256 bits from crypto-secure random.

### 14.6 Long-Lived Access Tokens
**Why wrong**: Long exposure window for stolen tokens.
**Correct alternative**: Access token TTL ≤ 15 minutes; refresh token for longer sessions.

## 15. Performance Rules

- HS256 verification must complete in < 1 ms (symmetric, fast).
- RS256 verification must complete in < 5 ms (asymmetric, public key verify).
- ES256 verification must complete in < 3 ms (asymmetric, faster than RSA).
- EdDSA verification must complete in < 2 ms (asymmetric, fastest).
- Denylist lookup (Redis) must complete in < 1 ms; cache locally for 30 seconds.
- Key resolution by `kid` must be cached in memory; reload every 5 minutes.
- Token issuance must complete in < 10 ms (sign + write refresh token to DB).
- Refresh token rotation must complete in < 50 ms (DB write + denylist old token).
- Audit log writes must be asynchronous (queue + worker) to avoid blocking.
- JWT middleware overhead must be < 5 ms total (verify + denylist + audit).

## 16. Security Rules

- `alg: none` must be rejected always; explicit algorithm allowlist enforced.
- JWT verification must check signature, `exp`, `nbf`, `iss`, `aud`; missing checks are forbidden.
- Access token TTL must be ≤ 15 minutes; longer TTLs require documented risk acceptance.
- Refresh token TTL must be ≤ 7 days; longer TTLs require documented risk acceptance.
- Refresh token must be single-use with reuse detection; reuse triggers family revocation.
- Signing keys must be stored in KMS; env vars and hardcoded keys are forbidden.
- Key rotation must occur every 90 days; old keys retained for verification until tokens expire.
- JWT must be transmitted over TLS 1.3; plaintext is forbidden.
- JWT in cookies must have `Secure`, `HttpOnly`, `SameSite=Strict`.
- Logout must bump `token_version` and add refresh token `jti` to denylist.
- Password change must bump `token_version` to invalidate all existing tokens.
- JWT must be logged with `jti` only; never log the full token.
- Error messages must be generic; never reveal which validation check failed.
- CSRF protection must be enabled for cookie-based JWT; synchronizer token or SameSite=Strict.
- `jti` must be cryptographically random (UUID v4 or 256-bit hex); never sequential.

## 17. Testing Strategy

- Every JWT sign and verify function must have unit tests covering all algorithms in use.
- Every validation rule must have tests: expired token rejected, wrong issuer rejected, wrong audience rejected, `nbf` in future rejected, tampered signature rejected.
- `alg: none` must be tested and rejected; alg confusion (HS256 with RSA public key) must be tested and rejected.
- Refresh token rotation must be tested: valid rotation succeeds, reuse triggers family revocation.
- Revocation must be tested: denylisted `jti` rejected, version bump invalidates all tokens.
- Key rotation must be tested: old `kid` validates during overlap, new `kid` signs new tokens.
- Performance tests must verify p99 latency under load (1000 req/s).
- Security tests must include: token forgery attempts, alg confusion, claim tampering, replay attacks.
- Integration tests must verify full flow: login → use access token → refresh → use new tokens → logout → verify revocation.
- Fuzz testing must run on JWT parsing to detect crashes and memory safety issues.

## 18. Documentation Standards

- Every JWT ADR must include: algorithm choice rationale, claim set, TTL, storage, rotation, revocation strategy.
- Every key rotation event must be logged with old and new `kid`, timestamp, and operator.
- Every JWT library must document the algorithm allowlist and required claims.
- Every runbook must include step-by-step procedure for key compromise, token revocation, emergency rotation.
- Every training material must cover: JWT structure, algorithms, validation rules, common pitfalls.
- Every incident report must include: timeline, impact, root cause, contributing factors, action items.
- Every JWT configuration must be documented in `jwt.config.ts` with rationale per setting.
- Every claim must be documented in `claims.ts` with type, purpose, and validation rule.

## 19. Code Review Checklist

- [ ] JWT library configured with explicit algorithm allowlist; `none` rejected.
- [ ] Verification checks signature, `exp`, `nbf`, `iss`, `aud`; no `decode` without `verify`.
- [ ] Access token TTL ≤ 15 minutes; refresh token TTL ≤ 7 days.
- [ ] Refresh token single-use with reuse detection; reuse triggers family revocation.
- [ ] `jti` is cryptographically random (UUID v4 or 256-bit hex).
- [ ] Signing key from KMS; not hardcoded or in env vars.
- [ ] `kid` header for key rotation; old keys retained for verification.
- [ ] JWT in cookies with `Secure`, `HttpOnly`, `SameSite=Strict`.
- [ ] CSRF protection enabled for cookie-based JWT.
- [ ] Logout bumps `token_version` and adds `jti` to denylist.
- [ ] Password change bumps `token_version`.
- [ ] JWT logged with `jti` only; never full token.
- [ ] Error messages generic; no revelation of which check failed.
- [ ] JWT transmitted over TLS 1.3.
- [ ] Security tests pass: alg confusion, missing claims, expired token, tampered signature.
- [ ] Performance tests pass: p99 verify latency < threshold.
- [ ] Key rotation tested in staging before production.
- [ ] Audit log captures issuance, verification, revocation, rotation, reuse detection.
- [ ] No JWT in URL parameters (logged in access logs).
- [ ] Refresh token storage encrypted at rest.

## 20. Refactoring Checklist

- [ ] Identify all `decode` without `verify`; replace with `verify`.
- [ ] Identify all `algorithms: ['none']` or absent algorithms; set explicit allowlist.
- [ ] Identify all hardcoded secrets; move to KMS.
- [ ] Identify all `localStorage` JWT storage; move to httpOnly cookies.
- [ ] Identify all missing `exp` claims; add with TTL ≤ 15 minutes.
- [ ] Identify all fixed refresh tokens; implement rotation with reuse detection.
- [ ] Identify all missing `jti` claims; add for revocation.
- [ ] Identify all missing CSRF protection on cookie-based JWT; add synchronizer token.
- [ ] Identify all long-lived access tokens (> 15 min); reduce TTL.
- [ ] Identify all weak HMAC secrets (< 256 bits); regenerate with crypto-secure random.
- [ ] Identify all missing key rotation; implement quarterly rotation with `kid`.
- [ ] Re-run security tests after refactoring; verify no new vulnerabilities.

## 21. Deployment Checklist

- [ ] JWT library version pinned; no known vulnerabilities (CVE check).
- [ ] Algorithm allowlist configured; `none` rejected.
- [ ] Signing key in KMS; application has read access.
- [ ] `kid` header configured; key map loaded.
- [ ] Access token TTL ≤ 15 minutes; refresh token TTL ≤ 7 days.
- [ ] Refresh token rotation with reuse detection tested in staging.
- [ ] Denylist (Redis) configured; lookup latency verified.
- [ ] Cookies configured with `Secure`, `HttpOnly`, `SameSite=Strict`.
- [ ] CSRF protection tested; state-changing operations require token.
- [ ] Audit log writer verified; events captured.
- [ ] Security tests pass: alg confusion, missing claims, expired, tampered.
- [ ] Performance tests pass: p99 verify latency < threshold.
- [ ] Key rotation tested in staging; overlap window verified.
- [ ] Error messages verified generic.
- [ ] Rollback plan documented; includes key reversion.
- [ ] On-call engineer briefed on JWT incident runbook.

## 22. Production Checklist

- [ ] JWT library version current; no known vulnerabilities.
- [ ] Algorithm allowlist enforced; `none` rejected.
- [ ] Signing keys in KMS; rotation every 90 days.
- [ ] `kid` header in use; old keys retained for verification.
- [ ] Access token TTL ≤ 15 minutes; refresh token TTL ≤ 7 days.
- [ ] Refresh token rotation with reuse detection active.
- [ ] Denylist (Redis) active; lookup latency < 1 ms.
- [ ] JWT in httpOnly, Secure, SameSite=Strict cookies.
- [ ] CSRF protection on all state-changing endpoints.
- [ ] Audit log centralized; retention ≥ 1 year.
- [ ] Alerts for: alg confusion attempts, reuse detection triggers, key rotation failures, denylist lookup latency spikes.
- [ ] Monitoring: token issuance rate, verification failure rate, refresh rate, revocation rate.
- [ ] Key compromise runbook documented; quarterly tabletop exercise.
- [ ] Security tests run in CI nightly.
- [ ] Penetration test annually; JWT specific tests included.
- [ ] Bug bounty program covers JWT vulnerabilities.

## 23. Logging Strategy

- Every token issuance must be logged: `sub`, `jti`, `iss`, `aud`, TTL, IP, user agent, timestamp.
- Every verification failure must be logged: reason (expired, invalid signature, wrong issuer, wrong audience), `jti` (if extractable), IP, timestamp.
- Every refresh token rotation must be logged: old `jti`, new `jti`, `family_id`, IP, timestamp.
- Every reuse detection must be logged: `family_id`, reused `jti`, IP, timestamp; alert security team.
- Every revocation must be logged: `jti`, reason (logout, password change, compromise), actor, timestamp.
- Every key rotation must be logged: old `kid`, new `kid`, operator, timestamp.
- Every alg confusion attempt must be logged: received `alg`, expected algorithms, IP, timestamp; alert security team.
- JWT must be logged with `jti` only; never log the full token.
- Logs must be shipped to centralized SIEM with retention ≥ 1 year.
- Logs must be tamper-evident; append-only with cryptographic chaining or WORM storage.

## 24. Monitoring Strategy

- Token issuance rate must alert on spikes (> 2× baseline); investigate attack or client bug.
- Verification failure rate must alert on spikes (> 5% of requests); investigate attack or key issue.
- Refresh rate must alert on spikes (> 2× baseline); investigate client bug or attack.
- Reuse detection must alert immediately; security incident response.
- Alg confusion attempts must alert immediately; security incident response.
- Denylist lookup latency must alert at > 5 ms p99; investigate Redis health.
- Key rotation must alert on failure; security incident response.
- Audit log gaps must alert; investigate log pipeline failure.
- Dashboard: token issuance rate, verification success/failure rate, active sessions, refresh rate, revocation rate, key rotation status.
- Monthly report: token volume, security events, key rotation status, penetration test findings.

## 25. Error Handling

- Expired token must return 401 Unauthorized with generic "Token expired"; client refreshes.
- Invalid signature must return 401 Unauthorized with generic "Invalid token"; never reveal signature failure.
- Wrong issuer must return 401 Unauthorized with generic "Invalid token"; never reveal issuer mismatch.
- Wrong audience must return 401 Unauthorized with generic "Invalid token"; never reveal audience mismatch.
- `nbf` in future must return 401 Unauthorized with generic "Token not yet valid".
- Missing required claim must return 401 Unauthorized with generic "Invalid token".
- `alg: none` must return 401 Unauthorized and log security event; alert security team.
- Alg confusion (HS256 with RSA public key) must return 401 Unauthorized and log security event; alert security team.
- Denylist hit must return 401 Unauthorized and log; investigate if reuse pattern.
- Key resolution failure must return 503 Service Unavailable; fail closed, never accept unsigned.

## 26. Examples

### Example 1: JWT Sign and Verify with RS256 (TypeScript)

```typescript
// auth/jwt/jwt.service.ts
import { SignJWT, jwtVerify, JWTVerifyOptions } from 'jose';
import { randomUUID } from 'crypto';
import { KeyManager } from './key-manager';

export interface JwtClaims {
  sub: string;
  aud: string;
  iss: string;
  role: string;
  tenantId: string;
  tokenVersion: number;
}

export class JwtService {
  constructor(
    private readonly keys: KeyManager,
    private readonly issuer = 'https://auth.example.com',
    private readonly audience = 'https://api.example.com',
    private readonly accessTtlSeconds = 900, // 15 minutes
  ) {}

  async signAccessToken(claims: Omit<JwtClaims, 'iss' | 'aud'>): Promise<string> {
    const key = await this.keys.getCurrentSigningKey();
    const now = Math.floor(Date.now() / 1000);
    return new SignJWT({ role: claims.role, tenantId: claims.tenantId, tokenVersion: claims.tokenVersion })
      .setProtectedHeader({ alg: 'RS256', kid: key.kid, typ: 'JWT' })
      .setIssuedAt(now)
      .setSubject(claims.sub)
      .setIssuer(this.issuer)
      .setAudience(this.audience)
      .setExpirationTime(now + this.accessTtlSeconds)
      .setJti(randomUUID())
      .sign(key.privateKey);
  }

  async verifyAccessToken(token: string): Promise<JwtClaims> {
    const unverifiedHeader = JSON.parse(Buffer.from(token.split('.')[0], 'base64url').toString());
    const kid = unverifiedHeader.kid;
    if (!kid) throw new Error('Missing kid header');
    const key = await this.keys.getVerificationKey(kid);
    const options: JWTVerifyOptions = {
      algorithms: ['RS256'],
      issuer: this.issuer,
      audience: this.audience,
    };
    const { payload } = await jwtVerify(token, key.publicKey, options);
    return {
      sub: payload.sub!,
      aud: payload.aud as string,
      iss: payload.iss!,
      role: payload.role as string,
      tenantId: payload.tenantId as string,
      tokenVersion: payload.tokenVersion as number,
    };
  }
}
```

### Example 2: Refresh Token Rotation with Reuse Detection (TypeScript)

```typescript
// auth/jwt/token.repository.ts
import { Redis } from 'ioredis';
import { Pool } from 'pg';

export interface RefreshTokenRecord {
  jti: string;
  familyId: string;
  userId: string;
  hashedToken: string;
  expiresAt: Date;
  used: boolean;
  rotatedFrom: string | null;
}

export class RefreshTokenRepository {
  constructor(
    private readonly pool: Pool,
    private readonly redis: Redis,
  ) {}

  async create(record: RefreshTokenRecord): Promise<void> {
    await this.pool.query(
      `INSERT INTO refresh_tokens (jti, family_id, user_id, hashed_token, expires_at, used, rotated_from)
       VALUES ($1, $2, $3, $4, $5, false, $6)`,
      [record.jti, record.familyId, record.userId, record.hashedToken, record.expiresAt, record.rotatedFrom],
    );
  }

  async consumeAndDetectReuse(jti: string): Promise<{ valid: boolean; familyId: string; userId: string }> {
    const result = await this.pool.query(
      `UPDATE refresh_tokens
          SET used = true, used_at = now()
        WHERE jti = $1 AND used = false
        RETURNING family_id, user_id`,
      [jti],
    );
    if (result.rows.length > 0) {
      return { valid: true, familyId: result.rows[0].family_id, userId: result.rows[0].user_id };
    }

    // Check if token was already used → reuse detected → revoke family
    const checkResult = await this.pool.query(
      `SELECT family_id, user_id FROM refresh_tokens WHERE jti = $1 AND used = true`,
      [jti],
    );
    if (checkResult.rows.length > 0) {
      const familyId = checkResult.rows[0].family_id;
      const userId = checkResult.rows[0].user_id;
      await this.revokeFamily(familyId);
      throw new ReuseDetectedError(`Refresh token reuse detected for family ${familyId}`);
    }
    return { valid: false, familyId: '', userId: '' };
  }

  async revokeFamily(familyId: string): Promise<void> {
    // Mark all tokens in family as used; bump user token_version
    const result = await this.pool.query(
      `UPDATE refresh_tokens SET used = true, revoked_at = now()
        WHERE family_id = $1 AND used = false RETURNING user_id`,
      [familyId],
    );
    if (result.rows.length > 0) {
      const userId = result.rows[0].user_id;
      await this.pool.query(`UPDATE users SET token_version = token_version + 1 WHERE id = $1`, [userId]);
    }
  }

  async addToDenylist(jti: string, ttlSeconds: number): Promise<void> {
    await this.redis.set(`jwt:denylist:${jti}`, '1', 'EX', ttlSeconds);
  }

  async isDenylisted(jti: string): Promise<boolean> {
    const result = await this.redis.get(`jwt:denylist:${jti}`);
    return result !== null;
  }
}

export class ReuseDetectedError extends Error {}
```

### Example 3: JWT Middleware with Full Validation (TypeScript)

```typescript
// auth/middleware/auth.middleware.ts
import { Request, Response, NextFunction } from 'express';
import { JwtService } from '../jwt/jwt.service';
import { RefreshTokenRepository } from '../jwt/token.repository';
import { UserRepository } from '../repositories/user.repository';

export function authMiddleware(
  jwt: JwtService,
  refreshTokens: RefreshTokenRepository,
  users: UserRepository,
) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const authHeader = req.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    const token = authHeader.slice(7);

    try {
      const claims = await jwt.verifyAccessToken(token);

      // Check denylist
      const jti = claims.jti;
      if (jti && await refreshTokens.isDenylisted(jti)) {
        return res.status(401).json({ error: 'Token revoked' });
      }

      // Check token version matches user's current version
      const user = await users.findById(claims.sub);
      if (!user || user.tokenVersion !== claims.tokenVersion) {
        return res.status(401).json({ error: 'Token invalidated' });
      }

      req.user = {
        id: claims.sub,
        role: claims.role,
        tenantId: claims.tenantId,
      };
      next();
    } catch (err) {
      // Generic error; never reveal which check failed
      return res.status(401).json({ error: 'Invalid token' });
    }
  };
}
```

## 27. Common Mistakes

### 27.1 Accepting `alg: none`
**What**: Library configured without explicit algorithm allowlist; attacker sends `alg: none`.
**Why**: Bypasses signature verification; full authentication bypass.
**How to avoid**: Always set `algorithms: ['RS256']` (or other expected); reject `none` always; pin algorithm per issuer.

### 27.2 Storing JWT in localStorage
**What**: `localStorage.setItem('token', jwt)` for SPA access.
**Why**: XSS can read `localStorage`; token theft.
**How to avoid**: Store in httpOnly, Secure, SameSite=Strict cookies; mitigate CSRF with synchronizer token.

### 27.3 `decode` Without `verify`
**What**: `jwt.decode(token)` to read claims without verifying signature.
**Why**: Attacker can forge any token; signature bypass.
**How to avoid**: Always use `jwt.verify(token, key, options)`; never trust `decode` output for auth decisions.

### 27.4 Missing `exp` Claim
**What**: Token without expiration; valid forever.
**Why**: Stolen token valid permanently; no recovery.
**How to avoid**: Always set `exp` with TTL ≤ 15 minutes for access tokens; refresh token for longer sessions.

### 27.5 Weak HMAC Secret
**What**: HS256 with `secret: 'mysecret'` or short string.
**Why**: Brute-forceable offline; attacker forges tokens.
**How to avoid**: Use RS256/ES256/EdDSA; if HS256, secret ≥ 256 bits from crypto-secure random.

### 27.6 Long-Lived Access Tokens
**What**: Access token with TTL = 1 day or more.
**Why**: Long exposure window for stolen tokens; no rotation.
**How to avoid**: Access token TTL ≤ 15 minutes; refresh token (7 days, rotating) for longer sessions.

## 28. Professional Workflow

1. **Receive request**: new auth flow, JWT migration, or vulnerability report.
2. **Threat model**: identify token types, trust boundaries, storage, revocation requirements.
3. **Design**: choose algorithm, claim set, TTLs, storage, rotation, revocation; document in ADR.
4. **Implement**: write sign/verify/rotate/revoke functions; configure library with explicit allowlist.
5. **Peer review**: PR requires second-engineer sign-off; security tests must pass.
6. **Test**: unit tests for all algorithms; security tests for alg confusion, missing claims, expired tokens.
7. **Stage deploy**: verify key rotation overlap; test refresh flow; test revocation.
8. **Pre-deploy checks**: confirm KMS access, denylist Redis, audit log pipeline, on-call briefing.
9. **Production deploy**: monitor verification failure rate; verify no alg confusion attempts succeed.
10. **Post-deploy**: verify key rotation schedule; test emergency rotation runbook.
11. **Post-mortem**: for incidents, write blameless post-mortem within 48 hours; update controls and runbooks.

## 29. Response Style

- Always cite the RFC (RFC 7519, RFC 7515, RFC 7518) when describing JWT behavior.
- Always state the algorithm and key management strategy when proposing JWT code.
- Always provide remediation code alongside vulnerability description.
- Never use the word "should" — use "must" or "must not".
- Always quantify risk using CVSS v3.1 score and impact rating.
- Always recommend defense in depth; never rely on a single control.
- Always link to the relevant OWASP or IETF guidance.
- Always fail closed in examples; never show failing open as acceptable.

## 30. Output Format

- Every code example must be syntactically valid for the stated language and JWT library.
- Every JWT must be presented as a structured object (header, payload, signature) when explaining structure; never as a raw string only.
- Every vulnerability description must include: title, CWE ID, CVSS score, description, proof-of-concept, impact, remediation, references.
- Every ADR must follow: context, decision, status, consequences, alternatives considered.
- Every runbook must be numbered step-by-step with verification commands at each step.
- Every key rotation event must be logged with old and new `kid`, timestamp, operator.
- Every incident report must follow: timeline, impact, root cause, contributing factors, action items with owners and dates.
- Every JWT configuration must be documented with rationale per setting.
- Every training material must include: concept, code example, common mistakes, exercise.
- Every code review comment must include: location, issue, severity, fix suggestion, CWE reference.
