# Code Standards

Implementation rules and conventions for BazaarFlow. Follow these in every session without exception. These rules prevent pattern drift across sessions in a two-language codebase (Python API, TypeScript web).

---

## Engineering Mindset

- **Think before implementing** — understand what is being built and why before writing a line
- **Read context files first** — never assume; verify against `architecture.md` and `project-overview.md`
- **Scope is sacred** — build only what the current task requires. Business fields not in the PRD require a change request
- **Every feature must be testable** — if it cannot be verified immediately after implementation, it is incomplete
- **Clean over clever** — readable code a junior developer can follow beats clever abstraction
- **One thing at a time** — complete one feature fully before touching the next
- **Reference the feature ID** — every task cites its feature/form ID or PRD section

---

## The Rules That Cannot Be Broken

These are architectural guarantees, not style preferences. A PR that violates one does not merge.
Each rule ends with `— enforced by: <check>`.

1. **No secrets in source control.** Ever. `.env.example` holds keys with empty values. — enforced by: secret scan (`security.yml`)
2. **No raw SQL string concatenation, anywhere.** Parameterized queries or the ORM only. — enforced by: ruff rule `S608` (enabled in Phase 0) + architecture test that no `text()` call builds SQL with f-strings
3. **Every business table has `tenant_id`, `ENABLE` + `FORCE` row-level security, and no grants to `anon`/`authenticated`.** The API runtime role is `NOBYPASSRLS`. — enforced by: architecture test that introspects the migrated schema (Phase 0 architecture-tests task) + Supabase security advisor before release
4. **Every query is tenant-scoped.** Bypassing the scope filter requires an explicit comment justifying it and a reviewer's approval. — enforced by: architecture test that every tenant-owned entity is filtered + integration test
5. **No business logic in the frontend.** Calculation of price, tax, stock or totals happens in the backend only. The frontend formats and displays; it does not decide. — enforced by: review layer 2 + architecture rules
6. **The AI/agent service never gets a database connection string.** If a task seems to need one, the task is wrong. — enforced by: infrastructure network policy + `verify.sh` infra lane
7. **Money is a fixed-precision decimal** (`decimal` / `numeric(18,4)` / integer minor units). Never `float`/`double`/JS `number` for arithmetic. — enforced by: architecture test that fails on any `Float` column or `float` money field in `app/models` and `app/schemas` (Phase 0 architecture-tests task)

8. **Every route has an explicit authorization decision** (`require_role(...)` or `public`). — enforced by: architecture test that enumerates the router and fails on undecided routes
9. **Agent tools take tenant and user from the server-side context, never from model-supplied arguments**, and writes above tenant limits create an `agent_actions` approval row. — enforced by: architecture test over the tool catalog + AI tests (PRD §36.20)
10. **Messaging providers are used only through the channel adapter interface** (`connect`, `send`, `receive`, `verify_webhook`). — enforced by: `tests/architecture/test_provider_isolation.py` (provider SDK imports and hosts outside `app/integrations/`, with a shrink-only legacy list)
11. **Storage buckets are private; object paths start with the tenant id; access is by API-issued signed URL.** — enforced by: integration test on the storage service + review layer 2
12. **Schema changes ship only as Alembic migrations in the same PR.** — enforced by: `verify.sh --lane api-db` (`alembic check`)
13. **No `service_role` or other production credential in agent or developer environments, the browser bundle or `NEXT_PUBLIC_*`.** — enforced by: secret scan (`security.yml`) + `.env.example` review

---

## TypeScript / React / Next.js (`frontend`)

- Strict mode; no exceptions
- Never `any` — use `unknown` and narrow; no `as X` assertions unless commented why
- Explicit parameter and return types on all functions
- `type` for object shapes and unions; `interface` only for extendable component props
- `const` by default
- (Next.js App Router) Server Components by default; `"use client"` only for state, effects, browser APIs or client-only libraries; never on a layout unless genuinely required
- Data fetching on the server; never fetch directly from a Client Component when a server path exists
- API types come from the generated client. Hand-written request/response types are a defect
- Schema validation (Zod) mirrors backend validation for UX only — the backend remains authoritative
- Currency, date and quantity formatting always goes through one `lib/format` module. Never inline `toLocaleString`
- Permission checks go through one `can(module, screen, action)` helper — unauthorized actions are hidden or disabled
- Every list view implements loading, empty, error and unauthorized states. All four, every time

