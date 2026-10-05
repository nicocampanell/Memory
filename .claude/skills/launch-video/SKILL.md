---
name: launch-video
description: Make an animated product launch video for Abode Money (or any product) with this repo's seek(t) studio. Use when asked for a launch video, product film, promo clip, end card or animated demo.
---

# Launch video

## Hard rules (these win over everything else)
- Never redraw product UI. Every product pixel is a real screenshot or crop from `kit/shots`.
- Never synthesize sound. Real recordings from `kit/audio` only.
- No CSS animations, transitions, timers, rAF, Date or Math.random. Every frame is a pure function of t.
- No made-up numbers, names, prices or claims. Only `kit/BRAND.md`'s approved data.
- Nothing fades and nothing cuts. Things change shape into the next thing.
- Follow `CLAUDE.md` (engine, render, checks) and `LOOK.md` (style) in the repo root.

## 1. Collect inputs, in one message, before any work
Ask for everything still missing from `kit/BRAND.md`: product URL or saved pages from a demo
account, what it does in five lines, the pain, three features, the payoff moment, the call to
action, brand colours/fonts/logo, approved data, compliance lines, and up to three reference
films. Don't start building until the story and the approved data are there.

## 2. Build the kit (once per product)
1. Save the real pages into `kit/site`. Screenshot every page and state at 2x into `kit/shots`, crop elements on transparent backgrounds, and record boxes in `kit/crops.js`.
2. Fill the `TODO`s in `LOOK.md` from the real brand. Break the reference films into beats in `kit/references.md`.
3. Sound: one 110-125 BPM track with a clear drop and the eight effects listed in `kit/README.md`, from mixkit.co (free commercial licence) or files the user provides. Record sources in `kit/audio/SOURCES.json`. Then run `python3 studio/measure_audio.py kit/audio` and read `kit/AUDIO.md` and `kit/beats.png`. Tell the user to listen to the track.

## 3. Smoke test
`python3 studio/render.py scenes/00-smoke`, then the determinism, sync and pops checks. If any fail, fix the studio before scenes.

## 4. Five scenes, one technique each
Each one goes in its own folder with its own `index.html` + `timeline.js`, from the brief in its `PROMPT.md`:
hook (`c1-hook`), demo (`c2-demo`), morph (`c3-morph`), proof (`c4-proof`), end card (`c5-end`).
Fill the brief's slots from `kit/BRAND.md`. Show the beat map and stills first, then render, then
run every check in `CLAUDE.md`. These are independent, so run them in parallel when you can.
End each with "what I'd still change".

## 5. Film
Follow `scenes/film/PROMPT.md`: one clock, one soundtrack, shared-shape handoffs, drop on the
payoff, phone-readable. Run every check.

## 6. Notes and formats
Take the user's notes as problem + result. Change only what the notes need. Reframe for 1080x1920 and
1080x1080 from the same timeline, never crop.

## Report
For every render: time taken, what the checks found and fixed, what you'd still change,
and anything decided that the brief didn't say. Say plainly that you measured the sound and never heard it.
