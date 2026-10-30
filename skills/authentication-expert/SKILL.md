---
name: authentication-expert
description: >-
  Designs and reviews authentication: argon2id password storage, server-side sessions and cookies, JWT issuing and verification with jose, OAuth 2.0 and OpenID Connect clients (PKCE, refresh token rotation), passkeys (WebAuthn), TOTP and other MFA, and account recovery. Use when working on login or signup, session cookies, refresh tokens, JWKS, openid-client, SSO, @simplewebauthn/server, password reset, or MFA enrollment. Not for permissions after login (use authorization-expert), API keys, request signing, DPoP or mTLS verification (use api-security-expert), or general injection and XSS flaws (use secure-coding-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Authentication Expert

This skill covers proving who a user or client is and keeping that proof safe: password storage, sessions, JWTs, OAuth 2.0 and OpenID Connect, passkeys, MFA and account recovery. It merges the former jwt-expert and oauth2-expert skills; their depth lives in the reference files. Deciding what an authenticated principal may do belongs to authorization-expert.

> Verified against jose 6.2, openid-client 6.8, @simplewebauthn/server 14.0, argon2 0.45, otplib 13.5, Express 5 with express-session 1.19, Node.js 22, RFC 9700, RFC 8725, RFC 9068, NIST SP 800-63B-4 and WebAuthn Level 3 (2026-10).

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

- Covered: password policy and hashing, login and recovery flows, cookie sessions, JWT and JWKS handling, OAuth 2.0 and OIDC client and resource-server code, refresh tokens, passkeys, TOTP and backup codes, step-up authentication, enumeration and brute-force resistance.
- Not covered: roles, permissions and policy engines (authorization-expert); HMAC request signing, API keys, DPoP and mTLS verification (api-security-expert); XSS, CSRF mechanics beyond cookie settings, injection (secure-coding-expert). Running your own authorization server is a large product; prefer a maintained server or hosted provider and use this skill for the client and resource-server side.

## 2. Core Expertise

| Mechanism | Best for | Main risk |
|---|---|---|
| Server-side session cookie | First-party web apps | Fixation, CSRF, store availability |
| OAuth 2.0 / OIDC authorization code + PKCE | SSO, third-party login, delegated API access | Redirect and state handling, token storage |
| JWT access token | Stateless verification at several resource servers | Hard revocation, algorithm and audience confusion |
| Opaque token + introspection (RFC 7662) | Immediate revocation, one resource server | Network hop per check |
| Passkey (WebAuthn) | Phishing-resistant primary login or second factor | Recovery path becomes the weak link |
| TOTP (RFC 6238) | Second factor fallback | Phishable, shared secret at rest |
| Password | Legacy and fallback | Reuse, stuffing, weak hashing |

- NIST SP 800-63B-4 (final, 2025): minimum 15 characters when the password is the only factor and 8 when it is one factor of MFA; accept at least 64 characters; allow paste and all printable characters; no composition rules and no scheduled rotation; reject passwords found in breach or common-password lists.
- OAuth: RFC 9700 (Security BCP, January 2025) is the current baseline. OAuth 2.1 is still an IETF Internet-Draft (draft-ietf-oauth-v2-1), not an RFC; treat it as a summary of the same practice: authorization code with PKCE only, exact redirect URI matching, no implicit and no password grant.
- JWT: RFC 8725 is the JWT best current practice; RFC 9068 profiles JWT access tokens (`typ: at+jwt`, required `iss`, `aud`, `sub`, `client_id`, `exp`, `iat`, `jti`).
- WebAuthn Level 3 is the current W3C specification level (check the W3C page for its exact status); passkeys are discoverable (resident) WebAuthn credentials, often synced between a user's devices.

## 3. Workflow

1. List the actors: end users (browser, native, CLI or TV device), service clients, and which resource servers consume the credential.
2. Pick the primary mechanism with the decision rules below; default to a cookie session for a first-party web app and authorization code with PKCE for anything delegated.
3. Define the credential lifecycle: issue, store, rotate, revoke, expire. Write the revocation story before the issuance code.
4. Define the second-factor and recovery paths together. Recovery must not be weaker than the strongest factor it replaces.
5. Implement with the maintained libraries in this skill (`jose`, `openid-client`, `@simplewebauthn/server`, `argon2`); do not hand-roll token parsing, PKCE, or WebAuthn parsing.
6. Add abuse controls: per-account and per-IP rate limits, identical responses for unknown users, breached-password screening.
7. Write negative tests (section 11) before shipping, then run the review checklist.

## 4. Decision Rules

- First-party web app on one site: server-side session in a `__Host-` cookie. Add OIDC only if users sign in through an external IdP.
- SPA or mobile app calling your own API: prefer a backend-for-frontend (BFF) that holds the OAuth tokens and gives the browser a session cookie. Without a BFF, keep access tokens in memory only, never in `localStorage`, and treat any XSS as full account takeover.
- Third-party login and enterprise SSO: OIDC authorization code with PKCE, `state` and `nonce`. The id_token authenticates; an access token only authorizes API calls.
- Machine-to-machine: client credentials with `private_key_jwt` or mTLS client authentication; no user context.
- Input-constrained devices: device authorization grant (RFC 8628).
- Several resource servers verifying locally: JWT access tokens (RFC 9068), 5 to 15 minutes. One resource server needing instant revocation: opaque tokens with introspection.
- Never use the implicit grant or the resource owner password grant. RFC 9700 says the password grant must not be used and the implicit grant should not; OAuth 2.1 drops both.
- Password hashing: Argon2id first; scrypt or bcrypt only where Argon2id is unavailable; never a plain or fast hash.
- Phishing risk matters (admins, finance, developers): require passkeys or hardware keys; keep SMS out of the strong tiers.

## 5. Coding Standards

- Verify tokens with a library using explicit `algorithms`, `issuer`, `audience` and `typ`; never `decode` and trust.
- Compare secrets, MACs, codes and token hashes with `crypto.timingSafeEqual` on equal-length buffers (hash first when lengths may differ).
- Generate tokens, session ids and codes with `crypto.randomBytes` or `crypto.randomUUID`; at least 128 bits (opaque refresh tokens: 256 bits).
- Store only hashes of reset tokens, refresh tokens and backup codes. High-entropy random values need only SHA-256; passwords need Argon2id.
- Return one generic message and status for unknown account and wrong password, and keep timing equal (verify against a dummy hash).
- Key external identities by `(iss, sub)`, never by email; require `email_verified` before linking by email.
- Keep secrets (peppers, signing keys, session secrets, client secrets) in a secret manager, not in code or the user database.
- TypeScript examples target Node.js 22 ESM; load private keys as `CryptoKey` or `KeyObject`, not strings spread through code.

## 6. Project Structure

```
src/auth/
  passwords.ts        # argon2id hash, verify, needsRehash, breach check
  sessions.ts         # session middleware, regenerate, destroy, step-up timestamps
  oidc.ts             # openid-client Configuration, login and callback routes
  tokens.ts           # jose sign and verify, JWKS, refresh rotation
  webauthn.ts         # registration and authentication ceremonies
  mfa.ts              # TOTP, backup codes, step-up policy
  recovery.ts         # reset tokens, account recovery
  rate-limit.ts       # per-account and per-IP limiters
```

## 7. Design Patterns

- **Authenticator interface**: each factor (password, passkey, TOTP, backup code) implements `verify(userId, proof)`; a policy layer decides which combinations satisfy a given assurance level.
- **BFF**: a server component performs the OAuth flow, stores tokens server-side, and proxies API calls with the session cookie. See [references/oauth2-oidc.md](references/oauth2-oidc.md).
- **Refresh token families**: every refresh token belongs to a family; using a spent token revokes the family. See [references/jwt.md](references/jwt.md).
- **Step-up authentication**: store `authTime` and the methods used in the session; sensitive actions (change email, add factor, payout) require a recent strong authentication.
- **Dummy verification**: verify against a precomputed hash when the account is unknown to equalize timing.
- **Separate issuer and verifier**: the verifier needs only the public JWKS; it never holds signing keys.

## 8. Best Practices

- Use passkeys as the preferred primary credential, with a recovery path of equal strength (second passkey, verified recovery codes), and keep passwords as a fallback.
- Regenerate the session id on login, privilege change and MFA completion; destroy it server-side on logout and password change; offer "sign out everywhere".
- Use both an idle timeout and an absolute lifetime for sessions; shorter for sensitive apps.
- Short access tokens (5 to 15 minutes), rotating refresh tokens with reuse detection, and an absolute refresh lifetime.
- Audience-restrict every access token to the API that consumes it; use resource indicators (RFC 8707) when the client talks to several APIs.
- After a password reset or credential compromise: revoke sessions and refresh token families, notify the user through a channel already on file.
- Treat email change, phone change and factor changes as high-risk events: re-authenticate, notify the old address, and delay or confirm.
- Do not put personal data or secrets in JWT payloads; they are signed, not encrypted.

## 9. Performance

- Argon2id cost is deliberate: measure on production hardware and tune memory and iterations to your latency budget rather than copying the minimum. The `argon2` package hashes on the libuv threadpool, so concurrent logins can queue behind each other; size `UV_THREADPOOL_SIZE` accordingly.
- Rate-limit before hashing so attackers cannot use login as a CPU-exhaustion vector.
- `createRemoteJWKSet` caches and refreshes keys itself; create it once at module level, not per request.
- Cache OIDC discovery (`client.discovery` once at startup, refresh on a schedule).
- Local JWT verification avoids a network call per request; introspection results can be cached for a few seconds, which bounds revocation latency.

## 10. Security

- OAuth: authorization code with PKCE (S256) for all clients, confidential ones included; exact string redirect URI matching; unique `state` bound to the browser session; `nonce` bound to the id_token; check the `iss` response parameter (RFC 9207) when a client talks to several authorization servers.
- Public clients cannot hold secrets: refresh tokens for them must be rotated or sender-constrained (DPoP, RFC 9449; verification is covered in [api-security-expert](../api-security-expert/references/request-signing.md)).
- Pushed authorization requests (RFC 9126) keep request parameters off the browser; use them for high-assurance flows.
- JWT (RFC 8725): fixed algorithm allowlist per issuer, reject `alg: none`, validate `iss`, `aud`, `exp`, `typ`, never honour `jku`, `x5u` or embedded `jwk` headers from the token, and keep ID tokens and access tokens non-interchangeable.
- Cookies: `HttpOnly; Secure; SameSite=Lax` (or `Strict`), `__Host-` prefix (no `Domain`, `Path=/`), no tokens in `localStorage` for high-risk apps.
- Enumeration: identical response body, status and timing for login, signup-by-email and reset-request; confirm by email instead of revealing.
- Brute force: per-account and per-IP limits with backoff; avoid hard lockouts that let an attacker lock victims out, prefer throttling plus step-up challenges.
- Reset tokens: random, hashed at rest, 15 to 60 minute expiry, single use, consumed in the same transaction as the password change, and not logged.
- TOTP: store the secret encrypted, reject reuse of an accepted time step, rate-limit attempts.
- WebAuthn: verify the origin and RP ID, use a single-use server-issued challenge, store credential id and public key only, and update the signature counter when it is non-zero.
- Mix-up and CSRF on callbacks: reject callbacks without a matching pending login.

## 11. Testing

- Unknown user and wrong password: same status, body and similar latency.
- Session id changes after login; the old id is rejected; logout invalidates server-side.
- JWT: `alg: none`, HS256 signed with the public key, wrong `iss`, wrong `aud`, expired, missing `typ`, id_token presented as access token: all rejected.
- Refresh: reusing a spent refresh token revokes the family; concurrent refresh calls produce exactly one success.
- OAuth callback: missing or mismatched `state`, replayed `code`, wrong PKCE verifier, unregistered redirect URI (including a prefix match or extra path) rejected.
- Reset: token works once, expires, is invalidated when a newer one is issued.
- WebAuthn: wrong origin, reused challenge and unknown credential id rejected.
- TOTP: the same code twice is rejected; the previous step is accepted, a step two periods old is not.

## 12. Review Checklist

- [ ] Hashing is Argon2id (or documented fallback) with OWASP-minimum parameters or higher, rehash on login
- [ ] No composition or rotation rules; length per NIST SP 800-63B-4; breached-password screening
- [ ] Session cookie flags and `__Host-` prefix; session regenerated on login
- [ ] OIDC: PKCE S256, `state`, `nonce`, exact redirect URIs, users keyed by `(iss, sub)`
- [ ] No implicit or password grant; no tokens in URLs
- [ ] JWT verification pins `algorithms`, `issuer`, `audience`, `typ`; keys come from a JWKS or a configured key
- [ ] Refresh tokens rotate with reuse detection and are stored hashed
- [ ] Login, reset and signup resist enumeration and are rate limited
- [ ] Recovery and MFA changes require step-up and notify the user
- [ ] Secrets and peppers are outside the database and source control

## 13. Production Notes

- Pepper and signing key rotation: publish new keys in the JWKS before using them to sign (`kid`), retire after the longest token lifetime has passed. Version peppers and session secrets (express-session accepts an array of secrets, the first signs).
- A hash upgrade path: `needsRehash` on successful login moves users to new parameters without a migration.
- Behind a reverse proxy, set Express `trust proxy` correctly, otherwise `secure` cookies and client IPs for rate limits are wrong.
- Session store outages lock everyone out: choose a store with replication (Redis or a SQL database) and decide fail-closed behaviour deliberately.
- Plan IdP unavailability: cache discovery and JWKS, keep existing sessions valid, and have a break-glass admin path with its own strong credential.
- Rolling out passkeys: enable as an add-on first, measure fallback use, then make it the default.
- Hosted identity providers (Auth0, Clerk, Cognito, Keycloak, and similar) remove most of this code; check their current docs for session, token and MFA settings, and keep the same verification rules on your resource servers.

## 14. Examples

### Example 1: Argon2id with pepper, dummy verify and rehash

The `secret` option applies the pepper natively in the `argon2` package. Memory is in KiB: 19456 is 19 MiB, the OWASP minimum with 2 iterations and 1 lane; raise it as far as latency allows.

```typescript
import argon2 from 'argon2';
import { randomBytes } from 'node:crypto';

// OWASP minimum for Argon2id: 19 MiB memory, 2 iterations, 1 lane. Raise memoryCost as far as latency allows.
const PARAMS = { type: argon2.argon2id, memoryCost: 19456, timeCost: 2, parallelism: 1 } as const;
const PEPPER = Buffer.from(process.env.PASSWORD_PEPPER ?? '', 'base64'); // from a secret manager, not the database

export const hashPassword = (password: string) => argon2.hash(password, { ...PARAMS, secret: PEPPER });

// Verifying against a dummy digest when the user is unknown keeps timing and the response identical.
const DUMMY_HASH = await argon2.hash(randomBytes(16).toString('hex'), { ...PARAMS, secret: PEPPER });

export interface UserRow { id: string; passwordHash: string }

export async function checkLogin(
  user: UserRow | undefined,
  password: string,
  saveHash: (userId: string, hash: string) => Promise<void>,
): Promise<UserRow | null> {
  const digest = user?.passwordHash ?? DUMMY_HASH;
  const ok = await argon2.verify(digest, password, { secret: PEPPER }).catch(() => false);
  if (!user || !ok) return null;
  if (argon2.needsRehash(user.passwordHash, PARAMS)) {
    await saveHash(user.id, await hashPassword(password));
  }
  return user;
}
```

### Example 2: Cookie session login with fixation protection

```typescript
import express from 'express';
import session from 'express-session';
import { checkLogin, type UserRow } from './password.js';

declare module 'express-session' {
  interface SessionData { userId?: string; authTime?: number }
}

declare const findUserByEmail: (email: string) => Promise<UserRow | undefined>;
declare const updateHash: (id: string, hash: string) => Promise<void>;
declare const store: session.Store; // connect-redis or another server-side store

const app = express();
app.set('trust proxy', 1);
app.use(express.json({ limit: '10kb' }));
app.use(session({
  name: '__Host-sid',                       // __Host- requires Secure, Path=/, no Domain
  secret: process.env.SESSION_SECRET!.split(','), // first entry signs, the rest verify (rotation)
  store,
  resave: false,
  saveUninitialized: false,
  rolling: false,
  cookie: { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 30 * 60 * 1000 },
}));

app.post('/login', async (req, res, next) => {
  const { email, password } = req.body ?? {};
  if (typeof email !== 'string' || typeof password !== 'string' || password.length > 1024) {
    return void res.status(400).json({ error: 'invalid_request' });
  }
  const user = await checkLogin(await findUserByEmail(email.toLowerCase()), password, updateHash);
  if (!user) return void res.status(401).json({ error: 'invalid_credentials' }); // same body for unknown user and wrong password
  req.session.regenerate((err) => {          // new session id on privilege change prevents fixation
    if (err) return next(err);
    req.session.userId = user.id;
    req.session.authTime = Date.now();
    req.session.save((err2) => (err2 ? next(err2) : void res.status(204).end()));
  });
});

app.post('/logout', (req, res, next) => {
  req.session.destroy((err) => {
    if (err) return next(err);
    res.clearCookie('__Host-sid', { httpOnly: true, secure: true, sameSite: 'lax', path: '/' });
    res.status(204).end();
  });
});
```

Cookie-authenticated state-changing routes also need CSRF defence: `SameSite=Lax` plus an `Origin` or `Sec-Fetch-Site` check, or tokens, per secure-coding-expert.

### Example 3: Resource server verifying JWT access tokens

```typescript
import type { RequestHandler } from 'express';
import { createRemoteJWKSet, jwtVerify, errors, type JWTPayload } from 'jose';

const jwks = createRemoteJWKSet(new URL('https://auth.example.com/.well-known/jwks.json'));

declare global { namespace Express { interface Request { token?: JWTPayload } } }

export const requireBearer: RequestHandler = async (req, res, next) => {
  const m = /^Bearer ([A-Za-z0-9._~+/-]+=*)$/.exec(req.headers.authorization ?? '');
  if (!m) return void res.set('WWW-Authenticate', 'Bearer').status(401).end();
  try {
    const { payload } = await jwtVerify(m[1], jwks, {
      algorithms: ['ES256'],                       // explicit allowlist; `none` and HS* are never accepted
      issuer: 'https://auth.example.com',
      audience: 'https://api.example.com',         // this API, not just any token from the issuer
      typ: 'at+jwt',                               // RFC 9068; blocks id_tokens used as access tokens
      requiredClaims: ['sub', 'exp', 'jti'],
    });
    req.token = payload;
    next();
  } catch (e) {
    if (e instanceof errors.JOSEError && !(e instanceof errors.JWKSTimeout)) return void res.set('WWW-Authenticate', 'Bearer error="invalid_token"').status(401).end();
    next(e);                                       // JWKS fetch failure etc. is a 5xx, not a 401
  }
};
```

Signing, JWKS publishing, rotation and refresh tokens are in [references/jwt.md](references/jwt.md); the OIDC login client is in [references/oauth2-oidc.md](references/oauth2-oidc.md).

## 15. Common Mistakes

- Accepting `alg: none`, or letting the token header pick the algorithm. Pin `algorithms`.
- Using `jwt.decode` (or reading the payload) and trusting it. Verify the signature first.
- Skipping `audience`: a token minted for another API from the same issuer is accepted.
- Treating an OAuth access token as proof of login. Use the OIDC id_token, validated for `aud`, `nonce` and signature.
- Registering redirect URI patterns or prefixes; match exact strings.
- Missing PKCE because the client is "confidential", or `state` that is not bound to the user's browser.
- Tokens in `localStorage` for high-risk apps; use a BFF with a `__Host-` cookie.
- Not regenerating the session id at login (fixation), or keeping sessions alive after password change.
- Different messages or timing for unknown user versus wrong password; reset forms that confirm an address exists.
- Refresh tokens that never rotate, are stored in plaintext, or have no absolute lifetime.
- Forced periodic password changes and composition rules; they contradict NIST SP 800-63B-4 and weaken real passwords.
- Hard lockout after N failures, turning login into a denial-of-service lever.
- SMS as the only strong factor, or account recovery by email alone for accounts protected by passkeys.
- Logging passwords, tokens, reset links or full Authorization headers.

## 16. References

- [references/jwt.md](references/jwt.md): JWT structure, RFC 8725 and RFC 9068 rules, jose signing and verification, JWKS rotation, revocation, refresh token rotation with reuse detection.
- [references/oauth2-oidc.md](references/oauth2-oidc.md): grant selection, authorization code with PKCE, OIDC login with openid-client, PAR, device flow, introspection and revocation, BFF, OAuth 2.1 status.
- [references/sessions-and-passwords.md](references/sessions-and-passwords.md): cookie and session lifecycle, CSRF basics, password policy, breached-password checks, reset and recovery flows, rate limiting.
- [references/passkeys-and-mfa.md](references/passkeys-and-mfa.md): WebAuthn registration and authentication with @simplewebauthn/server, passkey rollout, TOTP, backup codes, step-up.
- Related: [../api-security-expert/references/request-signing.md](../api-security-expert/references/request-signing.md) for DPoP and mTLS verification.
- Official: https://www.rfc-editor.org/rfc/rfc9700, https://www.rfc-editor.org/rfc/rfc8725, https://pages.nist.gov/800-63-4/sp800-63b.html, https://www.w3.org/TR/webauthn-3/, https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html, https://github.com/panva/jose
