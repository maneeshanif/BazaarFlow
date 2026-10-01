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
# Lanes: @@LANE_NAMES@@
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
  all) for l in @@ALL_LANES@@; do select_lane "$l"; done ;;
  explicit)
    for l in "${EXPLICIT_LANES[@]}"; do
      case "$l" in
        @@EXPLICIT_CASE@@) select_lane "$l" ;;
        *) echo "Unknown lane: $l" >&2; exit 2 ;;
      esac
    done ;;
  changed)
@@SELECTION@@
    ;;
esac

ORDER=(@@ORDER@@)
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
@@LANE_FUNCTIONS@@

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
