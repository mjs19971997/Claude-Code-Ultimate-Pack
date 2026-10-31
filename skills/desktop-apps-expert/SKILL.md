---
name: desktop-apps-expert
description: >-
  Builds, hardens, packages and tests cross-platform desktop apps with Electron 45 and Tauri 2: process model, IPC, preload and contextBridge, Electron Fuses, Tauri commands, capabilities and permissions, CSP, signing, notarisation and auto-update. Use when editing main.js, preload.js, forge.config.js, electron-builder.yml, tauri.conf.json, src-tauri/capabilities or Cargo.toml for Tauri, or choosing between Electron and Tauri. Not for web UI frameworks (use senior-react-19-engineer, svelte-expert or angular-expert), Rust language details (use rust-expert), Node runtime internals (use nodejs-architect), or native mobile apps (use swift-expert or android-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Desktop Apps Expert

This skill covers desktop applications built on web technology: Electron (Chromium plus Node.js) and Tauri 2 (Rust core plus the operating system webview). It addresses architecture, the security boundary between UI and privileged code, packaging, code signing, auto-update and testing. The web UI itself, Rust language questions, Node internals and native mobile development belong to other skills.

> Verified against Electron 45.2.1, @electron/fuses 2.1.3, Electron Forge 8.0.1, electron-builder 26.18.0, electron-updater 6.8.11, update-electron-app 3.3.0, @playwright/test 1.64.1, Tauri 2.12.5 (crate; @tauri-apps/cli and @tauri-apps/api 2.12.4), tauri-build 2.7.4, tauri-plugin-updater 2.14.1, tauri-plugin-fs 2.7.1, tauri-plugin-shell 2.6.0 and tauri-driver 2.1.0 (2026-10).

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

- Covered: Electron main, renderer, preload and utility processes; `contextIsolation`, sandbox, `contextBridge`, `ipcMain.handle` and `ipcRenderer.invoke`; IPC sender validation; CSP; navigation and window-open handlers; `shell.openExternal` allow-lists; Electron Fuses; Electron Forge and electron-builder; macOS and Windows signing; `autoUpdater`, `update-electron-app` and electron-updater; Tauri commands, events and channels; Tauri capabilities, permissions and scopes; Tauri plugins (fs, shell, dialog, store, updater, process); sidecars; Tauri bundling and signing; mobile targets in outline; Playwright, WebdriverIO and tauri-driver tests; choosing between Electron and Tauri.
- Not covered: React, Svelte, Angular or Vue component design (senior-react-19-engineer, svelte-expert, angular-expert); Rust ownership, async and crates beyond what Tauri code needs (rust-expert); Node event loop, streams and worker internals (nodejs-architect); Swift or Kotlin native apps (swift-expert, android-expert); general end-to-end test strategy (e2e-testing-expert); pipeline design for build matrices (cicd-expert); generic secret handling and threat modelling (secure-coding-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Electron process model | One main process (Node.js, full OS access), one renderer per window or view (Chromium), preload scripts that run before page code, and utility processes (`utilityProcess`) for untrusted or heavy Node work. Renderers are sandboxed by default since Electron 20; `nodeIntegration: true` disables the sandbox for that process |
| Context isolation | On by default. The preload runs in an isolated world and shares only what `contextBridge.exposeInMainWorld` exposes. Expose narrow functions, never `ipcRenderer` or `ipcRenderer.send` themselves |
| IPC | `ipcMain.handle(channel, handler)` with `ipcRenderer.invoke(channel, ...args)` for request and response; `webContents.send` with `ipcRenderer.on` for main-to-renderer pushes. Every handler must validate its arguments and `event.senderFrame` |
| Electron Fuses | Package-time binary toggles flipped before code signing (`@electron/fuses`, or `@electron-forge/plugin-fuses`). Names: `RunAsNode`, `EnableCookieEncryption`, `EnableNodeOptionsEnvironmentVariable`, `EnableNodeCliInspectArguments`, `EnableEmbeddedAsarIntegrityValidation`, `OnlyLoadAppFromAsar`, `LoadBrowserProcessSpecificV8Snapshot`, `GrantFileProtocolExtraPrivileges`, `WasmTrapHandlers`. Inspect with `npx @electron/fuses read --app <path>` |
| Electron ESM | The main process supports ES modules since Electron 28 (`.mjs` or `"type": "module"`). Sandboxed preload scripts cannot use ESM imports. Await everything that must finish before the `ready` event |
| Electron support window | The Electron team supports the latest 3 stable major versions; the latest published on npm at verification time was 45.2.1. Chromium and Node versions change per major, so read the breaking-changes list before upgrading |
| Electron packaging | Electron Forge (`@electron-forge/cli` 8.x; packager, makers, publishers, plugins) or electron-builder 26.x (declarative YAML, built-in `electron-updater`). Forge 8 ships as ESM packages and its alpha notes state a minimum of Node 22.12.0; confirm in the current release notes |
| Electron signing | macOS: Developer ID certificate, hardened runtime, notarisation with `notarytool`, via `osxSign` and `osxNotarize` in Forge or `@electron/notarize`. Windows: Azure Artifact Signing (formerly Trusted Signing) or an EV or standard certificate on compliant hardware |
| Electron updates | Built-in `autoUpdater` (Squirrel) on macOS and Windows; `update-electron-app` for public GitHub repos through update.electronjs.org; static storage manifests; electron-updater with electron-builder. Updates must come from signed builds over HTTPS |
| Tauri architecture | Rust core process hosts the app and the system webview (WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux). The frontend talks to Rust through `invoke` (commands), events and channels. No bundled Chromium or Node |
| Tauri commands | `#[tauri::command]` functions registered once through `tauri::generate_handler![...]` in `invoke_handler`; called from `invoke` in `@tauri-apps/api/core`. Arguments are deserialised with serde; errors need a `Serialize` type |
| Tauri capabilities | JSON or TOML files in `src-tauri/capabilities/` map permissions to windows or webviews (`identifier`, `windows`, `webviews`, `permissions`, `platforms`, `remote`). Files in that directory are enabled automatically unless `app.security.capabilities` lists specific ones. Plugin permissions follow `<plugin>:<default or allow-command or deny-command>` |
| Tauri commands vs permissions | Commands registered by the app are callable from every window by default. Restrict them with `tauri_build::AppManifest::commands` in `build.rs` plus app permission files in `src-tauri/permissions/*.toml` |
| Tauri updater | `tauri-plugin-updater` verifies a minisign-style signature made with a key from `tauri signer generate`; `plugins.updater.pubkey` holds the public key content, `bundle.createUpdaterArtifacts` is `true`, and the private key is supplied only through `TAURI_SIGNING_PRIVATE_KEY` in the build environment |
| Tauri mobile | iOS and Android targets via `tauri ios init` and `tauri android init`; the app entry is a library with `#[cfg_attr(mobile, tauri::mobile_entry_point)]`. Capabilities can target `iOS` and `android` through `platforms`. Plugin support varies, so check each plugin page |
| Testing | Playwright `_electron.launch` (experimental in Playwright), WebdriverIO with `wdio-electron-service`; Tauri uses `tauri-driver`, which supports Windows and Linux but not macOS desktop (no WKWebView driver); Rust unit tests for command logic with `tauri::test` mocks |

## 3. Workflow

1. Identify the framework from the repository: `electron` and `forge.config.*` or `electron-builder.yml` in `package.json`, or `src-tauri/tauri.conf.json`. Record the framework major version, the Node and Rust toolchain versions and the target operating systems before proposing changes.
2. Draw the trust boundary. List what the renderer or webview may load (bundled assets only, or remote URLs) and what privileged operations exist (file system, shell, network, secrets). Remote or user-supplied content moves the design toward more isolation, not less.
3. Define the smallest privileged surface: a named IPC channel per operation (Electron) or one command per operation with an explicit capability (Tauri). Validate inputs in the privileged side, never in the UI alone.
4. Implement, then run the project's own commands: `npm run start` or `npm run make` for Electron, `npm run tauri dev` or `cargo tauri dev` for Tauri. Open dev tools in the renderer and confirm that `process`, `require` and `window.__TAURI__` (when `withGlobalTauri` is off) behave as designed.
5. Harden before packaging: Electron fuses and CSP; Tauri CSP, capability review and permission scopes. Read `src-tauri/gen/schemas` (Tauri) or `npx @electron/fuses read` output (Electron) to confirm.
6. Package on each target OS (or in a CI matrix), sign, notarise, and install the produced artifact on a clean machine. Test the update path from the previous release to the new one with real signed artifacts.
7. Keep signing material in CI secrets and the operating system keychain. Report which commands ran and which platforms were exercised.

## 4. Decision Rules

- If the team is JavaScript-only, needs identical rendering on every OS, or depends on Node native modules, an existing Electron codebase or Chromium-only web APIs, choose Electron. If minimal download size, low idle memory and a Rust backend are priorities and the UI tolerates three different webview engines, choose Tauri.
- If a Tauri UI must look identical on Windows, macOS and Linux, test each platform: WebView2 is Chromium based, WKWebView and WebKitGTK are WebKit based, and feature support and bugs differ by OS and OS version.
- If a renderer shows only bundled code, keep `contextIsolation` and sandbox defaults and expose a typed API. If it shows remote content, give that window no preload API at all and treat it as a hostile web page.
- If an operation needs Node in Electron, run it in the main process behind `ipcMain.handle`, or in `utilityProcess` when the input is untrusted or the work is heavy. Do not turn on `nodeIntegration` to avoid writing IPC.
- If the Electron app does not use `child_process.fork` or `ELECTRON_RUN_AS_NODE`, disable the `RunAsNode` fuse; disable `EnableNodeOptionsEnvironmentVariable` and `EnableNodeCliInspectArguments` for production builds; enable `EnableEmbeddedAsarIntegrityValidation` with `OnlyLoadAppFromAsar`.
- If pages are served from `file://`, prefer a custom protocol (`protocol.handle`) and disable `GrantFileProtocolExtraPrivileges`.
- If you are starting an Electron project, use Electron Forge (official tooling, fuses plugin in templates) unless the team already runs electron-builder or needs its `electron-updater` flow and installer targets. Keep one packager per repository.
- If updates are needed for a public GitHub project, `update-electron-app` is the shortest path; for private distribution use static storage with `autoUpdater`, electron-updater, or a self-hosted update server. Linux has no `autoUpdater`; use the distribution's package manager or an AppImage updater, and check the current docs.
- If a Tauri frontend needs file access, grant `fs` permissions with narrow scopes (`$APPDATA/myapp/*`) instead of a broad home scope; prefer a dedicated command that opens a path the user picked through the dialog plugin.
- If long-running Rust work reports progress, use a `Channel` for ordered streaming to one caller and events for broadcast; do not poll from JavaScript.
- If the sidecar is a Node or Python program, remember that it ships as a separate binary per target triple and needs its own signing; prefer a Rust implementation when the logic is small.
- If end-to-end testing is needed on macOS for Tauri, the official `tauri-driver` path is unavailable; test the web layer in a browser with mocked IPC and cover Rust logic with unit tests.

## 5. Coding Standards

- Name IPC channels by verb and domain (`settings:read`, `file:save`). One handler per channel; no generic "run this" or "eval this" channel.
- Validate every IPC payload in the main process with a schema validator or hand-written type guards. Reject unknown keys and bound string lengths and array sizes.
- Never expose `ipcRenderer`, `ipcRenderer.send`, `require`, `shell` or `fs` through the bridge. Wrap each call in a function that fixes the channel.
- Return plain serialisable data from handlers. Throw `Error` for failures; the renderer receives a message, so do not leak paths, stack traces or secrets.
- Use `app.whenReady()` before creating windows; call `app.requestSingleInstanceLock()` for apps that must be single instance.
- In Rust, keep commands thin: parse arguments, call a plain function that is unit-testable without Tauri, map errors into a serialisable enum (`thiserror` plus a manual `Serialize` impl).
- Prefer `async fn` commands for I/O; an async command with borrowed arguments such as `&str` must return `Result`. Use `tauri::State<'_, T>` for shared state registered with `.manage(...)` and wrap mutable state in `Mutex` (or an async mutex when held across `.await`).
- Call `invoke` with camelCase argument names from JavaScript; the Rust parameters are snake_case. Use `#[tauri::command(rename_all = "snake_case")]` only when the frontend sends snake_case, and check the current docs.

## 6. Project Structure

```text
electron-app/
|-- package.json
|-- forge.config.ts            # packagerConfig, makers, publishers, FusesPlugin
|-- src/
|   |-- main/
|   |   |-- index.ts           # app lifecycle, window creation, session hardening
|   |   |-- ipc/               # one file per domain, handlers validate input
|   |   `-- updater.ts
|   |-- preload/
|   |   `-- index.ts           # contextBridge.exposeInMainWorld with narrow API
|   |-- shared/
|   |   `-- channels.ts        # channel names and payload types
|   `-- renderer/              # web UI (any framework), no Node access
`-- tests/e2e/                 # Playwright _electron tests
```

```text
tauri-app/
|-- package.json               # frontend, @tauri-apps/api and plugin JS packages
|-- src/                       # frontend sources
`-- src-tauri/
    |-- Cargo.toml             # tauri, tauri-build, plugins
    |-- build.rs               # tauri_build::build() or try_build with AppManifest
    |-- tauri.conf.json        # identifier, build, app.security.csp, bundle, plugins
    |-- capabilities/
    |   `-- default.json       # windows -> permissions
    |-- permissions/           # optional app permission files (TOML)
    |-- binaries/              # sidecars, named <name>-<target-triple>
    |-- icons/
    `-- src/
        |-- main.rs            # calls the library run function
        |-- lib.rs             # Builder, plugins, invoke_handler, mobile entry point
        `-- commands/          # #[tauri::command] modules
```

## 7. Design Patterns

- **Typed bridge**: the preload exports a single object whose methods call `ipcRenderer.invoke` with a fixed channel; a `.d.ts` file declares it on `Window`. The renderer imports no Electron code.
- **Service in main**: IPC handlers delegate to plain service classes (settings store, file service). Tests call the services directly; handlers contain only validation and mapping.
- **Window factory**: one function creates every `BrowserWindow` with the hardened `webPreferences`, the navigation guards and the CSP session hook, so no window is created with ad-hoc options.
- **Utility process for untrusted work**: parsing large or untrusted files, native modules and CPU-bound tasks run in `utilityProcess.fork` and talk to the main process over `MessagePort`.
- **Command and event split (Tauri)**: commands for request and response, `Channel<T>` for streaming results to the caller, `app.emit` and `listen` for application-wide notifications.
- **Capability per window class**: separate capability files for the main window, a settings window and any window that loads remote content, each with its own minimal permission list.
- **Scoped plugin permissions**: combine `fs:allow-read-text-file` style command permissions with an explicit `fs:scope` allow list, and add `deny` entries for sensitive paths (deny takes precedence).
- **Sidecar behind a command**: expose one Rust command that starts the sidecar with a validated argument list; keep `shell:allow-execute` limited to that sidecar and an argument validator.
- **Update orchestration**: check on a timer after startup in the main process or Rust side, download in the background, ask the user, then restart; never block startup on an update check.

## 8. Best Practices

- Start from the framework templates (Forge templates, `create-tauri-app`) and keep their security defaults; remove a default only with a documented reason.
- Treat the renderer as an untrusted web page even when it loads only your files: an XSS bug there should not reach the file system.
- Store user secrets with `safeStorage` (Electron), the OS keychain through a Rust crate or a Tauri plugin (check the current plugin list), never in `localStorage`, config JSON or the bundle. API keys that belong to the vendor stay on a backend; the desktop app authenticates the user and calls that backend.

## 9. Performance

- Measure first: Chromium DevTools Performance panel for the renderer, `--cpu-prof` and `--inspect` in development for the main process, and `cargo flamegraph` or `tracing` spans for Rust.
- Electron startup: import only what the first window needs, lazy-load heavy modules with dynamic `import()`, defer non-critical work until after the window shows, and bundle main and preload with esbuild, Vite or webpack to avoid thousands of small file reads.
- Avoid blocking the main process: it also drives window management and IPC. Move CPU work to `utilityProcess` or worker threads, and use async fs APIs.
- Never use `ipcRenderer.sendSync` or the deprecated `remote` module; synchronous IPC blocks the renderer until the main process answers.
- Send large payloads (images, buffers) through `MessagePort`, custom protocols or file paths instead of repeated JSON `invoke` calls.
- Call `Menu.setApplicationMenu(null)` when the default menu is unused on Windows and Linux; remove unused polyfills and avoid blocking network requests during startup.
- Tauri: release builds only for measurements (`tauri build`); profile with `[profile.release]` options such as `lto`, `codegen-units = 1`, `opt-level` and `strip` after measuring, and keep binary size in mind when adding crates.
- Tauri commands that run longer than a few milliseconds should be `async` so they do not block the main thread; heavy CPU work belongs on a spawned task or thread pool.

## 10. Security

- Electron hardening baseline for any window: `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`, `webSecurity` on, no `allowRunningInsecureContent`, no experimental features, no `enableBlinkFeatures`, no `allowpopups` on webviews.
- Define a Content Security Policy for every renderer page (a `<meta http-equiv>` tag or response headers through `session.webRequest.onHeadersReceived`): `default-src 'self'`, no `unsafe-eval`, no `unsafe-inline` scripts.
- Validate `event.senderFrame` in every `ipcMain.handle`: compare `senderFrame.origin` (not the URL) with an allow-list, and handle a `null` frame.
- Block navigation away from known origins with `will-navigate`, deny `window.open` with `setWindowOpenHandler(() => ({ action: 'deny' }))`, and route external links through an allow-listed `shell.openExternal` after parsing the URL with `new URL()` and checking protocol (`https:` or `mailto:`) and host. Never pass a user-controlled string unchecked.
- Handle `session.setPermissionRequestHandler` and `setPermissionCheckHandler` to deny camera, microphone, notifications and other permissions unless needed for a trusted origin.
- Flip fuses at package time (before signing) and verify with `npx @electron/fuses read --app <path>`. Disable `RunAsNode`, `EnableNodeOptionsEnvironmentVariable` and `EnableNodeCliInspectArguments` in production unless required.
- Keep Electron current (the project supports the latest three majors only), update dependencies, and remove unused native modules.
- Tauri: set `app.security.csp` in `tauri.conf.json` (Tauri adds nonces and hashes for bundled assets); avoid CDN scripts; allow `'wasm-unsafe-eval'` only for WebAssembly frontends.
- Tauri: grant the minimum permissions per window. Remember that all registered app commands are open to every window until restricted with `AppManifest::commands` and app permissions. Remote URLs get API access only through a capability with `remote.urls`, so avoid it.
- Tauri: scope `fs`, `shell` and `opener` style permissions to explicit paths, programs and argument validators. Do not use `shell:allow-execute` with an open command name.
- Auto-update security: serve manifests and artifacts over HTTPS only (Tauri enforces TLS in production unless `dangerousInsecureTransportProtocol` is set; do not set it), verify signatures, and sign installers.
- Never place secrets in renderer code, `tauri.conf.json`, `Cargo.toml` `build.rs` outputs or the Electron ASAR. Build-time secrets come from CI environment variables and are used only by the signing step.

## 11. Testing

- Unit-test main-process services and Rust functions without launching the app. In Rust, use `tauri::test` mock builders for commands that need an `AppHandle` (check the current API in docs.rs).
- Electron end-to-end: `@playwright/test` with `_electron.launch({ args: ['.'] })`; `electronApp.evaluate` runs code in the main process; `electronApp.firstWindow()` returns a `Page`. Playwright describes Electron support as experimental; pin its version.
- Run end-to-end tests against the packaged app as well as the dev build, because fuses, ASAR, CSP and path differences appear only after packaging.
- WebdriverIO with `wdio-electron-service` is an alternative with built-in main-process mocking.
- Tauri end-to-end: `tauri-driver` wraps the native WebDriver servers (Microsoft Edge Driver on Windows, WebKitWebDriver on Linux) and works with WebdriverIO or Selenium; macOS desktop is not supported by it. On CI, Linux needs a virtual display such as `xvfb-run`.
- Test security rules directly: a test that loads an untrusted origin must fail to call a privileged IPC channel, and a test that opens a disallowed URL must be blocked.
- Test the updater with a local HTTPS or test feed and two real signed builds; verify rollback by publishing a higher version, not by deleting a release.

## 12. Review Checklist

- [ ] Every window uses `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`; no `webSecurity: false`.
- [ ] Preload exposes named functions only; `ipcRenderer` and Node modules are not exposed.
- [ ] Each `ipcMain.handle` validates arguments and `senderFrame.origin`.
- [ ] CSP set; `will-navigate` and `setWindowOpenHandler` deny by default; `openExternal` is allow-listed.
- [ ] Fuses configured and verified on the built artifact.
- [ ] Tauri capabilities list only needed permissions per window; no wildcard windows with broad scopes.
- [ ] Tauri app commands that need restriction are listed in the app manifest; fs, shell and dialog scopes are narrow.
- [ ] Tauri CSP is set and does not allow remote scripts.
- [ ] No secrets, private keys or tokens in repository, renderer, config or bundle.
- [ ] Artifacts are signed on macOS (notarised and stapled) and Windows; the updater verifies signatures over HTTPS.
- [ ] Update path tested from the previous release; version numbers increase monotonically.
- [ ] Dev dependencies and native modules are rebuilt for the Electron ABI (`@electron/rebuild`) when used.
- [ ] Tests run on every target OS and include a packaged-app smoke test.
- [ ] Logging, crash handling and user-data locations follow platform conventions.

## 13. Production Notes

- CI matrix: build each OS on its own runner (macOS for macOS, Windows for Windows, Linux for Linux); cross-compiling signed desktop artifacts is fragile. Keep signing in the final job with secrets limited to that job.
- Electron macOS: sign with a Developer ID Application certificate, enable hardened runtime, notarise with `notarytool` using an App Store Connect API key or an app-specific password, and staple the ticket. Notarisation credentials come from environment variables, never from the repository.
- Electron Windows: use Azure Artifact Signing (availability is limited to certain countries and organisation types; check the docs) or an EV or standard certificate held on compliant hardware or a cloud HSM service. Unsigned apps trigger SmartScreen warnings.
- Tauri macOS: `APPLE_SIGNING_IDENTITY` (or `bundle.macOS.signingIdentity`) selects the identity; notarisation uses `APPLE_API_KEY`, `APPLE_API_ISSUER` and `APPLE_API_KEY_PATH`, or `APPLE_ID`, `APPLE_PASSWORD` and `APPLE_TEAM_ID`. In CI, `tauri-apps/tauri-action` accepts a base64 certificate secret.
- Tauri Windows: check the current signing guide for `bundle.windows` settings (certificate thumbprint or a custom sign command) and for NSIS versus MSI installer targets.
- Tauri updater key: generate once with `tauri signer generate -w <path>`, store the private key and its password as CI secrets, publish only the public key in `tauri.conf.json`. Losing the private key means existing installs cannot receive signed updates.
- Electron auto-update: `autoUpdater` works on macOS and Windows only and needs signed apps; Squirrel.Windows installs per user and expects a Squirrel-based installer. Differential updates depend on the chosen toolchain.
- Upgrade Electron by one major at a time, read the breaking-changes document for each, and rerun fuse and security checks because defaults can change.

## 14. Examples

Hardened Electron window factory, with the main process written as an ES module.

```ts
// src/main/window.ts
import { app, BrowserWindow, session, shell } from 'electron';
import path from 'node:path';

const TRUSTED_ORIGIN = 'app://bundle'; // custom protocol serving bundled files
const EXTERNAL_HOSTS = new Set(['example.com', 'docs.example.com']);

export function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1100,
    height: 760,
    show: false,
    webPreferences: {
      preload: path.join(import.meta.dirname, '../preload/index.cjs'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });

  win.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== TRUSTED_ORIGIN) event.preventDefault();
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    openExternalSafely(url);
    return { action: 'deny' };
  });

  win.once('ready-to-show', () => win.show());
  return win;
}

