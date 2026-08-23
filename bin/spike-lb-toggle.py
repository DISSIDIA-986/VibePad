#!/usr/bin/env python3
"""Spike: Xbox → vibepad mapping (Gate 0). Keep running in a Terminal window."""
from __future__ import annotations

import ctypes
import datetime as dt
import os
import subprocess
import threading
import time

os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = "/tmp/spike-lb-toggle.log"
INJECT_RCTRL = os.path.join(REPO, "bin/inject-rctrl.sh")
INJECT_KEY = os.path.join(REPO, "bin/inject-key.sh")
FOCUS_GHOSTTY = os.path.join(REPO, "bin/focus-ghostty.sh")
FOCUS_SAFARI = os.path.join(REPO, "bin/focus-safari.sh")
VIBEPAD = os.path.join(REPO, ".build/release/vibepad")
DEBOUNCE_S = 0.15
DEBOUNCE_B_S = 0.80
DEBOUNCE_X_S = 0.40
DEBOUNCE_LB_S = 0.30
HEARTBEAT_S = 30
# LB + R3: poll (Xbox BLE often drops stick-click / shoulder SDL events).
POLL_BUTTONS = {9}  # LB only (Xbox BLE R3 often never maps in SDL)
POLL_A_BUTTON = 0
A_DEBOUNCE_S = 0.12

# X: BLE ghosts cmd+enter when right stick moves — fire on release + cooldown.
FIRE_ON_RELEASE = {1, 2}
RSTICK_X_COOLDOWN_S = 2.0

RIGHT_STICK_GUARD = 0.20
# Right stick Y → scroll wheel in Ghostty (X button still on release + cooldown).
RSTICK_SCROLL_MAX_LINES_S = 90.0
GHOSTTY_BUNDLE = "com.mitchellh.ghostty"
SAFARI_BUNDLE = "com.apple.Safari"

SDL_AXIS_RIGHTX = 2
SDL_AXIS_RIGHTY = 3
SDL_AXIS_TRIGGERLEFT = 4
SDL_AXIS_TRIGGERRIGHT = 5
TRIGGER_THRESHOLD = 0.55  # LT/RT normalized axis 0..1

# Ghostty slash-command assist (View → "/", then short slash mode).
SDL_BUTTON_BACK = 4  # Xbox View / Back
SLASH_MODE_S = 8.0
SLASH_NAV_DEADZONE = 0.40
SLASH_NAV_COOLDOWN_S = 0.20

# Ghostty choice-mode (View hold → arrows/A/B/Y Space for CLI multi-choice prompts).
# Xbox BLE often never surfaces R3 (RIGHTSTICK) to SDL; View hold is the reliable entry.
SDL_BUTTON_RIGHTSTICK = 8  # Xbox R3 (optional fallback if BLE ever maps it)
CHOICE_MODE_S = 6.0
CHOICE_NAV_DEADZONE = 0.40
CHOICE_NAV_COOLDOWN_S = 0.20
CHOICE_STICK_IGNORE_S = 0.15  # ignore stick briefly after enter (click/hold wobble)
CHOICE_R3_DEBOUNCE_S = 0.30
CHOICE_VIEW_HOLD_S = 0.50  # View hold ≥500ms toggles choice; short tap keeps slash

# Left stick → mouse (matches config/default.yaml)
STICK_DEADZONE = 0.18
STICK_GAMMA = 2.0
STICK_MAX_SPEED_PX_S = 2400.0
POLL_HZ = 100.0  # ~time.sleep(0.01)

SDL_AXIS_LEFTX = 0
SDL_AXIS_LEFTY = 1

# Global focus switchers — always active (any frontmost app).
GLOBAL_BUTTON_MAP: dict[int, tuple[str, list[str]]] = {
    6: ("START", [FOCUS_GHOSTTY]),          # Menu → Ghostty
    10: ("RB", [FOCUS_SAFARI]),             # RB → Safari
}

# Ghostty profile (exclusive with Safari).
GHOSTTY_BUTTON_MAP: dict[int, tuple[str, list[str]]] = {
    9: ("LB", [INJECT_RCTRL]),              # Doubao voice toggle
    1: ("B", [INJECT_KEY, "ctrl+u"]),
    2: ("X", [INJECT_KEY, "cmd+enter"]),
    3: ("Y", [INJECT_KEY, "backspace"]),
    # VIEW (button 4) handled specially: short tap = slash, hold = choice mode
}

# Safari video-rest profile (exclusive with Ghostty). A=space via poll; LT/RT seek.
SAFARI_BUTTON_MAP: dict[int, tuple[str, list[str]]] = {
    1: ("B", [INJECT_KEY, "cmd+openbracket"]),  # browser back
    2: ("X", ["__click__"]),                    # left click at cursor
}

SAFARI_TRIGGER_SEEK: dict[int, tuple[str, list[str]]] = {
    SDL_AXIS_TRIGGERLEFT: ("LT", [INJECT_KEY, "left"]),
    SDL_AXIS_TRIGGERRIGHT: ("RT", [INJECT_KEY, "right"]),
}

# D-pad ←/→ : Ghostty previous_tab / next_tab (⌘⇧[ / ⌘⇧]) — poll only, once per press.
DPAD_TAB_BUTTONS: dict[int, tuple[str, list[str]]] = {
    13: ("DPAD-L", [INJECT_KEY, "cmd+shift+openbracket"]),
    14: ("DPAD-R", [INJECT_KEY, "cmd+shift+closebracket"]),
}

# D-pad ↑/↓ : Ghostty font size (⌘= / ⌘-) — poll only, Ghostty focused, once per press.
DPAD_ZOOM_BUTTONS: dict[int, tuple[str, list[str]]] = {
    11: ("DPAD-U", [INJECT_KEY, "cmd+equal"]),
    12: ("DPAD-D", [INJECT_KEY, "cmd+minus"]),
}

SDL_INIT_GAMECONTROLLER = 0x00002000
SDL_INIT_JOYSTICK = 0x00000200
SDL_INIT_EVENTS = 0x00004000
SDL_CONTROLLERAXISMOTION = 0x650
SDL_CONTROLLERBUTTONDOWN = 0x651
SDL_CONTROLLERBUTTONUP = 0x652
SDL_CONTROLLERDEVICEADDED = 0x653
SDL_CONTROLLERDEVICEREMOVED = 0x654

kCGEventMouseMoved = 5
kCGEventLeftMouseDown = 1
kCGEventLeftMouseUp = 2
kCGScrollEventUnitLine = 1
kCGAnnotatedSessionEventTap = 2
kVK_Return = 0x24
kVK_Space = 0x31
kCGHIDEventTap = 0
CURSOR_MARGIN = 4.0  # keep pointer inside menu-bar / dock inset


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


