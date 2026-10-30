# Android Architecture

Architecture guidance absorbed from the former android-architecture-expert skill: layers, modules, dependency injection, persistence, networking, paging, background sync and test setup. Verified against Android Gradle Plugin 9.5.0, Kotlin 2.4.21, Room 2.8.5, WorkManager 2.12.0, DataStore 1.3.0, Hilt (androidx.hilt) 1.4.0 and Compose BOM 2026.09.00 (2026-10). Code targets Room 2.8, Retrofit with its kotlinx.serialization converter, Paging 3, WorkManager and androidx.hilt 1.4; a separate Room 3 line exists, so check its release notes before adopting it.

## 1. Layers

| Layer | Contains | Depends on |
|---|---|---|
| UI | composables, ViewModels, UI state classes | domain (optional), data interfaces, model |
| Domain (optional) | use cases with business rules shared by several ViewModels | data interfaces, model |
| Data | repositories, data sources (Room, Retrofit, DataStore), mappers, sync workers | model |
| Model | plain Kotlin data classes and value classes | nothing Android |

Rules:

- Repositories are the single source of truth for their data and the only place that knows about both network and database.
- Each layer exposes its own types; DTOs and entities are mapped at the repository boundary.
- ViewModels are scoped to a screen or navigation entry and survive configuration changes; they receive arguments through `SavedStateHandle` or assisted injection.
- Feature modules never depend on each other; shared code moves to a core module and navigation between features goes through the app module or navigation keys in a shared module.

## 2. Model and database

```kotlin
// core/model
@JvmInline
value class ArticleId(val value: String)

data class Article(val id: ArticleId, val title: String, val summary: String)
```

```kotlin
// core/database
import androidx.paging.PagingSource
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "articles")
data class ArticleEntity(
    @PrimaryKey val id: String,
    val title: String,
    val summary: String,
    val page: Int = 0,          // set by the RemoteMediator for paged feeds
)

@Dao
interface ArticleDao {
    @Query("SELECT * FROM articles ORDER BY page ASC, id ASC")
    fun observeAll(): Flow<List<ArticleEntity>>

    @Query("SELECT * FROM articles ORDER BY page ASC, id ASC")
    fun pagingSource(): PagingSource<Int, ArticleEntity>

    @Upsert
    suspend fun upsertAll(articles: List<ArticleEntity>)

    @Query("DELETE FROM articles")
    suspend fun clearAll()
}

@Database(entities = [ArticleEntity::class], version = 2, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun articleDao(): ArticleDao
}
```

- Export schemas (Room Gradle plugin `room { schemaDirectory("$projectDir/schemas") }`) and commit them; they power `MigrationTestHelper` and auto-migrations.
- Use `@AutoMigration` for additive changes and hand-written `Migration` objects for renames, splits and data transforms.
- `Flow`-returning DAO queries re-emit on every write to the tables they read; `suspend` DAO functions run on Room's executors and are main-safe.

```kotlin
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE articles ADD COLUMN page INTEGER NOT NULL DEFAULT 0")
    }
}
```

## 3. Network

```kotlin
// core/network
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.http.GET
import retrofit2.http.Query

@Serializable
data class ArticleDto(
    val id: String,
    val title: String,
    @SerialName("summary_text") val summary: String = "",
)

interface ArticleApi {
    @GET("articles")
    suspend fun getArticles(): List<ArticleDto>

    @GET("articles")
    suspend fun getArticlesPage(
        @Query("page") page: Int,
        @Query("page_size") pageSize: Int,
    ): List<ArticleDto>
}
```

```kotlin
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true }

    @Provides
    @Singleton
    fun provideOkHttp(): OkHttpClient =
        OkHttpClient.Builder()
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BASIC))
                }
            }
            .build()

    @Provides
    @Singleton
    fun provideArticleApi(client: OkHttpClient, json: Json): ArticleApi =
        Retrofit.Builder()
            .baseUrl("https://api.example.com/")
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ArticleApi::class.java)
}
```

- `BuildConfig` here is the network module's generated class (enable `buildFeatures { buildConfig = true }`); it is fine for flags like `DEBUG` and non-secret base URLs, never for keys.
- Attach the user's session token with an OkHttp `Interceptor` that reads it from the token store; refresh expired tokens in an `Authenticator`, not in every call site.
- Use `Level.BASIC` or `HEADERS` with `redactHeader("Authorization")` in debug; never log bodies containing personal data.

## 4. Dependency injection

