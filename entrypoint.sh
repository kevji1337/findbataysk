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

echo "⏳ Running migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting bot..."
exec python -m bot.main
