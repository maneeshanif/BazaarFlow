---
name: integration-twilio-whatsapp
description: Build or change BazaarFlow's Twilio WhatsApp sandbox integration (demo channel, PRD A-004): sandbox join, inbound webhook, signature check, sending, limits. Use before touching app/integrations for Twilio or any task in the integrations pack that mentions WhatsApp via Twilio.
---

Project-local integration skill. It records what the vendor's own documentation says so an agent does not guess
at an API from memory. It is not a replacement for reading the page when a detail matters.

## Sources (cite these; re-check when the date is more than 90 days old)

| What | URL | Read on |
|---|---|---|
| WhatsApp sandbox: join, session rules, webhook configuration, limits | https://www.twilio.com/docs/whatsapp/sandbox | 2026-10-03 |
| Webhook request signing (`X-Twilio-Signature`) | https://www.twilio.com/docs/usage/webhooks/webhooks-security | 2026-10-03 |

Caveat: both pages were read through a summarising fetch on 2026-10-03, not verbatim. Facts below marked
**(verify)** are the ones to confirm on the page before relying on them in code.

## Facts from the documentation

**Sandbox**
- All sandbox users share one number, `+14155238886`. A person joins by sending `join <sandbox code>` to it (or by
  scanning the QR code in the console). The code is specific to the sandbox, so each tester needs it. **(verify)**
- Joining opens a 24-hour customer-service window in which free-form messages are allowed; outside it only
  pre-approved templates work, and the sandbox does not allow custom templates.
- A joined session expires after three days: the user must send `join ...` again.
- Limits: one message per three seconds; messages go to joined end users only (otherwise error 63015);
  functional testing only, not load testing.
- Configure the inbound webhook ("When a message comes in") and the status callback URL in the console under
  Sandbox settings. Status values: `queued`, `failed`, `sent`, `delivered`, `read`.

**Webhook signing**
- Header `X-Twilio-Signature`; HMAC-SHA1 keyed with the account auth token over the full webhook URL plus the
  form parameters sorted alphabetically (for JSON bodies, a `bodySHA256` query parameter is appended to the URL).
- Twilio says to use the official `RequestValidator` from its Python helper library and not to write your own:
  `validator.validate(url, params, signature)`, with the exact public URL Twilio called (query string included).

## How this maps onto BazaarFlow

- Twilio is one implementation of the `ChannelAdapter` protocol (`app/integrations/channels.py`); services and
  agents never import the Twilio SDK (architecture test `test_provider_isolation`). Keep the SDK inside
  `app/integrations/`.
- Tenant resolution comes before any other processing (PRD section 3.3): the inbound webhook maps the sandbox
  number or the `To` value to `tenant_integrations.external_id`. In the shared sandbox all testers share a number,
  so route by the sender (`From`) that joined, held as a sandbox-tenant mapping, and say so in the demo notes.
- The auth token is a per-tenant credential stored encrypted in `tenant_integrations`, never in source control or
  env files for tenants (PRD section 36; `docs/operations/env-vars.md` lists the platform-level keys only).
- Verify the signature before parsing the body, with a constant-time comparison. The URL passed to the validator
  must be the public URL behind any proxy (set it from configuration, not from the request's Host header).
- Idempotency: Twilio retries; key inbound handling on `MessageSid`.
- Outbound: every send goes through the adapter with a timeout, retry with backoff and an idempotency key, and
  records an audit row; sends that change anything for the customer follow the approval rules.

## Do not

- Do not implement signature checking by hand.
- Do not assume templates are available in the sandbox, or that a user outside the 24-hour window can be messaged.
- Do not use the sandbox for load or latency testing, or present it as the production path (production uses Meta
  Embedded Signup via a Tech Provider or BSP, PRD A-004).
- Do not commit the account SID, auth token, or the sandbox join code of a real account.

## Open items for the owner (task 26)

A Twilio account with the WhatsApp sandbox enabled and the credentials in the secret manager are required before a
sandbox call can be tried. Until then nothing here has been run against the real service.
