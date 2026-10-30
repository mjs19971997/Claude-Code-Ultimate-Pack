# Native Modules, Config Plugins and Builds

Writing native code for Expo apps: development builds versus Expo Go, Continuous Native Generation and prebuild, config plugins, and local modules with the Expo Modules API in Swift and Kotlin. Verified against Expo SDK 58 (expo 58.0.21, @expo/cli 58.1.x), React Native 0.88.1 and the New Architecture (2026-10).

## Contents

1. [Expo Go versus development builds](#1-expo-go-versus-development-builds)
2. [Continuous Native Generation](#2-continuous-native-generation)
3. [Config plugins](#3-config-plugins)
4. [Local Expo module](#4-local-expo-module)
5. [Module definition components](#5-module-definition-components)
6. [Native views](#6-native-views)
7. [Native code rules](#7-native-code-rules)
8. [Checklist](#8-checklist)

## 1. Expo Go versus development builds

- Expo Go is a prebuilt app with a fixed set of native modules. It suits learning, prototypes and pure-JavaScript work.
- A development build is your own app binary that includes `expo-dev-client`. It can contain any native library, custom native code, config plugin output (URL schemes, entitlements, permissions) and your app's real name and bundle identifier. It is the recommended base for apps released to stores.
- Build one with EAS (`eas build --profile development --platform ios|android`), or locally with `npx expo run:ios` / `npx expo run:android` (needs Xcode or the Android SDK).
- A development build loads JavaScript from a dev server (`npx expo start`) or from an EAS Update channel as long as the runtime version is compatible.
- Rebuild the binary after changing: native dependencies, config plugins, `scheme`, `ios` or `android` app config keys, or the Expo SDK version. JavaScript changes reload without a rebuild.
- Some options do not work in Expo Go, for example `expo-secure-store` with `requireAuthentication` when biometrics are available (missing `NSFaceIDUsageDescription`). Test those in a development build.

Example `eas.json` development profile:

```json
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": { "simulator": true }
    }
  }
}
```

## 2. Continuous Native Generation

CNG treats `ios/` and `android/` as generated output. `npx expo prebuild` reads the app config, the installed packages and the config plugins, and writes the native projects.

- In current CLI versions `npx expo prebuild` deletes and recreates the native folders by default; `--no-clean` applies changes on top of the existing folders instead. The CLI warns about uncommitted git changes before cleaning (skipped in CI; `EXPO_NO_GIT_STATUS=1` disables the check).
- Other useful flags: `--platform ios|android`, `--no-install` (skip package and pod installation), `--skip-dependency-update react-native,react`.
- `npx expo run:ios` and `npx expo run:android` run prebuild once if the folders are missing. After changing app config or plugins, run prebuild again before the next run.
- EAS Build runs prebuild on its servers when the native folders are not committed, so a CNG project can keep them in `.gitignore`.
- Upgrading an SDK in a CNG project means upgrading dependencies, adjusting app config and re-running prebuild.
- If the native folders are committed and hand-edited, EAS Build does not run prebuild for them, so config plugin changes are not applied; do not mix both styles in one project without a clear owner for each setting.

## 3. Config plugins

A config plugin is a function that receives the Expo config and returns a modified one, using "mods" that edit generated native files at prebuild.

```js
// plugins/with-camera-usage.js
const { withInfoPlist } = require('expo/config-plugins');

module.exports = function withCameraUsage(config, props = {}) {
  const message = props.message ?? 'Allow $(PRODUCT_NAME) to use the camera.';
  return withInfoPlist(config, (c) => {
    c.modResults.NSCameraUsageDescription = message;
    return c;
  });
};
```

```json
{
  "expo": {
    "plugins": [["./plugins/with-camera-usage", { "message": "Scan receipts with the camera." }]]
  }
}
```

- Android edits use `withAndroidManifest` with helpers from `AndroidConfig.Manifest`, for example `getMainApplicationOrThrow` and `addMetaDataItemToMainApplication`.
- iOS edits use `withInfoPlist`, entitlements mods and others exported by `expo/config-plugins`; the type for typed plugins is `ConfigPlugin<Props>`.
- Make plugins idempotent: running prebuild twice must give the same result. Non-idempotent regex edits are the main reason clean prebuilds are recommended.
- Library authors expose a plugin through `app.plugin.js` at the package root; users then list the package name in `plugins`.
- Validate props early and throw an error with context; unit-test transformations with mock config objects in Jest and verify real output with an example app.
- Plugin output never contains secrets; read non-secret values from props or from `process.env` at prebuild time, and remember anything written to `Info.plist` or the manifest ships in the binary.

## 4. Local Expo module

Scaffold a module inside the app:

```bash
npx create-expo-module@latest --local
npx expo prebuild --clean   # only if ios/ and android/ do not exist yet
```

The command creates `modules/<name>/` with `android/`, `ios/`, `src/`, `index.ts` and `expo-module.config.json`. Autolinking registers the classes listed in the config file:

```json
{
  "platforms": ["apple", "android"],
  "apple": { "modules": ["DeviceInfoModule"] },
  "android": { "modules": ["expo.modules.deviceinfo.DeviceInfoModule"] }
}
```

Swift:

```swift
import ExpoModulesCore

public class DeviceInfoModule: Module {
  public func definition() -> ModuleDefinition {
    Name("DeviceInfo")

    Events("onUptimeTick")

    Constant("platform") { "ios" }

    Function("uptimeSeconds") { () -> Double in
      ProcessInfo.processInfo.systemUptime
    }

    AsyncFunction("tick") { () in
      self.sendEvent("onUptimeTick", ["seconds": ProcessInfo.processInfo.systemUptime])
    }
  }
}
```

Kotlin:

```kotlin
package expo.modules.deviceinfo

import android.os.SystemClock
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class DeviceInfoModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("DeviceInfo")

    Events("onUptimeTick")

    Constant("platform") { "android" }

    Function("uptimeSeconds") {
      SystemClock.elapsedRealtime() / 1000.0
    }

    AsyncFunction("tick") {
      sendEvent("onUptimeTick", mapOf("seconds" to SystemClock.elapsedRealtime() / 1000.0))
    }
  }
}
```

TypeScript wrapper:

```ts
// modules/device-info/src/DeviceInfoModule.ts
import { NativeModule, requireNativeModule } from 'expo';

type DeviceInfoEvents = { onUptimeTick: (event: { seconds: number }) => void };

declare class DeviceInfoModule extends NativeModule<DeviceInfoEvents> {
  platform: string;
  uptimeSeconds(): number;
  tick(): Promise<void>;
}

export default requireNativeModule<DeviceInfoModule>('DeviceInfo');
```

After adding native files or editing `expo-module.config.json`, reinstall pods (`npx pod-install`) and rebuild the development build.

## 5. Module definition components

| Component | Behavior |
|---|---|
| `Name("X")` | Module name used by `requireNativeModule('X')`; set it explicitly |
| `Constant("name") { value }` | Computed once on first access and cached; replaces the deprecated `Constants` |
| `Function("name") { args in }` | Synchronous; blocks the calling JS thread, so keep it fast. Up to 8 arguments |
| `AsyncFunction("name") { args in }` | Returns a promise; runs off the JS thread; prefer it for I/O or anything that can take time. Takes an optional `Promise` argument to resolve or reject manually |
| `Events("a", "b")` | Declares event names; send with `sendEvent(name, payload)` |
| `OnStartObserving` / `OnStopObserving` | Hooks to attach and detach native listeners when JS adds or removes event listeners |
| `Property` | Native-backed properties on the module or on shared objects |
| `OnCreate` / `OnDestroy` | Module lifecycle |
| `View(MyView.self) { ... }` | Declares a native view and its props, events and view functions |

- Arguments and return values map between JS and Swift/Kotlin types (primitives, arrays, dictionaries, `Record` types, enums, URLs). Use `Record` types for structured arguments so invalid input fails with a typed error.
- Throw typed exceptions (`Exception` subclasses with a code) rather than crashing; they reach JS as rejected promises or thrown errors.
- Modules written with this API support the New Architecture by default; no TurboModule spec or codegen step is needed.

## 6. Native views

- Declare a view with `View(SomeView.self) { Prop("name") { view, value in ... } }` in the module, and expose it to JS with `requireNativeView('ModuleName')` from `expo`.
- Events that a view sends to JS are declared inside the `View` block with `Events`, and appear as callback props.
- Views must respect the main thread: Swift views are `ExpoView` subclasses, Kotlin views extend `ExpoView`; do layout and drawing on the UI thread only.
- For native UI that already exists in Expo's own packages (SwiftUI and Jetpack Compose components in `@expo/ui`), check the current docs before writing a custom view.

## 7. Native code rules

- Validate every input that comes from JavaScript, including file paths and URLs; do not build file paths from caller strings without resolving them under an allowed directory.
- Do not log tokens or personal data in native code; release builds still write to the system log.
- Store secrets in the Keychain or Keystore via `expo-secure-store` or the platform APIs, never in `UserDefaults`, `SharedPreferences` or bundled resources.
- Offer a fallback or a clear `UnavailabilityError`-style rejection on platforms where the feature does not exist (web, simulator).
- Keep the JS API small and typed; put platform branching in native code, not in the JS wrapper.
- Test native logic with each platform's own test targets (XCTest, JUnit) and the JS wrapper in Jest with the native module mocked.

## 8. Checklist

- [ ] Native libraries installed with `npx expo install`; `npx expo-doctor` is clean.
- [ ] A development build exists for the current SDK and includes all plugins.
- [ ] Config plugins are idempotent and contain no secrets.
- [ ] `runtimeVersion` changes whenever native code or plugin output changes (see the EAS reference).
- [ ] Module registered in `expo-module.config.json` for each platform it supports.
- [ ] Long-running work uses `AsyncFunction`; no blocking calls in `Function`.
- [ ] Inputs validated; errors surface as typed exceptions.
