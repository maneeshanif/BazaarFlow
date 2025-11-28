# How to Implement VAPI in This MedFlow Project

This guide walks you through **how VAPI is implemented in this repo** and how to **recreate or extend** the same pattern in your own environments.

It assumes you want:
- Web-based voice calls from the browser using the **VAPI Web SDK**.
- Production-style assistants (FAQ, scheduler, reminder) managed via the **VAPI HTTP API**.
- **Webhook-based tools** (function calls) for appointment workflows.
- Resilient, interruption-aware UX with a dedicated **test calls UI**.

---

## 1. Concepts and Roles

In this codebase, VAPI is used in three main ways:

1. **Server-side assistant management**
   - File: `app/scripts/vapi-client.js`
   - Purpose: Define assistant templates and talk to the VAPI REST API (create/list/update assistants, create calls, etc.).

2. **Webhook for function calls**
   - File: `app/api/vapi-webhook/route.js`
   - Purpose: Receive VAPI function calls (e.g., `schedule_appointment`) and run backend logic, then return text the assistant can speak.

3. **Browser voice calls (Web SDK)**
   - File: `app/src/app/test-calls/page.tsx`
   - Purpose: Next.js page that loads the `@vapi-ai/web` SDK, starts/stops calls, handles reconnection, speech interruption, and displays transcripts.

Config helpers live in `app/config/vapi-config.js`, and there is also a TypeScript-flavored VAPI client in `app/src/lib/vapi.ts` used in other parts of the app.

---

## 2. Environment Variables

Set these in your `.env.local` (for the Next app) and `.env` (for Node scripts) as needed:

Required for all VAPI use:
- `VAPI_API_KEY` — **private server key**, used by Node scripts and backend.
- `NEXT_PUBLIC_VAPI_PUBLIC_KEY` — **public web key**, used by the browser Web SDK.

For webhooks and assistants:
- `VAPI_WEBHOOK_URL` — deployed URL for `api/vapi-webhook`, e.g. `https://your-domain.com/api/vapi-webhook`.
- `VAPI_WEBHOOK_SECRET` — optional secret for securing calls from VAPI to your webhook.

For specific assistants (used by the test calls page):
- `NEXT_PUBLIC_VAPI_FAQ_ASSISTANT_ID`
- `NEXT_PUBLIC_VAPI_SCHEDULER_ASSISTANT_ID`
- `NEXT_PUBLIC_VAPI_REMINDER_ASSISTANT_ID`

You obtain these assistant IDs after creating assistants in VAPI (see next section).

---

## 3. Assistant Management with the VAPI HTTP API

### 3.1 VAPI client (Node, used by scripts)

File: `app/scripts/vapi-client.js`

Key points:
- Wraps the VAPI HTTP API with a small `VapiClient` class.
- Base URL: `https://api.vapi.ai`.
- Always sends `Authorization: Bearer ${VAPI_API_KEY}` and `Content-Type: application/json`.

Main methods:
- `createAssistant(assistantData, webhookUrl?)`
- `listAssistants()` / `getAssistant(id)` / `updateAssistant(id, assistantData)` / `deleteAssistant(id)`
- `createCall(callRequest)` / `getCall(id)` / `listCalls()`

`createAssistant` automatically injects webhook config when you provide `webhookUrl` and the assistant defines `functions`:

- `serverUrl: webhookUrl`
- `serverUrlSecret: process.env.VAPI_WEBHOOK_SECRET` (if defined)

This is what wires the assistant to your `api/vapi-webhook` route for function calls.

### 3.2 Assistant templates

Also in `app/scripts/vapi-client.js`, the constant `ASSISTANT_TEMPLATES` defines three production-style assistants:

- `APPOINTMENT_SCHEDULER`
- `APPOINTMENT_REMINDER`
- `FAQ_ASSISTANT`

Each template includes:
- `name`
- `model` (OpenAI GPT-4, temp, max tokens, system message)
- `voice` (ElevenLabs configuration)
- `firstMessage`
- `startSpeakingPlan` / `stopSpeakingPlan` (speech timing + interruption behavior)
- `backgroundSound` and `backgroundDenoisingEnabled`
- `functions` (JSON-schema-like tools the assistant can call)
- `recordingEnabled`, `endCallMessage`, duration limits

### 3.3 Function tools (appointment workflows)

Examples:

- Scheduler:
  - `schedule_appointment`
  - `reschedule_appointment`
  - `cancel_appointment`
- Reminder:
  - `confirm_appointment`
  - `request_reschedule`
- FAQ:
  - `schedule_appointment_request`
  - `transfer_to_staff`
  - `provide_office_info`

Each function has a `parameters` object with:
- `type: 'object'`
- `properties: { ... }` describing each argument.
- `required: [...]` listing required keys.

These names and schemas must match the webhook handlers in `app/api/vapi-webhook/route.js`.

---

## 4. Webhook: Handling VAPI Function Calls

