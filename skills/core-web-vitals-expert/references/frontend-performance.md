# Frontend Performance

General frontend performance beyond a single metric: delivery, resource priorities, images, fonts, CSS, JavaScript, third-party code, caching, bfcache, speculative navigation and rendering cost. This file absorbs the former performance-expert skill. Verified against MDN browser-compat-data 8.1.7, Next.js 16 image docs and the web-vitals 6.2.3 and Lighthouse 13.6.0 documentation (2026-10).

## 1. Document delivery and TTFB

- Every redirect adds a round trip before the HTML request. Link directly to the final URL (canonical host, scheme and trailing-slash form).
- Serve HTML from a CDN or edge cache where content allows; use `stale-while-revalidate` for pages that tolerate brief staleness.
- Use HTTP/2 or HTTP/3 and TLS session resumption. Do not shard domains.
- Compress text responses. Brotli is universal; zstd is supported by Chrome 123+, Firefox 126+ and Safari 26.3+. Negotiate through `Accept-Encoding` and keep a fallback.
- Stream HTML (server-side streaming, `<Suspense>` boundaries) so the head and above-the-fold content are sent before slow data resolves.
- 103 Early Hints lets the server send `Link: rel=preload` and `rel=preconnect` before the final response (Chrome 103+, Firefox 120+, Safari 17+).

```http
HTTP/1.1 103 Early Hints
Link: </assets/app.4f3a9c.css>; rel=preload; as=style
Link: <https://cdn.example.com>; rel=preconnect
```

## 2. Resource hints and priorities

| Hint | Use for | Notes |
|---|---|---|
| `fetchpriority="high"` or `"low"` on `<img>`, `<link>`, `<script>` | Raise the LCP image; lower below-the-fold or non-critical resources | Chrome 101+, Firefox 132+, Safari 17.2+. A hint, not a command |
| `<link rel="preload" as="...">` | Late-discovered critical resources: CSS background LCP image, font files, a module needed at start | Wrong or unused preloads waste bandwidth; `as` and `crossorigin` must match the later request |
| `<link rel="modulepreload">` | ES modules and their dependencies on the critical path | |
| `<link rel="preconnect">` | Critical third-party origins (CDN, API) | Keep to a few; each holds a socket. Add `crossorigin` for fonts and CORS fetches |
| `<link rel="dns-prefetch">` | Less critical origins | Cheap fallback |
| `<link rel="prefetch">` | Next-page resources at idle priority | Superseded by speculation rules on Chromium |

- Images already in the initial HTML do not need a preload; `fetchpriority="high"` on the `<img>` is enough.
- Preloading a responsive image needs `imagesrcset` and `imagesizes` so the browser picks the same candidate as the `<img>`.
- Check the Network panel priority column and the request waterfall: the LCP resource should start in the first few requests.

## 3. Images

- Formats: AVIF (Chrome 85+, Firefox 93+, Safari 16.4+) and WebP (all current browsers) with a JPEG or PNG fallback through `<picture>`. JPEG XL support is partial and not on a standards track at this version of the compat data; check current support before using it.
- Size for the layout, not the source: `srcset` with width descriptors and an accurate `sizes` attribute. An inaccurate `sizes` makes browsers download too much.
- Set intrinsic `width` and `height` on every image; CSS `height: auto` keeps responsiveness while the browser reserves the ratio.
- `loading="lazy"` for offscreen images and iframes (Chrome 77+, Firefox 75+, Safari 15.4+); `decoding="async"` for non-critical images. Do not lazy-load the LCP image.
- Resize and convert at build time or at a CDN image service; do not ship originals. Strip metadata.
- Animated GIFs: replace with muted, looping `<video playsinline>` (WebM or MP4), and `preload="none"` plus a `poster` for non-critical video.
- Next.js 16: the `priority` prop of `next/image` is deprecated in favor of `preload`; the docs advise `loading="eager"` or `fetchPriority="high"` in most cases and reserve `preload` for images that must be preloaded from the head.

