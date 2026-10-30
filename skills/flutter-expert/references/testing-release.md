# Testing, Linting and Release Builds

Reference for Flutter 3.47 (Dart 3.13), flutter_test, integration_test, mocktail 1.0.5, flutter_lints 6.0.0, flutter_secure_storage 11.2.0 and the `flutter build` commands (2026-10). Open this file when writing widget, golden or integration tests, configuring lints, or producing signed, obfuscated release builds.

## Contents

1. [Test layers](#1-test-layers)
2. [Widget tests](#2-widget-tests)
3. [mocktail](#3-mocktail)
4. [Golden tests](#4-golden-tests)
5. [Integration tests](#5-integration-tests)
6. [Lints and analysis options](#6-lints-and-analysis-options)
7. [Release builds](#7-release-builds)
8. [Android signing and flavors](#8-android-signing-and-flavors)
9. [Obfuscation and symbols](#9-obfuscation-and-symbols)
10. [Secrets and secure storage](#10-secrets-and-secure-storage)

## 1. Test layers

| Layer | Location | Command | Use for |
|---|---|---|---|
| Unit | `test/` | `flutter test` | Pure Dart: repositories, parsers, notifiers, blocs |
| Widget | `test/` | `flutter test` | Rendering, taps, text entry, state-driven UI, without a device |
| Golden | `test/` with `goldens/` | `flutter test --update-goldens` to regenerate | Pixel regression of key components |
| Integration | `integration_test/` | `flutter test integration_test -d <device>` | Full app flows on an emulator, simulator or device |

Useful flags: `--coverage` (writes `coverage/lcov.info`), `--plain-name "text"` or `--name regexp` to select tests, `--tags` and `--exclude-tags` with `@Tags(['golden'])` on a library.

## 2. Widget tests

```dart
testWidgets('form shows an error for an empty email', (tester) async {
  await tester.pumpWidget(const MaterialApp(home: Scaffold(body: SignInForm())));

  await tester.tap(find.byKey(const Key('submit')));
  await tester.pump();                      // one frame; use pumpAndSettle() to wait for animations

  expect(find.text('Email is required'), findsOneWidget);

  await tester.enterText(find.byType(TextFormField).first, 'a@example.com');
  await tester.pump();
  expect(find.text('Email is required'), findsNothing);
});
```

- `pump(Duration)` advances the fake clock; `pumpAndSettle()` times out on infinite animations (use `pump` with durations for spinners).
- Set the surface size with `tester.view.physicalSize` and `devicePixelRatio`, and `addTearDown(tester.view.reset)`.

## 3. mocktail

mocktail needs no code generation.

```dart
class MockAuthApi extends Mock implements AuthApi {}
class FakeCredentials extends Fake implements Credentials {}

void main() {
  setUpAll(() => registerFallbackValue(FakeCredentials()));

  test('signs in and stores the session', () async {
    final api = MockAuthApi();
    when(() => api.signIn(any())).thenAnswer((_) async => Session('token-from-test'));

    final result = await SignIn(api).call(Credentials('a@example.com', 'pw'));

    expect(result.isSuccess, isTrue);
    verify(() => api.signIn(any())).called(1);
  });
}
```

- Stubbing uses closures: `when(() => mock.method(args))`; a tear-off works for no-argument methods (`when(repo.fetchAll)`).
- `registerFallbackValue` is required for custom types used with `any()` or `captureAny()`; `Fake` classes implement only what is called.

## 4. Golden tests

```dart
testWidgets('product card matches golden', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal)),
      home: const Scaffold(body: Center(child: ProductCard(name: 'Sample'))),
    ),
  );
  await expectLater(find.byType(ProductCard), matchesGoldenFile('goldens/product_card.png'));
});
```

- Refresh images with `flutter test --update-goldens`; review the PNG diff in the pull request.
- Golden pixels depend on the platform and fonts. Generate and compare on one OS and Flutter version in CI (a pinned Linux runner), and tag golden tests so they can be skipped locally.

## 5. Integration tests

```dart
// integration_test/app_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:my_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('sign in shows the home screen', (tester) async {
    app.main();
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('email')), 'test@example.com');
    await tester.tap(find.byKey(const Key('submit')));
    await tester.pumpAndSettle();

    expect(find.text('Home'), findsOneWidget);
  });
}
```

- Add `integration_test` under `dev_dependencies` with `sdk: flutter`.
- Point the app at a test backend or inject fakes at the entry point so tests are deterministic and never touch production or real credentials.

## 6. Lints and analysis options

New projects include `flutter_lints` 6.0.0 as a dev dependency. Pure Dart packages use `package:lints/recommended.yaml` (`lints` 6.1.0) instead.

```yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"
    - build/**

linter:
  rules:
    always_use_package_imports: true
    avoid_print: true
    unawaited_futures: true
    prefer_final_locals: true
    use_build_context_synchronously: true
    cancel_subscriptions: true
    close_sinks: true
```

- `flutter analyze` reports; `dart fix --dry-run` and `dart fix --apply` apply automated fixes, including deprecation migrations such as `withOpacity` to `withValues`.

## 7. Release builds

| Target | Command | Notes |
|---|---|---|
| Play Store | `flutter build appbundle --release` | Output `build/app/outputs/bundle/release/app-release.aab`; upload to Play Console |
| Android APK | `flutter build apk --release --split-per-abi` | For direct distribution and testing |
| App Store | `flutter build ipa --release` | macOS with Xcode only; code signing set up in Xcode; check `flutter build ipa --help` for export options |

Common flags (confirmed in `flutter build appbundle --help`): `--build-name`, `--build-number`, `--flavor`, `-t <entry.dart>`, `--obfuscate`, `--split-debug-info=<dir>`, `-D`/`--dart-define=KEY=value`, `--dart-define-from-file=<file.json|.env>`, `--[no-]tree-shake-icons`, `--[no-]analyze-size`, `--target-platform`.

Before upload: bump the version, sign with the release key (not debug), check application ID, flavor and permissions, archive symbols, and smoke test the release artifact on a physical device.

## 8. Android signing and flavors

Keep `android/key.properties` out of git (the generated `android/.gitignore` already lists it and `**/*.jks`). The template signs release builds with the debug key until you add a release config.

```properties
# android/key.properties  (never committed; CI creates it from secrets)
storeFile=/secure/path/upload-keystore.jks
keyAlias=upload
storePassword=<from the secret store>
keyPassword=<from the secret store>
```

```kotlin
// android/app/build.gradle.kts
import java.util.Properties

val keystoreProperties = Properties().apply {
    val file = rootProject.file("key.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties.getProperty("keyAlias")
            keyPassword = keystoreProperties.getProperty("keyPassword")
            storeFile = keystoreProperties.getProperty("storeFile")?.let { file(it) }
            storePassword = keystoreProperties.getProperty("storePassword")
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }

    flavorDimensions += "env"
    productFlavors {
        create("dev") {
            dimension = "env"
            applicationIdSuffix = ".dev"
            resValue("string", "app_name", "MyApp Dev")
        }
        create("prod") {
            dimension = "env"
            resValue("string", "app_name", "MyApp")
        }
    }
}
```

- Run flavors with `flutter run --flavor dev -t lib/main_dev.dart`; build with `--flavor prod -t lib/main_prod.dart`.
- iOS flavors need Xcode build configurations and schemes named after the flavor (for example `Debug-dev`, `Release-prod`, scheme `dev`); `--flavor` selects the scheme.

## 9. Obfuscation and symbols

```bash
flutter build appbundle --release \
  --obfuscate --split-debug-info=build/symbols/1.4.0+23
```

- `--obfuscate` requires `--split-debug-info`; the symbol files map obfuscated names back to the source.
- Archive the directory for every released version (artifact storage, crash reporter upload). Without it stack traces cannot be decoded.
- Decode a trace: `flutter symbolize -i crash_trace.txt -d build/symbols/1.4.0+23` (or `-d` pointing to a single symbol file).
- Obfuscation renames Dart identifiers only; strings, assets and URLs stay visible. It is a speed bump, not protection for secrets.

## 10. Secrets and secure storage

Facts to apply:

- `--dart-define` and `--dart-define-from-file` values are compiled into the app as constants. They are fine for non-secret configuration (base URL, feature flags, public client IDs) and unsafe for secrets, because the binary can be unpacked and the strings extracted.
- Keep third-party API secrets on your server and expose a narrow endpoint that the app calls with the user's token.

User tokens go in `flutter_secure_storage` (11.2.0), which uses Android Keystore-backed encryption and the iOS/macOS Keychain:

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _storage = FlutterSecureStorage();

Future<void> saveRefreshToken(String token) =>
    _storage.write(key: 'refresh_token', value: token);

Future<String?> readRefreshToken() => _storage.read(key: 'refresh_token');

Future<void> clearSession() => _storage.deleteAll();
```

- Keep access tokens in memory, only the refresh token on disk; delete both on sign-out.
- Version 11 removed legacy Android ciphers and raised the Android minSdk to 24; if an app upgrades from a release older than v10, upgrade to v10 first so existing data migrates (see the package changelog; `checkUpgradeStatus()` reports data lost on a direct major upgrade).
