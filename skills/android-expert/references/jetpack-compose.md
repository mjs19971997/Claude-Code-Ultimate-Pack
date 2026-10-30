# Jetpack Compose

Reference for building Android UI with Jetpack Compose, absorbed from the former jetpack-compose-expert skill: state and effects, stability and recomposition, Material 3 theming, lazy lists, navigation, adaptive layouts, accessibility, animation and UI testing. Verified against Compose BOM 2026.09.00 (Compose UI 1.12.1, Material 3 1.4.0, Material 3 Adaptive 1.3.0), Navigation 3 1.2.0, Navigation 2.10.2, Lifecycle 2.11, Kotlin 2.4.21 and Android Gradle Plugin 9.5.0 (2026-10).

## 1. Setup

```kotlin
// app/build.gradle.kts (versions come from gradle/libs.versions.toml)
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)          // org.jetbrains.kotlin.plugin.compose, same version as Kotlin
}

android {
    buildFeatures { compose = true }
}

dependencies {
    val bom = platform(libs.androidx.compose.bom)
    implementation(bom)
    androidTestImplementation(bom)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.lifecycle.runtime.compose)   // collectAsStateWithLifecycle
    debugImplementation(libs.androidx.compose.ui.tooling)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
```

- The Compose compiler ships with Kotlin and is applied through the `org.jetbrains.kotlin.plugin.compose` Gradle plugin; there is no separate `kotlinCompilerExtensionVersion`.
- With AGP 9 the Kotlin Android plugin is built in; apply only the Compose compiler plugin on top.
- The BOM aligns all `androidx.compose.*` groups; do not put versions on Compose artifacts that the BOM manages. Libraries outside the BOM mapping (for example Navigation 3 and Material 3 Adaptive add-ons) keep their own versions in the catalog.

## 2. State

| Need | Use |
|---|---|
| Value that only matters to this composable | `remember { mutableStateOf(x) }` |
| Value that must survive rotation and process death | `rememberSaveable` (custom `Saver` for non-Bundle types) |
| Expensive computation from other state | `remember(key) { }` or `derivedStateOf` |
| Business or screen state | ViewModel exposing `StateFlow`, collected with `collectAsStateWithLifecycle()` |
| Compose state consumed by non-Compose code | `snapshotFlow { state }` |

- Hoist state to the lowest common parent that reads or writes it: state flows down as parameters, events flow up as lambdas. A stateless composable is previewable and testable.
- `derivedStateOf` is for state that changes more often than the derived result (for example `listState.firstVisibleItemIndex > 0`). Do not use it to wrap a cheap expression of a value that changes at the same rate.
- Prefer one immutable `UiState` per screen over many separate flows; map it to child composables with only the fields each needs.
- Use `mutableIntStateOf`, `mutableFloatStateOf` and `mutableLongStateOf` for primitives to avoid boxing.
- Read frequently changing state (scroll offset, animation values) as late as possible, preferably inside lambda-based modifiers (`Modifier.offset { }`, `graphicsLayer { }`, `drawBehind { }`) so only the layout or draw phase reruns, not composition.

```kotlin
@Composable
fun SearchField(
    query: String,
    onQueryChange: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        label = { Text("Search") },
        singleLine = true,
        modifier = modifier.fillMaxWidth(),
    )
}
```

## 3. Side effects

| API | Use for |
|---|---|
| `LaunchedEffect(key)` | Suspending work tied to the composition; restarts when `key` changes, cancelled on leaving |
| `rememberCoroutineScope()` | Launching coroutines from event handlers (clicks, gestures) |
| `DisposableEffect(key)` | Register and unregister listeners or observers; `onDispose { }` is mandatory |
| `SideEffect` | Publish Compose state to non-Compose code after every successful recomposition |
| `produceState` | Convert a non-Compose source into `State` |
| `rememberUpdatedState` | Let a long-running effect call the latest lambda without restarting |
| `snapshotFlow` | Observe Compose state as a Flow inside an effect |

```kotlin
@Composable
fun SnackbarOnError(
    errorMessage: String?,
    snackbarHostState: SnackbarHostState,
    onShown: () -> Unit,
) {
    val currentOnShown by rememberUpdatedState(onShown)
    LaunchedEffect(errorMessage) {
        if (errorMessage != null) {
            snackbarHostState.showSnackbar(errorMessage)
            currentOnShown()
        }
    }
}

@Composable
fun OnLifecycleStarted(onStart: () -> Unit) {
    val lifecycleOwner = LocalLifecycleOwner.current
    val currentOnStart by rememberUpdatedState(onStart)
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_START) currentOnStart()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
}
```

