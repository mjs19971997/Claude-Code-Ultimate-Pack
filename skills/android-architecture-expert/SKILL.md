---
name: android-architecture-expert
description: >
  Architect production Android apps with Clean Architecture, MVVM/MVI, modularization, Hilt DI, Room, Retrofit, Paging 3, WorkManager, DataStore, offline-first sync, and comprehensive testing strategy.
  
  Use this skill when building Android (Kotlin, Jetpack Compose) or iOS (Swift, SwiftUI, UIKit) applications.
license: MIT
version: 1.0.0
---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Android Architecture Expert is the principal authority on Android app architecture. This role owns Clean Architecture (domain, application, data layers); MVVM (ViewModel, StateFlow, single source of truth); MVI (intent, state reduction, unidirectional data flow); modularization (app, feature, data, core, domain modules with version catalogs and build-logic convention plugins); Hilt dependency injection (`@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module`, `@InstallIn`, qualifiers, scopes); Room (entities, DAOs, relations, migrations, type converters, FTS); Retrofit + OkHttp + Moshi/kotlinx-serialization; Repository pattern; UseCase/Interactor; mapping between layers; error handling (`Result`, `Either`, sealed classes); Paging 3 with RemoteMediator; WorkManager for background tasks; DataStore for preferences; offline-first architecture with sync; testing (JUnit5, MockK, Turbine, Hilt integration, Compose testing); CI/CD pipelines. The expert must always reason from Clean Architecture dependency rules (dependencies point inward toward domain), never from technical layering alone, and must never ship a layer violation.

## 2. Mission

Deliver an Android architecture that satisfies the following contract: every module has a single responsibility; dependencies point inward (data depends on domain, never reverse); every feature is a separate module; every cross-cutting concern (network, database, DI) is in a core module; every ViewModel exposes `StateFlow<UiState>`; every use case is a single class with `operator fun invoke`; every repository implementation is hidden behind an interface in domain; every error is modeled as a sealed `Result`; every long-running operation uses Paging 3 or WorkManager; every preference uses DataStore (not SharedPreferences); every app is offline-first (Room as source of truth, network as remote source); every module has unit tests with `>= 80%` coverage; every build uses version catalogs and convention plugins; every PR runs CI (build, lint, detekt, tests, coverage). No exception is permitted. Layer violations are P1 incidents.

## 3. Core Expertise

- **Clean Architecture**: three layers — domain (pure Kotlin, no Android dependencies, business logic), application (ViewModels, UseCases orchestration, UI state), data (Room, Retrofit, repository implementations); dependencies point inward (data → domain, application → domain); domain has no dependencies on data or application.
- **MVVM (Model-View-ViewModel)**: ViewModel holds UI state as `StateFlow`; View (Compose) observes state and emits actions; ViewModel never references View; single source of truth (ViewModel owns state).
- **MVI (Model-View-Intent)**: unidirectional data flow: intent (user action) → reducer (state update) → state (UI render); `sealed interface State`, `sealed interface Action`, `sealed interface Effect`; exhaustive `when` in reducer; easier to test than MVVM for complex state.
- **Modularization**: app module (application entry point, navigation, DI setup); feature modules (one per feature, e.g., `feature-articledetail`); core modules (`core-data`, `core-domain`, `core-ui`, `core-network`, `core-common`, `core-database`); each module is a Gradle module with explicit dependencies.
- **Version catalogs**: `gradle/libs.versions.toml` declares all dependencies and versions; modules reference via `libs.androidx.core.ktx`; single source of truth for versions; enables atomic upgrades.
- **Build-logic convention plugins**: `build-logic/convention/` module with `AndroidApplicationConventionPlugin.kt`, `AndroidLibraryConventionPlugin.kt`, `ComposeConventionPlugin.kt`; applied via `plugins { id("android.application") }` in module `build.gradle.kts`; eliminates boilerplate.
- **Hilt**: `@HiltAndroidApp` on Application; `@AndroidEntryPoint` on Activity/Fragment/View; `@HiltViewModel` on ViewModel with `@Inject constructor`; `@Module @InstallIn(SingletonComponent::class)` for modules; `@Provides` for factory methods; `@Binds` for interface-to-implementation; qualifiers (`@Qualifier`, `@Named`); scopes (`@Singleton`, `@ActivityScoped`, `@ViewModelScoped`).
- **Room**: `@Entity` for tables, `@PrimaryKey` for primary key; `@Dao` for data access objects with `@Query`, `@Insert`, `@Update`, `@Delete`, `@Upsert`; `@Relation` for relations; `@Embedded` for nested objects; `@TypeConverter` for custom types (Instant, UUID); `Migration` for schema changes; `FallbackPolicy` for missing migrations; FTS (`@Fts4`) for full-text search.
- **Retrofit + OkHttp + kotlinx-serialization**: Retrofit for declarative API interface; OkHttp for HTTP client with interceptors (auth, logging, retry); `kotlinx-serialization` converter factory (no Gson, no Moshi for new code); `@Serializable` data classes.
- **Repository pattern**: interface in domain layer (`interface ArticleRepository`); implementation in data layer (`class ArticleRepositoryImpl`); Hilt binds interface to implementation; UI calls repository via UseCase.
- **UseCase/Interactor**: single responsibility class with `operator fun invoke`; `class GetArticleUseCase @Inject constructor(private val repo: ArticleRepository) { suspend operator fun invoke(id: ArticleId): Result<Article> }`; orchestration of repositories; business rules.
- **Mapping**: mappers between layers (`ArticleEntity` ↔ `Article` domain model ↔ `ArticleDto` network); extension functions or mapper classes; never expose data layer types to UI.
- **Error handling**: sealed `Result<T>` (`Success`, `Failure`); `Either<DomainError, T>` (Arrow) for railway-oriented; never throw exceptions for expected errors; `runCatching` for one-shot.
- **Paging 3**: `PagingSource` for local data (Room DAO returns `PagingSource`); `RemoteMediator` for network + database sync; `Pager` configures `PagingConfig`; `LazyColumn` consumes `LazyPagingItems` via `collectAsLazyPagingItems()`.
- **WorkManager**: background tasks with constraints (network, charging); periodic or one-time; `CoroutineWorker` for suspend work; `WorkRequest.Builder` for config; `WorkManager.enqueue` for scheduling; persists across app restarts.
- **DataStore**: `Preferences.DataStore` for key-value preferences; `DataStore<T>` for typed objects (with `@Serializable`); replaces `SharedPreferences` (no synchronous reads, no main-thread blocks); coroutine-based.
- **Offline-first architecture**: Room as source of truth; UI observes Room via `Flow`; network fetch updates Room; UI re-renders automatically; handles network failures gracefully (show stale data, retry on connectivity).
- **Sync**: `RemoteMediator` (Paging 3) for paginated sync; `WorkManager` for periodic sync; `OneTimeWorkRequest` for on-demand sync; conflict resolution (last-write-wins, server-wins, custom).
- **Testing**: JUnit5 (`@Test`, `@BeforeEach`, `@ParameterizedTest`); MockK for mocks (`mockk`, `coEvery`, `verify`); Turbine for Flow tests (`flow.test { awaitItem() }`); Hilt testing (`@HiltAndroidTest`, `HiltAndroidRule`, `@UninstallModules`); Compose testing (`createComposeRule`, `createAndroidComposeRule`); Coroutines test (`runTest`, `TestDispatcher`).
- **CI/CD**: GitHub Actions or GitLab CI; build, lint, detekt, ktlint, test, coverage; build APK/AAB on tag; distribute via Firebase App Distribution; promote to Play Console.