_CG = None
_CURSOR_BOUNDS: tuple[float, float, float, float] | None = None
_FRONTMOST_CACHE: dict[str, float | str] = {"bundle": "", "at": 0.0}
_SLASH_UNTIL = 0.0  # monotonic deadline; 0 = inactive
_CHOICE_UNTIL = 0.0  # monotonic deadline; 0 = inactive
_CHOICE_STICK_IGNORE_UNTIL = 0.0
_CHOICE_R3_LAST_AT = 0.0
_BTN_MODE_AT_PRESS: dict[int, str] = {}  # btn -> mode name locked at DOWN
_SLASH_ARM_GEN = 0  # bumped to cancel in-flight View→slash workers
_VIEW_DOWN_AT = 0.0  # monotonic; 0 = View not held for pending short/hold resolve
_VIEW_HOLD_FIRED = False  # True if hold already toggled choice (suppress slash on UP)
SCREEN_BOUNDS_SCRIPT = os.path.join(REPO, "bin/screen-visible-frame.swift")


def log(msg: str) -> None:
    line = f"[{dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def run_cf_loop(seconds: float = 0.2) -> None:
    core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    kCFRunLoopDefaultMode = ctypes.c_void_p.in_dll(core, "kCFRunLoopDefaultMode")
    core.CFRunLoopRunInMode.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_bool]
    core.CFRunLoopRunInMode.restype = ctypes.c_int32
    core.CFRunLoopRunInMode(kCFRunLoopDefaultMode, seconds, False)


class SDL_Event(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("padding", ctypes.c_byte * 128)]


def load_sdl():
    sdl = ctypes.CDLL("/opt/homebrew/lib/libSDL2.dylib")
    sdl.SDL_SetHint.restype = ctypes.c_bool
    sdl.SDL_SetHint.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    sdl.SDL_Init.restype = ctypes.c_int
    sdl.SDL_Init.argtypes = [ctypes.c_uint32]
    sdl.SDL_GetError.restype = ctypes.c_char_p
    sdl.SDL_NumJoysticks.restype = ctypes.c_int
    sdl.SDL_IsGameController.restype = ctypes.c_bool
    sdl.SDL_IsGameController.argtypes = [ctypes.c_int]
    sdl.SDL_GameControllerOpen.restype = ctypes.c_void_p
    sdl.SDL_GameControllerOpen.argtypes = [ctypes.c_int]
    sdl.SDL_GameControllerName.restype = ctypes.c_char_p
    sdl.SDL_GameControllerName.argtypes = [ctypes.c_void_p]
    sdl.SDL_GameControllerGetButton.restype = ctypes.c_uint8
    sdl.SDL_GameControllerGetButton.argtypes = [ctypes.c_void_p, ctypes.c_int]
    sdl.SDL_GameControllerGetAxis.restype = ctypes.c_int16
    sdl.SDL_GameControllerGetAxis.argtypes = [ctypes.c_void_p, ctypes.c_int]
    sdl.SDL_GameControllerClose.restype = None
    sdl.SDL_GameControllerClose.argtypes = [ctypes.c_void_p]
    sdl.SDL_GameControllerGetAttached.restype = ctypes.c_bool
    sdl.SDL_GameControllerGetAttached.argtypes = [ctypes.c_void_p]
    sdl.SDL_PollEvent.restype = ctypes.c_bool
    sdl.SDL_PollEvent.argtypes = [ctypes.c_void_p]
    sdl.SDL_PumpEvents.restype = None
    return sdl


def load_cg():
    global _CG
    if _CG is not None:
        return _CG
    cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    cg.CGEventCreate.restype = ctypes.c_void_p
    cg.CGEventCreate.argtypes = [ctypes.c_void_p]
    cg.CGEventGetLocation.restype = CGPoint
    cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
    cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    cg.CGEventPost.restype = None
    cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cg.CGEventSourceCreate.restype = ctypes.c_void_p
    cg.CGEventSourceCreate.argtypes = [ctypes.c_int32]
    cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    cg.CGEventCreateKeyboardEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_bool,
    ]
    cg.CGEventCreateScrollWheelEvent.restype = ctypes.c_void_p
    cg.CGEventCreateScrollWheelEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_int32,
    ]
    cg.CGEventKeyboardSetUnicodeString.restype = None
    cg.CGEventKeyboardSetUnicodeString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,  # UniCharCount
        ctypes.c_void_p,  # const UniChar*
    ]
    _CG = cg
    return _CG


def tap_enter() -> None:
    """Inline Enter — annotated session tap (IME / Ghostty agent input)."""
    cg = load_cg()
    src = cg.CGEventSourceCreate(0)  # combinedSessionState
    for down in (True, False):
        ev = cg.CGEventCreateKeyboardEvent(src, kVK_Return, down)
        if not ev:
            log("  err: enter event create failed")
            return
        cg.CGEventPost(kCGAnnotatedSessionEventTap, ev)
        if down:
            time.sleep(0.006)


def tap_unicode(ch: str) -> None:
    """Insert literal Unicode (bypasses Chinese IME — e.g. '/' not '、')."""
    if not ch:
        return
    cg = load_cg()
    buf = (ctypes.c_uint16 * len(ch))(*(ord(c) for c in ch))
    for down in (True, False):
        # keycode 0 + unicode string → character insert, not physical key via IME
        ev = cg.CGEventCreateKeyboardEvent(None, 0, down)
        if not ev:
            log("  err: unicode event create failed")
            return
        cg.CGEventKeyboardSetUnicodeString(ev, len(ch), ctypes.byref(buf))
        cg.CGEventPost(kCGHIDEventTap, ev)
        if down:
            time.sleep(0.008)


def tap_slash() -> None:
    """ASCII slash for CLI menus — must not go through IME as '、'."""
    tap_unicode("/")


def tap_space() -> None:
    """Space — Safari play/pause."""
    cg = load_cg()
    src_ev = cg.CGEventSourceCreate(0)
    for down in (True, False):
        ev = cg.CGEventCreateKeyboardEvent(src_ev, kVK_Space, down)
        if not ev:
            log("  err: space event create failed")
            return
        cg.CGEventPost(kCGAnnotatedSessionEventTap, ev)
        if down:
            time.sleep(0.006)


def click_mouse() -> None:
    """Left click at current cursor (Safari UI)."""
    cg = load_cg()
    ev = cg.CGEventCreate(None)
    loc = cg.CGEventGetLocation(ev)
    for etype in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        click = cg.CGEventCreateMouseEvent(None, etype, loc, 0)
        if not click:
            log("  err: click event create failed")
            return
        cg.CGEventPost(kCGHIDEventTap, click)
        time.sleep(0.01)


