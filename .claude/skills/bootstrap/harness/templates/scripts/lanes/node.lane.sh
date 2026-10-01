# @select: ^{{DIR}}/
# @select: ^package(-lock)?\.json$
# @vars: DIR=folder holding the package.json for this lane
# @format-begin
  {{DIR}}/*.ts|{{DIR}}/*.tsx|{{DIR}}/*.js|{{DIR}}/*.mjs)
    NODE_REL="${REL#{{DIR}}/}"
    OUT="$(cd {{DIR}} && npx --no-install eslint --fix "$NODE_REL" 2>&1)" || PROBLEMS="$OUT"
    ;;
# @format-end
lane_{{LANE_FN}}() {
  have npm || { echo "⚠ {{LANE}}: npm not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  [ -d node_modules ] || [ -d {{DIR}}/node_modules ] || step "{{LANE}}: install" npm ci || return
  cd {{DIR}} || return 1
  has_script() { node -e 'process.exit(require("./package.json").scripts?.[process.argv[1]] ? 0 : 1)' "$1"; }
  has_script lint && step "{{LANE}}: lint" npm run --silent lint
  has_script typecheck && step "{{LANE}}: typecheck" npm run --silent typecheck
  [ -f tsconfig.json ] && ! has_script typecheck && step "{{LANE}}: tsc" npx tsc --noEmit
  has_script test && step "{{LANE}}: test" npm run --silent test
  has_script build && slow_step "{{LANE}}: build" npm run --silent build
  return 0
}
