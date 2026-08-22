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
VIBEPAD = os.path.join(REPO, ".build/release/vibepad")
DEBOUNCE_S = 0.15
DEBOUNCE_B_S = 0.80
DEBOUNCE_X_S = 0.40
DEBOUNCE_LB_S = 0.30
HEARTBEAT_S = 30
POLL_BUTTONS = {9}  # LB: poll (BLE misses events)
POLL_A_BUTTON = 0
A_DEBOUNCE_S = 0.12

# X: BLE ghosts cmd+enter when right stick moves — fire on release + cooldown.
FIRE_ON_RELEASE = {1, 2}
RSTICK_X_COOLDOWN_S = 2.0

RIGHT_STICK_GUARD = 0.20
# Right stick Y → scroll wheel in Ghostty (X button still on release + cooldown).
RSTICK_SCROLL_MAX_LINES_S = 90.0
GHOSTTY_BUNDLE = "com.mitchellh.ghostty"

SDL_AXIS_RIGHTX = 2
SDL_AXIS_RIGHTY = 3

# Left stick → mouse (matches config/default.yaml)
STICK_DEADZONE = 0.18
STICK_GAMMA = 2.0
STICK_MAX_SPEED_PX_S = 2400.0
POLL_HZ = 100.0  # ~time.sleep(0.01)

SDL_AXIS_LEFTX = 0
SDL_AXIS_LEFTY = 1

# SDL button id → (label, shell command argv)
BUTTON_MAP: dict[int, tuple[str, list[str]]] = {
    9: ("LB", [INJECT_RCTRL]),              # Doubao voice toggle
    1: ("B", [INJECT_KEY, "ctrl+u"]),
    2: ("X", [INJECT_KEY, "cmd+enter"]),
    3: ("Y", [INJECT_KEY, "backspace"]),
    6: ("START", [FOCUS_GHOSTTY]),          # Menu — focus Ghostty
}

# D-pad ←/→ : Ghostty previous_tab / next_tab (⌘⇧[ / ⌘⇧]) — poll only, once per press.
DPAD_TAB_BUTTONS: dict[int, tuple[str, list[str]]] = {
    13: ("DPAD-L", [INJECT_KEY, "cmd+shift+openbracket"]),
    14: ("DPAD-R", [INJECT_KEY, "cmd+shift+closebracket"]),
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
kCGScrollEventUnitLine = 1
kCGAnnotatedSessionEventTap = 2
kVK_Return = 0x24
kCGHIDEventTap = 0
CURSOR_MARGIN = 4.0  # keep pointer inside menu-bar / dock inset


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


_CG = None
_CURSOR_BOUNDS: tuple[float, float, float, float] | None = None
_FRONTMOST_CACHE: dict[str, float | str] = {"bundle": "", "at": 0.0}
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


def is_ghostty_focused() -> bool:
    now = time.monotonic()
    if now - float(_FRONTMOST_CACHE["at"]) < 0.25:
        return _FRONTMOST_CACHE["bundle"] == GHOSTTY_BUNDLE
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
    return bundle == GHOSTTY_BUNDLE


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
    *,
    last_rstick_active_at: float = 0.0,
) -> None:
    if btn not in BUTTON_MAP:
        return
    label, argv = BUTTON_MAP[btn]
    now = time.monotonic()
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

    if btn in FIRE_ON_RELEASE:
        if edge != "UP":
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
    """A → Enter via poll edge (BLE-friendly) + inline CGEvent."""
    pressed = bool(sdl.SDL_GameControllerGetButton(gc, POLL_A_BUTTON))
    if pressed and not prev_a:
        now = time.monotonic()
        if now - last_a_at[0] >= A_DEBOUNCE_S:
            last_a_at[0] = now
            log("POLL A → enter")
            threading.Thread(target=tap_enter, daemon=True).start()
    return pressed


def poll_dpad_tabs(
    sdl,
    gc,
    prev_dpad: dict[int, bool],
    dpad_latched: set[int],
) -> None:
    """One tab switch per physical d-pad press (poll only — no hat/event duplicate)."""
    for btn, (label, argv) in DPAD_TAB_BUTTONS.items():
        pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
        if pressed:
            if btn not in dpad_latched:
                dpad_latched.add(btn)
                log(f"DPAD {label}")
                run_action(label, argv)
        else:
            dpad_latched.discard(btn)
        prev_dpad[btn] = pressed


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
    for btn, (label, argv) in BUTTON_MAP.items():
        action = argv[-1] if argv[-1] != INJECT_RCTRL else "rctrl"
        if label == "START":
            action = "focus-ghostty"
        log(f"  {label} → {action}")
    log("  A → enter (poll+inline CGEvent)")
    for _btn, (label, argv) in DPAD_TAB_BUTTONS.items():
        log(f"  {label} → {argv[-1]} (Ghostty tab, once/press)")
    log(f"  L-stick → mouse (deadzone={STICK_DEADZONE}, max={int(STICK_MAX_SPEED_PX_S)}px/s, multi-display)")
    log(f"  R-stick → scroll Ghostty (max={int(RSTICK_SCROLL_MAX_LINES_S)} lines/s; X btn unchanged)")


def fresh_input_state() -> dict:
    return {
        "last_action": {},
        "b_down_at": {},
        "press_latched": set(),
        "last_rstick_active_at": 0.0,
        "prev_poll": {btn: False for btn in POLL_BUTTONS},
        "prev_dpad": {btn: False for btn in DPAD_TAB_BUTTONS},
        "dpad_latched": set(),
        "prev_a": False,
        "last_a_at": [0.0],
    }


def sync_pressed_state(sdl, gc, state: dict) -> None:
    """After reconnect, match poll edges to physical state — avoid ghost fire."""
    for btn in POLL_BUTTONS:
        state["prev_poll"][btn] = bool(sdl.SDL_GameControllerGetButton(gc, btn))
    state["prev_a"] = bool(sdl.SDL_GameControllerGetButton(gc, POLL_A_BUTTON))
    for btn in DPAD_TAB_BUTTONS:
        pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
        state["prev_dpad"][btn] = pressed
        if pressed:
            state["dpad_latched"].add(btn)
        else:
            state["dpad_latched"].discard(btn)
    state["press_latched"].clear()
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
        for btn, (label, _) in BUTTON_MAP.items():
            if sdl.SDL_GameControllerGetButton(gc, btn):
                log(f"WARN {label} held at startup — release before testing")

    log("ready — A=poll enter, D-pad=tabs, L-stick=mouse; hot-reconnect enabled")

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
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
            elif et == SDL_CONTROLLERBUTTONUP:
                btn = event.padding[8]
                if btn in POLL_BUTTONS:
                    continue
                try_fire_button(
                    btn, "UP", state["last_action"], state["b_down_at"], state["press_latched"],
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
        state["prev_a"] = poll_a_enter(sdl, gc, state["prev_a"], state["last_a_at"])

        for btn in POLL_BUTTONS:
            pressed = bool(sdl.SDL_GameControllerGetButton(gc, btn))
            if pressed and not state["prev_poll"][btn]:
                try_fire_button(
                    btn, "DOWN", state["last_action"], state["b_down_at"], state["press_latched"],
                    last_rstick_active_at=state["last_rstick_active_at"],
                )
            elif not pressed and state["prev_poll"][btn]:
                state["press_latched"].discard(btn)
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

        if is_ghostty_focused():
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