def refresh_desktop_bounds(force: bool = False) -> tuple[float, float, float, float]:
    """Bounding box of all displays' visible frames (macOS global desktop coords)."""
    global _CURSOR_BOUNDS
    if _CURSOR_BOUNDS is not None and not force:
        return _CURSOR_BOUNDS
    try:
        out = subprocess.run(
            ["/usr/bin/swift", SCREEN_BOUNDS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        parts = out.stdout.strip().split()
        if len(parts) != 5:
            raise ValueError(f"unexpected bounds: {out.stdout!r}")
        screen_count = int(parts[0])
        _CURSOR_BOUNDS = tuple(float(p) for p in parts[1:])  # type: ignore[assignment]
        log(
            f"desktop bounds ({screen_count} screens) "
            f"x={_CURSOR_BOUNDS[0]:.0f} y={_CURSOR_BOUNDS[1]:.0f} "
            f"w={_CURSOR_BOUNDS[2]:.0f} h={_CURSOR_BOUNDS[3]:.0f}"
        )
    except Exception as exc:
        if _CURSOR_BOUNDS is None:
            _CURSOR_BOUNDS = (0.0, 0.0, 2560.0, 1440.0)
            log(f"WARN desktop bounds fallback ({exc})")
    return _CURSOR_BOUNDS


def clamp_cursor(x: float, y: float, bounds: tuple[float, float, float, float]) -> CGPoint:
    fx, fy, fw, fh = bounds
    m = CURSOR_MARGIN
    cx = max(fx + m, min(fx + fw - m, x))
    cy = max(fy + m, min(fy + fh - m, y))
    return CGPoint(cx, cy)


def axis_delta(axis: float) -> float:
    magnitude = abs(axis)
    if magnitude <= STICK_DEADZONE:
        return 0.0
    normalized = (magnitude - STICK_DEADZONE) / (1.0 - STICK_DEADZONE)
    speed = STICK_MAX_SPEED_PX_S * (normalized ** STICK_GAMMA) * (1.0 if axis >= 0 else -1.0)
    return speed / POLL_HZ


def scroll_lines_delta(axis: float) -> int:
    magnitude = abs(axis)
    if magnitude <= STICK_DEADZONE:
        return 0
    normalized = (magnitude - STICK_DEADZONE) / (1.0 - STICK_DEADZONE)
    lines_per_s = RSTICK_SCROLL_MAX_LINES_S * (normalized ** STICK_GAMMA) * (1.0 if axis >= 0 else -1)
    delta = int(round(lines_per_s / POLL_HZ))
    if delta == 0 and lines_per_s != 0:
        return 1 if lines_per_s > 0 else -1
    return delta


def invalidate_frontmost_cache() -> None:
    """Force next frontmost_bundle() to re-query (e.g. after focus switch)."""
    _FRONTMOST_CACHE["at"] = 0.0


def assume_frontmost(bundle: str) -> None:
    """Optimistically set frontmost after Menu/RB — avoids 250ms stale-profile race."""
    _FRONTMOST_CACHE["bundle"] = bundle
    _FRONTMOST_CACHE["at"] = time.monotonic()


def frontmost_bundle() -> str:
    """Cached frontmost app bundle id (~0.25s)."""
    now = time.monotonic()
    if now - float(_FRONTMOST_CACHE["at"]) < 0.25:
        return str(_FRONTMOST_CACHE["bundle"])
    bundle = ""
    try:
        out = subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                "tell application \"System Events\" to get bundle identifier of "
                "first application process whose frontmost is true",
            ],
            capture_output=True,
            text=True,
            timeout=1,
            check=True,
        )
        bundle = out.stdout.strip()
    except Exception:
        bundle = ""
    _FRONTMOST_CACHE["bundle"] = bundle
    _FRONTMOST_CACHE["at"] = now
    return bundle


def is_ghostty_focused() -> bool:
    return frontmost_bundle() == GHOSTTY_BUNDLE


def is_safari_focused() -> bool:
    return frontmost_bundle() == SAFARI_BUNDLE


def active_profile() -> str | None:
    """Mutually exclusive profile; None if frontmost app is unmapped."""
    bundle = frontmost_bundle()
    if bundle == GHOSTTY_BUNDLE:
        return "ghostty"
    if bundle == SAFARI_BUNDLE:
        return "safari"
    return None


def profile_button_map(profile: str | None) -> dict[int, tuple[str, list[str]]]:
    if profile == "ghostty":
        return GHOSTTY_BUTTON_MAP
    if profile == "safari":
        return SAFARI_BUTTON_MAP
    return {}


def slash_mode_active() -> bool:
    """True while Ghostty slash-assist window is open."""
    global _SLASH_UNTIL
    if _SLASH_UNTIL <= 0:
        return False
    if time.monotonic() >= _SLASH_UNTIL:
        _SLASH_UNTIL = 0.0
        log("SLASH mode off (timeout)")
        return False
    if not is_ghostty_focused():
        _SLASH_UNTIL = 0.0
        log("SLASH mode off (left Ghostty)")
        return False
    return True


def enter_slash_mode(*, refresh: bool = False) -> None:
    global _SLASH_UNTIL
    _SLASH_UNTIL = time.monotonic() + SLASH_MODE_S
    log(f"SLASH mode {'refreshed' if refresh else 'on'} ({SLASH_MODE_S:.0f}s)")


def exit_slash_mode(reason: str) -> None:
    global _SLASH_UNTIL
    if _SLASH_UNTIL <= 0:
        return
    _SLASH_UNTIL = 0.0
    log(f"SLASH mode off ({reason})")


def choice_mode_active() -> bool:
    """True while Ghostty choice-assist window is open."""
    global _CHOICE_UNTIL
    if _CHOICE_UNTIL <= 0:
        return False
    if time.monotonic() >= _CHOICE_UNTIL:
        _CHOICE_UNTIL = 0.0
        suppress_held_face_buttons("choice timeout")
        log("CHOICE mode off (timeout)")
        return False
    if not is_ghostty_focused():
        _CHOICE_UNTIL = 0.0
        suppress_held_face_buttons("choice left Ghostty")
        log("CHOICE mode off (left Ghostty)")
        return False
    return True


def enter_choice_mode(*, refresh: bool = False) -> None:
    global _CHOICE_UNTIL, _CHOICE_STICK_IGNORE_UNTIL
    now = time.monotonic()
    _CHOICE_UNTIL = now + CHOICE_MODE_S
    if not refresh:
        # First entry: drop slash (mutex), kill pending View→/, ignore R3 stick wobble.
        cancel_pending_slash_arm("choice enter")
        if slash_mode_active():
            exit_slash_mode("choice enter")
        suppress_held_face_buttons("choice enter")
        _CHOICE_STICK_IGNORE_UNTIL = now + CHOICE_STICK_IGNORE_S
    log(f"CHOICE mode {'refreshed' if refresh else 'on'} ({CHOICE_MODE_S:.0f}s)")


