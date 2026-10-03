#!/usr/bin/env bash
# scripts/verify.sh — the single definition of "this change is verified".
#
# CI calls these same lanes (see .github/workflows/*.yml), so "passes
# locally" and "passes CI" mean the same thing. Agents and humans run this
# instead of hand-picking commands or clicking through the app.
#
#   scripts/verify.sh                 # FAST tier, lanes affected by your changes vs origin/main (default)
#   scripts/verify.sh --slow          # also run the slow checks (integration tests, builds, scans, E2E)
#   scripts/verify.sh --all           # every lane, slow tier included (before a big PR, or nightly)
#   scripts/verify.sh --lane <name>   # one lane explicitly (repeatable)
#   scripts/verify.sh --base <ref>    # diff against another ref
#   scripts/verify.sh --list          # print the lanes that would run, then exit
#
# Tiers: the fast tier is what the Stop hook runs after every turn (seconds, not minutes).
# The slow tier runs in CI (CI=true selects it automatically), with --slow/--all, and in /review.
# VERIFY_TIER=fast|slow overrides the default. A fast-tier PASS lists every slow check it deferred.
#
# Lanes: api api-db web infra
# Exit code is non-zero if any lane fails; every selected lane still runs so
# one report shows everything that is broken.
#
# GENERATED from Honey's Spec Harness lane snippets. Add or change lanes here
# freely afterwards; keep the workflows in .github/workflows/ in sync.

set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE="origin/main"
MODE="changed"
LIST_ONLY=0
TIER="${VERIFY_TIER:-}"
EXPLICIT_LANES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --all) MODE="all" ;;
    --changed) MODE="changed" ;;
    --lane) EXPLICIT_LANES+=("$2"); MODE="explicit"; shift ;;
    --base) BASE="$2"; shift ;;
    --slow) TIER="slow" ;;
    --fast) TIER="fast" ;;
    --list) LIST_ONLY=1 ;;
    -h|--help) sed -n '2,/^$/p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$TIER" ]; then
  if [ "$MODE" = "all" ] || [ "${CI:-}" = "true" ]; then TIER="slow"; else TIER="fast"; fi
fi
case "$TIER" in fast|slow) ;; *) echo "VERIFY_TIER must be fast or slow, got: $TIER" >&2; exit 2 ;; esac

# ---------------------------------------------------------------------------
# Changed files: committed on this branch + staged + unstaged + untracked.
# ---------------------------------------------------------------------------
changed_files() {
  local merge_base
  merge_base="$(git merge-base HEAD "$BASE" 2>/dev/null || git rev-parse HEAD)"
  {
    git diff --name-only "$merge_base"...HEAD
    git diff --name-only --cached
    git diff --name-only
    git ls-files --others --exclude-standard
  } | sort -u
}

CHANGED=""
if [ "$MODE" = "changed" ]; then
  CHANGED="$(changed_files)"
fi

touched() { # touched <extended-regex>
  [ -n "$CHANGED" ] && echo "$CHANGED" | grep -Eq "$1"
}

declare -A RUN=()
select_lane() { RUN["$1"]=1; }

case "$MODE" in
  all) for l in api api-db web infra; do select_lane "$l"; done ;;
  explicit)
    for l in "${EXPLICIT_LANES[@]}"; do
      case "$l" in
        api|api-db|web|infra) select_lane "$l" ;;
        *) echo "Unknown lane: $l" >&2; exit 2 ;;
      esac
    done ;;
  changed)
    touched '^./' && select_lane api
    touched '^./' && select_lane api-db
    touched '^frontend/' && select_lane web
    touched '^package(-lock)?\.json$' && select_lane web
    touched '^./|^\.github/workflows/|^scripts/' && select_lane infra
    ;;
esac

ORDER=(api api-db web infra)
SELECTED=()
for l in "${ORDER[@]}"; do [ -n "${RUN[$l]:-}" ] && SELECTED+=("$l"); done

