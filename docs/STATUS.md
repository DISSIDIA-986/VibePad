# VibePad — Project Status

**Last updated:** 2026-08-22 (v0.1.1 — hot-reconnect + right-stick scroll)

## Current production stack

```text
launchd (dev.vibepad.spike-lb)
  → ~/Library/Application Support/VibePad/bin/spike-lb-watch.sh
  → bin/spike-lb-toggle.py (Python SDL poll)
  → vibepad / osascript inject
```

**Verify:** `bin/status-daemon.sh` · `tail -f /tmp/spike-lb-toggle.log`

## Milestones

| Milestone | Status | Notes |
|-----------|--------|-------|
| Gate 0 — full mapping | ✅ PASSED | User verified 2026-08-22 |
| Phase 1 Step 1 — launchd | ✅ DONE | No Terminal window; singleton lock |
| Phase 1 Step 2 — VibePad.app | ✅ SCAFFOLD | Menu bar app built; GC path experimental |
| Phase 1 Step 3 — polish | ⏸ DEFERRED | After soak test |
| Git / releases | ✅ v0.1.0 + v0.1.1 | GitHub DISSIDIA-986/VibePad |

## Verified mapping (Ghostty + 豆包)

| Input | Action |
|-------|--------|
| LB | Doubao voice toggle (Right Ctrl) |
| A | Enter |
| B | Ctrl+U |
| X | ⌘Enter |
| Y | Backspace |
| Menu (Start) | Focus Ghostty |
| D-pad ← / → | Previous / next tab |
| Left stick | Mouse (multi-display) |
| Right stick | Scroll Ghostty terminal (↑ history / ↓ latest) |

X button: ⌘Enter on release (BLE may ghost when moving right stick — cooldown applies). Right stick Y-axis scroll does not use the X button.

## Accessibility grants (user confirmed)

- Python 3.14 (`/opt/homebrew/bin/python3`)
- vibepad (`.build/release/vibepad`)
- VibePad.app (menu bar, experimental)

## Known quirks (non-blocking)

1. **D-pad log `err: inject: osascript...`** — audit stderr from `inject-key.sh`, not a failure.
2. **`status-daemon.sh` may show `no lockfile`** — pgrep singleton still OK; re-run `install-daemon.sh` to refresh.
3. **`vibepad doctor` → `controller: none` in CLI** — GameController empty in CLI; may work in VibePad.app GUI.
4. **Spike + GameController daemon can run in parallel** — LB still uses spike; app warns when both active.

## Environment

- Mac Studio, macOS 27 beta
- Xbox Series X Controller (045E:0B13), Bluetooth
- 2–3 displays (incl. 雷鸟 Air 4 AR glasses)
- Ghostty + 豆包 IME (Toggle, Right Ctrl)

## Soak-test watch list (observe few days)

- [ ] LB: missed toggles or double-fire after sleep/wake
- [x] **Bluetooth disconnect/reconnect** — hot-reconnect in spike (2026-08-22); manual fallback: `bin/restart-daemon.sh`
- [ ] A: latency or double Enter in agent input box
- [ ] D-pad: tab switch after Ghostty update or focus change
- [ ] Left stick: cursor clamp at display edges (3 monitors)
- [ ] launchd survives logout/login and controller reconnect (hot-reconnect added; verify on device)
- [ ] Duplicate daemon if manual `spike-lb-watch.sh` is run (should be blocked)

## Resume pointer

Next dev session start here: [TASKS.md](./TASKS.md) → Phase 1 Step 3 or GameController migration.

Restore gstack context: `/context-restore` (checkpoint in `~/.gstack/projects/niuyp/checkpoints/`).
