# Security and Testing

Protecting data and credentials in an Expo app, hardening OAuth and deep links, and testing with Jest, React Native Testing Library and Maestro. Verified against expo-secure-store 58.0.x, expo-auth-session 58.0.x, jest-expo 58.0.x, @testing-library/react-native 14.1.x and Maestro as used in Expo's EAS Workflows guide (2026-10).

## Contents

1. [What ships in the app](#1-what-ships-in-the-app)
2. [Storage options](#2-storage-options)
3. [Token handling](#3-token-handling)
4. [OAuth with PKCE](#4-oauth-with-pkce)
5. [Deep link hardening](#5-deep-link-hardening)
6. [Jest and React Native Testing Library](#6-jest-and-react-native-testing-library)
7. [Mocking native modules](#7-mocking-native-modules)
8. [Maestro end-to-end flows](#8-maestro-end-to-end-flows)
9. [Security review questions](#9-security-review-questions)

## 1. What ships in the app

Anyone who installs the app can unpack the binary or the update bundle and read the JavaScript and bundled assets. Treat the following as public:

- `EXPO_PUBLIC_*` variables, which Metro inlines as literal strings (dot notation only; `process.env['EXPO_PUBLIC_X']` is not inlined).
- The `extra` field of the app config, reachable through `expo-constants`.
- Strings in source files, bundled JSON, and values copied into `Info.plist` or `AndroidManifest.xml` by config plugins.
- Anything fetched from EAS Update, because updates are downloaded by every installed client.

Secrets (database credentials, signing keys, third-party API keys with write or billing power, OAuth client secrets) belong on a server. The app talks to a backend endpoint that authenticates the user and performs the privileged call. Publishable keys that a vendor designs for client use (for example a map tile key restricted by bundle identifier) can be public configuration, but restrict them in the vendor console.

EAS "secret" variables hide values from the EAS website and CLI; they do not stop the value from being embedded when app code reads it.

## 2. Storage options

| Storage | Encrypted at rest by the library | Use for |
|---|---|---|
| `expo-secure-store` | Yes: Keychain (iOS), Keystore-encrypted SharedPreferences (Android) | Refresh tokens, session identifiers, small secrets |
| AsyncStorage | No | Non-sensitive preferences, UI state, cached public data |
| SQLite / MMKV / files | No unless you add encryption | Larger data; encrypt sensitive fields with a key kept in SecureStore |

SecureStore facts that affect design:

- API: `setItemAsync`, `getItemAsync`, `deleteItemAsync` (async) and `setItem` / `getItem` (synchronous, blocks the JS thread). Keys may contain alphanumerics, `.`, `-` and `_`.
- Large values can be rejected by the platform (historically some iOS releases refused values above about 2048 bytes); store a key or token, not a document.
- iOS: `keychainAccessible` sets when the item is readable (`WHEN_UNLOCKED` is the default; `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY` suits tokens read by background tasks; `*_THIS_DEVICE_ONLY` values are not migrated to other devices). `ALWAYS` and `ALWAYS_THIS_DEVICE_ONLY` are deprecated.
- iOS Keychain data can survive uninstall and reinstall with the same bundle ID. Android SecureStore data does not survive uninstall.
- `requireAuthentication: true` asks for biometrics or the device credential on access; the value becomes unreadable if the enrolled biometrics change. Handle rejections (cancelled prompt, lockout) as flow outcomes. Test on a real device; simulators do not enforce it the same way.
- Android Auto Backup must exclude the SecureStore preferences or restores produce undecryptable entries; the config plugin handles this by default (`configureAndroidBackup`).
- Apple export compliance: `ios.config.usesNonExemptEncryption: false` answers the encryption prompt when only exempt encryption is used.

## 3. Token handling

```ts
// src/services/session.ts
import * as SecureStore from 'expo-secure-store';

const ACCESS = 'session.access';
const REFRESH = 'session.refresh';
const OPTIONS = { keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY } as const;

export async function storeSession(access: string, refresh: string) {
  await SecureStore.setItemAsync(ACCESS, access, OPTIONS);
  await SecureStore.setItemAsync(REFRESH, refresh, OPTIONS);
}

export async function clearSession() {
  await SecureStore.deleteItemAsync(ACCESS);
  await SecureStore.deleteItemAsync(REFRESH);
}
```

- Keep access tokens short-lived and hold them in memory where possible; persist only the refresh token.
- Rotate refresh tokens on use if the server supports it, and clear the stored pair on any refresh failure.
- Sign-out deletes local tokens and revokes them on the server (`revokeAsync` from `expo-auth-session` when the provider exposes a revocation endpoint).
- Do not log tokens, put them in URLs, route params, analytics events or crash breadcrumbs.
- Redact `Authorization` headers in network debugging tools and in error reporting.
- The server authorizes every request and applies owner or tenant filters to reads and writes; a hidden screen is not access control.

## 4. OAuth with PKCE

A mobile app is a public client: it cannot keep a client secret. Use the authorization code flow with PKCE in the system browser.

- `useAuthRequest` creates the request; `usePKCE` defaults to `true` and the code challenge method to `S256`; `state` is generated and compared on return, and a mismatch yields an error result.
- `request.codeVerifier` must be sent to the token endpoint through `extraParams: { code_verifier }` in `exchangeCodeAsync`.
- Call `WebBrowser.maybeCompleteAuthSession()` at module scope of the screen that handles the redirect (required for the web popup flow and harmless on native).
- Build the redirect with `makeRedirectUri({ scheme, path })`. Register that exact URI with the identity provider; do not use wildcard redirect URIs.
- Prefer a verified HTTPS redirect (universal link or Android App Link) when the provider supports it, because other apps can claim a custom scheme.
- Request the minimum scopes; add `offline_access` only if the flow needs refresh tokens.
- Do not use an embedded WebView for sign-in; it hides the URL bar, breaks single sign-on and trains users to type passwords into untrusted UI.
- Do not use the implicit flow (`responseType: token`); tokens in URL fragments are exposed to other apps and logs.
- If the provider requires a client secret, run the token exchange on your backend and have the app send only the authorization code and PKCE verifier to it.

OAuth server behavior (token lifetimes, rotation, scopes, consent) is covered by the authentication-expert skill.

## 5. Deep link hardening

- A custom URL scheme such as `myapp://` is not exclusive to your app. Never carry tokens, one-time codes with long lifetimes or other credentials in these links.
- Prefer iOS Universal Links (`associatedDomains`, `apple-app-site-association`) and Android App Links (`autoVerify: true`, `assetlinks.json`) for links that trigger sensitive actions. List only the paths that should open the app.
- Handle every route as if its params were attacker-controlled: parse IDs to the expected type, check them against the signed-in user's data on the server, and show an error screen for anything malformed.
- Actions with side effects (payments, deletions, role changes) need an in-app confirmation step; a link alone must not complete them.
- Use `+native-intent.tsx` to allow-list incoming paths and map unknown ones to a safe route; do not forward link-provided URLs to `WebView`, `Linking.openURL` or file APIs without validation.
- When a link targets a protected route and the user is signed out, store only the intended path (not credentials), send the user to sign-in, then navigate after authentication.
- Test with `npx uri-scheme open <url> --ios|--android` using hostile inputs: empty params, very long strings, unexpected types, path traversal sequences, and URLs for routes that should not be reachable.

## 6. Jest and React Native Testing Library

Install and configure:

```bash
npx expo install jest-expo jest @types/jest --dev
npm install --save-dev @testing-library/react-native test-renderer
```

```json
{
  "scripts": { "test": "jest" },
  "jest": { "preset": "jest-expo" }
}
```

- `jest-expo` mocks the native part of the Expo SDK and sets up Babel and module resolution for Expo projects. Add `"jest"` to `compilerOptions.types` in `tsconfig.json`.
- RNTL 14 drops React 18, requires `test-renderer` as a peer dependency, and makes `render`, `fireEvent` and `userEvent` async. Always `await render(...)`.

```tsx
// src/components/__tests__/sign-in-form.test.tsx
import { render, screen, userEvent } from '@testing-library/react-native';
import { SignInForm } from '../sign-in-form';

test('submits the entered email', async () => {
  const onSubmit = jest.fn();
  const user = userEvent.setup();
  await render(<SignInForm onSubmit={onSubmit} />);

  await user.type(screen.getByLabelText('Email'), 'ada@example.com');
  await user.press(screen.getByRole('button', { name: 'Continue' }));

  expect(onSubmit).toHaveBeenCalledWith({ email: 'ada@example.com' });
});

test('shows an error for an invalid email', async () => {
  const user = userEvent.setup();
  await render(<SignInForm onSubmit={jest.fn()} />);

  await user.type(screen.getByLabelText('Email'), 'not-an-email');
  await user.press(screen.getByRole('button', { name: 'Continue' }));

  expect(await screen.findByText('Enter a valid email')).toBeOnTheScreen();
});
```

- Query by role, label or visible text so tests follow what users and screen readers see; use `testID` only when nothing else is stable.
- Use `findBy*` and `waitFor` for asynchronous UI instead of fixed delays.
- Reset mocks between tests (`jest.resetAllMocks()` in `afterEach` or `resetMocks` in config).
- Test hooks and services as plain functions where possible; keep screens thin.
- Run `npx jest --coverage` in CI together with `npx tsc --noEmit`.

## 7. Mocking native modules

Wrap storage and network access behind a service and fake that service in component tests. When testing the service itself, mock the native module with an in-memory implementation:

```ts
// src/services/__tests__/session.test.ts
jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 'AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY',
    setItemAsync: jest.fn(async (k: string, v: string) => void store.set(k, v)),
    getItemAsync: jest.fn(async (k: string) => store.get(k) ?? null),
    deleteItemAsync: jest.fn(async (k: string) => void store.delete(k)),
  };
});

import * as SecureStore from 'expo-secure-store';
import { clearSession, storeSession } from '../session';

test('stores and clears both tokens', async () => {
  await storeSession('a1', 'r1');
  expect(await SecureStore.getItemAsync('session.refresh')).toBe('r1');

  await clearSession();
  expect(await SecureStore.getItemAsync('session.refresh')).toBeNull();
});
```

- Cover failure paths: a rejected `getItemAsync` (cancelled biometric prompt), a refresh call that returns 401, and a storage write that throws.
- For navigation, use `renderRouter` from `expo-router/testing-library` (see the Expo Router reference).
- Reanimated provides Jest setup helpers; check the Reanimated testing docs for the setup that matches the installed version rather than copying older snippets.

## 8. Maestro end-to-end flows

Maestro drives the installed app through YAML flows. Keep them in `.maestro/` next to `eas.json`.

```yaml
# .maestro/sign-in.yml
appId: com.example.myapp
---
- launchApp:
    clearState: true
- tapOn: 'Sign in'
- assertVisible: 'Welcome back'
```

- Run locally after installing the Maestro CLI: `maestro test .maestro/sign-in.yml` against a booted simulator or emulator with a development or preview build installed.
- Run in CI with EAS Workflows: a build job with an `e2e-test` profile (`withoutCredentials: true`, iOS `simulator: true`, Android `buildType: "apk"`), then a `maestro` job that takes the build ID and a `flow_path` list.
- Use text and accessibility labels that users see; add `testID` props for elements without stable text and select them with `id`.
- Never put real credentials in flows. Use a dedicated test account, inject values through Maestro's environment mechanism or CI secrets, and keep test accounts out of production data.
- Test the highest-value paths only (sign-in, purchase, deep link entry, update install); keep logic checks in Jest.

## 9. Security review questions

- Which values are inlined into the bundle, and would any of them be harmful if published?
- Where do tokens live at rest, with which accessibility attribute, and when are they deleted?
- Does every API route authenticate the caller and filter by owner or tenant on reads and writes?
- Which deep links can trigger side effects, and what confirms the user's intent?
- Are redirect URIs exact, and is the OAuth flow authorization code with PKCE in the system browser?
- Who can publish an EAS Update to production, and is the Expo account protected with two-factor authentication?
- Do logs, analytics and crash reports exclude tokens and personal data?
