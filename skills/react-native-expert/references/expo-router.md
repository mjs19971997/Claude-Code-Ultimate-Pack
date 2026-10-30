# Expo Router

File-based routing for Expo apps: file conventions, layouts, typed routes, params, protected routes, deep links and universal links, rewriting incoming links, and route testing. Verified against Expo Router 58.0.x in Expo SDK 58 (2026-10).

## Contents

1. [File conventions](#1-file-conventions)
2. [Layouts and navigators](#2-layouts-and-navigators)
3. [Navigation and params](#3-navigation-and-params)
4. [Typed routes](#4-typed-routes)
5. [Protected routes](#5-protected-routes)
6. [Deep links](#6-deep-links)
7. [Universal links and App Links](#7-universal-links-and-app-links)
8. [Rewriting incoming links](#8-rewriting-incoming-links)
9. [Testing routes](#9-testing-routes)

## 1. File conventions

Every file in `src/app` with a default export is a route, except `_layout` files. Anything else placed there is also treated as a route, so keep components, hooks and utilities in sibling folders.

| Path | URL | Notes |
|---|---|---|
| `src/app/index.tsx` | `/` | Initial route; there is no initial-route config in code |
| `src/app/about.tsx` | `/about` | Static segment |
| `src/app/user/[id].tsx` | `/user/42` | Dynamic segment |
| `src/app/docs/[...rest].tsx` | `/docs/a/b` | Catch-all |
| `src/app/(tabs)/index.tsx` | `/` | `(group)` folders organise files and are not part of the URL |
| `src/app/_layout.tsx` | none | Root layout; providers, fonts, splash screen |
| `src/app/+not-found.tsx` | unmatched | Shown when no route matches |
| `src/app/+native-intent.tsx` | none | Native only; rewrites incoming system paths |

The root `_layout.tsx` runs before any route and replaces the old `App.tsx` entry point.

## 2. Layouts and navigators

A layout renders a navigator and its children. Common choices are `Stack`, `Tabs` and `Slot` (no navigator, just renders the matched child). Tabs and drawers have their own entry points (`expo-router/drawer`, `expo-router/tabs`, native tabs under `expo-router/unstable-native-tabs`); check the current docs before relying on a module that is marked unstable.

```tsx
// src/app/(app)/_layout.tsx
import { Tabs } from 'expo-router';

export default function AppLayout() {
  return (
    <Tabs screenOptions={{ headerShown: true }}>
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="orders" options={{ title: 'Orders' }} />
    </Tabs>
  );
}
```

- Declare each screen once per navigator. A screen cannot appear in two active groups at the same time; use a conditional group instead of duplicating it.
- `Stack.Screen` can also be rendered inside a screen component to set options from screen state.
- Keep the root layout free of data fetching that blocks first paint; hold the splash screen until fonts and session state are ready.

## 3. Navigation and params

```tsx
import { Link, router, useLocalSearchParams } from 'expo-router';
import { Text, Pressable } from 'react-native';

export default function Order() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <>
      <Text>Order {id}</Text>
      <Link href="/orders">All orders</Link>
      <Pressable onPress={() => router.push({ pathname: '/orders/[id]', params: { id: '43' } })}>
        <Text>Next order</Text>
      </Pressable>
    </>
  );
}
```

- `useLocalSearchParams` returns params for the current screen only and keeps the screen stable when other screens in the stack change; `useGlobalSearchParams` follows the focused route and re-renders on every URL change, so prefer the local hook.
- Params are strings (or string arrays) that originate outside the app when opened from a link. Parse and validate them (for example with a schema library or a manual check) before using them for lookups.
- `router.push`, `router.replace`, `router.back`, `router.dismiss` and `router.navigate` are imperative; use `<Link>` for tappable navigation so accessibility roles and web hrefs are right.
- Do not put tokens, passwords or large objects in params; they appear in URLs and can end up in logs.

## 4. Typed routes

Typed routes statically check `href` values for `<Link>`, `router` and related hooks.

```json
{
  "expo": {
    "experiments": { "typedRoutes": true }
  }
}
```

- The Expo CLI generates the type file the first time `npx expo start` runs and adds it to `.gitignore`. On CI, run `npx expo customize tsconfig.json` before `tsc` to produce the types without starting a dev server.
- Static routes accept strings: `href="/about"` or a template string such as `` `/user/${id}` ``.
- Dynamic routes with a pattern need an object: `{ pathname: '/user/[id]', params: { id: 1 } }`; unknown params are type errors.
- Relative hrefs (`./about`) are not supported by typed routes; use absolute paths.
- Cast with `as Href` only for values that were validated at run time.

## 5. Protected routes

`Stack.Protected` takes a boolean `guard`. When it is false, the listed screens cannot be reached by client-side navigation; a user already on such a screen is redirected, and its history entries are removed.

```tsx
// src/app/_layout.tsx
import { Stack } from 'expo-router';

export default function RootLayout({ isSignedIn }: { isSignedIn: boolean }) {
  return (
    <Stack>
      <Stack.Protected guard={!isSignedIn}>
        <Stack.Screen name="sign-in" />
      </Stack.Protected>
      <Stack.Protected guard={isSignedIn}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
    </Stack>
  );
}
```

- Protected screens can be nested for role-based layouts (for example an `isAdmin` guard inside a signed-in group).
- This is a UX control. Anyone can modify the JavaScript on a rooted or jailbroken device, so the API must authenticate and authorize every request regardless of which screens the app shows.
- Compute `isSignedIn` from secure storage plus a server check at startup; render a splash or loading state until the answer is known, so the wrong group never flashes.

## 6. Deep links

Add a custom scheme in app config, then create a development build (a scheme change is native configuration):

```json
{
  "expo": {
    "scheme": "myapp"
  }
}
```

- Without `scheme`, prebuild uses `android.package` and `ios.bundleIdentifier` as default schemes.
- Test on a simulator or emulator with `npx uri-scheme open myapp://orders/42 --ios` (or `--android`). In Expo Go the scheme is `exp://`, for example `exp://127.0.0.1:8081/--/orders/42`.
- Every file route is a link target by default. Routes that must not be reachable from outside (admin screens, payment confirmation) need a guard or a rewrite in `+native-intent.tsx`.
- A custom scheme can be registered by any other app on the device. Treat link content as untrusted, never carry credentials in a link, and use verified links for flows with security impact.
- For OAuth redirects use `makeRedirectUri({ scheme, path })` from `expo-auth-session` so the same code works in development builds and production.

## 7. Universal links and App Links

HTTPS links that open the app when it is installed and the website otherwise need two-way verification.

iOS: host `apple-app-site-association` (no extension, served over HTTPS at `/.well-known/`) and add the associated domain, without the protocol.

```json
{
  "applinks": {
    "apps": [],
    "details": [
      { "appID": "<APPLE_TEAM_ID>.com.example.myapp", "paths": ["/records/*"] }
    ]
  }
}
```

```json
{
  "expo": {
    "ios": {
      "bundleIdentifier": "com.example.myapp",
      "associatedDomains": ["applinks:www.example.com"]
    }
  }
}
```

Android: declare an intent filter with `autoVerify` and host `/.well-known/assetlinks.json` containing the package name and the SHA-256 fingerprint of the signing certificate (`eas credentials -p android` shows the fingerprint for EAS-managed keys).

```json
{
  "expo": {
    "android": {
      "package": "com.example.myapp",
      "intentFilters": [
        {
          "action": "VIEW",
          "autoVerify": true,
          "data": [{ "scheme": "https", "host": "www.example.com", "pathPrefix": "/records" }],
          "category": ["BROWSABLE", "DEFAULT"]
        }
      ]
    }
  }
}
```

- The files must be reachable over HTTPS without redirects that change the host; verify with a validator before shipping.
- The `*` wildcard in AASA paths does not match slashes or dots.
- Entitlements and intent filters are native configuration: rebuild the binary after changing them.
- Restrict `paths` and `pathPrefix` to the routes that should open in the app.

## 8. Rewriting incoming links

`+native-intent.tsx` exports `redirectSystemPath({ path, initial })`. It runs outside the React tree, before the app's state exists, and receives whatever the system passed: not always a valid URL.

```ts
// src/app/+native-intent.tsx
const ALLOWED_PREFIXES = ['/orders/', '/records/'];

export function redirectSystemPath({ path }: { path: string; initial: boolean }) {
  try {
    const url = new URL(path, 'myapp://app.home');
    if (ALLOWED_PREFIXES.some((p) => url.pathname.startsWith(p))) {
      return url.pathname + url.search;
    }
    return '/';
  } catch {
    return '/unexpected-error';
  }
}
```

- Never throw from this function; return a safe route such as `/unexpected-error` instead.
- Use it for allow-listing, mapping legacy URLs to current routes, and handing third-party referral links to their SDK. It has no access to auth state; do auth redirects in a layout.
- It is native only. On web, redirects are handled by the server or in the root layout.

## 9. Testing routes

`expo-router/testing-library` renders the router against a mocked file system and returns a promise.

```tsx
import { renderRouter, screen } from 'expo-router/testing-library';
import { Text } from 'react-native';

test('renders the order route', async () => {
  await renderRouter(
    {
      index: () => <Text>Home</Text>,
      'orders/[id]': () => <Text>Order</Text>,
    },
    { initialUrl: '/orders/42' },
  );
  expect(screen).toHavePathname('/orders/42');
});
```

- Matchers such as `toHavePathname` come from the router testing library; check the current docs for the full list and options.
- Cover the failure paths: unknown route (`+not-found`), malformed params, and a guard that flips from true to false while a protected screen is open.
