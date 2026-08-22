#!/bin/zsh
# Padjutsu shell action → vibepad flagsChanged Right Ctrl (Doubao Toggle).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$REPO/.build/release/vibepad"
if [[ ! -x "$BIN" ]]; then
  (cd "$REPO" && swift build -c release >&2) || exit 1
fi
exec "$BIN" inject-rctrl
