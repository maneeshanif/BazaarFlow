# {{PROJECT_NAME}} — Agent Instructions

This repository is built with AI assistance under a strict, documented process. Read `context/` before doing anything else — it is the authoritative source for architecture, build sequencing, and conventions, and it wins over general knowledge or training-data defaults.

## Read First, In Order

{{READ_FIRST_LIST}}

## Source of Truth

{{SOURCE_OF_TRUTH}}

Never invent a business field, rule or screen that is not in the source documents — record a change request in `docs/adr/` first.

## Non-Negotiable Constraints

{{CONSTRAINTS}}

## Verification — How "Done" Is Decided

Verification is mechanical and automatic. Do not hand-pick test commands, start the app, or click through the UI to convince yourself a change works.

- **`scripts/verify.sh`** is the single definition of "verified". It runs only the lanes your changes affect ({{LANES}}) with the same commands CI runs. Default is the **fast tier** (format, lint, types, unit tests: seconds). `--slow` adds integration tests, builds, scans and drift checks; `--all` runs every lane with the slow tier; `--lane <name>` runs one; `--list` shows what would run. A fast PASS lists every slow check it deferred. Run `--slow` before you call a task finished.
- **Per edit** (Claude Code `PostToolUse` hook, `.claude/settings.json`): the edited file is formatted/lint-fixed in seconds; problems that cannot be auto-fixed are reported back immediately.
- **Per turn** (`Stop` hook): when you finish with uncommitted changes, the fast tier runs. If it fails you are not done: fix the reported failures. Never weaken, skip or delete a check to make it pass.
- **Checkpoints:** after each verified step, make a local commit on the task branch. A failed run returns to the last checkpoint instead of restarting. Never push without the developer's say.
- **Needs a human:** if verification cannot be trusted (an unreadable review verdict, a check you cannot run, a rule that conflicts with the task), stop and write the question under "Needs a human" in your reply and in `context/progress-tracker.md`. Do not guess.
- **When a run goes wrong,** name the failure class and fix the surface it lives on, per `HARNESS.md`. Then run `bash scripts/harness-check.sh`.
- **Per push** (`.githooks/pre-push`, enable once per clone with `bash scripts/install-hooks.sh`): the same lanes, for commits made outside an agent session.
- **Manual/browser checks** only for UI work, when the `review` skill calls for them.

Write tests for the behaviour the plan's **acceptance tests** name (see `architect`), plus the non-negotiable coverage in `context/code-standards.md`. Do not write tests for trivia.

**When CI fails on something `verify.sh` passed**, the fix PR carries two changes: the fix, and the check (a `verify.sh` step, an architecture test, or a lint rule) that would have caught it locally. CI should surprise us at most once per failure class.

## Skills

This repo's `skills/` directory defines the working process:

- `architect` — think through a feature before writing code; produces a plan with acceptance tests
- `imprint` — capture UI patterns into `context/ui-registry.md` after building a component
- `review` — verify a finished feature against the plan, the architecture, and production readiness
- `recover` — diagnose a failure (bug vs. polluted session vs. wrong approach) before responding to it
- `remember` — save/restore session state between sessions

## Current Status

See `context/progress-tracker.md` for the live phase/task status.
