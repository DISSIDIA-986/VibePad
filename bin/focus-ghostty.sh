#!/bin/zsh
# Bring Ghostty to the foreground (focus recovery when another app stole focus).
set -euo pipefail
osascript <<'EOF'
tell application "Ghostty" to activate
EOF
