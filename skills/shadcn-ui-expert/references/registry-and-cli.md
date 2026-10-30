# CLI, components.json and Registries

Reference for the `shadcn` CLI, the `components.json` file and authoring or consuming component registries. Verified against shadcn CLI 4.23.0 (npm package `shadcn`, Node >= 20.18.1) and the shadcn/ui docs source on GitHub (2026-10). Command output and flags change between releases; run `npx shadcn@latest <command> --help` for the authoritative list.

## 1. Commands

| Command | Purpose | Notable options |
|---|---|---|
| `init [components...]` | Initialize an existing project, or scaffold one with `--name`; installs dependencies, adds `cn`, configures CSS variables. `create` is an alias | `-t, --template` (`next`, `vite`, `start`, `react-router`, `laravel`, `astro`), `-b, --base` (`base`, `radix`, `aria`), `-p, --preset`, `-d, --defaults` (template `next`, preset `nova`), `-f, --force`, `-c, --cwd`, `--css-variables` / `--no-css-variables`, `--monorepo`, `--rtl`, `--pointer`, `--reinstall` |
| `add [components...]` | Add components, by name, URL, local path or `@namespace/item` | `-y`, `-o, --overwrite`, `-a, --all`, `-p, --path`, `--dry-run`, `--diff [path]`, `--view [path]`, `-c, --cwd` |
| `apply [preset]` | Apply a preset to an existing project (rewrites theme and fonts, reinstalls detected components) | `--only theme\|font`, `--preset`, `-y` |
| `preset decode <code>` | Show what a preset code contains | `--json` |
| `preset resolve` / `preset info` | Resolve the preset of the current project | `--json` |
| `preset url <code>` / `preset open <code>` | Print or open the shadcn/create URL for a preset | |
| `view <items...>` | Print registry items before installing | |
| `search <registries...>` (alias `list`) | Search registries; names are prefixed with `@` | `-q, --query`, `-l, --limit`, `-o, --offset` |
| `build [registry]` | Generate registry JSON from `registry.json` | `-o, --output` (default `./public/r`) |
| `docs [component]` | Fetch docs and API reference for a component | `-b, --base`, `--json` |
| `info` | Project information: framework, Tailwind version, aliases, base, icon library, components | `--json` |
| `migrate [migration] [path]` | Run a migration (section 3) | `-l, --list`, `-f, --from`, `-t, --to`, `-y` |
| `eject` | Inline `shadcn/tailwind.css` and remove the `shadcn` dependency (irreversible) | `-y`, `-c` |
| `mcp init --client <client>` | Configure the shadcn MCP server for an AI client (`claude`, `cursor`, `vscode`, `codex`, `opencode`) | |

Typical flows:

```bash
npx shadcn@latest init -t next --base radix
npx shadcn@latest add dialog --diff                   # compare before overwriting
npx shadcn@latest add dialog --overwrite             # only after reviewing the diff
npx shadcn@latest apply a2r6bw --only theme          # preset code from shadcn/create
npx shadcn@latest search @shadcn -q "button"
```

## 2. components.json

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "radix-nova",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

| Key | Notes |
|---|---|
| `style` | Fixed at init. Current docs show IDs such as `base-nova`; the `default` style is deprecated, `new-york` remains the older name |
| `rsc` | When `true` the CLI adds `"use client"` to client components |
| `tsx` | `false` generates `.jsx` files |
| `tailwind.config` | Path to `tailwind.config.*` for Tailwind 3; leave `""` for Tailwind 4 |
| `tailwind.css` | The CSS file that imports Tailwind and holds tokens |
| `tailwind.baseColor` | `neutral`, `stone`, `zinc`, `mauve`, `olive`, `mist`, `taupe`; change with `migrate base-color` |
| `tailwind.cssVariables` | Fixed at init; `false` emits palette utilities instead of tokens |
| `tailwind.prefix` | Prefix for generated Tailwind classes |
| `aliases.*` | Import roots for `components`, `ui`, `lib`, `hooks`, `utils`. Back them with `tsconfig` `paths`, or with `package.json#imports` (needs `moduleResolution: "bundler"` and `resolvePackageJsonImports: true`) |
| `iconLibrary` | `lucide`, `tabler`, `hugeicons`, `phosphor`, `remixicon`; legacy `radix` |
| `registries` | Namespaced registries (section 5) |
| `rtl` | Enables RTL output (`init --rtl` or `migrate rtl`) |

`components.json` is only required to use the CLI; copy-and-paste installs do not need it.

## 3. Migrations

