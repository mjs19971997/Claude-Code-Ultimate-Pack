# Tokens and Theming

How to keep one source of truth for design decisions and ship it to CSS, Tailwind and JavaScript, with themes that switch without flashing. Verified against the DTCG format 2025.10, Style Dictionary 5.7, Tailwind CSS 4.3 and CSS Color Module 4 (2026-10).

## 1. Layering

| Layer | Example name | Holds | Who references it |
|---|---|---|---|
| Primitive | `color.blue.600`, `space.4`, `duration.200` | Raw values | Semantic tokens only |
| Semantic | `color.bg.accent`, `color.text.muted`, `space.inset.md` | Roles, remapped per theme | Components |
| Component | `button.bg`, `dialog.overlay` | Deviations for one component | That component |

Rules:

- Components never reference primitives directly.
- A theme (light, dark, high contrast, brand B) is a different semantic file pointing at the same or other primitives.
- Component tokens default to semantic tokens; add them only when a component truly differs.

## 2. Source format

The Design Tokens Community Group (DTCG) format reached its first stable version (2025.10). It is a community specification, not a W3C standard, and tooling support is still catching up, so check that your exporter and build tool read the same version. Core ideas:

- Each token is an object with `$value` and, usually, `$type` (`color`, `dimension`, `duration`, `cubicBezier`, `fontFamily`, `fontWeight`, `shadow`, `typography` and others) plus optional `$description`.
- Groups nest tokens; `$type` can be set on a group and inherited.
- Aliases reference another token with curly braces: `"{color.blue.600}"`.
- Colour and dimension values use structured objects in the stable spec; copy the exact shape from the spec rather than from older blog posts that use plain strings.

A semantic file is mostly aliases, which keeps it independent of the value format:

```json
{
  "color": {
    "$type": "color",
    "bg": {
      "default": { "$value": "{color.neutral.50}", "$description": "Page background" },
      "accent": { "$value": "{color.blue.600}", "$description": "Primary action fill" }
    },
    "text": {
      "default": { "$value": "{color.neutral.900}" },
      "muted": { "$value": "{color.neutral.600}", "$description": "Secondary text, 14px and up" }
    }
  }
}
```

## 3. Build output

Style Dictionary reads DTCG-style tokens and emits CSS variables, JS/TS modules and other platforms. Build one output per theme so each lands under its own selector:

```js
// style-dictionary.config.mjs
import StyleDictionary from 'style-dictionary';

const themes = [
  { name: 'light', selector: ':root' },
  { name: 'dark', selector: '[data-theme="dark"]' },
];

for (const theme of themes) {
  const sd = new StyleDictionary({
    source: ['tokens/primitives.tokens.json', `tokens/semantic.${theme.name}.tokens.json`],
    platforms: {
      css: {
        transformGroup: 'css',
        buildPath: 'build/css/',
        files: [
          {
            destination: `${theme.name}.css`,
            format: 'css/variables',
            filter: (token) => !token.path.includes('neutral') && !token.path.includes('blue'),
            options: { selector: theme.selector, outputReferences: false },
          },
        ],
      },
    },
  });
  await sd.buildAllPlatforms();
}
```

The filter keeps primitives out of the shipped CSS when only semantic tokens should be public; adjust it to your naming. Check the Style Dictionary docs for the version you install, since option names have changed between major versions.

## 4. Tailwind CSS v4

Tailwind v4 is configured in CSS. Map runtime CSS variables into the theme with `@theme inline` so utilities follow the active theme:

```css
/* src/styles/app.css */
@import "tailwindcss";
@import "../../design-system/build/css/light.css";
@import "../../design-system/build/css/dark.css";

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@theme inline {
  --color-bg: var(--color-bg-default);
  --color-fg: var(--color-text-default);
  --color-muted: var(--color-text-muted);
  --color-accent: var(--color-bg-accent);
}
```

Utilities such as `bg-bg`, `text-fg`, `text-muted` and `bg-accent` now switch with `data-theme` without any `dark:` overrides in components.

## 5. Theme switching without a flash

1. Default to the system preference with `@media (prefers-color-scheme: dark)` remapping the semantic tokens when no explicit choice exists.
2. Store an explicit choice in a cookie and render `data-theme` on `<html>` on the server, so the first paint is already correct.
3. On fully static hosting, a tiny inline script in `<head>` can read the stored choice before first paint. Under a Content Security Policy, allow it with a hash (`'sha256-…'`) or a per-request nonce; never add `'unsafe-inline'`.
4. Set `color-scheme` per theme so form controls and scrollbars match.

## 6. Contrast table

Generate a table from the token build: for each theme, list every text/background and border/background pair that the system allows, its computed WCAG contrast ratio and the required minimum (4.5, 3 or 3). Fail CI when a pair drops below its minimum. Libraries such as `culori` or `colorjs.io` can convert OKLCH to sRGB and compute relative luminance.

## 7. Versioning

- Patch: value tweaks that keep contrast and meaning.
- Minor: new tokens or themes.
- Major: renamed or removed tokens, or meaning changes. Ship aliases for one major version and a codemod or search-and-replace list.
