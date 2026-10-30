---
name: shadcn-ui-expert
description: >-
  Builds and maintains UIs with shadcn/ui: the shadcn CLI (init, add, apply, view, search, migrate, build), components.json, Radix or Base UI component bases, Tailwind CSS 4 with OKLCH CSS-variable theming, data-slot styling hooks, Field-based forms with React Hook Form or TanStack Form, sonner toasts, Recharts charts, next-themes dark mode, and custom registries. Use when adding or customizing shadcn components, changing theme tokens, wiring a form, publishing a private component registry, or migrating older shadcn code (forwardRef, HSL variables, tailwind.config). Not for general Tailwind configuration (use tailwindcss-master) or a visual design system (use ui-designer).
license: MIT
metadata:
  version: "3.0.0"
---

# shadcn/ui Expert

shadcn/ui is a set of components whose source is copied into your repository, plus a CLI and a registry format for distributing them. This skill covers the CLI and `components.json`, picking a component base, theming with Tailwind CSS 4 and OKLCH variables, editing owned components safely, forms, toasts, charts, dark mode and authoring registries. It targets React 19 function components where `ref` is an ordinary prop and `forwardRef` is not used.

> Verified against shadcn CLI 4.23.0 (npm `shadcn`, Node >= 20.18.1), Tailwind CSS 4.3.x, React 19.3, next-themes 0.4.6, sonner 2.0.8, Recharts 3.10, Base UI `@base-ui/react` 1.9, unified `radix-ui` 1.8 and the shadcn/ui docs source on GitHub (2026-10).

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

