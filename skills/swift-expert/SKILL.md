---
name: swift-expert
description: >-
  Writes, reviews and migrates Swift 6 code for Apple platforms: strict concurrency (actors, Sendable, MainActor, async/await), SwiftUI, UIKit, Codable networking, Keychain storage, Swift Testing and Instruments-driven performance work. Use when working on iOS, iPadOS, macOS, watchOS, tvOS or visionOS apps and Swift packages: .swift files, Package.swift, Xcode projects, SwiftUI views and @Observable models, UIKit view controllers, diffable data sources, Auto Layout, Swift 6 language-mode migration or data-race diagnostics. Not for Android or Kotlin (use android-expert); not for React or web front ends (use senior-react-19-engineer).
license: MIT
metadata:
  version: "3.0.0"
---

# Swift Expert

This skill covers production Swift on Apple platforms: the language, Swift 6 data-race safety, app architecture, SwiftUI and UIKit, networking, persistence of secrets, testing and profiling. SwiftUI and UIKit details live in the reference files. It does not cover Android, Kotlin, Kotlin Multiplatform UI or cross-platform frameworks such as React Native and Flutter.

> Verified against Swift 6.4 (bundled with Xcode 27.1, iOS 27 SDK), with concurrency features from Swift 6.2 (SE-0461, SE-0466) and 6.4 (SE-0493) (2026-10).

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

- Swift language: value types, enums with payloads, protocols, generics (`some` / `any`, primary associated types), result builders, property wrappers, macros, typed throws.
- Swift 6 language mode: `Sendable`, actor isolation, `@MainActor`, region-based isolation, migration from Swift 5 mode.
- Structured concurrency: `async`/`await`, task groups, `AsyncSequence`/`AsyncStream`, cancellation, continuations for callback APIs.
- App architecture for SwiftUI and UIKit apps, Swift packages and modularization.
- Networking with `URLSession` and `Codable`; secrets and tokens with the Keychain and a backend.
- Testing with Swift Testing and XCTest/XCUITest; profiling with Instruments.
- UI frameworks: [references/swiftui.md](references/swiftui.md) and [references/uikit.md](references/uikit.md).

## 2. Core Expertise

- **Isolation model.** Every declaration is isolated to an actor (`@MainActor`, a custom `actor`) or is `nonisolated`. Values that cross isolation boundaries must be `Sendable` or be proven disconnected by region-based isolation.
- **Approachable concurrency (Swift 6.2+).** The compiler flag `-default-isolation MainActor` or the SwiftPM setting `.defaultIsolation(MainActor.self)` makes unannotated code main-actor isolated (SE-0466). The upcoming feature `NonisolatedNonsendingByDefault` makes nonisolated async functions run on the caller's actor; `@concurrent` explicitly moves a function to the global concurrent executor (SE-0461). New Xcode app templates enable these settings, so check the target's build settings before reasoning about where code runs.
- **Swift 6.4 additions.** `await` inside `defer` (SE-0493), `withTaskCancellationShield` for cleanup that must not be cancelled, the `@diagnose` attribute for per-source warning control, Subprocess 1.0, and Swift Testing / XCTest interoperability.
- **Structured concurrency.** Child tasks (`async let`, `withTaskGroup`, `withThrowingTaskGroup`) inherit cancellation and propagate errors. `Task {}` is unstructured: it inherits the current actor and priority but must be stored and cancelled by its owner. `Task.detached` inherits nothing and is rarely right.
- **Actors.** Serialize access to mutable state. Actor methods are reentrant: state can change across any `await`, so re-check invariants after suspension points.
- **Generics.** Prefer `some Protocol` (static dispatch, specialization) and use `any Protocol` only where heterogeneity is required (stored dependencies, mixed collections).
- **Errors.** `throws(SomeError)` (typed throws) for closed error sets in leaf code; untyped `throws` at module boundaries where errors evolve.
- **Memory.** ARC; `weak` for back-references and delegates, `unowned` only where the lifetime is guaranteed. Escaping closures stored by `self` must not capture `self` strongly.
- **Codable.** `JSONDecoder` strategies (`keyDecodingStrategy`, `dateDecodingStrategy`), explicit `CodingKeys`, custom `init(from:)` for lenient or versioned payloads.

## 3. Workflow

