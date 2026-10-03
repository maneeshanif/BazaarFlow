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
| Button, buttonClass | `frontend/components/app/Button.tsx` | built (task 51) |
| TextInput, SelectInput, TextArea, Checkbox | `frontend/components/form/Controls.tsx` | built (task 51) |
| ConfirmDialog | `frontend/components/app/ConfirmDialog.tsx` | built (task 51) |
| WorkspaceShell (signed-in frame for new pages) | `frontend/components/app/WorkspaceShell.tsx` | built (task 51) |
| ProductForm, StockPanel (master form + stock history pattern) | `frontend/components/inventory/` | built (tasks 41, 51) |
| useLoad (four states), useSubmit (one request at a time) | `frontend/hooks/` | built (task 52) |
| API client and problem-details errors | `frontend/lib/api/client.ts` | built (task 51) |
| LookupDialog (standard search dialog), CustomerLookup, ProductPicker | `frontend/components/app/LookupDialog.tsx`, `frontend/components/sales/` | built (task 38) |
| SaleForm (transaction form: master fields, line grid, server-side totals) | `frontend/components/sales/SaleForm.tsx` | built (task 38) |
| ReverseDialog (destructive action with a required reason) | `frontend/components/orders/ReverseDialog.tsx` | built (task 39) |
| TeamMemberForm, RoleGuide | `frontend/components/team/` | built (task 43) |
| ApprovalCard (+ RejectDialog, EditApprovalDialog), ChatPanel, AgentStatusPanel | `frontend/components/agent/` | built (tasks 37, 44, 45) |
| DraftBriefForm, PostEditor (marketing studio) | `frontend/components/marketing/` | built (task 42) |
| DashboardView, SalesTrend (home) | `frontend/components/dashboard/` | built (tasks 36, 48) |

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

### Button / buttonClass
Purpose: the one button. Variants primary (`bg-action text-fg-inverse`), secondary (`border border-border bg-surface`), ghost, danger (`bg-danger text-fg-inverse`); sizes sm/md/lg map to `h-control-sm|md|lg`. `loading` disables it and sets `aria-busy`. Use `buttonClass(variant, size)` for a Link that must look like a button.
Don't: use `components/ui/button` (legacy shadcn colours) in new screens.

### Controls
Purpose: form controls on the control tokens: `h-control-md w-full rounded-md border bg-surface px-3 text-ui-base`, focus ring `ring-line-focus`, `invalid` switches the border to `border-danger` and sets `aria-invalid`. Numbers use `text-right font-mono tabular-nums`. Always inside a FormField.

### Master form pattern (ProductForm)
Compose FormShell mode="master"; fields in `grid grid-cols-1 gap-4 md:grid-cols-2`. A field shows its message once visited (blur) or after a submit attempt, and clears as soon as it is valid; never validate fields the person has not reached (it also shifts the layout under the cursor). Server errors: per-field under the field, the rest in one `role="alert"` banner at the top of the form. Submit through `useSubmit` (one request at a time, button `loading`). Success: toast that names the record. Destructive actions go through ConfirmDialog naming the record. Quantities that change only through movements are read-only and say how to change them.

### List pattern (Products page)
PageHeader with the primary action, a filter panel (`role="search"`), DataTable with all four states through `useLoad`, "Showing x to y of total" and Previous/Next with the API cursor. Empty state differs when filters are active ("No products match", with Clear filters) from truly empty (with the first-record action). Hide columns a role must not see (cost for staff) and the primary action for roles that cannot use it.

### Transaction form pattern (SaleForm)
FormShell in transaction mode: master fields (lookup for the customer, select for how they paid, optional amounts), the detail grid (a real table with a labelled input per cell, a "No items yet" row that says what to do, a Remove button per row), totals (a `dl` that is `aria-busy` while the server recalculates), actions (Cancel, then the primary "Post sale", disabled while settling and after posting), audit text. Every figure comes from the server (`/sales/preview`); the browser never adds money up. The Idempotency-Key is created once per form, so a retry posts once. After a successful post the form is done: the button stays disabled until navigation.

### Lookup fields (LookupDialog)
A large master list is never a plain select. The trigger is a secondary Button whose `aria-label` carries the current value ("Customer: Walk-in customer. Change"), because a `<label>` pointed at a button would replace its name. The dialog has a search box, results as full-width buttons (hover and focus-visible `bg-surface-hover`), an empty message that says what to do, and an optional footer for "add new".

### Approval card
`article` with an `aria-label` that names the kind and the summary; header = kind + StatusBadge; the summary; a bullet list of plain-words details (a line starting "Problem:" is `text-danger`); who asked and when it expires; the decision note (`role="alert"` when the run failed); right-aligned actions Reject, Edit, Approve (primary). Staff see "Waiting for a manager" instead of buttons. The same component serves the Approvals page and the inline card in the chat.

### Chat panel
Messages in an `aria-live="polite"` list; the user's messages `bg-action text-fg-inverse` right-aligned, the assistant's `bg-surface-sunken` with a border (warning tone for paused/limit outcomes); a visually hidden "You:" / "Assistant:" prefix; proposals appear as approval cards under the message that created them; Enter sends and Shift+Enter breaks the line; the empty state explains the flow and offers examples in English and Roman Urdu.

### Dashboard pattern
A period filter (`role="search"`), then a briefing card, then a `Key figures` region of `KpiCard`s (value, delta with sign, link to the records behind it), then a chart section. Cards a role may not see are never rendered because the API does not send them. Charts are drawn from server figures only and always come with an `sr-only` table; with no data the chart section says what to do and offers the primary action instead of an empty plot.

### Draft-then-approve (marketing studio)
AI output is a saved draft first: editable fields with a character count, "Save changes" (disabled until something changed), "Send for approval" (saves pending edits first), "Remove draft" (confirmed, names the post). Once sent the fields are read-only and the page says who decides and where. The approval card for it has no Edit button: it is edited here, not there.

### Public site (landing, live demo)
Own route group `app/(site)` with its own layout, fonts (Young Serif display, JetBrains Mono slip) and tokens (`ink`, `ledger`, `stamp`, `brass`, `display-lg/xl`): a shop ledger. One orchestrated motion, the hero sale slip (`components/site/HeroSlip.tsx`, GSAP): the finished state is plain HTML, motion only hides and reveals it and is skipped under reduced motion. Button classes live in `components/site/styles.ts` (never export class strings from a client module). Content rules: no unverifiable claims; planned channels are named as "coming next".
