#!/usr/bin/env python3
"""Log Xbox controller buttons via SDL2 to /tmp/gamepad-monitor.log"""
import ctypes, os, sys, time, datetime
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'
LOG = '/tmp/gamepad-monitor.log'
sdl = ctypes.CDLL('/opt/homebrew/lib/libSDL2.dylib')
SDL_Init = sdl.SDL_Init
SDL_GameControllerOpen = sdl.SDL_GameControllerOpen
SDL_GameControllerGetButton = sdl.SDL_GameControllerGetButton
SDL_GameControllerGetAxis = sdl.SDL_GameControllerGetAxis
SDL_GameControllerUpdate = sdl.SDL_GameControllerUpdate
SDL_NumJoysticks = sdl.SDL_NumJoysticks

def log(msg):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
    with open(LOG, 'a') as f:
        f.write(line)
    print(line, end='')

SDL_Init(0x2000 | 0x200)
n = SDL_NumJoysticks()
log(f"start joysticks={n}")
if n == 0:
    sys.exit(1)
gc = SDL_GameControllerOpen(0)
if not gc:
    log("failed open"); sys.exit(1)
log("monitoring — press LT LB RB")
last = {}
while True:
    SDL_GameControllerUpdate()
    lt = SDL_GameControllerGetAxis(gc, 4)
    rt = SDL_GameControllerGetAxis(gc, 5)
    state = {
        'LB': SDL_GameControllerGetButton(gc, 9),
        'RB': SDL_GameControllerGetButton(gc, 10),
        'A': SDL_GameControllerGetButton(gc, 0),
        'LT': lt > 16000,
        'RT': rt > 16000,
    }
    for k, v in state.items():
        if last.get(k) != v:
            if v:
                log(f"DOWN {k} (LTaxis={lt} RTaxis={rt})")
            else:
                log(f"UP {k}")
    last = state
    time.sleep(0.05)
