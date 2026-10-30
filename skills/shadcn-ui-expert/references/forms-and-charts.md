# Forms, Toasts and Charts

Reference for building forms with the shadcn `Field` components, showing toasts with sonner and drawing charts with the chart component. Verified against the shadcn/ui forms, sonner and chart docs, React Hook Form 7.91, TanStack Form (`@tanstack/react-form`) 1.33, Zod 4.6, `@hookform/resolvers` 6.0, sonner 2.0.8 and Recharts 3.10 (2026-10).

## 1. Field components

Install: `npx shadcn@latest add field input textarea button`.

| Part | Use |
|---|---|
| `FieldSet`, `FieldLegend` | Semantic `<fieldset>` and `<legend>` for related controls (radio and checkbox groups) |
| `FieldGroup` | Vertical stack of fields; spacing and container-query layout |
| `Field` | One labeled control; `orientation` supports `vertical`, `horizontal` and `responsive`; takes `data-invalid` |
| `FieldContent`, `FieldTitle` | Label and description column for horizontal layouts such as switches |
| `FieldLabel` | `<label>`; pair with the control's `id` through `htmlFor` |
| `FieldDescription` | Help text |
| `FieldError` | Renders `errors` (array of objects with `message`) |
| `FieldSeparator` | Divider between field groups |

Invalid-state contract: put `data-invalid` on `Field` (styles the label and description) and `aria-invalid` on the control itself (`Input`, `Textarea`, `SelectTrigger`, `Checkbox`). The current docs do not use a separate `Form` component; older projects may still contain `Form`, `FormField` and `FormMessage`, which can be migrated to this pattern one form at a time.

## 2. React Hook Form with Zod

```bash
npm install react-hook-form @hookform/resolvers zod
```

```tsx
"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"
import * as z from "zod"

import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"

const formSchema = z.object({
  title: z.string().min(5, "Title must be at least 5 characters.").max(32),
  email: z.string().email("Enter a valid email address."),
})

type FormValues = z.infer<typeof formSchema>

export function BugReportForm({ action }: { action: (values: FormValues) => Promise<void> }) {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { title: "", email: "" },
    mode: "onTouched",
  })

  async function onSubmit(values: FormValues) {
    try {
      await action(values)
      toast.success("Report sent")
      form.reset()
    } catch {
      toast.error("Could not send the report. Try again.")
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <FieldGroup>
        <Controller
          name="title"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="bug-title">Title</FieldLabel>
              <Input
                {...field}
                id="bug-title"
                aria-invalid={fieldState.invalid}
                autoComplete="off"
              />
              <FieldDescription>A short summary of the problem.</FieldDescription>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />
        <Controller
          name="email"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="bug-email">Email</FieldLabel>
              <Input
                {...field}
                id="bug-email"
                type="email"
                aria-invalid={fieldState.invalid}
                autoComplete="email"
              />
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          Send
        </Button>
      </FieldGroup>
    </form>
  )
}
```

Notes:

- The docs example uses Zod with `zodResolver`; any Standard Schema library supported by React Hook Form works. Check that your installed `@hookform/resolvers` version supports your Zod major version.
- `mode` controls when validation runs (`onSubmit` default, `onChange`, `onBlur`, `onTouched`, `all`); `onTouched` avoids errors while the user is still typing the first time.
- Use `Controller` for controlled shadcn components (`Select`, `Checkbox`, `Switch`, `RadioGroup`); native inputs can use `register`.
- The server action or API must re-validate; the client schema is a UX aid.

## 3. TanStack Form

```bash
npm install @tanstack/react-form zod
```

