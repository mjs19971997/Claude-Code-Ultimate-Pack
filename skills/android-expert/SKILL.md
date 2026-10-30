---
name: android-expert
description: >-
  Builds and reviews native Android apps in Kotlin, covering the former android-architecture-expert, android-kotlin-expert and jetpack-compose-expert skills: app architecture (UI, domain and data layers, modularization, Hilt, Room, Retrofit, WorkManager, DataStore, Paging), Kotlin coroutines and Flow, and Jetpack Compose UI with Material 3, navigation and adaptive layouts. Use when working on Android projects: .kt and build.gradle.kts files, libs.versions.toml, AndroidManifest.xml, ViewModels, composables, Room DAOs, Hilt modules, Gradle and AGP upgrades, offline-first sync, recomposition or ANR problems. Not for iOS or Swift (use swift-expert); not for Kotlin server back ends or React Native.
license: MIT
metadata:
  version: "3.0.0"
---

# Android Expert

This skill covers native Android development in Kotlin and absorbs the former android-architecture-expert, android-kotlin-expert and jetpack-compose-expert skills: architecture and modularization, coroutines and Flow, Jetpack Compose UI, persistence, networking, background work, security, testing and release. Deep material is split into three references: architecture, Kotlin and Jetpack Compose. It does not cover iOS, Kotlin server frameworks, or cross-platform UI toolkits; Kotlin Multiplatform is mentioned only where it shapes Android module design.

> Verified against Kotlin 2.4.21, Android Gradle Plugin 9.5.0 (Gradle 9.6.0 minimum), Compose BOM 2026.09.00 (Compose UI 1.12.1, Material 3 1.4.0), Android 17 / API 37 as compileSdk, Google Play target API 36 minimum, Navigation 3 1.2.0, Navigation 2.10.2 and androidx.hilt 1.4.0 (2026-10).

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

- **Architecture:** the layered architecture from the Android app architecture guide (UI layer, optional domain layer, data layer), unidirectional data flow, offline-first repositories, modularization with convention plugins and a version catalog. See [references/architecture.md](references/architecture.md).
- **Kotlin:** null safety, sealed and value classes, coroutines with structured concurrency, Flow, kotlinx.serialization, Gradle Kotlin DSL. See [references/kotlin.md](references/kotlin.md).
- **Jetpack Compose:** state and side effects, stability and recomposition, Material 3 theming, lazy lists, navigation (Navigation 3 and type-safe Navigation 2), adaptive layouts, accessibility, UI tests. See [references/jetpack-compose.md](references/jetpack-compose.md).
- **Platform:** Hilt, Room, Retrofit/OkHttp, WorkManager, DataStore, Paging 3, Android Keystore, R8, Baseline Profiles.

## 2. Core Expertise

- **Layers.** UI layer (composables + ViewModels exposing `StateFlow<UiState>`), optional domain layer (use cases for reusable or complex business logic), data layer (repositories as the single source of truth over Room, network and DataStore).
- **Unidirectional data flow.** State flows down from ViewModel to UI; events flow up as function calls. ViewModels never hold references to views, `Context` or composables.
- **Coroutines.** `viewModelScope` and `lifecycleScope` for UI-bound work, injected `CoroutineScope` for work that outlives a screen, WorkManager for work that must survive process death. Suspend functions are main-safe.
- **Flow.** Cold `Flow` from Room and repositories; `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)` to expose state; `collectAsStateWithLifecycle()` in Compose.
- **Compose.** Composables are functions of state; state is hoisted; side effects go through effect APIs; lazy lists use stable keys. Strong skipping is the compiler default since Kotlin 2.0.20, so unstable parameters no longer block skipping by themselves.
- **Build.** AGP 9 has built-in Kotlin support enabled by default (the `org.jetbrains.kotlin.android` plugin is no longer applied separately), Gradle Kotlin DSL, `libs.versions.toml`, KSP for annotation processors (Room, Hilt). Starting with AGP 10 the new Variant API becomes mandatory; migrate custom build logic early.
- **SDK levels.** `compileSdk` at the latest stable API (37); `targetSdk` at least the Google Play minimum (API 36 for new apps and updates since 2026-08-31); `minSdk` chosen from your audience data.

