#!/usr/bin/env bash
# Start local Postgres, Redis, LocalStack (S3), and Unleash.
set -euo pipefail
cd "$(dirname "$0")"
./compose.sh up -d
