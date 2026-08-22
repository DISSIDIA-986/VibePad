# VibePad

**Xbox controller → Ghostty terminal Vibe Coding on macOS** — lie down, keep coding.

Xbox 蓝牙手柄驱动 Ghostty + 豆包 IME，躺在床上做 Vibe Coding（Claude Code / Cursor CLI / Codex CLI）。

[![Release](https://img.shields.io/github/v/release/DISSIDIA-986/VibePad)](https://github.com/DISSIDIA-986/VibePad/releases)
**Repo:** https://github.com/DISSIDIA-986/VibePad · **Latest:** v0.1.2

---

## What it does

VibePad maps an **Xbox Bluetooth controller** to keyboard, mouse, and scroll input while you use **Ghostty** with **Doubao IME** (豆包, Right Ctrl voice toggle).

Built for **agent-style terminal workflows**: send prompts, clear the input line, switch tabs, move the cursor across monitors, scroll long CLI output — without a desk setup.

```
Xbox Controller (Bluetooth)
  → Python SDL daemon (production)
  → Swift vibepad / osascript inject
  → Ghostty + Doubao IME
```

Runs **headless** via `launchd` after one-time install — no Terminal window left open.

---

## Controller mapping (verified v0.1.1)

| Input | Action | Notes |
|-------|--------|-------|
| **LB** | Doubao voice toggle | Synthetic Right Ctrl (`flagsChanged`) |
| **A** | Enter / send | Optimized for agent input box |
| **B** | Ctrl+U | Clear current input line |
| **X** | ⌘Enter | Fires on **release**; Ghostty fullscreen |
| **Y** | Backspace | Delete character |
| **Menu (Start)** | Focus Ghostty | When another app stole focus |
| **D-pad ← / →** | Previous / next tab | ⌘⇧[ / ⌘⇧] |
| **Left stick** | Mouse move | Union of all displays (multi-monitor) |
| **Right stick ↑ / ↓** | Terminal scroll | Ghostty focused only; scrollback / latest output |

### Also included (v0.1.1)

- **Bluetooth hot-reconnect** — power off the controller to save battery; mappings resume after reconnect (no manual restart).
- **Singleton daemon** — one spike process; duplicate watch scripts are blocked.
- **VibePad.app** (experimental) — menu-bar status + optional GameController path (production stack remains Python SDL spike).

### Not mapped (yet)

| Input | Status |
|-------|--------|
| RB, LT, RT | Unassigned |
| D-pad ↑ / ↓ | Unassigned |
| Right stick ← / → | Unassigned (Y-axis scroll only) |

---

## Quick start

```bash
git clone https://github.com/DISSIDIA-986/VibePad.git
cd VibePad

brew install sdl2
swift build -c release

bin/install-daemon.sh      # launchd — recommended
bin/status-daemon.sh       # verify running
.build/release/vibepad doctor
```

**Accessibility** (System Settings → Privacy → Accessibility): grant **python3** and **vibepad** (`.build/release/vibepad`).

**Doubao IME:** Toggle mode, hotkey = Right Ctrl. Test with LB in Ghostty.

```bash
bin/restart-daemon.sh      # manual relaunch if needed
tail -f /tmp/spike-lb-toggle.log
```

Menu-bar app (optional): `bin/build-app.sh && open VibePad.app`

---

## Requirements

| Item | Detail |
|------|--------|
| macOS | 14+ (tested on macOS 27 beta, Mac Studio) |
| Controller | Xbox Series X\|S / Xbox One via **Bluetooth** (USB not tested) |
| Terminal | [Ghostty](https://ghostty.org) |
| IME | Doubao (豆包), Toggle + Right Ctrl |
| Dependencies | Homebrew `sdl2`, Swift 5.9+ toolchain, Python 3 |

---

## Architecture

| Component | Role |
|-----------|------|
| `bin/spike-lb-toggle.py` | Production input — SDL2 poll, BLE-friendly edge detection |
| `.build/release/vibepad` | CGEvent inject (Right Ctrl, keys, mouse) |
| `bin/inject-key.sh` | osascript for ⌘ combos (avoids bare-key leaks) |
| `bin/install-daemon.sh` | User launchd agent, Application Support install path |
| `Sources/VibePadCore/` | Swift library — inject, config, mouse engine |
| `VibePad.app` | Experimental menu-bar shell (not production input yet) |

---

## Known limitations

- **Production path is Python SDL spike**, not `vibepad run` / GameController CLI (GC returns 0 controllers in CLI on test hardware).
- **YAML config** (`config/default.yaml`) does not yet list all spike mappings (LB, Menu, D-pad are spike-only).
- **Right-stick scroll** only when Ghostty is the frontmost app.
- **X button** may ghost on BLE when moving right stick — mitigated with release-to-fire + cooldown.
- **VibePad.app** does not replace the spike daemon for daily use yet.

---

## Development

```bash
swift test                 # unit tests (VibePadCore)
bin/spike-lb-watch.sh      # foreground dev (blocked if launchd already runs)
bin/build-icon.sh          # rebuild AppIcon.icns from icon-1024.png
```

Docs: [Gate 0 checklist](docs/spike/GATE0.md) · [Phase 1 roadmap](docs/phases/PHASE1.md) · [Status](docs/STATUS.md) · [Tasks](docs/TASKS.md) · [Changelog](CHANGELOG.md)

Design notes: [docs/designs/vibepad.md](docs/designs/vibepad.md)

---

## Use case (why this exists)

**Vibe Coding from bed:** external displays (including AR glasses), Xbox controller in hand, Ghostty running Claude Code / Cursor CLI / Codex — voice input via Doubao, send with A, clear mistakes with B/Y, switch agent tabs with D-pad, point with left stick, scroll agent output with right stick.

Gate 0 passed · Phase 1 production daemon shipped · soak testing in progress.
