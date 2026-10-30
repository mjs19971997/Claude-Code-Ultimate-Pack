# Kotlin for Android

Kotlin language and coroutine guidance absorbed from the former android-kotlin-expert skill. Verified against Kotlin 2.4.21, kotlinx.coroutines 1.11 and kotlinx.serialization 1.12 as used on Android (2026-10). For new language features in your exact Kotlin version, check the "What's new" page on kotlinlang.org.

## 1. Language idioms

- **Null safety.** `?.`, `?:`, smart casts and `requireNotNull(value) { "message" }`; no `!!` outside tests.
- **Immutability.** `val` by default; read-only `List`/`Map` in APIs; `copy()` on data classes for state updates.
- **Sealed hierarchies.** `sealed interface` for UI state, results and events; `when` without `else` so new subtypes cause compile errors.
- **Value classes.** `@JvmInline value class UserId(val value: String)` gives type safety for IDs; boxing still happens when used as nullable, generic or through interfaces.
- **Scope functions.** `apply` to configure an object, `also` for side effects, `let` for nullable chains and scoped results, `run`/`with` for computing a value from a receiver. Avoid nesting them.
- **Extensions.** Use for mapping (`fun ArticleDto.toEntity()`) and small utilities; keep them close to the types they serve and `private`/`internal` when possible.
- **Delegation.** `by lazy` for expensive one-time initialization (thread-safe by default), `by viewModels()` / `by activityViewModels()` in Views, interface delegation (`class Logging(inner: Repo) : Repo by inner`).
- **Constants.** `const val` for compile-time primitives and strings; `SCREAMING_SNAKE_CASE` naming.
- **`lateinit`.** Only for non-null properties set by a framework before use (for example injected fields); otherwise constructor parameters or `lazy`.

## 2. Coroutines

### Scopes and ownership

| Work | Scope |
|---|---|
| Screen logic | `viewModelScope` |
| View-bound UI work | `lifecycleScope` with `repeatOnLifecycle` |
| Composable event handlers | `rememberCoroutineScope()` |
| Work that outlives a screen but not the process | injected application `CoroutineScope` (`SupervisorJob`) |
| Work that must survive process death | WorkManager |

`GlobalScope` has no owner and cannot be cancelled or replaced in tests.

### Main safety and dispatchers

- A suspend function must be safe to call from the main thread; it switches dispatchers internally with `withContext(ioDispatcher)` when it blocks.
- Inject dispatchers (`@IoDispatcher`); use `Dispatchers.Default` for CPU-bound work such as parsing or sorting large collections.
- Room, Retrofit and DataStore suspend APIs are already main-safe.

### Concurrency inside a coroutine

```kotlin
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

suspend fun loadDashboard(api: DashboardApi): Dashboard = coroutineScope {
    val profile = async { api.profile() }
    val feed = async { api.feed() }
    Dashboard(profile.await(), feed.await())   // if one fails, the other is cancelled
}
```

- `coroutineScope` fails fast: one child failure cancels siblings and rethrows. `supervisorScope` lets siblings continue; handle each child's failure.
- Use `launch` for fire-and-forget children and `async` only when you `await` the result.

### Cancellation

- Cancellation is cooperative: long loops call `ensureActive()` or `yield()`; blocking calls need interruptible alternatives.
- Never swallow `CancellationException`. Catch specific exceptions; if you must catch broadly, rethrow cancellation first.

```kotlin
import kotlinx.coroutines.CancellationException

suspend inline fun <T> suspendRunCatching(block: () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        Result.failure(e)
    }
```

`runCatching` from the standard library catches `Throwable`, including `CancellationException`, so it is unsafe in suspend code without such a wrapper.

- Cleanup that must run even after cancellation goes in `finally`; if the cleanup suspends, wrap it in `withContext(NonCancellable)`.
- `CoroutineExceptionHandler` only applies to root coroutines (`launch` on a scope); it is a last-resort logger, not error handling.

### Bridging callbacks

```kotlin
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

fun LocationClient.updates(): Flow<Location> = callbackFlow {
    val listener = LocationListener { location -> trySend(location) }
    register(listener)
    awaitClose { unregister(listener) }
}
```

Use `suspendCancellableCoroutine` for single-result callbacks and register an `invokeOnCancellation` handler that cancels the underlying request.

## 3. Flow

### Cold and hot

