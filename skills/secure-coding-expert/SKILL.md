---
name: secure-coding-expert
description: >-
  Writes, reviews and fixes application code in TypeScript, Python, Go and Java so it resists injection, XSS, path traversal, SSRF, insecure deserialization, weak cryptography and secret leaks, and maps findings to the OWASP Top 10:2025 (including OWASP Top 10 audits, threat modeling and SAST/SCA setup). Use when reviewing code for vulnerabilities, validating input, encoding output, building SQL or shell calls, handling file uploads or user-supplied URLs, hashing passwords, generating tokens, storing secrets, setting security headers, or running an OWASP Top 10 review. Not for API-specific controls such as BOLA, rate limits, webhooks or GraphQL limits (use api-security-expert), login, sessions, JWT or OAuth flows (use authentication-expert), or permission models and tenant isolation (use authorization-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Secure Coding Expert

This skill covers code-level defenses: how untrusted data enters a program, which sinks it can reach, and the canonical defense for each sink. It also covers OWASP Top 10:2025 reviews, threat modeling and the SAST/SCA/secret-scanning pipeline that keeps those defenses in place. It does not cover API-specific controls, the design of login and token flows, or permission models; those live in the sibling security skills.

> Verified against OWASP Top 10:2025, OWASP Password Storage and SSRF Prevention Cheat Sheets, Go standard library `net`, `net/http` and `net/netip`, Python 3 `pathlib`, Zod 4 and node `argon2` (2026-10).

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

- Covered: input validation, output encoding, SQL/NoSQL/OS/template injection, XSS, path traversal, SSRF, file uploads, deserialization, cryptography choices, randomness, secrets handling, security headers, cookies, error handling that does not leak, dependency and supply-chain hygiene, OWASP Top 10:2025 reviews.
- Languages: TypeScript/Node.js, Python, Go, Java. The rules are language-neutral; the examples name the concrete API.
- Not covered here: object- and function-level authorization in APIs, rate limiting, webhook signing, GraphQL cost limits (api-security-expert); password login, MFA, passkeys, sessions, JWT, OAuth 2.0/OIDC (authentication-expert); RBAC/ABAC/ReBAC, policy engines, Row-Level Security (authorization-expert).

## 2. Core Expertise

- **Trust boundaries and sinks**: HTTP bodies, headers, query strings, cookies, uploaded files, webhooks, queue messages, third-party API responses and LLM output are all untrusted. Sinks: SQL, NoSQL operators, shell, file system, HTML/JS/URL/CSS contexts, outbound HTTP, deserializers, template engines, log lines, redirects.
- **Validation**: allowlist schemas at the boundary (Zod, Pydantic, Joi, go-playground/validator, Jakarta Bean Validation); reject unknown fields; bound sizes, lengths and counts; parse into typed values once and pass the typed value on.
- **Output encoding**: auto-escaping templates (React JSX, Jinja2 autoescape, Go `html/template`, Thymeleaf); DOMPurify when raw HTML must be rendered; `encodeURIComponent` for URL parts; never build HTML, JS or CSS by string concatenation.
- **Injection**: parameterized queries (`$1` in pg, `%s` placeholders in psycopg, `?` in JDBC `PreparedStatement`); ORMs with their raw-SQL escape hatches reviewed; NoSQL operator injection (`{"$ne": null}`) blocked by schema typing; `execFile`/`subprocess.run([...])`/`exec.Command` with argument arrays, never a shell string.
- **Path traversal**: never use user input as a path component without validation; resolve the final path and check containment (`Path.is_relative_to`, `filepath.Rel`/`os.Root` in Go, `Path.normalize().startsWith()` in Java); prefer server-generated names.
- **SSRF**: allowlist destinations; resolve DNS and check the IP that is actually dialled (DNS rebinding); disable or re-check redirects; block private, loopback, link-local (cloud metadata `169.254.169.254`, `fd00:ec2::254`), CGNAT and unspecified ranges; no proxy from environment variables.
- **Deserialization**: JSON or Protobuf for untrusted data; never `pickle`, `yaml.load` without `SafeLoader`, Java `ObjectInputStream`, PHP `unserialize`, or .NET `BinaryFormatter` on untrusted input.
- **Cryptography**: AES-256-GCM or ChaCha20-Poly1305 through a vetted library (libsodium, Tink, platform crypto); TLS 1.2 minimum, TLS 1.3 preferred; no home-made crypto, no ECB, no static IVs.
- **Randomness**: `crypto.randomBytes`/`crypto.randomUUID` (Node), `secrets` (Python), `crypto/rand` (Go), `SecureRandom` (Java). Never `Math.random`, `random`, `math/rand` for anything secret.
- **Password storage** (detail in authentication-expert): Argon2id with at least m=19 MiB, t=2, p=1 (OWASP minimum); scrypt N=2^17, r=8, p=1; bcrypt cost of at least 10 only for legacy and with its 72-byte input limit handled; PBKDF2-HMAC-SHA256 with 600,000 iterations where FIPS is required.
- **Secrets**: secret manager (Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) or encrypted files (SOPS); short-lived credentials (workload identity, OIDC federation in CI) over static keys; nothing secret in client bundles, mobile app binaries, container images or logs.
- **Browser hardening**: CSP with nonces or hashes and `strict-dynamic`, no `unsafe-inline`; HSTS; `frame-ancestors 'none'`; `X-Content-Type-Options: nosniff`; `Referrer-Policy`; cookies with `Secure`, `HttpOnly`, `SameSite` and the `__Host-` prefix; SRI on third-party scripts.
- **Supply chain**: lockfiles, pinned versions, SCA (Dependabot, Renovate, Snyk, Trivy, OSV-Scanner), SBOM (CycloneDX or SPDX), signed artifacts (Sigstore), secret scanning (Gitleaks, GitHub secret scanning).
- **Exceptional conditions** (OWASP A10:2025): fail closed, never swallow errors on security paths, release locks and roll back transactions on every error path, bound retries, return generic errors with a correlation id.

## 3. Workflow

1. Identify the trust boundary: where untrusted data enters (endpoint, upload, webhook, queue, third-party response).
2. Trace the data flow from entry to every sink, including transformations, storage and later reads (stored XSS, second-order SQLi).
3. Classify each sink and apply its canonical defense: parameterization for SQL, argument arrays for processes, contextual encoding for HTML, containment checks for paths, dial-time IP checks for outbound HTTP, safe formats for deserialization.
4. Validate at the boundary with an allowlist schema, then rely on the typed value; keep encoding at the sink even when input was validated (defense in depth).
5. Check secrets, randomness and crypto calls on the path.
6. Look for race conditions (check-then-act on files, balances, coupons) and use atomic operations or locks.
7. Define the failure path: what happens on timeout, parse error, partial write; it must deny and clean up.
8. Map findings to OWASP Top 10:2025 and CWE; rank by exploitability and impact.
9. Add a regression test with the attack payload, then run SAST, SCA and secret scanning.
10. Record residual risk and any accepted exceptions with an owner and an expiry.

## 4. Decision Rules

- Allowlist over denylist for validation. Denylists are a secondary signal only.
- ORM or query builder by default; raw SQL only with bound parameters. Identifiers (table, column, sort order) cannot be parameters: map them from an allowlist.
- Argon2id for new password storage; keep bcrypt only for existing hashes and rehash on next login.
- Secret manager over plain environment variables for long-lived production secrets; environment variables are acceptable for injecting a short-lived token or a reference to the secret.
- JSON or Protobuf over native serialization for anything that crosses a trust boundary.
- Constant-time comparison (`crypto.timingSafeEqual`, `hmac.compare_digest`, `subtle.ConstantTimeCompare`, `MessageDigest.isEqual`) for MACs, tokens and API keys.
- CSP nonces for server-rendered pages, hashes for static inline scripts; never `unsafe-inline` for scripts.
- Server-generated file names over sanitized user file names.
- Fixed destination allowlist for outbound calls when possible; when users supply URLs (webhooks, link previews, importers), add the dial-time IP check from Example 2.
- Fail closed: if a validator, secret manager or security dependency is unavailable, deny the request.

## 5. Coding Standards

- Parse, do not validate-and-forget: `const input = schema.parse(req.body)` and use only `input` afterwards.
- One validation schema per request shape, named `<entity><Action>Schema` (`orderCreateSchema`), using `z.strictObject` in Zod 4 so unknown keys fail.
- Crypto helpers live in one module (`security/crypto`) with explicit names: `hashPassword`, `verifyPassword`, `generateToken`, `safeEqual`. Never call a one-way hash "encrypt".
- Secrets are read once at startup through a typed loader; the process fails to start if a required secret is missing (no hard-coded fallback).
- Every outbound HTTP client sets connect, header and total timeouts plus a maximum response size.
- Every error response to clients is generic (`{"error":"internal_error","correlationId":"..."}`); the full error goes to server logs with secrets redacted.
- Logs never contain passwords, tokens, session ids, full card numbers or raw request bodies of auth endpoints.
- Security-relevant code carries a short comment stating the threat it blocks.

## 6. Project Structure

```
src/
├── security/
│   ├── crypto.ts            # hashPassword, verifyPassword, generateToken, safeEqual
│   ├── headers.ts           # CSP (per-request nonce), HSTS, frame-ancestors
│   ├── outbound-http.ts     # SSRF-safe client (allowlist + dial-time IP check)
│   └── secrets.ts           # typed secret loader, fails closed
├── validation/
│   ├── order.schema.ts
│   └── common.schema.ts     # ids, emails, pagination bounds
├── uploads/
│   └── store.ts             # MIME sniffing, size limit, contained paths
├── repositories/            # parameterized queries only
└── api/
tests/
└── security/                # injection, XSS, traversal, SSRF payload tests
.github/workflows/
└── security.yml             # SAST, SCA, secret scan, SBOM
```

## 7. Design Patterns

- **Parse at the edge**: a schema turns untrusted input into a typed value; core code never sees raw input.
- **Safe sink wrappers**: expose `db.query(sql, params)`, `runTool(binary, args[])`, `safeFetch(url)`, `storeUpload(bytes)` and ban the raw APIs with lint or Semgrep rules.
- **Defense in depth**: validation, then parameterization or encoding at the sink, then least-privilege credentials (database user without DDL, read-only file system), then logging and alerts.
- **Fail closed**: any error in a security decision path returns deny; `try { ... } catch { return allow }` is a defect.
- **Secure defaults**: cookie helpers set `Secure; HttpOnly; SameSite=Lax; Path=/` by default and require an explicit, reviewed override.
- **Content-addressed storage**: store uploads by hash plus a server-chosen extension; keep the user's file name only as escaped metadata.

## 8. Best Practices

- Validate size first (body limits in the framework, streaming size caps for uploads), then shape, then semantics.
- Keep untrusted HTML out of the DOM; where rich text is required, sanitize with DOMPurify server- or client-side with an allowlist of tags and attributes.
- Use framework CSRF protection or `SameSite` cookies plus an anti-CSRF token for cookie-authenticated state changes; never change state on GET.
- Use `Content-Disposition: attachment` and a separate origin (for example a user-content domain) when serving user uploads.
- Re-encode user images (for example with Pillow or sharp) to strip active content and metadata.
- Treat LLM output and third-party API responses as untrusted input: validate before use, encode before rendering, never pass to a shell or `eval`.
- Pin dependencies through lockfiles, review new transitive dependencies, and prefer packages with provenance attestations.
- Use short-lived cloud credentials in CI through OIDC federation instead of stored keys.

## 9. Performance

- Compile validation schemas once at module load; do not rebuild them per request.
- Password hashing is intentionally slow; run it only on login, signup and password change, and size the worker pool so a login burst cannot starve the event loop (node `argon2` runs off the main thread).
- Cache DNS results in the SSRF-safe client only if the cached IP is still checked at dial time; the check in `net.Dialer.Control` costs microseconds.
- Bounded reads (`io.LimitReader`, streaming upload caps) keep memory flat under attack.
- Run SAST incrementally on pull requests and in full nightly; keep SCA on every build since it is fast.

## 10. Security

- TLS everywhere, including service-to-service; HSTS on public origins.
- Least privilege for every credential: the application database role cannot alter schema; the upload directory is not executable and not served directly by the app server.
- Secrets never cross into client code: no keys in `NEXT_PUBLIC_*`, Vite `VITE_*`, mobile `BuildConfig` or `Info.plist`, or cloud-init user-data.
- Container and runtime: run as non-root, read-only root file system where possible, no shell in distroless images.
- Error and debug pages disabled in production; stack traces only in server logs.
- Security logging: failed validation spikes, blocked SSRF attempts and upload rejections are logged with request id and actor, never with the payload's secrets.

## 11. Testing

- Unit-test every schema with valid, invalid, boundary and Unicode inputs, plus unknown extra fields.
- Payload tests for each sink: `' OR 1=1--` and `'; DROP TABLE` (SQL), `{"$ne":null}` (NoSQL), `; id` and `$(id)` (shell), `<script>`, `"><img src=x onerror=...>` and `javascript:` URLs (XSS), `../`, `..%2f`, absolute paths and symlinks (traversal), `http://169.254.169.254/`, `http://[::1]/`, decimal and octal IPs and a DNS name that resolves to `127.0.0.1` (SSRF).
- Property-based or fuzz tests on parsers and validators (fast-check, Hypothesis, Go native fuzzing, Jazzer for Java).
- SAST: Semgrep and CodeQL with custom rules for banned APIs (`eval`, `child_process.exec`, `pickle.loads`, raw `fetch` of user URLs).
- SCA and secret scanning on every pull request; DAST (OWASP ZAP) against a staging deployment, never production.

## 12. Review Checklist

- [ ] Every entry point validates with an allowlist schema and size limits; unknown fields are rejected.
- [ ] SQL and NoSQL calls use bound parameters; dynamic identifiers come from an allowlist.
- [ ] No shell strings with user input; processes use argument arrays.
- [ ] HTML output is auto-escaped; any raw HTML passes through a sanitizer.
- [ ] File paths derived from input are resolved and checked for containment; uploads use server-generated names.
- [ ] Outbound requests to user-influenced URLs use the SSRF-safe client (allowlist, dial-time IP check, redirect re-check, timeouts, size cap).
- [ ] No native deserialization of untrusted data; YAML uses safe loaders.
- [ ] Secrets come from the secret manager or a short-lived injected token; none in code, bundles, images or logs.
- [ ] Tokens and ids for security use a CSPRNG; secret comparisons are constant-time.
- [ ] Passwords use Argon2id (or legacy bcrypt with rehash on login).
- [ ] Security headers and cookie attributes are set by shared middleware.
- [ ] Error responses are generic with a correlation id; errors on security paths fail closed and clean up.
- [ ] A regression test with the attack payload exists for every fixed finding.
- [ ] SAST, SCA and secret scanning pass; refactors re-run them and introduce no new findings.

## 13. Production Notes

- Keep the CSP in report-only mode first, collect violation reports, then enforce; keep a nonce per response.
- Alert on bursts of validation failures, SSRF blocks and upload rejections per actor or IP; they usually precede a real attempt.
- Track open SCA findings by severity with a remediation SLA; rebuild images when base images get security patches.
- Rotate any secret that appears in a log, crash dump or repository, then remove it from history; rotation comes first.
- Keep the SBOM with each release so a new CVE can be matched to deployed versions within hours.

## 14. Examples

### Example 1: Upload handler with validated tenant id and contained path (Python, FastAPI)

The tenant id comes from the authenticated principal, is typed as `uuid.UUID` (only hex digits and hyphens survive `str()`), and the final path is resolved and checked against the tenant directory. The stored name and extension are server-generated, and the file is created with `O_EXCL | O_NOFOLLOW` so an existing file or symlink is never overwritten.

```python
import hashlib
import os
import uuid
from pathlib import Path

import magic  # python-magic (libmagic)
from fastapi import HTTPException, UploadFile

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}
MAX_BYTES = 10 * 1024 * 1024
UPLOAD_ROOT = Path("/var/app/uploads").resolve()


async def read_limited(file: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if size > limit:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    return b"".join(chunks)


async def store_upload(file: UploadFile, tenant_id: uuid.UUID) -> dict:
    content = await read_limited(file, MAX_BYTES)

    mime = magic.from_buffer(content[:8192], mime=True)  # sniff content, ignore the client's Content-Type
    extension = ALLOWED_TYPES.get(mime)
    if extension is None:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    digest = hashlib.sha256(content).hexdigest()
    tenant_dir = (UPLOAD_ROOT / str(tenant_id)).resolve()
    target = (tenant_dir / f"{digest}{extension}").resolve()
    # Containment check on the final, resolved path (blocks ../, absolute paths and symlinked dirs).
    if tenant_dir.parent != UPLOAD_ROOT or not target.is_relative_to(tenant_dir):
        raise HTTPException(status_code=400, detail="Invalid upload")

    tenant_dir.mkdir(mode=0o750, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, flags, 0o640)
    except FileExistsError:
        pass  # identical content already stored (content-addressed)
    else:
        with os.fdopen(fd, "wb") as out:
            out.write(content)

    original = os.path.basename(file.filename or "")[:255]  # metadata only, escape on display
    return {"id": digest, "mimeType": mime, "size": len(content), "originalName": original}
```

Next steps for production: antivirus scanning (for example ClamAV) before the file is made available, image re-encoding, and serving from a separate origin with `Content-Disposition: attachment`.

### Example 2: SSRF-safe HTTP client with dial-time IP check (Go)

Checking DNS before the request leaves a time-of-check/time-of-use gap: the resolver can return a public IP to the check and a private IP to the dialer (DNS rebinding). Here `net.Dialer.Control` runs after resolution with the exact IP and port being connected, for the first request and for every redirect and new connection.

```go
package outbound

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"syscall"
	"time"
)

var ErrDestinationBlocked = errors.New("destination not allowed")

var allowedHosts = map[string]bool{"api.github.com": true, "api.stripe.com": true}

var extraBlocked = []netip.Prefix{
	netip.MustParsePrefix("0.0.0.0/8"),
	netip.MustParsePrefix("100.64.0.0/10"), // carrier-grade NAT
	netip.MustParsePrefix("192.0.0.0/24"),
	netip.MustParsePrefix("198.18.0.0/15"),
	netip.MustParsePrefix("64:ff9b::/96"), // NAT64 can map to internal IPv4
}

func isBlocked(addr netip.Addr) bool {
	addr = addr.Unmap()
	if !addr.IsGlobalUnicast() || addr.IsPrivate() || addr.IsLoopback() || addr.IsLinkLocalUnicast() {
		return true
	}
	for _, p := range extraBlocked {
		if p.Contains(addr) {
			return true
		}
	}
	return false
}

// control runs for every connection attempt, with the resolved IP:port.
func control(network, address string, _ syscall.RawConn) error {
	if network != "tcp4" && network != "tcp6" {
		return ErrDestinationBlocked
	}
	ap, err := netip.ParseAddrPort(address)
	if err != nil || ap.Port() != 443 || isBlocked(ap.Addr()) {
		return ErrDestinationBlocked
	}
	return nil
}

func checkURL(u *url.URL) error {
	if u.Scheme != "https" || u.User != nil || (u.Port() != "" && u.Port() != "443") || !allowedHosts[u.Hostname()] {
		return ErrDestinationBlocked
	}
	return nil
}

func NewClient() *http.Client {
	dialer := &net.Dialer{Timeout: 5 * time.Second, Control: control}
	transport := &http.Transport{
		Proxy:                 nil, // never route through HTTP(S)_PROXY from the environment
		DialContext:           dialer.DialContext,
		ForceAttemptHTTP2:     true,
		TLSHandshakeTimeout:   5 * time.Second,
		ResponseHeaderTimeout: 10 * time.Second,
		IdleConnTimeout:       90 * time.Second,
	}
	return &http.Client{
		Transport: transport,
		Timeout:   15 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 3 {
				return errors.New("too many redirects")
			}
			return checkURL(req.URL)
		},
	}
}

const maxBody = 10 << 20

func Fetch(ctx context.Context, c *http.Client, rawURL string) ([]byte, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil, ErrDestinationBlocked
	}
	if err := checkURL(u); err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %d", resp.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, maxBody+1))
	if err != nil {
		return nil, err
	}
	if len(body) > maxBody {
		return nil, errors.New("response too large")
	}
	return body, nil
}
```

For user-supplied destinations (webhooks, link previews) drop the host allowlist but keep `control`, the redirect check and the limits; also run the fetcher in a network segment without access to internal services.

### Example 3: Password hashing, tokens and constant-time compare (TypeScript, Node.js)

```typescript
import argon2 from 'argon2';
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';

// OWASP minimum for Argon2id: m=19 MiB, t=2, p=1. Raise memory if login latency allows.
const ARGON2_OPTIONS = { type: argon2.argon2id, memoryCost: 19_456, timeCost: 2, parallelism: 1 } as const;

export async function hashPassword(plain: string): Promise<string> {
  return argon2.hash(plain, ARGON2_OPTIONS);
}

export async function verifyPassword(plain: string, stored: string): Promise<{ ok: boolean; rehash: boolean }> {
  try {
    const ok = await argon2.verify(stored, plain);
    return { ok, rehash: ok && argon2.needsRehash(stored, ARGON2_OPTIONS) };
  } catch {
    return { ok: false, rehash: false }; // malformed hash: fail closed
  }
}

export function generateToken(bytes = 32): string {
  return randomBytes(bytes).toString('base64url');
}

// Hashing both sides first gives equal-length buffers, so length is not leaked.
export function safeEqual(a: string, b: string): boolean {
  const da = createHash('sha256').update(a).digest();
  const db = createHash('sha256').update(b).digest();
  return timingSafeEqual(da, db);
}
```

## 15. Common Mistakes

- **Client-side validation only**: trivially bypassed with a direct request. Validate on the server; client checks are UX.
- **Denylist filters** (`replace('<script>', '')`, blocking `../` once): bypassed by encoding and nesting. Use allowlists and containment checks.
- **String-built SQL**, including `ORDER BY ${req.query.sort}`: parameterize values, map identifiers from an allowlist.
- **`exec('convert ' + file)`**: command injection. Use `execFile('convert', [file])` and validate the argument.
- **Joining a user-controlled id or name into a path** (`UPLOAD_BASE / tenant_id`): traversal. Validate the id's type and check the resolved path.
- **Checking DNS, then letting the HTTP client resolve again**: DNS rebinding bypass. Check the IP at dial time.
- **Following redirects without re-checking**: an allowed host redirects to `169.254.169.254`. Re-validate in `CheckRedirect` or disable redirects.
- **`pickle.loads`, `yaml.load`, `ObjectInputStream` on request data**: remote code execution. Use JSON with a schema.
- **Fast hashes for passwords** (MD5, SHA-1, SHA-256): GPU brute force. Use Argon2id.
- **`Math.random()` for reset tokens or ids**: predictable. Use the platform CSPRNG.
- **`===` on secrets**: timing side channel. Use constant-time comparison.
- **Verbose errors and debug mode in production**: stack traces, SQL and versions leak. Return generic errors with a correlation id.
- **Catch-all handlers that continue** (`catch { /* ignore */ }` on a security check): fails open. Deny and clean up.
- **Secrets in front-end env prefixes or mobile build configs**: shipped to every user. Keep them server-side.

## 16. References

- [references/owasp-top-10.md](references/owasp-top-10.md): OWASP Top 10:2025 categories with defenses, the 2021-to-2025 mapping, threat modeling with STRIDE and the SAST/DAST/SCA pipeline.
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- OWASP Top 10:2025: https://owasp.org/Top10/2025/