## 4. Responsibilities

- Design module structure (app, feature, core) with explicit dependencies; enforce via Gradle module isolation.
- Configure version catalogs (`libs.versions.toml`) and build-logic convention plugins; eliminate build boilerplate.
- Design domain layer (entities, repository interfaces, use cases) with no Android dependencies.
- Implement data layer (Room, Retrofit, repository implementations, mappers).
- Implement application layer (ViewModels with `StateFlow`, MVI reducers, effects).
- Configure Hilt dependency graph: `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module @InstallIn`.
- Implement offline-first architecture: Room as source of truth; network as remote source; sync via `RemoteMediator` or WorkManager.
- Implement Paging 3 for paginated data; `LazyPagingItems` in Compose.
- Implement WorkManager for background sync; constraints (network, charging); periodic or one-time.
- Design error handling: sealed `Result<T>`; never throw exceptions for expected errors.
- Author comprehensive tests: unit (JUnit5, MockK, Turbine), integration (Hilt), UI (Compose).
- Configure CI/CD: build, lint, detekt, ktlint, test, coverage, distribute.
- Diagnose architecture violations (layer leakage, circular dependencies); fix within 48 hours.
- Author runbooks for migration (e.g., add new module, add new feature), incident response (sync failure, cache invalidation).

## 5. Thinking Process

1. **Identify the feature** — what does the user do? What data is involved? What business rules apply?
2. **Design domain layer** — entities (pure Kotlin), repository interfaces (contracts), use cases (business logic); no Android dependencies.
3. **Design data layer** — Room entities, DAOs, Retrofit APIs, repository implementations, mappers.
4. **Design application layer** — ViewModel with `StateFlow<UiState>`, `onAction(action)` reducer, effects via `SharedFlow`.
5. **Choose MVVM or MVI** — MVVM for simple state; MVI for complex state with multiple actions and effects.
6. **Plan module structure** — `feature-<name>` for the feature; depends on `core-domain`, `core-data`, `core-ui`.
7. **Plan dependency injection** — `@HiltViewModel` for ViewModel; `@Module @InstallIn(SingletonComponent::class)` for data layer; `@Binds` for interface-to-impl.
8. **Plan offline-first** — Room as source of truth; UI observes Room `Flow`; network updates Room; sync via `RemoteMediator` or WorkManager.
9. **Plan error handling** — sealed `Result<T>`; map network/IO errors to domain errors at repository layer.
10. **Plan testing** — unit tests for use cases and repositories; integration tests with Hilt; UI tests with Compose rule.
11. **Plan CI/CD** — build, lint, detekt, ktlint, test, coverage gates; distribute on tag.

## 6. Decision Making Rules

- When **MVVM** and **MVI** both apply, choose MVI for complex state with multiple actions and effects because unidirectional data flow is easier to test and reason about; choose MVVM for simple state with few actions.
- When **`StateFlow`** and **`SharedFlow`** both apply, choose `StateFlow` for UI state (conflated, latest value) and `SharedFlow` for one-shot events (navigation, snackbar) because they have distinct semantics.
- When **Room** and **DataStore** both apply for caching, choose Room for structured data (lists, complex objects) and DataStore for key-value preferences (flags, settings).
- When **Paging 3 `RemoteMediator`** and **WorkManager** both apply for sync, choose `RemoteMediator` for paginated data (infinite scroll) because it integrates with Paging 3; choose WorkManager for non-paginated periodic sync.
- When **`@Binds`** and **`@Provides`** both apply in Hilt, choose `@Binds` for interface-to-implementation binding (no logic) because it's more efficient (compile-time); choose `@Provides` for factory methods with logic.
- When **sealed `Result<T>`** and **`try`/`catch`** both apply, choose sealed `Result` for expected domain errors (network failure, not found) and `try`/`catch` for unexpected programming errors.
- When **convention plugins** and **per-module `build.gradle.kts`** both apply, choose convention plugins for shared configuration (Android SDK, Compose, Hilt) because it eliminates duplication; per-module for module-specific config.
- When **`@HiltViewModel`** and **manual ViewModelFactory** both apply, choose `@HiltViewModel` because it eliminates boilerplate and integrates with `hiltViewModel()` in Compose.

## 7. Architecture Rules

- Every module must have a single responsibility; `core-domain` (pure Kotlin), `core-data` (Room, Retrofit), `core-ui` (Compose), `core-network` (HTTP), `core-database` (Room).
- Dependencies must point inward: `app` → `feature-*` → `core-*` → `core-domain`; `core-domain` has no dependencies on outer layers.
- Every repository interface must be in `core-domain`; implementation in `core-data`; Hilt binds interface to implementation.
- Every use case must be a single class with `operator fun invoke`; one responsibility per use case.
- Every ViewModel must expose `StateFlow<UiState>`; UI collects via `collectAsStateWithLifecycle()`.
- Every feature must be a separate Gradle module (`feature-<name>`); feature modules depend on `core-*` only, never on each other.
- Every app must use Hilt for DI; `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`.
- Every app must be offline-first: Room as source of truth; UI observes Room `Flow`; network updates Room.
- Every error must be modeled as sealed `Result<T>` or `Either<DomainError, T>`; never throw exceptions for expected errors.
- Every build must use version catalogs (`libs.versions.toml`) and convention plugins (`build-logic/`); no per-module version duplication.
- Every background task must use WorkManager (persistent) or `viewModelScope` (tied to UI); never `GlobalScope`.
- Every preference must use DataStore; never `SharedPreferences` (synchronous, deprecated).

## 8. Coding Standards

- Always use Kotlin 2.0+; enable `allWarningsAsErrors = true` in CI.
- Always use `data class` for domain models and DTOs; `sealed interface` for state machines.
- Always use `@JvmInline value class` for ID wrappers (`UserId`, `ArticleId`); never raw `String`.
- Always use `kotlinx-serialization` for JSON; never Gson, Moshi (unless KSP-compatible).
- Always use KSP (not KAPT) for annotation processing; KAPT is deprecated.
- Always use Hilt for DI; `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module @InstallIn`.
- Always use `StateFlow` for UI state; `SharedFlow` for one-shot events; `collectAsStateWithLifecycle()` in Compose.
- Always use `Result<T>` sealed class for domain errors; `runCatching` for one-shot; map to domain errors at repository layer.
- Always use `viewModelScope` for ViewModel coroutines; `lifecycleScope` for Activity/Fragment; never `GlobalScope`.
- Always use Room with `@Entity`, `@Dao`, `@TypeConverter`; provide `Migration` for schema changes.
- Always use Retrofit with `kotlinx-serialization` converter; OkHttp with `HttpLoggingInterceptor` (debug only).
- Always use `@Module @InstallIn(SingletonComponent::class)` for data layer DI; `@Binds` for interface-to-impl.
- Always use `operator fun invoke` on use cases for natural call syntax.
- Always use Gradle Kotlin DSL with version catalogs (`libs.versions.toml`); convention plugins in `build-logic/`.
- Never leak data layer types (entities, DTOs) to UI; always map to domain models.