```kotlin
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Qualifier
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class IoDispatcher

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class ApplicationScope

@Module
@InstallIn(SingletonComponent::class)
abstract class DataModule {
    @Binds
    @Singleton
    abstract fun bindArticleRepository(impl: OfflineFirstArticleRepository): ArticleRepository
}

@Module
@InstallIn(SingletonComponent::class)
object CoroutinesModule {
    @Provides
    @IoDispatcher
    fun provideIoDispatcher(): CoroutineDispatcher = Dispatchers.IO

    @Provides
    @Singleton
    @ApplicationScope
    fun provideApplicationScope(@IoDispatcher io: CoroutineDispatcher): CoroutineScope =
        CoroutineScope(SupervisorJob() + io)
}
```

- Hilt entry points: `@HiltAndroidApp` on the `Application`, `@AndroidEntryPoint` on activities, `@HiltViewModel` + `@Inject constructor` on ViewModels; in Compose obtain them with `hiltViewModel()` from `androidx.hilt.lifecycle.viewmodel.compose`.
- Use the application scope for work that must finish even if the screen closes but not survive process death (for example writing a draft); anything stronger belongs in WorkManager.
- Run Hilt and Room through KSP; check that the KSP and Dagger versions you use support your Kotlin version and AGP 9 built-in Kotlin.

## 5. Paging 3 with RemoteMediator

```kotlin
import androidx.paging.ExperimentalPagingApi
import androidx.paging.LoadType
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import androidx.paging.PagingState
import androidx.paging.RemoteMediator
import androidx.room.withTransaction
import java.io.IOException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import retrofit2.HttpException

@OptIn(ExperimentalPagingApi::class)
class ArticleRemoteMediator(
    private val api: ArticleApi,
    private val db: AppDatabase,
) : RemoteMediator<Int, ArticleEntity>() {

    override suspend fun load(
        loadType: LoadType,
        state: PagingState<Int, ArticleEntity>,
    ): MediatorResult {
        val page = when (loadType) {
            LoadType.REFRESH -> 1
            LoadType.PREPEND -> return MediatorResult.Success(endOfPaginationReached = true)
            LoadType.APPEND -> {
                val last = state.lastItemOrNull()
                    ?: return MediatorResult.Success(endOfPaginationReached = true)
                last.page + 1
            }
        }
        return try {
            val items = api.getArticlesPage(page = page, pageSize = state.config.pageSize)
            db.withTransaction {
                if (loadType == LoadType.REFRESH) db.articleDao().clearAll()
                db.articleDao().upsertAll(items.map { it.toEntity(page) })
            }
            MediatorResult.Success(endOfPaginationReached = items.size < state.config.pageSize)
        } catch (e: CancellationException) {
            throw e
        } catch (e: IOException) {
            MediatorResult.Error(e)
        } catch (e: HttpException) {
            MediatorResult.Error(e)
        }
    }
}

private fun ArticleDto.toEntity(page: Int) = ArticleEntity(id = id, title = title, summary = summary, page = page)

@OptIn(ExperimentalPagingApi::class)
fun articlePager(api: ArticleApi, db: AppDatabase): Flow<PagingData<ArticleEntity>> =
    Pager(
        config = PagingConfig(pageSize = 30),
        remoteMediator = ArticleRemoteMediator(api, db),
        pagingSourceFactory = { db.articleDao().pagingSource() },
    ).flow
```

- Map `PagingData<ArticleEntity>` to models with `.map { pagingData -> pagingData.map { it.toModel() } }` and `cachedIn(viewModelScope)` in the ViewModel.
- In Compose collect with `collectAsLazyPagingItems()` and use `itemKey { it.id.value }` for keys.
- For APIs with cursors, store the next cursor in a remote-keys table instead of deriving it from the last item.

## 6. WorkManager sync

```kotlin
import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val repository: ArticleRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result =
        repository.refresh().fold(
            onSuccess = { Result.success() },
            onFailure = { if (runAttemptCount < 3) Result.retry() else Result.failure() },
        )

    companion object {
        fun schedule(workManager: WorkManager) {
            val request = PeriodicWorkRequestBuilder<SyncWorker>(6, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            workManager.enqueueUniquePeriodicWork("article-sync", ExistingPeriodicWorkPolicy.KEEP, request)
        }
    }
}
```

- `@HiltWorker` requires the `Application` to implement `Configuration.Provider` with an injected `HiltWorkerFactory`, and the default WorkManager initializer removed from the manifest.
- Use unique work names so app restarts do not enqueue duplicates.
- Expedited work (`setExpedited`) is for short user-visible tasks; long transfers use foreground service types declared in the manifest.

