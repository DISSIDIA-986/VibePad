#!/bin/zsh
# Shared helpers: ensure at most one spike-lb-watch + spike-lb-toggle stack.
VPAD_LOCKDIR="${VPAD_LOCKDIR:-/tmp/vibepad-spike-watch.lock.d}"
VPAD_LABEL="dev.vibepad.spike-lb"

vpad_watch_pids() {
  pgrep -f '[s]pike-lb-watch\.sh' 2>/dev/null
}

vpad_toggle_pids() {
  pgrep -f '[s]pike-lb-toggle\.py' 2>/dev/null
}

vpad_launchd_loaded() {
  launchctl print "gui/$(id -u)/${VPAD_LABEL}" >/dev/null 2>&1
}

vpad_launchd_running() {
  vpad_launchd_loaded && launchctl print "gui/$(id -u)/${VPAD_LABEL}" 2>&1 | rg -q 'state = running'
}

vpad_lock_holder_pid() {
  [[ -f "$VPAD_LOCKDIR/pid" ]] && cat "$VPAD_LOCKDIR/pid" 2>/dev/null
}

vpad_pid_is_live_watch() {
  local pid="$1"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  ps -p "$pid" -o command= 2>/dev/null | rg -q 'spike-lb-watch'
}

vpad_clear_stale_lock() {
  if [[ ! -d "$VPAD_LOCKDIR" ]]; then
    return 0
  fi
  local holder
  holder="$(vpad_lock_holder_pid)"
  if vpad_pid_is_live_watch "$holder"; then
    return 1
  fi
  rm -rf "$VPAD_LOCKDIR"
  return 0
}

vpad_stop_spike_processes() {
  local self="${1:-$$}"
  local pid

  for pid in ${(f)"$(vpad_watch_pids)"}; do
    [[ "$pid" == "$self" || "$pid" == "$PPID" ]] && continue
    kill "$pid" 2>/dev/null || true
  done
  for pid in ${(f)"$(vpad_toggle_pids)"}; do
    kill "$pid" 2>/dev/null || true
  done
  sleep 1
  for pid in ${(f)"$(vpad_watch_pids)"}; do
    [[ "$pid" == "$self" || "$pid" == "$PPID" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
  done
  for pid in ${(f)"$(vpad_toggle_pids)"}; do
    kill -9 "$pid" 2>/dev/null || true
  done
  vpad_clear_stale_lock || true
}

vpad_count_watchers() {
  vpad_watch_pids | wc -l | tr -d ' '
}

vpad_count_toggles() {
  vpad_toggle_pids | wc -l | tr -d ' '
}

# Call at watch script startup. Exits 1 if another live watcher holds the lock.
vpad_acquire_watch_lock() {
  local replace="${1:-0}"
  local self="$$"
  local pid

  if [[ "$replace" == 1 ]]; then
    vpad_stop_spike_processes "$self"
  else
    for pid in ${(f)"$(vpad_watch_pids)"}; do
      [[ "$pid" == "$self" || "$pid" == "$PPID" ]] && continue
      echo "spike-lb-watch already running (pid ${pid})." >&2
      echo "  $(ps -p "$pid" -o command= 2>/dev/null)" >&2
      if vpad_launchd_running; then
        echo "  launchd ${VPAD_LABEL} is active — bin/status-daemon.sh" >&2
        echo "  To stop launchd: bin/uninstall-daemon.sh" >&2
      fi
      echo "  Replace all: bin/spike-lb-watch.sh --replace" >&2
      return 1
    done
    vpad_clear_stale_lock || true
  fi

  if ! mkdir "$VPAD_LOCKDIR" 2>/dev/null; then
    local holder
    holder="$(vpad_lock_holder_pid)"
    if vpad_pid_is_live_watch "$holder"; then
      echo "spike-lb-watch already running (pid ${holder})." >&2
      if vpad_launchd_running; then
        echo "  launchd ${VPAD_LABEL} is active — bin/status-daemon.sh" >&2
        echo "  To stop launchd: bin/uninstall-daemon.sh" >&2
      fi
      echo "  Replace all: bin/spike-lb-watch.sh --replace" >&2
      return 1
    fi
    vpad_clear_stale_lock || true
    mkdir "$VPAD_LOCKDIR" 2>/dev/null || {
      echo "spike-lb-watch lock busy — try again or use --replace" >&2
      return 1
    }
  fi

  echo $$ > "$VPAD_LOCKDIR/pid"
  trap 'rm -f "$VPAD_LOCKDIR/pid"; rmdir "$VPAD_LOCKDIR" 2>/dev/null' EXIT INT TERM
  return 0
}

vpad_release_watch_lock() {
  rm -f "$VPAD_LOCKDIR/pid"
  rmdir "$VPAD_LOCKDIR" 2>/dev/null || true
}

vpad_print_process_summary() {
  local watches toggles
  watches="$(vpad_count_watchers)"
  toggles="$(vpad_count_toggles)"
  if [[ "$watches" -gt 1 || "$toggles" -gt 1 ]]; then
    echo "WARN: duplicate spike processes (watch=${watches} toggle=${toggles})" >&2
    vpad_watch_pids | while read -r pid; do echo "  watch pid $pid: $(ps -p "$pid" -o command= 2>/dev/null)" >&2; done
    vpad_toggle_pids | while read -r pid; do echo "  toggle pid $pid" >&2; done
    echo "  Fix: bin/spike-lb-watch.sh --replace  OR  bin/install-daemon.sh" >&2
    return 1
  fi
  return 0
}
