# @select: ^{{DIR}}/|^{{CLIENT_DIR}}/
# @vars: DIR=API source folder; CLIENT_DIR=generated client package folder; START_CMD=command that starts the API bare (may use $PORT), run from repo root; PORT=free local port; HEALTH_PATH=e.g. /health; SPEC_PATH=e.g. /swagger/v1/swagger.json; GEN_CMD=command run inside CLIENT_DIR that regenerates the client (may use $SPEC_URL); GENERATED_FILE=path (from repo root) of the committed generated file to diff
# Fails when the committed generated client differs from what the live API contract produces.
{{LANE_FN}}_stop_port() {
  if have powershell.exe; then
    powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort $1 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }" > /dev/null 2>&1
  elif have fuser; then
    fuser -k "$1/tcp" > /dev/null 2>&1
  fi
  true
}

{{LANE_FN}}_check() {
  set -e
  local port={{PORT}} log pid
  export PORT="$port"
  log="$(mktemp)"
  # Bare, no database: the API's startup must tolerate that, exactly like CI.
  ( exec {{START_CMD}} ) > "$log" 2>&1 &
  pid=$!
  trap '{{LANE_FN}}_stop_port '"$port"'; kill $pid 2>/dev/null || true' RETURN
  local ok=0
  for _ in $(seq 1 60); do
    if curl -sf "http://localhost:$port{{HEALTH_PATH}}" > /dev/null; then ok=1; break; fi
    sleep 2
  done
  if [ "$ok" != 1 ]; then echo "API did not start:"; tail -40 "$log"; return 1; fi
  ( cd {{CLIENT_DIR}} && SPEC_URL="http://localhost:$port{{SPEC_PATH}}" {{GEN_CMD}} )
  if ! git diff --exit-code -- {{GENERATED_FILE}}; then
    echo "{{CLIENT_DIR}} was stale and has been REGENERATED — review and commit the diff above."
    return 1
  fi
  echo "{{CLIENT_DIR}} matches the live API contract."
}

lane_{{LANE_FN}}() {
  slow_step "{{LANE}}: API contract drift" {{LANE_FN}}_check
}
