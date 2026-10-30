# Playwright Visual, Aria, Network, Clock and API Testing

Verified against @playwright/test 1.64.1 and the Playwright docs for visual comparisons, aria snapshots, mocking, clock and API testing (2026-10). Companion to [../SKILL.md](../SKILL.md).

## Screenshot comparisons (`toHaveScreenshot`)

- First run writes the baseline and fails (`default` update mode); later runs compare against it. Baselines are stored per test file in `<file>-snapshots/`, named with project and platform (for example `-chromium-linux`), because rendering differs per OS, browser and fonts.
- Generate and review baselines in the same environment CI uses (the Playwright Docker image); update with `npx playwright test --update-snapshots`.
- Store as WebP by naming the snapshot `x.webp` (1.62+) or setting `expect.toHaveScreenshot.type: 'webp'` (1.64+).
- Options verified in the type definitions: `animations: 'disabled'`, `caret: 'hide'`, `mask: Locator[]`, `fullPage`, `clip`, `omitBackground`, `scale`, `stylePath`, `threshold` (0 strict to 1 lax, default 0.2), `maxDiffPixels`, `maxDiffPixelRatio`, `timeout`. Share defaults under `expect: { toHaveScreenshot: { ... } }` in the config.
- Move the mouse away (`page.mouse.move(-1, -1)`) before capturing to avoid hover effects.
- Prefer element screenshots of stable components over full pages, mask timestamps and ads, and freeze time with `page.clock`.
- `snapshotPathTemplate` in the config customizes where baselines live.

## Aria snapshots (`toMatchAriaSnapshot`)

Asserts the accessibility tree as YAML. It survives CSS and markup refactors and checks roles and names, so it doubles as an accessibility signal.

- Works on a locator and on a page (page form since 1.60; equivalent to `page.locator('body')`).
- Partial templates match by default (`/children: contain`). Use `- /children: equal` or `deep-equal` for exact children, or set `expect.toMatchAriaSnapshot.children` globally in the config.
- Regular expressions work for names and text: `- heading /Issues \d+/ [level=1]`.
- Store a template in its own file with `toMatchAriaSnapshot({ name: 'main.aria.yml' })`; files go to `<test file>-snapshots/` and one file is shared by all browsers. `expect.toMatchAriaSnapshot.pathTemplate` customizes the location.
- `npx playwright test --update-snapshots` updates inline templates. `--update-source-method` selects how: `patch` (default, writes a diff to apply with `git apply`), `3way` (conflict markers) or `overwrite`. Review the result before committing.
- `page.ariaSnapshot()` and `locator.ariaSnapshot()` produce the YAML for you to paste or inspect.

## Network mocking

Real examples, type-checked against 1.64:

```typescript
import { test, expect } from '@playwright/test';

test('visual options', async ({ page }) => {
  await page.goto('/pricing');
  await expect(page).toHaveScreenshot('pricing.png', {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    mask: [page.getByTestId('live-chat'), page.locator('time')],
    maxDiffPixelRatio: 0.01,
  });
  await expect(page.getByRole('main')).toMatchAriaSnapshot(`
    - heading "Pricing" [level=1]
    - list:
      - /children: equal
      - listitem: Free
      - listitem: Team
  `);
});

test('mock and modify a response', async ({ page }) => {
  await page.route('**/api/products*', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.items = body.items.slice(0, 1);
    await route.fulfill({ response, json: body });
  });
  await page.route('**/*.{png,jpg,jpeg}', (route) => route.abort());
  const reqPromise = page.waitForRequest((r) => r.url().includes('/api/cart') && r.method() === 'POST');
  await page.goto('/products');
  await page.getByRole('button', { name: 'Add to cart' }).click();
  const req = await reqPromise;
  expect(req.postDataJSON()).toMatchObject({ qty: 1 });
});

test('HAR replay', async ({ page }) => {
  await page.routeFromHAR('tests/hars/products.har', { url: '**/api/products*', notFound: 'abort' });
  await page.goto('/products');
});

test('timers with the clock', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-03-01T08:00:00') });
  await page.goto('/dashboard');
  await page.clock.pauseAt(new Date('2026-03-01T10:00:00'));
  await page.clock.fastForward('30:00');
  await expect(page.getByText('10:30')).toBeVisible();
  await page.clock.runFor(2000);
});

test.describe('api', () => {
  test.use({ extraHTTPHeaders: { Accept: 'application/json' } });
  test('create and read back', async ({ request }) => {
    const created = await request.post('/api/notes', { data: { title: 't' } });
    expect(created.status()).toBe(201);
    const { id } = (await created.json()) as { id: string };
    const res = await request.get(`/api/notes/${id}`);
    await expect(res).toBeOK();
    expect(await res.json()).toMatchObject({ title: 't' });
  });
});
```