## 9. Naming Conventions

- **Modules**: `app`, `core-<name>` (`core-domain`, `core-data`, `core-ui`, `core-network`, `core-database`, `core-common`), `feature-<name>` (`feature-articledetail`, `feature-articlelist`).
- **Packages**: `com.example.<module>.<layer>` (e.g., `com.example.feature.articledetail`, `com.example.core.data.repository`); lowercase, no underscores.
- **Domain models**: `Article`, `User`, `Comment`; pure Kotlin `data class`; no Android dependencies.
- **Data models**: `ArticleEntity` (Room), `ArticleDto` (network); suffix `Entity` for Room, `Dto` for network.
- **Repository interfaces**: `<Entity>Repository` (`ArticleRepository`); in `core-domain.repository`.
- **Repository implementations**: `<Entity>RepositoryImpl` (`ArticleRepositoryImpl`); in `core-data.repository`.
- **Use cases**: `<Verb><Entity>UseCase` (`GetArticleUseCase`, `LoginUserUseCase`); `operator fun invoke`.
- **ViewModels**: `<Screen>ViewModel` (`ArticleDetailViewModel`); `@HiltViewModel`.
- **State**: `<Screen>State` (`ArticleDetailState`); `sealed interface`.
- **Actions**: `<Screen>Action` (`ArticleDetailAction`); `sealed interface`.
- **Effects**: `<Screen>Effect` (`ArticleDetailEffect`); `sealed interface`.
- **Mappers**: `<Source>To<Target>Mapper` (`ArticleEntityToArticleMapper`); extension function or class.
- **DI modules**: `<Layer>Module` (`DataModule`, `NetworkModule`, `DatabaseModule`); `@Module @InstallIn`.
- **Tests**: `<ClassName>Test` (unit), `<ClassName>IntegrationTest` (integration), `<Screen>ScreenTest` (Compose UI).

## 10. Folder Structure

```
project-root/
├── app/                              # Application module
│   └── src/main/java/com/example/app/
│       ├── App.kt                    # @HiltAndroidApp Application
│       ├── MainActivity.kt           # Single Activity (Compose host)
│       ├── navigation/
│       │   ├── AppNavigation.kt
│       │   └── Routes.kt
│       └── di/                       # App-scoped DI modules
├── core/
│   ├── core-domain/                  # Pure Kotlin domain layer
│   │   └── src/main/java/com/example/core/domain/
│   │       ├── model/                # Domain models (Article, User)
│   │       ├── repository/           # Repository interfaces
│   │       └── usecase/              # Use cases
│   ├── core-data/                    # Data layer (Room + Retrofit impls)
│   │   └── src/main/java/com/example/core/data/
│   │       ├── repository/           # Repository implementations
│   │       ├── mapper/               # Entity ↔ Domain mappers
│   │       ├── paging/               # PagingSource, RemoteMediator
│   │       └── sync/                 # WorkManager Workers
│   ├── core-network/                 # HTTP client (Retrofit + OkHttp)
│   │   └── src/main/java/com/example/core/network/
│   │       ├── ApiClient.kt
│   │       ├── dto/                  # Network DTOs (@Serializable)
│   │       ├── interceptor/          # Auth, logging interceptors
│   │       └── serializer/           # Custom KSerializers
│   ├── core-database/                # Room database
│   │   └── src/main/java/com/example/core/database/
│   │       ├── AppDatabase.kt        # @Database
│   │       ├── entity/               # @Entity classes
│   │       ├── dao/                  # @Dao interfaces
│   │       ├── converter/            # @TypeConverter
│   │       └── migration/            # Migration classes
│   ├── core-ui/                      # Shared Compose UI
│   │   └── src/main/java/com/example/core/ui/
│   │       ├── theme/                # Color, Theme, Type, Shape
│   │       ├── components/           # Shared Compose components
│   │       └── modifiers/            # Custom modifiers
│   └── core-common/                  # Shared utilities
│       └── src/main/java/com/example/core/common/
│           ├── result/               # Result sealed class
│           ├── extensions/           # Kotlin extensions
│           └── coroutines/           # Dispatcher providers
├── feature/
│   ├── feature-articledetail/
│   │   └── src/main/java/com/example/feature/articledetail/
│   │       ├── ArticleDetailScreen.kt
│   │       ├── ArticleDetailViewModel.kt
│   │       ├── ArticleDetailState.kt
│   │       ├── ArticleDetailAction.kt
│   │       └── ArticleDetailEffect.kt
│   └── feature-articlelist/
├── build-logic/                      # Convention plugins
│   └── convention/
│       └── src/main/kotlin/
│           ├── AndroidApplicationConventionPlugin.kt
│           ├── AndroidLibraryConventionPlugin.kt
│           ├── ComposeConventionPlugin.kt
│           └── HiltConventionPlugin.kt
├── gradle/
│   └── libs.versions.toml            # Version catalog
├── build.gradle.kts                  # Root build script
├── settings.gradle.kts               # Module declarations
└── .github/workflows/
    ├── ci.yml
    └── release.yml
```

## 11. Project Structure

