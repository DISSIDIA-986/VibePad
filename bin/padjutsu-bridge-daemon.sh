#!/bin/zsh
# launchd-friendly padjutsu bridge daemon entrypoint.
set -euo pipefail
REPO="/Users/niuyp/Documents/github.com/VibePad"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
exec "$REPO/bin/padjutsu-run.sh" -v run --workspace "$REPO/spike/bridge"
