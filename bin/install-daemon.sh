#!/bin/zsh
# Install VibePad spike daemon as a user launchd agent (login startup, KeepAlive).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=daemon-singleton.sh
source "$REPO/bin/daemon-singleton.sh"

LABEL="dev.vibepad.spike-lb"
DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
APP_SUPPORT="$HOME/Library/Application Support/VibePad"
INSTALLED_BIN="$APP_SUPPORT/bin"
INSTALLED_WATCH="$INSTALLED_BIN/spike-lb-watch.sh"
PYTHON="$(command -v python3)"
UID="$(id -u)"

echo "Building vibepad..."
(cd "$REPO" && swift build -c release)

chmod +x "$REPO/bin/"*.sh "$REPO/bin/spike-lb-toggle.py" 2>/dev/null || true

mkdir -p "$APP_SUPPORT" "$INSTALLED_BIN"
if [[ ! -f "$APP_SUPPORT/config.yaml" ]]; then
  cp "$REPO/config/default.yaml" "$APP_SUPPORT/config.yaml"
  echo "Installed default config → $APP_SUPPORT/config.yaml"
fi

echo "$REPO" > "$APP_SUPPORT/repo.path"
cp "$REPO/bin/daemon-singleton.sh" "$INSTALLED_BIN/daemon-singleton.sh"
chmod +x "$INSTALLED_BIN/daemon-singleton.sh"
sed -e "s|REPO_PATH|$REPO|g" -e "s|APP_SUPPORT_PATH|$APP_SUPPORT|g" \
  "$REPO/config/launchd/spike-lb-watch.installed.sh.template" > "$INSTALLED_WATCH"
chmod +x "$INSTALLED_WATCH"

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|REPO_PATH|$REPO|g" -e "s|INSTALLED_WATCH|$INSTALLED_WATCH|g" \
  "$REPO/config/launchd/dev.vibepad.spike-lb.plist.template" > "$DEST"

echo "Ensuring single spike stack..."
launchctl bootout "gui/${UID}/${LABEL}" 2>/dev/null || true
vpad_stop_spike_processes "$$"
sleep 1

launchctl bootstrap "gui/${UID}" "$DEST"
launchctl kickstart -k "gui/${UID}/${LABEL}"

sleep 3
if pgrep -f spike-lb-toggle.py >/dev/null; then
  echo "Daemon running (launchd)."
else
  echo "WARN: spike-lb-toggle not running — check /tmp/spike-lb-watch.err.log" >&2
  tail -3 /tmp/spike-lb-watch.err.log 2>/dev/null || true
fi

vpad_print_process_summary || true

echo ""
echo "Installed launchd agent: ${LABEL}"
echo "  plist:  ${DEST}"
echo "  watch:  ${INSTALLED_WATCH}"
echo "  log:    /tmp/spike-lb-toggle.log"
echo "  status: bin/status-daemon.sh"
echo ""
echo "Accessibility (System Settings → Privacy → Accessibility):"
echo "  • ${PYTHON}"
echo "  • ${REPO}/.build/release/vibepad"
echo ""
echo "Manual watch is blocked while launchd runs (singleton lock)."
echo "  Force manual: bin/uninstall-daemon.sh && bin/spike-lb-watch.sh"
echo "Uninstall: bin/uninstall-daemon.sh"
