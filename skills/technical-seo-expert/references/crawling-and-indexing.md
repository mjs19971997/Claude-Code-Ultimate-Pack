# Crawling and Indexing

Crawl control and index control in detail: robots.txt syntax and precedence, meta robots and `X-Robots-Tag`, canonicals, hreflang, sitemaps, redirects, pagination and facets, Search Console and Bing Webmaster Tools, IndexNow, log analysis and migrations. Verified against RFC 9309, the Sitemaps protocol 0.9, the IndexNow documentation as reported by secondary sources, and Next.js 16 metadata conventions (2026-10). Google behavior listed here comes from Search Central guidance; items marked "check the current docs" could not be re-confirmed against Google's pages.

## 1. robots.txt

### Syntax

- The file lives at the host root (`https://www.example.com/robots.txt`); each host, scheme and port has its own file. Plain text, UTF-8, at most 500 KiB for Google (content beyond the limit is ignored).
- Lines are `field: value`. Google reads `user-agent`, `allow`, `disallow` and `sitemap`. Other fields (`crawl-delay`, `host`, `noindex`) are ignored by Google; some other engines honor `crawl-delay`.
- A group begins with one or more `User-agent` lines followed by rules. A crawler obeys only the group whose user agent token matches it most specifically; it falls back to `*` only if no specific group exists.
- Paths are matched as prefixes, case-sensitively. `*` matches any sequence of characters; `$` anchors the end of the URL.
- `Sitemap:` takes an absolute URL and applies to all groups; it may appear multiple times.

### Precedence: longest match wins

For a given URL the crawler finds every `Allow` and `Disallow` rule whose path matches, then applies the rule with the longest path (most characters). If an `Allow` and a `Disallow` tie, the least restrictive rule (`Allow`) applies. Rule order in the file does not matter to Google (RFC 9309 matching).

| Rules in the group | URL | Result | Why |
|---|---|---|---|
| `Disallow: /shop/` | `/shop/shoes` | blocked | prefix match |
| `Disallow: /shop/` and `Allow: /shop/sale/` | `/shop/sale/coat` | allowed | `/shop/sale/` is longer |
| `Disallow: /page` and `Allow: /page` | `/page` | allowed | tie, least restrictive |
| `Disallow:` (empty) | any | allowed | empty value allows everything |
| `Disallow: /` | any | blocked | blocks the whole site |
| `Disallow: /*?sort=` | `/list?sort=price` | blocked | wildcard |
| `Disallow: /*.json$` | `/data.json`, not `/data.json?x=1` | blocked | `$` anchors the end |
| `Allow: /` and `Disallow: /private/` | `/private/a` | blocked | `/private/` longer than `/` |

### The group trap

```
User-agent: *
Disallow: /private/
Disallow: /tmp/

User-agent: Googlebot
Allow: /
```

Googlebot matches its own group and ignores the `*` group completely, so `/private/` and `/tmp/` become crawlable for it. Repeat shared rules in every group:

```
User-agent: Googlebot
Disallow: /private/
Disallow: /tmp/
Allow: /private/press-kit/
```

An `Allow: /` line is never needed to permit crawling; absence of a matching Disallow already allows it.

### Status code handling (Google)

- 200: parsed. 3xx: followed for a few hops; unresolved redirects are treated as not found.
- 4xx (except 429): treated as "no robots.txt", so everything is crawlable.
- 5xx and 429: Google pauses crawling the host and retries; after prolonged failure it may use a cached copy or, if none, proceed as if there are no restrictions. A long robots.txt outage can halt crawling. Check the current docs for exact windows.

### What robots.txt does and does not do

- It controls crawling, not indexing. A disallowed URL with inbound links can be indexed with a bare title or URL. To keep a page out of results, allow the crawl and serve `noindex`.
- Do not block CSS, JavaScript or image files that pages need to render.
- It is public and not a security boundary.
- Per-bot rules for AI crawlers use their documented tokens (for example `Google-Extended`, `GPTBot`, `ClaudeBot`); each vendor documents what its token controls. Check the vendor's page before relying on one.
- Test with a parser that implements longest-match (Google's open-source `robotstxt` library, or Search Console's robots.txt report); do not rely on first-match parsers.

## 2. Meta robots and X-Robots-Tag

```html
<meta name="robots" content="noindex, follow">
<meta name="googlebot" content="max-snippet:160, max-image-preview:large">
```

```nginx
# nginx: keep PDFs and a staging area out of the index
location ~* \.pdf$ {
    add_header X-Robots-Tag "noindex, nofollow" always;
}
```

| Directive | Effect |
|---|---|
| `noindex` | Do not show the page in results |
| `nofollow` | Do not follow links on the page (treated as a hint) |
| `none` | `noindex, nofollow` |
| `nosnippet` | No text or video snippet; also limits use in some AI features |
| `max-snippet:N` | Text snippet at most N characters (`0` equals nosnippet, `-1` unlimited) |
| `max-image-preview:none/standard/large` | Largest image preview size |
| `max-video-preview:N` | Video preview seconds |
| `noimageindex` | Do not index images on the page |
| `notranslate` | Do not offer translation |
| `unavailable_after: <date>` | Drop from results after the date (RFC 822/850/ISO 8601) |
| `indexifembedded` | Allow indexing of content embedded through an iframe even when `noindex` is set |

