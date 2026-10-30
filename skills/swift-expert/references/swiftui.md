# SwiftUI

SwiftUI guidance absorbed from the former swiftui-expert skill. Verified against Swift 6.4.2, Xcode 27.2 and the iOS 27 SDK (2026-10). Examples assume an iOS 17+ deployment target (`@Observable`, `ContentUnavailableView`); APIs that need a newer OS are marked. Check the availability annotations in the current SDK before raising or lowering a deployment target.

## 1. State ownership

| Need | Use |
|---|---|
| Transient value owned by one view | `@State private var isExpanded = false` |
| `@Observable` model owned by a view | `@State private var model = Model()` |
| Read/write access to a parent's value | `@Binding var value: String` |
| Bindings into an `@Observable` model passed in | `@Bindable var model: Model` |
| Shared model injected down the tree | `.environment(model)` and `@Environment(Model.self) private var model` |
| Configuration values (theme, feature flags) | `EnvironmentValues` entry declared with `@Entry` |
| Legacy `ObservableObject` code | `@StateObject` (owner), `@ObservedObject` (passed in), `@EnvironmentObject` |

- Mark observable models `@MainActor @Observable final class`. Views only re-evaluate when a property they actually read changes.
- `@State` initial values are created every time the view's initializer runs, but only the first instance is kept. Keep model initializers cheap; do work in `.task`, not `init`.
- Do not mix `ObservableObject` and `@Observable` for the same model; migrate a model and its call sites together.

```swift
import SwiftUI

extension EnvironmentValues {
    @Entry var showsDebugInfo: Bool = false
}

struct ProfileForm: View {
    @Bindable var profile: ProfileModel

    var body: some View {
        Form {
            TextField("Name", text: $profile.name)
                .textContentType(.name)
            Toggle("Newsletter", isOn: $profile.wantsNewsletter)
        }
    }
}

@MainActor
@Observable
final class ProfileModel {
    var name = ""
    var wantsNewsletter = false
}
```

## 2. Navigation

Use `NavigationStack` with a typed path owned by a router model, and `NavigationSplitView` for multi-column layouts on iPad and Mac. `NavigationView` is deprecated.

```swift
import SwiftUI

enum Route: Hashable {
    case article(id: String)
    case author(id: String)
}

@MainActor
@Observable
final class Router {
    var path: [Route] = []

    func open(_ route: Route) { path.append(route) }
    func popToRoot() { path.removeAll() }
}

struct RootView: View {
    @State private var router = Router()
    let repository: ArticleRepository

    var body: some View {
        NavigationStack(path: $router.path) {
            ArticleListView()
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .article(let id):
                        ArticleDetailView(id: id, repository: repository)
                    case .author(let id):
                        AuthorView(id: id)
                    }
                }
        }
        .environment(router)
    }
}
```

- Child views call `router.open(.article(id:))` via `@Environment(Router.self)`.
- Deep links parse into `[Route]` and assign `router.path`; validate identifiers from URLs before using them.
- Present sheets with `.sheet(item:)` bound to an optional identifiable value; use `presentationDetents` for partial-height sheets.

## 3. Lists and identity

- `ForEach` and `List` need stable identity: `Identifiable` models or `id: \.stableKey`. Never `ForEach(items.indices, id: \.self)` for mutable collections; insertions shift identities and break animations and state.
- Conditional branches (`if`/`else`) create different identities; use modifiers (`.opacity`, `.disabled`) when the same view should persist.
- Long scrolling content uses `List` or `LazyVStack`/`LazyVGrid`; eager `VStack` inside `ScrollView` builds every row up front.
- Pull to refresh: `.refreshable { await model.refresh() }`.

## 4. Side effects

- `body` must be cheap and side-effect free; it runs often.
- `.task { }` starts work when the view appears and cancels it when it disappears; `.task(id:)` restarts when the id changes.
- `.onChange(of:)` reacts to value changes; prefer deriving state over chaining many `onChange` handlers.
- Event handlers (`Button` actions) that need async work start `Task { await model.action() }`; the task inherits the main actor.

