# Conversations, support and voice — ERD

> Generated from the schema by `docs/erd/generate_erd.py`. Do not hand-edit the diagram;
> edit `conversations-support-voice.template.md` for the prose.

Everything a customer says to the shop: WhatsApp threads, support tickets and phone calls. `customers` is shown only for
the link into it; it is documented in [catalog-sales-finance.md](catalog-sales-finance.md). Back to the
[overview](overview.md).

```mermaid
erDiagram
    %% Conversations, support and voice
    conversations {
        uuid id PK
        uuid tenant_id FK
        uuid customer_id FK
        varchar_20 channel
        varchar_30 phone
        varchar_120 contact_name
        varchar_20 status
        varchar_10 mode
        uuid assigned_to
        varchar_500 handoff_note
        timestamptz last_message_at
        varchar_160 last_message_text
        timestamptz created_at
        timestamptz updated_at
    }
    messages {
        uuid id PK
        uuid tenant_id FK
        uuid conversation_id FK
        varchar_10 sender
        uuid sent_by
        varchar_80 idempotency_key
        varchar_200 error
        uuid customer_id FK
        varchar_30 phone
        messagedirection direction
        text text
        varchar_50 status
        varchar_255 wa_message_id
        timestamptz created_at
        timestamptz updated_at
    }
    support_tickets {
        uuid id PK
        uuid tenant_id FK
        varchar_255 contact
        varchar_500 issue_summary
        text details
        varchar_50 preferred_channel
        varchar_50 status
        timestamptz created_at
        timestamptz updated_at
    }
    voice_calls {
        uuid id PK
        uuid tenant_id FK
        varchar_80 provider_call_id
        varchar_12 status
        varchar_12 caller_hint
        timestamptz started_at
        timestamptz ended_at
        integer duration_seconds
        varchar_80 ended_reason
        bigint spend_micros
        json turns_json
        boolean escalated
        varchar_500 handoff_note
        varchar_300 consent_notice
        text summary
        text transcript
        uuid ticket_id FK
        timestamptz created_at
        timestamptz updated_at
    }
    voice_settings {
        uuid id PK
        uuid tenant_id FK
        boolean enabled
        varchar_200 greeting
        varchar_300 consent_notice
        integer max_call_seconds
        numeric_8_2 monthly_cap_usd
        varchar_30 handoff_phone
        integer retention_days
        timestamptz created_at
        timestamptz updated_at
    }
    %% Referenced
    customers {
        uuid id PK
        uuid tenant_id FK
        varchar_30 phone
        varchar_255 name
        varchar_255 email
        varchar_512 address
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    customers ||--o{ conversations : "customer_id"
    conversations ||--o{ messages : "conversation_id"
    customers ||--o{ messages : "customer_id"
    support_tickets ||--o{ voice_calls : "ticket_id"
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
