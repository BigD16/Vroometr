#!/usr/bin/env bash
# Start local Postgres, Redis, and LocalStack (S3).
set -euo pipefail
cd "$(dirname "$0")"
./compose.sh up -d
