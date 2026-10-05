# Abode Money launch video studio

A $5,000 studio launch film, made as code. Each scene is a web page with one function,
`window.seek(t)`, that draws the exact frame for any moment. Headless Chromium films it
frame by frame, and ffmpeg joins the frames and the sound into an MP4. Same code, same video,
every time. A change is one line and a re-render.

The five-file studio:

| File | Job |
|---|---|
| `CLAUDE.md` | **Rules**: the standard for every frame, render and check |
| `LOOK.md` | **Look**: the style card that kills the model's cheap defaults (draft: brand TODOs) |
| `kit/` | **Kit**: Abode's real screens and real sounds, measured |
| `scenes/c1…c5/PROMPT.md` | **Scenes**: five short clips, one technique each |
| `scenes/film/PROMPT.md` | **Clock**: one timeline that joins them into a film |

Plus `.claude/skills/launch-video/SKILL.md`, so Claude Code can run the whole pipeline from one sentence.

## Setup

```bash
pip install -r studio/requirements.txt     # needs ffmpeg and Chromium (Playwright)
python3 studio/render.py scenes/00-smoke   # smoke test: renders scenes/00-smoke/clip.mp4
python3 studio/checks.py determinism scenes/00-smoke --frame 90
python3 studio/checks.py sync scenes/00-smoke/clip.mp4 --event 1.0
python3 studio/checks.py pops scenes/00-smoke/clip.mp4
```

## Tools

| Command | Does |
|---|---|
| `studio/render.py <scene> [--loop] [--workers N]` | Render to `<scene>/clip.mp4` with motion blur, mixed sound at -14 LUFS |
| `studio/render.py <scene> --stills-at-beats 2,7,12 --bpm 120 --offset 0.3` | Stills sheet for review before a full render |
| `studio/checks.py determinism <scene> --frame N` | Same frame from a fresh browser vs after rendering the whole timeline |
| `studio/checks.py contact <video> --bpm B --offset D` | One frame per beat on one sheet |
| `studio/checks.py pops <video>` | Single-frame glitches and jumps |
| `studio/checks.py sync <video> --event T` | Where the sound actually lands vs its event |
| `studio/checks.py loop <video>` | First and last frames identical? |
| `studio/checks.py phone <video>` | 360 px phone sheet + first-frame thumbnail |
| `studio/measure_audio.py kit/audio` | BPM, downbeat, beat grid, drop, effect sync points → `kit/AUDIO.md`, `kit/beats.png` |

## Next: what Abode needs to supply
Fill `kit/BRAND.md` (story, brand, approved demo data, compliance), add the logo and fonts,
and give access to the real product pages (a demo account or saved pages). Then the sound kit:
either allow `mixkit.co` in the environment's network settings or drop licensed files into `kit/audio/`.
