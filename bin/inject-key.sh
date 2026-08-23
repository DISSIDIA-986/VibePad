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
    cmd+equal|cmd+plus)
      echo "inject: osascript cmd+equal" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "=" using command down
end tell
EOF
      ;;
    cmd+minus)
      echo "inject: osascript cmd+minus" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "-" using command down
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
    cmd+openbracket)
      echo "inject: osascript cmd+[" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "[" using command down
end tell
EOF
      ;;
    space)
      echo "inject: osascript space" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 49
end tell
EOF
      ;;
    left|leftarrow)
      echo "inject: osascript left" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 123
end tell
EOF
      ;;
    right|rightarrow)
      echo "inject: osascript right" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 124
end tell
EOF
      ;;
    up|uparrow)
      echo "inject: osascript up" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 126
end tell
EOF
      ;;
    down|downarrow)
      echo "inject: osascript down" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 125
end tell
EOF
      ;;
    escape|esc)
      echo "inject: osascript escape" >&2
      osascript <<'EOF'
tell application "System Events"
  key code 53
end tell
EOF
      ;;
    slash|/)
      echo "inject: osascript slash" >&2
      osascript <<'EOF'
tell application "System Events"
  keystroke "/"
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
  cmd+z|cmd+enter|cmd+equal|cmd+plus|cmd+minus|cmd+grave|cmd+backtick|cmd+shift+grave|cmd+shift+backtick|cmd+shift+openbracket|cmd+shift+closebracket|cmd+openbracket|space|left|leftarrow|right|rightarrow|up|uparrow|down|downarrow|escape|esc|slash|/)
    cmd_via_system_events "$1"
    exit 0
    ;;
esac

if [[ ! -x "$VIBEPAD" ]]; then
  (cd "$REPO" && swift build -c release >&2) || exit 1
fi
echo "inject: vibepad test $*" >&2
exec "$VIBEPAD" test "$@"
