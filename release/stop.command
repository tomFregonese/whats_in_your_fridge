#!/usr/bin/env bash
# Double-click entry point for macOS — see run.command for why this works.
exec "$(dirname "$0")/stop.sh"
