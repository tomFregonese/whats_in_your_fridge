#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# End-user launcher: this download contains no source code, only compose
# files and this script — it always *pulls* the current published images
# (never builds), starts the stack, waits for health, then opens the app in
# your default browser. Re-run any time you're told a new version is
# available: pulling an already-current image is a fast no-op otherwise.

if ! command -v docker &> /dev/null; then
  echo "Docker was not found on this machine."
  echo "Install Docker Desktop (https://www.docker.com/products/docker-desktop/) first, then"
  echo "run this again."
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "Docker is installed but doesn't seem to be running."
  echo "Start Docker Desktop, then run this again."
  exit 1
fi

if docker compose version &> /dev/null; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose was not found (neither 'docker compose' nor 'docker-compose')."
  echo "Install it: https://docs.docker.com/compose/install/"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "Downloading What's in your fridge? — this can take a few minutes the first time."
"${DOCKER_COMPOSE[@]}" pull

echo "Starting…"
if "${DOCKER_COMPOSE[@]}" up -d --wait --wait-timeout 120; then
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  URL="http://127.0.0.1:${APP_PORT:-8080}"
  echo ""
  echo "✅ Ready! Opening ${URL} in your browser…"
  if command -v open &> /dev/null; then
    open "$URL"
  elif command -v xdg-open &> /dev/null; then
    xdg-open "$URL"
  else
    echo "Open ${URL} in your browser."
  fi
else
  echo ""
  echo "Something went wrong starting the app — see the errors above, or run"
  echo "'${DOCKER_COMPOSE[*]} logs' for more detail."
  exit 1
fi
