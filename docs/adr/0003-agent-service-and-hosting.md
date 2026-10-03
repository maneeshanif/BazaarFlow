# ADR 0003 — Separate agent service without database access; hosting

Status: accepted by the owner, 2026-10-03
Supersedes part of: PRD §3.3 ("agents run inside the API process")

## Context
Build-plan task 28 asks for an agent service separate from the API with no database credentials. The PRD kept agents in
the API process. The owner chose to keep task 28. The reason it is worth having: agent code runs model output
(prompt-injection exposure) and should not be one bug away from the database.

## Decision
- A second deployable, `agent_service/`, runs agents. It has no database variable, imports no database layer, and its
  image contains no database code. It refuses to start if a database variable is present in its environment.
- It reaches business data only by calling the API with the caller's scoped token, so tenant isolation and role checks
  stay in one place (the API plus row-level security).
- The API calls it with a shared secret (`X-Agent-Service-Token`, constant-time compare, mandatory outside tests).
- Until the tool-call path exists (phase 1), agents keep running inside the API process; `POST /v1/run` answers 501.
- Hosting (owner): web on Vercel; API and agent service on FastAPI Cloud; database on Supabase.

## Consequences
- One more process to deploy and monitor, and one extra network hop per agent turn.
- Three architecture tests keep the isolation true: no database imports, no database variable in compose, no database
  code in the image.
- The tool catalogue's runtime enforcement (task 29) lands together with this path: the API passes a `ToolContext`-equivalent
  to the service, and each tool call goes back through the API, where the role check and the approval rule are applied.
- FastAPI Cloud's feature set (secrets, regions, background tasks, outbound connections to the Supabase pooler) has not
  been verified yet; task 21 checks its documentation before the first deploy.