```tsx
"use client"

import { useForm } from "@tanstack/react-form"
import * as z from "zod"

import { Button } from "@/components/ui/button"
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"

const formSchema = z.object({ title: z.string().min(5, "Title must be at least 5 characters.") })

export function TitleForm() {
  const form = useForm({
    defaultValues: { title: "" },
    validators: { onSubmit: formSchema },
    onSubmit: async ({ value }) => {
      // send value to the server
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
    >
      <FieldGroup>
        <form.Field name="title">
          {(field) => {
            const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={field.name}>Title</FieldLabel>
                <Input
                  id={field.name}
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  aria-invalid={isInvalid}
                />
                {isInvalid && <FieldError errors={field.state.meta.errors} />}
              </Field>
            )
          }}
        </form.Field>
        <Button type="submit">Save</Button>
      </FieldGroup>
    </form>
  )
}
```

Validators can be set per event (`onChange`, `onBlur`, `onSubmit`); see the TanStack Form docs for async validation and form-level errors.

## 4. Server actions without a form library

For small forms a native `<form action={serverAction}>` with `useActionState` (React 19) returns field errors from the server. Render them through `Field data-invalid`, `aria-invalid` and `FieldError errors={[{ message }]}`; this keeps the same markup and works without client JavaScript.

## 5. Sonner toasts

```bash
npx shadcn@latest add sonner
```

```tsx
// app/layout.tsx (inside ThemeProvider so the toaster follows the theme)
import { Toaster } from "@/components/ui/sonner"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  )
}
```

```tsx
import { toast } from "sonner"

toast("Event has been created.")
toast.success("Saved")
toast.error("Could not save", { description: "Check your connection and retry." })
toast.promise(save(), {
  loading: "Saving...",
  success: "Saved",
  error: "Save failed",
})
```

- The shadcn `Toaster` wraps sonner's `Toaster` and reads the theme from next-themes; `position` and other props follow the sonner API.
- Mount `<Toaster />` once. Call `toast` from client code (event handlers, form `onSubmit`, effects), not from a Server Component body.
- Do not rely on a toast for errors that need user action; show `FieldError` or an inline alert and use the toast as a supplement. Keep messages short and free of untrusted HTML.
- The docs also list a `toast` component built on Base UI for the `base` component base; the sonner component is documented for `radix`. Check `shadcn docs sonner --base <base>` for your project.

## 6. Charts

```bash
npx shadcn@latest add chart
```

The chart component wraps Recharts (v3 in current docs) without hiding it: you write ordinary Recharts components inside `ChartContainer`.

```tsx
"use client"

import { Bar, BarChart, CartesianGrid, XAxis } from "recharts"

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

const chartData = [
  { month: "January", desktop: 186, mobile: 80 },
  { month: "February", desktop: 305, mobile: 200 },
  { month: "March", desktop: 237, mobile: 120 },
]

const chartConfig = {
  desktop: { label: "Desktop", color: "var(--chart-1)" },
  mobile: { label: "Mobile", color: "var(--chart-2)" },
} satisfies ChartConfig

export function VisitorsChart() {
  return (
    <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
      <BarChart accessibilityLayer data={chartData}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="month"
          tickLine={false}
          tickMargin={10}
          axisLine={false}
          tickFormatter={(value: string) => value.slice(0, 3)}
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="desktop" fill="var(--color-desktop)" radius={4} />
        <Bar dataKey="mobile" fill="var(--color-mobile)" radius={4} />
      </BarChart>
    </ChartContainer>
  )
}
```

- `chartConfig` maps each data key to a label, optional icon and a color (or theme-specific colors); the container exposes `--color-<key>` variables that series reference as `fill="var(--color-desktop)"`.
- Chart colors come from `--chart-1` to `--chart-5`, defined for light and dark. Use `var(--chart-1)`, not `hsl(var(--chart-1))`.
- Give `ChartContainer` an explicit height or aspect (`min-h-[200px]`, `h-*`, `aspect-video`); without it the responsive container cannot measure on first render.
- Keep `accessibilityLayer` on the Recharts chart for keyboard and screen reader support, and provide a text summary or a table alternative for important data.
- Upgrading from Recharts 2: `ChartTooltip` `defaultIndex` is for the initial tooltip only; remove `layout` from `Bar` when `BarChart` already sets it; follow the "Updating to Recharts v3" section of the chart docs.
- Charts are client components; load heavy dashboards with `next/dynamic` when below the fold.