- Covered: `npx shadcn@latest` commands, `components.json`, choosing and migrating the component base, theme tokens and dark mode, extending components with variants and `data-slot`, the Field form pattern, sonner, the chart component, registries (`registry.json`, `registry-item.json`, namespaces, authentication), the shadcn MCP server.
- Not covered: Tailwind setup details, plugins and config beyond shadcn needs (tailwindcss-master), designing a brand or token system from scratch (ui-designer), WCAG conformance review (accessibility-expert), Next.js routing and rendering (nextjs-15-architect), React 19 state and data patterns (senior-react-19-engineer), animation (framer-motion-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Package and runner | The CLI package is `shadcn` (run `npx shadcn@latest <command>`, or `pnpm dlx` / `bunx --bun`). Component code imports `shadcn/tailwind.css` in your CSS, so `shadcn` is also a dependency until you run `eject` |
| Commands | `init` (alias `create`), `add`, `apply`, `preset` (`decode`, `resolve`/`info`, `url`, `open`), `view`, `search` (alias `list`), `build`, `docs`, `info`, `migrate`, `eject`, `mcp init` |
| Component bases | `init --base` accepts `base` (Base UI), `radix` and `aria`. Style IDs combine base and style, for example `radix-nova` and `base-nova`; `style` cannot be changed after init |
| Primitives | Radix projects import from the unified `radix-ui` package and use `asChild`; Base UI projects import from `@base-ui/react/<part>` and use the `render` prop instead of `asChild` |
| Tailwind 4 | No `tailwind.config`: leave `tailwind.config` empty in `components.json`, theme in CSS with `@theme inline`; `@import "tw-animate-css"` and `@import "shadcn/tailwind.css"` provide animations and `data-open`/`data-closed`/`data-checked` style variants |
| Theming | Semantic pairs (`background`/`foreground`, `primary`/`primary-foreground`, ...) as OKLCH CSS variables under `:root` and `.dark`, mapped to utilities through `--color-*` entries in `@theme inline`; `--radius` drives the `radius-*` scale |
| Base colors | `neutral`, `stone`, `zinc`, `mauve`, `olive`, `mist`, `taupe`; `migrate base-color` switches an existing project |
| `data-slot` | Every part renders `data-slot="<name>"` (for example `button`, `dialog-content`, `field-set`) so parents can style children with `has-[>[data-slot=...]]` or `**:data-[slot=...]` selectors; Button also sets `data-variant` and `data-size` |
| `cn` helper | Current components import `cn` from the `cn` package (a drop-in for clsx plus tailwind-merge for Tailwind 4); `lib/utils.ts` re-exports it. `migrate cn` converts older clsx and tailwind-merge code |
| Forms | The forms guides build on `FieldSet`, `FieldGroup`, `Field`, `FieldLabel`, `FieldDescription`, `FieldError` with React Hook Form (`Controller`) or TanStack Form (`form.Field`); the docs list no separate `form` component |
| Registry | `registry.json` lists items (`registry:ui`, `block`, `component`, `hook`, `lib`, `page`, `file`, `theme`, `style`, `base`, `font`, `item`); `shadcn build` writes JSON to `public/r`; `@namespace` registries are configured in `components.json` |

## 3. Workflow

1. Run `npx shadcn@latest info --json` in an existing project to read framework, Tailwind version, aliases, base, icon library and installed components before changing anything.
2. New project: `npx shadcn@latest init -t next` (or `vite`, `start`, `react-router`, `laravel`, `astro`), choose `--base radix` or `--base base`, optionally `--preset <code>` from shadcn/create. Existing project: `npx shadcn@latest init`.
3. Add components with `npx shadcn@latest add button dialog field`. Preview first with `--dry-run`, `--diff` or `--view`; read the docs page for the active base with `npx shadcn@latest docs <component>`.
4. Theme by editing CSS variables in the global CSS file (tokens, `--radius`), not by editing every component. Add new semantic tokens in both `:root` and `.dark` and expose them in `@theme inline`.
5. Customize components in place (they are your code): add a `cva` variant, adjust classes, keep `data-slot` and `className` pass-through intact.
6. Wire dark mode with next-themes (class strategy), forms with the Field pattern, toasts with sonner, charts with the chart component.
7. For shared components across apps, publish a registry: describe items in `registry.json`, run `shadcn build`, host the JSON, and consume it through a namespace in `components.json`.
8. After upgrading the CLI, re-run `add <component> --diff` for components you want updated and merge by hand where you changed the source.

## 4. Decision Rules

- New project: choose the base once. Radix is the long-established primitive set (`asChild`); Base UI is the alternative with the `render` prop. Components, docs and examples are per base, so do not mix snippets from the other base in one project. Check `shadcn docs <component> --base <base>` when unsure.
- Existing project with the legacy per-package imports (`@radix-ui/react-dialog`): run `migrate radix` to consolidate to `radix-ui`; this is not a switch to Base UI.
- A link that looks like a button: use `buttonVariants` on a real `<a>`/`Link` in either base. With Radix, `asChild` also works. With Base UI, do not render `Button` as an anchor; the docs warn that it forces `role="button"` on the link.
- Toasts: sonner (`<Toaster />` from `components/ui/sonner`, `toast()` from `sonner`). Use inline `FieldError` and alerts for validation, toasts for transient confirmation only.
- Forms: React Hook Form when the project already uses it or needs field arrays and performance on large forms; TanStack Form for type-driven validators; a plain `<form action>` with server actions for simple cases. All three use the same Field components.
- `tailwind.cssVariables`: keep `true`. Switching to utility classes (`false`) is an init-time choice and requires reinstalling components.
- Customization: change tokens for global looks, change a component file for structural changes, wrap a component for app-specific behavior. Do not fork shadcn internals via global CSS overrides keyed on class names.
- Share components between repos: a registry (static JSON via `shadcn build`) rather than copying files, unless the components are used in one place.
- Tailwind 3 projects: the current docs target Tailwind 4; the Tailwind 3 docs are archived at v3.shadcn.com. Upgrade Tailwind first rather than mixing generations.

## 5. Coding Standards

- Components are plain function components typed with `React.ComponentProps<"button">` (or the Base UI `Part.Props`) and spread `...props` last. Do not add `forwardRef` or `displayName`; `ref` flows through props in React 19.
- Always merge classes with `cn(...)` and accept `className` last so callers can override.
- Set `data-slot="kebab-name"` on the root element of every new part; add `data-*` attributes (`data-variant`, `data-size`, `data-invalid`) for state that parents or CSS need.
- Use semantic utilities (`bg-background`, `text-muted-foreground`, `border-input`, `ring-ring`) instead of raw palette colors, so themes and dark mode work without `dark:` variants.
- Variants live in `cva` with `defaultVariants`; export the variants function (`buttonVariants`) next to the component for reuse on links.
- Use logical properties (`ms-*`, `ps-*`, `text-start`) in new code if the project enables `rtl` in `components.json` (`migrate rtl` converts existing components).
- Keep `"use client"` only on components that use hooks, state or event handlers; the CLI adds it when `rsc` is `true`.
- Icons come from the library named by `iconLibrary` in `components.json` (`lucide`, `tabler`, `hugeicons`, `phosphor`, `remixicon`); `migrate icons` switches libraries.
- Colors in CSS are `oklch(L C H / alpha)`; do not reintroduce `hsl(var(--x))` wrappers (the pre-Tailwind-4 convention) in new code.

## 6. Project Structure

```
.
├── components.json              # CLI config: style, aliases, tailwind.css, registries
├── app/
│   ├── globals.css              # @import tailwindcss, tw-animate-css, shadcn/tailwind.css; tokens
│   └── layout.tsx               # ThemeProvider, Toaster, <html suppressHydrationWarning>
├── components/
│   ├── ui/                      # shadcn-managed primitives (button.tsx, field.tsx, sonner.tsx ...)
│   ├── theme-provider.tsx       # next-themes wrapper ("use client")
│   └── forms/                   # app forms composed from ui/field + input + button
├── lib/utils.ts                 # export { cn } from "cn"
├── hooks/                       # hooks added by the CLI (aliases.hooks)
└── registry.json                # only when this repo publishes components
```

## 7. Design Patterns

- **Token layers**: raw OKLCH values in `:root`/`.dark`, semantic names through `@theme inline`, components use only semantic utilities. Details in [references/theming.md](references/theming.md).
- **Variant extension**: add a variant to the `cva` call (for example `success` using a `--success` token) instead of passing long `className` strings from call sites.
- **Composition over props**: parts such as `Card`, `CardHeader`, `CardContent` or `Field`, `FieldLabel`, `FieldError` are composed in JSX; wrap them in an app component when a pattern repeats.
- **Slot-aware parents**: a layout component styles children via `data-slot` (`[&_[data-slot=card]]:shadow-none`) rather than reaching for internal class names.
- **Field forms**: `Field` with `data-invalid`, the control with `aria-invalid`, `FieldError` underneath, `FieldGroup` to stack fields. Full code in [references/forms-and-charts.md](references/forms-and-charts.md).
- **Registry as distribution**: items declare `files`, `registryDependencies`, `dependencies`, `cssVars`, so one `add @acme/item` installs code, packages and tokens. See [references/registry-and-cli.md](references/registry-and-cli.md).

## 8. Best Practices

- Commit `components.json` and the generated `components/ui` files; reviewers should see component diffs like any other source.
- Run `add <component> --dry-run` or `--diff` before overwriting, and avoid `--overwrite` on components you have customized.
- Keep one global CSS file for tokens; do not scatter color definitions across components.
- Prefer built-in variants and sizes before inventing new ones, and document custom variants where they are defined.
- Use `FieldLabel htmlFor` with matching control `id`, `FieldDescription` for help, and `FieldError` for messages so labels and errors are programmatically associated.
- Put `<Toaster />` once in the root layout and call `toast()` from client code or server-action callbacks on the client.
- When using monorepos, use `init --monorepo` and run CLI commands with `-c <workspace>`; shared UI lives in one package.
- Pin the CLI in scripts (`shadcn@4.23.0`) for reproducible onboarding, and use `@latest` interactively.

## 9. Performance

- Only the components you add exist in the bundle; remove unused files from `components/ui` and unused packages after a base or icon migration.
- Import icons by name (`import { Check } from "lucide-react"`); do not import whole icon sets or build icon maps from the barrel.
- Charts: lazy-load the chart bundle (`next/dynamic` with a skeleton) on pages where charts are below the fold; Recharts is the largest dependency in typical shadcn apps.
- Keep `ChartContainer` height explicit (`min-h-*`, `aspect-*`) to avoid layout shift and failed first measurement.
- Dialogs, sheets and popovers mount their content on open; avoid heavy children outside `DialogContent` so closed state stays cheap.
- `disableTransitionOnChange` on the theme provider prevents a flash of transitioning colors when toggling dark mode.
- Large data tables: virtualize rows or paginate server-side before tuning component code.

## 10. Security

- Registry items are source code that you install into your app and execute. Inspect with `npx shadcn@latest view @acme/item`, or `add ... --dry-run`/`--view`, before first install and treat updates like dependency updates. Add only registries you trust to `components.json`.
- Never put secrets in registry items, `registry.json` or files under `public/r`; anything in `public/` is world-readable. Serve private items from an authenticated endpoint.
- Registry authentication: reference tokens as `${VAR}` in `headers` inside `components.json` (the CLI expands environment variables) and keep values in `.env.local` or CI secrets, never in the JSON. Prefer headers over `params` for tokens because URLs end up in logs.
- Dynamic registry routes must validate the item name before loading it (`loadRegistryItem` throws `RegistryItemNotFoundError`; map it to 404 and do not echo user input into file paths).
- `dangerouslySetInnerHTML`, `eval` and unreviewed `<script>` snippets do not belong in components; if a registry item contains them, reject it.
- Rendering user content in toasts, tooltips or chart labels goes through React text nodes (escaped); do not pass untrusted HTML strings.
- Validate form input on the server as well; client-side Zod validation improves UX but is not a security boundary.
- Third-party registries with `registryDependencies` URLs can pull from other hosts; review the dependency chain shown by `view`.

## 11. Testing

- Query by role and label in component tests (Testing Library): the Field pattern gives accessible names, so `getByRole("textbox", { name: "Email" })` works and also checks label wiring.
- Assert invalid state through `aria-invalid="true"` and the `FieldError` text, not class names.
- Test dialogs, popovers and selects with a user-event based library; Base UI and Radix portals render outside the container, so query from `document.body`/`screen`.
- Use Playwright for theme and responsive checks: set `colorScheme: "dark"` in the context and assert on `html.dark`.
- Run `npx shadcn@latest build` in CI for registry repos and check the generated JSON exists for every item; install each item into a fixture app in a smoke test.
- Typecheck after `migrate` commands and review the diff; migrations rewrite imports across files.

## 12. Review Checklist

- [ ] `components.json` matches reality: `tailwind.config` empty for Tailwind 4, correct `css` path, `iconLibrary`, aliases resolve in `tsconfig`.
- [ ] One base only (`radix` or `base`); no mixed `asChild` and `render` usage.
- [ ] No `forwardRef` in new components; `className` merged with `cn`; `data-slot` present.
- [ ] Theme tokens defined in both `:root` and `.dark` and exposed in `@theme inline`; colors are OKLCH.
- [ ] New components use semantic tokens, not hard-coded palette colors.
- [ ] Forms: `data-invalid` on `Field`, `aria-invalid` on the control, `FieldError` rendered, server validation present.
- [ ] `<html suppressHydrationWarning>` and `ThemeProvider attribute="class"` set; no theme flash.
- [ ] Registry items reviewed before install; no secrets in registry files.
- [ ] Chart containers have explicit height; chart colors use `var(--chart-N)`.
- [ ] Customized components not overwritten by a blind `add --overwrite`.

## 13. Production Notes

- The CLI and docs move quickly (new bases, presets, commands). Run `npx shadcn@latest --help` and the docs page for the command you are about to use rather than relying on memory.
- `style` and `tailwind.baseColor` are fixed at init in `components.json`; changing them later goes through `apply` (presets) and `migrate base-color`, or a reinstall.
- `apply <preset>` reinstalls detected components and rewrites tokens and fonts; run it on a clean git tree and review the diff. `apply --only theme` limits it to tokens.
- `eject` inlines `shadcn/tailwind.css` into your CSS and drops the `shadcn` dependency; it is irreversible, so later CLI updates to that file will not apply.
- Registry hosting: static JSON on any CDN works; set caching headers sensibly and version item names (or URLs) if consumers must pin.
- When a component library upgrade changes a primitive (Radix or Base UI minor releases), re-run `add <component> --diff` in a branch and test keyboard and focus behavior.
- Treat `components/ui` as application code in code review, ownership and linting rules.

## 14. Examples

Initialize, add components, inspect before installing:

```bash
npx shadcn@latest init -t next --base radix
npx shadcn@latest add button card field input sonner --dry-run
npx shadcn@latest add button card field input sonner
npx shadcn@latest view @acme/pricing-table        # read a registry item before installing
npx shadcn@latest info --json                      # framework, aliases, base, installed components
```

Global CSS wiring for Tailwind 4 with a custom semantic token (excerpt of the structure the docs generate):

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --radius-lg: var(--radius);
  --radius-md: calc(var(--radius) * 0.8);
}

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --success: oklch(0.527 0.154 150);
  --success-foreground: oklch(0.985 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --success: oklch(0.696 0.17 162);
  --success-foreground: oklch(0.145 0 0);
}
```

A variant added to a component you own, with `data-slot` and React 19 props (no `forwardRef`):

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        success: "bg-success text-success-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      data-variant={variant ?? "default"}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
```

