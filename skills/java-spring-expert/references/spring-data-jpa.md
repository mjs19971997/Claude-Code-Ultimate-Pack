# Spring Data JPA and Hibernate

Repositories, projections, fixing N+1 queries, fetch plans, pagination, transaction rules, locking, owner-scoped writes and schema migrations. Applies to Spring Boot 4.1.x (Spring Data 2026.0.x, Hibernate ORM 7.4.x, Jakarta Persistence 3.2); verify option names against the current docs when upgrading.

## Contents

1. [Dependencies and configuration](#1-dependencies-and-configuration)
2. [Entities](#2-entities)
3. [Repositories and projections](#3-repositories-and-projections)
4. [N+1 and fetch plans](#4-n1-and-fetch-plans)
5. [Pagination](#5-pagination)
6. [Transactions](#6-transactions)
7. [Owner and tenant scoping](#7-owner-and-tenant-scoping)
8. [Locking and concurrency](#8-locking-and-concurrency)
9. [Migrations with Flyway or Liquibase](#9-migrations-with-flyway-or-liquibase)

## 1. Dependencies and configuration

- Maven: `spring-boot-starter-data-jpa` plus the JDBC driver (for example `org.postgresql:postgresql`); tests add `spring-boot-starter-data-jpa-test`.
- Flyway needs `spring-boot-starter-flyway` in Boot 4 (the bare `flyway-core` dependency no longer triggers auto-configuration); Liquibase needs `spring-boot-starter-liquibase`. Some databases also need a Flyway database module such as `flyway-database-postgresql`; check the Flyway docs for your database.
- Recommended baseline (no credentials in the file; values come from the environment):

```yaml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate
    properties:
      hibernate:
        default_batch_fetch_size: 50
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true
```

- `open-in-view: false` ends the persistence context at the service boundary. Lazy access afterwards throws `LazyInitializationException`, which is the signal to fetch the data inside the service.
- Local SQL inspection: `logging.level.org.hibernate.SQL=DEBUG` in a dev or test profile. Avoid `spring.jpa.show-sql` in production, and never log bind values of personal data.

## 2. Entities

```java
@Entity
@Table(name = "note", indexes = @Index(name = "ix_note_owner", columnList = "owner_id"))
public class Note {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE)
    private Long id;

    @Column(name = "owner_id", nullable = false, updatable = false)
    private String ownerId;

    @Column(nullable = false, length = 200)
    private String title;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "folder_id")
    private Folder folder;

    @Version
    private long version;

    protected Note() {}                       // required by JPA

    public Note(String ownerId, String title) {
        this.ownerId = ownerId;
        this.title = title;
    }
    // getters; no setter for ownerId
}
```

- Records cannot be entities (JPA needs a mutable, non-final class with a no-arg constructor); use records for projections and DTOs.
- `@ManyToOne` and `@OneToOne` are eager by default; set `fetch = FetchType.LAZY` explicitly. Collections are lazy by default; keep them that way.
- `@Column(updatable = false)` on `ownerId` stops accidental reassignment through a managed entity.
- Prefer `Set` for many-to-many collections to avoid `MultipleBagFetchException`; map the owning side and keep both sides in sync through helper methods.
- `GenerationType.IDENTITY` disables JDBC insert batching; use sequences when you insert many rows.
- Store enums as strings (`@Enumerated(EnumType.STRING)`), not ordinals.

## 3. Repositories and projections

```java
public interface NoteRepository extends JpaRepository<Note, Long> {

    Optional<Note> findByIdAndOwnerId(Long id, String ownerId);

    List<NoteSummary> findByOwnerIdAndFolderId(String ownerId, Long folderId);   // DTO projection

    @Query("select n from Note n join fetch n.folder where n.ownerId = :ownerId")
    List<Note> findWithFolder(@Param("ownerId") String ownerId);

    boolean existsByIdAndOwnerId(Long id, String ownerId);
}

public record NoteSummary(Long id, String title) {}     // class-based projection
```

- Derived queries (`findBy...`) are parameterized automatically. `@Query` with `:name` parameters is parameterized too. `nativeQuery = true` also takes bind parameters; never concatenate input.
- Interface-based projections (`interface NoteView { Long getId(); String getTitle(); }`) select only the declared columns when closed (all getters map to properties); records as DTO projections use the constructor.
- Dynamic sort: accept a sort key, map it through an allow-list (`Map<String, String>`), then build `Sort.by(...)`. Do not pass raw request strings into `Sort` for native queries.
- Custom dynamic filters: use `Specification` or Querydsl rather than building JPQL strings.
- Derived `deleteBy...` loads entities and deletes them one by one; for bulk or owner-scoped deletes use `@Modifying @Query("delete ...")`, which returns the affected row count. After a bulk `@Modifying` query the persistence context can be stale; set `@Modifying(clearAutomatically = true)` when you read the same entities afterwards in the transaction.

## 4. N+1 and fetch plans

A list of N parents whose lazy association is read in a loop runs 1 + N queries. Detect it by counting statements in a test (Hibernate statistics or a datasource proxy) and fix it with one of:

| Technique | Use when | Caveat |
|---|---|---|
| `JOIN FETCH` in `@Query` | One association needed for the use case | Fetching a collection with pagination makes Hibernate page in memory; do not combine them |
| `@EntityGraph(attributePaths = "folder")` on the repository method | Same as above, without writing JPQL | Same collection and paging caveat |
| `@BatchSize` or `hibernate.default_batch_fetch_size` | Paged lists with lazy associations | Turns N queries into N/size queries, not one |
| Projection with the needed columns | Read-only views | No managed entity; cannot update through it |
| Second query by ids (`where id in (...)`) | Two collections would multiply rows | Two round trips |

```java
@EntityGraph(attributePaths = {"folder"})
List<Note> findByOwnerIdOrderByCreatedAtDesc(String ownerId);
```

- Fetch-joining two `List` collections at once raises `MultipleBagFetchException`; fetch one collection per query or use `Set`.
- Do not "fix" N+1 by switching associations to `FetchType.EAGER`; that applies to every query and usually makes it worse.
- Assert the fix: in the test, reset statistics, call the service, and assert the statement count.

```java
@Autowired EntityManagerFactory emf;

Statistics stats = emf.unwrap(SessionFactory.class).getStatistics();
stats.setStatisticsEnabled(true);
stats.clear();
service.listNotes("alice");
assertThat(stats.getPrepareStatementCount()).isEqualTo(1);
```

## 5. Pagination

- `Page<T>` runs an extra count query; use `Slice<T>` when the total is not displayed.
- Offset pagination degrades on deep pages. For large tables use keyset pagination with `Window<T>` and `ScrollPosition` (Spring Data JPA supports `ScrollPosition.keyset()` on derived queries with a deterministic sort including a unique column):

```java
Window<Note> findFirst20ByOwnerIdOrderByCreatedAtAscIdAsc(String ownerId, ScrollPosition position);
```

- Cap the page size on the server (`spring.data.web.pageable.max-page-size` for resolved `Pageable` parameters) so clients cannot request millions of rows.

## 6. Transactions

- Put `@Transactional` on service methods. Default propagation is `REQUIRED`; rollback happens for unchecked exceptions and errors only, so declare `rollbackFor` for checked exceptions that must roll back.
- `@Transactional(readOnly = true)` on query methods lets Hibernate skip dirty checking and lets some drivers route to replicas.
- Proxies: a call from one method to another method of the same bean, and `private` methods, are not intercepted. Move the code to another bean.
- Keep transactions short: no HTTP calls, message sends or file I/O inside; they hold a connection and a lock. Use an outbox table to publish events after commit, or `@TransactionalEventListener(phase = AFTER_COMMIT)` for in-process reactions.
- `@Async` and virtual-thread tasks start a new thread, so the transaction and security context do not carry over; open a new transaction in the task.
- Detached entities: re-load by id inside the transaction instead of calling `save` on a client-built object; this avoids overwriting columns you did not mean to change.
- A failed flush surfaces at commit; to see constraint violations inside a method, call `saveAndFlush` and handle `DataIntegrityViolationException`.

## 7. Owner and tenant scoping

Every statement that touches tenant-owned data carries the owner or tenant column, for reads, updates and deletes:

```java
@Modifying(clearAutomatically = true)
@Query("update Note n set n.title = :title where n.id = :id and n.ownerId = :ownerId")
int updateTitle(@Param("id") Long id, @Param("ownerId") String ownerId, @Param("title") String title);

@Modifying
@Query("delete from Note n where n.id = :id and n.ownerId = :ownerId")
int deleteOwned(@Param("id") Long id, @Param("ownerId") String ownerId);
```

- The service passes the owner id from the authenticated principal (`@AuthenticationPrincipal Jwt jwt` -> `jwt.getSubject()`), never from the request body or path.
- Check the returned count: 0 means "not found or not yours"; respond 404 in both cases.
- When loading then modifying an entity, load with `findByIdAndOwnerId`, not `findById`; a plain `findById` followed by an `if (owner != user)` check is easy to forget on a second code path.
- For multi-tenant schemas, add a database-level backstop where the engine supports it (PostgreSQL row-level security, set per connection) and still keep the application filter. Hibernate offers `@TenantId` for discriminator-column multi-tenancy; check the Hibernate 7 docs for its resolver setup.
- Test both directions: user A can modify A's row; user B gets 404 and the row is unchanged.

## 8. Locking and concurrency

- Optimistic locking: a `@Version` field makes concurrent updates fail with `ObjectOptimisticLockingFailureException`; map it to HTTP 409 and let the client reload.
- Pessimistic locking: `@Lock(LockModeType.PESSIMISTIC_WRITE)` on a repository method issues `select ... for update`; keep the transaction short and set a lock timeout hint (`jakarta.persistence.lock.timeout`).
- Atomic counters and idempotent state changes are safer as single `update ... set x = x + 1 where ...` statements than read-modify-write.
- Unique constraints in the schema are the final guard against duplicates; catch `DataIntegrityViolationException` rather than check-then-insert.

## 9. Migrations with Flyway or Liquibase

- Flyway files live in `src/main/resources/db/migration` named `V<version>__<description>.sql`; never edit an applied migration, add a new one. Repeatable migrations use `R__name.sql`.
- Liquibase changelogs default to `db/changelog/db.changelog-master.yaml`.
- Rollouts: write backward-compatible migrations (add nullable column, backfill, then add the constraint in a later release) so the old and new application versions can run against the same schema during a rolling deploy.
- Run migrations with a dedicated database user that has DDL rights, and run the application with a user limited to DML, when the platform allows two credentials. Credentials come from the environment (`spring.flyway.user`, `spring.flyway.password`).
- Test migrations in CI against a real database from scratch (Testcontainers) and keep `ddl-auto=validate` so entity/schema drift fails the test.
- Large tables: create indexes concurrently where the database supports it, and keep long-running data migrations out of the startup path.