## 7. DataStore

```kotlin
import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.settingsStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class SettingsRepository(private val context: Context) {
    private val darkThemeKey = booleanPreferencesKey("dark_theme")

    val darkTheme: Flow<Boolean> = context.settingsStore.data.map { it[darkThemeKey] ?: false }

    suspend fun setDarkTheme(enabled: Boolean) {
        context.settingsStore.edit { it[darkThemeKey] = enabled }
    }
}
```

Create exactly one DataStore instance per file (the `preferencesDataStore` delegate at top level guarantees this). Store encrypted session tokens (see section 10) as Base64 strings or in a typed DataStore.

## 8. Build logic

```toml
# gradle/libs.versions.toml (excerpt; add the other libraries you use)
[versions]
agp = "9.5.0"
kotlin = "2.4.21"
composeBom = "2026.09.00"
androidxHilt = "1.4.0"

[libraries]
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
androidx-compose-material3 = { group = "androidx.compose.material3", name = "material3" }
androidx-hilt-lifecycle-viewmodel-compose = { group = "androidx.hilt", name = "hilt-lifecycle-viewmodel-compose", version.ref = "androidxHilt" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
android-library = { id = "com.android.library", version.ref = "agp" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
```

```kotlin
// build-logic/convention/src/main/kotlin/AndroidLibraryConventionPlugin.kt
import com.android.build.api.dsl.LibraryExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

class AndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("com.android.library")
            extensions.configure<LibraryExtension> {
                compileSdk = 37
                defaultConfig.minSdk = 26
                testOptions.unitTests.isIncludeAndroidResources = true
            }
        }
    }
}
```

- Register convention plugins in `build-logic/convention/build.gradle.kts` (`gradlePlugin { plugins { register(...) } }`) and include the build with `pluginManagement { includeBuild("build-logic") }`.
- AGP 9 applies Kotlin itself (built-in Kotlin); do not also apply `org.jetbrains.kotlin.android`. Compose modules still apply `org.jetbrains.kotlin.plugin.compose`.
- Keep versions only in the catalog; use the Compose BOM so Compose artifacts stay aligned.

## 9. Test setup

```kotlin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestDispatcher
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.rules.TestWatcher
import org.junit.runner.Description

@OptIn(ExperimentalCoroutinesApi::class)
class MainDispatcherRule(
    val testDispatcher: TestDispatcher = UnconfinedTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) = Dispatchers.setMain(testDispatcher)
    override fun finished(description: Description) = Dispatchers.resetMain()
}
```

```kotlin
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class FakeArticleRepository(
    private val refreshResult: Result<Unit> = Result.success(Unit),
) : ArticleRepository {
    val articles = MutableStateFlow<List<Article>>(emptyList())
    override fun observeArticles(): Flow<List<Article>> = articles
    override suspend fun refresh(): Result<Unit> = refreshResult
}

class ArticleListViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun refreshFailureShowsError() = runTest {
        val viewModel = ArticleListViewModel(
            FakeArticleRepository(refreshResult = Result.failure(IOException("offline"))),
        )
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect {} }

        assertEquals("Could not refresh articles.", viewModel.uiState.value.errorMessage)
        assertEquals(false, viewModel.uiState.value.isRefreshing)
    }
}
```

Collecting in `backgroundScope` keeps the `WhileSubscribed` upstream active for the assertion and is cancelled automatically when the test ends.

## 10. Token encryption with the Android Keystore

Encrypts the per-user session token before it is written to DataStore. The key is non-exportable and never leaves the Keystore.

```kotlin
package com.example.core.datastore

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class TokenCipher(private val keyAlias: String = "session_token_key") {

    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun secretKey(): SecretKey {
        (keyStore.getEntry(keyAlias, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                keyAlias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    /** Returns IV length, IV and ciphertext in one array; store it (e.g. Base64) in DataStore. */
    fun encrypt(plaintext: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())   // Keystore generates a random IV
        val iv = cipher.iv
        return byteArrayOf(iv.size.toByte()) + iv + cipher.doFinal(plaintext)
    }

    fun decrypt(blob: ByteArray): ByteArray {
        val ivLength = blob[0].toInt()
        val iv = blob.copyOfRange(1, 1 + ivLength)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
        return cipher.doFinal(blob, 1 + ivLength, blob.size - 1 - ivLength)
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
    }
}
```

The token is the per-user session token your backend issues after sign-in. Keystore keys are deleted on uninstall and may be invalidated (for example after a lock-screen change for keys bound to user authentication), so treat decryption failure as "signed out".
