#!/usr/bin/env bash
# Double-click entry point for macOS — Terminal.app is the registered
# handler for .command files given the executable bit is set. See
# README.txt for the one-time Gatekeeper "unidentified developer" step.
exec "$(dirname "$0")/run.sh"