function openExternalSafely(raw: string): void {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return;
  }
  if (url.protocol === 'https:' && EXTERNAL_HOSTS.has(url.hostname)) {
    void shell.openExternal(url.toString());
  }
}

export function installCsp(): void {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self' app:; script-src 'self'; object-src 'none'; base-uri 'none'",
        ],
      },
    });
  });
}

app.on('web-contents-created', (_event, contents) => {
  contents.on('will-attach-webview', (event) => event.preventDefault());
});
```

Narrow preload bridge and a validated handler.

```ts
// src/preload/index.cts (sandboxed preload: CommonJS, only require('electron'))
import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('api', {
  readSetting: (key: string): Promise<string | null> =>
    ipcRenderer.invoke('settings:read', key),
});
```

```ts
// src/main/ipc/settings.ts
import { ipcMain } from 'electron';

const ALLOWED_KEYS = new Set(['theme', 'language']);

ipcMain.handle('settings:read', (event, key: unknown) => {
  const origin = event.senderFrame?.origin;
  if (origin !== 'app://bundle') throw new Error('forbidden');
  if (typeof key !== 'string' || !ALLOWED_KEYS.has(key)) throw new Error('invalid key');
  return readSettingFromDisk(key);
});

declare function readSettingFromDisk(key: string): string | null;
```

Tauri command with typed errors and a capability.

```rust
// src-tauri/src/lib.rs
use serde::Serialize;

