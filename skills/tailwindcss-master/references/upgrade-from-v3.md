# Upgrading from Tailwind CSS 3 to 4

Reference for migrating v3 projects to Tailwind CSS 4: the upgrade tool, what it did in a test run, what to check by hand, and every documented breaking change with its replacement. Verified against tailwindcss 4.3.3 and @tailwindcss/upgrade 4.3.3, run on a small v3.4.19 project with a JavaScript config, PostCSS config and `@apply` rules (2026-10), and against the official v4 upgrade guide.

## 1. Before you start

- Browser baseline for v4: Safari 16.4, Chrome 111, Firefox 128. If you must support older browsers, stay on v3.4.
- The upgrade tool requires Node.js 20 or newer.
- Start from a clean working tree on a new branch so the tool's diff is reviewable. Build and test the project first so you have a baseline (screenshots of key pages help).
- Remove or replace utilities that v4 deleted when they appear inside `@apply`: the tool cannot compile a stylesheet that applies a removed utility (in the test run `@apply ... bg-opacity-50` aborted the migration with "Cannot apply unknown utility class `bg-opacity-50`"). Use opacity modifiers (`bg-black/50`) there first.
- Sass, Less and Stylus stylesheets are not supported by Tailwind 4; convert them to plain CSS first.

## 2. Running the tool

```sh
git switch -c tailwind-v4
npx @tailwindcss/upgrade
```

It checks the installed version against `package.json`, so run `npm install` first if they disagree. Review the diff, then build and test.

What the tool did in the test project:

| Area | Result |
|---|---|
| Stylesheet | Replaced `@tailwind base/components/utilities` with `@import 'tailwindcss';` |
| `tailwind.config.js` | Converted `theme.extend.colors` and `fontFamily` into an `@theme` block and deleted the file |
| Dark mode | `darkMode: "class"` became `@custom-variant dark (&:is(.dark *));` |
| Border default | Added an `@layer base` rule that restores `border-color: var(--color-gray-200, currentcolor)` for compatibility |
| Templates | Renamed utilities: `shadow-sm` to `shadow-xs`, `rounded` to `rounded-sm`, `ring` to `ring-3`, `outline-none` to `outline-hidden`, `flex-grow` to `grow`, `overflow-ellipsis` to `text-ellipsis`; moved `!flex` to `flex!` |
| `@apply` | Renamed `rounded shadow-sm ring outline-none` inside the `@apply` rule |
| Dependencies | Updated `tailwindcss` to 4.x and installed `@tailwindcss/postcss` |
| PostCSS config | Replaced `tailwindcss` with `@tailwindcss/postcss` |

What it left for manual follow-up in the same run:

- `bg-opacity-50` in markup (removed utility; use `bg-black/50`).
- `flex-shrink-0` inside an `@apply` rule (use `shrink-0`).
- `autoprefixer` in the PostCSS config (no longer needed; remove it and `postcss-import`).
- The compatibility border-color rule, which you may keep or replace by adding explicit border colors.

Always grep the diff for removed utilities (section 4) and run the build.

## 3. Manual migration steps

PostCSS:

