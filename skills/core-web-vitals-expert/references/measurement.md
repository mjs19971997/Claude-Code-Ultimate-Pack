# Measurement

Where Core Web Vitals data comes from and how to use it: field data (CrUX, PageSpeed Insights, Search Console, RUM with the web-vitals library), lab data (Lighthouse, DevTools), and performance budgets in CI. Verified against web-vitals 6.2.3, Lighthouse 13.6.0 (requires Node 22.19 or newer), @lhci/cli 0.15.1 (bundles Lighthouse 12.6.1) and the Chrome UX Report API docs (2026-10).

## 1. Field versus lab

| | Field (real users) | Lab (synthetic) |
|---|---|---|
| Sources | CrUX, PageSpeed Insights field section, Search Console, your RUM | Lighthouse, PageSpeed Insights diagnostics, DevTools |
| Strength | Real devices, networks, interactions; the data Google uses for page experience reporting | Reproducible, debuggable, runs before release |
| Weakness | Delayed (CrUX 28 days), needs traffic, little detail without attribution | One profile; cannot see real interactions (INP) or post-load CLS well |
| Use for | Deciding what to fix and verifying the result | Finding why and preventing regressions |

Treat disagreement as information: a good lab score with poor field data usually means different devices, third parties, consent flows or interactions that the lab run never performs.

## 2. Chrome UX Report (CrUX)

- Anonymous metrics from opted-in Chrome users, available per origin and per URL (with enough traffic), split by form factor (phone, desktop, tablet) and sometimes by connection type.
- The API reports a 28-day collection period; the data refreshes daily and has no guaranteed schedule. Metrics are given as histograms and p75 values.
- Access: CrUX API (needs a Google Cloud API key), CrUX History API (trend over weekly collection periods), BigQuery (monthly origin-level datasets), and CrUX Vis (dashboard).
- Query pattern for the API (key kept in an environment variable, not in code or URLs shared publicly):

```bash
curl -s -X POST "https://chromeuxreport.googleapis.com/v1/records:queryRecord?key=${CRUX_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/products/","formFactor":"PHONE","metrics":["largest_contentful_paint","interaction_to_next_paint","cumulative_layout_shift"]}'
```

- Pass `origin` instead of `url` for origin-level data. A missing URL record means insufficient traffic; fall back to the origin or to RUM.
- CrUX covers Chrome (not other browsers), includes iframe content and the whole page life, and excludes users who opted out of usage statistics.

## 3. PageSpeed Insights and Search Console

- PageSpeed Insights shows CrUX data (URL-level when available, otherwise origin-level; check which one is displayed) next to a Lighthouse lab run on Google's infrastructure. Its API (`pagespeedonline/v5/runPagespeed`) returns both.
- Search Console's Core Web Vitals report groups URLs by status (good, needs improvement, poor) per device from CrUX and shows example URLs; fixes appear after the 28-day window.
- A group's status is the worst of its metrics at p75.

## 4. web-vitals library (RUM)

- Install with `npm install web-vitals`. The standard build is about 3 KB brotli; the attribution build (`web-vitals/attribution`) adds roughly 1.5 KB and the `attribution` object.
- Functions: `onLCP`, `onINP`, `onCLS`, `onFCP`, `onTTFB`. Each takes a callback and options (`reportAllChanges`, `reportSoftNavs`, `durationThreshold` for INP, `generateTarget` and `resourceBufferSize` for the attribution build).
- Metrics can be reported more than once per page (CLS and INP on visibility changes, all metrics after bfcache restore). Dedupe and group by `id`, and sum deltas where needed.
- INP is not reported if the user never interacts; CLS, FCP and LCP are not reported for pages loaded in the background.
- The library cannot see inside iframes; CrUX can. Expect small differences.
- Browser coverage: `onCLS` Chromium only; `onFCP`, `onINP`, `onLCP`, `onTTFB` in Chromium, Firefox and Safari; soft-navigation reporting needs Chromium 151+.
- Load it after critical code (it uses `buffered` observers, so late loading still sees early entries). Call each `onX` once per page load.
- Complete example: see the RUM snippet in SKILL.md. Server-side, accept only your own origin, validate the JSON schema, cap batch size and rate-limit.

