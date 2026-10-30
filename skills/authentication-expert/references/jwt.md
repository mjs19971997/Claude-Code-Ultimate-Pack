# JWT: Issuing, Verifying and Revoking

This file covers JSON Web Tokens as used for access tokens, ID tokens and short-lived signed assertions: when to use them, the RFC 8725 and RFC 9068 rules, `jose` (panva, v6) signing and verification, key rotation, revocation and refresh token rotation. Sender-constrained tokens (DPoP, mTLS) are verified as described in [api-security-expert](../../api-security-expert/references/request-signing.md).

## 1. When a JWT is the right tool

- Good: stateless verification by several resource servers, signed assertions between services, ID tokens, short-lived download or action links.
- Poor: browser sessions for a single first-party site (use a server-side session), anything that must be revocable instantly without a lookup, long-lived credentials.
- A JWT is signed (JWS) not encrypted; anyone holding it can read the payload. Do not put secrets, passwords or unnecessary personal data in it. Use JWE only when confidentiality towards the holder is required, and keep JWE and JWS algorithm allowlists separate.

## 2. Claims and header

| Item | Rule |
|---|---|
| `iss` | Exact issuer URL; validate against a configured value |
| `aud` | The API(s) allowed to accept the token; every verifier checks that it appears |
| `sub` | Stable user or client id, unique within `iss`; keep it opaque |
| `exp`, `iat` | Always set; access tokens 5 to 15 minutes; `nbf` optional |
| `jti` | Unique id for revocation lists and replay checks |
| `client_id`, `scope` | Required or expected by the RFC 9068 profile of OAuth access tokens |
| `typ` header | `at+jwt` for access tokens (RFC 9068); `JWT` or a specific value for others, validated by the verifier |
| `kid` header | Selects the verification key from the issuer's JWKS; never used as a file path or query value |

RFC 9068 requires `iss`, `exp`, `aud`, `sub`, `client_id`, `iat` and `jti` in JWT access tokens. A resource server that follows it should also check that `typ` is `at+jwt`, so an ID token cannot be replayed as an access token (the cross-JWT confusion RFC 8725 warns about).

## 3. RFC 8725 rules in practice

- Verify with an explicit algorithm allowlist; do not let the header choose. Never accept `none`.
- Use one algorithm family per key. ES256 and EdDSA are good defaults; RS256 or PS256 where the ecosystem needs RSA (2048-bit minimum). HS256 only when issuer and verifier are the same party and the key is at least 256 random bits; never mix HMAC and public-key algorithms for the same verifier, which enables the "public key as HMAC secret" attack.
- Validate `iss` and `aud` on every token; give each issuer its own validation rules.
- Do not follow `jku`, `x5u` or `jwk` headers supplied by the token to find keys; keys come from configuration or the issuer's metadata (`jwks_uri`) that you pinned.
- Use explicit typing (`typ`) and distinct audiences so one JWT type cannot be accepted as another.
- Reject tokens without `exp`; enforce a small `clockTolerance` (30 seconds or less).
- Treat decoded but unverified content as hostile; `decodeJwt` is for logging and routing only.

## 4. jose v6: sign and verify

`jose` is ESM-first and runs on Node.js, Deno, Bun and browsers. Relevant exports: `SignJWT`, `jwtVerify`, `createRemoteJWKSet`, `createLocalJWKSet`, `generateKeyPair`, `exportJWK`, `importPKCS8`, `importJWK`, `calculateJwkThumbprint`, and the `errors` namespace. `jwtVerify` options include `algorithms`, `issuer`, `audience`, `typ`, `subject`, `clockTolerance`, `maxTokenAge`, `requiredClaims` and `currentDate`. Keys are `CryptoKey`, `KeyObject`, JWK objects or `Uint8Array` for HMAC secrets.

```typescript
import { SignJWT, jwtVerify, createRemoteJWKSet, generateKeyPair, exportJWK, errors, type CryptoKey, type KeyObject } from 'jose';

// Issuer side: asymmetric key, kid, typ, short TTL, no personal data in the payload.
export async function signAccessToken(privateKey: CryptoKey | KeyObject, kid: string, sub: string, clientId: string, scope: string) {
  return new SignJWT({ scope, client_id: clientId })
    .setProtectedHeader({ alg: 'ES256', kid, typ: 'at+jwt' })
    .setIssuer('https://auth.example.com')
    .setAudience('https://api.example.com')
    .setSubject(sub)
    .setIssuedAt()
    .setExpirationTime('10m')
    .setJti(crypto.randomUUID())
    .sign(privateKey);
}

// Resource server side: the key set is fetched, cached and rotated by jose.
const jwks = createRemoteJWKSet(new URL('https://auth.example.com/.well-known/jwks.json'), {
  cooldownDuration: 30_000,
  cacheMaxAge: 600_000,
});

export async function verifyAccessToken(token: string) {
  try {
    const { payload } = await jwtVerify(token, jwks, {
      algorithms: ['ES256'],            // never derive from the token header
      issuer: 'https://auth.example.com',
      audience: 'https://api.example.com',
      typ: 'at+jwt',
      clockTolerance: '30s',
      requiredClaims: ['sub', 'client_id', 'exp', 'iat', 'jti'],
    });
    return payload;
  } catch (e) {
    if (e instanceof errors.JOSEError && !(e instanceof errors.JWKSTimeout)) return null; // expired, bad signature, wrong aud, unknown kid; JWKS timeouts are rethrown
    throw e;
  }
}

export async function newKey() {
  const { publicKey, privateKey } = await generateKeyPair('ES256');
  return { privateKey, publicJwk: { ...(await exportJWK(publicKey)), kid: 'k_2026_10', alg: 'ES256', use: 'sig' } };
}
```

