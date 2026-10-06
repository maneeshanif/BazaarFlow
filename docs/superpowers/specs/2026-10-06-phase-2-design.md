# Phase 2 design brief (autonomous run, 2026-10-06)

Source of truth for scope stays PRD v0.1.2 and `context/build-plan.md`. The owner asked for every Phase 2 task that
does not need a decision to be built while they are away. This brief records the defaults chosen for each open
question so the owner can overrule them afterwards; it adds no business field, rule or screen beyond PRD §5.2/§5.3/§7.

## Outcome
Exit gate (build-plan): a tenant connects WhatsApp sandbox and Facebook in the wizard; a customer message gets an AI
reply; an owner takes over; a scheduled post publishes. Everything except the live vendor calls is built and tested
against recorded responses; the live parts are listed under "Needs a human".

## Decisions (defaults, change on request)
| Topic | Default |
| --- | --- |
| Branch | stay on `feat/phase-1-mvp` (no push, no merge to `main`) |
| Batches | D: shop data (72, 73, 74, 78, 80, 81, 79, 82). E: channels (83, 84, 85, 59-62, 77, 71, 75, 76, 70). Fast tier after every task, `--slow --all` once per batch |
| Vendors (F-012) | DB table `vendors` (already exists, soft-delete) keeps name/phone/balance; adds `bills` (purchase bills, `NUMERIC(14,2)`) and vendor payments through the existing append-only `ledger_entries` (`party_type='vendor'`: debit = bill, credit = payment). Balance = sum of entries (what the shop owes). The legacy JSON `vendors` route is a WhatsApp-vendor registry (a different meaning of "vendor" = tenant) and stays legacy until the integrations batch replaces it with `tenant_integrations` |
| Finance (F-013) | read-only report over orders, payments, ledger entries; no new money tables. Expenses are out of scope (no field spec in the PRD) |
| Shop settings (F-020) | writes only existing `tenants` columns (name, owner_phone, city, timezone, currency read-only PKR, agents_enabled, agent_cap_usd read-only) |
| Platform admin (F-025, D-004) | operator-only endpoints use `require_platform_admin`; reads cross tenants through a dedicated platform session, never an `app.tenant_id` bypass of RLS for tenant routes |
| Integrations (F-018) | `tenant_integrations` rows; credentials encrypted with a key from settings (`INTEGRATIONS_ENCRYPTION_KEY`), write-only, masked, never returned |
| Providers | Twilio, Facebook Graph and Pexels only through adapters with timeout, retry, idempotency; tested with recorded fixtures (no network). Live sandbox runs are owner actions (task 26) |
| Out of scope | Phase 3 (voice, recipes, insights, Embedded Signup, system logs) and Phase 4 (billing). Task 92 has no content |

## Known risks carried in
- No vendor sandbox credentials exist yet (task 26), so no live provider call is proven.
- `.env.example` is protected from the assistant (task 12), so new variables are documented in
  `docs/operations/env-vars.md` and `docs/operations/env.example.proposed` only.
