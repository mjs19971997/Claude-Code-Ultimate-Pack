# Playwright Authentication and Fixtures

Verified against @playwright/test 1.64.1 (2026-10). Companion to [../SKILL.md](../SKILL.md).

## Choosing an authentication strategy

| Situation | Strategy |
|---|---|
| Tests do not change per-account server state | One account, one setup project, shared `storageState` (SKILL.md Example 1) |
| Tests change account state (settings, carts, quotas) | One account per worker, worker-scoped `storageState` fixture |
| Several roles (admin, member) | One setup test per role, one state file per role, `test.use({ storageState })` per describe or per context |
| The login UI is slow or has MFA/captcha | Log in through the API in the setup project and save `request.storageState`; test the UI login in one dedicated spec |
| Logged-out journeys | Separate project without `storageState` (or `test.use({ storageState: { cookies: [], origins: [] } })`) |

Rules for every strategy:
- Credentials come from environment variables or the CI secret store, never from source.
- State files live in a git-ignored folder (`playwright/.auth`). They hold live session cookies.
- Tests log in against the real application. Do not add a test-only endpoint, header or token that creates sessions; if one is unavoidable it must be absent from production builds.
- Delete stale state when it expires (or write it under the project's `outputDir`, which is cleaned before every run).
- UI Mode does not run the `setup` project by default; enable the project in the UI filters or run the setup file manually.

## One account per worker

Pre-created accounts are supplied as a JSON secret. `workerInfo.parallelIndex` is unique among workers running at the same time.

```typescript
import fs from 'node:fs';
import path from 'node:path';
import { test as baseTest, expect } from '@playwright/test';

export * from '@playwright/test';

type Account = { email: string; password: string };

// E2E_ACCOUNTS is a JSON array from the CI secret store, one pre-created account per worker.
function accountFor(index: number): Account {
  const accounts = JSON.parse(process.env.E2E_ACCOUNTS ?? '[]') as Account[];
  const account = accounts[index];
  if (!account) throw new Error(`E2E_ACCOUNTS needs at least ${index + 1} entries`);
  return account;
}

export const test = baseTest.extend<{}, { workerStorageState: string }>({
  // Every test in this worker starts from the worker's saved state.
  storageState: ({ workerStorageState }, use) => use(workerStorageState),

  workerStorageState: [
    async ({ browser }, use, workerInfo) => {
      const id = workerInfo.parallelIndex;
      const file = path.resolve(workerInfo.project.outputDir, `.auth/${id}.json`);

      if (!fs.existsSync(file)) {
        const { email, password } = accountFor(id);
        // Authenticate in a clean context: unset any project-level storage state.
        const page = await browser.newPage({ storageState: undefined });
        await page.goto(`${workerInfo.project.use.baseURL}/login`);
        await page.getByLabel('Email').fill(email);
        await page.getByLabel('Password').fill(password);
        await page.getByRole('button', { name: 'Sign in' }).click();
        await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible();
        fs.mkdirSync(path.dirname(file), { recursive: true });
        await page.context().storageState({ path: file });
        await page.close();
      }
      await use(file);
    },
    { scope: 'worker' },
  ],
});
```

Tests then import `test` from this module instead of `@playwright/test`. Keep at least as many accounts as the maximum worker count (`--workers`, or sharded jobs that run concurrently against the same environment need distinct accounts per job).

## Several roles via API login

Logging in through the API is faster and avoids UI-only obstacles. `request.storageState()` saves the cookies the API response set.

```typescript
import fs from 'node:fs';
import path from 'node:path';
import { test as setup, expect } from '@playwright/test';

const roles = [
  { name: 'admin', emailVar: 'E2E_ADMIN_EMAIL', passwordVar: 'E2E_ADMIN_PASSWORD' },
  { name: 'member', emailVar: 'E2E_MEMBER_EMAIL', passwordVar: 'E2E_MEMBER_PASSWORD' },
] as const;

for (const role of roles) {
  setup(`authenticate ${role.name} via API`, async ({ request }) => {
    const email = process.env[role.emailVar];
    const password = process.env[role.passwordVar];
    if (!email || !password) throw new Error(`Set ${role.emailVar} and ${role.passwordVar}`);

    const res = await request.post('/api/session', { data: { email, password } });
    expect(res.ok()).toBeTruthy();

    const file = `playwright/.auth/${role.name}.json`;
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await request.storageState({ path: file });
  });
}
```

Use the states in specs:

```typescript
import { test, expect } from '@playwright/test';

test.describe('admin area', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' });
  test('admin sees the audit log', async ({ page }) => {
    await page.goto('/admin/audit');
    await expect(page.getByRole('heading', { name: 'Audit log' })).toBeVisible();
  });
});

test('two roles in one test', async ({ browser }) => {
  const adminCtx = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
  const memberCtx = await browser.newContext({ storageState: 'playwright/.auth/member.json' });
  const [admin, member] = [await adminCtx.newPage(), await memberCtx.newPage()];
  await admin.goto('/admin/audit');
  await member.goto('/admin/audit');
  await expect(member.getByText('Forbidden')).toBeVisible();
  await adminCtx.close();
  await memberCtx.close();
});
```

Add each role file to `dependencies: ['setup']` projects only where needed. When a state is set via `use.storageState` at project level, a describe-level `test.use` overrides it.

## sessionStorage

Playwright persists cookies, localStorage and IndexedDB in `storageState`, not sessionStorage. If the app keeps auth data there, save and restore it yourself:

```typescript
import fs from 'node:fs';
import { test as setup } from '@playwright/test';
setup('save sessionStorage', async ({ page }) => {
  const s = await page.evaluate(() => JSON.stringify(sessionStorage));
  fs.writeFileSync('playwright/.auth/session.json', s, 'utf-8');
});
```

Restore it with `context.addInitScript` that writes the saved entries for the matching origin before the app loads. Prefer cookie or localStorage based auth in test environments where you can choose.

## Fixture scopes, options and auto fixtures

```typescript
import { test as base } from '@playwright/test';

export const test = base.extend<
  { consoleErrors: string[]; tenant: string },
  { apiVersion: string }
>({
  // Option fixture: projects override it through `use`.
  tenant: ['acme', { option: true }],

  // Auto fixture: runs for every test, fails the test on uncaught page errors.
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await use(errors);
      if (errors.length) throw new Error(`Uncaught page errors:\n${errors.join('\n')}`);
    },
    { auto: true },
  ],

  // Worker fixture: computed once per worker process.
  apiVersion: [async ({}, use) => { await use('v1'); }, { scope: 'worker' }],
});
```

Notes:
- Code after `await use(value)` is teardown and runs even when the test fails or times out.
- Worker fixtures cannot depend on test-scoped fixtures.
- Built-in option names (`locale`, `timezoneId`, `viewport`, `baseURL`, `storageState` and others) already exist; extending them with the same name and different options fails type checks.
- Merge fixtures from several modules with `mergeTests(a, b)`; merge matchers with `mergeExpects` (both exported from `@playwright/test`).
- Give slow fixtures their own timeout: `[async ({}, use) => {...}, { timeout: 60_000 }]`.
- `{ box: true }` on a fixture hides its steps from reports; `{ title: '...' }` names it in reports.

## Overriding the `request` fixture's behavior

The `request` fixture inherits `baseURL`, `extraHTTPHeaders` and `storageState` from the project's `use` block. To call an API as a different principal, create a context explicitly:

```typescript
import { test, expect, request as pwRequest } from '@playwright/test';

test('member cannot read admin data', async ({ baseURL }) => {
  const member = await pwRequest.newContext({ baseURL, storageState: 'playwright/.auth/member.json' });
  const res = await member.get('/api/admin/users');
  expect(res.status()).toBe(403);
  await member.dispose();
});
```
