#!/bin/zsh
# Key injection for spike — cmd combos use System Events (CGEvent ⌘ leaks bare keys).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VIBEPAD="$REPO/.build/release/vibepad"

cmd_via_system_events() {
  local key="$1"
  case "$key" in
    cmd+z)
      echo "inject: osascript cmd+z" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "z" using command down
end tell
EOF
      ;;
    cmd+enter)
      echo "inject: osascript cmd+enter" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 36 using command down
end tell
EOF
      ;;
    cmd+shift+openbracket)
      echo "inject: osascript cmd+shift+[" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "[" using {command down, shift down}
end tell
EOF
      ;;
    cmd+shift+closebracket)
      echo "inject: osascript cmd+shift+]" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "]" using {command down, shift down}
end tell
EOF
      ;;
    cmd+grave|cmd+backtick)
      echo "inject: osascript cmd+grave" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "`" using command down
end tell
EOF
      ;;
    cmd+shift+grave|cmd+shift+backtick)
      echo "inject: osascript cmd+shift+grave" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "`" using {command down, shift down}
end tell
EOF
      ;;
    *)
      echo "unknown cmd combo: $key" >&2
      return 1
      ;;
  esac
}

case "${1:-}" in
  cmd+z|cmd+enter|cmd+grave|cmd+backtick|cmd+shift+grave|cmd+shift+backtick|cmd+shift+openbracket|cmd+shift+closebracket)
    cmd_via_system_events "$1"
    exit 0
    ;;
esac

if [[ ! -x "$VIBEPAD" ]]; then
  (cd "$REPO" && swift build -c release >&2) || exit 1
fi
echo "inject: vibepad test $*" >&2
exec "$VIBEPAD" test "$@"
