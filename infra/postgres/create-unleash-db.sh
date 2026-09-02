#!/bin/bash
# Runs only on a brand-new Postgres volume (docker-entrypoint-initdb.d).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
  -c "SELECT 'CREATE DATABASE ${UNLEASH_DATABASE_NAME}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${UNLEASH_DATABASE_NAME}')\gexec"
