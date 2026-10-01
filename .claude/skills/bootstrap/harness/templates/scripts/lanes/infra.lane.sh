# @select: ^{{INFRA_DIR}}/|^\.github/workflows/|^scripts/
# @vars: INFRA_DIR=folder holding docker compose files (may not exist yet)
lane_{{LANE_FN}}() {
  if [ -f {{INFRA_DIR}}/docker-compose.yml ] && docker_up; then
    step "{{LANE}}: compose config" bash -c 'cd {{INFRA_DIR}} && docker compose -f docker-compose.yml config --quiet'
  else
    echo "⚠ {{LANE}}: no compose file or Docker not running — compose check SKIPPED."
    SKIPPED+=("{{LANE}}")
  fi
  if [ -d .github/workflows ] && docker_up; then
    # MSYS_NO_PATHCONV: stop Git Bash on Windows rewriting /repo into a host path.
    slow_step "{{LANE}}: actionlint" env MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$ROOT"):/repo" -w /repo rhysd/actionlint:1.7.7 -color
  fi
  step "{{LANE}}: verify.sh syntax" bash -n scripts/verify.sh
}
