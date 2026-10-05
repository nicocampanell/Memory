# Look: Abode Money launch

> DRAFT. The grammar below is settled. Every `TODO` is a brand value that must come from
> Abode Money's real site or brand guide (`kit/BRAND.md`), not from a guess. Until they're
> filled, scenes must not render finals.

## Canvas
- Light canvas: `TODO: Abode off-white` (fallback #F7F8F6), with a soft 5% tint of the accent behind whatever is in focus. No dark scenes.

## Type
- Headlines: `TODO: Abode's headline face` from `kit/fonts`, weight 700-800, letter-spacing -0.04em.
- One accent word per headline in a contrasting serif italic (`TODO: e.g. Instrument Serif` in `kit/fonts`), in the accent colour.
- Nothing on screen smaller than 28 px at 1080p.

## Colour
- Accent: `TODO: Abode primary` (good news, money landing, "done").
- Warning: `TODO: Abode warning/red`, used only for the one "problem" moment of the story.
- Ink: `TODO` for text, `TODO` for secondary text.

## UI
- Real crops from `kit/shots` on white cards: radius `TODO: match the product's own card radius`, 1px border `TODO`, shadow `0 12px 32px rgba(21,32,27,.08)`.
- The product is always the hero: a card in focus fills at least half the frame width.

## Motion
- Text rises out of a mask line, one word per beat. Nothing fades in and nothing blurs in.
- Things change shape into the next thing instead of cutting: a dot grows into a button, a button stretches into a card, a card folds into a pill.
- A colour change is a shape: a circle grows from the cursor and floods the element.
- One camera move at a time. Zoom in log space.
- Springs with a small overshoot. No linear moves except the cursor's final approach.

## Banned
- 3D, glows, particles, lens flares, gradients on UI, crossfades, invented logos or screens.
- Any hold longer than a beat and a half (except the loop frame).
- Numbered section labels ("01 · CREATE"), cream backgrounds, dark-mode-with-green-glow. These are the model's defaults, not Abode's.

## References
- `TODO`: three launch films in Abode's category you'd be jealous of (whatships.com). Break each
  into beats in `kit/references.md` and steal the grammar, never the words.