## 3. Workflow

1. Read the build: AGP, Gradle, Kotlin and Compose BOM versions, `compileSdk`/`targetSdk`/`minSdk`, module graph. Check the AGP release notes before upgrading; major versions remove deprecated DSL.
2. Model the feature: domain types (`data class`, `@JvmInline value class` IDs, sealed results), repository interface, data sources.
3. Implement the data layer: Room entities and DAOs, Retrofit service, repository that writes network results into Room and exposes Room `Flow`s.
4. Add a use case only if logic is reused across ViewModels or is complex enough to test separately.
5. Implement the ViewModel: combine repository flows into one immutable `UiState`, expose it as `StateFlow`, handle events as functions.
6. Build composables: a route composable that obtains the ViewModel and collects state, and a stateless screen composable that takes `UiState` and lambdas (previewable, testable).
7. Wire DI (Hilt modules, `@Binds`), navigation and background sync (WorkManager).
8. Test: ViewModel and repository unit tests with fakes, `runTest` and Turbine; Compose UI tests for the screen; migration tests for Room.
9. Verify performance: Baseline Profile, Macrobenchmark for startup and scrolling, Layout Inspector recomposition counts.
10. Release: R8 enabled, App Bundle, staged rollout, Android vitals monitoring.

## 4. Decision Rules

- **Domain layer or not.** Add use cases when logic combines several repositories or is shared by several ViewModels; otherwise ViewModels call repositories directly.
- **`StateFlow` vs one-shot events.** Model UI outcomes (navigate, show message) as state the UI consumes and acknowledges where possible; if a stream of events is required, use a `Channel` received as a flow and collected with lifecycle awareness, not a `SharedFlow` without replay that drops events while the UI is stopped.
- **Room vs DataStore.** Structured or queryable data: Room. Small key-value settings or a single typed object: DataStore.
- **WorkManager vs coroutine.** Work that must finish even if the user leaves or the process dies (uploads, sync): WorkManager. Work tied to a screen: `viewModelScope`.
- **RemoteMediator vs manual refresh.** Paged network lists cached locally: Paging 3 with `RemoteMediator`. Small lists: repository refresh plus Room `Flow`.
- **`@Binds` vs `@Provides`.** Interface to implementation: `@Binds`. Construction logic or third-party types (Retrofit, Room): `@Provides`.
- **Navigation 3 vs Navigation 2.** New Compose apps: Navigation 3 (back stack is app-owned state). Existing apps on Navigation 2: stay and use type-safe `@Serializable` routes; Navigation 2 remains supported (latest stable 2.10.2), so migrate when the back stack needs app-level control, not by default.
- **`remember` vs `rememberSaveable` vs ViewModel.** Transient UI state: `remember`. UI state that must survive configuration change and process death (text input, selection): `rememberSaveable`. Screen data and business state: ViewModel (with `SavedStateHandle` for arguments).
- **Compose vs Views.** New UI in Compose; existing View screens interoperate through `ComposeView` and `AndroidView`.

## 5. Coding Standards

