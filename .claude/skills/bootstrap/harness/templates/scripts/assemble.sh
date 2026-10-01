#!/usr/bin/env bash
# Assemble scripts/verify.sh and scripts/hooks/format-on-edit.sh for a target
# project from the lane snippets in templates/scripts/lanes/.
#
#   assemble.sh --target <project-dir> \
#       --lane 'api=dotnet@DIR=backend;SLN=App.sln;TESTS=App.Domain.Tests App.Api.Tests' \
#       --lane 'web=node@DIR=frontend' \
#       --lane 'infra=infra@INFRA_DIR=infra' \
#       [--generated-guard 'packages/api-client/src/generated/*|Generated from the OpenAPI contract; never hand-edit.']
#
# A --lane is  <lane-name>=<snippet>@KEY=VAL;KEY=VAL. Vars {{LANE}} (name) and
# {{LANE_FN}} (name with '-' -> '_') are added automatically. Values must not
# contain ";". Lanes run in the order given.
set -euo pipefail
# bash 5.2 treats "&" in ${var//pat/rep} as the matched text; we substitute shell code full of "&&".
shopt -u patsub_replacement 2> /dev/null || true

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET=""; LANES=(); GUARD=""
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift ;;
    --lane) LANES+=("$2"); shift ;;
    --generated-guard) GUARD="$2"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$TARGET" ] && [ ${#LANES[@]} -gt 0 ] || { sed -n 2,13p "$0"; exit 2; }

subst() { # subst <text> <vars-string 'K=V;K=V'>
  local text="$1" pair k v
  local IFS=';'
  for pair in $2; do
    k="${pair%%=*}"; v="${pair#*=}"
    text="${text//\{\{$k\}\}/$v}"
  done
  printf '%s' "$text"
}

NAMES=(); SELECTION=""; FUNCS=""; FORMATS=""
for spec in "${LANES[@]}"; do
  name="${spec%%=*}"; rest="${spec#*=}"
  snippet="${rest%%@*}"; vars=""
  [ "$rest" != "$snippet" ] && vars="${rest#*@}"
  vars="LANE=$name;LANE_FN=${name//-/_};${vars}"
  file="$HERE/lanes/$snippet.lane.sh"
  [ -f "$file" ] || { echo "No lane snippet: $snippet" >&2; exit 2; }
  NAMES+=("$name")
  section=body
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "# @select: "*)
        rx="$(subst "${line#\# @select: }" "$vars")"
        SELECTION+="    touched '$rx' && select_lane $name"$'\n' ;;
      "# @vars: "*) ;;
      "# @format-begin") section=format ;;
      "# @format-end") section=body ;;
      *)
        out="$(subst "$line" "$vars")"
        if [ "$section" = format ]; then FORMATS+="$out"$'\n'; else FUNCS+="$out"$'\n'; fi ;;
    esac
  done < "$file"
  FUNCS+=$'\n'
done

join() { local IFS="$1"; shift; echo "$*"; }
ALL="${NAMES[*]}"
mkdir -p "$TARGET/scripts/hooks"

verify="$(cat "$HERE/verify.sh")"
verify="${verify//@@LANE_NAMES@@/${ALL}}"
verify="${verify//@@ALL_LANES@@/${ALL}}"
verify="${verify//@@EXPLICIT_CASE@@/$(join '|' "${NAMES[@]}")}"
verify="${verify//@@ORDER@@/${ALL}}"
verify="${verify//@@SELECTION@@/${SELECTION%$'\n'}}"
verify="${verify//@@LANE_FUNCTIONS@@/${FUNCS}}"
printf '%s\n' "$verify" > "$TARGET/scripts/verify.sh"

guard_block=""
if [ -n "$GUARD" ]; then
  pat="${GUARD%%|*}"; msg="${GUARD#*|}"
  guard_block="  ${pat})
    PROBLEMS=\"${msg}\"
    ;;"
fi
hook="$(cat "$HERE/hooks/format-on-edit.sh")"
hook="${hook//@@FORMAT_CASES@@/${FORMATS%$'\n'}}"
hook="${hook//@@GENERATED_GUARD@@/${guard_block}}"
printf '%s\n' "$hook" > "$TARGET/scripts/hooks/format-on-edit.sh"

cp "$HERE/hooks/verify-on-stop.sh" "$TARGET/scripts/hooks/verify-on-stop.sh"
cp "$HERE/install-hooks.sh" "$TARGET/scripts/install-hooks.sh"
cp "$HERE/check_verdict.py" "$TARGET/scripts/check_verdict.py"
cp "$HERE/harness-check.sh" "$TARGET/scripts/harness-check.sh"
cp "$HERE/check_plan.py" "$TARGET/scripts/check_plan.py"
chmod +x "$TARGET"/scripts/*.sh "$TARGET"/scripts/hooks/*.sh
echo "assembled: lanes -> ${ALL}"
