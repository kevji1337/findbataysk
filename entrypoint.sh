#!/bin/bash
set -euo pipefail

parse_database_url() {
  python - <<'PY'
import os
import shlex
from urllib.parse import urlparse, unquote

database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url:
    raise SystemExit("DATABASE_URL is required")

parsed = urlparse(database_url)
host = parsed.hostname or "localhost"
port = parsed.port or 5432
user = unquote(parsed.username or "postgres")
password = unquote(parsed.password or "")
database = (parsed.path or "/postgres").lstrip("/") or "postgres"

for key, value in {
    "DB_HOST": host,
    "DB_PORT": str(port),
    "DB_USER": user,
    "DB_PASSWORD": password,
    "DB_NAME": database,
}.items():
    print(f"export {key}={shlex.quote(value)}")
PY
}

maybe_restore_backup() {
  local restore_mode="${RESTORE_BACKUP_MODE:-never}"
  local backup_path="${RESTORE_BACKUP_PATH:-/app/public.backup}"
  local restore_schema="${RESTORE_BACKUP_SCHEMA:-public}"

  case "$restore_mode" in
    never)
      return
      ;;
    if_empty|always)
      ;;
    *)
      echo "❌ Unknown RESTORE_BACKUP_MODE: $restore_mode"
      exit 1
      ;;
  esac

  if [[ ! -f "$backup_path" ]]; then
    echo "❌ Backup file not found: $backup_path"
    exit 1
  fi

  if [[ "$restore_mode" == "if_empty" ]]; then
    local table_count
    table_count=$(
      psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${restore_schema}' AND table_type='BASE TABLE';"
    )
    table_count="${table_count//[[:space:]]/}"

    if [[ "${table_count:-0}" != "0" ]]; then
      echo "ℹ️ Restore skipped: schema '${restore_schema}' is not empty"
      return
    fi
  fi

  echo "⏳ Restoring backup from $backup_path..."
  if [[ "$(head -c 5 "$backup_path" || true)" == "PGDMP" ]]; then
    pg_restore \
      --host="$DB_HOST" \
      --port="$DB_PORT" \
      --username="$DB_USER" \
      --dbname="$DB_NAME" \
      --schema="$restore_schema" \
      --clean \
      --if-exists \
      --no-owner \
      --no-privileges \
      --single-transaction \
      --exit-on-error \
      "$backup_path"
  else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$backup_path"
  fi
  echo "✅ Backup restored"
}

eval "$(parse_database_url)"
export PGPASSWORD="$DB_PASSWORD"

echo "⏳ Waiting for database ($DB_HOST:$DB_PORT/$DB_NAME)..."
for i in {1..30}; do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q; then
    echo "✅ Database is ready"
    break
  fi

  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "⚠️ Database wait timed out, attempting startup anyway..."
  fi
done

maybe_restore_backup

echo "⏳ Running migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting bot..."
exec python -m bot.main
