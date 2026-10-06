# Provider fixtures

Responses the adapter tests replay through `httpx.MockTransport`. Each file follows the shape in the provider's own
documentation (Twilio Messages API and error codes, Meta Graph API, Pexels API); no live call produced them, and a
sandbox run by the owner (task 26) may replace any of them with a real capture. Account ids, tokens and phone numbers
are made up.
