# @select: ^{{DIR}}/src/{{NS}}\.(Domain|Infrastructure)/|^{{DIR}}/src/{{NS}}\.Api/Program\.cs|^{{DIR}}/tests/{{NS}}\.Api\.IntegrationTests/
# @vars: DIR=.NET solution folder; NS=namespace prefix (e.g. Acme); MIGRATIONS_DIR=path under DIR to the Migrations folder (e.g. src/Acme.Infrastructure/Persistence/Migrations); SNAPSHOT=snapshot file name (e.g. AppDbContextModelSnapshot.cs); EF_PROJECT=path under DIR (e.g. src/Acme.Infrastructure); EF_STARTUP=path under DIR (e.g. src/Acme.Api)
# Two checks: the EF model matches the latest migration, and integration tests pass against a real database (Testcontainers; skipped when Docker is off, CI runs them).
{{LANE_FN}}_migration_check() {
  set -e
  cd {{DIR}}
  dotnet tool restore > /dev/null
  local dir={{MIGRATIONS_DIR}}
  local snapshot="$dir/{{SNAPSHOT}}" backup
  # Back up (not `git checkout`) so an uncommitted real migration survives.
  backup="$(mktemp)"; cp "$snapshot" "$backup"
  dotnet ef migrations add __CiModelCheck \
    --project {{EF_PROJECT}} --startup-project {{EF_STARTUP}} \
    --output-dir "${dir#{{EF_PROJECT}}/}" > /dev/null
  local file pending=0
  file="$(find "$dir" -name '*__CiModelCheck.cs' | head -1)"
  [ -n "$file" ] && grep -q "migrationBuilder\." "$file" && pending=1
  # Never leave the throwaway migration behind (it would edit the snapshot too).
  find "$dir" -name '*__CiModelCheck*' -delete
  cp "$backup" "$snapshot"
  if [ -z "$file" ]; then echo "Expected a generated migration file but found none."; return 1; fi
  if [ "$pending" = 1 ]; then
    echo "The EF Core model has changes not captured in a migration. Run 'dotnet ef migrations add <Name>' and commit it."
    return 1
  fi
  echo "Model matches the latest migration."
}

lane_{{LANE_FN}}() {
  have dotnet || { echo "⚠ {{LANE}}: dotnet not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  step "{{LANE}}: model matches latest migration" {{LANE_FN}}_migration_check
  cd {{DIR}} || return 1
  if [ "$TIER" != "slow" ]; then
    slow_step "{{LANE}}: integration tests (Testcontainers)" true
    return 0
  fi
  if docker_up; then
    step "{{LANE}}: integration tests (Testcontainers)" dotnet test tests/{{NS}}.Api.IntegrationTests --configuration Release --nologo
  else
    echo "⚠ {{LANE}}: Docker not running — integration tests SKIPPED (CI will run them)."
    SKIPPED+=("{{LANE}}: integration tests")
  fi
}
