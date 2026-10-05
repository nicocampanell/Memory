# Abode Money launch video studio: rules

Every video in this repo is a program. A scene is one `index.html` with `window.seek(t)`;
`studio/render.py` films it frame by frame in headless Chromium and ffmpeg makes the MP4.
Read `LOOK.md` for the style and `kit/` for the real product and real sound before any scene work.

## Product
- Every product pixel comes from `kit/shots`: real screenshots and crops (positions in `kit/crops.js`). Never redraw UI.
- Need a state the screenshots don't have? Change a copy of the real page in `kit/site` and screenshot it. Write down what you changed in `kit/site/CHANGES.md`.
- No invented numbers, names, prices or customers. Only what is on Abode Money's real pages (`kit/BRAND.md` lists what's approved). If the story needs data the pages don't have, stop and ask.
- Money is financial copy: use the currency, rounding and wording on the real pages, exactly. Never imply returns, guarantees or approval that the product doesn't state.
- `kit/` is shared and read-only from scenes. Write everything into the scene's own folder.

## Engine
- One `index.html` per scene with `window.SCENE` and `window.seek(t)` (see `studio/render.py`). Load `/studio/lib/motion.js` for springs, keyframes, camera and counters.
- Every frame is a pure function of time: no CSS animations or transitions, no timers, no `requestAnimationFrame`, no `Date`, no `Math.random` (use a seeded function of t), nothing remembered between frames.
- Every time lives in the scene's `timeline.js`, written in beats from `kit/AUDIO.md`. The picture and the sound (`SCENE.cues`, `SCENE.music`) both read it. Moving a moment is a one-number edit.
- Springs are closed-form (`M.spring`) with a small overshoot. A value that changes target more than once is a sum of springs (`M.springs`).
- The camera is one transform on one container (`M.camera` + `M.applyCamera`). Eased keyframes, one move at a time, zoom interpolated in log space.
- Fonts and images are local files in `kit/`. No network requests at render time.
- Don't use `will-change`. The renderer rebuilds every layer each frame, and `will-change` makes Chromium keep a stale raster scale.

## Render
- 1920x1080, 60 fps, H.264 yuv420p BT.709, AAC. `python3 studio/render.py scenes/<name>`.
- Motion blur: `SCENE.subframes` samples per frame over a 180° shutter. Use 4 by default, 8 where anything moves more than 15 px a frame, and 16 over 40 px a frame. Often the better fix is a slower move.
- A counter or any text people must read is never blurred into two values: hold its value fixed across a frame's subframes (drive it from `M.frameT(t)`) and blur only the movement.
- Loops: the first and last frames must hold still for at least 2 frames (blur samples are clamped at t=0), then render with `--loop` and run `checks.py loop`.

## Sound
- Music and effects come from `kit/audio` (real recordings, listed in `kit/AUDIO.md`). Never synthesize sound for a real video.
- Mix from the WAVs in `kit/audio/wav/`, never MP3s (encoder delay).
- The music starts on a downbeat. Each cue lands its sync point on its event: `align: "onset"` by default, `"max"` or explicit ms when AUDIO.md says so. Check the note column for two-hit files.
- The renderer normalises to -14 LUFS (two-pass, linear). You measured the sound. You never heard it: say so.

## Before you show me
- Stills first: `render.py <scene> --stills-at-beats ... --bpm ...` for the beats the brief names, before the full render.
- `checks.py determinism <scene> --frame N` on a frame after the busiest motion.
- `checks.py contact <video> --bpm <bpm> --offset <downbeat>`: look at it and fix the three worst problems.
- `checks.py pops <video>`: fix every flagged frame.
- `checks.py sync <video> --event <t>` on the two most important cues.
- `checks.py phone <video>`: text in focus must read at 360 px wide. Nothing smaller than 28 px at 1080p.
- Finish with: what you fixed, what you'd still change, and anything you decided that the brief didn't.