- Kotlin official code style enforced by ktlint or Spotless; static analysis with Android Lint and detekt in CI.
- Naming: classes `UpperCamelCase`; functions and properties `lowerCamelCase`; `const val` and top-level immutable constants `SCREAMING_SNAKE_CASE`; composables that emit UI are nouns in `UpperCamelCase` (`ArticleCard`); composables returning values are `lowerCamelCase` (`rememberPagerState`).
- Types: `data class` for models, `sealed interface` for closed hierarchies, `@JvmInline value class` for IDs, `enum class` for fixed sets.
- No `!!` in production code; use `?.`, `?:`, `requireNotNull` with a message.
- No `GlobalScope`, no `runBlocking` outside `main` functions and tests.
- Never swallow `CancellationException`; catch specific exceptions (`IOException`, `HttpException`) rather than `Exception`/`Throwable`. `runCatching` catches cancellation, so rethrow it if you use it inside coroutines.
- Expose read-only types: `StateFlow`, `List`, not `MutableStateFlow`, `MutableList`.
- Inject `CoroutineDispatcher`s instead of hard-coding `Dispatchers.IO` so tests can substitute them.
- Composables: `modifier: Modifier = Modifier` is the first optional parameter and applied to the root element; state in, lambdas out.
- Data layer types (entities, DTOs) do not leak into UI; map at the repository.
- Module dependencies point inward: features depend on core modules, never on other features; `core:domain`/`core:model` have no Android framework dependencies.

## 6. Project Structure

```
my-app/
├── app/                          # Application, MainActivity, navigation host, DI entry point
├── feature/
│   ├── articles/                 # UI + ViewModels for one feature
│   └── settings/
├── core/
│   ├── model/                    # pure Kotlin domain models
│   ├── domain/                   # optional use cases
│   ├── data/                     # repositories, sync workers, mappers
│   ├── database/                 # Room database, entities, DAOs, migrations
│   ├── network/                  # Retrofit services, DTOs, OkHttp setup
│   ├── datastore/                # DataStore definitions
│   ├── designsystem/             # Material 3 theme, shared components
│   └── testing/                  # fakes, test rules, test data
├── build-logic/convention/       # Gradle convention plugins
├── gradle/libs.versions.toml     # version catalog
├── settings.gradle.kts
└── build.gradle.kts
```

## 7. Design Patterns

- **Offline-first repository.** Room is the source of truth; the repository exposes `Flow`s from DAOs and a `refresh()` that writes network results into Room (Example 1).
- **Route / screen split.** `ArticleListRoute` obtains the ViewModel and collects state; `ArticleListScreen` is stateless and previewable (Example 2).
- **Single `UiState` per screen.** An immutable data class or sealed interface built with `combine` + `stateIn`.
- **Use case.** `class GetFeedUseCase @Inject constructor(...) { operator fun invoke(): Flow<Feed> }` for shared business logic.
- **Convention plugins.** Shared Android, Compose, Hilt and test configuration in `build-logic`, applied by plugin id in each module.
- **Sync worker.** A `@HiltWorker` `CoroutineWorker` calls repository sync functions, scheduled as unique periodic work with network constraints.

## 8. Best Practices

- Use `collectAsStateWithLifecycle()` in Compose and `repeatOnLifecycle(Lifecycle.State.STARTED)` in Views so collection stops in the background.
- Use `SharingStarted.WhileSubscribed(5_000)` for UI state so upstream flows survive configuration changes but stop when the user leaves.
- Make every suspend function main-safe; Room and Retrofit suspend functions already are.
- Use KSP for Room and Hilt; KAPT is in maintenance mode.
- Configure one `Json` instance (`ignoreUnknownKeys = true`) per module and inject it.
- Provide Room `Migration`s and export schemas (`room.schemaDirectory`) so migrations are testable; do not rely on destructive fallback in production.
- Use type-safe navigation keys/routes; pass IDs, not whole objects, and load data in the destination's ViewModel.
- Support edge-to-edge (enforced when targeting API 35+) by handling window insets in layouts.
- Declare only needed permissions and request runtime permissions in context with a rationale.

## 9. Performance

- Generate a Baseline Profile (Baseline Profile Gradle plugin + Macrobenchmark) for startup and critical journeys; ship it in the release build.
- Measure with Macrobenchmark (`StartupTimingMetric`, `FrameTimingMetric`) on physical devices, not debug builds; Compose runs much slower in debug.
- Keep work off the main thread; enable StrictMode in debug builds to catch disk and network access on the main thread.
- In Compose: stable keys in lazy lists, `contentType` for heterogeneous lists, defer frequently changing reads (scroll offset, animation values) to lambda-based modifiers such as `Modifier.offset { }` or `graphicsLayer { }`, `derivedStateOf` for values derived from rapidly changing state.
- Use `Modifier.Node` for custom modifiers; `Modifier.composed` is discouraged for performance.
- Use Paging 3 for large lists; never load unbounded tables into memory.
- Enable R8 full mode with correct keep rules; check that serialization and reflection users keep what they need.

