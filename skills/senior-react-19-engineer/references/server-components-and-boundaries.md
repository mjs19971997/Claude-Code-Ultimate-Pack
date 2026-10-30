# Server Components, Server Functions and Boundaries

Verified against React 19.3.1 (2026-10). React defines the component model and the directives; bundlers and frameworks (Next.js, React Router, Waku, Parcel, Vite RSC plugin) implement them. Routing and caching live in the framework (see nextjs-15-architect for Next.js).

## Mental model

- A Server Component renders on the server (at build time or per request) and never ships its code to the browser. It can be `async`, can read databases and secrets, and cannot use state, Effects or browser APIs.
- A Client Component is any module reached through a `'use client'` file. It renders on the server during SSR for the initial HTML and then hydrates in the browser. Treat it as code running in the browser: no secrets, no privileged access.
- `'use client'` marks a boundary in the module graph, not a component. Everything imported by that module becomes client code. Put it on leaves.
- `'use server'` does not mark a Server Component. It marks Server Functions: async functions callable from the client over the network. Directive text must be at the top of the file (module level) or the function body.
- A Server Component can import a Client Component and pass props; a Client Component cannot import a Server Component, but can receive one as `children` or another JSX prop from a Server parent.

```tsx
// ClientShell.tsx
'use client'
import { useState, type ReactNode } from 'react'

export function Collapsible({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <section>
      <button aria-expanded={open} onClick={() => setOpen((o) => !o)}>{title}</button>
      {open && children}
    </section>
  )
}
```

```tsx
// Page.tsx (Server Component)
import { Collapsible } from './ClientShell'
import { getReport } from './reports.server'

export default async function Page({ id }: { id: string }) {
  const report = await getReport(id)           // runs on the server only
  return (
    <Collapsible title={report.title}>
      <ReportBody body={report.body} />        {/* stays a Server Component, passed as children */}
    </Collapsible>
  )
}

function ReportBody({ body }: { body: string }) {
  return <p>{body}</p>
}
```

## Serialization across the boundary

Props from Server to Client Components, and arguments and results of Server Functions, travel over the wire.

Supported for Server-to-Client props: strings, numbers, bigint, booleans, `undefined`, `null`, registered symbols (`Symbol.for`), iterables of serializable values (arrays, Map, Set, typed arrays, ArrayBuffer), Date, plain objects, Server Functions, JSX elements, Promises.

Not supported: functions that are not Server Functions (or exported from client modules), classes and class instances, objects with a null prototype, unregistered symbols.

Rules of thumb:

- Pass the smallest DTO the client needs, not a database row. Everything passed is visible in the browser.
- Pass a Promise to a Client Component and read it there with `use()` inside Suspense to stream data without blocking the shell. Its resolved value must also be serializable.
- Server Function arguments are a different (more restrictive) set than component props; check the `'use server'` docs for exact types. Keep them to primitives, plain objects, arrays and `FormData`.

## Server Functions

```ts
// actions.ts
'use server'
import 'server-only'
import { z } from 'zod'
import { getSession } from './session.server'   // your auth module; verifies the session cookie
import { db } from './db.server'                // your data layer

const input = z.object({ noteId: z.uuid(), body: z.string().trim().min(1).max(5000) })

export async function updateNote(formData: FormData): Promise<{ ok: boolean }> {
  const session = await getSession()
  if (!session) throw new Error('Unauthenticated')
  if (!session.permissions.includes('notes:write')) throw new Error('Forbidden')

  const parsed = input.safeParse({ noteId: formData.get('noteId'), body: formData.get('body') })
  if (!parsed.success) return { ok: false }

  // Scope the write by tenant and owner in the same statement.
  const updated = await db.updateNote({
    id: parsed.data.noteId,
    tenantId: session.tenantId,
    ownerId: session.userId,
    body: parsed.data.body,
  })
  return { ok: updated }
}

// Interfaces assumed by this sketch (replace with your own modules):
//   getSession(): Promise<{ userId: string; tenantId: string; permissions: string[] } | null>
//   db.updateNote(args): Promise<boolean>  -- executes UPDATE ... WHERE id AND tenant_id AND owner_id
```

- They are stable for application developers, but the bundler-level APIs used to implement them can change between 19.x minors; frameworks pin the React version they ship against.
- Call them from `<form action>` or inside a Transition. They are meant for mutations, not data fetching; frameworks typically run client calls one at a time.
- Every Server Function is reachable by anyone who can craft an HTTP request: validate arguments, authenticate, authorize the specific resource, and scope writes by tenant and owner. The server is the only trusted layer.
- Return serializable state for expected failures; do not return error objects or stack traces.
- Optional experimental taint APIs (`experimental_taintObjectReference`, `experimental_taintUniqueValue`) can block sensitive values from reaching client code; they do not replace DTO filtering.

