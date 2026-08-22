# Changelog

All notable changes to VibePad are documented here.

## [0.1.0] — 2026-08-22

### What you can do now

- Map an Xbox Bluetooth controller to Ghostty + 豆包 IME: LB toggles voice, A sends Enter, B clears the agent input line (Ctrl+U), X fullscreen (⌘Enter), Y backspace, Menu focuses Ghostty, D-pad switches tabs, left stick moves the mouse across all displays.
- Run headless via launchd — no Terminal window after `bin/install-daemon.sh`.
- Check health with `bin/status-daemon.sh` and `.build/release/vibepad doctor`.

### Added

- **VibePadCore** — CGEvent inject, RCtrl debounce, mouse engine, YAML config, GameController service.
- **vibepad CLI** — `test`, `run`, `doctor`, `inject-rctrl`, `probe`, `bench`.
- **Python SDL spike** (`bin/spike-lb-toggle.py`) — production input path with poll fixes for BLE Xbox controller.
- **launchd daemon** — `bin/install-daemon.sh`, Application Support install path, singleton lock (`bin/daemon-singleton.sh`).
- **VibePad.app** (experimental scaffold) — menu-bar status, optional GameController daemon.
- **Docs** — Gate 0 checklist, Phase 1 roadmap, STATUS/TASKS trackers.

### Known limitations

- GameController does not see the controller in CLI; spike (Python SDL) is the production stack until in-app GC is verified.
- Config YAML missing d-pad / Menu / LB entries (spike-only for now).
- Right stick intentionally unused (BLE ghost X events).

[0.1.0]: https://github.com/DISSIDIA-986/VibePad/releases/tag/v0.1.0
