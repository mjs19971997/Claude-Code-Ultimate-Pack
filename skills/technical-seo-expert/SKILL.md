---
name: technical-seo-expert
description: >-
  Makes sites crawlable, indexable and eligible for rich results in search: robots.txt with correct longest-match rules, meta robots and X-Robots-Tag, canonicals, hreflang, XML sitemaps, redirects, pagination, JavaScript rendering (SSR/SSG), Search Console diagnostics, IndexNow, and Schema.org structured data as JSON-LD with safe serialization. Absorbs the former schema-org-expert and structured-data-expert skills. Use when pages are not indexed or wrong URLs rank, when writing robots.txt, sitemaps, canonical or hreflang tags, when adding or validating JSON-LD, or when auditing a site migration. Not for page speed or Core Web Vitals (use core-web-vitals-expert), content strategy, or WCAG compliance (use accessibility-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Technical SEO Expert

This skill covers the technical layer that lets search engines discover, render, index and understand a site: crawl control, indexing signals, URL consolidation, international targeting, rendering of JavaScript sites, sitemaps, migrations, and structured data. It absorbs the former schema-org-expert (vocabulary and entity modeling) and structured-data-expert (Google rich result eligibility, implementation and validation) skills; each has its own reference file, alongside crawling and JavaScript rendering references.

> Verified against RFC 9309 (Robots Exclusion Protocol), the Sitemaps protocol 0.9, Schema.org 30.1 (released 2026-09-16), schema-dts 2.1.0, IndexNow protocol, Next.js 16 metadata docs and Google Search Central guidance as reported through 2026-10 (2026-10). Google documentation hosts were not reachable while writing; items marked "check the current docs" should be confirmed there.

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

- Covered: robots.txt, meta robots and `X-Robots-Tag`, canonical URLs, hreflang, XML sitemaps (including image, video and news extensions), redirects and status codes, pagination and faceted navigation, JavaScript rendering strategy, Google Search Console and Bing Webmaster Tools, IndexNow, log analysis, site migrations, Schema.org vocabulary and JSON-LD, Google structured data features and validation.
- Not covered: keyword research and content strategy, link building, Core Web Vitals and page speed (core-web-vitals-expert), accessibility (accessibility-expert), framework routing internals (nextjs-15-architect).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| robots.txt | Controls crawling, not indexing. Groups start with `User-agent`; a crawler uses the most specific matching group only. Rule match: the longest matching path wins; on a tie the least restrictive (`Allow`) wins. `*` and `$` wildcards, paths are case-sensitive. Google reads `user-agent`, `allow`, `disallow`, `sitemap`; it ignores `crawl-delay` and unsupported `noindex`. Size limit 500 KiB |
| robots.txt status codes | 2xx parsed; 4xx (except 429) treated as no file (all allowed); 5xx and 429 treated as temporarily disallow-all, with fallback to a cached copy after prolonged errors |
| Meta robots / `X-Robots-Tag` | `noindex`, `nofollow`, `none`, `nosnippet`, `max-snippet:N`, `max-image-preview:large`, `max-video-preview:N`, `noimageindex`, `notranslate`, `unavailable_after:`, `indexifembedded`. The header is the way to control PDFs and images. A crawler must be able to fetch the page to see the directive |
| Canonical | `rel="canonical"` is a hint; one absolute URL per page, self-referencing by default; also via `Link` header and sitemaps. Must agree with redirects, internal links, hreflang and sitemaps |
| hreflang | `link rel="alternate" hreflang` in head, HTTP header, or sitemap; every version lists all versions including itself (return links); `x-default` for fallback; language `en` or language-region `en-GB` |
| Sitemaps | Up to 50,000 URLs and 50 MB uncompressed per file; sitemap index for more; UTF-8; absolute canonical 200 URLs only; accurate `lastmod`; Google ignores `priority` and `changefreq` |
| Redirects | 301/308 permanent, 302/307 temporary; avoid chains; Google follows a limited number of hops (about 10) |
| Rendering | Googlebot renders pages with an evergreen Chromium after fetching; render-dependent content is indexed later and less reliably than HTML content. SSR/SSG/ISR is the dependable choice. Googlebot processes the first 2 MB of an HTML file (check the current docs; larger crawler-wide default of 15 MB) |
| Pagination | `rel="prev"/"next"` is not used by Google; use crawlable `<a href>` links and self-canonical pages |
| Search Console | URL Inspection (live test, rendered HTML, selected canonical), Page indexing, Sitemaps, Crawl stats, Removals, Links, Core Web Vitals, rich result reports, Manual actions |
| IndexNow | Push protocol for URL changes: Bing, Naver, Seznam.cz and Yandex are widely listed participants (verify at indexnow.org); Google does not participate |
| Structured data | JSON-LD is the recommended format; markup must match visible content; eligibility is not a guarantee of rich results; several Google features were retired (see structured-data reference) |
| Schema.org | Vocabulary version 30.1 (2026-09-16); use `https://schema.org` as `@context`; model entities with `@id` and `@graph` |

## 3. Workflow

1. Identify the symptom: not indexed, wrong URL indexed, duplicate pages, missing rich results, traffic drop after a release, or a planned migration.
2. Collect evidence: Search Console Page indexing and URL Inspection (inspected vs. Google-selected canonical), server logs for Googlebot hits, a crawl of the site, and `curl -sI` of the affected URLs.
3. Check the pipeline in order: reachable (DNS, TLS, status code), allowed (robots.txt, `X-Robots-Tag`), renderable (content in HTML or after rendering), indexable (meta robots, canonical, duplicates, quality), discoverable (internal links, sitemap), understood (structured data, headings).
4. Fix the earliest failing stage first; a later signal cannot rescue an earlier failure (a blocked page cannot show its `noindex`).
5. Validate with URL Inspection live test, Rich Results Test and Schema Markup Validator, then request re-crawl only for critical URLs.
6. Monitor Page indexing, Crawl stats and sitemap coverage for two to four weeks; keep redirects and old sitemaps in place until migrations settle.

## 4. Decision Rules

- Keep a page out of results: allow crawling and add `noindex` (meta or `X-Robots-Tag`). Do not use robots.txt for this; blocked URLs can still be indexed from links, without content.
- Keep content private: use authentication. robots.txt and `noindex` are not access control and robots.txt publicly lists the paths.
- Duplicate content: 301 when the duplicate should not exist; canonical when both must stay accessible (parameters, print views); `noindex` when the page must exist but not rank.
- Retire a URL permanently: serve 404 or 410 (or 301 to a close equivalent) and remove it from sitemaps. Return a real 404 status, not a 200 "not found" page (soft 404).
- Faceted navigation and internal search: link only valuable combinations, canonicalize others, and disallow endless parameter spaces in robots.txt only when they do not need indexing signals.
- JavaScript apps: SSR/SSG/ISR for indexable content; client-only rendering only for authenticated areas. Do not use dynamic rendering for new work.
- Crawl budget is a concern mainly for very large sites (on the order of a million pages) or very fast-changing ones; for other sites, fix quality, duplicates and server speed instead.
- International sites: separate URLs per locale (subdirectory or domain) with hreflang; do not auto-redirect crawlers by IP or `Accept-Language`.
- Domain or URL changes: map every old URL with a 1:1 301, keep redirects at least a year, update canonicals, hreflang, sitemaps and internal links, then use Search Console's change of address for domain moves.
- AI features: Google documents no special markup for AI Overviews or AI Mode; use `nosnippet`, `max-snippet` and `data-nosnippet` to limit snippets and robots.txt tokens such as `Google-Extended` to limit use for model training (check the current docs; each AI vendor documents its own crawlers).
- Use structured data to describe what is on the page, for entities and eligible features; do not add markup for content users cannot see.

## 5. Coding Standards

- Emit canonical, robots meta, hreflang and JSON-LD server-side in the initial HTML.
- Canonical and hreflang URLs are absolute, use the preferred scheme and host, and match the sitemap exactly (trailing slash and parameters included).
- One canonical per page; one robots meta directive set; do not combine `noindex` with a canonical pointing elsewhere.
- Build URLs in a single function that normalizes host, scheme, case, trailing slash and parameter order.
- Return correct status codes at the server: 200, 301/308, 404, 410, 503 for maintenance (with `Retry-After`).
- JSON-LD: one `@graph` per page, `@id` for entities, absolute URLs, ISO 8601 dates, and typed builders (schema-dts) over hand-written objects.
- Serialize JSON-LD with escaping of `<`, `>`, `&` and U+2028/U+2029 (see Examples); never concatenate user input into JSON strings.

## 6. Project Structure

```
.
├── app/
│   ├── robots.ts                  # generated robots.txt with sitemap URL
│   ├── sitemap.ts                 # sitemap or generateSitemaps() for index files
│   └── [locale]/products/[slug]/page.tsx   # metadata + JSON-LD per template
├── lib/seo/
│   ├── urls.ts                    # absoluteUrl(), canonicalFor(), alternatesFor()
│   ├── jsonld.ts                  # serializeJsonLd() and typed builders
│   └── schema/                    # organization.ts, product.ts, article.ts, breadcrumb.ts
├── scripts/
│   ├── check-sitemap.mjs          # status, canonical and noindex checks for sitemap URLs
│   └── indexnow.mjs               # submits changed URLs after deploy
└── tests/seo/
    ├── head.spec.ts               # canonical, robots, hreflang per template
    └── jsonld.spec.ts             # parse and assert structured data
```

## 7. Design Patterns

- **Single URL authority**: one module decides the canonical URL, alternates and sitemap entries so all signals agree.
- **Self-referencing canonical plus parameters policy**: strip tracking parameters in the canonical; keep functional ones (page, variant) only when they produce distinct content.
- **Sitemap segmentation**: split by type (products, articles) so Search Console reports coverage per section; use a sitemap index; set `lastmod` only from real content changes.
- **Hub and spoke internal linking**: topic hubs link to detail pages with descriptive anchor text; breadcrumbs mirror the URL hierarchy.
- **Site-wide entity graph**: Organization and WebSite nodes defined once with stable `@id`s; page nodes reference them by `@id`.
- **Redirect map as data**: a tested table of old to new URLs, applied at the edge, with loop and chain checks in CI.
- **Preview protection**: non-production hosts return `X-Robots-Tag: noindex` and sit behind authentication.
- Deep dives: [references/crawling-and-indexing.md](references/crawling-and-indexing.md), [references/javascript-rendering.md](references/javascript-rendering.md), [references/schema-org.md](references/schema-org.md), [references/structured-data.md](references/structured-data.md).

## 8. Best Practices

- One preferred hostname and scheme (HTTPS) enforced by a single 301.
- Keep indexable pages in the sitemap and non-indexable ones out; keep sitemap and canonical consistent.
- Descriptive, unique `<title>` and meta description per page; one `<h1>`; meaningful `alt`; descriptive link text.
- Internal links are `<a href>` with real URLs; no fragment-only routing for indexable content.
- Use `rel="nofollow"`, `ugc` or `sponsored` for untrusted or paid links.
- Mobile and desktop versions serve equivalent content (Google indexes the mobile version).
- Tell search engines about changes: sitemaps and accurate `lastmod` for all engines; IndexNow for participating engines; Search Console URL Inspection sparingly for single critical URLs.
- Keep a changelog of SEO-relevant releases to correlate with Search Console trends.

## 9. Performance

- Server speed affects crawl rate: fast, stable responses let crawlers fetch more; frequent 5xx or timeouts reduce crawling.
- Use conditional requests (`ETag`, `Last-Modified`) so crawlers receive 304 for unchanged pages.
- Do not block CSS, JavaScript or images needed for rendering in robots.txt.
- Keep HTML response size modest; critical content and links should appear early in the document (Googlebot processes a limited number of bytes per file).
- Page experience metrics live in core-web-vitals-expert; check them separately in Search Console's Core Web Vitals report.
- Cache sitemap generation and robots.txt at the edge with a short TTL.

## 10. Security

- Escape JSON-LD when embedding it in HTML: replace `<` with `\u003c` (and `>`, `&`, U+2028, U+2029) after `JSON.stringify`, so a string like `</script><script>...` cannot break out of the script element.
- JSON-LD in `<script type="application/ld+json">` is a data block that browsers do not execute, so a Content Security Policy `script-src` does not need `'unsafe-inline'` for it. Scripts that inject JSON-LD at runtime are executable and need a nonce or hash; prefer server-rendered JSON-LD.
- Never build canonical, hreflang or sitemap URLs from the raw `Host` header or request URL; use a configured site origin or an allowlist to prevent cache poisoning and spoofed canonicals.
- Open redirect endpoints get indexed and abused; validate redirect targets against an allowlist.
- robots.txt reveals paths. Do not list secret or admin URLs by name; protect them with authentication.
- Protect staging and preview environments with authentication and `X-Robots-Tag: noindex`, not only robots.txt.
- User-generated links and content: `rel="ugc nofollow"`, moderation, and no user-controlled markup in head tags.
- Verify Googlebot by reverse DNS plus forward confirmation or Google's published IP ranges; the user agent string alone is spoofable.

## 11. Testing

- HTTP checks: `curl -sI -L https://example.com/old` for status chain and final URL; `curl -s https://example.com/robots.txt`.
- robots.txt: test with a parser that implements RFC 9309 longest-match (for example Google's open-source `robotstxt` library) and Search Console's robots.txt report; Python's `urllib.robotparser` uses different matching and can disagree.
- Rendering: URL Inspection live test, view rendered HTML and screenshot; compare with raw HTML (`curl`) to see what depends on JavaScript.
- Automated head tests (Playwright): canonical equals expected absolute URL, one robots meta, hreflang return links, no `noindex` on production templates.
- Structured data: parse every `script[type="application/ld+json"]`, assert it is valid JSON, has `@context`, expected `@type`s and required properties, and that text values appear in visible content; run the Rich Results Test and Schema Markup Validator on sample URLs.
- Sitemap script: fetch each URL, require status 200, no redirect, self-canonical, no `noindex`.
- Crawl a staging build with a crawler (Screaming Frog, Sitebulb or a custom script) before launch and diff against production after migrations.

## 12. Review Checklist

- [ ] robots.txt reachable with 200; groups reviewed for longest-match behavior; sitemap line present; nothing needed for rendering is blocked.
- [ ] No important page has `noindex`; no staging or private page lacks it.
- [ ] Canonical is absolute, self-referencing where appropriate, consistent with redirects and sitemap.
- [ ] hreflang pairs reciprocal, with self reference and `x-default`.
- [ ] Sitemap contains only canonical 200 indexable URLs, under size limits, with real `lastmod`.
- [ ] Redirects are single-hop 301/308; no chains or loops; 404/410 are real status codes.
- [ ] Indexable content and links exist in server-rendered HTML.
- [ ] JSON-LD valid, matches visible content, escaped safely, no fabricated ratings.
- [ ] Search Console property verified (domain property); sitemap submitted.

## 13. Production Notes

- Indexing takes days to weeks; do not judge a change within hours. Rankings can move after a migration for weeks.
- "Crawled - currently not indexed" and "Discovered - currently not indexed" usually indicate quality, duplication or low demand signals, not a technical block.
- "Duplicate, Google chose different canonical than user" means signals disagree; align redirects, internal links, canonicals and sitemap.
- During outages return 503 with `Retry-After`; prolonged 5xx on robots.txt halts crawling of the whole host.
- Google reported retiring several structured data features during 2025 and 2026 (HowTo, FAQ and others); the markup stays valid Schema.org but yields no rich result. Check the Search Central structured data gallery before promising a feature.
- The Search Console robots.txt report replaced the older tester; changes to robots.txt are picked up on the next fetch of the file.
- Bing Webmaster Tools has its own diagnostics and supports IndexNow; Google does not support IndexNow.

## 14. Examples

robots.txt with correct longest-match behavior:

```
# Rules for all crawlers
User-agent: *
Disallow: /admin/
Allow: /admin/help/
Disallow: /cart
Disallow: /search
Disallow: /*?sessionid=
Disallow: /*.pdf$

# AI training opt-out token example (check each vendor's current token)
User-agent: Google-Extended
Disallow: /

Sitemap: https://www.example.com/sitemap.xml
```

How it is evaluated: `/admin/help/page` matches `Disallow: /admin/` (7 characters) and `Allow: /admin/help/` (12 characters); the longer rule wins, so it is allowed. `/admin/users` matches only the Disallow. If an `Allow` and a `Disallow` match with equal length, the `Allow` wins. An empty `Disallow:` means allow everything. A bot-specific group replaces the `*` group for that bot: adding `User-agent: Googlebot` with `Allow: /` would exempt Googlebot from every rule above, so repeat the shared rules in each group.

Safe JSON-LD serialization and page output (TypeScript, React or any server renderer):

```ts
import type {Product, WithContext} from 'schema-dts';

export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

export function productJsonLd(p: {name: string; url: string; image: string; sku: string;
  price: string; currency: string; inStock: boolean}): WithContext<Product> {
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${p.url}#product`,
    name: p.name,
    image: [p.image],
    sku: p.sku,
    offers: {
      '@type': 'Offer',
      url: p.url,
      price: p.price,
      priceCurrency: p.currency,
      availability: p.inStock ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
    },
  };
}