Notes:
- Register routes before the navigation or action that triggers the request. Routes on `context` apply to every page in it; routes on `page` take precedence.
- Handlers must fulfill, continue, fallback or abort every request they intercept, otherwise the request hangs.
- `route.fetch()` plus `route.fulfill({ response, json })` modifies a real response while keeping status and headers.
- `routeFromHAR(path, { update: true })` records a HAR; later runs replay it. HAR files can contain cookies and tokens: scrub them before committing.
- Prefer `page.waitForResponse` / `waitForRequest` created before the triggering click, then awaited afterwards, over fixed waits.
- WebSocket traffic: `page.routeWebSocket` exists for mocking sockets; check the current docs for its API before use.

## Clock

- `setFixedTime` fixes `Date.now()` and `new Date()` but lets timers run; this is the default choice for "what does the UI show on date X".
- `install` takes over `Date` and timers; call it before any other clock call and before the page code starts timers. Then `pauseAt`, `fastForward('30:00')` (jumps, firing due timers once) and `runFor(ms)` (ticks through timers) control time.
- Clock control applies to the page, not to the server; server-side expiry needs server-side test hooks in a non-production environment.

## API testing with the `request` fixture

`request` honours `baseURL`, `extraHTTPHeaders`, `proxy` and `storageState` from the project config. `await expect(response).toBeOK()` checks a 2xx status and prints the body on failure. Use `playwright.request.newContext()` for a different principal or base URL and `dispose()` it afterwards (see the auth reference).

Good uses: seed and clean up data for UI tests, assert server post-conditions after a UI action, contract smoke tests of an API deployed with the UI. For API-only suites, `projects` without a browser dependency still work with the `request` fixture. For deep service tests with databases and message brokers prefer integration-testing-expert.

```typescript
// playwright.config.ts excerpt: token for API calls comes from the environment
use: {
  baseURL: process.env.API_URL,
  extraHTTPHeaders: { Authorization: `Bearer ${process.env.API_TOKEN}` },
},
```

Keep tokens out of the repository and out of traces shared publicly; API headers set via `extraHTTPHeaders` appear in trace network logs.

## Playwright MCP and test agents

- `@playwright/mcp` is the Model Context Protocol server for browser control (accessibility-tree based, no screenshots required); Playwright 1.62 bundles it as `npx playwright mcp`, and `playwright-cli` as `npx playwright cli`.
- Since 1.64, pages that register tools through the experimental WebMCP browser API are visible via `page.webmcp.tools()` and `page.webmcp.callTool(name, args)`, and Playwright MCP offers them as `webmcp_<tool>`; Chromium needs the `--enable-features=WebMCP` launch argument for the raw API.
- Test agents (1.56+): planner writes a Markdown plan into `specs/` from a seed test (`tests/seed.spec.ts`), generator turns the plan into spec files and verifies selectors live, healer replays failures and patches locators or waits. Generate definitions with `npx playwright init-agents --loop=claude`, and regenerate after upgrades.
- Use agents to draft and repair tests, then apply the same review rules as for handwritten tests; do not let a healer weaken assertions to get green.

## Accessibility checks with axe

```typescript
import AxeBuilder from '@axe-core/playwright';
import { test, expect } from '@playwright/test';

test('home has no detectable a11y violations', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(results.violations).toEqual([]);
});
```

Automated checks find a subset of issues; pair them with role-based locators and manual keyboard testing (accessibility-expert). `@axe-core/playwright` 4.14.0 was the current release at verification time.
