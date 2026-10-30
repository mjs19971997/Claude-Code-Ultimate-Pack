---
name: ui-designer
description: >-
  Turns product intent into a consistent visual system: design tokens, colour in OKLCH, type and spacing scales, component states, theming and dark mode, layout grids and motion guidelines, encoded so designers and engineers share one source. Use when defining or reviewing design tokens, CSS custom properties, a Tailwind theme, typography or spacing scales, colour palettes and contrast, dark mode, component state matrices, Figma-to-code handoff, or visual polish of a screen. Not for research, flows and information architecture (use ux-designer), WCAG audits and ARIA (use accessibility-expert), or component library specifics (use shadcn-ui-expert or tailwindcss-master).
license: MIT
metadata:
  version: "3.0.0"
---

# UI Designer

This skill covers the visual layer of a product and how it is expressed in code: tokens, colour, typography, spacing, elevation, iconography, component states, theming and motion guidelines. It aims for systems that stay consistent as teams and screens grow. It does not cover user research or task flows, and it treats accessibility rules as constraints rather than auditing them in depth.

> Verified against CSS Color Module 4 (`oklch()`, `color-mix()`, `light-dark()`), CSS container queries, the Design Tokens Community Group format 2025.10 (first stable version), Tailwind CSS 4.3 `@theme`, Style Dictionary 5.7, and WCAG 2.2 contrast criteria (2026-10).

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
10. [Testing](#10-testing)
11. [Review Checklist](#11-review-checklist)
12. [Examples](#12-examples)
13. [Common Mistakes](#13-common-mistakes)
14. [References](#14-references)

## 1. Scope

- Design tokens and their layering (primitive, semantic, component).
- Colour systems, palettes and contrast; light, dark and high-contrast themes.
- Typography (families, scales, line height, measure), spacing and sizing scales, radii, shadows and elevation, z-index layers.
- Layout: grids, responsive and container-based layouts.
- Component anatomy and state matrices (default, hover, focus-visible, active, selected, disabled, loading, error, empty).
- Motion guidelines (durations, easing, reduced motion) at the system level.
- Handoff: Figma variables and Dev Mode, token export, Storybook as the living reference.

## 2. Core Expertise

- **Visual hierarchy**: size, weight, colour, contrast, space and position used deliberately to show what matters first.
- **Gestalt grouping**: proximity, similarity, alignment and common region drive grouping more than borders and boxes.
- **Colour**: OKLCH for perceptually even ramps (equal lightness steps look equal across hues); sRGB fallbacks only where old browsers matter; Display P3 for vivid accents where supported. OKLCH lightness is not a contrast guarantee; always compute WCAG contrast for real pairs.
- **Contrast floors** (WCAG 2.2): 4.5:1 body text, 3:1 large text, 3:1 for UI boundaries, focus indicators and meaningful graphics.
- **Typography**: a modular scale (for example ratio 1.125 to 1.25 for dense UIs, larger for editorial), unitless line height (about 1.4 to 1.6 for body, tighter for headings), measure of roughly 45 to 75 characters, variable fonts to reduce files.
- **Spacing**: a 4 px base step (common 4/8 px rhythm) expressed in `rem`; consistent internal and external spacing per component.
- **Tokens**: DTCG format (`$value`, `$type`, `$description`, aliases with `{group.token}`) as the exchange format; CSS custom properties as the runtime format.
- **Theming**: semantic tokens remapped per theme; `color-scheme` and `light-dark()` for native controls and simple pairs.
- **Responsive design**: content-first breakpoints, container queries for components that live in different widths, fluid type with `clamp()`.
- **Elevation**: a small set of shadow levels; in dark themes, show elevation with lighter surfaces rather than stronger shadows.
- **Motion**: short durations (roughly 100 to 300 ms for UI feedback), ease-out for entering, ease-in for leaving, and a reduced-motion alternative for every animation.

## 3. Workflow

1. Clarify the product context: audience, brand attributes, density (data-heavy tool or marketing page), platforms and themes required.
2. Audit what exists: collect colours, font sizes, spacings and radii in use; count near-duplicates.
3. Define primitives: colour ramps, type scale, spacing scale, radii, shadows, durations.
4. Define semantic tokens on top: surface, text, border, accent, danger, success, focus ring; map each to primitives per theme.
5. Check every foreground/background semantic pair for contrast in every theme before building components.
6. Design components with a full state matrix; add component tokens only where a component must differ from semantic defaults.
7. Encode tokens in one source (DTCG JSON or Figma variables), generate CSS variables and framework config from it.
8. Document usage in Storybook or a docs site: when to use each token and component, with do/don't examples.
9. Review screens against the system; feed real gaps back as new tokens or variants instead of one-off values.

## 4. Decision Rules

- Semantic tokens in components, primitives only inside token definitions. A component that references `--blue-600` cannot be re-themed.
- OKLCH for new palettes; keep hex/sRGB values only as generated fallbacks.
- Fluid type with `clamp()` for headings and display text; keep body text close to the user's default size and always include a `rem` term so browser zoom and font-size settings still scale it (1.4.4).
- Container queries for reusable components (cards, media objects); media queries for page-level layout.
- Dark theme: use dark neutral surfaces with a few lighter elevation steps; reduce saturation of large accent areas; recheck contrast rather than inverting values.
- New token only when at least two places need the value or it encodes a real decision; otherwise use an existing token.
- One icon set, one stroke weight, aligned to the text baseline and sized from the type scale.
- Motion only when it explains a change (where something came from, what changed); otherwise none.
- When brand colour fails contrast as text, keep it for fills and large shapes and use a darker or lighter step for text.

## 5. Coding Standards

- Units: `rem` for type and spacing, `em` for component-relative padding where it should scale with font size, `px` only for hairlines.
- Line height unitless; letter spacing in `em`.
- Token names describe role, not value: `--color-text-muted`, not `--gray-500` in components.
- Naming scheme (pick one and keep it): `--{category}-{role}-{variant}-{state}`, for example `--color-bg-accent-hover`, `--space-4`, `--radius-md`, `--shadow-2`, `--duration-fast`, `--ease-out`.
- Component tokens are namespaced: `--button-bg`, `--button-fg`, defaulting to semantic tokens.
- Focus indicator: `:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }`; never remove it without a replacement.
- Do not hard-code colours, shadows or durations in components; lint for raw hex/`rgb()` values outside token files (Stylelint `color-no-hex` or a custom rule).
- Tokens are versioned with semver; renaming or removing a token is a breaking change and needs a migration note.

## 6. Project Structure

```
design-system/
├── tokens/
│   ├── primitives.tokens.json     # colour ramps, type scale, spacing, radii, durations
│   ├── semantic.light.tokens.json # role tokens for the light theme (aliases to primitives)
│   ├── semantic.dark.tokens.json
│   └── components.tokens.json     # only where a component deviates from semantic defaults
├── build/                         # generated: css/variables.css, js/tokens.ts (never edited by hand)
├── style-dictionary.config.mjs
└── docs/                          # usage guidance, contrast tables
apps/web/src/styles/
├── tokens.css                     # imports build output; theme selectors
└── base.css                       # element defaults, focus, reduced motion
```

## 7. Design Patterns

- **Three-layer tokens**: primitive (`blue-600`) to semantic (`color-bg-accent`) to component (`button-bg`). Themes swap only the semantic layer.
- **Theme by attribute**: `:root` holds the default theme, `[data-theme="dark"]` (and `@media (prefers-color-scheme: dark)` for the system default) remaps semantic tokens.
- **State layers**: derive hover/pressed from the base colour with `color-mix(in oklch, var(--color-bg-accent), black 10%)` so new accents get states automatically.
- **State matrix**: for every component, a grid of variant by state (default, hover, focus-visible, active, disabled, loading, error) reviewed in every theme.
- **Compound radius**: `--radius` as the base, smaller and larger radii derived with `calc()`, so the whole UI can be made sharper or softer in one place.
- **Container-query card**: the card switches from stacked to side-by-side based on its own width, not the viewport.
- **Elevation scale**: three to five shadow levels mapped to UI layers (raised, overlay, modal), paired with z-index tokens.

## 8. Best Practices

- Start from content and real data, not lorem ipsum; long names, empty values and large numbers change layouts.
- Keep the type scale short (six to eight sizes); most screens need three or four.
- Align to a consistent spacing rhythm; uneven spacing reads as error.
- Limit accent colours; use colour for meaning (status, selection, primary action), not decoration.
- Pair colour with icons or text for status so it survives colour-vision deficiencies and forced-colors mode.
- Design disabled states that are still legible; WCAG exempts inactive controls from contrast, but users still need to read them.
- Check designs at 320 CSS px width, at 200% zoom and with the largest OS text size.
- Provide a `forced-colors: active` review: borders and outlines must still show structure when backgrounds are overridden.
- Document "why" next to tokens (for example "use for secondary text, never below 14 px").

## 9. Performance

- Load at most a few font files; prefer one variable font per family, `woff2`, subset to the scripts in use, `font-display: swap` (or `optional` for non-essential faces).
- Use size-adjusted fallback fonts (`size-adjust`, `ascent-override`) to reduce layout shift when web fonts swap in; framework font loaders such as `next/font` do this automatically.
- Prefer CSS effects over images for gradients, shadows and shapes; keep large blur and backdrop-filter effects off scrolling content.
- Ship icons as inline SVG or an SVG sprite, not icon fonts.
- Media always has `width`/`height` or `aspect-ratio`. Loading-speed work belongs to core-web-vitals-expert.

## 10. Testing

- Contrast tests: generate a table of every semantic foreground/background pair per theme and fail the build if a pair falls below its required ratio.
- Visual regression (Chromatic, Percy or Playwright screenshots) per component state and theme.
- Storybook stories for every variant and state; include long-text and RTL stories.
- Check `prefers-reduced-motion`, `prefers-color-scheme`, `forced-colors` and `prefers-contrast` with browser emulation (Playwright `emulateMedia`).

## 11. Review Checklist

- [ ] No raw colours, sizes or durations in components; tokens used.
- [ ] Semantic pairs pass contrast in every theme and state.
- [ ] Focus-visible style present, at least 3:1 against adjacent colours.
- [ ] Full state matrix designed and implemented.
- [ ] Type uses the scale; fluid sizes include a `rem` term.
- [ ] Spacing follows the scale; no unexplained one-off values.
- [ ] Dark theme designed, not inverted; elevation readable.
- [ ] Layout holds at 320 CSS px, 200% zoom, long content and RTL.
- [ ] Motion follows the duration/easing tokens and has a reduced-motion path.
- [ ] Token additions documented and versioned; removals carry a migration note.

## 12. Examples

### Fluid type scale

```css
/* src/styles/typography.css */
:root {
  --font-sans: "Inter", system-ui, sans-serif;
  --text-sm: 0.875rem;
  --text-md: 1rem;
  --text-lg: clamp(1.125rem, 1.05rem + 0.35vw, 1.25rem);
  --text-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.75rem);
  --text-2xl: clamp(1.5rem, 1.2rem + 1.5vw, 2.25rem);
  --text-3xl: clamp(1.875rem, 1.4rem + 2.4vw, 3rem);
  --leading-tight: 1.2;
  --leading-body: 1.5;
}

body { font-family: var(--font-sans); font-size: var(--text-md); line-height: var(--leading-body); }
h1 { font-size: var(--text-3xl); line-height: var(--leading-tight); letter-spacing: -0.02em; }
h2 { font-size: var(--text-2xl); line-height: var(--leading-tight); }
```

### Semantic colour tokens with themes

```css
/* src/styles/tokens.css */
:root {
  color-scheme: light;
  --color-bg: oklch(0.99 0 0);
  --color-text: oklch(0.21 0.01 260);
  --color-text-muted: oklch(0.45 0.02 260);
  --color-border: oklch(0.88 0.01 260);
  --color-bg-accent: oklch(0.52 0.19 260);
  --color-text-on-accent: oklch(0.99 0 0);
  --color-focus: oklch(0.52 0.19 260);
  --color-danger: oklch(0.53 0.21 27);
}

[data-theme="dark"] {
  color-scheme: dark;
  --color-bg: oklch(0.18 0.01 260);
  --color-text: oklch(0.96 0 0);
  --color-text-muted: oklch(0.75 0.02 260);
  --color-border: oklch(0.34 0.01 260);
  --color-bg-accent: oklch(0.72 0.15 260);
  --color-text-on-accent: oklch(0.18 0.01 260);
  --color-focus: oklch(0.78 0.14 260);
  --color-danger: oklch(0.72 0.17 27);
}

.button-primary {
  background: var(--color-bg-accent);
  color: var(--color-text-on-accent);
}
.button-primary:hover {
  background: color-mix(in oklch, var(--color-bg-accent), var(--color-text) 12%);
}
```

The values are a starting point; run every pair through a contrast checker before shipping.

### Motion tokens with a reduced-motion path

```css
/* src/styles/motion.css */
:root {
  --duration-fast: 120ms;
  --duration-base: 200ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
}

.popover[data-state="open"] {
  animation: popover-in var(--duration-base) var(--ease-out);
}

@keyframes popover-in {
  from { opacity: 0; transform: translateY(4px) scale(0.98); }
  to { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  .popover[data-state="open"] { animation: fade-in var(--duration-fast) linear; }
}

@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
```

## 13. Common Mistakes

- **Hard-coded hex values in components**: breaks theming and audits. Reference semantic tokens.
- **Palette chosen without contrast checks**: a beautiful ramp still fails 4.5:1 for muted text. Check pairs, not swatches.
- **Assuming equal OKLCH lightness means equal contrast**: WCAG contrast uses relative luminance; compute it.
- **`clamp()` with only `vw` units**: text stops responding to zoom and user font size. Include a `rem` term.
- **Pixel font sizes everywhere**: ignore user font-size preferences. Use `rem`.
- **Dark mode by inverting colours**: produces glaring accents and muddy borders. Design dark semantic values separately.
- **Too many near-identical greys and spacings**: consolidate into the scale; one-offs become tomorrow's inconsistency.
- **Removing focus outlines for aesthetics**: keyboard users lose their place. Design a branded focus style instead.
- **Colour as the only status signal**: add text or icons.
- **Designing only the default state**: hover, focus, disabled, loading, error and empty states get invented ad hoc in code.
- **Tokens renamed without a migration path**: breaks consumers silently. Version and deprecate first.

## 14. References

- [references/tokens-and-theming.md](references/tokens-and-theming.md): token layering, DTCG source files, Style Dictionary and Tailwind v4 output, theme switching without a flash of the wrong theme.
- Official docs: https://www.designtokens.org/ , https://www.w3.org/TR/css-color-4/ , https://tailwindcss.com/docs/theme , https://styledictionary.com/ , https://www.w3.org/TR/WCAG22/
