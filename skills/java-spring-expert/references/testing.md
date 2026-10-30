# Testing Spring Boot Applications

JUnit 6, Spring Boot 4 test starters and annotation packages, test slices, Testcontainers with `@ServiceConnection`, security tests and build commands. Verified against Spring Boot 4.1.2, JUnit 6.0.x (managed by Boot; 6.1.x is released), Testcontainers 2.0.5 and Mockito 5.23 (2026-10).

## Contents

1. [Dependencies](#1-dependencies)
2. [JUnit 6 notes](#2-junit-6-notes)
3. [Choosing the test type](#3-choosing-the-test-type)
4. [Web slice](#4-web-slice)
5. [Persistence slice](#5-persistence-slice)
6. [Full context with Testcontainers](#6-full-context-with-testcontainers)
7. [Mocking beans](#7-mocking-beans)
8. [Failure-path checklist](#8-failure-path-checklist)
9. [Maven and Gradle commands](#9-maven-and-gradle-commands)

## 1. Dependencies

Boot 4 has a test starter per technology that brings `spring-boot-starter-test` transitively:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-webmvc-test</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-data-jpa-test</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-security-test</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-testcontainers</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>testcontainers-postgresql</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>testcontainers-junit-jupiter</artifactId>
  <scope>test</scope>
</dependency>
```

- Gradle equivalents: `testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")`, and so on. Versions are managed by the Boot BOM, so omit them.
- Testcontainers 2 renamed module artifacts to `testcontainers-<module>` and moved classes to `org.testcontainers.<module>` (for example `org.testcontainers.postgresql.PostgreSQLContainer`). Old `org.testcontainers:postgresql` coordinates are the 1.x names.
- `spring-boot-starter-classic` and `spring-boot-starter-test-classic` exist only as a bridge during migration.

## 2. JUnit 6 notes

- JUnit 6 requires Java 17, uses one version number for Platform, Jupiter and Vintage, and removes the JUnit 4 runner module. Imports stay in `org.junit.jupiter.api`, so Jupiter 5 tests normally compile unchanged.
- Boot 4.1.2 manages `junit-jupiter` 6.0.3; do not override the version unless a fix requires it (Maven property `junit-jupiter.version`, Gradle `ext["junit-jupiter.version"]`).
- Keep `@ParameterizedTest` with `@CsvSource` or `@MethodSource` for rule tables (validation, permissions).
- Use AssertJ (`assertThat`) for assertions; it comes with the starter.

## 3. Choosing the test type

| Goal | Annotation or tool | Starts |
|---|---|---|
| Business logic | plain JUnit + Mockito | nothing |
| Controller mapping, validation, JSON, security rules | `@WebMvcTest` | MVC layer only |
| Repository queries, mappings, migrations | `@DataJpaTest` | JPA layer, transaction per test, rolled back |
| JSON (de)serialization | `@JsonTest` | JSON mapper only |
| Wiring, full flows | `@SpringBootTest` | whole context |
| Outgoing HTTP client behavior | `@RestClientTest` | client beans with a mock server |

Prefer the narrowest row that proves the behavior.

## 4. Web slice

Boot 4 packages: `org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest` and `AutoConfigureMockMvc` (module `spring-boot-webmvc-test`).

```java
@WebMvcTest(NoteController.class)
@Import(SecurityConfig.class)
class NoteControllerTest {

    @Autowired MockMvc mvc;
    @MockitoBean NoteService service;

    @Test
    void renameRequiresAuthentication() throws Exception {
        mvc.perform(patch("/api/notes/1").contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"x\"}"))
           .andExpect(status().isUnauthorized());
    }

    @Test
    void blankTitleIsRejected() throws Exception {
        mvc.perform(patch("/api/notes/1").with(jwt()).contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"\"}"))
           .andExpect(status().isBadRequest());
    }
}
```

- `MockMvcTester` (AssertJ-style assertions, Spring Framework 6.2+) is an alternative to classic `MockMvc`; follow the project's choice.
- A `@WebMvcTest` loads only web beans, so import the security configuration and provide `@MockitoBean` for each service the controller needs.
- In a `@SpringBootTest`, MockMvc is no longer provided automatically in Boot 4: add `@AutoConfigureMockMvc`. `TestRestTemplate` needs `@AutoConfigureTestRestTemplate`, and `RestTestClient` needs `@AutoConfigureRestTestClient`.

## 5. Persistence slice

Boot 4 package: `org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest` (module `spring-boot-data-jpa-test`).

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)   // keep the real datasource
@Import(TestcontainersConfig.class)
class NoteRepositoryTest {

    @Autowired NoteRepository notes;

    @Test
    void updateOnlyAffectsOwnRows() {
        Note n = notes.saveAndFlush(new Note("alice", "old"));

        assertThat(notes.updateTitle(n.getId(), "bob", "hacked")).isZero();
        assertThat(notes.updateTitle(n.getId(), "alice", "new")).isOne();
    }
}
```

- `@DataJpaTest` replaces the datasource with an embedded database by default; `Replace.NONE` keeps the Testcontainers one so database-specific SQL and migrations are tested. Check the current docs for the import package of `@AutoConfigureTestDatabase` in Boot 4.
- Each test runs in a transaction that is rolled back; flush (`saveAndFlush`) before asserting on constraint behavior.
- Flyway runs on the container at startup, so the test also checks that migrations apply from scratch and that `ddl-auto=validate` agrees with the entities.
- Assert statement counts for list endpoints (see spring-data-jpa.md section 4).

## 6. Full context with Testcontainers

Declare containers as beans annotated with `@ServiceConnection`; Boot derives the connection properties (for PostgreSQL the datasource URL, username and password), so there is no `@DynamicPropertySource`.

```java
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfig {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:17");
    }
}
```

```java
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfig.class)
class NoteApiIT {

    @Autowired MockMvc mvc;

    @Test
    void foreignNoteReturnsNotFound() throws Exception {
        mvc.perform(delete("/api/notes/{id}", 1L).with(jwt().jwt(j -> j.subject("bob"))))
           .andExpect(status().isNotFound());
    }
}
```

- `@ServiceConnection` is in `org.springframework.boot.testcontainers.service.connection`; `@ImportTestcontainers` (in `org.springframework.boot.testcontainers.context`) imports container declarations from an interface or class with static fields.
- Annotation-based alternative: `@Testcontainers` and `@Container` on a `static` field, also with `@ServiceConnection`, using `org.testcontainers.junit.jupiter` from `testcontainers-junit-jupiter`.
- Containers declared as beans share the Spring context lifecycle, and the Spring test context cache reuses the context across test classes that import the same configuration; keep the set of distinct configurations small to avoid a container per class.
- Containers that have no `@ServiceConnection` support use `@DynamicPropertySource` with a `DynamicPropertyRegistry`.
- Pin container image tags to the production version of the database, not `latest`.
- Docker must be reachable in CI (image and service setup: docker-expert and cicd-expert).
- Test configuration must not carry real secrets; container credentials are generated or disposable.

## 7. Mocking beans

- `@MockBean` and `@SpyBean` are removed in Boot 4. Use `@MockitoBean` and `@MockitoSpyBean` (from `org.springframework.test.context.bean.override.mockito`) on test fields.
- They do not work inside `@Configuration` classes; put shared mocks on the test class or a common abstract base class with `@MockitoBean(types = ...)`.
- Prefer a real bean with a fake edge (a container or a stub server) over mocking a repository in integration tests; mocks hide query bugs.
- Reset mocks automatically: the Spring extension resets `@MockitoBean` after each test.

## 8. Failure-path checklist

- Validation: missing and over-long fields return 400 with a problem body.
- Authentication and authorization: no token gives 401, wrong role or scope gives 403, other tenant's id gives 404, and the row is unchanged afterwards.
- Concurrency: stale `@Version` gives 409.
- Transactions: an exception after the first write rolls everything back (assert the table is unchanged).
- Constraints: duplicate unique key maps to 409, not 500.
- Configuration: invalid `@ConfigurationProperties` fails context startup (a `ApplicationContextRunner` test with bad properties).
- Time and randomness: inject `Clock` and ID generators so tests are deterministic.

## 9. Maven and Gradle commands

```bash
./mvnw verify                                  # unit + integration tests, packaging
./mvnw test -Dtest=NoteServiceTest             # one class
./mvnw test -Dtest='NoteServiceTest#rename*'   # matching methods
./mvnw -q -DskipTests package                  # build without tests

./gradlew build                                # compile, test, assemble
./gradlew test --tests '*NoteServiceTest'      # one class
./gradlew test --tests '*NoteServiceTest.rename*'
./gradlew dependencies --configuration testRuntimeClasspath
```

- Maven runs `*Test` with Surefire and `*IT` with Failsafe (`mvn verify`) when the Failsafe plugin is configured; Gradle projects commonly add a separate `integrationTest` task and source set.
- Use the wrapper (`mvnw`, `gradlew`) and commit its files so CI and developers use the same build tool version.
- Print effective versions with `./mvnw dependency:tree -Dincludes=org.junit.jupiter` when a test dependency conflicts.
