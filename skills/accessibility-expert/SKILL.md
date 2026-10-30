---
name: accessibility-expert
description: >-
  Builds and audits web interfaces against WCAG 2.2 Level AA with semantic HTML, minimal and correct ARIA, keyboard and focus management, screen reader testing and automated axe-core checks in CI. Use when writing or reviewing HTML/JSX/TSX components, forms, dialogs, menus, tabs, live regions, focus styles, color contrast, reduced motion, or when setting up axe-core, Playwright accessibility tests or an accessibility audit. Not for visual design systems and tokens (use ui-designer), user research and flows (use ux-designer), or page speed (use core-web-vitals-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Accessibility Expert

This skill covers making web interfaces usable by people who rely on keyboards, screen readers, magnification, voice control, switch devices or reduced motion, and proving it with WCAG 2.2 AA checks. It focuses on component code (HTML, React/TSX, CSS) and on the test pipeline. It does not cover visual identity, user research, or native iOS/Android accessibility APIs beyond touch-target and screen-reader notes.

> Verified against WCAG 2.2 (W3C Recommendation, Oct 2023), WAI-ARIA 1.2, the ARIA Authoring Practices Guide, axe-core 4.x with `@axe-core/playwright`, and the WCAG 3 status page (2026-10).

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

- Conformance target: WCAG 2.2 Level A and AA. Legal regimes usually reference a WCAG version through another standard (for example EN 301 549 in the EU, which the European Accessibility Act relies on); check which version the project is bound to.
- WCAG 3 is still a W3C Working Draft (latest seen: March 2026) and is not a conformance target. W3C states that WCAG 2 will not be deprecated for years after WCAG 3 is final. Mention WCAG 3 only as future direction.
- Covered: semantic structure, names/roles/values, keyboard operation, focus management, forms and errors, images and media alternatives, contrast, motion, timing, live updates, automated and manual testing.
- Not covered: brand colour choices and token pipelines (ui-designer), research and IA (ux-designer), PDF remediation tooling in depth.

## 2. Core Expertise

- **POUR principles**: Perceivable, Operable, Understandable, Robust.
- **WCAG 2.2 additions**: 2.4.11 Focus Not Obscured (Minimum, AA), 2.4.12 Focus Not Obscured (Enhanced, AAA), 2.4.13 Focus Appearance (AAA), 2.5.7 Dragging Movements (AA), 2.5.8 Target Size (Minimum, AA: 24 by 24 CSS px or enough spacing), 3.2.6 Consistent Help (A), 3.3.7 Redundant Entry (A), 3.3.8 Accessible Authentication (Minimum, AA), 3.3.9 Accessible Authentication (Enhanced, AAA). 4.1.1 Parsing is obsolete and removed in 2.2.
- **Contrast**: 4.5:1 for normal text, 3:1 for large text (at least 18pt, or 14pt bold, roughly 24px / 18.66px bold), 3:1 for UI component boundaries, states and meaningful graphics (1.4.11).
- **ARIA**: the first rule of ARIA (use a native element when one exists); roles, states and properties; accessible name computation (`aria-labelledby` > `aria-label` > native label > content); "no ARIA is better than bad ARIA".
- **Keyboard**: Tab order follows DOM order; Enter/Space activate; arrow keys move within composite widgets (tabs, menus, listboxes, grids, radio groups); Escape closes popups; roving `tabindex` or `aria-activedescendant` for composites.
- **Focus**: visible `:focus-visible` indicator, not hidden by sticky headers (2.4.11), moved into dialogs on open and back to the trigger on close, moved to new content after client-side route changes.
- **Native platform features**: `<dialog>` with `showModal()` (built-in focus containment, Escape, top layer), the `inert` attribute, `<details>`/`<summary>`, `popover` attribute, form validation attributes.
- **Assistive technology**: NVDA and JAWS on Windows, VoiceOver on macOS and iOS, TalkBack on Android, Narrator, voice control (Voice Control, Dragon), screen magnifiers.
- **Mobile**: WCAG 2.5.8 sets a 24 px floor; platform guidelines recommend larger targets (Apple HIG 44 by 44 pt, Material 48 by 48 dp).

## 3. Workflow

1. Identify the WCAG success criteria the feature touches (forms, media, dynamic content, authentication, drag interactions).
2. Write the semantic HTML outline first: landmarks, one `h1`, ordered headings, lists, buttons vs links.
3. For each interactive element decide the native element; if none exists, pick the matching APG pattern and its keyboard model before writing code.
4. Define names and descriptions: visible label, hint text via `aria-describedby`, error text linked to the field.
5. Define focus behaviour: where focus goes on open, close, submit, error, route change and deletion of the focused item.
6. Define dynamic announcements: which updates need a live region and with which politeness.
7. Implement styles: `:focus-visible`, contrast in every theme, `prefers-reduced-motion`, `forced-colors`, 200% zoom and 320 CSS px reflow.
8. Automate: axe-core in component and end-to-end tests, lint rules (`eslint-plugin-jsx-a11y` for React).
9. Test manually: keyboard only, one desktop screen reader plus one mobile screen reader, zoom/reflow, Windows high-contrast mode.
10. Record known issues and their remediation plan in the accessibility statement or conformance report.

## 4. Decision Rules

- Native element over ARIA widget: `<button>`, `<a href>`, `<input>`, `<select>`, `<dialog>`, `<details>` bring keyboard, focus and semantics for free.
- `<button>` for actions, `<a href>` for navigation. A link styled as a button is still a link.
- Visible text is the accessible name. Use `aria-label` only when there is no visible text (icon-only buttons), and make sure it contains the visible label when both exist (2.5.3 Label in Name).
- `aria-live="polite"` (or `role="status"`) for routine updates; `role="alert"` only for urgent, time-sensitive messages.
- `alt=""` for decorative images; meaningful `alt` for informative images; for functional images (image links), the `alt` describes the destination or action.
- `tabindex` values: `0` to add a custom widget to the tab order, `-1` for programmatic focus targets. Never positive values.
- Modal UI: prefer native `<dialog>` with `showModal()` or a maintained library (Radix UI, React Aria) over a hand-written focus trap.
- Drag and drop: always provide a single-pointer alternative such as buttons or a menu (2.5.7).
- Authentication: allow paste and password managers, offer an alternative to cognitive tests such as puzzles (3.3.8).
- Automated tools find only a part of real issues. A clean axe run or a Lighthouse score of 100 is a floor, not a conformance claim.

## 5. Coding Standards

- `<html lang="…">` set; `lang` on inline passages in another language.
- One `<main>`; `header`, `nav`, `footer`, `aside` where they apply; multiple `nav` or `aside` elements get distinct `aria-label`s.
- Every form control has a programmatic label (`<label for>` or wrapping label); groups use `<fieldset>` and `<legend>`.
- Inputs use the right `type` and an `autocomplete` token for personal data (`email`, `name`, `tel`, `current-password`, `new-password`, `one-time-code`).
- Errors: set `aria-invalid="true"`, link the message with `aria-describedby`, describe how to fix it, keep the user's input.
- Required fields: native `required` (or `aria-required`) plus a visible indicator that is not colour alone.
- Icons: decorative SVGs get `aria-hidden="true"` and `focusable="false"`; standalone meaningful SVGs get `role="img"` and an accessible name.
- `<iframe>` has a `title` describing its content.
- Never remove focus outlines without a replacement of at least 3:1 contrast against adjacent colours.
- Do not convey information by colour, shape, position or sound alone.
- IDs used by `aria-labelledby`/`aria-describedby` must be unique per page; in React use `useId()`.
- Avoid `aria-hidden="true"` on focusable elements or their ancestors.

## 6. Project Structure

```
src/
├── components/
│   ├── ui/                    # accessible primitives (button, dialog, tabs, field)
│   ├── skip-link.tsx
│   └── live-region.tsx        # single polite region for app-wide announcements
├── hooks/
│   └── use-announce.ts
├── styles/
│   └── base.css               # :focus-visible, .visually-hidden, reduced motion, forced-colors
tests/
├── a11y/                      # Playwright + @axe-core/playwright page scans
└── components/                # component tests with axe and keyboard assertions
docs/
└── accessibility-statement.md
eslint.config.js               # includes eslint-plugin-jsx-a11y
```

## 7. Design Patterns

- **Skip link**: first focusable element, visible on focus, targets `<main id="main">` (add `tabindex="-1"` on the target if focus does not move in some browsers).
- **Dialog**: native `<dialog>` opened with `showModal()`, labelled by its heading, Escape closes, focus returns to the trigger.
- **Disclosure**: `<button aria-expanded aria-controls>` toggling a region, or `<details>`/`<summary>`.
- **Tabs**: `tablist` / `tab` / `tabpanel`, roving `tabindex`, arrow keys move between tabs, Home/End jump. See [references/widget-patterns.md](references/widget-patterns.md).
- **Live region**: mount the region empty on page load, then change its text; regions inserted together with their content are often not announced.
- **Route change announcement (SPA)**: after navigation, move focus to the new `h1` (with `tabindex="-1"`) or announce the page title in a polite live region.
- **Error summary**: on submit with errors, render a list of links to invalid fields at the top of the form and move focus to it.
- **Reduced motion**: design motion as an enhancement; under `prefers-reduced-motion: reduce` remove parallax, autoplay and large movement, and keep opacity fades short.

## 8. Best Practices

- Write accessibility acceptance criteria into tickets ("operable by keyboard; announced as …").
- Build a small set of tested primitives and reuse them instead of re-implementing widgets per feature.
- Prefer maintained headless libraries (React Aria, Radix UI, Headless UI) for complex widgets such as combobox, date picker and tree.
- Check every theme (light, dark, high contrast) and every state (hover, focus, disabled, error) for contrast.
- Support 400% zoom / 320 CSS px reflow without two-dimensional scrolling (1.4.10) and text spacing overrides (1.4.12).
- Respect `forced-colors: active`: avoid conveying state only with background colour or box-shadow; use borders or `outline`, which survive forced colours.
- Provide captions for prerecorded video, transcripts for audio, and pause/stop/hide controls for anything that moves for more than 5 seconds (2.2.2).
- Keep link text meaningful out of context; avoid repeated "Read more" without an accessible name that includes the target.

## 9. Performance

- Large DOMs slow down screen readers as well as rendering; virtualise very long lists, but keep `aria-setsize`/`aria-posinset` correct and make sure find-in-page and keyboard paging still work.
- Use `aria-busy="true"` on a region while it is being replaced, then remove it.
- Throttle live region updates (for example, announce "12 results" once after typing stops, not on every keystroke).
- Skeleton loaders should be `aria-hidden="true"` with a separate polite "Loading" status.

## 10. Security

- Accessible names and live regions render text; never inject untrusted HTML into them. Use text content, not `innerHTML`.
- Do not put secrets or personal data into `aria-label`, `title` or hidden text; screen readers and accessibility APIs expose it.
- Mask passwords but offer a "show password" toggle; allow paste and password managers (3.3.8).
- CAPTCHAs need an accessible alternative; prefer non-interactive bot detection.
- Session timeouts: warn before expiry and allow extension (2.2.1) without losing entered data.

## 11. Testing

- **Lint**: `eslint-plugin-jsx-a11y` for JSX; fix, do not disable, its rules.
- **Component tests**: Testing Library queries by role and name (`getByRole('button', { name: 'Save' })`) double as accessibility assertions; add axe checks (`jest-axe` with Jest, or run axe-core directly in Vitest browser mode).
- **End-to-end**: `@axe-core/playwright` per page and per important state (open dialog, error state), filtered to WCAG A/AA tags.
- **Keyboard tests**: script Tab/Shift+Tab/arrow/Escape flows in Playwright and assert focus with `toBeFocused()`.
- **Manual**: keyboard-only pass of every flow; screen reader pass with at least one desktop pairing (NVDA + Firefox or Chrome, or VoiceOver + Safari) and one mobile pairing (VoiceOver iOS or TalkBack); zoom 200%/400%; Windows contrast themes.
- **People**: usability sessions with disabled participants catch what tools and experts miss.

Details and a testing matrix: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Native elements used; no `div`/`span` with click handlers acting as buttons or links.
- [ ] Every control has an accessible name; visible label text is part of it.
- [ ] Headings ordered; landmarks present; page `<title>` unique and descriptive.
- [ ] All functionality operable by keyboard; no keyboard traps outside modal dialogs.
- [ ] Focus visible, not obscured by sticky UI, and managed on open/close/route change.
- [ ] Contrast meets 4.5:1 / 3:1 in all themes and states.
- [ ] Images have correct `alt`; decorative icons hidden from AT.
- [ ] Form errors identified in text, linked to fields, with suggestions; input preserved.
- [ ] Target size at least 24 by 24 CSS px or adequately spaced.
- [ ] Dragging has a single-pointer alternative.
- [ ] Motion respects `prefers-reduced-motion`; nothing flashes more than three times per second.
- [ ] Dynamic updates announced through a pre-existing live region.
- [ ] No positive `tabindex`; no `aria-hidden` on focusable content.
- [ ] axe-core run clean for the changed pages and states; manual keyboard pass done.
- [ ] Refactors kept behaviour: same names, roles, keyboard model and focus order as before.

## 13. Production Notes

- Publish an accessibility statement with contact details, known limitations and the date of the last audit; a VPAT/ACR (based on the ITI template) is often required in procurement.
- Route accessibility bug reports to the same triage as functional bugs, with severity based on blocked tasks rather than criterion count.
- Re-audit after design system upgrades and third-party widget updates (chat widgets, consent banners and embedded players are common regressions).

## 14. Examples

### Native modal dialog in React

```tsx
// src/components/ui/confirm-dialog.tsx
import { useEffect, useId, useRef, type ReactNode } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function ConfirmDialog({ open, title, onClose, children }: ConfirmDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal(); // top layer, inert background, Escape support
    if (!open && dialog.open) dialog.close();     // browser restores focus to the opener
  }, [open]);

  return (
    <dialog ref={ref} aria-labelledby={titleId} onClose={onClose}>
      <h2 id={titleId}>{title}</h2>
      {children}
      <button type="button" onClick={onClose}>
        Close
      </button>
    </dialog>
  );
}
```

### Field with hint and error

```tsx
// src/components/ui/email-field.tsx
import { useId } from 'react';

interface EmailFieldProps {
  value: string;
  error?: string;
  onChange: (value: string) => void;
}

export function EmailField({ value, error, onChange }: EmailFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;

  return (
    <div>
      <label htmlFor={id}>
        Email <span aria-hidden="true">*</span>
        <span className="visually-hidden">(required)</span>
      </label>
      <p id={hintId}>We use this to send your receipt.</p>
      <input
        id={id}
        type="email"
        autoComplete="email"
        required
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${hintId} ${errorId}` : hintId}
        onChange={(e) => onChange(e.target.value)}
      />
      {error && <p id={errorId}>Error: {error}</p>}
    </div>
  );
}
```

On submit, render an error summary and move focus to it; the inline error is then read when the user reaches the field, so it does not need `role="alert"`.

### Page scan with axe in Playwright

```ts
// tests/a11y/checkout.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('checkout has no detectable WCAG A/AA violations', async ({ page }) => {
  await page.goto('/checkout');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});

