# INP Optimization

Interaction to Next Paint (INP): how it is measured, how to find the slow interaction in the field and the lab, and how to fix input delay, processing duration and presentation delay. Verified against web-vitals 6.2.3 (attribution build), MDN browser-compat-data 8.1.7 (Long Animation Frames, `scheduler`), and the web.dev optimize-INP guidance (2026-10).

## 1. What INP measures

- INP observes the latency of clicks, taps and key presses during a visit (scrolling and hovering are excluded) and reports roughly the slowest one; for very interactive visits it ignores outliers (about one per 50 interactions). Good is 200 ms or less at p75, poor is over 500 ms. INP replaced FID as a Core Web Vital in March 2024.
- One interaction has three parts:
  - Input delay: time until event handlers can start (main thread busy with other tasks).
  - Processing duration: time spent in event handlers.
  - Presentation delay: time from the end of handlers to the next frame being presented (style, layout, paint, compositing).
- Event Timing is supported in Chrome, Firefox and Safari 26.2+, so INP data exists on all three engines; scripts attribution through LoAF is Chromium only.
- Interactions inside iframes count in CrUX but are invisible to the web-vitals library in the parent page.

## 2. Find the slow interaction

Field first (the same interaction that real users hit):

```ts
import {onINP} from 'web-vitals/attribution';

onINP((metric) => {
  const a = metric.attribution;
  console.log({
    value: metric.value,
    target: a.interactionTarget,        // selector of the element
    type: a.interactionType,            // 'pointer' | 'keyboard'
    inputDelay: a.inputDelay,
    processing: a.processingDuration,
    presentationDelay: a.presentationDelay,
    loadState: a.loadState,             // slow input during 'loading' points at startup work
    longestScript: a.longestScript?.entry.sourceURL,
    longestScriptPart: a.longestScript?.subpart,
  });
});
```

- `longestScript`, `totalScriptDuration`, `totalStyleAndLayoutDuration` and `longAnimationFrameEntries` are filled when the browser supports LoAF.
- Aggregate by `interactionTarget`, template and `loadState`; fix the top selector first.

Lab: DevTools Performance panel, record while repeating the slow interaction with 4x CPU throttling. The Interactions track shows the three phases; the Long animation frames track and Bottom-Up view show which functions ran. Lighthouse navigation mode does not click anything; use a DevTools user flow or timespan mode for interactions.

## 3. Long Animation Frames (LoAF)

LoAF reports frames that take over 50 ms to render, with script attribution (Chrome and Edge 123+; not in Firefox or Safari, and marked experimental in the compat data).

```js
const observer = new PerformanceObserver((list) => {
  for (const frame of list.getEntries()) {
    if (frame.blockingDuration < 100) continue; // focus on the worst frames
    console.log({
      duration: frame.duration,
      blocking: frame.blockingDuration,
      renderStart: frame.renderStart,
      styleAndLayoutStart: frame.styleAndLayoutStart,
      firstUIEvent: frame.firstUIEventTimestamp,
      scripts: frame.scripts.map((s) => ({
        url: s.sourceURL,
        fn: s.sourceFunctionName,
        invoker: s.invoker,
        invokerType: s.invokerType,   // e.g. event-listener, user-callback, resolve-promise
        duration: s.duration,
        forcedLayout: s.forcedStyleAndLayoutDuration,
      })),
    });
  }
});
observer.observe({type: 'long-animation-frame', buffered: true});
```

- Compare `renderStart` and `styleAndLayoutStart` to the frame end to see script versus rendering share.
- Many scripts from one third-party origin in LoAF entries is a strong signal for deferring or removing that tag.
- Ship LoAF summaries to RUM only for slow frames and strip query strings from script URLs.

## 4. Reduce input delay

- Startup: split and defer scripts that run before the page is interactive; interactions during `loading` or `dom-interactive` suffer most.
- Break long tasks (over 50 ms) into smaller ones with yielding (section 5).
- Third-party tags: load late, remove duplicates, move heavy ones to a worker or sandboxed iframe.
- Avoid timers that fire heavy work at fixed intervals; align work with user idle moments (`requestIdleCallback` where supported, otherwise `scheduler.postTask` with `background` priority).
- Prevent overlapping interactions: debounce expensive handlers on input, and cancel obsolete work.

## 5. Reduce processing duration

Yield so the browser can paint and handle the next input. `scheduler.yield()` (Chrome and Edge 129+, Firefox 142+, no Safari) continues the task with priority after the yield; the `setTimeout` fallback goes to the back of the queue.

```ts
type Sched = {yield?: () => Promise<void>};

export function yieldToMain(): Promise<void> {
  const s = (globalThis as {scheduler?: Sched}).scheduler;
  return s?.yield ? s.yield() : new Promise((resolve) => setTimeout(resolve, 0));
}

button.addEventListener('click', async () => {
  showSpinner();            // visual feedback first
  await yieldToMain();      // let the browser paint
  const result = computeExpensive(input);
  render(result);
  await yieldToMain();
  sendAnalytics();          // non-urgent work last
});
```

- Do only what the next frame needs inside the handler; defer analytics, logging, persistence and cache warming.
- Use `scheduler.postTask(fn, {priority: 'background'})` (Chrome 94+, Firefox 142+) for low-priority work; fall back to `setTimeout` or `requestIdleCallback`.
- `isInputPending()` is Chromium-only and experimental; do not build on it.
- Reduce algorithmic cost first: memoize, use maps instead of repeated array scans, avoid re-parsing JSON, paginate.
- Avoid layout thrashing: read layout values (offsetHeight, getBoundingClientRect) in one batch, then write styles in another. LoAF `forcedStyleAndLayoutDuration` quantifies it.
- Move CPU-heavy work to a Web Worker; the main thread then only posts messages and renders results.
- React and similar frameworks: mark non-urgent updates with `startTransition` or `useDeferredValue` so typing and clicking stay responsive; avoid rendering large lists on each keystroke; memoize expensive derived data; keep context values stable.

## 6. Reduce presentation delay

- Keep the DOM small (thousands, not tens of thousands of nodes); big DOMs make every style and layout pass expensive. Virtualize long lists.
- `content-visibility: auto` on offscreen sections lets the browser skip their rendering.
- Avoid forced synchronous layout and large `:has()`/universal selectors over huge DOMs when profiling shows selector cost.
- Limit work in `requestAnimationFrame`, `ResizeObserver` and `IntersectionObserver` callbacks, which run in the rendering step and delay the next frame.
- Prefer CSS transitions of `transform` and `opacity`; avoid animating layout.
- Large images decoding on the main thread can delay a frame: use `decoding="async"` and right-sized images.

## 7. Verify

- Reproduce the slow interaction with the same CPU throttling and confirm all three phases drop.
- Watch p75 INP per template in RUM for at least several days; CrUX reflects the change over its 28-day window.
- Add a regression test where possible: a Playwright script performing the interaction under CPU throttling and asserting Event Timing durations stay below a limit (use a loose threshold; lab variance is high).
- Keep an eye on bfcache restores and soft navigations: web-vitals reports them as separate metric instances with their own `navigationType` and `navigationURL`.