def exit_choice_mode(reason: str) -> None:
    global _CHOICE_UNTIL
    if _CHOICE_UNTIL <= 0:
        return
    _CHOICE_UNTIL = 0.0
    suppress_held_face_buttons(f"choice exit:{reason}")
    log(f"CHOICE mode off ({reason})")


def suppress_held_face_buttons(reason: str) -> None:
    """Cancel in-flight B/X/Y so UP cannot leak Ctrl+U / Cmd+Enter / Esc across mode flips."""
    for btn in (1, 2, 3):
        if btn in _BTN_MODE_AT_PRESS and _BTN_MODE_AT_PRESS[btn] != "suppress":
            _BTN_MODE_AT_PRESS[btn] = "suppress"
            log(f"BTN {btn} suppress ({reason})")


def cancel_pending_slash_arm(reason: str) -> None:
    """Invalidate View→slash workers that have not typed '/' yet."""
    global _SLASH_ARM_GEN
    _SLASH_ARM_GEN += 1
    log(f"SLASH arm canceled ({reason}) gen={_SLASH_ARM_GEN}")



def scroll_wheel(lines: int) -> None:
    if lines == 0:
        return
    cg = load_cg()
    src = cg.CGEventSourceCreate(0)
    ev = cg.CGEventCreateScrollWheelEvent(src, kCGScrollEventUnitLine, 1, lines)
    if not ev:
        return
    cg.CGEventPost(kCGHIDEventTap, ev)


def move_mouse(dx: int, dy: int, bounds: tuple[float, float, float, float]) -> None:
    if dx == 0 and dy == 0:
        return
    cg = load_cg()
    ev = cg.CGEventCreate(None)
    loc = cg.CGEventGetLocation(ev)
    new_loc = clamp_cursor(loc.x + dx, loc.y + dy, bounds)
    if abs(new_loc.x - loc.x) < 0.5 and abs(new_loc.y - loc.y) < 0.5:
        return
    move_ev = cg.CGEventCreateMouseEvent(None, kCGEventMouseMoved, new_loc, 0)
    cg.CGEventPost(kCGHIDEventTap, move_ev)


def run_action(label: str, argv: list[str]) -> None:
    if argv == ["__click__"]:
        log(f"ACTION {label} → click")
        threading.Thread(target=click_mouse, daemon=True).start()
        return
    if argv == ["__slash__"]:
        # Choice mode: View exits choice only (never type "/").
        if choice_mode_active():
            log(f"ACTION {label} → exit choice (View)")
            exit_choice_mode("View")
            return
        # View toggle: off → type "/" + enter mode; on → Esc + leave mode.
        if slash_mode_active():
            log(f"ACTION {label} → escape (View toggle off)")
            exit_slash_mode("View toggle")
            threading.Thread(
                target=lambda: subprocess.run(
                    [INJECT_KEY, "escape"],
                    check=False,
                    timeout=3,
                    capture_output=True,
                    text=True,
                ),
                daemon=True,
            ).start()
            return
        log(f"ACTION {label} → / + slash-mode (unicode, IME-safe)")
        global _SLASH_ARM_GEN
        _SLASH_ARM_GEN += 1
        armed = _SLASH_ARM_GEN

        def slash_worker(arm: int = armed) -> None:
            # Abort if R3/choice (or another View) invalidated this arm before typing.
            if arm != _SLASH_ARM_GEN or choice_mode_active():
                log(f"SLASH arm {arm} aborted before /")
                return
            try:
                tap_slash()
            except Exception as exc:
                log(f"  err: {exc}")
                return
            if arm != _SLASH_ARM_GEN or choice_mode_active():
                log(f"SLASH arm {arm} aborted after / (stray slash possible)")
                return
            enter_slash_mode()

        threading.Thread(target=slash_worker, daemon=True).start()
        return
    log(f"ACTION {label} → {' '.join(os.path.basename(a) if i == 0 else a for i, a in enumerate(argv))}")

    def worker() -> None:
        try:
            result = subprocess.run(argv, check=False, timeout=3, capture_output=True, text=True)
            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    log(f"  out: {line}")
            if result.stderr:
                for line in result.stderr.strip().splitlines():
                    log(f"  err: {line}")
        except Exception as exc:
            log(f"  err: {exc}")

    threading.Thread(target=worker, daemon=True).start()


def run_focus_sync(label: str, argv: list[str]) -> bool:
    """Run focus script synchronously so frontmost matches before next key."""
    log(f"ACTION {label} → {' '.join(os.path.basename(a) if i == 0 else a for i, a in enumerate(argv))} (sync)")
    try:
        result = subprocess.run(argv, check=False, timeout=3, capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log(f"  out: {line}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                log(f"  err: {line}")
        return result.returncode == 0
    except Exception as exc:
        log(f"  err: {exc}")
        return False


# Menu/RB: Chrome CDP / automation often re-steals focus after a single activate.
FOCUS_VERIFY_ATTEMPTS = 4
FOCUS_VERIFY_GAP_S = 0.12


def focus_target_bundle(label: str) -> str:
    if label == "START":
        return GHOSTTY_BUNDLE
    if label == "RB":
        return SAFARI_BUNDLE
    return ""


def focus_and_verify(label: str, argv: list[str]) -> bool:
    """Activate target app and confirm frontmost; retry briefly against re-steal."""
    target = focus_target_bundle(label)
    if not target:
        return run_focus_sync(label, argv)

    for attempt in range(1, FOCUS_VERIFY_ATTEMPTS + 1):
        ok = run_focus_sync(label, argv)
        invalidate_frontmost_cache()
        time.sleep(FOCUS_VERIFY_GAP_S)
        invalidate_frontmost_cache()
        actual = frontmost_bundle()
        if actual == target:
            assume_frontmost(target)
            if attempt > 1:
                log(f"FOCUS ok {label} after {attempt} tries → {actual}")
            return True
        log(
            f"FOCUS miss {label} try {attempt}/{FOCUS_VERIFY_ATTEMPTS} "
            f"want={target} got={actual or '?'} script_ok={ok}"
        )
    invalidate_frontmost_cache()
    log(f"FOCUS FAILED {label} — another app may be re-stealing (e.g. Chrome CDP)")
    return False


def right_stick_deflected(sdl, gc) -> bool:
    rx = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_RIGHTX) / 32768.0
    ry = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_RIGHTY) / 32768.0
    return abs(rx) > RIGHT_STICK_GUARD or abs(ry) > RIGHT_STICK_GUARD


