#!/bin/zsh
# Bring Ghostty to the foreground (Menu / focus recovery).
# Plain `activate` often loses to Chrome CDP / automation re-steal;
# open -a + System Events frontmost is more reliable.
set -euo pipefail

open -a Ghostty
osascript <<'EOF'
tell application "Ghostty" to activate
tell application "System Events"
  if exists process "ghostty" then
    set frontmost of process "ghostty" to true
  end if
end tell
EOF
