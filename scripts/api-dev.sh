#!/usr/bin/env bash
# Run the API. Compose (Postgres/Redis/LocalStack) should already be up.
# Host/port come from repo-root `.env` (API_HOST, API_PORT).
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
cd services/api
exec uvicorn app.main:app --reload --host "${API_HOST}" --port "${API_PORT}"
