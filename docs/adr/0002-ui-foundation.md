# ADR 0002: UI foundation (tokens, shell, Tailwind version)

Status: accepted for task 07 (the owner can overturn it)
Date: 2026-10-02

## Context
`context/ui-tokens.md` is written for Tailwind CSS v4 (`@theme`). The frontend runs Tailwind 3.x with shadcn/ui, whose
components and about 30 legacy pages depend on Tailwind 3 behaviour and on shadcn's CSS variables. The marketing
header and footer wrapped every route, so there was no place for an application shell.

## Decision
- Stay on Tailwind 3. Express the design tokens as CSS variables in `app/global.css` and map them in
  `tailwind.config.js`; the names follow `ui-tokens.md` except where they would collide with shadcn
  (`action` instead of `accent`, `text-ui-*` instead of overriding `text-sm`). Deviations are listed in
  `context/ui-tokens.md`.
- Split the App Router tree into route groups: `(marketing)` keeps the public header/footer and every existing page
  (URLs unchanged); `(app)` is for the signed-in application and uses `AppShell`. The root layout only has html/body,
  fonts and the toaster.
- Enforce "tokens only" with `scripts/check-tokens.mjs`: new code must have zero hard-coded colour, type or spacing
  values; legacy pages are on a shrink-only baseline (`token-baseline.json`).
- Test the foundation with Vitest + Testing Library (components, formatting, navigation, checker) and Playwright
  (no horizontal scroll at 360, 768, 1280 and 1440 px; the grid scrolls inside its own container).

## Alternatives rejected
Upgrading to Tailwind 4 now (risk to every legacy page for no launch benefit; revisit when the legacy pages are
rebuilt in phase 1), restyling shadcn's `accent` (breaks existing components), and a lint plugin for Tailwind classes
(does not cover hex/rgb literals or inline styles).

## Consequences
Legacy pages still contain 1,700+ hard-coded values; each page shrinks the baseline when it is rebuilt on the shell.
The identity (colours, type) is provisional (PRD section 33): only token values change when branding arrives.
