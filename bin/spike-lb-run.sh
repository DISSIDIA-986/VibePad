#!/bin/zsh
# Run spike-lb-toggle daemon (SDL input → inject-rctrl). Replaces padjutsu for Gate 0.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
LOG=/tmp/spike-lb-toggle.log

echo "Building vibepad..."
(cd "$REPO" && swift build -c release >/dev/null)

pkill -f spike-lb-toggle.py 2>/dev/null || true
pkill -f padjutsud 2>/dev/null || true
rm -f "$LOG"

echo "Starting spike-lb-toggle (LB or A → inject-rctrl)..."
nohup python3 -u "$REPO/bin/spike-lb-toggle.py" >> "$LOG" 2>&1 &
sleep 2

if pgrep -f spike-lb-toggle.py >/dev/null; then
  echo "OK pid $(pgrep -f spike-lb-toggle.py)"
  echo "Log: $LOG"
  echo "Press LB or A in Ghostty (both trigger Doubao toggle for this spike)"
  tail -8 "$LOG" 2>/dev/null || true
else
  echo "FAILED" >&2
  cat "$LOG" >&2
  exit 1
fi
