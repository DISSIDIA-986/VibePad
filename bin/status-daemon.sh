#!/bin/zsh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=daemon-singleton.sh
source "$REPO/bin/daemon-singleton.sh"

LABEL="dev.vibepad.spike-lb"
UID="$(id -u)"

echo "=== launchd ==="
if launchctl print "gui/${UID}/${LABEL}" >/dev/null 2>&1; then
  launchctl print "gui/${UID}/${LABEL}" 2>&1 | rg "state =|pid =|last exit"
else
  echo "not loaded (run bin/install-daemon.sh)"
fi

echo ""
echo "=== singleton lock ==="
if [[ -d "$VPAD_LOCKDIR" ]]; then
  holder="$(vpad_lock_holder_pid)"
  echo "lock held by pid ${holder:-?} ($(ps -p "${holder:-0}" -o command= 2>/dev/null || echo stale))"
elif [[ "$(vpad_count_watchers)" -gt 0 ]]; then
  echo "no lockfile (process detected — re-run bin/install-daemon.sh to refresh)"
else
  echo "no lock (watch not running)"
fi

echo ""
echo "=== processes ==="
WATCHES="$(vpad_count_watchers)"
TOGGLES="$(vpad_count_toggles)"
echo "watch scripts: ${WATCHES}, toggle python: ${TOGGLES}"
pgrep -fl spike-lb || echo "no spike-lb processes"

echo ""
if ! vpad_print_process_summary; then
  :
elif [[ "$WATCHES" -eq 0 && "$TOGGLES" -eq 0 ]]; then
  echo "singleton: ok (stopped)"
elif [[ "$WATCHES" -eq 1 && "$TOGGLES" -le 1 ]]; then
  echo "singleton: ok (one stack)"
fi

echo ""
echo "=== log (last 3) ==="
tail -3 /tmp/spike-lb-toggle.log 2>/dev/null || echo "no log yet"