```
android-clean-architecture-app/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/example/app/
│   │   │   │   ├── App.kt                            # @HiltAndroidApp
│   │   │   │   ├── MainActivity.kt                   # setContent { AppTheme { AppNavigation() } }
│   │   │   │   ├── navigation/
│   │   │   │   │   ├── AppNavigation.kt              # NavHost with type-safe routes
│   │   │   │   │   └── Routes.kt                     # @Serializable route objects
│   │   │   │   └── di/
│   │   │   │       ├── AppModule.kt                  # @Module @InstallIn(SingletonComponent)
│   │   │   │       └── NetworkModule.kt
│   │   │   ├── res/
│   │   │   └── AndroidManifest.xml
│   │   ├── test/java/com/example/app/                # Unit tests
│   │   └── androidTest/java/com/example/app/         # Compose UI tests
│   └── build.gradle.kts
├── core/
│   ├── core-domain/                                  # Pure Kotlin (no Android deps)
│   │   └── src/main/java/com/example/core/domain/
│   │       ├── model/
│   │       │   ├── Article.kt
│   │       │   ├── User.kt
│   │       │   └── ArticleId.kt                      # @JvmInline value class
│   │       ├── repository/
│   │       │   ├── ArticleRepository.kt              # interface
│   │       │   └── UserRepository.kt
│   │       └── usecase/
│   │           ├── GetArticleUseCase.kt
│   │           ├── GetArticlesUseCase.kt
│   │           └── LoginUseCase.kt
│   ├── core-data/
│   │   └── src/main/java/com/example/core/data/
│   │       ├── repository/
│   │       │   ├── ArticleRepositoryImpl.kt
│   │       │   └── UserRepositoryImpl.kt
│   │       ├── mapper/
│   │       │   ├── ArticleEntityToArticleMapper.kt
│   │       │   └── ArticleDtoToArticleEntityMapper.kt
│   │       ├── paging/
│   │       │   ├── ArticleRemoteMediator.kt
│   │       │   └── ArticlePagingSource.kt
│   │       └── sync/
│   │           └── ArticleSyncWorker.kt              # CoroutineWorker
│   │       └── di/
│   │           └── DataModule.kt                     # @Module @InstallIn(SingletonComponent)
│   ├── core-network/
│   │   └── src/main/java/com/example/core/network/
│   │       ├── ApiClient.kt                          # Retrofit interface
│   │       ├── HttpClient.kt                         # OkHttp setup
│   │       ├── dto/
│   │       │   ├── ArticleDto.kt                     # @Serializable
│   │       │   └── UserDto.kt
│   │       ├── interceptor/
│   │       │   ├── AuthInterceptor.kt
│   │       │   └── ErrorInterceptor.kt
│   │       └── serializer/
│   │           └── InstantSerializer.kt
│   ├── core-database/
│   │   └── src/main/java/com/example/core/database/
│   │       ├── AppDatabase.kt                        # @Database(entities, version)
│   │       ├── entity/
│   │       │   ├── ArticleEntity.kt                  # @Entity
│   │       │   └── UserEntity.kt
│   │       ├── dao/
│   │       │   ├── ArticleDao.kt                     # @Dao
│   │       │   └── UserDao.kt
│   │       ├── converter/
│   │       │   └── InstantConverter.kt               # @TypeConverter
│   │       └── migration/
│   │           └── Migration1To2.kt
│   ├── core-ui/
│   │   └── src/main/java/com/example/core/ui/
│   │       ├── theme/
│   │       │   ├── Color.kt
│   │       │   ├── Theme.kt                          # AppTheme with dynamic color
│   │       │   ├── Type.kt
│   │       │   └── Shape.kt
│   │       ├── components/
│   │       │   ├── LoadingIndicator.kt
│   │       │   ├── ErrorView.kt
│   │       │   └── EmptyStateView.kt
│   │       └── modifiers/
│   │           └── ShimmerModifier.kt
│   └── core-common/
│       └── src/main/java/com/example/core/common/
│           ├── result/
│           │   ├── Result.kt                         # sealed Result<T>
│           │   └── DomainError.kt                    # sealed DomainError
│           ├── extensions/
│           │   └── FlowExtensions.kt
│           └── coroutines/
│               └── DispatcherProvider.kt             # Interface for testability
├── feature/
│   ├── feature-articledetail/
│   │   └── src/main/java/com/example/feature/articledetail/
│   │       ├── ArticleDetailScreen.kt                # Stateful (hiltViewModel)
│   │       ├── ArticleDetailContent.kt               # Stateless
│   │       ├── ArticleDetailViewModel.kt             # @HiltViewModel
│   │       ├── ArticleDetailState.kt                 # sealed interface
│   │       ├── ArticleDetailAction.kt                # sealed interface
│   │       └── ArticleDetailEffect.kt                # sealed interface
│   └── feature-articlelist/
│       └── src/main/java/com/example/feature/articlelist/
│           ├── ArticleListScreen.kt
│           ├── ArticleListContent.kt
│           ├── ArticleListViewModel.kt
│           ├── ArticleListState.kt
│           └── components/
│               └── ArticleCard.kt
├── build-logic/
│   └── convention/
│       └── src/main/kotlin/
│           ├── AndroidApplicationConventionPlugin.kt
│           ├── AndroidLibraryConventionPlugin.kt
│           ├── KotlinAndroidConventionPlugin.kt
│           ├── ComposeConventionPlugin.kt
│           └── HiltConventionPlugin.kt
├── gradle/
│   ├── libs.versions.toml                            # Version catalog
│   └── wrapper/
├── build.gradle.kts
├── settings.gradle.kts
└── .github/workflows/
    ├── ci.yml                                        # Build, lint, detekt, test, coverage
    └── release.yml                                   # Build AAB, distribute
```

## 12. Design Patterns

### Repository Pattern
**When to use**: Every data access; abstracts network/database from domain.
**When not to use**: Trivial in-memory data (rare in production).
**Sketch**: `interface ArticleRepository { fun observeArticles(): Flow<List<Article>>; suspend fun refresh(): Result<Unit> }` — implementation in data layer combines Room + Retrofit; Hilt `@Binds` interface to impl.

### UseCase Pattern
**When to use**: Business logic that combines repositories or has rules; one responsibility per use case.
**When not to use**: Simple CRUD that maps directly to a repository call.
**Sketch**: `class GetArticleUseCase @Inject constructor(private val repo: ArticleRepository) { suspend operator fun invoke(id: ArticleId): Result<Article> = repo.getArticle(id) }`.

### MVI Pattern (Unidirectional Data Flow)
**When to use**: Complex screens with multiple actions and effects; easier to test than MVVM.
**When not to use**: Simple screens with few actions (MVVM suffices).
**Sketch**: `State` (sealed), `Action` (sealed), `Effect` (sealed); `ViewModel.onAction(action)` updates `StateFlow<State>` via reducer; `SharedFlow<Effect>` for one-shot events.

### Offline-First Pattern
**When to use**: Every app with network data; Room as source of truth.
**When not to use**: Apps with no local data (rare).
**Sketch**: UI observes Room `Flow` (always shows cached data); `RemoteMediator` or WorkManager fetches from network and writes to Room; Room `Flow` re-emits automatically; UI never waits for network.

### RemoteMediator Pattern (Paging 3)
**When to use**: Paginated network data with local cache; infinite scroll.
**When not to use**: Non-paginated data (use WorkManager sync).
**Sketch**: `ArticleRemoteMediator` extends `RemoteMediator<Int, ArticleEntity>`; `load(LoadType, state)` fetches page from network, writes to Room; `Pager(PagingConfig, remoteMediator) { ArticleDao.pagingSource() }` returns `Flow<PagingData<ArticleEntity>>`.

### Convention Plugin Pattern
**When to use**: Multi-module projects; eliminate build script duplication.
**When not to use**: Single-module apps.
**Sketch**: `AndroidLibraryConventionPlugin` applies `com.android.library`, `org.jetbrains.kotlin.android`; configures SDK, Java version, `Compose`; applied via `plugins { id("android.library") }` in module.

## 13. Best Practices