```html
<picture>
  <source type="image/avif" srcset="/img/card-400.avif 400w, /img/card-800.avif 800w" sizes="(min-width: 800px) 400px, 100vw">
  <source type="image/webp" srcset="/img/card-400.webp 400w, /img/card-800.webp 800w" sizes="(min-width: 800px) 400px, 100vw">
  <img src="/img/card-800.jpg" width="800" height="500" loading="lazy" decoding="async" alt="Team at the offsite">
</picture>
```

## 4. Fonts

- Self-host WOFF2 and subset to the needed character ranges; variable fonts replace several static files.
- `font-display: swap` shows fallback text immediately; `optional` avoids late swaps (and the shift) at the cost of sometimes keeping the fallback. Avoid `block`.
- Preload only the font files used by above-the-fold text, with `crossorigin` even for same-origin files.
- Reduce the swap shift by tuning the fallback face (`size-adjust` in all current browsers; `ascent-override` and `descent-override` in Chrome, Edge and Firefox):

```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;
}
@font-face {
  font-family: "Inter Fallback";
  src: local("Arial");
  size-adjust: 107%;
  ascent-override: 90%;
  descent-override: 22%;
  line-gap-override: 0%;
}
body { font-family: "Inter", "Inter Fallback", sans-serif; }
```

The override percentages depend on the font pair; generate them with a tool (for example the Next.js font system or Capsize) instead of guessing.

## 5. CSS

- Inline only the critical CSS needed for first paint (a few KB); load the rest with normal `<link>` tags. CSS is render-blocking by design; keep the blocking payload small.
- Avoid `@import` chains; they serialize downloads.
- `content-visibility: auto` with `contain-intrinsic-size` skips rendering of offscreen sections (Chrome 85+, Firefox 125+, Safari 18+). Reserve a realistic size to avoid scrollbar jumps.
- Prefer `aspect-ratio` over padding hacks; keep selectors cheap and DOM depth moderate.
- Use `@media` or `media` attributes to avoid blocking on print or large-screen-only styles.

## 6. JavaScript

- Budget: track compressed JS per route. Set the limit from field data for your slowest cohort (mid-range mobile) and tighten it over time.
- Split by route, then by interaction (`import()` on click or hover), then by visibility. Keep shared chunks stable for caching.
- Tree-shake: ESM dependencies, `sideEffects: false` where true, no barrel files that defeat shaking, avoid whole-library imports (`import _ from "lodash"`).
- Target modern browsers; do not ship transpilation and polyfills that Baseline features make unnecessary. Lighthouse 13 reports legacy JavaScript in the insights.
- Hydration cost: server-render, then hydrate only interactive islands or use server components so static content ships no JavaScript.
- Move CPU-heavy work (parsing, image processing, search indexing) to a Web Worker; pass results back with `postMessage`. Transfer large buffers instead of copying.
- Script loading: `defer` keeps order and runs after parsing; `async` runs when ready and can run any time; module scripts are deferred. Inline scripts that block parsing should be tiny.
- Do not poll in `setInterval` loops while the page is hidden; pause on `visibilitychange`.

## 7. Third-party scripts

- Inventory every tag: owner, purpose, bytes, long tasks (LoAF `scripts[]` shows script URLs and durations). Remove the unowned ones.
- Load after the primary content: `async`/`defer`, or on interaction or idle. Consent managers should gate tags that need consent.
- Facades for heavy embeds: show a poster and a button, load the player on click (see the pattern below).
- Self-host stable static scripts only when licensing allows and updates are tracked; always apply `integrity` to static third-party files.
- `<iframe loading="lazy" sandbox>` for embeds that do not need full access; add only the required sandbox tokens.
- Tag managers hide cost: review the container as code, not as a black box.

```html
<div class="video-facade" data-embed="https://www.youtube-nocookie.com/embed/VIDEO_ID?autoplay=1">
  <img src="/img/video-poster.webp" width="640" height="360" loading="lazy" alt="Video: product tour">
  <button type="button" aria-label="Play video: product tour">Play</button>
</div>
<script type="module">
  for (const el of document.querySelectorAll('.video-facade')) {
    el.querySelector('button').addEventListener('click', () => {
      const frame = document.createElement('iframe');
      frame.src = el.dataset.embed;
      frame.allow = 'autoplay; encrypted-media';
      frame.allowFullscreen = true;
      frame.title = 'Product tour';
      el.replaceChildren(frame);
    }, {once: true});
  }
</script>
```

