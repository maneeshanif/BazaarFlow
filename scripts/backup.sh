#!/usr/bin/env bash
# Logical backup of the BazaarFlow database (build-plan task 58, PRD section 18).
#
#   BACKUP_DATABASE_URL=postgresql://... bash scripts/backup.sh [output-dir]
#
# Uses the owner role's URL (DATABASE_URL_MIGRATIONS): the application role cannot read every table. The dump is the
# custom format, so `pg_restore` can restore all of it or one table. It runs pg_dump from a postgres:16 container, so
# nothing needs installing. The URL is never printed. Dumps older than BACKUP_KEEP_DAYS (default 7) are removed.
# Supabase also keeps its own daily backups; this script is the copy you hold yourself.
set -euo pipefail

url="${BACKUP_DATABASE_URL:-}"
if [ -z "$url" ]; then
  echo "backup: set BACKUP_DATABASE_URL to the owner database URL (postgresql://...)" >&2
  exit 2
fi
out="${1:-backups}"
keep="${BACKUP_KEEP_DAYS:-7}"
mkdir -p "$out"
file="bazaarflow-$(date -u +%Y%m%dT%H%M%SZ).dump"

# pg_dump takes a libpq URL: strip the SQLAlchemy driver suffix if it is there
url="${url/postgresql+asyncpg:/postgresql:}"

MSYS_NO_PATHCONV=1 docker run --rm -e "PGURL=$url" -v "$(cd "$out" && pwd -W 2>/dev/null || pwd):/out" postgres:16 \
  sh -c 'pg_dump --format=custom --no-owner --no-privileges "$PGURL" -f "/out/'"$file"'"'
size=$(wc -c < "$out/$file")
echo "backup: wrote $out/$file ($size bytes)"
find "$out" -name 'bazaarflow-*.dump' -mtime +"$keep" -print -delete | sed 's/^/backup: removed old /'
