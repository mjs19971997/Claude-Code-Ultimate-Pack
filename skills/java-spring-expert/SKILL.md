---
name: java-spring-expert
description: >-
  Writes and reviews modern Java 21/25 code and Spring Boot 4 (Spring Framework 7) services: records, sealed types, pattern matching, virtual threads, dependency injection, Spring Data JPA with Flyway, Spring Security, Actuator, and JUnit with Testcontainers. Use when working with pom.xml, build.gradle, application.yml, @Transactional, JpaRepository, SecurityFilterChain, @SpringBootTest, N+1 queries, LazyInitializationException, or virtual thread pinning. Not for Kotlin Android apps (use android-expert), container images (use docker-expert), generic REST design (use rest-api-expert), OAuth/OIDC protocol design (use authentication-expert), or metrics and tracing backends (use observability-expert).
license: MIT
metadata:
  version: "3.1.0"
---

# Java and Spring Expert

This skill covers server-side Java on the JVM with Spring Boot: language features of Java 21 and Java 25 that matter in application code, Spring Boot project setup, dependency injection and configuration, persistence with Spring Data JPA and Hibernate, Spring Security, virtual threads, Actuator, and testing with JUnit and Testcontainers. It also covers the Spring Boot 3 to 4 migration points that break code. API design, container packaging, protocol-level identity design and observability backends are left to the skills named in section 1.

> Verified against Java 21 and 25 (LTS), Spring Boot 4.1.2 (Spring Framework 7.0.10, Spring Security 7.1.2, Spring Data 2026.0.2, Hibernate ORM 7.4.13, Jakarta EE 11 baseline with Servlet 6.1, Tomcat 11.0.27), JUnit 6 (Boot 4.1.2 manages 6.0.3; 6.1.3 is the newest on Maven Central), Testcontainers 2.0.5, Flyway 12.4.0 and Liquibase 5.0.4 as managed by Boot 4.1.2 (2026-10).

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