File: `app/api/vapi-webhook/route.js`

### 4.1 Request shape

VAPI sends JSON bodies containing at least:
- `message.type`
- `message.functionCall` (if `type === 'function-call'`)
- `call` (metadata about the call)

The handler:

1. Parses the body: `const body = await request.json()`.
2. Extracts `{ message: { type, functionCall }, call }`.
3. If `type !== 'function-call'`, returns a no-op success.
4. Routes based on `functionCall.name` to one of the handler functions.
5. Returns:
   - `{ success: true, result, message: result.responseMessage || null }`.

That `message` field is what VAPI can feed back to the assistant to **speak to the user**.

### 4.2 Handlers implemented

Each handler is async, logs the incoming params, and returns a structured object including a user-facing `responseMessage`:

- `handleScheduleAppointment(params, call)`
- `handleRescheduleAppointment(params, call)`
- `handleCancelAppointment(params, call)`
- `handleConfirmAppointment(params, call)`
- `handleRequestReschedule(params, call)`
- `handleScheduleAppointmentRequest(params, call)`
- `handleTransferToStaff(params, call)`
- `handleProvideOfficeInfo(params, call)`

All handlers are currently **mock implementations**:
- They simulate DB writes and logic by logging.
- They return a friendly confirmation message.

You can replace the `TODO` comments with real DB queries or external API calls.

### 4.3 Error handling

If anything throws:
- Logs the error.
- Returns `{ success: false, error: 'Internal server error', message: 'I apologize, but I encountered an error...'} (HTTP 500)`.

VAPI will pass `message` back to the assistant, so the user hears a graceful error.

---

## 5. Configuration Helpers

File: `app/config/vapi-config.js`

This file centralizes **defaults** and helper messages.

### 5.1 `VAPI_CONFIG`

Contains:
- `WEBHOOK_URL` — from `process.env.VAPI_WEBHOOK_URL` or a default placeholder.
- `API_BASE_URL` — `https://api.vapi.ai`.
- `WEBHOOK_SECRET` — optional secret.
- `FUNCTION_TIMEOUT_MS` — default 10s.
- `DEFAULT_SETTINGS` — recording, background noise reduction, and generic speech/voice defaults (`startSpeakingPlan`, `stopSpeakingPlan`, `voice`).

### 5.2 `ASSISTANT_CONFIG`

Gives per-assistant defaults:
- `SCHEDULER`, `REMINDER`, `FAQ`
- Each includes `maxDurationSeconds` and which functions they expect.

### 5.3 Message + validation helpers

- `ERROR_MESSAGES` and `SUCCESS_MESSAGES` — common templated strings for appointment flows.
- `VALIDATORS` — small helpers for phone numbers, appointment dates, and patient name length.

You can import these helpers into webhook handlers or scripts to avoid duplicating logic.

---

## 6. Browser Integration: VAPI Web SDK

File: `app/src/app/test-calls/page.tsx`

This is the main **test harness UI** for making web calls.

### 6.1 High-level behavior

- Imports `@vapi-ai/web` dynamically in a `useEffect`.
- Initializes `new Vapi(publicKey)` using `NEXT_PUBLIC_VAPI_PUBLIC_KEY`.
- Sets up event listeners for:
  - `call-start` / `call-end`
  - `message`
  - `error`
  - `speech-start` / `speech-end`
  - `assistant-speech-start` / `assistant-speech-end`
  - `speech-interrupted`
  - `volume-level`
- Tracks:
  - Which assistant is selected (`faq`, `scheduler`, `reminder`).
  - Call state: active, connecting, ended, reconnecting.
  - Network status (online/offline).
  - Heartbeat timestamp to detect silent failures.
  - Call duration.
  - Whether the user or assistant is currently speaking.
  - Current partial transcript.
  - Conversation log.

### 6.2 Assistant selection

The page defines an `assistants` map:
- Keys: `faq`, `scheduler`, `reminder`.
- Each has:
  - `id`: from the `NEXT_PUBLIC_VAPI_*_ASSISTANT_ID` env vars with a fallback hard-coded UUID.
  - `name`, `description`, `icon`, `color` for UI.

The user picks an assistant using a `<Select>`; the selected entry determines which assistant ID is passed to `vapiInstance.start(assistantId)`.

### 6.3 Call control

Core functions:

- `startCall`:
  - Ensures `vapiInstance` exists.
  - If a call is already active, calls `vapiInstance.stop()` to end.
  - If not, sets `connectionStatus` to `connecting`, clears old conversation, and calls `vapiInstance.start(assistantId)`.

- `toggleMute`:
  - Toggles `vapiInstance.mute()` / `vapiInstance.unmute()`.
  - Updates `isMuted` flag.

### 6.4 Resilience and reconnection

The page layers in several resilience features:

1. **Network listeners**
   - Listens to `window.online` and `window.offline` events.
   - Tracks `networkStatus` (`online`/`offline`).
   - On reconnection, optionally calls `attemptReconnection()`.

