# OAuth 2.0 and OpenID Connect

This file covers choosing grants, writing a correct authorization code with PKCE client using `openid-client` v6, the extensions that matter (PAR, device flow, introspection, revocation), the BFF pattern, and the status of OAuth 2.1. JWT details are in [jwt.md](jwt.md); DPoP and mTLS-bound token verification are in [api-security-expert](../../api-security-expert/references/request-signing.md).

## 1. Standards map

| Standard | Use |
|---|---|
| RFC 6749 / RFC 6750 | OAuth 2.0 framework and bearer token usage |
| RFC 9700 (BCP 240, January 2025) | Current security best practice for OAuth 2.0 |
| RFC 7636 | PKCE (`code_challenge_method=S256`) |
| RFC 9207 | `iss` parameter in authorization responses (mix-up defence) |
| RFC 9126 | Pushed Authorization Requests (PAR) |
| RFC 9101 / RFC 9396 | JWT-secured authorization requests / Rich Authorization Requests |
| RFC 8707 | Resource indicators (`resource` parameter, audience restriction) |
| RFC 9068 | JWT profile for access tokens |
| RFC 9449 | DPoP sender-constrained tokens |
| RFC 8705 | mTLS client authentication and certificate-bound tokens |
| RFC 8628 | Device authorization grant |
| RFC 7009 / RFC 7662 | Token revocation / introspection |
| RFC 8693 | Token exchange |
| RFC 8414 | Authorization server metadata (`/.well-known/oauth-authorization-server`) |
| OpenID Connect Core 1.0 and Discovery 1.0 | Authentication layer, id_token, `/.well-known/openid-configuration` |

OAuth 2.1 (draft-ietf-oauth-v2-1) is still an Internet-Draft at the time of writing; check the IETF datatracker for the current revision. It consolidates RFC 6749, 6750 and the BCP: PKCE required for the authorization code flow, exact redirect URI matching, no implicit grant, no resource owner password grant, no bearer tokens in query strings, refresh tokens for public clients sender-constrained or one-time. Implement to RFC 9700 and these rules now; do not cite OAuth 2.1 as a standard.

## 2. Choosing a grant

| Situation | Grant |
|---|---|
| Browser or native app with a user | Authorization code + PKCE (+ PAR for high assurance) |
| Backend service, no user | Client credentials with `private_key_jwt` or mTLS client auth |
| TV, CLI, device without a browser | Device authorization (RFC 8628) |
| Service acting on behalf of a user towards another API | Token exchange (RFC 8693) |
| Renewing access | Refresh token grant (rotated) |
| Implicit (`response_type=token`), password (ROPC) | Do not use |

Native apps use the system browser (RFC 8252) with claimed HTTPS redirect URIs or loopback redirects; embedded web views defeat SSO and expose credentials.

## 3. Authorization code with PKCE and OIDC login

Rules enforced by the code below and by RFC 9700:
- `code_verifier` generated per login, `code_challenge_method=S256`; the verifier lives in the server-side session, never in the URL.
- `state` is a random value stored in the session and compared on the callback (it also provides CSRF protection); `nonce` is stored the same way and is compared with the id_token claim by the library.
- The redirect URI is registered exactly and sent exactly; no wildcards, no prefix matching, no open redirectors on the client.
- The id_token is validated (signature, `iss`, `aud`, `exp`, `nonce`) and the user is keyed by `(iss, sub)`.
- The session id is regenerated after the callback succeeds.

```typescript
import * as client from 'openid-client';
import express from 'express';
import session from 'express-session';

declare module 'express-session' {
  interface SessionData { oidc?: { state: string; nonce: string; verifier: string }; userId?: string }
}

const config = await client.discovery(
  new URL('https://idp.example.com'),
  process.env.OIDC_CLIENT_ID!,
  process.env.OIDC_CLIENT_SECRET,   // confidential client; omit and pass client.None() for a public client
);
const redirectUri = 'https://app.example.com/auth/callback';

export const router = express.Router();

router.get('/auth/login', async (req, res) => {
  const verifier = client.randomPKCECodeVerifier();
  const state = client.randomState();
  const nonce = client.randomNonce();
  req.session.oidc = { state, nonce, verifier };
  const url = client.buildAuthorizationUrl(config, {
    redirect_uri: redirectUri,
    scope: 'openid profile email',
    code_challenge: await client.calculatePKCECodeChallenge(verifier),
    code_challenge_method: 'S256',
    state,
    nonce,
  });
  res.redirect(url.href);
});

router.get('/auth/callback', async (req, res, next) => {
  const saved = req.session.oidc;
  delete req.session.oidc;                       // single use
  if (!saved) return void res.status(400).send('no login in progress');
  try {
    const current = new URL(req.originalUrl, 'https://app.example.com');
    const tokens = await client.authorizationCodeGrant(config, current, {
      pkceCodeVerifier: saved.verifier,
      expectedState: saved.state,
      expectedNonce: saved.nonce,
      idTokenExpected: true,
    });
    const claims = tokens.claims()!;             // id_token already verified: signature, iss, aud, exp, nonce
    req.session.regenerate((err) => {
      if (err) return next(err);
      req.session.userId = `${claims.iss}|${claims.sub}`; // key users by (iss, sub), never by email
      req.session.save(() => res.redirect('/'));
    });
  } catch (e) {
    next(e);
  }
});
```