Notes:
- Load the private key once from a secret manager with `importPKCS8(pem, 'ES256')` and keep it in memory; never log it or ship it to the client.
- `createRemoteJWKSet` caches, honours the cooldown between refetches for unknown `kid` values, and picks the key by `kid` and `alg`. Create it once per issuer.
- Catch `errors.JOSEError` subclasses (`JWTExpired`, `JWTClaimValidationFailed`, `JWSSignatureVerificationFailed`, and others) and map them to a single 401; do not return the specific reason to clients.
- HMAC: `jwtVerify(token, new TextEncoder().encode(secret), { algorithms: ['HS256'], ... })` with a secret of at least 32 random bytes from a secret manager.

## 5. Key management and rotation

1. Publish a JWKS (`/.well-known/jwks.json`) with public keys only, each with `kid`, `alg` and `use: "sig"`.
2. Rotate: add the new key to the JWKS, wait until verifiers have refreshed (at least the verifier cache lifetime), start signing with it, keep the old key published until the longest token lifetime has passed, then remove it.
3. Keep one active signing key; verifiers select by `kid`.
4. Emergency rotation: remove the compromised key from the JWKS immediately and accept the outage for tokens signed with it; revoke refresh token families as well.
5. Set `Cache-Control` on the JWKS endpoint so CDNs and verifiers refresh predictably.

## 6. Revocation options

| Option | Latency | Cost |
|---|---|---|
| Short TTL only (5 to 15 minutes) | Up to TTL | None |
| `jti` denylist with TTL equal to remaining lifetime | Immediate | Lookup per request |
| Per-user token version (`ver` claim compared with a stored value) | Immediate | Lookup per request |
| Opaque token and introspection (RFC 7662) | Immediate | Network hop, cacheable for seconds |

Pick short TTL plus refresh token revocation for most systems; add a denylist or version check only for the endpoints where minutes of residual access are unacceptable.

## 7. Refresh tokens with rotation and reuse detection

Make refresh tokens opaque random values (not JWTs), store only their hash, and put them in families. Every use consumes the token and issues a new one; presenting a spent token means theft or a replay, so the whole family is revoked. RFC 9700 requires public clients' refresh tokens to be sender-constrained or rotated.

```typescript
import { createHash, randomBytes } from 'node:crypto';

export interface RefreshRow { familyId: string; userId: string; tokenHash: string; usedAt: Date | null; expiresAt: Date }
export interface RefreshStore {
  /** Atomically marks the row used if and only if it is unused; returns the row or null when it was already used. */
  consume(tokenHash: string): Promise<RefreshRow | null>;
  find(tokenHash: string): Promise<RefreshRow | undefined>;
  insert(row: RefreshRow): Promise<void>;
  revokeFamily(familyId: string): Promise<void>;
}

const sha256 = (v: string) => createHash('sha256').update(v).digest('base64url');
const IDLE_MS = 14 * 24 * 3600_000;

export async function rotate(store: RefreshStore, presented: string) {
  const hash = sha256(presented);
  const row = await store.consume(hash);               // single atomic UPDATE ... WHERE used_at IS NULL
  if (!row) {
    const old = await store.find(hash);
    if (old) await store.revokeFamily(old.familyId);   // reuse of a spent token: kill the whole family
    throw new Error('invalid_grant');
  }
  if (row.expiresAt < new Date()) throw new Error('invalid_grant');
  const next = randomBytes(32).toString('base64url');  // opaque, 256 bits
  await store.insert({ familyId: row.familyId, userId: row.userId, tokenHash: sha256(next), usedAt: null, expiresAt: new Date(Date.now() + IDLE_MS) });
  return { refreshToken: next, userId: row.userId };
}
```

- `consume` must be one atomic statement, for example `UPDATE refresh_tokens SET used_at = now() WHERE token_hash = $1 AND used_at IS NULL RETURNING ...`, so two concurrent requests cannot both succeed.
- Legitimate clients with flaky networks may retry after a lost response. A short grace window (a few seconds) that returns the same successor, or a client retry after re-login, avoids false family revocations; keep it small and documented.
- Keep an absolute lifetime for a family in addition to the idle expiry above, and bind refresh tokens to the client that received them.
- Reauthenticate on family revocation and notify the user.

## 8. Test cases

- Token signed with HS256 using the RSA or EC public key as secret rejected by an ES256-only verifier.
- `alg: none` token with an empty signature rejected.
- Token with the right signature but other `aud`, other `iss`, expired, `nbf` in the future, or missing `typ`.
- ID token presented at the API (wrong `typ` and `aud`).
- Token with `jku`, `x5u` or `jwk` header pointing to attacker keys: key lookup ignores them.
- Unknown `kid` triggers at most one JWKS refetch per cooldown window.
- Rotation: tokens signed with the previous key still verify during the overlap, then fail after removal.