- `Flow` is cold: each collector runs the producer again. Room queries and `callbackFlow` are cold.
- `StateFlow` is hot, always has a value, conflates and skips equal values; use it for state.
- `SharedFlow` is hot with configurable replay and buffer; use it to share an expensive upstream between collectors.
- `stateIn` / `shareIn` turn cold flows hot inside a scope. In ViewModels use `SharingStarted.WhileSubscribed(5_000)`.

### Operators that matter

| Operator | Use |
|---|---|
| `map`, `filter`, `distinctUntilChanged` | transform and de-duplicate |
| `combine` | merge latest values of several flows into one state |
| `flatMapLatest` | switch to a new inner flow and cancel the old one (search queries, selected id) |
| `debounce` | wait for input to settle (marked `@FlowPreview`) |
| `catch` | handle upstream errors and emit a fallback; does not catch downstream errors |
| `onStart`, `onCompletion` | emit loading markers, cleanup |
| `flowOn` | change the dispatcher of upstream operators |
| `conflate`, `buffer`, `collectLatest` | control backpressure |

```kotlin
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn

@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
class SearchViewModel(private val repository: SearchRepository) : ViewModel() {
    private val query = MutableStateFlow("")

    val results: StateFlow<List<Article>> = query
        .debounce(300)
        .distinctUntilChanged()
        .flatMapLatest { q -> if (q.isBlank()) flowOf(emptyList()) else repository.search(q) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun onQueryChange(value: String) {
        query.value = value
    }
}
```

### One-shot events

Prefer modelling outcomes as state (`val snackbarMessage: String?` plus an `onMessageShown()` call). When an event stream is unavoidable:

```kotlin
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow

private val _events = Channel<UiEvent>(Channel.BUFFERED)
val events = _events.receiveAsFlow()
```

Collect it in the UI with lifecycle awareness (`LaunchedEffect` + `repeatOnLifecycle`, or `ObserveAsEvents`-style helpers). Each event is delivered to one collector.

## 4. kotlinx.serialization

```kotlin
import java.time.Instant
import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.json.Json

object InstantIsoSerializer : KSerializer<Instant> {
    override val descriptor: SerialDescriptor =
        PrimitiveSerialDescriptor("com.example.InstantIso", PrimitiveKind.STRING)

    override fun serialize(encoder: Encoder, value: Instant) = encoder.encodeString(value.toString())

    override fun deserialize(decoder: Decoder): Instant = Instant.parse(decoder.decodeString())
}

@Serializable
data class CommentDto(
    val id: String,
    @SerialName("author_name") val authorName: String,
    @Serializable(with = InstantIsoSerializer::class)
    @SerialName("created_at") val createdAt: Instant,
    val tags: List<String> = emptyList(),
)

val appJson = Json {
    ignoreUnknownKeys = true      // tolerate new server fields
    explicitNulls = false         // missing nullable fields decode as null
}
```

- Apply the `org.jetbrains.kotlin.plugin.serialization` Gradle plugin; serializers are generated at compile time, so no reflection keep rules are needed for `@Serializable` classes beyond what the library ships.
- `java.time` is available from API 26; for lower `minSdk` enable core library desugaring.
- Sealed hierarchies serialize polymorphically with a `type` discriminator; set `@SerialName` on each subclass so renames do not break the wire format.
- Catch `SerializationException` (and `IllegalArgumentException` from custom parsers) at the data source and map to a domain error.

## 5. Gradle Kotlin DSL

- Use `build.gradle.kts` and the version catalog accessors (`libs.androidx.compose.material3`); no hard-coded versions in module scripts.
- Configure the JVM toolchain once in a convention plugin (`kotlin { jvmToolchain(17) }` or the AGP-equivalent `compileOptions`) rather than per module.
- Treat compiler warnings as errors in CI (`kotlin { compilerOptions { allWarningsAsErrors.set(true) } }`) once the codebase is clean.
- KSP replaces KAPT for Room, Hilt and Moshi codegen; KAPT is in maintenance mode and slower because it generates Java stubs.

## 6. Common mistakes

- `runCatching { api.call() }` in a coroutine: cancellation becomes a failure result and the coroutine keeps running.
- `async` without `await`: exceptions surface late or are lost; use `launch`.
- `flow.collect` inside `init` of a ViewModel to copy values into another `MutableStateFlow`: use `stateIn` or `combine` instead.
- `catch` placed after `stateIn` expecting to catch upstream errors from inside the shared flow; put `catch` before sharing.
- `withContext(Dispatchers.IO)` around Room or Retrofit suspend calls everywhere: harmless but noisy; reserve it for genuinely blocking code.
- Mutable collections inside `StateFlow` values: mutating in place does not emit; always emit new instances.