`client.discovery` loads metadata and the JWKS URI. `authorizationCodeGrant` takes the full callback URL, so it validates the callback parameters (`state`, `code`, error responses) in one place. For public clients (native, SPA without a BFF) pass `client.None()` as the client authentication argument. With `idTokenExpected: true` a response without an id_token is rejected. openid-client v6 requires HTTPS by default; `allowInsecureRequests` exists for local development only and must not ship.

Scopes: request the minimum. `openid` yields an id_token; `offline_access` requests a refresh token on most providers. `email_verified` must be true before treating an email as proof of ownership. Linking a federated login to an existing local account by email is an account-takeover vector when the IdP does not verify email; require the local account holder to authenticate first.

## 4. PAR, introspection, revocation, device flow

```typescript
import * as client from 'openid-client';

declare const config: client.Configuration;

export async function startWithPar(verifier: string, state: string, nonce: string) {
  return client.buildAuthorizationUrlWithPAR(config, {
    redirect_uri: 'https://app.example.com/auth/callback',
    scope: 'openid',
    code_challenge: await client.calculatePKCECodeChallenge(verifier),
    code_challenge_method: 'S256',
    state, nonce,
  });
}

export async function introspect(token: string) {
  const r = await client.tokenIntrospection(config, token);
  return r.active === true;
}
export const revoke = (token: string) => client.tokenRevocation(config, token, { token_type_hint: 'refresh_token' });

export async function deviceFlow() {
  const d = await client.initiateDeviceAuthorization(config, { scope: 'openid offline_access' });
  console.log(`Open ${d.verification_uri} and enter ${d.user_code}`);
  return client.pollDeviceAuthorizationGrant(config, d);
}
```

- PAR (RFC 9126) sends the authorization parameters over a back channel and returns a `request_uri`, so they cannot be tampered with in the browser and long URLs are avoided. Some servers require it; the `buildAuthorizationUrlWithPAR` helper handles the push.
- Introspection (RFC 7662) lets a resource server ask the authorization server whether an opaque token is active; the caller authenticates itself. Cache for seconds, not minutes.
- Revocation (RFC 7009) of a refresh token should also end the grant on the server side; call it on logout.
- Device flow (RFC 8628): display `verification_uri` and `user_code`, poll at the interval returned, and stop on `expired_token` or `access_denied`. The user code needs rate limiting on the authorization server because it is short.

## 5. Backend for frontend (BFF)

For browser apps with sensitive data, the BFF is the confidential OAuth client: it runs the code flow above, keeps access and refresh tokens server-side, issues the browser only a `__Host-` session cookie, attaches the access token when proxying API calls, and refreshes tokens itself. Benefits: tokens are out of reach of XSS, refresh rotation is handled in one place, and the SPA needs no OAuth library. Costs: a stateful component and CSRF defence for cookie-authenticated routes (`SameSite`, `Origin` checks, and a custom header requirement). A SPA with no BFF must keep tokens in memory, use short TTLs and rotating refresh tokens, and accept the XSS exposure.

## 6. Resource server behaviour

- Verify JWT access tokens per [jwt.md](jwt.md), or introspect opaque ones.
- Check `aud` against this API, `scope` against the route, and `client_id` against the expected clients where it matters.
- Return `401` with `WWW-Authenticate: Bearer` and `error="invalid_token"` for bad tokens, `403` with `insufficient_scope` for missing scopes.
- Accept tokens only in the `Authorization` header, never in query strings.
- Token exchange and delegated calls: send the access token only to the API it was issued for (RFC 8707 audience), never forward it to third parties.

## 7. If you must build an authorization server

Prefer a maintained server or hosted product. If building, the minimum set from RFC 9700: exact redirect URI comparison, PKCE enforcement, single-use short-lived authorization codes (reuse of a code should revoke tokens already issued from it), refresh token rotation or sender-constraint, `iss` in responses, audience-restricted tokens, client authentication with `private_key_jwt` or mTLS for confidential clients, consent screens that name the client and scopes, and rate limits on the token and device endpoints. For Node.js, `node-oidc-provider` (panva) is a certified OIDC provider library; check its current docs for configuration.

## 8. Test cases

- Callback with wrong or missing `state`, with a reused `code`, with a wrong PKCE verifier, or with a different `iss`: rejected.
- Authorization request with an unregistered redirect URI, a registered one plus a suffix, or a different scheme: rejected by the server.
- id_token with wrong `aud`, wrong `nonce`, expired, or signed with an unexpected algorithm: rejected by the client.
- Refresh token reuse revokes the grant (see [jwt.md](jwt.md)).
- A token issued for API A is rejected by API B.
- Login CSRF: attacker-initiated callback with the attacker's `code` and no matching session state is rejected.
