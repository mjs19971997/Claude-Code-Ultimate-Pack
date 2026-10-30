# Server Actions and Data Mutation in Next.js

Verified against Next.js 16.4.3 and 15.5.x, React 19.3.1, Zod 4.6.7 (2026-10). Server Actions are React Server Functions invoked from forms or event handlers. Behavior is the same on 15 and 16 except the cache invalidation APIs (`updateTag` and `refresh` are 16 only; `revalidateTag` takes a second argument in 16).

## Mental model

- A `'use server'` function (file level or inline in a Server Component) becomes a POST endpoint. Unused exports are removed from the client bundle, and used ones get encrypted, non-deterministic ids, but a leaked or replayed id is still callable. Treat every action as a public API.
- Arguments arrive from the client and must be serializable; they are untrusted regardless of TypeScript types.
- The client dispatches actions one at a time; do not rely on `Promise.all` to run several in parallel. Do parallel work inside one action or in a Server Component.
- Variables captured by an inline action are encrypted before they reach the client. Self-hosted multi-instance deployments need the same `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` on every instance. Captured values are still not a substitute for server-side authorization.
- Forms using `<form action={fn}>` work before hydration; after hydration the browser does not reload.

## Action anatomy

Order of operations inside every action:

1. Authenticate: obtain the session from the server (cookie plus lookup or signature verification) inside the action.
2. Authorize: check the capability (`orders:update`) and, for object-level access, the specific resource.
3. Validate: parse inputs with a schema; pick fields explicitly from `FormData`.
4. Write: single statement scoped by tenant and owner (`WHERE id = $1 AND tenant_id = $2 AND user_id = $3`), so there is no check-then-write gap.
5. Invalidate: `updateTag` (read-your-writes), `revalidateTag(tag, 'max')`, `revalidatePath` or `refresh`. None of them throws, so the action can still return a value.
6. Respond: return serializable state for expected failures; `redirect()` last (it throws, so code after it does not run).

```typescript
// src/lib/auth.ts
import 'server-only'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export type Session = { userId: string; tenantId: string; permissions: readonly string[] }

// Your auth library verifies the session cookie here (signature or server-side lookup).
declare function verifySessionCookie(value: string | undefined): Promise<Session | null>

export async function requireSession(): Promise<Session> {
  const session = await verifySessionCookie((await cookies()).get('__Host-session')?.value)
  if (!session) redirect('/login')
  return session
}

export function requirePermission(session: Session, permission: string): void {
  if (!session.permissions.includes(permission)) throw new Error('Forbidden')
}
```

## Data access layer for writes

Keep the `"use server"` file thin and put the authorization-aware write in a server-only module, so the same rules apply wherever it is called.

```typescript
// src/lib/data/orders-write.ts
import 'server-only'
import { pool } from '@/lib/db'
import type { Session } from '@/lib/auth'

export async function cancelOrder(session: Session, orderId: string): Promise<boolean> {
  if (!session.permissions.includes('orders:cancel')) throw new Error('Forbidden')
  const { rowCount } = await pool.query(
    `UPDATE orders SET status = 'cancelled', updated_at = now()
      WHERE id = $1 AND tenant_id = $2 AND user_id = $3 AND status IN ('pending', 'paid')`,
    [orderId, session.tenantId, session.userId],
  )
  return rowCount === 1
}
```

```typescript
// src/app/(app)/orders/cancel-action.ts
'use server'
import { z } from 'zod'
import { updateTag } from 'next/cache'
import { requireSession } from '@/lib/auth'
import { cancelOrder } from '@/lib/data/orders-write'

const input = z.object({ orderId: z.uuid() })

export async function cancelOrderAction(orderId: string): Promise<{ ok: boolean }> {
  const session = await requireSession()
  const parsed = input.safeParse({ orderId })
  if (!parsed.success) return { ok: false }
  const ok = await cancelOrder(session, parsed.data.orderId)
  if (ok) updateTag(`orders:${session.tenantId}:${session.userId}`)
  return { ok }
}
```

`cancelOrderAction.bind(null, id)` is fine for convenience, but the bound value still comes from the client and is validated like any other argument.

## Validation and error state

- Expected failures (validation, conflicts, permission denied) return state; unexpected ones throw to the nearest error boundary.
- `useActionState(action, initialState)` passes the previous state as the first argument, so the action signature is `(prev, formData)`.
- With Zod 4: `schema.safeParse(...)`, then `z.flattenError(result.error).fieldErrors` for per-field messages. Do not echo raw error objects or database errors to the client.
- Use `z.strictObject` on an object you build yourself; do not run a strict schema over `Object.fromEntries(formData)` because the form contains framework hidden fields such as `$ACTION_*`.
- Limit sizes: `z.string().max(n)`, array lengths, file size and type checks. Raise `serverActions.bodySizeLimit` (under `experimental`) only for routes that need it; the default is 1 MB.
- File uploads: check the MIME type and size on the server, generate the storage key yourself (never use the client file name as a path), and store outside the web root or in object storage.

