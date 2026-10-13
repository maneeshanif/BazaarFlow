# BazaarFlow database — overview

> Generated from the schema by `docs/erd/generate_erd.py`. Do not hand-edit the diagram; edit
> `overview.template.md` for the prose. Column-level detail is in the six context diagrams linked below.

35 tables in one PostgreSQL schema (Supabase). Every line below is a real foreign key; relationships to `tenants` are
left off because **every table except `tenants`, `users` and `login_attempts` carries a `tenant_id`** that points at it.

```mermaid
erDiagram
    %% Tenancy and security
    tenants
    users
    memberships
    refresh_tokens
    login_attempts
    tenant_integrations
    webhook_events
    audit_logs
    %% Catalog, inventory and sales
    products
    inventory_items
    stock_movements
    customers
    orders
    order_items
    payments
    ledger_entries
    %% Purchasing and vendors
    vendors
    vendor_bills
    vendor_payments
    purchase_orders
    purchase_order_items
    %% Conversations, support and voice
    conversations
    messages
    support_tickets
    voice_calls
    voice_settings
    %% Marketing
    facebook_accounts
    marketing_posts
    scheduled_campaigns
    marketing_schedules
    comment_replies
    %% AI and automation
    agent_actions
    agent_runs
    automations
    automation_runs

    automations ||--o{ automation_runs : "automation_id"
    marketing_posts ||--o{ comment_replies : "post_id"
    customers ||--o{ conversations : "customer_id"
    products ||--o{ inventory_items : "product_id"
    users ||--o{ memberships : "user_id"
    conversations ||--o{ messages : "conversation_id"
    customers ||--o{ messages : "customer_id"
    orders ||--o{ order_items : "order_id"
    products ||--o{ order_items : "product_id"
    customers ||--o{ orders : "customer_id"
    customers ||--o{ payments : "customer_id"
    orders ||--o{ payments : "order_id"
    vendors ||--o{ products : "vendor_id"
    products ||--o{ purchase_order_items : "product_id"
    purchase_orders ||--o{ purchase_order_items : "purchase_order_id"
    vendors ||--o{ purchase_orders : "vendor_id"
    users ||--o{ refresh_tokens : "user_id"
    products ||--o{ stock_movements : "product_id"
    vendors ||--o{ vendor_bills : "vendor_id"
    vendors ||--o{ vendor_payments : "vendor_id"
    support_tickets ||--o{ voice_calls : "ticket_id"
```

## The six contexts

| Context | Diagram | What it holds |
| --- | --- | --- |
| Tenancy and security | [tenancy-security.md](tenancy-security.md) | Shops, people, roles, sessions, connected providers, the audit trail |
| Catalog, inventory and sales | [catalog-sales-finance.md](catalog-sales-finance.md) | Products, stock and its movements, customers, orders, payments, the customer credit (udhaar) ledger |
| Purchasing and vendors | [purchasing-vendors.md](purchasing-vendors.md) | Vendors, what the shop owes them, draft purchase orders |
| Conversations, support and voice | [conversations-support-voice.md](conversations-support-voice.md) | WhatsApp threads and messages, support tickets, voice calls and settings |
| Marketing | [marketing.md](marketing.md) | Facebook page link, posts, the posting schedule, comment replies |
| AI and automation | [ai-automation.md](ai-automation.md) | Approvals, agent runs, automation recipes and their history |

## Rules that hold for the whole schema

| Rule | How it shows in the tables |
| --- | --- |
| **Tenant isolation** | `tenant_id` on every business table, with row level security `ENABLE`d and `FORCE`d and one `tenant_isolation` policy. The API's database role is `NOBYPASSRLS`; the Data API roles have no grants. A test fails when a table lacks either. |
| **Money is exact** | Every money column is `NUMERIC(14,2)`, never a float (`price`, `cost`, `amount`, `balance`, `total`, `subtotal`, `discount`, `unit_cost`). |
| **Ids and time** | Every primary key is one `uuid` column named `id`. Every timestamp is `timestamptz`. |
| **History is append-only** | `audit_logs`, `stock_movements`, `ledger_entries`, `agent_runs`, `webhook_events`, `vendor_bills` and `vendor_payments` cannot be updated or deleted by the API's database role: a correction is a new row. `automation_runs` and `login_attempts` also have no `updated_at` (`login_attempts` rows are purged by the sign-in code once they fall outside the lock-out window). |
| **Soft delete** | `customers`, `vendors` and `products` are never removed: `deleted_at` marks them gone, so history that points at them stays readable. |
| **Optimistic concurrency** | `orders` and `inventory_items` carry a `version` column so two writers cannot silently overwrite each other. |
| **Every change leaves a trace** | State-changing actions by a person or an agent write an `audit_logs` row; agent actions that touch money, stock or public content go through `agent_actions` first. |

## How the pieces connect

- **A sale** is one transaction: an `orders` row with its `order_items`, one `stock_movements` row per line, a
  `payments` row for what was paid, and a `ledger_entries` row for the part left on credit.
- **A reorder** starts in `inventory_items` (`qty_on_hand <= reorder_level`), becomes an `agent_actions` approval to
  message the vendor, and is mirrored by a draft `purchase_orders` row.
- **An AI action** is an `agent_runs` row (what was asked and answered, redacted) and, when it wants to change something
  that matters, an `agent_actions` row waiting for a person.
- **A customer message** lands in `messages` under a `conversations` thread; `webhook_events` makes sure a replayed
  provider event is processed once.