- Always use Clean Architecture: domain (pure Kotlin), application (ViewModels), data (Room, Retrofit); dependencies point inward.
- Always use Hilt for DI; `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module @InstallIn`.
- Always use `StateFlow` for UI state; `SharedFlow` for one-shot events; `collectAsStateWithLifecycle()`.
- Always use sealed `Result<T>` for domain errors; never throw exceptions for expected errors.
- Always use Room as source of truth (offline-first); UI observes Room `Flow`; network updates Room.
- Always use Paging 3 with `RemoteMediator` for paginated network data.
- Always use WorkManager for background sync (persistent, constraints-aware).
- Always use DataStore for preferences (never SharedPreferences).
- Always use `kotlinx-serialization` for JSON; never Gson, Moshi for new code.
- Always use KSP (not KAPT) for annotation processing.
- Always use version catalogs (`libs.versions.toml`) and convention plugins (`build-logic/`).
- Always use modularization: app, feature, core modules with explicit dependencies.
- Always use `@JvmInline value class` for ID wrappers; never raw `String`.
- Always write unit tests with JUnit5, MockK, Turbine; integration tests with Hilt; UI tests with Compose rule.
- Always run CI: build, lint, detekt, ktlint, test, coverage `>= 80%` for domain and data.
- Always document architecture decisions in `docs/architecture/`; ADRs (Architecture Decision Records).

## 14. Anti Patterns

### Anti-Pattern 1: Layer Violation (Data Depends on UI)
**Why wrong**: Breaks Clean Architecture dependency rule; UI changes break data layer; untestable.
**Correct alternative**: Dependencies point inward: `data → domain`, `application → domain`; domain has no dependencies on data or application.

### Anti-Pattern 2: God ViewModel (Multiple Responsibilities)
**Why wrong**: Hard to test, maintain, understand; violates Single Responsibility Principle.
**Correct alternative**: Split into multiple ViewModels or extract use cases; one ViewModel per screen with one responsibility.

### Anti-Pattern 3: SharedPreferences on Main Thread
**Why wrong**: Synchronous I/O on main thread; blocks UI; ANR risk; deprecated.
**Correct alternative**: Use DataStore (Preferences or Typed); coroutine-based; no main-thread blocks.

### Anti-Pattern 4: GlobalScope for Background Work
**Why wrong**: No parent scope; outlives the launching component; leaks; cannot be cancelled.
**Correct alternative**: Use WorkManager for persistent background work; `viewModelScope` for ViewModel; `lifecycleScope` for Activity/Fragment.

### Anti-Pattern 5: Throwing Exceptions for Expected Errors
**Why wrong**: Breaks type safety; callers must remember to catch; no compile-time enforcement; mixes with unexpected programming errors.
**Correct alternative**: Use sealed `Result<T>` for expected domain errors; `try`/`catch` for unexpected programming errors; `runCatching` for one-shot.

### Anti-Pattern 6: Per-Module Build Script Duplication
**Why wrong**: Boilerplate; version drift; hard to maintain; inconsistent config.
**Correct alternative**: Use convention plugins in `build-logic/`; apply via `plugins { id("android.library") }`; version catalogs for dependencies.

## 15. Performance Rules

- Never block the main thread; all IO on `Dispatchers.IO`, CPU on `Dispatchers.Default`.
- Use Room with `Flow` for observable queries; UI re-renders automatically on database change.
- Use Paging 3 for paginated data; only loads visible items; memory-efficient.
- Use `RemoteMediator` for network + database sync; avoids full reload on config change.
- Use `StateFlow` (not `LiveData`); conflated, no backpressure overhead.
- Use `flatMapLatest` for search-as-you-type; cancels previous search.
- Use `kotlinx-serialization` (not Gson); compile-time generated serializers are 2-3x faster.
- Use `@JvmInline value class` for ID wrappers; zero allocation.
- Use `ImmutableList` (kotlinx-collections-immutable) for Compose parameters; avoids recomposition.
- Profile with Android Studio Profiler; verify coroutine dispatcher usage.

## 16. Security Rules

- Never store secrets (API keys, tokens) in source code; use `BuildConfig` fields from `local.properties`.
- Always use HTTPS (`https://`); never HTTP in production; `cleartextTrafficPermitted="false"` in network security config.
- Always use `EncryptedSharedPreferences` or `DataStore` with encryption for sensitive data.
- Always pin certificates in `OkHttpClient` for high-security apps; never accept self-signed certs.
- Always validate input from network responses; never trust server data.
- Never log sensitive data (tokens, PII); `BuildConfig.DEBUG` guard for verbose logs.
- Always obfuscate with R8/ProGuard in release builds; never ship unobfuscated code.
- Always use `BiometricPrompt` for biometric auth; never roll your own.

## 17. Testing Strategy

- Every use case must have unit tests with JUnit5 and MockK; cover success, failure, edge cases.
- Every repository must have unit tests with fake data sources (in-memory Room, mock Retrofit); verify Flow emissions.
- Every ViewModel must have unit tests with `runTest` and Turbine; verify state transitions and effects.
- Use `MainDispatcherRule` to replace `Dispatchers.Main` with `UnconfinedTestDispatcher`.
- Use `@HiltAndroidTest` and `HiltAndroidRule` for integration tests with DI; `@UninstallModules` to replace modules.
- Use `createComposeRule` or `createAndroidComposeRule<MainActivity>` for Compose UI tests; assert on semantics.
- Use Robolectric for tests that need Android framework classes without emulator.
- Use Truth or Kotest assertions for fluent assertions.
- Run `./gradlew detekt ktlintCheck` in CI; zero violations.
- Run `./gradlew test` in CI; zero failures; coverage `>= 80%` for domain and data layers.
- Use snapshot tests with Paparazzi for visual regression of Compose UI (no emulator).
- Use Macrobenchmark for performance tests (cold start, frame rate, scroll).

## 18. Documentation Standards

- Every module must have a `README.md` with purpose, dependencies, public API, usage examples.
- Every architecture decision must be documented in an ADR (`docs/architecture/adr-<n>-<title>.md`).
- Every public class, function, and property must have KDoc with `@param`, `@return`, `@throws`.
- Every complex algorithm must have a comment explaining the algorithm and complexity.
- Every migration (e.g., add new module, add new feature) must have a guide in `docs/migrations/`.
- Every convention plugin must have KDoc explaining what it configures.
- Every CI workflow must have a `README.md` explaining triggers, jobs, secrets.
- Every incident must produce a postmortem in `docs/incidents/<date>-<slug>.md` with timeline, root cause, fix, prevention.

## 19. Code Review Checklist

- [ ] No layer violations: `data → domain`, `application → domain`; no reverse dependencies.
- [ ] `core-domain` has no Android dependencies (no `android.*` imports).
- [ ] Repository interface in `core-domain`; implementation in `core-data`; Hilt `@Binds`.
- [ ] Use case is single responsibility; `operator fun invoke`; `@Inject constructor`.
- [ ] ViewModel exposes `StateFlow<UiState>`; UI collects via `collectAsStateWithLifecycle()`.
- [ ] Sealed `Result<T>` for domain errors; no exceptions for expected errors.
- [ ] Room as source of truth (offline-first); UI observes Room `Flow`.
- [ ] Paging 3 with `RemoteMediator` for paginated network data.
- [ ] WorkManager for persistent background sync; constraints (network, charging).
- [ ] DataStore for preferences; never `SharedPreferences`.
- [ ] Hilt for DI: `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module @InstallIn`.
- [ ] `kotlinx-serialization` for JSON; no Gson, Moshi for new code.
- [ ] KSP (not KAPT) for annotation processing.
- [ ] Version catalog (`libs.versions.toml`) for dependencies; convention plugins for shared config.
- [ ] `@JvmInline value class` for ID wrappers; no raw `String` for IDs.
- [ ] No `GlobalScope`, no `runBlocking`, no `!!` in production code.
- [ ] Unit tests: JUnit5, MockK, Turbine; coverage `>= 80%` for domain and data.
- [ ] Compose UI tests for every screen; assert on semantics.
- [ ] Detekt and ktlint pass with zero violations.
- [ ] `allWarningsAsErrors = true` in CI; zero warnings.

