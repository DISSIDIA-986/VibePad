#!/bin/zsh
# Keep padjutsud alive; restart on exit.
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH:-}"
LOG=/tmp/padjutsu.log
PADJUTSU=/Users/niuyp/.cargo/bin/padjutsud
LOCK="$HOME/Library/Application Support/padjutsud.lock"

while true; do
  rm -f "$LOCK"
  echo "[$(date '+%H:%M:%S')] starting padjutsud" >> "$LOG"
  "$PADJUTSU" run 2>&1 | tee -a "$LOG"
  echo "[$(date '+%H:%M:%S')] padjutsud exited $?, restart in 2s" >> "$LOG"
  sleep 2
done
