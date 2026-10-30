---
name: framer-motion-expert
description: >-
  Builds UI animation in React with Motion (the library formerly named Framer Motion; npm `motion`, imports from "motion/react"): motion components, variants and stagger, AnimatePresence exit animations, layout and layoutId shared-element transitions, gestures, scroll-linked effects with useScroll and useTransform, springs, LazyMotion with the m component, reduced-motion support and Next.js App Router client boundaries. Use when adding or debugging animations, migrating from the framer-motion package name, shrinking animation bundle size, or fixing jank. Not for CSS-only transitions or Tailwind utilities (use tailwindcss-master) or page-level accessibility audits (use accessibility-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Framer Motion Expert

Motion is the animation library for React, JavaScript and Vue that was previously published and documented as Framer Motion. This skill covers the React API: motion components, variants, presence and layout animations, gestures, scroll-linked values, springs, bundle-size control with `LazyMotion`, reduced-motion handling and use inside Next.js App Router. The legacy `framer-motion` package name is covered in the migration notes.

> Verified against motion 14.9.0 and framer-motion 14.9.0 (both published at the same version; `motion` depends on a pinned `framer-motion`), React 18 and 19 peers, Next.js App Router, motion changelog and package exports (2026-10).

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

- Covered: the `motion` package for React (`motion/react`, `motion/react-m`, `motion/react-client`), component props (`initial`, `animate`, `exit`, `variants`, `transition`, `while*`, `layout`, `layoutId`, `drag`), hooks (`useScroll`, `useTransform`, `useSpring`, `useMotionValue`, `useInView`, `useAnimate`, `useReducedMotion`), `AnimatePresence`, `LayoutGroup`, `LazyMotion`, `MotionConfig`, `Reorder`, Next.js integration, performance and testing.
- Not covered: Tailwind or CSS-only animation (tailwindcss-master), WCAG motion criteria and audits (accessibility-expert), page performance budgets and Core Web Vitals (core-web-vitals-expert), Next.js routing and caching (nextjs-15-architect), designing a motion language (ui-designer).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Package name | `npm install motion`; `import { motion } from "motion/react"`. The README states: "Framer Motion is now Motion. Import from `motion/react` instead of `framer-motion`." `framer-motion` is still published at the same version number, and `motion` depends on it |
| Entry points | `motion/react` (full API), `motion/react-m` (the `m` component for `LazyMotion`), `motion/react-client` (motion elements pre-marked `"use client"`, usable from Server Components), `motion/react-mini` (smaller `animate`), `motion/react-animate-view` (`AnimateView`, React view transitions); `motion` (vanilla `animate`, `scroll`, `inView`) |
| Engine | Hybrid: native browser animation (WAAPI, ScrollTimeline/ViewTimeline where supported) for compositor-friendly values, JavaScript for springs, layout and gestures. Since 14.2.0, independent transforms (`x`, `y`, `scaleX`, ...) can be hardware accelerated |
| Motion components | `motion.div`, `motion.button`, `motion.svg`, ...; animate with `animate={{ x: 100 }}`, start from `initial`, leave with `exit`. Wrap any component with `motion.create(Component)` (it must pass `ref` to a DOM element) |
| Variants | Named states (`"hidden"`, `"visible"`) propagate from a parent to motion children; `staggerChildren`, `delayChildren`, `when` live in the parent variant's `transition`; `custom` passes data into variant functions |
| Presence | `AnimatePresence` keeps exiting children mounted until `exit` finishes; props `mode` (`"sync"`, `"wait"`, `"popLayout"`), `initial`, `custom`, `onExitComplete`, `propagate`; children need stable unique `key`s |
| Layout | `layout` (`true`, `"position"`, `"size"`, `"preserve-aspect"`) animates size and position changes with transforms; `layoutId` connects elements across mounts for shared-element transitions; `LayoutGroup`, `layoutScroll`, `layoutRoot`, `layoutDependency` refine behavior |
| Gestures | `whileHover`, `whileTap`, `whileFocus`, `whileInView` (with `viewport={{ once, amount, margin }}`), `whileDrag`, `drag` (`true`, `"x"`, `"y"`), `dragConstraints`, `dragElastic`, `onPan` |
| Scroll | `useScroll({ target, container, offset })` returns `scrollX`, `scrollY`, `scrollXProgress`, `scrollYProgress`; combine with `useTransform` and `useSpring`; `offset` strings like `["start end", "end start"]` |
| Springs | `transition={{ type: "spring", stiffness, damping, mass }}` or duration-based `{ type: "spring", visualDuration: 0.4, bounce: 0.25 }`; negative `bounce` (to -1) gives an overdamped spring; `useSpring` smooths a motion value |
| Bundle size | `LazyMotion` with `features={domAnimation}` (animations, exit, hover, tap, focus, in-view) or `domMax` (adds drag and layout) plus the `m` component; `strict` throws if a full `motion` component is used inside |
| Reduced motion | `MotionConfig reducedMotion` takes `"user"`, `"always"` or `"never"` (default `"never"`); `useReducedMotion()` returns `boolean | null` |
| Imperative | `animate(el or value, keyframes, options)` and `useAnimate()` for sequences and timelines; `stagger()` helper |

## 3. Workflow

1. Decide whether the motion is needed and what it communicates (state change, hierarchy, feedback). Prefer CSS transitions for simple hover color changes; use Motion for orchestration, exit animations, layout and scroll-linked values.
2. Install `motion`, import from `motion/react`, and put animated components in client files (`"use client"`) unless using `motion/react-client` with static props.
3. Wrap the app (or animated area) in `<MotionConfig reducedMotion="user">` so transform and layout animations are skipped for users who request reduced motion.
4. Animate `transform` and `opacity` first (`x`, `y`, `scale`, `rotate`, `opacity`); avoid animating `width`, `height`, `top`, `left` and use `layout` instead for size and position changes.
5. Use variants for multi-element choreography, `AnimatePresence` for conditional mount and unmount, `layoutId` for shared elements, `useScroll` for scroll-linked effects.
6. Profile in the browser Performance panel; check long frames, layout thrash and main-thread work during animation.
7. If bundle size matters, convert to `LazyMotion` plus `m`, with `domAnimation` or `domMax`.
8. Verify with reduced motion on, with keyboard navigation, and on a throttled CPU.

## 4. Decision Rules

- New code uses `motion` and `motion/react`. Existing `framer-motion` imports keep working; migrate by changing the import specifier to `motion/react` and removing the direct `framer-motion` dependency (it stays installed transitively through `motion`).
- Server Component needing a static entrance animation: `import * as motion from "motion/react-client"`. Anything with event handlers, hooks, `useScroll`, `AnimatePresence` or `MotionConfig` goes in a file with `"use client"`.
- Conditional element with an exit animation: `AnimatePresence` as a parent that stays mounted, child with `key` and `exit`. `mode="wait"` for one-in-one-out swaps, `popLayout` when siblings should reflow immediately (custom children must accept a `ref` prop).
- Element moves or resizes because of layout (list reorder, accordion, tabs underline): `layout`. Same logical element appearing in two places (card to modal, active tab indicator): `layoutId`.
- Scroll effect tied to scroll position: `useScroll` plus `useTransform`. Effect that plays once when an element enters the viewport: `whileInView` with `viewport={{ once: true }}`.
- Spring or tween: springs for interactive, interruptible motion (gestures, layout); tweens (`duration`, `ease`) for fixed-time fades and choreography.
- Bundle size is a measured problem and most animation is simple: `LazyMotion` with `domAnimation`. Layout or drag in use: `domMax` (loaded asynchronously is possible).
- Drag-to-reorder lists: `Reorder.Group` and `Reorder.Item`; keyboard reordering is built in on recent versions, but test it.
- Route transitions in the App Router: enter animations via `app/**/template.tsx` (re-mounts per navigation); exit animations across routes are not reliable with `AnimatePresence` in the App Router, so consider `AnimateView` (React view transitions) and check its current docs.

## 5. Coding Standards

- Import only from `motion/react` family paths; do not mix `framer-motion` and `motion/react` in one project.
- Define variants and transitions as module-level constants (not inside render) to keep object identity stable.
- Use `as const` or `satisfies Variants` on variant objects for type safety (`import type { Variants } from "motion/react"`).
- Name variant states by meaning (`hidden`, `visible`, `open`, `closed`), not by effect.
- Give every child of `AnimatePresence` a stable `key`; never use the array index for items that can reorder or be removed.
- Use `initial={false}` on `AnimatePresence` or a component when the first render should not animate (for example server-rendered content).
- Prefer `useMotionValue` and `useTransform` over React state for values that change every frame; do not call `setState` in `onScroll` or `onDrag` for animation.
- Keep `transition` close to the property when properties differ: `transition={{ opacity: { duration: 0.2 }, y: { type: "spring", visualDuration: 0.4, bounce: 0.2 } }}`.
- Respect semantics: animate wrapper elements, keep interactive elements as real `<button>` or `<a>` (`motion.button`, `motion.a`).

## 6. Project Structure

```
src/
├── components/
│   ├── motion/
│   │   ├── motion-provider.tsx   # "use client": MotionConfig reducedMotion="user" (+ LazyMotion optional)
│   │   ├── fade-in.tsx           # small reusable wrappers using m or motion
│   │   └── variants.ts           # shared Variants and transition constants
│   └── ui/                       # components that use the wrappers
├── hooks/
│   └── use-parallax.ts           # useScroll + useTransform helpers
└── app/
    ├── layout.tsx                # mounts MotionProvider
    └── template.tsx              # optional per-navigation enter animation
```

## 7. Design Patterns

- **Variant orchestration**: parent defines `visible: { transition: { staggerChildren: 0.06 } }`; children define `hidden`/`visible` and inherit the active label without their own `animate`.
- **Presence wrapper**: a reusable `<Presence show>` component that renders `AnimatePresence` plus a keyed `motion.div` with `initial`, `animate`, `exit`.
- **Shared element**: the same `layoutId` on two elements in different states; only one is mounted at a time (or wrap in `AnimatePresence`), and Motion animates between their boxes. Details in [references/layout-and-presence.md](references/layout-and-presence.md).
- **Scroll progress and parallax**: `scrollYProgress` mapped with `useTransform` to `scaleX`, `y` or `opacity`; smoothed with `useSpring`. Details in [references/scroll-and-performance.md](references/scroll-and-performance.md).
- **Motion provider**: one client component combining `MotionConfig` (reduced motion, default transition) and optionally `LazyMotion`.
- **Imperative sequence**: `useAnimate()` returns `[scope, animate]`; run `await animate(...)` steps for toasts, success checkmarks or onboarding.
- **Gesture feedback**: `whileTap={{ scale: 0.97 }}` and `whileHover` on buttons and cards, kept subtle and short.

## 8. Best Practices

- Keep motion short and purposeful: feedback in roughly 100 to 300 ms, larger transitions a bit longer; avoid long delays that block interaction.
- Use springs with `visualDuration` and `bounce` when you want predictable timing without tuning stiffness and damping.
- Do not animate layout-affecting properties directly (`height`, `top`); use `layout`, or animate `height: "auto"` only for simple disclosure where it is acceptable and measure cost.
- Make exit animations quick; users should not wait on them.
- Give animated overlays focus management (move focus in, restore on close) and make them dismissible by keyboard; motion does not replace that.
- Avoid autoplaying looping animation near text; provide a way to pause, and honor reduced motion.
- When animating text, animate wrappers by word or line, and keep the text selectable and readable by assistive tech (do not split into per-letter elements without an accessible label).
- Pair `layout` with `layoutDependency` when layout should only be measured on specific state changes.
- Set `transformTemplate` or `style` transforms carefully: Motion owns `transform` on motion elements, so do not also set it in CSS.

## 9. Performance

- Compositor-friendly properties are `transform` (`x`, `y`, `scale`, `rotate`) and `opacity`, plus `filter` and `clip-path` in some cases. Animating them avoids layout and paint; Motion accelerates independent transforms and many opacity animations natively.
- Layout animations use transforms to move and scale elements, so they avoid animating `width` and `height` directly, but they measure the DOM: avoid triggering them for hundreds of elements at once.
- Scroll-linked values update outside React renders; `useTransform` and `useSpring` do not cause component re-renders unless you read `.get()` into state.
- `will-change` is rarely needed; add `will-change: transform` only for elements measured to benefit, and remove it afterward.
- Reduce bundle weight with `LazyMotion` and `m`; import `domMax` only where drag or layout is used. Use `motion/react-mini` or vanilla `animate` for simple one-off effects when the full component is overkill.
- Avoid animating many large box-shadows, blurs or full-screen filters; they are expensive to paint.
- Use `viewport={{ once: true }}` for `whileInView` reveals so observers disconnect after the first trigger.
- Keep the number of simultaneously animating elements modest on low-end devices; test with CPU throttling.
- Details and measurement tips: [references/scroll-and-performance.md](references/scroll-and-performance.md).

## 10. Security

- Motion does not touch the network; the main risks are indirect. Do not pass untrusted strings to `style`, `animate` values or SVG attributes that become URLs or CSS injection vectors; validate or whitelist values that come from user input.
- Do not render user-supplied HTML inside animated wrappers via `dangerouslySetInnerHTML`; sanitize first.
- Load Motion from npm with a lockfile; for CDN use (vanilla `animate`) pin an exact version and use Subresource Integrity.
- Honor user preferences (reduced motion) and avoid flashing content: rapid flashing can trigger seizures, so keep flashes below the thresholds in WCAG guidance (accessibility-expert).
- Animations must not obscure consent dialogs or security prompts, or delay input in a way that enables clickjacking-like confusion (elements moving under the pointer just before a click).

## 11. Testing

- Unit tests (Jest or Vitest with jsdom) do not run real animations. Assert end states and structure, or disable animation via `MotionConfig reducedMotion="always"` in the test wrapper and `transition={{ duration: 0 }}` defaults.
- Recent versions expose frame-loop helpers for tests (`stepFrames`, `processFrame` in the 14.x changelog); check the current docs before using them.
- `AnimatePresence` tests: assert the exiting element is removed after `onExitComplete` fires, using `waitFor`.
- Playwright: use `page.emulateMedia({ reducedMotion: "reduce" })` to test the reduced path and wait for elements by role rather than by timeout; record traces for jank investigations.
- Visual regression: disable animations globally during snapshots (reduced motion plus CSS `animation: none` for CSS-driven parts).
- Test keyboard behavior for dialogs, menus and `Reorder` lists, not only pointer behavior.

## 12. Review Checklist

- [ ] Imports come from `motion/react` (or `motion/react-m`, `motion/react-client`), not `framer-motion`.
- [ ] Files using hooks, handlers or `AnimatePresence` carry `"use client"`.
- [ ] `MotionConfig reducedMotion="user"` is applied app-wide (the default is `"never"`).
- [ ] Only transform and opacity are animated; size and position changes use `layout`.
- [ ] `AnimatePresence` children have stable keys and `exit` props; the presence parent stays mounted.
- [ ] `layoutId` values are unique per shared element and not duplicated on screen at once.
- [ ] Scroll effects use motion values, not React state.
- [ ] Bundle: `LazyMotion` and `m` considered; `domMax` used only where needed.
- [ ] Durations are short, nothing blocks interaction, loops are pausable.
- [ ] Animated interactive elements remain keyboard accessible with visible focus.

## 13. Production Notes

- Motion releases frequently (many minor versions per month in 2026). Pin `motion` in the lockfile, read the changelog on upgrades, and note that internal APIs are explicitly not stable.
- `motion` and `framer-motion` ship at identical versions and `motion` pins its `framer-motion` dependency; do not add a second, different `framer-motion` version to the tree.
- `LazyMotion` with an async `features` loader splits the animation engine into a separate chunk; make sure the first paint does not depend on animation features (use `initial={false}` or CSS for above-the-fold states).
- React 19 `Activity` and `Suspense` interact with mount animations; recent changelogs list fixes, so test behavior after upgrading.
- For SSR, content animated with `initial` opacity 0 is invisible until hydration; avoid hiding critical content (LCP element) behind a JS-driven fade, or render it visible and animate only secondary elements.
- Vue users install `motion-v`; this skill covers React only.

## 14. Examples

Provider with reduced-motion support and lazy features (client component):

```tsx
"use client"

import { LazyMotion, MotionConfig, domAnimation } from "motion/react"

export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0.25 }}>
      <LazyMotion features={domAnimation} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  )
}
```

Staggered list with enter and exit animations using `m` (works under the provider above):

```tsx
"use client"

import { AnimatePresence, m, type Variants } from "motion/react"

const list: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
}
const item: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

export function Notifications({ items }: { items: { id: string; text: string }[] }) {
  return (
    <m.ul variants={list} initial="hidden" animate="visible">
      <AnimatePresence initial={false}>
        {items.map((n) => (
          <m.li
            key={n.id}
            variants={item}
            exit={{ opacity: 0, x: -16 }}
          >
            {n.text}
          </m.li>
        ))}
      </AnimatePresence>
    </m.ul>
  )
}
```

With `strict` on `LazyMotion`, accidentally using a full `motion.*` component inside fails loudly during development. Adding `layout` or `drag` to these items requires `domMax` instead of `domAnimation`.

Reading progress bar driven by scroll, smoothed with a spring:

```tsx
"use client"

import { motion, useScroll, useSpring } from "motion/react"

export function ReadingProgress() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 30, restDelta: 0.001 })
  return (
    <motion.div
      aria-hidden="true"
      style={{ scaleX, transformOrigin: "0% 50%" }}
      className="fixed inset-x-0 top-0 h-1 bg-primary"
    />
  )
}
```

## 15. Common Mistakes

- **Importing from `framer-motion` in new code**: use `motion/react`. Mixing both can load two copies.
- **Using `motion.div` in a Server Component**: it needs client code. Add `"use client"` or import from `motion/react-client` and pass only serializable props.
- **No `reducedMotion` setting**: the default is `"never"`, so Motion ignores the OS preference until `MotionConfig reducedMotion="user"` is set.
- **`AnimatePresence` around an element that is itself conditionally rendered by a parent component**: the exit never runs because `AnimatePresence` unmounts with it. Keep `AnimatePresence` mounted and put the condition inside.
- **Missing or index keys on presence children**: exits animate the wrong element.
- **A direct child of `AnimatePresence` that renders no motion element**: nothing animates and it unmounts immediately. Put `exit` on a motion element inside it, or use `usePresence` to delay removal manually.
- **Animating `height` or `width` per frame in lists**: use `layout`.
- **Setting React state from scroll or drag handlers for animation**: causes re-renders every frame; use motion values.
- **Mixing `layout` with CSS `transform` on the same element**: Motion owns `transform`; the two conflict.
- **`LazyMotion strict` with full `motion.*` components inside**: throws; use `m`.
- **Importing `domMax` just in case**: it adds drag and layout code; use `domAnimation` unless you need them.
- **Passing a component to `motion.create` that does not forward `ref`**: layout, exit and gestures fail. Accept `ref` as a prop in React 19.
- **Hiding LCP content with an `initial` opacity of 0**: delays visible content until JavaScript runs.
- **Long, looping or parallax motion with no reduced-motion fallback**: provide a static or simplified version.

## 16. References

- [references/layout-and-presence.md](references/layout-and-presence.md): `AnimatePresence` modes, `usePresence`, `layout` props, `layoutId` shared transitions, `LayoutGroup`, `Reorder`, scrolling containers, Next.js client boundaries and route transitions.
- [references/scroll-and-performance.md](references/scroll-and-performance.md): `useScroll` offsets, `useTransform` patterns, springs and `useSpring`, `LazyMotion` details, reduced motion, hardware acceleration and profiling.
- Official docs: https://motion.dev/docs/react , https://motion.dev/docs/react-animation , https://motion.dev/docs/react-animate-presence , https://motion.dev/docs/react-layout-animations , https://motion.dev/docs/react-scroll-animations , https://motion.dev/docs/react-lazy-motion , https://motion.dev/docs/react-accessibility , https://github.com/motiondivision/motion