def try_fire_button(
    btn: int,
    edge: str,
    last_action: dict[int, float],
    b_down_at: dict[int, float],
    press_latched: set[int],
    press_profile: dict[int, str],
    *,
    last_rstick_active_at: float = 0.0,
) -> None:
    global _CHOICE_R3_LAST_AT
    # Global focus keys (Menu / RB) — sync activate + verify frontmost.
    if btn in GLOBAL_BUTTON_MAP:
        label, argv = GLOBAL_BUTTON_MAP[btn]
        now = time.monotonic()
        if edge == "UP":
            press_latched.discard(btn)
            return
        if edge != "DOWN":
            return
        if btn in press_latched:
            return
        last = last_action.get(btn, 0.0)
        if now - last < DEBOUNCE_S:
            return
        press_latched.add(btn)
        last_action[btn] = now
        log(f"EVENT DOWN {label} (global)")
        focus_and_verify(label, argv)
        return

    now = time.monotonic()

    # Lock profile at DOWN so UP uses the same mapping (Codex P2 mid-press focus switch).
    if edge == "DOWN":
        profile = active_profile()
        if profile:
            press_profile[btn] = profile
        else:
            press_profile.pop(btn, None)
        # Lock assist mode at DOWN so UP cannot leak Ctrl+U / Backspace after timeout.
        if profile == "ghostty" and btn in (1, 2, 3):
            if choice_mode_active():
                _BTN_MODE_AT_PRESS[btn] = "choice"
            elif slash_mode_active():
                _BTN_MODE_AT_PRESS[btn] = "slash"
            else:
                _BTN_MODE_AT_PRESS[btn] = "normal"
    else:
        profile = press_profile.pop(btn, None) or active_profile()

    # View: short tap → slash; hold → choice (Xbox BLE R3 is unreliable).
    if btn == SDL_BUTTON_BACK:
        global _VIEW_DOWN_AT, _VIEW_HOLD_FIRED
        if edge == "DOWN":
            if profile != "ghostty":
                return
            if btn in press_latched:
                return
            last = last_action.get(btn, 0.0)
            if now - last < DEBOUNCE_S:
                return
            press_latched.add(btn)
            last_action[btn] = now
            # Already in choice: tap exits immediately (no slash).
            if choice_mode_active():
                log("EVENT DOWN VIEW → exit choice")
                exit_choice_mode("View")
                _VIEW_HOLD_FIRED = True
                _VIEW_DOWN_AT = 0.0
                return
            _VIEW_DOWN_AT = now
            _VIEW_HOLD_FIRED = False
            log("EVENT DOWN VIEW (armed short=slash / hold=choice)")
            return
        if edge == "UP":
            press_latched.discard(btn)
            if _VIEW_HOLD_FIRED:
                log("EVENT UP VIEW (hold already handled)")
                _VIEW_HOLD_FIRED = False
                _VIEW_DOWN_AT = 0.0
                return
            _VIEW_DOWN_AT = 0.0
            if profile == "ghostty":
                log("EVENT UP VIEW → slash (short tap)")
                run_action("VIEW", ["__slash__"])
            return
        return

    # R3 → optional Choice Mode fallback (Ghostty only). Not in button maps.
    if btn == SDL_BUTTON_RIGHTSTICK:
        if edge == "UP":
            press_latched.discard(btn)
            return
        if edge != "DOWN":
            return
        if profile != "ghostty":
            return
        if btn in press_latched:
            return
        if now - _CHOICE_R3_LAST_AT < CHOICE_R3_DEBOUNCE_S:
            return
        if now - last_action.get(btn, 0.0) < DEBOUNCE_S:
            return
        press_latched.add(btn)
        last_action[btn] = now
        _CHOICE_R3_LAST_AT = now
        if choice_mode_active():
            log("EVENT DOWN R3 → exit choice")
            exit_choice_mode("R3 toggle")
        else:
            log("EVENT DOWN R3 → enter choice")
            enter_choice_mode()
        return

    button_map = profile_button_map(profile)
    if btn not in button_map:
        if edge == "UP":
            press_latched.discard(btn)
            _BTN_MODE_AT_PRESS.pop(btn, None)
        return
    label, argv = button_map[btn]
    locked_mode = _BTN_MODE_AT_PRESS.get(btn, "normal")

    # Mode transition canceled this press — absorb UP/DOWN, never inject.
    if profile == "ghostty" and locked_mode == "suppress":
        if edge == "UP":
            press_latched.discard(btn)
            _BTN_MODE_AT_PRESS.pop(btn, None)
            log(f"EVENT UP {label} suppressed (mode transition)")
        elif edge == "DOWN":
            press_latched.add(btn)
        return

    # Choice mode: swallow X (avoid Cmd+Enter); Y → Space; B → Esc.
    if profile == "ghostty" and locked_mode == "choice":
        if btn == 2:  # X
            if edge == "UP":
                press_latched.discard(btn)
                _BTN_MODE_AT_PRESS.pop(btn, None)
            elif edge == "DOWN":
                press_latched.add(btn)
                log("EVENT DOWN X swallowed (choice mode)")
            return
        if btn == 3:  # Y → Space on DOWN
            if edge == "UP":
                press_latched.discard(btn)
                _BTN_MODE_AT_PRESS.pop(btn, None)
                return
            if edge != "DOWN":
                return
            if btn in press_latched:
                return
            last = last_action.get(btn, 0.0)
            if now - last < DEBOUNCE_S:
                return
            press_latched.add(btn)
            last_action[btn] = now
            log("EVENT DOWN Y → space (choice mode)")
            enter_choice_mode(refresh=True)
            run_action("Y-SPACE", [INJECT_KEY, "space"])
            return
        if btn == 1:  # B → Esc on DOWN (BLE often drops UP)
            if edge == "UP":
                press_latched.discard(btn)
                _BTN_MODE_AT_PRESS.pop(btn, None)
                return
            if edge != "DOWN":
                return
            if btn in press_latched:
                return
            last = last_action.get(btn, 0.0)
            if now - last < DEBOUNCE_B_S:
                return
            press_latched.add(btn)
            last_action[btn] = now
            log("EVENT DOWN B → escape (choice mode)")
            exit_choice_mode("B escape")
            run_action("B-ESC", [INJECT_KEY, "escape"])
            return

    # Slash mode: B cancels menu (Esc) instead of Ctrl+U.
    if profile == "ghostty" and btn == 1 and locked_mode == "slash":
        if edge == "UP":
            press_latched.discard(btn)
            _BTN_MODE_AT_PRESS.pop(btn, None)
        if edge != "UP":
            if edge == "DOWN":
                press_latched.add(btn)
            return
        held_ms = (now - b_down_at.get(btn, now)) * 1000
        if held_ms < 40:
            return
        last = last_action.get(btn, 0.0)
        if now - last < DEBOUNCE_B_S:
            return
        last_action[btn] = now
        log("EVENT UP B → escape (slash mode)")
        exit_slash_mode("B escape")
        run_action("B-ESC", [INJECT_KEY, "escape"])
        return

    if btn == 1:
        debounce = DEBOUNCE_B_S
    elif btn == 2:
        debounce = DEBOUNCE_X_S
    elif btn == 9:
        debounce = DEBOUNCE_LB_S
    else:
        debounce = DEBOUNCE_S
    last = last_action.get(btn, 0.0)

    if edge == "UP":
        press_latched.discard(btn)
        _BTN_MODE_AT_PRESS.pop(btn, None)

    # Fire on release: Ghostty B/X (BLE), Safari X click (same BLE ghost while scrolling).
    fire_on_release = (profile == "ghostty" and btn in FIRE_ON_RELEASE) or (
        profile == "safari" and btn == 2
    )
    if fire_on_release:
        if edge != "UP":
            # Still latch on DOWN so BLE repeats don't queue.
            if edge == "DOWN":
                press_latched.add(btn)
            return
        if btn == 2 and now - last_rstick_active_at < RSTICK_X_COOLDOWN_S:
            log(f"EVENT UP {label} suppressed (recent right stick)")
            return
        held_ms = (now - b_down_at.get(btn, now)) * 1000
        if held_ms < 40:
            return
        if now - last < debounce:
            return
        last_action[btn] = now
        log(f"EVENT UP {label}")
        run_action(label, argv)
        return

    if edge != "DOWN":
        return
    # BLE repeats BUTTONDOWN while held — one action per press until UP.
    if btn in press_latched:
        return
    if now - last < debounce:
        return
    press_latched.add(btn)
    last_action[btn] = now
    log(f"EVENT DOWN {label}")
    run_action(label, argv)




