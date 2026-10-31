# Electron Security and IPC

Hardening an Electron 45 application: process model, webPreferences, preload and IPC design, sender validation, CSP, navigation and permission handling, custom protocols, Electron Fuses and ESM in the main process. Based on the Electron security, sandbox, context isolation, fuses and ESM documentation (checked 2026-10).

## Contents

1. [Process model and defaults](#1-process-model-and-defaults)
2. [Window baseline](#2-window-baseline)
3. [Preload and contextBridge](#3-preload-and-contextbridge)
4. [IPC handlers and sender validation](#4-ipc-handlers-and-sender-validation)
5. [CSP and permissions](#5-csp-and-permissions)
6. [Navigation, windows and external links](#6-navigation-windows-and-external-links)
7. [Custom protocol instead of file](#7-custom-protocol-instead-of-file)
8. [Electron Fuses](#8-electron-fuses)
9. [ESM in the main process](#9-esm-in-the-main-process)
10. [Secrets and storage](#10-secrets-and-storage)

## 1. Process model and defaults

- Main process: one per app, Node.js with full OS access, owns windows, menus, tray, protocols and sessions.
- Renderer processes: Chromium pages. Since Electron 20 they are sandboxed without extra configuration; setting `nodeIntegration: true` disables the sandbox for that process.
- Preload scripts: run before the page, with access to a limited `require` (only `electron` and its renderer modules `contextBridge`, `crashReporter`, `ipcRenderer`, `nativeImage`, `webFrame`, `webUtils`) and a reduced `process` when sandboxed.
- Utility processes: `utilityProcess.fork(modulePath)` starts a Node.js child that can use `MessagePort` to talk to the main process or a renderer; use it instead of `child_process.fork` once the `RunAsNode` fuse is off.
- `contextIsolation` is on by default; the preload and the page have separate JavaScript worlds and only `contextBridge` values cross.

## 2. Window baseline

```ts
import { BrowserWindow } from 'electron';
import path from 'node:path';

export function secureWindow(): BrowserWindow {
  return new BrowserWindow({
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,   // default, set explicitly for reviewers
      sandbox: true,            // default since Electron 20
      nodeIntegration: false,   // default
      webSecurity: true,        // default
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      webviewTag: false,
    },
  });
}
```

- Setting defaults explicitly makes a regression visible in code review; do not rely on memory of defaults.
- Never set `nodeIntegration: true`, `contextIsolation: false`, `sandbox: false`, `webSecurity: false` or `nodeIntegrationInSubFrames: true` for pages that can show external content.
- Disable the `<webview>` tag (`webviewTag: false`); if it is required, verify options in `will-attach-webview` and strip preload and Node options.

## 3. Preload and contextBridge

```ts
// preload.ts (compiled to CommonJS for the sandboxed preload)
import { contextBridge, ipcRenderer } from 'electron';

export interface AppApi {
  openFile(): Promise<{ name: string; text: string } | null>;
}

const api: AppApi = {
  openFile: () => ipcRenderer.invoke('file:open'),
};

contextBridge.exposeInMainWorld('api', api);
```

- Expose functions, one per operation. Do not expose `ipcRenderer`, `ipcRenderer.send`, `ipcRenderer.on` (it passes the event object, leaking `sender`), `require`, `process`, `shell` or `fs`.
- Callbacks given to the bridge run in the page world; wrap `on` handlers so the renderer never receives the raw `IpcRendererEvent`.
- A sandboxed preload cannot use ESM `import` of other files; bundle the preload to a single CommonJS file (esbuild, Vite, webpack) and keep it small.

## 4. IPC handlers and sender validation

```ts
import { ipcMain, dialog, type IpcMainInvokeEvent } from 'electron';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const TRUSTED_ORIGINS = new Set(['app://bundle']);

function assertTrusted(event: IpcMainInvokeEvent): void {
  const frame = event.senderFrame;
  // Use the origin, not the URL. The frame can be null if it has gone away.
  if (!frame || !TRUSTED_ORIGINS.has(frame.origin)) {
    throw new Error('untrusted sender');
  }
}

ipcMain.handle('file:open', async (event) => {
  assertTrusted(event);
  const result = await dialog.showOpenDialog({ properties: ['openFile'] });
  if (result.canceled || result.filePaths.length === 0) return null;
  const file = result.filePaths[0];
  return { name: path.basename(file), text: await readFile(file, 'utf8') };
});
```

- Prefer `handle` and `invoke` (promise based, errors propagate) over `send`, `on` and `event.reply`.
- If a path must come from the renderer, resolve it with `path.resolve`, check that the result stays inside an allowed directory, and reject symlink escapes with `fs.realpath`.
- Validate shape and size of every argument (type guards or a schema library). Reject unknown channels by not registering them; never build a channel name from input.
- Return only the data the renderer needs. Do not return raw error objects containing paths.
- Every window and iframe can in theory send IPC messages; check `senderFrame` against an allow-list on all handlers that return data or perform privileged work.

## 5. CSP and permissions

```ts
import { session } from 'electron';

export function installSecurityPolicy(): void {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
            "img-src 'self' data:; connect-src 'self' https://api.example.com; " +
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        ],
      },
    });
  });

  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => {
    callback(false); // deny by default; allow named permissions for trusted origins
  });
  session.defaultSession.setPermissionCheckHandler(() => false);
}
```

- A CSP set through a `<meta http-equiv="Content-Security-Policy">` tag works for pages loaded from a custom protocol or file; headers are better when you control the protocol handler.
- Avoid `unsafe-eval` and inline scripts. Bundlers in development mode may need `unsafe-eval` for hot reload; keep that in the dev configuration only.
- Deny permissions by default and allow a named permission only for the trusted origin (check `webContents.getURL()` parsed with `new URL`, or the requesting origin passed to the handler).

## 6. Navigation, windows and external links

```ts
import { app, shell } from 'electron';

const ALLOWED_EXTERNAL = new Set(['example.com', 'docs.example.com']);

app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsed = new URL(navigationUrl);
    if (parsed.origin !== 'app://bundle') event.preventDefault();
  });

  contents.on('will-redirect', (event, url) => {
    if (new URL(url).origin !== 'app://bundle') event.preventDefault();
  });

  contents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === 'https:' && ALLOWED_EXTERNAL.has(parsed.hostname)) {
        void shell.openExternal(parsed.toString());
      }
    } catch {
      // malformed URL: ignore
    }
    return { action: 'deny' };
  });

  contents.on('will-attach-webview', (event) => event.preventDefault());
});
```

- Compare `URL.origin`, not string prefixes: `startsWith('https://example.com')` accepts `https://example.com.attacker.test`.
- `shell.openExternal` hands a URL to the OS; schemes such as `file:` or custom app schemes can launch other software. Allow only `https:` (and `mailto:` if needed) to listed hosts.
- Deny all new windows by default and open allowed content explicitly.

## 7. Custom protocol instead of file

```ts
import { app, protocol, net } from 'electron';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true } },
]);

app.whenReady().then(() => {
  const root = path.join(app.getAppPath(), 'dist', 'renderer');
  protocol.handle('app', (request) => {
    const url = new URL(request.url);
    const target = path.normalize(path.join(root, url.pathname));
    if (!target.startsWith(root + path.sep)) {
      return new Response('forbidden', { status: 403 });
    }
    return net.fetch(pathToFileURL(target).toString());
  });
});
```

- Always normalise and bound the requested path to the asset root, as shown; a plain join lets `..` segments escape.

## 8. Electron Fuses

Fuses are bits in the Electron binary flipped at package time. Because they change before code signing, the OS signature check protects them from later tampering. Package: `@electron/fuses` (CLI and API); in Forge use `@electron-forge/plugin-fuses`.

| Fuse option (`FuseV1Options.*`) | Default | Guidance |
|---|---|---|
| `RunAsNode` | enabled | Disable unless the app relies on `ELECTRON_RUN_AS_NODE` or `child_process.fork`; use `utilityProcess` |
| `EnableCookieEncryption` | disabled | Enable for most apps; one-way: disabling later corrupts the cookie store. On macOS the app must be signed |
| `EnableNodeOptionsEnvironmentVariable` | enabled | Disable for production; stops `NODE_OPTIONS` and `NODE_EXTRA_CA_CERTS` |
| `EnableNodeCliInspectArguments` | enabled | Disable for production; blocks `--inspect` flags and the SIGUSR1 inspector |
| `EnableEmbeddedAsarIntegrityValidation` | disabled | Enable on macOS and Windows; validates `app.asar` content |
| `OnlyLoadAppFromAsar` | disabled | Enable together with ASAR integrity so only validated code loads |
| `LoadBrowserProcessSpecificV8Snapshot` | disabled | Optional; separate snapshot for the main process (see Electron docs for the startup trade-off) |
| `GrantFileProtocolExtraPrivileges` | enabled | Disable when pages are served from a custom protocol |
| `WasmTrapHandlers` | enabled | Leave on unless a platform issue requires otherwise |

```ts
// forge.config.ts (fragment)
import { FusesPlugin } from '@electron-forge/plugin-fuses';
import { FuseV1Options, FuseVersion } from '@electron/fuses';

export default {
  packagerConfig: { asar: true },
  plugins: [
    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
      [FuseV1Options.OnlyLoadAppFromAsar]: true,
      [FuseV1Options.GrantFileProtocolExtraPrivileges]: false,
    }),
  ],
};
```

- Verify on the produced app: `npx @electron/fuses read --app /path/to/MyApp.app` (or the `.exe` on Windows).
- ASAR integrity validation needs the build tooling to embed the integrity metadata; with Forge and the packager this is configured by the plugin and packager options (check the Electron "ASAR Integrity" page).

## 9. ESM in the main process

- Supported since Electron 28. Use `.mjs` files or `"type": "module"` in the nearest `package.json`.
- The main process uses Node's ESM loader; the renderer uses Chromium's. Sandboxed preload scripts cannot use ESM imports; unsandboxed preloads can but run after page load on pages with no content, which breaks the security model. Keep preloads sandboxed and bundled to CommonJS.
- Module loading is asynchronous: only side effects of the entry point's static imports run before `ready`. Await any dynamic `import()` that must finish before `app.whenReady()`, for example code that calls `app.setPath`.
- In ESM, `__dirname` and `__filename` do not exist; use `import.meta.dirname` and `import.meta.filename` (Node 20.11 and later) or `fileURLToPath(import.meta.url)`.

## 10. Secrets and storage

- Do not embed API keys, signing credentials or tokens in renderer code, the preload, `package.json` or the ASAR; anything shipped to users is extractable.
- Vendor API keys belong on a server. The desktop app obtains a short-lived token for the signed-in user and calls the server.
- For local credentials (refresh tokens), use `safeStorage.encryptString` and `decryptString` after checking `safeStorage.isEncryptionAvailable()`, then store the ciphertext under `userData`. On Linux the available backend may be weak (check `getSelectedStorageBackend()`).
