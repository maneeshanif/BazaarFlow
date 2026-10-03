# HARNESS.md — the ratchet

The model learns nothing between runs. This file is where the project learns.

**Rule:** when the agent makes a mistake, do not only fix the work. Name the failure class, change the surface that class lives on so the mistake becomes impossible, record it below, and re-run `bash scripts/harness-check.sh`. A harness change you did not re-check is a guess.

## The four failure classes

| Class | The sign | Fix lives in |
| --- | --- | --- |
| **Context** | It did not know: wrong convention, missed constraint, reinvented decision | `AGENTS.md`, a skill, a tool description |
| **Constraint** | It did something it should never have been able to do | `.claude/settings.json` deny/ask rules, sandbox, branch protection |
| **Verification** | Bad work was called done: tests not run, claim unchecked | a `verify.sh` step, a hook, required CI, the typed `/review` verdict |
| **Planning** | Right pieces, wrong order or size: wandering, bundled changes | a smaller task in `context/build-plan.md`, a step cap, a split |

Two failures with the same shape should be impossible. If you see a second, the first was classified wrong.

## Log

| Date | What went wrong (one sentence) | Class | The fix, and the surface it went on |
| --- | --- | --- | --- |
| | | | |
| 2026-10-03 | `verify.sh --slow` ran `alembic downgrade base` against the owner's real Supabase project (data wiped) because `.env` DATABASE_URL_MIGRATIONS overrides the throwaway DATABASE_URL the lane sets, and a failed `upgrade head` did not stop the following destructive steps (`set -e` is ignored in conditionals) | Constraint | The migration step pins both URL variables to the throwaway container, refuses any non-local URL before the downgrade, and chains every alembic command with `|| return 1`; `tests/architecture/test_ci_workflows.py` fails if any of those is removed |
