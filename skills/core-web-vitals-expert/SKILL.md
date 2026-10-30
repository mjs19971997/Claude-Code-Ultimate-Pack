---
name: core-web-vitals-expert
description: >-
  Measures and improves web performance with Core Web Vitals (LCP, INP, CLS) using field data (CrUX, web-vitals attribution build) and lab tools (Lighthouse, DevTools), and fixes the causes: LCP image discovery and fetchpriority, long tasks and scheduler.yield, layout shifts, fonts, bundles, caching, third-party scripts, bfcache and speculation rules. Absorbs the former performance-expert skill. Use when a page fails Core Web Vitals, INP or LCP regress, Lighthouse or PageSpeed Insights reports problems, or a performance budget or RUM pipeline is needed. Not for crawling, indexing or structured data (use technical-seo-expert), React rendering patterns (use senior-react-19-engineer), or server scaling (use scalability-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Core Web Vitals Expert

This skill covers measuring and improving user-perceived web performance: the three Core Web Vitals (LCP, INP, CLS), the field and lab tools that report them, and the frontend techniques that move them. It absorbs the former performance-expert skill; general frontend performance (images, fonts, JavaScript, caching, third parties, navigation speed) lives in a dedicated reference, as do INP debugging, measurement and LCP/CLS diagnosis.

> Verified against web-vitals 6.2.3, Lighthouse 13.6.0 (Node 22.19 or newer), Chrome UX Report (28-day rolling field data), MDN browser-compat-data 8.1.7 and Next.js 16 image docs (2026-10).

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

- Covered: Core Web Vitals definitions, thresholds and measurement; CrUX, PageSpeed Insights, Search Console reports, Lighthouse and DevTools; the web-vitals library and attribution; Long Animation Frames; resource hints, `fetchpriority`, image and font delivery; JavaScript cost, code splitting and third-party scripts; caching and compression; bfcache and speculation rules; performance budgets in CI.
- Not covered: crawl and index control, sitemaps and structured data (technical-seo-expert); component-level React rendering and Suspense design (senior-react-19-engineer); horizontal scaling and database tuning (scalability-expert); CSS architecture (tailwindcss-master).

## 2. Core Expertise

| Metric | Measures | Good (p75) | Poor | Notes |
|---|---|---|---|---|
| LCP | When the largest image or text block in the viewport is rendered | 2.5 s or less | over 4 s | Four parts: TTFB, resource load delay, resource load duration, element render delay |
| INP | Latency of the slowest typical interaction over the visit (click, tap, key) | 200 ms or less | over 500 ms | Replaced FID as a Core Web Vital in March 2024. Parts: input delay, processing duration, presentation delay |
| CLS | Largest burst of unexpected layout shifts | 0.1 or less | over 0.25 | Shifts within 500 ms of user input do not count |

- A page group passes when the 75th percentile of real visits is "good" for all three metrics. Thresholds also ship in the web-vitals library as `LCPThresholds` (2500, 4000), `INPThresholds` (200, 500) and `CLSThresholds` (0.1, 0.25).
- Field data: CrUX aggregates opted-in Chrome users over a rolling 28-day window at origin and URL level (CrUX API, CrUX History API, BigQuery, CrUX Vis). PageSpeed Insights shows CrUX plus a Lighthouse run; Search Console groups URLs by status.
- Lab data: Lighthouse 13 (insight-based audits; performance score formula unchanged from 12) and DevTools Performance panel. Navigation-mode Lighthouse does not measure INP; Total Blocking Time is the lab proxy.
- Browser APIs: Largest Contentful Paint and Event Timing work in Chrome, Firefox and Safari 26.2+; Layout Instability (CLS) and Long Animation Frames (LoAF, Chrome 123+) are Chromium-only, so CLS and LoAF data come from Chromium visits.
- web-vitals 6: `onLCP`, `onINP`, `onCLS`, `onFCP`, `onTTFB`; import from `web-vitals/attribution` for diagnostic fields; optional soft-navigation reporting in Chromium 151+.

## 3. Workflow

1. Establish the baseline from field data: CrUX or Search Console for the origin, then PageSpeed Insights per URL template. Identify the failing metric and device class (mobile usually fails first).
2. Reproduce in the lab with throttling (DevTools or Lighthouse) on the failing template. Treat lab as diagnosis, field as the verdict.
3. Attribute the cause. LCP: which element, which of the four parts is largest. INP: which interaction, which of the three parts, which script (LoAF). CLS: which element shifted and why.
4. Fix the largest part first (see decision rules), change one thing at a time, and keep the diff small enough to attribute.
5. Add RUM with the attribution build so the field confirms the fix (28 days to fully reflect it in CrUX; RUM shows it within days).
6. Lock the gain: performance budgets and Lighthouse assertions in CI, bundle-size checks, alerting on RUM p75.

## 4. Decision Rules

- LCP dominated by TTFB: fix server, CDN caching, redirects, Early Hints (`103`), not images.
- LCP dominated by resource load delay: the image is discovered late (CSS background, JS-rendered, lazy-loaded). Put an `<img>` in the initial HTML with `fetchpriority="high"`, or add a preload when it cannot be in markup.
- LCP dominated by resource load duration: smaller bytes (AVIF or WebP, correct `srcset`/`sizes`), CDN, `Cache-Control`.
- LCP dominated by element render delay: render-blocking CSS or JS, client-side rendering, a font that blocks text LCP.
- INP dominated by input delay: long tasks running at interaction time (startup scripts, third parties). Dominated by processing duration: slow handlers; do the minimum, then yield. Dominated by presentation delay: expensive style, layout or paint, huge DOM.
- CLS: reserve space (width/height, `aspect-ratio`, `min-height` for ads and embeds), avoid inserting content above existing content, use `transform` for animation, and match fallback font metrics.
- Use `loading="lazy"` for offscreen images and iframes only; never the LCP image.
- Preconnect only to critical cross-origin hosts (two or three at most); `dns-prefetch` for the rest.
- Use speculation rules for likely next navigations on Chromium; treat them as progressive enhancement.
- Prefer removing or deferring JavaScript over optimizing it. Code splitting by route, then by interaction, then by visibility.
- Prefer the platform: native lazy loading, `content-visibility: auto`, CSS animations on compositor properties, `<dialog>`, and native `<picture>` over libraries.

## 5. Coding Standards

- Every `<img>` and `<video>` has `width` and `height` (or CSS `aspect-ratio`) so space is reserved before load.
- The LCP image is never `loading="lazy"` and not injected by JavaScript; give it `fetchpriority="high"`. Do not mark more than one or two images high priority.
- Scripts: `defer` for application scripts, `async` only for independent scripts, `type="module"` is deferred by default. No synchronous third-party scripts in `<head>`.
- Fonts: self-host WOFF2, `font-display: swap` or `optional`, preload only the one or two files used above the fold (with `crossorigin`), and tune the fallback with `size-adjust`, `ascent-override`, `descent-override`.
- Event handlers do minimal work, then yield with `scheduler.yield()` (feature-detected, with a `setTimeout` fallback). No `isInputPending` (Chromium only, non-standard).
- Passive listeners for scroll and touch handlers that do not call `preventDefault()`.
- Animate `transform` and `opacity`; never animate `top`, `left`, `width`, `height` or `margin`.
- Do not use an `unload` listener; use `pagehide` and `visibilitychange` so pages stay eligible for bfcache.
- RUM code sends data with `navigator.sendBeacon()` or `fetch(..., {keepalive: true})`, strips query strings and fragments, and never sends user identifiers.

## 6. Project Structure

```
.
├── src/
│   ├── perf/
│   │   ├── rum.ts               # web-vitals attribution -> beacon
│   │   └── yield.ts             # yieldToMain() and chunked work helpers
│   └── components/
│       ├── HeroImage.tsx        # responsive picture, fetchpriority, dimensions
│       └── VideoFacade.tsx      # click-to-load embeds
├── public/fonts/                # self-hosted WOFF2
├── lighthouserc.json            # CI assertions on metrics and budgets
├── budgets.json                 # resource-size budgets (Lighthouse format)
└── scripts/
    └── check-bundle-size.mjs    # fails CI when a route chunk exceeds its limit
```

## 7. Design Patterns

- **Discoverable LCP**: LCP image or text in server-rendered HTML; no client-side fetch needed to know what to load.
- **Resource-hint ladder**: `fetchpriority` on the element first, `preload` only for late-discovered resources, `preconnect` for critical origins, `103 Early Hints` for server-known critical resources.
- **Facade**: render a poster and button for video, chat and map embeds; load the third-party code on click or when idle.
- **Yield-in-chunks**: process lists in time-boxed slices, calling `yieldToMain()` between slices so input is handled.
- **Defer non-urgent work**: after the visual update, push analytics, prefetch and state persistence to idle time or `scheduler.postTask` with `background` priority.
- **Route and interaction splitting**: dynamic `import()` on route change, hover or click for heavy widgets (editors, charts).
- **Virtualization**: render only visible rows for long lists; `content-visibility: auto` with `contain-intrinsic-size` for long static pages.
- **Speculative navigation**: speculation rules with `eagerness: "moderate"` for same-origin links.
- **RUM attribution loop**: report metric plus attribution target, group by selector and template, fix the top offender, verify in p75.
- Deep dives: [references/frontend-performance.md](references/frontend-performance.md), [references/inp-optimization.md](references/inp-optimization.md), [references/lcp-and-cls.md](references/lcp-and-cls.md).

## 8. Best Practices

- Segment by device, connection and country; global p75 hides the failing cohort.
- Report p75, not mean or median; Google's assessment and CrUX use the 75th percentile.
- Keep HTML small and streamable; send critical CSS first and avoid blocking scripts before first paint.
- Serve one cacheable, compressed response per asset: Brotli or zstd (zstd: Chrome 123+, Firefox 126+, Safari 26.3+; keep Brotli and gzip fallbacks via `Accept-Encoding` negotiation).
- Use content-hashed filenames with `Cache-Control: public, max-age=31536000, immutable`; HTML gets `no-cache` or a short TTL with revalidation.
- Review third-party tags quarterly; each tag needs an owner, a purpose and a measured cost.
- Test on a mid-range Android profile (4x CPU throttling), not only a developer laptop.
- Keep the DOM small; very large DOMs raise style, layout and presentation delay for every interaction.

## 9. Performance

- Order of leverage for LCP: server response and caching, image discovery and priority, image bytes, render-blocking resources.
- Order of leverage for INP: less JavaScript on the main thread, shorter tasks, cheaper handlers, smaller DOM, then rendering work.
- Order of leverage for CLS: dimensions on media, reserved slots for dynamic content, font metric matching, bfcache-safe animations.
- Bundle size: audit with the bundler analyzer, drop dead dependencies, prefer ESM libraries with tree shaking, ship modern syntax to modern browsers, avoid shipping polyfills Baseline features no longer need.
- Back/forward navigations should be instant through bfcache; remove `unload` handlers, close connections on `pagehide`, and check blockers with the `notRestoredReasons` API (Chromium) or DevTools.
- Prerendered pages count real metrics from activation; guard analytics that assume a visible page load.
- Details and code: [references/frontend-performance.md](references/frontend-performance.md).

## 10. Security

- Third-party scripts run with full page privileges; load only from reviewed origins, pin versions, and use Subresource Integrity (`integrity` plus `crossorigin`) for static CDN files.
- Keep a strict Content Security Policy based on nonces or hashes; do not weaken it to make a performance tag work.
- RUM payloads must not contain personal data: strip query strings and fragments, truncate selectors, never include form values or user IDs.
- Resource hints leak intent: do not preconnect or prefetch URLs that reveal sensitive state (account pages, tokens in query strings).
- Speculation rules prefetch or prerender GET pages; exclude URLs with side effects (logout, cart mutations, one-time links) and authenticated personalized pages unless they are safe to execute early.
- Service workers and edge caches must not cache personalized or authenticated responses under shared keys; use `Cache-Control: private` or `no-store` and correct `Vary`.

## 11. Testing

- Lab: Lighthouse CLI 13 (`npx lighthouse <url> --only-categories=performance --output=json`) with several runs per URL; compare medians, not single runs.
- CI: Lighthouse CI or the Lighthouse CLI with assertions on `largest-contentful-paint`, `cumulative-layout-shift`, `total-blocking-time` and a resource budget. Note: `@lhci/cli` 0.15.1 bundles Lighthouse 12.6.1; check the version your CI actually runs.
- Interaction testing: record the Performance panel while performing the slow interaction (or a DevTools user flow); use "Interactions" and "Long animation frames" tracks.
- E2E: use Playwright to assert that the LCP image is present in the initial HTML, has `fetchpriority="high"`, and is not lazy; and that no unexpected requests precede it.
- Field validation: RUM dashboards at p75 per template, CrUX History API for trend, Search Console Core Web Vitals report for status.
- Regression gate: block merges when a route chunk grows beyond its budget or a metric assertion fails.

## 12. Review Checklist

- [ ] Failing metric and device class identified from field data, not only a lab score.
- [ ] LCP element known; its image is in markup, sized, not lazy, high priority, correctly responsive.
- [ ] No render-blocking third-party scripts; analytics and tags are `async`/`defer` or loaded after interaction.
- [ ] Media and embeds have reserved space; fonts have fallback metric overrides.
- [ ] Event handlers are short; heavy work is chunked or moved to a worker.
- [ ] No `unload` listeners; bfcache eligibility checked.
- [ ] Static assets hashed, compressed and cached; HTML revalidated.
- [ ] RUM sends attribution without personal data; p75 tracked per template.
- [ ] CI enforces a budget; version of Lighthouse in CI is known.

## 13. Production Notes

- CrUX needs enough traffic to report a URL; low-traffic pages fall back to origin-level data in PageSpeed Insights.
- A fix reaches CrUX gradually over the 28-day window; confirm sooner with your own RUM at p75.
- Chrome-only metrics (CLS, LoAF) and iframes cause differences between RUM and CrUX; the web-vitals library cannot see inside iframes, while CrUX includes them.
- Lighthouse scores vary between runs and machines; do not set alerts on a single score. Use metric values and medians.
- Lighthouse 13 removed legacy audits (for example offscreen images, font-size, and several preload audits) in favor of insights; update CI assertions that reference removed audit IDs.
- Soft navigations in single-page apps are reported separately only in Chromium 151+ with web-vitals 6 and `reportSoftNavs`; otherwise the whole session counts toward the initial page.
- Re-check browser support in MDN or caniuse before relying on `scheduler.yield`, speculation rules or LoAF in production logic.

## 14. Examples

LCP image in markup, responsive, sized and prioritized; no preload needed because the browser discovers it in the HTML:

```html
<img
  src="/img/hero-1200.avif"
  srcset="/img/hero-640.avif 640w, /img/hero-1200.avif 1200w, /img/hero-1920.avif 1920w"
  sizes="(min-width: 1200px) 1200px, 100vw"
  width="1200" height="600"
  fetchpriority="high"
  decoding="async"
  alt="Product dashboard overview">
```

When the LCP image can only be found late (CSS background, JavaScript-rendered), preload the responsive set:

```html
<link rel="preload" as="image" fetchpriority="high"
      href="/img/hero-1200.avif"
      imagesrcset="/img/hero-640.avif 640w, /img/hero-1200.avif 1200w, /img/hero-1920.avif 1920w"
      imagesizes="(min-width: 1200px) 1200px, 100vw">
```

Real-user monitoring with the attribution build of web-vitals 6:

```ts
import {onCLS, onINP, onLCP, type MetricWithAttribution} from 'web-vitals/attribution';

const queue: Record<string, unknown>[] = [];

function pageOf(url?: string): string {
  const u = new URL(url ?? location.href);
  return u.origin + u.pathname; // drop query string and fragment
}

function record(metric: MetricWithAttribution): void {
  const base = {
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    id: metric.id,
    navigationType: metric.navigationType,
    page: pageOf(metric.navigationURL),
  };
  switch (metric.name) {
    case 'LCP': {
      const a = metric.attribution;
      queue.push({...base, target: a.target, ttfb: a.timeToFirstByte,
        loadDelay: a.resourceLoadDelay, loadDuration: a.resourceLoadDuration,
        renderDelay: a.elementRenderDelay});
      break;
    }
    case 'INP': {
      const a = metric.attribution;
      queue.push({...base, target: a.interactionTarget, type: a.interactionType,
        inputDelay: a.inputDelay, processing: a.processingDuration,
        presentationDelay: a.presentationDelay, loadState: a.loadState});
      break;
    }
    case 'CLS': {
      const a = metric.attribution;
      queue.push({...base, target: a.largestShiftTarget, shift: a.largestShiftValue});
      break;
    }
    default:
      queue.push(base);
  }
}

function flush(): void {
  if (queue.length === 0) return;
  const body = new Blob([JSON.stringify(queue.splice(0))], {type: 'application/json'});
  navigator.sendBeacon('/rum', body); // same-origin endpoint
}

onLCP(record);
onINP(record);
onCLS(record);
addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flush();
});
addEventListener('pagehide', flush);
```

Yield between slices of work so input and rendering are not starved:

```ts
type Sched = {yield?: () => Promise<void>};

export function yieldToMain(): Promise<void> {
  const s = (globalThis as {scheduler?: Sched}).scheduler;
  if (s?.yield) return s.yield(); // Chrome/Edge 129+, Firefox 142+
  return new Promise((resolve) => setTimeout(resolve, 0));
}

export async function processInSlices<T>(
  items: readonly T[],
  work: (item: T) => void,
  budgetMs = 40,
): Promise<void> {
  let deadline = performance.now() + budgetMs;
  for (const item of items) {
    work(item);
    if (performance.now() >= deadline) {
      await yieldToMain();
      deadline = performance.now() + budgetMs;
    }
  }
}
```

Lighthouse CI assertions (metric IDs are stable across Lighthouse 12 and 13):

```json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:3000/", "http://localhost:3000/products/example"],
      "numberOfRuns": 5,
      "startServerCommand": "npm run start"
    },
    "assert": {
      "assertions": {
        "largest-contentful-paint": ["error", {"maxNumericValue": 2500, "aggregationMethod": "median"}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1, "aggregationMethod": "median"}],
        "total-blocking-time": ["warn", {"maxNumericValue": 300, "aggregationMethod": "median"}]
      }
    }
  }
}
```

## 15. Common Mistakes

- **Optimizing the Lighthouse score only**: lab runs use one device profile; the verdict is field p75. Start from CrUX or RUM.
- **`loading="lazy"` on the hero image**: delays the LCP request until layout. Lazy-load only offscreen images.
- **Missing `width`/`height`**: causes layout shift when the image arrives. Add dimensions or `aspect-ratio`.
- **Preloading everything**: too many high-priority hints compete with the real LCP resource. Hint one or two resources.
- **`fetchpriority="high"` on many images**: removes the signal. Reserve it for the LCP image.
- **`font-display: block` for body text**: invisible text for up to three seconds. Use `swap` or `optional` with metric overrides.
- **Synchronous third-party tags in `<head>`**: block parsing and inflate input delay. Load async, defer to idle, or use a facade.
- **Measuring the mean or median**: the assessment uses the 75th percentile.
- **Treating FID as current**: INP replaced FID in March 2024; FID is no longer a Core Web Vital.
- **Debugging INP from page load only**: INP comes from interactions during the visit; reproduce the slow interaction with the Performance panel or RUM attribution.
- **Calling `scheduler.yield()` unguarded**: Safari has no `scheduler` object; feature-detect and fall back.
- **Using an `unload` listener**: blocks bfcache in several browsers. Use `pagehide`.
- **Animating layout properties**: triggers layout every frame. Use `transform` and `opacity`.
- **Caching personalized HTML at the edge**: serves one user's content to another. Vary or bypass the cache.

## 16. References

- [references/frontend-performance.md](references/frontend-performance.md): absorbed performance-expert content: image formats and responsive images, font loading, JavaScript and bundle size, caching and compression, resource hints, third-party scripts, bfcache, speculation rules, animations and long lists.
- [references/inp-optimization.md](references/inp-optimization.md): INP anatomy, finding the slow interaction, Long Animation Frames, yielding with `scheduler.yield`, workers, rendering cost, framework notes.
- [references/lcp-and-cls.md](references/lcp-and-cls.md): LCP subparts and fixes, TTFB and Early Hints, CLS causes and fixes, fonts and ads, bfcache and prerender effects.
- [references/measurement.md](references/measurement.md): CrUX, PageSpeed Insights, Search Console, Lighthouse 13, web-vitals 6 attribution, RUM pipeline, budgets and CI.
- Official docs: https://web.dev/articles/vitals , https://github.com/GoogleChrome/web-vitals , https://developer.chrome.com/docs/lighthouse/overview , https://developer.chrome.com/docs/crux , https://developer.chrome.com/docs/web-platform/long-animation-frames
