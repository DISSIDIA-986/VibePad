#!/bin/zsh
# Bring Safari to the foreground (RB). Same hardening as focus-ghostty.
set -euo pipefail

open -a Safari
osascript <<'EOF'
tell application "Safari" to activate
tell application "System Events"
  if exists process "Safari" then
    set frontmost of process "Safari" to true
  end if
end tell
EOF
