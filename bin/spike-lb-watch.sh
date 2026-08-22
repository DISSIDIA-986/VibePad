#!/bin/zsh
# Keep spike-lb-toggle alive — restart if it exits. Singleton: one stack at a time.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=daemon-singleton.sh
source "$REPO/bin/daemon-singleton.sh"

REPLACE=0
[[ "${1:-}" == "--replace" ]] && REPLACE=1

if ! vpad_acquire_watch_lock "$REPLACE"; then
  exit 1
fi

export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
LOG=/tmp/spike-lb-toggle.log
SCRIPT="$REPO/bin/spike-lb-toggle.py"

echo "[$(date '+%H:%M:%S')] spike-lb-watch started (pid $$, replace=${REPLACE})" >> "$LOG"
(cd "$REPO" && swift build -c release >/dev/null 2>&1) || true

while true; do
  echo "[$(date '+%H:%M:%S')] starting spike-lb-toggle" >> "$LOG"
  python3 -u "$SCRIPT"
  echo "[$(date '+%H:%M:%S')] exited, restart in 2s" >> "$LOG"
  sleep 2
done
