# Connecting WhatsApp (Twilio sandbox) and Facebook

How a shop connects its channels (PRD F-018, F-003), what the platform does with each credential, and what the owner of
BazaarFlow still has to do by hand. Everything below is built and tested against recorded provider responses; **no live
provider call has been made yet** (task 26 is the owner's).

## What is stored and how

- One row per shop and provider in `tenant_integrations`. The credentials are one JSON object encrypted with
  `INTEGRATIONS_ENCRYPTION_KEY` (Fernet; several keys separated by commas allow rotation: the first encrypts, all decrypt).
- The API never returns a credential. The integrations page shows the status, the last error and the last four
  characters of the saved token so an owner can tell which one is saved.
- `external_id` routes an inbound webhook to its shop and is unique across shops:
  - `whatsapp_twilio`: the **Twilio Account SID** (every Twilio webhook carries it; the sandbox number is shared by every
    tester, so it cannot route).
  - `facebook`: the **Page id**.
- Status: `pending` -> `connected` | `error` (the provider refused the credential, or is down) | `revoked` (the owner
  disconnected). An `error` caused by a refused credential means "reconnect": the page tells the owner to paste a new token.

## Twilio WhatsApp sandbox (per shop)

1. In the shop's own Twilio console, open **Messaging -> Try it out -> Send a WhatsApp message** and join the sandbox from the
   phone that will test (send `join <code>` to `+1 415 523 8886`; a join lasts three days).
2. In BazaarFlow open **Settings -> Integrations -> WhatsApp (Twilio)** and paste the Account SID and Auth Token. BazaarFlow
   checks them with a read-only account lookup before saving.
3. Copy the **webhook URL** shown on that page into Twilio's **Sandbox settings -> When a message comes in** (method POST).
   The URL is `PUBLIC_BASE_URL` + `/api/v1/webhooks/twilio`; `PUBLIC_BASE_URL` must be the exact public address Twilio
   calls (the signature covers it), with no proxy rewriting.
4. Send a message from the joined phone: it appears in the inbox. Outbound messages work only inside the 24-hour window
   that opens when the customer writes; the sandbox cannot send templates.

## Facebook Page (per shop)

1. The owner creates a Meta app and generates a **Page access token** for the page (long-lived: exchange a user token with
   `fb_exchange_token`; a page token made from a long-lived user token does not expire).
2. In **Settings -> Integrations -> Facebook** paste the Page id and the token. BazaarFlow checks that the token belongs to
   that page before saving.
3. If Facebook ever answers "token expired" (error code 190), the integration moves to `error`, scheduled posts pause, the
   owner sees a banner and an audit row is written. Pasting a new token resumes the schedule.

## Failure behaviour (task 62)

| What fails | What the shop sees | What the platform does |
| --- | --- | --- |
| A provider times out or returns 5xx | the message stays `send_failed` in the inbox with a Retry button | 3 attempts with growing delays, then an audit row `integration.degraded` and an error log line |
| A provider refuses the credential | integration status `error` with "reconnect" | no retries, scheduled posts pause, audit row, error log line |
| A webhook arrives with a bad signature | nothing | rejected with 403, no data stored |
| The same webhook arrives twice | nothing | the second is acknowledged and ignored (`webhook_events`) |

The error log lines carry `provider`, `kind` and `status` only, never a token. There is no email or SMS vendor in the PRD, so
"alert" means an audit row, an error log line (picked up by error reporting) and the banner on the integrations page.

## Still needs the owner

- Create or confirm the Twilio sandbox account and the Meta app, and add the first real credentials (task 26).
- Set `INTEGRATIONS_ENCRYPTION_KEY` (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`),
  `PUBLIC_BASE_URL`, and `PEXELS_API_KEY` on the API host. `.env.example` is protected from the assistant: copy
  `docs/operations/env.example.proposed` over it.
- Run one real inbound and outbound message, and one real post, to replace the recorded responses in
  `tests/fixtures/providers/` with captured ones.