- Multiple directives can be combined with commas; conflicting directives resolve to the most restrictive.
- `data-nosnippet` on an HTML element hides that text from snippets.
- The crawler must fetch the page to see these directives, so the URL must not be disallowed in robots.txt.
- Put the directive in the initial HTML or HTTP header; JavaScript-added `noindex` can work but JavaScript-removed `noindex` may not, because pages with `noindex` may skip rendering.

## 3. Canonical URLs

- `<link rel="canonical" href="https://www.example.com/page">` in `<head>`, or `Link: <https://www.example.com/doc.pdf>; rel="canonical"` for non-HTML files. One per page. Absolute URLs.
- Google treats it as a strong hint and may choose a different canonical when other signals (redirects, internal links, sitemap, hreflang, content similarity) disagree. Search Console shows both "User-declared canonical" and "Google-selected canonical" in URL Inspection.
- Self-reference by default. Cross-domain canonicals are allowed for syndicated content.
- Parameter handling: canonical to the clean URL for tracking, sort and session parameters; keep parameters in the canonical only when they change the primary content.
- Do not canonicalize paginated pages to page 1, and do not put `noindex` and a canonical to another URL on the same page.
- Keep canonical, redirects, sitemap `<loc>`, hreflang URLs and internal links on the same form (scheme, host, trailing slash, case).

## 4. hreflang

- Purpose: tell Google which URL serves which language or region; it is a signal for serving the right version, not for ranking.
- Values: language code ISO 639-1 (`en`), optionally region ISO 3166-1 alpha-2 (`en-GB`), `x-default` for the unspecified fallback. Region alone is invalid.
- Every version links to all versions, including itself, using absolute URLs; return links must be reciprocal or the annotations may be ignored.
- Use one method per site: HTML `<link>`, HTTP `Link` header (for non-HTML), or sitemap annotations.
- Each hreflang URL must be indexable and canonical to itself.

```html
<link rel="alternate" hreflang="en-GB" href="https://www.example.com/en-gb/pricing">
<link rel="alternate" hreflang="de-DE" href="https://www.example.com/de-de/pricing">
<link rel="alternate" hreflang="x-default" href="https://www.example.com/en-gb/pricing">
```

## 5. XML sitemaps

- Limits: 50,000 URLs and 50 MB uncompressed per file; a sitemap index can list up to 50,000 sitemaps. UTF-8, absolute URLs on the host that serves the sitemap, XML-escaped.
- Include only canonical, indexable URLs that return 200. Exclude redirected, `noindex`, blocked and parameter duplicates.
- `lastmod` in W3C date format, set only when the content changed meaningfully. Google ignores `priority` and `changefreq`.
- Declare the sitemap in robots.txt and submit it in Search Console. Break large sites into typed sitemaps for per-section reporting.
- Extensions: image (`image:image`), video (`video:video`), news (`news:news`, recent articles only), and hreflang via `xhtml:link`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://www.example.com/en-gb/pricing</loc>
    <lastmod>2026-09-30</lastmod>
    <xhtml:link rel="alternate" hreflang="en-GB" href="https://www.example.com/en-gb/pricing"/>
    <xhtml:link rel="alternate" hreflang="de-DE" href="https://www.example.com/de-de/pricing"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://www.example.com/en-gb/pricing"/>
  </url>