## 10. Security

- **An APK is not a secret store.** `BuildConfig` fields, `local.properties` values compiled into the app, resources, assets and native libraries can be extracted from the APK or App Bundle. Never ship third-party API keys, signing secrets or service credentials in the app.
- **No secrets in the repository.** Signing keystores and passwords, and any local credentials, stay out of version control: do not commit `gradle.properties`, `local.properties` or `*.jks` files that hold them; read signing values from CI secret storage or a developer-local, git-ignored file, and never copy them into `BuildConfig` or resources.
- **Backend for third-party access.** The app authenticates the user against your backend (OAuth 2.0 with PKCE via Custom Tabs, or Credential Manager with passkeys); the backend holds third-party keys, proxies calls or issues short-lived scoped tokens, and enforces quotas. The Play Integrity API helps the backend reject tampered clients.
- **Android Keystore for user tokens.** Encrypt session tokens with a non-exportable AES-GCM key generated in the Android Keystore and store the ciphertext in DataStore ([references/architecture.md](references/architecture.md), section 10). The `androidx.security:security-crypto` APIs (`EncryptedSharedPreferences`) are deprecated in favor of platform APIs and direct Keystore use.
- HTTPS only: network security config with `cleartextTrafficPermitted="false"`; certificate pinning only with backup pins and a rotation plan.
- Exported components: set `android:exported` deliberately; protect exported activities, services and receivers; validate all `Intent` extras and deep-link parameters.
- Use `PendingIntent.FLAG_IMMUTABLE` unless mutability is required.
- Do not log tokens or personal data; strip verbose logs from release builds with R8 rules or a no-op logging tree.
- Use `BiometricPrompt` (with a `CryptoObject` when protecting keys) for biometric gates.
- Password fields use `KeyboardType.Password` and `PasswordVisualTransformation()` (or the secure text field components) and correct autofill content types.

## 11. Testing

- Unit tests (JVM): ViewModels, repositories and use cases with hand-written fakes from `core:testing`; MockK only where a fake is impractical.
- Coroutines: `runTest` with an injected `StandardTestDispatcher`; a `MainDispatcherRule` sets `Dispatchers.setMain` for ViewModels.
- Flows: Turbine (`flow.test { awaitItem() }`) or collecting into a list in `backgroundScope`.
- Room: in-memory database tests for DAOs; `MigrationTestHelper` for each migration.
- Compose: `createComposeRule()` for stateless screens, asserting on semantics (`onNodeWithText`, `onNodeWithContentDescription`); `testTag` only where no semantic selector exists.
- Hilt integration tests: `@HiltAndroidTest`, `HiltAndroidRule`, `@TestInstallIn` to replace modules.
- Screenshot tests (for example Roborazzi or Paparazzi) for design-system components; Macrobenchmark for performance regressions.

## 12. Review Checklist

- [ ] Versions (AGP, Kotlin, Compose BOM, SDK levels) are current and consistent; `targetSdk` meets the Play requirement.
- [ ] Dependencies point inward; no feature-to-feature dependencies; no Android imports in pure modules.
- [ ] ViewModels expose immutable `StateFlow<UiState>`; no `Context`, `View` or composable references.
- [ ] UI collects with `collectAsStateWithLifecycle()` / `repeatOnLifecycle`.
- [ ] No `GlobalScope`, `runBlocking` or `!!` in production code; cancellation is never swallowed.
- [ ] Dispatchers are injected; suspend functions are main-safe.
- [ ] Repositories map DTOs/entities to domain models; Room is the source of truth for cached data.
- [ ] Room schema changes ship with migrations and migration tests.
- [ ] Composables are stateless where possible, take `modifier` first among optional params, use stable keys in lazy lists and have content descriptions for meaningful icons.
- [ ] No secrets in `BuildConfig`, resources or source; tokens encrypted with a Keystore key.
- [ ] Exported components and deep links validate input.
- [ ] New logic has unit tests; screens have Compose UI tests.
- [ ] Refactors (LiveData to Flow, KAPT to KSP, Navigation 2 to 3) are done in small, test-covered steps without behavior change.

