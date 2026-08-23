# VibePad — Task Tracker

**Phase:** 1 (production daemon) · **Mode:** next dev batch · **Updated:** 2026-08-22

---

## Done ✅

- [x] Gate 0 — LB/A/B/X/Y/Menu/D-pad/left stick verified in real Vibe Coding flow
- [x] Python SDL spike (`bin/spike-lb-toggle.py`) — poll fixes, multi-display mouse, D-pad latch
- [x] Swift inject (`vibepad`, `inject-rctrl.sh`, `inject-key.sh`)
- [x] launchd install (`bin/install-daemon.sh`) — Application Support path (Documents privacy fix)
- [x] Singleton daemon (`bin/daemon-singleton.sh`) — block duplicate watch; install cleans old processes
- [x] `bin/status-daemon.sh`, `bin/uninstall-daemon.sh`
- [x] `vibepad doctor` — accessibility, launchd, spike status
- [x] VibePad.app scaffold — menu bar, GC experimental daemon, dual-daemon warning
- [x] Config install → `~/Library/Application Support/VibePad/config.yaml`
- [x] Bluetooth hot-reconnect (spike SDL) — user verified 2026-08-22
- [x] Right stick → Ghostty terminal scroll — user verified 2026-08-22
- [x] `bin/restart-daemon.sh` — safe relaunch
- [x] GitHub releases v0.1.0–v0.1.2 + README infographics
- [x] macOS app icon + `assets/` marketing images
- [x] D-pad ↑/↓ → Ghostty font size zoom — user verified 2026-08-22
- [x] Ghostty View → `/` + slash-mode (R-stick↑↓ / A / B) — 2026-08-22
- [ ] User verify slash-mode in Claude Code / Cursor CLI / Codex
- [x] Safari video-rest profile scaffold (frontmost router + RB focus) — 2026-08-22
- [ ] User verify Safari mapping (A space / B back / X click / LT RT seek / scroll)

---

## Soak test 🔍

- [x] Daily bed use — LB/A/D-pad/sticks/scroll/reconnect verified
- [ ] Optional: launchd after reboot
- [ ] Log any new bugs in STATUS.md

**Soak test continues** — Python → Swift migration deferred until stable.

---

## Next dev batch 📋

> **Deferred:** Python → Swift migration — continue soak test; revisit when stable.
> **In flight:** Safari video-rest profile — user verify after `bin/restart-daemon.sh`.

### Priority 1 — GameController migration (on hold)

- [ ] Stop spike: `bin/uninstall-daemon.sh`
- [ ] Test VibePad.app → Start GameController daemon — all buttons + stick
- [ ] If GC works in app: port spike-only features (D-pad tabs, Start→focus, LB poll) into VibePadCore
- [ ] If GC fails: embed SDL2 poll inside VibePad.app (same as spike)

### Priority 2 — Config parity (Phase 1 Step 3)

- [ ] Sync `config/default.yaml` with spike: `lb`, `start`, `dpad_left`, `dpad_right` (fix `lt` → `lb`)
- [ ] Wire YAML into app daemon (replace hardcoded spike paths)

### Priority 3 — Polish

- [ ] Y hold → repeat backspace
- [ ] `vibepad doctor` — display count
- [ ] D-pad log level: stderr audit → info not err
- [ ] Singleton lockfile persistence after launchd restart

---

## Backlog (Phase 2+)

- [ ] GUI settings
- [ ] Hold-to-talk
- [ ] RB mapping
- [ ] Non-Ghostty profiles
- [ ] Drop Python spike entirely

---

## Commands cheat sheet

```bash
bin/status-daemon.sh              # health check
bin/restart-daemon.sh             # relaunch spike (after BT issues)
bin/install-daemon.sh             # (re)install launchd
bin/uninstall-daemon.sh           # stop everything
bin/build-app.sh && open VibePad.app
.build/release/vibepad doctor
tail -f /tmp/spike-lb-toggle.log
```