1. Read the target's settings first: Swift language mode, default actor isolation, upcoming features enabled, deployment target. The same code compiles differently under different settings.
2. Model the domain as `Sendable` value types (`struct`, `enum`) with no UIKit or SwiftUI imports.
3. Decide isolation per type: UI state on `@MainActor`, shared mutable non-UI state in an `actor`, stateless services as `Sendable` structs.
4. Design async APIs: `async` functions for one-shot results, `AsyncSequence` for streams, cancellation checked in long loops (`try Task.checkCancellation()`).
5. Wrap callback or delegate APIs once, with `withCheckedThrowingContinuation` (resume exactly once) or `AsyncStream` with `onTermination` cleanup.
6. Build the UI layer (SwiftUI or UIKit) against the models; keep side effects out of view construction.
7. Write Swift Testing tests for domain and model logic, XCUITest for critical flows; run with Thread Sanitizer on.
8. Profile with Instruments (Time Profiler, Allocations, Leaks, Swift Concurrency, SwiftUI) before optimizing.
9. When migrating to Swift 6 mode: enable complete checking module by module, fix diagnostics at the root (isolation of the type) instead of sprinkling `@unchecked Sendable` or `nonisolated(unsafe)`.

## 4. Decision Rules

- **`@MainActor` class vs `actor`.** UI-facing state belongs on the main actor; background shared state (caches, sessions, file access) belongs in an `actor`. An `actor` for UI state forces `await` on every read from the view.
- **`Task {}` vs task group vs `async let`.** Fixed number of parallel calls: `async let`. Dynamic fan-out: task group. Bridging from synchronous UI events: `Task {}` owned by the caller, or SwiftUI `.task`.
- **`@concurrent` vs default.** Mark CPU-heavy or blocking async work `@concurrent` so it leaves the caller's actor; leave ordinary async functions to inherit the caller's isolation.
- **`some` vs `any`.** Return and parameter positions: `some`. Stored heterogeneous dependencies or collections: `any`.
- **`weak` vs `unowned`.** Default to `weak`; `unowned` only when the referenced object provably outlives the reference.
- **Typed throws vs untyped.** Typed throws for internal leaf functions with a stable, closed error set; untyped at public API boundaries.
- **`AsyncStream` vs Combine.** New streaming code uses `AsyncSequence`; Combine is for existing pipelines and frameworks that still publish with it.
- **SwiftUI vs UIKit.** New screens default to SwiftUI; use UIKit for features SwiftUI lacks or for large existing UIKit codebases, bridging with `UIHostingController` / `UIViewRepresentable`.
- **Checked vs unsafe continuation.** Always `withChecked…Continuation`; the unsafe variant only after profiling proves the check matters.

## 5. Coding Standards

- Swift 6 language mode for new targets; warnings treated as errors in CI.
- `struct` and `enum` by default; `final class` when reference identity or inheritance from a framework class is needed.
- Naming follows the Swift API Design Guidelines: types `UpperCamelCase`, everything else `lowerCamelCase`, no `I`/`k` prefixes, Boolean properties read as assertions (`isLoading`, `hasMore`), argument labels that read as phrases.
- One primary type per file named after it; extensions as `Type+Feature.swift`.
- No force unwraps (`!`) or `try!` in production paths; `guard let` / `if let` and explicit error handling. `fatalError` only for programmer errors that tests would catch.
- `@unchecked Sendable` and `nonisolated(unsafe)` require a comment stating the synchronization that makes them safe.
- Access control is explicit at module boundaries: `public` API is deliberate; everything else `internal` or `private`.
- `///` documentation for public API, including `- Parameter`, `- Returns`, `- Throws`.
- Log with `os.Logger`; interpolate user data with `privacy: .private`.
- SwiftLint or swift-format in CI with a checked-in configuration.

## 6. Project Structure

```
MyApp/
├── MyApp.xcodeproj
├── App/                         # app target: @main entry, scene setup, composition root
├── Packages/
│   └── ArticlesKit/             # local Swift package
│       ├── Package.swift
│       ├── Sources/
│       │   ├── ArticlesCore/    # domain models, repositories, networking (no UI imports)
│       │   └── ArticlesUI/      # SwiftUI views and @Observable models
│       └── Tests/
│           └── ArticlesCoreTests/
├── Widgets/                     # WidgetKit extension target
├── UITests/                     # XCUITest target
└── Config/                      # .xcconfig files (no secrets)
```