#[derive(Debug, thiserror::Error)]
enum AppError {
    #[error("invalid name")]
    InvalidName,
}

impl Serialize for AppError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}

#[tauri::command]
fn greet(name: String) -> Result<String, AppError> {
    if name.is_empty() || name.len() > 64 {
        return Err(AppError::InvalidName);
    }
    Ok(format!("Hello, {name}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "main-capability",
  "description": "Permissions for the main window",
  "windows": ["main"],
  "permissions": ["core:default", "dialog:allow-open"]
}
```

```ts
import { invoke } from '@tauri-apps/api/core';

const message = await invoke<string>('greet', { name: 'Ada' });
```

Key handling for signing: keep it out of the repository and the app.

```bash
# CI step (secrets come from the CI secret store, never from files in the repo)
export TAURI_SIGNING_PRIVATE_KEY="$UPDATER_PRIVATE_KEY"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="$UPDATER_KEY_PASSWORD"
npm run tauri build
```

## 15. Common Mistakes

- **`nodeIntegration: true` or `contextIsolation: false` "to make it work"**: a single XSS then becomes remote code execution. Use a preload with `contextBridge`.
- **Exposing `ipcRenderer.send` or the whole `ipcRenderer`** through the bridge: any script in the page can call any channel. Wrap each channel in a named function.
- **IPC handlers that trust the payload and the sender**: validate argument types and `senderFrame.origin`.
- **`shell.openExternal(userUrl)` without checks**: custom protocol handlers can run local programs. Parse the URL and allow-list protocol and host.
- **Checking URLs with `startsWith`**: `https://example.com.evil.test` passes. Compare `new URL(x).origin`.
- **Loading remote pages in a window that has a powerful preload**: give remote windows no API, or load them in a `WebContentsView` with a separate session.
- **Flipping fuses after signing** (or not at all): the signature breaks or the hardening never applies. Use the Forge fuses plugin or flip before the signing step.
- **Using `file://` plus `GrantFileProtocolExtraPrivileges` enabled**: register a custom protocol and disable the fuse.
- **Native modules not rebuilt for Electron**: the build works in Node but crashes in the app. Rebuild with `@electron/rebuild` (Forge does it during packaging).
- **Assuming sandboxed preloads can `import` ES modules or Node built-ins**: they only get `require('electron')` subsets; bundle the preload into one CommonJS file.
- **ESM main with unawaited dynamic imports before `ready`**: `app.setPath` and similar calls run too late. Use top-level `await`.
- **Granting `core:default` plus broad `fs:scope` to every window in Tauri**: any UI bug reaches the disk. Split capabilities per window and narrow scopes.
- **Assuming Tauri app commands are protected by capabilities**: registered commands are callable from all windows unless restricted in the app manifest.
- **Setting `withGlobalTauri` or a loose CSP to simplify the frontend**: it enlarges the attack surface for every script in the page.
- **Putting `TAURI_SIGNING_PRIVATE_KEY` or Apple credentials in `.env` files that get bundled or committed**: store in CI secrets.
- **Sidecar binary without the target-triple suffix**: the bundler cannot find `binaries/app-x86_64-unknown-linux-gnu`. Use `rustc --print host-tuple` (Rust 1.84 or later) to get the suffix.

## 16. References

- [references/electron-security.md](references/electron-security.md): webPreferences baseline, preload and IPC design, sender validation, CSP, navigation and permissions, custom protocols, fuses configuration, ESM notes.
- [references/electron-packaging-updates.md](references/electron-packaging-updates.md): Forge and electron-builder configuration, macOS notarisation, Windows signing, auto-update options, performance and Playwright or WebdriverIO testing.
- [references/tauri-commands-capabilities.md](references/tauri-commands-capabilities.md): commands, state, errors, channels and events, capability and permission files, scopes, plugin permissions, CSP, remote access.
- [references/tauri-distribution.md](references/tauri-distribution.md): bundling targets, sidecars, updater keys and manifest, macOS and Windows signing, mobile outline, tauri-driver tests and Electron versus Tauri trade-offs.
- Electron documentation: https://www.electronjs.org/docs/latest/ ; security checklist https://www.electronjs.org/docs/latest/tutorial/security ; fuses https://www.electronjs.org/docs/latest/tutorial/fuses ; breaking changes https://www.electronjs.org/docs/latest/breaking-changes
- Electron Forge: https://www.electronforge.io/ ; electron-builder: https://www.electron.build/
- Tauri 2 documentation: https://v2.tauri.app/ ; capabilities https://v2.tauri.app/security/capabilities/ ; updater https://v2.tauri.app/plugin/updater/
- Playwright Electron API: https://playwright.dev/docs/api/class-electron
