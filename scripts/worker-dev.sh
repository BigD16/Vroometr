#!/usr/bin/env bash
# Run the Celery worker. Compose (Redis) should already be up.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source ./scripts/load-env.sh
export PYTHONPATH="${ROOT}/libs:${ROOT}:${PYTHONPATH:-}"
exec celery -A workers.celery_app worker --loglevel="${CELERY_LOG_LEVEL}"
