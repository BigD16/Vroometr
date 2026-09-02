#!/usr/bin/env bash
# Create the Unleash database if this Postgres volume already existed
# before Unleash was added (init.sql only runs on first boot).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .env.example
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi
set +a

if ! docker exec vroometr-postgres pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; then
  echo "Postgres is not running; skip Unleash database check."
  exit 0
fi

exists="$(docker exec vroometr-postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '${UNLEASH_DATABASE_NAME}'")"
if [[ "${exists}" != "1" ]]; then
  docker exec vroometr-postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -c "CREATE DATABASE ${UNLEASH_DATABASE_NAME}"
  echo "Created database ${UNLEASH_DATABASE_NAME}"
fi