## 8. Caching and compression

| Resource | Header |
|---|---|
| Hashed static assets (JS, CSS, fonts, images with hash in name) | `Cache-Control: public, max-age=31536000, immutable` |
| HTML | `Cache-Control: no-cache` (revalidate) or `s-maxage=60, stale-while-revalidate=300` at the CDN |
| API responses for public data | Short `max-age` plus `ETag`; `Vary` only on headers that really change the body |
| Personalized or authenticated responses | `Cache-Control: private` or `no-store`; never cacheable by shared caches |

- Use `ETag` or `Last-Modified` so revalidation costs a 304, not a full download.
- Service workers: cache-first for the app shell and hashed assets, network-first or stale-while-revalidate for content; version the cache and delete old ones on activate.
- A purge strategy matters as much as TTLs: deploy assets first, then HTML that references them.

## 9. Back/forward cache

- bfcache restores a page instantly on back/forward navigation. Pages restored from it report LCP, CLS and INP again and web-vitals reports them with `navigationType: "back-forward-cache"`.
- Blockers: `unload` listeners (in several browsers), open connections or locks at `pagehide`, `Cache-Control: no-store` on the main document in browsers that treat it as a blocker, and pages opened with a retained `window.opener` relationship.
- Use `pagehide` and `visibilitychange` instead of `unload`; reconnect WebSockets and refresh stale data on `pageshow` when `event.persisted` is true.
- Diagnose in DevTools (Application, Back/forward cache) and with `performance.getEntriesByType("navigation")[0].notRestoredReasons` (Chromium).

```js
addEventListener('pageshow', (event) => {
  if (event.persisted) {
    refreshSessionState(); // data may be stale after a long time in bfcache
  }
});
```

## 10. Speculation rules

Speculation rules prefetch or prerender likely next pages. They work in Chromium-based browsers (Chrome and Edge 109+); other browsers ignore the script, so use them as progressive enhancement.

```html
<script type="speculationrules">
{
  "prerender": [
    {
      "where": {
        "and": [
          {"href_matches": "/*"},
          {"not": {"href_matches": "/logout"}},
          {"not": {"selector_matches": "[rel~=nofollow]"}}
        ]
      },
      "eagerness": "moderate"
    }
  ]
}
</script>
```

- `eagerness`: `immediate`, `eager`, `moderate` (typically on hover or focus), `conservative` (pointer down). Start with `moderate` for prerender and `conservative` or `moderate` for prefetch.
- Exclude URLs with side effects, per-user state or heavy server cost. Prerendering runs the page's JavaScript, so guard analytics and ads with `document.prerendering` and the `prerenderingchange` event.
- With a Content Security Policy, inline rules need a nonce or hash on the script (or the `inline-speculation-rules` source keyword); alternatively serve rules from a file referenced by the `Speculation-Rules` response header. Check the current docs for exact CSP behavior.
- Measure with the `navigationType` value `prerender` in web-vitals and Chrome DevTools Application, Speculative loads.

## 11. Rendering and animation

- Animate `transform`, `opacity` and (where supported) `filter` on the compositor; do not animate layout properties.
- Batch DOM reads before writes; interleaving forces synchronous layout (visible as `forcedStyleAndLayoutDuration` in LoAF script entries).
- Use `requestAnimationFrame` for visual work, `IntersectionObserver` instead of scroll polling, and `ResizeObserver` instead of window resize polling.
- Virtualize long lists (windowing with a library such as TanStack Virtual) or use `content-visibility: auto`; keep list items cheap.
- Use `will-change` sparingly and remove it after the animation; each promoted layer costs memory.
- View Transitions (Chrome 111+, Firefox 144+, Safari 18) give animated navigation without layout thrash; check the user's `prefers-reduced-motion`.

## 12. Budgets and guardrails

- Define budgets by route: LCP/INP/CLS at p75, compressed JS and CSS size, image bytes, request count, third-party bytes.
- Enforce metric budgets with Lighthouse assertions and size budgets with the bundler or a script; fail CI on regressions.
- Review the budget when a new dependency or tag is added; budgets without owners decay.
- Keep a performance changelog next to deploys so metric movements in RUM can be tied to releases.
