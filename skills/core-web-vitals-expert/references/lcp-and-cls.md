# LCP and CLS

Diagnosing and fixing Largest Contentful Paint and Cumulative Layout Shift: subpart breakdown, the usual causes, concrete fixes, and the effect of fonts, ads, bfcache and prerendering. Verified against web-vitals 6.2.3 attribution fields, Lighthouse 13.6.0 and the web.dev optimize-LCP and optimize-CLS guidance (2026-10).

## 1. LCP: what is measured

- The LCP element is the largest image, video poster, element with a CSS `url()` background image, or block of text visible in the viewport during load. It can change while the page loads; the last candidate before user input wins.
- Good is 2.5 s or less at p75, poor is over 4 s.
- Identify the element type first (image or text); the fixes differ.
- The web-vitals attribution build splits LCP into four parts:

| Part | Attribution field | Target share of LCP |
|---|---|---|
| Time to first byte | `timeToFirstByte` | about 40% |
| Resource load delay | `resourceLoadDelay` | under 10% |
| Resource load duration | `resourceLoadDuration` | about 40% |
| Element render delay | `elementRenderDelay` | under 10% |

Fix the part that is furthest above its share. A text LCP has no resource load parts.

## 2. LCP: time to first byte

- Remove redirect chains (http to https to www to trailing slash).
- Cache HTML at the CDN where possible; use `stale-while-revalidate` for pages that tolerate it.
- Reduce origin work: database queries, server rendering cost, cold starts. Stream the response so the head arrives early.
- Send 103 Early Hints for critical CSS, fonts and the LCP image when the server knows them before computing the page.
- Measure TTFB in the field (`onTTFB` with `waitingDuration`, `dnsDuration`, `connectionDuration`, `requestDuration` attribution).

## 3. LCP: resource load delay

The LCP request starts too late.

- Put the LCP `<img>` in the server-rendered HTML; do not render it with client JavaScript or fetch its URL from an API after hydration.
- Never use `loading="lazy"` on it. Add `fetchpriority="high"`.
- If it is a CSS background image, switch to an `<img>` (or `<picture>`), or preload it with `imagesrcset`.
- Avoid carousels and sliders that load the first slide via script; render the first slide statically.
- Check that no render-blocking script or CSS delays preload scanning of the image; the browser's preload scanner finds `<img src>` in markup even while scripts block.
- Low-priority hints (`fetchpriority="low"`) on other above-the-fold images stop them competing with the LCP image.

## 4. LCP: resource load duration

- Serve AVIF or WebP at the displayed size with an accurate `sizes`; compress to the quality that is visually acceptable.
- Use a CDN with HTTP/2 or HTTP/3, same-origin where possible to avoid a new connection (or preconnect to the image origin).
- Cache with long-lived hashed URLs; avoid query-string cache busting that defeats CDNs.
- Do not wait for a placeholder swap: avoid blur-up techniques that make the final image the LCP late. A tiny inline placeholder is fine; the real image must start immediately.

## 5. LCP: element render delay

The resource has arrived but is not painted.

- Render-blocking CSS and synchronous scripts: shrink and defer them; inline only critical CSS.
- Client-side rendering: move the LCP content to the server-rendered HTML or use streaming.
- Web fonts for text LCP: use `font-display: swap`/`optional` and preload the critical font; a blocked font delays the text.
- Long main-thread tasks during load delay paint; split them and defer third-party code.
- Hidden-then-revealed content (opacity 0 until a script runs) delays LCP; reveal with CSS or do not hide the LCP element.

## 6. CLS: what is measured

- A layout shift is an unexpected movement of visible elements between frames. Shifts are grouped into session windows (shifts less than 1 s apart, window at most 5 s); CLS is the largest window. Shifts within 500 ms of a discrete user input are excluded.
- Good is 0.1 or less at p75, poor is over 0.25.
- CLS is Chromium-only in browser APIs; CrUX CLS reflects the whole page life, so lab load CLS is often lower than field CLS.
- In RUM use the attribution build: `largestShiftTarget`, `largestShiftValue`, `largestShiftTime`, `loadState`. In DevTools, the Layout Shifts track and the `cls-culprits-insight` audit in Lighthouse 13 name the shifted nodes.

## 7. CLS: common causes and fixes

| Cause | Fix |
|---|---|
| Images, video, iframes without dimensions | `width` and `height` attributes (or `aspect-ratio`); responsive CSS `max-width: 100%; height: auto` |
| Ads, embeds, consent banners injected late | Reserve a slot with `min-height` (use the most common ad size); collapse unfilled slots rarely and below the viewport; render banners as overlays or in reserved space |
| Web font swap | Preload critical fonts; `font-display: optional` or fallback metric overrides (`size-adjust`, `ascent-override`, `descent-override`) |
| Content inserted above existing content (notices, cookie bars, late banners) | Insert below the viewport, or reserve space, or use `position: fixed` overlays |
| Animations on layout properties | Animate `transform` and `opacity` only |
| Lazy content above the fold or infinite scroll without placeholders | Skeleton with fixed size; `contain-intrinsic-size` for `content-visibility` sections |
| Late-applied CSS or A/B test flicker | Ship final CSS before first paint; run experiments server-side or at the edge |
| Client-rendered widgets (reviews, related products) | Fixed-height container with a skeleton |

```css
.ad-slot  { min-height: 250px; }                 /* typical creative height */
.embed    { aspect-ratio: 16 / 9; width: 100%; }
.section  { content-visibility: auto; contain-intrinsic-size: auto 800px; }
img, video { max-width: 100%; height: auto; }
```

## 8. Fonts and layout

- Text that changes font swaps metrics and moves surrounding content. Matching the fallback to the web font removes most of this shift.
- `font-display: optional` eliminates swap shifts at the cost of occasionally using the fallback on first visit; reasonable for body text on fast-changing sites.
- Variable fonts and subsetting reduce the time to arrive; preload the single primary file.

## 9. bfcache, prerender and soft navigations

- Pages restored from bfcache start a new measurement; web-vitals reports them with `navigationType: "back-forward-cache"`. They are typically very fast and improve p75 LCP and CLS, so making pages bfcache-eligible helps all three metrics.
- Prerendered pages report LCP relative to activation; an activated prerender can have an LCP near zero.
- Single-page apps: Core Web Vitals are attributed to the initial hard navigation unless the browser supports soft navigation reporting (Chromium 151+ with web-vitals 6 `reportSoftNavs`).

## 10. Verification

- Compare the four LCP parts before and after, not only the total.
- Confirm the LCP element is stable across page templates and viewports; mobile and desktop often differ.
- For CLS, re-record with cache disabled and with cache enabled; cached visits shift differently.
- Use RUM p75 per template to confirm the lab result holds for real users.
