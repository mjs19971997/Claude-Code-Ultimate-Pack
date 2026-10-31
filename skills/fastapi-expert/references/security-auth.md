# Security and Authentication

OAuth2 password flow with JWT, Argon2 password hashing, scopes, API keys, CORS and hardening for FastAPI 0.162.0. Libraries as in the current tutorial: PyJWT 2.15.1 and pwdlib 0.3.1 (Argon2). Protocol theory is in authentication-expert; authorization models in authorization-expert. Snippets run on Python 3.13 (2026-10).

## Contents

1. [Install](#1-install)
2. [Password hashing](#2-password-hashing)
3. [JWT helpers](#3-jwt-helpers)
4. [Login and current user](#4-login-and-current-user)
5. [Scopes and roles](#5-scopes-and-roles)
6. [API keys and bearer tokens](#6-api-keys-and-bearer-tokens)
7. [Token lifecycle](#7-token-lifecycle)
8. [CORS and headers](#8-cors-and-headers)
9. [Hardening checklist](#9-hardening-checklist)

## 1. Install

```bash
pip install pyjwt "pwdlib[argon2]" python-multipart   # python-multipart parses the login form
pip install "pyjwt[crypto]"                           # only for RS256/ES256 keys
```

`fastapi[standard]` already includes `python-multipart`. The tutorial's older recommendations (python-jose, passlib) are superseded by PyJWT and pwdlib; do not start new code on python-jose or passlib.

## 2. Password hashing

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()  # Argon2id with library defaults
DUMMY_HASH = password_hash.hash("dummy-password")


def authenticate(stored_hash: str | None, password: str) -> bool:
    # Always run one verify so unknown users cost the same time as known ones.
    ok = password_hash.verify(password, stored_hash or DUMMY_HASH)
    return ok and stored_hash is not None
```

- Store only the hash string (it embeds algorithm, parameters and salt). Never log or return it; keep it out of every `response_model`.
- Hashing is CPU bound and takes tens of milliseconds by design. Run it from a `def` endpoint or `await anyio.to_thread.run_sync(password_hash.hash, pw)`; calling it directly in `async def` stalls the loop.
- To upgrade parameters later, check the pwdlib docs for `verify_and_update` and rehash on successful login.
- Enforce a minimum length (and a sane maximum such as 128) in the input model; do not impose composition rules without reason.

## 3. JWT helpers

```python
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError

from app.config import Settings


def create_access_token(sub: str, settings: Settings, minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,  # string, unique across the application
        "iat": now,
        "exp": now + timedelta(minutes=minutes or settings.access_token_minutes),
    }
    return jwt.encode(
        claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: Settings) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],  # required by PyJWT; pin it
        options={"require": ["exp", "sub"]},
    )  # raises InvalidTokenError subclasses on any problem
```

- `jwt.decode` without `algorithms=` raises `DecodeError` (verified). Never take the algorithm from the token header and never allow `none`.
- `datetime` values for `exp` and `iat` are converted to timestamps by PyJWT. Use timezone-aware UTC.
- HS256 needs a long random secret (`openssl rand -hex 32`), loaded from settings or a secret manager. If other services verify tokens, use RS256 or ES256 with a private key held only by the issuer and publish the public key (JWKS); add `iss` and `aud` and pass `issuer=` and `audience=` to `decode`.
- Do not put secrets or personal data in the payload: it is signed, not encrypted.
- Catch `InvalidTokenError` (base class) and return one generic 401; do not reveal whether the signature, expiry or format failed.

## 4. Login and current user

```python
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # relative URL of the login route
app = FastAPI()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], settings: SettingsDep) -> Token:
    user = users.get(form.username)  # database lookup in real code
    if not authenticate(user.hash if user else None, form.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(form.username, settings))


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], settings: SettingsDep) -> str:
    try:
        return str(decode_access_token(token, settings)["sub"])
    except InvalidTokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


CurrentUser = Annotated[str, Depends(get_current_user)]
```

- The login endpoint takes form data (`application/x-www-form-urlencoded`), not JSON; that is what Swagger UI's Authorize button sends. The tested example logs in with `client.post("/token", data={...})`.
- After loading the user from the database, check `disabled` / `is_active` in a second dependency (`get_current_active_user`) and return 400 or 403.
- Per-object checks belong in the endpoint or service: `if item.owner != user: raise HTTPException(404)`.
- Login is a good place for rate limiting and lockout (proxy or maintained library); count failures per account and per IP.

## 5. Scopes and roles

```python
from fastapi import Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

oauth2_scopes = OAuth2PasswordBearer(
    tokenUrl="token", scopes={"items:read": "Read items", "items:write": "Create items"}
)


def get_user_with_scopes(
    security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scopes)], settings: SettingsDep
) -> str:
    payload = decode_access_token(token, settings)  # wrap InvalidTokenError as above
    granted = set(str(payload.get("scope", "")).split())
    if not set(security_scopes.scopes) <= granted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions")
    return str(payload["sub"])


@app.get("/items")
def list_items(user: Annotated[str, Security(get_user_with_scopes, scopes=["items:read"])]): ...
```

- `Security(dep, scopes=[...])` is `Depends` plus declared scopes that appear in OpenAPI and reach the dependency through `SecurityScopes`. Issue only the scopes the user is allowed and requested at login (`form.scopes`).
- For simple role models a dependency that checks `user.role` (see `require_admin` in [dependencies-and-lifespan.md](dependencies-and-lifespan.md)) is clearer than scopes.
- Authorization design (RBAC, ABAC, ownership) is covered by authorization-expert.

## 6. API keys and bearer tokens

```python
import hmac

from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Annotated[str | None, Security(api_key_header)], settings: SettingsDep) -> None:
    expected = settings.service_api_key.get_secret_value()
    if key is None or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
