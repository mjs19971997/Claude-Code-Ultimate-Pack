# Tailwind CSS 4 Configuration

Reference for CSS-first configuration in Tailwind CSS 4: installation paths, directives and functions, theme variables, source detection, custom utilities and variants, dark mode, prefixes, container queries, plugins and cascade layers. Verified against tailwindcss 4.3.3, @tailwindcss/vite 4.3.3, @tailwindcss/postcss 4.3.3 and @tailwindcss/cli 4.3.3 (2026-10); snippets in sections 1 to 8 were compiled with these versions. The official docs at tailwindcss.com are the source for prose and the full utility reference.

## 1. Installation paths

Vite (`npm install tailwindcss @tailwindcss/vite`):

```ts
// vite.config.ts
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({ plugins: [tailwindcss()] });
```

PostCSS hosts such as Next.js (`npm install tailwindcss @tailwindcss/postcss postcss`):

```js
// postcss.config.mjs
export default { plugins: { "@tailwindcss/postcss": {} } };
```

CLI (`npm install tailwindcss @tailwindcss/cli`):

```sh
npx @tailwindcss/cli -i ./src/app.css -o ./dist/app.css --minify
npx @tailwindcss/cli -i ./src/app.css -o ./dist/app.css --watch
```

In every case the stylesheet starts with:

```css
@import "tailwindcss";
```

- `@tailwindcss/vite` declares Vite 5.2 through 8 as peer versions. `@tailwindcss/webpack` and `@tailwindcss/turbopack` also exist for those bundlers; follow the framework guide on tailwindcss.com for the current setup.
- `@tailwindcss/browser` compiles in the browser at runtime and is meant for prototyping.
- The CLI also offers `--optimize`, `--map`, `--cwd`, and `--poll` for watch mode when file events are unreliable.
- `tailwindcss canonicalize [classes...]` (CLI) rewrites class lists into canonical form, for example `px-4 py-4` to `p-4`; `--css input.css` loads a custom design system and `--stream` reads lines from stdin.
- Imports, vendor prefixes and nested CSS are handled by Tailwind (via Lightning CSS), so `postcss-import`, `autoprefixer` and Sass are unnecessary. Sass, Less and Stylus are not supported as preprocessors for Tailwind stylesheets.

## 2. Directives and functions

| Directive or function | Purpose |
|---|---|
| `@import "tailwindcss";` | Loads theme, Preflight and utilities (layers `theme, base, components, utilities`) |
| `@import "tailwindcss" prefix(tw);` | Adds a class prefix |
| `@import "tailwindcss" source("../src");` / `source(none)` | Sets the scanning base path or disables automatic detection |
| `@theme { ... }` | Defines design tokens that generate utilities and CSS variables; options `inline`, `static` |
| `@source "path";` / `@source not "path";` | Adds or excludes scanned paths relative to the stylesheet |
| `@source inline("...")` / `@source not inline("...")` | Safelists or blocks specific generated classes (brace expansion supported) |
| `@utility name { ... }` | Registers a custom utility (simple, nested or functional with `*`) |
| `@custom-variant name (selector);` | Registers a custom variant (shorthand or block with `@slot`) |
| `@variant name { ... }` | Applies a variant to custom CSS; 4.3 supports stacked (`hover:focus`) and compound (`hover, focus`) forms |
| `@apply classes;` | Inlines utilities into custom CSS |
| `@reference "path";` | Imports theme, utilities and variants for `@apply` without emitting CSS (Vue, Svelte, CSS modules) |
| `@plugin "package-or-path";` | Loads a JavaScript plugin (for example `@tailwindcss/typography`) |
| `@config "path";` | Loads a legacy `tailwind.config.js`; `corePlugins`, `safelist`, `separator` unsupported |
| `--alpha(color / 50%)` | Compiles to `color-mix()` for opacity |
| `--spacing(4)` | Compiles to `calc(var(--spacing) * 4)`, also usable inside arbitrary values and `calc()` |
| `--value()`, `--modifier()`, `--default()` | Argument resolution inside functional `@utility` definitions |
| `theme(--breakpoint-xl)` | Deprecated function; still useful inside media queries where `var()` is not allowed |

Subpath imports (`"imports": { "#app.css": "./src/css/app.css" }` in `package.json`) work in `@import`, `@reference`, `@plugin` and `@config` when using the CLI, Vite or PostCSS.

## 3. Theme variables

```css
@import "tailwindcss";

@theme {
  --font-display: "Satoshi", sans-serif;
  --breakpoint-3xl: 120rem;
  --color-brand-500: oklch(0.62 0.19 259);
  --ease-snappy: cubic-bezier(0.2, 0, 0, 1);
  --animate-fade-in: fade-in 0.2s var(--ease-snappy);

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
}
```

