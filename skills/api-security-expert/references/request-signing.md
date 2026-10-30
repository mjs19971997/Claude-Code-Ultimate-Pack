# Request Signing, API Keys and Sender-Constrained Tokens

This file covers proving who sent a request and that it was not altered or replayed: HMAC signing between your own parties, API key handling, mTLS, and tokens bound to the caller's key. Provider webhooks (Stripe-style `t=...,v1=...`) follow the provider's documented format; see Example 3 in SKILL.md. Examples use Express 5, ioredis and jose 6 on Node.js 22 or later.

## 1. Choosing a mechanism

| Need | Mechanism |
|---|---|
| Server-to-server calls, caller cannot hold a client certificate | HMAC-signed requests (section 2) |
| Service-to-service inside infrastructure you control | mTLS (section 4), often through a mesh |
| Public clients or user-delegated calls where a stolen bearer token is the risk | DPoP (RFC 9449) or mTLS-bound tokens (RFC 8705), section 5 |
| Interoperable signatures across proxies and vendors | HTTP Message Signatures (RFC 9421), section 6 |
| Identifying a calling application, low sensitivity | API key (section 3) over TLS |

A signature proves integrity and the holder of the secret; it does not authorize anything. Map the key id to a client and tenant, then authorize as usual.

## 2. HMAC request signing

**Canonical string.** Both sides must build byte-identical input. Use a fixed field order, one field per line, a version prefix, and reject any field that contains a newline.

```
v1
POST
/v1/payments
a=1&b=2
k_2026_10
1761840000
Zk3q0w9XlQ2m8TnR5aVbCg
<hex sha256 of the raw body>
```

Fields: version, upper-case method, URL path as received (not decoded twice), query pairs sorted by key then value and percent-encoded the same way on both sides, key id, Unix timestamp, nonce, SHA-256 hex of the raw body (the empty string hash for no body). Include `Host` if the same secret is valid for several hosts. Pitfalls: a proxy that rewrites the path or reorders the query, signing `req.url` inside a mounted router (use `req.originalUrl`), and hashing a re-serialized JSON body instead of the raw bytes.

**Verification order.** Cheap structural checks, timestamp window, key lookup, signature compare, then the nonce write. Writing the nonce only after the signature is valid keeps attackers from filling the cache.

```typescript
import { createHash, createHmac, timingSafeEqual } from 'node:crypto';
import express, { type RequestHandler } from 'express';
import type { Redis } from 'ioredis';

const WINDOW_S = 300;
export interface SigningKey { id: string; secret: Buffer; status: 'active' | 'retiring' | 'revoked'; clientId: string }

export function canonicalString(p: { method: string; path: string; query: URLSearchParams; keyId: string; ts: string; nonce: string; body: Buffer }): string {
  const query = [...p.query.entries()]
    .sort(([a, av], [b, bv]) => (a === b ? av.localeCompare(bv) : a.localeCompare(b)))
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
  const bodyHash = createHash('sha256').update(p.body).digest('hex');
  return ['v1', p.method.toUpperCase(), p.path, query, p.keyId, p.ts, p.nonce, bodyHash].join('\n');
}
export const sign = (secret: Buffer, canonical: string): string => createHmac('sha256', secret).update(canonical).digest('hex');

export function verifySigned(lookup: (id: string) => Promise<SigningKey | null>, redis: Redis): RequestHandler[] {
  const verify: RequestHandler = async (req, res, next) => {
    const keyId = req.get('x-key-id') ?? '', ts = req.get('x-timestamp') ?? '', nonce = req.get('x-nonce') ?? '', sig = req.get('x-signature') ?? '';
    const reject = (): void => { res.status(401).json({ error: 'invalid_signature' }); };  // one generic error
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(keyId) || !/^\d{10}$/.test(ts) || !/^[A-Za-z0-9_-]{16,64}$/.test(nonce) || !/^[0-9a-f]{64}$/.test(sig)) return reject();
    if (Math.abs(Date.now() / 1000 - Number(ts)) > WINDOW_S) return reject();
    const key = await lookup(keyId);
    if (!key || key.status === 'revoked') return reject();

    const url = new URL(req.originalUrl, 'http://placeholder');
    const expected = Buffer.from(sign(key.secret, canonicalString({
      method: req.method, path: url.pathname, query: url.searchParams, keyId, ts, nonce,
      body: Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0),
    })), 'hex');
    const received = Buffer.from(sig, 'hex');
    if (expected.length !== received.length || !timingSafeEqual(expected, received)) return reject();

    // SET ... EX ... NX returns null if the nonce already exists. TTL covers the whole acceptance window.
    if ((await redis.set(`nonce:${key.id}:${nonce}`, '1', 'EX', 2 * WINDOW_S, 'NX')) !== 'OK') return reject();
    res.locals.clientId = key.clientId;
    next();
  };
  return [express.raw({ type: '*/*', limit: '1mb' }), verify];   // raw bytes, never a parsed-then-reserialized body
}
```