```

- Compare secrets with `hmac.compare_digest`. For per-client keys store only a hash of each key and look it up by an identifier prefix.
- `HTTPBearer` extracts a bearer token without the password-flow login URL; use it for tokens issued by an external identity provider, then validate signature, `iss`, `aud` and expiry with the provider's keys (PyJWT's `PyJWKClient` fetches a JWKS).
- API keys belong in headers, not query strings (URLs are logged).

## 7. Token lifecycle

- Keep access tokens short (minutes). Use refresh tokens with rotation stored server side (database or Redis, hashed) so they can be revoked; JWTs alone cannot be revoked before `exp`.
- Deliver browser tokens in `HttpOnly`, `Secure`, `SameSite` cookies when the client is a first-party web app, and add CSRF protection if cookies authenticate state-changing requests. For SPA plus bearer header, keep tokens in memory.
- Rotate signing keys with a `kid` header and accept old keys until their tokens expire.
- Log authentication failures with account identifier and source IP, never the credential.

## 8. CORS and headers

- `CORSMiddleware(allow_origins=[exact origins], allow_methods=[...], allow_headers=[...])`; `allow_credentials=True` only with explicit origins. Browsers block `*` with credentials.
- CORS does not authenticate anything; it only tells browsers which sites may read responses.
- Add security headers at the proxy or in middleware: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, and a restrictive `Content-Security-Policy` for any HTML you serve.
- `TrustedHostMiddleware(allowed_hosts=["api.example.com"])` rejects forged `Host` headers.

## 9. Hardening checklist

- [ ] Secrets only from environment or secret manager; `SecretStr` in settings; none in git, logs or OpenAPI examples.
- [ ] Argon2 hashing off the event loop; unknown-user timing evened out; generic login error text.
- [ ] `jwt.decode` pins `algorithms`, requires `exp` and `sub`; lifetimes short; keys rotated.
- [ ] Every object-level route checks ownership or role; 404 vs 403 chosen deliberately.
- [ ] Output models exclude hashes, tokens and internal flags.
- [ ] Input models forbid extra fields where mass assignment matters (`ConfigDict(extra="forbid")`) and never contain `is_admin`, `owner` or `id`.
- [ ] Upload endpoints bound size, validate content and generate server-side filenames.
- [ ] Docs and OpenAPI disabled or protected on private APIs; `debug=False`.
- [ ] Login and other expensive endpoints rate limited; dependency audit (`pip-audit` or `uv audit`) in CI.
- [ ] TLS terminates at a proxy with `--proxy-headers` and a narrow `--forwarded-allow-ips`.