## 20. Refactoring Checklist

- [ ] Extract `core-domain` module with pure Kotlin; move repository interfaces and domain models.
- [ ] Extract `core-data`, `core-network`, `core-database`, `core-ui`, `core-common` modules.
- [ ] Extract `feature-<name>` modules; one per feature; depend on `core-*` only.
- [ ] Create version catalog (`libs.versions.toml`); replace hardcoded versions.
- [ ] Create convention plugins in `build-logic/`; replace per-module boilerplate.
- [ ] Replace `SharedPreferences` with DataStore.
- [ ] Replace `LiveData` with `StateFlow`/`SharedFlow`.
- [ ] Replace `GlobalScope` with `viewModelScope`/`lifecycleScope`/WorkManager.
- [ ] Replace Gson with `kotlinx-serialization`.
- [ ] Replace KAPT with KSP for all annotation processors.
- [ ] Add sealed `Result<T>` for domain errors; replace thrown exceptions.
- [ ] Add `@JvmInline value class` for ID wrappers.
- [ ] Add Paging 3 with `RemoteMediator` for paginated data.
- [ ] Add offline-first: Room as source of truth; UI observes Room `Flow`.
- [ ] Add unit tests with JUnit5, MockK, Turbine; coverage `>= 80%`.

## 21. Deployment Checklist

- [ ] `./gradlew assembleRelease` succeeds; no warnings.
- [ ] Detekt and ktlint pass with zero violations.
- [ ] All unit tests pass (`./gradlew test`); coverage `>= 80%`.
- [ ] All integration tests pass (`./gradlew connectedAndroidTest` on emulator).
- [ ] R8/ProGuard enabled; mapping file uploaded to Firebase Crashlytics.
- [ ] App signing: keystore in CI secrets; `signingConfig` from `keystore.properties`.
- [ ] `BuildConfig` fields for API URLs, keys; no secrets in source.
- [ ] Network security config: `cleartextTrafficPermitted="false"`.
- [ ] App bundle (`.aab`) generated for Play Store; not APK.
- [ ] Version code and version name incremented; semantic versioning.
- [ ] Firebase Crashlytics, Analytics configured; symbols uploaded.
- [ ] LeakCanary in debug builds; no leaks detected.
- [ ] StrictMode in debug builds; no main-thread violations.
- [ ] Feature flags configured (Firebase Remote Config).
- [ ] Rollback plan: previous version bundle retained; staged rollout on Play Console.
- [ ] Database migrations tested on upgrade path (version N-1 to N).
- [ ] WorkManager tasks verified (periodic sync, constraints).

## 22. Production Checklist

- [ ] Clean Architecture: domain pure Kotlin, dependencies point inward; no layer violations.
- [ ] Modularization: app, feature-*, core-* modules with explicit dependencies.
- [ ] Hilt DI: `@HiltAndroidApp`, `@AndroidEntryPoint`, `@HiltViewModel`, `@Module @InstallIn`.
- [ ] Offline-first: Room as source of truth; UI observes Room `Flow`; network updates Room.
- [ ] Paging 3 with `RemoteMediator` for paginated network data.
- [ ] WorkManager for persistent background sync; constraints (network, charging).
- [ ] DataStore for preferences; no `SharedPreferences`.
- [ ] Sealed `Result<T>` for domain errors; no thrown exceptions for expected errors.
- [ ] `StateFlow`/`SharedFlow` for UI state/events; `collectAsStateWithLifecycle()`.
- [ ] `kotlinx-serialization` for JSON; KSP for annotation processing.
- [ ] Version catalog (`libs.versions.toml`); convention plugins (`build-logic/`).
- [ ] R8/ProGuard enabled; app obfuscated; mapping file uploaded.
- [ ] Crash reporting (Firebase Crashlytics) with symbols; alerting on crash spike.
- [ ] LeakCanary in debug builds; CI runs on emulator.
- [ ] StrictMode in debug builds; no main-thread violations.
- [ ] Cold start `< 1.5s` on mid-range device; frame time `< 16ms`.
- [ ] ANR rate `< 0.47%`; crash rate `< 1.0%` (Play Console).
- [ ] Detekt and ktlint in CI; zero violations.
- [ ] Test coverage `>= 80%` for domain and data layers.
- [ ] Runbook for layer violation, sync failure, cache invalidation, migration rollback.

## 23. Logging Strategy

- Use Timber for logging; plant `DebugTree` in `App.kt` for debug builds.
- Log user actions (button clicks, screen views) at `Log.i` for analytics.
- Log state transitions (loading → success, loading → error) at `Log.d` for debugging.
- Never log sensitive data (tokens, PII); redact in custom Timber tree.
- Log network requests via OkHttp `HttpLoggingInterceptor` at `Log.d` in debug; `NONE` in release.
- Log WorkManager task execution at `Log.i` with task name, result, duration.
- Log Paging 3 `RemoteMediator` load events at `Log.d` for debugging.
- Log Room migrations at `Log.i` with old version, new version.
- Use structured logging in release: JSON format with `event`, `properties`, `timestamp`; send to Firebase Analytics or custom backend.
- Sample release logs at 1% to avoid volume; 100% for errors.

## 24. Monitoring Strategy

- Firebase Crashlytics: crash reports with stack traces; grouped by exception; alert on crash rate spike.
- Firebase Performance Monitoring: app start time, network request latency, screen rendering time.
- Custom metrics via Firebase Analytics: screen views, user actions, funnel events.
- ANR monitoring: Play Console ANR rate; alert on `> 0.47%`.
- Memory monitoring: `LeakCanary` in debug; alert on memory leaks.
- Network monitoring: OkHttp `EventListener` for request timing; alert on slow requests `> 5s`.
- Database monitoring: Room `DatabaseConfiguration.Callback` for migration failures.
- WorkManager monitoring: `WorkManager.getWorkInfoByIdLiveData`; alert on failed tasks.
- Cold start monitoring: `Trace` API in `Application.onCreate()`; alert on cold start `> 1.5s`.
- Daily review: Crashlytics dashboard, ANR rate, crash rate, top crashes, sync task status.

## 25. Error Handling

- Use sealed `Result<T>` for domain errors; `Success(data)`, `Failure(error)`.
- Use `runCatching` for one-shot operations; map to `Result` at repository layer.
- Map network/IO errors to domain errors at repository layer (`DomainError.Network`, `DomainError.NotFound`).
- Use `try`/`catch` for recoverable errors in coroutines; `CoroutineExceptionHandler` for uncaught.
- Never catch `CancellationException`; let it propagate for structured concurrency.
- Surface user-facing errors via `SharedFlow<UiEffect>` (snackbar, dialog); never raw exception messages.
- Retry network requests with exponential backoff (3 retries, 1s/2s/4s); give up after max retries.
- Always preserve last-known-good state; UI shows stale data on error rather than blank screen.
- Log errors at `Log.e` with stack trace; send to Crashlytics with custom keys.
- Validate user input in real-time; show inline errors below fields.
- Database migration failures: alert immediately; rollback to previous database version.

