#!/usr/bin/env bash
# Run Next.js with server-side settings from the repo-root `.env`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source ./scripts/load-env.sh
cd apps/web
exec npm run dev
