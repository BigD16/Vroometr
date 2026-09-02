#!/usr/bin/env bash
# Shared docker compose invocation: always load repo-root .env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
exec docker compose --env-file .env -f infra/docker-compose.yml "$@"
