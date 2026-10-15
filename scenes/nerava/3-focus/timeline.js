// Blur to focus, tracking tightens. Beats at a nominal 120 bpm (no music yet).
const CLOCK = M.clock({ bpm: 120, offset: 0 });
const B = CLOCK.at;
const T = {
  letters: B(0.4),   // letters come in from wide tracking and soft focus, centre letters first
  stagger: 0.07,     // seconds between rings of letters (centre -> outside)
  bolt: B(3.4),      // the word makes room and the bolt snaps in, sharp
  end: B(8),
};
