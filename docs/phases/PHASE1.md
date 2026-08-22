# Phase 1 — Production daemon

Gate 0 **passed** 2026-08-22 (Mac Studio, macOS 27 beta, Xbox 045E:0B13, 2–3 displays).

## Gate 0 recap (verified)

| Input | Action | Status |
|-------|--------|--------|
| LB | Doubao voice toggle (`flagsChanged` Right Ctrl) | ✅ |
| A | Enter / send | ✅ |
| B | Ctrl+U (clear line in agent input) | ✅ |
| X | ⌘Enter | ✅ |
| Y | Backspace | ✅ |
| Menu (Start) | Focus Ghostty | ✅ |
| Left stick | Mouse move (multi-display bounds) | ✅ |
| Right stick | Scroll Ghostty terminal (v0.1.1) | ✅ |
| Bluetooth reconnect | Hot-reconnect without restart (v0.1.1) | ✅ |

**Stack that works:** `bin/spike-lb-watch.sh` → Python SDL poll → `vibepad` / shell inject.

**Stack that does not (yet):** `vibepad run` with GameController — `GCController.controllers()` returns 0 in CLI context on this machine.

## Phase 1 goals

1. **No Terminal window** — launchd KeepAlive (`bin/install-daemon.sh`)
2. **Single shipped binary path** — VibePad.app (menu-bar) with SDL input + Swift inject
3. **Config parity** — YAML matches spike mappings; `start` → focus Ghostty as first-class action

## Recommended order

### Step 1 — launchd ✅

```bash
bin/install-daemon.sh      # one-time install
bin/status-daemon.sh       # check running
bin/uninstall-daemon.sh    # remove
tail -f /tmp/spike-lb-toggle.log
```

Grant Accessibility to `python3` and `.build/release/vibepad`.

**Note:** Singleton lock — only one spike stack (manual or launchd). `bin/status-daemon.sh` warns on duplicates.

### Step 2 — VibePad.app scaffold ✅ (initial)

```bash
bin/build-app.sh           # → VibePad.app (menu bar, LSUIElement)
open VibePad.app           # check GameController discovery in GUI context
```

- Menu-bar app shows controller + daemon status
- Experimental "Start GameController daemon" uses `VibePadCore` (no Python)
- Production input path remains spike launchd until in-app GC is verified

### Step 3 — polish

- Y hold → repeat backspace
- `vibepad doctor` reports launchd status + controller + display count
- Config install to `~/Library/Application Support/VibePad/config.yaml`

## Out of scope (Phase 2+)

- GUI settings
- Hold-to-talk
- Non-Ghostty profiles
- Karabiner / ControllerKeys fork

## References

- **Session status:** [STATUS.md](../STATUS.md)
- **Task tracker:** [TASKS.md](../TASKS.md)
- Gate 0 checklist: [GATE0.md](../spike/GATE0.md)
- Design: [vibepad.md](../designs/vibepad.md)
