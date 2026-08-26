#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up -d --build

# shellcheck disable=SC1091
source .env 2>/dev/null || true
echo ""
echo "What's in your fridge? is starting up."
echo "Open http://127.0.0.1:${APP_PORT:-8080} once the containers report healthy."
