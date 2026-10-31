# R2 Object Storage

R2 from Workers and from outside: the binding API, conditional and ranged reads, listing, multipart uploads, the S3 API with presigned URLs, CORS, public access and limits. Facts come from the R2 documentation sources and Wrangler 4.156.0 (2026-10).

## Contents

1. [Create a bucket and a binding](#1-create-a-bucket-and-a-binding)
2. [Binding API](#2-binding-api)
3. [Serving and uploading objects](#3-serving-and-uploading-objects)
4. [Listing](#4-listing)
5. [Multipart uploads](#5-multipart-uploads)
6. [S3 API and presigned URLs](#6-s3-api-and-presigned-urls)
7. [CORS](#7-cors)
8. [Public access and custom domains](#8-public-access-and-custom-domains)
9. [Limits and costs](#9-limits-and-costs)
10. [Security checklist](#10-security-checklist)

## 1. Create a bucket and a binding

```bash
npx wrangler r2 bucket create notes-attachments
npx wrangler r2 bucket list
npx wrangler r2 bucket info notes-attachments
```

```jsonc
{
  "r2_buckets": [
    { "binding": "BUCKET", "bucket_name": "notes-attachments" }
  ]
}
```

- Run `npx wrangler types` afterwards so `env.BUCKET` is typed as `R2Bucket`.
- `wrangler dev` simulates R2 locally in `.wrangler/state`; it does not touch the real bucket unless the binding is configured to use the remote resource (check the current local development docs).
- Other bucket subcommands from the CLI: `cors`, `lifecycle`, `lock`, `notification`, `domain`, `dev-url`, `sippy` (incremental migration from another provider) and `local-uploads`.
- Buckets are private by default. Public access is a separate, explicit step (section 8).

## 2. Binding API

The methods on `R2Bucket` (from the Workers API reference):

| Method | Signature (abridged) | Notes |
|---|---|---|
| `head` | `(key) => Promise<R2Object or null>` | Metadata only, no body. |
| `get` | `(key, options?) => Promise<R2ObjectBody or R2Object or null>` | Returns `null` when missing. With `onlyIf` a failed precondition returns an `R2Object` without a body. |
| `put` | `(key, value, options?) => Promise<R2Object or null>` | Value can be a stream, `ArrayBuffer`, view, string, `Blob` or null. Returns null when `onlyIf` fails. |
| `delete` | `(key or key[]) => Promise<void>` | Accepts an array for batch deletes. |
| `list` | `(options?) => Promise<R2Objects>` | Paginated by `cursor`; check `truncated`. |
| `createMultipartUpload` | `(key, options?)` | Returns an `R2MultipartUpload`. |
| `resumeMultipartUpload` | `(key, uploadId)` | Reattach to an in-progress upload. |

- `R2Object` fields include `key`, `size`, `etag`, `httpEtag`, `uploaded`, `httpMetadata`, `customMetadata`, `range`, and `writeHttpMetadata(headers)`.
- `R2ObjectBody` adds `body` (a `ReadableStream`), `bodyUsed`, and the readers `arrayBuffer()`, `text()`, `json()`, `blob()`.
- `put` options: `httpMetadata` (content type, cache control, content disposition, content encoding, content language, cache expiry), `customMetadata` (string map, counted against the 8,192 byte metadata limit), `onlyIf`, and checksum fields (`md5`, `sha1`, `sha256`, `sha384`, `sha512`) that R2 verifies on upload. Check the reference for storage class options.
- Keys are UTF-8 strings up to 1,024 bytes. Treat keys as opaque; never build them from raw user input without normalising (no `..` meaning, no leading slash assumptions).

## 3. Serving and uploading objects

Serving an object with conditional requests and ranges:

```ts
export default {
  async fetch(request, env): Promise<Response> {
    const url = new URL(request.url);
    const key = decodeURIComponent(url.pathname.slice(1));
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    }
    if (!/^[A-Za-z0-9._\/-]{1,512}$/.test(key) || key.includes("..")) {
      return new Response("Bad Request", { status: 400 });
    }

    const object = await env.BUCKET.get(key, {
      onlyIf: request.headers,
      range: request.headers,
    });
    if (object === null) return new Response("Not Found", { status: 404 });

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
    headers.set("X-Content-Type-Options", "nosniff");

    if (!("body" in object) || object.body === undefined) {
      return new Response(null, { status: 304, headers });
    }
    return new Response(request.method === "HEAD" ? null : object.body, {
      status: object.range ? 206 : 200,
      headers,
    });
  },
} satisfies ExportedHandler<Env>;
```

- Passing `request.headers` as `onlyIf` and `range` lets R2 evaluate `If-None-Match`, `If-Modified-Since` and `Range` directly. Confirm the status mapping against the current docs when editing.
- Stream `object.body` into the `Response`; do not call `arrayBuffer()` on large objects (isolate memory is limited).
- Set `X-Content-Type-Options: nosniff` and, for user-uploaded content, a `Content-Disposition: attachment` header unless inline display is intended and the content type is trusted.

Uploading through the Worker (small files, authenticated endpoint):

```ts
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = new Set(["image/png", "image/jpeg", "application/pdf"]);

async function upload(request: Request, env: Env, userId: string): Promise<Response> {
  const type = request.headers.get("Content-Type") ?? "";
  const length = Number(request.headers.get("Content-Length") ?? "0");
  if (!ALLOWED.has(type)) return Response.json({ error: "unsupported type" }, { status: 415 });
  if (!Number.isFinite(length) || length <= 0 || length > MAX_BYTES) {
    return Response.json({ error: "bad size" }, { status: 413 });
  }
  const key = `users/${userId}/${crypto.randomUUID()}`;
  await env.BUCKET.put(key, request.body, {
    httpMetadata: { contentType: type },
    customMetadata: { owner: userId },
  });
  return Response.json({ key }, { status: 201 });
}
```

- Generate keys server-side (UUID plus a prefix) instead of accepting client file names; store the original name in `customMetadata` or D1.
- Passing `request.body` streams the upload. A stream of unknown length may need a known length; with a fixed-length body `Content-Length` is available.
- A single binding `put` is limited by the single-part maximum (5 GiB); larger objects need multipart.

## 4. Listing

```ts
async function listAll(env: Env, prefix: string): Promise<string[]> {
  const keys: string[] = [];
  let cursor: string | undefined;
  do {
    const page = await env.BUCKET.list({ prefix, limit: 1000, cursor });
    for (const obj of page.objects) keys.push(obj.key);
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return keys;
}
```

- Do not compare the number of returned objects to `limit` to decide whether to continue; use the `truncated` flag and `cursor`.
- `delimiter: "/"` returns `delimitedPrefixes` for folder-like views.
- `include: ["httpMetadata", "customMetadata"]` adds metadata to each list entry; this needs a compatibility date of 2022-08-04 or later (or the `r2_list_honor_include` flag).
- Listing a large bucket in a request path is slow and costly; keep an index in D1 or KV for user-facing listings.

## 5. Multipart uploads

```ts
async function multipart(env: Env, key: string, chunks: AsyncIterable<Uint8Array>): Promise<void> {
  const upload = await env.BUCKET.createMultipartUpload(key);
  const parts: R2UploadedPart[] = [];
  try {
    let n = 1;
    for await (const chunk of chunks) {
      parts.push(await upload.uploadPart(n++, chunk));
    }
    await upload.complete(parts);
  } catch (err) {
    await upload.abort();
    throw err;
  }
}
```

- Every part except the last must meet the minimum part size of the S3 multipart protocol; the maximum number of parts is 10,000, and the multipart object limit is about 4.995 TiB.
- A browser can drive multipart through the Worker: one endpoint creates, one uploads a part, one completes, each calling `resumeMultipartUpload(key, uploadId)`.
- Abort incomplete uploads or add a lifecycle rule that aborts them; leftover parts count toward storage.

## 6. S3 API and presigned URLs

- The S3-compatible endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Use region `auto`. Create an R2 API token in the dashboard to obtain an Access Key ID and Secret Access Key, scoped to specific buckets and permissions.
- A presigned URL grants one S3 operation (GET, PUT, HEAD or DELETE) on one object until it expires. Expiry ranges from 1 second to 7 days (604,800 seconds). Signing happens locally with AWS Signature Version 4; no request goes to R2.
- The R2 Workers binding cannot create presigned URLs. In a Worker, sign with `aws4fetch` or with the AWS SDK for JavaScript v3 (with `nodejs_compat` enabled), and keep the key pair as Worker secrets.

```ts
import { AwsClient } from "aws4fetch";

async function presignPut(env: Env, key: string, contentType: string): Promise<string> {
  const client = new AwsClient({
    service: "s3",
    region: "auto",
    accessKeyId: env.R2_ACCESS_KEY_ID,
    secretAccessKey: env.R2_SECRET_ACCESS_KEY,
  });
  const target = `https://${env.ACCOUNT_ID}.r2.cloudflarestorage.com/notes-attachments/${key}?X-Amz-Expires=600`;
  const signed = await client.sign(
    new Request(target, { method: "PUT", headers: { "Content-Type": contentType } }),
    { aws: { signQuery: true, allHeaders: true } },
  );
  return signed.url.toString();
}
```

- Set `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` with `wrangler secret put`; `ACCOUNT_ID` is not secret and can live in `vars`.
- With `allHeaders: true` and a `Content-Type` header, the signature binds the content type, so the client must send the same header. Keep expiry short (minutes for uploads).
- Use temporary credentials instead of presigned URLs when a caller uses an S3 SDK for several operations within a scoped session.
- Expired URLs return 403 `ExpiredRequest`, and CORS headers are not included in that response, so a browser cannot read the error body. Refresh URLs before expiry.
- Using the AWS SDK for JavaScript v3 outside Workers: create `S3Client` with `region: "auto"` and the account endpoint, then `getSignedUrl(S3, new PutObjectCommand({ Bucket, Key, ContentType }), { expiresIn })` from `@aws-sdk/s3-request-presigner`.
- Do not use presigned URLs to expose the whole bucket: generate one per object, after authorising the user for that key.

## 7. CORS

CORS is required whenever a browser on another origin reads or writes objects, through a public bucket, a custom domain or presigned URLs.

```json
[
  {
    "AllowedOrigins": ["https://app.example.com"],
    "AllowedMethods": ["GET", "PUT"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

- Apply it in the dashboard or with `npx wrangler r2 bucket cors` (it has a `list <bucket>` subcommand; run `--help` for the others and their argument shape in the installed version).
- `AllowedMethods` must match the operations the presigned URLs perform. `AllowedHeaders` must include every header the client sends (content type, checksum, custom metadata). `ExposeHeaders: ["ETag"]` lets JavaScript read the upload ETag.
- Use exact origins. A wildcard origin on a bucket holding private or presigned content widens exposure.
- Custom domains connected to a bucket with a CORS policy return CORS headers for requests that carry an `Origin` header; testing with `curl` needs `-H "Origin: https://app.example.com"`.
- After changing CORS on a bucket already served through a custom domain, purge the cache for that hostname, because cached responses lack the new headers.
- Objects served through your own Worker are governed by the Worker's headers, not by the bucket CORS policy.

## 8. Public access and custom domains

- Custom domain: connect a domain on a Cloudflare zone to the bucket (dashboard or `wrangler r2 bucket domain`). This enables Cloudflare Cache, WAF custom rules, access controls and Bot Management. Up to 100 custom domains per bucket.
- `r2.dev` managed subdomain: intended for non-production use; WAF, caching, access controls and Bot Management are not available on it. Manage with `wrangler r2 bucket dev-url`.
- The two options are independent; enabling a custom domain does not enable `r2.dev`.
- For private content with a public front, serve through a Worker that checks authorisation and streams `env.BUCKET.get(key)`.
- Use Cache-Control in `httpMetadata` at upload time so edge caches can serve repeated reads.
- Lifecycle rules (`wrangler r2 bucket lifecycle`) expire objects or abort stale multipart uploads; bucket locks (`wrangler r2 bucket lock`) enforce retention.
- Event notifications (`wrangler r2 bucket notification`) send object events to a Queue, which can trigger processing after an upload.

## 9. Limits and costs

From the R2 limits page (2026-10); re-check before quoting:

| Item | Limit |
|---|---|
| Storage per bucket, objects per bucket | unlimited |
| Buckets per account | 100,000 by default |
| Object key length | 1,024 bytes |
| Object metadata size | 8,192 bytes |
| Object size | 5 TiB |
| Single-part upload | 5 GiB |
| Multipart upload | 4.995 TiB, up to 10,000 parts |
| Concurrent writes to the same key | 1 per second |
| Bucket management operations | 50 per second per bucket |

- Egress directly from R2 (Workers API, S3 API, `r2.dev`) is not charged. Storage and operations (Class A and Class B) are billed, and the Infrequent Access class adds data retrieval fees. Other metered services connected to a bucket can still charge. Read the pricing page for rates.
- Writing the same key more than once per second returns errors; use unique keys for concurrent writers.

## 10. Security checklist

- Bucket stays private; public exposure is an explicit decision with a custom domain.
- S3 credentials are scoped API tokens, stored as secrets, never in client code or git.
- Presigned URLs: shortest expiry, one object, specific method, bound content type, issued only after authorisation.
- Uploads validate size, content type and (for sensitive flows) content signature; server-generated keys.
- CORS lists exact origins, methods and headers.
- User-uploaded files served with `nosniff` and, where appropriate, `Content-Disposition: attachment`, ideally from a separate domain than the app.
- Delete flows remove both the object and its database record; consider lifecycle rules for temporary uploads.