2. **Heartbeat**
   - Stores `lastHeartbeat` timestamp, updated whenever a VAPI message arrives.
   - Every 5s, a timer checks how long since the last heartbeat.
     - > 30s: log a warning message to the conversation.
     - > 60s: attempts reconnection.

3. **Reconnection logic**
   - `attemptReconnection`:
     - Max 3 attempts.
     - If offline, waits and logs a message.
     - Otherwise:
       - Sets status to `reconnecting`.
       - Uses a backoff (`await` a short delay based on attempt count).
       - Calls `vapiInstance.start(assistantId)` again.
       - On success, logs a system message and resets state.

4. **Error-based retries**
   - In the `message` and `error` handlers, if an error includes words like `network`, `connection`, or `timeout`, `attemptReconnection()` is triggered.

### 6.5 Speech interruption and UX

The test page demonstrates **how to build a natural, interruptible conversation** using the event stream and assistant speech config.

Key patterns:

- Partial transcripts (`transcriptType === 'partial'`):
  - Stored in `currentPartialTranscript` for a live "typing" effect.
  - If `message.role === 'user'` *and* `isSpeaking === true`, it's treated as a user interruption; the page:
    - Sets `isSpeaking` to `false`.
    - Sets `isListening` to `true`.
    - Logs a system event saying the AI was interrupted.

- Speech events:
  - `speech-start` / `speech-end` control `isListening`.
  - `assistant-speech-start` / `assistant-speech-end` control `isSpeaking`.
  - `speech-interrupted` is logged explicitly as an interruption.

- Volume levels:
  - `volume-level` updates `speechLevel` for a simple visual bar.

The UI shows:
- Connection status and call duration.
- Live conversation transcript with roles (user/assistant/system) and timestamps.
- A small debug panel listing recent speech events and current speech state.

---

## 7. Putting It All Together: End-to-End Flow

1. You create assistants in VAPI using the `VapiClient` and `ASSISTANT_TEMPLATES` from `app/scripts/vapi-client.js` (or via the VAPI dashboard).
2. Those assistants are configured with `serverUrl` and `serverUrlSecret` pointing to your `VAPI_WEBHOOK_URL`.
3. When a call runs (from web or phone), and the assistant calls a tool (e.g., `schedule_appointment`), VAPI POSTs to `api/vapi-webhook`.
4. `app/api/vapi-webhook/route.js` routes that function call to a specific handler and returns a `responseMessage`.
5. VAPI uses `responseMessage` in the conversation, and the user hears the confirmation.
6. On the web, users navigate to `/test-calls`, pick an assistant, and start a call using the VAPI Web SDK.
7. The client monitors connection, retries as needed, and reacts to speech events to give a natural, interruption-aware UX.

---

## 8. How to Extend This Setup

To add **another assistant** (e.g., billing assistant):

1. Define a new template in `app/scripts/vapi-client.js` under `ASSISTANT_TEMPLATES`.
2. Add any tools (functions) it should call.
3. Implement matching handlers in `app/api/vapi-webhook/route.js` (extend the switch statement and add a function).
4. Create the assistant via a script using `VapiClient.createAssistant(...)` and note its ID.
5. (Optional) Add the assistant to the `assistants` map in `app/src/app/test-calls/page.tsx` to test it from the web.
6. Add `NEXT_PUBLIC_VAPI_<NAME>_ASSISTANT_ID` to your env.

To hook into a real database or EHR:
- Replace the `TODO` sections in webhook handlers with actual DB queries or external API calls.
- Use the existing `params` object from the tool call as your input payload.
- Return a `responseMessage` that clearly describes what was done or what will happen next.

---

## 9. Quick Checklist

Use this checklist to implement or re-implement VAPI here:

1. **Env setup**
   - [ ] Set `VAPI_API_KEY` and `NEXT_PUBLIC_VAPI_PUBLIC_KEY`.
   - [ ] Set `VAPI_WEBHOOK_URL` and (optionally) `VAPI_WEBHOOK_SECRET`.
2. **Assistants**
   - [ ] Define/update templates in `app/scripts/vapi-client.js`.
   - [ ] Create assistants in VAPI and capture their IDs.
   - [ ] Store IDs in `NEXT_PUBLIC_VAPI_*_ASSISTANT_ID`.
3. **Webhook**
   - [ ] Ensure `app/api/vapi-webhook/route.js` is deployed and reachable at `VAPI_WEBHOOK_URL`.
   - [ ] Implement or adapt handlers for all functions used in your templates.
4. **Web client**
   - [ ] Confirm `app/src/app/test-calls/page.tsx` loads without errors.
   - [ ] Verify calls connect, speech is audible, and interruption behaves as expected.
5. **Domain logic**
   - [ ] Swap mock handlers for real appointment / patient / billing logic.

Once all these boxes are checked, you have a complete, production-ready VAPI integration similar to the one in this MedFlow project.