## 13. Production Notes

- Always ship App Bundles with R8; upload the mapping file to your crash reporter so stack traces are readable.
- Watch Android vitals in Play Console (core vitals such as user-perceived crash and ANR rates); exceeding the bad-behavior thresholds affects store visibility, so check the current thresholds in the Play Console documentation.
- Use staged rollouts and halt them on regressions; server-side flags let you disable features without a release.
- Test Room migrations from every version still installed in the field, not just N-1.
- WorkManager work survives app updates; changing a worker's class name or input contract needs a migration plan for already-enqueued work.

## 14. Examples

### Example 1: Offline-first repository

```kotlin
package com.example.core.data

import com.example.core.database.ArticleDao
import com.example.core.database.ArticleEntity
import com.example.core.model.Article
import com.example.core.model.ArticleId
import com.example.core.network.ArticleApi
import com.example.core.network.ArticleDto
import java.io.IOException
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import retrofit2.HttpException

interface ArticleRepository {
    fun observeArticles(): Flow<List<Article>>
    suspend fun refresh(): Result<Unit>
}

class OfflineFirstArticleRepository @Inject constructor(
    private val api: ArticleApi,
    private val dao: ArticleDao,
) : ArticleRepository {

    override fun observeArticles(): Flow<List<Article>> =
        dao.observeAll().map { rows -> rows.map(ArticleEntity::toModel) }

    // Room and Retrofit suspend functions are main-safe, so no withContext is needed here.
    override suspend fun refresh(): Result<Unit> =
        try {
            val remote = api.getArticles()
            dao.upsertAll(remote.map(ArticleDto::toEntity))
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: IOException) {
            Result.failure(e)
        } catch (e: HttpException) {
            Result.failure(e)
        }
}

private fun ArticleEntity.toModel() = Article(id = ArticleId(id), title = title, summary = summary)

private fun ArticleDto.toEntity() = ArticleEntity(id = id, title = title, summary = summary)
```

The DAO, entity, Retrofit service and Hilt binding for this repository are in [references/architecture.md](references/architecture.md).

### Example 2: ViewModel and Compose screen

```kotlin
package com.example.feature.articles

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.example.core.data.ArticleRepository
import com.example.core.model.Article
import com.example.core.model.ArticleId
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class ArticleListUiState(
    val articles: List<Article> = emptyList(),
    val isRefreshing: Boolean = false,
    val errorMessage: String? = null,
)

@HiltViewModel
class ArticleListViewModel @Inject constructor(
    private val repository: ArticleRepository,
) : ViewModel() {

    private val isRefreshing = MutableStateFlow(false)
    private val errorMessage = MutableStateFlow<String?>(null)

    val uiState: StateFlow<ArticleListUiState> =
        combine(repository.observeArticles(), isRefreshing, errorMessage) { articles, refreshing, error ->
            ArticleListUiState(articles, refreshing, error)
        }.stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = ArticleListUiState(),
        )

    init {
        refresh()
    }

    fun refresh() {
        if (isRefreshing.value) return
        viewModelScope.launch {
            isRefreshing.value = true
            errorMessage.value = null
            try {
                repository.refresh().onFailure { errorMessage.value = "Could not refresh articles." }
            } finally {
                isRefreshing.value = false
            }
        }
    }
}

@Composable
fun ArticleListRoute(
    onArticleClick: (ArticleId) -> Unit,
    viewModel: ArticleListViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    ArticleListScreen(uiState = uiState, onRefresh = viewModel::refresh, onArticleClick = onArticleClick)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArticleListScreen(
    uiState: ArticleListUiState,
    onRefresh: () -> Unit,
    onArticleClick: (ArticleId) -> Unit,
    modifier: Modifier = Modifier,
) {
    PullToRefreshBox(
        isRefreshing = uiState.isRefreshing,
        onRefresh = onRefresh,
        modifier = modifier.fillMaxSize(),
    ) {
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            uiState.errorMessage?.let { message ->
                item(key = "error") {
                    Text(message, color = MaterialTheme.colorScheme.error)
                }
            }
            items(items = uiState.articles, key = { it.id.value }) { article ->
                ListItem(
                    headlineContent = { Text(article.title) },
                    supportingContent = {
                        Text(article.summary, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    },
                    modifier = Modifier.clickable(onClickLabel = "Open article") {
                        onArticleClick(article.id)
                    },
                )
            }
        }
    }
}
```