def poll_a_enter(
    sdl,
    gc,
    prev_a: bool,
    last_a_at: list[float],
) -> bool:
    """A → Enter (Ghostty) or Space (Safari); ignored otherwise."""
    pressed = bool(sdl.SDL_GameControllerGetButton(gc, POLL_A_BUTTON))
    if pressed and not prev_a:
        now = time.monotonic()
        if now - last_a_at[0] >= A_DEBOUNCE_S:
            profile = active_profile()
            if profile == "ghostty":
                last_a_at[0] = now
                if choice_mode_active():
                    enter_choice_mode(refresh=True)
                    log("POLL A → enter (choice refresh)")
                elif slash_mode_active():
                    exit_slash_mode("A confirm")
                    log("POLL A → enter")
                else:
                    log("POLL A → enter")
                threading.Thread(target=tap_enter, daemon=True).start()
            elif profile == "safari":
                last_a_at[0] = now
                log("POLL A → space")
                threading.Thread(target=tap_space, daemon=True).start()
    return pressed




def poll_dpad_latched(
    sdl,
    gc,
    buttons: dict[int, tuple[str, list[str]]],
    prev_dpad: dict[int, bool],
    dpad_latched: set[int],
) -> None:
    """One action per physical d-pad press (poll only — no hat/event duplicate)."""
    for btn, (label, argv) in buttons.items():
        pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
        if pressed:
            if btn not in dpad_latched:
                dpad_latched.add(btn)
                log(f"DPAD {label}")
                run_action(label, argv)
        else:
            dpad_latched.discard(btn)
        prev_dpad[btn] = pressed


def poll_dpad_tabs(
    sdl,
    gc,
    prev_dpad: dict[int, bool],
    dpad_latched: set[int],
) -> None:
    """Tab switch only when Ghostty is frontmost."""
    if choice_mode_active():
        # Latch held presses so exiting Choice mid-hold cannot fire tab switch.
        for btn in DPAD_TAB_BUTTONS:
            pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
            if pressed:
                dpad_latched.add(btn)
            else:
                dpad_latched.discard(btn)
            prev_dpad[btn] = pressed
        return
    if not is_ghostty_focused():
        for btn in DPAD_TAB_BUTTONS:
            if not bool(sdl.SDL_GameControllerGetButton(gc, btn)):
                dpad_latched.discard(btn)
                prev_dpad[btn] = False
        return
    poll_dpad_latched(sdl, gc, DPAD_TAB_BUTTONS, prev_dpad, dpad_latched)




def poll_dpad_zoom(
    sdl,
    gc,
    prev_dpad: dict[int, bool],
    dpad_latched: set[int],
) -> None:
    """Zoom in/out only when Ghostty is frontmost."""
    if choice_mode_active():
        # Latch held presses so exiting Choice mid-hold cannot fire zoom.
        for btn in DPAD_ZOOM_BUTTONS:
            pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
            if pressed:
                dpad_latched.add(btn)
            else:
                dpad_latched.discard(btn)
            prev_dpad[btn] = pressed
        return
    if not is_ghostty_focused():
        for btn in DPAD_ZOOM_BUTTONS:
            if not bool(sdl.SDL_GameControllerGetButton(gc, btn)):
                dpad_latched.discard(btn)
                prev_dpad[btn] = False
        return
    poll_dpad_latched(sdl, gc, DPAD_ZOOM_BUTTONS, prev_dpad, dpad_latched)



def poll_slash_nav(
    sdl,
    gc,
    state: dict,
) -> None:
    """In slash mode, right stick Y → ↑/↓ (menu select); else no-op here."""
    if not slash_mode_active():
        state["slash_nav_dir"] = 0
        return
    raw_ry = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_RIGHTY)
    ay = -(raw_ry / 32768.0)
    direction = 0
    if ay >= SLASH_NAV_DEADZONE:
        direction = 1  # up
    elif ay <= -SLASH_NAV_DEADZONE:
        direction = -1  # down
    now = time.monotonic()
    if direction == 0:
        state["slash_nav_dir"] = 0
        return
    last_dir = state.get("slash_nav_dir", 0)
    last_at = float(state.get("slash_nav_at", 0.0))
    if direction != last_dir or (now - last_at) >= SLASH_NAV_COOLDOWN_S:
        state["slash_nav_dir"] = direction
        state["slash_nav_at"] = now
        enter_slash_mode(refresh=True)
        key = "up" if direction > 0 else "down"
        label = "SLASH-UP" if direction > 0 else "SLASH-DOWN"
        log(f"SLASH nav {key}")
        run_action(label, [INJECT_KEY, key])


