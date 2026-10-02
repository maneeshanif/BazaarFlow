# UI Registry

Living document. Updated after every component is built (the `imprint` skill does this). Read this before building any new component — match existing patterns exactly before inventing new ones.

This file is what keeps BazaarFlow from drifting into many slightly different interpretations of the same layout.

---

## How to Use

Before building any component:

1. Check whether a similar component already exists here.
2. If yes — use it. If it needs a variant, add the variant to the existing component; do not fork it.
3. If no — build it following `ui-rules.md` and `ui-tokens.md`, then add it here.

After building any component, record: name, file path, purpose, variants, and the exact token classes used.

---

## Component Inventory

| Component | Path | Status |
| --- | --- | --- |
| AppShell | `frontend/components/app/AppShell.tsx` | built (task 07) |
| PageHeader | `frontend/components/app/PageHeader.tsx` | built |
| KpiCard | `frontend/components/app/KpiCard.tsx` | built |
| DataTable | `frontend/components/app/DataTable.tsx` | built |
| StatusBadge | `frontend/components/app/StatusBadge.tsx` | built |
| EmptyState / ErrorState / UnauthorizedState / TableSkeleton | `frontend/components/app/StateViews.tsx` | built |
| FormShell | `frontend/components/form/FormShell.tsx` | built |
| FormField | `frontend/components/form/FormField.tsx` | built |
| Formatting (money, number, date) | `frontend/lib/format.ts` | built |
| Navigation by role | `frontend/lib/navigation.ts` | built |
| Status -> tone | `frontend/lib/status.ts` | built |

---

## Components

### AppShell
Purpose: the signed-in application frame (PRD section 4). Persistent 240px sidebar from `lg` (1024px), drawer below it, 56px topbar, five-item tab bar on phones.
Classes: sidebar `w-sidebar border-r border-border bg-surface`; topbar `h-topbar border-b border-border bg-surface`; page `bg-canvas text-fg`; nav item `h-control-md rounded-md px-3 text-ui-base`, active `bg-action-subtle text-action font-medium`, idle `text-fg-muted hover:bg-surface-hover`; focus ring `focus-visible:ring-2 focus-visible:ring-line-focus`.
Do: pass `role` (navigation is filtered, unauthorized items are hidden); give pages `p-4 md:p-6` through the shell, never add a page-level horizontal scroller.
Don't: render the marketing header inside the shell (marketing pages live in `app/(marketing)`).

### DataTable
Purpose: the one data grid. Props: `caption`, `columns`, `rows`, `state` = ready | loading | empty | error | unauthorized, `emptyMessage/emptyAction`, `errorMessage/onRetry`.
Columns: `numeric` and `money` right-aligned with `tabular-nums` (`money` also `font-mono`), `mono` for SKUs and ids, `status` renders a StatusBadge.
Classes: container `overflow-x-auto rounded-lg border border-border bg-surface` (the grid scrolls inside itself), header `bg-surface-sunken text-ui-xs font-medium text-fg-muted` (sticky), cells `px-3 py-2 text-ui-sm`, row `border-t border-border hover:bg-surface-hover`.
Do: always pass a `state`; use `loading` with skeleton rows, never a spinner.

### StatusBadge
Purpose: status as text in a tinted pill. Tone comes from `lib/status.ts`, never chosen in the component.
Classes: `rounded-sm border px-2 py-0.5 text-ui-2xs font-medium` + one of `bg-success-subtle text-success border-success-border` (and warning, danger, info, neutral; accent = `bg-action-subtle text-action border-action-border`).
Don't: show a status as coloured text or a dot alone.

### FormShell
Purpose: the mandated form layout, in order: header (title + status badge), filters/master fields, detail grid, totals, actions (right-aligned, primary last), audit panel. `mode="master"` drops the grid and totals and caps width at `max-w-form`.
Classes: panels `rounded-lg border border-border bg-surface p-4`, title `text-ui-lg font-semibold text-fg`, audit `text-ui-xs text-fg-muted`.
Do: compose it for every form; Don't: hand-roll the section order.

### FormField
Purpose: label above control, required asterisk (`text-danger`), inline error directly below (`role="alert"`, `text-ui-xs text-danger`), optional hint (`text-ui-xs text-fg-subtle`). Label `text-ui-xs font-medium text-fg-muted`.

### KpiCard
Purpose: one dashboard figure that links to the records behind it. Value `font-mono text-ui-xl font-semibold tabular-nums`, delta `text-positive` / `text-negative`.

### State views
EmptyState (explains + offers the fixing action), ErrorState (`role="alert"`, "Try again", never a stack trace), UnauthorizedState ("Access is restricted", never a blank screen), TableSkeleton (rows that match the table).
