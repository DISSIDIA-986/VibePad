#!/bin/zsh
# Step 1: prove Xbox hardware buttons reach macOS via SDL (no padjutsu).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
DURATION="${1:-45}"
LOG=/tmp/spike-lb-toggle.log

echo "=== Xbox button diagnostic (SDL direct, ${DURATION}s) ==="
echo "1. Press Xbox logo to wake controller"
echo "2. Press LB, A, RB during the countdown"
echo ""

pkill -f spike-lb-toggle.py 2>/dev/null || true
pkill -f padjutsud 2>/dev/null || true
pkill -f gamepad-monitor 2>/dev/null || true
rm -f "$LOG"
sleep 1

python3 "$REPO/bin/spike-lb-toggle.py" &
PID=$!
sleep "$DURATION"
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

echo ""
echo "=== Results ($LOG) ==="
if [[ ! -s "$LOG" ]]; then
  echo "NO LOG — script failed to start"
  exit 1
fi

DOWN=$(rg -c " DOWN " "$LOG" 2>/dev/null || echo 0)
INJECT=$(rg -c "ACTION inject-rctrl" "$LOG" 2>/dev/null || echo 0)

echo "Button DOWN events: $DOWN"
echo "Inject actions:     $INJECT"
echo ""
rg "DOWN |ACTION |NO CONTROLLER|opened" "$LOG" || true

if [[ "$DOWN" -eq 0 ]]; then
  echo ""
  echo "VERDICT: Hardware input NOT detected."
  echo "Try: wake controller, quit Steam, re-pair Bluetooth, or plug in USB."
  exit 2
fi

if [[ "$INJECT" -eq 0 ]]; then
  echo ""
  echo "VERDICT: Buttons detected but LB did not fire inject."
  exit 3
fi

echo ""
echo "VERDICT: LB → inject path works. Check Doubao in Ghostty."
