#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <backup.env> <backup_file.sql.gz>"
  exit 1
fi

ENV_FILE="$1"
BACKUP_FILE="$2"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "env file not found: ${ENV_FILE}"
  exit 1
fi
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "backup file not found: ${BACKUP_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

export PGPASSWORD="${POSTGRES_PASSWORD}"
gunzip -c "${BACKUP_FILE}" | psql \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}"

echo "restore complete: ${BACKUP_FILE}"
