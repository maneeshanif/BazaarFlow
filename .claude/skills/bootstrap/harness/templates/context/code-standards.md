# Code Standards

Implementation rules and conventions for {{PROJECT_NAME}}. Follow these in every session without exception. These rules prevent pattern drift across sessions{{MULTI_LANGUAGE_NOTE}}.

<!-- Template notes for /bootstrap (removed by render.py):
     - Blocks opened by an @stack:X marker and closed by @end are kept only when stack X is chosen.
     - Blocks opened by an @when:X marker and closed by @end are kept only when the PRD has feature X
       (tenancy, audit, money, ai-agents, api-contract, database, ui, posted-documents).
     - Every rule in "Rules That Cannot Be Broken" must name the test, lint or architecture check that enforces it.
       A rule nothing enforces is a wish; either add the check as a verify.sh step or move it to conventions. -->

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

<!-- @when:always -->
1. **No secrets in source control.** Ever. `.env.example` holds keys with empty values. — enforced by: secret scan (`security.yml`)
2. **No raw SQL string concatenation, anywhere.** Parameterized queries or the ORM only. — enforced by: {{SQL_CHECK}}
<!-- @end -->
<!-- @when:api-contract -->
3. **`{{CLIENT_DIR}}` is generated from the API contract, never hand-edited.** — enforced by: `verify.sh --lane contract` and the edit hook
<!-- @end -->
<!-- @when:tenancy -->
4. **Every query is tenant-scoped.** Bypassing the scope filter requires an explicit comment justifying it and a reviewer's approval. — enforced by: architecture test that every tenant-owned entity is filtered + integration test
<!-- @end -->
<!-- @when:ui -->
5. **No business logic in the frontend.** Calculation of price, tax, stock or totals happens in the backend only. The frontend formats and displays; it does not decide. — enforced by: review layer 2 + architecture rules
<!-- @end -->
<!-- @when:ai-agents -->
6. **The AI/agent service never gets a database connection string.** If a task seems to need one, the task is wrong. — enforced by: infrastructure network policy + `verify.sh` infra lane
<!-- @end -->
<!-- @when:money -->
7. **Money is a fixed-precision decimal** (`decimal` / `numeric(18,4)` / integer minor units). Never `float`/`double`/JS `number` for arithmetic. — enforced by: {{MONEY_CHECK}}
<!-- @end -->
<!-- @when:posted-documents -->
8. **Posted financial and inventory documents expose no unrestricted Edit/Delete.** Corrections happen through reversal documents. — enforced by: integration test + architecture test
<!-- @end -->

{{PROJECT_RULES}}

---

<!-- @stack:dotnet -->
## C# / ASP.NET Core (`{{API_DIR}}`)

### Layering

| Project | May reference | Must never contain |
| --- | --- | --- |
| `{{NS}}.Domain` | nothing | ORM, web framework, HTTP, DTOs |
| `{{NS}}.Application` | `Domain` | ORM/`DbContext`, HTTP concerns |
| `{{NS}}.Infrastructure` | `Application`, `Domain` | controllers |
| `{{NS}}.Api` | `Application`, `Infrastructure` | business rules |

`Application` defines interfaces; `Infrastructure` implements them. Dependencies point inward, always. Enforce with an architecture test project (reflection over assembly references) — no database, milliseconds.

### Conventions

- Nullable reference types enabled; warnings as errors (`Directory.Build.props`)
- `sealed` by default on classes not designed for inheritance
- One `IEntityTypeConfiguration<T>` per entity; no mapping attributes on domain entities
- Async all the way down; every async method takes a `CancellationToken` and passes it on
- No `.Result`, no `.Wait()`, no `async void`
- Controllers are thin: validate, delegate to an application service, map the result. No logic
- Validation library for every command/request DTO; domain invariants live in the entity, the validator handles shape
- Explicit transactions around any multi-entity financial or inventory operation
- Never expose a domain entity from a controller — always a DTO
- Every schema change ships as a migration in the same PR; migrations are never edited after merge
- Index every foreign key and every column used in a scoping filter or high-volume lookup
- `AsNoTracking()` for read-only queries; never `Include` a large collection into a list view
<!-- @end -->

<!-- @stack:typescript -->
## TypeScript / React / Next.js (`{{WEB_DIR}}`)

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
<!-- @end -->

<!-- @stack:python -->
## Python (`{{PY_DIR}}`)

- Python 3.12+; type hints on everything; `mypy --strict` in `verify.sh`
- Pydantic models for every input and output — no untyped dicts crossing a boundary
- `ruff` for lint and format; the edit hook runs `ruff --fix` on every touched file
- Timeouts on every outbound call
- Structured logging with a correlation/execution ID
<!-- @end -->

<!-- @stack:go -->
## Go (`{{GO_DIR}}`)

- `gofmt` clean, `go vet` clean; errors are wrapped with context, never swallowed
- Context (`context.Context`) is the first parameter of anything that does I/O
- Table-driven tests
<!-- @end -->

---

## Naming

| Thing | Convention | Example |
| --- | --- | --- |
{{NAMING_TABLE}}
| API routes | kebab-case, plural | `/api/v1/purchase-orders` |
| Branches | `type/short-description` | `feat/f-001-short-name` |

---

## Error Handling

- **Backend:** one global handler returns structured problem details (RFC 7807). Domain rule violations return 422 with the rule; permission failures 403; never leak stack traces or SQL to the client
- **Frontend:** every mutation surfaces success and error with an actionable message. Never a bare "Something went wrong"
- Sensitive data is masked in all logs

---

## Testing

{{TESTING_TABLE}}

Non-negotiable test coverage (keep only what applies to this project):

<!-- @when:tenancy -->
- Every scoping rule — a user in scope A cannot reach scope B data through **any** endpoint
<!-- @end -->
<!-- @when:audit -->
- Every audited action actually writes an audit row
<!-- @end -->
- Every permission — the API rejects an unauthorized action even when the UI would have hidden it
<!-- @when:ai-agents -->
- Every AI tool — authorization, data isolation, action safety, schema validation, audit
<!-- @end -->
<!-- @when:posted-documents -->
- Idempotency — a replayed transaction ID never double-posts
<!-- @end -->

Prefer one architecture test covering every endpoint/entity over a hand-written test per feature for the same rule. A new "every X must Y" invariant belongs in the architecture tests; a deliberate exception goes in that test's exemption list with its reason.

### Verification loop

`scripts/verify.sh` is the local mirror of CI and the definition of "verified" (see `AGENTS.md` — Verification). Run it, or let the Claude Code hooks run it, instead of choosing commands by hand. A new CI check is added as a `verify.sh` lane step that the workflow calls, so local and CI cannot drift.

---

## Git & Pull Requests

- Protected `main`. No direct pushes
- One logical change per PR
- PR description records: the requirement (feature ID / PRD section), test evidence, and database migration notes
- Every PR is reviewed and understood by a human developer. AI-generated code is the author's responsibility, not the tool's
- CI must pass: {{CI_CHECKS}}
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
