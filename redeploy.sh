#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Convenience wrapper for the common "pull latest code, apply it" cycle —
# just chains update.sh (rebuild the images) and start.sh (launch the
# newly built ones) so you don't have to run them one at a time. Neither
# script's own behavior changes: `set -e` above stops here if update.sh
# fails, so start.sh never launches a stale/broken build. See each
# script's own comments for what it actually does.

./update.sh
./start.sh