- Never start network calls, analytics or writes in the composable body; the body can run many times, in any order, and be abandoned.
- Do not pass `Unit` or `true` as a `LaunchedEffect` key when the effect depends on a parameter; the effect would keep using the first value.
- Do not collect flows with a bare `LaunchedEffect { flow.collect { } }` for UI state; use `collectAsStateWithLifecycle()` so collection stops when the app is in the background.

## 4. Stability and recomposition

- Since Kotlin 2.0.20 strong skipping is on by default: composables with unstable parameters are still skippable, comparing unstable parameters with instance equality (`===`) and stable ones with `equals()`. Lambdas with unstable captures are remembered automatically.
- Classes with `val` properties of stable types declared in a module built with the Compose compiler are inferred stable. A plain `List`, `Set` or `Map` is unstable, but under strong skipping it skips when the same instance is passed again.
- Prefer preserving instance identity (compute or cache the list in the ViewModel or with `remember`) over wrapping everything in `ImmutableList`. `ImmutableList` and `@Immutable`/`@Stable` models trigger an element-by-element `equals()` on every recomposition pass, which can cost more than recomposing in large lists.
- Use `@Stable` or `@Immutable` only for classes from modules the compiler cannot analyze (for example a pure Kotlin `core:model` module without the Compose plugin) and only when `equals()` is cheap. List stability exceptions for such types in a stability configuration file (`composeCompiler { stabilityConfigurationFiles.add(...) }`) rather than depending on Compose from the model module.
- Diagnose with compiler reports (`composeCompiler { reportsDestination.set(...); metricsDestination.set(...) }`), the Layout Inspector recomposition counts and a release-like build; debug builds are not representative.
- `@NonSkippableComposable` opts a composable out of skipping when it intentionally must rerun.

## 5. Lazy lists and layouts

```kotlin
@Composable
fun ArticleList(
    articles: List<Article>,
    onArticleClick: (ArticleId) -> Unit,
    modifier: Modifier = Modifier,
    listState: LazyListState = rememberLazyListState(),
) {
    LazyColumn(
        modifier = modifier,
        state = listState,
        contentPadding = PaddingValues(vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items(items = articles, key = { it.id.value }, contentType = { "article" }) { article ->
            ArticleCard(
                article = article,
                onClick = { onArticleClick(article.id) },
                modifier = Modifier.animateItem(),
            )
        }
    }
}
```

- Always give `items` a stable `key` (the database id, never the index) and a `contentType` for heterogeneous lists; keys also preserve scroll position and `rememberSaveable` state per item.
- Do not nest a vertically scrolling lazy list inside another vertical scroller with unbounded height; use one lazy container with multiple item types, or `LazyVerticalGrid`.
- Use slot APIs (`content: @Composable () -> Unit`, `leadingIcon: @Composable (() -> Unit)? = null`) for customizable components instead of many boolean parameters.
- Custom layouts: `Layout` or `Modifier.layout` for single-pass measurement; `SubcomposeLayout` only when a child's size is needed to decide what to compose, as it is costlier.
- Custom modifiers: implement `Modifier.Node` (with `ModifierNodeElement`); `Modifier.composed` is discouraged because it composes per use.

## 6. Material 3 theming

```kotlin
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> AppDarkColors
        else -> AppLightColors
    }
    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        shapes = AppShapes,
        content = content,
    )
}
```

- Read colors, type and shapes from `MaterialTheme.colorScheme`, `.typography` and `.shapes`; no hard-coded hex colors or fixed text sizes in screens. Typography uses `sp` so it follows the system font scale.
- Provide static `lightColorScheme(...)`/`darkColorScheme(...)` fallbacks for devices below Android 12 (API 31) and for brand-locked screens.
- Define extra design tokens (spacing, elevation) in a `CompositionLocal` created with `staticCompositionLocalOf` when they never change at runtime, `compositionLocalOf` otherwise. Keep `CompositionLocal` for ambient design values, not for business data or dependencies.
- Material 3 1.4.0 is the stable line in the BOM; newer Expressive components ship in the 1.5 pre-release line. Check the release notes and `@ExperimentalMaterial3ExpressiveApi` opt-in markers before adopting them.
- Edge-to-edge is enforced when targeting API 35 and above: call `enableEdgeToEdge()` in the activity, use `Scaffold` content padding, and apply `WindowInsets` (`safeDrawing`, `imePadding()`) so content is not obscured by system bars or the keyboard.