Local packages give fast incremental builds, enforced module boundaries and test targets that run without the simulator for pure logic.

## 7. Design Patterns

- **Repository actor.** An `actor` wraps network and cache access, deduplicates in-flight requests and exposes `async` methods returning `Sendable` values (Example 1).
- **Observable model.** `@MainActor @Observable final class` owns screen state as an enum (`loading`, `loaded`, `failed`) and exposes intent methods; views render state and call methods (Example 2).
- **Dependency injection by initializer.** Pass protocols (`any HTTPClient`) into initializers; a composition root in the app target wires concrete types. No singletons for mutable state.
- **Continuation bridge.** Wrap each callback API once in an `async` function; resume exactly once on every path, including cancellation.
- **AsyncStream adapter.** Delegate-based sources (location, Bluetooth, notifications) become `AsyncStream` with `continuation.onTermination` stopping the source.
- **Coordinator / router.** UIKit apps use coordinators owning navigation controllers; SwiftUI apps use a typed `NavigationStack` path owned by a router model.

## 8. Best Practices

- Keep `@MainActor` work short; move parsing, image decoding and disk I/O into `@concurrent` functions or actors.
- Store unstructured tasks you create and cancel them when their owner goes away; prefer SwiftUI `.task` / `.task(id:)`, which cancel automatically.
- After every `await` inside an actor, re-validate assumptions (reentrancy).
- Decode network payloads into DTOs and map to domain models; the UI never sees transport types.
- Configure `JSONDecoder` explicitly; pick either `convertFromSnakeCase` or explicit `CodingKeys` raw values for a type, not both.
- Use `Duration` and `Clock` (`ContinuousClock`, `Task.sleep(for:)`) instead of `TimeInterval` arithmetic in async code; inject the clock for tests.
- Use `os.Logger` signposts (`OSSignposter`) around expensive operations to see them in Instruments.
- Keep `Info.plist` and `.xcconfig` free of secrets; they ship inside the app bundle.

## 9. Performance

- Measure first: Time Profiler for CPU, Allocations and Leaks for memory, Swift Concurrency instrument for actor contention and task counts, Hangs for main-thread stalls.
- Value types avoid reference counting traffic but large structs copied in hot loops cost; use `borrowing`/`consuming` parameters or classes where profiling shows copies.
- `some` and generics allow specialization; `any` adds existential boxing and dynamic dispatch in hot paths.
- `final` classes and `private` members enable devirtualization; Whole Module Optimization is the release default.
- `InlineArray` and `Span` (Swift 6.2+) avoid heap allocation and bounds-check overhead for fixed-size and contiguous data in performance-critical code.
- Avoid actor hopping in tight loops: batch work inside one isolation domain.
- Cache formatters (`Date.FormatStyle` values are cheap; legacy `DateFormatter` instances are not).

## 10. Security

- **App binaries are not a secret store.** Anything in source, `Info.plist`, `.xcconfig`, asset catalogs or the compiled binary can be extracted from the IPA. Never ship third-party API keys or signing secrets in the app.
- **Backend token exchange.** The app authenticates the user (Sign in with Apple, or OAuth via `ASWebAuthenticationSession` with PKCE) against your backend; the backend holds third-party credentials, calls the third-party API or mints short-lived scoped tokens, and enforces rate limits. App Attest (`DCAppAttestService`) can raise the bar against modified clients.
- **Keychain for user tokens.** Store access and refresh tokens with `SecItem*` APIs and an accessibility class such as `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` (Example 3). Never `UserDefaults`, plist files or plain files.
- Keep App Transport Security on; no `NSAllowsArbitraryLoads`. Certificate or public-key pinning only with a rotation plan.
- Use `CryptoKit` for hashing, signing and symmetric encryption; never custom cryptography.
- Validate server responses (status codes, schema) and treat deep links and universal-link parameters as untrusted input.
- Redact tokens and personal data in logs (`privacy: .private`), crash reports and analytics.
- Use `SecureField` / `isSecureTextEntry` and the correct `textContentType` so password managers work.

## 11. Testing

