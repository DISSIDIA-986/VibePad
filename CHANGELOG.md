# Changelog

All notable changes to VibePad are documented here.

## [0.1.2] — 2026-08-22

### Added

- **macOS app icon** — `AppIcon.icns` bundled in `VibePad.app`; source PNG at `config/VibePadApp/icon-1024.png`.
- `bin/build-icon.sh` — regenerate icns from 1024×1024 PNG.

### Changed

- **README** rewritten for accuracy (full mapping table, architecture, limitations, LinkedIn-ready use case).

## [0.1.1] — 2026-08-22

### What you can do now

- **Turn the Xbox off to save battery** — Bluetooth reconnect is automatic; buttons work again without restarting Terminal or VibePad.app.
- **Scroll Ghostty terminal with the right stick** — push down toward latest CLI output, up for scrollback (Claude Code / Cursor CLI / Codex sessions).
- **Recover manually** if needed: `bin/restart-daemon.sh` (kills stale processes before relaunch).

### Added

- SDL **hot-reconnect** — `CONTROLLERDEVICEADDED/REMOVED`, `GetAttached` poll, sync pressed state on attach (no ghost Enter/LB after reconnect).
- **Right stick → scroll wheel** in Ghostty (max ~90 lines/s; X button unchanged with release + cooldown).
- `bin/restart-daemon.sh` — safe launchd restart via singleton helpers.

### Fixed

- `restart-daemon.sh` no longer leaves orphan `spike-lb-toggle.py` processes.

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

[0.1.2]: https://github.com/DISSIDIA-986/VibePad/releases/tag/v0.1.2
[0.1.1]: https://github.com/DISSIDIA-986/VibePad/releases/tag/v0.1.1
[0.1.0]: https://github.com/DISSIDIA-986/VibePad/releases/tag/v0.1.0
