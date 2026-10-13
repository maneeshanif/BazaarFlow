# AI and automation — ERD

> Generated from the schema by `docs/erd/generate_erd.py`. Do not hand-edit the diagram;
> edit `ai-automation.template.md` for the prose.

What the AI assistants did, what they were allowed to do on their own, what waits for a person, and the automation
recipes that run on a schedule. Back to the [overview](overview.md).

```mermaid
{{DIAGRAM}}
```

## Tables

| Table | One row is | Notes |
| --- | --- | --- |
| `agent_actions` | One thing an agent wants to do that needs a person | `status` runs pending, approved, rejected, expired, executed or failed. `payload_json` is exactly what will run; `payload_hash` proves it was not changed after approval. Expires after 24 hours by default. |
| `agent_runs` | One agent run | Append-only. The redacted input and output, the tool-call trace, tokens, cost (`spend_micros`), duration and `outcome`. `user_id` is empty for the customer-facing agent (no staff user is behind it). |
| `automations` | One recipe switched on or off for a shop | Unique per (shop, recipe `key`). `consecutive_failures` drives the "needs attention" banner at three. |
| `automation_runs` | One run of a recipe | Append-only. `trigger_source` is schedule or manual; `status` is succeeded or failed with a plain reason. |

## Unenforced relationships

| Column | Points at | Why there is no FK |
| --- | --- | --- |
| `agent_actions.requested_by`, `decided_by` | A user, or the fixed id of an agent or recipe | Agents and recipes are not users. |
| `agent_runs.action_ids` | A list of `agent_actions.id` (JSON) | One run can file several approvals. |
| `agent_runs.user_id` | A user | Empty for runs with no person behind them. |
| `purchase_orders.action_id`, `comment_replies.action_id` | `agent_actions.id` | The owning rows live in other contexts and must survive approvals being archived. |

## Notable design choices

- **Agents never hold database credentials and never choose the tenant or user.** Those come from the server-side
  context; a model cannot point a tool at another shop.
- **Nothing that matters happens without a trace.** A write to money, stock or public content goes through
  `agent_actions` unless it is under the shop's configured limit, and every agent write has an audit row.
- **Spend is capped per shop.** `agent_runs.spend_micros` is summed per month against `tenants.agent_cap_usd`.
- **Recipes are safe to run again.** Each message carries an idempotency key built from what it is about, so the
  scheduler can call a recipe on every pass and "Run now" never sends anything twice.
