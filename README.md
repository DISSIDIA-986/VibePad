# VibePad

Xbox 蓝牙手柄 → Ghostty + 豆包 IME（Toggle 语音）。Swift 注入 + SDL spike daemon，YAML 配置。

## Gate 0 — passed ✅

```bash
bin/install-daemon.sh      # launchd (recommended — no Terminal window)
bin/status-daemon.sh
bin/restart-daemon.sh   # if buttons die after BT reconnect (should auto-recover now)
.build/release/vibepad doctor
```

Dev foreground: `bin/spike-lb-watch.sh` (blocked if launchd already runs; use `--replace` to force)

Logs: `/tmp/spike-lb-toggle.log`

Next: [docs/phases/PHASE1.md](docs/phases/PHASE1.md)

Menu-bar app (experimental): `bin/build-app.sh && open VibePad.app`

**Status / tasks:** [docs/STATUS.md](docs/STATUS.md) · [docs/TASKS.md](docs/TASKS.md)

**Changelog:** [CHANGELOG.md](CHANGELOG.md) (v0.1.1)

## Default mapping (Ghostty agent / shell)

| Button | Action |
|--------|--------|
| LB | Voice toggle (`rctrl`) |
| A | Enter |
| B | Ctrl+U (clear line) |
| X | ⌘Enter |
| Y | Backspace |
| Menu (Start) | Focus Ghostty |
| D-pad ← / → | Previous / next **tab** (⌘⇧[ / ⌘⇧]) |
| Left stick | Mouse move (multi-display) |
| Right stick | Scroll Ghostty terminal (↑ history / ↓ latest) |

## Build & doctor

```bash
swift build -c release
.build/release/vibepad doctor
.build/release/vibepad test rctrl    # Ghostty focused + 豆包 IME Toggle
```

Full spike checklist: [docs/spike/GATE0.md](docs/spike/GATE0.md)

Design: [docs/designs/vibepad.md](docs/designs/vibepad.md)

## Requirements

- macOS 14+ (GoldenGate Beta tested)
- Accessibility permission (`python3` + `vibepad` when using spike daemon)
- Xbox controller via Bluetooth
- SDL2: `brew install sdl2`

## Tests

```bash
swift test
```