Generated utilities: `font-display`, `3xl:*` variant, `bg-brand-500`/`text-brand-500`/`border-brand-500`, `ease-snappy`, `animate-fade-in`. Every theme variable also becomes a CSS variable on `:root` (only used ones by default).

Namespaces and what they drive:

| Namespace | Drives |
|---|---|
| `--color-*` | Color utilities (`bg-*`, `text-*`, `border-*`, `fill-*`, ...) |
| `--font-*` | `font-family` utilities |
| `--text-*` | Font size utilities (with `--text-xl--line-height` style companions) |
| `--font-weight-*`, `--tracking-*`, `--leading-*` | Weight, letter spacing, line height |
| `--breakpoint-*` | Responsive variants (`sm`, `md`, `lg`, `xl`, `2xl` default to 40, 48, 64, 80, 96rem) |
| `--container-*` | Container query variants (`@sm`, `@md`) and `max-w-*` sizes |
| `--spacing` | Base unit (default `0.25rem`) for `p-*`, `m-*`, `w-*`, `gap-*` and more |
| `--radius-*`, `--shadow-*`, `--inset-shadow-*`, `--drop-shadow-*`, `--blur-*` | Radii, shadows, filters |
| `--ease-*`, `--animate-*` | Timing functions and animations |
| `--perspective-*`, `--aspect-*`, `--tab-size-*`, `--zoom-*` | Other utility families (`--zoom-*` since 4.3) |

Options and patterns:

- Override one value by redefining it (`--breakpoint-sm: 30rem;`).
- Clear a namespace with `--color-*: initial;` then define your own colors; clear everything with `--*: initial;`.
- `@theme inline { --font-sans: var(--font-inter); }` makes utilities use the variable's value instead of `var(--font-sans)`, which avoids resolution surprises when the referenced variable is defined deeper in the tree. Use it for tokens that reference other variables, including theme-switching variables.
- `@theme static { ... }` always emits the variables even if no utility uses them.
- `@theme` must be top-level. Keep non-utility variables in `:root`.
- Keyframes inside `@theme` are emitted with the animation token; keyframes outside `@theme` are always emitted.
- Theme variables are available in custom CSS (`var(--color-brand-500)`, `var(--text-xl)`, `var(--radius-xl)`) and in JavaScript via `getComputedStyle(document.documentElement).getPropertyValue("--shadow-xl")`.
- With a prefix, generated variables are prefixed too (`--tw-color-brand-500`), while the `@theme` definitions stay unprefixed.
- Share a theme across projects by putting `@theme` in its own CSS file and importing it: `@import "tailwindcss"; @import "../brand/theme.css";`.
- Default colors are OKLCH values (for example `--color-red-500: oklch(63.7% 0.237 25.331)`).

Customizing Preflight (the base reset) by importing the pieces yourself:

```css
@layer theme, base, components, utilities;
@import "tailwindcss/theme.css" layer(theme);
@import "tailwindcss/utilities.css" layer(utilities);
```

Add `@import "tailwindcss/preflight.css" layer(base);` back when you want it.

## 4. Source detection

- Tailwind reads files as plain text and extracts tokens that look like class names; it does not execute or parse code. Dynamically constructed names are therefore invisible.
- Skipped by default: files in `.gitignore`, `node_modules`, binary files, CSS files, lockfiles.
- Register extra sources relative to the stylesheet: `@source "../node_modules/@acme/ui-lib";`.
- Exclude paths: `@source not "../src/components/legacy";`.
- Set the base path for monorepos: `@import "tailwindcss" source("../src");`; disable detection with `source(none)` and list `@source` entries.
- Safelist by pattern with brace expansion: `@source inline("{hover:,focus:,}underline");` and ranges `@source inline("{hover:,}bg-red-{50,{100..900..100},950}");`. Block classes with `@source not inline("container");`.
- Use a safelist only for classes that cannot appear literally in source (CMS-provided names); each listed class and variant adds CSS.

## 5. Custom utilities

```css
@utility content-auto {
  content-visibility: auto;
}

@utility scrollbar-hidden {
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}

@utility tab-* {
  tab-size: --value(integer, --default(4));   /* tab, tab-2, tab-[8] */
}

@theme { --tab-size-github: 8; }
@utility tab-* {
  tab-size: --value(--tab-size-*, integer, [integer]);   /* theme key, bare integer, arbitrary */
}
```

