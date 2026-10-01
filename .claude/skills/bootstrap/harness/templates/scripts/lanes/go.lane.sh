# @select: ^{{DIR}}/
# @vars: DIR=folder holding go.mod
# @format-begin
  {{DIR}}/*.go)
    OUT="$(gofmt -l -w "$REL" 2>&1)" || PROBLEMS="$OUT"
    ;;
# @format-end
lane_{{LANE_FN}}() {
  have go || { echo "⚠ {{LANE}}: go not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  cd {{DIR}} || return 1
  step "{{LANE}}: gofmt" bash -c 'test -z "$(gofmt -l .)"'
  step "{{LANE}}: vet" go vet ./...
  step "{{LANE}}: test" go test ./...
}
