# Tauri 2 Commands, Events, Capabilities and Permissions

How the Tauri 2 frontend talks to Rust and how access is restricted: commands, state, errors, channels and events, capability and permission files, scopes, plugin permissions, CSP and remote access. Checked against the Tauri 2 documentation and crate versions tauri 2.12.5, tauri-build 2.7.4, @tauri-apps/api 2.12.4, tauri-plugin-fs 2.7.1 and tauri-plugin-shell 2.6.0 (2026-10).

## Contents

1. [Architecture](#1-architecture)
2. [Commands](#2-commands)
3. [State and errors](#3-state-and-errors)
4. [Channels and events](#4-channels-and-events)
5. [Capabilities](#5-capabilities)
6. [Permissions and scopes](#6-permissions-and-scopes)
7. [Restricting app commands](#7-restricting-app-commands)
8. [Plugins](#8-plugins)
9. [CSP and remote content](#9-csp-and-remote-content)

## 1. Architecture

- The Rust core process owns windows, tray, menus, file access and plugins. The UI runs in the operating system webview: WebView2 on Windows, WKWebView on macOS and iOS, WebKitGTK on Linux, Android WebView on Android.
- The frontend can be any web framework that outputs static files (or a dev server URL during `tauri dev`). `build.frontendDist`, `build.devUrl`, `build.beforeDevCommand` and `build.beforeBuildCommand` in `tauri.conf.json` connect it.
- IPC is message passing: JavaScript calls `invoke('name', args)`, Rust returns serialised data. Everything crossing the boundary is serialised with serde (JSON by default; raw bytes via `tauri::ipc::Response` or `Request`).
- `@tauri-apps/api` provides JS modules: `core` (invoke, Channel, convertFileSrc), `event`, `window`, `webview`, `path`, `menu`, `tray`, `app`. Plugin JS packages are named `@tauri-apps/plugin-<name>`.
- The default scaffold (`npm create tauri-app@latest`, package `create-tauri-app`) generates `src-tauri/src/lib.rs` with the app logic and a thin `main.rs`, so the same code serves desktop and mobile.
- `withGlobalTauri` is off by default; import from `@tauri-apps/api` rather than using `window.__TAURI__`, which makes a stronger case for a strict CSP.

## 2. Commands

```rust
// src-tauri/src/commands/notes.rs
use tauri::State;

use crate::state::NotesStore;

#[tauri::command]
pub async fn add_note(store: State<'_, NotesStore>, title: String, body: String) -> Result<u64, String> {
    if title.trim().is_empty() || title.len() > 200 {
        return Err("title must be 1-200 characters".into());
    }
    store.insert(title, body).await.map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_titles(store: State<'_, NotesStore>) -> Vec<String> {
    store.titles()
}
```

```rust
// src-tauri/src/lib.rs
mod commands;
mod state;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(state::NotesStore::default())
        .invoke_handler(tauri::generate_handler![
            commands::notes::add_note,
            commands::notes::list_titles,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

```ts
import { invoke } from '@tauri-apps/api/core';

const id = await invoke<number>('add_note', { title: 'Plan', body: 'Draft' });
```

- Register all commands in one `generate_handler!` call. Calling `invoke_handler` more than once keeps only the last one.
- Commands in a module other than `lib.rs` must be `pub` and referenced by path in `generate_handler!`.
- JavaScript argument keys are camelCase by default (`filePath` for `file_path`); the docs describe the `rename_all` attribute to change that.
- Async commands run on the async runtime. A command that takes borrowed arguments (`&str`) or `State` and is `async` must return `Result`; use owned types (`String`) when possible.
- Commands can take `tauri::AppHandle`, `tauri::WebviewWindow` (the caller), `tauri::State<T>` and `tauri::ipc::Request` as injected arguments in addition to deserialised ones.
- Prefer typed arguments (`struct` with `#[derive(Deserialize)]`) for multi-field inputs; serde rejects wrong shapes before your code runs.
- Return `Result<T, E>` where `E: Serialize`; `Err` becomes a rejected promise in JavaScript.

## 3. State and errors

- Register state with `.manage(value)` on the builder or `app.manage(value)` in `setup`; read it with `State<'_, T>` or `app.state::<T>()`. State is shared across threads, so interior mutability (`Mutex`, `RwLock`, atomics) is required. Use `tokio::sync::Mutex` when a lock is held across `.await`.
- Errors that reach the UI should implement `Serialize` (a manual impl that serialises `to_string()` of a `thiserror` enum works well, see SKILL.md section 14).
- Do not serialise internal paths, connection strings or secrets into errors that reach the UI; log them in Rust and send a stable message or code.

## 4. Channels and events

```rust
use tauri::ipc::Channel;
use serde::Serialize;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase", tag = "event", content = "data")]
pub enum DownloadEvent {
    Progress { percent: u8 },
    Done,
}

#[tauri::command]
pub async fn download(url: String, on_event: Channel<DownloadEvent>) -> Result<(), String> {
    // validate url against an allow-list here before any network call
    for percent in [10u8, 50, 100] {
        on_event.send(DownloadEvent::Progress { percent }).map_err(|e| e.to_string())?;
    }
    on_event.send(DownloadEvent::Done).map_err(|e| e.to_string())
}
```

```ts
import { invoke, Channel } from '@tauri-apps/api/core';

type DownloadEvent =
  | { event: 'progress'; data: { percent: number } }
  | { event: 'done' };

const onEvent = new Channel<DownloadEvent>();
onEvent.onmessage = (msg) => console.log(msg);
await invoke('download', { url: 'https://example.com/file', onEvent });
```

- `Channel<T>` streams ordered messages from Rust to one caller and is the recommended tool for progress, logs and large streamed data; the docs use it for chunked image reading.
- Events (`app.emit`, `window.emit`, `emit_to`; JS `listen`, `once`, `emit` from `@tauri-apps/api/event`) are for notifications that several listeners may handle. Payloads are JSON, so keep them small.
- JavaScript `listen` returns an unlisten function; call it when the component unmounts.
- Event access is also governed by permissions (`core:event:default` and related); an event emitted to a window without that permission is not delivered.

## 5. Capabilities

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "main-capability",
  "description": "Main window: core APIs and a file open dialog",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "dialog:allow-open",
    "fs:allow-read-text-file",
    {
      "identifier": "fs:scope",
      "allow": [{ "path": "$APPDATA/notes/**" }]
    }
  ]
}
```

- Location: `src-tauri/capabilities/*.json` (or `.json5`, `.toml`). Every file in the directory is enabled automatically. If `app.security.capabilities` in `tauri.conf.json` lists identifiers (or inline capabilities), only those are used.
- Fields: `identifier`, `description`, `windows` (labels, globs allowed), `webviews`, `permissions`, `platforms` (`linux`, `macOS`, `windows`, `iOS`, `android`) and `remote` (see section 9).
- A window that matches several capabilities gets the union of their permissions. Keep window labels specific, avoid `"windows": ["*"]` with powerful permissions.
- Use the generated schema (`../gen/schemas/desktop-schema.json`, `mobile-schema.json`, `remote-schema.json`) in the editor for completion and validation. Schemas are generated during build.
- Platform-specific capability files (`desktop.json`, `mobile.json`) keep plugin permissions that exist on only some targets from breaking the others.
- Create one capability per window class: the main window, a settings window, a window that loads a remote site (with its own very small list).

## 6. Permissions and scopes

- Identifier forms: `<plugin>:default`, `<plugin>:allow-<command>`, `<plugin>:deny-<command>`, and plugin-defined sets such as `fs:read-files`. The `tauri-plugin-` prefix is implied. Names use lowercase ASCII and hyphens.
- `core:default` and other `core:*` entries cover built-in modules (path, event, window, webview, app, resources, menu, tray, image). Review what `core:default` includes before accepting it for windows that show less trusted content, and prefer individual `core:window:allow-set-title` style entries when you need little.
- Application permissions are TOML files in `src-tauri/permissions/`:

```toml
# src-tauri/permissions/notes.toml
[[permission]]
identifier = "allow-add-note"
description = "Allows the add_note command"
commands.allow = ["add_note"]

[[set]]
identifier = "notes-basic"
description = "Basic notes access"
permissions = ["allow-add-note"]
```

- A scope narrows what an allowed command can touch. For `fs`, a scope entry is a path pattern with a base-directory variable (`$APPDATA`, `$APPCONFIG`, `$DOCUMENT`, `$HOME`, `$TEMP` and others). `allow` and `deny` entries can be combined; deny takes precedence over allow.
- Prefer app-specific directories (`$APPDATA`, `$APPLOCALDATA`) over `$HOME`, and prefer letting the user pick files through the dialog plugin, which adds the chosen path to the runtime scope.
- Plugin permission lists are in each plugin's documentation page and in `permissions/` inside the plugin crate; run a build after adding a plugin to regenerate schemas, then search the schema for the identifier.
- Denied calls fail with an error naming the missing permission in the console, which speeds up debugging; add only the named permission.

## 7. Restricting app commands

- By default every command registered through `invoke_handler` can be called from every window and webview.
- To restrict, list them in `build.rs` so the build generates permissions for them, then add the generated `allow-<command>` permissions to each capability that needs them:

```rust
// src-tauri/build.rs
fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&["add_note", "list_titles", "download"]),
        ),
    )
    .expect("failed to run build script");
}
```

- Once `commands` is set, a command missing from a capability is rejected for that window. Generated app permission names follow the pattern `allow-<command-with-hyphens>`; confirm in the generated schema.
- Even with permissions in place, commands must validate their arguments: the permission says who may call, not what they send.

## 8. Plugins

| Plugin (crate / npm) | Purpose | Notes |
|---|---|---|
| `tauri-plugin-fs` / `@tauri-apps/plugin-fs` | Read and write files | Combine `fs:allow-*` command permissions with `fs:scope` |
| `tauri-plugin-shell` / `@tauri-apps/plugin-shell` | Spawn processes, sidecars | `shell:allow-execute`, `shell:allow-spawn` with `name`, `cmd`, `args` validators |
| `tauri-plugin-dialog` / `@tauri-apps/plugin-dialog` | Open, save, message dialogs | Picked paths join the fs scope |
| `tauri-plugin-store` / `@tauri-apps/plugin-store` | Persistent key-value store in a JSON file | Not encrypted; do not store secrets |
| `tauri-plugin-updater` / `@tauri-apps/plugin-updater` | Signed updates | See tauri-distribution.md |
| `tauri-plugin-process` / `@tauri-apps/plugin-process` | `relaunch`, `exit` | Needed after an update |

Add a plugin with `npm run tauri add <name>` (installs the crate and JS package and registers it), or manually: `cargo add tauri-plugin-fs`, `npm add @tauri-apps/plugin-fs`, `.plugin(tauri_plugin_fs::init())` on the builder, then add permissions to a capability. Desktop-only plugins, such as the updater, are registered inside `#[cfg(desktop)]` blocks, usually in `setup`.

- Shell scopes accept a fixed program name and an argument list where each entry is a literal or a `{ "validator": "<regex>" }` object. Use tight regular expressions and never `"args": true` for untrusted input.
- `tauri-plugin-store` writes plain JSON under the app data directory; keep tokens in the OS keychain through a dedicated crate or plugin (check the plugin list) instead.
- Check the plugin repository (`tauri-apps/plugins-workspace`) for platform support tables before using a plugin on mobile.

## 9. CSP and remote content

```json
{
  "app": {
    "security": {
      "csp": {
        "default-src": "'self' customprotocol: asset:",
        "connect-src": "ipc: http://ipc.localhost",
        "img-src": "'self' asset: http://asset.localhost blob: data:",
        "style-src": "'unsafe-inline' 'self'"
      }
    }
  }
}
```

- CSP protection exists only if `app.security.csp` is set. Tauri appends nonces and hashes for bundled scripts and styles at compile time, so write only what is specific to the app. The configuration may be a string or an object per directive.
- Include `'wasm-unsafe-eval'` in `script-src` if the frontend uses WebAssembly.
- Avoid remote scripts and CDNs. Bundle dependencies.
- Allow `connect-src` only to the API origins the app calls. Add `ipc:` and the localhost IPC origin shown above (the platform detail varies; take the current values from the CSP page of the docs).
- Remote API access is off by default: only bundled code may call commands. To allow a remote origin, add `remote` to a capability:

```json
{
  "$schema": "../gen/schemas/remote-schema.json",
  "identifier": "remote-docs",
  "windows": ["docs"],
  "remote": { "urls": ["https://*.example.com"] },
  "permissions": ["core:event:default"]
}
```

- Keep remote capabilities to the minimum permissions possible and never combine them with `fs` or `shell`.