## 5. RUM pipeline design

1. Collect: metric name, value, rating, id, navigationType, normalized page template, device class, effective connection type (when available), build version, and the attribution fields relevant to the metric.
2. Transport: `navigator.sendBeacon()` (or `fetch` with `keepalive: true`) on `visibilitychange` to hidden and `pagehide`.
3. Store: aggregate by template, metric, day and device; keep raw events for a short period only.
4. Analyze: p75 per template and device; breakdown of LCP parts and INP phases; top attribution targets.
5. Alert: on p75 regression beyond a margin sustained across days, not on single events.
6. Privacy: no user IDs, no full URLs with query strings, no text content; comply with consent requirements for analytics in your jurisdictions.

## 6. Lighthouse 13

- Version 13 (October 2025) removed legacy audits that insights replaced (for example image, preload and layout-shift audits; some audits like `font-size` and `offscreen-images` were dropped entirely). It does not change how the performance score is computed. Requires Node 22.19 or newer; current release at this writing is 13.6.0.
- Run: `npx lighthouse https://example.com --only-categories=performance --output=json --output-path=./lh.json`. Use `--preset=desktop` for desktop, mobile emulation is the default.
- Modes: navigation (default, page load), timespan (record interactions for INP-style analysis) and snapshot (a single state).
- Lab metrics: LCP, CLS, Total Blocking Time (proxy for responsiveness), FCP and Speed Index. INP is only available in timespan and user-flow runs that include interactions.
- Variability: run several times and use the median; keep CPU and network throttling consistent; avoid running next to heavy local load.
- The insights (for example LCP breakdown, CLS culprits, INP breakdown, network dependency tree, image delivery, third parties) are the actionable output; scores alone are not.
- CI: the Lighthouse CLI has a programmatic Node API (`import lighthouse from 'lighthouse'`) and a CLI. Pin the version in `package.json`.

## 7. Lighthouse CI and budgets

- `@lhci/cli` 0.15.1 bundles Lighthouse 12.6.1, so audit IDs and results come from Lighthouse 12 unless you override the version. Assert on stable metric IDs (`largest-contentful-paint`, `cumulative-layout-shift`, `total-blocking-time`) rather than on audits that Lighthouse 13 removed.
- Use `numberOfRuns` of 3 to 5 and assert on the median (`aggregationMethod: "median"`).
- Resource budgets: a `budgets.json` file (Lighthouse format) with `resourceSizes` and `resourceCounts`, applied with `--budget-path`.

```json
[
  {
    "path": "/*",
    "resourceSizes": [
      {"resourceType": "script", "budget": 200},
      {"resourceType": "image", "budget": 400},
      {"resourceType": "total", "budget": 900}
    ],
    "resourceCounts": [
      {"resourceType": "third-party", "budget": 10}
    ]
  }
]
```

Sizes are in kilobytes. Choose the numbers from your own baseline and slowest cohort.

- Bundle checks complement Lighthouse: fail the build when a route chunk exceeds its limit (bundler stats plus a small script), because Lighthouse sees only what the test page loads.

## 8. DevTools workflow

- Performance panel: record with 4x CPU throttling and Slow 4G, check LCP, layout shifts and long tasks tracks, and the Insights sidebar for LCP breakdown and third parties.
- Network panel: disable cache for first-visit analysis; read the priority column; confirm the LCP image requests starts early.
- Rendering tab: layout shift regions and paint flashing for CLS and repaint hotspots.
- Application tab: back/forward cache test, service worker and cache inspection, speculative loads.
- Console: use `PerformanceObserver` with `buffered: true` for `largest-contentful-paint`, `layout-shift`, `event` and `long-animation-frame` entries for quick checks.

## 9. Interpreting results

- Compare the same form factor and URL scope across tools; PageSpeed Insights URL-level data and Search Console group data differ.
- A change in p75 smaller than the noise between weeks is not a result; compare at least two full weeks.
- Prioritize by traffic share: a template covering 40% of visits with p75 INP of 300 ms beats a rarely visited page with 800 ms.
- Document each optimization with the metric it targets, the hypothesis, the release and the observed p75 change.
