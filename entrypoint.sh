#!/bin/bash
set -e

echo "⏳ Waiting for database..."
until pg_isready -h db -U postgres -q; do
  sleep 1
done
echo "✅ Database is ready"

echo "⏳ Running migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting bot..."
exec python -m bot.main
