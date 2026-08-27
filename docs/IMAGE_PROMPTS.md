# VibePad — ChatGPT image prompts (hackathon visuals)

Use these in ChatGPT (or similar) **image generation**. Keep a consistent art direction across the set so slices can become a GIF later.

## Art direction (paste once per session)

```text
Art direction for all frames:
- Product: VibePad — Xbox controller driving Ghostty terminal “Vibe Coding” on macOS
- Mood: cozy night coding, soft ambient light, slightly cinematic, not gamer-neon, not purple haze
- Palette: deep charcoal / warm amber accent / Ghostty-like terminal greens on dark UI
- Style: clean product illustration, readable UI chrome, no tiny illegible text, no watermarks, no logos of Xbox/Microsoft/Apple trademarks as brand marks (generic gamepad + terminal OK)
- Aspect: 16:10 or 1586×992 to match existing assets
- Avoid: cluttered dashboards, floating badges, sticker UI, comic speech bubbles
```

## Shot list (priority order for Submit screenshots — max 5)

### 1) Hero — couch / bed setup (replace or sit beside `vibepad-setup-environment.png`)

```text
Wide product hero: person reclining with a generic Xbox-style Bluetooth gamepad, looking at large external monitors showing a dark terminal (Ghostty-like) with an AI coding agent chat. Soft bedroom/living-room night lighting, Mac silhouette on desk edge, calm and premium. Title space top-left for “VibePad”. No readable copyrighted logos.
```

**Save as:** `assets/vibepad-hero-couch.png`

### 2) Feature overview (replace or refresh `vibepad-use-cases-features.png`)

```text
Single infographic panel explaining VibePad: left side gamepad with labeled callouts (LB = voice, A = send, B = clear, sticks = mouse/scroll); right side three vignettes — Ghostty agent workflow, multi-monitor cursor, Safari video rest. Dark charcoal background, amber accents, clean sans-serif labels in English only.
```

**Save as:** `assets/vibepad-use-cases-features.png` (overwrite only if better than current)

### 3–5) Slice frames for GIF / carousel (English labels)

**Slice 01 — Voice**

```text
Close-up illustrated gamepad LB bumper glowing amber; inset terminal with microphone waveform and caption “LB · Voice toggle (Doubao)”. Dark UI, minimal.
```

**Save as:** `assets/slices/01-voice-lb.png`

**Slice 02 — Send**

```text
Gamepad A button highlighted; terminal input box with a short prompt and caption “A · Send to agent”. Dark UI, minimal.
```

**Save as:** `assets/slices/02-send-a.png`

**Slice 03 — Clear**

```text
Gamepad B button highlighted; terminal line being cleared with caption “B · Clear input (Ctrl+U)”. Dark UI, minimal.
```

**Save as:** `assets/slices/03-clear-b.png`

**Slice 04 — Mouse**

```text
Left stick highlighted; cursor moving across two ultrawide monitors with caption “Left stick · Multi-monitor mouse”. Dark UI, minimal.
```

**Save as:** `assets/slices/04-mouse-stick.png`

**Slice 05 — Rest mode**

```text
RB bumper highlighted; scene switches from terminal to Safari-like video player with caption “RB · Safari rest mode”. Dark UI, minimal.
```

**Save as:** `assets/slices/05-safari-rest.png`

## Assembling a GIF later (optional, after 8:00 PM submit)

1. Export slices 01→05 at the same resolution.
2. Order: hero moment optional → 01 → 02 → 03 → 04 → 05 → loop.
3. ~800–1200 ms per frame; save as `assets/vibepad-feature-tour.gif`.
4. Uncomment the GIF block in `README.md`.

Suggested macOS assemble (when you have the PNGs):

```bash
mkdir -p assets/slices
# drop ChatGPT PNGs into assets/slices/
# then e.g. with ImageMagick:
# convert -delay 100 -loop 0 assets/slices/0*.png assets/vibepad-feature-tour.gif
```

## Submit Project — which 5 screenshots to upload tonight

If new ChatGPT art is not ready before **8:00 PM**, upload these from the repo (already public):

1. `assets/vibepad-setup-environment.png`
2. `assets/vibepad-use-cases-features.png`
3. (Optional third) any clear terminal + gamepad photo you already have
3–5. Add unique frames only when ready (hero / slices). Prefer fewer unique shots over duplicates.

When new art lands, you can update the submission anytime before judging closes if the hub allows edits.