def poll_choice_nav(
    sdl,
    gc,
    state: dict,
) -> None:
    """In choice mode, right stick Y → ↑/↓; else no-op here."""
    if not choice_mode_active():
        state["choice_nav_dir"] = 0
        return
    now = time.monotonic()
    if now < _CHOICE_STICK_IGNORE_UNTIL:
        state["choice_nav_dir"] = 0
        return
    raw_ry = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_RIGHTY)
    ay = -(raw_ry / 32768.0)
    direction = 0
    if ay >= CHOICE_NAV_DEADZONE:
        direction = 1  # up
    elif ay <= -CHOICE_NAV_DEADZONE:
        direction = -1  # down
    if direction == 0:
        state["choice_nav_dir"] = 0
        return
    last_dir = state.get("choice_nav_dir", 0)
    last_at = float(state.get("choice_nav_at", 0.0))
    if direction != last_dir or (now - last_at) >= CHOICE_NAV_COOLDOWN_S:
        state["choice_nav_dir"] = direction
        state["choice_nav_at"] = now
        enter_choice_mode(refresh=True)
        key = "up" if direction > 0 else "down"
        label = "CHOICE-UP" if direction > 0 else "CHOICE-DOWN"
        log(f"CHOICE nav {key}")
        run_action(label, [INJECT_KEY, key])


def poll_safari_triggers(
    sdl,
    gc,
    prev_triggers: dict[int, bool],
    trigger_latched: set[int],
) -> None:
    """LT/RT → seek left/right when Safari is frontmost."""
    if not is_safari_focused():
        for axis in SAFARI_TRIGGER_SEEK:
            raw = sdl.SDL_GameControllerGetAxis(gc, axis)
            pressed = (raw / 32767.0) >= TRIGGER_THRESHOLD
            if not pressed:
                trigger_latched.discard(axis)
                prev_triggers[axis] = False
        return
    for axis, (label, argv) in SAFARI_TRIGGER_SEEK.items():
        raw = sdl.SDL_GameControllerGetAxis(gc, axis)
        pressed = (raw / 32767.0) >= TRIGGER_THRESHOLD
        if pressed:
            if axis not in trigger_latched:
                trigger_latched.add(axis)
                log(f"TRIGGER {label}")
                run_action(label, argv)
        else:
            trigger_latched.discard(axis)
        prev_triggers[axis] = pressed



def open_first_controller(sdl) -> ctypes.c_void_p | None:
    count = sdl.SDL_NumJoysticks()
    for index in range(count):
        if sdl.SDL_IsGameController(index):
            gc = sdl.SDL_GameControllerOpen(index)
            if gc:
                return gc
    return None


def controller_label(sdl, gc) -> str:
    name = sdl.SDL_GameControllerName(gc)
    return name.decode() if name else "controller"


def close_controller(sdl, gc) -> None:
    if gc:
        sdl.SDL_GameControllerClose(gc)


def log_mapping(sdl, gc) -> None:
    log(f"opened {controller_label(sdl, gc)}")
    log("  [global]")
    for _btn, (label, argv) in GLOBAL_BUTTON_MAP.items():
        action = "focus-ghostty" if label == "START" else "focus-safari"
        log(f"    {label} → {action}")
    log("  [ghostty]")
    for _btn, (label, argv) in GHOSTTY_BUTTON_MAP.items():
        action = argv[-1] if argv[-1] != INJECT_RCTRL else "rctrl"
        log(f"    {label} → {action}")
    log("    A → enter (poll+inline CGEvent)")
    log("    VIEW tap → slash-mode (/ on, Esc off; R-stick↑↓, A confirm, B Esc, 8s)")
    log(f"    VIEW hold ≥{CHOICE_VIEW_HOLD_S:.1f}s → choice-mode (R-stick↑↓, A confirm+refresh, B Esc, Y Space, {CHOICE_MODE_S:.0f}s; swallows X/D-pad)")
    log("    R3 → choice-mode fallback only (often missing on Xbox BLE)")
    for _btn, (label, argv) in DPAD_TAB_BUTTONS.items():
        log(f"    {label} → {argv[-1]} (tab, once/press, focused only)")
    for _btn, (label, argv) in DPAD_ZOOM_BUTTONS.items():
        log(f"    {label} → {argv[-1]} (zoom, once/press, focused only)")
    log(f"    R-stick → scroll (max={int(RSTICK_SCROLL_MAX_LINES_S)} lines/s)")
    log("  [safari]")
    log("    A → space (play/pause)")
    for _btn, (label, argv) in SAFARI_BUTTON_MAP.items():
        action = "click" if argv == ["__click__"] else argv[-1]
        log(f"    {label} → {action}")
    for _axis, (label, argv) in SAFARI_TRIGGER_SEEK.items():
        log(f"    {label} → {argv[-1]} (seek, once/press, focused only)")
    log(f"    R-stick → scroll (max={int(RSTICK_SCROLL_MAX_LINES_S)} lines/s)")
    log(f"  L-stick → mouse (deadzone={STICK_DEADZONE}, max={int(STICK_MAX_SPEED_PX_S)}px/s, multi-display)")




def fresh_input_state() -> dict:
    return {
        "last_action": {},
        "b_down_at": {},
        "press_latched": set(),
        "press_profile": {},
        "last_rstick_active_at": 0.0,
        "prev_poll": {btn: False for btn in POLL_BUTTONS},
        "prev_dpad": {
            btn: False for btn in {**DPAD_TAB_BUTTONS, **DPAD_ZOOM_BUTTONS}
        },
        "dpad_latched": set(),
        "prev_triggers": {axis: False for axis in SAFARI_TRIGGER_SEEK},
        "trigger_latched": set(),
        "prev_a": False,
        "last_a_at": [0.0],
        "slash_nav_dir": 0,
        "slash_nav_at": 0.0,
        "choice_nav_dir": 0,
        "choice_nav_at": 0.0,
    }


def sync_pressed_state(sdl, gc, state: dict) -> None:
    """After reconnect, match poll edges to physical state — avoid ghost fire."""
    for btn in POLL_BUTTONS:
        state["prev_poll"][btn] = bool(sdl.SDL_GameControllerGetButton(gc, btn))
    state["prev_a"] = bool(sdl.SDL_GameControllerGetButton(gc, POLL_A_BUTTON))
    for btn in {**DPAD_TAB_BUTTONS, **DPAD_ZOOM_BUTTONS}:
        pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
        state["prev_dpad"][btn] = pressed
        if pressed:
            state["dpad_latched"].add(btn)
        else:
            state["dpad_latched"].discard(btn)
    for axis in SAFARI_TRIGGER_SEEK:
        raw = sdl.SDL_GameControllerGetAxis(gc, axis)
        pressed = (raw / 32767.0) >= TRIGGER_THRESHOLD
        state["prev_triggers"][axis] = pressed
        if pressed:
            state["trigger_latched"].add(axis)
        else:
            state["trigger_latched"].discard(axis)
    state["press_latched"].clear()
    state["press_profile"].clear()
    state["b_down_at"].clear()


