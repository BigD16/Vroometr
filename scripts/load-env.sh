# Source after cd to repo root. Values come from `.env` only.
if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in every value." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