## 7. Navigation

Navigation 3 is the recommended library for new Compose apps: the back stack is a list of keys that the app owns, and `NavDisplay` renders it. Navigation 2 (`navigation-compose`) remains available for existing apps.

```kotlin
// Needs androidx.navigation3:navigation3-runtime, navigation3-ui, androidx.lifecycle:lifecycle-viewmodel-navigation3
// and the kotlinx.serialization plugin so keys can be saved across process death.
@Serializable
data object ArticleList : NavKey

@Serializable
data class ArticleDetail(val id: String) : NavKey

@Composable
fun AppNavigation() {
    val backStack = rememberNavBackStack(ArticleList)

    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryDecorators = listOf(
            rememberSaveableStateHolderNavEntryDecorator(),   // keeps rememberSaveable state per entry
            rememberViewModelStoreNavEntryDecorator(),        // scopes ViewModels to the entry
        ),
        entryProvider = entryProvider {
            entry<ArticleList> {
                ArticleListRoute(onArticleClick = { id -> backStack.add(ArticleDetail(id.value)) })
            }
            entry<ArticleDetail> { key ->
                ArticleDetailRoute(articleId = key.id)
            }
        },
    )
}
```

- Keys are `@Serializable` types implementing `NavKey`; `rememberNavBackStack` saves and restores them. Pass identifiers in keys, not whole objects.
- Navigate by mutating the back stack (`add`, `removeLastOrNull`); there is no `NavController`. Hilt `hiltViewModel()` inside an entry is scoped by the ViewModel store decorator.
- Adaptive scenes (list-detail, supporting pane) come from the `adaptive-navigation3` add-on; it was still in alpha at the time of writing, so check its status before relying on it.

Navigation 2 with type-safe routes (2.8 and later):

```kotlin
@Serializable data object Home
@Serializable data class Detail(val id: String)

@Composable
fun AppNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Home) {
        composable<Home> {
            HomeRoute(onOpen = { id -> navController.navigate(Detail(id)) })
        }
        composable<Detail> { entry ->
            val route = entry.toRoute<Detail>()
            DetailRoute(articleId = route.id)
        }
    }
}
```

- Validate every route argument and deep-link parameter in the destination's ViewModel before using it for queries or file access.
- Handle system back with `BackHandler` only when the screen has state to unwind; do not intercept back for navigation that the library already handles.

## 8. Adaptive layouts

Window size classes (width): compact below 600 dp, medium 600 to 839 dp, expanded 840 to 1199 dp, large 1200 to 1599 dp, extra-large from 1600 dp. Height: compact below 480 dp, medium 480 to 899 dp, expanded from 900 dp.

```kotlin
@Composable
fun AdaptiveShell(content: @Composable () -> Unit) {
    val windowSizeClass = currentWindowAdaptiveInfo().windowSizeClass
    val wide = windowSizeClass.isWidthAtLeastBreakpoint(WindowSizeClass.WIDTH_DP_MEDIUM_LOWER_BOUND)
    // Use the flag to choose a one-pane or two-pane layout.
    if (wide) TwoPaneLayout(content) else content()
}
```

- Decide layout from the window size class (not from device type or orientation); apps are resized in split-screen, desktop windows and on foldables.
- `NavigationSuiteScaffold` (artifact `material3-adaptive-navigation-suite`) switches between a bottom bar, a rail and a drawer by window size. `ListDetailPaneScaffold` and `SupportingPaneScaffold` (`material3-adaptive-layout`) provide the canonical list-detail and supporting-pane layouts; `NavigableListDetailPaneScaffold` adds back navigation between panes.
- Do not lock orientation or assume a portrait phone. For apps targeting Android 16 (API 36) the system ignores orientation, aspect ratio and resizability restrictions on displays with smallest width of 600 dp or more; check the current large-screen behavior notes for the API level you target.
- Hoist selection state (selected item id) above the layout so it survives switching between one-pane and two-pane configurations.

## 9. Accessibility

