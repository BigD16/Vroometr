#!/usr/bin/env bash
# Stop local Postgres, Redis, and LocalStack.
set -euo pipefail
cd "$(dirname "$0")"
./compose.sh down
