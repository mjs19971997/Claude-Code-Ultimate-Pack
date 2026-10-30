# Scroll, Springs, Bundle Size, Reduced Motion and Performance

Reference for scroll-linked animation, motion values, springs, `LazyMotion`, reduced motion and profiling with Motion. Verified against motion 14.9.0 / framer-motion 14.9.0 type definitions and changelog (2026-10).

## 1. Motion values

`useMotionValue(initial)` creates a value that updates the DOM without re-rendering React. Pass it through `style`: `<motion.div style={{ x }} />`. Derive values with `useTransform` and `useSpring`; subscribe with `useMotionValueEvent(value, "change", cb)` for side effects.

`useTransform` signatures (from the types):

- `useTransform(value, inputRange, outputRange, options?)` maps a number range to numbers, colors or strings, with `clamp` and `ease` options.
- `useTransform(value, (v) => result)` derives from one value; `useTransform([a, b], ([x, y]) => ...)` from several.
- `useTransform(() => a.get() + b.get())` tracks values read inside the function.

```tsx
const x = useMotionValue(0)
const opacity = useTransform(x, [-100, 0, 100], [0, 1, 0])
const background = useTransform(x, [-100, 100], ["oklch(0.7 0.15 25)", "oklch(0.7 0.15 150)"])
```

## 2. useScroll

```tsx
"use client"

import { motion, useScroll, useTransform } from "motion/react"
import { useRef } from "react"

export function ParallaxImage({ src, alt }: { src: string; alt: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })
  const y = useTransform(scrollYProgress, [0, 1], ["-10%", "10%"])
  return (
    <div ref={ref} className="relative h-96 overflow-hidden">
      <motion.img src={src} alt={alt} style={{ y }} className="absolute inset-0 h-[120%] w-full object-cover" />
    </div>
  )
}
```

- With no options, `useScroll()` tracks the page scroll. `container` (a ref) tracks a scrollable element; `target` (a ref) tracks an element's progress through the viewport or container.
- Return values: `scrollX`, `scrollY` (pixels), `scrollXProgress`, `scrollYProgress` (0 to 1), and in recent versions `scrollXLength` and `scrollYLength` (maximum scroll offsets).
- `offset` pairs describe when progress is 0 and 1 as `"<target edge> <container edge>"`: `"start end"` means the target start meets the container end (just entering); `"end start"` means target end meets container start (just leaving). Named edges: `start`, `center`, `end`; numbers and percentages are also accepted.
- Scroll values are tracked on the main thread in current versions, with hardware-accelerated paths using ViewTimeline for some offsets; the API is the same either way.
- Set `position: relative` (or non-static) on the tracked container/target; `useScroll` warns about static positioning in development.
- Reveal-on-enter effects that need no continuous value: `whileInView` with `viewport={{ once: true, amount: 0.3 }}` or `useInView(ref, { once: true })`.
- Sticky storytelling sections: tall wrapper with a `position: sticky` child, `useScroll({ target: wrapper })`, and `useTransform` on the child contents.

## 3. Springs

```tsx
<motion.div animate={{ x: 100 }} transition={{ type: "spring", visualDuration: 0.4, bounce: 0.25 }} />
<motion.div animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 24, mass: 0.8 }} />
```

- Duration-based: `visualDuration` (seconds until the motion looks finished; overrides `duration`) and `bounce` (0 none to 1 very bouncy; negative values to -1 give an overdamped spring).
- Physics-based: `stiffness` (default 100), `damping` (default 10), `mass`; setting any of these overrides `bounce` and `duration`.
- `restDelta`/`restSpeed` control when a spring snaps to its target.
- `useSpring(source, options)` returns a motion value that springs toward a number, string or another motion value (for example smoothing `scrollYProgress`).
- Springs preserve velocity when interrupted, which is why they suit gestures and layout.
- Tweens: `transition={{ duration: 0.3, ease: "easeOut" }}` or cubic-bezier arrays; `type: "inertia"` for drag release.

## 4. Variants, stagger and sequences

- Parent `transition: { staggerChildren: 0.05, delayChildren: 0.1, when: "beforeChildren" }`.
- The `stagger()` helper (for `animate()` sequences and `delay`) offers options such as `from` and, in recent versions, grid-aware staggering.
- `useAnimate()` returns `[scope, animate]`; selectors are scoped to `scope.current`:

```tsx
const [scope, animate] = useAnimate()
async function playSuccess() {
  await animate(".check", { pathLength: [0, 1] }, { duration: 0.3 })
  await animate(scope.current, { scale: [1, 1.05, 1] }, { duration: 0.2 })
}
```

`useAnimate` respects the reduced-motion setting from `MotionConfig` in current versions (per the changelog); test the plain `animate()` function yourself if you rely on it.

## 5. LazyMotion and the m component

```tsx
"use client"
import { LazyMotion, m } from "motion/react"

const loadFeatures = () => import("./features").then((mod) => mod.default)
// features.ts: import { domAnimation } from "motion/react"; export default domAnimation

export function Lazy() {
  return (
    <LazyMotion features={loadFeatures} strict>
      <m.div animate={{ opacity: 1 }} initial={{ opacity: 0 }} />
    </LazyMotion>
  )
}
```

| Bundle | Includes |
|---|---|
| `domAnimation` | Animations (`animate`, variants, `transition`), exit animations, hover, tap, focus and in-view gestures |
| `domMax` | Everything in `domAnimation` plus drag and layout animations |

- `m` components render without bundled features; features come from the nearest `LazyMotion`. `features` can be a bundle object or a function returning (a promise of) one for async loading.
- `strict` raises an error if a full `motion.*` component renders inside, helping the bundle stay small.
- Import `m` from `motion/react` or `motion/react-m`; both work with `LazyMotion` in current versions.
- Size numbers change between releases (the changelog lists frequent reductions). Measure with your bundler's analyzer instead of trusting published figures.
- Reorder has a `LazyMotion`-compatible import in 14.x.

## 6. Reduced motion

```tsx
import { MotionConfig, useReducedMotion } from "motion/react"

<MotionConfig reducedMotion="user">{children}</MotionConfig>

function Hero() {
  const reduce = useReducedMotion() // boolean | null
  return <motion.h1 animate={reduce ? { opacity: 1 } : { opacity: 1, y: 0 }} initial={reduce ? { opacity: 0 } : { opacity: 0, y: 24 }} />
}
```

- `MotionConfig reducedMotion`: `"user"` follows the OS/browser `prefers-reduced-motion` setting, `"always"` forces it, `"never"` ignores it (the default).
- When active, transform and layout animations are switched off; non-transform values such as opacity and color still animate, which keeps state changes visible without movement.
- `useReducedMotion()` lets you replace motion with a calmer alternative (fade instead of slide), disable parallax, or stop autoplaying loops. Return value can be `null` before detection; treat it as falsy.
- Parallax, auto-scrolling marquees, large zooms and looping background motion should be removed entirely under reduced motion, not just shortened.
- Provide a user-facing pause control for motion that lasts more than a few seconds.
- Test both settings in browser devtools (rendering panel emulates `prefers-reduced-motion`).

## 7. Performance and profiling

- Prefer `transform` and `opacity`. Motion's independent transform properties (`x`, `y`, `scale`, `rotate`) can be hardware accelerated; the `transform` string shorthand is applied as a whole and may run on the main thread.
- Interrupted accelerated animations can be handed back to the main thread (recent fixes mention demoting transforms to the CPU while layout animations run); this is automatic.
- Animating CSS variables from JavaScript restyles descendants of the element on every frame; scope variables to small subtrees.
- Heavy paints: large blur, `backdrop-filter`, big `box-shadow` animations and full-viewport gradients are costly on low-end GPUs.
- Measure: open the browser Performance panel, record while interacting, look for long tasks, forced reflow and paint time; use CPU throttling (4x or 6x) to find problems early. React Profiler shows whether components re-render during animation (they should not).
- Limit concurrent layout animations; each `layout` element measures on every layout-affecting render.
- Use `viewport={{ once: true }}` and `useInView` with `once` for reveals; unobserve work is handled automatically.
- Avoid `AnimatePresence` around very large trees; animate a lightweight wrapper.
- `will-change` should be used sparingly and temporarily; Motion applies its own optimizations.
- Check bundle impact with the framework's analyzer (for Next.js, the bundle analyzer plugin) before and after introducing `LazyMotion`.
