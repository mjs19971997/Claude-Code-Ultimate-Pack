---
name: flutter-expert
description: >-
  Builds, tests and ships Flutter apps in Dart: widgets and layout constraints, Riverpod and Bloc state management, go_router navigation, platform channels with Pigeon, Material 3 theming, widget and golden tests, and signed release builds. Use when editing pubspec.yaml, analysis_options.yaml, lib/ Dart code, ConsumerWidget, Cubit, GoRouter, MethodChannel, flutter test, flutter build appbundle or ipa, or when seeing overflow or BuildContext errors. Not for React Native (use react-native-expert), native iOS Swift (use swift-expert), native Android Kotlin (use android-expert), or backend API design (use rest-api-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Flutter Expert

This skill covers application development with Flutter and Dart: the widget tree and layout model, state management with Riverpod and Bloc, declarative routing with go_router, calling native code through platform channels, Material 3 theming, automated tests, and building release artifacts for Android and iOS. Language-level guidance targets recent Dart 3 features. Native-only work, cross-platform alternatives and server design belong to other skills.

> Verified against Flutter 3.47.9 (Dart 3.13.7), flutter_riverpod 3.4.3, riverpod_generator 4.0.9, flutter_bloc 9.1.1, go_router 18.1.2, mocktail 1.0.5, flutter_secure_storage 11.2.0, pigeon 29.1.0, flutter_lints 6.0.0 (2026-10).

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

- Covered: Flutter widgets (stateless, stateful, inherited, keys, const constructors), `BuildContext` rules, layout constraints, Riverpod (including `riverpod_generator`) and Bloc/Cubit, go_router (redirects, shell routes, deep links), `MethodChannel`, Pigeon and FFI notes, Material 3 theming, unit, widget, golden and `integration_test` tests with mocktail, `analysis_options.yaml`, release builds (`flutter build appbundle`, `flutter build ipa`), obfuscation, flavors, and secure storage.
- Not covered: React Native apps (react-native-expert), native iOS code in Swift (swift-expert), native Android code in Kotlin and Gradle internals (android-expert), REST or backend API design (rest-api-expert), CI pipeline design (cicd-expert), end-to-end browser testing (e2e-testing-expert), general application security review (secure-coding-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Dart 3.10 | Dot shorthands: omit the type name when the context type is known (`mainAxisAlignment: .center`, enum values, static members); needs SDK constraint `^3.10.0` or newer |
| Dart 3.8 | Null-aware elements in list, set and map literals: `[?maybeNull, 'a']`, `{?key: value}` |
| Dart 3.12 | Private named parameters: `Point({required this._x})` initializes the private field `_x`, callers write `Point(x: 1)` |
| Dart 3.13 | Primary constructors (`class Point(var int x, var int y);`) are available behind SDK `^3.13.0`; optional brevity feature, existing syntax stays valid |
| Macros | Cancelled; the `macros` package on pub.dev is discontinued. Use `build_runner` generators (`json_serializable`, `freezed`, `riverpod_generator`) instead |
| Material and Cupertino | Flutter 3.47 ships standalone `material_ui` and `cupertino_ui` packages (1.x). `package:flutter/material.dart` still works during the transition; migrate with `dart fix --apply --code=migrate_design_widgets`. go_router 18 already depends on `material_ui` |
| Riverpod 3 | `StateProvider`, `StateNotifierProvider`, `ChangeNotifierProvider` moved to `package:flutter_riverpod/legacy.dart`; providers compare with `==`; failing providers retry automatically; `Ref.mounted` checks disposal; `AsyncValue.valueOrNull` removed (use `.value`); one `Notifier` class for auto-dispose and family |
| riverpod_generator 4 | `@riverpod` on a function or a class extending the generated `_$Name`; `Ref` is a single non-generic type; needs `riverpod_annotation`, `build_runner`, and a `part 'file.g.dart';` line |
| flutter_bloc 9 | `Cubit<State>` with `emit`; `Bloc<Event, State>` with `on<Event>(handler)`; `BlocProvider`, `BlocBuilder`, `BlocListener`, `BlocSelector`, `context.read`, `context.watch` |
| go_router 18 | Requires Flutter 3.44 / Dart 3.12; `GoRouter(routes, redirect, refreshListenable, initialLocation, onException)`; `ShellRoute`, `StatefulShellRoute.indexedStack`; top-level `onEnter`; route `metadata`; typed routes via `go_router_builder` |
| Platform channels | `MethodChannel('com.example/battery')` with `invokeMethod`; Pigeon 29 generates type-safe Dart, Kotlin, Swift, Java, Objective-C, C++ and GObject code from a Dart definition (`dart run pigeon --input pigeons/api.dart`) |
| Native interop | Dart FFI (`dart:ffi`, `package:ffigen`) for C libraries; Pigeon native interop (FFI and JNI) is marked experimental in its README |
| Testing | `flutter test` (unit and widget, `WidgetTester`, `pumpWidget`, `pump`, `pumpAndSettle`), `matchesGoldenFile` with `--update-goldens`, `integration_test` SDK package, `mocktail` (no code generation) |
| Release builds | `flutter build appbundle` and `flutter build ipa` (macOS only); `--obfuscate` must be combined with `--split-debug-info=<dir>`; `flutter symbolize` decodes stack traces; `--flavor`, `--dart-define`, `--dart-define-from-file` |
| Lints | New projects get `flutter_lints` 6.0.0 with `include: package:flutter_lints/flutter.yaml`; pure Dart packages use `package:lints` (6.1.0) |
| Deprecations | `Color.withOpacity` is deprecated, use `withValues(alpha: 0.5)`; Material 3 is the default (`useMaterial3` defaults to true) |

## 3. Workflow

1. Read `pubspec.yaml` (SDK constraint, state management package, router, lints) and `analysis_options.yaml`; run `flutter --version` and match new syntax to the SDK lower bound (dot shorthands need `^3.10.0`).
2. Identify the target platforms and whether the task touches native code (permissions, channels, Gradle, Xcode schemes).
3. Follow the existing architecture and state package; do not introduce a second one without a stated reason.
4. Build UI from small widgets with `const` constructors; keep `build` free of side effects, network calls and navigation.
5. Put state and I/O behind providers, blocs or repositories so widgets stay declarative and testable.
6. Run `dart format .`, `flutter analyze` and `flutter test`; for generated code run `dart run build_runner build` (add `--delete-conflicting-outputs` only when it reports conflicts).
7. For layout bugs, open Flutter DevTools (Widget Inspector, Layout Explorer) and read the constraint chain before wrapping widgets in `SizedBox` or `Expanded`.
8. For releases, bump `version:` in `pubspec.yaml`, build with obfuscation and a symbols directory, store the symbols, and verify the signed artifact on a device.

## 4. Decision Rules

- If the project uses Riverpod, keep it; for new code prefer `Notifier` and `AsyncNotifier` over the legacy `StateNotifier`. Use `riverpod_generator` only when the team already runs `build_runner`; plain provider declarations need no code generation.
- If the team wants explicit event logs and strict transitions (analytics, audit, complex flows), use `Bloc`; for simple state transitions use `Cubit` because it needs no event classes.
- If state is local to one widget (a text field, an animation, a toggle), use `StatefulWidget` or hooks; lifting it into a provider adds indirection for no gain.
- If navigation has deep links, web URLs, auth redirects or tabs that keep their stack, use `go_router`; for a few imperative screens `Navigator.push` is enough.
- If bottom tabs must keep per-tab navigation state, use `StatefulShellRoute.indexedStack`; use plain `ShellRoute` when only the chrome is shared and tab state need not be kept.
- If the native call is a one-off with a primitive result, a `MethodChannel` is acceptable; with several methods or structured data, use Pigeon so both sides share a typed contract.
- If you need a C library or high-frequency calls, use `dart:ffi` with `ffigen`; channels cost a serialization round trip per call.
- If a value is secret (API key, signing key, token), it cannot ship in the app; see section 10. `--dart-define` is configuration, not secrecy.
- If a layout overflows, find which parent gives unbounded or tight constraints, then fix with `Expanded`, `Flexible`, `ConstrainedBox` or a scrollable, instead of hard-coding sizes.
- If the SDK is older than 3.47, keep `package:flutter/material.dart`; if it is 3.47 or newer, plan the migration to `material_ui` before the in-framework libraries are removed (check the current docs for the timeline).

## 5. Coding Standards

- Run `dart format` and keep `flutter analyze` clean; the repository's `analysis_options.yaml` is authoritative.
- Use `const` constructors and `const` widget instances wherever possible; enable `prefer_const_constructors` and `prefer_const_literals_to_create_immutables` (both in `flutter_lints`).
- Pass `super.key` in widget constructors: `const MyWidget({super.key});`.
- Prefer small `StatelessWidget` classes over helper methods returning widgets; a class gets its own element, rebuild boundary and `const` benefit.
- Never use `BuildContext` after an `await` without checking `if (!context.mounted) return;` (in a `State`, `if (!mounted) return;`).
- Do not store `BuildContext` in fields, providers or static variables.
- Use `final` for fields and locals, sealed classes and `switch` expressions for state variants, records for small tuples.
- Use `ListView.builder` or slivers for long lists; `ValueKey` or `ObjectKey` on list items whose identity matters.
- Dispose controllers, focus nodes, animation controllers, stream subscriptions and timers in `dispose()`.
- Name files `snake_case.dart`, types `UpperCamelCase`, and import with `package:` URIs inside `lib/` (no relative paths that climb out of `lib/src`).
- Replace deprecated calls when analysis flags them (`withOpacity` becomes `withValues(alpha:)`).

## 6. Project Structure

```text
my_app/
├── pubspec.yaml
├── analysis_options.yaml
├── lib/
│   ├── main.dart                  # runApp(ProviderScope(...)), error zone setup
│   ├── app/                       # MaterialApp.router, theme, router, flavors
│   ├── core/                      # shared widgets, http client, storage, utils
│   └── features/
│       └── todos/
│           ├── data/              # repositories, DTOs, data sources
│           ├── domain/            # entities, repository interfaces
│           └── presentation/      # widgets, notifiers/cubits, pages
├── test/                          # mirrors lib/; goldens in test/goldens/
├── integration_test/              # on-device flows
├── pigeons/                       # Pigeon definitions
├── android/                       # key.properties (gitignored), flavors
├── ios/
└── tool/                          # scripts: symbol upload, build wrappers
```

Feature-first folders keep a feature's UI, state and data together. Split into packages only when teams or build times demand it.

## 7. Design Patterns

- **Repository behind an interface**: widgets and notifiers depend on an abstract repository, tests override it with a mocktail fake. Cost: one extra class per data source.
- **AsyncNotifier per screen**: `build()` loads data, methods mutate with `AsyncValue.guard`, the widget switches on `AsyncData`, `AsyncError` and loading. Cost: understand the retry and disposal rules of Riverpod 3.
- **Cubit for UI logic, Bloc for event streams**: start with a Cubit; promote to a Bloc when you need event transformers such as `debounce` or `restartable` from `bloc_concurrency`.
- **Sealed state classes**: `sealed class LoginState` with `Initial`, `Submitting`, `Failure` variants gives exhaustive `switch` checks in the UI.
- **Redirect-driven auth**: one `redirect` plus `refreshListenable` decides login gating in a single place instead of per-screen checks.
- **Typed platform contract**: Pigeon `@HostApi` for Flutter-to-native calls and `@FlutterApi` for native-to-Flutter callbacks.
- **Flavors as entry points or build configs**: one app with `dev`, `staging`, `prod` flavors differing in application ID, name, icon and base URL.
- Deeper material: [references/state-management.md](references/state-management.md) and [references/navigation-go-router.md](references/navigation-go-router.md).

## 8. Best Practices

- Keep `build` fast and pure; it can run every frame during animation, so compute and fetch elsewhere.
- Use `ref.watch` in `build`, `ref.read` in callbacks, and `ref.listen` for side effects such as snackbars; select narrow slices with `.select` to limit rebuilds.
- Scope rebuilds: wrap only the part that changes in `Consumer`, `BlocBuilder` or `ValueListenableBuilder`, and pass static children through `child:`.
- Handle loading, empty, error and data states for every async screen; show a retry action on errors.
- Keep business logic out of widgets so it can be unit tested without a widget tree.
- Use `Theme.of(context)` tokens (`colorScheme`, `textTheme`) rather than literal colors and sizes; the app then follows dark mode and accessibility settings.
- Support text scaling and screen readers: `Semantics` for custom controls, minimum 48 logical pixel tap targets, check with large font settings.
- Commit `pubspec.lock` for apps and run `flutter pub outdated` before upgrades.
- Report uncaught errors in one place: `FlutterError.onError` and `PlatformDispatcher.instance.onError` feed the crash reporter.

## 9. Performance

- Measure first: run in profile mode (`flutter run --profile`) on a real device and open DevTools Performance and CPU Profiler; debug mode timings are not meaningful.
- Target the frame budget: 16 ms per frame at 60 Hz, 8 ms at 120 Hz, for both the UI and raster threads.
- Rebuild less: `const` widgets, small widgets, `select`, `BlocSelector`, `buildWhen`; check with the "track widget rebuilds" option in DevTools.
- Avoid `Opacity`, `ClipRRect` with `saveLayer` and `ShaderMask` on large animated subtrees; prefer `FadeTransition`, `AnimatedOpacity`, or clip with a decoration.
- Use `ListView.builder`, `SliverList`, `itemExtent` or `prototypeItem` for long lists; do not build thousands of children eagerly.
- Move heavy work (JSON parsing of large payloads, image processing) off the UI isolate with `Isolate.run` or `compute`.
- Resize images to display size (`cacheWidth`, `cacheHeight`, `ResizeImage`) and cache network images.
- Analyze app size with `flutter build appbundle --analyze-size --target-platform android-arm64` (cannot be combined with `--split-debug-info`), and keep `--tree-shake-icons` on (default).

## 10. Security

- Everything in the app bundle is readable. `--dart-define` and `--dart-define-from-file` values become compile-time constants inside the binary and can be extracted, so never put API secrets, private keys or service-account credentials there. Keep secrets on a server and give the app short-lived, user-scoped tokens.
- Obfuscation (`--obfuscate`) renames identifiers only; it does not hide strings, assets or logic, and it is not encryption.
- Store tokens with `flutter_secure_storage` (Android Keystore-backed encryption, iOS Keychain); do not use `shared_preferences` for credentials. Clear storage on sign-out. Version 11 removed legacy ciphers; upgrade from v10 first so stored data migrates.
- Keep the Android keystore, `key.properties`, iOS certificates and provisioning profiles out of git (`key.properties` and `**/*.jks` are in the generated `android/.gitignore`); inject them in CI from a secret store.
- Use HTTPS only; do not install a `badCertificateCallback` that returns true. Consider certificate pinning for high-risk apps and plan pin rotation.
- Validate and sanitize deep link and route parameters; treat `state.uri` input as untrusted, and allow-list the `from` redirect target to internal paths so a crafted link cannot send users to another site.
- Do not log tokens or personal data.
- On Android, set `android:allowBackup="false"` or exclude secret stores when backups could expose them; on both platforms request the minimum permissions.
- Authentication and authorization decisions belong on the server; client checks only shape the UI.

## 11. Testing

- Unit tests (`test/`): plain Dart with `package:test` or `flutter_test`; mock collaborators with `mocktail` (`class MockRepo extends Mock implements Repo {}`, `when(() => repo.load()).thenAnswer(...)`, `registerFallbackValue` for custom argument matchers).
- Widget tests: `await tester.pumpWidget(...)`, then `tester.tap`, `tester.enterText`, `await tester.pump()` for one frame or `pumpAndSettle()` until animations end; wrap the widget in `MaterialApp` and `ProviderScope` or `BlocProvider`.
- Riverpod: override providers in `ProviderScope(overrides: [...])`; set `retry: (_, _) => null` in tests that expect errors so the automatic retry does not delay them.
- Bloc: drive the bloc or Cubit and assert the emitted sequence with `expectLater(bloc.stream, emitsInOrder([...]))`; `bloc_test` 10.0.0 failed to resolve against the test packages pinned by Flutter 3.47.9 when checked, so confirm `flutter pub add --dev bloc_test` resolves before relying on `blocTest`.
- Golden tests: `await expectLater(find.byType(Card), matchesGoldenFile('goldens/card.png'))`; update with `flutter test --update-goldens`; render on one OS in CI because font rendering differs across platforms.
- Integration tests: `integration_test/app_test.dart` with `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`; run `flutter test integration_test -d <device>`.
- Cover failure paths: network errors, empty lists, expired sessions, permission denial, and redirect behaviour for signed-out users.
- Commands: `flutter test`, `flutter test --coverage`, `flutter test test/features/todos_test.dart --plain-name "shows todos"`.
- Details and golden, integration and release material: [references/testing-release.md](references/testing-release.md).

## 12. Review Checklist

- [ ] SDK constraint and package versions match the syntax used (dot shorthands, primary constructors).
- [ ] `flutter analyze` and `dart format --set-exit-if-changed .` pass; no new lint ignores without a reason.
- [ ] Widgets use `const` where possible, accept `super.key`, and do no work in `build`.
- [ ] No `BuildContext` use after `await` without a `mounted` check.
- [ ] Controllers, subscriptions and timers are disposed.
- [ ] Async screens handle loading, error, empty and data states.
- [ ] State is read with `watch` in `build`, `read` in callbacks, with narrow `select` where lists are large.
- [ ] Routes validate parameters; redirects cannot loop and allow-list the return path.
- [ ] No secrets, keystores or `.env` files committed; no secret in `--dart-define`.
- [ ] Tokens use secure storage; HTTPS only; no disabled certificate checks.
- [ ] Tests cover the new logic and at least one failure path; goldens regenerated deliberately.
- [ ] Release build uses `--obfuscate --split-debug-info`, and symbols are archived per version.

## 13. Production Notes

- Version numbers: `version: 1.4.0+23` in `pubspec.yaml` maps to name and build number; override per build with `--build-name` and `--build-number`.
- Android: build an App Bundle for Play (`flutter build appbundle`); keep upload-key credentials in `android/key.properties` (gitignored) read by `android/app/build.gradle.kts`, or in CI secrets. Use Play App Signing.
- iOS: `flutter build ipa` runs on macOS with Xcode and signing set up; check `flutter build ipa --help` for the current export options.
- Archive the `--split-debug-info` directory for every released build and upload symbols to the crash reporter; without them obfuscated traces cannot be read (`flutter symbolize -i trace.txt -d build/symbols`).
- Flavors need matching native setup: Gradle `productFlavors` on Android and Xcode schemes and build configurations on iOS, then `flutter run --flavor staging -t lib/main_staging.dart`.
- Use staged rollouts (Play Console, TestFlight phased release) and keep a remote kill switch or minimum-version check for broken releases.
- Track Flutter upgrades with the breaking-changes page for each release; upgrade `flutter_riverpod`, `go_router` and Material packages in separate commits and read their changelogs.
- Material and Cupertino are moving out of the framework (`material_ui`, `cupertino_ui`); check the current docs for the deprecation timeline before large UI refactors.

## 14. Examples

An `AsyncNotifier` with a repository provider, widget, and a mocktail-backed test (Riverpod 3):

```dart
// lib/features/todos/todos.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

abstract interface class TodoRepository {
  Future<List<String>> fetchAll();
  Future<void> add(String title);
}

final todoRepositoryProvider = Provider<TodoRepository>(
  (ref) => throw UnimplementedError('Override in main() or in tests'),
);

class TodosNotifier extends AsyncNotifier<List<String>> {
  @override
  Future<List<String>> build() => ref.watch(todoRepositoryProvider).fetchAll();

  Future<void> add(String title) async {
    final repo = ref.read(todoRepositoryProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await repo.add(title);
      return repo.fetchAll();
    });
  }
}

final todosProvider = AsyncNotifierProvider<TodosNotifier, List<String>>(
  TodosNotifier.new,
);

class TodoList extends ConsumerWidget {
  const TodoList({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final todos = ref.watch(todosProvider);
    return switch (todos) {
      AsyncData(:final value) => ListView(
        children: [for (final t in value) ListTile(title: Text(t))],
      ),
      AsyncError(:final error) => Center(child: Text('Failed: $error')),
      _ => const Center(child: CircularProgressIndicator()),
    };
  }
}
```

```dart
// test/features/todos_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:my_app/features/todos/todos.dart';

class MockTodoRepository extends Mock implements TodoRepository {}

void main() {
  testWidgets('shows todos from the repository', (tester) async {
    final repo = MockTodoRepository();
    when(repo.fetchAll).thenAnswer((_) async => ['Buy milk']);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [todoRepositoryProvider.overrideWithValue(repo)],
        child: const MaterialApp(home: Scaffold(body: TodoList())),
      ),
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();
    expect(find.text('Buy milk'), findsOneWidget);
  });
}
```

go_router with an auth redirect and persistent tabs:

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

final signedIn = ValueNotifier<bool>(false);

final router = GoRouter(
  initialLocation: '/home',
  refreshListenable: signedIn,
  redirect: (context, state) {
    final onLogin = state.matchedLocation == '/login';
    if (!signedIn.value) {
      return onLogin
          ? null
          : '/login?from=${Uri.encodeComponent(state.uri.toString())}';
    }
    // Allow-list: only internal absolute paths are accepted as return targets.
    final from = state.uri.queryParameters['from'];
    final safe = from != null && from.startsWith('/') && !from.startsWith('//');
    return onLogin ? (safe ? from : '/home') : null;
  },
  routes: [
    GoRoute(path: '/login', builder: (_, _) => const Text('login')),
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
        StatefulShellBranch(routes: [
          GoRoute(path: '/home', builder: (_, _) => const Text('home')),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/profile', builder: (_, _) => const Text('profile')),
        ]),
      ],
    ),
  ],
);
```

A Pigeon definition and the call from Dart (run `dart run pigeon --input pigeons/device_api.dart`):

```dart
// pigeons/device_api.dart
import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/src/device_api.g.dart',
    kotlinOut: 'android/app/src/main/kotlin/com/example/my_app/DeviceApi.g.kt',
    kotlinOptions: KotlinOptions(package: 'com.example.my_app'),
    swiftOut: 'ios/Runner/DeviceApi.g.swift',
  ),
)
class BatteryInfo {
  BatteryInfo({required this.level, required this.charging});
  int level;
  bool charging;
}