- `timingSafeEqual` throws when buffer lengths differ, so compare lengths first (after decoding hex) and never compare hex strings with `===`.
- **Replay window**: reject timestamps outside plus or minus `WINDOW_S`. A request stamped at `now + WINDOW_S` stays acceptable until `now + 2 * WINDOW_S`, so the nonce TTL must be at least twice the window. Keep the window short (a few minutes) and keep server clocks synced (NTP).
- **Nonce scope**: key the cache by key id plus nonce, so one client cannot burn another's nonces. Equivalent Redis command: `SET nonce:<kid>:<nonce> 1 NX EX 600`.
- If Redis is unreachable, fail closed for sensitive routes; failing open turns the window back into a replay opportunity.
- Retried client requests need a fresh nonce and timestamp; pair signing with an idempotency key so a retry does not repeat the effect.
- Signing does not hide the body; TLS is still required.

## 3. Key rotation and API key lifecycle

**Key ids.** Every signing secret has a public id (`kid`) sent with each request, so the server can hold several secrets per client. Rotation: create the new key, let the client switch, mark the old key `retiring` (still accepted, flagged in metrics), then `revoked` after the last use disappears. Give each key an expiry and a last-used timestamp; alert on use of a retiring key after its deadline. Secrets come from a CSPRNG (`randomBytes(32)`) and live in a secret manager, not in the repository or the signed client bundle.

**API key format and storage.**

```
sk_live_<id>_<secret>      e.g. sk_live_7Hq2mXpA_Vd3k...43 base64url chars from randomBytes(32)
```

- The prefix names the environment and key type, which lets secret scanners and humans recognize a leaked key; the `<id>` is a short random public lookup value.
- Store `id`, the environment, the owner, scopes, created, expires and last-used, plus a hash of the secret. For 256-bit random secrets a fast hash is sufficient: `SHA-256(secret)`, or `HMAC-SHA256(serverPepper, secret)` if you want a database leak alone to be useless. Slow password hashes are not needed for high-entropy secrets and make every request expensive.
- Look up by `id`, hash the presented secret, compare with `timingSafeEqual`. Do not run a database query by the secret itself.
- Show the full key once at creation; afterwards show only the prefix and the last four characters.
- Send keys in a header (`Authorization` or `X-API-Key`), never in the URL, where they land in logs and referrers.
- Offer several keys per client, scopes per key, immediate revocation, and an audit trail of creation and revocation. Scope keys to one tenant.
- An API key identifies an application. User-level access needs a user credential (authentication-expert).

## 4. mTLS basics

In mutual TLS the server also requests and verifies a client certificate during the handshake, so the connection itself carries a verified identity.

- Run a private CA per environment. Issue short-lived client certificates (hours to days) and automate renewal; short lifetimes replace most revocation plumbing. Put the identity in the Subject Alternative Name (a URI or DNS name) and authorize on that, not on the common name.
- Node terminating TLS itself: `https.createServer({ key, cert, ca, requestCert: true, rejectUnauthorized: true }, app)`; then `req.socket.authorized` is true for a verified certificate and `req.socket.getPeerCertificate()` returns it. Do not set `rejectUnauthorized: false` and rely on a header or later check.
- When a proxy or mesh sidecar terminates TLS, the app sees only what the proxy forwards. Accept an identity header (for example the client certificate subject or SAN) only on the internal listener, make the proxy overwrite it, and strip it from external traffic. Proxy settings: nginx-expert, kubernetes-expert.
- mTLS authenticates the peer, not each request or user; combine it with authorization checks on the mapped identity.
- Outbound calls: pin the CA you expect (`ca` option) rather than disabling verification.

