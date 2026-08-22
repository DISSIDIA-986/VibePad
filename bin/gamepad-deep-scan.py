#!/usr/bin/env python3
"""Deep SDL gamepad diagnostic for macOS 27 + Xbox BLE."""
from __future__ import annotations

import ctypes
import ctypes.util
import datetime as dt
import os
import sys
import time

os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
LOG = "/tmp/gamepad-deep-scan.log"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 20

# SDL constants
SDL_INIT_EVENTS = 0x00004000
SDL_INIT_JOYSTICK = 0x00000200
SDL_INIT_GAMECONTROLLER = 0x00002000
SDL_CONTROLLERBUTTONDOWN = 0x650
SDL_CONTROLLERBUTTONUP = 0x651
SDL_CONTROLLERAXISMOTION = 0x652
SDL_JOYDEVICEADDED = 0x600
SDL_JOYDEVICEREMOVED = 0x601
SDL_CONTROLLERDEVICEADDED = 0x653
SDL_CONTROLLERDEVICEREMOVED = 0x654
SDL_JOYBUTTONDOWN = 0x603
SDL_JOYBUTTONUP = 0x604
SDL_QUIT = 0x100


def log(msg: str) -> None:
    line = f"[{dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def run_cf_loop(seconds: float = 0.15) -> None:
    core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    kCFRunLoopDefaultMode = ctypes.c_void_p.in_dll(core, "kCFRunLoopDefaultMode")
    core.CFRunLoopRunInMode.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_bool]
    core.CFRunLoopRunInMode.restype = ctypes.c_int32
    core.CFRunLoopRunInMode(kCFRunLoopDefaultMode, seconds, False)


class SDL_Event(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("padding", ctypes.c_byte * 128)]


def main() -> int:
    open(LOG, "w").close()
    log(f"deep-scan start duration={DURATION}s")

    # System info
    import subprocess

    ver = subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip()
    build = subprocess.check_output(["sw_vers", "-buildVersion"], text=True).strip()
    log(f"macOS {ver} ({build})")

    bt = subprocess.check_output(
        ["system_profiler", "SPBluetoothDataType"], text=True, stderr=subprocess.DEVNULL
    )
    for line in bt.splitlines():
        if "Xbox" in line or "Firmware Version" in line and "5." in line:
            log(f"bluetooth: {line.strip()}")

    log("CFRunLoop warm-up (SDL #11742 workaround)...")
    run_cf_loop(0.2)

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
    sdl.SDL_PollEvent.restype = ctypes.c_bool
    sdl.SDL_PollEvent.argtypes = [ctypes.c_void_p]
    sdl.SDL_PumpEvents.restype = None
    sdl.SDL_GameControllerUpdate.restype = None
    sdl.SDL_GameControllerUpdate.argtypes = [ctypes.c_void_p]

    sdl.SDL_SetHint(b"SDL_JOYSTICK_MFI", b"0")
    sdl.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI", b"1")
    sdl.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
    sdl.SDL_SetHint(b"SDL_GAMECONTROLLER_USE_BUTTON_LABELS", b"0")

    if sdl.SDL_Init(SDL_INIT_EVENTS | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) != 0:
        err = sdl.SDL_GetError()
        log(f"SDL_Init FAILED: {err.decode() if err else '?'}")
        return 1

    n = sdl.SDL_NumJoysticks()
    log(f"SDL_NumJoysticks={n}")
    if n <= 0:
        log("VERDICT: no joysticks — BT link may exist but SDL cannot open HID")
        return 2

    gc = None
    for i in range(n):
        is_gc = sdl.SDL_IsGameController(i)
        log(f"  joystick[{i}] is_game_controller={bool(is_gc)}")
        if is_gc and gc is None:
            gc = sdl.SDL_GameControllerOpen(i)
            if gc:
                name = sdl.SDL_GameControllerName(gc)
                log(f"  opened: {name.decode() if name else '?'}")

    if not gc:
        log("VERDICT: joysticks present but no game controller opened")
        return 3

    log(f"Polling {DURATION}s — press A, LB, Xbox logo NOW")
    event = SDL_Event()
    deadline = time.monotonic() + DURATION
    event_count = 0
    poll_ticks = 0

    while time.monotonic() < deadline:
        poll_ticks += 1
        sdl.SDL_PumpEvents()
        while sdl.SDL_PollEvent(ctypes.byref(event)):
            event_count += 1
            et = event.type
            if et == SDL_CONTROLLERBUTTONDOWN:
                btn = event.padding[8]
                log(f"EVENT ControllerButtonDOWN button={btn}")
            elif et == SDL_CONTROLLERBUTTONUP:
                btn = event.padding[8]
                log(f"EVENT ControllerButtonUP button={btn}")
            elif et == SDL_JOYBUTTONDOWN:
                btn = event.padding[8]
                log(f"EVENT JoyButtonDOWN button={btn}")
            elif et == SDL_CONTROLLERAXISMOTION:
                axis = int.from_bytes(bytes(event.padding[4:8]), "little", signed=True)
                val = int.from_bytes(bytes(event.padding[8:12]), "little", signed=True)
                if abs(val) > 1000:
                    log(f"EVENT AxisMotion axis={axis} value={val}")
            elif et in (SDL_JOYDEVICEADDED, SDL_CONTROLLERDEVICEADDED):
                log(f"EVENT device added type=0x{et:x}")
            else:
                log(f"EVENT type=0x{et:x}")

        # Polling fallback: read button state directly
        for btn_id, label in [(0, "A"), (9, "LB"), (10, "RB")]:
            if sdl.SDL_GameControllerGetButton(gc, btn_id):
                log(f"POLL state {label}=1")
        time.sleep(0.02)

    log(f"poll_ticks={poll_ticks} sdl_events={event_count}")
    if event_count == 0:
        log("VERDICT: ZERO SDL events — macOS/BLE input not reaching user-space")
        log("Likely causes: macOS 27 beta regression, background CLI restriction, or controller asleep")
    else:
        log(f"VERDICT: {event_count} events received — hardware path OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
