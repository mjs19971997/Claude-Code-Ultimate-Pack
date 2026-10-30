# JavaScript Rendering and SEO

How search engines process JavaScript-driven sites and which rendering strategy to choose: SSR, SSG, ISR, client-side rendering and hydration, common failure modes, SPA status codes, and how to test what crawlers see. Verified against Google Search Central guidance as summarized by secondary sources, Next.js 16 metadata docs and MDN browser-compat-data 8.1.7 (2026-10). Check the current Google JavaScript SEO documentation for exact limits.

## 1. How Google processes JavaScript pages

1. Crawl: Googlebot fetches the URL (subject to robots.txt) and receives the HTML response.
2. Initial indexing signals: links, canonical, robots meta, status code and any content in the raw HTML are extracted.
3. Render: pages are queued for rendering in an evergreen headless Chromium that executes JavaScript, with a limited time budget. Rendering may happen seconds to much later than the crawl.
4. Index: the rendered DOM is used to update indexed content, links and structured data.

Consequences:

- Content and links in the raw HTML are processed first and most reliably. Content that exists only after JavaScript runs is indexed later and can be missed on errors or timeouts.
- If the raw HTML contains `noindex`, rendering may be skipped, so JavaScript cannot remove it.
- Googlebot does not click, scroll, hover or fill forms. Content must appear without interaction (tabs and accordions are fine if the content is in the DOM at load).
- Each page is rendered statelessly: no cookies, local storage or sessions carry over, and permissions are not granted.
- Resources (JavaScript, CSS, API calls) blocked by robots.txt or failing to load prevent correct rendering. Fetch limits per file apply (Googlebot processes the first 2 MB of an HTML file, check the current docs).
- Other search engines and many AI crawlers render JavaScript less capably or not at all; do not assume they execute it. Check each vendor's documentation.

## 2. Rendering strategies

| Strategy | SEO view | Use for |
|---|---|---|
| SSG (static generation at build) | Best: complete HTML, fast, cacheable | Docs, blogs, marketing pages, catalogs that change per deploy |
| ISR / revalidation | Static HTML refreshed on a schedule or on demand | Large catalogs, articles with periodic updates |
| SSR (per request) | Complete HTML, depends on server speed | Personalized-or-fresh public pages, search results that must be indexed |
| Streaming SSR | Complete HTML delivered progressively; ensure critical content and links arrive in the first chunks | Pages with slow data sections |
| Hybrid / islands / server components | Static or server-rendered content with small interactive JavaScript | Content sites with widgets |
| CSR (client-side rendering) | Content depends on rendering; acceptable only for non-indexable areas | Authenticated dashboards, tools |
| Dynamic rendering (serving bots pre-rendered HTML) | A workaround that Google no longer recommends for new work | Legacy sites during migration |

Choose SSG or ISR when content is the same for every user; SSR when it must be fresh; CSR only when indexing does not matter.

## 3. Common failure modes

- Navigation implemented with `onClick` handlers, `<div>` or `<span>` elements, or `javascript:` URLs: crawlers follow `<a href>` with real URLs. Provide an `href` even if JavaScript intercepts the click.
- Hash-based routing (`/#/products/1`): fragments are not treated as separate URLs. Use the History API with real paths.
- Titles, meta descriptions, canonicals and structured data injected late by JavaScript, or different between raw HTML and rendered DOM: render them on the server, and make sure the canonical in raw HTML equals the one after rendering (conflicting canonicals are ignored or cause the wrong URL to be chosen).
- Lazy-loaded content that waits for scroll events: use `IntersectionObserver` or native `loading="lazy"`, and make sure important text is not gated behind scroll or click.
- Infinite scroll without paginated URLs: add crawlable pagination links.
- Content loaded from an API that blocks crawlers (authentication, CORS issues, rate limiting by user agent, robots.txt disallow on the API path).
- Interstitials, cookie walls or geolocation redirects that block content for crawlers without cookies.
- Service-worker-only rendering or content that needs permissions (geolocation, notifications).
- Client-side redirects as the only redirect mechanism; use HTTP redirects where possible.
- Very large HTML or JavaScript bundles that render slowly or exceed fetch limits.
- Soft 404s in SPAs (next section).

## 4. Status codes and error pages in SPAs

A single-page app typically returns 200 for every path. Search engines then index "not found" screens as soft 404s. Fixes:

- Preferred: have the server or edge return the real status (404 for unknown routes, 410 for removed items, 301 for moved items) before the client app loads. Frameworks with SSR do this by route.
- If the app cannot return the status: when a route resolves to "not found", redirect with JavaScript to a URL that returns a real 404, or inject `<meta name="robots" content="noindex">` for that view (remember that a `noindex` added by JavaScript works only if the page is rendered).
- Return 5xx or 503 for server errors, not a 200 error screen.

## 5. Head management

- Frameworks: Next.js `metadata` / `generateMetadata` (title, description, `alternates.canonical`, `alternates.languages`, `robots`) render in the initial HTML on the server. React 19 hoists `<title>`, `<meta>` and `<link>` rendered by components into `<head>`; with server rendering they appear in the HTML response.
- Keep one source of truth for the URL (`absoluteUrl()` helper) so canonical, Open Graph URL, hreflang and sitemap agree.
- Set `<html lang>` correctly for each locale.
- Avoid client-only head libraries for indexable pages unless rendering is server-side.

```tsx
// app/products/[slug]/page.tsx (Next.js, server component)
import type {Metadata} from 'next';
import {notFound} from 'next/navigation';

export async function generateMetadata(
  {params}: {params: Promise<{slug: string}>},
): Promise<Metadata> {
  const {slug} = await params;
  const product = await getProduct(slug);
  if (!product) return {robots: {index: false}};
  return {
    title: product.name,
    description: product.summary,
    alternates: {canonical: `https://www.example.com/products/${slug}`},
  };
}

export default async function Page({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  const product = await getProduct(slug);
  if (!product) notFound();      // responds with HTTP 404, not a 200 "not found" screen
  return <h1>{product.name}</h1>;
}
```

## 6. Testing what crawlers see

1. Raw HTML: `curl -s https://www.example.com/page | head -c 20000`, check title, canonical, robots meta, main content and links exist before JavaScript runs.
2. Rendered HTML: Search Console URL Inspection, live test, "View tested page" for HTML and screenshot; compare with the raw response.
3. JavaScript disabled in an automated test:

```ts
import {test, expect} from '@playwright/test';

test('indexable content and head tags exist without JavaScript', async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled: false});
  const page = await context.newPage();
  await page.goto('https://staging.example.com/products/example');

  await expect(page.locator('h1')).toHaveText('Example product');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://www.example.com/products/example');
  await expect(page.locator('a[href^="/products/"]').first()).toBeVisible();

  const robots = await page.locator('meta[name="robots"]').getAttribute('content');
  expect(robots ?? '').not.toContain('noindex');
  await context.close();
});
```

4. Crawl with a JavaScript-capable crawler and diff raw vs rendered text and links; large differences identify render-dependent templates.
5. Check the Crawl stats and Page indexing reports for "Crawled - currently not indexed" on JavaScript templates.
6. Check server logs for crawler requests to API endpoints and static bundles returning errors.

## 7. Performance and rendering cost

- Faster pages are cheaper to render and crawl. Reduce JavaScript, avoid long chains of dependent fetches, and cache API responses at the edge.
- Core Web Vitals and speed work is covered in core-web-vitals-expert; use the same RUM data to find slow templates.
- Keep critical content and the main navigation near the top of the HTML so they are within fetch limits even for large documents.