- Custom utilities work with every variant (`hover:content-auto`, `lg:scrollbar-hidden`) and land in the `utilities` layer.
- `--value()` accepts theme keys (`--tab-size-*`), bare types (`integer`, `number`, `ratio`, `percentage`), quoted literals (`"inherit"`), and bracketed arbitrary types (`[integer]`, `[length]`, `[color]`, `[*]`). Several arguments resolve left to right; multiple declarations let you treat each form differently, and declarations that fail to resolve are omitted.
- `--modifier()` works like `--value()` for the part after the slash (`tab-2/3`).
- Negative values need a separate `@utility -inset-*` definition with the sign applied in the declaration.
- Fractions use the `ratio` type (`aspect-3/4`).
- `--default()` supplies a value when the utility is used bare (`tab`).
- Customize `container` by extending it: `@utility container { margin-inline: auto; padding-inline: 2rem; }`.
- Custom utilities are ordered by how many properties they set, so a multi-property component-like utility can be overridden by single-purpose utilities without extra configuration.

Components and base styles use cascade layers:

```css
@layer base {
  h1 { @apply text-2xl font-semibold; }
}

@layer components {
  .btn-primary {
    @apply rounded-lg bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600;
  }
}
```

- `@layer components` no longer registers classes as utilities with variants; use `@utility` when you want variants.
- Unlayered CSS beats layered CSS regardless of specificity. Import third-party CSS into a layer: `@import "./lib.css" layer(components);`.

## 6. Custom variants

```css
@custom-variant theme-midnight (&:where([data-theme="midnight"] *));

@custom-variant any-hover {
  @media (any-hover: hover) {
    &:hover {
      @slot;
    }
  }
}
```

- Use as `theme-midnight:bg-black` or `any-hover:underline`.
- `@variant dark { ... }` inside custom CSS applies the project's `dark` definition to a rule.
- Arbitrary variants cover one-offs: `[&>svg]:size-4`, `[@media(min-width:900px)]:grid`.
- Stacked variants apply left to right: `dark:hover:bg-brand-600`, `*:first:pt-0`.

## 7. Dark mode

- Default: the `dark:` variant follows `prefers-color-scheme`.
- Class-based: `@custom-variant dark (&:where(.dark, .dark *));`.
- Attribute-based: `@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));`.
- Three-way (light, dark, system) toggle: store the choice in `localStorage` and set the class or attribute on `<html>` before first paint, with a small script that falls back to `window.matchMedia("(prefers-color-scheme: dark)")` when no choice is stored. Serve the script as an external file or with a nonce/hash if your CSP blocks inline scripts.
- For themes with many colors, switch CSS variables per theme and expose them with `@theme inline` (see SKILL.md), so components use `bg-surface` rather than repeating `dark:` pairs.

## 8. Prefixes, plugins and legacy config

- `@import "tailwindcss" prefix(tw);` makes utilities `tw:flex`, `tw:hover:bg-accent`; the prefix looks like a variant and always comes first. The important marker goes at the end: `tw:flex!`.
- `@plugin "@tailwindcss/typography";` and `@plugin "@tailwindcss/forms";` load official plugins (they are separate packages). Plugin JavaScript runs at build time.
- `@config "../../tailwind.config.js";` keeps an old config alive during migration; define new tokens in CSS and migrate gradually. JavaScript config files are no longer auto-detected.
- `resolveConfig` no longer exists; read CSS variables instead.

## 9. Container queries and responsive variants

- Mark a container with `@container`, then style children with `@sm:`, `@md:`, `@lg:` ... or ranges with `@max-md:`, `@min-[475px]:`; combine like `@sm:@max-md:flex-col`.
- Name containers with `@container/main` and target them with `@sm/main:`.
- `@container-size` (4.3) creates a size container so units like `cqb` work.
- Viewport breakpoints (`sm:`, `md:`, ...) are mobile-first (`min-width`); use `max-md:` for below-breakpoint rules and ranges like `md:max-xl:`.
- Data and ARIA variants: `aria-expanded:`, `aria-[sort=ascending]:`, `data-[state=open]:`, `group-data-[...]:`, `peer-checked:`; state variants `not-hover:`, `in-focus:`, `has-[:checked]:`, `inert:`, `starting:` (for `@starting-style` transitions).
- Motion and contrast: `motion-reduce:`, `motion-safe:`, `contrast-more:`, `forced-colors:`.

## 10. Preflight and base styles

- Preflight (built on modern-normalize) removes default margins, sets `box-sizing: border-box`, resets borders to `0 solid`, makes images and media block-level and responsive, and un-styles headings and lists.
- It lives in the `base` layer; add project defaults in `@layer base` and keep component rules in `@layer components` or as React/Vue components.
- Because borders default to `currentcolor` in v4, always specify a border color (`border border-neutral-200`).
