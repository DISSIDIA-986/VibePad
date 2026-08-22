# Gate 0 — Spike Checklist

**Status: PASSED** (2026-08-22) — see [Phase 1](../phases/PHASE1.md).

Padjutsu install failed on this machine (SDL2/CMake). **Production path: Python SDL spike + Swift `vibepad` inject.**

## Prerequisites

1. Ghostty open and focused
2. 豆包 IME enabled, **Toggle mode**, hotkey = Right Ctrl
3. Xbox Wireless Controller connected (Bluetooth)
4. Accessibility permission for Terminal / `vibepad`

## Build

```bash
cd /Users/niuyp/Documents/github.com/VibePad
swift build -c release
```

## Step 1 — Synthetic Right Ctrl (blocking)

```bash
.build/release/vibepad test rctrl
```

**Pass:** Doubao voice starts OR stops (same as physical Right Ctrl).
**Fail:** No IME reaction → try `.build/release/vibepad test rctrl` after toggling Accessibility; document result.

## Step 2 — Full mapping (spike daemon)

```bash
bin/spike-lb-watch.sh
# production: bin/install-daemon.sh
```

| Button | Expected |
|--------|----------|
| LB | Voice toggle start/stop |
| A | Enter |
| B | Ctrl+U (clear line) |
| X | ⌘Enter |
| Y | Backspace |
| **Menu (Start)** | **Focus Ghostty** (when another app stole focus) |
| Left stick | Move cursor (fine-tune click target) |

## Pass criteria (grilling Q10)

1. LB: 10 toggles, 0 missed, 0 double-fire
2. All buttons correct in real Vibe Coding flow in Ghostty
3. Focus lost → Menu (Start) activates Ghostty; left stick moves cursor across displays

## Production install (Phase 1)

```bash
bin/install-daemon.sh
tail -f /tmp/spike-lb-toggle.log
```

If Swift synthetic keys fail, install SDL2 then padjutsu:

```bash
brew install sdl2 cmake
cargo install --git https://github.com/IlyaGulya/padjutsu.git padjutsud
```

Use `spike/gate0-padjutsu.yaml` → `padjutsud run --workspace spike`

## Bridge spike (recommended — Codex plan)

**padjutsu SDL input + vibepad `flagsChanged` output.** Avoids enigo `KeyTap rctrl` which may not toggle Doubao reliably.

**Important finding:** `/tmp/vibepad-inject.log` entries so far came from **manual CLI tests** (`vibepad inject-rctrl`), not from Xbox buttons. Padjutsu logs show zero `ACTION: Shell` on button press. Fix input path first.

### Direct LB spike (input-first — use this now)

Bypass padjutsu. Single Python daemon: SDL reads LB → `inject-rctrl.sh`.

```bash
bin/spike-lb-run.sh          # start daemon
bin/diagnose-buttons.sh 45   # 45s hardware test (press LB/A/RB during countdown)
tail -f /tmp/spike-lb-toggle.log
```

**Pass:** log shows `DOWN LB` then `ACTION inject-rctrl`; Doubao toggles in Ghostty.

```bash
chmod +x bin/*.sh
bin/spike-bridge-run.sh
```

| Piece | Role |
|-------|------|
| `spike/bridge/gc_profile.yaml` | LB → `bin/inject-rctrl.sh` |
| `vibepad inject-rctrl` | Debounced CGEvent flagsChanged Right Ctrl |
| `/tmp/vibepad-inject.log` | Inject audit log |

**Manual inject test:**

```bash
.build/release/vibepad inject-rctrl
```

**Optional launchd (keep padjutsu alive):**

```bash
cp config/launchd/dev.vibepad.padjutsu-bridge.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.vibepad.padjutsu-bridge.plist
launchctl kickstart -k gui/$(id -u)/dev.vibepad.padjutsu-bridge
```

**Pass:** LB toggles Doubao voice start/stop in Ghostty; `/tmp/padjutsu-bridge.log` shows `ACTION: Shell` on press; `/tmp/vibepad-inject.log` shows `ok`.
