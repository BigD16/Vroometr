#!/usr/bin/env bash
# Run the Celery worker. Compose (Redis) should already be up.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source ./scripts/load-env.sh
# IDE/local HTTP proxies break outbound OpenAI embedding/rerank calls.
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export PYTHONPATH="${ROOT}/libs:${ROOT}/services/api:${ROOT}:${PYTHONPATH:-}"
exec celery -A workers.celery_app worker --loglevel="${CELERY_LOG_LEVEL}"
