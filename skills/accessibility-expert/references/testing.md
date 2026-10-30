# Accessibility Testing

Automated tools catch a subset of WCAG failures (missing names, contrast, invalid ARIA, duplicate IDs). Keyboard behaviour, meaningful alt text, reading order, focus management and announcement quality need manual checks.

## Automated layers

| Layer | Tool | What it catches |
|---|---|---|
| Editor/lint | `eslint-plugin-jsx-a11y` | Missing `alt`, click handlers on non-interactive elements, invalid ARIA props |
| Component | Testing Library role queries; axe-core (`jest-axe` for Jest) | Names, roles, states, rule violations in isolation |
| Page | `@axe-core/playwright` | Rule violations in real layouts, including contrast |
| Site crawl | Pa11y CI or axe-based crawlers | Regressions across many URLs |
| Lab audit | Lighthouse accessibility category | A subset of axe rules; useful as a smoke signal only |

### Component test with Jest

```tsx
// src/components/ui/email-field.a11y.test.tsx
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { EmailField } from './email-field';

expect.extend(toHaveNoViolations);

test('email field is labelled and passes axe', async () => {
  const { container } = render(<EmailField value="" error="Enter an email address" onChange={() => {}} />);
  const input = screen.getByRole('textbox', { name: /email/i });
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(await axe(container)).toHaveNoViolations();
});
```

`toHaveAttribute` requires `@testing-library/jest-dom`. jsdom does not compute layout, so colour-contrast results from component tests are unreliable; check contrast in browser-based tests.

### Scanning states, not only pages

Run axe after each meaningful state change: open menus and dialogs, show validation errors, expand accordions, switch themes. Use `.include('#region')` to limit a scan to the changed area and `.exclude()` only for third-party content you cannot fix (and track it).

### Keyboard flow test

```ts
// tests/a11y/navigation.spec.ts
import { test, expect } from '@playwright/test';

test('skip link moves focus to main content', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: 'Skip to content' });
  await expect(skip).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main')).toBeFocused();
});
```

## Manual test matrix

| Platform | Screen reader | Browser |
|---|---|---|
| Windows | NVDA | Firefox or Chrome |
| Windows | JAWS | Chrome or Edge |
| macOS | VoiceOver | Safari |
| iOS | VoiceOver | Safari |
| Android | TalkBack | Chrome |

Pick at least one desktop and one mobile pairing per release; rotate the others. For each core flow check:

1. Keyboard only: every action reachable, focus visible and logical, no trap, Escape closes popups.
2. Screen reader: headings and landmarks navigable, controls announced with name, role and state, errors and status messages announced once.
3. Zoom 200% and reflow at 320 CSS px wide: no clipped content, no horizontal scrolling for text.
4. Text spacing override (1.4.12) and Windows contrast themes / `forced-colors`.
5. Reduced motion setting on: no large movement or autoplay.
6. Voice control: visible labels can be spoken to activate controls.

## Writing an audit finding

Each finding should state: the URL or component, the WCAG success criterion (number and name), the user impact, steps to reproduce, the current code, the fix, and how to verify the fix. Group findings by blocked user task, not only by criterion, so the most harmful issues are fixed first.

## Conformance reports

A VPAT/ACR (Voluntary Product Accessibility Template / Accessibility Conformance Report) lists each criterion as Supports, Partially Supports, Does Not Support or Not Applicable, with remarks. Base it on a real audit and date it; do not claim "Supports" from automated results alone.
