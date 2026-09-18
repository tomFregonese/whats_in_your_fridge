#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if docker compose version &> /dev/null; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose was not found (neither 'docker compose' nor 'docker-compose')."
  exit 1
fi

echo "Stopping What's in your fridge?…"
"${DOCKER_COMPOSE[@]}" down
echo "Stopped. Your data (data/fridge.db) is untouched — run.sh starts it again anytime."
