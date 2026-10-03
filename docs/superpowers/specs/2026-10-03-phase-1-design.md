# Phase 1 design brief (owner decisions, 2026-10-03)

Source of truth for scope stays PRD v0.1.2 and `context/build-plan.md`. This brief records how the owner
chose to run Phase 1; it adds no business field, rule or screen.

## Outcome
Exit gate (build-plan): a new visitor signs up, adds a product, records a sale by chat, sees stock and the
dashboard update, and approves a pending action, all within 15 minutes.

## Decisions
| Topic | Decision |
| --- | --- |
| Branch | `feat/phase-1-mvp`, from `main` at 03ad8d0 |
| Scope | Tasks 34-50, packs 51-58 and 63-65, plus carry-overs 02, 12, 21, 26, 29. Integration pack 59-62 -> Phase 2; voice 66-69 -> Phase 3 |
| Batches | A: data + shop basics (34, 35, 38-41, 43, 51-52, 55-56). B: AI (49, 37, 44, 45, 63-65, 29 runtime gate). C: surface + launch (36, 48, 42, 46, 47, 50, 53, 54, 57, 58, 02, 12, 21, 26) |
| Verification | Fast tier after each task; `verify.sh --slow --all` after each batch (owner exception to AGENTS.md "slow before each task") |
| Sign-up | Per-IP rate limit and password rules; no email verification (no email vendor in PRD) |
| LLM | Gemini by default behind the existing provider config; switchable by env vars |
| Auto-post limit | Default PKR 0: every AI write waits for approval; owner can raise it per shop |
| Storage | `service_role` only in the API host's secret store; local dev and tests use a fake storage adapter |
| Legacy | Replace and delete: each module moved to the DB removes its JSON route and old page in the same batch. Facebook scheduler and finance extras stay legacy until Phase 2 |
| Marketing studio (F-014) | AI drafts saved as drafts or sent to approvals; no Facebook publishing (Phase 2) |
| Live demo (F-027) | One click creates a throwaway seeded tenant per visitor, deleted after 24 h by a cleanup job |
| Language | English UI; sales agent accepts English and Roman Urdu |
| Git | Checkpoint commit per task; push the branch and fast-forward `main` after each batch passes its full run |
| Autonomy | Run A, B, C; stop only for "Needs a human" items; short report after each batch |
| Landing copy | Drafted from PRD positioning with existing design tokens |
| Web deploy | After batch C, once the owner has added Vercel secrets |

## Known risks carried in
- `main` is meant to be protected (code-standards); pushes to it happen at the owner's instruction.
- Real Supabase login and tenant-scoped reads are not yet proven end to end (needs `DEMO_USER_PASSWORD`).
- Task 29: `authorize_call` exists but no runtime path calls it; batch B wires it with approvals.
- Customer ordering by the agent saves directly today; it becomes approval-gated in batch B.
- Load test (`tests/load`) has not been run; run it after batch A against the Docker stack.
