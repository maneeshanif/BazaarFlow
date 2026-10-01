# @select: ^{{DIR}}/
# @vars: DIR=folder holding alembic.ini (Python project managed with uv); URL_ENV=name of the env var alembic's env.py reads for the DB URL (e.g. DATABASE_URL); PG_IMAGE=postgres image for the throwaway database (e.g. postgres:16)
# Migrations must (1) apply cleanly to an empty database, (2) match the SQLAlchemy models (`alembic check`), (3) round-trip (downgrade base, upgrade head).
# Uses $URL_ENV when it is already set (CI service container); otherwise starts a throwaway container if Docker is running.
{{LANE_FN}}_migrations() {
  set -e
  local cid="" port=55432 url
  if [ -n "${{{URL_ENV}}:-}" ]; then
    url="${{{URL_ENV}}}"
  else
    cid="$(docker run -d --rm -p "$port:5432" -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=verify {{PG_IMAGE}})"
    trap 'docker stop "$cid" > /dev/null 2>&1 || true' RETURN
    for _ in $(seq 1 40); do
      docker exec "$cid" pg_isready -U postgres -d verify > /dev/null 2>&1 && break
      sleep 1
    done
    url="postgresql+psycopg://postgres:verify@localhost:$port/verify"
  fi
  export {{URL_ENV}}="$url"
  uv run alembic upgrade head
  uv run alembic check
  uv run alembic downgrade base
  uv run alembic upgrade head
  echo "Migrations apply, match the models, and round-trip."
}

lane_{{LANE_FN}}() {
  have uv || { echo "⚠ {{LANE}}: uv not installed — SKIPPED."; SKIPPED+=("{{LANE}}"); return 0; }
  cd {{DIR}} || return 1
  if [ "$TIER" != "slow" ]; then
    slow_step "{{LANE}}: migrations apply, match models, round-trip" true
    return 0
  fi
  if [ -z "${{{URL_ENV}}:-}" ] && ! docker_up; then
    echo "⚠ {{LANE}}: no {{URL_ENV}} and Docker not running — migration check SKIPPED (CI will run it)."
    SKIPPED+=("{{LANE}}")
    return 0
  fi
  step "{{LANE}}: uv sync" uv sync --locked --quiet || return
  step "{{LANE}}: migrations apply, match models, round-trip" {{LANE_FN}}_migrations
}