</urlset>
```

```ts
// app/sitemap.ts (Next.js)
import type {MetadataRoute} from 'next';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await getPublishedPosts(); // returns {slug, updatedAt}
  return posts.map((p) => ({
    url: `https://www.example.com/blog/${p.slug}`,
    lastModified: p.updatedAt,
  }));
}
```

## 6. Redirects and status codes

| Situation | Response |
|---|---|
| Permanent move | 301 or 308, single hop, to the final URL |
| Temporary move | 302 or 307 |
| Page removed, no replacement | 410 or 404 |
| Page removed, close replacement | 301 to the replacement |
| Maintenance | 503 with `Retry-After` |
| Rate limiting crawlers | 429 or 503 temporarily; prolonged use reduces crawling |
| Not found page | Real 404 status, never 200 (soft 404) |

```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://www.example.com$request_uri;
}
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;
    return 301 https://www.example.com$request_uri;
}
```

- Meta refresh and JavaScript redirects work but are slower and weaker signals than HTTP redirects.
- Avoid chains (A to B to C): redirect directly to the final URL. Check loops and limits in CI.
- Do not redirect all missing pages to the home page; Google may treat it as a soft 404.

## 7. Pagination, facets and infinite scroll

- Google does not use `rel="prev"` and `rel="next"` as indexing signals. Give each page a distinct URL, a self-referencing canonical and crawlable links (`<a href>`) between pages.
- Infinite scroll: also provide paginated URLs reachable through links and update the URL with the History API as sections load.
- Faceted navigation creates near-infinite URL combinations. Options: link only valuable combinations; canonicalize filtered views to the base category; block low-value parameter spaces in robots.txt (with the understanding that blocked URLs pass no signals); use `nofollow` on filter links as a hint; keep faceted URLs consistent in parameter order.
- Internal search result pages: usually disallow crawling or `noindex` them.
- Calendar, session ID and sort parameters: disallow or canonicalize.

## 8. Search Console and Bing Webmaster Tools

- Create a Domain property (DNS verification) to cover all subdomains and schemes.
- URL Inspection: indexed status, last crawl, user vs. Google-selected canonical, rendered HTML and screenshot from the live test, detected structured data. "Request indexing" is rate-limited; use sitemaps for scale.
- Page indexing report statuses to know: Indexed; Crawled - currently not indexed; Discovered - currently not indexed; Duplicate without user-selected canonical; Duplicate, Google chose different canonical than user; Alternate page with proper canonical tag; Excluded by `noindex` tag; Blocked by robots.txt; Soft 404; Not found (404); Page with redirect.
- Sitemaps report shows submission status and discovered URLs per sitemap.
- Settings, Crawl stats: requests by response code, file type, purpose, average response time, host status (robots.txt fetch, DNS, server connectivity).
- Removals: temporary hiding (about six months) and outdated-content requests; permanent removal still needs 404/410 or `noindex`.
- Performance report retains 16 months; the API allows scripted exports.
- Bing Webmaster Tools: site scan, URL inspection, sitemap submission, and IndexNow integration.

## 9. IndexNow

IndexNow lets a site notify participating search engines when URLs are added, updated or deleted. Google does not participate; Bing, Naver, Seznam.cz and Yandex are widely listed as participants and a submission to one participating engine is shared with the others (confirm the current participant list at indexnow.org before relying on a specific engine).

Setup:

1. Generate a key (8 to 128 characters; letters, digits and dashes).
2. Host a text file at `https://www.example.com/<key>.txt` containing only the key, or point to another same-host location with `keyLocation`.
3. Submit changed URLs after deploys (POST up to 10,000 URLs per request, all on the same host).

```js
// scripts/indexnow.mjs (Node 22+)
const HOST = 'www.example.com';
const KEY = process.env.INDEXNOW_KEY;       // keep the key out of the repository history if rotated often
const urls = process.argv.slice(2);          // e.g. https://www.example.com/blog/new-post

if (!KEY || urls.length === 0) {
  console.error('Usage: INDEXNOW_KEY=... node indexnow.mjs <url> [<url>...]');
  process.exit(1);
}

const res = await fetch('https://api.indexnow.org/indexnow', {
  method: 'POST',
  headers: {'Content-Type': 'application/json; charset=utf-8'},
  body: JSON.stringify({
    host: HOST,
    key: KEY,
    keyLocation: `https://${HOST}/${KEY}.txt`,
    urlList: urls,
  }),
});
console.log(res.status, res.statusText); // 200 or 202 accepted; 400, 403, 422, 429 are errors to inspect
```

Response codes: 200 and 202 mean accepted (202 means the key validation is pending), 400 invalid format, 403 key not valid, 422 URLs do not belong to the host or the key does not match, 429 too many requests. Submit only URLs that really changed. The key is not a secret in the sense of authentication (it is publicly hosted), it proves host ownership.

## 10. Log analysis

- Use server or CDN logs to see what Googlebot actually requests, how often, with which status codes and response times.
- Verify bots: reverse DNS of the IP must resolve to `googlebot.com`, `google.com` or `googleusercontent.com`, and the forward lookup must return the same IP; or match Google's published IP range lists.
- Look for: crawl waste on parameters and faceted URLs, 5xx and slow responses, redirect hops, 404 spikes, important URLs never crawled, and crawl share of low-value sections.
- Combine with Search Console Crawl stats for trends; logs show detail, Search Console shows Google's view.

## 11. Site migration checklist

1. Inventory old URLs (crawl, sitemaps, logs, Search Console, backlinks) and map each to a new URL (1:1 where possible).
2. Build and test the redirect map at staging: status 301 or 308, single hop, no loops, query strings handled.
3. Keep the same content, titles, headings and structured data unless deliberately changed; change one big thing at a time.
4. Update canonicals, hreflang, sitemaps (new URLs only), internal links, structured data URLs, robots.txt and `Sitemap:` lines.
5. Launch: verify robots.txt on the new host is not `Disallow: /` (a common carry-over from staging), the `noindex` header from staging is removed, TLS and HSTS are correct.
6. Add and verify the new Search Console property; for a domain move use the change of address tool after redirects are live; submit the new sitemap and keep the old sitemap for a while so Google discovers the redirects.
7. Monitor Page indexing, Crawl stats, 404 reports and organic traffic daily for the first two weeks; fix mapping gaps quickly.
8. Keep redirects live for at least a year.
