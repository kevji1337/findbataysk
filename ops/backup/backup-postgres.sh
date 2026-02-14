#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-${SCRIPT_DIR}/backup.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "backup env file not found: ${ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/findbataysk_${STAMP}.sql.gz"

export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --format=plain \
  --no-owner \
  --no-privileges \
  | gzip > "${OUT_FILE}"

find "${BACKUP_DIR}" -name "findbataysk_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "backup created: ${OUT_FILE}"
