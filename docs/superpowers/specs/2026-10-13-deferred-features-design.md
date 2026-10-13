# Deferred features design brief (autonomous run, 2026-10-13)

Source of truth for scope stays PRD v0.1.2. The owner asked for the deferred workflow steps to be built while they are
away. This brief records each decision and its default so the owner can overrule it afterwards. It adds no business
field beyond PRD W-003, W-004, W-006, W-008 and §16 (Urdu/RTL).

## Decisions
| Topic | Decision |
| --- | --- |
| Legacy JSON routes | Kept mounted (owner: "keep for now"). Nothing is deleted in this run |
| Assumptions in PRD §5.4.1 | Accepted by the owner; marked confirmed in the tracker |
| Recipe failure | Retry transient failures, then a fallback, then the existing behaviour (stay on, audit row `automation.failing`, banner) |
| Impersonation | Not built (owner did not select it; needs consent and expiry rules) |
| LLM default and cap | Gemini Flash default; per-tenant cap 5 USD/month, warn 80%, stop 100% (Q-003 default, unanswered) |
| Urdu scope | Core screens: switcher, RTL, sign-in, dashboard, sales, inventory, customers, approvals (Q-004 default, unanswered) |
| Push | Branch `feat/phase-1-mvp` to origin only; no PR, no merge (unanswered, safest reading of "push the code") |

## 1. Recipe retry and fallback (W-008)
- A recipe run is attempted up to 3 times when the failure is transient (`ProviderError`, or `RecipeError(transient=True)`
  from a send that the provider did not accept). Configuration errors (no phone number, WhatsApp not connected) are not
  retried.
- When retries are exhausted and the recipe has a fallback, the fallback runs. The WhatsApp-sending recipes fall back to
  filing the same message as an approval (`send_whatsapp_message`) so the owner can send it once WhatsApp is back.
- Fallback success is a `succeeded` run whose summary says WhatsApp was unavailable; it does not count as a failure.
- Fallback failure (or no fallback) is the current behaviour: `consecutive_failures += 1`, a `failed` run, and at 3 the
  `automation.failing` audit row and banner.
- Acceptance: recipe fails twice then succeeds -> `succeeded`, 0 failures; send keeps failing -> approval filed, run
  `succeeded` with the fallback summary; fallback also fails -> `failed`, counter 1; config error is not retried.

## 2. Draft purchase order (W-006 step 3)
- New tables `purchase_orders` and `purchase_order_items` (tenant-scoped, RLS, `NUMERIC(14,2)`, soft delete off:
  append-only status history through the audit log). Status: `drafted -> approved -> sent`, `cancelled`.
- The low-stock recipe stores one draft PO per vendor alongside the vendor-message approval; approving the message marks
  the PO `sent`. A vendor without a phone leaves the PO `drafted` with a warning (W-006 failure path).
- Owner can list and open POs and cancel a draft. No receiving/stock-in flow (not in the PRD).

## 3. Customer order drafts (W-003 step 2-3)
- The customer agent gains one tool, `draft_order(product, qty)`, that files an approval (never posts). The order is
  posted by the existing `post_order` executor on approval; the customer receives a confirmation after approval.
- Anything else still ends with `HANDOVER`. Stock is re-validated at approval time.

## 4. Facebook comment replies (W-004 step 4)
- Table `comment_replies`: comment id (unique per tenant), post, author, text, proposed reply, status
  `proposed -> approved -> posted | skipped | failed`.
- The scheduler pulls comments of recently published posts, the marketing writer proposes a reply, and the owner approves
  it (or it posts at once when the shop has auto-reply on). Posting goes through `reply_to_comment` with an idempotency key.

## 5. Urdu / RTL (§16)
- Small dictionary-based `useT` with `en` and `ur`, a language switcher stored in a cookie and the user profile, `dir`
  and `lang` set on `<html>`, logical CSS (`ms-`, `me-`, `ps-`, `pe-`) on the shared shell. Missing keys fall back to
  English. Core screens only.

## Acceptance tests (one line each)
- Unit: recipe retry succeeds on the third attempt; fallback files an approval; fallback failure is counted.
- Integration: low-stock recipe creates a draft PO per vendor and links it to the approval; PO of another tenant is not
  readable (RLS); approving the message marks the PO sent.
- Integration: `draft_order` creates a pending approval and no order; approving posts the order once; insufficient stock
  is reported, not posted.
- Integration: comments are stored once (idempotent), a reply is proposed, approving posts it with the right key; a
  tenant cannot read another tenant's comments; an audit row is written.
- UI: switching to Urdu sets `dir="rtl"`; a missing key falls back to English.

## Needs a human (carried)
No live Facebook, Twilio or Gemini call has been made; all four features are proven against recorded responses and the
scripted model only.