## 15. Common Mistakes

- **Wrapping components in `forwardRef` or adding `displayName`**: unnecessary in React 19 and not what the current components do; take `ref` from props.
- **Using `hsl(var(--primary))` or `tailwind.config.js` colors in a Tailwind 4 project**: current tokens are complete OKLCH colors mapped with `@theme inline`; chart code uses `var(--chart-1)`, not `hsl(var(--chart-1))`.
- **Forgetting the `.dark` block or `@custom-variant dark`**: tokens change only if the same names are redefined under `.dark` and the variant matches the class strategy.
- **Mixing `asChild` snippets into a Base UI project** (or `render` into Radix): the prop does not exist on the other base. Read the page for the active base.
- **Rendering Base UI `Button` as an anchor**: use `buttonVariants` on a real link instead.
- **Running `add --overwrite` on customized components**: wipes local changes; use `--diff` and merge.
- **Hand-editing generated tokens in many components** instead of the CSS variables: themes then drift between components.
- **Missing `suppressHydrationWarning` on `<html>`** with next-themes: causes a hydration warning because the class is set before hydration.
- **Chart that renders at zero height**: `ChartContainer` needs `min-h-*`, `h-*` or `aspect-*`.
- **Putting tokens or private components under `public/r` without auth**: the files are public.
- **Copying legacy `Form`/`FormField` examples into new code**: the current forms docs use `Field` with `Controller` or `form.Field`.
- **Changing `style` or `baseColor` by hand in `components.json`**: use `apply` or `migrate base-color`.

## 16. References

- [references/theming.md](references/theming.md): token table, adding tokens, radius scale, OKLCH notes, dark mode with next-themes, base colors, presets, `data-slot` styling.
- [references/registry-and-cli.md](references/registry-and-cli.md): every CLI command with options, `components.json` keys, `migrate` commands, registry authoring, namespaces, authentication, dynamic routes, MCP.
- [references/forms-and-charts.md](references/forms-and-charts.md): Field components with React Hook Form and TanStack Form, sonner, chart component with Recharts 3.
- Official docs: https://ui.shadcn.com/docs , https://ui.shadcn.com/docs/cli , https://ui.shadcn.com/docs/components-json , https://ui.shadcn.com/docs/theming , https://ui.shadcn.com/docs/registry , https://ui.shadcn.com/docs/forms , https://github.com/shadcn-ui/ui