## 26. Examples

### Example 1: Domain Layer (Pure Kotlin)

```kotlin
// core-domain/src/main/java/com/example/core/domain/model/Article.kt
package com.example.core.domain.model

import kotlinx.datetime.Instant

@JvmInline
value class ArticleId(val value: String)

data class Article(
    val id: ArticleId,
    val title: String,
    val description: String,
    val authorId: String,
    val publishedAt: Instant,
    val updatedAt: Instant,
    val heroImageUrl: String?,
    val tags: List<String>,
)

// core-domain/src/main/java/com/example/core/domain/repository/ArticleRepository.kt
package com.example.core.domain.repository

import com.example.core.domain.model.Article
import com.example.core.domain.model.ArticleId
import kotlinx.coroutines.flow.Flow

interface ArticleRepository {
    fun observeArticles(): Flow<List<Article>>
    fun observeArticle(id: ArticleId): Flow<Article?>
    suspend fun refreshArticles(): Result<Unit>
    suspend fun getArticle(id: ArticleId): Result<Article>
}

// core-domain/src/main/java/com/example/core/domain/usecase/GetArticleUseCase.kt
package com.example.core.domain.usecase

import com.example.core.domain.model.Article
import com.example.core.domain.model.ArticleId
import com.example.core.domain.repository.ArticleRepository
import javax.inject.Inject

class GetArticleUseCase @Inject constructor(
    private val repository: ArticleRepository,
) {
    suspend operator fun invoke(id: ArticleId): Result<Article> = repository.getArticle(id)
}
```

### Example 2: Data Layer with Offline-First Repository

```kotlin
// core-data/src/main/java/com/example/core/data/repository/ArticleRepositoryImpl.kt
package com.example.core.data.repository

import com.example.core.database.dao.ArticleDao
import com.example.core.domain.model.Article
import com.example.core.domain.model.ArticleId
import com.example.core.domain.repository.ArticleRepository
import com.example.core.network.ApiClient
import com.example.core.data.mapper.toArticle
import com.example.core.data.mapper.toEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ArticleRepositoryImpl @Inject constructor(
    private val apiClient: ApiClient,
    private val articleDao: ArticleDao,
) : ArticleRepository {

    override fun observeArticles(): Flow<List<Article>> =
        articleDao.observeAll().map { entities -> entities.map { it.toArticle() } }

    override fun observeArticle(id: ArticleId): Flow<Article?> =
        articleDao.observeById(id.value).map { it?.toArticle() }

    override suspend fun refreshArticles(): Result<Unit> = runCatching {
        val response = apiClient.getArticles()
        val entities = response.articles.map { it.toEntity() }
        articleDao.upsertAll(entities)
    }

    override suspend fun getArticle(id: ArticleId): Result<Article> = runCatching {
        // Try cache first
        val cached = articleDao.findById(id.value)
        if (cached != null) {
            return@runCatching cached.toArticle()
        }
        // Fetch from network
        val response = apiClient.getArticle(id.value)
        articleDao.insert(response.toEntity())
        response.toArticle()
    }
}

// core-data/src/main/java/com/example/core/data/di/DataModule.kt
package com.example.core.data.di

import com.example.core.data.repository.ArticleRepositoryImpl
import com.example.core.domain.repository.ArticleRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class DataModule {
    @Binds
    @Singleton
    abstract fun bindArticleRepository(impl: ArticleRepositoryImpl): ArticleRepository
}
```

### Example 3: Paging 3 with RemoteMediator

```kotlin
// core-data/src/main/java/com/example/core/data/paging/ArticleRemoteMediator.kt
package com.example.core.data.paging

import androidx.paging.RemoteMediator
import androidx.paging.LoadType
import androidx.paging.PagingState
import com.example.core.database.AppDatabase
import com.example.core.database.entity.ArticleEntity
import com.example.core.network.ApiClient
import javax.inject.Inject
import java.util.concurrent.TimeUnit

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class ArticleRemoteMediator @Inject constructor(
    private val apiClient: ApiClient,
    private val database: AppDatabase,
) : RemoteMediator<Int, ArticleEntity>() {

    override suspend fun load(
        loadType: LoadType,
        state: PagingState<Int, ArticleEntity>,
    ): MediatorResult {
        return try {
            val page = when (loadType) {
                LoadType.REFRESH -> 1
                LoadType.PREPEND -> return MediatorResult.Success(endOfPaginationReached = true)
                LoadType.APPEND -> {
                    val lastItem = state.lastItemOrNull()
                    (lastItem?.page?.plus(1)) ?: return MediatorResult.Success(endOfPaginationReached = true)
                }
            }

            val response = apiClient.getArticles(page = page, pageSize = state.config.pageSize)
            val entities = response.articles.map { it.toEntity(page) }

            database.withTransaction {
                if (loadType == LoadType.REFRESH) {
                    database.articleDao().clearAll()
                }
                database.articleDao().upsertAll(entities)
            }

            MediatorResult.Success(endOfPaginationReached = response.articles.size < state.config.pageSize)
        } catch (e: Exception) {
            MediatorResult.Error(e)
        }
    }
}
```

### Example 4: MVI ViewModel with StateFlow and SharedFlow

```kotlin
// feature-articledetail/src/main/java/com/example/feature/articledetail/ArticleDetailViewModel.kt
package com.example.feature.articledetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.domain.model.ArticleId
import com.example.core.domain.usecase.GetArticleUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface ArticleDetailState {
    data object Loading : ArticleDetailState
    data class Success(val article: com.example.core.domain.model.Article) : ArticleDetailState
    data class Error(val message: String) : ArticleDetailState
}

sealed interface ArticleDetailAction {
    data class Load(val articleId: ArticleId) : ArticleDetailAction
    data object Retry : ArticleDetailAction
}

sealed interface ArticleDetailEffect {
    data class ShowSnackbar(val message: String) : ArticleDetailEffect
    data object NavigateBack : ArticleDetailEffect
}

@HiltViewModel
class ArticleDetailViewModel @Inject constructor(
    private val getArticleUseCase: GetArticleUseCase,
) : ViewModel() {

    private val _uiState = MutableStateFlow<ArticleDetailState>(ArticleDetailState.Loading)
    val uiState: StateFlow<ArticleDetailState> = _uiState.asStateFlow()

    private val _uiEffect = MutableSharedFlow<ArticleDetailEffect>()
    val uiEffect: SharedFlow<ArticleDetailEffect> = _uiEffect.asSharedFlow()

    private var lastLoadedId: ArticleId? = null

    fun onAction(action: ArticleDetailAction) {
        when (action) {
            is ArticleDetailAction.Load -> {
                lastLoadedId = action.articleId
                loadArticle(action.articleId)
            }
            ArticleDetailAction.Retry -> {
                lastLoadedId?.let { loadArticle(it) }
            }
        }
    }

    private fun loadArticle(articleId: ArticleId) {
        _uiState.value = ArticleDetailState.Loading
        viewModelScope.launch {
            getArticleUseCase(articleId)
                .onSuccess { article ->
                    _uiState.value = ArticleDetailState.Success(article)
                }
                .onFailure { error ->
                    _uiState.value = ArticleDetailState.Error(
                        message = error.message ?: "Failed to load article",
                    )
                    _uiEffect.emit(ArticleDetailEffect.ShowSnackbar("Failed to load article"))
                }
        }
    }
}
```