## 5. Sender-constrained tokens

A bearer token works for whoever holds it. A sender-constrained token also requires proof of a key, so a stolen token alone is useless.

**DPoP (RFC 9449).** The client generates a key pair and sends a `DPoP` header on each request: a JWT with header `typ: dpop+jwt` and the public `jwk`, and claims `htm` (HTTP method), `htu` (URL without query and fragment), `iat`, a unique `jti`, and `ath` (base64url SHA-256 of the access token) when presenting a token. The authorization server binds the access token to the key's JWK thumbprint (RFC 7638) in `cnf.jkt`, and the client sends `Authorization: DPoP <token>`. Servers may require a server-issued nonce (`DPoP-Nonce` header) to bound proof lifetime.

```typescript
import { createHash } from 'node:crypto';
import { EmbeddedJWK, calculateJwkThumbprint, jwtVerify } from 'jose';

// `cnfJkt` is cnf.jkt from the already verified access token; `seenJti` returns false for a repeat.
export async function verifyDpop(o: {
  proof: string; accessToken: string; cnfJkt: string; method: string; url: string;
  seenJti: (jti: string, ttlSeconds: number) => Promise<boolean>;
}): Promise<void> {
  const { payload, protectedHeader } = await jwtVerify(o.proof, EmbeddedJWK, {
    typ: 'dpop+jwt', algorithms: ['ES256'], maxTokenAge: '60s', requiredClaims: ['jti', 'iat', 'htm', 'htu', 'ath'],
  });
  const ath = createHash('sha256').update(o.accessToken).digest('base64url');
  if (payload.htm !== o.method || payload.htu !== o.url) throw new Error('htm/htu mismatch');  // o.url: scheme, host, path only
  if (payload.ath !== ath) throw new Error('ath mismatch');
  if ((await calculateJwkThumbprint(protectedHeader.jwk!)) !== o.cnfJkt) throw new Error('key not bound to token');
  if (!(await o.seenJti(String(payload.jti), 120))) throw new Error('replayed proof');
}
```

Build `url` from the externally visible scheme and host (set `trust proxy` correctly), not from the internal address. Accept only the algorithms you intend, and never accept a `jwk` that contains a private key.

**mTLS-bound tokens (RFC 8705).** The authorization server puts the SHA-256 thumbprint of the client certificate in `cnf` as `x5t#S256`. The resource server compares it with the certificate on the TLS connection that carried the request. This suits confidential clients that already run mTLS; browsers and SPAs generally cannot use it, which is where DPoP fits.

Issuing these tokens and the OAuth flows belong to authentication-expert; here the resource server only verifies the binding.

## 6. HTTP Message Signatures (RFC 9421)

RFC 9421 standardizes signing selected components of an HTTP message with the `Signature-Input` and `Signature` header fields: components such as `@method`, `@target-uri`, `@authority` and `content-digest`, plus parameters like `created`, `expires`, `nonce`, `keyid` and `alg`. Use `Content-Digest` (RFC 9530) to cover the body. Reasons to prefer it over a custom canonical string: interoperability with vendors and gateways, a defined component grammar, and support for asymmetric algorithms (so the verifier holds no secret).

- The signature base is built from the exact serialization rules of the RFC; hand-rolled approximations fail at the edges (multiple header values, structured field encoding). Use a maintained library and check it against the test vectors in RFC 9421.
- The RFC defines the mechanism, not a replay policy: require `created` or `expires`, a `nonce` for sensitive calls, and apply the same window and nonce cache as in section 2.
- Verifiers should require the signature to cover method, target URI and `content-digest` for requests with a body; a signature that covers only a header is easy to replay against other requests.
- Algorithm and key choice come from the verifier's configuration for the `keyid`, not from the `alg` the sender claims.

## 7. Test cases

- Valid signature accepted; same request replayed rejected; same body with a new nonce but the old signature rejected.
- Altered body, query order changed, different method, different path, wrong key id: all rejected.
- Timestamp at plus and minus `WINDOW_S` plus one second rejected; clock skew within the window accepted.
- Revoked key rejected immediately; retiring key accepted and counted.
- Hex signature of the wrong length rejected without throwing.
- DPoP: wrong `htm`, wrong `htu`, wrong `ath`, proof signed by another key, reused `jti`, expired `iat` all rejected.