- Swift Testing for new tests: `@Test`, `#expect`, `#require`, parameterized arguments, traits (`.timeLimit`, `.tags`). Swift 6.4 lets `XCTAssert` and `#expect` work across both frameworks, so suites can migrate incrementally.
- Tests run in parallel by default; shared mutable fixtures must be isolated per test.
- Inject protocols (`HTTPClient`, clocks, stores) and use stubs or fakes; no real network in unit tests.
- Test `@MainActor` models from `@MainActor` test functions; await their async methods directly.
- Test cancellation paths explicitly: start a task, cancel it, assert the state.
- XCUITest for end-to-end flows using `accessibilityIdentifier`; launch arguments switch the app to stubbed services.
- Run with Thread Sanitizer and Address Sanitizer in CI schemes; turn on Main Thread Checker.

```swift
import Foundation
import Testing
@testable import ArticlesCore

struct StubClient: HTTPClient {
    let article: Article

    func get<T: Decodable & Sendable>(_ type: T.Type, from url: URL) async throws -> T {
        guard let value = article as? T else { throw NetworkError.invalidResponse }
        return value
    }
}

@Test func returnsArticleFromClient() async throws {
    let article = Article(id: "a1", title: "Hello", publishedAt: .now)
    let repository = ArticleRepository(
        client: StubClient(article: article),
        baseURL: try #require(URL(string: "https://api.example.com"))
    )
    let loaded = try await repository.article(id: "a1")
    #expect(loaded == article)
}
```

## 12. Review Checklist

- [ ] Language mode, default isolation and upcoming features are known for each target.
- [ ] Shared mutable state lives in an actor or on `@MainActor`; no ad-hoc locks around class properties without justification.
- [ ] Every `@unchecked Sendable` / `nonisolated(unsafe)` has a comment naming its synchronization.
- [ ] Unstructured `Task`s are owned and cancelled; no `Task.detached` without a reason.
- [ ] Actor methods re-check state after `await`.
- [ ] Continuations resume exactly once on every path.
- [ ] Escaping closures stored by `self` capture it `weak`; delegates are `weak`.
- [ ] No force unwraps or `try!` in production paths.
- [ ] Decoder strategies and `CodingKeys` do not conflict.
- [ ] No secrets in source, `Info.plist`, `.xcconfig` or assets; tokens in the Keychain.
- [ ] Logs redact personal data and tokens.
- [ ] New logic has Swift Testing coverage; critical flows have UI tests.
- [ ] Refactors keep behavior: tests green before and after, one mechanical change at a time (e.g. GCD to async/await, `ObservableObject` to `@Observable`).

## 13. Production Notes

- Upload dSYMs to the crash reporter for every build; without them stack traces are unreadable.
- MetricKit (`MXMetricManager`) delivers hang, launch, memory and diagnostic payloads from the field; Xcode Organizer shows the aggregated metrics.
- Use `OSSignposter` intervals around launch and key interactions to compare builds.
- Phased release in App Store Connect limits blast radius; server-side feature flags let you disable a feature without a new binary.
- Privacy manifests (`PrivacyInfo.xcprivacy`) must declare required-reason API use and data collection for the app and bundled SDKs; check current App Store requirements before submission.

## 14. Examples

### Example 1: Repository actor with request deduplication

```swift
import Foundation

struct Article: Sendable, Hashable, Identifiable, Decodable {
    let id: String
    let title: String
    let publishedAt: Date
}

enum NetworkError: Error {
    case invalidResponse
    case status(Int)
}

protocol HTTPClient: Sendable {
    func get<T: Decodable & Sendable>(_ type: T.Type, from url: URL) async throws -> T
}

struct URLSessionHTTPClient: HTTPClient {
    let session: URLSession

    func get<T: Decodable & Sendable>(_ type: T.Type, from url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse else { throw NetworkError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw NetworkError.status(http.statusCode) }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase   // published_at -> publishedAt
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(T.self, from: data)
    }
}

actor ArticleRepository {
    private let client: any HTTPClient
    private let baseURL: URL
    private var cache: [String: Article] = [:]
    private var inFlight: [String: Task<Article, any Error>] = [:]

    init(client: any HTTPClient, baseURL: URL) {
        self.client = client
        self.baseURL = baseURL
    }

    func article(id: String) async throws -> Article {
        if let cached = cache[id] { return cached }
        if let running = inFlight[id] { return try await running.value }

        let url = baseURL.appending(path: "articles").appending(path: id)
        let task = Task { [client] in try await client.get(Article.self, from: url) }
        inFlight[id] = task
        defer { inFlight[id] = nil }

        let article = try await task.value
        cache[id] = article          // re-entrancy safe: written after the await completes
        return article
    }
}
```

