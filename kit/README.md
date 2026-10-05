# Kit: the real product and the real sound

Shared by every scene. Read-only from scenes.

| Path | What goes here | Who makes it |
|---|---|---|
| `BRAND.md` | Product story, brand values, approved data, compliance | Abode team |
| `logo.svg` | The real logo | Abode team |
| `fonts/` | Brand fonts as local files (.woff2/.ttf) plus their licences | Abode team |
| `site/` | A saved copy of each real page (HTML/CSS) from a demo account, so new states can be made by editing it | Claude Code, from the real site |
| `site/CHANGES.md` | Every edit made to `site/`, and how to undo it | Claude Code |
| `shots/` | Screenshots at 2x of every page and state used, plus transparent-background element crops | Claude Code, from `site/` |
| `crops.js` | The box of every crop in its source shot | Claude Code |
| `audio/music/`, `audio/sfx/` | Real recordings (Mixkit or licensed), never synthesized | Claude Code (needs network access to mixkit.co) or you |
| `audio/SOURCES.json` | Source page and licence of each audio file | Claude Code |
| `AUDIO.md`, `beats.png` | Measured BPM, downbeat, beat grid, drop, effect sync points | `python3 studio/measure_audio.py kit/audio` |

## Sound kit you need
One modern, minimal, upbeat track between 110 and 125 BPM with a clear drop, plus one short clean
sound for each of: mouse click, soft keyboard typing, whoosh, pop, notification ding,
success chime, coin/cash, soft impact. Put them in `audio/music/` and `audio/sfx/`, fill
`audio/SOURCES.json`, then run the measurer and *listen* to the track before building on it.
