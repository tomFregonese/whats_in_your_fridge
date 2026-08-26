#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker &> /dev/null; then
  echo "Docker was not found on this machine."
  echo "Install Docker Desktop first: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "Docker is installed but doesn't seem to be running."
  echo "Start Docker Desktop, then run this script again."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "Starting What's in your fridge? — this can take a minute on first launch."

# `--wait` blocks until both containers report healthy (see each
# Dockerfile's HEALTHCHECK) instead of just "started", so the URL below is
# only printed once the app is actually ready to open.
if docker compose up -d --build --wait --wait-timeout 120; then
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  echo ""
  echo "✅ Ready! Open http://127.0.0.1:${APP_PORT:-8080} in your browser."
else
  echo ""
  echo "Something went wrong starting the app — see the errors above, or run"
  echo "'docker compose logs' for more detail."
  exit 1
fi
