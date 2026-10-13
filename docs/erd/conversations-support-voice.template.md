# Conversations, support and voice — ERD

> Generated from the schema by `docs/erd/generate_erd.py`. Do not hand-edit the diagram;
> edit `conversations-support-voice.template.md` for the prose.

Everything a customer says to the shop: WhatsApp threads, support tickets and phone calls. `customers` is shown only for
the link into it; it is documented in [catalog-sales-finance.md](catalog-sales-finance.md). Back to the
[overview](overview.md).

```mermaid
{{DIAGRAM}}
```

## Tables

| Table | One row is | Notes |
| --- | --- | --- |
| `conversations` | A thread with one phone number on a channel | `mode` is `ai` or `human` (who answers); `status` moves `open`, `ai_handling`, `needs_human`, `resolved`. `handoff_note` says why a person was needed. |
| `messages` | One message in or out | `direction` inbound/outbound; `sender` is customer, ai or staff. `idempotency_key` stops a message being sent twice; `wa_message_id` is the provider's id; `status` includes `send_failed`. |
| `support_tickets` | A request that needs a person | Raised by the voice agent when it cannot finish a request. |
| `voice_calls` | One phone call | Unique per (shop, provider call id), so a replayed event is ignored. Holds status, duration, cost (`spend_micros`), per-turn latency, a redacted `transcript` and `summary`. The transcript is removed after the shop's retention period. |
| `voice_settings` | The shop's voice agent settings | One row per shop: on/off, greeting, consent notice, longest call, monthly cap, the number to hand over to, and how many days transcripts are kept. |

## Unenforced relationships

| Column | Points at | Why there is no FK |
| --- | --- | --- |
| `conversations.assigned_to` | A user | History must not break when a person is removed. |
| `messages.sent_by` | A user, or the fixed id of the AI assistant | The AI is not a user. |
| `messages.wa_message_id`, `voice_calls.provider_call_id` | The provider's own ids | They live outside our database. |

## Notable design choices

- **Idempotent by design.** A replayed webhook is dropped (`webhook_events`, `voice_calls` unique key), and an outgoing
  message carries an idempotency key, so retries never double-send.
- **Handover is a state, not a flag.** `mode = 'human'` stops the AI for that thread until a person hands it back.
- **Personal data has a lifetime.** Voice transcripts are redacted on the way in and deleted after retention; a consent
  notice is recorded per call (`consent_notice`).