// In a React server component:
// <script type="application/ld+json"
//   dangerouslySetInnerHTML={{__html: serializeJsonLd(productJsonLd(product))}} />
```

Escaped sequences such as `\u003c` are valid JSON, so parsers read the original characters back. If a content security policy is in force, the data block needs no `unsafe-inline`; give executable scripts a per-request nonce, for example `script-src 'nonce-<random>' 'strict-dynamic'; object-src 'none'; base-uri 'none'`.

Next.js metadata with canonical, hreflang and robots:

```ts
// app/[locale]/products/[slug]/page.tsx
import type {Metadata} from 'next';

const ORIGIN = 'https://www.example.com';

export async function generateMetadata(
  {params}: {params: Promise<{locale: string; slug: string}>},
): Promise<Metadata> {
  const {locale, slug} = await params;
  const path = `/products/${slug}`;
  return {
    title: 'Product name | Example',
    description: 'One sentence that matches the page content.',
    alternates: {
      canonical: `${ORIGIN}/${locale}${path}`,
      languages: {
        'en-GB': `${ORIGIN}/en-gb${path}`,
        'de-DE': `${ORIGIN}/de-de${path}`,
        'x-default': `${ORIGIN}/en-gb${path}`,
      },
    },
    robots: {index: true, follow: true},
  };
}
```

## 15. Common Mistakes

- **Blocking a URL in robots.txt to deindex it**: the crawler cannot see `noindex`, and the URL can still appear without a snippet. Allow crawling and use `noindex`.
- **`noindex` in robots.txt**: not supported by Google since 2019. Use meta robots or `X-Robots-Tag`.
- **A bot-specific group that drops the shared rules**: `User-agent: Googlebot` with only `Allow: /` ignores every `Disallow` in the `*` group. Repeat the rules in each group.
- **Assuming rule order matters**: Google evaluates by longest match, not top to bottom; other parsers may differ, so keep rules unambiguous.
- **Canonical to another page plus `noindex`**: contradictory signals. Pick one intent.
- **Canonical pointing at page 1 from paginated pages**: hides the content of later pages. Self-canonicalize each page.
- **Redirect chains and temporary redirects for permanent moves**: use a single 301/308.
- **Soft 404s**: a 200 status on "not found" or empty pages. Return 404 or 410.
- **Client-only routing with `#` fragments or `onClick` links**: crawlers follow `<a href>` URLs.
- **`noindex` removed by JavaScript**: if the initial HTML has `noindex`, rendering may be skipped. Put the correct robots directive in the initial HTML.
- **Sitemap listing redirected, blocked or non-canonical URLs**: dilutes trust. List final canonical URLs only.
- **Assuming priority and changefreq are used**: Google ignores both; keep `lastmod` honest.
- **`unsafe-inline` CSP or unescaped `JSON.stringify` for JSON-LD**: the first weakens the policy unnecessarily, the second allows `</script>` breakout. Use a data block and escape `<`.
- **Markup for content that is not on the page, or invented ratings**: violates guidelines and risks manual actions.
- **Expecting FAQ or HowTo rich results**: these features were retired in Google Search; the markup no longer produces them.

## 16. References

- [references/crawling-and-indexing.md](references/crawling-and-indexing.md): robots.txt syntax and precedence, meta robots, canonicals, hreflang, sitemaps, redirects, pagination, faceted navigation, Search Console, IndexNow, log analysis, migrations.
- [references/javascript-rendering.md](references/javascript-rendering.md): SSR/SSG/ISR choices, how Googlebot renders, common JavaScript SEO failures, soft 404s in SPAs, testing rendered output.
- [references/schema-org.md](references/schema-org.md): absorbed schema-org-expert: Schema.org vocabulary, JSON-LD syntax, `@id` and `@graph` entity modeling, common types, schema-dts builders.
- [references/structured-data.md](references/structured-data.md): absorbed structured-data-expert: Google rich result eligibility and retired features, required properties, safe implementation, validation, CI tests, monitoring.
- Official docs: https://developers.google.com/search/docs/crawling-indexing/robots/intro , https://www.rfc-editor.org/rfc/rfc9309 , https://www.sitemaps.org/protocol.html , https://schema.org/docs/documents.html , https://developers.google.com/search/docs/appearance/structured-data/search-gallery , https://www.indexnow.org/documentation , https://nextjs.org/docs/app/api-reference/file-conventions/metadata