@HostApi()
abstract class DeviceApi {
  @async
  BatteryInfo getBattery();
}

// Dart side: final info = await DeviceApi().getBattery();
```

Release build with obfuscation, keeping signing material out of git:

```bash
# android/key.properties and the keystore are gitignored; CI writes them from secrets.
flutter build appbundle --release --flavor prod -t lib/main_prod.dart \
  --obfuscate --split-debug-info=build/symbols/1.4.0+23 \
  --dart-define-from-file=config/prod.json   # public config only, never secrets
# Archive build/symbols/1.4.0+23 with the release; decode traces later:
flutter symbolize -i crash_trace.txt -d build/symbols/1.4.0+23
```

## 15. Common Mistakes

- **Using `context` after `await`**: the widget may be disposed, causing "use_build_context_synchronously" warnings or crashes. Check `context.mounted` first.
- **Unbounded constraints**: a `ListView` or `Column` inside another `Column` throws "Vertical viewport was given unbounded height" or an overflow stripe. Wrap in `Expanded`/`Flexible` or give a bounded parent.
- **Side effects in `build`**: starting requests or navigating inside `build` repeats on every rebuild. Move to `initState`, a notifier `build`, or a listener.
- **`ref.read` in `build`**: the widget never updates. Use `ref.watch`; use `ref.read` only in event handlers.
- **Mutating state in place**: `state.add(x)` on a list does not notify (Riverpod 3 compares with `==`, Bloc ignores equal states). Emit a new list or use immutable classes with value equality (Equatable, freezed).
- **Importing removed Riverpod 2 APIs**: `StateProvider` and `StateNotifierProvider` now live in `legacy.dart`; `valueOrNull` is gone. Migrate to `Notifier` and `.value`.
- **Secrets in `--dart-define`**: anyone can extract them from the binary. Move the call to a backend.
- **Obfuscating without keeping symbols**: crash traces become unreadable. Always pass `--split-debug-info` and archive the directory per version.
- **Committing `key.properties` or keystores**: signing identity leak. Keep them in `.gitignore` and rotate if exposed.
- **Keys missing in dynamic lists**: reordering items loses state of stateful children. Give items a `ValueKey(id)`.
- **Golden tests on mixed OSs**: pixel differences make CI flaky. Generate and compare on one platform.
- **Leaving go_router redirects unbounded**: a redirect that returns a location which redirects back loops. Return `null` when already at the target and test both signed-in states.

## 16. References

- [references/state-management.md](references/state-management.md): Riverpod 3 providers, Notifier and AsyncNotifier, code generation, migration from 2.x, Bloc and Cubit patterns and tests.
- [references/navigation-go-router.md](references/navigation-go-router.md): go_router configuration, redirects, shell routes, deep links on Android and iOS, typed routes, testing navigation.
- [references/testing-release.md](references/testing-release.md): widget, golden and integration tests, mocktail, lints, release builds, flavors, signing, obfuscation and secrets handling.
- Official docs: https://docs.flutter.dev/ , https://dart.dev/ , https://riverpod.dev/ , https://bloclibrary.dev/ , https://pub.dev/packages/go_router , https://pub.dev/packages/pigeon , https://pub.dev/packages/flutter_secure_storage , https://pub.dev/packages/mocktail , https://docs.flutter.dev/release/breaking-changes
