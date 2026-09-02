#!/usr/bin/env bash
# Run the API. Compose (Postgres/Redis/LocalStack) should already be up.
set -euo pipefail
cd "$(dirname "$0")/../services/api"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