```js
// postcss.config.mjs
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

Vite: remove the PostCSS setup and use the plugin.

```ts
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({ plugins: [tailwindcss()] });
```

CLI: replace `npx tailwindcss -i input.css -o output.css` with `npx @tailwindcss/cli -i input.css -o output.css`.

Stylesheet:

```css
@import "tailwindcss";
```

Legacy config you cannot migrate yet:

```css
@config "../../tailwind.config.js";
@plugin "@tailwindcss/typography";
```

`corePlugins`, `safelist` and `separator` do not work in v4; use `@source inline(...)` for safelists. `resolveConfig` is gone; read CSS variables (`getComputedStyle(document.documentElement).getPropertyValue("--color-blue-500")`).

## 4. Removed and renamed utilities

Removed (replacement):

| v3 | v4 |
|---|---|
| `bg-opacity-*`, `text-opacity-*`, `border-opacity-*`, `divide-opacity-*`, `ring-opacity-*`, `placeholder-opacity-*` | Opacity modifiers: `bg-black/50`, `text-black/50`, ... |
| `flex-shrink-*` | `shrink-*` |
| `flex-grow-*` | `grow-*` |
| `overflow-ellipsis` | `text-ellipsis` |
| `decoration-slice`, `decoration-clone` | `box-decoration-slice`, `box-decoration-clone` |

Renamed (scale shifted so every utility has a named size):

| v3 | v4 |
|---|---|
| `shadow-sm` / `shadow` | `shadow-xs` / `shadow-sm` |
| `drop-shadow-sm` / `drop-shadow` | `drop-shadow-xs` / `drop-shadow-sm` |
| `blur-sm` / `blur` | `blur-xs` / `blur-sm` |
| `backdrop-blur-sm` / `backdrop-blur` | `backdrop-blur-xs` / `backdrop-blur-sm` |
| `rounded-sm` / `rounded` | `rounded-xs` / `rounded-sm` |
| `outline-none` | `outline-hidden` (the new `outline-none` sets `outline-style: none`) |
| `ring` (3px) | `ring-3` (bare `ring` is 1px) |

The bare names (`shadow`, `rounded`, `blur`) still work for compatibility but resolve to the new smaller values, so rename `-sm` first, then the bare names.

## 5. Behavior changes

| Change | What to do |
|---|---|
| Default border and divide color is `currentcolor` (was `gray-200`) | Add explicit colors (`border-gray-200`), or add the compatibility `@layer base` rule for `*, ::after, ::before, ::backdrop, ::file-selector-button` |
| Default `ring` is 1px and `currentcolor` (was 3px `blue-500`) | Use `ring-3 ring-blue-500`, or set `--default-ring-width` and `--default-ring-color` in `@theme` (compatibility only) |
| `outline` sets a 1px width; `outline-<n>` implies solid style | Drop redundant `outline` next to `outline-2` |
| `space-x/y-*` and `divide-x/y-*` selectors changed to `:not(:last-child)` | Check inline elements and children with custom margins; prefer `flex`/`grid` with `gap-*` |
| Variants with gradients keep the other stops | Use `via-none` to unset a middle stop in a state |
| Variants stack left to right | Reverse order-sensitive stacks: `first:*:pt-0` becomes `*:first:pt-0` |
| Important modifier goes at the end | `!flex` becomes `flex!` (the old form still works but is deprecated) |
| CSS variable shorthand uses parentheses | `bg-[--brand]` becomes `bg-(--brand)` |
| Commas in `grid-cols-*`, `grid-rows-*`, `object-*` arbitrary values no longer become spaces | Use underscores: `grid-cols-[max-content_auto]` |
| `hover:` applies only when the device supports hover (`@media (hover: hover)`) | Treat hover as an enhancement, or restore with `@custom-variant hover (&:hover);` |
| `transition` and `transition-colors` include `outline-color` | Set outline colors in both states to avoid unexpected transitions |
| `rotate-*`, `scale-*`, `translate-*` use individual CSS properties | `transform-none` no longer resets them; reset `rotate-none`, `scale-none`, `translate-none`; include them in custom `transition-[...]` lists |
| Prefix looks like a variant and comes first | `tw:flex`, and `@import "tailwindcss" prefix(tw);`; theme variables stay unprefixed in `@theme`, generated variables are prefixed |
| `container` options (`center`, `padding`) removed | `@utility container { margin-inline: auto; padding-inline: 2rem; }` |
| `@layer utilities` / `@layer components` custom classes no longer get variants | Use `@utility name { ... }` |
| `theme()` function | Use `var(--color-red-500)`; in media queries `theme(--breakpoint-xl)` |
| `corePlugins` option | Removed; no replacement |
| `@apply` in Vue, Svelte, Astro `<style>` blocks and CSS modules | Add `@reference "../app.css";` or use `var(--...)` |
| Sass, Less, Stylus | Unsupported |

Preflight changes:

- Placeholder text uses the current text color at 50% opacity (was `gray-400`).
- Buttons use `cursor: default` (was `pointer`). Restore with `@layer base { button:not(:disabled), [role="button"]:not(:disabled) { cursor: pointer; } }` if desired.
- `<dialog>` margins are reset; add `dialog { margin: auto; }` in `@layer base` to keep centered dialogs.
- Display utilities (`block`, `flex`) no longer override the `hidden` attribute (except `hidden="until-found"`).
- The 4.3.3 changelog notes the default font stacks now use explicit platform fonts instead of `system-ui`/`ui-sans-serif`; verify typography if you depended on the old stack.

## 6. Post-upgrade checklist

1. Build, then diff the key pages visually against v3 (focus on borders, rings, shadows, rounded corners, inline `space-*` usage, form controls and dialogs).
2. Search for removed utilities and old syntax: `bg-opacity-`, `text-opacity-`, `flex-shrink`, `flex-grow`, `overflow-ellipsis`, `\[--`, `@tailwind `, `theme(`, `@layer utilities`, `@layer components`.
3. Remove `postcss-import` and `autoprefixer`; remove `tailwind.config.js` once its content lives in CSS.
4. Check third-party plugins (`@plugin`) still support v4 (the official typography and forms packages include v4 in their peer ranges; the container-queries plugin is unnecessary because container queries are built in).
5. Configure `prettier-plugin-tailwindcss` with `tailwindStylesheet` and run it across the repo to normalize class order.
6. Run `npx @tailwindcss/cli canonicalize` on class lists in a few components to see suggested canonical forms, or enable the corresponding lint rule.
7. Pin all `@tailwindcss/*` packages to the same version as `tailwindcss`.
