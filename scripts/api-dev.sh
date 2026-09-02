#!/usr/bin/env bash
# Run the API. Compose (Postgres/Redis/LocalStack) should already be up.
# Host/port come from repo-root `.env` (API_HOST, API_PORT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source ./scripts/load-env.sh
cd services/api
exec uvicorn app.main:app --reload --host "${API_HOST}" --port "${API_PORT}"
