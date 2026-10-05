# c5-end: a card that loops (10 beats)

Technique: on X videos loop. If the last frame matches the first, the loop disappears and people watch twice.

```text
Make scenes/c5-end/clip.mp4: a 10-beat end card for Abode Money that loops, the product in kit/. Follow CLAUDE.md and LOOK.md, and use the tempo in kit/AUDIO.md.

Beats 0-2: an accent dot in the centre springs up into the real Abode Money logo mark (kit/logo.svg) at 160px.
Beat 3: the wordmark wipes out from behind the mark.
Beats 4-5: the tagline from kit/BRAND.md rises in under it in two parts, with the second part as the serif accent.
Beat 6: the real call-to-action button from the landing page pops in. The cursor clicks it on beat 8, with a click.
Beats 8-10: everything folds back into the dot over at least three beats, so the last frame is the same as the first and the clip loops.

Hold the first and last frames still for at least 2 frames. Render with --loop and prove the first and last frames of the MP4 are identical with checks.py loop.
```