| Command | Effect |
|---|---|
| `migrate radix` | Rewrites `@radix-ui/react-*` imports to the unified `radix-ui` package; afterwards remove unused `@radix-ui/react-*` packages |
| `migrate cn` | Replaces `clsx` plus `tailwind-merge` (and `cnfast`) with the `cn` package; works without `components.json`; Tailwind 4 only for the merge engine, Tailwind 3 projects keep `tailwind-merge` v2 |
| `migrate icons --from lucide --to phosphor --yes` | Rewrites icon imports in the `ui` directory and updates `iconLibrary` (scoped runs do not update `components.json`) |
| `migrate base-color --to zinc --yes` | Rewrites theme variables for another base color |
| `migrate rtl` | Converts physical properties to logical ones (`ml-4` to `ms-4`, `text-left` to `text-start`) and sets `rtl: true` |

Run migrations on a clean git tree, review the diff, then typecheck. Items without an equivalent are reported, not silently changed.

## 4. Registry authoring

A registry is any HTTP location that serves JSON conforming to the schemas, or a public GitHub repository with a `registry.json` at its root.

`registry.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema/registry.json",
  "name": "acme",
  "homepage": "https://acme.example",
  "items": [
    {
      "name": "pricing-table",
      "type": "registry:block",
      "title": "Pricing table",
      "description": "Three-tier pricing section.",
      "registryDependencies": ["button", "card"],
      "dependencies": ["lucide-react"],
      "files": [
        { "path": "registry/pricing-table/pricing-table.tsx", "type": "registry:component" }
      ],
      "cssVars": {
        "light": { "brand": "oklch(0.55 0.2 260)" },
        "dark": { "brand": "oklch(0.7 0.15 260)" }
      }
    }
  ]
}
```

- Item `type` values: `registry:base`, `registry:block`, `registry:component`, `registry:font`, `registry:lib`, `registry:hook`, `registry:ui`, `registry:page`, `registry:file`, `registry:style`, `registry:theme`, `registry:item`.
- Each file needs `path` and `type`. `target` is required for `registry:page` and `registry:file` items because the CLI cannot infer their destination.
- `registryDependencies` accepts names (`button`), namespaced items (`@acme/input-form`) and URLs. `dependencies` and `devDependencies` are npm packages, optionally with versions (`is-even@3.0.0`).
- `cssVars` has `theme`, `light` and `dark` maps; `css` adds rules such as `@layer base`, `@utility` and `@plugin`; `envVars`, `font`, `docs`, `categories` and `meta` are also supported. The old `tailwind.config` property is deprecated for Tailwind 4; use `cssVars.theme`.
- Large registries split definitions across files with `include`: the root lists `"include": ["components/ui/registry.json", "hooks/registry.json"]`, and file paths inside an included file are relative to that file. `shadcn build` flattens the result (the generated `registry.json` has no `include`).
- Start from the official registry template repository (shadcn-ui/registry-template) when creating a new registry app.

Build and serve:

```bash
npx shadcn@latest build                 # writes public/r/<name>.json
npx shadcn@latest build --output ./public/registry
```

Dynamic alternative (Next.js route handlers) using the loaders in `shadcn/registry`, with `shadcn` installed as a runtime dependency:

```ts
// app/r/[name].json/route.ts
import { loadRegistryItem, RegistryItemNotFoundError } from "shadcn/registry"

export async function GET(
  _request: Request,
  context: { params: Promise<{ name: string }> }
) {
  const { name } = await context.params
  try {
    return Response.json(await loadRegistryItem(name))
  } catch (error) {
    if (error instanceof RegistryItemNotFoundError) {
      return Response.json({ error: "Registry item not found." }, { status: 404 })
    }
    console.error(error)
    return Response.json({ error: "Failed to load registry item." }, { status: 500 })
  }
}
```

The docs also describe HTTP content negotiation so one URL can serve both a human page and registry JSON; check the registry docs before relying on it.

## 5. Consuming registries

```json
{
  "registries": {
    "@acme": "https://registry.acme.example/r/{name}.json",
    "@private": {
      "url": "https://api.acme.example/registry/{name}.json",
      "headers": { "Authorization": "Bearer ${REGISTRY_TOKEN}" }
    }
  }
}
```

- `{name}` is replaced with the item name. `${VAR}` placeholders in `headers` and `params` expand from the environment, so tokens stay in `.env.local` or CI secrets, not in `components.json`.
- Install with `npx shadcn@latest add @acme/pricing-table`; inspect first with `view @acme/pricing-table` or `add ... --dry-run`.
- `search @acme -q pricing` browses a namespace.

## 6. Authentication for your own registry

- Bearer token or API key in a header is the common pattern; query-string tokens (`params`) work but appear in access logs and proxies.
- On the server, compare the presented token with a constant-time check, return 401 without echoing details, and scope tokens per team or customer when items differ by audience.
- Never place private items in `public/r`; serve them from a route that checks credentials.
- Rotate tokens through CI secrets; do not commit them in `components.json`, `.env` files or registry items.

## 7. MCP server

`npx shadcn@latest mcp init --client claude` writes the MCP configuration so an assistant can browse, search and add components from the registries configured in `components.json`. Restart the client afterwards; in Claude Code, `/mcp` helps with debugging. As with any registry install, review what is added.