In an app target that uses `-default-isolation MainActor`, mark `Article`, `NetworkError`, `URLSessionHTTPClient` and other non-UI types `nonisolated` (SE-0449) so they and their conformances are not pinned to the main actor.

### Example 2: Observable model driven by `.task(id:)`

```swift
import SwiftUI
import Observation

@MainActor
@Observable
final class ArticleDetailModel {
    enum State {
        case loading
        case loaded(Article)
        case failed(String)
    }

    private(set) var state: State = .loading
    private let repository: ArticleRepository

    init(repository: ArticleRepository) {
        self.repository = repository
    }

    func load(id: String) async {
        state = .loading
        do {
            state = .loaded(try await repository.article(id: id))
        } catch {
            guard !Task.isCancelled else { return }   // view went away or id changed
            state = .failed("The article could not be loaded.")
        }
    }
}

struct ArticleDetailView: View {
    let id: String
    @State private var model: ArticleDetailModel

    init(id: String, repository: ArticleRepository) {
        self.id = id
        _model = State(initialValue: ArticleDetailModel(repository: repository))
    }

    var body: some View {
        Group {
            switch model.state {
            case .loading:
                ProgressView()
            case .loaded(let article):
                Text(article.title).font(.title)
            case .failed(let message):
                ContentUnavailableView {
                    Label("Unavailable", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(message)
                } actions: {
                    Button("Retry") { Task { await model.load(id: id) } }
                }
            }
        }
        .task(id: id) { await model.load(id: id) }
    }
}
```

### Example 3: Keychain token store

```swift
import Foundation
import Security

enum KeychainError: Error {
    case unexpectedStatus(OSStatus)
}

struct TokenStore: Sendable {
    let service: String

    func save(_ token: Data, account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: token,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        var status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            let item = query.merging(attributes) { _, new in new }
            status = SecItemAdd(item as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw KeychainError.unexpectedStatus(status) }
    }

    func read(account: String) throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw KeychainError.unexpectedStatus(status) }
        return result as? Data
    }

    func delete(account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unexpectedStatus(status)
        }
    }
}
```

The token stored here is the user's session token issued by your backend after sign-in, never a third-party API key.

## 15. Common Mistakes

- **Secrets in `Info.plist`, `.xcconfig` or source.** They are readable in the shipped bundle. Move third-party keys to a backend and store only per-user tokens in the Keychain.
- **Silencing Swift 6 errors with `@unchecked Sendable` or `nonisolated(unsafe)`.** The race is still there. Fix isolation: make the type an actor, a `Sendable` value, or main-actor isolated.
- **Assuming where async code runs.** With `NonisolatedNonsendingByDefault` a nonisolated async function runs on the caller's actor, so heavy work called from the UI stays on the main actor unless marked `@concurrent`.
- **Ignoring actor reentrancy.** Checking a cache, awaiting, then writing can duplicate work or overwrite newer values. Store in-flight tasks or re-check after `await`.
- **Leaking unstructured tasks.** `Task {}` started in `init` or `viewDidLoad` and never cancelled keeps running after the screen is gone. Store and cancel it, or use `.task`.
- **Resuming a continuation twice or never.** Crashes or hangs the caller. Audit every callback path, including errors and cancellation.
- **`convertFromSnakeCase` plus snake_case `CodingKeys` raw values.** The strategy converts keys before matching, so `case authorId = "author_id"` no longer matches. Use one mechanism.
- **Strong `self` in stored escaping closures.** Retain cycles that Instruments Leaks shows; capture `[weak self]`.
- **`Task.detached` to "get off the main thread".** Loses priority, task-locals and cancellation; use `@concurrent` functions or an actor.
- **`any Protocol` everywhere.** Existential boxing and lost type information; return `some Protocol` where one concrete type is produced.
- **Blocking the main actor with `DispatchSemaphore` or synchronous I/O.** Causes hangs and watchdog terminations; make the call async.

## 16. References

- [references/swiftui.md](references/swiftui.md) - SwiftUI state ownership, navigation, lists, environment, animation, accessibility, previews, performance and testing.
- [references/uikit.md](references/uikit.md) - UIKit lifecycle, Auto Layout, diffable data sources with cell registrations, containment, custom transitions, image downsampling and SwiftUI interop.
