---
name: tailwindcss-master
description: >-
  Builds and maintains Tailwind CSS 4 styling systems with CSS-first configuration (@import "tailwindcss", @theme, @utility, @custom-variant, @variant, @source, @plugin, @reference), the Vite, PostCSS and CLI integrations, the OKLCH default palette, built-in container queries, dark mode through @custom-variant, class sorting with prettier-plugin-tailwindcss, and statically detectable class names. Covers the v3 to v4 upgrade tool and every breaking change. Use when setting up Tailwind 4, writing theme tokens or custom utilities and variants, migrating a tailwind.config.js project, debugging missing classes, or composing class names in components. Not for component library structure (use shadcn-ui-expert), design-system strategy (use ui-designer), accessibility audits (use accessibility-expert), or animation libraries (use framer-motion-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Tailwind CSS Master

This skill covers Tailwind CSS 4: how the CSS-first configuration works, how classes are detected and generated, how to extend the theme with design tokens, custom utilities and variants, how to wire Tailwind into Vite, PostCSS or the CLI, and how to migrate from v3. It focuses on keeping the generated CSS predictable and the class names in components statically analyzable.

> Verified against tailwindcss 4.3.3, @tailwindcss/vite 4.3.3 (Vite 5.2 to 8), @tailwindcss/postcss 4.3.3, @tailwindcss/cli 4.3.3, @tailwindcss/upgrade 4.3.3, prettier-plugin-tailwindcss 0.8.1, tailwind-merge 3.7.0, class-variance-authority 0.7.1, Node.js 22 (2026-10).

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

- Covered: Tailwind CSS 4.x setup and configuration, theme variables, custom utilities and variants, source detection, dark mode, responsive and container-query variants, prefixes, plugins, v3 to v4 migration, formatting and linting for class names, and class composition helpers (`clsx`, `tailwind-merge`, `class-variance-authority`).
- Not covered: Tailwind 3.x projects that stay on v3 (browser support below Safari 16.4, Chrome 111 or Firefox 128 requires v3.4), component library architecture (shadcn-ui-expert), UX and visual design decisions (ui-designer, ux-designer), WCAG audits (accessibility-expert), motion (framer-motion-expert), page speed work (core-web-vitals-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Entry point | One line in your CSS: `@import "tailwindcss";`. It loads the layers `theme, base, components, utilities`, the default theme and Preflight. No `tailwind.config.js` and no `@tailwind` directives |
| Theme variables | `@theme { --color-brand-500: oklch(...); --font-display: ...; --breakpoint-3xl: 120rem; }` creates utilities (`bg-brand-500`, `font-display`, `3xl:*`) and CSS variables. Namespaces include `--color-*`, `--font-*`, `--text-*`, `--font-weight-*`, `--tracking-*`, `--leading-*`, `--breakpoint-*`, `--container-*`, `--spacing`, `--radius-*`, `--shadow-*`, `--blur-*`, `--ease-*`, `--animate-*` |
| Theme options | `@theme inline` (utilities use the value instead of the variable; needed when a theme variable references another variable), `@theme static` (always emit variables), `--color-*: initial;` clears a namespace, `--*: initial;` clears the whole default theme |
| Custom utilities | `@utility name { ... }` (works with all variants); functional `@utility tab-* { tab-size: --value(integer, --default(4)); }` with `--value()` and `--modifier()` |
| Custom variants | `@custom-variant dark (&:where(.dark, .dark *));`, block form with `@slot`; `@variant dark { ... }` applies a variant inside custom CSS; 4.3 allows stacked and compound `@variant` |
| Sources | Automatic detection scans the project (respecting `.gitignore`, skipping `node_modules`, binaries, CSS and lockfiles). `@source "../path"`, `@source not "../legacy"`, `@source inline("{hover:,}bg-red-{50,{100..900..100},950}")`, `@import "tailwindcss" source("../src")`, `source(none)` |
| Build integrations | `@tailwindcss/vite` (preferred with Vite), `@tailwindcss/postcss` (Next.js and other PostCSS hosts), `@tailwindcss/cli`, plus `@tailwindcss/webpack` and `@tailwindcss/turbopack` packages; `@tailwindcss/browser` is for prototyping |
| Colors | Default palette in OKLCH; 4.2 added mauve, olive, mist and taupe. `--alpha(var(--color-x) / 50%)` and opacity modifiers such as `bg-black/50` compile to `color-mix()` |
| Layout features | Container queries built in (`@container`, `@sm:`, `@max-md:`, `@min-[475px]:`, named `@container/main` with `@sm/main:`), `not-*`, `in-*`, `nth-*`, `inert`, `starting:`; logical-property utilities (`pbs-*`, `mbs-*`, `inline-*`, `block-*`) since 4.2; `scrollbar-*`, `zoom-*` since 4.3 |
| Compatibility | `@config "./tailwind.config.js"` and `@plugin "@tailwindcss/typography"` load v3-style config and plugins; `corePlugins`, `safelist` and `separator` are not supported |
| Browser baseline | Safari 16.4, Chrome 111, Firefox 128 (relies on `@property`, `color-mix()`, cascade layers) |
| Tooling | `npx @tailwindcss/upgrade` for v3 to v4, `tailwindcss canonicalize` to normalize class lists, `prettier-plugin-tailwindcss` for ordering, `eslint-plugin-better-tailwindcss` for lint rules |

## 3. Workflow

1. Check browser support requirements. If Safari below 16.4, Chrome below 111 or Firefox below 128 matters, stay on v3.4.
2. Install the integration that matches the build tool: `tailwindcss` plus `@tailwindcss/vite`, `@tailwindcss/postcss` or `@tailwindcss/cli`.
3. Create one entry stylesheet with `@import "tailwindcss";` and import it once from the app entry.
4. Put design tokens in `@theme` (colors in OKLCH, fonts, breakpoints, easing, animations); reference them through utilities, not hard-coded values.
5. Write components with complete, static class strings; map props to class names through lookup objects or `cva`.
6. Add custom utilities (`@utility`) and variants (`@custom-variant`) for repeated patterns instead of long arbitrary values or `@apply` chains.
7. Set the dark mode strategy (media query default, or `@custom-variant dark` with a class or data attribute) before building dark styles.
8. Add `prettier-plugin-tailwindcss` with `tailwindStylesheet` pointing at the entry CSS and check the production build output size.
9. For migrations, run the upgrade tool on a clean branch, then read the diff using [references/upgrade-from-v3.md](references/upgrade-from-v3.md).

## 4. Decision Rules

- Vite project: `@tailwindcss/vite`. Other PostCSS pipelines (including Next.js): `@tailwindcss/postcss`. No bundler: `@tailwindcss/cli`. Do not combine two integrations.
- Remove `postcss-import` and `autoprefixer` when using `@tailwindcss/postcss`; v4 handles imports and vendor prefixes.
- Token that should create a utility: `@theme`. Plain variable that should not: `:root { --x: ... }`.
- A theme variable that references another variable (for example `--font-sans: var(--font-inter)`): use `@theme inline`.
- Repeated class combination: component abstraction (React/Vue component, partial) first; `@utility` when it is a single-purpose CSS pattern; `@apply` mainly for third-party markup you do not control.
- Variant depends on state or attributes: `@custom-variant`. A one-off selector: arbitrary variant `[&>svg]:size-4`.
- Dark mode: media query default for system-only; `@custom-variant dark (&:where(.dark, .dark *));` or `[data-theme=dark]` for a user toggle.
- Container queries (`@container` + `@md:`) for components that live in different layout widths; viewport breakpoints for page-level layout.
- Spacing between children: prefer `flex`/`grid` with `gap-*` over `space-x-*`/`space-y-*` (selector changed in v4).
- Classes that exist only at runtime (CMS-provided names): `@source inline(...)` safelist with explicit ranges, or avoid driving styles from arbitrary strings.
- Tailwind with Sass, Less or Stylus: not supported; use native CSS nesting and variables.
- CSS modules, Vue/Svelte `<style>` blocks needing `@apply`: add `@reference "../app.css";` (or `@reference "tailwindcss";`) at the top, or use `var(--color-*)` directly. Each separately processed stylesheet costs a Tailwind run, so prefer utilities in markup.

## 5. Coding Standards

- Class names appear as complete literal strings in source files. Never build them from fragments (`` `bg-${color}-500` ``); use lookup objects of full class strings.
- Order classes with `prettier-plugin-tailwindcss`; do not hand-sort. Configure `tailwindFunctions` for helper names such as `cn`, `cva` and `clsx`.
- Use the v4 syntax: `shadow-xs`, `rounded-xs`, `outline-hidden`, `ring-3`, opacity modifiers (`bg-black/50`), important suffix (`flex!`), variable shorthand with parentheses (`bg-(--brand)`), and variants stacked left to right (`dark:hover:bg-brand-600`).
- Define colors in OKLCH when adding tokens; name tokens by role when possible (`--color-surface`, `--color-accent`) and map raw palette values underneath.
- Keep `@theme` at the top level of the stylesheet, not nested in selectors or media queries.
- Prefer theme variables over the deprecated `theme()` function; in CSS write `var(--color-red-500)`, and `theme(--breakpoint-xl)` only inside media queries.
- Use logical utilities (`ms-*`, `me-*`, `ps-*`, `pe-*`, `inline-*`, `block-*`) for layouts that must support right-to-left text.
- Keep arbitrary values (`w-[137px]`) rare; add a theme token when a value repeats.
- Write interactive states with `hover:`, `focus-visible:`, `disabled:`, `aria-*:` and `data-*:` variants rather than JavaScript-driven class toggling where possible.

## 6. Project Structure

```
.
├── package.json
├── vite.config.ts              # @tailwindcss/vite plugin (or postcss.config.mjs)
├── .prettierrc.json            # prettier-plugin-tailwindcss + tailwindStylesheet
├── src/
│   ├── styles/
│   │   ├── app.css             # @import "tailwindcss"; @source; @plugin; dark variant
│   │   ├── theme.css           # @theme tokens (importable by other apps/packages)
│   │   ├── utilities.css       # @utility definitions
│   │   └── base.css            # @layer base element defaults
│   ├── components/
│   │   └── button.tsx          # cva variants with full class strings
│   ├── lib/cn.ts               # clsx + tailwind-merge helper
│   └── main.tsx                # imports styles/app.css once
└── index.html
```

## 7. Design Patterns

- **Token layer**: `theme.css` holds `@theme` tokens; apps import it (`@import "../brand/theme.css";`) so several projects share one design language. In a design system, reset the defaults with `--color-*: initial;` and define only the palette you ship.
- **Semantic color variables**: raw palette in `@theme`, role variables switched per theme (`--surface`) and exposed with `@theme inline { --color-surface: var(--surface); }`, so `bg-surface` follows the active theme without `dark:` variants everywhere.
- **Variant maps**: component props map to full class strings with `cva`; `tailwind-merge` resolves conflicts when callers pass extra classes.
- **Container-driven components**: mark the component root with `@container` and size internals with `@sm:`/`@md:`, so the same card works in a sidebar and in a main column.
- **Custom utilities for repeated CSS**: `@utility scrollbar-hidden { ... }` keeps variants working (`md:scrollbar-hidden`).
- **Functional utilities**: `@utility tab-* { tab-size: --value(integer, --default(4)); }` gives `tab`, `tab-2`, `tab-[8]` and theme-driven values.
- **Data and ARIA variants**: style from attributes (`aria-expanded:rotate-90`, `data-[state=open]:block`, `group-data-[open]:...`) to keep state in markup attributes that assistive tech also reads.
- **Safelist by range**: `@source inline("{hover:,}bg-red-{50,{100..900..100},950}")` for classes that cannot appear literally in source.
- Details: [references/v4-configuration.md](references/v4-configuration.md) and [references/patterns-and-tooling.md](references/patterns-and-tooling.md).

## 8. Best Practices

- Keep design decisions in tokens: spacing scale (`--spacing`), type scale (`--text-*`), radii, shadows, easing, and breakpoints.
- Use Preflight's resets as the base; add project defaults in `@layer base` (heading sizes, link colors) instead of per-element overrides.
- Test content at the smallest and largest container sizes, with long words and RTL text.
- Respect user preferences: `motion-reduce:`, `prefers-contrast` variants (`contrast-more:`), `forced-colors:`, and dark mode.
- Use `outline-hidden` (not `outline-none`) when replacing the default focus outline so forced-colors mode still shows focus, and always provide a visible `focus-visible:` style.
- Use the `sr-only` utility for screen-reader text and `not-sr-only` to undo it.
- Document custom utilities and tokens next to their definition with a one-line comment.
- Version-pin `tailwindcss` and all `@tailwindcss/*` packages to the same version.

## 9. Performance

- Tailwind generates only the CSS for classes it finds, so build size follows usage; check the production CSS size after adding safelists (`@source inline` ranges emit every listed class and variant).
- The v4 engine is a Rust-based scanner plus Lightning CSS; the v4.0 release notes report builds up to 5x faster for full builds and over 100x faster for incremental builds.
- Limit scanning: `@source not "./legacy"` and `@import "tailwindcss" source("../src")` in monorepos where the build runs from the repository root; `source(none)` plus explicit `@source` entries for multi-stylesheet projects.
- Avoid one Tailwind run per CSS module or component style block (`@reference` makes each a separate compile); keep styling in utilities.
- Use native CSS features the framework already flattens (nesting, variables, `color-mix()`) rather than preprocessors.
- Prefer `gap` and `grid` over `space-*`/`divide-*` on large lists.
- Ship the compiled CSS as one cacheable file with content hashing; avoid runtime compilation (`@tailwindcss/browser`) in production.

## 10. Security

- Production CSS should be a static file; keep `style-src 'self'` in the Content-Security-Policy and do not add `unsafe-inline` for Tailwind. `@tailwindcss/browser` compiles styles in the browser at runtime, so use it only for prototypes and demos.
- The dark-mode toggle snippet is commonly inlined in `<head>`; serve it as an external script or protect an inline copy with a nonce or hash.
- `@plugin` and `@config` execute JavaScript from packages or files at build time. Treat them like any build dependency: pin versions, review sources, and do not load plugins from untrusted paths.
- Pin and audit `tailwindcss`, `@tailwindcss/*`, `prettier-plugin-tailwindcss`, `tailwind-merge`, and CDN-hosted scripts (use Subresource Integrity if a CDN script is unavoidable).
- User-controlled HTML (CMS, Markdown, comments) can carry class attributes such as `fixed inset-0 z-50` that overlay the page. Sanitize HTML with an allowlist that strips `class` (or restricts it), and scope typography output (`prose`) to a sanitized container.
- Never interpolate user input into class names or `@source`/`@import` paths; class names should come from fixed lookup tables.
- Do not put secrets in CSS custom properties or theme variables; the stylesheet is public.
- Review third-party CSS imported with `@import url(...)`; prefer local copies.

## 11. Testing

- Build check in CI: compile the CSS (`vite build`, `@tailwindcss/cli --minify`) and fail on errors; unknown utilities in `@apply` abort the build.
- Snapshot or assert on critical generated rules by building a small fixture stylesheet and searching the output for expected selectors (for example `.btn-primary`, a custom `@utility`, a safelisted class).
- Use `npx @tailwindcss/cli canonicalize "px-4 py-4"` to verify class lists collapse to canonical forms (`p-4`) when cleaning up code.
- Visual regression tests (Playwright screenshots) for components in light, dark and narrow-container states; accessibility checks (axe) for contrast and focus.
- Lint with `eslint-plugin-better-tailwindcss` (unknown classes, conflicting classes, canonical form) and format with Prettier.
- For migrations, run the upgrade tool on a branch, build, and compare screenshots against v3 for pages that use `space-*`, `divide-*`, `ring`, `shadow-sm`, `border` without a color, and buttons.

## 12. Review Checklist

- [ ] One entry stylesheet imports `tailwindcss`; no `@tailwind` directives, `postcss-import` or `autoprefixer` left.
- [ ] All class names are complete literals or come from lookup maps; no string-built classes.
- [ ] Tokens live in `@theme` at top level; variable-referencing tokens use `@theme inline`.
- [ ] Dark mode strategy is explicit (`@custom-variant dark` if class or attribute based).
- [ ] v4 renames applied (`shadow-xs`, `rounded-xs`, `outline-hidden`, `ring-3`, `flex!`, `bg-(--x)`); no removed utilities (`bg-opacity-*`, `flex-grow`, `overflow-ellipsis`).
- [ ] Borders, dividers and rings specify a color (default is `currentcolor`).
- [ ] `@source` entries cover external UI libraries in `node_modules`; ignored paths are intentional.
- [ ] Focus-visible styles exist; reduced-motion and forced-colors considered.
- [ ] Prettier plugin configured with `tailwindStylesheet`; CI builds the CSS.
- [ ] No untrusted input in class names; CSP has no `unsafe-inline` for styles.

## 13. Production Notes

- Vite and PostCSS builds optimize and minify CSS in production mode; with the CLI pass `--minify` (or `--optimize`).
- Output uses cascade layers and `@property`, so serve the CSS to supported browsers only; there is no automatic fallback for older ones.
- `npx @tailwindcss/upgrade` needs Node.js 20 or newer; run it in a new branch with a clean working tree so the diff is reviewable. It rewrites config to CSS, templates and dependencies, but it can leave things for manual follow-up (see the reference).
- The upgrade tool cannot process `@apply` of utilities removed in v4 (for example `bg-opacity-50`); replace them with opacity modifiers before running it.
- Source detection reads `.gitignore`; a dependency listed there is skipped unless registered with `@source`.
- Monorepo packages that ship Tailwind classes need consumers to register them with `@source "../node_modules/@acme/ui"` (or the workspace path).
- Cascade-layer order is `theme, base, components, utilities`; unlayered third-party CSS beats layered rules, so import third-party CSS inside a layer (`@import "lib.css" layer(components);`) when you need utilities to win.
- Details: [references/upgrade-from-v3.md](references/upgrade-from-v3.md).

## 14. Examples

Entry stylesheet with tokens, semantic colors, a data-attribute dark variant, a functional utility and a component (compiled with tailwindcss 4.3.3):

```css
@import "tailwindcss";

@source "../node_modules/@acme/ui";          /* classes inside a gitignored dependency */
@source not "./legacy";                        /* directory without Tailwind classes */

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@theme {
  --font-display: "Satoshi", sans-serif;
  --breakpoint-3xl: 120rem;
  --color-brand-500: oklch(0.62 0.19 259);
  --color-brand-600: oklch(0.55 0.2 259);
  --ease-snappy: cubic-bezier(0.2, 0, 0, 1);
  --animate-fade-in: fade-in 0.2s var(--ease-snappy);

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
}

/* Role-based colors that change with the theme; inline so utilities use the variable reference */
@theme inline {
  --color-surface: var(--surface);
}
:root { --surface: oklch(0.99 0 0); }
[data-theme="dark"] { --surface: oklch(0.2 0.02 260); }

@utility tab-* {
  tab-size: --value(integer, --default(4));    /* tab, tab-2, tab-[8] */
}

@utility scrollbar-hidden {
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}

@layer components {
  .btn-primary {
    @apply rounded-lg bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600;
  }
}
```

Vite setup (install `tailwindcss` and `@tailwindcss/vite`):

```ts
// vite.config.ts
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
});
```

```css
/* src/style.css, imported from the app entry or linked from index.html */
@import "tailwindcss";
```

PostCSS hosts use `postcss.config.mjs` with `export default { plugins: { "@tailwindcss/postcss": {} } };`. The CLI form is `npx @tailwindcss/cli -i src/app.css -o dist/app.css --minify`.

Component variants with full class strings, `cva` and `tailwind-merge` (type-checked with TypeScript 7):

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { cva, type VariantProps } from "class-variance-authority";

export const cn = (...inputs: ClassValue[]): string => twMerge(clsx(inputs));

export const button = cva(
  "inline-flex items-center justify-center rounded-md font-medium focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      intent: {
        primary: "bg-blue-600 text-white hover:bg-blue-500 focus-visible:outline-blue-600",
        danger: "bg-red-600 text-white hover:bg-red-500 focus-visible:outline-red-600",
        ghost: "bg-transparent text-neutral-900 hover:bg-neutral-100 dark:text-neutral-50 dark:hover:bg-neutral-800",
      },
      size: { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" },
    },
    defaultVariants: { intent: "primary", size: "md" },
  },
);
export type ButtonProps = VariantProps<typeof button>;

