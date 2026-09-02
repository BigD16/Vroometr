#!/usr/bin/env bash
# Shared docker compose invocation: always load repo-root .env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source ./scripts/load-env.sh

compose() {
  docker compose --env-file .env -f infra/docker-compose.yml "$@"
}

# Create Unleash's database before that container starts. init.sql only runs
# on a brand-new Postgres volume; existing volumes need this extra step.
if [[ "${1:-}" == "up" ]]; then
  compose up -d --wait postgres
  ./scripts/ensure-unleash-db.sh
fi

compose "$@"

