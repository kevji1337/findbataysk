#!/bin/bash
set -e

# Пытаемся достать хост из DATABASE_URL если он есть
if [[ -n "$DATABASE_URL" ]]; then
  # Извлекаем хост из URL (поддерживает форматы postgresql://user:pass@host:port/db)
  DB_HOST=$(echo $DATABASE_URL | sed -e 's|.*@||' -e 's|:.*||' -e 's|/.*||')
fi

DB_HOST="${DB_HOST:-localhost}"

echo "⏳ Waiting for database ($DB_HOST)..."
# Ждем максимум 30 секунд, чтобы не висеть вечно если что-то не так
for i in {1..30}; do
  if pg_isready -h "$DB_HOST" -U postgres -q; then
    echo "✅ Database is ready"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "⚠️ Database wait timed out, attempting migrations anyway..."
  fi
done

echo "⏳ Running migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting bot..."
exec python -m bot.main
