# Navigation with go_router

Reference for go_router 18.1.2 (requires Flutter 3.44 / Dart 3.12 or newer, depends on the `material_ui` and `cupertino_ui` packages since 18.0.0) on Flutter 3.47 (2026-10). Open this file when configuring routes, redirects, tab shells, deep links or navigation tests.

## Contents

1. [Setup](#1-setup)
2. [Routes and parameters](#2-routes-and-parameters)
3. [Navigating](#3-navigating)
4. [Redirects and guards](#4-redirects-and-guards)
5. [ShellRoute and StatefulShellRoute](#5-shellroute-and-statefulshellroute)
6. [Deep links](#6-deep-links)
7. [Typed routes and transitions](#7-typed-routes-and-transitions)
8. [Testing navigation](#8-testing-navigation)

## 1. Setup

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

final _router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomePage()),
  ],
);

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) =>
      MaterialApp.router(routerConfig: _router);
}
```

- Create the `GoRouter` once and keep it alive; do not build it inside `build`, because every rebuild would reset navigation state. With Riverpod, expose it through a provider and read it once.
- `MaterialApp.router(routerConfig: router)` replaces `home` and `onGenerateRoute`.
- Handle unknown locations with `errorBuilder` or `onException` (use only one of `onException`, `errorBuilder`, `errorPageBuilder`).
- Web: use path URLs by calling `usePathUrlStrategy()` from `flutter_web_plugins/url_strategy.dart` before `runApp`, and configure the server to serve `index.html` for unknown paths.

## 2. Routes and parameters

```dart
GoRoute(
  path: '/books/:id',
  name: 'book',
  builder: (context, state) {
    final id = state.pathParameters['id']!;
    final tab = state.uri.queryParameters['tab'] ?? 'info';
    return BookPage(id: id, tab: tab);
  },
  routes: [
    GoRoute(path: 'reviews', builder: (_, state) => ReviewsPage(state.pathParameters['id']!)),
  ],
)
```

- Child paths are relative (no leading slash) and nest under the parent URL: `/books/42/reviews`.
- Path parameters are strings and untrusted: parse with `int.tryParse` and show a not-found page on failure. Regular expression constraints on path parameters are documented in the go_router changelog (17.5.0); check the current docs for syntax.
- Query parameters come from `state.uri.queryParameters`. Use them for filters that should survive a refresh and be shareable.
- `state.extra` carries an object in memory only. It is lost on web reload and on deep links, so use it for optimization, never as the only source of data. Fetch by id from the path instead.
- Route `metadata` (17.5.0) attaches application-defined data to routes and is exposed on `GoRouterState`.
- Give routes a `name` and use `context.goNamed('book', pathParameters: {'id': '42'})` when paths change often.

## 3. Navigating

| Call | Effect |
|---|---|
| `context.go('/books/42')` | Replaces the stack with the matching routes (declarative) |
| `context.push('/books/42')` | Adds a page on top of the current stack; returns a `Future` with the pop result |
| `context.pop([result])` | Removes the top page |
| `context.replace('/x')` | Replaces the top entry |
| `context.pushReplacement('/x')` | Pushes and removes the previous top |
| `context.canPop()` | Whether a pop is possible |

- Prefer `go` for moving between destinations (tabs, deep links) and `push` for transient pages such as detail views, dialogs-as-pages and pickers that return a value.
- `context.go` and friends are extensions on `BuildContext`; outside widgets use a `GoRouter` instance (`router.go(...)`).
- Use `GoRoute.onExit` to confirm leaving a page with unsaved changes.

## 4. Redirects and guards

```dart
final router = GoRouter(
  refreshListenable: authState,          // a Listenable that fires on sign-in or sign-out
  redirect: (context, state) {
    final loggedIn = authState.isSignedIn;
    final atLogin = state.matchedLocation == '/login';

    if (!loggedIn) {
      return atLogin
          ? null
          : '/login?from=${Uri.encodeComponent(state.uri.toString())}';
    }
    if (atLogin) {
      final from = state.uri.queryParameters['from'];
      final internal = from != null && from.startsWith('/') && !from.startsWith('//');
      return internal ? from : '/';
    }
    return null;
  },
  routes: [/* ... */],
);
```

- A redirect returns the new location or `null` to stay. Return `null` when the user is already at the destination, or the redirect loops.
- `refreshListenable` makes go_router re-evaluate redirects when auth state changes. With Riverpod, build a small `ChangeNotifier` that listens to the auth provider with `ref.listen` and calls `notifyListeners`.
- `GoRoute.redirect` guards one subtree (for example `/admin` requires a role); top-level `redirect` guards the whole app. Chained redirects are resolved fully since 17.2.1.
- Validate the `from` return path as an internal path before using it, otherwise a crafted link can bounce users to an arbitrary location.
- Top-level `onEnter` (16.3.0 and later) receives `(context, currentState, nextState, router)` and returns `Allow()` or `Block()`; use it to intercept literal navigation or deep links (for example to handle an invite link). It is evaluated once per navigation against the literal target, before the top-level and route-level `redirect` callbacks, so it never sees locations reached only through a redirect.
- Redirects are UX, not security: the server must authorize every request.

## 5. ShellRoute and StatefulShellRoute

- `ShellRoute(builder: (context, state, child) => ...)`: shared chrome (app bar, navigation rail) around a changing child. Switching away discards the child's stack.
- `StatefulShellRoute.indexedStack(builder: (context, state, navigationShell) => ..., branches: [...])`: each `StatefulShellBranch` keeps its own `Navigator` and stack, held in an `IndexedStack`. Use it for bottom navigation where each tab remembers its position.

```dart
StatefulShellRoute.indexedStack(
  builder: (context, state, shell) => Scaffold(
    body: shell,
    bottomNavigationBar: NavigationBar(
      selectedIndex: shell.currentIndex,
      onDestinationSelected: (i) =>
          shell.goBranch(i, initialLocation: i == shell.currentIndex),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.home), label: 'Home'),
        NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
      ],
    ),
  ),
  branches: [
    StatefulShellBranch(routes: [GoRoute(path: '/home', builder: (_, _) => const HomeTab())]),
    StatefulShellBranch(routes: [GoRoute(path: '/profile', builder: (_, _) => const ProfileTab())]),
  ],
)
```

- `goBranch(index, initialLocation: true)` resets the branch to its first page when the active tab is tapped again.
- To show a page above the bottom bar (full screen), set `parentNavigatorKey` to the root navigator key on that `GoRoute`.
- `ShellRoute` and `StatefulShellRoute` notify the root observers about shell navigation by default since 17.0.0 (`notifyRootObserver`); disable it if analytics would double count screens.
- Both route types accept `clipBehavior` for the nested navigator since 18.1.0.
- Use `StatefulShellRoute` (the `StatefulShellRoute()` constructor with a custom container) only when you need a different container than `IndexedStack`, such as lazy branches.

## 6. Deep links

Android (`android/app/src/main/AndroidManifest.xml`, inside the main `<activity>`):

```xml
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https" android:host="app.example.com" />
</intent-filter>
```

- Host a Digital Asset Links file at `https://app.example.com/.well-known/assetlinks.json` listing the package name and the SHA-256 fingerprint of the signing certificate (the Play App Signing key for store builds).
- iOS: add the Associated Domains capability `applinks:app.example.com` in Xcode and host `apple-app-site-association` over HTTPS without redirects.
- Custom schemes (`myapp://`) work without hosted files but are not verified, so any app can claim them; prefer verified HTTPS links for anything sensitive.
- go_router receives the incoming URL as the initial or next location, so a route table that matches the web URLs handles deep links without extra code. Check the current Flutter deep linking documentation for whether the framework handler is enabled by default in your project and for the Android and iOS opt-in or opt-out switch.
- Treat deep link content as untrusted input: validate ids, never execute actions (payments, deletes) from a link without confirmation, and require sign-in through the normal redirect.
- Test locally with `adb shell am start -a android.intent.action.VIEW -d "https://app.example.com/books/42"` and `xcrun simctl openurl booted "https://app.example.com/books/42"`.

