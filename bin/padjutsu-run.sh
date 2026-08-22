#!/bin/zsh
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
# Single instance — avoid duplicate padjutsud from watch/restart loops.
if pgrep -x padjutsud >/dev/null 2>&1; then
  echo "padjutsud already running ($(pgrep -x padjutsud | tr '\n' ' '))" >&2
  exit 0
fi
exec /Users/niuyp/.cargo/bin/padjutsud "$@"
