# Layout, Presence and Next.js Boundaries

Reference for `AnimatePresence`, layout animations, shared-element transitions, `Reorder` and using Motion inside the Next.js App Router. Verified against motion 14.9.0 / framer-motion 14.9.0 type definitions and changelog (2026-10). Props and behaviors listed here come from the package types; check the Motion docs for visual examples.

## 1. AnimatePresence

```tsx
"use client"

import { AnimatePresence, motion } from "motion/react"

export function Panel({ open }: { open: boolean }) {
  return (
    <AnimatePresence initial={false} mode="wait">
      {open && (
        <motion.div
          key="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.2 }}
        >
          Content
        </motion.div>
      )}
    </AnimatePresence>
  )
}
```

| Prop | Meaning |
|---|---|
| `initial` | `false` skips the `initial` animation of children present on first render |
| `mode` | `"sync"` (default: entering and exiting at the same time), `"wait"` (the entering child waits until the exiting child is gone; use with one child), `"popLayout"` (exiting child is removed from layout flow so siblings with `layout` reflow immediately) |
| `custom` | Value passed to variant functions of exiting children, which can no longer receive new props |
| `onExitComplete` | Fires after exiting children have been removed |
| `propagate` | Lets a parent exit animation propagate to nested `AnimatePresence` |
| `presenceAffectsLayout` | Whether presence changes trigger layout animations in siblings (default `true`) |
| `anchorX`, `anchorY`, `root` | Positioning and portal root for `popLayout` (for example when rendering into another window) |

Rules:

- `AnimatePresence` must remain mounted; the conditional goes inside it.
- Direct children need unique, stable `key`s. A changing `key` on one element is a valid way to animate content swaps (for example a counter or tab panel).
- Exit animations run on motion elements inside the removed child through presence context; a plain child with no motion element unmounts at once.
- `popLayout`: custom components that are direct children should accept a `ref` (a prop in React 19) so Motion can measure and pin the element.
- Manual control for non-motion work: `const [isPresent, safeToRemove] = usePresence()` and call `safeToRemove()` when your exit finishes; `useIsPresent()` reads the state without taking over removal. `usePresenceData()` reads the `custom` value.
- Directional transitions (carousel, wizard): pass `custom={direction}` to `AnimatePresence` and to the motion child, and use variant functions `exit: (dir) => ({ x: dir * -40, opacity: 0 })`.

## 2. Layout animations

```tsx
<motion.div layout style={{ borderRadius: 12 }}>
  {expanded ? <Details /> : <Summary />}
</motion.div>
```

- `layout`: animates position and size changes caused by any re-render (class change, children, reorder). Values: `true`, `"position"` (only position, avoids stretching content), `"size"`, `"preserve-aspect"`.
- Animation uses transforms, which can distort children and border radius or box shadow during scale. Set `borderRadius` and `boxShadow` through `style` on the motion element so Motion corrects them, and give text children `layout="position"` or their own `layout` to avoid stretching.
- `layoutDependency`: re-measure layout only when this value changes, which reduces measurement cost.
- `layoutScroll`: add to scrollable ancestors so measurements account for their scroll offset. `layoutRoot`: marks a container such that its `layoutId` descendants animate relative to it (recent versions animate `layoutId` elements relative to the closest `layoutRoot`), useful with fixed-position or transformed ancestors.
- `layoutAnchor` configures a custom anchor for resolving relative projection boxes (added in the 12.x line); check the docs before using it.
- Layout features are part of `domMax`, not `domAnimation`, when using `LazyMotion`.
- `LayoutGroup`: wrap sibling components that each own `layout` elements so a change in one triggers measurement in the others; `<LayoutGroup id="nav">` namespaces `layoutId`s when the same component renders multiple times.
- `animateLayout` offers layout animations for vanilla JS (added in 14.1.0).

## 3. Shared elements with layoutId