- Covered: Java 21 and 25 language and runtime features used in services (records, sealed types, pattern matching, virtual threads, scoped values), Spring Boot 4 on Spring Framework 7, constructor injection, `@Configuration`, profiles, `@ConfigurationProperties`, Spring Data JPA and Hibernate (N+1, fetch strategies, transactions, Flyway or Liquibase migrations), Spring Security (filter chains, method security, JWT resource server, CSRF, password hashing), virtual threads in Spring, Actuator exposure, JUnit, `@SpringBootTest` and test slices, Testcontainers with `@ServiceConnection`, Maven and Gradle builds.
- Not covered: Kotlin Android apps (android-expert), container images and Compose (docker-expert), generic REST resource and error design (rest-api-expert), OAuth 2.0 and OIDC protocol design, token lifetimes and identity provider choice (authentication-expert), metrics, tracing and logging backends (observability-expert), Kubernetes manifests (kubernetes-expert), SQL tuning inside PostgreSQL (postgresql-expert), architecture-level decisions such as bounded contexts (ddd-expert, clean-architecture-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Boot line | Boot 4.0 (Nov 2025) is built on Spring Framework 7 and Jakarta EE 11; 4.1.2 is the newest GA seen on Maven Central, 4.2.0-RC1 is a release candidate. Java 17 is the minimum; use the newest LTS (25) when the platform allows. Maven 3.6.3+, Gradle 8.14+ or 9.x |
| Starters | Modular: `spring-boot-starter-webmvc` (was `-web`), each technology has a `-test` companion (`spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`). Flyway and Liquibase need `spring-boot-starter-flyway` or `spring-boot-starter-liquibase`. `spring-boot-starter-classic` is a temporary bridge |
| Removed in Boot 4 | `@MockBean` and `@SpyBean` (use `@MockitoBean`, `@MockitoSpyBean`), Undertow, `@SpringBootTest` no longer provides MockMvc or `TestRestTemplate` automatically (add `@AutoConfigureMockMvc` etc.) |
| Jackson 3 | Packages move from `com.fasterxml.jackson` to `tools.jackson` (annotations stay). Define a `JsonMapper` bean, not an `ObjectMapper` bean; `@JsonComponent` is now `@JacksonComponent` |
| Spring Framework 7 | JSpecify null-safety annotations, API versioning for MVC and WebFlux, `@Retryable` and `@ConcurrencyLimit` in core (enable with `@EnableResilientMethods`), `RestTestClient` |
| Java 21 final | Virtual threads (JEP 444), pattern matching for `switch` (441), record patterns (440), sequenced collections (431). Records and sealed classes were final earlier (16 and 17) |
| Java 22-24 final | Unnamed variables and patterns `_` (JEP 456, JDK 22), stream gatherers (485, JDK 24), `synchronized` no longer pins virtual threads (491, JDK 24) |
| Java 25 final | Scoped values (JEP 506), flexible constructor bodies (513), compact source files and instance main methods (512), module import declarations (511). Structured concurrency (505) is still a preview in 25 |
| Persistence | Jakarta Persistence 3.2, Hibernate 7. Records cannot be `@Entity`; use them for projections and DTOs. `spring.jpa.open-in-view` should be set explicitly to `false` |
| Security 7 | `and()` chaining removed, only the lambda DSL; `authorizeRequests` removed in favour of `authorizeHttpRequests`; `AntPathRequestMatcher` and `MvcRequestMatcher` replaced by `PathPatternRequestMatcher` |
| Testing | JUnit 6 needs Java 17, uses a single version number for Platform, Jupiter and Vintage, and removes the JUnit 4 runner module. Testcontainers 2 moved modules to `testcontainers-<name>` artifacts and `org.testcontainers.<name>` packages |
| Virtual threads | `spring.threads.virtual.enabled=true` (Java 21+) switches the auto-configured task executor and scheduler to virtual threads. JDK 24+ removes most `synchronized` pinning; the `-Djdk.tracePinnedThreads` option was dropped in favour of the JFR event `jdk.VirtualThreadPinned` |

## 3. Workflow

1. Identify the build tool (`pom.xml` or `build.gradle(.kts)`), Java toolchain, Boot version, web stack (MVC or WebFlux), database and migration tool before writing code.
2. Read the existing configuration (`application.yml`, `@Configuration` classes, security chain, test setup) and follow its conventions.
3. For a Boot 3 to 4 move: upgrade to the latest 3.5.x first, remove deprecation warnings, then change starters, test annotations, Jackson packages and security DSL (section 2 lists the breaking points).
4. For persistence work, turn on SQL logging in a test profile, count statements for the use case, then change the fetch plan. Measure before and after.
5. Make the smallest change that fits the project's layering: controller (HTTP only), service (transaction and authorization boundary), repository (queries).
6. Add a test at the narrowest level that proves the change: unit test, slice test, then `@SpringBootTest` with a real database for persistence and security wiring.
7. Run the build (`./mvnw verify` or `./gradlew build`) and report which commands ran and which tests were added.

## 4. Decision Rules

- If the target is a new service, use Java 25 and Boot 4.1.x; if the platform is pinned to Java 21, stay on 21 (Boot 4 supports it) and avoid relying on `synchronized`-pinning fixes from JDK 24.
- If the work is request/response with blocking I/O (JDBC, HTTP clients), use Spring MVC with virtual threads; choose WebFlux only for streaming back-pressure or an existing reactive stack, because mixing blocking JPA into reactive code stalls event loops.
- If data is read-only and shaped for one screen, return a projection (interface or record) instead of an entity, to avoid loading associations and to keep entities out of the API.
- If a query touches an association for many parents, use `JOIN FETCH` or `@EntityGraph` for single-valued or small collections, and `default_batch_fetch_size` for paged lists, because a fetch-joined collection cannot be paged in SQL.
- If a client is a browser using cookies, keep CSRF protection on; if clients send only `Authorization: Bearer` tokens and the app keeps no session, CSRF can be disabled for that chain.
- If more than one object type implements a closed set of cases, use a sealed interface with records and an exhaustive `switch`, because the compiler then flags a missing case.
- If a value has to travel down a call tree on virtual threads, prefer `ScopedValue` (final in 25) over `ThreadLocal`; on Java 21 keep `ThreadLocal` small and clear it.
- If a test needs a real database, use Testcontainers with `@ServiceConnection`; use an embedded H2 only for logic that does not depend on database-specific SQL.
- If a setting is a secret (password, key, token), read it from the environment, a mounted secret or a secret manager, never from a committed `application.yml`.

## 5. Coding Standards

- Use constructor injection with `final` fields; a single constructor needs no `@Autowired`. Do not use field injection in production code.
- Use `@ConfigurationProperties` on a record with `@Validated` and register it with `@ConfigurationPropertiesScan` or `@EnableConfigurationProperties`; avoid scattering `@Value`.
- Keep `@Transactional` on service methods, not on controllers or repositories. Use `@Transactional(readOnly = true)` for queries. Calls inside the same class and `private` methods bypass the proxy, so the annotation has no effect there.
- Entities: `jakarta.persistence` annotations, a protected no-arg constructor, `equals`/`hashCode` based on a stable business key or on the id handled for null, `FetchType.LAZY` on every `@ManyToOne` and `@OneToOne` (the default is eager), `@Version` for optimistic locking, `@Enumerated(EnumType.STRING)`.
- Never expose entities in controller signatures; map to records. Validate input with Jakarta Validation (`@Valid`, `@NotBlank`, `@Size`) on request records.
- Use `Optional` as a return type only; never as a field or parameter. Return empty collections, not `null`.
- Use `var` for obvious local types; use records for immutable data carriers; use `switch` expressions with pattern matching over `instanceof` chains.
- Throw domain exceptions from services and map them in one `@RestControllerAdvice` (or `ProblemDetail`); do not catch `Exception` to return a generic value.
- Use SLF4J with parameterized messages (`log.info("order {} created", id)`); never log secrets, tokens or full personal data.
- Use Java toolchains (`maven.compiler.release` or Gradle `java.toolchain`) so the compile level is explicit.

## 6. Project Structure

Package by feature so each slice holds its controller, service, repository and DTOs; keep the `@SpringBootApplication` class in the root package so component scanning covers everything below it.

```text
orders-service/
├── pom.xml                         # or build.gradle.kts
├── src/main/java/com/example/orders/
│   ├── OrdersApplication.java      # @SpringBootApplication
│   ├── config/                     # SecurityConfig, properties records
│   ├── order/
│   │   ├── Order.java              # @Entity
│   │   ├── OrderRepository.java
│   │   ├── OrderService.java       # @Transactional boundary
│   │   ├── OrderController.java
│   │   └── dto/                    # request and response records
│   └── shared/                     # error handling, small utilities
├── src/main/resources/
│   ├── application.yml             # defaults, no secrets
│   ├── application-local.yml       # developer overrides, no secrets
│   └── db/migration/               # V1__init.sql, V2__add_index.sql
└── src/test/java/com/example/orders/
    ├── order/OrderControllerTest.java      # @WebMvcTest
    ├── order/OrderRepositoryTest.java      # @DataJpaTest or SpringBootTest + container
    └── TestcontainersConfig.java           # @ServiceConnection beans
```

## 7. Design Patterns

- **Layered service boundary**: controller maps HTTP to a command, the service opens the transaction and enforces authorization, the repository runs queries. Cost: simple CRUD gets thin pass-through services; keep them anyway for the transaction boundary.
- **Sealed result types**: model outcomes as `sealed interface Result permits Ok, NotFound, Conflict` and switch exhaustively. Cost: more types than exceptions; use for expected business outcomes, exceptions for failures.
- **Projection per use case**: interface or record projections for list views, entities only for writes. Cost: more query methods.
- **Optimistic locking with `@Version`**: concurrent updates fail with `ObjectOptimisticLockingFailureException`; map it to HTTP 409. Cost: callers must retry or reload.
- **Outbox table**: write the event in the same transaction as the state change and publish it from a separate poller, instead of calling a broker inside `@Transactional`. Cost: a poller and idempotent consumers.
- **Conditional beans and profiles**: `@Profile`, `@ConditionalOnProperty` for local or test replacements. Cost: profile combinations multiply; keep them few and name them by environment.
- **Programmatic bean registration**: Spring Framework 7 adds `BeanRegistrar` for dynamic registrations; prefer plain `@Bean` methods unless beans are generated from data.

## 8. Best Practices

- Pin the Boot version through the parent or the Gradle plugin and let Boot manage dependency versions; override a managed version only with a written reason.
- Keep configuration in `application.yml` for defaults and environment variables for deployment values; Boot's relaxed binding maps `APP_STORAGE_BUCKET` to `app.storage.bucket`.
- Run schema changes through Flyway or Liquibase and set `spring.jpa.hibernate.ddl-auto` to `validate` or `none` outside throwaway tests, because Hibernate-generated DDL is not reviewable or repeatable.
- Set `spring.jpa.open-in-view=false` so lazy loading outside the service layer fails in tests instead of running queries from the view layer in production.
- Use `RestClient` (blocking) or declarative HTTP interface clients for outgoing calls, with explicit connect and read timeouts.
- Paginate every list endpoint with a server-side maximum page size; return `Slice` or a keyset `Window` when the total count is not needed.
- Use virtual threads for blocking request handling and bound downstream resources (connection pools, rate-limited APIs) with a pool size or `@ConcurrencyLimit`, since virtual threads remove the thread limit but not the limit of the database.
- Expose only the Actuator endpoints you need (section 13) and keep them on an authenticated chain or a separate management port.
- Fail fast on bad configuration: validated `@ConfigurationProperties` stop startup with a clear message.

## 9. Performance

- Measure first: enable `spring.jpa.properties.hibernate.generate_statistics` in a test or a local profile, count statements per request, and use the database's `EXPLAIN` for slow ones. Do not tune without a number.
- N+1: a lazy association accessed in a loop triggers one query per row. Fix with `@EntityGraph`, `JOIN FETCH`, `@BatchSize` or `hibernate.default_batch_fetch_size`, or by selecting a projection. Details in [references/spring-data-jpa.md](references/spring-data-jpa.md).
- Fetch joining two collections in one query produces a Cartesian product (and `MultipleBagFetchException` with bags); fetch one collection per query.
- Add indexes for every foreign key and every filter column used with the tenant or owner id; check the plan, then keep migration scripts for them.
- Batch writes: `spring.jpa.properties.hibernate.jdbc.batch_size` and `order_inserts`; note that `GenerationType.IDENTITY` disables JDBC insert batching, so prefer sequences for bulk inserts.
- Size the Hikari pool (`spring.datasource.hikari.maximum-pool-size`) to the database, not to the request count; with virtual threads, excess requests wait for a connection, which is the intended back-pressure.
- Cache with `@Cacheable` only for data with a clear invalidation rule and key that includes the tenant; measure hit rate.
- JVM: set container-aware memory (`-XX:MaxRAMPercentage`), look at GC logs and JFR before changing collectors. Startup-sensitive services can evaluate AOT/CDS options from the current Boot docs.

## 10. Security

- Authorization on every read and write path: queries for updates and deletes carry the owner or tenant condition (`where id = :id and owner_id = :ownerId`), and the code checks the affected row count. A check only on the read path leaves update and delete open to cross-tenant access (IDOR).
- Return 404 rather than 403 for another tenant's resource so ids cannot be probed.
- Parameterized queries only: derived queries, JPQL with named parameters, or `JdbcClient`/`NamedParameterJdbcTemplate` with `:name` binds. Never concatenate input into JPQL, native SQL or `@Query` strings; for `ORDER BY`, map the request value through an allow-list.
- No secrets in `application.yml`, `pom.xml` or test resources: use `${DB_PASSWORD}` placeholders resolved from the environment, mounted files (`spring.config.import=configtree:/run/secrets/`) or a secret manager. Do not commit `application-prod.yml` with credentials.
- Bind request bodies to dedicated records, not entities, to avoid mass assignment of fields such as `role` or `ownerId`. Set `ownerId` from the authenticated principal, never from the body.
- Hash passwords with `DelegatingPasswordEncoder` (`PasswordEncoderFactories.createDelegatingPasswordEncoder()`), Argon2 or BCrypt; never store plain, MD5 or SHA-1 values.
- Keep CSRF on for cookie-session browser apps; disable it only on stateless bearer-token chains. Configure CORS with explicit origins, not `*` with credentials.
- Do not expose `env`, `heapdump`, `threaddump` or `beans` over HTTP; Actuator health details only to authorized callers.
- Do not deserialize untrusted data with Java serialization; keep Jackson default typing off for untrusted JSON.
- Keep dependencies updated (Boot patch releases carry CVE fixes) and run a dependency scan in CI (pipeline design: cicd-expert).
- More in [references/spring-security.md](references/spring-security.md).

## 11. Testing

- Unit tests: plain JUnit and AssertJ with Mockito for collaborators; no Spring context. These carry most of the logic coverage.
- Web slice: `@WebMvcTest(OrderController.class)` with `@MockitoBean` for services and `MockMvcTester` or `MockMvc`; include security tests for 401, 403 and cross-tenant 404.
- Persistence slice: `@DataJpaTest` against a real PostgreSQL (or your production engine) via Testcontainers; assert statement counts for list endpoints and the owner-filtered update and delete paths.
- Integration: `@SpringBootTest` with Testcontainers and `@ServiceConnection`; keep these few and cover wiring, migrations and security configuration.
- Test failure paths: validation errors, not found, optimistic lock conflict, rollback on exception, unauthorized access to another tenant's data.
- Commands: `./mvnw verify` (Failsafe for `*IT` classes if configured) or `./gradlew test integrationTest`; run a single test with `-Dtest=OrderServiceTest` (Maven) or `--tests`.
- Details and package names for Boot 4 test annotations: [references/testing.md](references/testing.md).

## 12. Review Checklist

- [ ] Versions and starters match the "Verified against" line (modular starters, `-test` companions, no `@MockBean`).
- [ ] Constructor injection only; no field injection, no static state, no `new` of managed beans.
- [ ] `@Transactional` sits on service methods, reads are `readOnly`, no self-invocation relying on a proxy.
- [ ] Every update and delete has an owner or tenant filter and checks the affected row count.
- [ ] No entities in API signatures; request records are validated; `ownerId` comes from the principal.
- [ ] All queries parameterized; sort fields from an allow-list; no string-built JPQL or SQL.
- [ ] No lazy association touched outside a transaction; no N+1 on list endpoints (statement count asserted).
- [ ] Schema changes are in a migration; `ddl-auto` is `validate` or `none`; `open-in-view` is `false`.
- [ ] No secrets in `application*.yml`, build files or tests; configuration comes from the environment.
- [ ] Security chain: lambda DSL, `anyRequest().authenticated()` or stricter, CSRF decision explained, method security enabled where used.
- [ ] Actuator exposes only the needed endpoints and is protected.
- [ ] Tests cover success, validation failure, unauthorized and cross-tenant access, and run in CI.

## 13. Production Notes

- Actuator: add `spring-boot-starter-actuator` and expose the minimum, for example `management.endpoints.web.exposure.include=health,info`. Use `management.endpoint.health.probes.enabled=true` for liveness and readiness groups, `management.endpoint.health.show-details=when-authorized`, and a separate `management.server.port` bound to an internal network when possible. Metrics and tracing backends: observability-expert.
- Graceful shutdown: `server.shutdown=graceful` with `spring.lifecycle.timeout-per-shutdown-phase` (for example `30s`) so in-flight requests finish during rollout.
- Database migrations run at startup by default with Flyway or Liquibase; for multi-instance rollouts either use a lock-aware tool (both lock) or run migrations as a separate step, and keep migrations backward compatible for one release (expand, then contract).
- Virtual threads: after enabling, watch connection-pool wait time and JFR `jdk.VirtualThreadPinned` events; on Java 21, blocking inside `synchronized` pins the carrier thread; from JDK 24 that case is fixed, but native methods and foreign function calls can still pin, so check JEP 491 for the current list.
- Configuration: use profiles for environment differences, `spring.config.import` for external sources, and `spring.profiles.active` from the environment; never commit prod values.
- Upgrades: plan the move from 3.x to 4.x early, with Jackson 3 and Security 7 as the largest code changes. Check the Boot support policy page for the end-of-support date of the line you run.
- Native images (GraalVM) and CRaC are options for startup time; check the current Boot docs for the supported GraalVM version before adopting.

## 14. Examples

An owner-scoped repository and service: reads, updates and deletes all carry the owner condition, and zero affected rows maps to "not found".

```java
public interface NoteRepository extends JpaRepository<Note, Long> {

    Optional<Note> findByIdAndOwnerId(Long id, String ownerId);

    Slice<NoteView> findByOwnerIdOrderByCreatedAtDesc(String ownerId, Pageable pageable);

    @Modifying
    @Query("update Note n set n.title = :title where n.id = :id and n.ownerId = :ownerId")
    int updateTitle(@Param("id") Long id, @Param("ownerId") String ownerId, @Param("title") String title);

    @Modifying
    @Query("delete from Note n where n.id = :id and n.ownerId = :ownerId")
    int deleteOwned(@Param("id") Long id, @Param("ownerId") String ownerId);
}

public record NoteView(Long id, String title) {}

@Service
class NoteService {
    private final NoteRepository notes;

    NoteService(NoteRepository notes) { this.notes = notes; }

    @Transactional
    public void rename(Long id, String ownerId, String title) {
        if (notes.updateTitle(id, ownerId, title) == 0) {
            throw new NoteNotFoundException(id);   // 404 for missing and for foreign notes
        }
    }

    @Transactional
    public void delete(Long id, String ownerId) {
        if (notes.deleteOwned(id, ownerId) == 0) {
            throw new NoteNotFoundException(id);
        }
    }
}
```

A stateless JWT resource server on Spring Security 7 (lambda DSL only), with method security enabled. The issuer comes from `spring.security.oauth2.resourceserver.jwt.issuer-uri` in the environment.

```java
@Configuration
@EnableMethodSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // Bearer tokens only, no cookies or session: CSRF protects cookie-based auth.
            .csrf(csrf -> csrf.disable());
        return http.build();
    }
}
```

Sealed types with record patterns and an exhaustive `switch` (Java 21+); adding a new permitted type without a case is a compile error.

```java
sealed interface PaymentResult permits Approved, Declined, Pending {}
record Approved(String authCode) implements PaymentResult {}
record Declined(String reason) implements PaymentResult {}
record Pending(String reference) implements PaymentResult {}

static int toHttpStatus(PaymentResult result) {
    return switch (result) {
        case Approved a -> 200;
        case Declined(String reason) when reason.startsWith("fraud") -> 403;
        case Declined d -> 402;
        case Pending p -> 202;
    };
}
```

A repository test against a real database with `@ServiceConnection` (Boot 4 packages, Testcontainers 2). More test examples are in [references/testing.md](references/testing.md).

```java
@TestConfiguration(proxyBeanMethods = false)
class TestcontainersConfig {
    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:17");
    }
}

@SpringBootTest
@Import(TestcontainersConfig.class)
class NoteServiceIT {
    @Autowired NoteService service;
    @Autowired NoteRepository notes;

    @Test
    void otherUserCannotDelete() {
        Note n = notes.save(new Note("alice", "title"));
        assertThatThrownBy(() -> service.delete(n.getId(), "bob"))
            .isInstanceOf(NoteNotFoundException.class);
        assertThat(notes.findByIdAndOwnerId(n.getId(), "alice")).isPresent();
    }
}
```

## 15. Common Mistakes

- **Open Session in View left on**: lazy loads run from controllers and serializers, hide N+1 and hold connections during rendering. Set `spring.jpa.open-in-view=false` and fetch what the service needs.
- **`@Transactional` on a private or self-invoked method**: no proxy, no transaction, silent partial writes. Move the method to another bean or call through the proxy.
- **Eager `@ManyToOne` defaults**: every load pulls the association graph. Declare `fetch = FetchType.LAZY` and fetch explicitly.
- **Owner check only on GET**: `PUT` and `DELETE` by id let any authenticated user modify others' rows. Add the owner condition to the write query and test it.
- **Entity returned from the controller**: lazy proxies fail to serialize, internal fields leak, and clients can set protected fields. Use records.
- **`@Value` with secrets in `application.yml`**: committed credentials. Use environment variables or a secret manager.
- **String-built JPQL or native SQL**: injection. Use named parameters and allow-lists for sort fields.
- **`ddl-auto=update` in production**: unreviewed DDL and drift. Use migrations and `validate`.
- **Using removed Boot 3 APIs after upgrading**: `@MockBean`, `spring-boot-starter-web`, `com.fasterxml.jackson` imports, `.and()` in the security DSL, `AntPathRequestMatcher`. Follow the Boot 4 and Security 7 migration guides.
- **Disabling CSRF globally without a reason**: cookie-session apps become forgeable. Disable it only on stateless bearer-token chains and say why in a comment.
- **Virtual threads treated as free**: thousands of concurrent requests exhaust the connection pool or a downstream API. Bound resources and watch pool wait time.
- **Pooling virtual threads or using large `ThreadLocal` caches**: virtual threads are cheap to create; pooling defeats the model and `ThreadLocal` data multiplies. Create one per task.
- **Over-exposed Actuator**: `include=*` publishes `env`, `heapdump` and more. List endpoints explicitly.
- **`@SpringBootTest` for everything**: slow suites and vague failures. Use unit tests and slices, and a few full-context tests.

## 16. References

- [references/spring-data-jpa.md](references/spring-data-jpa.md): repositories, projections, N+1 fixes, fetch joins and entity graphs, pagination, transaction rules, locking, owner-scoped queries, Flyway and Liquibase.
- [references/spring-security.md](references/spring-security.md): `SecurityFilterChain` lambda DSL, multiple chains, method security, JWT resource server, CSRF and CORS rules, password encoding, Actuator security.
- [references/testing.md](references/testing.md): JUnit 6, Boot 4 test starters and annotation packages, slices, Testcontainers with `@ServiceConnection`, security tests, Maven and Gradle commands.
- [references/java-21-25-and-virtual-threads.md](references/java-21-25-and-virtual-threads.md): records, sealed types, pattern matching, what finalized in 21 to 25, virtual threads in Spring and pinning.
- Spring Boot reference and system requirements: https://docs.spring.io/spring-boot/
- Spring Boot 4.0 migration guide: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- Spring Framework reference: https://docs.spring.io/spring-framework/reference/
- Spring Data JPA reference: https://docs.spring.io/spring-data/jpa/reference/
- Spring Security reference and 7.0 migration: https://docs.spring.io/spring-security/reference/
- Hibernate ORM documentation: https://hibernate.org/orm/documentation/
- JUnit 6 user guide and release notes: https://docs.junit.org/
- Testcontainers for Java: https://java.testcontainers.org/
- OpenJDK JEPs: https://openjdk.org/jeps/0 (JEP 444, 441, 440, 491, 506, 512, 513)
