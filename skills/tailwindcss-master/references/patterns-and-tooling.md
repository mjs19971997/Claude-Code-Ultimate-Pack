# Patterns and Tooling

Reference for composing Tailwind classes in components, theming with CSS variables, formatting and linting class names, accessibility-related utilities and debugging missing styles. Verified against tailwindcss 4.3.3, prettier-plugin-tailwindcss 0.8.1, prettier 3.9, eslint-plugin-better-tailwindcss 4.10.0, tailwind-merge 3.7.0, clsx 2.1.1, class-variance-authority 0.7.1 and TypeScript 7.0.2 (2026-10). The Prettier, ESLint and class-helper snippets were executed.

## 1. Class composition

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- `clsx` joins conditional class values; `twMerge` removes earlier classes that conflict with later ones, so a caller can override a component default (`cn("px-6 bg-red-600", "px-2 bg-black")` keeps `px-2 bg-black`).
- tailwind-merge 3.x targets Tailwind CSS 4 class names; 2.x targets v3. If you add custom theme tokens (for example a `text-hero` font size or `bg-brand-500`), check the tailwind-merge docs for extending its config so it recognizes them.
- `class-variance-authority` (`cva`) maps props to complete class strings and gives typed variant props through `VariantProps`. `tailwind-variants` is an alternative with built-in merging.
- Write full class strings inside variant maps. Do not assemble `bg-${intent}-600`.
- Keep `cn` at the outermost layer of a component (`className={cn(button({ intent, size }), className)}`) so callers can adjust spacing and color.

```ts
import { cva, type VariantProps } from "class-variance-authority";

export const badge = cva("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100",
      success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
      danger: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
    },
  },
  defaultVariants: { tone: "neutral" },
});
export type BadgeProps = VariantProps<typeof badge>;
```

## 2. Theming with CSS variables

```css
@import "tailwindcss";

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

:root {
  --surface: oklch(0.99 0 0);
  --surface-raised: oklch(1 0 0);
  --ink: oklch(0.2 0.02 260);
  --accent: oklch(0.55 0.2 259);
}
[data-theme="dark"] {
  --surface: oklch(0.18 0.02 260);
  --surface-raised: oklch(0.23 0.02 260);
  --ink: oklch(0.96 0.01 260);
  --accent: oklch(0.72 0.14 259);
}

@theme inline {
  --color-surface: var(--surface);
  --color-surface-raised: var(--surface-raised);
  --color-ink: var(--ink);
  --color-accent: var(--accent);
}
```

- `bg-surface`, `text-ink`, `border-accent` follow the active theme; individual components need `dark:` only for exceptions.
- `@theme inline` is required here because the tokens reference other variables.
- Check contrast for each theme pair (WCAG AA is 4.5:1 for body text); OKLCH lightness differences are a quick guide but not a substitute for measuring.
- Keep brand scales (`--color-brand-50` to `-950`) in `@theme` and map semantic roles onto them.
- Respect system preferences by default; if you add a toggle, store the choice and apply the attribute before first paint (external script or nonce/hash for an inline one).
- Multi-brand or white-label apps can swap an attribute (`data-brand="acme"`) that redefines the variables; Tailwind output stays the same.

## 3. Prettier and ESLint

Prettier class sorting:

```json
{
  "plugins": ["prettier-plugin-tailwindcss"],
  "tailwindStylesheet": "./src/app.css",
  "tailwindFunctions": ["cn", "cva", "clsx"]
}
```

- `tailwindStylesheet` points to the CSS entry file for v4 projects (`tailwindEntryPoint` is the deprecated name; `tailwindConfig` is for v3 JavaScript configs). Paths resolve relative to the Prettier config.
- `tailwindFunctions` lists helper calls whose string arguments should be sorted; `tailwindAttributes` adds attributes beyond `class` and `className`.
- If you use other Prettier plugins, load `prettier-plugin-tailwindcss` last (the plugin documents compatible combinations).
- Example result: `cn("p-4 flex text-white bg-black items-center", open && "hidden md:block")` is sorted to `"flex items-center bg-black p-4 text-white"`.

ESLint with `eslint-plugin-better-tailwindcss` (flat config; TSX parsing shown with typescript-eslint):

