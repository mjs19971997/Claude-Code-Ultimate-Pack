# Reactivity and Composables

Reference for the Vue 3.5 reactivity system, `<script setup>` macros, composable design, and provide/inject. Verified against Vue 3.5.44 and vue-tsc 3.3.14 (2026-10). Vue 3.6 (Vapor mode) is published only as a release candidate (npm tag `rc`, 3.6.0-rc.14) and is not covered as stable.

## Contents

1. [ref, reactive, shallowRef](#1-ref-reactive-shallowref)
2. [computed](#2-computed)
3. [watch, watchEffect and cleanup](#3-watch-watcheffect-and-cleanup)
4. [Props, emits and defineModel](#4-props-emits-and-definemodel)
5. [Template refs](#5-template-refs)
6. [Composables](#6-composables)
7. [provide and inject](#7-provide-and-inject)
8. [Slots, expose and options](#8-slots-expose-and-options)

## 1. ref, reactive, shallowRef

| API | Use when | Watch out for |
|---|---|---|
| `ref(v)` | Default choice for any value, including objects and arrays | Needs `.value` in script, unwrapped in templates only at top level |
| `reactive(obj)` | A local object whose identity never changes | Replacing the variable loses reactivity; destructuring breaks tracking; does not work for primitives |
| `shallowRef(v)` | Large objects, class instances, third-party objects (maps, charts) replaced as a whole | Mutating inner fields does not trigger; assign a new value or call `triggerRef` |
| `shallowReactive` | Only top-level keys are reactive | Same trade-off as `shallowRef` |
| `readonly(x)` | Hand a read-only view to a child or a store consumer | Does not copy; the source can still change |
| `toRef(obj, 'key')` / `toRefs(obj)` | Keep reactivity when pulling fields out of a reactive object | `toRefs` on a `reactive` created from props is rarely needed with props destructure |
| `toValue(x)` | Normalise `MaybeRefOrGetter<T>` arguments in composables | Call it inside `watch` getters or `computed` so it stays tracked |

```ts
import { reactive, ref, toRefs, shallowRef } from 'vue'

const form = reactive({ name: '', tags: [] as string[] })
const { name } = toRefs(form) // name.value stays linked to form.name
const chart = shallowRef<Chart | null>(null) // a heavy third-party instance
```

- `reactive` returns a Proxy; compare with the proxy, not the raw object. `toRaw(x)` returns the original.
- Reassigning a `ref` holding an array (`list.value = list.value.filter(...)`) and mutating it (`list.value.push(x)`) both work.
- Avoid wrapping DOM nodes, `Map` of large size, or class instances with private fields in deep reactivity; prefer `shallowRef` or `markRaw`.

## 2. computed

- `computed(() => ...)` is cached and lazy; the getter must be pure (no assignment, no fetch, no DOM access).
- Writable form: `computed({ get, set })` for adapters such as a `v-model` over a derived value.
- Since Vue 3.4 a computed returns the old value without triggering dependents when the new result is `Object.is` equal. In 3.4+ the getter receives the previous value as its first argument.
- Do not use `computed` to sort in place: `[...items.value].sort(...)`, not `items.value.sort(...)`.
- Prefer `computed` over `watch` when the result is derived state with no side effects.

## 3. watch, watchEffect and cleanup

```ts
import { ref, watch, watchEffect, onWatcherCleanup } from 'vue'

const query = ref('')
const results = ref<string[]>([])

watch(query, async (q) => {
  const controller = new AbortController()
  onWatcherCleanup(() => controller.abort()) // Vue 3.5+, call before any await
  if (!q) { results.value = []; return }
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`, { signal: controller.signal })
  results.value = await res.json()
})
```

| Option | Meaning |
|---|---|
| `immediate: true` | Run the callback once at creation |
| `once: true` | Run the callback once, then stop (Vue 3.4+) |
| `deep: true` or `deep: n` | Traverse nested values; a number limits the depth (Vue 3.5+). Costly on large trees |
| `flush: 'pre'` (default) | Run before the component updates |
| `flush: 'post'` | Run after the DOM updated; use when reading layout. Shortcut `watchPostEffect` |
| `flush: 'sync'` | Run on every change synchronously; rarely correct |

- Watch a getter for a single field of a `reactive` object: `watch(() => state.id, ...)`. `watch(state.id, ...)` passes a plain number and fails.
- `watchEffect` tracks whatever it reads synchronously; reads after an `await` are not tracked. Use `watch` with explicit sources when the dependency list matters.
- `onWatcherCleanup` must be called synchronously inside the watcher callback or effect; the third callback argument `onCleanup` also works and has no such restriction.
- Stop manual watchers with the returned handle when they are created outside setup; those created in setup stop with the component.

## 4. Props, emits and defineModel

```vue
<script setup lang="ts">
interface Props {
  items: readonly string[]
  max?: number
  variant?: 'solid' | 'outline'
}
// Reactive props destructure (stable in Vue 3.5): defaults are plain JS defaults.
const { items, max = 10, variant = 'solid' } = defineProps<Props>()

const emit = defineEmits<{
  select: [item: string]
  close: []
}>()

const open = defineModel<boolean>('open', { default: false }) // parent: v-model:open
const query = defineModel<string>({ required: true }) // parent: v-model

const visible = computed(() => items.slice(0, max))
watch(() => max, (m) => console.log(m)) // wrap destructured props in a getter
</script>
```

- Destructured props are compiled to `props.x` accesses. Passing one to `watch` or to a composable as a bare value loses tracking; use `() => max` or `toRef(() => max)`.
- Object and array defaults work directly with destructure (`const { tags = [] } = defineProps<{ tags?: string[] }>()`); the compiler wraps them in a factory. Without destructure, use `withDefaults(defineProps<Props>(), { tags: () => [] })`.
- `defineModel()` creates a prop plus an `update:` event. Assigning to the returned ref emits the event. Modifiers are available through `const [model, modifiers] = defineModel<string, 'trim'>()`.
- Event payload types use the named-tuple syntax shown above (Vue 3.3+); the older call-signature syntax also works.
- Never mutate a prop object from a child; emit an event or use `defineModel`.
- Boolean casting: a prop typed `boolean` is `true` when present without a value and `false` when absent.

## 5. Template refs

```vue
<script setup lang="ts">
import { useTemplateRef, onMounted } from 'vue'
import MyDialog from './MyDialog.vue'

const input = useTemplateRef<HTMLInputElement>('input') // Vue 3.5+, string id matches ref="input"
const dialog = useTemplateRef('dialog') // the type is inferred from the component by vue-tsc
onMounted(() => input.value?.focus())
</script>
<template>
  <input ref="input" />
  <MyDialog ref="dialog" />
</template>
```

- The ref is `null` until mount and inside `v-if` that is false; always guard.
- `useTemplateRef` replaces the pattern of declaring `const input = ref(null)` with the same name as the template ref. Both keep working.
- A component exposes to a parent ref only what it lists in `defineExpose({ focus })`.
- For `v-for`, the ref holds an array whose order is not guaranteed to match the source array.

## 6. Composables

A composable is a function that uses Composition API state and lifecycle hooks and returns reactive values.

```ts
import { onScopeDispose, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

export function useDebounced<T>(source: MaybeRefOrGetter<T>, ms = 300) {
  const debounced = ref(toValue(source)) as { value: T }
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(
    () => toValue(source),
    (value) => {
      clearTimeout(timer)
      timer = setTimeout(() => { debounced.value = value }, ms)
    },
  )
  onScopeDispose(() => clearTimeout(timer))
  return debounced
}
```

Rules:

- Name it `useX`, one file per composable under `src/composables/`.
- Accept `MaybeRefOrGetter<T>` for inputs and read them with `toValue`. Return an object of refs (or a single ref), not a `reactive` object, so callers can destructure.
- Register cleanup with `onScopeDispose` (works in any effect scope) or `onUnmounted` (component only). Remove listeners, timers, observers, and abort requests.
- Call composables synchronously in `setup`, not after an `await` (other than in `<script setup>`, where the compiler restores the instance for the first `await`) and not inside event handlers.
- Do not create module-level state unless it is meant to be a singleton shared across requests; in SSR, module state leaks between users. Use Pinia or `provide` per app instead.
- Side effects that need the DOM (`window`, `document`) belong in `onMounted` for SSR safety.
- For shared reactive state outside components use `effectScope()` and `scope.run(...)`, and stop the scope when done.

## 7. provide and inject

```ts
// keys.ts
import type { InjectionKey, Ref } from 'vue'
export interface Theme { mode: Ref<'light' | 'dark'>; toggle: () => void }
export const themeKey: InjectionKey<Theme> = Symbol('theme')
```

```ts
// Provider.vue (script setup)
import { provide, ref } from 'vue'
import { themeKey } from './keys'
const mode = ref<'light' | 'dark'>('light')
provide(themeKey, { mode, toggle: () => { mode.value = mode.value === 'light' ? 'dark' : 'light' } })
```

```ts
// Consumer
import { inject } from 'vue'
import { themeKey } from './keys'
const theme = inject(themeKey)
if (!theme) throw new Error('themeKey was not provided')
```

- `inject(key)` returns `T | undefined` unless a default is supplied (`inject(key, fallback)`, or a factory with `true` as the third argument). A small `useTheme()` wrapper that throws keeps call sites clean.
- Provide refs (not unwrapped values) so consumers stay reactive; expose mutations as functions on the same object so the provider owns the writes.
- App-level: `app.provide(key, value)` in `main.ts`.
- Use `readonly(mode)` when consumers must not write.
- Prefer props for one level of nesting and Pinia for state used across unrelated parts of the tree.

## 8. Slots, expose and options

```vue
<script setup lang="ts" generic="T extends { id: string }">
defineProps<{ rows: T[] }>()
defineSlots<{
  row(props: { row: T; index: number }): any
  empty(): any
}>()
defineOptions({ inheritAttrs: false, name: 'DataList' })
</script>
```

- `generic="..."` declares a generic component; vue-tsc infers `T` from props.
- `defineSlots` types slot props for the parent; it is a compile-time macro with no runtime effect.
- `defineOptions` sets `name` and `inheritAttrs` without a second `<script>` block.
- Macros (`defineProps`, `defineEmits`, `defineModel`, `defineExpose`, `defineSlots`, `defineOptions`) are compiler hints: they are not imported and must sit at the top level of `<script setup>`.
- `useId()` (Vue 3.5+) returns an ID that is stable across server and client; use it for `for`/`id` pairs instead of counters or random numbers.
- `Teleport` accepts `defer` (Vue 3.5+) to target an element rendered later in the same tick.
- Lazy hydration (Vue 3.5+): `defineAsyncComponent({ loader, hydrate: hydrateOnVisible() })` delays hydration of server-rendered components until visible.