if [ ${#SELECTED[@]} -eq 0 ]; then
  echo "verify: nothing to verify (no changes vs $BASE)."
  exit 0
fi

echo "verify: lanes -> ${SELECTED[*]}  (tier: $TIER)"
[ "$LIST_ONLY" = 1 ] && exit 0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FAILED=()
SKIPPED=()
CURRENT_LANE=""

step() { # step <label> <command...> — runs in a subshell, records failure and duration
  local label="$1" t0="$SECONDS"; shift
  echo ""
  echo "── $label"
  if ! ( "$@" ); then
    echo "✗ $label"
    echo "  next: read the output above, fix the cause, then re-run only this lane: bash scripts/verify.sh --lane ${CURRENT_LANE:-<lane>}"
    echo "[time] $((SECONDS - t0))s $label"
    FAILED+=("$label")
    return 1
  fi
  echo "[time] $((SECONDS - t0))s $label"
}

slow_step() { # slow_step <label> <command...> — runs only in the slow tier
  local label="$1"
  if [ "$TIER" = "slow" ]; then
    step "$@"
  else
    echo "[slow-deferred] $label — run: bash scripts/verify.sh --slow --lane ${CURRENT_LANE:-<lane>}"
  fi
}

have() { command -v "$1" > /dev/null 2>&1; }
host_path() { if have cygpath; then cygpath -m "$1"; else echo "$1"; fi; }
docker_up() { have docker && docker info > /dev/null 2>&1; }

# ---------------------------------------------------------------------------
# Lanes — each mirrors a CI job. Keep them in sync with the workflow that
# calls them; that sync is the whole point of this file.
# ---------------------------------------------------------------------------
lane_api() {
  have uv || { echo "⚠ api: uv not installed — SKIPPED."; SKIPPED+=("api"); return 0; }
  cd . || return 1
  step "api: uv sync" uv sync --locked --quiet || return
  step "api: ruff" uv run ruff check .
  step "api: mypy" uv run mypy .
  step "api: pytest" uv run pytest -q
  slow_step "api: dependency audit" uv run pip-audit --progress-spinner off --skip-editable
  # Real-Postgres tests (RLS, auth, schema rules) need Docker; CI always has it.
  if docker_up; then
    step "api: postgres tests (RLS, auth, schema rules)" uv run pytest -m pg -q
  else
    echo "⚠ api: Docker not running — Postgres/RLS tests SKIPPED (CI will run them)."
    SKIPPED+=("api: postgres tests")
  fi
}

# Migrations must (1) apply cleanly to an empty database, (2) match the SQLAlchemy models (`alembic check`), (3) round-trip (downgrade base, upgrade head).
# Uses $URL_ENV when it is already set (CI service container); otherwise starts a throwaway container if Docker is running.
api_db_migrations() {
  set -e
  local cid="" port=55432 url
  if [ -n "${DATABASE_URL:-}" ]; then
    url="${DATABASE_URL}"
  else
    cid="$(docker run -d --rm -p "$port:5432" -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=verify postgres:16)"
    trap 'docker stop "$cid" > /dev/null 2>&1 || true' RETURN
    for _ in $(seq 1 40); do
      docker exec "$cid" pg_isready -U postgres -d verify > /dev/null 2>&1 && break
      sleep 1
    done
    url="postgresql+psycopg://postgres:verify@localhost:$port/verify"
  fi
  export DATABASE_URL="$url"
  uv run alembic upgrade head
  uv run alembic check
  uv run alembic downgrade base
  uv run alembic upgrade head
  echo "Migrations apply, match the models, and round-trip."
}

lane_api_db() {
  have uv || { echo "⚠ api-db: uv not installed — SKIPPED."; SKIPPED+=("api-db"); return 0; }
  cd . || return 1
  if [ "$TIER" != "slow" ]; then
    slow_step "api-db: migrations apply, match models, round-trip" true
    return 0
  fi
  if [ -z "${DATABASE_URL:-}" ] && ! docker_up; then
    echo "⚠ api-db: no DATABASE_URL and Docker not running — migration check SKIPPED (CI will run it)."
    SKIPPED+=("api-db")
    return 0
  fi
  step "api-db: uv sync" uv sync --locked --quiet || return
  step "api-db: migrations apply, match models, round-trip" api_db_migrations
}

lane_web() {
  have npm || { echo "⚠ web: npm not installed — SKIPPED."; SKIPPED+=("web"); return 0; }
  [ -d node_modules ] || [ -d frontend/node_modules ] || step "web: install" npm ci || return
  cd frontend || return 1
  has_script() { node -e 'process.exit(require("./package.json").scripts?.[process.argv[1]] ? 0 : 1)' "$1"; }
  has_script lint && step "web: lint" npm run --silent lint
  has_script typecheck && step "web: typecheck" npm run --silent typecheck
  [ -f tsconfig.json ] && ! has_script typecheck && step "web: tsc" npx tsc --noEmit
  has_script format:check && step "web: format (new code)" npm run --silent format:check
  has_script check:tokens && step "web: design tokens (no hard-coded colour, type or spacing)" npm run --silent check:tokens
  has_script test && step "web: test" npm run --silent test
  slow_step "web: dependency audit (reviewed allow-list)" npm run --silent check:audit
  has_script build && slow_step "web: build" npm run --silent build
  # real-browser responsive check (needs the build above and Chromium: `npx playwright install chromium`)
  has_script test:e2e && slow_step "web: e2e shell (no horizontal scroll at 360-1440 px)" npm run --silent test:e2e
  return 0
}

lane_infra() {
  if [ -f ./docker-compose.yml ] && docker_up; then
    step "infra: compose config" bash -c 'cd . && docker compose -f docker-compose.yml config --quiet'
  else
    echo "⚠ infra: no compose file or Docker not running — compose check SKIPPED."
    SKIPPED+=("infra")
  fi
  if [ -d .github/workflows ] && docker_up; then
    # MSYS_NO_PATHCONV: stop Git Bash on Windows rewriting /repo into a host path.
    slow_step "infra: actionlint" env MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$ROOT"):/repo" -w /repo rhysd/actionlint:1.7.7 -color
  fi
  if docker_up; then
    # Whole history, minus the reviewed baseline: a new secret anywhere fails. Same scan as CI (security.yml).
    slow_step "infra: secret scan (gitleaks, baselined)" env MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$ROOT"):/repo" zricethezav/gitleaks:v8.30.1 detect --source /repo --redact --no-banner --baseline-path /repo/.gitleaks-baseline.json
  fi
  step "infra: verify.sh syntax" bash -n scripts/verify.sh
}



RUN_LOG="$(mktemp "${TMPDIR:-/tmp}/verify-run.XXXXXX")"  # per run, so concurrent runs cannot mix their summaries
for lane in "${SELECTED[@]}"; do
  CURRENT_LANE="$lane"
  echo ""
  echo "════ lane: $lane"
  # Failures are reported from the "✗" markers in the log, below.
  # A lane that bails out early must never look like a pass.
  ( cd "$ROOT" && "lane_${lane//-/_}" ) || echo "✗ lane $lane did not complete cleanly (see output above)"
done 2>&1 | tee "$RUN_LOG"

echo ""
echo "════ summary"
LOG="$RUN_LOG"
cp "$LOG" "${TMPDIR:-/tmp}/verify-last.log" 2>/dev/null || true
trap 'rm -f "$RUN_LOG"' EXIT
FAILS="$(grep -aE '^✗ ' "$LOG" || true)"
SKIPS="$(grep -aE '^⚠ ' "$LOG" || true)"
DEFERRED="$(grep -aE '^\[slow-deferred\] ' "$LOG" || true)"
[ -n "$SKIPS" ] && echo "$SKIPS"
echo "slowest steps:"
grep -aE '^\[time\] ' "$LOG" | sed 's/^\[time\] //' | sort -rn | head -5 | sed 's/^/  /'
if [ -n "$FAILS" ]; then
  echo "$FAILS"
  echo "verify: FAILED"
  exit 1
fi
if [ -n "$DEFERRED" ]; then
  echo "$DEFERRED"
  echo "verify: PASSED, fast tier (${SELECTED[*]}) — $(echo "$DEFERRED" | wc -l | tr -d ' ') slow check(s) deferred; run 'bash scripts/verify.sh --slow' before merging"
else
  echo "verify: PASSED (${SELECTED[*]})"
fi
