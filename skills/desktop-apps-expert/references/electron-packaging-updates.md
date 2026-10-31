# Electron Packaging, Updates, Performance and Tests

Packaging Electron 45 apps with Electron Forge 8 or electron-builder 26, signing and notarising on macOS and Windows, auto-update options, startup performance and end-to-end testing with Playwright or WebdriverIO. Versions checked 2026-10: Forge 8.0.1, electron-builder 26.18.0, electron-updater 6.8.11, update-electron-app 3.3.0, @electron/notarize 3.1.2, @electron/packager 20.3.0, @playwright/test 1.64.1, wdio-electron-service 9.2.1.

## Contents

1. [Choosing a packager](#1-choosing-a-packager)
2. [Electron Forge configuration](#2-electron-forge-configuration)
3. [electron-builder configuration](#3-electron-builder-configuration)
4. [macOS signing and notarisation](#4-macos-signing-and-notarisation)
5. [Windows signing](#5-windows-signing)
6. [Auto-update](#6-auto-update)
7. [Performance](#7-performance)
8. [Testing with Playwright](#8-testing-with-playwright)
9. [Release pipeline outline](#9-release-pipeline-outline)

## 1. Choosing a packager

- Electron Forge: the Electron team's all-in-one tool. It wraps `@electron/packager`, adds makers (zip, deb, rpm, Squirrel.Windows, DMG, MSI and others), publishers (GitHub, S3) and plugins (Vite, webpack, fuses). Templates include the fuses plugin.
- electron-builder: declarative configuration (`electron-builder.yml` or the `build` key), many installer targets (NSIS, MSI, AppImage, DMG, pkg, snap, flatpak) and its own updater package `electron-updater`.
- Pick one per repository. Mixing both duplicates signing and update logic.
- Forge 8 ships as ESM packages. Its alpha release notes state a minimum of Node.js 22.12.0 and note that ASAR packaging is on by default in `@electron/packager`; read the stable v8 notes for the final list of breaking changes before upgrading from Forge 7.
- Create a project with the official generator (`npm init electron-app@latest`); check the Forge docs for the current template names (Vite, webpack, TypeScript variants).

## 2. Electron Forge configuration

```ts
// forge.config.ts
import type { ForgeConfig } from '@electron-forge/shared-types';
import { MakerSquirrel } from '@electron-forge/maker-squirrel';
import { MakerZIP } from '@electron-forge/maker-zip';
import { MakerDeb } from '@electron-forge/maker-deb';
import { MakerRpm } from '@electron-forge/maker-rpm';

const config: ForgeConfig = {
  packagerConfig: {
    asar: true,
    appBundleId: 'com.example.notes',
    // macOS signing and notarisation, credentials from the environment
    osxSign: {},
    osxNotarize: {
      appleApiKey: process.env.APPLE_API_KEY_PATH!,
      appleApiKeyId: process.env.APPLE_API_KEY_ID!,
      appleApiIssuer: process.env.APPLE_API_ISSUER!,
    },
  },
  makers: [
    new MakerSquirrel({}),
    new MakerZIP({}, ['darwin']),
    new MakerDeb({}),
    new MakerRpm({}),
  ],
  publishers: [
    {
      name: '@electron-forge/publisher-github',
      config: { repository: { owner: 'example', name: 'notes' }, prerelease: false, draft: true },
    },
  ],
};

export default config;
```

- Maker package names and option names move between major versions; check the Forge docs for each maker you use (https://www.electronforge.io/config/makers).
- Commands: `npm run start` (dev), `npm run package` (unpacked app), `npm run make` (installers), `npm run publish` (make then upload).
- Keep the fuses plugin in `plugins` (see electron-security.md) so fuses are flipped before signing.

## 3. electron-builder configuration

```yaml
# electron-builder.yml
appId: com.example.notes
productName: Notes
directories:
  output: release
files:
  - dist/**
  - package.json
asar: true
mac:
  category: public.app-category.productivity
  hardenedRuntime: true
  entitlements: build/entitlements.mac.plist
  entitlementsInherit: build/entitlements.mac.plist
  notarize: true
win:
  target: nsis
nsis:
  oneClick: false
  perMachine: false
linux:
  target:
    - AppImage
    - deb
publish:
  provider: github
```

- `notarize` options and Windows signing keys (Azure Artifact Signing, certificate files, custom sign hooks) are documented on https://www.electron.build/; check the current names before copying older examples.
- Credentials (`APPLE_API_KEY`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER` or Apple ID variables, `CSC_LINK`, `CSC_KEY_PASSWORD`) are read from the environment in CI. Never commit certificate files.
- electron-builder generates update metadata (`latest.yml`, `latest-mac.yml`) that `electron-updater` reads.
- Electron Fuses are not applied by electron-builder on its own; use `afterPack` with `@electron/fuses` (see the electron-builder docs) before signing happens.

## 4. macOS signing and notarisation

1. Join the Apple Developer Program and create a Developer ID Application certificate; export it to the CI keychain from a secret, or use a runner with the certificate installed.
2. Sign with the hardened runtime and the entitlements the app needs. Electron apps usually need JIT-related entitlements for the V8 engine; Forge and electron-builder defaults include them (check the current templates).
3. Notarise with `notarytool` (through `@electron/notarize`, used by Forge and the packager), authenticating with an App Store Connect API key or an Apple ID plus an app-specific password and team ID.
4. Staple the ticket so the app validates offline.
5. Verify on a clean Mac: `spctl --assess --type execute --verbose MyApp.app` and `codesign --verify --deep --strict --verbose=2 MyApp.app`.

- Signing and notarisation need macOS (or a macOS runner); plan CI accordingly.
- Some APIs require a signed app to work, for example `safeStorage` and encrypted cookies, because they use the Keychain.

## 5. Windows signing

- Azure Artifact Signing (formerly Azure Trusted Signing) is Microsoft's cloud signing service. The Electron docs note it is limited to developers in certain countries; check the eligibility page. Forge, electron-builder and `jsign` have documented integration paths.
- Traditional certificates: EV code-signing certificates must be stored on hardware (FIPS 140 Level 2 or Common Criteria EAL 4+ equivalents) or in a cloud HSM service; plan CI around a signing service or self-hosted runner with the token attached.
- Sign both the app executables and the installer. Squirrel.Windows, NSIS and MSI each have their own signing option.

## 6. Auto-update

| Option | Platforms | Notes |
|---|---|---|
| `autoUpdater` (Squirrel) with static storage | macOS, Windows | Official built-in module. Publish `RELEASES.json` for macOS (Forge ZIP maker `macUpdateManifestBaseUrl`) and the `RELEASES` file for Windows (Squirrel.Windows maker `remoteReleases`) |
| `update-electron-app` | macOS, Windows | Small module that uses update.electronjs.org; the app needs a public GitHub repository and uses GitHub Releases. Call it once after `app.whenReady()` |
| Update server (Hazel and similar) | macOS, Windows | For private repositories or custom hosting |
| `electron-updater` | macOS, Windows, Linux AppImage and some package types | Part of electron-builder; uses `latest*.yml` files and supports differential downloads |

```ts
// src/main/updater.ts (public GitHub repository)
import { updateElectronApp } from 'update-electron-app';
import { app } from 'electron';

export function startUpdates(): void {
  if (!app.isPackaged) return; // never check in development
  updateElectronApp(); // reads repository from package.json
}
```

```ts
// Manual autoUpdater flow
import { autoUpdater, dialog, app } from 'electron';

export function startUpdates(feedUrl: string): void {
  if (!app.isPackaged) return;
  autoUpdater.setFeedURL({ url: feedUrl });
  autoUpdater.on('update-downloaded', async () => {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      buttons: ['Restart', 'Later'],
      message: 'An update is ready to install.',
    });
    if (response === 0) autoUpdater.quitAndInstall();
  });
  autoUpdater.on('error', (err) => console.error('update error', err.message));
  autoUpdater.checkForUpdates();
  setInterval(() => autoUpdater.checkForUpdates(), 6 * 60 * 60 * 1000);
}
```

- Updates require signed builds on macOS and Windows; unsigned apps cannot be updated by Squirrel.Mac.
- Serve feeds and artifacts over HTTPS from a location the release pipeline controls.
- Check on a timer after startup, never block the first window on a network call, and show a restart prompt instead of restarting silently while the user has unsaved work.

## 7. Performance

The Electron performance guide lists these checks, in priority order:

1. Be careful with modules: measure `require` and `import` cost, avoid pulling in large libraries for small features.
2. Load and run code late: lazy-load modules after the first window renders.
3. Do not block the main process: it handles input events, IPC and windows.
4. Do not block the renderer: break up long tasks, use workers.
5. Remove unnecessary polyfills; Chromium is current.
6. Avoid unnecessary or blocking network requests at startup.
7. Bundle the code (esbuild, webpack, Vite) to cut file-system overhead.
8. Call `Menu.setApplicationMenu(null)` when the default menu is not needed (Windows and Linux).

- Show the window on `ready-to-show` with a lightweight first paint; keep a splash only if load exceeds about one second.
- Avoid `ipcRenderer.sendSync` in all cases. For large data use `MessagePort`, a custom protocol, or pass a file path.
- Use `utilityProcess` for heavy tasks and file parsing so the main process stays responsive.
- Compare packaged startup, not dev startup; ASAR, fuses and minification change timing.

## 8. Testing with Playwright

```ts
// tests/e2e/app.spec.ts
import { test, expect, _electron as electron } from '@playwright/test';

test('window opens and API is exposed', async () => {
  const app = await electron.launch({ args: ['.'] });
  const isPackaged = await app.evaluate(({ app }) => app.isPackaged);
  expect(isPackaged).toBe(false);

  const page = await app.firstWindow();
  await expect(page).toHaveTitle(/Notes/);
  const hasNode = await page.evaluate(() => typeof (window as any).require);
  expect(hasNode).toBe('undefined'); // no Node in the renderer
  const bridged = await page.evaluate(() => typeof (window as any).api?.openFile);
  expect(bridged).toBe('function');

  await app.close();
});
```

- Playwright's Electron support goes through the Chrome DevTools Protocol and is marked experimental by both the Electron and Playwright documentation. Pin the Playwright version and re-run after Electron upgrades.
- `electron.launch({ executablePath })` runs a packaged binary; use it for a smoke test of the real artifact (fuses, ASAR, CSP).
- `app.evaluate(fn)` runs in the main process with the `electron` module as the first parameter; use it to stub `dialog.showOpenDialog` or read state.
- Disable the fuses `EnableNodeCliInspectArguments` and similar only in production builds; tests may need a dev build or a test-specific fuse configuration since Playwright attaches through debugging flags (check the Playwright Electron API notes).
- Linux CI needs a display server: run tests under `xvfb-run -a`.
- WebdriverIO with `wdio-electron-service` is an alternative that offers service-level mocking of Electron APIs and handles ChromeDriver version matching. The Electron docs list WebdriverIO and Playwright among supported options; Spectron is no longer maintained.
- Test the security properties: no `require` in the page, IPC from an untrusted origin is rejected, navigation to an outside origin is blocked.

## 9. Release pipeline outline

```yaml
# .github/workflows/release.yml (fragment)
name: release
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run make
        env:
          APPLE_API_KEY_PATH: ${{ runner.temp }}/AuthKey.p8
          APPLE_API_KEY_ID: ${{ secrets.APPLE_API_KEY_ID }}
          APPLE_API_ISSUER: ${{ secrets.APPLE_API_ISSUER }}
      - uses: actions/upload-artifact@v4
        with:
          name: installers-${{ matrix.os }}
          path: out/make/**
```

- Write the Apple key file from a secret in an earlier step into `runner.temp`; do not commit it and do not echo it.
- Upload to a draft release first, run the update test, then publish.