// cn(button({ intent: "danger", size: "lg" }), "px-2 bg-black") keeps only the last px-* and bg-* classes
```

## 15. Common Mistakes

- **Dynamic class names** (`` `bg-${color}-600` ``, `"text-" + tone`): Tailwind scans text and never sees the complete class, so no CSS is generated. Use a map of full strings (`{ blue: "bg-blue-600", red: "bg-red-600" }`) or `@source inline(...)`.
- **Keeping `@tailwind base; @tailwind components; @tailwind utilities;`**: removed in v4. Use `@import "tailwindcss";`.
- **Leaving `tailwindcss` as the PostCSS plugin**: v4 needs `@tailwindcss/postcss` (and no `postcss-import` or `autoprefixer`).
- **Expecting `tailwind.config.js` to load automatically**: not detected in v4. Move settings to CSS or load explicitly with `@config`.
- **Using `@layer utilities { .foo {} }` for custom utilities**: those no longer get variants. Use `@utility foo { ... }`.
- **Border, divide or ring without a color**: defaults changed to `currentcolor` (and `ring` is 1px). Add colors, or `ring-3` plus an explicit color for the old look.
- **`outline-none` to remove focus rings**: it now means `outline-style: none`; use `outline-hidden` for the old invisible-outline behavior and keep a visible focus style.
- **`@apply` in CSS modules, Vue or Svelte style blocks without `@reference`**: theme, utilities and variants from other files are not available there.
- **Referencing a variable-based token without `@theme inline`**: the utility resolves the variable where it is defined and can fall back unexpectedly.
- **Sass, Less or Stylus pipelines**: not supported; remove them before adding Tailwind.
- **Old stacking order**: variants apply left to right in v4 (`*:first:pt-0` instead of v3's `first:*:pt-0`); reverse order-sensitive stacks from v3.
- **Relying on `hover:` for touch devices**: in v4 `hover` applies only when the primary input supports hover; restore the old behavior with `@custom-variant hover (&:hover);` only if needed.
- **Mixing different `@tailwindcss/*` versions**: keep all packages on the same version.
- **Scanning surprises**: classes in a dependency listed in `.gitignore` or `node_modules` are skipped; register it with `@source`.

## 16. References

- [references/v4-configuration.md](references/v4-configuration.md): directives and functions, theme namespaces and options, source detection, custom utilities and variants, dark mode, prefixes, plugins, container queries, integrations (Vite, PostCSS, CLI, frameworks) and cascade layers.
- [references/upgrade-from-v3.md](references/upgrade-from-v3.md): using `@tailwindcss/upgrade`, what it changes, what it leaves, and every v3 to v4 breaking change with replacements.
- [references/patterns-and-tooling.md](references/patterns-and-tooling.md): class composition helpers, Prettier and ESLint setup, accessibility utilities, theming with CSS variables, third-party CSS and markup, debugging missing classes.
- Official docs: https://tailwindcss.com/docs , https://tailwindcss.com/docs/upgrade-guide , https://tailwindcss.com/docs/theme , https://tailwindcss.com/docs/detecting-classes-in-source-files , https://tailwindcss.com/docs/functions-and-directives , https://github.com/tailwindlabs/tailwindcss