## Optimistic UI

```tsx
'use client'
import { useOptimistic, useTransition } from 'react'
import { cancelOrderAction } from './cancel-action'

type Row = { id: string; status: string }

export function OrderRow({ order }: { order: Row }) {
  const [optimistic, setOptimistic] = useOptimistic(order.status)
  const [pending, startTransition] = useTransition()

  return (
    <li>
      {order.id}: {optimistic}
      <button
        disabled={pending || optimistic === 'cancelled'}
        onClick={() =>
          startTransition(async () => {
            setOptimistic('cancelled')              // must run inside a Transition or Action
            await cancelOrderAction(order.id)       // the server decides; props reset to real data afterwards
          })
        }
      >
        Cancel
      </button>
    </li>
  )
}
```

The optimistic value reverts to the real prop when the transition finishes; the revalidated server data is what stays.

## Choosing the invalidation call

| Need | Call |
|---|---|
| The user must see their own change immediately | `updateTag(tag)` (Server Actions only, 16) |
| Stale content is acceptable while fresh data loads | `revalidateTag(tag, 'max')` |
| A webhook or external service changed data | `revalidateTag(tag, 'max')` in a route handler |
| One route is affected, no tags | `revalidatePath('/orders')` |
| Only UI state outside the cache changed | `refresh()` (16) |
| Next.js 15 | `revalidateTag(tag)` or `revalidatePath(path)`; no `updateTag` |

`updateTag`, `revalidatePath` and `refresh` make the action response include a re-rendered route payload; `revalidateTag` with a stale-while-revalidate profile intentionally does not.

## Route handlers for third parties

Use `route.ts` for endpoints called by other systems. Authenticate the caller (signature or token), parse with a schema, and invalidate with `revalidateTag(tag, 'max')`.

```typescript
// src/app/api/webhooks/catalog/route.ts
import { createHmac, timingSafeEqual } from 'node:crypto'
import { revalidateTag } from 'next/cache'
import { z } from 'zod'

const payload = z.object({ productId: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/) })

export async function POST(request: Request) {
  const secret = process.env.CATALOG_WEBHOOK_SECRET
  if (!secret) return new Response(null, { status: 500 })

  const raw = await request.text()                                   // verify over the raw body
  const received = Buffer.from(request.headers.get('x-signature') ?? '', 'hex')
  const expected = createHmac('sha256', secret).update(raw).digest()
  if (received.length !== expected.length || !timingSafeEqual(received, expected)) {
    return new Response(null, { status: 401 })
  }

  let json: unknown
  try { json = JSON.parse(raw) } catch { return new Response(null, { status: 400 }) }
  const parsed = payload.safeParse(json)
  if (!parsed.success) return new Response(null, { status: 400 })

  revalidateTag(`product:${parsed.data.productId}`, 'max')
  return new Response(null, { status: 204 })
}
```

Follow the provider's documented signature scheme (timestamp tolerance, replay protection) and prefer its official verifier when one exists; the above shows the shape only.

## Forms

- `<form action={serverAction}>` in Server or Client Components; `useActionState` for returned state; `useFormStatus` from `react-dom` inside a child of the form for pending state; `next/form` for GET forms that navigate with a query string.
- Forms are reset by React after a successful action; return the submitted values in state when fields must persist after an error, and render them as `defaultValue`.
- CSRF: the `Origin` header is compared with `Host` (or `X-Forwarded-Host`). Behind a proxy that changes the host, forward the original host or list trusted hosts in `experimental.serverActions.allowedOrigins`.
- Authentication cookies: `HttpOnly`, `Secure`, `SameSite=Lax` or `Strict`, `__Host-` prefix when possible; set them from Server Actions or route handlers via `(await cookies()).set(...)`.

## Mistakes specific to actions

- Authorizing only the page that renders the form.
- Accepting `tenantId`, `userId`, `role` or `price` from `formData`.
- Updating by `id` alone, then checking ownership afterwards, or not checking at all (IDOR).
- Calling `redirect()` before `updateTag`/`revalidateTag`; code after `redirect()` does not run.
- Returning thrown database errors or stack traces to the client.
- Exporting non-async values or non-function constants from a `'use server'` file; only async functions may be exported (types are fine).
