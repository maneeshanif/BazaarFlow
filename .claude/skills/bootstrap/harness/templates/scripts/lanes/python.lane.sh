# @select: ^{{DIR}}/
# @vars: DIR=folder holding pyproject.toml (uv + ruff + mypy + pytest)
# @format-begin
  {{DIR}}/*.py)
    if command -v uv > /dev/null 2>&1; then
      PY_REL="${REL#{{DIR}}/}"
      OUT="$(cd {{DIR}} && uv run --quiet ruff check --fix "$PY_REL" 2>&1)" || PROBLEMS="$OUT"
    fi
    ;;
# @format-end
lane_{{LANE_FN}}() {
  have uv || { echo "⚠ {{LANE}}: uv not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  cd {{DIR}} || return 1
  step "{{LANE}}: uv sync" uv sync --locked --quiet || return
  step "{{LANE}}: ruff" uv run ruff check .
  step "{{LANE}}: mypy" uv run mypy .
  step "{{LANE}}: pytest" uv run pytest -q
}
