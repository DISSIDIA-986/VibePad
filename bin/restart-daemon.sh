#!/bin/zsh
# Restart spike daemon (fallback if hot-reconnect fails).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=daemon-singleton.sh
source "$REPO/bin/daemon-singleton.sh"
UID="$(id -u)"
LABEL="dev.vibepad.spike-lb"
if launchctl print "gui/${UID}/${LABEL}" >/dev/null 2>&1; then
  vpad_stop_spike_processes "$$"
  launchctl kickstart -k "gui/${UID}/${LABEL}"
  echo "Restarted ${LABEL}"
else
  echo "launchd not loaded — run bin/install-daemon.sh" >&2
  exit 1
fi
sleep 2
exec "$REPO/bin/status-daemon.sh"
