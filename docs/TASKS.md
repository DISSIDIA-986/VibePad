# VibePad — Task Tracker

**Phase:** 1 (production daemon) · **Mode:** soak test · **Updated:** 2026-08-22

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
- [x] GitHub releases v0.1.0 / v0.1.1

---

## Soak test (user, few days) 🔍

- [ ] Daily use lying in bed — Ghostty agent input + voice
- [ ] Note any bugs in STATUS.md watch list
- [ ] Confirm launchd auto-starts after reboot (optional)

**If no issues → proceed to "Next dev batch" below.**

---

## Next dev batch (after soak test) 📋

### Priority 1 — GameController migration

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
