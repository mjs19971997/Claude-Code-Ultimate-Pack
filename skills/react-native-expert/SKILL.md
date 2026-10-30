---
name: react-native-expert
description: >-
  Builds, secures and ships React Native apps with Expo: Expo Router navigation, the New Architecture, Hermes, Expo Modules API native code, config plugins and prebuild, EAS Build, Submit and Update, secure token storage, OAuth with PKCE, and list and animation performance. Use when working with app.json or app.config.ts, eas.json, expo-router layouts, development builds, expo-secure-store, expo-auth-session, Reanimated, FlashList, expo-image, jest-expo or Maestro flows. Not for native Swift apps (use swift-expert), native Kotlin apps (use android-expert), Flutter (use flutter-expert), web React (use senior-react-19-engineer) or OAuth server design (use authentication-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# React Native Expert

This skill covers cross-platform mobile apps written in TypeScript with React Native and the Expo toolchain: project setup, file-based routing with Expo Router, native modules and config plugins, build and release pipelines on EAS, performance work on the JavaScript and UI threads, and the security rules that apply to code shipped inside an app binary. It assumes the New Architecture, which is the only architecture in current releases. Platform-native apps, Flutter, web React and OAuth server design belong to other skills.

> Verified against React Native 0.88.1, Expo SDK 58 (expo 58.0.21, which pins React 19.3.0 and React Native 0.88.1), Expo Router 58.0.x, react-native-reanimated 4.7.x with react-native-worklets 0.13.x, @shopify/flash-list 2.3.x, expo-image 58.0.x, expo-secure-store 58.0.x, expo-auth-session 58.0.x, eas-cli 27.2.x, jest-expo 58.0.x and @testing-library/react-native 14.1.x (2026-10).

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

- Covered: Expo SDK projects (`app.json`, `app.config.ts`, `eas.json`), Expo Router routes and layouts, typed routes, deep links and universal links, development builds versus Expo Go, Continuous Native Generation (`npx expo prebuild`), config plugins, local Expo modules in Swift and Kotlin, EAS Build, EAS Submit, EAS Update (runtime versions, channels, rollouts), environment variables, `expo-secure-store`, `expo-auth-session` with PKCE, FlashList, Reanimated, `expo-image`, Jest with React Native Testing Library, and Maestro flows.
- Not covered: native iOS apps in Swift or SwiftUI (swift-expert), native Android apps in Kotlin or Compose (android-expert), Flutter and Dart (flutter-expert), React for the web (senior-react-19-engineer), OAuth or OpenID Connect server design and token issuance (authentication-expert), general end-to-end test strategy (e2e-testing-expert), API design for the backend the app calls (rest-api-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | `expo@58.0.21` is the npm `latest`; its `bundledNativeModules.json` pins `react@19.3.0`, `react-native@0.88.1`, `react-native-reanimated@4.7.1`, `react-native-worklets@0.13.0`, `@shopify/flash-list@2.3.2`. Install native libraries with `npx expo install <pkg>` so versions match the SDK |
| New Architecture | React Native 0.82 was the first release that runs entirely on it, and it cannot be disabled; Expo SDK 55 and later (RN 0.83+) always enable it. `newArchEnabled: false` works only on SDK 54 and earlier. Fabric renders, TurboModules and the Expo Modules API sit on JSI |
| Hermes | Default JavaScript engine in Expo apps. Hermes bytecode can differ between Hermes versions, so an update built against a different React Native version needs a new `runtimeVersion` |
| Expo Router | Routes are files under `src/app`; `_layout.tsx` defines navigators; `(group)` folders do not appear in URLs; `[id].tsx` is a dynamic segment; `+not-found.tsx` and `+native-intent.tsx` are special files. Typed routes: `experiments.typedRoutes: true` |
| Protected routes | `<Stack.Protected guard={isLoggedIn}>` hides screens from client-side navigation only; it is not authorization, the server must check every request |
| Development build | A project-specific Expo Go with `expo-dev-client`; needed for custom native code, config plugins and most production-like testing. Expo Go cannot load arbitrary native modules |
| Prebuild (CNG) | `npx expo prebuild` generates `ios` and `android` from app config and config plugins. In current CLI versions it recreates the folders by default and `--no-clean` applies changes on top of existing folders. Treat generated folders as build output |
| Expo Modules API | `Module` subclass with a `definition()` DSL (`Name`, `Function`, `AsyncFunction`, `Events`, `View`, `Constant`) in Swift and Kotlin; scaffold with `npx create-expo-module@latest --local`; JS side uses `requireNativeModule` from `expo` |
| Config plugins | Functions of type `ConfigPlugin` from `expo/config-plugins` (`withInfoPlist`, `withAndroidManifest`, ...) run during prebuild; entry point `app.plugin.js` |
| EAS Build | `eas build --profile <name> --platform <ios\|android\|all>`; profiles in `eas.json`; `cli.appVersionSource: "remote"` plus `autoIncrement: true` manages `buildNumber` and `versionCode` |
| EAS Submit | `eas submit --platform ios\|android --profile production`, or `eas build --auto-submit`; non-interactive runs need `EXPO_TOKEN` and, on iOS, `ascAppId` in the submit profile |
| EAS Update | `eas update --channel <name> --message "..." --environment <env>`; `--environment` is required on SDK 55 and later; builds read updates from the channel set in their build profile |
| runtimeVersion | A string, or a policy object: `appVersion`, `nativeVersion` or `fingerprint`. Set per platform under `ios` or `android` to override the top-level value |
| Rollouts | `eas update --rollout-percentage=10`, then `eas update:edit`; revert with `eas update:revert-update-rollout`; roll back a published update with the rollback commands in the EAS docs |
| Env vars | `process.env.EXPO_PUBLIC_*` is inlined at bundle time with dot notation only (`process.env['X']` and destructuring are not inlined) and is readable by anyone with the binary. EAS "secret" visibility only hides a value from EAS surfaces, not from the bundle |
| Secure storage | `expo-secure-store`: `setItemAsync`, `getItemAsync`, `deleteItemAsync`; Keychain on iOS, Keystore-encrypted SharedPreferences on Android; keys allow alphanumerics, `.`, `-`, `_`; iOS items can survive uninstall |
| OAuth | `expo-auth-session`: `useAutoDiscovery`, `useAuthRequest`, `exchangeCodeAsync`; `usePKCE` defaults to `true`; `state` is generated and checked; a mobile app is a public client and holds no client secret |
| Reanimated | 4.x requires the New Architecture and the separate `react-native-worklets` package; `babel-preset-expo` configures the Babel plugin; `runOnJS` still exists, `scheduleOnRN(fn, ...args)` is available in worklets 0.13 |
| FlashList | v2 is New Architecture only and needs no `estimatedItemSize`; set `keyExtractor` and `getItemType` for mixed rows |
| expo-image | `cachePolicy`: `none`, `disk`, `memory`, `memory-disk`; `recyclingKey` for recycled list cells; `placeholder` accepts a blurhash or thumbhash; `transition` |
| Testing | `jest-expo` preset; RNTL 14 makes `render` and `userEvent` async (`await render(...)`) and needs the `test-renderer` dev dependency; Maestro flows live in `.maestro/` and can run on EAS Workflows |

## 3. Workflow

1. Read `package.json`, `app.json` or `app.config.ts`, `eas.json` and the router folder. Note the Expo SDK, React Native version, and whether `ios` and `android` folders are committed or generated.
2. Decide the runtime: Expo Go is enough for pure-JS prototypes; any custom native module, config plugin or non-SDK native library needs a development build.
3. Run `npx expo install --check` and `npx expo-doctor` before changing dependencies, and fix mismatches the tools report instead of pinning versions by hand.
4. Make the change in JavaScript or TypeScript first. Reach for native code only when no maintained library or SDK module covers the need.
5. Run the project's checks: `npx tsc --noEmit`, the linter, `npx jest`, and a development build on a simulator or device for anything touching native code, permissions or deep links.
6. For release work, build a preview profile, test it, publish an update to a staging channel, then promote. State the `runtimeVersion` policy and channel names used.
7. Report what was run, which platforms were verified, and which steps (store review, credentials, device tests) remain for the user.

## 4. Decision Rules

- If the app needs only SDK modules and pure JavaScript, use Expo Go while prototyping; if it adds a native library, a config plugin or custom native code, switch to a development build because Expo Go ships a fixed set of native modules.
- If the project keeps `ios` and `android` out of git, use CNG and config plugins; if native folders are hand-edited and committed, say so and avoid `prebuild` without `--no-clean`, since a clean prebuild discards manual edits.
- If a library has no config plugin, write a small one with `withInfoPlist` or `withAndroidManifest` instead of editing generated folders.
- If code must run on every frame (gestures, scroll-linked effects), put it in a Reanimated worklet; if it only runs on state changes, plain React state is simpler.
- If a list has more than a few dozen rows or mixed row types, use FlashList v2 with `getItemType`; keep `FlatList` for short lists and where virtualization behavior must match core exactly.
- If an update changes only JavaScript and assets, ship it with EAS Update; if it adds or upgrades native code or the React Native version, build a new binary and change the `runtimeVersion`.
- If the team often forgets to bump versions, choose `runtimeVersion` policy `fingerprint`; if every store release should be its own runtime, `appVersion` or `nativeVersion` fits and needs a disciplined version bump.
- If a value is a credential, signing key or API secret, keep it on a server and expose a narrow endpoint; `EXPO_PUBLIC_` values are for public configuration such as a base URL or a publishable key.
- If a user session token must persist, store it in `expo-secure-store`; use AsyncStorage only for non-sensitive preferences and caches.
- If an OAuth provider offers both implicit and authorization-code flows, use authorization code with PKCE in the system browser, never an embedded WebView.
- If a deep link carries identifiers or tokens, treat the URL as untrusted input and validate it on the server before acting on it.

## 5. Coding Standards

- TypeScript with `strict: true`; route params read with `useLocalSearchParams<{ id: string }>()` and validated before use, because params are strings from outside the app.
- Typed navigation: pass typed `href` values (`{ pathname: '/user/[id]', params: { id } }`); typed routes do not support relative paths such as `./about`.
- Function components and hooks only; one component per file; no component definitions inside other components.
- Keep non-route files out of `src/app`; every file there is treated as a route. Components, hooks and services live in sibling folders.
- Styles through `StyleSheet.create` or the project's styling library; no inline style objects in list row renderers.
- Platform code: prefer `Platform.select` and `.ios.tsx` / `.android.tsx` file suffixes over scattered `Platform.OS` checks.
- Async calls to native modules are wrapped in `try/catch`; native rejections (cancelled biometric prompt, denied permission) are normal outcomes.
- Do not read `process.env` with bracket access or destructuring for `EXPO_PUBLIC_` variables; use `process.env.EXPO_PUBLIC_NAME` so Metro can inline it.
- Config in `app.config.ts` is typed with `ExpoConfig` from `expo/config` and contains no secrets.

## 6. Project Structure

```text
my-app/
├── src/
│   ├── app/                     # routes only
│   │   ├── _layout.tsx          # root layout, providers, splash handling
│   │   ├── +not-found.tsx
│   │   ├── +native-intent.tsx   # optional: rewrite incoming native links
│   │   ├── (auth)/sign-in.tsx
│   │   └── (app)/
│   │       ├── _layout.tsx      # tabs or stack for signed-in users
│   │       ├── index.tsx
│   │       └── orders/[id].tsx
│   ├── components/
│   ├── hooks/
│   ├── services/                # api client, secure token store
│   └── lib/
├── modules/                     # local Expo modules (create-expo-module --local)
│   └── device-info/{android,ios,src,expo-module.config.json}
├── plugins/                     # local config plugins
├── .maestro/                    # E2E flows
├── app.config.ts
├── eas.json
├── .env.example                 # names only; real .env files are gitignored
└── package.json
```

`ios/` and `android/` are generated by prebuild; add them to `.gitignore` when the project uses CNG.

## 7. Design Patterns

- **Auth gate with protected routes**: a root layout renders `Stack.Protected` groups keyed on session state; cheap UX gating, with the server still authorizing each call. Cost: session state must load before first render, so keep the splash screen visible until it does.
- **Thin service layer**: screens call `services/api.ts`, which attaches the token from secure storage and handles 401 refresh once. Keeps screens free of transport code.
- **Local Expo module**: platform code in `modules/<name>` with one JS wrapper that exposes a typed API. Cost: a development build is required and both platforms need an implementation or a safe fallback.
- **Config plugin per native requirement**: one plugin per concern (URL scheme, entitlement, manifest flag) so prebuild stays reproducible. Cost: plugins must be idempotent.
- **Runtime-version channels**: `production` and `preview` channels with builds tied to runtime versions; promote an update by republishing to the next channel. Cost: more builds when native code changes.
- **Feature flags from the server**: toggle risky features without a store release; flags are not secrets and must be safe if tampered with on the client.
- More router patterns: [references/expo-router.md](references/expo-router.md).

## 8. Best Practices

- Pin the Expo SDK and upgrade one SDK at a time, following the release notes; run `npx expo install --fix` afterwards and rebuild native binaries.
- Create a development build early and keep it current; many bugs appear only with real native configuration.
- Keep `app.config.ts` deterministic; read non-secret variant values from `process.env` and keep per-environment values in EAS environment variables.
- Use `expo-image` instead of the core `Image` for remote images to get disk caching, placeholders and transitions.
- Handle permissions at the point of use with a clear rationale string; set the usage description keys through the library's config plugin.
- Log with a small wrapper that drops sensitive fields; ship crash reporting that uploads source maps for the Hermes bundle.
- Test on a low-end Android device and an older iPhone; simulators hide memory and startup problems.
- Enable the React Compiler only after `react-compiler-healthcheck` passes; on SDK 54 and later Babel is configured automatically when `experiments.reactCompiler` is `true`.

## 9. Performance

- Measure first: React DevTools profiler for re-renders, the Hermes profiler and `npx expo start` dev tools for JS time, Xcode Instruments and Android Studio profiler for native time, and release builds for numbers (development mode is much slower).
- Startup: keep the root layout light, load fonts and assets while the splash screen is shown, defer non-critical SDK initialisation, and avoid large synchronous work in module scope.
- Lists: FlashList v2 with stable `keyExtractor`, `getItemType` for different row layouts, memoised row components, and no heavy work in `renderItem`. Do not nest vertical lists inside vertical `ScrollView`s.
- Images: `expo-image` with a sized container, `contentFit`, `placeholder` (blurhash or thumbhash), `cachePolicy="memory-disk"` for repeated images, and `recyclingKey` in recycled cells. Serve images at display size from the server.
- Animation: drive transforms and opacity from shared values in Reanimated worklets so they run on the UI thread; call back to JS with `scheduleOnRN` or `runOnJS` only on gesture end or state change.
- Memoisation: with the React Compiler enabled, manual `useMemo` and `useCallback` are rarely needed; without it, memoise row components and callbacks passed to lists.
- Avoid JS-thread work during interactions: no JSON parsing of large payloads in a press handler, no synchronous `SecureStore.getItem` in render, no chained `setState` calls per frame.
- Bundle size: audit with `npx expo export` output and a bundle visualizer; prefer SDK modules over large utility libraries; lazy load rarely used screens.
- Hermes bytecode makes startup faster; do not disable it to debug unless a tool requires it.

## 10. Security

- Everything in the bundle is public. `EXPO_PUBLIC_*` variables, `extra` in app config, strings in JavaScript and bundled JSON can all be read from the binary or an OTA update. Put secrets (API keys with write power, signing keys, database credentials, client secrets) on a server; the app calls the server.
- Tokens go in `expo-secure-store`, not AsyncStorage or MMKV without encryption. Use `keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY` (or `WHEN_UNLOCKED_THIS_DEVICE_ONLY`) so credentials are not migrated to other devices. iOS Keychain items can persist after uninstall, so clear them on first launch after a fresh install if that matters.
- OAuth and OpenID Connect: system browser via `expo-auth-session` with PKCE (S256) and the generated `state`; register an exact redirect URI (custom scheme or verified HTTPS link); never embed a client secret in the app; exchange the code with `exchangeCodeAsync` passing `extraParams: { code_verifier }`.
- Deep links are untrusted input: a custom scheme can be claimed by any installed app, so do not pass access tokens in links and prefer verified universal links (iOS) and Android App Links (`autoVerify: true` plus `assetlinks.json`) for anything sensitive. Validate route params; use `+native-intent.tsx` to reject or rewrite unexpected URLs and never let a link choose an arbitrary internal path, file path or WebView URL.
- Transport: HTTPS only; keep App Transport Security and Android cleartext restrictions at their defaults; never disable certificate validation in production or development builds that talk to real data.
- Client-side route guards are not authorization. Every server endpoint checks the caller and filters by tenant or owner on reads and writes.
- EAS Update is code distribution: protect the Expo account with 2FA, restrict who can publish, use `EXPO_TOKEN` only as a CI secret, and consider code signing for updates (check the current docs). Review the Android `allowBackup` and Auto Backup behaviour for sensitive data.
- WebViews: load only trusted origins, restrict `originWhitelist`, and avoid `javaScriptEnabled` with untrusted content.
- Biometric gating: `requireAuthentication: true` in SecureStore invalidates the value if biometrics change; handle the rejection and re-authenticate.
- Set the native usage description strings and privacy manifest entries through config plugins; review third-party SDK data collection before release.

## 11. Testing

- Unit and component tests: `jest-expo` preset, `@testing-library/react-native` 14 (async `render`, `userEvent.setup()`), query by role, label or text rather than test IDs when possible. Commands: `npx jest`, `npx jest --watch`, `npx jest --coverage`.
- Mock native modules at the boundary: wrap `expo-secure-store` and network calls behind services and fake those, rather than mocking deep internals.
- Navigation tests: `await renderRouter(...)` from `expo-router/testing-library` renders the router against an in-memory file structure (check the current docs for its options).
- Test failure paths: network errors, 401 with refresh failure, cancelled OAuth prompt, denied permission, expired or malformed deep link parameters.
- Type checks in CI: `npx tsc --noEmit` and `npx expo-doctor`.
- End-to-end: Maestro YAML flows in `.maestro/` (`appId`, `launchApp`, `assertVisible`, `tapOn`) run locally with the Maestro CLI against a simulator or emulator, or on EAS Workflows. Use a build that matches production configuration, not Expo Go.
- Native modules: test the pure logic in unit tests on each platform's own test target, and cover the JS wrapper with a mocked native module.

## 12. Review Checklist

- [ ] Versions and APIs match the "Verified against" line; native packages installed with `npx expo install`.
- [ ] No secrets in `EXPO_PUBLIC_*`, `app.config.ts`, `extra`, source or committed `.env` files.
- [ ] Tokens stored with `expo-secure-store` and a restrictive `keychainAccessible` value.
- [ ] OAuth uses authorization code with PKCE in the system browser; redirect URIs are exact.
- [ ] Deep link parameters validated; no tokens in links; universal or app links verified for sensitive routes.
- [ ] Server enforces authentication and owner or tenant checks; client route guards are only UX.
- [ ] `runtimeVersion` changes with any native change; update channel matches the build profile.
- [ ] `eas update` includes `--environment` and does not publish to production without a preview check.
- [ ] Lists use FlashList or a justified FlatList with stable keys; images use `expo-image`.
- [ ] Animations on the UI thread; no heavy synchronous work on press or render.
- [ ] Error and permission-denied paths handled and tested.
- [ ] Tested on a physical device or a development build for native-facing changes.

## 13. Production Notes

- Release flow: `eas build --profile production`, `eas submit --profile production` (or `--auto-submit`), staged store rollout, then OTA updates for JavaScript fixes. Keep store builds and OTA channels paired by profile.
- Roll out updates gradually with `--rollout-percentage` and watch crash-free rate before raising it; a rollout that targets the same branch, platform and runtime version blocks a second publish unless `--force-end-active-rollout` is passed.
- Keep a rollback path: republish the previous good update or roll back to the embedded bundle. Updates are tied to a runtime version, so a bad native change needs a new binary.
- Store policies still apply to OTA updates; check the current Apple and Google guidance before shipping large behavior changes over the air.
- Upgrade cadence: new Expo SDKs ship several times a year (SDK 55 in 2026-02, SDK 58 in 2026-09 per the npm release dates); plan upgrades, read the changelog for breaking changes, and rebuild binaries after each upgrade. Check the current docs for which SDKs are still supported by Expo Go and EAS.
- Observability: crash reporting with source maps for Hermes bytecode, performance traces for cold start and key screens, and release health per update ID and runtime version.
- Environment variables on EAS: define per-environment values with `eas env:set` or the dashboard and pass `--environment` to builds and updates; plain-text and sensitive variables can be pulled for local use, secret ones cannot.
- Android: keep signing credentials under EAS credentials management or an offline backup; check the Play Console documentation for key recovery options before relying on them.

## 14. Examples

A token store backed by Keychain and Keystore, with keys that match the allowed character set.

```ts
// src/services/token-store.ts
import * as SecureStore from 'expo-secure-store';

const REFRESH_KEY = 'auth.refresh-token';

export async function saveRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_KEY, token, {
    keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
  });
}

export function readRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_KEY);
}

export function clearRefreshToken(): Promise<void> {
  return SecureStore.deleteItemAsync(REFRESH_KEY);
}
```

OAuth authorization code flow with PKCE as a public client; the issuer URL and client ID are public configuration and there is no client secret.

```tsx
// src/app/(auth)/sign-in.tsx
import { Button } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import {
  exchangeCodeAsync,
  makeRedirectUri,
  useAuthRequest,
  useAutoDiscovery,
} from 'expo-auth-session';
import { saveRefreshToken } from '@/services/token-store';

WebBrowser.maybeCompleteAuthSession();

export default function SignIn() {
  const discovery = useAutoDiscovery(process.env.EXPO_PUBLIC_OIDC_ISSUER!);
  const redirectUri = makeRedirectUri({ scheme: 'myapp', path: 'auth/callback' });

  // usePKCE defaults to true; state is generated and verified by the library.
  const [request, , promptAsync] = useAuthRequest(
    {
      clientId: process.env.EXPO_PUBLIC_OIDC_CLIENT_ID!,
      redirectUri,
      scopes: ['openid', 'profile', 'offline_access'],
    },
    discovery,
  );

  async function onPress() {
    const result = await promptAsync();
    if (result.type !== 'success' || !request?.codeVerifier || !discovery) return;
    const tokens = await exchangeCodeAsync(
      {
        clientId: process.env.EXPO_PUBLIC_OIDC_CLIENT_ID!,
        code: result.params.code,
        redirectUri,
        extraParams: { code_verifier: request.codeVerifier },
      },
      discovery,
    );
    if (tokens.refreshToken) await saveRefreshToken(tokens.refreshToken);
  }

  return <Button title="Sign in" disabled={!request} onPress={onPress} />;
}
```

A root layout that gates routes on session state, with the server still enforcing access.

```tsx
// src/app/_layout.tsx
import { Stack } from 'expo-router';
import { useSession } from '@/hooks/use-session';

export default function RootLayout() {
  const { isSignedIn } = useSession();
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={!isSignedIn}>
        <Stack.Screen name="(auth)" />
      </Stack.Protected>
      <Stack.Protected guard={isSignedIn}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
    </Stack>
  );
}
```

## 15. Common Mistakes

- **Putting an API secret in `EXPO_PUBLIC_*` or `extra`**: it is inlined in the bundle and visible to anyone. Move the call behind a server endpoint.
- **Treating EAS "secret" visibility as protection for bundle values**: it hides the value in EAS tools only; if the value is used by app code it is still shipped.
- **Reading `process.env['EXPO_PUBLIC_X']` or destructuring `process.env`**: Metro does not inline it and the value is `undefined` at run time. Use dot notation.
- **Storing refresh tokens in AsyncStorage**: plain-text storage readable on rooted devices and in backups. Use `expo-secure-store`.
- **Embedding an OAuth client secret in the app**: a mobile app cannot keep it private. Use a public client with PKCE, or a backend-for-frontend.
- **Sending tokens through a custom-scheme deep link**: another app can register the same scheme. Use verified links and server-side code exchange.
- **Assuming `Stack.Protected` secures data**: it only blocks client navigation. Authorize on the server.
- **Publishing an update that needs new native code**: running builds crash or roll back. Change `runtimeVersion` and ship a new binary first.
- **Running `eas update` without `--environment` on SDK 55+**: the flag is required, so non-interactive runs fail and interactive runs prompt. Pass the environment explicitly so the right variables are inlined.
- **Editing generated `ios` or `android` folders under CNG**: the next prebuild discards the change. Write a config plugin.
- **Installing native libraries with `npm install` at arbitrary versions**: mismatches with the SDK cause build or runtime errors. Use `npx expo install`.
- **Putting components or helpers in `src/app`**: they are registered as routes and can break typed routes. Keep them outside.
- **Using `FlatList` with inline `renderItem` closures for large lists**: frequent re-renders and dropped frames. Use FlashList v2, memoised rows and stable keys.
- **Starting animations with `setState` on every frame**: the JS thread saturates. Use shared values and `useAnimatedStyle`.
- **Testing only in Expo Go**: native config such as deep links, entitlements and push setup differs. Verify in a development or preview build.
- **Using legacy-architecture flags or libraries on SDK 55+**: `newArchEnabled: false` no longer disables anything. Replace libraries that do not support the New Architecture.

## 16. References

- [references/expo-router.md](references/expo-router.md): file conventions, layouts, typed routes, params, protected routes, deep links, universal links and App Links, `+native-intent`, and route testing.
- [references/native-modules.md](references/native-modules.md): Expo Modules API in Swift and Kotlin, local modules, views and events, config plugins, prebuild and CNG, development builds versus Expo Go.
- [references/eas-build-update.md](references/eas-build-update.md): `eas.json` profiles, versioning, EAS Submit, EAS Update channels, runtime version policies, rollouts, rollbacks and environment variables.
- [references/security-and-testing.md](references/security-and-testing.md): secure storage options, OAuth with PKCE details, deep link hardening, Jest and React Native Testing Library setup, Maestro flows.
- Official docs: https://docs.expo.dev/ , https://docs.expo.dev/router/introduction/ , https://docs.expo.dev/eas-update/introduction/ , https://docs.expo.dev/modules/overview/ , https://reactnative.dev/docs/getting-started , https://reactnative.dev/architecture/landing-page , https://docs.swmansion.com/react-native-reanimated/ , https://shopify.github.io/flash-list/ , https://docs.maestro.dev/