def main() -> int:
    open(LOG, "w", encoding="utf-8").close()
    log("spike gamepad mapping (Gate 0 buttons + left stick)")

    run_cf_loop()
    sdl = load_sdl()
    sdl.SDL_SetHint(b"SDL_JOYSTICK_MFI", b"0")
    sdl.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI", b"1")
    sdl.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")

    if sdl.SDL_Init(SDL_INIT_EVENTS | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) != 0:
        err = sdl.SDL_GetError()
        log(f"SDL_Init failed: {err.decode() if err else '?'}")
        return 1

    gc: ctypes.c_void_p | None = None
    if sdl.SDL_NumJoysticks() > 0:
        gc = open_first_controller(sdl)
        if not gc:
            log("GameControllerOpen failed")
            return 1
        log_mapping(sdl, gc)
    else:
        log("no controller yet — waiting for Bluetooth reconnect")

    desktop_bounds = refresh_desktop_bounds(force=True)

    event = SDL_Event()
    state = fresh_input_state()
    last_heartbeat = time.monotonic()
    last_stick_log = 0.0

    if gc:
        for btn, (label, _) in {**GLOBAL_BUTTON_MAP, **GHOSTTY_BUTTON_MAP, **SAFARI_BUTTON_MAP}.items():
            if sdl.SDL_GameControllerGetButton(gc, btn):
                log(f"WARN {label} held at startup — release before testing")

    log("ready — ghostty|safari + View tap=slash / hold=choice; hot-reconnect")

    def attach_controller(*, reason: str) -> None:
        nonlocal gc
        if gc:
            return
        gc = open_first_controller(sdl)
        if not gc:
            return
        state.clear()
        state.update(fresh_input_state())
        sync_pressed_state(sdl, gc, state)
        log_mapping(sdl, gc)
        log(f"controller ready ({reason})")

    def detach_controller(*, reason: str) -> None:
        nonlocal gc
        if not gc:
            return
        close_controller(sdl, gc)
        gc = None
        state.clear()
        state.update(fresh_input_state())
        log(f"controller disconnected ({reason}) — waiting for reconnect")

    while True:
        sdl.SDL_PumpEvents()

        while sdl.SDL_PollEvent(ctypes.byref(event)):
            et = event.type
            if et == SDL_CONTROLLERDEVICEREMOVED:
                detach_controller(reason="SDL device removed event")
            elif et == SDL_CONTROLLERDEVICEADDED:
                attach_controller(reason="SDL device added event")
            elif gc is None:
                continue
            elif et == SDL_CONTROLLERBUTTONDOWN:
                btn = event.padding[8]
                if btn in POLL_BUTTONS:
                    continue
                state["b_down_at"][btn] = time.monotonic()
                try_fire_button(
                    btn, "DOWN", state["last_action"], state["b_down_at"], state["press_latched"],
                    state["press_profile"],
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
            elif et == SDL_CONTROLLERBUTTONUP:
                btn = event.padding[8]
                if btn in POLL_BUTTONS:
                    continue
                try_fire_button(
                    btn, "UP", state["last_action"], state["b_down_at"], state["press_latched"],
                    state["press_profile"],
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
                state["b_down_at"].pop(btn, None)

        if gc is None:
            if sdl.SDL_NumJoysticks() > 0:
                attach_controller(reason="poll")
        elif not sdl.SDL_GameControllerGetAttached(gc):
            detach_controller(reason="SDL_GetAttached false")

        if gc is None:
            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_S:
                last_heartbeat = now
                log("heartbeat waiting for controller")
            time.sleep(0.05)
            continue

        if right_stick_deflected(sdl, gc):
            state["last_rstick_active_at"] = time.monotonic()

        poll_dpad_tabs(sdl, gc, state["prev_dpad"], state["dpad_latched"])
        poll_dpad_zoom(sdl, gc, state["prev_dpad"], state["dpad_latched"])
        poll_safari_triggers(sdl, gc, state["prev_triggers"], state["trigger_latched"])
        poll_slash_nav(sdl, gc, state)
        poll_choice_nav(sdl, gc, state)
        state["prev_a"] = poll_a_enter(sdl, gc, state["prev_a"], state["last_a_at"])

        # View hold → choice (poll button still down past threshold).
        global _VIEW_DOWN_AT, _VIEW_HOLD_FIRED
        if _VIEW_DOWN_AT > 0 and not _VIEW_HOLD_FIRED:
            if time.monotonic() - _VIEW_DOWN_AT >= CHOICE_VIEW_HOLD_S:
                held = bool(sdl.SDL_GameControllerGetButton(gc, SDL_BUTTON_BACK))
                if held and is_ghostty_focused():
                    _VIEW_HOLD_FIRED = True
                    _VIEW_DOWN_AT = 0.0
                    log("VIEW hold → enter choice")
                    enter_choice_mode()
                elif not held:
                    # Released between polls; short-tap path handled on UP.
                    pass

        for btn in POLL_BUTTONS:
            pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
            if pressed and not state["prev_poll"][btn]:
                state["b_down_at"][btn] = time.monotonic()
                try_fire_button(
                    btn, "DOWN", state["last_action"], state["b_down_at"], state["press_latched"],
                    state["press_profile"],
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
            elif not pressed and state["prev_poll"][btn]:
                try_fire_button(
                    btn, "UP", state["last_action"], state["b_down_at"], state["press_latched"],
                    state["press_profile"],
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
                state["press_latched"].discard(btn)
                state["b_down_at"].pop(btn, None)
            state["prev_poll"][btn] = pressed

        raw_x = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_LEFTX)
        raw_y = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_LEFTY)
        ax = raw_x / 32768.0
        ay = -(raw_y / 32768.0)
        dx = int(round(axis_delta(ax)))
        dy = int(round(axis_delta(ay)))
        if dx or dy:
            move_mouse(dx, dy, desktop_bounds)
            now = time.monotonic()
            if now - last_stick_log >= 0.5:
                last_stick_log = now
                log(f"STICK move dx={dx} dy={dy}")

        # Right stick: slash/choice arrows take over; else scroll.
        if slash_mode_active() or choice_mode_active():
            pass
        elif is_ghostty_focused() or is_safari_focused():
            raw_ry = sdl.SDL_GameControllerGetAxis(gc, SDL_AXIS_RIGHTY)
            ay = -(raw_ry / 32768.0)
            scroll_y = scroll_lines_delta(ay)
            if scroll_y:
                scroll_wheel(scroll_y)

        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_S:
            last_heartbeat = now
            desktop_bounds = refresh_desktop_bounds(force=True)
            log("heartbeat alive")
        time.sleep(0.01)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("interrupted")
        raise SystemExit(0)