## 5. Animation

- Explicit: `withAnimation(.snappy) { isExpanded.toggle() }`. Implicit: `.animation(.default, value: isExpanded)`, always with the `value:` parameter.
- `transition(_:)` animates insertion and removal; `matchedGeometryEffect` links views across branches; `navigationTransition(.zoom(sourceID:in:))` with `matchedTransitionSource(id:in:)` gives zoom pushes (iOS 18+).
- `phaseAnimator` and `keyframeAnimator` for multi-step motion (iOS 17+).
- Respect `@Environment(\.accessibilityReduceMotion)`: replace movement with fades or no animation.

## 6. Accessibility

- Icon-only buttons need `.accessibilityLabel`; decorative images use `Image(decorative:)` or `.accessibilityHidden(true)`.
- Group composite rows with `.accessibilityElement(children: .combine)`; add traits with `.accessibilityAddTraits(.isHeader)`.
- Use text styles (`.font(.body)`) so Dynamic Type works; test at accessibility sizes and switch stacks to vertical with `ViewThatFits` or `dynamicTypeSize` checks.
- `accessibilityIdentifier` is for UI tests only; never put personal data in labels or identifiers.

## 7. Charts, widgets and intents

```swift
import SwiftUI
import Charts

struct DailyViews: Identifiable {
    let date: Date
    let views: Int
    var id: Date { date }
}

struct ViewsChart: View {
    let data: [DailyViews]

    var body: some View {
        Chart(data) { point in
            LineMark(x: .value("Date", point.date, unit: .day), y: .value("Views", point.views))
            AreaMark(x: .value("Date", point.date, unit: .day), y: .value("Views", point.views))
                .foregroundStyle(.linearGradient(colors: [.blue.opacity(0.3), .clear], startPoint: .top, endPoint: .bottom))
        }
        .frame(height: 200)
        .accessibilityLabel("Daily article views")
    }
}
```

- WidgetKit widgets use a `TimelineProvider` (or `AppIntentTimelineProvider` for configurable widgets); timelines are budgeted by the system, so widgets are not real-time.
- App Intents expose actions to Shortcuts, Siri and Spotlight; keep `perform()` fast and share logic with the app through a package.

## 8. Previews

```swift
#Preview("Profile form") {
    @Previewable @State var profile = ProfileModel()
    ProfileForm(profile: profile)
}
```

Provide previews for light and dark appearance, a large Dynamic Type size and a right-to-left locale on critical screens. Previews use stub repositories, never live services.

## 9. Performance

- Split large views so state reads are local; a parent that reads a frequently changing value re-evaluates its whole body.
- Avoid `AnyView`; use `@ViewBuilder`, `Group` or generic views to keep structural identity.
- Precompute sorting, filtering and formatting in the model, not in `body`.
- `Self._printChanges()` (debug only) prints why a view body re-evaluated; the SwiftUI instrument shows update counts and long view bodies.
- Use `.drawingGroup()` only for complex vector compositions that profiling shows are expensive.
- Images: size and downsample before display; `AsyncImage` has no persistent cache, so use a caching loader for feeds.

## 10. Testing

- Unit-test `@Observable` models directly (`@MainActor @Test`), calling intent methods and asserting `state`.
- UI flows: XCUITest with `accessibilityIdentifier`; pass launch arguments that swap in stub services.
- Visual regressions: snapshot testing (for example the open-source swift-snapshot-testing package) across appearance and Dynamic Type sizes.

## 11. Common mistakes

- Creating the model inside `body` or as a plain `let` property: state resets on every parent update. Own it with `@State`.
- `@ObservedObject` for an object the view creates: it is recreated with the view. Use `@StateObject` or migrate to `@Observable` with `@State`.
- Index-based identity in `ForEach`.
- Network calls in `onAppear` without cancellation: repeated appearances start duplicate requests. Use `.task`.
- `.animation(.default)` without `value:`: deprecated and animates unrelated changes.