```js
// eslint.config.mjs
import tseslint from "typescript-eslint";
import betterTailwind from "eslint-plugin-better-tailwindcss";

export default [
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { parser: tseslint.parser, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { "better-tailwindcss": betterTailwind },
    settings: { "better-tailwindcss": { entryPoint: "src/app.css" } },
    rules: { ...betterTailwind.configs.recommended.rules },
  },
];
```

- The recommended set includes `no-unknown-classes`, `no-conflicting-classes`, `no-deprecated-classes`, `enforce-canonical-classes`, `no-duplicate-classes`, class order and whitespace rules. In the test run it reported a deprecated `flex-shrink-0`, class order, and wrapping.
- The plugin is aware of `cn`, `clsx`, `cva`, `twMerge` and similar helpers; for custom helpers see its advanced configuration (callees, attributes, variables).
- Typescript-eslint's peer range for TypeScript is `>=4.8.4 <6.1.0` (8.72.1), so lint with TypeScript 6 until it supports 7 (see the typescript-master skill).

## 4. Accessibility utilities

- Focus: replace the default outline deliberately. `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600` gives a visible ring only for keyboard focus. If you must hide the default outline, use `outline-hidden` (which still shows in forced-colors mode) and add your own indicator.
- Screen-reader-only text: `sr-only`; undo with `not-sr-only` (for skip links: `sr-only focus:not-sr-only`).
- Motion: `motion-reduce:transition-none motion-reduce:animate-none`, or gate animations with `motion-safe:`.
- Contrast and forced colors: `contrast-more:` and `forced-colors:` variants adjust borders and backgrounds for those modes.
- State from attributes: `aria-expanded:`, `aria-disabled:`, `aria-invalid:`, `data-[state=open]:` keep visual state tied to the attributes assistive technology reads.
- Do not rely on color alone: pair `text-red-700` with an icon or text for errors.
- Touch targets: keep interactive elements at least about 24 by 24 CSS pixels (`min-h-6 min-w-6`), larger for primary actions; use `pointer-coarse:` to enlarge for touch.
- For deeper audits, use the accessibility-expert skill.

## 5. Third-party CSS and markup you do not control

- Style Markdown or CMS HTML with `@tailwindcss/typography` (`@plugin "@tailwindcss/typography";`, then `prose` and `dark:prose-invert`), or write element rules in `@layer components` using theme variables (`font-size: var(--text-base)`).
- Override third-party widgets with `@apply` inside a stylesheet that is part of your main CSS build, or use `@reference` in a separate file.
- Import third-party CSS into a layer so utilities can override it: `@import "./vendor/widget.css" layer(components);`.
- Sanitize user-supplied HTML (allowlist, remove `class` attributes or restrict them) before rendering; classes such as `fixed inset-0` can overlay your UI.

## 6. Debugging missing or wrong styles

1. Is the class a complete literal in a scanned file? Search the source for the exact string; fragments and template concatenation are not detected.
2. Is the file scanned? Files in `.gitignore`, `node_modules`, binary files and CSS files are skipped; add `@source` for libraries, and check the `source(...)` base path in monorepos.
3. Does the class exist in v4? Removed names (`bg-opacity-50`, `flex-grow`) generate nothing. Run `npx @tailwindcss/cli canonicalize "your classes"` or the ESLint `no-unknown-classes` rule.
4. Does a theme token exist? `bg-brand-500` needs `--color-brand-500` in `@theme`; `--color-*: initial;` removed the defaults.
5. Is the variant defined? `dark:` without `@custom-variant` follows the media query, not your class or attribute.
6. Cascade: unlayered CSS beats layered; check that custom CSS is inside `@layer base` or `@layer components`, and that third-party CSS is imported into a layer.
7. Variable resolution: a token that references another variable without `@theme inline` can resolve to an unexpected value.
8. Prefix: with `prefix(tw)` every class and variant starts with `tw:`; custom CSS uses prefixed variables (`--tw-color-accent`).
9. Compiled output: build with the CLI to a file and search for the selector (`grep -n "btn-primary" out.css`); a missing selector means detection or definition failed, a present selector with no effect means cascade or specificity.
10. Modifiers that cannot apply (for example `rounded-sm/foo`) generate nothing in recent 4.x releases; remove invalid modifiers.