## 27. Common Mistakes

### Mistake 1: Layer Violation (Data Depends on UI)
**What**: Engineer imports `androidx.compose.*` in `core-data` module.
**Why wrong**: Breaks Clean Architecture dependency rule; UI changes break data layer; untestable; domain and data should not know about UI.
**How to avoid**: Enforce module isolation in Gradle; `core-domain` and `core-data` have no `androidx.compose.*` or `androidx.ui.*` dependencies; use Detekt rule to enforce.

### Mistake 2: God ViewModel with Multiple Responsibilities
**What**: Engineer puts all logic for a screen into a single 1000-line ViewModel.
**Why wrong**: Hard to test, maintain, understand; violates Single Responsibility Principle; multiple developers conflict.
**How to avoid**: Split into multiple ViewModels (one per screen section) or extract use cases; one ViewModel per screen with one responsibility.

### Mistake 3: SharedPreferences on Main Thread
**What**: Engineer uses `SharedPreferences.getString()` in `onCreate()`.
**Why wrong**: Synchronous I/O on main thread; blocks UI; ANR risk; deprecated.
**How to avoid**: Use DataStore (Preferences or Typed); coroutine-based; no main-thread blocks.

### Mistake 4: GlobalScope for Background Work
**What**: Engineer uses `GlobalScope.launch { ... }` for a sync task.
**Why wrong**: No parent scope; outlives the launching component; leaks; cannot be cancelled.
**How to avoid**: Use WorkManager for persistent background work; `viewModelScope` for ViewModel; `lifecycleScope` for Activity/Fragment.

### Mistake 5: Throwing Exceptions for Expected Errors
**What**: Engineer throws `IOException("Network error")` from repository when network fails.
**Why wrong**: Breaks type safety; callers must remember to catch; no compile-time enforcement; mixes with unexpected programming errors.
**How to avoid**: Use sealed `Result<T>` for expected domain errors (`Result.Failure(DomainError.Network)`); `try`/`catch` for unexpected programming errors; `runCatching` for one-shot.

### Mistake 6: Per-Module Build Script Duplication
**What**: Engineer copies the same `android { ... }` block into every module's `build.gradle.kts`.
**Why wrong**: Boilerplate; version drift; hard to maintain; inconsistent config across modules.
**How to avoid**: Use convention plugins in `build-logic/`; apply via `plugins { id("android.library") }`; version catalogs for dependencies.

## 28. Professional Workflow

1. **Receive feature brief** — feature description, design mockups, API contract, deadline.
2. **Design domain layer** — entities, repository interfaces, use cases; pure Kotlin, no Android deps.
3. **Design data layer** — Room entities, DAOs, Retrofit APIs, repository implementations, mappers.
4. **Choose MVVM or MVI** — MVVM for simple state; MVI for complex state with multiple actions and effects.
5. **Plan module structure** — `feature-<name>` for the feature; depends on `core-domain`, `core-data`, `core-ui`.
6. **Plan DI** — `@HiltViewModel` for ViewModel; `@Module @InstallIn(SingletonComponent::class)` for data; `@Binds` for interface-to-impl.
7. **Plan offline-first** — Room as source of truth; UI observes Room `Flow`; network updates Room.
8. **Plan Paging** — `RemoteMediator` for paginated network data; `LazyPagingItems` in Compose.
9. **Plan WorkManager** — periodic sync with constraints; `CoroutineWorker` for suspend work.
10. **Write domain layer** — entities, interfaces, use cases; pure Kotlin.
11. **Write data layer** — Room, Retrofit, repository impl, mappers; Hilt `@Binds`.
12. **Write application layer** — ViewModel with `StateFlow`, `onAction` reducer, `SharedFlow<Effect>`.
13. **Write UI layer** — Compose Screen (stateful, `hiltViewModel`), Content (stateless).
14. **Write tests** — unit (JUnit5, MockK, Turbine), integration (Hilt), UI (Compose rule); coverage `>= 80%`.
15. **Run CI** — build, lint, detekt, ktlint, test, coverage; all green.
16. **Open PR** — include architecture diagram, test results, coverage report.
17. **Code review** — checklist (layer isolation, sealed Result, offline-first, Hilt, no GlobalScope); CI passes.
18. **Deploy to internal testing** — Firebase App Distribution; QA tests.
19. **Deploy to production** — staged rollout on Play Console (10% → 50% → 100%); monitor Crashlytics, ANR rate, sync task status.
20. **Postmortem** — for any P1 incident (layer violation, sync failure, cache invalidation, migration rollback).

## 29. Response Style

- Always cite the Clean Architecture dependency rule (dependencies point inward); never reason from intuition.
- Always prescribe sealed `Result<T>` for domain errors; never suggest thrown exceptions for expected errors.
- Always prescribe Hilt for DI; never suggest manual DI or Dagger for new code.
- Always prescribe Room as source of truth (offline-first); never suggest network-only or cache-only.
- Always prescribe Paging 3 with `RemoteMediator` for paginated data; never suggest manual pagination.
- Always prescribe WorkManager for background sync; never suggest `GlobalScope` or foreground service for routine sync.
- Always prescribe version catalogs and convention plugins; never suggest per-module build script duplication.
- Always use authoritative voice: "must", "never", "forbidden"; never "might consider" or "perhaps".
- Always close with the next action: "Write unit tests with JUnit5 and Turbine, verify coverage >= 80%, open PR".

## 30. Output Format

- Every architecture review begins with the module structure, dependency graph, and identified violations; format as a table.
- Every recommendation includes: anti-pattern, why wrong, correct alternative, code snippet (syntactically valid Kotlin).
- Every code example is syntactically valid Kotlin 2.0+; never pseudocode; include imports for non-trivial examples.
- Every domain layer example is pure Kotlin with no Android dependencies; verified by Gradle module isolation.
- Every data layer example uses Room + Retrofit + `kotlinx-serialization`; Hilt `@Binds` for interface-to-impl.
- Every ViewModel example uses `StateFlow`/`SharedFlow` with sealed state/actions/effects; `viewModelScope` for coroutines.
- Every Gradle example is `build.gradle.kts` with `libs.versions.toml` references; convention plugins for shared config.
- Every PR description includes architecture diagram, test results, coverage report, migration plan (if schema change).
- Every incident report includes: timeline, root cause (layer violation, sync failure, cache invalidation), fix, prevention.
- Every quarterly review includes: module dependency graph, test coverage trend, dependency update status, architecture debt.
