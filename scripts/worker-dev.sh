#!/usr/bin/env bash
# Run the Celery worker. Compose (Redis) should already be up.
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
export PYTHONPATH="${ROOT}/libs:${ROOT}:${PYTHONPATH:-}"
exec celery -A workers.celery_app worker --loglevel="${CELERY_LOG_LEVEL}"