## Context across the boundary

Server Components cannot create or consume Context (`createContext` and `use(Context)` are client features). In 19.3 a Server Component can render a Context imported from a `'use client'` module, so a wrapper Provider component is no longer required:

```tsx
// user-context.ts
'use client'
import { createContext } from 'react'

export type CurrentUser = { id: string; displayName: string } | null
export const UserContext = createContext<CurrentUser>(null)
```

```tsx
// Layout.tsx (Server Component)
import type { ReactNode } from 'react'
import { UserContext } from './user-context'
import { getCurrentUserDTO } from './session.server'

export async function Layout({ children }: { children: ReactNode }) {
  const user = await getCurrentUserDTO()         // DTO with only fields the UI may show
  return <UserContext value={user}>{children}</UserContext>
}
```

On React versions before 19.3 export a small `'use client'` Provider component that renders `<UserContext value={...}>`.

## Server-only helpers

- `cache(fn)` (from `react`, Server Components) deduplicates calls with the same arguments within one render pass. `cacheSignal()` (19.2) returns an `AbortSignal` that fires when the cache lifetime ends (render complete, aborted or failed) so you can cancel in-flight work.
- `import 'server-only'` (package `server-only`, supported by RSC bundlers) makes the build fail if a client module imports the file. Use it for data access, secrets and session code.
- Environment variables exposed to the client by bundlers (`VITE_*`, `NEXT_PUBLIC_*`) are public.

## Suspense, streaming and metadata

- Wrap slow Server Components in `<Suspense>`; the server streams the fallback first and the content when ready. SSR batches reveals of Suspense boundaries for a short time (19.2) so more content appears together.
- Partial pre-rendering primitives (19.2): `prerender(<App />, { signal })` from `react-dom/static` returns `{ prelude, postponed }`; `resume` (`react-dom/server`) and `resumeAndPrerender` (`react-dom/static`) continue from `postponed`. Frameworks use these; application code rarely calls them.
- Render `<title>`, `<meta>`, `<link>` and async stylesheets directly in components. React hoists them to `<head>`, dedupes stylesheets by `href` with `precedence`, and suspends until a stylesheet is loaded.
- `use(browser())` from `react-dom` (19.3) renders the Suspense fallback on the server and the component on the client, for UI that cannot be server rendered (it reads `localStorage` or the local time zone).

## Activity, ViewTransition and Fragment refs

```tsx
import { Activity, startTransition, useState, type ReactNode } from 'react'

export function Panels({ panels }: { panels: { id: string; label: string; content: ReactNode }[] }) {
  const [active, setActive] = useState(panels[0]?.id)
  return (
    <>
      <nav>
        {panels.map((p) => (
          <button key={p.id} aria-pressed={p.id === active} onClick={() => startTransition(() => setActive(p.id))}>
            {p.label}
          </button>
        ))}
      </nav>
      {panels.map((p) => (
        // Hidden panels keep their state (form input, scroll, expanded rows) and have their Effects cleaned up.
        <Activity key={p.id} mode={p.id === active ? 'visible' : 'hidden'}>
          <section>{p.content}</section>
        </Activity>
      ))}
    </>
  )
}
```

- `<Activity mode>`: `'hidden'` hides children with `display: none`, tears down their Effects (subscriptions are cleaned up), defers their updates at low priority, and preserves state; `'visible'` restores them and re-creates Effects. Default is `'visible'`. A hidden Activity that renders only text produces no output. Since 19.3, errors do not escape a hidden Activity and portals inside it are hidden.
- `<ViewTransition>` (stable in 19.3; wrap the element that should animate, for example `<ViewTransition><Panel /></ViewTransition>`) animates enter, exit, update and share changes triggered by `startTransition`, `<Suspense>` reveals or `useDeferredValue`. Updates outside a Transition do not animate.
- Fragment refs (19.3): attach a ref to `<Fragment>` to observe or focus a group of siblings without a wrapper element.
- For a real tab widget, wire the ARIA tab pattern and keyboard handling; see accessibility-expert.

## Common boundary mistakes

- Adding `'use client'` to a layout or page just to use one `useState`; move the stateful part into a small client component.
- Importing a server-only module (database client, secrets) into a Client Component; the build should fail because of `server-only`.
- Passing functions, class instances or ORM entities as props.
- Treating `'use server'` as a way to mark a component as server-rendered.
- Assuming a Server Function is private because no UI links to it.
- Reading `process.env` secrets outside the data layer.