- Provide `contentDescription` for meaningful icons and images; pass `null` for decorative ones.
- Use `Modifier.semantics { }` for roles, state descriptions and headings (`heading()`); merge related elements with `Modifier.semantics(mergeDescendants = true) { }` or `clearAndSetSemantics` when replacing child semantics deliberately.
- Interactive targets are at least 48 dp; Material components enforce this, custom `clickable` areas need `Modifier.minimumInteractiveComponentSize()`.
- Use `Modifier.clickable(onClickLabel = "...")`, `toggleable` and `selectable` with a `Role` so screen readers announce the action.
- Use text in `sp`, test at 200 percent font scale, and ensure contrast through theme tokens (`onSurface` on `surface`).
- Respect users who disable animations (the system animator duration scale): keep large movement optional and avoid animation-only feedback.
- Verify with TalkBack, Accessibility Scanner, and automated checks in UI tests (`enableAccessibilityChecks()` in the Compose test rule).

## 10. Animation

| Need | API |
|---|---|
| One value reacts to state | `animateColorAsState`, `animateDpAsState`, `animateFloatAsState` |
| Several values change together | `updateTransition` |
| Show or hide content | `AnimatedVisibility` |
| Swap content | `AnimatedContent(targetState)` or `Crossfade` |
| Size changes | `Modifier.animateContentSize()` |
| Imperative or gesture-driven | `Animatable` with `animateTo` / `snapTo` |
| Endless loop | `rememberInfiniteTransition` |
| List item add, remove, reorder | `Modifier.animateItem()` in lazy lists |

- Read animated values inside `graphicsLayer { }` or `drawBehind { }` lambdas so frames do not recompose.
- Prefer spring specs for interactive motion and tween for fixed-duration effects; keep durations short and skippable.
- Shared element transitions use `SharedTransitionLayout` with `Modifier.sharedElement()`/`sharedBounds()`; check the foundation release notes for the current API status.

## 11. Testing

```kotlin
class ArticleListScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun showsArticlesAndReportsClicks() {
        var clicked: ArticleId? = null
        composeRule.setContent {
            AppTheme {
                ArticleListScreen(
                    uiState = ArticleListUiState(
                        articles = listOf(Article(ArticleId("a1"), "Hello", "First post")),
                    ),
                    onRefresh = {},
                    onArticleClick = { clicked = it },
                )
            }
        }

        composeRule.onNodeWithText("Hello").assertIsDisplayed().performClick()

        assertEquals(ArticleId("a1"), clicked)
    }
}
```

- Test stateless screen composables with fake `UiState`; test ViewModels separately with `runTest`.
- Prefer semantic matchers (`onNodeWithText`, `onNodeWithContentDescription`, `hasClickAction()`) over `testTag`; add a `testTag` only where no semantics exist.
- The compose test clock is virtual: use `composeRule.mainClock.advanceTimeBy(...)` for animations, and `waitUntil { }` or idling resources instead of `Thread.sleep`.
- Use `createAndroidComposeRule<MainActivity>()` only when an activity (Hilt entry point, navigation host) is required; for Hilt tests combine it with `HiltAndroidRule`.
- Screenshot tests (Roborazzi or Paparazzi) cover the design system in light, dark, large font and right-to-left variants.
- Previews: annotate with `@Preview`, and use multi-preview annotations for theme, font scale and device variants; previews take fake state, never real repositories.

## 12. Interop

- Embed a View in Compose with `AndroidView(factory = { context -> ... }, update = { view -> ... })`; the factory runs once, `update` runs on state change. Release resources in the `onRelease` parameter.
- Embed Compose in Views with `ComposeView`; call `setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)` in fragments.
- Migrate screen by screen: wrap existing screens in a Compose host first, then replace inner components.

## 13. Common mistakes

- Creating state without `remember`: it resets on every recomposition.
- Using the list index as a lazy list key: item state and animations attach to positions.
- Reading fast-changing state in a parent composable that does not need it, causing broad recomposition; defer the read.
- Using `collectAsState()` where lifecycle matters; use `collectAsStateWithLifecycle()`.
- Starting work in the composable body instead of `LaunchedEffect` or the ViewModel.
- Hard-coding colors, dimensions in `dp` for text, or fixed screen widths; breaks dark theme, dynamic color, font scaling and large screens.
- Applying `Modifier` only to a child instead of the root element and not exposing a `modifier` parameter.
- Wrapping every model in `ImmutableList` or `@Immutable` without measuring.
- Passing a `ViewModel` into deep composables; pass state and lambdas instead.
- Profiling in a debug build and drawing conclusions about Compose speed.
