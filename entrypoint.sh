#!/bin/bash
set -e

# Хост БД: supabase-db (контейнер из стека Supabase на VPS)
DB_HOST="${DB_HOST:-supabase-db}"

echo "⏳ Waiting for database ($DB_HOST)..."
until pg_isready -h "$DB_HOST" -U postgres -q; do
  sleep 1
done
echo "✅ Database is ready"

echo "⏳ Running migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting bot..."
exec python -m bot.main