test('payment dialog traps and returns focus', async ({ page }) => {
  await page.goto('/checkout');
  const trigger = page.getByRole('button', { name: 'Change payment method' });
  await trigger.click();
  await expect(page.getByRole('dialog', { name: 'Payment method' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
});
```

## 15. Common Mistakes

- **Clickable `div`**: not focusable, no role, no Enter/Space. Use `<button type="button">`.
- **`aria-label` that contradicts visible text**: `<button aria-label="Submit form">Save</button>` breaks voice control ("click Save"). Remove the `aria-label` or include the visible words.
- **Missing or filename `alt`**: screen readers read the file name. Write purpose-based `alt` or `alt=""` for decoration.
- **Positive `tabindex`**: creates an order that no longer matches the page. Fix DOM order instead.
- **Hand-rolled modal without focus handling**: focus escapes behind the overlay and is lost on close. Use `<dialog>` with `showModal()` or a maintained library.
- **Live region injected with its message**: often not announced. Keep the region mounted and change its text.
- **`role="alert"` on every inline error**: floods the user with interruptions while typing. Use an error summary on submit and `aria-describedby` on fields.
- **Placeholder used as label**: disappears on input and usually fails contrast. Use a visible `<label>`.
- **Colour-only status**: a red border alone fails 1.4.1. Add text and an icon.
- **Autoplaying carousels and parallax with no pause or reduced-motion path**: add pause controls and honour `prefers-reduced-motion`.
- **`outline: none` without replacement**: keyboard users lose their place.
- **Treating a Lighthouse 100 as compliance**: automated rules cover only part of WCAG; manual testing is still required.
- **Disabling paste in password or OTP fields**: fails 3.3.8 and blocks password managers.

## 16. References

- [references/widget-patterns.md](references/widget-patterns.md): keyboard models and code for tabs, menu button, disclosure, combobox and live announcements.
- [references/testing.md](references/testing.md): automated tooling setup, manual screen reader matrix, and how to write an audit finding.