## Python (`.`)

- Python 3.12+; type hints on everything; `mypy --strict` in `verify.sh`
- Pydantic models for every input and output — no untyped dicts crossing a boundary
- `ruff` for lint and format; the edit hook runs `ruff --fix` on every touched file
- Timeouts on every outbound call
- Structured logging with a correlation/execution ID

---

## Naming

| Thing | Convention | Example |
| --- | --- | --- |
| Python modules, functions | `snake_case` | `inventory_service.add_stock` |
| Python classes | `PascalCase` | `StockMovement` |
| DB tables / columns | `lower_snake_case`, plural tables | `stock_movements.tenant_id` |
| Alembic revisions | `<yyyymmdd>_<short_description>` | `20261002_add_tenants` |
| TS components | `PascalCase` file and export | `ApprovalCard.tsx` |
| TS functions, hooks | `camelCase`, hooks start with `use` | `useApprovals` |
| Env vars | `UPPER_SNAKE_CASE` | `DATABASE_URL_MIGRATIONS` |
| API routes | kebab-case, plural | `/api/v1/purchase-orders` |
| Branches | `type/short-description` | `feat/f-001-short-name` |

---

## Error Handling

- **Backend:** one global handler returns structured problem details (RFC 7807). Domain rule violations return 422 with the rule; permission failures 403; never leak stack traces or SQL to the client
- **Frontend:** every mutation surfaces success and error with an actionable message. Never a bare "Something went wrong"
- Sensitive data is masked in all logs

---

## Testing

| Level | Scope | Tooling | Where |
| --- | --- | --- | --- |
| Unit | pricing, stock and ledger rules | pytest | `tests/unit/` |
| Architecture | RLS on every table, route authorization, tool isolation, no float money | pytest introspection | `tests/architecture/` |
| Integration | API + Postgres + auth + RLS + audit (real Postgres, not SQLite) | pytest + httpx | `tests/integration/` |
| Web component | forms, validation, permissions, four states | Vitest + Testing Library | `frontend/tests/` |
| E2E | onboarding, record sale, approval flow | Playwright (to add, label `run-e2e`) | `frontend/e2e/` |
| AI | tool authorization, tenant isolation, injection corpus, schemas | pytest with recorded model fixtures | `tests/ai/` |

Non-negotiable test coverage (keep only what applies to this project):

- Every scoping rule — a user in scope A cannot reach scope B data through **any** endpoint
- Every audited action actually writes an audit row
- Every permission — the API rejects an unauthorized action even when the UI would have hidden it
- Every AI tool — authorization, data isolation, action safety, schema validation, audit

Prefer one architecture test covering every endpoint/entity over a hand-written test per feature for the same rule. A new "every X must Y" invariant belongs in the architecture tests; a deliberate exception goes in that test's exemption list with its reason.

### Verification loop

`scripts/verify.sh` is the local mirror of CI and the definition of "verified" (see `AGENTS.md` — Verification). Run it, or let the Claude Code hooks run it, instead of choosing commands by hand. A new CI check is added as a `verify.sh` lane step that the workflow calls, so local and CI cannot drift.

---

## Git & Pull Requests

- Protected `main`. No direct pushes
- One logical change per PR
- PR description records: the requirement (feature ID / PRD section), test evidence, and database migration notes
- Every PR is reviewed and understood by a human developer. AI-generated code is the author's responsibility, not the tool's
- CI must pass: `api`, `api-db`, `web`, `infra`, `security` (gitleaks + actionlint); `e2e` when labelled `run-e2e`
- When CI fails on something `verify.sh` passed, the fix PR carries two changes: the fix, and the check that would have caught it locally

---

## AI-Assisted Development Protocol

1. **Requirement** — a small, testable story with acceptance criteria
2. **Context** — supply the relevant structure, conventions and constraints. `context/` is that context
3. **Design** — agree database/API/UI design *before* large generation (`/architect`)
4. **Generate** — scaffolding, implementation, refactoring, tests
5. **Review** — a human reviews all generated code, queries, security and error handling (`/review`)
6. **Test** — the acceptance tests from step 1 were written first and pass; `scripts/verify.sh` passes
7. **PR** — requirement, test evidence, migration notes
8. **Merge** — only approved, passing PRs reach protected branches

AI tooling is never given unrestricted production credentials or unrestricted database write access. Production deployment uses controlled CI/CD credentials only.
