# BazaarFlow — Agent Instructions

This repository is built with AI assistance under a strict, documented process. Read `context/` before doing anything else — it is the authoritative source for architecture, build sequencing, and conventions, and it wins over general knowledge or training-data defaults.

## Read First, In Order

1. `context/project-overview.md` — what BazaarFlow is, who it serves, scope
2. `context/architecture.md` — layers, tenancy, Supabase design, data flow
3. `context/code-standards.md` — rules that cannot be broken, naming, testing
4. `context/library-docs.md` — how each library is used here, with gotchas
5. `context/ui-rules.md`, `context/ui-tokens.md`, `context/ui-registry.md` — UI work only
6. `context/build-plan.md` — phases and tasks with acceptance criteria
7. `context/progress-tracker.md` — live status (read last)

## Source of Truth

- `docs/prd/PRD.md` wins on **function**: scope, forms, workflows, roles, acceptance, phases.
- `docs/adr/` and PRD §3 win on **technology**: stack, tenancy model, Supabase design.
- `context/build-plan.md` wins on **order of work**; `context/code-standards.md` wins on **how code is written**.
- If two documents disagree, stop and record the conflict under "Needs a human" instead of choosing.

Never invent a business field, rule or screen that is not in the source documents — record a change request in `docs/adr/` first.

## Non-Negotiable Constraints

- **Tenant isolation:** every business table has `tenant_id`, `ENABLE`+`FORCE` RLS and no `anon`/`authenticated` grants; the API runtime role is `NOBYPASSRLS`; sessions set `app.tenant_id` per request (PRD §3.5, §3.8).
- **The API owns logic and data.** Browser, webhooks, scheduler and AI agents are tenant-scoped clients; agents hold no database credentials and never take tenant/user from model output.
- **Every route has an explicit authorization decision** (`require_role` or `public`).
- **Approvals:** agent writes to money, stock or public content go through `agent_actions` approval unless under the tenant's configured limit; every agent write has an audit row.
- **Schema changes** ship only as Alembic migrations (with RLS) in the same PR; migrations run as the `migrator` role over the direct connection.
- **No secrets in source control**; integration tokens are encrypted at rest and masked in logs; no `service_role` key in agent/dev environments or the browser.
- **Money is `NUMERIC(14,2)`** — never float.
- **External providers** (Meta, Twilio, VAPI, LLM) only through adapters with timeouts, retries and idempotency keys.
- **UI uses design tokens and registry components only;** no hard-coded colours; four states on every list.
- **Scope:** no field, screen or feature outside the PRD without a change request (PRD §25).

## Verification — How "Done" Is Decided

Verification is mechanical and automatic. Do not hand-pick test commands, start the app, or click through the UI to convince yourself a change works.

- **`scripts/verify.sh`** is the single definition of "verified". It runs only the lanes your changes affect (`api`, `api-db`, `web`, `infra`) with the same commands CI runs. Default is the **fast tier** (format, lint, types, unit tests: seconds). `--slow` adds integration tests, builds, scans and drift checks; `--all` runs every lane with the slow tier; `--lane <name>` runs one; `--list` shows what would run. A fast PASS lists every slow check it deferred. Run `--slow` before you call a task finished. **Phase 1 exception (owner, 2026-10-03):** work runs in batches A/B/C (`docs/superpowers/specs/2026-10-03-phase-1-design.md`); the fast tier runs after every task and `--slow --all` runs once at the end of each batch, which is when a batch counts as verified.
- **Per edit** (Claude Code `PostToolUse` hook, `.claude/settings.json`): the edited file is formatted/lint-fixed in seconds; problems that cannot be auto-fixed are reported back immediately.
- **Per turn** (`Stop` hook): when you finish with uncommitted changes, the fast tier runs. If it fails you are not done: fix the reported failures. Never weaken, skip or delete a check to make it pass.
- **Checkpoints:** after each verified step, make a local commit on the task branch. A failed run returns to the last checkpoint instead of restarting. Never push without the developer's say.
- **Needs a human:** if verification cannot be trusted (an unreadable review verdict, a check you cannot run, a rule that conflicts with the task), stop and write the question under "Needs a human" in your reply and in `context/progress-tracker.md`. Do not guess.
- **When a run goes wrong,** name the failure class and fix the surface it lives on, per `HARNESS.md`. Then run `bash scripts/harness-check.sh`.
- **Per push** (`.githooks/pre-push`, enable once per clone with `bash scripts/install-hooks.sh`): the same lanes, for commits made outside an agent session.
- **Manual/browser checks** only for UI work, when the `review` skill calls for them.
- **E2E** (`.github/workflows/e2e.yml`) runs on PRs labelled `run-e2e` and manually until Playwright is added to `frontend/`.

Write tests for the behaviour the plan's **acceptance tests** name (see `architect`), plus the non-negotiable coverage in `context/code-standards.md`. Do not write tests for trivia.

**When CI fails on something `verify.sh` passed**, the fix PR carries two changes: the fix, and the check (a `verify.sh` step, an architecture test, or a lint rule) that would have caught it locally. CI should surprise us at most once per failure class.

## Skills

This repo's `skills/` directory defines the working process:

- `architect` — think through a feature before writing code; produces a plan with acceptance tests
- `imprint` — capture UI patterns into `context/ui-registry.md` after building a component
- `review` — verify a finished feature against the plan, the architecture, and production readiness
- `recover` — diagnose a failure (bug vs. polluted session vs. wrong approach) before responding to it
- `remember` — save/restore session state between sessions

## Current Status

See `context/progress-tracker.md` for the live phase/task status.