## 15. Common Mistakes

- **API keys in `BuildConfig` or `local.properties`.** They end up in the APK in plain form. Move third-party calls behind your backend; keep only per-user tokens on the device, encrypted with a Keystore key.
- **Catching `Exception` (or using `runCatching`) around suspend calls.** It swallows `CancellationException` and breaks structured concurrency. Rethrow cancellation and catch specific types.
- **`GlobalScope.launch` for background work.** No owner, no cancellation, hard to test. Use `viewModelScope`, an injected application scope, or WorkManager.
- **Collecting flows without lifecycle awareness.** `lifecycleScope.launch { flow.collect {} }` or `collectAsState()` keeps collecting in the background. Use `repeatOnLifecycle` / `collectAsStateWithLifecycle()`.
- **One-shot events in a `SharedFlow` with no replay.** Events emitted while the UI is stopped are lost. Model them as state or use a `Channel`.
- **Exposing `MutableStateFlow` from a ViewModel.** Any caller can change state; expose `StateFlow`.
- **Data-layer types in the UI.** Room entities or DTOs in composables couple the UI to storage formats; map to models.
- **God ViewModels and feature-to-feature dependencies.** Split by screen, extract shared logic into use cases or core modules.
- **State without `remember`, or `remember` where `rememberSaveable` is needed.** Values reset on recomposition or on rotation and process death.
- **Lazy list items without stable keys.** Item state and animations attach to positions instead of items.
- **Side effects in composable bodies.** Network calls or analytics run on every recomposition; use `LaunchedEffect` or move them to the ViewModel.
- **Hard-coded colors and text sizes.** Break dark theme, dynamic color and font scaling; use `MaterialTheme` tokens and `sp`-based typography.
- **Destructive Room migrations in production.** `fallbackToDestructiveMigration()` deletes user data; write and test migrations.
- **SharedPreferences `commit()` or synchronous reads on the main thread.** Causes jank and ANRs; use DataStore.

## 16. References

- [references/architecture.md](references/architecture.md) - layers and modules, Hilt modules, Room, Retrofit with kotlinx.serialization, Paging 3 with RemoteMediator, WorkManager sync, DataStore, convention plugins and test setup.
- [references/kotlin.md](references/kotlin.md) - Kotlin idioms, coroutines and cancellation, Flow operators and sharing, events, kotlinx.serialization with custom serializers, Gradle Kotlin DSL.
- [references/jetpack-compose.md](references/jetpack-compose.md) - state and effects, stability and strong skipping, lazy lists, Material 3 theming with dynamic color, Navigation 3 and type-safe Navigation 2, adaptive layouts, accessibility, animation and UI testing.
- Official docs: https://developer.android.com/topic/architecture , https://developer.android.com/develop/ui/compose , https://developer.android.com/guide/navigation/navigation-3 , https://developer.android.com/kotlin/coroutines , https://developer.android.com/build/releases/gradle-plugin , https://developer.android.com/privacy-and-security/keystore
