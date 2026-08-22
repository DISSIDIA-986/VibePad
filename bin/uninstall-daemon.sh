#!/bin/zsh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=daemon-singleton.sh
source "$REPO/bin/daemon-singleton.sh"

LABEL="dev.vibepad.spike-lb"
UID="$(id -u)"
DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/${UID}/${LABEL}" 2>/dev/null || true
rm -f "$DEST"
vpad_stop_spike_processes "$$"
vpad_release_watch_lock

echo "Removed ${LABEL} and stopped spike processes."
