# Tauri 2 Distribution, Updater, Testing and Framework Choice

Bundling, sidecars, the updater plugin and its signing keys, platform code signing, mobile targets in outline, WebDriver testing and the Electron versus Tauri decision. Versions checked 2026-10: tauri 2.12.5, @tauri-apps/cli 2.12.4, tauri-plugin-updater 2.14.1, @tauri-apps/plugin-updater 2.14.1, @tauri-apps/plugin-process 2.4.0, tauri-driver 2.1.0, create-tauri-app 4.7.5.

## Contents

1. [Bundling](#1-bundling)
2. [Sidecars](#2-sidecars)
3. [Updater plugin](#3-updater-plugin)
4. [Update manifest and releases](#4-update-manifest-and-releases)
5. [macOS and Windows signing](#5-macos-and-windows-signing)
6. [CI release outline](#6-ci-release-outline)
7. [Mobile targets](#7-mobile-targets)
8. [Testing](#8-testing)
9. [Electron or Tauri](#9-electron-or-tauri)

## 1. Bundling

- `tauri build` compiles the Rust app in release mode, builds the frontend (`build.beforeBuildCommand`) and creates installers for the host OS. `tauri dev` runs the app with hot reload.
- Bundle section of `src-tauri/tauri.conf.json`:

```json
{
  "productName": "Notes",
  "version": "1.2.0",
  "identifier": "com.example.notes",
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.icns", "icons/icon.ico"],
    "createUpdaterArtifacts": true
  }
}
```

- Typical outputs: Windows NSIS (`.exe`) and WiX (`.msi`) installers, macOS `.app` and `.dmg`, Linux `.deb`, `.rpm` and AppImage. Restrict with `bundle.targets` or the `--bundles` flag.
- Building for an OS requires that OS (or a runner for it) for signed, distributable artifacts. Linux builds need the WebKitGTK development packages; the prerequisites page lists them per distribution.
- Windows apps need WebView2; the installer can bootstrap it (check the Windows installer page for the install mode options).
- The `identifier` is permanent after release: it keys the app data folder and update continuity.

## 2. Sidecars

A sidecar is an external binary bundled with the app, for example a Python or Node program compiled into one executable, or a database engine.

```json
{
  "bundle": {
    "externalBin": ["binaries/my-sidecar"]
  }
}
```

- File naming: for `binaries/my-sidecar`, place `src-tauri/binaries/my-sidecar-<target-triple>` for each target, for example `my-sidecar-x86_64-unknown-linux-gnu` or `my-sidecar-aarch64-apple-darwin`. Windows targets use `.exe`.
- Get the triple of the build machine with `rustc --print host-tuple` (Rust 1.84 and later) or `rustc -Vv` and read the `host:` line.
- Run from Rust with the shell plugin:

```rust
use tauri_plugin_shell::ShellExt;

#[tauri::command]
async fn run_sidecar(app: tauri::AppHandle, input: String) -> Result<String, String> {
    if input.len() > 1024 {
        return Err("input too long".into());
    }
    let output = app
        .shell()
        .sidecar("my-sidecar")
        .map_err(|e| e.to_string())?
        .args([input])
        .output()
        .await
        .map_err(|e| e.to_string())?;
    String::from_utf8(output.stdout).map_err(|e| e.to_string())
}
```

- `sidecar("my-sidecar")` takes the file name without the directory. From JavaScript, `Command.sidecar('binaries/my-sidecar')` must match the `externalBin` entry exactly, and the capability grants it:

```json
{
  "identifier": "shell:allow-execute",
  "allow": [
    {
      "name": "binaries/my-sidecar",
      "sidecar": true,
      "args": ["--mode", { "validator": "^[a-z]+$" }]
    }
  ]
}
```

- Keep the sidecar interface minimal: argument lists, not shell strings, and no network listeners unless required (bind to localhost with a random port and a token if so).

## 3. Updater plugin

1. Install: `npm run tauri add updater` (adds `tauri-plugin-updater` and `@tauri-apps/plugin-updater`). Add `tauri-plugin-process` and `@tauri-apps/plugin-process` for `relaunch`.
2. Generate signing keys once: `npm run tauri signer generate -- -w ~/.tauri/notes.key` (or `cargo tauri signer generate -w ...`). This prints a public key and writes the private key file.
3. Configure the public key and endpoints:

```json
{
  "bundle": { "createUpdaterArtifacts": true },
  "plugins": {
    "updater": {
      "pubkey": "CONTENT OF THE PUBLIC KEY FILE (not a path)",
      "endpoints": [
        "https://releases.example.com/{{target}}/{{arch}}/{{current_version}}"
      ]
    }
  }
}
```

4. Provide the private key to the build only through the environment: `TAURI_SIGNING_PRIVATE_KEY` (path or content) and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Never commit the key or embed it in the app. The build then writes a `.sig` file next to each updater artifact.
5. Register the plugin in Rust (desktop only) and add the permission `updater:default` to a capability:

```rust
tauri::Builder::default()
    .setup(|app| {
        #[cfg(desktop)]
        app.handle().plugin(tauri_plugin_updater::Builder::new().build())?;
        Ok(())
    })
    .plugin(tauri_plugin_process::init())
```

```ts
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

const update = await check();
if (update) {
  await update.downloadAndInstall((event) => {
    if (event.event === 'Progress') console.log('chunk', event.data.chunkLength);
  });
  await relaunch();
}
```

- URL variables available in endpoints: `{{current_version}}`, `{{target}}` (`linux`, `windows`, `darwin`) and `{{arch}}` (`x86_64`, `i686`, `aarch64`, `armv7`). Custom variables are not supported.
- The updater tries the next endpoint only after a non-2xx response. TLS is enforced in production; `dangerousInsecureTransportProtocol` exists but must stay off.
- The `pubkey` setting is the key content, not a file path.
- On Windows, `plugins.updater.windows.installMode` selects how the installer runs (see the updater page for values).
- Back up the private key and password in a secret manager. If they are lost, installed apps cannot trust any new key and users must reinstall.

## 4. Update manifest and releases

- A dynamic endpoint returns HTTP 204 when no update exists, or JSON with `version`, `url`, `signature` and optional `notes` and `pub_date` (RFC 3339) when one does.
- A static JSON file (for example attached to a release or object storage) contains `version`, `notes`, `pub_date` and a `platforms` object keyed by `<os>-<arch>` with `signature` (the content of the `.sig` file) and `url` for each. Check the updater page for the exact field list and key names (for example `linux-x86_64`, `windows-x86_64`, `darwin-aarch64`).
- `tauri-apps/tauri-action` can build, create a GitHub release and upload the updater manifest (`latest.json`) for you; check its README for inputs.
- Publish new artifacts first and the manifest last, so clients never see a manifest that points at missing files.

## 5. macOS and Windows signing

macOS:

- Sign with a Developer ID Application certificate. Set `APPLE_SIGNING_IDENTITY` (or `bundle.macOS.signingIdentity`). List identities with `security find-identity -v -p codesigning`. In CI, `APPLE_CERTIFICATE` (base64 of the exported certificate) and `APPLE_CERTIFICATE_PASSWORD` import it into a temporary keychain (the `tauri-action` flow).
- Notarise with either an App Store Connect API key (`APPLE_API_KEY` for the key id, `APPLE_API_ISSUER`, `APPLE_API_KEY_PATH` for the `.p8` file) or an Apple ID (`APPLE_ID`, an app-specific password in `APPLE_PASSWORD`, and `APPLE_TEAM_ID`).
- An identity of `-` produces an ad-hoc signature, useful for local Apple Silicon builds but not for distribution.
- If stapling fails on the first attempt, the docs mention `--skip-stapling` as a workaround; stapling lets Gatekeeper validate offline.
- Entitlements and `Info.plist` additions are set under `bundle.macOS` (for example for camera or microphone usage descriptions).

Windows:

- Unsigned installers trigger SmartScreen. Sign with an OV or EV certificate, or a cloud signing service. Tauri's Windows signing guide describes the `bundle.windows` settings (certificate thumbprint, timestamp URL and a custom sign command hook for cloud HSMs and Azure services); check the current page because settings names have changed between releases.
- Sign every produced executable and installer, and use a timestamp server.

## 6. CI release outline

```yaml
# .github/workflows/tauri-release.yml (fragment)
name: tauri-release
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  release:
    strategy:
      fail-fast: false
      matrix:
        include:
          - { platform: macos-latest, args: '--target aarch64-apple-darwin' }
          - { platform: macos-latest, args: '--target x86_64-apple-darwin' }
          - { platform: ubuntu-22.04, args: '' }
          - { platform: windows-latest, args: '' }
    runs-on: ${{ matrix.platform }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - uses: dtolnay/rust-toolchain@stable
      - name: Linux system packages
        if: startsWith(matrix.platform, 'ubuntu')
        run: |
          sudo apt-get update
          sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev patchelf
      - run: npm ci
      - uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
          TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
        with:
          tagName: ${{ github.ref_name }}
          releaseName: 'Notes ${{ github.ref_name }}'
          releaseDraft: true
          args: ${{ matrix.args }}
```

- The Linux package list and runner image change over time; copy the current list from the Tauri prerequisites page. Pin actions to full commit SHAs in production.
- Add the Apple and Windows signing secrets to the same `env` block only on the jobs that need them. Fork pull requests must not receive secrets.

## 7. Mobile targets

- Initialise with `npm run tauri android init` and `npm run tauri ios init`; run with `tauri android dev` and `tauri ios dev`; build with `tauri android build` and `tauri ios build`. iOS needs macOS and Xcode; Android needs Android Studio, the SDK and NDK.
- The shared app code lives in the library crate (`lib.rs`) with `#[cfg_attr(mobile, tauri::mobile_entry_point)]`.
- Capabilities use `platforms: ["iOS", "android"]` for mobile-only permissions (biometric, NFC, barcode scanner plugins) and `platforms: ["linux", "macOS", "windows"]` for desktop-only ones.
- Desktop-only plugins (updater, global shortcut, window state) must sit behind `#[cfg(desktop)]`. Mobile app updates go through the stores.

## 8. Testing

- Frontend: unit-test with the normal web tooling (Vitest, Jest) and mock IPC with `mockIPC` from `@tauri-apps/api/mocks` (check the current docs for the helper set).
- Rust: `cargo test` in `src-tauri` for logic; `tauri::test` mocks for command tests that need an app handle.
- End to end: `tauri-driver` (cargo install `tauri-driver`, crate version 2.1.0) is a wrapper that talks to the native WebDriver server of the platform: Microsoft Edge Driver on Windows and WebKitWebDriver on Linux. It is used with WebdriverIO or Selenium.
- macOS desktop is not supported by `tauri-driver` because there is no WKWebView driver; do E2E on Windows and Linux CI runners and rely on unit tests plus manual checks for macOS. Third-party drivers exist; evaluate maturity before depending on them.
- On Windows the Edge Driver version must match the installed WebView2 or Edge runtime; a mismatch can make the suite hang at connection time. Pass `--native-driver` to `tauri-driver` if the driver is not on `PATH`.

## 9. Electron or Tauri

| Factor | Electron | Tauri 2 |
|---|---|---|
| Runtime | Bundled Chromium and Node.js | OS webview plus Rust binary |
| Installer size | Large (Chromium included) | Much smaller; the app carries no browser engine |
| Rendering consistency | Same engine and version on every OS | WebView2 (Chromium), WKWebView and WebKitGTK differ; test each |
| Backend language | JavaScript or TypeScript with Node APIs and npm native modules | Rust; JavaScript sidecars possible |
| Ecosystem | Largest: Node modules, mature tooling, many examples | Growing plugin set; Rust crates for native work |
| Security model | Process isolation plus your own IPC checks; fuses; strong defaults since sandbox on | Deny-by-default capabilities and scoped permissions for built-in and plugin APIs; app commands open until restricted |
| Updates | Squirrel `autoUpdater`, electron-updater, update.electronjs.org | Updater plugin with mandatory signature verification |
| Mobile | None | iOS and Android supported in Tauri 2 |
| Team skills | Web developers can own everything | Needs at least one developer comfortable with Rust |
| Testing | Playwright (experimental) and WebdriverIO | tauri-driver on Windows and Linux |

- Choose Electron when pixel-identical rendering, Node native modules or the broad npm ecosystem matter more than size.
- Choose Tauri when download size, memory use and a Rust core matter and the UI works in the three platform webviews.
- Measure on your own app; size and memory differences depend on the UI and dependencies, and published benchmark figures vary by method.
- A migration from Electron to Tauri means rewriting main-process code in Rust (or a sidecar) and re-testing the UI in each webview; plan it as a rewrite of the native layer.
