#!/bin/zsh
# Gate 0 spike: padjutsu (SDL input) + vibepad inject-rctrl (CGEvent output).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
WORKSPACE="$REPO/spike/bridge"
LOG=/tmp/padjutsu-bridge.log
PADJUTSU_RUN="$REPO/bin/padjutsu-run.sh"

echo "Building vibepad..."
(cd "$REPO" && swift build -c release)

echo "Stopping old padjutsud..."
pkill -f padjutsud 2>/dev/null || true
rm -f "$HOME/Library/Application Support/padjutsud.lock"
sleep 1

if [[ ! -x "$HOME/.cargo/bin/padjutsud" ]]; then
  echo "padjutsud not found at ~/.cargo/bin/padjutsud" >&2
  exit 1
fi

echo "Starting padjutsu bridge (workspace=$WORKSPACE)..."
nohup "$PADJUTSU_RUN" -v run --workspace "$WORKSPACE" >> "$LOG" 2>&1 &
sleep 2

if pgrep -x padjutsud >/dev/null; then
  echo "OK padjutsud running (pid $(pgrep -x padjutsud))"
  echo "Log: $LOG"
  echo "Inject log: /tmp/vibepad-inject.log"
  echo "Test: focus Ghostty, press LB on Xbox controller"
  tail -8 "$LOG"
else
  echo "FAILED to start padjutsud" >&2
  tail -20 "$LOG" >&2
  exit 1
fi
