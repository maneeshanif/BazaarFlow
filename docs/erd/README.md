# Database documentation (`docs/erd/`)

Entity-relationship diagrams for every table (35), **generated** from the schema, never hand-drawn. GitHub and most
editors render the Mermaid diagrams directly.

Start at **[overview.md](overview.md)**: all tables and every foreign key on one page, the rules that hold for the whole
schema, and links to the six context diagrams.

| Diagram | Tables |
| --- | --- |
| [overview.md](overview.md) | all 35, relationships only |
| [tenancy-security.md](tenancy-security.md) | tenants, users, memberships, refresh_tokens, login_attempts, tenant_integrations, webhook_events, audit_logs |
| [catalog-sales-finance.md](catalog-sales-finance.md) | products, inventory_items, stock_movements, customers, orders, order_items, payments, ledger_entries |
| [purchasing-vendors.md](purchasing-vendors.md) | vendors, vendor_bills, vendor_payments, purchase_orders, purchase_order_items |
| [conversations-support-voice.md](conversations-support-voice.md) | conversations, messages, support_tickets, voice_calls, voice_settings |
| [marketing.md](marketing.md) | facebook_accounts, marketing_posts, scheduled_campaigns, marketing_schedules, comment_replies |
| [ai-automation.md](ai-automation.md) | agent_actions, agent_runs, automations, automation_runs |

Each context page has the diagram (columns, keys, types), a table-by-table description, the relationships that exist in
the domain but have **no** database foreign key (and why), and the design choices worth knowing.

## Files

- `<context>.md` — generated. Do not edit.
- `<context>.template.md` — the hand-written prose around the diagram. Edit this.
- `erd.config.json` — which tables belong to which diagram.
- `generate_erd.py` — regenerates every diagram.

## Regenerating

Run this whenever a migration adds, removes or renames a table or column, and commit the result with the migration.

```
uv run python docs/erd/generate_erd.py --from-models     # reads the models; no database needed
python3 docs/erd/generate_erd.py                         # reads a live, migrated database ($DATABASE_URL)
```

`alembic check` (part of `scripts/verify.sh --slow`) fails when the models and the migrations differ, so the two
sources agree on a green build. `tests/architecture/test_erd_docs.py` fails when a table has no context, or when a
committed diagram no longer matches the models, so the diagrams cannot quietly go stale.

To document a new context, add an entry to `erd.config.json` and a `<context>.template.md` containing `{{DIAGRAM}}`.
