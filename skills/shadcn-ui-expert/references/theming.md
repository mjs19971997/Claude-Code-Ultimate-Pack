# Theming and Dark Mode

Reference for theme tokens, Tailwind CSS 4 wiring, OKLCH colors, dark mode and `data-slot` styling in shadcn/ui projects. Verified against shadcn CLI 4.23.0, Tailwind CSS 4.3.x, next-themes 0.4.6 and the shadcn/ui theming and dark-mode docs (2026-10).

## 1. How tokens flow

1. Raw values live in your global CSS under `:root` (light) and `.dark` (dark) as CSS variables, for example `--primary: oklch(0.205 0 0)`.
2. `@theme inline { --color-primary: var(--primary); }` exposes each variable to Tailwind, which generates `bg-primary`, `text-primary`, `border-primary` and so on.
3. Components use only the semantic utilities, so changing a variable restyles every component and dark mode needs no per-component `dark:` classes.
4. `tailwind.cssVariables: true` in `components.json` selects this mode (default). `false` makes the CLI emit raw palette utilities (`bg-zinc-950 dark:bg-white`); it is chosen at init and switching later means reinstalling components.

## 2. Token convention

Surface tokens come in pairs: the base name is the background, `-foreground` is the text or icon color drawn on it. `bg-primary text-primary-foreground` is the canonical use.

| Token | Role |
|---|---|
| `background` / `foreground` | Page background and default text |
| `card` / `card-foreground` | Elevated surfaces such as Card and panels |
| `popover` / `popover-foreground` | Floating surfaces: Popover, DropdownMenu, ContextMenu |
| `primary` / `primary-foreground` | High-emphasis actions and selected states |
| `secondary` / `secondary-foreground` | Lower-emphasis filled actions |
| `muted` / `muted-foreground` | Subtle surfaces, helper text, placeholders |
| `accent` / `accent-foreground` | Hover, focus and active surfaces (ghost buttons, menu highlight) |
| `destructive` | Destructive actions and error emphasis |
| `border`, `input`, `ring` | Borders, control borders, focus rings |
| `chart-1` to `chart-5` | Default chart palette |
| `sidebar`, `sidebar-foreground`, `sidebar-primary`, `sidebar-primary-foreground`, `sidebar-accent`, `sidebar-accent-foreground`, `sidebar-border`, `sidebar-ring` | Sidebar component |
| `radius` | Base corner radius |

Older generated files may also define `--destructive-foreground`; the current default theme scaffold in the docs does not list it as a token, so check your generated CSS before relying on it.

## 3. Global CSS skeleton (Tailwind 4)

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  /* one --color-* line per token in the table above */
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
}

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  /* light values */
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --border: oklch(1 0 0 / 10%);
  /* dark values */
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- `@theme inline` makes utilities reference the variable at use time (`var(--primary)`) rather than copying its value, which is why overriding `--primary` under `.dark` works.
- `shadcn/tailwind.css` ships shared Tailwind 4 utilities and custom variants (`data-open:`, `data-closed:`, `data-checked:`, `data-unchecked:`, `data-selected:`, `data-disabled:`, `data-active:`, `data-horizontal:`, `data-vertical:`) plus accordion keyframes and `no-scrollbar`. `npx shadcn@latest eject` inlines it.
- Keep `tailwind.config` empty in `components.json` for Tailwind 4; there is no JavaScript config to point at.

## 4. OKLCH notes

- Syntax: `oklch(L C H)` or `oklch(L C H / alpha)`. L is lightness (0 to 1), C is chroma (0 is gray), H is hue in degrees.
- Neutral tokens have chroma 0 (`oklch(0.205 0 0)`); tinted themes add small chroma and a hue.
- Dark borders and inputs use alpha on white (`oklch(1 0 0 / 10%)`) so they adapt to the surface under them.
- Lightness is perceptually even, so adjusting L by the same amount gives comparable contrast steps across hues. Still verify text/background contrast with a checker; token pairs are not guaranteed to meet WCAG after you change them (accessibility-expert covers conformance).
- Browsers without OKLCH support are rare in current evergreen versions; check your support matrix and Tailwind's own compatibility notes before shipping to older browsers.

## 5. Adding a token

```css
:root {
  --warning: oklch(0.84 0.16 84);
  --warning-foreground: oklch(0.28 0.07 46);
}
.dark {
  --warning: oklch(0.41 0.11 46);
  --warning-foreground: oklch(0.99 0.02 95);
}
@theme inline {
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
}
```

Now `bg-warning text-warning-foreground` work. A registry item can ship the same through `cssVars` (`theme`, `light`, `dark`).

## 6. Radius scale

`--radius` is the base; `radius-sm` to `radius-4xl` are multiples of it (0.6, 0.8, 1, 1.4, 1.8, 2.2, 2.6 times). Change `--radius` once to restyle corners everywhere.

## 7. Base colors and presets

- `tailwind.baseColor`: `neutral`, `stone`, `zinc`, `mauve`, `olive`, `mist`, `taupe`. It seeds the generated tokens at `init` or when a preset is applied.
- Change it later with `npx shadcn@latest migrate base-color --to zinc --yes` (optionally `--from`). Tokens that no longer match the source color are left untouched and reported.
- shadcn/create (the website) lets you pick style, colors, radius, fonts and icons and gives a preset code. Use `init --preset <code>` for new projects and `apply <code>` for existing ones; `apply <code> --only theme` (or `font`) limits what is rewritten. `preset decode <code> --json` shows what a code contains.

## 8. Dark mode with next-themes

```bash
npm install next-themes
```

```tsx
// components/theme-provider.tsx
"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
```

```tsx
// app/layout.tsx
import { ThemeProvider } from "@/components/theme-provider"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- `attribute="class"` toggles the `dark` class on `<html>`, which matches `@custom-variant dark (&:is(.dark *))` and the `.dark` token block.
- `suppressHydrationWarning` on `<html>` is required because next-themes sets the class before React hydrates.
- A toggle reads and sets the theme with the `useTheme()` hook (`theme`, `setTheme`, `resolvedTheme`); render theme-dependent UI only after mount, or use CSS (`dark:`) so server and client markup match.
- Vite and other frameworks: next-themes works without Next.js; follow the framework page in the shadcn dark-mode docs.
- The sonner `Toaster` component reads `useTheme()` from next-themes, so it follows the same setting; keep it inside the provider.

## 9. `data-slot` styling

Components set `data-slot` on their root parts, for example `button`, `card`, `card-header`, `dialog-content`, `field`, `field-set`. Use it to restyle without reaching into class names.

```tsx
// Parent controls how Cards look inside a dashboard grid.
<section className="grid gap-4 [&_[data-slot=card]]:shadow-none">
  <Card>...</Card>
</section>

// Direct-child detection inside a component (pattern used by FieldSet).
// has-[>[data-slot=checkbox-group]]:gap-3
```

- `Button` also exposes `data-variant` and `data-size`, which you can target (`data-[variant=outline]:...`).
- Keep `data-slot` when you edit a component; other components and user CSS depend on it.
- Prefer slot selectors from a parent over editing the child file when the change is page-specific.

## 10. Recipes

- **Brand color**: edit `--primary`, `--primary-foreground`, `--ring` and the sidebar equivalents in both blocks; check contrast of the pair.
- **Second theme**: add a class such as `.theme-blue { --primary: ...; }` and apply it on a wrapper; tokens cascade, so only the overrides are needed.
- **Fonts**: define `--font-sans` and friends in `@theme inline` (the CLI can install fonts through presets or `registry:font` items).
- **Per-section dark**: add the `dark` class to a wrapper element; tokens switch for that subtree.