## 7. Typed routes and transitions

- `go_router_builder` with `build_runner` generates type-safe route classes from `@TypedGoRoute` annotations; arguments become constructor fields, and `const BookRoute(id: '42').go(context)` replaces string paths. `TypedQueryParameter` customizes query names and encoding (17.1.0 and 17.2.0).
- Custom transitions: return a `CustomTransitionPage` from `pageBuilder`; use `NoTransitionPage` for tab switches.
- Dialog and bottom-sheet routes can be modeled as `GoRoute` with `pageBuilder` returning `DialogPage` (your own `Page` subclass) when they need a URL; otherwise call `showDialog` directly.

## 8. Testing navigation

```dart
testWidgets('signed-out users land on the login page', (tester) async {
  signedIn.value = false;
  await tester.pumpWidget(MaterialApp.router(routerConfig: router));
  await tester.pumpAndSettle();
  expect(find.text('login'), findsOneWidget);

  signedIn.value = true;               // refreshListenable fires, redirect runs again
  await tester.pumpAndSettle();
  expect(find.text('home'), findsOneWidget);
});
```

- Build a fresh `GoRouter` per test (a factory function) so state does not leak between tests.
- Assert the location with `router.routerDelegate.currentConfiguration.uri.toString()`.
- Test the redirect function directly for table-driven cases: signed out to protected path, signed in at `/login`, hostile `from` values (`https://evil.example`, `//evil.example`).
- For widgets that call `context.go`, wrap them in a minimal `GoRouter` with a stub destination instead of mocking the context extension.
