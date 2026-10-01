# @select: ^{{DIR}}/
# @vars: DIR=path to the .NET solution folder (contains {{SLN}}); SLN=solution file name; TESTS=space-separated test project dirs under {{DIR}}/tests
# @format-begin
  {{DIR}}/*.cs)
    # Whitespace/EOL only: no build, ~2s. Analyzer issues surface in verify.
    (cd {{DIR}} && dotnet format whitespace . --folder --include "${REL#{{DIR}}/}" > /dev/null 2>&1)
    ;;
# @format-end
# Same scan CI runs. Fix a hit by pinning the patched version in the offending project.
{{LANE_FN}}_vulnerable_packages() {
  local output
  output="$(dotnet list {{SLN}} package --vulnerable --include-transitive 2>&1)" || true
  if echo "$output" | grep -qi "has the following vulnerable packages"; then
    echo "$output"
    return 1
  fi
}

lane_{{LANE_FN}}() {
  have dotnet || { echo "⚠ {{LANE}}: dotnet not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  cd {{DIR}} || return 1
  step "{{LANE}}: dotnet format --verify-no-changes" dotnet format {{SLN}} --verify-no-changes
  step "{{LANE}}: build" dotnet build {{SLN}} --configuration Release --nologo -v q || return
  for t in {{TESTS}}; do
    step "{{LANE}}: test $t" dotnet test "tests/$t" --configuration Release --no-build --nologo
  done
  slow_step "{{LANE}}: NuGet vulnerability scan" {{LANE_FN}}_vulnerable_packages
}
