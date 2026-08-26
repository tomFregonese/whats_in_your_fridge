#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker &> /dev/null; then
  echo "Docker was not found on this machine."
  echo "Install Docker Desktop (https://www.docker.com/products/docker-desktop/) or Colima"
  echo "(https://github.com/abiosoft/colima) first."
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "Docker is installed but doesn't seem to be running."
  echo "Start it (Docker Desktop, or 'colima start' if that's what you use), then run this"
  echo "script again."
  exit 1
fi

# Prefer the modern `docker compose` plugin; fall back to the standalone
# `docker-compose` binary otherwise — common on Colima setups, where a
# compose binary is often installed (e.g. via Homebrew) without the plugin
# actually being wired up under `docker`.
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

# This script only ever *launches* the images already built by
# `update.sh` — it never builds. Fails clearly instead of silently
# building (Compose's own default for a missing image), so what's
# actually running is never a surprise. See update.sh's docstring.
missing=()
for image in $("${DOCKER_COMPOSE[@]}" config --images); do
  if ! docker image inspect "$image" &> /dev/null; then
    missing+=("$image")
  fi
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "No built image found for: ${missing[*]}"
  echo "Run ./update.sh first to build it, then run this script again."
  exit 1
fi

echo "Starting What's in your fridge?…"

# `--wait` blocks until both containers report healthy (see each
# Dockerfile's HEALTHCHECK) instead of just "started", so the URL below is
# only printed once the app is actually ready to open.
if "${DOCKER_COMPOSE[@]}" up -d --wait --wait-timeout 120; then
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  echo ""
  echo "✅ Ready! Open http://127.0.0.1:${APP_PORT:-8080} in your browser."
else
  echo ""
  echo "Something went wrong starting the app — see the errors above, or run"
  echo "'${DOCKER_COMPOSE[*]} logs' for more detail."
  exit 1
fi
