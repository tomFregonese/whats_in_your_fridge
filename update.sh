#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Rebuilds the app's images from the current source — this is the only
# script that ever builds (see start.sh, which only launches whatever was
# last built here). Doesn't touch anything in ./data: images are separate
# from your data volume, so your fridge.db is never at risk from this.
#
# Safe to run while the app is up: the running containers keep using the
# old image until you run start.sh again, which picks up the new one.

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

if docker compose version &> /dev/null; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose was not found (neither 'docker compose' nor 'docker-compose')."
  echo "Install it: https://docs.docker.com/compose/install/"
  exit 1
fi

echo "Rebuilding What's in your fridge? images — this can take a minute."

if "${DOCKER_COMPOSE[@]}" build; then
  echo ""
  echo "✅ Images rebuilt. Run ./start.sh to launch the new version."
else
  echo ""
  echo "Something went wrong rebuilding the images — see the errors above."
  exit 1
fi
