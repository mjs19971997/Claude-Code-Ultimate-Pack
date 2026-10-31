# D1 and Other Data Bindings

D1 (SQLite) in depth: queries, batches, migrations, Time Travel, read replication and limits. KV, Durable Objects with SQLite storage, Queues and Hyperdrive follow in outline. Facts come from the D1, KV, Durable Objects and Workers documentation sources and Wrangler 4.156.0 (2026-10).

## Contents

1. [Create a database and a binding](#1-create-a-database-and-a-binding)
2. [Query API](#2-query-api)
3. [Batches and transactions](#3-batches-and-transactions)
4. [Migrations](#4-migrations)
5. [Time Travel and exports](#5-time-travel-and-exports)
6. [Read replication and the Sessions API](#6-read-replication-and-the-sessions-api)
7. [D1 limits](#7-d1-limits)
8. [KV](#8-kv)
9. [Durable Objects with SQLite](#9-durable-objects-with-sqlite)
10. [Queues](#10-queues)
11. [Hyperdrive](#11-hyperdrive)

## 1. Create a database and a binding

```bash
npx wrangler d1 create notes
npx wrangler d1 info notes
npx wrangler d1 list
```

```jsonc
{
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "notes",
      "database_id": "<D1_DATABASE_ID>",
      "migrations_dir": "migrations"
    }
  ]
}
```

- `d1 create` prints the binding snippet and the database UUID. Copy it into the config, then run `npx wrangler types`.
- Run SQL by hand with `npx wrangler d1 execute notes --command "SELECT 1" --local` (or `--remote`, or `--file ./query.sql`, or `--json`). `--local` uses the simulated database for `wrangler dev`; `--remote` hits the real database. State the target explicitly every time.
- For `wrangler dev --persist-to`, local state lives in `.wrangler/state` by default and `d1 execute --local --persist-to <dir>` must match it.
- `preview_database_id` in the binding selects a separate database for preview use; D1 can also be created with a location hint to place the primary near users.

## 2. Query API

```ts
interface Note {
  id: number;
  title: string;
  body: string;
}

async function getNote(env: Env, id: number): Promise<Note | null> {
  return env.DB.prepare("SELECT id, title, body FROM notes WHERE id = ?1").bind(id).first<Note>();
}

async function searchNotes(env: Env, term: string, limit: number): Promise<Note[]> {
  const pattern = `%${term.replace(/[%_\\]/g, "\\$&")}%`;
  const { results } = await env.DB.prepare(
    "SELECT id, title, body FROM notes WHERE title LIKE ?1 ESCAPE '\\' ORDER BY id DESC LIMIT ?2",
  )
    .bind(pattern, Math.min(limit, 100))
    .all<Note>();
  return results;
}

async function renameNote(env: Env, id: number, title: string): Promise<boolean> {
  const res = await env.DB.prepare("UPDATE notes SET title = ?1 WHERE id = ?2").bind(title, id).run();
  return res.meta.changes > 0;
}
```

- `prepare(sql)` returns a statement; `bind(...values)` attaches parameters and returns a new statement. D1 supports anonymous `?` and ordered `?NNN` parameters; the docs encourage `?NNN` because it is easy to miscount question marks. Named parameters are not supported.
- Terminal methods: `first()` (first row or null, optionally a column name), `all()` (`{ results, success, meta }`), `run()` (same shape; for writes), `raw()` (rows as arrays). `exec(sql)` runs raw SQL strings without binding and is meant for maintenance or migrations, not for user input.
- Never build SQL by concatenation. Dynamic identifiers (sort columns, table names) must come from a fixed whitelist:

```ts
const SORTABLE = { created: "created_at", title: "title" } as const;
function orderClause(key: string): string {
  return key in SORTABLE ? SORTABLE[key as keyof typeof SORTABLE] : "created_at";
}
```

- Bind values are limited to 100 bound parameters per query; chunk `IN (...)` lists.
- `meta` carries timing and row counts (for example `changes`, `last_row_id`, `rows_read`, `rows_written`); log them while tuning.
- Use `RETURNING` to get generated values in one round trip.
- Types: SQLite storage classes apply (INTEGER, REAL, TEXT, BLOB, NULL). Store timestamps as ISO 8601 text or Unix integers, booleans as 0 or 1, JSON as TEXT.
- Index every column used in a `WHERE` or `JOIN` on large tables; check plans with `EXPLAIN QUERY PLAN` through `d1 execute`. Rows read, not rows returned, drive cost.
- Foreign keys are enforced; when a migration must temporarily violate them, use `PRAGMA defer_foreign_keys = true`.

## 3. Batches and transactions

```ts
async function createNoteWithTags(env: Env, title: string, tags: string[]): Promise<void> {
  const insert = env.DB.prepare("INSERT INTO notes (title) VALUES (?1)").bind(title);
  const link = env.DB.prepare(
    "INSERT INTO note_tags (note_id, tag) VALUES (last_insert_rowid(), ?1)",
  );
  await env.DB.batch([insert, ...tags.map((t) => link.bind(t))]);
}
```

- `batch([...statements])` sends many statements in one round trip. Statements execute sequentially and non-concurrently. A batch is a SQL transaction: if one statement fails, the whole sequence is rolled back and an error is returned.
- Results come back as an array in the same order as the statements.
- A prepared statement can be reused by calling `bind()` repeatedly on it, as above.
- D1 has no interactive multi-request transaction from a Worker; do read-modify-write logic inside a single SQL statement or batch, or in a Durable Object.
- Every query counts as a subrequest-like call against the per-invocation limit (1,000 on Paid, 50 on Free), so batches also conserve that budget.

## 4. Migrations

```bash
npx wrangler d1 migrations create notes add_tags     # new file in migrations/
npx wrangler d1 migrations list notes --local        # unapplied migrations
npx wrangler d1 migrations apply notes --local
npx wrangler d1 migrations apply notes --remote
```

```sql
-- migrations/0001_init.sql
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  body TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes (created_at);
```

- Each migration is a `.sql` file with a version number in its name, applied in order. Applied names are recorded in the `d1_migrations` table (configurable with `migrations_table`); the folder is `migrations` by default (`migrations_dir`).
- Use the database name rather than the binding name on the command line to avoid applying to the wrong binding after a rename.
- `migrations_pattern` (a glob that must start with `migrations_dir`) supports nested layouts such as Drizzle's `migrations/0001_init/migration.sql`; generate files with the ORM's own command in that case.
- Migrations are forward-only. To undo, write a new migration. Before a risky remote migration, record a Time Travel bookmark (section 5).
- Apply to local first, run tests, then apply to remote, then deploy the Worker code that needs the new schema. For breaking changes use expand-then-contract: add columns and code that handles both, backfill, then remove old columns in a later release.
- Keep migrations idempotent where possible (`IF NOT EXISTS`) and small enough to stay under the statement length and duration limits.
- D1 uses SQLite syntax; SQLite `ALTER TABLE` is limited, so major column changes may need create-copy-drop-rename inside one migration.

## 5. Time Travel and exports

```bash
npx wrangler d1 time-travel info notes                      # current bookmark
npx wrangler d1 time-travel info notes --timestamp=<unix>   # bookmark at a time
npx wrangler d1 time-travel restore notes --bookmark=<bookmark>
npx wrangler d1 export notes --remote --output=backup.sql
```

- Time Travel is point-in-time recovery: restore to any minute within the retention window, which the limits page gives as 30 days on Workers Paid and 7 days on Free. Bookmarks are created automatically; bookmarks older than the window are invalid.
- Restoring does not delete older bookmarks, so a second restore to an earlier point is possible. A restore overwrites the database in place: take a new bookmark or an export first.
- There is a limit of 10 restore operations per 10 minutes per database.
- `wrangler d1 info <db>` shows `version`; `production` supports the Time Travel API, `alpha` only the older snapshot-based backups.
- `d1 export` writes the schema and data as a `.sql` file, useful for off-platform backups and for copying to local with `d1 execute --local --file`. Flags include `--table`, `--no-schema` and `--no-data`; `--output` is required.
- Confirm exact flag names with `npx wrangler d1 time-travel restore --help` before scripting.

## 6. Read replication and the Sessions API

- Status: global read replication is documented as Beta. Without it all queries go to the primary instance in one location.
- Replicas are asynchronously updated read-only copies in other regions. Replica lag means a replica can be out of date; the Sessions API provides sequential consistency within a session. Writes always go to the primary.
- Queries use replicas only when issued through a session. Using `env.DB.prepare()` directly continues to hit the primary.

```ts
export default {
  async fetch(request, env): Promise<Response> {
    const bookmark = request.headers.get("x-d1-bookmark") ?? "first-unconstrained";
    const session = env.DB.withSession(bookmark);

    const { results } = await session.prepare("SELECT id, title FROM notes ORDER BY id DESC LIMIT 20").all();

    const response = Response.json(results);
    response.headers.set("x-d1-bookmark", session.getBookmark() ?? "");
    return response;
  },
} satisfies ExportedHandler<Env>;
```

- `withSession("first-unconstrained")` lets the first query run on any instance; `"first-primary"` forces the first query to the primary; passing a bookmark continues a session so later reads are at least as fresh as that bookmark.
- Pass the bookmark back to the client (a header or cookie) and send it with the next request to preserve read-your-writes across requests.
- Read replication is enabled per database through the dashboard or API; follow the current read replication page for the exact steps and replica locations.
- Because the feature is beta, treat behaviour and pricing as subject to change.

## 7. D1 limits

From the D1 limits page (2026-10); re-check before quoting:

| Item | Free | Paid |
|---|---|---|
| Databases per account | 10 | 1,000,000 (first 100,000 included) |
| Maximum database size | 500 MB | 10 GB |
| Storage per account | 5 GB | 1 TB |
| Queries per Worker invocation | 50 | 1,000 |
| Time Travel retention | 7 days | 30 days |

- Other limits on both plans: 100 columns per table, 2,000,000 bytes per string, BLOB or row, 100,000 bytes per SQL statement, 100 bound parameters per query, 30 seconds maximum query duration, 50 MB maximum query result size, 5 GB maximum `d1 execute` file import.
- A single database is one SQLite instance with a single primary; scale out by sharding across databases (per tenant or per region) or by moving hot, coordinated state to Durable Objects.

## 8. KV

```ts
const profile = await env.CACHE_KV.get<{ name: string }>(`profile:${id}`, { type: "json", cacheTtl: 300 });
await env.CACHE_KV.put(`profile:${id}`, JSON.stringify(data), { expirationTtl: 3600 });
await env.CACHE_KV.delete(`profile:${id}`);
const page = await env.CACHE_KV.list({ prefix: "profile:", limit: 100 });
```

- KV is an eventually consistent edge store tuned for read-heavy, highly cacheable data: configuration, feature flags, routing tables, static JSON. Writes made in one location are usually visible there immediately but this is not guaranteed; other locations can take 60 seconds or more.
- The default `cacheTtl` for reads is 60 seconds. Raising it speeds reads of rarely changing keys at the cost of longer staleness.
- For write-after-write consistency, funnel writes for a key through a Durable Object and read from KV elsewhere. For strong consistency use a Durable Object or D1.
- Keep keys structured (`entity:id`), values small, and never use KV as a counter or lock.
- Create with `npx wrangler kv namespace create CACHE_KV`; add the printed `id` to `kv_namespaces`. `wrangler dev` uses local simulated KV.
- Use `expirationTtl` or `expiration` to age data out.

## 9. Durable Objects with SQLite

```ts
import { DurableObject } from "cloudflare:workers";

export class Room extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.storage.sql.exec(
      "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL)",
    );
  }

  async post(body: string): Promise<number> {
    this.ctx.storage.sql.exec("INSERT INTO messages (body) VALUES (?)", body);
    return this.ctx.storage.sql.exec("SELECT count(*) AS n FROM messages").one().n as number;
  }
}
```

```jsonc
{
  "durable_objects": { "bindings": [{ "name": "ROOM", "class_name": "Room" }] },
  "migrations": [{ "tag": "v1", "new_sqlite_classes": ["Room"] }]
}
```

```ts
const stub = env.ROOM.get(env.ROOM.idFromName("lobby"));
const count = await stub.post("hello"); // RPC call on the stub
```

- A Durable Object is a single-instance compute unit with private, transactional, strongly consistent storage. One named object handles all requests for its ID, so it suits rooms, per-user state, counters, rate limiters and coordination.
- SQLite storage is the recommended backend; classes must be declared with `new_sqlite_classes` in a migration (tags unique per entry) to get the SQL API on `ctx.storage.sql`. Storage also offers key-value, point-in-time recovery and alarm APIs.
- Persist anything that must survive deploys or eviction to storage; in-memory state is lost when the object is evicted or code updates. The default code update strategy is deferred with a 300 second maximum delay.
- Calls on a stub (RPC) are methods on the class; classes are exported by name from the main module.
- Durable Objects are the right tool for strict rate limits, unique-ID allocation and serialising writes; they are not a general database for large cross-object queries.
- `ctx.storage.sql.exec(query, ...bindings)` takes positional bindings; keep using bindings rather than string building.

## 10. Queues

```ts
// producer
await env.JOBS.send({ type: "resize", key });
await env.JOBS.sendBatch([{ body: { type: "resize", key: "a" } }, { body: { type: "resize", key: "b" } }]);

// consumer
export default {
  async queue(batch, env): Promise<void> {
    for (const message of batch.messages) {
      try {
        await process(env, message.body);
        message.ack();
      } catch {
        message.retry();
      }
    }
  },
} satisfies ExportedHandler<Env>;
```

- Producer binding: `queues.producers[]` with `binding` and `queue`. Consumer: `queues.consumers[]` with `queue`, `max_batch_size`, and optionally `dead_letter_queue`. Create queues with `npx wrangler queues create <name>`.
- Messages are delivered at least once; make handlers idempotent. Acknowledge each message that succeeded so a retry of the batch does not repeat it.
- Use a dead-letter queue for poison messages. Check the Queues docs for retry, delay and batch timeout settings and the current limits.
- R2 event notifications can feed a queue to trigger processing after uploads.

## 11. Hyperdrive

- Hyperdrive pools and accelerates connections from Workers to an existing regional database such as PostgreSQL. Bind it with `hyperdrive: [{ "binding": "HYPERDRIVE", "id": "<HYPERDRIVE_ID>" }]` and create the config with `npx wrangler hyperdrive create`.
- In the Worker, pass `env.HYPERDRIVE.connectionString` to a supported driver (such as `postgres` or `pg`), usually with `nodejs_compat`; create the client per request, not at module level, and close it with `ctx.waitUntil(client.end())` where the driver requires it. Check the Hyperdrive docs for the driver list, local development connection string and current limits.
- Keep database credentials in the Hyperdrive configuration, not in Worker code.
- Use D1 when a new database on the platform is acceptable; use Hyperdrive when data must remain in an existing external database.