```tsx
"use client"

import { AnimatePresence, LayoutGroup, motion } from "motion/react"
import { useState } from "react"

const tabs = ["Overview", "Usage", "Pricing"]

export function Tabs() {
  const [active, setActive] = useState(tabs[0])
  return (
    <LayoutGroup id="docs-tabs">
      <div role="tablist" className="flex gap-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            onClick={() => setActive(tab)}
            className="relative px-3 py-1"
          >
            {tab}
            {active === tab && (
              <motion.span
                layoutId="tab-underline"
                className="absolute inset-x-0 -bottom-px h-0.5 bg-primary"
              />
            )}
          </button>
        ))}
      </div>
    </LayoutGroup>
  )
}
```

- Two elements with the same `layoutId` are treated as one: when one unmounts and the other mounts, Motion animates from the old box to the new one. Only one should be present at a time unless wrapped in `AnimatePresence` for crossfades.
- Card-to-modal: render the card with `layoutId={"card-" + id}` and the modal's container with the same id inside `AnimatePresence`; fade the backdrop separately. Handle focus (move into the modal, restore on close) and Escape yourself.
- Recent fixes (14.x) changed how `layoutId` elements animate relative to `layoutRoot` and allow changing `layoutId` after mount; if behavior differs from older tutorials, read the changelog.
- Keep `layoutId` strings unique per logical element, and namespace with `LayoutGroup id` when a component can appear more than once.

## 4. Reorder

`Reorder.Group axis="y" values={items} onReorder={setItems}` with `Reorder.Item value={item} key={item.id}` gives drag-to-reorder lists. Keys must be stable ids. Recent versions add keyboard reordering (focus the first item, arrow keys move focus, grab-and-move to reorder), multi-dimensional reorder, RTL and `onReorder` second argument (`moved`). A `LazyMotion`-compatible import exists in 14.x; check the docs for the path. Always offer a non-drag alternative (move up/down buttons) for accessibility.

## 5. Next.js App Router boundaries

- Motion components use hooks and refs, so they run on the client. A file importing `motion` from `motion/react` needs `"use client"` at its top (or must be imported by a client component).
- `import * as motion from "motion/react-client"` provides motion elements already marked as client components, so a Server Component can render `<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} />`. Props must be serializable: no event handlers, no functions, no refs.
- Put interactive pieces in small client components (`FadeIn`, `Reveal`, `MotionProvider`) and keep pages as Server Components that compose them.
- `app/layout.tsx` should stay a Server Component; mount a client `MotionProvider` inside it for `MotionConfig` and `LazyMotion`.
- `app/**/template.tsx` re-mounts on every navigation, which makes enter animations simple: wrap `children` in `<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>`.
- Exit animations between routes with `AnimatePresence` are not reliable in the App Router because the layout tree keeps the outgoing route only briefly. Prefer enter-only transitions, or evaluate `AnimateView` (`motion/react-animate-view`, built on React view transitions, which depends on React's `ViewTransition` support) and check its docs for the required React version.
- Hydration: elements with `initial` styles render those styles on the server. Use `initial={false}` where the server markup should be final, and avoid hiding above-the-fold content.
- Streaming and Suspense: animations replay when Suspense reveals memoized content in recent versions; test loading states.
- Do not import client-only Motion code from `middleware`, route handlers or other server-only modules.

## 6. Gesture and drag notes

- `whileHover` is ignored for touch pointers that do not hover; do not hide essential information behind hover.
- `whileTap` also responds to keyboard activation on focusable elements (press gesture cleanup of keyboard events was improved in 14.5); use real buttons so Enter and Space work natively.
- `drag` with `dragConstraints` accepting a ref or an object; `dragElastic`, `dragMomentum`, `dragSnapToOrigin`; `useDragControls` to start a drag from another element. `drag` and layout animations are in `domMax`.
- `propagate={{ tap: false }}` on a motion element stops its tap gesture from reaching parent motion components (all gestures propagate by default).
